"""Process cached Poly Haven texture sets into resized WebP PBR maps (diff, nor, arm).

Usage:
  python3 -I tools/polyhaven/process_textures.py
"""
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = Path(__file__).resolve().parent / 'manifest.json'
CACHE_DIR = ROOT / '.cache' / 'polyhaven'
OUT_ROOT = ROOT / 'public' / 'textures' / 'v4'

TIER_TO_SIZE = {
  'lite': 512,
  'medium': 1024,
  'high': 2048,
}

# Quality profiles keep Lite (512) compact within the 6 MB precache budget while staying crisp.
QUALITY = {
  512: {'diff': 75, 'nor': 78, 'arm': 74, 'method': 6},
  1024: {'diff': 82, 'nor': 85, 'arm': 80, 'method': 4},
  2048: {'diff': 84, 'nor': 86, 'arm': 82, 'method': 4},
}


def find_map(adir, stem):
  for ext in ('png', 'jpg', 'jpeg'):
    p = adir / f'{stem}.{ext}'
    if p.exists():
      return p
  return None


def load_rgb(path):
  with Image.open(path) as im:
    return im.convert('RGB')


def load_normal_gl(adir):
  p = find_map(adir, 'nor_gl')
  if p:
    return load_rgb(p)
  p = find_map(adir, 'nor_dx')
  if not p:
    raise FileNotFoundError(f'Missing normal map in {adir}')
  im = load_rgb(p)
  r, g, b = im.split()
  g_gl = g.point(lambda v: 255 - v)
  return Image.merge('RGB', (r, g_gl, b))


def load_arm(adir, fallback_size):
  p = find_map(adir, 'arm')
  if p:
    return load_rgb(p)
  ao_p = find_map(adir, 'AO')
  rough_p = find_map(adir, 'Rough')
  metal_p = find_map(adir, 'Metal')
  ao = Image.open(ao_p).convert('L') if ao_p else Image.new('L', fallback_size, 255)
  rough = Image.open(rough_p).convert('L') if rough_p else Image.new('L', fallback_size, 200)
  metal = Image.open(metal_p).convert('L') if metal_p else Image.new('L', fallback_size, 0)
  size = rough.size
  if ao.size != size:
    ao = ao.resize(size, Image.Resampling.LANCZOS)
  if metal.size != size:
    metal = metal.resize(size, Image.Resampling.LANCZOS)
  return Image.merge('RGB', (ao, rough, metal))


def main():
  manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
  textures = [a for a in manifest['assets'] if a['type'] == 'texture']

  lite_bytes = 0
  for entry in textures:
    aid = entry['id']
    adir = CACHE_DIR / aid
    diff_path = find_map(adir, 'Diffuse')
    if not diff_path:
      raise FileNotFoundError(f'Missing Diffuse map for {aid} in {adir}')
    diff = load_rgb(diff_path)
    nor = load_normal_gl(adir)
    arm = load_arm(adir, diff.size)

    sizes = sorted({TIER_TO_SIZE[t] for t in entry.get('tiers', ['lite', 'medium', 'high']) if t in TIER_TO_SIZE})
    per_size_kb = []
    for sz in sizes:
      out_dir = OUT_ROOT / str(sz)
      out_dir.mkdir(parents=True, exist_ok=True)
      q = QUALITY[sz]
      maps = {'diff': diff, 'nor': nor, 'arm': arm}
      sz_total = 0
      for key, img in maps.items():
        resized = img if img.size == (sz, sz) else img.resize((sz, sz), Image.Resampling.LANCZOS)
        out_path = out_dir / f'{aid}_{key}.webp'
        resized.save(out_path, format='WEBP', quality=q[key], method=q['method'])
        sz_total += out_path.stat().st_size
      if sz == 512:
        lite_bytes += sz_total
      per_size_kb.append(f'{sz}:{sz_total / 1024:.0f}KB')
    print(f'[tex] {aid:26s} ' + '  '.join(per_size_kb))

  print(f'Total 512 (Lite) textures: {lite_bytes / 1048576:.2f} MB across {len(textures)} sets')


if __name__ == '__main__':
  main()
