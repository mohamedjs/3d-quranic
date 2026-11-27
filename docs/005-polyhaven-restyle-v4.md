# 005 — Restyle v4: the whole game with Poly Haven assets
Status: Ready (milestone by milestone)     Builds on: docs/art-direction.md, docs/001, docs/002, docs/003, docs/004

Owner's request (2026-11-26): change every character, all the graphic design and the whole
space/world of the game, using assets downloaded from https://polyhaven.com (CC0). Gemini 4 Neon
implements; if Neon runs out of credit, Claude implements by hand. Starts automatically 19:00 EET.

Executor: Gemini 4 Neon XHigh (`gemini-4-neon-xhigh` via `~/.claude/skills/delegate/delegate.sh`).
Orchestrator/reviewer: Claude Opus 5.5. Fallback executor: Claude (same doc, same checks).
Branch: `restyle-v4` (cut from `restyle-v3` @ d66042c).

---

## 0. What Poly Haven can and cannot give us (checked against api.polyhaven.com, 2026-11-26)

Catalog: 522 models, 872 textures, 999 HDRIs, all CC0 (no attribution required; we credit anyway).

| Need | From Poly Haven? | Source |
|---|---|---|
| Sky, sun, ambient light, reflections | ✓ HDRIs (sunrise-sunset, outdoor, clear/partly cloudy, `_puresky` variants) | Poly Haven |
| Ground: mud, sand, dirt paths, field soil, river bank | ✓ `brown_mud*`, `brown_mud_dry`, `aerial_sand`, `coast_sand_0x`, `clean_pebbles`, `bicolour_gravel`, `cobblestone_*` | Poly Haven |
| House walls, floors, roofs | ✓ textures `clay_plaster`, `clay_block_wall`, `clay_floor_001`, `blue_plaster_weathered`, `blue_plaster_wall`, `beige_wall_00x`, `brick_wall_*`, wood planks, `bamboo_wall*` | textures from Poly Haven, **geometry from Blender** |
| Rocks, boulders, cliffs, horizon | ✓ `namaqualand_boulder_0x`, `rock_0x`, `sand_rocks_small_01`, `rock_face_0x`, `namaqualand_cliff_0x`, `mountainside` | Poly Haven |
| Shrubs, grass, flowers, ground cover | ✓ `shrub_01..04`, `grass_medium_0x`, `grass_bermuda_01`, `fern_02`, flower_* , `nettle_plant`, `moss_01` | Poly Haven |
| Broadleaf trees (sycamore/acacia stand-ins) | ◐ `jacaranda_tree`, `island_tree_0x`, `tree_small_02`, `searsia_*`, stumps | Poly Haven (heavily decimated) |
| **Date palms** | ✗ none exist | Blender, with Poly Haven `bark_*` texture |
| Village props | ✓ `brass_pot_01/02`, `brass_pan_01`, `brass_diya_lantern`, `Lantern_01`, `ceramic_pot`, `ceramic_vase_0x`, `antique_ceramic_vase_01`, `planter_pot_clay`, `pot_enamel_01`, `folding_wooden_stool`, `painted_wooden_bench`, `painted_wooden_stool`, `Barrel_0x`, `stone_fire_pit`, `dry_branches_medium_01` | Poly Haven |
| **Characters (people)** | ✗ none — the "rigged" category is clocks/tools/a cannon | **Blender** (rebuild of docs/001 cast), dressed with Poly Haven fabric textures (`cotton`, `linen`, `wool`, `leather`, `hessian`, `denim` categories) |
| UI / 2D graphic design | ✗ not Poly Haven's domain | Hand-built (CSS/SVG), new design in M6 |

**Content filter (hard rule, applies to every download):** never fetch or use statues, busts or
any human/animal figure (`gothic_statue`, `marble_bust_01`, …), weapons (`cannon_01`, firearms,
`ammo_box`), church/gothic/castle-religious textures (`church_bricks_*`), alcohol or modern
signage. Nothing modern-industrial in the village (no plastic crates, propane, CCTV, power boxes,
asphalt). If unsure whether an asset fits an Egyptian Nile village before 1900, leave it out.

## R. Decisions that override earlier docs

1. **Art direction v4 — "naturalistic world, storybook people".** The world moves from
   flat/baked-toon to real PBR materials (Poly Haven albedo + normal + roughness, packed ARM)
   under a warm golden-hour HDRI, with a gentle painterly colour grade so it still feels like a
   children's film, not a photo. Characters stay stylized (big heads, warm eyes) but drop hard
   toon bands and ink outlines for soft-shaded PBR skin and real fabric textures, so they sit in
   the new world. This overrides docs/art-direction.md "not photoreal", docs/004 §2 "never noisy
   photo-scans" and docs/001 §2 "no downloads, no external assets". The palette in
   art-direction.md stays the target for the colour grade and the UI.
2. Still binding from docs/004 §R: Lite is what most children see and must look better every
   milestone; Lite budgets are hard limits; locked positions (`HOME`, `MASTABA`, every encounter
   position, river/canal/oasis topology); walkability changes bump `SET_VERSION` in
   `src/game/world/coins.js` and re-run `__game.balance({verify:true})` (every story
   `reached: true`, `coins >= 20`, `notWalkable: 0`, `unreachable: 0`); zero new npm
   dependencies; never depict prophets/companions; no faces or figures in the environment;
   Quran text only from Quran.com at runtime.
3. One milestone per executor run. After each milestone: checks in §6 pass → commit locally on
   `restyle-v4` (`v4 M<n>: …`), never push. Checks fail after two fix rounds → stop, write the
   reason under §9 and report.
4. The executor does not edit this doc. Claude appends answers to §9.

## 1. Budgets

| Tier | Tris on screen | Draw calls | New texture download | Texture size |
|---|---|---|---|---|
| Lite | ≤ 180k | ≤ 140 | ≤ 6 MB total (precached) | 512 |
| Medium | ≤ 350k | ≤ 220 | lazy | 1024 |
| High/Ultra | ≤ 700k | ≤ 320 | lazy | 1024 / 2048 |

Per asset after processing: props ≤ 1.5k tris (Lite LOD) / 5k (High); rocks ≤ 800 / 3k;
shrubs ≤ 600 / 2k (instanced); trees ≤ 4k / 12k; characters ≤ 9k each. HDRI shipped as an
equirect 1k (Lite) / 2k (High) `.webp` LDR + precomputed PMREM at load, never the raw `.hdr`/`.exr`
in `public/`. Measure with `renderer.info` in game.

## 2. Structure

```
tools/polyhaven/
  manifest.json      every asset we use: id, type, resolution fetched, role in game, tiers
  fetch.py           reads manifest, downloads via https://api.polyhaven.com/files/<id> into
                     .cache/polyhaven/<id>/ (one empty dir per asset), verifies md5 from the API
  process_models.py  Blender headless: import glTF, apply content filter, decimate to budget,
                     make LOD0/LOD1, bake/pack textures, export Draco GLB (level 6)
  process_textures.py  resize to 512/1024/2048, pack ARM (AO/rough/metal), write .webp
  process_hdri.py    tonemap HDRI → LDR equirect webp 1k/2k, write sun direction/colour json
  CREDITS.md         list of all Poly Haven assets used (CC0, credit Poly Haven + authors)
.cache/polyhaven/    raw downloads (gitignored, never in public/)
public/models/env/      processed GLBs (props, rocks, plants, trees)
public/textures/v4/{512,1024,2048}/   processed material sets
public/textures/v4/sky/  HDRI webp + sun.json
blender/v4/          palms, houses (UV-unwrapped geometry for PH textures), characters, previews
```
Scripts run with `python3 -I` (and `blender -b --python …`), from the repo root, reading the
cache by path. `.gitignore` gets `.cache/`. `tools/vite-pwa.js` SKIP adds
`^textures\/v4\/(1024|2048)\/` and `^models\/env\/.*_hi\.glb$`.

## 3. Milestones

**M0 — Pipeline + manifest.** Build `tools/polyhaven/*`, choose the concrete asset list in
`manifest.json` from §0 (respecting the filter), fetch at 2k, process everything, write
`CREDITS.md`. Proof: `blender/v4/previews/M0_contact_sheet.png` (every processed asset on a grey
floor with its tri count). No game code changes yet.

**M1 — Sky & light.** Replace `Sky.js` gradient/sun with the chosen sunset HDRI (background on
High+, gradient sampled from the HDRI on Lite), `scene.environment` from PMREM, sun direction
and colour from `sun.json`, ACES/AgX tone mapping + warm grade LUT in `Effects.jsx` (Medium+),
cheap grade in the material on Lite. Files: `environment/Sky.js`, `environment/Environment.jsx`,
`lighting/Lighting.jsx`, `lighting/environmentMap.js`, `effects/Effects.jsx`.

**M2 — Ground & water banks.** `terrainMaterial.js` becomes a splat of 4 PH sets (field mud,
dry path dirt, sand/oasis, pebble bank) driven by the existing baked path-distance texture and
height/slope; triplanar only on High. Keep per-pixel roads from docs/002. Water keeps its shader
but takes reflections from the new environment map and wet-bank darkening from the bank set.

**M3 — Buildings.** `envAssets.js` stops stripping UVs/materials for buildings: new path that
keeps UVs and assigns `MeshStandardMaterial` with PH sets (`clay_plaster`, `clay_block_wall`,
`blue_plaster_weathered`, wood planks for doors/shutters, `clay_floor_001` mastaba). Rebuild
house geometry in `blender/v4/env/houses.py` with UVs, 5+ variants (not the 3 cloned boxes),
corner wear via a second UV/vertex-colour AO mask. Landmarks (Nile bridge, oasis arish, ruins)
rebuilt with PH stone/wood. Vertex-colour toon path stays only as a Lite fallback if Lite fails
the budget.

**M4 — Props, rocks & vegetation.** Instanced PH shrubs/grass/flowers in `vegetation/`,
PH rocks/boulders along river and horizon (replace `backdrop_hills` with `namaqualand_cliff`/
`mountainside` ring, 3 haze layers), PH props dressing story spots (≥ 2.0 m clear of every
storyteller, path walkable). Date palms rebuilt in Blender with PH bark. Broadleaf trees from
PH `jacaranda_tree`/`island_tree_*` recoloured green and decimated.

**M5 — Characters.** Rebuild the 7-character cast from docs/001/003 (player, farmer,
grandma_zainab, grandma, trader, sheikh, aunt) in `blender/v4/characters/` — same export names,
skeleton, clip names (idle, walk, run, talk, sit, sit_talk) and `public/models/*.glb` paths so
`glbRig.js` keeps working. New look per §R1; garments use PH fabric textures (cotton galabiya,
linen tarha/hijab, wool vest, leather sandals). Hijab/modest dress rules from docs/001 stay.
Proof: `lineup.png`, `<key>_turn.png`, `<key>_face.png`, and in-game screenshots.

**M6 — Graphic design / UI.** New UI pass on `ui/style.css`, `ui/clay.css`, `ui/scenes.js`,
title screen and dock icons to match the v4 world: keep teal-glass + gold from art-direction.md,
add the ornamental verse frame, lesson chip, medal art and a painted title backdrop rendered from
the new 3D world (Blender or in-game capture, no people). Arabic RTL first, Tajawal / Amiri Quran.

## 4. Coding conventions
Match the repo: ES modules, 2-space indent, no TypeScript, comments only for the non-obvious.
New loaders go through `src/game/world/loaders.js`. Quality tiers read from `systems/quality.js`.
No new npm packages (three's own `KTX2Loader`/`DRACOLoader` in `three/examples` are allowed).

## 5. Out of scope
Story content, audio, encounters.json data, Android project, deploy config. No `git push`, no
deploy, no Facebook posts.

## 6. Acceptance checks (every milestone)
1. `npm run build` passes.
2. `__game.balance({verify:true})` all green (see §R2).
3. Headless Chromium + SwiftShader screenshots (docs/002 §10 method) on `lite` and `high`:
   `blender/v4/previews/M<n>_{lite,high}_{home,street,river,oasis}.png`.
4. `renderer.info` per tier reported and within §1.
5. `git status` shows only files from §2/§3 for that milestone; `.cache/` not tracked.

## 7. Run procedure (used by the 19:00 scheduled task)
1. `git checkout restyle-v4` in `/var/www/html/old/3d-quranic`.
2. For each milestone M0…M6 in order, skipping ones already committed (`git log --oneline`):
   `~/.claude/skills/delegate/delegate.sh build gemini-4-neon-xhigh docs/005-polyhaven-restyle-v4.md`
   with the milestone named in the reply message (`reply … "Do milestone M<n> only"`).
3. On a quota / rate-limit / credit error from agy: try `gemini-4-neon-high`, then
   `gemini-4-argon-high`; if all fail, Claude implements the milestone itself.
4. Review the diff against this doc, run §6 yourself, fix or send fixes with `reply`, commit.
5. Stop at the first milestone that fails twice, or when Claude usage ≥ 85%; write a handoff in §9.

## 8. Credits
All Poly Haven assets are CC0. `tools/polyhaven/CREDITS.md` lists each asset id, author and URL,
and the in-game About/privacy page gets one line: "Environment assets: Poly Haven (CC0)".

## 9. Decisions / log
(appended by Claude during the runs)

### M0 run decisions (done)
Do M0 (§3) and nothing from M1 onward, then stop and report. No file under `src/` changes in M0.

Decisions for M0 (binding):
1. **Python.** Run `fetch.py` and `process_textures.py` with `python3 -I`. System Python has `requests`
   and PIL but no numpy, OpenEXR or imageio, so it cannot read `.hdr`/`.exr`: `process_hdri.py` and
   `process_models.py` run as `blender -b --factory-startup --python tools/polyhaven/<script>.py`
   (Blender's Python has numpy and image I/O). Every script is self-contained: no sibling imports.
2. **Downloads.** Fetch 2k only, never 4k/8k (disk is nearly full). One directory per asset,
   `.cache/polyhaven/<id>/`, verify every file's md5; a re-run skips files whose md5 already matches.
   Send a generic `User-Agent` (`asset-fetcher/1.0`) with no names, e-mail or project name.
3. **Content filter (hard rule, §0).** No statues, busts, human or animal figures, weapons, church /
   religious-building textures, alcohol, signage or modern-industrial props. Check each id's API
   categories/tags; `fetch.py` refuses ids matching a deny list. When unsure, leave it out.
4. **Models.** Output `public/models/env/ph_<id>.glb` (Lite LOD) and `public/models/env/ph_<id>_hi.glb`
   (High LOD), triangle budgets from §1, Draco 6, textures embedded as WebP (Lite ≤ 512 px, small props
   ≤ 256 px; High ≤ 1024 px). Origin at the base centre, Y-up, real-world metres. Never overwrite or
   delete an existing file in `public/models/env/`. Decimated foliage must keep its alpha cutout and
   still read as the plant (do not collapse leaf cards into blobs; drop whole leaf cards instead).
5. **Textures.** `public/textures/v4/{512,1024,2048}/<id>_{diff,nor,arm}.webp` (nor = OpenGL
   convention, arm = AO/roughness/metal in R/G/B).
6. **HDRI.** One sunset/golden-hour sky. `public/textures/v4/sky/<id>_1k.webp` (1024×512) and
   `<id>_2k.webp` (2048×1024), tonemapped LDR, plus `sun.json`:
   `{"hdri": id, "sunDirection": [x,y,z], "sunColor": "#rrggbb", "sunElevationDeg": n,
   "exposure": n, "gradient": [{"elevationDeg": n, "color": "#rrggbb"}, … from -10 to 90],
   "ground": "#rrggbb"}`. `sunDirection` is a unit vector in three.js world space (Y up) consistent with
   three.js equirect lookup `u = atan2(z, x)/(2π) + 0.5`, `v = asin(y)/π + 0.5` (v = 1 is the top row).
7. **Lite download budget.** The precached additions (all 512 textures, the 1k sky and the `ph_*.glb`
   Lite models together) must be ≤ 6 MB. Choose the asset list to fit: prefer fewer, reusable assets
   (about 12–16 models and 14–18 texture sets, covering the needs of M2–M5, including bark for palms,
   wood, plaster, ground, and cotton/linen/wool/leather fabrics for M5). Only ship at 512 what Lite
   will really use; if it still does not fit, lower WebP quality or resolution and say so in `notes`.
8. **vite-pwa.** Add exactly the two SKIP regexes of §2.
9. **Contact sheet.** `process_models.py` renders `blender/v4/previews/M0_contact_sheet.png` (flag
   `-- --sheet`): every processed model (Lite and High) on a grey floor with its id and tri count
   labelled, texture sets as labelled swatches, and the sky as a labelled strip. Open the PNG and check
   it yourself before reporting.
10. Do not commit, do not push, do not edit this doc.

#### M0 log (2026-11-26) — passed
- Executor: Gemini 4 Neon XHigh (2 runs: build + one fix round). Reviewer: Claude.
- 33 CC0 assets (1 HDRI, 16 texture sets, 16 models). Precache core grew 5.48 → 8.64 MB (≈3.0 MB, limit 6).
- Fix round 1: foliage exported as BLEND (now MASK 0.5), foliage too sparse, `shrub_04` was four tiny plants,
  Lite wicker basket had holes, lantern had 5 primitives.
- No `src/` change, so tiers measure the same as before v4 (max over 4 spots): Lite 52 calls / 152k tris;
  High 299 calls / 1.69M tris.
- **Pre-existing before v4** (measured on d66042c's build): High is over the §1 triangle budget (1.69M vs
  700k) and `balance({verify:true})` on High reports `best-dates` `unreachable: 1`. M4 must bring both within
  limits. Lite is green: 22 stories, min 22 coins.

### M1 run decisions (done)
Do M1 (§3) and nothing from M2 onward, then stop and report. M0 is committed; build on it.

Files you may change: `src/game/environment/Sky.js`, `src/game/environment/Environment.jsx`,
`src/game/lighting/Lighting.jsx`, `src/game/lighting/environmentMap.js`, `src/game/effects/Effects.jsx`,
and `src/game/world/World.jsx` **only** for the one `gl.toneMapping` effect in `PostFX`. If the aerial
fog colours must change, set them from `Environment.jsx` through the exported `AERIAL` uniforms; do not
edit `stylizedPbr.js`. Add screenshots under `blender/v4/previews/`. Nothing else.

Decisions for M1 (binding):
1. **Loading.** `loadEnvironment()` fetches `./textures/v4/sky/sun.json` with the backdrop GLB and returns
   `{ sunDir, sun, backdropGeo }`. If the fetch fails, fall back to built-in constants (today's `SUN_DIR`
   and colours) so the game still starts. Equirect textures load through three's `TextureLoader` from a
   small cached helper in `environmentMap.js` (loaders stay in one place per file, no new npm packages):
   `_1k` for Lite/Low/Medium, `_2k` for High/Ultra, `colorSpace = SRGBColorSpace`. A tier change swaps
   textures and disposes the old PMREM target.
2. **Sun direction.** Azimuth from `sun.json`; light elevation = `max(sun.json elevation, 16°)` so streets
   and faces stay readable. One `sunDir` (the clamped one) drives lights, shadows, fog, backdrop, water
   and the visible sun disc in the sky shader.
3. **Warm grade of the sky.** The HDRI average horizon is grey-blue; art-direction.md asks for golden
   dusk. Write one `warmGrade(color, elevationDeg)` (JS for gradient stops, same formula in GLSL for the
   textured path): mix toward `#F2B86B` by 0.65 at ≤5°, 0.35 at 10°, 0.12 at 20°, 0 from 30° up
   (smooth between), and mix toward `#4D7EA8` by 0.2 above 45°.
4. **Sky shader** (one camera-following sphere, `createSky(sun, { dir, octaves, map })`):
   - Lite/Low/Medium (`map` null): gradient built from the warm-graded `sun.json` stops, plus today's
     sun halo/disc and the painterly cloud layers (keep them, tinted to the new palette).
   - High/Ultra (`map` = 2k texture): sample the equirect (three's `equirectUv` convention) through
     `warmGrade`, plus the sun halo/disc and the same cloud layers at lower opacity (the HDRI is nearly
     cloudless).
5. **IBL.** `getSkyPMREM` bakes a sphere whose upper hemisphere is the warm-graded equirect and whose
   lower hemisphere is the warm ground bounce (`#C48952` → golden-tan, as today), never the HDRI's dark
   blue ground. `scene.environment` is set on every tier (toon materials ignore it); tune
   `environmentIntensity` so Medium/High are not brighter or flatter than today.
6. **Light colour.** Directional colour = `sun.json.sunColor` mixed 35 % toward white. Keep the lavender
   sky fill / ochre ground hemisphere; retune intensities by looking at the screenshots (characters'
   faces and white galabiya must not turn orange or clip).
7. **Fog and backdrop.** `scene.fog`, `scene.background`, `AERIAL.uAerialWarm/uAerialCool/uAerialSunGlow`
   and the backdrop uniforms take their colours from the warm-graded gradient (horizon stops).
8. **Tone mapping + grade.**
   - Medium+ (`post`): `ToneMappingMode.ACES_FILMIC` replaces NEUTRAL, followed by a warm LUT built
     procedurally in `Effects.jsx` (a 17³ `LookupTexture`/`Data3DTexture` used with the `LUT` effect from
     `@react-three/postprocessing`): gently warm highlights toward `#F4C766`, slightly cool-teal deep
     shadows, saturation about +5 %. Keep Bloom, DoF, Vignette, SMAA.
   - Lite/Low (no post): a cheap warm grade applied by the renderer to every material at once:
     `gl.toneMapping = THREE.CustomToneMapping` with `THREE.ShaderChunk.tonemapping_pars_fragment`'s
     `CustomToneMapping` replaced once (module level, in `environmentMap.js`) by three's neutral curve
     plus a small warm lift. No per-material patching, no extra passes. This must run before any material
     compiles.
9. **Quality bar.** Compare your screenshots with `blender/v4/previews/M0_*.png` (same spots, today's
   look). Lite must look clearly warmer/golden and at least as bright and readable; no blown-out sky, no
   muddy shadows, UI unchanged. Lite budgets: ≤ 140 draw calls, ≤ 180k triangles. No walkability change.
10. Save your screenshots as `blender/v4/previews/M1_{lite,high}_{home,street,river,oasis}.png`. Do not
    commit, do not push, do not edit this doc.

#### M1 log (2026-11-26) — passed
- Executor: Gemini 4 Neon XHigh (1 run). Reviewer: Claude, with a small hand tune on Lite/Low only: toon sun
  colour mixed 55 % toward white (was 35 %), toon hemisphere 2.60 → 2.80, softer CustomToneMapping warm lift
  (the white galabiya had turned peach and the oasis had darkened).
- Accepted deviations: High/Ultra sky multiplies the LDR equirect by 1.32 before the grade; LUT stored as Uint8.
- Checks: build passes, precache core 8.66 MB; Lite 52 calls / 152k tris, balance green (22 stories, min 22);
  High 299 calls / 1.69M tris, balance as before v4 (`best-dates` 1 unreachable). No page errors.

### M2 run decisions (done)
Do M2 (§3) and nothing from M3 onward, then stop and report. M0 and M1 are committed; build on them.

Files you may change: `src/game/shaders/terrainMaterial.js`, `src/game/terrain/Terrain.jsx`,
`src/game/world/loaders.js`, `src/game/shaders/waterMaterial.js`, `src/game/water/Water.jsx`,
`src/game/lighting/environmentMap.js` and `src/game/environment/Environment.jsx` (the last two only to
publish the sky texture for water reflections). Add screenshots under `blender/v4/previews/`. Do not
touch `heightfield.js`, geometry, colliders or `coins.js`: no walkability change.

Decisions for M2 (binding):
1. **Layers** (array index order): 0 field mud `brown_mud_02` (3.5 m tile), 1 path dirt `brown_mud_dry`
   (2.5 m), 2 sand `coast_sand_01` (4 m), 3 pebble bank `clean_pebbles` (2 m).
2. **Texture arrays, not 12 samplers.** `loaders.js` exports `loadTextureArray(urls, { srgb, size })`
   returning a cached promise of a `THREE.DataArrayTexture` (images decoded, drawn to a canvas, packed;
   repeat wrap, mipmaps, anisotropy 4 on Medium+) plus each layer's average linear colour. Lite/Low:
   diffuse array only, from `textures/v4/512`. Medium and High: diffuse + normal + ARM from `1024`.
   Ultra: the same from `2048`. A tier change swaps arrays and disposes the old ones.
3. **Loading.** `Terrain.jsx` starts with a 1×1 placeholder and `uTexOn = 0` (today's painterly ground),
   then switches on when the arrays arrive. Never suspend or rebuild the world for textures; if a file
   fails to load, keep the painterly ground and `console.warn` once.
4. **Keep the palette.** The textures add material, they do not replace the art direction. Per layer:
   `detail = tex.rgb / layerAverage` and `albedo = painterlyColour * mix(1, detail, strength)`; on the
   road core and the pebble bank additionally mix 35–50 % toward the real texture colour, warm-graded to
   the existing `FIELD_COLORS`. Meadow greens and crop colours must stay clearly green/gold.
5. **Weights** come from what the shader already computes: road/shoulder → path dirt (keep today's
   per-pixel baked path-distance roads and their exact edges), damp/mud near water → pebble bank, desert
   mask and the oasis shore → sand, everything else (fields, meadows) → field mud at lower strength.
   Slopes (height/normal) take the sand layer. Use a little noise on the blend borders; no hard edges.
6. **Normals/roughness (Medium+).** World-space planar normal mapping on XZ (the geometry has no
   tangents) replaces today's procedural micro-normals; roughness and AO come from ARM; wet banks are
   darker and glossy using the bank set. High/Ultra only: triplanar projection for the sand layer on
   steep slopes. Fade normal strength with distance so there is no shimmer or visible tiling: break
   repetition with the existing macro noise (and a second, larger-scale lookup if needed).
7. **Water.** Keep the water shader and its tiers. Replace the body of `sampleSkyRefl` with a lookup of
   the same warm-graded equirect used by M1 (1k Lite–Medium, 2k High/Ultra), published as shared
   uniforms (`SKY_REFL = { uSkyMap, uHasSkyMap }`) from `environmentMap.js`; keep the analytic
   version as the fallback while the texture is missing, and keep the sun glint. Add wet-bank darkening
   along the waterline that matches the pebble bank. The street rill uses the same lookup.
8. **Performance.** Lite adds at most 4 array fetches per ground pixel, no normal maps, no triplanar.
   Lite budgets: ≤ 140 draw calls, ≤ 180k triangles. Check there are no shader errors on lite, medium,
   high and ultra, and that a live tier switch works.
9. **Quality bar.** Compare with `blender/v4/previews/M1_*.png`: the ground must clearly show real mud,
   sand, dirt and pebbles near the camera on Lite and High, with no obvious tiling in the distance, no
   dark or muddy overall shift, and roads as readable as before.
10. Save screenshots as `blender/v4/previews/M2_{lite,high}_{home,street,river,oasis}.png`. Do not
    commit, do not push, do not edit this doc.

#### M2 log (2026-11-26) — passed
- Executor: Gemini 4 Neon XHigh (1 run). Reviewer: Claude, no hand edits.
- Accepted deviations: water skips the planar reflection for one frame after a live tier switch (stops
  shadow-sampler GL warnings); water uniforms are merged shallowly so shared sky/fog uniforms stay live.
- Checks: build passes, precache core 8.68 MB; Lite 51 calls / 152k tris, balance green (22, min 22); Medium
  204 calls / 1.04M tris; High 299 calls / 1.69M tris; no page or shader errors on lite, medium, high.
- Also pre-existing before v4 (same on d66042c's build): Medium reports `qays-the-fasting-farmer`
  `notWalkable: 1`; Medium is over the 350k triangle budget. For M4.

### M3 run decisions (done)
Do M3 (§3) and nothing from M4 onward, then stop and report. M0–M2 are committed; build on them.
This is the milestone the owner will notice most: make the houses beautiful.

Files you may create or change (nothing else):
- `blender/v4/env/lib.py` (shared helpers: UV, AO, export), `blender/v4/env/houses.py` (houses, mastaba,
  garden wall, preview sheet), `blender/v4/env/landmarks.py` (Nile bridge, arish, ruins). Each script runs
  headless from the repo root with `blender -b --factory-startup --python <script>`. Do not save `.blend`.
- `public/models/env/{house_a,house_b,house_c,house_d,house_e,house_f,mastaba,garden_wall,river_bridge,
  oasis_arish,ruins_wall_a,ruins_wall_b,ruins_wall_c,ruins_column,ruins_arch}.glb` (overwrite existing,
  add the new ones).
- `src/game/shaders/buildingMaterial.js` (new: the only building material factory),
  `src/game/world/envAssets.js`, `src/game/world/instancing.js` (only if needed),
  `src/game/world/loaders.js`, `src/game/buildings/village.js`, `src/game/world/World.jsx` (only if needed).
- `blender/v4/previews/M3_*.png`.

Decisions for M3 (binding):
1. **Material contract.** The GLBs carry geometry only (no textures, no images). Material names are the
   texture layers, in this array order: `ph_plaster` (clay_plaster, 2.5 m tile), `ph_mudbrick`
   (clay_block_wall, 2 m), `ph_blue` (blue_plaster_weathered, 2.5 m), `ph_wood` (weathered_brown_planks,
   1.6 m), `ph_floor` (clay_floor_001, 2 m), `ph_stone` (sandstone_blocks_05, 2.4 m), `ph_cloth`
   (hessian_230, 1.2 m; also reed/palm roofs, tinted), plus `ph_dark` (openings: no texture, vertex colour).
2. **UVs** are in real metres (box projection per face, V up on walls, grain along planks/beams); the
   game divides by each layer's tile size in the shader. **Vertex colour** (`COLOR_0`, linear) = painted
   tint × baked AO/wear: darker splashed base, grime under parapets and sills, softly lighter edges,
   corner occlusion. This is the second wear mask; no second UV set is needed.
3. **One material, one draw per model.** `envAssets.js` gets a `ph_` path that keeps position, normal,
   uv, colour, writes a per-vertex `aLayer` from the material name and merges all `ph_*` parts of a LOD
   into one geometry using the single building material. Everything else keeps today's paths.
4. **`buildingMaterial.js`.** Lite/Low: `MeshToonMaterial` (today's gradient) sampling the 512 diffuse
   `DataArrayTexture` (`loadTextureArray`, repeat wrap). Medium+: `MeshStandardMaterial` sampling diffuse,
   normal and ARM arrays at 1024 (High and Ultra stay at 1024 for memory), tangent frame from screen
   derivatives, AO + roughness from ARM, low `envMapIntensity` like the terrain. Keep the palette as in M2:
   `albedo = vColor * mix(1, tex/layerAverage, strength)`, mixing toward the real texture colour more for
   mudbrick, wood, stone and cloth. Aerial fog and the warm rim as on other env materials. Until arrays
   arrive show plain vertex colours (no black or grey flash); never suspend or rebuild for textures. This
   replaces the vertex-colour-only look on every tier (Lite stays textured; no separate fallback unless a
   Lite budget fails).
5. **Six house variants**, three footprints, so walkability does not change. `house_a`/`house_d` share
   house_a's current footprint, `house_b`/`house_e` share house_b's, `house_c`/`house_f` share
   house_c's (nothing solid outside today's bounding box below 2.2 m). In `village.js` the size group is
   chosen exactly as today, then the variant inside the group is picked from a hash of the position —
   **without consuming `r()`**, so every placement, collider and garden stays where it is. Grandma's
   house stays `house_a` with the same door position (x −0.59), front wall (z +2.4) and mastaba
   (x 0.05..2.55, seat 0.45 m).
6. **Look.** Egyptian Nile mudbrick, pre-1900: rounded hand-plastered walls with slight taper, real
   recessed doors and windows (geometry), plank doors and shutters (`ph_wood`, painted blue/green by
   vertex tint), wooden roof beams, parapets, patches where plaster has fallen showing `ph_mudbrick`,
   domes, outside stair, pigeon tower, reed shade — each of the six clearly different in silhouette and
   colour (whitewash, warm ochre, blue-wash base, bare mud). Geometric/floral painted folk bands only:
   no people, animals or faces. Quality bar is today's houses or better in shape detail.
7. **Budgets.** House LOD0 ≤ 4 500 tris, LOD1 (`<name>_LOD1` node, as today) ≤ 1 500; mastaba ≤ 1 000;
   garden wall ≤ 1 200 / 500; bridge ≤ 4 000 / 1 600; arish ≤ 2 000 / 800; each ruins piece ≤ 700 / 300.
   Lite ≤ 140 calls, ≤ 180k tris. High draw calls ≤ 320.
8. **Landmarks.** `river_bridge`: same size, axis, deck height (0.55) and origin as today, stone piers
   and arches (`ph_stone`) with timber deck and rails (`ph_wood`). `oasis_arish`: replaces the box
   shelter in `village.js` (posts `ph_wood`, frond/reed roof and rug bench), same spot and footprint.
   Ruins: weathered sandstone walls (3 heights: about 1.2, 2.2, 3.4 m, each 4 m long, 0.9 m thick),
   column, gate arch; place them from `village.js` with the same positions, heights (nearest variant +
   small y scale) and **identical colliders**; keep every existing `r()` call in the same order. The
   arish and ruins must still block the camera as today.
9. **No walkability change**: colliders byte-identical, `SET_VERSION` unchanged. Verify by comparing
   `buildVillage().colliders` before and after (they must be equal) and run `balance({verify:true})`.
10. **Proof.** `blender/v4/previews/M3_houses_sheet.png` (all new models, textured, with tri counts) and
    `M3_{lite,high}_{home,street,river,oasis}.png`. Look at them yourself and iterate until the village
    clearly looks better than `M2_*.png` (no stretched or seamed textures, no z-fighting, no black
    faces). Also check the ruins (around x 160, z −140) and the arish (x −92, z −9) in game. Do not
    commit, do not push, do not edit this doc.

#### M3 log (2026-11-26) — passed
- Executor: Gemini 4 Neon XHigh (1 run). Reviewer: Claude, no hand edits.
- Six house variants, mastaba, garden wall, bridge, arish and ruins rebuilt (geometry-only GLBs, one
  texture-array material). `buildVillage().colliders` compared with M2: 65/65 identical; `SET_VERSION`
  unchanged.
- Accepted deviations: no square capital on `ruins_column` (it is also used squashed and fallen); the
  pigeon tower's three bird spheres were dropped (§0, no animals).
- Checks: build passes, precache core 9.26 MB (+0.58 MB); Lite 55 calls / 147k tris, balance green;
  Medium 209 calls / 1.04M tris; High 306 calls / 1.68M tris (limit 320 calls), balance as before v4.

### M4 run decisions (done)
Do M4 (§3) and nothing from M5 onward, then stop and report. M0–M3 are committed; build on them.
It is a large milestone: budgets first, then beauty. Commit nothing.

Files you may create or change (nothing else):
- `blender/v4/env/{palms.py,trees.py,rocks.py,horizon.py}` and `blender/v4/env/lib.py`.
- `public/models/env/{palm_a,palm_b,palm_c,palm_d,sycamore_a,sycamore_b,acacia,bush_a,bush_b,boulder,
  rock_small,backdrop_hills}.glb` (overwrite or add). `tools/polyhaven/*`, `public/textures/v4/**` and
  `ph_*.glb` only if you must add or re-process a Poly Haven asset (same §0 filter and pipeline).
- `src/game/vegetation/*`, `src/game/world/{envAssets.js,instancing.js,loaders.js,details.js,Props.jsx,
  World.jsx}`, new `src/game/world/storySets.js`, `src/game/shaders/buildingMaterial.js`, new
  `src/game/shaders/propMaterial.js`, `src/game/environment/Environment.jsx`,
  `src/game/systems/quality.js`, and `src/game/world/coins.js` (only `SET_VERSION` and a walkability fix).
- `blender/v4/previews/M4_*.png`.

Budgets and how they are measured (binding):
- **Triangles** = main camera pass: `renderer.info.render.triangles` of `renderer.render(scene, camera)`
  for the game camera, minus what the shadow-map render inside it adds (planar reflection and shadow
  passes are reported separately, not counted). Lite ≤ 180k, Medium ≤ 350k, High ≤ 700k, at all of
  home, street, river and oasis (facing as in the M3 screenshots) and at the ruins (160, −112, facing −z).
- **Draw calls** = whole frame (`renderer.info`, all passes): Lite ≤ 140, Medium ≤ 220, High ≤ 320.
- Today, whole frame: Lite 55 calls / 147k; Medium 209 calls / 1.04M; High 306 calls / 1.68M. So Medium
  and High triangles must drop by roughly half while the world gains Poly Haven detail. Biggest items on
  High now: wheat ≈ 500k, terrain 148k (`terrainSeg` 272), rocks 36k, grass 80k. Use distance LODs,
  chunk culling, thinner crops/grass presets, a smaller `terrainSeg`, and shadow casting only near.
- New precached bytes for all of v4 stay ≤ 6 MB (`coreBytes` ≤ 11.4 MB; today 9.26 MB).
- Per file: palm LOD0 ≤ 2 500 / LOD1 ≤ 500; broadleaf and acacia LOD0 ≤ 3 500 / LOD1 ≤ 600; bush LOD0
  ≤ 600 / LOD1 ≤ 150; boulder ≤ 600 / 150; rock_small ≤ 100; backdrop ring ≤ 12 000.
  Distant trees must use LOD1; LOD0 only close to the camera.

Decisions for M4 (binding):
1. **Date palms** (`palms.py`): four variants, curved trunk with the leaf-scar diamond pattern, trunk
   material `ph_bark` = `palm_bark` added as layer 8 of the building texture array (`ph_dark` stays 7),
   fronds on today's foliage atlas material (`foliage_frond`), date bunches vertex-coloured. Same
   heights, origins and placement as today, so no collider change.
2. **Broadleaf trees** (`trees.py`): `sycamore_a/b` from `island_tree_02` and `tree_small_02`, `acacia`
   (flat umbrella crown) built from the same leaf cards; recoloured a warm healthy green, full crowns,
   ONE material per file with a single baked leaf+bark atlas (≤ 512 px WebP embedded, alpha MASK 0.5).
3. **Shrubs** `bush_a/b` come from `shrub_02`/`shrub_04` (same one-atlas rule). Grass and crops stay the
   cheap v3 cards (tinted to match); `ph_grass_medium_01` and `ph_flower_gazania` are hero accents only
   (≤ 60 instances each, near water, the oasis and house gardens; none on Lite if budget is tight).
4. **Rocks**: `boulder` (from `namaqualand_boulder_02`) and `rock_small` (from `rock_07`) replace the
   procedural `lump` rocks: big ones on river banks, hill feet and around the ruins, small ones scattered.
5. **Horizon** (`horizon.py`): rebuild `backdrop_hills.glb` from `namaqualand_cliff_01` rock masses
   arranged in 3 rings, same contract as today (one mesh, vertex colour baked from the cliff albedo and
   graded to the golden palette, `uv.x` = layer 0/0.5/1, `uv.y` = normalised height, same Nile openings,
   same radii). Keep the 3 haze layers; no hard silhouettes or gaps at the horizon.
6. **Textured prop path**: `envAssets.js` keeps UVs and maps for textured models (`ph_*.glb`, the new
   one-atlas trees/shrubs/rocks) and builds materials in `propMaterial.js` (Lite/Low: toon with map;
   Medium+: standard with the GLB's maps), with aerial fog, wind on foliage and the warm rim. High/Ultra
   load `ph_*_hi.glb` for props only (never trees or bushes in bulk). Merge dressing props per chunk ×
   material on every tier to keep draw calls down.
7. **Story-spot dressing** in new `storySets.js`: a table keyed by encounter id (positions read from
   encounters.json at runtime) placing `ph_` props (brass pot, lantern, ceramic pot, bench, stool,
   basket, fire pit) and a few rocks/shrubs so each of the 22 story spots looks inhabited and fitting
   (e.g. fire pit for `ibrahim-and-the-fire`, pots by the well). Every prop ≥ 2.0 m from every
   storyteller position, off the roads (`pathDist` > 1.6) and out of the approach from the road. Only
   large props (bench, fire pit, boulder) get colliders. No figures of people or animals.
8. **Walkability.** Colliders change here, so bump `SET_VERSION` to 4. `__game.balance({verify:true})`
   must be fully green (every story `reached: true`, `coins >= 20`, `notWalkable: 0`, `unreachable: 0`)
   on **lite, medium and high**. Two failures predate v4 and must now be fixed: High `best-dates`
   `unreachable: 1`, Medium `qays-the-fasting-farmer` `notWalkable: 1` (tree colliders differ per tier).
   Fix the cause (a clearing or placement rule), not the check.
9. **Quality bar.** Compare with `M3_*.png`: lusher, more natural vegetation, rocks with real texture, a
   cliff horizon, dressed story spots; nothing floating, no black or see-through leaf cards, no popping at
   close range. Lite must look clearly better, not emptier.
10. **Proof.** `M4_{lite,medium,high}_{home,street,river,oasis}.png`, plus `M4_models_sheet.png` (new
    models with tri counts) and ruins and `ibrahim-and-the-fire` shots; report per tier calls, main-pass
    triangles and the balance result. Do not commit, do not push, do not edit this doc.

#### M4 log (2026-11-26) — passed after one fix round
- Executor: Gemini 4 Neon XHigh (build + 1 fix round). Reviewer: Claude, no hand edits.
- Palms with Poly Haven bark, broadleaf/acacia trees and bushes from PH foliage, PH rocks, new sandstone
  horizon ring, `storySets.js` dressing for the 22 story spots, `SET_VERSION` 4.
- Fix round 1: High 329 draw calls (now 276), broken shard-like horizon (now continuous ridge rings), palm
  trunks had lost the leaf-scar pattern, Lite river bank emptier.
- Accepted deviations: horizon is a displaced heightfield ridge coloured from `namaqualand_cliff_01`
  (not the decimated cliff meshes); no hero grass/flowers on Lite; date bunches vertex-coloured.
  Remaining nit: fewer reed clumps in the Lite river foreground than M3.
- Checks (max over home, street, river, oasis, ruins, ibrahim; calls = whole frame, tris = main pass):
  Lite 87 calls / 167k; Medium 170 / 340k; High 276 / 574k. `balance({verify:true})` green on Lite,
  Medium and High (22 stories, min 22) — both pre-v4 failures are fixed. Precache core 10.01 MB.

### M4b run decisions (done)
Added after M4 at the owner's request (2026-11-26, relayed from the owner's planning session; owner's words:
«الميه عايزها حقيقيه اتصرف» — "I want the water real, handle it"). Today's water is stylised toon water:
flat cyan with cartoon wave lines. Make it read as real water at a glance. Do M4b only, then stop and
report. M0–M4 are committed.

Files you may create or change (nothing else): `src/game/shaders/waterMaterial.js` (river/canal/oasis
material and `toonStreamWaterMaterial`), `src/game/water/Water.jsx`, `src/game/water/waterBank.js` (only
if needed), `src/game/world/loaders.js` (the water normal loader), `src/game/lighting/environmentMap.js`
and `src/game/environment/Environment.jsx` (only to publish the sun colour next to `SKY_REFL`), new
`tools/polyhaven/process_water.py`, new `public/textures/v4/{512,1024}/water_nor.webp`, and
`blender/v4/previews/M4b_*.png`.

Decisions for M4b (binding):
1. **Normal map.** Poly Haven has no water set, so `process_water.py`
   (`blender -b --factory-startup --python tools/polyhaven/process_water.py`, fixed seed) generates one
   seamlessly tileable water normal map (OpenGL convention) from a band-limited FFT wave spectrum:
   natural multi-scale ripples, no visible grid, directional streaks or repetition. 512 (Lite/Low,
   precached, ≤ 200 KB) and 1024 (Medium+). The existing vite-pwa SKIP rule already excludes `1024/`.
2. **Waves.** Remove the procedural toon ripples. Medium+: two scrolling layers of the normal map at
   different scales and angles along the bank-texture flow direction, plus a slower large swell layer.
   Lite/Low: ONE normal fetch (scrolling along the flow). Oasis nearly calm, Nile broad and slow, canals
   in between. Fade normal strength with distance (no shimmer, no visible tiling).
3. **Colour by depth** (`bank.g`, metres = value × 2.2): Beer–Lambert absorption; shallows are clear and
   show the real riverbed (the M2 pebble/mud ground under the water), grading to a deep Nile green-teal.
   Canals muddy olive-green, oasis clear deep green-teal. No flat cyan anywhere, no toon bands, no
   cartoon wave lines, ribbons or lacy foam.
4. **Transparency and edges.** The water material becomes transparent (keep depth test; choose depth
   write so the world still sorts correctly): alpha from depth and Fresnel, fading to 0 at the shore, a
   thin broken foam/wet line only where depth is under about 6 cm, and M2's wet-bank darkening kept.
5. **Reflection.** Schlick Fresnel (F0 ≈ 0.02) against the M1 sky (`SKY_REFL` equirect, analytic
   fallback), reflected vector from the perturbed normal. High: half-res planar reflection and Ultra:
   full-res, both distorted by the normals (as today's passes; no new pass). A sharp golden sun specular
   path (GGX or tight Blinn–Phong) using the world sun direction and `sun.json` sun colour, sparkling
   along the path on the Nile without blowing out the screen.
6. **Street rill and canals:** the same look scaled down — shallow, clear, pebbles visible under it, quick
   small ripples, same reflection and sun glint.
7. **Performance and safety.** No extra draw calls or render passes on any tier; Lite fragment cost stays
   small (1 normal + 1 sky + 1 bank fetch). Budgets of §1 still hold with M4's measurement (Lite ≤ 140
   calls / 180k main tris, Medium ≤ 220 / 350k, High ≤ 320 / 700k). No shader errors on lite, medium,
   high, ultra and after a live tier switch. Water geometry, topology, colliders and walkability are
   unchanged; do not bump `SET_VERSION`; `balance({verify:true})` stays green.
8. **Proof.** `M4b_{lite,high}_{street,river,oasis}.png` (same spots as M4) plus `M4b_high_nile.png` and
   `M4b_lite_nile.png`, a close-up of the Nile beside the bridge (player at x 6.5, z 66, facing −0.35).
   Look at them yourself and iterate until the water reads as real water at a glance, compared with the
   `M4_*` shots. Do not commit, do not push, do not edit this doc.

### M4b review (Claude, 2026-11-27)
The orchestrating run dropped at 23:29 (no internet) after Neon finished M4b; reviewed here. Build passes;
lite/high: no page errors, no 404s, balance 22/22 stories (min coins 22, 0 bad). Main pass: Lite ≤ 87 calls /
166k tris, High ≤ 140 calls / 574k tris. The original Nile proof was blocked by an NPC; replaced by shots from
the bridge deck (0, 70, facing +x). Accepted: water reads as real (Fresnel sky + planar reflections on High,
depth colour, soft shores, clear rill over pebbles).

### M5 run decisions (done)
Do M5 (§3) and nothing from M6 onward, then stop and report. M0–M4b are committed; build on them.
The owner judges this milestone most after the houses: the seven villagers must look clearly better and belong in
the new naturalistic world, while staying warm, cute storybook children's-film characters (never realistic humans).

Files you may create or change (nothing else):
- `blender/v4/characters/` — start as a copy of `blender/v3/characters/*.py` (same module split: build_all, lib,
  rig, head, body, garments, anim, cast, preview) and change it there. Do not edit `blender/v3/`. Do not save
  `.blend` files. Run: `blender -b --factory-startup --python blender/v4/characters/build_all.py -- <keys…>`.
- `blender/v4/DESIGN_NOTES_characters.md` (your design notes per character).
- `public/models/{player,farmer,grandma_zainab,grandma,trader,sheikh,aunt}.glb` (overwrite).
- `src/game/shaders/characterMaterial.js` (new: the only character material factory),
  `src/game/characters/glbRig.js`, `src/game/world/loaders.js` (only to reuse `loadTextureArray`).
- `blender/v4/previews/M5_*.png`.

Decisions for M5 (binding):
1. **Contract with the game stays.** Same 22-bone skeleton and bone names (incl. `head`, `lid_l/r`, `mouth`),
   same clip names per character (player idle/walk/run/talk; grandma_zainab sit/sit_talk/idle; others
   idle/walk/talk), same heights, same seated geometry for Zainab on the 0.45 m mastaba, same export axes and
   origin. `glbRig.js` must still find clips and the head bone exactly as today.
2. **No ink outlines.** Do not export `outline` hulls. Keep `glbRig.js` able to ignore an `outline` material if
   one ever appears, but the new files have none.
3. **Materials.** Name each material by layer: `ph_cotton` (cotton_jersey), `ph_linen` (rough_linen),
   `ph_wool` (knitted_fleece), `ph_hessian` (hessian_230), `ph_leather` (brown_leather), `skin`, `hair`
   (plain, vertex colour), `face_<key>` (the 512 face/eye atlas, kept as an embedded texture), `eye`,
   `metal` (glasses, agal gold, buckles). Garment UVs in real metres (the shader divides by a tile size:
   cotton 0.35 m, linen 0.45 m, wool 0.3 m, hessian 0.4 m, leather 0.5 m) so weave reads at the right
   scale. Garment colour = vertex colour (linear `COLOR_0`) × texture detail, using the v3 palette per
   character as the start; fabric textures never replace the character colours.
4. **`characterMaterial.js`.** One `MeshStandardMaterial`-based factory (Lite/Low use `MeshLambertMaterial`
   with the same maps if cheaper) shared by all characters: fabric layers from a `DataArrayTexture`
   (512 on Lite/Low, 1024 on Medium+; diffuse + normal on Medium+, diffuse only on Lite), per-vertex
   `aLayer` like `buildingMaterial.js`; detail = `tex / layerAverage` mixed at 0.55 so colours stay. Skin:
   soft wrap diffuse (no hard cel band) with a warm subsurface tint in the shadow side and the existing
   rim light; roughness 0.55. Hair 0.6, fabrics 0.8–0.9, leather 0.5, metal 0.3/metalness 1. Uses
   `scene.environment` like the other v4 materials (low `envMapIntensity`). Until textures arrive show the
   vertex colours (no grey/black flash).
5. **Draw calls.** Merge each character's skinned parts into at most 3 skinned draws (skin+face, garments,
   hair/eyes/metal). Budgets: each character ≤ 9 000 tris, GLB ≤ 280 KB (Draco 6). Lite main pass
   ≤ 140 calls, High ≤ 320, as before.
6. **Look.** Keep the cast, roles and outfits of `blender/v3/DESIGN_NOTES.md` (who wears what) and improve
   them: softer real shading on round faces, bigger warm eyes with real catchlights, gentle blush, hair
   with soft strand clumps, garments with real folds at elbows/waist/hem that read under a low sun, fabric
   weave visible up close. Modesty rules from docs/001 stay: women in hijab/tarha with covered hair and
   neck, loose full-length dresses; men in galabiya/thobe/kaftan. Never depict prophets or companions.
7. **Proof.** `blender/v4/previews/M5_lineup.png` (all seven, 2600×1000), `M5_<key>_turn.png` (front, 3/4,
   side, back) and `M5_<key>_face.png` for each key, and in-game `M5_{lite,high}_{home,street,river,oasis}.png`.
   Look at the renders and in-game shots yourself and iterate until every character clearly looks better
   than `blender/v3/previews/lineup.png` and sits naturally in the v4 world (no clipping, no black faces, no
   stretched textures, Zainab seated on the mastaba). Do not commit, do not push, do not edit this doc.

### M5 review (Claude, 2026-11-27)
Two Neon passes (draft + fix round 1: shemagh checks, colour space/saturation, slimmer hijabs, stronger weave,
softer faces). Checks: build ok; lite/high no errors or 404s; balance 22/22 (min coins 22); main pass Lite ≤ 89
calls / 170k tris, High ≤ 141 / 559k. Accepted: outlines gone, soft shading, real fabric weave, v3 palette kept.
Known follow-up: hijab/tarha drape is still a stiff pointed cape (no worse than v3); give it real folds later.
