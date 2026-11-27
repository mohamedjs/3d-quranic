"""Generate seamlessly tileable 512 and 1024 OpenGL water normal maps from a band-limited FFT wave spectrum.

Usage:
  blender -b --factory-startup --python tools/polyhaven/process_water.py
"""
import math
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / 'public' / 'textures' / 'v4'

SEED = 42071
BASE_RES = 1024
MAX_512_BYTES = 200 * 1024


def periodic_bilinear(field, u_coords, v_coords):
  """Sample a 2D periodic array at fractional (col=u, row=v) pixel coordinates."""
  h, w = field.shape
  u = np.mod(u_coords, w)
  v = np.mod(v_coords, h)
  x0 = np.floor(u).astype(np.int32)
  y0 = np.floor(v).astype(np.int32)
  x1 = (x0 + 1) % w
  y1 = (y0 + 1) % h
  fx = u - x0
  fy = v - y0
  c00 = field[y0, x0]
  c10 = field[y0, x1]
  c01 = field[y1, x0]
  c11 = field[y1, x1]
  return (c00 * (1.0 - fx) + c10 * fx) * (1.0 - fy) + (c01 * (1.0 - fx) + c11 * fx) * fy


def synthesize_water_normals(n=BASE_RES, seed=SEED):
  """Synthesize an isotropic multi-scale OpenGL normal map (H, W, 3) in [-1, 1] via 2D FFT."""
  rng = np.random.default_rng(seed)

  # Integer wave numbers in cycles per tile: axis 1 = u (+X), axis 0 = v (+Y in OpenGL / Blender).
  kx = np.fft.fftfreq(n, d=1.0 / n)
  ky = np.fft.fftfreq(n, d=1.0 / n)
  KX, KY = np.meshgrid(kx, ky)
  K = np.hypot(KX, KY)

  # Band-limited isotropic capillary-gravity spectrum:
  # - High-pass cuts k < ~4 cycles/tile so there is no obvious tile-scale repeating lump.
  # - Power-law k^-2.18 gives natural multi-scale wave slopes (broad swells -> crisp capillary ripples).
  # - Smooth Gaussian low-pass cuts above k ~ 76 cycles/tile to avoid Nyquist grid/shimmer at 512/1024.
  hp = 1.0 - np.exp(-np.power(K / 4.8, 4.0))
  pow_law = np.where(K > 0.0, np.power(np.maximum(K, 1e-6), -2.18), 0.0)
  lp = np.exp(-np.power(K / 76.0, 2.0))
  amp = hp * pow_law * lp
  amp[0, 0] = 0.0

  # FFT of real Gaussian white noise has exact Hermitian symmetry -> strictly real periodic fields.
  white = rng.standard_normal((n, n))
  H = np.fft.fft2(white) * amp

  # Exact spectral derivatives dh/du and dh/dv
  dh_du = np.fft.ifft2(1j * (2.0 * math.pi * KX) * H).real
  dh_dv = np.fft.ifft2(1j * (2.0 * math.pi * KY) * H).real

  # Gentle periodic Gerstner-like horizontal warp gives rounded troughs and crisper organic crests.
  inv_k = np.where(K > 0.0, 1.0 / np.maximum(K, 1e-6), 0.0)
  disp_u = np.fft.ifft2(1j * (KX * inv_k) * H).real
  disp_v = np.fft.ifft2(1j * (KY * inv_k) * H).real
  d_rms = math.sqrt(float(np.mean(disp_u * disp_u + disp_v * disp_v)))
  shift_u = (disp_u / max(d_rms, 1e-8)) * 2.1
  shift_v = (disp_v / max(d_rms, 1e-8)) * 2.1

  cols, rows = np.meshgrid(np.arange(n, dtype=np.float64), np.arange(n, dtype=np.float64))
  dh_du = periodic_bilinear(dh_du, cols - shift_u, rows - shift_v)
  dh_dv = periodic_bilinear(dh_dv, cols - shift_u, rows - shift_v)

  # Normalize slope RMS for rich 8-bit precision with smooth outlier rolloff.
  s_rms = math.sqrt(float(np.mean(dh_du * dh_du + dh_dv * dh_dv)))
  scale = 0.36 / max(s_rms, 1e-8)
  sx = 1.65 * np.tanh((dh_du * scale) / 1.65)
  sy = 1.65 * np.tanh((dh_dv * scale) / 1.65)

  # OpenGL tangent-space normal: +X right (col), +Y up (row, v=0 bottom -> v=1 top), +Z out.
  nx = -sx
  ny = -sy
  nz = np.ones_like(nx)
  inv_len = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
  normals = np.stack((nx * inv_len, ny * inv_len, nz * inv_len), axis=-1).astype(np.float32)
  return normals


def downsample_normals(normals):
  """2x2 area-average normal vectors and re-normalize to unit length."""
  h, w, _ = normals.shape
  avg = normals.reshape(h // 2, 2, w // 2, 2, 3).mean(axis=(1, 3))
  lengths = np.linalg.norm(avg, axis=-1, keepdims=True)
  return (avg / np.maximum(lengths, 1e-6)).astype(np.float32)


def verify_normals(normals, label):
  """Assert seamless periodicity and isotropy."""
  dx_int = float(np.mean(np.abs(normals[:, 1:, :] - normals[:, :-1, :])))
  dx_wrap = float(np.mean(np.abs(normals[:, 0, :] - normals[:, -1, :])))
  dy_int = float(np.mean(np.abs(normals[1:, :, :] - normals[:-1, :, :])))
  dy_wrap = float(np.mean(np.abs(normals[0, :, :] - normals[-1, :, :])))
  rx = dx_wrap / max(dx_int, 1e-8)
  ry = dy_wrap / max(dy_int, 1e-8)
  rms_x = math.sqrt(float(np.mean(normals[:, :, 0] ** 2)))
  rms_y = math.sqrt(float(np.mean(normals[:, :, 1] ** 2)))
  iso = rms_x / max(rms_y, 1e-8)
  if rx > 1.35 or ry > 1.35:
    raise RuntimeError(f'{label}: tile seam check failed (wrap/interior ratio x={rx:.3f}, y={ry:.3f})')
  if not (0.85 <= iso <= 1.18):
    raise RuntimeError(f'{label}: isotropy check failed (rms_x/rms_y={iso:.3f})')
  return rms_x, rms_y, rx, ry


def save_normal_webp(normals, out_path, quality):
  """Encode unit normals [-1, 1] into linear [0, 1] WebP without colour-management gamma."""
  h, w, _ = normals.shape
  rgba = np.ones((h, w, 4), dtype=np.float32)
  rgba[:, :, :3] = np.clip(normals * 0.5 + 0.5, 0.0, 1.0)

  sc = bpy.context.scene
  sc.view_settings.view_transform = 'Raw'
  sc.view_settings.look = 'None'
  sc.view_settings.exposure = 0.0
  sc.view_settings.gamma = 1.0
  sc.render.image_settings.file_format = 'WEBP'
  sc.render.image_settings.color_mode = 'RGB'
  sc.render.image_settings.quality = quality

  out_path.parent.mkdir(parents=True, exist_ok=True)
  img = bpy.data.images.new(out_path.stem, width=w, height=h, alpha=False, float_buffer=False)
  img.colorspace_settings.name = 'Non-Color'
  img.pixels.foreach_set(rgba.ravel())
  img.save_render(str(out_path), scene=sc)
  bpy.data.images.remove(img)


def main():
  nor_1024 = synthesize_water_normals(BASE_RES, SEED)
  nor_512 = downsample_normals(nor_1024)

  m1024 = verify_normals(nor_1024, '1024')
  m512 = verify_normals(nor_512, '512')

  p1024 = OUT_ROOT / '1024' / 'water_nor.webp'
  p512 = OUT_ROOT / '512' / 'water_nor.webp'

  save_normal_webp(nor_1024, p1024, quality=85)

  q512 = 82
  while True:
    save_normal_webp(nor_512, p512, quality=q512)
    if p512.stat().st_size <= MAX_512_BYTES or q512 <= 60:
      break
    q512 -= 4

  if p512.stat().st_size > MAX_512_BYTES:
    raise RuntimeError(f'512 water_nor.webp exceeds 200 KB budget: {p512.stat().st_size} bytes')

  print(
    f'[water] 1024={p1024.stat().st_size / 1024:.1f}KB '
    f'(rms={m1024[0]:.3f}/{m1024[1]:.3f}, wrap={m1024[2]:.2f}/{m1024[3]:.2f})  '
    f'512={p512.stat().st_size / 1024:.1f}KB q={q512} '
    f'(rms={m512[0]:.3f}/{m512[1]:.3f}, wrap={m512[2]:.2f}/{m512[3]:.2f})'
  )


if __name__ == '__main__':
  main()
