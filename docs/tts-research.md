# Dialogue voice-over: text → speech research (Sept 2026)

Scope: the character dialogue lines in `public/data/encounters.json` (Arabic + English).
**Quran recitation stays with real reciters via Quran.com and is never synthesised.** The
`verses` steps are skipped by everything below.

What the data holds today (counted from encounters.json): 9 encounters, 44 `say`, 43 `choice`,
18 `question` steps. Counting the replies, hints, praise lines and the child's own questions, that
comes to **418 audio lines (209 per language, about 34k characters in total)**. The script's `--dry-run` confirms this: farmer 62, hamdan 48, amina 43, player 41, grandma 15 per language. Speakers: `grandma` (Zainab), `amina` (Grandma Amina),
`farmer` (Grandpa Salim), `hamdan` (Uncle Hamdan), `player` (the boy, about 41 lines). The
single-character encounters (`quraysh-journeys`, `yusuf-dream`) have no `host`/`id`, so the
speaker comes from `character.name.en`. The Arabic is simple MSA with Egyptian touches
("اقعد", "فيه", "من عينيّ"), mostly **without** full tashkeel.

---

## TL;DR: ranked recommendation

| Goal | Pick | Why |
|---|---|---|
| **1. Best quality** | **Habibi-TTS** (open, F5-TTS based). Use the **EGY** or **MSA** specialised checkpoint and give each character a consented reference clip. Hosted alternative: **ElevenLabs v3** or **Azure ar-EG Neural** (Salma/Shakir). | The Habibi paper reports it beats ElevenLabs v3 (alpha) on all six major dialect test sets. It needs no tashkeel, and voice cloning gives a distinct voice to each of grandpa, grandma, uncle and boy. |
| **2. Best free + commercial-OK** | **Habibi-TTS EGY/MSA (Apache-2.0)** for Arabic, **Kokoro-82M (Apache-2.0)** or **Chatterbox (MIT)** for English. Runner-ups: **SILMA TTS v1** (Apache-2.0, MSA+English, 150M, light) and **Chatterbox Multilingual / NAMAA-Egyptian-TTS** (MIT). | These are the only strong options whose weights clearly allow commercial use. Watch out: Habibi's *unified*, SAU and UAE checkpoints are CC-BY-NC-SA. Use EGY or MSA only. |
| **3. Quickest paste → download today** | HF Space **chenxie95/Habibi-TTS** (ZeroGPU, choose dialect, download wav). Or **ResembleAI/Chatterbox-Multilingual-TTS-V3** (language = Arabic). Or **silma-ai/silma-tts-v1-demo**. Hosted: **Azure Speech Studio → Audio Content Creation** (ar-EG-SalmaNeural / ShakirNeural, export mp3, 0.5M chars/month free). | No install. A Space gives a wav, which you convert to mp3 or opus with ffmpeg. |
| **4. Game pipeline** | Offline batch: `tools/voice_lines.py` (below) writes `public/audio/<enc>/<step>…-<lang>.mp3` plus `public/audio/manifest.json`. `Voice.speak()` looks up the manifest first, then falls back to the current system-voice / Piper path. | Pre-rendered files give no 63 MB Piper download for voiced lines and the same voice on every device. The Piper fallback still covers any line that hasn't been recorded yet. |

Avoid for this (commercial) project: **facebook/mms-tts-ara** (CC-BY-NC 4.0), **Coqui XTTS-v2**
and its Egyptian fine-tune **EGTTS-V0.1** (CPML, which is non-commercial and covers *outputs* too),
**Fish Audio S2 Pro / OpenAudio S1-mini** (research / non-commercial licence),
**IbrahimSalah Arabic-F5-TTS-v2 / Arabic-TTS-Spark** (non-commercial, and they need full tashkeel),
and **MAdel121/f5-tts-egyptian-arabic** (CC-BY-NC, research-stage, UTMOS 2.63).
**Kokoro, CosyVoice 3 and Qwen3-TTS do not support Arabic.**

---

## Option-by-option (verified on model cards / repos)

### Already in the game: Piper (in-browser)
- Arabic voices: only **ar_JO-kareem** (`low` and `medium`), single male speaker, 22.05 kHz. It is a
  fine-tune of the English `lessac` voice on the arabicttstrain dataset. Voice licence is listed as MIT.
  https://huggingface.co/rhasspy/piper-voices/tree/main/ar ·
  https://huggingface.co/rhasspy/piper-voices/blob/main/ar/ar_JO/kareem/medium/MODEL_CARD
- Quality: intelligible but flat, and there is only one (male) voice, so grandma cannot be told apart
  from grandpa. The espeak-based phonemisation guesses short vowels. Undiacritised text gets wrong
  vowels, so adding tashkeel (CATT, below) helps noticeably.
- English: many voices, e.g. `en_US-lessac-high`, `en_GB-cori-high`, and multi-speaker
  `en_US-libritts_r-medium` (904 speakers) and `en_GB-vctk-medium` (109 speakers).
  https://huggingface.co/rhasspy/piper-voices/blob/main/voices.json
- Runs in the browser (onnxruntime-web) and on CPU. Keep it as the **fallback**, not the main voice.

### facebook/mms-tts-ara (VITS, Meta MMS)
- **CC-BY-NC 4.0, so no commercial use.** One generic voice. https://huggingface.co/facebook/mms-tts-ara
- Runs in transformers.js (browser) and on CPU, but the licence rules it out for a product.

### Coqui XTTS-v2 and EGTTS-V0.1 (Egyptian fine-tune)
- 17 languages including Arabic, 6 s voice cloning. **Licence is CPML**: "non-commercial purposes …
  only so far as you do not receive any direct or indirect payment arising from the use of the model
  or its output". Coqui shut down, so no commercial licence can be bought.
  https://huggingface.co/coqui/XTTS-v2 · https://huggingface.co/coqui/XTTS-v2/blob/main/LICENSE.txt
- EGTTS-V0.1 (Egyptian) inherits the CPML. https://huggingface.co/OmarSamir/EGTTS-V0.1

### Habibi-TTS (SWivid, the F5-TTS authors, Jan 2026): **top open pick**
- Unified-dialect Arabic TTS: MSA, EGY, SAU, UAE, ALG, IRQ, MAR (+ OMN, TUN, LEV, SDN, LBY ids).
  **Needs no diacritisation.** The paper reports it outperforms ElevenLabs Eleven v3 (alpha) on
  all six major dialect test sets. https://arxiv.org/html/2601.13802v1
- **Licence:** code MIT. Weights: the *unified*, SAU and UAE models are **CC-BY-NC-SA-4.0**.
  **EGY, MSA, ALG, IRQ and MAR are Apache-2.0** (commercial OK).
  https://huggingface.co/SWivid/Habibi-TTS · https://github.com/SWivid/Habibi-TTS
- Zero-shot cloning: needs a reference clip plus its transcript. Dialect samples ship in the package.
  `pip install habibi-tts`, then `habibi-tts_infer-gradio` (local web UI) or
  `habibi-tts_infer-cli --ref_audio ref.wav --ref_text "…" --gen_text "…"`.
- Size and speed: F5-TTS base (~0.3B params). Comfortable on a 6–8 GB laptop RTX. CPU works but slowly.
  Not browser-friendly.
- Free demo Space (ZeroGPU): https://huggingface.co/spaces/chenxie95/Habibi-TTS
- English: this is an Arabic model. Use Kokoro or Chatterbox for the English track.

### SILMA TTS v1 (silma-ai)
- **Apache-2.0** weights, MIT code. 150M params, F5-TTS architecture pretrained from scratch.
  **Arabic (MSA) + English** with code-switching. Accepts text **with or without tashkeel**. Voice
  cloning from under 8 s of reference audio. RTF ~0.12 on an RTX 4090.
  `pip install silma-tts`; `SilmaTTS().infer(ref_file=…, gen_text=…)`.
  https://huggingface.co/silma-ai/silma-tts · https://silma.ai/open-source-arabic-tts-models
- Demo Space (needs your own reference clip plus transcript): https://huggingface.co/spaces/silma-ai/silma-tts-v1-demo
- Side-by-side listening test of open Arabic models: https://huggingface.co/spaces/silma-ai/opensource-arabic-tts-benchmark
- MSA only, no Egyptian dialect. It is the lightest good option and a single model covers both languages.

### Chatterbox Multilingual (Resemble AI) and Egyptian fine-tunes
- **MIT.** Multilingual V3, 500M params, 23 languages **including Arabic (`ar`)**, zero-shot cloning,
  "exaggeration" (emotion) control. Every output carries an imperceptible **Perth watermark** (harmless
  for a game). `pip install chatterbox-tts`.
  https://huggingface.co/ResembleAI/chatterbox · https://github.com/resemble-ai/chatterbox
- Demo Space: https://huggingface.co/spaces/ResembleAI/Chatterbox-Multilingual-TTS-V3
- Egyptian fine-tunes:
  - **NAMAA-Space/NAMAA-Egyptian-TTS**: MIT, 0.5B, conversational Egyptian. Known issues: sometimes
    mispronounces ق, numbers are inconsistent. https://huggingface.co/NAMAA-Space/NAMAA-Egyptian-TTS
  - **oddadmix/chatterbox-egyptian-v0**: MIT. The reference accent can override the dialect.
    https://huggingface.co/oddadmix/chatterbox-egyptian-v0
  - **AliAbdallah/egyptian-arabic-tts-chatterbox**: Apache-2.0, 120 h single speaker, partial
    epoch. https://huggingface.co/AliAbdallah/egyptian-arabic-tts-chatterbox
- The English quality of base Chatterbox is very good, which makes it a sensible one-engine choice for both languages.

### F5-TTS Arabic community fine-tunes
- **IbrahimSalah/Arabic-F5-TTS-v2** and **IbrahimSalah/Arabic-TTS-Spark** (Spark-TTS): **non-commercial**,
  MSA only, and they **require full tashkeel**. https://huggingface.co/IbrahimSalah/Arabic-F5-TTS-v2 ·
  https://huggingface.co/IbrahimSalah/Arabic-TTS-Spark
- **MAdel121/f5-tts-egyptian-arabic**: CC-BY-NC, stopped at 5k/22k steps, UTMOS 2.63.
  https://huggingface.co/MAdel121/f5-tts-egyptian-arabic
- Superseded by Habibi-TTS.

### Fish Speech / OpenAudio / Fish Audio S2 Pro
- The current open model is S2 Pro (4B params). Arabic is "tier 2". Licence is the **Fish Audio Research
  License** (non-commercial without a separate deal). OpenAudio S1-mini is CC-BY-NC-SA.
  https://github.com/fishaudio/fish-speech · https://huggingface.co/fishaudio/openaudio-s1-mini/discussions/7
- 4B is also too heavy for a laptop GPU. **Skip.**

### Kokoro-82M
- **Apache-2.0**, 82M, excellent English (`af_heart` A, `af_bella` A-). Male voices are weaker (`am_michael`,
  `am_puck` C+). **No Arabic.** It runs on CPU and in the browser (kokoro-js / transformers.js).
  https://huggingface.co/hexgrad/Kokoro-82M · https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
- A good free English track for grandma and the narrator voices. For grandpa and uncle, Chatterbox or
  Piper `en_GB-*` male voices sound older and warmer.

### CosyVoice 3 / Spark-TTS / Qwen3-TTS
- Fun-CosyVoice3-0.5B: Apache-2.0 but **no Arabic** (9 languages).
  https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B-2512
- Qwen3-TTS: Apache-2.0, **no Arabic** (10 languages). https://github.com/QwenLM/Qwen3-TTS
- Spark-TTS: Arabic only via the non-commercial fine-tune above.

---

## Arabic diacritisation (tashkeel)

Needed for Piper ar_JO (strongly recommended) and for the IbrahimSalah models (required). Habibi,
SILMA and Chatterbox do not need it, though tashkeel on ambiguous words still helps. Hand-diacritise
names and key words anyway: أبرهة, عبد المطّلب, قريش.
- **CATT** (Abjad AI): **Apache-2.0** (moved from CC-BY-NC). `pip install catt-tashkeel`.
  Encoder-only is fast and encoder-decoder is more accurate. Exports to ONNX. **Recommended.** https://github.com/abjadai/catt
- **Mishkal**: rule-based, **GPL-3.0** (fine as an offline tool, don't bundle it). `pip install mishkal`.
  https://github.com/linuxscout/mishkal
- **Shakkala**: older Keras model. https://pypi.org/project/shakkala/
- **Sadeed** (2025, small LM diacritiser): https://arxiv.org/abs/2504.21635
- Tip: tashkeel tools target MSA and will "correct" Egyptian words. Run them only on the Arabic sent to
  Piper, and let the script accept a hand-fixed `ar_tts` override per line.

---

## Hosted APIs (for comparison, 2026 list prices)

| Service | Arabic voices | Price | Notes |
|---|---|---|---|
| **Azure AI Speech** | **ar-EG-SalmaNeural (F), ar-EG-ShakirNeural (M)**, ar-SA, other ar-* locales | $16 / 1M chars neural, $22 / 1M HD. **0.5M chars/month free** | Best Egyptian choice among the big clouds. The Speech Studio "Audio Content Creation" editor exports mp3. The whole game (about 34k chars for both languages) fits many times over inside the free tier. https://texttolab.com/blog/azure-text-to-speech-pricing |
| **Google Cloud TTS** | ar-XA (MSA), incl. Chirp 3 HD | Standard/WaveNet $4 / 1M, Neural2 $16 / 1M, Chirp 3 HD $30 / 1M. Free: 4M std, 1M Chirp 3 HD/month | No Egyptian locale. https://texttolab.com/blog/google-cloud-tts-pricing · https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd |
| **ElevenLabs** | Arabic in Multilingual v2 / v3, large voice library, cloning | Free 10k credits (no commercial use). **Starter $5/mo: 30k credits, commercial**. Creator $22/mo: 100k | Most expressive. The game's ~34k chars fit in one Creator month, including retakes. https://bigvu.tv/blog/elevenlabs-pricing-2026-plans-credits-commercial-rights-api-costs/ |
| **OpenAI** | Speaks Arabic with a noticeable foreign accent | tts-1 $15 / 1M, tts-1-hd $30 / 1M, gpt-4o-mini-tts ≈ $0.015/min | Good English, weakest Arabic of the four. https://costgoat.com/pricing/openai-tts |
| edge-tts (unofficial) | same ar-EG Salma/Shakir voices | free | Scrapes the Edge "Read aloud" endpoint. Not a licensed API, so fine for prototyping and not for release. https://github.com/rany2/edge-tts |

---

## Hardware notes (Lenovo LOQ, Linux, NVIDIA)

LOQ models ship with an RTX 3050 6 GB, 4050 6 GB, 4060 8 GB or 4070 8 GB. Check with `nvidia-smi`.
- Habibi / SILMA (F5-TTS class, ~0.15–0.3B): ~2–4 GB VRAM. Several seconds of audio per second. A few
  hundred lines take minutes.
- Chatterbox Multilingual (0.5B): ~4–6 GB in fp32. Fine on 6–8 GB. Close the game/Blender while it runs.
- Kokoro: CPU is enough.
- Fish S2 Pro (4B): does not fit. Skip.
- Setup: the NVIDIA proprietary driver plus a PyTorch CUDA wheel (`pip install torch --index-url
  https://download.pytorch.org/whl/cu124`), `ffmpeg` from the distro. Use a separate venv per engine,
  because Chatterbox and F5/Habibi pin different torch/transformers versions.

## Voices per character (cloning ethics and licence)

Cloning models need a 6–15 s clean reference clip plus its transcript for each character. Use only
voices you have rights to: record family or friends or hire a voice actor (a grandmother, a grandfather,
an uncle, and a boy with parental consent). Or use the sample voices shipped with the model (check
their licence). Never clone a real public figure or reciter. Record the reference in the target
language and register (Egyptian-flavoured MSA), because the accent of the reference carries over.
Suggested mapping:

| speaker id | character | Arabic reference | English voice |
|---|---|---|---|
| `grandma` | Grandma Zainab | older female, warm | Kokoro `af_heart` / cloned |
| `amina` | Grandma Amina | different older female | Kokoro `bf_emma` / cloned |
| `farmer` | Grandpa Salim | older male, slow | Chatterbox cloned / Piper `en_GB-alan` |
| `hamdan` | Uncle Hamdan | middle-aged male, lively | Chatterbox cloned / Kokoro `am_michael` |
| `player` | the boy | child (with consent) or higher-pitched young female | Kokoro `af_sky` style young voice |

---

## Pipeline for the game

### Files
```
public/audio/manifest.json                    { "ar|<exact line text>": "people-of-the-elephant/03-ar.mp3", … }
public/audio/<encounter-id>/<NN>[-oK][-rJ|-hint|-praise]-<lang>.mp3
tools/voices/<speaker>-<lang>.wav + .txt      reference clip + its transcript (for cloning engines)
```
Keying the manifest by the **exact text** means `Voice.speak(text, lang)` needs no step ids. An
edited line misses the manifest and falls back to live TTS until you re-run the script. Nothing
plays the wrong audio.

Format: mono **MP3 48 kbps** plays everywhere, including iOS Safari (~6 KB/s, so 418 lines of about 5 s each is
roughly 12 MB). If size matters more than old-Safari support, use
`--format opus` (Ogg Opus 24 kbps, about half the size).

### `tools/voice_lines.py`
```python
#!/usr/bin/env python3
"""Pre-render dialogue voice lines (never Quran) from public/data/encounters.json.

  python tools/voice_lines.py --engine habibi  --lang ar          # Arabic, Habibi EGY/MSA (Apache-2.0 ckpts only)
  python tools/voice_lines.py --engine chatterbox --lang ar,en    # MIT, one engine for both
  python tools/voice_lines.py --engine kokoro --lang en           # English on CPU
  python tools/voice_lines.py --engine azure --lang ar,en         # hosted (AZURE_SPEECH_KEY, AZURE_SPEECH_REGION)
  add --only people-of-the-elephant, --force, --dry-run, --format opus
Existing files are skipped unless --force; the manifest is rewritten each run.
"""
import argparse, json, os, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public/data/encounters.json'
OUT = ROOT / 'public/audio'
VOICES = ROOT / 'tools/voices'           # <speaker>-<lang>.wav + <speaker>-<lang>.txt (transcript)
NAME2ID = {'Uncle Hamdan': 'hamdan', 'Grandma Amina': 'amina', 'Grandma Zainab': 'grandma', 'Grandpa Salim': 'farmer'}

# hosted / preset voices per speaker (used by azure and kokoro; cloning engines use VOICES/)
AZURE = {'ar': {'grandma': 'ar-EG-SalmaNeural', 'amina': 'ar-SA-ZariyahNeural', 'farmer': 'ar-EG-ShakirNeural',
                'hamdan': 'ar-SA-HamedNeural', 'player': 'ar-EG-SalmaNeural'},
         'en': {'grandma': 'en-GB-SoniaNeural', 'amina': 'en-US-JaneNeural', 'farmer': 'en-GB-RyanNeural',
                'hamdan': 'en-US-GuyNeural', 'player': 'en-US-AnaNeural'}}
AZURE_STYLE = {'player': {'pitch': '+15%'}, 'farmer': {'rate': '-8%', 'pitch': '-6%'}, 'grandma': {'rate': '-5%'}}
KOKORO = {'grandma': 'af_heart', 'amina': 'bf_emma', 'farmer': 'bm_george', 'hamdan': 'am_michael', 'player': 'af_sky'}

def speak_text(text, lang):   # same substitution the game does before speaking
    return text.replace('ﷺ', 'صلى الله عليه وسلم' if lang == 'ar' else 'peace be upon him')

def lines(enc, langs):
    """Yield (relative file stem, speaker, lang, exact text) for every spoken dialogue line."""
    host = enc.get('host') or NAME2ID.get(enc.get('character', {}).get('name', {}).get('en'), 'narrator')
    for i, s in enumerate(enc['steps']):
        if s['type'] in ('verses', 'reward'):       # Quran comes from Quran.com; reward has no line
            continue
        spk = s.get('speaker') or host
        base = f"{enc['id']}/{i:02d}"
        for lang in langs:
            asking = s['type'] == 'choice' and spk == 'player'
            if s.get(lang) and not asking:           # the child's "Ask:" prompt is shown, not spoken
                yield base, spk, lang, s[lang], s.get(f'{lang}_tts')
            for k, o in enumerate(s.get('options', [])):
                if asking and o.get(lang):
                    yield f'{base}-o{k}', 'player', lang, o[lang], o.get(f'{lang}_tts')
                reps = o.get('reply') or []
                for j, r in enumerate(reps if isinstance(reps, list) else [reps]):
                    if r.get(lang):
                        yield f'{base}-o{k}-r{j}', r.get('speaker') or (host if asking else spk), lang, r[lang], r.get(f'{lang}_tts')
            for part in ('hint', 'praise'):
                if isinstance(s.get(part), dict) and s[part].get(lang):
                    yield f'{base}-{part}', spk, lang, s[part][lang], s[part].get(f'{lang}_tts')

# ---------- engines: each returns a function (text, speaker, lang, wav_path) -> None ----------
def ref(speaker, lang):
    wav = VOICES / f'{speaker}-{lang}.wav'
    if not wav.exists(): wav = VOICES / f'{speaker}-ar.wav'   # cross-lingual clone if no English ref
    txt = wav.with_suffix('.txt')
    return str(wav), (txt.read_text(encoding='utf-8').strip() if txt.exists() else '')

def engine_chatterbox():
    import torch, torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    m = ChatterboxMultilingualTTS.from_pretrained(device='cuda' if torch.cuda.is_available() else 'cpu')
    def run(text, spk, lang, wav):
        w = m.generate(text, language_id=lang, audio_prompt_path=ref(spk, lang)[0],
                       exaggeration=0.6 if spk == 'player' else 0.5, cfg_weight=0.4)
        torchaudio.save(wav, w, m.sr)
    return run

def engine_habibi():
    # Uses the CLI so we don't depend on internal APIs; pass --model with an EGY or MSA (Apache-2.0)
    # checkpoint (check `habibi-tts_infer-cli --help` for the exact flag names of your version).
    def run(text, spk, lang, wav):
        if lang != 'ar': raise SystemExit('habibi is Arabic-only; use --engine kokoro/chatterbox for en')
        r_wav, r_txt = ref(spk, 'ar')
        out = Path(wav)
        subprocess.run(['habibi-tts_infer-cli', '--ref_audio', r_wav, '--ref_text', r_txt,
                        '--gen_text', text, '--output_dir', str(out.parent), '--output_file', out.name],
                       check=True)
    return run

def engine_kokoro():
    import numpy as np, soundfile as sf
    from kokoro import KPipeline
    pipes = {}
    def run(text, spk, lang, wav):
        v = KOKORO.get(spk, 'af_heart'); code = v[0]           # 'a' US, 'b' GB
        p = pipes.setdefault(code, KPipeline(lang_code=code))
        sf.write(wav, np.concatenate([a for _, _, a in p(text, voice=v, speed=0.95)]), 24000)
    return run

def engine_azure():
    import azure.cognitiveservices.speech as sdk
    from xml.sax.saxutils import escape
    cfg = sdk.SpeechConfig(subscription=os.environ['AZURE_SPEECH_KEY'], region=os.environ['AZURE_SPEECH_REGION'])
    cfg.set_speech_synthesis_output_format(sdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)
    def run(text, spk, lang, wav):
        voice = AZURE[lang].get(spk, AZURE[lang]['grandma']); st = AZURE_STYLE.get(spk, {})
        prosody = ' '.join(f'{k}="{v}"' for k, v in st.items())
        ssml = (f'<speak version="1.0" xml:lang="{voice[:5]}"><voice name="{voice}">'
                f'<prosody {prosody}>{escape(text)}</prosody></voice></speak>')
        synth = sdk.SpeechSynthesizer(cfg, sdk.audio.AudioOutputConfig(filename=wav))
        r = synth.speak_ssml_async(ssml).get()
        if r.reason != sdk.ResultReason.SynthesizingAudioCompleted: raise RuntimeError(r.cancellation_details.error_details)
    return run

ENGINES = {'chatterbox': engine_chatterbox, 'habibi': engine_habibi, 'kokoro': engine_kokoro, 'azure': engine_azure}

def encode(wav, dst, fmt):
    args = ['-c:a', 'libmp3lame', '-b:a', '48k'] if fmt == 'mp3' else ['-c:a', 'libopus', '-b:a', '24k']
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, '-ac', '1', '-af',
                    'silenceremove=start_periods=1:start_threshold=-50dB,areverse,'
                    'silenceremove=start_periods=1:start_threshold=-50dB,areverse,loudnorm=I=-18:TP=-2',
                    *args, str(dst)], check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--engine', choices=ENGINES, required=True)
    ap.add_argument('--lang', default='ar,en'); ap.add_argument('--only')
    ap.add_argument('--format', choices=['mp3', 'opus'], default='mp3')
    ap.add_argument('--force', action='store_true'); ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(); langs = a.lang.split(','); ext = 'mp3' if a.format == 'mp3' else 'ogg'
    data = json.loads(DATA.read_text(encoding='utf-8'))
    mpath = OUT / 'manifest.json'
    manifest = json.loads(mpath.read_text(encoding='utf-8')) if mpath.exists() else {}
    todo = []
    for enc in data['encounters']:
        if a.only and enc['id'] != a.only: continue
        for stem, spk, lang, text, override in lines(enc, langs):
            rel = f'{stem}-{lang}.{ext}'
            manifest[f'{lang}|{text}'] = rel                       # key = exact text the game passes to Voice.speak
            if a.force or not (OUT / rel).exists(): todo.append((rel, spk, lang, override or speak_text(text, lang)))
    print(f'{len(todo)} lines to render', file=sys.stderr)
    if a.dry_run:
        for t in todo: print(*t, sep='\t')
        return
    run = ENGINES[a.engine]() if todo else None
    with tempfile.TemporaryDirectory() as tmp:
        for n, (rel, spk, lang, text) in enumerate(todo, 1):
            dst = OUT / rel; dst.parent.mkdir(parents=True, exist_ok=True)
            wav = os.path.join(tmp, 'line.wav')
            print(f'[{n}/{len(todo)}] {spk:8} {rel}', file=sys.stderr)
            run(text, spk, lang, wav); encode(wav, dst, a.format)
    OUT.mkdir(parents=True, exist_ok=True)
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=0), encoding='utf-8')

if __name__ == '__main__':
    main()
```
Notes:
- An optional `ar_tts` / `en_tts` field on any step, option, reply, hint or praise lets you hand-fix
  pronunciation (tashkeel, spelled-out names) without changing the on-screen text.
- Mix engines per language: e.g. `--engine habibi --lang ar`, then `--engine kokoro --lang en`. The
  manifest merges both runs.
- Voice names in `AZURE` were current Azure voices as of this writing. List them with the Speech SDK /
  REST "list voices" call before relying on them. `en-US-AnaNeural` is Azure's child voice.
- Listen to every file before release, especially religious terms and names. Keep the teacher
  review that `_note` already asks for.
- Requirements by engine: `pip install chatterbox-tts` | `pip install habibi-tts` | `pip install kokoro
  soundfile` (+ `espeak-ng` system package) | `pip install azure-cognitiveservices-speech`. Plus `ffmpeg`.

### Game side: `src/game/systems/audio.js`
Add a manifest lookup at the top of `Voice.speak`. Everything after it (system voice, then Piper) stays
the fallback:
```js
let voiceFiles = null;                                   // "lang|text" -> "enc/NN-lang.mp3"
fetch(`${import.meta.env.BASE_URL}audio/manifest.json`).then(r => r.ok ? r.json() : {})
  .then(m => { voiceFiles = m; }).catch(() => { voiceFiles = {}; });

// inside Voice.speak(text, lang), right after `if (!this.enabled) return;`
const file = voiceFiles?.[`${lang}|${text}`];
if (file) {
  const my = ++token;
  voiceAudio.src = `${import.meta.env.BASE_URL}audio/${file}`; voiceAudio.playbackRate = 1;
  try { await voiceAudio.play(); return; }               // recorded line: done
  catch (e) { if (my !== token) return; }                // autoplay block / 404: fall through to live TTS
}
```
Also make `Voice.prepare('ar')` skip the 63 MB Piper download when the manifest covers every line
(check `Object.keys(voiceFiles).some(k => k.startsWith('ar|'))`). Then Linux players only download
Piper for lines that aren't voiced yet. `cancel()` already pauses `voiceAudio`, so skipping a line
still cuts the audio. Recitation uses its own element, so voice lines and recitation never overlap.

---

## Sources
- Habibi paper: https://arxiv.org/html/2601.13802v1 · weights/licence: https://huggingface.co/SWivid/Habibi-TTS · code: https://github.com/SWivid/Habibi-TTS · demo: https://huggingface.co/spaces/chenxie95/Habibi-TTS
- SILMA TTS: https://huggingface.co/silma-ai/silma-tts · https://silma.ai/open-source-arabic-tts-models · https://huggingface.co/spaces/silma-ai/silma-tts-v1-demo · benchmark: https://huggingface.co/spaces/silma-ai/opensource-arabic-tts-benchmark
- Chatterbox: https://huggingface.co/ResembleAI/chatterbox · https://github.com/resemble-ai/chatterbox · https://huggingface.co/spaces/ResembleAI/Chatterbox-Multilingual-TTS-V3
- Egyptian fine-tunes: https://huggingface.co/NAMAA-Space/NAMAA-Egyptian-TTS · https://huggingface.co/oddadmix/chatterbox-egyptian-v0 · https://huggingface.co/AliAbdallah/egyptian-arabic-tts-chatterbox · https://huggingface.co/MAdel121/f5-tts-egyptian-arabic · https://huggingface.co/OmarSamir/EGTTS-V0.1
- Piper: https://huggingface.co/rhasspy/piper-voices/tree/main/ar · https://huggingface.co/rhasspy/piper-voices/blob/main/voices.json
- MMS: https://huggingface.co/facebook/mms-tts-ara
- XTTS-v2 / CPML: https://huggingface.co/coqui/XTTS-v2 · https://huggingface.co/coqui/XTTS-v2/blob/main/LICENSE.txt
- IbrahimSalah fine-tunes: https://huggingface.co/IbrahimSalah/Arabic-F5-TTS-v2 · https://huggingface.co/IbrahimSalah/Arabic-TTS-Spark
- Fish: https://github.com/fishaudio/fish-speech · https://huggingface.co/fishaudio/openaudio-s1-mini/discussions/7
- Kokoro: https://huggingface.co/hexgrad/Kokoro-82M · https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
- CosyVoice 3: https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B-2512 · Qwen3-TTS: https://github.com/QwenLM/Qwen3-TTS
- Diacritisation: https://github.com/abjadai/catt · https://github.com/linuxscout/mishkal · https://pypi.org/project/shakkala/ · https://arxiv.org/abs/2504.21635
- Pricing: https://texttolab.com/blog/azure-text-to-speech-pricing · https://texttolab.com/blog/google-cloud-tts-pricing · https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd · https://bigvu.tv/blog/elevenlabs-pricing-2026-plans-credits-commercial-rights-api-costs/ · https://costgoat.com/pricing/openai-tts · edge-tts: https://github.com/rany2/edge-tts
