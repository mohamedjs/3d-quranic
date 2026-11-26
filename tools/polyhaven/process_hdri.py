"""Tonemap cached Poly Haven HDRI to 1k/2k LDR WebP equirects and extract sun.json.

Usage:
  blender -b --factory-startup --python tools/polyhaven/process_hdri.py
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = Path(__file__).resolve().parent / 'manifest.json'
CACHE_DIR = ROOT / '.cache' / 'polyhaven'
OUT_DIR = ROOT / 'public' / 'textures' / 'v4' / 'sky'


def aces_tonemap(x):
  x = np.maximum(x, 0.0)
  num = x * (2.51 * x + 0.03)
  den = x * (2.43 * x + 0.59) + 0.14
  return np.clip(num / np.maximum(den, 1e-6), 0.0, 1.0)


def linear_to_srgb(x):
  x = np.clip(x, 0.0, 1.0)
  return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


def rgb_to_hex(rgb):
  r, g, b = [int(round(float(np.clip(c, 0.0, 1.0)) * 255)) for c in rgb]
  return f'#{r:02x}{g:02x}{b:02x}'


def resize_area(img, out_h, out_w):
  h, w, c = img.shape
  if h == out_h and w == out_w:
    return img
  if h % out_h == 0 and w % out_w == 0:
    fy, fx = h // out_h, w // out_w
    return img.reshape(out_h, fy, out_w, fx, c).mean(axis=(1, 3))
  # Separable bilinear fallback for non-integer ratios
  ys = np.linspace(0, h - 1, out_h)
  xs = np.linspace(0, w - 1, out_w)
  y0 = np.floor(ys).astype(int)
  y1 = np.minimum(y0 + 1, h - 1)
  wy = (ys - y0)[:, None, None]
  tmp = img[y0] * (1.0 - wy) + img[y1] * wy
  x0 = np.floor(xs).astype(int)
  x1 = np.minimum(x0 + 1, w - 1)
  wx = (xs - x0)[None, :, None]
  return tmp[:, x0] * (1.0 - wx) + tmp[:, x1] * wx


def save_srgb_webp(srgb_rgb, out_path, quality):
  h, w, _ = srgb_rgb.shape
  rgba = np.ones((h, w, 4), dtype=np.float32)
  rgba[:, :, :3] = np.clip(srgb_rgb, 0.0, 1.0)

  sc = bpy.context.scene
  sc.view_settings.view_transform = 'Raw'
  sc.view_settings.look = 'None'
  sc.view_settings.exposure = 0.0
  sc.view_settings.gamma = 1.0
  sc.render.image_settings.file_format = 'WEBP'
  sc.render.image_settings.color_mode = 'RGB'
  sc.render.image_settings.quality = quality

  img = bpy.data.images.new(out_path.stem, width=w, height=h, alpha=False, float_buffer=False)
  img.colorspace_settings.name = 'Non-Color'
  img.pixels.foreach_set(rgba.ravel())
  img.save_render(str(out_path), scene=sc)
  bpy.data.images.remove(img)


def find_hdri_file(adir):
  for ext in ('hdr', 'exr'):
    matches = sorted(adir.glob(f'*.{ext}'))
    if matches:
      return matches[0]
  raise FileNotFoundError(f'No .hdr/.exr found in {adir}')


def main():
  manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
  hdris = [a for a in manifest['assets'] if a['type'] == 'hdri']
  if not hdris:
    raise SystemExit('No hdri entry in manifest.json')
  entry = hdris[0]
  aid = entry['id']
  src = find_hdri_file(CACHE_DIR / aid)

  bl_img = bpy.data.images.load(str(src))
  w, h = bl_img.size[0], bl_img.size[1]
  raw = np.empty(h * w * 4, dtype=np.float32)
  bl_img.pixels.foreach_get(raw)
  bpy.data.images.remove(bl_img)

  # Blender image pixels are stored bottom-to-top: row 0 is v=0 (nadir), row h-1 is v=1 (zenith).
  rgb = raw.reshape(h, w, 4)[:, :, :3]
  lum = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]

  # Sanity check: sky (upper rows) should be brighter than ground (lower rows).
  upper_mean = float(lum[h // 2 :, :].mean())
  lower_mean = float(lum[: h // 2, :].mean())
  if upper_mean < lower_mean:
    raise RuntimeError(f'Unexpected HDRI orientation: upper_mean={upper_mean:.3f} < lower_mean={lower_mean:.3f}')

  # Build equirectangular coordinates consistent with Three.js:
  #   u = atan2(z, x) / (2*pi) + 0.5,  v = asin(y) / pi + 0.5  (v=1 is top row)
  u = (np.arange(w, dtype=np.float64) + 0.5) / w
  v = (np.arange(h, dtype=np.float64) + 0.5) / h
  theta = (u - 0.5) * (2.0 * math.pi)
  phi = (v - 0.5) * math.pi
  cos_phi = np.cos(phi)[:, None]
  sin_phi = np.sin(phi)[:, None]

  # Extract sun direction from brightest pixels in upper hemisphere (v > 0.5).
  upper_mask = v[:, None] > 0.5
  upper_lum = np.where(upper_mask, lum, 0.0)
  peak = float(upper_lum.max())
  thresh = max(peak * 0.4, float(np.quantile(lum[h // 2 :, :], 0.9995)))
  sun_mask = upper_lum >= thresh
  weights = upper_lum * cos_phi * sun_mask
  w_sum = float(weights.sum())
  dx = float((weights * (cos_phi * np.cos(theta)[None, :])).sum() / w_sum)
  dy = float((weights * sin_phi).sum() / w_sum)
  dz = float((weights * (cos_phi * np.sin(theta)[None, :])).sum() / w_sum)
  norm = math.sqrt(dx * dx + dy * dy + dz * dz)
  dx, dy, dz = dx / norm, dy / norm, dz / norm

  # Verify inverse matches Three.js equirect lookup
  u_check = math.atan2(dz, dx) / (2.0 * math.pi) + 0.5
  v_check = math.asin(max(-1.0, min(1.0, dy))) / math.pi + 0.5
  sun_col = int(np.argmax(upper_lum.max(axis=0)))
  sun_row = int(np.argmax(upper_lum.max(axis=1)))
  u_peak = (sun_col + 0.5) / w
  v_peak = (sun_row + 0.5) / h
  du = min(abs(u_check - u_peak), 1.0 - abs(u_check - u_peak))
  dv = abs(v_check - v_peak)
  if du > 0.03 or dv > 0.03:
    raise RuntimeError(f'Sun direction lookup mismatch: peak=({u_peak:.3f},{v_peak:.3f}) check=({u_check:.3f},{v_check:.3f})')

  sun_elev_deg = round(math.degrees(math.asin(max(-1.0, min(1.0, dy)))), 2)

  # Compute exposure from 90th-percentile upper-hemisphere luminance so the golden sunset
  # horizon retains warm saturation without clipping to white under ACES filmic tone mapping.
  sky_p90 = float(np.quantile(lum[h // 2 :, :], 0.90))
  exposure = round(float(np.clip(0.50 / max(sky_p90, 1e-4), 0.15, 2.0)), 3)

  # Sun color from warm solar corona / disc (linear normalized, converted to sRGB).
  dir_x = cos_phi * np.cos(theta)[None, :]
  dir_y = np.broadcast_to(sin_phi, (h, w))
  dir_z = cos_phi * np.sin(theta)[None, :]
  dot_sun = dir_x * dx + dir_y * dy + dir_z * dz
  corona_mask = (dot_sun >= math.cos(math.radians(6.0))) & (dot_sun <= math.cos(math.radians(1.0)))
  sun_rgb_lin = rgb[corona_mask].mean(axis=0) if np.any(corona_mask) else rgb[sun_mask].mean(axis=0)
  sun_rgb_lin = sun_rgb_lin / max(float(sun_rgb_lin.max()), 1e-6)
  sun_color = rgb_to_hex(linear_to_srgb(sun_rgb_lin))

  # Tonemap full HDR to LDR sRGB
  ldr_2k = linear_to_srgb(aces_tonemap(rgb * exposure))
  ldr_2k_out = resize_area(ldr_2k, 1024, 2048)
  ldr_1k_out = resize_area(ldr_2k_out, 512, 1024)

  OUT_DIR.mkdir(parents=True, exist_ok=True)
  p2k = OUT_DIR / f'{aid}_2k.webp'
  p1k = OUT_DIR / f'{aid}_1k.webp'
  save_srgb_webp(ldr_2k_out, p2k, quality=82)
  save_srgb_webp(ldr_1k_out, p1k, quality=76)

  # Sample vertical sky gradient from -10 to 90 degrees (azimuth-averaged LDR sRGB).
  elevs = [-10, 0, 5, 10, 20, 35, 55, 75, 90]
  gradient = []
  h2 = ldr_2k_out.shape[0]
  for deg in elevs:
    vf = (math.radians(deg) / math.pi) + 0.5
    row = int(np.clip(round(vf * (h2 - 1)), 0, h2 - 1))
    r0, r1 = max(0, row - 2), min(h2, row + 3)
    avg = ldr_2k_out[r0:r1, :, :].mean(axis=(0, 1))
    gradient.append({'elevationDeg': deg, 'color': rgb_to_hex(avg)})

  # Ground color from -45 to -5 degrees
  g0 = int(round((math.radians(-45) / math.pi + 0.5) * (h2 - 1)))
  g1 = int(round((math.radians(-5) / math.pi + 0.5) * (h2 - 1)))
  ground_hex = rgb_to_hex(ldr_2k_out[g0:g1, :, :].mean(axis=(0, 1)))

  sun_json = {
    'hdri': aid,
    'sunDirection': [round(dx, 5), round(dy, 5), round(dz, 5)],
    'sunColor': sun_color,
    'sunElevationDeg': sun_elev_deg,
    'exposure': exposure,
    'gradient': gradient,
    'ground': ground_hex,
  }
  (OUT_DIR / 'sun.json').write_text(json.dumps(sun_json, indent=2) + '\n', encoding='utf-8')
  print(f'[hdri] {aid}: 1k={p1k.stat().st_size / 1024:.1f}KB, 2k={p2k.stat().st_size / 1024:.1f}KB, elev={sun_elev_deg}deg, sun={sun_color}, exp={exposure}')


if __name__ == '__main__':
  main()
