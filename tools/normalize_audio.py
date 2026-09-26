#!/usr/bin/env python3
"""Even out the loudness of voice clips WITHOUT loudnorm (single-pass loudnorm ruins clips < 3 s).
   Measures each clip's mean volume and applies a plain gain to TARGET dB with a peak limiter;
   the boy's lines (player-*) get atempo=0.75 when --slow-player is given (fresh generations only).
   python3 tools/normalize_audio.py [--ids ids.json] [--slow-player]"""
import glob, json, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = -19.0
def mean_db(data):
    r = subprocess.run(['ffmpeg', '-i', 'pipe:0', '-af', 'volumedetect', '-f', 'null', '-'], input=data, capture_output=True).stderr.decode()
    return float(re.search(r'mean_volume: (\S+) dB', r).group(1))
files = glob.glob(os.path.join(ROOT, 'public/audio/**/*.mp3'), recursive=True)
if '--ids' in sys.argv:
    ids = set(json.load(open(sys.argv[sys.argv.index('--ids') + 1])))
    files = [f for f in files if os.path.relpath(f, os.path.join(ROOT, 'public/audio'))[:-4] in ids]
for f in files:
    src = open(f, 'rb').read(); m = mean_db(src)
    slow = '--slow-player' in sys.argv and os.path.basename(f).startswith('player-')
    if not slow and abs(m - TARGET) < 2.5: continue
    af = (['atempo=0.75'] if slow else []) + [f'volume={TARGET - m:.1f}dB', 'alimiter=limit=0.89:level=false']
    out = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', 'pipe:0', '-af', ','.join(af), '-ac', '1', '-ar', '24000', '-b:a', '48k', '-f', 'mp3', 'pipe:1'], input=src, capture_output=True).stdout
    if len(out) > 500:
        open(f, 'wb').write(out); print(f'{m:6.1f} → {mean_db(out):6.1f} dB  {os.path.relpath(f, ROOT)}')
