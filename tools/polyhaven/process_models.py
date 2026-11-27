"""Process cached Poly Haven glTF models into Lite/High Draco WebP GLBs and render M0 contact sheet.

Usage:
  blender -b --factory-startup --python tools/polyhaven/process_models.py
  blender -b --factory-startup --python tools/polyhaven/process_models.py -- --sheet
"""
import argparse
import json
import math
import re
import struct
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = Path(__file__).resolve().parent / 'manifest.json'
CACHE_DIR = ROOT / '.cache' / 'polyhaven'
OUT_MODELS_DIR = ROOT / 'public' / 'models' / 'env'
TEX_V4_DIR = ROOT / 'public' / 'textures' / 'v4'
SHEET_PATH = ROOT / 'blender' / 'v4' / 'previews' / 'M0_contact_sheet.png'

BUDGETS = {
  'prop': {'lite': 1500, 'high': 5000},
  'rock': {'lite': 800, 'high': 3000},
  'shrub': {'lite': 600, 'high': 2000},
  'tree': {'lite': 4000, 'high': 12000},
}

# Single-clump variant picks for multi-variant Poly Haven botanical packs.
VARIANT_PICK = {
  'grass_medium_01': 'grass_medium_01_large_a_LOD0',
  'flower_gazania': 'flower_gazania_h_LOD0',
}

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

# Minimal 5x7 bitmap font for self-contained contact sheet labels.
FONT_5X7 = {
  ' ': (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
  '0': (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
  '1': (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
  '2': (0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F),
  '3': (0x1E, 0x01, 0x01, 0x0E, 0x01, 0x01, 0x1E),
  '4': (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
  '5': (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
  '6': (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
  '7': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
  '8': (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
  '9': (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
  'A': (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
  'B': (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
  'C': (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
  'D': (0x1C, 0x12, 0x11, 0x11, 0x11, 0x12, 0x1C),
  'E': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
  'F': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
  'G': (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
  'H': (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
  'I': (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
  'J': (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
  'K': (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
  'L': (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
  'M': (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
  'N': (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
  'O': (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
  'P': (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
  'Q': (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
  'R': (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
  'S': (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
  'T': (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
  'U': (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
  'V': (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
  'W': (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
  'X': (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
  'Y': (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
  'Z': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
  '_': (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1F),
  '-': (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
  '.': (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
  ':': (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00),
  '/': (0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10),
  '|': (0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
  '(': (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
  ')': (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
  '#': (0x0A, 0x1F, 0x0A, 0x0A, 0x1F, 0x0A, 0x00),
  ',': (0x00, 0x00, 0x00, 0x00, 0x04, 0x04, 0x08),
  '+': (0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00),
  '&': (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
  '<': (0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02),
  '>': (0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08),
}


def check_content_filter(asset_id):
  info_path = CACHE_DIR / asset_id / '_info.json'
  fields = [asset_id]
  if info_path.exists():
    info = json.loads(info_path.read_text(encoding='utf-8'))
    fields.append(info.get('name', ''))
    fields.extend(info.get('categories', []))
    fields.extend(info.get('tags', []))
  tokens = set()
  for f in fields:
    tokens |= set(re.findall(r'[a-z0-9]+', str(f).lower().replace('_', ' ').replace('-', ' ')))
  bad = sorted(tokens & DENY_TOKENS)
  if bad:
    raise SystemExit(f'Content filter rejected {asset_id!r}: {bad}')


def mesh_tri_count(obj):
  return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def total_tri_count(objs):
  return sum(mesh_tri_count(o) for o in objs if o.type == 'MESH')


def mesh_surface_area(obj):
  a = np.empty(len(obj.data.polygons), dtype=np.float32)
  obj.data.polygons.foreach_get('area', a)
  return float(a.sum())


def select_only(objs):
  bpy.ops.object.select_all(action='DESELECT')
  for o in objs:
    o.select_set(True)
  if objs:
    bpy.context.view_layer.objects.active = objs[0]


def apply_all_transforms(objs):
  for o in objs:
    if o.parent is not None:
      mat = o.matrix_world.copy()
      o.parent = None
      o.matrix_world = mat
  for o in list(bpy.data.objects):
    if o.type != 'MESH':
      bpy.data.objects.remove(o, do_unlink=True)
  select_only(objs)
  bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def normalize_origin_base_center(objs):
  all_pts = []
  for o in objs:
    me = o.data
    coords = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get('co', coords)
    if len(coords):
      all_pts.append(coords.reshape(-1, 3))
  if not all_pts:
    return
  pts = np.concatenate(all_pts, axis=0)
  mn = pts.min(axis=0)
  mx = pts.max(axis=0)
  offset = np.array([(mn[0] + mx[0]) * 0.5, (mn[1] + mx[1]) * 0.5, mn[2]], dtype=np.float32)
  for o in objs:
    me = o.data
    coords = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get('co', coords)
    if len(coords):
      c = coords.reshape(-1, 3) - offset
      me.vertices.foreach_set('co', c.ravel())
      me.update()


def scale_objs_uniform(objs, factor):
  for o in objs:
    me = o.data
    coords = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get('co', coords)
    if len(coords):
      me.vertices.foreach_set('co', (coords * float(factor)).ravel())
      me.update()


def dilate_rgb_under_alpha(rgb, alpha, iters=6):
  """Bleed opaque edge colors into transparent pixels so mipmaps/filtering never fringe black."""
  out = rgb.copy()
  valid = alpha > 0.25
  for _ in range(iters):
    if np.all(valid):
      break
    acc = np.zeros_like(out)
    cnt = np.zeros(alpha.shape, dtype=np.float32)
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
      sv = np.roll(valid, shift=(dy, dx), axis=(0, 1))
      sr = np.roll(out, shift=(dy, dx), axis=(0, 1))
      m = (~valid) & sv
      acc[m] += sr[m]
      cnt[m] += 1.0
    fill = cnt > 0
    out[fill] = acc[fill] / cnt[fill, None]
    valid = valid | fill
  return out


def wire_alpha_mask(nt, tex_node, pbr, cutoff=0.5):
  """Wire TexImage.Alpha -> Math(GREATER_THAN, 0.5) -> Principled.Alpha so Blender's glTF
  exporter strictly emits alphaMode='MASK' (alphaCutoff=0.5), never BLEND."""
  alpha_in = pbr.inputs['Alpha']
  for lk in list(alpha_in.links):
    nt.links.remove(lk)
  gt = nt.nodes.new('ShaderNodeMath')
  gt.operation = 'GREATER_THAN'
  gt.inputs[1].default_value = float(cutoff)
  nt.links.new(tex_node.outputs['Alpha'], gt.inputs[0])
  nt.links.new(gt.outputs['Value'], alpha_in)


def clear_alpha_to_opaque(nt, pbr):
  alpha_in = pbr.inputs.get('Alpha')
  if alpha_in:
    for lk in list(alpha_in.links):
      nt.links.remove(lk)
    alpha_in.default_value = 1.0
  # Clear transmission so glTF never emits transparency extensions on opaque props
  for tname in ('Transmission Weight', 'Transmission'):
    tin = pbr.inputs.get(tname)
    if tin:
      for lk in list(tin.links):
        nt.links.remove(lk)
      tin.default_value = 0.0


def composite_alpha_mask(aid, mat, pbr):
  """Composite Poly Haven's cached *_alpha_*.png into RGBA diffuse and wire MASK (cutoff 0.5)."""
  bc_in = pbr.inputs.get('Base Color')
  if not bc_in or not bc_in.is_linked:
    return False
  tex_node = bc_in.links[0].from_node
  if tex_node.type != 'TEX_IMAGE':
    for inp in tex_node.inputs:
      if inp.is_linked and inp.links[0].from_node.type == 'TEX_IMAGE':
        tex_node = inp.links[0].from_node
        break
  if tex_node.type != 'TEX_IMAGE' or tex_node.image is None:
    return False

  tex_dir = CACHE_DIR / aid / 'textures'
  if not tex_dir.exists():
    return False
  img_name = Path(bpy.path.abspath(tex_node.image.filepath)).name.lower() if tex_node.image.filepath else tex_node.image.name.lower()
  alpha_file = None
  if 'leaves' in img_name:
    cand = sorted(tex_dir.glob('*leaves_alpha*'))
    if cand:
      alpha_file = cand[0]
  if alpha_file is None:
    cand = [p for p in sorted(tex_dir.glob('*alpha*')) if 'leaves' not in p.name.lower()]
    if cand:
      alpha_file = cand[0]
  if alpha_file is None:
    return False

  diff_img = tex_node.image
  w, h = diff_img.size[0], diff_img.size[1]
  if w == 0 or h == 0:
    return False
  diff_buf = np.empty(h * w * 4, dtype=np.float32)
  diff_img.pixels.foreach_get(diff_buf)
  diff_rgba = diff_buf.reshape(h, w, 4)

  a_img = bpy.data.images.load(str(alpha_file))
  aw, ah = a_img.size[0], a_img.size[1]
  a_buf = np.empty(ah * aw * 4, dtype=np.float32)
  a_img.pixels.foreach_get(a_buf)
  bpy.data.images.remove(a_img)
  a_ch = a_buf.reshape(ah, aw, 4)[:, :, 0]
  if (aw, ah) != (w, h):
    ys = np.linspace(0, ah - 1, h).astype(np.int32)
    xs = np.linspace(0, aw - 1, w).astype(np.int32)
    a_ch = a_ch[np.ix_(ys, xs)]

  # On tree_small_02, the baked alpha PNG has stray Voronoi rays outside the real green sprig;
  # suppress alpha on pure-black pixels and on the right-hand Voronoi bleed margin (u > 0.845).
  if aid == 'tree_small_02':
    diff_max = diff_rgba[:, :, :3].max(axis=2)
    a_ch = np.where(diff_max < 0.03, 0.0, a_ch)
    xs_norm = (np.arange(w, dtype=np.float32) + 0.5) / w
    a_ch = np.where(xs_norm[None, :] > 0.845, 0.0, a_ch)

  rgb_clean = dilate_rgb_under_alpha(diff_rgba[:, :, :3], a_ch, iters=6)
  out_rgba = np.empty((h, w, 4), dtype=np.float32)
  out_rgba[:, :, :3] = rgb_clean
  out_rgba[:, :, 3] = np.clip(a_ch, 0.0, 1.0)

  new_img = bpy.data.images.new(f'{diff_img.name}_rgba', width=w, height=h, alpha=True, float_buffer=False)
  new_img.colorspace_settings.name = 'sRGB'
  new_img.pixels.foreach_set(out_rgba.ravel())
  new_img.pack()
  tex_node.image = new_img

  wire_alpha_mask(mat.node_tree, tex_node, pbr, cutoff=0.5)
  return True


def sanitize_materials(aid, is_foliage):
  """Wire MASK (cutoff 0.5) for alpha-cutout foliage materials and strictly OPAQUE for all others."""
  for mat in bpy.data.materials:
    nt = mat.node_tree
    if not nt:
      continue
    pbr = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not pbr:
      continue
    if is_foliage and composite_alpha_mask(aid, mat, pbr):
      continue
    clear_alpha_to_opaque(nt, pbr)


def consolidate_lantern(meshes):
  """Join brass_diya_lantern into 1 mesh with at most 2 opaque materials/primitives (brass + warm glow)."""
  select_only(meshes)
  if len(meshes) > 1:
    bpy.ops.object.join()
  obj = bpy.context.view_layer.objects.active

  # Pick primary brass material (opaque PBR with textures)
  brass_mat = next((m for m in bpy.data.materials if m.name == 'brass_diya_lantern'), None)
  if brass_mat is None:
    brass_mat = obj.material_slots[0].material
  pbr_b = next((n for n in brass_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
  if pbr_b:
    clear_alpha_to_opaque(brass_mat.node_tree, pbr_b)

  # Build single opaque warm golden glow material for glass + flame core
  glow_mat = bpy.data.materials.new('brass_diya_lantern_glow')
  nt = glow_mat.node_tree
  pbr_g = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
  pbr_g.inputs['Base Color'].default_value = (0.96, 0.72, 0.28, 1.0)
  pbr_g.inputs['Roughness'].default_value = 0.28
  pbr_g.inputs['Metallic'].default_value = 0.0
  if 'Emission Color' in pbr_g.inputs:
    pbr_g.inputs['Emission Color'].default_value = (1.0, 0.70, 0.22, 1.0)
    pbr_g.inputs['Emission Strength'].default_value = 0.85
  clear_alpha_to_opaque(nt, pbr_g)

  old_slots = [s.material.name.lower() if s.material else '' for s in obj.material_slots]
  me = obj.data
  me.materials.clear()
  me.materials.append(brass_mat)
  me.materials.append(glow_mat)
  for poly in me.polygons:
    old_name = old_slots[poly.material_index] if poly.material_index < len(old_slots) else ''
    poly.material_index = 1 if ('glass' in old_name or 'flame' in old_name) else 0
  me.update()
  return [obj]


def triangulate_obj(obj):
  select_only([obj])
  mod = obj.modifiers.new('Tri', 'TRIANGULATE')
  mod.quad_method = 'BEAUTY'
  bpy.ops.object.modifier_apply(modifier=mod.name)


def decimate_solid(obj, target_tris, preserve_uv=True):
  triangulate_obj(obj)
  cur = mesh_tri_count(obj)
  if cur <= target_tris:
    return obj
  select_only([obj])
  ratio = max(0.002, (target_tris * 0.96) / cur)
  mod = obj.modifiers.new('Dec', 'DECIMATE')
  mod.decimate_type = 'COLLAPSE'
  mod.ratio = min(1.0, ratio)
  if preserve_uv:
    mod.delimit = {'UV', 'MATERIAL'}
  bpy.ops.object.modifier_apply(modifier=mod.name)
  triangulate_obj(obj)

  cur = mesh_tri_count(obj)
  if cur > target_tris:
    ratio = max(0.002, (target_tris * 0.95) / cur)
    mod = obj.modifiers.new('Dec2', 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = min(1.0, ratio)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    triangulate_obj(obj)
  return obj


def build_solid_wicker_shell(ref_obj, mat, radial_segs=28, height_segs=6, inset=0.0):
  """Create a watertight open-top rounded-rectangular basket shell matching ref_obj's exact
  contour, UV-mapped cleanly onto the continuous woven panels of wicker_basket_01_diff_2k.jpg."""
  me_ref = ref_obj.data
  coords = np.empty(len(me_ref.vertices) * 3, dtype=np.float32)
  me_ref.vertices.foreach_get('co', coords)
  coords = coords.reshape(-1, 3)
  mn, mx = coords.min(axis=0), coords.max(axis=0)
  cx, cy = float((mn[0] + mx[0]) * 0.5), float((mn[1] + mx[1]) * 0.5)
  z0, z1 = float(mn[2]), float(mx[2])
  hx = float((mx[0] - mn[0]) * 0.5) - inset
  hy = float((mx[1] - mn[1]) * 0.5) - inset
  h = max(0.02, z1 - z0 - inset)

  # Build open-top rounded-rectangle loft (superellipse n=3.2 tapers gently toward base)
  bm = bmesh.new()
  uv_layer = bm.loops.layers.uv.new('UVMap')

  rings = []
  for hi in range(height_segs + 1):
    t = hi / float(height_segs)
    z = z0 + inset * 0.5 + t * h
    taper = 0.86 + 0.14 * t
    ring = []
    for ri in range(radial_segs):
      ang = (2.0 * math.pi * ri) / radial_segs
      ca, sa = math.cos(ang), math.sin(ang)
      # Superellipse gives authentic rounded rectangular basket footprint
      sx = math.copysign(abs(ca) ** 0.62, ca) * hx * taper
      sy = math.copysign(abs(sa) ** 0.62, sa) * hy * taper
      ring.append(bm.verts.new((cx + sx, cy + sy, z)))
    rings.append(ring)

  # Side walls
  for hi in range(height_segs):
    r0, r1 = rings[hi], rings[hi + 1]
    v0 = 0.06 + (hi / height_segs) * 0.56
    v1 = 0.06 + ((hi + 1) / height_segs) * 0.56
    for ri in range(radial_segs):
      rn = (ri + 1) % radial_segs
      u0 = 0.05 + (ri / radial_segs) * 0.60
      u1 = 0.05 + ((ri + 1) / radial_segs) * 0.60
      f = bm.faces.new((r0[ri], r0[rn], r1[rn], r1[ri]))
      for lp, uv in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
        lp[uv_layer].uv = uv

  # Solid woven bottom (fan around center)
  bot_c = bm.verts.new((cx, cy, z0 + inset * 0.5))
  for ri in range(radial_segs):
    rn = (ri + 1) % radial_segs
    f = bm.faces.new((bot_c, rings[0][rn], rings[0][ri]))
    ang0 = (2.0 * math.pi * ri) / radial_segs
    ang1 = (2.0 * math.pi * rn) / radial_segs
    for lp, uv in zip(f.loops, (
      (0.35, 0.34),
      (0.35 + 0.25 * math.cos(ang1), 0.34 + 0.25 * math.sin(ang1)),
      (0.35 + 0.25 * math.cos(ang0), 0.34 + 0.25 * math.sin(ang0)),
    )):
      lp[uv_layer].uv = uv

  bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
  mesh = bpy.data.meshes.new('wicker_shell')
  bm.to_mesh(mesh)
  bm.free()
  mesh.materials.append(mat)
  shell = bpy.data.objects.new('wicker_shell', mesh)
  bpy.context.collection.objects.link(shell)

  # Shrinkwrap outer profile onto the real high-poly basket so silhouette matches closely
  if inset == 0.0:
    sw = shell.modifiers.new('SW', 'SHRINKWRAP')
    sw.target = ref_obj
    sw.wrap_method = 'NEAREST_SURFACEPOINT'
    sw.wrap_mode = 'ON_SURFACE'
    select_only([shell])
    bpy.ops.object.modifier_apply(modifier=sw.name)

    sm = shell.modifiers.new('Smooth', 'SMOOTH')
    sm.factor = 0.45
    sm.iterations = 2
    bpy.ops.object.modifier_apply(modifier=sm.name)

    # Give the basket real solid rim & inner wall thickness (1.1 cm)
    sol = shell.modifiers.new('Solid', 'SOLIDIFY')
    sol.thickness = 0.011
    sol.offset = -1.0
    sol.use_rim = True
    bpy.ops.object.modifier_apply(modifier=sol.name)

    # Remap the top rim strip UVs onto the horizontal braided wicker band (v in [0.78, 0.94])
    me_s = shell.data
    uv_l = me_s.uv_layers.active
    for poly in me_s.polygons:
      if poly.center.z > z1 - 0.015 and abs(poly.normal.z) > 0.45:
        for li in poly.loop_indices:
          u_cur, _ = uv_l.data[li].uv
          uv_l.data[li].uv = (0.06 + (u_cur % 0.70), 0.86)
    me_s.update()

  triangulate_obj(shell)
  return shell


def process_wicker_basket(obj, budget, is_lite):
  """Keep wicker_basket_01 solid and hole-free: on Lite use a shrinkwrapped solid woven shell
  with real rim thickness (~950 tris); on High combine decimated outer woven reeds with a
  recessed solid inner liner so zero pinholes show through."""
  mat = obj.material_slots[0].material
  if is_lite:
    shell = build_solid_wicker_shell(obj, mat, radial_segs=28, height_segs=6, inset=0.0)
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh_tri_count(shell) > budget:
      decimate_solid(shell, budget, preserve_uv=True)
    return [shell]
  else:
    liner = build_solid_wicker_shell(obj, mat, radial_segs=20, height_segs=3, inset=0.006)
    reed_budget = max(500, budget - mesh_tri_count(liner) - 40)
    decimate_solid(obj, reed_budget, preserve_uv=True)
    select_only([obj, liner])
    bpy.ops.object.join()
    merged = bpy.context.view_layer.objects.active
    triangulate_obj(merged)
    return [merged]


def find_vertex_islands(me):
  """Fast Union-Find connected components across mesh vertices; returns per-poly island root id."""
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
  pfirst = lverts[lstart]
  return np.fromiter((find(int(v)) for v in pfirst), dtype=np.int32, count=n_polys)


def keep_poly_islands_and_scale(obj, keep_roots_set, island_scale=1.0, roots=None):
  me = obj.data
  n_polys = len(me.polygons)
  if roots is None:
    roots = find_vertex_islands(me)

  keep_poly = np.fromiter((int(r) in keep_roots_set for r in roots), dtype=bool, count=n_polys)
  if not np.all(keep_poly):
    select_only([obj])
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

  if abs(island_scale - 1.0) > 1e-3 and len(me.polygons) > 0:
    roots2 = find_vertex_islands(me)
    n_verts = len(me.vertices)
    coords = np.empty(n_verts * 3, dtype=np.float32)
    me.vertices.foreach_get('co', coords)
    coords = coords.reshape(-1, 3)

    lstart = np.empty(len(me.polygons), dtype=np.int32)
    ltot = np.empty(len(me.polygons), dtype=np.int32)
    lverts = np.empty(len(me.loops), dtype=np.int32)
    me.polygons.foreach_get('loop_start', lstart)
    me.polygons.foreach_get('loop_total', ltot)
    me.loops.foreach_get('vertex_index', lverts)

    vert_root = np.full(n_verts, -1, dtype=np.int32)
    for pi in range(len(me.polygons)):
      s = lstart[pi]
      vert_root[lverts[s : s + ltot[pi]]] = roots2[pi]

    valid_v = np.nonzero(vert_root >= 0)[0]
    _, inv = np.unique(vert_root[valid_v], return_inverse=True)
    counts = np.bincount(inv).astype(np.float32)
    cx = np.bincount(inv, weights=coords[valid_v, 0]) / counts
    cy = np.bincount(inv, weights=coords[valid_v, 1]) / counts
    cz = np.bincount(inv, weights=coords[valid_v, 2]) / counts
    centers = np.stack([cx, cy, cz], axis=1)
    coords[valid_v] = centers[inv] + (coords[valid_v] - centers[inv]) * float(island_scale)
    me.vertices.foreach_set('co', coords.ravel())
    me.update()


def select_spatial_islands(obj, target_count, seed=42, roots=None, prefer_large=False, min_polys=0):
  """Select up to target_count whole islands distributed evenly across 3D space.
  When prefer_large=True, prioritize higher-area islands within each 3D voxel cell."""
  me = obj.data
  if roots is None:
    roots = find_vertex_islands(me)
  centers = np.empty(len(me.polygons) * 3, dtype=np.float32)
  me.polygons.foreach_get('center', centers)
  centers = centers.reshape(-1, 3)
  areas = np.empty(len(me.polygons), dtype=np.float32)
  me.polygons.foreach_get('area', areas)

  uniq, inv, counts = np.unique(roots, return_inverse=True, return_counts=True)
  i_areas = np.bincount(inv, weights=areas)

  # Optional filter to keep only large compound frond islands when enough exist
  eligible = np.arange(len(uniq))
  if min_polys > 0:
    big = np.nonzero(counts >= min_polys)[0]
    if len(big) >= target_count:
      eligible = big

  if len(eligible) <= target_count:
    return set(int(uniq[i]) for i in eligible), roots

  icx = np.bincount(inv, weights=centers[:, 0]) / counts
  icy = np.bincount(inv, weights=centers[:, 1]) / counts
  icz = np.bincount(inv, weights=centers[:, 2]) / counts
  ic = np.stack([icx[eligible], icy[eligible], icz[eligible]], axis=1)

  mn = ic.min(axis=0)
  span = np.maximum(ic.max(axis=0) - mn, 1e-4)
  g = max(2, int(round((target_count / 1.5) ** (1.0 / 3.0))))
  idx = np.clip(((ic - mn) / span * g).astype(np.int32), 0, g - 1)
  cell_keys = idx[:, 0] * (g * g) + idx[:, 1] * g + idx[:, 2]

  rng = np.random.default_rng(seed)
  buckets = defaultdict(list)
  if prefer_large:
    # Sort ascending by area so pop() yields the largest islands first per spatial cell
    order = np.argsort(i_areas[eligible])
  else:
    order = rng.permutation(len(eligible))
  for pos in order:
    orig_i = eligible[pos]
    buckets[int(cell_keys[pos])].append(int(uniq[orig_i]))

  keys = sorted(buckets.keys())
  rng.shuffle(keys)
  kept = []
  while len(kept) < target_count and keys:
    next_keys = []
    for k in keys:
      b = buckets[k]
      if b:
        kept.append(b.pop())
        if len(kept) >= target_count:
          break
        if b:
          next_keys.append(k)
    keys = next_keys
  return set(kept), roots


def convert_islands_to_uv_cards(obj, keep_roots_set, source_area, scale_cap=3.0, min_scale=1.0, roots=None):
  """Replace each kept leaf/frond island with a crisp 2-tri UV-mapped alpha-cutout card quad
  fitted to its exact 3D tangent plane and affine UV box, then scaled about its centroid by
  clamp(sqrt(source_area / kept_area), min_scale, scale_cap) to preserve full lush foliage area."""
  me = obj.data
  if roots is None:
    roots = find_vertex_islands(me)
  mat = obj.material_slots[0].material if obj.material_slots else None

  n_polys = len(me.polygons)
  n_verts = len(me.vertices)
  coords = np.empty(n_verts * 3, dtype=np.float32)
  me.vertices.foreach_get('co', coords)
  coords = coords.reshape(-1, 3)

  areas = np.empty(n_polys, dtype=np.float32)
  me.polygons.foreach_get('area', areas)
  lstart = np.empty(n_polys, dtype=np.int32)
  ltot = np.empty(n_polys, dtype=np.int32)
  lverts = np.empty(len(me.loops), dtype=np.int32)
  me.polygons.foreach_get('loop_start', lstart)
  me.polygons.foreach_get('loop_total', ltot)
  me.loops.foreach_get('vertex_index', lverts)

  uv_layer = me.uv_layers.active
  uvs = np.empty(len(me.loops) * 2, dtype=np.float32)
  uv_layer.data.foreach_get('uv', uvs)
  uvs = uvs.reshape(-1, 2)

  # Group polygon indices belonging to each kept island
  island_polys = defaultdict(list)
  kept_area = 0.0
  for pi in range(n_polys):
    r = int(roots[pi])
    if r in keep_roots_set:
      island_polys[r].append(pi)
      kept_area += float(areas[pi])

  if not island_polys:
    return obj

  # Compute area-preserving card scale factor: sqrt(source_area / kept_area), capped at scale_cap.
  area_ratio = source_area / max(kept_area, 1e-6)
  scale_factor = max(min_scale, min(scale_cap, math.sqrt(max(1.0, area_ratio))))

  bm = bmesh.new()
  bm_uv = bm.loops.layers.uv.new('UVMap')

  for r, plist in island_polys.items():
    # Gather loop vertices and UVs of this island
    loop_ids = []
    for pi in plist:
      s = int(lstart[pi])
      loop_ids.extend(range(s, s + int(ltot[pi])))
    l_arr = np.asarray(loop_ids, dtype=np.int32)
    pts = coords[lverts[l_arr]]
    uv_pts = uvs[l_arr]
    if len(pts) < 3:
      continue

    c = pts.mean(axis=0)
    rel = pts - c
    # PCA tangent plane of the leaf / compound sprig
    _, _, vt = np.linalg.svd(rel, full_matrices=False)
    e1, e2 = vt[0], vt[1]
    s_proj = rel @ e1
    t_proj = rel @ e2
    s0, s1 = float(s_proj.min()), float(s_proj.max())
    t0, t1 = float(t_proj.min()), float(t_proj.max())
    hs = max((s1 - s0) * 0.5, 1e-4)
    ht = max((t1 - t0) * 0.5, 1e-4)
    sc = (s0 + s1) * 0.5
    tc = (t0 + t1) * 0.5
    c_mid = c + sc * e1 + tc * e2

    # Least-squares affine mapping (s - sc, t - tc, 1) -> (u, v)
    X = np.stack([s_proj - sc, t_proj - tc, np.ones_like(s_proj)], axis=1)
    A, _, _, _ = np.linalg.lstsq(X, uv_pts, rcond=None)
    u_min = uv_pts.min(axis=0)
    u_max = uv_pts.max(axis=0)

    corner_st = [(-hs, -ht), (hs, -ht), (hs, ht), (-hs, ht)]
    q_verts = []
    q_uvs = []
    for ds, dt in corner_st:
      pos = c_mid + (ds * scale_factor) * e1 + (dt * scale_factor) * e2
      uv_c = np.array([ds, dt, 1.0], dtype=np.float32) @ A
      uv_c = np.clip(uv_c, u_min, u_max)
      q_verts.append(bm.verts.new((float(pos[0]), float(pos[1]), float(pos[2]))))
      q_uvs.append((float(uv_c[0]), float(uv_c[1])))

    # Emit 2 triangles directly (avoids extra triangulate pass)
    for tri in ((0, 1, 2), (0, 2, 3)):
      try:
        f = bm.faces.new((q_verts[tri[0]], q_verts[tri[1]], q_verts[tri[2]]))
        for lp, idx_c in zip(f.loops, tri):
          lp[bm_uv].uv = q_uvs[idx_c]
      except ValueError:
        pass

  new_me = bpy.data.meshes.new(f'{obj.name}_cards')
  bm.to_mesh(new_me)
  bm.free()
  if mat:
    new_me.materials.append(mat)
  new_obj = bpy.data.objects.new(f'{obj.name}_cards', new_me)
  bpy.context.collection.objects.link(new_obj)
  bpy.data.objects.remove(obj, do_unlink=True)
  return new_obj


def duplicate_obj(obj, name):
  cp = obj.copy()
  cp.data = obj.data.copy()
  cp.name = name
  bpy.context.collection.objects.link(cp)
  return cp


def transform_mesh_verts(obj, matrix):
  me = obj.data
  coords = np.empty(len(me.vertices) * 3, dtype=np.float32)
  me.vertices.foreach_get('co', coords)
  pts = coords.reshape(-1, 3)
  m = np.array(matrix, dtype=np.float32)
  pts_h = np.concatenate([pts, np.ones((len(pts), 1), dtype=np.float32)], axis=1)
  out = (pts_h @ m.T)[:, :3]
  me.vertices.foreach_set('co', out.ravel())
  me.update()


def prepare_single_clump_shrub(aid, meshes):
  """Ensure every shrub is ONE bushy, grounded clump (>= 0.6 m tall)."""
  if aid == 'shrub_02':
    # Combine the three bushiest variants (shrub_02_c, shrub_02_b @ 115 deg, shrub_02_a @ 235 deg)
    # centered at (0,0,0) into ONE dense, 360-degree bushy village shrub.
    c_obj = next((o for o in meshes if o.name == 'shrub_02_c'), meshes[0])
    b_obj = next((o for o in meshes if o.name == 'shrub_02_b'), None)
    a_obj = next((o for o in meshes if o.name == 'shrub_02_a'), None)
    keep = [o for o in (c_obj, b_obj, a_obj) if o is not None]
    for o in meshes:
      if o not in keep:
        bpy.data.objects.remove(o, do_unlink=True)
    apply_all_transforms(keep)
    for o, deg in zip(keep, (0.0, 115.0, 235.0)):
      normalize_origin_base_center([o])
      if deg:
        transform_mesh_verts(o, Matrix.Rotation(math.radians(deg), 4, 'Z'))
    select_only(keep)
    if len(keep) > 1:
      bpy.ops.object.join()
    return [bpy.context.view_layer.objects.active]

  if aid == 'shrub_04':
    # shrub_04 ships 4 tiny 0.21m shoots side-by-side along world X ([-0.02, 0.56]); gather the
    # 3 bushiest shoots centered at (0,0,0) rotated 0/120/240 deg with gentle splay and enlarge
    # into ONE lush 0.85 m tall village bush.
    apply_all_transforms(meshes)
    src = meshes[0]
    me = src.data
    roots = find_vertex_islands(me)
    ctrs = np.empty(len(me.polygons) * 3, dtype=np.float32)
    me.polygons.foreach_get('center', ctrs)
    ctrs = ctrs.reshape(-1, 3)
    uniq, inv = np.unique(roots, return_inverse=True)
    counts = np.bincount(inv).astype(np.float32)
    cx = np.bincount(inv, weights=ctrs[:, 0]) / counts

    # World X bounds of shoots 2, 3, 4 (skip smallest shoot 1 at x ~ 0.00)
    shoot_ranges = [(0.08, 0.25, 0.0), (0.25, 0.41, 120.0), (0.41, 0.60, 240.0)]
    clumps = []
    for x0, x1, azim_deg in shoot_ranges:
      kept = {int(uniq[i]) for i in range(len(uniq)) if x0 <= cx[i] <= x1}
      if not kept:
        continue
      cp = duplicate_obj(src, f'shrub_04_s_{int(azim_deg)}')
      keep_poly_islands_and_scale(cp, kept, island_scale=1.0, roots=roots)
      normalize_origin_base_center([cp])
      # Tilt slightly outward (14 deg) and arrange at 120 deg intervals around shared root base
      m = Matrix.Rotation(math.radians(azim_deg), 4, 'Z') @ Matrix.Rotation(math.radians(14.0), 4, 'X')
      transform_mesh_verts(cp, m)
      clumps.append(cp)

    bpy.data.objects.remove(src, do_unlink=True)
    select_only(clumps)
    if len(clumps) > 1:
      bpy.ops.object.join()
    bush = bpy.context.view_layer.objects.active
    normalize_origin_base_center([bush])
    # Scale uniformly to 0.85 m tall (>= 0.6 m real-world village bush)
    pts = np.empty(len(bush.data.vertices) * 3, dtype=np.float32)
    bush.data.vertices.foreach_get('co', pts)
    h_cur = float(pts.reshape(-1, 3)[:, 2].max())
    if h_cur > 1e-3:
      scale_objs_uniform([bush], 0.85 / h_cur)
    normalize_origin_base_center([bush])
    return [bush]

  return meshes


def decimate_foliage_shrub(aid, obj, target_tris, is_lite, seed=42):
  """Spend >=75% of budget on alpha-cutout leaf/blade cards, preserve grounded stems on woody
  shrubs, and scale surviving cards by sqrt(source_area / kept_area) (cap 3) for lush fullness."""
  triangulate_obj(obj)
  source_area = mesh_surface_area(obj)
  roots = find_vertex_islands(obj.data)
  uniq, counts = np.unique(roots, return_counts=True)
  med_tris = float(np.median(counts)) if len(counts) else 1.0

  # 1. Woody shrubs (shrub_02, shrub_04): split stems (>= 80 tris) vs leaves (< 80 tris).
  stem_thresh = max(80, int(med_tris * 2.5))
  stem_roots = {int(uniq[i]) for i in range(len(uniq)) if counts[i] >= stem_thresh}
  leaf_roots = {int(uniq[i]) for i in range(len(uniq)) if counts[i] < stem_thresh}

  if aid in ('shrub_02', 'shrub_04') and stem_roots and len(leaf_roots) >= 20:
    stem_obj = duplicate_obj(obj, f'{obj.name}_stems')
    keep_poly_islands_and_scale(stem_obj, stem_roots, island_scale=1.0, roots=roots)
    keep_poly_islands_and_scale(obj, leaf_roots, island_scale=1.0, roots=roots)
    leaf_src_area = mesh_surface_area(obj)

    # Decimate woody stems hard (keep primary grounded branches, ~18% of budget)
    stem_budget = int(target_tris * 0.18)
    decimate_solid(stem_obj, stem_budget, preserve_uv=True)
    while mesh_tri_count(stem_obj) > stem_budget:
      sr = find_vertex_islands(stem_obj.data)
      su, sc = np.unique(sr, return_counts=True)
      if len(su) <= 2:
        decimate_solid(stem_obj, stem_budget, preserve_uv=False)
        break
      keep_k = max(2, min(len(su) - 1, int(len(su) * (stem_budget * 0.88) / max(mesh_tri_count(stem_obj), 1))))
      top_idx = np.argsort(-sc)[:keep_k]
      keep_poly_islands_and_scale(stem_obj, {int(su[i]) for i in top_idx}, island_scale=1.0, roots=sr)
      triangulate_obj(stem_obj)

    leaf_budget = max(80, target_tris - mesh_tri_count(stem_obj) - 10)
    l_roots = find_vertex_islands(obj.data)
    l_uniq = np.unique(l_roots)
    # 2 tris per alpha-cutout leaf card -> fits 230+ lush leaves on Lite and all leaves on High!
    max_cards = leaf_budget // 2
    kept_set, l_roots = select_spatial_islands(obj, min(len(l_uniq), max_cards), seed=seed, roots=l_roots, prefer_large=True)
    # Target lush fullness (boost airy willow shrub_02 leaves slightly so it reads bushy at distance)
    min_sc = 1.65 if aid == 'shrub_02' else 1.45
    target_area = leaf_src_area * (2.6 if aid == 'shrub_02' else 2.2)
    leaf_cards = convert_islands_to_uv_cards(obj, kept_set, source_area=target_area, scale_cap=3.0, min_scale=min_sc, roots=l_roots)

    select_only([stem_obj, leaf_cards])
    bpy.ops.object.join()
    merged = bpy.context.view_layer.objects.active
    triangulate_obj(merged)
    return merged

  # 2. Grass clump (grass_medium_01_large_a_LOD0: 311 arched blades):
  #    Preserve genuine narrow arched blade geometry in BOTH Lite and High (never flattening curved
  #    blades into wide square quads), dropping whole blades on Lite and scaling surviving blades
  #    by sqrt(source_area / kept_area) (cap 3) so both LODs read as dense feathery grass tufts.
  if aid == 'grass_medium_01':
    # First drop whole blades to fit target blade count (Lite ~140 blades at ~4 tris; High all 311 at ~6 tris)
    want_blades = 145 if is_lite else len(uniq)
    if len(uniq) > want_blades:
      kept_set, roots = select_spatial_islands(obj, want_blades, seed=seed, roots=roots, prefer_large=True)
      keep_poly_islands_and_scale(obj, kept_set, island_scale=1.0, roots=roots)
    select_only([obj])
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.dissolve_limited(angle_limit=math.radians(38.0 if is_lite else 28.0), delimit={'UV'})
    bpy.ops.object.mode_set(mode='OBJECT')
    triangulate_obj(obj)
    if mesh_tri_count(obj) > target_tris:
      decimate_solid(obj, target_tris, preserve_uv=True)
    step = 0
    while mesh_tri_count(obj) > target_tris and step < 5:
      step += 1
      r2 = find_vertex_islands(obj.data)
      u2 = np.unique(r2)
      keep_n = max(30, min(len(u2) - 1, int(len(u2) * (target_tris * 0.94) / max(mesh_tri_count(obj), 1))))
      ks2, r2 = select_spatial_islands(obj, keep_n, seed=seed + step * 3, roots=r2, prefer_large=True)
      keep_poly_islands_and_scale(obj, ks2, island_scale=1.0, roots=r2)
      triangulate_obj(obj)
    kept_area = mesh_surface_area(obj)
    sc = max(1.15, min(3.0, math.sqrt(max(1.0, source_area / max(kept_area, 1e-6)))))
    keep_poly_islands_and_scale(obj, set(int(x) for x in np.unique(find_vertex_islands(obj.data))), island_scale=sc)
    return obj

  # 3. Flowering clump (flower_gazania_h_LOD0): keep whole rosette leaves + blooms, area-matched scale.
  if is_lite:
    max_cards = (target_tris - 10) // 2
    kept_set, roots = select_spatial_islands(obj, min(len(uniq), max_cards), seed=seed, roots=roots, prefer_large=True)
    return convert_islands_to_uv_cards(obj, kept_set, source_area=source_area * 1.4, scale_cap=3.0, min_scale=1.2, roots=roots)
  else:
    if mesh_tri_count(obj) > target_tris:
      select_only([obj])
      bpy.ops.object.mode_set(mode='EDIT')
      bpy.ops.mesh.select_all(action='SELECT')
      bpy.ops.mesh.dissolve_limited(angle_limit=math.radians(20.0), delimit={'UV'})
      bpy.ops.object.mode_set(mode='OBJECT')
      triangulate_obj(obj)
    if mesh_tri_count(obj) > target_tris:
      r2 = find_vertex_islands(obj.data)
      u2, c2 = np.unique(r2, return_counts=True)
      keep_n = max(40, int(len(u2) * (target_tris * 0.93) / max(mesh_tri_count(obj), 1)))
      ks2, r2 = select_spatial_islands(obj, keep_n, seed=seed, roots=r2, prefer_large=True)
      keep_poly_islands_and_scale(obj, ks2, island_scale=1.0, roots=r2)
      triangulate_obj(obj)
    if mesh_tri_count(obj) > target_tris:
      decimate_solid(obj, target_tris, preserve_uv=True)
    kept_area = mesh_surface_area(obj)
    if kept_area < source_area:
      sc = min(3.0, math.sqrt(source_area / max(kept_area, 1e-6)))
      keep_poly_islands_and_scale(obj, set(int(x) for x in np.unique(find_vertex_islands(obj.data))), island_scale=sc)
    return obj


def decimate_tree(aid, obj, target_tris, is_lite, seed=42):
  """Split tree into trunk, branches, and leaves: decimate trunk/branches hard (dropping invisible
  twigs) and spend ~87% of triangle budget on 2-tri alpha-cutout leaf/frond cards scaled by
  sqrt(source_area / kept_area) (cap 3) for a closed, lush crown silhouette in both LODs."""
  triangulate_obj(obj)
  select_only([obj])
  bpy.ops.object.mode_set(mode='EDIT')
  bpy.ops.mesh.select_all(action='SELECT')
  bpy.ops.mesh.separate(type='MATERIAL')
  bpy.ops.object.mode_set(mode='OBJECT')

  parts = [o for o in bpy.data.objects if o.type == 'MESH']
  trunk_parts, branch_parts, leaf_parts = [], [], []
  for p in parts:
    mname = (p.material_slots[0].material.name.lower() if p.material_slots and p.material_slots[0].material else '')
    if 'leave' in mname or 'leaf' in mname or 'foliage' in mname:
      leaf_parts.append(p)
    elif 'branch' in mname or 'twig' in mname:
      branch_parts.append(p)
    else:
      trunk_parts.append(p)

  # Spend ~87% of budget on leaves, ~9% trunk, ~4% primary branches (drop invisible fine twigs)
  trunk_budget = int(target_tris * 0.09)
  branch_budget = int(target_tris * 0.04)

  for p in trunk_parts:
    # Keep only the main structural trunk islands (top 8/20) so stray twigs don't steal tris
    tr = find_vertex_islands(p.data)
    tu, tc = np.unique(tr, return_counts=True)
    keep_t = 8 if is_lite else 20
    if len(tu) > keep_t:
      top_idx = np.argsort(-tc)[:keep_t]
      keep_poly_islands_and_scale(p, {int(tu[i]) for i in top_idx}, island_scale=1.0, roots=tr)
    decimate_solid(p, trunk_budget, preserve_uv=True)

  for p in branch_parts:
    # Keep only the thickest primary limbs supporting the canopy; discard fine invisible twigs
    br = find_vertex_islands(p.data)
    bu, bc = np.unique(br, return_counts=True)
    keep_b = 18 if is_lite else 50
    if len(bu) > keep_b:
      top_idx = np.argsort(-bc)[:keep_b]
      keep_poly_islands_and_scale(p, {int(bu[i]) for i in top_idx}, island_scale=1.0, roots=br)
    decimate_solid(p, branch_budget, preserve_uv=True)

  wood_tris = sum(mesh_tri_count(x) for x in trunk_parts + branch_parts)
  leaf_budget = max(200, target_tris - wood_tris - 20)
  max_leaf_cards = leaf_budget // 2

  for p in leaf_parts:
    src_area = mesh_surface_area(p)
    # On tree_small_02, prioritize the 8,607 huge compound frond islands (>= 100 polys, 8 leaflets each!)
    min_p = 100 if aid == 'tree_small_02' else 0
    kept_set, roots = select_spatial_islands(p, max_leaf_cards, seed=seed, prefer_large=True, min_polys=min_p)
    # Area-preserving card scale: sqrt(source_area / kept_area) capped at 3.0
    convert_islands_to_uv_cards(p, kept_set, source_area=src_area * 1.15, scale_cap=3.0, min_scale=1.25, roots=roots)

  kept_parts = [o for o in bpy.data.objects if o.type == 'MESH' and len(o.data.polygons) > 0]
  select_only(kept_parts)
  if len(kept_parts) > 1:
    bpy.ops.object.join()
  merged = bpy.context.view_layer.objects.active
  triangulate_obj(merged)
  return [merged]


def resize_embedded_images(max_dim):
  for img in bpy.data.images:
    w, h = img.size[0], img.size[1]
    if w == 0 or h == 0 or max(w, h) <= max_dim:
      continue
    scale = max_dim / float(max(w, h))
    nw = max(16, int(round(w * scale)))
    nh = max(16, int(round(h * scale)))
    img.scale(nw, nh)
    img.pack()


def verify_glb_json(glb_path, expect_mask, max_primitives=None):
  """Parse GLB JSON chunk directly and verify:
  - ZERO materials have alphaMode == 'BLEND'
  - Foliage GLBs have alphaMode == 'MASK' with effective alphaCutoff == 0.5
  - Primitive count within max_primitives if specified."""
  data = glb_path.read_bytes()
  clen, ctype = struct.unpack_from('<II', data, 12)
  assert ctype == 0x4E4F534A, f'{glb_path.name}: first chunk is not JSON'
  g = json.loads(data[20 : 20 + clen].decode('utf-8'))
  mats = g.get('materials', [])
  for m in mats:
    am = m.get('alphaMode', 'OPAQUE')
    if am == 'BLEND':
      raise RuntimeError(f'{glb_path.name}: forbidden alphaMode=BLEND on material {m.get("name")!r}')
  if expect_mask:
    mask_mats = [m for m in mats if m.get('alphaMode') == 'MASK']
    if not mask_mats:
      raise RuntimeError(f'{glb_path.name}: expected MASK foliage material, got {[m.get("alphaMode","OPAQUE") for m in mats]}')
    for m in mask_mats:
      cutoff = m.get('alphaCutoff', 0.5)
      if abs(cutoff - 0.5) > 1e-4:
        raise RuntimeError(f'{glb_path.name}: material {m.get("name")!r} alphaCutoff={cutoff} != 0.5')
  prims = sum(len(mesh.get('primitives', [])) for mesh in g.get('meshes', []))
  if max_primitives is not None and prims > max_primitives:
    raise RuntimeError(f'{glb_path.name}: primitives={prims} > max {max_primitives}')
  return len(mats), prims, [m.get('alphaMode', 'OPAQUE') for m in mats]


def process_single_lod(entry, is_lite):
  aid = entry['id']
  cat = entry['category']
  is_foliage = bool(entry.get('foliage', False))
  small_prop = bool(entry.get('small_prop', False))
  budget = BUDGETS[cat]['lite' if is_lite else 'high']
  max_tex = (256 if small_prop else 512) if is_lite else 1024
  if is_lite and cat == 'tree':
    max_tex = 256
  webp_q = 72 if is_lite else 80

  out_name = f'ph_{aid}.glb' if is_lite else f'ph_{aid}_hi.glb'
  assert out_name.startswith('ph_'), 'Refusing to write non-ph_ file into public/models/env/'
  out_path = OUT_MODELS_DIR / out_name

  gltf_files = sorted((CACHE_DIR / aid).glob('*.gltf'))
  if not gltf_files:
    raise FileNotFoundError(f'No .gltf found in {CACHE_DIR / aid}')

  bpy.ops.wm.read_factory_settings(use_empty=True)
  bpy.ops.import_scene.gltf(filepath=str(gltf_files[0]))

  meshes = [o for o in bpy.data.objects if o.type == 'MESH']
  if aid in VARIANT_PICK:
    want = VARIANT_PICK[aid]
    chosen = [o for o in meshes if o.name == want]
    if not chosen:
      raise RuntimeError(f'Variant {want!r} not found in {aid}; found {[o.name for o in meshes]}')
    for o in meshes:
      if o not in chosen:
        bpy.data.objects.remove(o, do_unlink=True)
    meshes = chosen

  if aid in ('shrub_02', 'shrub_04'):
    meshes = prepare_single_clump_shrub(aid, meshes)
  else:
    apply_all_transforms(meshes)

  if aid == 'brass_diya_lantern':
    meshes = consolidate_lantern(meshes)

  sanitize_materials(aid, is_foliage=is_foliage)

  if aid == 'wicker_basket_01':
    meshes = process_wicker_basket(meshes[0], budget, is_lite=is_lite)
  elif cat == 'tree':
    meshes = decimate_tree(aid, meshes[0], budget, is_lite=is_lite)
  elif is_foliage:
    if len(meshes) > 1:
      select_only(meshes)
      bpy.ops.object.join()
      meshes = [bpy.context.view_layer.objects.active]
    meshes = [decimate_foliage_shrub(aid, meshes[0], budget, is_lite=is_lite)]
  else:
    cur_total = total_tri_count(meshes)
    if cur_total > budget:
      for o in meshes:
        t = mesh_tri_count(o)
        share = max(24, int(budget * (t / max(cur_total, 1))))
        decimate_solid(o, share, preserve_uv=True)
      cur_total = total_tri_count(meshes)
      if cur_total > budget:
        biggest = max(meshes, key=mesh_tri_count)
        decimate_solid(biggest, max(24, mesh_tri_count(biggest) - (cur_total - budget) - 4), preserve_uv=False)
    else:
      for o in meshes:
        triangulate_obj(o)

  normalize_origin_base_center(meshes)
  final_tris = total_tri_count(meshes)
  if final_tris > budget:
    raise RuntimeError(f'{out_name} exceeded budget: {final_tris} > {budget}')

  resize_embedded_images(max_tex)
  OUT_MODELS_DIR.mkdir(parents=True, exist_ok=True)
  select_only(meshes)
  bpy.ops.export_scene.gltf(
    filepath=str(out_path),
    export_format='GLB',
    use_selection=True,
    export_yup=True,
    export_apply=True,
    export_image_format='WEBP',
    export_image_quality=webp_q,
    export_image_webp_fallback=False,
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=6,
    export_unused_images=False,
  )
  max_prims = 2 if aid == 'brass_diya_lantern' else None
  _, prims, amodes = verify_glb_json(out_path, expect_mask=is_foliage, max_primitives=max_prims)
  size_kb = out_path.stat().st_size / 1024.0
  return final_tris, size_kb, prims, amodes


def process_all_models():
  manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
  models = [a for a in manifest['assets'] if a['type'] == 'model']
  lite_bytes = 0
  for entry in models:
    aid = entry['id']
    check_content_filter(aid)
    lt, lkb, lpr, lam = process_single_lod(entry, is_lite=True)
    ht, hkb, hpr, ham = process_single_lod(entry, is_lite=False)
    lite_bytes += int(round(lkb * 1024))
    print(f'[model] {aid:24s} Lite={lt:5d}t ({lkb:6.1f}KB p={lpr} {lam})  High={ht:5d}t ({hkb:6.1f}KB p={hpr} {ham})')
  print(f'Total Lite ph_*.glb: {lite_bytes / 1048576:.2f} MB across {len(models)} models')


# ---------------------------------------------------------------------------
# Contact Sheet Renderer (--sheet)
# ---------------------------------------------------------------------------

def draw_text(canvas, x, y, text, color=(255, 255, 255), scale=2, bg=None):
  """Draw crisp bitmap text onto an (H, W, 3) uint8 top-down RGB canvas."""
  s = text.upper()
  cw = 6 * scale
  ch = 7 * scale
  tw = len(s) * cw
  if bg is not None:
    y0 = max(0, y - 3)
    y1 = min(canvas.shape[0], y + ch + 3)
    x0 = max(0, x - 4)
    x1 = min(canvas.shape[1], x + tw + 4)
    canvas[y0:y1, x0:x1] = (canvas[y0:y1, x0:x1].astype(np.float32) * 0.25 + np.array(bg, dtype=np.float32) * 0.75).astype(np.uint8)
  for idx, ch_c in enumerate(s):
    glyph = FONT_5X7.get(ch_c, FONT_5X7[' '])
    gx = x + idx * cw
    for row in range(7):
      bits = glyph[row]
      for col in range(5):
        if bits & (1 << (4 - col)):
          py0 = y + row * scale
          px0 = gx + col * scale
          if 0 <= py0 and py0 + scale <= canvas.shape[0] and 0 <= px0 and px0 + scale <= canvas.shape[1]:
            canvas[py0 : py0 + scale, px0 : px0 + scale] = color


def load_image_topdown_u8(path, target_w=None, target_h=None):
  img = bpy.data.images.load(str(path))
  w, h = img.size[0], img.size[1]
  buf = np.empty(h * w * 4, dtype=np.float32)
  img.pixels.foreach_get(buf)
  bpy.data.images.remove(img)
  rgb = np.clip(buf.reshape(h, w, 4)[:, :, :3], 0.0, 1.0)[::-1, :, :]
  if target_w and target_h and (w != target_w or h != target_h):
    ys = np.linspace(0, h - 1, target_h).astype(np.int32)
    xs = np.linspace(0, w - 1, target_w).astype(np.int32)
    rgb = rgb[np.ix_(ys, xs)]
  return (rgb * 255.0 + 0.5).astype(np.uint8)


def save_topdown_u8_png(arr_u8, out_path):
  h, w, _ = arr_u8.shape
  rgba = np.ones((h, w, 4), dtype=np.float32)
  rgba[:, :, :3] = arr_u8[::-1, :, :].astype(np.float32) / 255.0

  sc = bpy.context.scene
  sc.view_settings.view_transform = 'Raw'
  sc.view_settings.look = 'None'
  sc.view_settings.exposure = 0.0
  sc.view_settings.gamma = 1.0
  sc.render.image_settings.file_format = 'PNG'
  sc.render.image_settings.color_mode = 'RGB'

  img = bpy.data.images.new('sheet_out', width=w, height=h, alpha=False, float_buffer=False)
  img.colorspace_settings.name = 'Non-Color'
  img.pixels.foreach_set(rgba.ravel())
  out_path.parent.mkdir(parents=True, exist_ok=True)
  img.save_render(str(out_path), scene=sc)
  bpy.data.images.remove(img)


def render_model_tile(glb_path, tile_w, tile_h, tmp_png):
  """Render a single processed GLB on a grey studio floor and return (tile_h, tile_w, 3) uint8 + tri count."""
  bpy.ops.wm.read_factory_settings(use_empty=True)
  bpy.ops.import_scene.gltf(filepath=str(glb_path))
  meshes = [o for o in bpy.data.objects if o.type == 'MESH']
  tris = total_tri_count(meshes)

  pts = []
  for o in meshes:
    for c in o.bound_box:
      pts.append(o.matrix_world @ Vector(c))
  mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
  mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
  size = mx - mn
  center = (mn + mx) * 0.5
  radius = max(size.length * 0.5, 0.05)

  bpy.ops.mesh.primitive_plane_add(size=max(20.0, radius * 20.0), location=(0, 0, 0))
  floor = bpy.context.active_object
  fmat = bpy.data.materials.new('grey_floor')
  fpbr = next(n for n in fmat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
  fpbr.inputs['Base Color'].default_value = (0.24, 0.24, 0.24, 1.0)
  fpbr.inputs['Roughness'].default_value = 0.90
  floor.data.materials.append(fmat)

  sc = bpy.context.scene
  sc.render.engine = 'BLENDER_EEVEE'
  sc.render.resolution_x = tile_w
  sc.render.resolution_y = tile_h
  sc.render.image_settings.file_format = 'PNG'
  sc.view_settings.view_transform = 'AgX'
  if hasattr(sc.eevee, 'taa_render_samples'):
    sc.eevee.taa_render_samples = 8

  world = bpy.data.worlds.new('sheet_world')
  sc.world = world
  bg = world.node_tree.nodes.get('Background')
  if bg:
    bg.inputs['Color'].default_value = (0.28, 0.30, 0.34, 1.0)
    bg.inputs['Strength'].default_value = 0.85

  sun_d = bpy.data.lights.new('KeySun', 'SUN')
  sun_d.energy = 3.8
  sun_d.color = (1.0, 0.90, 0.76)
  sun = bpy.data.objects.new('KeySun', sun_d)
  sun.rotation_euler = (math.radians(52), math.radians(10), math.radians(-35))
  sc.collection.objects.link(sun)

  fill_d = bpy.data.lights.new('FillSun', 'SUN')
  fill_d.energy = 1.1
  fill_d.color = (0.76, 0.86, 1.0)
  fill = bpy.data.objects.new('FillSun', fill_d)
  fill.rotation_euler = (math.radians(65), math.radians(0), math.radians(140))
  sc.collection.objects.link(fill)

  cam_d = bpy.data.cameras.new('Cam')
  cam_d.lens = 50.0
  cam_d.clip_start = max(0.005, radius * 0.01)
  cam_d.clip_end = max(100.0, radius * 50.0)
  cam = bpy.data.objects.new('Cam', cam_d)
  dist = radius * 3.05
  elev = math.radians(22.0)
  azim = math.radians(-32.0)
  cam.location = center + Vector((
    dist * math.cos(elev) * math.sin(azim),
    -dist * math.cos(elev) * math.cos(azim),
    dist * math.sin(elev),
  ))
  cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
  sc.collection.objects.link(cam)
  sc.camera = cam

  sc.render.filepath = str(tmp_png)
  bpy.ops.render.render(write_still=True)
  tile = load_image_topdown_u8(tmp_png, tile_w, tile_h)
  return tile, tris, size.z


def render_contact_sheet():
  manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
  hdris = [a for a in manifest['assets'] if a['type'] == 'hdri']
  textures = [a for a in manifest['assets'] if a['type'] == 'texture']
  models = [a for a in manifest['assets'] if a['type'] == 'model']

  cols = 4
  rows_m = math.ceil(len(models) / cols)
  tile_w, tile_h = 260, 220
  cell_w = tile_w * 2 + 4
  cell_h = tile_h + 40
  pad = 16
  sheet_w = cols * cell_w + (cols + 1) * pad

  sky_hdr_h = 34
  sky_img_h = 220
  sky_grad_h = 28

  tex_cols = 8
  tex_rows = math.ceil(len(textures) / tex_cols)
  tex_cell_w = (sheet_w - (tex_cols + 1) * pad) // tex_cols
  tex_sw_h = tex_cell_w - 40
  tex_cell_h = tex_sw_h + 36

  header_h = 46
  models_hdr_h = 34
  tex_hdr_h = 34

  sheet_h = (
    header_h
    + sky_hdr_h + sky_img_h + sky_grad_h + pad * 2
    + models_hdr_h + rows_m * (cell_h + pad) + pad
    + tex_hdr_h + tex_rows * (tex_cell_h + pad) + pad
  )

  canvas = np.full((sheet_h, sheet_w, 3), 26, dtype=np.uint8)
  draw_text(canvas, pad, 14, 'M0 POLY HAVEN CONTACT SHEET  -  LITE & HIGH MODELS, TEXTURES & SUNSET HDRI', color=(244, 199, 102), scale=2)

  y = header_h

  # --- 1. Sky Strip ---
  sun_json = json.loads((TEX_V4_DIR / 'sky' / 'sun.json').read_text(encoding='utf-8'))
  hid = hdris[0]['id']
  sky_1k = TEX_V4_DIR / 'sky' / f'{hid}_1k.webp'
  sky_2k = TEX_V4_DIR / 'sky' / f'{hid}_2k.webp'
  draw_text(
    canvas, pad, y + 6,
    f'SKY HDRI: {hid}  |  SUN ELEV {sun_json["sunElevationDeg"]} DEG  SUN {sun_json["sunColor"]}  EXP {sun_json["exposure"]}  1K:{sky_1k.stat().st_size/1024:.1f}KB 2K:{sky_2k.stat().st_size/1024:.1f}KB',
    color=(235, 240, 245), scale=2,
  )
  y += sky_hdr_h
  sky_w = sheet_w - pad * 2
  sky_img = load_image_topdown_u8(sky_1k, sky_w, sky_img_h)
  canvas[y : y + sky_img_h, pad : pad + sky_w] = sky_img
  sx, sy, sz = sun_json['sunDirection']
  u_sun = math.atan2(sz, sx) / (2.0 * math.pi) + 0.5
  v_sun = math.asin(max(-1.0, min(1.0, sy))) / math.pi + 0.5
  px_s = pad + int(round(u_sun * (sky_w - 1)))
  py_s = y + int(round((1.0 - v_sun) * (sky_img_h - 1)))
  for dy in range(-10, 11):
    for dx in range(-10, 11):
      if 64 <= dx * dx + dy * dy <= 100:
        yy, xx = py_s + dy, px_s + dx
        if y <= yy < y + sky_img_h and pad <= xx < pad + sky_w:
          canvas[yy, xx] = (255, 60, 40)
  y += sky_img_h + 4

  grad = sun_json['gradient']
  seg_w = sky_w // len(grad)
  for gi, stop in enumerate(grad):
    hx = stop['color'].lstrip('#')
    rgb = tuple(int(hx[i : i + 2], 16) for i in (0, 2, 4))
    x0 = pad + gi * seg_w
    x1 = pad + sky_w if gi == len(grad) - 1 else x0 + seg_w
    canvas[y : y + sky_grad_h, x0:x1] = rgb
    draw_text(canvas, x0 + 6, y + 7, f'{stop["elevationDeg"]}:{stop["color"]}', color=(15, 15, 15) if sum(rgb) > 380 else (245, 245, 245), scale=2)
  y += sky_grad_h + pad * 2

  # --- 2. Models Grid ---
  draw_text(canvas, pad, y + 6, f'PROCESSED MODELS ({len(models)} ASSETS - LEFT: LITE PH_<ID>.GLB | RIGHT: HIGH PH_<ID>_HI.GLB)', color=(244, 199, 102), scale=2)
  y += models_hdr_h

  tmp_dir = Path(tempfile.mkdtemp(prefix='ph_sheet_'))
  tmp_png = tmp_dir / 'tile.png'

  for idx, entry in enumerate(models):
    aid = entry['id']
    r = idx // cols
    c = idx % cols
    cx = pad + c * (cell_w + pad)
    cy = y + r * (cell_h + pad)
    canvas[cy : cy + cell_h, cx : cx + cell_w] = 42

    lite_p = OUT_MODELS_DIR / f'ph_{aid}.glb'
    high_p = OUT_MODELS_DIR / f'ph_{aid}_hi.glb'
    lite_img, lite_tris, lite_h = render_model_tile(lite_p, tile_w, tile_h, tmp_png)
    high_img, high_tris, _ = render_model_tile(high_p, tile_w, tile_h, tmp_png)

    canvas[cy : cy + tile_h, cx : cx + tile_w] = lite_img
    canvas[cy : cy + tile_h, cx + tile_w + 4 : cx + tile_w * 2 + 4] = high_img
    draw_text(canvas, cx + 6, cy + 6, f'LITE {lite_tris}T {lite_p.stat().st_size/1024:.0f}KB', color=(255, 230, 140), scale=2, bg=(15, 15, 15))
    draw_text(canvas, cx + tile_w + 10, cy + 6, f'HIGH {high_tris}T {high_p.stat().st_size/1024:.0f}KB', color=(150, 230, 255), scale=2, bg=(15, 15, 15))
    draw_text(canvas, cx + 8, cy + tile_h + 12, f'{aid} ({entry["category"]} {lite_h:.2f}M)', color=(245, 245, 245), scale=2)
    print(f'[sheet] rendered {aid} ({idx + 1}/{len(models)})')

  y += rows_m * (cell_h + pad) + pad

  # --- 3. Textures Grid ---
  draw_text(canvas, pad, y + 6, f'PROCESSED TEXTURE SETS ({len(textures)} SETS - 512 WEBP DIFF / NOR / ARM)', color=(244, 199, 102), scale=2)
  y += tex_hdr_h

  for idx, entry in enumerate(textures):
    aid = entry['id']
    r = idx // tex_cols
    c = idx % tex_cols
    cx = pad + c * (tex_cell_w + pad)
    cy = y + r * (tex_cell_h + pad)
    canvas[cy : cy + tex_cell_h, cx : cx + tex_cell_w] = 42

    d_p = TEX_V4_DIR / '512' / f'{aid}_diff.webp'
    n_p = TEX_V4_DIR / '512' / f'{aid}_nor.webp'
    a_p = TEX_V4_DIR / '512' / f'{aid}_arm.webp'
    set_kb = (d_p.stat().st_size + n_p.stat().st_size + a_p.stat().st_size) / 1024.0

    main_w = int(tex_cell_w * 0.68)
    side_w = tex_cell_w - main_w - 2
    half_h = tex_sw_h // 2

    canvas[cy : cy + tex_sw_h, cx : cx + main_w] = load_image_topdown_u8(d_p, main_w, tex_sw_h)
    canvas[cy : cy + half_h, cx + main_w + 2 : cx + main_w + 2 + side_w] = load_image_topdown_u8(n_p, side_w, half_h)
    canvas[cy + half_h : cy + tex_sw_h, cx + main_w + 2 : cx + main_w + 2 + side_w] = load_image_topdown_u8(a_p, side_w, tex_sw_h - half_h)

    draw_text(canvas, cx + 4, cy + tex_sw_h + 6, aid[:20], color=(245, 245, 245), scale=1)
    draw_text(canvas, cx + 4, cy + tex_sw_h + 20, f'512: {set_kb:.0f}KB', color=(180, 220, 190), scale=1)

  bpy.ops.wm.read_factory_settings(use_empty=True)
  save_topdown_u8_png(canvas, SHEET_PATH)
  tmp_png.unlink(missing_ok=True)
  try:
    tmp_dir.rmdir()
  except OSError:
    pass
  print(f'Contact sheet written to {SHEET_PATH.relative_to(ROOT)} ({sheet_w}x{sheet_h})')


def parse_args():
  argv = sys.argv
  if '--' in argv:
    argv = argv[argv.index('--') + 1 :]
  else:
    argv = []
  ap = argparse.ArgumentParser()
  ap.add_argument('--sheet', action='store_true', help='Render M0 contact sheet PNG')
  return ap.parse_args(argv)


def main():
  args = parse_args()
  if args.sheet:
    render_contact_sheet()
  else:
    process_all_models()


if __name__ == '__main__':
  main()
