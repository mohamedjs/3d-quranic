# Canal pieces + the toon water material.
# Toon water (Blender preview, and the spec for the game port — see WATER below):
#   flat colour bands by distance to the bank (UV u across the channel, 0..1; v along, metres),
#   white foam line hugging the banks + dashed inner foam, stylized elongated highlight streaks.
import math, random, bmesh, bpy
from mathutils import Vector
import tk
from tk import B, M, hexc, _nodes

WATER = dict(
    deep='#1F6E74', mid='#3E9C94', shallow='#7CC8B0', foam='#F2FBF4', streak='#FFF6D8',
    # band edges on e = distance-from-bank (0 at bank .. 1 at centre) + noise*0.18
    shallow_to_mid=0.22, mid_to_deep=0.55, noise_scale=0.35,
    foam_edge=0.12, foam_noise=0.05, dash_band=(0.16, 0.2), dash_period_m=1.6, dash_duty=0.45,
    streak_scale=(9.0, 0.2), streak_threshold=0.7, streak_speed=0.35, flow_speed=0.25,
    opacity=0.92,
)

def water_material():
    m = bpy.data.materials.get('toon_water')
    if m: return m
    m = bpy.data.materials.new('toon_water'); n, l = _nodes(m); n.clear()
    fl = n.new('NodeFrame'); fl.name = 'WATERFLAG'
    out = n.new('ShaderNodeOutputMaterial'); out.name = 'OUT'
    pbr = n.new('ShaderNodeBsdfPrincipled'); pbr.name = 'PBR'
    pbr.inputs['Base Color'].default_value = (*hexc(WATER['mid']), 1); pbr.inputs['Roughness'].default_value = 0.1
    m.diffuse_color = (*hexc(WATER['mid']), 1)
    uv = n.new('ShaderNodeUVMap'); uv.uv_map = 'UVMap'
    sep = n.new('ShaderNodeSeparateXYZ'); l.new(uv.outputs[0], sep.inputs[0])
    geo = n.new('ShaderNodeNewGeometry')
    def math_(op, a, b=None, v=None):
        x = n.new('ShaderNodeMath'); x.operation = op
        (l.new(a, x.inputs[0]) if not isinstance(a, (int, float)) else x.inputs[0].__setattr__('default_value', a))
        if b is not None: (l.new(b, x.inputs[1]) if not isinstance(b, (int, float)) else x.inputs[1].__setattr__('default_value', b))
        return x.outputs[0]
    # e = 2*min(u, 1-u)  (0 at bank, 1 at centre)
    e = math_('MULTIPLY', math_('MINIMUM', sep.outputs['X'], math_('SUBTRACT', 1.0, sep.outputs['X'])), 2.0)
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = WATER['noise_scale']; l.new(geo.outputs['Position'], nz.inputs['Vector'])
    en = math_('ADD', e, math_('MULTIPLY', math_('SUBTRACT', nz.outputs['Fac'], 0.5), 0.36))
    ramp = n.new('ShaderNodeValToRGB'); ramp.color_ramp.interpolation = 'CONSTANT'; el = ramp.color_ramp.elements
    el[0].position = 0; el[0].color = (*hexc(WATER['shallow']), 1)
    el[1].position = WATER['shallow_to_mid']; el[1].color = (*hexc(WATER['mid']), 1)
    x = el.new(WATER['mid_to_deep']); x.color = (*hexc(WATER['deep']), 1)
    l.new(en, ramp.inputs[0])
    # highlight streaks: noise stretched along the flow (v), thresholded
    sc = n.new('ShaderNodeCombineXYZ')
    l.new(math_('MULTIPLY', sep.outputs['X'], 9.0), sc.inputs['X']); l.new(math_('MULTIPLY', sep.outputs['Y'], 0.2), sc.inputs['Y'])
    nz2 = n.new('ShaderNodeTexNoise'); nz2.inputs['Scale'].default_value = 1.4; nz2.inputs['Detail'].default_value = 0.5; l.new(sc.outputs[0], nz2.inputs['Vector'])
    st = math_('MULTIPLY', math_('GREATER_THAN', nz2.outputs['Fac'], WATER['streak_threshold']), math_('GREATER_THAN', e, 0.25))
    # foam at the banks (wobbly) + dashed inner line
    nz3 = n.new('ShaderNodeTexNoise'); nz3.inputs['Scale'].default_value = 2.5; l.new(geo.outputs['Position'], nz3.inputs['Vector'])
    fe = math_('LESS_THAN', math_('ADD', e, math_('MULTIPLY', math_('SUBTRACT', nz3.outputs['Fac'], 0.5), WATER['foam_noise'] * 2)), WATER['foam_edge'])
    band = math_('MULTIPLY', math_('GREATER_THAN', e, WATER['dash_band'][0]), math_('LESS_THAN', e, WATER['dash_band'][1]))
    dash = math_('GREATER_THAN', math_('SINE', math_('ADD', math_('MULTIPLY', sep.outputs['Y'], math.tau / WATER['dash_period_m']), math_('MULTIPLY', nz3.outputs['Fac'], 3.0))), 1 - 2 * WATER['dash_duty'])
    foam = math_('MAXIMUM', fe, math_('MULTIPLY', band, dash))
    c1 = n.new('ShaderNodeMix'); c1.data_type = 'RGBA'; l.new(st, c1.inputs['Factor']); l.new(ramp.outputs[0], c1.inputs[6]); c1.inputs[7].default_value = (*hexc(WATER['streak']), 1)
    c2 = n.new('ShaderNodeMix'); c2.data_type = 'RGBA'; l.new(foam, c2.inputs['Factor']); l.new(c1.outputs[2], c2.inputs[6]); c2.inputs[7].default_value = (*hexc(WATER['foam']), 1)
    em = n.new('ShaderNodeEmission'); em.name = 'TOON'; l.new(c2.outputs[2], em.inputs['Color'])
    l.new(em.outputs[0], out.inputs['Surface'])
    return m

def water_strip(name, pts, width, col, z=0.0):
    """UV'd water ribbon along a polyline (u across 0..1, v = metres along)."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); rows = []; acc = 0.0; prev = None; vs = []
    pts = [Vector(p) for p in pts]
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]); t.z = 0; t.normalize()
        s = Vector((-t.y, t.x, 0)); W = width[i] if isinstance(width, (list, tuple)) else width
        if prev is not None: acc += (p - prev).length
        prev = p; vs.append(acc)
        rows.append([bm.verts.new((p.x + s.x * W * (k / 4 - 0.5), p.y + s.y * W * (k / 4 - 0.5), z)) for k in range(5)])
    for i in range(len(rows) - 1):
        for k in range(4):
            f = bm.faces.new((rows[i][k], rows[i][k + 1], rows[i + 1][k + 1], rows[i + 1][k]))
            for lp, (ii, kk) in zip(f.loops, ((i, k), (i, k + 1), (i + 1, k + 1), (i + 1, k))):
                lp[uvl].uv = (kk / 4, vs[ii])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(water_material())
    o = bpy.data.objects.new(name, me); col.objects.link(o)
    return o

def sluice(seed=81):
    """Sluice gate across a 2.6 m canal (spans X, posts at x = ±1.45)."""
    rnd = random.Random(seed); b = B(seed)
    for s in (-1.45, 1.45):
        b.box((0.26, 0.26, 1.8), (s, 0, 0.42), 'toon_wood', bevel=0.04, wobble=0.01)
        b.box((0.6, 0.7, 0.5), (s * 1.12, 0, -0.1), 'toon_stone', bevel=0.12, wobble=0.04, freq=2)   # stone abutments
    b.box((3.4, 0.22, 0.22), (0, 0, 1.3), 'toon_wood', bevel=0.04, wobble=0.01)
    for i in range(5):
        b.box((0.52, 0.08, 0.72), (-1.0 + i * 0.5, 0, -0.08), 'toon_wood_dark' if i % 2 else 'toon_wood', bevel=0.02)
    b.cyl(0.04, 0.04, 1.0, (0, 0, 1.78), 'toon_wood', verts=6)
    b.cyl(0.25, 0.25, 0.06, (0, 0, 2.3), 'toon_iron', verts=10, rot=(0, 0, 0))   # wheel
    for k in range(3): b.box((0.5, 0.03, 0.03), (0, 0, 2.3), 'toon_iron', rot=(0, 0, k * math.pi / 3))
    return b

def footbridge(seed=82):
    """Plank footbridge spanning X (3.4 m), 1.75 m wide, plank top at z = 0.14."""
    rnd = random.Random(seed); b = B(seed)
    for i in range(5):
        b.box((3.4 + rnd.uniform(-0.1, 0.1), 0.33, 0.09), (rnd.uniform(-0.05, 0.05), -0.7 + i * 0.35, 0.095), 'toon_wood' if i % 2 else 'toon_wood_dark', bevel=0.02, rot=(0, 0, rnd.uniform(-0.02, 0.02)), wobble=0.005)
    for s in (-1.5, 1.5): b.box((0.18, 1.95, 0.14), (s, 0, 0.0), 'toon_wood_dark', bevel=0.02)
    for s in (-1.5, 1.5):   # a single handrail on one side, lashed
        b.cyl(0.04, 0.035, 1.0, (s, -0.95, 0.55), 'toon_wood', verts=6)
    b.cyl(0.03, 0.03, 3.1, (0, -0.95, 0.95), 'toon_wood', rot=(0, math.pi / 2, 0), verts=6)
    for s in (-1.5, 1.5): b.cyl(0.055, 0.055, 0.06, (s, -0.95, 0.95), 'toon_rope', verts=6)
    return b

def shaduf(seed=83):
    """شادوف: two mud pillars, a pivot, a sweep pole (+X over the water), mud counterweight, bucket."""
    b = B(seed)
    for s in (-0.45, 0.45): b.box((0.34, 0.3, 2.2), (0, s, 1.1), 'toon_plaster', bevel=0.12, taper=0.8, wobble=0.03)
    b.cyl(0.05, 0.05, 1.2, (0, 0, 2.3), 'toon_wood_dark', rot=(math.pi / 2, 0, 0), verts=6)
    a = 0.32; c, s_ = math.cos(a), math.sin(a)
    p0 = Vector((-1.9 * c + 0.6, 0, 2.3 - 1.9 * s_ * 1.0)); p1 = Vector((0.6 + 2.6 * c, 0, 2.3 + 2.6 * s_))
    b.tube([p0, (p0 + p1) / 2 + Vector((0, 0, 0.04)), p1], [0.07, 0.055, 0.035], 'toon_wood', sides=6)
    b.ball(0.36, p0 + Vector((-0.05, 0, -0.1)), 'toon_mud', scale=(1, 0.9, 0.8), sub=2, wobble=0.05, freq=3)
    b.cyl(0.012, 0.012, p1.z - 0.62, (p1.x, 0, (p1.z + 0.62) / 2), 'toon_rope', verts=4)
    b.lathe([(0.001, 0.35), (0.12, 0.36), (0.17, 0.6), (0.18, 0.62), (0.16, 0.62), (0.14, 0.5)], loc=(p1.x, 0, 0), mat='toon_clay', segs=10)
    return b

def stream(seed=84):
    """Street stream channel, 4 m along Y, 0.8 m wide; stones on the curbs. Water surface: separate UV'd mesh."""
    rnd = random.Random(seed); b = B(seed)
    b.box((0.95, 4.0, 0.1), (0, 0, -0.34), 'toon_mud')
    for s in (-1, 1):
        b.box((0.14, 4.0, 0.42), (s * 0.48, 0, -0.14), 'toon_stone_dark', bevel=0.03)
        y = -2.0
        while y < 2.0:
            L = rnd.uniform(0.35, 0.55)
            b.ball(0.5, (s * 0.6, y + L / 2, 0.0), 'toon_stone' if rnd.random() < 0.6 else 'toon_stone_dark', scale=(0.28, L * 0.92, 0.22), sub=0, wobble=0.012, freq=4)
            y += L * 0.95
    return b

def canal_bank(seed=85):
    """4 m bank edge along Y: grassy top at z=0 (x<0), mud slope down to the water (x>0, to z=-1.4),
    a row of stones at the waterline (z≈-0.5) and a few tufts. Mirror (rot 180°) for the other bank."""
    rnd = random.Random(seed); b = B(seed)
    prof = [(-0.9, 0.02), (-0.3, 0.0), (0.05, -0.08), (0.35, -0.38), (0.6, -0.62), (0.9, -1.0), (1.1, -1.4)]
    n = 8; bm = bmesh.new(); rows = []
    for i in range(n + 1):
        y = -2 + 4 * i / n
        rows.append([bm.verts.new((x + 0.05 * math.sin(y * 2.3 + x), y, z)) for x, z in prof])
    for i in range(n):
        for k in range(len(prof) - 1):
            f = bm.faces.new((rows[i][k], rows[i][k + 1], rows[i + 1][k + 1], rows[i + 1][k])); f.material_index = 0
    grass = [f for f in bm.faces if f.calc_center_median().x < -0.05]
    b.put(bm, 'toon_mud', None, True)
    # re-colour the flat top: overlay a grassy lip
    b.box((0.95, 4.0, 0.06), (-0.5, 0, 0.0), 'toon_ground_green', bevel=0.03)
    y = -1.9
    while y < 1.95:
        L = rnd.uniform(0.3, 0.5)
        b.ball(0.5, (0.72 + rnd.uniform(-0.05, 0.05), y + L / 2, -0.52), 'toon_stone' if rnd.random() < 0.6 else 'toon_stone_dark', scale=(0.3, L * 0.95, 0.24), sub=1, wobble=0.02, freq=4)
        y += L
    for i in range(4):   # tufts on the lip
        x, yy = rnd.uniform(-0.6, 0.0), rnd.uniform(-1.8, 1.8)
        for k in range(4):
            a = rnd.uniform(0, math.tau)
            d = Vector((math.cos(a), math.sin(a), 0))
            pts = [Vector((x, yy, 0.02)) + d * (0.15 * t * t) + Vector((0, 0, 0.32 * t)) for t in (0, 0.5, 1)]
            b.strip(pts, [0.06, 0.04, 0.0], mat='toon_grass', side=(-d.y, d.x, 0))
    return b

def canal_stones(seed=86):
    """2 m stone-lined edge piece (rounded rubble stones in a row, along Y) for canal/pond edges."""
    rnd = random.Random(seed); b = B(seed)
    y = -1.0
    while y < 0.98:
        L = rnd.uniform(0.28, 0.45)
        b.ball(0.5, (rnd.uniform(-0.04, 0.04), y + L / 2, 0.05), 'toon_stone' if rnd.random() < 0.6 else 'toon_stone_dark', scale=(0.42, L, 0.3), sub=1, wobble=0.025, freq=4)
        if rnd.random() < 0.5:
            b.ball(0.5, (0.22, y + L / 2, -0.12), 'toon_stone_dark', scale=(0.3, L * 0.8, 0.25), sub=1, wobble=0.02, freq=4)
        y += L
    return b

tk.SPECIAL['toon_water'] = water_material
