// Terrain: one analytic height function drives the mesh, the minimap and gameplay
// ground height, so what you see is exactly what you walk on.
import * as THREE from 'three';

export const SIZE = 520, HALF = SIZE / 2, WATER_Y = -0.5;

export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
export const lerp = (a, b, t) => a + (b - a) * t;
export const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };

export function hash(x, y) {
  let h = (Math.imul(x | 0, 374761393) + Math.imul(y | 0, 668265263)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967295;
}
export function noise(x, y) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = hash(xi, yi), b = hash(xi + 1, yi), c = hash(xi, yi + 1), d = hash(xi + 1, yi + 1);
  return (a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v) * 2 - 1;
}
export function fbm(x, y, oct = 4) {
  let s = 0, a = 0.5, f = 1;
  for (let i = 0; i < oct; i++) { s += a * noise(x * f, y * f); a *= 0.5; f *= 2.03; }
  return s;
}
export function rng(seed) {
  return () => {
    seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ---- world layout -------------------------------------------------------
export const riverZ = x => 72 + 14 * Math.sin(x * 0.021) + 6 * Math.sin(x * 0.057 + 1.3);
export const CANALS = [-45, -15, 15, 45];
export const OASIS = { x: -110, z: -20, r: 15 };
export const RUINS = { x: 160, z: -140 };
export const BRIDGE = { x: 0, halfW: 1.7, halfL: 10, deck: 0.55 };
export const SPAWN = { x: 0, z: -58 };

const PATHS = [
  [[0, -95], [0, 0]],
  [[0, 0], [0, 140]],
  [[0, 0], [-40, -8], [-80, -16], [-96, -19]],
  [[0, 0], [40, -10], [90, -26], [130, -34], [158, -90], [160, -128]],
  [[-75, 14], [75, 14]],
];
const SEGS = PATHS.flatMap(p => p.slice(1).map((b, i) => [p[i], b]));
export function pathDist(x, z) {
  let m = 1e9;
  for (const [[ax, az], [bx, bz]] of SEGS) {
    const dx = bx - ax, dz = bz - az;
    const t = clamp(((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz), 0, 1);
    const d = Math.hypot(x - ax - dx * t, z - az - dz * t);
    if (d < m) m = d;
  }
  return m;
}

// Farm plots between the village and the river, 15 × 10 m, bounded by canals.
// Returns -1 outside, 0..3 crop type, 4 for the earth bund between plots.
export function fieldPlot(x, z) {
  if (x < -75 || x > 75 || z < 16 || z > riverZ(x) - 8) return -1;
  const ex = (x + 75) % 15, ez = (z - 16) % 10;
  if (ex < 0.9 || ez < 0.7) return 4;
  return Math.floor(hash(Math.floor((x + 75) / 15) + 11, Math.floor((z - 16) / 10) + 7) * 4);
}

export function height(x, z) {
  let h = 1.6 + fbm(x * 0.011, z * 0.011) * 2.4;
  // desert dunes to the east
  const des = smooth(85, 150, x);
  if (des > 0) {
    const ridge = Math.sin(x * 0.045 + Math.sin(z * 0.03) * 2.2) * 0.5 + 0.5;
    h += des * (1.5 + 3 * ridge * ridge + fbm(x * 0.02, z * 0.02) * 2.5);
  }
  // mountains: north range plus a rim round the map edge, one snowy peak
  const edge = Math.max(Math.abs(x), Math.abs(z));
  const m = Math.max(smooth(125, 215, z), smooth(185, 252, edge));
  if (m > 0) {
    const r = 1 - Math.abs(noise(x * 0.012, z * 0.012));
    h += m * (28 + 55 * r * r + 14 * fbm(x * 0.03, z * 0.03));
  }
  h += 55 * Math.exp(-((x - 70) ** 2 + (z - 235) ** 2) / 3200);

  // flatten the places people live and farm
  const fx = 1 - smooth(70, 80, Math.abs(x));
  const fz = smooth(8, 14, z) * (1 - smooth(riverZ(x) - 10, riverZ(x) - 4, z));
  h = lerp(h, 1.0, fx * fz);
  const dv = Math.hypot(x, z);
  h = lerp(h, 1.3 + fbm(x * 0.05, z * 0.05) * 0.15, 1 - smooth(34, 50, dv));
  const dO = Math.hypot(x - OASIS.x, z - OASIS.z);
  h = lerp(h, 0.9, 1 - smooth(22, 40, dO));
  const dR = Math.hypot(x - RUINS.x, z - RUINS.z);
  h = lerp(h, 2.4, 1 - smooth(26, 40, dR));
  h -= 0.1 * (1 - smooth(1.5, 2.6, pathDist(x, z)));

  // carve water: river, irrigation canals, oasis pond
  h = lerp(-2.4, h, smooth(4.5, 9, Math.abs(z - riverZ(x))));
  for (const c of CANALS) {
    if (z > 15 && z < riverZ(c) + 2) h = lerp(-0.85, h, Math.max(smooth(0.9, 1.7, Math.abs(x - c)), 1 - smooth(16, 19, z)));
  }
  h = lerp(-2.2, h, smooth(OASIS.r * 0.6, OASIS.r, dO + fbm(x * 0.1, z * 0.1) * 2));
  return h;
}

export function onBridge(x, z) {
  return Math.abs(x - BRIDGE.x) < BRIDGE.halfW && Math.abs(z - riverZ(BRIDGE.x)) < BRIDGE.halfL;
}
export const groundAt = (x, z) => onBridge(x, z) ? Math.max(height(x, z), BRIDGE.deck) : height(x, z);

export function waterDist(x, z) {
  let d = Math.abs(z - riverZ(x)) - 6;
  d = Math.min(d, Math.hypot(x - OASIS.x, z - OASIS.z) - OASIS.r);
  if (z > 15 && z < riverZ(x)) for (const c of CANALS) d = Math.min(d, Math.abs(x - c) - 1);
  return Math.max(0, d);
}

// ---- colour ---------------------------------------------------------------
const hex = h => new THREE.Color().setHex(h, THREE.LinearSRGBColorSpace); // raw sRGB numbers
const P = {
  grassA: hex(0x6a8c34), grassB: hex(0x97aa4c), dry: hex(0xbba562), sand: hex(0xe3c48c), sand2: hex(0xcfa56d),
  dirt: hex(0xbc9a6a), village: hex(0xcaa877), mud: hex(0x6b5638), rock: hex(0x8c7c6c), rock2: hex(0x6a5f58),
  snow: hex(0xf4f1ec), bund: hex(0x9a8052),
  crops: [hex(0x5a8a28), hex(0xd8b85a), hex(0x8b6843), hex(0x4a7c26)],
};
export function colorAt(x, z, h, slope, c) {
  const n = fbm(x * 0.08, z * 0.08);
  c.copy(P.grassA).lerp(P.grassB, n * 0.5 + 0.5);
  c.lerp(P.dry, smooth(60, 110, x) * 0.8);
  const des = smooth(92, 138, x + fbm(x * 0.03, z * 0.03) * 15);
  if (des > 0) c.lerp(P.sand2.clone().lerp(P.sand, n * 0.5 + 0.5), des);
  c.lerp(P.village, 1 - smooth(22, 36, Math.hypot(x, z) + n * 5));
  c.lerp(P.sand2, 1 - smooth(18, 34, Math.hypot(x - RUINS.x, z - RUINS.z) + n * 5));
  const fp = fieldPlot(x, z);
  if (fp >= 0) c.copy(fp === 4 ? P.bund : P.crops[fp]).multiplyScalar(0.92 + n * 0.12);
  c.lerp(P.dirt, 1 - smooth(1.2, 2.5, pathDist(x, z) + n * 0.8));
  c.lerp(n > 0 ? P.rock : P.rock2, Math.max(smooth(0.55, 0.95, slope), smooth(9, 22, h)));
  c.lerp(P.snow, smooth(58, 72, h + n * 8));
  c.lerp(P.mud, 1 - smooth(-0.4, 0.35, h));
  return c;
}

// ---- meshes ---------------------------------------------------------------
export function buildTerrain() {
  const seg = 256, step = SIZE / seg, row = seg + 1;
  const geo = new THREE.PlaneGeometry(SIZE, SIZE, seg, seg);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position, H = new Float32Array(pos.count);
  for (let i = 0; i < pos.count; i++) { H[i] = height(pos.getX(i), pos.getZ(i)); pos.setY(i, H[i]); }
  const col = new Float32Array(pos.count * 3), c = new THREE.Color(), srgb = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) {
    const r = Math.floor(i / row), k = i % row;
    const hx = H[r * row + Math.min(k + 1, seg)] - H[r * row + Math.max(k - 1, 0)];
    const hz = H[Math.min(r + 1, seg) * row + k] - H[Math.max(r - 1, 0) * row + k];
    colorAt(pos.getX(i), pos.getZ(i), H[i], Math.hypot(hx, hz) / (2 * step), c);
    srgb.set([c.r, c.g, c.b], i * 3);
    c.convertSRGBToLinear();
    col.set([c.r, c.g, c.b], i * 3);
  }
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  geo.computeVertexNormals();
  const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95 }));
  mesh.receiveShadow = true;
  return { mesh, mapCanvas: mapImage(H, srgb, seg) };
}

// Top-down painted map (north = +z at the top) for the minimap and world map.
function mapImage(H, srgb, seg) {
  const n = seg + 1, cv = document.createElement('canvas');
  cv.width = cv.height = n;
  const ctx = cv.getContext('2d'), img = ctx.createImageData(n, n);
  for (let r = 0; r < n; r++) for (let k = 0; k < n; k++) {
    const i = r * n + k, o = ((n - 1 - r) * n + k) * 4, h = H[i];
    const shade = 1 + clamp((h - H[r * n + Math.max(k - 1, 0)]) * 0.12, -0.25, 0.25);
    let R = srgb[i * 3], G = srgb[i * 3 + 1], B = srgb[i * 3 + 2];
    if (h < WATER_Y) { const d = clamp((WATER_Y - h) / 2, 0, 1); R = lerp(0.42, 0.2, d); G = lerp(0.68, 0.48, d); B = lerp(0.72, 0.62, d); }
    img.data[o] = R * 255 * shade; img.data[o + 1] = G * 255 * shade; img.data[o + 2] = B * 255 * shade; img.data[o + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  return cv;
}
export const toMap = (x, z, size) => [(x + HALF) / SIZE * size, (HALF - z) / SIZE * size];

export function buildWater(sunDir) {
  const mat = new THREE.ShaderMaterial({
    transparent: true, fog: true,
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, {
      uTime: { value: 0 }, uSun: { value: sunDir.clone() },
      uDeep: { value: new THREE.Color(0x1f5a63) }, uShallow: { value: new THREE.Color(0x4f9b8e) }, uSky: { value: new THREE.Color(0xf2d6ae) },
    }]),
    vertexShader: `
      varying vec3 vW;
      #include <fog_pars_vertex>
      void main(){ vec4 w = modelMatrix * vec4(position,1.); vW = w.xyz;
        vec4 mvPosition = viewMatrix * w; gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }`,
    fragmentShader: `
      uniform float uTime; uniform vec3 uSun, uDeep, uShallow, uSky; varying vec3 vW;
      #include <common>
      #include <fog_pars_fragment>
      float wv(vec2 p){ return sin(p.x*.9+uTime*1.1)*.5 + sin(p.y*1.3-uTime*.9)*.35 + sin((p.x+p.y)*2.7+uTime*2.)*.12 + sin((p.x-p.y)*4.1-uTime*2.6)*.06; }
      void main(){
        vec2 p = vW.xz; float e = .05;
        vec3 n = normalize(vec3(-(wv(p+vec2(e,0.))-wv(p-vec2(e,0.)))*.9, 1., -(wv(p+vec2(0.,e))-wv(p-vec2(0.,e)))*.9));
        vec3 v = normalize(cameraPosition - vW);
        float fr = pow(1. - max(dot(n, v), 0.), 3.);
        vec3 col = mix(uShallow, uDeep, .55 + .25*sin(p.x*.05)*sin(p.y*.07));
        col = mix(col, uSky, fr*.65);
        float sp = pow(max(dot(reflect(-uSun, n), v), 0.), 160.);
        col += vec3(1., .86, .6) * sp * 2.2;
        gl_FragColor = vec4(col, .78 + fr*.2);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
        #include <fog_fragment>
      }`,
  });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(SIZE, SIZE, 1, 1).rotateX(-Math.PI / 2), mat);
  mesh.position.y = WATER_Y;
  return mesh;
}
