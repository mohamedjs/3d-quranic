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
  water/       <Water/> toon water (bands, bank foam, flowing streaks)
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
  models/                anime cast GLBs + models/env/ toon environment (built in blender/v2)
  illustrations/         painted story scenes (WebP ≤150 KB, blender/illustrations)
  ui/                    icon sprite, ornaments, world map
```

## Controls

| | |
|---|---|
| Walk | WASD / arrows, or tap/click the ground |
| Look | drag (mouse or one finger) |
| Zoom / fly up | mouse wheel · trackpad pinch · two-finger pinch · `+` / `−` · `PageDown` / `PageUp` · `Z` (in) / `Q` (out) · the ＋/－ HUD buttons (hold to keep zooming) |
| Talk · Map · Journal | `E` · `M` · `J` |

The camera eases from a close follow (2.6 m, default 5.2 m) out to a bird's-eye view (60 m);
on the way out the pitch leans to ~68° so it looks down over the village. The zoom is saved
(`settings.zoom`); dialogue and Quran shots use their own framing and hand the player's zoom
back afterwards. The world map (`M`) zooms with the wheel / pinch / buttons, pans by dragging,
double-click zooms in, and ◎ centres on the child.

## Quality levels

Settings → Graphics quality: Auto / Low / Medium / High / Ultra.
Auto starts at Low or Medium from a device guess (GPU string, `deviceMemory`,
`hardwareConcurrency`, phone/tablet UA; High only for clearly strong desktop GPUs). While
exploring, drei's `PerformanceMonitor` first trims the resolution (down to 70 %), then steps the
level down (or back up). Phones cap the pixel ratio at 1.5. Menus redraw at ~12 fps, hidden tabs not at all.

| | Low | Medium | High | Ultra |
|---|---|---|---|---|
| Resolution scale | 0.8 | 1 | 1.25 | 1.75 |
| Shadow map · redrawn every | 1K · 3rd frame | 2K · 2nd frame | 2K · frame | 4K · frame |
| Grass clumps | 12k | 34k | 65k | 100k |
| Terrain grid | 256² | 320² | 360² | 360² |
| Cast drawn within | 60 m | 90 m | 140 m | 200 m |
| Post-processing | off (not even downloaded) | bloom, DoF, SMAA… | ✓ | ✓ |
| Water | toon water (bands, foam, streaks) — one pass on every level | | | |

The shadow map is also redrawn whenever the child moves, so their own shadow never lags.
Grass, flowers, crops, reeds and bushes are chunked (24 m) and thinned toward their draw
distance (instances are shuffled, so drawing the first N is an even thinning). Draw distances
are measured from what the camera frames and stretch (thinner) as it zooms out; the shadow box
grows with the zoom. Voice (Piper / onnxruntime) and post-processing are lazy chunks; three and
React are separate cached chunks. All GLBs go through one loader with one local Draco decoder.

## Assets

Art style: anime / toon (see `blender/v2/STYLE.md`, `docs/art-direction.md`). All models are
built procedurally in Blender — `blender/v2/env/build_all.py` (houses, crops, water, props) and
`blender/v2/characters/build_all.py` (cast); the preview village is `blender/v2/village_v2.blend`.
No texture packs or HDRIs are shipped; colours come from `src/game/shaders/toonPalette.js`.
Old v1 scripts are kept for reference in `blender/legacy_v1/`.

Quran text, translation, tafsir and recitation: fetched live from Quran.com API v4.
Nothing Quranic is stored in this repository.

### Characters (anime cast, Blender v2)

`blender/v2/characters/` rebuilds all five cast GLBs from scratch (MPFB body + `game_engine`
skeleton, anime head with a painted face texture, sculpted-clump hair/beards, simple smooth
garments, inverted-hull outlines, keyframed clips):

    python3 blender/v2/bg.py blender/v2/characters/build_all.py cast     # poll blender/v2/_jobs/cast.log for BG_DONE

| file | who | clips |
|---|---|---|
| `player.glb` | the village boy, 1.25 m | idle, walk, run, talk |
| `farmer.glb` | Grandpa Salim, 1.74 m | idle, walk, talk |
| `grandma_zainab.glb` | Grandma Zainab, seated on the 0.45 m mastaba | sit, sit_talk |
| `grandma.glb` | Grandma Amina, 1.60 m | idle, walk, talk |
| `trader.glb` | Uncle Hamdan, 1.78 m | idle, walk, talk |

Scripts: `toon_lib.py` (materials, outlines, render helpers), `body.py` (MPFB), `head.py`
(anime head + face painter + blink lids/mouth), `garments.py`, `anim.py`, `cast.py` (per-character
config), `preview.py` (turnarounds, `cast_lineup.png`, `cast_faces.png` in `blender/v2/previews/`).
Each GLB = one skinned mesh `<key>` (materials `toon_*`) + `<key>_outline` (material `outline`,
flipped normals — render BackSide/unlit). Extra bones `lid_l`, `lid_r`, `mouth` (children of `head`)
are scale-keyed in every clip: blinks and a talking mouth.
