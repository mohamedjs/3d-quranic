"""Fetch Poly Haven CC0 assets declared in tools/polyhaven/manifest.json.

Usage:
  python3 -I tools/polyhaven/fetch.py [--credits-only]
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = Path(__file__).resolve().parent / 'manifest.json'
CREDITS_PATH = Path(__file__).resolve().parent / 'CREDITS.md'
CACHE_DIR = ROOT / '.cache' / 'polyhaven'
API_BASE = 'https://api.polyhaven.com'
HEADERS = {'User-Agent': 'asset-fetcher/1.0'}

ALLOWED_RESOLUTIONS = {'1k', '2k'}

# Whole-word content filter deny list (figures, weapons, church/gothic, alcohol, signage, modern-industrial).
DENY_TOKENS = {
  'statue', 'statues', 'bust', 'busts', 'sculpture', 'sculptures', 'figurine', 'mannequin',
  'human', 'person', 'people', 'skull', 'skeleton', 'animal', 'animals', 'portrait',
  'weapon', 'weapons', 'cannon', 'gun', 'guns', 'firearm', 'firearms', 'rifle', 'pistol',
  'ammo', 'ammunition', 'military', 'sword', 'saber', 'grenade', 'explosive',
  'church', 'gothic', 'cathedral', 'chapel', 'crucifix', 'grave', 'tomb', 'cemetery',
  'alcohol', 'wine', 'beer', 'whiskey', 'vodka', 'liquor', 'champagne', 'brewery', 'pub',
  'signage', 'neon', 'billboard', 'traffic', 'roadsign',
  'industrial', 'plastic', 'propane', 'cctv', 'asphalt', 'fuel', 'oil', 'modern',
  'electronic', 'electronics', 'electric', 'wheelchair', 'hospital', 'vehicle', 'car', 'truck',
}

DENY_PHRASES = (
  'power box', 'oil drum', 'fuel barrel', 'explosive barrel', 'metal rack', 'traffic sign',
  'human face', 'human head', 'animal figure',
)


def tokenize(text):
  return set(re.findall(r'[a-z0-9]+', str(text).lower().replace('_', ' ').replace('-', ' ')))


def check_content_filter(asset_id, info):
  fields = [asset_id, info.get('name', '')]
  fields.extend(info.get('categories', []))
  fields.extend(info.get('tags', []))
  joined = ' '.join(str(x).lower() for x in fields)
  for phrase in DENY_PHRASES:
    if phrase in joined:
      raise SystemExit(f'Content filter rejected {asset_id!r}: matched phrase {phrase!r}')
  tokens = set()
  for f in fields:
    tokens |= tokenize(f)
  bad = sorted(tokens & DENY_TOKENS)
  if bad:
    raise SystemExit(f'Content filter rejected {asset_id!r}: matched tokens {bad}')


def file_md5(path):
  h = hashlib.md5()
  with path.open('rb') as f:
    for chunk in iter(lambda: f.read(1 << 20), b''):
      h.update(chunk)
  return h.hexdigest()


def api_get(session, endpoint, cache_file):
  if cache_file.exists():
    return json.loads(cache_file.read_text(encoding='utf-8'))
  r = session.get(f'{API_BASE}/{endpoint}', headers=HEADERS, timeout=30)
  r.raise_for_status()
  data = r.json()
  cache_file.parent.mkdir(parents=True, exist_ok=True)
  cache_file.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')
  return data


def download_verified(session, url, expected_md5, dest):
  dest.parent.mkdir(parents=True, exist_ok=True)
  if dest.exists() and file_md5(dest) == expected_md5:
    return False
  tmp = dest.with_suffix(dest.suffix + '.part')
  h = hashlib.md5()
  with session.get(url, headers=HEADERS, stream=True, timeout=120) as r:
    r.raise_for_status()
    with tmp.open('wb') as f:
      for chunk in r.iter_content(chunk_size=1 << 18):
        if chunk:
          f.write(chunk)
          h.update(chunk)
  got = h.hexdigest()
  if got != expected_md5:
    tmp.unlink(missing_ok=True)
    raise RuntimeError(f'MD5 mismatch for {url}: expected {expected_md5}, got {got}')
  tmp.replace(dest)
  return True


def pick_format(res_dict, preferred):
  for ext in preferred:
    if ext in res_dict and isinstance(res_dict[ext], dict) and 'url' in res_dict[ext]:
      return ext, res_dict[ext]
  raise KeyError(f'None of {preferred} available in {list(res_dict.keys())}')


def collect_downloads(entry, files_json):
  asset_id = entry['id']
  atype = entry['type']
  res = entry['resolution']
  if res not in ALLOWED_RESOLUTIONS:
    raise SystemExit(f'Refusing resolution {res!r} for {asset_id!r} (only {sorted(ALLOWED_RESOLUTIONS)} allowed)')

  plan = []  # list of (rel_path, url, md5)
  if atype == 'hdri':
    ext, spec = pick_format(files_json['hdri'][res], ('hdr', 'exr'))
    plan.append((f'{asset_id}_{res}.{ext}', spec['url'], spec['md5']))
  elif atype == 'texture':
    # Diffuse
    ext, spec = pick_format(files_json['Diffuse'][res], ('png', 'jpg'))
    plan.append((f'Diffuse.{ext}', spec['url'], spec['md5']))
    # Normal (prefer OpenGL)
    if 'nor_gl' in files_json and res in files_json['nor_gl']:
      ext, spec = pick_format(files_json['nor_gl'][res], ('png', 'jpg'))
      plan.append((f'nor_gl.{ext}', spec['url'], spec['md5']))
    elif 'nor_dx' in files_json and res in files_json['nor_dx']:
      ext, spec = pick_format(files_json['nor_dx'][res], ('png', 'jpg'))
      plan.append((f'nor_dx.{ext}', spec['url'], spec['md5']))
    else:
      raise KeyError(f'No normal map at {res} for {asset_id}')
    # ARM (or fallback to separate AO / Rough / Metal)
    if 'arm' in files_json and res in files_json['arm']:
      ext, spec = pick_format(files_json['arm'][res], ('png', 'jpg'))
      plan.append((f'arm.{ext}', spec['url'], spec['md5']))
    else:
      for ch in ('AO', 'Rough', 'Metal'):
        if ch in files_json and res in files_json[ch]:
          ext, spec = pick_format(files_json[ch][res], ('png', 'jpg'))
          plan.append((f'{ch}.{ext}', spec['url'], spec['md5']))
  elif atype == 'model':
    gltf_spec = files_json['gltf'][res]['gltf']
    root_name = Path(gltf_spec['url']).name
    plan.append((root_name, gltf_spec['url'], gltf_spec['md5']))
    seen = {root_name}
    for rel, inc in sorted(gltf_spec.get('include', {}).items()):
      plan.append((rel, inc['url'], inc['md5']))
      seen.add(rel)
    # Poly Haven's glTF bundle ships JPG diffuse maps without alpha; also fetch alpha masks when present.
    for alpha_key in ('Alpha', 'leaves_alpha'):
      if alpha_key in files_json and res in files_json[alpha_key]:
        _, spec = pick_format(files_json[alpha_key][res], ('png', 'jpg'))
        rel = f'textures/{Path(spec["url"]).name}'
        if rel not in seen:
          plan.append((rel, spec['url'], spec['md5']))
          seen.add(rel)
  else:
    raise SystemExit(f'Unknown asset type {atype!r} for {asset_id!r}')
  return plan


def write_credits(manifest_assets, infos):
  lines = [
    '# Poly Haven Assets Credits',
    '',
    'All assets below are sourced from [Poly Haven](https://polyhaven.com) under the **CC0 1.0 Universal** license (public domain; attribution given with appreciation).',
    '',
    '| Asset ID | Name | Type | Role | Author(s) | Source |',
    '|---|---|---|---|---|---|',
  ]
  for entry in manifest_assets:
    aid = entry['id']
    info = infos[aid]
    name = info.get('name', aid)
    authors = ', '.join(sorted(info.get('authors', {}).keys())) or 'Poly Haven'
    url = f'https://polyhaven.com/a/{aid}'
    lines.append(f'| `{aid}` | {name} | {entry["type"]} | {entry["role"]} | {authors} | [polyhaven.com/a/{aid}]({url}) |')
  lines.append('')
  CREDITS_PATH.write_text('\n'.join(lines), encoding='utf-8')


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument('--credits-only', action='store_true')
  args = ap.parse_args()

  manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
  assets = manifest['assets']
  session = requests.Session()
  infos = {}
  downloaded = 0
  skipped = 0

  for entry in assets:
    aid = entry['id']
    adir = CACHE_DIR / aid
    adir.mkdir(parents=True, exist_ok=True)
    info = api_get(session, f'info/{aid}', adir / '_info.json')
    check_content_filter(aid, info)
    infos[aid] = info
    if args.credits_only:
      continue
    files_json = api_get(session, f'files/{aid}', adir / '_files.json')
    plan = collect_downloads(entry, files_json)
    asset_dl = 0
    for rel, url, md5 in plan:
      if download_verified(session, url, md5, adir / rel):
        downloaded += 1
        asset_dl += 1
      else:
        skipped += 1
    status = f'downloaded {asset_dl}' if asset_dl else 'cached'
    print(f'[{entry["type"]:7s}] {aid:28s} ({len(plan)} files: {status})')

  write_credits(assets, infos)
  print(f'Done: {downloaded} downloaded, {skipped} verified/skipped. Credits written to {CREDITS_PATH.relative_to(ROOT)}')


if __name__ == '__main__':
  main()
