"""Seamless 24 fps NLA animation clips (idle, walk, run, talk, sit, sit_talk) for the 22-bone rig."""
import math
import bpy
from mathutils import Matrix, Vector

FPS = 24
X = Vector((1.0, 0.0, 0.0))
Y = Vector((0.0, 1.0, 0.0))
Z = Vector((0.0, 0.0, 1.0))

BODY_BONES = [
    'pelvis', 'spine_01', 'spine_02', 'neck', 'head',
    'clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l',
    'clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r',
    'thigh_l', 'calf_l', 'foot_l',
    'thigh_r', 'calf_r', 'foot_r',
]
FACE_BONES = ['lid_l', 'lid_r', 'mouth']


def _sin(t, k=1.0, phase=0.0):
    return math.sin((t * k + phase) * math.tau)


def _reset_pose(rig):
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()


def _rot(rig, name, axis, deg):
    pb = rig.pose.bones.get(name)
    if not pb or abs(deg) < 1e-4:
        return
    m = pb.matrix.copy()
    h = m.to_translation()
    pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-h) @ m
    bpy.context.view_layer.update()


def _aim(rig, name, direction):
    pb = rig.pose.bones.get(name)
    if not pb:
        return
    cur = (pb.tail - pb.head).normalized()
    tgt = Vector(direction).normalized()
    q = cur.rotation_difference(tgt)
    axis, ang = q.to_axis_angle()
    if abs(ang) > 1e-4:
        _rot(rig, name, axis, math.degrees(ang))


def _move(rig, name, offset):
    pb = rig.pose.bones.get(name)
    if not pb:
        return
    pb.matrix = Matrix.Translation(Vector(offset)) @ pb.matrix
    bpy.context.view_layer.update()


def _face(rig, blink=0.0, mouth=0.0):
    """Drive lid_l/lid_r (0 open .. 1 closed) and mouth (0 closed .. 1 open)."""
    for n in ('lid_l', 'lid_r'):
        pb = rig.pose.bones.get(n)
        if pb:
            if blink <= 0.02:
                pb.scale = (0.001, 0.001, 0.001)
            else:
                pb.scale = (1.0, min(1.0, blink), 1.0)
    pb = rig.pose.bones.get('mouth')
    if pb:
        if mouth <= 0.02:
            pb.scale = (0.001, 0.001, 0.001)
        else:
            w = 0.68 + 0.34 * mouth
            pb.scale = (w, max(0.05, mouth), w)


def _blink_at(t, times, dur=0.045):
    b = 0.0
    for tb in times:
        d = min(abs(t - tb), abs(t - tb + 1.0), abs(t - tb - 1.0))
        if d < dur:
            b = max(b, 1.0 - d / dur)
    return min(1.0, b * 1.55)


def _key_frame(rig, frame):
    for n in BODY_BONES:
        pb = rig.pose.bones.get(n)
        if pb:
            pb.keyframe_insert('rotation_quaternion', frame=frame)
            if n == 'pelvis':
                pb.keyframe_insert('location', frame=frame)
    for n in FACE_BONES:
        pb = rig.pose.bones.get(n)
        if pb:
            pb.keyframe_insert('scale', frame=frame)


def _make_clip(rig, key, clip_name, frames, pose_fn):
    act_name = f'{key}|{clip_name}'
    old = bpy.data.actions.get(act_name)
    if old:
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(act_name)
    act.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = act

    for f in range(frames + 1):
        t = f / frames
        _reset_pose(rig)
        pose_fn(rig, t)
        _key_frame(rig, f + 1)

    act['clip'] = clip_name
    return act


def _push_nla(rig, acts):
    ad = rig.animation_data
    for tr in list(ad.nla_tracks):
        ad.nla_tracks.remove(tr)
    for act in acts:
        tr = ad.nla_tracks.new()
        tr.name = act['clip']
        tr.strips.new(act['clip'], 1, act)
        tr.mute = True
    ad.action = acts[0] if acts else None


class Animator:
    """Procedural storybook character acting tailored per character style."""

    def __init__(self, rig, style):
        self.rig = rig
        self.st = style
        b = rig.data.bones
        self.leg_len = (b['thigh_l'].head_local - b['calf_l'].tail_local).length
        self.thigh_len = (b['thigh_l'].tail_local - b['thigh_l'].head_local).length
        self.calf_len = (b['calf_l'].tail_local - b['calf_l'].head_local).length
        self.hip_z = b['thigh_l'].head_local.z
        self.ankle_z = b['foot_l'].head_local.z

    def _arms_relaxed(self, out=0.22, fwd=0.08, elbow=16.0):
        r = self.rig
        for sd, s in (('l', 1.0), ('r', -1.0)):
            _aim(r, f'upperarm_{sd}', (s * out, -fwd, -1.0))
            _aim(r, f'lowerarm_{sd}', (s * out * 0.52, -fwd - math.sin(math.radians(elbow)), -1.0))
            _rot(r, f'hand_{sd}', Z, -s * 8.0)
        if self.st.get('staff'):
            # Grandpa Salim holds his shepherd's staff comfortably forward-left
            _aim(r, 'upperarm_l', (0.28, -0.24, -1.0))
            _aim(r, 'lowerarm_l', (0.14, -0.78, -0.58))
            _rot(r, 'hand_l', X, 16.0)

    def _stoop(self, k=1.0):
        deg = self.st.get('stoop', 0.0) * k
        if deg:
            _rot(self.rig, 'spine_01', X, deg * 0.45)
            _rot(self.rig, 'spine_02', X, deg * 0.55)
            _rot(self.rig, 'neck', X, -deg * 0.42)
            _rot(self.rig, 'head', X, -deg * 0.25)

    def idle(self, rig, t):
        e = self.st.get('energy', 1.0)
        self._arms_relaxed(out=self.st.get('arm_out', 0.22), elbow=self.st.get('elbow', 15.0))
        self._stoop()

        br = _sin(t, 1.0)
        _rot(rig, 'spine_01', X, -1.2 * br)
        _rot(rig, 'spine_02', X, -1.6 * br)
        for sd in ('l', 'r'):
            _rot(rig, f'clavicle_{sd}', X, 0.9 * br)
            _rot(rig, f'upperarm_{sd}', X, 1.8 * br)

        sway = _sin(t, 1.0, 0.25)
        _rot(rig, 'pelvis', Y, 1.3 * e * sway)
        _rot(rig, 'spine_01', Y, -1.1 * e * sway)
        _rot(rig, 'head', Z, 4.5 * e * _sin(t, 1.0, 0.12))
        _rot(rig, 'head', X, 1.6 * _sin(t, 2.0))
        _rot(rig, 'head', Y, 2.2 * e * _sin(t, 1.0, 0.38))

        _face(rig, _blink_at(t, (0.28, 0.78)), 0.0)

    def gait(self, run=False):
        st = self.st
        # Walk: 24 frames (1.0s) covering ~1.1 m -> half-stride 0.55 m
        # Run:  16 frames (0.667s) covering ~1.8 m -> 2.7 m/s at 1x -> half-stride 0.90 m
        stride = 0.86 if run else 0.55
        robe = st.get('robe', False)
        raw_amp = math.degrees(math.asin(min(0.86, stride / max(0.3, 2.0 * self.leg_len))))
        amp = raw_amp * (0.88 if run else (0.76 if robe else 0.92))
        lean = 12.0 if run else 3.5

        def pose(rig, t):
            self._arms_relaxed(out=0.20 if run else 0.22, elbow=52.0 if run else 18.0)
            self._stoop(0.75)
            ph = _sin(t, 1.0)

            _rot(rig, 'pelvis', Z, (7.5 if run else 5.0) * ph)
            _rot(rig, 'spine_01', Z, -(5.5 if run else 3.8) * ph)
            _rot(rig, 'spine_02', Z, -(5.0 if run else 3.5) * ph)
            _rot(rig, 'spine_01', X, lean)

            for sd, sign in (('l', 1.0), ('r', -1.0)):
                w = sign * ph
                # Thigh swings forward (-X) and back (+X)
                _rot(rig, f'thigh_{sd}', X, -amp * w - (9.0 if run else 1.5))
                # Swing-phase knee bend (smooth positive X bend)
                sw = max(0.0, -_sin(t, 1.0, 0.08 if sign > 0 else 0.58))
                knee_max = 82.0 if run else (34.0 if robe else 48.0)
                _rot(rig, f'calf_{sd}', X, sw * knee_max + (10.0 if run else 4.0))
                _rot(rig, f'foot_{sd}', X, -8.0 * w - (8.0 * sw if run else 2.0 * sw))

                # Counter-swinging arms (keep staff arm steady & purposeful!)
                arm_k = 0.30 if (sd == 'l' and st.get('staff')) else 1.0
                arm_amp = (42.0 if run else 22.0) * arm_k
                _rot(rig, f'upperarm_{sd}', X, arm_amp * w)
                _rot(rig, f'lowerarm_{sd}', X, -(14.0 if run else 8.0) * max(0.0, w) * arm_k)

            _rot(rig, 'head', X, -lean * 0.55)
            _rot(rig, 'head', Z, 2.2 * ph)

            # Grounded vertical bounce (lowest on heel contact, gently lifting on passing)
            bob = (0.5 - 0.5 * _sin(t, 2.0, 0.25)) * (0.048 if run else 0.020) * self.leg_len
            _move(rig, 'pelvis', (0.0, 0.0, -bob))
            _face(rig, _blink_at(t, (0.52,)) if not run else 0.0, 0.22 if run else 0.0)

        return pose

    def talk(self, rig, t):
        e = self.st.get('energy', 1.0)
        self._arms_relaxed(out=self.st.get('arm_out', 0.22), elbow=16.0)
        self._stoop()

        br = _sin(t, 1.0)
        _rot(rig, 'spine_01', X, -1.2 * br)
        _rot(rig, 'spine_02', X, -1.4 * br)
        _rot(rig, 'pelvis', Y, 1.1 * e * _sin(t, 1.0, 0.25))

        # Expressive storybook explaining gestures (right hand leads)
        g1 = max(0.0, _sin(t, 2.0, -0.04)) ** 1.35
        _rot(rig, 'upperarm_r', X, -36.0 * g1 * e)
        _rot(rig, 'upperarm_r', Y, -10.0 * g1)
        _rot(rig, 'lowerarm_r', X, -58.0 * g1)
        _rot(rig, 'lowerarm_r', Z, -22.0 * g1)
        _rot(rig, 'hand_r', Y, 24.0 * g1)
        _rot(rig, 'hand_r', X, 12.0 * g1 * _sin(t, 6.0))

        # Left hand joins warmly unless holding a staff
        if not self.st.get('staff'):
            g2 = max(0.0, _sin(t, 1.0, 0.54)) ** 1.45
            _rot(rig, 'upperarm_l', X, -26.0 * g2 * e)
            _rot(rig, 'upperarm_l', Y, 10.0 * g2)
            _rot(rig, 'lowerarm_l', X, -52.0 * g2)
            _rot(rig, 'lowerarm_l', Z, 18.0 * g2)
            _rot(rig, 'hand_l', Y, -24.0 * g2)

        _rot(rig, 'spine_02', X, 2.8 * g1)
        _rot(rig, 'spine_01', Z, -3.5 * g1)
        _rot(rig, 'head', X, -5.5 * max(0.0, _sin(t, 4.0)) + 2.0)
        _rot(rig, 'head', Z, 6.5 * _sin(t, 1.0, 0.28))
        _rot(rig, 'head', Y, -3.0 * _sin(t, 2.0, 0.18))

        # Natural conversational speech rhythm with brief pauses
        m = abs(_sin(t, 5.0)) * 0.62 + abs(_sin(t, 7.0, 0.30)) * 0.38
        pause = (
            1.0
            - max(0.0, 1.0 - abs(t - 0.50) / 0.065)
            - max(0.0, 1.0 - abs(t - 0.97) / 0.05)
            - max(0.0, 1.0 - t / 0.03)
        )
        _face(rig, _blink_at(t, (0.24, 0.72)), max(0.0, min(1.0, m * pause * 1.10)))

    def sitting(self, rig, t, talk=False, seat=0.45):
        """Grounded mastaba-bench seated pose at seat=0.45 m, feet on z=0, zero dress/arm clip."""
        hip_target = seat + 0.088
        drop_hip = hip_target - self.hip_z

        # Thighs rest horizontally on the 0.45m bench; calves drop smoothly so slippers kiss z=0
        for sd, s in (('l', 1.0), ('r', -1.0)):
            _rot(rig, f'thigh_{sd}', X, -86.0)
            _rot(rig, f'thigh_{sd}', Y, -4.5 * s)
            vert_drop = max(0.15, hip_target - 0.025 - self.ankle_z)
            # Small forward knee tuck so feet sit squarely on floor
            calf_ang = math.degrees(math.acos(min(1.0, vert_drop / max(0.15, self.calf_len))))
            _rot(rig, f'calf_{sd}', X, 86.0 - calf_ang * 0.45)
            _rot(rig, f'foot_{sd}', X, -2.0)

        _move(rig, 'pelvis', (0.0, 0.04, drop_hip))

        br = _sin(t, 1.0)
        _rot(rig, 'spine_01', X, 3.0 + 1.0 * br)
        _rot(rig, 'spine_02', X, 3.5 + 1.2 * br)
        _rot(rig, 'neck', X, -3.0)

        # Warm relaxed arms held clearly OUTSIDE dress bodice, hands resting warmly above lap
        for sd, s in (('l', 1.0), ('r', -1.0)):
            _aim(rig, f'upperarm_{sd}', (s * 0.26, -0.44, -1.0))
            _aim(rig, f'lowerarm_{sd}', (-s * 0.14, -1.00, -0.24))
            _rot(rig, f'hand_{sd}', X, 16.0)

        if talk:
            g1 = max(0.0, _sin(t, 2.0, -0.05)) ** 1.35
            _rot(rig, 'upperarm_r', X, -24.0 * g1)
            _rot(rig, 'lowerarm_r', X, -48.0 * g1)
            _rot(rig, 'lowerarm_r', Z, -18.0 * g1)
            _rot(rig, 'hand_r', Y, 24.0 * g1)

            g2 = max(0.0, _sin(t, 1.0, 0.58)) ** 1.55
            _rot(rig, 'upperarm_l', X, -14.0 * g2)
            _rot(rig, 'lowerarm_l', X, -32.0 * g2)
            _rot(rig, 'hand_l', Y, -20.0 * g2)

            _rot(rig, 'spine_02', X, 2.0 * g1)
            _rot(rig, 'head', X, -5.0 * max(0.0, _sin(t, 4.0)) + 1.5)
            _rot(rig, 'head', Z, 6.5 * _sin(t, 1.0, 0.28))
            _rot(rig, 'head', Y, 2.8 * _sin(t, 1.0, 0.12))

            m = abs(_sin(t, 5.0)) * 0.62 + abs(_sin(t, 7.0, 0.30)) * 0.38
            pause = (
                1.0
                - max(0.0, 1.0 - abs(t - 0.50) / 0.065)
                - max(0.0, 1.0 - abs(t - 0.97) / 0.05)
                - max(0.0, 1.0 - t / 0.03)
            )
            _face(rig, _blink_at(t, (0.28, 0.76)), max(0.0, min(1.0, m * pause * 1.10)))
        else:
            _rot(rig, 'head', Z, 4.8 * _sin(t, 1.0, 0.10))
            _rot(rig, 'head', X, 2.0 * _sin(t, 2.0))
            _rot(rig, 'head', Y, 2.2 * _sin(t, 1.0, 0.36))
            _face(rig, _blink_at(t, (0.22, 0.68)), 0.0)


def animate(rig, key, clips, style):
    """Create all requested clips as NLA tracks with exact contract names."""
    mv = Animator(rig, style)
    acts = []
    for clip in clips:
        if clip == 'idle':
            acts.append(_make_clip(rig, key, 'idle', FPS * 3, mv.idle))
        elif clip == 'walk':
            acts.append(_make_clip(rig, key, 'walk', FPS, mv.gait(False)))
        elif clip == 'run':
            acts.append(_make_clip(rig, key, 'run', int(FPS * 0.67), mv.gait(True)))
        elif clip == 'talk':
            acts.append(_make_clip(rig, key, 'talk', FPS * 4, mv.talk))
        elif clip == 'sit':
            acts.append(_make_clip(rig, key, 'sit', FPS * 3, lambda r, t: mv.sitting(r, t, False)))
        elif clip == 'sit_talk':
            acts.append(_make_clip(rig, key, 'sit_talk', FPS * 4, lambda r, t: mv.sitting(r, t, True)))
    _push_nla(rig, acts)
    return acts
