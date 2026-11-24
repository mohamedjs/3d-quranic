"""Headless Blender v3 build entry point for Environment v3 assets.

Usage:
  blender -b --python blender/v3/env/build_all.py -- [asset_names...]

With no keys, builds all currently implemented v3 assets (M1: backdrop_hills).
Exports Draco-6 GLBs to public/models/env/<name>.glb and writes a JSON budget report.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import landmarks
import lib

BUILDERS = {
    'backdrop_hills': landmarks.build_backdrop_hills,
}


def parse_keys():
    if '--' not in sys.argv:
        return list(BUILDERS.keys())
    args = [a for a in sys.argv[sys.argv.index('--') + 1:] if not a.startswith('-')]
    return args or list(BUILDERS.keys())


def main():
    lib.ensure_dirs()
    keys = parse_keys()
    report = []
    for key in keys:
        if key not in BUILDERS:
            raise SystemExit(f'Unknown environment v3 asset: {key}')
        lib.reset_scene()
        col = lib.make_collection(key)
        obj = BUILDERS[key](col)
        out_path = lib.OUT_MODELS / f'{key}.glb'
        size_b = lib.export_glb([obj], out_path, draco_level=6)
        info = {
            'name': key,
            'tris': lib.tri_count(obj),
            'kb': round(size_b / 1024.0, 1),
            'mats': [m.name for m in obj.data.materials],
        }
        report.append(info)
        print('BUILT_ENV', json.dumps(info), flush=True)
    lib.save_report(report)
    print('ENV_V3_BUILD_OK', len(report), flush=True)


if __name__ == '__main__':
    main()
