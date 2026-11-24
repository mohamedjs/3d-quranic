"""Shared headless Blender v3 pipeline helpers for Environment v3 assets.

Provides deterministic scene reset, UV packing, vertex-AO baking, spherical normal
transfer (for Ghibli foliage cards), LOD1 decimation, Draco-6 GLB export, and budget
reporting. All paths resolve from the current workspace root so worktrees stay isolated.
"""
from pathlib import Path
import json
import math
import os

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

ROOT = Path(__file__).resolve().parents[3]
OUT_MODELS = ROOT / 'public' / 'models' / 'env'
OUT_TEX = ROOT / 'public' / 'textures' / 'env'
V3_DIR = ROOT / 'blender' / 'v3'
V3_ENV = V3_DIR / 'env'
PREVIEWS = V3_DIR / 'previews'


def ensure_dirs():
    for d in (OUT_MODELS, PREVIEWS):
        d.mkdir(parents=True, exist_ok=True)


def reset_scene():
    """Start from a completely empty Blender scene with deterministic settings."""
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


def make_material(name, base_color=(0.8, 0.7, 0.55), roughness=0.92, use_vcol=True):
    """Create a clean Principled BSDF material suitable for glTF export."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    pbr = nt.nodes.new('ShaderNodeBsdfPrincipled')
    pbr.inputs['Roughness'].default_value = roughness
    if 'Specular IOR Level' in pbr.inputs:
        pbr.inputs['Specular IOR Level'].default_value = 0.2
    if use_vcol:
        vc = nt.nodes.new('ShaderNodeVertexColor')
        vc.layer_name = 'Color'
        nt.links.new(vc.outputs['Color'], pbr.inputs['Base Color'])
    else:
        pbr.inputs['Base Color'].default_value = (*base_color, 1.0)
    nt.links.new(pbr.outputs['BSDF'], out.inputs['Surface'])
    mat.diffuse_color = (*base_color, 1.0)
    return mat


def make_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
    else:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    return col


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def pack_uvs(obj, angle_limit=66.0, island_margin=0.02):
    """Smart-project and pack UVs for an object lacking explicit UVs."""
    me = obj.data
    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle_limit), island_margin=island_margin)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)


def bake_vertex_ao(obj, strength=0.35, min_val=0.55):
    """Fast geometric crease + height AO baked directly into the mesh's Color attribute."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.normal_update()
    z_vals = [v.co.z for v in bm.verts]
    z_min, z_max = (min(z_vals), max(z_vals)) if z_vals else (0.0, 1.0)
    z_span = max(z_max - z_min, 1e-4)

    ao_per_vert = []
    for v in bm.verts:
        # Concavity proxy from neighbor directions relative to vertex normal
        concav = 0.0
        n_edges = len(v.link_edges)
        if n_edges:
            for e in v.link_edges:
                other = e.other_vert(v)
                d = other.co - v.co
                ln = d.length
                if ln > 1e-5:
                    concav += max(0.0, d.dot(v.normal) / ln)
            concav /= n_edges
        ground_occ = max(0.0, 1.0 - (v.co.z - z_min) / min(z_span, 1.2)) * 0.35
        occ = max(min_val, 1.0 - strength * (concav * 1.4 + ground_occ))
        ao_per_vert.append(occ)
    bm.free()

    col_attr = me.color_attributes.get('Color')
    if col_attr is None:
        col_attr = me.color_attributes.new(name='Color', type='BYTE_COLOR', domain='POINT')
        for i, occ in enumerate(ao_per_vert):
            col_attr.data[i].color = (occ, occ, occ, 1.0)
    elif col_attr.domain == 'POINT':
        for i, occ in enumerate(ao_per_vert):
            c = col_attr.data[i].color
            col_attr.data[i].color = (c[0] * occ, c[1] * occ, c[2] * occ, c[3])
    else:
        for poly in me.polygons:
            for li in poly.loop_indices:
                vi = me.loops[li].vertex_index
                occ = ao_per_vert[vi]
                c = col_attr.data[li].color
                col_attr.data[li].color = (c[0] * occ, c[1] * occ, c[2] * occ, c[3])


def transfer_spherical_normals(obj, center=None, blend=0.85):
    """Blend mesh normals toward an outward sphere from `center` for soft Ghibli foliage."""
    me = obj.data
    if center is None:
        pts = [v.co for v in me.vertices]
        c = sum(pts, Vector((0, 0, 0))) / max(len(pts), 1)
    else:
        c = Vector(center)
    norms = []
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index]
            out = v.co - c
            if out.length > 1e-5:
                out.normalize()
            else:
                out = Vector((0, 0, 1))
            n = v.normal.lerp(out, blend).normalized()
            norms.append(n)
    me.normals_split_custom_set(norms)


def make_lod1(obj, ratio=0.4, name=None):
    """Create a decimated LOD1 sibling mesh without mutating the source object."""
    copy_obj = obj.copy()
    copy_obj.data = obj.data.copy()
    copy_obj.name = name or f'{obj.name}_LOD1'
    for col in obj.users_collection:
        col.objects.link(copy_obj)
    mod = copy_obj.modifiers.new('lod', 'DECIMATE')
    mod.ratio = ratio
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


def export_glb(objs, path, draco_level=6):
    """Export selected objects to a Y-up Draco-compressed GLB and return file size in bytes."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.hide_set(False)
        o.hide_viewport = False
        if o.type == 'MESH' and o.data.color_attributes:
            idx = o.data.color_attributes.find('Color')
            if idx < 0:
                idx = 0
            o.data.color_attributes.active_color_index = idx
            o.data.color_attributes.render_color_index = idx
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(
        filepath=str(path),
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
        export_draco_mesh_compression_level=draco_level,
        export_materials='EXPORT',
        export_image_format='NONE',
        export_animations=False,
    )
    for o in objs:
        o.select_set(False)
    return os.path.getsize(path)


def save_report(entries, name='_report_env_v3.json'):
    V3_ENV.mkdir(parents=True, exist_ok=True)
    out = V3_ENV / name
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2)
    return out
