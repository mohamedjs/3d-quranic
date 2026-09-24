import sys, importlib; sys.path.insert(0, '/var/www/html/old/3d-quranic/blender/v2/env')
for m in ('tk', 'houses', 'palms', 'crops', 'props', 'water'):
    if m in sys.modules: importlib.reload(sys.modules[m])
import tk, houses, palms, crops, props, water, math, random
from tk import *
reset(); look()
col = collection('style')
asset('house_a', houses.house_a(), col, t=0.025, lod_ratio=0.35)
asset('mastaba', props.mastaba(), col, t=0.015)
asset('palm_a', palms.build_palm('palm_a'), col, t=0.02, lod_ratio=0.35, loc=(-5.6, 0.8, 0))
asset('jar', props.jar(), col, t=0.012, loc=(-1.55, -2.75, 0))
asset('jar_b', props.jar_b(), col, t=0.012, loc=(-2.1, -2.7, 0))
asset('basket', props.basket(), col, t=0.012, loc=(2.95, -2.75, 0))
ber = asset('crop_berseem', crops.berseem(), col, t=0.012, loc=(0, 0, -50))
# ground: village dirt + a berseem field patch + a canal along Y at x = -9
g = B(1)
g.box((21.8, 30, 1), (3.6, 0, -0.5), 'toon_ground', smooth=False)
g.box((8.7, 30, 1), (-15.65, 0, -0.5), 'toon_ground_green', smooth=False)
g.box((7, 6, 0.1), (7.5, -6.5, 0.0), 'toon_earth', smooth=False)
g.box((4, 30, 0.2), (-9.5, 0, -1.5), 'toon_mud', smooth=False)
gro = g.obj('ground', col)
for s, x in ((1, -11.0), (-1, -7.6)):
    for k in range(7):
        y = -12 + k * 4
        o = water.canal_bank().obj(f'bank{s}{k}', col); o.location = (x, y, 0.0); o.rotation_euler.z = 0 if s > 0 else math.pi
        o.location.z = 0.0 if s > 0 else 0.0
        outline(o, 0.015)
water.water_strip('canal_water', [(-9.3, -14 + i * 2, 0) for i in range(15)], 2.9, col, z=-0.5)
# berseem clumps on the patch
src = bpy.data.objects['crop_berseem']; srco = bpy.data.objects['crop_berseem_outline']
rnd = random.Random(3)
for i in range(12):
    for j in range(10):
        x, y = 4.4 + i * 0.52 + rnd.uniform(-0.12, 0.12), -9.2 + j * 0.55 + rnd.uniform(-0.12, 0.12)
        for s_ in (src, srco):
            d = s_.copy(); col.objects.link(d); d.location = (x, y, 0.03); d.rotation_euler.z = rnd.uniform(0, 6.3)
            sc = rnd.uniform(0.85, 1.2); d.scale = (sc, sc, sc)
b2 = water.footbridge().obj('fb', col); b2.location = (-9.3, 3, 0.0); outline(b2, 0.012).location = b2.location
cam = camera('ShotCam', (6.5, -16, 3.0), (-3.2, -1.5, 1.8), lens=28)
render(PREV + 'env_style.png', cam)
cam2 = camera('CanalCam', (-4.5, -9.5, 2.2), (-9.5, 1.0, -0.4), lens=30)
render(PREV + 'env_style_canal.png', cam2)
save_report('style')
bpy.ops.wm.save_as_mainfile(filepath=V2 + 'env/_style.blend')
