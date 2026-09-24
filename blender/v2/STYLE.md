# Blender v2 — anime / toon rebuild (shared contract for all agents)

## Look
Warm anime / Ghibli-like village of the Egyptian countryside at golden hour. Humanoid (not chibi)
proportions, clean readable shapes, flat colours with 2–3 cel bands, warm shadows, dark-brown
ink outlines. See docs/art-direction.md for the palette (sun gold #F4C766, clay #B8743F/#D9A066,
palm green #4F7A2A/#8DB34A, ink #2B1A10).

- Shading in Blender preview: EEVEE, Diffuse → Shader to RGB → ColorRamp (CONSTANT, 3 stops)
  × base colour, + soft rim; world = warm sky gradient. Materials must ALSO carry a plain
  Principled "Base Color" (flat colour or small painted texture) so glTF exports cleanly.
- Outlines: inverted hull — a copy of the mesh with Solidify (offset −1, flip normals, thickness
  0.006 m characters / 0.02–0.03 m buildings) using material `outline` (ink #2B1A10, backface
  culling on). In GLBs export the hull as its own mesh named `<obj>_outline`, material `outline`
  (the game renders it with BackSide + unlit). Keep it skinned for characters.
- Material names: `toon_<what>` (e.g. toon_skin_boy, toon_galabiya_brown, toon_plaster,
  toon_wood_blue) + `outline`. Textures only where needed (faces/eyes, small painted details),
  ≤ 512 px (faces 1024 max), PNG/JPEG. No realistic PBR maps.

## Units / axes
Metres, Z up, character faces −Y in Blender (= +Z in glTF/three). Origin at the feet (characters)
or at the ground centre of the footprint (props/houses). Apply transforms before export.

## Running Blender
- The GUI Blender (on the user's desktop) runs `blender/_bridge/bridge.py`. Use it only for
  quick things: `python3 blender/_bridge/bx.py job.py`.
- For all real work start your OWN background Blender (parallel-safe, several at once):
  `python3 blender/v2/bg.py <script.py> <name>` → returns immediately; poll
  `blender/v2/_jobs/<name>.log` until a line `BG_DONE ok|error`. Scripts must be self-contained
  (open/save their own .blend, render previews with bpy.ops.render.render(write_still=True)).
  Paths inside scripts must be HOST paths: /var/www/html/old/3d-quranic/...
- Previews: render PNGs into blender/v2/previews/ then stage + Read them to judge the look.

## Files
blender/v2/characters/  build scripts + characters.blend     → public/models/*.glb
blender/v2/env/         build scripts + env.blend            → public/models/env/*.glb
blender/v2/village_v2.blend  the assembled village the user opens (env + cast)
blender/v2/previews/    preview renders (PNG)

## Budgets (browser, per GLB, Draco level 6)
characters ≤ 1.5 MB, ~12–20k tris incl. outline · houses ≤ 250 KB, ≤ 6k tris (+ LOD1 at ~35 %
named `<name>_LOD1`) · small props ≤ 60 KB · plants: tiny instanced meshes ≤ 800 tris.
