// Dual-path painterly environment shaders & unified directional aerial-perspective fog.
// - Lite / Low (`shading: 'toon'`): painterly 3-band toon (toon.js) + aerial fog.
// - Medium / High / Ultra (`shading: 'pbr'`): MeshStandardMaterial + PMREM IBL + cool/warm
//   shadow tint + sun rim + directional aerial-perspective fog (+ optional foliage SSS).
import * as THREE from 'three';
import { injectWind } from './wind.js';
import { toonMaterial } from './toon.js';

// Shared directional aerial-perspective uniforms (linear working space, applied pre-tonemap
// so distant fog matches Sky.js identically on both Lite NeutralTM and High EffectComposer).
export const AERIAL = {
  uAerialSunDir:  { value: new THREE.Vector3(0.7764, 0.2756, 0.5668).normalize() },
  uAerialWarm:    { value: new THREE.Color('#e4d5be') },   // pale warm-cream horizon mist (gentle, never orange soup)
  uAerialCool:    { value: new THREE.Color('#b6c6da') },   // pale warm-blue aerial perspective horizon
  uAerialSunGlow: { value: new THREE.Color('#f7d89c') },   // subtle golden Mie scatter toward the sun
  uShadowTint:    { value: new THREE.Color('#6e7fa3') },   // cool lavender-indigo shadow harmony
  uRimColor:      { value: new THREE.Color('#ffd58e') },   // honey-gold backlit rim
};

export function updateAerialFog(sunDir) {
  if (sunDir) AERIAL.uAerialSunDir.value.copy(sunDir).normalize();
}

// Replace Three.js's flat post-tonemap <fog_fragment> with linear pre-tonemap directional
// aerial-perspective fog (warm golden haze toward the sun, cool lavender-rose away from it,
// gentle valley-floor mist weighting). Works on regular, instanced, and skinned meshes.
export function injectAerialFog(sh) {
  Object.assign(sh.uniforms, {
    uAerialSunDir: AERIAL.uAerialSunDir,
    uAerialWarm: AERIAL.uAerialWarm,
    uAerialCool: AERIAL.uAerialCool,
    uAerialSunGlow: AERIAL.uAerialSunGlow,
  });
  sh.vertexShader = sh.vertexShader
    .replace('#include <common>', '#include <common>\nvarying vec3 vAerialPos;')
    .replace('#include <fog_vertex>', `#include <fog_vertex>
      {
        vec4 aW = vec4(transformed, 1.0);
        #ifdef USE_INSTANCING
          aW = instanceMatrix * aW;
        #endif
        vAerialPos = (modelMatrix * aW).xyz;
      }`);
  sh.fragmentShader = sh.fragmentShader
    .replace('#include <common>', `#include <common>
      uniform vec3 uAerialSunDir, uAerialWarm, uAerialCool, uAerialSunGlow;
      varying vec3 vAerialPos;`)
    .replace('#include <tonemapping_fragment>', `#ifdef USE_FOG
      {
        vec3 aDir = normalize(vAerialPos - cameraPosition);
        float aSun = clamp(dot(aDir, uAerialSunDir) * 0.5 + 0.5, 0.0, 1.0);
        vec3 aCol = mix(uAerialCool, uAerialWarm, smoothstep(0.18, 0.92, aSun));
        aCol += uAerialSunGlow * pow(max(dot(aDir, uAerialSunDir), 0.0), 5.0) * 0.12;
        float aLow = exp(-max(vAerialPos.y + 1.5, 0.0) * 0.025);
        float aDist = smoothstep(fogNear, fogFar, vFogDepth);
        float aFog = clamp(aDist * (0.82 + 0.12 * aLow), 0.0, 0.92);
        gl_FragColor.rgb = mix(gl_FragColor.rgb, aCol, aFog);
      }
    #endif
    #include <tonemapping_fragment>`)
    .replace('#include <fog_fragment>', '/* aerial fog applied pre-tonemap */');
}

const pbrCache = new Map();

// Stylized PBR material for Medium–Ultra: matte painterly roughness, PMREM IBL response,
// warm/cool shadow harmony, soft honey rim, directional aerial fog, optional wind & foliage SSS.
export function stylizedPbrMaterial(key, {
  color = 0xffffff, map = null, normalMap = null, roughnessMap = null, aoMap = null,
  roughness = 0.88, metalness = 0.0, envMapIntensity = 0.55, side = THREE.FrontSide,
  vertexColors = false, alphaTest = 0, wind = null, rim = 0.16, sss = 0, sssColor = 0xa8cf58,
} = {}) {
  if (pbrCache.has(key)) return pbrCache.get(key);
  const m = new THREE.MeshStandardMaterial({
    color, map, normalMap, roughnessMap, aoMap, roughness, metalness, envMapIntensity, side, vertexColors, alphaTest,
  });
  m.name = key;
  const w = wind ? `${wind.strength}|${wind.factor}|${wind.flutter ?? 0}` : '';
  m.customProgramCacheKey = () => `spbr|${w}|${rim.toFixed(2)}|${sss.toFixed(2)}`;
  m.onBeforeCompile = sh => {
    if (wind) injectWind(sh, wind);
    injectAerialFog(sh);
    sh.uniforms.uRimColor = AERIAL.uRimColor;
    sh.uniforms.uShadowTint = AERIAL.uShadowTint;
    if (sss > 0) sh.uniforms.uSssColor = { value: new THREE.Color(sssColor) };
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        uniform vec3 uRimColor, uShadowTint;${sss > 0 ? '\nuniform vec3 uSssColor;' : ''}`)
      .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
        {
          vec3 vDir = normalize(vViewPosition);
          // Subtle cool lavender lift in deep shadow so shaded world surfaces harmonize with cel cast
          float dirLum = dot(reflectedLight.directDiffuse, vec3(0.3, 0.59, 0.11));
          reflectedLight.indirectDiffuse += diffuseColor.rgb * uShadowTint * (1.0 - smoothstep(0.0, 0.35, dirLum)) * 0.08;
          ${rim > 0 ? `float rimF = 1.0 - clamp(dot(vDir, normal), 0.0, 1.0);
          reflectedLight.directDiffuse += diffuseColor.rgb * uRimColor * smoothstep(0.62, 0.90, rimF) * ${rim.toFixed(3)};` : ''}
          ${sss > 0 ? `vec3 wDir = normalize(vAerialPos - cameraPosition);
          float back = pow(clamp(dot(wDir, uAerialSunDir), 0.0, 1.0), 3.0);
          reflectedLight.directDiffuse += diffuseColor.rgb * uSssColor * back * ${sss.toFixed(3)};` : ''}
        }`);
  };
  pbrCache.set(key, m);
  return m;
}

// Dual-path factory: returns painterly toon on Lite/Low and stylized PBR on Medium–Ultra.
export function envMaterial(key, opts = {}) {
  const { shading = 'toon', ...rest } = opts;
  return shading === 'pbr' ? stylizedPbrMaterial(`pbr_${key}`, rest) : toonMaterial(key, rest);
}
