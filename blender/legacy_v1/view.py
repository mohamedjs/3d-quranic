# Frame the given collections in the 3D viewport with material colours (for screenshots).
import bpy, sys
NAMES = globals().get('FRAME', None)
for w in bpy.context.window_manager.windows:
    for a in w.screen.areas:
        if a.type != 'VIEW_3D': continue
        sp = a.spaces.active
        sp.shading.type = 'SOLID'; sp.shading.color_type = 'MATERIAL'; sp.shading.light = 'STUDIO'
        sp.shading.show_shadows = True; sp.shading.show_cavity = True; sp.overlay.show_overlays = False
        r = next(r for r in a.regions if r.type == 'WINDOW')
        for o in bpy.context.view_layer.objects: o.select_set(bool(NAMES) and any(o.name.startswith(n) for n in NAMES))
        with bpy.context.temp_override(window=w, area=a, region=r):
            if NAMES: bpy.ops.view3d.view_selected()
            else: bpy.ops.view3d.view_all()
            sp.region_3d.view_rotation = __import__('mathutils').Euler((1.15, 0, -0.55)).to_quaternion()
            if NAMES: bpy.ops.view3d.view_selected()
        for o in bpy.context.view_layer.objects: o.select_set(False)
print('framed')
