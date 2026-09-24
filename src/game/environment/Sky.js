// Painted toon sky: a warm golden-hour gradient (peach horizon → cream → soft blue), a
// glow and disc around the sun, and a few flat anime clouds with a lavender underside.
// One big back-faced sphere that follows the camera; no textures.
import * as THREE from 'three';

export function createSky(sunDir) {
  const mat = new THREE.ShaderMaterial({
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
      float fbm(vec2 p) { float s = 0., a = .5; for (int i = 0; i < 4; i++) { s += a * n(p); p *= 2.07; a *= .5; } return s; }
      vec3 srgb(vec3 c) { return pow(c, vec3(2.2)); }
      void main() {
        vec3 d = normalize(vDir); float y = max(d.y, 0.);
        vec3 c = mix(srgb(vec3(.965, .79, .56)), srgb(vec3(.97, .87, .68)), smoothstep(0., .1, y));
        c = mix(c, srgb(vec3(.87, .86, .8)), smoothstep(.08, .3, y));
        c = mix(c, srgb(vec3(.53, .68, .85)), smoothstep(.25, .75, y));
        float s = max(dot(d, uSun), 0.);
        c += srgb(vec3(1., .82, .55)) * (pow(s, 8.) * .35 + pow(s, 64.) * .5);
        c = mix(c, srgb(vec3(1., .96, .84)) * 1.6, smoothstep(.9985, .9992, s));      // sun disc
        // clouds on a flat layer above the valley
        if (d.y > .02) {
          vec2 uv = d.xz / (d.y + .08) * .9 + vec2(uTime * .004, 0.);
          float cl = fbm(uv * .8) * .75 + fbm(uv * 2.3 + 4.) * .25;
          float band = smoothstep(.05, .2, d.y) * (1. - smoothstep(.55, .8, d.y));
          float m = smoothstep(.56, .6, cl) * band;
          float lit = smoothstep(.56, .66, fbm(uv * .8 + (uSun.xz) * .06) * .75 + fbm(uv * 2.3 + 4.) * .25);
          vec3 cc = mix(srgb(vec3(.86, .78, .86)), srgb(vec3(1., .95, .86)), lit);
          cc += srgb(vec3(1., .8, .5)) * pow(s, 6.) * .4;
          c = mix(c, cc, m * .95);
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
