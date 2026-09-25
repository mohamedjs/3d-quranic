# illustrations_asbab.py — 12 painted illustrations for the asbab-al-nuzul stories (2:187, 2:267, 2:189,
# 2:144, 59:9). Reuses the toolkit in illustrations.py (toon + haze materials, painted sky, compositor,
# WebP size loop). NO people / prophets / companions anywhere — only places, objects, light, animals.
# Background run (parallel-safe):  a driver that sets NAMES / PCT / FINAL then exec()s this file,
#   e.g. blender/v2/_jobs/g_<x>.py:  NAMES=['threads_dawn']; PCT=40; FINAL=False; exec(open(<this>).read())
# FINAL=True renders public/illustrations/<name>.webp (≤150 KB loop); SAVE=True writes illustrations_asbab.blend.
import bpy, bmesh, math, random, os
from mathutils import Vector, Matrix, Euler
exec(open('/var/www/html/old/3d-quranic/blender/illustrations/illustrations.py').read())
PREV = ROOT + '/blender/v2/previews/asbab/'
BLEND_A = ROOT + '/blender/illustrations/illustrations_asbab.blend'
BASE_P.update(levels=[(0.0, 0.03), (0.025, 0.22), (0.12, 0.55), (0.42, 1.0), (0.97, 1.25)], amb_col='#1c2036')

# ---------------------------------------------------------------- light-coloured toon (night / interiors)
def toonL(name, base, rim=0.8, nscale=1.5, namt=0.1, fog=1.0, gloss=0.0, amb=None, levels=None, emit=0.0):
    """Like toon() but the band colour keeps the HUE of the lights (warm lamp vs blue moon)."""
    m, fresh = _newmat(name)
    if not fresh: return m
    g = G(m.node_tree); geo = g.node('ShaderNodeNewGeometry')
    bcol = base(g, geo) if callable(base) else lin(base)[:3]
    dif = g.node('ShaderNodeBsdfDiffuse'); s2r = g.node('ShaderNodeShaderToRGB'); g.L.new(dif.outputs[0], s2r.inputs[0])
    L = s2r.outputs[0]
    bw = g.node('ShaderNodeRGBToBW'); g.L.new(L, bw.inputs[0]); bw = bw.outputs[0]
    q = g.ramp(bw, [(p, (v, v, v, 1)) for p, v in (levels or P['levels'])], 'CONSTANT')
    m1 = g.math('MAXIMUM', bw, 0.003)
    hue = g.vm('DIVIDE', L, g.comb(m1, m1, m1))
    hue = g.vm('MINIMUM', hue, (2.2, 2.2, 2.2))
    light = g.vm('MULTIPLY', hue, q)
    light = g.vm('ADD', light, lin(amb or P['amb_col'])[:3])
    col = g.vm('MULTIPLY', bcol, light)
    if namt > 0:
        nz = g.noise(geo.outputs['Position'], nscale, 4.0, 0.6)
        col = g.mix(1.0, col, g.mr(nz, 0.3, 0.7, 1 - namt, 1 + namt), 'MULTIPLY')
    if rim > 0:
        lw = g.node('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.3
        r = g.math('MULTIPLY', g.mr(lw.outputs['Facing'], 0.5, 0.85), g.mr(bw, 0.02, 0.2))
        rr = g.math('MULTIPLY', r, rim)
        col = g.vm('ADD', col, g.vm('MULTIPLY', g.vm('MULTIPLY', hue, bcol), g.comb(rr, rr, rr)))
    if gloss > 0:
        gl = g.node('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.22
        s2 = g.node('ShaderNodeShaderToRGB'); g.L.new(gl.outputs[0], s2.inputs[0])
        gb = g.node('ShaderNodeRGBToBW'); g.L.new(s2.outputs[0], gb.inputs[0])
        k = g.math('MULTIPLY', g.mr(gb.outputs[0], 0.35, 0.5), gloss)
        col = g.vm('ADD', col, g.vm('MULTIPLY', hue, g.comb(k, k, k)))
    if emit: col = g.vm('ADD', col, lin(emit if isinstance(emit, str) else '#ffffff')[:3])
    col = add_haze(g, geo, col, fog)
    em = g.node('ShaderNodeEmission'); g.put(em.inputs[0], col)
    out = g.node('ShaderNodeOutputMaterial'); g.L.new(em.outputs[0], out.inputs[0])
    return m

def glow(name, col, k=1.0, fog=0.0, alpha=None):
    return toon(name, col, flat=True, lit=lin(col, k), rim=0, namt=0, fog=fog, alpha=alpha)

def stripes(c1, c2, freq=40.0, axis=0, c3=None, freq2=None):
    """woven / striped procedural base colour"""
    def f(g, geo):
        p = g.sep(geo.outputs['Position'])
        s = g.math('SINE', g.math('MULTIPLY', p[axis], freq))
        c = g.mix(g.mr(s, -0.2, 0.2), lin(c1), lin(c2))
        if freq2:
            s2 = g.math('SINE', g.math('MULTIPLY', p[1 - axis if axis < 2 else 0], freq2))
            c = g.mix(g.math('MULTIPLY', g.mr(s2, 0.6, 1.0), 0.35), c, lin(c3 or '#000000'))
        return c
    return f

# ---------------------------------------------------------------- geometry helpers
def bevel(o, w=0.02, seg=2):
    m = o.modifiers.new('bev', 'BEVEL'); m.width = w; m.segments = seg; m.limit_method = 'ANGLE'; return o

def bx(name, loc, size, mat, bev=0.02, rot=(0, 0, 0), seg=2):
    bm = bmesh.new(); bm_cube(bm, Matrix.Diagonal(tuple(size) + (1,)))
    o = obj(name, mesh_bm(name, bm, mat, smooth=False)); o.location = loc; o.rotation_euler = rot
    if bev: bevel(o, bev, seg)
    return o

def cutter(name, loc, size, rot=(0, 0, 0), cyl=False):
    bm = bmesh.new()
    if cyl: bm_cone(bm, Matrix.Diagonal(tuple(size) + (1,)), 0.5, 0.5, 1.0, 32)
    else: bm_cube(bm, Matrix.Diagonal(tuple(size) + (1,)))
    o = obj(name, mesh_bm(name, bm, smooth=False)); o.location = loc; o.rotation_euler = rot
    o.hide_render = True; o.display_type = 'WIRE'; return o

def cut(o, cutters, bev=0.03):
    """boolean-subtract cutters, then round the edges"""
    for md in [m for m in o.modifiers if m.type == 'BEVEL']: o.modifiers.remove(md)
    for c in cutters:
        b = o.modifiers.new('cut_' + c.name, 'BOOLEAN'); b.operation = 'DIFFERENCE'; b.object = c; b.solver = 'EXACT'
    if bev: bevel(o, bev, 2)
    return o

def arch_hole(name, cx, y, z0, w, h, depth=1.0):
    """rectangular opening with a round top (window/door) as cutter objects, in a wall along X at y"""
    r = w / 2
    return [cutter(name + '_r', (cx, y, z0 + (h - r) / 2), (w, depth, h - r)),
            cutter(name + '_a', (cx, y, z0 + h - r), (w, depth, w), rot=(math.pi / 2, 0, 0), cyl=True)]

def lathe(bm, prof, seg=32, M=Matrix()):
    rings = []
    for (r, z) in prof:
        if r < 1e-6: rings.append([bm.verts.new(M @ Vector((0, 0, z)))])
        else: rings.append([bm.verts.new(M @ Vector((r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg), z))) for k in range(seg)])
    for a, b in zip(rings[:-1], rings[1:]):
        if len(a) == 1 and len(b) == 1: continue
        for k in range(seg):
            k1 = (k + 1) % seg
            if len(a) == 1: bm.faces.new((a[0], b[k], b[k1]))
            elif len(b) == 1: bm.faces.new((a[k], a[k1], b[0]))
            else: bm.faces.new((a[k], a[k1], b[k1], b[k]))

def lathe_obj(name, prof, mat, loc=(0, 0, 0), seg=32, scale=1.0, rot=(0, 0, 0)):
    bm = bmesh.new(); lathe(bm, prof, seg)
    o = obj(name, mesh_bm(name, bm, mat)); o.location = loc; o.scale = (scale,) * 3 if isinstance(scale, (int, float)) else scale
    o.rotation_euler = rot; return o

def plight(name, loc, col='#ffb060', energy=30, radius=0.05, shadow=True):
    ld = bpy.data.lights.new(name, 'POINT'); ld.energy = energy; ld.color = lin(col)[:3]; ld.shadow_soft_size = radius
    ld.use_shadow = shadow
    o = obj(name, ld); o.location = loc; return o

def spot(name, loc, target, col='#ffd08a', energy=300, size=0.6, blend=0.6, radius=0.3):
    ld = bpy.data.lights.new(name, 'SPOT'); ld.energy = energy; ld.color = lin(col)[:3]; ld.spot_size = size; ld.spot_blend = blend
    ld.shadow_soft_size = radius
    o = obj(name, ld); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o

def import_glb2(fname, mk=None, over=None):
    """import an env glb and convert each material to a painted toon of its base colour"""
    me = import_glb(fname, {})
    mk = mk or (lambda n, c: toon(n, c, rim=1.0))
    for i, m in enumerate(me.materials):
        if m is None or m.name.startswith(S().name + ':'): continue
        base = m.name.split('.')[0]
        if over and base in over:
            me.materials[i] = over[base]; continue
        c = (0.5, 0.5, 0.5, 1)
        if m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == 'BSDF_PRINCIPLED': c = tuple(n.inputs['Base Color'].default_value); break
        me.materials[i] = mk('g_' + base, tuple(c))
    return me

def stars(n, seed=1, dist=3000, zmin=0.12, zmax=0.95, size=4.0, col='#fff4d6', k=3.0, az=(-1.2, 1.2), cam=(0, 0, 0)):
    mat = glow('star', col, k)
    bm = bmesh.new(); rnd = random.Random(seed)
    for i in range(n):
        a = rnd.uniform(*az) + math.pi / 2; e = math.asin(rnd.uniform(zmin, zmax))
        d = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
        s = size * (rnd.uniform(0.5, 1.0) ** 2) * (1.6 if rnd.random() < 0.08 else 1.0)
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=s, matrix=Matrix.Translation(Vector(cam) + d * dist))
    return obj('stars', mesh_bm('stars', bm, mat))

def crescent(name, center, facing, R=1.0, d=0.42, rin=0.88, mat=None, roll=0.0):
    """flat crescent moon (ngon) at `center`, plane facing `facing` (towards camera)"""
    ca = (rin * rin - 1 - d * d) / (2 * d); al = math.acos(max(-1, min(1, ca)))
    p = Vector((math.cos(al), math.sin(al))); be = math.atan2(p.y, p.x + d)
    pts = [(math.cos(-al + 2 * al * i / 40), math.sin(-al + 2 * al * i / 40)) for i in range(41)]
    pts += [(-d + rin * math.cos(be - 2 * be * i / 40), rin * math.sin(be - 2 * be * i / 40)) for i in range(1, 40)]
    bm = bmesh.new(); vs = [bm.verts.new((x * R, 0, y * R)) for x, y in pts]; bm.faces.new(vs)
    o = obj(name, mesh_bm(name, bm, mat, smooth=False)); o.location = center
    f = Vector(facing).normalized()
    o.rotation_euler = (f.to_track_quat('-Y', 'Z').to_matrix().to_4x4() @ Matrix.Rotation(roll, 4, 'Y')).to_euler()
    return o

def tube(bm, pts, radii, seg=8, caps=True):
    """smooth swept tube along points (radius per point or constant)"""
    pts = [Vector(p) for p in pts]; n = len(pts); rings = []
    if isinstance(radii, (int, float)): radii = [radii] * n
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        R = t.to_track_quat('Z', 'Y').to_matrix(); r = radii[i]
        rings.append([bm.verts.new(p + R @ Vector((r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg), 0))) for k in range(seg)])
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(seg): bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    if caps:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])

def ellip(bm, c, s, seg=10, rings=7, rot=(0, 0, 0)):
    bm_sphere(bm, TRS(c, rot, s), seg, rings)

# ---- small props
def oil_lamp(name, loc, clay, flame=None, rot=0.0, lit=True, s=1.0):
    """clay oil lamp (siraj) with spout toward +X; flame optional. returns wick tip world position"""
    root = link(bpy.data.objects.new(name, None)); root.location = loc; root.rotation_euler = (0, 0, rot); root.scale = (s,) * 3
    bm = bmesh.new()
    lathe(bm, [(0, 0), (0.035, 0.0), (0.052, 0.012), (0.056, 0.024), (0.045, 0.036), (0.022, 0.04), (0.016, 0.046), (0.02, 0.05), (0.012, 0.05), (0, 0.04)], 24)
    ellip(bm, (0.06, 0, 0.026), (0.045, 0.02, 0.013), 16, 8)
    bm_cone(bm, seg_matrix((0.085, 0, 0.028), (0.103, 0, 0.036)), 0.012, 0.009, 1.0, 10)
    bm_seg(bm, (-0.05, 0, 0.03), (-0.075, 0, 0.042), 0.009, 0.008, 8)
    o = obj(name + '_body', mesh_bm(name + '_body', bm, clay)); o.parent = root
    tip = Vector((0.104, 0, 0.038))
    if lit and flame:
        bm = bmesh.new(); lathe(bm, [(0, 0), (0.007, 0.004), (0.0095, 0.013), (0.0075, 0.024), (0.003, 0.034), (0, 0.042)], 16)
        f = obj(name + '_flame', mesh_bm(name + '_flame', bm, flame)); f.parent = root; f.location = tip + Vector((0, 0, -0.002)); f.scale = (1.3, 1.3, 1.3)
    bpy.context.view_layer.update()
    return root.matrix_world @ tip

def jug(name, loc, mat, s=1.0, rot=0.0):
    bm = bmesh.new()
    prof = [(0, 0), (0.06, 0), (0.085, 0.02), (0.11, 0.08), (0.115, 0.14), (0.095, 0.2), (0.058, 0.245), (0.042, 0.275), (0.041, 0.3), (0.054, 0.32), (0.05, 0.328), (0.036, 0.31), (0.03, 0.26)]
    lathe(bm, prof, 28)
    pts = [Vector((0.045, 0, 0.29)), Vector((0.12, 0, 0.3)), Vector((0.15, 0, 0.22)), Vector((0.11, 0, 0.15))]
    for i in range(3):
        for k in range(4):
            a = bez(*pts, (i * 4 + k) / 12); b = bez(*pts, (i * 4 + k + 1) / 12); bm_seg(bm, a, b, 0.013, 0.013, 8)
    o = obj(name, mesh_bm(name, bm, mat)); o.location = loc; o.scale = (s,) * 3; o.rotation_euler = (0, 0, rot); return o

def bowl(name, loc, mat, r=0.12, h=0.06, s=1.0):
    prof = [(0, 0), (r * 0.45, 0), (r * 0.5, h * 0.12), (r * 0.85, h * 0.45), (r, h), (r * 0.94, h * 1.02), (r * 0.8, h * 0.55), (r * 0.4, h * 0.2), (0, h * 0.18)]
    return lathe_obj(name, prof, mat, loc, 32, s)

def dates_heap(name, mat, center, rad, n, rnd, top=0.05, size=(0.011, 0.011, 0.017), dry=False, zf=None):
    bm = bmesh.new()
    for i in range(n):
        a = rnd.uniform(0, 2 * math.pi); r = rad * math.sqrt(rnd.random())
        z = top * (1 - (r / rad) ** 2) + rnd.uniform(0, 0.012)
        if zf: z = zf(r)
        sc = [x * rnd.uniform(0.85, 1.12) for x in size]
        if dry: sc = [sc[0] * rnd.uniform(0.6, 0.85), sc[1] * rnd.uniform(0.55, 0.8), sc[2] * rnd.uniform(0.7, 0.95)]
        st = len(bm.verts)
        ellip(bm, (center[0] + math.cos(a) * r, center[1] + math.sin(a) * r, center[2] + z), sc, 10, 7,
              (rnd.uniform(0.9, 2.2), rnd.uniform(-0.5, 0.5), rnd.uniform(0, 6.3)))
        if dry:  # wrinkles
            bm.verts.ensure_lookup_table()
            for v in bm.verts[st:]:
                c = Vector((center[0] + math.cos(a) * r, center[1] + math.sin(a) * r, center[2] + z))
                dvec = v.co - c; v.co = c + dvec * (1 + 0.35 * noise.noise(v.co * 260 + Vector((i, 0, 0))))
    return obj(name, mesh_bm(name, bm, mat))

def bread(name, loc, mat, r=0.1, s=1.0, seed=0):
    bm = bmesh.new(); ellip(bm, (0, 0, 0), (r, r, r * 0.22), 24, 10)
    for v in bm.verts: v.co.z += 0.004 * noise.noise(v.co * 40 + Vector((seed, 0, 0)))
    o = obj(name, mesh_bm(name, bm, mat)); o.location = loc; o.scale = (s,) * 3; return o

def cushion(name, loc, size, mat, rot=0.0):
    bm = bmesh.new(); bm_cube(bm, Matrix.Diagonal(tuple(size) + (1,)))
    o = obj(name, mesh_bm(name, bm, mat)); o.location = loc; o.rotation_euler = (0, 0, rot)
    bevel(o, min(size) * 0.45, 4); sd = o.modifiers.new('sub', 'SUBSURF'); sd.levels = 2; sd.render_levels = 2
    return o

def sparrow(name, mat_body, mat_belly, mat_dark, loc, rot=0.0, s=1.0, peck=0.0):
    """small sitting sparrow ~14 cm facing +X"""
    root = link(bpy.data.objects.new(name, None)); root.location = loc; root.rotation_euler = (0, 0, rot); root.scale = (s,) * 3
    bm = bmesh.new()
    ellip(bm, (0, 0, 0.045), (0.06, 0.035, 0.035), 14, 10, (0, -0.35, 0))
    ellip(bm, (0.05, 0, 0.078 - peck), (0.03, 0.028, 0.028), 12, 8)
    bm_cone(bm, seg_matrix((-0.04, 0, 0.055), (-0.1, 0, 0.075)), 0.018, 0.012, 1.0, 8)
    ellip(bm, (-0.005, 0.026, 0.05), (0.045, 0.012, 0.022), 10, 6, (0, -0.3, 0))
    ellip(bm, (-0.005, -0.026, 0.05), (0.045, 0.012, 0.022), 10, 6, (0, -0.3, 0))
    obj(name + '_b', mesh_bm(name + '_b', bm, mat_body)).parent = root
    bm = bmesh.new(); ellip(bm, (0.025, 0, 0.035), (0.04, 0.03, 0.026), 12, 8)
    ellip(bm, (0.07, 0, 0.072 - peck), (0.012, 0.022, 0.012), 8, 6)
    obj(name + '_w', mesh_bm(name + '_w', bm, mat_belly)).parent = root
    bm = bmesh.new()
    bm_cone(bm, seg_matrix((0.075, 0, 0.078 - peck), (0.095, 0, 0.074 - peck)), 0.008, 0.0, 1.0, 6)
    for sg in (1, -1):
        ellip(bm, (0.066, sg * 0.018, 0.085 - peck), (0.006, 0.004, 0.006), 6, 4)
        bm_seg(bm, (0.01, sg * 0.01, 0.02), (0.015, sg * 0.01, -0.005), 0.003, 0.003, 4)
    obj(name + '_d', mesh_bm(name + '_d', bm, mat_dark)).parent = root
    return root

def palm_trunk(name, a, b, r, mat, rings=True):
    """palm-trunk pillar / beam with ring bumps"""
    bm = bmesh.new(); a, b = Vector(a), Vector(b); L = (b - a).length; n = int(L / 0.11) if rings else 1
    for i in range(n):
        p0 = a.lerp(b, i / n); p1 = a.lerp(b, (i + 1) / n)
        bm_cone(bm, seg_matrix(p0, p1), r * 1.06, r * 0.94, 1.0, 12)
    return obj(name, mesh_bm(name, bm, mat))

def fronds_roof(name, x0, x1, y0, y1, z, mat, rnd, n=None, gap=0.0):
    """thatch of palm fronds (jareed) laid across beams"""
    bm = bmesh.new(); n = n or int((x1 - x0) / 0.09)
    for i in range(n):
        if gap and rnd.random() < gap: continue
        x = x0 + (x1 - x0) * (i + rnd.uniform(-0.3, 0.3)) / n
        bm_seg(bm, (x, y0 + rnd.uniform(-0.1, 0.1), z + rnd.uniform(0, 0.03)), (x + rnd.uniform(-0.1, 0.1), y1 + rnd.uniform(-0.1, 0.1), z + rnd.uniform(0, 0.03)), 0.028, 0.022, 5)
        for k in range(10):  # leaflets hanging at the edges
            if rnd.random() < 0.5: continue
            yy = rnd.choice((y0, y1)); t = rnd.uniform(0, 1)
            p = Vector((x + rnd.uniform(-0.05, 0.05), yy + (0.02 if yy == y1 else -0.02), z))
            q = p + Vector((rnd.uniform(-0.15, 0.15), (0.12 if yy == y1 else -0.12) * rnd.uniform(0.3, 1), -rnd.uniform(0.15, 0.4)))
            bm_seg(bm, p, q, 0.012, 0.003, 4)
    return obj(name, mesh_bm(name, bm, mat, smooth=False))

def ground_plane(name, mat, x0=-80, x1=80, y0=-10, y1=300, amp=0.0, nx=60, ny=60, seed=1, fz=None):
    return heightfield(name, x0, x1, y0, y1, nx, ny, fz or (lambda x, y: amp * (fbm(x / 20, y / 20, 3, seed) - 0.5)), mat)

def scatter_palms(meshes, rnd, n, xr, yr, sc=(1.0, 1.4), zf=lambda x, y: 0.0, avoid=None, prefix='palm'):
    for i in range(n):
        x = rnd.uniform(*xr); y = rnd.uniform(*yr)
        if avoid and avoid(x, y): continue
        inst('%s%d' % (prefix, i), meshes[i % len(meshes)], (x, y, zf(x, y) - 0.2), (0, 0, rnd.uniform(0, 6.3)), rnd.uniform(*sc))

def night_P(**kw):
    P.update(sun=(0.35, 1.0, 0.35), sun_r=0.02, disc='#dfe6ff', disc_str=1.2, core='#c8d4ff', core_amt=0.0, glow='#8a9ad0', glow_amt=0.25, glow_pow=8.0,
             sky=[(-0.12, '#10142c'), (0.0, '#3a4a7a'), (0.05, '#2a3868'), (0.2, '#1a2452'), (0.5, '#10183c'), (0.9, '#0a0f2a')],
             clouds=0.0, fog=1 / 400, fog_ground=1.0, fog_h=6.0, lit=(0.62, 0.72, 1.05), shadow=(0.2, 0.22, 0.36), shade='#0e1024', shade_mix=0.3,
             rim='#9fb4ff', rim_amt=0.9, sun_str=0.6, amb=0.08, bloom=0.8, bloom_thr=0.8, beams=0.0, kuwa=4, vign=0.6, vig_col='#05060f',
             lift=(1.0, 1.0, 1.02), gain=(1.02, 1.0, 1.0), amb_col='#141a34')
    P.update(kw)

SC_A = {}
def scene_a(fn): SC_A[fn.__name__.replace('sc_', '', 1)] = fn; return fn
exec(open(ROOT + '/blender/illustrations/illustrations_asbab_scenes.py').read())

def preview(name, pct):
    sc = S(); compositor(sun_screen()); os.makedirs(PREV, exist_ok=True)
    sc.render.resolution_percentage = pct
    ims = sc.render.image_settings; ims.file_format = 'JPEG'; ims.quality = 90; ims.color_mode = 'RGB'
    sc.render.filepath = PREV + name + '.jpg'
    bpy.ops.render.render(write_still=True, scene=sc.name); print('PREVIEW', name, sc.render.filepath)

def run_a(name, pct=40, final=False):
    global P
    P = dict(BASE_P); new_scene(name); random.seed(7)
    SC_A[name]()
    build_world(); sl = sun_lamp()
    if P.get('sun_col'): sl.data.color = lin(P['sun_col'])[:3]
    if final: return render(name, 100)
    if pct: preview(name, pct)

if 'NAMES' in globals():
    for _n in NAMES:
        try:
            print('RESULT', _n, run_a(_n, globals().get('PCT', 40), globals().get('FINAL', False)), flush=True)
        except Exception:
            import traceback; traceback.print_exc(); print('FAILED', _n, flush=True)
    if globals().get('SAVE'):
        for s in [s for s in bpy.data.scenes if s.name not in SC_A]:
            if len(bpy.data.scenes) > 1: bpy.data.scenes.remove(s)
        bpy.ops.wm.save_as_mainfile(filepath=BLEND_A)
        print('SAVED', BLEND_A)
