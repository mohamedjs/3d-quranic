"""EEVEE v4 PBR golden-hour preview renders: M5_lineup, M5_<key>_turn, M5_<key>_face, M5_poses."""
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
    # Exact mastaba bench matching village.js (seat top z = 0.45 m, depth 0.60 m: y = -0.35..+0.25)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, -0.05, 0.225))
    obj = bpy.context.active_object
    obj.name = '_prev_bench'
    obj.scale = (0.96, 0.60, 0.45)
    mat = bpy.data.materials.get('_prev_bench_mat') or bpy.data.materials.new('_prev_bench_mat')
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    pr = nt.nodes.new('ShaderNodeBsdfPrincipled')
    pr.inputs['Base Color'].default_value = (*L.lin('#D9A874'), 1.0)
    pr.inputs['Roughness'].default_value = 0.90
    nt.links.new(pr.outputs['BSDF'], out.inputs['Surface'])
    obj.data.materials.append(mat)


def _floor(on):
    old = bpy.data.objects.get('_prev_floor')
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    if not on:
        return
    bpy.ops.mesh.primitive_plane_add(size=24.0, location=(0.0, 0.0, -0.001))
    obj = bpy.context.active_object
    obj.name = '_prev_floor'
    mat = bpy.data.materials.get('_prev_floor_mat') or bpy.data.materials.new('_prev_floor_mat')
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    pr = nt.nodes.new('ShaderNodeBsdfPrincipled')
    pr.inputs['Base Color'].default_value = (*L.lin('#C9A474'), 1.0)
    pr.inputs['Roughness'].default_value = 0.94
    nt.links.new(pr.outputs['BSDF'], out.inputs['Surface'])
    obj.data.materials.append(mat)


def _render_setup(res):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.eevee.taa_render_samples = 32
    # Khronos PBR Neutral preserves exact v3 hue/saturation & value across midtones with clean highlight roll-off!
    try:
        sc.view_settings.view_transform = 'Khronos PBR Neutral'
        sc.view_settings.look = 'None'
    except Exception:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Base Contrast'
    sc.view_settings.exposure = 0.05

    # Warm golden-hour sky backdrop for camera + soft calibrated v4 HDRI IBL for lighting!
    w = sc.world or bpy.data.worlds.new('World')
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')

    # Camera background: warm dusk-to-sky studio gradient matching v4 art direction
    bg_cam = nt.nodes.new('ShaderNodeBackground')
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
    nt.links.new(rp.outputs['Color'], bg_cam.inputs['Color'])
    bg_cam.inputs['Strength'].default_value = 0.96

    # Lighting environment: soft warm-graded HDRI IBL calibrated so garments match exact v3 DESIGN_NOTES values
    bg_ibl = nt.nodes.new('ShaderNodeBackground')
    sky_path = L.TEX_V4 + 'sky/qwantani_sunset_puresky_2k.webp'
    if os.path.exists(sky_path):
        env_tex = nt.nodes.new('ShaderNodeTexEnvironment')
        env_img = bpy.data.images.load(sky_path, check_existing=True)
        env_img.colorspace_settings.name = 'sRGB'
        env_tex.image = env_img
        mix_w = nt.nodes.new('ShaderNodeMix')
        mix_w.data_type = 'RGBA'
        mix_w.inputs['Factor'].default_value = 0.30
        mix_w.inputs[7].default_value = (*L.lin('#F0DFC6'), 1.0)
        nt.links.new(env_tex.outputs['Color'], mix_w.inputs[6])
        nt.links.new(mix_w.outputs[2], bg_ibl.inputs['Color'])
        bg_ibl.inputs['Strength'].default_value = 0.72
    else:
        bg_ibl.inputs['Color'].default_value = (*L.lin('#E8D6BE'), 1.0)
        bg_ibl.inputs['Strength'].default_value = 0.72

    lp = nt.nodes.new('ShaderNodeLightPath')
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mx.inputs[0])
    nt.links.new(bg_ibl.outputs[0], mx.inputs[1])
    nt.links.new(bg_cam.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])

    for o in [o for o in bpy.data.objects if o.name.startswith('_prev_')]:
        bpy.data.objects.remove(o, do_unlink=True)

    # Clean warm-white golden-hour key sun (sculpts folds & cloth weave while keeping exact v3 hex value & hue)
    ld = bpy.data.lights.new('_prev_sun', 'SUN')
    ld.energy = 3.15
    ld.color = L.lin('#FFF6E8')
    ld.angle = math.radians(5.5)
    ld.use_shadow = True
    sun = bpy.data.objects.new('_prev_sun', ld)
    sc.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(56), 0.0, math.radians(-32))

    # Gentle airy sky fill + subtle warm rim so shadow sides stay soft & rich
    lf = bpy.data.lights.new('_prev_fill', 'SUN')
    lf.energy = 0.52
    lf.color = L.lin('#DAE2F2')
    lf.angle = math.radians(24.0)
    lf.use_shadow = False
    fill = bpy.data.objects.new('_prev_fill', lf)
    sc.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(38), 0.0, math.radians(125))

    lr = bpy.data.lights.new('_prev_rim', 'SUN')
    lr.energy = 0.85
    lr.color = L.lin('#FFE0AD')
    lr.angle = math.radians(10.0)
    lr.use_shadow = False
    rim = bpy.data.objects.new('_prev_rim', lr)
    sc.collection.objects.link(rim)
    rim.rotation_euler = (math.radians(68), 0.0, math.radians(155))

    cam_d = bpy.data.cameras.new('_prev_cam')
    cam_d.type = 'ORTHO'
    cam = bpy.data.objects.new('_prev_cam', cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam, sun, fill, rim


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
    bg = np.array((*L.hex_rgb('#EED2A6'), 1.0), dtype=np.float32)
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
    """Render 4-view turnaround (front, 3/4, side, back) at 1600x900 -> M5_<key>_turn.png."""
    os.makedirs(L.PREV, exist_ok=True)
    L.set_all_mat_mode('preview')
    state = _save_state()
    cam, sun, fill, rim = _render_setup((400, 900))
    _solo(key)

    rig = bpy.data.objects[key + '_rig']
    rig.location = (0.0, 0.0, 0.0)
    clip = 'sit' if key == 'grandma_zainab' else 'idle'
    _pose(rig, clip, 6)
    _bench(key == 'grandma_zainab', 0.0)

    top = _mesh_top_z(key)
    center_z = top * 0.44 if key == 'grandma_zainab' else top * 0.51
    ortho_h = top * 0.94 if key == 'grandma_zainab' else top * 1.14
    paths = []
    for idx, yaw in enumerate((0.0, 38.0, 90.0, 180.0)):
        _frame_camera(cam, (0.0, 0.0, center_z), ortho_h, elev_deg=4.0, yaw_deg=yaw)
        sun.rotation_euler = (math.radians(58), 0.0, math.radians(-34 + yaw))
        fill.rotation_euler = (math.radians(38), 0.0, math.radians(125 + yaw))
        rim.rotation_euler = (math.radians(68), 0.0, math.radians(155 + yaw))
        p = L.PREV + f'_tmp_{key}_t{idx}.png'
        _render_to(p)
        paths.append(p)

    _stitch(paths, L.PREV + f'M5_{key}_turn.png', cols=4)
    _bench(False)
    _show_all()
    _cleanup_prev()
    _restore_state(state)


def render_face(key):
    """Render 900x900 close-up portrait at gentle 3/4 angle -> M5_<key>_face.png."""
    os.makedirs(L.PREV, exist_ok=True)
    L.set_all_mat_mode('preview')
    state = _save_state()
    cam, sun, fill, rim = _render_setup((900, 900))
    _solo(key)

    rig = bpy.data.objects[key + '_rig']
    rig.location = (0.0, 0.0, 0.0)
    clip = 'sit' if key == 'grandma_zainab' else 'idle'
    _pose(rig, clip, 6)

    pb_head = rig.pose.bones['head']
    head_mid = rig.matrix_world @ pb_head.head.lerp(pb_head.tail, 0.56)
    head_len = (pb_head.tail - pb_head.head).length
    _frame_camera(cam, (head_mid.x, head_mid.y, head_mid.z + head_len * 0.06), head_len * 1.95, elev_deg=2.5, yaw_deg=16.0)
    sun.rotation_euler = (math.radians(52), 0.0, math.radians(-24))
    _render_to(L.PREV + f'M5_{key}_face.png')

    _show_all()
    _cleanup_prev()
    _restore_state(state)


def render_lineup():
    """Render all seven characters side by side at 2600x1000 -> M5_lineup.png."""
    os.makedirs(L.PREV, exist_ok=True)
    L.set_all_mat_mode('preview')
    state = _save_state()
    cam, sun, fill, rim = _render_setup((2600, 1000))
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
    _floor(True)
    span_x = max(3.6, len(built) * spacing + 0.9)
    _frame_camera(cam, (0.0, 0.0, 0.96), span_x, elev_deg=3.5, yaw_deg=6.0)
    sun.rotation_euler = (math.radians(56), 0.0, math.radians(-30))
    _render_to(L.PREV + 'M5_lineup.png')

    _floor(False)
    _bench(False)
    _cleanup_prev()
    _restore_state(state)


def render_poses():
    """Render key action poses (walk, run, talk, sit, sit_talk) to verify zero clipping -> M5_poses.png."""
    os.makedirs(L.PREV, exist_ok=True)
    L.set_all_mat_mode('preview')
    state = _save_state()
    cam, sun, fill, rim = _render_setup((420, 660))

    shots = [
        ('player', 'walk', 7, 58.0),
        ('player', 'run', 5, 65.0),
        ('player', 'talk', 26, 18.0),
        ('farmer', 'walk', 7, 58.0),
        ('farmer', 'talk', 26, 20.0),
        ('grandma_zainab', 'sit', 10, 38.0),
        ('grandma_zainab', 'sit_talk', 70, 22.0),
        ('grandma_zainab', 'idle', 10, 22.0),
        ('grandma', 'walk', 7, 58.0),
        ('grandma', 'talk', 70, 18.0),
        ('trader', 'walk', 7, 58.0),
        ('trader', 'talk', 26, 20.0),
        ('sheikh', 'walk', 7, 58.0),
        ('sheikh', 'talk', 70, 18.0),
        ('aunt', 'walk', 7, 58.0),
        ('aunt', 'talk', 70, 18.0),
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
        sun.rotation_euler = (math.radians(56), 0.0, math.radians(-32 + yaw))
        p = L.PREV + f'_tmp_pose_{k}_{clip}.png'
        _render_to(p)
        paths.append(p)
        _bench(False)

    if paths:
        _stitch(paths, L.PREV + 'M5_poses.png', cols=4)

    _show_all()
    _cleanup_prev()
    _restore_state(state)
