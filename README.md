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
| Walk | WASD / arrows (`Shift` runs), or tap/click the ground · touch: floating joystick in the left half |
| Look | drag (mouse) · touch: one-finger drag in the right half (a flick coasts) |
| Walk to the story | 👣 HUD button or `F`: walks along the golden path to the next storyteller |
| Zoom / fly up | mouse wheel · trackpad pinch · two-finger pinch · `+` / `−` · `PageDown` / `PageUp` · `Z` (in) / `Q` (out) · the ＋/－ HUD buttons (hold to keep zooming) |
| Talk · Map · Journal · Stories | `E` · `M` · `J` · `K` |

The camera eases from a close follow (2.6 m, default 5.2 m) out to a bird's-eye view (60 m);
on the way out the pitch leans to ~68° so it looks down over the village. The zoom is saved
(`settings.zoom`); dialogue and Quran shots use their own framing and hand the player's zoom
back afterwards. The world map (`M`) zooms with the wheel / pinch / buttons, pans by dragging,
double-click zooms in, and ◎ centres on the child.

**Phones and tablets.** Touch devices (`pointer: coarse` / `maxTouchPoints`; the first touch also
switches over) get a split screen: a finger landing in the **left half** spawns a translucent
teal-glass joystick under the thumb (gold ring + knob, 60 px travel, 12 % dead-zone, eased).
Up is away from the camera; a small push strolls, most of the travel walks, the outer ring runs.
It feeds the same movement path as the keys (collisions, slopes, coin pickups) and cancels any
tap-to-walk target. The **right half** orbits the camera with one finger (yaw + limited pitch,
with a little inertia); two fingers pinch-zoom anywhere; a short tap anywhere still walks to that
spot. Joystick and camera fingers work at the same time (tracked per `pointerId`). All buttons
sit on the physical right in both languages (dock bottom-right, then 👣 / ＋ / － above it, or in
one row on landscape phones; «تحدّث» next to them), clear of the joystick, inside the
safe-area insets. The page never scrolls, zooms or opens a long-press menu. A one-time hint
(«اسحب يسار لتمشي · اسحب يمين لتلفّ الكاميرا») explains it.

**Stories (`K`, the book-with-pin button in the dock).** A sheet lists every story in
`encounters.json` as a card: its first painted illustration (else a gold emblem), title in both
languages, the storytellers' portraits and names, the place, the verse reference and the distance,
with a ✓ done / ! open / 🔒 not-yet badge. Tapping a card (or a story marker on the world map)
makes it the target: trail, beacon, minimap/world-map route, objective chip and 👣 switch to it and
the narrator says where to go. Any story can be picked: a locked one is unlocked for good
(`save.unlocked`), a done one reopens for a replay (no double points, no new breadcrumb coins).
The pick is saved (`save.chosen`) until that story is finished; then the default order (nearest
open / newly unlocked story) takes over again. Without a pick nothing changes.

**Walk to the story (👣 / `F`).** Shown in explore mode while a guided route exists. The child
walks the guide's A* route (`systems/autowalk.js` aims ~2.5 m ahead on the polyline) at walking
pace, collecting the breadcrumb coins; the camera follows and slowly swings behind. It stops
~2 m short of the storyteller so the Talk prompt appears (the dialogue never starts by itself).
Tapping 👣 again, the joystick, a movement key or tap-to-walk cancels. Re-routes are followed
as they arrive; if progress stalls for 2 s it aims further along the route, and after a couple
of tries it stops with a gentle message.

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
