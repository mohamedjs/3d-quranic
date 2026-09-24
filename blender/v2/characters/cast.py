# The five cast members: body macros, anime face specs, outfits, clips.
import bpy, bmesh, math
from mathutils import Vector, Matrix
from toon_lib import *
import body as B, head as HD, garments as G, anim as A

CAST = {
    'player': dict(
        height=1.25, outline=0.005,
        macro=dict(gender=1.0, age=B.age(9), muscle=0.5, weight=0.45, height=0.5, proportions=0.7),
        head_k=0.82,
        skin='#C98C62',
        face=dict(skin='#C98C62', eye_z=-0.33, eye_x=0.37, eye_w=0.23, eye_h=0.27, iris_hi='#2E160A', iris_lo='#B06F32',
                  nose_z=-0.72, mouth_z=-0.98, mouth_w=0.1, smile=0.03, brow_col='#2A170E', blush=0.3, cheeks=0.06, chin=0.44),
        clips=['idle', 'walk', 'run', 'talk'], style=dict(energy=1.3, twist=0),
    ),
    'farmer': dict(
        height=1.74, outline=0.006,
        macro=dict(gender=1.0, age=B.age(68), muscle=0.45, weight=0.5, height=0.55, proportions=0.55),
        head_k=0.8, skin='#B97D55',
        face=dict(skin='#B97D55', eye_z=-0.36, eye_x=0.35, eye_w=0.2, eye_h=0.16, lid_top=0.62, lid_bot=0.7, lid_lift=-0.12,
                  iris_hi='#24120A', iris_lo='#7A4A25', iris_rx=0.52, nose_z=-0.7, mouth_z=-0.98, mouth_w=0.11, smile=0.035,
                  brow_col='#F2EDE4', brow_w=0.034, brow_gap=0.1, brow_tilt=0.07, age_lines=True, blush=0.14, chin=0.46, lash_w=0.019),
        clips=['idle', 'walk', 'talk'], style=dict(energy=0.8, stoop=8, staff=True, robe=True),
    ),
    'grandma_zainab': dict(
        height=1.58, outline=0.006,
        macro=dict(gender=0.0, age=B.age(70), muscle=0.35, weight=0.62, height=0.4, proportions=0.5, cupsize=0.3, firmness=0.3),
        head_k=0.84, skin='#C99470',
        face=dict(ears=False, skin='#C99470', eye_z=-0.36, eye_x=0.35, eye_w=0.2, eye_h=0.19, lid_top=0.7, lid_lift=-0.08, lashes=True,
                  iris_hi='#2A150C', iris_lo='#8B5530', nose_z=-0.72, mouth_z=-0.98, mouth_w=0.1, smile=0.045,
                  brow_col='#9A8E86', brow_w=0.02, brow_tilt=0.04, age_lines=True, blush=0.3, cheeks=0.08, chin=0.42),
        clips=['sit', 'sit_talk'], style=dict(energy=0.8),
    ),
    'grandma': dict(
        height=1.60, outline=0.006,
        macro=dict(gender=0.0, age=B.age(64), muscle=0.4, weight=0.55, height=0.45, proportions=0.55, cupsize=0.3, firmness=0.3),
        head_k=0.84, skin='#D2A27C',
        face=dict(ears=False, skin='#D2A27C', eye_z=-0.36, eye_x=0.35, eye_w=0.2, eye_h=0.2, lid_top=0.72, lid_lift=-0.04, lashes=True,
                  iris_hi='#2E1A0C', iris_lo='#A0703A', nose_z=-0.72, mouth_z=-0.98, mouth_w=0.1, smile=0.04,
                  brow_col='#6B5548', brow_w=0.02, age_lines=True, blush=0.28, cheeks=0.05, chin=0.44),
        clips=['idle', 'walk', 'talk'], style=dict(energy=0.9, stoop=4, robe=True),
    ),
    'trader': dict(
        height=1.78, outline=0.006,
        macro=dict(gender=1.0, age=B.age(45), muscle=0.6, weight=0.55, height=0.6, proportions=0.6),
        head_k=0.8, skin='#C08A60',
        face=dict(ears=False, skin='#C08A60', eye_z=-0.36, eye_x=0.35, eye_w=0.2, eye_h=0.16, lid_top=0.72, lid_bot=0.72, lid_lift=0.06,
                  iris_hi='#1A0E08', iris_lo='#6A4020', iris_rx=0.52, nose_z=-0.7, mouth_z=-0.98, mouth_w=0.11, smile=0.03,
                  brow_col='#1E120C', brow_w=0.032, brow_gap=0.09, brow_tilt=-0.05, blush=0.12, chin=0.5, lash_w=0.02),
        clips=['idle', 'walk', 'talk'], style=dict(energy=1.0, robe=True),
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
    C = Vector((0, h.head0.y + 0.08 * R, h.head0.z + (0.95 + F.get('chin', 0.48)) * R + cfg.get('head_dz', -0.35) * R))
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
    if key in POST: parts += POST[key](h, M, cfg)
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
    drop = {i for i, m in enumerate(src) if m and m.name in ('toon_lash', 'toon_mouth', 'toon_glasses_gold') or (m and m.name.startswith('toon_skin_') and False)}
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
    shirt = G.robe_top(h, h.key + '_shirt', M['gal'], loose=0.012, sleeve_end=0.72, sleeve_flare=0.012, drape=40, cut_z=arm_z - 0.1, collar=-0.012)
    parts.append(shirt)
    parts.append(G.skirt(h, h.key + '_skirt', M['gal'], arm_z, h.knee_z - 0.06, flare=0.14, margin=0.028, folds=0.025, levels=9))
    parts.append(G.trousers(h, h.key + '_sirwal', M['sirwal'], hem_up=0.075))
    parts.append(G.shoes(h, h.key + '_shoes', M['shoe'], height=0.075))
    for o in G.curly_hair(hf, h.key + '_hair', col, M['hair']):
        parts.append(rigid_to(o, h.rig, 'head'))
    parts += G.backpack(h, h.key + '_bag', M['shoe'], M['strap'], shirt)
    return parts


def skin_keep_fn(h, fore=0.6, neck=True):
    b = h.rig.data.bones
    def f(d, co):
        if d == 'neck_01': return neck
        if B.HAND(d): return True
        if d.startswith('lowerarm'):
            bb = b['lowerarm_' + d[-1]]; a, c = bb.head_local, bb.tail_local
            return (co - a).dot(c - a) / (c - a).length_squared > fore
        return False
    return f

def robe(h, M, mat, hem=0.03, flare=0.2, sleeve_end=0.8, flare_sleeve=0.04, folds=0.035, skirt_on=True):
    arm_z = h.rig.data.bones['upperarm_l'].head_local.z - 0.07
    top = G.robe_top(h, h.key + '_robe', mat, loose=0.016, sleeve_end=sleeve_end, sleeve_flare=flare_sleeve, drape=130,
                     cut_z=(arm_z - 0.1) if skirt_on else None, collar=-0.01)
    out = [top]
    if skirt_on:
        out.append(G.skirt(h, h.key + '_skirt', mat, arm_z, h.foot_z + hem, flare=flare, margin=0.03, folds=folds, levels=10))
    return out, top

def outfit_farmer(h, hf, M, cfg):
    col = h.col
    M['robe'] = toon_mat('toon_galabiya_brown', '#7A4E2D', shadow='#A88C98')
    M['turban'] = toon_mat('toon_turban_white', '#F3EEE3', shadow='#C9C3D6')
    M['beard'] = toon_mat('toon_beard_white', '#F2EEE8', shadow='#D6D0DE', rim=0.25)
    M['shoe'] = toon_mat('toon_leather_dark', '#4A2E1A', shadow='#B08E90')
    M['scarf'] = toon_mat('toon_keffiyeh_brown', image=check_image('keffiyeh_brown', '#EDE3CF', '#6B4228', cell=32), shadow='#B9A6A8')
    parts = [h.visible_skin(h.key + '_skin', skin_keep_fn(h, 0.62), M['skin'])]
    r, top = robe(h, M, M['robe'], hem=0.035, flare=0.22, flare_sleeve=0.05)
    parts += r
    parts.append(G.shoes(h, h.key + '_shoes', M['shoe'], height=0.06))
    sc = G.scarf_collar(h, h.key + '_scarf', M['scarf']); uv_box(sc, 0.09); parts.append(sc)
    for o in G.turban(hf, h.key + '_turban', col, M['turban'], band_front=0.34): parts.append(rigid_to(o, h.rig, 'head'))
    for o in G.beard(hf, h.key + '_beard', col, M['beard'], thick=0.13, chin_len=0.36, side_up=-0.12): parts.append(rigid_to(o, h.rig, 'head'))
    return parts

def post_farmer(h, M, cfg):
    M['wood'] = toon_mat('toon_wood_staff', '#8A5F3A', shadow='#B08E90')
    act = next(a for a in bpy.data.actions if a.name == h.key + '|idle')
    return [G.staff(h, h.key + '_staff', M['wood'], act)]

def outfit_grandma_zainab(h, hf, M, cfg):
    col = h.col
    M['robe'] = toon_mat('toon_galabiya_black', '#2F2B35', shadow='#8E86A6', rim=0.3)
    M['tarha'] = toon_mat('toon_tarha_black', '#25222B', shadow='#8E86A6', rim=0.3)
    M['shoe'] = toon_mat('toon_slipper_black', '#1F1B1E', shadow='#B08E90')
    parts = [h.visible_skin(h.key + '_skin', skin_keep_fn(h, 0.7, neck=False), M['skin'])]
    top = G.robe_top(h, h.key + '_robe', M['robe'], loose=0.022, sleeve_end=0.84, sleeve_flare=0.03, drape=90, collar=-0.01)
    parts.append(top)
    parts.append(G.shoes(h, h.key + '_shoes', M['shoe'], height=0.05))
    parts.append(rigid_to(G.hood(hf, h.key + '_tarha', col, M['tarha'], face_rx=0.8, face_top=0.42, face_bot=-1.62, thick=0.1), h.rig, 'head'))
    parts.append(G.cape(h, hf, h.key + '_tarha_cape', M['tarha'], drop_front=0.1, drop_back=0.18))
    return parts

def post_grandma_zainab(h, M, cfg):
    act = next(a for a in bpy.data.actions if a.name == h.key + '|sit')
    return [G.seated_skirt(h, h.key + '_skirt', M['robe'], act)]

def outfit_grandma(h, hf, M, cfg):
    col = h.col
    M['robe'] = toon_mat('toon_dress_green', '#2F6B55', shadow='#8E9AB0')
    M['tarha'] = toon_mat('toon_tarha_indigo', '#3E4A8C', shadow='#9A94BE', rim=0.25)
    M['shoe'] = toon_mat('toon_slipper_brown', '#5A3A24', shadow='#B08E90')
    M['gold'] = toon_mat('toon_glasses_gold', '#B8862E', shadow='#C9A0A0')
    parts = [h.visible_skin(h.key + '_skin', skin_keep_fn(h, 0.72, neck=False), M['skin'])]
    r, top = robe(h, M, M['robe'], hem=0.02, flare=0.28, sleeve_end=0.84, flare_sleeve=0.03, folds=0.04)
    parts += r
    parts.append(G.shoes(h, h.key + '_shoes', M['shoe'], height=0.05))
    parts.append(rigid_to(G.hood(hf, h.key + '_tarha', col, M['tarha'], face_rx=0.8, face_top=0.45, face_bot=-1.62, thick=0.1), h.rig, 'head'))
    parts.append(G.cape(h, hf, h.key + '_tarha_cape', M['tarha'], drop_front=0.12, drop_back=0.2))
    parts.append(rigid_to(G.glasses(hf, h.key + '_glasses', col, M['gold']), h.rig, 'head'))
    return parts

def outfit_trader(h, hf, M, cfg):
    col = h.col
    M['robe'] = toon_mat('toon_robe_indigo', '#2E3C74', shadow='#9A94BE')
    M['kef'] = toon_mat('toon_keffiyeh_red', image=check_image('keffiyeh_red', '#F1ECE4', '#B2342C', cell=32), shadow='#C4AEB8')
    M['agal'] = toon_mat('toon_agal_black', '#1A1618', shadow='#FFFFFF', rim=0.35)
    M['beard'] = toon_mat('toon_beard_dark', '#2A1C16', shadow='#9C8AA0', rim=0.25)
    M['shoe'] = toon_mat('toon_leather_brown', '#8A5A30', shadow='#B08E90')
    M['belt'] = toon_mat('toon_sash_gold', '#C99A3E', shadow='#C9A0A0')
    parts = [h.visible_skin(h.key + '_skin', skin_keep_fn(h, 0.62), M['skin'])]
    r, top = robe(h, M, M['robe'], hem=0.04, flare=0.16, flare_sleeve=0.04)
    parts += r
    parts.append(G.shoes(h, h.key + '_shoes', M['shoe'], height=0.06))
    kh = G.hood(hf, h.key + '_keffiyeh', col, M['kef'], face_rx=0.74, face_top=0.5, face_bot=-1.6, thick=0.09, open_bottom=True)
    uv_box(kh, 0.13); parts.append(rigid_to(kh, h.rig, 'head'))
    kc = G.cape(h, hf, h.key + '_keffiyeh_tails', M['kef'], drop_front=0.2, drop_back=0.25, open_front=0.75, spread=0.02)
    uv_box(kc, 0.13); parts.append(kc)
    parts.append(rigid_to(G.agal(hf, h.key + '_agal', col, M['agal'], z=0.52), h.rig, 'head'))
    for o in G.beard(hf, h.key + '_beard', col, M['beard'], thick=0.04, chin_len=0.07, side_up=-0.28): parts.append(rigid_to(o, h.rig, 'head'))
    return parts

OUTFITS = {'player': outfit_player, 'farmer': outfit_farmer, 'grandma_zainab': outfit_grandma_zainab, 'grandma': outfit_grandma, 'trader': outfit_trader}
POST = {'farmer': post_farmer, 'grandma_zainab': post_grandma_zainab}
