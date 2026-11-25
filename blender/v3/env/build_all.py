"""Headless Blender v3 build entry point for Environment v3 assets (`build_all.py`).

Usage:
  blender -b --python blender/v3/env/build_all.py -- [asset_names...]
  blender -b --python blender/v3/env/build_all.py -- foliage     # build all M3 foliage & crops

With no keys, builds all implemented v3 assets (M1: backdrop_hills;
M2: river_bridge, footbridge, canal_bank, stream_channel;
M3: palms, sycamores, acacia, bougainvillea, bushes, lotus_pad, pot_plant, crops, grass, reeds, papyrus, wildflowers, field_bund).
Exports Draco-6 GLBs to public/models/env/<name>.glb and writes a JSON budget report.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import crops
import foliage
import landmarks
import lib
import water_props

BUILDERS = {
    'backdrop_hills': landmarks.build_backdrop_hills,
    'river_bridge': water_props.build_river_bridge,
    'footbridge': water_props.build_footbridge,
    'canal_bank': water_props.build_canal_bank,
    'stream_channel': water_props.build_stream_channel,
    **foliage.FOLIAGE_BUILDERS,
    **crops.CROP_BUILDERS,
}

GROUPS = {
    'm1': ['backdrop_hills'],
    'm2': ['river_bridge', 'footbridge', 'canal_bank', 'stream_channel'],
    'm3': list(foliage.FOLIAGE_BUILDERS.keys()) + list(crops.CROP_BUILDERS.keys()),
    'foliage': list(foliage.FOLIAGE_BUILDERS.keys()),
    'crops': list(crops.CROP_BUILDERS.keys()),
}


def parse_keys():
    if '--' not in sys.argv:
        return list(BUILDERS.keys())
    raw = [a for a in sys.argv[sys.argv.index('--') + 1:] if not a.startswith('-')]
    if not raw:
        return list(BUILDERS.keys())
    out = []
    for k in raw:
        if k in GROUPS:
            out.extend(GROUPS[k])
        else:
            out.append(k)
    return out


def main():
    lib.ensure_dirs()
    keys = parse_keys()
    report = []
    for key in keys:
        if key not in BUILDERS:
            raise SystemExit(f'Unknown environment v3 asset: {key}')
        lib.reset_scene()
        col = lib.make_collection(key)
        res = BUILDERS[key](col)
        objs = res if isinstance(res, list) else [res]
        out_path = lib.OUT_MODELS / f'{key}.glb'
        size_b = lib.export_glb(objs, out_path, draco_level=6)
        lod0_tris = sum(lib.tri_count(o) for o in objs if '_LOD1' not in o.name)
        lod1_tris = sum(lib.tri_count(o) for o in objs if '_LOD1' in o.name)
        info = {
            'name': key,
            'tris': lod0_tris,
            'tris_lod1': lod1_tris,
            'kb': round(size_b / 1024.0, 1),
            'mats': sorted({m.name for o in objs for m in o.data.materials}),
        }
        report.append(info)
        print('BUILT_ENV', json.dumps(info), flush=True)
    lib.save_report(report)
    print('ENV_V3_BUILD_OK', len(report), flush=True)


if __name__ == '__main__':
    main()
