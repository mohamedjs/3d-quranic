// Golden-hour sky dome driven by Poly Haven sun.json:
//  - Lite / Low / Medium (`map` null): warm-graded gradient stops from sun.json + sun halo/disc
//    + two sculpted painterly cumulus layers + high cirrus wisps (tiered 2/3/4 oct).
//  - High / Ultra (`map` = 2k equirect): samples the sunset HDRI (three's equirectUv convention)
//    through warmGrade, plus sun halo/disc and subtle painterly cloud wisps.
// One camera-following back-faced sphere.
import * as THREE from 'three';
import { FALLBACK_SUN, SUN_DIR, warmGrade, WARM_GRADE_GLSL } from '../lighting/environmentMap.js';

const MAX_STOPS = 12;
const WHITE = new THREE.Color('#ffffff');

export function createSky(sun, { dir = null, octaves = 4, map = null } = {}) {
  const isVec = sun && sun.isVector3;
  const sunData = isVec || !sun ? FALLBACK_SUN : sun;
  const sunDir = (dir ?? (isVec ? sun : (Array.isArray(sunData.sunDirection) ? new THREE.Vector3(...sunData.sunDirection) : SUN_DIR))).clone().normalize();
  const oct = typeof octaves === 'boolean' ? (octaves ? 2 : 4) : Math.max(2, Math.min(4, octaves | 0));

  const rawStops = (sunData.gradient?.length ? sunData.gradient : FALLBACK_SUN.gradient).slice(0, MAX_STOPS);
  const stopElev = new Float32Array(MAX_STOPS);
  const stopCol = [];
  for (let i = 0; i < MAX_STOPS; i++) {
    const s = rawStops[Math.min(i, rawStops.length - 1)];
    stopElev[i] = s.elevationDeg;
    stopCol.push(warmGrade(s.color, s.elevationDeg));
  }

  const sunTint = new THREE.Color(sunData.sunColor || '#ffd488').lerp(WHITE, 0.35);
  const valleyMist = new THREE.Color('#c48952').lerp(stopCol[0], 0.45);
  const horizonCol = stopCol.find((_, i) => rawStops[Math.min(i, rawStops.length - 1)].elevationDeg >= 0) ?? stopCol[0];
  const zenithCol = stopCol[rawStops.length - 1];

  const mat = new THREE.ShaderMaterial({
    defines: { SKY_OCT: oct, ...(map ? { USE_SKY_MAP: 1 } : {}) },
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    uniforms: {
      uSun:       { value: sunDir },
      uTime:      { value: 0 },
      uSunTint:   { value: sunTint },
      uValleyCol: { value: valleyMist },
      uHorizon:   { value: horizonCol.clone() },
      uZenith:    { value: zenithCol.clone() },
      ...(map
        ? { uMap: { value: map } }
        : {
          uStopElev:  { value: stopElev },
          uStopCol:   { value: stopCol },
          uStopCount: { value: rawStops.length },
        }),
    },
    vertexShader: /* glsl */`
      varying vec3 vDir;
      void main() { vDir = normalize(position); vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.); gl_Position = p.xyww; }`,
    fragmentShader: /* glsl */`
      uniform vec3 uSun, uSunTint, uValleyCol, uHorizon, uZenith;
      uniform float uTime;
      #ifdef USE_SKY_MAP
        uniform sampler2D uMap;
      #else
        uniform float uStopElev[${MAX_STOPS}];
        uniform vec3 uStopCol[${MAX_STOPS}];
        uniform int uStopCount;
      #endif
      varying vec3 vDir;

      float h(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      float n(vec2 p) {
        vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
        return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y);
      }
      float fbm(vec2 p) {
        float s = 0., a = .5;
        for (int i = 0; i < SKY_OCT; i++) { s += a * n(p); p = p * 2.04 + vec2(13.7, 7.3); a *= .5; }
        return s * (.9375 / (1. - pow(.5, float(SKY_OCT))));
      }
      vec3 srgb(vec3 c) { return pow(c, vec3(2.2)); }
      ${WARM_GRADE_GLSL}

      #ifndef USE_SKY_MAP
      vec3 sampleGradient(float elevDeg) {
        vec3 c = uStopCol[0];
        for (int i = 0; i < ${MAX_STOPS - 1}; i++) {
          if (i + 1 >= uStopCount) break;
          c = mix(c, uStopCol[i + 1], smoothstep(uStopElev[i], uStopElev[i + 1], elevDeg));
        }
        return c;
      }
      #endif

      void main() {
        vec3 d = normalize(vDir);
        float y = max(d.y, 0.);
        float elevDeg = degrees(asin(clamp(d.y, -1.0, 1.0)));
        float sunDot = dot(d, uSun);
        float s = max(sunDot, 0.);
        float anti = pow(max(-sunDot, 0.), 1.5);

        #ifdef USE_SKY_MAP
          // Equirect lookup matching three's equirectUv convention; lift pre-tonemapped LDR slightly
          // so golden horizon stays luminous under ACES Filmic, and clamp below horizon to valley mist
          vec3 sampleDir = d.y >= 0.0 ? d : normalize(vec3(d.x, 0.0, d.z));
          vec2 uv = vec2(atan(sampleDir.z, sampleDir.x) * 0.15915494309 + 0.5, asin(clamp(sampleDir.y, -1.0, 1.0)) * 0.31830988618 + 0.5);
          vec3 c = warmGrade(texture2D(uMap, uv).rgb * 1.32, max(elevDeg, 0.0));
          if (d.y < 0.0) {
            c = mix(c, uValleyCol, smoothstep(0.0, 0.25, -d.y));
          }
          // Subtle Mie aureole + crisp sun disc aligned with the clamped sunDir
          float horBoost = 1.0 - smoothstep(0.0, 0.45, y);
          c += uSunTint * (pow(s, 3.5) * .20 * (.55 + .45 * horBoost) + pow(s, 16.0) * .32 + pow(s, 92.0) * .54);
          c = mix(c, mix(uSunTint, vec3(1.0, .97, .88), 0.65) * 1.9, smoothstep(.9986, .9994, s));
          float cloudAlpha = 0.62;
        #else
          // Warm-graded gradient stops from sun.json + Belt of Venus opposite the sun
          vec3 c = sampleGradient(elevDeg);
          vec3 antiRose = mix(uHorizon, srgb(vec3(.78, .58, .64)), 0.58);
          vec3 antiLav  = mix(uZenith,  srgb(vec3(.52, .54, .68)), 0.52);
          vec3 oppCol   = mix(antiRose, antiLav, smoothstep(0.04, 0.36, y));
          c = mix(c, oppCol, anti * (1.0 - smoothstep(0.06, 0.56, y)) * 0.42);
          if (d.y < 0.0) {
            c = mix(c, uValleyCol, smoothstep(0.0, 0.25, -d.y));
          }
          // Mie forward scattering + golden aureole + crisp sun disc
          float horBoost = 1.0 - smoothstep(0.0, 0.45, y);
          c += uSunTint * (pow(s, 3.0) * .24 * (.55 + .45 * horBoost) + pow(s, 14.0) * .36 + pow(s, 84.0) * .54);
          c = mix(c, mix(uSunTint, vec3(1.0, .97, .88), 0.65) * 1.85, smoothstep(.9986, .9994, s));
          float cloudAlpha = 1.0;
        #endif

        // Painterly cloud deck (2 sculpted cumulus layers + high cirrus wisps), tinted to the new palette
        if (d.y > 0.015) {
          vec2 pUv = d.xz / (d.y + 0.11);
          float drift = uTime * 0.0032;

          // High cirrus wisps catching warm golden upper sunlight
          vec2 wispUv = vec2(pUv.x * 0.55 + pUv.y * 0.22 + drift * 0.55, pUv.y * 2.1 - pUv.x * 0.35);
          float wisp = n(wispUv * 1.15) * 0.65 + n(wispUv * 2.7 + 3.1) * 0.35;
          float wispBand = smoothstep(0.14, 0.38, y) * (1.0 - smoothstep(0.72, 0.96, y));
          float wispMask = smoothstep(0.56, 0.78, wisp) * wispBand * 0.34 * cloudAlpha;
          vec3 wispCol = mix(mix(uHorizon, srgb(vec3(.96, .84, .76)), 0.55), mix(uSunTint, vec3(1.0, .96, .86), 0.6), smoothstep(-0.3, 0.8, sunDot));
          c = mix(c, wispCol, wispMask);

          // Primary sculpted painterly cumulus layer
          vec2 uv1 = pUv * 0.78 + vec2(drift, drift * 0.25);
          float c1 = fbm(uv1 * 0.82) * 0.72 + fbm(uv1 * 2.15 + vec2(3.4, 1.8)) * 0.28;
          float band1 = smoothstep(0.035, 0.16, y) * (1.0 - smoothstep(0.46, 0.74, y));
          float m1 = smoothstep(0.51, 0.61, c1) * band1;
          float lit1 = smoothstep(0.48, 0.66, fbm(uv1 * 0.82 + uSun.xz * 0.075) * 0.72 + fbm(uv1 * 2.15 + vec2(3.4, 1.8)) * 0.28);
          vec3 shade1 = mix(mix(uZenith, srgb(vec3(.62, .56, .66)), 0.55), mix(uHorizon, srgb(vec3(.78, .62, .62)), 0.55), 0.45 + 0.35 * anti);
          vec3 top1 = mix(mix(uSunTint, vec3(1.0, .92, .78), 0.55), vec3(1.0, .96, .88), lit1);
          vec3 cc1 = mix(shade1, top1, smoothstep(0.22, 0.78, lit1));
          float rim1 = smoothstep(0.50, 0.59, c1) * (1.0 - smoothstep(0.59, 0.70, c1));
          cc1 += uSunTint * (pow(s, 5.0) * 0.38 + pow(s, 12.0) * rim1 * 0.58);
          c = mix(c, cc1, m1 * 0.86 * cloudAlpha);

          #if SKY_OCT >= 3
          // Secondary lower broken cumulus puffs for storybook depth (Low/Med/High/Ultra)
          vec2 uv2 = pUv * 1.22 + vec2(-drift * 0.65 + 7.1, drift * 0.4 + 2.3);
          float c2 = fbm(uv2 * 0.95);
          float band2 = smoothstep(0.06, 0.22, y) * (1.0 - smoothstep(0.36, 0.60, y));
          float m2 = smoothstep(0.58, 0.67, c2) * band2;
          float lit2 = smoothstep(0.52, 0.69, fbm(uv2 * 0.95 + uSun.xz * 0.055));
          vec3 cc2 = mix(mix(uHorizon, srgb(vec3(.68, .58, .64)), 0.6), mix(uSunTint, vec3(1.0, .93, .80), 0.55), lit2);
          cc2 += uSunTint * pow(s, 6.0) * 0.32;
          c = mix(c, cc2, m2 * 0.68 * cloudAlpha);
          #endif
        }

        gl_FragColor = vec4(c, 1.);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(950, 32, 16), mat);
  mesh.frustumCulled = false; mesh.renderOrder = -1; mesh.name = 'sky';
  mesh.onBeforeRender = (_, __, camera) => mesh.position.copy(camera.position);
  return mesh;
}
