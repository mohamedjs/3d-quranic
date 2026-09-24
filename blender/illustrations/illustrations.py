# illustrations.py — painterly story illustrations for the 2D story cards.
# EEVEE + hand-built "toon + haze" materials (Shader-to-RGB bands, rim light, depth/height fog
# that fades into the sky colour) + compositor (Kuwahara paint, bloom, sun beams, grade, vignette).
# Rerun through the bridge:
#   exec(open('/var/www/html/old/3d-quranic/blender/illustrations/illustrations.py').read()); run('army')
#   ... run_all(); save_blend()
# Every illustration lives in its own Blender scene inside scene/illustrations.blend.
import bpy, bmesh, math, random, os, time
from mathutils import Vector, Matrix, Euler, Quaternion, noise
from bpy_extras.object_utils import world_to_camera_view

ROOT = '/var/www/html/old/3d-quranic'
OUT = ROOT + '/public/illustrations'
BLEND = ROOT + '/blender/illustrations/illustrations.blend'
ENV = ROOT + '/public/models/env/'
MAXB = 150_000
RES = (1600, 900)

# ---------------------------------------------------------------- colour
def lin(h, k=1.0):
    if not isinstance(h, str): return tuple(x * k for x in h[:3]) + (1.0,)
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(k * ((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (1.0,)
def cmul(c, t): return tuple(c[i] * t[i] for i in range(3)) + (1.0,)
def cmix(a, b, f): return tuple(a[i] * (1 - f) + b[i] * f for i in range(3)) + (1.0,)

# ---------------------------------------------------------------- node graph helper
class G:
    def __init__(s, nt): s.nt = nt; s.N = nt.nodes; s.L = nt.links
    def put(s, sock, v):
        if isinstance(v, bpy.types.NodeSocket): s.L.new(v, sock)
        elif v is not None: sock.default_value = v
    def node(s, t, **kw):
        n = s.N.new(t)
        for k, v in kw.items(): setattr(n, k, v)
        return n
    def math(s, op, a, b=0.0, clamp=False):
        n = s.node('ShaderNodeMath', operation=op, use_clamp=clamp); s.put(n.inputs[0], a); s.put(n.inputs[1], b); return n.outputs[0]
    def vm(s, op, a, b=None):
        n = s.node('ShaderNodeVectorMath', operation=op); s.put(n.inputs[0], a)
        if b is not None: s.put(n.inputs[1], b)
        return n.outputs['Value'] if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else n.outputs['Vector']
    def mix(s, f, a, b, blend='MIX'):
        n = s.node('ShaderNodeMix', data_type='RGBA', blend_type=blend); n.clamp_factor = True
        s.put(n.inputs[0], f); s.put(n.inputs[6], a); s.put(n.inputs[7], b); return n.outputs[2]
    def mr(s, v, a, b, c=0.0, d=1.0, clamp=True, interp='LINEAR'):
        n = s.node('ShaderNodeMapRange', clamp=clamp, interpolation_type=interp)
        s.put(n.inputs['Value'], v)
        for k, x in zip(('From Min', 'From Max', 'To Min', 'To Max'), (a, b, c, d)): s.put(n.inputs[k], x)
        return n.outputs['Result']
    def ramp(s, f, stops, interp='LINEAR'):
        n = s.node('ShaderNodeValToRGB'); cr = n.color_ramp; cr.interpolation = interp
        while len(cr.elements) < len(stops): cr.elements.new(0.5)
        for e, (p, c) in zip(cr.elements, stops):
            e.position = p; e.color = lin(c) if isinstance(c, str) else (tuple(c) if len(c) == 4 else tuple(c) + (1,))
        s.put(n.inputs[0], f); return n.outputs[0]
    def sep(s, v):
        n = s.node('ShaderNodeSeparateXYZ'); s.put(n.inputs[0], v); return n.outputs[0], n.outputs[1], n.outputs[2]
    def comb(s, x, y, z):
        n = s.node('ShaderNodeCombineXYZ')
        for i, v in enumerate((x, y, z)): s.put(n.inputs[i], v)
        return n.outputs[0]
    def noise(s, vec, scale, detail=3.0, rough=0.55):
        n = s.node('ShaderNodeTexNoise'); s.put(n.inputs['Vector'], vec); n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = rough; return n.outputs['Fac']

# ---------------------------------------------------------------- scene params
BASE_P = dict(
    sun=(-0.3, 1.0, 0.07), sun_r=0.03,
    sky=[(-0.12, '#e9b27a'), (0.0, '#f8d49a'), (0.07, '#f2b86b'), (0.22, '#d98f72'), (0.5, '#8f8fb0'), (0.9, '#5a5f8f')],
    glow='#ffd489', glow_pow=5.0, glow_amt=0.75, core='#fff0c4', core_pow=70.0, core_amt=0.95, disc='#fff8e0', disc_str=5.0,
    clouds=0.0, cloud_lit='#ffd9a0', cloud_dark='#b27a86', cloud_scale=1.3, cloud_cov=0.55, cloud_z=0.18,
    fog=1 / 700, fog_ground=2.5, fog_h=10.0, fog_max=0.97, haze_z=0.03,
    lit=(1.18, 1.0, 0.8), shadow=(0.46, 0.34, 0.33), shade='#3a2420', shade_mix=0.3, bands=(0.14, 0.42),
    rim='#ffc76e', rim_amt=1.4, sun_str=3.0, amb=0.25,
    bloom=0.5, bloom_thr=0.85, beams=0.18, kuwa=5, vign=0.55, vig_col='#2b1a10',
    lift=(1.02, 1.0, 0.99), gamma=(1.0, 1.0, 1.0), gain=(1.05, 1.0, 0.94), sat=1.0,
)
P = dict(BASE_P)

def sunv(): return Vector(P['sun']).normalized()

def sky_nodes(g, d, disc=True, zclamp=None, clouds=True):
    """Painted sky colour for direction d (normalized) — also used as the haze colour."""
    x, y, z = g.sep(d)
    if zclamp is not None:
        z = g.math('MINIMUM', g.math('MAXIMUM', z, -0.02), zclamp)
        d = g.vm('NORMALIZE', g.comb(x, y, z))
    e = g.mr(z, -0.12, 0.9)
    col = g.ramp(e, [((el + 0.12) / 1.02, c) for el, c in P['sky']])
    s = g.math('MAXIMUM', g.vm('DOT_PRODUCT', d, tuple(sunv())), 0.0)
    if clouds and P['clouds'] > 0 and zclamp is None:
        # stylized cloud banks: noise on a plane above, lit near the sun, banded
        k = g.math('ADD', z, P['cloud_z'] * 0.35)
        n0 = g.node('ShaderNodeVectorMath', operation='SCALE')
        g.put(n0.inputs[0], g.comb(g.math('DIVIDE', x, k), g.math('DIVIDE', y, k), 0.3)); n0.inputs['Scale'].default_value = P['cloud_scale']
        stretch = g.vm('MULTIPLY', n0.outputs['Vector'], (0.35, 1.0, 1.0))
        nf = g.noise(stretch, 1.0, 5.0, 0.6)
        m = g.mr(nf, P['cloud_cov'], P['cloud_cov'] + 0.08)
        m = g.math('MULTIPLY', m, g.mr(z, -0.01, 0.12))
        m = g.math('MULTIPLY', m, g.mr(z, 0.75, 0.35))
        m = g.math('MULTIPLY', m, P['clouds'])
        shadef = g.mr(nf, P['cloud_cov'] + 0.05, P['cloud_cov'] + 0.2)
        ccol = g.mix(g.math('MULTIPLY', g.math('POWER', s, 3.0), 1.4), lin(P['cloud_dark']), lin(P['cloud_lit']))
        ccol = g.mix(g.math('MULTIPLY', shadef, 0.45), ccol, g.mix(0.5, lin(P['cloud_dark']), col))
        col = g.mix(m, col, ccol)
    w = g.math('MULTIPLY', g.math('POWER', s, P['glow_pow']), P['glow_amt'])
    col = g.mix(w, col, lin(P['glow']))
    w2 = g.math('MULTIPLY', g.math('POWER', s, P['core_pow']), P['core_amt'])
    col = g.mix(w2, col, lin(P['core']))
    if disc:
        c0 = math.cos(P['sun_r']); c1 = math.cos(P['sun_r'] * 0.85)
        dd = g.mr(s, c0, c1)
        col = g.mix(dd, col, lin(P['disc'], P['disc_str']))
    return col

def build_world():
    w = bpy.data.worlds.new('W_' + S().name); S().world = w; w.use_nodes = True
    g = G(w.node_tree); g.N.clear()
    tc = g.node('ShaderNodeTexCoord')
    d = g.vm('NORMALIZE', tc.outputs['Generated'])
    col = sky_nodes(g, d)
    lp = g.node('ShaderNodeLightPath')
    bg = g.node('ShaderNodeBackground'); g.put(bg.inputs[0], col)
    bg2 = g.node('ShaderNodeBackground'); g.put(bg2.inputs[0], col); bg2.inputs[1].default_value = P['amb']
    ms = g.node('ShaderNodeMixShader'); g.put(ms.inputs[0], lp.outputs['Is Camera Ray'])
    g.L.new(bg2.outputs[0], ms.inputs[1]); g.L.new(bg.outputs[0], ms.inputs[2])
    out = g.node('ShaderNodeOutputWorld'); g.L.new(ms.outputs[0], out.inputs[0])

# ---------------------------------------------------------------- materials
def _newmat(name):
    key = S().name + ':' + name
    m = bpy.data.materials.get(key)
    if m: return m, False
    m = bpy.data.materials.new(key); m.use_nodes = True; m.node_tree.nodes.clear(); return m, True

def toon(name, base, rim=1.0, nscale=1.5, namt=0.12, fog=1.0, lit=None, shadow=None, emit=0.0, flat=False, alpha=None, bands=None):
    """Painterly toon: diffuse -> Shader-to-RGB -> bands -> shadow/lit colours, brush noise, rim, haze."""
    m, fresh = _newmat(name)
    if not fresh: return m
    g = G(m.node_tree)
    geo = g.node('ShaderNodeNewGeometry')
    if callable(base):  # procedural base colour (e.g. patchwork fields)
        bn = base(g, geo)
        litc = g.mix(1.0, bn, tuple(P['lit']) + (1,), 'MULTIPLY')
        shc = g.mix(P['shade_mix'], g.mix(1.0, bn, tuple(P['shadow']) + (1,), 'MULTIPLY'), lin(P['shade']))
    else:
        b = lin(base)
        litc = lin(lit) if lit else cmul(b, P['lit'])
        shc = lin(shadow) if shadow else cmix(cmul(b, P['shadow']), lin(P['shade']), P['shade_mix'])
    if flat:
        col = litc
    else:
        dif = g.node('ShaderNodeBsdfDiffuse'); s2r = g.node('ShaderNodeShaderToRGB'); g.L.new(dif.outputs[0], s2r.inputs[0])
        bw = g.node('ShaderNodeRGBToBW'); g.L.new(s2r.outputs[0], bw.inputs[0])
        b1, b2 = bands or P['bands']
        t = g.ramp(bw.outputs[0], [(0, '#000000'), (b1, '#000000'), (b1 + 0.04, '#6b6b6b'), (b2, '#6b6b6b'), (b2 + 0.05, '#ffffff')])
        col = g.mix(t, shc, litc)
    if namt > 0:
        nz = g.noise(geo.outputs['Position'], nscale, 4.0, 0.6)
        col = g.mix(1.0, col, g.mr(nz, 0.3, 0.7, 1 - namt, 1 + namt), 'MULTIPLY')
    if rim > 0:
        lw = g.node('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.3
        r = g.mr(lw.outputs['Facing'], 0.55, 0.85)
        bl = g.mr(g.vm('DOT_PRODUCT', geo.outputs['Normal'], tuple(sunv())), -0.4, 0.5, 0.1, 1.0)
        col = g.mix(g.math('MULTIPLY', g.math('MULTIPLY', r, bl), rim * P['rim_amt']), col, lin(P['rim']), 'ADD')
    if emit: col = g.mix(1.0, col, (emit, emit, emit, 1), 'MULTIPLY')
    col = add_haze(g, geo, col, fog)
    em = g.node('ShaderNodeEmission'); g.put(em.inputs[0], col)
    out = g.node('ShaderNodeOutputMaterial')
    if alpha is not None:
        tr = g.node('ShaderNodeBsdfTransparent'); ms = g.node('ShaderNodeMixShader')
        g.put(ms.inputs[0], alpha(g, geo) if callable(alpha) else alpha); g.L.new(tr.outputs[0], ms.inputs[1]); g.L.new(em.outputs[0], ms.inputs[2])
        g.L.new(ms.outputs[0], out.inputs[0]); m.surface_render_method = 'BLENDED'
    else:
        g.L.new(em.outputs[0], out.inputs[0])
    return m

def add_haze(g, geo, col, fogk=1.0):
    """Depth + ground-height haze towards the sky colour seen in that direction (atmospheric perspective)."""
    if fogk <= 0: return col
    cd = g.node('ShaderNodeCameraData')
    dist = cd.outputs['View Distance']
    z = g.sep(geo.outputs['Position'])[2]
    hg = g.math('ADD', 1.0, g.math('MULTIPLY', P['fog_ground'], g.math('EXPONENT', g.math('DIVIDE', g.math('MAXIMUM', z, 0.0), -P['fog_h']))))
    f = g.math('SUBTRACT', 1.0, g.math('EXPONENT', g.math('MULTIPLY', g.math('MULTIPLY', dist, P['fog'] * fogk), g.math('MULTIPLY', hg, -1.0))))
    f = g.math('MINIMUM', f, P['fog_max'])
    d = g.vm('NORMALIZE', g.vm('MULTIPLY', geo.outputs['Incoming'], (-1, -1, -1)))
    hc = sky_nodes(g, d, disc=False, zclamp=P['haze_z'])
    return g.mix(f, col, hc)

def water_mat(name, tint='#7c8fb5', dark=0.3, fog=1.0):
    m, fresh = _newmat(name)
    if not fresh: return m
    g = G(m.node_tree)
    geo = g.node('ShaderNodeNewGeometry')
    d = g.vm('NORMALIZE', g.vm('MULTIPLY', geo.outputs['Incoming'], (-1, -1, -1)))
    x, y, z = g.sep(d)
    nz = g.noise(g.vm('MULTIPLY', geo.outputs['Position'], (0.25, 1.2, 1.0)), 0.8, 3.0, 0.5)
    rz = g.math('ADD', g.math('ABSOLUTE', z), g.math('MULTIPLY', g.math('SUBTRACT', nz, 0.5), 0.06))
    rd = g.vm('NORMALIZE', g.comb(x, y, rz))
    col = sky_nodes(g, rd, disc=False, clouds=False)
    col = g.mix(dark, col, lin(tint, 0.6))
    sp = g.mr(nz, 0.6, 0.68)
    s = g.math('POWER', g.math('MAXIMUM', g.vm('DOT_PRODUCT', rd, tuple(sunv())), 0), 20.0)
    col = g.mix(g.math('MULTIPLY', sp, s), col, lin(P['core'], 2.5))
    col = add_haze(g, geo, col, fog)
    em = g.node('ShaderNodeEmission'); g.put(em.inputs[0], col)
    out = g.node('ShaderNodeOutputMaterial'); g.L.new(em.outputs[0], out.inputs[0])
    return m

def dust_mat(name, col='#e8b27a', amt=0.55, fog=0.6):
    def a(g, geo):
        lw = g.node('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
        f = g.math('SUBTRACT', 1.0, lw.outputs['Facing'])
        nz = g.noise(geo.outputs['Position'], 0.35, 3.0, 0.6)
        return g.math('MULTIPLY', g.math('MULTIPLY', g.math('POWER', f, 1.6), g.mr(nz, 0.35, 0.65, 0.4, 1.0)), amt)
    return toon(name, col, rim=0.6, namt=0.05, fog=fog, alpha=a, lit=col, shadow=col)

# ---------------------------------------------------------------- scene / objects
_S = [None]
def S(): return _S[0]

def new_scene(name):
    win = bpy.context.window_manager.windows[0]
    tmp = bpy.data.scenes.get('_tmp') or bpy.data.scenes.new('_tmp')
    win.scene = tmp
    old = bpy.data.scenes.get(name)
    if old:
        for o in list(old.collection.all_objects): bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.scenes.remove(old)
    for m in [m for m in bpy.data.materials if m.name.startswith(name + ':')]: bpy.data.materials.remove(m)
    for n in [n for n in bpy.data.node_groups if n.name == 'Comp_' + name]: bpy.data.node_groups.remove(n)
    bpy.data.orphans_purge(do_recursive=True)
    sc = bpy.data.scenes.new(name); _S[0] = sc; win.scene = sc
    bpy.data.scenes.remove(tmp)
    for s in [s for s in bpy.data.scenes if s.name in ('Scene',) and not s.objects]: bpy.data.scenes.remove(s)
    r = sc.render; r.engine = 'BLENDER_EEVEE'; r.resolution_x, r.resolution_y = RES; r.resolution_percentage = 100
    r.film_transparent = False
    sc.eevee.taa_render_samples = 48; sc.eevee.use_raytracing = False; sc.eevee.use_shadows = True
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    return sc

def link(o): S().collection.objects.link(o); return o
def obj(name, me): return link(bpy.data.objects.new(name, me))

def mesh_bm(name, bm, mat=None, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    if mat:
        for m in (mat if isinstance(mat, (list, tuple)) else [mat]): me.materials.append(m)
    return me

def inst(name, me, loc, rot=(0, 0, 0), scale=1.0):
    o = obj(name, me); o.location = loc; o.rotation_euler = rot
    o.scale = (scale,) * 3 if isinstance(scale, (int, float)) else scale
    return o

def camera(loc, target, lens=35, shift=(0, 0)):
    cd = bpy.data.cameras.new('Cam'); cd.lens = lens; cd.clip_start = 0.1; cd.clip_end = 30000
    cd.shift_x, cd.shift_y = shift
    c = obj('Cam', cd); c.location = loc
    c.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    S().camera = c; return c

def sun_lamp(strength=None, angle=3.0):
    ld = bpy.data.lights.new('Sun', 'SUN'); ld.energy = strength or P['sun_str']; ld.angle = math.radians(angle)
    ld.color = (1, 1, 1)
    o = obj('Sun', ld); o.rotation_euler = sunv().to_track_quat('Z', 'Y').to_euler(); return o

# ---- primitive bmesh builders (each adds into a bmesh through a matrix)
def bm_sphere(bm, m, seg=16, rings=10, r=1.0):
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r, matrix=m)
def bm_cone(bm, m, r1, r2, depth, seg=12, caps=True):
    bmesh.ops.create_cone(bm, cap_ends=caps, segments=seg, radius1=r1, radius2=r2, depth=depth, matrix=m)
def bm_cube(bm, m, size=1.0):
    bmesh.ops.create_cube(bm, size=size, matrix=m)
def TRS(t=(0, 0, 0), r=(0, 0, 0), s=(1, 1, 1)):
    return Matrix.Translation(t) @ Euler(r).to_matrix().to_4x4() @ Matrix.Diagonal(tuple(s) + (1,))
def seg_matrix(a, b):
    """matrix placing a unit-depth z-aligned cylinder/cone from a to b"""
    a, b = Vector(a), Vector(b); d = b - a
    q = d.normalized().to_track_quat('Z', 'Y')
    return Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((1, 1, d.length, 1))
def bm_seg(bm, a, b, r1, r2=None, seg=8):
    bm_cone(bm, seg_matrix(a, b), r1, r2 if r2 is not None else r1, 1.0, seg)
def bm_matidx(bm, idx, start):
    """set material idx on faces created after `start` (a len(bm.faces) snapshot or a set of old faces)"""
    if isinstance(start, set):
        for f in bm.faces:
            if f not in start: f.material_index = idx
        return
    bm.faces.index_update()
    for f in bm.faces:
        if f.index >= start: f.material_index = idx

# ---------------------------------------------------------------- terrain
def fbm(x, y, oct=5, seed=0, ridged=False):
    a, f, s, n = 1.0, 1.0, 0.0, 0.0
    for i in range(oct):
        v = noise.noise(Vector((x * f + seed * 13.1, y * f - seed * 7.7, seed * 3.3 + i * 1.7)))
        if ridged: v = 1 - abs(v); v = v * v
        else: v = v * 0.5 + 0.5
        s += v * a; n += a; a *= 0.5; f *= 2.02
    return s / n

def heightfield(name, x0, x1, y0, y1, nx, ny, fz, mat, smooth=True):
    bm = bmesh.new(); vs = []
    for j in range(ny + 1):
        y = y0 + (y1 - y0) * j / ny
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            vs.append(bm.verts.new((x, y, fz(x, y))))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            bm.faces.new((vs[a], vs[a + 1], vs[a + nx + 2], vs[a + nx + 1]))
    return obj(name, mesh_bm(name, bm, mat, smooth))

def ridge(name, y, width, depth, height, mat, seed=0, x0=0.0, sharp=True, nx=160, ny=24, freq=3.0, base=0.35, peaks=None, rough=0.12, taper=True):
    """A mountain range band centred at x0; front foot at y, crest about depth/2 behind."""
    def fz(x, yy):
        u = (x - x0) / width; v = (yy - y) / depth
        crest = fbm(u * freq, 0.3, 6, seed, ridged=sharp)
        crest = base + (1 - base) * crest
        if peaks:
            for (px, pw, ph) in peaks: crest += ph * math.exp(-((u - px) / pw) ** 2)
        prof = math.sin(min(max(v, 0), 1) * math.pi) ** 0.7
        prof *= min(1.0, max(0.0, (0.5 - abs(u)) / 0.12)) ** 0.8 if taper else 1.0
        rr = rough * (fbm(u * freq * 7, v * 5, 4, seed + 5, ridged=True) - 0.35)
        return height * max(crest * prof + rr * prof, 0) - 2
    return heightfield(name, x0 - width / 2, x0 + width / 2, y, y + depth, nx, ny, fz, mat)

# ---------------------------------------------------------------- props: elephant
def metaball_mesh(name, balls, res=0.07, thresh=0.6):
    mb = bpy.data.metaballs.new(name + 'MB'); mb.resolution = res; mb.render_resolution = res; mb.threshold = thresh
    for (co, r) in balls:
        e = mb.elements.new(type='BALL'); e.co = co; e.radius = r; e.stiffness = 2.0
    o = obj(name + 'MB', mb)
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    bpy.data.objects.remove(o); bpy.data.metaballs.remove(mb)
    me.name = name
    for p in me.polygons: p.use_smooth = True
    return me

def chain(a, b, r1, r2, n, bend=(0, 0, 0)):
    a, b, bend = Vector(a), Vector(b), Vector(bend); out = []
    for i in range(n):
        t = i / (n - 1); out.append((a.lerp(b, t) + bend * math.sin(t * math.pi), r1 + (r2 - r1) * t))
    return out

def curve_pts(pts, r1, r2, step=0.12):
    out = []; N = len(pts)
    for i in range(N - 1):
        a, b = Vector(pts[i]), Vector(pts[i + 1]); n = max(2, int((b - a).length / step))
        for k in range(n):
            t = (i + k / n) / (N - 1); out.append((a.lerp(b, k / n), r1 + (r2 - r1) * t))
    out.append((Vector(pts[-1]), r2)); return out

def elephant(name, skin, kneel=False, tusk=None, blanket=None, trim=None, howdah=None, trunk='down', eye=True):
    """Stylized elephant facing +X, feet at z=0, ~3 m at the shoulder. Returns [(mesh, material)]."""
    B = []
    if not kneel:
        B += chain((-1.0, 0, 2.05), (0.8, 0, 2.25), 1.12, 1.18, 5, (0, 0, 0.25))
        B += [((0.0, 0, 1.75), 1.05), ((-0.6, 0, 1.7), 0.95)]
        for (x, y) in ((0.85, 0.52), (0.85, -0.52), (-1.0, 0.5), (-1.0, -0.5)):
            B += chain((x, y, 1.9), (x + 0.05, y, 0.25), 0.5, 0.4, 7)
            B += [((x + 0.08, y, 0.18), 0.43)]
        head = Vector((1.75, 0, 2.55)); top = 2.95
    else:  # kneeling on the front knees, rear still raised, head bowed
        B += chain((-1.0, 0, 1.95), (0.8, 0, 1.15), 1.12, 1.15, 5, (0, 0, 0.22))
        B += [((0.0, 0, 1.25), 1.0), ((-0.7, 0, 1.5), 0.95)]
        for y in (0.55, -0.55):
            B += chain((0.85, y, 1.0), (1.15, y, 0.32), 0.5, 0.42, 6)       # upper front leg down to the knee
            B += chain((1.15, y, 0.3), (0.35, y, 0.26), 0.42, 0.36, 6)      # shin folded back along the ground
            B += chain((-1.0, y, 1.6), (-0.75, y, 0.75), 0.52, 0.45, 5)     # hind thigh
            B += chain((-0.75, y, 0.75), (-1.1, y, 0.22), 0.45, 0.42, 5)    # hind shin
        head = Vector((1.85, 0, 1.5)); top = 2.5
    h = head
    B += [(h, 0.85), (h + Vector((0.1, 0, 0.42)), 0.62), (h + Vector((-0.25, 0, 0.3)), 0.6)]
    if trunk == 'down':
        tp = [h + Vector((0.55, 0, -0.1)), h + Vector((0.8, 0, -0.7)), h + Vector((0.85, 0, -1.4)), h + Vector((0.8, 0, -2.0)), h + Vector((0.98, 0, -2.25))]
    elif trunk == 'up':
        tp = [h + Vector((0.55, 0, -0.1)), h + Vector((0.95, 0, -0.55)), h + Vector((1.35, 0, -0.35)), h + Vector((1.6, 0, 0.2)), h + Vector((1.5, 0, 0.6))]
    else:  # 'ground': trunk resting on the ground in front
        tp = [h + Vector((0.55, 0, -0.1)), h + Vector((0.85, 0, -0.6)), h + Vector((1.05, 0, -1.1)), h + Vector((1.5, 0, -1.28)), h + Vector((1.9, 0, -1.2))]
    B += curve_pts(tp, 0.36, 0.14)
    tb = Vector((-2.0, 0, top - 0.6))
    B += chain(tb, tb + Vector((-0.3, 0, -1.0)), 0.1, 0.07, 6)
    parts = [(metaball_mesh(name + '_body', B), skin)]
    bm = bmesh.new()  # ears: big rounded flaps
    for sgn in (1, -1):
        # big flaps lying along the side of the head (plane XZ), front edge flared out a little
        bm_sphere(bm, TRS(h + Vector((-0.45, sgn * 0.7, -0.1)), (0, 0, -sgn * math.radians(18)), (0.6, 0.1, 0.8)), 18, 12)
        bm_sphere(bm, TRS(h + Vector((-0.4, sgn * 0.72, -0.62)), (0, 0, -sgn * math.radians(18)), (0.42, 0.09, 0.42)), 14, 10)
    parts.append((mesh_bm(name + '_ears', bm), skin))
    if tusk:
        bm = bmesh.new()
        for sgn in (1, -1):
            pts = [h + Vector((0.35, sgn * 0.32, -0.45)), h + Vector((0.7, sgn * 0.36, -0.78)), h + Vector((1.05, sgn * 0.38, -0.76)), h + Vector((1.28, sgn * 0.36, -0.52))]
            for i in range(3): bm_seg(bm, pts[i], pts[i + 1], 0.1 - i * 0.028, 0.1 - (i + 1) * 0.028, 8)
        parts.append((mesh_bm(name + '_tusks', bm), tusk))
    if eye:
        bm = bmesh.new()
        for sgn in (1, -1): bm_sphere(bm, TRS(h + Vector((0.45, sgn * 0.52, 0.12)), s=(0.075, 0.075, 0.075)), 10, 6)
        parts.append((mesh_bm(name + '_eyes', bm), toon('eye', '#120a06', rim=0.3, namt=0)))
    if blanket:
        bm = bmesh.new()
        bm_sphere(bm, TRS((-0.15, 0, top - 0.48), s=(1.28, 1.22, 0.62)), 24, 12)
        parts.append((mesh_bm(name + '_blanket', bm), blanket))
        if trim:
            bm = bmesh.new()
            bm_cone(bm, TRS((-0.15, 0, top - 0.72), s=(1.0, 0.95, 1.0)), 1.3, 1.26, 0.16, 32, caps=False)
            parts.append((mesh_bm(name + '_trim', bm), trim))
        if howdah:
            bm = bmesh.new(); bm_cube(bm, TRS((-0.2, 0, top + 0.3), s=(1.1, 0.9, 0.55)))
            bm_cone(bm, TRS((-0.2, 0, top + 0.95)), 0.75, 0.05, 0.75, 12)
            parts.append((mesh_bm(name + '_howdah', bm, smooth=False), howdah))
    return parts

def place(parts, name, loc, rot_z=0.0, scale=1.0):
    root = link(bpy.data.objects.new(name, None)); root.location = loc; root.rotation_euler = (0, 0, rot_z); root.scale = (scale,) * 3
    for me, m in parts:
        if m is not None and len(me.materials) == 0: me.materials.append(m)
        o = obj(name + '_' + me.name, me); o.parent = root
    return root

# ---------------------------------------------------------------- props: people & things
def soldier_mesh(name, pose='walk', spear=True, shield=True):
    """Chunky silhouette soldier ~1.8 m, facing +X."""
    bm = bmesh.new()
    lean = {'walk': 0.05, 'push': 0.5, 'pull': -0.4}.get(pose, 0)
    stride = 0.25 if pose == 'walk' else 0.45
    def P2(x, z): return Vector((x + z * math.sin(lean), 0, z * math.cos(lean)))
    for s, y in ((1, 0.11), (-1, -0.11)):
        st_ = 0.5 if pose in ('reach', 'haul') else 0.0
        foot = Vector((s * (stride + st_) * 0.5 - (0.35 if pose == 'push' else (-0.3 if pose == 'pull' else 0)), y, 0.05))
        bm_seg(bm, foot, P2(0, 0.85) + Vector((0, y, 0)), 0.075, 0.1, 8)
    bm_cone(bm, Matrix.Translation(P2(0, 1.1)) @ Euler((0, lean, 0)).to_matrix().to_4x4(), 0.34, 0.2, 0.6, 12)
    bm_seg(bm, P2(0, 1.35), P2(0, 1.52), 0.2, 0.17, 10)
    bm_sphere(bm, TRS(P2(0.02, 1.66), s=(0.13, 0.12, 0.14)), 12, 8)
    bm_cone(bm, TRS(P2(0.0, 1.8), (0, lean, 0)), 0.15, 0.02, 0.22, 10)
    sh = P2(0, 1.45)
    if pose == 'reach':
        for y in (0.2, -0.2): bm_seg(bm, sh + Vector((0, y, 0)), sh + Vector((0.6, y * 0.6, -0.02)), 0.065, 0.055, 6)
    elif pose == 'haul':
        for y in (0.2, -0.2): bm_seg(bm, sh + Vector((0, y, 0)), sh + Vector((0.28, y * 0.4, 0.12)), 0.065, 0.055, 6)
    elif pose == 'push':
        for y in (0.2, -0.2): bm_seg(bm, sh + Vector((0, y, 0)), sh + Vector((0.55, y * 0.7, 0.1)), 0.065, 0.055, 6)
    elif pose == 'pull':
        for y in (0.2, -0.2): bm_seg(bm, sh + Vector((0, y, 0)), sh + Vector((0.6, y * 0.4, -0.2)), 0.065, 0.055, 6)
    else:
        bm_seg(bm, sh + Vector((0, 0.22, 0)), sh + Vector((0.12, 0.26, -0.45)), 0.065, 0.055, 6)
        bm_seg(bm, sh + Vector((0, -0.22, 0)), sh + Vector((0.2, -0.3, -0.3)), 0.065, 0.055, 6)
    if spear and pose == 'walk':
        base = sh + Vector((0.2, -0.3, -1.0))
        bm_seg(bm, base, base + Vector((0.25, 0, 2.7)), 0.028, 0.028, 5)
        bm_cone(bm, seg_matrix(base + Vector((0.25, 0, 2.7)), base + Vector((0.28, 0, 3.0))), 0.07, 0.0, 1.0, 6)
    if shield:
        bm_cone(bm, TRS(sh + Vector((0.02, 0.33, -0.3)), (math.pi / 2, 0, 0)), 0.3, 0.3, 0.06, 14)
    return mesh_bm(name, bm)

def banner_mesh(name, h=4.2, w=1.3, ht=0.9, seed=0.0):
    """pole (mat 0) + waving swallow-tail pennant (mat 1)"""
    bm = bmesh.new()
    bm_seg(bm, (0, 0, 0), (0, 0, h), 0.045, 0.04, 6)
    bm_cone(bm, TRS((0, 0, h + 0.12)), 0.09, 0, 0.25, 6)
    nx, nz = 12, 4; vs = []
    for j in range(nz + 1):
        for i in range(nx + 1):
            u = i / nx; v = j / nz
            x = u * w; z = h - 0.1 - v * ht * (1 - 0.3 * u)
            y = 0.22 * math.sin(u * 5 + seed) * u
            if u > 0.8 and 0.3 < v < 0.7: x -= 0.3 * w * (u - 0.8) / 0.2 * (1 - abs(v - 0.5) / 0.2)
            vs.append(bm.verts.new((x, y, z)))
    start = set(bm.faces)
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i; bm.faces.new((vs[a], vs[a + 1], vs[a + nx + 2], vs[a + nx + 1]))
    bm_matidx(bm, 1, start)
    return mesh_bm(name, bm)

def puff_mesh(name, r=1.0, seed=0, n=6):
    bm = bmesh.new(); rnd = random.Random(seed)
    for k in range(n):
        off = Vector((rnd.uniform(-1.3, 1.3), rnd.uniform(-0.5, 0.5), rnd.uniform(-0.1, 0.5))) * r
        bm_sphere(bm, TRS(off, s=(r * rnd.uniform(0.6, 1.1),) * 3), 16, 10)
    return mesh_bm(name, bm)

def rock_mesh(name, size=(1, 1, 1), seed=0, sub=2, rough=0.35):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub + 1, radius=1.0)
    for v in bm.verts:
        p = v.co.copy()
        d = 1 + rough * noise.noise(p * 1.3 + Vector((seed, seed * 2, 0))) + 0.12 * noise.noise(p * 4 + Vector((seed, 0, 0)))
        v.co = Vector((p.x * size[0], p.y * size[1], max(p.z, -0.2) * size[2])) * d
    return mesh_bm(name, bm)

def bird_mesh(name, flap=0.5, stones=True):
    """Swallow-like bird facing +X, span ~1.0. Materials: 0 body, 1 stones (beak + two feet), 2 wings."""
    bm = bmesh.new()
    bm_sphere(bm, TRS((0, 0, 0), s=(0.2, 0.07, 0.07)), 12, 8)
    bm_sphere(bm, TRS((0.19, 0, 0.03), s=(0.075, 0.065, 0.065)), 10, 6)
    bm_cone(bm, seg_matrix((0.26, 0, 0.03), (0.33, 0, 0.02)), 0.025, 0.0, 1.0, 6)
    for s in (1, -1):
        v = [bm.verts.new(p) for p in ((-0.15, 0, 0), (-0.44, s * 0.13, 0.02), (-0.34, s * 0.02, 0.0))]; bm.faces.new(v)
    wings = []
    for s in (1, -1):
        a = flap
        root1, root2 = Vector((0.1, s * 0.04, 0.02)), Vector((-0.1, s * 0.04, 0.02))
        mid = Vector((0.02, s * 0.3 * math.cos(a), 0.3 * math.sin(a)))
        tip = Vector((-0.25, s * 0.55 * math.cos(a * 0.8), 0.55 * math.sin(a * 0.8) + 0.04))
        v = [bm.verts.new(p) for p in (root1, mid, tip, root2)]; wings.append(bm.faces.new(v))
    for f in wings: f.material_index = 2
    start = set(bm.faces)
    if stones:
        bm_sphere(bm, TRS((0.35, 0, 0.0), s=(0.045,) * 3), 8, 6)
        for s in (1, -1): bm_sphere(bm, TRS((0.02, s * 0.05, -0.11), s=(0.05,) * 3), 8, 6)
        bm_matidx(bm, 1, start)
    me = mesh_bm(name, bm, smooth=False)
    for p in me.polygons:  # wings -> material 2
        if len(p.vertices) == 4 and abs(p.center.y) > 0.12 and p.material_index == 0: p.material_index = 2
    return me

def import_glb(fname, mats):
    """Import an env glb (LOD0 only); remap its materials by base name through `mats`."""
    before = set(bpy.data.objects); win = bpy.context.window_manager.windows[0]
    with bpy.context.temp_override(window=win, scene=S()):
        bpy.ops.import_scene.gltf(filepath=ENV + fname + '.glb')
    new = [o for o in bpy.data.objects if o not in before]
    keep = [o for o in new if o.type == 'MESH' and 'LOD' not in o.name][0]
    me = keep.data
    for o in new: bpy.data.objects.remove(o)
    for i, m in enumerate(me.materials):
        base = m.name.split('.')[0]
        if base in mats: me.materials[i] = mats[base]
    for p in me.polygons: p.use_smooth = True
    return me

# ---------------------------------------------------------------- compositor + render
def compositor(sunpos=None):
    sc = S(); ng = bpy.data.node_groups.new('Comp_' + sc.name, 'CompositorNodeTree'); sc.compositing_node_group = ng
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    N, L = ng.nodes, ng.links
    rl = N.new('CompositorNodeRLayers'); rl.scene = sc
    cur = rl.outputs['Image']
    if P['bloom']:
        gl = N.new('CompositorNodeGlare'); gl.inputs['Type'].default_value = 'Bloom'; gl.inputs['Quality'].default_value = 'High'
        gl.inputs['Threshold'].default_value = P['bloom_thr']; gl.inputs['Strength'].default_value = P['bloom']; gl.inputs['Size'].default_value = 0.9
        L.new(cur, gl.inputs['Image']); cur = gl.outputs['Image']
    if P['beams'] and sunpos is not None:
        gb = N.new('CompositorNodeGlare'); gb.inputs['Type'].default_value = 'Sun Beams'; gb.inputs['Quality'].default_value = 'High'
        gb.inputs['Threshold'].default_value = 0.95; gb.inputs['Strength'].default_value = P['beams']; gb.inputs['Size'].default_value = 0.5
        sp = gb.inputs['Sun Position']; n = len(sp.default_value)
        sp.default_value = (sunpos[0], sunpos[1], 0.0)[:n]
        L.new(cur, gb.inputs['Image']); cur = gb.outputs['Image']
    if P['kuwa']:
        k = N.new('CompositorNodeKuwahara'); k.inputs['Type'].default_value = 'Anisotropic'
        k.inputs['Size'].default_value = P['kuwa']; k.inputs['Uniformity'].default_value = 4
        k.inputs['Sharpness'].default_value = 0.6; k.inputs['Eccentricity'].default_value = 1.0
        L.new(cur, k.inputs['Image']); cur = k.outputs['Image']
    cb = N.new('CompositorNodeColorBalance'); cb.inputs['Type'].default_value = 'Lift/Gamma/Gain'
    for nm, v in (('Lift', P['lift']), ('Gamma', P['gamma']), ('Gain', P['gain'])):
        s = [i for i in cb.inputs if i.name == nm and i.type == 'RGBA'][0]; s.default_value = tuple(v) + (1,)
    L.new(cur, cb.inputs['Image']); cur = cb.outputs['Image']
    if P['sat'] != 1.0:
        hs = N.new('CompositorNodeHueSat'); hs.inputs['Saturation'].default_value = P['sat']
        L.new(cur, hs.inputs['Image']); cur = hs.outputs['Image']
    if P['vign']:
        em = N.new('CompositorNodeEllipseMask'); em.inputs['Operation'].default_value = 'Subtract'
        em.inputs['Mask'].default_value = 1.0; em.inputs['Value'].default_value = 1.0
        em.inputs['Size'].default_value = (1.0, 0.9)
        bl = N.new('CompositorNodeBlur'); bl.inputs['Type'].default_value = 'Fast Gaussian'; bl.inputs['Size'].default_value = (300, 300)
        L.new(em.outputs['Mask'], bl.inputs['Image'])
        mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = P['vign']
        L.new(bl.outputs['Image'], mm.inputs[0])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
        L.new(mm.outputs[0], mx.inputs[0]); L.new(cur, mx.inputs[6]); mx.inputs[7].default_value = lin(P['vig_col'])
        cur = mx.outputs[2]
    go = N.new('NodeGroupOutput'); L.new(cur, go.inputs[0])
    sc.render.use_compositing = True

def sun_screen():
    sc = S(); p = sc.camera.location + sunv() * 5000
    v = world_to_camera_view(sc, sc.camera, p); return (v.x, v.y)

def render(name, pct=100):
    sc = S(); t0 = time.time()
    compositor(sun_screen())
    os.makedirs(OUT, exist_ok=True)
    sc.render.resolution_percentage = pct
    bpy.ops.render.render(write_still=False, scene=sc.name)
    img = bpy.data.images['Render Result']
    ims = sc.render.image_settings
    ims.file_format = 'WEBP'; ims.color_mode = 'RGB'
    path = OUT + '/' + name + '.webp'; best = None
    for q in (99, 98, 97, 96, 95, 94, 93, 92, 90, 88, 86, 84, 82, 80, 78, 76, 74, 72, 70, 67, 64, 60, 56, 52, 48, 44, 40, 35, 30):
        ims.quality = q; img.save_render(path, scene=sc)
        sz = os.path.getsize(path)
        if sz <= MAXB: best = (q, sz); break
    sc.render.resolution_percentage = 100
    print('RENDER', name, 'quality=%s bytes=%s' % best if best else 'TOO BIG', '%.1fs' % (time.time() - t0))
    return best

def save_blend():
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, copy=True)

SCENES = {}
def scene(fn): SCENES[fn.__name__.replace('sc_', '', 1)] = fn; return fn

def run(name, do_render=True, pct=100, **over):
    global P
    P = dict(BASE_P); new_scene(name); random.seed(7)
    SCENES[name](**over)
    build_world(); sun_lamp()
    return render(name, pct) if do_render else None

def run_all():
    return {n: run(n) for n in ('army', 'kaaba', 'elephant', 'birds', 'straw', 'year', 'title')}

exec(open(ROOT + '/blender/illustrations/illustrations_scenes.py').read())
