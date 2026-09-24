# Preview renders: turnaround per character, cast line-up, faces close-up.
import bpy, math
from mathutils import Vector
import toon_lib as T

ORDER = ['player', 'farmer', 'grandma_zainab', 'grandma', 'trader']
SLOT = {k: (i - 2) * 1.0 for i, k in enumerate(ORDER)}

def rigs():
    return {k: bpy.data.objects.get(k + '_rig') for k in ORDER if bpy.data.objects.get(k + '_rig')}

def layout():
    for k, r in rigs().items(): r.location.x = SLOT[k] * 1.2

def pose(rig, clip, frame):
    ad = rig.animation_data
    act = next((a for a in bpy.data.actions if a.get('clip') == clip and a.name.startswith(rig.name[:-4] + '|')), None)
    if act: ad.action = act
    bpy.context.scene.frame_set(frame)

def solo(key):
    for c in bpy.data.collections:
        if c.name.startswith('char_'): c.hide_render = c.name != 'char_' + key

def show_all():
    for c in bpy.data.collections:
        if c.name.startswith('char_'): c.hide_render = False

def bench(on, x=0):
    o = bpy.data.objects.get('_prev_bench')
    if o: bpy.data.objects.remove(o, do_unlink=True)
    if not on: return
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0.25, 0.225)); o = bpy.context.active_object; o.name = '_prev_bench'
    o.scale = (1.0, 0.5, 0.45)
    o.data.materials.append(T.toon_mat('toon_prev_bench', '#D9A066'))

def turnaround(key, clip=None, frame=10):
    T.all_mode('cel')
    cam = T.render_setup((640, 960)); solo(key)
    rig = rigs()[key]; x0 = rig.location.x; rig.location.x = 0
    clip = clip or ('sit' if key == 'grandma_zainab' else 'idle')
    pose(rig, clip, frame); bench(key == 'grandma_zainab')
    h = max((rig.matrix_world @ Vector(b)).z for b in [(0, 0, 0)]) or 1
    top = max(v.co.z for v in bpy.data.objects[key].data.vertices)
    sun = bpy.data.objects['_prev_sun']
    paths = []
    for i, yaw in enumerate((0, 35, 90)):
        T.frame_camera(cam, (0, 0, top * 0.5), top * 1.12, yaw=math.radians(yaw), elev=math.radians(4))
        sun.rotation_euler = (math.radians(50), 0, math.radians(-35 + yaw))
        p = T.PREV + f'_{key}_{i}.png'; T.render_to(p); paths.append(p)
    # face close-up
    head = rig.pose.bones['head']; hp = rig.matrix_world @ head.head
    T.frame_camera(cam, (0, 0, hp.z + top * 0.07), top * 0.26, yaw=math.radians(12), elev=math.radians(3))
    sun.rotation_euler = (math.radians(50), 0, math.radians(-23))
    p = T.PREV + f'_{key}_3.png'; T.render_to(p); paths.append(p)
    T.stitch(paths, T.PREV + f'{key}_turnaround.png')
    rig.location.x = x0; bench(False); show_all()

def lineup():
    T.all_mode('cel')
    cam = T.render_setup((2400, 1000)); show_all()
    R = rigs(); xs = {}
    x = -2.4
    for k in ORDER:
        r = R.get(k)
        if not r: continue
        r.location.x = x; xs[k] = x
        pose(r, 'sit' if k == 'grandma_zainab' else 'idle', 10)
        x += 1.2 if k != 'grandma_zainab' else 1.2
    bench(True, xs.get('grandma_zainab', 0))
    T.frame_camera(cam, (0, 0, 0.95), 2.2, yaw=math.radians(10), elev=math.radians(4))
    bpy.data.objects['_prev_sun'].rotation_euler = (math.radians(50), 0, math.radians(-25))
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 2600, 1000
    T.frame_camera(cam, (0, 0, 0.95), 6.2, yaw=math.radians(8), elev=math.radians(3))
    T.render_to(T.PREV + 'cast_lineup.png')
    bench(False)

def faces():
    T.all_mode('cel')
    cam = T.render_setup((560, 640)); paths = []
    for k in ORDER:
        r = rigs().get(k)
        if not r: continue
        solo(k); x0 = r.location.x; r.location.x = 0
        pose(r, 'sit' if k == 'grandma_zainab' else 'idle', 10)
        hp = r.matrix_world @ r.pose.bones['head'].head
        T.frame_camera(cam, (0, 0, hp.z + 0.11), 0.42, yaw=math.radians(14), elev=math.radians(3))
        bpy.data.objects['_prev_sun'].rotation_euler = (math.radians(50), 0, math.radians(-20))
        p = T.PREV + f'_face_{k}.png'; T.render_to(p); paths.append(p)
        r.location.x = x0
    show_all()
    T.stitch(paths, T.PREV + 'cast_faces.png')

def poses():
    T.all_mode('cel')
    cam = T.render_setup((480, 760)); paths = []
    for k in ORDER:
        r = rigs().get(k)
        if not r: continue
        solo(k); x0 = r.location.x; r.location.x = 0
        top = max(v.co.z for v in bpy.data.objects[k].data.vertices)
        for clip, fr, yaw in (('walk', 7, 60), ('talk', 17, 20), ('sit_talk', 17, 20), ('run', 5, 70)):
            if not any(a.get('clip') == clip and a.name.startswith(k + '|') for a in bpy.data.actions): continue
            pose(r, clip, fr); bench(clip.startswith('sit'))
            T.frame_camera(cam, (0, 0, top * 0.5), top * 1.15, yaw=math.radians(yaw), elev=math.radians(4))
            bpy.data.objects['_prev_sun'].rotation_euler = (math.radians(50), 0, math.radians(-35 + yaw))
            p = T.PREV + f'_pose_{k}_{clip}.png'; T.render_to(p); paths.append(p)
        bench(False); r.location.x = x0
    show_all()
    T.stitch(paths, T.PREV + '_poses_check.png', cols=5)
