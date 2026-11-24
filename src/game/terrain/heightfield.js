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

export const PATHS = [
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
// Bake pathDist over the whole map into a single-channel Uint8 buffer (0..8 m → 0..255).
export function bakePathDist(res = 1024) {
  const data = new Uint8Array(res * res), step = SIZE / res, o = -HALF + 0.5 * step, scale = 255 / 8;
  const segs = SEGS.map(([[ax, az], [bx, bz]]) => {
    const dx = bx - ax, dz = bz - az;
    return [ax, az, dx, dz, 1 / (dx * dx + dz * dz), Math.min(ax, bx) - 8, Math.max(ax, bx) + 8, Math.min(az, bz) - 8, Math.max(az, bz) + 8];
  });
  for (let r = 0; r < res; r++) {
    const z = o + r * step, row = r * res, active = [];
    for (let s = 0; s < segs.length; s++) if (z >= segs[s][7] && z <= segs[s][8]) active.push(segs[s]);
    if (!active.length) { data.fill(255, row, row + res); continue; }
    for (let c = 0; c < res; c++) {
      const x = o + c * step;
      let m2 = 64;
      for (let s = 0; s < active.length; s++) {
        const g = active[s];
        if (x < g[5] || x > g[6]) continue;
        let t = ((x - g[0]) * g[2] + (z - g[1]) * g[3]) * g[4];
        if (t < 0) t = 0; else if (t > 1) t = 1;
        const px = x - g[0] - g[2] * t, pz = z - g[1] - g[3] * t, d2 = px * px + pz * pz;
        if (d2 < m2) m2 = d2;
      }
      data[row + c] = m2 >= 64 ? 255 : Math.round(Math.sqrt(m2) * scale);
    }
  }
  return data;
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
// footbridges across the canals: { x, z, rot } (rot: plank direction across the water)
export const FOOTBRIDGES = [{ x: 5, z: -76, rot: 0 }, { x: -65, z: -8.5, rot: Math.PI / 2 - 0.19 }, { x: 70, z: -23.8, rot: Math.PI / 2 + 0.32 }, { x: 4, z: 40, rot: 0 }, { x: -15, z: 34.5, rot: 0 }];
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

// Desert sandiness biome factor (0 = lush Nile valley loam/meadow, 1 = golden desert sand):
// transitions smoothly across the eastern desert plateau & ruins (x > ~80, matching sand footsteps
// in game.js) and the arid outer rim west/south of the oasis, while keeping the Nile banks lush.
export function desertFactor(x, z) {
  const n = fbm(x * 0.022, z * 0.022, 3) * 16;
  let d = smooth(72, 122, x + n);                                          // eastern desert & ruins
  const dO = Math.hypot(x - OASIS.x, z - OASIS.z);
  d = Math.max(d, smooth(-130, -178, x + n * 0.6) * smooth(24, 42, dO));   // arid fringe west of oasis
  d = Math.max(d, smooth(-95, -148, z + n * 0.6) * smooth(34, 56, Math.hypot(x - LOOKOUT.x, z - LOOKOUT.z)) * 0.72);
  // River corridor and inner oasis stay lush green
  d *= smooth(10, 22, Math.abs(z - riverZ(x)));
  d *= smooth(OASIS.r + 4, OASIS.r + 18, dO);
  return clamp(d, 0, 1);
}

// Bake per-pixel terrain feature maps into a single RGBA Uint8 buffer (1 texture fetch in shader):
//   R = pathDist  (0..8 m -> 0..255)
//   G = waterDist (0..8 m -> 0..255)
//   B = fieldMask (0 or 255: crisp per-pixel farm plot region)
//   A = desert    (0..1 -> 0..255: golden desert biome blend)
export function bakeTerrainMaps(res = 1024) {
  const data = new Uint8Array(res * res * 4), step = SIZE / res, o = -HALF + 0.5 * step, scale = 255 / 8;
  const prep = list => list.map(([[ax, az], [bx, bz]]) => {
    const dx = bx - ax, dz = bz - az;
    return [ax, az, dx, dz, 1 / (dx * dx + dz * dz), Math.min(ax, bx) - 10, Math.max(ax, bx) + 10, Math.min(az, bz) - 10, Math.max(az, bz) + 10];
  });
  const psegs = prep(SEGS), csegs = prep(CSEGS);
  // Precompute riverZ(x) once per column and low-frequency desert noise on a 129^2 grid
  const rzCol = new Float32Array(res);
  for (let c = 0; c < res; c++) rzCol[c] = riverZ(o + c * step);
  const ng = 128, ng1 = ng + 1, nGrid = new Float32Array(ng1 * ng1), nStep = SIZE / ng;
  for (let gr = 0; gr <= ng; gr++) {
    const gz = -HALF + gr * nStep;
    for (let gc = 0; gc <= ng; gc++) nGrid[gr * ng1 + gc] = fbm((-HALF + gc * nStep) * 0.022, gz * 0.022, 3) * 16;
  }
  const sampleN = (x, z) => {
    const gx = clamp((x + HALF) / nStep, 0, ng - 1e-4), gz = clamp((z + HALF) / nStep, 0, ng - 1e-4);
    const ix = gx | 0, iz = gz | 0, fx = gx - ix, fz = gz - iz, p = iz * ng1 + ix;
    return lerp(lerp(nGrid[p], nGrid[p + 1], fx), lerp(nGrid[p + ng1], nGrid[p + ng1 + 1], fx), fz);
  };

  for (let r = 0; r < res; r++) {
    const z = o + r * step, row = r * res;
    const pAct = [], cAct = [];
    for (let s = 0; s < psegs.length; s++) if (z >= psegs[s][7] && z <= psegs[s][8]) pAct.push(psegs[s]);
    for (let s = 0; s < csegs.length; s++) if (z >= csegs[s][7] && z <= csegs[s][8]) cAct.push(csegs[s]);
    const inFieldZ = z >= -150 && z <= 150 && z < 126;
    const zSmooth = smooth(118, 150, z);
    const inCanalZ = z > 15;
    for (let c = 0; c < res; c++) {
      const x = o + c * step, idx = (row + c) * 4;
      // R: pathDist (0..8 m)
      let pm2 = 64;
      for (let s = 0; s < pAct.length; s++) {
        const g = pAct[s];
        if (x < g[5] || x > g[6]) continue;
        let t = ((x - g[0]) * g[2] + (z - g[1]) * g[3]) * g[4];
        if (t < 0) t = 0; else if (t > 1) t = 1;
        const px = x - g[0] - g[2] * t, pz = z - g[1] - g[3] * t, d2 = px * px + pz * pz;
        if (d2 < pm2) pm2 = d2;
      }
      const pd = pm2 >= 64 ? 8 : Math.sqrt(pm2);

      // G: waterDist (0..8 m) — river, oasis, field canals, road canals
      const rz = rzCol[c], dzR = Math.abs(z - rz);
      let cm2 = 100;
      for (let s = 0; s < cAct.length; s++) {
        const g = cAct[s];
        if (x < g[5] || x > g[6]) continue;
        let t = ((x - g[0]) * g[2] + (z - g[1]) * g[3]) * g[4];
        if (t < 0) t = 0; else if (t > 1) t = 1;
        const px = x - g[0] - g[2] * t, pz = z - g[1] - g[3] * t, d2 = px * px + pz * pz;
        if (d2 < cm2) cm2 = d2;
      }
      const cd = cm2 >= 100 ? 10 : Math.sqrt(cm2);
      const ox = x - OASIS.x, oz = z - OASIS.z, dO2 = ox * ox + oz * oz, dO = Math.sqrt(dO2);
      let wd = Math.min(dzR - 6, dO - OASIS.r, cd - 1.5);
      if (inCanalZ && z < rz) {
        for (let k = 0; k < CANALS.length; k++) {
          const d = Math.abs(x - CANALS[k]) - 1;
          if (d < wd) wd = d;
        }
      }
      if (wd < 0) wd = 0; else if (wd > 8) wd = 8;

      // B: crisp farmland mask (matches fieldPlot() exactly using squared-distance checks)
      let fm = 0;
      if (inFieldZ && x >= -205 && x <= 205 && pd >= 3.2 && cd >= 3.6 && dzR >= 11 && dO2 >= 1764) {
        const ax = x < 0 ? -x : x, az = z < 0 ? -z : z;
        const rx = x - RUINS.x, rzd = z - RUINS.z, lx = x - LOOKOUT.x, lz = z - LOOKOUT.z;
        if (x * x + z * z >= 2116 && !(ax < 16 && z > -60 && z < -8)
          && rx * rx + rzd * rzd >= 1764 && lx * lx + lz * lz >= 900
          && Math.max(zSmooth, smooth(170, 200, ax > az ? ax : az)) <= 0.2) fm = 255;
      }

      // A: desert biome factor (reuses precomputed rz, dO, and low-freq noise grid)
      let des = 0;
      if (x > 50 || x < -105 || z < -75) {
        const nv = sampleN(x, z);
        des = smooth(72, 122, x + nv);
        if (x < -105) des = Math.max(des, smooth(-130, -178, x + nv * 0.6) * smooth(24, 42, dO));
        if (z < -75) {
          const lx = x - LOOKOUT.x, lz = z - LOOKOUT.z;
          des = Math.max(des, smooth(-95, -148, z + nv * 0.6) * smooth(34, 56, Math.sqrt(lx * lx + lz * lz)) * 0.72);
        }
        if (des > 0) des *= smooth(10, 22, dzR) * smooth(OASIS.r + 4, OASIS.r + 18, dO);
      }

      data[idx]     = pm2 >= 64 ? 255 : Math.round(pd * scale);
      data[idx + 1] = Math.round(wd * scale);
      data[idx + 2] = fm;
      data[idx + 3] = Math.round(des * 255);
    }
  }
  return data;
}

// ---- colour: painterly Nile valley ground palette -----------------------------------
const hex = h => new THREE.Color(h);   // sRGB hex → linear working colour
const P = {
  grass: hex(0x80A846), grass2: hex(0x6C963B), grass3: hex(0x95B754), village: hex(0xD2B07E), villageGrass: hex(0x9EB25B),
  yard: hex(0xD9BA88), path: hex(0xE2C184), pathEdge: hex(0xCCA167),
  desert: hex(0xDEB677), desert2: hex(0xCFA060),
  bank: hex(0x705236), mud: hex(0x523A24), moss: hex(0x5B7D34),
  hill: hex(0xA4AD5C), rock: hex(0xB89E7A), rockDark: hex(0x9A8162),
  bund: hex(0x98744B), crops: [hex(0x569A37), hex(0xDAB654), hex(0x698E38), hex(0x7FAE48)],
};
const HOME_YARD = { x: -5.9, z: 26 };
// Base ground colour without sharp edges (paths, fields and wet banks are drawn per pixel in shader,
// eliminating sawtooth canal/river triangles on Lite's coarse vertex grid).
export function groundColor(x, z, h, slope, c) {
  const n = fbm(x * 0.08, z * 0.08);
  c.copy(n < -0.1 ? P.grass2 : n < 0.22 ? P.grass : P.grass3);
  const des = desertFactor(x, z);
  if (des > 0) c.lerp(n < 0 ? P.desert2 : P.desert, des);
  const vil = Math.max(1 - smooth(40, 46, Math.hypot(x, z)), (1 - smooth(14, 16, Math.abs(x))) * smooth(-64, -60, z) * (1 - smooth(-10, -6, z)));
  if (vil > 0) c.lerp(n < 0.14 ? P.village : P.villageGrass, vil);
  c.lerp(P.yard, 1 - smooth(3.5, 5, Math.hypot(x - HOME_YARD.x, z - HOME_YARD.z)));
  c.lerp(P.hill, smooth(4, 14, h) * 0.55 * (1 - des * 0.5));
  c.lerp(P.rock, smooth(0.65, 1.15, slope) * 0.78);
  return c;
}
// Sharp-feature masks for the shader: [farmland 0..1, path 0..1]
export function groundMask(x, z, out) {
  out[0] = fieldPlot(x, z) >= 0 ? 1 : 0;
  out[1] = 1 - smooth(1.2, 2.4, pathDist(x, z));
  return out;
}
export const FIELD_COLORS = {
  crops: P.crops, bund: P.bund, path: P.path, pathEdge: P.pathEdge,
  desert: P.desert, desert2: P.desert2, bank: P.bank, mud: P.mud, moss: P.moss, rockDark: P.rockDark,
};
// Full colour (minimap / world map): ground + banks + paths + fields.
export function colorAt(x, z, h, slope, c) {
  groundColor(x, z, h, slope, c);
  c.lerp(P.bank, (1 - smooth(0.4, 1.0, waterDist(x, z))) * (1 - smooth(0.8, 1.1, h)));
  c.lerp(P.mud, 1 - smooth(-0.35, -0.15, h));
  const fp = fieldPlot(x, z);
  if (fp >= 0) c.copy(fp === 4 ? P.bund : P.crops[fp]);
  c.lerp(P.path, 1 - smooth(1.6, 2.0, pathDist(x, z)));
  return c.convertLinearToSRGB();
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
