# EYE, TARGET, LENS, SHADING, then viewport looks through camera 'ShotCam'
import bpy, mathutils
sc = bpy.context.scene
cam = bpy.data.objects.get('ShotCam')
if not cam:
    cam = bpy.data.objects.new('ShotCam', bpy.data.cameras.new('ShotCam')); sc.collection.objects.link(cam)
cam.location = EYE; cam.data.lens = LENS if 'LENS' in globals() else 35
cam.rotation_euler = (mathutils.Vector(TARGET) - mathutils.Vector(EYE)).to_track_quat('-Z', 'Y').to_euler()
sc.camera = cam
for w in bpy.context.window_manager.windows:
    for a in w.screen.areas:
        if a.type != 'VIEW_3D': continue
        sp = a.spaces.active; sp.shading.type = SHADING; sp.overlay.show_overlays = False
        sp.region_3d.view_perspective = 'CAMERA'
        try: sp.region_3d.view_camera_zoom = 0; sp.region_3d.view_camera_offset = (0, 0)
        except Exception: pass
