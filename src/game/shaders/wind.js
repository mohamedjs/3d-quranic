// Shader-based wind for instanced vegetation: a slow travelling gust front, a sway, and a
// small flutter for leaves. `factor` is a GLSL expression that is 0 at the plant's root.
// Used by the toon materials (toon.js) for every material flagged `w` in the art contract,
// and by their outline hulls so the ink line moves with the leaves.
import * as THREE from 'three';

export const wind = { uTime: { value: 0 }, uStrength: { value: 1 }, uSunDirV: { value: new THREE.Vector3() }, uSunDirW: { value: new THREE.Vector3(0, 1, 0) } };

// GLSL to insert after <begin_vertex>; needs `uniform float uTime, uStrength`.
export function windChunk({ strength = 0.2, flutter = 0, factor = 'position.y' } = {}) {
  return `
      vec4 ip = vec4(0., 0., 0., 1.);
      #ifdef USE_INSTANCING
        ip = instanceMatrix * ip;
      #endif
      float k = pow(clamp(${factor}, 0., 2.), 1.5) * ${strength.toFixed(3)} * uStrength;
      float gust = .55 + .45 * sin(dot(ip.xz, vec2(.045, .03)) - uTime * .9);
      float sway = sin(uTime * 1.3 + ip.x * .21 + ip.z * .17) * .6 + sin(uTime * 2.1 + ip.x * .5) * .25;
      transformed.x += (sway + .6) * k * gust;
      transformed.z += (sway * .5 + .25) * k * gust;
      ${flutter ? `transformed += objectNormal * sin(uTime * 7. + position.x * 11. + position.z * 9. + ip.x) * ${flutter.toFixed(3)} * k * 4.;` : ''}`;
}

export function injectWind(sh, opts) {
  Object.assign(sh.uniforms, { uTime: wind.uTime, uStrength: wind.uStrength });
  sh.vertexShader = 'uniform float uTime; uniform float uStrength;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n' + windChunk(opts));
}
