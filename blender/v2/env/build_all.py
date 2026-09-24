# Entry point (rerunnable):  python3 blender/v2/bg.py blender/v2/env/build_all.py env_build
# Builds every environment asset, exports public/models/env/<name>.glb (Draco, toon_* + outline),
# saves blender/v2/env/env.blend (showcase grid) and renders previews/env_assets.png.
import sys, importlib; sys.path.insert(0, '/var/www/html/old/3d-quranic/blender/v2/env')
for m in ('tk', 'houses', 'palms', 'crops', 'props', 'water'):
    if m in sys.modules: importlib.reload(sys.modules[m])
import tk, houses, palms, crops, props, water, math, json
from tk import *

reset(); look()
# (name, builder, outline thickness, lod ratio, showcase row)
SPEC = [
    ('house_a', houses.house_a, 0.025, 0.35, 0), ('house_b', houses.house_b, 0.025, 0.35, 0), ('house_c', houses.house_c, 0.025, 0.35, 0),
    ('mastaba', props.mastaba, 0.014, None, 0),
    ('palm_a', lambda: palms.build_palm('palm_a'), 0.02, 0.35, 1), ('palm_b', lambda: palms.build_palm('palm_b'), 0.02, 0.35, 1),
    ('palm_c', lambda: palms.build_palm('palm_c'), 0.02, 0.35, 1), ('sycamore', palms.sycamore, 0.025, 0.35, 1),
    ('bougainvillea', palms.bougainvillea, 0.012, None, 1),
    ('well', props.well, 0.014, 0.5, 2), ('shaduf', water.shaduf, 0.014, None, 2), ('sluice', water.sluice, 0.014, None, 2),
    ('footbridge', water.footbridge, 0.012, None, 2), ('stall', props.stall, 0.014, 0.5, 2), ('garden_wall', props.garden_wall, 0.016, 0.5, 2),
    ('fence', props.fence, 0.01, None, 2), ('hay', props.hay, 0.014, None, 2),
    ('jar', props.jar, 0.012, None, 3), ('jar_b', props.jar_b, 0.012, None, 3), ('basket', props.basket, 0.012, None, 3),
    ('hoe', props.hoe, 0.01, None, 3), ('pot_plant', props.pot_plant, 0.012, None, 3),
    ('stream', water.stream, 0.012, None, 3), ('canal_bank', water.canal_bank, 0.014, None, 3), ('canal_stones', water.canal_stones, 0.012, None, 3),
] + [(k, f, 0.008, None, 4) for k, f in crops.PLANTS.items()]

DEC = dict(house_a=0.6, house_b=0.55, house_c=0.6, sycamore=0.6, stall=0.6)
MINSIZE = dict(house_a=0.16, house_b=0.2, house_c=0.16, stall=0.12, crop_cotton=0.12, stream=0.0, well=0.1, basket=0.1, palm_a=0.0, sycamore=0.0)
WIDTH = {0: 9.0, 1: 7.0, 2: 5.0, 3: 2.2, 4: 1.6}
cursor = {}
root = collection('env_assets')
for name, fn, t, lr, row in SPEC:
    x = cursor.get(row, 0.0); cursor[row] = x + WIDTH[row]
    col = collection(name, root)
    b = fn()
    extra = []
    if name == 'stream':   # UV'd toon water surface as a second mesh in the same GLB
        extra.append(water.water_strip('stream_water', [(0, -2 + i * 0.5, 0) for i in range(9)], 0.86, col, z=-0.06))
    o = b.obj(name, col)
    ms = MINSIZE.get(name, 0.0)
    objs = [o, outline(o, t, min_size=ms, decimate=DEC.get(name))]
    if lr:
        lo = lod(o, lr, name + '_LOD1'); objs += [lo, outline(lo, t * 1.3, min_size=ms * 1.5)]
    for h in [x_ for x_ in objs if x_.name.endswith('_outline') and not x_.data.polygons]:   # blade plants: no hull
        objs.remove(h); bpy.data.objects.remove(h)
    objs += extra
    kb = export(objs, OUT + name + '.glb') / 1024
    hl = bpy.data.objects.get(name + '_outline'); lo_ = bpy.data.objects.get(name + '_LOD1')
    info = dict(name=name, tris=tris(o), tris_outline=tris(hl) if hl else 0, tris_lod1=tris(lo_) if lr else 0, kb=round(kb, 1),
                mats=sorted({m.name for x in objs for m in x.data.materials}))
    REPORT.append(info); print('ASSET', json.dumps(info), flush=True)
    for x_ in objs:
        x_.location = (x, -row * 20.0, 0)
        if '_LOD1' in x_.name: x_.hide_render = True; x_.hide_set(True); x_.location.y += 6
json.dump(REPORT, open(V2 + 'env/_report_build.json', 'w'), indent=1)
# material manifest for the game port
mats = sorted({m for r in REPORT for m in r['mats']})
man = {m: dict(color=PAL[m][0] if m in PAL else (INK if m == 'outline' else None), flags=PAL.get(m, ('', ''))[1]) for m in mats}
man['_water'] = water.WATER; man['_shadow_tint'] = SHADOW_TINT; man['_ink'] = INK
json.dump(man, open(V2 + 'env/toon_materials.json', 'w'), indent=1)
render(PREV + 'env_houses.png', camera('ShowHouses', (15, -17, 7), (13.5, 0, 1.8), lens=30))
render(PREV + 'env_trees.png', camera('ShowTrees', (15, -44, 4), (15, -20, 4.2), lens=30))
render(PREV + 'env_props.png', camera('ShowProps', (19, -54, 4.5), (19, -40, 0.8), lens=30))
render(PREV + 'env_small.png', camera('ShowSmall', (9, -68.5, 2.4), (9, -60, 0.2), lens=30))
render(PREV + 'env_plants.png', camera('ShowPlants', (8, -91, 3.0), (8, -80, 0.2), lens=26))
bpy.ops.wm.save_as_mainfile(filepath=V2 + 'env/env.blend')
print('BUILD_OK', len(REPORT))

# then assemble the preview village (village_v2.blend + village_*.png) from the fresh env.blend
if '--assets-only' not in sys.argv:
    import runpy; runpy.run_path('/var/www/html/old/3d-quranic/blender/v2/env/village.py', run_name='__main__')
