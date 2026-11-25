"""Cast definitions (proportions, palette, face specs, outfits, clips) and character assembly."""
import bpy

import lib as L
import rig as R
import body as B
import head as HD
import garments as G
import anim as A

ORDER = ['player', 'farmer', 'grandma_zainab', 'grandma', 'trader', 'sheikh', 'aunt']

# Outline thicknesses per §5.5 (~0.003 m on face/hands, ~0.005 m on clothes/hair)
OUTLINE_SKIN = 0.0028
OUTLINE_CLOTH = 0.0046

CAST = {
    'player': dict(
        label='Explorer Boy',
        props=dict(
            height=1.25, head_ratio=4.2, neck_frac=0.20, neck_ratio=0.35,
            hip_frac=0.44, ankle_frac=0.056, shoulder_w=0.128, hip_w=0.070,
            chest_d=0.072, belly_d=0.076, pelvis_d=0.076,
            waist_ratio=0.78, chest_ratio=0.92, hip_full=1.02, belly_full=1.06, chest_full=0.98, belly_fwd=0.7,
            arm_thick=0.95, hand_scale=1.00, leg_thick=0.98, foot_len=0.122, foot_w=1.04,
        ),
        skin='#CC8E64',
        face=dict(
            skin='#CC8E64', skull_w=0.98, skull_d=1.00, crown_h=1.02, jaw_taper=0.16, chin_drop=0.13,
            cheek_full=0.14, eye_z=-0.06, eye_x=0.35, eye_w=0.225, eye_h=0.235, eye_tilt=0.03,
            iris_r=0.58, iris_hi='#2A1308', iris_lo='#B87336', iris_glow='#F0B85A',
            nose_z=-0.35, nose_len=0.155, nose_w=0.13, nose_lift=0.032,
            mouth_z=-0.61, mouth_w=0.20, smile=0.068, lip_col='#C46F5A', lip_alpha=0.28,
            blush=0.34, blush_col='#E47D69', lash_thick=0.034, lashes=False,
            brow_col='#4B2D1A', brow_thick=0.044, brow_gap=0.08, brow_arch=0.055, brow_tilt=-0.02,
            ears=True, ear_scale=1.06,
        ),
        clips=['idle', 'walk', 'run', 'talk'],
        style=dict(energy=1.25, arm_out=0.24, elbow=28.0, robe=False),
    ),
    'farmer': dict(
        label='Grandpa Salim',
        props=dict(
            height=1.74, head_ratio=5.6, neck_frac=0.23, neck_ratio=0.40,
            hip_frac=0.46, ankle_frac=0.050, shoulder_w=0.138, hip_w=0.072,
            chest_d=0.076, belly_d=0.086, pelvis_d=0.080,
            waist_ratio=0.86, chest_ratio=0.95, hip_full=1.06, belly_full=1.18, chest_full=1.05, belly_fwd=1.0,
            arm_thick=1.10, hand_scale=1.06, leg_thick=1.04, foot_len=0.114, foot_w=1.04,
        ),
        skin='#B97B53',
        face=dict(
            skin='#B97B53', skull_w=0.96, skull_d=1.02, crown_h=1.00, jaw_taper=0.18, chin_drop=0.17,
            cheek_full=0.10, eye_z=-0.05, eye_x=0.34, eye_w=0.195, eye_h=0.185, eye_tilt=-0.06,
            iris_r=0.52, iris_hi='#241108', iris_lo='#8B572D', iris_glow='#D89A4E',
            nose_z=-0.34, nose_len=0.215, nose_w=0.165, nose_lift=-0.01,
            mouth_z=-0.61, mouth_w=0.21, smile=0.062, lip_col='#A45D49', lip_alpha=0.24,
            blush=0.18, blush_col='#D2725C', age_lines=True, age_col='#8B523B',
            lash_thick=0.030, lashes=False,
            brow_col='#F0EBE0', brow_thick=0.058, brow_gap=0.06, brow_arch=0.060, brow_tilt=0.12,
            ears=True, ear_scale=1.02,
        ),
        clips=['idle', 'walk', 'talk'],
        style=dict(energy=0.82, stoop=6.5, staff=True, robe=True, arm_out=0.24),
    ),
    'grandma_zainab': dict(
        label='Grandma Zainab',
        props=dict(
            height=1.58, head_ratio=5.4, neck_frac=0.20, neck_ratio=0.36,
            hip_frac=0.535, knee_frac=0.525, ankle_frac=0.050, shoulder_w=0.126, hip_w=0.076,
            chest_d=0.078, belly_d=0.086, pelvis_d=0.084,
            waist_ratio=0.86, chest_ratio=0.94, hip_full=1.14, belly_full=1.14, chest_full=1.08, belly_fwd=0.80,
            upperarm_frac=0.72, lowerarm_frac=0.63,
            arm_thick=1.02, hand_scale=0.96, leg_thick=1.02, foot_len=0.108, foot_w=1.00,
        ),
        skin='#CB946F',
        face=dict(
            skin='#CB946F', skull_w=0.98, skull_d=1.00, crown_h=1.00, jaw_taper=0.15, chin_drop=0.13,
            cheek_full=0.15, eye_z=-0.06, eye_x=0.34, eye_w=0.205, eye_h=0.200, eye_tilt=-0.04,
            iris_r=0.54, iris_hi='#28140A', iris_lo='#945D34', iris_glow='#E0A456',
            nose_z=-0.34, nose_len=0.170, nose_w=0.145, nose_lift=0.008,
            mouth_z=-0.60, mouth_w=0.20, smile=0.074, lip_col='#BA6B5A', lip_alpha=0.32,
            blush=0.30, blush_col='#E0816F', age_lines=True, age_col='#9A654D',
            lash_thick=0.034, lashes=True,
            brow_col='#8F8278', brow_thick=0.036, brow_gap=0.08, brow_arch=0.062, brow_tilt=0.08,
            ears=False,
        ),
        clips=['sit', 'sit_talk', 'idle'],
        style=dict(energy=0.85, stoop=3.0, robe=True, arm_out=0.26),
    ),
    'grandma': dict(
        label='Grandma Amina',
        props=dict(
            height=1.60, head_ratio=5.5, neck_frac=0.21, neck_ratio=0.35,
            hip_frac=0.45, ankle_frac=0.050, shoulder_w=0.122, hip_w=0.072,
            chest_d=0.074, belly_d=0.078, pelvis_d=0.082,
            waist_ratio=0.80, chest_ratio=0.92, hip_full=1.10, belly_full=1.08, chest_full=1.04, belly_fwd=0.65,
            arm_thick=0.96, hand_scale=0.95, leg_thick=0.98, foot_len=0.108, foot_w=0.98,
        ),
        skin='#D5A27C',
        face=dict(
            skin='#D5A27C', skull_w=0.96, skull_d=1.00, crown_h=1.01, jaw_taper=0.17, chin_drop=0.14,
            cheek_full=0.12, eye_z=-0.05, eye_x=0.34, eye_w=0.210, eye_h=0.205, eye_tilt=-0.02,
            iris_r=0.55, iris_hi='#2B170A', iris_lo='#A4703A', iris_glow='#E8B25E',
            nose_z=-0.34, nose_len=0.175, nose_w=0.140, nose_lift=0.012,
            mouth_z=-0.60, mouth_w=0.195, smile=0.068, lip_col='#BF705D', lip_alpha=0.30,
            blush=0.28, blush_col='#E38674', age_lines=True, age_col='#A47056',
            lash_thick=0.034, lashes=True,
            brow_col='#6A5446', brow_thick=0.036, brow_gap=0.09, brow_arch=0.064, brow_tilt=0.04,
            ears=False,
        ),
        clips=['idle', 'walk', 'talk'],
        style=dict(energy=0.90, stoop=3.5, robe=True, arm_out=0.24),
    ),
    'trader': dict(
        label='Uncle Hamdan',
        props=dict(
            height=1.78, head_ratio=5.7, neck_frac=0.23, neck_ratio=0.41,
            hip_frac=0.47, ankle_frac=0.050, shoulder_w=0.146, hip_w=0.072,
            chest_d=0.080, belly_d=0.078, pelvis_d=0.078,
            waist_ratio=0.78, chest_ratio=0.98, hip_full=1.02, belly_full=1.04, chest_full=1.10, belly_fwd=0.55,
            arm_thick=1.12, hand_scale=1.08, leg_thick=1.05, foot_len=0.116, foot_w=1.04,
        ),
        skin='#BC8258',
        face=dict(
            skin='#BC8258', skull_w=0.95, skull_d=1.02, crown_h=1.01, jaw_taper=0.19, chin_drop=0.17,
            cheek_full=0.08, eye_z=-0.05, eye_x=0.34, eye_w=0.200, eye_h=0.185, eye_tilt=0.04,
            iris_r=0.52, iris_hi='#1D0F08', iris_lo='#754622', iris_glow='#CE8E46',
            nose_z=-0.34, nose_len=0.210, nose_w=0.155, nose_lift=-0.005,
            mouth_z=-0.61, mouth_w=0.205, smile=0.055, lip_col='#9D5844', lip_alpha=0.22,
            blush=0.14, blush_col='#CF7058', age_lines=False,
            lash_thick=0.032, lashes=False,
            brow_col='#221610', brow_thick=0.050, brow_gap=0.06, brow_arch=0.050, brow_tilt=-0.08,
            ears=False,
        ),
        clips=['idle', 'walk', 'talk'],
        style=dict(energy=1.02, stoop=0.0, robe=True, arm_out=0.26),
    ),
    'sheikh': dict(
        label='Sheikh Younis',
        props=dict(
            height=1.76, head_ratio=5.6, neck_frac=0.23, neck_ratio=0.38,
            hip_frac=0.46, ankle_frac=0.050, shoulder_w=0.134, hip_w=0.070,
            chest_d=0.074, belly_d=0.076, pelvis_d=0.076,
            waist_ratio=0.80, chest_ratio=0.94, hip_full=1.02, belly_full=1.06, chest_full=1.02, belly_fwd=0.65,
            arm_thick=1.02, hand_scale=1.02, leg_thick=1.00, foot_len=0.114, foot_w=1.02,
        ),
        skin='#C78E65',
        face=dict(
            skin='#C78E65', skull_w=0.95, skull_d=1.01, crown_h=1.01, jaw_taper=0.18, chin_drop=0.16,
            cheek_full=0.09, eye_z=-0.05, eye_x=0.34, eye_w=0.200, eye_h=0.190, eye_tilt=-0.03,
            iris_r=0.53, iris_hi='#221209', iris_lo='#83532C', iris_glow='#D99B50',
            nose_z=-0.34, nose_len=0.200, nose_w=0.150, nose_lift=0.0,
            mouth_z=-0.61, mouth_w=0.20, smile=0.062, lip_col='#AB6450', lip_alpha=0.24,
            blush=0.16, blush_col='#D47A64', age_lines=True, age_col='#965F48',
            lash_thick=0.030, lashes=False,
            brow_col='#B5B0A8', brow_thick=0.048, brow_gap=0.07, brow_arch=0.056, brow_tilt=0.06,
            ears=True, ear_scale=1.00,
        ),
        clips=['idle', 'walk', 'talk'],
        style=dict(energy=0.88, stoop=2.5, robe=True, arm_out=0.25),
    ),
    'aunt': dict(
        label='Aunt Salma',
        props=dict(
            height=1.58, head_ratio=5.4, neck_frac=0.21, neck_ratio=0.33,
            hip_frac=0.46, ankle_frac=0.050, shoulder_w=0.118, hip_w=0.070,
            chest_d=0.070, belly_d=0.068, pelvis_d=0.076,
            waist_ratio=0.72, chest_ratio=0.90, hip_full=1.08, belly_full=0.96, chest_full=1.00, belly_fwd=0.45,
            arm_thick=0.92, hand_scale=0.92, leg_thick=0.95, foot_len=0.106, foot_w=0.96,
        ),
        skin='#D0966B',
        face=dict(
            skin='#D0966B', skull_w=0.96, skull_d=0.99, crown_h=1.02, jaw_taper=0.18, chin_drop=0.14,
            cheek_full=0.13, eye_z=-0.05, eye_x=0.34, eye_w=0.220, eye_h=0.220, eye_tilt=0.04,
            iris_r=0.57, iris_hi='#271309', iris_lo='#A86B33', iris_glow='#EDB458',
            nose_z=-0.34, nose_len=0.155, nose_w=0.128, nose_lift=0.025,
            mouth_z=-0.60, mouth_w=0.20, smile=0.076, lip_col='#C86B5D', lip_alpha=0.38,
            blush=0.34, blush_col='#E67F6E', age_lines=False,
            lash_thick=0.036, lashes=True,
            brow_col='#3B2217', brow_thick=0.036, brow_gap=0.09, brow_arch=0.068, brow_tilt=-0.02,
            ears=False,
        ),
        clips=['idle', 'walk', 'talk'],
        style=dict(energy=1.10, stoop=0.0, robe=True, arm_out=0.23),
    ),
}


def _base_mats(key, cfg):
    """Create shared per-character skin, lash, brow, mouth, and teeth toon materials."""
    F = cfg['face']
    img = HD.paint_face_texture(key, F)
    return {
        'skin': L.toon_mat(f'toon_skin_{key}', cfg['skin'], shadow='#CA978F', rim=0.22, bands=(0.05, 0.26)),
        'face': L.toon_mat(f'toon_face_{key}', image=img, shadow='#D4A198', rim=0.22, bands=(0.04, 0.24)),
        'lash': L.toon_mat('toon_lash', '#2B1810', shadow='#FFFFFF', rim=0.0),
        'brow': L.toon_mat(f'toon_brow_{key}', F['brow_col'], shadow='#B9959A', rim=0.06),
        'mouth': L.toon_mat('toon_mouth', '#69221C', shadow='#FFFFFF', rim=0.0),
        'teeth': L.toon_mat('toon_teeth', '#FFF6EA', shadow='#E4D6C8', rim=0.0),
    }


# ------------------------------------------------------------------ outfits per character
def _outfit_player(col, lm, p, F, M, rig_obj):
    M['gal'] = L.toon_mat('toon_galabiya_cream', '#F2E5C9', shadow='#C9B19E', rim=0.20)
    M['trim'] = L.toon_mat('toon_trim_turquoise', '#2F8B8C', shadow='#8BA0AE', rim=0.16)
    M['sash'] = L.toon_mat('toon_sash_gold', '#DFA543', shadow='#BA9380', rim=0.18)
    M['sirwal'] = L.toon_mat('toon_sirwal_sand', '#D8C7A8', shadow='#B39E92', rim=0.16)
    M['hair'] = L.toon_mat('toon_hair_chestnut', '#6A4227', shadow='#987A7F', rim=0.22)
    M['bag'] = L.toon_mat('toon_leather_cognac', '#9B5B30', shadow='#A88384', rim=0.18)
    M['strap'] = L.toon_mat('toon_leather_dark', '#63381D', shadow='#987A82', rim=0.14)
    M['brass'] = L.toon_mat('toon_gold_brass', '#F0BE59', shadow='#C69C72', rim=0.28)

    parts = []
    # Visible skin: sturdy neck, lower forearms+hands, ankles+sandal feet
    parts.append((B.build_neck('player_neck', col, lm, p, M['skin'], rig_obj), OUTLINE_SKIN))
    for o in B.build_forearms_and_hands('player_arm', col, lm, p, M['skin'], rig_obj, forearm_start=0.40):
        parts.append((o, OUTLINE_SKIN))
    sk_ft, sh_ft = B.build_ankles_and_feet(
        'player_ft', col, lm, p, M['skin'], M['strap'], rig_obj, shoe_style='sandal', ankle_top=0.14
    )
    for o in sk_ft:
        parts.append((o, OUTLINE_SKIN))
    for o in sh_ft:
        parts.append((o, OUTLINE_CLOTH))

    # Knee-length explorer galabiya with turquoise neckline embroidery & warm gold cloth sash
    for o in G.build_galabiya(
        'player_gal', col, lm, p, M['gal'], rig_obj,
        hem_z=lm['knee_z'] - 0.03, ease=0.022, skirt_flare=0.22, folds=0.024,
        sleeve_end=0.72, sleeve_r=0.048, sleeve_flare=0.014, collar_h=0.020,
        trim_mat=M['trim'], trim_style='placket_cuff',
    ):
        ol_th = 0.0 if ('placket' in o.name or 'cufftrim' in o.name) else OUTLINE_CLOTH
        parts.append((o, ol_th))
    for o in G.build_sash('player_sash', col, lm, p, M['sash'], rig_obj, ease=0.026, height=0.052, tails=True, tail_side=1.0):
        parts.append((o, OUTLINE_CLOTH * 0.75))
    for o in G.build_trousers('player_sirwal', col, lm, p, M['sirwal'], rig_obj, hem_up=0.036, loose=0.024):
        parts.append((o, OUTLINE_CLOTH))

    # Voluminous wavy chestnut boy hair (iconic from behind!)
    hair = HD.build_boy_hair('player_hair', col, lm['head_center'], lm['head_r'], F, M['hair'])
    R.skin_rigid(hair, rig_obj, 'head')
    parts.append((hair, OUTLINE_CLOTH))

    # Explorer leather satchel + snug shoulder straps + brass buckles
    for o in G.build_backpack('player_bag', col, lm, p, M['bag'], M['strap'], M['brass'], rig_obj, robe_ease=0.022):
        ol_th = 0.0 if 'buckles' in o.name else (OUTLINE_SKIN if 'straps' in o.name else OUTLINE_CLOTH)
        parts.append((o, ol_th))
    return parts


def _outfit_farmer(col, lm, p, F, M, rig_obj):
    M['gal'] = L.toon_mat('toon_galabiya_brown', '#835230', shadow='#9F8086', rim=0.20)
    M['vest'] = L.toon_mat('toon_vest_olive', '#556B3E', shadow='#8A9292', rim=0.20)
    M['brass'] = L.toon_mat('toon_brass_button', '#E4B150', shadow='#BA9378', rim=0.25)
    M['turban'] = L.toon_mat('toon_turban_cream', '#F3EDE0', shadow='#C5BDCB', rim=0.22)
    M['beard'] = L.toon_mat('toon_beard_white', '#F1ECE4', shadow='#C9C2D0', rim=0.24)
    M['scarf'] = L.toon_mat(
        'toon_scarf_village',
        image=L.check_pattern_image('scarf_village', '#EFE4CE', '#7E4A29', '#C98A2E', size=256, cells=8),
        shadow='#BA9F9E', rim=0.18,
    )
    M['shoe'] = L.toon_mat('toon_shoe_brown', '#4E311D', shadow='#947B84', rim=0.18)

    parts = []
    parts.append((B.build_neck('farmer_neck', col, lm, p, M['skin'], rig_obj), OUTLINE_SKIN))
    for o in B.build_forearms_and_hands('farmer_arm', col, lm, p, M['skin'], rig_obj, forearm_start=0.50):
        parts.append((o, OUTLINE_SKIN))
    sk_ft, sh_ft = B.build_ankles_and_feet(
        'farmer_ft', col, lm, p, M['skin'], M['shoe'], rig_obj, shoe_style='slipper', ankle_top=0.10
    )
    for o in sk_ft:
        parts.append((o, OUTLINE_SKIN))
    for o in sh_ft:
        parts.append((o, OUTLINE_CLOTH))

    for o in G.build_galabiya(
        'farmer_gal', col, lm, p, M['gal'], rig_obj,
        hem_z=0.052, ease=0.025, skirt_flare=0.24, folds=0.032,
        sleeve_end=0.80, sleeve_r=0.056, sleeve_flare=0.024, collar_h=0.022,
    ):
        parts.append((o, OUTLINE_CLOTH))
    for o in G.build_vest('farmer_vest', col, lm, p, M['vest'], rig_obj, ease=0.050, button_mat=M['brass']):
        parts.append((o, 0.0 if 'buttons' in o.name else OUTLINE_CLOTH))
    parts.append((G.build_shoulder_scarf('farmer_scarf', col, lm, p, M['scarf'], rig_obj, side=-1.0, ease=0.066), OUTLINE_CLOTH))

    for o in G.build_turban('farmer_turban', col, lm, F, M['turban'], rig_obj, wraps=4, puff=0.24):
        parts.append((o, OUTLINE_CLOTH))
    beard = HD.build_beard('farmer_beard', col, lm['head_center'], lm['head_r'], F, M['beard'], style='full')
    R.skin_rigid(beard, rig_obj, 'head')
    parts.append((beard, OUTLINE_CLOTH))
    return parts


def _post_farmer(col, lm, M, rig_obj):
    M['wood'] = L.toon_mat('toon_wood_staff', '#7B4E2B', shadow='#9C7C82', rim=0.20)
    M['grip'] = L.toon_mat('toon_staff_grip', '#4C2E1A', shadow='#927880', rim=0.18)
    idle_act = next(a for a in bpy.data.actions if a.name == 'farmer|idle')
    return [(o, OUTLINE_CLOTH) for o in G.build_staff('farmer_staff', col, rig_obj, M['wood'], idle_act, grip_mat=M['grip'])]


def _outfit_grandma_zainab(col, lm, p, F, M, rig_obj):
    M['dress'] = L.toon_mat('toon_dress_plum', '#30293A', shadow='#8882A4', rim=0.22)
    M['tarha'] = L.toon_mat('toon_tarha_dark', '#25202E', shadow='#847FA2', rim=0.22)
    M['gold'] = L.toon_mat('toon_trim_gold', '#E5B454', shadow='#BE9878', rim=0.26)
    M['shoe'] = L.toon_mat('toon_slipper_dark', '#201B24', shadow='#8A849A', rim=0.16)

    parts = []
    # Neck is modestly covered by the tarha; hands & ankles/slippers show
    for o in B.build_forearms_and_hands('zainab_arm', col, lm, p, M['skin'], rig_obj, forearm_start=0.58):
        parts.append((o, OUTLINE_SKIN))
    sk_ft, sh_ft = B.build_ankles_and_feet(
        'zainab_ft', col, lm, p, M['skin'], M['shoe'], rig_obj, shoe_style='slipper', ankle_top=0.10
    )
    for o in sk_ft:
        parts.append((o, OUTLINE_SKIN))
    for o in sh_ft:
        parts.append((o, OUTLINE_CLOTH))

    # Seated-friendly flowing dress with antique sun-gold cuffs (no chest placket to poke through tarha!)
    for o in G.build_galabiya(
        'zainab_dress', col, lm, p, M['dress'], rig_obj,
        hem_z=0.055, ease=0.030, skirt_flare=0.30, folds=0.030,
        sleeve_end=0.84, sleeve_r=0.050, sleeve_flare=0.016, collar_h=0.020,
        seated_mode=True, trim_mat=M['gold'], trim_style='cuff_hem',
    ):
        parts.append((o, 0.0 if ('placket' in o.name or 'cufftrim' in o.name) else OUTLINE_CLOTH))
    for o in G.build_hijab(
        'zainab_tarha', col, lm, p, F, M['tarha'], rig_obj,
        trim_mat=M['gold'], drop_front=0.14, drop_back=0.26, bun_puff=0.22,
    ):
        parts.append((o, 0.0 if ('trim' in o.name or 'folds' in o.name) else OUTLINE_CLOTH))
    return parts


def _outfit_grandma(col, lm, p, F, M, rig_obj):
    M['dress'] = L.toon_mat('toon_dress_emerald', '#2E6E54', shadow='#8699A8', rim=0.20)
    M['hijab'] = L.toon_mat('toon_hijab_indigo', '#3B4F8F', shadow='#9092BC', rim=0.20)
    M['trim'] = L.toon_mat('toon_trim_creamgold', '#ECD49A', shadow='#C3B09E', rim=0.20)
    M['shoe'] = L.toon_mat('toon_slipper_brown', '#5E3B24', shadow='#9C7F84', rim=0.16)
    M['glasses'] = L.toon_mat('toon_glasses_gold', '#D89E3C', shadow='#B8906E', rim=0.24)

    parts = []
    for o in B.build_forearms_and_hands('grandma_arm', col, lm, p, M['skin'], rig_obj, forearm_start=0.58):
        parts.append((o, OUTLINE_SKIN))
    sk_ft, sh_ft = B.build_ankles_and_feet(
        'grandma_ft', col, lm, p, M['skin'], M['shoe'], rig_obj, shoe_style='slipper', ankle_top=0.10
    )
    for o in sk_ft:
        parts.append((o, OUTLINE_SKIN))
    for o in sh_ft:
        parts.append((o, OUTLINE_CLOTH))

    for o in G.build_galabiya(
        'grandma_dress', col, lm, p, M['dress'], rig_obj,
        hem_z=0.045, ease=0.026, skirt_flare=0.30, folds=0.036,
        sleeve_end=0.84, sleeve_r=0.048, sleeve_flare=0.016, collar_h=0.020,
        trim_mat=M['trim'], trim_style='cuff_hem',
    ):
        parts.append((o, 0.0 if ('placket' in o.name or 'cufftrim' in o.name) else OUTLINE_CLOTH))
    for o in G.build_hijab(
        'grandma_hijab', col, lm, p, F, M['hijab'], rig_obj,
        trim_mat=None, drop_front=0.23, drop_back=0.30, bun_puff=0.22,
    ):
        parts.append((o, 0.0 if 'folds' in o.name else OUTLINE_CLOTH))
    parts.append((G.build_glasses('grandma_glasses', col, lm, F, M['glasses'], rig_obj), 0.0))
    return parts


def _outfit_trader(col, lm, p, F, M, rig_obj):
    M['thobe'] = L.toon_mat('toon_thobe_royal', '#2E457E', shadow='#8E94B8', rim=0.20)
    M['bisht'] = L.toon_mat('toon_bisht_espresso', '#573B2A', shadow='#95808A', rim=0.18)
    M['gold'] = L.toon_mat('toon_zari_gold', '#F0BE59', shadow='#C49A74', rim=0.28)
    M['shemagh'] = L.toon_mat(
        'toon_shemagh_red',
        image=L.check_pattern_image('shemagh_red', '#F5EFE6', '#B9342C', size=256, cells=8),
        shadow='#C2A8B2', rim=0.18,
    )
    M['agal'] = L.toon_mat('toon_agal_black', '#1D181A', shadow='#8C8698', rim=0.22)
    M['beard'] = L.toon_mat('toon_beard_dark', '#291B14', shadow='#8D7D8C', rim=0.16)
    M['shoe'] = L.toon_mat('toon_leather_camel', '#8A5830', shadow='#A88584', rim=0.16)

    parts = []
    parts.append((B.build_neck('trader_neck', col, lm, p, M['skin'], rig_obj), OUTLINE_SKIN))
    for o in B.build_forearms_and_hands('trader_arm', col, lm, p, M['skin'], rig_obj, forearm_start=0.52):
        parts.append((o, OUTLINE_SKIN))
    sk_ft, sh_ft = B.build_ankles_and_feet(
        'trader_ft', col, lm, p, M['skin'], M['shoe'], rig_obj, shoe_style='slipper', ankle_top=0.10
    )
    for o in sk_ft:
        parts.append((o, OUTLINE_SKIN))
    for o in sh_ft:
        parts.append((o, OUTLINE_CLOTH))

    for o in G.build_galabiya(
        'trader_thobe', col, lm, p, M['thobe'], rig_obj,
        hem_z=0.050, ease=0.022, skirt_flare=0.20, folds=0.024,
        sleeve_end=0.82, sleeve_r=0.050, sleeve_flare=0.012, collar_h=0.024,
    ):
        parts.append((o, OUTLINE_CLOTH))
    for o in G.build_sash('trader_sash', col, lm, p, M['gold'], rig_obj, ease=0.028, height=0.058, tails=False):
        parts.append((o, 0.0))
    for o in G.build_open_robe(
        'trader_bisht', col, lm, p, M['bisht'], rig_obj,
        trim_mat=M['gold'], hem_z=0.070, ease=0.044, skirt_flare=0.30,
        open_rad=0.44, sleeve_end=0.68, sleeve_r=0.070, sleeve_flare=0.032,
    ):
        parts.append((o, 0.0 if 'trim' in o.name else OUTLINE_CLOTH))

    for o in G.build_shemagh_and_agal('trader_shemagh', col, lm, p, F, M['shemagh'], M['agal'], M['gold'], rig_obj):
        parts.append((o, 0.0 if 'gold' in o.name else OUTLINE_CLOTH))
    beard = HD.build_beard('trader_beard', col, lm['head_center'], lm['head_r'], F, M['beard'], style='trimmed')
    R.skin_rigid(beard, rig_obj, 'head')
    parts.append((beard, OUTLINE_CLOTH))
    return parts


def _outfit_sheikh(col, lm, p, F, M, rig_obj):
    M['thobe'] = L.toon_mat('toon_thobe_ivory', '#F4EBDA', shadow='#C9BBB2', rim=0.20)
    M['kaftan'] = L.toon_mat('toon_kaftan_olive', '#748857', shadow='#94A09C', rim=0.20)
    M['piping'] = L.toon_mat('toon_piping_gold', '#E0C078', shadow='#BBA88E', rim=0.22)
    M['imama'] = L.toon_mat('toon_imama_white', '#F7F3EA', shadow='#C6C0D0', rim=0.20)
    M['tarboush'] = L.toon_mat('toon_tarboush_crimson', '#8F2929', shadow='#9D7686', rim=0.20)
    M['beard'] = L.toon_mat('toon_beard_grey', '#CCC8C2', shadow='#AAA6B8', rim=0.20)
    M['shoe'] = L.toon_mat('toon_shoe_walnut', '#5B3A24', shadow='#9C7F84', rim=0.16)

    parts = []
    parts.append((B.build_neck('sheikh_neck', col, lm, p, M['skin'], rig_obj), OUTLINE_SKIN))
    for o in B.build_forearms_and_hands('sheikh_arm', col, lm, p, M['skin'], rig_obj, forearm_start=0.52):
        parts.append((o, OUTLINE_SKIN))
    sk_ft, sh_ft = B.build_ankles_and_feet(
        'sheikh_ft', col, lm, p, M['skin'], M['shoe'], rig_obj, shoe_style='slipper', ankle_top=0.10
    )
    for o in sk_ft:
        parts.append((o, OUTLINE_SKIN))
    for o in sh_ft:
        parts.append((o, OUTLINE_CLOTH))

    for o in G.build_galabiya(
        'sheikh_thobe', col, lm, p, M['thobe'], rig_obj,
        hem_z=0.050, ease=0.022, skirt_flare=0.20, folds=0.024,
        sleeve_end=0.84, sleeve_r=0.048, sleeve_flare=0.012, collar_h=0.026,
    ):
        parts.append((o, OUTLINE_CLOTH))
    for o in G.build_open_robe(
        'sheikh_kaftan', col, lm, p, M['kaftan'], rig_obj,
        trim_mat=M['piping'], hem_z=0.075, ease=0.040, skirt_flare=0.28,
        open_rad=0.38, sleeve_end=0.72, sleeve_r=0.066, sleeve_flare=0.026,
    ):
        parts.append((o, 0.0 if 'trim' in o.name else OUTLINE_CLOTH))

    for o in G.build_turban('sheikh_imama', col, lm, F, M['imama'], rig_obj, tarboush_mat=M['tarboush'], wraps=4, puff=0.18):
        parts.append((o, OUTLINE_CLOTH))
    beard = HD.build_beard('sheikh_beard', col, lm['head_center'], lm['head_r'], F, M['beard'], style='neat')
    R.skin_rigid(beard, rig_obj, 'head')
    parts.append((beard, OUTLINE_CLOTH))
    return parts


def _outfit_aunt(col, lm, p, F, M, rig_obj):
    M['dress'] = L.toon_mat('toon_dress_ochre', '#DCA042', shadow='#BA917E', rim=0.20)
    M['hijab'] = L.toon_mat('toon_hijab_terracotta', '#C26052', shadow='#AC7E8A', rim=0.20)
    M['sash'] = L.toon_mat('toon_sash_turquoise', '#2A8A8B', shadow='#829EA8', rim=0.20)
    M['trim'] = L.toon_mat('toon_trim_cream', '#F5E7C8', shadow='#C9B7A6', rim=0.20)
    M['shoe'] = L.toon_mat('toon_slipper_tan', '#7A4A2A', shadow='#A48484', rim=0.16)

    parts = []
    for o in B.build_forearms_and_hands('aunt_arm', col, lm, p, M['skin'], rig_obj, forearm_start=0.56):
        parts.append((o, OUTLINE_SKIN))
    sk_ft, sh_ft = B.build_ankles_and_feet(
        'aunt_ft', col, lm, p, M['skin'], M['shoe'], rig_obj, shoe_style='slipper', ankle_top=0.10
    )
    for o in sk_ft:
        parts.append((o, OUTLINE_SKIN))
    for o in sh_ft:
        parts.append((o, OUTLINE_CLOTH))

    for o in G.build_galabiya(
        'aunt_dress', col, lm, p, M['dress'], rig_obj,
        hem_z=0.045, ease=0.022, skirt_flare=0.32, folds=0.036,
        sleeve_end=0.82, sleeve_r=0.045, sleeve_flare=0.018, collar_h=0.020,
        trim_mat=M['trim'], trim_style='cuff_hem',
    ):
        parts.append((o, 0.0 if ('placket' in o.name or 'cufftrim' in o.name) else OUTLINE_CLOTH))
    for o in G.build_sash('aunt_sash', col, lm, p, M['sash'], rig_obj, ease=0.030, height=0.072, tails=True, tail_side=1.0):
        parts.append((o, OUTLINE_CLOTH * 0.75))
    for o in G.build_hijab(
        'aunt_hijab', col, lm, p, F, M['hijab'], rig_obj,
        trim_mat=None, drop_front=0.21, drop_back=0.28, asymmetric_tail=True, bun_puff=0.24,
    ):
        parts.append((o, 0.0 if 'folds' in o.name else OUTLINE_CLOTH))
    return parts


OUTFITS = {
    'player': _outfit_player,
    'farmer': _outfit_farmer,
    'grandma_zainab': _outfit_grandma_zainab,
    'grandma': _outfit_grandma,
    'trader': _outfit_trader,
    'sheikh': _outfit_sheikh,
    'aunt': _outfit_aunt,
}

POST_ANIM = {
    'farmer': _post_farmer,
}


# ------------------------------------------------------------------ character assembly
def build(key):
    """Build one complete rigged, animated, outlined character and return its info dict."""
    cfg = CAST[key]
    p = cfg['props']
    F = dict(cfg['face'])
    col = L.fresh_collection('char_' + key)

    # Clear any old actions for this key
    for act in list(bpy.data.actions):
        if act.name.startswith(key + '|'):
            bpy.data.actions.remove(act)

    lm = R.compute_landmarks(p)
    rig_obj = R.build_armature(key + '_rig', col, lm)
    M = _base_mats(key, cfg)

    # 1) Sculpted 3D Head, Eyes, Lids, Brows, Talking Mouth
    head_obj = HD.build_head_mesh(key + '_head', col, lm['head_center'], lm['head_r'], F, M['face'])
    eyes_obj, lash_obj, lid_objs, lid_bones = HD.build_eyes_and_lids(
        key, col, lm['head_center'], lm['head_r'], F, M['face'], M['skin'], M['lash']
    )
    brows_obj = HD.build_brows(key, col, lm['head_center'], lm['head_r'], F, M['brow'])
    mouth_obj, mouth_bone = HD.build_talking_mouth(
        key, col, lm['head_center'], lm['head_r'], F, M['mouth'], M['teeth']
    )

    face_bones = dict(lid_bones)
    face_bones['mouth'] = mouth_bone
    R.add_face_bones(rig_obj, face_bones)

    R.skin_rigid(head_obj, rig_obj, 'head')
    R.skin_rigid(eyes_obj, rig_obj, 'head')
    R.skin_rigid(lash_obj, rig_obj, 'head')
    R.skin_rigid(brows_obj, rig_obj, 'head')
    for bname, lobj in lid_objs:
        R.skin_rigid(lobj, rig_obj, bname)
    R.skin_rigid(mouth_obj, rig_obj, 'mouth')

    # Outline policy (§5.5): thin outline on head/skin, ZERO outline on eyes, lashes, lids, brows, mouth, glasses!
    parts = [
        (head_obj, OUTLINE_SKIN),
        (eyes_obj, 0.0),
        (lash_obj, 0.0),
        (brows_obj, 0.0),
        (mouth_obj, 0.0),
    ] + [(lobj, 0.0) for _, lobj in lid_objs]

    # 2) Body + Outfit parts
    parts.extend(OUTFITS[key](col, lm, p, F, M, rig_obj))

    # 3) Animations as NLA tracks
    A.animate(rig_obj, key, cfg['clips'], cfg.get('style', {}))

    # 4) Pose-aligned accessories (Grandpa Salim's staff)
    if key in POST_ANIM:
        parts.extend(POST_ANIM[key](col, lm, M, rig_obj))

    # 5) Build selective per-part inverted-hull outline BEFORE joining into 1 character mesh
    ol_obj = L.build_combined_outline(parts, key + '_outline', col, rig_obj)
    mesh_objs = [o for o, _ in parts]
    mesh_obj = L.join_objects(mesh_objs, key, col)
    # Apply lifted soft cheek/mouth/jaw custom normals after join so EEVEE + Three.js toon cel wraps softly!
    HD.apply_soft_face_normals(mesh_obj, lm['head_center'], lm['head_r'], F)
    for m in list(mesh_obj.modifiers):
        if m.type == 'ARMATURE':
            m.object = rig_obj

    return {
        'key': key,
        'rig': rig_obj,
        'mesh': mesh_obj,
        'outline': ol_obj,
        'tris': L.tri_count(mesh_obj),
        'outline_tris': L.tri_count(ol_obj),
        'bones': L.bone_count(rig_obj),
        'height': p['height'],
    }
