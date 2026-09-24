# The five cast members: body macros, anime face specs, outfits, clips.
import bpy, bmesh, math
from mathutils import Vector, Matrix
from toon_lib import *
import body as B, head as HD, garments as G, anim as A

CAST = {
    'player': dict(
        height=1.25, outline=0.005,
        macro=dict(gender=1.0, age=B.age(9), muscle=0.5, weight=0.45, height=0.5, proportions=0.7),
        head_k=0.78,
        skin='#C98C62',
        face=dict(skin='#C98C62', eye_z=-0.33, eye_x=0.37, eye_w=0.23, eye_h=0.27, iris_hi='#2E160A', iris_lo='#B06F32',
                  nose_z=-0.72, mouth_z=-0.98, mouth_w=0.1, smile=0.03, brow_col='#2A170E', blush=0.3, cheeks=0.06, chin=0.44),
        clips=['idle', 'walk', 'run', 'talk'], style=dict(energy=1.3, twist=0),
    ),
}

def mats(key, cfg):
    M = {}
    M['skin'] = toon_mat('toon_skin_' + key, cfg['skin'], shadow='#C8958F')
    M['lash'] = toon_mat('toon_lash', '#2B1A10', shadow='#FFFFFF', rim=0)
    M['mouth'] = toon_mat('toon_mouth', '#6A2620', shadow='#FFFFFF', rim=0)
    return M

def fresh_collection(key):
    col = bpy.data.collections.get('char_' + key)
    if col:
        for o in list(col.objects): bpy.data.objects.remove(o, do_unlink=True)
    else:
        col = bpy.data.collections.new('char_' + key); bpy.context.scene.collection.children.link(col)
    for a in list(bpy.data.actions):
        if a.name.startswith(key + '|'): bpy.data.actions.remove(a)
    return col

def add_face_bones(rig, lids, mouth):
    bpy.context.view_layer.objects.active = rig
    for o in bpy.context.selected_objects: o.select_set(False)
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = rig.data.edit_bones
    for n, (a, b) in (('lid_l', lids[0]), ('lid_r', lids[1]), ('mouth', mouth)):
        if n in eb: eb.remove(eb[n])
        e = eb.new(n); e.head = a; e.tail = b; e.roll = 0; e.parent = eb['head']; e.use_deform = True
    bpy.ops.object.mode_set(mode='OBJECT')

def build(key):
    cfg = CAST[key]
    col = fresh_collection(key)
    M = mats(key, cfg); F = dict(cfg['face'])
    h = B.Human(key, cfg['macro'], col, cfg.get('targets'))
    L = (h.head1 - h.head0).length
    R = cfg['head_k'] * L
    C = Vector((0, h.head0.y + 0.08 * R, h.head1.z - 0.92 * R + cfg.get('head_dz', 0) * R))
    img = HD.paint_face(key, F)
    M['face'] = toon_mat('toon_face_' + key, image=img, shadow='#D8A69C', bands=(0.06, 0.3))
    head = HD.build_head(key + '_head', col, C, R, F, M['face'])
    hf = G.HeadFrame(C, R, F, head)
    lids = []; lid_bones = []
    for s in (1, -1):
        o, bb = HD.lid_patch(col, head, C, R, F, s, M['skin'], M['lash']); lids.append(o); lid_bones.append(bb)
    mo, mb = HD.mouth_patch(col, head, C, R, F, M['mouth'])
    add_face_bones(h.rig, lid_bones, mb)
    rigid_to(head, h.rig, 'head')
    rigid_to(lids[0], h.rig, 'lid_l'); rigid_to(lids[1], h.rig, 'lid_r'); rigid_to(mo, h.rig, 'mouth')
    parts = [head, lids[0], lids[1], mo]
    parts += OUTFITS[key](h, hf, M, cfg)
    print('PARTS', key, [(o.name, tri_count(o)) for o in parts], flush=True)
    # ---- scale to the target height
    top = max((o.matrix_world @ v.co).z for o in parts for v in o.data.vertices)
    k = cfg['height'] / top
    rig = h.rig
    for o in bpy.context.selected_objects: o.select_set(False)
    objs = [rig] + parts + [h.ref]
    for o in objs: o.select_set(True)
    rig.scale = (k, k, k)
    bpy.context.view_layer.objects.active = rig
    with bpy.context.temp_override(selected_editable_objects=objs, selected_objects=objs, active_object=rig, object=rig):
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    # ---- clips
    A.animate(rig, key, cfg['clips'], cfg.get('style', {}))
    if 'post' in cfg: parts += cfg['post'](h, M, cfg)
    # ---- join + outline
    for o in parts:
        for mdf in o.modifiers:
            if mdf.type == 'ARMATURE': mdf.object = rig
    mesh = join(parts, key)
    ol = outline_for(mesh, cfg['outline'])
    bpy.data.objects.remove(h.ref, do_unlink=True)
    return dict(key=key, rig=rig, mesh=mesh, outline=ol, tris=tri_count(mesh), tris_outline=tri_count(ol))

def outline_for(mesh, th):
    ol = make_outline(mesh, th)
    skip = {i for i, m in enumerate(ol.data.materials)}
    # drop faces of face-overlay materials from the hull (lids, mouth)
    src = mesh.data.materials
    drop = {i for i, m in enumerate(src) if m and m.name in ('toon_lash', 'toon_mouth') or (m and m.name.startswith('toon_skin_') and False)}
    bm = bmesh.new(); bm.from_mesh(ol.data)
    orig = [p.material_index for p in mesh.data.polygons]
    lid_faces = set()
    # lids share toon_skin with hands: identify them by their vertex groups instead
    dl = bm.verts.layers.deform.active
    gi = {g.name: g.index for g in ol.vertex_groups}
    face_bones = {gi[n] for n in ('lid_l', 'lid_r', 'mouth') if n in gi}
    kill = [f for f in bm.faces if orig[f.index] in drop or (dl and any(any(b in face_bones for b in v[dl].keys()) for v in f.verts))]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(ol.data); bm.free()
    ol.data.materials.clear(); ol.data.materials.append(outline_mat())
    for p in ol.data.polygons: p.material_index = 0
    return ol

# ---------------------------------------------------------------- outfits
def outfit_player(h, hf, M, cfg):
    col = h.col
    M['gal'] = toon_mat('toon_galabiya_cream', '#EFE3C8', shadow='#C9B3A6')
    M['sirwal'] = toon_mat('toon_sirwal', '#D8CDB6', shadow='#B7A79F')
    M['hair'] = toon_mat('toon_hair_dark', '#3A2418', shadow='#9C8AA0', rim=0.3)
    M['shoe'] = toon_mat('toon_leather_brown', '#8A5A30', shadow='#B08E90')
    M['strap'] = toon_mat('toon_leather_dark', '#5E3A1E', shadow='#B08E90')
    b = h.rig.data.bones
    def skin_keep(d, co):
        if d == 'neck_01': return True
        if B.HAND(d): return True
        if d.startswith('lowerarm'):
            bb = b['lowerarm_' + d[-1]]; a, c = bb.head_local, bb.tail_local
            return (co - a).dot(c - a) / (c - a).length_squared > 0.55
        return False
    parts = [h.visible_skin(h.key + '_skin', skin_keep, M['skin'])]
    arm_z = h.rig.data.bones['upperarm_l'].head_local.z - 0.07
    shirt = G.robe_top(h, h.key + '_shirt', M['gal'], loose=0.012, sleeve_end=0.72, sleeve_flare=0.012, drape=40, cut_z=arm_z - 0.1)
    parts.append(shirt)
    parts.append(G.skirt(h, h.key + '_skirt', M['gal'], arm_z, h.knee_z - 0.06, flare=0.14, margin=0.028, folds=0.025, levels=9))
    parts.append(G.trousers(h, h.key + '_sirwal', M['sirwal'], hem_up=0.075))
    parts.append(G.shoes(h, h.key + '_shoes', M['shoe'], height=0.075))
    for o in G.curly_hair(hf, h.key + '_hair', col, M['hair']):
        parts.append(rigid_to(o, h.rig, 'head'))
    parts += G.backpack(h, h.key + '_bag', M['shoe'], M['strap'], shirt)
    return parts

OUTFITS = {'player': outfit_player}
