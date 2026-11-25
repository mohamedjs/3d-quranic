"""Environment v3 hero foliage builders (`foliage.py`).

Rebuilds every tree, shrub, vine, and water plant in painterly-naturalistic Ghibli style
using the shared WebP foliage atlas (`textures.FOLIAGE_UV`), baked vertex AO, and
transferred spherical normals on leaf/flower canopies (zero blobby spheres, zero ink hulls):
  - palm_a, palm_b, palm_c, palm_d : 4 distinct Egyptian date palms (diamond-bark trunks,
    gracefully arched V-folded feathery alpha-cutout frond cards, dry skirt fronds, amber/ruby dates)
  - sycamore, sycamore_a, sycamore_b : gnarled buttressed Egyptian `جميز` shade trees with
    layered broad leaf-cluster cards + transferred spherical normals
  - acacia : flat-topped desert umbrella acacia (`Acacia tortilis`) with airy feathery cards
  - bougainvillea, bougainvillea_bush, bougainvillea_vine : twisting woody stems + cascading
    magenta/rose bougainvillea flower-vine cards (replacing v2's pink spheres on green spheres)
  - bush_a, bush_b : lush Nile olive-emerald & warm sage-gold leaf-cluster shrubs
  - lotus_pad : floating notched emerald oasis lotus pad + sculpted cream-pink blossom
  - pot_plant : terracotta clay pot with folk band + lush layered foliage & red blooms

Material contract (matched automatically by `src/game/world/envAssets.js`):
  - `foliage_frond` : foliage atlas + alphaTest + DoubleSide + WIND.frond + backlit SSS
  - `foliage_leaf`  : foliage atlas + alphaTest + DoubleSide + WIND.leaf  + backlit SSS
  - `foliage_shrub` : foliage atlas + alphaTest + DoubleSide + WIND.shrub + backlit SSS
  - `foliage_bark`  : foliage atlas (opaque bark strip) + FrontSide + matte PBR/toon
  - `foliage_solid` : vertex-color solid accents (dates, pot, lotus petals), FrontSide
"""
import math
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector, noise

from lib import bake_vertex_ao, make_material, srgb_to_linear, transfer_spherical_normals
from textures import FOLIAGE_UV


def _jitter_srgb(hex_str, rnd, spread=0.07):
    """Jittered sRGB (0..1) tuple for bmesh BYTE_COLOR (stored as sRGB, exported linear)."""
    h = hex_str.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    k = 1.0 + rnd.uniform(-spread, spread)
    w = rnd.uniform(-spread * 0.3, spread * 0.3)
    return (
        max(0.0, min(1.0, r * k + w)),
        max(0.0, min(1.0, g * k)),
        max(0.0, min(1.0, b * k - w * 0.5)),
    )


def _tint_srgb(r, g, b, rnd, spread=0.06):
    k = 1.0 + rnd.uniform(-spread, spread)
    return (max(0.0, min(1.0, r * k)), max(0.0, min(1.0, g * k)), max(0.0, min(1.0, b * k)))


def _wob(p, amp, freq=2.0, seed=0):
    if not amp:
        return p
    return p + noise.noise_vector(p * freq + Vector((seed * 5.7, seed * 2.9, seed * 1.3))) * amp


class FoliagePart:
    """Bmesh accumulator with UVMap + sRGB vertex-color tint/AO layer for one material bucket."""

    def __init__(self, seed=0):
        self.bm = bmesh.new()
        self.uvl = self.bm.loops.layers.uv.new('UVMap')
        self.coll = self.bm.loops.layers.color.new('Color')
        self.seed = seed
        self.rnd = random.Random(seed)

    def add_quad_grid(self, rows, uv_rect, srgb=(1.0, 1.0, 1.0), smooth=True, v_ao=None):
        """Add a grid of vertices `rows[iy][ix]` mapped linearly across `uv_rect=(u0,v0,u1,v1)`."""
        u0, v0, u1, v1 = uv_rect
        ny = len(rows) - 1
        nx = len(rows[0]) - 1
        vgrid = [[self.bm.verts.new(p) for p in row] for row in rows]
        for iy in range(ny):
            tv0 = iy / ny
            tv1 = (iy + 1) / ny
            vv0 = v0 + (v1 - v0) * tv0
            vv1 = v0 + (v1 - v0) * tv1
            ao0 = v_ao(tv0) if v_ao else 1.0
            ao1 = v_ao(tv1) if v_ao else 1.0
            c0 = (srgb[0] * ao0, srgb[1] * ao0, srgb[2] * ao0, 1.0)
            c1 = (srgb[0] * ao1, srgb[1] * ao1, srgb[2] * ao1, 1.0)
            for ix in range(nx):
                tu0 = ix / nx
                tu1 = (ix + 1) / nx
                uu0 = u0 + (u1 - u0) * tu0
                uu1 = u0 + (u1 - u0) * tu1
                try:
                    f = self.bm.faces.new((vgrid[iy][ix], vgrid[iy][ix + 1], vgrid[iy + 1][ix + 1], vgrid[iy + 1][ix]))
                    f.smooth = smooth
                    uvs = ((uu0, vv0), (uu1, vv0), (uu1, vv1), (uu0, vv1))
                    cols = (c0, c0, c1, c1)
                    for lp, uv, col in zip(f.loops, uvs, cols):
                        lp[self.uvl].uv = uv
                        lp[self.coll] = col
                except ValueError:
                    pass

    def add_curved_card(self, center, normal_dir, size_w, size_h, uv_rect,
                        cup=0.18, srgb=(1.0, 1.0, 1.0), roll=0.0):
        """Add a gently cupped 2x2 alpha-cutout botanical leaf-cluster card (8 tris, lush volume!)."""
        n = Vector(normal_dir).normalized()
        up_ref = Vector((0, 0, 1)) if abs(n.z) < 0.92 else Vector((1, 0, 0))
        right = n.cross(up_ref).normalized()
        up = right.cross(n).normalized()
        if roll:
            cr, sr = math.cos(roll), math.sin(roll)
            right, up = right * cr + up * sr, -right * sr + up * cr
        c = Vector(center)
        rows = []
        for iy in range(3):
            fy = iy - 1.0   # -1, 0, +1
            row = []
            for ix in range(3):
                fx = ix - 1.0
                # Gentle dome cupping outward along `n` so card never looks paper-flat edge-on
                dz = cup * (size_w * 0.5) * (1.0 - 0.5 * (fx * fx + fy * fy))
                p = c + right * (fx * size_w * 0.5) + up * (fy * size_h * 0.5) + n * dz
                row.append(p)
            rows.append(row)
        self.add_quad_grid(rows, uv_rect, srgb=srgb, smooth=True)

    def add_cross_card(self, center, radius, height, uv_rect, srgb=(1.0, 1.0, 1.0), yaw=0.0, cup=0.14):
        """Two gently arched intersecting vertical-ish botanical cards (16 tris) — reads full from 360°."""
        for k in range(2):
            a = yaw + k * math.pi * 0.5
            n = Vector((math.cos(a), math.sin(a), 0.18)).normalized()
            self.add_curved_card(center, n, radius * 2.0, height, uv_rect, cup=cup, srgb=srgb, roll=0.0)

    def add_tube(self, pts, radii, uv_rect, sides=7, v_repeat=1.0, srgb=(1.0, 1.0, 1.0), wobble=0.0, cap_top=True):
        """Tapered curved UV-mapped trunk/branch tube with seamless V tiling along the bark strip."""
        u0, v0, u1, v1 = uv_rect
        rings = []
        cum_len = [0.0]
        for i in range(1, len(pts)):
            cum_len.append(cum_len[-1] + (Vector(pts[i]) - Vector(pts[i - 1])).length)
        total_len = max(cum_len[-1], 1e-4)
        prev_right = Vector((1, 0, 0))
        for i, (p, rad) in enumerate(zip(pts, radii)):
            p = Vector(p)
            if i == 0:
                tang = (Vector(pts[1]) - p).normalized()
            elif i == len(pts) - 1:
                tang = (p - Vector(pts[i - 1])).normalized()
            else:
                tang = (Vector(pts[i + 1]) - Vector(pts[i - 1])).normalized()
            right = prev_right - tang * prev_right.dot(tang)
            if right.length < 1e-4:
                right = Vector((0, 1, 0)).cross(tang)
            right.normalize()
            prev_right = right
            fwd = tang.cross(right).normalized()
            ring = []
            for k in range(sides + 1):   # +1 seam vertex so UVs wrap cleanly inside the atlas tile!
                a = (k / sides) * math.tau
                pos = p + (right * math.cos(a) + fwd * math.sin(a)) * rad
                ring.append(self.bm.verts.new(_wob(pos, wobble, 2.2, self.seed + i)))
            rings.append((cum_len[i] / total_len, ring))
        for i in range(len(rings) - 1):
            t0, r0 = rings[i]
            t1, r1 = rings[i + 1]
            # Clamp V cleanly inside tile with repeat folded via ping-pong so atlas neighbors never bleed!
            tv0 = abs(((t0 * v_repeat) % 2.0) - 1.0)
            tv1 = abs(((t1 * v_repeat) % 2.0) - 1.0)
            vv0 = v0 + (v1 - v0) * (0.04 + 0.92 * tv0)
            vv1 = v0 + (v1 - v0) * (0.04 + 0.92 * tv1)
            # Subtle root-to-crown brightness gradient
            ao0 = 0.78 + 0.22 * min(1.0, t0 * 2.5)
            ao1 = 0.78 + 0.22 * min(1.0, t1 * 2.5)
            c0 = (srgb[0] * ao0, srgb[1] * ao0, srgb[2] * ao0, 1.0)
            c1 = (srgb[0] * ao1, srgb[1] * ao1, srgb[2] * ao1, 1.0)
            for k in range(sides):
                uu0 = u0 + (u1 - u0) * (0.04 + 0.92 * (k / sides))
                uu1 = u0 + (u1 - u0) * (0.04 + 0.92 * ((k + 1) / sides))
                try:
                    f = self.bm.faces.new((r0[k], r0[k + 1], r1[k + 1], r1[k]))
                    f.smooth = True
                    for lp, uv, col in zip(f.loops, ((uu0, vv0), (uu1, vv0), (uu1, vv1), (uu0, vv1)), (c0, c0, c1, c1)):
                        lp[self.uvl].uv = uv
                        lp[self.coll] = col
                except ValueError:
                    pass
        if cap_top and rings:
            top_ring = rings[-1][1][:-1]
            try:
                f = self.bm.faces.new(top_ring)
                f.smooth = True
                uc, vc = (u0 + u1) * 0.5, (v0 + v1) * 0.5
                for lp in f.loops:
                    lp[self.uvl].uv = (uc, vc)
                    lp[self.coll] = (srgb[0] * 0.72, srgb[1] * 0.72, srgb[2] * 0.72, 1.0)
            except ValueError:
                pass

    def add_icosphere(self, center, scale, srgb, sub=1, wobble=0.0):
        """Solid vertex-colored accent mapped to the pure-white opaque atlas swatch (0.985, 0.015)."""
        src = bmesh.new()
        bmesh.ops.create_icosphere(src, subdivisions=sub, radius=1.0)
        m = Matrix.LocRotScale(Vector(center), Euler((0, 0, 0)), Vector(scale))
        src.verts.index_update()
        vm = [self.bm.verts.new(_wob(m @ v.co, wobble, 6.0, self.seed)) for v in src.verts]
        rgba = (srgb[0], srgb[1], srgb[2], 1.0)
        for f in src.faces:
            try:
                nf = self.bm.faces.new([vm[v.index] for v in f.verts])
                nf.smooth = True
                for lp in nf.loops:
                    lp[self.uvl].uv = (0.985, 0.015)
                    lp[self.coll] = rgba
            except ValueError:
                pass
        src.free()

    def add_cone(self, r1, r2, depth, loc, srgb, rot=(0, 0, 0), verts=8, cap=True):
        src = bmesh.new()
        bmesh.ops.create_cone(src, cap_ends=cap, cap_tris=False, segments=verts, radius1=r1, radius2=r2, depth=depth)
        m = Matrix.LocRotScale(Vector(loc), Euler(rot), Vector((1, 1, 1)))
        src.verts.index_update()
        vm = [self.bm.verts.new(m @ v.co) for v in src.verts]
        rgba = (srgb[0], srgb[1], srgb[2], 1.0)
        for f in src.faces:
            try:
                nf = self.bm.faces.new([vm[v.index] for v in f.verts])
                nf.smooth = True
                for lp in nf.loops:
                    lp[self.uvl].uv = (0.985, 0.015)
                    lp[self.coll] = rgba
            except ValueError:
                pass
        src.free()

    def to_object(self, name, mat_name, col=None, ao_strength=0.22, ao_min=0.66,
                  spherical_center=None, spherical_blend=0.0):
        me = bpy.data.meshes.new(name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        if me.color_attributes:
            me.color_attributes.active_color_index = 0
            me.color_attributes.render_color_index = 0
        mat = make_material(mat_name, base_color=(0.75, 0.78, 0.65), roughness=0.82, use_vcol=True)
        me.materials.append(mat)
        obj = bpy.data.objects.new(name, me)
        (col or bpy.context.scene.collection).objects.link(obj)
        if ao_strength > 0:
            bake_vertex_ao(obj, strength=ao_strength, min_val=ao_min)
        if spherical_blend > 0:
            transfer_spherical_normals(obj, center=spherical_center, blend=spherical_blend)
        return obj


# ---- 1. Date Palms (`palm_a`, `palm_b`, `palm_c`, `palm_d`) --------------------------------
def _add_palm_frond_card(part, top, yaw, pitch, length, droop, width, uv_rect, srgb, segs=5):
    """Gracefully arched V-folded feathery date palm frond card (20 tris at segs=5!)."""
    d = Vector((math.cos(yaw), math.sin(yaw), 0.0))
    side = Vector((-d.y, d.x, 0.0))
    pts = []
    for i in range(segs + 1):
        t = i / segs
        horiz = length * t * math.cos(pitch)
        vert = length * t * math.sin(pitch) - droop * length * (t ** 1.85)
        pts.append(Vector(top) + d * horiz + Vector((0, 0, vert)))
    rows = []
    for i, p in enumerate(pts):
        t = i / segs
        tang = (pts[min(i + 1, segs)] - pts[max(i - 1, 0)]).normalized()
        nrm = side.cross(tang).normalized()
        # Slight V-fold along spine + gentle upward arch so fronds catch golden sunlight from every angle
        fold = nrm * (width * 0.24 * math.sin(t * math.pi))
        rows.append([
            p - side * width - fold * 0.35,
            p + fold * 0.55,
            p + side * width - fold * 0.35,
        ])
    # Darken slightly at the crown heart (t=0) and brighten toward sunlit arching tips (t=1)
    part.add_quad_grid(rows, uv_rect, srgb=srgb, smooth=True, v_ao=lambda t: 0.78 + 0.22 * (t ** 0.7))


def _build_palm_variant(name, h, lean, lean_y, n_fronds, droop, seed, dry_n=4, bunches=4, col=None, lod1=False):
    rnd = random.Random(seed)
    bark = FoliagePart(seed)
    fronds = FoliagePart(seed + 100)
    dates = FoliagePart(seed + 200)

    # Gently curved, fibrous diamond-bark trunk with subtle root flare
    n_seg = 6 if lod1 else 10
    sides = 6 if lod1 else 8
    pts, rads = [], []
    for i in range(n_seg + 1):
        t = i / n_seg
        curve = t * t
        px = lean * curve + 0.14 * math.sin(t * math.pi) * (1 if seed % 2 else -1)
        py = lean_y * curve
        pz = -0.18 + (h + 0.18) * t
        r = 0.29 * (1.0 - t) ** 1.35 + 0.17 * t + (0.11 if i == 0 else 0.0)
        pts.append((px, py, pz))
        rads.append(r)
    bark.add_tube(pts, rads, FOLIAGE_UV['bark_palm'], sides=sides, v_repeat=max(2.0, h / 1.9),
                  srgb=_tint_srgb(0.98, 0.94, 0.88, rnd, 0.05), wobble=0.012)
    top = Vector(pts[-1])
    # Fibrous crown heart cap
    bark.add_icosphere(top + Vector((0, 0, -0.05)), (0.28, 0.28, 0.26), (0.62, 0.48, 0.32), sub=1)

    # Layered feathery arching palm fronds (outer drooping ring + mid lush ring + young upright plume)
    nf = max(8, int(n_fronds * 0.58)) if lod1 else n_fronds
    segs = 3 if lod1 else 5
    for i in range(nf):
        young = i >= nf - 3
        lower = i < nf // 3
        yaw = i * 2.39996 + rnd.uniform(-0.14, 0.14)
        pitch = rnd.uniform(0.92, 1.18) if young else (rnd.uniform(0.18, 0.42) if lower else rnd.uniform(0.45, 0.78))
        L = rnd.uniform(2.7, 3.5) * (0.68 if young else (1.05 if lower else 0.95))
        d_cur = (0.22 if young else droop) * rnd.uniform(0.88, 1.14)
        w = rnd.uniform(0.62, 0.76) * (0.78 if young else 1.0)
        tint = _tint_srgb(1.06, 1.08, 0.94, rnd, 0.06) if young else (
            _tint_srgb(0.88, 0.92, 0.84, rnd, 0.06) if lower else _tint_srgb(0.98, 1.02, 0.94, rnd, 0.06)
        )
        _add_palm_frond_card(fronds, top + Vector((0, 0, 0.06 if young else -0.04)),
                             yaw, pitch, L, d_cur, w, FOLIAGE_UV['palm_frond'], tint, segs=segs)

    # Dry golden skirt fronds hanging naturally below the green crown
    dn = max(2, dry_n // 2) if lod1 else dry_n
    for i in range(dn):
        yaw = i * (math.tau / dn) + 0.5 + rnd.uniform(-0.22, 0.22)
        _add_palm_frond_card(fronds, top + Vector((0, 0, -0.22)),
                             yaw, rnd.uniform(-1.05, -0.78), rnd.uniform(1.65, 2.15), 0.10, 0.48,
                             FOLIAGE_UV['palm_dry'], _tint_srgb(1.0, 0.96, 0.88, rnd, 0.07), segs=3)

    # Hanging amber-gold and ruby Egyptian date bunches merged onto trunk material (2 draws/palm!)
    if not lod1:
        for i in range(bunches):
            a = i * math.tau / bunches + rnd.uniform(-0.25, 0.25)
            stalk_p = top + Vector((math.cos(a) * 0.26, math.sin(a) * 0.26, -0.22))
            bunch_p = top + Vector((math.cos(a) * 0.44, math.sin(a) * 0.44, -0.58 - rnd.uniform(0.0, 0.14)))
            bark.add_cone(0.025, 0.02, 0.46, stalk_p, _jitter_srgb('#D69B38', rnd, 0.06),
                          rot=(math.sin(a) * 0.7, -math.cos(a) * 0.7, 0), verts=5)
            col_d = _jitter_srgb('#C94E1E' if i % 2 == 0 else '#E2A238', rnd, 0.08)
            bark.add_icosphere(bunch_p, (0.18, 0.18, 0.28), col_d, sub=1, wobble=0.022)

    suf = '_LOD1' if lod1 else ''
    return [
        bark.to_object(f'{name}_trunk{suf}', 'foliage_bark', col, ao_strength=0.22, ao_min=0.65),
        fronds.to_object(f'{name}_fronds{suf}', 'foliage_frond', col, ao_strength=0.14, ao_min=0.76,
                         spherical_center=top + Vector((0, 0, 0.35)), spherical_blend=0.55),
    ]


PALM_SPECS = {
    'palm_a': (7.2,  0.85,  0.20, 16, 0.56, 301, 4, 4),   # classic graceful Nile village palm
    'palm_b': (9.4,  1.65, -0.35, 18, 0.62, 302, 5, 5),   # tall sweeping oasis landmark palm
    'palm_c': (5.2,  0.40,  0.25, 14, 0.46, 303, 3, 3),   # sturdy young canal-side palm
    'palm_d': (8.2, -1.25,  0.65, 16, 0.58, 304, 4, 4),   # wind-sculpted riverside palm
}


def build_palm(name, col=None):
    spec = PALM_SPECS[name]
    return (
        _build_palm_variant(name, *spec, col=col, lod1=False)
        + _build_palm_variant(name, *spec, col=col, lod1=True)
    )


# ---- 2. Sycamores (`sycamore`, `sycamore_a`, `sycamore_b`) ---------------------------------
def _build_sycamore_variant(name, seed, canopy_r=3.6, trunk_h=2.1, spread_z=4.7, col=None, lod1=False):
    """Egyptian `جميز` sycamore shade tree: buttressed gnarled trunk + limbs + layered Ghibli
    painterly leaf-cluster cards with transferred spherical normals (soft cloud lighting, ZERO spheres!)."""
    rnd = random.Random(seed)
    bark = FoliagePart(seed)
    leaves = FoliagePart(seed + 50)

    sides_t = 6 if lod1 else 8
    sides_b = 5 if lod1 else 6
    # Gnarled wide trunk with buttressed roots gripping the Nile loam
    bark.add_tube([(0, 0, -0.22), (0.06, -0.04, trunk_h * 0.45), (0.10, 0.05, trunk_h)],
                  [0.54, 0.41, 0.34], FOLIAGE_UV['bark_wood'], sides=sides_t, v_repeat=1.4,
                  srgb=_tint_srgb(0.95, 0.92, 0.88, rnd, 0.05), wobble=0.035)
    if not lod1:
        for k in range(5):
            a = k * math.tau / 5 + rnd.uniform(-0.18, 0.18)
            bark.add_tube([(0.03, 0.02, 0.62), (math.cos(a) * 0.58, math.sin(a) * 0.58, 0.12),
                           (math.cos(a) * 1.05, math.sin(a) * 1.05, -0.18)],
                          [0.21, 0.14, 0.06], FOLIAGE_UV['bark_wood'], sides=5, v_repeat=0.9,
                          srgb=(0.82, 0.78, 0.72), wobble=0.02)

    # 5 organically spreading limbs lifting the broad shade crown
    n_limbs = 4 if lod1 else 5
    tips = []
    for i in range(n_limbs):
        a = i * math.tau / n_limbs + 0.35 + rnd.uniform(-0.22, 0.22)
        reach = canopy_r * rnd.uniform(0.52, 0.66)
        tip = Vector((math.cos(a) * reach, math.sin(a) * reach, spread_z - 0.55 + rnd.uniform(-0.35, 0.45)))
        mid = Vector((math.cos(a) * reach * 0.48, math.sin(a) * reach * 0.48, trunk_h + (tip.z - trunk_h) * 0.55))
        bark.add_tube([(0.10, 0.05, trunk_h - 0.1), mid, tip], [0.27, 0.18, 0.10],
                      FOLIAGE_UV['bark_wood'], sides=sides_b, v_repeat=1.2,
                      srgb=_tint_srgb(0.94, 0.90, 0.85, rnd, 0.05), wobble=0.025)
        tips.append(tip)

    # Layered painterly leaf-cluster cards arranged in a lush, billowing Ghibli dome
    canopy_center = Vector((0.0, 0.0, spread_z))
    n_cards = 24 if lod1 else 48
    for i in range(n_cards):
        # Fibonacci-sphere dome distribution filling both outer silhouette and upper-mid crown
        t = (i + 0.5) / n_cards
        phi = i * 2.39996 + rnd.uniform(-0.2, 0.2)
        elev = -0.32 + 1.32 * t
        rad = canopy_r * (0.42 + 0.56 * math.sqrt(max(0.06, 1.0 - (elev * 0.72) ** 2))) * rnd.uniform(0.86, 1.08)
        cx = math.cos(phi) * rad
        cy = math.sin(phi) * rad
        cz = spread_z + elev * (canopy_r * 0.48)
        pos = Vector((cx, cy, cz))
        out_dir = (pos - canopy_center + Vector((0, 0, 0.42))).normalized()
        card_sz = canopy_r * rnd.uniform(0.60, 0.78) * (1.22 if lod1 else 1.0)
        # Warm sunlit crown tint at top, deeper cool-olive shade underneath
        h_frac = max(0.0, min(1.0, (elev + 0.32) / 1.32))
        tint = _tint_srgb(0.82 + 0.24 * h_frac, 0.86 + 0.18 * h_frac, 0.78 + 0.14 * h_frac, rnd, 0.06)
        leaves.add_curved_card(pos, out_dir, card_sz, card_sz * 0.94, FOLIAGE_UV['sycamore_leaf'],
                               cup=0.24, srgb=tint, roll=rnd.uniform(0, math.tau))
        # Orthogonal cross-facing cards on outer lobes so canopy never shows vertical edge slots
        if not lod1 and i % 3 == 0:
            side_dir = out_dir.cross(Vector((0, 0, 1)))
            if side_dir.length > 0.1:
                leaves.add_curved_card(pos - out_dir * 0.22, side_dir.normalized(), card_sz * 0.92, card_sz * 0.86,
                                       FOLIAGE_UV['sycamore_leaf'], cup=0.20, srgb=tint, roll=rnd.uniform(0, math.tau))

    suf = '_LOD1' if lod1 else ''
    return [
        bark.to_object(f'{name}_trunk{suf}', 'foliage_bark', col, ao_strength=0.24, ao_min=0.62),
        leaves.to_object(f'{name}_leaves{suf}', 'foliage_leaf', col, ao_strength=0.16, ao_min=0.72,
                         spherical_center=canopy_center - Vector((0, 0, 0.5)), spherical_blend=0.88),
    ]


def build_sycamore(name='sycamore_a', col=None):
    specs = {
        'sycamore':   (321, 3.55, 2.1, 4.65),
        'sycamore_a': (321, 3.55, 2.1, 4.65),
        'sycamore_b': (322, 3.95, 2.35, 5.05),
    }
    seed, cr, th, sz = specs[name]
    return (
        _build_sycamore_variant(name, seed, cr, th, sz, col=col, lod1=False)
        + _build_sycamore_variant(name, seed, cr, th, sz, col=col, lod1=True)
    )


# ---- 3. Egyptian Desert Umbrella Acacia (`acacia`) -----------------------------------------
def _build_acacia_variant(seed=331, col=None, lod1=False):
    """Iconic sun-sculpted Egyptian desert acacia (`سنط`): twisted multi-stem trunk fanning
    wide into a graceful flat-topped umbrella canopy of feathery sage-olive pinnate cards."""
    rnd = random.Random(seed)
    bark = FoliagePart(seed)
    leaves = FoliagePart(seed + 40)

    sides_t = 5 if lod1 else 7
    # Leaning gnarled main trunk splitting low (~1.3 m) into sweeping V-shaped umbrella limbs
    bark.add_tube([(0, 0, -0.2), (0.15, -0.05, 0.75), (0.28, 0.04, 1.55)],
                  [0.34, 0.26, 0.21], FOLIAGE_UV['bark_wood'], sides=sides_t, v_repeat=1.2,
                  srgb=(0.86, 0.80, 0.72), wobble=0.03)
    n_limbs = 4 if lod1 else 5
    limb_tips = []
    for i in range(n_limbs):
        a = i * math.tau / n_limbs + 0.25 + rnd.uniform(-0.22, 0.22)
        reach = rnd.uniform(2.5, 3.3)
        h_tip = rnd.uniform(3.55, 4.15)
        mid = Vector((0.28 + math.cos(a) * reach * 0.52, 0.04 + math.sin(a) * reach * 0.52, 2.65))
        tip = Vector((0.28 + math.cos(a) * reach, 0.04 + math.sin(a) * reach, h_tip))
        bark.add_tube([(0.26, 0.04, 1.48), mid, tip], [0.16, 0.11, 0.06],
                      FOLIAGE_UV['bark_wood'], sides=5, v_repeat=1.3, srgb=(0.84, 0.78, 0.70), wobble=0.025)
        limb_tips.append(tip)

    # Wide flat-topped layered umbrella tiers of feathery acacia cards (horizontal-domed!)
    canopy_center = Vector((0.28, 0.04, 3.45))
    n_cards = 14 if lod1 else 28
    for i in range(n_cards):
        t = (i + 0.5) / n_cards
        a = i * 2.39996 + rnd.uniform(-0.2, 0.2)
        rr = math.sqrt(t) * 3.75 * rnd.uniform(0.88, 1.06)
        # Flat-topped umbrella profile: gently arched top, crisp underside
        cz = 4.28 - 0.55 * (rr / 3.9) ** 2 + rnd.uniform(-0.22, 0.20)
        pos = Vector((0.28 + math.cos(a) * rr, 0.04 + math.sin(a) * rr, cz))
        # Mostly upward-facing domed plates so umbrella silhouette reads razor-crisp against sky
        nrm = Vector((math.cos(a) * 0.38 * (rr / 3.9), math.sin(a) * 0.38 * (rr / 3.9), 0.92)).normalized()
        sz = rnd.uniform(1.85, 2.45) * (1.18 if lod1 else 1.0)
        tint = _tint_srgb(0.96, 0.98, 0.88, rnd, 0.07)
        leaves.add_curved_card(pos, nrm, sz, sz * 0.85, FOLIAGE_UV['acacia_leaf'],
                               cup=0.16, srgb=tint, roll=rnd.uniform(0, math.tau))
        # Vertical edge-fill fringe on outer skirt so eye-level silhouettes look feathery & full
        if not lod1 and rr > 1.8 and i % 2 == 0:
            edge_n = Vector((math.cos(a), math.sin(a), 0.35)).normalized()
            leaves.add_curved_card(pos - Vector((0, 0, 0.18)), edge_n, sz * 0.82, sz * 0.58,
                                   FOLIAGE_UV['acacia_leaf'], cup=0.14, srgb=(0.86, 0.90, 0.80), roll=rnd.uniform(-0.3, 0.3))

    suf = '_LOD1' if lod1 else ''
    return [
        bark.to_object(f'acacia_trunk{suf}', 'foliage_bark', col, ao_strength=0.22, ao_min=0.64),
        leaves.to_object(f'acacia_leaves{suf}', 'foliage_leaf', col, ao_strength=0.14, ao_min=0.74,
                         spherical_center=canopy_center, spherical_blend=0.88),
    ]


def build_acacia(col=None):
    return _build_acacia_variant(331, col=col, lod1=False) + _build_acacia_variant(331, col=col, lod1=True)


# ---- 4. Bougainvillea (`bougainvillea`, `bougainvillea_bush`, `bougainvillea_vine`) --------
def _build_bougainvillea(name, vine=False, seed=341, col=None, lod1=False):
    """Cascading magenta/rose bougainvillea built from woody stems + painterly flower-vine cards."""
    rnd = random.Random(seed)
    bark = FoliagePart(seed)
    cards = FoliagePart(seed + 30)

    if vine:
        # Wall-draping flowering cascade (y ≈ 0 plane, arching forward +Y and spilling down from z=2.3 -> 0.3)
        bark.add_tube([(0, 0.06, -0.05), (-0.18, 0.14, 1.05), (0.12, 0.16, 2.25)],
                      [0.055, 0.038, 0.022], FOLIAGE_UV['bark_wood'], sides=5, v_repeat=1.0, srgb=(0.72, 0.62, 0.54))
        n_c = 7 if lod1 else 14
        for i in range(n_c):
            t = i / max(1, n_c - 1)
            px = rnd.uniform(-0.75, 0.75) * (0.55 + 0.45 * math.sin(t * math.pi))
            pz = 0.45 + 1.95 * t + rnd.uniform(-0.14, 0.14)
            py = 0.18 + 0.24 * math.sin(t * math.pi) + rnd.uniform(-0.08, 0.10)
            nrm = Vector((px * 0.45, 0.85, 0.25)).normalized()
            sz = rnd.uniform(0.78, 1.08) * (1.18 if lod1 else 1.0)
            cards.add_curved_card((px, py, pz), nrm, sz, sz * 0.92, FOLIAGE_UV['bougainvillea'],
                                  cup=0.22, srgb=_tint_srgb(1.0, 0.98, 0.98, rnd, 0.06), roll=rnd.uniform(0, math.tau))
        c_center = Vector((0.0, 0.05, 1.35))
    else:
        # Lush overflowing garden bougainvillea bush (matching v2 ~1.6 m height & footprint)
        for k in range(3):
            a = k * math.tau / 3 + 0.3
            bark.add_tube([(0, 0, -0.08), (math.cos(a) * 0.22, math.sin(a) * 0.22, 0.55),
                           (math.cos(a) * 0.42, math.sin(a) * 0.42, 1.08)],
                          [0.055, 0.036, 0.02], FOLIAGE_UV['bark_wood'], sides=5, v_repeat=0.9, srgb=(0.74, 0.64, 0.54))
        n_c = 8 if lod1 else 16
        c_center = Vector((0.0, 0.0, 0.88))
        for i in range(n_c):
            t = (i + 0.5) / n_c
            a = i * 2.39996 + rnd.uniform(-0.25, 0.25)
            elev = -0.35 + 1.30 * t
            rr = (0.32 + 0.44 * math.sqrt(max(0.05, 1.0 - elev * elev * 0.55))) * rnd.uniform(0.85, 1.08)
            pos = Vector((math.cos(a) * rr, math.sin(a) * rr, 0.92 + elev * 0.55))
            nrm = (pos - c_center + Vector((0, 0, 0.15))).normalized()
            sz = rnd.uniform(0.76, 1.02) * (1.16 if lod1 else 1.0)
            cards.add_curved_card(pos, nrm, sz, sz * 0.95, FOLIAGE_UV['bougainvillea'],
                                  cup=0.24, srgb=_tint_srgb(1.0, 0.98, 0.98, rnd, 0.06), roll=rnd.uniform(0, math.tau))

    suf = '_LOD1' if lod1 else ''
    return [
        bark.to_object(f'{name}_stem{suf}', 'foliage_bark', col, ao_strength=0.22, ao_min=0.65),
        cards.to_object(f'{name}_blooms{suf}', 'foliage_shrub', col, ao_strength=0.14, ao_min=0.74,
                        spherical_center=c_center, spherical_blend=0.85),
    ]


def build_bougainvillea(name='bougainvillea', col=None):
    vine = name == 'bougainvillea_vine'
    seed = 342 if vine else 341
    return _build_bougainvillea(name, vine=vine, seed=seed, col=col, lod1=False) + _build_bougainvillea(name, vine=vine, seed=seed, col=col, lod1=True)


# ---- 5. Shrubs (`bush_a`, `bush_b`) --------------------------------------------------------
def build_bush(name='bush_a', col=None):
    """Lush Ghibli painterly leaf-cluster shrub (~96 tris!) replacing procedural 288-tri bush(31)."""
    dry = name == 'bush_b'
    seed = 352 if dry else 351
    rnd = random.Random(seed)
    p = FoliagePart(seed)
    uv = FOLIAGE_UV['acacia_leaf'] if dry else FOLIAGE_UV['sycamore_leaf']
    base_tint = (1.06, 0.98, 0.78) if dry else (0.94, 1.02, 0.88)
    center = Vector((0.0, 0.0, 0.42))
    # 15 cupped layered cards forming a lush fluffy shrub mound (~120 tris total)
    for i in range(15):
        t = (i + 0.5) / 15.0
        a = i * 2.39996 + rnd.uniform(-0.22, 0.22)
        elev = -0.22 + 1.18 * t
        rr = (0.18 + 0.38 * math.sqrt(max(0.05, 1.0 - elev * elev * 0.5))) * rnd.uniform(0.85, 1.08)
        pos = Vector((math.cos(a) * rr, math.sin(a) * rr, 0.42 + elev * 0.34))
        nrm = (pos - center + Vector((0, 0, 0.22))).normalized()
        sz = rnd.uniform(0.70, 0.92)
        h_k = 0.80 + 0.24 * t
        srgb = _tint_srgb(base_tint[0] * h_k, base_tint[1] * h_k, base_tint[2] * h_k, rnd, 0.07)
        p.add_curved_card(pos, nrm, sz, sz * 0.90, uv, cup=0.24, srgb=srgb, roll=rnd.uniform(0, math.tau))
    return [p.to_object(name, 'foliage_shrub', col, ao_strength=0.16, ao_min=0.72,
                        spherical_center=center - Vector((0, 0, 0.2)), spherical_blend=0.88)]


# ---- 6. Oasis Lotus Pad (`lotus_pad`) ------------------------------------------------------
def build_lotus_pad(col=None):
    """Floating emerald oasis lotus pad cluster + delicate sculpted cream-pink blossom (1 draw call!)."""
    rnd = random.Random(361)
    p = FoliagePart(361)
    # 3 floating overlapping lotus pads resting cleanly on the water plane (z ≈ 0.02..0.035)
    for px, py, pz, rad, roll in ((0.0, 0.0, 0.025, 0.44, 0.3), (0.36, 0.24, 0.020, 0.32, 2.2), (-0.32, 0.22, 0.022, 0.28, 4.4)):
        p.add_curved_card((px, py, pz), (0, 0, 1), rad * 2.0, rad * 2.0, FOLIAGE_UV['lotus'],
                          cup=-0.04, srgb=_tint_srgb(0.98, 1.02, 0.96, rnd, 0.06), roll=roll)
    # Sculpted 8-petal cream-rose lotus blossom using the white swatch so lotus_pad is 1 single mesh!
    bx, by, bz = 0.14, -0.14, 0.045
    for k in range(8):
        a = k * math.tau / 8.0
        tilt = 0.65 if k % 2 == 0 else 0.95
        col_p = _jitter_srgb('#FCEAE8' if k % 2 == 0 else '#F5B8C8', rnd, 0.05)
        p.add_cone(0.036, 0.008, 0.14, (bx + math.cos(a) * 0.06, by + math.sin(a) * 0.06, bz + 0.04),
                   col_p, rot=(math.sin(a) * tilt, -math.cos(a) * tilt, a), verts=4)
    p.add_icosphere((bx, by, bz + 0.04), (0.042, 0.042, 0.032), _jitter_srgb('#F5C846', rnd, 0.04), sub=0)
    return [p.to_object('lotus_pad', 'foliage_shrub', col, ao_strength=0.0, spherical_blend=0.0)]


# ---- 7. Street Pot Plant (`pot_plant`) -----------------------------------------------------
def build_pot_plant(col=None):
    """Hand-thrown Egyptian terracotta pot with painted white folk band + lush foliage & blooms."""
    rnd = random.Random(371)
    pot = FoliagePart(371)
    fol = FoliagePart(372)
    # Tapered terracotta pot + rolled rim + white lime band + soil disc
    pot.add_cone(0.20, 0.28, 0.40, (0, 0, 0.20), _jitter_srgb('#C96E3D', rnd, 0.04), verts=10)
    pot.add_cone(0.295, 0.305, 0.065, (0, 0, 0.40), _jitter_srgb('#B85D32', rnd, 0.04), verts=10)
    pot.add_cone(0.265, 0.275, 0.045, (0, 0, 0.31), _jitter_srgb('#F5ECDA', rnd, 0.02), verts=10)
    pot.add_cone(0.25, 0.25, 0.02, (0, 0, 0.41), _jitter_srgb('#5C432C', rnd, 0.04), verts=8)
    # Lush layered geranium / bougainvillea sprigs spilling from the pot
    center = Vector((0, 0, 0.62))
    for i in range(7):
        a = i * 2.39996
        rr = 0.08 + 0.14 * (i / 6.0)
        pos = Vector((math.cos(a) * rr, math.sin(a) * rr, 0.56 + (i % 3) * 0.09))
        nrm = (pos - center + Vector((0, 0, 0.35))).normalized()
        uv = FOLIAGE_UV['bougainvillea'] if i % 2 == 0 else FOLIAGE_UV['sycamore_leaf']
        fol.add_curved_card(pos, nrm, 0.44, 0.42, uv, cup=0.22,
                            srgb=_tint_srgb(1.0, 0.98, 0.96, rnd, 0.06), roll=rnd.uniform(0, math.tau))
    return [
        pot.to_object('pot_plant_pot', 'foliage_bark', col, ao_strength=0.26, ao_min=0.62),
        fol.to_object('pot_plant_leaves', 'foliage_shrub', col, ao_strength=0.14, ao_min=0.74,
                      spherical_center=center, spherical_blend=0.82),
    ]


FOLIAGE_BUILDERS = {
    'palm_a': lambda col=None: build_palm('palm_a', col),
    'palm_b': lambda col=None: build_palm('palm_b', col),
    'palm_c': lambda col=None: build_palm('palm_c', col),
    'palm_d': lambda col=None: build_palm('palm_d', col),
    'sycamore': lambda col=None: build_sycamore('sycamore', col),
    'sycamore_a': lambda col=None: build_sycamore('sycamore_a', col),
    'sycamore_b': lambda col=None: build_sycamore('sycamore_b', col),
    'acacia': build_acacia,
    'bougainvillea': lambda col=None: build_bougainvillea('bougainvillea', col),
    'bougainvillea_bush': lambda col=None: build_bougainvillea('bougainvillea_bush', col),
    'bougainvillea_vine': lambda col=None: build_bougainvillea('bougainvillea_vine', col),
    'bush_a': lambda col=None: build_bush('bush_a', col),
    'bush_b': lambda col=None: build_bush('bush_b', col),
    'lotus_pad': build_lotus_pad,
    'pot_plant': build_pot_plant,
}
