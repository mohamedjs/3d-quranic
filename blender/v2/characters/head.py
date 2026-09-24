# Anime head: sculpted-by-function skull + pointed chin, painted face texture (eyes, brows,
# nose, mouth, blush, age lines), blink lids + talking mouth driven by extra bones.
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from toon_lib import *

def ss(e0, e1, x):
    t = min(1, max(0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)

# texture window in head units (R = 1): x in [-1.2, 1.2], z in [Z0, Z0 + 2.4]
Z0 = -1.6; SPAN = 2.4

def head_shape(p, F):
    """Unit sphere point -> anime head (units of R, centre = skull centre, -Y = front)."""
    x, y, z = p
    x *= F.get('skull_w', 0.94); y *= 1.0
    j = ss(0.15, -1.0, z)                          # 0 at the crown, 1 under the jaw
    front = ss(0.35, -0.85, y)
    x *= 1 - F.get('jaw_narrow', 0.40) * j ** 1.15 * (0.55 + 0.45 * front)
    if y > 0: y *= 1 - 0.5 * j                     # back of the jaw tucks into the neck
    z -= F.get('chin', 0.48) * j * front ** 1.3     # chin drops in front
    y -= 0.05 * j * front
    if y < -0.62: y = -0.62 + (y + 0.62) * 0.55     # flat anime face plane
    if z > 0: z *= F.get('crown', 1.0)
    # cheek fullness (kids / grannies)
    ck = F.get('cheeks', 0.0) * math.exp(-((z + 0.55) / 0.35) ** 2) * front
    x *= 1 + ck
    return Vector((x, y, z))

def build_head(name, col, center, R, F, mat):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=22, radius=1.0)
    for v in bm.verts: v.co = head_shape(v.co, F)
    # ears
    if F.get('ears', True):
        for s in (1, -1):
            e = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=8, radius=1.0)
            for v in e['verts']:
                v.co = Vector((v.co.x * 0.06 + s * 0.83, v.co.y * 0.14 + 0.1, v.co.z * 0.21 - 0.4))
                v.co = Matrix.Rotation(-0.25 * s, 3, 'Z') @ (v.co - Vector((s * 0.83, 0.1, 0))) + Vector((s * 0.83, 0.1, 0))
    uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        for l in f.loops:
            c = l.vert.co
            u = (c.x + 1.2) / SPAN; vv = (c.z - Z0) / SPAN
            if c.y > 0.05 or abs(c.x) > 0.8: u = 0.0 if c.x < 0 else 1.0   # sides/back: skin border
            l[uv].uv = (min(1, max(0, u)), min(1, max(0, vv)))
    for v in bm.verts: v.co = v.co * R + Vector(center)
    o = bm_obj(bm, name, col, mat)
    return o

# ---------------------------------------------------------------- face painting
class Canvas:
    def __init__(self, res, skin):
        self.res = res; self.px = SPAN / res
        xs = -1.2 + (np.arange(res) + 0.5) * self.px; zs = Z0 + (np.arange(res) + 0.5) * self.px
        self.X, self.Z = np.meshgrid(xs, zs)
        self.img = np.ones((res, res, 3)) * np.array(hex_rgb(skin))
    def put(self, sd, color, alpha=1.0, soft=1.0):
        a = np.clip(0.5 - sd / (self.px * soft), 0, 1) * alpha
        c = np.array(hex_rgb(color) if isinstance(color, str) else color)
        self.img = self.img * (1 - a[..., None]) + c * a[..., None]
    def put_col(self, sd, colimg, alpha=1.0):
        a = np.clip(0.5 - sd / self.px, 0, 1) * alpha
        self.img = self.img * (1 - a[..., None]) + colimg * a[..., None]
    def ellipse(self, cx, cz, rx, rz):
        return (np.sqrt(((self.X - cx) / rx) ** 2 + ((self.Z - cz) / rz) ** 2) - 1) * min(rx, rz)
    def stroke(self, pts, w0, w1=None):
        """Distance field of a polyline with width tapering w0 -> w1 (half widths)."""
        w1 = w0 if w1 is None else w1
        P = np.array(pts); n = len(P); best = np.full(self.X.shape, 1e9)
        L = np.concatenate([[0], np.cumsum(np.linalg.norm(P[1:] - P[:-1], axis=1))]); L /= max(L[-1], 1e-9)
        for i in range(n - 1):
            a, b = P[i], P[i + 1]; ab = b - a; l2 = max(ab @ ab, 1e-12)
            t = np.clip(((self.X - a[0]) * ab[0] + (self.Z - a[1]) * ab[1]) / l2, 0, 1)
            d = np.hypot(self.X - (a[0] + t * ab[0]), self.Z - (a[1] + t * ab[1]))
            w = w0 + (w1 - w0) * (L[i] + t * (L[i + 1] - L[i]))
            best = np.minimum(best, d - w)
        return best

def paint_face(key, F):
    c = Canvas(F.get('res', 1024), F['skin'])
    X, Z = c.X, c.Z
    ez, ex, ew, eh = F['eye_z'], F['eye_x'], F['eye_w'], F['eye_h']
    # blush
    for s in (1, -1):
        d = np.sqrt(((X - s * (ex + 0.1)) / 0.2) ** 2 + ((Z - (ez - eh - 0.12)) / 0.09) ** 2)
        c.img = c.img * (1 - (np.clip(1 - d, 0, 1) ** 1.5 * F.get('blush', 0.35))[..., None]) + np.array(hex_rgb(F.get('blush_col', '#E88A7A'))) * (np.clip(1 - d, 0, 1) ** 1.5 * F.get('blush', 0.35))[..., None]
    line = F.get('line', '#3A1C10')
    for s in (1, -1):
        u = (X - s * ex) * s / ew; v = (Z - ez) / eh       # u > 0 toward the outer corner
        uc = np.clip(u, -1, 1)
        top = F.get('lid_top', 0.8) * (1 - uc ** 2) ** 0.7 + 0.12 * uc + F.get('lid_lift', 0.0) * uc
        bot = -F.get('lid_bot', 0.85) * (1 - uc ** 2) ** 0.9 + 0.05 * uc
        open_sd = np.maximum.reduce([(v - top) * eh, (bot - v) * eh, (np.abs(u) - 1) * ew])
        c.put(open_sd, '#FFFDF8')
        # lid shadow on the sclera
        c.put(np.maximum(open_sd, (top - 0.28 - v) * eh), '#D9CFCB', 1.0)
        ix, iz = -0.08, -0.1 + F.get('iris_up', 0.0)
        irx, irz = F.get('iris_rx', 0.56), F.get('iris_rz', 1.0)
        iris = np.sqrt(((u - ix) / irx) ** 2 + ((v - iz) / irz) ** 2)
        iris_sd = np.maximum((iris - 1) * irx * ew, open_sd)
        g = np.clip((v - iz + irz) / (2 * irz), 0, 1)[..., None]
        icol = np.array(hex_rgb(F['iris_lo'])) * (1 - g) + np.array(hex_rgb(F['iris_hi'])) * g
        c.put_col(iris_sd, icol)
        ring = np.maximum(np.abs(iris - 0.93) * irx * ew - 0.012, open_sd)
        c.put(ring, F['iris_hi'], 0.9)
        c.put(np.maximum((np.sqrt(((u - ix) / (irx * 0.45)) ** 2 + ((v - iz - 0.05) / (irz * 0.5)) ** 2) - 1) * irx * 0.45 * ew, open_sd), F.get('pupil', '#1E0E08'))
        # soft light arc in the lower iris
        arc = np.maximum.reduce([(np.sqrt(((u - ix) / (irx * 0.7)) ** 2 + ((v - iz + 0.35) / (irz * 0.38)) ** 2) - 1) * 0.06, open_sd, iris_sd])
        c.put(arc, F.get('iris_glow', '#E0A860'), 0.55)
        # highlights (same side on both eyes: light from the upper left of the picture)
        icx = s * ex + s * ix * ew
        c.put(np.maximum(c.ellipse(icx - 0.24 * ew, ez + 0.3 * eh, 0.17 * ew, 0.21 * eh), open_sd), '#FFFFFF')
        c.put(np.maximum(c.ellipse(icx + 0.22 * ew, ez - 0.4 * eh, 0.07 * ew, 0.08 * eh), open_sd), '#FFFFFF', 0.9)
        # upper lash line: thick, heavier at the outer corner, small flick
        us = np.linspace(-1.02, 1.08, 24)
        ut = np.clip(us, -1, 1)
        tl = F.get('lid_top', 0.8) * (1 - ut ** 2) ** 0.7 + 0.12 * ut + F.get('lid_lift', 0.0) * ut
        pts = [(s * ex + s * a * ew, ez + b * eh + 0.012) for a, b in zip(us, tl)]
        lw = F.get('lash_w', 0.022)
        c.put(c.stroke(pts, lw * 0.5, lw * 1.1), line)
        if F.get('lashes', False):
            for a, ang in ((0.72, 0.9), (0.92, 0.55)):
                bx, bz = s * ex + s * a * ew, ez + (F.get('lid_top', 0.8) * (1 - a * a) ** 0.7 + 0.12 * a + F.get('lid_lift', 0) * a) * eh
                c.put(c.stroke([(bx, bz), (bx + s * 0.05 * math.cos(ang), bz + 0.05 * math.sin(ang) + 0.01)], 0.009, 0.002), line)
        # lower lash hint
        us = np.linspace(0.15, 0.95, 10)
        pts = [(s * ex + s * a * ew, ez + (-F.get('lid_bot', 0.85) * (1 - a * a) ** 0.9 + 0.05 * a) * eh - 0.008) for a in us]
        c.put(c.stroke(pts, 0.004, 0.009), F.get('line_soft', '#7A4A30'))
        # brows
        bz0 = ez + eh * (F.get('lid_top', 0.8) + 0.12) + F.get('brow_gap', 0.13)
        bw = F.get('brow_w', 0.018)
        us = np.linspace(-0.85, 1.05, 12)
        pts = [(s * ex + s * a * ew, bz0 + F.get('brow_arch', 0.05) * (1 - a * a) - F.get('brow_tilt', 0.0) * a) for a in us]
        c.put(c.stroke(pts, bw, bw * 0.45), F.get('brow_col', '#3A1C10'))
        # age lines
        if F.get('age_lines'):
            k = F.get('age_col', '#B07A5E')
            ox = s * (ex + ew * 1.15)
            for dz, ang in ((0.02, 0.35), (-0.06, -0.3)):
                c.put(c.stroke([(ox, ez + dz), (ox + s * 0.08, ez + dz + 0.08 * math.tan(ang))], 0.006, 0.002), k)
            pts = [(s * ex + s * a * ew, ez - eh * 1.05 - 0.035 - 0.03 * (1 - a * a)) for a in np.linspace(-0.6, 0.7, 8)]
            c.put(c.stroke(pts, 0.004, 0.003), k, 0.8)
            # smile folds
            nz, mz = F['nose_z'], F['mouth_z']
            pts = [(s * (0.14 + 0.1 * t + 0.03 * math.sin(t * 3)), nz - 0.02 - (nz - mz + 0.02) * t) for t in np.linspace(0, 1, 8)]
            c.put(c.stroke(pts, 0.006, 0.003), k, 0.7)
    # nose: small shadow tick + nostril dot
    nz = F['nose_z']
    c.put(c.stroke([(0.035, nz + 0.08), (0.05, nz + 0.01), (0.012, nz - 0.012)], 0.009, 0.006), F.get('nose_col', '#A2603F'))
    # mouth: gentle smile
    mz, mw = F['mouth_z'], F['mouth_w']
    pts = [(mw * a, mz + F.get('smile', 0.03) * (a * a - 0.3) + (0.012 * a * a * a if False else 0)) for a in np.linspace(-1, 1, 14)]
    c.put(c.stroke(pts, 0.009, 0.009), F.get('mouth_col', '#6B2A20'))
    for s in (1, -1):   # upturned corners
        c.put(c.stroke([(s * mw, mz + F.get('smile', 0.03) * 0.7), (s * (mw + 0.025), mz + F.get('smile', 0.03) * 0.7 + 0.018)], 0.006, 0.003), F.get('mouth_col', '#6B2A20'))
    return save_image(key + '_face', c.img)

# ---------------------------------------------------------------- lids + mouth
def surface_patch(name, col, head_obj, center, R, pts2d, mat, offset=0.0012):
    """Flat 2D polygon fan (head units, x/z) projected onto the head front along +Y."""
    bvh = BVHTree.FromObject(head_obj, bpy.context.evaluated_depsgraph_get())
    bm = bmesh.new(); vs = []
    cx, cy, cz = center
    for x, z in pts2d:
        o = Vector((cx + x * R, cy - 3 * R, cz + z * R))
        hit = bvh.ray_cast(o, Vector((0, 1, 0)))
        p = hit[0] if hit[0] else Vector((cx + x * R, cy - 0.6 * R, cz + z * R))
        n = hit[1] if hit[1] else Vector((0, -1, 0))
        vs.append(bm.verts.new(p + n * offset))
    return bm, vs

def lid_patch(col, head_obj, center, R, F, s, skin_mat, lash_mat):
    ex, ez, ew, eh = s * F['eye_x'], F['eye_z'], F['eye_w'], F['eye_h']
    n = 9; rows = 5
    grid = []
    for j in range(rows + 1):          # from upper lid (j=0) down to the lower lid line
        t = j / rows; row = []
        for i in range(n + 1):
            a = -1.08 + 2.18 * i / n; ac = max(-1, min(1, a))
            top = F.get('lid_top', 0.8) * (1 - ac * ac) ** 0.7 + 0.12 * ac + F.get('lid_lift', 0.0) * ac + 0.18
            bot = -F.get('lid_bot', 0.85) * (1 - ac * ac) ** 0.9 + 0.05 * ac - 0.05
            row.append((ex + s * a * ew, ez + (top + (bot - top) * t) * eh))
        grid.append(row)
    flat = [p for r in grid for p in r]
    bm, vs = surface_patch('lid', col, head_obj, center, R, flat, None, offset=0.0016 * R / 0.1)
    for j in range(rows):
        for i in range(n):
            a, b, c2, d = vs[j * (n + 1) + i], vs[j * (n + 1) + i + 1], vs[(j + 1) * (n + 1) + i + 1], vs[(j + 1) * (n + 1) + i]
            f = bm.faces.new((a, b, c2, d) if s < 0 else (b, a, d, c2))
            f.material_index = 1 if j == rows - 1 else 0
    o = bm_obj(bm, f'_lid_{"l" if s > 0 else "r"}', col)
    o.data.materials.append(skin_mat); o.data.materials.append(lash_mat)
    bm2 = bmesh.new(); bm2.from_mesh(o.data); bm2.normal_update()
    if sum(f.normal.y for f in bm2.faces) > 0: bmesh.ops.reverse_faces(bm2, faces=bm2.faces)
    bm2.to_mesh(o.data); bm2.free()
    top_z = center[2] + (ez + (F.get('lid_top', 0.8) + 0.12) * eh) * R
    bot_z = center[2] + (ez - F.get('lid_bot', 0.85) * eh) * R
    return o, (Vector((center[0] + ex * R, center[1] - 0.9 * R, top_z)), Vector((center[0] + ex * R, center[1] - 0.9 * R, bot_z)))

def mouth_patch(col, head_obj, center, R, F, mat):
    mz, mw = F['mouth_z'], F['mouth_w'] * 0.8
    pts = [(0, mz - 0.03)]
    ring = []
    for i in range(16):
        a = i / 16 * math.tau
        x = math.cos(a) * mw; z = math.sin(a)
        z = (z * 0.012 if z > 0 else z * 0.07) + mz - 0.005
        ring.append((x, z))
    bm, vs = surface_patch('mouth', col, head_obj, center, R, pts + ring, None, offset=0.0022 * R / 0.1)
    for i in range(16): bm.faces.new((vs[0], vs[1 + i], vs[1 + (i + 1) % 16]))
    bm.normal_update()
    if sum(f.normal.y for f in bm.faces) > 0: bmesh.ops.reverse_faces(bm, faces=bm.faces)
    o = bm_obj(bm, '_mouth', col, mat)
    top = Vector((center[0], center[1] - 0.9 * R, center[2] + (mz + 0.012) * R))
    return o, (top, top - Vector((0, 0, 0.08 * R)))

