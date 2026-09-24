# Characters built with MPFB (MakeHuman for Blender): realistic body + game skeleton.
# Clothing, hair and animations are added by later steps in this file.
import sys, importlib, math
sys.path.insert(0, '/var/www/html/old/3d-quranic/blender')
import lib; importlib.reload(lib)
from lib import *
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService

# MakeHuman age: 0 → 1 yr, 0.1875 → 11 yrs, 0.5 → 25 yrs, 1 → 90 yrs
def age(years):
    return years / 11 * 0.1875 if years <= 11 else (0.1875 + (years - 11) / 14 * 0.3125 if years <= 25 else 0.5 + (years - 25) / 65 * 0.5)

LEVANT = {'asian': 0.12, 'caucasian': 0.6, 'african': 0.28}
PEOPLE = {
    'player':  dict(gender=1.0, age=age(9),  muscle=0.5,  weight=0.45, height=0.5, proportions=0.6, race=LEVANT),
    'farmer':  dict(gender=1.0, age=age(68), muscle=0.45, weight=0.45, height=0.55, proportions=0.5, race={'asian': 0.1, 'caucasian': 0.55, 'african': 0.35}),
    'trader':  dict(gender=1.0, age=age(45), muscle=0.55, weight=0.55, height=0.6, proportions=0.55, race=LEVANT),
    'grandma': dict(gender=0.0, age=age(70), muscle=0.35, weight=0.6,  height=0.38, proportions=0.5, cupsize=0.15, firmness=0.2, race={'asian': 0.1, 'caucasian': 0.55, 'african': 0.35}),
}

DATA = '/home/mohamed/.config/blender/5.2/extensions/.user/user_default/mpfb/data/'
LOOKS = {   # skin (MakeHuman CC0), hair (None: covered by turban/keffiyeh/hijab), eyebrows
    'player':  dict(skin='young_caucasian_male', hair=None, brows='eyebrow001'),   # stylized hair: stylize.py
    'farmer':  dict(skin='old_caucasian_male', hair=None, brows='eyebrow007'),
    'trader':  dict(skin='middleage_caucasian_male', hair=None, brows='eyebrow003'),
    'grandma': dict(skin='old_caucasian_female', hair=None, brows='eyebrow010'),
}

def dress_body(key, body):
    look = LOOKS[key]
    HumanService.set_character_skin(DATA + f"skins/{look['skin']}/{look['skin']}.mhmat", body, skin_type='GAMEENGINE', material_instances=False)
    eyes = HumanService.add_mhclo_asset(DATA + 'eyes/low-poly/low-poly.mhclo', body, asset_type='Eyes', subdiv_levels=0, material_type='MAKESKIN')
    for m in eyes.data.materials:                             # brown eyes
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE': n.image = bpy.data.images.load(DATA + 'eyes/materials/brown_eye.png', check_existing=True)
    HumanService.add_mhclo_asset(DATA + f"eyebrows/{look['brows']}/{look['brows']}.mhclo", body, asset_type='Eyebrows', subdiv_levels=0)
    HumanService.add_mhclo_asset(DATA + 'eyelashes/eyelashes01/eyelashes01.mhclo', body, asset_type='Eyelashes', subdiv_levels=0)
    if look['hair']:
        HumanService.add_mhclo_asset(DATA + f"hair/{look['hair']}/{look['hair']}.mhclo", body, asset_type='Hair', subdiv_levels=0)

TARGETS = '/home/mohamed/.config/blender/5.2/extensions/user_default/mpfb/data/targets/'
FACE = {   # animated-film face shaping (MakeHuman targets): big expressive eyes, soft round cheeks
    'player': {'eyes/l-eye-scale-incr': 1.0, 'eyes/r-eye-scale-incr': 1.0, 'nose/nose-scale-horiz-decr': 0.45, 'nose/nose-scale-vert-decr': 0.35,
               'cheek/l-cheek-volume-incr': 0.7, 'cheek/r-cheek-volume-incr': 0.7, 'head/head-fat-incr': 0.45},
    'farmer': {'eyes/l-eye-scale-incr': 0.45, 'eyes/r-eye-scale-incr': 0.45, 'cheek/l-cheek-volume-incr': 0.4, 'cheek/r-cheek-volume-incr': 0.4,
               'nose/nose-scale-depth-incr': 0.3},
}

def build(key, x):
    col = clear_collection('char_' + key)
    macro = TargetService.get_default_macro_info_dict()
    p = PEOPLE[key]; macro.update({k: v for k, v in p.items() if k != 'race' and k in macro}); macro['race'] = p['race']
    body = HumanService.create_human(mask_helpers=True, detailed_helpers=True, extra_vertex_groups=True, feet_on_ground=True, scale=0.1, macro_detail_dict=macro)
    body.name = key + '_body'
    for t, w in FACE.get(key, {}).items():
        TargetService.load_target(body, TARGETS + t + '.target.gz', weight=w)
    rig = HumanService.add_builtin_rig(body, 'game_engine', import_weights=True)
    rig.name = key + '_rig'
    dress_body(key, body)
    for o in [rig] + list(rig.children_recursive): link(o, col)
    rig.location.x = x
    dims = body.dimensions
    return body, rig, (round(dims.x, 2), round(dims.y, 2), round(dims.z, 2))

if __name__ != 'characters':
    KEYS = globals().get('KEYS') or list(PEOPLE)
    out = []
    for i, k in enumerate(PEOPLE):
        if k not in KEYS: continue
        b, r, d = build(k, -20 - i * 1.2)
        out.append((k, d, len(r.data.bones)))
    print(out)
