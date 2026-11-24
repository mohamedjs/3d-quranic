# 004 — Environment v3: painterly-naturalistic Nile village, Lite → Ultra
Status: Ready (milestone by milestone)     Builds on: docs/001, docs/002, docs/003, docs/art-direction.md

Author of the art direction: Gemini 4 Neon XHigh (the owner asked that Gemini designs the world).
Reviewer: Claude Opus 5.5. Sections 1–6 below are Gemini's proposal, accepted with the decisions in §R,
which override anything in 1–6 they contradict.

## CURRENT RUN: milestone M1 only (Sky, Light, Horizon & Terrain — see §5). Stop after M1 and report.
The coin/road/footbridge fixes of docs/002 are already in this branch (commit 1970cb4).

## R. Reviewer decisions (binding)
1. Direction accepted: painterly-naturalistic storybook world, cel-shaded characters keep ink
   outlines, environment ink hulls are dropped.
2. **Lite is what most children see** (the game auto-starts most phones on Lite). Every
   milestone must make Lite visibly better, not only High/Ultra. Lite budgets from §3 are hard
   limits; measure them with `renderer.info` in the game.
3. Do NOT redo what docs/002 already fixed (per-pixel roads via the baked path-distance texture,
   footbridge (-15,34.5) unified, oasis storytellers separated, chevrons vs coins). Build on that
   code; read it first.
4. Story-spot set dressing lives in the static world (`details.js` / `village.js`, or a new
   `src/game/world/storySets.js` keyed by encounter id that reads positions from
   encounters.json at runtime) — NOT in `encounters.json` (`props[]` stays as is). Props must stay
   ≥ 2.0 m clear of every storyteller position and leave the approach path walkable.
5. Locked: `HOME` [-9.4, 26], `MASTABA` (seat 0.45), all encounter positions (incl. the 4 new
   stories from docs/003: yunus-and-the-whale, sulayman-and-the-ant, companions-of-the-cave,
   luqman-wisdom), river/canal/oasis topology. Cosmetic bank work only.
6. If anything changes walkability (new colliders, bridges, props with collision), bump
   `SET_VERSION` in `src/game/world/coins.js` and re-run `__game.balance({verify:true})`:
   every story `reached: true`, `coins >= 20`, `notWalkable: 0`, `unreachable: 0`.
7. Zero new npm dependencies. High/Ultra texture folders (`public/textures/env/1024`, `/2048`)
   are excluded from the PWA precache (tools/vite-pwa.js) and lazy-loaded.
8. One milestone per run. Each run ends with: `npm run build` passing, the proof screenshots
   listed in §5 taken with headless Chromium + SwiftShader (see docs/002 §10) on `lite` and on
   `high` (force the level via the store / `?q=` if the game supports it; otherwise
   `__game.store.setState({quality:'high'})` and reload logic as the code requires), saved to
   `blender/v3/previews/env_M<n>_*.png`, and a short report of renderer.info per tier.
9. Characters v3 (docs/001) land in `public/models/*.glb` first; calibrate against them from M1.
10. Never depict people in the environment (no figures in murals beyond geometric/floral folk
    patterns; no faces). The Kaaba is not built in the 3D world.
11. Do not commit, do not push. Do not edit `docs/`.

---
### 1. What Is Weak Today

- **Cloned shoebox village & sterile surfaces** ([_ingame_now.png](file:///var/www/html/old/3d-quranic/blender/v2/previews/_ingame_now.png), [env_houses.png](file:///var/www/html/old/3d-quranic/blender/v2/previews/env_houses.png), [houses.py](file:///var/www/html/old/3d-quranic/blender/v2/env/houses.py)): Only 3 rectangular boxes (`house_a/b/c`) repeat symmetrically down the street with identical blue zigzags and pasted decal palms. [envAssets.js](file:///var/www/html/old/3d-quranic/src/game/world/envAssets.js#L81-L91) strips UVs and flattens materials into single-hex vertex colors—zero plaster wear, brick relief, wood grain, or corner AO—so houses read as cardboard ([village_home.png](file:///var/www/html/old/3d-quranic/blender/v2/previews/village_home.png)).
- **Blobby, toy-like vegetation** ([env_trees.png](file:///var/www/html/old/3d-quranic/blender/v2/previews/env_trees.png), [palms.py](file:///var/www/html/old/3d-quranic/blender/v2/env/palms.py)): `sycamore` is 8 lumpy icospheres on a 4-branch fork; `bougainvillea` is pink spheres on green spheres; palms use stiff 7-segment zigzag ribbons with uniform ring trunks. Grass in `_ingame_now.png` is sparse flat spikes on bare mud.
- **Jaggy terrain, raw horizon, opaque water** ([village_wide.png](file:///var/www/html/old/3d-quranic/blender/v2/previews/village_wide.png), [village_canal.png](file:///var/www/html/old/3d-quranic/blender/v2/previews/village_canal.png), [terrainMaterial.js](file:///var/www/html/old/3d-quranic/src/game/shaders/terrainMaterial.js), [waterMaterial.js](file:///var/www/html/old/3d-quranic/src/game/shaders/waterMaterial.js)): Vertex-interpolated `toonMask` causes jagged sawtooth roads on Lite's `224²` mesh (`_ingame_now.png`) and stair-stepped canal/river banks (`village_wide.png`). The valley ends in a flat tabletop horizon. Water is an opaque cyan band—no Fresnel sky reflection, sun specular path, wave normals, depth absorption, or wet bank transition; the street stream (`x=-3.3`) barely reads as water.
- **Flat lighting, thin sky, costly atmosphere** ([Lighting.jsx](file:///var/www/html/old/3d-quranic/src/game/lighting/Lighting.jsx), [Sky.js](file:///var/www/html/old/3d-quranic/src/game/environment/Sky.js), [Atmosphere.jsx](file:///var/www/html/old/3d-quranic/src/game/environment/Atmosphere.jsx), [Effects.jsx](file:///var/www/html/old/3d-quranic/src/game/effects/Effects.jsx)): Harsh 3-step ramp ([toon.js](file:///var/www/html/old/3d-quranic/src/game/shaders/toon.js#L14)) + `Math.PI` flat hemisphere + `scene.environment = null` washes shadows chalky with no contact grounding. `Sky.js` has faint single-layer clouds and no god rays. Birds cost 3 draw calls *each* (~84 draws).
- **Primitive landmarks & bare story spots** ([village.js](file:///var/www/html/old/3d-quranic/src/game/buildings/village.js#L126-L166), [encounters.json](file:///var/www/html/old/3d-quranic/public/data/encounters.json)): The Nile bridge, oasis arish, and ruins are raw Three.js boxes/cylinders/torus; 13 of 18 encounters have `props=[]`, leaving storytellers standing in empty grass.

---

### 2. Art Direction — Painterly-Naturalistic Storybook

- **Reconciling "feels real" with cel-shaded characters:** Follow the **Studio Ghibli / *Ni no Kuni* / *Breath of the Wild*** contract: cel-shaded characters stay crisp and readable while the world around them is richly painted, tactile, and atmospherically believable. Broad brush-stroked baked textures (never noisy photo-scans), warm/cool bounced light, glittering reflective water, and sunlit translucent foliage ground the cast seamlessly.
- **Drop environment ink hulls:** Removing inverted-hull outlines from buildings/trees/crops eliminates messy dark lines (`village_wide.png`), cuts 35–45% of env tris, and lets architecture read through silhouette, baked crease AO, rim light, and aerial perspective—while characters keep their v3 outlines and pop heroically.
- **Palette & Golden-Hour Light:** Sun lowered to ~16° elevation, honey-gold key (`#FFC978`) casting long dramatic alley shadows; warm ochre ground bounce (`#C48952`) vs cool lavender-indigo sky shadow fill (`#6E7FA3`) matching characters' shadow tint. Warm lantern glows (`#FFBE64`) begin waking up in shaded alleys and story spots.
- **Sky & Encircling Horizon:** Rayleigh/Mie-inspired gradient (apricot horizon `#F7B96B` → cream `#F7D9A8` → cerulean zenith `#4D7EA8`, dusty rose opposite sun), glowing sun halo, two sculpted painterly cumulus layers + high cirrus wisps. A distant **limestone escarpment & palm ridge ring** (`backdrop_hills.glb`) encircles the 520 m valley in 3 aerial-perspective haze layers—ending the tabletop horizon.
- **Water (4 Distinct Personalities):** Slow emerald-teal Nile with golden sun-path glints; shaded irrigation canals with mossy stone quays and wet-mud darkening; sparkling shallow street rill over pebbles; calm mirror-like oasis pond reflecting palms and sky.
- **Vegetation:**
  - *Date palms (4 hero types):* Curved feathery alpha-cutout frond cards (richer silhouette at *fewer* tris than v2 ribbons), fibrous diamond-bark trunks, amber/ruby date bunches, dry skirt fronds.
  - *Sycamores (`جميز`) & Desert Acacias:* Gnarled buttressed limbs + layered painterly leaf-cluster cards with **transferred spherical normals** (Ghibli softness) and backlit subsurface glow.
  - *Bougainvillea & Crops:* Wall-draping vine cards replacing pink balls; denser wheat/maize/berseem/cotton rows; papyrus, cattails, oasis lotus pads, and root-blended grass tufts.
- **Egyptian Nile Architecture (6 Archetypes + Landmarks):** Chamfered, hand-plastered mudbrick silhouettes with real recessed doorways, lintels, mashrabiya grilles, mud parapets, rooftop pergolas, and baked folk murals (not floating decals):
  1. `house_grandma` (canal hero: blue arched door, reed-shaded mastaba, bougainvillea vine, Hajj mural);
  2. `house_courtyard` (L-shaped + low front yard + *furn baladi* bread oven);
  3. `house_dovecote` (exterior stair + conical *burj hamam* pigeon tower);
  4. `house_domed` (Hassan Fathy-inspired dome + vaulted iwan porch);
  5. `house_trader` (corner shop + cantilevered fabric awning);
  6. `house_cottage` (humble oasis/field-edge home).
  Plus a modest mudbrick **village mosque/kuttab landmark** anchoring the skyline, overhead **street cloth canopies** breaking the lane tunnel, arched timber-stone **Nile bridge**, turning **saqiya waterwheel**, and moored **felucca**.
- **Set Dressing Per Story Area:**
  - *Village Street & Square:* Varied house facades, hanging cloth shades, glowing lanterns (`the-guest-and-the-lamp`, `ali-and-the-trusts`), spice/produce market stalls (`umar-and-the-widow`), stone-paved well square + water trough (`uthman-and-the-well`), decorated doorway courtyard (`houses-by-their-doors`).
  - *Fields & Nile:* Timber boat-building planks & moored felucca (`nuh-and-the-ark`), lush papyrus marsh cove & stepping stones (`musa-on-the-river`), turning saqiya & harvest pergola (`qays-the-fasting-farmer`).
  - *Palm Oasis:* Sculpted palm-frond *arish* pavilion with rugs/lanterns, lotus reflection spring (`yusuf-dream`, `isa-in-the-cradle`), date-harvest crates & ladders (`best-dates`).
  - *Eastern Desert Edge:* Striped Bedouin tent, carpet/spice bales & camel trough (`quraysh-journeys`); acacia-shaded stone hearth with glowing embers (`ibrahim-and-the-fire`).
  - *Ancient Ruins:* Sculpted weathered limestone colonnade & prayer-niche arch (`the-new-qibla`); rocky hillside cave-mouth overhang (`abu-bakr-the-cave`).
  - *Northern Mountain Overlook:* Terraced stone path, gnarled olive/acacia tree & stone parapet overlooking the entire valley (`muhammad-the-trustworthy`).

---

### 3. Five-Tier Scalability Plan

| Feature | Lite (Old phones, 30fps) | Low (Mid mobile / iGPU) | Medium (Modern phone / laptop) | High (Desktop / M-series) | Ultra (RTX / RX / M-Pro) |
|---|---|---|---|---|---|
| **Models & LOD** | Merged 24m chunks (LOD0<16m, LOD1<38m, big<110m) | Instanced (LOD0<35m → LOD1) | Instanced (LOD0<55m), full story props | Instanced (LOD0<85m), micro-clutter | Instanced (LOD0<130m), animated saqiya/cloth/boat |
| **Textures (WebP)** | 512px Albedo+AO atlas (core) | 512px Albedo+AO | 1024px Albedo+ORM+Normal (lazy) | 2048px PBR + terrain detail (lazy) | 2048px PBR, 8× aniso, 2K bank map |
| **Shading** | Painterly 3-band toon + baked AO | Soft painterly toon + wind | **Stylized PBR** + PMREM IBL + foliage SSS | Full Stylized PBR + aerial fog + 2 pooled lantern lights | Same + 3 pooled warm lights + crisp contact |
| **Shadows** | 2K static baked (re-baked ~40m) + blobs | 1K PCF · 3rd frame (32m) | 2K PCFSoft · 2nd frame (45m) | 2K every frame (55m) | **4K** every frame (75m) |
| **Water** | Depth bands + bank foam + Fresnel sheen | Animated foam + sun glints | Dual normal ripples + sky refl + shore wetness | Half-res planar refl (Nile/Oasis) + caustics | Full-res planar refl + refraction + caustics |
| **Sky & Atmos** | 2-oct clouds + horizon ring; haze 35–140m | 3-oct + 1-draw birds + sparse motes | 4-oct layered clouds + Mie glow + motes/embers | + Sun disc God Rays + directional aerial haze | Full aerial haze + dense pollen/embers/birds |
| **Post-FX** | Off (not downloaded); Neutral TM | Off | Bloom, DoF, Vignette, SMAA, Neutral | + GodRays + half-res SSAO | + GodRays + full-res SSAO |
| **Veg Density** | 3k grass (<22m), 45% trees, crops <26m | 14k (<45m), 60%, crops <42m | 36k (<68m), 85%, crops <60m | 70k (<95m), 100%, crops <75m | 110k (<125m), 100%+understory, crops <100m |
| **Budgets** | **≤70 draws · ≤150k tris · 1.8 MB** | **≤110 · ≤380k · 2.2 MB** | **≤150 · ≤750k · 4.0 MB** | **≤210 · ≤1.3M · 6.5 MB** | **≤260 · ≤2.2M · 7.5 MB** |

*(High/Ultra 1024–2048px atlases are lazy-loaded on demand and excluded from core PWA precache so Lite phones never download them.)*

---

### 4. Technical Plan

**Blender v3 Pipeline (`blender/v3/env/` → `public/models/env/` & `public/textures/env/{512,1024,2048}/`):**
- `lib.py` — headless reset, UV packing, vertex-AO baker, spherical normal transfer for leaf cards, LOD1 builder, Draco-6 GLB export & budget report.
- `textures.py` — procedural node-based bakes to shared WebP atlases: `arch_{albedo,orm,normal}`, `foliage_{albedo,normal}`, `terrain_detail_{albedo,normal,rough}`.
- `houses.py` — 6 house archetypes (`house_grandma` preserving `house_a` door/mastaba coords, `house_courtyard`, `house_dovecote`, `house_domed`, `house_trader`, `house_cottage`), `mosque_landmark`, `street_arch_awning`, `garden_wall`, `mastaba`, `furn_oven`.
- `foliage.py` & `crops.py` — `palm_a/b/c/d`, `sycamore_a/b`, `acacia`, `bougainvillea_{bush,vine}`, `bush_a/b`, `lotus_pad`, `pot_plant`, 5 crops, `grass_a/b/c`, `reeds`, `papyrus`, `wildflowers`, `field_bund`.
- `water_props.py` — `river_bridge`, `footbridge`, `saqiya`, `shaduf`, `sluice`, `felucca`, `canal_bank`, `canal_stones`, `stream_channel`, `stepping_stones`.
- `landmarks.py` & `props.py` — `backdrop_hills`, `oasis_arish`, `ruins_{arch,wall,column,rubble}`, `cave_outcrop`, `caravan_tent`, `cargo_bales`, `desert_hearth`, `hill_overlook`, `well`, `stall_a/b`, `jar`, `jar_b`, `zir_stand`, `basket`, `crate_dates`, `hay`, `hoe`, `fence`, `clothesline`, `lantern_wall`, `boulder_a/b`.
- `build_all.py` & `preview.py` — builds all ~48 GLBs, bakes all 3 texture tiers, saves `village_v3.blend`, renders EEVEE contact sheets & hero vistas to `blender/v3/previews/`.

**Game Code Changes (`src/game/` & `tools/`):**
- [quality.js](file:///var/www/html/old/3d-quranic/src/game/systems/quality.js), [store.js](file:///var/www/html/old/3d-quranic/src/game/systems/store.js): Add `shading`, `texRes`, `waterMode`, `ssao`, `godRays`, `pointLights`, `lodDist`.
- [envAssets.js](file:///var/www/html/old/3d-quranic/src/game/world/envAssets.js), [instancing.js](file:///var/www/html/old/3d-quranic/src/game/world/instancing.js): Keep UVs + baked vertex AO; bind tier-appropriate atlas textures; preserve Lite chunk merging (shared atlas = still 2–3 draw calls/cell).
- `shaders/stylizedPbr.js` *(new)* & [toon.js](file:///var/www/html/old/3d-quranic/src/game/shaders/toon.js): Dual-path material factory—soft painterly-toon on Lite/Low; `MeshStandardMaterial` + warm shadow tint, aerial-perspective fog, and backlit foliage translucency on Med–Ultra.
- [heightfield.js](file:///var/www/html/old/3d-quranic/src/game/terrain/heightfield.js), [terrainGeometry.js](file:///var/www/html/old/3d-quranic/src/game/terrain/terrainGeometry.js), [terrainMaterial.js](file:///var/www/html/old/3d-quranic/src/game/shaders/terrainMaterial.js): Export `PATHS`/`ROAD_CANALS` for **per-pixel crisp roads & wet banks** (fixing Lite sawtooth roads); unify all `FOOTBRIDGES` (including `(-15, 34.5)`); add desert/loam biome blending & detail normals on Med–Ultra.
- [Water.jsx](file:///var/www/html/old/3d-quranic/src/game/water/Water.jsx), [waterBank.js](file:///var/www/html/old/3d-quranic/src/game/water/waterBank.js), [waterMaterial.js](file:///var/www/html/old/3d-quranic/src/game/shaders/waterMaterial.js): 5-tier water shader + optional planar reflection render target on High/Ultra + matching street-stream ribbon shader.
- [Sky.js](file:///var/www/html/old/3d-quranic/src/game/environment/Sky.js), [Environment.jsx](file:///var/www/html/old/3d-quranic/src/game/environment/Environment.jsx), [environmentMap.js](file:///var/www/html/old/3d-quranic/src/game/lighting/environmentMap.js), [Lighting.jsx](file:///var/www/html/old/3d-quranic/src/game/lighting/Lighting.jsx), [Atmosphere.jsx](file:///var/www/html/old/3d-quranic/src/game/environment/Atmosphere.jsx): Procedural sky-baked PMREM IBL (zero HDRI download), layered clouds + sun disc, 1-draw-call instanced birds, pooled dynamic lantern lights (High/Ultra).
- [village.js](file:///var/www/html/old/3d-quranic/src/game/buildings/village.js), [details.js](file:///var/www/html/old/3d-quranic/src/game/world/details.js), [Vegetation.jsx](file:///var/www/html/old/3d-quranic/src/game/vegetation/Vegetation.jsx), [World.jsx](file:///var/www/html/old/3d-quranic/src/game/world/World.jsx): Replace all raw Three.js landmarks with v3 GLBs, diversify street & regional set dressing, blend grass roots to terrain color.
- [Effects.jsx](file:///var/www/html/old/3d-quranic/src/game/effects/Effects.jsx), [vite-pwa.js](file:///var/www/html/old/3d-quranic/tools/vite-pwa.js): Tiered Bloom/GodRays/SSAO/DoF/SMAA using already-installed `@react-three/postprocessing`; exclude `1024/2048` texture folders from core PWA precache.

---

### 5. Shippable Milestones & Proof

1. **M1 — Sky, Light, Horizon & Terrain:** New sky + PMREM IBL, `backdrop_hills.glb`, per-pixel terrain paths/biomes, unified footbridges, aerial fog. *Proof:* In-game `lite` & `high` shots from spawn, lookout hill, and bird's-eye showing crisp paths and ringed horizon.
2. **M2 — Water & Crossings:** 5-tier water shader, planar reflection (High/Ultra), upgraded `canal_bank`, `stream_channel`, `river_bridge`, `footbridge`. *Proof:* In-game shots of street rill, Grandma's canal, Nile bridge, and Oasis pond across `lite` / `medium` / `ultra`.
3. **M3 — Painterly Atlases & Foliage:** Shared WebP atlases, rebuilt palms/sycamores/acacias/bougainvillea/crops/grass, foliage SSS, 1-draw-call birds. *Proof:* Blender `foliage_sheet.png` + in-game oasis & fields shots vs `env_trees.png` / `village_wide.png`.
4. **M4 — Architecture & Village Street:** 6 house archetypes, mosque landmark, street canopies, well, stalls, saqiya, felucca; stylized-PBR integration. *Proof:* Blender `houses_sheet.png` + in-game spawn street & Grandma's house A/B vs `_ingame_now.png` / `village_home.png`.
5. **M5 — Landmarks & All 18 Story Spots:** `oasis_arish`, `ruins_*`, `cave_outcrop`, `caravan_tent`, `desert_hearth`, `hill_overlook`, boat-yard; complete per-area set dressing. *Proof:* 7 regional in-game postcards + walkability/collider check across all encounters.
6. **M6 — High/Ultra Polish & 5-Tier Perf Sign-Off:** GodRays, SSAO, pooled lantern lights, animated saqiya/cloth/felucca, PWA rules, perf audit. *Proof:* 5-tier comparison strip (`lite`→`ultra`) + `renderer.info` table hitting all budgets.

---

### 6. Risks & Decisions Needed From You (Claude)

- **Style harmony with Characters v3:** Confirm the Painterly-Naturalistic Storybook direction and dropping env ink hulls. Share one v3 character GLB (e.g., `player.glb`) before M4 so we calibrate skin/cloth contrast and shadow tint side-by-side.
- **Story-spot prop ownership:** Should regional encounter set-dressing live in [details.js](file:///var/www/html/old/3d-quranic/src/game/world/details.js)/[village.js](file:///var/www/html/old/3d-quranic/src/game/buildings/village.js) (static world) or in [encounters.json](file:///var/www/html/old/3d-quranic/public/data/encounters.json) `props[]`? Confirm `HOME` (`[-9.4, 26]`) and `MASTABA` (`seat=0.45`) remain locked, and whether you'll separate the overlapping oasis encounters (`yusuf-dream` / `isa-in-the-cradle`, 3.55 m apart).
- **Zero new npm deps & PWA lazy textures:** Confirm using only already-installed `@react-three/postprocessing` (`GodRays`, `SSAO`) and skipping `public/textures/env/{1024,2048}/` from core PWA precache.
- **Heightfield & coin cache stability:** Confirm keeping river/canal/oasis topology intact (cosmetic bank smoothing + unified footbridges only) and bumping the `localStorage` coin-set cache version when new footbridges land.
