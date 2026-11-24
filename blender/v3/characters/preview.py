"""EEVEE cel-shaded preview renders: 4-view turnarounds, face close-ups, full cast lineup, key poses."""
import math
import os
import bpy
import numpy as np
from mathutils import Vector

import lib as L
from cast import ORDER


def _rigs():
    return {k: bpy.data.objects.get(k + '_rig') for k in ORDER if bpy.data.objects.get(k + '_rig')}


def _save_state():
    """Snapshot rig locations and active actions so preview never alters exported object state."""
    state = {}
    for k, rig in _rigs().items():
        act = rig.animation_data.action if rig.animation_data else None
        state[k] = (rig.location.copy(), act)
    return state


def _restore_state(state):
    for k, (loc, act) in state.items():
        rig = bpy.data.objects.get(k + '_rig')
        if not rig:
            continue
        rig.location = loc
        if rig.animation_data:
            rig.animation_data.action = act
    bpy.context.view_layer.update()


def layout():
    """Space all built characters cleanly side-by-side in the .blend viewport."""
    built = [k for k in ORDER if bpy.data.objects.get(k + '_rig')]
    mid = (len(built) - 1) * 0.5
    for idx, k in enumerate(built):
        rig = bpy.data.objects[k + '_rig']
        rig.location = ((idx - mid) * 1.15, 0.0, 0.0)


def _solo(key):
    for col in bpy.data.collections:
        if col.name.startswith('char_'):
            col.hide_render = (col.name != 'char_' + key)


def _show_all():
    for col in bpy.data.collections:
        if col.name.startswith('char_'):
            col.hide_render = False


def _pose(rig, clip_name, frame):
    ad = rig.animation_data
    prefix = rig.name[:-4] + '|'
    act = next((a for a in bpy.data.actions if a.get('clip') == clip_name and a.name.startswith(prefix)), None)
    if act and ad:
        ad.action = act
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def _bench(on, x=0.0):
    old = bpy.data.objects.get('_prev_bench')
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    if not on:
        return
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, 0.24, 0.225))
    obj = bpy.context.active_object
    obj.name = '_prev_bench'
    obj.scale = (0.96, 0.48, 0.45)
    obj.data.materials.append(L.toon_mat('toon_prev_bench', '#D9A066', shadow='#B8887A', rim=0.14))


def _render_setup(res):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'

    # Warm golden-hour Nile gradient backdrop
    w = sc.world or bpy.data.worlds.new('World')
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    bg = nt.nodes.new('ShaderNodeBackground')
    out = nt.nodes.new('ShaderNodeOutputWorld')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    rp = nt.nodes.new('ShaderNodeValToRGB')
    rp.color_ramp.elements[0].position = 0.0
    rp.color_ramp.elements[0].color = (*L.lin('#F5CC8A'), 1.0)
    mid = rp.color_ramp.elements.new(0.42)
    mid.color = (*L.lin('#F3D9AA'), 1.0)
    rp.color_ramp.elements[-1].position = 1.0
    rp.color_ramp.elements[-1].color = (*L.lin('#92AACE'), 1.0)
    nt.links.new(tc.outputs['Window'], sep.inputs[0])
    nt.links.new(sep.outputs['Y'], rp.inputs['Fac'])
    nt.links.new(rp.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 1.0

    amb = nt.nodes.new('ShaderNodeBackground')
    amb.inputs['Color'].default_value = (*L.lin('#D4BFA8'), 1.0)
    amb.inputs['Strength'].default_value = 0.28
    lp = nt.nodes.new('ShaderNodeLightPath')
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mx.inputs[0])
    nt.links.new(amb.outputs[0], mx.inputs[1])
    nt.links.new(bg.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])

    for o in [o for o in bpy.data.objects if o.name.startswith('_prev_')]:
        bpy.data.objects.remove(o, do_unlink=True)

    ld = bpy.data.lights.new('_prev_sun', 'SUN')
    ld.energy = 3.4
    ld.color = L.lin('#FFF0D8')
    ld.angle = math.radians(2.0)
    ld.use_shadow = False
    sun = bpy.data.objects.new('_prev_sun', ld)
    sc.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(48), 0.0, math.radians(-32))

    cam_d = bpy.data.cameras.new('_prev_cam')
    cam_d.type = 'ORTHO'
    cam = bpy.data.objects.new('_prev_cam', cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam, sun


def _cleanup_prev():
    for o in [o for o in bpy.data.objects if o.name.startswith('_prev_')]:
        bpy.data.objects.remove(o, do_unlink=True)


def _frame_camera(cam, center, ortho_scale, dist=6.0, elev_deg=4.0, yaw_deg=0.0):
    cam.data.ortho_scale = ortho_scale
    yaw = math.radians(yaw_deg)
    elev = math.radians(elev_deg)
    d = Vector((math.sin(yaw) * math.cos(elev), -math.cos(yaw) * math.cos(elev), math.sin(elev))) * dist
    cam.location = Vector(center) + d
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_end = 100.0


def _render_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def _stitch(paths, out_path, cols=None):
    imgs = [bpy.data.images.load(p) for p in paths]
    arrs = []
    for im in imgs:
        buf = np.empty(im.size[0] * im.size[1] * 4, dtype=np.float32)
        im.pixels.foreach_get(buf)
        arrs.append(buf.reshape(im.size[1], im.size[0], 4))
    cols = cols or len(arrs)
    rows = math.ceil(len(arrs) / cols)
    h, w = arrs[0].shape[:2]
    # Fill unused grid slots with warm golden backdrop color
    bg = np.array((*L.hex_rgb('#F3D9AA'), 1.0), dtype=np.float32)
    big = np.broadcast_to(bg, (h * rows, w * cols, 4)).copy()
    for i, a in enumerate(arrs):
        r, c = divmod(i, cols)
        big[(rows - 1 - r) * h:(rows - r) * h, c * w:(c + 1) * w] = a
    out_im = bpy.data.images.new('_stitch', w * cols, h * rows)
    out_im.pixels.foreach_set(big.ravel())
    out_im.filepath_raw = out_path
    out_im.file_format = 'PNG'
    out_im.save()
    for im in imgs:
        bpy.data.images.remove(im)
    bpy.data.images.remove(out_im)
    for p in paths:
        if os.path.exists(p):
            os.remove(p)


def _mesh_top_z(key):
    mesh = bpy.data.objects.get(key)
    if not mesh:
        return 1.6
    return max(v.co.z for v in mesh.data.vertices)


def render_turnaround(key):
    """Render 4-view turnaround (front, 3/4, side, back) at 1600x900 -> <key>_turn.png."""
    os.makedirs(L.PREV, exist_ok=True)
    L.set_all_mat_mode('cel')
    state = _save_state()
    cam, sun = _render_setup((400, 900))
    _solo(key)

    rig = bpy.data.objects[key + '_rig']
    rig.location = (0.0, 0.0, 0.0)
    clip = 'sit' if key == 'grandma_zainab' else 'idle'
    _pose(rig, clip, 6)
    _bench(key == 'grandma_zainab', 0.0)

    top = _mesh_top_z(key)
    center_z = top * 0.44 if key == 'grandma_zainab' else top * 0.51
    ortho_h = (top * 0.94 if key == 'grandma_zainab' else top * 1.14)
    # Ortho camera uses larger of horizontal/vertical axis; for 400x900 (tall), ortho_scale = height!
    paths = []
    for idx, yaw in enumerate((0.0, 38.0, 90.0, 180.0)):
        _frame_camera(cam, (0.0, 0.0, center_z), ortho_h, elev_deg=4.0, yaw_deg=yaw)
        sun.rotation_euler = (math.radians(48), 0.0, math.radians(-32 + yaw))
        p = L.PREV + f'_tmp_{key}_t{idx}.png'
        _render_to(p)
        paths.append(p)

    _stitch(paths, L.PREV + f'{key}_turn.png', cols=4)
    _bench(False)
    _show_all()
    _cleanup_prev()
    _restore_state(state)


def render_face(key):
    """Render 900x900 close-up portrait at gentle 3/4 angle -> <key>_face.png."""
    os.makedirs(L.PREV, exist_ok=True)
    L.set_all_mat_mode('cel')
    state = _save_state()
    cam, sun = _render_setup((900, 900))
    _solo(key)

    rig = bpy.data.objects[key + '_rig']
    rig.location = (0.0, 0.0, 0.0)
    clip = 'sit' if key == 'grandma_zainab' else 'idle'
    _pose(rig, clip, 6)

    pb_head = rig.pose.bones['head']
    head_mid = rig.matrix_world @ pb_head.head.lerp(pb_head.tail, 0.56)
    head_len = (pb_head.tail - pb_head.head).length
    _frame_camera(cam, (head_mid.x, head_mid.y, head_mid.z + head_len * 0.06), head_len * 1.95, elev_deg=2.5, yaw_deg=16.0)
    sun.rotation_euler = (math.radians(46), 0.0, math.radians(-22))
    _render_to(L.PREV + f'{key}_face.png')

    _show_all()
    _cleanup_prev()
    _restore_state(state)


def render_lineup():
    """Render all built characters side by side on a warm golden-hour gradient at 2600x1000."""
    os.makedirs(L.PREV, exist_ok=True)
    L.set_all_mat_mode('cel')
    state = _save_state()
    cam, sun = _render_setup((2600, 1000))
    _show_all()

    built = [k for k in ORDER if bpy.data.objects.get(k + '_rig')]
    if not built:
        _cleanup_prev()
        _restore_state(state)
        return

    spacing = 1.02
    mid = (len(built) - 1) * 0.5
    zainab_x = None
    for idx, k in enumerate(built):
        rig = bpy.data.objects[k + '_rig']
        x = (idx - mid) * spacing
        rig.location = (x, 0.0, 0.0)
        _pose(rig, 'sit' if k == 'grandma_zainab' else 'idle', 6)
        if k == 'grandma_zainab':
            zainab_x = x

    _bench(zainab_x is not None, zainab_x or 0.0)
    # 2600x1000 wide ortho -> ortho_scale is horizontal span!
    span_x = max(3.6, len(built) * spacing + 0.9)
    _frame_camera(cam, (0.0, 0.0, 0.96), span_x, elev_deg=3.0, yaw_deg=6.0)
    sun.rotation_euler = (math.radians(48), 0.0, math.radians(-28))
    _render_to(L.PREV + 'lineup.png')

    _bench(False)
    _cleanup_prev()
    _restore_state(state)


def render_poses():
    """Render key action poses (walk, run, talk, sit, sit_talk) to verify zero clipping -> poses.png."""
    os.makedirs(L.PREV, exist_ok=True)
    L.set_all_mat_mode('cel')
    state = _save_state()
    cam, sun = _render_setup((420, 660))

    shots = [
        ('player', 'walk', 7, 58.0),
        ('player', 'run', 5, 65.0),
        ('player', 'talk', 14, 18.0),
        ('farmer', 'walk', 7, 58.0),
        ('farmer', 'talk', 14, 20.0),
        ('grandma_zainab', 'sit', 10, 32.0),
        ('grandma_zainab', 'sit_talk', 14, 18.0),
        ('grandma_zainab', 'idle', 10, 22.0),
        ('grandma', 'walk', 7, 58.0),
        ('grandma', 'talk', 14, 18.0),
        ('trader', 'walk', 7, 58.0),
        ('trader', 'talk', 14, 20.0),
        ('sheikh', 'walk', 7, 58.0),
        ('sheikh', 'talk', 14, 18.0),
        ('aunt', 'walk', 7, 58.0),
        ('aunt', 'talk', 14, 18.0),
    ]
    paths = []
    for k, clip, frame, yaw in shots:
        rig = bpy.data.objects.get(k + '_rig')
        if not rig:
            continue
        if not any(a.get('clip') == clip and a.name.startswith(k + '|') for a in bpy.data.actions):
            continue
        _solo(k)
        rig.location = (0.0, 0.0, 0.0)
        _pose(rig, clip, frame)
        _bench(clip.startswith('sit'), 0.0)
        top = _mesh_top_z(k)
        cz = top * 0.44 if clip.startswith('sit') else top * 0.51
        oh = top * 0.96 if clip.startswith('sit') else top * 1.18
        _frame_camera(cam, (0.0, 0.0, cz), oh, elev_deg=4.0, yaw_deg=yaw)
        sun.rotation_euler = (math.radians(48), 0.0, math.radians(-32 + yaw))
        p = L.PREV + f'_tmp_pose_{k}_{clip}.png'
        _render_to(p)
        paths.append(p)
        _bench(False)

    if paths:
        _stitch(paths, L.PREV + 'poses.png', cols=4)

    _show_all()
    _cleanup_prev()
    _restore_state(state)
