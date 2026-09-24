# MPFB body + game_engine skeleton. The body itself is mostly hidden: only the parts that
# show (neck, hands, forearm ends, feet) are kept; everything else is a weight reference
# that garments copy their skinning from.
import bpy, bmesh, math
from mathutils import Vector
from toon_lib import *
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService

TARGETS = '/home/mohamed/.config/blender/5.2/extensions/user_default/mpfb/data/targets/'

def age(years):   # MakeHuman age: 0 -> 1 yr, 0.1875 -> 11, 0.5 -> 25, 1 -> 90
    return years / 11 * 0.1875 if years <= 11 else (0.1875 + (years - 11) / 14 * 0.3125 if years <= 25 else 0.5 + (years - 25) / 65 * 0.5)

HAND = lambda n: n.startswith(('hand_', 'thumb', 'index', 'middle', 'ring', 'pinky'))
FOOT = lambda n: n.startswith(('foot_', 'ball_'))

class Human:
    """rig, ref (full evaluated body with weights), bones set, landmarks."""
    def __init__(self, key, macro, col, targets=None):
        m = TargetService.get_default_macro_info_dict()
        m.update({k: v for k, v in macro.items() if k in m})
        body = HumanService.create_human(mask_helpers=True, detailed_helpers=True, extra_vertex_groups=True,
                                         feet_on_ground=True, scale=0.1, macro_detail_dict=m)
        for t, w in (targets or {}).items():
            TargetService.load_target(body, TARGETS + t + '.target.gz', weight=w)
        rig = HumanService.add_builtin_rig(body, 'game_engine', import_weights=True)
        rig.name = key + '_rig'; rig.data.name = key + '_rig'
        for c in list(rig.users_collection): c.objects.unlink(rig)
        col.objects.link(rig)
        self.key, self.col, self.rig = key, col, rig
        self.bones = set(b.name for b in rig.data.bones)
        # evaluated copy (targets applied, helpers masked away, rest pose)
        for mo in body.modifiers: mo.show_viewport = mo.type != 'ARMATURE'
        dg = bpy.context.evaluated_depsgraph_get(); dg.update()
        me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        ref = new_obj(key + '_ref', me, col); ref.matrix_world = body.matrix_world.copy()
        for g in body.vertex_groups: ref.vertex_groups.new(name=g.name)
        for g in list(ref.vertex_groups):
            if g.name not in self.bones: ref.vertex_groups.remove(g)
        me.materials.clear()
        for o in [body] + [c for c in body.children]:
            if o != rig: bpy.data.objects.remove(o, do_unlink=True)
        self.ref = ref
        self.dom = self.dominant(ref)
        b = rig.data.bones
        self.bone = lambda n: (b[n].head_local.copy(), b[n].tail_local.copy())
        pts = [v.co for v in ref.data.vertices]
        self.foot_z = min(p.z for p in pts)
        self.hip_z = b['thigh_l'].head_local.z
        self.knee_z = b['calf_l'].head_local.z
        self.neck = b['neck_01'].head_local.copy()
        self.head0, self.head1 = b['head'].head_local.copy(), b['head'].tail_local.copy()
        self.shoulder_x = b['upperarm_l'].head_local.x

    def dominant(self, o):
        names = {g.index: g.name for g in o.vertex_groups if g.name in self.bones}
        out = []
        for v in o.data.vertices:
            gs = [g for g in v.groups if g.group in names and g.weight > 0]
            out.append(names[max(gs, key=lambda g: g.weight).group] if gs else '')
        return out

    def copy_ref(self, name, keep=None):
        me = self.ref.data.copy(); o = new_obj(name, me, self.col); o.matrix_world = self.ref.matrix_world.copy()
        for g in self.ref.vertex_groups: o.vertex_groups.new(name=g.name)
        if keep is not None:
            d = self.dom; keep_verts(o, [keep(d[i], v.co) for i, v in enumerate(me.vertices)])
        return o

    def skin(self, o, clean=True):
        """Copy bone weights from the reference body (nearest face) and bind to the rig."""
        for g in list(o.vertex_groups): o.vertex_groups.remove(g)
        for g in self.ref.vertex_groups: o.vertex_groups.new(name=g.name)
        dt = o.modifiers.new('w', 'DATA_TRANSFER'); dt.object = self.ref
        dt.use_vert_data = True; dt.data_types_verts = {'VGROUP_WEIGHTS'}; dt.vert_mapping = 'POLYINTERP_NEAREST'
        dt.layers_vgroup_select_src = 'ALL'; dt.layers_vgroup_select_dst = 'NAME'
        apply_all(o)
        return bind(o, self.rig)

    def visible_skin(self, name, keep_fn, mat, slim_neck=0.85, hand_scale=0.86, decimate=0.22):
        o = self.copy_ref(name, keep_fn)
        # slimmer anime neck and slightly smaller hands
        d = self.dominant(o)
        ax0, ax1 = self.neck, self.head0
        for i, v in enumerate(o.data.vertices):
            if d[i] in ('neck_01', 'head'):
                t = max(0, min(1, (v.co.z - ax0.z) / max(1e-4, ax1.z - ax0.z)))
                c = ax0.lerp(ax1, t); off = v.co - c; off.z = 0
                v.co = Vector((c.x + off.x * slim_neck, c.y + off.y * slim_neck, v.co.z))
            elif HAND(d[i]):
                side = 'l' if d[i].endswith('_l') else 'r'
                w = self.rig.data.bones['hand_' + side].head_local
                v.co = w + (v.co - w) * hand_scale
        if decimate < 1:
            dm = o.modifiers.new('d', 'DECIMATE'); dm.ratio = decimate; apply_all(o)
        o.data.materials.clear(); o.data.materials.append(mat)
        shade_smooth(o)
        return bind(o, self.rig)
