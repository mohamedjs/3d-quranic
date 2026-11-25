"""Stylized zero-clip garment & accessory builders (robes, vests, hijabs, turbans, shemagh, bisht, props)."""
import math
import bmesh
from mathutils import Vector, Matrix

from lib import (
    add_ring_torus,
    add_tube,
    bm_to_obj,
    loft_rings,
    smoothstep,
    uv_cylindrical,
    uv_planar_drape,
)
from body import torso_radii, _limb_frame
from head import head_shape, head_front_y
import rig as R


def _skin_robe_body(obj, rig_obj, lm, hem_z, calf_follow=0.68, seated_mode=False):
    """Skin a continuous torso+skirt robe smoothly from neck through spine, pelvis, thighs, and calves."""
    z_hip = lm['hip_z']
    z_wst = lm['waist_z']
    z_chs = lm['chest_z']
    z_nb = lm['neck_bot'].z
    z_knee = lm['knee_z']
    hip_x = lm['hip_x']
    wmap = {}

    for v in obj.data.vertices:
        p = v.co
        z = p.z
        if z >= z_wst:
            if z <= z_chs:
                t = smoothstep(z_wst, z_chs, z)
                bw = {'spine_01': 1.0 - t, 'spine_02': t}
            elif z <= z_nb:
                bw = {'spine_02': 1.0}
            else:
                t = smoothstep(z_nb, z_nb + 0.045, z)
                bw = {'spine_02': 1.0 - t, 'neck': t}
        elif z >= z_hip + 0.04:
            t = smoothstep(z_hip + 0.04, z_wst, z)
            bw = {'pelvis': 1.0 - t, 'spine_01': t}
        else:
            lr_span = hip_x * (1.05 if seated_mode else 1.32)
            w_l = smoothstep(-lr_span, lr_span, p.x)
            w_r = 1.0 - w_l
            if seated_mode:
                if z > z_knee + 0.07:
                    t_th = smoothstep(z_hip + 0.04, z_hip - 0.08, z)
                    bw = {
                        'pelvis': max(0.0, 1.0 - t_th),
                        'thigh_l': t_th * w_l,
                        'thigh_r': t_th * w_r,
                    }
                else:
                    t_cf = smoothstep(z_knee + 0.07, z_knee - 0.08, z)
                    bw = {
                        'thigh_l': (1.0 - t_cf) * w_l,
                        'thigh_r': (1.0 - t_cf) * w_r,
                        'calf_l': t_cf * w_l,
                        'calf_r': t_cf * w_r,
                    }
            else:
                t_leg = smoothstep(z_hip + 0.04, z_hip - 0.13, z)
                t_calf = smoothstep(z_knee + 0.09, z_knee - 0.10, z) * calf_follow
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
    return R._set_weights(obj, rig_obj, wmap)


def _skin_sleeve(obj, rig_obj, lm, sd):
    """Smoothly skin one sleeve from spine_02/clavicle at the shoulder cap down upperarm & lowerarm."""
    sh = lm[f'sh_{sd}']
    elb = lm[f'elb_{sd}']
    wri = lm[f'wri_{sd}']
    ua_dir = (elb - sh).normalized()
    ua_len = (elb - sh).length
    la_dir = (wri - elb).normalized()
    la_len = (wri - elb).length
    wmap = {}

    for v in obj.data.vertices:
        p = v.co
        t_ua = (p - sh).dot(ua_dir) / max(ua_len, 1e-4)
        t_la = (p - elb).dot(la_dir) / max(la_len, 1e-4)
        if t_ua <= 0.22:
            # Smoothly blend upper shoulder cap into spine_02 so arms lowering NEVER spikes the shoulder!
            f = smoothstep(-0.18, 0.24, t_ua)
            top_anchor = smoothstep(sh.z - 0.01, sh.z + 0.045, p.z)
            f *= (1.0 - 0.55 * top_anchor)
            bw = {
                'spine_02': (1.0 - f) * 0.72,
                f'clavicle_{sd}': (1.0 - f) * 0.28,
                f'upperarm_{sd}': f,
            }
        elif t_ua < 0.78:
            bw = {f'upperarm_{sd}': 1.0}
        elif t_la < 0.24:
            f = smoothstep(-0.18, 0.24, t_la)
            bw = {f'upperarm_{sd}': 1.0 - f, f'lowerarm_{sd}': f}
        else:
            bw = {f'lowerarm_{sd}': 1.0}
        wmap[v.index] = bw
    return R._set_weights(obj, rig_obj, wmap)


# ------------------------------------------------------------------ galabiya / thobe / dress
def build_galabiya(
    name,
    col,
    lm,
    p,
    mat,
    rig_obj,
    hem_z=0.05,
    ease=0.022,
    skirt_flare=0.26,
    folds=0.032,
    sleeve_end=0.80,
    sleeve_r=0.050,
    sleeve_flare=0.018,
    collar_h=0.024,
    seated_mode=False,
    trim_mat=None,
    trim_style=None,
):
    """Build a complete continuous galabiya/thobe/dress (body+skirt + sleeves + optional trim)."""
    parts = []
    h = lm['height']
    scale = h / 1.60
    z_top = lm['neck_bot'].z + collar_h * scale
    z_sh = lm['sh_z']
    z_hip = lm['hip_z']

    # --- 1) Continuous torso + flared skirt mesh (smooth & compact ~640 tris!)
    segs = 22
    zs = [
        z_top,
        lm['neck_bot'].z + 0.004 * scale,
        z_sh + 0.025 * scale,
        z_sh - 0.020 * scale,
        lm['chest_z'],
        lm['waist_z'],
        z_hip + 0.04 * scale,
        z_hip - 0.04 * scale,
    ]
    n_skirt = 9 if seated_mode else 6
    z_start = z_hip - 0.08 * scale
    for i in range(n_skirt):
        t = (i + 1) / n_skirt
        zs.append(z_start + (hem_z - z_start) * t)

    bm = bmesh.new()
    rings = []
    prev_rx, prev_ry = 0.0, 0.0
    for idx, z in enumerate(zs):
        bx, by, cy = torso_radii(lm, p, max(z, z_hip))
        if z >= z_sh + 0.01 * scale:
            t_col = smoothstep(z_sh + 0.01 * scale, z_top, z)
            # Broaden upper shoulder yoke gently so shoulders slope smoothly straight into rounded sleeves!
            rx = (bx + 0.018 * scale * (1.0 - t_col)) + ease * (1.0 - 0.45 * t_col)
            ry = by + ease * (1.0 - 0.45 * t_col)
        elif z >= z_hip:
            t_b = smoothstep(z_sh, z_hip, z)
            rx = bx + ease * (1.0 + 0.32 * t_b)
            ry = by + ease * (1.08 + 0.32 * t_b)
        else:
            t_sk = smoothstep(z_hip, hem_z, z)
            base_rx = max(bx + ease * 1.32, lm['hip_x'] * 1.72 + ease)
            base_ry = max(by + ease * 1.42, lm['pelvis_d'] + ease * 1.45)
            stride_extra = (0.045 if seated_mode else 0.026) * scale * (t_sk ** 1.1)
            rx = base_rx * (1.0 + skirt_flare * (t_sk ** 1.35))
            ry = base_ry * (1.0 + skirt_flare * 0.92 * (t_sk ** 1.35)) + stride_extra
            rx = max(rx, prev_rx)
            ry = max(ry, prev_ry)
        if z < z_hip:
            prev_rx, prev_ry = rx, ry

        t_sk_fold = smoothstep(z_hip + 0.04, hem_z, z)
        k_fold = folds * (t_sk_fold ** 1.25)
        ring = []
        for k in range(segs):
            th = k / segs * math.tau
            f = 1.0 + k_fold * (0.58 * math.sin(6.0 * th + 0.4) + 0.42 * math.sin(10.0 * th + 1.5))
            z_mod = z
            if idx == 0:
                z_mod -= 0.016 * scale * max(0.0, -math.sin(th)) ** 1.6
            py = ry * f * math.sin(th)
            # For seated_mode (Grandma Zainab), trim rear (+Y) skirt cushion so buttocks/thighs sit flush
            # at z=0.45 m on the mastaba and lower back hem hangs cleanly in front of the bench edge!
            if seated_mode and py > 0.0 and z < z_hip + 0.05 * scale:
                t_seat = smoothstep(z_hip + 0.05 * scale, z_hip - 0.10 * scale, z)
                t_low = smoothstep(lm['knee_z'] + 0.06 * scale, hem_z, z)
                back_mul = 1.0 - 0.48 * t_seat - 0.16 * t_low
                py *= back_mul
            ring.append(bm.verts.new((rx * f * math.cos(th), cy + py, z_mod)))
        rings.append(ring)

    hem_inner = [bm.verts.new((v.co.x * 0.92, v.co.y * 0.92, v.co.z + 0.020 * scale)) for v in rings[-1]]
    rings.append(hem_inner)
    collar_inner = [bm.verts.new((v.co.x * 0.88, v.co.y * 0.88, v.co.z - 0.014 * scale)) for v in rings[0]]
    rings.insert(0, collar_inner)

    loft_rings(bm, rings, closed_u=True, cap_start=False, cap_end=False)
    body_obj = bm_to_obj(bm, name + '_body', col, mat)
    _skin_robe_body(body_obj, rig_obj, lm, hem_z, calf_follow=0.72, seated_mode=seated_mode)
    parts.append(body_obj)

    # --- 2) Silky natural downward-sloping sleeves (roof-clamped to collarbone slope -> ZERO shoulder humps!)
    sl_r = sleeve_r * scale * p.get('arm_thick', 1.0)
    sl_fl = sleeve_flare * scale
    z_roof_base = lm['neck_bot'].z - 0.014 * scale
    for sd, s in (('l', 1.0), ('r', -1.0)):
        sh = lm[f'sh_{sd}']
        elb = lm[f'elb_{sd}']
        wri = lm[f'wri_{sd}']
        ua_dir = (elb - sh).normalized()
        la_dir = (wri - elb).normalized()

        # Start inside the torso shoulder and flow cleanly down the arm (narrower cap, full forearm/cuff!)
        pts = [
            sh + Vector((-s * 0.045 * scale, 0.0, -0.008 * scale)),
            sh + Vector((-s * 0.015 * scale, 0.0, -0.010 * scale)),
            sh.lerp(elb, 0.16),
            sh.lerp(elb, 0.44),
            sh.lerp(elb, 0.82),
            elb.lerp(wri, 0.16),
            elb.lerp(wri, sleeve_end * 0.68),
            elb.lerp(wri, sleeve_end),
        ]
        rad_prof = [
            sl_r * 0.62,
            sl_r * 0.82,
            sl_r * 0.90,
            sl_r * 0.92,
            sl_r * 0.92,
            sl_r * 0.96 + sl_fl * 0.25,
            sl_r * 1.02 + sl_fl * 0.68,
            sl_r * 1.08 + sl_fl * 1.00,
        ]
        bm_s = bmesh.new()
        sl_segs = 12
        sl_rings = []
        for i, (pt, rad) in enumerate(zip(pts, rad_prof)):
            t_dir = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            _, lat, fwd = _limb_frame(sh if i < 5 else elb, elb if i < 5 else wri, s)
            up_v = t_dir.cross(fwd)
            up_v = lat if up_v.length < 1e-4 else up_v.normalized()
            fwd_v = up_v.cross(t_dir).normalized()
            ring = []
            for k in range(sl_segs):
                a = k / sl_segs * math.tau
                pos = pt + up_v * (math.cos(a) * rad) + fwd_v * (math.sin(a) * rad)
                # Gently slope top shoulder cap vertices down from collarbone roof -> zero boxy/puffed humps!
                if i <= 3:
                    dist_out = max(0.0, abs(pos.x) - lm['sh_x'] * 0.45)
                    max_z = z_roof_base - 0.34 * dist_out
                    if pos.z > max_z:
                        pos.z = max_z
                ring.append(bm_s.verts.new(pos))
            sl_rings.append(ring)

        cuff_pt = pts[-1] - la_dir * (0.022 * scale)
        cuff_in = [bm_s.verts.new(cuff_pt + (v.co - pts[-1]) * 0.80) for v in sl_rings[-1]]
        sl_rings.append(cuff_in)
        loft_rings(bm_s, sl_rings, closed_u=True, cap_start=True, cap_end=False)

        sl_obj = bm_to_obj(bm_s, f'{name}_sleeve_{sd}', col, mat)
        _skin_sleeve(sl_obj, rig_obj, lm, sd)
        parts.append(sl_obj)

        if trim_mat is not None and trim_style in ('placket_cuff', 'cuff_hem', 'full'):
            bm_tc = bmesh.new()
            c_pts = [elb.lerp(wri, max(0.2, sleeve_end - 0.14)), elb.lerp(wri, sleeve_end + 0.006)]
            tc_rings = []
            for ci, cpt in enumerate(c_pts):
                r_tc = (sl_r * 1.04 + sl_fl * (0.86 + 0.16 * ci)) + 0.004 * scale
                _, _, fwd_c = _limb_frame(elb, wri, s)
                up_c = la_dir.cross(fwd_c).normalized()
                fw_c = up_c.cross(la_dir).normalized()
                tc_rings.append([
                    bm_tc.verts.new(cpt + (up_c * math.cos(a) + fw_c * math.sin(a)) * r_tc)
                    for a in (k / sl_segs * math.tau for k in range(sl_segs))
                ])
            loft_rings(bm_tc, tc_rings, closed_u=True, cap_start=False, cap_end=False)
            tc_obj = bm_to_obj(bm_tc, f'{name}_cufftrim_{sd}', col, trim_mat)
            _skin_sleeve(tc_obj, rig_obj, lm, sd)
            parts.append(tc_obj)

    # --- 3) Optional neckline embroidery / placket trim (flush closed prism, excluded from outline!)
    if trim_mat is not None and trim_style in ('placket_cuff', 'placket', 'full'):
        bm_tr = bmesh.new()
        tr_rings = []
        for z_off, dr in ((0.005 * scale, 0.0045 * scale), (-0.020 * scale, 0.0045 * scale)):
            z_c = z_top - 0.004 * scale + z_off
            bx, by, cy = torso_radii(lm, p, z_c)
            rx = bx + ease * 0.62 + dr
            ry = by + ease * 0.62 + dr
            tr_rings.append([
                bm_tr.verts.new((
                    rx * math.cos(th),
                    cy + ry * math.sin(th),
                    z_c - 0.016 * scale * max(0.0, -math.sin(th)) ** 1.6,
                ))
                for th in (k / 20 * math.tau for k in range(20))
            ])
        loft_rings(bm_tr, tr_rings, closed_u=True)

        pl_w = 0.020 * scale
        z_pl_top = z_top - 0.018 * scale
        z_pl_bot = lm['chest_z'] - 0.060 * scale
        pl_pts = []
        for i in range(6):
            u = i / 5.0
            zp = z_pl_top + (z_pl_bot - z_pl_top) * u
            bx, by, cy = torso_radii(lm, p, zp)
            ry = by + ease * (1.02 + 0.14 * u) + 0.0045 * scale
            pl_pts.append(Vector((0.0, cy - ry, zp)))
        add_tube(bm_tr, pl_pts, radius=(pl_w, 0.0045 * scale), segs=6, closed_caps=True, ref_up=Vector((0.0, -1.0, 0.0)))
        tr_obj = bm_to_obj(bm_tr, name + '_placket', col, trim_mat)
        R.skin_spine_mesh(tr_obj, rig_obj, lm, allow_neck=True)
        parts.append(tr_obj)

    return parts


# ------------------------------------------------------------------ sirwal trousers (player)
def build_trousers(name, col, lm, p, mat, rig_obj, hem_up=0.042, loose=0.026):
    """Build comfy two-legged sirwal trousers overlapping the ankle cleanly (zero gaps)."""
    scale = lm['height'] / 1.60
    z_top = lm['hip_z'] + 0.06 * scale
    z_bot = lm['ankle_z'] + hem_up * scale
    hip_x = lm['hip_x']
    leg_r = 0.048 * scale * p.get('leg_thick', 1.0) + loose * scale

    parts = []
    for sd, s in (('l', 1.0), ('r', -1.0)):
        bm = bmesh.new()
        segs = 12
        rings = []
        levels = 6
        for i in range(levels):
            u = i / (levels - 1)
            z = z_top + (z_bot - z_top) * u
            cx = s * hip_x * (0.98 - 0.04 * u)
            cy = -0.005 * math.sin(u * math.pi)
            r = leg_r * (1.16 - 0.32 * (u ** 1.15))
            rings.append([
                bm.verts.new((cx + r * math.cos(a), cy + r * 1.06 * math.sin(a), z))
                for a in (k / segs * math.tau for k in range(segs))
            ])
        in_ring = [bm.verts.new((cx + (v.co.x - cx) * 0.78, cy + (v.co.y - cy) * 0.78, z_bot + 0.016 * scale)) for v in rings[-1]]
        rings.append(in_ring)
        loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=False)
        obj = bm_to_obj(bm, f'{name}_{sd}', col, mat)
        R.skin_trousers(obj, rig_obj, lm)
        parts.append(obj)
    return parts


# ------------------------------------------------------------------ waist sash / belt
def build_sash(name, col, lm, p, mat, rig_obj, ease=0.032, height=0.075, tails=True, tail_side=1.0, accent_mat=None):
    """Build a soft wrapped woven cloth sash around the waist with optional hanging side tails."""
    scale = lm['height'] / 1.60
    z_c = lm['waist_z'] - 0.015 * scale
    hh = height * 0.5 * scale
    segs = 20

    bm = bmesh.new()
    rings = []
    for i in range(4):
        u = i / 3.0
        z = z_c + hh - 2.0 * hh * u
        bx, by, cy = torso_radii(lm, p, z)
        puff = ease + 0.008 * scale * math.sin(u * math.pi)
        rx = bx + puff
        ry = by + puff * 1.08
        rings.append([
            bm.verts.new((rx * math.cos(th), cy + ry * math.sin(th), z))
            for th in (k / segs * math.tau for k in range(segs))
        ])
    loft_rings(bm, rings, closed_u=True)
    parts = [R.skin_spine_mesh(bm_to_obj(bm, name + '_band', col, mat), rig_obj, lm)]

    if tails:
        bm_t = bmesh.new()
        bx, by, cy = torso_radii(lm, p, z_c)
        kx = tail_side * (bx + ease + 0.014 * scale) * 0.80
        ky = cy - (by + ease + 0.015 * scale) * 0.72
        ret = bmesh.ops.create_uvsphere(bm_t, u_segments=8, v_segments=6, radius=0.022 * scale)
        for v in ret['verts']:
            v.co = Vector((kx + v.co.x * 1.12, ky + v.co.y * 0.82, z_c + v.co.z * 0.92))
        for off_x, length, spread in ((-0.014, 0.22, -0.018), (0.014, 0.27, 0.024)):
            pts = []
            for i in range(5):
                u = i / 4.0
                zt = z_c - length * scale * u
                bx_t, by_t, cy_t = torso_radii(lm, p, max(zt, lm['hip_z']))
                flare = 1.0 + 0.24 * (u ** 1.2)
                px = kx + (off_x + spread * u) * scale * (1.0 + 0.18 * u)
                py = min(ky - 0.010 * scale * u, cy_t - (by_t + ease + 0.022 * scale) * flare * 0.78)
                pts.append(Vector((px, py, zt)))
            add_tube(
                bm_t,
                pts,
                radius=lambda u: (0.018 * scale * (0.75 + 0.40 * u), 0.007 * scale),
                segs=6,
                closed_caps=True,
                ref_up=Vector((0.0, -1.0, 0.0)),
            )
        t_obj = bm_to_obj(bm_t, name + '_tails', col, accent_mat or mat)
        R.skin_skirt(t_obj, rig_obj, lm, z_c + 0.04, z_c - 0.30 * scale, calf_follow=0.15)
        parts.append(t_obj)

    return parts


# ------------------------------------------------------------------ vest / waistcoat (farmer)
def build_vest(name, col, lm, p, mat, rig_obj, ease=0.048, button_mat=None):
    """Build an open-V traditional Egyptian waistcoat (sadiri) fitted cleanly outside the galabiya."""
    scale = lm['height'] / 1.60
    z_top = lm['neck_bot'].z + 0.008 * scale
    z_bot = lm['hip_z'] - 0.02 * scale
    segs = 18

    bm = bmesh.new()
    rings = []
    levels = 7
    for i in range(levels):
        u = i / (levels - 1)
        z = z_top + (z_bot - z_top) * u
        bx, by, cy = torso_radii(lm, p, max(z, lm['hip_z']))
        # Match galabiya bodice silhouette + generous clearance everywhere -> ZERO brown poking through!
        rx = bx + ease * (0.95 + 0.35 * u)
        ry = by + ease * (1.05 + 0.38 * u)
        gap = 0.54 * (1.0 - smoothstep(0.0, 0.50, u)) + 0.08
        a0 = -math.pi * 0.5 + gap
        a1 = -math.pi * 0.5 + math.tau - gap
        ring = []
        for k in range(segs + 1):
            th = a0 + (a1 - a0) * (k / segs)
            ring.append(bm.verts.new((rx * math.cos(th), cy + ry * math.sin(th), z)))
        rings.append(ring)

    rings_in = []
    for ring in rings:
        rings_in.append([bm.verts.new((v.co.x * 0.94, v.co.y * 0.94, v.co.z)) for v in ring])

    loft_rings(bm, rings, closed_u=False)
    n = segs + 1
    for r0, r1 in zip(rings_in, rings_in[1:]):
        for k in range(n - 1):
            bm.faces.new((r0[k + 1], r0[k], r1[k], r1[k + 1]))
    for i in range(levels - 1):
        bm.faces.new((rings[i][0], rings_in[i][0], rings_in[i + 1][0], rings[i + 1][0]))
        bm.faces.new((rings[i][-1], rings[i + 1][-1], rings_in[i + 1][-1], rings_in[i][-1]))
    for k in range(n - 1):
        bm.faces.new((rings[0][k], rings[0][k + 1], rings_in[0][k + 1], rings_in[0][k]))
        bm.faces.new((rings[-1][k + 1], rings[-1][k], rings_in[-1][k], rings_in[-1][k + 1]))

    vest_obj = bm_to_obj(bm, name, col, mat)
    R.skin_spine_mesh(vest_obj, rig_obj, lm, allow_neck=False)
    parts = [vest_obj]

    if button_mat is not None:
        bm_b = bmesh.new()
        for u in (0.54, 0.69, 0.84):
            zb = z_top + (z_bot - z_top) * u
            bx, by, cy = torso_radii(lm, p, max(zb, lm['hip_z']))
            yb = cy - (by + ease * (1.05 + 0.38 * u)) - 0.005 * scale
            for s in (1.0, -1.0):
                ret = bmesh.ops.create_uvsphere(bm_b, u_segments=8, v_segments=6, radius=0.009 * scale)
                for v in ret['verts']:
                    v.co = Vector((s * 0.022 * scale + v.co.x, yb + v.co.y * 0.55, zb + v.co.z))
        b_obj = bm_to_obj(bm_b, name + '_buttons', col, button_mat)
        R.skin_spine_mesh(b_obj, rig_obj, lm)
        parts.append(b_obj)
    return parts


def build_shoulder_scarf(name, col, lm, p, mat, rig_obj, side=-1.0, ease=0.062):
    """Build a flat, soft folded woven village scarf resting snugly across one shoulder (zero fin!)."""
    scale = lm['height'] / 1.60
    sh_z = lm['sh_z']
    sh_x = lm['sh_x']
    sx = side * sh_x * 0.58
    bx_s, by_s, cy_s = torso_radii(lm, p, sh_z)
    bx_c, by_c, cy_c = torso_radii(lm, p, lm['chest_z'])
    bx_w, by_w, cy_w = torso_radii(lm, p, lm['waist_z'])

    pts = [
        Vector((sx * 0.96, cy_w - by_w - ease - 0.010 * scale, lm['waist_z'] - 0.04 * scale)),
        Vector((sx * 0.98, cy_c - by_c - ease - 0.006 * scale, lm['chest_z'] - 0.01 * scale)),
        Vector((sx * 1.00, cy_s - by_s * 0.78 - ease * 0.85, sh_z + 0.010 * scale)),
        Vector((sx * 0.98, 0.004, lm['neck_bot'].z + 0.006 * scale)),
        Vector((sx * 1.00, cy_s + by_s * 0.80 + ease * 0.85, sh_z + 0.006 * scale)),
        Vector((sx * 0.98, cy_c + by_c + ease + 0.006 * scale, lm['chest_z'] - 0.03 * scale)),
        Vector((sx * 0.95, cy_w + by_w + ease + 0.010 * scale, lm['waist_z'] - 0.02 * scale)),
    ]
    # Build flat ribbon directly with lateral X = wide (0.044) and surface-normal = thin (0.010)!
    bm = bmesh.new()
    segs = 8
    rings = []
    n_pts = len(pts)
    for i, pt in enumerate(pts):
        u = i / (n_pts - 1)
        t_vec = (pts[min(i + 1, n_pts - 1)] - pts[max(i - 1, 0)]).normalized()
        lat = Vector((1.0, 0.0, 0.0))
        lat = (lat - t_vec * lat.dot(t_vec)).normalized()
        nrm = t_vec.cross(lat).normalized()
        rw = 0.044 * scale * (1.0 + 0.14 * abs(u - 0.5))
        rt = 0.010 * scale
        rings.append([
            bm.verts.new(pt + lat * (math.cos(a) * rw) + nrm * (math.sin(a) * rt))
            for a in (k / segs * math.tau for k in range(segs))
        ])
    loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)
    obj = bm_to_obj(bm, name, col, mat)
    uv_cylindrical(obj, scale_u=4.0, scale_v=6.0)
    return R.skin_spine_mesh(obj, rig_obj, lm)


# ------------------------------------------------------------------ open bisht / kaftan
def build_open_robe(
    name,
    col,
    lm,
    p,
    mat,
    rig_obj,
    trim_mat=None,
    hem_z=0.07,
    ease=0.042,
    skirt_flare=0.30,
    open_rad=0.42,
    sleeve_end=0.72,
    sleeve_r=0.068,
    sleeve_flare=0.032,
):
    """Build an open-front outer bisht or scholarly kaftan cleanly layered outside the thobe."""
    scale = lm['height'] / 1.60
    z_top = lm['neck_bot'].z + 0.015 * scale
    z_sh = lm['sh_z']
    z_hip = lm['hip_z']

    zs = [
        z_top,
        z_sh + 0.02 * scale,
        z_sh - 0.03 * scale,
        lm['chest_z'],
        lm['waist_z'],
        z_hip + 0.04 * scale,
        z_hip - 0.04 * scale,
    ]
    for i in range(5):
        t = (i + 1) / 5.0
        zs.append((z_hip - 0.06 * scale) + (hem_z - (z_hip - 0.06 * scale)) * t)

    segs = 18
    bm = bmesh.new()
    rings = []
    rings_in = []
    prev_rx, prev_ry = 0.0, 0.0
    for idx, z in enumerate(zs):
        bx, by, cy = torso_radii(lm, p, max(z, z_hip))
        if z >= z_hip:
            t_b = smoothstep(z_top, z_hip, z)
            rx = bx + ease * (0.85 + 0.45 * t_b)
            ry = by + ease * (0.95 + 0.45 * t_b)
        else:
            t_sk = smoothstep(z_hip, hem_z, z)
            rx = max(prev_rx, (bx + ease * 1.32) * (1.0 + skirt_flare * (t_sk ** 1.3)))
            ry = max(prev_ry, (by + ease * 1.42) * (1.0 + skirt_flare * 0.90 * (t_sk ** 1.3)) + 0.032 * scale * t_sk)
        if z < z_hip:
            prev_rx, prev_ry = rx, ry

        # Open front gap widens slightly toward the hem for dramatic flowing bisht/kaftan lines
        t_all = idx / max(1, len(zs) - 1)
        gap = open_rad * (0.85 + 0.35 * t_all)
        a0 = -math.pi * 0.5 + gap
        a1 = -math.pi * 0.5 + math.tau - gap
        k_fold = 0.028 * (t_all ** 1.3)
        ring = []
        rin = []
        for k in range(segs + 1):
            th = a0 + (a1 - a0) * (k / segs)
            f = 1.0 + k_fold * math.sin(6.0 * th + 0.3)
            px = rx * f * math.cos(th)
            py = cy + ry * f * math.sin(th)
            ring.append(bm.verts.new((px, py, z)))
            rin.append(bm.verts.new((px * 0.95, cy + (py - cy) * 0.95, z)))
        rings.append(ring)
        rings_in.append(rin)

    loft_rings(bm, rings, closed_u=False)
    n = segs + 1
    for r0, r1 in zip(rings_in, rings_in[1:]):
        for k in range(n - 1):
            bm.faces.new((r0[k + 1], r0[k], r1[k], r1[k + 1]))
    for i in range(len(zs) - 1):
        bm.faces.new((rings[i][0], rings_in[i][0], rings_in[i + 1][0], rings[i + 1][0]))
        bm.faces.new((rings[i][-1], rings[i + 1][-1], rings_in[i + 1][-1], rings_in[i][-1]))
    for k in range(n - 1):
        bm.faces.new((rings[0][k], rings[0][k + 1], rings_in[0][k + 1], rings_in[0][k]))
        bm.faces.new((rings[-1][k + 1], rings[-1][k], rings_in[-1][k], rings_in[-1][k + 1]))

    # Extract front-edge & collar paths BEFORE bm_to_obj frees bm!
    trim_paths = None
    if trim_mat is not None:
        trim_paths = (
            [r[0].co.copy() for r in rings],
            [r[-1].co.copy() for r in rings],
            [v.co.copy() for v in rings[0]],
        )

    cloak_obj = bm_to_obj(bm, name + '_cloak', col, mat)
    _skin_robe_body(cloak_obj, rig_obj, lm, hem_z, calf_follow=0.68)
    parts = [cloak_obj]

    # Wide outer sleeves with roof-clamped smooth shoulder slope (sits cleanly 10 mm above inner thobe sleeve!)
    sl_r = sleeve_r * scale * p.get('arm_thick', 1.0)
    sl_fl = sleeve_flare * scale
    z_roof_base = lm['neck_bot'].z - 0.003 * scale
    for sd, s in (('l', 1.0), ('r', -1.0)):
        sh = lm[f'sh_{sd}']
        elb = lm[f'elb_{sd}']
        wri = lm[f'wri_{sd}']
        la_dir = (wri - elb).normalized()
        pts = [
            sh + Vector((-s * 0.056 * scale, 0.0, -0.008 * scale)),
            sh + Vector((-s * 0.018 * scale, 0.0, -0.008 * scale)),
            sh.lerp(elb, 0.22),
            sh.lerp(elb, 0.58),
            sh.lerp(elb, 0.90),
            elb.lerp(wri, 0.28),
            elb.lerp(wri, sleeve_end),
        ]
        rads = [sl_r * 0.62, sl_r * 0.80, sl_r * 0.88, sl_r * 0.94, sl_r * 0.98, sl_r * 1.04 + sl_fl * 0.5, sl_r * 1.12 + sl_fl]
        bm_s = bmesh.new()
        sl_segs = 12
        sl_rings = []
        for i, (pt, rad) in enumerate(zip(pts, rads)):
            t_dir = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            _, lat, fwd = _limb_frame(sh if i < 5 else elb, elb if i < 5 else wri, s)
            up_v = t_dir.cross(fwd)
            up_v = lat if up_v.length < 1e-4 else up_v.normalized()
            fwd_v = up_v.cross(t_dir).normalized()
            ring = []
            for k in range(sl_segs):
                a = k / sl_segs * math.tau
                pos = pt + (up_v * math.cos(a) + fwd_v * math.sin(a)) * rad
                if i <= 3:
                    dist_out = max(0.0, abs(pos.x) - lm['sh_x'] * 0.42)
                    max_z = z_roof_base - 0.28 * dist_out
                    if pos.z > max_z:
                        pos.z = max_z
                ring.append(bm_s.verts.new(pos))
            sl_rings.append(ring)
        cuff_pt = pts[-1] - la_dir * (0.025 * scale)
        sl_rings.append([bm_s.verts.new(cuff_pt + (v.co - pts[-1]) * 0.85) for v in sl_rings[-1]])
        loft_rings(bm_s, sl_rings, closed_u=True, cap_start=True, cap_end=False)
        sl_obj = bm_to_obj(bm_s, f'{name}_sleeve_{sd}', col, mat)
        _skin_sleeve(sl_obj, rig_obj, lm, sd)
        parts.append(sl_obj)

    # Gleaming gold/piped zari border framing both front edges and collar!
    if trim_paths is not None:
        bm_t = bmesh.new()
        for path in trim_paths:
            nudged = [Vector((pt.x * 1.015, pt.y * 1.015, pt.z)) for pt in path]
            add_tube(bm_t, nudged, radius=0.013 * scale, segs=5, closed_caps=True)
        t_obj = bm_to_obj(bm_t, name + '_trim', col, trim_mat)
        _skin_robe_body(t_obj, rig_obj, lm, hem_z, calf_follow=0.68)
        parts.append(t_obj)

    return parts


# ------------------------------------------------------------------ hijab / tarha (women)
def build_hijab(
    name,
    col,
    lm,
    p,
    F,
    mat,
    rig_obj,
    trim_mat=None,
    drop_front=0.22,
    drop_back=0.30,
    asymmetric_tail=False,
    bun_puff=0.22,
):
    """Build a modest, graceful fabric hijab/tarha (plush rolled front edge + chin/shoulder folds + drape)."""
    C = lm['head_center']
    R_h = lm['head_r']
    scale = lm['height'] / 1.60
    parts = []

    # --- 1) Sculpted head wrap with smooth 32-seg crown, thick rounded rolled front edge & soft back bun
    bm_h = bmesh.new()
    u_segs = 32
    v_segs = 11
    face_rx = 0.78
    face_top = 0.45
    face_bot = -0.96
    face_cz = 0.5 * (face_top + face_bot)
    face_rz = 0.5 * (face_top - face_bot)

    rings = []
    open_pts = []
    for i in range(u_segs):
        a = i / u_segs * math.tau
        fx = face_rx * math.cos(a)
        fz = face_cz + face_rz * math.sin(a)
        f_surf = head_front_y(F, fx, fz)
        d_open = Vector((fx, f_surf.y, fz)).normalized()
        open_pts.append((a, d_open, head_shape(d_open, F)))

    # 3-ring plush rolled fabric front edge (tuck -> thick rounded front roll -> smooth outer crest)
    rim_in = []
    rim_lip = []
    rim_outer = []
    for a, d_open, p_head in open_pts:
        brow_w = max(0.0, math.sin(a)) ** 1.25
        chin_w = max(0.0, -math.sin(a)) ** 1.25
        # Soft gentle scarf-overlap swell across upper-left temple so it reads as folded woven cloth
        wrap_swell = 0.032 * math.exp(-(((a - 1.08 + math.pi) % math.tau - math.pi) / 0.58) ** 2)
        p_tuck = p_head + d_open * (0.028 + 0.010 * brow_w) + Vector((0.0, 0.024, 0.0))
        p_roll = (
            p_head
            + d_open * (0.125 + 0.042 * brow_w + wrap_swell)
            + Vector((0.0, -0.068 - 0.028 * brow_w - 0.022 * chin_w, -0.056 * chin_w))
        )
        p_crest = (
            p_head
            + d_open * (0.158 + 0.036 * brow_w + wrap_swell * 0.85)
            + Vector((0.0, -0.032 - 0.012 * brow_w - 0.018 * chin_w, -0.042 * chin_w))
        )
        rim_in.append(bm_h.verts.new(C + p_tuck * R_h))
        rim_lip.append(bm_h.verts.new(C + p_roll * R_h))
        rim_outer.append(bm_h.verts.new(C + p_crest * R_h))

    rings.append(rim_in)
    rings.append(rim_lip)
    rings.append(rim_outer)

    # Sweep from behind the plush rolled edge over crown & bun to smooth back cap
    d_back = Vector((0.0, 1.0, -0.04)).normalized()
    for j in range(1, v_segs + 1):
        tv = 0.06 + (j / v_segs) * 0.87
        ring = []
        for i in range(u_segs):
            a, d_open, _ = open_pts[i]
            ang = d_open.angle(d_back)
            if ang < 1e-4:
                sdir = d_back
            else:
                sa = math.sin(ang)
                sdir = (d_open * math.sin((1.0 - tv) * ang) + d_back * math.sin(tv * ang)) / sa
                sdir.normalize()

            p_head = head_shape(sdir, F)
            bun = bun_puff * math.exp(-((sdir.y - 0.88) / 0.36) ** 2 - ((sdir.z + 0.05) / 0.42) ** 2)
            # Soft organic cloth wrap folds arcing subtly across crown & sides
            fold = (
                0.024 * math.sin(tv * 4.0 * math.pi + 0.7 * math.cos(a - 0.4)) * smoothstep(0.06, 0.30, tv)
                + 0.014 * math.cos(3.0 * a + 2.2 * tv) * smoothstep(0.08, 0.36, tv)
            )
            thick = 0.146 + 0.038 * smoothstep(0.06, 0.38, tv) + bun + fold
            p_out = p_head + sdir * thick
            if math.sin(a) < -0.45 and tv < 0.32:
                chin_f = (-math.sin(a) - 0.45) / 0.55
                p_out.z -= 0.072 * chin_f * (1.0 - tv / 0.32)
                p_out.y -= 0.032 * chin_f * (1.0 - tv / 0.32)
            ring.append(bm_h.verts.new(C + p_out * R_h))
        rings.append(ring)

    # Smooth spherical back-cap close (zero pole star pinch!)
    back_c = sum((v.co for v in rings[-1]), Vector()) / u_segs
    back_n = (back_c - C).normalized()
    rings.append([bm_h.verts.new(back_c.lerp(v.co, 0.42) + back_n * (0.018 * R_h)) for v in rings[-1]])

    loft_rings(bm_h, rings, closed_u=True, cap_start=False, cap_end=True)

    rim_pts = None
    if trim_mat is not None:
        # Clean continuous upper arch framing forehead & cheeks flush along the plush rolled edge
        ordered = []
        for i in range(u_segs):
            a = i / u_segs * math.tau
            if a > math.pi * 1.5:
                a -= math.tau
            if -math.pi * 0.22 <= a <= math.pi * 1.22:
                ordered.append((a, rings[1][i].co.copy() + Vector((0.0, -0.004 * scale, 0.0))))
        ordered.sort(key=lambda pair: pair[0])
        rim_pts = [pt for _, pt in ordered]
    head_wrap = bm_to_obj(bm_h, name + '_head', col, mat)
    R.skin_rigid(head_wrap, rig_obj, 'head')
    parts.append(head_wrap)

    if rim_pts:
        bm_tr = bmesh.new()
        add_tube(bm_tr, rim_pts, radius=0.0075 * scale, segs=5, closed_caps=True)
        tr_h = bm_to_obj(bm_tr, name + '_head_trim', col, trim_mat)
        R.skin_rigid(tr_h, rig_obj, 'head')
        parts.append(tr_h)

    # --- 2) Flowing modest shoulder drape with crisp sculpted chin & shoulder fabric folds (zero harsh tubes!)
    sh_z = lm['sh_z']
    z_nb = lm['neck_bot'].z
    z_top_d = C.z - R_h * 0.72
    neck_r = R_h * 0.70
    bx_s, by_s, cy_s = torso_radii(lm, p, sh_z)
    bx_c, by_c, cy_c = torso_radii(lm, p, lm['chest_z'])
    bx_w, by_w, cy_w = torso_radii(lm, p, lm['waist_z'])

    # Dense smooth vertical profile (12 rings) so the sculpted chin-wrap & shoulder-drape folds
    # create genuine downward-tilted shadow undersides and upward-tilted sunlit fabric ridges!
    ctrl_levels = [
        # (z_base, rx, ry, cy, t_drop, side_slope)
        (z_top_d, neck_r, neck_r * 1.04, C.y + 0.008 * scale, 0.00, 0.00),
        (C.z - R_h * 0.94, neck_r * 1.14, neck_r * 1.18, C.y + 0.002 * scale, 0.04, 0.00),
        (z_nb + 0.022 * scale, neck_r * 1.32, neck_r * 1.36, 0.002, 0.10, 0.004),
        (z_nb - 0.004 * scale, lm['sh_x'] * 0.68 + 0.028 * scale, by_s + 0.074 * scale, cy_s, 0.19, 0.012),
        (z_nb - 0.024 * scale, lm['sh_x'] * 0.94 + 0.046 * scale, by_s + 0.092 * scale, cy_s, 0.31, 0.020),
        (sh_z - 0.020 * scale, lm['sh_x'] + 0.068 * scale, by_c + 0.100 * scale, cy_c, 0.48, 0.022),
        (sh_z - 0.066 * scale, lm['sh_x'] + 0.078 * scale, by_c + 0.105 * scale, cy_c, 0.74, 0.015),
        (sh_z - 0.112 * scale, lm['sh_x'] + 0.084 * scale, by_w + 0.107 * scale, cy_w, 1.00, 0.008),
    ]
    # Subdivide upper/mid drape smoothly to 13 rings so folds read crisply under cel-shading!
    levels = []
    for idx in range(len(ctrl_levels) - 1):
        a0, a1 = ctrl_levels[idx], ctrl_levels[idx + 1]
        levels.append(a0)
        if idx in (1, 2, 3, 4, 5):
            levels.append(tuple(0.5 * (x + y) for x, y in zip(a0, a1)))
    levels.append(ctrl_levels[-1])

    bm_d = bmesh.new()
    d_segs = 32
    d_rings = []
    for z, rx, ry, cy, t, s_slope in levels:
        ring = []
        for k in range(d_segs):
            th = k / d_segs * math.tau
            front_w = max(0.0, -math.sin(th))
            back_w = max(0.0, math.sin(th))
            side_w = abs(math.cos(th)) ** 1.4

            # Subtle sculpted cloth drapery ripples integrated into the drape surface
            t1_c = 0.14 + 0.14 * math.cos(th)
            u1 = (t - t1_c) / 0.065
            fold1 = (0.012 * math.exp(-u1 * u1) - 0.006 * math.exp(-((t - (t1_c + 0.07)) / 0.055) ** 2))
            fold1 *= scale * (0.20 + 0.80 * front_w) * smoothstep(0.01, 0.06, t)

            t2_c = 0.42 - 0.18 * math.cos(th)
            u2 = (t - t2_c) / 0.085
            fold2 = (0.016 * math.exp(-u2 * u2) - 0.008 * math.exp(-((t - (t2_c + 0.09)) / 0.070) ** 2))
            fold2 *= scale * (0.25 + 0.75 * front_w) * smoothstep(0.14, 0.26, t)

            flute = 1.0 + 0.032 * t * (0.62 * math.sin(6.0 * th + 0.6) + 0.38 * math.cos(10.0 * th))
            dr = fold1 + fold2
            drop = t * (drop_front * (front_w ** 1.25) + drop_back * (back_w ** 1.25)) * scale
            drop += s_slope * side_w * scale
            if asymmetric_tail:
                dth = (th + math.pi * 0.28 + math.pi) % math.tau - math.pi
                drop += t * 0.085 * scale * math.exp(-(dth / 0.65) ** 2)
            ring.append(bm_d.verts.new((
                (rx * flute + dr * 0.55) * math.cos(th),
                cy + (ry * flute + dr) * math.sin(th),
                z - drop + 0.18 * dr,
            )))
        d_rings.append(ring)

    # Turned-in hem edge for rich cloth volume
    d_in = [bm_d.verts.new((v.co.x * 0.93, v.co.y * 0.93, v.co.z + 0.016 * scale)) for v in d_rings[-1]]
    d_rings.append(d_in)
    loft_rings(bm_d, d_rings, closed_u=True, cap_start=False, cap_end=False)

    hem_pts = [v.co.copy() for v in d_rings[-2]] if trim_mat is not None else None
    # Sample surface points on the drape along two gentle flush-hugging cloth fold arcs BEFORE bm_to_obj!
    def _sample_drape(ring_i, th_rad, out_pad):
        # Smooth linear interpolation around d_rings[ring_i] at angle th_rad
        u_k = (th_rad % math.tau) / math.tau * d_segs
        k0 = int(u_k) % d_segs
        k1 = (k0 + 1) % d_segs
        frac = u_k - math.floor(u_k)
        pt = d_rings[ring_i][k0].co.lerp(d_rings[ring_i][k1].co, frac)
        radial = Vector((pt.x, pt.y - cy_s, 0.0))
        if radial.length > 1e-4:
            pt = pt + radial.normalized() * out_pad
        return pt

    # Fold 1: gentle crescent scarf fold cradling softly under the chin & tapering onto left shoulder
    # Fold 2: subtle lower drapery pleat sweeping across upper chest toward right shoulder
    # Built as flush low-profile rounded cloth folds WITHOUT ink outline (0.0) so they read as pure soft fabric!
    fold_specs = [
        # ([(ring_idx, th_deg, pad_m), ...], half_width, half_thick)
        ([
            (1, -142.0, 0.002 * scale),
            (2, -112.0, 0.009 * scale),
            (3,  -84.0, 0.011 * scale),
            (4,  -56.0, 0.010 * scale),
            (5,  -28.0, 0.007 * scale),
            (6,   -4.0, 0.001 * scale),
        ], 0.022 * scale, 0.009 * scale),
        ([
            (5,  -58.0, 0.002 * scale),
            (6,  -82.0, 0.010 * scale),
            (7, -108.0, 0.012 * scale),
            (8, -134.0, 0.009 * scale),
            (9, -158.0, 0.002 * scale),
        ], 0.026 * scale, 0.010 * scale),
    ]
    fold_curves = [
        ([_sample_drape(ri, math.radians(deg), pad) for ri, deg, pad in spec], hw, ht)
        for spec, hw, ht in fold_specs
    ]

    drape_obj = bm_to_obj(bm_d, name + '_drape', col, mat)
    R.skin_cape_drape(drape_obj, rig_obj, lm, z_top_d, sh_z)
    parts.append(drape_obj)

    bm_fl = bmesh.new()
    for pts, hw, ht in fold_curves:
        add_tube(
            bm_fl,
            pts,
            radius=lambda u, hw=hw, ht=ht: (
                hw * (0.35 + 0.65 * math.sin(u * math.pi)),
                ht * (0.28 + 0.72 * math.sin(u * math.pi)),
            ),
            segs=8,
            closed_caps=True,
            ref_up=Vector((0.0, -1.0, 0.35)),
        )
    fold_obj = bm_to_obj(bm_fl, name + '_folds', col, mat)
    R.skin_cape_drape(fold_obj, rig_obj, lm, z_top_d, sh_z)
    parts.append(fold_obj)

    if hem_pts is not None:
        bm_td = bmesh.new()
        hem_pts.append(hem_pts[0])
        add_tube(bm_td, hem_pts, radius=0.0085 * scale, segs=5, closed_caps=False)
        td_obj = bm_to_obj(bm_td, name + '_drape_trim', col, trim_mat)
        R.skin_cape_drape(td_obj, rig_obj, lm, z_top_d, sh_z)
        parts.append(td_obj)

    return parts


# ------------------------------------------------------------------ turban / imama (farmer, sheikh)
def build_turban(name, col, lm, F, mat, rig_obj, tarboush_mat=None, wraps=5, puff=0.22):
    """Build a richly layered storybook Egyptian turban (or Azhari imama over crimson tarboush)."""
    C = lm['head_center']
    R_h = lm['head_r']
    parts = []

    if tarboush_mat is not None:
        bm_f = bmesh.new()
        segs = 20
        f_rings = []
        for i, (zf, rad_m) in enumerate(((0.52, 0.98), (0.76, 0.96), (1.02, 0.90), (1.24, 0.82), (1.36, 0.62), (1.40, 0.20))):
            f_rings.append([
                bm_f.verts.new(C + Vector((rad_m * math.cos(th), 0.04 + rad_m * 1.02 * math.sin(th), zf)) * R_h)
                for th in (k / segs * math.tau for k in range(segs))
            ])
        loft_rings(bm_f, f_rings, closed_u=True, cap_start=True, cap_end=True)
        fez_obj = bm_to_obj(bm_f, name + '_tarboush', col, tarboush_mat)
        R.skin_rigid(fez_obj, rig_obj, 'head')
        parts.append(fez_obj)

    bm = bmesh.new()
    top_phi = math.radians(54.0) if tarboush_mat is not None else math.radians(88.0)
    u_segs, v_segs = 22, 9
    dome_rings = []
    for j in range(v_segs + 1):
        tv = j / v_segs
        ring = []
        for i in range(u_segs):
            th = i / u_segs * math.tau
            front_f = max(0.0, -math.sin(th))
            back_f = max(0.0, math.sin(th))
            # Lower rim sits proudly above eyebrows so Grandpa Salim & Sheikh Younis's 3D brows shine!
            z_rim = 0.56 * front_f - 0.12 * back_f + 0.18 * abs(math.cos(th))
            phi0 = math.asin(max(-0.45, min(0.76, z_rim)))
            phi = phi0 + (top_phi - phi0) * tv
            sdir = Vector((math.cos(phi) * math.cos(th), math.cos(phi) * math.sin(th), math.sin(phi)))
            p_h = head_shape(sdir, F)
            p_out = p_h + sdir * (puff * (0.72 + 0.36 * math.sin(tv * math.pi * 0.85)))
            ring.append(bm.verts.new(C + p_out * R_h))
        dome_rings.append(ring)
    loft_rings(bm, dome_rings, closed_u=True, cap_start=True, cap_end=(tarboush_mat is None))

    for w in range(wraps):
        t = w / max(1, wraps - 1)
        z_w = (0.56 + 0.44 * t) if tarboush_mat is None else (0.56 + 0.36 * t)
        rx = (0.98 + puff * 0.62) * (1.0 - 0.14 * (t ** 1.35)) * R_h
        ry = (1.03 + puff * 0.65) * (1.0 - 0.14 * (t ** 1.35)) * R_h
        tube_r = (0.140 - 0.016 * t) * R_h if tarboush_mat is None else (0.118 - 0.012 * t) * R_h
        tilt = (0.08 if w % 2 == 0 else -0.07) * R_h * (1.0 - 0.25 * t)
        add_ring_torus(
            bm,
            C + Vector((0.0, 0.03 * R_h, 0.0)),
            rx,
            ry,
            C.z + z_w * R_h,
            tube_rx=tube_r * 1.02,
            tube_rz=tube_r * 0.84,
            tilt=tilt,
            phase=w * 0.72,
            segs=18,
            tsegs=6,
            bulge=0.09,
        )

    turb_obj = bm_to_obj(bm, name, col, mat)
    R.skin_rigid(turb_obj, rig_obj, 'head')
    parts.append(turb_obj)
    return parts


# ------------------------------------------------------------------ shemagh + agal (trader)
def build_shemagh_and_agal(name, col, lm, p, F, shemagh_mat, agal_mat, gold_mat, rig_obj):
    """Build a crisp woven red-white shemagh with clean shoulder wings + glossy black/gold agal."""
    C = lm['head_center']
    R_h = lm['head_r']
    scale = lm['height'] / 1.60
    parts = []

    # --- 1) Shemagh head wrap (covers crown, sides, and back cleanly — ZERO front throat band!)
    bm_h = bmesh.new()
    u_segs = 22
    v_segs = 10
    rings = []
    # Sweep from open horseshoe face framing (front brow + cheeks) over crown & back
    for j in range(v_segs + 1):
        tv = j / v_segs
        ring = []
        for i in range(u_segs):
            # Parameterize around face opening: front brow at a=pi/2, sides at 0/pi, open gap at bottom
            a = -math.pi * 0.26 + (math.pi * 1.52) * (i / (u_segs - 1))
            fx = 0.84 * math.cos(a)
            fz = 0.48 * math.sin(a) + 0.06
            f_surf = head_front_y(F, max(-0.92, min(0.92, fx)), max(-0.85, min(0.85, fz)))
            d_open = Vector((fx, f_surf.y, fz)).normalized()
            d_back = Vector((0.0, 1.0, -0.05)).normalized()
            ang = d_open.angle(d_back)
            sa = max(1e-4, math.sin(ang))
            sdir = (d_open * math.sin((1.0 - tv) * ang) + d_back * math.sin(tv * ang)) / sa
            sdir.normalize()
            p_h = head_shape(sdir, F)
            thick = 0.115 + 0.045 * smoothstep(0.0, 0.4, tv)
            ring.append(bm_h.verts.new(C + (p_h + sdir * thick) * R_h))
        rings.append(ring)

    loft_rings(bm_h, rings, closed_u=False)
    head_sh = bm_to_obj(bm_h, name + '_head', col, shemagh_mat)
    uv_cylindrical(head_sh, center=(0.0, 0.02 * scale), scale_u=2.6, scale_v=5.4)
    R.skin_rigid(head_sh, rig_obj, 'head')
    parts.append(head_sh)

    # --- 2) Flowing draped shemagh side & back tails (clears bisht back 100%, seamless check UVs!)
    sh_z = lm['sh_z']
    z_top_d = C.z - R_h * 0.24
    bx_s, by_s, cy_s = torso_radii(lm, p, sh_z)
    bx_c, by_c, cy_c = torso_radii(lm, p, lm['chest_z'])
    open_front = 0.88
    a0 = -math.pi * 0.5 + open_front
    a1 = -math.pi * 0.5 + math.tau - open_front

    levels = [
        (z_top_d, R_h * 0.96, R_h * 1.02, C.y + 0.02 * scale, 0.0),
        (lm['neck_bot'].z + 0.032 * scale, R_h * 1.08, R_h * 1.14, 0.018 * scale, 0.18),
        (sh_z + 0.048 * scale, lm['sh_x'] + 0.088 * scale, by_s + 0.124 * scale, cy_s + 0.024 * scale, 0.46),
        (sh_z - 0.045 * scale, lm['sh_x'] + 0.098 * scale, by_c + 0.130 * scale, cy_c + 0.028 * scale, 0.76),
        (sh_z - 0.140 * scale, lm['sh_x'] + 0.106 * scale, by_c + 0.134 * scale, cy_c + 0.030 * scale, 1.00),
    ]
    bm_d = bmesh.new()
    d_segs = 18
    d_rings = []
    d_rings_in = []
    for z, rx, ry, cy, t in levels:
        ring = []
        rin = []
        for k in range(d_segs + 1):
            th = a0 + (a1 - a0) * (k / d_segs)
            back_w = max(0.0, math.sin(th))
            side_w = abs(math.cos(th))
            fold = 1.0 + 0.036 * t * math.sin(6.0 * th + 0.4)
            drop = t * (0.20 * side_w + 0.24 * back_w) * scale
            px = rx * fold * math.cos(th)
            py = cy + ry * fold * math.sin(th)
            ring.append(bm_d.verts.new((px, py, z - drop)))
            rin.append(bm_d.verts.new((px * 0.94, cy + (py - cy) * 0.94, z - drop)))
        d_rings.append(ring)
        d_rings_in.append(rin)

    loft_rings(bm_d, d_rings, closed_u=False)
    n = d_segs + 1
    for r0, r1 in zip(d_rings_in, d_rings_in[1:]):
        for k in range(n - 1):
            bm_d.faces.new((r0[k + 1], r0[k], r1[k], r1[k + 1]))
    for i in range(len(levels) - 1):
        bm_d.faces.new((d_rings[i][0], d_rings_in[i][0], d_rings_in[i + 1][0], d_rings[i + 1][0]))
        bm_d.faces.new((d_rings[i][-1], d_rings[i + 1][-1], d_rings_in[i + 1][-1], d_rings_in[i][-1]))
    for k in range(n - 1):
        bm_d.faces.new((d_rings[-1][k + 1], d_rings[-1][k], d_rings_in[-1][k], d_rings_in[-1][k + 1]))

    drape_sh = bm_to_obj(bm_d, name + '_tails', col, shemagh_mat)
    uv_cylindrical(drape_sh, center=(0.0, 0.02 * scale), scale_u=3.2, scale_v=5.4)
    R.skin_cape_drape(drape_sh, rig_obj, lm, z_top_d, sh_z)
    parts.append(drape_sh)

    # --- 3) Double-coil glossy black Agal + subtle gold accent cords
    bm_a = bmesh.new()
    for dz, r_mul in ((0.46, 1.07), (0.58, 1.03)):
        add_ring_torus(
            bm_a,
            C + Vector((0.0, 0.02 * R_h, 0.0)),
            R_h * r_mul * 0.97,
            R_h * r_mul * 1.03,
            C.z + dz * R_h,
            tube_rx=0.056 * R_h,
            tube_rz=0.054 * R_h,
            tilt=0.04 * R_h,
            segs=24,
            tsegs=6,
        )
    agal_obj = bm_to_obj(bm_a, name + '_agal', col, agal_mat)
    R.skin_rigid(agal_obj, rig_obj, 'head')
    parts.append(agal_obj)

    if gold_mat is not None:
        bm_g = bmesh.new()
        for side_ang in (math.radians(20), math.radians(160)):
            cx = C.x + R_h * 1.06 * 0.97 * math.cos(side_ang)
            cy = C.y + 0.02 * R_h + R_h * 1.06 * 1.03 * math.sin(side_ang)
            pts = [
                Vector((cx, cy, C.z + 0.42 * R_h)),
                Vector((cx, cy, C.z + 0.62 * R_h)),
            ]
            add_tube(bm_g, pts, radius=0.064 * R_h, segs=8, closed_caps=True)
        g_obj = bm_to_obj(bm_g, name + '_agal_gold', col, gold_mat)
        R.skin_rigid(g_obj, rig_obj, 'head')
        parts.append(g_obj)

    return parts


# ------------------------------------------------------------------ backpack (player)
def _sample_torso_point(lm, p, z, angle_rad, pad):
    """Return a smooth surface point on the galabiya torso at height z and azimuth angle_rad (-pi/2 = front)."""
    bx, by, cy = torso_radii(lm, p, z)
    rx = bx + pad
    ry = by + pad * 1.05
    return Vector((rx * math.cos(angle_rad), cy + ry * math.sin(angle_rad), z))


def build_backpack(name, col, lm, p, bag_mat, flap_mat, brass_mat, rig_obj, robe_ease=0.022):
    """Build an adorable rounded storybook leather satchel + body-hugging curved shoulder straps."""
    scale = lm['height'] / 1.60
    sh_z = lm['sh_z']
    sh_x = lm['sh_x']
    z_top = sh_z - 0.012 * scale
    z_bot = lm['waist_z'] - 0.028 * scale
    z_mid = 0.5 * (z_top + z_bot)
    bx, by, cy = torso_radii(lm, p, z_mid)
    back_y = cy + by + robe_ease + 0.008 * scale

    bag_w = sh_x * 1.34
    bag_h = (z_top - z_bot) * 1.06
    bag_d = 0.112 * scale

    # --- 1) Soft rounded leather pack body (compact 14x10 superellipsoid)
    bm_bag = bmesh.new()
    u_segs, v_segs = 14, 10
    rings = []
    for j in range(1, v_segs):
        phi = (j / v_segs - 0.5) * math.pi
        sp, cp = math.sin(phi), math.cos(phi)
        sz = math.copysign(abs(sp) ** 0.52, sp)
        sr = abs(cp) ** 0.52
        ring = []
        for i in range(u_segs):
            th = i / u_segs * math.tau
            sx = math.copysign(abs(math.cos(th)) ** 0.52, math.cos(th)) * sr
            sy = math.copysign(abs(math.sin(th)) ** 0.52, math.sin(th)) * sr
            taper = 1.0 - 0.08 * sz
            ring.append(bm_bag.verts.new((
                sx * (bag_w * 0.5) * taper,
                back_y + bag_d * 0.50 + sy * (bag_d * 0.5),
                z_mid + sz * (bag_h * 0.5),
            )))
        rings.append(ring)
    top_v = bm_bag.verts.new((0.0, back_y + bag_d * 0.50, z_mid + bag_h * 0.5))
    bot_v = bm_bag.verts.new((0.0, back_y + bag_d * 0.50, z_mid - bag_h * 0.5))
    loft_rings(bm_bag, rings, closed_u=True)
    for i in range(u_segs):
        inext = (i + 1) % u_segs
        bm_bag.faces.new((rings[-1][i], rings[-1][inext], top_v))
        bm_bag.faces.new((rings[0][inext], rings[0][i], bot_v))

    bag_obj = bm_to_obj(bm_bag, name + '_body', col, bag_mat)
    R.skin_rigid(bag_obj, rig_obj, 'spine_02')

    # --- 2) Darker leather top flap + vertical straps + top handle + smooth body-hugging shoulder straps
    bm_fl = bmesh.new()
    fl_pts = []
    for k in range(6):
        u = k / 5.0
        ang = math.radians(150 - 160 * u)
        py = back_y + bag_d * 0.44 + math.cos(ang) * (bag_d * 0.60)
        pz = z_mid + bag_h * 0.14 + math.sin(ang) * (bag_h * 0.42)
        if u > 0.62:
            py = back_y + bag_d * 1.04
            pz = z_mid + bag_h * (0.44 - 0.54 * (u - 0.62) / 0.38)
        fl_pts.append(Vector((0.0, py, pz)))
    add_tube(
        bm_fl,
        fl_pts,
        radius=lambda u: (bag_w * 0.52 * (1.0 - 0.06 * u), 0.010 * scale),
        segs=8,
        closed_caps=True,
        ref_up=Vector((0.0, -1.0, 0.0)),
    )

    for s in (1.0, -1.0):
        sx = s * bag_w * 0.27
        s_pts = [
            Vector((sx, back_y + bag_d * 1.05, z_mid + bag_h * 0.36)),
            Vector((sx, back_y + bag_d * 1.06, z_mid + bag_h * 0.04)),
            Vector((sx, back_y + bag_d * 1.02, z_mid - bag_h * 0.36)),
        ]
        add_tube(bm_fl, s_pts, radius=(0.014 * scale, 0.0055 * scale), segs=6, closed_caps=True, ref_up=Vector((0.0, 1.0, 0.0)))

    h_pts = [
        Vector((-bag_w * 0.15, back_y + bag_d * 0.44, z_mid + bag_h * 0.48)),
        Vector((-bag_w * 0.11, back_y + bag_d * 0.44, z_mid + bag_h * 0.63)),
        Vector((0.0, back_y + bag_d * 0.44, z_mid + bag_h * 0.67)),
        Vector((bag_w * 0.11, back_y + bag_d * 0.44, z_mid + bag_h * 0.63)),
        Vector((bag_w * 0.15, back_y + bag_d * 0.44, z_mid + bag_h * 0.48)),
    ]
    add_tube(bm_fl, h_pts, radius=0.0085 * scale, segs=6, closed_caps=True)

    # Smoothly contoured surface-hugging shoulder straps (clean 12-point spline -> ~260 tris!)
    pad = robe_ease + 0.008 * scale
    z_crest = lm['neck_bot'].z - 0.005 * scale
    for s in (1.0, -1.0):
        strap_pts = [
            Vector((s * bag_w * 0.32, back_y + 0.015 * scale, z_mid + bag_h * 0.38)),
            _sample_torso_point(lm, p, sh_z + 0.010 * scale, math.pi * 0.5 - s * 0.72, pad),
            Vector((s * sh_x * 0.58, 0.004 * scale, z_crest)),
            _sample_torso_point(lm, p, sh_z + 0.015 * scale, -math.pi * 0.5 + s * 0.64, pad),
            _sample_torso_point(lm, p, lm['chest_z'] + 0.020 * scale, -math.pi * 0.5 + s * 0.68, pad),
            _sample_torso_point(lm, p, lm['chest_z'] - 0.030 * scale, -math.pi * 0.5 + s * 0.80, pad),
            _sample_torso_point(lm, p, lm['waist_z'] + 0.050 * scale, -math.pi * 0.5 + s * 1.12, pad + 0.004 * scale),
            _sample_torso_point(lm, p, lm['waist_z'] + 0.018 * scale, -math.pi * 0.5 + s * 1.52, pad + 0.005 * scale),
            _sample_torso_point(lm, p, z_bot + 0.022 * scale, math.pi * 0.5 - s * 1.00, pad + 0.004 * scale),
            Vector((s * bag_w * 0.38, back_y + 0.018 * scale, z_bot + 0.028 * scale)),
        ]
        # 12 smooth midpoint-averaged points along the strap
        smooth_pts = [strap_pts[0]]
        for a, b in zip(strap_pts[:-1], strap_pts[1:]):
            smooth_pts.append(a.lerp(b, 0.5))
        smooth_pts.append(strap_pts[-1])
        add_tube(
            bm_fl,
            smooth_pts,
            radius=(0.016 * scale, 0.0065 * scale),
            segs=6,
            closed_caps=True,
            ref_up=Vector((s, 0.0, 0.0)),
        )

    flap_obj = bm_to_obj(bm_fl, name + '_straps', col, flap_mat)
    R.skin_spine_mesh(flap_obj, rig_obj, lm)

    bm_br = bmesh.new()
    for s in (1.0, -1.0):
        sx = s * bag_w * 0.27
        zb = z_mid - bag_h * 0.08
        yb = back_y + bag_d * 1.075
        bw, bh = 0.017 * scale, 0.019 * scale
        ring = [
            Vector((sx - bw, yb, zb - bh)),
            Vector((sx + bw, yb, zb - bh)),
            Vector((sx + bw, yb, zb + bh)),
            Vector((sx - bw, yb, zb + bh)),
            Vector((sx - bw, yb, zb - bh)),
        ]
        add_tube(bm_br, ring, radius=0.0048 * scale, segs=5, closed_caps=False)
    brass_obj = bm_to_obj(bm_br, name + '_buckles', col, brass_mat)
    R.skin_rigid(brass_obj, rig_obj, 'spine_02')

    return [bag_obj, flap_obj, brass_obj]


# ------------------------------------------------------------------ glasses (grandma Amina)
def build_glasses(name, col, lm, F, mat, rig_obj):
    """Build delicate warm-gold round spectacles perched accurately on the 3D nose bridge."""
    C = lm['head_center']
    R_h = lm['head_r']
    ez = F.get('eye_z', -0.06)
    ex = F.get('eye_x', 0.34)
    ew = F.get('eye_w', 0.21)
    eh = F.get('eye_h', 0.21)

    bm = bmesh.new()
    wire_r = 0.016 * R_h
    lens_rx = ew * 1.26 * R_h
    lens_rz = eh * 1.24 * R_h
    frame_y = head_front_y(F, ex, ez).y - 0.145   # cleanly clears eyelashes and sits on nose bridge!

    for s in (1.0, -1.0):
        lc = C + Vector((s * ex * 1.02, frame_y, ez - 0.01)) * R_h
        ring_pts = [
            lc + Vector((math.cos(a) * lens_rx, 0.0, math.sin(a) * lens_rz))
            for a in (k / 24 * math.tau for k in range(25))
        ]
        add_tube(bm, ring_pts, radius=wire_r, segs=6, closed_caps=False)

        # Slender temple arm curving gently back to tuck neatly into the hijab
        arm_start = lc + Vector((s * lens_rx, 0.0, 0.03 * R_h))
        arm_mid = C + Vector((s * 0.86, frame_y * 0.45, ez + 0.04)) * R_h
        arm_end = C + Vector((s * 0.88, 0.16, ez + 0.02)) * R_h
        add_tube(bm, [arm_start, arm_mid, arm_end], radius=wire_r * 0.90, segs=6, closed_caps=True)

    # Graceful arched nose bridge resting right across the 3D nose bridge
    nose_surf = head_front_y(F, 0.0, ez + 0.04)
    bridge_y = min(frame_y, nose_surf.y - 0.03)
    b_pts = [
        C + Vector((-ex * 1.02 + ew * 1.24, frame_y, ez + 0.02)) * R_h,
        C + Vector((0.0, bridge_y, ez + 0.07)) * R_h,
        C + Vector((ex * 1.02 - ew * 1.24, frame_y, ez + 0.02)) * R_h,
    ]
    add_tube(bm, b_pts, radius=wire_r * 0.95, segs=6, closed_caps=True)

    obj = bm_to_obj(bm, name, col, mat)
    return R.skin_rigid(obj, rig_obj, 'head')


# ------------------------------------------------------------------ shepherd staff (farmer)
def build_staff(name, col, rig_obj, mat, idle_act, grip_mat=None):
    """Build a hand-carved wooden walking staff positioned cleanly in Grandpa Salim's left hand."""
    import bpy
    rig_obj.animation_data.action = idle_act
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    pb = rig_obj.pose.bones['hand_l']
    # Grip center sits in the palm of hand_l in idle pose
    grip = pb.head.lerp(pb.tail, 0.48) + Vector((0.0, -0.015, 0.0))
    top_z = grip.z + 0.56
    bot_z = 0.004   # kisses ground cleanly

    bm = bmesh.new()
    pts = []
    n = 14
    for i in range(n):
        u = i / (n - 1)   # 0 = top knob -> 1 = bottom tip
        z = top_z + (bot_z - top_z) * u
        # Gentle organic hand-carved wooden slight wave
        wx = 0.008 * math.sin(u * math.pi * 2.2)
        wy = 0.005 * math.cos(u * math.pi * 1.6)
        pts.append(Vector((grip.x + wx, grip.y + wy, z)))

    def staff_r(u):
        if u < 0.07:
            return 0.024 * (0.75 + 0.35 * math.sin(u / 0.07 * math.pi))
        return 0.0175 * (1.0 - 0.22 * u)

    add_tube(bm, pts, radius=staff_r, segs=10, closed_caps=True)
    obj = bm_to_obj(bm, name, col, mat)

    # Transform back from posed space into rest space of hand_l!
    inv_mat = pb.bone.matrix_local @ pb.matrix.inverted()
    obj.data.transform(inv_mat)
    R.skin_rigid(obj, rig_obj, 'hand_l')
    parts = [obj]

    if grip_mat is not None:
        bm_g = bmesh.new()
        g_pts = [Vector((grip.x, grip.y, grip.z + 0.065 - 0.13 * (i / 4.0))) for i in range(5)]
        add_tube(bm_g, g_pts, radius=0.0205, segs=10, closed_caps=True)
        g_obj = bm_to_obj(bm_g, name + '_grip', col, grip_mat)
        g_obj.data.transform(inv_mat)
        R.skin_rigid(g_obj, rig_obj, 'hand_l')
        parts.append(g_obj)

    return parts
