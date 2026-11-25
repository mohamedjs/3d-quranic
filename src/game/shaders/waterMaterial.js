// 5-tier painterly-naturalistic water shader with 4 distinct water personalities:
//  1. Nile river       — broad emerald-teal current, warm shallow sandy bed, golden sun-path glints
//  2. Canals           — shaded mossy olive-emerald irrigation water with snug stone-quay depth
//  3. Oasis pond       — calm mirror-like turquoise spring reflecting palms & golden sky
//  4. Street rill      — transparent sparkling shallow water flowing over 3D sculpted river pebbles
//
// Tiers (quality.js `waterMode`):
//  0 lite   : depth-absorbed bands + shoreline foam + golden-hour Fresnel sky sheen + aerial fog
//  1 low    : + animated shoreline foam + flowing sun glints
//  2 medium : + dual scrolling wave normals + analytic golden-hour sky reflection + shore wetness
//  3 high   : + half-res planar reflection (tReflect) + sunlit underwater caustics
//  4 ultra  : + full-res planar reflection + 3-oct normals + refracted riverbed pebble detail
import * as THREE from 'three';
import { AERIAL } from './stylizedPbr.js';

export const waterTime = { value: 0 };
export const streamWaterTier = { value: 0 };

export const WATER_TIERS = { lite: 0, low: 1, medium: 2, high: 3, ultra: 4 };

// Shared GLSL helpers: noise, dual/triple wave-normal perturbation, analytic golden-hour sky
// reflection (matched to Sky.js), animated caustics, and linear pre-tonemap directional aerial fog.
const WATER_HELPERS = /* glsl */`
  uniform float uTime;
  uniform vec3 uAerialSunDir, uAerialWarm, uAerialCool, uAerialSunGlow;

  float wh(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float wn(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(wh(i), wh(i + vec2(1.0, 0.0)), f.x),
               mix(wh(i + vec2(0.0, 1.0)), wh(i + vec2(1.0, 1.0)), f.x), f.y);
  }
  float wfbm(vec2 p) { return wn(p) * 0.62 + wn(p * 2.07 + vec2(5.3, 2.7)) * 0.38; }

  // Organic rotated-ridge sunlit caustic webs (zero grid/zigzag artifacts, High/Ultra + rill)
  float caustic(vec2 p, float t) {
    mat2 r1 = mat2(0.80, -0.60, 0.60, 0.80);
    mat2 r2 = mat2(0.54,  0.84, -0.84, 0.54);
    vec2 w = vec2(wn(p * 0.65 + vec2(t * 0.18, -t * 0.14)), wn(p * 0.65 + vec2(-t * 0.15, t * 0.21) + 4.7)) - 0.5;
    vec2 p1 = r1 * (p * 1.15 + w * 0.95) + vec2(t * 0.26, -t * 0.21);
    vec2 p2 = r2 * (p * 1.62 - w * 0.85) + vec2(-t * 0.22, t * 0.29);
    float c1 = 1.0 - abs(wn(p1) * 2.0 - 1.0);
    float c2 = 1.0 - abs(wn(p2) * 2.0 - 1.0);
    return pow(clamp(c1 * c2, 0.0, 1.0), 3.4);
  }

  // Analytic golden-hour sky reflection matching Sky.js (apricot horizon -> cream -> cerulean zenith + sun)
  vec3 sampleSkyRefl(vec3 rd, vec3 sunDir) {
    float y = max(rd.y, 0.0);
    float sd = dot(rd, sunDir);
    float s = max(sd, 0.0);
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
    c += pow(vec3(1.0, 0.80, 0.48), vec3(2.2)) * (pow(s, 7.0) * 0.18 + pow(s, 48.0) * 0.45);
    return c;
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
    defines: { WATER_TIER: tier },
    uniforms: THREE.UniformsUtils.merge([
      THREE.UniformsLib.fog,
      {
        tBank:          { value: null },
        tReflect:       { value: null },
        uHasReflect:    { value: 0.0 },
        uTexMatrix:     { value: new THREE.Matrix4() },
        uSize:          { value: size },
        uTime:          waterTime,
        uAerialSunDir:  AERIAL.uAerialSunDir,
        uAerialWarm:    AERIAL.uAerialWarm,
        uAerialCool:    AERIAL.uAerialCool,
        uAerialSunGlow: AERIAL.uAerialSunGlow,
      },
    ]),
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

      // Compute procedural water wave normal in world space along flow vector
      vec3 waveNormal(vec2 p, vec2 dir, vec2 perp, float flowSpd, float amp, float t) {
        vec2 fUv = vec2(dot(p, perp), dot(p, dir));
        // Primary swell + secondary cross-ripple
        vec2 uv1 = fUv * vec2(1.15, 0.55) - vec2(0.0, t * 0.55 * flowSpd);
        vec2 uv2 = vec2(fUv.x * 1.9 + fUv.y * 0.85, fUv.y * 1.6 - fUv.x * 0.7) + vec2(t * 0.32, -t * 0.42 * flowSpd);
        float e = 0.08;
        float h0 = wn(uv1) * 0.6 + wn(uv2) * 0.4;
        float hx = wn(uv1 + vec2(e, 0.0)) * 0.6 + wn(uv2 + vec2(e, 0.0)) * 0.4;
        float hy = wn(uv1 + vec2(0.0, e)) * 0.6 + wn(uv2 + vec2(0.0, e)) * 0.4;
        #if WATER_TIER >= 4
          // Ultra: fine 3rd wind-capillary octave for crisp sunlit micro-glints
          vec2 uv3 = p * 3.4 + vec2(-t * 0.65, t * 0.48);
          h0 += wn(uv3) * 0.22;
          hx += wn(uv3 + vec2(e, 0.0)) * 0.22;
          hy += wn(uv3 + vec2(0.0, e)) * 0.22;
        #endif
        float gx = (h0 - hx) / e;
        float gy = (h0 - hy) / e;
        vec2 wGrad = perp * gx + dir * gy;
        return normalize(vec3(wGrad.x * amp, 1.0, wGrad.y * amp));
      }

      void main() {
        vec2 p = vW.xz;
        vec4 b = texture2D(tBank, p / uSize + 0.5);
        float e = b.r;           // 0 at bank -> 1 mid-stream
        float depth = b.g;       // 0..1 normalized physical depth (0..2.2 m)
        float ang = (b.b - 0.5) * PI;
        vec2 dir = vec2(cos(ang), sin(ang));
        vec2 perp = vec2(-dir.y, dir.x);
        float kind = b.a;        // ~0.15 Oasis, ~0.55 Canal, ~0.95 Nile

        // Smooth personality weights
        float oasisW = 1.0 - smoothstep(0.22, 0.44, kind);
        float nileW  = smoothstep(0.68, 0.88, kind);
        float canalW = clamp(1.0 - oasisW - nileW, 0.0, 1.0);
        float flowSpd = mix(0.22, mix(0.62, 0.95, nileW), 1.0 - oasisW);

        // 3 distinct linear-space water palettes (Nile emerald-teal, Canal mossy-emerald, Oasis turquoise)
        vec3 nileShallow  = vec3(0.135, 0.505, 0.395);
        vec3 nileMid      = vec3(0.024, 0.225, 0.240);
        vec3 nileDeep     = vec3(0.008, 0.072, 0.105);

        vec3 canalShallow = vec3(0.115, 0.285, 0.165);
        vec3 canalMid     = vec3(0.022, 0.155, 0.135);
        vec3 canalDeep    = vec3(0.009, 0.056, 0.062);

        vec3 oasisShallow = vec3(0.205, 0.695, 0.605);
        vec3 oasisMid     = vec3(0.018, 0.370, 0.385);
        vec3 oasisDeep    = vec3(0.008, 0.128, 0.205);

        vec3 cShallow = nileShallow * nileW + canalShallow * canalW + oasisShallow * oasisW;
        vec3 cMid     = nileMid     * nileW + canalMid     * canalW + oasisMid     * oasisW;
        vec3 cDeep    = nileDeep    * nileW + canalDeep    * canalW + oasisDeep    * oasisW;

        // Warm sunlit sandy riverbed / mossy canal bed tint visible in the shallow margin
        vec3 bedCol = mix(vec3(0.27, 0.19, 0.09), vec3(0.16, 0.13, 0.07), canalW);
        bedCol = mix(bedCol, vec3(0.38, 0.30, 0.16), oasisW);

        vec3 sunDir = normalize(uAerialSunDir);
        vec3 V = normalize(cameraPosition - vW);
        float t = uTime;

        // ---- Surface normal (flat+gentle on Lite/Low, dual/triple scrolling normals on Med–Ultra) ----
        #if WATER_TIER >= 2
          float waveAmp = mix(0.11, mix(0.075, 0.032, oasisW), 1.0 - nileW);
          vec3 N = waveNormal(p, dir, perp, flowSpd, waveAmp, t);
          #if WATER_TIER >= 3
            // Oasis gentle concentric spring ripples around (-110, -20)
            if (oasisW > 0.05) {
              vec2 oc = p - vec2(-110.0, -20.0);
              float od = length(oc);
              float ring = cos(od * 2.4 - t * 1.1) * exp(-od * 0.06) * 0.035 * oasisW;
              vec2 orad = oc / max(od, 0.01);
              N = normalize(N + vec3(orad.x * ring, 0.0, orad.y * ring));
            }
          #endif
        #elif WATER_TIER == 1
          float rip = (wn(vec2(dot(p, perp) * 1.4, dot(p, dir) * 0.7 - t * 0.45 * flowSpd)) - 0.5) * 0.11;
          vec3 N = normalize(vec3(perp.x * rip, 1.0, perp.y * rip));
        #else
          vec3 N = vec3(0.0, 1.0, 0.0);
        #endif

        // ---- Beer-Lambert depth absorption + shallow shore bed + caustics ----
        float dEff = clamp(max(depth, e * 0.55), 0.0, 1.0);
        #if WATER_TIER >= 4
          // Ultra: refract riverbed sample coordinates by wave normal scaled by shallow clarity
          vec2 refractP = p + N.xz * (0.28 * (1.0 - dEff));
          float pebbles = wn(refractP * 5.2) * 0.6 + wn(refractP * 11.5 + 3.1) * 0.4;
          bedCol *= 0.80 + 0.42 * pebbles;
        #endif

        vec3 bodyCol = mix(cShallow, cMid, smoothstep(0.08, 0.42, dEff));
        bodyCol = mix(bodyCol, cDeep, smoothstep(0.36, 0.88, dEff));

        // Shore transparency / riverbed peek right at the shallow edge (e < 0.25)
        float shallowReveal = (1.0 - smoothstep(0.02, 0.28, depth)) * (1.0 - smoothstep(0.05, 0.45, e));
        bodyCol = mix(bodyCol, mix(bedCol, cShallow, 0.45), shallowReveal * 0.62);

        // Subtle cozy bank-shadow occlusion along narrow shaded canals
        bodyCol *= 1.0 - canalW * (1.0 - smoothstep(0.0, 0.65, e)) * 0.24;

        #if WATER_TIER >= 3
          // Animated golden underwater caustics dancing on shallow Nile, canal, and oasis beds
          vec2 caustP = p;
          #if WATER_TIER >= 4
            caustP = refractP;
          #endif
          float cVis = (1.0 - smoothstep(0.18, 0.78, dEff)) * smoothstep(0.02, 0.14, e);
          float cVal = caustic(caustP * mix(0.75, 1.10, canalW + oasisW * 0.4), t * (0.65 + 0.35 * flowSpd));
          bodyCol += vec3(0.95, 0.84, 0.52) * cVal * cVis * mix(0.42, 0.58, oasisW);
        #endif

        // ---- Sky & Planar Reflection blended by Schlick Fresnel ----
        float ndv = clamp(dot(N, V), 0.0, 1.0);
        float f0 = mix(0.04, mix(0.03, 0.07, oasisW), 1.0 - nileW);
        float fresnel = f0 + (1.0 - f0) * pow(1.0 - ndv, 4.2);
        // Balanced reflection so jewel emerald/turquoise water color always glows beneath sky/palm reflections
        float reflStrength = fresnel * mix(0.62, mix(0.46, 0.72, oasisW), 1.0 - nileW);
        #if WATER_TIER == 0
          // Lite: clean painterly Fresnel sky sheen while keeping rich emerald/turquoise jewel depth
          vec3 skyRefl = sampleSkyRefl(reflect(-V, N), sunDir);
          vec3 col = mix(bodyCol, skyRefl, clamp(reflStrength * 0.58 + oasisW * 0.05, 0.05, mix(0.48, 0.40, oasisW)));
        #elif WATER_TIER == 1
          vec3 skyRefl = sampleSkyRefl(reflect(-V, N), sunDir);
          vec3 col = mix(bodyCol, skyRefl, clamp(reflStrength * 0.70 + oasisW * 0.10, 0.06, 0.56));
        #elif WATER_TIER == 2
          vec3 skyRefl = sampleSkyRefl(reflect(-V, N), sunDir);
          vec3 col = mix(bodyCol, skyRefl, clamp(reflStrength * 0.74 + oasisW * 0.12, 0.08, 0.62));
        #else
          // High & Ultra: real planar reflection of palms, houses, bridges, backdrop hills & golden sky!
          vec3 skyRefl = sampleSkyRefl(reflect(-V, N), sunDir);
          vec3 reflCol = skyRefl;
          if (uHasReflect > 0.5 && vReflUv.w > 0.05) {
            float distFade = clamp(vReflUv.w * 0.025, 0.25, 1.35);
            float warp = mix(0.42, 0.16, oasisW) * distFade;
            vec2 rUv = (vReflUv.xy + N.xz * warp) / vReflUv.w;
            float inBounds = step(0.002, rUv.x) * step(rUv.x, 0.998) * step(0.002, rUv.y) * step(rUv.y, 0.998);
            vec3 planar = texture2D(tReflect, clamp(rUv, 0.002, 0.998)).rgb;
            reflCol = mix(skyRefl, planar, inBounds * 0.94);
          }
          // Calm oasis pond shows crisp upside-down palm & sky reflection while preserving turquoise glow
          float mirrorFloor = oasisW * 0.34 + nileW * 0.14 + canalW * 0.10;
          vec3 col = mix(bodyCol, reflCol, clamp(reflStrength * 0.80 + mirrorFloor, 0.10, 0.78));
        #endif

        // ---- Golden-hour sun-path glints & current shimmer ----
        vec3 R = reflect(-V, N);
        float rSun = max(dot(R, sunDir), 0.0);
        vec3 sunGold = vec3(1.0, 0.83, 0.45);
        #if WATER_TIER == 0
          // Lite: subtle warm sun sheen on the Nile & oasis without bleaching the pond
          float litePath = pow(rSun, 36.0) * (0.42 * nileW + 0.28 * oasisW + 0.15 * canalW);
          col += sunGold * litePath;
        #else
          float along = dot(p, dir), across = dot(p, perp);
          float glintNoise = wn(vec2(across * 2.8, along * 0.65 - t * 0.95 * flowSpd));
          float sharpSpec = pow(rSun, mix(96.0, 180.0, oasisW)) * (0.65 + 1.05 * glintNoise);
          float broadSheen = pow(rSun, 32.0) * 0.14;
          // Nile gets the richest golden sun-path sparkles; oasis stays jewel-clear; canals dappled
          float sunWeight = nileW * 1.15 + oasisW * 0.62 + canalW * 0.48;
          col += sunGold * (sharpSpec * 1.35 + broadSheen) * sunWeight * smoothstep(0.05, 0.25, e);
          // Delicate sunlit current ribbons on Nile & canals
          float ribbon = smoothstep(0.68, 0.84, wfbm(vec2(across * 2.4, (along - t * 1.05 * flowSpd) * 0.24)));
          col += vec3(0.96, 0.91, 0.74) * ribbon * smoothstep(0.22, 0.55, e) * (0.14 * nileW + 0.10 * canalW);
        #endif

        // ---- Delicate lacy shoreline foam & gentle wave lap ----
        vec3 foamCol = vec3(0.94, 0.96, 0.90);
        #if WATER_TIER == 0
          float fn0 = wn(p * 2.2);
          float foamLine = (1.0 - smoothstep(0.015, 0.080, e + (fn0 - 0.5) * 0.035)) * mix(0.56, 0.38, oasisW);
          col = mix(col, foamCol, foamLine);
        #else
          float fn = wfbm(p * 2.6 + vec2(t * 0.22 * flowSpd, -t * 0.16));
          float lap = sin(e * 32.0 - t * (1.8 + flowSpd) + fn * 5.0) * 0.5 + 0.5;
          float shoreEdge = (1.0 - smoothstep(0.012, 0.072, e + (fn - 0.5) * 0.055)) * (0.65 + 0.35 * fn);
          float innerRipple = smoothstep(0.065, 0.115, e) * (1.0 - smoothstep(0.115, 0.185, e)) * smoothstep(0.62, 0.90, lap) * 0.24;
          float foamAmt = clamp(max(shoreEdge * mix(0.62, 0.42, oasisW), innerRipple * (1.0 - oasisW * 0.65)), 0.0, 0.68);
          col = mix(col, foamCol, foamAmt);
        #endif

        // Unified pre-tonemap directional aerial-perspective fog
        #ifdef USE_FOG
          col = applyAerialFog(col, vW, vFogDepth);
        #endif

        gl_FragColor = vec4(col, 1.0);
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
// Transparent, sparkling shallow clear stream over visible 3D sculpted river pebbles!
// Single shared material whose `uTier` uniform tracks `preset.waterMode` (0..4) dynamically.
let streamMat;
export function toonStreamWaterMaterial(width = 0.86) {
  if (streamMat) return streamMat;
  streamMat = new THREE.ShaderMaterial({
    fog: true,
    transparent: true,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -1,
    polygonOffsetUnits: -1,
    uniforms: THREE.UniformsUtils.merge([
      THREE.UniformsLib.fog,
      {
        uTime:          waterTime,
        uTier:          streamWaterTier,
        uWidth:         { value: width },
        uAerialSunDir:  AERIAL.uAerialSunDir,
        uAerialWarm:    AERIAL.uAerialWarm,
        uAerialCool:    AERIAL.uAerialCool,
        uAerialSunGlow: AERIAL.uAerialSunGlow,
      },
    ]),
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
        float e = 2.0 * min(vUv.x, 1.0 - vUv.x); // 0 at stone curbs -> 1 at rill center
        vec2 flowUv = vec2(vUv.x * uWidth, vUv.y);
        vec3 sunDir = normalize(uAerialSunDir);
        vec3 V = normalize(cameraPosition - vW);

        // Brisk shallow ripple normal flowing along the village street
        vec2 r1 = vec2(flowUv.x * 4.2, flowUv.y * 1.45 - t * 1.65);
        vec2 r2 = vec2(flowUv.x * 6.5 + 1.7, flowUv.y * 2.2 - t * 2.35);
        float h0 = wn(r1) * 0.65 + wn(r2) * 0.35;
        float hx = wn(r1 + vec2(0.12, 0.0)) * 0.65 + wn(r2 + vec2(0.12, 0.0)) * 0.35;
        float hz = wn(r1 + vec2(0.0, 0.12)) * 0.65 + wn(r2 + vec2(0.0, 0.12)) * 0.35;
        float amp = uTier >= 2.0 ? 0.24 : 0.14;
        vec3 N = normalize(vec3((h0 - hx) * amp * 4.5, 1.0, (h0 - hz) * amp * 4.5));

        // Clear sunlit aqua-jade rill water (semi-transparent so 3D pebbles beneath shine through!)
        vec3 rillEdge = vec3(0.18, 0.56, 0.48);
        vec3 rillMid  = vec3(0.06, 0.34, 0.34);
        vec3 col = mix(rillEdge, rillMid, smoothstep(0.12, 0.78, e));

        // Crisp sky reflection + Schlick Fresnel sparkle
        float ndv = clamp(dot(N, V), 0.0, 1.0);
        float fresnel = 0.08 + 0.92 * pow(1.0 - ndv, 3.2);
        vec3 skyRefl = sampleSkyRefl(reflect(-V, N), sunDir);
        col = mix(col, skyRefl, clamp(fresnel * (uTier >= 2.0 ? 0.85 : 0.62), 0.12, 0.82));

        // Dancing sunlit caustics + sparkling current glints
        float cSpark = caustic(vec2(flowUv.x * 2.2, flowUv.y * 1.2 - t * 0.85), t * 1.25);
        vec3 R = reflect(-V, N);
        float spec = pow(max(dot(R, sunDir), 0.0), 48.0) * (0.7 + 0.8 * h0);
        float streaks = smoothstep(0.66, 0.86, wn(vec2(flowUv.x * 6.0, flowUv.y * 0.75 - t * 2.1)));
        col += vec3(1.0, 0.92, 0.66) * (spec * 1.35 + cSpark * (uTier >= 2.0 ? 0.55 : 0.30) + streaks * 0.28);

        // Delicate white bubbly foam kissing both limestone curbs
        float edgeWob = (wn(vec2(vUv.y * 3.8 - t * 1.4, vUv.x * 5.0)) - 0.5) * 0.10;
        float foam = (1.0 - smoothstep(0.04, 0.20, e + edgeWob)) * 0.85;
        col = mix(col, vec3(0.95, 0.98, 0.96), foam);

        // Clear enough in center to reveal colorful submerged 3D pebbles, crisper at Fresnel glints & curb foam
        float alpha = clamp(mix(0.46, 0.62, e) + fresnel * 0.28 + foam * 0.34 + spec * 0.36, 0.44, 0.95);
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
