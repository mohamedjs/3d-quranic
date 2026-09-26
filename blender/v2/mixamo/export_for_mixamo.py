# Export each anime character as an UNRIGGED mesh in its rest pose (FBX + embedded textures)
# for Mixamo's auto-rigger: blender/v2/mixamo/upload/<key>.fbx
import bpy
SRC = '/var/www/html/old/3d-quranic/blender/v2/characters/characters.blend'
OUT = '/var/www/html/old/3d-quranic/blender/v2/mixamo/upload/'
bpy.ops.wm.open_mainfile(filepath=SRC)
for key in ('player', 'farmer', 'grandma', 'trader'):
    rig = bpy.data.objects[key + '_rig']; rig.data.pose_position = 'REST'
    src = bpy.data.objects[key]
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(src.evaluated_get(dg))
    o = bpy.data.objects.new(key + '_mixamo', me); bpy.context.scene.collection.objects.link(o)
    o.matrix_world = src.matrix_world.copy()
    for x in bpy.context.selected_objects: x.select_set(False)
    o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.export_scene.fbx(filepath=OUT + key + '.fbx', use_selection=True, object_types={'MESH'},
                             path_mode='COPY', embed_textures=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', add_leaf_bones=False, mesh_smooth_type='FACE')
    print('exported', key, len(me.polygons), 'faces, height', round(o.dimensions.z, 2))
