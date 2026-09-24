#!/usr/bin/env python3
"""Send a job to the running Blender bridge and wait for the result.
   python3 bx.py job.py [timeout_s]      (or '-' to read code from stdin)"""
import sys, os, time, json, uuid
ROOT = os.path.dirname(os.path.abspath(__file__))
src = sys.stdin.read() if sys.argv[1] == '-' else open(sys.argv[1]).read()
tmo = float(sys.argv[2]) if len(sys.argv) > 2 else 170
name = time.strftime('%H%M%S') + '_' + uuid.uuid4().hex[:6]
tmp = os.path.join(ROOT, 'in', name + '.tmp')
open(tmp, 'w').write(src); os.rename(tmp, tmp[:-4] + '.py')
out = os.path.join(ROOT, 'out', name + '.json'); t0 = time.time()
while not os.path.exists(out):
    if time.time() - t0 > tmo: print('TIMEOUT (job may still be running):', name); sys.exit(2)
    time.sleep(0.3)
time.sleep(0.1); r = json.load(open(out))
print(r.get('stdout', '')); print('status:', r['status'], r.get('seconds'), 's')
if r['status'] != 'success': print(r.get('error')); sys.exit(1)
