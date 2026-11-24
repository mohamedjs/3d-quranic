"""Entry point: build cast, export Draco-6 GLBs, save characters.blend, render EEVEE previews."""
import os
import sys

# Avoid polluting blender/v3/characters/ with __pycache__
sys.dont_write_bytecode = True

ROOT = '/var/www/html/old/3d-quranic/'
HERE = ROOT + 'blender/v3/characters/'
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy
import lib as L
import cast
import preview


def _parse_keys():
    if '--' in sys.argv:
        args = [a for a in sys.argv[sys.argv.index('--') + 1:] if a and not a.startswith('-')]
        if args:
            return args
    return list(cast.ORDER)


def main(keys=None):
    keys = keys or _parse_keys()
    for k in keys:
        if k not in cast.CAST:
            raise SystemExit(f'Unknown character key: {k}. Expected one of {cast.ORDER}')

    L.reset_scene()
    built = []
    for k in keys:
        info = cast.build(k)
        L.export_glb(info)
        print(
            f"BUILT {info['key']} tris={info['tris']} outline_tris={info['outline_tris']} "
            f"bones={info['bones']} glb_kb={info['glb_kb']}",
            flush=True,
        )
        built.append(info)

    preview.layout()
    os.makedirs(os.path.dirname(L.BLEND), exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=L.BLEND)

    for info in built:
        preview.render_turnaround(info['key'])
        preview.render_face(info['key'])

    if len(built) > 1 or set(keys) == set(cast.ORDER):
        preview.render_lineup()
        preview.render_poses()

    preview.layout()
    return built


if __name__ == '__main__':
    main()
