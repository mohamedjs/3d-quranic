#!/usr/bin/env python3
"""Scene timing from the voice clips → /tmp/ad/timing.json. Order follows the game:
   logo · pick a level · walk & collect (real) · villagers (real + cards) · categories · Quran · play."""
import json, subprocess
VO = json.load(open('/tmp/ad/vo_files.json'))
dur = lambda f: float(subprocess.check_output(['ffprobe', '-v', '0', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]))
d = {k: dur(f) for k, f in VO.items()}
WALK, HOUSE = 270 / 30, 248 / 30
s, vo = {}, {}
t = 0.0
s['s1'] = t; vo['n1'] = [t + .7, d['n1']]; t = max(t + 3.6, vo['n1'][0] + d['n1'] + .5)
s['s6'] = t; vo['n6'] = [t + .6, d['n6']]; t = vo['n6'][0] + d['n6'] + .8
s['s2'] = t; vo['n2'] = [t + .6, d['n2']]; t = max(t + .1 + WALK + .5, vo['n2'][0] + d['n2'] + .6)
s['s3'] = t; vo['n3'] = [t + .45, d['n3']]; s3B = t + .1 + HOUSE + .15
vo['farmer'] = [s3B + 1.4, d['farmer']]; vo['player'] = [vo['farmer'][0] + d['farmer'] + .35, d['player']]; t = vo['player'][0] + d['player'] + .6
for k, n in (('s4', 'n4'), ('s5', 'n5')):
    s[k] = t; vo[n] = [t + .45, d[n]]; t = vo[n][0] + d[n] + .7
s['s7'] = t; vo['n7'] = [t + 1.0, d['n7']]; total = vo['n7'][0] + d['n7'] + 3.0
# the grandma's own greeting from the recording (house clip 6.5 s → end)
clips = [{'file': '/tmp/ad/audio/clip_house.wav', 'from': 6.5, 'to': HOUSE, 'at': s['s3'] + .1 + 6.5}]
json.dump({'total': round(total, 2), 's3B': round(s3B, 3), 's': {k: round(v, 3) for k, v in s.items()}, 'vo': {k: [round(a, 3), round(b, 3)] for k, (a, b) in vo.items()}, 'files': VO, 'clips': clips},
          open('/tmp/ad/timing.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(s), 's3B', round(s3B, 2), 'total', round(total, 2))
