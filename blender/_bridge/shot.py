# usage: set LOC, DIST, ROT (pitch,0,yaw deg), SHADING, OUT then exec this
import bpy, mathutils, math
for w in bpy.context.window_manager.windows:
    for a in w.screen.areas:
        if a.type != 'VIEW_3D': continue
        sp = a.spaces.active; sp.shading.type = SHADING; sp.overlay.show_overlays = False
        sp.shading.use_scene_lights = True; sp.shading.use_scene_world = SHADING == 'RENDERED'
        r3 = sp.region_3d; r3.view_perspective = 'PERSP'; sp.lens = LENS if 'LENS' in globals() else 50
        r3.view_location = LOC; r3.view_distance = DIST
        r3.view_rotation = mathutils.Euler([math.radians(v) for v in ROT]).to_quaternion()
bpy.context.view_layer.update()
import time
def _later():
    viewport_shot(OUT); return None
