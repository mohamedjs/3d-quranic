# Clothing, headwear, beards and skin tint for the MPFB characters built by characters.py.
# Every garment is derived from the body's own surface (so it fits), then skinned by
# copying the body's bone weights (so it moves with the same skeleton).
import sys, importlib, math, random
sys.path.insert(0, '/var/www/html/old/3d-quranic/blender')
import lib; importlib.reload(lib)
from lib import *
import numpy as np
from mathutils import Vector

MAT_COLORS.update({'cloth_thobe_white': (0.86, 0.82, 0.74), 'cloth_robe_brown': (0.34, 0.22, 0.13), 'cloth_robe_indigo': (0.16, 0.2, 0.32),
                   'cloth_hijab': (0.52, 0.36, 0.3), 'cloth_dress_green': (0.2, 0.28, 0.22), 'cloth_turban': (0.9, 0.87, 0.8),
                   'cloth_keffiyeh': (0.9, 0.88, 0.84), 'cloth_agal': (0.03, 0.03, 0.03), 'cloth_tunic': (0.84, 0.78, 0.66),
                   'cloth_trousers': (0.22, 0.28, 0.38), 'cloth_scarf_blue': (0.18, 0.35, 0.55), 'leather': (0.3, 0.18, 0.1),
                   'beard_white': (0.82, 0.8, 0.76), 'beard_dark': (0.07, 0.05, 0.04), 'cloth_bag': (0.35, 0.22, 0.12), 'cloth_linen': (0.88, 0.84, 0.74), 'cloth_tunic_blue': (0.56, 0.64, 0.72),
                   'cloth_galabiya_grey': (0.40, 0.35, 0.30), 'cloth_galabiya_black': (0.035, 0.033, 0.035), 'cloth_tarha_black': (0.022, 0.021, 0.024),
                   'cloth_galabiya_boy': (0.74, 0.66, 0.52), 'cloth_sirwal': (0.86, 0.83, 0.76)})

HEAD = {'head', 'neck_01'}
HANDS = lambda n: n.startswith(('hand_', 'thumb', 'index', 'middle', 'ring', 'pinky'))
FEET = lambda n: n.startswith(('foot_', 'ball_'))
LEGS = lambda n: n.startswith(('thigh_', 'calf_'))

def body_copy(body, name):
    """Evaluated body (shape targets applied, rest pose) as a new mesh keeping vertex groups."""
    dg = bpy.context.evaluated_depsgraph_get()
    arm = [m for m in body.modifiers if m.type == 'ARMATURE']
    for m in body.modifiers: m.show_viewport = m.type != 'ARMATURE'   # keep helpers masked out, rest pose
    dg.update()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    for m in body.modifiers: m.show_viewport = True
    o = bpy.data.objects.new(name, me); o.matrix_world = body.matrix_world.copy()
    for g in body.vertex_groups: o.vertex_groups.new(name=g.name) if g.name not in o.vertex_groups else None
    body.users_collection[0].objects.link(o)
    return o

BONES = set()
def dominant(o):
    """Per vertex: name of the skeleton bone with the largest weight (MPFB also has
    non-bone groups like 'body' or 'Left', which must not count)."""
    names = {g.index: g.name for g in o.vertex_groups if g.name in BONES}
    out = []
    for v in o.data.vertices:
        gs = [g for g in v.groups if g.group in names]
        out.append(names[max(gs, key=lambda g: g.weight).group] if gs else '')
    return out

def keep_verts(o, keep):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in range(len(bm.verts)) if not keep[i]], context='VERTS')
    bm.to_mesh(o.data); bm.free()

def inflate(o, amount_fn):
    o.data.calc_normals_split() if hasattr(o.data, 'calc_normals_split') else None
    bm = bmesh.new(); bm.from_mesh(o.data); bm.normal_update()
    for v in bm.verts: v.co += v.normal * amount_fn(v.co)
    bm.to_mesh(o.data); bm.free()

def skin_to(o, body, rig):
    """Copy bone weights from the body (nearest surface) and bind to the rig."""
    for g in body.vertex_groups:
        if g.name not in o.vertex_groups: o.vertex_groups.new(name=g.name)
    dt = o.modifiers.new('weights', 'DATA_TRANSFER'); dt.object = body
    dt.use_vert_data = True; dt.data_types_verts = {'VGROUP_WEIGHTS'}; dt.vert_mapping = 'POLYINTERP_NEAREST'
    dt.layers_vgroup_select_src = 'ALL'; dt.layers_vgroup_select_dst = 'NAME'
    apply_all(o)
    for g in list(o.vertex_groups):                         # only real bones
        if g.name not in rig.data.bones: o.vertex_groups.remove(g)
    o.parent = rig
    m = o.modifiers.new('rig', 'ARMATURE'); m.object = rig
    return o

def skirt_weights(o, rig, top_z, hem_z):
    """A skirt is one tube over both legs: blend hips → thighs smoothly around it and down
    it, so walking swings the hem instead of tearing the cloth between the legs."""
    gp, gl, gr = (o.vertex_groups.new(name=n) for n in ('pelvis', 'thigh_l', 'thigh_r'))
    for v in o.data.vertices:
        t = min(1, max(0, (top_z - v.co.z) / max(0.01, top_z - hem_z)))
        side = 0.5 + 0.5 * max(-1, min(1, v.co.x / 0.12))          # +X is the character's left
        gp.add([v.index], max(0.05, 1 - 0.75 * t), 'REPLACE')
        gl.add([v.index], 0.75 * t * side, 'REPLACE'); gr.add([v.index], 0.75 * t * (1 - side), 'REPLACE')
    o.parent = rig; m = o.modifiers.new('rig', 'ARMATURE'); m.object = rig

def rigid_to(o, rig, bone):
    o.vertex_groups.clear() if hasattr(o.vertex_groups, 'clear') else None
    g = o.vertex_groups.new(name=bone); g.add(range(len(o.data.vertices)), 1.0, 'REPLACE')
    o.parent = rig; m = o.modifiers.new('rig', 'ARMATURE'); m.object = rig
    return o

def bounds(o, sel):
    pts = [o.matrix_world @ v.co for i, v in enumerate(o.data.vertices) if sel[i]]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi

def lathe_mesh(name, profile, center, material, col, segs=28, squash=1.0):
    bm = bmesh.new(); rings = []
    for r, z in profile:
        rings.append([bm.verts.new((center.x + r * math.cos(a), center.y + r * math.sin(a) * squash, z)) for a in (i / segs * math.tau for i in range(segs))])
    for a, b in zip(rings, rings[1:]):
        for i in range(segs): bm.faces.new((a[i], a[(i + 1) % segs], b[(i + 1) % segs], b[i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); col.objects.link(o); me.materials.append(mat(material))
    return o

def tint_skin(body, rgb):
    """Bake a warm tint into the skin texture so it survives glTF export."""
    for m in body.data.materials:
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image and 'diffuse' in n.image.name.lower() and not n.image.get('tinted'):
                img = n.image; px = np.empty(len(img.pixels), np.float32); img.pixels.foreach_get(px)
                px = px.reshape(-1, 4); px[:, :3] *= np.array(rgb, np.float32); px = np.clip(px, 0, 1)
                img.pixels.foreach_set(px.ravel()); img['tinted'] = True; img.pack()

def outfit(key, style):
    body = bpy.data.objects[key + '_body']; rig = bpy.data.objects[key + '_rig']; col = body.users_collection[0]
    BONES.clear(); BONES.update(b.name for b in rig.data.bones)
    for o in list(col.objects):
        if o.get('garment'): bpy.data.objects.remove(o, do_unlink=True)
    x0 = {'player': -20, 'farmer': -21.2, 'trader': -22.4, 'grandma': -23.6}[key]; rig.location.x = 0   # build at origin, then back to its slot
    bpy.context.view_layer.update()
    tint_skin(body, style['tint'])
    made = []
    base = body_copy(body, key + '_shirt'); dom = dominant(base)
    base_all = body_copy(body, key + '_measure'); dom_all = dominant(base_all)
    head_sel = [d in HEAD for d in dom]
    hlo, hhi = bounds(base, [d == 'head' for d in dom])
    hc = (hlo + hhi) / 2; H = hhi.z - hlo.z
    hip_z = max((base.matrix_world @ v.co).z for i, v in enumerate(base.data.vertices) if dom[i].startswith('thigh'))
    foot_z = min((base.matrix_world @ v.co).z for v in base.data.vertices)

    # ---- upper garment: torso + arms, loose, wide sleeves for robes ----------------------------
    keep = [not (d in HEAD or HANDS(d) or FEET(d) or LEGS(d)) for d in dom]
    keep_verts(base, keep)
    loose = style['loose']
    inflate(base, lambda co: loose + (0.02 if co.z < hip_z + 0.15 else 0))
    # cloth hangs over the torso: strong smoothing there only (arms keep their shape)
    d_now = dominant(base)
    tg = base.vertex_groups.new(name='_torso')
    tg.add([i for i, d in enumerate(d_now) if d.startswith(('spine', 'pelvis'))], 1.0, 'REPLACE')
    sm = base.modifiers.new('drape', 'SMOOTH'); sm.factor = 1.4; sm.iterations = style.get('drape', 90); sm.vertex_group = '_torso'
    sm2 = base.modifiers.new('drape2', 'SMOOTH'); sm2.factor = 0.9; sm2.iterations = 18
    apply_all(base)
    if '_torso' in base.vertex_groups: base.vertex_groups.remove(base.vertex_groups['_torso'])
    inflate(base, lambda co: 0.012)
    base.data.materials.clear(); base.data.materials.append(mat(style['upper']))
    made.append(base)

    # ---- lower garment: a skirt (robe/dress) down to the ankle, or trousers --------------------
    pts = [base_all.matrix_world @ v.co for i, v in enumerate(base_all.data.vertices) if dom_all[i].startswith(('thigh', 'calf', 'pelvis'))]
    cy = sum(p.y for p in pts) / len(pts)
    def skirt(name, top, hem, flare, material, margin=0.03):
        # ellipse fitted to the body at each height (never narrower going down), gentle flare
        levels = [top - (top - hem) * t for t in (0, 0.1, 0.25, 0.45, 0.7, 1.0)]
        rings, prev = [], None
        for i, z in enumerate(levels):
            band = [p for p in pts if abs(p.z - z) < 0.05] or ([] if prev else sorted(pts, key=lambda p: abs(p.z - z))[:200])
            if band: rx = max(abs(p.x) for p in band) + margin; ry = max(abs(p.y - cy) for p in band) + margin
            else: rx, ry = prev
            if prev: rx, ry = max(rx, prev[0]), max(ry, prev[1])
            prev = (rx, ry)
            f = 1 + flare * (i / (len(levels) - 1)) ** 1.6
            rings.append((rx * f, ry * f, z))
        bm = bmesh.new(); vr = [[bm.verts.new((rx * math.cos(a), cy + ry * math.sin(a), z)) for a in (k / 32 * math.tau for k in range(32))] for rx, ry, z in rings]
        for a, b in zip(vr, vr[1:]):
            for k in range(32): bm.faces.new((a[k], a[(k + 1) % 32], b[(k + 1) % 32], b[k]))
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(name, me); col.objects.link(o); me.materials.append(mat(material))
        return o
    if style['skirt']:
        made.append(skirt(key + '_skirt', hip_z + 0.22, foot_z + style['hem'], style['flare'], style['lower'], margin=0.04))
    else:
        tr = body_copy(body, key + '_trousers'); d2 = dominant(tr)
        keep_verts(tr, [LEGS(d) or d == 'pelvis' for d in d2]); inflate(tr, lambda co: 0.018)
        tr.data.materials.clear(); tr.data.materials.append(mat(style['lower'])); made.append(tr)
        if style.get('tunic_to'):                            # tunic falls to the knee over the trousers
            made.append(skirt(key + '_tunic', hip_z + 0.3, foot_z + style['tunic_to'], 0.25, style['upper'], margin=0.045))
    for o in made:
        if o.name.endswith(('_skirt', '_tunic')): skirt_weights(o, rig, hip_z, foot_z)
        else: skin_to(o, body, rig)
    bpy.data.objects.remove(base_all, do_unlink=True)

    # ---- headwear --------------------------------------------------------------------------------
    top = hhi.z; brow = hlo.z + H * 0.7
    hw = style.get('head')
    rigid = []
    if hw == 'turban':
        for i, (z, r, t) in enumerate([(brow + 0.012, 0.115, 0.03), (brow + 0.045, 0.118, 0.03), (brow + 0.078, 0.108, 0.028)]):
            bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=t, major_segments=28, minor_segments=8, location=(hc.x, hc.y + 0.005, z), rotation=(0.08 * (i - 1), 0.05 * i, 0))
            t_ = bpy.context.active_object; t_.scale.y = 1.12; t_.data.materials.append(mat('cloth_turban')); link(t_, col); rigid.append(t_)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(hc.x, hc.y + 0.005, brow + 0.07)); cap = bpy.context.active_object
        cap.scale = (1, 1.12, 0.62); cap.data.materials.append(mat('cloth_turban')); link(cap, col); rigid.append(cap)
    if hw in ('keffiyeh', 'hijab'):
        sh = body_copy(body, key + '_headcloth'); d3 = dominant(sh)
        face_front = lambda co: co.y < hc.y - 0.02 and abs(co.x - hc.x) < 0.075 and (hlo.z + H * 0.12) < co.z < (brow + 0.02)
        sz = max((sh.matrix_world @ v.co).z for i, v in enumerate(sh.data.vertices) if d3[i].startswith('clavicle'))
        keep_verts(sh, [(d in HEAD or (d.startswith(('clavicle', 'spine_03', 'upperarm')) and (sh.matrix_world @ sh.data.vertices[i].co).z > sz - 0.1))
                        and not face_front(sh.matrix_world @ sh.data.vertices[i].co) for i, d in enumerate(d3)])
        inflate(sh, lambda co: style.get('head_puff', 0.022) + (0.018 if co.z < hlo.z + H * 0.1 else 0))
        sh.data.materials.clear(); sh.data.materials.append(mat(style.get('head_mat') or ('cloth_keffiyeh' if hw == 'keffiyeh' else 'cloth_hijab')))
        skin_to(sh, body, rig); made.append(sh)
        if hw == 'keffiyeh':
            for i, z in enumerate((brow + 0.035, brow + 0.06)):
                bpy.ops.mesh.primitive_torus_add(major_radius=0.112, minor_radius=0.011, major_segments=28, minor_segments=6, location=(hc.x, hc.y + 0.005, z))
                a = bpy.context.active_object; a.scale.y = 1.12; a.data.materials.append(mat('cloth_agal')); link(a, col); rigid.append(a)
    if style.get('beard'):
        bd = body_copy(body, key + '_beard'); d4 = dominant(bd)
        chin = lambda co: co.y < hc.y + 0.01 and (hlo.z - 0.01) < co.z < (hlo.z + H * 0.36) and abs(co.x - hc.x) < 0.07
        keep_verts(bd, [d == 'head' and chin(bd.matrix_world @ v.co) for d, v in zip(d4, bd.data.vertices)])
        rnd = random.Random(3)
        inflate(bd, lambda co: 0.006 + style['beard_len'] * max(0, 1 - (co.z - hlo.z) / (H * 0.36)) + rnd.uniform(0, 0.004))
        bd.data.materials.clear(); bd.data.materials.append(mat(style['beard'])); skin_to(bd, body, rig); made.append(bd)
    for o in rigid: rigid_to(o, rig, 'head'); made.append(o)
    if style.get('bag'):
        bg = box(key + '_bag', (0.26, 0.12, 0.3), (hc.x, hc.y + 0.14, hip_z + 0.3), 'cloth_bag', col, bevel=0.03); apply_all(bg)
        rigid_to(bg, rig, 'spine_02'); made.append(bg)

    for o in made:
        o['garment'] = True; link(o, col); uv_world(o, 0.4); shade_auto(o, 60)
    rig.location.x = x0
    return [(o.name, len(o.data.polygons)) for o in made]

STYLES = {
    'farmer':  dict(tint=(0.8, 0.58, 0.42), upper='cloth_galabiya_grey', lower='cloth_galabiya_grey', loose=0.032, skirt=True, hem=0.03, flare=0.2, head='turban'),   # beard, cloak, scarf: stylize.py
    'trader':  dict(tint=(0.9, 0.7, 0.54), upper='cloth_robe_indigo', lower='cloth_robe_indigo', loose=0.028, skirt=True, hem=0.05, flare=0.15, head='keffiyeh', shoulder=0.26, beard='beard_dark', beard_len=0.018),
    'grandma': dict(tint=(0.86, 0.66, 0.52), upper='cloth_galabiya_black', lower='cloth_galabiya_black', loose=0.05, drape=160, skirt=True, hem=0.01, flare=0.26, head='hijab', head_mat='cloth_tarha_black', head_puff=0.03, shoulder=0.24),
    'player':  dict(tint=(0.8, 0.58, 0.42), upper='cloth_galabiya_boy', lower='cloth_sirwal', loose=0.028, skirt=False, tunic_to=0.3),   # hair, backpack, stick: stylize.py
}
if __name__ != 'dress':   # run when executed, not when stylize.py imports the helpers
    print({k: outfit(k, s) for k, s in STYLES.items() if k in (globals().get('KEYS') or STYLES)})
