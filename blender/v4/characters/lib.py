"""Shared Blender v4 character utilities: PBR/export materials, metric UVs, BVH AO, Draco-6 GLB export."""
import json
import math
import os
import struct
import tempfile
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = '/var/www/html/old/3d-quranic/'
HERE = ROOT + 'blender/v4/characters/'
PREV = ROOT + 'blender/v4/previews/'
TEX_V4 = ROOT + 'public/textures/v4/'
MODELS = ROOT + 'public/models/'

# Exact v4 fabric contract matching src/game/shaders/characterMaterial.js
# (polyhaven_id, tile_m, diff_avg_lin, roughness, normal_strength, detail_gain)
FABRIC_META = {
    'ph_cotton':  ('cotton_jersey',  0.35, (0.5333, 0.4052, 0.3360), 0.85, 4.20, 4.60),
    'ph_linen':   ('rough_linen',    0.45, (0.2830, 0.4104, 0.6144), 0.88, 2.35, 1.60),
    'ph_wool':    ('knitted_fleece', 0.30, (0.0922, 0.0731, 0.0507), 0.90, 2.45, 1.45),
    'ph_hessian': ('hessian_230',    0.40, (0.2757, 0.1986, 0.1084), 0.88, 1.15, 0.95),
    'ph_leather': ('brown_leather',  0.50, (0.0832, 0.0269, 0.0053), 0.50, 1.35, 1.30),
}

ALLOWED_MAT_BASES = set(FABRIC_META.keys()) | {'skin', 'hair', 'eye', 'metal'}


def hex_rgb(h):
    """Convert '#RRGGBB' hex string to (r, g, b) floats in [0, 1] sRGB."""
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def lin(c):
    """Convert sRGB (hex string or 3-tuple) to linear RGB."""
    if isinstance(c, str):
        c = hex_rgb(c)
    return tuple(
        x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
        for x in c[:3]
    )


def scale_hex(h, k):
    """Scale an sRGB hex color's linear brightness by k and return linear RGB."""
    r, g, b = lin(h)
    return (min(1.0, r * k), min(1.0, g * k), min(1.0, b * k))


def reset_scene():
    """Clear all objects, collections, actions, meshes, armatures, materials, images."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for act in list(bpy.data.actions):
        bpy.data.actions.remove(act)
    for bank in (
        bpy.data.meshes,
        bpy.data.armatures,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.lights,
        bpy.data.cameras,
    ):
        for item in list(bank):
            if item.users == 0:
                bank.remove(item)
    sc = bpy.context.scene
    sc.render.fps = 24
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0


def fresh_collection(name):
    """Create or clear a character collection in the active scene."""
    col = bpy.data.collections.get(name)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
    else:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


# ------------------------------------------------------------------ images
def pack_image(name, rgb, alpha=None):
    """Create an in-memory packed PNG image (sRGB float array HxWx3, row 0 = bottom)."""
    h, w = rgb.shape[:2]
    old = bpy.data.images.get(name)
    if old:
        bpy.data.images.remove(old)
    img = bpy.data.images.new(name, w, h, alpha=alpha is not None)
    img.colorspace_settings.name = 'sRGB'
    a = np.ones((h, w, 1), dtype=np.float32) if alpha is None else alpha[..., None].astype(np.float32)
    rgba = np.concatenate([np.clip(rgb, 0.0, 1.0).astype(np.float32), a], axis=-1)
    img.pixels.foreach_set(rgba.ravel())
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tf:
        tmp_path = tf.name
    try:
        img.filepath_raw = tmp_path
        img.file_format = 'PNG'
        img.save()
        img.filepath = tmp_path
        img.source = 'FILE'
        img.reload()
        img.pack()
        img.filepath = f'//{name}.png'
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return img


# ------------------------------------------------------------------ dual-mode PBR materials
def _set_input(node, names, val):
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = val
            return


def _wire_shemagh_preview(nt, nd, uv_out, vc_out):
    """Build exact 2.8 cm red-and-white Arabian shemagh preview nodes on ph_linen when UV.x > 50."""
    sep_uv = nd('ShaderNodeSeparateXYZ', -1120, 260)
    nt.links.new(uv_out, sep_uv.inputs['Vector'])

    is_sh = nd('ShaderNodeMath', -940, 360)
    is_sh.operation = 'GREATER_THAN'
    is_sh.inputs[1].default_value = 50.0
    nt.links.new(sep_uv.outputs['X'], is_sh.inputs[0])

    # Recover real-metre UV (subtract 100.0 on shemagh vertices so fabric weave tiles normally too)
    sub_u = nd('ShaderNodeMath', -940, 200)
    sub_u.operation = 'SUBTRACT'
    sub_u.inputs[1].default_value = 100.0
    nt.links.new(sep_uv.outputs['X'], sub_u.inputs[0])

    mx_u = nd('ShaderNodeMix', -760, 240)
    mx_u.data_type = 'FLOAT'
    nt.links.new(is_sh.outputs['Value'], mx_u.inputs['Factor'])
    nt.links.new(sep_uv.outputs['X'], mx_u.inputs['A'])
    nt.links.new(sub_u.outputs['Value'], mx_u.inputs['B'])

    clean_uv = nd('ShaderNodeCombineXYZ', -590, 240)
    nt.links.new(mx_u.outputs['Result'], clean_uv.inputs['X'])
    nt.links.new(sep_uv.outputs['Y'], clean_uv.inputs['Y'])

    # Cell coords sg = mUv / 0.028 (2.8 cm squares)
    def mmath(op, x, y, a=None, b=None):
        n = nd('ShaderNodeMath', x, y)
        n.operation = op
        if a is not None:
            if isinstance(a, (int, float)):
                n.inputs[0].default_value = a
            else:
                nt.links.new(a, n.inputs[0])
        if b is not None:
            if isinstance(b, (int, float)):
                n.inputs[1].default_value = b
            else:
                nt.links.new(b, n.inputs[1])
        return n.outputs['Value']

    gx = mmath('DIVIDE', -420, 620, mx_u.outputs['Result'], 0.026)
    gy = mmath('DIVIDE', -420, 480, sep_uv.outputs['Y'], 0.026)
    cx = mmath('FLOOR', -260, 680, gx)
    cy = mmath('FLOOR', -260, 560, gy)
    fx = mmath('FRACT', -260, 440, gx)
    fy = mmath('FRACT', -260, 320, gy)

    par = mmath('MODULO', -90, 640, mmath('ADD', -170, 640, cx, cy), 2.0)
    is_even = mmath('LESS_THAN', 50, 640, par, 0.5)

    # Classic Arabian shemagh square houndstooth/check weave (like v3):
    # crisp warp/weft double bands + alternating solid woven red check/diamond squares!
    def band_1d(f_out, y_off):
        d0 = mmath('ABSOLUTE', -90, y_off, mmath('SUBTRACT', -170, y_off, f_out, 0.5))
        b0 = mmath('LESS_THAN', 50, y_off, d0, 0.105)
        d1 = mmath('ABSOLUTE', -90, y_off - 70, mmath('SUBTRACT', -170, y_off - 70, f_out, 0.25))
        b1 = mmath('LESS_THAN', 50, y_off - 70, d1, 0.044)
        d2 = mmath('ABSOLUTE', -90, y_off - 140, mmath('SUBTRACT', -170, y_off - 140, f_out, 0.75))
        b2 = mmath('LESS_THAN', 50, y_off - 140, d2, 0.044)
        return mmath('MAXIMUM', 180, y_off - 40, b0, mmath('MAXIMUM', 120, y_off - 90, b1, b2))

    bu = band_1d(fx, 440)
    bv = band_1d(fy, 200)
    lines = mmath('MAXIMUM', 290, 320, bu, bv)

    # Alternating woven square houndstooth check (square box + notched diamond, NEVER polka-dots!)
    dx_c = mmath('ABSOLUTE', -90, 520, mmath('SUBTRACT', -170, 520, fx, 0.5))
    dy_c = mmath('ABSOLUTE', -90, 480, mmath('SUBTRACT', -170, 480, fy, 0.5))
    cheb = mmath('MAXIMUM', 160, 500, dx_c, dy_c)
    sq_check = mmath('LESS_THAN', 270, 500, cheb, 0.34)
    d_manh = mmath('ADD', 160, 580, dx_c, dy_c)
    diam = mmath('LESS_THAN', 270, 580, d_manh, 0.44)
    even_block = mmath('MULTIPLY', 380, 520, is_even, mmath('MAXIMUM', 320, 520, sq_check, diam))
    pat_val = mmath('MAXIMUM', 490, 520, lines, even_block)

    # Detect solid red border faces via vertex color (r - g > 0.20) so border stays solid #B23029
    sep_vc = nd('ShaderNodeSeparateColor', -90, 820)
    nt.links.new(vc_out, sep_vc.inputs['Color'])
    rg_diff = mmath('SUBTRACT', 90, 820, sep_vc.outputs['Red'], sep_vc.outputs['Green'])
    not_border = mmath('LESS_THAN', 230, 820, rg_diff, 0.20)
    apply_pat = mmath('MULTIPLY', 620, 620, mmath('MULTIPLY', 560, 700, is_sh.outputs['Value'], not_border), pat_val)

    # Preserve exact baked AO from vc.r / 0.929 onto strong red #B23029 (lin 0.4452, 0.0296, 0.0222)
    s_ao = mmath('DIVIDE', 230, 920, sep_vc.outputs['Red'], 0.929)
    red_rgb = nd('ShaderNodeCombineColor', 420, 920)
    nt.links.new(mmath('MULTIPLY', 320, 980, s_ao, 0.4452), red_rgb.inputs['Red'])
    nt.links.new(mmath('MULTIPLY', 320, 920, s_ao, 0.0296), red_rgb.inputs['Green'])
    nt.links.new(mmath('MULTIPLY', 320, 860, s_ao, 0.0222), red_rgb.inputs['Blue'])

    mx_col = nd('ShaderNodeMix', 760, 520)
    mx_col.data_type = 'RGBA'
    nt.links.new(apply_pat, mx_col.inputs['Factor'])
    nt.links.new(vc_out, mx_col.inputs[6])
    nt.links.new(red_rgb.outputs['Color'], mx_col.inputs[7])
    return clean_uv.outputs['Vector'], mx_col.outputs[2]


def fabric_mat(name, tex_size=1024):
    """Return shared v4 Poly Haven fabric material (geometry-only in 'export', live PH PBR in 'preview')."""
    if name not in FABRIC_META:
        raise ValueError(f'Unknown fabric layer: {name}')
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat

    tex_id, tile_m, avg_lin, rough, nor_s, det_gain = FABRIC_META[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    nt = mat.node_tree
    nt.nodes.clear()

    def nd(bl_type, x, y, nname=None):
        n = nt.nodes.new(bl_type)
        n.location = (x, y)
        if nname:
            n.name = nname
        return n

    out = nd('ShaderNodeOutputMaterial', 1240, 0, 'out')

    # --- Export branch: pure vertex colour, zero external images packed into GLB
    vc = nd('ShaderNodeVertexColor', -320, 260, 'vc')
    vc.layer_name = 'Color'
    pr_exp = nd('ShaderNodeBsdfPrincipled', 820, 320, 'export')
    pr_exp.inputs['Roughness'].default_value = rough
    pr_exp.inputs['Metallic'].default_value = 0.0
    nt.links.new(vc.outputs['Color'], pr_exp.inputs['Base Color'])

    # --- Preview branch: matches characterMaterial.js (zero-mean luminance weave detail @ 0.55 + normal map)
    pr_prev = nd('ShaderNodeBsdfPrincipled', 960, -180, 'preview')
    pr_prev.inputs['Roughness'].default_value = rough
    pr_prev.inputs['Metallic'].default_value = 0.0
    _set_input(pr_prev, ('Specular IOR Level',), 0.30 if name == 'ph_leather' else 0.04)

    uv = nd('ShaderNodeTexCoord', -1280, -180)
    if name == 'ph_linen':
        base_uv, base_col = _wire_shemagh_preview(nt, nd, uv.outputs['UV'], vc.outputs['Color'])
    else:
        base_uv, base_col = uv.outputs['UV'], vc.outputs['Color']

    mp = nd('ShaderNodeMapping', -560, -180)
    inv = 1.0 / tile_m
    mp.inputs['Scale'].default_value = (inv, inv, 1.0)
    nt.links.new(base_uv, mp.inputs['Vector'])

    tdir = Path(TEX_V4) / str(tex_size)
    diff_img = bpy.data.images.load(str(tdir / f'{tex_id}_diff.webp'), check_existing=True)
    diff_img.colorspace_settings.name = 'sRGB'
    nor_img = bpy.data.images.load(str(tdir / f'{tex_id}_nor.webp'), check_existing=True)
    nor_img.colorspace_settings.name = 'Non-Color'

    n_diff = nd('ShaderNodeTexImage', -340, -60, 'prev_diff')
    n_diff.image = diff_img
    nt.links.new(mp.outputs['Vector'], n_diff.inputs['Vector'])

    n_nor = nd('ShaderNodeTexImage', -340, -340, 'prev_nor')
    n_nor.image = nor_img
    nt.links.new(mp.outputs['Vector'], n_nor.inputs['Vector'])

    # Zero-mean luminance detail with per-layer contrast gain (exact mean 1.0, visible cotton/linen/wool weave)
    lum = nd('ShaderNodeRGBToBW', -100, -20)
    nt.links.new(n_diff.outputs['Color'], lum.inputs['Color'])
    avg_lum = max(0.01, avg_lin[0] * 0.2126 + avg_lin[1] * 0.7152 + avg_lin[2] * 0.0722)
    div_l = nd('ShaderNodeMath', 50, -20)
    div_l.operation = 'DIVIDE'
    div_l.inputs[1].default_value = avg_lum
    nt.links.new(lum.outputs['Val'], div_l.inputs[0])

    sub_1 = nd('ShaderNodeMath', 180, -20)
    sub_1.operation = 'SUBTRACT'
    sub_1.inputs[1].default_value = 1.0
    nt.links.new(div_l.outputs['Value'], sub_1.inputs[0])

    mul_g = nd('ShaderNodeMath', 310, -20)
    mul_g.operation = 'MULTIPLY'
    mul_g.inputs[1].default_value = det_gain
    nt.links.new(sub_1.outputs['Value'], mul_g.inputs[0])

    clmp = nd('ShaderNodeClamp', 440, -20)
    clmp.inputs['Min'].default_value = -0.34
    clmp.inputs['Max'].default_value = 0.34
    nt.links.new(mul_g.outputs['Value'], clmp.inputs['Value'])

    add_1 = nd('ShaderNodeMath', 560, -20)
    add_1.operation = 'ADD'
    add_1.inputs[1].default_value = 1.0
    nt.links.new(clmp.outputs['Result'], add_1.inputs[0])

    mix_det = nd('ShaderNodeMix', 690, -40)
    mix_det.data_type = 'FLOAT'
    mix_det.inputs['Factor'].default_value = 0.55
    mix_det.inputs['A'].default_value = 1.0
    nt.links.new(add_1.outputs['Value'], mix_det.inputs['B'])

    comb = nd('ShaderNodeCombineColor', 690, 120)
    nt.links.new(mix_det.outputs['Result'], comb.inputs['Red'])
    nt.links.new(mix_det.outputs['Result'], comb.inputs['Green'])
    nt.links.new(mix_det.outputs['Result'], comb.inputs['Blue'])

    mul_vc = nd('ShaderNodeMix', 830, 60)
    mul_vc.data_type = 'RGBA'
    mul_vc.blend_type = 'MULTIPLY'
    mul_vc.inputs['Factor'].default_value = 1.0
    nt.links.new(base_col, mul_vc.inputs[6])
    nt.links.new(comb.outputs['Color'], mul_vc.inputs[7])
    nt.links.new(mul_vc.outputs[2], pr_prev.inputs['Base Color'])

    nmap = nd('ShaderNodeNormalMap', 440, -340)
    nmap.inputs['Strength'].default_value = nor_s * 0.85
    nt.links.new(n_nor.outputs['Color'], nmap.inputs['Color'])
    nt.links.new(nmap.outputs['Normal'], pr_prev.inputs['Normal'])

    set_mat_mode(mat, 'preview')
    return mat


def plain_mat(name, roughness=0.60, metalness=0.0, sss=0.0, spec=0.35):
    """Return shared vertex-color PBR material (`skin`, `hair`, `metal`)."""
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new('ShaderNodeOutputMaterial')
    out.name = 'out'
    out.location = (700, 0)

    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = 'Color'
    vc.location = (-200, 0)

    pr_exp = nt.nodes.new('ShaderNodeBsdfPrincipled')
    pr_exp.name = 'export'
    pr_exp.location = (260, 180)
    pr_exp.inputs['Roughness'].default_value = roughness
    pr_exp.inputs['Metallic'].default_value = metalness
    nt.links.new(vc.outputs['Color'], pr_exp.inputs['Base Color'])

    pr_prev = nt.nodes.new('ShaderNodeBsdfPrincipled')
    pr_prev.name = 'preview'
    pr_prev.location = (260, -180)
    pr_prev.inputs['Roughness'].default_value = roughness
    pr_prev.inputs['Metallic'].default_value = metalness
    _set_input(pr_prev, ('Specular IOR Level',), spec)
    if sss > 0.0:
        _set_input(pr_prev, ('Subsurface Weight',), sss)
        _set_input(pr_prev, ('Subsurface Scale',), 0.014)
        _set_input(pr_prev, ('Subsurface Radius',), (1.0, 0.42, 0.25))
    nt.links.new(vc.outputs['Color'], pr_prev.inputs['Base Color'])

    set_mat_mode(mat, 'preview')
    return mat


def face_mat(key, image):
    """Return per-character `face_<key>` material with the embedded 512 face/eye atlas."""
    name = f'face_{key}'
    old = bpy.data.materials.get(name)
    if old is not None:
        bpy.data.materials.remove(old)

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new('ShaderNodeOutputMaterial')
    out.name = 'out'
    out.location = (820, 0)

    tx = nt.nodes.new('ShaderNodeTexImage')
    tx.name = 'face_tex'
    tx.image = image
    tx.interpolation = 'Linear'
    tx.location = (-280, 120)

    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = 'Color'
    vc.location = (-280, -140)

    mul = nt.nodes.new('ShaderNodeMix')
    mul.data_type = 'RGBA'
    mul.blend_type = 'MULTIPLY'
    mul.inputs['Factor'].default_value = 1.0
    mul.location = (20, 40)
    nt.links.new(tx.outputs['Color'], mul.inputs[6])
    nt.links.new(vc.outputs['Color'], mul.inputs[7])

    pr_exp = nt.nodes.new('ShaderNodeBsdfPrincipled')
    pr_exp.name = 'export'
    pr_exp.location = (380, 180)
    pr_exp.inputs['Roughness'].default_value = 0.55
    pr_exp.inputs['Metallic'].default_value = 0.0
    nt.links.new(mul.outputs[2], pr_exp.inputs['Base Color'])

    pr_prev = nt.nodes.new('ShaderNodeBsdfPrincipled')
    pr_prev.name = 'preview'
    pr_prev.location = (380, -180)
    pr_prev.inputs['Roughness'].default_value = 0.55
    pr_prev.inputs['Metallic'].default_value = 0.0
    _set_input(pr_prev, ('Specular IOR Level',), 0.24)
    _set_input(pr_prev, ('Subsurface Weight',), 0.22)
    _set_input(pr_prev, ('Subsurface Scale',), 0.014)
    _set_input(pr_prev, ('Subsurface Radius',), (1.0, 0.42, 0.25))
    nt.links.new(mul.outputs[2], pr_prev.inputs['Base Color'])

    set_mat_mode(mat, 'preview')
    return mat


def eye_mat(key, image):
    """Return glossy cornea material sharing the character's 512 face/eye atlas (renamed 'eye' on export)."""
    tmp_name = f'eye__{key}'
    old = bpy.data.materials.get(tmp_name)
    if old is not None:
        bpy.data.materials.remove(old)

    mat = bpy.data.materials.new(tmp_name)
    mat['export_name'] = 'eye'
    mat.use_nodes = True
    mat.use_backface_culling = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new('ShaderNodeOutputMaterial')
    out.name = 'out'
    out.location = (700, 0)

    tx = nt.nodes.new('ShaderNodeTexImage')
    tx.name = 'eye_tex'
    tx.image = image
    tx.interpolation = 'Linear'
    tx.location = (-220, 0)

    pr_exp = nt.nodes.new('ShaderNodeBsdfPrincipled')
    pr_exp.name = 'export'
    pr_exp.location = (260, 180)
    pr_exp.inputs['Roughness'].default_value = 0.12
    pr_exp.inputs['Metallic'].default_value = 0.0
    nt.links.new(tx.outputs['Color'], pr_exp.inputs['Base Color'])

    pr_prev = nt.nodes.new('ShaderNodeBsdfPrincipled')
    pr_prev.name = 'preview'
    pr_prev.location = (260, -180)
    pr_prev.inputs['Roughness'].default_value = 0.10
    pr_prev.inputs['Metallic'].default_value = 0.0
    _set_input(pr_prev, ('Specular IOR Level',), 0.85)
    _set_input(pr_prev, ('Coat Weight',), 0.65)
    _set_input(pr_prev, ('Coat Roughness',), 0.04)
    nt.links.new(tx.outputs['Color'], pr_prev.inputs['Base Color'])

    set_mat_mode(mat, 'preview')
    return mat


def set_mat_mode(mat, mode):
    """Switch material output between 'preview' (live PH textures + SSS) and 'export' (geometry-only GLB)."""
    if not mat.use_nodes:
        return
    nt = mat.node_tree
    out = nt.nodes.get('out')
    src = nt.nodes.get('preview' if mode == 'preview' else 'export')
    if out and src:
        nt.links.new(src.outputs[0], out.inputs['Surface'])


def set_all_mat_mode(mode):
    """Switch every dual-branch material in the scene to 'preview' or 'export'."""
    for mat in bpy.data.materials:
        if mat.use_nodes and mat.node_tree.nodes.get('export'):
            set_mat_mode(mat, mode)


# ------------------------------------------------------------------ mesh, metric UV & vertex-color helpers
def new_obj(name, mesh, col):
    """Create a mesh object linked to col, replacing any existing object of same name."""
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    return obj


def ensure_uv_layer(obj):
    """Ensure mesh has a primary UV layer named 'UVMap'."""
    me = obj.data
    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')
    else:
        me.uv_layers[0].name = 'UVMap'


def ensure_color_layer(obj, default_rgba=(1.0, 1.0, 1.0, 1.0)):
    """Ensure mesh has an active linear FLOAT_COLOR attribute named 'Color'."""
    me = obj.data
    ca = me.color_attributes.get('Color')
    if ca is None:
        ca = me.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
        for i in range(len(ca.data)):
            ca.data[i].color = default_rgba
    idx = me.color_attributes.find('Color')
    if idx >= 0:
        me.color_attributes.active_color_index = idx
        me.color_attributes.render_color_index = idx
    return ca


def paint_bm(bm, color, jitter=0.0):
    """Paint all loops in bmesh with linear RGB derived from sRGB hex or linear tuple."""
    col_layer = bm.loops.layers.float_color.get('Color') or bm.loops.layers.float_color.new('Color')
    rgb = lin(color) if isinstance(color, str) else tuple(color[:3])
    rgba = (rgb[0], rgb[1], rgb[2], 1.0)
    for f in bm.faces:
        for lp in f.loops:
            lp[col_layer] = rgba
    return col_layer


def _box_metric_uv(co, fn):
    """Real-metre box UV projection (V up on vertical surfaces)."""
    ax, ay, az = abs(fn.x), abs(fn.y), abs(fn.z)
    if az > 0.72:
        return (co.x if fn.z >= 0 else -co.x, co.y)
    if ay >= ax:
        return (co.x if fn.y < 0 else -co.x, co.z)
    return (co.y if fn.x > 0 else -co.y, co.z)


def apply_metric_box_uv(bm, uv_layer):
    """Assign real-metre box UVs to all faces in bm."""
    bm.normal_update()
    for f in bm.faces:
        fn = f.normal
        for lp in f.loops:
            lp[uv_layer].uv = _box_metric_uv(lp.vert.co, fn)


def apply_metric_cylindrical_uv(obj, center=(0.0, 0.0)):
    """Assign real-metre cylindrical UVs around Z axis (u = arc length in metres, v = z in metres)."""
    me = obj.data
    ensure_uv_layer(obj)
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    cx, cy = center
    for f in bm.faces:
        angs = [math.atan2(lp.vert.co.y - cy, lp.vert.co.x - cx) for lp in f.loops]
        if max(angs) - min(angs) > math.pi:
            angs = [a + math.tau if a < 0 else a for a in angs]
        mean_r = sum(math.hypot(lp.vert.co.x - cx, lp.vert.co.y - cy) for lp in f.loops) / max(1, len(f.loops))
        r_eff = max(0.06, mean_r)
        for lp, a in zip(f.loops, angs):
            lp[uv].uv = (a * r_eff, lp.vert.co.z)
    bm.to_mesh(me)
    bm.free()


def bm_to_obj(bm, name, col, mat=None, color=None, smooth=True, ensure_uv=True, uv_mode='box'):
    """Convert bmesh to a Blender object with UVMap and linear FLOAT_COLOR 'Color'."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if ensure_uv and not bm.loops.layers.uv:
        uv_layer = bm.loops.layers.uv.new('UVMap')
        if uv_mode == 'zero':
            for f in bm.faces:
                for lp in f.loops:
                    lp[uv_layer].uv = (0.0, 0.0)
        else:
            apply_metric_box_uv(bm, uv_layer)

    if color is not None and not bm.loops.layers.float_color.get('Color'):
        paint_bm(bm, color)
    elif not bm.loops.layers.float_color.get('Color'):
        paint_bm(bm, (1.0, 1.0, 1.0))

    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if ensure_uv and me.uv_layers:
        me.uv_layers[0].name = 'UVMap'
    ensure_color_layer(new_obj_tmp := new_obj(name, me, col))
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    if mat is not None:
        me.materials.append(mat)
    if uv_mode == 'cyl':
        apply_metric_cylindrical_uv(new_obj_tmp)
    return new_obj_tmp


def shade_smooth(obj):
    for p in obj.data.polygons:
        p.use_smooth = True


def loft_rings(bm, rings, closed_u=True, cap_start=False, cap_end=False, metric_uv=False, uv_scale=(1.0, 1.0)):
    """Connect vertex loops (each length N) into a smooth quad skin, optionally writing real-metre arc UVs."""
    n = len(rings[0])
    m = len(rings)
    uv_layer = None
    u_coords = None
    v_coords = None

    if metric_uv:
        uv_layer = bm.loops.layers.uv.get('UVMap') or bm.loops.layers.uv.new('UVMap')
        # Compute per-ring cumulative arc-length U (in metres) and ring-to-ring cumulative V (in metres)
        ring_arc = []
        for r in rings:
            acc = [0.0]
            count = n if closed_u else n - 1
            for k in range(count):
                kn = (k + 1) % n
                acc.append(acc[-1] + (r[kn].co - r[k].co).length)
            ring_arc.append(acc)
        # Use average circumference progression normalized gently so seam stays vertical & unskewed
        v_coords = [0.0]
        for i in range(m - 1):
            step = sum((rings[i + 1][k].co - rings[i][k].co).length for k in range(n)) / n
            v_coords.append(v_coords[-1] + step)
        u_coords = ring_arc

    su, sv = uv_scale
    for ri, (r0, r1) in enumerate(zip(rings, rings[1:])):
        count = n if closed_u else n - 1
        for k in range(count):
            kn = (k + 1) % n
            f = bm.faces.new((r0[k], r0[kn], r1[kn], r1[k]))
            if uv_layer is not None:
                u00, u01 = u_coords[ri][k] * su, u_coords[ri][k + 1] * su
                u10, u11 = u_coords[ri + 1][k] * su, u_coords[ri + 1][k + 1] * su
                v0, v1 = v_coords[ri] * sv, v_coords[ri + 1] * sv
                lps = f.loops
                lps[0][uv_layer].uv = (u00, v0)
                lps[1][uv_layer].uv = (u01, v0)
                lps[2][uv_layer].uv = (u11, v1)
                lps[3][uv_layer].uv = (u10, v1)

    if cap_start and closed_u:
        c = sum((v.co for v in rings[0]), Vector()) / n
        cv = bm.verts.new(c)
        for k in range(n):
            kn = (k + 1) % n
            f = bm.faces.new((rings[0][kn], rings[0][k], cv))
            if uv_layer is not None:
                for lp in f.loops:
                    lp[uv_layer].uv = (lp.vert.co.x * su, lp.vert.co.y * sv)
    if cap_end and closed_u:
        c = sum((v.co for v in rings[-1]), Vector()) / n
        cv = bm.verts.new(c)
        for k in range(n):
            kn = (k + 1) % n
            f = bm.faces.new((rings[-1][k], rings[-1][kn], cv))
            if uv_layer is not None:
                for lp in f.loops:
                    lp[uv_layer].uv = (lp.vert.co.x * su, lp.vert.co.y * sv)


def add_tube(bm, pts, radius, segs=10, flat=1.0, closed_caps=True, ref_up=None, metric_uv=False):
    """Add a smooth swept tube along 3D polyline pts using parallel transport framing."""
    n_pts = len(pts)
    if n_pts < 2:
        return []
    up = Vector(ref_up).normalized() if ref_up is not None else Vector((0.0, 0.0, 1.0))
    tangents = []
    for i in range(n_pts):
        t = (pts[min(i + 1, n_pts - 1)] - pts[max(i - 1, 0)])
        if t.length < 1e-6:
            t = Vector((0.0, 0.0, 1.0))
        tangents.append(t.normalized())

    t0 = tangents[0]
    ax = t0.cross(up)
    if ax.length < 1e-4:
        ax = t0.orthogonal()
    ax.normalize()
    bx = t0.cross(ax).normalized()

    rings = []
    for i, p in enumerate(pts):
        ti = tangents[i]
        if i > 0:
            q = tangents[i - 1].rotation_difference(ti)
            ax = (q @ ax)
            ax = (ax - ti * ax.dot(ti)).normalized()
            bx = ti.cross(ax).normalized()
        u = i / max(1, n_pts - 1)
        r = radius(u) if callable(radius) else radius
        if isinstance(r, tuple):
            rx, ry = r
        else:
            rx, ry = r, r * flat
        ring = []
        for k in range(segs):
            ang = k / segs * math.tau
            ring.append(bm.verts.new(p + ax * (math.cos(ang) * rx) + bx * (math.sin(ang) * ry)))
        rings.append(ring)

    loft_rings(bm, rings, closed_u=True, cap_start=closed_caps, cap_end=closed_caps, metric_uv=metric_uv)
    return rings


def add_ring_torus(
    bm, center, rx, ry, z, tube_rx, tube_rz=None, tilt=0.0, phase=0.0,
    segs=28, tsegs=8, bulge=0.0, metric_uv=False,
):
    """Add a closed organic wrapped torus ring (used for turban folds and agal) with optional metric UVs."""
    tube_rz = tube_rx if tube_rz is None else tube_rz
    c = Vector(center)
    pts = [
        Vector((
            c.x + rx * math.cos(a),
            c.y + ry * math.sin(a),
            z + tilt * math.sin(a + phase),
        ))
        for a in (k / segs * math.tau for k in range(segs))
    ]
    rings = []
    for i, p in enumerate(pts):
        d = (pts[(i + 1) % segs] - pts[i - 1]).normalized()
        out = Vector((p.x - c.x, p.y - c.y, 0.0)).normalized()
        up = d.cross(out).normalized()
        out = up.cross(d).normalized()
        mul = 1.0 + bulge * math.sin(3.0 * i / segs * math.tau + phase)
        ring = []
        for k in range(tsegs):
            a = k / tsegs * math.tau
            ring.append(bm.verts.new(p + (out * math.cos(a) * tube_rx + up * math.sin(a) * tube_rz) * mul))
        rings.append(ring)

    uv_layer = (bm.loops.layers.uv.get('UVMap') or bm.loops.layers.uv.new('UVMap')) if metric_uv else None
    circ_maj = math.tau * 0.5 * (rx + ry)
    circ_min = math.tau * 0.5 * (tube_rx + tube_rz)

    for i in range(segs):
        r0, r1 = rings[i], rings[(i + 1) % segs]
        u0 = (i / segs) * circ_maj
        u1 = ((i + 1) / segs) * circ_maj
        for k in range(tsegs):
            kn = (k + 1) % tsegs
            f = bm.faces.new((r0[k], r0[kn], r1[kn], r1[k]))
            if uv_layer is not None:
                v0 = (k / tsegs) * circ_min
                v1 = ((k + 1) / tsegs) * circ_min
                f.loops[0][uv_layer].uv = (u0, v0)
                f.loops[1][uv_layer].uv = (u0, v1)
                f.loops[2][uv_layer].uv = (u1, v1)
                f.loops[3][uv_layer].uv = (u1, v0)
    return rings


def smoothstep(e0, e1, x):
    """Smooth Hermite interpolation in [0, 1]."""
    if abs(e1 - e0) < 1e-8:
        return 1.0 if x >= e1 else 0.0
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3.0 - 2.0 * t)


# ------------------------------------------------------------------ join & BVH AO baking
def join_objects(objs, name, col=None):
    """Join a list of skinned mesh objects into one object named `name` preserving UVMap & Color."""
    for obj in objs:
        ensure_uv_layer(obj)
        ensure_color_layer(obj)
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for obj in objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    with bpy.context.temp_override(
        active_object=objs[0],
        object=objs[0],
        selected_objects=objs,
        selected_editable_objects=objs,
    ):
        bpy.ops.object.join()
    res = objs[0]
    res.name = name
    res.data.name = name
    ensure_color_layer(res)
    if col and res.name not in col.objects:
        col.objects.link(res)
    return res


def _hemi_dirs(n=14):
    dirs = []
    phi_step = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(n):
        u = (i + 0.5) / n
        r = math.sqrt(u)
        theta = i * phi_step
        dirs.append(Vector((r * math.cos(theta), r * math.sin(theta), math.sqrt(max(0.06, 1.0 - u)))).normalized())
    return dirs


HEMI_14 = _hemi_dirs(14)


def bake_character_ao(mesh_obj, lm):
    """Bake soft raytraced crevice/fold AO and subtle vertical light-wrap into linear COLOR_0."""
    me = mesh_obj.data
    col_attr = me.color_attributes.get('Color')
    if col_attr is None:
        return

    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    bvh = BVHTree.FromBMesh(bm)

    h = lm['height']
    ao_dist = 0.24 * (h / 1.60)

    # Pre-classify materials by slot index
    mat_kind = {}
    for idx, m in enumerate(me.materials):
        if m is None:
            mat_kind[idx] = 'other'
            continue
        b = (m.get('export_name') or m.name).split('.')[0]
        if b == 'eye' or b == 'metal':
            mat_kind[idx] = 'skip'
        elif b.startswith('face_'):
            mat_kind[idx] = 'face'
        elif b == 'skin':
            mat_kind[idx] = 'skin'
        elif b == 'hair':
            mat_kind[idx] = 'hair'
        elif b in FABRIC_META:
            mat_kind[idx] = 'fabric'
        else:
            mat_kind[idx] = 'other'

    # Compute per-vertex occlusion & geometric crease concavity
    vert_occ = [0.0] * len(bm.verts)
    vert_conc = [0.0] * len(bm.verts)
    vert_z = [v.co.z / max(h, 0.5) for v in bm.verts]
    for vi, v in enumerate(bm.verts):
        p = v.co
        n = v.normal
        if n.length < 1e-6:
            continue
        n = n.normalized()
        ref = Vector((1.0, 0.0, 0.0)) if abs(n.z) > 0.85 else Vector((0.0, 0.0, 1.0))
        t = ref.cross(n).normalized()
        b = n.cross(t)
        origin = p + n * 0.004
        occ = 0.0
        for d in HEMI_14:
            rd = t * d.x + b * d.y + n * d.z
            hit, _, _, dist = bvh.ray_cast(origin, rd, ao_dist)
            if hit is not None and dist > 0.003:
                w = 1.0 - (dist / ao_dist)
                occ += w * w
        vert_occ[vi] = min(1.0, (occ / len(HEMI_14)) * 2.2)

        # Crease concavity: positive = folded trough (darken), negative = convex ridge (soft sunlit lift)
        n_ed = len(v.link_edges)
        if n_ed:
            conv = 0.0
            for e in v.link_edges:
                dv = e.other_vert(v).co - p
                ln = dv.length
                if ln > 1e-5:
                    conv += dv.dot(n) / ln
            vert_conc[vi] = conv / n_ed

    bm.free()

    for poly in me.polygons:
        kind = mat_kind.get(poly.material_index, 'other')
        if kind == 'skip':
            continue
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            occ = vert_occ[vi]
            conv = vert_conc[vi]
            zn = vert_z[vi]
            c = col_attr.data[li].color

            if kind == 'face':
                # Ultra-gentle AO on face only (keeps face luminous & warm, subtle chin/socket depth)
                k = 1.0 - occ * 0.10
                r_m, g_m, b_m = k, k * (1.0 - occ * 0.02), k * (1.0 - occ * 0.03)
            elif kind == 'skin':
                # Soft neck-under-chin and inner-palm occlusion with warm subsurface preservation
                k = 1.0 - occ * 0.19
                r_m, g_m, b_m = k, k * (1.0 - occ * 0.04), k * (1.0 - occ * 0.06)
            elif kind == 'hair':
                # Rich strand/root crevice depth + subtle crown sunlit sheen
                crease = 1.0 - min(0.18, max(0.0, conv) * 0.42) + min(0.06, max(0.0, -conv) * 0.16)
                k = max(0.62, min(1.08, (1.0 - occ * 0.26) * crease * (0.95 + 0.08 * zn)))
                r_m = g_m = b_m = k
            else:
                # Garment fabrics: crisp cloth-fold crevice depth, gentle hem grounding & shoulder lift
                crease = 1.0 - min(0.26, max(0.0, conv) * 0.62) + min(0.06, max(0.0, -conv) * 0.18)
                grad = 0.89 + 0.14 * smoothstep(0.02, 0.72, zn)
                k = max(0.52, min(1.08, (1.0 - occ * 0.34) * crease * grad))
                r_m = g_m = b_m = k

            col_attr.data[li].color = (
                min(1.0, c[0] * r_m),
                min(1.0, c[1] * g_m),
                min(1.0, c[2] * b_m),
                c[3],
            )


def tri_count(obj):
    if obj is None or obj.type != 'MESH':
        return 0
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def bone_count(rig):
    return sum(1 for b in rig.data.bones if b.use_deform)


# ------------------------------------------------------------------ export & verification
def verify_glb(path, key, expected_clips):
    """Parse GLB JSON chunk and assert M5 contract (no outline, allowed mats, clips, head bone, budgets)."""
    raw = Path(path).read_bytes()
    size_kb = len(raw) / 1024.0
    if size_kb > 280.0:
        raise RuntimeError(f'{key}.glb size {size_kb:.1f} KB exceeds 280 KB budget')
    jlen = struct.unpack('<I', raw[12:16])[0]
    j = json.loads(raw[20:20 + jlen].decode('utf-8'))

    mats = [m.get('name', '') for m in j.get('materials', [])]
    for mn in mats:
        base = mn.split('.')[0]
        if base == 'outline':
            raise RuntimeError(f'{key}.glb must not export outline material')
        if base not in ALLOWED_MAT_BASES and base != f'face_{key}':
            raise RuntimeError(f'{key}.glb has disallowed material {mn!r}')

    n_imgs = len(j.get('images', []))
    if n_imgs != 1:
        raise RuntimeError(f'{key}.glb expected 1 embedded image (face/eye atlas), found {n_imgs}')

    nodes = [n.get('name', '') for n in j.get('nodes', [])]
    if 'head' not in nodes:
        raise RuntimeError(f'{key}.glb missing head bone node')

    clips = [a.get('name', '') for a in j.get('animations', [])]
    for c in expected_clips:
        if c not in clips:
            raise RuntimeError(f'{key}.glb missing clip {c!r}; found {clips}')

    joints = len(j.get('skins', [{}])[0].get('joints', []))
    if joints != 22:
        raise RuntimeError(f'{key}.glb expected 22 joints, found {joints}')

    return {'mats': mats, 'clips': clips, 'images': n_imgs, 'joints': joints}


def export_glb(info):
    """Export one character (rig + mesh, zero outline) as Draco-6 Y-up GLB and verify contract."""
    os.makedirs(MODELS, exist_ok=True)
    set_all_mat_mode('export')

    rig = info['rig']
    mesh = info['mesh']

    # Temporarily rename character's eye material to exact 'eye' (clearing any other 'eye' collision)
    renamed = []
    other_eye = bpy.data.materials.get('eye')
    char_eye = next((m for m in mesh.data.materials if m and m.get('export_name') == 'eye'), None)
    if other_eye is not None and other_eye != char_eye:
        renamed.append((other_eye, other_eye.name))
        other_eye.name = '_tmp_other_eye'
    if char_eye is not None and char_eye.name != 'eye':
        renamed.append((char_eye, char_eye.name))
        char_eye.name = 'eye'

    loc0 = rig.location.copy()
    act0 = rig.animation_data.action if rig.animation_data else None
    rig.location = (0.0, 0.0, 0.0)
    if rig.animation_data:
        rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.location = (0.0, 0.0, 0.0)
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()

    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in (rig, mesh):
        o.hide_set(False)
        o.hide_viewport = False
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig

    path = MODELS + info['key'] + '.glb'
    try:
        bpy.ops.export_scene.gltf(
            filepath=path,
            export_format='GLB',
            use_selection=True,
            export_yup=True,
            export_apply=False,
            export_skins=True,
            export_animations=True,
            export_animation_mode='NLA_TRACKS',
            export_optimize_animation_size=True,
            export_draco_mesh_compression_enable=True,
            export_draco_mesh_compression_level=6,
            export_image_format='AUTO',
            export_materials='EXPORT',
            export_morph=False,
        )
    finally:
        for mat, orig in reversed(renamed):
            mat.name = orig
        rig.location = loc0
        if rig.animation_data and act0:
            rig.animation_data.action = act0
        set_all_mat_mode('preview')

    if info['tris'] > 9000:
        raise RuntimeError(f"{info['key']}: tris {info['tris']} exceeds 9000 budget")

    size_kb = round(os.path.getsize(path) / 1024.0, 1)
    check = verify_glb(path, info['key'], info['expected_clips'])
    info['glb'] = path
    info['glb_kb'] = size_kb
    info['mats'] = check['mats']
    info['clips'] = check['clips']
    return path, size_kb
