"""Storybook v4 3D head/face builder: round sculpted faces, big warm catchlight eyes, soft hair clumps & beards."""
import math
import bmesh
import numpy as np
from mathutils import Vector, Matrix

from lib import (
    bm_to_obj,
    hex_rgb,
    lin,
    loft_rings,
    pack_image,
    paint_bm,
    smoothstep,
)

# Face + eye atlas coordinates inside the 512x512 PNG:
FACE_U0, FACE_U1 = 0.02, 0.58
FACE_V0, FACE_V1 = 0.16, 0.84
FACE_X_MIN, FACE_X_MAX = -0.95, 0.95
FACE_Z_MIN, FACE_Z_MAX = -1.18, 0.82

EYE_U0, EYE_U1 = 0.64, 0.98
EYE_V0, EYE_V1 = 0.56, 0.90


def head_shape(p, F):
    """Map unit sphere point p -> warm Pixar/storybook round head (units of R, -Y = front, +Z = up)."""
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
    cheek_full = F.get('cheek_full', 0.12)
    cheek_g = math.exp(-((abs(x) - (ex + 0.16)) / 0.30) ** 2 - ((z - (ez - 0.30)) / 0.28) ** 2) * front
    x += math.copysign(cheek_full * 0.74 * cheek_g, x)
    y -= cheek_full * 0.56 * cheek_g

    # Soft orbital eye sockets so larger 3D eyes nestle naturally
    for s in (1.0, -1.0):
        dx = (x - s * ex) / (F.get('eye_w', 0.22) * 1.24)
        dz = (z - ez) / (F.get('eye_h', 0.22) * 1.24)
        d2 = dx * dx + dz * dz
        if d2 < 2.2 and y < -0.25:
            y += 0.112 * math.exp(-d2 * 1.15) * front

    # Gentle brow ridge above sockets
    brow_z = ez + F.get('eye_h', 0.22) * 1.34
    brow_g = math.exp(-((z - brow_z) / 0.14) ** 2 - (x / 0.65) ** 2) * front
    y -= 0.052 * brow_g

    # Soft rounded 3D storybook nose (cute rounded button tip, soft nostril wings, smooth profile — never sharp!)
    nz = F.get('nose_z', -0.34)
    n_len = F.get('nose_len', 0.16) * 1.00
    n_w = F.get('nose_w', 0.14)
    n_lift = F.get('nose_lift', 0.018)
    if y < -0.32:
        bridge_t = smoothstep(ez + 0.05, nz + 0.02, z) * smoothstep(nz - 0.12, nz - 0.01, z)
        bridge_x = math.exp(-(x / (n_w * 0.74)) ** 2)
        tip_g = math.exp(-((x / (n_w * 1.04)) ** 2 + ((z - nz) / (n_w * 0.96)) ** 2))
        ala_g = math.exp(-(((abs(x) - n_w * 0.76) / (n_w * 0.52)) ** 2 + ((z - (nz - 0.026)) / (n_w * 0.46)) ** 2))
        nose_push = (0.56 * bridge_t * bridge_x + 0.94 * tip_g + 0.36 * ala_g) * n_len * front
        y -= nose_push
        z += n_lift * tip_g * front

    # Warm lip cushion + soft rounded chin pad
    mz = F.get('mouth_z', -0.60)
    if y < -0.30:
        muzzle = math.exp(-((x / 0.34) ** 2 + ((z - (mz - 0.015)) / 0.19) ** 2)) * front
        y -= 0.056 * muzzle
        groove = math.exp(-((x / 0.24) ** 2 + ((z - (mz - 0.14)) / 0.070) ** 2)) * front
        y += 0.020 * groove
        chin_pad = math.exp(-((x / 0.28) ** 2 + ((z - (mz - 0.25)) / 0.12) ** 2)) * front
        y -= 0.044 * chin_pad

    return Vector((x, y, z))


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
    """Paint a rich 512x512 Pixar-storybook face+eye atlas (soft blush, warm sculpted lips, vibrant radial iris)."""
    res = 512
    c = _Canvas(res, F['skin'])

    fx = FACE_X_MIN + (c.U - FACE_U0) / (FACE_U1 - FACE_U0) * (FACE_X_MAX - FACE_X_MIN)
    fz = FACE_Z_MIN + (c.V - FACE_V0) / (FACE_V1 - FACE_V0) * (FACE_Z_MAX - FACE_Z_MIN)
    in_face = (c.U >= FACE_U0) & (c.U <= FACE_U1) & (c.V >= FACE_V0) & (c.V <= FACE_V1)
    fpx = (FACE_X_MAX - FACE_X_MIN) / ((FACE_U1 - FACE_U0) * res)

    ez = F.get('eye_z', -0.06)
    ex = F.get('eye_x', 0.34)
    eh = F.get('eye_h', 0.22)
    ew = F.get('eye_w', 0.22)
    nz = F.get('nose_z', -0.34)
    mz = F.get('mouth_z', -0.60)
    mw = F.get('mouth_w', 0.20)

    # Subtle warm sunlit forehead & cheekbone lift (gives Pixar skin depth even in soft shade)
    d_fh = np.hypot(fx / 0.54, (fz - 0.34) / 0.30)
    c.blend((np.clip(1.0 - d_fh, 0.0, 1.0) ** 1.8) * 0.08 * in_face, '#FFF2DF')

    # Gentle rosy peach-coral cheek blush + sunlit upper cheekbone lift + cute nose-tip warmth
    blush = F.get('blush', 0.30)
    blush_col = F.get('blush_col', '#E87E6B')
    for s in (1.0, -1.0):
        # Soft rosy apple of the cheek
        d = np.hypot((fx - s * (ex + 0.12)) / 0.29, (fz - (ez - eh - 0.11)) / 0.19)
        c.blend((np.clip(1.0 - d, 0.0, 1.0) ** 1.65) * min(0.62, blush * 1.38) * in_face, blush_col)
        # Subtle warm sunlit highlight on upper cheek apple
        d_ch = np.hypot((fx - s * (ex + 0.14)) / 0.19, (fz - (ez - eh - 0.04)) / 0.10)
        c.blend((np.clip(1.0 - d_ch, 0.0, 1.0) ** 1.8) * 0.11 * in_face, '#FFF4E6')

    # Soft storybook nose: peachy-warm tip blush, cute cream tip shine, curved under-nose shadow & soft nostril ovals
    n_w = F.get('nose_w', 0.13)
    dn = np.hypot(fx / (n_w * 1.24), (fz - (nz + 0.012)) / 0.115)
    c.blend((np.clip(1.0 - dn, 0.0, 1.0) ** 1.75) * min(0.46, blush * 0.72) * in_face, blush_col)

    # Gentle sunlit nose bridge & rounded button-tip highlight
    d_nbr = np.hypot(fx / (n_w * 0.34), (fz - (nz + 0.095)) / 0.115)
    c.blend((np.clip(1.0 - d_nbr, 0.0, 1.0) ** 1.8) * 0.13 * in_face, '#FFF6EA')
    d_nhi = np.hypot(fx / (n_w * 0.48), (fz - (nz + 0.022)) / 0.068)
    c.blend((np.clip(1.0 - d_nhi, 0.0, 1.0) ** 1.6) * 0.22 * in_face, '#FFF7EC')

    # Warm terracotta-sienna under-nose crescent + soft cute nostril shading (gentle, never a dark smudge!)
    sock_col = F.get('socket_col', '#98593F')
    nost_col = F.get('nostril_col', '#8B4D35')
    n_arc_z = nz - 0.062 + 0.022 * np.clip((fx / max(n_w * 0.95, 1e-4)) ** 2, 0.0, 1.3)
    d_nsh = np.hypot(fx / (n_w * 1.02), (fz - n_arc_z) / 0.044)
    c.blend((np.clip(1.0 - d_nsh, 0.0, 1.0) ** 1.75) * 0.19 * in_face, sock_col)
    for s in (1.0, -1.0):
        # Soft shaded nostril ovals tucked gently beneath the rounded nose wings
        d_nost = np.hypot((fx - s * n_w * 0.56) / (n_w * 0.34), (fz - (nz - 0.048)) / 0.026)
        c.blend((np.clip(1.0 - d_nost, 0.0, 1.0) ** 1.65) * 0.21 * in_face, nost_col)
        # Soft nose-wing (ala) crease warmth defining the button-nose width
        d_ala = np.hypot((fx - s * n_w * 0.96) / (n_w * 0.28), (fz - (nz - 0.018)) / 0.048)
        c.blend((np.clip(1.0 - d_ala, 0.0, 1.0) ** 1.85) * 0.11 * in_face, sock_col)

    # Soft orbital socket warmth + delicate upper eyelid crease (clean cheeks below eyes!)
    for s in (1.0, -1.0):
        ds = np.hypot((fx - s * ex) / (ew * 1.24), (fz - (ez + 0.02)) / (eh * 1.16))
        c.blend((np.clip(1.0 - ds, 0.0, 1.0) ** 2.2) * 0.12 * in_face, sock_col)
        cr_pts = [
            (s * (ex + a * ew * 0.92), ez + eh * (0.98 + 0.24 * (1.0 - a * a)))
            for a in np.linspace(-0.76, 0.80, 10)
        ]
        sd_cr = c.stroke(fx, fz, cr_pts, 0.0075, 0.0030)
        c.sd_put(np.where(in_face, sd_cr, 1.0), fpx, sock_col, alpha=0.34, soft=1.9)

    # Gentle elder warmth: soft laugh crinkles & smile lines
    if F.get('age_lines', False):
        ac = F.get('age_col', '#945D44')
        for s in (1.0, -1.0):
            ox = s * (ex + ew * 1.14)
            sd1 = c.stroke(fx, fz, [(ox, ez + 0.02), (ox + s * 0.10, ez + 0.06)], 0.0075, 0.0028)
            sd2 = c.stroke(fx, fz, [(ox, ez - 0.05), (ox + s * 0.09, ez - 0.09)], 0.0075, 0.0028)
            c.sd_put(np.where(in_face, sd1, 1.0), fpx, ac, alpha=0.40, soft=1.8)
            c.sd_put(np.where(in_face, sd2, 1.0), fpx, ac, alpha=0.36, soft=1.8)
            pts_nl = [
                (s * (0.20 + 0.13 * t + 0.02 * math.sin(t * math.pi)), nz - 0.04 - (nz - mz + 0.05) * t)
                for t in np.linspace(0.0, 1.0, 8)
            ]
            sd_nl = c.stroke(fx, fz, pts_nl, 0.009, 0.0035)
            c.sd_put(np.where(in_face, sd_nl, 1.0), fpx, ac, alpha=0.32, soft=2.0)

    # Warm sculpted storybook lips + gentle resting smile + soft smile corner dimples
    smile = F.get('smile', 0.064)
    lip_col = F.get('lip_col', '#C86957')
    mouth_col = F.get('mouth_col', '#64241B')
    lip_a = min(0.68, F.get('lip_alpha', 0.38) * 1.38)
    # Soft upper lip with gentle cupid's-bow arch & fuller warm lower lip cushion
    up_arch = 0.010 * np.exp(-((np.abs(fx) - mw * 0.34) / (mw * 0.30)) ** 2) - 0.005 * np.exp(-(fx / (mw * 0.22)) ** 2)
    dlip_up = np.hypot(fx / (mw * 0.94), (fz - (mz + 0.012 + up_arch)) / 0.044)
    dlip_lo = np.hypot(fx / (mw * 0.96), (fz - (mz - 0.036)) / 0.054)
    c.blend((np.clip(1.0 - dlip_up, 0.0, 1.0) ** 1.45) * (lip_a * 0.88) * in_face, lip_col)
    c.blend((np.clip(1.0 - dlip_lo, 0.0, 1.0) ** 1.40) * (lip_a * 1.12) * in_face, lip_col)
    # Soft sunlit cushion glint on center of lower lip + gentle warm under-lip shadow
    dlip_hi = np.hypot(fx / (mw * 0.44), (fz - (mz - 0.038)) / 0.024)
    c.blend((np.clip(1.0 - dlip_hi, 0.0, 1.0) ** 1.55) * 0.18 * in_face, '#FFF3E8')
    dlip_sh = np.hypot(fx / (mw * 0.66), (fz - (mz - 0.094)) / 0.028)
    c.blend((np.clip(1.0 - dlip_sh, 0.0, 1.0) ** 1.65) * 0.22 * in_face, sock_col)

    us = np.linspace(-1.0, 1.0, 20)
    m_pts = [(mw * a, mz + smile * (a * a - 0.35)) for a in us]
    sd_m = c.stroke(fx, fz, m_pts, 0.0105, 0.0105)
    c.sd_put(np.where(in_face, sd_m, 1.0), fpx, mouth_col, alpha=0.88, soft=1.4)
    for s in (1.0, -1.0):
        cx0 = s * mw
        cz0 = mz + smile * 0.65
        sd_c = c.stroke(fx, fz, [(cx0, cz0), (cx0 + s * 0.026, cz0 + 0.019)], 0.0065, 0.0025)
        c.sd_put(np.where(in_face, sd_c, 1.0), fpx, mouth_col, alpha=0.62, soft=1.6)
        # Gentle warm smile dimple glow
        d_dimp = np.hypot((fx - (cx0 + s * 0.032)) / 0.044, (fz - (cz0 + 0.014)) / 0.034)
        c.blend((np.clip(1.0 - d_dimp, 0.0, 1.0) ** 1.75) * 0.16 * in_face, sock_col)

    # ---- 2) Dedicated 3D Eyeball Iris+Sclera quadrant (rich multi-layered warm Pixar eye!)
    eu = (c.U - EYE_U0) / (EYE_U1 - EYE_U0) * 2.0 - 1.0
    ev = (c.V - EYE_V0) / (EYE_V1 - EYE_V0) * 2.0 - 1.0
    in_eye = (c.U >= EYE_U0) & (c.U <= EYE_U1) & (c.V >= EYE_V0) & (c.V <= EYE_V1)
    epx = 2.0 / ((EYE_U1 - EYE_U0) * res)

    # Warm porcelain sclera with soft radial ambient falloff toward eye corners
    c.blend(in_eye.astype(np.float32), '#FFFDF9')
    edge_sh = np.clip((np.hypot(eu, ev) - 0.68) / 0.48, 0.0, 1.0) ** 1.6 * in_eye
    c.blend(edge_sh * 0.24, '#D9C8C2')
    # Soft upper-lid ambient shadow across top sclera (relaxed warm gaze)
    top_sh = np.clip((ev - 0.22) / 0.44, 0.0, 1.0) * in_eye
    c.blend(top_sh * 0.46, '#C8B8B8')

    ir = F.get('iris_r', 0.59)
    iy = ev + 0.025
    ir_dist = np.hypot(eu / ir, iy / (ir * 1.04))
    iris_sd = (ir_dist - 1.0) * ir

    # Rich vertical gradient + subtle radial iris fiber streaks
    g = np.clip((iy + ir) / (2.0 * ir), 0.0, 1.0)
    ang_e = np.arctan2(iy, eu)
    fibers = (
        0.5
        + 0.30 * np.sin(ang_e * 22.0 + 0.4)
        + 0.20 * np.cos(ang_e * 37.0 - 1.1)
    ) * np.clip(1.0 - np.abs(ir_dist - 0.65) / 0.34, 0.0, 1.0)
    col_hi = np.array(hex_rgb(F.get('iris_hi', '#2A1308')), dtype=np.float32)
    col_lo = np.array(hex_rgb(F.get('iris_lo', '#B87236')), dtype=np.float32)
    col_gl = np.array(hex_rgb(F.get('iris_glow', '#F4BC5C')), dtype=np.float32)
    iris_rgb = col_lo * (1.0 - g[..., None] ** 0.85) + col_hi * (g[..., None] ** 0.85)
    iris_rgb = iris_rgb * (0.92 + 0.18 * fibers[..., None]) + col_gl * (0.14 * fibers[..., None] * (1.0 - g[..., None]))
    iris_rgb = np.clip(iris_rgb, 0.0, 1.0)

    iris_mask = np.clip(0.5 - iris_sd / (epx * 1.4), 0.0, 1.0) * in_eye
    c.blend_img(iris_mask, iris_rgb)

    # Luminous sunlit honey lower-iris crescent (catches golden-hour warmth!)
    glow_d = np.hypot(eu / (ir * 0.74), (ev + ir * 0.34) / (ir * 0.36))
    glow_m = np.clip(1.0 - glow_d, 0.0, 1.0) ** 1.25 * iris_mask * 0.76
    c.blend(glow_m, F.get('iris_glow', '#F4BC5C'))

    # Soft dark limbal ring framing the iris
    ring_sd = np.abs(ir_dist - 0.93) * ir - 0.048
    c.sd_put(np.where(in_eye, np.maximum(ring_sd, iris_sd - 0.02), 1.0), epx, F.get('iris_hi', '#241008'), alpha=0.92, soft=1.3)

    # Deep warm pupil
    pup_r = ir * F.get('pupil_ratio', 0.45)
    pup_sd = (np.hypot(eu / pup_r, (ev + 0.01) / (pup_r * 1.04)) - 1.0) * pup_r
    c.sd_put(np.where(in_eye, pup_sd, 1.0), epx, '#140905', alpha=1.0, soft=1.2)

    # Crisp sky-window primary catchlight + warm golden secondary sparkle + soft lower rim glint
    hl1 = (np.hypot((eu + ir * 0.33) / (ir * 0.27), (ev - ir * 0.30) / (ir * 0.29)) - 1.0) * (ir * 0.27)
    hl2 = (np.hypot((eu - ir * 0.30) / (ir * 0.12), (ev + ir * 0.36) / (ir * 0.12)) - 1.0) * (ir * 0.12)
    hl3 = (np.hypot((eu + ir * 0.06) / (ir * 0.075), (ev - ir * 0.48) / (ir * 0.065)) - 1.0) * (ir * 0.075)
    c.sd_put(np.where(in_eye, hl1, 1.0), epx, '#FFFFFF', alpha=0.99, soft=1.0)
    c.sd_put(np.where(in_eye, hl2, 1.0), epx, '#FFF8EA', alpha=0.92, soft=1.0)
    c.sd_put(np.where(in_eye, hl3, 1.0), epx, '#FFFBF2', alpha=0.72, soft=1.2)

    return pack_image(key + '_face', c.img)


# ------------------------------------------------------------------ head, ears, eyes, lids, brows, mouth
def build_head_mesh(name, col, center, R, F, face_mat):
    """Build smooth sculpted 3D head (28x22) with integrated nose, cheeks, eye sockets, and optional ears."""
    C = Vector(center)
    bm = bmesh.new()

    # Smooth front head mesh (packed around eyes/nose/mouth via v_angles) staying well under 9k tris
    u_segs = 26
    v_segs = 21
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
            ret = bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=1.0)
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
        is_back = all(v.co.y > 0.12 for v in f.verts)
        for loop in f.loops:
            p = loop.vert.co
            if is_ear or is_back:
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

    # White vertex colour so the embedded face atlas drives the exact painted skin/blush/smile
    return bm_to_obj(bm, name, col, face_mat, color=(1.0, 1.0, 1.0), ensure_uv=False)


def apply_soft_face_normals(mesh_obj, head_center, R, F):
    """Gently soften cheek/mouth normals for soft PBR shading while keeping 88% of 3D roundness & nose relief."""
    me = mesh_obj.data
    C = Vector(head_center)
    face_slots = {
        idx for idx, m in enumerate(me.materials)
        if m is not None and m.name.startswith('face_')
    }
    if not face_slots or not me.uv_layers:
        return

    uv_data = me.uv_layers[0].data
    head_skin_verts = set()
    for poly in me.polygons:
        if poly.material_index not in face_slots:
            continue
        for li in poly.loop_indices:
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
        chin_keep = smoothstep(-1.14, -0.88, p.z)
        n_soft = Vector((p.x * 0.80, -0.88, 0.18 + 0.28 * max(-0.55, p.z))).normalized()

        # Keep true 3D normals strong on the sculpted nose & brow ridge so PBR sunlight models the face cleanly
        nose_x = math.exp(-(p.x / (n_w * 1.25)) ** 2)
        nose_z = smoothstep(nz_pos - 0.15, nz_pos - 0.04, p.z) * smoothstep(ez + 0.05, nz_pos + 0.08, p.z)
        nose_y = smoothstep(-0.66, -0.92, p.y)
        nose_m = nose_x * nose_z * nose_y

        blend = 0.20 * front_m * chin_keep * (1.0 - 0.92 * nose_m)
        norms[vi] = norms[vi].lerp(n_soft, blend).normalized()

    me.normals_split_custom_set_from_vertices([tuple(n) for n in norms])


def build_eyes_and_lids(key, col, center, R, F, eye_mat, skin_mat, hair_mat):
    """Build larger glossy 3D eyeballs ('eye'), sculpted lash rims ('hair'), and blinking eyelids ('skin'+'hair')."""
    C = Vector(center)
    ez = F.get('eye_z', -0.06)
    ex = F.get('eye_x', 0.34)
    ew = F.get('eye_w', 0.22)
    eh = F.get('eye_h', 0.22)
    eye_tilt = F.get('eye_tilt', 0.03)

    bm_eyes = bmesh.new()
    uv_eyes = bm_eyes.loops.layers.uv.new('UVMap')
    bm_lash = bmesh.new()

    lid_objs = []
    lid_bones = {}

    skin_rgb = lin(F['skin'])
    lash_rgb = lin('#24140D')

    for sd, s in (('l', 1.0), ('r', -1.0)):
        surf = head_front_y(F, s * ex, ez)
        eye_center_u = Vector((s * ex, surf.y + ew * 0.42, ez))
        eye_center_w = C + eye_center_u * R
        yaw = s * 0.22
        rot_eye = Matrix.Rotation(yaw, 3, 'Z')

        # 1) Smooth 14x7 domed eyeball
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

        # 2) Sculpted upper lash arch hugging top rim of the eyeball
        lash_w = F.get('lash_thick', 0.032)
        n_arc = 12
        arc_pts = []
        for i in range(n_arc):
            t = i / (n_arc - 1)
            ang = math.pi * (0.98 - 1.00 * t)
            lx = s * math.cos(ang) * ew * 0.96
            lz = (math.sin(ang) * 0.68 + 0.08 + eye_tilt * (t - 0.5) * 2.0) * eh * 0.94
            rn = min(0.94, math.hypot(lx / (ew * 1.00), lz / (eh * 1.00)))
            ly = -math.sqrt(max(0.05, 1.0 - rn * rn)) * ew * 0.66 - 0.015
            pu = eye_center_u + (rot_eye @ Vector((lx, ly, lz)))
            h_surf = head_front_y(F, pu.x, pu.z)
            pu.y = min(pu.y, h_surf.y - 0.016)
            thick = lash_w * (0.48 + 0.72 * math.sin(math.pi * min(1.0, t * 0.85 + 0.10)))
            if t > 0.76 and F.get('lashes', False):
                thick *= 1.20
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

        # 3) Blinking eyelid dome (slot 0 = skin, slot 1 = hair lash rim)
        bm_lid = bmesh.new()
        col_lid = bm_lid.loops.layers.float_color.new('Color')
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
                is_rim = (j == lid_v - 1)
                f.material_index = 1 if is_rim else 0
                rgba = (*lash_rgb, 1.0) if is_rim else (*skin_rgb, 1.0)
                for lp in f.loops:
                    lp[col_lid] = rgba

        bmesh.ops.recalc_face_normals(bm_lid, faces=bm_lid.faces)
        if sum(f.normal.y for f in bm_lid.faces) > 0:
            bmesh.ops.reverse_faces(bm_lid, faces=bm_lid.faces)
        lid_obj = bm_to_obj(bm_lid, f'{key}_lid_{sd}', col, uv_mode='zero')
        lid_obj.data.materials.append(skin_mat)
        lid_obj.data.materials.append(hair_mat)
        lid_objs.append((f'lid_{sd}', lid_obj))

        top_bone = eye_center_w + (rot_eye @ Vector((0.0, -ew * 0.66, eh * 0.96))) * R
        bot_bone = eye_center_w + (rot_eye @ Vector((0.0, -ew * 0.66, -eh * 0.92))) * R
        lid_bones[f'lid_{sd}'] = (top_bone, bot_bone)

    eyes_obj = bm_to_obj(bm_eyes, f'{key}_eyes', col, eye_mat, color=(1.0, 1.0, 1.0), ensure_uv=False)
    lash_obj = bm_to_obj(bm_lash, f'{key}_lashes', col, hair_mat, color='#24140D', uv_mode='zero')
    return eyes_obj, lash_obj, lid_objs, lid_bones


def build_brows(key, col, center, R, F, hair_mat):
    """Build soft sculpted 3D storybook eyebrows using shared 'hair' material & brow colour in COLOR_0."""
    C = Vector(center)
    ez = F.get('eye_z', -0.06)
    ex = F.get('eye_x', 0.34)
    ew = F.get('eye_w', 0.22)
    eh = F.get('eye_h', 0.22)
    brow_z0 = ez + eh * 1.24 + F.get('brow_gap', 0.06)
    brow_w = F.get('brow_thick', 0.044)
    brow_arch = F.get('brow_arch', 0.055)
    brow_tilt = F.get('brow_tilt', 0.0)

    bm = bmesh.new()
    segs = 6
    n_pts = 8
    for s in (1.0, -1.0):
        pts, radii = [], []
        for i in range(n_pts):
            t = i / (n_pts - 1)
            a = -0.90 + 1.92 * t
            ux = s * (ex + a * ew * 0.96)
            uz = brow_z0 + brow_arch * math.sin(math.pi * t) - brow_tilt * (t - 0.5) * 0.14
            surf = head_front_y(F, ux, uz)
            pts.append(C + Vector((surf.x, surf.y - 0.034, surf.z)) * R)
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

    return bm_to_obj(bm, f'{key}_brows', col, hair_mat, color=F['brow_col'], uv_mode='zero')


def build_talking_mouth(key, col, center, R, F, hair_mat):
    """Build curved 3D smiling open-mouth cup & teeth driven by the 'mouth' bone (vertex-coloured on 'hair')."""
    C = Vector(center)
    mz = F.get('mouth_z', -0.60)
    mw = F.get('mouth_w', 0.20) * 0.88

    bm = bmesh.new()
    col_l = bm.loops.layers.float_color.new('Color')
    m_rgba = (*lin('#69221C'), 1.0)
    t_rgba = (*lin('#FFF6EA'), 1.0)

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
        for lp in f.loops:
            lp[col_l] = m_rgba

    t_top, t_bot = [], []
    for i in range(5):
        tx = (-0.64 + 1.28 * (i / 4.0)) * mw
        surf = head_front_y(F, tx, mz)
        t_top.append(bm.verts.new(C + Vector((tx, surf.y - 0.028, mz + 0.008)) * R))
        t_bot.append(bm.verts.new(C + Vector((tx, surf.y - 0.029, mz - 0.022)) * R))
    for i in range(4):
        f = bm.faces.new((t_top[i], t_bot[i], t_bot[i + 1], t_top[i + 1]))
        for lp in f.loops:
            lp[col_l] = t_rgba

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if sum(f.normal.y for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)

    obj = bm_to_obj(bm, f'{key}_mouth', col, hair_mat, uv_mode='zero')
    top_b = C + Vector((0.0, center_surf.y - 0.02, mz + 0.014)) * R
    bot_b = top_b - Vector((0.0, 0.0, 0.12 * R))
    return obj, (top_b, bot_b)


# ------------------------------------------------------------------ soft strand-clump hair & beards
def _sample_bezier_curve(ctrl_pts, n_samples=8):
    pts = [Vector(q) for q in ctrl_pts]
    m = len(pts) - 1
    out = []
    for k in range(n_samples):
        u = k / max(1, n_samples - 1)
        work = [p.copy() for p in pts]
        for _ in range(m):
            work = [work[i].lerp(work[i + 1], u) for i in range(len(work) - 1)]
        out.append(work[0])
    return out


def _add_hair_lock(bm, pts, r0, r_mid, r_tip, flat=0.72, segs=7, base_rgb=None, tip_rgb=None):
    """Build a smooth Pixar-stylized hair strand clump with soft tapered tip & optional root-to-tip tint."""
    n = len(pts)
    rings = []
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

    prev_faces = set(bm.faces)
    loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)

    if base_rgb is not None:
        tip_rgb = tip_rgb or base_rgb
        col_l = bm.loops.layers.float_color.get('Color') or bm.loops.layers.float_color.new('Color')
        v_u = {}
        for i, ring in enumerate(rings):
            u = i / max(1, n - 1)
            for v in ring:
                v_u[v] = u
        for f in bm.faces:
            if f in prev_faces:
                continue
            for lp in f.loops:
                u = v_u.get(lp.vert, 0.5)
                rgb = tuple(base_rgb[c] + (tip_rgb[c] - base_rgb[c]) * (u ** 0.8) for c in range(3))
                lp[col_l] = (rgb[0], rgb[1], rgb[2], 1.0)


def build_boy_hair(name, col, center, R, F, hair_mat, hair_hex):
    """Build cohesive soft tousled boy hair with layered sculpted strand clumps & sunlit root-to-tip warmth."""
    C = Vector(center)
    bm = bmesh.new()
    col_l = bm.loops.layers.float_color.new('Color')
    base_rgb = lin(hair_hex)
    root_rgb = (base_rgb[0] * 0.78, base_rgb[1] * 0.75, base_rgb[2] * 0.74)
    tip_rgb = (min(1.0, base_rgb[0] * 1.16), min(1.0, base_rgb[1] * 1.12), min(1.0, base_rgb[2] * 1.05))

    # 1) Sculpted silky wavy hair dome (24x11) with natural integrated sweeping fringe & round crown
    u_segs, v_segs = 24, 11
    rings = []
    for j in range(v_segs + 1):
        tv = j / v_segs
        ring = []
        for i in range(u_segs):
            th = i / u_segs * math.tau
            front_f = max(0.0, -math.sin(th))
            back_f = max(0.0, math.sin(th))
            side_f = abs(math.cos(th))

            # Natural sculpted hairline with subtle side-swept forehead fringe arch (clear of eyebrows!)
            fringe_dip = 0.085 * math.sin(3.0 * th + 0.7) * front_f
            hl_z = 0.36 * front_f - 0.68 * back_f - 0.05 * side_f + fringe_dip
            ear_ang_l = abs((th - 0.18 + math.pi) % math.tau - math.pi)
            ear_ang_r = abs((th - (math.pi - 0.18) + math.pi) % math.tau - math.pi)
            ear_arch = (math.exp(-(ear_ang_l / 0.28) ** 2) + math.exp(-(ear_ang_r / 0.28) ** 2)) * 0.24
            sb_l = abs((th + 0.26 + math.pi) % math.tau - math.pi)
            sb_r = abs((th - (math.pi + 0.26) + math.pi) % math.tau - math.pi)
            sb_dip = (math.exp(-(sb_l / 0.20) ** 2) + math.exp(-(sb_r / 0.20) ** 2)) * 0.22
            nape_wave = 0.052 * back_f * math.sin(6.0 * th + 0.4)
            hl_z = hl_z + ear_arch - sb_dip + nape_wave

            phi_bot = math.asin(max(-0.88, min(0.75, hl_z)))
            # Start at phi = 82 deg (not 89.1 deg) so crown closes smoothly without pole pinch!
            phi = math.pi * 0.455 * (1.0 - tv) + phi_bot * tv

            sdir = Vector((math.cos(phi) * math.cos(th), math.cos(phi) * math.sin(th), math.sin(phi)))
            p_base = head_shape(sdir, F)

            wave = (
                1.0
                + 0.12 * math.sin(5.0 * th + 0.6 + 2.0 * tv) * math.sin(tv * math.pi * 0.90)
                + 0.08 * math.cos(8.0 * th - 1.5 * tv) * math.sin(tv * math.pi)
            )
            crown_lift = 0.14 * math.exp(-((th - 1.10) ** 2) / 2.2 - ((tv - 0.24) / 0.30) ** 2)
            back_fluff = 0.22 * back_f * math.sin(tv * math.pi * 0.84)
            edge_taper = smoothstep(1.0, 0.72, tv)
            puff = (0.20 + 0.10 * (1.0 - tv) + back_fluff + crown_lift) * wave * (0.38 + 0.62 * edge_taper)
            p_out = p_base + sdir * (0.025 if tv > 0.94 else puff)
            ring.append(bm.verts.new(C + p_out * R))
        rings.append(ring)

    # Smooth rounded crown cap (one lifted center vertex -> zero facet ridge on crown!)
    crown_c = sum((v.co for v in rings[0]), Vector()) / u_segs + Vector((0.0, 0.0, 0.032 * R))
    crown_v = bm.verts.new(crown_c)
    loft_rings(bm, rings, closed_u=True, cap_start=False, cap_end=False)
    for i in range(u_segs):
        bm.faces.new((rings[0][(i + 1) % u_segs], rings[0][i], crown_v))
    inner_c = bm.verts.new(C + Vector((0.0, 0.04, 0.06)) * R)
    for i in range(u_segs):
        bm.faces.new((rings[-1][(i + 1) % u_segs], rings[-1][i], inner_c))

    # Paint dome with gentle sunlit crown gradient
    for f in bm.faces:
        for lp in f.loops:
            zn = max(0.0, min(1.0, (lp.vert.co.z - (C.z - 0.6 * R)) / (1.8 * R)))
            rgb = tuple(root_rgb[c] + (tip_rgb[c] - root_rgb[c]) * (0.25 + 0.65 * zn) for c in range(3))
            lp[col_l] = (rgb[0], rgb[1], rgb[2], 1.0)

    # 2) Soft wide overlapping side-swept storybook fringe ribbons (hugging the hair dome smoothly!)
    bangs_spec = [
        # (start_x, start_z, mid_x, mid_z, end_x, end_z, r_mid, flat)
        (-0.62, 0.84, -0.74, 0.56, -0.80, 0.24, 0.14, 0.40),
        (-0.44, 0.90, -0.22, 0.68,  0.02, 0.41, 0.19, 0.36),
        (-0.14, 0.94,  0.14, 0.70,  0.42, 0.40, 0.20, 0.36),
        ( 0.24, 0.88,  0.52, 0.64,  0.72, 0.30, 0.16, 0.38),
        ( 0.56, 0.78,  0.74, 0.50,  0.80, 0.20, 0.13, 0.40),
    ]
    for sx, sz, mx, mz, ex2, ez2, rmid, fl in bangs_spec:
        pts = []
        for k in range(7):
            u = k / 6.0
            # Quadratic Bezier sweeping smoothly out of the crown and tucking down across the forehead
            ux = (1 - u) * (1 - u) * sx + 2 * (1 - u) * u * mx + u * u * ex2
            uz = (1 - u) * (1 - u) * sz + 2 * (1 - u) * u * mz + u * u * ez2
            surf = head_front_y(F, max(-0.88, min(0.88, ux)), max(-0.2, min(0.95, uz)))
            out_y = surf.y - (0.028 + 0.082 * math.sin(u * math.pi * 0.85))
            pts.append(C + Vector((ux, out_y, uz)) * R)
        _add_hair_lock(bm, pts, rmid * 0.82 * R, rmid * R, 0.026 * R, flat=fl, segs=6, base_rgb=root_rgb, tip_rgb=tip_rgb)

    # 3) Soft rounded Bezier strand clumps hugging crown, sides, back & nape (seen from behind in gameplay!)
    smooth_tufts = [
        ([(-0.20, 0.06, 1.02), (0.08, 0.20, 1.32), (0.42, 0.40, 1.26), (0.60, 0.56, 0.98)], 0.135, 0.180, 0.032, 0.68, 6),
        ([( 0.04, 0.26, 1.04), (-0.18, 0.62, 1.26), (-0.40, 0.98, 1.04), (-0.50, 1.08, 0.70)], 0.135, 0.180, 0.032, 0.70, 6),
        ([(-0.10, 0.42, 0.98), ( 0.18, 0.86, 1.20), ( 0.40, 1.12, 0.96), ( 0.42, 1.14, 0.64)], 0.135, 0.180, 0.032, 0.70, 6),
        ([( 0.22, 0.58, 0.86), ( 0.62, 1.08, 0.70), ( 0.88, 1.06, 0.28), ( 0.78, 0.94, -0.06)], 0.135, 0.185, 0.032, 0.68, 6),
        ([(-0.26, 0.62, 0.84), (-0.68, 1.06, 0.62), (-0.90, 1.02, 0.22), (-0.78, 0.90, -0.08)], 0.135, 0.185, 0.032, 0.68, 6),
        ([(-0.04, 0.72, 0.68), ( 0.08, 1.22, 0.40), ( 0.22, 1.18, -0.02), ( 0.12, 1.00, -0.34)], 0.145, 0.195, 0.034, 0.68, 6),
        ([(-0.34, 0.76, 0.42), (-0.50, 1.16, 0.08), (-0.38, 1.08, -0.28)], 0.125, 0.165, 0.030, 0.66, 5),
        ([( 0.34, 0.76, 0.42), ( 0.52, 1.14, 0.06), ( 0.38, 1.06, -0.28)], 0.125, 0.165, 0.030, 0.66, 5),
        # Soft rounded nape waves hugging the back of the head (zero spiky tips!)
        ([(-0.48, 0.66, -0.08), (-0.62, 0.86, -0.34), (-0.42, 0.84, -0.58)], 0.095, 0.125, 0.030, 0.64, 5),
        ([(-0.10, 0.80, -0.14), (-0.20, 1.02, -0.42), ( 0.00, 0.96, -0.64)], 0.105, 0.140, 0.032, 0.64, 5),
        ([( 0.26, 0.76, -0.12), ( 0.42, 0.98, -0.38), ( 0.28, 0.90, -0.60)], 0.100, 0.130, 0.030, 0.64, 5),
    ]
    for ctrl, r0, rmid, rtip, fl, sg in smooth_tufts:
        curve = _sample_bezier_curve(ctrl, n_samples=6)
        _add_hair_lock(bm, [C + q * R for q in curve], r0 * R, rmid * R, rtip * R, flat=fl, segs=sg, base_rgb=root_rgb, tip_rgb=tip_rgb)

    return bm_to_obj(bm, name, col, hair_mat, uv_mode='zero')


def build_beard(name, col, center, R, F, hair_mat, beard_hex, style='full'):
    """Build soft sculpted 3D beard (rounded U-bottom with gentle hair-clump waves) + curved moustache."""
    C = Vector(center)
    mz = F.get('mouth_z', -0.60)
    nz = F.get('nose_z', -0.34)
    mw = F.get('mouth_w', 0.20)
    bm = bmesh.new()
    col_l = bm.loops.layers.float_color.new('Color')

    base_rgb = lin(beard_hex)
    deep_rgb = (base_rgb[0] * 0.82, base_rgb[1] * 0.82, base_rgb[2] * 0.84)
    lit_rgb = (min(1.0, base_rgb[0] * 1.08), min(1.0, base_rgb[1] * 1.07), min(1.0, base_rgb[2] * 1.04))

    if style == 'full':
        drop_len, jaw_thick, side_top, cheek_top, back_cut, round_pow = 0.48, 0.22, -0.10, mz + 0.08, 0.30, 0.72
    elif style == 'neat':
        drop_len, jaw_thick, side_top, cheek_top, back_cut, round_pow = 0.30, 0.145, -0.14, mz + 0.06, 0.24, 0.78
    else:
        drop_len, jaw_thick, side_top, cheek_top, back_cut, round_pow = 0.17, 0.112, -0.16, mz + 0.055, 0.20, 0.82

    u_segs, v_segs = 17, 6
    grid_outer, grid_inner = [], []
    for j in range(v_segs + 1):
        tv = j / v_segs
        row_o, row_i = [], []
        for i in range(u_segs + 1):
            tu = i / u_segs * 2.0 - 1.0
            span_ang = 0.48 if style == 'trimmed' else 0.56
            ang = -math.pi * 0.5 + tu * (math.pi * span_ang)
            ax = abs(tu)
            top_z = cheek_top + (side_top - cheek_top) * smoothstep(0.26, 0.86, ax)
            # Clean mouth opening without leaving a chin slit on trimmed beard
            dip = 0.088 if style == 'full' else (0.072 if style == 'neat' else 0.048)
            top_z -= dip * math.exp(-(tu / 0.23) ** 2)
            front_full = max(0.0, math.cos(tu * math.pi * 0.5)) ** round_pow
            bot_z = -0.98 - drop_len * front_full + 0.38 * (ax ** 2.1)
            z = top_z + (bot_z - top_z) * tv

            z_clamped = max(-0.98, min(0.5, z))
            r_xy = math.sqrt(max(0.04, 1.0 - z_clamped * z_clamped * 0.85))
            sdir = Vector((r_xy * math.cos(ang), min(back_cut, r_xy * math.sin(ang)), z_clamped)).normalized()
            p_head = head_shape(sdir, F)

            v_prof = math.sin(tv * math.pi * 0.88) ** 0.68
            side_taper = smoothstep(1.0, 0.72, ax) if style == 'trimmed' else (0.55 + 0.45 * smoothstep(1.0, 0.78, ax))
            thick = (jaw_thick * (0.50 + 0.50 * front_full) * v_prof + 0.036) * (0.25 + 0.75 * side_taper)
            # Soft vertical sculpted hair-clump waves that read warmly under low sun
            clump_amp = 0.065 if style == 'full' else (0.045 if style == 'neat' else 0.030)
            thick *= 1.0 + clump_amp * math.cos(tu * 6.0 * math.pi) * math.sin(tv * math.pi)

            out_dir = Vector((math.cos(ang), math.sin(ang) * 0.92, -0.18 * tv)).normalized()
            p_outer = Vector((p_head.x, p_head.y, z)) + out_dir * thick
            if tv > 0.78:
                t_tip = (tv - 0.78) / 0.22
                p_outer.y += 0.11 * t_tip * front_full
                p_outer.x *= 1.0 - 0.05 * t_tip

            p_inner = Vector((p_head.x * 0.84, p_head.y + 0.08, z + 0.03 * tv))
            row_o.append(bm.verts.new(C + p_outer * R))
            row_i.append(bm.verts.new(C + p_inner * R))
        grid_outer.append(row_o)
        grid_inner.append(row_i)

    def _put_beard_face(vs, tv_frac, is_inner=False):
        f = bm.faces.new(vs)
        k = 0.15 if is_inner else (0.85 - 0.35 * tv_frac)
        rgb = tuple(deep_rgb[c] + (lit_rgb[c] - deep_rgb[c]) * k for c in range(3))
        for lp in f.loops:
            lp[col_l] = (rgb[0], rgb[1], rgb[2], 1.0)

    for j in range(v_segs):
        tv = j / v_segs
        for i in range(u_segs):
            _put_beard_face((grid_outer[j][i], grid_outer[j + 1][i], grid_outer[j + 1][i + 1], grid_outer[j][i + 1]), tv)
            _put_beard_face((grid_inner[j][i], grid_inner[j][i + 1], grid_inner[j + 1][i + 1], grid_inner[j + 1][i]), tv, True)
    for i in range(u_segs):
        _put_beard_face((grid_outer[0][i], grid_outer[0][i + 1], grid_inner[0][i + 1], grid_inner[0][i]), 0.0)
        _put_beard_face((grid_outer[-1][i], grid_inner[-1][i], grid_inner[-1][i + 1], grid_outer[-1][i + 1]), 1.0)
    for j in range(v_segs):
        tv = j / v_segs
        _put_beard_face((grid_outer[j][0], grid_inner[j][0], grid_inner[j + 1][0], grid_outer[j + 1][0]), tv)
        _put_beard_face((grid_outer[j][-1], grid_outer[j + 1][-1], grid_inner[j + 1][-1], grid_inner[j][-1]), tv)

    # Soft curved 3D moustache under the nose
    m_z0 = 0.45 * nz + 0.55 * mz + 0.035
    m_rad = 0.084 if style == 'full' else (0.066 if style == 'neat' else 0.056)
    m_span = mw * (1.72 if style == 'full' else 1.50)
    for s in (1.0, -1.0):
        pts = []
        for k in range(6):
            u = k / 5.0
            ux = s * (0.015 + m_span * u)
            uz = m_z0 - 0.095 * (u ** 1.45) + (0.025 * math.sin(u * math.pi) if style == 'full' else 0.0)
            surf = head_front_y(F, ux, uz)
            out = 0.075 + 0.045 * math.sin(u * math.pi * 0.85)
            pts.append(C + Vector((ux, surf.y - out, uz)) * R)
        _add_hair_lock(bm, pts, m_rad * 0.72 * R, m_rad * R, m_rad * 0.32 * R, flat=0.70, segs=6, base_rgb=lit_rgb, tip_rgb=base_rgb)

    return bm_to_obj(bm, name, col, hair_mat, uv_mode='zero')
