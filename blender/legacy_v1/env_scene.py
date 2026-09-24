# Surat Al-Fil — the village vignette in Blender (preview of the game's farmland).
# Coordinates match the game: Blender (x, y) = game (x, -z); ground at grandma's house = 0.
#   terrain with fields, dirt road and yard · a meandering canal (ترعة) with flowing water
#   berseem / maize / reed / grass scatter · houses from public/models/env + the mastaba
#   HDRI sky + golden-hour sun (EEVEE)
import bpy, bmesh, math, random, sys, importlib
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, '/var/www/html/old/3d-quranic/blender')
import lib; importlib.reload(lib)
from lib import clear_collection, link, apply_all, shade_auto

PUB = '/var/www/html/old/3d-quranic/public/'
TEX = PUB + 'textures/'
HOME = Vector((-9.4, -26.0)); HOME_ROT = math.pi / 2          # game HOME (x, z) → blender (x, -z)
SIZE, RES = 150.0, 300                                         # terrain metres / grid cells

# ---------------------------------------------------------------- shape of the land
def canal_x(y): return -15.0 + 1.3 * math.sin(y * 0.045) + 0.6 * math.sin(y * 0.11 + 1.0)
CANAL_W, CANAL_D = 1.7, 0.95                                   # half-width, depth
def is_field(x, y):
    """Plots east of the road and west of the canal; 1 m bunds between them."""
    if 3.0 < x < 60 and -70 < y < 70:
        fx, fy = (x - 3.0) % 15.0, (y + 70) % 19.0
        return fx > 1.0 and fy > 1.0, int((x - 3.0) // 15.0), int((y + 70) // 19.0)
    if -70 < x < canal_x(y) - 4.0 and -70 < y < 70:
        fx, fy = (x + 70) % 14.0, (y + 70) % 17.0
        return fx > 1.0 and fy > 1.0, 10 + int((x + 70) // 14.0), int((y + 70) // 17.0)
    return False, -1, -1

def crop(ix, iy):
    """Which crop a plot grows (deterministic patchwork)."""
    if ix < 0: return None
    r = (ix * 7 + iy * 13) % 10
    return 'clover' if r < 4 else 'maize' if r < 7 else 'soil'

def yard(x, y):
    d = Vector((x, y)) - Vector((-5.0, -26.0))
    return abs(d.x) < 4.2 and abs(d.y) < 6.5

def height(x, y):
    r = math.hypot(x, y + 20)
    hills = (0.25 * math.sin(x * 0.07) * math.cos(y * 0.05) + 0.15 * math.sin(x * 0.19 + y * 0.13)) * min(1, r / 40)
    far = max(0, r - 60) ** 1.4 * 0.02                          # land rises gently toward the horizon
    h = hills + far
    d = abs(x - canal_x(y))
    if d < CANAL_W: h = min(h, -CANAL_D * (1 - (d / CANAL_W) ** 2) - 0.05)
    elif d < CANAL_W + 1.2: h += 0.18 * math.sin((d - CANAL_W) / 1.2 * math.pi)     # levee
    if abs(x) < 1.8: h -= 0.03 * (1 - abs(x) / 1.8)            # road worn a little lower
    f, _, _ = is_field(x, y)
    if f: h -= 0.06                                             # fields sit below the bunds
    if yard(x, y) or math.hypot(x - HOME.x, y - HOME.y) < 5: h *= 0.1
    return h

def masks(x, y):
    """(soil, dirt, mud, 0): terrain material weights; grass where all are 0."""
    d = abs(x - canal_x(y))
    mud = 1.0 if d < CANAL_W + 0.4 else max(0, 1 - (d - CANAL_W - 0.4) / 0.8)
    f, ix, iy = is_field(x, y)
    soil = 1.0 if f and crop(ix, iy) in ('soil', 'maize') else (0.55 if f else 0.0)
    dirt = 1.0 if abs(x) < 1.6 or yard(x, y) else max(0, 1 - (abs(x) - 1.6) / 0.6)
    return soil, dirt, mud

# ---------------------------------------------------------------- materials
def img(path, color=True):
    im = bpy.data.images.load(path, check_existing=True)
    if not color: im.colorspace_settings.name = 'Non-Color'
    return im

def pbr_nodes(nt, name, mapping_out, x=0, y=0):
    """diff + normal + arm for one Poly Haven set; returns (color, normal, rough) sockets."""
    N = nt.nodes; L = nt.links
    d = N.new('ShaderNodeTexImage'); d.image = img(TEX + name + '/diff.jpg'); d.location = (x, y)
    n = N.new('ShaderNodeTexImage'); n.image = img(TEX + name + '/nor.jpg', False); n.location = (x, y - 280)
    a = N.new('ShaderNodeTexImage'); a.image = img(TEX + name + '/arm.jpg', False); a.location = (x, y - 560)
    for t in (d, n, a): L.new(mapping_out, t.inputs['Vector'])
    sp = N.new('ShaderNodeSeparateColor'); sp.location = (x + 300, y - 560); L.new(a.outputs['Color'], sp.inputs['Color'])
    return d.outputs['Color'], n.outputs['Color'], sp.outputs['Green']

def mix(nt, a, b, fac, kind='RGBA', loc=(0, 0)):
    m = nt.nodes.new('ShaderNodeMix'); m.data_type = kind; m.location = loc
    if kind == 'RGBA': m.blend_type = 'MIX'
    nt.links.new(fac, m.inputs['Factor']); nt.links.new(a, m.inputs[6 if kind == 'RGBA' else 2]); nt.links.new(b, m.inputs[7 if kind == 'RGBA' else 3])
    return m.outputs[2 if kind == 'RGBA' else 0]

def terrain_material():
    m = bpy.data.materials.get('terrain') or bpy.data.materials.new('terrain'); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); N, L = nt.nodes, nt.links
    out = N.new('ShaderNodeOutputMaterial'); out.location = (1800, 0)
    bs = N.new('ShaderNodeBsdfPrincipled'); bs.location = (1500, 0); L.new(bs.outputs[0], out.inputs[0])
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.3, 0.3, 0.3)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    sets = [pbr_nodes(nt, s, mp.outputs['Vector'], -600, 900 - i * 900) for i, s in enumerate(('aerial_grass_rock', 'farm_soil', 'dry_ground_01', 'brown_mud_02'))]
    col = N.new('ShaderNodeVertexColor'); col.layer_name = 'mask'; sep = N.new('ShaderNodeSeparateColor'); L.new(col.outputs['Color'], sep.inputs['Color'])
    # break up the tiling of the grass with a large-scale noise
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.04; L.new(tc.outputs['Object'], nz.inputs['Vector'])
    hsv = N.new('ShaderNodeHueSaturation'); L.new(sets[0][0], hsv.inputs['Color'])
    mr = N.new('ShaderNodeMapRange'); L.new(nz.outputs['Fac'], mr.inputs['Value']); mr.inputs['To Min'].default_value = 0.75; mr.inputs['To Max'].default_value = 1.25
    L.new(mr.outputs['Result'], hsv.inputs['Value']); hsv.inputs['Saturation'].default_value = 1.3; hsv.inputs['Hue'].default_value = 0.54
    tint = N.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'; tint.inputs['Factor'].default_value = 1
    L.new(hsv.outputs['Color'], tint.inputs[6]); tint.inputs[7].default_value = (0.62, 0.95, 0.42, 1)        # Nile delta green
    road = N.new('ShaderNodeMix'); road.data_type = 'RGBA'; road.blend_type = 'MULTIPLY'; road.inputs['Factor'].default_value = 1
    L.new(sets[2][0], road.inputs[6]); road.inputs[7].default_value = (0.95, 0.78, 0.6, 1)                   # warm silt dust
    sets[2] = (road.outputs[2], sets[2][1], sets[2][2])
    c, n, r = tint.outputs[2], sets[0][1], sets[0][2]
    for (sc, sn, sr), fac in zip(sets[1:], (sep.outputs['Red'], sep.outputs['Green'], sep.outputs['Blue'])):
        c = mix(nt, c, sc, fac); n = mix(nt, n, sn, fac); r = mix(nt, r, sr, fac, 'FLOAT')
    nm = N.new('ShaderNodeNormalMap'); L.new(n, nm.inputs['Color']); nm.inputs['Strength'].default_value = 1.2
    L.new(c, bs.inputs['Base Color']); L.new(nm.outputs['Normal'], bs.inputs['Normal']); L.new(r, bs.inputs['Roughness'])
    m.diffuse_color = (0.3, 0.33, 0.15, 1)
    return m

def water_material():
    m = bpy.data.materials.get('canal_water') or bpy.data.materials.new('canal_water'); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); N, L = nt.nodes, nt.links
    out = N.new('ShaderNodeOutputMaterial'); bs = N.new('ShaderNodeBsdfPrincipled'); L.new(bs.outputs[0], out.inputs[0])
    bs.inputs['Base Color'].default_value = (0.045, 0.07, 0.045, 1); bs.inputs['Roughness'].default_value = 0.035
    bs.inputs['IOR'].default_value = 1.333; bs.inputs['Transmission Weight'].default_value = 0.35
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); L.new(tc.outputs['Object'], mp.inputs['Vector'])
    # the current: the pattern drifts along +Y (downstream) every frame
    fc = mp.inputs['Location'].driver_add('default_value', 1).driver; fc.type = 'SCRIPTED'; fc.expression = '-frame * 0.012'
    w1 = N.new('ShaderNodeTexNoise'); w1.inputs['Scale'].default_value = 1.6; w1.inputs['Detail'].default_value = 6; L.new(mp.outputs['Vector'], w1.inputs['Vector'])
    mp2 = N.new('ShaderNodeMapping'); mp2.inputs['Scale'].default_value = (1, 0.35, 1); L.new(mp.outputs['Vector'], mp2.inputs['Vector'])
    w2 = N.new('ShaderNodeTexWave'); w2.wave_type = 'BANDS'; w2.bands_direction = 'Y'; w2.inputs['Scale'].default_value = 3.5; w2.inputs['Distortion'].default_value = 6
    L.new(mp2.outputs['Vector'], w2.inputs['Vector'])
    ad = N.new('ShaderNodeMath'); ad.operation = 'ADD'; L.new(w1.outputs['Fac'], ad.inputs[0]); L.new(w2.outputs['Fac'], ad.inputs[1])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.18; bump.inputs['Distance'].default_value = 0.05
    L.new(ad.outputs[0], bump.inputs['Height']); L.new(bump.outputs['Normal'], bs.inputs['Normal'])
    m.diffuse_color = (0.05, 0.08, 0.06, 1)
    try: m.surface_render_method = 'BLENDED'
    except Exception: pass
    return m

def plant_material(name, rgb, var=0.12, sss=0.0):
    """Leaf material with per-plant colour variation (Object Info → Random)."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); N, L = nt.nodes, nt.links
    out = N.new('ShaderNodeOutputMaterial'); bs = N.new('ShaderNodeBsdfPrincipled'); L.new(bs.outputs[0], out.inputs[0])
    oi = N.new('ShaderNodeObjectInfo'); hsv = N.new('ShaderNodeHueSaturation')
    hsv.inputs['Color'].default_value = (*rgb, 1)
    mr = N.new('ShaderNodeMapRange'); L.new(oi.outputs['Random'], mr.inputs['Value']); mr.inputs['To Min'].default_value = 1 - var; mr.inputs['To Max'].default_value = 1 + var
    L.new(mr.outputs['Result'], hsv.inputs['Value'])
    mr2 = N.new('ShaderNodeMapRange'); L.new(oi.outputs['Random'], mr2.inputs['Value']); mr2.inputs['To Min'].default_value = 0.48; mr2.inputs['To Max'].default_value = 0.53
    L.new(mr2.outputs['Result'], hsv.inputs['Hue'])
    # darker at the base, lighter at the tips (ambient occlusion inside the clump)
    gc = N.new('ShaderNodeTexCoord'); sepz = N.new('ShaderNodeSeparateXYZ'); L.new(gc.outputs['Generated'], sepz.inputs['Vector'])
    ramp = N.new('ShaderNodeMapRange'); L.new(sepz.outputs['Z'], ramp.inputs['Value']); ramp.inputs['To Min'].default_value = 0.45
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1
    L.new(hsv.outputs['Color'], mul.inputs[6]); L.new(ramp.outputs['Result'], mul.inputs[7])
    L.new(mul.outputs[2], bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.55
    if sss:
        bs.inputs['Transmission Weight'].default_value = 0.0
        bs.inputs['Subsurface Weight'].default_value = sss; bs.inputs['Subsurface Radius'].default_value = (0.1, 0.2, 0.05)
    m.diffuse_color = (*rgb, 1)
    return m

# ---------------------------------------------------------------- plant meshes
def blade(bm, base, height, width, lean_dir, bend, segs=4, twist=0.0):
    """Tapered bent blade (quad strip)."""
    prev = None
    side = Vector((-lean_dir.y, lean_dir.x, 0)).normalized()
    for i in range(segs + 1):
        t = i / segs
        p = base + Vector((0, 0, height * t)) + lean_dir * bend * t * t * height
        w = width * (1 - t) ** 0.8 + 0.002
        sd = (side * math.cos(twist * t) + Vector((0, 0, 0.3)) * math.sin(twist * t)).normalized()
        a, b = bm.verts.new(p - sd * w / 2), bm.verts.new(p + sd * w / 2)
        if prev: bm.faces.new((prev[0], prev[1], b, a))
        prev = (a, b)

def plant_obj(name, build, material, col):
    bm = bmesh.new(); build(bm)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); col.objects.link(o); me.materials.append(material)
    for p in me.polygons: p.use_smooth = True
    return o

def make_plants(col):
    rnd = random.Random(5)
    grass_m = plant_material('grass_blade', (0.16, 0.27, 0.07), 0.18, sss=0.1)
    clover_m = plant_material('berseem', (0.1, 0.3, 0.05), 0.12, sss=0.1)
    maize_m = plant_material('maize_leaf', (0.2, 0.33, 0.1), 0.1, sss=0.1)
    reed_m = plant_material('reed', (0.3, 0.34, 0.14), 0.15)
    def grass(bm):
        for i in range(11):
            a = rnd.uniform(0, math.tau); r = rnd.uniform(0, 0.05)
            blade(bm, Vector((r * math.cos(a), r * math.sin(a), 0)), rnd.uniform(0.18, 0.42), rnd.uniform(0.012, 0.02),
                  Vector((math.cos(a), math.sin(a), 0)), rnd.uniform(0.2, 0.6), segs=3)
    def clover(bm):
        for i in range(14):   # stems + trefoil leaf pads
            a = rnd.uniform(0, math.tau); r = rnd.uniform(0, 0.09); h = rnd.uniform(0.12, 0.32)
            c = Vector((r * math.cos(a), r * math.sin(a), h))
            for k in range(3):
                b = a + k * math.tau / 3
                ctr = c + Vector((math.cos(b), math.sin(b), 0.1)) * 0.022
                v = [bm.verts.new(ctr + Vector((math.cos(b + q * math.tau / 6) * 0.02, math.sin(b + q * math.tau / 6) * 0.02, 0.004 * math.sin(q))))for q in range(6)]
                bm.faces.new(v)
            blade(bm, Vector((c.x * 0.6, c.y * 0.6, 0)), h, 0.004, Vector((math.cos(a), math.sin(a), 0)), 0.2, segs=2)
    def maize(bm):
        H = rnd.uniform(1.7, 2.3)
        blade(bm, Vector((0, 0, 0)), H, 0.045, Vector((0.05, 0, 0)), 0.02, segs=5)                       # stalk (flat card x2)
        blade(bm, Vector((0, 0, 0)), H, 0.045, Vector((0, 0.05, 0)), 0.02, segs=5, twist=1.57)
        for i in range(9):
            z = 0.25 + i * (H - 0.5) / 9; a = i * 2.4 + rnd.uniform(-0.3, 0.3)
            d = Vector((math.cos(a), math.sin(a), 0))
            prev = None
            for j in range(7):       # long arching leaf
                t = j / 6; L = rnd.uniform(0.6, 0.9)
                p = Vector((0, 0, z)) + d * L * t + Vector((0, 0, 0.35 * L * math.sin(t * 2.2) - 0.25 * t * t))
                w = 0.075 * math.sin(math.pi * min(1, t * 1.1 + 0.08)) + 0.004
                sd = Vector((-d.y, d.x, 0))
                a_, b_ = bm.verts.new(p - sd * w / 2), bm.verts.new(p + sd * w / 2)
                if prev: bm.faces.new((prev[0], prev[1], b_, a_))
                prev = (a_, b_)
        for k in range(6):           # tassel
            blade(bm, Vector((0, 0, H - 0.05)), 0.3, 0.008, Vector((math.cos(k), math.sin(k), 0)), 0.5, segs=2)
    def reed(bm):
        for i in range(9):
            a = rnd.uniform(0, math.tau); r = rnd.uniform(0, 0.12)
            blade(bm, Vector((r * math.cos(a), r * math.sin(a), 0)), rnd.uniform(0.9, 1.8), rnd.uniform(0.02, 0.035),
                  Vector((math.cos(a), math.sin(a), 0)), rnd.uniform(0.05, 0.3), segs=5)
    out = {}
    for name, fn, m, n in (('grass', grass, grass_m, 4), ('clover', clover, clover_m, 3), ('maize', maize, maize_m, 3), ('reed', reed, reed_m, 2)):
        vs = [plant_obj(f'plant_{name}_{i}', fn, m, col) for i in range(n)]
        pc = bpy.data.collections.get('plants_' + name) or bpy.data.collections.new('plants_' + name)
        for v in vs:
            for c in v.users_collection: c.objects.unlink(v)
            pc.objects.link(v); v.location = (0, 0, -50)
        if pc.name not in col.children: col.children.link(pc)
        out[name] = pc
    return out

# ---------------------------------------------------------------- scatter (hair particles, instanced)
def emitter(name, polys, col):
    """A hidden flat mesh that only emits instances (rows, patches)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    for quad in polys: bm.faces.new([bm.verts.new(v) for v in quad])
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); col.objects.link(o); o.hide_render = False
    return o

def scatter(o, coll, count, size=1.0, rand_size=0.35, seed=1, display=100):
    ps = o.modifiers.new('scatter', 'PARTICLE_SYSTEM').particle_system
    st = ps.settings; st.type = 'HAIR'; st.use_advanced_hair = True; st.count = count; st.hair_length = 1
    st.render_type = 'COLLECTION'; st.instance_collection = coll; st.use_collection_pick_random = True
    st.particle_size = size; st.size_random = rand_size; st.use_rotations = True; st.rotation_mode = 'OB_Z'
    st.phase_factor_random = 2.0; st.use_rotation_instance = False; st.display_percentage = display
    st.emit_from = 'FACE'; st.distribution = 'RAND'; ps.seed = seed
    o.show_instancer_for_render = False; o.show_instancer_for_viewport = False
    return ps

def build(fast=False):
    for c in list(bpy.data.collections):                      # previous plant libraries
        if c.name.startswith(('plants_', 'plant_lib')):
            for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.collections.remove(c)
    for m in list(bpy.data.meshes):
        if m.users == 0: bpy.data.meshes.remove(m)
    col = clear_collection('village_env')
    for c in list(col.children): col.children.unlink(c)
    k = 0.35 if fast else 1.0

    # terrain grid with height + vertex-colour masks
    me = bpy.data.meshes.new('terrain'); bm = bmesh.new()
    n = RES; st = SIZE / n; cx, cy = -5.0, -20.0
    vs = [[bm.verts.new((cx - SIZE / 2 + i * st, cy - SIZE / 2 + j * st, 0)) for i in range(n + 1)] for j in range(n + 1)]
    for v in bm.verts: v.co.z = height(v.co.x, v.co.y)
    for j in range(n):
        for i in range(n): bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    cl = bm.loops.layers.color.new('mask')
    for f in bm.faces:
        for l in f.loops:
            s, d, m_ = masks(l.vert.co.x, l.vert.co.y); l[cl] = (s, d, m_, 1)
    bm.to_mesh(me); bm.free()
    ter = bpy.data.objects.new('terrain', me); col.objects.link(ter); me.materials.append(terrain_material())
    for p in me.polygons: p.use_smooth = True

    # canal water: a ribbon following the canal centre line
    me = bpy.data.meshes.new('canal_water'); bm = bmesh.new(); prev = None
    for j in range(0, 181):
        y = cy - SIZE / 2 + j * SIZE / 180; x = canal_x(y); z = -0.32
        a, b = bm.verts.new((x - CANAL_W * 0.9, y, z)), bm.verts.new((x + CANAL_W * 0.9, y, z))
        if prev: bm.faces.new((prev[0], prev[1], b, a))
        prev = (a, b)
    bm.to_mesh(me); bm.free()
    wat = bpy.data.objects.new('canal_water', me); col.objects.link(wat); me.materials.append(water_material())

    lib_c = bpy.data.collections.new('plant_lib'); col.children.link(lib_c); lib_c.hide_render = False
    plants = make_plants(lib_c)

    # crops: berseem patches fill a plot; maize in rows 0.8 m apart
    clover, maize = [], []
    rects = {}
    for x in np.arange(-70, 60, 0.5):
        for y in np.arange(-70, 70, 0.5):
            f, ix, iy = is_field(x + 0.25, y + 0.25)
            if f: rects.setdefault((ix, iy), []).append((x, y))
    for key, cells in rects.items():
        kind = crop(*key)
        xs = [c[0] for c in cells]; ys = [c[1] for c in cells]
        x0, x1, y0, y1 = min(xs) + 0.3, max(xs) + 0.2, min(ys) + 0.3, max(ys) + 0.2
        if math.hypot((x0 + x1) / 2 + 5, (y0 + y1) / 2 + 20) > 70: continue          # only near the story spot
        z = lambda x, y: height(x, y) + 0.01
        if kind == 'clover':
            clover.append([(x0, y0, z(x0, y0)), (x1, y0, z(x1, y0)), (x1, y1, z(x1, y1)), (x0, y1, z(x0, y1))])
        elif kind == 'maize':
            xx = x0
            while xx < x1:
                maize.append([(xx - 0.05, y0, z(xx, y0)), (xx + 0.05, y0, z(xx, y0)), (xx + 0.05, y1, z(xx, y1)), (xx - 0.05, y1, z(xx, y1))]); xx += 0.8
    if clover:
        e = emitter('crop_berseem', clover, col); area = sum(abs((q[1][0] - q[0][0]) * (q[2][1] - q[1][1])) for q in clover)
        scatter(e, plants['clover'], int(area * 9 * k), 1.0, 0.3, 2)
    if maize:
        e = emitter('crop_maize', maize, col); L = sum(abs(q[2][1] - q[1][1]) for q in maize)
        scatter(e, plants['maize'], int(L / 0.35 * k), 1.0, 0.25, 3)

    # grass: patches everywhere that isn't field, road, yard or water (sampled on a grid)
    rnd = random.Random(9); gq, rq = [], []
    for x in np.arange(-45, 35, 2.0):
        for y in np.arange(-65, 25, 2.0):
            px, py = x + 1, y + 1
            s, d, m_ = masks(px, py)
            dc = abs(px - canal_x(py))
            if CANAL_W - 0.2 < dc < CANAL_W + 1.6: rq.append((px, py))
            if s > 0.1 or d > 0.1 or dc < CANAL_W + 0.3: continue
            gq.append((px, py))
    def quads(pts, h=1.0):
        return [[(x - h, y - h, height(x - h, y - h)), (x + h, y - h, height(x + h, y - h)), (x + h, y + h, height(x + h, y + h)), (x - h, y + h, height(x - h, y + h))] for x, y in pts]
    near = [p for p in gq if math.hypot(p[0] + 6, p[1] + 26) < 24]; far = [p for p in gq if p not in near]
    e = emitter('grass_near', quads(near), col); scatter(e, plants['grass'], int(len(near) * 4 * 45 * k), 1.25, 0.5, 4)
    e = emitter('grass_far', quads(far), col); scatter(e, plants['grass'], int(len(far) * 4 * 10 * k), 1.4, 0.5, 6)
    e = emitter('reed_banks', quads(rq, 0.6), col); scatter(e, plants['reed'], int(len(rq) * 5 * k), 1.0, 0.4, 5)
    shade_auto(ter, 60)
    return col

if __name__ != 'env_scene':
    build(globals().get('FAST', False))
    print('env built')
