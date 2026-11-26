"""M4 Egyptian Date Palms (`palm_a`, `palm_b`, `palm_c`, `palm_d`) with Poly Haven `palm_bark`.

Rebuilds all 4 date-palm variants preserving exact v3 heights, leans, and origins so no
colliders change:
  - Curved trunk built as a true rhombic diamond leaf-scar lattice (both LOD0 and LOD1!):
    deep dark recessed diagonal crevices framing protruding upward-lipped diamond boots with
    warm cinnamon-tan per-diamond vertex shading + blended radial/facet normals, on top of
    material `ph_bark` (layer 8 of `buildingMaterial.js` texture array) with clean vertical-grain
    metric cylindrical UVs.
  - Graceful 3-tier arching V-folded fronds + dry golden skirt fronds on `foliage_frond`
    (existing shared foliage atlas, spherical canopy normals).
  - Clustered hanging amber/ruby Egyptian date bunches on vertex-coloured `foliage_solid`
    (LOD0 only).

Budgets: LOD0 <= 2,500 tris, LOD1 <= 500 tris. Geometry-only GLBs (no embedded images).
Run headless from repo root:
  blender -b --factory-startup --python blender/v4/env/palms.py
"""
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector, noise

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib

# Shared v3 foliage atlas UV rects (glTF bottom-left origin)
UV_PALM_FROND = (0.000, 0.500, 0.500, 1.000)
UV_PALM_DRY   = (0.000, 0.000, 0.250, 0.500)

# Exact v3 heights, leans, and seed contracts so placement & colliders stay identical
PALM_SPECS = {
    'palm_a': (7.2,  0.85,  0.20, 17, 0.56, 301, 5, 4),   # classic graceful Nile village palm
    'palm_b': (9.4,  1.65, -0.35, 19, 0.62, 302, 5, 5),   # tall sweeping oasis landmark palm
    'palm_c': (5.2,  0.40,  0.25, 15, 0.46, 303, 4, 3),   # sturdy young canal-side palm
    'palm_d': (8.2, -1.25,  0.65, 17, 0.58, 304, 5, 4),   # wind-sculpted riverside palm
}

LOD0_BUDGET = 2500
LOD1_BUDGET = 500


def _tint_lin(r, g, b, rnd, spread=0.05):
    k = 1.0 + rnd.uniform(-spread, spread)
    return lib.rgb_srgb_to_linear(r * k, g * k, b * k)


def _simple_vcol_material(name):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    pbr = nt.nodes.new('ShaderNodeBsdfPrincipled')
    pbr.inputs['Roughness'].default_value = 0.80 if name == 'foliage_frond' else 0.55
    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = 'Color'
    nt.links.new(vc.outputs['Color'], pbr.inputs['Base Color'])
    nt.links.new(pbr.outputs['BSDF'], out.inputs['Surface'])
    return mat


def _spine_sample(t, h, lean, lean_y, seed):
    t = max(0.0, min(1.0, t))
    curve = t * t
    sway = 0.14 * math.sin(t * math.pi) * (1.0 if seed % 2 else -1.0)
    px = lean * curve + sway
    py = lean_y * curve
    pz = -0.20 + (h + 0.20) * t
    flare = 0.13 * math.exp(-t * 14.0)
    crown_swell = 0.055 * math.exp(-((1.0 - t) * 14.0) ** 2)
    rad = 0.285 * ((1.0 - t) ** 1.15) + 0.165 * t + flare + crown_swell
    return Vector((px, py, pz)), rad


def _build_trunk(name, h, lean, lean_y, seed, lod1=False):
    """Curved Egyptian date-palm trunk built as a closed rhombic diamond leaf-scar lattice.
    Both LOD0 and LOD1 keep the unmistakable diamond crevice/boot pattern and vertical-grain UVs."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    coll = bm.loops.layers.float_color.new('Color')

    if lod1:
        sides = 5
        n_half = max(8, min(12, int(round(h * 1.25))))
    else:
        sides = 6
        n_half = max(23, min(40, int(round(h * 4.3))))

    # Build spine frames along the curved trunk
    pts, rads, cum_len = [], [], [0.0]
    for i in range(n_half + 1):
        p, rad = _spine_sample(i / n_half, h, lean, lean_y, seed)
        pts.append(p)
        rads.append(rad)
        if i > 0:
            cum_len.append(cum_len[-1] + (pts[i] - pts[i - 1]).length)

    frames = []
    prev_right = Vector((1.0, 0.0, 0.0))
    for i, p in enumerate(pts):
        if i == 0:
            tang = (pts[1] - p).normalized()
        elif i == n_half:
            tang = (p - pts[i - 1]).normalized()
        else:
            tang = (pts[i + 1] - pts[i - 1]).normalized()
        right = prev_right - tang * prev_right.dot(tang)
        if right.length < 1e-4:
            right = Vector((0.0, 1.0, 0.0)).cross(tang)
        right.normalize()
        prev_right = right
        fwd = tang.cross(right).normalized()
        frames.append((p, rads[i], cum_len[i], tang, right, fwd))

    def trunk_shade(t):
        # Dark damp root collar, warm sunlit mid-trunk, shadowed collar right under the frond crown
        return (0.72 + 0.28 * min(1.0, t * 5.0)) * (1.0 - 0.24 * max(0.0, (t - 0.88) / 0.12))

    # Groove-corner rings: alternating half-step twist forms a true rhombic diamond lattice
    groove_d = 0.008 if lod1 else 0.015
    boot_h = 0.022 if lod1 else 0.038
    rings = []
    for i in range(n_half + 1):
        t = i / n_half
        p, rad, v_m, tang, right, fwd = frames[i]
        # Fade groove relief softly right at the underground root base & crown top
        relief_mask = min(1.0, i / 1.5) * min(1.0, (n_half - i) / 1.5)
        r_g = rad - groove_d * relief_mask
        ring = []
        off = 0.5 if (i % 2 == 1) else 0.0
        for k in range(sides):
            ang = ((k + off) / sides) * math.tau
            dir_v = right * math.cos(ang) + fwd * math.sin(ang)
            wob = 0.0 if lod1 else 0.006 * noise.noise(p * 2.1 + Vector((k * 1.4, seed * 0.7, 0.0)))
            pos = p + dir_v * (r_g + wob)
            ring.append((bm.verts.new(pos), dir_v, ang))
        rings.append(ring)

    # Warm Egyptian date-palm cinnamon-tan base colour (sRGB -> linear)
    base_srgb = (0.74, 0.53, 0.32)

    def col_rgba(srgb_scale, j_k=1.0, warm_shift=0.0):
        r = min(1.0, max(0.0, base_srgb[0] * srgb_scale * j_k + warm_shift))
        g = min(1.0, max(0.0, base_srgb[1] * srgb_scale * j_k + warm_shift * 0.4))
        b = min(1.0, max(0.0, base_srgb[2] * srgb_scale * j_k - warm_shift * 0.3))
        lin = lib.rgb_srgb_to_linear(r, g, b)
        return (lin[0], lin[1], lin[2], 1.0)

    circ_ref = math.tau * 0.24   # uniform cylindrical UV scale (~1.5 m around) so texture never stretches
    step_u = circ_ref / sides

    def add_tri(va, vb, vc, uvs, cols):
        try:
            f = bm.faces.new((va, vb, vc))
            f.smooth = True
            for lp, uv, c in zip(f.loops, uvs, cols):
                lp[uvl].uv = uv
                lp[coll] = c
            return f
        except ValueError:
            return None

    # Bottom half-skirt closing ring 0 (even) -> ring 1 (odd)
    v0, v1 = frames[0][2], frames[1][2]
    sh0, sh1 = trunk_shade(0.0), trunk_shade(1.0 / n_half)
    c_root0 = col_rgba(sh0 * 0.56)
    c_root1 = col_rgba(sh1 * 0.52)
    for k in range(sides):
        kn = (k + 1) % sides
        u_b0 = k * step_u
        u_b1 = (k + 1) * step_u
        u_m = (k + 0.5) * step_u
        add_tri(rings[0][k][0], rings[0][kn][0], rings[1][k][0],
                ((u_b0, v0), (u_b1, v0), (u_m, v1)), (c_root0, c_root0, c_root1))

    # Main shaft: true sculpted 4-tri rhombic diamond leaf-scar boots
    face_norm_targets = {}   # face -> (radial_dir, blend_weight) for crisp 3D diamond relief shading
    for i in range(n_half - 1):
        even = (i % 2 == 0)
        t_c = (i + 1.16) / n_half    # upper-biased lip apex creates real date-palm boot overhang!
        p_mid, rad_mid, v_mid, tang_m, right_m, fwd_m = frames[i + 1]
        p_c, rad_c = _spine_sample(t_c, h, lean, lean_y, seed)
        v_bot = frames[i][2]
        v_top = frames[i + 2][2]
        v_c = v_mid + (v_top - v_mid) * 0.16

        sh_b = trunk_shade(i / n_half)
        sh_m = trunk_shade((i + 1) / n_half)
        sh_t = trunk_shade((i + 2) / n_half)
        # Taper boot protrusion slightly near root base & top collar
        boot_scale = (0.78 + 0.32 * (i / max(1, n_half - 1)))
        if i == 0:
            boot_scale *= 0.65
        elif i == n_half - 2:
            boot_scale *= 0.72

        for k in range(sides):
            if even:
                vB = rings[i][k][0]
                vR = rings[i + 1][k][0]
                vT = rings[i + 2][k][0]
                vL = rings[i + 1][(k - 1) % sides][0]
                k_center = float(k)
            else:
                vB = rings[i][k][0]
                vR = rings[i + 1][(k + 1) % sides][0]
                vT = rings[i + 2][k][0]
                vL = rings[i + 1][k][0]
                k_center = k + 0.5

            ang_c = (k_center / sides) * math.tau
            dir_c = (right_m * math.cos(ang_c) + fwd_m * math.sin(ang_c)).normalized()
            # Subtle organic irregularity per individual leaf-scar boot
            j_k = 1.0 + rnd.uniform(-0.07, 0.07)
            warm_s = rnd.uniform(-0.025, 0.025)
            h_jit = boot_h * boot_scale * (1.0 + rnd.uniform(-0.14, 0.14))
            pos_c = p_c + dir_c * (rad_c + h_jit)
            vC = bm.verts.new(pos_c)

            # Seamless local unwrapped UVs per diamond (zero seam flip, strictly vertical V grain!)
            uC = k_center * step_u
            uL = uC - 0.5 * step_u
            uR = uC + 0.5 * step_u

            # Crisp date-palm diamond shading: deep dark diagonal grooves + warm sunlit upper ridge
            c_top_notch = col_rgba(sh_t * 0.38, j_k, -0.01)    # deepest shadow notch under next boot
            c_bot_groov = col_rgba(sh_b * 0.46, j_k, -0.01)    # bottom V-groove
            c_sid_groov = col_rgba(sh_m * 0.52, j_k,  0.00)    # side diagonal X-grooves
            c_lip_hi    = col_rgba(sh_m * 1.24, j_k,  warm_s + 0.02)  # sunlit upper boot shelf
            c_lip_lo    = col_rgba(sh_m * 0.98, j_k,  warm_s)         # shaded underside of boot lip

            f1 = add_tri(vB, vR, vC, ((uC, v_bot), (uR, v_mid), (uC, v_c)), (c_bot_groov, c_sid_groov, c_lip_lo))
            f2 = add_tri(vR, vT, vC, ((uR, v_mid), (uC, v_top), (uC, v_c)), (c_sid_groov, c_top_notch, c_lip_hi))
            f3 = add_tri(vT, vL, vC, ((uC, v_top), (uL, v_mid), (uC, v_c)), (c_top_notch, c_sid_groov, c_lip_hi))
            f4 = add_tri(vL, vB, vC, ((uL, v_mid), (uC, v_bot), (uC, v_c)), (c_sid_groov, c_bot_groov, c_lip_lo))
            for f in (f1, f2, f3, f4):
                if f is not None:
                    face_norm_targets[f] = dir_c

    # Top half-skirt closing ring (n_half - 1) -> ring (n_half)
    last = n_half
    prev = n_half - 1
    v_p, v_l = frames[prev][2], frames[last][2]
    sh_p, sh_l = trunk_shade(prev / n_half), trunk_shade(1.0)
    c_top0 = col_rgba(sh_p * 0.56)
    c_top1 = col_rgba(sh_l * 0.52)
    last_even = (last % 2 == 0)
    for k in range(sides):
        kn = (k + 1) % sides
        if last_even:
            # prev is odd (k+0.5), last is even (k, k+1)
            u_m = (k + 0.5) * step_u
            add_tri(rings[prev][k][0], rings[last][kn][0], rings[last][k][0],
                    ((u_m, v_p), ((k + 1) * step_u, v_l), (k * step_u, v_l)), (c_top0, c_top1, c_top1))
        else:
            # prev is even (k), last is odd (k-0.5, k+0.5)
            u_m = k * step_u
            add_tri(rings[prev][k][0], rings[last][k][0], rings[last][(k - 1) % sides][0],
                    ((u_m, v_p), ((k + 0.5) * step_u, v_l), ((k - 0.5) * step_u, v_l)), (c_top0, c_top1, c_top1))

    # Fibrous crown heart cap closing the trunk top
    top = pts[-1]
    top_ring = [x[0] for x in rings[-1]]
    c_top = bm.verts.new(top + Vector((0.0, 0.0, 0.14)))
    cap_col = col_rgba(0.45)
    for k in range(sides):
        kn = (k + 1) % sides
        add_tri(top_ring[k], top_ring[kn], c_top,
                ((k * step_u, v_l), ((k + 1) * step_u, v_l), ((k + 0.5) * step_u, v_l + 0.2)),
                (cap_col, cap_col, cap_col))

    bm.normal_update()
    # Blend each diamond face's sharp geometric relief normal (58%) with smooth radial trunk normal (42%)
    # so golden sunlight sculpts every single protruding leaf-scar boot while lighting wraps smoothly!
    custom_norms = []
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        rad_dir = face_norm_targets.get(f)
        fn = f.normal.normalized() if f.normal.length > 1e-5 else Vector((1.0, 0.0, 0.0))
        for _ in f.loops:
            if rad_dir is not None:
                n = (fn * 0.58 + rad_dir * 0.42).normalized()
            else:
                n = fn
            custom_norms.append(n)

    suf = '_LOD1' if lod1 else ''
    me = bpy.data.meshes.new(f'{name}_trunk{suf}')
    bm.to_mesh(me)
    bm.free()
    me.normals_split_custom_set(custom_norms)
    me.materials.append(lib.make_material('ph_bark', textured=False))
    obj = bpy.data.objects.new(f'{name}_trunk{suf}', me)
    bpy.context.scene.collection.objects.link(obj)
    return obj, top


def _add_frond(bm, uvl, coll, top, yaw, pitch, length, droop, width, uv_rect, lin_col, segs=5):
    """Gracefully arched V-folded feathery date-palm frond card."""
    d = Vector((math.cos(yaw), math.sin(yaw), 0.0))
    side = Vector((-d.y, d.x, 0.0))
    pts = []
    for i in range(segs + 1):
        t = i / segs
        horiz = length * t * math.cos(pitch)
        vert = length * t * math.sin(pitch) - droop * length * (t ** 1.85)
        pts.append(Vector(top) + d * horiz + Vector((0.0, 0.0, vert)))

    rows = []
    for i, p in enumerate(pts):
        t = i / segs
        tang = (pts[min(i + 1, segs)] - pts[max(i - 1, 0)]).normalized()
        nrm = side.cross(tang).normalized()
        fold = nrm * (width * 0.25 * math.sin(t * math.pi))
        rows.append([
            bm.verts.new(p - side * width - fold * 0.35),
            bm.verts.new(p + fold * 0.55),
            bm.verts.new(p + side * width - fold * 0.35),
        ])

    u0, v0, u1, v1 = uv_rect
    for iy in range(segs):
        tv0, tv1 = iy / segs, (iy + 1) / segs
        vv0 = v0 + (v1 - v0) * tv0
        vv1 = v0 + (v1 - v0) * tv1
        ao0 = 0.74 + 0.26 * (tv0 ** 0.7)
        ao1 = 0.74 + 0.26 * (tv1 ** 0.7)
        c0 = (lin_col[0] * ao0, lin_col[1] * ao0, lin_col[2] * ao0, 1.0)
        c1 = (lin_col[0] * ao1, lin_col[1] * ao1, lin_col[2] * ao1, 1.0)
        for ix in range(2):
            uu0 = u0 + (u1 - u0) * (ix / 2.0)
            uu1 = u0 + (u1 - u0) * ((ix + 1) / 2.0)
            f = bm.faces.new((rows[iy][ix], rows[iy][ix + 1], rows[iy + 1][ix + 1], rows[iy + 1][ix]))
            f.smooth = True
            for lp, uv, c in zip(f.loops, ((uu0, vv0), (uu1, vv0), (uu1, vv1), (uu0, vv1)), (c0, c0, c1, c1)):
                lp[uvl].uv = uv
                lp[coll] = c


def _transfer_spherical_normals(obj, center, blend=0.52):
    me = obj.data
    normals = []
    for p in me.polygons:
        for li in p.loop_indices:
            v = me.vertices[me.loops[li].vertex_index]
            out = v.co - center
            if out.length < 1e-5:
                out = Vector((0.0, 0.0, 1.0))
            else:
                out.normalize()
            n = (v.normal * (1.0 - blend) + out * blend)
            normals.append(n.normalized() if n.length > 1e-5 else Vector((0.0, 0.0, 1.0)))
    me.normals_split_custom_set(normals)


def _build_fronds(name, top, n_fronds, droop, dry_n, seed, lod1=False):
    rnd = random.Random(seed + 100)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    coll = bm.loops.layers.float_color.new('Color')

    nf = max(8, int(n_fronds * 0.52)) if lod1 else n_fronds
    segs = 2 if lod1 else 5
    for i in range(nf):
        young = i >= nf - 3
        lower = i < nf // 3
        yaw = i * 2.39996 + rnd.uniform(-0.14, 0.14)
        pitch = rnd.uniform(0.92, 1.18) if young else (rnd.uniform(0.16, 0.42) if lower else rnd.uniform(0.45, 0.78))
        L = rnd.uniform(2.75, 3.55) * (0.68 if young else (1.06 if lower else 0.96))
        d_cur = (0.22 if young else droop) * rnd.uniform(0.88, 1.14)
        w = rnd.uniform(0.64, 0.78) * (0.78 if young else (1.15 if lod1 else 1.0))
        if young:
            col = _tint_lin(0.98, 1.00, 0.84, rnd, 0.05)
        elif lower:
            col = _tint_lin(0.82, 0.86, 0.76, rnd, 0.05)
        else:
            col = _tint_lin(0.92, 0.96, 0.86, rnd, 0.05)
        _add_frond(bm, uvl, coll, top + Vector((0.0, 0.0, 0.06 if young else -0.04)),
                   yaw, pitch, L, d_cur, w, UV_PALM_FROND, col, segs=segs)

    # Dry golden straw skirt fronds hanging under the green crown
    dn = max(2, dry_n // 2) if lod1 else dry_n
    for i in range(dn):
        yaw = i * (math.tau / dn) + 0.5 + rnd.uniform(-0.22, 0.22)
        col = _tint_lin(0.96, 0.90, 0.78, rnd, 0.06)
        _add_frond(bm, uvl, coll, top + Vector((0.0, 0.0, -0.22)),
                   yaw, rnd.uniform(-1.05, -0.78), rnd.uniform(1.65, 2.15), 0.10, 0.50,
                   UV_PALM_DRY, col, segs=2 if lod1 else 3)

    bm.normal_update()
    suf = '_LOD1' if lod1 else ''
    me = bpy.data.meshes.new(f'{name}_fronds{suf}')
    bm.to_mesh(me)
    bm.free()
    me.materials.append(_simple_vcol_material('foliage_frond'))
    obj = bpy.data.objects.new(f'{name}_fronds{suf}', me)
    bpy.context.scene.collection.objects.link(obj)
    _transfer_spherical_normals(obj, top + Vector((0.0, 0.0, 0.35)), blend=0.52)
    return obj


def _build_dates(name, top, bunches, seed):
    """Hanging Egyptian amber-gold and ruby-red date bunches on vertex-coloured `foliage_solid`."""
    rnd = random.Random(seed + 200)
    bm = bmesh.new()
    coll = bm.loops.layers.float_color.new('Color')

    def add_prim(src, mat4, lin_col):
        src.verts.index_update()
        vm = [bm.verts.new(mat4 @ v.co) for v in src.verts]
        rgba = (lin_col[0], lin_col[1], lin_col[2], 1.0)
        for f in src.faces:
            try:
                nf = bm.faces.new([vm[v.index] for v in f.verts])
                nf.smooth = True
                for lp in nf.loops:
                    lp[coll] = rgba
            except ValueError:
                pass
        src.free()

    for i in range(bunches):
        a = i * math.tau / bunches + rnd.uniform(-0.25, 0.25)
        stalk_p = top + Vector((math.cos(a) * 0.26, math.sin(a) * 0.26, -0.22))
        bunch_p = top + Vector((math.cos(a) * 0.44, math.sin(a) * 0.44, -0.58 - rnd.uniform(0.0, 0.14)))

        st = bmesh.new()
        bmesh.ops.create_cone(st, cap_ends=True, cap_tris=False, segments=5, radius1=0.024, radius2=0.018, depth=0.46)
        add_prim(st, Matrix.LocRotScale(stalk_p, Euler((math.sin(a) * 0.7, -math.cos(a) * 0.7, 0.0)), Vector((1, 1, 1))),
                 lib.jitter_linear('#C89238', rnd, 0.06))

        hex_c = '#BA441C' if i % 2 == 0 else '#D9942E'
        main_col = lib.jitter_linear(hex_c, rnd, 0.07)
        sp = bmesh.new()
        bmesh.ops.create_icosphere(sp, subdivisions=1, radius=1.0)
        for v in sp.verts:
            v.co += noise.noise_vector(v.co * 2.5 + Vector((i * 3.1, seed, 0.0))) * 0.14
        add_prim(sp, Matrix.LocRotScale(bunch_p, Euler((0, 0, a)), Vector((0.18, 0.18, 0.28))), main_col)

        for side in (-1, 1):
            sub_p = bunch_p + Vector((math.cos(a + side * 0.35) * 0.12, math.sin(a + side * 0.35) * 0.12, 0.05))
            sp2 = bmesh.new()
            bmesh.ops.create_icosphere(sp2, subdivisions=1, radius=1.0)
            add_prim(sp2, Matrix.LocRotScale(sub_p, Euler((0, 0, 0)), Vector((0.11, 0.11, 0.16))),
                     (main_col[0] * 0.88, main_col[1] * 0.88, main_col[2] * 0.88))

    bm.normal_update()
    me = bpy.data.meshes.new(f'{name}_dates')
    bm.to_mesh(me)
    bm.free()
    me.materials.append(_simple_vcol_material('foliage_solid'))
    obj = bpy.data.objects.new(f'{name}_dates', me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def build_and_export_palm(name):
    lib.reset_scene()
    h, lean, lean_y, n_fronds, droop, seed, dry_n, bunches = PALM_SPECS[name]

    trunk0, top0 = _build_trunk(name, h, lean, lean_y, seed, lod1=False)
    fronds0 = _build_fronds(name, top0, n_fronds, droop, dry_n, seed, lod1=False)
    dates0 = _build_dates(name, top0, bunches, seed)

    trunk1, top1 = _build_trunk(name, h, lean, lean_y, seed, lod1=True)
    fronds1 = _build_fronds(name, top1, n_fronds, droop, dry_n, seed, lod1=True)

    lod0_objs = [trunk0, fronds0, dates0]
    lod1_objs = [trunk1, fronds1]
    t0 = sum(lib.tri_count(o) for o in lod0_objs)
    t1 = sum(lib.tri_count(o) for o in lod1_objs)
    if t0 > LOD0_BUDGET:
        raise RuntimeError(f'{name}: LOD0 tris {t0} > {LOD0_BUDGET}')
    if t1 > LOD1_BUDGET:
        raise RuntimeError(f'{name}: LOD1 tris {t1} > {LOD1_BUDGET}')

    out_path = lib.OUT_MODELS / f'{name}.glb'
    nbytes = lib.export_textured_glb(out_path, lod0_objs + lod1_objs, embed_images=False)
    print(f'[v4/palms] {name:10s} LOD0={t0:4d}/{LOD0_BUDGET}  LOD1={t1:3d}/{LOD1_BUDGET}  {nbytes/1024:5.1f}KB', flush=True)


def main():
    for name in ('palm_a', 'palm_b', 'palm_c', 'palm_d'):
        build_and_export_palm(name)


if __name__ == '__main__':
    main()
