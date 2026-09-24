// Toon water (port of blender/v2/env/water.py, spec in toonPalette.js TOON_WATER):
// three flat colour bands shallow → mid → deep by distance from the bank ("e": 0 at the bank,
// 1 mid-stream), a wobbly white foam line hugging the banks plus a dashed inner foam line,
// and pale elongated highlight streaks that scroll along the flow. No reflection or
// refraction passes: it costs one cheap pass on every quality level.
//  · the big water plane has no UVs: e, the flow direction and speed come from a small
//    world-space "bank" texture baked from the heightfield (water/waterBank.js)
//  · UV'd ribbons (the street stream GLB) use u across / v metres along, as in Blender
import * as THREE from 'three';
import { TOON_WATER as W } from './toonPalette.js';

export const waterTime = { value: 0 };
const col = h => ({ value: new THREE.Color(h) });
const colors = () => ({ uDeep: col(W.deep), uMid: col(W.mid), uShallow: col(W.shallow), uFoam: col(W.foam), uStreak: col(W.streak) });
const f = x => x.toFixed(4);

const COMMON = /* glsl */`
  uniform float uTime; uniform vec3 uDeep, uMid, uShallow, uFoam, uStreak;
  float wh(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
  float wnoise(vec2 p) { vec2 i = floor(p), g = fract(p); g = g * g * (3. - 2. * g);
    return mix(mix(wh(i), wh(i + vec2(1, 0)), g.x), mix(wh(i + vec2(0, 1)), wh(i + vec2(1, 1)), g.x), g.y); }
  float wfbm(vec2 p) { return wnoise(p) * .6 + wnoise(p * 2.03 + 7.1) * .4; }
  // e: 0 bank → 1 centre · along/across: metres in the flow frame · p: world xz · flow: speed factor
  vec3 toonWater(float e, float along, float across, vec2 p, float flow) {
    float t = uTime;
    float en = e + (wfbm(p * ${f(W.noise_scale)} + vec2(t * .03, 0.)) - .5) * .36;
    vec3 c = en < ${f(W.shallow_to_mid)} ? uShallow : (en < ${f(W.mid_to_deep)} ? uMid : uDeep);
    float s = wfbm(vec2(across * 3.2, (along - t * ${f(W.streak_speed * 4)} * flow) * .22));
    float streak = step(${f(W.streak_threshold)}, s) * step(.25, e);
    c = mix(c, uStreak, streak * .85);
    float n3 = wnoise(p * 2.5 + vec2(t * .15, -t * .1));
    float edge = step(e + (n3 - .5) * ${f(W.foam_noise * 2)}, ${f(W.foam_edge)});
    float band = step(${f(W.dash_band[0])}, e) * step(e, ${f(W.dash_band[1])});
    float dash = step(${f(1 - 2 * W.dash_duty)}, sin((along - t * ${f(W.flow_speed * 2)} * flow) * ${f(2 * Math.PI / W.dash_period_m)} + n3 * 3.));
    return mix(c, uFoam, max(edge, band * dash));
  }`;

// The world water plane. tBank: r = e, g = unused, b = flow angle / π + .5, a = flow speed.
export function createWaterMaterial({ bankTex, size }) {
  return new THREE.ShaderMaterial({
    fog: true,
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, colors(), { tBank: { value: null }, uSize: { value: size } }]),
    vertexShader: /* glsl */`
      varying vec3 vW;
      #include <fog_pars_vertex>
      void main() {
        vec4 w = modelMatrix * vec4(position, 1.); vW = w.xyz;
        vec4 mvPosition = viewMatrix * w; gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }`,
    fragmentShader: /* glsl */`
      uniform sampler2D tBank; uniform float uSize;
      varying vec3 vW;
      ${COMMON}
      #include <common>
      #include <fog_pars_fragment>
      void main() {
        vec2 p = vW.xz;
        vec4 b = texture2D(tBank, p / uSize + .5);
        float a = (b.b - .5) * PI; vec2 dir = vec2(cos(a), sin(a));
        vec3 c = toonWater(b.r, dot(p, dir), dot(p, vec2(-dir.y, dir.x)), p, b.a);
        gl_FragColor = vec4(c, 1.);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
        #include <fog_fragment>
      }`,
  });
}
export function bindWater(mat, bankTex) { mat.uniforms.tBank.value = bankTex; mat.uniforms.uTime = waterTime; return mat; }

// UV'd ribbons (street stream): u across 0..1, v metres along. Instancing-aware.
let stream;
export function toonStreamWaterMaterial(width = 0.86) {
  if (stream) return stream;
  stream = new THREE.ShaderMaterial({
    fog: true,
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, colors()]),
    vertexShader: /* glsl */`
      varying vec2 vUv; varying vec3 vW;
      #include <fog_pars_vertex>
      void main() {
        vUv = uv;
        vec4 w = vec4(position, 1.);
        #ifdef USE_INSTANCING
          w = instanceMatrix * w;
        #endif
        w = modelMatrix * w; vW = w.xyz;
        vec4 mvPosition = viewMatrix * w; gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }`,
    fragmentShader: /* glsl */`
      varying vec2 vUv; varying vec3 vW;
      ${COMMON}
      #include <common>
      #include <fog_pars_fragment>
      void main() {
        float e = 2. * min(vUv.x, 1. - vUv.x);
        vec3 c = toonWater(e, vUv.y, vUv.x * ${f(width)}, vW.xz, 1.);
        gl_FragColor = vec4(c, 1.);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
        #include <fog_fragment>
      }`,
  });
  stream.uniforms.uTime = waterTime;
  return stream;
}
