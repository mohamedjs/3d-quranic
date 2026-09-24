# Keyframed clips for the game_engine rig (+ lid_l / lid_r / mouth bones added by the head
# pass). Poses are world-axis rotations about each bone's head (character faces -Y, Z up),
# so they are independent of bone rolls. Every clip keys the face bones so blends stay clean.
import bpy, math
from mathutils import Matrix, Vector

FPS = 24
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
BODY = ['pelvis', 'spine_01', 'spine_02', 'spine_03', 'neck_01', 'head',
        'clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l', 'clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r',
        'thigh_l', 'calf_l', 'foot_l', 'thigh_r', 'calf_r', 'foot_r']
FINGERS = [f'{f}_{i}_{s}' for s in 'lr' for f in ('index', 'middle', 'ring', 'pinky', 'thumb') for i in ('01', '02', '03')]
FACE = ['lid_l', 'lid_r', 'mouth']

def s(t, k=1, ph=0): return math.sin((t * k + ph) * math.tau)

def reset(rig):
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()

def rot(rig, name, axis, deg):
    pb = rig.pose.bones.get(name)
    if not pb or not deg: return
    M = pb.matrix.copy(); h = M.to_translation()
    pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-h) @ M
    bpy.context.view_layer.update()

def aim(rig, name, direction):
    pb = rig.pose.bones.get(name)
    cur = (pb.tail - pb.head).normalized()
    q = cur.rotation_difference(Vector(direction).normalized())
    axis, ang = q.to_axis_angle()
    rot(rig, name, axis, math.degrees(ang))

def move(rig, name, offset):
    pb = rig.pose.bones[name]
    pb.matrix = Matrix.Translation(Vector(offset)) @ pb.matrix; bpy.context.view_layer.update()

def face(rig, blink=0.0, mouth=0.0):
    """blink 0 open .. 1 closed; mouth 0 closed .. 1 open."""
    for n in ('lid_l', 'lid_r'):
        pb = rig.pose.bones.get(n)
        if pb: pb.scale = (1, max(0.001, blink), 1)
    pb = rig.pose.bones.get('mouth')
    if pb:
        w = 0.001 if mouth <= 0.02 else 0.6 + 0.4 * mouth
        pb.scale = (w, max(0.001, mouth), w)

def blink_at(t, times, dur=0.05):
    b = 0.0
    for tb in times:
        d = abs(t - tb)
        if d < dur: b = max(b, 1 - d / dur)
    return min(1, b * 1.6)

def fingers(rig, curl=12, grip_l=0):
    for side in 'lr':
        g = grip_l if side == 'l' else 0
        hb = rig.pose.bones['hand_' + side]
        ax = (hb.matrix.to_3x3() @ Vector((1, 0, 0))).normalized()     # hand's lateral axis
        sx = 1 if side == 'l' else -1
        for f in ('index', 'middle', 'ring', 'pinky'):
            k = {'index': 0.7, 'middle': 0.9, 'ring': 1.0, 'pinky': 1.15}[f]
            for i in ('01', '02', '03'):
                rot(rig, f'{f}_{i}_{side}', ax, sx * (curl * k + g * (1.0 if i == '01' else 0.9)))

def key_all(rig, frame):
    for n in BODY + FINGERS:
        pb = rig.pose.bones.get(n)
        if pb:
            pb.keyframe_insert('rotation_quaternion', frame=frame)
            if n == 'pelvis': pb.keyframe_insert('location', frame=frame)
    for n in FACE:
        pb = rig.pose.bones.get(n)
        if pb: pb.keyframe_insert('scale', frame=frame)

def make_clip(rig, key, clip, frames, fn):
    name = f'{key}|{clip}'
    act = bpy.data.actions.get(name)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    rig.animation_data_create(); rig.animation_data.action = act
    for f in range(frames + 1):
        t = f / frames
        reset(rig); fn(rig, t); key_all(rig, f + 1)
    act['clip'] = clip
    return act

def push_nla(rig, acts):
    ad = rig.animation_data
    for tr in list(ad.nla_tracks): ad.nla_tracks.remove(tr)
    for a in acts:
        tr = ad.nla_tracks.new(); tr.name = a['clip']
        st = tr.strips.new(a['clip'], 1, a); tr.mute = True
    ad.action = acts[0]

# ---------------------------------------------------------------- poses
class Moves:
    def __init__(self, rig, style):
        self.rig, self.st = rig, style
        b = rig.data.bones
        self.leg = (b['thigh_l'].head_local - b['calf_l'].tail_local).length
    def arms_down(self, out=0.17, fwd=0.05, elbow=14):
        r = self.rig; st = self.st
        for sd, side in (('l', 1), ('r', -1)):
            aim(r, f'upperarm_{sd}', (side * out, -fwd, -1))
            aim(r, f'lowerarm_{sd}', (side * out * 0.5, -fwd - math.sin(math.radians(elbow)), -1))
            lb = r.pose.bones[f'lowerarm_{sd}']
            rot(r, f'lowerarm_{sd}', (lb.tail - lb.head).normalized(), side * self.st.get('twist', 0))
        if st.get('staff'):            # left forearm forward holding the staff
            rot(r, 'upperarm_l', X, -10); rot(r, 'lowerarm_l', X, -48); rot(r, 'lowerarm_l', Y, 8)
        if st.get('hands_behind'):
            pass
    def stoop(self, k=1.0):
        a = self.st.get('stoop', 0) * k
        if a: rot(self.rig, 'spine_02', X, a * 0.5); rot(self.rig, 'spine_03', X, a * 0.5); rot(self.rig, 'neck_01', X, -a * 0.4)

    def idle(self, rig, t):
        st = self.st; e = st.get('energy', 1.0)
        self.arms_down(); self.stoop()
        b = s(t)
        rot(rig, 'spine_02', X, -1.4 * b); rot(rig, 'spine_03', X, -1.0 * b)
        for sd in 'lr': rot(rig, f'clavicle_{sd}', X, 0.8 * b)
        rot(rig, 'pelvis', Y, 1.2 * e * s(t, 1, 0.25)); rot(rig, 'spine_02', Y, -1.0 * e * s(t, 1, 0.25))
        rot(rig, 'head', Z, 4 * e * s(t, 1, 0.1)); rot(rig, 'head', X, 1.5 * s(t, 2)); rot(rig, 'head', Y, 2 * s(t, 1, 0.4))
        for sd in 'lr': rot(rig, f'upperarm_{sd}', X, 1.5 * b)
        fingers(rig, 26, 55 if st.get('staff') else 0)
        face(rig, blink_at(t, (0.3, 0.82)), 0)

    def gait(self, run=False):
        st = self.st
        stride = 0.9 if run else 0.55
        amp = math.degrees(math.asin(min(0.9, stride / (2 * self.leg)))) * (0.9 if run else 1)
        lean = 10 if run else 3
        def pose(rig, t):
            self.arms_down(out=0.13, elbow=40 if run else 14); self.stoop(0.8)
            ph = s(t)
            rot(rig, 'pelvis', Z, (7 if run else 5) * ph); rot(rig, 'spine_02', Z, -(9 if run else 7) * ph)
            rot(rig, 'spine_01', X, lean)
            for side, sign in (('l', 1), ('r', -1)):
                w = sign * ph
                rot(rig, f'thigh_{side}', X, -amp * w - (8 if run else 0))
                sw = max(0, -s(t, 1, 0.08 if sign > 0 else 0.58))
                knee = sw * (95 if run else 55) + (12 if run else 5)
                rot(rig, f'calf_{side}', X, knee)
                rot(rig, f'foot_{side}', X, -10 * w - (8 * sw if run else 0))
                arm = (40 if run else 22) * w * (0.35 if (side == 'l' and st.get('staff')) else 1)
                rot(rig, f'upperarm_{side}', X, arm)
                rot(rig, f'lowerarm_{side}', X, -(8 if run else 6) * max(0, w))
            rot(rig, 'head', X, -lean * 0.4); rot(rig, 'head', Z, 2 * ph)
            bob = (0.5 - 0.5 * s(t, 2, 0.25)) * (0.05 if run else 0.022) * self.leg
            move(rig, 'pelvis', (0, 0, -bob))
            fingers(rig, 18 if run else 12, 55 if st.get('staff') else 0)
            face(rig, blink_at(t, (0.55,)) if not run else 0, 0.25 if run else 0)
        return pose

    def talk(self, rig, t):
        st = self.st; e = st.get('energy', 1.0)
        self.idle_base(rig, t)
        g = max(0, s(t, 2, -0.05)) ** 1.3                 # right hand: two explaining gestures
        rot(rig, 'upperarm_r', X, -38 * g * e); rot(rig, 'upperarm_r', Y, -12 * g)
        rot(rig, 'lowerarm_r', X, -62 * g); rot(rig, 'lowerarm_r', Z, -25 * g); rot(rig, 'hand_r', Y, 25 * g); rot(rig, 'hand_r', X, 15 * g * s(t, 8))
        if not st.get('staff'):
            g2 = max(0, s(t, 1, 0.55)) ** 1.5              # left hand: one open-palm gesture
            rot(rig, 'upperarm_l', X, -25 * g2 * e); rot(rig, 'upperarm_l', Y, 10 * g2)
            rot(rig, 'lowerarm_l', X, -55 * g2); rot(rig, 'lowerarm_l', Z, 20 * g2); rot(rig, 'hand_l', Y, -30 * g2)
        rot(rig, 'spine_03', X, 3 * g); rot(rig, 'spine_02', Z, -4 * g)
        rot(rig, 'head', X, -6 * max(0, s(t, 4)) + 2); rot(rig, 'head', Z, 7 * s(t, 1, 0.3)); rot(rig, 'head', Y, -3 * s(t, 2, 0.2))
        fingers(rig, 10, 55 if st.get('staff') else 0)
        m = abs(s(t, 5)) * 0.6 + abs(s(t, 7, 0.3)) * 0.4
        pause = 1 - max(0, 1 - abs(t - 0.5) / 0.06) - max(0, 1 - abs(t - 0.98) / 0.05) - max(0, 1 - t / 0.03)
        face(rig, blink_at(t, (0.25, 0.7)), max(0, min(1, m * pause * 1.1)))

    def idle_base(self, rig, t):
        self.arms_down(); self.stoop()
        b = s(t); e = self.st.get('energy', 1.0)
        rot(rig, 'spine_02', X, -1.4 * b); rot(rig, 'spine_03', X, -1.0 * b)
        rot(rig, 'pelvis', Y, 1.0 * e * s(t, 1, 0.25))

    # ---- seated (Grandma Zainab on the mastaba)
    def sitting(self, rig, t, talk=False, seat=0.45):
        b = rig.data.bones
        thigh = (b['thigh_l'].tail_local - b['thigh_l'].head_local).length
        calf = (b['calf_l'].tail_local - b['calf_l'].head_local).length
        ankle_rest = b['foot_l'].head_local.z
        hip_target = seat + 0.075
        hip0 = b['thigh_l'].head_local.z
        for side, sx in (('l', 1), ('r', -1)):
            rot(rig, f'thigh_{side}', X, -84); rot(rig, f'thigh_{side}', Y, -5 * sx)
            drop = hip_target - 0.03 - ankle_rest
            ang = math.degrees(math.acos(min(1, drop / calf)))
            rot(rig, f'calf_{side}', X, 84 - ang * 0.6); rot(rig, f'foot_{side}', X, -6)
        move(rig, 'pelvis', (0, 0.05, hip_target - hip0))
        br = s(t)
        rot(rig, 'spine_01', X, 4); rot(rig, 'spine_02', X, 5 + 1.3 * br); rot(rig, 'spine_03', X, 3 + 0.9 * br)
        rot(rig, 'neck_01', X, -4)
        for side, sx in (('l', 1), ('r', -1)):
            aim(rig, f'upperarm_{side}', (sx * 0.2, -0.5, -1))
            aim(rig, f'lowerarm_{side}', (sx * 0.08, -1, -0.3))
            rot(rig, f'hand_{side}', X, 25)
        if talk:
            g = max(0, s(t, 2, -0.05)) ** 1.4
            rot(rig, 'upperarm_r', X, -25 * g); rot(rig, 'lowerarm_r', X, -50 * g); rot(rig, 'lowerarm_r', Z, -20 * g); rot(rig, 'hand_r', Y, 25 * g)
            g2 = max(0, s(t, 1, 0.6)) ** 1.6
            rot(rig, 'lowerarm_l', X, -30 * g2); rot(rig, 'hand_l', Y, -25 * g2)
            rot(rig, 'head', X, -5 * max(0, s(t, 4)) + 1.5); rot(rig, 'head', Z, 7 * s(t, 1, 0.3)); rot(rig, 'head', Y, 3 * s(t, 1, 0.1))
            rot(rig, 'spine_03', X, 2 * g)
            m = abs(s(t, 5)) * 0.6 + abs(s(t, 7, 0.3)) * 0.4
            pause = 1 - max(0, 1 - abs(t - 0.5) / 0.06) - max(0, 1 - abs(t - 0.98) / 0.05) - max(0, 1 - t / 0.03)
            fingers(rig, 14); face(rig, blink_at(t, (0.3, 0.78)), max(0, min(1, m * pause * 1.1)))
        else:
            rot(rig, 'head', Z, 5 * s(t, 1, 0.1)); rot(rig, 'head', X, 2 * s(t, 2)); rot(rig, 'head', Y, 2 * s(t, 1, 0.35))
            fingers(rig, 22); face(rig, blink_at(t, (0.2, 0.6)), 0)

def animate(rig, key, clips, style):
    mv = Moves(rig, style); acts = []
    for c in clips:
        if c == 'idle': acts.append(make_clip(rig, key, 'idle', FPS * 3, mv.idle))
        elif c == 'walk': acts.append(make_clip(rig, key, 'walk', FPS, mv.gait(False)))
        elif c == 'run': acts.append(make_clip(rig, key, 'run', int(FPS * 0.66), mv.gait(True)))
        elif c == 'talk': acts.append(make_clip(rig, key, 'talk', FPS * 4, mv.talk))
        elif c == 'sit': acts.append(make_clip(rig, key, 'sit', FPS * 4, lambda r, t: mv.sitting(r, t, False)))
        elif c == 'sit_talk': acts.append(make_clip(rig, key, 'sit_talk', FPS * 4, lambda r, t: mv.sitting(r, t, True)))
    push_nla(rig, acts)
    return acts
