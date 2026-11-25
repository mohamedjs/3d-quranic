"""Headless Blender EEVEE contact-sheet renderer for Environment v3 (`preview.py`).

Usage:
  blender -b --python blender/v3/env/preview.py -- foliage

Renders `blender/v3/previews/foliage_sheet.png` showing all M3 hero trees, shrubs,
water plants, crops, and grass side-by-side under golden-hour Nile sun with the real
painted `public/textures/env/1024/foliage_albedo.webp` & `foliage_normal.webp` maps.
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import crops
import foliage
import lib


def bind_foliage_preview_mats():
    """Wire the baked 1024px WebP foliage albedo + normal + alpha clip into Blender preview mats."""
    alb_path = lib.OUT_TEX / '1024' / 'foliage_albedo.webp'
    nrm_path = lib.OUT_TEX / '1024' / 'foliage_normal.webp'
    alb_img = bpy.data.images.load(str(alb_path), check_existing=True)
    nrm_img = bpy.data.images.load(str(nrm_path), check_existing=True)
    nrm_img.colorspace_settings.name = 'Non-Color'

    atlas_mats = {'foliage_frond', 'foliage_leaf', 'foliage_shrub', 'foliage_bark', 'foliage_crop_card'}
    cutout_mats = {'foliage_frond', 'foliage_leaf', 'foliage_shrub', 'foliage_crop_card'}

    for mat in bpy.data.materials:
        if mat.name not in atlas_mats:
            continue
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        pbr = nt.nodes.new('ShaderNodeBsdfPrincipled')
        pbr.inputs['Roughness'].default_value = 0.85
        if 'Specular IOR Level' in pbr.inputs:
            pbr.inputs['Specular IOR Level'].default_value = 0.15

        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = alb_img
        vc = nt.nodes.new('ShaderNodeVertexColor')
        vc.layer_name = 'Color'
        mul = nt.nodes.new('ShaderNodeMix')
        mul.data_type = 'RGBA'
        mul.blend_type = 'MULTIPLY'
        mul.inputs['Factor'].default_value = 1.0
        nt.links.new(tex.outputs['Color'], mul.inputs[6])
        nt.links.new(vc.outputs['Color'], mul.inputs[7])
        nt.links.new(mul.outputs[2], pbr.inputs['Base Color'])

        ntex = nt.nodes.new('ShaderNodeTexImage')
        ntex.image = nrm_img
        nmap = nt.nodes.new('ShaderNodeNormalMap')
        nmap.inputs['Strength'].default_value = 0.75
        nt.links.new(ntex.outputs['Color'], nmap.inputs['Color'])
        nt.links.new(nmap.outputs['Normal'], pbr.inputs['Normal'])

        if mat.name in cutout_mats:
            # Threshold alpha cleanly for crisp cutout silhouette in EEVEE
            gt = nt.nodes.new('ShaderNodeMath')
            gt.operation = 'GREATER_THAN'
            gt.inputs[1].default_value = 0.42
            nt.links.new(tex.outputs['Alpha'], gt.inputs[0])
            nt.links.new(gt.outputs['Value'], pbr.inputs['Alpha'])
            if hasattr(mat, 'surface_render_method'):
                mat.surface_render_method = 'DITHERED'

        nt.links.new(pbr.outputs['BSDF'], out.inputs['Surface'])


def setup_studio(cam_loc, look_at, lens=42):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = 1600
    sc.render.resolution_y = 900
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'AgX'
    if hasattr(sc.eevee, 'taa_render_samples'):
        sc.eevee.taa_render_samples = 16

    # Warm golden-hour sky & cool fill world
    world = bpy.data.worlds.new('studio')
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs['Color'].default_value = (0.48, 0.56, 0.72, 1.0)
        bg.inputs['Strength'].default_value = 0.65

    # Warm sunlit sand/meadow ground sweep
    bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 0, 0))
    ground = bpy.context.active_object
    gmat = lib.make_material('studio_ground', base_color=(0.38, 0.44, 0.22), roughness=0.95, use_vcol=False)
    ground.data.materials.append(gmat)

    # Honey-gold sun key (~20° elevation)
    sun_d = bpy.data.lights.new('Sun', 'SUN')
    sun_d.energy = 4.2
    sun_d.color = (1.0, 0.84, 0.56)
    sun = bpy.data.objects.new('Sun', sun_d)
    sun.rotation_euler = (math.radians(68), math.radians(12), math.radians(-38))
    sc.collection.objects.link(sun)

    cam_d = bpy.data.cameras.new('Cam')
    cam_d.lens = lens
    cam = bpy.data.objects.new('Cam', cam_d)
    cam.location = Vector(cam_loc)
    direction = Vector(look_at) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    sc.collection.objects.link(cam)
    sc.camera = cam


def render_foliage_sheet():
    lib.reset_scene()
    lib.ensure_dirs()
    col = lib.make_collection('foliage_sheet')

    # Back row: tall hero trees (4 date palms, 2 sycamores, umbrella acacia)
    back = [
        ('palm_a',     (-15.5, 4.5, 0)),
        ('palm_b',     (-10.5, 4.8, 0)),
        ('palm_c',     ( -5.5, 4.2, 0)),
        ('palm_d',     ( -0.8, 4.6, 0)),
        ('sycamore_a', (  5.2, 4.8, 0)),
        ('sycamore_b', ( 11.8, 5.2, 0)),
        ('acacia',     ( 18.2, 4.5, 0)),
    ]
    # Mid row: shrubs, bougainvillea, papyrus, reeds, pot plant, lotus pad
    mid = [
        ('bougainvillea_bush', (-11.0, -2.5, 0)),
        ('bougainvillea_vine', ( -7.8, -2.5, 0)),
        ('bush_a',             ( -4.8, -2.5, 0)),
        ('bush_b',             ( -2.2, -2.5, 0)),
        ('papyrus',            (  0.6, -2.5, 0)),
        ('reeds',              (  3.2, -2.5, 0)),
        ('pot_plant',          (  5.6, -2.5, 0)),
        ('lotus_pad',          (  8.0, -2.5, 0)),
        ('field_bund',         ( 12.2, -2.5, 0)),
    ]
    # Front row: 5 crops + 3 grasses + wildflowers (scaled 2.2x so tiny ground plants inspect clearly!)
    front = [
        ('crop_maize',   (-9.0, -6.4, 0), 1.3),
        ('crop_wheat',   (-6.6, -6.4, 0), 1.8),
        ('crop_cotton',  (-4.2, -6.4, 0), 2.1),
        ('crop_berseem', (-1.8, -6.4, 0), 2.2),
        ('crop_cabbage', ( 0.4, -6.4, 0), 2.5),
        ('wildflowers',  ( 2.8, -6.4, 0), 2.3),
        ('grass_a',      ( 5.0, -6.4, 0), 2.4),
        ('grass_b',      ( 7.0, -6.4, 0), 2.1),
        ('grass_c',      ( 9.0, -6.4, 0), 2.4),
    ]

    all_builders = {**foliage.FOLIAGE_BUILDERS, **crops.CROP_BUILDERS}
    for name, loc in back + mid:
        for o in all_builders[name](col):
            if '_LOD1' in o.name:
                bpy.data.objects.remove(o, do_unlink=True)
            else:
                o.location = Vector(loc)
    for name, loc, sc in front:
        for o in all_builders[name](col):
            if '_LOD1' in o.name:
                bpy.data.objects.remove(o, do_unlink=True)
            else:
                o.location = Vector(loc)
                o.scale = Vector((sc, sc, sc))

    bind_foliage_preview_mats()
    setup_studio(cam_loc=(1.5, -29.5, 8.8), look_at=(1.2, 0.5, 3.0), lens=31)
    out = lib.PREVIEWS / 'foliage_sheet.png'
    bpy.context.scene.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    print('RENDERED_SHEET', out)


if __name__ == '__main__':
    render_foliage_sheet()
