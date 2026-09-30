"""build_audio.py <lang>  → /root/gv/pkg/<lang>/audio/... mp3 (trimmed, gain-normalised to -19 dB) + manifest_<lang>.json"""
import json, os, re, subprocess, sys
LG = sys.argv[1]; D = '/root/gv'
lines = json.load(open(f'{D}/voice_lines.json' if LG == 'ar' else f'{D}/voice_lines_{LG}.json'))
RAW = f'{D}/ar_habibi/raw' if LG == 'ar' else f'{D}/{LG}/raw'
qc = json.load(open(f'{RAW}/../qc.json'))
PK = f'{D}/pkg/{LG}'; man = {}; bad = []
def mean_db(f):
    r = subprocess.run(['ffmpeg', '-i', f, '-af', 'volumedetect', '-f', 'null', '-'], capture_output=True).stderr.decode()
    return float(re.search(r'mean_volume: (\S+) dB', r).group(1))
for L in lines:
    w = f"{RAW}/{L['id'].replace('/', '__')}.wav"
    if not os.path.exists(w): bad.append((L['id'], 'missing')); continue
    if qc.get(L['id'], {}).get('cer', 1) > 0.25: bad.append((L['id'], qc.get(L['id'])))
    rel = 'audio/' + L['id'] + '.mp3'; out = f'{PK}/{rel}'; os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + '.wav'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', w, '-af', 'silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,apad=pad_dur=0.12', '-ac', '1', '-ar', '24000', tmp], check=True)
    g = -19.0 - mean_db(tmp)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-af', f'volume={g:.1f}dB,alimiter=limit=0.89:level=false', '-b:a', '48k', out], check=True)
    os.remove(tmp); man[L['text']] = rel
json.dump(man, open(f'{D}/pkg/manifest_{LG}.json', 'w'), ensure_ascii=False, indent=0)
print(LG, 'files', len(man), 'flagged', len(bad)); print(bad[:40])
