# Export each character: rig + body + eyes/brows/lashes/hair + garments, with its four
# animations as named glTF clips (idle, walk, run, talk). Skin textures are reduced to 1K.
import sys, importlib
sys.path.insert(0, '/var/www/html/old/3d-quranic/blender')
import bpy
OUT = '/var/www/html/old/3d-quranic/public/models/'

def prepare(key):
    rig = bpy.data.objects[key + '_rig']
    meshes = [o for o in rig.children_recursive if o.type == 'MESH']
    for o in meshes:                                   # bake body-shape targets into the mesh
        if o.data.shape_keys:
            with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o], selected_editable_objects=[o]):
                bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
        for m in o.data.materials:
            for n in (m.node_tree.nodes if m and m.use_nodes else []):
                if n.type == 'TEX_IMAGE' and n.image and max(n.image.size) > 1024:
                    n.image.scale(1024, 1024); n.image.pack()
    # one NLA track per clip so the exporter writes exactly this rig's four animations
    ad = rig.animation_data_create(); ad.action = None
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    for clip in ('idle', 'walk', 'run', 'talk'):
        act = bpy.data.actions[f'{key}_rig_{clip}']
        tr = ad.nla_tracks.new(); tr.name = clip
        st = tr.strips.new(clip, 1, act); st.name = clip
    return rig, meshes

def export(key):
    rig, meshes = prepare(key)
    x0 = rig.location.x; rig.location.x = 0
    for x in bpy.context.selected_objects: x.select_set(False)
    for o in [rig] + meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=OUT + key + '.glb', export_format='GLB', use_selection=True, export_apply=True,
                              export_yup=True, export_skins=True, export_animations=True, export_animation_mode='NLA_TRACKS',
                              export_morph=False, export_image_format='AUTO', export_jpeg_quality=85,
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
    rig.location.x = x0
    import os
    return round(os.path.getsize(OUT + key + '.glb') / 1e6, 2)

print({k: export(k) for k in ('player', 'farmer', 'trader', 'grandma')})
