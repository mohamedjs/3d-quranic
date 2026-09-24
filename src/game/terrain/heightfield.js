// Heightfield: one analytic height function drives the terrain mesh, the minimap,
// vegetation placement and gameplay ground height — what you see is what you walk on.
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
// the village street: a lane from the south into the square, a stream channel beside it
export const STREET = { z0: -54, z1: -12, channelX: -3.3 };
// title-screen lookout: a grassy hill south-west of the village, looking over it
export const LOOKOUT = { x: -33, z: -80, facing: Math.atan2(33, 58) };

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

// Irrigation canals (ترع) running beside the roads — water along every path out of the village.
export const ROAD_CANALS = [
  [[5, -95], [5, -57]],                                   // beside the south road, up to the street
  [[-42, -3.9], [-80, -11.5], [-94, -14.5]],              // beside the west road toward the oasis
  [[42, -14.5], [90, -30.5], [130, -38.5]],               // beside the east road
  [[4, 17], [4, 58]],                                     // beside the north road through the fields to the river
];
const CSEGS = ROAD_CANALS.flatMap(p => p.slice(1).map((b, i) => [p[i], b]));
export function canalDist(x, z) {
  let m = 1e9;
  for (const [[ax, az], [bx, bz]] of CSEGS) {
    const dx = bx - ax, dz = bz - az, t = clamp(((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz), 0, 1);
    m = Math.min(m, Math.hypot(x - ax - dx * t, z - az - dz * t));
  }
  return m;
}
// footbridges across the road canals: { x, z, rot } (rot: plank direction across the water)
export const FOOTBRIDGES = [{ x: 5, z: -76, rot: 0 }, { x: -65, z: -8.5, rot: Math.PI / 2 - 0.19 }, { x: 70, z: -23.8, rot: Math.PI / 2 + 0.32 }, { x: 4, z: 40, rot: 0 }];
export const FOOTBRIDGE_DECK = 1.1;   // plank top height (the plain sits near 1.0)

// Farm plots, 15 × 10 m, over the whole plain except the village, street, oasis, ruins,
// lookout hill, river banks and hills. -1 outside, 0 berseem (clover) · 1 wheat · 2 maize ·
// 3 young greens, 4 for the earth bund between plots.
export function fieldPlot(x, z) {
  if (Math.abs(x) > 205 || z < -150 || z > 150) return -1;
  if (Math.hypot(x, z) < 46 || (Math.abs(x) < 16 && z > -60 && z < -8)) return -1;       // village + street
  if (Math.hypot(x - OASIS.x, z - OASIS.z) < 42 || Math.hypot(x - RUINS.x, z - RUINS.z) < 42) return -1;
  if (Math.hypot(x - LOOKOUT.x, z - LOOKOUT.z) < 30 || Math.abs(z - riverZ(x)) < 11) return -1;
  if (pathDist(x, z) < 3.2 || canalDist(x, z) < 3.6) return -1;                         // road verge, canal banks
  if (Math.max(smooth(118, 150, z), smooth(170, 200, Math.max(Math.abs(x), Math.abs(z)))) > 0.2) return -1;
  const ex = ((x + 1000) % 15), ez = ((z + 1000) % 10);
  if (ex < 0.9 || ez < 0.7) return 4;
  return Math.floor(hash(Math.floor((x + 1000) / 15) + 11, Math.floor((z + 1000) / 10) + 7) * 4);
}

export function height(x, z) {
  let h = 1.6 + fbm(x * 0.011, z * 0.011) * 2.4;
  // soft green hills to the north and round the edge of the valley
  const edge = Math.max(Math.abs(x), Math.abs(z));
  const m = Math.max(smooth(125, 225, z), smooth(185, 255, edge));
  if (m > 0) {
    const r = 1 - Math.abs(noise(x * 0.01, z * 0.01));
    h += m * (9 + 20 * r * r + 5 * fbm(x * 0.03, z * 0.03));
  }
  // the river plain is flat farmland (Nile-valley style)
  h = lerp(h, 1.0 + fbm(x * 0.012, z * 0.012) * 0.35, (1 - m) * 0.9);
  h += 9 * Math.exp(-((x - LOOKOUT.x) ** 2 + (z - LOOKOUT.z) ** 2) / 420);   // lookout hill

  const dv = Math.hypot(x, z);
  h = lerp(h, 1.3 + fbm(x * 0.05, z * 0.05) * 0.15, 1 - smooth(34, 50, dv));
  const street = (1 - smooth(13, 20, Math.abs(x))) * smooth(STREET.z0 - 12, STREET.z0 - 2, z) * (1 - smooth(-14, -4, z));
  h = lerp(h, 1.3 + fbm(x * 0.05, z * 0.05) * 0.12, street);
  const dO = Math.hypot(x - OASIS.x, z - OASIS.z);
  h = lerp(h, 0.9, 1 - smooth(22, 40, dO));
  const dR = Math.hypot(x - RUINS.x, z - RUINS.z);
  h = lerp(h, 1.4, 1 - smooth(26, 40, dR));
  h -= 0.1 * (1 - smooth(1.5, 2.6, pathDist(x, z)));

  // carve water: river, field canals, road canals, oasis pond
  h = lerp(-2.4, h, smooth(4.5, 9, Math.abs(z - riverZ(x))));
  for (const c of CANALS) {
    if (z > 15 && z < riverZ(c) + 2) h = lerp(-0.85, h, Math.max(smooth(0.9, 1.7, Math.abs(x - c)), 1 - smooth(16, 19, z)));
  }
  h = lerp(-1.3, h, smooth(1.0, 2.3, canalDist(x, z)));
  h = lerp(-2.2, h, smooth(OASIS.r * 0.6, OASIS.r, dO + fbm(x * 0.1, z * 0.1) * 2));
  return h;
}

const onFootbridge = (x, z) => FOOTBRIDGES.find(b => {
  const dx = x - b.x, dz = z - b.z, c = Math.cos(b.rot), sn = Math.sin(b.rot);
  return Math.abs(dx * c - dz * sn) < 1.9 && Math.abs(dx * sn + dz * c) < 0.9;   // 3.4 m span × 1.7 m wide
});
export function onBridge(x, z) {
  return (Math.abs(x - BRIDGE.x) < BRIDGE.halfW && Math.abs(z - riverZ(BRIDGE.x)) < BRIDGE.halfL) || !!onFootbridge(x, z);
}
export const groundAt = (x, z) => {
  if (Math.abs(x - BRIDGE.x) < BRIDGE.halfW && Math.abs(z - riverZ(BRIDGE.x)) < BRIDGE.halfL) return Math.max(height(x, z), BRIDGE.deck);
  const fb = onFootbridge(x, z);
  return fb ? Math.max(height(x, z), FOOTBRIDGE_DECK) : height(x, z);
};

export function waterDist(x, z) {
  let d = Math.abs(z - riverZ(x)) - 6;
  d = Math.min(d, Math.hypot(x - OASIS.x, z - OASIS.z) - OASIS.r);
  if (z > 15 && z < riverZ(x)) for (const c of CANALS) d = Math.min(d, Math.abs(x - c) - 1);
  d = Math.min(d, canalDist(x, z) - 1.5);
  return Math.max(0, d);
}

// ---- colour ---------------------------------------------------------------
const hex = h => new THREE.Color().setHex(h, THREE.LinearSRGBColorSpace); // raw sRGB numbers
const P = {
  grassA: hex(0x6a8c34), grassB: hex(0x97aa4c), dry: hex(0xbba562), sand: hex(0xe3c48c), sand2: hex(0xcfa56d),
  dirt: hex(0xbc9a6a), village: hex(0xcaa877), mud: hex(0x6b5638), rock: hex(0x8c7c6c), rock2: hex(0x6a5f58),
  snow: hex(0xf4f1ec), bund: hex(0x9a8052),
  crops: [hex(0x4f8a26), hex(0xd8b85a), hex(0x6f8a30), hex(0x3f7c22)],
};
export function colorAt(x, z, h, slope, c) {
  const n = fbm(x * 0.08, z * 0.08);
  c.copy(P.grassA).lerp(P.grassB, n * 0.5 + 0.5);
  c.lerp(P.village, 1 - smooth(22, 36, Math.hypot(x, z) + n * 5));
  const fp = fieldPlot(x, z);
  if (fp >= 0) c.copy(fp === 4 ? P.bund : P.crops[fp]).multiplyScalar(0.92 + n * 0.12);
  c.lerp(P.dirt, 1 - smooth(1.2, 2.5, pathDist(x, z) + n * 0.8));
  c.lerp(n > 0 ? P.rock : P.rock2, smooth(0.7, 1.1, slope) * 0.7);
  c.lerp(P.mud, 1 - smooth(-0.4, 0.35, h));
  return c;
}

// ---- splat weights: which PBR layer covers the ground here --------------
// 0 grass · 1 dry dirt (paths, village) · 2 farm soil · 3 wet mud · 4 rock · 5 sand (unused: no desert)
export function splatAt(x, z, h, slope, out) {
  const n = fbm(x * 0.08, z * 0.08);
  out.fill(0); out[0] = 1;
  out[1] += 1 - smooth(20, 34, Math.hypot(x, z) + n * 6);
  const fp = fieldPlot(x, z);
  if (fp >= 0) {                                           // green crops read as green from afar
    if (fp === 4) out[1] += 1.2;
    else if (fp === 0 || fp === 3) out[0] += 3;
    else out[2] += fp === 2 ? 2.2 : 3;
  }
  out[1] += 3 * (1 - smooth(1.0, 2.4, pathDist(x, z) + n * 0.8));
  out[4] += 3 * smooth(0.75, 1.2, slope);
  out[3] += 4 * (1 - smooth(-0.3, 0.55, h + n * 0.2));
  let sum = 0; for (let i = 0; i < 6; i++) sum += out[i];
  for (let i = 0; i < 6; i++) out[i] /= sum;
  return out;
}
// Tint over the textures: berseem fields a vivid green, wheat golden, hills a touch drier.
export function tintAt(x, z, h, out) {
  out[0] = out[1] = out[2] = 1;
  const fp = fieldPlot(x, z);
  if (fp === 0 || fp === 3) { out[0] = 0.78; out[1] = 1.12; out[2] = 0.62; }
  else if (fp === 1) { out[0] = 1.25; out[1] = 1.08; out[2] = 0.62; }
  const hill = smooth(4, 20, h) * 0.3;
  out[0] += hill * 0.1; out[2] -= hill * 0.1;
  return out;
}

// Top-down painted map (north = +z at the top) for the minimap and world map.
export function mapImage(H, srgb, seg) {
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
