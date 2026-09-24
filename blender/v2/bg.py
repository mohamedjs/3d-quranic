#!/usr/bin/env python3
"""Run a script in a separate BACKGROUND Blender process on the host (parallel-safe).
   python3 v2/bg.py script.py [name]   → starts it, prints the log path, returns at once.
   The GUI Blender (with bridge.py running) only launches the process.
   Log: blender/v2/_jobs/<name>.log ; the script ends by printing 'BG_DONE' (added automatically)."""
import sys, os, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__))
script = os.path.abspath(sys.argv[1]); name = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(script)[:-3]
HOST = '/var/www/html/old/3d-quranic/blender/v2/'
rel = os.path.relpath(script, HERE); host_script = HOST + rel
wrap = os.path.join(HERE, '_jobs', name + '_wrap.py'); log = HOST + '_jobs/' + name + '.log'
open(wrap, 'w').write(f"""import sys, traceback, runpy
try:
    runpy.run_path({host_script!r}, run_name='__main__')
    print('BG_DONE ok', flush=True)
except SystemExit: print('BG_DONE ok', flush=True)
except Exception:
    traceback.print_exc(); print('BG_DONE error', flush=True)
""")
job = f"""import subprocess, bpy
lf = open({log!r}, 'w')
p = subprocess.Popen([bpy.app.binary_path, '-b', '--python', {HOST + '_jobs/' + name + '_wrap.py'!r}], stdout=lf, stderr=subprocess.STDOUT)
print('pid', p.pid)
"""
p = subprocess.run(['python3', os.path.join(HERE, '..', '_bridge', 'bx.py'), '-', '60'], input=job, text=True, capture_output=True)
print(p.stdout.strip()); print('log:', os.path.join(HERE, '_jobs', name + '.log'))
