# Point the viewport at a spot: set LOC=(x,y,z), DIST, ROT=(pitch, 0, yaw) before running.
import bpy, mathutils
for w in bpy.context.window_manager.windows:
    for a in w.screen.areas:
        if a.type != 'VIEW_3D': continue
        sp = a.spaces.active; sp.shading.type = SHADING if 'SHADING' in globals() else 'MATERIAL'; sp.overlay.show_overlays = False
        r3 = sp.region_3d; r3.view_perspective = 'PERSP'
        r3.view_location = LOC; r3.view_distance = DIST
        r3.view_rotation = mathutils.Euler(ROT).to_quaternion()
print('ok')
