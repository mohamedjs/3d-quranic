# Assembles blender/v2/village_v2.blend: a preview vignette with the SAME layout as the game
# (Blender x, y = game x, -z; z up). Assets are appended from env.blend (run build_all.py first).
#   python3 blender/v2/bg.py blender/v2/env/village.py env_village
import sys, importlib; sys.path.insert(0, '/var/www/html/old/3d-quranic/blender/v2/env')
for m in ('tk', 'water', 'gameport'):
    if m in sys.modules: importlib.reload(sys.modules[m])
import tk, water, gameport as G, math, random, bmesh
from tk import *
from mathutils import Vector

reset()
ENV = V2 + 'env/env.blend'
NAMES = ['house_a', 'house_b', 'house_c', 'mastaba', 'palm_a', 'palm_b', 'palm_c', 'sycamore', 'bougainvillea', 'well', 'shaduf',
         'sluice', 'footbridge', 'stall', 'garden_wall', 'fence', 'hay', 'jar', 'jar_b', 'basket', 'hoe', 'pot_plant', 'stream',
         'canal_bank', 'canal_stones', 'crop_berseem', 'crop_maize', 'crop_wheat', 'crop_cotton', 'crop_cabbage', 'grass_a', 'grass_b',
         'grass_c', 'reeds', 'wildflowers', 'field_bund']
want = set(NAMES) | {n + '_outline' for n in NAMES} | {'stream_water'}
with bpy.data.libraries.load(ENV, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n in want]
LIB = {}
for n in NAMES:
    c = bpy.data.collections.new('lib_' + n); LIB[n] = c
    for suffix in ('', '_outline'):
        o = bpy.data.objects.get(n + suffix)
        if o: o.location = (0, 0, 0); o.parent = None; c.objects.link(o)
    if n == 'stream':
        o = bpy.data.objects.get('stream_water'); o.location = (0, 0, 0); c.objects.link(o)
look(sun_rot=(math.radians(66), 0, math.radians(135)), strength=3.2)
sc = bpy.context.scene
scene_col = sc.collection
def coll(name):
    c = bpy.data.collections.new(name); scene_col.children.link(c); return c
C_TER, C_WAT, C_BLD, C_PROP, C_TREE, C_CROP = (coll(n) for n in ('terrain', 'water', 'buildings', 'props', 'trees', 'crops'))
coll('cast')   # the character agent's GLBs are dropped in here

def B2(x, z, y=None):   # game -> Blender location
    return Vector((x, -z, G.height(x, z) if y is None else y))

def inst(model, x, z, y=None, rot=0.0, s=(1, 1, 1), col=None, tilt=0.0, name=None):
    e = bpy.data.objects.new(name or model, None); e.instance_type = 'COLLECTION'; e.instance_collection = LIB[model]
    e.location = B2(x, z, y); e.rotation_euler = (tilt, 0, rot)
    e.scale = (s[0], s[2], s[1]) if isinstance(s, (tuple, list)) else (s, s, s)
    (col or C_PROP).objects.link(e); return e

# ---------------------------------------------------------------------------------------
# terrain: the game's height function, flat painted patches per face (fields, paths, banks)
X0, X1, Z0, Z1, STEP = -80.0, 70.0, -62.0, 96.0, 0.7
HEX = lambda h: hexc(h)
PAINT = dict(mud_dark='#6A4E34', bank='#80603F', path='#DCC28F', bund='#9C7A50', berseem='#5FA03A', wheat='#D7B85C', maize='#71923A',
             greens='#86B44E', village='#CFAF7C', village_grass='#A9B862', grass='#8DB04C', grass2='#7AA443', grass3='#9DBE5A', yard='#D8BA88')
PC = {k: HEX(v) for k, v in PAINT.items()}
def paint(x, z, h):
    if h < -0.25: return 'mud_dark'
    if G.waterDist(x, z) < 0.7 and h < 0.95: return 'bank'
    if G.pathDist(x, z) < 1.8: return 'path'
    t = G.fieldPlot(x, z)
    if t >= 0: return ('berseem', 'wheat', 'maize', 'greens', 'bund')[t]
    if math.hypot(x - G.HOME['x'] - 3.5, z - G.HOME['z']) < 4.5: return 'yard'
    n = G.fbm(x * 0.09, z * 0.09)
    if math.hypot(x, z) < 44 or (abs(x) < 15 and -62 < z < -8): return 'village' if n < 0.12 else 'village_grass'
    return 'grass' if n < -0.1 else ('grass2' if n < 0.2 else 'grass3')
nx, nz = int((X1 - X0) / STEP) + 1, int((Z1 - Z0) / STEP) + 1
H = [[G.height(X0 + i * STEP, Z0 + j * STEP) for i in range(nx)] for j in range(nz)]
verts = [(X0 + i * STEP, -(Z0 + j * STEP), H[j][i]) for j in range(nz) for i in range(nx)]
faces, fcol = [], []
keys = list(PAINT)
for j in range(nz - 1):
    for i in range(nx - 1):
        a = j * nx + i
        faces.append((a, a + nx, a + nx + 1, a + 1))
        x, z = X0 + (i + 0.5) * STEP, Z0 + (j + 0.5) * STEP
        fcol.append(keys.index(paint(x, z, (H[j][i] + H[j + 1][i + 1]) / 2)))
me = bpy.data.meshes.new('terrain'); me.from_pydata(verts, [], faces)
ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
cols = []
for f in fcol: cols += [*PC[keys[f]], 1.0] * 4
ca.data.foreach_set('color', cols)
for p in me.polygons: p.use_smooth = True
tm = bpy.data.materials.new('toon_terrain'); n_, l_ = tk._nodes(tm); n_.clear()
out = n_.new('ShaderNodeOutputMaterial'); out.name = 'OUT'
pbr = n_.new('ShaderNodeBsdfPrincipled'); pbr.name = 'PBR'
at = n_.new('ShaderNodeVertexColor'); at.layer_name = 'Col'
grp = n_.new('ShaderNodeGroup'); grp.node_tree = toon_group(); grp.name = 'TOON'; grp.inputs['Shadow'].default_value = (*SHADOW_TINT, 1)
l_.new(at.outputs['Color'], grp.inputs['Color']); l_.new(at.outputs['Color'], pbr.inputs['Base Color']); l_.new(grp.outputs[0], out.inputs['Surface'])
me.materials.append(tm)
ter = bpy.data.objects.new('terrain', me); C_TER.objects.link(ter)
far = B(0); far.box((900, 900, 1), (0, -20, 0.45), 'toon_ground_green', smooth=False)
fo = far.obj('far_plain', C_TER)
print('terrain', len(faces), flush=True)

# ---------------------------------------------------------------------------------------
# water: UV'd toon strips for the canals / road canal / river + a plain sheet underneath
def strip_along(name, pts_game, width):
    return water.water_strip(name, [(x, -z, 0) for x, z in pts_game], width, C_WAT, z=G.WATER_Y)
for c in (-15, 15):
    zt = G.riverZ(c) + 2
    strip_along(f'canal_{c}', [(c, 15.5 + k * (zt - 15.5) / 30) for k in range(31)], 2.7)
strip_along('road_canal', [(4, 16.5 + k * 1.5) for k in range(28)], 3.1)
strip_along('road_canal_s', [(5, -95 + k * 1.5) for k in range(26)], 3.1)
strip_along('river', [(x, G.riverZ(x)) for x in range(-90, 82, 3)], [14.0] * len(range(-90, 82, 3)))
wp = bpy.data.materials.new('toon_water_plain'); n_, l_ = tk._nodes(wp); n_.clear()
o_ = n_.new('ShaderNodeOutputMaterial'); em = n_.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*hexc(water.WATER['deep']), 1)
l_.new(em.outputs[0], o_.inputs['Surface'])
pb = B(0); pb.box((200, 220, 0.02), (-5, -20, G.WATER_Y - 0.03), 'toon_water', smooth=False); sheet = pb.obj('water_sheet', C_WAT); sheet.data.materials[0] = wp

# ---------------------------------------------------------------------------------------
# buildings + props: exactly the game's placements
VP, placed, gardens = G.village_placements()
CP = G.canal_placements()
blocked = []
for p in VP + CP:
    m = p['model']
    col = C_BLD if m.startswith('house') or m == 'mastaba' else C_PROP
    inst(m, p['x'], p['z'], p['y'], p['rot'], (p['sx'], p['sy'], p['sz']), col, tilt=p.get('tilt', 0.0))
    if m.startswith('house'): blocked.append((p['x'], p['z'], 3.6 * max(p['sx'], p['sz'])))
    elif m in ('well', 'stall'): blocked.append((p['x'], p['z'], 1.8))
def is_blocked(x, z, pad=0.0):
    return any(math.hypot(x - bx, z - bz) < R + pad for bx, bz, R in blocked)
# canal banks: stone/mud edge pieces along the canal by grandma's house (x = -15), both sides
for k in range(12):
    z = 20.5 + k * 4.0
    if abs(z - 34.5) < 2.5: continue
    inst('canal_bank', -15 - 1.95, z, G.WATER_Y + 0.5 + 0.02, rot=0.0, col=C_PROP)
    inst('canal_bank', -15 + 1.95, z, G.WATER_Y + 0.5 + 0.02, rot=math.pi, col=C_PROP)
# a little flower bed + bougainvillea by grandma's door, pots on the square
hx, hz, hr = G.HOME['x'], G.HOME['z'], G.HOME['rot']
Wm = lambda mx, mz: (hx + mx * math.cos(hr) + mz * math.sin(hr), hz - mx * math.sin(hr) + mz * math.cos(hr))
bx, bz = Wm(3.35, 2.1); inst('bougainvillea', bx, bz, rot=0.6, s=1.15, col=C_TREE)
px, pz = Wm(-2.9, 2.55); inst('pot_plant', px, pz, rot=1.0, s=1.1)
for gx, gz in gardens:
    if -60 < gz < 90: inst('bougainvillea' if (int(gx * 7 + gz) % 3 == 0) else 'pot_plant', gx, gz, rot=gx + gz, s=1.0)

# ---------------------------------------------------------------------------------------
# palms + shade trees (the game's rules, own RNG)
rnd = random.Random(5); spots = []
def try_palm(x, z, force=False):
    h = G.height(x, z)
    if not force:
        if h < G.WATER_Y + 0.4 or G.pathDist(x, z) < 2.6 or G.fieldPlot(x, z) >= 0 or is_blocked(x, z, 1.3): return
        if any(math.hypot(p[0] - x, p[1] - z) < 3.2 for p in spots): return
    spots.append((x, z, h))
try_palm(-13.4, 23.2, True); try_palm(-12.8, 30.4, True)                       # framing grandma's house, by the canal
for i in range(70): a = rnd.uniform(0, 6.3); d = 12 + rnd.uniform(0, 30); try_palm(math.cos(a) * d, math.sin(a) * d)
for i in range(30): try_palm(-80 + rnd.uniform(0, 160), 11 + rnd.uniform(0, 1.5))
for line in G.ROAD_CANALS:
    for j in range(len(line) - 1):
        (ax, az), (bx_, bz_) = line[j], line[j + 1]; L = math.hypot(bx_ - ax, bz_ - az); nx_, nz_ = -(bz_ - az) / L, (bx_ - ax) / L
        d = 3
        while d < L:
            if rnd.random() < 0.8:
                for side in (-1, 1): try_palm(ax + (bx_ - ax) * d / L + nx_ * side * 3.3, az + (bz_ - az) * d / L + nz_ * side * 3.3)
            d += 6.5 + rnd.uniform(0, 3)
for i in range(110): x = -80 + rnd.uniform(0, 150); s = 1 if rnd.random() < 0.5 else -1; try_palm(x, G.riverZ(x) + s * (8 + rnd.uniform(0, 9)))
for i in range(60): try_palm(rnd.uniform(-80, 70), rnd.uniform(-60, 95))
for i, (x, z, h) in enumerate(spots):
    sc_ = 0.85 + rnd.uniform(0, 0.35)
    inst(('palm_a', 'palm_b', 'palm_c')[i % 3], x, z, h - 0.1, rnd.uniform(0, 6.3), sc_, C_TREE)
trees = [(-4.6, 31.8), (5.2, 52), (-5.2, 58), (5.2, 63), (-26, 6), (22, -2), (-36, -4)]
for x, z in trees:
    if not is_blocked(x, z, 1.0): inst('sycamore', x, z, rot=rnd.uniform(0, 6.3), s=rnd.uniform(0.85, 1.1), col=C_TREE)
print('palms', len(spots), flush=True)

# ---------------------------------------------------------------------------------------
# crops / grass / reeds / flowers: instanced with Geometry Nodes (points + rot/scale attributes)
def scatter(model, pts, col=C_CROP):
    if not pts: return None
    me = bpy.data.meshes.new('pts_' + model); me.from_pydata([B2(x, z, y) for x, z, y, r_, s_ in pts], [], [])
    for nm, idx in (('rot', 3), ('scl', 4)):
        a = me.attributes.new(nm, 'FLOAT', 'POINT'); a.data.foreach_set('value', [p[idx] for p in pts])
    o = bpy.data.objects.new('scatter_' + model, me); col.objects.link(o)
    ng = bpy.data.node_groups.new('GN_' + model, 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N, Lk = ng.nodes, ng.links
    gi, go = N.new('NodeGroupInput'), N.new('NodeGroupOutput')
    iop = N.new('GeometryNodeInstanceOnPoints')
    ci = N.new('GeometryNodeCollectionInfo'); ci.inputs['Collection'].default_value = LIB[model]
    try: ci.inputs['Reset Children'].default_value = True
    except Exception: pass
    ra = N.new('GeometryNodeInputNamedAttribute'); ra.data_type = 'FLOAT'; ra.inputs['Name'].default_value = 'rot'
    sa = N.new('GeometryNodeInputNamedAttribute'); sa.data_type = 'FLOAT'; sa.inputs['Name'].default_value = 'scl'
    cx = N.new('ShaderNodeCombineXYZ'); Lk.new(ra.outputs['Attribute'], cx.inputs['Z'])
    er = N.new('FunctionNodeEulerToRotation') if hasattr(bpy.types, 'FunctionNodeEulerToRotation') else None
    if er: Lk.new(cx.outputs[0], er.inputs[0]); Lk.new(er.outputs[0], iop.inputs['Rotation'])
    else: Lk.new(cx.outputs[0], iop.inputs['Rotation'])
    Lk.new(sa.outputs['Attribute'], iop.inputs['Scale'])
    Lk.new(gi.outputs[0], iop.inputs['Points']); Lk.new(ci.outputs[0], iop.inputs['Instance']); Lk.new(iop.outputs[0], go.inputs[0])
    md = o.modifiers.new('scatter', 'NODES'); md.node_group = ng
    return o

rs = random.Random(9)
buckets = {k: [] for k in ('crop_berseem', 'crop_wheat', 'crop_maize', 'crop_cotton', 'crop_cabbage', 'field_bund', 'grass_a', 'grass_b', 'grass_c', 'reeds', 'wildflowers')}
x = X0
while x < X1:
    z = Z0
    while z < Z1:
        t = G.fieldPlot(x, z)
        if t >= 0 and t != 4:
            jx = x + rs.uniform(-0.1, 0.1); h = G.height(jx, z)
            if t == 0: buckets['crop_berseem'].append((jx, z, h - 0.02, rs.uniform(0, 6.3), rs.uniform(1.0, 1.35)))
            elif t == 1: buckets['crop_wheat'].append((jx, z, h - 0.03, rs.uniform(0, 6.3), rs.uniform(0.9, 1.15)))
            elif t == 2:
                if int(round(z / 0.6)) % 2 == 0 and rs.random() < 0.85: buckets['crop_maize'].append((jx, z, h - 0.02, rs.uniform(0, 6.3), rs.uniform(0.85, 1.1)))
            else:
                k = 'crop_cotton' if G.jhash(math.floor((x + 1000) / 15), math.floor((z + 1000) / 10)) < 0.5 else 'crop_cabbage'
                if int(round(z / 0.6)) % 2 == 0: buckets[k].append((jx, z, h - 0.02, rs.uniform(0, 6.3), rs.uniform(0.9, 1.2)))
        z += 0.6
    x += 0.8
# field bunds: 4 m pieces along plot edges (x = 15k lines run along z, z = 10k lines run along x)
xs = [k * 15 - 1000 + 0.45 for k in range(int((X0 + 1000) / 15), int((X1 + 1000) / 15) + 1)]
zs = [k * 10 - 1000 + 0.35 for k in range(int((Z0 + 1000) / 10), int((Z1 + 1000) / 10) + 1)]
for xx in xs:
    z = Z0
    while z < Z1:
        if G.fieldPlot(xx, z) == 4 and G.fieldPlot(xx, z + 1.5) == 4: buckets['field_bund'].append((xx, z + 2, G.height(xx, z + 2) - 0.1, math.pi / 2, 1.0))
        z += 4
for zz in zs:
    x = X0
    while x < X1:
        if G.fieldPlot(x, zz) == 4 and G.fieldPlot(x + 1.5, zz) == 4: buckets['field_bund'].append((x + 2, zz, G.height(x + 2, zz) - 0.1, 0.0, 1.0))
        x += 4
# grass on verges, patchy village ground and banks; reeds + flowers by the water
for i in range(26000):
    x, z = rs.uniform(X0, X1), rs.uniform(Z0, Z1)
    h = G.height(x, z)
    if h < G.WATER_Y - 0.3 or is_blocked(x, z, 0.3): continue
    wd = G.waterDist(x, z); t = G.fieldPlot(x, z); pd = G.pathDist(x, z)
    if wd < 1.4 and G.WATER_Y - 0.3 < h < G.WATER_Y + 1.2:
        if rs.random() < 0.55: buckets['reeds'].append((x, z, h - 0.05, rs.uniform(0, 6.3), rs.uniform(0.8, 1.25)))
        continue
    if t >= 0 and t != 4: continue
    if pd < 1.2: continue
    village = math.hypot(x, z) < 44 or (abs(x) < 15 and -62 < z < -8)
    if village and G.fbm(x * 0.09, z * 0.09) < 0.12 and rs.random() < 0.9: continue
    r_ = rs.random()
    if r_ < 0.07: buckets['wildflowers'].append((x, z, h - 0.02, rs.uniform(0, 6.3), rs.uniform(0.9, 1.3)))
    else:
        k = 'grass_c' if (village and rs.random() < 0.5) else ('grass_b' if (t == 4 or pd < 3.5 or rs.random() < 0.35) else 'grass_a')
        buckets[k].append((x, z, h - 0.03, rs.uniform(0, 6.3), rs.uniform(0.9, 1.4)))
for k, v in buckets.items():
    scatter(k, v); print('scatter', k, len(v), flush=True)

# ---------------------------------------------------------------------------------------
# cameras + renders
g0 = G.height(G.HOME['x'], G.HOME['z'])
shot = camera('ShotCam', (-1.3, -20.6, g0 + 1.65), (-7.7, -25.2, g0 + 1.25), lens=30)
wide = camera('WideCam', (26, 6, 26), (-6, -32, 0), lens=28)
sc.camera = shot
render(PREV + 'village_home.png', shot, res=(1600, 900))
render(PREV + 'village_wide.png', wide, res=(1600, 900))
sc.camera = shot
bpy.ops.wm.save_as_mainfile(filepath=V2 + 'village_v2.blend')
print('VILLAGE_OK', flush=True)
