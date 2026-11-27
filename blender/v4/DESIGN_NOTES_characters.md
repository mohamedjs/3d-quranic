# M5 Character Design Notes (v4 — Stylized PBR + Poly Haven Fabrics)

Milestone **M5** rebuilds all 7 character rigs in `blender/v4/characters/` to match the v4 Poly Haven PBR world while preserving the exact v3 runtime contract (22-bone skeleton, exact clip names, heights, seated Zainab pose on the 0.45 m mastaba, +Z glTF facing, feet at origin, Draco 6).

---

## 1. Visual Direction & Material Pipeline

- **Zero ink outlines**: No inverted-hull `outline` geometry is exported (`glbRig.js` still safely ignores any legacy `outline` material if encountered).
- **10-material contract**:
  - **5 Poly Haven fabrics** (UVs authored in real metres via arc-length `loft_rings`/`add_tube`/`add_ring_torus`, base colour + baked 14-ray BVH crevice/fold AO in linear `COLOR_0`):
    - `ph_cotton` → `cotton_jersey` (0.35 m/tile, roughness 0.85) — galabiyas, shirts, dresses, trousers
    - `ph_linen` → `rough_linen` (0.45 m/tile, roughness 0.88) — hijabs, turbans, shemagh, imama, under-thobes
    - `ph_wool` → `knitted_fleece` (0.30 m/tile, roughness 0.90) — farmer vest, Sheikh kaftan, Trader bisht & agal, tarboush
    - `ph_hessian` → `hessian_230` (0.40 m/tile, roughness 0.88) — sashes, striped village scarf, woven hem/placket/collar trims
    - `ph_leather` → `brown_leather` (0.50 m/tile, roughness 0.50) — footwear, player satchel & straps, staff leather grip
  - **5 non-fabric character materials**:
    - `skin` (roughness 0.55) — neck, forearms, hands, ankles, eyelids (warm tinted `COLOR_0`, subtle fingertip/heel warmth)
    - `hair` (roughness 0.60) — sculpted hair clumps, beards, moustaches, brows, lash rims, talking mouth cup
    - `face_<key>` (roughness 0.55) — single embedded 512×512 PNG face/eye atlas (warm skin, soft rosy cheek blush, subtle warm nose-tip highlight and terracotta nostril/under-nose shading, warmer sculpted lips with lower-lip cushion shine, gentle eye creases for elders, rich multi-layer radial-iris eyes with 3 catchlights); vertex colour multiplies subtle chin/brow AO
    - `eye` (roughness 0.12) — glossy cornea eyeballs mapped into the right-side eye tile of `face_<key>`
    - `metal` (roughness 0.30, metalness 1.0) — brass buckles, vest buttons, Grandma Amina's wire glasses, Trader's gold agal wraps
- **Exact palette fidelity & visible fabric weave (`src/game/shaders/characterMaterial.js` + `blender/v4/characters/lib.py`)**:
  - `COLOR_0` linear floats match the exact v3 `DESIGN_NOTES` palette hexes (including restored `#30293A` / `#25202E` on Grandma Zainab).
  - Pure **zero-mean luminance detail** (`dLum = lum(tex) / lum(layerAverage) - 1.0`, symmetrically clamped and applied at `0.55 * detDist`) preserves the exact mean garment colour across all 5 layers without hue drift or dark-channel distortion.
  - Matte fabrics suppress white Fresnel specular wash (`Specular IOR Level = 0.04` in Blender previews; `indirectSpecular *= 0.08`, `directSpecular *= 0.14`, `envMapIntensity = 0.22` on Medium+ PBR) while keeping clean diffuse luminance + soft wrap across folds so in-game colours match v3 saturation and value on both Lite and Medium/High.
  - Medium+ raises per-layer normal-map strengths (`cotton 5.6`, `linen 3.4`, `wool 3.1`, `hessian 1.3`, `leather 1.45`) with `-1.0 * cNormFade` mip bias and subtle near-camera cotton micro-weave relief so cotton, linen, and wool weave are clearly readable at 1–2 m talk-camera distance without shifting mean colour; Lite stays single-fetch diffuse-only with no normal maps.
  - Blender previews render under `Khronos PBR Neutral` (`exposure = 0.05`) with calibrated warm-white sun, fill, rim, and studio IBL so preview hues and values match the v3 reference lineup cleanly.
- **Classic Trader shemagh**:
  - Real-metre symmetrically centered UVs (`+100.0` U-sentinel on `ph_linen`) drive a crisp procedural **2.6 cm red-and-white square houndstooth/check** (`#B23029` on cream `#F7EFE2` with `fwidth` antialiasing and distance-readable check preservation) over the entire head dome and shoulder tails, framed by a bold `#B23029` red border band along the bottom U-hem and cheek edges — synchronized identically in Blender previews and runtime GLSL (both Lite and PBR).
- **Baked crevice & fold AO**: Each character runs a 14-ray hemisphere BVH AO pass over the assembled rest-pose body (darkening under-chin, collar creases, waist sash contact, sleeve cuffs, hem pleats, and under-hijab shadows), clamped safely above `0.78` on the face so no character ever has dark/muddy facial shading.
- **Runtime 3-draw merge (`src/game/characters/glbRig.js` + `src/game/shaders/characterMaterial.js`)**:
  - Every character is merged at load time into **at most 3 skinned draws**:
    1. `skinFace` (`aPart`: `0=face`, `1=skin`, `2=eye`) — per-character 512 face atlas, soft wrap diffuse + warm skin subsurface tint across the terminator (no cel banding), glossy cornea highlight
    2. `garment` (`aLayer`: `0..4`) — shared across all characters; samples the 5-layer Poly Haven fabric `DataArrayTexture` (`512` diffuse on Lite/Low `MeshLambertMaterial`, `1024` diffuse + screen-derivative TBN normal map on Medium+ `MeshStandardMaterial`), zero-mean detail modulation at `0.55`, UV-space Trader shemagh houndstooth/check, distance fade, and shared `injectAerialFog`
    3. `hairMetal` (`aPart`: `0=hair`, `1=metal`) — shared across all characters; per-part roughness/metalness on PBR and warm hair sheen / metal specular on Lite
  - Live quality tier changes automatically swap materials and textures via `useGame.subscribe`.

---

## 2. Geometry & Silhouette Upgrades (v3 → v4)

- **Soft naturally draped hijabs & tarhas (`aunt`, `grandma`, `grandma_zainab`)**: Replaced stiff conical shells with slimmer head wraps, face-framing front edges, and 4 soft outward diagonal wrap folds + gentle vertical gravity pleats and undulating hems over the shoulders — fully covering hair and neck with verified zero clipping across `idle`, `walk`, `talk`, `sit`, and `sit_talk` (`M5_poses.png`).
- **Closed shadowed sleeve cuffs & hijab returns**: All sleeves and hijab shoulder drapes turn inward cleanly with darkened interior depth so open hems never reveal backface-culled sky from below or side angles.
- **Readable cloth folds**: Waist gathers, subtle elbow compression creases, deeper pleated galabiya hems, and soft rounded drapery ripples on hijabs and robes.
- **Expressive storybook faces**: Higher-resolution `26×21` head mesh, preserved large glossy 3D eyes with multi-layer radial iris fibres and 3 catchlights, gently sculpted rounded nose tip & subtle nostril wings (`92%` nose normal preservation), warm nose/nostril shading, soft rosy cheek blush, and warmer sculpted lips.
- **Per-character cast**:
  - **Boy (`player`, 1.28 m)**: Warm ivory `ph_cotton` galabiya with teal `ph_hessian` placket/cuffs, warm ochre sash, loose sirwal trousers, smooth layered wavy brown hair with side-swept fringe, stitched `ph_leather` satchel with brass `metal` buckles and brown sandals.
  - **Grandpa Salim (`farmer`, 1.72 m)**: Terracotta-brown `ph_cotton` galabiya, olive `ph_wool` vest with brass buttons, striped ivory/ochre/terracotta `ph_hessian` shoulder scarf, crisp layered white `ph_linen` turban, full soft silver-white beard, wooden staff with leather grip.
  - **Grandma Zainab (`grandma_zainab`, 1.62 m standing / seated on 0.45 m mastaba)**: Deep midnight-plum `#30293A` `ph_cotton` abaya and `#25202E` `ph_linen` tarha with warm golden `ph_hessian` edging and natural draped folds; seated mastaba `sit` & `sit_talk` poses with skirt draped smoothly over knees and feet resting naturally on the ground.
  - **Grandma Amina (`grandma`, 1.60 m)**: Deep village-green `ph_cotton` dress with cream `ph_hessian` cuffs, rich cobalt `ph_linen` hijab with soft shoulder folds, and forward-cleared golden `metal` wire glasses.
  - **Trader (`trader`, 1.78 m)**: Royal indigo `ph_cotton` thobe, rich espresso `ph_wool` bisht with gold `ph_hessian` trim, crisp 2.6 cm red-and-white checkered `ph_linen` shemagh (`#B23029` on cream) with red border band clearing the bisht shoulders, black `ph_wool` double-coil agal with gold `metal` accents, neat dark trimmed beard.
  - **Sheikh (`sheikh`, 1.75 m)**: Soft ivory `ph_linen` under-thobe, sage-green `ph_wool` kaftan with cream `ph_hessian` front/collar trim, crimson `ph_wool` tarboush wrapped in a layered white `ph_linen` Azhari imama, neat silver-white beard.
  - **Aunt (`aunt`, 1.64 m)**: Warm ochre `ph_cotton` dress, terracotta-rose `ph_linen` hijab with soft asymmetric shoulder folds, turquoise `ph_hessian` waist sash with knotted tails.

---

## 3. Export & Budget Summary

All 7 GLBs are exported with Draco compression level 6, zero `.blend` files saved, zero outlines, 22 bones (`head`, `lid_l`, `lid_r`, `mouth` preserved), and 1 embedded 512 PNG face atlas:

| Character | Height (m) | Tris (≤ 9,000) | GLB KB (≤ 280) | Bones | Clips | Materials |
|---|---:|---:|---:|---:|---|---|
| `player` | 1.28 | 8,826 | 215.5 | 22 | `idle, walk, run, talk` | `face_player, eye, hair, skin, ph_cotton, ph_linen, ph_hessian, ph_leather, metal` |
| `farmer` | 1.72 | 7,946 | 188.3 | 22 | `idle, walk, talk` | `face_farmer, eye, hair, skin, ph_cotton, ph_linen, ph_wool, ph_hessian, ph_leather, metal` |
| `grandma_zainab` | 1.62 | 7,870 | 188.4 | 22 | `sit, sit_talk, idle` | `face_grandma_zainab, eye, hair, skin, ph_cotton, ph_linen, ph_hessian, ph_leather` |
| `grandma` | 1.60 | 7,782 | 187.8 | 22 | `idle, walk, talk` | `face_grandma, eye, hair, skin, ph_cotton, ph_linen, ph_hessian, ph_leather, metal` |
| `trader` | 1.78 | 8,804 | 199.1 | 22 | `idle, walk, talk` | `face_trader, eye, hair, skin, ph_cotton, ph_linen, ph_wool, ph_hessian, ph_leather, metal` |
| `sheikh` | 1.75 | 8,626 | 201.5 | 22 | `idle, walk, talk` | `face_sheikh, eye, hair, skin, ph_cotton, ph_linen, ph_wool, ph_hessian, ph_leather` |
| `aunt` | 1.64 | 7,550 | 188.9 | 22 | `idle, walk, talk` | `face_aunt, eye, hair, skin, ph_cotton, ph_linen, ph_hessian, ph_leather` |

- **Total character GLB size**: 1,369.5 KB (~1.34 MB across all 7 rigs).
- **Build precache `coreBytes`**: `10,152,643` bytes (~9.68 MB, well within the 11.4 MB budget).
- **In-game runtime verification (Headless Chromium + SwiftShader, 0 page/console errors)**:
  - **Per-character skinned draws**: `3` (`min = 3`, `max = 3`, `outlines = 0`, `uTexOn = 1` across all loaded rigs — 29 on Lite/Medium, 31 on High).
  - **Live tier swap (`high → lite → high`)**: All 31 loaded rigs swap cleanly between `MeshLambertMaterial` (512 px 5-layer `DataArrayTexture`, `uTexOn = 1` on 31/31) and `MeshStandardMaterial` (1024 px 5-layer diffuse + normal `DataArrayTexture`s, `uTexOn = 1` on 31/31) with 0 errors.
  - **Draw calls (whole frame) & main-pass triangles across `home / street / river / oasis`**:
    - **Lite** (≤ 140 / ≤ 180k): `67 / 84 / 49 / 46` calls, `154.5k / 156.2k / 118.7k / 111.5k` tris.
    - **Medium** (≤ 220 / ≤ 350k): `129 / 159 / 104 / 104` whole calls (`99 / 129 / 74 / 74` main calls), `317.3k / 329.2k / 212.3k / 276.5k` main tris.
    - **High** (≤ 320 / ≤ 700k): `229 / 247 / 221 / 175` whole calls (`110 / 166 / 98 / 81` main calls), `480.2k / 538.2k / 424.7k / 451.1k` main tris.
  - **`__game.balance({ verify: true })`**: 22/22 stories `reached: true`, `minCoins = 22` (≥ 20), `notWalkable = 0`, `unreachable = 0` on Lite, Medium, and High.
- **Preview sheets**: `blender/v4/previews/M5_lineup.png`, `M5_<key>_turn.png`, `M5_<key>_face.png`, `M5_poses.png`, and in-game `M5_{lite,high}_{home,street,river,oasis}.png`.
