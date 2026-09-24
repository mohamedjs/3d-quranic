# Claude <-> Blender file bridge.
# Run ONCE inside Blender (Scripting tab -> Open this file -> Run Script).
# Claude drops .py jobs in _bridge/in/, Blender runs them on the main thread
# and writes the result (stdout / error) to _bridge/out/<job>.json.
import bpy, os, io, json, time, traceback, contextlib

ROOT = '/var/www/html/old/3d-quranic/blender/_bridge'
IN, OUT = os.path.join(ROOT, 'in'), os.path.join(ROOT, 'out')
os.makedirs(IN, exist_ok=True); os.makedirs(OUT, exist_ok=True)

def viewport_shot(path, size=1200):
    """Save a screenshot of the biggest 3D viewport (helper available to jobs)."""
    for w in bpy.context.window_manager.windows:
        areas = [a for a in w.screen.areas if a.type == 'VIEW_3D']
        if not areas: continue
        a = max(areas, key=lambda a: a.width * a.height)
        with bpy.context.temp_override(window=w, area=a):
            bpy.ops.screen.screenshot_area(filepath=path)
        return path

def _tick():
    try:
        jobs = sorted(f for f in os.listdir(IN) if f.endswith('.py'))
    except Exception:
        return 1.0
    for f in jobs:
        p = os.path.join(IN, f)
        code = open(p, encoding='utf-8').read()
        os.remove(p)
        buf, t0 = io.StringIO(), time.time()
        res = {'job': f, 'status': 'success'}
        try:
            with contextlib.redirect_stdout(buf):
                exec(compile(code, f, 'exec'), {'__name__': '__bridge__', 'bpy': bpy, 'viewport_shot': viewport_shot})
        except Exception:
            res['status'] = 'error'; res['error'] = traceback.format_exc()
        res['stdout'] = buf.getvalue()[-20000:]
        res['seconds'] = round(time.time() - t0, 2)
        with open(os.path.join(OUT, f[:-3] + '.json'), 'w', encoding='utf-8') as o:
            json.dump(res, o, ensure_ascii=False)
    return 0.5

if bpy.app.timers.is_registered(_tick) if hasattr(bpy.app.timers, 'is_registered') else False:
    pass
bpy.app.timers.register(_tick, persistent=True)
with open(os.path.join(OUT, '_hello.json'), 'w') as o:
    json.dump({'status': 'bridge up', 'blender': bpy.app.version_string, 'file': bpy.data.filepath}, o)
print('Claude bridge running ->', ROOT)
