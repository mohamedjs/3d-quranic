# illustrations_scenes.py — the seven compositions (exec'd by illustrations.py; uses its helpers).

def bez(p0, p1, p2, p3, t):
    p0, p1, p2, p3 = map(Vector, (p0, p1, p2, p3)); u = 1 - t
    return p0 * u ** 3 + p1 * 3 * u * u * t + p2 * 3 * u * t * t + p3 * t ** 3

def desert(name, mat, x0=-900, x1=900, y0=-20, y1=2400, amp=4.0, nx=140, ny=110, flat_path=None, seed=1, wave=1.5):
    def fz(x, y):
        d = max(y, 1)
        z = amp * (fbm(x / 70, y / 55, 4, seed) - 0.5) * (1 + d / 300)
        z += wave * math.sin(x / 23 + y / 41)
        if flat_path:
            z *= flat_path(x, y)
        return z
    # denser rows near the camera
    bm = bmesh.new(); vs = []
    ys = [y0 + (y1 - y0) * (j / ny) ** 2.2 for j in range(ny + 1)]
    for y in ys:
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx; vs.append(bm.verts.new((x, y, fz(x, y))))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i; bm.faces.new((vs[a], vs[a + 1], vs[a + nx + 2], vs[a + nx + 1]))
    return obj(name, mesh_bm(name, bm, mat))

def ground_z(o, x, y, z0=500):
    """raycast straight down onto object o (world coords)"""
    mi = o.matrix_world.inverted()
    ok, loc, n, i = o.ray_cast(mi @ Vector((x, y, z0)), (mi.to_3x3() @ Vector((0, 0, -1))).normalized())
    return (o.matrix_world @ loc).z if ok else 0.0

# ------------------------------------------------------------------ 1. army
def fg_lip(name, mat, y=8.0, h=1.4, x0=-60, x1=60, seed=4, bumps=()):
    """dark near-ground dune lip across the bottom of frame (nearest depth layer)"""
    def fz(x, yy):
        z = h * math.exp(-((yy - y) / 3.0) ** 2) * (0.55 + 0.7 * fbm(x / 9, 0.5, 3, seed))
        for (bx, bw, bh) in bumps: z += bh * math.exp(-((x - bx) / bw) ** 2) * math.exp(-((yy - y) / 3.5) ** 2)
        return z - 0.3
    return heightfield(name, x0, x1, y - 8, y + 8, 120, 24, fz, mat)

@scene
def sc_army():
    P.update(sun=(-0.34, 1.0, 0.17), sun_r=0.04, clouds=0.75, cloud_cov=0.5, cloud_scale=1.0,
             sky=[(-0.12, '#e6a86c'), (0.0, '#fbd08a'), (0.05, '#f3a860'), (0.16, '#dd7f5c'), (0.38, '#a06f7e'), (0.8, '#4c4775')],
             fog=1 / 1800, fog_ground=1.8, fog_h=5.0, glow_amt=0.8, beams=0.3)
    sand = toon('sand', '#c98a52', nscale=0.08, namt=0.18, rim=0.3)
    dark = toon('dune_dark', '#6a3e26', nscale=0.3, namt=0.15, rim=1.2)
    mfar = toon('mnt_far', '#8a7390', nscale=0.01, namt=0.1, rim=0.3)
    mmid = toon('mnt_mid', '#6e4a44', nscale=0.02, namt=0.15, rim=0.6)
    skin = toon('ele', '#6f5a4c', nscale=1.2, namt=0.1, rim=1.3)
    skin_lead = toon('ele_lead', '#948272', nscale=1.2, namt=0.1, rim=1.4)
    ivory = toon('ivory', '#efe2c4', namt=0.03, rim=0.8)
    red = toon('cloth_red', '#b33a2a', namt=0.08, rim=1.0)
    gold = toon('gold', '#d9a441', namt=0.05, rim=1.2)
    wood = toon('wood', '#5a3a26', namt=0.1, rim=0.8)
    sold = toon('soldier', '#46302a', namt=0.06, rim=1.4)
    dust = dust_mat('dust', '#f2c08a', 0.35, fog=0.7)

    camera((0, -6, 1.7), (-3, 60, 4.5), lens=30, shift=(0, 0.1))
    # column marches from the near right toward the far-left hills of Makkah; t=0 = vanguard (far)
    path = lambda t: bez((-330, 560, 0), (-160, 90, 0), (-60, 22, 0), (22, 20, 0), t)
    pts = [path(k / 60).xy for k in range(61)]
    def flat(x, y):
        best = min((Vector((x, y)) - q).length for q in pts)
        return min(1.0, 0.2 + best / 50)
    gnd = desert('desert', sand, flat_path=flat, amp=5.0)
    ridge('mnt_far', 1900, 5600, 800, 360, mfar, seed=3, x0=-300, freq=4.0, base=0.3, peaks=[(-0.06, 0.04, 0.35), (0.07, 0.05, 0.3)])
    ridge('mnt_mid', 950, 2400, 380, 170, mmid, seed=8, x0=-700, freq=5.0, base=0.2, peaks=[(0.15, 0.05, 0.5), (0.3, 0.05, 0.3)])
    ridge('hills', 460, 1500, 200, 45, mmid, seed=11, x0=300, freq=4.0, base=0.1)
    for i, (x, y, sc_) in enumerate(((-5.4, 4.5, 0.55), (-4.1, 4.2, 0.3), (-7.5, 6, 0.9), (6.5, 5, 0.4))):
        o = inst('rock%d' % i, rock_mesh('rock%d' % i, (sc_ * 1.6, sc_, sc_ * 0.7), seed=i), (x, y, 0.0)); o.data.materials.append(dark)
    ele_std = elephant('EleA', skin, tusk=ivory, blanket=red, trim=gold, howdah=wood, trunk='down', eye=False)
    ele_up = elephant('EleB', skin, tusk=ivory, blanket=red, trim=gold, trunk='up', eye=False)
    ele_lead = elephant('EleL', skin_lead, tusk=ivory, blanket=red, trim=gold, howdah=wood, trunk='up', eye=True)
    soldiers = [soldier_mesh('sold%d' % i, 'walk', spear=(i % 3 != 2), shield=(i % 2 == 0)) for i in range(3)]
    for m in soldiers: m.materials.append(sold)
    ban = banner_mesh('banner', seed=0.0); ban.materials.append(wood); ban.materials.append(red)
    ban2 = banner_mesh('banner2', seed=1.7); ban2.materials.append(wood); ban2.materials.append(gold)
    puff = puff_mesh('puff', 1.0, 3); puff.materials.append(dust)
    rnd = random.Random(4)
    ts = [0.1, 0.25, 0.4, 0.53, 0.65, 0.76, 0.85, 0.915, 0.975]
    for k, t in enumerate(ts):
        p = path(t); p2 = path(t - 0.01); ang = math.atan2((p2 - p).y, (p2 - p).x)
        z = ground_z(gnd, p.x, p.y)
        big = (k == 6)
        parts = ele_lead if big else (ele_std if k % 2 else ele_up)
        place(parts, 'ele%d' % k, (p.x, p.y, z - 0.1), ang, 1.25 if big else 1.0)
        for j in range(2):
            q = path(min(t + 0.03 + j * 0.02, 1)); off = Vector((rnd.uniform(-3, 3), rnd.uniform(2, 6), 0)) * (1 + (1 - t) * 3)
            inst('puff%d_%d' % (k, j), puff, (q.x + off.x, q.y + off.y, ground_z(gnd, q.x, q.y) + 0.3),
                 (0, 0, rnd.uniform(0, 3)), (2.5 + 7 * (1 - t)) * rnd.uniform(0.8, 1.2))
    for i in range(220):
        t = rnd.uniform(0.0, 1.0); p = path(t); p2 = path(max(t - 0.01, 0)); dirv = (p2 - p).normalized()
        if dirv.length == 0: continue
        side = Vector((-dirv.y, dirv.x, 0)); lat = rnd.choice((-1, 1)) * rnd.uniform(3.2, 5 + 12 * (1 - t))
        pos = p + side * lat
        if pos.y < 9 or (pos - Vector((0, -6, 0))).length < 12: continue
        ang = math.atan2(dirv.y, dirv.x)
        inst('s%d' % i, soldiers[i % 3], (pos.x, pos.y, ground_z(gnd, pos.x, pos.y) - 0.05), (0, 0, ang), rnd.uniform(0.9, 1.1))
        if i % 8 == 0:
            inst('b%d' % i, ban if i % 16 else ban2, (pos.x + 0.6, pos.y, ground_z(gnd, pos.x, pos.y)), (0, 0, ang + math.pi), 1.1)


# ------------------------------------------------------------------ shared: Makkah valley
def house_mesh(name, w, d, h, seed=0, upper=True):
    """flat-roofed mud-brick house; mat 0 wall, 1 dark openings, 2 roof lip/wood"""
    rnd = random.Random(seed); bm = bmesh.new()
    bm_cube(bm, TRS((0, 0, h / 2), s=(w, d, h)))
    if upper and rnd.random() < 0.6:
        uw, ud, uh = w * rnd.uniform(0.35, 0.55), d * rnd.uniform(0.4, 0.6), h * rnd.uniform(0.45, 0.7)
        bm_cube(bm, TRS((rnd.choice((-1, 1)) * (w - uw) / 2, (d - ud) / 2, h + uh / 2), s=(uw, ud, uh)))
    st = set(bm.faces)
    bm_cube(bm, TRS((rnd.uniform(-0.25, 0.25) * w, -d / 2 - 0.02, 0.9), s=(0.9, 0.12, 1.8)))
    for k in range(rnd.randint(1, 3)):
        bm_cube(bm, TRS((rnd.uniform(-0.4, 0.4) * w, -d / 2 - 0.02, h * rnd.uniform(0.55, 0.8)), s=(0.45, 0.12, 0.45)))
    bm_matidx(bm, 1, st); st = set(bm.faces)
    bm_cube(bm, TRS((0, 0, h + 0.1), s=(w + 0.25, d + 0.25, 0.2)))
    bm_matidx(bm, 2, st)
    return mesh_bm(name, bm, smooth=False)

def kaaba_parts(black, gold, stone, pale):
    out = []
    bm = bmesh.new(); bm_cube(bm, TRS((0, 0, 6.55), s=(11.0, 12.8, 13.1))); out.append((mesh_bm('kaaba', bm, smooth=False), black))
    bm = bmesh.new(); bm_cube(bm, TRS((0, 0, 9.3), s=(11.12, 12.92, 0.95)))
    bm_cube(bm, TRS((5.56, -2.4, 3.9), s=(0.1, 2.0, 3.4)))       # door (faces +X)
    bm_cube(bm, TRS((5.56, -2.4, 5.7), s=(0.12, 2.4, 0.2)))
    out.append((mesh_bm('kaaba_gold', bm, smooth=False), gold))
    bm = bmesh.new(); bm_cube(bm, TRS((0, 0, 0.25), s=(11.8, 13.6, 0.5))); out.append((mesh_bm('kaaba_base', bm, smooth=False), stone))
    bm = bmesh.new()  # Hijr Ismail: low semicircular wall on the -Y side... placed on +Y side
    for i in range(25):
        a0 = math.pi * i / 25; a1 = math.pi * (i + 1) / 25
        p0 = Vector((math.cos(a0) * 5.2, 6.4 + math.sin(a0) * 7.5, 0.6)); p1 = Vector((math.cos(a1) * 5.2, 6.4 + math.sin(a1) * 7.5, 0.6))
        c = (p0 + p1) / 2; ang = math.atan2((p1 - p0).y, (p1 - p0).x)
        bm_cube(bm, TRS(c, (0, 0, ang), ((p1 - p0).length + 0.1, 0.9, 1.3)))
    out.append((mesh_bm('hijr', bm, smooth=False), pale))
    return out

def makkah_valley(mats, seed=2, n_houses=90, r0=34, r1=190, hills=True, near_cut=None):
    """ground bowl + mud-brick town ringed around the Kaaba + dark craggy hills around the valley"""
    rnd = random.Random(seed)
    def fz(x, y):
        r = math.hypot(x, y)
        z = 0.0015 * max(r - 80, 0) ** 1.5 + 2.0 * (fbm(x / 60, y / 60, 3, seed) - 0.5)
        return z
    gnd = heightfield('valley', -900, 900, -900, 1400, 150, 150, fz, mats['ground'])
    # plaza (mataf) — slightly paler stone disc
    bm = bmesh.new(); bmesh.ops.create_circle(bm, segments=48, radius=28, cap_ends=True, matrix=TRS((0, 0, 0.05)))
    obj('mataf', mesh_bm('mataf', bm, mats['plaza'], smooth=False))
    hv = [house_mesh('house%d' % i, rnd.uniform(5, 9), rnd.uniform(5, 8), rnd.uniform(3.5, 7.5), seed=i) for i in range(9)]
    for i, m in enumerate(hv):
        for k in (('wall', 'wall2', 'wall3')[i % 3], 'dark', 'lip'): m.materials.append(mats[k])
    placed = 0; tries = 0
    while placed < n_houses and tries < 4000:
        tries += 1
        a = rnd.uniform(0, 2 * math.pi); r = r0 + (r1 - r0) * rnd.random() ** 0.8
        x, y = math.cos(a) * r, math.sin(a) * r
        if near_cut and near_cut(x, y): continue
        z = ground_z(gnd, x, y)
        inst('h%d' % placed, hv[placed % len(hv)], (x, y, z - 0.3), (0, 0, a + math.pi / 2 + rnd.uniform(-0.2, 0.2)), rnd.uniform(0.9, 1.25))
        placed += 1
    if hills:
        # dark craggy hills ringing the valley, paler further back
        ridge('hill_back', 420, 1800, 420, 130, mats['hill'], seed=seed + 1, x0=0, freq=7.0, base=0.2, peaks=[(-0.18, 0.06, 0.4), (0.22, 0.05, 0.5)], rough=0.45)
        ridge('hill_far', 1000, 3600, 600, 230, mats['hill_far'], seed=seed + 2, x0=0, freq=5.0, base=0.3, peaks=[(0.05, 0.05, 0.3)])
        ridge('hill_farthest', 1900, 6000, 900, 500, mats['hill_far2'], seed=seed + 3, x0=0, freq=4.0, base=0.35)
        # left / right hills closer in, framing the valley
        ridge('hill_left', 170, 700, 260, 120, mats['hill'], seed=seed + 5, x0=-560, freq=6.0, base=0.25, rough=0.5, peaks=[(0.2, 0.08, 0.4)])
        ridge('hill_right', 120, 700, 260, 100, mats['hill'], seed=seed + 6, x0=560, freq=6.0, base=0.25, rough=0.5, peaks=[(-0.25, 0.08, 0.5)])
    return gnd

def makkah_mats(ground='#a87a52', wall='#b98a60', hill='#4a3434', hill_far='#6a5a78', hill_far2='#8f8fb0'):
    return dict(ground=toon('ground', ground, nscale=0.05, namt=0.15, rim=0.0),
                plaza=toon('plaza', '#cdb08a', nscale=0.2, namt=0.1, rim=0.2),
                wall=toon('wall', wall, nscale=0.6, namt=0.12, rim=0.9),
                wall2=toon('wall2', '#c9a47a', nscale=0.6, namt=0.12, rim=0.9),
                wall3=toon('wall3', '#8a6448', nscale=0.6, namt=0.12, rim=0.9),
                dark=toon('opening', '#2a1a12', namt=0.0, rim=0.0),
                lip=toon('lip', '#7a5236', namt=0.08, rim=0.6),
                hill=toon('hill', hill, nscale=0.02, namt=0.18, rim=0.03),
                hill_far=toon('hill_far', hill_far, nscale=0.01, namt=0.12, rim=0.02),
                hill_far2=toon('hill_far2', hill_far2, nscale=0.01, namt=0.08, rim=0.0))

# ------------------------------------------------------------------ 2. kaaba (dawn)
@scene
def sc_kaaba():
    P.update(sun=(0.25, 1.0, 0.04), sun_r=0.035,
             sky=[(-0.12, '#c98a6a'), (0.0, '#f6c88a'), (0.035, '#eea070'), (0.08, '#b87a8c'), (0.16, '#6a6a9a'), (0.4, '#343a6a'), (0.8, '#1e2248')],
             glow='#ffcf88', glow_amt=0.8, glow_pow=22.0, core_amt=0.9, core_pow=120.0, clouds=0.55, cloud_cov=0.55, cloud_lit='#ffc98a', cloud_dark='#6c5a86', cloud_scale=1.4,
             fog=1 / 6000, fog_ground=1.2, fog_h=15.0, lit=(1.1, 0.95, 0.85), shadow=(0.4, 0.36, 0.48), shade='#2a2238', shade_mix=0.35,
             rim='#ffc27a', rim_amt=1.6, sun_str=2.4, amb=0.06, beams=0.0, gain=(1.04, 1.0, 0.97))
    mats = makkah_mats(hill='#3a2c30', hill_far='#5a5076', hill_far2='#8a88ac', wall='#a88060')
    black = toon('kaaba', '#141214', namt=0.03, rim=1.8, shadow='#0c0a0e', lit='#2a2628')
    gold = toon('kgold', '#e2b04a', namt=0.03, rim=1.5, emit=1.5, lit='#f4c766', shadow='#b07a2a')
    stone = toon('kstone', '#8a7a6a', namt=0.08, rim=0.6)
    pale = toon('kpale', '#e8dcc6', namt=0.05, rim=0.6)
    makkah_valley(mats, seed=2, n_houses=110, near_cut=lambda x, y: (y < -20 and abs(x - 0.29 * y) < 22 + 0.1 * abs(y)))
    place(kaaba_parts(black, gold, stone, pale), 'kaaba', (0, 0, 0), math.radians(-25))
    camera((-60, -210, 20), (0, 0, 8), lens=50, shift=(0, 0.22))
    # near dark rocky slope in the foreground (camera stands on a hillside)
    dk = toon('fg_rock', '#3a2620', nscale=0.3, namt=0.18, rim=1.4)
    heightfield('fg_slope', -110, 10, -205, -175, 60, 16, lambda x, y: 14 + 4 * math.exp(-((x + 85) / 16) ** 2) - (y + 205) * 0.5 + 2.0 * fbm(x / 6, y / 6, 3, 9), dk)
    for i, (x, y, z, sz) in enumerate(((-84, -190, 15.5, 2.6), (-74, -193, 14.5, 1.4), (-95, -186, 16, 2.0))):
        o = inst('fgr%d' % i, rock_mesh('fgr%d' % i, (sz * 1.4, sz, sz * 0.8), seed=i + 3), (x, y, z)); o.data.materials.append(dk)
    # a few birds for life
    bmesh_bird = bird_mesh('dawnbird', 0.5, stones=False); _m = toon('bird', '#2a1c1c', namt=0, rim=1.0)
    for _k in range(3): bmesh_bird.materials.append(_m)
    rnd = random.Random(3)
    for i in range(7):
        inst('bd%d' % i, bmesh_bird, (rnd.uniform(-60, 40), rnd.uniform(40, 160), rnd.uniform(55, 85)), (0.3, 0, rnd.uniform(-0.3, 0.3)), rnd.uniform(2.5, 3.5))

# ------------------------------------------------------------------ 3. elephant kneels
@scene
def sc_elephant():
    P.update(sun=(0.55, 1.0, 0.1), sun_r=0.04, clouds=0.6, cloud_cov=0.52,
             sky=[(-0.12, '#e6a86c'), (0.0, '#fbd08a'), (0.06, '#f2ae66'), (0.18, '#de8a64'), (0.4, '#a0708a'), (0.85, '#4c4775')],
             fog=1 / 900, fog_ground=1.5, fog_h=5.0, beams=0.3, rim_amt=1.7)
    sand = toon('sand', '#c68a56', nscale=0.1, namt=0.18, rim=0.3)
    skin = toon('ele', '#8a7466', nscale=1.0, namt=0.1, rim=1.6)
    ivory = toon('ivory', '#efe2c4', namt=0.03, rim=0.8)
    red = toon('cloth_red', '#b33a2a', namt=0.08, rim=1.0)
    gold = toon('gold', '#d9a441', namt=0.05, rim=1.2)
    sold = toon('soldier', '#46302a', namt=0.06, rim=1.5)
    rope = toon('rope', '#6a4a30', namt=0, rim=0.8)
    mfar = toon('mnt_far', '#8a7390', nscale=0.01, namt=0.1, rim=0.3)
    mmid = toon('mnt_mid', '#5a3c3c', nscale=0.02, namt=0.15, rim=0.7)
    desert('desert', sand, amp=1.2, x0=-600, x1=600, y1=1500, nx=120, ny=90, wave=0.1, flat_path=lambda x, y: min(1.0, max(0.05, (y - 20) / 60)))
    ridge('mnt_mid', 520, 1600, 300, 120, mmid, seed=21, x0=250, freq=6.0, base=0.2, peaks=[(0.1, 0.05, 0.5)], rough=0.2)
    ridge('mnt_far', 1300, 4000, 600, 300, mfar, seed=22, x0=300, freq=4.0, base=0.3)
    # Mahmoud kneels, facing Makkah (to the right, towards the glowing hills)
    place(elephant('Mahmoud', skin, kneel=True, tusk=ivory, blanket=red, trim=gold, trunk='ground'), 'mahmoud', (0.5, 14, 0), 0.0, 1.15)
    push = soldier_mesh('push', 'reach', shield=False, spear=False); push.materials.append(sold)
    haul = soldier_mesh('haul', 'haul', shield=False, spear=False); haul.materials.append(sold)
    walk = soldier_mesh('walk', 'walk'); walk.materials.append(sold)
    yaw = 0.0
    # pushers lean into the rump; haulers lean away toward Makkah with ropes over their shoulders
    for i, (x, y) in enumerate(((-3.0, 13.2), (-2.8, 15.0), (-3.4, 14.2))):
        inst('pu%d' % i, push, (x, y, 0), (0, math.radians(16), yaw), 1.0)
    for i, (x, y) in enumerate(((5.6, 13.0), (6.7, 14.6), (7.8, 16.0))):
        inst('pl%d' % i, haul, (x, y, 0), (0, math.radians(22), yaw), 1.0)
        a = Vector((2.2, 14.0 + (y - 14.6) * 0.3, 2.0)); b = Vector((x + 0.75, y, 1.45)); m_ = (a + b) / 2 - Vector((0, 0, 0.12))
        bm = bmesh.new(); bm_seg(bm, a, m_, 0.022, 0.022, 6); bm_seg(bm, m_, b, 0.022, 0.022, 6); obj('rope%d' % i, mesh_bm('rope%d' % i, bm, rope))
    for i, (x, y, r) in enumerate(((-9, 24, 0.3), (-12, 30, 0.1), (12, 30, 3.3), (-6, 40, 0.2), (15, 45, 3.0), (-18, 45, 0.3))):
        inst('w%d' % i, walk, (x, y, 0), (0, 0, r), 1.0)
    ban = banner_mesh('banner', seed=0.5); ban.materials.append(toon('wood', '#5a3a26')); ban.materials.append(red)
    inst('ban1', ban, (-10.5, 26, 0), (0, 0, math.pi), 1.1); inst('ban2', ban, (-19, 46, 0), (0, 0, math.pi), 1.1)
    dust = dust_mat('dust', '#f2c08a', 0.3, fog=0.7); puff = puff_mesh('puff', 1.0, 5); puff.materials.append(dust)
    for i, (x, y, sc_) in enumerate(((-15, 60, 5), (-40, 90, 8), (5, 75, 6))):
        inst('puff%d' % i, puff, (x, y, 0.5), (0, 0, i), sc_)
    camera((1.2, -3.5, 1.2), (1.6, 20, 2.6), lens=34, shift=(0, 0.06))

# ------------------------------------------------------------------ 4. birds
@scene
def sc_birds():
    P.update(sun=(-0.45, 1.0, 0.16), sun_r=0.04, clouds=1.0, cloud_cov=0.46, cloud_scale=0.9,
             cloud_lit='#ffc47a', cloud_dark='#5a3a5a',
             sky=[(-0.12, '#d9905a'), (0.0, '#f6b96a'), (0.06, '#e98a54'), (0.2, '#b05a50'), (0.45, '#5a3a5c'), (0.9, '#22203e')],
             glow='#ffc070', glow_amt=0.75, fog=1 / 1400, fog_ground=1.6, fog_h=5.0, beams=0.0, rim_amt=1.6,
             bloom=0.6)
    sand = toon('sand', '#9a6038', nscale=0.1, namt=0.18, rim=0.3)
    body = toon('bird', '#1e1418', namt=0.0, rim=0.45, lit='#2e2020', shadow='#22161a')
    wing = toon('wing', '#241818', namt=0.0, rim=0.0, flat=True, lit='#2a1c1c')
    stone = toon('stone', '#e0a860', namt=0.0, rim=0.8, emit=1.15, fog=0.5)
    sold = toon('soldier', '#2e1f1c', namt=0.05, rim=1.2)
    skin = toon('ele', '#3a2c2a', namt=0.08, rim=1.2)
    red = toon('cloth_red', '#7a2a22', namt=0.08, rim=0.8)
    mmid = toon('mnt_mid', '#4a2e34', nscale=0.02, namt=0.15, rim=0.6)
    desert('desert', sand, amp=2.5, x0=-800, x1=800, y1=2000, nx=100, ny=80)
    ridge('mnt_mid', 900, 3000, 400, 110, mmid, seed=31, x0=0, freq=5.0, base=0.25)
    # army on the horizon line
    walk = soldier_mesh('walk', 'walk'); walk.materials.append(sold)
    rnd = random.Random(8)
    for i in range(160):
        x = rnd.uniform(-45, 50); y = rnd.uniform(34, 80)
        inst('s%d' % i, walk, (x, y, 0), (0, 0, math.pi + rnd.uniform(-0.3, 0.3)), rnd.uniform(0.9, 1.1))
    ele = elephant('EleB', skin, blanket=red, trunk='up', eye=False, tusk=toon('ivory', '#cbb898', namt=0))
    for i, (x, y) in enumerate(((-16, 42), (6, 50), (24, 58), (-34, 66))):
        place(ele, 'ele%d' % i, (x, y, 0), math.pi + rnd.uniform(-0.3, 0.3), 1.0)
    # flocks: streams of birds from the upper left (the sea) sweeping over the army
    meshes = []
    for k, f in enumerate((0.55, 0.15, -0.35)):
        m = bird_mesh('bird%d' % k, f); m.materials.append(body); m.materials.append(stone); m.materials.append(wing); meshes.append(m)
    cam = Vector((0, -8, 1.2))
    for i in range(700):
        t = rnd.random()
        base = Vector((-120 + 200 * t, 20 + 90 * rnd.random() ** 0.7, 18 + 55 * (1 - t) * rnd.uniform(0.6, 1.2) + rnd.uniform(0, 18)))
        if (base - cam).length < 14: continue
        dirv = Vector((1, 0.25, -0.35)).normalized()
        ang = math.atan2(dirv.y, dirv.x)
        inst('b%d' % i, meshes[i % 3], base, (rnd.uniform(-0.3, 0.3), 0.35, ang + rnd.uniform(-0.3, 0.3)), rnd.uniform(2.4, 3.4))
    # a few big hero birds close to camera
    for i, (x, y, z, sc_) in enumerate(((-7, 14, 9.5, 3.4), (-2, 18, 12.5, 3.0), (-11, 22, 13.5, 3.0), (4, 20, 8.5, 2.8), (-4.5, 11, 7.0, 2.6))):
        inst('hb%d' % i, meshes[i % 3], (x, y, z), (0.1, 0.35, math.radians(15)), sc_)
    camera((0, -8, 1.2), (-6, 60, 20), lens=26)

# ------------------------------------------------------------------ 5. straw (ka'asf ma'kul)
def straw_field(name, mat, x0, x1, y0, y1, n, rnd, trample=None, maxh=0.45):
    bm = bmesh.new()
    for i in range(n):
        y = y0 + (y1 - y0) * rnd.random() ** 1.6; x = x0 + (x1 - x0) * rnd.random()
        tr = trample(x, y) if trample else 0.0
        for b in range(rnd.randint(5, 10)):
            h = rnd.uniform(0.08, maxh) * (1 - 0.6 * tr) * (0.5 if rnd.random() < 0.35 else 1.0)
            ang = rnd.uniform(0, 2 * math.pi); lean = rnd.uniform(0.05, 0.5) + tr * rnd.uniform(0.6, 1.3)
            bx, by = x + rnd.uniform(-0.06, 0.06), y + rnd.uniform(-0.06, 0.06)
            w = rnd.uniform(0.008, 0.016); segs = 3
            d = Vector((math.cos(ang), math.sin(ang), 0)); side = Vector((-d.y, d.x, 0))
            prev = None
            for k in range(segs + 1):
                t = k / segs; bend = lean * t * (1 + 0.6 * t)
                c = Vector((bx, by, 0)) + d * math.sin(bend) * h * t + Vector((0, 0, math.cos(bend) * h * t))
                ww = w * (1 - 0.6 * t)
                a, b_ = bm.verts.new(c - side * ww), bm.verts.new(c + side * ww)
                if prev: bm.faces.new((prev[0], prev[1], b_, a))
                prev = (a, b_)
    return obj(name, mesh_bm(name, bm, mat, smooth=False))

def lying_straw(name, mat, x0, x1, y0, y1, n, rnd):
    bm = bmesh.new()
    for i in range(n):
        y = y0 + (y1 - y0) * rnd.random() ** 1.5; x = x0 + (x1 - x0) * rnd.random()
        a = rnd.uniform(0, math.pi); L = rnd.uniform(0.08, 0.35)
        p = Vector((x, y, 0.01)); q = p + Vector((math.cos(a), math.sin(a), rnd.uniform(0, 0.03))) * L
        bm_seg(bm, p, q, 0.008, 0.006, 4)
    return obj(name, mesh_bm(name, bm, mat, smooth=False))

def straw_heaps(name, mat, centers, n, rnd, spread=0.35):
    bm = bmesh.new()
    for i in range(n):
        cx, cy, r = centers[i % len(centers)]
        x = cx + rnd.gauss(0, r * spread * 2); y = cy + rnd.gauss(0, r * spread * 2)
        d = math.hypot(x - cx, y - cy) / r
        z = max(0.0, 0.12 * r * (1 - d * d)) * rnd.random()
        a = rnd.uniform(0, math.pi); tilt = rnd.uniform(-0.5, 0.5); L = rnd.uniform(0.06, 0.26)
        p = Vector((x, y, z + 0.01)); q = p + Vector((math.cos(a), math.sin(a), tilt * 0.3)) * L
        bm_seg(bm, p, q, 0.009, 0.006, 4)
    return obj(name, mesh_bm(name, bm, mat, smooth=False))

@scene
def sc_straw():
    P.update(sun=(-0.55, 1.0, 0.13), sun_r=0.035, clouds=0.35, cloud_cov=0.6, cloud_scale=1.2,
             sky=[(-0.12, '#e8c49a'), (0.0, '#fbe3b4'), (0.05, '#f6d49a'), (0.18, '#e2bfa0'), (0.45, '#a6aecb'), (0.9, '#7486b0')],
             glow='#ffe0a0', glow_amt=0.7, core_amt=0.8, fog=1 / 1500, fog_ground=1.0, fog_h=4.0, beams=0.2,
             lit=(1.15, 1.03, 0.85), shadow=(0.55, 0.45, 0.42), shade='#5a3e36', rim='#ffe2a0', rim_amt=1.5, sun_str=3.0, amb=0.45,
             bands=(0.12, 0.36), kuwa=4, vign=0.5)
    earth = toon('earth', '#9a7048', nscale=0.8, namt=0.22, rim=0.2)
    strawm = toon('straw', '#dcb468', nscale=3.0, namt=0.2, rim=1.6)
    strawd = toon('straw_dry', '#b89050', nscale=3.0, namt=0.2, rim=1.3)
    metal = toon('metal', '#7a5a3a', nscale=4.0, namt=0.1, rim=2.0, lit='#b08a58', shadow='#4a3424')
    wood = toon('wood', '#6a4830', nscale=4.0, namt=0.1, rim=1.4)
    hills = toon('hills', '#b89070', nscale=0.02, namt=0.1, rim=0.3)
    mfar = toon('mnt_far', '#9a94b0', nscale=0.01, namt=0.08, rim=0.2)
    rnd = random.Random(12)
    heightfield('earth', -60, 60, -2, 160, 110, 110, lambda x, y: 0.06 * fbm(x / 0.8, y / 0.8, 3, 2) + 0.004 * max(y - 20, 0) ** 1.4 * (0.5 + fbm(x / 30, y / 30, 3, 5)), earth)
    ridge('hills', 170, 700, 220, 25, hills, seed=41, x0=-60, sharp=False, freq=3.0, base=0.3)
    ridge('mnt_far', 700, 3000, 500, 170, mfar, seed=42, x0=100, freq=4.0, base=0.3)
    # stubble: short broken stalks, some trampled flat along a track
    tr = lambda x, y: max(0.0, 1 - abs(x - 0.25 * y + 0.6) / 0.9)
    straw_field('stubble', strawm, -5, 5, 0.25, 12, 3200, rnd, trample=lambda x, y: min(1.0, tr(x, y)), maxh=0.24)
    straw_field('stubble_mid', strawd, -18, 18, 10, 40, 2600, rnd, maxh=0.22)
    straw_field('stubble_far', strawd, -40, 40, 38, 90, 1800, rnd, maxh=0.3)
    # chewed straw lying about and in little heaps
    lying_straw('lying', strawm, -3.5, 3.5, 0.15, 7, 5000, rnd)
    lying_straw('lying2', strawd, -3.5, 3.5, 0.15, 7, 3000, rnd)
    straw_heaps('heaps', strawm, [(-0.9, 1.3, 0.5), (1.3, 2.6, 0.6), (-1.8, 3.6, 0.7), (0.6, 4.8, 0.5)], 5000, rnd)
    # the lone empty helmet, tipped over and half-buried in straw
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=14, radius=0.14)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.01], context='VERTS')
    bm_cone(bm, TRS((0, 0, 0.0)), 0.175, 0.14, 0.03, 28, caps=False)
    bm_cone(bm, TRS((0, 0, 0.17)), 0.035, 0.0, 0.09, 10)
    bm_cube(bm, TRS((0.14, 0, -0.03), s=(0.02, 0.035, 0.1)))
    helm = obj('helmet', mesh_bm('helmet', bm, metal))
    helm.location = (0.3, 1.6, -0.02); helm.scale = (1.5, 1.5, 1.5); helm.rotation_euler = (math.radians(-22), math.radians(14), math.radians(35))
    # a broken spear: shaft stuck in the ground at an angle + the broken piece lying down
    bm = bmesh.new(); bm_seg(bm, (0, 0, -0.2), (0, 0, 0.62), 0.02, 0.018, 8)
    sp = obj('spear', mesh_bm('spear', bm, wood)); sp.location = (-0.75, 2.9, 0); sp.rotation_euler = (math.radians(-22), math.radians(-30), 0)
    bm = bmesh.new(); bm_seg(bm, (0, 0, 0), (0.62, 0, 0), 0.018, 0.018, 8); st = set(bm.faces)
    bm_cone(bm, seg_matrix((0.62, 0, 0), (0.84, 0, 0.0)), 0.04, 0.0, 1.0, 8); bm_matidx(bm, 1, st)
    sp2 = obj('spear2', mesh_bm('spear2', bm, [wood, metal])); sp2.location = (-0.55, 1.35, 0.03); sp2.rotation_euler = (0, 0, math.radians(-150))
    bb = bird_mesh('calm_bird', 0.4, stones=False); _m = toon('bird', '#5a4a4a', namt=0, rim=0.8)
    for _k in range(3): bb.materials.append(_m)
    for i in range(5):
        inst('cb%d' % i, bb, (rnd.uniform(-20, 10), rnd.uniform(40, 70), rnd.uniform(6, 11)), (0.2, 0, rnd.uniform(-0.3, 0.3)), 1.6)
    cam = camera((0.05, -0.25, 0.62), (-0.25, 8, -0.6), lens=30, shift=(0, 0.05))
    cam.data.dof.use_dof = True; cam.data.dof.focus_distance = 1.9; cam.data.dof.aperture_fstop = 3.5

# ------------------------------------------------------------------ 6. year of the elephant — Makkah, peaceful dawn
@scene
def sc_year():
    P.update(sun=(-0.2, 1.0, 0.16), sun_r=0.045,
             sky=[(-0.12, '#f0b88a'), (0.0, '#ffe0a8'), (0.05, '#fbc486'), (0.14, '#eea88e'), (0.32, '#a9a3c4'), (0.8, '#6f86b8')],
             glow='#ffe0a0', glow_amt=0.85, glow_pow=10.0, core='#fff6d8', core_amt=1.0, clouds=0.5, cloud_cov=0.56, cloud_lit='#ffe0b0', cloud_dark='#b89aae',
             fog=1 / 5000, fog_ground=1.6, fog_h=20.0, lit=(1.15, 1.02, 0.88), shadow=(0.5, 0.44, 0.52), shade='#40385a', shade_mix=0.35,
             rim='#ffd890', rim_amt=1.7, sun_str=2.6, amb=0.1, beams=0.0, bloom=0.6, gain=(1.05, 1.01, 0.97))
    mats = makkah_mats(wall='#c49a70', hill='#5a4448', hill_far='#8a7a96', hill_far2='#b0aac8')
    black = toon('kaaba', '#141214', namt=0.03, rim=1.8, shadow='#100c10', lit='#2e2a2c')
    gold = toon('kgold', '#e2b04a', namt=0.03, rim=1.5, emit=1.6, lit='#f4c766', shadow='#b07a2a')
    stone = toon('kstone', '#8a7a6a', namt=0.08, rim=0.6)
    pale = toon('kpale', '#eee2cc', namt=0.05, rim=0.6)
    makkah_valley(mats, seed=5, n_houses=140, r1=230, near_cut=lambda x, y: (y < -20 and abs(x + 0.077 * y) < 22 + 0.1 * abs(y)))
    place(kaaba_parts(black, gold, stone, pale), 'kaaba', (0, 0, 0), math.radians(-20))
    # a few palms at the valley edges
    pm = {'bark': toon('bark', '#6a4a30', rim=1.0), 'frond': toon('frond', '#5f7f32', rim=1.2, nscale=2.0), 'dates': toon('dates', '#a0502a')}
    palm = import_glb('palm_a', pm); palm2 = import_glb('palm_b', pm)
    rnd = random.Random(6)
    for i in range(14):
        a = rnd.uniform(0.6, 2.6) + (math.pi if i % 2 else 0); r = rnd.uniform(60, 200)
        inst('palm%d' % i, palm if i % 3 else palm2, (math.cos(a) * r, math.sin(a) * r, 0), (0, 0, rnd.uniform(0, 6)), rnd.uniform(1.0, 1.4))
    # doves circling in the morning light
    bb = bird_mesh('dove', 0.5, stones=False); _m = toon('dove', '#f4eadc', namt=0, rim=1.2, fog=0.5)
    for _k in range(3): bb.materials.append(_m)
    for i in range(9):
        inst('dv%d' % i, bb, (rnd.uniform(-70, 40), rnd.uniform(-60, 80), rnd.uniform(45, 75)), (0.2, rnd.uniform(-0.3, 0.3), rnd.uniform(0, 6)), 3.0)
    # near hillside with warm rocks (foreground layer) + camera high on the slope
    dk = toon('fg_rock', '#4a3026', nscale=0.3, namt=0.18, rim=1.5)
    heightfield('fg_slope', -30, 90, -270, -235, 60, 20, lambda x, y: 20 - (y + 270) * 0.5 + 3 * fbm(x / 8, y / 8, 3, 7) + 6 * math.exp(-((x - 45) / 12) ** 2), dk)
    for i, (x, y, z, sz) in enumerate(((52, -250, 19, 3.0), (42, -252, 18, 1.6), (70, -248, 17, 2.2))):
        o = inst('fgr%d' % i, rock_mesh('fgr%d' % i, (sz * 1.4, sz, sz * 0.8), seed=i + 7), (x, y, z)); o.data.materials.append(dk)
    camera((20, -260, 26), (0, 0, 10), lens=35, shift=(0, 0.16))

# ------------------------------------------------------------------ 7. title vista
def ground_z_multi(x, y):
    best = -1e9
    for o in S().objects:
        if o.name.startswith('ledge') and o.type == 'MESH' and not o.name.startswith('ledge_grass'):
            z = ground_z(o, x, y, 200)
            if z != 0.0: best = max(best, z)
    return best if best > -1e9 else -50
def boy_parts(shirt, pants, skin, hair, pack, strap, stick):
    """stylized boy ~1.35 m seen from behind (+Y is where he looks); feet at z=0"""
    out = []
    bm = bmesh.new()
    for y_, s in ((0.1, 1), (-0.1, -1)):
        bm_seg(bm, (y_, 0.02 * s, 0.03), (y_ * 0.8, 0, 0.62), 0.065, 0.075, 10)
    bm_sphere(bm, TRS((0, 0, 0.66), s=(0.2, 0.14, 0.12)), 14, 8)
    out.append((mesh_bm('boy_pants', bm), pants))
    bm = bmesh.new()
    bm_cone(bm, TRS((0, 0, 0.9)), 0.2, 0.19, 0.5, 16)
    bm_sphere(bm, TRS((0, 0, 1.12), s=(0.21, 0.15, 0.12)), 16, 8)
    bm_seg(bm, (0.2, 0, 1.1), (0.28, 0.06, 0.82), 0.055, 0.05, 8)   # right arm down to stick
    bm_seg(bm, (-0.2, 0, 1.1), (-0.27, -0.02, 0.8), 0.055, 0.05, 8)
    out.append((mesh_bm('boy_shirt', bm), shirt))
    bm = bmesh.new()
    bm_seg(bm, (0, 0, 1.17), (0, 0, 1.24), 0.05, 0.05, 8)
    bm_sphere(bm, TRS((0, 0.01, 1.36), s=(0.115, 0.12, 0.13)), 16, 10)
    bm_sphere(bm, TRS((0.29, 0.07, 0.8), s=(0.05, 0.05, 0.05)), 8, 6)
    bm_sphere(bm, TRS((-0.28, -0.02, 0.78), s=(0.05, 0.05, 0.05)), 8, 6)
    for sgn in (1, -1): bm_sphere(bm, TRS((sgn * 0.115, 0.01, 1.35), s=(0.025, 0.02, 0.035)), 8, 6)
    out.append((mesh_bm('boy_skin', bm), skin))
    bm = bmesh.new(); rnd = random.Random(5)
    for i in range(90):  # curly hair: clustered blobs over the back and top of the head
        th = rnd.uniform(0, 2 * math.pi); ph = rnd.uniform(0.0, 1.9)
        d = Vector((math.sin(ph) * math.cos(th), math.sin(ph) * math.sin(th), math.cos(ph)))
        if d.y > 0.3 or d.z < -0.45: continue  # keep the face side clear
        c = Vector((0, 0.01, 1.37)) + Vector((d.x * 0.12, d.y * 0.125, d.z * 0.13))
        bm_sphere(bm, TRS(c, s=(rnd.uniform(0.035, 0.05),) * 3), 8, 6)
    out.append((mesh_bm('boy_hair', bm), hair))
    bm = bmesh.new()
    bm_cube(bm, TRS((0, -0.19, 0.98), s=(0.3, 0.14, 0.36)))
    bm_cube(bm, TRS((0, -0.27, 0.9), s=(0.24, 0.05, 0.16)))
    bm_sphere(bm, TRS((0, -0.19, 1.16), s=(0.15, 0.075, 0.05)), 12, 6)
    out.append((mesh_bm('boy_pack', bm), pack))
    bm = bmesh.new()
    for sgn in (1, -1): bm_seg(bm, (sgn * 0.1, -0.13, 1.16), (sgn * 0.12, -0.14, 0.84), 0.022, 0.022, 6)
    out.append((mesh_bm('boy_straps', bm), strap))
    bm = bmesh.new(); bm_seg(bm, (0.31, 0.16, 0.0), (0.28, 0.04, 1.3), 0.022, 0.018, 8); bm_sphere(bm, TRS((0.28, 0.04, 1.31), s=(0.03,) * 3), 8, 6)
    out.append((mesh_bm('boy_stick', bm), stick))
    return out

@scene
def sc_title():
    P.update(sun=(0.12, 1.0, 0.06), sun_r=0.045, clouds=0.55, cloud_cov=0.57, cloud_scale=1.2, cloud_z=0.25,
             sky=[(-0.12, '#e9b27a'), (0.0, '#fbd592'), (0.05, '#f5bc72'), (0.16, '#e39a72'), (0.36, '#a894a8'), (0.8, '#6c7fae')],
             glow='#ffd489', glow_amt=0.85, glow_pow=4.5, fog=1 / 11000, fog_ground=1.0, fog_h=60.0, haze_z=0.02,
             rim='#ffcb78', rim_amt=1.7, beams=0.3, bloom=0.55, sun_str=3.0, amb=0.35)
    def fields(g, geo):
        vor = g.node('ShaderNodeTexVoronoi'); g.put(vor.inputs['Vector'], g.vm('MULTIPLY', geo.outputs['Position'], (1.0, 0.6, 1.0)))
        vor.inputs['Scale'].default_value = 0.012
        c = g.ramp(g.node('ShaderNodeSeparateColor').outputs[0] if False else vor.outputs['Color'], [(0.0, '#2f5a1a'), (0.22, '#4f7a2a'), (0.4, '#7aa53e'), (0.55, '#3f6a22'), (0.72, '#c0a64a'), (0.85, '#8db34a'), (1.0, '#35621e')])
        return c
    fieldm = toon('fields', fields, nscale=0.05, namt=0.12, rim=0.3)
    slope = toon('slope', '#6a5a30', nscale=0.05, namt=0.18, rim=0.8)
    rock = toon('rock', '#3e281c', nscale=1.2, namt=0.3, rim=1.4, shadow='#23150e', lit='#7a5436')
    rock2 = toon('rock2', '#4a3222', nscale=1.2, namt=0.3, rim=1.3, shadow='#2a1a10', lit='#8a603c')
    m1 = toon('hill_mid', '#5a6a3a', nscale=0.004, namt=0.12, rim=0.05)
    m2 = toon('mnt_far', '#7c8aa8', nscale=0.002, namt=0.08, rim=0.3)
    m3 = toon('mnt_far2', '#a8aec8', nscale=0.002, namt=0.05, rim=0.2)
    water = water_mat('river', '#35557f', dark=0.55)
    river_x = lambda y: -140 + 260 * math.sin(y / 520 + 0.6) + 0.04 * y
    def fz(x, y):
        d = abs(x - river_x(y))
        z = 1.5 * fbm(x / 90, y / 90, 3, 3) + 0.00002 * (x + 200) ** 2
        z -= 3.2 * max(0, 1 - d / 85)
        return z
    heightfield('valley', -3500, 3500, 120, 5200, 220, 170, fz, fieldm)
    wp = heightfield('water', -3500, 3500, 120, 5200, 8, 8, lambda x, y: -0.35, water)
    ridge('hill_mid', 3000, 7000, 900, 130, m1, seed=51, x0=0, freq=8.0, base=0.15, sharp=True, rough=0.3)
    ridge('mnt_far', 5200, 11000, 1500, 700, m2, seed=52, x0=-500, freq=5.0, base=0.3, peaks=[(0.12, 0.04, 0.3)])
    ridge('mnt_far2', 8500, 16000, 2000, 1100, m3, seed=53, x0=500, freq=4.0, base=0.4)
    # the slope falling from the ledge into the valley (near-mid layer)
    heightfield('slope', -250, 250, -20, 160, 90, 40, lambda x, y: max(0, 60 - 0.45 * max(y, 0) ** 1.05) * (0.9 + 0.2 * fbm(x / 20, y / 20, 3, 4)) + 3 * fbm(x / 7, y / 7, 3, 6) - 3, slope)
    # clay villages and palms along the river
    hm = {'plaster': toon('plaster', '#d9a066', rim=1.0), 'plaster_light': toon('plaster_l', '#e8c08a', rim=1.0), 'wood': toon('hwood', '#6a4a30'),
          'wood_dark': toon('hwood_d', '#3a2a1e'), 'clay': toon('clay', '#b8743f', rim=1.0), 'lime': toon('lime', '#efe6d4', rim=1.0)}
    houses = [import_glb(n, hm) for n in ('house_a', 'house_b', 'house_c')]
    pm = {'bark': toon('bark', '#6a4a30', rim=1.2), 'frond': toon('frond', '#4f7a2a', rim=1.4, nscale=2.0), 'dates': toon('dates', '#a0502a')}
    palms = [import_glb(n, pm) for n in ('palm_a', 'palm_b', 'palm_c')]
    rnd = random.Random(21)
    for vi, (vy, side) in enumerate(((330, 1), (620, -1), (1000, 1), (1500, -1), (2100, 1), (2800, -1))):
        cx = river_x(vy) + side * rnd.uniform(70, 120)
        for k in range(18 if vy < 1600 else 12):
            x = cx + rnd.gauss(0, 30 + vy * 0.015); y = vy + rnd.gauss(0, 25 + vy * 0.01)
            if abs(x - river_x(y)) < 40: continue
            inst('v%d_%d' % (vi, k), houses[k % 3], (x, y, fz(x, y) - 0.2), (0, 0, rnd.choice((0, 1.57, 3.14, 4.71)) + rnd.uniform(-0.1, 0.1)), 1.4)
    for i in range(40):  # a nearer grove below the ledge (mid layer)
        x = rnd.uniform(-260, -40); y = rnd.uniform(150, 320)
        inst('pn%d' % i, palms[i % 3], (x, y, fz(x, y) - 0.3), (0, 0, rnd.uniform(0, 6.3)), rnd.uniform(1.6, 2.2))
    for i in range(420):
        y = 180 + 3000 * rnd.random() ** 1.7
        x = river_x(y) + rnd.choice((-1, 1)) * rnd.uniform(40, 150) + rnd.gauss(0, 15)
        inst('p%d' % i, palms[i % 3], (x, y, fz(x, y) - 0.3), (0, 0, rnd.uniform(0, 6.3)), rnd.uniform(1.3, 1.8))
    # rocky ledge (near, dark, lower right) + the boy
    for i, (x, y, z, sz, m) in enumerate(((6.5, 1.5, 57.2, (3.4, 2.6, 2.9), rock), (10.5, -1.0, 55.5, (4.2, 3.4, 4.2), rock),
                                          (3.2, 3.2, 56.5, (2.2, 1.6, 1.9), rock2), (13.5, 3.5, 54, (3.0, 3.0, 3.2), rock),
                                          (8.5, 5.0, 55.2, (2.2, 2.2, 1.9), rock2))):
        o = inst('ledge%d' % i, rock_mesh('ledge%d' % i, sz, seed=i + 11, sub=3, rough=0.22), (x, y, z)); o.data.materials.append(m)
    bpy.context.view_layer.update() if False else None
    S().view_layers[0].update()
    top = ground_z(bpy.data.objects['ledge0'], 6.3, 1.9, 200)
    shirt = toon('shirt', '#e9dcc0', rim=1.8, namt=0.06); pants = toon('pants', '#6b4a3a', rim=1.4)
    skin = toon('skin', '#a8704a', rim=1.6, namt=0.04); hair = toon('hair', '#1e1410', rim=0.7, namt=0.12, nscale=30, lit='#3a2618', shadow='#26180f')
    pack = toon('pack', '#8a5a32', rim=1.5); strap = toon('strap', '#5a3a22', rim=1.0); stick = toon('stick', '#6a4a2a', rim=1.4)
    boy = place(boy_parts(shirt, pants, skin, hair, pack, strap, stick), 'boy', (6.3, 1.9, top - 0.05), math.radians(-8), 1.0)
    print('ledge top', top)
    camera((5.4, -5.6, top + 1.2), (-30, 400, 22), lens=32)
