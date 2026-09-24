# Place houses, mastaba, palms and props from public/models/env into the vignette,
# upgrade their flat materials to the game's PBR textures, add sky + sun, pose the cast.
import bpy, bmesh, math, os, sys, importlib, random
from mathutils import Vector, Matrix, Euler
sys.path.insert(0, '/var/www/html/old/3d-quranic/blender')
import lib; importlib.reload(lib)
from lib import clear_collection, box, lumpy, uv_world, mat, apply_all, MAT_COLORS
import env_scene; importlib.reload(env_scene)
from env_scene import height, canal_x, HOME, HOME_ROT, PUB, TEX, img, pbr_nodes

ENV = PUB + 'models/env/'
def load_lib():
    lib_c = bpy.data.collections.get('env_lib')
    if not lib_c or not len(lib_c.objects):
        lib_c = lib_c or bpy.data.collections.new('env_lib')
        if lib_c.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(lib_c)
        for f in sorted(os.listdir(ENV)):
            before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=ENV + f)
            for o in set(bpy.data.objects) - before:
                for c in o.users_collection: c.objects.unlink(o)
                lib_c.objects.link(o)
    lc = bpy.context.view_layer.layer_collection.children.get('env_lib')
    if lc: lc.exclude = True
    return {o.name: o for o in lib_c.objects if o.type == 'MESH' and not o.name.endswith('_LOD1')}

TEXMAP = {'plaster': ('clay_plaster', 1.25), 'plaster_light': ('clay_plaster', 1.45), 'lime': ('clay_plaster', 2.2), 'mud': ('brown_mud_02', 1.3),
          'clay': ('clay_plaster', 1.2), 'wood': ('old_planks_02', 1.4), 'wood_dark': ('old_planks_02', 0.9), 'stone': ('large_sandstone_blocks', 1.3),
          'bark': ('palm_bark', 1.5)}
def upgrade_materials(objs):
    done = set()
    for o in objs:
        for m in o.data.materials:
            if not m or m.name in done or m.get('pbr'): continue
            base = m.name.split('.')[0]
            if base not in TEXMAP: continue
            done.add(m.name); tset, gain = TEXMAP[base]
            nt = m.node_tree; bs = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
            rgb = tuple(bs.inputs['Base Color'].default_value)[:3]
            for l in list(bs.inputs['Base Color'].links): nt.links.remove(l)
            uv = nt.nodes.new('ShaderNodeUVMap')
            c, n, r = pbr_nodes(nt, tset, uv.outputs['UV'], -900, 300)
            mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1
            nt.links.new(c, mul.inputs[6]); mul.inputs[7].default_value = (*[min(1, v * gain) for v in rgb], 1)
            nt.links.new(mul.outputs[2], bs.inputs['Base Color'])
            nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(n, nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
            nt.links.new(r, bs.inputs['Roughness']); m['pbr'] = True

def put(src, name, x, y, rot=0.0, s=1.0, col=None, z=None):
    o = bpy.data.objects.new(name, src.data); col.objects.link(o)
    o.location = (x, y, height(x, y) - 0.04 if z is None else z); o.rotation_euler = (0, 0, rot); o.scale = (s, s, s)
    return o

def mastaba(col):
    """مصطبة: plastered mud-brick bench along grandma's front wall (model space matches village.js)."""
    h, depth, ln, x0, wall = 0.45, 0.6, 2.5, 0.05, 2.4
    M = Matrix.Translation((HOME.x, HOME.y, height(HOME.x, HOME.y) - 0.04)) @ Matrix.Rotation(HOME_ROT, 4, 'Z')
    b = box('mastaba', (ln, depth, h), (0, 0, 0), 'plaster', col, bevel=0.04, segments=3)
    apply_all(b); lumpy(b, 0.012, 0.6, 0)
    b.matrix_world = M @ Matrix.Translation((x0 + ln / 2, -(wall + depth / 2), h / 2))
    # a woven kilim and a cushion on top
    MAT_COLORS.update({'cloth_kilim': (0.5, 0.12, 0.08), 'cloth_cushion': (0.18, 0.28, 0.45)})
    k = box('kilim', (ln - 0.3, depth - 0.1, 0.02), (0, 0, 0), 'cloth_kilim', col, bevel=0.005); apply_all(k)
    k.matrix_world = M @ Matrix.Translation((x0 + ln / 2, -(wall + depth / 2), h + 0.01))
    c = box('cushion', (0.55, 0.16, 0.4), (0, 0, 0), 'cloth_cushion', col, bevel=0.06, segments=4); apply_all(c)
    c.matrix_world = M @ Matrix.Translation((x0 + 0.5, -(wall + 0.1), h + 0.2)) @ Matrix.Rotation(-0.15, 4, 'X')
    for o in (b, k, c): uv_world(o, 0.5)
    return b

def sky_and_sun():
    sc = bpy.context.scene
    w = sc.world or bpy.data.worlds.new('World'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld'); bg = nt.nodes.new('ShaderNodeBackground'); env = nt.nodes.new('ShaderNodeTexEnvironment')
    env.image = img(PUB + 'hdri/sky_2k.hdr', False); env.image.colorspace_settings.name = 'Linear Rec.709' if 'Linear Rec.709' in [i.name for i in bpy.types.ColorManagedInputColorspaceSettings.bl_rna.properties['name'].enum_items] else env.image.colorspace_settings.name
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, math.radians(200))
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
    nt.links.new(env.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 0.9; nt.links.new(bg.outputs[0], out.inputs[0])
    sun = bpy.data.objects.get('Sun')
    if not sun:
        sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); sc.collection.objects.link(sun)
    sun.data.energy = 4.2; sun.data.color = (1.0, 0.86, 0.68); sun.data.angle = math.radians(1.2)
    to_sun = Vector((0.8, -0.35, 0.42)).normalized()                  # morning sun from the east: lights the house fronts
    sun.rotation_euler = (-to_sun).to_track_quat('-Z', 'Y').to_euler()
    for n in ('Light', 'Cube'):
        if n in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    ee = sc.eevee
    for attr, v in (('use_raytracing', True), ('use_shadows', True), ('shadow_ray_count', 2), ('use_fast_gi', True), ('taa_render_samples', 64)):
        try: setattr(ee, attr, v)
        except Exception: pass
    sc.view_settings.view_transform = 'AgX'
    try: sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception: pass
    sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'

def place():
    L = load_lib(); col = clear_collection('village_props')
    upgrade_materials(L.values())
    rnd = random.Random(4)
    put(L['house_a'], 'grandma_house', HOME.x, HOME.y, HOME_ROT, col=col)
    put(L['house_b'], 'house_north', -11.2, -13.5, HOME_ROT, col=col)
    h = put(L['house_a'], 'house_south', -10.0, -38.5, HOME_ROT, col=col); h.scale.x = -1
    mastaba(col)
    for i, (x, y, r) in enumerate([(-6.75, -27.9, 0.2), (-6.55, -28.5, 1.1)]):
        put(L['jar' if i == 0 else 'jar_b'], f'jar{i}', x, y, r, col=col)
    put(L['basket'], 'basket', -6.3, -23.0, 0.4, col=col)
    put(L['hay'], 'hay', -5.5, -33.5, 0.3, col=col, z=height(-5.5, -33.5) + 0.5)
    put(L['pot_plant'], 'pot', -6.9, -22.9, 0, col=col)
    put(L['shaduf'], 'shaduf', canal_x(-31) + 2.6, -31, math.pi, col=col)
    put(L['footbridge'], 'footbridge', canal_x(-19), -19, math.pi / 2, col=col, z=0.12)
    put(L['garden_wall'], 'wall1', -8.6, -31.5, 0, col=col)
    put(L['well'], 'well', -3.4, -41, 0, col=col)
    palms = [(-12.7, -21.5), (-12.9, -30.5), (-17.9, -24), (-18.4, -34), (-17.6, -12), (-12.4, -45), (-3.6, -19.8), (-18.0, -48), (-24, -30), (-26, -18), (5.5, -40), (-13.5, -8)]
    for i, (x, y) in enumerate(palms):
        put(L[rnd.choice(['palm_a', 'palm_b', 'palm_c'])], f'palm{i}', x, y, rnd.uniform(0, 6.28), rnd.uniform(0.85, 1.15), col=col)
    return col

CAST = {'grandma': ((-6.75, -24.7), math.pi / 2, 'grandma_rig_sit'),
        'farmer':  ((-6.0, -26.2), 1.92, 'farmer_rig_idle'),
        'player':  ((-4.1, -25.05), None, 'player_rig_idle')}
def cast():
    for k, ((x, y), rot, act) in CAST.items():
        r = bpy.data.objects.get(k + '_rig')
        if not r: continue
        if rot is None:                                          # the boy faces the elders
            d = Vector((-6.4, -25.4)) - Vector((x, y)); rot = math.atan2(d.y, d.x) + math.pi / 2
        r.location = (x, y, height(x, y) - 0.04); r.rotation_euler = (0, 0, rot)
        r.animation_data.action = bpy.data.actions.get(act)

if __name__ != 'env_place':
    place(); sky_and_sun(); cast()
    print('placed')
