# Date palms: scarred trunk (leaf-base "boots"), pinnate fronds made of real leaflets,
# hanging date clusters, dry fronds skirting older trees. Three variants + LOD1 each.
import sys, importlib, math, random
sys.path.insert(0, '/var/www/html/old/3d-quranic/blender')
import lib; importlib.reload(lib)
from lib import *
from mathutils import Vector, Matrix
OUT = '/var/www/html/old/3d-quranic/public/models/env/'

def mesh_obj(name, bm, material, col):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); col.objects.link(o)
    for m in material if isinstance(material, list) else [material]: me.materials.append(mat(m))
    return o

def trunk(height, lean, col, seed):
    random.seed(seed)
    bm = bmesh.new(); uv = bm.loops.layers.uv.new()
    rings, sides = int(height / 0.12), 12
    prev = None
    path = lambda t: Vector((lean * t * t, 0, height * t))
    for i in range(rings + 1):
        t = i / rings; c = path(t)
        tang = (path(min(1, t + 0.01)) - path(max(0, t - 0.01))).normalized()
        side = tang.cross(Vector((0, 1, 0))).normalized(); up2 = tang.cross(side)
        base = 0.34 if i == 0 else 0.26 - 0.07 * t + (0.1 * (1 - t) ** 6)
        boot = 0.035 * (1 if (i % 2) else -0.4)            # diamond leaf-base scars
        ring = []
        for k in range(sides):
            a = k / sides * math.tau + (i % 2) * math.pi / sides
            r = base + boot + random.uniform(-0.008, 0.008)
            ring.append(bm.verts.new(c + (side * math.cos(a) + up2 * math.sin(a)) * r))
        if prev:
            for k in range(sides):
                f = bm.faces.new((prev[k], prev[(k + 1) % sides], ring[(k + 1) % sides], ring[k]))
                for j, l in enumerate(f.loops):
                    kk = k + (1 if j in (1, 2) else 0); ii = i - (1 if j in (0, 1) else 0)
                    l[uv].uv = (kk / sides * 1.6, ii * 0.12 / 0.8)
        prev = ring
    bm.normal_update()
    return mesh_obj('trunk', bm, 'bark', col), path(1)

def frond(bm, top, yaw, pitch, length, droop, dry=False, seed=0):
    """A pinnate frond: rachis + paired leaflets folded in a shallow V."""
    rnd = random.Random(seed)
    def spine(t):
        s = t * length
        return Vector((0, s * math.cos(pitch), s * math.sin(pitch) - droop * s * s / length))
    R = Matrix.Rotation(yaw, 4, 'Z')
    n = 34
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        p0, p1 = spine(t0), spine(t1)
        w0, w1 = 0.035 * (1 - t0 * 0.8), 0.035 * (1 - t1 * 0.8)
        v = [bm.verts.new(top + R @ (p + Vector((dx, 0, 0)))) for p, dx in ((p0, -w0), (p0, w0), (p1, w1), (p1, -w1))]
        bm.faces.new(v).material_index = 1 if not dry else 2
        if t0 < 0.12: continue
        L = 0.62 * math.sin(math.pi * min(1, (t0 - 0.05) * 1.05)) + 0.1
        d = (p1 - p0).normalized()
        for s in (-1, 1):
            out = Vector((s, 0, 0)); tip = p0 + (out * 0.9 + d * 0.55 + Vector((0, 0, -0.25 - 0.3 * t0 + rnd.uniform(-0.1, 0.12)))).normalized() * L
            mid = p0.lerp(tip, 0.5) + Vector((0, 0, 0.035))       # fold: leaflets are V-shaped
            wv = d * 0.045
            q = [bm.verts.new(top + R @ x) for x in (p0 - wv, mid, tip, mid + wv * 1.6)]
            bm.faces.new(q).material_index = 1 if not dry else 2

def dates(bm, top, yaw, rnd):
    R = Matrix.Rotation(yaw, 4, 'Z')
    for k in range(5):
        a = rnd.uniform(-0.4, 0.4)
        strand0 = top + R @ Vector((a, 0.35, -0.25)); strand1 = strand0 + R @ Vector((a * 0.5, 0.25, -0.75))
        bmesh.ops.create_cone(bm, cap_ends=False, segments=4, radius1=0.015, radius2=0.012, depth=(strand1 - strand0).length,
                              matrix=Matrix.Translation((strand0 + strand1) / 2) @ (strand1 - strand0).to_track_quat('Z', 'Y').to_matrix().to_4x4())
        for j in range(9):
            p = strand0.lerp(strand1, 0.3 + j * 0.08) + Vector((rnd.uniform(-.06, .06), rnd.uniform(-.06, .06), 0))
            ret = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.035, matrix=Matrix.Translation(p) @ Matrix.Scale(1.4, 4, (0, 0, 1)))
            for f in {f for v in ret['verts'] for f in v.link_faces}: f.material_index = 3

def palm(key, height, lean, fronds, droop, skirt, seed):
    rnd = random.Random(seed)
    col = clear_collection('palm_' + key)
    t, top = trunk(height, lean, col, seed)
    bm = bmesh.new()
    for i in range(fronds):
        young = i >= fronds - 4
        yaw = i * 2.39996 + rnd.uniform(-0.2, 0.2)            # golden-angle phyllotaxis
        pitch = (1.15 if young else rnd.uniform(0.25, 0.75))
        frond(bm, top, yaw, pitch, rnd.uniform(3.0, 3.8) * (0.75 if young else 1), (0.25 if young else droop) * rnd.uniform(0.8, 1.2), seed=seed * 100 + i)
    for i in range(skirt):                                       # dead fronds hanging down
        frond(bm, top - Vector((0, 0, 0.35)), i * 2.39996 + 1, -1.2 + rnd.uniform(-0.2, 0.2), rnd.uniform(2.2, 2.9), 0.1, dry=True, seed=seed * 200 + i)
    for i in range(3): dates(bm, top - Vector((0, 0, 0.2)), i * 2.1 + rnd.uniform(0, 1), rnd)
    bm.normal_update()
    crown = mesh_obj('crown', bm, ['bark', 'frond', 'frond_dry', 'dates'], col)
    obj = join([t, crown], 'palm_' + key)
    shade_auto(obj, 60)
    low = lod(obj, 0.2, 'palm_' + key + '_LOD1')
    return obj, low

MAT_COLORS.update({'frond': (0.20, 0.30, 0.10), 'frond_dry': (0.45, 0.35, 0.18), 'dates': (0.55, 0.2, 0.05), 'bark': (0.42, 0.33, 0.24)})
V = [('a', 7.0, 0.9, 20, 0.5, 0, 11), ('b', 9.5, 1.8, 22, 0.65, 7, 12), ('c', 5.2, 0.4, 16, 0.4, 3, 13)]
report = []
for i, (k, h, lean, fr, dr, sk, s) in enumerate(V):
    obj, low = palm(k, h, lean, fr, dr, sk, s)
    obj.location = (0, 0, 0); low.location = (0, 0, 0)
    export_glb([obj, low], OUT + f'palm_{k}.glb')
    report.append((k, len(obj.data.polygons), len(low.data.polygons)))
    obj.location = (40 + i * 8, 0, 0); low.location = (40 + i * 8, 10, 0)
print(report)
