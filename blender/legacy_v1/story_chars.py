# Surat Al-Fil cast pass (run after characters.py → dress.py → stylize.py → anim.py):
#  - keffiyeh check pattern on the farmer's shoulder scarf
#  - grandma: sit + sit_talk clips (sitting on a 0.45 m mastaba, origin under the pelvis)
import sys, importlib, math
sys.path.insert(0, '/var/www/html/old/3d-quranic/blender')
import bpy, numpy as np
import anim; importlib.reload(anim)
from anim import rot, aim, reset, make_action, s, X, Y, Z, FPS
from mathutils import Vector, Matrix

SEAT = 0.45

def keffiyeh_texture():
    m = bpy.data.materials.get('cloth_keffiyeh_check')
    if not m: return
    n = 256; img = bpy.data.images.get('keffiyeh_check') or bpy.data.images.new('keffiyeh_check', n, n)
    y, x = np.mgrid[0:n, 0:n]
    cell = 8
    u, v = (x % cell) / cell, (y % cell) / cell
    grid = ((np.abs(u - 0.5) < 0.09) | (np.abs(v - 0.5) < 0.09))           # woven lines
    dots = (np.abs(u - 0.5) + np.abs(v - 0.5) < 0.17) & ((x // cell + y // cell) % 2 == 0)
    border = (y % 128) < 10                                               # a dark band every half repeat
    dark = grid | dots | border
    base = np.array([0.86, 0.84, 0.8]); ink = np.array([0.08, 0.08, 0.1])
    rgb = np.where(dark[..., None], ink, base) * (0.94 + 0.06 * np.random.default_rng(1).random((n, n, 1)))
    px = np.concatenate([rgb, np.ones((n, n, 1))], -1).astype(np.float32)
    img.pixels.foreach_set(px.ravel()); img.pack()
    nt = m.node_tree; b = nt.nodes.get('Principled BSDF')
    tex = nt.nodes.get('kef') or nt.nodes.new('ShaderNodeTexImage'); tex.name = 'kef'; tex.image = img
    nt.links.new(tex.outputs['Color'], b.inputs['Base Color'])
    m.diffuse_color = (0.8, 0.78, 0.74, 1)

def sitting(rig, t, talk=False):
    """Seated on a bench: hips at SEAT, thighs forward, shins down, hands resting on the knees."""
    pb = rig.pose.bones['pelvis']
    hip = (rig.matrix_world @ rig.pose.bones['thigh_l'].head).z
    for side, sx in (('l', 1), ('r', -1)):
        rot(rig, f'thigh_{side}', X, -86); rot(rig, f'thigh_{side}', Y, -4 * sx)   # knees slightly apart
        rot(rig, f'calf_{side}', X, 84); rot(rig, f'foot_{side}', X, -4)
    drop = hip - (SEAT + 0.085)
    pb.matrix = Matrix.Translation((0, 0.04, -drop)) @ pb.matrix; bpy.context.view_layer.update()
    b = s(t)                                                    # slow breathing, a tired old back
    rot(rig, 'spine_01', X, -8); rot(rig, 'spine_02', X, -5 - 1.2 * b); rot(rig, 'spine_03', X, -3 - 0.8 * b)
    rot(rig, 'neck_01', X, 6)
    for side, sx in (('l', 1), ('r', -1)):
        aim(rig, f'upperarm_{side}', (sx * 0.18, -0.55, -1))
        aim(rig, f'lowerarm_{side}', (sx * 0.05, -1, -0.35))
    if talk:
        g = max(0, s(t, 2)) ** 1.5                              # right hand lifts from the knee as she explains
        rot(rig, 'upperarm_r', X, -22 * g); rot(rig, 'lowerarm_r', X, -45 * g); rot(rig, 'hand_r', Z, 18 * g)
        rot(rig, 'head', X, -5 * s(t, 3)); rot(rig, 'head', Z, 6 * s(t, 1, 0.3))
    else:
        rot(rig, 'head', Z, 4 * s(t, 1, 0.1)); rot(rig, 'head', X, 1.5 * s(t, 2))

def add_sit(key='grandma'):
    rig = bpy.data.objects[key + '_rig']; x0 = rig.location.x; rig.location.x = 0; bpy.context.view_layer.update()
    acts = [make_action(rig, 'sit', FPS * 4, lambda r, t: sitting(r, t)),
            make_action(rig, 'sit_talk', FPS * 4, lambda r, t: sitting(r, t, True))]
    rig.animation_data.action = acts[0]; rig.location.x = x0
    return [a.name for a in acts]

def seated_skirt(key='grandma'):
    """Galabiya skirt for a seated woman: the convex hull of the seated legs + hips (how a
    long dress drapes from the lap over the knees to the ankles), remeshed smooth, then
    stored in rest space and bound rigidly to the pelvis (the seated clips keep the legs still)."""
    import dress; importlib.reload(dress)
    from dress import body_copy, dominant, rigid_to, BONES
    from lib import mat, apply_all, link, uv_world, shade_auto
    import bmesh
    body = bpy.data.objects[key + '_body']; rig = bpy.data.objects[key + '_rig']; col = body.users_collection[0]
    for n in (key + '_skirt', key + '_seated_skirt'):
        if n in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    x0 = rig.location.x; rig.location.x = 0
    BONES.clear(); BONES.update(b.name for b in rig.data.bones)
    rig.animation_data.action = bpy.data.actions[key + '_rig_sit']; bpy.context.scene.frame_set(1); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    tmp = bpy.data.objects.new('_seat_ref', me); col.objects.link(tmp); tmp.matrix_world = body.matrix_world.copy()
    for g in body.vertex_groups: tmp.vertex_groups.new(name=g.name)
    dom = dominant(tmp)
    pts = [tmp.matrix_world @ v.co for i, v in enumerate(me.vertices) if dom[i].startswith(('thigh', 'calf', 'pelvis'))]
    bpy.data.objects.remove(tmp, do_unlink=True)
    ankle = min(p.z for p in pts)
    bm = bmesh.new()
    for p in pts: bm.verts.new(p)
    for p in [p for p in pts if p.z < ankle + 0.06]: bm.verts.new((p.x * 1.15, p.y - 0.03, ankle - 0.03))   # hem falls to the ankle
    bmesh.ops.convex_hull(bm, input=bm.verts)
    me2 = bpy.data.meshes.new(key + '_seated_skirt'); bm.to_mesh(me2); bm.free()
    o = bpy.data.objects.new(key + '_seated_skirt', me2); col.objects.link(o)
    rm = o.modifiers.new('r', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.022
    sm = o.modifiers.new('s', 'SMOOTH'); sm.factor = 1.0; sm.iterations = 6
    apply_all(o)
    import dress as D
    D.inflate(o, lambda co: 0.025)
    dec = o.modifiers.new('d', 'DECIMATE'); dec.ratio = 0.5; apply_all(o)
    # posed → rest for the pelvis, so the rig puts it back in the lap
    pb = rig.pose.bones['pelvis']
    o.data.transform((rig.matrix_world @ pb.bone.matrix_local) @ (rig.matrix_world @ pb.matrix).inverted())
    o.data.materials.append(mat('cloth_galabiya_black'))
    rigid_to(o, rig, 'pelvis'); o['garment'] = True; uv_world(o, 0.4); shade_auto(o, 70)
    rig.location.x = x0
    return len(o.data.polygons)

def bodice(key='grandma'):
    """Loose dress top: convex hull of the chest/belly/back in the rest pose (a galabiya hangs
    straight from the bust, it does not follow the figure), skinned like the body."""
    import dress; importlib.reload(dress)
    from dress import body_copy, dominant, skin_to, keep_verts, inflate, BONES
    from lib import mat, apply_all, uv_world, shade_auto
    import bmesh
    body = bpy.data.objects[key + '_body']; rig = bpy.data.objects[key + '_rig']; col = body.users_collection[0]
    if key + '_bodice' in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[key + '_bodice'], do_unlink=True)
    x0 = rig.location.x; rig.location.x = 0
    rig.animation_data.action = None; reset(rig); bpy.context.view_layer.update()
    BONES.clear(); BONES.update(b.name for b in rig.data.bones)
    ref = body_copy(body, '_bod_ref'); dom = dominant(ref)
    hipz = (rig.matrix_world @ rig.data.bones['thigh_l'].head_local).z
    neckz = (rig.matrix_world @ rig.data.bones['neck_01'].head_local).z
    pts = [ref.matrix_world @ v.co for i, v in enumerate(ref.data.vertices)
           if dom[i].startswith(('spine', 'pelvis', 'clavicle')) and hipz - 0.02 < (ref.matrix_world @ v.co).z < neckz - 0.03]
    bpy.data.objects.remove(ref, do_unlink=True)
    bm = bmesh.new()
    for p in pts: bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > 0.9 or f.normal.z < -0.9], context='FACES')   # open top/bottom
    me = bpy.data.meshes.new(key + '_bodice'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(key + '_bodice', me); col.objects.link(o)
    sd = o.modifiers.new('sd', 'SUBSURF'); sd.levels = 2; apply_all(o)
    inflate(o, lambda co: 0.018)
    dec = o.modifiers.new('d', 'DECIMATE'); dec.ratio = 0.35; apply_all(o)
    o.data.materials.append(mat('cloth_galabiya_black'))
    skin_to(o, body, rig); o['garment'] = True; uv_world(o, 0.4); shade_auto(o, 70)
    rig.location.x = x0; rig.animation_data.action = bpy.data.actions[key + '_rig_sit']
    return len(o.data.polygons)

if __name__ != 'story_chars':
    keffiyeh_texture()
    print(add_sit())
    print('seated skirt faces', seated_skirt())
    print('bodice faces', bodice())
