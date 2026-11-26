"""Shared Blender v4 environment pipeline helpers (UVs, recessed walls, BVH AO/wear, export, previews).

Run headless via houses.py or landmarks.py from repo root:
  blender -b --factory-startup --python blender/v4/env/houses.py
  blender -b --factory-startup --python blender/v4/env/landmarks.py
"""
import json
import math
import os
import random
import struct
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector, noise
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[3]
OUT_MODELS = ROOT / 'public' / 'models' / 'env'
TEX_V4 = ROOT / 'public' / 'textures' / 'v4'
PREVIEWS = ROOT / 'blender' / 'v4' / 'previews'

# Material contract (exact array order matching src/game/shaders/buildingMaterial.js)
LAYERS = (
    'ph_plaster',
    'ph_mudbrick',
    'ph_blue',
    'ph_wood',
    'ph_floor',
    'ph_stone',
    'ph_cloth',
    'ph_dark',
)

# (polyhaven_id_or_None, tile_m, diff_avg_lin, detail_strength, real_mix, normal_strength)
LAYER_META = {
    'ph_plaster':  ('clay_plaster',           2.5, (0.170, 0.102, 0.046), 0.72, 0.08, 0.65),
    'ph_mudbrick': ('clay_block_wall',        2.0, (0.226, 0.133, 0.062), 0.85, 0.42, 1.05),
    'ph_blue':     ('blue_plaster_weathered', 2.5, (0.243, 0.375, 0.351), 0.78, 0.28, 0.72),
    'ph_wood':     ('weathered_brown_planks', 1.6, (0.116, 0.071, 0.040), 0.85, 0.40, 0.95),
    'ph_floor':    ('clay_floor_001',         2.0, (0.195, 0.117, 0.047), 0.78, 0.25, 0.75),
    'ph_stone':    ('sandstone_blocks_05',    2.4, (0.428, 0.330, 0.230), 0.88, 0.52, 1.15),
    'ph_cloth':    ('hessian_230',            1.2, (0.263, 0.188, 0.100), 0.85, 0.30, 0.85),
    'ph_dark':     (None,                     1.0, (0.045, 0.036, 0.030), 0.00, 0.00, 0.00),
}

# Minimal 5x7 bitmap font for contact sheet labels
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
    ',': (0x00, 0x00, 0x00, 0x00, 0x04, 0x04, 0x08),
    '+': (0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00),
    '&': (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
}


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0


def srgb_to_linear(hex_str):
    h = hex_str.lstrip('#')
    vals = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in vals)


def rgb_srgb_to_linear(r, g, b):
    def conv(v):
        v = max(0.0, min(1.0, v))
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (conv(r), conv(g), conv(b))


def jitter_linear(color, rnd, spread=0.045):
    """Return jittered linear RGB tuple from either '#rrggbb' (sRGB) or linear (r, g, b)."""
    if isinstance(color, str):
        h = color.lstrip('#')
        r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
        if spread > 0:
            k = 1.0 + rnd.uniform(-spread, spread)
            warm = rnd.uniform(-spread * 0.3, spread * 0.3)
            r = max(0.0, min(1.0, r * k + warm))
            g = max(0.0, min(1.0, g * k))
            b = max(0.0, min(1.0, b * k - warm * 0.5))
        return rgb_srgb_to_linear(r, g, b)
    r, g, b = color[:3]
    if spread > 0:
        k = 1.0 + rnd.uniform(-spread, spread)
        return (max(0.0, min(1.0, r * k)), max(0.0, min(1.0, g * k)), max(0.0, min(1.0, b * k)))
    return (r, g, b)


def make_material(name, textured=False, tex_size=1024):
    """Create a geometry-only ph_* material for export, or a live-textured one for preview renders."""
    if name not in LAYER_META:
        raise ValueError(f'Unknown v4 building material: {name!r}')
    key = f'{name}__prev' if textured else name
    mat = bpy.data.materials.get(key)
    if mat:
        return mat
    mat = bpy.data.materials.new(key)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    pbr = nt.nodes.new('ShaderNodeBsdfPrincipled')
    pbr.inputs['Roughness'].default_value = 0.90
    if 'Specular IOR Level' in pbr.inputs:
        pbr.inputs['Specular IOR Level'].default_value = 0.25

    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = 'Color'

    tex_id, tile_m, avg_lin, det_s, real_m, nor_s = LAYER_META[name]
    if not textured or tex_id is None:
        nt.links.new(vc.outputs['Color'], pbr.inputs['Base Color'])
        if name == 'ph_dark':
            pbr.inputs['Roughness'].default_value = 0.98
        nt.links.new(pbr.outputs['BSDF'], out.inputs['Surface'])
        return mat

    # Preview material matching buildingMaterial.js look using Poly Haven v4 WebPs
    uv = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    inv = 1.0 / tile_m
    mp.inputs['Scale'].default_value = (inv, inv, 1.0)
    nt.links.new(uv.outputs['UV'], mp.inputs['Vector'])

    tdir = TEX_V4 / str(tex_size)
    diff_img = bpy.data.images.load(str(tdir / f'{tex_id}_diff.webp'), check_existing=True)
    diff_img.colorspace_settings.name = 'sRGB'
    nor_img = bpy.data.images.load(str(tdir / f'{tex_id}_nor.webp'), check_existing=True)
    nor_img.colorspace_settings.name = 'Non-Color'
    arm_img = bpy.data.images.load(str(tdir / f'{tex_id}_arm.webp'), check_existing=True)
    arm_img.colorspace_settings.name = 'Non-Color'

    n_diff = nt.nodes.new('ShaderNodeTexImage')
    n_diff.image = diff_img
    nt.links.new(mp.outputs['Vector'], n_diff.inputs['Vector'])

    n_nor = nt.nodes.new('ShaderNodeTexImage')
    n_nor.image = nor_img
    nt.links.new(mp.outputs['Vector'], n_nor.inputs['Vector'])

    n_arm = nt.nodes.new('ShaderNodeTexImage')
    n_arm.image = arm_img
    nt.links.new(mp.outputs['Vector'], n_arm.inputs['Vector'])

    # detail = clamp(tex / avg, 0.45, 1.65); albedo = vc * mix(1, detail, det_s)
    div = nt.nodes.new('ShaderNodeVectorMath')
    div.operation = 'DIVIDE'
    div.inputs[1].default_value = avg_lin
    nt.links.new(n_diff.outputs['Color'], div.inputs[0])

    # Clamp detail ratio via Mix with white
    mix_det = nt.nodes.new('ShaderNodeMix')
    mix_det.data_type = 'RGBA'
    mix_det.inputs['Factor'].default_value = det_s
    mix_det.inputs[6].default_value = (1.0, 1.0, 1.0, 1.0)
    nt.links.new(div.outputs['Vector'], mix_det.inputs[7])

    mul_vc = nt.nodes.new('ShaderNodeMix')
    mul_vc.data_type = 'RGBA'
    mul_vc.blend_type = 'MULTIPLY'
    mul_vc.inputs['Factor'].default_value = 1.0
    nt.links.new(vc.outputs['Color'], mul_vc.inputs[6])
    nt.links.new(mix_det.outputs[2], mul_vc.inputs[7])

    # Real-texture colour blend scaled by vertex luminance
    if real_m > 0.01:
        vc_bw = nt.nodes.new('ShaderNodeRGBToBW')
        nt.links.new(vc.outputs['Color'], vc_bw.inputs['Color'])
        avg_lum = max(0.01, avg_lin[0] * 0.2126 + avg_lin[1] * 0.7152 + avg_lin[2] * 0.0722)
        sc = nt.nodes.new('ShaderNodeMath')
        sc.operation = 'DIVIDE'
        sc.inputs[1].default_value = avg_lum
        nt.links.new(vc_bw.outputs['Val'], sc.inputs[0])
        real_sc = nt.nodes.new('ShaderNodeVectorMath')
        real_sc.operation = 'SCALE'
        nt.links.new(n_diff.outputs['Color'], real_sc.inputs[0])
        nt.links.new(sc.outputs['Value'], real_sc.inputs['Scale'])

        mix_real = nt.nodes.new('ShaderNodeMix')
        mix_real.data_type = 'RGBA'
        mix_real.inputs['Factor'].default_value = real_m * 0.75
        nt.links.new(mul_vc.outputs[2], mix_real.inputs[6])
        nt.links.new(real_sc.outputs['Vector'], mix_real.inputs[7])
        albedo_out = mix_real.outputs[2]
    else:
        albedo_out = mul_vc.outputs[2]

    sep = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(n_arm.outputs['Color'], sep.inputs['Color'])

    ao_mix = nt.nodes.new('ShaderNodeMix')
    ao_mix.data_type = 'RGBA'
    ao_mix.blend_type = 'MULTIPLY'
    ao_mix.inputs['Factor'].default_value = 0.45
    nt.links.new(albedo_out, ao_mix.inputs[6])
    nt.links.new(sep.outputs['Red'], ao_mix.inputs[7])
    nt.links.new(ao_mix.outputs[2], pbr.inputs['Base Color'])

    r_map = nt.nodes.new('ShaderNodeMapRange')
    r_map.inputs['To Min'].default_value = 0.72 if name in ('ph_wood', 'ph_floor') else 0.80
    r_map.inputs['To Max'].default_value = 0.96
    nt.links.new(sep.outputs['Green'], r_map.inputs['Value'])
    nt.links.new(r_map.outputs['Result'], pbr.inputs['Roughness'])

    nmap = nt.nodes.new('ShaderNodeNormalMap')
    nmap.inputs['Strength'].default_value = nor_s * 0.75
    nt.links.new(n_nor.outputs['Color'], nmap.inputs['Color'])
    nt.links.new(nmap.outputs['Normal'], pbr.inputs['Normal'])

    nt.links.new(pbr.outputs['BSDF'], out.inputs['Surface'])
    return mat


def _wob(p, amp, freq=1.3, seed=0):
    if not amp:
        return p
    o = Vector((seed * 7.1, seed * 3.3, seed * 1.7))
    return p + noise.noise_vector(p * freq + o) * amp


def rt(loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    return Matrix.LocRotScale(Vector(loc), Euler(rot), Vector(scale))


def _world_box_uv(co, fn):
    """Real-metre box UV projection: V strictly up on walls, right-handed U on every face."""
    ax, ay, az = abs(fn.x), abs(fn.y), abs(fn.z)
    if az > 0.72:
        u = co.x if fn.z >= 0 else -co.x
        v = co.y
        return (u, v)
    if ay >= ax:
        u = co.x if fn.y < 0 else -co.x
        return (u, co.z)
    u = co.y if fn.x > 0 else -co.y
    return (u, co.z)


def _local_grain_uv(co, fn, grain):
    """Real-metre UV with U running along `grain` ('x', 'y', or 'z') in local plank/beam space."""
    ax, ay, az = abs(fn.x), abs(fn.y), abs(fn.z)
    if grain == 'x':
        if ax > 0.75:
            return (co.y, co.z)
        v = co.y if az > 0.70 else co.z
        return (co.x, v)
    if grain == 'y':
        if ay > 0.75:
            return (co.x, co.z)
        v = co.x if az > 0.70 else co.z
        return (co.y, v)
    # grain == 'z' (vertical posts, door boards, shutters)
    if az > 0.75:
        return (co.x, co.y)
    v = co.x if ay >= ax else co.y
    return (co.z, v)


class V4Builder:
    """Multi-material bmesh builder emitting real-metre UVs and linear FLOAT_COLOR vertex colors."""

    def __init__(self, seed=0):
        self.bm = bmesh.new()
        self.uv_layer = self.bm.loops.layers.uv.new('UVMap')
        self.col_layer = self.bm.loops.layers.float_color.new('Color')
        self.mats = []
        self.seed = seed
        self.rnd = random.Random(seed)

    def mi(self, name):
        if name not in LAYER_META:
            raise ValueError(f'Disallowed material {name!r}; must be in LAYERS')
        if name not in self.mats:
            self.mats.append(name)
        return self.mats.index(name)

    def put(self, src, mat_name, color, mat4=None, smooth=True, wobble=0.0, freq=1.3,
            grain=None, uv_off=None, spread=0.035, uv_scale=1.0, custom_uv=None):
        src.verts.index_update()
        src.normal_update()
        lin = jitter_linear(color, self.rnd, spread)
        rgba = (lin[0], lin[1], lin[2], 1.0)
        uo, vo = uv_off if uv_off is not None else (0.0, 0.0)

        local_cos = [v.co.copy() for v in src.verts]
        vm = []
        for v in src.verts:
            p = (mat4 @ v.co) if mat4 is not None else v.co.copy()
            vm.append(self.bm.verts.new(_wob(p, wobble, freq, self.seed)))

        k = self.mi(mat_name)
        for fi, f in enumerate(src.faces):
            fverts = [vm[v.index] for v in f.verts]
            try:
                nf = self.bm.faces.new(fverts)
            except ValueError:
                continue
            nf.material_index = k
            nf.smooth = smooth
            nf.normal_update()
            if custom_uv is not None:
                cuvs = custom_uv[fi]
                for lp, (u, v) in zip(nf.loops, cuvs):
                    lp[self.uv_layer].uv = (u * uv_scale + uo, v * uv_scale + vo)
                    lp[self.col_layer] = rgba
            elif grain is not None:
                fn_loc = f.normal
                for lp, sv in zip(nf.loops, f.verts):
                    u, v = _local_grain_uv(local_cos[sv.index], fn_loc, grain)
                    lp[self.uv_layer].uv = (u * uv_scale + uo, v * uv_scale + vo)
                    lp[self.col_layer] = rgba
            else:
                fn = nf.normal
                for lp in nf.loops:
                    u, v = _world_box_uv(lp.vert.co, fn)
                    lp[self.uv_layer].uv = (u * uv_scale + uo, v * uv_scale + vo)
                    lp[self.col_layer] = rgba
        src.free()
        return self

    def box(self, size, loc=(0, 0, 0), mat='ph_plaster', color='#EFE2C6', bevel=0.0, seg=1,
            rot=(0, 0, 0), taper=1.0, taper_y=None, smooth=True, wobble=0.0, freq=1.3,
            grain=None, uv_off=None, spread=0.035, top_only=False, uv_scale=1.0):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
            if v.co.z > 0 and (taper != 1.0 or taper_y is not None):
                v.co.x *= taper
                v.co.y *= (taper if taper_y is None else taper_y)
        if bevel > 0:
            ed = bm.edges[:] if not top_only else [e for e in bm.edges if all(v.co.z > 0 for v in e.verts)]
            bmesh.ops.bevel(
                bm, geom=ed,
                offset=min(bevel, min(size) * 0.45), segments=seg,
                affect='EDGES', profile=0.5, clamp_overlap=True,
            )
        return self.put(bm, mat, color, rt(loc, rot), smooth, wobble, freq,
                        grain=grain, uv_off=uv_off, spread=spread, uv_scale=uv_scale)

    def cyl(self, r1, r2, depth, loc=(0, 0, 0), mat='ph_wood', color='#9A6B3F',
            rot=(0, 0, 0), verts=8, smooth=True, cap=True, wobble=0.0, bevel=0.0,
            scale=(1, 1, 1), grain='z', uv_off=None, spread=0.04, uv_scale=1.0):
        bm = bmesh.new()
        bmesh.ops.create_cone(
            bm, cap_ends=cap, cap_tris=False, segments=verts,
            radius1=r1, radius2=r2, depth=depth,
        )
        if bevel > 0 and cap:
            ed = [
                e for e in bm.edges
                if len(e.link_faces) == 2 and abs(e.link_faces[0].normal.dot(e.link_faces[1].normal)) < 0.5
            ]
            if ed:
                bmesh.ops.bevel(
                    bm, geom=ed, offset=bevel, segments=2,
                    affect='EDGES', profile=0.5, clamp_overlap=True,
                )
        # Cylindrical metric UVs for curved sides + planar caps
        bm.normal_update()
        rm = max(r1, r2, 0.05)
        circ = math.tau * rm
        cuvs = []
        for f in bm.faces:
            if abs(f.normal.z) > 0.72:
                cuvs.append([(v.co.x, v.co.y) for v in f.verts])
            else:
                angs = [math.atan2(v.co.y, v.co.x) for v in f.verts]
                # Unwrap seam crossing [-pi, pi]
                a0 = angs[0]
                u_ring = []
                for a in angs:
                    da = a - a0
                    if da > math.pi:
                        a -= math.tau
                    elif da < -math.pi:
                        a += math.tau
                    u_ring.append((a / math.tau) * circ)
                if grain == 'z':
                    cuvs.append([(v.co.z + depth * 0.5, u) for v, u in zip(f.verts, u_ring)])
                else:
                    cuvs.append([(u, v.co.z + depth * 0.5) for v, u in zip(f.verts, u_ring)])
        return self.put(bm, mat, color, rt(loc, rot, scale), smooth, wobble,
                        uv_off=uv_off, spread=spread, uv_scale=uv_scale, custom_uv=cuvs)

    def lathe(self, prof, loc=(0, 0, 0), mat='ph_plaster', color='#EFE2C6', segs=12,
              rot=(0, 0, 0), smooth=True, close_top=False, wobble=0.0, scale=(1, 1, 1),
              spread=0.03, uv_off=None):
        """Revolved profile `[(r, z), ...]` with metric circumferential U and arc-length V."""
        bm = bmesh.new()
        rings = []
        arc_v = [0.0]
        for i in range(1, len(prof)):
            dr = prof[i][0] - prof[i - 1][0]
            dz = prof[i][1] - prof[i - 1][1]
            arc_v.append(arc_v[-1] + math.hypot(dr, dz))
        max_r = max((r for r, _ in prof), default=0.5)
        circ = math.tau * max(max_r, 0.1)

        for r, z in prof:
            if r < 1e-3:
                rings.append([bm.verts.new((0.0, 0.0, z))])
            else:
                rings.append([
                    bm.verts.new((r * math.cos(i / segs * math.tau), r * math.sin(i / segs * math.tau), z))
                    for i in range(segs)
                ])

        cuvs = []
        for idx, (a, b) in enumerate(zip(rings, rings[1:])):
            v0, v1 = arc_v[idx], arc_v[idx + 1]
            if len(a) == 1:
                for i in range(segs):
                    u0 = (i / segs) * circ
                    u1 = ((i + 1) / segs) * circ
                    bm.faces.new((a[0], b[i], b[(i + 1) % segs]))
                    cuvs.append([((u0 + u1) * 0.5, v0), (u0, v1), (u1, v1)])
            elif len(b) == 1:
                for i in range(segs):
                    u0 = (i / segs) * circ
                    u1 = ((i + 1) / segs) * circ
                    bm.faces.new((a[i], a[(i + 1) % segs], b[0]))
                    cuvs.append([(u0, v0), (u1, v0), ((u0 + u1) * 0.5, v1)])
            else:
                for i in range(segs):
                    u0 = (i / segs) * circ
                    u1 = ((i + 1) / segs) * circ
                    bm.faces.new((a[i], a[(i + 1) % segs], b[(i + 1) % segs], b[i]))
                    cuvs.append([(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
        if close_top and len(rings[-1]) > 1:
            bm.faces.new(rings[-1])
            cuvs.append([(v.co.x, v.co.y) for v in rings[-1]])
        return self.put(bm, mat, color, rt(loc, rot, scale), smooth, wobble,
                        spread=spread, uv_off=uv_off, custom_uv=cuvs)

    def quad(self, pts, mat, color, smooth=False, spread=0.02, uv_off=None):
        bm = bmesh.new()
        vs = [bm.verts.new(Vector(p)) for p in pts]
        bm.faces.new(vs)
        return self.put(bm, mat, color, None, smooth, spread=spread, uv_off=uv_off)

    def wall_shell(self, w, d, h, mat='ph_plaster', color='#F2E5CC', taper=0.978,
                   corner_bevel=0.14, wobble=0.025, openings=None, reveal_mat=None,
                   reveal_color=None, back_color='#2B201A'):
        """Build a 4-walled tapered mudbrick house shell with REAL geometric recessed openings.

        `openings`: list of dicts:
          face: 'front' (-Y), 'back' (+Y), 'left' (-X), 'right' (+X)
          s: centre along face horizontal axis (metres, world X on front/back, world Y on left/right)
          z0, z1: opening bottom & top height (metres)
          w: opening width (metres)
          depth: recess depth inward (default 0.18 m)
          mat, color: optional override for reveal jambs
          back: bool (emit recessed ph_dark backing quad, default True)
        """
        openings = openings or []
        rmat = reveal_mat or mat
        rcol = reveal_color or color
        hw, hd = w * 0.5, d * 0.5
        cb = min(corner_bevel, w * 0.08, d * 0.08)

        def scale_at(z):
            t = max(0.0, min(1.0, z / max(h, 1e-4)))
            return 1.0 + (taper - 1.0) * t

        # Face descriptors: (name, half_span, half_depth, map_pt(s, z, inset)->Vector)
        faces_spec = [
            ('front', hw - cb, hd, lambda s, z, ins: Vector((s * scale_at(z), (-hd + ins) * scale_at(z), z))),
            ('back',  hw - cb, hd, lambda s, z, ins: Vector((-s * scale_at(z), (hd - ins) * scale_at(z), z))),
            ('right', hd - cb, hw, lambda s, z, ins: Vector(((hw - ins) * scale_at(z), s * scale_at(z), z))),
            ('left',  hd - cb, hw, lambda s, z, ins: Vector(((-hw + ins) * scale_at(z), -s * scale_at(z), z))),
        ]

        # Build each main wall face with clean grid subdivisions around recessed openings
        for fname, hspan, _, pt_fn in faces_spec:
            f_ops = []
            for op in openings:
                if op['face'] != fname:
                    continue
                # Convert world horizontal coordinate into face-local s (right-handed when facing wall)
                s_c = op['s'] if fname in ('front', 'right') else -op['s']
                s0 = max(-hspan + 0.08, s_c - op['w'] * 0.5)
                s1 = min(hspan - 0.08, s_c + op['w'] * 0.5)
                z0 = max(0.0, op['z0'])
                z1 = min(h - 0.12, op['z1'])
                f_ops.append((s0, s1, z0, z1, op))

            s_cuts = {-hspan, hspan}
            z_cuts = {0.0, min(0.50, h * 0.25), h * 0.55, max(h - 0.42, h * 0.72), h}
            # Gentle horizontal subdivisions (~1.3 m) for smooth hand-plaster wobble & AO
            n_sub = max(2, int(round((2 * hspan) / 1.35)))
            for i in range(1, n_sub):
                s_cuts.add(-hspan + (2 * hspan) * i / n_sub)
            for s0, s1, z0, z1, _ in f_ops:
                s_cuts.add(s0)
                s_cuts.add(s1)
                z_cuts.add(z0)
                z_cuts.add(z1)

            def _dedup(vals, eps=0.03):
                out = []
                for v in sorted(vals):
                    if not out or v - out[-1] > eps:
                        out.append(v)
                    elif v == max(vals):
                        out[-1] = v
                return out

            # Keep exact opening boundaries by preferring them during dedup
            exact_s = {-hspan, hspan} | {x for s0, s1, _, _, _ in f_ops for x in (s0, s1)}
            exact_z = {0.0, h} | {z for _, _, z0, z1, _ in f_ops for z in (z0, z1)}
            s_list = sorted(exact_s | {s for s in s_cuts if all(abs(s - ex) > 0.14 for ex in exact_s)})
            z_list = sorted(exact_z | {z for z in z_cuts if all(abs(z - ex) > 0.14 for ex in exact_z)})

            bm = bmesh.new()
            grid = {}
            for iz, z in enumerate(z_list):
                for is_, s in enumerate(s_list):
                    p = pt_fn(s, z, 0.0)
                    # Keep exact opening edges crisp (less wobble on frame edges)
                    w_amp = wobble * 0.25 if (s in exact_s and z in exact_z) else wobble
                    grid[(is_, iz)] = bm.verts.new(_wob(p, w_amp, 0.75, self.seed))

            for iz in range(len(z_list) - 1):
                zm = 0.5 * (z_list[iz] + z_list[iz + 1])
                for is_ in range(len(s_list) - 1):
                    sm = 0.5 * (s_list[is_] + s_list[is_ + 1])
                    inside = any(s0 < sm < s1 and z0 < zm < z1 for s0, s1, z0, z1, _ in f_ops)
                    if inside:
                        continue
                    v00 = grid[(is_, iz)]
                    v10 = grid[(is_ + 1, iz)]
                    v11 = grid[(is_ + 1, iz + 1)]
                    v01 = grid[(is_, iz + 1)]
                    bm.faces.new((v00, v10, v11, v01))
            self.put(bm, mat, color, None, smooth=True, wobble=0.0, spread=0.015)

            # Emit real 3D recessed reveal walls (jambs, sill, lintel soffit) & recessed backing
            for s0, s1, z0, z1, op in f_ops:
                dep = op.get('depth', 0.18)
                om = op.get('mat', rmat)
                oc = op.get('color', rcol)
                p00 = pt_fn(s0, z0, 0.0)
                p10 = pt_fn(s1, z0, 0.0)
                p11 = pt_fn(s1, z1, 0.0)
                p01 = pt_fn(s0, z1, 0.0)
                q00 = pt_fn(s0, z0, dep)
                q10 = pt_fn(s1, z0, dep)
                q11 = pt_fn(s1, z1, dep)
                q01 = pt_fn(s0, z1, dep)

                # Inward-facing reveal sides (normals point into the opening cavity)
                rbm = bmesh.new()
                for quad_pts in (
                    (p00, p01, q01, q00),   # left jamb
                    (p10, q10, q11, p11),   # right jamb
                    (p01, p11, q11, q01),   # top lintel soffit
                    (p00, q00, q10, p10),   # bottom sill
                ):
                    if (quad_pts[1] - quad_pts[0]).length > 1e-4:
                        rbm.faces.new([rbm.verts.new(v) for v in quad_pts])
                self.put(rbm, om, oc, None, smooth=False, wobble=0.0, spread=0.01)

                if op.get('back', True):
                    bbm = bmesh.new()
                    bbm.faces.new([bbm.verts.new(v) for v in (q00, q10, q11, q01)])
                    self.put(bbm, 'ph_dark', back_color, None, smooth=False, spread=0.0)

        # Rounded vertical corner fillets connecting the 4 walls cleanly (hand-plastered silhouette!)
        c_z = [0.0, h * 0.20, h * 0.55, h * 0.85, h]
        corners = [
            (hw - cb, -hd + cb, -math.pi * 0.5, 0.0),         # front-right
            (hw - cb,  hd - cb,  0.0,           math.pi * 0.5),  # back-right
            (-hw + cb, hd - cb,  math.pi * 0.5, math.pi),        # back-left
            (-hw + cb, -hd + cb, math.pi,       math.pi * 1.5),  # front-left
        ]
        c_segs = 3
        cbm = bmesh.new()
        for cx, cy, a0, a1 in corners:
            rows = []
            for z in c_z:
                sc = scale_at(z)
                row = []
                for j in range(c_segs + 1):
                    a = a0 + (a1 - a0) * (j / c_segs)
                    px = (cx + math.cos(a) * cb) * sc
                    py = (cy + math.sin(a) * cb) * sc
                    row.append(cbm.verts.new(_wob(Vector((px, py, z)), wobble * 0.7, 0.75, self.seed)))
                rows.append(row)
            for iz in range(len(c_z) - 1):
                for j in range(c_segs):
                    cbm.faces.new((rows[iz][j], rows[iz][j + 1], rows[iz + 1][j + 1], rows[iz + 1][j]))
        self.put(cbm, mat, color, None, smooth=True, wobble=0.0, spread=0.015)

        # Roof deck cap so the shell is completely closed from above
        t_top = scale_at(h)
        self.box(
            ((w - 0.14) * t_top, (d - 0.14) * t_top, 0.12),
            (0.0, 0.0, h - 0.04),
            mat='ph_floor', color='#B99364', smooth=False, spread=0.02,
        )
        return self

    def merge_from(self, other, mat4=None):
        other.bm.verts.index_update()
        vm = [self.bm.verts.new((mat4 @ v.co) if mat4 is not None else v.co.copy()) for v in other.bm.verts]
        for f in other.bm.faces:
            try:
                nf = self.bm.faces.new([vm[v.index] for v in f.verts])
            except ValueError:
                continue
            nf.material_index = self.mi(other.mats[f.material_index])
            nf.smooth = f.smooth
            for lp_dst, lp_src in zip(nf.loops, f.loops):
                lp_dst[self.uv_layer].uv = lp_src[other.uv_layer].uv.copy()
                lp_dst[self.col_layer] = lp_src[other.col_layer]
        return self

    def to_object(self, name, col=None, textured=False):
        me = bpy.data.meshes.new(name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        for mname in self.mats:
            me.materials.append(make_material(mname, textured=textured))
        if me.color_attributes:
            idx = me.color_attributes.find('Color')
            if idx < 0:
                idx = 0
            me.color_attributes.active_color_index = idx
            me.color_attributes.render_color_index = idx
        obj = bpy.data.objects.new(name, me)
        (col or bpy.context.scene.collection).objects.link(obj)
        return obj


def _hemi_dirs(n=18):
    """Deterministic cosine-weighted Fibonacci hemisphere directions in tangent space (+Z up)."""
    dirs = []
    phi_step = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(n):
        u = (i + 0.5) / n
        r = math.sqrt(u)
        theta = i * phi_step
        x = r * math.cos(theta)
        y = r * math.sin(theta)
        z = math.sqrt(max(0.05, 1.0 - u))
        dirs.append(Vector((x, y, z)).normalized())
    return dirs


HEMI_18 = _hemi_dirs(18)


def bake_wear_and_ao(obj, base_z=0.0, eaves_z=None, ao_strength=0.40, ao_dist=1.55,
                     splash_h=0.62, splash_strength=0.18, grime_strength=0.11,
                     edge_lift=0.06, wet_z=None):
    """Bake real BVH raytraced AO + ground splash + under-parapet grime + worn edge lift into COLOR_0."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    bvh = BVHTree.FromBMesh(bm)

    # Identify ph_dark material index so recesses stay rich dark without edge brightening
    dark_mi = next((i for i, m in enumerate(me.materials) if m and m.name.startswith('ph_dark')), -1)

    factors = []
    for v in bm.verts:
        p = v.co
        n = v.normal
        if n.length < 1e-6:
            n = Vector((0.0, 0.0, 1.0))
        else:
            n = n.normalized()

        # Tangent frame around n
        ref = Vector((1.0, 0.0, 0.0)) if abs(n.z) > 0.85 else Vector((0.0, 0.0, 1.0))
        t = ref.cross(n).normalized()
        b = n.cross(t)

        # Raytraced hemisphere ambient occlusion (catches deep door/window recesses, under beams & eaves)
        origin = p + n * 0.015
        occ = 0.0
        for d in HEMI_18:
            rd = t * d.x + b * d.y + n * d.z
            hit, _, _, dist = bvh.ray_cast(origin, rd, ao_dist)
            if hit is not None and dist > 0.01:
                w = 1.0 - (dist / ao_dist)
                occ += w * w
        ao = 1.0 - ao_strength * min(1.0, (occ / len(HEMI_18)) * 2.35)

        # Geometric edge convexity / concavity
        conv = 0.0
        n_ed = len(v.link_edges)
        if n_ed:
            for e in v.link_edges:
                dvec = e.other_vert(v).co - p
                ln = dvec.length
                if ln > 1e-5:
                    conv += dvec.dot(n) / ln
            conv /= n_ed
        # conv > 0 => concave crease (darken); conv < 0 => convex corner/edge (soft sun-bleached wear lift)
        if conv > 0.0:
            edge_k = 1.0 - min(0.24, conv * 0.55)
        else:
            edge_k = 1.0 + min(edge_lift, (-conv) * 0.20)

        # Splashed earth wear along the base of walls
        r_m, g_m, b_m = 1.0, 1.0, 1.0
        if splash_h > 0.0 and splash_strength > 0.0:
            hz = (p.z - base_z) / splash_h
            if hz < 1.0:
                sp = max(0.0, 1.0 - max(0.0, hz))
                sp = sp * sp * splash_strength
                # Warm earthy splash darkening
                r_m *= 1.0 - sp * 0.72
                g_m *= 1.0 - sp * 0.92
                b_m *= 1.0 - sp * 1.15

        # Wet waterline darkening (e.g. Nile bridge piers near/below Z = 0)
        if wet_z is not None and p.z < wet_z + 0.55:
            wt = max(0.0, min(1.0, (wet_z + 0.55 - p.z) / 0.85))
            r_m *= 1.0 - wt * 0.36
            g_m *= 1.0 - wt * 0.32
            b_m *= 1.0 - wt * 0.40

        # Subtle rain grime under parapets / eaves on vertical walls
        if eaves_z is not None and grime_strength > 0.0 and abs(n.z) < 0.55:
            dz = eaves_z - p.z
            if -0.08 <= dz <= 0.55:
                streak = 0.55 + 0.45 * max(0.0, noise.noise(Vector((p.x * 2.2, p.y * 2.2, 1.7))))
                band = max(0.0, 1.0 - abs(dz - 0.10) / 0.45)
                gr = band * streak * grime_strength
                r_m *= 1.0 - gr * 0.85
                g_m *= 1.0 - gr * 0.95
                b_m *= 1.0 - gr * 1.05

        # Gentle macro plaster mottling (+-3.5%) so large walls feel hand-troweled
        mottle = 1.0 + noise.noise(p * 0.65 + Vector((3.1, 7.4, 2.2))) * 0.038
        k = max(0.45, min(1.12, ao * edge_k * mottle))
        factors.append((
            max(0.40, min(1.12, k * r_m)),
            max(0.40, min(1.12, k * g_m)),
            max(0.40, min(1.12, k * b_m)),
        ))

    bm.free()

    col_attr = me.color_attributes.get('Color')
    if col_attr is None:
        return
    if col_attr.domain == 'CORNER':
        for poly in me.polygons:
            if poly.material_index == dark_mi:
                continue
            for li in poly.loop_indices:
                vi = me.loops[li].vertex_index
                fr, fg, fb = factors[vi]
                c = col_attr.data[li].color
                col_attr.data[li].color = (
                    min(1.0, c[0] * fr),
                    min(1.0, c[1] * fg),
                    min(1.0, c[2] * fb),
                    c[3],
                )
    else:
        for i, (fr, fg, fb) in enumerate(factors):
            c = col_attr.data[i].color
            col_attr.data[i].color = (min(1.0, c[0] * fr), min(1.0, c[1] * fg), min(1.0, c[2] * fb), c[3])


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def bounds_summary(obj):
    vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
    xs = [v.x for v in vs]
    ys = [v.y for v in vs]
    zs = [v.z for v in vs]
    vs22 = [v for v in vs if v.z < 2.2]
    xs2 = [v.x for v in vs22] if vs22 else xs
    ys2 = [v.y for v in vs22] if vs22 else ys
    return {
        'all': (round(min(xs), 2), round(max(xs), 2), round(min(ys), 2), round(max(ys), 2), round(min(zs), 2), round(max(zs), 2)),
        'lt22': (round(min(xs2), 2), round(max(xs2), 2), round(min(ys2), 2), round(max(ys2), 2)),
    }


def make_lod1(obj, max_tris, name=None):
    """Create a decimated LOD1 sibling mesh strictly within `max_tris` preserving materials & UVs."""
    copy_obj = obj.copy()
    copy_obj.data = obj.data.copy()
    copy_obj.name = name or f'{obj.name}_LOD1'
    for col in obj.users_collection:
        col.objects.link(copy_obj)

    cur = tri_count(copy_obj)
    if cur <= max_tris:
        return copy_obj

    for delimit in ({'MATERIAL', 'UV'}, {'MATERIAL'}, set()):
        cur = tri_count(copy_obj)
        if cur <= max_tris:
            break
        ratio = max(0.08, min(0.95, (max_tris * 0.94) / max(cur, 1)))
        mod = copy_obj.modifiers.new('lod', 'DECIMATE')
        mod.decimate_type = 'COLLAPSE'
        mod.ratio = ratio
        mod.delimit = delimit
        mod.use_collapse_triangulate = True
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        ev = copy_obj.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev)
        me.validate(clean_customdata=False)
        copy_obj.modifiers.clear()
        old = copy_obj.data
        copy_obj.data = me
        me.name = copy_obj.name
        bpy.data.meshes.remove(old)
    return copy_obj


def verify_glb_contract(path, expected_name, lod0_budget, lod1_budget=None):
    """Verify exported GLB carries geometry only (no images/textures) and only ph_* materials."""
    raw = Path(path).read_bytes()
    jlen = struct.unpack('<I', raw[12:16])[0]
    j = json.loads(raw[20:20 + jlen].decode('utf-8'))
    if j.get('images') or j.get('textures'):
        raise RuntimeError(f'{expected_name}: GLB must not contain images/textures!')
    bad_mats = [m.get('name', '') for m in j.get('materials', []) if m.get('name', '').split('.')[0] not in LAYER_META]
    if bad_mats:
        raise RuntimeError(f'{expected_name}: disallowed material names in GLB: {bad_mats}')
    return len(raw)


def export_asset(name, obj, lod0_budget, lod1_budget=None, max_lt22=None):
    """Validate budgets & bounds, build LOD1, export Draco-6 geometry-only GLB, return info dict."""
    t0 = tri_count(obj)
    if t0 > lod0_budget:
        raise RuntimeError(f'{name}: LOD0 tris {t0} > budget {lod0_budget}')

    bs = bounds_summary(obj)
    if max_lt22 is not None:
        x0, x1, y0, y1 = bs['lt22']
        bx0, bx1, by0, by1 = max_lt22
        tol = 0.02
        if x0 < bx0 - tol or x1 > bx1 + tol or y0 < by0 - tol or y1 > by1 + tol:
            raise RuntimeError(
                f'{name}: <2.2m bounds X[{x0},{x1}] Y[{y0},{y1}] exceed limit X[{bx0},{bx1}] Y[{by0},{by1}]'
            )

    objs = [obj]
    t1 = 0
    if lod1_budget is not None:
        lod1 = make_lod1(obj, lod1_budget, name=f'{name}_LOD1')
        t1 = tri_count(lod1)
        if t1 > lod1_budget:
            raise RuntimeError(f'{name}: LOD1 tris {t1} > budget {lod1_budget}')
        objs.append(lod1)

    OUT_MODELS.mkdir(parents=True, exist_ok=True)
    out_path = OUT_MODELS / f'{name}.glb'
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.hide_set(False)
        o.hide_viewport = False
        if o.type == 'MESH' and o.data.color_attributes:
            idx = o.data.color_attributes.find('Color')
            idx = idx if idx >= 0 else 0
            o.data.color_attributes.active_color_index = idx
            o.data.color_attributes.render_color_index = idx
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]

    bpy.ops.export_scene.gltf(
        filepath=str(out_path),
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_texcoords=True,
        export_normals=True,
        export_vertex_color='ACTIVE',
        export_all_vertex_colors=False,
        export_attributes=False,
        export_draco_mesh_compression_enable=True,
        export_draco_mesh_compression_level=6,
        export_materials='EXPORT',
        export_image_format='NONE',
        export_animations=False,
    )
    for o in objs:
        o.select_set(False)

    nbytes = verify_glb_contract(out_path, name, lod0_budget, lod1_budget)
    info = {
        'name': name,
        'tris0': t0,
        'tris1': t1,
        'kb': round(nbytes / 1024.0, 1),
        'lt22': bs['lt22'],
        'all': bs['all'],
        'mats': [m.name for m in obj.data.materials],
    }
    print(
        f"[v4] {name:16s} LOD0={t0:4d}/{lod0_budget:<4d}  LOD1={t1:4d}/{lod1_budget or 0:<4d}  "
        f"{info['kb']:5.1f}KB  <2.2m={bs['lt22']}",
        flush=True,
    )
    return info


# ---------------------------------------------------------------------------
# Textured Contact Sheet Renderer (M3_houses_sheet.png)
# ---------------------------------------------------------------------------

def draw_text(canvas, x, y, text, color=(255, 255, 255), scale=2, bg=None):
    s = text.upper()
    cw, ch = 6 * scale, 7 * scale
    tw = len(s) * cw
    if bg is not None:
        y0, y1 = max(0, y - 3), min(canvas.shape[0], y + ch + 3)
        x0, x1 = max(0, x - 4), min(canvas.shape[1], x + tw + 4)
        canvas[y0:y1, x0:x1] = (
            canvas[y0:y1, x0:x1].astype(np.float32) * 0.25 + np.array(bg, dtype=np.float32) * 0.75
        ).astype(np.uint8)
    for idx, ch_c in enumerate(s):
        glyph = FONT_5X7.get(ch_c, FONT_5X7[' '])
        gx = x + idx * cw
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits & (1 << (4 - col)):
                    py0, px0 = y + row * scale, gx + col * scale
                    if 0 <= py0 and py0 + scale <= canvas.shape[0] and 0 <= px0 and px0 + scale <= canvas.shape[1]:
                        canvas[py0:py0 + scale, px0:px0 + scale] = color


def _load_topdown_u8(path, w_tgt, h_tgt):
    img = bpy.data.images.load(str(path))
    w, h = img.size[0], img.size[1]
    buf = np.empty(h * w * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    rgb = np.clip(buf.reshape(h, w, 4)[:, :, :3], 0.0, 1.0)[::-1, :, :]
    if w != w_tgt or h != h_tgt:
        ys = np.linspace(0, h - 1, h_tgt).astype(np.int32)
        xs = np.linspace(0, w - 1, w_tgt).astype(np.int32)
        rgb = rgb[np.ix_(ys, xs)]
    return (rgb * 255.0 + 0.5).astype(np.uint8)


def _save_topdown_u8_png(arr_u8, out_path):
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
    img = bpy.data.images.new('m3_sheet', width=w, height=h, alpha=False, float_buffer=False)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(rgba.ravel())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save_render(str(out_path), scene=sc)
    bpy.data.images.remove(img)


def render_model_tile(glb_path, tile_w, tile_h, tmp_png):
    """Import one exported v4 GLB, assign live Poly Haven textures, and render a studio tile."""
    reset_scene()
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    lod0 = [o for o in meshes if '_LOD1' not in o.name]
    lod1 = [o for o in meshes if '_LOD1' in o.name]
    t0 = sum(tri_count(o) for o in lod0)
    t1 = sum(tri_count(o) for o in lod1)
    for o in lod1:
        o.hide_render = True
        o.hide_viewport = True

    # Swap geometry-only ph_* materials for live textured preview shaders
    for o in lod0:
        for i, m in enumerate(o.data.materials):
            if m is None:
                continue
            bname = m.name.split('.')[0]
            if bname in LAYER_META:
                o.data.materials[i] = make_material(bname, textured=True, tex_size=512)

    pts = []
    for o in lod0:
        for c in o.bound_box:
            pts.append(o.matrix_world @ Vector(c))
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    # Frame above ground (z >= -0.05) so sunken bridge piers don't pull the camera down
    mn_vis = Vector((mn.x, mn.y, max(mn.z, -0.05)))
    center = (mn_vis + mx) * 0.5
    size = mx - mn_vis
    radius = max(size.length * 0.5, 0.5)

    bpy.ops.mesh.primitive_plane_add(size=max(30.0, radius * 14.0), location=(center.x, center.y, 0.0))
    floor = bpy.context.active_object
    fmat = bpy.data.materials.new('sand_floor')
    fpbr = next(n for n in fmat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    fpbr.inputs['Base Color'].default_value = (*srgb_to_linear('#C7A778'), 1.0)
    fpbr.inputs['Roughness'].default_value = 0.94
    floor.data.materials.append(fmat)

    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = tile_w
    sc.render.resolution_y = tile_h
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'AgX'
    if hasattr(sc.eevee, 'taa_render_samples'):
        sc.eevee.taa_render_samples = 12

    world = bpy.data.worlds.new('m3_world')
    sc.world = world
    bg = world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs['Color'].default_value = (*srgb_to_linear('#89A8C7'), 1.0)
        bg.inputs['Strength'].default_value = 0.72

    sun_d = bpy.data.lights.new('Sun', 'SUN')
    sun_d.energy = 4.2
    sun_d.color = (1.0, 0.89, 0.72)
    sun = bpy.data.objects.new('Sun', sun_d)
    sun.rotation_euler = (math.radians(58), math.radians(8), math.radians(-38))
    sc.collection.objects.link(sun)

    fill_d = bpy.data.lights.new('Fill', 'SUN')
    fill_d.energy = 1.0
    fill_d.color = (0.78, 0.86, 1.0)
    fill = bpy.data.objects.new('Fill', fill_d)
    fill.rotation_euler = (math.radians(65), 0.0, math.radians(145))
    sc.collection.objects.link(fill)

    cam_d = bpy.data.cameras.new('Cam')
    cam_d.lens = 45.0
    cam_d.clip_start = 0.05
    cam_d.clip_end = max(150.0, radius * 30.0)
    cam = bpy.data.objects.new('Cam', cam_d)
    fit_r = max(radius, size.z * 0.72)
    dist = fit_r * 2.55
    elev = math.radians(10.0) if glb_path.stem == 'river_bridge' else math.radians(20.0)
    # 3/4 view showing front (-Y) and right (+X)
    azim = math.radians(-58.0) if glb_path.stem == 'river_bridge' else math.radians(-30.0)
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
    tile = _load_topdown_u8(tmp_png, tile_w, tile_h)
    kb = glb_path.stat().st_size / 1024.0
    return tile, t0, t1, kb


def render_contact_sheet(model_names, out_path):
    """Render all listed M3 GLBs textured on a warm sand ground into a labelled contact sheet PNG."""
    cols = 5
    rows = math.ceil(len(model_names) / cols)
    tw, th = 420, 310
    pad = 12
    hdr = 52
    W = pad + cols * (tw + pad)
    H = hdr + pad + rows * (th + pad)
    canvas = np.full((H, W, 3), (32, 34, 38), dtype=np.uint8)
    draw_text(canvas, 16, 16, 'M3 POLY HAVEN BUILDINGS & LANDMARKS (15 MODELS, TEXTURED)', (244, 199, 102), scale=2)

    tmp_png = Path('/tmp/m3_tile_tmp.png')
    for idx, name in enumerate(model_names):
        p = OUT_MODELS / f'{name}.glb'
        if not p.exists():
            continue
        tile, t0, t1, kb = render_model_tile(p, tw, th, tmp_png)
        r, c = divmod(idx, cols)
        x0 = pad + c * (tw + pad)
        y0 = hdr + pad + r * (th + pad)
        canvas[y0:y0 + th, x0:x0 + tw] = tile
        draw_text(canvas, x0 + 6, y0 + 6, f'{name}', (251, 241, 220), scale=2, bg=(15, 42, 51))
        lbl = f'L0:{t0}T L1:{t1}T {kb:.0f}KB' if t1 else f'L0:{t0}T {kb:.0f}KB'
        draw_text(canvas, x0 + 6, y0 + th - 22, lbl, (244, 199, 102), scale=2, bg=(15, 42, 51))

    if tmp_png.exists():
        tmp_png.unlink()
    reset_scene()
    _save_topdown_u8_png(canvas, out_path)
    print(f'[v4] Rendered contact sheet -> {out_path}', flush=True)
