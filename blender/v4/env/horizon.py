"""M4 Horizon Escarpment Ring (`backdrop_hills.glb`) driven by Poly Haven `namaqualand_cliff_01`.

Builds 3 continuous, closed, solid heightfield-like sandstone cliff & mountain rings displaced
and coloured from the Poly Haven `namaqualand_cliff_01` cliff asset (both its scanned rock
geometry and its albedo texture), preserving the exact v3/M1 contract for `Environment.jsx`:
  - ONE single vertex-colored mesh (geometry-only GLB, no embedded images) <= 12,000 tris.
  - Three concentric superellipse rings around the 520 m Nile valley with identical radii
    and east/west Nile valley openings (`atan2(72, +-260)`).
  - Closed solid silhouettes with continuous smooth normals: zero gaps, zero floating
    triangles, zero jagged shards, crisp stepped sandstone escarpments & mountain ridges.
  - Vertex colour (`COLOR_0`, linear) smoothly sampled from `namaqualand_cliff_01_diff_2k.jpg`,
    warm-filtered and Laplacian-smoothed into a narrow warm Egyptian sandstone range (no
    isolated pale/white/grey facets).
  - `uv.x` = layer (`0.0` near foothills, `0.5` mid Theban cliffs, `1.0` far desert peaks),
    `uv.y` = normalised height `[0..1]` for the 3 haze layers in `Environment.jsx`.

Run headless from repo root:
  blender -b --factory-startup --python blender/v4/env/horizon.py
  blender -b --factory-startup --python blender/v4/env/horizon.py -- --sheet
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib

MAX_TRIS = 12000


def _fbm1(angle, harmonics):
    return sum(math.sin(angle * f + p) * a for f, a, p in harmonics)


def _ridged1(angle, harmonics):
    return sum((1.0 - abs(math.sin(angle * f + p))) * a for f, a, p in harmonics)


def _superellipse_dir(theta, power):
    cx, cz = math.cos(theta), math.sin(theta)
    denom = (abs(cx) ** power + abs(cz) ** power) ** (1.0 / power)
    return cx / denom, cz / denom


def _nile_pass_mask(wx, wz):
    """Smooth valley opening where the Nile enters/exits at wz ~ 68..78 on east & west."""
    ang_e = math.atan2(72.0, 260.0)
    ang_w = math.atan2(72.0, -260.0)
    a = math.atan2(wz, wx)

    def wrap(d):
        return abs((d + math.pi) % (2.0 * math.pi) - math.pi)

    m_e = math.exp(-((wrap(a - ang_e) / 0.25) ** 2))
    m_w = math.exp(-((wrap(a - ang_w) / 0.27) ** 2))
    return max(m_e, m_w)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _lerp3(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def _box_blur_periodic_1d(arr, radius=2, passes=2):
    out = arr.astype(np.float32).copy()
    k = 2 * radius + 1
    for _ in range(passes):
        acc = np.zeros_like(out)
        for d in range(-radius, radius + 1):
            acc += np.roll(out, d, axis=0)
        out = acc / k
    return out


def _box_blur_2d(arr, radius=2, passes=2, wrap_x=True):
    out = arr.astype(np.float32).copy()
    h, w = out.shape[:2]
    k = 2 * radius + 1
    for _ in range(passes):
        acc = np.zeros_like(out)
        if wrap_x:
            for d in range(-radius, radius + 1):
                acc += np.roll(out, d, axis=1)
        else:
            for d in range(-radius, radius + 1):
                idx = np.clip(np.arange(w) + d, 0, w - 1)
                acc += out[:, idx]
        out = acc / k
        acc = np.zeros_like(out)
        for d in range(-radius, radius + 1):
            idx = np.clip(np.arange(h) + d, 0, h - 1)
            acc += out[idx, :]
        out = acc / k
    return out


def _extract_cliff_fields():
    """Extract crisp periodic rock-relief & smooth warm sandstone albedo fields from Poly Haven
    `namaqualand_cliff_01` (both scanned cliff geometry and its 2k diffuse texture)."""
    lib.reset_scene()
    src = lib.OUT_MODELS / 'ph_namaqualand_cliff_01_hi.glb'
    bpy.ops.import_scene.gltf(filepath=str(src))
    objs = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    pts_list = []
    for o in objs:
        mw = o.matrix_world
        pts_list.append(np.array([mw @ v.co for v in o.data.vertices], dtype=np.float32))
    pts = np.concatenate(pts_list, axis=0)
    mn, mx = pts.min(axis=0), pts.max(axis=0)
    span = np.maximum(mx - mn, 1e-4)

    u = np.clip((pts[:, 0] - mn[0]) / span[0], 0.0, 0.9999)
    v = np.clip((pts[:, 2] - mn[2]) / span[2], 0.0, 0.9999)
    depth = ((pts[:, 1] - (mn[1] + mx[1]) * 0.5) / (span[1] * 0.5)).astype(np.float32)

    # 1. Rasterize half-period crest & face buttress relief, then mirror for seamless 360° tiling
    nu_half, nv = 64, 32
    crest_max = np.zeros(nu_half, dtype=np.float32)
    crest_cnt = np.zeros(nu_half, dtype=np.float32)
    face_sum = np.zeros((nv, nu_half), dtype=np.float32)
    face_cnt = np.zeros((nv, nu_half), dtype=np.float32)

    iu = (u * nu_half).astype(np.int32)
    iv = (v * nv).astype(np.int32)
    for k in range(len(pts)):
        c = iu[k]
        r = iv[k]
        if v[k] > crest_max[c]:
            crest_max[c] = v[k]
        crest_cnt[c] += 1.0
        face_sum[r, c] += max(0.0, depth[k])
        face_cnt[r, c] += 1.0

    valid_c = crest_cnt > 0
    c_mean = float(crest_max[valid_c].mean()) if np.any(valid_c) else 0.75
    crest_max[~valid_c] = c_mean

    valid_f = face_cnt > 0
    f_mean = float((face_sum[valid_f] / face_cnt[valid_f]).mean()) if np.any(valid_f) else 0.35
    face_grid = np.where(valid_f, face_sum / np.maximum(face_cnt, 1.0), f_mean)

    # Light smoothing preserves crisp cliff crags & buttress ribs without noisy spikes
    crest_full = np.concatenate([crest_max, crest_max[::-1]])
    crest_full = _box_blur_periodic_1d(crest_full, radius=1, passes=2)
    crest_full = (crest_full - crest_full.mean()) / max(float(crest_full.std()), 0.05)
    crest_full = np.clip(crest_full, -1.7, 1.7)

    face_full = np.concatenate([face_grid, face_grid[:, ::-1]], axis=1)
    face_full = _box_blur_2d(face_full, radius=1, passes=2, wrap_x=True)
    face_full = (face_full - face_full.mean()) / max(float(face_full.std()), 0.05)
    face_full = np.clip(face_full, -1.7, 1.7)

    # 2. Extract heavily smoothed, warm-filtered sandstone albedo modulation from the 2k cliff texture
    diff_p = sorted((lib.CACHE_PH / 'namaqualand_cliff_01' / 'textures').glob('*diff*'))[0]
    diff_raw = lib.load_image_rgba(diff_p, (128, 128))[:, :, :3]
    lum_raw = 0.2126 * diff_raw[:, :, 0] + 0.7152 * diff_raw[:, :, 1] + 0.0722 * diff_raw[:, :, 2]
    med_lum = float(np.median(lum_raw))
    lum_clamped = np.clip(lum_raw, med_lum * 0.80, med_lum * 1.15)
    scale_l = lum_clamped / np.maximum(lum_raw, 1e-4)
    warm_rgb = np.clip(diff_raw * scale_l[:, :, None], 0.0, 1.0)
    # Enforce warm sandstone chromaticity (suppress any greenish/grey/blue outliers)
    warm_rgb[:, :, 1] = np.minimum(warm_rgb[:, :, 1], warm_rgb[:, :, 0] * 0.88)
    warm_rgb[:, :, 2] = np.minimum(warm_rgb[:, :, 2], warm_rgb[:, :, 1] * 0.84)

    half_c = warm_rgb[:, :64, :]
    col_full = np.concatenate([half_c, half_c[:, ::-1, :]], axis=1)
    col_full = _box_blur_2d(col_full, radius=4, passes=4, wrap_x=True)
    col_mean = np.maximum(col_full.mean(axis=(0, 1)), 0.05)
    # Narrow warm modulation ratio around 1.0 (strictly [0.92, 1.06] — zero pale snow/paper facets!)
    col_ratio = np.clip(col_full / col_mean[None, None, :], 0.92, 1.06)

    return crest_full, face_full, col_ratio


def _sample_1d(arr, u):
    n = len(arr)
    x = (u % 1.0) * n
    i0 = int(x) % n
    i1 = (i0 + 1) % n
    f = x - math.floor(x)
    return float(arr[i0] * (1.0 - f) + arr[i1] * f)


def _sample_2d(arr, u, v):
    h, w = arr.shape[:2]
    x = (u % 1.0) * w
    y = _clamp(v, 0.0, 0.9999) * (h - 1)
    x0 = int(x) % w
    x1 = (x0 + 1) % w
    y0 = int(y)
    y1 = min(y0 + 1, h - 1)
    fx = x - math.floor(x)
    fy = y - y0
    top = arr[y0, x0] * (1.0 - fx) + arr[y0, x1] * fx
    bot = arr[y1, x0] * (1.0 - fx) + arr[y1, x1] * fx
    return top * (1.0 - fy) + bot * fy


def _smooth_grid_colors(grid, passes=2):
    """Laplacian-smooth sRGB colours along the ring (wrapping in theta, gentle vertically)
    so isolated bright or dark facets can never occur while horizontal sandstone strata stay crisp."""
    segs = len(grid)
    n_rows = len(grid[0])
    cols = [[list(grid[i][r][3]) for r in range(n_rows)] for i in range(segs)]
    for _ in range(passes):
        nxt = [[None] * n_rows for _ in range(segs)]
        for i in range(segs):
            il = (i - 1) % segs
            ir = (i + 1) % segs
            for r in range(n_rows):
                c0 = cols[i][r]
                cl = cols[il][r]
                cr = cols[ir][r]
                cu = cols[i][min(r + 1, n_rows - 1)]
                cd = cols[i][max(r - 1, 0)]
                nxt[i][r] = [
                    0.48 * c0[c] + 0.21 * cl[c] + 0.21 * cr[c] + 0.05 * cu[c] + 0.05 * cd[c]
                    for c in range(3)
                ]
        cols = nxt
    for i in range(segs):
        for r in range(n_rows):
            rad, wy, vn, _ = grid[i][r]
            grid[i][r] = (rad, wy, vn, tuple(cols[i][r]))


def _build_ring(bm, uvl, coll, segs, power, profile_fn, layer_u, smooth_passes=2, min_dr=6.0):
    """Build one closed solid continuous cliff/mountain ring with smooth inward+upward normals
    and strictly monotonic radial progression (eliminates overhangs and dark fold-under facets)."""
    grid = []
    dirs = []
    for i in range(segs):
        theta = (i / segs) * math.tau
        dx, dz = _superellipse_dir(theta, power)
        dirs.append((dx, dz))
        samples = list(profile_fn(theta, dx, dz))
        # Enforce strictly monotonic outward radius so cliff faces never overhang inward
        prev_r = samples[0][0]
        for idx in range(1, len(samples)):
            rad, wy, vn, srgb = samples[idx]
            if rad < prev_r + min_dr:
                rad = prev_r + min_dr
                samples[idx] = (rad, wy, vn, srgb)
            prev_r = rad
        grid.append(samples)

    _smooth_grid_colors(grid, passes=smooth_passes)

    n_rows = len(grid[0])
    vrings = []
    for i in range(segs):
        dx, dz = dirs[i]
        row = []
        for rad, wy, vn, srgb in grid[i]:
            wx = dx * rad
            wz = dz * rad
            # Three.js (wx, wy, wz) -> Blender (wx, -wz, wy) matching export_yup=True
            v = bm.verts.new((wx, -wz, wy))
            row.append((v, vn, srgb))
        vrings.append(row)

    for i in range(segs):
        a = vrings[i]
        b = vrings[(i + 1) % segs]
        for r in range(n_rows - 1):
            v00, vn00, c00 = a[r]
            v10, vn10, c10 = b[r]
            v11, vn11, c11 = b[r + 1]
            v01, vn01, c01 = a[r + 1]
            try:
                f = bm.faces.new((v00, v10, v11, v01))
                f.smooth = True
                for lp, (vn, srgb) in zip(f.loops, ((vn00, c00), (vn10, c10), (vn11, c11), (vn01, c01))):
                    lp[uvl].uv = (layer_u, vn)
                    lin = lib.rgb_srgb_to_linear(*srgb)
                    lp[coll] = (lin[0], lin[1], lin[2], 1.0)
            except ValueError:
                pass


def build_horizon():
    crest_f, face_f, col_ratio = _extract_cliff_fields()
    lib.reset_scene()

    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    coll = bm.loops.layers.float_color.new('Color')

    segs = 192

    # Warm, narrow-range Egyptian sandstone & Nile valley palette (sRGB, zero pale/white/grey values)
    nile_olive   = (0.58, 0.64, 0.39)
    foot_ochre   = (0.76, 0.61, 0.42)
    desert_sand  = (0.81, 0.66, 0.45)
    cliff_talus  = (0.70, 0.53, 0.36)
    cliff_scarp  = (0.80, 0.63, 0.43)
    cliff_ledge  = (0.71, 0.54, 0.37)
    cliff_cap    = (0.86, 0.72, 0.51)
    far_base     = (0.72, 0.59, 0.47)
    far_mid      = (0.77, 0.64, 0.51)
    far_peak     = (0.82, 0.69, 0.56)

    def mod_col(base_srgb, u_tex, v_tex, strength=0.80, clamp_hi=0.87):
        mr, mg, mb = _sample_2d(col_ratio, u_tex, v_tex)
        r = base_srgb[0] * (1.0 + (float(mr) - 1.0) * strength)
        g = base_srgb[1] * (1.0 + (float(mg) - 1.0) * strength)
        b = base_srgb[2] * (1.0 + (float(mb) - 1.0) * strength)
        return (_clamp(r, 0.32, clamp_hi), _clamp(g, 0.27, clamp_hi * 0.89), _clamp(b, 0.21, clamp_hi * 0.76))

    # --- Layer 0: Grounded near valley foothills & low limestone bluffs (r ~ 250..382 m, h ~ 10..24 m) ---
    def layer0(theta, dx, dz):
        nile = _nile_pass_mask(dx * 280.0, dz * 280.0)
        north = _clamp(dz * 0.5 + 0.5, 0.0, 1.0)
        east = _clamp((dx - 0.08) * 1.15, 0.0, 1.0)

        u_c = (theta / math.tau) * 8.0 + 0.13
        c_rock = _sample_1d(crest_f, u_c)
        broad = _fbm1(theta, [(3, 0.38, 0.4), (5, 0.24, 1.8), (9, 0.16, 0.9), (16, 0.08, 2.3)])
        h = (13.5 + 6.0 * north + 4.5 * broad + 2.4 * c_rock) * (1.0 - 0.52 * nile)
        h = max(8.5, h)

        spur1 = 10.0 * _sample_2d(face_f, u_c, 0.35) + 6.0 * _fbm1(theta, [(7, 0.55, 0.6), (15, 0.45, 2.1)])
        spur2 = 13.0 * _sample_2d(face_f, u_c, 0.75) + 8.0 * _fbm1(theta, [(7, 0.55, 0.6), (15, 0.45, 2.1)])

        c_toe = _lerp3(nile_olive, desert_sand, east * 0.85)
        c_mid = _lerp3(foot_ochre, desert_sand, east * 0.70)
        c_top = _lerp3(foot_ochre, cliff_cap, 0.35 + east * 0.28)

        return [
            (250.0,               -14.0,    0.00, mod_col(c_toe, u_c, 0.10, 0.45, 0.84)),
            (278.0 + spur1 * 0.5, h * 0.38, 0.30, mod_col(c_toe, u_c, 0.35, 0.55, 0.84)),
            (294.0 + spur1,       h * 0.76, 0.68, mod_col(c_mid, u_c, 0.62, 0.65, 0.85)),
            (308.0 + spur2,       h * 0.96, 0.92, mod_col(c_top, u_c, 0.84, 0.65, 0.86)),
            (334.0 + spur2 * 0.5, h,        1.00, mod_col(c_top, u_c, 0.95, 0.55, 0.86)),
            (384.0,               -18.0,    0.00, mod_col(c_mid, u_c, 0.20, 0.40, 0.84)),
        ]

    # --- Layer 1: Steep stepped Theban/Luxor sandstone cliff escarpment (r ~ 370..555 m, h ~ 22..58 m) ---
    def layer1(theta, dx, dz):
        nile = _nile_pass_mask(dx * 445.0, dz * 445.0)
        north = _clamp(dz * 0.5 + 0.5, 0.0, 1.0)
        east = _clamp((dx + 0.1) * 0.8, 0.0, 1.0)

        u_c = (theta / math.tau) * 10.0 + 0.41
        c_rock = _sample_1d(crest_f, u_c)
        raw = _fbm1(theta, [(4, 0.44, 0.9), (7, 0.26, 2.3), (13, 0.15, 0.4), (21, 0.08, 3.0)])
        # Crisp flat-topped tabular mesas separated by carved desert wadis
        mesa = math.tanh((raw + 0.24 * c_rock) * 2.5) * 0.5 + 0.5
        wadi = max(0.0, math.sin(theta * 5.0 + 1.6)) ** 5
        crag = _ridged1(theta, [(11, 0.55, 0.4), (19, 0.35, 1.9)]) - 0.45
        h = (26.0 + 12.0 * north + 21.0 * mesa + 4.2 * c_rock + 3.5 * crag - 11.0 * wadi) * (1.0 - 0.52 * nile)
        h = max(16.0, h)

        # Crisp vertical sandstone cliff buttress ribs sculpted from namaqualand_cliff_01 relief
        rib = _ridged1(theta, [(9, 0.52, 1.1), (17, 0.38, 2.7), (29, 0.22, 0.5)]) - 0.55
        b_lo = 14.0 * _sample_2d(face_f, u_c, 0.25) + 18.0 * rib
        b_md = 22.0 * _sample_2d(face_f, u_c, 0.55) + 26.0 * rib
        b_hi = 18.0 * _sample_2d(face_f, u_c, 0.85) + 22.0 * rib

        # Steep stepped sandstone escarpment: talus -> vertical lower scarp -> bench -> steep upper cliff -> mesa cap
        s1 = h * (0.32 + 0.025 * math.sin(theta * 9.0))
        s2 = h * (0.66 + 0.025 * math.sin(theta * 11.0 + 0.4))
        s3 = h * (0.71 + 0.020 * math.cos(theta * 13.0))
        s4 = h * (0.96 + 0.015 * math.cos(theta * 10.0 + 0.7))

        # Slight warm shadow darkening inside recessed buttress flutes (rib < 0)
        flute = _clamp(0.95 + 0.08 * rib, 0.89, 1.04)
        c_tal = _lerp3(cliff_talus, desert_sand, east * 0.20)
        c_ldg = _lerp3(cliff_ledge, cliff_scarp, 0.25 * mesa)
        c_mid = _lerp3(cliff_scarp, cliff_cap, 0.28 * mesa)
        c_cap = _lerp3(cliff_cap, desert_sand, east * 0.16)

        def fl(c):
            return (c[0] * flute, c[1] * flute, c[2] * flute)

        return [
            (370.0 + b_lo * 0.30, -20.0,   0.00, mod_col(c_tal,      u_c, 0.08, 0.55, 0.85)),
            (408.0 + b_lo * 0.75, s1,      0.30, mod_col(fl(c_tal),  u_c, 0.28, 0.70, 0.85)),
            (415.0 + b_md * 1.00, s2,      0.64, mod_col(fl(c_mid),  u_c, 0.56, 0.80, 0.87)),
            (428.0 + b_md * 0.90, s3,      0.70, mod_col(fl(c_ldg),  u_c, 0.68, 0.75, 0.85)),
            (434.0 + b_hi * 1.00, s4,      0.95, mod_col(fl(c_cap),  u_c, 0.88, 0.75, 0.88)),
            (462.0 + b_hi * 0.65, h,       1.00, mod_col(c_cap,      u_c, 0.96, 0.60, 0.88)),
            (496.0 + b_hi * 0.35, h * 0.92, 0.88, mod_col(c_mid,     u_c, 0.80, 0.55, 0.86)),
            (524.0 + b_md * 0.20, h * 0.52, 0.48, mod_col(c_tal,     u_c, 0.45, 0.50, 0.84)),
            (558.0,               -26.0,   0.00, mod_col(c_tal,      u_c, 0.15, 0.45, 0.84)),
        ]

    # --- Layer 2: Distant craggy sandstone mountain ridges (r ~ 558..815 m, h ~ 46..92 m) ---
    def layer2(theta, dx, dz):
        nile = _nile_pass_mask(dx * 680.0, dz * 680.0)
        north = _clamp(dz * 0.5 + 0.5, 0.0, 1.0)

        u_c = (theta / math.tau) * 7.0 + 0.67
        c_rock = _sample_1d(crest_f, u_c)
        w1 = _fbm1(theta, [(3, 0.40, 1.4), (6, 0.26, 0.3), (11, 0.16, 2.8)])
        ridge = _ridged1(theta, [(4.5, 0.58, 0.8), (9, 0.32, 2.1), (17, 0.18, 0.4)])
        h = (44.0 + 18.0 * north + 18.0 * (w1 * 0.5 + 0.5) + 18.0 * ridge + 5.5 * c_rock) * (1.0 - 0.38 * nile)
        h = max(28.0, h)

        rib = _ridged1(theta, [(7, 0.55, 2.0), (15, 0.38, 0.5)]) - 0.45
        spur1 = 18.0 * _sample_2d(face_f, u_c, 0.35) + 22.0 * rib
        spur2 = 24.0 * _sample_2d(face_f, u_c, 0.75) + 28.0 * rib

        return [
            (558.0 + spur1 * 0.35, -28.0,    0.00, mod_col(far_base, u_c, 0.10, 0.45, 0.82)),
            (614.0 + spur1 * 0.80, h * 0.40, 0.38, mod_col(far_base, u_c, 0.34, 0.55, 0.82)),
            (640.0 + spur2 * 1.00, h * 0.76, 0.74, mod_col(far_mid,  u_c, 0.64, 0.60, 0.83)),
            (668.0 + spur2 * 0.90, h * 0.95, 0.94, mod_col(far_peak, u_c, 0.86, 0.55, 0.84)),
            (704.0 + spur2 * 0.55, h,        1.00, mod_col(far_peak, u_c, 0.95, 0.50, 0.84)),
            (758.0 + spur1 * 0.25, h * 0.62, 0.60, mod_col(far_mid,  u_c, 0.55, 0.45, 0.83)),
            (814.0,                -32.0,    0.00, mod_col(far_base, u_c, 0.15, 0.40, 0.82)),
        ]

    _build_ring(bm, uvl, coll, segs, 6.0, layer0, 0.0, smooth_passes=2, min_dr=7.0)
    _build_ring(bm, uvl, coll, segs, 3.2, layer1, 0.5, smooth_passes=1, min_dr=8.0)
    _build_ring(bm, uvl, coll, segs, 2.2, layer2, 1.0, smooth_passes=2, min_dr=12.0)

    bm.normal_update()
    me = bpy.data.meshes.new('backdrop_hills')
    bm.to_mesh(me)
    bm.free()

    mat = bpy.data.materials.new('env_backdrop_hills')
    mat.use_nodes = True
    nt = mat.node_tree
    pbr = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = 'Color'
    nt.links.new(vc.outputs['Color'], pbr.inputs['Base Color'])
    pbr.inputs['Roughness'].default_value = 0.98
    me.materials.append(mat)

    obj = bpy.data.objects.new('backdrop_hills', me)
    bpy.context.scene.collection.objects.link(obj)

    tris = lib.tri_count(obj)
    if tris > MAX_TRIS:
        raise RuntimeError(f'backdrop_hills: tris {tris} > {MAX_TRIS}')

    out_path = lib.OUT_MODELS / 'backdrop_hills.glb'
    nbytes = lib.export_textured_glb(out_path, [obj], embed_images=False)
    print(f'[v4/horizon] backdrop_hills tris={tris}/{MAX_TRIS}  {nbytes/1024:5.1f}KB', flush=True)


def main():
    build_horizon()
    if '--sheet' in sys.argv:
        models = [
            'palm_a', 'palm_b', 'palm_c', 'palm_d',
            'sycamore_a', 'sycamore_b', 'acacia', 'bush_a',
            'bush_b', 'boulder', 'rock_small', 'backdrop_hills',
        ]
        lib.render_m4_sheet(models, lib.PREVIEWS / 'M4_models_sheet.png')


if __name__ == '__main__':
    main()
