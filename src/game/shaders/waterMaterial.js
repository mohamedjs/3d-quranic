// 5-tier physically-grounded water shader with 4 distinct water personalities:
//  1. Nile river       — broad slow current, Beer-Lambert depth absorption from clear pebble/mud
//                        shallows to deep Nile green-teal, golden GGX sun-path sparkles
//  2. Canals           — muddy olive-green irrigation water with shaded banks & lively ripples
//  3. Oasis pond       — nearly calm, crystal-clear deep green-teal spring reflecting palms & sky
//  4. Street rill      — clear shallow running water over 3D sculpted river pebbles, brisk ripples
//
// Tiers (quality.js `waterMode`):
//  0 lite / 1 low : 1 normal fetch (512 water_nor) + 1 sky fetch + 1 bank fetch, Beer-Lambert alpha,
//                   Schlick Fresnel (F0=0.02), GGX sun glint, thin broken <6 cm shore meniscus
//  2 medium       : + 2 flow-advected normal layers (1024 water_nor) at distinct scales/angles + slow swell
//  3 high         : + half-res planar reflection (tReflect) distorted by wave normals
//  4 ultra        : + full-res planar reflection + 2048^2 bank map
import * as THREE from 'three';
import { AERIAL } from './stylizedPbr.js';
import { SKY_REFL, WARM_GRADE_GLSL } from '../lighting/environmentMap.js';

export const waterTime = { value: 0 };
export const streamWaterTier = { value: 0 };

export const WATER_TIERS = { lite: 0, low: 1, medium: 2, high: 3, ultra: 4 };

// 1x1 flat OpenGL normal placeholder (0, 0, 1) while water_nor.webp loads (never blocks or flashes black).
let phWaterNor;
function placeholderWaterNor() {
  if (!phWaterNor) {
    const t = new THREE.DataTexture(new Uint8Array([128, 128, 255, 255]), 1, 1, THREE.RGBAFormat);
    t.colorSpace = THREE.NoColorSpace;
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.minFilter = t.magFilter = THREE.LinearFilter;
    t.generateMipmaps = false;
    t.needsUpdate = true;
    phWaterNor = t;
  }
  return phWaterNor;
}

export const WATER_NOR = {
  tWaterNor: { value: placeholderWaterNor() },
  uHasWaterNor: { value: 0.0 },
};

export function setWaterNormal(tex) {
  WATER_NOR.tWaterNor.value = tex || placeholderWaterNor();
  WATER_NOR.uHasWaterNor.value = tex ? 1.0 : 0.0;
}

// Shared GLSL helpers: tiny value noise (shore foam breakup only), warm-graded equirect sky
// reflection (analytic fallback while loading), GGX sun specular, and unified linear aerial fog.
const WATER_HELPERS = /* glsl */`
  uniform float uTime;
  uniform sampler2D tWaterNor;
  uniform float uHasWaterNor;
  uniform sampler2D uSkyMap;
  uniform float uHasSkyMap;
  uniform vec3 uSunColor;
  uniform vec3 uAerialSunDir, uAerialWarm, uAerialCool, uAerialSunGlow;

  float wh(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float wn(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(wh(i), wh(i + vec2(1.0, 0.0)), f.x),
               mix(wh(i + vec2(0.0, 1.0)), wh(i + vec2(1.0, 1.0)), f.x), f.y);
  }

  ${WARM_GRADE_GLSL}

  // Warm-graded equirect HDRI sky reflection matching M1 Sky.js (analytic fallback while loading)
  vec3 sampleSkyRefl(vec3 rd, vec3 sunDir) {
    vec3 d = normalize(vec3(rd.x, max(abs(rd.y), 0.015), rd.z));
    float sd = dot(d, sunDir);
    float s = max(sd, 0.0);
    if (uHasSkyMap > 0.5) {
      vec2 uv = vec2(atan(d.z, d.x) * 0.15915494309 + 0.5, asin(clamp(d.y, -1.0, 1.0)) * 0.31830988618 + 0.5);
      float elevDeg = degrees(asin(clamp(d.y, 0.0, 1.0)));
      vec3 c = warmGrade(texture2D(uSkyMap, uv).rgb * 1.32, elevDeg);
      c += uSunColor * (pow(s, 8.0) * 0.14 + pow(s, 48.0) * 0.30);
      return c;
    }
    float y = d.y;
    float anti = pow(max(-sd, 0.0), 1.5);
    vec3 hor  = pow(vec3(0.969, 0.725, 0.420), vec3(2.2));
    vec3 low  = pow(vec3(0.969, 0.851, 0.659), vec3(2.2));
    vec3 mid  = pow(vec3(0.700, 0.795, 0.845), vec3(2.2));
    vec3 zen  = pow(vec3(0.302, 0.494, 0.659), vec3(2.2));
    vec3 rose = pow(vec3(0.790, 0.590, 0.640), vec3(2.2));
    vec3 c = mix(hor, low, smoothstep(0.0, 0.12, y));
    c = mix(c, mid, smoothstep(0.10, 0.36, y));
    c = mix(c, zen, smoothstep(0.30, 0.82, y));
    c = mix(c, rose, anti * (1.0 - smoothstep(0.06, 0.52, y)) * 0.48);
    c += uSunColor * (pow(s, 8.0) * 0.14 + pow(s, 48.0) * 0.30);
    return c;
  }

  // Sharp golden GGX sun specular path with soft highlight rolloff (sparkles without blowing out bloom)
  vec3 waterSunSpecular(vec3 N, vec3 V, vec3 sunDir, float rough, float strength) {
    vec3 H = normalize(sunDir + V);
    float ndh = max(dot(N, H), 0.0);
    float ndl = max(dot(N, sunDir), 0.0);
    float ndv = max(dot(N, V), 0.06);
    float vdh = max(dot(V, H), 0.0);
    float a = rough * rough;
    float a2 = a * a;
    float dDen = ndh * ndh * (a2 - 1.0) + 1.0;
    float D = a2 / (PI * dDen * dDen + 1e-5);
    float F = 0.02 + 0.98 * pow(1.0 - vdh, 5.0);
    float specRaw = D * F * ndl / max(4.0 * ndv * max(ndl, 0.08), 0.06);
    float spec = specRaw / (1.0 + specRaw * 0.38);
    float broad = pow(ndh, 32.0) * F * 0.42;
    vec3 coreCol = mix(uSunColor, vec3(1.0, 0.95, 0.84), clamp(spec * 0.25, 0.0, 0.50));
    return coreCol * (spec * 1.15 + broad) * strength;
  }

  // Unified pre-tonemap directional aerial-perspective fog (identical to stylizedPbr.js)
  vec3 applyAerialFog(vec3 col, vec3 wPos, float depth) {
    #ifdef USE_FOG
      vec3 aDir = normalize(wPos - cameraPosition);
      float aSun = clamp(dot(aDir, uAerialSunDir) * 0.5 + 0.5, 0.0, 1.0);
      vec3 aCol = mix(uAerialCool, uAerialWarm, smoothstep(0.18, 0.92, aSun));
      aCol += uAerialSunGlow * pow(max(dot(aDir, uAerialSunDir), 0.0), 5.0) * 0.12;
      float aLow = exp(-max(wPos.y + 1.5, 0.0) * 0.025);
      float aNear = max(fogNear, 25.0);
      float aDist = smoothstep(aNear, max(fogFar, aNear + 40.0), depth);
      float aFog = clamp(aDist * (0.82 + 0.12 * aLow), 0.0, 0.92);
      return mix(col, aCol, aFog);
    #else
      return col;
    #endif
  }
`;

// Main world water plane (Nile, Canals, Oasis Pond) across all 5 quality tiers.
export function createWaterMaterial({ size, mode = 'lite', lite = false } = {}) {
  const tier = typeof mode === 'string' && mode in WATER_TIERS ? WATER_TIERS[mode] : (lite ? 0 : 2);
  return new THREE.ShaderMaterial({
    fog: true,
    transparent: true,
    depthTest: true,
    depthWrite: false,
    defines: { WATER_TIER: tier },
    uniforms: {
      ...THREE.UniformsUtils.clone(THREE.UniformsLib.fog),
      tBank:          { value: null },
      tWaterNor:      WATER_NOR.tWaterNor,
      uHasWaterNor:   WATER_NOR.uHasWaterNor,
      tReflect:       { value: null },
      uHasReflect:    { value: 0.0 },
      uTexMatrix:     { value: new THREE.Matrix4() },
      uSize:          { value: size },
      uTime:          waterTime,
      uSkyMap:        SKY_REFL.uSkyMap,
      uHasSkyMap:     SKY_REFL.uHasSkyMap,
      uSunColor:      SKY_REFL.uSunColor,
      uAerialSunDir:  AERIAL.uAerialSunDir,
      uAerialWarm:    AERIAL.uAerialWarm,
      uAerialCool:    AERIAL.uAerialCool,
      uAerialSunGlow: AERIAL.uAerialSunGlow,
    },
    vertexShader: /* glsl */`
      uniform mat4 uTexMatrix;
      varying vec3 vW;
      #if WATER_TIER >= 3
        varying vec4 vReflUv;
      #endif
      #include <fog_pars_vertex>
      void main() {
        vec4 w = modelMatrix * vec4(position, 1.0);
        vW = w.xyz;
        #if WATER_TIER >= 3
          vReflUv = uTexMatrix * w;
        #endif
        vec4 mvPosition = viewMatrix * w;
        gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }`,
    fragmentShader: /* glsl */`
      uniform sampler2D tBank;
      uniform sampler2D tReflect;
      uniform float uHasReflect;
      uniform float uSize;
      varying vec3 vW;
      #if WATER_TIER >= 3
        varying vec4 vReflUv;
      #endif
      #include <common>
      #include <fog_pars_fragment>
      ${WATER_HELPERS}

      #if WATER_TIER >= 2
      // Variance-preserving 2-phase flow advection: scrolls along spatially varying flow vectors
      // without stretching over time or pulsing contrast during crossfades (k0^2 + k1^2 = 1).
      vec2 sampleFlowNor(vec2 baseUv, vec2 flow, float t, float period, float dist) {
        float ph0 = fract(t / period);
        float ph1 = fract(ph0 + 0.5);
        float u = sin(ph0 * PI);
        u *= u;
        float v = 1.0 - u;
        float inv = inversesqrt(u * u + v * v);
        vec2 n0 = texture2D(tWaterNor, baseUv - flow * ((ph0 - 0.5) * dist)).xy * 2.0 - 1.0;
        vec2 n1 = texture2D(tWaterNor, baseUv - flow * ((ph1 - 0.5) * dist)).xy * 2.0 - 1.0;
        return n0 * (u * inv) + n1 * (v * inv);
      }
      #endif

      void main() {
        vec2 p = vW.xz;
        vec4 b = texture2D(tBank, p / uSize + 0.5);
        float e = b.r;           // 0 at shoreline -> 1 mid-stream
        float depth = b.g;       // 0..1 normalized physical depth (0..2.2 m)
        float depthM = depth * 2.2;
        if (depthM <= 0.001) discard;

        float ang = (b.b - 0.5) * PI;
        vec2 bankDir = vec2(cos(ang), sin(ang));
        float kind = b.a;        // ~0.15 Oasis, ~0.55 Canal, ~0.95 Nile

        // Smooth personality weights
        float oasisW = 1.0 - smoothstep(0.22, 0.44, kind);
        float nileW  = smoothstep(0.68, 0.88, kind);
        float canalW = clamp(1.0 - oasisW - nileW, 0.0, 1.0);

        // Oasis uses a steady gentle breeze direction so its calm pond never shows an angle seam
        vec2 breezeDir = vec2(0.84, 0.54);
        vec2 flowDir = normalize(mix(bankDir, breezeDir, oasisW));
        float flowSpd = nileW * 0.48 + canalW * 0.62 + oasisW * 0.10;

        vec3 sunDir = normalize(uAerialSunDir);
        vec3 toCam = cameraPosition - vW;
        float camDist = length(toCam);
        vec3 V = toCam / max(camDist, 1e-4);
        float t = uTime;

        // Distance-faded FFT normal map ripples (zero shimmer or visible tiling at distance)
        float detailFade = 1.0 - smoothstep(18.0, 88.0, camDist);
        float swellFade  = 1.0 - smoothstep(48.0, 175.0, camDist);
        float shallowCalm = 0.50 + 0.50 * smoothstep(0.0, 0.25, depthM);
        float baseAmp = (nileW * 0.52 + canalW * 0.44 + oasisW * 0.16) * shallowCalm;

        #if WATER_TIER >= 2
          // Medium+: two flow-advected layers at distinct scales & angles + slow large swell
          mat2 R1 = mat2( 0.9563, -0.2924,  0.2924, 0.9563); // +17 deg
          mat2 R2 = mat2( 0.8387,  0.5446, -0.5446, 0.8387); // -33 deg
          mat2 R3 = mat2( 0.5446, -0.8387,  0.8387, 0.5446); // +57 deg
          mat2 R1T = mat2( 0.9563,  0.2924, -0.2924, 0.9563);
          mat2 R2T = mat2( 0.8387, -0.5446,  0.5446, 0.8387);
          mat2 R3T = mat2( 0.5446,  0.8387, -0.8387, 0.5446);

          vec2 flow1 = R1 * flowDir;
          vec2 crossFlow = mat2(0.9135, 0.4067, -0.4067, 0.9135) * flowDir; // -24 deg off flow
          vec2 flow2 = R2 * crossFlow;

          vec2 n1 = sampleFlowNor((R1 * p) / 3.8, flow1, t, 8.5, 1.35 * flowSpd);
          vec2 n2 = sampleFlowNor((R2 * p) / 1.85, flow2, t + 2.7, 6.0, 1.25 * flowSpd);
          vec2 n3 = texture2D(tWaterNor, (R3 * p) / 11.5 - (R3 * breezeDir) * (t * 0.016)).xy * 2.0 - 1.0;

          float w1 = nileW * 0.58 + canalW * 0.46 + oasisW * 0.42;
          float w2 = nileW * 0.42 + canalW * 0.58 + oasisW * 0.28;
          float w3 = nileW * 0.46 + canalW * 0.14 + oasisW * 0.20;
          vec2 slopeXZ = (R1T * n1 * w1 + R2T * n2 * w2) * detailFade + (R3T * n3 * w3) * swellFade;
          vec3 N = normalize(vec3(slopeXZ.x * baseAmp, 1.0, slopeXZ.y * baseAmp));
        #else
          // Lite / Low: strictly ONE normal fetch scrolling along the flow
          vec2 n0 = texture2D(tWaterNor, p / 3.2 - flowDir * (t * 0.11 * flowSpd)).xy * 2.0 - 1.0;
          float liteAmp = baseAmp * (0.28 + 0.72 * detailFade);
          vec3 N = normalize(vec3(n0.x * liteAmp, 1.0, n0.y * liteAmp));
        #endif

        // ---- Beer-Lambert depth absorption over the real M2 riverbed ----
        float flatNdv = max(V.y, 0.18);
        float cosT = sqrt(1.0 - (1.0 - flatNdv * flatNdv) * 0.5625); // Snell refraction (n = 1.333)
        float optDepth = depthM / cosT;

        // Per-body turbidity: clear shallow edges, murky olive canals, deep green-teal Nile & oasis
        float kExtinct = nileW * 1.95 + canalW * 3.10 + oasisW * 1.35;
        float Tbed = exp(-optDepth * kExtinct);

        // Naturalistic dark-linear water column colours (no flat cyan anywhere)
        vec3 nileShallow  = vec3(0.044, 0.094, 0.066);
        vec3 nileDeep     = vec3(0.008, 0.036, 0.036);
        vec3 canalShallow = vec3(0.058, 0.064, 0.025);
        vec3 canalDeep    = vec3(0.015, 0.029, 0.013);
        vec3 oasisShallow = vec3(0.026, 0.114, 0.092);
        vec3 oasisDeep    = vec3(0.006, 0.042, 0.050);

        vec3 cShallow = nileShallow * nileW + canalShallow * canalW + oasisShallow * oasisW;
        vec3 cDeep    = nileDeep    * nileW + canalDeep    * canalW + oasisDeep    * oasisW;
        vec3 bodyCol  = mix(cShallow, cDeep, 1.0 - exp(-optDepth * mix(1.30, 1.85, canalW)));

        // Subtle sunlit wave-body scattering + cozy bank-shadow occlusion along shaded canals
        float waveLight = 0.80 + 0.28 * max(dot(N, sunDir), 0.0);
        float sss = pow(max(dot(V, -sunDir + N * 0.35), 0.0), 4.0) * (0.14 * nileW + 0.18 * oasisW);
        bodyCol = bodyCol * waveLight + cShallow * sss;
        bodyCol *= 1.0 - canalW * (1.0 - smoothstep(0.0, 0.72, e)) * 0.22;

        // Keep M2's wet-bank darkening right along the damp pebble waterline
        float wetMargin = (1.0 - smoothstep(0.015, 0.22, depthM)) * (1.0 - oasisW * 0.65);
        bodyCol *= mix(1.0, 0.62, wetMargin);

        // ---- Schlick Fresnel (F0 = 0.02) + M1 Sky & Planar Reflections ----
        float ndv = clamp(dot(N, V), 0.0, 1.0);
        float fresnel = 0.02 + 0.98 * pow(1.0 - ndv, 5.0);
        vec3 R = reflect(-V, N);
        vec3 skyRefl = sampleSkyRefl(R, sunDir);

        #if WATER_TIER >= 3
          vec3 reflCol = skyRefl;
          if (uHasReflect > 0.5 && vReflUv.w > 0.05) {
            float distScale = clamp(vReflUv.w * 0.022, 0.18, 1.15);
            float warp = mix(0.32, 0.11, oasisW) * distScale;
            vec2 rUv = (vReflUv.xy + N.xz * warp) / vReflUv.w;
            float edgeX = smoothstep(0.002, 0.03, rUv.x) * smoothstep(0.002, 0.03, 1.0 - rUv.x);
            float edgeY = smoothstep(0.002, 0.03, rUv.y) * smoothstep(0.002, 0.03, 1.0 - rUv.y);
            vec3 planar = texture2D(tReflect, clamp(rUv, 0.002, 0.998)).rgb;
            reflCol = mix(skyRefl, planar, edgeX * edgeY * 0.96);
          }
        #else
          // Narrow canals reflect shaded grassy banks more than open sky when no planar pass exists
          float bankReflOcc = 1.0 - canalW * (1.0 - smoothstep(0.0, 0.85, e)) * 0.34;
          vec3 reflCol = skyRefl * bankReflOcc;
        #endif

        // ---- Sharp golden GGX sun specular path ----
        float shoreFade = smoothstep(0.002, 0.065, depthM);
        float rough = mix(0.145, 0.095, oasisW);
        rough = clamp(rough + smoothstep(18.0, 115.0, camDist) * 0.055, 0.08, 0.22);
        float specStrength = (nileW * 1.25 + oasisW * 0.80 + canalW * 0.60) * shoreFade;
        vec3 sunSpec = waterSunSpecular(N, V, sunDir, rough, specStrength);

        // ---- Thin broken foam / wet meniscus line strictly under ~6 cm depth ----
        float foamZone = smoothstep(0.004, 0.020, depthM) * (1.0 - smoothstep(0.030, 0.064, depthM));
        float foamNoise = wn(p * 4.4 - flowDir * (t * 0.22 * flowSpd));
        float foamBreak = smoothstep(0.46, 0.80, foamNoise + (N.x + N.z) * 0.35);
        float foamAmt = foamZone * foamBreak * (nileW * 0.28 + canalW * 0.20 + oasisW * 0.10);
        vec3 foamCol = mix(vec3(0.58, 0.60, 0.56), uSunColor * 0.72 + vec3(0.28), 0.45);

        // ---- Physically consistent alpha blend over real riverbed ----
        float bodyW = (1.0 - fresnel) * (1.0 - Tbed);
        float reflW = fresnel;
        float cov = clamp(bodyW + reflW, 0.0, 1.0);
        vec3 col = (bodyW * bodyCol + reflW * reflCol) / max(cov, 0.001);
        col = mix(col, foamCol, foamAmt);
        float alpha = clamp((cov + foamAmt * 0.45) * shoreFade, 0.0, 1.0);

        // Lift alpha subtly on bright sun sparkles so glints stay crisp even over clear shallows
        float specLuma = dot(sunSpec, vec3(0.2126, 0.7152, 0.0722));
        alpha = clamp(alpha + min(specLuma * 0.45, 0.58) * shoreFade, 0.0, 1.0);
        col += sunSpec;

        #ifdef USE_FOG
          col = applyAerialFog(col, vW, vFogDepth);
        #endif

        gl_FragColor = vec4(col, alpha);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

export function bindWater(mat, bankTex) {
  mat.uniforms.tBank.value = bankTex;
  mat.uniforms.uTime = waterTime;
  return mat;
}

// ---- Street Rill Shader (`stream_channel.glb` water ribbon) ---------------------------------
// Clear, brisk shallow running water over visible 3D sculpted river pebbles, matching the main
// water shader's FFT normal ripples, Schlick Fresnel sky reflection, and golden GGX sun glint.
let streamMat;
export function toonStreamWaterMaterial(width = 0.86) {
  if (streamMat) return streamMat;
  streamMat = new THREE.ShaderMaterial({
    fog: true,
    transparent: true,
    depthTest: true,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -1,
    polygonOffsetUnits: -1,
    uniforms: {
      ...THREE.UniformsUtils.clone(THREE.UniformsLib.fog),
      uTime:          waterTime,
      uTier:          streamWaterTier,
      uWidth:         { value: width },
      tWaterNor:      WATER_NOR.tWaterNor,
      uHasWaterNor:   WATER_NOR.uHasWaterNor,
      uSkyMap:        SKY_REFL.uSkyMap,
      uHasSkyMap:     SKY_REFL.uHasSkyMap,
      uSunColor:      SKY_REFL.uSunColor,
      uAerialSunDir:  AERIAL.uAerialSunDir,
      uAerialWarm:    AERIAL.uAerialWarm,
      uAerialCool:    AERIAL.uAerialCool,
      uAerialSunGlow: AERIAL.uAerialSunGlow,
    },
    vertexShader: /* glsl */`
      varying vec2 vUv;
      varying vec3 vW;
      #include <fog_pars_vertex>
      void main() {
        vUv = uv;
        vec4 w = vec4(position, 1.0);
        #ifdef USE_INSTANCING
          w = instanceMatrix * w;
        #endif
        w = modelMatrix * w;
        vW = w.xyz;
        vec4 mvPosition = viewMatrix * w;
        gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }`,
    fragmentShader: /* glsl */`
      uniform float uTier;
      uniform float uWidth;
      varying vec2 vUv;
      varying vec3 vW;
      #include <common>
      #include <fog_pars_fragment>
      ${WATER_HELPERS}

      void main() {
        float t = uTime;
        float e = 2.0 * min(vUv.x, 1.0 - vUv.x); // 0 at limestone curbs -> 1 at rill center
        vec2 p = vW.xz;
        vec3 sunDir = normalize(uAerialSunDir);
        vec3 toCam = cameraPosition - vW;
        float camDist = length(toCam);
        vec3 V = toCam / max(camDist, 1e-4);

        // Quick small ripples flowing continuously along the village street (world XZ = seamless across 4 m segments)
        float detailFade = 1.0 - smoothstep(14.0, 52.0, camDist);
        vec2 n1 = texture2D(tWaterNor, vec2(p.x / 0.85, (p.y - t * 0.62) / 0.85)).xy * 2.0 - 1.0;
        vec2 slopeXZ = n1;
        if (uTier >= 2.0) {
          mat2 R2 = mat2(0.8829, 0.4695, -0.4695, 0.8829); // -28 deg
          mat2 R2T = mat2(0.8829, -0.4695, 0.4695, 0.8829);
          vec2 q = R2 * vec2(p.x, p.y - t * 0.88);
          vec2 n2 = texture2D(tWaterNor, q / 0.46).xy * 2.0 - 1.0;
          slopeXZ = n1 * 0.62 + (R2T * n2) * 0.48;
        }
        float amp = (uTier >= 2.0 ? 0.54 : 0.40) * (0.28 + 0.72 * detailFade);
        vec3 N = normalize(vec3(slopeXZ.x * amp, 1.0, slopeXZ.y * amp));

        // Clear shallow Beer-Lambert absorption (~8 cm deep: 3D sculpted pebbles stay crisp underneath)
        float flatNdv = max(V.y, 0.22);
        float depthM = mix(0.035, 0.11, smoothstep(0.0, 0.55, e));
        float Tbed = exp(-(depthM / flatNdv) * 2.15);
        vec3 bodyCol = mix(vec3(0.044, 0.080, 0.058), vec3(0.022, 0.058, 0.048), smoothstep(0.1, 0.8, e));
        bodyCol *= 0.82 + 0.25 * max(dot(N, sunDir), 0.0);

        // Schlick Fresnel (F0 = 0.02) + M1 sky reflection + sharp golden GGX sun glints
        float ndv = clamp(dot(N, V), 0.0, 1.0);
        float fresnel = 0.02 + 0.98 * pow(1.0 - ndv, 5.0);
        vec3 skyRefl = sampleSkyRefl(reflect(-V, N), sunDir) * mix(0.74, 0.94, smoothstep(0.0, 0.45, e));
        float rough = clamp(0.135 + smoothstep(14.0, 52.0, camDist) * 0.05, 0.10, 0.22);
        vec3 sunSpec = waterSunSpecular(N, V, sunDir, rough, 1.05);

        // Delicate broken meniscus right against the limestone curbs (no cartoon white stripe)
        float curbEdge = 1.0 - smoothstep(0.02, 0.12, e);
        float curbBreak = smoothstep(0.45, 0.82, wn(vec2(p.y * 5.2 - t * 1.4, p.x * 6.0)) + (N.x + N.z) * 0.35);
        float foamAmt = curbEdge * curbBreak * 0.18;
        vec3 foamCol = mix(vec3(0.62, 0.64, 0.60), uSunColor * 0.70 + vec3(0.30), 0.42);

        float bodyW = (1.0 - fresnel) * (1.0 - Tbed);
        float reflW = fresnel;
        float cov = clamp(bodyW + reflW, 0.0, 1.0);
        vec3 col = (bodyW * bodyCol + reflW * skyRefl) / max(cov, 0.001);
        col = mix(col, foamCol, foamAmt);

        float specLuma = dot(sunSpec, vec3(0.2126, 0.7152, 0.0722));
        float alpha = clamp(cov + foamAmt * 0.35 + min(specLuma * 0.45, 0.55), 0.08, 0.94);
        col += sunSpec;

        #ifdef USE_FOG
          col = applyAerialFog(col, vW, vFogDepth);
        #endif

        gl_FragColor = vec4(col, alpha);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  streamMat.userData.noShadow = true;
  return streamMat;
}
