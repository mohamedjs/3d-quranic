# Stylized (animated-film) pass for Grandpa Salim and the boy, run after dress.py:
#  - friendlier proportions: head scaled up about the neck (body, eyes, brows, headwear together)
#  - sculpted hair made of smooth clumps (farmer's beard + moustache, boy's thick wavy hair)
#  - farmer: brown sleeveless cloak open at the front + beige scarf over the linen tunic
#  - boy: leather backpack with shoulder straps + a wooden walking stick in his right hand
import sys, importlib, math, random
CLOAK = False
sys.path.insert(0, '/var/www/html/old/3d-quranic/blender')
import lib; importlib.reload(lib)
from lib import *
import dress; importlib.reload(dress)
from dress import body_copy, dominant, keep_verts, inflate, skin_to, rigid_to, bounds, BONES, skirt_weights
from mathutils import Vector, Matrix
lib.MAT_COLORS.update({'hair_clumps_white': (0.9, 0.88, 0.84), 'hair_clumps_dark': (0.06, 0.035, 0.02), 'cloth_cloak_brown': (0.3, 0.18, 0.1),
                   'cloth_scarf_beige': (0.78, 0.66, 0.48), 'leather': (0.34, 0.19, 0.09), 'leather_dark': (0.2, 0.11, 0.05), 'wood_stick': (0.42, 0.28, 0.16), 'brass': (0.7, 0.55, 0.25)})

def cleanup(col):
    for o in list(col.objects):
        if o.get('stylized'): bpy.data.objects.remove(o, do_unlink=True)

def clump(bm, root, direction, length, radius, rnd, curl=0.25, side=Vector((1, 0, 0))):
    """One smooth hair clump: a rounded, tapering teardrop that curls slightly at the tip."""
    d = direction.normalized(); ax = d.cross(Vector((0, 0, 1)))
    if ax.length < 1e-3: ax = side.copy()
    ax.normalize(); bx = d.cross(ax).normalized()
    rings, segs = [], 7
    for i in range(8):
        t = i / 7
        c = root + d * length * t + (bx * math.sin(t * math.pi) * curl + ax * math.sin(t * math.pi * 1.5) * curl * 0.4) * length * 0.3
        r = radius * (0.55 + 0.45 * math.sin(math.pi * min(1, t * 1.6 + 0.2))) * (1 - t) ** 0.7 + 0.0008
        rings.append([bm.verts.new(c + (ax * math.cos(a) + bx * math.sin(a) * 0.72) * r) for a in (k / segs * math.tau for k in range(segs))])
    for a, b in zip(rings, rings[1:]):
        for k in range(segs): bm.faces.new((a[k], a[(k + 1) % segs], b[(k + 1) % segs], b[k]))
    tip = bm.verts.new(root + d * length * 1.02)
    for k in range(segs): bm.faces.new((rings[-1][k], rings[-1][(k + 1) % segs], tip))
    bm.faces.new(list(reversed(rings[0])))

def tube(bm, pts, radius, segs=8):
    """Constant-radius tube along a polyline (straps, scarf rolls)."""
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        ax = d.cross(Vector((0, 0, 1))); ax = ax if ax.length > 1e-3 else d.cross(Vector((1, 0, 0))); ax.normalize(); bx = d.cross(ax)
        rings.append([bm.verts.new(p + (ax * math.cos(a) + bx * math.sin(a)) * radius) for a in (k / segs * math.tau for k in range(segs))])
    for a, b in zip(rings, rings[1:]):
        for k in range(segs): bm.faces.new((a[k], a[(k + 1) % segs], b[(k + 1) % segs], b[k]))

def flat_strip(bm, pts, width, thick=0.012):
    """A flat cloth band (scarf ends) along a polyline, facing forward."""
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        side = d.cross(Vector((0, -1, 0))).normalized(); nrm = side.cross(d).normalized()
        w = width * (1 - 0.15 * i / len(pts))
        rings.append([bm.verts.new(p + side * sx * w / 2 + nrm * nz * thick / 2) for sx, nz in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for a, b in zip(rings, rings[1:]):
        for k in range(4): bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
    bm.faces.new(rings[-1])

def tangent(n, flow):
    """Direction along the surface: the flow with its normal component removed."""
    t = flow - n * flow.dot(n)
    return t.normalized() if t.length > 1e-4 else flow.normalized()

def surface_points(o, sel, spacing, rnd):
    """Evenly spread (point, normal) samples from the selected vertices of a mesh."""
    o.data.update(); pts = []
    for i, v in enumerate(o.data.vertices):
        if not sel(o.matrix_world @ v.co): continue
        p = o.matrix_world @ v.co
        if all((p - q).length > spacing for q, _ in pts): pts.append((p, (o.matrix_world.to_3x3() @ v.normal).normalized()))
    rnd.shuffle(pts)
    return pts

def mesh_from(bm, name, material, col):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); col.objects.link(o); me.materials.append(mat(material))
    o['stylized'] = True; o['garment'] = True
    return o

def scale_head(rig, k):
    """Bigger head about the neck. Every mesh on the rig scales by its own head weight, so
    body, eyes, brows, lashes, headwear and hair stay together and the neck blends."""
    pivot = rig.matrix_world @ rig.data.bones['head'].head_local
    for o in rig.children_recursive:
        if o.type != 'MESH' or 'head' not in o.vertex_groups: continue
        if o.data.shape_keys:
            with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o], selected_editable_objects=[o]):
                bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
        gi = o.vertex_groups['head'].index; inv = o.matrix_world.inverted()
        for v in o.data.vertices:
            w = next((g.weight for g in v.groups if g.group == gi), 0)
            if w:
                p = o.matrix_world @ v.co
                v.co = inv @ (pivot + (p - pivot) * (1 + k * w))

def farmer(key='farmer'):
    body = bpy.data.objects[key + '_body']; rig = bpy.data.objects[key + '_rig']; col = body.users_collection[0]
    cleanup(col); x0 = rig.location.x; rig.location.x = 0; bpy.context.view_layer.update()
    BONES.clear(); BONES.update(b.name for b in rig.data.bones)
    ref = body_copy(body, '_ref'); dom = dominant(ref)
    hlo, hhi = bounds(ref, [d == 'head' for d in dom]); hc = (hlo + hhi) / 2; H = hhi.z - hlo.z
    mouth = hlo.z + H * 0.33; rnd = random.Random(11); made = []

    # beard + moustache from smooth clumps
    bm = bmesh.new()
    beard_zone = lambda p: p.y < hc.y - 0.005 and hlo.z - 0.015 < p.z < mouth - 0.005 and abs(p.x - hc.x) < 0.072
    for p, n in surface_points(ref, beard_zone, 0.016, rnd):
        drop = 1 - (p.z - hlo.z) / (mouth - hlo.z)                 # longer toward the chin
        L = 0.016 + 0.022 * max(0, drop) + rnd.uniform(0, 0.006)          # short, trimmed white beard
        clump(bm, p - n * 0.006, tangent(n, Vector((0, -0.25, -1))) + n * 0.1, L, 0.014 + rnd.uniform(0, 0.005), rnd, curl=rnd.uniform(0.15, 0.3))
    for side in (-1, 1):                                            # moustache: two sweeping clumps
        for j in range(4):
            root = Vector((hc.x + side * (0.006 + j * 0.008), hc.y - 0.105 + j * 0.004, mouth + 0.012 - j * 0.003))
            clump(bm, root, Vector((side * 1.0, -0.25, -0.65)), 0.028 - j * 0.003, 0.007, rnd, curl=0.25)
    b = mesh_from(bm, key + '_beard_clumps', 'hair_clumps_white', col); rigid_to(b, rig, 'head'); made.append(b)

    # sleeveless cloak (optional, off for the galabiya look) + long open-front skirt
    if not CLOAK: ck = None
    if CLOAK:
     ck = body_copy(body, key + '_cloak'); d2 = dominant(ck)
     keep_verts(ck, [d.startswith(('spine', 'pelvis', 'clavicle')) for d in d2])
     inflate(ck, lambda co: 0.052)
     sm = ck.modifiers.new('s', 'SMOOTH'); sm.factor = 1.3; sm.iterations = 60; apply_all(ck)
     inflate(ck, lambda co: 0.01)
     bm = bmesh.new(); bm.from_mesh(ck.data)                        # open the front
     bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.calc_center_median().x) < 0.055 and f.calc_center_median().y < -0.02], context='FACES')
     bm.to_mesh(ck.data); bm.free()
     ck.data.materials.clear(); ck.data.materials.append(mat('cloth_cloak_brown')); skin_to(ck, body, rig); made.append(ck)
     hip = max((ref.matrix_world @ v.co).z for i, v in enumerate(ref.data.vertices) if dom[i].startswith('thigh'))
     foot = min((ref.matrix_world @ v.co).z for v in ref.data.vertices)
     pts = [ref.matrix_world @ v.co for i, v in enumerate(ref.data.vertices) if dom[i].startswith(('thigh', 'calf', 'pelvis'))]
     cy = sum(p.y for p in pts) / len(pts)
     bm = bmesh.new(); rings = []
     for i, t in enumerate((0, 0.2, 0.45, 0.7, 1.0)):
         z = hip + 0.1 - (hip + 0.1 - (foot + 0.22)) * t
         band = [p for p in pts if abs(p.z - z) < 0.05] or pts
         rx = max(abs(p.x) for p in band) + 0.07 + 0.05 * t; ry = max(abs(p.y - cy) for p in band) + 0.07 + 0.04 * t
         ring = []
         for k in range(33):                                          # open arc: gap at the front
             a = -math.pi / 2 + 0.32 + k / 32 * (math.tau - 0.64)
             ring.append(bm.verts.new((rx * math.cos(a), cy + ry * math.sin(a), z)))
         rings.append(ring)
     for a_, b_ in zip(rings, rings[1:]):
         for k in range(32): bm.faces.new((a_[k], a_[k + 1], b_[k + 1], b_[k]))
     sk = mesh_from(bm, key + '_cloak_skirt', 'cloth_cloak_brown', col); skirt_weights(sk, rig, hip + 0.1, foot + 0.22); made.append(sk)

    # beige scarf: a soft roll around the neck with two ends hanging down the chest
    neck_z = hlo.z - 0.05; bm = bmesh.new()
    for j, (r_, dz) in enumerate(((0.104, 0.0), (0.112, -0.03))):
        tube(bm, [Vector((hc.x + r_ * math.cos(a), hc.y + 0.02 + r_ * 0.95 * math.sin(a), neck_z + dz - 0.012 * math.sin(a))) for a in (k / 28 * math.tau for k in range(29))], 0.026)
    for side in (-1, 1):
        flat_strip(bm, [Vector((hc.x + side * 0.05, hc.y - 0.1, neck_z - 0.02)) + Vector((side * 0.02 * t, -0.03 * t, -0.11 * t)) for t in range(5)], 0.11)
    sc = mesh_from(bm, key + '_scarf', 'cloth_keffiyeh_check', col); skin_to(sc, body, rig); made.append(sc)

    for o in made: link(o, col); uv_world(o, 0.3); shade_auto(o, 80); o['stylized'] = True; o['garment'] = True
    bpy.data.objects.remove(ref, do_unlink=True)
    scale_head(rig, 0.08)
    rig.location.x = x0

def boy(key='player'):
    body = bpy.data.objects[key + '_body']; rig = bpy.data.objects[key + '_rig']; col = body.users_collection[0]
    cleanup(col); x0 = rig.location.x; rig.location.x = 0; bpy.context.view_layer.update()
    BONES.clear(); BONES.update(b.name for b in rig.data.bones)
    ref = body_copy(body, '_ref'); dom = dominant(ref)
    hlo, hhi = bounds(ref, [d == 'head' for d in dom]); hc = (hlo + hhi) / 2; H = hhi.z - hlo.z
    rnd = random.Random(21); made = []

    # thick wavy hair: dark scalp cap + clumps sweeping back and down, a fringe at the front
    brow = hlo.z + H * 0.66
    scalp = lambda p: p.z > brow + (0.0 if p.y > hc.y - 0.03 else 0.018) or (p.y > hc.y + 0.02 and p.z > hlo.z + H * 0.35)
    cap = body_copy(body, key + '_scalp'); d3 = dominant(cap)
    keep_verts(cap, [d == 'head' and scalp(cap.matrix_world @ v.co) for d, v in zip(d3, cap.data.vertices)])
    inflate(cap, lambda co: 0.012); cap.data.materials.clear(); cap.data.materials.append(mat('hair_clumps_dark'))
    rigid_to(cap, rig, 'head'); made.append(cap)
    bm = bmesh.new()
    for p, n in surface_points(ref, lambda p: scalp(p) and p.z > brow - 0.01, 0.016, rnd):
        front = p.y < hc.y - 0.04
        flow = Vector((0, -0.4, -0.5)) if front else Vector(((p.x - hc.x) * 1.5, 0.7, -0.7))
        L = (0.045 if front else 0.06) + rnd.uniform(0, 0.02)
        clump(bm, p + n * 0.012, tangent(n, flow) + n * 0.12, L, 0.024 + rnd.uniform(0, 0.008), rnd, curl=rnd.uniform(0.45, 0.8))
    hr = mesh_from(bm, key + '_hair_clumps', 'hair_clumps_dark', col); rigid_to(hr, rig, 'head'); made.append(hr)

    # leather backpack: rounded body, flap with brass buckle, two shoulder straps
    back = max((ref.matrix_world @ v.co).y for i, v in enumerate(ref.data.vertices) if dom[i].startswith('spine_02'))
    sh_z = max((ref.matrix_world @ v.co).z for i, v in enumerate(ref.data.vertices) if dom[i].startswith('clavicle'))
    pack = box(key + '_pack', (0.26, 0.13, 0.3), (0, back + 0.07, sh_z - 0.22), 'leather', col, bevel=0.035, segments=3); apply_all(pack)
    flap = box(key + '_flap', (0.27, 0.14, 0.1), (0, back + 0.075, sh_z - 0.1), 'leather_dark', col, bevel=0.03, segments=3); apply_all(flap)
    buckle = box(key + '_buckle', (0.035, 0.012, 0.04), (0, back + 0.15, sh_z - 0.14), 'brass', col, bevel=0.004); apply_all(buckle)
    parts = [pack, flap, buckle]
    for side in (-1, 1):
        bm = bmesh.new()
        path = [Vector((side * 0.07, back + 0.02, sh_z - 0.12)), Vector((side * 0.085, back - 0.03, sh_z + 0.03)), Vector((side * 0.09, back - 0.11, sh_z + 0.035)),
                Vector((side * 0.095, back - 0.17, sh_z - 0.04)), Vector((side * 0.11, back - 0.15, sh_z - 0.2)), Vector((side * 0.13, back - 0.06, sh_z - 0.3))]
        tube(bm, path, 0.014)
        parts.append(mesh_from(bm, f'{key}_strap{side}', 'leather_dark', col))
    for o in parts: o['stylized'] = True; o['garment'] = True
    bp = join(parts, key + '_backpack'); rigid_to(bp, rig, 'spine_03'); made.append(bp)

    # walking stick held upright in the right hand (placed in the posed hand, stored in rest space)
    import anim; importlib.reload(anim)
    anim.reset(rig); anim.arms_down(rig); bpy.context.view_layer.update()
    pb = rig.pose.bones['hand_r']; hand_pose = rig.matrix_world @ pb.matrix; hand_rest = rig.matrix_world @ pb.bone.matrix_local
    grip = hand_pose @ Vector((0, pb.bone.length * 0.55, 0))
    top = grip.z + 0.14; Ls = top - 0.02
    st = cylinder(key + '_stick', 0.015, Ls, (grip.x, grip.y - 0.02, 0.02 + Ls / 2), 'wood_stick', col, verts=8, r2=0.012)
    knob = cylinder(key + '_knob', 0.021, 0.05, (grip.x, grip.y - 0.02, top), 'wood_stick', col, verts=8)
    apply_all(st); stick = join([st, knob], key + '_walkstick')
    stick.data.transform(stick.matrix_world); stick.matrix_world = Matrix()
    stick.data.transform(hand_rest @ hand_pose.inverted())         # posed → rest, so the rig puts it back in the hand
    anim.reset(rig)
    rigid_to(stick, rig, 'hand_r'); made.append(stick)

    for o in made: link(o, col); uv_world(o, 0.3); shade_auto(o, 80); o['stylized'] = True; o['garment'] = True
    bpy.data.objects.remove(ref, do_unlink=True)
    scale_head(rig, 0.16)
    rig.location.x = x0

farmer(); boy()
print('stylized')
