"""Procedural painterly WebP texture atlas generator for Environment v3 (`textures.py`).

Generates deterministic, brush-stroked storybook-naturalistic WebP atlases across all 3
quality tiers (`public/textures/env/{512,1024,2048}/`):
  - 512/  (core precached for Lite/Low): `foliage_albedo.webp`, `arch_albedo.webp`
  - 1024/ & 2048/ (lazy-loaded for Med/High/Ultra, excluded from core PWA precache):
      `foliage_albedo.webp`, `foliage_normal.webp`,
      `arch_albedo.webp`, `arch_orm.webp`, `arch_normal.webp`,
      `terrain_detail_albedo.webp`, `terrain_detail_normal.webp`, `terrain_detail_rough.webp`

Every alpha-cutout atlas performs multi-pass color dilation into transparent pixels so
GPU mipmapping NEVER produces dark halos around fronds, leaves, or blossoms at distance.

Foliage Atlas UV Layout (OpenGL/glTF origin = bottom-left (0,0) -> top-right (1,1)):
  PALM_FROND    : (0.000, 0.500, 0.500, 1.000)  # arched feathery green date palm frond (alpha)
  PALM_DRY      : (0.000, 0.000, 0.250, 0.500)  # dry golden-straw skirt palm frond (alpha)
  BARK_PALM     : (0.250, 0.000, 0.375, 0.500)  # diamond-boot fibrous palm bark (opaque, V-tile)
  BARK_WOOD     : (0.375, 0.000, 0.500, 0.500)  # gnarled sycamore/acacia bark (opaque, V-tile)
  SYCAMORE_LEAF : (0.500, 0.500, 0.750, 1.000)  # lush Ghibli broad leaf cluster card (alpha)
  ACACIA_LEAF   : (0.750, 0.500, 1.000, 1.000)  # airy desert acacia bipinnate cluster (alpha)
  BOUGAINVILLEA : (0.500, 0.000, 0.750, 0.500)  # magenta/coral bougainvillea vine card (alpha)
  PAPYRUS       : (0.750, 0.250, 0.875, 0.500)  # Nile papyrus radial filament umbel (alpha)
  LOTUS         : (0.875, 0.250, 1.000, 0.500)  # notched emerald lotus pad + veins (alpha)
  WILDFLOWER    : (0.750, 0.000, 0.875, 0.250)  # lush wildflower sprig cluster (alpha)
  CROP_CLOVER   : (0.875, 0.000, 1.000, 0.250)  # leafy berseem/cotton foliage cluster (alpha)
"""
from pathlib import Path
import math
import random

import numpy as np

try:
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    Image = ImageDraw = ImageFilter = None  # Blender embedded Python imports only FOLIAGE_UV

ROOT = Path(__file__).resolve().parents[3]
OUT_TEX = ROOT / 'public' / 'textures' / 'env'

# Shared UV rects (u0, v0, u1, v1) in glTF bottom-left coordinates (imported by foliage.py & crops.py)
FOLIAGE_UV = {
    'palm_frond':    (0.000, 0.500, 0.500, 1.000),
    'palm_dry':      (0.000, 0.000, 0.250, 0.500),
    'bark_palm':     (0.250, 0.000, 0.375, 0.500),
    'bark_wood':     (0.375, 0.000, 0.500, 0.500),
    'sycamore_leaf': (0.500, 0.500, 0.750, 1.000),
    'acacia_leaf':   (0.750, 0.500, 1.000, 1.000),
    'bougainvillea': (0.500, 0.000, 0.750, 0.500),
    'papyrus':       (0.750, 0.250, 0.875, 0.500),
    'lotus':         (0.875, 0.250, 1.000, 0.500),
    'wildflower':    (0.750, 0.000, 0.875, 0.250),
    'crop_clover':   (0.875, 0.045, 0.962, 0.250),
}


def _uv_to_px(rect, S):
    """Convert glTF bottom-left (u0, v0, u1, v1) to PIL top-left (x0, y0, x1, y1)."""
    u0, v0, u1, v1 = rect
    return (int(round(u0 * S)), int(round((1.0 - v1) * S)), int(round(u1 * S)), int(round((1.0 - v0) * S)))


def _clamp_rgb(r, g, b, a=255):
    return (max(0, min(255, int(r))), max(0, min(255, int(g))), max(0, min(255, int(b))), max(0, min(255, int(a))))


def _jitter(rgb, rnd, amp=14, warm=6):
    k = rnd.uniform(-amp, amp)
    w = rnd.uniform(-warm, warm)
    return _clamp_rgb(rgb[0] + k + w, rgb[1] + k + w * 0.25, rgb[2] + k - w * 0.5)


def _poly_leaf(cx, cy, angle, length, width, bend=0.0, segs=8):
    """Return a tapered organic leaf polygon around (cx, cy) pointing along `angle`."""
    ca, sa = math.cos(angle), math.sin(angle)
    px, py = -sa, ca
    left, right = [], []
    for i in range(segs + 1):
        t = i / segs
        w = width * (math.sin(t * math.pi) ** 0.72)
        d = t * length
        b = bend * (t * t) * length
        mx = cx + ca * d + px * b
        my = cy + sa * d + py * b
        left.append((mx + px * w, my + py * w))
        right.append((mx - px * w, my - py * w))
    return left + list(reversed(right))


def _tile_noise(w, h, scale_x, scale_y, seed=0):
    """Fast seamless periodic value noise in [0, 1] of shape (h, w)."""
    rng = np.random.default_rng(seed)
    gx, gy = max(2, int(scale_x)), max(2, int(scale_y))
    grid = rng.random((gy, gx), dtype=np.float32)
    xs = np.linspace(0, gx, w, endpoint=False, dtype=np.float32)
    ys = np.linspace(0, gy, h, endpoint=False, dtype=np.float32)
    x0 = np.floor(xs).astype(np.int32) % gx
    y0 = np.floor(ys).astype(np.int32) % gy
    x1 = (x0 + 1) % gx
    y1 = (y0 + 1) % gy
    fx = xs - np.floor(xs)
    fy = ys - np.floor(ys)
    fx = fx * fx * (3.0 - 2.0 * fx)
    fy = fy * fy * (3.0 - 2.0 * fy)
    a = grid[np.ix_(y0, x0)]
    b = grid[np.ix_(y0, x1)]
    c = grid[np.ix_(y1, x0)]
    d = grid[np.ix_(y1, x1)]
    return (a * (1.0 - fx) + b * fx) * (1.0 - fy)[:, None] + (c * (1.0 - fx) + d * fx) * fy[:, None]


def _dilate_rgba(img, passes=18):
    """Bleed opaque RGB outward into transparent pixels so mipmaps never get dark halos."""
    arr = np.array(img, dtype=np.uint8)
    rgb = arr[..., :3].astype(np.float32)
    alpha = arr[..., 3]
    mask = alpha > 24
    for _ in range(passes):
        if mask.all():
            break
        # 4-neighbor average of valid pixels
        acc = np.zeros_like(rgb)
        cnt = np.zeros(mask.shape, dtype=np.float32)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
            sm = np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
            sr = np.roll(np.roll(rgb, dy, axis=0), dx, axis=1)
            acc += sr * sm[..., None]
            cnt += sm
        fill = (~mask) & (cnt > 0)
        if not fill.any():
            break
        rgb[fill] = acc[fill] / cnt[fill, None]
        mask[fill] = True
    out = np.empty_like(arr)
    out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out[..., 3] = alpha
    return Image.fromarray(out, 'RGBA')


def _height_to_normal(height_arr, strength=2.6):
    """Convert float32 heightfield [0..1] to OpenGL tangent-space RGB normal map."""
    gx = (np.roll(height_arr, -1, axis=1) - np.roll(height_arr, 1, axis=1)) * 0.5 * strength
    gy = (np.roll(height_arr, -1, axis=0) - np.roll(height_arr, 1, axis=0)) * 0.5 * strength
    nx = -gx
    ny = gy   # +Y up in OpenGL tangent space
    nz = np.ones_like(height_arr)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-8)
    rgb = np.stack([
        (nx * inv * 0.5 + 0.5) * 255.0,
        (ny * inv * 0.5 + 0.5) * 255.0,
        (nz * inv * 0.5 + 0.5) * 255.0,
    ], axis=-1)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB')


# ---- Foliage Atlas Painter (2048px master, downsampled cleanly to 1024 & 512) ---------------
def paint_foliage_atlas(S=2048):
    """Paint the 2048px painterly foliage RGBA albedo + matching height-derived normal map."""
    albedo = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    height_img = Image.new('L', (S, S), 128)
    ad = ImageDraw.Draw(albedo)
    hd = ImageDraw.Draw(height_img)
    rnd = random.Random(301)

    # 1. PALM_FROND (0.00..0.50, 0.50..1.00) -> feathered arched green date palm frond
    x0, y0, x1, y1 = _uv_to_px(FOLIAGE_UV['palm_frond'], S)
    tw, th = x1 - x0, y1 - y0
    cx = x0 + tw * 0.5
    # Rachis central spine from bottom (y1 - margin) to top (y0 + margin)
    stem_bot = y1 - th * 0.02
    stem_top = y0 + th * 0.03
    n_pairs = 24
    for side in (-1, 1):
        for i in range(n_pairs):
            t = i / (n_pairs - 1)
            # slightly denser near tip
            ty = stem_bot + (stem_top - stem_bot) * (0.07 + 0.90 * (t ** 0.94))
            env = (math.sin(min(1.0, (t + 0.08) * 0.96) * math.pi) ** 0.58)
            lf_len = tw * (0.14 + 0.34 * env) * rnd.uniform(0.92, 1.07)
            lf_w = tw * (0.017 + 0.013 * env) * rnd.uniform(0.88, 1.12)
            # Leaflets sweep upward toward the tip and curve gracefully outward
            base_ang = (-math.pi * 0.5) + side * (1.22 - 0.88 * (t ** 1.05)) + rnd.uniform(-0.05, 0.05)
            bend = side * (0.14 + 0.08 * (1.0 - t))
            # Rich sunlit date-palm green palette (darker olive at base, vibrant sunlit tips)
            r_c = int(76 + 52 * t + rnd.uniform(-10, 10))
            g_c = int(126 + 48 * t + rnd.uniform(-12, 12))
            b_c = int(42 + 22 * t + rnd.uniform(-8, 8))
            col_dark = _clamp_rgb(r_c * 0.78, g_c * 0.82, b_c * 0.75)
            col_mid = _clamp_rgb(r_c, g_c, b_c)
            col_hi = _clamp_rgb(r_c * 1.18 + 14, g_c * 1.14 + 10, b_c * 0.95)
            poly = _poly_leaf(cx + side * tw * 0.008, ty, base_ang, lf_len, lf_w, bend=bend, segs=7)
            ad.polygon(poly, fill=col_mid)
            # Painterly sunlit edge + dark rib stroke along each leaflet
            tip_x = cx + side * tw * 0.008 + math.cos(base_ang) * lf_len * 0.88
            tip_y = ty + math.sin(base_ang) * lf_len * 0.88
            ad.line([(cx + side * tw * 0.008, ty), (tip_x, tip_y)], fill=col_hi, width=max(1, int(S * 0.0018)))
            ad.line([(cx + side * tw * 0.008, ty), (cx + side * tw * 0.008 + math.cos(base_ang) * lf_len * 0.42,
                                                     ty + math.sin(base_ang) * lf_len * 0.42)],
                    fill=col_dark, width=max(1, int(S * 0.0022)))
            hd.polygon(poly, fill=int(155 + 45 * t))
            hd.line([(cx + side * tw * 0.008, ty), (tip_x, tip_y)], fill=235, width=max(1, int(S * 0.0025)))
    # Terminal crown plume leaflets
    for ang_off in (-0.22, -0.08, 0.0, 0.08, 0.22):
        poly = _poly_leaf(cx, stem_top + th * 0.06, -math.pi * 0.5 + ang_off, tw * 0.16, tw * 0.016, bend=ang_off * 0.3, segs=5)
        ad.polygon(poly, fill=(138, 178, 72, 255))
        hd.polygon(poly, fill=210)
    # Tapered golden-olive central rachis
    for i in range(28):
        t0, t1 = i / 28, (i + 1) / 28
        yy0 = stem_bot + (stem_top - stem_bot) * t0
        yy1 = stem_bot + (stem_top - stem_bot) * t1
        rw = max(2, int(tw * (0.022 * (1.0 - t0 * 0.78))))
        rc = _clamp_rgb(138 + 26 * t0, 140 + 28 * t0, 62 + 12 * t0)
        ad.line([(cx, yy0), (cx, yy1)], fill=rc, width=rw)
        hd.line([(cx, yy0), (cx, yy1)], fill=245, width=rw)

    # 2. PALM_DRY (0.00..0.25, 0.00..0.50) -> sun-dried golden skirt palm frond
    x0, y0, x1, y1 = _uv_to_px(FOLIAGE_UV['palm_dry'], S)
    tw, th = x1 - x0, y1 - y0
    cx = x0 + tw * 0.5
    stem_bot, stem_top = y1 - th * 0.03, y0 + th * 0.05
    for side in (-1, 1):
        for i in range(18):
            t = i / 17.0
            ty = stem_bot + (stem_top - stem_bot) * (0.08 + 0.88 * t)
            env = math.sin(min(1.0, (t + 0.1) * 0.94) * math.pi) ** 0.65
            lf_len = tw * (0.14 + 0.32 * env) * rnd.uniform(0.75, 1.05)
            lf_w = tw * (0.024 + 0.014 * env)
            ang = -math.pi * 0.5 + side * (1.15 - 0.75 * t) + rnd.uniform(-0.14, 0.14)
            col = _jitter((188, 146, 82), rnd, amp=18, warm=8)
            poly = _poly_leaf(cx, ty, ang, lf_len, lf_w, bend=side * 0.22, segs=5)
            ad.polygon(poly, fill=col)
            hd.polygon(poly, fill=175)
    ad.line([(cx, stem_bot), (cx, stem_top)], fill=(142, 102, 54, 255), width=max(3, int(tw * 0.035)))
    hd.line([(cx, stem_bot), (cx, stem_top)], fill=235, width=max(3, int(tw * 0.035)))

    # 3. BARK_PALM (0.25..0.375, 0.00..0.50) -> tileable fibrous diamond-boot palm trunk bark
    x0, y0, x1, y1 = _uv_to_px(FOLIAGE_UV['bark_palm'], S)
    tw, th = x1 - x0, y1 - y0
    yy, xx = np.mgrid[0:th, 0:tw].astype(np.float32)
    u = xx / tw
    v = yy / th
    # Criss-crossing diamond leaf-base boots (seamless in u & v!)
    d1 = np.abs(np.sin((u * 4.0 + v * 12.0) * math.pi))
    d2 = np.abs(np.sin((u * 4.0 - v * 12.0) * math.pi))
    diamond = np.minimum(d1, d2) ** 0.55
    boot_step = 0.5 + 0.5 * np.sin((v * 24.0 + 0.35 * np.sin(u * 8.0 * math.pi)) * math.pi)
    fiber = _tile_noise(tw, th, 28, 10, seed=310)
    grain = _tile_noise(tw, th, 10, 32, seed=311)
    h_palm = np.clip(0.22 + 0.52 * diamond + 0.16 * boot_step + 0.12 * fiber - 0.08 * grain, 0.0, 1.0)
    r_p = 104 + 68 * h_palm + 16 * grain
    g_p = 76 + 52 * h_palm + 10 * grain
    b_p = 46 + 34 * h_palm + 6 * fiber
    palm_rgba = np.stack([np.clip(r_p, 0, 255), np.clip(g_p, 0, 255), np.clip(b_p, 0, 255), np.full_like(r_p, 255)], axis=-1).astype(np.uint8)
    albedo.paste(Image.fromarray(palm_rgba, 'RGBA'), (x0, y0))
    height_img.paste(Image.fromarray((h_palm * 255).astype(np.uint8), 'L'), (x0, y0))

    # 4. BARK_WOOD (0.375..0.50, 0.00..0.50) -> tileable gnarled sycamore / acacia furrowed bark
    x0, y0, x1, y1 = _uv_to_px(FOLIAGE_UV['bark_wood'], S)
    tw, th = x1 - x0, y1 - y0
    f1 = _tile_noise(tw, th, 14, 4, seed=312)
    f2 = _tile_noise(tw, th, 32, 10, seed=313)
    warp = _tile_noise(tw, th, 6, 8, seed=314)
    yy, xx = np.mgrid[0:th, 0:tw].astype(np.float32)
    furrow = 0.5 + 0.5 * np.sin((xx / tw * 10.0 + warp * 1.4) * math.tau)
    h_wood = np.clip(0.25 + 0.42 * (furrow ** 0.7) + 0.22 * f1 + 0.14 * f2, 0.0, 1.0)
    r_w = 88 + 66 * h_wood + 10 * f2
    g_w = 68 + 52 * h_wood + 8 * f2
    b_w = 48 + 38 * h_wood + 6 * f1
    wood_rgba = np.stack([np.clip(r_w, 0, 255), np.clip(g_w, 0, 255), np.clip(b_w, 0, 255), np.full_like(r_w, 255)], axis=-1).astype(np.uint8)
    albedo.paste(Image.fromarray(wood_rgba, 'RGBA'), (x0, y0))
    height_img.paste(Image.fromarray((h_wood * 255).astype(np.uint8), 'L'), (x0, y0))

    # 5. SYCAMORE_LEAF (0.50..0.75, 0.50..1.00) -> lush Ghibli broad leaf cluster card
    x0, y0, x1, y1 = _uv_to_px(FOLIAGE_UV['sycamore_leaf'], S)
    tw, th = x1 - x0, y1 - y0
    cx, cy = x0 + tw * 0.5, y0 + th * 0.5
    # Draw back-to-front layered clusters of broad heart/fig sycamore leaves
    # First subtle woody twigs near center
    for i in range(5):
        ang = i * math.tau / 5 + 0.3
        ad.line([(cx, cy + th * 0.06), (cx + math.cos(ang) * tw * 0.24, cy + math.sin(ang) * th * 0.24)],
                fill=(96, 72, 46, 255), width=max(2, int(tw * 0.016)))
    layers = [
        (26, 0.24, (54, 96, 36), 145),    # deep shaded interior leaves
        (32, 0.31, (82, 134, 46), 185),   # mid emerald canopy leaves
        (24, 0.27, (124, 168, 62), 225),  # sunlit warm olive-lime top leaves
    ]
    for count, rad_frac, base_rgb, h_val in layers:
        for i in range(count):
            a = i * 2.39996 + rnd.uniform(-0.35, 0.35)
            rr = math.sqrt((i + 0.5) / count) * rad_frac * tw
            lx = cx + math.cos(a) * rr
            ly = cy + math.sin(a) * rr * 0.92
            ang = a + rnd.uniform(-0.55, 0.55)
            llen = tw * rnd.uniform(0.14, 0.21)
            lw = llen * rnd.uniform(0.42, 0.56)
            col = _jitter(base_rgb, rnd, amp=15, warm=8)
            poly = _poly_leaf(lx - math.cos(ang) * llen * 0.2, ly - math.sin(ang) * llen * 0.2, ang, llen, lw, bend=rnd.uniform(-0.12, 0.12), segs=6)
            ad.polygon(poly, fill=col)
            # Soft painterly central vein highlight
            vcol = _clamp_rgb(col[0] + 24, col[1] + 22, col[2] + 8)
            ad.line([(lx, ly), (lx + math.cos(ang) * llen * 0.65, ly + math.sin(ang) * llen * 0.65)], fill=vcol, width=max(1, int(tw * 0.005)))
            hd.polygon(poly, fill=min(250, h_val + rnd.randint(-15, 18)))

    # 6. ACACIA_LEAF (0.75..1.00, 0.50..1.00) -> airy Egyptian desert acacia pinnate umbrella card
    x0, y0, x1, y1 = _uv_to_px(FOLIAGE_UV['acacia_leaf'], S)
    tw, th = x1 - x0, y1 - y0
    cx, cy = x0 + tw * 0.5, y0 + th * 0.52
    # Fine branching twigs radiating outward
    for i in range(9):
        a = i * math.tau / 9 + rnd.uniform(-0.2, 0.2)
        L = tw * rnd.uniform(0.28, 0.40)
        ex, ey = cx + math.cos(a) * L, cy + math.sin(a) * L * 0.82
        ad.line([(cx, cy), (ex, ey)], fill=(108, 86, 62, 255), width=max(1, int(tw * 0.010)))
        # Delicate paired fine olive-sage leaflets along each twig spray
        n_sprays = 7
        for j in range(1, n_sprays + 1):
            t = j / (n_sprays + 0.5)
            bx = cx + (ex - cx) * t
            by = cy + (ey - cy) * t
            for side in (-1, 1):
                sa = a + side * 0.95 + rnd.uniform(-0.2, 0.2)
                sl = tw * (0.09 + 0.06 * (1.0 - abs(t - 0.55)))
                for k in range(5):
                    kt = k / 4.5
                    px = bx + math.cos(sa) * sl * kt
                    py = by + math.sin(sa) * sl * kt
                    for ls in (-1, 1):
                        la = sa + ls * 1.05
                        col = _jitter((114, 138, 72) if t > 0.45 else (86, 112, 56), rnd, amp=14, warm=8)
                        poly = _poly_leaf(px, py, la, tw * 0.036, tw * 0.013, segs=4)
                        ad.polygon(poly, fill=col)
                        hd.polygon(poly, fill=190)
    # Tiny sunlit golden acacia blossom puffs scattered lightly across the crown
    for _ in range(14):
        a = rnd.uniform(0, math.tau)
        rr = math.sqrt(rnd.random()) * tw * 0.34
        fx, fy = cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.8
        fr = tw * rnd.uniform(0.012, 0.018)
        ad.ellipse((fx - fr, fy - fr, fx + fr, fy + fr), fill=_jitter((238, 206, 102), rnd, 12, 6))
        hd.ellipse((fx - fr, fy - fr, fx + fr, fy + fr), fill=235)

    # 7. BOUGAINVILLEA (0.50..0.75, 0.00..0.50) -> lush cascading green leaves + vibrant magenta/coral bracts
    x0, y0, x1, y1 = _uv_to_px(FOLIAGE_UV['bougainvillea'], S)
    tw, th = x1 - x0, y1 - y0
    cx, cy = x0 + tw * 0.5, y0 + th * 0.5
    # Deep green heart leaves backing the vine
    for i in range(38):
        a = i * 2.39996 + rnd.uniform(-0.3, 0.3)
        rr = math.sqrt((i + 0.5) / 38.0) * tw * 0.34
        lx, ly = cx + math.cos(a) * rr, cy + math.sin(a) * rr
        ang = a + rnd.uniform(-0.6, 0.6)
        llen = tw * rnd.uniform(0.11, 0.16)
        col = _jitter((56, 104, 42) if i < 18 else (78, 128, 52), rnd, 14, 6)
        poly = _poly_leaf(lx, ly, ang, llen, llen * 0.52, segs=5)
        ad.polygon(poly, fill=col)
        hd.polygon(poly, fill=165)
    # Cascading 3-bract papery magenta / rose-crimson bougainvillea blooms
    bloom_cols = [(216, 46, 124), (236, 78, 148), (186, 30, 108), (242, 102, 134)]
    for i in range(34):
        a = i * 2.39996 + 0.6 + rnd.uniform(-0.35, 0.35)
        rr = math.sqrt((i + 0.3) / 34.0) * tw * 0.35
        fx, fy = cx + math.cos(a) * rr, cy + math.sin(a) * rr
        bcol = _jitter(bloom_cols[i % len(bloom_cols)], rnd, 14, 8)
        b_ang = rnd.uniform(0, math.tau)
        for p in range(3):
            pa = b_ang + p * math.tau / 3.0 + rnd.uniform(-0.15, 0.15)
            blen = tw * rnd.uniform(0.065, 0.095)
            poly = _poly_leaf(fx, fy, pa, blen, blen * 0.62, segs=5)
            ad.polygon(poly, fill=bcol)
            hd.polygon(poly, fill=225)
        # Tiny cream pistil star in center of the 3 bracts
        pr = max(1, int(tw * 0.011))
        ad.ellipse((fx - pr, fy - pr, fx + pr, fy + pr), fill=(252, 240, 206, 255))

    # 8. PAPYRUS (0.75..0.875, 0.25..0.50) -> radiant Nile papyrus filament starburst umbel
    x0, y0, x1, y1 = _uv_to_px(FOLIAGE_UV['papyrus'], S)
    tw, th = x1 - x0, y1 - y0
    cx, cy = x0 + tw * 0.5, y0 + th * 0.54
    for i in range(44):
        a = i * math.tau / 44.0 + rnd.uniform(-0.04, 0.04)
        L = tw * rnd.uniform(0.32, 0.45)
        mx = cx + math.cos(a) * L * 0.55
        my = cy + math.sin(a) * L * 0.55 - th * 0.03
        ex = cx + math.cos(a) * L
        ey = cy + math.sin(a) * L + th * 0.05
        col = _jitter((118, 162, 62), rnd, 16, 10)
        ad.line([(cx, cy), (mx, my), (ex, ey)], fill=col, width=max(1, int(tw * 0.014)))
        hd.line([(cx, cy), (mx, my), (ex, ey)], fill=205, width=max(1, int(tw * 0.014)))
        # Tiny golden-straw floret tip
        tr = max(1, int(tw * 0.014))
        ad.ellipse((ex - tr, ey - tr, ex + tr, ey + tr), fill=_jitter((196, 184, 92), rnd, 14, 6))
    # Warm olive bract cup at umbel center
    cr = int(tw * 0.085)
    ad.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), fill=(86, 124, 48, 255))
    hd.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), fill=235)

    # 9. LOTUS (0.875..1.00, 0.25..0.50) -> floating notched emerald oasis lotus pad + veins
    x0, y0, x1, y1 = _uv_to_px(FOLIAGE_UV['lotus'], S)
    tw, th = x1 - x0, y1 - y0
    cx, cy = x0 + tw * 0.5, y0 + th * 0.5
    rad = tw * 0.43
    pts = []
    # Circular scalloped lotus pad with classic V-notch on one side
    for i in range(44):
        a = 0.24 + (math.tau - 0.48) * (i / 43.0)
        rr = rad * (1.0 + 0.025 * math.sin(a * 11.0))
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    pts.append((cx + rad * 0.14, cy))
    ad.polygon(pts, fill=(68, 128, 62, 255))
    hd.polygon(pts, fill=190)
    # Soft lighter inner disc & radial sunlit leaf veins
    inner_r = rad * 0.78
    ad.pieslice((cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r), start=15, end=345, fill=(84, 144, 68, 255))
    for i in range(13):
        a = 0.38 + (math.tau - 0.76) * (i / 12.0)
        ex, ey = cx + math.cos(a) * rad * 0.90, cy + math.sin(a) * rad * 0.90
        ad.line([(cx, cy), (ex, ey)], fill=(128, 174, 86, 255), width=max(1, int(tw * 0.014)))
        hd.line([(cx, cy), (ex, ey)], fill=230, width=max(1, int(tw * 0.016)))
    # Warm coppery rim edge
    ad.line(pts + [pts[0]], fill=(104, 146, 62, 255), width=max(2, int(tw * 0.018)))

    # 10. WILDFLOWER (0.75..0.875, 0.00..0.25) -> lush meadow foliage & bright Egyptian wildflowers
    x0, y0, x1, y1 = _uv_to_px(FOLIAGE_UV['wildflower'], S)
    tw, th = x1 - x0, y1 - y0
    bx, by = x0 + tw * 0.5, y1 - th * 0.04
    # Fanning grass & herb stems from bottom center
    stems = []
    for i in range(11):
        t = (i / 10.0) - 0.5
        ang = -math.pi * 0.5 + t * 1.15 + rnd.uniform(-0.08, 0.08)
        L = th * rnd.uniform(0.55, 0.84)
        poly = _poly_leaf(bx + t * tw * 0.22, by, ang, L, tw * 0.045, bend=t * 0.22, segs=5)
        ad.polygon(poly, fill=_jitter((96, 142, 54), rnd, 16, 8))
        hd.polygon(poly, fill=175)
        stems.append((bx + t * tw * 0.22 + math.cos(ang) * L * 0.92, by + math.sin(ang) * L * 0.92))
    fl_cols = [(248, 206, 68), (255, 248, 228), (224, 72, 58), (156, 118, 212)]
    for i, (fx, fy) in enumerate(stems):
        if i % 2 == 0 or i in (3, 7):
            fc = fl_cols[i % len(fl_cols)]
            pr = tw * rnd.uniform(0.055, 0.075)
            for k in range(5):
                pa = k * math.tau / 5.0 + i * 0.4
                px, py = fx + math.cos(pa) * pr * 0.72, fy + math.sin(pa) * pr * 0.72
                ad.ellipse((px - pr * 0.55, py - pr * 0.55, px + pr * 0.55, py + pr * 0.55), fill=fc)
                hd.ellipse((px - pr * 0.55, py - pr * 0.55, px + pr * 0.55, py + pr * 0.55), fill=232)
            cr = pr * 0.42
            ad.ellipse((fx - cr, fy - cr, fx + cr, fy + cr), fill=(238, 162, 38, 255))

    # 11. CROP_CLOVER (0.875..1.00, 0.00..0.25) -> lush feathery Egyptian berseem clover / crop foliage
    x0, y0, x1, y1 = _uv_to_px(FOLIAGE_UV['crop_clover'], S)
    tw, th = x1 - x0, y1 - y0
    bx, by = x0 + tw * 0.45, y1 - th * 0.05
    for i in range(18):
        t = (i / 17.0) - 0.5
        ang = -math.pi * 0.5 + t * 1.35 + rnd.uniform(-0.14, 0.14)
        L = th * rnd.uniform(0.42, 0.76)
        sx, sy = bx + t * tw * 0.22, by
        ex = sx + math.cos(ang) * L
        ey = sy + math.sin(ang) * L
        ad.line([(sx, sy), (ex, ey)], fill=(72, 128, 44, 255), width=max(1, int(tw * 0.016)))
        # 3-leaf clover rosette at each stem tip
        for k in range(3):
            la = ang + (k - 1) * 0.95
            col = _jitter((84, 154, 54) if i % 2 else (112, 174, 68), rnd, 14, 6)
            poly = _poly_leaf(ex, ey, la, tw * 0.13, tw * 0.072, segs=5)
            ad.polygon(poly, fill=col)
            hd.polygon(poly, fill=195)
    # A few tiny ivory berseem clover blossom heads on top
    for i in range(5):
        fx = x0 + tw * (0.18 + 0.52 * (i / 4.0)) + rnd.uniform(-tw * 0.04, tw * 0.04)
        fy = y0 + th * rnd.uniform(0.16, 0.34)
        fr = tw * 0.042
        ad.ellipse((fx - fr, fy - fr * 1.2, fx + fr, fy + fr * 1.2), fill=(246, 242, 224, 255))
        hd.ellipse((fx - fr, fy - fr * 1.2, fx + fr, fy + fr * 1.2), fill=240)

    # Pure-white opaque neutral UV swatch in the very bottom-right corner (u: 0.97..1.0, v: 0.0..0.03)
    # so solid vertex-colored accents (cotton bolls, lotus petals, papyrus stems, date bunches, pots)
    # share the exact same single foliage atlas draw call with zero hue shift!
    sw = max(16, S // 32)
    ad.rectangle((S - sw, S - sw, S, S), fill=(255, 255, 255, 255))
    hd.rectangle((S - sw, S - sw, S, S), fill=128)

    # Slight painterly softening of height map before deriving normal map, then dilate RGB into alpha=0
    height_smooth = height_img.filter(ImageFilter.GaussianBlur(radius=max(1.0, S / 1024.0)))
    h_arr = np.array(height_smooth, dtype=np.float32) / 255.0
    normal_img = _height_to_normal(h_arr, strength=2.8)
    albedo_bled = _dilate_rgba(albedo, passes=24)
    return albedo_bled, normal_img


# ---- Architecture Atlas (2×2 painterly Nile mudbrick, lime plaster, cedar timber, limestone) --
def paint_arch_atlas(S=2048):
    """Paint shared 2×2 architecture PBR atlas: lime plaster, mudbrick, weathered timber, limestone."""
    h = S // 2
    albedo = np.zeros((S, S, 3), dtype=np.float32)
    height = np.zeros((S, S), dtype=np.float32)
    rough = np.full((S, S), 0.90, dtype=np.float32)
    ao = np.ones((S, S), dtype=np.float32)

    # Q0 (top-left): Hand-troweled warm Egyptian lime plaster (subtle brush/trowel undulations)
    n1 = _tile_noise(h, h, 8, 8, 401)
    n2 = _tile_noise(h, h, 24, 24, 402)
    n3 = _tile_noise(h, h, 64, 64, 403)
    hp = 0.5 * n1 + 0.32 * n2 + 0.18 * n3
    albedo[:h, :h, 0] = 228 + (hp - 0.5) * 28
    albedo[:h, :h, 1] = 208 + (hp - 0.5) * 26
    albedo[:h, :h, 2] = 172 + (hp - 0.5) * 22
    height[:h, :h] = hp * 0.55
    rough[:h, :h] = 0.88 + 0.08 * n2
    ao[:h, :h] = 0.90 + 0.10 * hp

    # Q1 (top-right): Sun-baked Nile mudbrick plaster with warm straw flecks & subtle courses
    yy, xx = np.mgrid[0:h, 0:h].astype(np.float32)
    row = np.floor(yy / (h / 12.0))
    bx = (xx / (h / 6.0) + (row % 2) * 0.5) % 1.0
    by = (yy / (h / 12.0)) % 1.0
    mortar = (np.minimum(bx, 1.0 - bx) < 0.05) | (np.minimum(by, 1.0 - by) < 0.09)
    nm = _tile_noise(h, h, 14, 14, 404)
    nf = _tile_noise(h, h, 48, 48, 405)
    hm = np.where(mortar, 0.25 + 0.15 * nf, 0.65 + 0.25 * nm + 0.10 * nf)
    albedo[:h, h:, 0] = 186 + (hm - 0.5) * 44
    albedo[:h, h:, 1] = 138 + (hm - 0.5) * 36
    albedo[:h, h:, 2] = 94 + (hm - 0.5) * 28
    height[:h, h:] = hm
    rough[:h, h:] = 0.93 + 0.05 * nf
    ao[:h, h:] = np.where(mortar, 0.72, 0.92 + 0.08 * nm)

    # Q2 (bottom-left): Weathered Egyptian cedar timber planks
    gw = _tile_noise(h, h, 6, 48, 406)
    g2 = _tile_noise(h, h, 18, 96, 407)
    plank_seam = np.abs(((xx / (h / 6.0)) % 1.0) - 0.5) > 0.47
    hw = np.where(plank_seam, 0.18, 0.55 + 0.30 * gw + 0.15 * g2)
    albedo[h:, :h, 0] = 142 + (hw - 0.5) * 52
    albedo[h:, :h, 1] = 98 + (hw - 0.5) * 38
    albedo[h:, :h, 2] = 58 + (hw - 0.5) * 24
    height[h:, :h] = hw
    rough[h:, :h] = 0.84 + 0.10 * g2
    ao[h:, :h] = np.where(plank_seam, 0.62, 0.88 + 0.12 * gw)

    # Q3 (bottom-right): Dressed warm Egyptian limestone ashlar blocks
    srow = np.floor(yy / (h / 8.0))
    sx = (xx / (h / 4.0) + (srow % 2) * 0.5) % 1.0
    sy = (yy / (h / 8.0)) % 1.0
    s_joint = (np.minimum(sx, 1.0 - sx) < 0.04) | (np.minimum(sy, 1.0 - sy) < 0.06)
    ns = _tile_noise(h, h, 12, 12, 408)
    ns2 = _tile_noise(h, h, 40, 40, 409)
    hs = np.where(s_joint, 0.20, 0.68 + 0.22 * ns + 0.10 * ns2)
    albedo[h:, h:, 0] = 204 + (hs - 0.5) * 42
    albedo[h:, h:, 1] = 182 + (hs - 0.5) * 38
    albedo[h:, h:, 2] = 144 + (hs - 0.5) * 32
    height[h:, h:] = hs
    rough[h:, h:] = 0.89 + 0.08 * ns2
    ao[h:, h:] = np.where(s_joint, 0.66, 0.90 + 0.10 * ns)

    alb_img = Image.fromarray(np.clip(albedo, 0, 255).astype(np.uint8), 'RGB')
    orm = np.stack([ao * 255.0, rough * 255.0, np.zeros_like(ao)], axis=-1)
    orm_img = Image.fromarray(np.clip(orm, 0, 255).astype(np.uint8), 'RGB')
    nrm_img = _height_to_normal(height, strength=3.0)
    return alb_img, orm_img, nrm_img


# ---- Terrain Detail Pack (seamless painterly earth/sand/grass micro-relief) -----------------
def paint_terrain_detail(S=1024):
    """Paint seamless tileable painterly terrain micro-detail albedo, normal, and roughness."""
    n1 = _tile_noise(S, S, 8, 8, 501)
    n2 = _tile_noise(S, S, 24, 24, 502)
    n3 = _tile_noise(S, S, 72, 72, 503)
    h = np.clip(0.45 * n1 + 0.35 * n2 + 0.20 * n3, 0.0, 1.0)
    # Neutral-centered warm painterly grain (for subtle multiplicative tint)
    albedo = np.stack([
        228 + (h - 0.5) * 36,
        224 + (h - 0.5) * 34,
        216 + (h - 0.5) * 30,
    ], axis=-1)
    rough = np.clip((0.86 + 0.12 * n2) * 255.0, 0, 255).astype(np.uint8)
    alb_img = Image.fromarray(np.clip(albedo, 0, 255).astype(np.uint8), 'RGB')
    nrm_img = _height_to_normal(h, strength=2.2)
    rgh_img = Image.fromarray(rough, 'L')
    return alb_img, nrm_img, rgh_img


def _save_webp(img, path, quality=86, resize=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    out = img.resize((resize, resize), Image.Resampling.LANCZOS) if (resize and img.width != resize) else img
    out.save(path, format='WEBP', quality=quality, method=5)
    return path.stat().st_size


def build_all_textures():
    """Bake all 3 quality tiers (512, 1024, 2048) and return a size summary dict."""
    f_alb, f_nrm = paint_foliage_atlas(2048)
    a_alb, a_orm, a_nrm = paint_arch_atlas(2048)
    t_alb, t_nrm, t_rgh = paint_terrain_detail(1024)

    report = {}
    for res in (512, 1024, 2048):
        d = OUT_TEX / str(res)
        q_alb = 82 if res == 512 else 88
        q_nrm = 88
        sizes = {}
        # 512 core tier: albedo atlases only (Lite never downloads normals/ORM!)
        sizes['foliage_albedo.webp'] = _save_webp(f_alb, d / 'foliage_albedo.webp', quality=q_alb, resize=res)
        sizes['arch_albedo.webp'] = _save_webp(a_alb, d / 'arch_albedo.webp', quality=q_alb, resize=res)
        if res >= 1024:
            sizes['foliage_normal.webp'] = _save_webp(f_nrm, d / 'foliage_normal.webp', quality=q_nrm, resize=res)
            sizes['arch_orm.webp'] = _save_webp(a_orm, d / 'arch_orm.webp', quality=86, resize=res)
            sizes['arch_normal.webp'] = _save_webp(a_nrm, d / 'arch_normal.webp', quality=q_nrm, resize=res)
            t_res = min(res, 1024)
            sizes['terrain_detail_albedo.webp'] = _save_webp(t_alb, d / 'terrain_detail_albedo.webp', quality=84, resize=t_res)
            sizes['terrain_detail_normal.webp'] = _save_webp(t_nrm, d / 'terrain_detail_normal.webp', quality=88, resize=t_res)
            sizes['terrain_detail_rough.webp'] = _save_webp(t_rgh, d / 'terrain_detail_rough.webp', quality=84, resize=t_res)
        report[str(res)] = {k: round(v / 1024.0, 1) for k, v in sizes.items()}
    return report


if __name__ == '__main__':
    import json
    rep = build_all_textures()
    print('BAKED_TEXTURES', json.dumps(rep, indent=2))
