#!/usr/bin/env python3
"""Generate every Arabic dialogue line of the game with Gemini TTS (gemini-3.8-flash-tts).

    python3 tools/gemini_tts_lines.py                 # all missing lines (resumable)
    python3 tools/gemini_tts_lines.py --retry-failed  # only the lines that failed last time
    python3 tools/gemini_tts_lines.py --only farmer --limit 20 --rpm 6
    python3 tools/voice_import.py tools/voice_raw_gemini --no-post   # → public/audio + manifest.json

Needs `pip install google-genai` (Lura's venv already has it:
    /var/www/html/lura/.venv/bin/python tools/gemini_tts_lines.py).
Key: GEMINI_API_KEY, or ~/.config/lura/keys.json → "gemini". It is never printed.

Lines come from tools/voice_lines.json (rebuild it first with `python3 tools/voice_lines.py ar`
when the stories change). Output: tools/voice_raw_gemini/<enc>__<speaker>-<hash>.wav — the same
naming voice_import.py expects. A line that exists is never regenerated, so the script can be
stopped and run again at any time.

Errors: every line gets up to 5 attempts (back-off, honouring the server's retry delay on
429 / RESOURCE_EXHAUSTED). A line that still fails is written to
tools/voice_raw_gemini/_failed.json with its last error, and the run moves on. When the
quota for the day is used up the run stops on its own; run it again later (or with
--retry-failed) and it picks up where it left off.
Voices per character: tools/voices_gemini.json (created with defaults on first run).
"""
import argparse, json, os, re, struct, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINES = ROOT / 'tools/voice_lines.json'
OUT = ROOT / 'tools/voice_raw_gemini'
FAILED = OUT / '_failed.json'
SUSPECT = OUT / '_suspect.json'
VOICES = ROOT / 'tools/voices_gemini.json'
MODEL = 'gemini-3.8-flash-tts'
ATTEMPTS = 5

DEFAULT_VOICES = {
    "_note": "Gemini prebuilt voice + a short English profile per character. Edit freely; delete a line's wav to regenerate it.",
    "zainab":   {"voice": "Sulafat",      "profile": "Grandma Zainab, an elderly, loving Egyptian grandmother telling her grandson a Quran story; warm, gentle and unhurried."},
    "amina":    {"voice": "Vindemiatrix", "profile": "Grandma Amina, a kind elderly grandmother; soft, patient and caring, like a bedtime storyteller."},
    "farmer":   {"voice": "Algenib",      "profile": "Grandpa Salim, an old village farmer; deep, slightly gravelly, wise and kind, speaks slowly."},
    "hamdan":   {"voice": "Charon",       "profile": "Uncle Hamdan, a friendly middle-aged village man; clear, confident and warm."},
    "player":   {"voice": "Puck",         "profile": "A curious nine-year-old boy; bright, eager and polite, asking his grandparents questions."},
    "narrator": {"voice": "Mako",         "profile": "A warm, friendly narrator for a children's game; encouraging and clear."},
}


def gemini_key():
    k = os.environ.get('GEMINI_API_KEY')
    if not k:
        k = json.loads((Path.home() / '.config/lura/keys.json').read_text())['gemini']
    return k


def wav_from_pcm(data, mime):
    rate = int(m.group(1)) if (m := re.search(r'rate=(\d+)', mime or '')) else 24000
    bits = int(m.group(1)) if (m := re.search(r'audio/L(\d+)', mime or '')) else 16
    block = bits // 8
    return struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36 + len(data), b'WAVE', b'fmt ', 16, 1, 1,
                       rate, rate * block, block, bits, b'data', len(data)) + data, rate, bits


def prompt(line, v, plain):
    text = line['text'].replace('ﷺ', 'صلى الله عليه وسلم')
    if plain:
        return '## Transcript:\n' + text
    return ('# AUDIO PROFILE\n' + v['profile'] + '\n'
            '## DIRECTOR\'S NOTES\nSpeak Modern Standard Arabic (فصحى) clearly, following the tashkeel exactly. '
            'Natural storytelling for children. Read only the transcript, nothing else.\n'
            '## Transcript:\n' + text)


def retry_delay(msg, attempt):
    m = re.search(r"retry(?:Delay)?['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", msg, re.I) or re.search(r'retry in (\d+(?:\.\d+)?)', msg, re.I)
    if m:
        return min(float(m.group(1)) + 2, 180)
    return min(10 * 2 ** attempt, 120)


def is_daily_quota(msg):
    return bool(re.search(r'per ?day|PerDay|daily', msg, re.I))


def synth(client, types, line, v, plain):
    cfg = types.GenerateContentConfig(
        temperature=1, response_modalities=['audio'],
        speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=v['voice']))))
    audio, mime = bytearray(), ''
    for ch in client.models.generate_content_stream(
            model=MODEL, config=cfg,
            contents=[types.Content(role='user', parts=[types.Part.from_text(text=prompt(line, v, plain))])]):
        if ch.parts is None:
            continue
        p = ch.parts[0]
        if p.inline_data and p.inline_data.data:
            audio.extend(p.inline_data.data); mime = p.inline_data.mime_type
    if not audio:
        raise RuntimeError('no audio in response')
    return wav_from_pcm(bytes(audio), mime)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--retry-failed', action='store_true', help='only lines listed in _failed.json')
    ap.add_argument('--only', help='only this speaker (zainab, amina, farmer, hamdan, player, narrator)')
    ap.add_argument('--limit', type=int, default=0, help='stop after N lines')
    ap.add_argument('--rpm', type=float, default=8, help='max requests per minute (default 8)')
    ap.add_argument('--plain', action='store_true', help='send only the transcript, no voice profile')
    a = ap.parse_args()

    from google import genai
    from google.genai import types
    client = genai.Client(api_key=gemini_key())

    OUT.mkdir(parents=True, exist_ok=True)
    if not VOICES.exists():
        VOICES.write_text(json.dumps(DEFAULT_VOICES, ensure_ascii=False, indent=2))
    voices = json.loads(VOICES.read_text())
    lines = json.loads(LINES.read_text())
    failed = json.loads(FAILED.read_text()) if FAILED.exists() else {}
    suspect = json.loads(SUSPECT.read_text()) if SUSPECT.exists() else {}

    path = lambda L: OUT / (L['id'].replace('/', '__') + '.wav')
    todo = [L for L in lines if not path(L).exists()]
    if a.retry_failed:
        todo = [L for L in todo if L['id'] in failed]
    if a.only:
        todo = [L for L in todo if L['speaker'] == a.only]
    if a.limit:
        todo = todo[:a.limit]
    print(f'{len(lines)} lines · {len(lines) - len([L for L in lines if not path(L).exists()])} done · {len(todo)} to generate', flush=True)

    gap, last, ok = 60.0 / max(a.rpm, .1), 0.0, 0
    save = lambda: (FAILED.write_text(json.dumps(failed, ensure_ascii=False, indent=1)),
                    SUSPECT.write_text(json.dumps(suspect, ensure_ascii=False, indent=1)))
    try:
        for i, L in enumerate(todo, 1):
            v = voices.get(L['speaker']) or voices['narrator']
            err = ''
            for attempt in range(ATTEMPTS):
                wait = last + gap - time.time()
                if wait > 0:
                    time.sleep(wait)
                last = time.time()
                try:
                    wav, rate, bits = synth(client, types, L, v, a.plain)
                    secs = (len(wav) - 44) / (rate * bits / 8)
                    chars = len(re.sub(r'[ً-ْ\s]', '', L['text']))
                    # far too long for the text → the model probably read the notes aloud; try again
                    if secs > max(4.0, chars * 0.22) and attempt < ATTEMPTS - 1 and not a.plain:
                        err = f'suspicious length {secs:.1f}s for {chars} chars'
                        print(f'  {L["id"]}: {err}, retrying', flush=True)
                        continue
                    path(L).write_bytes(wav)
                    failed.pop(L['id'], None)
                    if err.startswith('suspicious'):
                        suspect[L['id']] = err
                    ok += 1
                    print(f'{i}/{len(todo)} ✓ {L["id"]} ({secs:.1f}s)', flush=True)
                    err = ''
                    break
                except Exception as e:
                    err = str(e)
                    short = err.replace('\n', ' ')[:180]
                    if is_daily_quota(err):
                        failed[L['id']] = {'text': L['text'], 'error': short}
                        save()
                        sys.exit(f'\nDaily quota reached after {ok} new lines. Run again later — finished files are kept; '
                                 f'{len(failed)} line(s) are listed in {FAILED.relative_to(ROOT)}.')
                    d = retry_delay(err, attempt)
                    print(f'  {L["id"]}: attempt {attempt + 1}/{ATTEMPTS} failed ({short}); waiting {d:.0f}s', flush=True)
                    if attempt < ATTEMPTS - 1:
                        time.sleep(d)
            if err:
                failed[L['id']] = {'text': L['text'], 'error': err.replace('\n', ' ')[:300]}
                print(f'{i}/{len(todo)} ✗ {L["id"]} — gave up after {ATTEMPTS} attempts', flush=True)
                save()
    except KeyboardInterrupt:
        print('\nStopped. Finished files are kept.')
    finally:
        save()
    print(f'\nDone: {ok} generated, {len(failed)} failed (see {FAILED.relative_to(ROOT)}).')
    if failed:
        print('Retry them with:  python3 tools/gemini_tts_lines.py --retry-failed')
    print('Then import:      python3 tools/voice_import.py tools/voice_raw_gemini --no-post')


if __name__ == '__main__':
    main()
