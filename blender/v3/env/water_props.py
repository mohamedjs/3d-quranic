"""Environment v3 water & crossing builders (`water_props.py`).

Builds 4 handcrafted storybook-naturalistic Egyptian Nile water/crossing assets
with rich per-stone/per-plank vertex colors, baked geometric crease AO, and LOD1s:
  - river_bridge   : 20 m arched limestone-and-timber bridge across the Nile (deck z = 0.55)
  - footbridge     : 3.6 m timber plank & stone-abutment canal crossing (plank top z = 0.14)
  - canal_bank     : 4 m stepped mossy limestone quay & earthen lip (lip z = 0, toe z = -1.4)
  - stream_channel : 4 m raised stone-curbed village street rill with 3D submerged river pebbles
                     and a separate UV'd `toon_water` surface floating cleanly above terrain.

All coordinates preserve the exact v2/heightfield contracts so walkability stays unchanged.
"""
import math
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector, noise

from lib import bake_vertex_ao, make_lod1, make_material, srgb_to_linear


def _wob(p, amp, freq=1.6, seed=0):
    if not amp:
        return p
    o = Vector((seed * 7.1, seed * 3.3, seed * 1.7))
    return p + noise.noise_vector(p * freq + o) * amp


def _rt(loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    return Matrix.LocRotScale(Vector(loc), Euler(rot), Vector(scale))


def _jitter_hex(hex_str, rnd, spread=0.07):
    """Return jittered sRGB (0..1) tuple for bmesh `loops.layers.color` (BYTE_COLOR is sRGB-encoded)."""
    h = hex_str.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    k = 1.0 + rnd.uniform(-spread, spread)
    warm = rnd.uniform(-spread * 0.35, spread * 0.35)
    return (
        max(0.0, min(1.0, r * k + warm)),
        max(0.0, min(1.0, g * k)),
        max(0.0, min(1.0, b * k - warm * 0.6)),
    )


class MeshBuilder:
    """Bmesh builder that paints per-element sRGB-to-linear vertex colors for baked-AO v3 GLBs."""

    def __init__(self, seed=0):
        self.bm = bmesh.new()
        self.col_layer = self.bm.loops.layers.color.new('Color')
        self.seed = seed
        self.rnd = random.Random(seed)

    def _put(self, src, lin_col, mat4=None, smooth=True, wobble=0.0, freq=1.8):
        src.verts.index_update()
        vm = []
        for v in src.verts:
            p = (mat4 @ v.co) if mat4 else v.co.copy()
            vm.append(self.bm.verts.new(_wob(p, wobble, freq, self.seed)))
        rgba = (lin_col[0], lin_col[1], lin_col[2], 1.0)
        for f in src.faces:
            try:
                nf = self.bm.faces.new([vm[v.index] for v in f.verts])
                nf.smooth = smooth
                for lp in nf.loops:
                    lp[self.col_layer] = rgba
            except ValueError:
                pass
        src.free()
        return self

    def box(self, size, loc=(0, 0, 0), color='#C9B08A', bevel=0.0, seg=1, rot=(0, 0, 0),
            taper=1.0, smooth=True, wobble=0.0, freq=1.8, spread=0.06):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
            if v.co.z > 0 and taper != 1.0:
                v.co.x *= taper
                v.co.y *= taper
        if bevel > 0:
            bmesh.ops.bevel(
                bm, geom=bm.edges[:],
                offset=min(bevel, min(size) * 0.42), segments=seg,
                affect='EDGES', profile=0.5, clamp_overlap=True,
            )
        col = _jitter_hex(color, self.rnd, spread) if isinstance(color, str) else color
        return self._put(bm, col, _rt(loc, rot), smooth, wobble, freq)

    def cyl(self, r1, r2, depth, loc=(0, 0, 0), color='#8E623A', rot=(0, 0, 0),
            verts=7, smooth=True, cap=True, wobble=0.0, scale=(1, 1, 1), spread=0.06):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=verts, radius1=r1, radius2=r2, depth=depth)
        col = _jitter_hex(color, self.rnd, spread) if isinstance(color, str) else color
        return self._put(bm, col, _rt(loc, rot, scale), smooth, wobble)

    def stone(self, loc, scale=(0.3, 0.4, 0.25), color='#C6B08E', rot=(0, 0, 0),
              sub=0, wobble=0.015, freq=3.5, flat_bottom=None, spread=0.09):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=sub + 1, radius=0.5)
        if flat_bottom is not None:
            for v in bm.verts:
                v.co.z = max(v.co.z, -0.5 * flat_bottom)
        col = _jitter_hex(color, self.rnd, spread) if isinstance(color, str) else color
        return self._put(bm, col, _rt(loc, rot, scale), True, wobble, freq)

    def arch_rib(self, y0, y1, x, z_base, z_top, thickness=0.20, width=0.20, segs=8, color='#6B4829'):
        """Curved timber or stone arch rib spanning Y from y0 to y1 at lateral offset x."""
        bm = bmesh.new()
        rings = []
        hw = width * 0.5
        ht = thickness * 0.5
        for i in range(segs + 1):
            t = i / segs
            y = y0 + (y1 - y0) * t
            s = math.sin(t * math.pi)
            z = z_base + (z_top - z_base) * (s ** 0.72)
            rings.append([
                bm.verts.new((x - hw, y, z - ht)),
                bm.verts.new((x + hw, y, z - ht)),
                bm.verts.new((x + hw, y, z + ht)),
                bm.verts.new((x - hw, y, z + ht)),
            ])
        for a, b in zip(rings, rings[1:]):
            for k in range(4):
                bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
        col = _jitter_hex(color, self.rnd, 0.05) if isinstance(color, str) else color
        return self._put(bm, col, None, True, 0.006, 2.2)

    def to_object(self, name, col=None, mat_name='env_v3_water_prop', ao_strength=0.30, ao_min=0.60):
        me = bpy.data.meshes.new(name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        if me.color_attributes:
            me.color_attributes.active_color_index = 0
            me.color_attributes.render_color_index = 0
        mat = make_material(mat_name, base_color=(0.8, 0.7, 0.55), roughness=0.88, use_vcol=True)
        me.materials.append(mat)
        obj = bpy.data.objects.new(name, me)
        (col or bpy.context.scene.collection).objects.link(obj)
        bake_vertex_ao(obj, strength=ao_strength, min_val=ao_min)
        return obj


def _water_ribbon(name, length=4.0, width=0.86, z=0.105, segs_y=10, segs_x=4, col=None):
    """Create a UV'd water surface mesh (`u` across 0..1, `v` metres along) with material `toon_water`."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    rows = []
    for iy in range(segs_y + 1):
        v_m = length * (iy / segs_y)
        y = -length * 0.5 + v_m
        row = []
        for ix in range(segs_x + 1):
            u = ix / segs_x
            x = (u - 0.5) * width
            dz = 0.006 * math.sin(u * math.pi)
            row.append(bm.verts.new((x, y, z + dz)))
        rows.append((v_m, row))
    for iy in range(segs_y):
        v0, r0 = rows[iy]
        v1, r1 = rows[iy + 1]
        for ix in range(segs_x):
            f = bm.faces.new((r0[ix], r0[ix + 1], r1[ix + 1], r1[ix]))
            f.smooth = True
            uvs = ((ix / segs_x, v0), ((ix + 1) / segs_x, v0), ((ix + 1) / segs_x, v1), (ix / segs_x, v1))
            for lp, uv in zip(f.loops, uvs):
                lp[uvl].uv = uv
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    mat = make_material('toon_water', base_color=srgb_to_linear('#48A89E'), roughness=0.08, use_vcol=False)
    me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    (col or bpy.context.scene.collection).objects.link(obj)
    return obj


# ---- 1. Nile River Bridge (`river_bridge.glb`) ---------------------------------------------
def build_river_bridge(col=None):
    """20 m arched limestone-and-timber bridge across the Nile.
    Matches heightfield.js BRIDGE = { halfW: 1.7, halfL: 10, deck: 0.55 }:
    spans Y in [-10, 10], walkable deck top at z = 0.55, side rails at x = +-1.74."""
    b = MeshBuilder(seed=201)
    rnd = b.rnd
    wood_a, wood_b, wood_dark = '#9D6D3E', '#825731', '#593A20'
    stone_hi, stone_mid, stone_wet = '#D8C096', '#B99F78', '#6D6950'
    rope_col, iron_col, glow_col = '#C4A264', '#4B3E31', '#FFD878'

    # 4 masonry cutwater piers anchored deep into the riverbed (z = -2.8 .. +0.42)
    for py in (-9.4, -3.2, 3.2, 9.4):
        end_pier = abs(py) > 8.0
        pw = 4.1 if end_pier else 3.95
        pd = 1.65 if end_pier else 1.25
        b.box((pw + 0.25, pd + 0.28, 2.2), (0, py, -1.7), stone_wet, bevel=0.08, taper=0.92, wobble=0.025)
        b.box((pw, pd, 1.05), (0, py, -0.10), stone_mid, bevel=0.06, taper=0.96, wobble=0.018)
        b.box((pw + 0.14, pd + 0.16, 0.18), (0, py, 0.40), stone_hi, bevel=0.03, wobble=0.008)
        if not end_pier:
            for sx in (-1, 1):
                b.cyl(0.56, 0.42, 2.9, (sx * (pw * 0.5 + 0.12), py, -1.15), stone_wet, verts=5, wobble=0.02)

    # 3 graceful curved timber arch ribs under each bay
    for y0, y1 in ((-9.2, -3.2), (-3.2, 3.2), (3.2, 9.2)):
        for rx in (-1.52, 0.0, 1.52):
            b.arch_rib(y0, y1, rx, z_base=-0.38, z_top=0.36, thickness=0.22, width=0.20, segs=8, color=wood_dark)

    # Longitudinal heavy timber deck stringers running the full 20 m span
    for sx in (-1.52, -0.52, 0.52, 1.52):
        b.box((0.18, 20.2, 0.20), (sx, 0, 0.37), wood_dark, bevel=0.0, wobble=0.005)

    # 32 hand-hewn weathered deck planks (plank top cleanly at z = 0.55)
    n_planks = 32
    for i in range(n_planks):
        y = -9.85 + (19.7 * i) / (n_planks - 1)
        w = 3.54 + rnd.uniform(-0.07, 0.07)
        col_p = wood_a if (i % 3 != 0) else wood_b
        b.box((w, 0.56, 0.10), (rnd.uniform(-0.03, 0.03), y, 0.50), col_p,
              bevel=0.015, rot=(0, 0, rnd.uniform(-0.007, 0.007)), wobble=0.004, spread=0.09)

    # Timber wheel-curb beams along both edges of the deck
    for sx in (-1.66, 1.66):
        b.box((0.14, 19.6, 0.12), (sx, 0, 0.60), wood_dark, bevel=0.0)

    # Sculpted entrance limestone bollards + warm amber corner bridge lanterns
    for sy in (-9.6, 9.6):
        for sx in (-1.78, 1.78):
            b.box((0.52, 0.52, 1.25), (sx, sy, 1.05), stone_hi, bevel=0.05, taper=0.88, wobble=0.014)
            b.box((0.60, 0.60, 0.16), (sx, sy, 1.70), stone_mid, bevel=0.03)
            b.cyl(0.14, 0.12, 0.34, (sx, sy, 1.95), glow_col, verts=6, spread=0.02)
            b.cyl(0.20, 0.04, 0.18, (sx, sy, 2.20), iron_col, verts=6, spread=0.03)

    # Timber parapet railing posts, double rails, diagonal knee braces & rope lashings
    rail_ys = [-7.4, -5.2, -3.2, -1.1, 1.1, 3.2, 5.2, 7.4]
    for sx in (-1.74, 1.74):
        b.box((0.13, 19.0, 0.10), (sx, 0, 1.44), wood_a, bevel=0.02, wobble=0.005)
        b.box((0.09, 19.0, 0.08), (sx, 0, 1.02), wood_b, bevel=0.0, wobble=0.005)
        for py in rail_ys:
            b.box((0.15, 0.15, 1.04), (sx, py, 0.96), wood_dark, bevel=0.0, wobble=0.005)
            b.box((0.09, 0.09, 0.56), (sx + math.copysign(0.11, sx), py, 0.72), wood_b,
                  bevel=0.0, rot=(0, math.copysign(0.45, sx), 0))
            b.cyl(0.095, 0.095, 0.08, (sx, py, 1.40), rope_col, verts=6)

    obj = b.to_object('river_bridge', col, ao_strength=0.32, ao_min=0.58)
    lod1 = make_lod1(obj, ratio=0.40, name='river_bridge_LOD1')
    return [obj, lod1]


# ---- 2. Canal Footbridge (`footbridge.glb`) ------------------------------------------------
def build_footbridge(col=None):
    """3.6 m timber plank & stone-abutment canal footbridge.
    Matches details.js placement `y = FOOTBRIDGE_DECK - 0.14`: spans X, plank top at z = +0.14."""
    b = MeshBuilder(seed=202)
    rnd = b.rnd
    wood_a, wood_b, wood_dark = '#9E6E40', '#835931', '#5A3A20'
    stone_hi, stone_dark, rope_col = '#CEB78F', '#8F7D61', '#C4A366'

    # Stone bank abutments anchoring both ends into the canal slopes (x = +-1.66)
    for sx in (-1.66, 1.66):
        b.box((0.52, 2.04, 0.72), (sx, 0, -0.34), stone_dark, bevel=0.05, taper=0.92, wobble=0.02)
        for ky in (-0.64, 0.0, 0.64):
            b.stone((sx + math.copysign(0.15, sx), ky, -0.08), (0.36, 0.54, 0.26), stone_hi, sub=0, wobble=0.014)

    # Gently arched under-stringers & cross sleepers supporting the planks
    for sy in (-0.62, 0.62):
        segs = 6
        for i in range(segs):
            t0, t1 = i / segs, (i + 1) / segs
            xm = -1.65 + 3.30 * (t0 + t1) * 0.5
            zm = -0.14 + 0.16 * math.sin(((t0 + t1) * 0.5) * math.pi)
            dz = 0.16 * (math.sin(t1 * math.pi) - math.sin(t0 * math.pi))
            ang = math.atan2(dz, 3.30 / segs)
            b.box((3.45 / segs, 0.14, 0.15), (xm, sy, zm), wood_dark, bevel=0.0, rot=(0, -ang, 0))
    for sx in (-1.42, 1.42):
        b.box((0.16, 1.98, 0.14), (sx, 0, -0.02), wood_dark, bevel=0.0)

    # 6 hand-hewn weathered planks spanning X (plank top at exact z = +0.14)
    for i in range(6):
        y = -0.75 + i * 0.30
        b.box((3.56 + rnd.uniform(-0.10, 0.10), 0.27, 0.085),
              (rnd.uniform(-0.04, 0.04), y, 0.098),
              wood_a if i % 2 else wood_b, bevel=0.015,
              rot=(0, 0, rnd.uniform(-0.014, 0.014)), wobble=0.004, spread=0.09)

    # Rustic lashed timber handrail along one side (y = -0.94, preserving v2 clearance)
    for sx in (-1.48, 0.0, 1.48):
        b.cyl(0.052, 0.042, 1.06, (sx, -0.94, 0.54), wood_dark, verts=6, wobble=0.006)
        b.cyl(0.068, 0.068, 0.07, (sx, -0.94, 0.96), rope_col, verts=6)
    b.cyl(0.042, 0.038, 3.25, (0, -0.94, 0.97), wood_a, rot=(0, math.pi * 0.5, 0), verts=6, wobble=0.008)
    b.cyl(0.028, 0.028, 3.05, (0, -0.94, 0.56), wood_b, rot=(0, math.pi * 0.5, 0), verts=6, wobble=0.006)

    obj = b.to_object('footbridge', col, ao_strength=0.30, ao_min=0.60)
    lod1 = make_lod1(obj, ratio=0.45, name='footbridge_LOD1')
    return [obj, lod1]


# ---- 3. Mossy Limestone Canal Quay (`canal_bank.glb`) --------------------------------------
def build_canal_bank(col=None):
    """4 m stepped limestone quay & mossy mud bank along Y (y in [-2, 2]).
    Matches details.js placement: grassy lip at x < 0, z = 0; slopes down toward +x to z = -1.4."""
    b = MeshBuilder(seed=203)
    rnd = b.rnd
    grass_col = '#6B943C'
    mud_col, mud_wet = '#6D5033', '#44311E'
    stone_hi, stone_mid, stone_moss = '#C6AD82', '#9E8866', '#5F7543'
    wood_post = '#664325'

    # Continuous sculpted earthen bank & wet slope tucked cleanly under the dressed stone quay
    prof = [(-0.82, 0.00), (-0.28, -0.02), (0.06, -0.14), (0.40, -0.52), (0.78, -0.96), (1.12, -1.42)]
    ny = 5
    rows = []
    for iy in range(ny + 1):
        y = -2.0 + 4.0 * iy / ny
        row = []
        for x, z in prof:
            jx = x + 0.03 * math.sin(y * 2.1 + x * 1.7)
            row.append(b.bm.verts.new((jx, y, z)))
        rows.append(row)
    for iy in range(ny):
        for k in range(len(prof) - 1):
            f = b.bm.faces.new((rows[iy][k], rows[iy][k + 1], rows[iy + 1][k + 1], rows[iy + 1][k]))
            f.smooth = True
            xc = (prof[k][0] + prof[k + 1][0]) * 0.5
            zc = (prof[k][1] + prof[k + 1][1]) * 0.5
            hx = grass_col if xc < -0.10 else (mud_wet if zc < -0.72 else mud_col)
            lc = _jitter_hex(hx, rnd, 0.05)
            for lp in f.loops:
                lp[b.col_layer] = (lc[0], lc[1], lc[2], 1.0)

    # Dressed chiseled Egyptian limestone quay coping stones flush with the grassy bank lip
    y = -1.96
    while y < 1.88:
        L = min(rnd.uniform(0.68, 0.96), 2.02 - y)
        b.box((0.34, L * 0.94, 0.16), (0.08 + rnd.uniform(-0.02, 0.02), y + L * 0.5, -0.11),
              stone_hi if rnd.random() < 0.62 else stone_mid,
              bevel=0.0, taper=0.92, smooth=False, wobble=0.012, spread=0.08)
        y += L

    # Lower waterline mossy limestone blocks sitting in the wet splash zone
    y = -1.94
    while y < 1.88:
        L = min(rnd.uniform(0.64, 0.92), 2.02 - y)
        st_c = stone_moss if rnd.random() < 0.60 else stone_mid
        b.box((0.40, L * 0.93, 0.26), (0.42 + rnd.uniform(-0.025, 0.025), y + L * 0.5, -0.52),
              st_c, bevel=0.0, taper=0.92, smooth=False, wobble=0.016, spread=0.09)
        y += L

    # Submerged mossy rubble stones along the canal toe
    y = -1.80
    while y < 1.80:
        L = rnd.uniform(0.75, 1.05)
        b.box((0.36, L * 0.84, 0.22), (0.76 + rnd.uniform(-0.04, 0.04), y + L * 0.5, -0.92),
              stone_moss, bevel=0.0, taper=0.82, smooth=False, wobble=0.024, spread=0.10)
        y += L

    # Weathered timber mooring stake along the quay edge
    b.cyl(0.058, 0.050, 0.66, (0.22, -0.65, -0.14), wood_post, verts=6, wobble=0.008)

    obj = b.to_object('canal_bank', col, ao_strength=0.30, ao_min=0.58)
    lod1 = make_lod1(obj, ratio=0.45, name='canal_bank_LOD1')
    return [obj, lod1]


# ---- 4. Village Street Rill (`stream_channel.glb`) -----------------------------------------
def build_stream_channel(col=None):
    """4 m raised stone-curbed street rill with 3D submerged river pebbles and sparkling water ribbon.
    Sits cleanly proud of the street dirt (bed z = +0.02, water z = +0.105, curbs z = +0.16) so
    terrain never clips through the water surface; fits inside village.js's existing 0.6 m collider."""
    b = MeshBuilder(seed=204)
    rnd = b.rnd
    bed_col = '#735737'
    curb_hi, curb_mid, curb_moss = '#CBB084', '#A78E6A', '#617C42'
    pebble_cols = ['#B8905E', '#896B49', '#6B6559', '#D2AE78', '#965F3B']

    # Recessed stone-and-silt channel floor sitting cleanly above ground (z = +0.025)
    b.box((1.06, 4.0, 0.14), (0, 0, -0.045), bed_col, bevel=0.0, smooth=False, spread=0.04)

    # Dressed chiseled limestone curb walls on both sides (x = +-0.50, top z = +0.165)
    for sx in (-1, 1):
        b.box((0.16, 4.0, 0.28), (sx * 0.49, 0, 0.01), curb_mid, bevel=0.0, smooth=False, spread=0.04)
        y = -2.0
        while y < 1.96:
            L = min(rnd.uniform(0.56, 0.80), 2.02 - y)
            col_c = curb_moss if rnd.random() < 0.24 else (curb_hi if rnd.random() < 0.62 else curb_mid)
            b.box((0.23 + rnd.uniform(-0.014, 0.014), L * 0.93, 0.145),
                  (sx * (0.52 + rnd.uniform(-0.012, 0.012)), y + L * 0.5, 0.102 + rnd.uniform(-0.008, 0.008)),
                  col_c, bevel=0.0, taper=0.90, smooth=False, wobble=0.009, spread=0.08)
            y += L

    # 12 sculpted rounded colorful river pebbles resting on the submerged channel bed
    for _ in range(12):
        px = rnd.uniform(-0.31, 0.31)
        py = rnd.uniform(-1.86, 1.86)
        sx = rnd.uniform(0.15, 0.27)
        sy = rnd.uniform(0.16, 0.30)
        sz = rnd.uniform(0.052, 0.084)
        b.stone((px, py, 0.038), (sx, sy, sz), rnd.choice(pebble_cols),
                rot=(0, 0, rnd.uniform(0, math.tau)), sub=0, wobble=0.007, flat_bottom=0.2)

    body = b.to_object('stream_channel', col, ao_strength=0.28, ao_min=0.60)
    water = _water_ribbon('stream_channel_water', length=4.0, width=0.86, z=0.105, segs_y=8, segs_x=3, col=col)
    # Lightweight LOD1 for distance & Lite mid/far chunks (clean curbs + bed + 2-seg water)
    b_lo = MeshBuilder(seed=205)
    b_lo.box((1.06, 4.0, 0.14), (0, 0, -0.045), bed_col, bevel=0.0, smooth=False, spread=0.02)
    for sx in (-1, 1):
        b_lo.box((0.24, 4.0, 0.29), (sx * 0.51, 0, 0.02), curb_hi, bevel=0.0, taper=0.92, smooth=False, spread=0.03)
    body_lo = b_lo.to_object('stream_channel_LOD1', col, ao_strength=0.24, ao_min=0.62)
    water_lo = _water_ribbon('stream_channel_water_LOD1', length=4.0, width=0.86, z=0.105, segs_y=2, segs_x=2, col=col)
    return [body, water, body_lo, water_lo]
