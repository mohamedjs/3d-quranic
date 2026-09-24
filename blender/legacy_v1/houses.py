# Mud-brick house kit: three variants + a simplified LOD each, exported to the game.
# Front (door) faces Blender -Y, which becomes +Z in glTF / three.js.
import sys, importlib, math, random
sys.path.insert(0, '/var/www/html/old/3d-quranic/blender')
import lib; importlib.reload(lib)
from lib import *
OUT = '/var/www/html/old/3d-quranic/public/models/env/'
import os; os.makedirs(OUT, exist_ok=True)

def house(key, w, d, h, seed, arch=False, stair=False, dome=False, upper=False, x0=0.0):
    random.seed(seed)
    col = clear_collection('house_' + key)
    parts = []
    P = lambda o: parts.append(o) or o
    ox = x0

    walls = P(box('walls', (w, d, h + 0.2), (ox, 0, h / 2 - 0.1), 'plaster', col))
    lumpy(walls, strength=0.05, scale=0.8, seed=seed)
    plinth = P(box('plinth', (w + 0.28, d + 0.28, 0.55), (ox, 0, 0.1), 'plaster', col))
    lumpy(plinth, strength=0.04, scale=0.5, levels=2, seed=seed + 1)

    # parapet: a lumpy ring around the flat roof, with a low notch pattern on top
    rim = box('parapet', (w + 0.1, d + 0.1, 0.45), (ox, 0, h + 0.2), 'plaster_light', col)
    hole = box('hole', (w - 0.34, d - 0.34, 0.8), (ox, 0, h + 0.35), 'plaster', col)
    boolean_cut(rim, hole)
    lumpy(rim, strength=0.03, scale=0.6, levels=2, seed=seed + 2)
    P(rim)

    # door: arched or square recess cut into the front wall, planked leaf inside
    dx = ox + random.uniform(-0.25, 0.25) * max(0, w - 2.4)
    cut = box('doorcut', (1.1, 0.7, 2.05), (dx, -d / 2, 1.0), 'plaster', col)
    if arch:
        c2 = cylinder('arch', 0.55, 0.7, (dx, -d / 2, 2.02), 'plaster', col, rot=(math.pi / 2, 0, 0), verts=24)
        boolean_cut(cut, c2, 'UNION')   # a clean single solid; joining overlapping meshes breaks the cut
    boolean_cut(walls, cut)
    for i in range(5):
        P(box(f'plank{i}', (0.2, 0.06, 1.98 if not arch else 2.3), (dx - 0.42 + i * 0.21, -d / 2 + 0.2, 1.0 if not arch else 1.13), 'wood', col, bevel=0.012))
    for z in (0.45, 1.55):
        P(box(f'batten{z}', (1.0, 0.05, 0.1), (dx, -d / 2 + 0.16, z), 'wood_dark', col, bevel=0.01))
    P(cylinder('ring', 0.05, 0.02, (dx + 0.3, -d / 2 + 0.13, 1.05), 'wood_dark', col, rot=(math.pi / 2, 0, 0)))
    if not arch:
        P(box('lintel', (1.55, 0.26, 0.2), (dx, -d / 2 + 0.02, 2.14), 'wood', col, bevel=0.02))

    # small windows with wooden shutters, front and side
    wins = [((ox + (w * 0.3 if dx < ox else -w * 0.3)), -d / 2, 'front')] if w > 4.4 else []
    wins.append((ox + w / 2, random.uniform(-d * 0.2, d * 0.2), 'side'))
    for i, (x, y, face) in enumerate(wins):
        z = h * 0.64
        if face == 'front':
            boolean_cut(walls, box('wc', (0.62, 0.6, 0.72), (x, y, z), 'plaster', col))
            P(box(f'sill{i}', (0.8, 0.22, 0.08), (x, y - 0.06, z - 0.4), 'wood', col, bevel=0.01))
            for s in (-1, 1):
                sh = P(box(f'shutter{i}{s}', (0.3, 0.04, 0.68), (x + s * 0.45, y - 0.2, z), 'wood', col, bevel=0.008))
                sh.rotation_euler.z = s * 0.5
        else:
            boolean_cut(walls, box('wc', (0.6, 0.6, 0.7), (x, y, z), 'plaster', col))
            P(box(f'sill{i}', (0.22, 0.8, 0.08), (x + 0.06, y, z - 0.4), 'wood', col, bevel=0.01))
            P(box(f'grille{i}', (0.05, 0.55, 0.65), (x - 0.12, y, z), 'wood_dark', col))

    # roof beams (vigas) poking out front and back, clay drain spout
    n = max(3, round(w / 0.95))
    for i in range(n):
        x = ox - w / 2 + (i + 0.5) * w / n
        for s in (-1, 1):
            P(cylinder(f'viga{i}{s}', 0.075 + random.uniform(-0.01, 0.015), 0.55, (x, s * (d / 2 + 0.18), h - 0.28), 'wood', col, rot=(math.pi / 2, 0, 0), verts=8))
    P(cylinder('spout', 0.09, 0.7, (ox + w / 2 + 0.3, d * 0.2, h + 0.05), 'clay', col, rot=(0, math.pi / 2 - 0.15, 0), verts=10))

    if stair:   # outside stair up the right-hand wall to the roof
        steps = 10
        for i in range(steps):
            P(box(f'step{i}', (0.9, (i + 1) * (d - 0.6) / steps, h * (i + 1) / steps), (ox + w / 2 + 0.45, -d / 2 + 0.3 + (i + 1) * (d - 0.6) / steps / 2, h * (i + 1) / steps / 2), 'plaster', col, bevel=0.03))
    if upper:   # small roof room at the back
        uw, ud, uh = w * 0.45, d * 0.5, h * 0.62
        room = P(box('upper', (uw, ud, uh), (ox - w * 0.22, d * 0.2, h + uh / 2), 'plaster', col)); lumpy(room, 0.04, 0.8, seed=seed + 5)
        boolean_cut(room, box('uc', (0.8, 0.6, 1.5), (ox - w * 0.22, d * 0.2 - ud / 2, h + 0.75), 'plaster', col))
    if dome:
        r = min(w, d) * 0.26
        P(cylinder('drum', r, 0.4, (ox + w * 0.12, d * 0.1, h + 0.2), 'lime', col, verts=24))
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=r, location=(ox + w * 0.12, d * 0.1, h + 0.4))
        dm = bpy.context.active_object; dm.name = 'dome'; dm.data.materials.append(mat('lime')); link(dm, col)
        bm = bmesh.new(); bm.from_mesh(dm.data)                  # keep the upper hemisphere only
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context='VERTS')
        bm.to_mesh(dm.data); bm.free()
        P(dm)

    for o in parts:
        if o.data.materials and o.data.materials[0].name.startswith('plaster'): uv_world(o, 2.0)
        else: uv_world(o, 1.0)
    obj = join(parts, 'house_' + key)
    shade_auto(obj, 35)
    obj.location.x -= ox; bpy.ops.object.transform_apply(location=True)
    obj.location.x = ox
    low = lod(obj, 0.25, 'house_' + key + '_LOD1')
    low.location.x = ox; low.location.y = d + 3
    return obj, low

V = [('a', 5.6, 4.8, 3.1, 1, dict(arch=True)),
     ('b', 6.4, 5.4, 3.4, 2, dict(stair=True, upper=True)),
     ('c', 4.6, 4.4, 2.9, 3, dict(dome=True))]
report = []
for i, (k, w, d, h, s, o) in enumerate(V):
    obj, low = house(k, w, d, h, s, x0=i * 9.0, **o)
    obj.location.x = 0; low.location = (0, 0, 0)
    export_glb([obj, low], OUT + f'house_{k}.glb')
    report.append((k, len(obj.data.polygons), len(low.data.polygons), [m.name for m in obj.data.materials]))
    obj.location.x = i * 9.0; low.location = (i * 9.0, 9, 0)
print(report)
