# Stages the Surat Al-Fil encounter on the Blender timeline, read straight from
# public/data/encounters.json: the boy walks up the village road, then every line of the
# dialogue gets its own shot, talk/idle (sit/sit_talk) clips per speaker, a timeline marker
# and a line in the "AlFil_script" text block. Press Space in the viewport to play it.
import bpy, json, math, sys, importlib
from mathutils import Vector
sys.path.insert(0, '/var/www/html/old/3d-quranic/blender')
import env_scene; importlib.reload(env_scene)
from env_scene import height

FPS = 24
DATA = '/var/www/html/old/3d-quranic/public/data/encounters.json'
B, G, F = Vector((-4.1, -25.05)), Vector((-6.75, -24.7)), Vector((-6.0, -26.2))
HEAD = {'player': 1.12, 'grandma': 1.18, 'farmer': 1.66}
POS = {'player': B, 'grandma': G, 'farmer': F}
START = Vector((-0.6, -36.0))                                          # the boy comes up the road from the south

def lines():
    enc = next(e for e in json.load(open(DATA))['encounters'] if e['id'] == 'people-of-the-elephant')
    host = enc.get('host', 'grandma'); out = []
    for s in enc['steps']:
        sp = s.get('speaker') or host
        if s['type'] == 'say': out.append((sp, s['ar'], s.get('en', '')))
        elif s['type'] in ('choice', 'question'):
            if sp != 'player': out.append((sp, s['ar'], s.get('en', '')))
            o = s['options'][0]
            out.append(('player', o['ar'], o.get('en', '')))
            rep = o.get('reply') or []
            for r in (rep if isinstance(rep, list) else [rep]): out.append((r.get('speaker') or host, r['ar'], r.get('en', '')))
        elif s['type'] == 'verses': out.append(('verses', 'سورة الفيل ١–٥ — بصوت الشيخ', 'Surat Al-Fil 105:1-5, recited'))
    return out

def dur(text, sp):
    return 14 * FPS if sp == 'verses' else int(max(2.6, min(9.0, len(text) * 0.07)) * FPS)

def nla(rig, segs):
    """segs: [(start, end, action_name)] → alternating NLA tracks with short crossfades."""
    ad = rig.animation_data_create(); ad.action = None
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    tr = [ad.nla_tracks.new(), ad.nla_tracks.new()]; tr[0].name, tr[1].name = 'story_A', 'story_B'
    for i, (a, b, name) in enumerate(segs):
        act = bpy.data.actions[name]; L = act.frame_range[1] - act.frame_range[0]
        st = tr[i % 2].strips.new(f'{name}_{i}', int(a), act)
        st.repeat = max(0.05, (b - a + 6) / L); st.blend_in = 0 if i == 0 else 6
        st.extrapolation = 'NOTHING' if i < len(segs) - 1 else 'HOLD_FORWARD'
        if i == 0: st.extrapolation = 'HOLD' if len(segs) == 1 else 'HOLD'

def key_cam(cam, f, eye, target, lens=35):
    cam.location = eye; cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f); cam.data.keyframe_insert('lens', frame=f)

def v3(p, z): return Vector((p.x, p.y, height(p.x, p.y) + z))

def shot(sp, k):
    """(eye, target, lens) for a line spoken by sp; k alternates the side a little."""
    if sp in ('grandma', 'farmer'):
        d = (B - POS[sp]).normalized(); side = Vector((-d.y, d.x)) * (0.75 if k % 2 else 0.62)
        return v3(B + d * 1.45 + side, 1.38), v3(POS[sp], HEAD[sp] - 0.12), 42
    if sp == 'player':
        mid = (G + F) / 2; d = (mid - B).normalized()
        return v3(B + d * 1.9 + Vector((-d.y, d.x)) * 0.5, 1.2), v3(B, HEAD['player'] - 0.05), 45
    return v3(B + Vector((2.6, -1.2)), 1.3), v3((G + F + B) / 3, 1.0), 28          # group / verses

def build():
    sc = bpy.context.scene; sc.render.fps = FPS
    prefs = bpy.context.preferences.edit; old_interp = prefs.keyframe_new_interpolation_type; prefs.keyframe_new_interpolation_type = 'LINEAR'
    rigs = {k: bpy.data.objects[k + '_rig'] for k in ('player', 'grandma', 'farmer')}
    cam = bpy.data.objects.get('StoryCam') or bpy.data.objects.new('StoryCam', bpy.data.cameras.new('StoryCam'))
    if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
    cam.animation_data_clear(); cam.data.animation_data_clear(); cam.data.sensor_width = 36; sc.camera = cam
    sc.timeline_markers.clear()
    boy = rigs['player']; boy.animation_data_clear()

    # 1) establishing shot over the fields and the canal (0–6 s)
    f = 1
    key_cam(cam, f, (28, -64, 16), (-6, -28, 1), 24); key_cam(cam, f + 6 * FPS - 1, (14, -48, 7), (-6, -27, 1.2), 28)
    sc.timeline_markers.new('Establishing: village, fields, canal', frame=f)
    # 2) the boy walks up the road to grandma's mastaba (tracking shot)
    f0 = f + 6 * FPS; path = [START, Vector((-0.8, -30.5)), Vector((-2.4, -26.8)), B]
    seg = [(a - b).length for a, b in zip(path[1:], path)]; walk_f = int(sum(seg) / 1.05 * FPS)
    t = 0; boy.rotation_mode = 'XYZ'
    for i in range(len(path)):
        fr = f0 + int(sum(seg[:i]) / sum(seg) * walk_f); p = path[i]
        d = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized() if i < len(path) - 1 else ((G + F) / 2 - B).normalized()
        boy.location = v3(p, -0.04); boy.rotation_euler = (0, 0, math.atan2(d.y, d.x) + math.pi / 2)
        boy.keyframe_insert('location', frame=fr); boy.keyframe_insert('rotation_euler', frame=fr)
    for fc in boy.animation_data.action.fcurves if hasattr(boy.animation_data.action, 'fcurves') else []:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    sc.timeline_markers.new('The boy walks to Grandma Zainab\'s house', frame=f0)
    for i in range(0, walk_f + 1, 12):                                       # camera trucks along beside him
        s_ = i / walk_f; acc = s_ * sum(seg); j = 0
        while j < len(seg) - 1 and acc > seg[j]: acc -= seg[j]; j += 1
        p = path[j].lerp(path[j + 1], min(1, acc / seg[j]))
        key_cam(cam, f0 + i, v3(p + Vector((3.2, -3.4)), 1.5), v3(p + Vector((-0.8, 1.2)), 0.9), 32)
    # 3) the dialogue
    f = f0 + walk_f + 12; boy_segs = [(f0 - 1, f0 + walk_f, 'player_rig_walk')]
    segs = {k: [] for k in rigs}; script = ['Surat Al-Fil — story timeline (frame @24fps · speaker · Arabic · English)\n']
    k = 0
    for sp, ar, en in lines():
        n = dur(ar, sp)
        eye, tgt, lens = shot(sp, k); k += 1
        key_cam(cam, f, eye, tgt, lens)
        drift = (Vector(tgt) - Vector(eye)).normalized() * 0.12
        if sp == 'verses':                                   # crane up over the palms to the open sky
            key_cam(cam, f + n - 1, Vector(eye) + Vector((1.5, -1.0, 6.5)), Vector(tgt) + Vector((-6, 2, 9)), 24)
        else:
            key_cam(cam, f + n - 1, Vector(eye) + drift, tgt, lens)
        for who in rigs:
            talking = who == sp
            if who == 'grandma': name = 'grandma_rig_sit_talk' if talking else 'grandma_rig_sit'
            else: name = f'{who}_rig_{"talk" if talking else "idle"}'
            segs[who].append((f, f + n, name))
        sc.timeline_markers.new(f'{sp}: {en[:70]}', frame=f)
        script.append(f'[{f:5d}] {sp:8s} | {ar}\n        {"":8s} | {en}\n')
        f += n
    # the verses: crane up from the group toward the sky above the palms
    last = f
    segs['player'] = boy_segs + [(boy_segs[0][1], segs['player'][0][0], 'player_rig_idle')] + segs['player']
    for who, sg in segs.items(): nla(rigs[who], sg)
    for fc in (cam.animation_data.action.fcurves if hasattr(cam.animation_data.action, 'fcurves') else []):
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    sc.frame_start, sc.frame_end = 1, last + FPS
    txt = bpy.data.texts.get('AlFil_script') or bpy.data.texts.new('AlFil_script'); txt.clear(); txt.write(''.join(script))
    prefs.keyframe_new_interpolation_type = old_interp
    sc.frame_set(1)
    return last, len(script) - 1

if __name__ != 'story_timeline':
    print(build())
