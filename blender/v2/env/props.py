# Village props in the anime style. Origins at ground contact, front = -Y, same footprints as v1.
import math, random
from mathutils import Vector
from tk import B

def mastaba(seed=61):
    """Grandma's مصطبة in house_a MODEL SPACE (place it with house_a's transform, at ground height):
    x 0.05..2.55, y -2.4..-3.0 (front wall face at y=-2.4), seat top z = 0.45, body sunk to z = -0.2."""
    rnd = random.Random(seed); b = B(seed)
    x0, L, D, H, wy = 0.05, 2.5, 0.6, 0.45, -2.4
    cx, cy = x0 + L / 2, wy - D / 2
    b.box((L, D + 0.02, H + 0.2 - 0.05), (cx, cy + 0.01, (H - 0.25) / 2), 'toon_lime_warm', bevel=0.07, wobble=0.012, freq=2)
    b.box((L + 0.04, D + 0.04, 0.06), (cx, cy - 0.01, H - 0.03), 'toon_lime', bevel=0.03, wobble=0.006)
    b.poly([(x0 + 0.05, wy - D - 0.011, 0.05), (x0 + L - 0.05, wy - D - 0.011, 0.05), (x0 + L - 0.05, wy - D - 0.011, 0.14), (x0 + 0.05, wy - D - 0.011, 0.14)], 'toon_paint_blue')
    # kilim where grandma sits, draping over the front edge, with woven stripes
    kx, kw = cx - 0.2, 1.3
    b.box((kw, D - 0.08, 0.014), (kx, cy + 0.02, H + 0.007), 'toon_fabric_red', smooth=False)
    b.box((kw, 0.014, 0.16), (kx, wy - D + 0.025, H - 0.07), 'toon_fabric_red', smooth=False)
    for i, m in enumerate(('toon_fabric_ochre', 'toon_fabric_blue', 'toon_fabric_ochre')):
        x = kx - kw / 2 + 0.2 + i * (kw - 0.4) / 2
        b.box((0.05, D - 0.06, 0.004), (x, cy + 0.02, H + 0.016), m, smooth=False)
        b.box((0.05, 0.004, 0.16), (x, wy - D + 0.016, H - 0.07), m, smooth=False)
    for k in range(7):   # fringe
        b.box((0.02, 0.01, 0.05), (kx - kw / 2 + 0.1 + k * (kw - 0.2) / 6, wy - D + 0.022, H - 0.17), 'toon_fabric_cream', smooth=False)
    # folded cushion at her side, and a rolled one against the wall
    b.box((0.36, 0.3, 0.1), (kx + 0.65 + 0.2, wy - 0.17, H + 0.05), 'toon_fabric_cream', bevel=0.04, wobble=0.008, freq=4)
    b.box((0.37, 0.05, 0.02), (kx + 0.85, wy - 0.17, H + 0.101), 'toon_fabric_blue', smooth=False)
    b.cyl(0.09, 0.09, 0.55, (kx - 0.2, wy - 0.1, H + 0.09), 'toon_fabric_ochre', rot=(0, math.pi / 2, 0), verts=10, bevel=0.03)
    return b

def jar(seed=62):
    b = B(seed)
    b.lathe([(0.001, 0), (0.12, 0.0), (0.22, 0.12), (0.27, 0.32), (0.25, 0.46), (0.16, 0.58), (0.09, 0.64), (0.1, 0.7), (0.14, 0.74), (0.11, 0.75), (0.08, 0.7)], mat='toon_clay', segs=12)
    b.lathe([(0.26, 0.28), (0.275, 0.3), (0.275, 0.34), (0.26, 0.36)], mat='toon_paint_white', segs=12)
    b.disc(0.12, (0, 0, 0.745), 'toon_fabric_cream', segs=8)   # cloth cover
    return b

def jar_b(seed=63):
    b = B(seed)
    b.lathe([(0.001, 0), (0.12, 0.0), (0.28, 0.16), (0.31, 0.28), (0.26, 0.45), (0.14, 0.53), (0.15, 0.58), (0.18, 0.6), (0.15, 0.61), (0.12, 0.56)], mat='toon_clay_dark', segs=12)
    b.lathe([(0.3, 0.22), (0.315, 0.25), (0.31, 0.29), (0.3, 0.3)], mat='toon_paint_ochre', segs=12)
    return b

def basket(seed=64):
    rnd = random.Random(seed); b = B(seed)
    b.lathe([(0.001, 0), (0.22, 0.0), (0.32, 0.14), (0.36, 0.24), (0.33, 0.26), (0.3, 0.2), (0.001, 0.16)], mat='toon_straw', segs=12)
    b.lathe([(0.34, 0.1), (0.355, 0.12), (0.35, 0.15), (0.335, 0.16)], mat='toon_wood', segs=12)
    for i in range(3):   # a pile of bread rounds and dates
        b.cyl(0.13, 0.12, 0.05, (rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), 0.2 + i * 0.03), 'toon_straw' if i % 2 else 'toon_produce', verts=10, bevel=0.02, rot=(rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), 0))
    for i in range(6):
        b.ball(0.035, (rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), 0.24), 'toon_dates', scale=(1, 1, 1.4), sub=0)
    return b

def hoe(seed=65):
    b = B(seed)
    b.cyl(0.024, 0.02, 1.35, (0, 0, 0.68), 'toon_wood', verts=6)
    b.box((0.28, 0.2, 0.03), (0, -0.09, 0.03), 'toon_iron', bevel=0.01, rot=(0.15, 0, 0))
    b.cyl(0.035, 0.035, 0.08, (0, -0.01, 0.04), 'toon_iron', verts=6)
    return b

def fence(seed=66):
    """2.2 m palm-rib (جريد) fence panel along X."""
    rnd = random.Random(seed); b = B(seed)
    for x in (-1.1, 1.1): b.cyl(0.06, 0.05, 1.3, (x, 0, 0.55), 'toon_wood', verts=6, wobble=0.01)
    for z in (0.4, 0.85): b.cyl(0.03, 0.03, 2.35, (0, -0.04, z), 'toon_wood_dark', rot=(0, math.pi / 2, rnd.uniform(-0.03, 0.03)), verts=5)
    for i in range(14):
        x = -1.0 + i * 0.154; h = 1.05 + rnd.uniform(-0.1, 0.12)
        b.box((0.035, 0.02, h), (x, 0.0, h / 2 - 0.05), 'toon_frond_dry' if i % 4 else 'toon_stalks', rot=(0, rnd.uniform(-0.05, 0.05), 0))
        b.poly([(x - 0.018, 0.0, h - 0.05), (x + 0.018, 0.0, h - 0.05), (x, 0.0, h + 0.05)], 'toon_frond_dry')
    for z in (0.4, 0.85):   # rope lashings
        for x in (-1.1, 1.1): b.cyl(0.07, 0.07, 0.05, (x, 0, z), 'toon_rope', verts=6)
    return b

def garden_wall(seed=67):
    """4 m wall segment along X: rubble-stone base, plastered upper, rounded coping, a painted band."""
    rnd = random.Random(seed); b = B(seed)
    b.box((4.0, 0.46, 0.5), (0, 0, 0.2), 'toon_stone_dark', bevel=0.06, wobble=0.03, freq=1.5)
    for i in range(9):   # stones showing in the base
        b.ball(0.13, (-1.8 + i * 0.45 + rnd.uniform(-0.05, 0.05), -0.23, 0.18 + rnd.uniform(-0.06, 0.08)), 'toon_stone', scale=(1.3, 0.4, 0.8), sub=1)
    b.box((4.0, 0.38, 0.5), (0, 0, 0.68), 'toon_lime_warm', bevel=0.05, wobble=0.02)
    b.cyl(0.2, 0.2, 4.04, (0, 0, 0.94), 'toon_lime', rot=(0, math.pi / 2, 0), verts=10, scale=(0.6, 1.05, 1))
    b.poly([(-1.95, -0.192, 0.55), (1.95, -0.192, 0.55), (1.95, -0.192, 0.62), (-1.95, -0.192, 0.62)], 'toon_paint_blue')
    b.poly([(1.95, 0.192, 0.55), (-1.95, 0.192, 0.55), (-1.95, 0.192, 0.62), (1.95, 0.192, 0.62)], 'toon_paint_blue')
    return b

def pot_plant(seed=68):
    rnd = random.Random(seed); b = B(seed)
    b.lathe([(0.001, 0), (0.16, 0.0), (0.22, 0.32), (0.26, 0.37), (0.26, 0.42), (0.22, 0.42), (0.001, 0.36)], mat='toon_clay', segs=10)
    b.lathe([(0.23, 0.2), (0.24, 0.22), (0.245, 0.25), (0.235, 0.26)], mat='toon_paint_white', segs=10)
    for i in range(4):
        a = i * 1.6; r = 0.08 if i else 0
        b.ball(rnd.uniform(0.16, 0.2), (math.cos(a) * r, math.sin(a) * r, 0.55 + rnd.uniform(0, 0.12)), 'toon_leaf' if i % 2 else 'toon_leaf_light', scale=(1, 1, 0.85), sub=1, wobble=0.02, freq=6)
    for i in range(5):
        a = rnd.uniform(0, math.tau)
        b.ball(0.045, (math.cos(a) * 0.17, math.sin(a) * 0.17, 0.65 + rnd.uniform(0, 0.12)), 'toon_flower_red', sub=0)
    return b

def hay(seed=69):
    """Hay / straw stack (lying round bale, ~1.2 m) with loose tufts."""
    rnd = random.Random(seed); b = B(seed)
    b.cyl(0.6, 0.58, 1.2, (0, 0, 0.58), 'toon_straw', rot=(0, math.pi / 2, 0), verts=12, bevel=0.12, wobble=0.04)
    for s in (-1, 1):
        b.disc(0.4, (s * 0.605, 0, 0.58), 'toon_stalks', segs=10, rot=(0, s * math.pi / 2, 0))
    for x in (-0.3, 0.3): b.cyl(0.61, 0.61, 0.06, (x, 0, 0.58), 'toon_rope', rot=(0, math.pi / 2, 0), verts=12)
    for i in range(6):
        a = rnd.uniform(0, math.tau)
        b.poly([(rnd.uniform(-0.5, 0.5), math.cos(a) * 0.6, 0.58 + math.sin(a) * 0.6), (rnd.uniform(-0.5, 0.5), math.cos(a + 0.2) * 0.78, 0.58 + math.sin(a + 0.2) * 0.72),
                (rnd.uniform(-0.5, 0.5), math.cos(a + 0.3) * 0.6, 0.58 + math.sin(a + 0.3) * 0.6)], 'toon_straw')
    return b

def well(seed=70):
    """Village well: plastered round kerb with a painted band, wooden frame, pulley, rope and bucket."""
    b = B(seed)
    b.lathe([(1.05, -0.1), (1.1, 0.0), (1.1, 0.78), (1.16, 0.84), (1.14, 0.94), (0.86, 0.94), (0.84, 0.86), (0.82, 0.1)], mat='toon_lime_warm', segs=18, wobble=0.02)
    b.lathe([(1.105, 0.5), (1.11, 0.62)], mat='toon_paint_blue', segs=18)
    b.disc(0.83, (0, 0, 0.55), 'toon_water', segs=14)
    for s in (-1, 1):
        b.cyl(0.09, 0.08, 2.2, (s * 1.0, 0, 1.05), 'toon_wood', verts=7, wobble=0.012)
        b.ball(0.12, (s * 1.0, 0, 0.9), 'toon_stone', scale=(1.2, 1.2, 0.8), sub=1)
    b.cyl(0.06, 0.06, 2.3, (0, 0, 2.02), 'toon_wood_dark', rot=(0, math.pi / 2, 0), verts=7)
    b.cyl(0.16, 0.16, 0.1, (0.2, 0, 2.02), 'toon_wood', rot=(0, math.pi / 2, 0), verts=10, bevel=0.02)
    b.cyl(0.014, 0.014, 0.9, (0.25, -0.15, 1.55), 'toon_rope', verts=4)
    b.lathe([(0.001, 0.94), (0.12, 0.95), (0.16, 1.18), (0.17, 1.2), (0.15, 1.2), (0.13, 1.0)], loc=(0.25, -0.15, 0.0), mat='toon_wood', segs=10)
    b.box((0.4, 0.04, 0.3), (0, 0, 2.3), 'toon_clay', bevel=0.02)   # little roof tile over the axle
    return b

def stall(seed=71):
    """Market stall with a striped awning, a table and bowls of produce."""
    rnd = random.Random(seed); b = B(seed)
    for x, y in ((-1.4, -0.9), (1.4, -0.9), (-1.4, 0.9), (1.4, 0.9)):
        hh = 2.5 if y < 0 else 2.2
        b.cyl(0.055, 0.05, hh, (x, y, hh / 2), 'toon_wood', verts=6, wobble=0.01)
    for i in range(6):   # striped awning
        x = -1.6 + (i + 0.5) * 3.2 / 6
        b.box((3.2 / 6 + 0.005, 2.3, 0.04), (x, 0, 2.36), 'toon_fabric_red' if i % 2 else 'toon_fabric_cream', rot=(-0.14, 0, 0))
        b.poly([(x - 0.26, -1.14, 2.52), (x + 0.26, -1.14, 2.52), (x, -1.14, 2.34)], 'toon_fabric_red' if i % 2 else 'toon_fabric_cream')
    b.box((2.7, 1.2, 0.08), (0, 0.1, 0.8), 'toon_wood', bevel=0.02)
    b.box((2.5, 1.0, 0.7), (0, 0.15, 0.4), 'toon_wood_dark', bevel=0.02)
    for i, m in enumerate(('toon_produce', 'toon_tomato', 'toon_dates')):
        bx = -0.85 + i * 0.85
        b.lathe([(0.001, 0), (0.2, 0.02), (0.3, 0.14), (0.28, 0.15)], loc=(bx, 0.1, 0.84), mat='toon_straw', segs=10)
        for k in range(6):
            b.ball(0.075, (bx + rnd.uniform(-0.13, 0.13), 0.1 + rnd.uniform(-0.13, 0.13), 0.99 + rnd.uniform(0, 0.05)), m, sub=0)
    b.box((0.45, 0.35, 0.3), (-1.0, -0.75, 0.15), 'toon_wood', bevel=0.02)   # crate
    for k in range(4): b.ball(0.08, (-1.1 + (k % 2) * 0.2, -0.8 + (k // 2) * 0.12, 0.33), 'toon_cabbage', sub=0)
    return b
