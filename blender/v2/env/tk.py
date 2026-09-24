# Toon kit: shared helpers for the v2 environment build (anime / Ghibli-like look).
# - Geometry is built with bmesh into a Builder (one mesh, several materials), with soft
#   bevels and a gentle hand-made wobble.
# - Materials are `toon_*`: Principled "Base Color" for glTF + an EEVEE cel chain for previews
#   (Diffuse -> Shader to RGB -> 3-band CONSTANT ramp x base colour + warm rim).
# - Outlines: inverted hull `<obj>_outline` (outward-offset copy, normal winding kept) with
#   material `outline`; Blender shows only its back faces (= three.js side: BackSide).
import bpy, bmesh, math, random, os, json
from mathutils import Vector, Matrix, Euler, noise

ROOT = '/var/www/html/old/3d-quranic/'
OUT = ROOT + 'public/models/env/'
V2 = ROOT + 'blender/v2/'
PREV = V2 + 'previews/'

def hexc(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)   # sRGB -> linear

# name: (hex, flags)   flags: n = no outline, d = double sided, w = wind-animated in game
PAL = {
    'toon_lime': ('#F1E4C8', ''), 'toon_lime_warm': ('#E8CFA4', ''),
    'toon_plaster': ('#D29A62', ''), 'toon_plaster_light': ('#E2B07A', ''),
    'toon_mudbrick': ('#B0703F', ''), 'toon_mud_dark': ('#8A5634', ''),
    'toon_wood': ('#9A6A3E', ''), 'toon_wood_dark': ('#5E3D24', ''),
    'toon_wood_blue': ('#3F8CC0', ''), 'toon_wood_green': ('#4E9A72', ''),
    'toon_paint_blue': ('#2F74B0', 'n'), 'toon_paint_green': ('#3F8F5A', 'n'),
    'toon_paint_ochre': ('#D9962E', 'n'), 'toon_paint_white': ('#FAF3E2', 'n'), 'toon_paint_red': ('#B8452E', 'n'),
    'toon_window_dark': ('#3A2A22', 'n'),
    'toon_straw': ('#E3BC62', ''), 'toon_firewood': ('#8E6A45', ''), 'toon_stalks': ('#C9A566', ''),
    'toon_clay': ('#C8703E', ''), 'toon_clay_dark': ('#9C5230', ''),
    'toon_stone': ('#CDB897', ''), 'toon_stone_dark': ('#A89678', ''),
    'toon_bark': ('#8C6A48', ''), 'toon_bark_dark': ('#6A4C32', ''),
    'toon_frond': ('#5E8C2E', 'dw'), 'toon_frond_light': ('#8DB64A', 'dw'), 'toon_frond_dry': ('#B8904E', 'dw'),
    'toon_dates': ('#B8481C', ''), 'toon_dates_gold': ('#E0A03A', ''),
    'toon_leaf': ('#4E7E2C', 'w'), 'toon_leaf_light': ('#7FAE44', 'w'), 'toon_leaf_dark': ('#3A6424', 'w'),
    'toon_berseem': ('#4F9A34', 'w'), 'toon_berseem_flower': ('#F2EEF0', 'nw'),
    'toon_maize': ('#6FA03A', 'dw'), 'toon_maize_tassel': ('#E0C26A', 'nw'), 'toon_maize_cob': ('#E8C85A', ''),
    'toon_wheat': ('#DDBB5C', 'ndw'), 'toon_wheat_green': ('#A8A84A', 'ndw'),
    'toon_cotton': ('#F6F2E8', ''), 'toon_cabbage': ('#8CBF5A', 'w'), 'toon_cabbage_dark': ('#5E9A3C', 'w'),
    'toon_grass': ('#6FA23A', 'ndw'), 'toon_grass_light': ('#A4C656', 'ndw'), 'toon_grass_dry': ('#C8B266', 'ndw'),
    'toon_reed': ('#7C9C40', 'ndw'), 'toon_reed_head': ('#9A7248', 'n'),
    'toon_flower_pink': ('#E0408A', ''), 'toon_flower_magenta': ('#B82E78', ''), 'toon_flower_yellow': ('#F4C94A', 'n'),
    'toon_flower_white': ('#FFF8EC', 'n'), 'toon_flower_purple': ('#8E6CC8', 'n'), 'toon_flower_red': ('#D9443A', 'n'),
    'toon_mud': ('#7E5E40', ''), 'toon_earth': ('#9A7550', ''), 'toon_earth_dark': ('#6E5238', ''),
    'toon_ground': ('#C9A877', ''), 'toon_ground_green': ('#8DAE4C', ''),
    'toon_fabric_red': ('#B8472E', ''), 'toon_fabric_cream': ('#EDD9AE', ''), 'toon_fabric_blue': ('#3D6E9E', ''),
    'toon_fabric_ochre': ('#D89A38', ''), 'toon_fabric_green': ('#5A8A4A', ''),
    'toon_rope': ('#B89A62', ''), 'toon_iron': ('#4C4A4E', ''),
    'toon_produce': ('#E88A2A', ''), 'toon_tomato': ('#D8432E', ''),
    'toon_water': ('#3E9C94', 'n'), 'toon_water_foam': ('#F2FBF4', 'n'),
    'toon_pigeon': ('#E9E6E0', ''),
}
INK = '#2B1A10'
SHADOW_TINT = (0.56, 0.47, 0.62)   # warm-violet shadows (anime)

def flags(name): return PAL.get(name, ('#888888', ''))[1]

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def _nodes(m):
    try: m.use_nodes = True
    except Exception: pass
    return m.node_tree.nodes, m.node_tree.links

def toon_group():
    """Node group: cel shading of a base colour. In: Color, Shadow tint. Out: Shader."""
    g = bpy.data.node_groups.get('ToonCel')
    if g: return g
    g = bpy.data.node_groups.new('ToonCel', 'ShaderNodeTree')
    g.interface.new_socket('Color', in_out='INPUT', socket_type='NodeSocketColor')
    g.interface.new_socket('Shadow', in_out='INPUT', socket_type='NodeSocketColor')
    g.interface.new_socket('Shader', in_out='OUTPUT', socket_type='NodeSocketShader')
    n, l = g.nodes, g.links
    gi = n.new('NodeGroupInput'); go = n.new('NodeGroupOutput')
    dif = n.new('ShaderNodeBsdfDiffuse'); dif.inputs['Color'].default_value = (1, 1, 1, 1)
    s2r = n.new('ShaderNodeShaderToRGB'); l.new(dif.outputs[0], s2r.inputs[0])
    bw = n.new('ShaderNodeRGBToBW'); bw.name = 'BW'; l.new(s2r.outputs['Color'], bw.inputs[0])
    mr = n.new('ShaderNodeMapRange'); mr.name = 'RANGE'; mr.inputs['From Max'].default_value = 3.2
    l.new(bw.outputs[0], mr.inputs['Value'])
    ramp = n.new('ShaderNodeValToRGB'); ramp.name = 'BANDS'; ramp.color_ramp.interpolation = 'CONSTANT'
    e = ramp.color_ramp.elements
    e[0].position = 0.0; e[0].color = (0, 0, 0, 1)
    e[1].position = 0.16; e[1].color = (0.45, 0.45, 0.45, 1)
    e3 = e.new(0.42); e3.color = (1, 1, 1, 1)
    l.new(mr.outputs[0], ramp.inputs[0])
    sh = n.new('ShaderNodeMix'); sh.data_type = 'RGBA'; sh.blend_type = 'MULTIPLY'; sh.inputs['Factor'].default_value = 1
    l.new(gi.outputs['Color'], sh.inputs[6]); l.new(gi.outputs['Shadow'], sh.inputs[7])
    lit = n.new('ShaderNodeMix'); lit.data_type = 'RGBA'; lit.blend_type = 'MULTIPLY'; lit.inputs['Factor'].default_value = 1
    l.new(gi.outputs['Color'], lit.inputs[6]); lit.inputs[7].default_value = (1.06, 1.0, 0.88, 1)
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    l.new(ramp.outputs['Color'], mix.inputs['Factor']); l.new(sh.outputs[2], mix.inputs[6]); l.new(lit.outputs[2], mix.inputs[7])
    lw = n.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.35
    rs = n.new('ShaderNodeMath'); rs.operation = 'GREATER_THAN'; rs.inputs[1].default_value = 0.75
    l.new(lw.outputs['Facing'], rs.inputs[0])
    rl = n.new('ShaderNodeMath'); rl.operation = 'MULTIPLY'; l.new(rs.outputs[0], rl.inputs[0]); l.new(ramp.outputs['Color'], rl.inputs[1])
    rk = n.new('ShaderNodeMath'); rk.operation = 'MULTIPLY'; rk.inputs[1].default_value = 0.15; l.new(rl.outputs[0], rk.inputs[0])
    add = n.new('ShaderNodeMix'); add.data_type = 'RGBA'; add.blend_type = 'ADD'
    l.new(rk.outputs[0], add.inputs['Factor']); l.new(mix.outputs[2], add.inputs[6]); add.inputs[7].default_value = (1.0, 0.78, 0.42, 1)
    em = n.new('ShaderNodeEmission'); l.new(add.outputs[2], em.inputs['Color'])
    l.new(em.outputs[0], go.inputs['Shader'])
    return g

SPECIAL = {}   # name -> factory (e.g. toon_water from water.py)

def M(name):
    """Get/create a toon material (or `outline`)."""
    m = bpy.data.materials.get(name)
    if m: return m
    if name in SPECIAL: return SPECIAL[name]()
    m = bpy.data.materials.new(name)
    n, l = _nodes(m); n.clear()
    out = n.new('ShaderNodeOutputMaterial'); out.name = 'OUT'; out.location = (600, 0)
    pbr = n.new('ShaderNodeBsdfPrincipled'); pbr.name = 'PBR'; pbr.location = (200, 300)
    if name == 'outline':
        c = hexc(INK)
        pbr.inputs['Base Color'].default_value = (*c, 1); pbr.inputs['Roughness'].default_value = 1
        em = n.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*c, 1)
        tr = n.new('ShaderNodeBsdfTransparent'); geo = n.new('ShaderNodeNewGeometry')
        mx = n.new('ShaderNodeMixShader'); mx.name = 'TOON'
        l.new(geo.outputs['Backfacing'], mx.inputs[0]); l.new(tr.outputs[0], mx.inputs[1]); l.new(em.outputs[0], mx.inputs[2])
        l.new(mx.outputs[0], out.inputs['Surface'])
        m.diffuse_color = (*c, 1)
        return m
    hx, fl = PAL.get(name, ('#888888', ''))
    c = hexc(hx)
    pbr.inputs['Base Color'].default_value = (*c, 1); pbr.inputs['Roughness'].default_value = 0.9
    m.diffuse_color = (*c, 1)
    grp = n.new('ShaderNodeGroup'); grp.node_tree = toon_group(); grp.name = 'TOON'; grp.location = (200, -100)
    rgb = n.new('ShaderNodeRGB'); rgb.outputs[0].default_value = (*c, 1); rgb.name = 'BASE'; rgb.location = (-400, 0)
    tex = n.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value = 1.6; tex.location = (-600, -200)
    va = n.new('ShaderNodeMix'); va.data_type = 'RGBA'; va.blend_type = 'OVERLAY'; va.inputs['Factor'].default_value = 0.10
    l.new(rgb.outputs[0], va.inputs[6]); l.new(tex.outputs['Color'], va.inputs[7])
    l.new(va.outputs[2], grp.inputs['Color'])
    grp.inputs['Shadow'].default_value = (*SHADOW_TINT, 1)
    m.use_backface_culling = False
    l.new(grp.outputs[0], out.inputs['Surface'])
    return m

def export_mode(on):
    """Swap every material output between the cel chain (preview) and Principled (glTF)."""
    for m in bpy.data.materials:
        if not m.node_tree: continue
        n, l = m.node_tree.nodes, m.node_tree.links
        out, pbr, toon = n.get('OUT'), n.get('PBR'), n.get('TOON')
        if not (out and pbr and toon): continue
        src = pbr if on else toon
        for lk in list(out.inputs['Surface'].links): l.remove(lk)
        l.new(src.outputs[0], out.inputs['Surface'])

# ---------------------------------------------------------------------------------------
# geometry builder
def wob(p, amp, freq=1.3, seed=0):
    if not amp: return p
    o = Vector((seed * 7.1, seed * 3.3, seed * 1.7))
    return p + noise.noise_vector(p * freq + o) * amp

def RT(loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    return Matrix.LocRotScale(Vector(loc), Euler(rot), Vector(scale))

class B:
    """One mesh, several materials. Primitives are created in local bmeshes, transformed and merged."""
    def __init__(self, seed=0):
        self.bm = bmesh.new(); self.mats = []; self.seed = seed; self.rnd = random.Random(seed)
    def mi(self, name):
        if name not in self.mats: self.mats.append(name)
        return self.mats.index(name)
    def put(self, src, mat, M=None, smooth=True, wobble=0.0, freq=1.3):
        src.verts.index_update()
        vm = []
        for v in src.verts:
            p = (M @ v.co) if M else v.co.copy()
            vm.append(self.bm.verts.new(wob(p, wobble, freq, self.seed)))
        k = self.mi(mat)
        for f in src.faces:
            try:
                nf = self.bm.faces.new([vm[v.index] for v in f.verts]); nf.material_index = k; nf.smooth = smooth
            except ValueError: pass
        src.free()
        return self
    def box(self, size, loc=(0, 0, 0), mat='toon_plaster', bevel=0.0, seg=2, rot=(0, 0, 0), taper=1.0, smooth=True, wobble=0.0, freq=1.3, top_only=False, taper_y=None):
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
            if v.co.z > 0 and taper != 1.0:
                v.co.x *= taper; v.co.y *= (taper if taper_y is None else taper_y)
        if bevel:
            ed = bm.edges[:] if not top_only else [e for e in bm.edges if all(v.co.z > 0 for v in e.verts)]
            bmesh.ops.bevel(bm, geom=ed, offset=min(bevel, min(size) * 0.49), segments=seg, affect='EDGES', profile=0.5, clamp_overlap=True)
        return self.put(bm, mat, RT(loc, rot), smooth, wobble, freq)
    def cyl(self, r1, r2, depth, loc=(0, 0, 0), mat='toon_wood', rot=(0, 0, 0), verts=10, smooth=True, cap=True, wobble=0.0, bevel=0.0, scale=(1, 1, 1)):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=verts, radius1=r1, radius2=r2, depth=depth)
        if bevel and cap:
            ed = [e for e in bm.edges if len(e.link_faces) == 2 and abs(e.link_faces[0].normal.dot(e.link_faces[1].normal)) < 0.5]
            bmesh.ops.bevel(bm, geom=ed, offset=bevel, segments=2, affect='EDGES', profile=0.5, clamp_overlap=True)
        return self.put(bm, mat, RT(loc, rot, scale), smooth, wobble)
    def ball(self, r, loc=(0, 0, 0), mat='toon_leaf', scale=(1, 1, 1), sub=1, rot=(0, 0, 0), smooth=True, wobble=0.0, freq=2.0, flat_bottom=None):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub + 1, radius=r)   # sub=0: 20 tris, 1: 80, 2: 320
        if flat_bottom is not None:
            for v in bm.verts: v.co.z = max(v.co.z, -r * flat_bottom)
        return self.put(bm, mat, RT(loc, rot, scale), smooth, wobble, freq)
    def uvball(self, r, loc=(0, 0, 0), mat='toon_leaf', scale=(1, 1, 1), seg=8, rings=5, rot=(0, 0, 0), smooth=True, wobble=0.0, freq=2.0, cut=None):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
        if cut is not None:
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < cut * r - 1e-5], context='VERTS')
        return self.put(bm, mat, RT(loc, rot, scale), smooth, wobble, freq)
    def lathe(self, prof, loc=(0, 0, 0), mat='toon_clay', segs=12, rot=(0, 0, 0), smooth=True, close_top=False, wobble=0.0, scale=(1, 1, 1)):
        bm = bmesh.new(); rings = []
        for r, z in prof:
            if r < 1e-3: rings.append([bm.verts.new((0, 0, z))])
            else: rings.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for a in (i / segs * math.tau for i in range(segs))])
        for a, b in zip(rings, rings[1:]):
            if len(a) == 1:
                for i in range(segs): bm.faces.new((a[0], b[i], b[(i + 1) % segs]))
            elif len(b) == 1:
                for i in range(segs): bm.faces.new((a[i], a[(i + 1) % segs], b[0]))
            else:
                for i in range(segs): bm.faces.new((a[i], a[(i + 1) % segs], b[(i + 1) % segs], b[i]))
        if close_top and len(rings[-1]) > 1: bm.faces.new(rings[-1])
        return self.put(bm, mat, RT(loc, rot, scale), smooth, wobble)
    def tube(self, pts, radii, mat='toon_bark', sides=8, smooth=True, cap=True, wobble=0.0, ring_fn=None):
        if not isinstance(radii, (list, tuple)): radii = [radii] * len(pts)
        pts = [Vector(p) for p in pts]; bm = bmesh.new(); rings = []
        up = Vector((0, 0, 1))
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            ref = Vector((1, 0, 0)) if abs(t.dot(up)) > 0.9 else up
            s = t.cross(ref).normalized(); u = t.cross(s)
            ring = []
            for k in range(sides):
                a = k / sides * math.tau; f = ring_fn(i, k) if ring_fn else 1.0
                ring.append(bm.verts.new(p + (s * math.cos(a) + u * math.sin(a)) * radii[i] * f))
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            for k in range(sides): bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]))
        if cap:
            bm.faces.new(rings[-1]); bm.faces.new(list(reversed(rings[0])))
        return self.put(bm, mat, None, smooth, wobble)
    def strip(self, pts, widths, normal_hint=(0, 0, 1), mat='toon_leaf', smooth=True, side=None):
        if not isinstance(widths, (list, tuple)): widths = [widths] * len(pts)
        pts = [Vector(p) for p in pts]; bm = bmesh.new(); L = []; R = []
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            s = Vector(side) if side else t.cross(Vector(normal_hint))
            s = s.normalized() if s.length > 1e-5 else Vector((1, 0, 0))
            L.append(bm.verts.new(p - s * widths[i] / 2)); R.append(bm.verts.new(p + s * widths[i] / 2))
        for i in range(len(pts) - 1):
            if widths[i + 1] < 1e-4: bm.faces.new((L[i], R[i], R[i + 1]))
            else: bm.faces.new((L[i], R[i], R[i + 1], L[i + 1]))
        return self.put(bm, mat, None, smooth)
    def poly(self, verts, mat, smooth=False):
        bm = bmesh.new(); bm.faces.new([bm.verts.new(v) for v in verts]); return self.put(bm, mat, None, smooth)
    def disc(self, r, loc, mat, segs=10, rot=(0, 0, 0), scale=(1, 1, 1)):
        bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=True, cap_tris=False, segments=segs, radius=r)
        return self.put(bm, mat, RT(loc, rot, scale), False)
    def merge_from(self, other, M=None):
        other.bm.verts.index_update()
        vm = [self.bm.verts.new((M @ v.co) if M else v.co.copy()) for v in other.bm.verts]
        for f in other.bm.faces:
            try:
                nf = self.bm.faces.new([vm[v.index] for v in f.verts]); nf.material_index = self.mi(other.mats[f.material_index]); nf.smooth = f.smooth
            except ValueError: pass
        return self
    def obj(self, name, col=None):
        me = bpy.data.meshes.new(name); self.bm.normal_update(); self.bm.to_mesh(me); self.bm.free()
        for n in self.mats: me.materials.append(M(n))
        o = bpy.data.objects.new(name, me)
        (col or bpy.context.scene.collection).objects.link(o)
        return o

def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)

# ---------------------------------------------------------------------------------------
def outline(o, t=0.02, name=None, skip=(), min_size=0.0):
    """Inverted-hull outline: outward copy along even-thickness vertex normals, material `outline`.
    Winding is kept (outward) -> render back faces only (three.js BackSide)."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    mats = [m.name for m in o.data.materials]
    kill = [f for f in bm.faces if 'n' in flags(mats[f.material_index]) or mats[f.material_index] in skip]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.faces.index_update()
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bm.faces.index_update()
    if min_size:   # drop hulls of tiny parts (pots, studs, fruit) to save triangles
        seen, small = set(), []
        for f in bm.faces:
            if f.index in seen: continue
            stack, isl = [f], []
            seen.add(f.index)
            while stack:
                g = stack.pop(); isl.append(g)
                for e in g.edges:
                    for h in e.link_faces:
                        if h.index not in seen: seen.add(h.index); stack.append(h)
            vs = {v for g in isl for v in g.verts}
            lo = Vector((min(v.co.x for v in vs), min(v.co.y for v in vs), min(v.co.z for v in vs)))
            hi = Vector((max(v.co.x for v in vs), max(v.co.y for v in vs), max(v.co.z for v in vs)))
            if (hi - lo).length < min_size: small += isl
        bmesh.ops.delete(bm, geom=small, context='FACES')
    bm.normal_update()
    moves = []
    for v in bm.verts:
        if not v.link_faces: moves.append(None); continue
        n = Vector((0, 0, 0))
        for f in v.link_faces: n += f.normal * max(f.calc_area(), 1e-6) ** 0.5
        if n.length < 1e-8: moves.append(None); continue
        n.normalize()
        d = min(max(n.dot(f.normal), 0.4) for f in v.link_faces)
        moves.append(n * (t / d))
    for v, mv in zip(bm.verts, moves):
        if mv is not None: v.co += mv
    for f in bm.faces: f.material_index = 0; f.smooth = True
    nm = name or o.name + '_outline'
    me = bpy.data.meshes.new(nm); bm.to_mesh(me); bm.free()
    me.materials.append(M('outline'))
    h = bpy.data.objects.new(nm, me)
    for c in o.users_collection: c.objects.link(h)
    h.matrix_world = o.matrix_world.copy()
    return h

def lod(o, ratio, name=None):
    c = o.copy(); c.data = o.data.copy(); c.name = name or o.name + '_LOD1'
    for col in o.users_collection: col.objects.link(c)
    m = c.modifiers.new('lod', 'DECIMATE'); m.ratio = ratio; m.use_collapse_triangulate = True
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); ev = c.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev); c.modifiers.clear(); old = c.data; c.data = me; me.name = c.name
    bpy.data.meshes.remove(old)
    return c

def collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col:
        for o in list(col.objects): bpy.data.objects.remove(o, do_unlink=True)
    else:
        col = bpy.data.collections.new(name); (parent or bpy.context.scene.collection).children.link(col)
    return col

def export(objs, path):
    export_mode(True)
    bpy.context.view_layer.update()
    for x in bpy.context.view_layer.objects: x.select_set(False)
    saved = [o.matrix_world.copy() for o in objs]
    for o in objs:
        o.hide_set(False); o.hide_viewport = False; o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True,
                              export_yup=True, export_draco_mesh_compression_enable=True,
                              export_draco_mesh_compression_level=6, export_materials='EXPORT',
                              export_image_format='NONE', export_animations=False)
    export_mode(False)
    for o in objs: o.select_set(False)
    return os.path.getsize(path)

REPORT = []
def asset(name, b, col, t=0.02, lod_ratio=None, skip=(), out=True, lod_t=None, hull=True, loc=(0, 0, 0)):
    """Builder -> object `name` + `name_outline` (+ `name_LOD1` pair); exports GLB with origin at 0,
    then moves the objects to `loc` for the showcase layout in env.blend."""
    o = b.obj(name, col)
    objs = [o]
    if hull: objs.append(outline(o, t, skip=skip))
    lo = None
    if lod_ratio:
        lo = lod(o, lod_ratio, name + '_LOD1'); objs.append(lo)
        if hull: objs.append(outline(lo, lod_t or t * 1.3, skip=skip))
    size = export(objs, OUT + name + '.glb') if out else 0
    info = dict(name=name, tris=tris(o), tris_outline=tris(objs[1]) if hull else 0,
                tris_lod1=tris(lo) if lo else 0, kb=round(size / 1024, 1), mats=list(dict.fromkeys(m.name for m in o.data.materials)))
    REPORT.append(info); print('ASSET', json.dumps(info), flush=True)
    for x in objs:
        x.location = Vector(loc)
        if '_LOD1' in x.name: x.hide_render = True; x.hide_set(True)
    return o

def save_report(tag):
    p = V2 + f'env/_report_{tag}.json'; json.dump(REPORT, open(p, 'w'), indent=1)

# ---------------------------------------------------------------------------------------
# preview scene: warm sky, golden sun, EEVEE, Standard view
def look(sun_rot=(math.radians(64), 0, math.radians(65)), strength=3.2, res=(1600, 900)):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    for k, v in (('taa_render_samples', 24), ('use_shadows', True), ('shadow_ray_count', 1), ('shadow_step_count', 4)):
        try: setattr(sc.eevee, k, v)
        except Exception: pass
    w = bpy.data.worlds.get('ToonSky') or bpy.data.worlds.new('ToonSky'); sc.world = w
    n, l = _nodes(w); n.clear()
    out = n.new('ShaderNodeOutputWorld')
    tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Generated'], sep.inputs[0])
    ramp = n.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements
    e[0].position = 0.0; e[0].color = (*hexc('#F8DCA8'), 1)
    e[1].position = 0.6; e[1].color = (*hexc('#86ACD6'), 1)
    m = e.new(0.10); m.color = (*hexc('#F6CF96'), 1)
    m2 = e.new(0.3); m2.color = (*hexc('#DCD8C4'), 1)
    l.new(sep.outputs['Z'], ramp.inputs[0])
    bgc = n.new('ShaderNodeBackground'); l.new(ramp.outputs[0], bgc.inputs['Color']); bgc.inputs['Strength'].default_value = 1.0
    amb = n.new('ShaderNodeBackground'); amb.inputs['Color'].default_value = (*hexc('#B8A898'), 1); amb.inputs['Strength'].default_value = 0.5
    lp = n.new('ShaderNodeLightPath'); mx = n.new('ShaderNodeMixShader')
    l.new(lp.outputs['Is Camera Ray'], mx.inputs[0]); l.new(amb.outputs[0], mx.inputs[1]); l.new(bgc.outputs[0], mx.inputs[2])
    l.new(mx.outputs[0], out.inputs['Surface'])
    sun = bpy.data.objects.get('Sun')
    if not sun:
        ld = bpy.data.lights.new('Sun', 'SUN'); sun = bpy.data.objects.new('Sun', ld); sc.collection.objects.link(sun)
    sun.data.energy = strength; sun.data.color = hexc('#FFE4B8'); sun.data.angle = math.radians(1.0)
    sun.rotation_euler = sun_rot
    return sun

def camera(name, loc, target, lens=35):
    cam = bpy.data.objects.get(name)
    if not cam:
        cd = bpy.data.cameras.new(name); cam = bpy.data.objects.new(name, cd); bpy.context.scene.collection.objects.link(cam)
    cam.data.lens = lens; cam.data.clip_end = 800; cam.data.clip_start = 0.05
    cam.location = loc
    d = Vector(target) - Vector(loc); cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return cam

def render(path, cam=None, res=None):
    sc = bpy.context.scene
    if cam: sc.camera = cam
    if res: sc.render.resolution_x, sc.render.resolution_y = res
    export_mode(False)
    sc.render.filepath = path; sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)
    print('RENDERED', path, flush=True)
