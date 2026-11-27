"""Entry point: build v4 cast, export Draco-6 GLBs (no .blend, no outlines), render PBR previews."""
import sys

sys.dont_write_bytecode = True

ROOT = '/var/www/html/old/3d-quranic/'
HERE = ROOT + 'blender/v4/characters/'
if HERE not in sys.path:
    sys.path.insert(0, HERE)

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
            f"BUILT {info['key']} tris={info['tris']} bones={info['bones']} "
            f"glb_kb={info['glb_kb']} mats={','.join(info['mats'])} clips={','.join(info['clips'])}",
            flush=True,
        )
        built.append(info)

    for info in built:
        preview.render_turnaround(info['key'])
        preview.render_face(info['key'])

    if len(built) > 1 or set(keys) == set(cast.ORDER):
        preview.render_lineup()
        preview.render_poses()

    return built


if __name__ == '__main__':
    main()
