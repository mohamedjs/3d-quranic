# Village houses (anime Delta / Upper-Egypt countryside). Front / door faces Blender -Y (= glTF +Z).
# house_a = Grandma Zainab's (lime-washed, blue door, mastaba along the front wall: model x 0.05..2.55,
# front wall face at y = -2.4, door centred at x = -0.59). house_b = mud-plaster with outside stair and
# a pigeon tower. house_c = small lime-washed house with a dome.
import math, random
from mathutils import Vector
from tk import B

def zigzag(b, x0, x1, y, z, h, mat, n=None, face='front'):
    """Row of painted triangles on a wall (decal, 1 cm proud)."""
    n = n or max(3, int((x1 - x0) / 0.34)); w = (x1 - x0) / n
    for i in range(n):
        a = x0 + i * w
        if face == 'front':
            b.poly([(a, y, z), (a + w, y, z), (a + w / 2, y, z + h)], mat)
        else:   # side wall at x = y-arg, running along y
            b.poly([(y, a + w, z), (y, a, z), (y, a + w / 2, z + h)], mat) if face == 'right' else b.poly([(y, a, z), (y, a + w, z), (y, a + w / 2, z + h)], mat)

def band(b, x0, x1, y, z0, z1, mat):
    b.poly([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], mat)

def painted_palm(b, x, y, z, s, mat_trunk='toon_paint_ochre', mat_leaf='toon_paint_green'):
    """Simple folk-art palm painted on a front wall (decal), base at (x, z), height ~1.3*s."""
    for i in range(6):
        t0, t1 = i / 6, (i + 1) / 6
        b.poly([(x - 0.05 * s + 0.03 * s * t0, y, z + t0 * s), (x + 0.05 * s - 0.03 * s * t0, y, z + t0 * s),
                (x + 0.05 * s - 0.03 * s * t1, y, z + t1 * s - 0.03 * s), (x - 0.05 * s + 0.03 * s * t1, y, z + t1 * s - 0.03 * s)], mat_trunk)
    top = (x, z + s)
    for a in (-2.6, -1.9, -1.2, 1.2, 1.9, 2.6, 0.0):
        L = 0.45 * s if a else 0.3 * s
        dx, dz = math.sin(a) * L, math.cos(a) * L - (0.12 * s if abs(a) > 1.5 else 0)
        px, pz = -math.cos(a) * 0.07 * s, math.sin(a) * 0.07 * s
        b.poly([(top[0], y, top[1]), (top[0] + dx * 0.5 + px, y, top[1] + dz * 0.5 + pz + 0.04 * s), (top[0] + dx, y, top[1] + dz),
                (top[0] + dx * 0.5 - px, y, top[1] + dz * 0.5 - pz)], mat_leaf)
    for k in (-1, 1):   # two date bunches
        b.poly([(x + k * 0.06 * s + dx2, y, z + 0.9 * s + dz2) for dx2, dz2 in ((0, 0), (k * 0.07 * s, -0.02 * s), (k * 0.05 * s, -0.12 * s), (0, -0.1 * s))], 'toon_paint_red')

def beams(b, w, d, h, n, rnd, out=0.32, r=0.075, sides=(-1, 1)):
    for i in range(n):
        x = -w / 2 + (i + 0.5) * w / n + rnd.uniform(-0.05, 0.05)
        for s in sides:
            L = out + rnd.uniform(-0.06, 0.1)
            b.cyl(r * rnd.uniform(0.85, 1.15), r * 0.9, 0.5 + L, (x, s * (d / 2 + L / 2 - 0.25), h - 0.22 + rnd.uniform(-0.03, 0.03)),
                  'toon_wood', rot=(math.pi / 2, rnd.uniform(-0.06, 0.06), 0), verts=7, wobble=0.01)

def window(b, x, y, z, w=0.62, h=0.72, face='front', shutter='toon_wood_blue', rnd=None, open_=True):
    """Small window: dark opening, painted frame, open shutters, wooden sill."""
    if face == 'front':
        b.box((w, 0.05, h), (x, y - 0.005, z), 'toon_window_dark', smooth=False)
        b.box((w + 0.2, 0.08, 0.1), (x, y - 0.05, z - h / 2 - 0.04), 'toon_wood', bevel=0.02)
        b.box((w + 0.14, 0.06, 0.1), (x, y - 0.03, z + h / 2 + 0.05), 'toon_wood', bevel=0.02)
        for s in (-1, 1):
            if open_:
                b.box((w / 2, 0.05, h * 0.98), (x + s * (w / 2 + w / 4 + 0.02), y - 0.12, z), shutter, bevel=0.015, rot=(0, 0, s * -0.35))
            else:
                b.box((w / 2 - 0.01, 0.05, h * 0.98), (x + s * w / 4, y - 0.04, z), shutter, bevel=0.015)
        for k in range(3):   # wooden grille bars
            b.box((0.03, 0.03, h * 0.95), (x - w / 3 + k * w / 3 + w / 6 - w / 6, y - 0.04, z), 'toon_wood_dark') if not open_ else None
    else:   # side wall at x = x (normal ±X by sign)
        sg = 1 if face == 'right' else -1
        b.box((0.05, w, h), (x + sg * 0.005, y, z), 'toon_window_dark', smooth=False)
        b.box((0.08, w + 0.2, 0.1), (x + sg * 0.05, y, z - h / 2 - 0.04), 'toon_wood', bevel=0.02)
        for k in range(2):
            b.box((0.04, 0.035, h * 0.95), (x + sg * 0.04, y - w / 6 + k * w / 3, z), shutter)
        b.box((0.04, w, 0.035), (x + sg * 0.04, y, z), shutter)

def door(b, x, y, w=1.0, h=1.95, leaf='toon_wood_blue', frame='toon_paint_blue', arch=True, rnd=None):
    # painted frame band (decal) + fanlight arch
    fw = 0.15
    band(b, x - w / 2 - fw, x - w / 2, y - 0.012, 0.15, h + 0.02, frame)
    band(b, x + w / 2, x + w / 2 + fw, y - 0.012, 0.15, h + 0.02, frame)
    if arch:
        seg = 8; R = w / 2 + fw
        for i in range(seg):
            a0, a1 = math.pi * i / seg, math.pi * (i + 1) / seg
            b.poly([(x + math.cos(a0) * R, y - 0.012, h + math.sin(a0) * R * 0.8), (x + math.cos(a1) * R, y - 0.012, h + math.sin(a1) * R * 0.8),
                    (x + math.cos(a1) * (R - fw), y - 0.012, h + math.sin(a1) * (R - fw) * 0.8), (x + math.cos(a0) * (R - fw), y - 0.012, h + math.sin(a0) * (R - fw) * 0.8)], frame)
            b.poly([(x, y - 0.01, h), (x + math.cos(a1) * (R - fw), y - 0.01, h + math.sin(a1) * (R - fw) * 0.8),
                    (x + math.cos(a0) * (R - fw), y - 0.01, h + math.sin(a0) * (R - fw) * 0.8)], 'toon_window_dark')
    # the leaf: two planks panels with battens and studs
    b.box((w, 0.08, h), (x, y - 0.04, h / 2), leaf, bevel=0.025)
    for z in (0.45, h - 0.4):
        b.box((w * 0.94, 0.04, 0.09), (x, y - 0.1, z), leaf, bevel=0.015)
    b.box((0.03, 0.03, h - 0.1), (x, y - 0.085, h / 2), 'toon_wood_dark')
    b.cyl(0.055, 0.055, 0.025, (x + 0.2, y - 0.12, 1.05), 'toon_iron', rot=(math.pi / 2, 0, 0), verts=8)
    b.box((w + 0.36, 0.18, 0.08), (x, y - 0.06, 0.04), 'toon_lime_warm', bevel=0.03)   # threshold step

def parapet(b, w, d, h, mat, rnd, ph=0.42, th=0.24, horns=True):
    z = h + ph / 2 - 0.02
    for s in (-1, 1):
        b.box((w + 0.04, th, ph), (0, s * (d / 2 - th / 2 + 0.02), z), mat, bevel=0.1, seg=2, wobble=0.02)
        b.box((th, d + 0.04, ph), (s * (w / 2 - th / 2 + 0.02), 0, z), mat, bevel=0.1, seg=2, wobble=0.02)
    if horns:   # rounded corner "horns" typical of Upper-Egypt houses
        for sx in (-1, 1):
            for sy in (-1, 1):
                b.lathe([(0.2, 0), (0.19, 0.12), (0.13, 0.28), (0.07, 0.4), (0.001, 0.44)], (sx * (w / 2 - 0.12), sy * (d / 2 - 0.12), h + ph - 0.06), mat, segs=8)
    b.box((w - 0.3, d - 0.3, 0.12), (0, 0, h - 0.02), 'toon_mud', smooth=False)   # roof deck

def firewood(b, x, y, z, L, n, rnd, mat='toon_stalks', r=0.07, along='x'):
    """A stack of cotton-stalk / firewood bundles on the roof edge."""
    k = 0
    for row in range(3):
        for i in range(n - row):
            rr = r * rnd.uniform(0.85, 1.2)
            off = (i - (n - row - 1) / 2) * r * 2.0
            p = (x, y + off, z + row * r * 1.7 + rr) if along == 'x' else (x + off, y, z + row * r * 1.7 + rr)
            rot = (0, math.pi / 2, rnd.uniform(-0.08, 0.08)) if along == 'x' else (math.pi / 2, 0, rnd.uniform(-0.08, 0.08))
            b.cyl(rr, rr * 0.9, L * rnd.uniform(0.88, 1.05), p, mat if (k % 3) else 'toon_firewood', rot=rot, verts=6, wobble=0.015)
            k += 1

def walls(b, w, d, h, mat, rnd, taper=0.985):
    b.box((w, d, h), (0, 0, h / 2), mat, bevel=0.14, seg=2, taper=taper, wobble=0.035, freq=0.8)
    b.box((w + 0.2, d + 0.2, 0.34), (0, 0, 0.1), 'toon_plaster', bevel=0.08, seg=1, taper=0.97, wobble=0.02)   # plinth skirt

def pigeon_tower(b, x, y, z, rnd, s=1.0):
    """برج حمام: a bulbous mud tower studded with clay pots and perching sticks, pigeons on top."""
    prof = [(0.001, 0), (0.95 * s, 0), (1.0 * s, 0.35 * s), (0.9 * s, 1.2 * s), (0.62 * s, 2.0 * s), (0.3 * s, 2.55 * s), (0.12 * s, 2.72 * s), (0.001, 2.78 * s)]
    b.lathe(prof, (x, y, z), 'toon_lime_warm', segs=14, wobble=0.03)
    for ring, (rz, rr) in enumerate(((0.55, 0.99), (1.05, 0.93), (1.55, 0.78), (2.05, 0.6))):
        n = int(7 * rr) + 3
        for i in range(n):
            a = i / n * math.tau + ring * 0.4
            px, py = x + math.cos(a) * rr * s, y + math.sin(a) * rr * s
            b.cyl(0.075 * s, 0.075 * s, 0.14, (px, py, z + rz * s), 'toon_clay', rot=(math.pi / 2, 0, a + math.pi / 2), verts=5, cap=False)
            b.disc(0.07 * s, (x + math.cos(a) * (rr * s + 0.02), y + math.sin(a) * (rr * s + 0.02), z + rz * s), 'toon_window_dark', segs=5, rot=(math.pi / 2, 0, a + math.pi / 2))
        for i in range(3):   # perching sticks
            a = i / 4 * math.tau + ring
            b.cyl(0.02, 0.018, 0.9 * s, (x + math.cos(a) * rr * s, y + math.sin(a) * rr * s, z + rz * s - 0.2), 'toon_wood', rot=(math.pi / 2, 0, a + math.pi / 2), verts=5)
    for i, (a, hh) in enumerate(((0.4, 2.72), (2.2, 2.4), (4.0, 1.9))):
        rr = 0.14 if i == 0 else (0.42 if i == 1 else 0.66)
        pigeon(b, x + math.cos(a) * rr * s, y + math.sin(a) * rr * s, z + hh * s, a)

def pigeon(b, x, y, z, yaw):
    b.ball(0.09, (x, y, z + 0.07), 'toon_pigeon', scale=(1.5, 1, 0.9), sub=1, rot=(0, 0, yaw))
    b.ball(0.05, (x + math.cos(yaw) * 0.12, y + math.sin(yaw) * 0.12, z + 0.15), 'toon_pigeon', sub=1)

def house_a(seed=1):
    """Grandma Zainab's house. 5.6 x 4.8 x 3.1 m (plinth -> 5.8 x 5.0)."""
    rnd = random.Random(seed); b = B(seed)
    w, d, h = 5.6, 4.8, 3.1; fy = -d / 2
    walls(b, w, d, h, 'toon_lime', rnd)
    parapet(b, w, d, h, 'toon_lime_warm', rnd)
    beams(b, w, d, h, 6, rnd)
    # lower painted dado (warm ochre wash) on the sides and back only; the front keeps the mastaba
    door(b, -0.59, fy, rnd=rnd)
    window(b, 1.85, fy, 1.85, rnd=rnd)
    window(b, w / 2, 0.4, 1.9, face='right', shutter='toon_wood_blue')
    window(b, -w / 2, -0.3, 1.9, face='left', shutter='toon_wood_blue')
    zigzag(b, -w / 2 + 0.25, w / 2 - 0.25, fy - 0.012, 2.6, 0.16, 'toon_paint_blue')
    band(b, -w / 2 + 0.2, w / 2 - 0.2, fy - 0.011, 2.53, 2.57, 'toon_paint_blue')
    painted_palm(b, -2.05, fy - 0.013, 0.95, 1.2)
    painted_palm(b, 0.72, fy - 0.013, 0.95, 0.95)   # above the mastaba, behind grandma
    # roof: firewood / cotton-stalk bundles along the back, a straw heap, a water-jar
    firewood(b, 0.3, 1.55, h + 0.02, 3.4, 4, rnd)
    b.ball(0.7, (-1.7, 1.2, h + 0.1), 'toon_straw', scale=(1.2, 0.9, 0.55), sub=2, wobble=0.07, flat_bottom=0.2)
    b.lathe([(0.001, 0), (0.14, 0.02), (0.22, 0.2), (0.2, 0.36), (0.09, 0.46), (0.1, 0.52)], (1.9, -1.4, h + 0.05), 'toon_clay', segs=10)
    b.cyl(0.08, 0.07, 0.6, (w / 2 + 0.22, 1.2, h - 0.05), 'toon_clay', rot=(0, math.pi / 2 - 0.2, 0), verts=8)   # drain spout
    return b

def house_b(seed=2):
    """Mud-plaster house with an outside stair (+X) and a pigeon tower on the roof. 6.2 x 5.4 x 3.3 (+0.95 stair)."""
    rnd = random.Random(seed); b = B(seed)
    w, d, h = 6.2, 5.4, 3.3; fy = -d / 2; ox = -0.5   # body shifted so body+stair are centred
    bb = B(seed)
    walls(bb, w, d, h, 'toon_plaster', rnd)
    parapet(bb, w, d, h, 'toon_plaster_light', rnd)
    beams(bb, w, d, h, 7, rnd)
    door(bb, -1.2, fy, leaf='toon_wood_green', frame='toon_paint_white', arch=False, rnd=rnd)
    bb.box((1.6, 0.26, 0.2), (-1.2, fy - 0.08, 2.18), 'toon_wood', bevel=0.03, wobble=0.01)   # palm-log lintel
    window(bb, 1.2, fy, 1.95, shutter='toon_wood_green')
    window(bb, -w / 2, 0.5, 1.95, face='left', shutter='toon_wood_green')
    band(bb, -w / 2 + 0.2, w / 2 - 0.2, fy - 0.011, 0.3, 0.9, 'toon_paint_white')          # lime-washed dado
    zigzag(bb, -w / 2 + 0.2, w / 2 - 0.2, fy - 0.012, 0.9, 0.16, 'toon_paint_white')
    # outside stair up the right wall (towards the back), with a low parapet
    steps = 11; sw = 0.95
    for i in range(steps):
        t = (i + 1) / steps; L = (d - 0.7) * t
        bb.box((sw, (d - 0.7) / steps + 0.02, h * t), (w / 2 + sw / 2 - 0.02, -d / 2 + 0.35 + L - (d - 0.7) / steps / 2, h * t / 2), 'toon_plaster', bevel=0.04, seg=1, wobble=0.015)
    bb.box((0.16, d - 0.7, 0.5), (w / 2 + sw - 0.08, 0.35 - 0.0, h + 0.1), 'toon_plaster_light', bevel=0.07, rot=(math.atan2(h, d - 0.7) * 0 , 0, 0))
    pigeon_tower(bb, -1.5, 0.9, h - 0.02, rnd, 0.95)
    firewood(bb, 1.4, 1.6, h + 0.02, 2.6, 3, rnd, along='y')
    b.merge_from(bb, __import__('mathutils').Matrix.Translation((ox, 0, 0)))
    return b

def house_c(seed=3):
    """Small lime-washed house with a dome and a green door. 4.6 x 4.4 x 2.9."""
    rnd = random.Random(seed); b = B(seed)
    w, d, h = 4.6, 4.4, 2.9; fy = -d / 2
    walls(b, w, d, h, 'toon_lime_warm', rnd)
    parapet(b, w, d, h, 'toon_lime', rnd, ph=0.36)
    beams(b, w, d, h, 5, rnd)
    door(b, 0.8, fy, leaf='toon_wood_green', frame='toon_paint_green', rnd=rnd)
    window(b, -1.2, fy, 1.8, shutter='toon_wood_green')
    window(b, w / 2, -0.2, 1.8, face='right', shutter='toon_wood_green')
    band(b, -w / 2 + 0.15, w / 2 - 0.15, fy - 0.011, 2.32, 2.4, 'toon_paint_ochre')
    for i in range(8):   # a dotted band
        b.disc(0.06, (-w / 2 + 0.45 + i * (w - 0.9) / 7, fy - 0.013, 2.2), 'toon_paint_ochre', segs=6, rot=(math.pi / 2, 0, 0))
    painted_palm(b, -0.35, fy - 0.013, 0.7, 1.05, mat_leaf='toon_paint_blue')
    r = 1.05   # the dome on a low drum
    b.cyl(r + 0.05, r + 0.05, 0.35, (0.6, 0.5, h + 0.17), 'toon_lime', verts=16, bevel=0.05)
    b.uvball(r, (0.6, 0.5, h + 0.34), 'toon_lime', seg=16, rings=8, cut=0.0, scale=(1, 1, 0.95))
    b.cyl(0.05, 0.02, 0.35, (0.6, 0.5, h + 0.34 + r * 0.95 + 0.12), 'toon_paint_ochre', verts=6)
    firewood(b, -1.3, -0.6, h + 0.02, 2.2, 3, rnd, along='y')
    return b
