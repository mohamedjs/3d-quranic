import bpy, sys
print('VER', bpy.app.version_string)
print('ENGINES', [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items])
m = bpy.data.materials.new('x'); print('rm', [e.identifier for e in m.bl_rna.properties['surface_render_method'].enum_items])
import inspect
op = bpy.ops.export_scene.gltf.get_rna_type()
print('GLTF', [p.identifier for p in op.properties if 'draco' in p.identifier or 'apply' in p.identifier or 'image' in p.identifier])
