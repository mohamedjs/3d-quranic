// Dual-path Poly Haven ground splat terrain shader:
//  - Lite / Low (`shading: 'toon'`): painterly 3-band toon + 4-layer diffuse DataArrayTexture
//    (512, max 4 array fetches/px, no normal maps, no triplanar) + per-pixel RGBA terrain map.
//  - Medium / High / Ultra (`shading: 'pbr'`): MeshStandardMaterial + PMREM IBL + 4-layer
//    diffuse/normal/ARM DataArrayTextures (1024 Med/High, 2048 Ultra) + XZ world-space normal
//    mapping + ARM roughness/AO + wet pebble bank gloss + triplanar sand on steep slopes (High+).
// Layers: 0 brown_mud_02 (3.5 m), 1 brown_mud_dry (2.5 m), 2 coast_sand_01 (4 m), 3 clean_pebbles (2 m).
import * as THREE from 'three';
import { toonGradient, RIM } from './toon.js';
import { AERIAL, injectAerialFog } from './stylizedPbr.js';
import { FIELD_COLORS, SIZE, HALF, WATER_Y, OASIS } from '../terrain/heightfield.js';
import { getTerrainMapTexture } from '../terrain/terrainGeometry.js';

export const TERRAIN_LAYERS = ['brown_mud_02', 'brown_mud_dry', 'coast_sand_01', 'clean_pebbles'];

const v3 = c => `vec3(${c.r.toFixed(4)}, ${c.g.toFixed(4)}, ${c.b.toFixed(4)})`;
const SOIL = new THREE.Color(0x6E4E33);

let phDiff, phNor, phArm;
function makePlaceholder(r, g, b, srgb) {
  const data = new Uint8Array(4 * 4);
  for (let i = 0; i < 4; i++) { data[i * 4] = r; data[i * 4 + 1] = g; data[i * 4 + 2] = b; data[i * 4 + 3] = 255; }
  const t = new THREE.DataArrayTexture(data, 1, 1, 4);
  t.format = THREE.RGBAFormat;
  t.type = THREE.UnsignedByteType;
  t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.minFilter = t.magFilter = THREE.LinearFilter;
  t.generateMipmaps = false;
  t.needsUpdate = true;
  return t;
}
const placeholderDiff = () => (phDiff ??= makePlaceholder(128, 128, 128, true));
const placeholderNor  = () => (phNor  ??= makePlaceholder(128, 128, 255, false));
const placeholderArm  = () => (phArm  ??= makePlaceholder(255, 230, 0, false));

const DEFAULT_AVGS = [
  new THREE.Vector3(0.08, 0.06, 0.04),
  new THREE.Vector3(0.19, 0.12, 0.06),
  new THREE.Vector3(0.22, 0.17, 0.11),
  new THREE.Vector3(0.30, 0.25, 0.21),
];

export function setTerrainTextures(mat, texSet) {
  const u = mat?.userData?.terrainUniforms;
  if (!u) return;
  if (!texSet?.diff) {
    u.uTexOn.value = 0.0;
    u.uDiffArr.value = placeholderDiff();
    if (u.uNorArr) u.uNorArr.value = placeholderNor();
    if (u.uArmArr) u.uArmArr.value = placeholderArm();
    return;
  }
  u.uDiffArr.value = texSet.diff.texture;
  if (texSet.diff.averages) {
    for (let i = 0; i < 4; i++) {
      if (texSet.diff.averages[i]) u.uDiffAvg.value[i].copy(texSet.diff.averages[i]);
    }
  }
  if (u.uNorArr && texSet.nor) u.uNorArr.value = texSet.nor.texture;
  if (u.uArmArr && texSet.arm) {
    u.uArmArr.value = texSet.arm.texture;
    if (texSet.arm.averages && u.uArmAO) {
      for (let i = 0; i < 4; i++) u.uArmAO.value[i] = Math.max(texSet.arm.averages[i]?.x ?? 1, 0.35);
    }
  }
  u.uTexOn.value = (!u.uNorArr || (texSet.nor && texSet.arm)) ? 1.0 : 0.0;
}

export function createTerrainMaterial({ shading = 'toon', triplanar = false } = {}) {
  const pbr = shading === 'pbr';
  const useTri = pbr && !!triplanar;
  const mat = pbr
    ? new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.96, metalness: 0.0, envMapIntensity: 0.36 })
    : new THREE.MeshToonMaterial({ vertexColors: true, gradientMap: toonGradient() });
  mat.name = pbr ? (useTri ? 'pbrTerrainTri' : 'pbrTerrain') : 'toonTerrain';
  mat.customProgramCacheKey = () => (pbr ? (useTri ? 'pbrTerrain_v4_tri' : 'pbrTerrain_v4') : 'toonTerrain_v4');

  const terrainUniforms = {
    uTexOn:   { value: 0.0 },
    uDiffArr: { value: placeholderDiff() },
    uDiffAvg: { value: DEFAULT_AVGS.map(v => v.clone()) },
    ...(pbr ? {
      uNorArr: { value: placeholderNor() },
      uArmArr: { value: placeholderArm() },
      uArmAO:  { value: [0.79, 0.59, 0.94, 0.72] },
    } : {}),
  };
  mat.userData.terrainUniforms = terrainUniforms;

  mat.onBeforeCompile = sh => {
    injectAerialFog(sh);
    Object.assign(sh.uniforms, terrainUniforms);
    sh.uniforms.uRimColor = pbr ? AERIAL.uRimColor : RIM;
    sh.uniforms.uShadowTint = AERIAL.uShadowTint;
    sh.uniforms.uTerrainMap = { value: getTerrainMapTexture() };

    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>
        attribute vec2 toonMask;
        varying vec2 vMask;
        varying vec3 vWPos;
        varying vec3 vWNorm;`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        vMask = toonMask;
        vWPos = (modelMatrix * vec4(position, 1.)).xyz;
        vWNorm = normalize(mat3(modelMatrix) * objectNormal);`);

    const [c0, c1, c2, c3] = FIELD_COLORS.crops;
    const pbrDecls = pbr ? `
        float tAo = 1.0;
        float tRough = 0.96;
        vec3 tWorldNorm = vec3(0.0, 1.0, 0.0);
        float tHasNorm = 0.0;` : '';

    const pbrSplatCode = pbr ? /* glsl */`
            float normFade = 1.0 - smoothstep(16.0, 58.0, camDist);
            float macroMix = smoothstep(14.0, 44.0, camDist) * 0.42;
            mat2 rotM = mat2(0.80, -0.60, 0.60, 0.80);

            vec3 tex0 = uDiffAvg[0], tex1 = uDiffAvg[1], tex2 = uDiffAvg[2], tex3 = uDiffAvg[3];
            vec3 arm0 = vec3(uArmAO[0], 0.95, 0.0), arm1 = vec3(uArmAO[1], 0.55, 0.0);
            vec3 arm2 = vec3(uArmAO[2], 0.96, 0.0), arm3 = vec3(uArmAO[3], 0.77, 0.0);
            vec2 tsXY = vec2(0.0);
            ${useTri ? 'vec3 triSandN = wN; float triBlend = 0.0;' : ''}

            if (w0 > 0.005) {
              vec2 uv0 = wp / 3.5;
              tex0 = texture(uDiffArr, vec3(uv0, 0.0)).rgb;
              if (macroMix > 0.01) tex0 = mix(tex0, texture(uDiffArr, vec3(rotM * (uv0 * 0.31) + vec2(1.7, 3.1), 0.0)).rgb, macroMix);
              arm0 = texture(uArmArr, vec3(uv0, 0.0)).rgb;
              if (normFade > 0.01) {
                vec2 n0 = texture(uNorArr, vec3(uv0, 0.0)).xy * 2.0 - 1.0;
                tsXY += n0 * (mix(0.85, 0.48, max(greenness, fieldBlend * 0.85)) * normFade * w0);
              }
            }
            if (w1 > 0.005) {
              vec2 uv1 = wp / 2.5;
              tex1 = texture(uDiffArr, vec3(uv1, 1.0)).rgb;
              if (macroMix > 0.01) tex1 = mix(tex1, texture(uDiffArr, vec3(rotM * (uv1 * 0.31) + vec2(4.2, 1.3), 1.0)).rgb, macroMix);
              arm1 = texture(uArmArr, vec3(uv1, 1.0)).rgb;
              if (normFade > 0.01) {
                vec2 n1 = texture(uNorArr, vec3(uv1, 1.0)).xy * 2.0 - 1.0;
                tsXY += n1 * (0.90 * normFade * w1);
              }
            }
            if (w2 > 0.005) {
              vec2 uv2 = wp / 4.0;
              tex2 = texture(uDiffArr, vec3(uv2, 2.0)).rgb;
              if (macroMix > 0.01) tex2 = mix(tex2, texture(uDiffArr, vec3(rotM * (uv2 * 0.31) + vec2(2.6, 5.4), 2.0)).rgb, macroMix);
              arm2 = texture(uArmArr, vec3(uv2, 2.0)).rgb;
              vec3 n2Raw = normFade > 0.01 ? (texture(uNorArr, vec3(uv2, 2.0)).xyz * 2.0 - 1.0) : vec3(0.0, 0.0, 1.0);
              ${useTri ? `
              if (steep > 0.08) {
                vec3 tw = pow(abs(wN), vec3(4.0));
                tw /= max(tw.x + tw.y + tw.z, 1e-5);
                vec2 uvX = vec2(vWPos.z, -vWPos.y) / 4.0;
                vec2 uvZ = vec2(vWPos.x, -vWPos.y) / 4.0;
                vec3 dX = texture(uDiffArr, vec3(uvX, 2.0)).rgb;
                vec3 dZ = texture(uDiffArr, vec3(uvZ, 2.0)).rgb;
                tex2 = tex2 * tw.y + dX * tw.x + dZ * tw.z;
                vec3 aX = texture(uArmArr, vec3(uvX, 2.0)).rgb;
                vec3 aZ = texture(uArmArr, vec3(uvZ, 2.0)).rgb;
                arm2 = arm2 * tw.y + aX * tw.x + aZ * tw.z;
                if (normFade > 0.01) {
                  float sTri = 0.80 * normFade;
                  vec3 nXts = texture(uNorArr, vec3(uvX, 2.0)).xyz * 2.0 - 1.0;
                  vec3 nZts = texture(uNorArr, vec3(uvZ, 2.0)).xyz * 2.0 - 1.0;
                  vec3 nY = vec3(n2Raw.x * sTri + wN.x, abs(n2Raw.z) * wN.y, -n2Raw.y * sTri + wN.z);
                  vec3 nX = vec3(abs(nXts.z) * wN.x, nXts.y * sTri + wN.y, nXts.x * sTri + wN.z);
                  vec3 nZ = vec3(nZts.x * sTri + wN.x, nZts.y * sTri + wN.y, abs(nZts.z) * wN.z);
                  triSandN = normalize(nX * tw.x + nY * tw.y + nZ * tw.z);
                  triBlend = w2 * smoothstep(0.08, 0.24, steep);
                }
              }` : ''}
              if (normFade > 0.01) tsXY += n2Raw.xy * (0.78 * normFade * w2);
            }
            if (w3 > 0.005) {
              vec2 uv3 = wp / 2.0;
              tex3 = texture(uDiffArr, vec3(uv3, 3.0)).rgb;
              if (macroMix > 0.01) tex3 = mix(tex3, texture(uDiffArr, vec3(rotM * (uv3 * 0.31) + vec2(6.1, 2.2), 3.0)).rgb, macroMix);
              arm3 = texture(uArmArr, vec3(uv3, 3.0)).rgb;
              if (normFade > 0.01) {
                vec2 n3 = texture(uNorArr, vec3(uv3, 3.0)).xy * 2.0 - 1.0;
                tsXY += n3 * (1.05 * normFade * w3);
              }
            }

            // Normalized micro-AO (crevice depth without overall dimming) + physical dry/wet roughness
            float ao0 = clamp(arm0.r / uArmAO[0], 0.50, 1.15);
            float ao1 = clamp(arm1.r / uArmAO[1], 0.50, 1.15);
            float ao2 = clamp(arm2.r / uArmAO[2], 0.50, 1.15);
            float ao3 = clamp(arm3.r / uArmAO[3], 0.50, 1.15);
            tAo = mix(1.0, ao0 * w0 + ao1 * w1 + ao2 * w2 + ao3 * w3, 0.55 * normFade);

            float r0 = mix(0.84, 0.98, arm0.g);
            float r1 = mix(0.80, 0.98, arm1.g);
            float r2 = mix(0.84, 0.99, arm2.g);
            float r3 = mix(0.68, 0.92, arm3.g);
            float baseRough = r0 * w0 + r1 * w1 + r2 * w2 + r3 * w3;
            tRough = mix(baseRough, mix(0.14, 0.34, arm3.g), tWet * 0.92);

            if (normFade > 0.01) {
              vec3 wT = normalize(vec3(wN.y, -wN.x, 0.0));
              vec3 wB = cross(wN, wT);
              vec3 wOut = normalize(wT * tsXY.x + wB * tsXY.y + wN);
              ${useTri ? 'if (triBlend > 0.01) wOut = normalize(mix(wOut, triSandN, triBlend));' : ''}
              tWorldNorm = wOut;
              tHasNorm = 1.0;
            }` : /* glsl */`
            vec3 tex0 = uDiffAvg[0], tex1 = uDiffAvg[1], tex2 = uDiffAvg[2], tex3 = uDiffAvg[3];
            if (w0 > 0.005) tex0 = texture(uDiffArr, vec3(wp / 3.5, 0.0)).rgb;
            if (w1 > 0.005) tex1 = texture(uDiffArr, vec3(wp / 2.5, 1.0)).rgb;
            if (w2 > 0.005) tex2 = texture(uDiffArr, vec3(wp / 4.0, 2.0)).rgb;
            if (w3 > 0.005) tex3 = texture(uDiffArr, vec3(wp / 2.0, 3.0)).rgb;`;

    const terrainColorCode = /* glsl */`
        float tWet = 0.0;
        float tPath = 0.0;
        float tDesert = 0.0;
        float tField = 0.0;${pbrDecls}
        {
          vec2 wp = vWPos.xz;
          vec3 wN = normalize(vWNorm);
          vec4 tm = texture2D(uTerrainMap, (wp + ${HALF.toFixed(1)}) / ${SIZE.toFixed(1)});
          float pd = tm.r * 8.0;
          float wd = tm.g * 8.0;
          float fm = tm.b;
          tDesert = tm.a;
          tField = fm;

          // Broad painterly brush patches so wide meadows and desert never read flat
          float pch = tn(wp * 0.045) * 0.60 + tn(wp * 0.16) * 0.40;
          float micro = tn(wp * 0.85);
          diffuseColor.rgb *= mix(0.92, 1.07, smoothstep(0.28, 0.72, pch));
          diffuseColor.rgb *= 0.97 + 0.06 * micro;

          // Desert wind-blown sand ripples and warm ochre sheen
          if (tDesert > 0.02) {
            float rip = sin(wp.x * 1.1 + wp.y * 0.42 + tn(wp * 0.18) * 3.5);
            vec3 dCol = mix(${v3(FIELD_COLORS.desert2)}, ${v3(FIELD_COLORS.desert)}, 0.55 + 0.35 * rip * 0.5 + 0.25 * pch);
            diffuseColor.rgb = mix(diffuseColor.rgb, dCol, tDesert * 0.78);
          }

          // Subtle limestone strata on elevated hill slopes
          float steep = 1.0 - clamp(wN.y, 0.0, 1.0);
          if (vWPos.y > 3.5 && steep > 0.12) {
            float strata = 0.5 + 0.5 * sin(vWPos.y * 1.65 + tn(wp * 0.08) * 3.2);
            vec3 rCol = mix(${v3(FIELD_COLORS.rockDark)}, diffuseColor.rgb * 1.08, strata);
            diffuseColor.rgb = mix(diffuseColor.rgb, rCol, smoothstep(0.12, 0.42, steep) * smoothstep(3.5, 9.0, vWPos.y) * 0.65);
          }

          // Per-pixel crisp farmland plots (no sawtooth vertex borders)
          float wob = (tn(wp * 1.6) - 0.5) * 0.24;
          float fieldBlend = smoothstep(0.32, 0.68, fm + wob * 0.35);
          if (fieldBlend > 0.01) {
            vec2 q = wp + 1000.0;
            vec2 e = mod(q, vec2(15.0, 10.0));
            vec3 fc;
            if (e.x < 0.9 || e.y < 0.7) fc = ${v3(FIELD_COLORS.bund)} * (0.94 + 0.12 * micro);
            else {
              int t = int(floor(plotHash(int(floor(q.x / 15.0)) + 11, int(floor(q.y / 10.0)) + 7) * 4.0));
              fc = t == 0 ? ${v3(c0)} : t == 1 ? ${v3(c1)} : t == 2 ? ${v3(c2)} : ${v3(c3)};
              float rows = fract(wp.y / 1.2), aa = min(fwidth(wp.y / 1.2) * 1.5, 0.5);
              float stripe = smoothstep(0.48 - aa, 0.48 + aa, rows);
              float fade = 1.0 - smoothstep(0.15, 0.45, fwidth(wp.y / 1.2));
              vec3 between = t >= 2 ? ${v3(SOIL)} : fc * 0.84;
              fc = mix(fc, mix(fc, between, stripe), fade * (t >= 2 ? 0.78 : 0.52));
              fc *= 0.94 + 0.11 * plotHash(int(floor(q.x / 15.0)), int(floor(q.y / 10.0)));
            }
            diffuseColor.rgb = mix(diffuseColor.rgb, fc, fieldBlend);
          }

          // Per-pixel wet banks & mossy Nile verge (kept tight to the waterline so roads stay clean)
          float bankNear = 1.0 - smoothstep(0.08, 0.80, wd + wob * 0.45);
          float bankLow = 1.0 - smoothstep(${(WATER_Y + 0.20).toFixed(2)}, ${(WATER_Y + 0.92).toFixed(2)}, vWPos.y);
          float mossBand = smoothstep(0.18, 0.65, wd) * (1.0 - smoothstep(0.65, 1.45, wd)) * (1.0 - tDesert) * (1.0 - fieldBlend);
          diffuseColor.rgb = mix(diffuseColor.rgb, ${v3(FIELD_COLORS.moss)}, mossBand * 0.30);
          float damp = bankNear * bankLow;
          diffuseColor.rgb = mix(diffuseColor.rgb, ${v3(FIELD_COLORS.bank)} * (0.92 + 0.14 * micro), damp * 0.85);
          float mud = clamp(1.0 - smoothstep(${(WATER_Y - 0.05).toFixed(2)}, ${(WATER_Y + 0.36).toFixed(2)}, vWPos.y), 0.0, 1.0);
          diffuseColor.rgb = mix(diffuseColor.rgb, ${v3(FIELD_COLORS.mud)}, mud * 0.90);
          tWet = clamp(max(damp * 0.72, mud), 0.0, 1.0);

          // Per-pixel crisp dirt roads: soft dusty shoulder + warm packed clay + sunlit track center
          float shoulder = 1.0 - smoothstep(1.55, 2.55, pd + wob * 1.1);
          float road = 1.0 - smoothstep(1.22, 1.72, pd + wob * 0.65);
          float centerWear = 1.0 - smoothstep(0.15, 0.72, pd);
          vec3 roadCol = mix(${v3(FIELD_COLORS.pathEdge)}, ${v3(FIELD_COLORS.path)}, smoothstep(0.2, 0.8, road));
          roadCol *= 0.96 + 0.07 * micro + 0.03 * centerWear;
          diffuseColor.rgb = mix(diffuseColor.rgb, ${v3(FIELD_COLORS.pathEdge)} * (0.96 + 0.08 * micro), shoulder * 0.52 * (1.0 - tWet * 0.6));
          diffuseColor.rgb = mix(diffuseColor.rgb, roadCol, road * (1.0 - mud * 0.5));
          tPath = road;

          // Poly Haven 4-layer material splat (palette-preserving detail + warm-graded road/pebble blend)
          if (uTexOn > 0.5) {
            float camDist = length(vWPos - cameraPosition);
            float detDist = mix(1.0, 0.30, smoothstep(18.0, 62.0, camDist));
            float bNoise = (tn(wp * 0.55) - 0.5) * 0.22 + (tn(wp * 1.45 + 7.3) - 0.5) * 0.12;

            float dOasis = length(wp - vec2(${OASIS.x.toFixed(1)}, ${OASIS.z.toFixed(1)}));
            float oasisShore = (1.0 - smoothstep(${(OASIS.r + 1.0).toFixed(1)}, ${(OASIS.r + 12.0).toFixed(1)}, dOasis + bNoise * 8.0))
                             * (1.0 - smoothstep(0.5, 5.5, wd + bNoise * 2.0));
            // Subtle warm sandy beach tint right along the oasis pond waterline (surrounding meadow stays green)
            float oasisBeach = oasisShore * (1.0 - smoothstep(0.35, 2.50, wd + bNoise * 1.2)) * (1.0 - road * 0.85);
            diffuseColor.rgb = mix(diffuseColor.rgb, ${v3(FIELD_COLORS.desert)} * 0.94, oasisBeach * 0.55);

            vec3 painterly = diffuseColor.rgb;
            float greenness = smoothstep(0.0, 0.12, painterly.g - painterly.r * 0.85);

            float bankVerge = (1.0 - smoothstep(0.15, 2.20, wd + bNoise * 1.4))
                            * (1.0 - smoothstep(${(WATER_Y + 0.25).toFixed(2)}, ${(WATER_Y + 1.50).toFixed(2)}, vWPos.y));
            float wPebble = clamp(max(max(damp, mud), bankVerge * 0.82) * (1.0 - oasisShore * 0.78) * (1.0 - road * 0.85), 0.0, 1.0);
            float wPathRaw = clamp(max(road, shoulder * 0.72) * (1.0 - mud * 0.5), 0.0, 1.0);
            float slopeSand = smoothstep(0.09, 0.28, steep + bNoise * 0.08) * (1.0 - wPebble) * smoothstep(1.3, 4.0, vWPos.y);
            float wSandRaw = clamp(max(max(smoothstep(0.05, 0.85, tDesert + bNoise * 0.25), oasisShore), slopeSand), 0.0, 1.0);

            float rem = 1.0;
            float w3 = wPebble;
            rem *= (1.0 - w3);
            float w1 = wPathRaw * rem;
            rem *= (1.0 - wPathRaw);
            float w2 = wSandRaw * rem;
            float w0 = max(0.0, 1.0 - w3 - w1 - w2);

            ${pbrSplatCode}

            vec3 det0 = clamp(tex0 / uDiffAvg[0], vec3(0.42), vec3(1.68));
            vec3 det1 = clamp(tex1 / uDiffAvg[1], vec3(0.42), vec3(1.68));
            vec3 det2 = clamp(tex2 / uDiffAvg[2], vec3(0.42), vec3(1.68));
            vec3 det3 = clamp(tex3 / uDiffAvg[3], vec3(0.38), vec3(1.75));

            float s0 = mix(0.56, 0.38, max(greenness, fieldBlend * 0.85)) * detDist;
            vec3 col0 = painterly * mix(vec3(1.0), det0, s0);
            vec3 col1 = painterly * mix(vec3(1.0), det1, 0.70 * detDist);
            vec3 col2 = painterly * mix(vec3(1.0), det2, 0.74 * detDist);
            vec3 col3 = painterly * mix(vec3(1.0), det3, 0.85 * detDist);

            // Road core: mix 42% toward warm-graded real brown_mud_dry colour
            if (road > 0.01 && w1 > 0.005) {
              float avgL1 = max(dot(uDiffAvg[1], vec3(0.2126, 0.7152, 0.0722)), 0.01);
              vec3 pathRef = mix(${v3(FIELD_COLORS.pathEdge)}, ${v3(FIELD_COLORS.path)}, smoothstep(0.2, 0.8, road));
              float refL1 = dot(pathRef, vec3(0.2126, 0.7152, 0.0722));
              vec3 graded1 = mix(tex1 * (refL1 / avgL1), pathRef * det1, 0.50);
              col1 = mix(col1, graded1, 0.42 * road * mix(1.0, 0.55, smoothstep(22.0, 65.0, camDist)));
            }

            // Pebble bank: mix 48% toward warm-graded real clean_pebbles colour
            if (w3 > 0.005) {
              float avgL3 = max(dot(uDiffAvg[3], vec3(0.2126, 0.7152, 0.0722)), 0.01);
              vec3 bankRef = mix(${v3(FIELD_COLORS.bank)} * 1.75, ${v3(FIELD_COLORS.mud)} * 1.25, mud);
              float refL3 = dot(bankRef, vec3(0.2126, 0.7152, 0.0722));
              vec3 graded3 = mix(tex3 * (refL3 / avgL3), bankRef * det3, 0.35);
              col3 = mix(col3, graded3, 0.48 * mix(1.0, 0.60, smoothstep(22.0, 65.0, camDist)));
            }

            diffuseColor.rgb = col0 * w0 + col1 * w1 + col2 * w2 + col3 * w3;
            diffuseColor.rgb *= mix(1.0, 0.86, tWet * (1.0 - road * 0.7));
          }
        }`;

    const pbrUniformDecls = pbr ? `
        uniform highp sampler2DArray uNorArr;
        uniform highp sampler2DArray uArmArr;
        uniform float uArmAO[4];` : '';

    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        uniform sampler2D uTerrainMap;
        uniform highp sampler2DArray uDiffArr;
        uniform vec3 uDiffAvg[4];
        uniform float uTexOn;${pbrUniformDecls}
        uniform vec3 uRimColor, uShadowTint;
        varying vec2 vMask;
        varying vec3 vWPos;
        varying vec3 vWNorm;
        float th(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
        float tn(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
          return mix(mix(th(i), th(i + vec2(1, 0)), f.x), mix(th(i + vec2(0, 1)), th(i + vec2(1, 1)), f.x), f.y); }
        float plotHash(int x, int y) {        // = hash() in heightfield.js
          uint h = uint(x) * 374761393u + uint(y) * 668265263u;
          h = (h ^ (h >> 13u)) * 1274126177u; h = h ^ (h >> 16u);
          return float(h) / 4294967295.;
        }`)
      .replace('#include <color_fragment>', `#include <color_fragment>\n${terrainColorCode}`);

    if (pbr) {
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>
          if (uTexOn > 0.5) {
            roughnessFactor = tRough;
          } else {
            roughnessFactor = mix(roughnessFactor, 0.99, clamp(tPath + tDesert, 0.0, 1.0));
            roughnessFactor = mix(roughnessFactor, 0.28, tWet * 0.90);
          }`)
        .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
          if (uTexOn > 0.5) {
            if (tHasNorm > 0.5) {
              normal = normalize((viewMatrix * vec4(tWorldNorm, 0.0)).xyz);
            }
          } else {
            // Procedural detail micro-normals fallback while Poly Haven arrays load
            float camDist = length(vWPos - cameraPosition);
            float detFade = 1.0 - smoothstep(18.0, 72.0, camDist);
            if (detFade > 0.01) {
              vec2 wp = vWPos.xz;
              float freq = mix(2.2, 3.8, tPath);
              float h0 = tn(wp * freq) * 0.65 + tn(wp * freq * 2.3 + 4.1) * 0.35;
              float hx = tn((wp + vec2(0.08, 0.0)) * freq) * 0.65 + tn((wp + vec2(0.08, 0.0)) * freq * 2.3 + 4.1) * 0.35;
              float hz = tn((wp + vec2(0.0, 0.08)) * freq) * 0.65 + tn((wp + vec2(0.0, 0.08)) * freq * 2.3 + 4.1) * 0.35;
              float ripSlope = tDesert * cos(wp.x * 1.1 + wp.y * 0.42 + tn(wp * 0.18) * 3.5) * 0.22;
              float furSlope = tField * cos(wp.y * 5.236) * 0.14;
              vec3 wBump = vec3((h0 - hx) * 1.6 + ripSlope, 0.0, (h0 - hz) * 1.6 + furSlope);
              float bumpAmp = mix(0.24, 0.14, tWet) * detFade;
              vec3 vBump = (viewMatrix * vec4(wBump, 0.0)).xyz;
              normal = normalize(normal + vBump * bumpAmp);
            }
          }`)
        .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
          {
            reflectedLight.indirectDiffuse *= tAo;
            // Matte dry earth/roads; glossy specular reflection on wet pebble banks
            float specMask = mix(0.10, 0.95, tWet);
            reflectedLight.indirectSpecular *= specMask;
            reflectedLight.directSpecular *= mix(0.14, 0.95, tWet);
            // Warm dusty bounce on shadowed roads instead of cool blue shift
            float dirLum = dot(reflectedLight.directDiffuse, vec3(0.3, 0.59, 0.11));
            float inShade = 1.0 - smoothstep(0.0, 0.32, dirLum);
            vec3 shadeCol = mix(uShadowTint * 0.05, vec3(0.86, 0.66, 0.40) * 0.09, tPath);
            reflectedLight.indirectDiffuse += diffuseColor.rgb * shadeCol * inShade;
            float rimF = 1.0 - clamp(dot(normalize(vViewPosition), normal), 0.0, 1.0);
            reflectedLight.directDiffuse += diffuseColor.rgb * uRimColor * smoothstep(0.70, 0.94, rimF) * (0.09 * (1.0 - 0.6 * tPath));
          }`);
    } else {
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
          {
            float rimF = 1.0 - clamp(dot(normalize(vViewPosition), normal), 0.0, 1.0);
            reflectedLight.directDiffuse += diffuseColor.rgb * uRimColor * smoothstep(0.68, 0.90, rimF) * 0.12;
          }`);
    }
  };
  return mat;
}
