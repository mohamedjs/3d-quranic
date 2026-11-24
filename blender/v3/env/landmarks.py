"""Environment v3 landmark builders.

M1 implements `backdrop_hills`: a 3-layer Egyptian Nile valley horizon ring
(near valley foothills + distant palm-grove ridge, mid Theban limestone escarpment
mesas with protruding buttresses and carved wadis, and far mountain silhouette
peaks) encircling the 520 m terrain with zero tabletop horizon gap. Coordinates
are computed in Three.js world space (X east, Y up, Z north) and converted to
Blender space (X, -Z, Y) so `export_yup=True` aligns exactly with heightfield.js.
"""
import math

import bmesh
import bpy

from lib import make_material, rgb_srgb_to_linear


def _fbm1(angle, harmonics):
    """Deterministic periodic fbm around a full circle (seamless at 0 / 2pi)."""
    s = 0.0
    for freq, amp, phase in harmonics:
        s += math.sin(angle * freq + phase) * amp
    return s


def _superellipse_dir(theta, power):
    """Unit-like direction stretched onto a superellipse (max(|x|,|z|) ~ 1 at high p)."""
    cx = math.cos(theta)
    cz = math.sin(theta)
    denom = (abs(cx) ** power + abs(cz) ** power) ** (1.0 / power)
    return cx / denom, cz / denom


def _nile_pass_mask(wx, wz):
    """Smooth valley opening where the Nile enters/exits at wz ~ 68..78 on east & west."""
    ang_e = math.atan2(72.0, 260.0)
    ang_w = math.atan2(72.0, -260.0)
    a = math.atan2(wz, wx)

    def wrap(d):
        return abs((d + math.pi) % (2.0 * math.pi) - math.pi)

    de = wrap(a - ang_e)
    dw = wrap(a - ang_w)
    m_e = math.exp(-((de / 0.25) ** 2))
    m_w = math.exp(-((dw / 0.27) ** 2))
    return max(m_e, m_w)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _lerp3(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def _build_ring(bm, uv_layer, col_layer, segs, power, profile_fn, layer_u):
    """Build one closed terrain-band ring with smooth normals, UV (layer, height), and sRGB color."""
    rings = []
    n_rows = None
    for i in range(segs):
        theta = (i / segs) * math.tau
        dx, dz = _superellipse_dir(theta, power)
        samples = profile_fn(theta, dx, dz)
        if n_rows is None:
            n_rows = len(samples)
        row = []
        for rad, wy, v_norm, srgb in samples:
            wx = dx * rad
            wz = dz * rad
            # Three.js (wx, wy, wz) -> Blender (wx, -wz, wy) for export_yup=True
            v = bm.verts.new((wx, -wz, wy))
            row.append((v, v_norm, srgb))
        rings.append(row)

    for i in range(segs):
        a = rings[i]
        b = rings[(i + 1) % segs]
        for r in range(n_rows - 1):
            v00, vn00, c00 = a[r]
            v10, vn10, c10 = b[r]
            v11, vn11, c11 = b[r + 1]
            v01, vn01, c01 = a[r + 1]
            try:
                # Winding so face normal points inward toward the valley center and upward
                face = bm.faces.new((v00, v10, v11, v01))
                face.smooth = True
                data = (
                    (vn00, c00),
                    (vn10, c10),
                    (vn11, c11),
                    (vn01, c01),
                )
                for loop, (vn, srgb) in zip(face.loops, data):
                    loop[uv_layer].uv = (layer_u, vn)
                    lin = rgb_srgb_to_linear(*srgb)
                    loop[col_layer] = (lin[0], lin[1], lin[2], 1.0)
            except ValueError:
                pass


def build_backdrop_hills(col=None):
    """Create the 3-layer Nile valley horizon escarpment & palm-ridge ring (`backdrop_hills`)."""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new('UVMap')
    col_layer = bm.loops.layers.color.new('Color')

    segs = 144

    # Palette (sRGB) calibrated to docs/art-direction.md & docs/004 §2
    nile_olive = (0.58, 0.67, 0.37)
    palm_crown = (0.43, 0.56, 0.30)
    foot_ochre = (0.82, 0.67, 0.45)
    desert_sand = (0.88, 0.74, 0.50)
    cliff_base = (0.80, 0.63, 0.44)
    cliff_mid = (0.88, 0.73, 0.52)
    cliff_cap = (0.94, 0.82, 0.62)
    far_base = (0.76, 0.66, 0.62)
    far_peak = (0.84, 0.75, 0.68)

    # Layer 0: Valley rim skirt + near olive/ochre foothills + undulating palm-grove rim.
    # Low profile (~14..28 m) hugs the 520 m terrain perimeter without blocking the sky.
    def layer0(theta, dx, dz):
        nile = _nile_pass_mask(dx * 280.0, dz * 280.0)
        north = _clamp(dz * 0.5 + 0.5, 0.0, 1.0)
        east_desert = _clamp((dx - 0.15) * 1.15, 0.0, 1.0)

        broad = _fbm1(theta, [(3, 0.40, 0.4), (5, 0.26, 1.8), (9, 0.18, 0.9), (15, 0.10, 2.5)])
        canopy = (0.5 + 0.5 * math.sin(theta * 48.0 + 0.5 * math.sin(theta * 13.0))) * (1.0 - east_desert * 0.75)
        h = (15.5 + 7.5 * north + 5.5 * broad + 2.4 * canopy) * (1.0 - 0.48 * nile)
        h = max(9.5, h)
        # Radial spur ripples create alternating sunlit & shaded hillside facets
        spur = 10.0 * _fbm1(theta, [(7, 0.55, 0.6), (13, 0.45, 2.1)])

        toe_col = _lerp3(nile_olive, desert_sand, east_desert * 0.85)
        mid_col = _lerp3(foot_ochre, desert_sand, east_desert * 0.72)
        crest_col = _lerp3(mid_col, palm_crown, (1.0 - east_desert) * (0.28 + 0.42 * nile))

        return [
            (250.0, -10.0, 0.00, toe_col),
            (274.0 + spur * 0.4, h * 0.46, 0.34, toe_col),
            (304.0 + spur, h * 0.88, 0.74, mid_col),
            (334.0 + spur * 0.8, h, 1.00, crest_col),
            (378.0, -15.0, 0.00, mid_col),
        ]

    # Layer 1: Mid Egyptian limestone escarpments (Luxor / Theban flat-topped stepped mesas
    # with protruding cliff buttresses and carved wadi notches, ~28..56 m tall).
    def layer1(theta, dx, dz):
        nile = _nile_pass_mask(dx * 445.0, dz * 445.0)
        north = _clamp(dz * 0.5 + 0.5, 0.0, 1.0)
        east_desert = _clamp((dx + 0.1) * 0.8, 0.0, 1.0)

        # Flat-topped tabular mesas separated by distinct wadi valleys
        raw = _fbm1(theta, [(4, 0.46, 0.9), (7, 0.28, 2.3), (12, 0.16, 0.4), (19, 0.09, 3.0)])
        mesa = math.tanh(raw * 2.4) * 0.5 + 0.5
        wadi = max(0.0, math.sin(theta * 5.0 + 1.6)) ** 5
        h = (28.0 + 13.0 * north + 21.0 * mesa - 11.0 * wadi) * (1.0 - 0.50 * nile)
        h = max(16.0, h)
        step1 = h * (0.50 + 0.05 * math.sin(theta * 11.0))
        step2 = h * (0.90 + 0.03 * math.cos(theta * 9.0 + 0.7))
        # Pronounced cliff buttresses give dramatic sunlit-gold vs shadow-lavender cliff facets!
        buttress = 26.0 * _fbm1(theta, [(8, 0.55, 1.1), (15, 0.45, 2.7)])

        c_base = _lerp3(cliff_base, desert_sand, east_desert * 0.30)
        c_mid = _lerp3(cliff_mid, cliff_cap, 0.35 * mesa)
        c_cap = _lerp3(cliff_cap, desert_sand, east_desert * 0.22)

        return [
            (372.0 + buttress * 0.4, -16.0, 0.00, c_base),
            (408.0 + buttress * 0.85, step1, 0.42, c_base),
            (436.0 + buttress, step2, 0.80, c_mid),
            (486.0 + buttress * 0.6, h, 1.00, c_cap),
            (548.0, -22.0, 0.00, c_base),
        ]

    # Layer 2: Distant mountain & desert ridge ring (~48..88 m tall -> 4..8 deg elevation,
    # leaving ~70% of the sky open for the 16 deg golden sun, cerulean zenith, and clouds!).
    def layer2(theta, dx, dz):
        nile = _nile_pass_mask(dx * 680.0, dz * 680.0)
        north = _clamp(dz * 0.5 + 0.5, 0.0, 1.0)
        w1 = _fbm1(theta, [(3, 0.42, 1.4), (6, 0.28, 0.3), (11, 0.18, 2.8), (17, 0.10, 1.1)])
        ridge = 1.0 - abs(math.sin(theta * 4.5 + 0.8))
        h = (44.0 + 20.0 * north + 24.0 * (w1 * 0.5 + 0.5) + 14.0 * ridge) * (1.0 - 0.38 * nile)
        h = max(28.0, h)
        spur = 30.0 * _fbm1(theta, [(5, 0.6, 2.0), (11, 0.4, 0.5)])

        return [
            (560.0 + spur * 0.5, -24.0, 0.00, far_base),
            (635.0 + spur, h * 0.58, 0.54, far_base),
            (708.0 + spur * 0.7, h, 1.00, far_peak),
            (795.0, -28.0, 0.00, far_base),
        ]

    _build_ring(bm, uv_layer, col_layer, segs, 6.0, layer0, 0.0)
    _build_ring(bm, uv_layer, col_layer, segs, 3.2, layer1, 0.5)
    _build_ring(bm, uv_layer, col_layer, segs, 2.2, layer2, 1.0)

    bm.normal_update()
    me = bpy.data.meshes.new('backdrop_hills')
    bm.to_mesh(me)
    bm.free()

    mat = make_material('env_backdrop_hills', base_color=(0.82, 0.68, 0.50), roughness=0.98, use_vcol=True)
    me.materials.append(mat)
    obj = bpy.data.objects.new('backdrop_hills', me)
    (col or bpy.context.scene.collection).objects.link(obj)
    return obj
