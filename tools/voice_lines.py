#!/usr/bin/env python3
"""Collect every Arabic dialogue line the game speaks (Voice.speak) with its speaker.
   → tools/voice_lines.json  [{id, enc, speaker, text}]   (deduplicated by speaker+text)"""
import json, hashlib, os, re, sys
L = sys.argv[1] if len(sys.argv) > 1 else "ar"   # ar | en | ru
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data = json.load(open(os.path.join(ROOT, 'public/data/encounters.json')))

def speaker_ids(enc):
    cs = enc.get('characters') or [enc.get('character')]
    host = enc.get('host') or cs[0].get('id')
    if not host:   # single-character stories without ids: name the voice from the character
        n = cs[0]['name']['en'].lower()
        host = 'hamdan' if 'hamdan' in n else 'amina' if 'amina' in n else 'farmer' if 'salim' in n else 'grandma'
    return host

def voice_key(sp):
    return {'grandma': 'zainab'}.get(sp, sp)

out, seen = [], set()
def add(enc, sp, text):
    if not text or not text.strip(): return
    k = (sp, text)
    if k in seen: return
    seen.add(k)
    h = hashlib.sha1(text.encode()).hexdigest()[:10]
    out.append({'id': (f"{L}/" if L != 'ar' else '') + f"{enc}/{voice_key(sp)}-{h}", 'enc': enc, 'speaker': voice_key(sp), 'text': text})

for e in data['encounters']:
    host = speaker_ids(e)
    for f in ('greeting', 'after'):
        if isinstance(e.get(f), dict): add(e['id'], host, e[f].get(L))
    for s in e['steps']:
        sp = s.get('speaker') or host
        if s['type'] in ('say',): add(e['id'], sp, s.get(L))
        if s['type'] in ('choice', 'question'):
            if sp != 'player': add(e['id'], sp, s.get(L))
            for o in s.get('options', []):
                if sp == 'player' or s['type'] == 'choice': add(e['id'], 'player', o.get(L))
                rep = o.get('reply') or []
                for r in (rep if isinstance(rep, list) else [rep]): add(e['id'], r.get('speaker') or host, r.get(L))
            for f in ('hint', 'praise', 'wrong', 'right'):
                v = s.get(f)
                if isinstance(v, dict): add(e['id'], sp if sp != 'player' else host, v.get(L))
for k in ('intro', 'next'):
    add('narrator', 'narrator', data.get('narrator', {}).get(k, {}).get(L))
for e in data['encounters']:
    add('narrator', 'narrator', e.get('narration', {}).get(L))
json.dump(out, open(os.path.join(ROOT, 'tools/voice_lines.json' if L == 'ar' else f'tools/voice_lines_{L}.json'), 'w'), ensure_ascii=False, indent=0)
from collections import Counter
print(len(out), Counter(x['speaker'] for x in out), sum(len(x['text']) for x in out), 'chars')
