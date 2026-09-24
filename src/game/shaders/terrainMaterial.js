// Terrain: MeshStandardMaterial extended with a six-layer PBR splat.
// Per layer: albedo, normal and ARM (AO/roughness/metal) from texture arrays.
// Height-based blending gives crisp, natural transitions (grass fills the cracks of dirt,
// not a smeary crossfade), a rotated second sample breaks tiling, and ground near the
// waterline turns dark and glossy.
import * as THREE from 'three';
import { WATER_Y } from '../terrain/heightfield.js';

export const LAYER_SCALE = [3.2, 2.6, 2.2, 2.4, 6.0, 5.0]; // metres per texture repeat

export function createTerrainMaterial(arrays, antiTile) {
  const mat = new THREE.MeshStandardMaterial({ roughness: 1, metalness: 0 });
  mat.defines = { ANTI_TILE: antiTile ? 1 : 0 };
  mat.customProgramCacheKey = () => 'terrain' + (antiTile ? 1 : 0);
  mat.onBeforeCompile = sh => {
    Object.assign(sh.uniforms, {
      tDiff: { value: arrays.diff }, tNor: { value: arrays.nor }, tArm: { value: arrays.arm },
      uScale: { value: LAYER_SCALE },
    });
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>
        attribute vec3 splatA; attribute vec3 splatB; attribute vec3 tint;
        varying vec3 vSplatA; varying vec3 vSplatB; varying vec3 vTint; varying vec3 vWPos;`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        vSplatA = splatA; vSplatB = splatB; vTint = tint; vWPos = (modelMatrix * vec4(position, 1.)).xyz;`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        precision highp sampler2DArray;
        uniform sampler2DArray tDiff, tNor, tArm;
        uniform float uScale[6];
        varying vec3 vSplatA; varying vec3 vSplatB; varying vec3 vTint; varying vec3 vWPos;
        float th21(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
        float tnoise(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
          return mix(mix(th21(i), th21(i + vec2(1, 0)), f.x), mix(th21(i + vec2(0, 1)), th21(i + vec2(1, 1)), f.x), f.y); }
        const mat2 ROT = mat2(0.8, -0.6, 0.6, 0.8);
        void layerSample(int i, vec2 wp, vec2 dx, vec2 dy, float mixN, out vec3 a, out vec3 n, out vec3 r) {
          float s = 1. / uScale[i];
          vec2 uv = wp * s; vec2 gx = dx * s, gy = dy * s;
          a = textureGrad(tDiff, vec3(uv, float(i)), gx, gy).rgb;
          n = textureGrad(tNor, vec3(uv, float(i)), gx, gy).xyz * 2. - 1.;
          r = textureGrad(tArm, vec3(uv, float(i)), gx, gy).rgb;
          #if ANTI_TILE
            vec2 uv2 = ROT * uv * 0.43 + vec2(0.37, 0.71); vec2 gx2 = ROT * gx * 0.43, gy2 = ROT * gy * 0.43;
            vec3 a2 = textureGrad(tDiff, vec3(uv2, float(i)), gx2, gy2).rgb;
            vec3 n2 = textureGrad(tNor, vec3(uv2, float(i)), gx2, gy2).xyz * 2. - 1.;
            vec3 r2 = textureGrad(tArm, vec3(uv2, float(i)), gx2, gy2).rgb;
            n2.xy = transpose(ROT) * n2.xy;
            a = mix(a, a2, mixN); n = normalize(mix(n, n2, mixN)); r = mix(r, r2, mixN);
          #endif
        }`)
      .replace('#include <map_fragment>', `
        vec2 wp = vWPos.xz, wdx = dFdx(wp), wdy = dFdy(wp);
        float mixN = smoothstep(0.3, 0.7, tnoise(wp * 0.045));
        float w[6] = float[6](vSplatA.x, vSplatA.y, vSplatA.z, vSplatB.x, vSplatB.y, vSplatB.z);
        vec3 la[6]; vec3 ln[6]; vec3 lr[6]; float lh[6]; float top = -1.;
        for (int i = 0; i < 6; i++) {
          la[i] = vec3(0.); ln[i] = vec3(0., 0., 1.); lr[i] = vec3(1., 1., 0.); lh[i] = -1.;
          if (w[i] > 0.015) {
            layerSample(i, wp, wdx, wdy, mixN, la[i], ln[i], lr[i]);
            if (i == 0) {   // grass layer: the photo texture is dry and rocky — push it to living green
              float l = dot(la[i], vec3(0.3, 0.59, 0.11));
              la[i] = max(mix(vec3(l), la[i], 1.5), 0.) * vec3(0.72, 1.08, 0.5) * (0.9 + 0.35 * tnoise(wp * 0.08));
            }
            lh[i] = w[i] + dot(la[i], vec3(0.3, 0.59, 0.11)) * 0.55;   // albedo brightness as a height cue
            top = max(top, lh[i]);
          }
        }
        vec3 tAlb = vec3(0.), tN = vec3(0.), tArmV = vec3(0.); float bsum = 0.;
        for (int i = 0; i < 6; i++) {
          float b = max(lh[i] - (top - 0.18), 0.);
          tAlb += la[i] * b; tN += ln[i] * b; tArmV += lr[i] * b; bsum += b;
        }
        tAlb /= bsum; tN = normalize(tN); tArmV /= bsum;
        float macro = 0.82 + 0.36 * tnoise(wp * 0.012) * tnoise(wp * 0.05 + 3.1);
        float wet = 1. - smoothstep(${(WATER_Y + 0.05).toFixed(2)}, ${(WATER_Y + 1.0).toFixed(2)}, vWPos.y);
        tAlb *= vTint * macro * mix(1., 0.48, wet);
        float tRough = mix(tArmV.g, 0.22, wet * 0.85);
        diffuseColor.rgb *= tAlb;`)
      .replace('#include <roughnessmap_fragment>', 'float roughnessFactor = roughness * clamp(tRough, 0.08, 1.);')
      .replace('#include <metalnessmap_fragment>', 'float metalnessFactor = 0.;')
      .replace('#include <normal_fragment_maps>', `
        vec3 tV = normalize((viewMatrix * vec4(1., 0., 0., 0.)).xyz);
        vec3 bV = normalize((viewMatrix * vec4(0., 0., 1., 0.)).xyz);
        tV = normalize(tV - normal * dot(normal, tV));
        bV = normalize(bV - normal * dot(normal, bV) - tV * dot(tV, bV));
        tN.xy *= 1.15;
        normal = normalize(tV * tN.x + bV * tN.y + normal * tN.z);`)
      .replace('#include <aomap_fragment>', `
        float ambientOcclusion = mix(1., tArmV.r, 0.9);
        reflectedLight.indirectDiffuse *= ambientOcclusion;
        reflectedLight.indirectSpecular *= ambientOcclusion;`);
  };
  return mat;
}
