# Entry point: builds the anime cast, saves characters.blend, exports public/models/*.glb and
# renders previews.   python3 blender/v2/bg.py blender/v2/characters/build_all.py cast
# To rebuild only some: set KEYS below (or import build_all and call main(['player'])).
import sys, os, importlib, math
HERE = '/var/www/html/old/3d-quranic/blender/v2/characters/'
sys.path.insert(0, HERE)
import bpy
for m in ('toon_lib', 'head', 'body', 'garments', 'anim', 'cast', 'preview'):
    if m in sys.modules: importlib.reload(sys.modules[m])
import toon_lib as T, cast, preview

BLEND = HERE + 'characters.blend'
ORDER = ['player', 'farmer', 'grandma_zainab', 'grandma', 'trader']

def start(fresh):
    if not fresh and os.path.exists(BLEND):
        bpy.ops.wm.open_mainfile(filepath=BLEND)
    else:
        for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
        for c in list(bpy.data.collections): bpy.data.collections.remove(c)
        for a in list(bpy.data.actions): bpy.data.actions.remove(a)
        for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images):
            for x in list(coll):
                if x.users == 0: coll.remove(x)

def export(info):
    T.all_mode('gltf')
    rig, mesh, ol = info['rig'], info['mesh'], info['outline']
    for o in bpy.context.selected_objects: o.select_set(False)
    for o in (rig, mesh, ol): o.select_set(True); o.hide_set(False)
    bpy.context.view_layer.objects.active = rig
    path = T.MODELS + info['key'] + '.glb'
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True,
                              export_apply=False, export_skins=True, export_animations=True,
                              export_animation_mode='NLA_TRACKS', export_optimize_animation_size=True,
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
                              export_image_format='AUTO', export_materials='EXPORT', export_morph=False)
    T.all_mode('cel')
    return path, os.path.getsize(path)

def main(keys=None, fresh=False, do_export=True, previews=True):
    keys = keys or [k for k in ORDER if k in cast.CAST]
    start(fresh)
    out = []
    for k in keys:
        info = cast.build(k)
        rig = info['rig']
        if do_export:
            p, size = export(info); info['glb'] = p; info['kb'] = round(size / 1024)
        print('BUILT', k, 'tris', info['tris'], '+ outline', info['tris_outline'], 'glb KB', info.get('kb'), flush=True)
        out.append(info)
    preview.layout()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    if previews:
        for k in keys: preview.turnaround(k)
        preview.lineup(); preview.faces(); preview.poses()
        preview.layout()
    return out

if __name__ == '__main__':
    main(globals().get('KEYS'), fresh=globals().get('FRESH', False))
