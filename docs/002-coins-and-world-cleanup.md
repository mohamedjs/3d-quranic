# 002 — Coins and world cleanup
Status: Ready     Builds on: UNDERSTANDING_AND_AUDIT.md §3–§4 (Gemini's audit; every finding below was re-checked against the code)

Executor: Gemini 4 Neon (High). Reviewer: Claude Opus 5.5.

## 1. Goal
The game «رحلة مع القرآن» (React 19 + R3F + three r186 + Vite, `src/game/`) has a set of small
bugs that make it feel unpolished, worst of all the coin collection. Fix them all, each with the
smallest change that is correct, without changing how the game plays or looks otherwise and
without costing frame rate on phones (Lite preset, 30 fps cap).

## 2. Stack
Nothing to install (`node_modules` is present). `npm run build` must pass. No new packages.

## 3. Structure — the only files you may change
```
src/game/world/coins.js
src/game/systems/game.js
src/game/systems/guide.js
src/game/terrain/heightfield.js
src/game/terrain/terrainGeometry.js
src/game/shaders/terrainMaterial.js
src/game/world/details.js
src/game/ui/ui.js
src/game/characters/glbRig.js
src/game/characters/Blobs.jsx
public/data/encounters.json        (only the one position fix in task 9)
public/.nojekyll                   (new, empty)
```

## 4–6. Responsibilities, layering, conventions
Keep each file's current role. Match the existing style exactly: ES modules, 2-space indent,
single quotes, semicolons, dense one-line helpers, short comments that say WHY. No TypeScript,
no new files beyond §3, no console noise in hot paths, no allocations per frame.

## 7–9. Tasks (do them in this order)

### Coins (`coins.js`, `game.js`, `guide.js`)
1. **Coins and chevrons drawn on top of each other.** Route coins sit exactly on the guide
   trail line, so the golden chevrons are drawn through every coin and the way ahead looks like a
   tangle. Fix in `guide.js` trail loop: skip (fade to 0) a chevron whose position is within
   0.9 m (horizontal) of an uncollected coin of the currently shown set. Expose from `coins.js` a
   cheap query `coins.occupied(x, z, r)` that only checks the ≤ 64 pool slots in state IDLE
   (route coins of the shown set) — no scan of static coins. Pass it to guide via the existing
   `guide.update(..., { ... })` options object from `game.js` (`occupied: coins.occupied`). Keep
   the chevrons everywhere else unchanged.
2. **Slow first appearance (“…” / «نجهّز العملات على الطريق…»).** Add `ensure(id)` to the coins API:
   if `id` is queued or is the running job, finish it synchronously right now (run the search
   with an unlimited budget: `search.step(1e9)`), so its set exists in the same frame. Call
   `coins.ensure(id)` from `chooseStory(id)` and from `updateObjective()` right after
   `coins.want([target.enc.id], true)`. Background building of the other sets stays time-sliced.
3. **POP slot bug.** In `show(id)` pool slots still in state POP are neither cleared nor reused, so
   a new story's coins at those indices silently go missing. Fix: when `show()` runs, every slot
   in POP is finished immediately (set to 0 before laying out) — the pop animation of a coin
   picked up in the same instant as a target switch may be cut short; that is acceptable.
4. **Bad cache entries.** In the localStorage cache: bump `SET_VERSION` to 3; never write a set to
   the cache when its route has `reached === false` (still use it in memory); include in `sig`
   a short hash of all storytellers' positions (the `avoid` list rounded to 0.1 m) so moving a
   character invalidates old sets.

### Guide arrows (`guide.js`)
5. Chevrons tilt with the ground: build the chevron quaternion from the route tangent in 3D
   (use `route.y` slope between the same `a`/`b` samples), so they lie on slopes and bridges
   instead of sinking in.
6. Short routes (< 4 m) must still show at least the last 2 chevrons: clamp the end-fade so it
   never zeroes the whole trail.
7. Chaikin smoothing in `buildRoute()`: after smoothing, if a smoothed point is not
   `grid.walkable`, keep the original unsmoothed point there.

### World (`heightfield.js`, `details.js`, terrain)
8. **Missing footbridge.** `details.js:24` places a footbridge at `(CX, 34.5)` that is not in
   `FOOTBRIDGES`, so walking and A* ignore it. Move it into `FOOTBRIDGES` in `heightfield.js`
   (same x, z, rot as placed now — read `CX` and the rotation from `details.js`) and delete the
   separate `place('footbridge', ...)` line, so it's drawn once by the existing loop. Check the
   deck height of the loop matches what the old line produced; if it differs visibly, keep the
   loop's.
9. **Two storytellers too close at the oasis.** `yusuf-dream` and `isa-in-the-cradle` hosts are
   3.55 m apart. In `public/data/encounters.json` move the `isa-in-the-cradle` host 3 m further
   away from yusuf along the line between them (keep `facing` pointing back toward the oasis
   centre roughly as before). Verify the new spot is walkable ground, not water (use
   `grid.walkable` / `groundAt` logic or check in the browser).
10. **Jagged roads in Lite.** Roads come from `pathDist` sampled per vertex (Lite grid ≈ 2.3 m),
    so diagonal roads look stair-stepped. Fix: at terrain build time bake `pathDist` for the whole
    map into a 1024×1024 single-channel `THREE.DataTexture` (Uint8, distance clamped to 0–8 m,
    linear filtering) once, and sample it in the terrain fragment shader instead of the
    interpolated vertex value. One texture fetch per pixel, same look on all presets. Bake cost
    must stay < 150 ms on desktop (measure with `performance.now()`; if it's more, bake 512²).

### UI (`ui.js`)
11. **World-map route drifts when zooming.** `layer` moves in % but `routeG` in px
    (`ui.js` `layout()`): make the route follow the same transform as `layer` (put `routeG`
    inside `layer`, or convert to the same units) so the golden line stays on the roads at every
    zoom/pan.
12. `SURAHS` has 5 entries; replace it with all 114 surah names `[ar, en]` (standard transliterated
    English names, e.g. 'Al-Fatihah', 'Al-Baqarah', …, 'An-Nas').
13. `REGIONS`: add `ru` names (Оазис, Деревня, Река и поля, Горы, Древнее поселение, Пустынная
    тропа) and use them when the language is `ru` wherever `ar`/`en` are picked.

### Loader / hosting
14. `glbRig.js` HEAD check: reject only when `!head.ok` or the content-type contains
    `text/html`; any other or missing content-type is accepted (GitHub Pages serves .glb as
    `application/octet-stream` or nothing). Leave `wave()` as is.
15. `Blobs.jsx`: `MAX = 24` → `48`.
16. Create empty `public/.nojekyll`.

## 10. Acceptance checks (run them, report output)
- `npm run build` exits 0.
- Dev server `npx vite --port 5181 --strictPort` starts; then in a headless Chromium with
  SwiftShader (`--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`; the
  Playwright Chromium is at `~/.cache/ms-playwright/chromium-1248/chrome-linux*/chrome`, use
  `playwright-core` from a temp dir outside the repo): load the page, wait 15 s, run
  `__game.begin()`, wait 5 s; then `__game.balance()` returns a row for every story with
  `notWalkable: 0` and `coins >= 20`; no `pageerror`. Take a screenshot after `begin()` and look
  at it: chevrons must not overlap coins.
- `__game.chooseStory('ali-and-the-trusts')` followed immediately (same evaluate) by
  `__game.coins.progress('ali-and-the-trusts')` returns non-null.

## 11. Out of scope
Do not touch `blender/`, `public/models/`, `public/audio/`, `docs/`, stories text, voices,
illustrations, the service worker, Android. Don't refactor beyond the tasks. Do not commit,
do not push.

## 12. Decisions
