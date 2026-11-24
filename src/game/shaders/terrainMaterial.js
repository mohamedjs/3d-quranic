// Dual-path painterly terrain shader:
//  - Lite / Low (`shading: 'toon'`): painterly 3-band toon + 1-fetch RGBA terrain map + aerial fog.
//  - Medium / High / Ultra (`shading: 'pbr'`): Stylized PBR (MeshStandardMaterial + PMREM IBL)
//    + procedural detail normals (sand ripples, packed clay grain, crop furrows, rock strata)
//    + wet-bank specular sheen near Nile/canals/oasis + directional aerial-perspective fog.
// All sharp boundaries (roads, wet banks, farm plots, desert biome) are evaluated per pixel from
// the baked 1024^2 RGBA terrain map (zero downloads, zero sawtooth edges even on Lite's 224^2 mesh).
import * as THREE from 'three';
import { toonGradient, RIM } from './toon.js';
import { AERIAL, injectAerialFog } from './stylizedPbr.js';
import { FIELD_COLORS, SIZE, HALF, WATER_Y } from '../terrain/heightfield.js';
import { getTerrainMapTexture } from '../terrain/terrainGeometry.js';

const v3 = c => `vec3(${c.r.toFixed(4)}, ${c.g.toFixed(4)}, ${c.b.toFixed(4)})`;
const SOIL = new THREE.Color(0x6E4E33);

export function createTerrainMaterial({ shading = 'toon' } = {}) {
  const pbr = shading === 'pbr';
  const mat = pbr
    ? new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.96, metalness: 0.0, envMapIntensity: 0.36 })
    : new THREE.MeshToonMaterial({ vertexColors: true, gradientMap: toonGradient() });
  mat.name = pbr ? 'pbrTerrain' : 'toonTerrain';
  mat.customProgramCacheKey = () => (pbr ? 'pbrTerrain_v3' : 'toonTerrain_v3');

  mat.onBeforeCompile = sh => {
    injectAerialFog(sh);
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
    const terrainColorCode = /* glsl */`
        float tWet = 0.0;
        float tPath = 0.0;
        float tDesert = 0.0;
        float tField = 0.0;
        {
          vec2 wp = vWPos.xz;
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
          float steep = 1.0 - clamp(vWNorm.y, 0.0, 1.0);
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
          float mud = 1.0 - smoothstep(${(WATER_Y - 0.05).toFixed(2)}, ${(WATER_Y + 0.36).toFixed(2)}, vWPos.y);
          diffuseColor.rgb = mix(diffuseColor.rgb, ${v3(FIELD_COLORS.mud)}, clamp(mud, 0.0, 1.0) * 0.90);
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
        }`;

    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        uniform sampler2D uTerrainMap;
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
      // Stylized PBR: matte dusty roads/earth, wet-bank sheen only along water, detail normals
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>
          roughnessFactor = mix(roughnessFactor, 0.99, clamp(tPath + tDesert, 0.0, 1.0));
          roughnessFactor = mix(roughnessFactor, 0.28, tWet * 0.90);`)
        .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
          {
            // Procedural detail micro-normals in view space (fade cleanly with camera distance)
            float camDist = length(vWPos - cameraPosition);
            float detFade = 1.0 - smoothstep(18.0, 72.0, camDist);
            if (detFade > 0.01) {
              vec2 wp = vWPos.xz;
              float freq = mix(2.2, 3.8, tPath);
              float h0 = tn(wp * freq) * 0.65 + tn(wp * freq * 2.3 + 4.1) * 0.35;
              float hx = tn((wp + vec2(0.08, 0.0)) * freq) * 0.65 + tn((wp + vec2(0.08, 0.0)) * freq * 2.3 + 4.1) * 0.35;
              float hz = tn((wp + vec2(0.0, 0.08)) * freq) * 0.65 + tn((wp + vec2(0.0, 0.08)) * freq * 2.3 + 4.1) * 0.35;
              // Add desert sand ripple slope & farm furrow relief
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
            // Kill grazing blue-sky Fresnel shine on dry roads/earth; keep specular glint on wet banks only
            float specMask = mix(0.04, 0.92, tWet);
            reflectedLight.indirectSpecular *= specMask;
            reflectedLight.directSpecular *= mix(0.08, 0.92, tWet);
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
