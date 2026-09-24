# Shared helpers for the asset scripts (run inside Blender via bl.py).
# Materials are named after the game's PBR sets; the game swaps in real textures by name.
import bpy, bmesh, math, random
from mathutils import Vector

MAT_COLORS = {
    'plaster': (0.62, 0.45, 0.30), 'plaster_light': (0.72, 0.56, 0.40), 'wood': (0.30, 0.20, 0.12),
    'wood_dark': (0.18, 0.12, 0.07), 'clay': (0.55, 0.28, 0.15), 'stone': (0.70, 0.60, 0.45),
    'cloth': (0.60, 0.30, 0.20), 'bark': (0.35, 0.28, 0.2), 'frond': (0.22, 0.32, 0.12), 'dates': (0.5, 0.22, 0.06),
    'lime': (0.86, 0.82, 0.74),
}

def mat(name):
    m = bpy.data.materials.get(name)
    if m and name in MAT_COLORS:                       # keep colours in sync when the table changes
        c = MAT_COLORS[name]; m.diffuse_color = (*c, 1)
        b = m.node_tree.nodes.get('Principled BSDF') if m.use_nodes else None
        if b: b.inputs['Base Color'].default_value = (*c, 1)
    if not m:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get('Principled BSDF')
        c = MAT_COLORS.get(name, (0.5, 0.5, 0.5))
        bsdf.inputs['Base Color'].default_value = (*c, 1)
        bsdf.inputs['Roughness'].default_value = 0.9
        m.diffuse_color = (*c, 1)   # viewport colour
    return m

def clear_collection(name):
    col = bpy.data.collections.get(name)
    if col:
        for o in list(col.objects): bpy.data.objects.remove(o, do_unlink=True)
    else:
        col = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(col)
    return col

def link(obj, col):
    for c in obj.users_collection: c.objects.unlink(obj)
    col.objects.link(obj)
    return obj

def box(name, size, loc, material, col, bevel=0.0, segments=2):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object; o.name = name
    o.scale = size; bpy.ops.object.transform_apply(scale=True)
    if bevel:
        m = o.modifiers.new('bevel', 'BEVEL'); m.width = bevel; m.segments = segments; m.limit_method = 'ANGLE'
    o.data.materials.append(mat(material))
    return link(o, col)

def cylinder(name, r, depth, loc, material, col, rot=(0, 0, 0), verts=12, r2=None):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r if r2 is None else r2, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    o.data.materials.append(mat(material))
    return link(o, col)

def apply_all(o):
    with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o], selected_editable_objects=[o]):
        for m in list(o.modifiers): bpy.ops.object.modifier_apply(modifier=m.name)

def boolean_cut(target, cutter, op='DIFFERENCE'):
    m = target.modifiers.new('cut', 'BOOLEAN'); m.operation = op; m.object = cutter; m.solver = 'EXACT'
    apply_all(target)
    bpy.data.objects.remove(cutter, do_unlink=True)

def lumpy(o, strength=0.03, scale=0.9, levels=3, seed=0):
    """Soft, hand-plastered look: rounded corners, then gentle unevenness."""
    if levels:
        s = o.modifiers.new('soft', 'SUBSURF'); s.levels = levels; s.render_levels = levels; s.subdivision_type = 'CATMULL_CLARK'
    attr = o.data.attributes.get('crease_edge') or o.data.attributes.new('crease_edge', 'FLOAT', 'EDGE')
    for i in range(len(o.data.edges)): attr.data[i].value = 0.82      # keep the box shape, soften the corners
    tex = bpy.data.textures.get(f'lump{seed}') or bpy.data.textures.new(f'lump{seed}', 'CLOUDS')
    tex.noise_scale = scale; tex.noise_depth = 2
    d = o.modifiers.new('uneven', 'DISPLACE'); d.texture = tex; d.strength = strength; d.mid_level = 0.5; d.texture_coords = 'GLOBAL'
    apply_all(o)

def uv_world(o, size=1.0):
    """Box-project UVs in world units (per face, along its dominant axis) so textures
    tile at a consistent real-world scale on every object."""
    me = o.data; bm = bmesh.new(); bm.from_mesh(me)
    uv = bm.loops.layers.uv.verify(); mw = o.matrix_world
    for f in bm.faces:
        n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            p = mw @ l.vert.co
            u, v = ((p.y, p.z), (p.x, p.z), (p.x, p.y))[ax]
            l[uv].uv = (u / size, v / size)
    bm.to_mesh(me); bm.free()

def join(objs, name):
    for x in bpy.context.selected_objects: x.select_set(False)
    for o in objs: apply_all(o); o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.active_object; o.name = name
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return o

def shade_auto(o, angle=40):
    with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o], selected_editable_objects=[o]):
        try: bpy.ops.object.shade_auto_smooth(angle=math.radians(angle))
        except Exception: bpy.ops.object.shade_smooth()

def export_glb(objs, path, draco=True):
    for x in bpy.context.selected_objects: x.select_set(False)
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True,
                              export_yup=True, export_draco_mesh_compression_enable=draco,
                              export_draco_mesh_compression_level=6, export_materials='EXPORT', export_image_format='NONE')

def lod(o, ratio, name):
    c = o.copy(); c.data = o.data.copy(); c.name = name
    for col in o.users_collection: col.objects.link(c)
    m = c.modifiers.new('lod', 'DECIMATE'); m.ratio = ratio
    apply_all(c)
    return c
