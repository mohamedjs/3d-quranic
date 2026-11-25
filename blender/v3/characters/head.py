"""Storybook 3D head/face builder: sculpted head+nose+ears, 3D eyes/lids/brows/mouth, hair & beards."""
import math
import bmesh
import numpy as np
from mathutils import Vector, Matrix

from lib import (
    bm_to_obj,
    hex_rgb,
    loft_rings,
    pack_image,
    smoothstep,
)

# Face texture atlas coordinates inside a 512x512 PNG:
FACE_U0, FACE_U1 = 0.02, 0.58
FACE_V0, FACE_V1 = 0.16, 0.84
FACE_X_MIN, FACE_X_MAX = -0.95, 0.95
FACE_Z_MIN, FACE_Z_MAX = -1.18, 0.82

EYE_U0, EYE_U1 = 0.64, 0.98
EYE_V0, EYE_V1 = 0.56, 0.90


def head_shape(p, F):
    """Map unit sphere point p -> warm Pixar/Ghibli storybook head (units of R, -Y = front, +Z = up)."""
    x, y, z = p.x, p.y, p.z

    x *= F.get('skull_w', 0.96)
    y *= F.get('skull_d', 1.00)
    if z > 0.0:
        z *= F.get('crown_h', 1.02)

    front = smoothstep(0.25, -0.75, y)
    lower = smoothstep(0.18, -0.95, z)

    jaw_taper = F.get('jaw_taper', 0.19)
    x *= 1.0 - jaw_taper * (lower ** 1.35) * (0.45 + 0.55 * front)
    chin_drop = F.get('chin_drop', 0.16)
    z -= chin_drop * (lower ** 1.2) * (front ** 1.1)
    if y > 0.0:
        y *= 1.0 - 0.34 * (lower ** 1.15)
        z += 0.10 * lower * smoothstep(0.1, 0.85, y)

    ez = F.get('eye_z', -0.06)
    ex = F.get('eye_x', 0.34)
    cheek_full = F.get('cheek_full', 0.11)
    cheek_g = math.exp(-((abs(x) - (ex + 0.16)) / 0.30) ** 2 - ((z - (ez - 0.30)) / 0.28) ** 2) * front
    x += math.copysign(cheek_full * 0.72 * cheek_g, x)
    y -= cheek_full * 0.52 * cheek_g

    # Gentle orbital eye-socket recesses so 3D eyes nestle cleanly
    for s in (1.0, -1.0):
        dx = (x - s * ex) / (F.get('eye_w', 0.21) * 1.24)
        dz = (z - ez) / (F.get('eye_h', 0.21) * 1.24)
        d2 = dx * dx + dz * dz
        if d2 < 2.2 and y < -0.25:
            y += 0.105 * math.exp(-d2 * 1.15) * front

    # Soft brow ridge above the sockets
    brow_z = ez + F.get('eye_h', 0.21) * 1.35
    brow_g = math.exp(-((z - brow_z) / 0.14) ** 2 - (x / 0.65) ** 2) * front
    y -= 0.048 * brow_g

    # Real 3D sculpted storybook nose (clear bridge, soft button tip, gentle alae & crisp underside)!
    nz = F.get('nose_z', -0.34)
    n_len = F.get('nose_len', 0.17) * 1.26
    n_w = F.get('nose_w', 0.13)
    n_lift = F.get('nose_lift', 0.02)
    if y < -0.32:
        bridge_t = smoothstep(ez + 0.06, nz + 0.01, z) * smoothstep(nz - 0.095, nz - 0.015, z)
        bridge_x = math.exp(-(x / (n_w * 0.64)) ** 2)
        tip_g = math.exp(-((x / (n_w * 0.84)) ** 2 + ((z - nz) / (n_w * 0.68)) ** 2))
        ala_g = math.exp(-(((abs(x) - n_w * 0.72) / (n_w * 0.44)) ** 2 + ((z - (nz - 0.026)) / (n_w * 0.38)) ** 2))
        nose_push = (0.68 * bridge_t * bridge_x + 1.02 * tip_g + 0.30 * ala_g) * n_len * front
        y -= nose_push
        z += n_lift * tip_g * front

    # Gentle warm lip cushion + smooth soft rounded chin pad (no harsh lower-face shadow shelf!)
    mz = F.get('mouth_z', -0.60)
    if y < -0.30:
        muzzle = math.exp(-((x / 0.36) ** 2 + ((z - (mz - 0.02)) / 0.21) ** 2)) * front
        y -= 0.046 * muzzle
        groove = math.exp(-((x / 0.24) ** 2 + ((z - (mz - 0.15)) / 0.075) ** 2)) * front
        y += 0.014 * groove
        chin_pad = math.exp(-((x / 0.28) ** 2 + ((z - (mz - 0.26)) / 0.12) ** 2)) * front
        y -= 0.036 * chin_pad

    return Vector((x, y, z))


def head_surface_point(F, direction):
    """Find point and outward normal on the parametric head_shape along unit direction."""
    s = Vector(direction).normalized()
    p = head_shape(s, F)
    eps = 2e-3
    t1 = s.orthogonal().normalized()
    t2 = s.cross(t1).normalized()
    p1 = head_shape((s + t1 * eps).normalized(), F)
    p2 = head_shape((s + t2 * eps).normalized(), F)
    n = (p1 - p).cross(p2 - p)
    n = p.normalized() if n.length < 1e-8 else n.normalized()
    if n.dot(p) < 0.0:
        n = -n
    return p, n


def head_front_y(F, ux, uz):
    """Approximate front-surface unit point on the sculpted head at unit (ux, uz)."""
    r2 = ux * ux + uz * uz
    uy = -math.sqrt(max(0.05, 1.0 - min(0.95, r2)))
    s = Vector((ux, uy, uz)).normalized()
    for _ in range(4):
        p = head_shape(s, F)
        s.x += (ux - p.x) * 0.55
        s.z += (uz - p.z) * 0.55
        s.normalize()
    return head_shape(s, F)


# ------------------------------------------------------------------ 512px face + eye texture
class _Canvas:
    def __init__(self, res, bg_hex):
        self.res = res
        self.img = np.ones((res, res, 3), dtype=np.float32) * np.array(hex_rgb(bg_hex), dtype=np.float32)
        us = (np.arange(res) + 0.5) / res
        vs = (np.arange(res) + 0.5) / res
        self.U, self.V = np.meshgrid(us, vs)

    def blend(self, mask, color, alpha=1.0):
        a = np.clip(mask, 0.0, 1.0) * alpha
        c = np.array(hex_rgb(color) if isinstance(color, str) else color, dtype=np.float32)
        self.img = self.img * (1.0 - a[..., None]) + c * a[..., None]

    def blend_img(self, mask, col_img, alpha=1.0):
        a = np.clip(mask, 0.0, 1.0) * alpha
        self.img = self.img * (1.0 - a[..., None]) + col_img * a[..., None]

    def sd_put(self, sd, px_scale, color, alpha=1.0, soft=1.2):
        a = np.clip(0.5 - sd / (px_scale * soft), 0.0, 1.0) * alpha
        self.blend(a, color, 1.0)

    def stroke(self, X, Z, pts, w0, w1=None):
        w1 = w0 if w1 is None else w1
        P = np.array(pts, dtype=np.float32)
        best = np.full(X.shape, 1e9, dtype=np.float32)
        lens = np.concatenate([[0.0], np.cumsum(np.linalg.norm(P[1:] - P[:-1], axis=1))])
        lens /= max(float(lens[-1]), 1e-6)
        for i in range(len(P) - 1):
            a, b = P[i], P[i + 1]
            ab = b - a
            l2 = max(float(ab @ ab), 1e-9)
            t = np.clip(((X - a[0]) * ab[0] + (Z - a[1]) * ab[1]) / l2, 0.0, 1.0)
            d = np.hypot(X - (a[0] + t * ab[0]), Z - (a[1] + t * ab[1]))
            w = w0 + (w1 - w0) * (lens[i] + t * (lens[i + 1] - lens[i]))
            best = np.minimum(best, d - w)
        return best


def paint_face_texture(key, F):
    """Paint a crisp 512x512 face+eye texture atlas (blush, warm lips, age lines + expressive iris)."""
    res = 512
    c = _Canvas(res, F['skin'])

    fx = FACE_X_MIN + (c.U - FACE_U0) / (FACE_U1 - FACE_U0) * (FACE_X_MAX - FACE_X_MIN)
    fz = FACE_Z_MIN + (c.V - FACE_V0) / (FACE_V1 - FACE_V0) * (FACE_Z_MAX - FACE_Z_MIN)
    in_face = (c.U >= FACE_U0) & (c.U <= FACE_U1) & (c.V >= FACE_V0) & (c.V <= FACE_V1)
    fpx = (FACE_X_MAX - FACE_X_MIN) / ((FACE_U1 - FACE_U0) * res)

    ez = F.get('eye_z', -0.06)
    ex = F.get('eye_x', 0.34)
    eh = F.get('eye_h', 0.21)
    ew = F.get('eye_w', 0.21)
    nz = F.get('nose_z', -0.34)
    mz = F.get('mouth_z', -0.60)
    mw = F.get('mouth_w', 0.20)

    # Warm rosy cheek blush + gentle nose-tip peach warmth
    blush = F.get('blush', 0.28)
    blush_col = F.get('blush_col', '#E17E69')
    for s in (1.0, -1.0):
        d = np.hypot((fx - s * (ex + 0.14)) / 0.26, (fz - (ez - eh - 0.13)) / 0.16)
        c.blend((np.clip(1.0 - d, 0.0, 1.0) ** 1.7) * blush * in_face, blush_col)

    n_w = F.get('nose_w', 0.13)
    dn = np.hypot(fx / (n_w * 1.12), (fz - (nz + 0.015)) / 0.10)
    c.blend((np.clip(1.0 - dn, 0.0, 1.0) ** 1.8) * (blush * 0.58) * in_face, blush_col)

    # Soft nose bridge + tip light catch so the 3D nose reads gently forward
    d_nhi = np.hypot(fx / (n_w * 0.42), (fz - (nz + 0.045)) / 0.090)
    c.blend((np.clip(1.0 - d_nhi, 0.0, 1.0) ** 1.7) * 0.16 * in_face, '#FFF3E4')

    # Warm painted crescent shade under the nose tip + subtle nostril wing cues
    n_arc_z = nz - 0.066 + 0.022 * np.clip((fx / max(n_w * 0.85, 1e-4)) ** 2, 0.0, 1.4)
    d_nsh = np.hypot(fx / (n_w * 0.94), (fz - n_arc_z) / 0.036)
    c.blend((np.clip(1.0 - d_nsh, 0.0, 1.0) ** 1.45) * 0.50 * in_face, F.get('socket_col', '#8D523A'))
    for s in (1.0, -1.0):
        d_nost = np.hypot((fx - s * n_w * 0.58) / (n_w * 0.34), (fz - (nz - 0.048)) / 0.024)
        c.blend((np.clip(1.0 - d_nost, 0.0, 1.0) ** 1.55) * 0.30 * in_face, F.get('socket_col', '#8D523A'))

    # Subtle upper eyelid crease & soft socket warmth
    sock_col = F.get('socket_col', '#985C42')
    for s in (1.0, -1.0):
        ds = np.hypot((fx - s * ex) / (ew * 1.24), (fz - (ez + 0.03)) / (eh * 1.15))
        c.blend((np.clip(1.0 - ds, 0.0, 1.0) ** 2.0) * 0.16 * in_face, sock_col)
        # Delicate warm upper eyelid fold arc right above the eye
        cr_pts = [
            (s * (ex + a * ew * 0.92), ez + eh * (0.98 + 0.24 * (1.0 - a * a)))
            for a in np.linspace(-0.78, 0.82, 10)
        ]
        sd_cr = c.stroke(fx, fz, cr_pts, 0.008, 0.004)
        c.sd_put(np.where(in_face, sd_cr, 1.0), fpx, sock_col, alpha=0.38, soft=1.6)

    # Gentle elder warmth: soft laugh crinkles & smile lines
    if F.get('age_lines', False):
        ac = F.get('age_col', '#945D44')
        for s in (1.0, -1.0):
            ox = s * (ex + ew * 1.14)
            sd1 = c.stroke(fx, fz, [(ox, ez + 0.02), (ox + s * 0.10, ez + 0.06)], 0.008, 0.003)
            sd2 = c.stroke(fx, fz, [(ox, ez - 0.05), (ox + s * 0.09, ez - 0.09)], 0.008, 0.003)
            c.sd_put(np.where(in_face, sd1, 1.0), fpx, ac, alpha=0.45, soft=1.6)
            c.sd_put(np.where(in_face, sd2, 1.0), fpx, ac, alpha=0.42, soft=1.6)
            pts_nl = [
                (s * (0.20 + 0.13 * t + 0.02 * math.sin(t * math.pi)), nz - 0.04 - (nz - mz + 0.05) * t)
                for t in np.linspace(0.0, 1.0, 8)
            ]
            sd_nl = c.stroke(fx, fz, pts_nl, 0.010, 0.004)
            c.sd_put(np.where(in_face, sd_nl, 1.0), fpx, ac, alpha=0.38, soft=1.8)

    # Warm resting smile
    smile = F.get('smile', 0.060)
    lip_col = F.get('lip_col', '#BC6854')
    mouth_col = F.get('mouth_col', '#5E241A')
    dlip = np.hypot(fx / (mw * 1.06), (fz - (mz - 0.012)) / 0.068)
    c.blend((np.clip(1.0 - dlip, 0.0, 1.0) ** 1.6) * F.get('lip_alpha', 0.34) * in_face, lip_col)
    us = np.linspace(-1.0, 1.0, 18)
    m_pts = [(mw * a, mz + smile * (a * a - 0.35)) for a in us]
    sd_m = c.stroke(fx, fz, m_pts, 0.011, 0.011)
    c.sd_put(np.where(in_face, sd_m, 1.0), fpx, mouth_col, alpha=0.92, soft=1.3)
    for s in (1.0, -1.0):
        cx0 = s * mw
        cz0 = mz + smile * 0.65
        sd_c = c.stroke(fx, fz, [(cx0, cz0), (cx0 + s * 0.028, cz0 + 0.020)], 0.007, 0.003)
        c.sd_put(np.where(in_face, sd_c, 1.0), fpx, mouth_col, alpha=0.68, soft=1.4)

    # ---- 2) Dedicated 3D Eyeball Iris+Sclera quadrant
    eu = (c.U - EYE_U0) / (EYE_U1 - EYE_U0) * 2.0 - 1.0
    ev = (c.V - EYE_V0) / (EYE_V1 - EYE_V0) * 2.0 - 1.0
    in_eye = (c.U >= EYE_U0) & (c.U <= EYE_U1) & (c.V >= EYE_V0) & (c.V <= EYE_V1)
    epx = 2.0 / ((EYE_U1 - EYE_U0) * res)

    c.blend(in_eye.astype(np.float32), '#FFFDF8')
    # Soft warm-lavender upper lid shadow across top 28% of sclera -> relaxed friendly Pixar gaze!
    top_sh = np.clip((ev - 0.24) / 0.42, 0.0, 1.0) * in_eye
    c.blend(top_sh * 0.52, '#CFC3C0')

    ir = F.get('iris_r', 0.56)
    ir_dist = np.hypot(eu / ir, (ev + 0.03) / (ir * 1.05))
    iris_sd = (ir_dist - 1.0) * ir

    g = np.clip(((ev + 0.03) + ir) / (2.0 * ir), 0.0, 1.0)
    col_hi = np.array(hex_rgb(F.get('iris_hi', '#2C150B')), dtype=np.float32)
    col_lo = np.array(hex_rgb(F.get('iris_lo', '#B57034')), dtype=np.float32)
    iris_rgb = col_lo * (1.0 - g[..., None] ** 0.85) + col_hi * (g[..., None] ** 0.85)
    iris_mask = np.clip(0.5 - iris_sd / (epx * 1.4), 0.0, 1.0) * in_eye
    c.blend_img(iris_mask, iris_rgb)

    glow_d = np.hypot(eu / (ir * 0.72), (ev + ir * 0.36) / (ir * 0.34))
    glow_m = np.clip(1.0 - glow_d, 0.0, 1.0) ** 1.3 * iris_mask * 0.70
    c.blend(glow_m, F.get('iris_glow', '#F0B65A'))

    ring_sd = np.abs(ir_dist - 0.94) * ir - 0.044
    c.sd_put(np.where(in_eye, np.maximum(ring_sd, iris_sd - 0.02), 1.0), epx, F.get('iris_hi', '#241008'), alpha=0.92, soft=1.2)

    pup_r = ir * F.get('pupil_ratio', 0.46)
    pup_sd = (np.hypot(eu / pup_r, (ev + 0.01) / (pup_r * 1.04)) - 1.0) * pup_r
    c.sd_put(np.where(in_eye, pup_sd, 1.0), epx, '#170B06', alpha=1.0, soft=1.2)

    hl1 = (np.hypot((eu + ir * 0.34) / (ir * 0.26), (ev - ir * 0.30) / (ir * 0.28)) - 1.0) * (ir * 0.26)
    hl2 = (np.hypot((eu - ir * 0.30) / (ir * 0.11), (ev + ir * 0.36) / (ir * 0.11)) - 1.0) * (ir * 0.11)
    c.sd_put(np.where(in_eye, hl1, 1.0), epx, '#FFFFFF', alpha=0.98, soft=1.1)
    c.sd_put(np.where(in_eye, hl2, 1.0), epx, '#FFF9EE', alpha=0.90, soft=1.1)

    return pack_image(key + '_face', c.img)


# ------------------------------------------------------------------ head, ears, eyes, lids, brows, mouth
def build_head_mesh(name, col, center, R, F, face_mat):
    """Build the sculpted 3D head with integrated 3D nose, cheeks, eye sockets, and optional 3D ears."""
    C = Vector(center)
    bm = bmesh.new()

    u_segs = 24
    v_segs = 18
    v_angles = []
    for j in range(1, v_segs):
        t = j / v_segs
        phi = (t - 0.5) * math.pi
        phi = phi - 0.16 * math.sin(2.0 * phi)
        v_angles.append(phi)

    rings = []
    for phi in v_angles:
        cp, sp = math.cos(phi), math.sin(phi)
        rings.append([
            bm.verts.new(head_shape(Vector((cp * math.cos(th), cp * math.sin(th), sp)), F))
            for th in (i / u_segs * math.tau for i in range(u_segs))
        ])

    top_v = bm.verts.new(head_shape(Vector((0.0, 0.0, 1.0)), F))
    bot_v = bm.verts.new(head_shape(Vector((0.0, 0.0, -1.0)), F))
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(u_segs):
            inext = (i + 1) % u_segs
            bm.faces.new((r0[i], r0[inext], r1[inext], r1[i]))
    for i in range(u_segs):
        inext = (i + 1) % u_segs
        bm.faces.new((rings[-1][i], rings[-1][inext], top_v))
        bm.faces.new((rings[0][inext], rings[0][i], bot_v))

    ear_verts = set()
    if F.get('ears', True):
        ez = F.get('eye_z', -0.06)
        ear_z = ez - 0.13
        ear_x = F.get('skull_w', 0.96) * 0.95
        ear_scale = F.get('ear_scale', 1.0)
        for s in (1.0, -1.0):
            ret = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=1.0)
            rot_z = Matrix.Rotation(-0.30 * s, 3, 'Z')
            rot_y = Matrix.Rotation(0.12 * s, 3, 'Y')
            for v in ret['verts']:
                ear_verts.add(v)
                p = v.co.copy()
                if p.y < -0.10 and abs(p.z) < 0.65:
                    p.y += 0.30 * (1.0 - p.z * p.z)
                q = Vector((p.x * 0.115 * ear_scale, p.y * 0.155 * ear_scale, p.z * 0.225 * ear_scale))
                q = rot_z @ rot_y @ q
                v.co = Vector((s * ear_x + q.x, 0.09 + q.y, ear_z + q.z))

    uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        is_ear = any(v in ear_verts for v in f.verts)
        for loop in f.loops:
            p = loop.vert.co
            if is_ear or p.y > 0.05 or abs(p.x) > 0.88:
                loop[uv].uv = (0.01, 0.01)
            else:
                u = FACE_U0 + (p.x - FACE_X_MIN) / (FACE_X_MAX - FACE_X_MIN) * (FACE_U1 - FACE_U0)
                v_coord = FACE_V0 + (p.z - FACE_Z_MIN) / (FACE_Z_MAX - FACE_Z_MIN) * (FACE_V1 - FACE_V0)
                loop[uv].uv = (
                    max(FACE_U0 + 0.002, min(FACE_U1 - 0.002, u)),
                    max(FACE_V0 + 0.002, min(FACE_V1 - 0.002, v_coord)),
                )

    for v in bm.verts:
        v.co = C + v.co * R

    return bm_to_obj(bm, name, col, face_mat)


def apply_soft_face_normals(mesh_obj, head_center, R, F):
    """Smooth and lift cheek/mouth/jaw vertex normals so toon cel shadow wraps softly and never stains the mouth."""
    me = mesh_obj.data
    C = Vector(head_center)
    face_slots = {
        idx for idx, m in enumerate(me.materials)
        if m is not None and m.name.startswith('toon_face_')
    }
    if not face_slots or not me.uv_layers:
        return

    uv_data = me.uv_layers[0].data
    head_skin_verts = set()
    for poly in me.polygons:
        if poly.material_index not in face_slots:
            continue
        for li in poly.loop_indices:
            # Face skin occupies U <= FACE_U1 (0.58); 3D eyeballs occupy U >= EYE_U0 (0.64)
            if uv_data[li].uv[0] <= FACE_U1 + 0.01:
                head_skin_verts.add(me.loops[li].vertex_index)

    if not head_skin_verts:
        return

    nz_pos = F.get('nose_z', -0.34)
    n_w = F.get('nose_w', 0.13)
    ez = F.get('eye_z', -0.06)

    norms = [v.normal.copy() for v in me.vertices]
    for vi in head_skin_verts:
        p = (me.vertices[vi].co - C) / R
        if p.y > 0.22:
            continue
        front_m = smoothstep(0.20, -0.30, p.y) * smoothstep(0.94, 0.72, abs(p.x))
        if front_m <= 1e-4:
            continue
        # Keep the entire front face (forehead, cheeks, mouth, chin front) gently lifted;
        # only fade back toward downward geometric normal beneath the very bottom of the chin.
        chin_keep = smoothstep(-1.16, -0.92, p.z)
        n_soft = Vector((
            p.x * 0.72,
            -0.90,
            0.24 + 0.24 * max(-0.45, p.z),
        )).normalized()

        # Preserve ~74% of true 3D sculpted normals on the nose bridge/tip/underside so the nose pops cleanly!
        nose_x = math.exp(-(p.x / (n_w * 1.18)) ** 2)
        nose_z = smoothstep(nz_pos - 0.15, nz_pos - 0.04, p.z) * smoothstep(ez + 0.05, nz_pos + 0.08, p.z)
        nose_y = smoothstep(-0.66, -0.92, p.y)
        nose_m = nose_x * nose_z * nose_y

        blend = 0.92 * front_m * chin_keep * (1.0 - 0.74 * nose_m)
        norms[vi] = norms[vi].lerp(n_soft, blend).normalized()

    me.normals_split_custom_set_from_vertices([tuple(n) for n in norms])


def build_eyes_and_lids(key, col, center, R, F, face_mat, skin_mat, lash_mat):
    """Build 3D curved eyeballs, sculpted upper lash rims, and 3D blinking eyelid domes."""
    C = Vector(center)
    ez = F.get('eye_z', -0.06)
    ex = F.get('eye_x', 0.34)
    ew = F.get('eye_w', 0.21)
    eh = F.get('eye_h', 0.20)
    eye_tilt = F.get('eye_tilt', 0.03)

    bm_eyes = bmesh.new()
    uv_eyes = bm_eyes.loops.layers.uv.new('UVMap')
    bm_lash = bmesh.new()

    lid_objs = []
    lid_bones = {}

    for sd, s in (('l', 1.0), ('r', -1.0)):
        surf = head_front_y(F, s * ex, ez)
        # Nestle eyeball cleanly so the upper lash arch hugs the sclera with zero skin gap!
        eye_center_u = Vector((s * ex, surf.y + ew * 0.42, ez))
        eye_center_w = C + eye_center_u * R
        yaw = s * 0.22
        rot_eye = Matrix.Rotation(yaw, 3, 'Z')

        # 1) 3D Domed Eyeball (compact 14x7 mesh -> silky smooth & low poly!)
        u_segs, v_segs = 14, 7
        rings = []
        for j in range(1, v_segs + 1):
            theta = (j / v_segs) * (math.pi * 0.54)
            st, ct = math.sin(theta), math.cos(theta)
            ring = []
            for i in range(u_segs):
                a = i / u_segs * math.tau
                lx = st * math.cos(a) * ew * 0.98
                lz = st * math.sin(a) * eh * 0.96
                ly = -ct * ew * 0.64
                ring.append(bm_eyes.verts.new(eye_center_w + (rot_eye @ Vector((lx, ly, lz))) * R))
            rings.append(ring)

        apex_v = bm_eyes.verts.new(eye_center_w + (rot_eye @ Vector((0.0, -ew * 0.64, 0.0))) * R)
        new_faces = []
        for i in range(u_segs):
            inext = (i + 1) % u_segs
            new_faces.append(bm_eyes.faces.new((apex_v, rings[0][i], rings[0][inext])))
        for r0, r1 in zip(rings, rings[1:]):
            for i in range(u_segs):
                inext = (i + 1) % u_segs
                new_faces.append(bm_eyes.faces.new((r0[i], r1[i], r1[inext], r0[inext])))

        inv_rot = rot_eye.inverted()
        for f in new_faces:
            for loop in f.loops:
                rel = inv_rot @ ((loop.vert.co - eye_center_w) / R)
                eu = max(-0.98, min(0.98, rel.x / (ew * 0.90)))
                ev = max(-0.98, min(0.98, rel.z / (eh * 0.88)))
                loop[uv_eyes].uv = (
                    EYE_U0 + (eu * 0.5 + 0.5) * (EYE_U1 - EYE_U0),
                    EYE_V0 + (ev * 0.5 + 0.5) * (EYE_V1 - EYE_V0),
                )

        # 2) 3D Upper Eyelid Rim / Lash Arch hugging directly along the top rim of the eyeball!
        lash_w = F.get('lash_thick', 0.032)
        n_arc = 11
        arc_pts = []
        for i in range(n_arc):
            t = i / (n_arc - 1)
            ang = math.pi * (0.98 - 1.00 * t)
            lx = s * math.cos(ang) * ew * 0.96
            lz = (math.sin(ang) * 0.68 + 0.08 + eye_tilt * (t - 0.5) * 2.0) * eh * 0.94
            rn = min(0.94, math.hypot(lx / (ew * 1.00), lz / (eh * 1.00)))
            ly = -math.sqrt(max(0.05, 1.0 - rn * rn)) * ew * 0.66 - 0.016
            pu = eye_center_u + (rot_eye @ Vector((lx, ly, lz)))
            h_surf = head_front_y(F, pu.x, pu.z)
            pu.y = min(pu.y, h_surf.y - 0.018)
            thick = lash_w * (0.50 + 0.72 * math.sin(math.pi * min(1.0, t * 0.85 + 0.10)))
            if t > 0.76 and F.get('lashes', False):
                thick *= 1.18
            arc_pts.append((C + pu * R, thick * R))

        l_rings = []
        for idx, (pt, th) in enumerate(arc_pts):
            t_vec = (arc_pts[min(idx + 1, n_arc - 1)][0] - arc_pts[max(idx - 1, 0)][0]).normalized()
            out_n = (pt - eye_center_w).normalized()
            up_n = out_n.cross(t_vec).normalized()
            if up_n.z < 0:
                up_n = -up_n
            l_rings.append([
                bm_lash.verts.new(pt + up_n * (math.cos(a) * th) + out_n * (math.sin(a) * th * 0.72))
                for a in (k / 5.0 * math.tau for k in range(5))
            ])
        loft_rings(bm_lash, l_rings, closed_u=True, cap_start=True, cap_end=True)

        if F.get('lashes', False):
            outer_pt = arc_pts[-2][0]
            flick_dir = (rot_eye @ Vector((s * 0.85, -0.35, 0.50))).normalized()
            f_len = ew * 0.28 * R
            f_rings = []
            for u, rm in ((0.0, 1.0), (0.55, 0.52), (1.0, 0.12)):
                c_pt = outer_pt + flick_dir * (u * f_len)
                ax1 = flick_dir.cross(Vector((0.0, -1.0, 0.0))).normalized()
                ax2 = flick_dir.cross(ax1).normalized()
                f_rings.append([
                    bm_lash.verts.new(c_pt + (ax1 * math.cos(a) + ax2 * math.sin(a)) * (lash_w * 0.48 * R * rm))
                    for a in (k / 4.0 * math.tau for k in range(4))
                ])
            loft_rings(bm_lash, f_rings, closed_u=True, cap_start=True, cap_end=True)

        # 3) 3D Blinking Eyelid Dome
        bm_lid = bmesh.new()
        lid_u, lid_v = 8, 4
        lid_grid = []
        for j in range(lid_v + 1):
            tv = j / lid_v
            row = []
            for i in range(lid_u + 1):
                a_lat = -1.06 + 2.12 * (i / lid_u)
                ac = max(-1.0, min(1.0, a_lat))
                top_z = (0.84 * (1.0 - ac * ac) ** 0.55 + 0.12) * eh * 1.06
                bot_z = (-0.94 * (1.0 - ac * ac) ** 0.65 - 0.04) * eh * 1.04
                lx = s * a_lat * ew * 1.06
                lz = top_z + (bot_z - top_z) * tv
                rn = min(0.95, math.hypot(lx / (ew * 1.12), lz / (eh * 1.12)))
                ly = -math.sqrt(max(0.05, 1.0 - rn * rn)) * ew * 0.68 - 0.022
                row.append(bm_lid.verts.new(eye_center_w + (rot_eye @ Vector((lx, ly, lz))) * R))
            lid_grid.append(row)

        for j in range(lid_v):
            for i in range(lid_u):
                a, b, c2, d = lid_grid[j][i], lid_grid[j][i + 1], lid_grid[j + 1][i + 1], lid_grid[j + 1][i]
                f = bm_lid.faces.new((a, b, c2, d) if s < 0 else (b, a, d, c2))
                f.material_index = 1 if j == lid_v - 1 else 0

        bmesh.ops.recalc_face_normals(bm_lid, faces=bm_lid.faces)
        if sum(f.normal.y for f in bm_lid.faces) > 0:
            bmesh.ops.reverse_faces(bm_lid, faces=bm_lid.faces)
        lid_obj = bm_to_obj(bm_lid, f'{key}_lid_{sd}', col)
        lid_obj.data.materials.append(skin_mat)
        lid_obj.data.materials.append(lash_mat)
        lid_objs.append((f'lid_{sd}', lid_obj))

        top_bone = eye_center_w + (rot_eye @ Vector((0.0, -ew * 0.66, eh * 0.96))) * R
        bot_bone = eye_center_w + (rot_eye @ Vector((0.0, -ew * 0.66, -eh * 0.92))) * R
        lid_bones[f'lid_{sd}'] = (top_bone, bot_bone)

    eyes_obj = bm_to_obj(bm_eyes, f'{key}_eyes', col, face_mat, ensure_uv=False)
    lash_obj = bm_to_obj(bm_lash, f'{key}_lashes', col, lash_mat)
    return eyes_obj, lash_obj, lid_objs, lid_bones


def build_brows(key, col, center, R, F, brow_mat):
    """Build real 3D sculpted storybook eyebrows hovering cleanly above the eyes."""
    C = Vector(center)
    ez = F.get('eye_z', -0.06)
    ex = F.get('eye_x', 0.34)
    ew = F.get('eye_w', 0.21)
    eh = F.get('eye_h', 0.20)
    brow_z0 = ez + eh * 1.24 + F.get('brow_gap', 0.06)
    brow_w = F.get('brow_thick', 0.044)
    brow_arch = F.get('brow_arch', 0.055)
    brow_tilt = F.get('brow_tilt', 0.0)

    bm = bmesh.new()
    segs = 6
    n_pts = 7
    for s in (1.0, -1.0):
        pts, radii = [], []
        for i in range(n_pts):
            t = i / (n_pts - 1)
            a = -0.90 + 1.92 * t
            ux = s * (ex + a * ew * 0.96)
            uz = brow_z0 + brow_arch * math.sin(math.pi * t) - brow_tilt * (t - 0.5) * 0.14
            surf = head_front_y(F, ux, uz)
            pts.append(C + Vector((surf.x, surf.y - 0.036, surf.z)) * R)
            taper = math.sin(math.pi * (0.14 + 0.82 * t)) * (1.05 - 0.36 * t)
            radii.append(brow_w * max(0.30, taper) * R)

        rings = []
        for i, (pt, rad) in enumerate(zip(pts, radii)):
            t_vec = (pts[min(i + 1, n_pts - 1)] - pts[max(i - 1, 0)]).normalized()
            up_n = t_vec.cross(Vector((0.0, -1.0, 0.0)))
            up_n = Vector((0.0, 0.0, 1.0)) if up_n.length < 1e-4 else up_n.normalized()
            out_n = up_n.cross(t_vec).normalized()
            if out_n.y > 0:
                out_n = -out_n
            rings.append([
                bm.verts.new(pt + up_n * (math.cos(a) * rad) + out_n * (math.sin(a) * rad * 0.65))
                for a in (k / segs * math.tau for k in range(segs))
            ])
        loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)

    return bm_to_obj(bm, f'{key}_brows', col, brow_mat)


def build_talking_mouth(key, col, center, R, F, mouth_mat, teeth_mat):
    """Build a cute curved 3D smiling open-mouth cup driven by the 'mouth' bone."""
    C = Vector(center)
    mz = F.get('mouth_z', -0.60)
    mw = F.get('mouth_w', 0.20) * 0.88

    bm = bmesh.new()
    segs = 14
    center_surf = head_front_y(F, 0.0, mz - 0.04)
    center_v = bm.verts.new(C + Vector((0.0, center_surf.y - 0.020, mz - 0.045)) * R)
    ring = []
    for i in range(segs):
        a = i / segs * math.tau
        ux = math.cos(a) * mw
        sa = math.sin(a)
        uz = mz + (sa * 0.020 if sa >= 0 else sa * 0.115) - 0.008
        surf = head_front_y(F, ux, uz)
        ring.append(bm.verts.new(C + Vector((ux, surf.y - 0.025, uz)) * R))

    for i in range(segs):
        f = bm.faces.new((center_v, ring[i], ring[(i + 1) % segs]))
        f.material_index = 0

    t_top, t_bot = [], []
    for i in range(5):
        tx = (-0.64 + 1.28 * (i / 4.0)) * mw
        surf = head_front_y(F, tx, mz)
        t_top.append(bm.verts.new(C + Vector((tx, surf.y - 0.028, mz + 0.008)) * R))
        t_bot.append(bm.verts.new(C + Vector((tx, surf.y - 0.029, mz - 0.022)) * R))
    for i in range(4):
        f = bm.faces.new((t_top[i], t_bot[i], t_bot[i + 1], t_top[i + 1]))
        f.material_index = 1

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if sum(f.normal.y for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)

    obj = bm_to_obj(bm, f'{key}_mouth', col)
    obj.data.materials.append(mouth_mat)
    obj.data.materials.append(teeth_mat)

    top_b = C + Vector((0.0, center_surf.y - 0.02, mz + 0.014)) * R
    bot_b = top_b - Vector((0.0, 0.0, 0.12 * R))
    return obj, (top_b, bot_b)


# ------------------------------------------------------------------ cohesive Pixar hair & beards
def _sample_bezier_curve(ctrl_pts, n_samples=8):
    """Evaluate a smooth cubic/quadratic Bezier spline through ctrl_pts for silky curved hair locks."""
    pts = [Vector(q) for q in ctrl_pts]
    m = len(pts) - 1
    out = []
    for k in range(n_samples):
        u = k / max(1, n_samples - 1)
        # De Casteljau's algorithm -> guaranteed C-infinity smooth curve with zero boxy bends!
        work = [p.copy() for p in pts]
        for r in range(m):
            work = [work[i].lerp(work[i + 1], u) for i in range(len(work) - 1)]
        out.append(work[0])
    return out


def _add_hair_lock(bm, pts, r0, r_mid, r_tip, flat=0.72, segs=7):
    """Build a smooth Pixar-stylized sculpted hair lock along a 3D spline with soft rounded tips."""
    n = len(pts)
    rings = []
    # Smooth parallel-transport framing so curved locks never twist or kink!
    tangents = [(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(n)]
    t0 = tangents[0]
    ax = t0.cross(Vector((0.0, 0.0, 1.0)))
    ax = t0.orthogonal() if ax.length < 1e-3 else ax.normalized()
    bx = t0.cross(ax).normalized()
    for i, p in enumerate(pts):
        u = i / max(1, n - 1)
        ti = tangents[i]
        if i > 0:
            q = tangents[i - 1].rotation_difference(ti)
            ax = (q @ ax)
            ax = (ax - ti * ax.dot(ti)).normalized()
            bx = ti.cross(ax).normalized()
        if u < 0.38:
            t2 = u / 0.38
            r = r0 + (r_mid - r0) * math.sin(t2 * math.pi * 0.5)
        else:
            t2 = (u - 0.38) / 0.62
            r = r_mid * math.cos(t2 * math.pi * 0.48) + r_tip * (t2 ** 1.35)
        rings.append([
            bm.verts.new(p + ax * (math.cos(a) * r) + bx * (math.sin(a) * r * flat))
            for a in (k / segs * math.tau for k in range(segs))
        ])
    loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)


def build_boy_hair(name, col, center, R, F, hair_mat):
    """Build cohesive, soft tousled Pixar/Ghibli boy hair with smooth wavy crown, back & nape tufts."""
    C = Vector(center)
    bm = bmesh.new()

    # 1) Sculpted organic wavy hair dome (compact 24x11 grid -> lush rear volume & comfortable tri budget!)
    u_segs, v_segs = 24, 11
    rings = []
    for j in range(v_segs + 1):
        tv = j / v_segs
        ring = []
        for i in range(u_segs):
            th = i / u_segs * math.tau   # -pi/2 = front (-Y), +pi/2 = back (+Y), 0/pi = sides
            front_f = max(0.0, -math.sin(th))
            back_f = max(0.0, math.sin(th))
            side_f = abs(math.cos(th))

            # Soft natural hairline: open forehead, curved sideburn dip, clean ear arch, gentle nape curve
            hl_z = 0.45 * front_f - 0.68 * back_f - 0.05 * side_f
            ear_ang_l = abs((th - 0.18 + math.pi) % math.tau - math.pi)
            ear_ang_r = abs((th - (math.pi - 0.18) + math.pi) % math.tau - math.pi)
            ear_arch = (math.exp(-(ear_ang_l / 0.28) ** 2) + math.exp(-(ear_ang_r / 0.28) ** 2)) * 0.22
            sb_l = abs((th + 0.26 + math.pi) % math.tau - math.pi)
            sb_r = abs((th - (math.pi + 0.26) + math.pi) % math.tau - math.pi)
            sb_dip = (math.exp(-(sb_l / 0.20) ** 2) + math.exp(-(sb_r / 0.20) ** 2)) * 0.22
            nape_wave = 0.045 * back_f * math.sin(5.0 * th + 0.4)
            hl_z = hl_z + ear_arch - sb_dip + nape_wave

            phi_bot = math.asin(max(-0.88, min(0.75, hl_z)))
            phi = math.pi * 0.495 * (1.0 - tv) + phi_bot * tv

            sdir = Vector((math.cos(phi) * math.cos(th), math.cos(phi) * math.sin(th), math.sin(phi)))
            p_base = head_shape(sdir, F)

            # Soft sculpted storybook hair waves flowing asymmetrically across crown & back
            wave = (
                1.0
                + 0.16 * math.sin(4.0 * th + 0.6 + 2.0 * tv) * math.sin(tv * math.pi * 0.90)
                + 0.10 * math.cos(6.0 * th - 1.5 * tv) * math.sin(tv * math.pi)
            )
            crown_lift = 0.20 * math.exp(-((th - 1.10) ** 2) / 2.2 - ((tv - 0.24) / 0.28) ** 2)
            back_fluff = 0.22 * back_f * math.sin(tv * math.pi * 0.84)
            edge_taper = smoothstep(1.0, 0.72, tv)
            puff = (0.20 + 0.12 * (1.0 - tv) + back_fluff + crown_lift) * wave * (0.36 + 0.64 * edge_taper)
            p_out = p_base + sdir * (0.022 if tv > 0.94 else puff)
            ring.append(bm.verts.new(C + p_out * R))
        rings.append(ring)

    loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=False)
    inner_c = bm.verts.new(C + Vector((0.0, 0.04, 0.06)) * R)
    for i in range(u_segs):
        bm.faces.new((rings[-1][(i + 1) % u_segs], rings[-1][i], inner_c))

    # 2) Sweeping smooth Bezier bangs across upper forehead (soft curved tips, CLEAR of eyebrows!)
    bangs_spec = [
        (-0.56, 0.66, -0.76, 0.24, 0.145, 0.10),
        (-0.34, 0.74, -0.10, 0.44, 0.165, 0.15),
        (-0.02, 0.77,  0.26, 0.42, 0.175, 0.16),
        ( 0.28, 0.72,  0.54, 0.36, 0.155, 0.14),
        ( 0.56, 0.62,  0.76, 0.22, 0.145, 0.10),
    ]
    for sx, sz, ex2, ez2, rmid, fpuff in bangs_spec:
        pts = []
        for k in range(6):
            u = k / 5.0
            ux = sx + (ex2 - sx) * (u ** 1.12)
            uz = sz + (ez2 - sz) * (u ** 1.08) + 0.045 * math.sin(u * math.pi)
            surf = head_front_y(F, max(-0.88, min(0.88, ux)), max(-0.2, min(0.95, uz)))
            out_y = surf.y - (0.065 + fpuff * math.sin(u * math.pi * 0.80))
            pts.append(C + Vector((ux, out_y, uz)) * R)
        _add_hair_lock(bm, pts, rmid * 0.72 * R, rmid * R, 0.014 * R, flat=0.64, segs=6)

    # 3) Silky curved Ghibli/Pixar cowlicks, layered rear wave tufts & feathered nape wisps
    #    (De Casteljau Bezier curves -> smooth flowing arcs with zero boxy facets or crisscrossing cracks!)
    smooth_tufts = [
        # Playful crown cowlick sweeping gracefully up-right-back (soft charming silhouette from ALL angles!)
        ([(-0.18, 0.08, 1.04), (0.08, 0.22, 1.44), (0.44, 0.44, 1.40), (0.64, 0.62, 1.08)], 0.14, 0.19, 0.015, 0.72, 7),
        # Gentle upper-back crest wave arcing softly up-and-back (charming profile in side view!)
        ([(-0.10, 0.44, 1.02), (-0.28, 0.94, 1.32), (-0.42, 1.24, 1.08), (-0.44, 1.28, 0.76)], 0.14, 0.19, 0.016, 0.74, 7),
        # Soft right-back sweeping wave tuft curving cleanly along upper-mid back
        ([( 0.20, 0.62, 0.92), ( 0.64, 1.18, 0.76), ( 0.96, 1.16, 0.30), ( 0.86, 1.02, -0.06)], 0.14, 0.20, 0.016, 0.72, 7),
        # Soft left-back sweeping wave tuft curving cleanly along mid-back
        ([(-0.26, 0.66, 0.88), (-0.72, 1.16, 0.68), (-0.98, 1.12, 0.24), (-0.86, 0.98, -0.10)], 0.14, 0.20, 0.016, 0.72, 7),
        # Cozy center-back layered curl sweeping gently down-right (catches golden cel highlight from behind!)
        ([(-0.04, 0.78, 0.72), ( 0.08, 1.34, 0.42), ( 0.26, 1.32, -0.04), ( 0.14, 1.10, -0.36)], 0.15, 0.21, 0.016, 0.72, 7),
        # Soft curved nape wisps feathering organically along the rear neckline
        ([(-0.48, 0.72, -0.08), (-0.70, 0.98, -0.38), (-0.48, 1.02, -0.66)], 0.10, 0.135, 0.012, 0.68, 6),
        ([(-0.08, 0.86, -0.14), (-0.22, 1.16, -0.46), ( 0.04, 1.14, -0.74)], 0.11, 0.150, 0.012, 0.68, 6),
        ([( 0.36, 0.78, -0.10), ( 0.58, 1.06, -0.40), ( 0.40, 1.04, -0.66)], 0.10, 0.140, 0.012, 0.68, 6),
    ]
    for ctrl, r0, rmid, rtip, fl, sg in smooth_tufts:
        curve = _sample_bezier_curve(ctrl, n_samples=7)
        _add_hair_lock(bm, [C + q * R for q in curve], r0 * R, rmid * R, rtip * R, flat=fl, segs=sg)

    return bm_to_obj(bm, name, col, hair_mat)


def build_beard(name, col, center, R, F, beard_mat, style='full'):
    """Build cohesive sculpted 3D storybook beard (soft rounded U-bottom) + friendly curved moustache."""
    C = Vector(center)
    mz = F.get('mouth_z', -0.60)
    nz = F.get('nose_z', -0.34)
    mw = F.get('mouth_w', 0.20)
    bm = bmesh.new()

    if style == 'full':
        drop_len, jaw_thick, side_top, cheek_top, back_cut, round_pow = 0.48, 0.22, -0.10, mz + 0.08, 0.30, 0.72
    elif style == 'neat':
        drop_len, jaw_thick, side_top, cheek_top, back_cut, round_pow = 0.30, 0.145, -0.14, mz + 0.06, 0.24, 0.78
    else:
        drop_len, jaw_thick, side_top, cheek_top, back_cut, round_pow = 0.16, 0.105, -0.16, mz + 0.06, 0.20, 0.80

    u_segs, v_segs = 16, 6
    grid_outer, grid_inner = [], []
    for j in range(v_segs + 1):
        tv = j / v_segs
        row_o, row_i = [], []
        for i in range(u_segs + 1):
            tu = i / u_segs * 2.0 - 1.0
            ang = -math.pi * 0.5 + tu * (math.pi * 0.56)
            ax = abs(tu)
            top_z = cheek_top + (side_top - cheek_top) * smoothstep(0.26, 0.86, ax)
            # Gentle mouth opening dip that keeps chin lip neatly connected (no weird gap under lip!)
            top_z -= (0.095 if style != 'trimmed' else 0.065) * math.exp(-(tu / 0.24) ** 2)
            # Soft rounded U-bottom instead of sharp V-point!
            front_full = max(0.0, math.cos(tu * math.pi * 0.5)) ** round_pow
            bot_z = -0.96 - drop_len * front_full + 0.38 * (ax ** 2.1)
            z = top_z + (bot_z - top_z) * tv

            z_clamped = max(-0.98, min(0.5, z))
            r_xy = math.sqrt(max(0.04, 1.0 - z_clamped * z_clamped * 0.85))
            sdir = Vector((r_xy * math.cos(ang), min(back_cut, r_xy * math.sin(ang)), z_clamped)).normalized()
            p_head = head_shape(sdir, F)

            v_prof = math.sin(tv * math.pi * 0.88) ** 0.70
            thick = jaw_thick * (0.48 + 0.52 * front_full) * v_prof + 0.038
            if style == 'full':
                thick *= 1.0 + 0.045 * math.cos(tu * 5.0 * math.pi) * tv

            out_dir = Vector((math.cos(ang), math.sin(ang) * 0.92, -0.18 * tv)).normalized()
            p_outer = Vector((p_head.x, p_head.y, z)) + out_dir * thick
            if tv > 0.80:
                t_tip = (tv - 0.80) / 0.20
                p_outer.y += 0.10 * t_tip * front_full
                p_outer.x *= 1.0 - 0.05 * t_tip

            p_inner = Vector((p_head.x * 0.86, p_head.y + 0.08, z + 0.04 * tv))
            row_o.append(bm.verts.new(C + p_outer * R))
            row_i.append(bm.verts.new(C + p_inner * R))
        grid_outer.append(row_o)
        grid_inner.append(row_i)

    for j in range(v_segs):
        for i in range(u_segs):
            bm.faces.new((grid_outer[j][i], grid_outer[j + 1][i], grid_outer[j + 1][i + 1], grid_outer[j][i + 1]))
            bm.faces.new((grid_inner[j][i], grid_inner[j][i + 1], grid_inner[j + 1][i + 1], grid_inner[j + 1][i]))
    for i in range(u_segs):
        bm.faces.new((grid_outer[0][i], grid_outer[0][i + 1], grid_inner[0][i + 1], grid_inner[0][i]))
        bm.faces.new((grid_outer[-1][i], grid_inner[-1][i], grid_inner[-1][i + 1], grid_outer[-1][i + 1]))
    for j in range(v_segs):
        bm.faces.new((grid_outer[j][0], grid_inner[j][0], grid_inner[j + 1][0], grid_outer[j + 1][0]))
        bm.faces.new((grid_outer[j][-1], grid_outer[j + 1][-1], grid_inner[j + 1][-1], grid_inner[j][-1]))

    # Friendly curved 3D moustache under the nose
    m_z0 = 0.45 * nz + 0.55 * mz + 0.035
    m_rad = 0.082 if style == 'full' else (0.064 if style == 'neat' else 0.054)
    m_span = mw * (1.72 if style == 'full' else 1.48)
    for s in (1.0, -1.0):
        pts = []
        for k in range(5):
            u = k / 4.0
            ux = s * (0.02 + m_span * u)
            uz = m_z0 - 0.095 * (u ** 1.45) + (0.025 * math.sin(u * math.pi) if style == 'full' else 0.0)
            surf = head_front_y(F, ux, uz)
            out = 0.075 + 0.045 * math.sin(u * math.pi * 0.85)
            pts.append(C + Vector((ux, surf.y - out, uz)) * R)
        _add_hair_lock(bm, pts, m_rad * 0.72 * R, m_rad * R, m_rad * 0.34 * R, flat=0.72, segs=6)

    return bm_to_obj(bm, name, col, beard_mat)
