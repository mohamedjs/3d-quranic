"""Shared 22-bone stylized character skeleton and smooth analytical skinning."""
import math
import bpy
from mathutils import Vector

from lib import smoothstep


def compute_landmarks(p):
    """Derive exact 3D joint positions (metres, Z up, facing -Y) from a proportions dict."""
    h = p['height']
    head_ratio = p['head_ratio']           # total height / head height (4.2 child, 5.5 adult)
    head_h = h / head_ratio
    head_r = head_h * 0.46                 # base skull radius (vertical span ~2.18*R incl. soft chin)
    head_z = h - head_r * 1.04             # skull center Z so crown sits right at h

    neck_top_z = head_z - head_r * 1.02
    neck_bot_z = neck_top_z - head_h * p.get('neck_frac', 0.22)
    sh_z = neck_bot_z - head_h * 0.10      # soft warm storybook shoulder slope
    hip_z = h * p.get('hip_frac', 0.46)    # hip joint height
    waist_z = hip_z + (sh_z - hip_z) * 0.42
    chest_z = hip_z + (sh_z - hip_z) * 0.78

    ankle_z = h * p.get('ankle_frac', 0.052)
    knee_z = ankle_z + (hip_z - ankle_z) * 0.50

    sh_x = h * p.get('shoulder_w', 0.125)
    hip_x = h * p.get('hip_w', 0.068)
    chest_d = h * p.get('chest_d', 0.068)
    belly_d = h * p.get('belly_d', 0.068)
    pelvis_d = h * p.get('pelvis_d', 0.072)

    # Natural relaxed A-pose (68 deg below horizontal) so shoulders stay silky-smooth in idle & talk!
    upper_len = (sh_z - hip_z) * p.get('upperarm_frac', 0.54)
    lower_len = (sh_z - hip_z) * p.get('lowerarm_frac', 0.47)
    hand_len = head_h * p.get('hand_frac', 0.36)

    a_angle = math.radians(p.get('arm_drop_deg', 68.0))
    f_angle = math.radians(p.get('arm_drop_deg', 68.0) + 6.0)

    clav_head = lambda s: Vector((s * sh_x * 0.24, 0.0, neck_bot_z - 0.012))
    sh_pos = lambda s: Vector((s * sh_x, 0.008, sh_z))
    elb_pos = lambda s: sh_pos(s) + Vector((
        s * math.cos(a_angle) * upper_len,
        0.012,
        -math.sin(a_angle) * upper_len,
    ))
    wri_pos = lambda s: elb_pos(s) + Vector((
        s * math.cos(f_angle) * lower_len,
        -0.022 * lower_len / 0.22,
        -math.sin(f_angle) * lower_len,
    ))
    hand_tip = lambda s: wri_pos(s) + Vector((
        s * math.cos(f_angle + 0.06) * hand_len,
        -0.012 * hand_len / 0.12,
        -math.sin(f_angle + 0.06) * hand_len,
    ))

    foot_len = h * p.get('foot_len', 0.115)
    foot_y_heel = 0.028 * (h / 1.65)

    return {
        'height': h,
        'head_h': head_h,
        'head_r': head_r,
        'head_center': Vector((0.0, -0.006, head_z)),
        'neck_top': Vector((0.0, 0.0, neck_top_z)),
        'neck_bot': Vector((0.0, 0.0, neck_bot_z)),
        'pelvis': Vector((0.0, 0.0, hip_z)),
        'waist': Vector((0.0, 0.0, waist_z)),
        'chest': Vector((0.0, 0.0, chest_z)),
        'sh_z': sh_z,
        'sh_x': sh_x,
        'hip_z': hip_z,
        'hip_x': hip_x,
        'knee_z': knee_z,
        'ankle_z': ankle_z,
        'waist_z': waist_z,
        'chest_z': chest_z,
        'chest_d': chest_d,
        'belly_d': belly_d,
        'pelvis_d': pelvis_d,
        'upper_len': upper_len,
        'lower_len': lower_len,
        'hand_len': hand_len,
        'foot_len': foot_len,
        'foot_y_heel': foot_y_heel,
        'clav_l': clav_head(1), 'clav_r': clav_head(-1),
        'sh_l': sh_pos(1), 'sh_r': sh_pos(-1),
        'elb_l': elb_pos(1), 'elb_r': elb_pos(-1),
        'wri_l': wri_pos(1), 'wri_r': wri_pos(-1),
        'hand_l': hand_tip(1), 'hand_r': hand_tip(-1),
        'hip_l': Vector((hip_x, 0.0, hip_z)),
        'hip_r': Vector((-hip_x, 0.0, hip_z)),
        'knee_l': Vector((hip_x * 0.96, -0.006, knee_z)),
        'knee_r': Vector((-hip_x * 0.96, -0.006, knee_z)),
        'ankle_l': Vector((hip_x * 0.94, 0.004, ankle_z)),
        'ankle_r': Vector((-hip_x * 0.94, 0.004, ankle_z)),
        'toe_l': Vector((hip_x * 0.96, -foot_len * 0.72, ankle_z * 0.36)),
        'toe_r': Vector((-hip_x * 0.96, -foot_len * 0.72, ankle_z * 0.36)),
    }


def build_armature(name, col, lm, face_bones=None):
    """Build the 22-bone stylized armature from computed landmarks."""
    arm_data = bpy.data.armatures.new(name)
    arm_obj = bpy.data.objects.new(name, arm_data)
    col.objects.link(arm_obj)

    bpy.context.view_layer.objects.active = arm_obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    arm_obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones

    def add_bone(bname, head, tail, parent=None, connect=False):
        b = eb.new(bname)
        b.head = Vector(head)
        b.tail = Vector(tail)
        b.roll = 0.0
        b.use_deform = True
        if parent is not None:
            b.parent = eb[parent]
            b.use_connect = connect
        return b

    # Core spine & head
    add_bone('pelvis', lm['pelvis'], lm['waist'])
    add_bone('spine_01', lm['waist'], lm['chest'], 'pelvis', connect=True)
    add_bone('spine_02', lm['chest'], lm['neck_bot'], 'spine_01', connect=True)
    add_bone('neck', lm['neck_bot'], lm['neck_top'], 'spine_02', connect=True)
    head_top = lm['head_center'] + Vector((0.0, 0.0, lm['head_r'] * 1.05))
    add_bone('head', lm['neck_top'], head_top, 'neck', connect=True)

    # Arms (A-pose)
    for sd in ('l', 'r'):
        add_bone(f'clavicle_{sd}', lm[f'clav_{sd}'], lm[f'sh_{sd}'], 'spine_02', connect=False)
        add_bone(f'upperarm_{sd}', lm[f'sh_{sd}'], lm[f'elb_{sd}'], f'clavicle_{sd}', connect=True)
        add_bone(f'lowerarm_{sd}', lm[f'elb_{sd}'], lm[f'wri_{sd}'], f'upperarm_{sd}', connect=True)
        add_bone(f'hand_{sd}', lm[f'wri_{sd}'], lm[f'hand_{sd}'], f'lowerarm_{sd}', connect=True)

    # Legs
    for sd in ('l', 'r'):
        add_bone(f'thigh_{sd}', lm[f'hip_{sd}'], lm[f'knee_{sd}'], 'pelvis', connect=False)
        add_bone(f'calf_{sd}', lm[f'knee_{sd}'], lm[f'ankle_{sd}'], f'thigh_{sd}', connect=True)
        add_bone(f'foot_{sd}', lm[f'ankle_{sd}'], lm[f'toe_{sd}'], f'calf_{sd}', connect=True)

    # Optional face bones (lid_l, lid_r, mouth)
    if face_bones:
        for bname, (head, tail) in face_bones.items():
            add_bone(bname, head, tail, 'head', connect=False)

    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return arm_obj


def add_face_bones(rig, face_bones):
    """Add or update lid_l, lid_r, mouth deform bones parented to 'head'."""
    bpy.context.view_layer.objects.active = rig
    for o in bpy.context.selected_objects:
        o.select_set(False)
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = rig.data.edit_bones
    for bname, (head, tail) in face_bones.items():
        if bname in eb:
            eb.remove(eb[bname])
        b = eb.new(bname)
        b.head = Vector(head)
        b.tail = Vector(tail)
        b.roll = 0.0
        b.parent = eb['head']
        b.use_deform = True
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'


# ------------------------------------------------------------------ skinning
def bind_armature(obj, rig):
    """Parent obj to rig with identity offset and Armature modifier."""
    obj.parent = rig
    obj.matrix_parent_inverse = rig.matrix_world.inverted()
    for m in list(obj.modifiers):
        if m.type == 'ARMATURE':
            m.object = rig
            return obj
    am = obj.modifiers.new('rig', 'ARMATURE')
    am.object = rig
    return obj


def _set_weights(obj, rig, weight_map):
    """Assign normalized vertex weights {vert_idx: {bone_name: w}} and bind to rig."""
    for vg in list(obj.vertex_groups):
        obj.vertex_groups.remove(vg)
    groups = {}

    def get_vg(name):
        if name not in groups:
            groups[name] = obj.vertex_groups.new(name=name)
        return groups[name]

    for vi, bw in weight_map.items():
        items = [(k, v) for k, v in bw.items() if v > 1e-4]
        items.sort(key=lambda kv: -kv[1])
        items = items[:4]  # glTF max 4 influences per vertex
        total = sum(v for _, v in items)
        if total <= 1e-6:
            continue
        for bname, w in items:
            get_vg(bname).add([vi], w / total, 'REPLACE')
    return bind_armature(obj, rig)


def skin_rigid(obj, rig, bone_name):
    """Bind every vertex of obj rigidly to a single bone."""
    wmap = {v.index: {bone_name: 1.0} for v in obj.data.vertices}
    return _set_weights(obj, rig, wmap)


def _seg_t_dist(p, a, b):
    """Return parameter t in [0, 1] and distance from point p to segment a-b."""
    ab = b - a
    l2 = ab.length_squared
    if l2 < 1e-10:
        return 0.0, (p - a).length
    t = max(0.0, min(1.0, (p - a).dot(ab) / l2))
    proj = a + ab * t
    return t, (p - proj).length


def skin_limb_chain(obj, rig, bone_names, blend=0.22):
    """Smooth analytical weighting along a sequential bone chain (e.g. arm or leg)."""
    bones = [(n, rig.data.bones[n].head_local.copy(), rig.data.bones[n].tail_local.copy()) for n in bone_names]
    wmap = {}
    for v in obj.data.vertices:
        p = v.co
        # Find closest segment
        best_i, best_t, best_d = 0, 0.0, 1e9
        for i, (_, a, b) in enumerate(bones):
            t, d = _seg_t_dist(p, a, b)
            if d < best_d:
                best_i, best_t, best_d = i, t, d
        bw = {}
        name_i = bones[best_i][0]
        if best_i > 0 and best_t < blend:
            f = smoothstep(0.0, blend, best_t) * 0.5 + 0.5
            bw[name_i] = f
            bw[bones[best_i - 1][0]] = 1.0 - f
        elif best_i < len(bones) - 1 and best_t > 1.0 - blend:
            f = smoothstep(1.0 - blend, 1.0, best_t) * 0.5
            bw[name_i] = 1.0 - f
            bw[bones[best_i + 1][0]] = f
        else:
            bw[name_i] = 1.0
        wmap[v.index] = bw
    return _set_weights(obj, rig, wmap)


def skin_spine_mesh(obj, rig, lm, allow_neck=False, allow_head=False):
    """Smooth vertical spine skinning (pelvis -> spine_01 -> spine_02 -> optional neck/head)."""
    z_pel = lm['hip_z']
    z_wst = lm['waist_z']
    z_chs = lm['chest_z']
    z_nb = lm['neck_bot'].z
    z_nt = lm['neck_top'].z
    wmap = {}
    for v in obj.data.vertices:
        z = v.co.z
        bw = {}
        if z <= z_pel:
            bw['pelvis'] = 1.0
        elif z <= z_wst:
            t = smoothstep(z_pel, z_wst, z)
            bw['pelvis'] = 1.0 - t
            bw['spine_01'] = t
        elif z <= z_chs:
            t = smoothstep(z_wst, z_chs, z)
            bw['spine_01'] = 1.0 - t
            bw['spine_02'] = t
        elif allow_neck and z > z_nb - 0.02:
            t = smoothstep(z_nb - 0.02, z_nb + 0.035, z)
            bw['spine_02'] = 1.0 - t
            if allow_head and z > z_nt - 0.025:
                th = smoothstep(z_nt - 0.025, z_nt + 0.02, z)
                bw['neck'] = t * (1.0 - th)
                bw['head'] = t * th
            else:
                bw['neck'] = t
        else:
            bw['spine_02'] = 1.0
        wmap[v.index] = bw
    return _set_weights(obj, rig, wmap)


def skin_upper_garment(obj, rig, lm, sleeve_blend=0.05):
    """Skin a unified torso+sleeves top (or standalone torso) smoothly across spine & arms."""
    sh_x = lm['sh_x']
    sh_z = lm['sh_z']
    z_pel = lm['hip_z']
    z_wst = lm['waist_z']
    z_chs = lm['chest_z']
    z_nb = lm['neck_bot'].z
    wmap = {}

    arm_bones = {
        'l': [
            ('upperarm_l', lm['sh_l'], lm['elb_l']),
            ('lowerarm_l', lm['elb_l'], lm['wri_l']),
            ('hand_l', lm['wri_l'], lm['hand_l']),
        ],
        'r': [
            ('upperarm_r', lm['sh_r'], lm['elb_r']),
            ('lowerarm_r', lm['elb_r'], lm['wri_r']),
            ('hand_r', lm['wri_r'], lm['hand_r']),
        ],
    }

    for v in obj.data.vertices:
        p = v.co
        # Base spine weights
        if p.z <= z_pel:
            sp = {'pelvis': 1.0}
        elif p.z <= z_wst:
            t = smoothstep(z_pel, z_wst, p.z)
            sp = {'pelvis': 1.0 - t, 'spine_01': t}
        elif p.z <= z_chs:
            t = smoothstep(z_wst, z_chs, p.z)
            sp = {'spine_01': 1.0 - t, 'spine_02': t}
        elif p.z <= z_nb:
            sp = {'spine_02': 1.0}
        else:
            t = smoothstep(z_nb, z_nb + 0.04, p.z)
            sp = {'spine_02': 1.0 - t, 'neck': t}

        # Check lateral arm proximity (vertices beyond torso flank and in shoulder height band)
        sd = 'l' if p.x >= 0.0 else 'r'
        ax = abs(p.x)
        # Only blend into arm if vertex is laterally outside torso wall near shoulder/arm
        _, d_ua = _seg_t_dist(p, lm[f'sh_{sd}'], lm[f'elb_{sd}'])
        _, d_la = _seg_t_dist(p, lm[f'elb_{sd}'], lm[f'wri_{sd}'])
        arm_d = min(d_ua, d_la)

        in_arm = smoothstep(sh_x * 0.78, sh_x * 1.10, ax) * (1.0 - smoothstep(0.09, 0.16, arm_d))
        if p.z < lm[f'elb_{sd}'].z - 0.12 and d_la > 0.09:
            in_arm = 0.0

        if in_arm > 0.01:
            # Compute arm bone weights along upperarm/lowerarm
            t_ua, d1 = _seg_t_dist(p, lm[f'sh_{sd}'], lm[f'elb_{sd}'])
            t_la, d2 = _seg_t_dist(p, lm[f'elb_{sd}'], lm[f'wri_{sd}'])
            if d1 <= d2:
                if t_ua > 0.78:
                    f = smoothstep(0.78, 1.0, t_ua) * 0.5
                    aw = {f'upperarm_{sd}': 1.0 - f, f'lowerarm_{sd}': f}
                else:
                    aw = {f'upperarm_{sd}': 1.0}
            else:
                if t_la < 0.22:
                    f = smoothstep(0.0, 0.22, t_la) * 0.5 + 0.5
                    aw = {f'lowerarm_{sd}': f, f'upperarm_{sd}': 1.0 - f}
                else:
                    aw = {f'lowerarm_{sd}': 1.0}
            bw = {}
            for k, w in sp.items():
                bw[k] = bw.get(k, 0.0) + w * (1.0 - in_arm)
            for k, w in aw.items():
                bw[k] = bw.get(k, 0.0) + w * in_arm
            wmap[v.index] = bw
        else:
            wmap[v.index] = sp

    return _set_weights(obj, rig, wmap)


def skin_skirt(obj, rig, lm, top_z, hem_z, calf_follow=0.68, seated_mode=False):
    """Skin a flowing robe skirt across spine/pelvis, thighs, and calves so legs never clip."""
    z_wst = lm['waist_z']
    z_hip = lm['hip_z']
    z_knee = lm['knee_z']
    hip_x = lm['hip_x']
    wmap = {}

    for v in obj.data.vertices:
        p = v.co
        z = p.z
        # Lateral left/right split (smooth across center so front/back drape bridges softly)
        lr_span = hip_x * (1.1 if seated_mode else 1.35)
        w_l = smoothstep(-lr_span, lr_span, p.x)
        w_r = 1.0 - w_l

        if seated_mode:
            # Tailored for sitting + standing: crisp pelvis->thigh fold at hip, smooth thigh->calf bend at knee
            if z > z_hip + 0.05:
                t = smoothstep(z_hip + 0.05, z_wst + 0.06, z)
                bw = {'pelvis': 1.0 - t, 'spine_01': t}
            elif z > z_knee + 0.05:
                # Hip-to-knee lap region: blends from pelvis into thigh_l / thigh_r
                t_th = smoothstep(z_hip + 0.05, z_hip - 0.08, z)
                bw = {
                    'pelvis': max(0.0, 1.0 - t_th),
                    'thigh_l': t_th * w_l,
                    'thigh_r': t_th * w_r,
                }
            else:
                # Knee-to-hem shin drape: transitions smoothly from thigh into calf
                t_cf = smoothstep(z_knee + 0.05, z_knee - 0.07, z)
                bw = {
                    'thigh_l': (1.0 - t_cf) * w_l,
                    'thigh_r': (1.0 - t_cf) * w_r,
                    'calf_l': t_cf * w_l,
                    'calf_r': t_cf * w_r,
                }
        else:
            # Walking/running robe: smoothly follows thighs AND calves so heels never clip out the back
            if z > z_hip + 0.04:
                t = smoothstep(z_hip + 0.04, top_z, z)
                bw = {'pelvis': 1.0 - t * 0.75, 'spine_01': t * 0.75}
            else:
                t_leg = smoothstep(z_hip + 0.04, z_hip - 0.14, z)
                t_calf = smoothstep(z_knee + 0.08, z_knee - 0.12, z) * calf_follow
                w_pel = 1.0 - t_leg * 0.90
                w_legs = 1.0 - w_pel
                w_th = w_legs * (1.0 - t_calf)
                w_cf = w_legs * t_calf
                bw = {
                    'pelvis': w_pel,
                    'thigh_l': w_th * w_l,
                    'thigh_r': w_th * w_r,
                    'calf_l': w_cf * w_l,
                    'calf_r': w_cf * w_r,
                }
        wmap[v.index] = bw

    return _set_weights(obj, rig, wmap)


def skin_cape_drape(obj, rig, lm, head_top_z, shoulder_z):
    """Skin a hijab/tarha/shemagh shoulder cape smoothly from head/neck into chest & clavicles."""
    sh_x = lm['sh_x']
    wmap = {}
    for v in obj.data.vertices:
        p = v.co
        t_head = smoothstep(shoulder_z + 0.06, head_top_z, p.z)
        t_neck = smoothstep(shoulder_z + 0.01, shoulder_z + 0.08, p.z) * (1.0 - t_head)
        t_body = max(0.0, 1.0 - t_head - t_neck)
        sd = 'l' if p.x >= 0.0 else 'r'
        t_sh = smoothstep(sh_x * 0.45, sh_x * 1.05, abs(p.x)) * t_body * 0.55
        bw = {
            'head': t_head,
            'neck': t_neck,
            'spine_02': max(0.0, t_body - t_sh),
            f'clavicle_{sd}': t_sh,
        }
        wmap[v.index] = bw
    return _set_weights(obj, rig, wmap)


def skin_trousers(obj, rig, lm):
    """Skin split-leg sirwal trousers cleanly per leg (pelvis, thigh, calf)."""
    z_hip = lm['hip_z']
    z_knee = lm['knee_z']
    wmap = {}
    for v in obj.data.vertices:
        p = v.co
        sd = 'l' if p.x >= 0.0 else 'r'
        if p.z > z_hip + 0.03:
            bw = {'pelvis': 1.0}
        elif p.z > z_hip - 0.07:
            t = smoothstep(z_hip + 0.03, z_hip - 0.07, p.z)
            # Blend near crotch x=0 softly
            lat = smoothstep(0.0, lm['hip_x'] * 0.45, abs(p.x))
            w_th = t * (0.55 + 0.45 * lat)
            bw = {'pelvis': 1.0 - w_th, f'thigh_{sd}': w_th}
        else:
            t_cf = smoothstep(z_knee + 0.045, z_knee - 0.045, p.z)
            bw = {f'thigh_{sd}': 1.0 - t_cf, f'calf_{sd}': t_cf}
        wmap[v.index] = bw
    return _set_weights(obj, rig, wmap)
