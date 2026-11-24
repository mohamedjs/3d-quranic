"""Stylized storybook body builder: torso silhouette, neck, forearms, mitten hands, ankles, sandals/shoes."""
import math
import bmesh
from mathutils import Vector

from lib import bm_to_obj, loft_rings, smoothstep
import rig as R


def torso_radii(lm, p, z):
    """Return (rx, ry, cy) cross-section of the stylized torso at height z (for garment fitting)."""
    z_hip = lm['hip_z']
    z_wst = lm['waist_z']
    z_chs = lm['chest_z']
    z_nb = lm['neck_bot'].z
    h = lm['height']

    sh_x = lm['sh_x']
    hip_x = lm['hip_x'] * 1.48 * p.get('hip_full', 1.0)
    wst_x = sh_x * p.get('waist_ratio', 0.72)
    chs_x = sh_x * p.get('chest_ratio', 0.92)
    neck_r = lm['head_r'] * p.get('neck_ratio', 0.36)

    pel_d = lm['pelvis_d'] * p.get('hip_full', 1.0)
    bel_d = lm['belly_d'] * p.get('belly_full', 1.0)
    chs_d = lm['chest_d'] * p.get('chest_full', 1.0)

    if z <= z_hip:
        rx, ry = hip_x, pel_d
    elif z <= z_wst:
        t = smoothstep(z_hip, z_wst, z)
        rx = hip_x + (wst_x - hip_x) * t
        ry = pel_d + (bel_d - pel_d) * t
    elif z <= z_chs:
        t = smoothstep(z_wst, z_chs, z)
        rx = wst_x + (chs_x - wst_x) * t
        ry = bel_d + (chs_d - bel_d) * t
    elif z <= z_nb:
        t = smoothstep(z_chs, z_nb, z)
        rx = chs_x + (neck_r * 1.32 - chs_x) * (t ** 1.55)
        ry = chs_d + (neck_r * 1.18 - chs_d) * (t ** 1.55)
    else:
        rx = ry = neck_r

    belly_fwd = -0.011 * (h / 1.6) * p.get('belly_fwd', 0.5) * math.exp(-((z - z_wst) / max(0.08, z_chs - z_hip)) ** 2)
    return rx, ry, belly_fwd


def build_neck(name, col, lm, p, mat, rig_obj):
    """Build a warm, sturdy stylized neck seamlessly bridging upper chest into the skull base."""
    neck_r = lm['head_r'] * p.get('neck_ratio', 0.35)
    z0 = lm['neck_bot'].z - 0.045 * (lm['height'] / 1.6)
    z1 = lm['neck_top'].z + lm['head_r'] * 0.28
    cy_bot = 0.004
    cy_top = lm['head_center'].y + lm['head_r'] * 0.06

    bm = bmesh.new()
    segs = 12
    levels = 5
    rings = []
    for i in range(levels):
        t = i / (levels - 1)
        z = z0 + (z1 - z0) * t
        flare = 1.0 + 0.52 * ((1.0 - t) ** 2.4)
        rx = neck_r * flare * 1.06
        ry = neck_r * (1.0 + 0.34 * ((1.0 - t) ** 2.2))
        cy = cy_bot + (cy_top - cy_bot) * t
        rings.append([
            bm.verts.new((rx * math.cos(a), cy + ry * math.sin(a), z))
            for a in (k / segs * math.tau for k in range(segs))
        ])

    loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)
    obj = bm_to_obj(bm, name, col, mat)
    return R.skin_spine_mesh(obj, rig_obj, lm, allow_neck=True, allow_head=True)


def _limb_frame(a, b, side_sign):
    """Build consistent right-handed orthonormal frame (tangent, u_axis, v_axis) for a limb."""
    t = (b - a).normalized()
    # Always start with world forward (-Y) projected orthogonal to t, so BOTH sides stay right-handed!
    fwd = Vector((0.0, -1.0, 0.0))
    fwd = fwd - t * fwd.dot(t)
    if fwd.length < 1e-4:
        fwd = Vector((side_sign, 0.0, 0.0))
    fwd.normalize()
    lat = fwd.cross(t).normalized()   # guarantees lat x fwd = -t consistently on both sides
    return t, lat, fwd


def build_forearms_and_hands(name, col, lm, p, mat, rig_obj, forearm_start=0.38):
    """Build smooth stylized lower forearms + soft rounded Pixar mitten-with-thumb hands."""
    parts = []
    h = lm['height']
    scale = h / 1.60
    wrist_r = 0.023 * scale * p.get('arm_thick', 1.0)
    elbow_r = 0.031 * scale * p.get('arm_thick', 1.0)
    palm_w = 0.034 * scale * p.get('hand_scale', 1.0)
    palm_t = 0.020 * scale * p.get('hand_scale', 1.0)

    for sd, s in (('l', 1.0), ('r', -1.0)):
        elb = lm[f'elb_{sd}']
        wri = lm[f'wri_{sd}']
        tip = lm[f'hand_{sd}']
        hand_len = (tip - wri).length

        bm = bmesh.new()
        t_fa, lat_fa, fwd_fa = _limb_frame(elb, wri, s)
        t_hd, lat_hd, fwd_hd = _limb_frame(wri, tip, s)

        # Rotate frame around t_hd by a tiny symmetric palm-inward angle so both hands stay 100% right-handed!
        ang_in = -s * math.radians(18.0)
        ca, sa = math.cos(ang_in), math.sin(ang_in)
        # u_hand ~ palm thickness axis (points inward toward body on L, outward on R -> use s*u_hand for inward!)
        u_hand = (lat_hd * ca + fwd_hd * sa).normalized()
        v_hand = (-lat_hd * sa + fwd_hd * ca).normalized()
        # Inward direction toward body midline is always -s * u_hand (since lat_fa points roughly +X on both sides)
        inward = -u_hand if (u_hand.x * s) > 0 else u_hand
        fwd_palm = v_hand if v_hand.y < 0 else -v_hand

        segs = 10
        rings = []
        # 1) Forearm segment (consistently using lat_fa, fwd_fa -> zero wrist twist!)
        for i in range(5):
            u = forearm_start + (1.0 - forearm_start) * (i / 4.0)
            c = elb.lerp(wri, u)
            r = elbow_r + (wrist_r - elbow_r) * (u ** 0.85)
            rings.append([
                bm.verts.new(c + (lat_fa * math.cos(a) * 0.96 + fwd_fa * math.sin(a) * 1.04) * r)
                for a in (k / segs * math.tau for k in range(segs))
            ])

        # 2) Soft chunky mitten hand using SAME right-handed basis (u_hand, v_hand) so zero twist/flip!
        hand_profile = [
            # (t_along, thick_mul, width_mul, curl_in)
            (0.10, 0.96, 0.92, 0.00),
            (0.32, 1.04, 1.10, 0.03),
            (0.58, 0.96, 1.06, 0.08),
            (0.80, 0.80, 0.90, 0.14),
            (0.95, 0.56, 0.64, 0.19),
            (1.00, 0.30, 0.34, 0.21),
        ]
        for u, tm, wm, curl in hand_profile:
            c = wri + t_hd * (u * hand_len) + inward * (curl * hand_len * 0.38)
            ru = palm_t * tm
            rv = palm_w * wm
            rings.append([
                bm.verts.new(c + u_hand * (math.cos(a) * ru) + v_hand * (math.sin(a) * rv))
                for a in (k / segs * math.tau for k in range(segs))
            ])

        loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)

        # 3) Cute rounded thumb on the forward-inner side of the palm
        thumb_base = wri + t_hd * (0.20 * hand_len) + fwd_palm * (palm_w * 0.72) + inward * (palm_t * 0.25)
        thumb_dir = (t_hd * 0.68 + fwd_palm * 0.56 + inward * 0.46).normalized()
        thumb_len = hand_len * 0.46
        th_u = thumb_dir.cross(inward)
        if th_u.length < 1e-4:
            th_u = thumb_dir.orthogonal()
        th_u.normalize()
        th_v = thumb_dir.cross(th_u).normalized()
        th_r = palm_t * 0.56
        th_rings = []
        for u, rm, bend in ((0.0, 1.12, 0.0), (0.38, 1.0, 0.02), (0.76, 0.84, 0.08), (1.0, 0.36, 0.12)):
            c = thumb_base + thumb_dir * (u * thumb_len) + inward * (bend * thumb_len)
            th_rings.append([
                bm.verts.new(c + (th_u * math.cos(a) + th_v * math.sin(a)) * (th_r * rm))
                for a in (k / 8.0 * math.tau for k in range(8))
            ])
        loft_rings(bm, th_rings, closed_u=True, cap_start=True, cap_end=True)

        obj = bm_to_obj(bm, f'{name}_{sd}', col, mat)
        R.skin_limb_chain(obj, rig_obj, [f'lowerarm_{sd}', f'hand_{sd}'], blend=0.20)
        parts.append(obj)

    return parts


def build_ankles_and_feet(name, col, lm, p, skin_mat, shoe_mat, rig_obj, shoe_style='slipper', ankle_top=0.14):
    """Build continuous lower ankles + charming stylized shoes or sandals seated cleanly on z=0."""
    skin_parts = []
    shoe_parts = []
    h = lm['height']
    scale = h / 1.60
    ankle_r = 0.031 * scale * p.get('leg_thick', 1.0)
    calf_r = 0.041 * scale * p.get('leg_thick', 1.0)
    foot_l = lm['foot_len']
    foot_w = 0.044 * scale * p.get('foot_w', 1.0)
    heel_y = lm['foot_y_heel']
    ankle_z = lm['ankle_z']
    sole_h = 0.015 * scale

    for sd, s in (('l', 1.0), ('r', -1.0)):
        ax = lm[f'ankle_{sd}'].x
        ay = lm[f'ankle_{sd}'].y

        # --- Lower ankle skin cylinder
        bm_s = bmesh.new()
        segs = 10
        top_z = ankle_z + ankle_top * scale
        bot_z = sole_h + 0.006 * scale if shoe_style == 'sandal' else ankle_z * 0.45
        rings = []
        for i in range(4):
            u = i / 3.0
            z = bot_z + (top_z - bot_z) * u
            r = ankle_r + (calf_r - ankle_r) * (u ** 1.35)
            rings.append([
                bm_s.verts.new((ax + r * 0.96 * math.cos(a), ay + r * 1.06 * math.sin(a), z))
                for a in (k / segs * math.tau for k in range(segs))
            ])
        loft_rings(bm_s, rings, closed_u=True, cap_start=True, cap_end=True)

        if shoe_style == 'sandal':
            f_rings = []
            f_prof = [
                (heel_y * 0.85, foot_w * 0.62, ankle_z * 0.80, sole_h + 0.002),
                (ay, foot_w * 0.72, ankle_z * 0.92, sole_h),
                (-foot_l * 0.32, foot_w * 0.84, ankle_z * 0.74, sole_h),
                (-foot_l * 0.64, foot_w * 0.92, ankle_z * 0.54, sole_h),
                (-foot_l * 0.84, foot_w * 0.76, ankle_z * 0.38, sole_h + 0.002),
                (-foot_l * 0.92, foot_w * 0.42, sole_h + 0.011 * scale, sole_h + 0.004),
            ]
            for py, rw, zt, zb in f_prof:
                cz = 0.5 * (zt + zb)
                rz = max(0.004, 0.5 * (zt - zb))
                f_rings.append([
                    bm_s.verts.new((ax + math.cos(a) * rw, py, max(sole_h, cz + math.sin(a) * rz)))
                    for a in (k / segs * math.tau for k in range(segs))
                ])
            loft_rings(bm_s, f_rings, closed_u=True, cap_start=True, cap_end=True)

        sk_obj = bm_to_obj(bm_s, f'{name}_ankle_{sd}', col, skin_mat)
        R.skin_limb_chain(sk_obj, rig_obj, [f'calf_{sd}', f'foot_{sd}'], blend=0.25)
        skin_parts.append(sk_obj)

        # --- Shoe / Sandal mesh grounded flush on z = 0.0
        bm_sh = bmesh.new()
        sh_segs = 10
        if shoe_style == 'sandal':
            s_prof = [
                (heel_y * 1.05, foot_w * 0.74),
                (ay, foot_w * 0.84),
                (-foot_l * 0.34, foot_w * 0.94),
                (-foot_l * 0.68, foot_w * 1.02),
                (-foot_l * 0.90, foot_w * 0.82),
                (-foot_l * 0.98, foot_w * 0.42),
            ]
            s_rings = []
            for py, rw in s_prof:
                s_rings.append([
                    bm_sh.verts.new((ax + math.cos(a) * rw, py, max(0.0, sole_h * (0.50 + 0.50 * math.sin(a)))))
                    for a in (k / sh_segs * math.tau for k in range(sh_segs))
                ])
            loft_rings(bm_sh, s_rings, closed_u=True, cap_start=True, cap_end=True)

            # Soft rounded instep leather strap curving cleanly over the foot (zero boxy corners!)
            for y_c, half_dy, top_mul in ((-foot_l * 0.40, foot_l * 0.14, 0.80), (heel_y * 0.25, foot_l * 0.11, 0.96)):
                st_rings = []
                for y_off, puff in ((-half_dy, 0.96), (0.0, 1.03), (half_dy, 0.96)):
                    py = y_c + y_off
                    rw = foot_w * (0.94 if y_c < -0.02 else 0.84) * puff
                    top_s = ankle_z * top_mul + 0.006 * scale
                    st_rings.append([
                        bm_sh.verts.new((
                            ax + math.cos(a) * rw,
                            py,
                            sole_h * 0.65 + (max(0.0, math.sin(a)) ** 0.75) * (top_s - sole_h * 0.65),
                        ))
                        for a in (k / sh_segs * math.tau for k in range(sh_segs))
                    ])
                loft_rings(bm_sh, st_rings, closed_u=True, cap_start=False, cap_end=False)
        else:
            sh_prof = [
                (heel_y * 1.10, foot_w * 0.72, ankle_z * 0.70),
                (heel_y * 0.45, foot_w * 0.86, ankle_z * 0.90),
                (ay - foot_l * 0.14, foot_w * 0.94, ankle_z * 1.02),
                (-foot_l * 0.44, foot_w * 1.02, ankle_z * 0.84),
                (-foot_l * 0.76, foot_w * 0.94, ankle_z * 0.64),
                (-foot_l * 0.95, foot_w * 0.62, ankle_z * 0.42),
                (-foot_l * 1.02, foot_w * 0.28, ankle_z * 0.24),
            ]
            sh_rings = []
            for py, rw, zt in sh_prof:
                ring = []
                for k in range(sh_segs):
                    a = k / sh_segs * math.tau
                    ca, sa = math.cos(a), math.sin(a)
                    if sa < -0.25:
                        z = 0.0
                    elif sa < 0.0:
                        z = (sa + 0.25) / 0.25 * (zt * 0.22)
                    else:
                        z = zt * (0.22 + 0.78 * (sa ** 0.75))
                    ring.append(bm_sh.verts.new((ax + ca * rw, py, z)))
                sh_rings.append(ring)
            loft_rings(bm_sh, sh_rings, closed_u=True, cap_start=True, cap_end=True)

        sh_obj = bm_to_obj(bm_sh, f'{name}_shoe_{sd}', col, shoe_mat)
        R.skin_rigid(sh_obj, rig_obj, f'foot_{sd}')
        shoe_parts.append(sh_obj)

    return skin_parts, shoe_parts
