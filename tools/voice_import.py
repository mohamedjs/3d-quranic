#!/usr/bin/env python3
"""Import generated voice clips into the game.
   python3 tools/voice_import.py <folder-with-wavs>
   Each wav is named like tools/voice_lines.json ids with '/' → '__' (e.g. people-of-the-elephant__farmer-1a2b3c4d5e.wav).
   → public/audio/<enc>/<speaker>-<hash>.mp3 (mono, 24 kHz, 48 kbps) + public/audio/manifest.json {text: path}"""
import json, os, sys, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = sys.argv[1]
lines = json.load(open(os.path.join(ROOT, 'tools/voice_lines.json')))
voices = json.load(open(os.path.join(ROOT, 'tools/voices.json')))
mpath = os.path.join(ROOT, 'public/audio/manifest.json')
manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
done = 0
for L in lines:
    base = os.path.join(src, L['id'].replace('/', '__'))
    wav = next((base + x for x in ('.wav', '.mp3') if os.path.exists(base + x)), None)
    if not wav: continue
    rel = 'audio/' + L['id'] + '.mp3'; out = os.path.join(ROOT, 'public', rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    post = voices.get(L['speaker'], {}).get('post') or 'anull'
    af = f"silenceremove=start_periods=1:start_threshold=-45dB,{post},areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,loudnorm=I=-18:TP=-2"
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-af', af, '-ac', '1', '-ar', '24000', '-b:a', '48k', out], check=True)
    manifest[L['text']] = rel; done += 1
json.dump(manifest, open(mpath, 'w'), ensure_ascii=False, indent=0)
print('imported', done, 'of', len(lines), '→ manifest entries', len(manifest))
