// Painterly golden-hour sky: Rayleigh/Mie-inspired gradient (apricot horizon #F7B96B ->
// cream #F7D9A8 -> cerulean zenith #4D7EA8, dusty rose opposite sun), glowing sun halo + disc,
// and two sculpted painterly cumulus layers + high cirrus wisps tiered by quality (2/3/4 oct).
// One big back-faced sphere that follows the camera; zero textures.
import * as THREE from 'three';

export function createSky(sunDir, octaves = 4) {
  const oct = typeof octaves === 'boolean' ? (octaves ? 2 : 4) : Math.max(2, Math.min(4, octaves | 0));
  const mat = new THREE.ShaderMaterial({
    defines: { SKY_OCT: oct },
    side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: { uSun: { value: sunDir.clone().normalize() }, uTime: { value: 0 } },
    vertexShader: /* glsl */`
      varying vec3 vDir;
      void main() { vDir = normalize(position); vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.); gl_Position = p.xyww; }`,
    fragmentShader: /* glsl */`
      uniform vec3 uSun; uniform float uTime; varying vec3 vDir;
      float h(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      float n(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
        return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y); }
      float fbm(vec2 p) {
        float s = 0., a = .5;
        for (int i = 0; i < SKY_OCT; i++) { s += a * n(p); p = p * 2.04 + vec2(13.7, 7.3); a *= .5; }
        return s * (.9375 / (1. - pow(.5, float(SKY_OCT))));
      }
      vec3 srgb(vec3 c) { return pow(c, vec3(2.2)); }
      void main() {
        vec3 d = normalize(vDir);
        float y = max(d.y, 0.);
        float sunDot = dot(d, uSun);
        float s = max(sunDot, 0.);
        float anti = pow(max(-sunDot, 0.), 1.5);

        // Rayleigh/Mie sky dome: apricot horizon -> warm cream -> soft azure -> cerulean zenith
        vec3 horizonApricot = srgb(vec3(.969, .725, .420)); // #F7B96B
        vec3 lowCream       = srgb(vec3(.969, .851, .659)); // #F7D9A8
        vec3 midSky         = srgb(vec3(.700, .795, .845));
        vec3 zenithCerulean = srgb(vec3(.302, .494, .659)); // #4D7EA8
        vec3 antiRose       = srgb(vec3(.790, .590, .640)); // dusty rose opposite sun
        vec3 antiLav        = srgb(vec3(.495, .520, .665)); // cool lavender above anti-sun

        vec3 c = mix(horizonApricot, lowCream, smoothstep(0.0, 0.11, y));
        c = mix(c, midSky, smoothstep(0.09, 0.34, y));
        c = mix(c, zenithCerulean, smoothstep(0.28, 0.82, y));

        // Belt of Venus / dusty rose glow opposite the low golden-hour sun
        vec3 oppCol = mix(antiRose, antiLav, smoothstep(0.04, 0.36, y));
        c = mix(c, oppCol, anti * (1.0 - smoothstep(0.06, 0.56, y)) * 0.58);

        // Below horizon: warm valley mist gradient so no harsh line shows beneath distant passes
        if (d.y < 0.0) {
          c = mix(horizonApricot, srgb(vec3(.82, .63, .42)), smoothstep(0.0, 0.25, -d.y));
        }

        // Mie forward scattering + broad golden aureole + crisp sun disc
        float horBoost = 1.0 - smoothstep(0.0, 0.45, y);
        c += srgb(vec3(1.0, .78, .44)) * (pow(s, 3.0) * .26 * (.55 + .45 * horBoost) + pow(s, 14.0) * .38 + pow(s, 84.0) * .55);
        c = mix(c, srgb(vec3(1.0, .97, .86)) * 1.85, smoothstep(.9986, .9994, s));

        // Painterly cloud deck (2 sculpted cumulus layers + high cirrus wisps)
        if (d.y > 0.015) {
          vec2 pUv = d.xz / (d.y + 0.11);
          float drift = uTime * 0.0032;

          // High cirrus wisps catching warm pink-gold upper sunlight
          vec2 wispUv = vec2(pUv.x * 0.55 + pUv.y * 0.22 + drift * 0.55, pUv.y * 2.1 - pUv.x * 0.35);
          float wisp = n(wispUv * 1.15) * 0.65 + n(wispUv * 2.7 + 3.1) * 0.35;
          float wispBand = smoothstep(0.14, 0.38, y) * (1.0 - smoothstep(0.72, 0.96, y));
          float wispMask = smoothstep(0.56, 0.78, wisp) * wispBand * 0.36;
          vec3 wispCol = mix(srgb(vec3(.97, .82, .74)), srgb(vec3(1.0, .94, .82)), smoothstep(-0.3, 0.8, sunDot));
          c = mix(c, wispCol, wispMask);

          // Primary sculpted painterly cumulus layer
          vec2 uv1 = pUv * 0.78 + vec2(drift, drift * 0.25);
          float c1 = fbm(uv1 * 0.82) * 0.72 + fbm(uv1 * 2.15 + vec2(3.4, 1.8)) * 0.28;
          float band1 = smoothstep(0.035, 0.16, y) * (1.0 - smoothstep(0.46, 0.74, y));
          float m1 = smoothstep(0.51, 0.61, c1) * band1;
          float lit1 = smoothstep(0.48, 0.66, fbm(uv1 * 0.82 + uSun.xz * 0.075) * 0.72 + fbm(uv1 * 2.15 + vec2(3.4, 1.8)) * 0.28);
          vec3 shade1 = mix(srgb(vec3(.59, .54, .66)), srgb(vec3(.78, .62, .64)), 0.45 + 0.35 * anti);
          vec3 top1 = mix(srgb(vec3(1.0, .92, .78)), srgb(vec3(1.0, .97, .89)), lit1);
          vec3 cc1 = mix(shade1, top1, smoothstep(0.22, 0.78, lit1));
          // Silver-lining sun rim on cumulus edges near the sun
          float rim1 = smoothstep(0.50, 0.59, c1) * (1.0 - smoothstep(0.59, 0.70, c1));
          cc1 += srgb(vec3(1.0, .82, .48)) * (pow(s, 5.0) * 0.42 + pow(s, 12.0) * rim1 * 0.65);
          c = mix(c, cc1, m1 * 0.90);

          #if SKY_OCT >= 3
          // Secondary lower broken cumulus puffs for storybook depth (Low/Med/High/Ultra)
          vec2 uv2 = pUv * 1.22 + vec2(-drift * 0.65 + 7.1, drift * 0.4 + 2.3);
          float c2 = fbm(uv2 * 0.95);
          float band2 = smoothstep(0.06, 0.22, y) * (1.0 - smoothstep(0.36, 0.60, y));
          float m2 = smoothstep(0.58, 0.67, c2) * band2;
          float lit2 = smoothstep(0.52, 0.69, fbm(uv2 * 0.95 + uSun.xz * 0.055));
          vec3 cc2 = mix(srgb(vec3(.70, .59, .64)), srgb(vec3(1.0, .93, .80)), lit2);
          cc2 += srgb(vec3(1.0, .80, .46)) * pow(s, 6.0) * 0.35;
          c = mix(c, cc2, m2 * 0.72);
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
