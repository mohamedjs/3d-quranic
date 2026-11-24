# 001 — Character restyle v3 (Blender)
Status: Ready     Builds on: UNDERSTANDING_AND_AUDIT.md §2, blender/v2/STYLE.md, docs/art-direction.md

Executor: Gemini 4 Neon (XHigh). Orchestrator/reviewer: Claude Opus 5.5.
**You are the character artist.** This doc fixes the contract (files, export format, names,
budgets, cast). Inside that contract the visual design is YOUR call: face shapes, eye style,
clothing cut, folds, colours within the palette, animation acting. Make them beautiful — this is
the main thing the owner will judge. Record your design choices in `blender/v3/DESIGN_NOTES.md` (do not edit this doc).

## 1. Goal
The villagers in the game «رحلة مع القرآن» (a 3D Quran-stories game for children, Egyptian Nile
village at golden hour, React Three Fiber) look stiff and off-model today (see
`blender/v2/previews/cast_lineup.png`, `cast_faces.png`): pointy anime chins, flat decal faces,
garments clipping through bodies, blocky hair, heavy MPFB rigs. Rebuild the whole cast from
scratch in Blender as warm, appealing **storybook-stylized 3D characters** (think a gentle
Pixar/Ghibli children's film: round soft silhouettes, big warm expressive eyes, readable shapes,
cel-shaded) and export them as GLBs the game already knows how to load.

Children play this on phones and in browsers, so beauty must come from good shapes and colour,
not from polygon count.

## 2. Stack
- Blender 5.2.2 LTS at `/home/mohamed/.local/bin/blender`. Run headless:
  `blender -b --python blender/v3/characters/build_all.py -- <keys...>`
  (no GUI bridge needed; ignore `blender/_bridge` and `blender/v2/bg.py`).
- Python inside Blender only (bpy, bmesh, mathutils, numpy). No add-ons, no MPFB, no downloads,
  no external assets: everything is modelled procedurally by script.
- glTF exporter built into Blender (Draco level 6).

## 3. Structure (create exactly these; nothing else in the repo changes)
```
blender/v3/characters/
  build_all.py      entry point: build → export GLB → render previews, for the keys given (default: all)
  lib.py            shared helpers: scene reset, materials (toon_* + outline), outline hull, export, tri count
  rig.py            the shared light skeleton + automatic weights + face bones
  head.py           head/face builder (3D nose, brows, ears, eyes, lids, mouth, hair/beard helpers)
  body.py           stylized body builder (proportions per character, hands, feet)
  garments.py       clothing builders (galabiya/thobe, vest, hijab/tarha, turban, shemagh+agal, bisht, backpack, staff, glasses)
  anim.py           animation clips (idle, walk, run, talk, sit, sit_talk) as NLA tracks
  cast.py           the CAST dict: one entry per character (proportions, colours, outfit, clips)
  preview.py        preview renders (EEVEE, cel look)
  characters.blend  saved result (binary, written by build_all.py)
blender/v3/DESIGN_NOTES.md   your design notes: per character the look you chose and why, open issues
blender/v3/previews/
  <key>_turn.png    4-view turnaround per character (front, 3/4, side, back), 1600×900
  <key>_face.png    face close-up per character, 900×900
  lineup.png        all 7 side by side on a warm gradient, 2600×1000
  poses.png         walk/run/talk/sit key poses
public/models/
  player.glb  farmer.glb  grandma_zainab.glb  grandma.glb  trader.glb   (overwrite)
  sheikh.glb  aunt.glb                                                 (new)
```
`blender/v2/` stays untouched as reference. You may read anything under `blender/v2/` and
copy ideas/code from it (e.g. `toon_lib.py` cel material, `anim.py` clip structure, the export
call in `build_all.py`), but v3 must not import from v2.

## 4. File responsibilities
- `build_all.py` — parses keys after `--`, calls `lib.reset_scene()`, `cast.build(key)` per key,
  `lib.export_glb(info)`, saves `characters.blend`, calls preview renders, prints one line per
  character: `BUILT <key> tris=<n> outline_tris=<n> bones=<n> glb_kb=<n>`.
- `lib.py` — no character knowledge. Materials, hull, export, stats.
- `rig.py` — builds the armature from a proportions dict; parents meshes with weights.
- `head.py` / `body.py` / `garments.py` — return mesh objects; no export, no animation.
- `anim.py` — creates actions and pushes them to NLA tracks with the exact clip names.
- `cast.py` — data + per-character assembly only.
- `preview.py` — cameras, lights, renders. Never touches exported objects' data.

## 5. Export contract (the game depends on this — do not deviate)
The loader is `src/game/characters/glbRig.js` (read it). Requirements:
1. One GLB per character in `public/models/`, Y-up, metres, origin at the feet, character faces
   **+Z in glTF** (−Y in Blender). The game rescales to the height in §7, so real height only
   needs to be roughly right.
2. Clips by exact name (NLA tracks, 24 fps, seamless loops):
   - player: `idle`, `walk`, `run`, `talk`
   - farmer, grandma, trader, sheikh, aunt: `idle`, `walk`, `talk`
   - grandma_zainab: `sit`, `sit_talk`, `idle`
   Walk covers ~1.1 m per cycle, run ~2.7 m/s at 1× — so feet don't slide (the game scales
   timeScale by ground speed). Clips animate in place (no root translation).
3. A bone named exactly `head`.
4. Materials: body/clothes/hair named `toon_<what>` (e.g. `toon_skin`, `toon_galabiya`,
   `toon_hair`) with a plain Principled Base Color (flat colour) — the game replaces them with its
   own cel shader and keeps only `color` and `map`. Faces may use one texture (`toon_face`,
   ≤ 512 px, eyes/mouth painted or separate small meshes — your choice). Names containing
   `lash` or `brow` get alpha-cutout. Avoid other transparency.
5. Outline: inverted-hull copy of the skinned mesh, named `<mesh>_outline`, material named exactly
   `outline`, skinned to the same armature. Leave eyes, lids, mouth, brows and glasses OUT of the
   hull. Thinner on face/hands (~0.003 m), ~0.005 m on clothes/hair.
6. Few objects: the loader merges same-skeleton untextured parts in lite mode, so keep all parts
   skinned to the one armature, with identical object transforms (apply transforms).
7. No shape keys / morph targets (export_morph=False). Face motion (blink, mouth) via small face
   bones (`lid_l`, `lid_r`, `jaw` or `mouth`) is welcome.

## 6. Conventions
- Python: 4-space indent, snake_case, short docstring at the top of each file, constants UPPER.
- All paths absolute from `ROOT = '/var/www/html/old/3d-quranic/'`.
- Deterministic: no randomness without a fixed seed.
- Every script must run headless from a fresh Blender with no saved state.

## 7. The cast (identity is fixed; the look is yours)
Egyptian/Arab countryside villagers, modest Islamic dress. Women always in hijab/tarha covering
hair and neck, loose dresses, long sleeves. Nobody depicts a prophet or companion — these are
ordinary villagers who tell the stories.

| key | who | height | role in game | notes |
|---|---|---|---|---|
| `player` | the boy you play, ~8 y | 1.25 | runs everywhere, seen from behind most of the time | readable from behind: hair, small backpack, galabiya + trousers, sandals |
| `farmer` | Grandpa Salim (الجدّ سالم) | 1.74 | farmer, story host | old, white beard and moustache, turban (عمّة), wooden staff in left hand, warm brown galabiya |
| `grandma_zainab` | Grandma Zainab (الجدّة زينب) | 1.58 | the boy's grandmother, sits on the mastaba bench | seated at 0.45 m seat height; dark tarha, kind round face, may have a gold trim; dress designed for sitting — no clipping through knees/arms |
| `grandma` | Grandma Amina (الجدّة آمنة) | 1.60 | storyteller | round glasses on the nose bridge, indigo/blue hijab, green dress |
| `trader` | Uncle Hamdan (العم حمدان) | 1.78 | caravan trader | middle-aged, short dark beard, red-white shemagh + black agal, blue thobe, open bisht with gold trim |
| `sheikh` | Sheikh Younis (الشيخ يونس) — NEW | 1.76 | village teacher | white turban over a small red tarboush or plain white imama, neat grey beard, light olive kaftan over ivory thobe, kind scholarly face |
| `aunt` | Aunt Salma (الخالة سلمى) — NEW | 1.58 | orchard keeper, ~35 y | warm terracotta/rose hijab, ochre-gold dress, turquoise sash; youthful, cheerful |

Palette: docs/art-direction.md (sun gold #F4C766, clay #B8743F/#D9A066, palm green, ink outline
#2B1A10). Skin: warm Egyptian browns, varied per character.

## 8. Quality bar and budgets
- Proportions: child ~1:4.2 heads, adults ~1:5.5–6. Round soft chins, real 3D noses, brows,
  ears (hidden under hijab/headwear where appropriate), expressive eyes with highlights.
- Hands: simple mitten + thumb is fine; no 5-finger bone chains needed.
- Garments are modelled ON the body silhouette with clearance — zero visible clipping in any
  clip at any frame (check the extreme frames of walk/run/sit).
- Budget per GLB (Draco 6): **≤ 15k triangles incl. outline, ≤ 600 KB, ≤ 30 bones**.
- Look in EEVEE previews: cel ramp (2–3 bands) + rim, like v2's `toon_lib.py`, so previews
  match the game's toon shader.

## 9. Tasks
1. Read `src/game/characters/glbRig.js`, `blender/v2/STYLE.md`, `blender/v2/characters/*.py`,
   look at `blender/v2/previews/*.png` to see what is wrong today.
2. Build `lib.py`, `rig.py`, `body.py`, `head.py` and ONE character (`player`) end to end;
   render its turnaround + face; look at the PNGs yourself and iterate until it is genuinely
   appealing.
3. Then the other six, re-using the shared builders.
4. `lineup.png`, `poses.png`; export all 7 GLBs.
5. Run the acceptance checks; fix anything that fails.

## 10. Acceptance checks
- `blender -b --python blender/v3/characters/build_all.py` exits 0 and prints 7 `BUILT` lines
  within budget.
- `python3 - <<'E'` script (write it inline, don't add a file) that parses each GLB's JSON chunk
  and asserts: clip names per §5.2, a node named `head`, a material named `outline`, ≤ 30 joints.
- All preview PNGs from §3 exist and you have looked at each one.

## 11. Out of scope
Do not edit anything under `src/`, `public/data/`, `public/audio/`, `docs/`, `blender/v2/`. Do not commit, do not push, do not run npm. Do not wire
`sheikh`/`aunt` into the game — the orchestrator does that.

## 12. Decisions
(orchestrator answers to the artist's questions)
