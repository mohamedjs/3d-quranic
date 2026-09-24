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

