# Shared helpers for the v2 anime cast: toon materials (cel preview + flat glTF colour),
# inverted-hull outlines, small mesh utilities and the preview render setup.
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector, Matrix

ROOT = '/var/www/html/old/3d-quranic/'
HERE = ROOT + 'blender/v2/characters/'
TEX = HERE + 'tex/'
PREV = ROOT + 'blender/v2/previews/'
MODELS = ROOT + 'public/models/'
INK = '#2B1A10'

def hex_rgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
def lin(c):
    """sRGB (0..1 tuple or hex) -> linear, as Blender colour sockets want."""
    if isinstance(c, str): c = hex_rgb(c)
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c[:3])

# ---------------------------------------------------------------- materials
def toon_mat(name, color='#808080', image=None, shadow='#B7939A', rim=0.18, bands=(0.12, 0.42)):
    """Material with two outputs wired on demand (set_mode): a plain Principled BSDF
    (glTF export) and a cel network: Diffuse → Shader to RGB → constant ramp × base + rim."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    N = lambda t, x, y: (lambda n: (setattr(n, 'location', (x, y)), n)[1])(nt.nodes.new(t))
    out = N('ShaderNodeOutputMaterial', 900, 0); out.name = 'out'
    pr = N('ShaderNodeBsdfPrincipled', 500, 300); pr.name = 'gltf'
    pr.inputs['Roughness'].default_value = 0.85
    if 'Specular IOR Level' in pr.inputs: pr.inputs['Specular IOR Level'].default_value = 0.15
    if image:
        tx = N('ShaderNodeTexImage', 0, 300); tx.name = 'tex'; tx.image = image; tx.interpolation = 'Linear'
        base = tx.outputs['Color']
    else:
        rgb = N('ShaderNodeRGB', 0, 300); rgb.name = 'base'; rgb.outputs[0].default_value = (*lin(color), 1)
        base = rgb.outputs[0]
    nt.links.new(base, pr.inputs['Base Color'])
    # cel branch
    df = N('ShaderNodeBsdfDiffuse', 0, -100)
    s2r = N('ShaderNodeShaderToRGB', 180, -100)
    ramp = N('ShaderNodeValToRGB', 360, -100); r = ramp.color_ramp; r.interpolation = 'CONSTANT'
    sh = lin(shadow)
    r.elements[0].position = 0.0; r.elements[0].color = (*[a * 0.82 for a in sh], 1)
    r.elements[1].position = bands[0]; r.elements[1].color = (*sh, 1)
    e = r.elements.new(bands[1]); e.color = (1, 0.97, 0.93, 1)
    mul = N('ShaderNodeMix', 600, -100); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
    mul.inputs['Factor'].default_value = 1
    nt.links.new(df.outputs[0], s2r.inputs[0]); nt.links.new(s2r.outputs['Color'], ramp.inputs['Fac'])
    nt.links.new(base, mul.inputs[6]); nt.links.new(ramp.outputs['Color'], mul.inputs[7])
    lw = N('ShaderNodeLayerWeight', 360, -350); lw.inputs['Blend'].default_value = 0.25
    rr = N('ShaderNodeMath', 540, -350); rr.operation = 'GREATER_THAN'; rr.inputs[1].default_value = 0.72
    rs = N('ShaderNodeMath', 700, -350); rs.operation = 'MULTIPLY'; rs.inputs[1].default_value = rim
    nt.links.new(lw.outputs['Facing'], rr.inputs[0]); nt.links.new(rr.outputs[0], rs.inputs[0])
    add = N('ShaderNodeMix', 760, -150); add.data_type = 'RGBA'; add.blend_type = 'ADD'
    nt.links.new(rs.outputs[0], add.inputs['Factor']); nt.links.new(mul.outputs[2], add.inputs[6])
    add.inputs[7].default_value = (1, 0.85, 0.6, 1)
    em = N('ShaderNodeEmission', 820, -150); em.name = 'cel'
    nt.links.new(add.outputs[2], em.inputs['Color'])
    m.diffuse_color = (*lin(color if not image else '#d9a383'), 1)
    m.roughness = 0.9
    set_mode(m, 'cel')
    return m

def outline_mat():
    m = bpy.data.materials.get('outline') or bpy.data.materials.new('outline')
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.name = 'out'
    pr = nt.nodes.new('ShaderNodeBsdfPrincipled'); pr.name = 'gltf'
    pr.inputs['Base Color'].default_value = (*lin(INK), 1); pr.inputs['Roughness'].default_value = 1
    em = nt.nodes.new('ShaderNodeEmission'); em.name = 'cel'; em.inputs['Color'].default_value = (*lin(INK), 1)
    m.use_backface_culling = True; m.diffuse_color = (*lin(INK), 1)
    set_mode(m, 'cel')
    return m

def set_mode(m, mode):
    nt = m.node_tree; out = nt.nodes.get('out')
    src = nt.nodes.get('cel' if mode == 'cel' else 'gltf')
    if out and src: nt.links.new(src.outputs[0], out.inputs['Surface'])

def all_mode(mode):
    for m in bpy.data.materials:
        if m.use_nodes and m.node_tree.nodes.get('gltf'): set_mode(m, mode)

def save_image(name, rgb, alpha=None):
    """rgb: (h, w, 3) float sRGB, row 0 = bottom. Saved as PNG under tex/ and loaded."""
    os.makedirs(TEX, exist_ok=True)
    h, w = rgb.shape[:2]
    img = bpy.data.images.get(name)
    if img: bpy.data.images.remove(img)
    img = bpy.data.images.new(name, w, h, alpha=alpha is not None)
    a = np.ones((h, w, 1)) if alpha is None else alpha[..., None]
    img.pixels.foreach_set(np.concatenate([np.clip(rgb, 0, 1), a], -1).astype(np.float32).ravel())
    img.filepath_raw = TEX + name + '.png'; img.file_format = 'PNG'; img.save()
    img.filepath = TEX + name + '.png'; img.source = 'FILE'; img.reload()
    return img

# ---------------------------------------------------------------- mesh utils
def apply_all(o):
    with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o], selected_editable_objects=[o]):
        for m in list(o.modifiers): bpy.ops.object.modifier_apply(modifier=m.name)

def new_obj(name, me, col):
    if name in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    o = bpy.data.objects.new(name, me); col.objects.link(o); return o

def bm_obj(bm, name, col, material=None, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    o = new_obj(name, me, col)
    if material: me.materials.append(material)
    return o

def shade_smooth(o, sharp_angle=None):
    for p in o.data.polygons: p.use_smooth = True
    if sharp_angle:
        with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o], selected_editable_objects=[o]):
            try: bpy.ops.object.shade_auto_smooth(angle=math.radians(sharp_angle))
            except Exception: pass

def keep_verts(o, keep):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in range(len(bm.verts)) if not keep[i]], context='VERTS')
    bm.to_mesh(o.data); bm.free()

def inflate(o, amount_fn):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.normal_update()
    for v in bm.verts: v.co += v.normal * amount_fn(v.co.copy(), v.normal.copy())
    bm.to_mesh(o.data); bm.free()

def smooth_mod(o, factor, iters, group=None):
    s = o.modifiers.new('sm', 'SMOOTH'); s.factor = factor; s.iterations = iters
    if group: s.vertex_group = group
    apply_all(o)

def rigid_to(o, rig, bone):
    for g in list(o.vertex_groups): o.vertex_groups.remove(g)
    g = o.vertex_groups.new(name=bone); g.add(range(len(o.data.vertices)), 1.0, 'REPLACE')
    bind(o, rig); return o

def bind(o, rig):
    o.parent = rig; o.matrix_parent_inverse = rig.matrix_world.inverted()
    if not any(m.type == 'ARMATURE' for m in o.modifiers):
        m = o.modifiers.new('rig', 'ARMATURE'); m.object = rig
    return o

def clump(bm, root, direction, length, radius, curl_axis=None, curl=0.0, segs=6, rings=6, flat=0.75, fat=0.35):
    """A sculpted hair / beard clump: rounded teardrop along a curve that hooks by `curl` radians."""
    d = Vector(direction).normalized()
    ax = Vector(curl_axis).normalized() if curl_axis is not None else d.orthogonal().normalized()
    pts, p, dd = [], Vector(root), d.copy()
    step = length / rings
    for i in range(rings + 1):
        pts.append(p.copy()); p = p + dd * step
        dd = Matrix.Rotation(curl / rings, 3, ax) @ dd
    loops = []
    for i, c in enumerate(pts[:-1]):
        t = i / rings
        tan = (pts[i + 1] - c).normalized()
        a = ax - tan * ax.dot(tan); a.normalize(); b = tan.cross(a)
        r = radius * (fat + (1 - fat) * math.sin(math.pi * min(1, 0.25 + t * 1.1))) * (1 - t) ** 0.55 + 0.0006
        loops.append([bm.verts.new(c + (a * math.cos(k / segs * math.tau) * flat + b * math.sin(k / segs * math.tau)) * r) for k in range(segs)])
    for A, B in zip(loops, loops[1:]):
        for k in range(segs): bm.faces.new((A[k], A[(k + 1) % segs], B[(k + 1) % segs], B[k]))
    tip = bm.verts.new(pts[-1])
    for k in range(segs): bm.faces.new((loops[-1][k], loops[-1][(k + 1) % segs], tip))
    base = bm.verts.new(pts[0] - d * radius * 0.3)
    for k in range(segs): bm.faces.new((loops[0][(k + 1) % segs], loops[0][k], base))

def tube(bm, pts, radius, segs=8, closed=True, flat=1.0, up=Vector((0, 0, 1))):
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        ax = d.cross(up); ax = ax if ax.length > 1e-3 else d.orthogonal(); ax.normalize(); bx = d.cross(ax)
        r = radius(i / (len(pts) - 1)) if callable(radius) else radius
        rings.append([bm.verts.new(p + (ax * math.cos(a) + bx * math.sin(a) * flat) * r) for a in (k / segs * math.tau for k in range(segs))])
    for a, b in zip(rings, rings[1:]):
        for k in range(segs): bm.faces.new((a[k], a[(k + 1) % segs], b[(k + 1) % segs], b[k]))
    if closed:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    return rings

def lathe(bm, rings_def, segs=24, center=(0, 0), cap_top=False, cap_bottom=False):
    """rings_def: list of (z, rx, ry, fn) where fn(theta)->radius multiplier (folds) or None.
    theta 0 = +X, -pi/2 = front (-Y)."""
    cx, cy = center; loops = []
    for z, rx, ry, fn in rings_def:
        loop = []
        for k in range(segs):
            th = k / segs * math.tau; f = fn(th) if fn else 1
            loop.append(bm.verts.new((cx + rx * f * math.cos(th), cy + ry * f * math.sin(th), z)))
        loops.append(loop)
    for a, b in zip(loops, loops[1:]):
        for k in range(segs): bm.faces.new((a[k], a[(k + 1) % segs], b[(k + 1) % segs], b[k]))
    if cap_top: bm.faces.new(loops[0])
    if cap_bottom: bm.faces.new(list(reversed(loops[-1])))
    return loops

def make_outline(o, thickness, name=None, scale_group=None):
    """Inverted hull: copy, push along smooth vertex normals, flip; material 'outline'.
    Keeps vertex groups + armature so it stays skinned."""
    me = o.data.copy(); me.name = (name or o.name + '_outline')
    bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
    dl = bm.verts.layers.deform.active
    sg = o.vertex_groups[scale_group].index if scale_group and scale_group in o.vertex_groups else None
    for v in bm.verts:
        k = 1.0
        if sg is not None and dl: k = v[dl].get(sg, 1.0)
        v.co += v.normal * thickness * k
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    me.materials.clear(); me.materials.append(outline_mat())
    for p in me.polygons: p.material_index = 0
    oo = new_obj(name or o.name + '_outline', me, o.users_collection[0])
    oo.matrix_world = o.matrix_world.copy()
    for g in o.vertex_groups: oo.vertex_groups.new(name=g.name)
    if o.parent: oo.parent = o.parent; oo.matrix_parent_inverse = o.matrix_parent_inverse.copy()
    for m in o.modifiers:
        if m.type == 'ARMATURE': a = oo.modifiers.new('rig', 'ARMATURE'); a.object = m.object
    return oo

def join(objs, name):
    for x in bpy.context.selected_objects: x.select_set(False)
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs, selected_objects=objs, object=objs[0]):
        bpy.ops.object.join()
    o = objs[0]; o.name = name; o.data.name = name
    return o

def tri_count(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)

# ---------------------------------------------------------------- render setup
def render_setup(res=(700, 1000)):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    w = sc.world or bpy.data.worlds.new('World'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    bg = nt.nodes.new('ShaderNodeBackground'); out = nt.nodes.new('ShaderNodeOutputWorld')
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); rp = nt.nodes.new('ShaderNodeValToRGB')
    rp.color_ramp.elements[0].color = (*lin('#F2C98B'), 1); rp.color_ramp.elements[1].color = (*lin('#9DB3D6'), 1)
    nt.links.new(tc.outputs['Window'], sep.inputs[0]); nt.links.new(sep.outputs['Y'], rp.inputs['Fac'])
    nt.links.new(rp.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.0
    amb = nt.nodes.new('ShaderNodeBackground'); amb.inputs['Color'].default_value = (*lin('#C9B8A8'), 1); amb.inputs['Strength'].default_value = 0.25
    lp = nt.nodes.new('ShaderNodeLightPath'); mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mx.inputs[0]); nt.links.new(amb.outputs[0], mx.inputs[1]); nt.links.new(bg.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    for o in [o for o in bpy.data.objects if o.name.startswith('_prev_')]: bpy.data.objects.remove(o, do_unlink=True)
    ld = bpy.data.lights.get('_prev_sun') or bpy.data.lights.new('_prev_sun', 'SUN'); ld.energy = 3.5; ld.color = lin('#FFF1DC')
    ld.angle = math.radians(2); ld.use_shadow = False
    sun = bpy.data.objects.new('_prev_sun', ld); sc.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    cam_d = bpy.data.cameras.get('_prev_cam') or bpy.data.cameras.new('_prev_cam'); cam_d.type = 'ORTHO'
    cam = bpy.data.objects.new('_prev_cam', cam_d); sc.collection.objects.link(cam); sc.camera = cam
    return cam

def frame_camera(cam, center, height, dist=6, elev=0.0, yaw=0.0):
    cam.data.ortho_scale = height
    d = Vector((math.sin(yaw) * math.cos(elev), -math.cos(yaw) * math.cos(elev), math.sin(elev))) * dist
    cam.location = Vector(center) + d
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_end = 100

def render_to(path):
    bpy.context.scene.render.filepath = path; bpy.ops.render.render(write_still=True)

def stitch(paths, out, cols=None):
    imgs = [bpy.data.images.load(p) for p in paths]
    arrs = []
    for im in imgs:
        a = np.empty(im.size[0] * im.size[1] * 4, np.float32); im.pixels.foreach_get(a)
        arrs.append(a.reshape(im.size[1], im.size[0], 4))
    cols = cols or len(arrs); rows = math.ceil(len(arrs) / cols)
    h, w = arrs[0].shape[:2]
    big = np.ones((h * rows, w * cols, 4), np.float32)
    for i, a in enumerate(arrs):
        r, c = divmod(i, cols); big[(rows - 1 - r) * h:(rows - r) * h, c * w:(c + 1) * w] = a
    im = bpy.data.images.new('_stitch', w * cols, h * rows); im.pixels.foreach_set(big.ravel())
    im.filepath_raw = out; im.file_format = 'PNG'; im.save()
    for x in imgs: bpy.data.images.remove(x)
    bpy.data.images.remove(im)
    for p in paths: os.remove(p)
