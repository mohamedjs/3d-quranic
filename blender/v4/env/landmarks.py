"""Build M3 landmarks: Nile river bridge, oasis arish shelter, and ancient sandstone ruins set.

Usage:
  blender -b --factory-startup --python blender/v4/env/landmarks.py
"""
import math
import sys
from pathlib import Path

from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib
from lib import V4Builder, bake_wear_and_ao, export_asset, reset_scene


# ---------------------------------------------------------------------------
# 1. Nile River Bridge (river_bridge.glb)
# Same size, axis, deck height (0.55), and origin as heightfield.js BRIDGE:
#   spans Y in [-10, +10], walkable width X in [-1.7, +1.7], deck top Z = 0.55.
#   Stone piers & masonry arches (ph_stone) + timber deck & rails (ph_wood).
# ---------------------------------------------------------------------------

def _add_stone_arch_bay(b, y0, y1, half_w=1.80, z_spring=-0.55, z_crown=0.22,
                        ring_th=0.26, segs=8):
    """Masonry sandstone vaulted barrel arch + raised voussoir arch rings + spandrel walls."""
    span = y1 - y0
    ym = 0.5 * (y0 + y1)
    hr = span * 0.5
    rise = z_crown - z_spring

    # Continuous sandstone vault soffit + spandrel side faces between piers
    vbm = lib.bmesh.new()
    in_l, in_r, top_l, top_r = [], [], [], []
    z_spandrel = 0.34
    for i in range(segs + 1):
        t = i / segs
        ang = t * math.pi
        y = ym - math.cos(ang) * hr
        z_in = z_spring + math.sin(ang) * rise
        in_l.append(vbm.verts.new((-half_w, y, z_in)))
        in_r.append(vbm.verts.new((half_w, y, z_in)))
        top_l.append(vbm.verts.new((-half_w, y, z_spandrel)))
        top_r.append(vbm.verts.new((half_w, y, z_spandrel)))

    for i in range(segs):
        # Curved arch underside (normals point down into the water)
        vbm.faces.new((in_l[i], in_r[i], in_r[i + 1], in_l[i + 1]))
        # Left spandrel wall (-X face)
        vbm.faces.new((in_l[i], in_l[i + 1], top_l[i + 1], top_l[i]))
        # Right spandrel wall (+X face)
        vbm.faces.new((in_r[i + 1], in_r[i], top_r[i], top_r[i + 1]))
    b.put(vbm, 'ph_stone', '#C9B18A', None, smooth=False, wobble=0.010, spread=0.025)

    # Raised sculpted sandstone voussoir blocks along both outer arch faces
    for sx in (-1, 1):
        for i in range(segs):
            t = (i + 0.5) / segs
            ang = t * math.pi
            y = ym - math.cos(ang) * (hr - 0.04)
            z = z_spring + math.sin(ang) * rise + ring_th * 0.45
            # Tangent slope of arch in YZ plane
            dy = math.sin(ang) * hr
            dz = math.cos(ang) * rise
            pitch = math.atan2(dz, dy)
            seg_len = (math.hypot(dy, dz) * (math.pi / segs)) + 0.04
            col = '#DFC8A0' if i in (segs // 2 - 1, segs // 2) else ('#D3BA92' if i % 2 == 0 else '#C4AB84')
            b.box((0.20, seg_len, ring_th), (sx * (half_w + 0.04), y, z),
                  'ph_stone', col, bevel=0.0, rot=(pitch, 0, 0),
                  uv_off=(i * 0.31, sx * 0.4), spread=0.04)


def build_river_bridge():
    b = V4Builder(seed=201)
    rnd = b.rnd
    stone_hi, stone_mid, stone_wet = '#DAC39B', '#C3AA82', '#9F9072'
    wood_a, wood_b, wood_dark = '#9E6E40', '#835832', '#644225'
    rope_col, iron_col, glow_col = '#C4A264', '#38302A', '#F7CB65'

    # 4 heavy sandstone cutwater piers anchored down to riverbed (z = -2.8 .. +0.42)
    for py in (-9.3, -3.1, 3.1, 9.3):
        end_pier = abs(py) > 8.0
        pw = 4.15 if end_pier else 3.95
        pd = 1.65 if end_pier else 1.25
        # Lower submerged pier footing
        b.box((pw + 0.24, pd + 0.26, 2.25), (0, py, -1.68), 'ph_stone', stone_wet,
              bevel=0.07, seg=1, taper=0.93, wobble=0.020, spread=0.03)
        # Mid dressed sandstone pier shaft
        b.box((pw, pd, 1.05), (0, py, -0.08), 'ph_stone', stone_mid,
              bevel=0.05, seg=1, taper=0.96, wobble=0.014, spread=0.03)
        # Molded sandstone coping cap
        b.box((pw + 0.16, pd + 0.18, 0.18), (0, py, 0.39), 'ph_stone', stone_hi,
              bevel=0.03, seg=1, wobble=0.008, spread=0.025)
        # Pointed triangular stone cutwater prows on mid-river piers (upstream/downstream)
        if not end_pier:
            for sx in (-1, 1):
                b.cyl(0.58, 0.42, 2.85, (sx * (pw * 0.5 + 0.10), py, -1.15),
                      'ph_stone', stone_mid, verts=5, wobble=0.015, grain=None)
                b.cyl(0.46, 0.05, 0.34, (sx * (pw * 0.5 + 0.10), py, 0.42),
                      'ph_stone', stone_hi, verts=5, grain=None)

    # 3 sandstone vaulted masonry arches spanning the bays between piers
    for y0, y1 in ((-8.6, -3.6), (-2.6, 2.6), (3.6, 8.6)):
        _add_stone_arch_bay(b, y0, y1, half_w=1.80, z_spring=-0.52, z_crown=0.22, ring_th=0.24, segs=7)

    # Heavy longitudinal timber deck stringers running the full 20 m span
    for sx in (-1.52, -0.52, 0.52, 1.52):
        b.box((0.18, 20.1, 0.18), (sx, 0.0, 0.37), 'ph_wood', wood_dark,
              grain='y', uv_off=(sx, 0.0), spread=0.04)

    # 30 hand-hewn weathered deck planks (plank top cleanly at z = 0.55)
    n_planks = 30
    for i in range(n_planks):
        y = -9.82 + (19.64 * i) / (n_planks - 1)
        pw = 3.54 + rnd.uniform(-0.06, 0.06)
        col_p = wood_a if (i % 3 != 0) else wood_b
        b.box((pw, 0.58, 0.10), (rnd.uniform(-0.025, 0.025), y, 0.50),
              'ph_wood', col_p, bevel=0.0,
              rot=(0, 0, rnd.uniform(-0.006, 0.006)), wobble=0.004,
              grain='x', uv_off=(rnd.uniform(0, 3.0), i * 0.37), spread=0.06)

    # Timber wheel-curb beams along both edges of the deck
    for sx in (-1.66, 1.66):
        b.box((0.14, 19.4, 0.12), (sx, 0.0, 0.60), 'ph_wood', wood_dark, grain='y', spread=0.03)

    # 4 sculpted sandstone entrance bollards + wrought-iron & amber lanterns
    for sy in (-9.6, 9.6):
        for sx in (-1.78, 1.78):
            b.box((0.54, 0.54, 1.24), (sx, sy, 1.04), 'ph_stone', stone_hi,
                  bevel=0.045, seg=1, taper=0.88, wobble=0.012, spread=0.03)
            b.box((0.62, 0.62, 0.16), (sx, sy, 1.69), 'ph_stone', stone_mid,
                  bevel=0.025, seg=1, spread=0.025)
            b.cyl(0.14, 0.12, 0.32, (sx, sy, 1.94), 'ph_plaster', glow_col, verts=6, spread=0.01)
            b.cyl(0.20, 0.04, 0.18, (sx, sy, 2.18), 'ph_dark', iron_col, verts=6, spread=0.01)

    # Timber railing posts, double rails, knee braces & woven rope lashings
    rail_ys = (-7.4, -5.2, -3.1, -1.05, 1.05, 3.1, 5.2, 7.4)
    for sx in (-1.74, 1.74):
        b.box((0.13, 18.8, 0.10), (sx, 0.0, 1.44), 'ph_wood', wood_a, bevel=0.015, seg=1, grain='y', spread=0.04)
        b.box((0.09, 18.8, 0.08), (sx, 0.0, 1.02), 'ph_wood', wood_b, grain='y', spread=0.04)
        for idx, py in enumerate(rail_ys):
            b.box((0.15, 0.15, 1.02), (sx, py, 0.96), 'ph_wood', wood_dark,
                  grain='z', uv_off=(idx * 0.4, sx), spread=0.04)
            b.box((0.09, 0.09, 0.54), (sx + math.copysign(0.11, sx), py, 0.72),
                  'ph_wood', wood_b, rot=(0, math.copysign(0.45, sx), 0), grain='z', spread=0.04)
            b.cyl(0.096, 0.096, 0.08, (sx, py, 1.40), 'ph_cloth', rope_col, verts=6, grain=None)

    obj = b.to_object('river_bridge')
    bake_wear_and_ao(obj, base_z=-2.8, ao_strength=0.38, splash_h=0.0, splash_strength=0.0, wet_z=-0.20)
    return export_asset('river_bridge', obj, lod0_budget=4000, lod1_budget=1600)


# ---------------------------------------------------------------------------
# 2. Oasis Arish Shelter (oasis_arish.glb)
# Same footprint & spot as village.js: posts at X = +-2.0, Y = +-1.6, roof 4.8 x 4.0 at Z ~ 2.65,
# rug-covered bench at Three (0, 0.15, +0.6) -> Blender (0, -0.6, 0.15).
# ---------------------------------------------------------------------------

def build_oasis_arish():
    b = V4Builder(seed=210)
    rnd = b.rnd
    wood_post = '#7E5634'
    wood_beam = '#91663D'
    rope_col = '#C4A264'
    reed_a, reed_b = '#C8AA68', '#B89756'

    # 4 corner weathered palm-wood posts anchored in low sandstone collars
    for px, py in ((-2.0, -1.6), (2.0, -1.6), (-2.0, 1.6), (2.0, 1.6)):
        b.cyl(0.20, 0.17, 0.24, (px, py, 0.08), 'ph_stone', '#CBB38A', verts=7, wobble=0.012, grain=None)
        b.cyl(0.105, 0.088, 2.72, (px, py, 1.32), 'ph_wood', wood_post,
              verts=7, wobble=0.014, grain='z', uv_off=(px, py), spread=0.05)
        # Rope lashings at the beam joints
        b.cyl(0.115, 0.115, 0.12, (px, py, 2.50), 'ph_cloth', rope_col, verts=7, grain=None)
        # Diagonal knee braces
        b.box((0.08, 0.08, 0.72), (px - math.copysign(0.24, px), py, 2.26),
              'ph_wood', wood_beam, rot=(0, math.copysign(0.72, px), 0), grain='z', spread=0.04)
        b.box((0.08, 0.08, 0.72), (px, py - math.copysign(0.24, py), 2.26),
              'ph_wood', wood_beam, rot=(-math.copysign(0.72, py), 0, 0), grain='z', spread=0.04)

    # Perimeter timber eave beams (long along X, cross along Y)
    for py in (-1.6, 1.6):
        b.cyl(0.075, 0.070, 4.68, (0.0, py, 2.52), 'ph_wood', wood_beam,
              rot=(0, math.pi * 0.5, 0), verts=7, wobble=0.012, grain='z')
    for px in (-2.0, 2.0):
        b.cyl(0.070, 0.066, 3.88, (px, 0.0, 2.60), 'ph_wood', wood_post,
              rot=(math.pi * 0.5, 0, 0), verts=7, wobble=0.010, grain='z')

    # 7 rustic palm-rib rafters spanning Y across the roof
    for i in range(7):
        rx = -2.15 + i * (4.30 / 6.0)
        b.cyl(0.045, 0.042, 4.05, (rx, 0.0, 2.66), 'ph_wood', wood_beam,
              rot=(math.pi * 0.5, rnd.uniform(-0.02, 0.02), 0), verts=6, wobble=0.010, grain='z', uv_off=(i * 0.5, 0))

    # Layered woven palm-frond / reed thatch shade canopy (slightly pitched & ruffled, solid thickness)
    b.box((4.84, 4.04, 0.14), (0.0, 0.0, 2.75), 'ph_cloth', reed_a,
          bevel=0.04, seg=1, rot=(-0.035, 0, 0), wobble=0.025, freq=1.6, spread=0.03)
    # 5 overlapping reed mat bundles along the roof for rich tactile silhouette
    for i in range(5):
        ry = -1.60 + i * 0.80
        b.box((4.92, 0.74, 0.07), (rnd.uniform(-0.03, 0.03), ry, 2.83 + (i - 2) * 0.026),
              'ph_cloth', reed_a if i % 2 == 0 else reed_b,
              bevel=0.02, seg=1, rot=(-0.05, 0, 0), wobble=0.016, freq=2.2,
              uv_off=(i * 0.4, i * 0.7), spread=0.04)
    # Timber hold-down poles across the thatch
    for py in (-1.35, 0.0, 1.35):
        b.cyl(0.038, 0.035, 4.78, (0.0, py, 2.89 - py * 0.035), 'ph_wood', wood_post,
              rot=(0, math.pi * 0.5, 0), verts=6, wobble=0.008, grain='z')

    # Rug-covered resting bench (matching village.js box(2.4, 0.3, 1.2) at Three z=+0.6 -> Blender y=-0.6)
    by = -0.60
    b.box((2.40, 1.18, 0.32), (0.0, by, 0.14), 'ph_plaster', '#DEC49A',
          bevel=0.05, seg=1, wobble=0.010, spread=0.02)
    # Timber edge frame around bench top
    b.box((2.46, 1.24, 0.06), (0.0, by, 0.30), 'ph_wood', wood_beam, bevel=0.015, seg=1, grain='x')
    # Hand-woven crimson-terracotta oasis kilim rug + ochre/blue stripes + two bolsters
    b.box((2.18, 1.06, 0.024), (0.0, by, 0.342), 'ph_cloth', '#B44830', bevel=0.008, seg=1, wobble=0.004, spread=0.02)
    for sx, scol in ((-0.78, '#D9A03C'), (-0.42, '#3A6B8F'), (0.42, '#3A6B8F'), (0.78, '#D9A03C')):
        b.box((0.10, 1.07, 0.012), (sx, by, 0.356), 'ph_cloth', scol, smooth=False, spread=0.015)
    for sx, scol in ((-0.92, '#E6D4B2'), (0.92, '#D89E3E')):
        b.cyl(0.11, 0.11, 0.62, (sx, by + 0.10, 0.45), 'ph_cloth', scol,
              rot=(math.pi * 0.5, 0, rnd.uniform(-0.12, 0.12)), verts=9, bevel=0.035, spread=0.02)

    obj = b.to_object('oasis_arish')
    bake_wear_and_ao(obj, base_z=0.0, eaves_z=2.75, ao_strength=0.40, splash_strength=0.14)
    return export_asset('oasis_arish', obj, lod0_budget=2000, lod1_budget=800)


# ---------------------------------------------------------------------------
# 3. Ancient Sandstone Ruins Set (5 GLBs, each <= 700 / 300 tris)
# ---------------------------------------------------------------------------

def _build_ruins_wall(name, nominal_h, seed, blocks_top):
    """Weathered ancient sandstone wall (4.0 m along X, 0.9 m along Y, nominal height `nominal_h`)."""
    b = V4Builder(seed=seed)
    rnd = b.rnd
    st_a, st_b, st_c = '#D4BC93', '#C5AC82', '#DFC9A4'

    # Stepped wider stone footing anchored slightly below y=0
    b.box((4.02, 0.96, 0.34), (0.0, 0.0, 0.15), 'ph_stone', st_b,
          bevel=0.04, seg=1, wobble=0.020, freq=1.3, spread=0.03)

    # Main battered ancient sandstone wall core (slightly lower than nominal_h so broken top stones crown it)
    core_h = max(0.55, nominal_h - 0.36)
    b.box((3.96, 0.88, core_h), (0.0, 0.0, 0.22 + core_h * 0.5), 'ph_stone', st_a,
          bevel=0.045, seg=1, taper=0.96, wobble=0.024, freq=1.1, spread=0.03)

    # Molded sandstone stringcourse on mid & tall walls
    if nominal_h >= 2.0:
        b.box((4.04, 0.96, 0.16), (0.0, 0.0, nominal_h * 0.52), 'ph_stone', st_c,
              bevel=0.025, seg=1, wobble=0.014, spread=0.025)

    # Stepped crumbling ashlar stone blocks along the eroded crest
    z_top = 0.22 + core_h
    for bx, bw, bh in blocks_top:
        b.box((bw, 0.82 + rnd.uniform(-0.06, 0.04), bh),
              (bx, rnd.uniform(-0.02, 0.02), z_top + bh * 0.5 - 0.06),
              'ph_stone', rnd.choice((st_a, st_b, st_c)),
              bevel=0.035, seg=1, wobble=0.018, freq=1.6,
              uv_off=(bx * 0.7, bh), spread=0.045)

    # A couple of protruding weathered corner stones for silhouette relief
    for sx in (-1.55, 0.25, 1.45):
        sz = rnd.uniform(0.35, max(0.45, core_h - 0.1))
        b.box((0.68, 0.93, 0.28), (sx, rnd.uniform(-0.02, 0.02), sz),
              'ph_stone', rnd.choice((st_a, st_c)), bevel=0.028, seg=1, wobble=0.014,
              uv_off=(sx, sz), spread=0.045)

    obj = b.to_object(name)
    bake_wear_and_ao(obj, base_z=0.0, ao_strength=0.42, splash_h=0.55, splash_strength=0.18)
    return export_asset(name, obj, lod0_budget=700, lod1_budget=300)


def build_ruins_wall_a():
    """Low ruined wall (~1.2 m tall, 4.0 x 0.9 m)."""
    return _build_ruins_wall('ruins_wall_a', 1.20, seed=221, blocks_top=[
        (-1.45, 0.95, 0.42),
        (-0.35, 1.05, 0.24),
        (0.95,  1.25, 0.48),
    ])


def build_ruins_wall_b():
    """Mid ruined wall (~2.2 m tall, 4.0 x 0.9 m)."""
    return _build_ruins_wall('ruins_wall_b', 2.20, seed=222, blocks_top=[
        (-1.40, 1.08, 0.52),
        (-0.15, 1.15, 0.30),
        (1.15,  1.22, 0.58),
    ])


def build_ruins_wall_c():
    """Tall ruined wall (~3.4 m tall, 4.0 x 0.9 m)."""
    return _build_ruins_wall('ruins_wall_c', 3.40, seed=223, blocks_top=[
        (-1.35, 1.15, 0.56),
        (0.05,  1.25, 0.44),
        (1.38,  0.98, 0.32),
    ])


def build_ruins_column():
    """Ancient weathered sandstone drum column (nominal height 4.2 m, radius ~0.40 m).
    Works both upright (scaled to broken or full height) and laid horizontally as a fallen column."""
    b = V4Builder(seed=224)
    st_a, st_b, st_c = '#D7C098', '#C6AD84', '#E0CB9F'

    # Stepped square sandstone plinth base
    b.box((1.02, 1.02, 0.24), (0.0, 0.0, 0.12), 'ph_stone', st_b, bevel=0.03, seg=1, wobble=0.012, spread=0.03)
    b.cyl(0.46, 0.43, 0.18, (0.0, 0.0, 0.31), 'ph_stone', st_a, verts=12, wobble=0.010, grain=None)

    # 5 stacked cylindrical sandstone drums with crisp mortar shadow seams (scales cleanly for tall, broken & fallen columns)
    drum_z = [0.40, 1.16, 1.92, 2.68, 3.44, 4.10]
    for i in range(len(drum_z) - 1):
        z0, z1 = drum_z[i], drum_z[i + 1]
        t0 = i / (len(drum_z) - 1)
        t1 = (i + 1) / (len(drum_z) - 1)
        r0 = 0.42 - 0.045 * t0
        r1 = 0.42 - 0.045 * t1
        b.cyl(r0, r1, (z1 - z0) - 0.018, (0.0, 0.0, 0.5 * (z0 + z1)),
              'ph_stone', st_a if i % 2 == 0 else st_b,
              verts=12, bevel=0.0, wobble=0.010, grain=None,
              uv_off=(i * 0.45, z0), spread=0.04)

    # Subtle weathered carved collar ring at the top (no overhanging flat slab when scaled to broken stubs)
    b.cyl(0.38, 0.42, 0.14, (0.0, 0.0, 4.17), 'ph_stone', st_c, verts=12, wobble=0.010, grain=None)

    obj = b.to_object('ruins_column')
    bake_wear_and_ao(obj, base_z=0.0, ao_strength=0.38, splash_h=0.50, splash_strength=0.14)
    return export_asset('ruins_column', obj, lod0_budget=700, lod1_budget=300)


def build_ruins_arch():
    """Ancient sandstone gate arch: twin piers at X = +-2.0 (0.9 x 0.9 x 3.4 m), sculpted voussoir
    arch ring with proud keystone rising cleanly over the road."""
    b = V4Builder(seed=225)
    st_a, st_b, st_c = '#D5BD95', '#C2A980', '#E0CA9E'

    # Twin weathered sandstone gate piers (exact collider positions X = +-2.0, 0.9 x 0.9)
    for sx in (-2.0, 2.0):
        b.box((1.06, 1.06, 0.36), (sx, 0.0, 0.16), 'ph_stone', st_b, bevel=0.04, seg=1, wobble=0.014, spread=0.03)
        b.box((0.92, 0.92, 2.86), (sx, 0.0, 1.74), 'ph_stone', st_a,
              bevel=0.04, seg=1, taper=0.97, wobble=0.018, spread=0.03)
        # Molded impost capital at arch springing (z = 3.28)
        b.box((1.10, 1.08, 0.24), (sx, 0.0, 3.28), 'ph_stone', st_c, bevel=0.03, seg=1, wobble=0.012, spread=0.025)

    # 9 sculpted radial sandstone voussoir arch blocks spanning X in [-2.0, +2.0] above z = 3.38
    n_v = 9
    R = 1.98
    for i in range(n_v):
        t = (i + 0.5) / n_v
        ang = t * math.pi
        is_key = (i == n_v // 2)
        rad = R + (0.06 if is_key else 0.0)
        vx = -math.cos(ang) * rad
        vz = 3.36 + math.sin(ang) * rad
        rot_y = -(ang - math.pi * 0.5)
        bw = 0.78 if is_key else 0.76
        bd = 0.96 if is_key else 0.88
        bh = 0.82 if is_key else 0.66
        col = st_c if is_key else (st_a if i % 2 == 0 else st_b)
        b.box((bw, bd, bh), (vx, 0.0, vz), 'ph_stone', col,
              bevel=0.0, rot=(0, rot_y, 0), wobble=0.014,
              uv_off=(i * 0.37, 0.2), spread=0.04)

    # Eroded upper lintel shoulder blocks over the arch haunches
    for sx in (-1.65, 1.65):
        b.box((1.35, 0.86, 0.46), (sx, 0.0, 5.20), 'ph_stone', st_b,
              bevel=0.0, wobble=0.018, spread=0.04)

    obj = b.to_object('ruins_arch')
    bake_wear_and_ao(obj, base_z=0.0, ao_strength=0.40, splash_h=0.55, splash_strength=0.16)
    return export_asset('ruins_arch', obj, lod0_budget=700, lod1_budget=300)


def main():
    builders = [
        build_river_bridge,
        build_oasis_arish,
        build_ruins_wall_a,
        build_ruins_wall_b,
        build_ruins_wall_c,
        build_ruins_column,
        build_ruins_arch,
    ]
    for fn in builders:
        reset_scene()
        fn()


if __name__ == '__main__':
    main()
