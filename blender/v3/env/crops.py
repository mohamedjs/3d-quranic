"""Environment v3 crops, grass, reeds, papyrus, wildflowers & field bunds (`crops.py`).

Rebuilds all 11 ground-cover and farmland assets with painterly Ghibli silhouettes,
grounded root-to-tip vertex color gradients, soft upward-biased normals (blending roots
cleanly into terrain with zero harsh seams), and 2.5x–4.5x fewer triangles than v2 so
both Lite (<=150k tris) and High (<=1.3M tris) look dramatically denser and softer:
  - crop_berseem, crop_maize, crop_wheat, crop_cotton, crop_cabbage
  - grass_a, grass_b, grass_c
  - reeds, papyrus, wildflowers, field_bund

Material contract (matched automatically by `src/game/world/envAssets.js`):
  - `foliage_crop_card` : foliage atlas + alphaTest + DoubleSide + wind + backlit SSS
  - `foliage_grass`     : vertex-color blades + DoubleSide + WIND.grass + backlit SSS + root blend
  - `foliage_crop_vc`   : vertex-color crop blades/leaves + DoubleSide + crop wind + backlit SSS
  - `foliage_solid`     : vertex-color opaque soil/bunds/cobs/cotton bolls + FrontSide
"""
import math
import random

import bmesh
import bpy
from mathutils import Vector

from foliage import FoliagePart, _jitter_srgb, _tint_srgb
from lib import bake_vertex_ao, make_material
from textures import FOLIAGE_UV


def _lerp3(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def _add_blade(part, base, yaw, length, width, bend, col_root, col_tip, segs=2, lean=0.0):
    """Gracefully tapered curved blade ribbon with root-to-tip vertex gradient (2*segs - 1 tris)."""
    d = Vector((math.cos(yaw), math.sin(yaw), 0.0))
    side = Vector((-d.y, d.x, 0.0))
    b = Vector(base)
    pts = []
    for i in range(segs + 1):
        t = i / segs
        p = b + d * (bend * length * t * t + lean * length * t) + Vector((0, 0, length * t * (1.0 - 0.24 * bend * t)))
        pts.append((t, p))
    rings = []
    for i, (t, p) in enumerate(pts):
        if i == segs:
            v = part.bm.verts.new(p)
            rings.append((t, [v]))
        else:
            w = width * (1.0 - (t ** 1.35)) * 0.5
            rings.append((t, [part.bm.verts.new(p - side * w), part.bm.verts.new(p + side * w)]))
    for i in range(segs):
        t0, r0 = rings[i]
        t1, r1 = rings[i + 1]
        c0 = (*_lerp3(col_root, col_tip, t0), 1.0)
        c1 = (*_lerp3(col_root, col_tip, t1), 1.0)
        try:
            if len(r1) == 1:
                f = part.bm.faces.new((r0[0], r0[1], r1[0]))
                cols = (c0, c0, c1)
            else:
                f = part.bm.faces.new((r0[0], r0[1], r1[1], r1[0]))
                cols = (c0, c0, c1, c1)
            f.smooth = True
            for lp, col in zip(f.loops, cols):
                lp[part.uvl].uv = (0.31, 0.25)
                lp[part.coll] = col
        except ValueError:
            pass
    return pts[-1][1]


def _soft_up_normals(obj, up_bias=0.78):
    """Blend vertex normals smoothly upward so grass & low crops catch cohesive lawn light."""
    me = obj.data
    up = Vector((0, 0, 1))
    norms = [up] * len(me.loops)
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index]
            n = Vector((v.normal.x, v.normal.y, abs(v.normal.z))).normalized()
            norms[li] = n.lerp(up, up_bias).normalized()
    me.normals_split_custom_set(norms)


# ---- 1. Grass Tufts (`grass_a`, `grass_b`, `grass_c`) --------------------------------------
def build_grass(variant=0, col=None):
    """Lush curved grass tuft (~24–33 tris) with grounded meadow-root to sunlit-tip gradient."""
    name = f"grass_{'abc'[variant]}"
    rnd = random.Random(401 + variant * 19)
    p = FoliagePart(401 + variant * 19)
    # Match terrain meadow / verge base at the root so grass melts cleanly into the earth!
    specs = [
        (8,  (0.30, 0.46), '#4B7426', '#A8C952', '#649234'),   # grass_a: lush meadow tuft
        (11, (0.46, 0.72), '#3D6822', '#9EC44C', '#56862C'),   # grass_b: tall riverside lush tuft
        (8,  (0.32, 0.52), '#7A6B34', '#DFCA7A', '#9A9046'),   # grass_c: warm sun-kissed dry tuft
    ]
    n_blades, (l0, l1), c_root_h, c_tip_h, c_mid_h = specs[variant]
    for i in range(n_blades):
        a = (i / n_blades) * math.tau + rnd.uniform(-0.35, 0.35)
        r = rnd.uniform(0.01, 0.12)
        c_root = _jitter_srgb(c_root_h, rnd, 0.05)
        c_tip = _jitter_srgb(c_tip_h if i % 3 else c_mid_h, rnd, 0.07)
        _add_blade(p, (math.cos(a) * r, math.sin(a) * r, -0.01), a + rnd.uniform(-0.3, 0.3),
                   rnd.uniform(l0, l1), rnd.uniform(0.068, 0.105), rnd.uniform(0.38, 0.88),
                   c_root, c_tip, segs=2)
    obj = p.to_object(name, 'foliage_grass', col, ao_strength=0.0)
    _soft_up_normals(obj, up_bias=0.82)
    return [obj]


# ---- 2. Crops (`crop_berseem`, `crop_wheat`, `crop_maize`, `crop_cotton`, `crop_cabbage`) --
def build_berseem(col=None):
    """Egyptian clover (`برسيم`): 4 crossed feathery clover-cluster cards (~48 tris vs v2 340 tris!)."""
    rnd = random.Random(411)
    p = FoliagePart(411)
    for i in range(3):
        a = i * math.tau / 3.0 + rnd.uniform(-0.2, 0.2)
        cx, cy = math.cos(a) * 0.06, math.sin(a) * 0.06
        n = Vector((math.cos(a), math.sin(a), 0.22)).normalized()
        p.add_curved_card((cx, cy, 0.22), n, 0.58, 0.48, FOLIAGE_UV['crop_clover'],
                          cup=0.16, srgb=_tint_srgb(0.96, 1.04, 0.90, rnd, 0.07))
    # One tilted top crown card so bird's-eye & high angles see thick lush clover carpet
    p.add_curved_card((0, 0, 0.26), (0.12, 0.08, 0.98), 0.62, 0.62, FOLIAGE_UV['crop_clover'],
                      cup=0.18, srgb=(1.02, 1.06, 0.94), roll=0.6)
    obj = p.to_object('crop_berseem', 'foliage_crop_card', col, ao_strength=0.12, ao_min=0.78,
                      spherical_center=(0, 0, 0.12), spherical_blend=0.85)
    return [obj]


def build_wheat(col=None):
    """Golden swaying wheat sheaf (~78 tris vs v2 242 tris) with arched golden ears & green base."""
    rnd = random.Random(412)
    p = FoliagePart(412)
    for i in range(11):
        a = (i / 11.0) * math.tau + rnd.uniform(-0.28, 0.28)
        r = rnd.uniform(0.01, 0.14)
        base = (math.cos(a) * r, math.sin(a) * r, -0.01)
        c_root = _jitter_srgb('#7E8C38', rnd, 0.06)
        c_tip = _jitter_srgb('#E8C458' if i % 4 else '#CBB452', rnd, 0.07)
        top = _add_blade(p, base, a + rnd.uniform(-0.25, 0.25), rnd.uniform(0.84, 1.06),
                         0.044, rnd.uniform(0.14, 0.30), c_root, c_tip, segs=2, lean=0.07)
        # Plump harvest honey-gold grain head nodding gracefully at the stalk tip
        ear_col = _jitter_srgb('#E4B742', rnd, 0.06)
        p.add_cone(0.022, 0.008, 0.16, top + Vector((0, 0, 0.04)), ear_col,
                   rot=(rnd.uniform(-0.26, 0.26), rnd.uniform(-0.26, 0.26), 0), verts=4)
    for i in range(4):
        a = i * 1.57 + 0.3
        _add_blade(p, (0, 0, 0), a, 0.44, 0.056, 0.85, _jitter_srgb('#6E8832', rnd, 0.06),
                   _jitter_srgb('#B8B24E', rnd, 0.06), segs=2)
    obj = p.to_object('crop_wheat', 'foliage_crop_vc', col, ao_strength=0.10, ao_min=0.78)
    _soft_up_normals(obj, up_bias=0.62)
    return [obj]


def build_maize(col=None):
    """Tall Egyptian maize (`ذرة`) (~94 tris vs v2 161 tris): stalk, sweeping arched leaves, cob & tassel."""
    rnd = random.Random(413)
    p = FoliagePart(413)
    H = 1.95
    # Tapered green stalk
    p.add_cone(0.036, 0.014, H, (0, 0, H * 0.5), _jitter_srgb('#669634', rnd, 0.05), verts=5, cap=False)
    # 7 sweeping broad curved maize leaves alternating up the stalk
    for i in range(7):
        z = 0.28 + i * (H * 0.72 / 7.0)
        yaw = i * 2.45 + rnd.uniform(-0.2, 0.2)
        L = 0.82 - i * 0.05
        _add_blade(p, (0, 0, z), yaw, L, 0.12, 0.92,
                   _jitter_srgb('#4F862B', rnd, 0.06), _jitter_srgb('#92B84A', rnd, 0.06), segs=2, lean=0.45)
    # 3 golden tassel plumes crowning the stalk
    for i in range(3):
        _add_blade(p, (0, 0, H - 0.02), i * 2.1, 0.34, 0.042, 0.65,
                   _jitter_srgb('#CFA84A', rnd, 0.05), _jitter_srgb('#F2D478', rnd, 0.05), segs=2)
    # Sunlit golden corn cob nestled mid-stalk
    p.add_cone(0.052, 0.024, 0.26, (0.065, 0.0, H * 0.54), _jitter_srgb('#EBC958', rnd, 0.05),
               rot=(0, 0.38, 0), verts=5)
    obj = p.to_object('crop_maize', 'foliage_crop_vc', col, ao_strength=0.14, ao_min=0.72)
    _soft_up_normals(obj, up_bias=0.52)
    return [obj]


def build_cotton(col=None):
    """Egyptian cotton (`قطن`) (~92 tris vs v2 492 tris!): leafy cards + 5 crisp white bolls (1 draw!)."""
    rnd = random.Random(414)
    p = FoliagePart(414)
    # 3 crossed lush broad-leaf cards + top crown card forming the cotton bush
    for i in range(3):
        a = i * math.tau / 3.0 + 0.2
        n = Vector((math.cos(a), math.sin(a), 0.28)).normalized()
        p.add_curved_card((0, 0, 0.32), n, 0.64, 0.54, FOLIAGE_UV['sycamore_leaf'],
                          cup=0.18, srgb=_tint_srgb(0.86, 0.96, 0.78, rnd, 0.07))
    p.add_curved_card((0, 0, 0.42), (0, 0, 1), 0.56, 0.56, FOLIAGE_UV['sycamore_leaf'],
                      cup=0.18, srgb=(0.92, 1.0, 0.84), roll=0.8)
    # Stem + 5 snowy white cotton bolls mapped to pure-white swatch -> single draw call per chunk!
    p.add_cone(0.022, 0.015, 0.28, (0, 0, 0.14), _jitter_srgb('#7A5B3C', rnd, 0.05), verts=4)
    for i in range(5):
        a = i * math.tau / 5.0 + rnd.uniform(-0.2, 0.2)
        rr = rnd.uniform(0.15, 0.24)
        p.add_icosphere((math.cos(a) * rr, math.sin(a) * rr, 0.38 + rnd.uniform(0.0, 0.14)),
                        (0.062, 0.062, 0.052), _jitter_srgb('#FCF8EE', rnd, 0.02), sub=0)
    return [p.to_object('crop_cotton', 'foliage_crop_card', col, ao_strength=0.12, ao_min=0.76,
                        spherical_center=(0, 0, 0.25), spherical_blend=0.82)]


def build_cabbage(col=None):
    """Egyptian leafy cabbage (`كرنب`) (~76 tris): pale heart cradled in rounded cupped rosette leaves."""
    rnd = random.Random(415)
    p = FoliagePart(415)
    # Pale chartreuse inner cabbage head
    p.add_icosphere((0, 0, 0.145), (0.145, 0.145, 0.125), _jitter_srgb('#B4D87A', rnd, 0.05), sub=1, wobble=0.012)
    # 7 broad rounded cupped outer cabbage leaves (wide oval contour, NOT sharp spikes!)
    for i in range(7):
        a = i * math.tau / 7.0 + rnd.uniform(-0.12, 0.12)
        d = Vector((math.cos(a), math.sin(a), 0.0))
        side = Vector((-d.y, d.x, 0.0))
        c_in = _jitter_srgb('#468232', rnd, 0.05)
        c_out = _jitter_srgb('#7EB44E', rnd, 0.06)
        # 3-row cupped petal fan: narrow stem base -> wide rounded mid -> gently curved broad rim
        r_steps = [(0.08, 0.04, 0.07), (0.18, 0.11, 0.155), (0.28, 0.14, 0.13), (0.33, 0.10, 0.065)]
        rows = []
        for rad, z, hw in r_steps:
            # Bowl-like upward curl at the edges of each leaf
            center_p = d * rad + Vector((0, 0, z))
            rows.append([
                center_p - side * hw + Vector((0, 0, 0.025)),
                center_p,
                center_p + side * hw + Vector((0, 0, 0.025)),
            ])
        p.add_quad_grid(rows, (0.980, 0.010, 0.990, 0.020), srgb=c_out, smooth=True,
                        v_ao=lambda t: 0.72 + 0.28 * t)
    obj = p.to_object('crop_cabbage', 'foliage_crop_vc', col, ao_strength=0.16, ao_min=0.72)
    _soft_up_normals(obj, up_bias=0.72)
    return [obj]


# ---- 3. Reeds, Papyrus, Wildflowers & Field Bund -------------------------------------------
def build_reeds(col=None):
    """Swaying riverbank reeds & velvety brown cattails (~56 tris vs v2 93 tris)."""
    rnd = random.Random(421)
    p = FoliagePart(421)
    for i in range(9):
        a = (i / 9.0) * math.tau + rnd.uniform(-0.3, 0.3)
        r = rnd.uniform(0.02, 0.18)
        top = _add_blade(p, (math.cos(a) * r, math.sin(a) * r, -0.04), a, rnd.uniform(1.35, 1.95),
                         0.062, rnd.uniform(0.08, 0.32),
                         _jitter_srgb('#4E6F2B', rnd, 0.06), _jitter_srgb('#98AE4C', rnd, 0.06), segs=2)
        if i % 3 == 0:
            p.add_cone(0.032, 0.028, 0.24, top + Vector((0, 0, -0.18)), _jitter_srgb('#7D4E2B', rnd, 0.07), verts=5)
    obj = p.to_object('reeds', 'foliage_crop_vc', col, ao_strength=0.12, ao_min=0.74)
    _soft_up_normals(obj, up_bias=0.55)
    return [obj]


def build_papyrus(col=None):
    """Iconic Egyptian Nile papyrus (`بردي`): 5 tall triangular stalks + starburst umbel cards (1 draw!)."""
    rnd = random.Random(422)
    p = FoliagePart(422)
    for i in range(5):
        a = i * math.tau / 5.0 + rnd.uniform(-0.25, 0.25)
        rr = rnd.uniform(0.04, 0.18)
        h = rnd.uniform(1.55, 2.25)
        lean = rnd.uniform(0.10, 0.26)
        bx, by = math.cos(a) * rr, math.sin(a) * rr
        tx, ty = bx + math.cos(a) * lean, by + math.sin(a) * lean
        p.add_cone(0.024, 0.012, h, ((bx + tx) * 0.5, (by + ty) * 0.5, h * 0.5 - 0.05),
                   _jitter_srgb('#588C34', rnd, 0.06),
                   rot=(-math.sin(a) * (lean / h), math.cos(a) * (lean / h), a), verts=3, cap=False)
        top = Vector((tx, ty, h - 0.02))
        sz = rnd.uniform(0.46, 0.62)
        p.add_cross_card(top, sz * 0.5, sz, FOLIAGE_UV['papyrus'],
                         srgb=_tint_srgb(0.98, 1.04, 0.90, rnd, 0.06), yaw=a, cup=0.14)
    return [p.to_object('papyrus', 'foliage_crop_card', col, ao_strength=0.10, ao_min=0.80,
                        spherical_center=(0, 0, 1.45), spherical_blend=0.70)]


def build_wildflowers(col=None):
    """Sunlit wildflower cluster built from 3 crossed botanical wildflower sprig cards (~48 tris vs v2 213!)."""
    rnd = random.Random(423)
    p = FoliagePart(423)
    for i in range(3):
        a = i * math.tau / 3.0 + rnd.uniform(-0.2, 0.2)
        n = Vector((math.cos(a), math.sin(a), 0.18)).normalized()
        p.add_curved_card((math.cos(a) * 0.05, math.sin(a) * 0.05, 0.24), n, 0.52, 0.48,
                          FOLIAGE_UV['wildflower'], cup=0.14, srgb=_tint_srgb(1.0, 1.0, 0.96, rnd, 0.05))
    obj = p.to_object('wildflowers', 'foliage_crop_card', col, ao_strength=0.08, ao_min=0.82,
                      spherical_center=(0, 0, 0.15), spherical_blend=0.78)
    return [obj]


def build_field_bund(col=None):
    """4 m sculpted Nile earth bund separating farm plots (~88 tris vs v2 214 tris) with baked AO & crest grass."""
    rnd = random.Random(424)
    p = FoliagePart(424)
    prof = [(-0.56, -0.02), (-0.34, 0.02), (-0.14, 0.16), (0.0, 0.20), (0.14, 0.16), (0.34, 0.02), (0.56, -0.02)]
    nx = 6
    rows = []
    for ix in range(nx + 1):
        x = -2.0 + 4.0 * ix / nx
        row = []
        for y, z in prof:
            dz = 0.02 * math.sin(x * 2.8 + y * 4.5) if abs(y) < 0.45 else 0.0
            row.append(Vector((x, y, z + dz)))
        rows.append(row)
    p.add_quad_grid(rows, FOLIAGE_UV['bark_wood'], srgb=_jitter_srgb('#8F6C49', rnd, 0.04), smooth=True)
    # Sparse tufts along the earth ridge
    for i in range(4):
        x = -1.5 + i * 1.0 + rnd.uniform(-0.15, 0.15)
        for k in range(2):
            _add_blade(p, (x, rnd.uniform(-0.06, 0.06), 0.17), rnd.uniform(0, math.tau), 0.24, 0.055, 0.65,
                       _jitter_srgb('#5B7D32', rnd, 0.06), _jitter_srgb('#98B44A', rnd, 0.06), segs=2)
    return [p.to_object('field_bund', 'foliage_solid', col, ao_strength=0.28, ao_min=0.64)]


CROP_BUILDERS = {
    'crop_berseem': build_berseem,
    'crop_maize': build_maize,
    'crop_wheat': build_wheat,
    'crop_cotton': build_cotton,
    'crop_cabbage': build_cabbage,
    'grass_a': lambda col=None: build_grass(0, col),
    'grass_b': lambda col=None: build_grass(1, col),
    'grass_c': lambda col=None: build_grass(2, col),
    'reeds': build_reeds,
    'papyrus': build_papyrus,
    'wildflowers': build_wildflowers,
    'field_bund': build_field_bund,
}
