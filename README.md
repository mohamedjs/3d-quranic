# Quran Journey — رحلة القرآن

A 3D exploration game for children: walk a golden-hour farming valley, meet villagers,
hear a Quran story, then listen to the verses in an authentic recitation.

## Run

```bash
npm install
npm run dev          # http://localhost:5173
npm run build        # → dist/, served by Apache at http://localhost/old/3d-quranic/dist/
```

Opening `index.html` straight from disk (`file://`) will not work; it must be served.
The original single-file version still runs at `classic/`.

## Stack

React 19 · React Three Fiber 9 · drei · @react-three/postprocessing · three r186 · Vite.

**Renderer: WebGL 2.** The brief asked for GLSL water shaders, `onBeforeCompile`
material extensions and pmndrs post-processing — none of which run on three's
WebGPURenderer (it needs every shader rewritten in TSL and a different post stack).
Porting is possible later; today WebGL 2 is the path that supports all requested effects
in every browser.

## Layout

```
src/game/
  components/  Game.jsx (Canvas, adaptive quality)
  world/       World.jsx (scene graph), details.js (hand-placed canal scene)
  terrain/     heightfield.js (analytic land: height, paths, fields, water), geometry, <Terrain/>
  water/       <Water/> + refraction/depth and planar-reflection passes
  vegetation/  plants.js (procedural geometry), <Vegetation/> (instanced scatter)
  buildings/   village.js, triplanar PBR materials, <Built/>
  characters/  procedural rigs, GLB loader, PlayerController
  camera/      CameraRig (spring follow, occlusion, cinematic shots)
  lighting/    HDR sky + sun-matched directional light
  environment/ dust, pollen, gnats, birds, sun disc for god rays
  effects/     post-processing
  shaders/     terrain splat, water, wind, triplanar
  systems/     game flow, QuranService, recitation, story runner, audio, quality, store
  ui/          HUD / dialogue / Quran overlay (DOM), illustrations
public/
  data/encounters.json   stories — edit here to add encounters, no code changes
  textures/  hdri/       Poly Haven CC0 assets (1K)
  models/                optional GLB characters (see README there)
```

## Quality levels

Settings → Graphics quality: Auto / Low / Medium / High / Ultra.
Auto starts from a GPU guess and steps down/up from measured frame rate while exploring.

| | Low | Medium | High | Ultra |
|---|---|---|---|---|
| Resolution scale | 0.8 | 1 | 1.25 | 1.75 |
| Shadow map | 1K | 2K | 2K | 4K |
| Grass clumps | 14k | 30k | 55k | 90k |
| Water | sky reflection | + refraction, depth colour, foam | + planar reflection | full-res passes |
| AO / bloom / god rays / DoF | – | ✓ / ✓ / – / ✓ | ✓ all | ✓ all |

## Assets

Textures and HDRI: [Poly Haven](https://polyhaven.com), CC0 — aerial_grass_rock,
dry_ground_01, farm_soil, brown_mud_02, aerial_rocks_02, aerial_sand, clay_plaster,
old_planks_02, large_sandstone_blocks, palm_bark, bark_brown_02, cotton_jersey,
qwantani_late_afternoon_puresky. Shipped as 1K JPG with GPU mipmaps; no KTX2 yet
(`toktx` isn't installed here — convert with `gltf-transform`/`toktx` to cut VRAM further).

Quran text, translation, tafsir and recitation: fetched live from Quran.com API v4.
Nothing Quranic is stored in this repository.
