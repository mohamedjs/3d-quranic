"""Cast definitions (proportions, palette, bigger warm eyes, v4 Poly Haven fabric layers, clips) & assembly."""
import bpy

import lib as L
import rig as R
import body as B
import head as HD
import garments as G
import anim as A

ORDER = ['player', 'farmer', 'grandma_zainab', 'grandma', 'trader', 'sheikh', 'aunt']

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
            skin='#CC8E64', skull_w=0.98, skull_d=1.00, crown_h=1.02, jaw_taper=0.15, chin_drop=0.12,
            cheek_full=0.15, eye_z=-0.05, eye_x=0.345, eye_w=0.242, eye_h=0.252, eye_tilt=0.03,
            iris_r=0.61, iris_hi='#2A1308', iris_lo='#BC7638', iris_glow='#F5BE5E',
            nose_z=-0.35, nose_len=0.155, nose_w=0.13, nose_lift=0.034,
            mouth_z=-0.61, mouth_w=0.205, smile=0.072, lip_col='#CC6A57', lip_alpha=0.40,
            blush=0.42, blush_col='#EC7B67', lash_thick=0.034, lashes=False,
            brow_col='#4B2D1A', brow_thick=0.044, brow_gap=0.075, brow_arch=0.058, brow_tilt=-0.02,
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
            skin='#B97B53', skull_w=0.96, skull_d=1.02, crown_h=1.00, jaw_taper=0.17, chin_drop=0.16,
            cheek_full=0.11, eye_z=-0.045, eye_x=0.34, eye_w=0.212, eye_h=0.204, eye_tilt=-0.06,
            iris_r=0.56, iris_hi='#241108', iris_lo='#8F5A2E', iris_glow='#DE9F52',
            nose_z=-0.34, nose_len=0.215, nose_w=0.165, nose_lift=-0.01,
            mouth_z=-0.61, mouth_w=0.21, smile=0.064, lip_col='#B4604B', lip_alpha=0.34,
            blush=0.26, blush_col='#DC745D', age_lines=True, age_col='#8B523B',
            lash_thick=0.030, lashes=False,
            brow_col='#F0EBE0', brow_thick=0.058, brow_gap=0.055, brow_arch=0.060, brow_tilt=0.12,
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
            skin='#CB946F', skull_w=0.98, skull_d=1.00, crown_h=1.00, jaw_taper=0.14, chin_drop=0.12,
            cheek_full=0.16, eye_z=-0.05, eye_x=0.34, eye_w=0.222, eye_h=0.218, eye_tilt=-0.04,
            iris_r=0.58, iris_hi='#28140A', iris_lo='#986136', iris_glow='#E6AA5A',
            nose_z=-0.34, nose_len=0.170, nose_w=0.145, nose_lift=0.008,
            mouth_z=-0.60, mouth_w=0.205, smile=0.078, lip_col='#C76B59', lip_alpha=0.42,
            blush=0.38, blush_col='#E87F6B', age_lines=True, age_col='#9A654D',
            lash_thick=0.034, lashes=True,
            brow_col='#8F8278', brow_thick=0.036, brow_gap=0.075, brow_arch=0.064, brow_tilt=0.08,
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
            skin='#D5A27C', skull_w=0.96, skull_d=1.00, crown_h=1.01, jaw_taper=0.16, chin_drop=0.13,
            cheek_full=0.13, eye_z=-0.045, eye_x=0.34, eye_w=0.226, eye_h=0.222, eye_tilt=-0.02,
            iris_r=0.58, iris_hi='#2B170A', iris_lo='#A8743C', iris_glow='#EDB862',
            nose_z=-0.34, nose_len=0.175, nose_w=0.140, nose_lift=0.012,
            mouth_z=-0.60, mouth_w=0.20, smile=0.072, lip_col='#CC705B', lip_alpha=0.42,
            blush=0.36, blush_col='#EB836F', age_lines=True, age_col='#A47056',
            lash_thick=0.034, lashes=True,
            brow_col='#6A5446', brow_thick=0.036, brow_gap=0.085, brow_arch=0.066, brow_tilt=0.04,
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
            skin='#BC8258', skull_w=0.95, skull_d=1.02, crown_h=1.01, jaw_taper=0.18, chin_drop=0.16,
            cheek_full=0.09, eye_z=-0.045, eye_x=0.34, eye_w=0.216, eye_h=0.204, eye_tilt=0.04,
            iris_r=0.56, iris_hi='#1D0F08', iris_lo='#7A4A24', iris_glow='#D4944A',
            nose_z=-0.34, nose_len=0.210, nose_w=0.155, nose_lift=-0.005,
            mouth_z=-0.61, mouth_w=0.205, smile=0.058, lip_col='#AD5C48', lip_alpha=0.34,
            blush=0.22, blush_col='#DA735A', age_lines=False,
            lash_thick=0.032, lashes=False,
            brow_col='#221610', brow_thick=0.050, brow_gap=0.055, brow_arch=0.052, brow_tilt=-0.08,
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
            skin='#C78E65', skull_w=0.95, skull_d=1.01, crown_h=1.01, jaw_taper=0.17, chin_drop=0.15,
            cheek_full=0.10, eye_z=-0.045, eye_x=0.34, eye_w=0.216, eye_h=0.208, eye_tilt=-0.03,
            iris_r=0.57, iris_hi='#221209', iris_lo='#88572E', iris_glow='#DFA154',
            nose_z=-0.34, nose_len=0.200, nose_w=0.150, nose_lift=0.0,
            mouth_z=-0.61, mouth_w=0.20, smile=0.066, lip_col='#B96650', lip_alpha=0.34,
            blush=0.24, blush_col='#DE7B64', age_lines=True, age_col='#965F48',
            lash_thick=0.030, lashes=False,
            brow_col='#B5B0A8', brow_thick=0.048, brow_gap=0.065, brow_arch=0.058, brow_tilt=0.06,
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
            skin='#D0966B', skull_w=0.96, skull_d=0.99, crown_h=1.02, jaw_taper=0.17, chin_drop=0.13,
            cheek_full=0.14, eye_z=-0.045, eye_x=0.34, eye_w=0.236, eye_h=0.238, eye_tilt=0.04,
            iris_r=0.60, iris_hi='#271309', iris_lo='#AC6F36', iris_glow='#F2BA5C',
            nose_z=-0.34, nose_len=0.155, nose_w=0.128, nose_lift=0.025,
            mouth_z=-0.60, mouth_w=0.202, smile=0.078, lip_col='#D4695B', lip_alpha=0.46,
            blush=0.42, blush_col='#EE7C6B', age_lines=False,
            lash_thick=0.036, lashes=True,
            brow_col='#3B2217', brow_thick=0.036, brow_gap=0.085, brow_arch=0.070, brow_tilt=-0.02,
            ears=False,
        ),
        clips=['idle', 'walk', 'talk'],
        style=dict(energy=1.10, stoop=0.0, robe=True, arm_out=0.23),
    ),
}


def _shared_mats(key, cfg):
    """Build exact M5 contract material palette (5 PH fabrics + skin + hair + face_<key> + eye + metal)."""
    img = HD.paint_face_texture(key, cfg['face'])
    return {
        'cotton':  L.fabric_mat('ph_cotton'),
        'linen':   L.fabric_mat('ph_linen'),
        'wool':    L.fabric_mat('ph_wool'),
        'hessian': L.fabric_mat('ph_hessian'),
        'leather': L.fabric_mat('ph_leather'),
        'skin':    L.plain_mat('skin', roughness=0.55, metalness=0.0, sss=0.22, spec=0.24),
        'hair':    L.plain_mat('hair', roughness=0.60, metalness=0.0, sss=0.0, spec=0.36),
        'metal':   L.plain_mat('metal', roughness=0.30, metalness=1.0, sss=0.0, spec=0.80),
        'face':    L.face_mat(key, img),
        'eye':     L.eye_mat(key, img),
    }


# ------------------------------------------------------------------ outfits per character
def _outfit_player(col, lm, p, F, M, rig_obj):
    sk = F['skin']
    parts = []
    parts.append(B.build_neck('player_neck', col, lm, p, M['skin'], sk, rig_obj))
    parts.extend(B.build_forearms_and_hands('player_arm', col, lm, p, M['skin'], sk, rig_obj, forearm_start=0.40))
    sk_ft, sh_ft = B.build_ankles_and_feet(
        'player_ft', col, lm, p, M['skin'], sk, M['leather'], '#63381D', rig_obj, shoe_style='sandal', ankle_top=0.14
    )
    parts.extend(sk_ft)
    parts.extend(sh_ft)

    parts.extend(G.build_galabiya(
        'player_gal', col, lm, p, M['cotton'], '#F2E5C9', rig_obj,
        hem_z=lm['knee_z'] - 0.03, ease=0.022, skirt_flare=0.22, folds=0.032, waist_cinch=0.85,
        sleeve_end=0.72, sleeve_r=0.048, sleeve_flare=0.014, collar_h=0.020,
        trim_mat=M['hessian'], trim_color='#2F8B8C', trim_style='placket_cuff',
    ))
    parts.extend(G.build_sash('player_sash', col, lm, p, M['hessian'], '#DFA543', rig_obj, ease=0.026, height=0.052, tails=True, tail_side=1.0))
    parts.extend(G.build_trousers('player_sirwal', col, lm, p, M['linen'], '#D8C7A8', rig_obj, hem_up=0.036, loose=0.024))

    hair = HD.build_boy_hair('player_hair', col, lm['head_center'], lm['head_r'], F, M['hair'], '#6A4227')
    R.skin_rigid(hair, rig_obj, 'head')
    parts.append(hair)

    parts.extend(G.build_backpack(
        'player_bag', col, lm, p, M['leather'], '#9B5B30', '#63381D', M['metal'], '#F0BE59', rig_obj, robe_ease=0.022
    ))
    return parts


def _outfit_farmer(col, lm, p, F, M, rig_obj):
    sk = F['skin']
    parts = []
    parts.append(B.build_neck('farmer_neck', col, lm, p, M['skin'], sk, rig_obj))
    parts.extend(B.build_forearms_and_hands('farmer_arm', col, lm, p, M['skin'], sk, rig_obj, forearm_start=0.50))
    sk_ft, sh_ft = B.build_ankles_and_feet(
        'farmer_ft', col, lm, p, M['skin'], sk, M['leather'], '#4E311D', rig_obj, shoe_style='slipper', ankle_top=0.10
    )
    parts.extend(sk_ft)
    parts.extend(sh_ft)

    parts.extend(G.build_galabiya(
        'farmer_gal', col, lm, p, M['cotton'], '#835230', rig_obj,
        hem_z=0.052, ease=0.025, skirt_flare=0.24, folds=0.042,
        sleeve_end=0.80, sleeve_r=0.056, sleeve_flare=0.024, collar_h=0.022,
    ))
    parts.extend(G.build_vest(
        'farmer_vest', col, lm, p, M['wool'], '#556B3E', rig_obj, ease=0.050, button_mat=M['metal'], button_color='#E4B150'
    ))
    parts.append(G.build_shoulder_scarf('farmer_scarf', col, lm, p, M['hessian'], rig_obj, side=-1.0, ease=0.066))

    parts.extend(G.build_turban('farmer_turban', col, lm, F, M['linen'], '#F3EDE0', rig_obj, wraps=4, puff=0.24))
    beard = HD.build_beard('farmer_beard', col, lm['head_center'], lm['head_r'], F, M['hair'], '#F1ECE4', style='full')
    R.skin_rigid(beard, rig_obj, 'head')
    parts.append(beard)
    return parts


def _post_farmer(col, lm, M, rig_obj):
    idle_act = next(a for a in bpy.data.actions if a.name == 'farmer|idle')
    return G.build_staff('farmer_staff', col, rig_obj, M['leather'], '#7B4E2B', '#4C2E1A', idle_act)


def _outfit_grandma_zainab(col, lm, p, F, M, rig_obj):
    sk = F['skin']
    parts = []
    parts.extend(B.build_forearms_and_hands('zainab_arm', col, lm, p, M['skin'], sk, rig_obj, forearm_start=0.58))
    sk_ft, sh_ft = B.build_ankles_and_feet(
        'zainab_ft', col, lm, p, M['skin'], sk, M['leather'], '#241E28', rig_obj, shoe_style='slipper', ankle_top=0.10
    )
    parts.extend(sk_ft)
    parts.extend(sh_ft)

    parts.extend(G.build_galabiya(
        'zainab_dress', col, lm, p, M['cotton'], '#30293A', rig_obj,
        hem_z=0.055, ease=0.030, skirt_flare=0.30, folds=0.038,
        sleeve_end=0.84, sleeve_r=0.050, sleeve_flare=0.016, collar_h=0.020,
        seated_mode=True, trim_mat=M['hessian'], trim_color='#E5B454', trim_style='cuff_hem',
    ))
    parts.extend(G.build_hijab(
        'zainab_tarha', col, lm, p, F, M['linen'], '#25202E', rig_obj,
        trim_mat=M['hessian'], trim_color='#E5B454', drop_front=0.14, drop_back=0.26, bun_puff=0.22,
    ))
    return parts


def _outfit_grandma(col, lm, p, F, M, rig_obj):
    sk = F['skin']
    parts = []
    parts.extend(B.build_forearms_and_hands('grandma_arm', col, lm, p, M['skin'], sk, rig_obj, forearm_start=0.58))
    sk_ft, sh_ft = B.build_ankles_and_feet(
        'grandma_ft', col, lm, p, M['skin'], sk, M['leather'], '#5E3B24', rig_obj, shoe_style='slipper', ankle_top=0.10
    )
    parts.extend(sk_ft)
    parts.extend(sh_ft)

    parts.extend(G.build_galabiya(
        'grandma_dress', col, lm, p, M['cotton'], '#2E6E54', rig_obj,
        hem_z=0.045, ease=0.026, skirt_flare=0.30, folds=0.044,
        sleeve_end=0.84, sleeve_r=0.048, sleeve_flare=0.016, collar_h=0.020,
        trim_mat=M['hessian'], trim_color='#ECD49A', trim_style='cuff_hem',
    ))
    parts.extend(G.build_hijab(
        'grandma_hijab', col, lm, p, F, M['linen'], '#3B4F8F', rig_obj,
        trim_mat=None, drop_front=0.23, drop_back=0.30, bun_puff=0.22,
    ))
    parts.append(G.build_glasses('grandma_glasses', col, lm, F, M['metal'], '#E0A842', rig_obj))
    return parts


def _outfit_trader(col, lm, p, F, M, rig_obj):
    sk = F['skin']
    parts = []
    parts.append(B.build_neck('trader_neck', col, lm, p, M['skin'], sk, rig_obj))
    parts.extend(B.build_forearms_and_hands('trader_arm', col, lm, p, M['skin'], sk, rig_obj, forearm_start=0.52))
    sk_ft, sh_ft = B.build_ankles_and_feet(
        'trader_ft', col, lm, p, M['skin'], sk, M['leather'], '#8A5830', rig_obj, shoe_style='slipper', ankle_top=0.10
    )
    parts.extend(sk_ft)
    parts.extend(sh_ft)

    parts.extend(G.build_galabiya(
        'trader_thobe', col, lm, p, M['cotton'], '#2E457E', rig_obj,
        hem_z=0.050, ease=0.022, skirt_flare=0.20, folds=0.030, waist_cinch=0.70,
        sleeve_end=0.82, sleeve_r=0.050, sleeve_flare=0.012, collar_h=0.024,
    ))
    parts.extend(G.build_sash('trader_sash', col, lm, p, M['hessian'], '#F0BE59', rig_obj, ease=0.028, height=0.058, tails=False))
    parts.extend(G.build_open_robe(
        'trader_bisht', col, lm, p, M['wool'], '#573B2A', rig_obj,
        trim_mat=M['hessian'], trim_color='#F0BE59', hem_z=0.070, ease=0.044, skirt_flare=0.30,
        open_rad=0.44, sleeve_end=0.68, sleeve_r=0.070, sleeve_flare=0.032,
    ))
    parts.extend(G.build_shemagh_and_agal('trader_shemagh', col, lm, p, F, M['linen'], M['wool'], M['metal'], rig_obj))
    beard = HD.build_beard('trader_beard', col, lm['head_center'], lm['head_r'], F, M['hair'], '#291B14', style='trimmed')
    R.skin_rigid(beard, rig_obj, 'head')
    parts.append(beard)
    return parts


def _outfit_sheikh(col, lm, p, F, M, rig_obj):
    sk = F['skin']
    parts = []
    parts.append(B.build_neck('sheikh_neck', col, lm, p, M['skin'], sk, rig_obj))
    parts.extend(B.build_forearms_and_hands('sheikh_arm', col, lm, p, M['skin'], sk, rig_obj, forearm_start=0.52))
    sk_ft, sh_ft = B.build_ankles_and_feet(
        'sheikh_ft', col, lm, p, M['skin'], sk, M['leather'], '#5B3A24', rig_obj, shoe_style='slipper', ankle_top=0.10
    )
    parts.extend(sk_ft)
    parts.extend(sh_ft)

    parts.extend(G.build_galabiya(
        'sheikh_thobe', col, lm, p, M['cotton'], '#F4EBDA', rig_obj,
        hem_z=0.050, ease=0.022, skirt_flare=0.20, folds=0.030,
        sleeve_end=0.84, sleeve_r=0.048, sleeve_flare=0.012, collar_h=0.026,
    ))
    parts.extend(G.build_open_robe(
        'sheikh_kaftan', col, lm, p, M['wool'], '#748857', rig_obj,
        trim_mat=M['hessian'], trim_color='#E0C078', hem_z=0.075, ease=0.040, skirt_flare=0.28,
        open_rad=0.38, sleeve_end=0.72, sleeve_r=0.066, sleeve_flare=0.026,
    ))
    parts.extend(G.build_turban(
        'sheikh_imama', col, lm, F, M['linen'], '#F7F3EA', rig_obj,
        tarboush_mat=M['wool'], tarboush_color='#8F2929', wraps=4, puff=0.18,
    ))
    beard = HD.build_beard('sheikh_beard', col, lm['head_center'], lm['head_r'], F, M['hair'], '#CCC8C2', style='neat')
    R.skin_rigid(beard, rig_obj, 'head')
    parts.append(beard)
    return parts


def _outfit_aunt(col, lm, p, F, M, rig_obj):
    sk = F['skin']
    parts = []
    parts.extend(B.build_forearms_and_hands('aunt_arm', col, lm, p, M['skin'], sk, rig_obj, forearm_start=0.56))
    sk_ft, sh_ft = B.build_ankles_and_feet(
        'aunt_ft', col, lm, p, M['skin'], sk, M['leather'], '#7A4A2A', rig_obj, shoe_style='slipper', ankle_top=0.10
    )
    parts.extend(sk_ft)
    parts.extend(sh_ft)

    parts.extend(G.build_galabiya(
        'aunt_dress', col, lm, p, M['cotton'], '#DCA042', rig_obj,
        hem_z=0.045, ease=0.022, skirt_flare=0.32, folds=0.044, waist_cinch=0.80,
        sleeve_end=0.82, sleeve_r=0.045, sleeve_flare=0.018, collar_h=0.020,
        trim_mat=M['hessian'], trim_color='#F5E7C8', trim_style='cuff_hem',
    ))
    parts.extend(G.build_sash('aunt_sash', col, lm, p, M['hessian'], '#2A8A8B', rig_obj, ease=0.030, height=0.072, tails=True, tail_side=1.0))
    parts.extend(G.build_hijab(
        'aunt_hijab', col, lm, p, F, M['linen'], '#C26052', rig_obj,
        trim_mat=None, drop_front=0.21, drop_back=0.28, asymmetric_tail=True, bun_puff=0.24,
    ))
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
    """Build one complete rigged, animated v4 PBR character (no ink outlines) and return info dict."""
    cfg = CAST[key]
    p = cfg['props']
    F = dict(cfg['face'])
    col = L.fresh_collection('char_' + key)

    for act in list(bpy.data.actions):
        if act.name.startswith(key + '|'):
            bpy.data.actions.remove(act)

    lm = R.compute_landmarks(p)
    rig_obj = R.build_armature(key + '_rig', col, lm)
    M = _shared_mats(key, cfg)

    # 1) Sculpted 3D Head, Eyes, Lids, Brows, Talking Mouth
    head_obj = HD.build_head_mesh(key + '_head', col, lm['head_center'], lm['head_r'], F, M['face'])
    eyes_obj, lash_obj, lid_objs, lid_bones = HD.build_eyes_and_lids(
        key, col, lm['head_center'], lm['head_r'], F, M['eye'], M['skin'], M['hair']
    )
    brows_obj = HD.build_brows(key, col, lm['head_center'], lm['head_r'], F, M['hair'])
    mouth_obj, mouth_bone = HD.build_talking_mouth(key, col, lm['head_center'], lm['head_r'], F, M['hair'])

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

    parts = [head_obj, eyes_obj, lash_obj, brows_obj, mouth_obj] + [lobj for _, lobj in lid_objs]

    # 2) Body + Outfit parts
    parts.extend(OUTFITS[key](col, lm, p, F, M, rig_obj))

    # 3) Animations as NLA tracks
    A.animate(rig_obj, key, cfg['clips'], cfg.get('style', {}))

    # 4) Pose-aligned accessories (Grandpa Salim's staff)
    if key in POST_ANIM:
        parts.extend(POST_ANIM[key](col, lm, M, rig_obj))

    # 5) Join into one clean multi-material skinned mesh (zero outline hull)
    mesh_obj = L.join_objects(parts, key, col)
    L.bake_character_ao(mesh_obj, lm)
    HD.apply_soft_face_normals(mesh_obj, lm['head_center'], lm['head_r'], F)
    for m in list(mesh_obj.modifiers):
        if m.type == 'ARMATURE':
            m.object = rig_obj

    return {
        'key': key,
        'rig': rig_obj,
        'mesh': mesh_obj,
        'tris': L.tri_count(mesh_obj),
        'bones': L.bone_count(rig_obj),
        'height': p['height'],
        'expected_clips': list(cfg['clips']),
    }
