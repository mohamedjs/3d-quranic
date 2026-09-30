import subprocess, json, os
T = json.load(open(os.environ.get('TIMING', '/tmp/ad/timing.json'))); C = json.load(open(os.environ.get('CUES', '/tmp/ad/cues.json'))); total = T['total']
VO = [(T['files'][k], a) for k, (a, d) in T['vo'].items()]
SFX = [('whoosh', t) for t in C['whoosh']] + [('pop', t) for t in C['pop']] + [('chime', t) for t in C['coin']]
ins = []; fc = []; n = 0; vo = []; sf = []
for f, t in VO:
    ins += ['-i', f]; fc.append(f'[{n}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={int(t*1000)}|{int(t*1000)}[v{n}]'); vo.append(f'[v{n}]'); n += 1
for c in T.get('clips', []):
    ins += ['-i', c['file']]; a = c['at']
    fc.append(f"[{n}:a]atrim={c['from']}:{c['to']},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,afade=t=in:d=0.12,afade=t=out:st={c['to']-c['from']-0.35}:d=0.35,volume={c.get('vol', 1.6)},adelay={int(a*1000)}|{int(a*1000)}[v{n}]"); vo.append(f'[v{n}]'); n += 1
for name, t in SFX:
    ins += ['-i', f'/tmp/ad/audio/{name}.wav']; g = {'whoosh': 0.6, 'pop': 0.45, 'chime': 0.35}[name]
    fc.append(f'[{n}:a]aresample=48000,aformat=channel_layouts=stereo,volume={g},adelay={int(max(0,t)*1000)}|{int(max(0,t)*1000)}[s{n}]'); sf.append(f'[s{n}]'); n += 1
fc.append(''.join(vo) + f'amix=inputs={len(vo)}:normalize=0,loudnorm=I=-15:TP=-1.5:LRA=7,apad=whole_dur={total}[vo]')
fc.append(''.join(sf) + f'amix=inputs={len(sf)}:normalize=0,apad=whole_dur={total}[sfx]')
fc.append(f'[vo][sfx]amix=inputs=2:normalize=0,alimiter=limit=0.95,atrim=0:{total}[out]')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error'] + ins + ['-filter_complex', ';'.join(fc), '-map', '[out]', '-ar', '48000', os.environ.get('MIXOUT', '/tmp/ad/audio/mix.wav')], check=True)
print('mixed', total)
