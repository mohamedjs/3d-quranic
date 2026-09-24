# Blender pipeline — Surat Al-Fil

Open `scene/al_fil_story.blend`, look through the camera (Numpad 0) and press Space.
Markers on the timeline = one line of dialogue each; full Arabic script: Text Editor → `AlFil_script`.

Rebuild from scratch (run inside Blender, in this order):
1. characters.py   (KEYS = ['player','farmer','grandma'])  MPFB bodies + rig
2. dress.py        galabiyas, turban, tarha, sirwal
3. stylize.py      white beard, keffiyeh scarf, curly hair, backpack
4. anim.py         idle / walk / run / talk
5. story_chars.py  keffiyeh pattern, grandma sit + sit_talk, seated skirt, bodice
6. env_scene.py    terrain, fields, canal water, grass/berseem/maize/reeds (FAST=True → lighter viewport)
7. env_place.py    houses, mastaba, palms, props, HDRI sky + sun, cast placement
8. story_timeline.py  reads public/data/encounters.json → camera shots, NLA clips, markers
9. export_story.py → public/models/{player,farmer,grandma}.glb   (then reopen the .blend)

Claude bridge: run `bridge.py` once in Blender (Scripting → Run Script); jobs go through `_bridge/`.
