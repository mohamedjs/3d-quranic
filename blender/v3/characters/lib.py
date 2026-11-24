"""Shared Blender utilities: scene reset, cel/glTF materials, outlines, export, stats."""
import math
import os
import tempfile
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix

ROOT = '/var/www/html/old/3d-quranic/'
HERE = ROOT + 'blender/v3/characters/'
PREV = ROOT + 'blender/v3/previews/'
MODELS = ROOT + 'public/models/'
BLEND = HERE + 'characters.blend'

INK = '#2B1A10'
DEFAULT_SHADOW = '#B9959A'


def hex_rgb(h):
    """Convert '#RRGGBB' hex string to (r, g, b) floats in [0, 1] sRGB."""
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def lin(c):
    """Convert sRGB (hex string or 3-tuple) to linear RGB for Blender shaders."""
    if isinstance(c, str):
        c = hex_rgb(c)
    return tuple(
        x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
        for x in c[:3]
    )


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
    bpy.context.scene.render.fps = 24


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
    # Save via temporary PNG and pack so glTF export and .blend retain lossless PNG without extra repo files
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


def check_pattern_image(name, base_hex, ink_hex, accent_hex=None, size=256, cells=8):
    """Generate a crisp woven shemagh/scarf check pattern as a packed 256px PNG."""
    y, x = np.mgrid[0:size, 0:size]
    cell = size / cells
    u = (x % cell) / cell
    v = (y % cell) / cell
    cx = (x // cell).astype(int)
    cy = (y // cell).astype(int)

    base = np.array(hex_rgb(base_hex), dtype=np.float32)
    ink = np.array(hex_rgb(ink_hex), dtype=np.float32)
    img = np.ones((size, size, 3), dtype=np.float32) * base

    # Classic houndstooth/shemagh weave: double thin warp/weft bands + alternating solid woven diamonds
    band_u = (np.abs(u - 0.5) < 0.085) | (np.abs(u - 0.30) < 0.032) | (np.abs(u - 0.70) < 0.032)
    band_v = (np.abs(v - 0.5) < 0.085) | (np.abs(v - 0.30) < 0.032) | (np.abs(v - 0.70) < 0.032)
    diamond = ((cx + cy) % 2 == 0) & ((np.abs(u - 0.5) + np.abs(v - 0.5)) < 0.24)
    # Soft woven cross-hatch at intersections
    mask = band_u | band_v | diamond
    img = np.where(mask[..., None], ink, img)

    if accent_hex:
        acc = np.array(hex_rgb(accent_hex), dtype=np.float32)
        dot = ((cx + cy) % 2 == 1) & ((np.abs(u - 0.5) + np.abs(v - 0.5)) < 0.09)
        img = np.where(dot[..., None], acc, img)

    return pack_image(name, img)


# ------------------------------------------------------------------ materials
def toon_mat(
    name,
    color='#808080',
    image=None,
    shadow=DEFAULT_SHADOW,
    rim=0.20,
    bands=(0.10, 0.42),
    double_sided=False,
):
    """Create dual-branch material: plain Principled (glTF) + 3-band cel ramp with rim (EEVEE)."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = not double_sided
    nt = mat.node_tree
    nt.nodes.clear()

    def node(bl_type, x, y, nname=None):
        n = nt.nodes.new(bl_type)
        n.location = (x, y)
        if nname:
            n.name = nname
        return n

    out = node('ShaderNodeOutputMaterial', 960, 0, 'out')
    pr = node('ShaderNodeBsdfPrincipled', 520, 300, 'gltf')
    pr.inputs['Roughness'].default_value = 0.88
    if 'Specular IOR Level' in pr.inputs:
        pr.inputs['Specular IOR Level'].default_value = 0.12

    if image is not None:
        tx = node('ShaderNodeTexImage', 0, 300, 'tex')
        tx.image = image
        tx.interpolation = 'Linear'
        base = tx.outputs['Color']
    else:
        rgb = node('ShaderNodeRGB', 0, 300, 'base')
        rgb.outputs[0].default_value = (*lin(color), 1.0)
        base = rgb.outputs[0]

    nt.links.new(base, pr.inputs['Base Color'])

    # Cel branch for EEVEE previews matching Three.js toon.js
    df = node('ShaderNodeBsdfDiffuse', 0, -120)
    s2r = node('ShaderNodeShaderToRGB', 190, -120)
    ramp = node('ShaderNodeValToRGB', 380, -120)
    cr = ramp.color_ramp
    cr.interpolation = 'CONSTANT'
    sh = lin(shadow)
    cr.elements[0].position = 0.0
    cr.elements[0].color = (sh[0] * 0.84, sh[1] * 0.84, sh[2] * 0.86, 1.0)
    cr.elements[1].position = bands[0]
    cr.elements[1].color = (sh[0], sh[1], sh[2], 1.0)
    lit = cr.elements.new(bands[1])
    lit.color = (1.0, 0.98, 0.94, 1.0)

    mul = node('ShaderNodeMix', 620, -120)
    mul.data_type = 'RGBA'
    mul.blend_type = 'MULTIPLY'
    mul.inputs['Factor'].default_value = 1.0
    nt.links.new(df.outputs[0], s2r.inputs[0])
    nt.links.new(s2r.outputs['Color'], ramp.inputs['Fac'])
    nt.links.new(base, mul.inputs[6])
    nt.links.new(ramp.outputs['Color'], mul.inputs[7])

    # Soft golden rim highlight
    lw = node('ShaderNodeLayerWeight', 380, -360)
    lw.inputs['Blend'].default_value = 0.28
    rr = node('ShaderNodeMath', 560, -360)
    rr.operation = 'GREATER_THAN'
    rr.inputs[1].default_value = 0.70
    rs = node('ShaderNodeMath', 710, -360)
    rs.operation = 'MULTIPLY'
    rs.inputs[1].default_value = rim
    nt.links.new(lw.outputs['Facing'], rr.inputs[0])
    nt.links.new(rr.outputs[0], rs.inputs[0])

    add = node('ShaderNodeMix', 770, -140)
    add.data_type = 'RGBA'
    add.blend_type = 'ADD'
    add.inputs[7].default_value = (1.0, 0.87, 0.64, 1.0)
    nt.links.new(rs.outputs[0], add.inputs['Factor'])
    nt.links.new(mul.outputs[2], add.inputs[6])

    em = node('ShaderNodeEmission', 850, -140, 'cel')
    nt.links.new(add.outputs[2], em.inputs['Color'])

    mat.diffuse_color = (*lin(color if image is None else '#d9a383'), 1.0)
    set_mat_mode(mat, 'cel')
    return mat


def outline_mat():
    """Return the shared ink outline material named exactly 'outline'."""
    mat = bpy.data.materials.get('outline') or bpy.data.materials.new('outline')
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    out.name = 'out'
    pr = nt.nodes.new('ShaderNodeBsdfPrincipled')
    pr.name = 'gltf'
    pr.inputs['Base Color'].default_value = (*lin(INK), 1.0)
    pr.inputs['Roughness'].default_value = 1.0
    em = nt.nodes.new('ShaderNodeEmission')
    em.name = 'cel'
    em.inputs['Color'].default_value = (*lin(INK), 1.0)
    mat.use_backface_culling = True
    mat.diffuse_color = (*lin(INK), 1.0)
    set_mat_mode(mat, 'cel')
    return mat


def set_mat_mode(mat, mode):
    """Switch material output between 'cel' (EEVEE preview) and 'gltf' (Principled export)."""
    if not mat.use_nodes:
        return
    nt = mat.node_tree
    out = nt.nodes.get('out')
    src = nt.nodes.get('cel' if mode == 'cel' else 'gltf')
    if out and src:
        nt.links.new(src.outputs[0], out.inputs['Surface'])


def set_all_mat_mode(mode):
    """Switch every dual-branch material in the scene to 'cel' or 'gltf'."""
    for mat in bpy.data.materials:
        if mat.use_nodes and mat.node_tree.nodes.get('gltf'):
            set_mat_mode(mat, mode)


# ------------------------------------------------------------------ mesh helpers
def new_obj(name, mesh, col):
    """Create a mesh object linked to col, replacing any existing object of same name."""
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    return obj


def bm_to_obj(bm, name, col, mat=None, smooth=True, ensure_uv=True):
    """Convert bmesh to a Blender object, guaranteeing a UVMap for Lite mergeSkinned."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if ensure_uv and not bm.loops.layers.uv:
        uv_layer = bm.loops.layers.uv.new('UVMap')
        for f in bm.faces:
            for loop in f.loops:
                loop[uv_layer].uv = (0.0, 0.0)

    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if ensure_uv and me.uv_layers:
        me.uv_layers[0].name = 'UVMap'
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    obj = new_obj(name, me, col)
    if mat is not None:
        me.materials.append(mat)
    return obj


def ensure_uv_layer(obj):
    """Ensure mesh has a primary UV layer named 'UVMap'."""
    me = obj.data
    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')
    else:
        me.uv_layers[0].name = 'UVMap'


def apply_modifiers(obj):
    """Apply all non-Armature modifiers on obj."""
    with bpy.context.temp_override(
        object=obj,
        active_object=obj,
        selected_objects=[obj],
        selected_editable_objects=[obj],
    ):
        for m in list(obj.modifiers):
            if m.type != 'ARMATURE':
                bpy.ops.object.modifier_apply(modifier=m.name)


def shade_smooth(obj):
    """Mark all faces smooth."""
    for p in obj.data.polygons:
        p.use_smooth = True


def uv_cylindrical(obj, center=(0.0, 0.0), scale_u=1.0, scale_v=1.0):
    """Apply clean cylindrical UVs around Z axis (great for woven textiles/shemagh)."""
    me = obj.data
    ensure_uv_layer(obj)
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    cx, cy = center
    for f in bm.faces:
        angs = []
        for loop in f.loops:
            p = loop.vert.co
            a = math.atan2(p.y - cy, p.x - cx)
            angs.append(a)
        # Avoid seam wrap jump within a single face
        if max(angs) - min(angs) > math.pi:
            angs = [a + math.tau if a < 0 else a for a in angs]
        for loop, a in zip(f.loops, angs):
            p = loop.vert.co
            loop[uv].uv = ((a / math.tau) * scale_u, p.z * scale_v)
    bm.to_mesh(me)
    bm.free()


def uv_planar_drape(obj, scale=6.0):
    """Apply smooth surface-flow UVs from spherical/planar coordinates for draped cloth."""
    me = obj.data
    ensure_uv_layer(obj)
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    for f in bm.faces:
        for loop in f.loops:
            p = loop.vert.co
            # Smoothly project horizontal arc length + vertical drop
            r_xy = math.hypot(p.x, p.y)
            arc = math.atan2(p.x, -p.y) * max(r_xy, 0.12)
            loop[uv].uv = (arc * scale, p.z * scale)
    bm.to_mesh(me)
    bm.free()


def loft_rings(bm, rings, closed_u=True, cap_start=False, cap_end=False):
    """Connect a list of vertex loops (each length N) into a smooth quad skin."""
    n = len(rings[0])
    for r0, r1 in zip(rings, rings[1:]):
        count = n if closed_u else n - 1
        for k in range(count):
            kn = (k + 1) % n
            bm.faces.new((r0[k], r0[kn], r1[kn], r1[k]))
    if cap_start and closed_u:
        c = sum((v.co for v in rings[0]), Vector()) / n
        cv = bm.verts.new(c)
        for k in range(n):
            bm.faces.new((rings[0][(k + 1) % n], rings[0][k], cv))
    if cap_end and closed_u:
        c = sum((v.co for v in rings[-1]), Vector()) / n
        cv = bm.verts.new(c)
        for k in range(n):
            bm.faces.new((rings[-1][k], rings[-1][(k + 1) % n], cv))


def add_tube(bm, pts, radius, segs=10, flat=1.0, closed_caps=True, ref_up=None):
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

    # Initial frame
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

    loft_rings(bm, rings, closed_u=True, cap_start=closed_caps, cap_end=closed_caps)
    return rings


def add_ring_torus(bm, center, rx, ry, z, tube_rx, tube_rz=None, tilt=0.0, phase=0.0, segs=28, tsegs=8, bulge=0.0):
    """Add a closed organic wrapped torus ring (used for turban folds and agal)."""
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
    for i in range(segs):
        r0, r1 = rings[i], rings[(i + 1) % segs]
        for k in range(tsegs):
            kn = (k + 1) % tsegs
            bm.faces.new((r0[k], r0[kn], r1[kn], r1[k]))
    return rings


def smoothstep(e0, e1, x):
    """Smooth Hermite interpolation in [0, 1]."""
    if abs(e1 - e0) < 1e-8:
        return 1.0 if x >= e1 else 0.0
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3.0 - 2.0 * t)


# ------------------------------------------------------------------ join & outline
def join_objects(objs, name, col=None):
    """Join a list of skinned mesh objects into one object named `name`."""
    for obj in objs:
        ensure_uv_layer(obj)
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
    if col and res.name not in col.objects:
        col.objects.link(res)
    return res


def build_outline_part(obj, thickness, col):
    """Create a flipped-normal inverted hull copy of one skinned mesh part."""
    me = obj.data.copy()
    me.name = obj.name + '_ol'
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * thickness
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()

    me.materials.clear()
    me.materials.append(outline_mat())
    for p in me.polygons:
        p.material_index = 0
        p.use_smooth = True

    ol = new_obj(obj.name + '_ol', me, col)
    ol.matrix_world = obj.matrix_world.copy()
    for vg in obj.vertex_groups:
        ol.vertex_groups.new(name=vg.name)
    if obj.parent:
        ol.parent = obj.parent
        ol.matrix_parent_inverse = obj.matrix_parent_inverse.copy()
    for m in obj.modifiers:
        if m.type == 'ARMATURE':
            am = ol.modifiers.new('rig', 'ARMATURE')
            am.object = m.object
    return ol


def build_combined_outline(parts_with_thick, name, col, rig):
    """Build per-part inverted hulls with custom thickness and join into `<name>_outline`."""
    hulls = []
    for obj, thick in parts_with_thick:
        if thick > 0.0 and len(obj.data.polygons) > 0:
            hulls.append(build_outline_part(obj, thick, col))
    if not hulls:
        return None
    if len(hulls) == 1:
        ol = hulls[0]
        ol.name = name
        ol.data.name = name
    else:
        ol = join_objects(hulls, name, col)
    for m in list(ol.modifiers):
        if m.type == 'ARMATURE':
            m.object = rig
    return ol


def tri_count(obj):
    """Count triangles in a Blender mesh object."""
    if obj is None or obj.type != 'MESH':
        return 0
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def bone_count(rig):
    """Count deform bones in an armature."""
    return sum(1 for b in rig.data.bones if b.use_deform)


# ------------------------------------------------------------------ export
def export_glb(info):
    """Export one character (rig + mesh + outline) as Draco-6 Y-up GLB."""
    os.makedirs(MODELS, exist_ok=True)
    set_all_mat_mode('gltf')

    rig = info['rig']
    mesh = info['mesh']
    outline = info['outline']

    # Remember and zero rig location/pose cleanly for export
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
    export_objs = [o for o in (rig, mesh, outline) if o is not None]
    for o in export_objs:
        o.hide_set(False)
        o.hide_viewport = False
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig

    path = MODELS + info['key'] + '.glb'
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

    # Restore preview state
    rig.location = loc0
    if rig.animation_data and act0:
        rig.animation_data.action = act0
    set_all_mat_mode('cel')

    size_kb = round(os.path.getsize(path) / 1024.0, 1)
    info['glb'] = path
    info['glb_kb'] = size_kb
    return path, size_kb
