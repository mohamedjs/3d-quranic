// Dual-path material builder for textured Poly Haven GLBs (`ph_*.glb`, one-atlas trees/shrubs/rocks):
// - Lite / Low (`shading: 'toon'`): MeshToonMaterial with the GLB's albedo map, aerial fog, warm rim,
//   and optional foliage wind + backlit SSS.
// - Medium / High / Ultra (`shading: 'pbr'`): MeshStandardMaterial preserving all GLB maps
//   (albedo, normal, roughness/metalness, AO, emissive), tuned IBL intensity, aerial fog, shadow lift,
//   warm rim, and optional foliage wind + backlit SSS.
// Both variants share a pair reference so live tier switches swap materials in O(1) without losing maps.
import * as THREE from 'three';
import { toonGradient, RIM } from './toon.js';
import { AERIAL, injectAerialFog } from './stylizedPbr.js';
import { injectWind } from './wind.js';

function patchShader(mat, pbr, { wind = null, rim = 0.14, sss = 0, sssColor = 0xb8d954 }) {
  const w = wind ? `${wind.strength}|${wind.factor}|${wind.flutter ?? 0}` : '';
  mat.customProgramCacheKey = () => `phprop_v4|${pbr ? 'p' : 't'}|${w}|${rim.toFixed(2)}|${sss.toFixed(2)}|${mat.alphaTest > 0 ? 1 : 0}`;
  mat.onBeforeCompile = sh => {
    if (wind) injectWind(sh, wind);
    injectAerialFog(sh);
    sh.uniforms.uRimColor = pbr ? AERIAL.uRimColor : RIM;
    if (pbr) sh.uniforms.uShadowTint = AERIAL.uShadowTint;
    if (sss > 0) sh.uniforms.uSssColor = { value: new THREE.Color(sssColor) };

    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        uniform vec3 uRimColor;${pbr ? '\nuniform vec3 uShadowTint;' : ''}${sss > 0 ? '\nuniform vec3 uSssColor;' : ''}`)
      .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
        {
          vec3 pVDir = normalize(vViewPosition);
          ${pbr ? `float pDirLum = dot(reflectedLight.directDiffuse, vec3(0.3, 0.59, 0.11));
          reflectedLight.indirectDiffuse += diffuseColor.rgb * uShadowTint * (1.0 - smoothstep(0.0, 0.35, pDirLum)) * 0.08;` : ''}
          ${rim > 0 ? `float pRim = 1.0 - clamp(abs(dot(pVDir, normal)), 0.0, 1.0);
          reflectedLight.directDiffuse += diffuseColor.rgb * uRimColor * smoothstep(0.62, 0.88, pRim) * ${rim.toFixed(3)};` : ''}
          ${sss > 0 ? `vec3 pWDir = normalize(vAerialPos - cameraPosition);
          float pBack = pow(clamp(dot(pWDir, uAerialSunDir), 0.0, 1.0), 2.4);
          reflectedLight.directDiffuse += diffuseColor.rgb * uSssColor * (pBack * ${pbr ? '0.78' : '0.52'} + ${pbr ? '0.16' : '0.10'}) * ${sss.toFixed(3)};` : ''}
        }`);
  };
}

function setTexAniso(mat, aniso) {
  for (const k of ['map', 'normalMap', 'roughnessMap', 'metalnessMap', 'aoMap']) {
    const t = mat[k];
    if (t && t.anisotropy !== aniso) {
      t.anisotropy = aniso;
      t.needsUpdate = true;
    }
  }
}

export function createPropMaterial(srcMat, {
  shading = 'toon',
  vertexColors = false,
  isFoliage = false,
  alphaTest = 0,
  side = null,
  wind = null,
  rim = 0.14,
  sss = 0,
  noShadow = false,
  noReflect = false,
} = {}) {
  const cut = alphaTest || (isFoliage ? 0.5 : (srcMat?.alphaTest > 0 ? srcMat.alphaTest : 0));
  const useSide = side ?? (isFoliage || cut > 0 ? THREE.DoubleSide : (srcMat?.side ?? THREE.FrontSide));
  const baseColor = srcMat?.color ? srcMat.color.clone() : new THREE.Color(0xffffff);
  const emissive = srcMat?.emissive ? srcMat.emissive.clone() : new THREE.Color(0x000000);
  const emissiveIntensity = srcMat?.emissiveIntensity ?? 1.0;
  const hasGlow = (emissive.r + emissive.g + emissive.b) > 0.01;
  const isMetal = (srcMat?.metalness ?? 0) > 0.35 || /brass/.test(srcMat?.name ?? '');

  // Ensure crisp mipmapped sampling on embedded WebP maps
  if (srcMat?.map) {
    srcMat.map.colorSpace = THREE.SRGBColorSpace;
    srcMat.map.minFilter = THREE.LinearMipmapLinearFilter;
    srcMat.map.magFilter = THREE.LinearFilter;
    srcMat.map.needsUpdate = true;
  }

  const toon = new THREE.MeshToonMaterial({
    name: `phPropToon_${srcMat?.name || 'm'}`,
    color: baseColor,
    map: srcMat?.map ?? null,
    emissive,
    emissiveIntensity: hasGlow ? emissiveIntensity : 0,
    gradientMap: toonGradient(),
    vertexColors,
    alphaTest: cut,
    transparent: false,
    depthWrite: true,
    side: useSide,
  });
  // Slight brightness lift on metallic brass maps in toon mode (no IBL specular on MeshToonMaterial)
  if (isMetal && !hasGlow) toon.color.multiplyScalar(1.22);

  const pbr = new THREE.MeshStandardMaterial({
    name: `phPropPbr_${srcMat?.name || 'm'}`,
    color: baseColor,
    map: srcMat?.map ?? null,
    normalMap: srcMat?.normalMap ?? null,
    normalScale: srcMat?.normalScale ? srcMat.normalScale.clone().multiplyScalar(0.85) : new THREE.Vector2(0.82, 0.82),
    roughnessMap: srcMat?.roughnessMap ?? null,
    metalnessMap: srcMat?.metalnessMap ?? null,
    aoMap: srcMat?.aoMap ?? null,
    aoMapIntensity: srcMat?.aoMap ? 0.65 : 1.0,
    roughness: srcMat?.roughnessMap ? 1.0 : (srcMat?.roughness ?? (isFoliage ? 0.82 : 0.86)),
    metalness: srcMat?.metalnessMap ? (srcMat?.metalness ?? 1.0) : (isFoliage ? 0.0 : (srcMat?.metalness ?? 0.0)),
    emissive,
    emissiveIntensity: hasGlow ? emissiveIntensity : 0,
    envMapIntensity: isMetal ? 0.72 : (isFoliage ? 0.42 : 0.46),
    vertexColors,
    alphaTest: cut,
    transparent: false,
    depthWrite: true,
    side: useSide,
  });

  patchShader(toon, false, { wind, rim: hasGlow ? 0 : rim, sss });
  patchShader(pbr, true, { wind, rim: hasGlow ? 0 : rim, sss });

  const pair = { toon, pbr };
  for (const m of [toon, pbr]) {
    m.userData.prop = true;
    m.userData.propPair = pair;
    m.userData.foliage = isFoliage;
    m.userData.noShadow = noShadow;
    m.userData.noReflect = noReflect;
  }

  const active = shading === 'pbr' ? pbr : toon;
  setTexAniso(active, shading === 'pbr' ? 4 : 1);
  return active;
}

// Swap every textured prop/tree/shrub/rock material across cached assets & mounted scene meshes on live tier change.
export function syncPropShading(assets, scene, shading = 'toon') {
  const key = shading === 'pbr' ? 'pbr' : 'toon';
  const aniso = key === 'pbr' ? 4 : 1;
  const touched = new Set();
  const swap = m => {
    const pair = m?.userData?.propPair;
    if (!pair) return m;
    const next = pair[key];
    if (!touched.has(next)) {
      touched.add(next);
      setTexAniso(next, aniso);
    }
    return next;
  };
  if (assets) {
    for (const a of Object.values(assets)) {
      for (const lod of [a?.lod0, a?.lod1]) {
        if (!lod) continue;
        for (const p of lod) {
          if (p.material?.userData?.propPair) p.material = swap(p.material);
        }
      }
    }
  }
  scene?.traverse(o => {
    if (!o.isMesh) return;
    if (Array.isArray(o.material)) {
      let changed = false;
      const arr = o.material.map(m => { const n = swap(m); if (n !== m) changed = true; return n; });
      if (changed) o.material = arr;
    } else if (o.material?.userData?.propPair) {
      const next = swap(o.material);
      if (o.material !== next) o.material = next;
    }
  });
}
