// Toon terrain: cel-lit MeshToonMaterial over the painted vertex colours, with the crisp
// features drawn per pixel so they stay sharp on a 1.4 m vertex grid:
//  · farm plots (15 × 10 m, same hash as fieldPlot) in flat crop colours with earth bunds
//    and soft crop-row stripes up close
//  · warm dirt paths with a slightly wobbly painted edge
//  · large soft two-tone patches so wide lawns don't read as one flat sheet
// No textures: one draw call, a handful of ALU ops per pixel.
import * as THREE from 'three';
import { toonGradient, RIM } from './toon.js';
import { FIELD_COLORS } from '../terrain/heightfield.js';

const v3 = c => `vec3(${c.r.toFixed(4)}, ${c.g.toFixed(4)}, ${c.b.toFixed(4)})`;
const SOIL = new THREE.Color(0x8A6A44);

export function createTerrainMaterial() {
  const mat = new THREE.MeshToonMaterial({ vertexColors: true, gradientMap: toonGradient() });
  mat.customProgramCacheKey = () => 'toonTerrain';
  mat.onBeforeCompile = sh => {
    sh.uniforms.uRimColor = RIM;
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>
        attribute vec2 toonMask; varying vec2 vMask; varying vec3 vWPos;`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        vMask = toonMask; vWPos = (modelMatrix * vec4(position, 1.)).xyz;`);
    const [c0, c1, c2, c3] = FIELD_COLORS.crops;
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        varying vec2 vMask; varying vec3 vWPos;
        float th(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
        float tn(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
          return mix(mix(th(i), th(i + vec2(1, 0)), f.x), mix(th(i + vec2(0, 1)), th(i + vec2(1, 1)), f.x), f.y); }
        float plotHash(int x, int y) {        // = hash() in heightfield.js
          uint h = uint(x) * 374761393u + uint(y) * 668265263u;
          h = (h ^ (h >> 13u)) * 1274126177u; h = h ^ (h >> 16u);
          return float(h) / 4294967295.;
        }`)
      .replace('#include <color_fragment>', `#include <color_fragment>
        {
          vec2 wp = vWPos.xz;
          float pch = tn(wp * .06) * .65 + tn(wp * .23) * .35;
          diffuseColor.rgb *= mix(.95, 1.05, smoothstep(.48, .52, pch));
          float wob = (tn(wp * 1.7) - .5) * .22;
          if (vMask.x > .5) {                                        // farmland
            vec2 q = wp + 1000.;
            vec2 e = mod(q, vec2(15., 10.));
            vec3 fc;
            if (e.x < .9 || e.y < .7) fc = ${v3(FIELD_COLORS.bund)};
            else {
              int t = int(floor(plotHash(int(floor(q.x / 15.)) + 11, int(floor(q.y / 10.)) + 7) * 4.));
              fc = t == 0 ? ${v3(c0)} : t == 1 ? ${v3(c1)} : t == 2 ? ${v3(c2)} : ${v3(c3)};
              float rows = fract(wp.y / 1.2), aa = min(fwidth(wp.y / 1.2) * 1.5, .5);
              float stripe = smoothstep(.5 - aa, .5 + aa, rows) * (1. - smoothstep(.95 - aa, .95 + aa, rows) * 0.);
              float fade = 1. - smoothstep(.15, .45, fwidth(wp.y / 1.2));   // rows only up close
              vec3 between = t >= 2 ? ${v3(SOIL)} : fc * .86;
              fc = mix(fc, mix(fc, between, stripe), fade * (t >= 2 ? .75 : .5));
              fc *= .96 + .08 * plotHash(int(floor(q.x / 15.)), int(floor(q.y / 10.)));
            }
            diffuseColor.rgb = mix(diffuseColor.rgb, fc, smoothstep(.45, .55, vMask.x));
          }
          float path = smoothstep(.47, .53, vMask.y + wob * vMask.y);
          diffuseColor.rgb = mix(diffuseColor.rgb, ${v3(FIELD_COLORS.path)} * (.97 + .06 * tn(wp * .8)), path);
        }`)
      .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
        { float rimF = 1. - clamp(dot(normalize(vViewPosition), normal), 0., 1.);
          reflectedLight.directDiffuse += diffuseColor.rgb * uRimColor * smoothstep(.7, .9, rimF) * .12; }`);
    sh.fragmentShader = 'uniform vec3 uRimColor;\n' + sh.fragmentShader;
  };
  return mat;
}
