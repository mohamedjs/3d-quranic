#!/usr/bin/env python3
"""Scene timing from the voice clips → /tmp/ad/timing.json (read by render.py and mix.py)."""
import json, subprocess, sys
VO = json.load(open('/tmp/ad/vo_files.json'))          # key → file
dur = lambda f: float(subprocess.check_output(['ffprobe', '-v', '0', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]))
d = {k: dur(f) for k, f in VO.items()}
s, vo = {}, {}
t = 0.0
s['s1'] = t; vo['n1'] = [t + .7, d['n1']]; t = max(t + 3.8, vo['n1'][0] + d['n1'] + .5)
s['s2'] = t; vo['n2'] = [t + .45, d['n2']]; t = max(t + 6.0, vo['n2'][0] + d['n2'] + .6)
s['s3'] = t; vo['n3'] = [t + .35, d['n3']]; f = vo['n3'][0] + d['n3'] + .35; vo['farmer'] = [f, d['farmer']]
vo['player'] = [f + d['farmer'] + .35, d['player']]; t = vo['player'][0] + d['player'] + .6
for k, n in (('s4', 'n4'), ('s5', 'n5'), ('s6', 'n6')):
    s[k] = t; vo[n] = [t + .45, d[n]]; t = vo[n][0] + d[n] + .7
s['s7'] = t; vo['n7'] = [t + .6, d['n7']]; total = vo['n7'][0] + d['n7'] + 3.0
json.dump({'total': round(total, 2), 's': {k: round(v, 3) for k, v in s.items()}, 'vo': {k: [round(a, 3), round(b, 3)] for k, (a, b) in vo.items()}, 'files': VO},
          open('/tmp/ad/timing.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(s), 'total', round(total, 2))
