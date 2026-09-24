# Keyframed animations for the MPFB game_engine rig: idle, walk, run, talk.
# Poses are expressed as world-space rotations about each bone's head (character faces -Y,
# +Z up), converted to bone-local keys, so they work regardless of the rig's bone rolls.
import sys, importlib, math
sys.path.insert(0, '/var/www/html/old/3d-quranic/blender')
import bpy
from mathutils import Matrix, Vector, Quaternion

FPS = 24
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
ORDER = ['pelvis', 'spine_01', 'spine_02', 'spine_03', 'neck_01', 'head',
         'clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l', 'clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r',
         'thigh_l', 'calf_l', 'foot_l', 'thigh_r', 'calf_r', 'foot_r']

def reset(rig):
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    bpy.context.view_layer.update()

def rot(rig, name, axis, deg):
    """Rotate a bone about a world axis through its head (armature space == world here)."""
    pb = rig.pose.bones.get(name)
    if not pb or not deg: return
    M = pb.matrix.copy(); h = M.to_translation()
    pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-h) @ M
    bpy.context.view_layer.update()

def aim(rig, name, direction):
    """Rotate a bone so it points along `direction` (world)."""
    pb = rig.pose.bones.get(name)
    cur = (pb.tail - pb.head).normalized()
    q = cur.rotation_difference(Vector(direction).normalized())
    axis, ang = q.to_axis_angle()
    rot(rig, name, axis, math.degrees(ang))

def arms_down(rig, out=0.16, fwd=0.04, elbow=12):
    for s, side in (('l', 1), ('r', -1)):
        aim(rig, f'upperarm_{s}', (side * out, -fwd, -1))
        rot(rig, f'lowerarm_{s}', X, -elbow)                  # slight natural bend, hands forward

def key_all(rig, frame):
    for n in ORDER:
        pb = rig.pose.bones.get(n)
        if pb:
            pb.keyframe_insert('rotation_quaternion', frame=frame)
            if n == 'pelvis': pb.keyframe_insert('location', frame=frame)

def make_action(rig, name, frames, pose_fn):
    act = bpy.data.actions.get(f'{rig.name}_{name}')
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(f'{rig.name}_{name}'); act.use_fake_user = True
    rig.animation_data_create(); rig.animation_data.action = act
    for f in range(frames + 1):
        t = f / frames                                      # 0..1 over the loop
        reset(rig); pose_fn(rig, t); key_all(rig, f + 1)
    act['gltf_name'] = name
    return act

def s(t, k=1, ph=0): return math.sin((t * k + ph) * math.tau)

def idle(rig, t):
    arms_down(rig)
    b = s(t)                                                 # one breath per loop
    rot(rig, 'spine_02', X, -1.2 * b); rot(rig, 'spine_03', X, -0.8 * b)
    rot(rig, 'pelvis', Y, 1.0 * s(t, 1, 0.25))              # slow weight shift
    rot(rig, 'head', Z, 3 * s(t, 1, 0.1)); rot(rig, 'head', X, 1.5 * s(t, 2))
    for sd in 'lr': rot(rig, f'upperarm_{sd}', X, 1.5 * b)

def gait(amp, lean):
    def pose(rig, t):
        arms_down(rig, out=0.12)
        ph = s(t)
        pb = rig.pose.bones['pelvis']; pb.location = (0, 0, 0)
        rot(rig, 'pelvis', Z, 6 * amp * ph); rot(rig, 'spine_02', Z, -8 * amp * ph)
        rot(rig, 'spine_01', X, -lean)
        for side, sign in (('l', 1), ('r', -1)):
            w = sign * ph                                     # +1 = this leg forward
            rot(rig, f'thigh_{side}', X, -28 * amp * w)
            knee = max(0, -s(t, 1, 0.1 if sign > 0 else 0.6)) * 45 * amp + 6
            rot(rig, f'calf_{side}', X, knee)
            rot(rig, f'foot_{side}', X, -12 * amp * w)
            rot(rig, f'upperarm_{side}', X, 22 * amp * w)     # arms swing opposite the legs
            rot(rig, f'lowerarm_{side}', X, -10 * amp - 8 * amp * max(0, -w))
        rot(rig, 'head', X, lean * 0.5)
        pb.location = (0, 0, 0)
        bob = abs(s(t, 1)) * 0.025 * amp
        rig.pose.bones['pelvis'].matrix = Matrix.Translation((0, 0, -bob)) @ rig.pose.bones['pelvis'].matrix
        bpy.context.view_layer.update()
    return pose

def talk(rig, t):
    idle(rig, t)
    g = max(0, s(t, 2)) ** 1.5                                # two gestures per loop
    rot(rig, 'upperarm_r', X, -35 * g); rot(rig, 'upperarm_r', Y, 10 * g)
    rot(rig, 'lowerarm_r', X, -55 * g); rot(rig, 'hand_r', Z, 20 * g)
    rot(rig, 'head', X, -4 * s(t, 3)); rot(rig, 'head', Z, 5 * s(t, 1, 0.3))

def animate(key):
    rig = bpy.data.objects[key + '_rig']
    x0 = rig.location.x; rig.location.x = 0; bpy.context.view_layer.update()
    acts = [make_action(rig, 'idle', FPS * 3, idle), make_action(rig, 'walk', FPS, gait(1.0, 4)),
            make_action(rig, 'run', int(FPS * 0.66), gait(1.6, 12)), make_action(rig, 'talk', FPS * 4, talk)]
    rig.animation_data.action = acts[0]
    rig.location.x = x0
    return [a.name for a in acts]

if __name__ != 'anim':
    print({k: animate(k) for k in (globals().get('KEYS') or ('player', 'farmer', 'trader', 'grandma'))})
