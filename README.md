# Quran Journey — رحلة مع القرآن

A 3D exploration game for children: walk a golden-hour farming valley, meet villagers,
hear a Quran story, then listen to the verses in an authentic recitation.

## Run

```bash
npm install
npm run dev          # http://localhost:5173
npm run build        # → dist/ (+ sw.js, offline PWA), served by Apache at http://localhost/old/3d-quranic/dist/
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
| Walk | WASD / arrows (`Shift` runs), or tap/click the ground · touch: the fixed joystick at the bottom-left |
| Look | drag (mouse) · touch: one-finger drag anywhere off the joystick (a flick coasts) |
| Walk to the story | 👣 HUD button or `F`: walks along the golden path to the next storyteller |
| Zoom / fly up | mouse wheel · trackpad pinch · two-finger pinch · `+` / `−` · `PageDown` / `PageUp` · `Z` (in) / `Q` (out) · the ＋/－ HUD buttons (hold to keep zooming) |
| Talk · Map · Journal · Stories | `E` · `M` · `J` · `K` |

The camera eases from a close follow (2.6 m, default 5.2 m) out to a bird's-eye view (60 m);
on the way out the pitch leans to ~68° so it looks down over the village. The zoom is saved
(`settings.zoom`); dialogue and Quran shots use their own framing and hand the player's zoom
back afterwards. The world map (`M`) zooms with the wheel / pinch / buttons, pans by dragging,
double-click zooms in, and ◎ centres on the child.

**Phones and tablets.** Touch devices (`pointer: coarse` / `maxTouchPoints`; the first touch also
switches over) always show a **fixed joystick** in the bottom-left corner (128 px teal-glass base
with a gold ring and knob, inside the safe area, dimmed to 60 % until touched; `ui/joystick.js`).
Only a touch that **starts on it** moves the child: the knob follows the finger (even off the base,
50 px travel, 12 % dead-zone, eased) until it lifts, and springs back. Up is away from the camera;
a small push strolls, most of the travel walks, the outer ring runs. It feeds the same movement
path as the keys (collisions, slopes, coin pickups) and cancels any tap-to-walk target / 👣.
**Any other one-finger drag, left or right half, orbits the camera** (yaw + limited pitch, a flick
coasts); two fingers pinch-zoom anywhere and never move the child — the finger left over from a
pinch doesn't swing the camera either. A short tap off the joystick still walks to that spot.
Joystick and camera fingers work at the same time (tracked per `pointerId`). Panels (world map,
stories, journal) sit above the canvas, so dragging the map pans only the map. All buttons sit on
the physical right in both languages (dock bottom-right, then 👣 / ＋ / － above it, or in one row on
landscape phones; «تحدّث» next to them), clear of the joystick (slimmer dock on ≤ 430 px phones),
inside the safe-area insets. The page never scrolls, zooms or opens a long-press menu. A one-time
hint («استخدم العصا تحت لتمشي · اسحب في أي مكان لتلفّ الكاميرا») explains it.

**Stories (`K`, the book-with-pin button in the dock).** A sheet lists every story in
`encounters.json` as a card: its first painted illustration (else a gold emblem), title in both
languages, the storytellers' portraits and names, the place, the verse reference and the distance,
with a ✓ done / ! open / 🔒 not-yet badge. Tapping a card (or a story marker on the world map)
makes it the target: trail, beacon, minimap/world-map route, objective chip and 👣 switch to it and
the narrator says where to go. Any story can be picked: one that isn't open yet becomes the target with its coins laid out
(it still opens only with its coin share — see below), a done one reopens for a replay (no double points).
The pick is saved (`save.chosen`) until that story is finished; then the default order (nearest
open / newly unlocked story) takes over again. Without a pick nothing changes.

**Difficulty and coin-gated stories.** «رحلة جديدة» first asks for a level — «سهل ٢٠٪ · متوسط ٥٠٪
· صعب ٩٠٪» (`save.difficulty`, default Easy; Settings → «مستوى الصعوبة» changes it for the stories
that are not open yet). Every story owns a deterministic **coin set** (`world/coins.js`): coins every
~4.5 m along the A* route from the story before it in its category (or the spawn) to its storyteller,
plus the exploration clusters (≤ 6 m) and big stars (≤ 12 m) near that route, topped up with small
side arches on short routes — 22–45 coins per story. Route coins have ids `"<story>:<k>"`; cluster
coins/stars keep their numeric ids and can count for several sets. Sets are computed a few ms per
frame (on the title screen already) and cached in `localStorage['quran-journey-coinsets']`.
A story opens when (a) the story before it in its category is done and (b) the child has
⌈level × set size⌉ of its coins; then it stays open (`save.opened`). While waiting, its storyteller
shows a padlock in a gold progress ring with a «١٢ / ٢٠ 🪙» pill, talking to them gives a text nudge
(«اجمع ٨ عملات أخرى على الطريق لتفتح القصة!»), the objective chip shows the count, only that story's
route coins are laid out, and the golden trail (and 👣) leads from coin to coin (`guide.update({goal})`).
Reaching the share plays a fanfare, toasts «فتحت القصة! 🎉» and the marker turns into "!".
`window.__game.balance({verify: true})` prints the size/length/reachability table.

**Categories.** `encounters.json` → `categories: [{id, title, icon}]` and per story `category` / `order`
(defaults: `quran`, file order; `systems/progress.js`). Each category is its own chain: a story's
`requires` inside its category, else the story before it in `order`. The stories sheet has a tab per
category (icons `i-quran`, `i-prophets`, `i-companions` in `public/ui/icons.svg`) listing done ✓ /
open ! / coin progress / 🔒. The HUD follows the category of the last picked or finished story
(`save.category`); leaving the sheet on another tab switches to it. Picking a story (sheet or map)
makes it the target even out of chain order, but it still needs its coins. Old saves: done stories
stay done, cluster coins keep counting, and breadcrumb coins collected on the way to a story are
matched to that story's set.

**Walk to the story (👣 / `F`).** Shown in explore mode while a guided route exists. The child
walks the guide's A* route (`systems/autowalk.js` aims ~2.5 m ahead on the polyline) at walking
pace, collecting the breadcrumb coins; the camera follows and slowly swings behind. It stops
~2 m short of the storyteller so the Talk prompt appears (the dialogue never starts by itself).
Tapping 👣 again, the joystick, a movement key or tap-to-walk cancels. Re-routes are followed
as they arrive; if progress stalls for 2 s it aims further along the route, and after a couple
of tries it stops with a gentle message.

## Quality levels

Settings → Graphics quality: Auto / Lite «خفيف جدًا» / Low / Medium / High / Ultra.
**The level is settled on the loading screen, before anything is built** («نجهّز العالم لجهازك…»):
`main.jsx` awaits `resolveQuality()` and only then loads the game module (and its store), so the
world is built once, at that level (`window.__builds` lists each build; `window.__quality` the
decision). Order of precedence: a level chosen in Settings → the remembered measured Lite →
Auto. **Device age:** a device from before ~2021 starts on Low (Lite if the guess below already
says Lite); 2021+ keeps the guess. "Before 2021" is any of: Android ≤ 10 (UA Client Hints
`platformVersion`; the UA string only when it isn't Chrome's frozen "Android 10; K"), iOS ≤ 14,
an iPhone screen only older models have (320×568, 375×667, 414×736, 414×896), a GPU from the
`OLD_GPU` table in `quality.js` (Adreno ≤ 650, Mali-T / G31…G77, PowerVR, Apple A12-, Intel HD /
UHD 6xx / Iris Plus, GTX 9xx–16xx / MX, Radeon R/HD/RX 4xx–5xx/Vega), or ≤ 2 GB `deviceMemory`.
Auto's guess itself (`systems/quality.js`: GPU string, `deviceMemory`,
`hardwareConcurrency`, phone/tablet UA; High only for clearly strong desktop GPUs):
**Lite** for old/weak devices — ≤ 2–3 GB RAM phones, quad-core Android phones, old GPUs
(Mali-4xx / T6xx–T8xx / G31–G57, Adreno 3xx/4xx/5xx below 530, PowerVR, Intel HD ≤ 5xxx,
VideoCore/Vivante, software renderers). It also drops to Lite when the first seconds on the
title / first steps measure < 25 fps, and at runtime from Low when fps stays < 28 — mid-play that
switches only Lite's per-frame settings (30 fps cap, DPR ≤ 1, baked shadow, simple water…), never
a rebuild; it is remembered in `localStorage['quran-journey-perf']` so the next launch *builds*
Lite straight away. While
exploring, drei's `PerformanceMonitor` first trims the resolution (down to 70 %), then steps the
level down (or back up; Lite never climbs by itself). Phones cap the pixel ratio at 1.5.
Menus redraw at ~12 fps, hidden tabs not at all.

| | Lite | Low | Medium | High | Ultra |
|---|---|---|---|---|---|
| Frame rate | capped at 30 (8 under the Quran overlay) | display | display | display | display |
| Resolution scale | 1, never above (0.75 on tiny GPUs / 2 GB phones) | 0.8 | 1 | 1.25 | 1.75 |
| Sun shadows | 2K map rendered **once** for the static world (re-baked after walking ~40 m); the cast get soft blob shadows | 1K · 3rd frame | 2K · 2nd frame | 2K · frame | 4K · frame |
| Houses, props, trees | merged per 24 m cell × material (detailed < 14 m, LOD1 < 35 m, big shapes only to 100 m), no wind on trees | instanced per model, LOD by distance | ✓ | ✓ | ✓ |
| Grass clumps · drawn within | 2.6k · 20 m | 12k · 42 m | 34k | 65k | 100k |
| Crops drawn within | 24 m (the terrain paints the fields) | 38 m | 55 m | 70 m | 90 m |
| Terrain grid | 224² in 4×4 culled tiles | 256² | 320² | 360² | 360² |
| Cast drawn within · posed | 30 m · ~10 fps beyond 12 m; each character merged to 2–3 draw calls | 60 m | 90 m | 140 m | 200 m |
| Ink outlines · birds · motes | – · – · – | – · ✓ · some | ✓ | ✓ | ✓ |
| Water | flat bands + bank foam | toon water (bands, foam, streaks) | ✓ | ✓ | ✓ |
| Sky clouds / fog | 2 noise octaves / haze 30–125 m | 4 / 90–620 m | ✓ | ✓ | ✓ |
| Post-processing | off (not even downloaded) | off | bloom, DoF, SMAA… | ✓ | ✓ |

Measured headless (Chromium + SwiftShader, spawn view down the village street — the heaviest
view — renderer.info per frame):

| | draw calls | triangles | geometries · programs | frame (SwiftShader) |
|---|---|---|---|---|
| Low, 1280×720 | 166 | 668k | 173 · 47 | 760 ms |
| **Lite**, 1280×720 | **74** | **165k** | 131 · 33 | 490–540 ms (at 1.56× Low's pixels) |
| Low, phone 390×844 @3x | 146 | 606k | 172 · 44 | 495 ms |
| **Lite**, phone 390×844 @3x | **46** | **134k** | 93 · 29 | 210 ms |

The shadow map (Low and up) is also redrawn whenever the child moves, so their own shadow never
lags. Grass, flowers, crops, reeds and bushes are chunked (24 m) and thinned toward their draw
distance (instances are shuffled, so drawing the first N is an even thinning). Draw distances
are measured from what the camera frames and stretch (thinner) as it zooms out; the shadow box
grows with the zoom. Voice (Piper / onnxruntime) and post-processing are lazy chunks; three and
React are separate cached chunks. All GLBs go through one loader with one local Draco decoder;
a storyteller's GLB is only fetched when the camera first comes within draw distance + 60 m.
Google Fonts load without blocking the first paint.

## Offline app (PWA)

The build is an installable Progressive Web App that works without internet:

- `public/manifest.webmanifest` — «رحلة مع القرآن», `lang: ar`, `dir: rtl`, fullscreen, any
  orientation, teal `#0f2a33` theme; icons in `public/icons/` (192/512, maskable, apple-touch)
  made from the title emblem by `python3 tools/make_icons.py` (headless Chromium via Playwright
  if installed, else ImageMagick). `start_url`/`scope` are `./`, so the same `dist/` works at
  `/old/3d-quranic/dist/` and on GitHub Pages (`/<repo>/`).
- `src/pwa/sw.js` — the service worker, emitted as `dist/sw.js` by `tools/vite-pwa.js` with the
  precache list of **this** build (hand-written, no Workbox: `vite-plugin-pwa` would not install
  here). It precaches the shell, JS/CSS, `data/encounters.json`, UI svgs, every model + the Draco
  decoder, the illustrations and the recorded voice lines — **~15 MB (337 files; 4.8 MB core)**,
  see `dist/precache-report.json`. Files keep their cache entry across versions when unchanged.
  Not precached: the Piper voice (63 MB, Piper keeps it itself; it is not even requested offline)
  and the Piper/onnxruntime chunks.
- Quran.com: API JSON is stale-while-revalidate, recitation mp3s cache-first with byte-range
  support — any story played once works offline. **Settings → «تنزيل كل القصص للّعب بدون
  إنترنت»** fetches (3 at a time, with a progress bar) only what the stories use: 5 chapters,
  16 verses + tafsir, 16 recitation mp3s. Offline, a verse that was never fetched shows a kind
  message («هذه الآيات تحتاج اتصالًا بالإنترنت أول مرة…») and the story continues by itself.
- Updates: a new deploy installs in the background and waits; a small «تحديث جديد متاح — اضغط
  للتحديث» button appears and reloads into the new version only when tapped.
- Install: «ثبّت اللعبة» on the title screen when the browser offers installation
  (Android / desktop Chrome, Edge); on iOS Safari it shows the Share → «إضافة إلى الشاشة
  الرئيسية» hint.
- The service worker registers ~2.5 s after the world is up (so the precache never competes with
  the first load) and needs https or localhost.

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
