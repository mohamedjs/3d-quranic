"""M4 Poly Haven Rocks (`boulder` from `namaqualand_boulder_02`, `rock_small` from `rock_07`).

Replaces the procedural `lump` rocks with textured Poly Haven stone models graded warmly
to the Nile valley / desert sandstone palette:
  - `boulder`    : LOD0 <= 600 tris, LOD1 <= 150 tris (~2.2 m wide x 1.05 m tall)
  - `rock_small` : <= 100 tris (~0.75 m wide x 0.45 m tall), lifted from dark wet brown to
                   dusty warm Egyptian limestone/sandstone.

Run headless from repo root:
  blender -b --factory-startup --python blender/v4/env/rocks.py
"""
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib

BOULDER_LOD0 = 600
BOULDER_LOD1 = 150
ROCK_SMALL_MAX = 100


def _select_only(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]


def _decimate(obj, target_tris):
    cur = lib.tri_count(obj)
    if cur <= target_tris:
        return
    _select_only([obj])
    for delimit in ({'UV'}, set()):
        cur = lib.tri_count(obj)
        if cur <= target_tris:
            break
        mod = obj.modifiers.new('Dec', 'DECIMATE')
        mod.decimate_type = 'COLLAPSE'
        mod.ratio = max(0.015, min(0.95, (target_tris * 0.93) / cur))
        mod.delimit = delimit
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=mod.name)


def _grade_rock_diff(rgb, mode):
    if mode == 'boulder':
        # Gentle warm sandstone harmony with Nile desert palette
        r = np.clip(rgb[:, :, 0] * 1.12 + 0.03, 0.0, 1.0)
        g = np.clip(rgb[:, :, 1] * 1.08 + 0.02, 0.0, 1.0)
        b = np.clip(rgb[:, :, 2] * 0.98 + 0.01, 0.0, 1.0)
        return np.stack([r, g, b], axis=2)
    # rock_07 is raw dark wet reddish-brown; lift & neutralize into warm dry Nile sandstone!
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    # Desaturate heavy mahogany tint while preserving rock surface grain contrast
    dr = lum + (r - lum) * 0.35
    dg = lum + (g - lum) * 0.35
    db = lum + (b - lum) * 0.35
    # Map brightness into sun-baked sandstone range (~0.46..0.78 sRGB)
    nr = np.clip(dr * 1.65 + 0.28, 0.0, 1.0)
    ng = np.clip(dg * 1.60 + 0.22, 0.0, 1.0)
    nb = np.clip(db * 1.48 + 0.14, 0.0, 1.0)
    return np.stack([nr, ng, nb], axis=2)


def _build_rock_material(name, aid, mode, diff_size=512, nor_size=256):
    tdir = lib.CACHE_PH / aid / 'textures'
    diff_p = sorted(tdir.glob(f'{aid}_diff*'))[0]
    nor_p  = sorted(tdir.glob(f'{aid}_nor_gl*'))[0]
    arm_p  = sorted(tdir.glob(f'{aid}_arm*'))[0]

    diff = lib.load_image_rgba(diff_p, (diff_size, diff_size))
    diff[:, :, :3] = _grade_rock_diff(diff[:, :, :3], mode)
    diff[:, :, 3] = 1.0

    nor = lib.load_image_rgba(nor_p, (nor_size, nor_size))
    arm = lib.load_image_rgba(arm_p, (nor_size, nor_size))
    # Matte weathered stone (never glossy wet plastic)
    arm[:, :, 1] = np.clip(arm[:, :, 1] * 0.45 + 0.55, 0.78, 0.96)
    arm[:, :, 2] = 0.0

    img_d = lib.make_packed_image(f'{name}_diff', diff, srgb=True)
    img_n = lib.make_packed_image(f'{name}_nor',  nor,  srgb=False)
    img_a = lib.make_packed_image(f'{name}_arm',  arm,  srgb=False)
    return lib.build_pbr_atlas_material(
        f'mat_{name}', img_d, img_n, img_a,
        alpha_mask=False, use_vcol=True, roughness=0.90, double_sided=False,
    )


def _paint_rock_ao(obj):
    """Darken bottom skirt subtly so rocks look grounded into soil/sand."""
    me = obj.data
    if 'Color' in me.color_attributes:
        me.color_attributes.remove(me.color_attributes['Color'])
    ca = me.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
    me.color_attributes.active_color_index = me.color_attributes.find('Color')
    me.color_attributes.render_color_index = me.color_attributes.active_color_index

    zs = [v.co.z for v in me.vertices]
    z0, z1 = min(zs), max(zs)
    span = max(z1 - z0, 0.1)
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index]
            hz = max(0.0, min(1.0, (v.co.z - z0) / span))
            up = max(0.0, v.normal.z)
            k = (0.76 + 0.24 * (hz ** 0.7)) * (0.94 + 0.08 * up)
            k = max(0.65, min(1.04, k))
            ca.data[li].color = (k, k, k, 1.0)
    me.update()


def _import_and_normalize(src_glb, target_width, z_sink_frac=0.14):
    bpy.ops.import_scene.gltf(filepath=str(src_glb))
    imported = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    for o in imported:
        if o.parent:
            mw = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = mw
    _select_only(imported)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(imported) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active

    pts = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', pts)
    pts = pts.reshape(-1, 3)
    w_cur = max(0.05, float(max(pts[:, 0].max() - pts[:, 0].min(), pts[:, 1].max() - pts[:, 1].min())))
    sc = target_width / w_cur
    pts *= sc
    h_cur = float(pts[:, 2].max() - pts[:, 2].min())
    pts[:, 0] -= float((pts[:, 0].min() + pts[:, 0].max()) * 0.5)
    pts[:, 1] -= float((pts[:, 1].min() + pts[:, 1].max()) * 0.5)
    # Sink bottom slightly below z=0 so boulders sit firmly on sloped banks without floating!
    pts[:, 2] -= float(pts[:, 2].min()) + h_cur * z_sink_frac
    obj.data.vertices.foreach_set('co', pts.ravel())
    obj.data.update()
    return obj


def build_boulder():
    lib.reset_scene()
    src = lib.OUT_MODELS / 'ph_namaqualand_boulder_02_hi.glb'
    mat = _build_rock_material('boulder', 'namaqualand_boulder_02', 'boulder', diff_size=512, nor_size=256)

    lod0 = _import_and_normalize(src, target_width=2.3, z_sink_frac=0.16)
    _decimate(lod0, 560)
    _paint_rock_ao(lod0)
    lod0.data.materials.clear()
    lod0.data.materials.append(mat)
    lod0.name = 'boulder'
    lod0.data.name = 'boulder'

    lod1 = lod0.copy()
    lod1.data = lod0.data.copy()
    lod1.name = 'boulder_LOD1'
    lod1.data.name = 'boulder_LOD1'
    bpy.context.collection.objects.link(lod1)
    _decimate(lod1, 140)
    _paint_rock_ao(lod1)

    t0, t1 = lib.tri_count(lod0), lib.tri_count(lod1)
    if t0 > BOULDER_LOD0 or t1 > BOULDER_LOD1:
        raise RuntimeError(f'boulder: LOD0={t0}/{BOULDER_LOD0}, LOD1={t1}/{BOULDER_LOD1}')

    out_path = lib.OUT_MODELS / 'boulder.glb'
    lib.export_textured_glb(out_path, [lod0, lod1], webp_quality=76, embed_images=True)
    nbytes, nmats, nimgs = lib.verify_textured_glb(out_path, expect_mask=False, max_mats=1)
    print(f'[v4/rocks] {"boulder":12s} LOD0={t0:4d}/{BOULDER_LOD0}  LOD1={t1:3d}/{BOULDER_LOD1}  '
          f'mats={nmats} imgs={nimgs} {nbytes/1024:5.1f}KB', flush=True)


def build_rock_small():
    lib.reset_scene()
    src = lib.OUT_MODELS / 'ph_rock_07_hi.glb'
    mat = _build_rock_material('rock_small', 'rock_07', 'small', diff_size=256, nor_size=256)

    obj = _import_and_normalize(src, target_width=0.72, z_sink_frac=0.18)
    _decimate(obj, 92)
    _paint_rock_ao(obj)
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    obj.name = 'rock_small'
    obj.data.name = 'rock_small'

    t0 = lib.tri_count(obj)
    if t0 > ROCK_SMALL_MAX:
        raise RuntimeError(f'rock_small: tris {t0} > {ROCK_SMALL_MAX}')

    out_path = lib.OUT_MODELS / 'rock_small.glb'
    lib.export_textured_glb(out_path, [obj], webp_quality=74, embed_images=True)
    nbytes, nmats, nimgs = lib.verify_textured_glb(out_path, expect_mask=False, max_mats=1)
    print(f'[v4/rocks] {"rock_small":12s} LOD0={t0:4d}/{ROCK_SMALL_MAX}  mats={nmats} imgs={nimgs} {nbytes/1024:5.1f}KB', flush=True)


def main():
    build_boulder()
    build_rock_small()


if __name__ == '__main__':
    main()
