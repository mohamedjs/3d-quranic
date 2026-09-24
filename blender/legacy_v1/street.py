# Village-street pieces: stone-lined water channel (4 m segment), low garden wall
# (4 m segment with plaster coping), potted plant. Origins at ground level.
import sys, importlib, math, random
sys.path.insert(0, '/var/www/html/old/3d-quranic/blender')
import lib; importlib.reload(lib)
from lib import *
OUT = '/var/www/html/old/3d-quranic/public/models/env/'
MAT_COLORS.update({'stream_water': (0.1, 0.25, 0.25), 'mud': (0.25, 0.18, 0.12), 'leaf': (0.2, 0.35, 0.12)})

def rock(name, size, loc, col, seed, material='stone'):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=loc)
    o = bpy.context.active_object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(mat(material)); link(o, col)
    lumpy(o, strength=0.18 * min(size), scale=0.35, levels=0, seed=seed)
    return o

def finish(parts, key, uv=1.0, lod_ratio=None):
    for o in parts: uv_world(o, uv)
    obj = join(parts, key); shade_auto(obj, 45)
    out = [obj]
    if lod_ratio: out.append(lod(obj, lod_ratio, key + '_LOD1'))
    for o in out: o.location = (0, 0, 0)
    export_glb(out, OUT + key + '.glb')
    return obj

made = []
# ---- stream channel: runs along Blender Y (→ three.js -Z), 4 m long, 0.8 m wide ----------
col = clear_collection('stream'); P = []; rnd = random.Random(3)
P.append(box('bed', (0.9, 4.0, 0.1), (0, 0, -0.32), 'mud', col))
for s in (-1, 1):
    y = -2.0
    while y < 2.0:
        L = rnd.uniform(0.35, 0.6)
        P.append(rock(f'curb{s}{y:.2f}', (rnd.uniform(0.18, 0.24), L / 2, rnd.uniform(0.16, 0.22)), (s * 0.55, y + L / 2, 0.02), col, rnd.randint(0, 999)))
        y += L * 0.92
    P.append(box(f'wall{s}', (0.12, 4.0, 0.4), (s * 0.47, 0, -0.15), 'stone', col))
w = box('surface', (0.84, 4.0, 0.001), (0, 0, -0.06), 'stream_water', col)
P.append(w)
made.append(finish(P, 'stream', uv=0.8))

# ---- garden wall: rubble stone base, plaster upper, rounded coping ------------------------
col = clear_collection('garden_wall'); P = []; rnd = random.Random(5)
base = box('base', (4.0, 0.45, 0.5), (0, 0, 0.2), 'stone', col); lumpy(base, 0.04, 0.4, levels=2, seed=41); P.append(base)
up = box('upper', (4.0, 0.38, 0.55), (0, 0, 0.7), 'plaster', col); lumpy(up, 0.035, 0.7, levels=2, seed=42); P.append(up)
cap = cylinder('coping', 0.2, 4.05, (0, 0, 0.98), 'plaster_light', col, rot=(0, math.pi / 2, 0), verts=12)
cap.scale = (1, 1.05, 0.6); P.append(cap)
made.append(finish(P, 'garden_wall', uv=1.5, lod_ratio=0.35))

# ---- potted plant: terracotta pot with a small leafy plant --------------------------------------
col = clear_collection('pot_plant'); P = []
bm = bmesh.new(); prof = [(0.001, 0), (0.16, 0.01), (0.22, 0.34), (0.25, 0.4), (0.22, 0.42)]
rings = [[bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for a in (i / 18 * math.tau for i in range(18))] for r, z in prof]
for a, b in zip(rings, rings[1:]):
    for i in range(18): bm.faces.new((a[i], a[(i + 1) % 18], b[(i + 1) % 18], b[i]))
me = bpy.data.meshes.new('pot'); bm.to_mesh(me); bm.free(); pot = bpy.data.objects.new('pot', me); col.objects.link(pot); me.materials.append(mat('clay')); P.append(pot)
P.append(cylinder('soil', 0.21, 0.02, (0, 0, 0.38), 'mud', col, verts=18))
bm = bmesh.new(); rnd = random.Random(9)
for i in range(14):
    a = i * 2.4; L = rnd.uniform(0.35, 0.6); up = rnd.uniform(0.6, 1.1)
    p0 = (0, 0, 0.38); p1 = (math.cos(a) * L * 0.6, math.sin(a) * L * 0.6, 0.38 + L * up)
    wv = (-math.sin(a) * 0.06, math.cos(a) * 0.06, 0)
    v = [bm.verts.new(x) for x in (p0, (p1[0] + wv[0], p1[1] + wv[1], p1[2]), (p1[0] * 1.3, p1[1] * 1.3, p1[2] - 0.12), (p1[0] - wv[0], p1[1] - wv[1], p1[2]))]
    bm.faces.new(v)
me = bpy.data.meshes.new('leaves'); bm.to_mesh(me); bm.free(); lv = bpy.data.objects.new('leaves', me); col.objects.link(lv); me.materials.append(mat('frond')); P.append(lv)
made.append(finish(P, 'pot_plant'))

for i, o in enumerate(made): o.location = (i * 5, -30, 0)
print([(o.name, len(o.data.polygons)) for o in made])
