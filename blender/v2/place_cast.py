# Drops the five character GLBs into the `cast` collection of village_v2.blend at their game
# positions (Blender x, y = game x, -z), poses them, saves and renders previews/village_cast.png.
#   python3 blender/v2/bg.py blender/v2/place_cast.py place_cast
import sys; sys.path.insert(0, '/var/www/html/old/3d-quranic/blender/v2/env')
import bpy, math
import gameport as G
ROOT = '/var/www/html/old/3d-quranic/'
bpy.ops.wm.open_mainfile(filepath=ROOT + 'blender/v2/village_v2.blend')
cast = bpy.data.collections.get('cast')
if cast is None:
    cast = bpy.data.collections.new('cast'); bpy.context.scene.collection.children.link(cast)
for o in list(cast.all_objects): bpy.data.objects.remove(o, do_unlink=True)
print('blender', bpy.app.version_string, flush=True)

def look_at(x, z, tx, tz): return math.atan2(tx - x, tz - z)
CAST = [   # glb, game x, game z, facing (game yaw), clip
    ('grandma_zainab', -6.75, 24.7, math.pi / 2, 'sit'),
    ('farmer', -6.0, 26.2, 1.92, 'idle'),
    ('player', -4.1, 25.05, look_at(-4.1, 25.05, -6.4, 25.45), 'idle'),
    ('grandma', -1.7, 33.5, math.pi, 'idle'),         # Amina walking down the north road
    ('trader', 1.7, 32.2, -math.pi / 2 - 0.3, 'idle'),  # Hamdan greeting her
]
for name, x, z, yaw, clip in CAST:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=ROOT + f'public/models/{name}.glb')
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new('cast_' + name, None); cast.objects.link(root)
    print('  new', [(o.name, o.type) for o in new], flush=True)
    root.location = (x, -z, G.height(x, z)); root.rotation_euler = (0, 0, yaw)
    for o in new:
        for c in list(o.users_collection): c.objects.unlink(o)
        cast.objects.link(o)
        if o.parent is None: o.parent = root
    arm = next((o for o in new if o.type == 'ARMATURE'), None)
    for o in [o for o in new if o is not arm and o.name.split('.')[0] not in (name, name + '_outline')]:
        print('  drop helper', o.name, o.type, flush=True); new.remove(o); bpy.data.objects.remove(o, do_unlink=True)
    acts = [a for a in bpy.data.actions if a.name.split('|')[-1].split('_')[0] == clip or a.name == clip or a.name.startswith(clip + '_') or a.name.endswith('|' + clip)]
    # prefer an action created by this import (names get .001 suffixes)
    pick = None
    for a in bpy.data.actions:
        base = a.name.split('|')[-1]
        if base.split('.')[0] in (clip,) and a.users == 0 or (arm and arm.animation_data and arm.animation_data.action == a): pass
    cands = [a for a in bpy.data.actions if a.name.split('|')[-1].split('.')[0] == clip]
    if arm and cands:
        arm.animation_data_create()
        # last created candidate belongs to this import
        pick = cands[-1]
        arm.animation_data.action = pick
        try:
            if hasattr(arm.animation_data, 'action_slot') and pick.slots: arm.animation_data.action_slot = pick.slots[0]
        except Exception as e: print('slot', e)
        # hold the first frame of the clip
    print('placed', name, 'objs', len(new), 'arm', arm and arm.name, 'action', pick and pick.name, [a.name for a in bpy.data.actions][-8:], flush=True)
sc = bpy.context.scene
sc.frame_set(1)
cam = bpy.data.objects.get('ShotCam')
if cam: sc.camera = cam
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.render.filepath = ROOT + 'blender/v2/previews/village_cast.png'; sc.render.image_settings.file_format = 'PNG'
bpy.ops.wm.save_as_mainfile(filepath=ROOT + 'blender/v2/village_v2.blend')
print('SAVED', flush=True)
bpy.ops.render.render(write_still=True)
print('RENDERED', flush=True)
