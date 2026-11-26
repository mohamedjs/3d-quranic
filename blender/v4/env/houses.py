"""Build M3 Egyptian Nile houses (6 variants), mastaba, garden wall & preview sheet.

Usage:
  blender -b --factory-startup --python blender/v4/env/houses.py
  blender -b --factory-startup --python blender/v4/env/houses.py -- --sheet
"""
import math
import sys
from pathlib import Path

from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib
from lib import V4Builder, bake_wear_and_ao, export_asset, reset_scene

# Original < 2.2 m footprints (exact walkability contract from existing house_a/b/c GLBs)
LIMIT_A = (-2.89, 2.89, -2.59, 2.48)
LIMIT_B = (-3.69, 3.54, -2.91, 2.78)
LIMIT_C = (-2.39, 2.39, -2.39, 2.28)

ALL_M3_MODELS = [
    'house_a', 'house_b', 'house_c', 'house_d', 'house_e', 'house_f',
    'mastaba', 'garden_wall', 'river_bridge', 'oasis_arish',
    'ruins_wall_a', 'ruins_wall_b', 'ruins_wall_c', 'ruins_column', 'ruins_arch',
]


# ---------------------------------------------------------------------------
# Architectural Details (metric UVs, recessed openings, mudbrick wear, folk bands)
# ---------------------------------------------------------------------------

def add_plinth(b, w, d, h=0.34, mat='ph_mudbrick', color='#C69666', pad=0.14):
    """Low stepped earth/mudbrick skirt grounding the walls into the Nile dirt."""
    b.box((w + pad, d + pad, h), (0, 0, h * 0.5 - 0.06), mat, color,
          bevel=0.06, seg=1, taper=0.975, wobble=0.016, freq=0.9, spread=0.02)


def add_parapet(b, w, d, h, mat='ph_plaster', color='#EFE1C5', ph=0.42, th=0.22,
                horns=True, horn_col=None, taper=0.978):
    """Rounded mud-plaster parapet with optional Upper-Egypt sculpted corner horns."""
    tw, td = w * taper, d * taper
    z = h + ph * 0.5 - 0.03
    for s in (-1, 1):
        b.box((tw + 0.02, th, ph), (0, s * (td * 0.5 - th * 0.5), z), mat, color,
              bevel=0.07, seg=1, wobble=0.016, freq=1.0, spread=0.015)
        b.box((th, td - th * 1.4, ph), (s * (tw * 0.5 - th * 0.5), 0, z), mat, color,
              bevel=0.07, seg=1, wobble=0.016, freq=1.0, spread=0.015)
    if horns:
        hc = horn_col or color
        for sx in (-1, 1):
            for sy in (-1, 1):
                b.lathe(
                    [(0.19, 0.0), (0.18, 0.12), (0.12, 0.28), (0.06, 0.39), (0.001, 0.44)],
                    (sx * (tw * 0.5 - 0.11), sy * (td * 0.5 - 0.11), h + ph - 0.07),
                    mat, hc, segs=7, wobble=0.008, spread=0.015,
                )


def add_beams(b, w, d, h, n, rnd, out=0.30, r=0.072, sides=(-1, 1), taper=0.978, color='#8E623A'):
    """Projecting hand-hewn palm-log roof joists with grain along beam length."""
    tw, td = w * taper, d * taper
    for i in range(n):
        x = -tw * 0.5 + (i + 0.5) * tw / n + rnd.uniform(-0.04, 0.04)
        for s in sides:
            L = out + rnd.uniform(-0.04, 0.08)
            b.cyl(
                r * rnd.uniform(0.88, 1.10), r * 0.90, 0.45 + L,
                (x, s * (td * 0.5 + L * 0.5 - 0.22), h - 0.20 + rnd.uniform(-0.025, 0.025)),
                'ph_wood', color, rot=(math.pi * 0.5, rnd.uniform(-0.05, 0.05), 0),
                verts=7, wobble=0.008, grain='z', uv_off=(rnd.uniform(0, 2), rnd.uniform(0, 2)),
            )


def add_recessed_door(b, x, fy, w=0.96, h=1.92, depth=0.18, leaf_col='#3C82B4',
                      frame_mat='ph_blue', frame_col='#3C79A8', arch=True,
                      taper=0.978, wall_h=3.1, lintel_wood=False):
    """Door set cleanly inside a wall_shell recess: vertical plank boards, battens, iron ring & step."""
    # Wall front face moves slightly inward with height due to taper
    def y_wall(z):
        t = max(0.0, min(1.0, z / max(wall_h, 1e-4)))
        return fy * (1.0 + (taper - 1.0) * t)

    ym = y_wall(h * 0.5)
    # Recessed wooden door panel made of 4 vertical planks (grain vertical = 'z')
    n_planks = 4
    pw = (w - 0.04) / n_planks
    door_y = ym + depth - 0.045
    for i in range(n_planks):
        px = x - (w - 0.04) * 0.5 + (i + 0.5) * pw
        b.box((pw - 0.012, 0.055, h - 0.04), (px, door_y, h * 0.5),
              'ph_wood', leaf_col, bevel=0.0, grain='z',
              uv_off=(i * 0.37, i * 0.19), spread=0.045)
    # Horizontal cross battens (grain horizontal = 'x')
    for bz in (0.36, h * 0.52, h - 0.34):
        b.box((w - 0.08, 0.04, 0.085), (x, door_y - 0.032, bz),
              'ph_wood', leaf_col, bevel=0.0, grain='x', uv_off=(0.2, bz), spread=0.04)
    # Dark center seam + iron ring knocker
    b.box((0.022, 0.022, h - 0.08), (x, door_y - 0.025, h * 0.5), 'ph_dark', '#2E231D', smooth=False, spread=0.0)
    b.cyl(0.052, 0.052, 0.024, (x + 0.22, door_y - 0.052, 1.02), 'ph_dark', '#3C3734',
          rot=(math.pi * 0.5, 0, 0), verts=6, spread=0.0)

    # Painted plaster frame surround (proud by 1.8 cm, solid thickness — zero z-fighting)
    fw = 0.14
    if frame_mat:
        for sx in (-1, 1):
            b.box((fw, 0.04, h - 0.08), (x + sx * (w * 0.5 + fw * 0.5), ym - 0.016, h * 0.5 + 0.04),
                  frame_mat, frame_col, bevel=0.0, spread=0.02)
    if lintel_wood:
        yt = y_wall(h + 0.08)
        b.box((w + 0.54, 0.22, 0.18), (x, yt - 0.05, h + 0.09),
              'ph_wood', '#8B5E38', bevel=0.02, seg=1, wobble=0.008, grain='x', spread=0.04)
    elif arch:
        yt = y_wall(h)
        seg = 7
        R_out = w * 0.5 + fw
        R_in = w * 0.5
        for i in range(seg):
            a0 = math.pi * i / seg
            a1 = math.pi * (i + 1) / seg
            am = 0.5 * (a0 + a1)
            rm = 0.5 * (R_out + R_in)
            seg_len = (math.pi / seg) * rm + 0.03
            cx = x + math.cos(am) * rm
            cz = h + math.sin(am) * rm * 0.72
            ang_y = -math.atan2(math.cos(am) * 0.72, -math.sin(am))
            b.box((seg_len, 0.05, fw), (cx, yt - 0.016, cz),
                  frame_mat or 'ph_plaster', frame_col, bevel=0.0,
                  rot=(0, ang_y, 0), spread=0.02)
        # Recessed dark fanlight lunette
        for i in range(seg):
            a0 = math.pi * i / seg
            a1 = math.pi * (i + 1) / seg
            b.quad([
                (x, yt + 0.06, h),
                (x + math.cos(a1) * R_in, yt + 0.06, h + math.sin(a1) * R_in * 0.72),
                (x + math.cos(a0) * R_in, yt + 0.06, h + math.sin(a0) * R_in * 0.72),
            ], 'ph_dark', '#2A1E18', spread=0.0)
    else:
        yt = y_wall(h + 0.06)
        b.box((w + fw * 2.0, 0.045, fw), (x, yt - 0.016, h + fw * 0.5),
              frame_mat or 'ph_plaster', frame_col, bevel=0.01, seg=1, spread=0.02)

    # Clay/stone threshold step (stays well inside plinth footprint)
    yb = y_wall(0.06)
    b.box((w + 0.30, 0.20, 0.09), (x, yb - 0.05, 0.045),
          'ph_floor', '#D5B88E', bevel=0.025, seg=1, spread=0.02)


def add_recessed_window(b, pos_s, wall_coord, z, w=0.64, h=0.76, face='front',
                        shutter_col='#3E86B8', open_=True, sill_col='#8F6139',
                        taper=0.978, wall_h=3.1, depth=0.16, grille=True):
    """Wooden sill, lintel, lattice bars & hinged shutters framing a wall_shell window recess."""
    t = max(0.0, min(1.0, z / max(wall_h, 1e-4)))
    wc = wall_coord * (1.0 + (taper - 1.0) * t)

    if face == 'front':
        # Wooden sill & lintel
        b.box((w + 0.22, 0.14, 0.09), (pos_s, wc - 0.03, z - h * 0.5 - 0.045),
              'ph_wood', sill_col, bevel=0.0, grain='x', spread=0.035)
        b.box((w + 0.20, 0.12, 0.10), (pos_s, wc - 0.02, z + h * 0.5 + 0.05),
              'ph_wood', sill_col, bevel=0.0, grain='x', spread=0.035)
        if grille:
            for k in (-1, 0, 1):
                b.box((0.03, 0.03, h - 0.04), (pos_s + k * (w * 0.25), wc + depth * 0.45, z),
                      'ph_wood', '#68462A', grain='z', spread=0.03)
            b.box((w - 0.04, 0.03, 0.03), (pos_s, wc + depth * 0.45, z),
                  'ph_wood', '#68462A', grain='x', spread=0.03)
        for s in (-1, 1):
            sw = w * 0.49
            if open_:
                b.box((sw, 0.045, h * 0.96),
                      (pos_s + s * (w * 0.5 + sw * 0.46), wc - 0.08, z),
                      'ph_wood', shutter_col, bevel=0.0,
                      rot=(0, 0, s * -0.32), grain='z', uv_off=(s * 0.5, z), spread=0.04)
            else:
                b.box((sw - 0.01, 0.045, h * 0.96),
                      (pos_s + s * (sw * 0.5), wc + 0.04, z),
                      'ph_wood', shutter_col, bevel=0.0, grain='z', spread=0.04)
    else:
        sg = 1 if face == 'right' else -1
        b.box((0.14, w + 0.20, 0.09), (wc + sg * 0.03, pos_s, z - h * 0.5 - 0.045),
              'ph_wood', sill_col, bevel=0.0, grain='y', spread=0.035)
        b.box((0.12, w + 0.18, 0.10), (wc + sg * 0.02, pos_s, z + h * 0.5 + 0.05),
              'ph_wood', sill_col, bevel=0.0, grain='y', spread=0.035)
        for k in (-1, 1):
            b.box((0.035, 0.032, h - 0.04), (wc - sg * depth * 0.42, pos_s + k * (w * 0.22), z),
                  'ph_wood', shutter_col, grain='z', spread=0.03)
        b.box((0.035, w - 0.04, 0.032), (wc - sg * depth * 0.42, pos_s, z),
              'ph_wood', shutter_col, grain='y', spread=0.03)


def add_mudbrick_patch(b, x, y, z, sx, sy, sz, color='#BD7F4E'):
    """Slightly proud beveled patch where lime plaster has flaked away, revealing raw mudbrick."""
    b.box((sx, sy, sz), (x, y, z), 'ph_mudbrick', color,
          bevel=0.02, seg=1, wobble=0.012, freq=2.2, spread=0.04)


def add_folk_band(b, x0, x1, y_face, z, h, mat='ph_blue', color='#2E74AC',
                  triangles=True, wall_h=3.1, taper=0.978):
    """Painted geometric Egyptian folk frieze strip with solid thickness (no z-fighting)."""
    t = max(0.0, min(1.0, z / max(wall_h, 1e-4)))
    yf = y_face * (1.0 + (taper - 1.0) * t)
    # Thin raised plaster strip
    b.box((x1 - x0, 0.026, 0.042), ((x0 + x1) * 0.5, yf - 0.008, z - 0.03),
          mat, color, smooth=False, spread=0.015)
    if triangles:
        n = max(4, int((x1 - x0) / 0.36))
        tw = (x1 - x0) / n
        for i in range(n):
            a = x0 + i * tw
            # Slight relief wedge proud by 1.6 cm
            b.quad([
                (a + 0.02, yf - 0.018, z + 0.01),
                (a + tw - 0.02, yf - 0.018, z + 0.01),
                (a + tw * 0.5, yf - 0.018, z + h),
            ], mat, color, smooth=False, spread=0.02)


def add_firewood(b, x, y, z, L, n, rnd, r=0.068, along='x'):
    """Roof stack of firewood / cotton-stalk bundles."""
    k = 0
    for row in range(2):
        for i in range(n - row):
            rr = r * rnd.uniform(0.86, 1.15)
            off = (i - (n - row - 1) * 0.5) * r * 2.05
            p = (x, y + off, z + row * r * 1.7 + rr) if along == 'x' else (x + off, y, z + row * r * 1.7 + rr)
            rot = (0, math.pi * 0.5, rnd.uniform(-0.07, 0.07)) if along == 'x' else (math.pi * 0.5, 0, rnd.uniform(-0.07, 0.07))
            col = '#AE8B54' if (k % 3) else '#825F3C'
            b.cyl(rr, rr * 0.90, L * rnd.uniform(0.88, 1.04), p, 'ph_wood', col,
                  rot=rot, verts=6, wobble=0.012, grain='z', uv_off=(k * 0.4, row * 0.3))
            k += 1


def add_roof_jar(b, x, y, z, scale=1.0):
    """Terracotta roof water jar (زير / قلة)."""
    prof = [(0.001, 0), (0.14 * scale, 0.02), (0.23 * scale, 0.20 * scale),
            (0.20 * scale, 0.36 * scale), (0.10 * scale, 0.46 * scale), (0.12 * scale, 0.54 * scale)]
    b.lathe(prof, (x, y, z), 'ph_mudbrick', '#C77442', segs=10, spread=0.03)


def add_dome(b, x, y, z, r=1.05, drum_h=0.34, mat='ph_plaster', color='#F3E7CE', finial_col='#D49838'):
    """Classic Upper-Egypt / Nubian mudbrick dome on a low drum with sculpted finial."""
    b.cyl(r + 0.05, r + 0.04, drum_h, (x, y, z + drum_h * 0.5), mat, color,
          verts=16, bevel=0.04, wobble=0.01, grain=None, spread=0.015)
    # Slightly pointed parabolic mudbrick dome profile (feels genuinely Egyptian!)
    prof = []
    steps = 8
    for i in range(steps + 1):
        t = i / steps
        ang = t * (math.pi * 0.5)
        rr = max(0.001, r * math.cos(ang) ** 0.88)
        zz = r * 1.02 * math.sin(ang) ** 1.08
        prof.append((rr, zz))
    b.lathe(prof, (x, y, z + drum_h - 0.02), mat, color, segs=16, wobble=0.012, spread=0.015)
    b.cyl(0.055, 0.02, 0.34, (x, y, z + drum_h + r * 1.02 + 0.14),
          'ph_wood', finial_col, verts=6, spread=0.02)


def add_pigeon_tower(b, x, y, z, rnd, s=0.95):
    """برج حمام: sculpted mudbrick pigeon tower with nesting pot holes and wooden perches (no birds/animals)."""
    prof = [
        (0.001, 0.0), (0.94 * s, 0.0), (0.98 * s, 0.35 * s), (0.88 * s, 1.15 * s),
        (0.64 * s, 1.95 * s), (0.34 * s, 2.50 * s), (0.14 * s, 2.70 * s), (0.001, 2.78 * s),
    ]
    b.lathe(prof, (x, y, z), 'ph_plaster', '#E6C99E', segs=12, wobble=0.022, spread=0.02)
    # Sculpted mudbrick horizontal rim ledges + recessed clay nesting pots + wooden perching sticks
    for ring, (rz, rr) in enumerate(((0.58, 0.96), (1.18, 0.88), (1.76, 0.70))):
        if ring % 2 == 0:
            b.cyl((rr + 0.05) * s, (rr + 0.02) * s, 0.09 * s, (x, y, z + (rz - 0.14) * s),
                  'ph_mudbrick', '#C48A56', verts=10, grain=None, spread=0.03)
        n = int(5 * rr) + 3
        for i in range(n):
            a = i / n * math.tau + ring * 0.42
            px, py = x + math.cos(a) * rr * s, y + math.sin(a) * rr * s
            b.cyl(0.072 * s, 0.068 * s, 0.11 * s, (px, py, z + rz * s),
                  'ph_mudbrick', '#B96B3D', rot=(math.pi * 0.5, 0, a + math.pi * 0.5),
                  verts=5, cap=False, grain=None)
            b.cyl(0.055 * s, 0.055 * s, 0.03 * s,
                  (x + math.cos(a) * (rr * s + 0.035), y + math.sin(a) * (rr * s + 0.035), z + rz * s),
                  'ph_dark', '#2A1E17', rot=(math.pi * 0.5, 0, a + math.pi * 0.5), verts=5, spread=0.0)
        for i in range(3):
            a = i / 3.0 * math.tau + ring * 0.9
            b.cyl(0.020 * s, 0.017 * s, 0.78 * s,
                  (x + math.cos(a) * (rr * s + 0.12), y + math.sin(a) * (rr * s + 0.12), z + (rz - 0.15) * s),
                  'ph_wood', '#7E5634', rot=(math.pi * 0.5, 0, a + math.pi * 0.5), verts=5, grain='z')


def add_roof_reed_arish(b, cx, cy, z0, w, d, h_post=1.55, slope=0.14):
    """Light timber-and-reed rooftop shade pergola (sits above z = 3.0 m, outside <2.2 m bounds)."""
    hw, hd = w * 0.5, d * 0.5
    for sx in (-1, 1):
        for sy in (-1, 1):
            hp = h_post + (slope if sy > 0 else 0.0)
            b.cyl(0.062, 0.052, hp, (cx + sx * (hw - 0.14), cy + sy * (hd - 0.14), z0 + hp * 0.5),
                  'ph_wood', '#865B36', verts=6, wobble=0.008, grain='z')
    # Cross beams
    for sy in (-1, 1):
        zb = z0 + h_post + (slope if sy > 0 else 0.0)
        b.cyl(0.052, 0.050, w + 0.22, (cx, cy + sy * (hd - 0.14), zb),
              'ph_wood', '#785030', rot=(0, math.pi * 0.5, 0), verts=6, grain='z')
    # Woven palm-frond / reed mat canopy with solid thickness
    ang = math.atan2(slope, d - 0.28)
    b.box((w + 0.30, d + 0.28, 0.10), (cx, cy, z0 + h_post + slope * 0.5 + 0.07),
          'ph_cloth', '#C6A868', bevel=0.025, seg=1, rot=(-ang, 0, 0), wobble=0.016, spread=0.035)


# ---------------------------------------------------------------------------
# 6 House Variants (3 Footprints)
# ---------------------------------------------------------------------------

def build_house_a():
    """Grandma Zainab's house: sunlit cream limewash, recessed blue arched door (x=-0.59),
    open wall for mastaba (x=0.05..2.55, front wall y=-2.40), folk blue frieze, corner horns."""
    b = V4Builder(seed=101)
    w, d, h = 5.6, 4.8, 3.1
    fy = -d * 0.5
    openings = [
        {'face': 'front', 's': -0.59, 'z0': 0.04, 'z1': 1.94, 'w': 0.96, 'depth': 0.18, 'back': True},
        {'face': 'front', 's': 1.82,  'z0': 1.54, 'z1': 2.28, 'w': 0.64, 'depth': 0.16, 'back': True},
        {'face': 'right', 's': 0.40,  'z0': 1.52, 'z1': 2.26, 'w': 0.62, 'depth': 0.16, 'back': True},
        {'face': 'left',  's': -0.30, 'z0': 1.52, 'z1': 2.26, 'w': 0.62, 'depth': 0.16, 'back': True},
    ]
    b.wall_shell(w, d, h, mat='ph_plaster', color='#F2E5CC', taper=0.980, wobble=0.022,
                 openings=openings, reveal_mat='ph_plaster', reveal_color='#E6D4B4')
    add_plinth(b, w, d, h=0.34, mat='ph_plaster', color='#D7AE7C', pad=0.14)
    add_parapet(b, w, d, h, mat='ph_plaster', color='#ECDCB9', ph=0.42, horns=True, horn_col='#F2E4C8', taper=0.980)
    add_beams(b, w, d, h, 6, b.rnd, out=0.30, taper=0.980)

    add_recessed_door(b, -0.59, fy, w=0.96, h=1.92, leaf_col='#3D86B8',
                      frame_mat='ph_blue', frame_col='#3A79A8', arch=True, taper=0.980, wall_h=h)
    add_recessed_window(b, 1.82, fy, 1.91, w=0.64, h=0.74, face='front',
                        shutter_col='#3E88BA', open_=True, taper=0.980, wall_h=h)
    add_recessed_window(b, 0.40, w * 0.5, 1.89, w=0.62, h=0.74, face='right',
                        shutter_col='#3E88BA', taper=0.980, wall_h=h)
    add_recessed_window(b, -0.30, -w * 0.5, 1.89, w=0.62, h=0.74, face='left',
                        shutter_col='#3E88BA', taper=0.980, wall_h=h)

    # Geometric folk frieze under parapet + weathered mudbrick patches on side/back base
    add_folk_band(b, -w * 0.5 + 0.26, w * 0.5 - 0.26, fy, 2.58, 0.16, mat='ph_blue', color='#2E72A6', wall_h=h, taper=0.980)
    add_mudbrick_patch(b, -2.76, 1.15, 0.68, 0.05, 0.85, 0.52, '#BD7E4C')
    add_mudbrick_patch(b, 1.25, 2.37, 0.62, 0.95, 0.05, 0.48, '#BA7A48')
    add_mudbrick_patch(b, 2.76, -1.25, 0.58, 0.05, 0.72, 0.42, '#C08250')

    # Roof life: firewood bundles, straw heap, terracotta water jar, rain drain spout
    add_firewood(b, 0.25, 1.50, h + 0.02, 3.2, 4, b.rnd, along='x')
    b.lathe([(0.001, 0), (0.65, 0.02), (0.72, 0.20), (0.52, 0.42), (0.001, 0.50)],
            (-1.65, 1.18, h + 0.02), 'ph_cloth', '#DEC06C', segs=10, wobble=0.04, scale=(1.15, 0.85, 0.85))
    add_roof_jar(b, 1.85, -1.35, h + 0.03)
    b.cyl(0.075, 0.062, 0.58, (w * 0.5 + 0.16, 1.15, h - 0.06), 'ph_mudbrick', '#C27442',
          rot=(0, math.pi * 0.5 - 0.20, 0), verts=7, grain=None)

    obj = b.to_object('house_a')
    bake_wear_and_ao(obj, base_z=0.0, eaves_z=h, ao_strength=0.40, splash_strength=0.16)
    return export_asset('house_a', obj, lod0_budget=4500, lod1_budget=1500, max_lt22=LIMIT_A)


def build_house_d():
    """House A footprint variant: blue-washed lower dado, warm cream-ochre upper, natural
    timber door with heavy lintel, green shutters, rear dome + rooftop reed arish pergola."""
    b = V4Builder(seed=104)
    w, d, h = 5.5, 4.7, 3.15
    fy = -d * 0.5
    openings = [
        {'face': 'front', 's': 0.92,  'z0': 0.04, 'z1': 1.94, 'w': 0.96, 'depth': 0.18, 'back': True},
        {'face': 'front', 's': -1.40, 'z0': 1.44, 'z1': 2.20, 'w': 0.62, 'depth': 0.16, 'back': True},
        {'face': 'front', 's': -0.32, 'z0': 1.44, 'z1': 2.20, 'w': 0.62, 'depth': 0.16, 'back': True},
        {'face': 'left',  's': 0.35,  'z0': 1.48, 'z1': 2.22, 'w': 0.64, 'depth': 0.16, 'back': True},
        {'face': 'right', 's': -0.40, 'z0': 1.48, 'z1': 2.22, 'w': 0.64, 'depth': 0.16, 'back': True},
    ]
    b.wall_shell(w, d, h, mat='ph_plaster', color='#EDD8B2', taper=0.976, wobble=0.024,
                 openings=openings, reveal_mat='ph_plaster', reveal_color='#DFC79C')
    # Weathered Egyptian blue-wash lower wall band (0.30..1.18 m) around the house
    add_plinth(b, w, d, h=0.34, mat='ph_mudbrick', color='#BC8354', pad=0.14)
    for sx in (-1, 1):
        b.box((0.05, d - 0.36, 0.86), (sx * (w * 0.5 + 0.005), 0.0, 0.74),
              'ph_blue', '#84B5C0', bevel=0.015, seg=1, wobble=0.01, spread=0.02)
    b.box((w - 0.36, 0.05, 0.86), (0.0, d * 0.5 + 0.005, 0.74),
          'ph_blue', '#84B5C0', bevel=0.015, seg=1, wobble=0.01, spread=0.02)
    # Front blue dado split cleanly around the doorway (s = 0.92, half-w 0.48 -> x in [0.44, 1.40])
    b.box((2.82, 0.05, 0.86), (-1.12, fy - 0.005, 0.74),
          'ph_blue', '#84B5C0', bevel=0.015, seg=1, wobble=0.01, spread=0.02)
    b.box((1.06, 0.05, 0.86), (2.06, fy - 0.005, 0.74),
          'ph_blue', '#84B5C0', bevel=0.015, seg=1, wobble=0.01, spread=0.02)

    add_parapet(b, w, d, h, mat='ph_plaster', color='#E7CE9F', ph=0.38, horns=False, taper=0.976)
    # Stepped crenellation merlons on front & back parapet (distinctive silhouette!)
    for sy in (-1, 1):
        for mx in (-1.9, -0.95, 0.0, 0.95, 1.9):
            b.box((0.36, 0.22, 0.22), (mx, sy * (d * 0.976 * 0.5 - 0.11), h + 0.44),
                  'ph_plaster', '#EFE0C0', bevel=0.05, seg=1, taper=0.72, spread=0.015)

    add_beams(b, w, d, h, 5, b.rnd, out=0.28, taper=0.976, color='#805633')
    add_recessed_door(b, 0.92, fy, w=0.96, h=1.92, leaf_col='#92663D',
                      frame_mat='ph_mudbrick', frame_col='#C48956', arch=False,
                      taper=0.976, wall_h=h, lintel_wood=True)
    for wx in (-1.40, -0.32):
        add_recessed_window(b, wx, fy, 1.82, w=0.62, h=0.76, face='front',
                            shutter_col='#4B8E69', open_=True, taper=0.976, wall_h=h)
    add_recessed_window(b, 0.35, -w * 0.5, 1.85, w=0.64, h=0.74, face='left',
                        shutter_col='#4B8E69', taper=0.976, wall_h=h)
    add_recessed_window(b, -0.40, w * 0.5, 1.85, w=0.64, h=0.74, face='right',
                        shutter_col='#4B8E69', taper=0.976, wall_h=h)

    add_mudbrick_patch(b, -2.20, fy - 0.008, 1.92, 0.65, 0.04, 0.55, '#BD7E4E')
    add_mudbrick_patch(b, 2.71, 1.10, 1.80, 0.04, 0.80, 0.52, '#B97848')

    # Rear mudbrick dome + timber/reed rooftop shade arish
    add_dome(b, -1.15, 0.65, h - 0.02, r=0.98, drum_h=0.30, mat='ph_plaster', color='#F0E0C0')
    add_roof_reed_arish(b, 1.05, 0.15, h - 0.02, w=2.35, d=2.55, h_post=1.48, slope=0.14)
    add_roof_jar(b, -1.75, -1.30, h + 0.03)

    obj = b.to_object('house_d')
    bake_wear_and_ao(obj, base_z=0.0, eaves_z=h, ao_strength=0.40, splash_strength=0.18)
    return export_asset('house_d', obj, lod0_budget=4500, lod1_budget=1500, max_lt22=LIMIT_A)


def build_house_b():
    """Large warm mud-ochre farmhouse with outside mudbrick stair (+X), whitewashed dado,
    palm-log lintel, forest-green shutters, and sculpted Egyptian pigeon tower on the roof."""
    bb = V4Builder(seed=102)
    w, d, h = 6.0, 5.2, 3.3
    fy = -d * 0.5
    ox = -0.50   # shift so body + 0.92m outside stair are centered within LIMIT_B
    openings = [
        {'face': 'front', 's': -1.18, 'z0': 0.04, 'z1': 1.96, 'w': 0.98, 'depth': 0.18, 'back': True},
        {'face': 'front', 's': 1.18,  'z0': 1.56, 'z1': 2.32, 'w': 0.66, 'depth': 0.16, 'back': True},
        {'face': 'left',  's': 0.50,  'z0': 1.56, 'z1': 2.32, 'w': 0.64, 'depth': 0.16, 'back': True},
        {'face': 'back',  's': -0.80, 'z0': 1.62, 'z1': 2.32, 'w': 0.62, 'depth': 0.16, 'back': True},
    ]
    bb.wall_shell(w, d, h, mat='ph_plaster', color='#D8A069', taper=0.976, wobble=0.026,
                  openings=openings, reveal_mat='ph_plaster', reveal_color='#C88D56')
    add_plinth(bb, w, d, h=0.36, mat='ph_mudbrick', color='#B47545', pad=0.14)
    add_parapet(bb, w, d, h, mat='ph_plaster', color='#E2B27D', ph=0.44, horns=True, horn_col='#E6BA89', taper=0.976)
    add_beams(bb, w, d, h, 7, bb.rnd, out=0.28, taper=0.976, color='#825834')

    # Whitewashed lower dado & geometric sawtooth trim on front wall
    bb.box((1.10, 0.04, 0.62), (-2.30, fy - 0.008, 0.62), 'ph_plaster', '#F3E9D4', bevel=0.01, spread=0.015)
    bb.box((3.20, 0.04, 0.62), (1.15, fy - 0.008, 0.62), 'ph_plaster', '#F3E9D4', bevel=0.01, spread=0.015)
    add_folk_band(bb, -0.35, 2.70, fy, 0.94, 0.15, mat='ph_plaster', color='#F3E9D4', wall_h=h, taper=0.976)

    # Exposed mudbrick patches (weathered earth farmhouse character!)
    add_mudbrick_patch(bb, -2.96, -0.85, 1.35, 0.05, 1.10, 0.72, '#B67646')
    add_mudbrick_patch(bb, 0.15, fy - 0.006, 2.25, 0.92, 0.04, 0.62, '#BA7B4A')
    add_mudbrick_patch(bb, 1.30, d * 0.5 + 0.005, 1.25, 1.25, 0.05, 0.75, '#B27242')

    add_recessed_door(bb, -1.18, fy, w=0.98, h=1.94, leaf_col='#488F68',
                      frame_mat='ph_plaster', frame_col='#F4EAD5', arch=False,
                      taper=0.976, wall_h=h, lintel_wood=True)
    add_recessed_window(bb, 1.18, fy, 1.94, w=0.66, h=0.76, face='front',
                        shutter_col='#488F68', open_=True, taper=0.976, wall_h=h)
    add_recessed_window(bb, 0.50, -w * 0.5, 1.94, w=0.64, h=0.76, face='left',
                        shutter_col='#488F68', taper=0.976, wall_h=h)
    add_recessed_window(bb, -0.80, d * 0.5, 1.97, w=0.62, h=0.70, face='back',
                        shutter_col='#488F68', open_=False, taper=0.976, wall_h=h)

    # Outside mudbrick staircase climbing the +X wall (fits strictly inside x <= 3.54 after ox=-0.50)
    steps = 10
    sw = 0.90
    run_y = d - 0.80
    step_d = run_y / steps
    for i in range(steps):
        t = (i + 1) / steps
        sz = h * t
        sy = -d * 0.5 + 0.40 + i * step_d + step_d * 0.5
        bb.box((sw, step_d + 0.02, sz), (w * 0.5 + sw * 0.5 - 0.04, sy, sz * 0.5),
               'ph_mudbrick' if i % 3 == 0 else 'ph_plaster', '#CE955F',
               bevel=0.0, wobble=0.012, spread=0.03)
        bb.box((sw - 0.06, step_d, 0.05), (w * 0.5 + sw * 0.5 - 0.04, sy, sz + 0.015),
               'ph_floor', '#C8A373', bevel=0.0, spread=0.02)
    # Low side guard wall at top landing + timber newel post
    bb.box((0.15, 1.15, 0.52), (w * 0.5 + sw - 0.11, d * 0.5 - 0.72, h + 0.24),
           'ph_plaster', '#E2B27D', bevel=0.05, seg=1)
    bb.cyl(0.055, 0.048, 0.92, (w * 0.5 + sw - 0.12, -d * 0.5 + 0.45, 0.78),
           'ph_wood', '#7E5634', verts=6, grain='z')

    # Sculpted pigeon tower + roof firewood
    add_pigeon_tower(bb, -1.45, 0.85, h - 0.02, bb.rnd, s=0.95)
    add_firewood(bb, 1.35, 1.40, h + 0.02, 2.5, 3, bb.rnd, along='y')

    b = V4Builder(seed=102)
    b.merge_from(bb, Matrix.Translation((ox, 0.0, 0.0)))
    obj = b.to_object('house_b')
    bake_wear_and_ao(obj, base_z=0.0, eaves_z=h, ao_strength=0.40, splash_strength=0.18)
    return export_asset('house_b', obj, lod0_budget=4500, lod1_budget=1500, max_lt22=LIMIT_B)


def build_house_e():
    """House B footprint variant: grand stepped two-level Nile merchant house with sandstone base
    courses, warm honey plaster, recessed cedar double-door, cantilevered reed sun-canopy (>2.4 m),
    upper clerestory belvedere with Egyptian windcatcher (malqaf) and side dome."""
    b = V4Builder(seed=105)
    w, d, h = 6.7, 5.1, 3.10
    fy = -d * 0.5
    openings = [
        {'face': 'front', 's': 0.0,   'z0': 0.04, 'z1': 2.04, 'w': 1.24, 'depth': 0.22, 'back': True},
        {'face': 'front', 's': -2.05, 'z0': 1.46, 'z1': 2.22, 'w': 0.68, 'depth': 0.16, 'back': True},
        {'face': 'front', 's': 2.05,  'z0': 1.46, 'z1': 2.22, 'w': 0.68, 'depth': 0.16, 'back': True},
        {'face': 'left',  's': -0.25, 'z0': 1.46, 'z1': 2.22, 'w': 0.66, 'depth': 0.16, 'back': True},
        {'face': 'right', 's': 0.25,  'z0': 1.46, 'z1': 2.22, 'w': 0.66, 'depth': 0.16, 'back': True},
    ]
    b.wall_shell(w, d, h, mat='ph_plaster', color='#ECD5AA', taper=0.978, wobble=0.022,
                 openings=openings, reveal_mat='ph_stone', reveal_color='#D6BE96')
    # Dressed sandstone lower base skirt
    add_plinth(b, w, d, h=0.46, mat='ph_stone', color='#CEB58E', pad=0.14)
    add_parapet(b, w, d, h, mat='ph_plaster', color='#F0DEC0', ph=0.38, horns=True, horn_col='#F3E4C9', taper=0.978)
    add_beams(b, w, d, h, 7, b.rnd, out=0.26, taper=0.978, color='#7D5432')

    # Wide cedar double-door in recessed sandstone arch + flanking blue folk bands
    add_recessed_door(b, 0.0, fy, w=1.24, h=2.02, depth=0.22, leaf_col='#845834',
                      frame_mat='ph_stone', frame_col='#D8C19B', arch=True, taper=0.978, wall_h=h)
    add_recessed_window(b, -2.05, fy, 1.84, w=0.68, h=0.76, face='front',
                        shutter_col='#357A9E', open_=True, taper=0.978, wall_h=h)
    add_recessed_window(b, 2.05, fy, 1.84, w=0.68, h=0.76, face='front',
                        shutter_col='#357A9E', open_=True, taper=0.978, wall_h=h)
    add_recessed_window(b, -0.25, -w * 0.5, 1.84, w=0.66, h=0.76, face='left',
                        shutter_col='#357A9E', taper=0.978, wall_h=h)
    add_recessed_window(b, 0.25, w * 0.5, 1.84, w=0.66, h=0.76, face='right',
                        shutter_col='#357A9E', taper=0.978, wall_h=h)

    add_folk_band(b, -w * 0.5 + 0.28, w * 0.5 - 0.28, fy, 2.66, 0.14, mat='ph_blue', color='#3B7CA3', wall_h=h, taper=0.978)

    # Cantilevered timber & reed sun-canopy over the main door (every vertex strictly above z = 2.25 m!)
    for sx in (-0.95, 0.95):
        b.box((0.10, 0.88, 0.10), (sx, fy - 0.34, 2.66), 'ph_wood', '#7E5532', grain='y')
        b.box((0.08, 0.56, 0.08), (sx, fy - 0.18, 2.46), 'ph_wood', '#754E2E', rot=(0.55, 0, 0), grain='y')
    b.box((2.35, 0.92, 0.08), (0.0, fy - 0.36, 2.74), 'ph_cloth', '#C8AA6A',
          bevel=0.02, seg=1, rot=(-0.16, 0, 0), wobble=0.012, spread=0.03)

    # Stepped second-story rear belvedere room (z = 3.05 .. 4.95 m) + malqaf windcatcher + side dome
    uw, ud, uh = 3.6, 2.5, 1.95
    ub = V4Builder(seed=106)
    u_ops = [
        {'face': 'front', 's': -0.85, 'z0': 0.55, 'z1': 1.25, 'w': 0.56, 'depth': 0.15, 'back': True},
        {'face': 'front', 's': 0.85,  'z0': 0.55, 'z1': 1.25, 'w': 0.56, 'depth': 0.15, 'back': True},
    ]
    ub.wall_shell(uw, ud, uh, mat='ph_plaster', color='#F1E0BE', taper=0.975, wobble=0.018,
                  openings=u_ops, reveal_mat='ph_plaster', reveal_color='#E2CBA3')
    add_parapet(ub, uw, ud, uh, mat='ph_plaster', color='#F3E5C8', ph=0.30, horns=False, taper=0.975)
    for sx in (-0.85, 0.85):
        add_recessed_window(ub, sx, -ud * 0.5, 0.90, w=0.56, h=0.70, face='front',
                            shutter_col='#357A9E', open_=False, taper=0.975, wall_h=uh)
    # Egyptian wooden windcatcher scoop (malqaf) rising on top of the belvedere
    ub.box((1.55, 0.95, 0.88), (0.0, 0.25, uh + 0.42), 'ph_plaster', '#EAD4AA', bevel=0.05, seg=1)
    ub.box((1.72, 1.25, 0.10), (0.0, 0.12, uh + 0.98), 'ph_wood', '#865B36',
           bevel=0.02, rot=(0.28, 0, 0), grain='x')
    ub.box((1.25, 0.08, 0.58), (0.0, -0.22, uh + 0.48), 'ph_dark', '#291E18', smooth=False, spread=0.0)
    b.merge_from(ub, Matrix.Translation((-1.05, 0.72, h - 0.04)))

    # Companion mudbrick dome on the right side of the roof
    add_dome(b, 1.95, 0.65, h - 0.02, r=0.96, drum_h=0.30, mat='ph_plaster', color='#F2E4C8')

    obj = b.to_object('house_e')
    bake_wear_and_ao(obj, base_z=0.0, eaves_z=h, ao_strength=0.40, splash_strength=0.16)
    return export_asset('house_e', obj, lod0_budget=4500, lod1_budget=1500, max_lt22=LIMIT_B)


def build_house_c():
    """Small lime-washed domed cottage (4.6 x 4.4 x 2.9 m), golden ochre folk frieze,
    recessed green arched door & shutters, graceful bulbous dome with finial."""
    b = V4Builder(seed=103)
    w, d, h = 4.6, 4.4, 2.90
    fy = -d * 0.5
    openings = [
        {'face': 'front', 's': 0.78,  'z0': 0.04, 'z1': 1.90, 'w': 0.92, 'depth': 0.17, 'back': True},
        {'face': 'front', 's': -1.18, 'z0': 1.38, 'z1': 2.10, 'w': 0.60, 'depth': 0.15, 'back': True},
        {'face': 'right', 's': -0.20, 'z0': 1.38, 'z1': 2.10, 'w': 0.60, 'depth': 0.15, 'back': True},
        {'face': 'left',  's': 0.25,  'z0': 1.38, 'z1': 2.10, 'w': 0.58, 'depth': 0.15, 'back': True},
    ]
    b.wall_shell(w, d, h, mat='ph_plaster', color='#F0DFBE', taper=0.978, wobble=0.022,
                 openings=openings, reveal_mat='ph_plaster', reveal_color='#E2CCA4')
    add_plinth(b, w, d, h=0.32, mat='ph_mudbrick', color='#BE8250', pad=0.14)
    add_parapet(b, w, d, h, mat='ph_plaster', color='#F4E8CF', ph=0.36, horns=True, horn_col='#F4E8CF', taper=0.978)
    add_beams(b, w, d, h, 5, b.rnd, out=0.26, taper=0.978)

    add_recessed_door(b, 0.78, fy, w=0.92, h=1.88, leaf_col='#4B946A',
                      frame_mat='ph_plaster', frame_col='#4C8E60', arch=True, taper=0.978, wall_h=h)
    add_recessed_window(b, -1.18, fy, 1.74, w=0.60, h=0.72, face='front',
                        shutter_col='#4B946A', open_=True, taper=0.978, wall_h=h)
    add_recessed_window(b, -0.20, w * 0.5, 1.74, w=0.60, h=0.72, face='right',
                        shutter_col='#4B946A', taper=0.978, wall_h=h)
    add_recessed_window(b, 0.25, -w * 0.5, 1.74, w=0.58, h=0.72, face='left',
                        shutter_col='#4B946A', taper=0.978, wall_h=h)

    # Golden ochre folk geometric band under parapet
    add_folk_band(b, -w * 0.5 + 0.24, w * 0.5 - 0.24, fy, 2.38, 0.14, mat='ph_plaster', color='#D69634', wall_h=h, taper=0.978)
    add_mudbrick_patch(b, -2.26, -0.95, 0.66, 0.04, 0.72, 0.46, '#BA7B4A')
    add_mudbrick_patch(b, 0.55, d * 0.5 + 0.005, 0.72, 0.85, 0.04, 0.48, '#BE804E')

    add_dome(b, 0.55, 0.45, h - 0.02, r=1.02, drum_h=0.34, mat='ph_plaster', color='#F5EBD4')
    add_firewood(b, -1.25, -0.55, h + 0.02, 2.0, 3, b.rnd, along='y')

    obj = b.to_object('house_c')
    bake_wear_and_ao(obj, base_z=0.0, eaves_z=h, ao_strength=0.40, splash_strength=0.16)
    return export_asset('house_c', obj, lod0_budget=4500, lod1_budget=1500, max_lt22=LIMIT_C)


def build_house_f():
    """House C footprint variant: bare sun-baked terracotta mudbrick cottage with a Nubian
    parabolic barrel-vault roof (قبو), cream plaster repair patches, weathered blue door surround,
    and wooden reed rooftop shade."""
    b = V4Builder(seed=106)
    w, d, h = 4.55, 4.35, 2.75
    fy = -d * 0.5
    openings = [
        {'face': 'front', 's': -0.68, 'z0': 0.04, 'z1': 1.88, 'w': 0.90, 'depth': 0.17, 'back': True},
        {'face': 'front', 's': 1.08,  'z0': 1.32, 'z1': 2.02, 'w': 0.58, 'depth': 0.15, 'back': True},
        {'face': 'left',  's': -0.25, 'z0': 1.32, 'z1': 2.02, 'w': 0.58, 'depth': 0.15, 'back': True},
        {'face': 'right', 's': 0.30,  'z0': 1.32, 'z1': 2.02, 'w': 0.58, 'depth': 0.15, 'back': True},
    ]
    b.wall_shell(w, d, h, mat='ph_mudbrick', color='#C68856', taper=0.974, wobble=0.026,
                 openings=openings, reveal_mat='ph_mudbrick', reveal_color='#B27446')
    add_plinth(b, w, d, h=0.34, mat='ph_stone', color='#C2A880', pad=0.14)
    add_parapet(b, w, d, h, mat='ph_mudbrick', color='#CE9462', ph=0.30, horns=False, taper=0.974)
    add_beams(b, w, d, h, 4, b.rnd, out=0.24, taper=0.974, color='#7A5130')

    # Hand-plastered cream limewash repair patches contrasting against raw mudbrick (clear of windows!)
    b.box((1.05, 0.04, 0.72), (1.10, fy - 0.008, 0.76), 'ph_plaster', '#EFE0C2', bevel=0.025, wobble=0.015, spread=0.015)
    b.box((0.04, 1.35, 0.80), (w * 0.5 + 0.005, -0.95, 1.55), 'ph_plaster', '#ECD9B6', bevel=0.025, wobble=0.015, spread=0.015)

    add_recessed_door(b, -0.68, fy, w=0.90, h=1.86, leaf_col='#8B5E38',
                      frame_mat='ph_blue', frame_col='#4989B0', arch=True, taper=0.974, wall_h=h)
    add_recessed_window(b, 1.08, fy, 1.67, w=0.58, h=0.70, face='front',
                        shutter_col='#8B5E38', open_=True, taper=0.974, wall_h=h)
    add_recessed_window(b, -0.25, -w * 0.5, 1.67, w=0.58, h=0.70, face='left',
                        shutter_col='#4989B0', taper=0.974, wall_h=h)
    add_recessed_window(b, 0.30, w * 0.5, 1.67, w=0.58, h=0.70, face='right',
                        shutter_col='#4989B0', taper=0.974, wall_h=h)

    # Nubian parabolic barrel-vault roof running front-to-back on the left half of the roof
    vw, vd, vh = 2.15, 3.65, 1.25
    vx = -0.78
    segs_a, segs_y = 12, 6
    vbm = lib.bmesh.new()
    rings = []
    for iy in range(segs_y + 1):
        yy = -vd * 0.5 + vd * (iy / segs_y)
        ring = []
        for ia in range(segs_a + 1):
            t = ia / segs_a
            ang = t * math.pi
            xx = vx + math.cos(ang) * (vw * 0.5)
            zz = h + math.sin(ang) ** 0.85 * vh
            ring.append(vbm.verts.new((xx, yy, zz)))
        rings.append(ring)
    for iy in range(segs_y):
        for ia in range(segs_a):
            vbm.faces.new((rings[iy][ia], rings[iy + 1][ia], rings[iy + 1][ia + 1], rings[iy][ia + 1]))
    # End gable walls closing the barrel vault cleanly
    for iy, rev in ((0, False), (segs_y, True)):
        r = rings[iy]
        mid_b = vbm.verts.new((vx, -vd * 0.5 if iy == 0 else vd * 0.5, h))
        for ia in range(segs_a):
            tri = (mid_b, r[ia + 1], r[ia]) if not rev else (mid_b, r[ia], r[ia + 1])
            vbm.faces.new(tri)
    b.put(vbm, 'ph_mudbrick', '#CE9260', None, smooth=True, wobble=0.015, freq=1.0, spread=0.02)

    # Light timber & reed roof shade beside the vault
    add_roof_reed_arish(b, 1.10, 0.15, h - 0.02, w=1.75, d=2.65, h_post=1.22, slope=0.12)
    add_roof_jar(b, 1.25, -1.35, h + 0.02, scale=0.92)

    obj = b.to_object('house_f')
    bake_wear_and_ao(obj, base_z=0.0, eaves_z=h, ao_strength=0.42, splash_strength=0.18)
    return export_asset('house_f', obj, lod0_budget=4500, lod1_budget=1500, max_lt22=LIMIT_C)


# ---------------------------------------------------------------------------
# Mastaba & Garden Wall
# ---------------------------------------------------------------------------

def build_mastaba():
    """Grandma's مصطبة in house_a model space: x 0.05..2.55, y -3.00..-2.40, seat top z = 0.45."""
    b = V4Builder(seed=161)
    x0, L, D, H, wy = 0.05, 2.50, 0.60, 0.45, -2.40
    cx, cy = x0 + L * 0.5, wy - D * 0.5

    # Hand-plastered mudbrick bench body (sunk to z = -0.20) + clay floor seating slab
    b.box((L - 0.02, D, H + 0.14), (cx, cy + 0.01, (H - 0.24) * 0.5),
          'ph_plaster', '#EAD6B2', bevel=0.06, seg=1, wobble=0.010, freq=1.8, spread=0.015)
    b.box((L + 0.04, D + 0.04, 0.07), (cx, cy - 0.01, H - 0.035),
          'ph_floor', '#DEC59B', bevel=0.025, seg=1, wobble=0.005, spread=0.015)
    # Weathered Egyptian blue base trim strip + tiny exposed mudbrick corner patch
    b.box((L - 0.10, 0.028, 0.11), (cx, wy - D - 0.006, 0.11),
          'ph_blue', '#3A79A8', bevel=0.0, spread=0.02)
    add_mudbrick_patch(b, x0 + L - 0.16, wy - D - 0.006, 0.25, 0.26, 0.028, 0.16, '#BF8250')

    # Draped woven Egyptian kilim rug (solid thickness, zero z-fighting)
    kx, kw = cx - 0.18, 1.32
    b.box((kw, D - 0.06, 0.018), (kx, cy + 0.01, H + 0.009),
          'ph_cloth', '#B84B32', bevel=0.0, wobble=0.003, spread=0.02)
    b.box((kw, 0.020, 0.18), (kx, wy - D - 0.012, H - 0.075),
          'ph_cloth', '#B84B32', bevel=0.0, wobble=0.003, spread=0.02)
    # Woven ochre & indigo stripe bands (proud by 4 mm, solid)
    for i, scol in enumerate(('#DBA03B', '#386C94', '#DBA03B')):
        sx = kx - kw * 0.5 + 0.20 + i * (kw - 0.40) * 0.5
        b.box((0.085, D - 0.05, 0.010), (sx, cy + 0.01, H + 0.019), 'ph_cloth', scol, smooth=False, spread=0.015)
        b.box((0.085, 0.010, 0.175), (sx, wy - D - 0.021, H - 0.075), 'ph_cloth', scol, smooth=False, spread=0.015)

    # Plump woven cushion at her side + rolled bolster against the house wall
    b.box((0.38, 0.32, 0.11), (kx + 0.86, wy - 0.19, H + 0.058),
          'ph_cloth', '#EDE0C2', bevel=0.04, seg=1, wobble=0.008, freq=3.5, spread=0.02)
    b.box((0.39, 0.06, 0.025), (kx + 0.86, wy - 0.19, H + 0.112),
          'ph_cloth', '#386C94', bevel=0.0, spread=0.015)
    b.cyl(0.092, 0.092, 0.56, (kx - 0.22, wy - 0.11, H + 0.095),
          'ph_cloth', '#D69A3C', rot=(0, math.pi * 0.5, 0), verts=9, bevel=0.025, spread=0.02)

    obj = b.to_object('mastaba')
    bake_wear_and_ao(obj, base_z=0.0, ao_strength=0.38, splash_strength=0.14)
    return export_asset('mastaba', obj, lod0_budget=1000, lod1_budget=450)


def build_garden_wall():
    """4 m village garden wall along X: sandstone rubble base, hand-plastered upper, rounded coping."""
    b = V4Builder(seed=167)
    # Sandstone masonry base course
    b.box((4.0, 0.44, 0.50), (0, 0, 0.21), 'ph_stone', '#BFA680',
          bevel=0.05, seg=1, wobble=0.020, freq=1.4, spread=0.03)
    # Sculpted projecting corner/base sandstone quoins along both sides
    for sy in (-1, 1):
        for i in range(6):
            sx = -1.68 + i * 0.67 + b.rnd.uniform(-0.04, 0.04)
            b.box((0.46, 0.08, 0.24), (sx, sy * 0.21, 0.22 + b.rnd.uniform(-0.03, 0.03)),
                  'ph_stone', '#D2BA94', bevel=0.03, seg=1, wobble=0.010,
                  uv_off=(i * 0.43, sy * 0.3), spread=0.05)
    # Upper hand-plastered wall + exposed mudbrick patch + rounded coping cap
    b.box((4.0, 0.36, 0.48), (0, 0, 0.68), 'ph_plaster', '#EFE0C2',
          bevel=0.045, seg=1, wobble=0.016, spread=0.02)
    b.cyl(0.19, 0.19, 4.02, (0, 0, 0.94), 'ph_plaster', '#F3E7CE',
          rot=(0, math.pi * 0.5, 0), verts=10, scale=(0.62, 1.05, 1.0), wobble=0.010, grain=None)
    add_mudbrick_patch(b, -0.75, -0.18, 0.66, 0.72, 0.035, 0.30, '#BE804E')
    # Subtle weathered Egyptian blue band on both sides
    for sy in (-1, 1):
        b.box((3.88, 0.024, 0.075), (0, sy * 0.184, 0.56), 'ph_blue', '#3D7DA8', smooth=False, spread=0.02)

    obj = b.to_object('garden_wall')
    bake_wear_and_ao(obj, base_z=0.0, eaves_z=0.95, ao_strength=0.38, splash_strength=0.18)
    return export_asset('garden_wall', obj, lod0_budget=1200, lod1_budget=500)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    sheet_only = '--sheet' in args

    if not sheet_only:
        builders = [
            build_house_a, build_house_b, build_house_c,
            build_house_d, build_house_e, build_house_f,
            build_mastaba, build_garden_wall,
        ]
        for fn in builders:
            reset_scene()
            fn()

    if sheet_only or '--with-sheet' in args:
        lib.render_contact_sheet(ALL_M3_MODELS, lib.PREVIEWS / 'M3_houses_sheet.png')


if __name__ == '__main__':
    main()
