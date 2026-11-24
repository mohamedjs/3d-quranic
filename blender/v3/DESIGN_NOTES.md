# Blender v3 Character Restyle — Design Notes

## Aesthetic & Technical Direction
- **Target look**: Warm Pixar/Ghibli children's storybook 3D — soft, rounded facial silhouettes (eliminating v2's sharp triangular anime chins and flat face planes), integrated 3D noses, 3D orbital sockets with domed multi-highlight eyes, sculpted 3D eyebrows, rounded ears (omitted where wrapped under headwear), soft mitten+thumb hands, and clean inverted-hull ink outlines (`#2B1A10`).
- **Proportions**: Child (`player`) at **1:4.2** heads; adults at **1:5.4–5.7** heads, giving warm, approachable, readable silhouettes on mobile screens.
- **Shared 22-bone skeleton (`rig.py`)**: Replaces v2's heavy 56–68 bone MPFB rig with a clean 22-bone analytical skeleton (`pelvis`, `spine_01`, `spine_02`, `neck`, `head`, `lid_l`, `lid_r`, `mouth`, `clavicle/upperarm/lowerarm/hand` ×2, `thigh/calf/foot` ×2) in a relaxed 68° A-pose so sleeves drape smoothly without shoulder pinching or spikes.
- **Single 512×512 face+eye texture atlas (`toon_face_<key>`)**: Packed directly into `.blend` and `.glb` (zero external `tex/` directory). Maps warm cheek/nose blush, gentle elder laugh crinkles, soft lip shading, and an anti-aliased high-resolution iris+sclera+catchlight quadrant onto the 3D eyeballs.
- **Selective inverted-hull outlines**: Thin outlines (`0.0028 m`) on head/skin/hands, crisp outlines (`0.0046 m`) on garments/hair/headwear; eyes, lashes, eyelids, eyebrows, talking mouth, glasses, and flush trims/piping are completely excluded (`0.0 m`) from the outline hull.
- **Zero-clipping cloth strategy**: Hidden torso/upper-leg skin under full-coverage robes is omitted; sleeves are roof-clamped smoothly to the collarbone slope; robes and skirts skin smoothly across `pelvis`, `thigh_l/r`, and `calf_l/r` so walking heels never poke through hems and Grandma Zainab's continuous dress bends cleanly across her seated lap and knees.

## Per-Character Look & Choices

### 1. `player` — Explorer Boy (1.25 m · 1:4.2 · `idle`, `walk`, `run`, `talk`)
- **Silhouette & rear readability**: Because the player sees him from behind most of the time, gave him a cohesive tousled chestnut-brown hair silhouette with sculpted wave lobes, sideburns, and sweeping bangs (clear of his 3D eyebrows), plus a chunky cognac-leather satchel (`#9B5B30`) with darker leather flap, sun-gold brass buckles, top carry handle, and body-hugging spline shoulder straps.
- **Outfit**: Warm cream knee-length galabiya (`#F2E5C9`) with turquoise neckline placket & cuffs (`#2F8B8C`), golden cloth waist sash with knotted hanging side tails (`#DFA543`), comfy sand sirwal trousers (`#D8C7A8`) overlapping the ankles cleanly, and rounded leather sandals.

### 2. `farmer` — Grandpa Salim (الجدّ سالم · 1.74 m · 1:5.6 · `idle`, `walk`, `talk`)
- **Look**: Kindly, sturdy village elder with a gentle forward stoop, warm tanned skin (`#B97B53`), laugh crinkles, bushy white 3D eyebrows visible beneath a 4-wrap layered cream rural turban (`عمّة`), and a full soft U-rounded white beard and curved moustache.
- **Outfit**: Warm earth-brown galabiya (`#835230`), tailored open-V olive-moss village waistcoat (`#556B3E`) with brass buttons, a flat-draped woven village scarf over his right shoulder, dark brown leather slippers, and a hand-carved wooden walking staff with dark leather grip bound in his posed left hand.

### 3. `grandma_zainab` — Grandma Zainab (الجدّة زينب · 1.58 m · 1:5.4 · `sit`, `sit_talk`, `idle`)
- **Look**: Warm, round-cheeked, affectionate grandmother seated comfortably on the 0.45 m mastaba bench with kind laugh crinkles, gentle grey arched brows, and softly winged lashes.
- **Outfit**: Rich velvety charcoal-plum modest dress (`#30293A`) and deep dark tarha (`#25202E`) accented with warm antique sun-gold trim (`#E5B454`) along her cuffs, the sweeping tarha hem, and a continuous curved golden brow-to-cheek trim framing her face. Her continuous skirt is weighted specifically for hip/knee flexion (`seated_mode=True`) so `sit`, `sit_talk`, and `idle` all deform cleanly without knee or arm clipping.

### 4. `grandma` — Grandma Amina (الجدّة آمنة · 1.60 m · 1:5.5 · `idle`, `walk`, `talk`)
- **Look**: Warm scholarly storyteller with lighter warm-olive Egyptian skin (`#D5A27C`), kind arched brows, and delicate warm-gold round spectacles (`toon_glasses_gold`, excluded from outline) perched accurately on her 3D nose bridge with slim temples tucking into her hijab.
- **Outfit**: Palm-emerald modest dress (`#2E6E54`) with cream-gold cuffs (`#ECD49A`), draped lapis-indigo hijab (`#3B4F8F`) with a soft back bun silhouette and rounded shoulder drape, and brown leather slippers.

### 5. `trader` — Uncle Hamdan (العم حمدان · 1.78 m · 1:5.7 · `idle`, `walk`, `talk`)
- **Look**: Broad-shouldered, confident middle-aged caravan merchant with warm bronze skin (`#BC8258`), neat trimmed dark espresso beard and moustache, and expressive dark brows.
- **Outfit**: Royal indigo-blue thobe (`#2E457E`) with a golden waist sash underneath a majestic open-front espresso-brown desert bisht (`#573B2A`) edged in gleaming sun-gold zari border trim (`#F0BE59`), crowned by a crisp red-and-cream woven checkered shemagh (continuous cylindrical UVs, zero neck clipping) and a double-coil black agal with subtle gold cord wraps.

### 6. `sheikh` — Sheikh Younis (الشيخ يونس · 1.76 m · 1:5.6 · `idle`, `walk`, `talk`) — NEW
- **Look**: Serene, dignified village teacher with kind scholarly expression, gentle elder laugh lines, visible silver-grey 3D eyebrows, and a neat rounded silver-grey beard and moustache.
- **Outfit**: Classic Egyptian Azhari/village teacher silhouette — crisp white layered imama wrapped around a crimson-burgundy tarboush dome (`#8F2929`), light olive-sage open kaftan (`#748857`) with warm cream-gold piping (`#E0C078`) layered smoothly over an ivory thobe (`#F4EBDA`) whose cuffs peek out cleanly at the wrists, plus walnut leather slippers.

### 7. `aunt` — Aunt Salma (الخالة سلمى · 1.58 m · 1:5.4 · `idle`, `walk`, `talk`) — NEW
- **Look**: Youthful (~35 y), cheerful orchard keeper with warm sunlit skin (`#D0966B`), rosy cheeks, bright eyes with delicate lash flicks, and an expressive joyful smile.
- **Outfit**: Warm terracotta-rose draped hijab (`#C26052`) with a gentle asymmetric front-left scarf drape and back bun, sunny ochre-gold long dress (`#DCA042`) with cream cuffs, a vibrant turquoise woven waist sash (`#2A8A8B`) knotted with hanging ribbons at her hip, and tan leather slippers.

## Budgets & Export Verification Summary

| key | tris | outline_tris | total_tris (≤15k) | bones (≤30) | glb_kb (≤600) | clips |
|---|---:|---:|---:|---:|---:|---|
| `player` | 7,298 | 6,156 | 13,454 | 22 | 196.4 | `idle`, `walk`, `run`, `talk` |
| `farmer` | 7,550 | 6,168 | 13,718 | 22 | 176.8 | `idle`, `walk`, `talk` |
| `grandma_zainab` | 5,320 | 3,912 | 9,232 | 22 | 157.1 | `sit`, `sit_talk`, `idle` |
| `grandma` | 5,462 | 3,780 | 9,242 | 22 | 160.5 | `idle`, `walk`, `talk` |
| `trader` | 7,724 | 6,208 | 13,932 | 22 | 183.2 | `idle`, `walk`, `talk` |
| `sheikh` | 7,966 | 6,634 | 14,600 | 22 | 182.8 | `idle`, `walk`, `talk` |
| `aunt` | 5,098 | 4,100 | 9,198 | 22 | 160.3 | `idle`, `walk`, `talk` |

## Open Notes / Future Polish Ideas
- In `sheikh_turn.png` and `trader_turn.png`, the outer kaftan/bisht shoulder seam has a tiny crisp step where the wide outer sleeve joins the collar yoke (intentionally kept tight so the inner thobe sleeve stays 100% hidden); in a future pass, lofting the outer cloak and outer sleeves as a single unified topology could smooth that seam even further.
- On `trader_turn.png` side view, a tiny dark edge of the bisht shoulder cap briefly touches the upper shemagh fold at the outer deltoid corner when looking strictly side-on; completely invisible from front, 3/4, and back, and zero clipping in motion.
- All 7 GLBs satisfy `src/game/characters/glbRig.js` requirements (Draco 6, Y-up, origin at feet, facing +Z in glTF, `head` node, `toon_*` + `outline` materials, UVMap present on all primitives for Lite `mergeSkinned`, zero morph targets).
