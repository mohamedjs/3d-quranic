"""M4 Poly Haven Broadleaf Trees & Shrubs (`sycamore_a`, `sycamore_b`, `acacia`, `bush_a`, `bush_b`).

Builds every broadleaf tree and shrub with ONE material per file and ONE baked leaf+bark
WebP atlas (<= 512 px embedded, alphaMode=MASK, alphaCutoff=0.5):
  - `sycamore_a` : from Poly Haven `island_tree_02` (lush Egyptian shade sycamore, ~6.8 m)
  - `sycamore_b` : from Poly Haven `tree_small_02` (tall fuller sycamore variant, ~7.4 m)
  - `acacia`     : Egyptian desert umbrella acacia (`Acacia tortilis`, ~4.8 m) built from a
                   twisted gnarled trunk/limbs + real Poly Haven `island_tree_02` leaf cards
  - `bush_a`     : from Poly Haven `shrub_02` (lush Nile olive-emerald shrub, ~1.25 m)
  - `bush_b`     : from Poly Haven `shrub_04` (warm golden-sage desert scrub, ~1.05 m)

Budgets:
  - Trees:  LOD0 <= 3,500 tris, LOD1 <= 600 tris
  - Bushes: LOD0 <=   600 tris, LOD1 <= 150 tris

Run headless from repo root:
  blender -b --factory-startup --python blender/v4/env/trees.py
"""
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector, noise

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib

TREE_LOD0_BUDGET = 3500
TREE_LOD1_BUDGET = 600
BUSH_LOD0_BUDGET = 600
BUSH_LOD1_BUDGET = 150

# 512x512 1-atlas UV vertical split (glTF V=0 bottom, V=1 top; bottom-up array rows match!)
# Bottom strip [0.00..0.34]: seamless horizontal bark (alpha = 1.0, wraps freely in U!)
# Guard band   [0.34..0.36]: dilated bleed margin
# Top band     [0.36..1.00]: alpha-cutout leaf sprigs (warm healthy green, alpha MASK 0.5)
BARK_V0, BARK_V1 = 0.02, 0.32
LEAF_V0, LEAF_V1 = 0.37, 0.99


def _grade_green_foliage(rgb, alpha, style='sycamore'):
    """Recolour Poly Haven leaves to a warm healthy Mediterranean/Nile green (sRGB in/out)."""
    r = rgb[:, :, 0]
    g = rgb[:, :, 1]
    b = rgb[:, :, 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b

    # Detect actual leaf pixels vs woody twigs/petioles (leaves have higher G relative to R/B)
    greenness = np.clip((g - np.maximum(r, b) * 0.78) * 5.0 + 0.45, 0.0, 1.0)

    if style == 'sycamore':
        # Rich sunlit Nile sycamore green (warm emerald-olive, lively but naturalistic)
        tr = np.clip(lum * 0.62 + r * 0.34 + 0.02, 0.0, 1.0)
        tg = np.clip(lum * 0.96 + g * 0.38 + 0.05, 0.0, 1.0)
        tb = np.clip(lum * 0.32 + b * 0.22, 0.0, 1.0)
        out_r = r * (1.0 - 0.68 * greenness) + tr * (0.68 * greenness)
        out_g = g * (1.0 - 0.68 * greenness) + tg * (0.68 * greenness)
        out_b = b * (1.0 - 0.68 * greenness) + tb * (0.68 * greenness)
    elif style == 'acacia':
        # Sun-warmed dusty desert olive-sage green (characteristic Acacia tortilis)
        tr = np.clip(lum * 0.80 + r * 0.32 + 0.03, 0.0, 1.0)
        tg = np.clip(lum * 0.98 + g * 0.34 + 0.04, 0.0, 1.0)
        tb = np.clip(lum * 0.40 + b * 0.22, 0.0, 1.0)
        out_r = r * (1.0 - 0.72 * greenness) + tr * (0.72 * greenness)
        out_g = g * (1.0 - 0.72 * greenness) + tg * (0.72 * greenness)
        out_b = b * (1.0 - 0.72 * greenness) + tb * (0.72 * greenness)
    elif style == 'bush_lush':
        # Lush Nile village olive-emerald shrub
        tr = np.clip(lum * 0.58 + r * 0.38 + 0.02, 0.0, 1.0)
        tg = np.clip(lum * 0.98 + g * 0.40 + 0.06, 0.0, 1.0)
        tb = np.clip(lum * 0.30 + b * 0.24, 0.0, 1.0)
        out_r = r * (1.0 - 0.70 * greenness) + tr * (0.70 * greenness)
        out_g = g * (1.0 - 0.70 * greenness) + tg * (0.70 * greenness)
        out_b = b * (1.0 - 0.70 * greenness) + tb * (0.70 * greenness)
    else:  # 'bush_dry'
        # Warm golden-olive desert scrub (bush_b)
        tr = np.clip(lum * 0.88 + r * 0.34 + 0.03, 0.0, 1.0)
        tg = np.clip(lum * 0.94 + g * 0.32 + 0.03, 0.0, 1.0)
        tb = np.clip(lum * 0.36 + b * 0.22, 0.0, 1.0)
        out_r = r * (1.0 - 0.65 * greenness) + tr * (0.65 * greenness)
        out_g = g * (1.0 - 0.65 * greenness) + tg * (0.65 * greenness)
        out_b = b * (1.0 - 0.65 * greenness) + tb * (0.65 * greenness)

    graded = np.stack([out_r, out_g, out_b], axis=2)
    # Gentle lift so dark scanned shadows in leaf clusters stay bright and storybook-warm
    graded = np.clip(graded * 1.16 + 0.025, 0.0, 1.0)
    return lib.dilate_rgb_under_alpha(graded, alpha, iters=10)


def _grade_bark(rgb):
    """Warm up bark slightly toward sunlit Nile wood tones."""
    r = np.clip(rgb[:, :, 0] * 1.18 + 0.04, 0.0, 1.0)
    g = np.clip(rgb[:, :, 1] * 1.12 + 0.03, 0.0, 1.0)
    b = np.clip(rgb[:, :, 2] * 1.02 + 0.02, 0.0, 1.0)
    return np.stack([r, g, b], axis=2)


def _build_tree_atlas(name, bark_id, leaf_id, style='sycamore', size=512, nor_size=256):
    """Pack bark (bottom strip, opaque) + leaves (top band, MASK 0.5) into ONE atlas set."""
    b_dir = lib.CACHE_PH / bark_id / 'textures'
    l_dir = lib.CACHE_PH / leaf_id / 'textures'

    bark_diff_p = sorted(b_dir.glob(f'{bark_id}_diff*'))[0]
    bark_nor_p  = sorted(b_dir.glob(f'{bark_id}_nor_gl*'))[0]
    bark_arm_p  = sorted(b_dir.glob(f'{bark_id}_arm*'))[0]

    leaf_diff_p  = sorted(l_dir.glob(f'{leaf_id}_leaves_diff*'))[0]
    leaf_alpha_p = sorted(l_dir.glob(f'{leaf_id}_leaves_alpha*'))[0]
    leaf_nor_p   = sorted(l_dir.glob(f'{leaf_id}_leaves_nor_gl*'))[0]
    leaf_arm_p   = sorted(l_dir.glob(f'{leaf_id}_leaves_arm*'))[0]

    split = int(round(size * 0.35))
    leaf_h = size - split

    b_diff = lib.load_image_rgba(bark_diff_p, (size, split))
    l_diff = lib.load_image_rgba(leaf_diff_p, (size, leaf_h))
    l_alp  = lib.load_image_rgba(leaf_alpha_p, (size, leaf_h))[:, :, 0]

    if leaf_id == 'tree_small_02':
        # Suppress stray Voronoi bleed on right margin (u > 0.845) and pure-black gaps
        dmax = l_diff[:, :, :3].max(axis=2)
        l_alp = np.where(dmax < 0.03, 0.0, l_alp)
        xs_n = (np.arange(size, dtype=np.float32) + 0.5) / size
        l_alp = np.where(xs_n[None, :] > 0.845, 0.0, l_alp)

    # Boost alpha slightly around thin sprigs so 512px mipmaps never lose crisp leaf silhouettes
    l_alp = np.clip((l_alp - 0.18) / 0.62, 0.0, 1.0)
    l_rgb = _grade_green_foliage(l_diff[:, :, :3], l_alp, style=style)
    b_rgb = _grade_bark(b_diff[:, :, :3])

    diff_atlas = np.ones((size, size, 4), dtype=np.float32)
    diff_atlas[:split, :, :3] = b_rgb
    diff_atlas[:split, :, 3] = 1.0
    diff_atlas[split:, :, :3] = l_rgb
    diff_atlas[split:, :, 3] = l_alp

    # Normal & ARM packed at nor_size (256px keeps GLB size lean ~70-90 KB while adding crisp PBR depth)
    nsplit = int(round(nor_size * 0.35))
    nleaf_h = nor_size - nsplit
    b_nor = lib.load_image_rgba(bark_nor_p, (nor_size, nsplit))
    l_nor = lib.load_image_rgba(leaf_nor_p, (nor_size, nleaf_h))
    nor_atlas = np.ones((nor_size, nor_size, 4), dtype=np.float32)
    nor_atlas[:nsplit, :, :3] = b_nor[:, :, :3]
    nor_atlas[nsplit:, :, :3] = l_nor[:, :, :3]

    b_arm = lib.load_image_rgba(bark_arm_p, (nor_size, nsplit))
    l_arm = lib.load_image_rgba(leaf_arm_p, (nor_size, nleaf_h))
    arm_atlas = np.ones((nor_size, nor_size, 4), dtype=np.float32)
    arm_atlas[:nsplit, :, :3] = b_arm[:, :, :3]
    arm_atlas[nsplit:, :, :3] = l_arm[:, :, :3]
    # Keep foliage matte-natural (roughness >= 0.68) and non-metallic
    arm_atlas[:, :, 1] = np.clip(arm_atlas[:, :, 1], 0.68, 0.96)
    arm_atlas[:, :, 2] = 0.0

    img_diff = lib.make_packed_image(f'{name}_atlas_diff', diff_atlas, srgb=True)
    img_nor  = lib.make_packed_image(f'{name}_atlas_nor',  nor_atlas,  srgb=False)
    img_arm  = lib.make_packed_image(f'{name}_atlas_arm',  arm_atlas,  srgb=False)
    return lib.build_pbr_atlas_material(
        f'mat_{name}', img_diff, img_nor, img_arm,
        alpha_mask=True, use_vcol=True, roughness=0.82, double_sided=True,
    )


def _build_shrub_material(name, aid, style, size=384, nor_size=256):
    """Build ONE recoloured WebP PBR+MASK material for a Poly Haven shrub (`shrub_02` / `shrub_04`)."""
    tdir = lib.CACHE_PH / aid / 'textures'
    diff_p  = sorted(tdir.glob(f'{aid}_diff*'))[0]
    alpha_p = sorted(tdir.glob(f'{aid}_alpha*'))[0]
    nor_p   = sorted(tdir.glob(f'{aid}_nor_gl*'))[0]
    arm_p   = sorted(tdir.glob(f'{aid}_arm*'))[0]

    diff = lib.load_image_rgba(diff_p, (size, size))
    alp  = lib.load_image_rgba(alpha_p, (size, size))[:, :, 0]
    alp  = np.clip((alp - 0.18) / 0.62, 0.0, 1.0)
    rgb  = _grade_green_foliage(diff[:, :, :3], alp, style=style)

    rgba = np.empty((size, size, 4), dtype=np.float32)
    rgba[:, :, :3] = rgb
    rgba[:, :, 3] = alp

    nor = lib.load_image_rgba(nor_p, (nor_size, nor_size))
    arm = lib.load_image_rgba(arm_p, (nor_size, nor_size))
    arm[:, :, 1] = np.clip(arm[:, :, 1], 0.70, 0.96)
    arm[:, :, 2] = 0.0

    img_diff = lib.make_packed_image(f'{name}_diff', rgba, srgb=True)
    img_nor  = lib.make_packed_image(f'{name}_nor',  nor,  srgb=False)
    img_arm  = lib.make_packed_image(f'{name}_arm',  arm,  srgb=False)
    return lib.build_pbr_atlas_material(
        f'mat_{name}', img_diff, img_nor, img_arm,
        alpha_mask=True, use_vcol=True, roughness=0.84, double_sided=True,
    )


def _select_only(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]


def _find_islands(me):
    n_verts = len(me.vertices)
    n_edges = len(me.edges)
    n_polys = len(me.polygons)
    if n_polys == 0:
        return np.empty(0, dtype=np.int32)
    ek = np.empty(n_edges * 2, dtype=np.int32)
    me.edges.foreach_get('vertices', ek)
    parent = list(range(n_verts))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(0, len(ek), 2):
        ra = find(int(ek[i]))
        rb = find(int(ek[i + 1]))
        if ra != rb:
            parent[rb] = ra

    lstart = np.empty(n_polys, dtype=np.int32)
    me.polygons.foreach_get('loop_start', lstart)
    lverts = np.empty(len(me.loops), dtype=np.int32)
    me.loops.foreach_get('vertex_index', lverts)
    return np.fromiter((find(int(v)) for v in lverts[lstart]), dtype=np.int32, count=n_polys)


def _select_spatial_card_islands(obj, target_count, seed=42):
    """Spatially stratified selection of whole leaf-card islands for full even crown coverage."""
    me = obj.data
    roots = _find_islands(me)
    uniq, inv, counts = np.unique(roots, return_inverse=True, return_counts=True)
    if len(uniq) <= target_count:
        return set(int(u) for u in uniq), roots

    ctrs = np.empty(len(me.polygons) * 3, dtype=np.float32)
    me.polygons.foreach_get('center', ctrs)
    ctrs = ctrs.reshape(-1, 3)
    areas = np.empty(len(me.polygons), dtype=np.float32)
    me.polygons.foreach_get('area', areas)

    icx = np.bincount(inv, weights=ctrs[:, 0]) / counts
    icy = np.bincount(inv, weights=ctrs[:, 1]) / counts
    icz = np.bincount(inv, weights=ctrs[:, 2]) / counts
    i_areas = np.bincount(inv, weights=areas)
    ic = np.stack([icx, icy, icz], axis=1)

    mn = ic.min(axis=0)
    span = np.maximum(ic.max(axis=0) - mn, 1e-4)
    g = max(3, int(round((target_count / 1.4) ** (1.0 / 3.0))))
    idx = np.clip(((ic - mn) / span * g).astype(np.int32), 0, g - 1)
    cell_keys = idx[:, 0] * (g * g) + idx[:, 1] * g + idx[:, 2]

    buckets = defaultdict(list)
    for pos in np.argsort(i_areas):
        buckets[int(cell_keys[pos])].append(int(uniq[pos]))

    rng = np.random.default_rng(seed)
    keys = sorted(buckets.keys())
    rng.shuffle(keys)
    kept = []
    while len(kept) < target_count and keys:
        nxt = []
        for k in keys:
            b = buckets[k]
            if b:
                kept.append(b.pop())
                if len(kept) >= target_count:
                    break
                if b:
                    nxt.append(k)
        keys = nxt
    return set(kept), roots


def _filter_and_scale_islands(obj, keep_set, scale_factor=1.0, roots=None):
    me = obj.data
    if roots is None:
        roots = _find_islands(me)
    keep_poly = np.fromiter((int(r) in keep_set for r in roots), dtype=bool, count=len(me.polygons))
    if not np.all(keep_poly):
        _select_only([obj])
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='FACE')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        me.polygons.foreach_set('select', (~keep_poly).tolist())
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.delete(type='FACE')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        me.update()

    if abs(scale_factor - 1.0) > 1e-3 and len(me.polygons) > 0:
        roots2 = _find_islands(me)
        n_v = len(me.vertices)
        coords = np.empty(n_v * 3, dtype=np.float32)
        me.vertices.foreach_get('co', coords)
        coords = coords.reshape(-1, 3)

        lstart = np.empty(len(me.polygons), dtype=np.int32)
        ltot = np.empty(len(me.polygons), dtype=np.int32)
        lverts = np.empty(len(me.loops), dtype=np.int32)
        me.polygons.foreach_get('loop_start', lstart)
        me.polygons.foreach_get('loop_total', ltot)
        me.loops.foreach_get('vertex_index', lverts)

        v_root = np.full(n_v, -1, dtype=np.int32)
        for pi in range(len(me.polygons)):
            s = lstart[pi]
            v_root[lverts[s:s + ltot[pi]]] = roots2[pi]
        valid = np.nonzero(v_root >= 0)[0]
        _, inv = np.unique(v_root[valid], return_inverse=True)
        cnts = np.bincount(inv).astype(np.float32)
        cx = np.bincount(inv, weights=coords[valid, 0]) / cnts
        cy = np.bincount(inv, weights=coords[valid, 1]) / cnts
        cz = np.bincount(inv, weights=coords[valid, 2]) / cnts
        ctrs = np.stack([cx, cy, cz], axis=1)
        coords[valid] = ctrs[inv] + (coords[valid] - ctrs[inv]) * float(scale_factor)
        me.vertices.foreach_set('co', coords.ravel())
        me.update()


def _decimate_mesh(obj, target_tris):
    cur = lib.tri_count(obj)
    if cur <= target_tris:
        return
    _select_only([obj])
    mod = obj.modifiers.new('Dec', 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = max(0.03, min(0.96, (target_tris * 0.94) / cur))
    mod.delimit = {'UV'}
    mod.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    cur = lib.tri_count(obj)
    if cur > target_tris:
        mod = obj.modifiers.new('Dec2', 'DECIMATE')
        mod.decimate_type = 'COLLAPSE'
        mod.ratio = max(0.03, min(0.95, (target_tris * 0.92) / cur))
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=mod.name)


def _remap_uv_band(obj, v0, v1, is_bark=False):
    """Remap UVMap vertically into [v0, v1]. For bark, ping-pong V cleanly and keep U tiling."""
    me = obj.data
    if not me.uv_layers:
        return
    uvl = me.uv_layers.active
    n = len(uvl.data)
    uvs = np.empty(n * 2, dtype=np.float32)
    uvl.data.foreach_get('uv', uvs)
    uvs = uvs.reshape(-1, 2)
    if is_bark:
        # Ping-pong V in [0,1] so wrapped trunk UVs stay strictly inside the opaque bark strip!
        vv = np.abs((uvs[:, 1] % 2.0) - 1.0)
        uvs[:, 1] = v0 + (v1 - v0) * vv
    else:
        uvs[:, 0] = np.clip(uvs[:, 0], 0.005, 0.995)
        uvs[:, 1] = v0 + (v1 - v0) * np.clip(uvs[:, 1], 0.0, 1.0)
    uvl.data.foreach_set('uv', uvs.ravel())
    me.update()


def _paint_canopy_vcol(obj, is_leaf, canopy_center, canopy_r, min_z, max_z, is_shrub=False):
    """Bake soft sunlit-crown / shaded-interior vertex colors (`Color`, linear) for painterly depth."""
    me = obj.data
    if 'Color' in me.color_attributes:
        me.color_attributes.remove(me.color_attributes['Color'])
    ca = me.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
    me.color_attributes.active_color_index = me.color_attributes.find('Color')
    me.color_attributes.render_color_index = me.color_attributes.active_color_index

    verts = me.vertices
    span_z = max(max_z - min_z, 0.5)
    for poly in me.polygons:
        for li in poly.loop_indices:
            p = verts[me.loops[li].vertex_index].co
            hz = max(0.0, min(1.0, (p.z - min_z) / span_z))
            if is_leaf:
                d_rad = min(1.0, (p - canopy_center).length / max(canopy_r, 0.4))
                # Soft inner-crown AO + warm golden sunlit crown top
                ao = 0.72 + 0.28 * d_rad
                sun = 0.80 + 0.26 * (hz ** 0.85)
                k = max(0.60, min(1.08, ao * sun))
                # Slight warm sunlit golden tint at crown top, cooler shade below
                r = min(1.0, k * (0.96 + 0.07 * hz))
                g = min(1.0, k * (0.98 + 0.04 * hz))
                b = min(1.0, k * (0.92 - 0.04 * hz if is_shrub else 0.94))
            else:
                # Grounded dark soil splash at trunk base, shaded right under canopy
                base_sh = 0.68 + 0.32 * min(1.0, hz * 3.5)
                top_sh = 1.0 - 0.18 * max(0.0, (hz - 0.55) / 0.45)
                k = max(0.55, min(1.0, base_sh * top_sh))
                r = g = b = k
            ca.data[li].color = (r, g, b, 1.0)
    me.update()


def _blend_spherical_normals(obj, center, blend=0.58):
    me = obj.data
    normals = []
    for p in me.polygons:
        for li in p.loop_indices:
            v = me.vertices[me.loops[li].vertex_index]
            out = v.co - center
            if out.length < 1e-5:
                out = Vector((0.0, 0.0, 1.0))
            else:
                out.normalize()
            n = v.normal * (1.0 - blend) + out * blend
            normals.append(n.normalized() if n.length > 1e-5 else Vector((0.0, 0.0, 1.0)))
    me.normals_split_custom_set(normals)


def _scale_mesh(obj, sx, sy, sz, z_sink=-0.15):
    me = obj.data
    coords = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get('co', coords)
    pts = coords.reshape(-1, 3)
    pts[:, 0] *= sx
    pts[:, 1] *= sy
    pts[:, 2] *= sz
    pts[:, 2] += z_sink - pts[:, 2].min()
    # Re-center trunk root footprint around (0, 0) using lower 18% of vertices
    z_cut = pts[:, 2].min() + (pts[:, 2].max() - pts[:, 2].min()) * 0.18
    base = pts[pts[:, 2] <= z_cut]
    if len(base):
        pts[:, 0] -= float(base[:, 0].mean())
        pts[:, 1] -= float(base[:, 1].mean())
    me.vertices.foreach_set('co', pts.ravel())
    me.update()


def _build_ph_tree_lod(src_glb, name, mat, scale_xyz, wood_budget, leaf_budget,
                       card_boost, seed, lod1=False):
    """Import processed Poly Haven tree, decimate wood + spatially select leaf cards, pack 1 atlas."""
    bpy.ops.import_scene.gltf(filepath=str(src_glb))
    imported = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if not imported:
        raise RuntimeError(f'No meshes imported from {src_glb}')
    # Apply transforms cleanly
    for o in imported:
        if o.parent:
            mw = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = mw
    _select_only(imported)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(imported) > 1:
        bpy.ops.object.join()
    root = bpy.context.view_layer.objects.active
    _scale_mesh(root, *scale_xyz, z_sink=-0.16)

    # Separate wood vs leaf materials so we remap each cleanly into its 1-atlas band
    _select_only([root])
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='MATERIAL')
    bpy.ops.object.mode_set(mode='OBJECT')

    parts = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    wood_parts, leaf_parts = [], []
    for p in parts:
        mn = p.material_slots[0].material.name.lower() if p.material_slots and p.material_slots[0].material else ''
        if 'leave' in mn or 'leaf' in mn:
            leaf_parts.append(p)
        else:
            wood_parts.append(p)

    # Join & decimate wood
    _select_only(wood_parts)
    if len(wood_parts) > 1:
        bpy.ops.object.join()
    wood = bpy.context.view_layer.objects.active
    _decimate_mesh(wood, wood_budget)
    _remap_uv_band(wood, BARK_V0, BARK_V1, is_bark=True)

    # Join & spatially select leaf cards + area-compensating boost for full lush crowns!
    _select_only(leaf_parts)
    if len(leaf_parts) > 1:
        bpy.ops.object.join()
    leaves = bpy.context.view_layer.objects.active
    max_cards = max(40, (leaf_budget - 8) // 2)
    kept, roots = _select_spatial_card_islands(leaves, max_cards, seed=seed)
    # Compute scale factor so kept cards fill full lush canopy even at LOD1!
    src_cnt = len(np.unique(roots))
    ratio = math.sqrt(max(1.0, src_cnt / max(len(kept), 1)))
    sc = min(3.1 if lod1 else 2.55, max(1.22, ratio * card_boost))
    _filter_and_scale_islands(leaves, kept, scale_factor=sc, roots=roots)
    _remap_uv_band(leaves, LEAF_V0, LEAF_V1, is_bark=False)

    # Pull overly wide V-shaped crown gently toward a full billowing Nile sycamore dome on sycamore_a
    if name == 'sycamore_a':
        lp = np.empty(len(leaves.data.vertices) * 3, dtype=np.float32)
        leaves.data.vertices.foreach_get('co', lp)
        lp = lp.reshape(-1, 3)
        z_hi = float(lp[:, 2].max())
        z_lo = float(lp[:, 2].min())
        hz = np.clip((lp[:, 2] - z_lo) / max(z_hi - z_lo, 0.5), 0.0, 1.0)
        # Gently gather upper outer lobes inward and arch the crown center higher for a lush dome
        rad_xy = np.hypot(lp[:, 0], lp[:, 1])
        pull = 1.0 - 0.14 * hz
        lp[:, 0] *= pull
        lp[:, 1] *= pull
        lp[:, 2] += 0.55 * np.exp(-((rad_xy / 2.2) ** 2)) * (0.4 + 0.6 * hz)
        leaves.data.vertices.foreach_set('co', lp.ravel())
        leaves.data.update()

    # Compute canopy bounds for soft painterly AO & spherical leaf normals
    l_pts = np.empty(len(leaves.data.vertices) * 3, dtype=np.float32)
    leaves.data.vertices.foreach_get('co', l_pts)
    l_pts = l_pts.reshape(-1, 3)
    c_ctr = Vector(tuple(l_pts.mean(axis=0)))
    c_rad = max(1.0, float(np.linalg.norm(l_pts - l_pts.mean(axis=0), axis=1).mean()) * 1.35)
    z_min, z_max = float(l_pts[:, 2].min()), float(l_pts[:, 2].max())

    w_pts = np.empty(len(wood.data.vertices) * 3, dtype=np.float32)
    wood.data.vertices.foreach_get('co', w_pts)
    w_pts = w_pts.reshape(-1, 3)
    _paint_canopy_vcol(wood, False, c_ctr, c_rad, float(w_pts[:, 2].min()), float(w_pts[:, 2].max()))
    _paint_canopy_vcol(leaves, True, c_ctr, c_rad, z_min, z_max)
    _blend_spherical_normals(leaves, c_ctr - Vector((0, 0, 0.35)), blend=0.58)

    # Assign the ONE shared atlas material to both parts and join into ONE mesh/primitive!
    for o in (wood, leaves):
        o.data.materials.clear()
        o.data.materials.append(mat)
    _select_only([wood, leaves])
    bpy.ops.object.join()
    merged = bpy.context.view_layer.objects.active
    suf = '_LOD1' if lod1 else ''
    merged.name = f'{name}{suf}'
    merged.data.name = merged.name
    # Remove any extra UV layers (glTF uses active TEXCOORD_0)
    while len(merged.data.uv_layers) > 1:
        merged.data.uv_layers.remove(merged.data.uv_layers[-1])
    return merged


def build_sycamore(name, ph_id, scale_xyz, seed):
    lib.reset_scene()
    src_glb = lib.OUT_MODELS / f'ph_{ph_id}_hi.glb'
    mat = _build_tree_atlas(name, ph_id, ph_id, style='sycamore', size=512, nor_size=256)

    # Build LOD0 (<= 3,500 tris) and LOD1 (<= 600 tris)
    lod0 = _build_ph_tree_lod(
        src_glb, name, mat, scale_xyz,
        wood_budget=520, leaf_budget=2680, card_boost=1.18 if ph_id == 'island_tree_02' else 0.98,
        seed=seed, lod1=False,
    )
    lod1 = _build_ph_tree_lod(
        src_glb, name, mat, scale_xyz,
        wood_budget=110, leaf_budget=460, card_boost=1.22 if ph_id == 'island_tree_02' else 1.04,
        seed=seed + 7, lod1=True,
    )
    t0, t1 = lib.tri_count(lod0), lib.tri_count(lod1)
    if t0 > TREE_LOD0_BUDGET:
        raise RuntimeError(f'{name}: LOD0 tris {t0} > {TREE_LOD0_BUDGET}')
    if t1 > TREE_LOD1_BUDGET:
        raise RuntimeError(f'{name}: LOD1 tris {t1} > {TREE_LOD1_BUDGET}')

    out_path = lib.OUT_MODELS / f'{name}.glb'
    lib.export_textured_glb(out_path, [lod0, lod1], webp_quality=76, embed_images=True)
    nbytes, nmats, nimgs = lib.verify_textured_glb(out_path, expect_mask=True, max_mats=1)
    print(f'[v4/trees] {name:12s} LOD0={t0:4d}/{TREE_LOD0_BUDGET}  LOD1={t1:3d}/{TREE_LOD1_BUDGET}  '
          f'mats={nmats} imgs={nimgs} {nbytes/1024:5.1f}KB', flush=True)


def _add_bark_tube(bm, uvl, coll, pts, rads, sides=6, wobble=0.025, seed=0):
    """Tapered twisted gnarled branch/trunk mapped cleanly into the opaque bark atlas strip."""
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + (Vector(pts[i]) - Vector(pts[i - 1])).length)
    rings = []
    prev_r = Vector((1.0, 0.0, 0.0))
    for i, (p, rad) in enumerate(zip(pts, rads)):
        p = Vector(p)
        tang = (Vector(pts[1]) - p).normalized() if i == 0 else (
            (p - Vector(pts[i - 1])).normalized() if i == len(pts) - 1
            else (Vector(pts[i + 1]) - Vector(pts[i - 1])).normalized()
        )
        right = prev_r - tang * prev_r.dot(tang)
        if right.length < 1e-4:
            right = Vector((0.0, 1.0, 0.0)).cross(tang)
        right.normalize()
        prev_r = right
        fwd = tang.cross(right).normalized()
        ring = []
        for k in range(sides):
            a = (k / sides) * math.tau
            pos = p + (right * math.cos(a) + fwd * math.sin(a)) * rad
            if wobble:
                pos += noise.noise_vector(pos * 2.1 + Vector((seed * 3.1, i, k))) * wobble
            ring.append(bm.verts.new(pos))
        rings.append((cum[i], ring))

    tot = max(cum[-1], 0.1)
    for i in range(len(rings) - 1):
        c0, r0 = rings[i]
        c1, r1 = rings[i + 1]
        tv0 = abs(((c0 * 0.9) % 2.0) - 1.0)
        tv1 = abs(((c1 * 0.9) % 2.0) - 1.0)
        vv0 = BARK_V0 + (BARK_V1 - BARK_V0) * tv0
        vv1 = BARK_V0 + (BARK_V1 - BARK_V0) * tv1
        sh0 = 0.68 + 0.30 * min(1.0, (c0 / tot) * 2.5)
        sh1 = 0.68 + 0.30 * min(1.0, (c1 / tot) * 2.5)
        col0 = (sh0, sh0, sh0, 1.0)
        col1 = (sh1, sh1, sh1, 1.0)
        for k in range(sides):
            kn = (k + 1) % sides
            u0, u1 = k / sides, (k + 1) / sides
            f = bm.faces.new((r0[k], r0[kn], r1[kn], r1[k]))
            f.smooth = True
            for lp, uv, col in zip(f.loops, ((u0, vv0), (u1, vv0), (u1, vv1), (u0, vv1)), (col0, col0, col1, col1)):
                lp[uvl].uv = uv
                lp[coll] = col


def _build_acacia_lod(mat, leaf_card_templates, seed=331, lod1=False):
    """Flat-topped Egyptian desert umbrella acacia built from gnarled limbs + Poly Haven leaf cards."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    coll = bm.loops.layers.float_color.new('Color')

    sides_t = 5 if lod1 else 7
    sides_b = 4 if lod1 else 5

    # Twisted leaning desert trunk splitting low (~1.4 m) into sweeping V-shaped umbrella limbs
    _add_bark_tube(bm, uvl, coll,
                   [(0.0, 0.0, -0.20), (0.14, -0.05, 0.72), (0.26, 0.04, 1.50)],
                   [0.34, 0.25, 0.20], sides=sides_t, wobble=0.025, seed=seed)

    n_limbs = 4 if lod1 else 6
    for i in range(n_limbs):
        a = i * math.tau / n_limbs + 0.22 + rnd.uniform(-0.18, 0.18)
        reach = rnd.uniform(2.5, 3.45)
        h_tip = rnd.uniform(3.55, 4.10)
        mid = (0.26 + math.cos(a) * reach * 0.50, 0.04 + math.sin(a) * reach * 0.50, 2.65)
        tip = (0.26 + math.cos(a) * reach, 0.04 + math.sin(a) * reach, h_tip)
        _add_bark_tube(bm, uvl, coll, [(0.24, 0.04, 1.44), mid, tip],
                       [0.15, 0.10, 0.05], sides=sides_b, wobble=0.02, seed=seed + i + 1)
        # Secondary fork near outer canopy on LOD0
        if not lod1:
            fa = a + rnd.uniform(0.35, 0.55) * (1 if i % 2 else -1)
            fr = reach * 0.92
            ftip = (0.26 + math.cos(fa) * fr, 0.04 + math.sin(fa) * fr, h_tip + rnd.uniform(-0.15, 0.18))
            _add_bark_tube(bm, uvl, coll, [mid, ftip], [0.09, 0.04], sides=4, wobble=0.015, seed=seed + 20 + i)

    # Populate wide flat-topped umbrella canopy using real Poly Haven leaf-card UV templates!
    # Each template is (w, h, [(u,v), (u,v), (u,v), (u,v)]) extracted from island_tree_02_leaves.
    canopy_center = Vector((0.26, 0.04, 3.55))
    n_cards = 160 if lod1 else 860
    for i in range(n_cards):
        t = (i + 0.5) / n_cards
        a = i * 2.39996 + rnd.uniform(-0.22, 0.22)
        rr = math.sqrt(t) * 4.05 * rnd.uniform(0.86, 1.06)
        # Iconic flat-topped umbrella dome (crisp horizontal table top, gentle skirt curve)
        tier_z = 4.35 - 0.58 * ((rr / 4.2) ** 2.2) + rnd.uniform(-0.26, 0.22)
        cx = 0.26 + math.cos(a) * rr
        cy = 0.04 + math.sin(a) * rr
        pos = Vector((cx, cy, tier_z))

        # Mix mostly horizontal canopy plates (top) with tilted skirt cards (sides) so readable from every angle
        if rr > 2.2 and i % 3 == 0:
            nrm = Vector((math.cos(a) * 0.82, math.sin(a) * 0.82, 0.55)).normalized()
        else:
            nrm = Vector((
                math.cos(a) * 0.35 * (rr / 4.2) + rnd.uniform(-0.28, 0.28),
                math.sin(a) * 0.35 * (rr / 4.2) + rnd.uniform(-0.28, 0.28),
                0.92,
            )).normalized()

        up_ref = Vector((0.0, 0.0, 1.0)) if abs(nrm.z) < 0.90 else Vector((1.0, 0.0, 0.0))
        e1 = nrm.cross(up_ref).normalized()
        e2 = nrm.cross(e1).normalized()
        roll = rnd.uniform(0.0, math.tau)
        cr, sr = math.cos(roll), math.sin(roll)
        e1, e2 = e1 * cr + e2 * sr, -e1 * sr + e2 * cr

        tw, th, uvs = leaf_card_templates[i % len(leaf_card_templates)]
        sc = (2.10 if lod1 else 1.18) * rnd.uniform(0.84, 1.24)
        hw, hh = tw * sc * 0.5, th * sc * 0.5

        hz = max(0.0, min(1.0, (tier_z - 3.3) / 1.25))
        d_rad = min(1.0, (pos - canopy_center).length / 4.2)
        k = max(0.66, min(1.08, (0.76 + 0.24 * d_rad) * (0.82 + 0.24 * hz)))
        rgba = (min(1.0, k * 1.02), min(1.0, k * 1.00), min(1.0, k * 0.92), 1.0)

        # Emit 2-tri card quad
        q = [
            bm.verts.new(pos - e1 * hw - e2 * hh),
            bm.verts.new(pos + e1 * hw - e2 * hh),
            bm.verts.new(pos + e1 * hw + e2 * hh),
            bm.verts.new(pos - e1 * hw + e2 * hh),
        ]
        for tri in ((0, 1, 2), (0, 2, 3)):
            try:
                f = bm.faces.new((q[tri[0]], q[tri[1]], q[tri[2]]))
                f.smooth = True
                for lp, idx_c in zip(f.loops, tri):
                    lp[uvl].uv = uvs[idx_c]
                    lp[coll] = rgba
            except ValueError:
                pass

    bm.normal_update()
    suf = '_LOD1' if lod1 else ''
    me = bpy.data.meshes.new(f'acacia{suf}')
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    obj = bpy.data.objects.new(f'acacia{suf}', me)
    bpy.context.scene.collection.objects.link(obj)
    # Soft spherical normals on canopy vertices (z > 3.0) while preserving trunk cylinder normals
    normals = []
    for p in me.polygons:
        for li in p.loop_indices:
            v = me.vertices[me.loops[li].vertex_index]
            if v.co.z > 2.9:
                out = (v.co - canopy_center)
                out = out.normalized() if out.length > 1e-5 else Vector((0, 0, 1))
                n = (v.normal * 0.35 + out * 0.65).normalized()
            else:
                n = v.normal
            normals.append(n)
    me.normals_split_custom_set(normals)
    return obj


def _extract_leaf_card_templates(src_glb, max_samples=24):
    """Sample real Poly Haven leaf-card UV patches & aspect ratios from `ph_island_tree_02_hi.glb`."""
    bpy.ops.import_scene.gltf(filepath=str(src_glb))
    imported = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    templates = []
    for o in imported:
        me = o.data
        uvl = me.uv_layers.active
        if not uvl:
            continue
        leaf_mi = {
            i for i, m in enumerate(me.materials)
            if m and ('leave' in m.name.lower() or 'leaf' in m.name.lower())
        }
        if not leaf_mi:
            continue
        # Walk leaf polygons (pairs of tris forming each card quad) and extract their UV boxes
        seen = set()
        step = max(1, len(me.polygons) // (max_samples * 6))
        for pi in range(0, len(me.polygons), step):
            poly = me.polygons[pi]
            if poly.material_index not in leaf_mi:
                continue
            uvs = [uvl.data[li].uv for li in poly.loop_indices]
            u0 = max(0.01, min(u.x for u in uvs))
            u1 = min(0.99, max(u.x for u in uvs))
            v0 = max(0.01, min(u.y for u in uvs))
            v1 = min(0.99, max(u.y for u in uvs))
            if u1 - u0 < 0.08 or v1 - v0 < 0.08:
                continue
            key = (round(u0, 2), round(v0, 2), round(u1, 2), round(v1, 2))
            if key in seen:
                continue
            seen.add(key)
            # Remap V into top leaf band [LEAF_V0, LEAF_V1]
            rv0 = LEAF_V0 + (LEAF_V1 - LEAF_V0) * v0
            rv1 = LEAF_V0 + (LEAF_V1 - LEAF_V0) * v1
            aspect = (u1 - u0) / max(v1 - v0, 1e-3)
            h = 0.72
            w = max(0.45, min(1.05, h * aspect))
            templates.append((w, h, [(u0, rv0), (u1, rv0), (u1, rv1), (u0, rv1)]))
            if len(templates) >= max_samples:
                break
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    if not templates:
        # Fallback full leaf-band card
        templates.append((0.82, 0.72, [(0.04, LEAF_V0), (0.96, LEAF_V0), (0.96, LEAF_V1), (0.04, LEAF_V1)]))
    return templates


def build_acacia():
    lib.reset_scene()
    # Use airy compound feathery sprig UV cards from tree_small_02 (pinnate look fits Acacia tortilis!)
    templates = _extract_leaf_card_templates(lib.OUT_MODELS / 'ph_tree_small_02_hi.glb')
    lib.reset_scene()
    mat = _build_tree_atlas('acacia', 'tree_small_02', 'tree_small_02', style='acacia', size=512, nor_size=256)

    lod0 = _build_acacia_lod(mat, templates, seed=331, lod1=False)
    lod1 = _build_acacia_lod(mat, templates, seed=332, lod1=True)
    t0, t1 = lib.tri_count(lod0), lib.tri_count(lod1)
    if t0 > TREE_LOD0_BUDGET:
        raise RuntimeError(f'acacia: LOD0 tris {t0} > {TREE_LOD0_BUDGET}')
    if t1 > TREE_LOD1_BUDGET:
        raise RuntimeError(f'acacia: LOD1 tris {t1} > {TREE_LOD1_BUDGET}')

    out_path = lib.OUT_MODELS / 'acacia.glb'
    lib.export_textured_glb(out_path, [lod0, lod1], webp_quality=76, embed_images=True)
    nbytes, nmats, nimgs = lib.verify_textured_glb(out_path, expect_mask=True, max_mats=1)
    print(f'[v4/trees] {"acacia":12s} LOD0={t0:4d}/{TREE_LOD0_BUDGET}  LOD1={t1:3d}/{TREE_LOD1_BUDGET}  '
          f'mats={nmats} imgs={nimgs} {nbytes/1024:5.1f}KB', flush=True)


def _build_bush_lod(src_glb, name, mat, target_h, target_tris, seed, lod1=False):
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

    # Scale uniformly to natural village shrub height, base centered & sunk 4 cm
    pts = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', pts)
    pts = pts.reshape(-1, 3)
    cur_h = max(0.1, float(pts[:, 2].max() - pts[:, 2].min()))
    sc = target_h / cur_h
    pts *= sc
    pts[:, 0] -= float((pts[:, 0].min() + pts[:, 0].max()) * 0.5)
    pts[:, 1] -= float((pts[:, 1].min() + pts[:, 1].max()) * 0.5)
    pts[:, 2] -= float(pts[:, 2].min()) + 0.04
    obj.data.vertices.foreach_set('co', pts.ravel())
    obj.data.update()

    # Keep grounded stems on LOD0; on LOD1 spend 100% of tight 150-tri budget on lush leaf cards!
    roots = _find_islands(obj.data)
    uniq, counts = np.unique(roots, return_counts=True)
    stem_roots = {int(uniq[i]) for i in range(len(uniq)) if counts[i] >= 12}
    leaf_roots = {int(uniq[i]) for i in range(len(uniq)) if counts[i] < 12}

    if not lod1 and stem_roots and len(leaf_roots) >= 20:
        stem_obj = obj.copy()
        stem_obj.data = obj.data.copy()
        bpy.context.collection.objects.link(stem_obj)
        _filter_and_scale_islands(stem_obj, stem_roots, 1.0, roots=roots)
        _filter_and_scale_islands(obj, leaf_roots, 1.0, roots=roots)

        stem_budget = int(target_tris * 0.16)
        _decimate_mesh(stem_obj, stem_budget)
        if lib.tri_count(stem_obj) > stem_budget:
            # Drop smallest stem fragments if decimate hit island floor
            sr = _find_islands(stem_obj.data)
            su, sc_i = np.unique(sr, return_counts=True)
            if len(su) > 1:
                top_k = max(1, int(len(su) * stem_budget / max(lib.tri_count(stem_obj), 1)))
                top_idx = np.argsort(-sc_i)[:top_k]
                _filter_and_scale_islands(stem_obj, {int(su[i]) for i in top_idx}, 1.0, roots=sr)
                _decimate_mesh(stem_obj, stem_budget)

        leaf_budget = max(40, target_tris - lib.tri_count(stem_obj) - 6)
        max_cards = leaf_budget // 2
        kept, lroots = _select_spatial_card_islands(obj, max_cards, seed=seed)
        src_n = len(np.unique(lroots))
        boost = min(1.85, max(1.15, math.sqrt(max(1.0, src_n / max(len(kept), 1))) * 1.12))
        _filter_and_scale_islands(obj, kept, boost, roots=lroots)

        _select_only([stem_obj, obj])
        bpy.ops.object.join()
        obj = bpy.context.view_layer.objects.active
    else:
        if leaf_roots and len(leaf_roots) >= 20:
            _filter_and_scale_islands(obj, leaf_roots, 1.0, roots=roots)
            roots = _find_islands(obj.data)
        max_cards = max(30, (target_tris - 6) // 2)
        kept, roots = _select_spatial_card_islands(obj, max_cards, seed=seed)
        src_n = len(np.unique(roots))
        boost = min(2.45 if lod1 else 1.80, max(1.18, math.sqrt(max(1.0, src_n / max(len(kept), 1))) * 1.15))
        _filter_and_scale_islands(obj, kept, boost, roots=roots)

    if lib.tri_count(obj) > target_tris:
        _decimate_mesh(obj, target_tris)

    pts2 = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', pts2)
    pts2 = pts2.reshape(-1, 3)
    c_ctr = Vector(tuple(pts2.mean(axis=0)))
    c_rad = max(0.35, float(np.linalg.norm(pts2 - pts2.mean(axis=0), axis=1).mean()) * 1.35)
    _paint_canopy_vcol(obj, True, c_ctr, c_rad, float(pts2[:, 2].min()), float(pts2[:, 2].max()), is_shrub=True)
    _blend_spherical_normals(obj, c_ctr - Vector((0, 0, 0.12)), blend=0.52)

    obj.data.materials.clear()
    obj.data.materials.append(mat)
    suf = '_LOD1' if lod1 else ''
    obj.name = f'{name}{suf}'
    obj.data.name = obj.name
    while len(obj.data.uv_layers) > 1:
        obj.data.uv_layers.remove(obj.data.uv_layers[-1])
    return obj


def build_bush(name, ph_id, style, target_h, seed):
    lib.reset_scene()
    src_glb = lib.OUT_MODELS / f'ph_{ph_id}_hi.glb'
    mat = _build_shrub_material(name, ph_id, style=style, size=384, nor_size=256)

    lod0 = _build_bush_lod(src_glb, name, mat, target_h, 540, seed=seed, lod1=False)
    lod1 = _build_bush_lod(src_glb, name, mat, target_h, 136, seed=seed + 5, lod1=True)
    t0, t1 = lib.tri_count(lod0), lib.tri_count(lod1)
    if t0 > BUSH_LOD0_BUDGET:
        raise RuntimeError(f'{name}: LOD0 tris {t0} > {BUSH_LOD0_BUDGET}')
    if t1 > BUSH_LOD1_BUDGET:
        raise RuntimeError(f'{name}: LOD1 tris {t1} > {BUSH_LOD1_BUDGET}')

    out_path = lib.OUT_MODELS / f'{name}.glb'
    lib.export_textured_glb(out_path, [lod0, lod1], webp_quality=76, embed_images=True)
    nbytes, nmats, nimgs = lib.verify_textured_glb(out_path, expect_mask=True, max_mats=1)
    print(f'[v4/trees] {name:12s} LOD0={t0:4d}/{BUSH_LOD0_BUDGET}  LOD1={t1:3d}/{BUSH_LOD1_BUDGET}  '
          f'mats={nmats} imgs={nimgs} {nbytes/1024:5.1f}KB', flush=True)


def main():
    # Match v3 sycamore_a (~6.8 m tall, ~7.6 m wide) and sycamore_b (~7.4 m tall, ~6.6 m wide)
    build_sycamore('sycamore_a', 'island_tree_02', (1.92, 1.92, 2.02), seed=401)
    build_sycamore('sycamore_b', 'tree_small_02',  (1.88, 1.88, 1.58), seed=402)
    build_acacia()
    build_bush('bush_a', 'shrub_02', style='bush_lush', target_h=1.28, seed=411)
    build_bush('bush_b', 'shrub_04', style='bush_dry',  target_h=1.08, seed=412)


if __name__ == '__main__':
    main()
