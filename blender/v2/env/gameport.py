# Python port of the game's layout functions (src/game/terrain/heightfield.js, buildings/village.js,
# world/details.js) so the Blender vignette uses the SAME layout. Game coords: x, z (y up).
import math

def i32(v):
    v &= 0xffffffff
    return v - (1 << 32) if v & 0x80000000 else v
def u32(v): return v & 0xffffffff
def imul(a, b): return i32(u32(a) * u32(b))

def jhash(x, y):
    h = i32(imul(int(x), 374761393) + imul(int(y), 668265263))
    h = imul(u32(h) ^ (u32(h) >> 13), 1274126177)
    return u32(u32(h) ^ (u32(h) >> 16)) / 4294967295

def noise(x, y):
    xi, yi = math.floor(x), math.floor(y); xf, yf = x - xi, y - yi
    u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)
    a, b, c, d = jhash(xi, yi), jhash(xi + 1, yi), jhash(xi, yi + 1), jhash(xi + 1, yi + 1)
    return (a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v) * 2 - 1

def fbm(x, y, oct=4):
    s, a, f = 0.0, 0.5, 1.0
    for _ in range(oct): s += a * noise(x * f, y * f); a *= 0.5; f *= 2.03
    return s

def rng(seed):
    st = [i32(seed)]
    def r():
        st[0] = i32(st[0] + 0x6D2B79F5); s = st[0]
        t = imul(u32(s) ^ (u32(s) >> 15), 1 | s)
        t = i32(t + imul(u32(t) ^ (u32(t) >> 7), 61 | t)) ^ t
        return u32(t ^ (u32(t) >> 14)) / 4294967296
    return r

clamp = lambda v, a, b: max(a, min(b, v))
lerp = lambda a, b, t: a + (b - a) * t
def smooth(a, b, x):
    t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

riverZ = lambda x: 72 + 14 * math.sin(x * 0.021) + 6 * math.sin(x * 0.057 + 1.3)
CANALS = [-45, -15, 15, 45]
OASIS = dict(x=-110, z=-20, r=15); RUINS = dict(x=160, z=-140)
STREET = dict(z0=-54, z1=-12, channelX=-3.3)
LOOKOUT = dict(x=-33, z=-80)
WATER_Y = -0.5
PATHS = [[[0, -95], [0, 0]], [[0, 0], [0, 140]], [[0, 0], [-40, -8], [-80, -16], [-96, -19]],
         [[0, 0], [40, -10], [90, -26], [130, -34], [158, -90], [160, -128]], [[-75, 14], [75, 14]]]
SEGS = [(p[i], p[i + 1]) for p in PATHS for i in range(len(p) - 1)]
ROAD_CANALS = [[[5, -95], [5, -57]], [[-42, -3.9], [-80, -11.5], [-94, -14.5]], [[42, -14.5], [90, -30.5], [130, -38.5]], [[4, 17], [4, 58]]]
CSEGS = [(p[i], p[i + 1]) for p in ROAD_CANALS for i in range(len(p) - 1)]
FOOTBRIDGES = [dict(x=5, z=-76, rot=0), dict(x=-65, z=-8.5, rot=math.pi / 2 - 0.19), dict(x=70, z=-23.8, rot=math.pi / 2 + 0.32), dict(x=4, z=40, rot=0)]
FOOTBRIDGE_DECK = 1.1
HOME = dict(x=-9.4, z=26, rot=math.pi / 2)
MASTABA = dict(h=0.45, depth=0.6, len=2.5, x0=0.05, wallZ=2.4)

def _segdist(x, z, segs):
    m = 1e9
    for (ax, az), (bx, bz) in segs:
        dx, dz = bx - ax, bz - az
        t = clamp(((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz), 0, 1)
        m = min(m, math.hypot(x - ax - dx * t, z - az - dz * t))
    return m
pathDist = lambda x, z: _segdist(x, z, SEGS)
canalDist = lambda x, z: _segdist(x, z, CSEGS)

def fieldPlot(x, z):
    if abs(x) > 205 or z < -150 or z > 150: return -1
    if math.hypot(x, z) < 46 or (abs(x) < 16 and -60 < z < -8): return -1
    if math.hypot(x - OASIS['x'], z - OASIS['z']) < 42 or math.hypot(x - RUINS['x'], z - RUINS['z']) < 42: return -1
    if math.hypot(x - LOOKOUT['x'], z - LOOKOUT['z']) < 30 or abs(z - riverZ(x)) < 11: return -1
    if pathDist(x, z) < 3.2 or canalDist(x, z) < 3.6: return -1
    if max(smooth(118, 150, z), smooth(170, 200, max(abs(x), abs(z)))) > 0.2: return -1
    ex, ez = math.fmod(x + 1000, 15), math.fmod(z + 1000, 10)
    if ex < 0.9 or ez < 0.7: return 4
    return int(jhash(math.floor((x + 1000) / 15) + 11, math.floor((z + 1000) / 10) + 7) * 4)

def height(x, z):
    h = 1.6 + fbm(x * 0.011, z * 0.011) * 2.4
    edge = max(abs(x), abs(z))
    m = max(smooth(125, 225, z), smooth(185, 255, edge))
    if m > 0:
        r = 1 - abs(noise(x * 0.01, z * 0.01))
        h += m * (9 + 20 * r * r + 5 * fbm(x * 0.03, z * 0.03))
    h = lerp(h, 1.0 + fbm(x * 0.012, z * 0.012) * 0.35, (1 - m) * 0.9)
    h += 9 * math.exp(-((x - LOOKOUT['x']) ** 2 + (z - LOOKOUT['z']) ** 2) / 420)
    dv = math.hypot(x, z)
    h = lerp(h, 1.3 + fbm(x * 0.05, z * 0.05) * 0.15, 1 - smooth(34, 50, dv))
    street = (1 - smooth(13, 20, abs(x))) * smooth(STREET['z0'] - 12, STREET['z0'] - 2, z) * (1 - smooth(-14, -4, z))
    h = lerp(h, 1.3 + fbm(x * 0.05, z * 0.05) * 0.12, street)
    dO = math.hypot(x - OASIS['x'], z - OASIS['z'])
    h = lerp(h, 0.9, 1 - smooth(22, 40, dO))
    dR = math.hypot(x - RUINS['x'], z - RUINS['z'])
    h = lerp(h, 1.4, 1 - smooth(26, 40, dR))
    h -= 0.1 * (1 - smooth(1.5, 2.6, pathDist(x, z)))
    h = lerp(-2.4, h, smooth(4.5, 9, abs(z - riverZ(x))))
    for c in CANALS:
        if 15 < z < riverZ(c) + 2: h = lerp(-0.85, h, max(smooth(0.9, 1.7, abs(x - c)), 1 - smooth(16, 19, z)))
    h = lerp(-1.3, h, smooth(1.0, 2.3, canalDist(x, z)))
    h = lerp(-2.2, h, smooth(OASIS['r'] * 0.6, OASIS['r'], dO + fbm(x * 0.1, z * 0.1) * 2))
    return h

def waterDist(x, z):
    d = abs(z - riverZ(x)) - 6
    d = min(d, math.hypot(x - OASIS['x'], z - OASIS['z']) - OASIS['r'])
    if 15 < z < riverZ(x):
        for c in CANALS: d = min(d, abs(x - c) - 1)
    d = min(d, canalDist(x, z) - 1.5)
    return max(0, d)

def village_placements():
    """buildVillage(): model placements {model,x,y,z,rot,sx,sy,sz} (+ gardens), same RNG sequence."""
    r = rng(21); P = []; placed = []; gardens = []
    HOUSES = [('house_a', 5.6, 4.8), ('house_b', 7.3, 5.4), ('house_c', 4.6, 4.4)]
    def house(x, z, w, d, h, rot):
        model, mw, md = min(HOUSES, key=lambda v: abs(v[1] * v[2] - w * d))
        sx = clamp(w / mw, 0.88, 1.12); sz = clamp(d / md, 0.88, 1.12)
        P.append(dict(model=model, x=x, y=height(x, z) - 0.05, z=z, rot=rot, sx=sx, sy=clamp(h / 3.1, 0.92, 1.1), sz=sz))
    def place(model, x, z, rot, s=1):
        P.append(dict(model=model, x=x, y=height(x, z) - 0.03, z=z, rot=rot, sx=s, sy=s, sz=s))
    z = STREET['z0'] + 2; i = 0
    while z < STREET['z1'] - 3:
        for side in (-1, 1):
            if (i + (1 if side > 0 else 0)) % 4 == 3:
                place('garden_wall', side * 6.2, z + 2, math.pi / 2); gardens.append((side * 8, z + 2)); continue
            w = 5 + r() * 1.6; d = 4.6 + r() * 1; x = side * (5.6 + d / 2)
            house(x, z + w / 2, w, d, 2.9 + r() * 0.6, math.pi / 2 if side < 0 else -math.pi / 2)
            placed.append((x, z + w / 2, max(w, d) / 2))
            if r() < 0.7: place('pot_plant', side * 5.0, z + r() * w, r() * 6, 0.9 + r() * 0.4)
            if r() < 0.5: place('jar' if r() < 0.5 else 'jar_b', side * 5.2, z + w - 0.6, r() * 6)
            if r() < 0.8: gardens.append((side * 5.1, z + (0.4 if r() < 0.5 else w - 0.4)))
        z += 7.2; i += 1
    zz = STREET['z0']
    while zz < STREET['z1']: place('stream', STREET['channelX'], zz + 2, 0); zz += 4
    k = 0
    while k < 600 and len(placed) < 17:
        k += 1
        a = r() * math.pi * 2; dist = 13 + r() * 25; x = math.cos(a) * dist; z = math.sin(a) * dist
        w = 4 + r() * 3; d = 4 + r() * 2.5; h = 2.8 + r() * 1.3
        rot = round(math.atan2(-x, -z) / (math.pi / 2)) * (math.pi / 2)
        R = max(w, d) / 2
        if pathDist(x, z) < R + 2.8 or math.hypot(x, z) - R < 10: continue
        if math.hypot(x - HOME['x'], z - HOME['z']) < R + 7: continue
        if any(abs(p[0] - x) < p[2] + R + 1.8 and abs(p[1] - z) < p[2] + R + 1.8 for p in placed): continue
        placed.append((x, z, R)); house(x, z, w, d, h, rot)
    P.append(dict(model='house_a', x=HOME['x'], y=height(HOME['x'], HOME['z']) - 0.05, z=HOME['z'], rot=HOME['rot'], sx=1, sy=1, sz=1))
    P.append(dict(model='mastaba', x=HOME['x'], y=height(HOME['x'], HOME['z']), z=HOME['z'], rot=HOME['rot'], sx=1, sy=1, sz=1))
    P.append(dict(model='well', x=-5, y=height(-5, 4), z=4, rot=0.4, sx=1, sy=1, sz=1))
    for x, z in ((9, -7), (-10, -8)):
        P.append(dict(model='stall', x=x, y=height(x, z), z=z, rot=math.atan2(-x, -z), sx=1, sy=1, sz=1))
    for i in range(9):
        x = -70 + r() * 140
        if abs(x) < 4: continue
        z = 11.5 + r()
        P.append(dict(model='hay', x=x, y=height(x, z) - 0.05, z=z, rot=r() * 3, sx=1, sy=1, sz=1))
    return P, placed, gardens

def canal_placements():
    """buildCanalScene() placements with grandma at home."""
    r = rng(77); P = []; CX = -15
    def place(model, x, z, rot=0, s=1, dy=0, tilt=0):
        P.append(dict(model=model, x=x, y=height(x, z) + dy, z=z, rot=rot, sx=s, sy=s, sz=s, tilt=tilt))
    place('sluice', CX, 18.4, 0, 1, -0.05)
    place('shaduf', CX - 1.9, 24, 0)
    place('footbridge', CX, 34.5, 0, 1, 0.05)
    for b in FOOTBRIDGES: P.append(dict(model='footbridge', x=b['x'], y=FOOTBRIDGE_DECK - 0.14, z=b['z'], rot=b['rot'], sx=1, sy=1, sz=1))
    hx, hz, hr = HOME['x'], HOME['z'], HOME['rot']
    w = lambda mx, mz: (hx + mx * math.cos(hr) + mz * math.sin(hr), hz - mx * math.sin(hr) + mz * math.cos(hr))
    (jx, jz), (bx, bz), (kx, kz) = w(-1.55, 2.75), w(-2.1, 2.7), w(2.95, 2.75)
    place('jar', jx, jz, 0.3); place('jar_b', bx, bz, 1.2, 0.9); place('basket', kx, kz, 0.5)
    place('hoe', CX + 1.25, 18.75, 0.2, tilt=-0.3)
    for a, b in ((-42, -17.8), (-9.5, -3)):
        x = a + 1.1
        while x < b:
            place('fence', x, 15.4 + (r() - 0.5) * 0.1, (r() - 0.5) * 0.05); x += 2.25
    return P
