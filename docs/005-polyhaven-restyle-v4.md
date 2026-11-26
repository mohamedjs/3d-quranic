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
