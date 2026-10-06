#!/usr/bin/env python3
"""Generate every Arabic dialogue line of the game through OpenRouter (Gemini TTS).

    python3 tools/openrouter_tts_lines.py --list-models      # which speech models OpenRouter has right now
    python3 tools/openrouter_tts_lines.py --limit 5          # quick test, then listen
    python3 tools/openrouter_tts_lines.py                    # all missing lines (resumable)
    python3 tools/openrouter_tts_lines.py --retry-failed     # only the ones that failed
    python3 tools/voice_import.py tools/voice_raw_openrouter --no-post   # → public/audio + manifest.json

No packages needed (standard library only).
Key: OPENROUTER_API_KEY, or ~/.config/lura/keys.json → "openrouter" (Lura's key). Never printed.
Model: google/gemini-3.8-flash-lite-tts by default (--model <id> to change; --list-models to see others).

Each character has its own voice and a profile (tools/voices_openrouter.json, created on the
first run). Each line also gets a tone of its own — a question sounds curious, praise sounds
proud, a long story beat is told slowly — guessed from the text, and overridable per line in
tools/voice_tones.json  {"<line id>": "whispering, amazed"}.

Up to 5 attempts per line (back-off; honours Retry-After / "retry in Xs" on 429). Lines that
still fail go to tools/voice_raw_openrouter/_failed.json and the run continues. When the
account is out of credit or a daily limit is hit, the run stops; run again later and it
continues — finished files are never regenerated.
"""
import argparse, json, os, re, sys, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINES = ROOT / 'tools/voice_lines.json'
OUT = ROOT / 'tools/voice_raw_openrouter'
FAILED = OUT / '_failed.json'
VOICES = ROOT / 'tools/voices_openrouter.json'
TONES = ROOT / 'tools/voice_tones.json'
BASE = 'https://openrouter.ai/api/v1'
HEADERS = {'HTTP-Referer': 'https://github.com/local/quran-journey', 'X-Title': 'quran-journey-voices'}
ATTEMPTS = 5

DEFAULT_VOICES = {
    "_note": "Gemini prebuilt voice + profile per character. Change a voice, delete that character's wavs, run again.",
    "zainab":   {"voice": "Sulafat",      "profile": "Grandma Zainab: an elderly, loving grandmother telling her grandson a Quran story. Warm, gentle, unhurried."},
    "amina":    {"voice": "Vindemiatrix", "profile": "Grandma Amina: a kind elderly grandmother. Soft, patient and caring, like a bedtime storyteller."},
    "farmer":   {"voice": "Algenib",      "profile": "Grandpa Salim: an old village farmer. Deep, slightly gravelly, wise and kind; speaks slowly."},
    "hamdan":   {"voice": "Charon",       "profile": "Uncle Hamdan: a friendly middle-aged village man. Clear, confident and warm."},
    "player":   {"voice": "Leda",         "profile": "The player: a curious eight-year-old Arab boy. A small, light, high child's voice, bright and eager, never an adult's; short breaths, a little shy and excited.", "post": "rubberband=pitch=1.14"},
    "narrator": {"voice": "Mako",         "profile": "The game narrator: warm, friendly and encouraging, for children."},
}


def api_key():
    k = os.environ.get('OPENROUTER_API_KEY')
    if not k:
        p = Path.home() / '.config/lura/keys.json'
        if p.exists():
            k = json.loads(p.read_text()).get('openrouter')
    if not k:
        sys.exit('No OpenRouter key: set OPENROUTER_API_KEY or store it with `lura login --provider openrouter`.')
    return k


def request(path, key=None, body=None, timeout=120):
    h = dict(HEADERS, **({'Authorization': f'Bearer {key}'} if key else {}))
    data = None
    if body is not None:
        data = json.dumps(body).encode(); h['Content-Type'] = 'application/json'
    req = urllib.request.Request(BASE + path, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get('Content-Type', '')


def speech_models():
    raw, _ = request('/models')
    out = []
    for m in json.loads(raw)['data']:
        arch = m.get('architecture') or {}
        outs = arch.get('output_modalities') or []
        if 'audio' in outs or re.search(r'tts|speech', m['id'], re.I):
            out.append(m)
    return out


DEFAULT_MODEL = 'google/gemini-3.8-flash-lite-tts'


def pick_model(arg):
    if arg:
        return arg
    return DEFAULT_MODEL
    ms = [m['id'] for m in speech_models()]
    for mid in ms:
        if 'gemini' in mid.lower() and 'tts' in mid.lower():
            return mid
    sys.exit('No Gemini TTS model found on OpenRouter. Speech models available:\n  ' + '\n  '.join(ms) +
             '\nPick one with --model <id>.')


def tone_for(line, tones):
    if line['id'] in tones:
        return tones[line['id']]
    t, sp = line['text'], line['speaker']
    if re.search(r'أحسنت|بارك الله|رائع|ممتاز|أصبت|صحيح', t):
        return 'proud, cheerful, smiling'
    if re.search(r'حاول|فكّر|انتبه|ليس تمامًا|لا بأس', t):
        return 'gentle, encouraging, patient'
    if t.strip().endswith(('؟', '?')):
        return 'curious, eager, asking' if sp == 'player' else 'thoughtful, inviting the child to think'
    if sp == 'narrator':
        return 'warm, encouraging, inviting'
    if len(t) > 140:
        return 'calm storytelling, unhurried, with natural pauses'
    if '!' in t:
        return 'lively, warm, excited' if sp == 'player' else 'warm, delighted'
    if sp == 'player':
        return 'curious, polite child'
    return 'warm, gentle, kind'


def build_input(line, v, tone):
    text = line['text'].replace('ﷺ', 'صلى الله عليه وسلم')
    return f'[{tone}] {text}'


def instructions(v, tone):
    return (v['profile'] + ' Speak Modern Standard Arabic (فصحى) clearly and follow the tashkeel exactly. '
            f'Tone for this line: {tone}. Read only the line, nothing else.')


def wait_from(err_text, headers, attempt):
    ra = headers.get('Retry-After') if headers else None
    if ra and ra.strip().replace('.', '', 1).isdigit():
        return min(float(ra) + 1, 180)
    m = re.search(r'retry (?:in|after) (\d+(?:\.\d+)?)', err_text, re.I)
    if m:
        return min(float(m.group(1)) + 2, 180)
    return min(10 * 2 ** attempt, 120)


def fatal(code, text):
    if code == 402 or re.search(r'insufficient credits|out of credit', text, re.I):
        return 'The OpenRouter account is out of credit.'
    if code == 401:
        return 'OpenRouter rejected the key (401).'
    if re.search(r'per ?day|daily', text, re.I):
        return 'A daily limit was reached.'
    return None


CHILD_CANDIDATES = ['Leda', 'Zephyr', 'Laomedeia', 'Autonoe', 'Aoede', 'Kore', 'Callirrhoe', 'Puck']


def postprocess(path, filt):
    """Optional per-character ffmpeg filter (e.g. raise the boy's pitch). Falls back to a
    plain resample pitch shift when this ffmpeg has no rubberband."""
    if not filt:
        return
    import shutil, subprocess
    if not shutil.which('ffmpeg'):
        print('  (ffmpeg not found — skipping post filter)'); return
    tmp = path.with_name(path.stem + '.tmp' + path.suffix)
    for f in (filt, None):
        if f is None:
            m = re.search(r'pitch=([\d.]+)', filt)
            if not m:
                return
            k = float(m.group(1)); f = f'asetrate=24000*{k},aresample=24000,atempo={1 / k:.4f}'
        r = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(path), '-af', f, str(tmp)], capture_output=True)
        if r.returncode == 0:
            tmp.replace(path); return


def audition(key, model, voices, lines, speaker, fmt):
    """Same sample line in several voices (raw + pitched up) so you can pick the best."""
    v = voices.get(speaker) or voices['narrator']
    sample = next((L for L in lines if L['speaker'] == speaker and 25 < len(L['text']) < 90), None) or next(L for L in lines if L['speaker'] == speaker)
    out = OUT / '_audition'; out.mkdir(parents=True, exist_ok=True)
    tone = tone_for(sample, {})
    print(f'sample ({speaker}): {sample["text"]}', flush=True)
    for name in CHILD_CANDIDATES if speaker == 'player' else [v['voice']]:
        body = {'model': model, 'input': build_input(sample, v, tone), 'voice': name, 'response_format': fmt,
                'instructions': instructions(v, tone)}
        for attempt in range(ATTEMPTS):
            try:
                audio, ctype = request('/audio/speech', key, body)
                break
            except urllib.error.HTTPError as e:
                text = e.read().decode('utf-8', 'replace')
                if e.code == 400 and 'instruction' in text.lower():
                    body.pop('instructions', None); continue
                if e.code == 400:
                    sys.exit(text[:600])
                time.sleep(wait_from(text, e.headers, attempt))
        else:
            print(f'  {name}: failed'); continue
        f = out / f'{speaker}_{name}.wav'
        f.write_bytes(to_wav(audio, ctype, fmt))
        g = out / f'{speaker}_{name}_pitch114.wav'
        g.write_bytes(f.read_bytes()); postprocess(g, 'rubberband=pitch=1.14')
        print(f'  ✓ {f.name}  +  {g.name}', flush=True)
        time.sleep(6)
    print(f'\nListen in {out.relative_to(ROOT)}/ — put the voice you like (and "post": "rubberband=pitch=1.14" if the\n'
          f'pitched one is better) under "{speaker}" in {VOICES.relative_to(ROOT)}, delete that speaker\'s old wavs, run again.')


def to_wav(audio, ctype, fmt):
    if fmt == 'pcm' or 'pcm' in ctype or 'L16' in ctype:
        import struct
        rate = int(m.group(1)) if (m := re.search(r'rate=(\d+)', ctype)) else 24000
        return struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36 + len(audio), b'WAVE', b'fmt ', 16, 1, 1, rate, rate * 2, 2, 16, b'data', len(audio)) + audio
    return audio


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list-models', action='store_true')
    ap.add_argument('--audition', metavar='SPEAKER', help='try one sample line in several voices (player: 8 child-voice candidates)')
    ap.add_argument('--model')
    ap.add_argument('--retry-failed', action='store_true')
    ap.add_argument('--only', help='only one speaker: zainab, amina, farmer, hamdan, player, narrator')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--rpm', type=float, default=10, help='max requests per minute (default 10)')
    ap.add_argument('--format', default='pcm', choices=['pcm', 'mp3', 'wav'])
    ap.add_argument('--no-instructions', action='store_true', help='send only "[tone] text" (if the model rejects instructions)')
    a = ap.parse_args()

    if a.list_models:
        for m in speech_models():
            p = m.get('pricing') or {}
            print(f"{m['id']:<45} out={','.join((m.get('architecture') or {}).get('output_modalities') or [])} price={p}")
        return

    key = api_key()
    model = pick_model(a.model)
    OUT.mkdir(parents=True, exist_ok=True)
    if not VOICES.exists():
        VOICES.write_text(json.dumps(DEFAULT_VOICES, ensure_ascii=False, indent=2))
    voices = json.loads(VOICES.read_text())
    tones = json.loads(TONES.read_text()) if TONES.exists() else {}
    lines = json.loads(LINES.read_text())
    if a.audition:
        return audition(key, model, voices, lines, a.audition, a.format)
    failed = json.loads(FAILED.read_text()) if FAILED.exists() else {}

    def path(L, ext=None):
        base = OUT / L['id'].replace('/', '__')
        if ext:
            return base.with_suffix('.' + ext)
        return next((base.with_suffix(x) for x in ('.wav', '.mp3') if base.with_suffix(x).exists()), None)

    todo = [L for L in lines if not path(L)]
    if a.retry_failed:
        todo = [L for L in todo if L['id'] in failed]
    if a.only:
        todo = [L for L in todo if L['speaker'] == a.only]
    if a.limit:
        todo = todo[:a.limit]
    print(f'model {model} · {len(lines)} lines · {len(lines) - len([L for L in lines if not path(L)])} done · {len(todo)} to generate', flush=True)

    use_instr = not a.no_instructions
    gap, last, ok = 60.0 / max(a.rpm, .1), 0.0, 0
    save = lambda: FAILED.write_text(json.dumps(failed, ensure_ascii=False, indent=1))
    try:
        for i, L in enumerate(todo, 1):
            v = voices.get(L['speaker']) or voices['narrator']
            tone = tone_for(L, tones)
            err = ''
            for attempt in range(ATTEMPTS):
                w = last + gap - time.time()
                if w > 0:
                    time.sleep(w)
                last = time.time()
                body = {'model': model, 'input': build_input(L, v, tone), 'voice': v['voice'], 'response_format': a.format}
                if use_instr:
                    body['instructions'] = instructions(v, tone)
                try:
                    audio, ctype = request('/audio/speech', key, body, timeout=120)
                    if len(audio) < 1000 or 'json' in ctype:
                        raise RuntimeError(f'no audio in response ({ctype}): {audio[:200]!r}')
                    if a.format == 'pcm' or 'pcm' in ctype or 'L16' in ctype:
                        import struct
                        rate = int(m.group(1)) if (m := re.search(r'rate=(\d+)', ctype)) else 24000
                        audio = struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36 + len(audio), b'WAVE', b'fmt ', 16, 1, 1, rate, rate * 2, 2, 16, b'data', len(audio)) + audio
                        ext = 'wav'
                    else:
                        ext = 'wav' if ('wav' in ctype and 'mpeg' not in ctype) else 'mp3'
                    path(L, ext).write_bytes(audio)
                    postprocess(path(L, ext), v.get('post'))
                    failed.pop(L['id'], None); ok += 1; err = ''
                    print(f'{i}/{len(todo)} ✓ {L["id"]}  [{tone}]', flush=True)
                    break
                except urllib.error.HTTPError as e:
                    text = e.read().decode('utf-8', 'replace')
                    err = f'HTTP {e.code}: {text[:240]}'
                    if e.code == 400 and 'response_format' in text:
                        want = 'pcm' if '"pcm"' in text or "'pcm'" in text or 'pcm' in text.split('Got')[0] else 'mp3'
                        if want != a.format:
                            a.format = want
                            print(f'  model wants response_format={want} — switching', flush=True)
                            continue
                    if e.code == 400 and use_instr and re.search(r'instruction', text, re.I):
                        use_instr = False
                        print('  model does not take "instructions" — sending the tone inside the text only', flush=True)
                        continue
                    if e.code == 400:
                        failed[L['id']] = {'text': L['text'], 'error': text[:1500]}; save()
                        sys.exit(f'\nOpenRouter rejected the request (400) — not retrying, it would fail the same way:\n{text[:1500]}')
                    if (msg := fatal(e.code, text)):
                        failed[L['id']] = {'text': L['text'], 'error': err}; save()
                        sys.exit(f'\n{msg} Stopped after {ok} new lines — run again later; finished files are kept.')
                    d = wait_from(text, e.headers, attempt)
                except Exception as e:
                    err = str(e)[:240]; d = min(10 * 2 ** attempt, 120)
                print(f'  {L["id"]}: attempt {attempt + 1}/{ATTEMPTS} failed ({err[:150]}); waiting {d:.0f}s', flush=True)
                if attempt < ATTEMPTS - 1:
                    time.sleep(d)
            if err:
                failed[L['id']] = {'text': L['text'], 'error': err}
                print(f'{i}/{len(todo)} ✗ {L["id"]} — gave up after {ATTEMPTS} attempts', flush=True)
                save()
    except KeyboardInterrupt:
        print('\nStopped. Finished files are kept.')
    finally:
        save()
    print(f'\nDone: {ok} generated, {len(failed)} failed (see {FAILED.relative_to(ROOT)}).')
    if failed:
        print('Retry them with:  python3 tools/openrouter_tts_lines.py --retry-failed')
    print('Then import:      python3 tools/voice_import.py tools/voice_raw_openrouter --no-post')


if __name__ == '__main__':
    main()
