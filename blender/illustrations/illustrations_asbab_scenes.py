# illustrations_asbab_scenes.py — compositions for illustrations_asbab.py (exec'd there; uses its helpers).

def clay_mats(mk=None, wall='#b8743f', floor='#8a5a36'):
    mk = mk or toonL
    return dict(wall=mk('wall', wall, nscale=3.0, namt=0.16, rim=0.4), floor=mk('floor', floor, nscale=4.0, namt=0.18, rim=0.2),
                wood=mk('wood', '#6a4428', nscale=12.0, namt=0.18, rim=0.6), clay=mk('clay', '#b0643a', nscale=8.0, namt=0.12, rim=0.9),
                clay2=mk('clay2', '#c98a55', nscale=8.0, namt=0.12, rim=0.9))

def palms_night(rim=0.35):
    return [import_glb2(n, lambda nm, c: toonL(nm, c, rim=rim, namt=0.06)) for n in ('palm_a', 'palm_b', 'palm_c')]

def thread_mesh(name, top, L, sway, mat, r=0.0045, rnd=None, knot=True):
    bm = bmesh.new(); top = Vector(top); pts = []
    for i in range(25):
        t = i / 24
        pts.append(top + Vector((sway * math.sin(t * math.pi * 0.9) + 0.01 * math.sin(t * 9), 0.01 * math.sin(t * 5), -L * t)))
    tube(bm, pts, r, 10)
    if knot:
        bm_sphere(bm, TRS(top + Vector((0, 0, -0.025)), s=(r * 2.6, r * 2.6, r * 3.2)), 10, 8)
        bm_cone(bm, TRS(top + Vector((0, 0, 0)), (math.pi / 2, 0, 0), (1, 1, 1)), 0.03, 0.03, 0.012, 16, caps=False)  # loop around the rod
    bm_sphere(bm, TRS(pts[-1], s=(r * 1.8, r * 1.8, r * 2.4)), 8, 6)
    return obj(name, mesh_bm(name, bm, mat))

# ------------------------------------------------------------------ 1. threads at the window, first light
@scene_a
def sc_threads_dawn():
    night_P(sun=(0.3, 1.0, -0.03), sun_r=0.02,
            sky=[(-0.12, '#16182c'), (0.0, '#f6dcaa'), (0.018, '#e0c8b4'), (0.045, '#8594c8'), (0.09, '#3e4e94'), (0.18, '#243070'), (0.4, '#131b4a'), (0.9, '#0a0e2c')],
            glow='#ffd8a0', glow_amt=0.45, glow_pow=14.0, fog=1 / 1400, fog_ground=1.5, fog_h=4.0, haze_z=0.004, sun_str=0.35,
            amb=0.1, amb_col='#1e2038', bloom=0.6, sun_col='#9fb0ff')
    M = clay_mats()
    wall = bx('wall', (0, 0, 1.5), (7, 0.42, 3.4), M['wall'], bev=0)
    cut(wall, arch_hole('win', 0, 0, 0.95, 0.92, 1.3), 0.035)
    bx('sill', (0, -0.05, 0.935), (1.2, 0.56, 0.05), M['wood'], bev=0.012)
    bx('floor_in', (0, -2, -0.02), (7, 4, 0.04), M['floor'], bev=0)
    palm_trunk('rod', (-0.56, -0.13, 1.72), (0.56, -0.13, 1.72), 0.022, M['wood'], rings=False)
    white = toonL('thread_white', '#fffaf0', rim=1.2, namt=0.0, fog=0.0, amb='#6a6e90')
    black = toonL('thread_black', '#0c0a0a', rim=1.5, namt=0.0, fog=0.0, amb='#040406')
    thread_mesh('thread_w', (-0.075, -0.13, 1.72), 0.66, 0.03, white, r=0.0065)
    thread_mesh('thread_b', (0.075, -0.13, 1.72), 0.64, -0.025, black, r=0.0065)
    flame = glow('flame', '#ffcf7a', 3.0)
    tip = oil_lamp('lamp', (0.36, -0.14, 0.96), M['clay'], flame, rot=math.pi * 0.92, s=1.3)
    plight('lamp_light', tip + Vector((0, -0.06, 0.05)), '#ff9a4a', 14.0, 0.03)
    jug('jug', (-0.38, -0.1, 0.96), M['clay2'], s=0.75, rot=2.6)
    far = toon('field_far', '#141420', nscale=0.05, namt=0.1, rim=0.0, lit='#181826', shadow='#10101a', fog=0.4)
    heightfield('ground', -500, 500, 0.3, 900, 80, 60, lambda x, y: -1.6 + 1.5 * (fbm(x / 60, y / 60, 3, 3) - 0.5) + 0.002 * max(y - 200, 0), far)
    hills = toon('hills', '#2c2c46', nscale=0.01, namt=0.08, rim=0.2, lit='#34345a', shadow='#262640')
    ridge('hills', 900, 3000, 500, 50, hills, seed=61, x0=0, sharp=False, freq=4.0, base=0.3)
    pm = [import_glb2(n, lambda nm, c: toon(nm, '#12121c', rim=0.8, namt=0.05, lit='#1a1a28', shadow='#0e0e18', fog=0.5)) for n in ('palm_a', 'palm_b', 'palm_c')]
    rnd = random.Random(3)
    for i, (x, y, s) in enumerate(((-9, 26, 1.3), (-16, 40, 1.4), (8, 30, 1.2), (14, 55, 1.5), (-5, 75, 1.3), (22, 90, 1.4), (-26, 95, 1.5), (3, 120, 1.4), (-40, 140, 1.6), (40, 150, 1.5))):
        inst('palm%d' % i, pm[i % 3], (x, y, -1.8), (0, 0, rnd.uniform(0, 6.3)), s)
    stars(200, seed=4, dist=2500, zmin=0.12, zmax=0.75, size=2.6, az=(-0.55, 0.55), k=2.5)
    cam = Vector((0.04, -1.75, 1.2))
    d = Vector((-0.17, 0.9, 0.36)).normalized()
    crescent('crescent', cam + d * 500, -d, R=9.0, mat=glow('moon', '#f6eed8', 1.4), roll=math.radians(-35))
    camera(tuple(cam), (0.0, 0, 1.5), lens=25)

# ------------------------------------------------------------------ 2. suhoor tray at night
@scene_a
def sc_suhoor_table():
    night_P(sun=(-0.3, -1.0, 0.7), sun_r=0.02, sun_str=0.5, amb=0.04, amb_col='#3a2c4a', fog=1 / 900, kuwa=4, bloom=0.8, glow_amt=0.2,
            sun_col='#8a9cff')
    M = clay_mats(wall='#b07048')
    wall = bx('wall_back', (0, 1.05, 1.5), (5, 0.36, 3.0), M['wall'], bev=0)
    cut(wall, arch_hole('win', -0.35, 1.05, 0.32, 0.6, 0.72), 0.03)
    bx('win_sill', (-0.35, 0.86, 0.31), (0.85, 0.12, 0.04), M['wood'], bev=0.01)
    bx('wall_side', (-1.6, 0, 1.5), (0.36, 5, 3.0), M['wall'], bev=0.03)
    bx('floor', (0, 0, -0.02), (6, 6, 0.04), M['floor'], bev=0)
    mat = toonL('mat', stripes('#d8b26a', '#a88048', 70.0, 0, '#6a4a28', 9.0), nscale=20, namt=0.08, rim=0.2)
    bx('mat', (0, 0.05, 0.006), (1.7, 1.3, 0.012), mat, bev=0.004)
    brass = toonL('brass', '#d0a04a', rim=1.2, gloss=0.8, namt=0.05)
    lathe_obj('tray', [(0, 0.0), (0.33, 0.0), (0.36, 0.012), (0.37, 0.03), (0.355, 0.03), (0.34, 0.012), (0, 0.012)], brass, (0, 0.1, 0.012), 48)
    jug('jug', (0.22, 0.3, 0.024), M['clay'], s=1.0, rot=2.2)
    bw = toonL('bowl', '#e0bc8c', rim=0.8, gloss=0.3, namt=0.1, nscale=10)
    bowl('dbowl', (-0.13, 0.2, 0.024), bw, r=0.13, h=0.065)
    dm = toonL('dates', '#8a3a16', rim=1.4, gloss=1.4, namt=0.08, nscale=30)
    rnd = random.Random(5)
    dates_heap('dates', dm, (-0.13, 0.2, 0.05), 0.1, 26, rnd, top=0.05)
    br = toonL('bread', '#d0944e', rim=0.8, namt=0.25, nscale=40)
    bread('bread1', (0.12, -0.06, 0.03), br, r=0.12, seed=1); bread('bread2', (0.1, -0.08, 0.052), br, r=0.115, seed=2)
    cup = toonL('cup', '#dccbac', rim=0.9, gloss=0.4, namt=0.05)
    lathe_obj('cup', [(0, 0), (0.03, 0), (0.036, 0.01), (0.042, 0.06), (0.038, 0.062), (0.032, 0.012), (0, 0.012)], cup, (-0.2, -0.08, 0.024), 24)
    milk = toonL('milk', '#f8f0e0', rim=0.3, namt=0.0)
    lathe_obj('milk', [(0, 0), (0.037, 0)], milk, (-0.2, -0.08, 0.075), 24)
    for i in range(3):
        dates_heap('ld%d' % i, dm, (0.0 + i * 0.05, 0.05 - i * 0.04, 0.03), 0.01, 1, rnd, top=0.0)
    flame = glow('flame', '#ffcf7a', 3.0)
    tip = oil_lamp('lamp', (-0.5, 0.32, 0.012), M['clay'], flame, rot=-0.5, s=1.4)
    plight('lamp_light', tip + Vector((0.02, -0.02, 0.07)), '#ff9a48', 22.0, 0.04)
    pm = [import_glb2('palm_b', lambda nm, c: toon(nm, '#141424', rim=0.5, namt=0.05, lit='#1c1c30', shadow='#10101c'))]
    inst('palm', pm[0], (1.2, 14, -4.0), (0, 0, 1.0), 1.1)
    stars(150, seed=8, dist=2500, zmin=0.0, zmax=0.25, size=2.2, az=(-0.4, 0.1), k=2.5)
    cam = Vector((0.05, -1.32, 0.9))
    d = (Vector((-0.42, 1.05, 0.86)) - cam).normalized()
    crescent('crescent', cam + d * 500, -d, R=7.0, mat=glow('moon', '#f6eed8', 1.8), roll=math.radians(20))
    camera(tuple(cam), (-0.02, 0.25, 0.1), lens=28, shift=(0, 0.14))

# ------------------------------------------------------------------ 4. night house with an empty bowl on the doorstep
@scene_a
def sc_night_house():
    night_P(sun=(0.8, -0.55, 0.6), sun_str=1.6, amb=0.12, fog=1 / 220, fog_ground=1.2, fog_h=5.0, amb_col='#262c52', sun_col='#a6b6ff',
            sky=[(-0.12, '#10142c'), (0.0, '#4e5e96'), (0.06, '#34437a'), (0.2, '#202b5e'), (0.5, '#121c46'), (0.9, '#0a0f2c')], rim_amt=1.2)
    M = clay_mats(wall='#c49a70')
    house = bx('house', (0.4, 2.5, 1.6), (6.5, 5.0, 3.2), M['wall'], bev=0)
    cut(house, [cutter('door_h', (-0.9, 0.0, 0.95), (1.05, 0.5, 1.9))] + arch_hole('win', 1.6, 0, 1.15, 0.8, 1.0, 0.5), 0.05)
    bx('parapet', (0.4, 2.5, 3.25), (6.7, 5.2, 0.14), M['wall'], bev=0.04)
    bx('upper', (-1.2, 3.4, 3.9), (2.6, 2.6, 1.3), M['wall'], bev=0.05)
    door = toonL('door', '#4a6e7a', nscale=6, namt=0.2, rim=0.6)
    bx('door', (-0.9, 0.16, 0.95), (1.0, 0.08, 1.88), door, bev=0.01)
    for i in range(4): bx('plank%d' % i, (-1.28 + i * 0.25, 0.11, 0.95), (0.02, 0.02, 1.8), M['wood'], bev=0.004)
    bx('lintel', (-0.9, -0.03, 1.97), (1.35, 0.3, 0.14), M['wood'], bev=0.02)
    iron = toonL('iron', '#2a2420', rim=1.0, gloss=0.6)
    lathe_obj('ring', [(0.035, -0.006), (0.045, 0.0), (0.035, 0.006), (0.025, 0.0), (0.035, -0.006)], iron, (-0.62, 0.1, 1.0), 20, rot=(math.pi / 2, 0, 0))
    lit = glow('winlight', '#ffc26a', 1.6)
    bx('win_glow', (1.6, 0.28, 1.6), (1.0, 0.04, 1.2), lit, bev=0)
    bx('sill', (1.6, -0.12, 1.12), (1.0, 0.3, 0.06), M['wood'], bev=0.01)
    for sg in (-1, 1):
        bx('shutter%d' % sg, (1.6 + sg * 0.62, -0.2, 1.62), (0.42, 0.04, 0.9), door, bev=0.01, rot=(0, 0, -sg * 0.6))
    plight('inside', (1.6, 0.7, 1.75), '#ff9a4a', 120.0, 0.2)
    stone = toonL('step', '#a08a74', nscale=4, namt=0.2, rim=0.5)
    bx('step1', (-0.9, -0.3, 0.09), (1.7, 0.6, 0.18), stone, bev=0.04)
    bw = toonL('bowl', '#c87a44', rim=1.6, gloss=0.6, namt=0.1, nscale=10)
    bowl('ebowl', (-0.55, -0.42, 0.18), bw, r=0.2, h=0.1)
    for k in (-1, 1): bx('bar%d' % k, (1.6 + k * 0.14, -0.02, 1.62), (0.05, 0.05, 0.95), M['wood'], bev=0.01)
    pstone = toonL('pstone', '#8c7c6c', nscale=5, namt=0.2, rim=0.5)
    rnd2 = random.Random(4)
    for i in range(14):
        t = i / 13; x = -0.9 - 1.6 * t * t + rnd2.uniform(-0.2, 0.2); y = -0.9 - 5.0 * t
        o = inst('ps%d' % i, rock_mesh('ps%d' % i, (0.28, 0.22, 0.05), seed=i, sub=1, rough=0.2), (x, y, 0.0), (0, 0, rnd2.uniform(0, 3)))
        o.data.materials.append(pstone)
    gm = import_glb2('grass_a', lambda nm, c: toonL(nm, c, rim=0.8, namt=0.1))
    for i in range(26):
        x = rnd2.uniform(-5, 5); y = rnd2.uniform(-5, -0.4)
        if abs(x - (-0.9 - 1.6 * ((-0.9 - y) / 5) ** 2)) < 0.6: continue
        inst('gr%d' % i, gm, (x, y, 0), (0, 0, rnd2.uniform(0, 6)), rnd2.uniform(0.8, 1.5))
    ground = toonL('ground', '#a08060', nscale=0.6, namt=0.2, rim=0.1)
    heightfield('ground', -60, 60, -12, 120, 80, 60, lambda x, y: 0.05 * fbm(x, y, 3, 2) - 0.02 + (0.0 if y < 30 else 0.01 * (y - 30)), ground)
    jar = import_glb2('jar', lambda nm, c: toonL(nm, c, rim=0.8, namt=0.08))
    inst('jar', jar, (3.0, -0.45, 0.0), (0, 0, 0.5), 1.0)
    inst('jar2', import_glb2('jar_b', lambda nm, c: toonL(nm, c, rim=0.8, namt=0.08)), (3.5, -0.1, 0.0), (0, 0, 0.5), 0.9)
    pm = palms_night(0.6)
    rnd = random.Random(9)
    for i, (x, y, s) in enumerate(((-4.6, 3.0, 1.3), (5.2, 5.0, 1.2), (-8, 14, 1.4), (10, 18, 1.4), (-15, 26, 1.5), (18, 30, 1.3), (-5, 30, 1.4))):
        inst('palm%d' % i, pm[i % 3], (x, y, 0), (0, 0, rnd.uniform(0, 6.3)), s)
    stars(320, seed=11, dist=2500, zmin=0.06, zmax=0.95, size=2.6, az=(-1.0, 1.0), k=2.6)
    camera((-2.5, -4.9, 0.8), (0.0, 0, 1.45), lens=26)

# ------------------------------------------------------------------ 10. lamp just blown out
def smoke_mesh(name, base, mat, h=0.34, turns=1.6, rnd=None):
    bm = bmesh.new(); base = Vector(base); pts = []
    for i in range(60):
        t = i / 59; a = t * turns * 2 * math.pi
        rad = 0.004 + 0.035 * t ** 1.3
        pts.append(base + Vector((rad * math.sin(a) + 0.03 * t * t, rad * math.cos(a) * 0.6, h * t)))
    tube(bm, pts, [0.0025 + 0.006 * (i / 59) for i in range(60)], 8)
    return obj(name, mesh_bm(name, bm, mat))

@scene_a
def sc_lamp_out():
    night_P(sun=(-0.4, -1.0, 0.5), sun_str=0.2, amb=0.04, amb_col='#1a1e3a', fog=1 / 900, kuwa=4, bloom=0.7, glow_amt=0.2, sun_col='#8a9cff',
            sky=[(-0.12, '#10142c'), (0.0, '#3a4a7a'), (0.1, '#26346c'), (0.5, '#121a40'), (0.9, '#0a0f2a')])
    M = clay_mats(wall='#a8744e')
    back = bx('wall_back', (0, 0.2, 1.5), (5, 0.4, 3.0), M['wall'], bev=0)
    cut(back, arch_hole('win', 0.75, 0.2, 0.95, 0.62, 1.0), 0.03)
    for k in (-1, 1): bx('peg%d' % k, (-0.35 + k * 0.32, -0.08, 0.86), (0.05, 0.16, 0.06), M['wood'], bev=0.01)
    bx('shelf', (-0.35, -0.12, 0.9), (0.9, 0.24, 0.05), M['wood'], bev=0.01)
    bx('floor', (0, -1, -0.02), (5, 5, 0.04), M['floor'], bev=0)
    bx('win_sill', (0.75, 0.0, 0.93), (0.75, 0.12, 0.04), M['wood'], bev=0.01)
    oil_lamp('lamp', (-0.4, -0.12, 0.925), M['clay'], None, rot=0.3, lit=False, s=1.7)
    tip = Vector((-0.4, -0.12, 0.925)) + Matrix.Rotation(0.3, 3, 'Z') @ Vector((0.104, 0, 0.038)) * 1.7
    ember = glow('ember', '#ff7a2a', 3.5)
    bm = bmesh.new(); bm_sphere(bm, TRS(tip, s=(0.006,) * 3), 8, 6); obj('ember', mesh_bm('ember', bm, ember))
    def sm_alpha(g, geo):
        z = g.sep(geo.outputs['Position'])[2]
        lw = g.node('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
        edge = g.mr(lw.outputs['Facing'], 0.2, 0.9, 0.9, 0.3)
        return g.math('MULTIPLY', g.mr(z, tip.z + 0.03, tip.z + 0.42, 0.9, 0.0), edge)
    smoke = toon('smoke', '#dde2f2', flat=True, lit=lin('#d4dcf4', 1.05), rim=0, namt=0, fog=0, alpha=sm_alpha)
    smoke_mesh('smoke', tip + Vector((0, 0, 0.004)), smoke, 0.42, 1.5)
    jug('jug', (-0.08, -0.1, 0.925), M['clay2'], s=0.6, rot=2.5)
    spot('moonbeam', (0.5, -1.6, 1.7), (-0.3, -0.05, 1.0), '#8fa4ff', 70, 0.5, 1.0, 0.4)
    pm = [import_glb2('palm_c', lambda nm, c: toon(nm, '#141424', rim=0.5, namt=0.05, lit='#1c1c30', shadow='#10101c'))]
    inst('palm', pm[0], (2.4, 8, -0.8), (0, 0, 2.0), 1.0)
    stars(120, seed=2, dist=2500, zmin=0.02, zmax=0.6, size=2.4, az=(-0.9, 0.1), k=2.5)
    cam = Vector((-0.1, -1.1, 1.16))
    d = (Vector((0.84, 0.2, 1.62)) - cam).normalized()
    crescent('crescent', cam + d * 500, -d, R=8.0, mat=glow('moon', '#f6eed8', 1.8), roll=math.radians(-25))
    camera(tuple(cam), (0.05, 0.1, 1.12), lens=27)

# ------------------------------------------------------------------ 11. a meal set for a guest
@scene_a
def sc_guest_meal():
    night_P(sun=(0.3, -1.0, 0.5), sun_str=0.5, amb=0.06, amb_col='#2e2846', fog=1 / 700, kuwa=4, bloom=0.8, glow_amt=0.2, sun_col='#8a9cff',
            sky=[(-0.12, '#10142c'), (0.0, '#4a5a90'), (0.06, '#2e3d74'), (0.2, '#1c2758'), (0.5, '#111a42'), (0.9, '#0a0f2c')])
    M = clay_mats(wall='#b07a50')
    back = bx('wall_back', (0, 2.0, 1.6), (6, 0.4, 3.2), M['wall'], bev=0)
    cut(back, arch_hole('door', 0.45, 2.0, 0.0, 1.0, 2.1), 0.04)
    bx('threshold', (0.45, 1.95, 0.02), (1.1, 0.5, 0.04), M['wood'], bev=0.01)
    bx('wall_side', (-1.7, 0.5, 1.6), (0.4, 4.0, 3.2), M['wall'], bev=0.03)

    bx('floor', (0, 0, -0.02), (7, 7, 0.04), M['floor'], bev=0)
    mat = toonL('mat', stripes('#d4ae68', '#a47c44', 60.0, 1, '#6a4a28', 8.0), nscale=20, namt=0.08, rim=0.2)
    bx('mat', (0.05, 0.95, 0.006), (1.5, 1.1, 0.012), mat, bev=0.004)
    cl = toonL('plate', '#c07a44', rim=1.0, gloss=0.4, namt=0.1, nscale=10)
    lathe_obj('plate', [(0, 0), (0.12, 0), (0.2, 0.03), (0.23, 0.05), (0.215, 0.052), (0.18, 0.03), (0, 0.02)], cl, (0.05, 0.95, 0.012), 40)
    stew = toonL('stew', '#8a4a22', rim=0.4, gloss=0.6, namt=0.2, nscale=25)
    lathe_obj('stew', [(0, 0.04), (0.17, 0.035), (0.18, 0.03)], stew, (0.05, 0.95, 0.012), 40)
    br = toonL('bread', '#d6a05a', rim=0.8, namt=0.25, nscale=40)
    rnd = random.Random(3)
    for i in range(7):
        a = i / 7 * 6.28 + rnd.uniform(-0.2, 0.2); r = rnd.uniform(0.02, 0.1)
        bm = bmesh.new(); ellip(bm, (0, 0, 0), (0.045, 0.035, 0.012), 10, 6)
        o = obj('crumb%d' % i, mesh_bm('crumb%d' % i, bm, br)); o.location = (0.05 + math.cos(a) * r, 0.95 + math.sin(a) * r, 0.058)
        o.rotation_euler = (rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), a)
    jug('jug', (0.45, 1.1, 0.012), M['clay'], s=0.95, rot=2.4)
    cup = toonL('cup', '#dccbac', rim=0.9, gloss=0.4, namt=0.05)
    lathe_obj('cup', [(0, 0), (0.03, 0), (0.036, 0.01), (0.042, 0.06), (0.038, 0.062), (0.032, 0.012), (0, 0.012)], cup, (0.36, 0.78, 0.012), 24)
    dm = toonL('dates', '#8a3a16', rim=1.4, gloss=1.4, namt=0.08, nscale=30)
    bw = toonL('dbowl', '#e0bc8c', rim=0.8, gloss=0.3, namt=0.1, nscale=10)
    bowl('dbowl', (-0.25, 0.72, 0.012), bw, r=0.08, h=0.045)
    dates_heap('dates', dm, (-0.25, 0.72, 0.035), 0.06, 11, rnd, top=0.03)
    cu = toonL('cushion', '#9a3a2a', rim=0.8, namt=0.15, nscale=6)
    cushion('cushion', (-0.72, 1.05, 0.11), (0.34, 0.65, 0.24), cu, rot=0.08)
    flame = glow('flame', '#ffcf7a', 3.0)
    tip = oil_lamp('lamp', (-0.42, 1.25, 0.012), M['clay'], flame, rot=-0.6, s=1.4)
    plight('lamp_light', tip + Vector((0.02, -0.03, 0.08)), '#ff9a48', 14.0, 0.05)
    ground = toon('yard', '#2a2a44', nscale=0.5, namt=0.15, rim=0.1, lit='#343458', shadow='#20203a')
    heightfield('yard', -40, 40, 2.1, 80, 30, 30, lambda x, y: 0.03 * fbm(x, y, 3, 1), ground)
    pm = [import_glb2(n, lambda nm, c: toon(nm, '#161628', rim=0.6, namt=0.05, lit='#1e1e34', shadow='#12121e')) for n in ('palm_a', 'palm_b')]
    inst('palm0', pm[0], (2.2, 24, 0), (0, 0, 1.0), 1.0); inst('palm1', pm[1], (-3.0, 30, 0), (0, 0, 3.0), 1.1)
    stars(200, seed=13, dist=2500, zmin=0.05, zmax=0.6, size=2.4, az=(-0.4, 0.4), k=2.6)
    cam = Vector((0.12, -0.55, 0.64))
    d = (Vector((0.62, 2.0, 1.35)) - cam).normalized()
    crescent('crescent', cam + d * 500, -d, R=7.0, mat=glow('moon', '#f6eed8', 1.8), roll=math.radians(-20))
    camera(tuple(cam), (0.22, 1.5, 0.52), lens=22)

# ================================================================== daytime scenes
def palms_day(rim=1.2):
    return [import_glb2(n, lambda nm, c: toon(nm, c, rim=rim, namt=0.08)) for n in ('palm_a', 'palm_b', 'palm_c')]

def glb_day(name, rim=1.0):
    return import_glb2(name, lambda nm, c: toon(nm, c, rim=rim, namt=0.08))

def woven(c1, c2, f=90.0):
    """coiled palm-leaf basket: horizontal coils with small diagonal stitches"""
    def fn(g, geo):
        x, y, z = g.sep(geo.outputs['Position'])
        a = g.math('SINE', g.math('MULTIPLY', z, f))
        ang = g.node('ShaderNodeMath', operation='ARCTAN2'); g.put(ang.inputs[0], y); g.put(ang.inputs[1], x)
        st = g.math('SINE', g.math('ADD', g.math('MULTIPLY', ang.outputs[0], 60.0), g.math('MULTIPLY', z, f * 0.5)))
        k = g.math('ADD', g.mr(a, -0.3, 0.6), g.math('MULTIPLY', g.mr(st, 0.85, 1.0), 0.5))
        return g.mix(g.math('MINIMUM', k, 1.0), lin(c2), lin(c1))
    return fn

def basket_obj(name, loc, mat, rimmat, r=0.24, h=0.22, s=1.0):
    bm = bmesh.new()
    lathe(bm, [(0, 0), (r * 0.7, 0), (r * 0.85, h * 0.1), (r, h * 0.6), (r * 1.04, h), (r * 0.98, h), (r * 0.94, h * 0.6), (r * 0.8, h * 0.12), (0, h * 0.1)], 40)
    o = obj(name, mesh_bm(name, bm, mat)); o.location = loc; o.scale = (s,) * 3
    bm = bmesh.new(); pts = [Vector((math.cos(a) * r * 1.03, math.sin(a) * r * 1.03, h)) for a in [i / 40 * 2 * math.pi for i in range(41)]]
    tube(bm, pts, r * 0.07, 10, caps=False)
    o2 = obj(name + '_rim', mesh_bm(name + '_rim', bm, rimmat)); o2.parent = o
    return o

def date_cluster(name, top, mats, rnd, L=0.55, n_str=34, per=10, spread=0.28, stalk_mat=None):
    """a heavy date bunch (idhq) hanging from `top`: curved stalk + strands + dates (random colour from mats)"""
    top = Vector(top); bm_s = bmesh.new(); bms = [bmesh.new() for _ in mats]
    stalk = [top + Vector((0.02 * math.sin(t * 3), 0, -0.22 * t)) for t in [i / 8 for i in range(9)]]
    tube(bm_s, stalk, [0.022 - 0.006 * i / 8 for i in range(9)], 10)
    base = stalk[-1]
    for k in range(n_str):
        a = rnd.uniform(0, 2 * math.pi); sp = rnd.uniform(0.3, 1.0) * spread
        ln = L * rnd.uniform(0.7, 1.05)
        pts = [base + Vector((math.cos(a) * sp * t ** 0.7, math.sin(a) * sp * t ** 0.7 * 0.8, -ln * t)) for t in [i / 6 for i in range(7)]]
        tube(bm_s, pts, 0.0035, 5, caps=False)
        for j in range(per):
            t = rnd.uniform(0.15, 1.0); pos = pts[0].lerp(pts[-1], t)
            pos = base + Vector((math.cos(a) * sp * t ** 0.7, math.sin(a) * sp * t ** 0.7 * 0.8, -ln * t))
            off = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)).normalized() * 0.018
            c = pos + off + Vector((0, 0, -0.012))
            mi = rnd.randrange(len(mats))
            ellip(bms[mi], c, (0.015, 0.015, 0.024), 8, 6, (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 0))
    obj(name + '_stalk', mesh_bm(name + '_stalk', bm_s, stalk_mat))
    for i, b in enumerate(bms): obj(name + '_d%d' % i, mesh_bm(name + '_d%d' % i, b, mats[i]))

def rope_between(name, a, b, sag, mat, r=0.012):
    a, b = Vector(a), Vector(b); pts = [a.lerp(b, t) - Vector((0, 0, sag * 4 * t * (1 - t))) for t in [i / 30 for i in range(31)]]
    bm = bmesh.new(); tube(bm, pts, r, 8); obj(name, mesh_bm(name, bm, mat))
    return lambda t: a.lerp(b, t) - Vector((0, 0, sag * 4 * t * (1 - t)))

def sparrow_mats():
    return (toon('sp_body', '#8a5a36', rim=1.2, namt=0.15, nscale=40), toon('sp_belly', '#e6d2b0', rim=1.0, namt=0.05), toon('sp_dark', '#2a1c14', rim=0.6, namt=0))

def day_P(**kw):
    P.update(sun=(-0.45, 1.0, 0.1), sun_r=0.04, clouds=0.5, cloud_cov=0.56, cloud_scale=1.2,
             sky=[(-0.12, '#e9b27a'), (0.0, '#fbd592'), (0.05, '#f5bc72'), (0.16, '#e39a72'), (0.36, '#a894a8'), (0.8, '#6c7fae')],
             glow='#ffd489', glow_amt=0.8, fog=1 / 1500, fog_ground=1.4, fog_h=5.0, rim='#ffcb78', rim_amt=1.6, beams=0.25, bloom=0.55,
             sun_str=3.0, amb=0.35, kuwa=4)
    P.update(kw)

# ------------------------------------------------------------------ 3. the farmer's plot at sunset
@scene_a
def sc_qays_field():
    day_P(sun=(0.18, 1.0, 0.055), sun_r=0.045, clouds=0.6, cloud_cov=0.55,
          sky=[(-0.12, '#e6a86c'), (0.0, '#fbd08a'), (0.05, '#f3a860'), (0.15, '#e08a62'), (0.36, '#a47890'), (0.8, '#565284')],
          glow_amt=0.85, glow_pow=5.0, fog=1 / 900, fog_ground=1.5, fog_h=4.0, beams=0.35, rim_amt=1.8, bands=(0.14, 0.42))
    soil = toon('soil', '#7a4a2c', nscale=2.0, namt=0.22, rim=0.6)
    grass = toon('grass', '#6a7a30', nscale=0.3, namt=0.2, rim=0.5)
    bank = toon('bank', '#8a6a3e', nscale=1.0, namt=0.2, rim=0.5)
    cx = lambda y: 3.6 + 0.06 * y + 0.8 * math.sin(y / 14)
    def fz(x, y):
        z = 0.03 * fbm(x / 2, y / 2, 3, 2)
        if -4.5 < x < 2.2 and 0 < y < 40:
            z += 0.07 * (0.5 + 0.5 * math.sin(x * 2 * math.pi / 0.55)) * min(1, (2.2 - x) / 0.4, (x + 4.5) / 0.4)
        d = abs(x - cx(y))
        z -= 0.55 * max(0, 1 - d / 1.5) ** 0.7
        return z
    heightfield('soil', -5, 2.4, -3, 45, 260, 180, fz, soil)
    heightfield('grass', -60, -4.8, -3, 400, 40, 60, lambda x, y: 0.04 * fbm(x / 3, y / 3, 3, 4), grass)
    heightfield('bank', 2.3, 60, -3, 400, 120, 110, fz, bank)
    water_mat_ = water_mat('canal', '#35557f', dark=0.45)
    heightfield('water', -5, 60, -3, 400, 4, 4, lambda x, y: -0.28, water_mat_)
    pm = palms_day(1.4)
    rnd = random.Random(12)
    for i, (x, y, s) in enumerate(((-3.2, 5.0, 1.0), (6.4, 9, 1.1), (7.2, 18, 1.2), (-7, 20, 1.3), (5.5, 30, 1.2), (9, 40, 1.4), (-12, 45, 1.3), (-2, 60, 1.4), (12, 70, 1.5), (-20, 80, 1.5))):
        inst('palm%d' % i, pm[i % 3], (x, y, fz(x, y) - 0.05), (0, 0, rnd.uniform(0, 6.3)), s)
    scatter_palms(pm, rnd, 70, (-120, 120), (90, 600), (1.2, 1.7))
    rd = glb_day('reeds', 1.4)
    for i in range(22):
        y = rnd.uniform(1, 30); side = rnd.choice((-1, 1)); x = cx(y) + side * rnd.uniform(1.1, 1.6)
        inst('reed%d' % i, rd, (x, y, fz(x, y) - 0.05), (0, 0, rnd.uniform(0, 6)), rnd.uniform(0.8, 1.3))
    hoe = glb_day('hoe', 1.6)
    inst('hoe', hoe, (-2.85, 4.62, 0.02), (math.radians(-12), math.radians(-24), 0.3), 1.0)
    bk = glb_day('basket', 1.4)
    inst('basket', bk, (-1.4, 2.6, 0.05), (0, 0, 0.4), 1.0)
    skin = toon('skin', '#8a5a30', rim=1.6, namt=0.1)
    bm = bmesh.new(); ellip(bm, (0, 0, 0.12), (0.22, 0.15, 0.12), 16, 10); bm_seg(bm, (0.2, 0, 0.14), (0.3, 0, 0.26), 0.035, 0.03, 8)
    o = obj('waterskin', mesh_bm('waterskin', bm, skin)); o.location = (-2.35, 3.9, 0.0); o.rotation_euler = (0, 0, 2.4)
    far = toon('hills', '#8a7390', nscale=0.01, namt=0.1, rim=0.3)
    ridge('hills', 900, 3000, 500, 60, far, seed=71, x0=0, sharp=False, freq=4.0, base=0.3)
    bb = bird_mesh('bird', 0.5, stones=False); _m = toon('bird', '#3a2420', namt=0, rim=0.8)
    for _k in range(3): bb.materials.append(_m)
    for i in range(6):
        inst('bd%d' % i, bb, (rnd.uniform(-6, 4), rnd.uniform(30, 50), rnd.uniform(7, 11)), (0.2, 0, rnd.uniform(-0.4, 0.4)), 0.8)
    camera((-0.9, -2.4, 1.25), (0.2, 20, 1.6), lens=28)

# ------------------------------------------------------------------ 5. date clusters hanging in a palm-trunk porch
def porch(M, rnd, x0=-1.5, x1=1.5, y=2.0, h=2.6, depth=2.4, gap=0.0):
    for x in (x0, x1):
        palm_trunk('pillar%d' % int(x * 10), (x, y, 0), (x, y, h), 0.13, M['trunk'])
        palm_trunk('pillarb%d' % int(x * 10), (x, y + depth, 0), (x, y + depth, h), 0.13, M['trunk'])
    palm_trunk('beam_f', (x0 - 0.4, y, h), (x1 + 0.4, y, h), 0.1, M['trunk'], rings=False)
    palm_trunk('beam_b', (x0 - 0.4, y + depth, h), (x1 + 0.4, y + depth, h), 0.1, M['trunk'], rings=False)
    fronds_roof('roof', x0 - 0.5, x1 + 0.5, y - 0.3, y + depth + 0.3, h + 0.1, M['frond'], rnd, gap=gap)

@scene_a
def sc_date_clusters():
    day_P(sun=(-0.55, -0.6, 0.45), sun_r=0.04, clouds=0.4, cloud_cov=0.6,
          sky=[(-0.12, '#e8c49a'), (0.0, '#fbe3b4'), (0.05, '#f6daa6'), (0.16, '#d8c8b4'), (0.4, '#9fb4d0'), (0.9, '#6f8fc0')],
          glow='#ffe6b0', glow_amt=0.4, fog=1 / 700, fog_ground=1.0, fog_h=5.0, beams=0.0, rim='#ffe2a0', rim_amt=1.4,
          lit=(1.15, 1.04, 0.88), shadow=(0.55, 0.46, 0.46), shade='#5a3e3a', bands=(0.12, 0.38), amb=0.45, sun_str=3.2)
    rnd = random.Random(21)
    M = dict(trunk=toon('trunk', '#7a5a3a', nscale=8, namt=0.2, rim=1.2), frond=toon('frond_dry', '#b89a5a', nscale=4, namt=0.2, rim=1.0),
             rope=toon('rope', '#c4a46a', nscale=30, namt=0.2, rim=1.0), wall=toon('wall', '#d0a070', nscale=1.5, namt=0.15, rim=0.8),
             ground=toon('ground', '#c89a68', nscale=0.8, namt=0.18, rim=0.2))
    porch(M, rnd)
    ground_plane('ground', M['ground'], -40, 40, -5, 120, amp=0.1)
    bx('yard_wall', (0, 9, 1.0), (30, 0.5, 2.0), M['wall'], bev=0.08)
    ropef = rope_between('rope', (-1.45, 1.95, 2.25), (1.45, 1.95, 2.25), 0.12, M['rope'])
    stalk = toon('stalk', '#d0902e', nscale=10, namt=0.1, rim=1.2)
    gold = toon('date_gold', '#e8a826', nscale=20, namt=0.08, rim=1.8)
    red = toon('date_red', '#b8321e', nscale=20, namt=0.08, rim=1.8)
    amber = toon('date_amber', '#d86a1e', nscale=20, namt=0.08, rim=1.8)
    brown = toon('date_brown', '#6a2a14', nscale=20, namt=0.08, rim=1.6)
    for i, (t, ms) in enumerate(((0.2, [gold, gold, amber]), (0.5, [red, red, amber]), (0.8, [amber, brown, red]))):
        p = ropef(t)
        date_cluster('bunch%d' % i, p + Vector((0, 0, 0.01)), ms, rnd, L=0.62, n_str=52, per=15, spread=0.26, stalk_mat=stalk)
    mat = toon('mat', stripes('#d8b26a', '#a88048', 60.0, 0, '#6a4a28', 8.0), nscale=20, namt=0.08, rim=0.2)
    bx('mat', (0, 1.9, 0.006), (2.4, 1.8, 0.012), mat, bev=0.004)
    rnd2 = random.Random(3)
    for i in range(9): dates_heap('fallen%d' % i, gold if i % 2 else red, (rnd2.uniform(-0.6, 0.7), rnd2.uniform(1.1, 1.8), 0.012), 0.01, 1, rnd2, top=0.0, size=(0.014, 0.014, 0.022))
    sb, sw, sd = sparrow_mats()
    sparrow('sp1', sb, sw, sd, ropef(0.35) + Vector((0, 0, 0.005)), rot=-0.6, s=1.9)
    sparrow('sp2', sb, sw, sd, (1.05, 1.98, 2.69), rot=-2.6, s=1.9)
    sparrow('sp3', sb, sw, sd, (0.5, 1.2, 0.012), rot=-2.4, s=2.0, peck=0.03)
    stick = toon('stick', '#6a4a2a', rim=1.4)
    bm = bmesh.new(); bm_seg(bm, (0, 0, 0), (0, 0, 1.6), 0.018, 0.015, 8); o = obj('stick', mesh_bm('stick', bm, stick)); o.location = (1.3, 1.83, 0.0); o.rotation_euler = (0, math.radians(-8), 0)
    pm = palms_day(1.2)
    for i, (x, y, s) in enumerate(((-4, 12, 1.2), (3.5, 14, 1.3), (-9, 18, 1.4), (8, 20, 1.3), (0, 24, 1.5), (-15, 30, 1.4))):
        inst('palm%d' % i, pm[i % 3], (x, y, 0), (0, 0, rnd.uniform(0, 6.3)), s)
    camera((0.1, -0.95, 1.2), (0.0, 2.0, 1.45), lens=26)

# ------------------------------------------------------------------ 6. the best dates vs the poor ones
@scene_a
def sc_best_dates():
    day_P(sun=(-0.5, -0.2, 0.75), sun_r=0.04, clouds=0.3,
          sky=[(-0.12, '#e8c49a'), (0.0, '#fbe3b4'), (0.05, '#f6daa6'), (0.16, '#d8c8b4'), (0.4, '#9fb4d0'), (0.9, '#6f8fc0')],
          glow_amt=0.3, fog=1 / 450, fog_ground=1.0, fog_h=4.0, beams=0.0, lit=(1.12, 1.03, 0.9), shadow=(0.5, 0.42, 0.42), shade='#4a3030',
          bands=(0.12, 0.36), amb=0.35, sun_str=1.2, rim_amt=1.4, kuwa=4)
    rnd = random.Random(8)
    mat = toon('mat', stripes('#d8b26a', '#a88048', 60.0, 0, '#6a4a28', 8.0), nscale=20, namt=0.08, rim=0.2)
    bx('mat', (0, 0.2, 0.006), (2.2, 1.6, 0.012), mat, bev=0.004)
    ground = toon('ground', '#b88a5c', nscale=0.8, namt=0.15, rim=0.2)
    ground_plane('ground', ground, -30, 30, -5, 80, amp=0.05)
    wv = toon('weave', woven('#dcb46e', '#a67c40', 190.0), nscale=20, namt=0.08, rim=1.2)
    wvd = toon('weave_d', woven('#c4a064', '#94703e', 190.0), nscale=20, namt=0.08, rim=0.8)
    rimm = toon('brim', '#b08a4a', nscale=30, namt=0.1, rim=1.2)
    basket_obj('good', (-0.3, 0.25, 0.012), wv, rimm, r=0.24, h=0.2)
    basket_obj('poor', (0.34, 0.3, 0.012), wvd, rimm, r=0.22, h=0.18)
    gold = toon('date_gold', '#c8801e', nscale=20, namt=0.06, rim=2.4, lit='#e8a032', bands=(0.1, 0.3))
    red = toon('date_red', '#8e2a12', nscale=20, namt=0.06, rim=2.4, lit='#b43c1a', bands=(0.1, 0.3))
    amber = toon('date_amber', '#b0561a', nscale=20, namt=0.06, rim=2.4, lit='#d06a22', bands=(0.1, 0.3))
    for i, m in enumerate((gold, red, amber)):
        dates_heap('gd%d' % i, m, (-0.3, 0.25, 0.15), 0.21, 45, rnd, top=0.1, size=(0.017, 0.017, 0.032))
    dry = toon('date_dry', '#6a5444', nscale=60, namt=0.35, rim=0.3, lit='#7e6a58', shadow='#40302a')
    dry2 = toon('date_dry2', '#857060', nscale=60, namt=0.35, rim=0.3, lit='#958070', shadow='#4a3a30')
    for i, m in enumerate((dry, dry2)):
        dates_heap('pd%d' % i, m, (0.34, 0.3, 0.13), 0.17, 34, rnd, top=0.035, size=(0.017, 0.017, 0.027), dry=True)
    brk = toon('broken_stalk', '#8a7a52', rim=0.5, namt=0.2)
    bm = bmesh.new(); tube(bm, [(0.28, 0.25, 0.14), (0.36, 0.28, 0.16), (0.45, 0.26, 0.2)], 0.008, 6); obj('bstalk', mesh_bm('bstalk', bm, brk))
    for i in range(4): dates_heap('gl%d' % i, (gold, red)[i % 2], (-0.55 + i * 0.06, -0.02 - (i % 2) * 0.05, 0.03), 0.01, 1, rnd, top=0.0, size=(0.018, 0.018, 0.028))
    spot('sunpatch', (-0.9, -0.6, 2.2), (-0.3, 0.25, 0.1), '#ffd89a', 900, 0.32, 0.5, 0.15)
    M = dict(trunk=toon('trunk', '#7a5a3a', nscale=8, namt=0.2, rim=1.2), frond=toon('frond_dry', '#b89a5a', nscale=4, namt=0.2, rim=1.0))
    palm_trunk('pillar', (1.2, 1.6, 0), (1.2, 1.6, 2.6), 0.13, M['trunk'])
    pm = palms_day(1.2)
    for i, (x, y, s) in enumerate(((-3, 8, 1.2), (2.5, 10, 1.3), (-7, 14, 1.4), (6, 16, 1.3), (0, 20, 1.5))):
        inst('palm%d' % i, pm[i % 3], (x, y, 0), (0, 0, rnd.uniform(0, 6.3)), s)
    wall = toon('wall', '#d0a070', nscale=1.5, namt=0.15, rim=0.8)
    bx('yard_wall', (0, 6, 0.9), (30, 0.5, 1.8), wall, bev=0.08)
    cam = camera((0.02, -0.95, 0.72), (0.02, 0.3, 0.12), lens=38)
    cam.data.dof.use_dof = True; cam.data.dof.focus_distance = 1.3; cam.data.dof.aperture_fstop = 2.8

# ------------------------------------------------------------------ 7. the front door, open and welcoming
def bundle(name, loc, mat, knot_mat, s=1.0, rot=0.0):
    """traveller's cloth bundle: a soft squarish sack tied at the top with two ears"""
    o = cushion(name, loc, (0.42, 0.34, 0.3), mat, rot=rot); o.scale = (s,) * 3; o.location.z += 0.15 * s
    bm = bmesh.new(); bm_cone(bm, TRS((0, 0, 0.13)), 0.07, 0.03, 0.1, 10)
    ellip(bm, (0.08, 0, 0.2), (0.1, 0.035, 0.05), 10, 6, (0, 0.6, 0)); ellip(bm, (-0.08, 0, 0.2), (0.1, 0.035, 0.05), 10, 6, (0, -0.6, 0))
    bm_cone(bm, TRS((0, 0, 0.1)), 0.075, 0.075, 0.03, 12)
    k = obj(name + '_knot', mesh_bm(name + '_knot', bm, knot_mat)); k.parent = o
    return o

def house_shell(name, loc, size, mat, holes, wall_t=0.3, bev=0.05):
    """clay house with a hollow room inside (so openings show an interior)"""
    w, d, h = size
    o = bx(name, (loc[0], loc[1] + d / 2, loc[2] + h / 2), (w, d, h), mat, bev=0)
    room = cutter(name + '_room', (loc[0], loc[1] + d / 2, loc[2] + (h - 0.3) / 2 + 0.05), (w - 2 * wall_t, d - 2 * wall_t, h - 0.3))
    cut(o, [room] + holes, bev)
    return o

@scene_a
def sc_house_door():
    day_P(sun=(-0.75, -0.55, 0.3), sun_r=0.04, clouds=0.6, cloud_cov=0.56,
          sky=[(-0.12, '#e9b27a'), (0.0, '#fbd592'), (0.05, '#f7c47e'), (0.16, '#eaa878'), (0.36, '#b49cae'), (0.8, '#7488b4')],
          glow_amt=0.5, fog=1 / 900, beams=0.0, rim_amt=1.4, amb=0.4, sun_str=3.0)
    rnd = random.Random(31)
    wall = toon('wall', '#d8a46e', nscale=1.5, namt=0.15, rim=0.8)
    inner = toon('inner', '#e0a060', nscale=1.5, namt=0.1, rim=0.3, lit='#ffc070', shadow='#c07838')
    house_shell('house', (0, 0, 0), (7.0, 5.0, 3.3), wall, arch_hole('door', 0, 0.15, 0.0, 1.4, 2.4, 0.8) + arch_hole('win', 2.2, 0.15, 1.2, 0.7, 1.0, 0.8))
    bx('parapet', (0, 2.5, 3.38), (7.2, 5.2, 0.14), wall, bev=0.04)
    bx('inner_back', (0, 4.6, 1.5), (6.3, 0.05, 3.0), inner, bev=0)
    bx('inner_floor', (0, 2.5, 0.06), (6.3, 4.3, 0.02), toon('inner_floor', '#c8884a', lit='#e8a860', shadow='#a86a3a', namt=0.1, rim=0), bev=0)
    plight('inside', (0, 2.6, 2.2), '#ffb060', 180.0, 0.5)
    dm = toon('door', '#3f7f8a', nscale=6, namt=0.2, rim=1.0)
    stud = toon('stud', '#c8a050', rim=1.2, namt=0)
    for sg in (-1, 1):  # double doors swung wide open towards the visitor
        leaf = bx('leaf%d' % sg, (0, 0, 0), (0.66, 0.06, 2.0), dm, bev=0.01)
        for k in range(3):
            st = bx('studs%d_%d' % (sg, k), (0, 0, 0), (0.56, 0.02, 0.05), stud, bev=0.005)
            st.parent = leaf; st.location = (0, -0.04, -0.6 + k * 0.6)
        hinge = Vector((sg * 0.7, -0.02, 0))
        a = sg * math.radians(62)
        leaf.rotation_euler = (0, 0, a); off = Matrix.Rotation(a, 3, 'Z') @ Vector((-sg * 0.33, 0, 0))
        leaf.location = hinge + off + Vector((0, 0, 1.0))
    mat = toon('mat', stripes('#d8b26a', '#a88048', 60.0, 0, '#6a4a28', 8.0), nscale=20, namt=0.08, rim=0.2)
    bx('mat_in', (0, 2.8, 0.075), (1.6, 1.0, 0.012), mat, bev=0.004)
    jar = glb_day('jar', 0.6); inst('jar_in', jar, (1.2, 3.8, 0.07), (0, 0, 0.3), 1.0)
    bx('step', (0, -0.25, 0.07), (1.8, 0.5, 0.14), toon('step', '#b09a80', namt=0.2, rim=0.6), bev=0.03)
    ground = toon('ground', '#c89a68', nscale=0.8, namt=0.18, rim=0.2)
    ground_plane('ground', ground, -60, 60, -12, 120, amp=0.06)
    ps = toon('pstone', '#a48c70', nscale=5, namt=0.2, rim=0.5)
    for i in range(16):
        t = i / 15; x = 0.3 * math.sin(t * 3) + (0.22 if i % 2 else -0.22) + rnd.uniform(-0.05, 0.05); y = -0.75 - 5.2 * t
        o = inst('ps%d' % i, rock_mesh('ps%d' % i, (0.3, 0.22, 0.025), seed=i, sub=1, rough=0.15), (x, y, 0.0), (0, 0, rnd.uniform(0, 3)))
        o.data.materials.append(ps)
    ochre = toon('cloth_ochre', '#c8862e', namt=0.15, nscale=8, rim=1.2); blue = toon('cloth_blue', '#3a5a8a', namt=0.15, nscale=8, rim=1.2)
    red = toon('cloth_red', '#a83a28', namt=0.15, nscale=8, rim=1.2); rope = toon('rope', '#8a6a3e', rim=0.8)
    bundle('b1', (-1.35, -0.75, 0), ochre, rope, 1.2, 0.3); bundle('b2', (-1.75, -0.45, 0), blue, rope, 1.0, 1.2); bundle('b3', (1.4, -0.8, 0), red, rope, 1.1, 2.0)
    skin = toon('skin', '#8a5a30', rim=1.6, namt=0.1)
    bm = bmesh.new(); ellip(bm, (0, 0, 0.14), (0.26, 0.16, 0.14), 16, 10); bm_seg(bm, (0.24, 0, 0.16), (0.34, 0, 0.3), 0.04, 0.035, 8)
    o = obj('waterskin', mesh_bm('waterskin', bm, skin)); o.location = (1.75, -0.45, 0.0); o.rotation_euler = (0, 0, 2.6)
    stick = toon('stick', '#6a4a2a', rim=1.4)
    bm = bmesh.new(); bm_seg(bm, (0, 0, 0), (0, 0, 1.7), 0.02, 0.017, 8); o = obj('staff', mesh_bm('staff', bm, stick)); o.location = (-1.0, -0.12, 0.0); o.rotation_euler = (math.radians(-10), math.radians(-12), 0)
    pp = glb_day('pot_plant', 1.2)
    for i, (x, y) in enumerate(((-2.3, -0.35), (2.4, -0.35))): inst('pp%d' % i, pp, (x, y, 0), (0, 0, i), 0.9)
    bg = glb_day('bougainvillea', 1.2); inst('boug', bg, (3.3, -0.2, 0), (0, 0, 0), 1.0)
    pm = palms_day(1.3)
    for i, (x, y, s) in enumerate(((4.6, 1.5, 1.2), (-5.2, 3.0, 1.3), (-9, 12, 1.4), (9, 14, 1.4), (0, 22, 1.5), (-14, 25, 1.5))):
        inst('palm%d' % i, pm[i % 3], (x, y, 0), (0, 0, rnd.uniform(0, 6.3)), s)
    camera((0.35, -6.4, 1.3), (0.0, 0, 1.35), lens=30)

# ------------------------------------------------------------------ 8. the back wall with a hole (gently comic)
@scene_a
def sc_house_back():
    day_P(sun=(0.85, -0.45, 0.16), sun_r=0.045, clouds=0.6, cloud_cov=0.55,
          sky=[(-0.12, '#e6a86c'), (0.0, '#fbd08a'), (0.05, '#f3a860'), (0.15, '#e08a62'), (0.36, '#a47890'), (0.8, '#565284')],
          glow_amt=0.6, fog=1 / 900, beams=0.0, rim_amt=1.6, amb=0.35, sun_str=3.0)
    rnd = random.Random(41)
    wall = toon('wall', '#c89464', nscale=1.5, namt=0.18, rim=0.9)
    hole = cutter('hole', (0.55, 0.0, 0.95), (1, 1, 1))
    rm = rock_mesh('holeshape', (0.42, 0.6, 0.46), seed=5, sub=2, rough=0.22); hole.data = rm
    house_shell('house', (0, 0, 0), (6.5, 4.5, 3.1), wall, [hole], bev=0.04)
    bx('parapet', (0, 2.25, 3.18), (6.7, 4.7, 0.14), wall, bev=0.04)
    inner = toon('inner', '#d08a4a', namt=0.1, rim=0.0, lit='#f0a860', shadow='#8a5030')
    bx('inner_back', (0, 4.0, 1.5), (5.9, 0.05, 3.0), inner, bev=0)
    plight('inside', (0.5, 2.0, 1.4), '#ffb060', 60.0, 0.5)
    brick = toon('brick', '#b27a4c', nscale=4, namt=0.15, rim=1.0)
    for i in range(7):
        o = bx('brick%d' % i, (0.55 + rnd.uniform(-0.45, 0.45), -0.25 - rnd.uniform(0, 0.45), 0.05), (0.2, 0.1, 0.08), brick, bev=0.015,
               rot=(rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), rnd.uniform(0, 3)))
    for i in range(12):
        o = inst('crumb%d' % i, rock_mesh('crumb%d' % i, (0.05, 0.04, 0.03), seed=i + 20, sub=1), (0.55 + rnd.uniform(-0.6, 0.6), -0.1 - rnd.uniform(0, 0.6), 0.0))
        o.data.materials.append(brick)
    wood = toon('wood', '#8a6038', nscale=10, namt=0.18, rim=1.2)
    for sg in (-1, 1): palm_trunk('rail%d' % sg, (-1.25 + sg * 0.2, -0.75, 0.0), (-1.25 + sg * 0.2, -0.12, 2.6), 0.03, wood, rings=False)
    for k in range(7):
        z = 0.3 + k * 0.33; y = -0.75 + (0.63) * (z / 2.6)
        palm_trunk('rung%d' % k, (-1.49, y, z), (-1.01, y, z), 0.022, wood, rings=False)
    gm = glb_day('grass_a', 1.2); wf = glb_day('wildflowers', 1.2); gb = glb_day('grass_b', 1.2)
    for i in range(60):
        x = rnd.uniform(-3.4, 3.4); y = rnd.uniform(-2.5, -0.15)
        if abs(x - 0.55) < 0.4 and y > -0.7: continue
        inst('w%d' % i, (gm, wf, gb)[i % 3], (x, y, 0), (0, 0, rnd.uniform(0, 6)), rnd.uniform(0.9, 1.8))
    sb, sw, sd = sparrow_mats()
    S().view_layers[0].update()
    dg = bpy.context.evaluated_depsgraph_get()
    hit = S().ray_cast(dg, Vector((0.42, 0.06, 1.0)), Vector((0, 0, -1)))
    zb = hit[1].z if hit[0] else 0.62
    print('hole bottom', zb)
    sparrow('sp1', sb, sw, sd, (0.4, 0.0, zb), rot=math.radians(62), s=2.6)
    ground = toon('ground', '#b8885a', nscale=0.8, namt=0.18, rim=0.2)
    ground_plane('ground', ground, -60, 60, -12, 120, amp=0.06)
    pot = glb_day('jar_b', 1.0); inst('pot', pot, (2.3, -0.4, 0), (0, 0, 1), 0.8)
    pm = palms_day(1.4)
    for i, (x, y, s) in enumerate(((-4.4, 1.0, 1.2), (4.2, 2.5, 1.3), (-9, 12, 1.4), (9, 14, 1.4), (-16, 22, 1.5), (15, 26, 1.5))):
        inst('palm%d' % i, pm[i % 3], (x, y, 0), (0, 0, rnd.uniform(0, 6.3)), s)
    camera((-0.3, -3.9, 1.2), (0.25, 0, 1.25), lens=28)

# ------------------------------------------------------------------ 9. the open prayer place and the turning light
@scene_a
def sc_qibla_ground():
    day_P(sun=(-0.9, 0.35, 0.3), sun_r=0.04, clouds=0.5, cloud_cov=0.57,
          sky=[(-0.12, '#e9b27a'), (0.0, '#fbe0a8'), (0.05, '#f6cf8e'), (0.16, '#e6b48a'), (0.36, '#a6a6c0'), (0.8, '#6c86b8')],
          glow_amt=0.5, fog=1 / 900, beams=0.0, rim_amt=1.5, amb=0.4, sun_str=3.2, bloom=0.7)
    rnd = random.Random(51)
    M = dict(trunk=toon('trunk', '#7a5a3a', nscale=8, namt=0.2, rim=1.2), frond=toon('frond_dry', '#b89a5a', nscale=4, namt=0.2, rim=1.0))
    xs = (-3.3, 0.0, 3.3); ys = (4.6, 7.0)
    for x in xs:
        for y in ys: palm_trunk('p%d_%d' % (int(x * 10), int(y * 10)), (x, y, 0), (x, y, 2.9), 0.14, M['trunk'])
    for y in ys: palm_trunk('beam%d' % int(y * 10), (-3.8, y, 2.9), (3.8, y, 2.9), 0.1, M['trunk'], rings=False)
    fronds_roof('roof', -3.9, 3.9, 4.2, 7.4, 3.0, M['frond'], rnd, gap=0.1)
    sand = toon('sand', '#d4a46c', nscale=0.6, namt=0.16, rim=0.2)
    ground_plane('ground', sand, -60, 60, -12, 120, amp=0.05)
    wall = toon('wall', '#c8966a', nscale=1.5, namt=0.15, rim=0.8)
    bx('wall_back', (0, 8.2, 0.7), (11, 0.4, 1.4), wall, bev=0.06); bx('wall_r', (5.3, 3.5, 0.7), (0.4, 9.8, 1.4), wall, bev=0.06)
    bx('wall_l', (-5.3, 5.5, 0.7), (0.4, 5.8, 1.4), wall, bev=0.06)
    ma = toon('pmat', stripes('#d8b26a', '#b08848', 70.0, 0, '#7a5230', 7.0), nscale=20, namt=0.08, rim=0.3)
    mb = toon('pmat2', stripes('#c8a060', '#a07a40', 70.0, 0, '#6a4a28', 7.0), nscale=20, namt=0.08, rim=0.3)
    for r, y in enumerate((2.4, 3.4, 4.9, 5.9)):
        for k in range(6):
            bx('mat%d_%d' % (r, k), (-2.75 + k * 1.1, y, 0.008), (1.0, 0.75, 0.014), ma if (k + r) % 2 else mb, bev=0.003)
    # the turning light: a glowing path on the ground sweeping round from the far side (north) to the near side (south)
    cx, cy, R = 0.0, 3.9, 2.3
    a0, a1 = math.radians(95), math.radians(-75)
    def rib_alpha(g, geo):
        x, y, z = g.sep(geo.outputs['Position'])
        ang = g.node('ShaderNodeMath', operation='ARCTAN2'); g.put(ang.inputs[0], g.math('SUBTRACT', y, cy)); g.put(ang.inputs[1], g.math('SUBTRACT', x, cx))
        a = g.mr(ang.outputs[0], a0, a1, 0.15, 1.0)
        lw = g.node('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.2
        return g.math('MULTIPLY', a, 0.9)
    rib = toon('ribbon', '#ffd784', flat=True, lit=lin('#ffe39a', 2.2), rim=0, namt=0, fog=0.2, alpha=rib_alpha)
    bm = bmesh.new(); rows = []
    for i in range(121):
        t = i / 120; a = a0 + (a1 - a0) * t
        hw = 0.07 + 0.16 * t
        c = Vector((cx + R * math.cos(a), cy + R * math.sin(a), 0.06))
        n = Vector((math.cos(a), math.sin(a), 0))
        rows.append((bm.verts.new(c - n * hw), bm.verts.new(c + n * hw)))
    for (p0, p1), (q0, q1) in zip(rows[:-1], rows[1:]): bm.faces.new((p0, q0, q1, p1))
    tdir = Vector((math.sin(a1), -math.cos(a1), 0)) * -1  # direction of travel at the end (clockwise)
    tdir = Vector((-math.sin(a1), math.cos(a1), 0)) * (-1)
    e = Vector((cx + R * math.cos(a1), cy + R * math.sin(a1), 0.06)); n = Vector((math.cos(a1), math.sin(a1), 0))
    tri = [bm.verts.new(e - n * 0.42), bm.verts.new(e + n * 0.42), bm.verts.new(e + tdir * 0.55)]
    bm.faces.new(tri)
    obj('ribbon', mesh_bm('ribbon', bm, rib, smooth=False))
    plight('glow_end', e + Vector((0, 0, 0.5)), '#ffd070', 60.0, 0.5, shadow=False)
    sp = glow('spark', '#fff0c0', 2.5)
    bm = bmesh.new()
    for i in range(60):
        t = rnd.random() ** 0.6; a = a0 + (a1 - a0) * t
        c = Vector((cx + R * math.cos(a), cy + R * math.sin(a), 0.1)) + Vector((rnd.gauss(0, 0.12), rnd.gauss(0, 0.12), abs(rnd.gauss(0, 0.5))))
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.012 + 0.02 * t * rnd.random(), matrix=Matrix.Translation(c))
    obj('sparks', mesh_bm('sparks', bm, sp))
    pm = palms_day(1.3)
    for i, (x, y, s) in enumerate(((-6.5, 10, 1.3), (6.8, 11, 1.4), (-2, 13, 1.5), (3, 16, 1.4), (-10, 18, 1.5), (11, 20, 1.5), (-6.8, -2, 1.2))):
        inst('palm%d' % i, pm[i % 3], (x, y, 0), (0, 0, rnd.uniform(0, 6.3)), s)
    camera((-2.4, -3.9, 2.9), (0.3, 3.9, 0.55), lens=26)

# ------------------------------------------------------------------ 12. the old book on its stand by the window (cover vista)
def book_half(name, side, mats, rnd, W=0.2, H=0.27, ang=math.radians(38), crotch=Vector((0, 0, 0))):
    """one open half of the book: cover, curved page block and suggestive 'lines' (not text)"""
    cover, page, ink, gold = mats
    root = link(bpy.data.objects.new(name, None)); root.location = crotch
    root.rotation_euler = (0, -side * ang, 0)
    pz = lambda u: 0.02 + 0.014 * math.exp(-u / 0.035) - 0.004 * (u / W) ** 2
    bm = bmesh.new(); bm_cube(bm, TRS((side * (W / 2 + 0.005), 0, 0.003), s=(W + 0.012, H + 0.014, 0.006)))
    o = obj(name + '_cover', mesh_bm(name + '_cover', bm, cover, smooth=False)); o.parent = root
    bm = bmesh.new(); nu, nv = 24, 8; vs = []
    for j in range(nv + 1):
        for i in range(nu + 1):
            u = W * i / nu; vs.append(bm.verts.new((side * u, -H / 2 + H * j / nv, pz(u))))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i; f = (vs[a], vs[a + 1], vs[a + nu + 2], vs[a + nu + 1]); bm.faces.new(f if side > 0 else tuple(reversed(f)))
    for i in range(nu):  # edge of the page block
        for yy in (-H / 2, H / 2):
            u0, u1 = W * i / nu, W * (i + 1) / nu
            q = [bm.verts.new(p) for p in ((side * u0, yy, 0.006), (side * u1, yy, 0.006), (side * u1, yy, pz(u1)), (side * u0, yy, pz(u0)))]; bm.faces.new(q)
    q = [bm.verts.new(p) for p in ((side * W, -H / 2, 0.006), (side * W, H / 2, 0.006), (side * W, H / 2, pz(W)), (side * W, -H / 2, pz(W)))]; bm.faces.new(q)
    o = obj(name + '_pages', mesh_bm(name + '_pages', bm, page)); o.parent = root
    bm = bmesh.new()
    rows = 13; y0 = H / 2 - 0.05
    for r in range(rows):
        y = y0 - r * 0.0155; u = 0.028
        while u < W - 0.02:
            L = rnd.uniform(0.012, 0.04)
            if u + L > W - 0.018: L = W - 0.018 - u
            if L > 0.005:
                for k in range(3):
                    a0 = u + L * k / 3; a1 = u + L * (k + 1) / 3
                    wob = 0.0012 * math.sin(r * 3 + a0 * 300)
                    v = [bm.verts.new((side * a0, y + wob - 0.0017, pz(a0) + 0.0006)), bm.verts.new((side * a1, y + wob - 0.0017, pz(a1) + 0.0006)),
                         bm.verts.new((side * a1, y + wob + 0.0017, pz(a1) + 0.0006)), bm.verts.new((side * a0, y + wob + 0.0017, pz(a0) + 0.0006))]
                    bm.faces.new(v if side > 0 else list(reversed(v)))
            u += L + rnd.uniform(0.006, 0.012)
    o = obj(name + '_ink', mesh_bm(name + '_ink', bm, ink, smooth=False)); o.parent = root
    bm = bmesh.new()
    for (u0, u1, yy, hh) in ((0.03, W - 0.02, H / 2 - 0.028, 0.012), (0.024, W - 0.014, -H / 2 + 0.02, 0.003), (0.024, W - 0.014, H / 2 - 0.016, 0.003)):
        for k in range(6):
            a0 = u0 + (u1 - u0) * k / 6; a1 = u0 + (u1 - u0) * (k + 1) / 6
            v = [bm.verts.new((side * a0, yy - hh, pz(a0) + 0.0007)), bm.verts.new((side * a1, yy - hh, pz(a1) + 0.0007)),
                 bm.verts.new((side * a1, yy + hh, pz(a1) + 0.0007)), bm.verts.new((side * a0, yy + hh, pz(a0) + 0.0007))]
            bm.faces.new(v if side > 0 else list(reversed(v)))
    o = obj(name + '_gold', mesh_bm(name + '_gold', bm, gold, smooth=False)); o.parent = root
    return root

@scene_a
def sc_story_book():
    day_P(sun=(-0.45, 1.0, 0.2), sun_r=0.045, clouds=0.55, cloud_cov=0.56,
          sky=[(-0.12, '#e9b27a'), (0.0, '#fbd592'), (0.05, '#f5bc72'), (0.16, '#e39a72'), (0.36, '#a894a8'), (0.8, '#6c7fae')],
          glow_amt=0.85, glow_pow=5.0, fog=1 / 700, fog_ground=1.4, fog_h=5.0, beams=0.3, rim_amt=1.6, amb=0.3, sun_str=3.4, bloom=0.6,
          shadow=(0.42, 0.3, 0.3), shade='#3a2018')
    rnd = random.Random(61)
    wall = toon('wall', '#c88a58', nscale=1.5, namt=0.15, rim=0.6)
    back = bx('wall_back', (0, 1.6, 1.6), (6, 0.4, 3.2), wall, bev=0)
    cut(back, arch_hole('win', -0.4, 1.6, 0.3, 1.2, 1.8), 0.04)
    bx('wall_side', (1.6, 0.0, 1.6), (0.4, 4.0, 3.2), wall, bev=0.03)
    wood = toon('wood', '#7a4e2c', nscale=10, namt=0.15, rim=1.2)
    bx('sill', (-0.4, 1.4, 0.28), (1.4, 0.2, 0.05), wood, bev=0.01)
    floor = toon('floor', '#9a6a40', nscale=3, namt=0.15, rim=0.1)
    bx('floor', (0, 0, -0.02), (6, 6, 0.04), floor, bev=0)
    mat = toon('mat', stripes('#c8505a', '#8a2a30', 40.0, 0, '#e0b060', 6.0), nscale=20, namt=0.08, rim=0.2)
    bx('rug', (0.2, 0.35, 0.006), (1.3, 1.0, 0.012), mat, bev=0.004)
    # rahl (folding X book stand), its spine pointing at the viewer; the book sits in the upper V
    stand = toon('stand', '#8a5630', nscale=12, namt=0.15, rim=1.4)
    cx, cy, cz = 0.2, 0.42, 0.24; A = math.radians(40)
    piv = link(bpy.data.objects.new('rahl', None)); piv.location = (cx, cy, cz); piv.rotation_euler = (0, 0, math.radians(28))
    for sg in (-1, 1):
        o = bx('rahl%d' % sg, (0, 0, 0), (0.7, 0.32, 0.018), stand, bev=0.006, rot=(0, sg * A, 0)); o.parent = piv
    cov = toon('cover', '#2f5a3e', rim=1.2, namt=0.1); page = toon('page', '#f6e8c4', rim=0.6, namt=0.05, nscale=30, lit='#fff4d4')
    ink = toon('ink', '#4a3020', flat=True, lit='#5a3a24', rim=0, namt=0); gold = toon('pgold', '#c89030', flat=True, lit='#d8a040', rim=0, namt=0)
    for sg in (-1, 1):
        r = book_half('book%d' % sg, sg, (cov, page, ink, gold), rnd, W=0.25, H=0.34, crotch=Vector((0, 0, 0)), ang=A)
        r.parent = piv
        r.location = Matrix.Rotation(-sg * A, 3, 'Y') @ Vector((0, 0, 0.012))
    # the whole stand leans back a little towards the window
    bpy.context.view_layer.update()
    # sunbeam through the window + floating dust
    beam = toon('beam', '#ffd890', flat=True, lit=lin('#ffe0a0', 1.3), rim=0, namt=0, fog=0,
                alpha=lambda g, geo: g.mr(g.sep(geo.outputs['Position'])[1], 1.5, -0.4, 0.13, 0.0))
    d = -sunv(); bm = bmesh.new()
    corners = [Vector((-0.98, 1.42, 0.33)), Vector((0.18, 1.42, 0.33)), Vector((0.18, 1.42, 1.5)), Vector((-0.98, 1.42, 1.5))]
    a = [bm.verts.new(c) for c in corners]; b = [bm.verts.new(c + d * 2.2) for c in corners]
    for i in range(4): bm.faces.new((a[i], a[(i + 1) % 4], b[(i + 1) % 4], b[i]))
    obj('beam', mesh_bm('beam', bm, beam, smooth=False))
    dust = glow('dust', '#fff0c8', 1.8)
    bm = bmesh.new()
    for i in range(45):
        t = rnd.random() * 0.8; c = corners[0].lerp(corners[2], rnd.random()) + d * (t * 1.8)
        c.x = rnd.uniform(-0.8, 0.1) + d.x * t * 1.8
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rnd.uniform(0.002, 0.005), matrix=Matrix.Translation(c))
    obj('dust', mesh_bm('dust', bm, dust))
    # garden outside
    fields = toon('fields', '#6f8a3a', nscale=0.2, namt=0.18, rim=0.3)
    heightfield('garden', -300, 300, 2.0, 900, 60, 60, lambda x, y: -1.0 + 0.8 * fbm(x / 30, y / 30, 3, 2), fields)
    pm = palms_day(1.5)
    scatter_palms(pm, rnd, 60, (-60, 40), (6, 160), (1.1, 1.6), zf=lambda x, y: -0.9)
    hills = toon('hills', '#9a88a0', nscale=0.01, namt=0.1, rim=0.3)
    ridge('hills', 600, 2000, 400, 40, hills, seed=81, x0=0, sharp=False, freq=4.0, base=0.3)
    jar = glb_day('jar', 0.8); inst('jar', jar, (1.15, 1.2, 0.0), (0, 0, 2.0), 0.9)
    camera((0.56, -0.47, 0.86), (-0.1, 0.95, 0.5), lens=24, shift=(0, 0.05))
