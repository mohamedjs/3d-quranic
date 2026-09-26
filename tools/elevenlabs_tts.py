#!/usr/bin/env python3
"""Voice every Arabic dialogue line with ElevenLabs (plain REST, no SDK).
   Setup: in the project's .env
       ELEVENLABS_API_KEY=sk_...          (elevenlabs.io → Profile → API keys)
   Voices per character: tools/voices_elevenlabs.json (voice IDs from elevenlabs.io → Voices;
   pick Arabic / Egyptian voices from the Voice Library, "Add to my voices", copy the ID).
   Run:   python3 tools/elevenlabs_tts.py --dry     (count characters = credits, no calls)
          python3 tools/elevenlabs_tts.py           (only lines not voiced yet)
          python3 tools/elevenlabs_tts.py --all     (re-voice everything)
   → public/audio/<encounter>/<speaker>-<hash>.mp3 + public/audio/manifest.json"""
import json, os, sys, time, urllib.request, urllib.error
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = {}
if os.path.exists(os.path.join(ROOT, '.env')):
    for l in open(os.path.join(ROOT, '.env')):
        if '=' in l and not l.lstrip().startswith('#'):
            k, v = l.strip().split('=', 1); env[k.strip()] = v.strip()
KEY = os.environ.get('ELEVENLABS_API_KEY') or env.get('ELEVENLABS_API_KEY')
cfg = json.load(open(os.path.join(ROOT, 'tools/voices_elevenlabs.json')))
lines = json.load(open(os.path.join(ROOT, 'tools/voice_lines.json')))
mpath = os.path.join(ROOT, 'public/audio/manifest.json')
manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
done_ids = set(manifest.get('_elevenlabs', []))
SKIP = set(a.split('=',1)[1] for a in sys.argv if a.startswith('--skip=')) if any(a.startswith('--skip=') for a in sys.argv) else set()
todo = [L for L in lines if '--all' in sys.argv or L['id'] not in done_ids]
chars = sum(len(L['text']) for L in todo)
print(f'{len(todo)} lines, {chars} characters (≈ credits on multilingual v2; v3 / flash differ)')
if '--dry' in sys.argv: sys.exit()
if not KEY: sys.exit('Put ELEVENLABS_API_KEY in .env')
for i, L in enumerate(todo):
    v = cfg['voices'][L['speaker']]
    if not v.get('voice_id') or v['voice_id'].startswith('PUT_') or L['speaker'] in SKIP:
        continue                                                      # voice not chosen yet → keep the fallback TTS
    body = json.dumps({'text': L['text'].replace('ﷺ', 'صلى الله عليه وسلم'), 'model_id': cfg.get('model_id', 'eleven_multilingual_v2'),
                       'language_code': 'ar', 'voice_settings': v.get('settings', {'stability': 0.5, 'similarity_boost': 0.75})}).encode()
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{v['voice_id']}?output_format=mp3_44100_64",
                                 data=body, method='POST', headers={'xi-api-key': KEY, 'Content-Type': 'application/json', 'Accept': 'audio/mpeg'})
    for attempt in range(4):
        try: data = urllib.request.urlopen(req, timeout=60).read(); break
        except urllib.error.HTTPError as e:
            msg = e.read()[:300]
            if e.code == 429 and attempt < 3: time.sleep(5 * (attempt + 1)); continue
            json.dump(manifest, open(mpath, 'w'), ensure_ascii=False, indent=0)
            sys.exit(f'ElevenLabs error {e.code}: {msg!r}  (progress saved — rerun to continue)')
    rel = 'audio/' + L['id'] + '.mp3'; out = os.path.join(ROOT, 'public', rel)
    os.makedirs(os.path.dirname(out), exist_ok=True); open(out, 'wb').write(data)
    manifest[L['text']] = rel; done_ids.add(L['id']); manifest['_elevenlabs'] = sorted(done_ids)
    if i % 10 == 0: json.dump(manifest, open(mpath, 'w'), ensure_ascii=False, indent=0)
    print(f'{i + 1}/{len(todo)} {L["speaker"]:7s} {len(data) // 1024} KB  {L["text"][:50]}')
json.dump(manifest, open(mpath, 'w'), ensure_ascii=False, indent=0)
print('done')
