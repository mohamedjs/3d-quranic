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

### CURRENT RUN: milestone M1 only (Sky & light)
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
