// Shared v4 Poly Haven character material factory (3 skinned draws max per character:
// skin+face+eye, garments, hair+metal).
// - Lite / Low (`shading !== 'pbr'`): MeshLambertMaterial + 512px 5-layer diffuse DataArrayTexture
//   (no normal map, cheap wrap diffuse + warm skin SSS + view-space cornea/metal glint).
// - Medium / High / Ultra (`shading === 'pbr'`): MeshStandardMaterial + 1024px diffuse & normal
//   DataArrayTextures, screen-derivative TBN, scene.environment IBL (low envMapIntensity),
//   per-layer roughness/metalness, soft wrap diffuse + warm subsurface scatter on skin.
// Automatically swaps tier textures and materials on live quality changes via useGame.subscribe.
import * as THREE from 'three';
import { AERIAL, injectAerialFog } from './stylizedPbr.js';
import { RIM } from './toon.js';
import { wind } from './wind.js';
import { loadTextureArray } from '../world/loaders.js';
import { useGame } from '../systems/store.js';
import { PRESETS } from '../systems/quality.js';

export const FABRIC_LAYERS = [
  'ph_cotton',
  'ph_linen',
  'ph_wool',
  'ph_hessian',
  'ph_leather',
];

export const FABRIC_LAYER_INDEX = Object.fromEntries(FABRIC_LAYERS.map((n, i) => [n, i]));

const FABRIC_IDS = [
  'cotton_jersey',
  'rough_linen',
  'knitted_fleece',
  'hessian_230',
  'brown_leather',
];

const DEFAULT_AVGS = [
  new THREE.Vector3(0.5333, 0.4052, 0.3360),
  new THREE.Vector3(0.2830, 0.4104, 0.6144),
  new THREE.Vector3(0.0922, 0.0731, 0.0507),
  new THREE.Vector3(0.2757, 0.1986, 0.1084),
  new THREE.Vector3(0.0832, 0.0269, 0.0053),
];

let phDiff, phNor;
function makePlaceholder(r, g, b, srgb) {
  const n = FABRIC_IDS.length;
  const data = new Uint8Array(n * 4);
  for (let i = 0; i < n; i++) {
    data[i * 4] = r;
    data[i * 4 + 1] = g;
    data[i * 4 + 2] = b;
    data[i * 4 + 3] = 255;
  }
  const t = new THREE.DataArrayTexture(data, 1, 1, n);
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

const garmentMats = { toon: null, pbr: null };
const hairMetalMats = { toon: null, pbr: null };
const skinFaceCache = new WeakMap();
const trackedMeshes = new Set();

let activeSet = null;
let wantKey = null;
const warned = new Set();

function applyTexSet(mat, set) {
  const u = mat?.userData?.charUniforms;
  if (!u) return;
  const isPbr = !!u.uNorArr;
  if (!set?.diff || (isPbr && !set.nor)) {
    u.uTexOn.value = 0.0;
    u.uDiffArr.value = placeholderDiff();
    if (u.uNorArr) u.uNorArr.value = placeholderNor();
    return;
  }
  u.uDiffArr.value = set.diff.texture;
  for (let i = 0; i < FABRIC_IDS.length; i++) {
    if (set.diff.averages?.[i]) u.uDiffAvg.value[i].copy(set.diff.averages[i]);
  }
  if (isPbr) u.uNorArr.value = set.nor.texture;
  u.uTexOn.value = 1.0;
}

function disposeTexSet(set) {
  if (!set) return;
  set.diff?.texture?.dispose();
  set.nor?.texture?.dispose();
}

const layerUrls = (size, kind) => FABRIC_IDS.map(id => `./textures/v4/${size}/${id}_${kind}.webp`);

// Non-blocking fabric texture array load (512 diff on Lite/Low, 1024 diff+nor on Medium+).
export function ensureCharacterTextures(shading = 'toon') {
  const pbr = shading === 'pbr';
  const size = pbr ? 1024 : 512;
  const key = `${size}|${pbr ? 1 : 0}`;
  wantKey = key;
  if (activeSet?.key === key) {
    if (garmentMats.toon) applyTexSet(garmentMats.toon, !pbr ? activeSet : null);
    if (garmentMats.pbr) applyTexSet(garmentMats.pbr, pbr ? activeSet : null);
    return;
  }
  const aniso = pbr ? 4 : 1;
  const job = pbr
    ? Promise.all([
      loadTextureArray(layerUrls(size, 'diff'), { srgb: true, size, anisotropy: aniso }),
      loadTextureArray(layerUrls(size, 'nor'),  { srgb: false, size, anisotropy: aniso }),
    ]).then(([diff, nor]) => ({ key, diff, nor }))
    : loadTextureArray(layerUrls(size, 'diff'), { srgb: true, size, anisotropy: aniso })
      .then(diff => ({ key, diff, nor: null }));

  job.then(next => {
    if (wantKey !== key) {
      if (activeSet?.key !== key) disposeTexSet(next);
      return;
    }
    const prev = activeSet;
    activeSet = next;
    if (garmentMats.toon) applyTexSet(garmentMats.toon, !pbr ? next : null);
    if (garmentMats.pbr) applyTexSet(garmentMats.pbr, pbr ? next : null);
    if (prev && prev.key !== next.key) disposeTexSet(prev);
  }).catch(err => {
    if (!warned.has(key)) {
      warned.add(key);
      console.warn(`[char] v4 fabric textures (${size}) unavailable, keeping vertex colours:`, err?.message || err);
    }
  });
}

// ---- 1) Garments (ph_cotton, ph_linen, ph_wool, ph_hessian, ph_leather) ------------------------
function createGarmentMaterial(pbr) {
  const mat = pbr
    ? new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.88, metalness: 0.0, envMapIntensity: 0.22 })
    : new THREE.MeshLambertMaterial({ vertexColors: true, reflectivity: 0 });
  mat.name = pbr ? 'charGarmentPbr' : 'charGarmentLite';
  mat.customProgramCacheKey = () => (pbr ? 'charGarment_v4_pbr_r2' : 'charGarment_v4_lite_r2');

  const charUniforms = {
    uTexOn:   { value: 0.0 },
    uDiffArr: { value: placeholderDiff() },
    uDiffAvg: { value: DEFAULT_AVGS.map(v => v.clone()) },
    ...(pbr ? { uNorArr: { value: placeholderNor() } } : {}),
  };
  mat.userData.charUniforms = charUniforms;

  mat.onBeforeCompile = sh => {
    injectAerialFog(sh);
    Object.assign(sh.uniforms, charUniforms);
    sh.uniforms.uRimColor = pbr ? AERIAL.uRimColor : RIM;
    sh.uniforms.uShadowTint = AERIAL.uShadowTint;
    sh.uniforms.uSunDirV = wind.uSunDirV;

    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>
        attribute float aLayer;
        varying float vLayer;
        varying vec2 vCharUv;`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        vLayer = aLayer;
        vCharUv = uv;`);

    const pbrDecls = pbr ? '\nuniform highp sampler2DArray uNorArr;' : '';

    const colorCode = /* glsl */`
        int cLayer = clamp(int(floor(vLayer + 0.5)), 0, 4);
        bool isShemagh = (cLayer == 1 && vCharUv.x > 50.0);
        vec2 mUv = isShemagh ? vec2(vCharUv.x - 100.0, vCharUv.y) : vCharUv;
        vec2 cUv = mUv;
        float cCamDist = length(vAerialPos - cameraPosition);
        ${pbr ? 'float cRough = cLayer == 4 ? 0.50 : cLayer == 2 ? 0.90 : cLayer == 0 ? 0.85 : 0.88; float cNormFade = 1.0 - smoothstep(6.0, 22.0, cCamDist);' : ''}
        if (isShemagh) {
          // Classic small ~2.6 cm red-and-white Arabian shemagh square houndstooth/check (#B23029 on cream) + red border band
          float isBorder = smoothstep(0.14, 0.28, diffuseColor.r - diffuseColor.g);
          vec2 sg = mUv / 0.026;
          vec2 sci = floor(sg);
          vec2 sf = fract(sg);
          vec2 fw = max(fwidth(sg), vec2(0.015));
          float par = mod(sci.x + sci.y, 2.0);
          float bu = (1.0 - smoothstep(0.105 - fw.x, 0.105 + fw.x, abs(sf.x - 0.5)))
                   + (1.0 - smoothstep(0.044 - fw.x, 0.044 + fw.x, abs(sf.x - 0.25)))
                   + (1.0 - smoothstep(0.044 - fw.x, 0.044 + fw.x, abs(sf.x - 0.75)));
          float bv = (1.0 - smoothstep(0.105 - fw.y, 0.105 + fw.y, abs(sf.y - 0.5)))
                   + (1.0 - smoothstep(0.044 - fw.y, 0.044 + fw.y, abs(sf.y - 0.25)))
                   + (1.0 - smoothstep(0.044 - fw.y, 0.044 + fw.y, abs(sf.y - 0.75)));
          float lines = clamp(max(bu, bv), 0.0, 1.0);
          vec2 dc = abs(sf - 0.5);
          float fwm = max(fw.x, fw.y);
          float sqCheck = 1.0 - smoothstep(0.34 - fwm, 0.34 + fwm, max(dc.x, dc.y));
          float diam = 1.0 - smoothstep(0.44 - fwm, 0.44 + fwm, dc.x + dc.y);
          float evenBlock = (1.0 - step(0.5, par)) * max(sqCheck, diam);
          float patNear = max(lines, evenBlock);
          // Preserve crisp 2.6 cm red-and-white square check readability at game camera distance
          float patFar = mix(0.86, 0.18, step(0.5, par));
          float pat = mix(patNear, patFar, smoothstep(0.24, 0.58, fwm));
          float sAo = clamp(diffuseColor.r / 0.929, 0.22, 1.15);
          vec3 redCol = vec3(0.4452, 0.0296, 0.0222) * sAo;
          diffuseColor.rgb = mix(mix(diffuseColor.rgb, redCol, pat), diffuseColor.rgb, isBorder);
        }
        if (uTexOn > 0.5) {
          float tileM = cLayer == 0 ? 0.35 : cLayer == 1 ? 0.45 : cLayer == 2 ? 0.30 : cLayer == 3 ? 0.40 : 0.50;
          cUv = mUv / tileM;
          ${pbr
            ? 'vec3 tex = texture(uDiffArr, vec3(cUv, float(cLayer)), -1.0 * cNormFade).rgb;'
            : 'vec3 tex = texture(uDiffArr, vec3(cUv, float(cLayer))).rgb;'}
          vec3 avg = uDiffAvg[cLayer];
          float lumT = dot(tex, vec3(0.2126, 0.7152, 0.0722));
          float lumA = max(dot(avg, vec3(0.2126, 0.7152, 0.0722)), 0.01);
          // Zero-mean luminance detail preserves exact mean palette colour across all 5 fabric layers
          float dLum = lumT / lumA - 1.0;
          ${pbr
            ? 'float cGain = cLayer == 0 ? 5.8 : cLayer == 1 ? 2.45 : cLayer == 2 ? 1.95 : cLayer == 3 ? 1.05 : 1.40;'
            : 'float cGain = cLayer == 0 ? 3.0 : cLayer == 1 ? 2.80 : cLayer == 2 ? 1.60 : cLayer == 3 ? 1.00 : 1.35;'}
          float det = 1.0 + clamp(dLum * cGain, ${pbr ? '-0.42, 0.42' : '-0.36, 0.36'});
          ${pbr
            ? 'if (cLayer == 0) { float wNear = 1.0 - smoothstep(1.8, 5.2, cCamDist); det += sin(mUv.x * 380.0) * sin(mUv.y * 380.0) * 0.075 * wNear; }'
            : 'if (cLayer == 0) { float wNear = 1.0 - smoothstep(2.0, 5.5, cCamDist); det += sin(mUv.x * 260.0) * sin(mUv.y * 260.0) * 0.065 * wNear; }'}
          float detDist = mix(1.0, 0.55, smoothstep(8.0, 28.0, cCamDist));
          diffuseColor.rgb *= mix(1.0, det, 0.55 * detDist);
        }`;

    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        uniform highp sampler2DArray uDiffArr;
        uniform vec3 uDiffAvg[5];
        uniform float uTexOn;${pbrDecls}
        uniform vec3 uRimColor, uShadowTint, uSunDirV;
        varying float vLayer;
        varying vec2 vCharUv;`)
      .replace('#include <color_fragment>', `#include <color_fragment>\n${colorCode}`);

    if (pbr) {
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>
          roughnessFactor = cRough;`)
        .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
          if (uTexOn > 0.5 && cNormFade > 0.01) {
            vec3 q0 = dFdx(-vViewPosition);
            vec3 q1 = dFdy(-vViewPosition);
            vec2 st0 = dFdx(cUv);
            vec2 st1 = dFdy(cUv);
            vec3 q1p = cross(q1, normal);
            vec3 q0p = cross(normal, q0);
            vec3 cT = q1p * st0.x + q0p * st1.x;
            vec3 cB = q1p * st0.y + q0p * st1.y;
            float detN = max(dot(cT, cT), dot(cB, cB));
            if (detN > 1e-10) {
              float scN = inversesqrt(detN);
              mat3 cTbn = mat3(cT * scN, cB * scN, normal);
              vec3 mapN = texture(uNorArr, vec3(cUv, float(cLayer)), -1.0 * cNormFade).xyz * 2.0 - 1.0;
              float ns = (cLayer == 0 ? 5.60 : cLayer == 1 ? 3.40 : cLayer == 2 ? 3.10 : cLayer == 3 ? 1.30 : 1.45) * cNormFade;
              mapN.xy *= vec2(ns, -ns);
              if (cLayer == 0) {
                float wn = (1.0 - smoothstep(1.8, 5.2, cCamDist)) * 0.14;
                mapN.x += cos(mUv.x * 380.0) * sin(mUv.y * 380.0) * wn;
                mapN.y += sin(mUv.x * 380.0) * cos(mUv.y * 380.0) * wn;
              }
              normal = normalize(cTbn * mapN);
            }
          }`)
        .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
          {
            // Keep matte cloth free of white Fresnel specular wash while preserving full v3 palette luminance & saturation
            reflectedLight.indirectDiffuse *= 1.02;
            reflectedLight.directDiffuse *= 1.08;
            reflectedLight.indirectSpecular *= (cLayer == 4 ? 0.55 : 0.08);
            reflectedLight.directSpecular *= (cLayer == 4 ? 0.65 : 0.14);
            vec3 sDir = length(uSunDirV) > 0.001 ? normalize(uSunDirV) : vec3(0.4, 0.7, 0.5);
            float ndl = dot(normal, sDir);
            float wrapExtra = max(0.0, clamp((ndl + 0.35) / 1.35, 0.0, 1.0) - max(ndl, 0.0));
            reflectedLight.directDiffuse += diffuseColor.rgb * (wrapExtra * 0.16);
            float dirLum = dot(reflectedLight.directDiffuse, vec3(0.3, 0.59, 0.11));
            reflectedLight.indirectDiffuse += diffuseColor.rgb * uShadowTint * (1.0 - smoothstep(0.0, 0.30, dirLum)) * 0.04;
            float rimF = 1.0 - clamp(abs(dot(normalize(vViewPosition), normal)), 0.0, 1.0);
            reflectedLight.directDiffuse += diffuseColor.rgb * uRimColor * smoothstep(0.62, 0.90, rimF) * 0.14;
          }`);
    } else {
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
          {
            reflectedLight.indirectDiffuse *= 0.84;
            reflectedLight.directDiffuse *= 1.06;
            vec3 vDir = normalize(vViewPosition);
            if (cLayer == 4) {
              vec3 sDir = length(uSunDirV) > 0.001 ? normalize(uSunDirV) : vec3(0.4, 0.7, 0.5);
              float sp = pow(max(dot(normal, normalize(sDir + vDir)), 0.0), 22.0);
              reflectedLight.directDiffuse += vec3(1.0, 0.92, 0.78) * sp * 0.16;
            }
            float rimF = 1.0 - clamp(abs(dot(vDir, normal)), 0.0, 1.0);
            reflectedLight.directDiffuse += diffuseColor.rgb * uRimColor * smoothstep(0.62, 0.90, rimF) * 0.15;
          }`);
    }
  };
  return mat;
}

// ---- 2) Skin + Face + Eye (aPart: 0=face, 1=skin, 2=eye) ---------------------------------------
function createSkinFaceMaterial(faceMap, pbr) {
  const mat = pbr
    ? new THREE.MeshStandardMaterial({ map: faceMap, vertexColors: true, roughness: 0.55, metalness: 0.0, envMapIntensity: 0.28 })
    : new THREE.MeshLambertMaterial({ map: faceMap, vertexColors: true, reflectivity: 0 });
  mat.name = pbr ? 'charSkinFacePbr' : 'charSkinFaceLite';
  mat.customProgramCacheKey = () => (pbr ? 'charSkinFace_v4_pbr_r2' : 'charSkinFace_v4_lite_r2');

  mat.onBeforeCompile = sh => {
    injectAerialFog(sh);
    sh.uniforms.uRimColor = pbr ? AERIAL.uRimColor : RIM;
    sh.uniforms.uSunDirV = wind.uSunDirV;

    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>
        attribute float aPart;
        varying float vCharPart;`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        vCharPart = aPart;`);

    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        uniform vec3 uRimColor, uSunDirV;
        varying float vCharPart;`)
      .replace('#include <map_fragment>', `#ifdef USE_MAP
        if (vCharPart < 0.5 || vCharPart > 1.5) {
          vec4 sampledDiffuseColor = texture2D( map, vMapUv );
          diffuseColor *= sampledDiffuseColor;
        }
      #endif`);

    if (pbr) {
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>
          roughnessFactor = vCharPart > 1.5 ? 0.12 : 0.55;`)
        .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
          {
            vec3 vDir = normalize(vViewPosition);
            vec3 sDir = length(uSunDirV) > 0.001 ? normalize(uSunDirV) : vec3(0.4, 0.7, 0.5);
            if (vCharPart < 1.5) {
              // Soft wrap diffuse + warm subsurface tint across terminator & shadow side (no hard cel band)
              reflectedLight.indirectDiffuse *= 0.92;
              reflectedLight.directDiffuse *= 1.04;
              float ndl = dot(normal, sDir);
              float wrap = clamp((ndl + 0.44) / 1.44, 0.0, 1.0);
              float wrapExtra = max(0.0, wrap - max(ndl, 0.0));
              float shadowSide = 1.0 - smoothstep(-0.15, 0.35, ndl);
              vec3 sssTint = vec3(1.0, 0.45, 0.28);
              reflectedLight.directDiffuse += diffuseColor.rgb * sssTint * (wrapExtra * 0.32);
              reflectedLight.indirectDiffuse += diffuseColor.rgb * sssTint * (shadowSide * 0.09);
              reflectedLight.directSpecular *= 0.28;
              reflectedLight.indirectSpecular *= 0.18;
              float rimF = 1.0 - clamp(abs(dot(vDir, normal)), 0.0, 1.0);
              reflectedLight.directDiffuse += diffuseColor.rgb * uRimColor * smoothstep(0.60, 0.88, rimF) * 0.22;
            } else {
              // Glossy cornea specular + bright catchlight boost
              reflectedLight.directSpecular *= 1.25;
              reflectedLight.indirectSpecular *= 0.90;
            }
          }`);
    } else {
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
          {
            vec3 vDir = normalize(vViewPosition);
            vec3 sDir = length(uSunDirV) > 0.001 ? normalize(uSunDirV) : vec3(0.4, 0.7, 0.5);
            if (vCharPart < 1.5) {
              reflectedLight.indirectDiffuse *= 0.80;
              reflectedLight.directDiffuse *= 1.02;
              float ndl = dot(normal, sDir);
              float wrap = clamp((ndl + 0.44) / 1.44, 0.0, 1.0);
              float wrapExtra = max(0.0, wrap - max(ndl, 0.0));
              float shadowSide = 1.0 - smoothstep(-0.15, 0.35, ndl);
              vec3 sssTint = vec3(1.0, 0.45, 0.28);
              reflectedLight.directDiffuse += diffuseColor.rgb * sssTint * (wrapExtra * 0.30);
              reflectedLight.indirectDiffuse += diffuseColor.rgb * sssTint * (shadowSide * 0.09);
              float rimF = 1.0 - clamp(abs(dot(vDir, normal)), 0.0, 1.0);
              reflectedLight.directDiffuse += diffuseColor.rgb * uRimColor * smoothstep(0.60, 0.88, rimF) * 0.22;
            } else {
              reflectedLight.indirectDiffuse *= 0.82;
              float eyeSp = pow(max(dot(normal, normalize(sDir + vDir)), 0.0), 48.0);
              reflectedLight.directDiffuse += vec3(1.0, 0.98, 0.94) * eyeSp * 0.38;
            }
          }`);
    }
  };
  return mat;
}

// ---- 3) Hair + Metal (aPart: 0=hair/brows/lashes/mouth, 1=metal) -------------------------------
function createHairMetalMaterial(pbr) {
  const mat = pbr
    ? new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.60, metalness: 0.0, envMapIntensity: 0.38 })
    : new THREE.MeshLambertMaterial({ vertexColors: true, reflectivity: 0 });
  mat.name = pbr ? 'charHairMetalPbr' : 'charHairMetalLite';
  mat.customProgramCacheKey = () => (pbr ? 'charHairMetal_v4_pbr_r2' : 'charHairMetal_v4_lite_r2');

  mat.onBeforeCompile = sh => {
    injectAerialFog(sh);
    sh.uniforms.uRimColor = pbr ? AERIAL.uRimColor : RIM;
    sh.uniforms.uSunDirV = wind.uSunDirV;

    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>
        attribute float aPart;
        varying float vCharPart;`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        vCharPart = aPart;`);

    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        uniform vec3 uRimColor, uSunDirV;
        varying float vCharPart;`);

    if (pbr) {
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>
          roughnessFactor = vCharPart > 0.5 ? 0.30 : 0.60;`)
        .replace('#include <metalnessmap_fragment>', `#include <metalnessmap_fragment>
          metalnessFactor = vCharPart > 0.5 ? 1.0 : 0.0;`)
        .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
          {
            vec3 vDir = normalize(vViewPosition);
            if (vCharPart > 0.5) {
              reflectedLight.directSpecular *= 1.35;
              reflectedLight.indirectSpecular *= 1.55;
            } else {
              reflectedLight.indirectDiffuse *= 0.92;
              reflectedLight.directDiffuse *= 1.04;
              reflectedLight.directSpecular *= 0.42;
              reflectedLight.indirectSpecular *= 0.22;
              float rimF = 1.0 - clamp(abs(dot(vDir, normal)), 0.0, 1.0);
              reflectedLight.directDiffuse += diffuseColor.rgb * uRimColor * smoothstep(0.60, 0.88, rimF) * 0.18;
            }
          }`);
    } else {
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
          {
            vec3 vDir = normalize(vViewPosition);
            vec3 sDir = length(uSunDirV) > 0.001 ? normalize(uSunDirV) : vec3(0.4, 0.7, 0.5);
            vec3 hDir = normalize(sDir + vDir);
            if (vCharPart > 0.5) {
              reflectedLight.indirectDiffuse *= 0.85;
              float sp = pow(max(dot(normal, hDir), 0.0), 32.0);
              reflectedLight.directDiffuse += (diffuseColor.rgb * 0.45 + vec3(0.55)) * sp * 0.85;
              reflectedLight.indirectDiffuse += diffuseColor.rgb * 0.22;
            } else {
              reflectedLight.indirectDiffuse *= 0.78;
              reflectedLight.directDiffuse *= 1.04;
              float sheen = pow(max(dot(normal, hDir), 0.0), 14.0);
              reflectedLight.directDiffuse += diffuseColor.rgb * vec3(1.0, 0.94, 0.84) * sheen * 0.14;
              float rimF = 1.0 - clamp(abs(dot(vDir, normal)), 0.0, 1.0);
              reflectedLight.directDiffuse += diffuseColor.rgb * uRimColor * smoothstep(0.60, 0.88, rimF) * 0.18;
            }
          }`);
    }
  };
  return mat;
}

// ---- Public material getters & live tier synchronization ---------------------------------------
function currentShading() {
  return PRESETS[useGame.getState().quality]?.shading ?? 'toon';
}

export function getGarmentMaterial(shading = currentShading()) {
  const k = shading === 'pbr' ? 'pbr' : 'toon';
  if (!garmentMats.toon) {
    garmentMats.toon = createGarmentMaterial(false);
    garmentMats.pbr = createGarmentMaterial(true);
    const pair = { toon: garmentMats.toon, pbr: garmentMats.pbr };
    garmentMats.toon.userData.charPair = pair;
    garmentMats.pbr.userData.charPair = pair;
  }
  if (activeSet) {
    applyTexSet(garmentMats[k], activeSet.key === `${k === 'pbr' ? 1024 : 512}|${k === 'pbr' ? 1 : 0}` ? activeSet : null);
  }
  return garmentMats[k];
}

export function getSkinFaceMaterial(faceMap, shading = currentShading()) {
  const k = shading === 'pbr' ? 'pbr' : 'toon';
  if (faceMap && skinFaceCache.has(faceMap)) return skinFaceCache.get(faceMap)[k];
  const pair = {
    toon: createSkinFaceMaterial(faceMap, false),
    pbr: createSkinFaceMaterial(faceMap, true),
  };
  pair.toon.userData.charPair = pair;
  pair.pbr.userData.charPair = pair;
  if (faceMap) skinFaceCache.set(faceMap, pair);
  return pair[k];
}

export function getHairMetalMaterial(shading = currentShading()) {
  const k = shading === 'pbr' ? 'pbr' : 'toon';
  if (!hairMetalMats.toon) {
    hairMetalMats.toon = createHairMetalMaterial(false);
    hairMetalMats.pbr = createHairMetalMaterial(true);
    const pair = { toon: hairMetalMats.toon, pbr: hairMetalMats.pbr };
    hairMetalMats.toon.userData.charPair = pair;
    hairMetalMats.pbr.userData.charPair = pair;
  }
  return hairMetalMats[k];
}

export function registerCharacterMesh(mesh) {
  if (!mesh) return mesh;
  trackedMeshes.add(mesh);
  return mesh;
}

let lastShading = null;
function syncAllCharacters(shading) {
  const k = shading === 'pbr' ? 'pbr' : 'toon';
  if (trackedMeshes.size > 0) ensureCharacterTextures(k);
  const aniso = k === 'pbr' ? 4 : 1;
  for (const mesh of trackedMeshes) {
    const pair = mesh.material?.userData?.charPair;
    if (!pair) continue;
    const next = pair[k];
    if (next.map && next.map.anisotropy !== aniso) {
      next.map.anisotropy = aniso;
      next.map.needsUpdate = true;
    }
    if (mesh.material !== next) mesh.material = next;
  }
}

useGame.subscribe(state => {
  const next = PRESETS[state.quality]?.shading ?? 'toon';
  if (next !== lastShading) {
    lastShading = next;
    syncAllCharacters(next);
  }
});
