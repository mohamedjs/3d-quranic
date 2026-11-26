// Single shared Poly Haven building material factory (one draw call per building LOD).
// - Lite / Low (`shading: 'toon'`): MeshToonMaterial (3-band toon gradient) sampling a 512
//   7-layer diffuse DataArrayTexture (1 array fetch/px, no normals/ARM) + aerial fog + warm rim.
// - Medium / High / Ultra (`shading: 'pbr'`): MeshStandardMaterial sampling 1024 diffuse, normal
//   and ARM DataArrayTextures (High/Ultra stay at 1024 for memory), screen-derivative tangent
//   frame, normalized ARM micro-AO & roughness, low envMapIntensity + aerial fog + warm rim.
// Layer order (per-vertex `aLayer` 0..7):
//   0 ph_plaster (clay_plaster, 2.5 m), 1 ph_mudbrick (clay_block_wall, 2 m),
//   2 ph_blue (blue_plaster_weathered, 2.5 m), 3 ph_wood (weathered_brown_planks, 1.6 m),
//   4 ph_floor (clay_floor_001, 2 m), 5 ph_stone (sandstone_blocks_05, 2.4 m),
//   6 ph_cloth (hessian_230, 1.2 m), 7 ph_dark (openings: no texture, vertex colour).
import * as THREE from 'three';
import { toonGradient, RIM } from './toon.js';
import { AERIAL, injectAerialFog } from './stylizedPbr.js';
import { loadTextureArray } from '../world/loaders.js';

export const BUILDING_LAYERS = [
  'ph_plaster',
  'ph_mudbrick',
  'ph_blue',
  'ph_wood',
  'ph_floor',
  'ph_stone',
  'ph_cloth',
  'ph_dark',
];

export const BUILDING_LAYER_INDEX = Object.fromEntries(BUILDING_LAYERS.map((n, i) => [n, i]));

const TEX_IDS = [
  'clay_plaster',
  'clay_block_wall',
  'blue_plaster_weathered',
  'weathered_brown_planks',
  'clay_floor_001',
  'sandstone_blocks_05',
  'hessian_230',
];

const DEFAULT_AVGS = [
  new THREE.Vector3(0.170, 0.102, 0.046),
  new THREE.Vector3(0.226, 0.133, 0.062),
  new THREE.Vector3(0.243, 0.375, 0.351),
  new THREE.Vector3(0.116, 0.071, 0.040),
  new THREE.Vector3(0.195, 0.117, 0.047),
  new THREE.Vector3(0.428, 0.330, 0.230),
  new THREE.Vector3(0.263, 0.188, 0.100),
];

const DEFAULT_ARM_AO = [0.976, 0.815, 0.980, 0.950, 0.981, 0.861, 0.905];

let phDiff, phNor, phArm;
function makePlaceholder(r, g, b, srgb) {
  const n = TEX_IDS.length;
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
const placeholderArm  = () => (phArm  ??= makePlaceholder(255, 224, 0, false));

const mats = { toon: null, pbr: null };
let activeSet = null;
let wantKey = null;
const warned = new Set();

function applyTexSet(mat, set) {
  const u = mat?.userData?.buildingUniforms;
  if (!u) return;
  const isPbr = !!u.uNorArr;
  if (!set?.diff || (isPbr && (!set.nor || !set.arm))) {
    u.uTexOn.value = 0.0;
    u.uDiffArr.value = placeholderDiff();
    if (u.uNorArr) u.uNorArr.value = placeholderNor();
    if (u.uArmArr) u.uArmArr.value = placeholderArm();
    return;
  }
  u.uDiffArr.value = set.diff.texture;
  for (let i = 0; i < TEX_IDS.length; i++) {
    if (set.diff.averages?.[i]) u.uDiffAvg.value[i].copy(set.diff.averages[i]);
  }
  if (isPbr) {
    u.uNorArr.value = set.nor.texture;
    u.uArmArr.value = set.arm.texture;
    for (let i = 0; i < TEX_IDS.length; i++) {
      u.uArmAO.value[i] = Math.max(set.arm.averages?.[i]?.x ?? DEFAULT_ARM_AO[i], 0.35);
    }
  }
  u.uTexOn.value = 1.0;
}

function disposeTexSet(set) {
  if (!set) return;
  set.diff?.texture?.dispose();
  set.nor?.texture?.dispose();
  set.arm?.texture?.dispose();
}

const layerUrls = (size, kind) => TEX_IDS.map(id => `./textures/v4/${size}/${id}_${kind}.webp`);

// Non-blocking texture array load for the requested shading tier ('toon' -> 512 diff, 'pbr' -> 1024 diff+nor+arm).
// Disposes the previous tier's arrays cleanly after swapping.
export function ensureBuildingTextures(shading = 'toon') {
  const pbr = shading === 'pbr';
  const size = pbr ? 1024 : 512;
  const key = `${size}|${pbr ? 1 : 0}`;
  wantKey = key;
  if (activeSet?.key === key) {
    if (mats.toon) applyTexSet(mats.toon, !pbr ? activeSet : null);
    if (mats.pbr) applyTexSet(mats.pbr, pbr ? activeSet : null);
    return;
  }
  const aniso = pbr ? 4 : 1;
  const job = pbr
    ? Promise.all([
      loadTextureArray(layerUrls(size, 'diff'), { srgb: true, size, anisotropy: aniso }),
      loadTextureArray(layerUrls(size, 'nor'),  { srgb: false, size, anisotropy: aniso }),
      loadTextureArray(layerUrls(size, 'arm'),  { srgb: false, size, anisotropy: aniso }),
    ]).then(([diff, nor, arm]) => ({ key, diff, nor, arm }))
    : loadTextureArray(layerUrls(size, 'diff'), { srgb: true, size, anisotropy: aniso })
      .then(diff => ({ key, diff, nor: null, arm: null }));

  job.then(next => {
    if (wantKey !== key) {
      if (activeSet?.key !== key) disposeTexSet(next);
      return;
    }
    const prev = activeSet;
    activeSet = next;
    if (mats.toon) applyTexSet(mats.toon, !pbr ? next : null);
    if (mats.pbr) applyTexSet(mats.pbr, pbr ? next : null);
    if (prev && prev.key !== next.key) disposeTexSet(prev);
  }).catch(err => {
    if (!warned.has(key)) {
      warned.add(key);
      console.warn(`[building] v4 building textures (${size}) unavailable, keeping vertex colours:`, err?.message || err);
    }
  });
}

function createBuildingMaterial(pbr) {
  const mat = pbr
    ? new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.90, metalness: 0.0, envMapIntensity: 0.36 })
    : new THREE.MeshToonMaterial({ vertexColors: true, gradientMap: toonGradient() });
  mat.name = pbr ? 'phBuildingPbr' : 'phBuildingToon';
  mat.userData.building = true;
  mat.customProgramCacheKey = () => (pbr ? 'phBuilding_v4_pbr' : 'phBuilding_v4_toon');

  const buildingUniforms = {
    uTexOn:   { value: 0.0 },
    uDiffArr: { value: placeholderDiff() },
    uDiffAvg: { value: DEFAULT_AVGS.map(v => v.clone()) },
    ...(pbr ? {
      uNorArr: { value: placeholderNor() },
      uArmArr: { value: placeholderArm() },
      uArmAO:  { value: DEFAULT_ARM_AO.slice() },
    } : {}),
  };
  mat.userData.buildingUniforms = buildingUniforms;

  mat.onBeforeCompile = sh => {
    injectAerialFog(sh);
    Object.assign(sh.uniforms, buildingUniforms);
    sh.uniforms.uRimColor = pbr ? AERIAL.uRimColor : RIM;
    sh.uniforms.uShadowTint = AERIAL.uShadowTint;

    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>
        attribute float aLayer;
        varying float vLayer;
        varying vec2 vBldUv;`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        vLayer = aLayer;
        vBldUv = uv;`);

    const pbrUniformDecls = pbr ? `
        uniform highp sampler2DArray uNorArr;
        uniform highp sampler2DArray uArmArr;
        uniform float uArmAO[7];` : '';

    const colorCode = /* glsl */`
        int bLayer = clamp(int(floor(vLayer + 0.5)), 0, 7);
        vec2 bUv = vBldUv;
        float bCamDist = length(vAerialPos - cameraPosition);
        ${pbr ? 'float bAo = 1.0; float bRough = 0.92; float bNormFade = 1.0 - smoothstep(26.0, 82.0, bCamDist);' : ''}
        if (uTexOn > 0.5 && bLayer < 7) {
          float tileM = bLayer == 0 ? 2.5 : bLayer == 1 ? 2.0 : bLayer == 2 ? 2.5 : bLayer == 3 ? 1.6 : bLayer == 4 ? 2.0 : bLayer == 5 ? 2.4 : 1.2;
          bUv = vBldUv / tileM;
          float lf = float(bLayer);
          vec3 tex = texture(uDiffArr, vec3(bUv, lf)).rgb;
          vec3 avg = uDiffAvg[bLayer];
          vec3 det = clamp(tex / avg, vec3(0.45), vec3(1.65));

          vec3 base = diffuseColor.rgb;
          float detDist = mix(1.0, 0.58, smoothstep(32.0, 95.0, bCamDist));
          float detS = bLayer == 0 ? 0.84 : bLayer == 1 ? 0.86 : bLayer == 2 ? 0.78 : bLayer == 3 ? 0.85 : bLayer == 4 ? 0.78 : bLayer == 5 ? 0.88 : 0.86;
          float realM = 0.08;
          if (bLayer == 1) realM = 0.42;
          else if (bLayer == 2) realM = 0.26;
          else if (bLayer == 3) {
            // Keep painted blue/green shutters vivid while letting natural brown planks take real timber colour
            float painted = clamp((max(base.b, base.g) - base.r) * 4.5, 0.0, 1.0);
            realM = mix(0.46, 0.10, painted);
          } else if (bLayer == 4) realM = 0.26;
          else if (bLayer == 5) realM = 0.52;
          else if (bLayer == 6) {
            float mxC = max(max(base.r, base.g), base.b);
            float mnC = min(min(base.r, base.g), base.b);
            float sat = (mxC - mnC) / max(mxC, 0.01);
            realM = mix(0.44, 0.18, smoothstep(0.32, 0.68, sat));
          }

          vec3 detCol = base * mix(vec3(1.0), det, detS * detDist);
          float baseL = dot(base, vec3(0.2126, 0.7152, 0.0722));
          float avgL = max(dot(avg, vec3(0.2126, 0.7152, 0.0722)), 0.01);
          vec3 realMatched = tex * (baseL / avgL);
          diffuseColor.rgb = mix(detCol, realMatched, realM * detDist);

          ${pbr ? `
          vec3 arm = texture(uArmArr, vec3(bUv, lf)).rgb;
          bAo = mix(1.0, clamp(arm.r / uArmAO[bLayer], 0.50, 1.12), 0.60 * bNormFade);
          float rMin = bLayer == 3 ? 0.68 : (bLayer == 4 || bLayer == 5) ? 0.76 : 0.84;
          float rMax = bLayer == 3 ? 0.92 : (bLayer == 4 || bLayer == 5) ? 0.95 : 0.98;
          bRough = mix(rMin, rMax, arm.g);` : ''}
        } ${pbr ? 'else if (bLayer == 7) { bRough = 0.97; }' : ''}`;

    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        uniform highp sampler2DArray uDiffArr;
        uniform vec3 uDiffAvg[7];
        uniform float uTexOn;${pbrUniformDecls}
        uniform vec3 uRimColor, uShadowTint;
        varying float vLayer;
        varying vec2 vBldUv;`)
      .replace('#include <color_fragment>', `#include <color_fragment>\n${colorCode}`);

    if (pbr) {
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>
          if (uTexOn > 0.5 || bLayer == 7) roughnessFactor = bRough;`)
        .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
          if (uTexOn > 0.5 && bLayer < 7 && bNormFade > 0.01) {
            vec3 q0 = dFdx(-vViewPosition);
            vec3 q1 = dFdy(-vViewPosition);
            vec2 st0 = dFdx(bUv);
            vec2 st1 = dFdy(bUv);
            vec3 q1p = cross(q1, normal);
            vec3 q0p = cross(normal, q0);
            vec3 bT = q1p * st0.x + q0p * st1.x;
            vec3 bB = q1p * st0.y + q0p * st1.y;
            float detN = max(dot(bT, bT), dot(bB, bB));
            if (detN > 1e-10) {
              float scN = inversesqrt(detN);
              mat3 bTbn = mat3(bT * scN, bB * scN, normal);
              vec3 mapN = texture(uNorArr, vec3(bUv, float(bLayer))).xyz * 2.0 - 1.0;
              float ns = (bLayer == 0 ? 0.80 : bLayer == 1 ? 1.05 : bLayer == 2 ? 0.74 : bLayer == 3 ? 0.95 : bLayer == 4 ? 0.75 : bLayer == 5 ? 1.15 : 0.85) * bNormFade;
              mapN.xy *= vec2(ns, -ns);   // flip Y for glTF flipY=false + OpenGL nor_gl
              normal = normalize(bTbn * mapN);
            }
          }`)
        .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
          {
            reflectedLight.indirectDiffuse *= bAo;
            reflectedLight.indirectSpecular *= 0.36;
            reflectedLight.directSpecular *= 0.50;
            float dirLum = dot(reflectedLight.directDiffuse, vec3(0.3, 0.59, 0.11));
            reflectedLight.indirectDiffuse += diffuseColor.rgb * uShadowTint * (1.0 - smoothstep(0.0, 0.35, dirLum)) * 0.07;
            float rimF = 1.0 - clamp(abs(dot(normalize(vViewPosition), normal)), 0.0, 1.0);
            reflectedLight.directDiffuse += diffuseColor.rgb * uRimColor * smoothstep(0.64, 0.90, rimF) * 0.14;
          }`);
    } else {
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
          {
            float rimF = 1.0 - clamp(abs(dot(normalize(vViewPosition), normal)), 0.0, 1.0);
            reflectedLight.directDiffuse += diffuseColor.rgb * uRimColor * smoothstep(0.64, 0.88, rimF) * 0.16;
          }`);
    }
  };
  return mat;
}

export function getBuildingMaterial(shading = 'toon') {
  const pbr = shading === 'pbr';
  const k = pbr ? 'pbr' : 'toon';
  if (!mats[k]) {
    mats[k] = createBuildingMaterial(pbr);
    if (activeSet) applyTexSet(mats[k], activeSet.key === `${pbr ? 1024 : 512}|${pbr ? 1 : 0}` ? activeSet : null);
  }
  return mats[k];
}

// Swap building material across cached asset descriptors and mounted meshes on live tier change.
export function syncBuildingShading(assets, scene, shading = 'toon') {
  const target = getBuildingMaterial(shading);
  ensureBuildingTextures(shading);
  if (assets) {
    for (const a of Object.values(assets)) {
      for (const lod of [a?.lod0, a?.lod1]) {
        if (!lod) continue;
        for (const p of lod) {
          if (p.material?.userData?.building) p.material = target;
        }
      }
    }
  }
  scene?.traverse(o => {
    if (o.isMesh && o.material?.userData?.building && o.material !== target) o.material = target;
  });
}
