# Tiny instanced farmland / wild plants (<= 800 tris incl. outline). Origin at the ground.
# Blade-type plants (grass, wheat, reeds) have no hull outline (flagged 'n' materials / skip).
import math, random
from mathutils import Vector
from tk import B

def blade(b, base, yaw, L, w, bend, mat, segs=3, lean=0.0):
    d = Vector((math.cos(yaw), math.sin(yaw), 0))
    pts = [Vector(base) + d * (bend * L * (i / segs) ** 2 + lean * L * i / segs) + Vector((0, 0, L * (i / segs) * (1 - 0.25 * bend * (i / segs))))
           for i in range(segs + 1)]
    ws = [w * (1 - (i / segs) ** 1.5) for i in range(segs + 1)]; ws[-1] = 0
    b.strip(pts, ws, mat=mat, side=(-d.y, d.x, 0))
    return pts[-1]

def berseem(seed=41):
    """Egyptian clover: soft round mounds with a few white flower heads."""
    rnd = random.Random(seed); b = B(seed)
    for i in range(3):
        a = i * 2.1 + rnd.uniform(0, 0.5); r = 0.14 if i else 0.0
        b.ball(rnd.uniform(0.2, 0.26), (math.cos(a) * r, math.sin(a) * r, 0.06), 'toon_berseem', scale=(1.15, 1.15, 0.7), sub=1, wobble=0.03, freq=6)
    for i in range(5):
        a = rnd.uniform(0, math.tau); r = rnd.uniform(0.05, 0.28)
        b.ball(0.026, (math.cos(a) * r, math.sin(a) * r, 0.19 + rnd.uniform(0, 0.05)), 'toon_berseem_flower', sub=0, scale=(1, 1, 1.3))
    return b

def maize(seed=42):
    rnd = random.Random(seed); b = B(seed)
    H = 1.9 + rnd.uniform(-0.1, 0.2)
    b.tube([(0, 0, 0), (0.02, 0, H * 0.5), (0.05, 0.02, H)], [0.035, 0.028, 0.015], 'toon_maize', sides=5, cap=False)
    for i in range(7):
        z = 0.25 + i * (H * 0.75 / 7); yaw = i * 2.5 + rnd.uniform(-0.3, 0.3)
        L = 0.75 - i * 0.05
        d = Vector((math.cos(yaw), math.sin(yaw), 0))
        pts = [Vector((0, 0, z)) + d * (L * t) + Vector((0, 0, L * (0.7 * t - 0.9 * t * t))) for t in (0, 0.25, 0.5, 0.75, 1.0)]
        b.strip(pts, [0.02, 0.09, 0.085, 0.06, 0.0], mat='toon_maize', side=(-d.y, d.x, 0))
    for i in range(4):   # tassel
        a = i * 1.6
        blade(b, (0.05, 0.02, H), a, 0.3, 0.03, 0.8, 'toon_maize_tassel', segs=2)
    b.ball(0.05, (0.06, 0.0, H * 0.55), 'toon_maize_cob', scale=(1, 1, 2.6), sub=1, rot=(0, 0.35, 0))
    return b

def wheat(seed=43):
    rnd = random.Random(seed); b = B(seed)
    for i in range(10):
        a = rnd.uniform(0, math.tau); r = rnd.uniform(0, 0.12)
        base = Vector((math.cos(a) * r, math.sin(a) * r, 0)); yaw = rnd.uniform(0, math.tau)
        top = blade(b, base, yaw, rnd.uniform(0.8, 1.0), 0.035, 0.12, 'toon_wheat_green' if i % 3 == 0 else 'toon_wheat', segs=2, lean=0.08)
        b.ball(0.03, top + Vector((0, 0, 0.05)), 'toon_wheat', scale=(1, 1, 2.6), sub=0)
    for i in range(4):
        blade(b, (0, 0, 0), i * 1.7, 0.4, 0.05, 0.9, 'toon_wheat_green', segs=2)
    return b

def cotton(seed=44):
    """Low bushy crop with white bolls."""
    rnd = random.Random(seed); b = B(seed)
    for i in range(3):
        a = i * 2.1; r = 0.1 if i else 0
        b.ball(rnd.uniform(0.2, 0.25), (math.cos(a) * r, math.sin(a) * r, 0.32 + rnd.uniform(-0.05, 0.08)), 'toon_leaf' if i else 'toon_leaf_light', scale=(1, 1, 0.8), sub=1, wobble=0.03, freq=6)
    b.cyl(0.02, 0.015, 0.3, (0, 0, 0.15), 'toon_bark', verts=4)
    for i in range(6):
        a = rnd.uniform(0, math.tau); r = rnd.uniform(0.12, 0.26)
        b.ball(0.05, (math.cos(a) * r, math.sin(a) * r, 0.3 + rnd.uniform(0, 0.2)), 'toon_cotton', sub=0)
    return b

def cabbage(seed=45):
    """Young greens / cabbage: a round head in cupped leaves."""
    rnd = random.Random(seed); b = B(seed)
    b.ball(0.14, (0, 0, 0.13), 'toon_cabbage', scale=(1, 1, 0.9), sub=1, wobble=0.015, freq=8)
    for i in range(6):
        a = i * math.tau / 6 + rnd.uniform(-0.2, 0.2)
        b.uvball(0.17, (math.cos(a) * 0.14, math.sin(a) * 0.14, 0.06), 'toon_cabbage_dark', scale=(1.1, 0.8, 0.45), seg=6, rings=4, rot=(0, -0.5, a), cut=-0.2)
    return b

def grass(variant=0, seed=46):
    rnd = random.Random(seed + variant * 17); b = B(seed + variant)
    n, L, mats = [(9, (0.28, 0.42), ('toon_grass', 'toon_grass_light')),
                  (12, (0.45, 0.7), ('toon_grass', 'toon_grass', 'toon_grass_light')),
                  (9, (0.3, 0.5), ('toon_grass_dry', 'toon_grass_dry', 'toon_grass'))][variant]
    for i in range(n):
        a = rnd.uniform(0, math.tau); r = rnd.uniform(0, 0.08)
        blade(b, (math.cos(a) * r, math.sin(a) * r, 0), a + rnd.uniform(-0.4, 0.4), rnd.uniform(*L), rnd.uniform(0.06, 0.09),
              rnd.uniform(0.4, 0.9), mats[i % len(mats)], segs=3)
    return b

def reeds(seed=49):
    rnd = random.Random(seed); b = B(seed)
    for i in range(9):
        a = rnd.uniform(0, math.tau); r = rnd.uniform(0, 0.18)
        top = blade(b, (math.cos(a) * r, math.sin(a) * r, 0), a, rnd.uniform(1.3, 1.9), 0.06, rnd.uniform(0.05, 0.3), 'toon_reed', segs=3)
        if i % 3 == 0:
            b.cyl(0.035, 0.03, 0.22, top + Vector((0, 0, -0.18)), 'toon_reed_head', verts=5)
    return b

def wildflowers(seed=50):
    rnd = random.Random(seed); b = B(seed)
    cols = ('toon_flower_yellow', 'toon_flower_white', 'toon_flower_purple', 'toon_flower_red')
    for i in range(5):
        blade(b, (0, 0, 0), i * 1.3, 0.22, 0.06, 0.8, 'toon_grass', segs=2)
    for i in range(6):
        a = rnd.uniform(0, math.tau); r = rnd.uniform(0.02, 0.15)
        top = blade(b, (math.cos(a) * r, math.sin(a) * r, 0), a, rnd.uniform(0.25, 0.42), 0.02, 0.1, 'toon_grass', segs=2)
        m = cols[i % 4]
        for k in range(5):   # five petals around a centre
            pa = k / 5 * math.tau
            b.poly([top, top + Vector((math.cos(pa - 0.35) * 0.05, math.sin(pa - 0.35) * 0.05, 0.01)), top + Vector((math.cos(pa) * 0.075, math.sin(pa) * 0.075, 0.02)),
                    top + Vector((math.cos(pa + 0.35) * 0.05, math.sin(pa + 0.35) * 0.05, 0.01))], m)
        b.ball(0.015, top + Vector((0, 0, 0.02)), 'toon_flower_yellow' if m != 'toon_flower_yellow' else 'toon_produce', sub=0)
    return b

def field_bund(seed=51):
    """4 m earth bund (ridge between plots) with a furrow along each side. Runs along X."""
    import bmesh
    rnd = random.Random(seed); b = B(seed)
    prof = [(-0.6, 0.0), (-0.45, -0.05), (-0.3, 0.02), (-0.15, 0.16), (0.0, 0.2), (0.15, 0.16), (0.3, 0.02), (0.45, -0.05), (0.6, 0.0)]
    n = 10
    bm = bmesh.new(); rows = []
    for i in range(n + 1):
        x = -2 + 4 * i / n
        rows.append([bm.verts.new((x, y, z + (0.02 * math.sin(x * 3.1 + y * 5) if abs(y) < 0.5 else 0))) for y, z in prof])
    for i in range(n):
        for k in range(len(prof) - 1):
            bm.faces.new((rows[i][k], rows[i + 1][k], rows[i + 1][k + 1], rows[i][k + 1]))
    b.put(bm, 'toon_earth', None, True)
    for i in range(6):   # grass tufts on the ridge
        x = -1.8 + i * 0.7 + rnd.uniform(-0.1, 0.1)
        for k in range(3):
            blade(b, (x, rnd.uniform(-0.05, 0.05), 0.18), rnd.uniform(0, math.tau), 0.22, 0.05, 0.6, 'toon_grass', segs=2)
    return b

PLANTS = {
    'crop_berseem': berseem, 'crop_maize': maize, 'crop_wheat': wheat, 'crop_cotton': cotton, 'crop_cabbage': cabbage,
    'grass_a': lambda: grass(0), 'grass_b': lambda: grass(1), 'grass_c': lambda: grass(2),
    'reeds': reeds, 'wildflowers': wildflowers, 'field_bund': field_bund,
}
