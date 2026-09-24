# Stylized date palms (anime): ringed trunk, chunky serrated fronds with a folded spine,
# date bunches under the crown. Also the sycamore / nabq shade tree and a bougainvillea bush.
import math, random
from mathutils import Vector, Matrix, Euler
from tk import B

def frond(b, top, yaw, pitch, L, droop, w, mat, rnd, segs=7):
    """Arching frond from `top`: V-folded ribbon with serrated (zig-zag) edges."""
    d = Vector((math.cos(yaw), math.sin(yaw), 0)); side = Vector((-d.y, d.x, 0))
    pts = []
    for i in range(segs + 1):
        t = i / segs
        horiz = L * t * math.cos(pitch)
        vert = L * t * math.sin(pitch) - droop * L * t * t
        pts.append(Vector(top) + d * horiz + Vector((0, 0, vert)))
    import bmesh
    bm = bmesh.new(); Ls, Cs, Rs = [], [], []
    for i, p in enumerate(pts):
        t = i / segs
        env = math.sin(min(1, t * 1.15) * math.pi) ** 0.7 * w   # widest in the middle
        tooth = 1.0 if i % 2 else 0.62
        ww = env * (tooth if 0 < i < segs else 1)
        tang = (pts[min(i + 1, segs)] - pts[max(i - 1, 0)]).normalized()
        nrm = side.cross(tang).normalized()
        fold = nrm * ww * 0.35
        Ls.append(bm.verts.new(p - side * ww - fold * 0.2)); Cs.append(bm.verts.new(p + fold * 0.45)); Rs.append(bm.verts.new(p + side * ww - fold * 0.2))
    for i in range(segs):
        bm.faces.new((Ls[i], Cs[i], Cs[i + 1], Ls[i + 1])); bm.faces.new((Cs[i], Rs[i], Rs[i + 1], Cs[i + 1]))
    b.put(bm, mat, None, True)
    return pts

def trunk(b, h, lean, rnd, r0=0.3, r1=0.2, mat='toon_bark', rings=None):
    n = rings or int(h / 0.28)
    pts = [Vector((lean * (i / n) ** 2, lean * 0.3 * (i / n) ** 2, h * i / n)) for i in range(n + 1)]
    rad = [r1 + (r0 - r1) * (1 - i / n) ** 2 + (0.12 if i == 0 else 0) for i in range(n + 1)]
    # ringed look: duplicate each ring with a smaller radius just above it (stacked "boots")
    P, R = [], []
    for i in range(n + 1):
        P.append(pts[i]); R.append(rad[i] * 1.05)
        if i < n:
            P.append(pts[i].lerp(pts[i + 1], 0.55)); R.append(rad[i] * 0.9)
    b.tube(P, R, mat, sides=8, wobble=0.0, ring_fn=lambda i, k: 1 + 0.04 * math.sin(k * 2.1 + i))
    return pts[-1]

def palm(key, h, lean, nfr, droop, seed, dry=3, bunches=3):
    rnd = random.Random(seed); b = B(seed)
    top = trunk(b, h, lean, rnd)
    b.ball(0.32, top + Vector((0, 0, 0.05)), 'toon_bark_dark', scale=(1, 1, 0.8), sub=1)
    for i in range(nfr):
        young = i >= nfr - 3
        yaw = i * 2.39996 + rnd.uniform(-0.15, 0.15)
        pitch = 1.1 if young else rnd.uniform(0.35, 0.8)
        L = rnd.uniform(2.6, 3.2) * (0.7 if young else 1.0)
        frond(b, top, yaw, pitch, L, (0.25 if young else droop) * rnd.uniform(0.85, 1.15), rnd.uniform(0.36, 0.44),
              'toon_frond_light' if (young or i % 3 == 0) else 'toon_frond', rnd)
    for i in range(dry):
        frond(b, top - Vector((0, 0, 0.25)), i * 2.1 + 0.7, -1.15 + rnd.uniform(-0.15, 0.15), rnd.uniform(1.6, 2.1), 0.05, 0.3, 'toon_frond_dry', rnd, segs=5)
    for i in range(bunches):
        a = i * math.tau / bunches + rnd.uniform(0, 0.8)
        p = top + Vector((math.cos(a) * 0.4, math.sin(a) * 0.4, -0.45))
        b.cyl(0.03, 0.03, 0.5, top + Vector((math.cos(a) * 0.22, math.sin(a) * 0.22, -0.12)), 'toon_dates_gold', rot=(math.sin(a) * 0.9, -math.cos(a) * 0.9, 0), verts=5)
        b.ball(0.2, p, 'toon_dates' if i % 2 == 0 else 'toon_dates_gold', scale=(0.9, 0.9, 1.35), sub=1, wobble=0.03, freq=9)
    return b

PALMS = {'palm_a': (7.0, 0.8, 16, 0.55, 11), 'palm_b': (9.0, 1.6, 18, 0.62, 12), 'palm_c': (5.0, 0.35, 14, 0.45, 13)}

def build_palm(name):
    h, lean, nfr, droop, seed = PALMS[name]
    return palm(name, h, lean, nfr, droop, seed)

def canopy(b, center, radius, n, rnd, mats=('toon_leaf', 'toon_leaf_light', 'toon_leaf_dark'), squash=0.7, sub=2):
    """Ghibli-style cloud canopy: overlapping lumpy balls, lighter on top."""
    for i in range(n):
        a = rnd.uniform(0, math.tau); r = radius * rnd.uniform(0.2, 0.75)
        z = rnd.uniform(-0.3, 0.45) * radius * squash
        p = Vector(center) + Vector((math.cos(a) * r, math.sin(a) * r, z))
        s = radius * rnd.uniform(0.38, 0.55)
        m = mats[1] if z > radius * 0.15 else (mats[2] if z < -radius * 0.15 else mats[0])
        b.ball(s, p, m, scale=(1, 1, 0.8), sub=sub, wobble=s * 0.12, freq=2.5 / s)

def sycamore(seed=21):
    """جميز / nabq shade tree: thick short trunk splitting into limbs, broad cloud canopy."""
    rnd = random.Random(seed); b = B(seed)
    b.tube([(0, 0, -0.2), (0.05, 0, 1.0), (0.1, 0.05, 2.0)], [0.55, 0.42, 0.36], 'toon_bark', sides=10, wobble=0.05)
    tips = []
    for i in range(4):
        a = i * math.tau / 4 + 0.4
        tip = Vector((math.cos(a) * 1.9, math.sin(a) * 1.9, 4.0 + rnd.uniform(-0.3, 0.4)))
        b.tube([(0.1, 0.05, 1.9), (math.cos(a) * 0.8, math.sin(a) * 0.8, 3.0), tip], [0.3, 0.2, 0.12], 'toon_bark', sides=7)
        tips.append(tip)
    for k in range(5):   # roots flaring into the ground
        a = k * math.tau / 5
        b.tube([(0, 0, 0.5), (math.cos(a) * 0.6, math.sin(a) * 0.6, 0.05), (math.cos(a) * 1.0, math.sin(a) * 1.0, -0.15)], [0.22, 0.14, 0.06], 'toon_bark_dark', sides=6)
    canopy(b, (0, 0, 4.7), 3.6, 8, rnd, squash=0.55)
    for t in tips: b.ball(1.2, t + Vector((0, 0, 0.5)), 'toon_leaf', scale=(1, 1, 0.75), sub=1, wobble=0.12, freq=1.5)
    return b

def bougainvillea(seed=31):
    """Bougainvillea bush spilling magenta/pink bracts over green."""
    rnd = random.Random(seed); b = B(seed)
    b.tube([(0, 0, 0), (0.1, 0, 0.6), (0.05, 0.1, 1.1)], [0.07, 0.05, 0.03], 'toon_bark_dark', sides=5)
    for i in range(6):
        a = rnd.uniform(0, math.tau); r = rnd.uniform(0.1, 0.6); z = rnd.uniform(0.5, 1.3)
        b.ball(rnd.uniform(0.35, 0.5), (math.cos(a) * r, math.sin(a) * r, z), 'toon_leaf' if i < 3 else 'toon_leaf_dark', scale=(1, 1, 0.8), sub=1, wobble=0.06, freq=3)
    for i in range(9):
        a = rnd.uniform(0, math.tau); r = rnd.uniform(0.3, 0.75); z = rnd.uniform(0.6, 1.55)
        b.ball(rnd.uniform(0.2, 0.32), (math.cos(a) * r, math.sin(a) * r, z), 'toon_flower_pink' if i % 3 else 'toon_flower_magenta', scale=(1, 1, 0.75), sub=1, wobble=0.05, freq=4)
    return b
