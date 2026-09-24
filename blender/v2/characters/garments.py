# Clothes, headwear, hair and props for the anime cast. Garments are simple smooth shapes
# derived from the MPFB reference body (so they fit) and skinned from its weights.
import bpy, bmesh, math, random
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from toon_lib import *
from head import head_shape, ss

# ---------------------------------------------------------------- body measurements
def extent(h, z, band=0.03, filt=None):
    pts = [v.co for i, v in enumerate(h.ref.data.vertices) if abs(v.co.z - z) < band and (filt is None or filt(h.dom[i]))]
    if not pts: return 0.1, 0.1, 0.0
    xs = [abs(p.x) for p in pts]; ys = [p.y for p in pts]
    cy = (min(ys) + max(ys)) / 2
    return max(xs), (max(ys) - min(ys)) / 2, cy

TORSO = lambda d: d.startswith(('spine', 'pelvis', 'clavicle'))
LEGS = lambda d: d.startswith(('thigh', 'calf', 'pelvis'))

# ---------------------------------------------------------------- upper robe (torso + sleeves)
def robe_top(h, name, mat, loose=0.028, sleeve_end=0.78, sleeve_flare=0.035, drape=80, dec=0.28, collar=0.012, cut_z=None):
    b = h.rig.data.bones
    def keep(d, co):
        if d.startswith(('spine', 'pelvis', 'clavicle', 'upperarm')): return True
        if d.startswith('thigh'): return co.z > h.hip_z - 0.08
        if d == 'neck_01': return co.z < h.neck.z + collar
        if d.startswith('lowerarm'):
            bb = b['lowerarm_' + d[-1]]; a, c = bb.head_local, bb.tail_local
            return (co - a).dot(c - a) / (c - a).length_squared < sleeve_end
        return False
    o = h.copy_ref(name, (lambda d, co: keep(d, co) and (cut_z is None or co.z > cut_z or d.startswith(('upperarm', 'lowerarm')))))
    d = h.dominant(o)
    tg = o.vertex_groups.new(name='_torso')
    tg.add([i for i, x in enumerate(d) if x.startswith(('spine', 'pelvis', 'thigh'))], 1.0, 'REPLACE')
    inflate(o, lambda co, n: loose + (0.015 if co.z < h.hip_z + 0.12 else 0))
    s = o.modifiers.new('drape', 'SMOOTH'); s.factor = 1.3; s.iterations = drape; s.vertex_group = '_torso'
    s2 = o.modifiers.new('all', 'SMOOTH'); s2.factor = 0.8; s2.iterations = 12
    apply_all(o); o.vertex_groups.remove(o.vertex_groups['_torso'])
    # wide sleeves: flare toward the cuff
    d = h.dominant(o)
    bm = bmesh.new(); bm.from_mesh(o.data); bm.normal_update(); bm.verts.ensure_lookup_table()
    for i, v in enumerate(bm.verts):
        if d[i].startswith('lowerarm'):
            bb = b['lowerarm_' + d[i][-1]]; a, c = bb.head_local, bb.tail_local
            t = max(0, (v.co - a).dot(c - a) / (c - a).length_squared)
            v.co += v.normal * (0.012 + sleeve_flare * t ** 2)
    bm.to_mesh(o.data); bm.free()
    if dec < 1:
        dm = o.modifiers.new('d', 'DECIMATE'); dm.ratio = dec; apply_all(o)
    o.data.materials.clear(); o.data.materials.append(mat); shade_smooth(o)
    return h.skin(o)

# ---------------------------------------------------------------- skirts (lathe) + trousers
def skirt(h, name, mat, top, hem, flare=0.2, margin=0.04, folds=0.035, segs=28, levels=7, front_short=0.0, taper=0.8):
    pts = [v.co for i, v in enumerate(h.ref.data.vertices) if LEGS(h.dom[i]) or h.dom[i].startswith('spine')]
    cy = sum(p.y for p in pts if p.z < h.hip_z) / max(1, sum(1 for p in pts if p.z < h.hip_z))
    rings, prev = [], None
    for i in range(levels):
        t = i / (levels - 1); z = top - (top - hem) * t
        band = [p for p in pts if abs(p.z - z) < 0.05] or (sorted(pts, key=lambda p: abs(p.z - z))[:150] if prev is None else [])
        if band: rx = max(abs(p.x) for p in band) + margin; ry = max(abs(p.y - cy) for p in band) + margin * 1.3
        else: rx, ry = prev
        if prev: rx, ry = max(rx, prev[0]), max(ry, prev[1])
        prev = (rx, ry)
        f = 1 + flare * t ** 1.6
        k = folds * t ** 1.4
        fn = (lambda th, k=k: 1 + k * (0.6 * math.sin(6 * th + 0.4) + 0.4 * math.sin(11 * th + 1.3)))
        zf = (lambda th, t=t: front_short * t * max(0, -math.sin(th)) ** 2)
        if i == 0 and taper: rx, ry = rx * taper, ry * taper
        rings.append((z, rx * f, ry * f, fn, zf))
        if i == 0 and taper: prev = (rx / taper * 0.97, ry / taper * 0.97)
    print('SKIRT', name, [(round(r[0], 3), round(r[1], 3), round(r[2], 3)) for r in rings], 'hip', round(h.hip_z, 3), flush=True)
    bm = bmesh.new()
    loops = []
    for z, rx, ry, fn, zf in rings:
        loops.append([bm.verts.new((rx * fn(th) * math.cos(th), cy + ry * fn(th) * math.sin(th), z + zf(th)))
                      for th in (k / segs * math.tau for k in range(segs))])
    for a, c in zip(loops, loops[1:]):
        for k in range(segs): bm.faces.new((a[k], a[(k + 1) % segs], c[(k + 1) % segs], c[k]))
    # a turned-in hem so the edge reads as cloth thickness
    inner = [bm.verts.new((v.co.x * 0.94, cy + (v.co.y - cy) * 0.94, v.co.z + 0.02)) for v in loops[-1]]
    for k in range(segs): bm.faces.new((loops[-1][k], loops[-1][(k + 1) % segs], inner[(k + 1) % segs], inner[k]))
    o = bm_obj(bm, name, h.col, mat)
    bm2 = bmesh.new(); bm2.from_mesh(o.data); bm2.normal_update()
    if sum((f.calc_center_median() - Vector((0, cy, f.calc_center_median().z))).dot(f.normal) for f in bm2.faces) < 0:
        bmesh.ops.reverse_faces(bm2, faces=bm2.faces)
    bm2.to_mesh(o.data); bm2.free()
    skirt_weights(o, h, top, hem)
    return o

def skirt_weights(o, h, top_z, hem_z):
    """One tube over both legs: hips -> thighs blend smoothly around and down it."""
    for g in list(o.vertex_groups): o.vertex_groups.remove(g)
    gp, gl, gr = (o.vertex_groups.new(name=n) for n in ('pelvis', 'thigh_l', 'thigh_r'))
    for v in o.data.vertices:
        t = min(1, max(0, (top_z - v.co.z) / max(0.01, top_z - hem_z)))
        side = 0.5 + 0.5 * max(-1, min(1, v.co.x / 0.12))
        gp.add([v.index], max(0.05, 1 - 0.85 * t), 'REPLACE')
        gl.add([v.index], 0.85 * t * side, 'REPLACE'); gr.add([v.index], 0.85 * t * (1 - side), 'REPLACE')
    bind(o, h.rig)

def trousers(h, name, mat, hem_up=0.07, loose=0.02, dec=0.35):
    ankle = h.foot_z + hem_up
    o = h.copy_ref(name, lambda d, co: (d.startswith(('thigh', 'calf')) or (d == 'pelvis')) and co.z > ankle)
    inflate(o, lambda co, n: loose + 0.012 * ss(h.knee_z, ankle, co.z))
    smooth_mod(o, 0.6, 6)
    dm = o.modifiers.new('d', 'DECIMATE'); dm.ratio = dec; apply_all(o)
    o.data.materials.clear(); o.data.materials.append(mat); shade_smooth(o)
    return h.skin(o)

def shoes(h, name, mat, height=0.07, puff=0.01, dec=0.14):
    ankle = h.foot_z + height
    o = h.copy_ref(name, lambda d, co: (d.startswith(('foot', 'ball')) or d.startswith('calf')) and co.z < ankle)
    inflate(o, lambda co, n: puff + (0.004 if co.z < h.foot_z + 0.015 else 0))
    smooth_mod(o, 1.0, 25)
    bm = bmesh.new(); bm.from_mesh(o.data)
    for v in bm.verts:
        if v.co.z < h.foot_z: v.co.z = h.foot_z          # flat sole on the ground
    bm.to_mesh(o.data); bm.free()
    dm = o.modifiers.new('d', 'DECIMATE'); dm.ratio = dec; apply_all(o)
    o.data.materials.clear(); o.data.materials.append(mat); shade_smooth(o)
    return h.skin(o)

# ---------------------------------------------------------------- head-space shells
class HeadFrame:
    def __init__(self, center, R, F, head_obj):
        self.C, self.R, self.F, self.obj = Vector(center), R, F, head_obj
    def w(self, p): return self.C + Vector(p) * self.R
    def u(self, co): return (Vector(co) - self.C) / self.R

def head_shell(hf, name, col, keep, thick, mat, snap=None, subdiv=0, dec=1.0):
    """Copy of the head keeping vertices with keep(unit co); boundary vertices snapped onto
    snap(unit co)->unit co (then back onto the head surface); inflated by thick(unit co)*R."""
    me = hf.obj.data.copy(); o = new_obj(name, me, col); o.matrix_world = hf.obj.matrix_world.copy()
    keep_verts(o, [keep(hf.u(v.co)) for v in me.vertices])
    bvh = BVHTree.FromObject(hf.obj, bpy.context.evaluated_depsgraph_get())
    bm = bmesh.new(); bm.from_mesh(o.data)
    if snap:
        for v in bm.verts:
            if v.is_boundary:
                q = hf.w(snap(hf.u(v.co))); hit = bvh.find_nearest(q)
                if hit[0]: v.co = hit[0]
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * thick(hf.u(v.co)) * hf.R
    for f in bm.faces: f.material_index = 0
    bm.to_mesh(o.data); bm.free()
    if subdiv:
        sd = o.modifiers.new('s', 'SUBSURF'); sd.levels = subdiv; apply_all(o)
    if dec < 1:
        dm = o.modifiers.new('d', 'DECIMATE'); dm.ratio = dec; apply_all(o)
    o.data.materials.clear(); o.data.materials.append(mat); shade_smooth(o)
    return o

def ellipse_snap(cx, cz, rx, rz):
    def f(u):
        a = math.atan2((u.z - cz) / rz, (u.x - cx) / rx)
        return Vector((cx + rx * math.cos(a), u.y, cz + rz * math.sin(a)))
    return f

def fib_points(n):
    out = []
    ga = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n; r = math.sqrt(1 - z * z); t = ga * i
        out.append(Vector((r * math.cos(t), r * math.sin(t), z)))
    return out

def head_surface(F, s):
    p = head_shape(s, F); e = 1e-3
    t1 = s.orthogonal().normalized(); t2 = s.cross(t1)
    n = (head_shape((s + t1 * e).normalized(), F) - p).cross(head_shape((s + t2 * e).normalized(), F) - p).normalized()
    if n.dot(p) < 0: n = -n
    return p, n

# ---------------------------------------------------------------- hair
def curly_hair(hf, name, col, mat, front_z=0.32, back_z=-0.72, n_curls=30, length=0.36, radius=0.2, seed=4):
    rnd = random.Random(seed); F = hf.F
    def hairline(u):
        hl = front_z + (back_z - front_z) * ss(-0.55, 0.55, u.y)
        if abs(u.x) > 0.62 and -0.45 < u.y < 0.4: hl = max(hl, -0.1)
        return hl
    cap = head_shell(hf, name, col, lambda u: u.z > hairline(u) - 0.05,
                     lambda u: 0.07 + 0.05 * max(0, u.z) ** 1.5, mat, subdiv=0)
    bm = bmesh.new()
    samples = []
    for s in fib_points(420):
        p, n = head_surface(F, s)
        if p.z > hairline(p) + 0.02: samples.append((p, n))
    rnd.shuffle(samples); chosen = []
    for p, n in samples:
        if all((p - q).length > 0.3 for q, _ in chosen): chosen.append((p, n))
    for p, n in chosen[:n_curls]:
        front = p.y < -0.35 and p.z > front_z - 0.05
        flow = Vector((0.25 * math.copysign(1, p.x) if not front else -0.2 * p.x, 0.25 if not front else -0.9, -1))
        ft = (flow - n * flow.dot(n)).normalized()
        d = (n * (0.3 if not front else 0.2) * (0.6 if p.z > 0.5 else 1) + ft).normalized()
        ax = ft.cross(n).normalized()
        L = length * rnd.uniform(0.85, 1.2) * (1.15 if front else 1)
        root = p + n * (0.07 + 0.05 * max(0, p.z) ** 1.5 - 0.02)
        clump(bm, hf.w(root), d, L * hf.R, radius * hf.R * rnd.uniform(0.9, 1.15), curl_axis=ax,
              curl=rnd.uniform(2.2, 2.9) * rnd.choice((1, -1)) * (1 if not front else 0.6), segs=7, rings=5, flat=0.85, fat=0.6)
    # fringe: a few chunky locks falling over the forehead
    for x in (-0.42, -0.14, 0.16, 0.44):
        s = Vector((x, -0.9, front_z + 0.3)).normalized()
        p, n = head_surface(F, s)
        root = p + n * 0.1
        d = Vector((x * 0.3, -0.35, -1)).normalized()
        clump(bm, hf.w(root), d, 0.4 * hf.R * rnd.uniform(0.9, 1.1), 0.17 * hf.R, curl_axis=Vector((1, 0, 0)) if x > 0 else Vector((-1, 0, 0)),
              curl=rnd.uniform(1.4, 2.0) * (1 if x > 0 else -1) * 0 + 1.7, segs=6, rings=5, flat=0.75, fat=0.5)
    curls = bm_obj(bm, name + '_curls', col, mat)
    return [cap, curls]

# ---------------------------------------------------------------- beard
def beard(hf, name, col, mat, top=0.05, side_up=-0.35, chin_len=0.14, thick=0.05, moustache=True, mouth_hole=True):
    F = hf.F; mz, mw = F['mouth_z'], F['mouth_w']
    def top_z(x): return mz + top + (side_up - mz - top) * ss(0.35, 0.72, abs(x))
    def keep(u):
        if u.y > 0.42 or u.z > top_z(u.x) or abs(u.x) > 0.8: return False
        if mouth_hole and abs(u.x) < mw * 1.15 and u.z > mz - 0.09 and u.y < -0.3: return False
        return True
    def snap(u):
        if mouth_hole and abs(u.x) < mw * 1.6 and u.z > mz - 0.2 and u.y < -0.3 and u.z < mz + 0.1:
            return ellipse_snap(0, mz, mw * 1.15, 0.09)(u)
        return Vector((u.x, u.y, top_z(u.x)))
    o = head_shell(hf, name, col, keep, lambda u: thick + chin_len * ss(-0.95, -1.55, u.z) * max(0, -u.y), mat, snap=snap, subdiv=1)
    parts = [o]
    if moustache:
        bm = bmesh.new()
        for s in (1, -1):
            p, n = head_surface(F, Vector((s * 0.05, -1, mz + 0.09)).normalized())
            p = Vector((s * 0.03, p.y, mz + 0.075)); p.y = head_surface(F, Vector((s * 0.03, -1, mz + 0.08)).normalized())[0].y
            clump(bm, hf.w(p + Vector((0, -0.05, 0))), Vector((s * 1, -0.25, -0.45)), mw * 1.6 * hf.R, 0.085 * hf.R,
                  curl_axis=Vector((0, 1, 0)), curl=0.6 * s, segs=6, rings=5, flat=0.7, fat=0.6)
        parts.append(bm_obj(bm, name + '_moustache', col, mat))
    return parts

# ---------------------------------------------------------------- headwear
def ring_tube(bm, center, rx, ry, z, r, tilt=0.0, phase=0.0, segs=32, tsegs=8, bulge=0.0):
    pts = [Vector((center.x + rx * math.cos(a), center.y + ry * math.sin(a), z + tilt * math.sin(a + phase)))
           for a in (k / segs * math.tau for k in range(segs))]
    rings = []
    for i, p in enumerate(pts):
        d = (pts[(i + 1) % segs] - pts[i - 1]).normalized()
        out = Vector((p.x - center.x, p.y - center.y, 0)).normalized()
        up = d.cross(out).normalized()
        rr = r * (1 + bulge * math.sin(3 * i / segs * math.tau + phase))
        rings.append([bm.verts.new(p + (out * math.cos(a) * 1.0 + up * math.sin(a) * 0.8) * rr) for a in (k / tsegs * math.tau for k in range(tsegs))])
    for i in range(segs):
        A, B = rings[i], rings[(i + 1) % segs]
        for k in range(tsegs): bm.faces.new((A[k], A[(k + 1) % tsegs], B[(k + 1) % tsegs], B[k]))

def head_width_at(F, z):
    """Half width / half depth (unit) and centre y of the head at unit height z."""
    pts = [head_shape(s, F) for s in fib_points(1500)]
    band = [p for p in pts if abs(p.z - z) < 0.06]
    xs = [abs(p.x) for p in band]; ys = [p.y for p in band]
    return max(xs), (max(ys) - min(ys)) / 2, (max(ys) + min(ys)) / 2

def turban(hf, name, col, mat, band_front=0.42, band_back=-0.2, puff=0.2, wraps=4):
    F = hf.F
    bz = lambda u: band_front + (band_back - band_front) * ss(-0.6, 0.6, u.y)
    dome = head_shell(hf, name, col, lambda u: u.z > bz(u) - 0.02, lambda u: puff + 0.06 * max(0, u.z), mat,
                      snap=lambda u: Vector((u.x, u.y, bz(u))))
    bm = bmesh.new()
    for i in range(wraps):
        t = i / max(1, wraps - 1)
        z = (band_front + band_back) / 2 + 0.05 + 0.34 * t
        hx, hy, cy = head_width_at(F, z)
        k = 1 + puff * 1.05 - 0.07 * t * t
        ring_tube(bm, hf.w((0, cy, 0)), (hx + puff * 0.45) * hf.R * (1 - 0.08 * t), (hy + puff * 0.45) * hf.R * (1 - 0.08 * t),
                  hf.w((0, 0, z)).z, (0.16 - 0.02 * t) * hf.R, tilt=(0.16 if i % 2 else -0.13) * hf.R, phase=0.6 * i, bulge=0.12)
    wr = bm_obj(bm, name + '_wraps', col, mat)
    return [dome, wr]

def hood(hf, name, col, mat, face_rx=0.78, face_top=0.45, face_bot=-1.62, thick=0.1, open_bottom=False):
    F = hf.F
    cz = (face_top + face_bot) / 2; rz = (face_top - face_bot) / 2
    def inside(u):
        if u.y > -0.05: return False
        if open_bottom and u.z < cz: return abs(u.x) < face_rx * 1.02
        return (u.x / face_rx) ** 2 + ((u.z - cz) / rz) ** 2 < 1
    def snap(u):
        if open_bottom and u.z < cz: return Vector((math.copysign(face_rx, u.x), u.y, u.z))
        return ellipse_snap(0, cz, face_rx, rz)(u)
    return head_shell(hf, name, col, lambda u: not inside(u),
                      lambda u: thick + 0.03 * max(0, -u.z - 0.4), mat, snap=snap)

def cape(h, hf, name, mat, drop_front=0.12, drop_back=0.2, open_front=0.0, segs=30, spread=0.05, folds=0.04):
    """Cloth falling from under the head over the shoulders (tarha / keffiyeh tails).
    open_front > 0 leaves a gap of that half-angle (radians) at the front."""
    C, R = hf.C, hf.R
    sh_z = h.rig.data.bones['upperarm_l'].head_local.z
    sx, sy, scy = extent(h, sh_z - 0.03, 0.03, TORSO)
    nx, ny, ncy = extent(h, h.neck.z + 0.02, 0.02, lambda d: d.startswith('neck'))
    levels = [
        (C.z - 0.95 * R, 0.62 * R, 0.62 * R, C.y + 0.05 * R, 0),
        (h.neck.z + 0.01, nx + 0.035, ny + 0.035, ncy, 0),
        (sh_z + 0.04, sx * 0.75 + spread, sy + 0.055, scy, 0.2),
        (sh_z - 0.03, sx + 0.045 + spread, sy + 0.07, scy, 0.6),
        (sh_z - 0.10, sx + 0.06 + spread, sy + 0.085, scy, 1.0),
    ]
    a0 = -math.pi / 2 + open_front; a1 = -math.pi / 2 + math.tau - open_front
    closed = open_front <= 0
    n = segs if closed else segs + 1
    bm = bmesh.new(); loops = []
    for z, rx, ry, cy, t in levels:
        loop = []
        for k in range(n):
            th = a0 + (a1 - a0) * k / segs
            f = 1 + folds * t * math.sin(7 * th + 0.5)
            drop = t * (drop_front * max(0, -math.sin(th)) + drop_back * max(0, math.sin(th)))
            loop.append(bm.verts.new((rx * f * math.cos(th), cy + ry * f * math.sin(th), z - drop)))
        loops.append(loop)
    for A, B in zip(loops, loops[1:]):
        for k in range(n if closed else n - 1):
            bm.faces.new((A[k], A[(k + 1) % n], B[(k + 1) % n], B[k]))
    o = bm_obj(bm, name, h.col, mat)
    bm2 = bmesh.new(); bm2.from_mesh(o.data); bm2.normal_update()
    if sum(Vector((f.calc_center_median().x, f.calc_center_median().y - scy, 0)).dot(f.normal) for f in bm2.faces) < 0:
        bmesh.ops.reverse_faces(bm2, faces=bm2.faces)
    bm2.to_mesh(o.data); bm2.free()
    sd = o.modifiers.new('s', 'SUBSURF'); sd.levels = 1; apply_all(o)
    shade_smooth(o)
    return h.skin(o)

def scarf_collar(h, name, mat, width=0.05, tails=0.2):
    """Checked scarf around the shoulders with two ends hanging down the front."""
    sh_z = h.rig.data.bones['upperarm_l'].head_local.z
    nx, ny, ncy = extent(h, h.neck.z - 0.01, 0.02, lambda d: d.startswith(('neck', 'spine_03', 'clavicle')))
    sx, sy, scy = extent(h, sh_z, 0.03, TORSO)
    bm = bmesh.new(); segs = 28
    rings = [(h.neck.z + 0.02, nx * 0.75 + 0.04, ny * 0.8 + 0.05, 0.0), (h.neck.z - 0.02, nx + 0.05, ny + 0.06, 0.4),
             (sh_z + 0.03, sx * 0.72, sy + 0.05, 0.8), (sh_z - 0.01, sx * 0.82, sy + 0.06, 1.0)]
    loops = []
    for z, rx, ry, t in rings:
        loops.append([bm.verts.new((rx * math.cos(th) * (1 + 0.04 * t * math.sin(5 * th)), scy + ry * math.sin(th), z - 0.03 * t * max(0, -math.sin(th))))
                      for th in (k / segs * math.tau for k in range(segs))])
    for A, B in zip(loops, loops[1:]):
        for k in range(segs): bm.faces.new((A[k], A[(k + 1) % segs], B[(k + 1) % segs], B[k]))
    front_y = scy - sy - 0.06
    for s in (1, -1):
        x0 = s * nx * 0.9
        pts = [Vector((x0, front_y + 0.01, h.neck.z - 0.02)), Vector((x0 + s * 0.01, front_y - 0.005, sh_z - 0.06)),
               Vector((x0 + s * 0.015, front_y - 0.015, sh_z - 0.06 - tails * 0.5)), Vector((x0 + s * 0.02, front_y - 0.02, sh_z - 0.06 - tails))]
        tube(bm, pts, lambda t: width * (0.5 + 0.15 * t), segs=8, flat=0.35, up=Vector((0, -1, 0)))
    o = bm_obj(bm, name, h.col, mat)
    bm2 = bmesh.new(); bm2.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm2, faces=bm2.faces); bm2.to_mesh(o.data); bm2.free()
    shade_smooth(o)
    return h.skin(o)

def agal(hf, name, col, mat, z=0.5, puff=0.1):
    bm = bmesh.new()
    for i, dz in enumerate((0.0, 0.12)):
        hx, hy, cy = head_width_at(hf.F, z + dz)
        ring_tube(bm, hf.w((0, cy, 0)), (hx + puff + 0.02) * hf.R, (hy + puff + 0.02) * hf.R, hf.w((0, 0, z + dz)).z, 0.045 * hf.R, tilt=0.04 * hf.R, segs=28, tsegs=6)
    return bm_obj(bm, name, col, mat)

# ---------------------------------------------------------------- props
def backpack(h, name, mat_bag, mat_strap, shirt):
    sh_z = h.rig.data.bones['upperarm_l'].head_local.z
    sx, sy, scy = extent(h, sh_z - 0.12, 0.04, TORSO)
    bvh = BVHTree.FromObject(shirt, bpy.context.evaluated_depsgraph_get())
    H = (sh_z - h.hip_z) * 0.72; zc = sh_z - 0.05 - H / 2
    backs = [shirt.matrix_world @ v.co for v in shirt.data.vertices if abs((shirt.matrix_world @ v.co).z - zc) < H / 2 and abs(v.co.x) < sx * 0.6]
    back_y = max(p.y for p in backs) + 0.004
    W, D = sx * 1.25, 0.1
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * W, back_y + D / 2 + v.co.y * D, zc + v.co.z * H))
    o = bm_obj(bm, name, h.col, mat_bag, smooth=False)
    bv = o.modifiers.new('b', 'BEVEL'); bv.width = 0.035; bv.segments = 3; apply_all(o)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * W * 1.02, back_y + D + 0.008 + v.co.y * 0.018, zc + H * 0.28 + v.co.z * H * 0.46))
    fl = bm_obj(bm, name + '_flap', h.col, mat_strap, smooth=False)
    bv = fl.modifiers.new('b', 'BEVEL'); bv.width = 0.008; bv.segments = 2; apply_all(fl)
    bm = bmesh.new()
    for s in (1, -1):
        x = s * sx * 0.45
        pts = [Vector((x, back_y + 0.03, zc + H * 0.42)), Vector((x, back_y, sh_z + 0.02)), Vector((x * 1.05, scy, sh_z + 0.12)),
               Vector((x * 1.1, scy - sy, sh_z + 0.03)), Vector((x * 1.2, scy - sy, sh_z - 0.08)), Vector((x * 1.4, scy - sy, sh_z - 0.16)),
               Vector((s * sx * 1.0, scy - sy * 0.2, sh_z - 0.22)), Vector((s * sx * 0.9, back_y - 0.02, zc - H * 0.3))]
        dense = []
        for a, b in zip(pts, pts[1:]):
            for k in range(3): dense.append(a.lerp(b, k / 3))
        dense.append(pts[-1])
        proj = []
        for i, p in enumerate(dense):
            if i < 2: proj.append(p); continue
            q, n, _, _ = bvh.find_nearest(p)
            proj.append(q + n * 0.012 if q else p)
        tube(bm, proj, 0.012, segs=6, flat=0.35, closed=True)
    st = bm_obj(bm, name + '_straps', h.col, mat_strap)
    for x in (o, fl): shade_smooth(x, 40)
    out = []
    for x in (o, fl): out.append(rigid_to(x, h.rig, 'spine_03'))
    out.append(h.skin(st))
    return out

# ---------------------------------------------------------------- seated lap skirt (Grandma Zainab)
def seated_skirt(h, name, mat, act, voxel=0.03, dec=0.3, puff=0.022):
    """A long dress on a seated woman: convex hull of the seated legs + hips (cloth falls from the
    lap over the knees to the ankles), remeshed smooth, moved back to rest space through the pelvis
    and bound rigidly to it (the seated clips keep the legs still)."""
    import bmesh
    rig = h.rig
    tmp = h.copy_ref('_seat_ref'); bind(tmp, rig)
    rig.animation_data.action = act; bpy.context.scene.frame_set(1); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg), depsgraph=dg)
    pts = [tmp.matrix_world @ v.co for i, v in enumerate(me.vertices) if h.dom[i].startswith(('thigh', 'calf', 'pelvis'))]
    bpy.data.objects.remove(tmp, do_unlink=True); bpy.data.meshes.remove(me)
    ankle = min(p.z for p in pts)
    bm = bmesh.new()
    for p in pts: bm.verts.new(p)
    for p in [p for p in pts if p.z < ankle + 0.07]: bm.verts.new((p.x * 1.18, p.y - 0.04, max(0.02, ankle - 0.02)))
    bmesh.ops.convex_hull(bm, input=bm.verts)
    o = bm_obj(bm, name, h.col, mat)
    rm = o.modifiers.new('r', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = voxel
    sm = o.modifiers.new('s', 'SMOOTH'); sm.factor = 1.0; sm.iterations = 6
    apply_all(o)
    inflate(o, lambda co, n: puff)
    dm = o.modifiers.new('d', 'DECIMATE'); dm.ratio = dec; apply_all(o)
    pb = rig.pose.bones['pelvis']
    o.data.transform(pb.bone.matrix_local @ pb.matrix.inverted())
    o.data.materials.clear(); o.data.materials.append(mat); shade_smooth(o)
    return rigid_to(o, rig, 'pelvis')

def staff(h, name, mat, act, length_up=0.42, r=0.016):
    rig = h.rig
    rig.animation_data.action = act; bpy.context.scene.frame_set(1); bpy.context.view_layer.update()
    pb = rig.pose.bones['hand_l']
    grip = (pb.head * 0.4 + rig.pose.bones['middle_01_l'].head * 0.6)
    bm = bmesh.new()
    pts = [Vector((grip.x + 0.004 * math.sin(i), grip.y, grip.z + length_up - (grip.z + length_up) * i / 8)) for i in range(9)]
    tube(bm, pts, lambda t: r * (1.25 if t < 0.08 else 1.0 - 0.15 * t), segs=8)
    o = bm_obj(bm, name, h.col, mat)
    o.data.transform(pb.bone.matrix_local @ pb.matrix.inverted())
    return rigid_to(o, rig, 'hand_l')

def glasses(hf, name, col, mat):
    F = hf.F; bm = bmesh.new()
    for s in (1, -1):
        p, n = head_surface(F, Vector((s * F['eye_x'], -1, F['eye_z'])).normalized())
        c = hf.w((s * F['eye_x'], p.y - 0.1, F['eye_z'] - 0.02))
        ring = [c + Vector((math.cos(a) * F['eye_w'] * 1.2, 0, math.sin(a) * F['eye_h'] * 1.25)) * hf.R for a in (k / 20 * math.tau for k in range(21))]
        tube(bm, ring, 0.007 * hf.R, segs=5, closed=False)
        # temple arm back to the ear
        tube(bm, [c + Vector((s * F['eye_w'] * 1.2 * hf.R, 0, 0)), hf.w((s * 0.9, 0.0, F['eye_z']))], 0.007 * hf.R, segs=5)
    tube(bm, [hf.w((0.1, -0.83, F['eye_z'] + 0.02)), hf.w((0, -0.86, F['eye_z'] + 0.05)), hf.w((-0.1, -0.83, F['eye_z'] + 0.02))], 0.007 * hf.R, segs=5)
    return bm_obj(bm, name, col, mat)
