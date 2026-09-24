# Village and canal props, one GLB each (origin at ground contact, front = -Y).
import sys, importlib, math, random
sys.path.insert(0, '/var/www/html/old/3d-quranic/blender')
import lib; importlib.reload(lib)
from lib import *
from mathutils import Vector
OUT = '/var/www/html/old/3d-quranic/public/models/env/'
MAT_COLORS.update({'rope': (0.62, 0.52, 0.34), 'straw': (0.78, 0.63, 0.32), 'water_dark': (0.05, 0.09, 0.09), 'iron': (0.2, 0.2, 0.22), 'produce': (0.8, 0.45, 0.1), 'fabric_red': (0.55, 0.16, 0.1)})

def lathe(name, profile, material, col, loc=(0, 0, 0), segs=20):
    """Revolve a (radius, z) profile around Z — jars, baskets, buckets."""
    bm = bmesh.new(); rings = []
    for r, z in profile:
        rings.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for a in (i / segs * math.tau for i in range(segs))])
    for a, b in zip(rings, rings[1:]):
        for i in range(segs): bm.faces.new((a[i], a[(i + 1) % segs], b[(i + 1) % segs], b[i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); col.objects.link(o); o.location = loc
    me.materials.append(mat(material))
    return o

def finish(parts, key, uv=1.0, lod_ratio=None):
    for o in parts: uv_world(o, uv)
    obj = join(parts, key); shade_auto(obj, 40)
    out = [obj]
    if lod_ratio: out.append(lod(obj, lod_ratio, key + '_LOD1'))
    for o in out: o.location = (0, 0, 0)
    export_glb(out, OUT + key + '.glb')
    return obj

made = []
# ---- well: rendered stone ring, wooden frame, pulley, rope, bucket --------------------
col = clear_collection('well'); P = []
ring = lathe('ring', [(1.05, 0), (1.12, 0.05), (1.1, 0.85), (1.16, 0.9), (1.14, 0.98), (0.88, 0.98), (0.86, 0.9), (0.84, 0.1)], 'stone', col, segs=28)
lumpy(ring, 0.03, 0.5, levels=1, seed=31); P.append(ring)
P.append(cylinder('water', 0.84, 0.02, (0, 0, 0.55), 'water_dark', col, verts=28))
for s in (-1, 1): P.append(box(f'post{s}', (0.16, 0.16, 2.1), (s * 1.02, 0, 1.05), 'wood', col, bevel=0.02))
P.append(cylinder('axle', 0.06, 2.3, (0, 0, 2.0), 'wood', col, rot=(0, math.pi / 2, 0), verts=10))
P.append(cylinder('pulley', 0.14, 0.08, (0.2, 0, 2.0), 'wood_dark', col, rot=(0, math.pi / 2, 0), verts=16))
P.append(cylinder('rope', 0.012, 0.95, (0.2, -0.14, 1.52), 'rope', col, verts=5))
P.append(lathe('bucket', [(0.13, 0.95), (0.16, 1.2), (0.17, 1.22)], 'wood', col, segs=14))
made.append(finish(P, 'well', lod_ratio=0.4))

# ---- shaduf: uprights, pivot, sweep pole with stone counterweight and bucket -------------
col = clear_collection('shaduf'); P = []
for s in (-0.45, 0.45): P.append(cylinder(f'up{s}', 0.08, 2.4, (0, s, 1.2), 'wood', col, verts=8, r2=0.065))
P.append(cylinder('pivot', 0.05, 1.1, (0, 0, 2.3), 'wood_dark', col, rot=(math.pi / 2, 0, 0), verts=8))
pole = cylinder('sweep', 0.055, 5.2, (0.6, 0, 2.3), 'wood', col, rot=(0, math.pi / 2, 0), verts=8, r2=0.035)
pole.rotation_euler.y = math.pi / 2 - 0.32; P.append(pole)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.34, location=(-1.25, 0, 1.55)); w = bpy.context.active_object
w.name = 'weight'; w.scale = (1, 0.9, 0.8); w.data.materials.append(mat('stone')); link(w, col); lumpy(w, 0.06, 0.4, levels=1, seed=5); P.append(w)
tip = Vector((0.6 + 2.6 * math.cos(0.32), 0, 2.3 + 2.6 * math.sin(0.32)))
P.append(cylinder('line', 0.012, tip.z - 0.6, (tip.x, 0, (tip.z + 0.6) / 2), 'rope', col, verts=5))
P.append(lathe('bucket', [(0.12, 0.35), (0.17, 0.6), (0.18, 0.62)], 'clay', col, loc=(tip.x, 0, 0), segs=14))
made.append(finish(P, 'shaduf', lod_ratio=0.4))

# ---- sluice gate across a 2.6 m canal --------------------------------------------------------------
col = clear_collection('sluice'); P = []
for s in (-1.45, 1.45): P.append(box(f'post{s}', (0.22, 0.22, 1.7), (s, 0, 0.45), 'wood', col, bevel=0.02))
P.append(box('beam', (3.3, 0.2, 0.2), (0, 0, 1.3), 'wood', col, bevel=0.02))
for i in range(5): P.append(box(f'board{i}', (0.5, 0.07, 0.62), (-1.0 + i * 0.5, 0, -0.05), 'wood_dark', col, bevel=0.01))
P.append(cylinder('handle', 0.03, 0.9, (0, 0, 1.75), 'wood', col, verts=6))
made.append(finish(P, 'sluice'))

# ---- clay jars (two shapes), basket with dates, hoe ---------------------------------------------------
col = clear_collection('jar'); j = lathe('jar', [(0.001, 0), (0.16, 0.01), (0.25, 0.2), (0.27, 0.36), (0.22, 0.52), (0.1, 0.62), (0.11, 0.7), (0.14, 0.72), (0.12, 0.73)], 'clay', col)
made.append(finish([j], 'jar'))
col = clear_collection('jar_b'); j = lathe('jar', [(0.001, 0), (0.12, 0.02), (0.3, 0.28), (0.26, 0.5), (0.13, 0.56), (0.15, 0.6)], 'clay', col)
made.append(finish([j], 'jar_b'))
col = clear_collection('basket'); P = [lathe('b', [(0.001, 0), (0.24, 0.01), (0.33, 0.18), (0.36, 0.24), (0.33, 0.25), (0.3, 0.2)], 'straw', col)]
rnd = random.Random(4)
for i in range(22):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.04, location=(rnd.uniform(-.2, .2), rnd.uniform(-.2, .2), 0.2 + rnd.uniform(0, .05)))
    d = bpy.context.active_object; d.scale.z = 1.4; d.data.materials.append(mat('dates')); link(d, col); P.append(d)
made.append(finish(P, 'basket'))
col = clear_collection('hoe'); P = [cylinder('shaft', 0.022, 1.35, (0, 0, 0.68), 'wood', col, verts=8),
                                    box('blade', (0.26, 0.2, 0.025), (0, -0.08, 0.02), 'iron', col, bevel=0.005)]
made.append(finish(P, 'hoe'))

# ---- palm-rib fence panel (2.2 m) and plank footbridge --------------------------------------------------
col = clear_collection('fence'); P = []; rnd = random.Random(8)
for x in (-1.1, 1.1): P.append(cylinder(f'post{x}', 0.055, 1.25, (x, 0, 0.55), 'wood', col, verts=7, r2=0.045))
for z in (0.42, 0.85): P.append(cylinder(f'rail{z}', 0.025, 2.3, (0, 0, z), 'wood', col, rot=(0, math.pi / 2, 0), verts=6))
for i in range(15):
    x = -1.0 + i * 0.143; h = 1.0 + rnd.uniform(-0.1, 0.12)
    r = cylinder(f'rib{i}', 0.014, h, (x, 0.03, h / 2 - 0.05), 'frond_dry' if 'frond_dry' in MAT_COLORS else 'straw', col, verts=5, r2=0.008)
    r.rotation_euler.y = rnd.uniform(-0.05, 0.05); P.append(r)
MAT_COLORS['frond_dry'] = (0.45, 0.35, 0.18)
made.append(finish(P, 'fence'))
col = clear_collection('footbridge'); P = []
for i in range(5): P.append(box(f'pl{i}', (3.4, 0.33, 0.08), (0, -0.7 + i * 0.35, 0.1), 'wood' if i % 2 else 'wood_dark', col, bevel=0.012))
for s in (-1.5, 1.5): P.append(box(f'sleeper{s}', (0.16, 1.9, 0.12), (s, 0, 0.02), 'wood_dark', col, bevel=0.01))
made.append(finish(P, 'footbridge'))

# ---- market stall with awning and produce; hay bale ------------------------------------------------------
col = clear_collection('stall'); P = []
for x, y in ((-1.4, -0.9), (1.4, -0.9), (-1.4, 0.9), (1.4, 0.9)): P.append(cylinder(f'p{x}{y}', 0.05, 2.5 if y < 0 else 2.2, (x, y, 1.25 if y < 0 else 1.1), 'wood', col, verts=7))
aw = box('awning', (3.2, 2.2, 0.04), (0, 0, 2.35), 'fabric_red', col); aw.rotation_euler.x = 0.14; P.append(aw)
P.append(box('table', (2.6, 1.2, 0.08), (0, 0.1, 0.8), 'wood', col, bevel=0.01))
for x in (-1.2, 1.2): P.append(box(f'leg{x}', (0.08, 1.1, 0.78), (x, 0.1, 0.39), 'wood_dark', col))
rnd = random.Random(2)
for i in range(3):
    b = lathe(f'bowl{i}', [(0.001, 0), (0.2, 0.02), (0.28, 0.14)], 'straw', col, loc=(-0.8 + i * 0.8, 0.1, 0.84), segs=14); P.append(b)
    for k in range(8):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.07, location=(-0.8 + i * 0.8 + rnd.uniform(-.12, .12), 0.1 + rnd.uniform(-.12, .12), 0.98))
        f = bpy.context.active_object; f.data.materials.append(mat(['produce', 'dates', 'frond'][i])); link(f, col); P.append(f)
made.append(finish(P, 'stall', lod_ratio=0.4))
col = clear_collection('hay'); h = cylinder('bale', 0.6, 1.2, (0, 0, 0.6), 'straw', col, rot=(0, math.pi / 2, 0), verts=18)
lumpy(h, 0.05, 0.3, levels=1, seed=9)
made.append(finish([h], 'hay'))

for i, o in enumerate(made): o.location = (i * 4.5, -20, 0)
print([(o.name, len(o.data.polygons)) for o in made])
