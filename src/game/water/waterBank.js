// Bakes the world-space water bank & personality map (1024^2 Lite–High, 2048^2 Ultra):
//   R  e      — 0 at shoreline, 1 mid-stream (clamped by real depth so foam hugs actual shores)
//   G  depth  — normalized physical water depth (0..2.2 m -> 0..1) for Beer-Lambert absorption & caustics
//   B  flow   — flow direction angle / pi + 0.5 (Nile along course, canals along axis, oasis gentle swirl)
//   A  type   — water personality: ~0.15 Oasis pond, ~0.55 Irrigation canals, ~0.95 Nile river
import * as THREE from 'three';
import { SIZE, HALF, WATER_Y, height, riverZ, CANALS, ROAD_CANALS, OASIS } from '../terrain/heightfield.js';

const RIVER_HW = 6.7, CANAL_HW = 1.15, ROAD_HW = 1.55, POND_R = 12.2, SHORE = 0.34, MAX_DEPTH = 2.2;
const TYPE_OASIS = 0.15, TYPE_CANAL = 0.55, TYPE_NILE = 0.95;
const SEGS = ROAD_CANALS.flatMap(p => p.slice(1).map((b, i) => {
  const [ax, az] = p[i], [bx, bz] = b, dx = bx - ax, dz = bz - az;
  return [ax, az, dx, dz, 1 / (dx * dx + dz * dz), Math.atan2(dz, dx),
    Math.min(ax, bx) - ROAD_HW - 2, Math.max(ax, bx) + ROAD_HW + 2,
    Math.min(az, bz) - ROAD_HW - 2, Math.max(az, bz) + ROAD_HW + 2];
}));
const fold = a => { while (a > Math.PI / 2) a -= Math.PI; while (a <= -Math.PI / 2) a += Math.PI; return a; };

const bankCache = new Map();
export function buildWaterBank(N = 1024) {
  if (bankCache.has(N)) return bankCache.get(N);
  const data = new Uint8Array(N * N * 4), step = SIZE / N, o0 = -HALF + 0.5 * step;
  const rzCol = new Float32Array(N), angCol = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    const x = o0 + i * step;
    rzCol[i] = riverZ(x);
    angCol[i] = Math.atan(0.294 * Math.cos(x * 0.021) + 0.342 * Math.cos(x * 0.057 + 1.3));
  }
  const rLim = RIVER_HW + 2.2, cLim = CANAL_HW + 2.0, oLim2 = (POND_R + 4) ** 2;

  for (let j = 0; j < N; j++) {
    const z = o0 + j * step, row = j * N, inCanalZ = z > 15;
    const act = [];
    for (let s = 0; s < SEGS.length; s++) if (z >= SEGS[s][8] && z <= SEGS[s][9]) act.push(SEGS[s]);
    const oz = z - OASIS.z, oz2 = oz * oz;

    for (let i = 0; i < N; i++) {
      const x = o0 + i * step;
      let e = -1, ang = 0, kind = TYPE_NILE;

      const rz = rzCol[i], dr = Math.abs(z - rz);
      if (dr < rLim) { e = 1 - dr / RIVER_HW; ang = angCol[i]; kind = TYPE_NILE; }

      if (inCanalZ && z < rz + 2) {
        for (let k = 0; k < CANALS.length; k++) {
          const d = Math.abs(x - CANALS[k]);
          if (d > cLim) continue;
          const ec = 1 - d / CANAL_HW;
          if (ec > e) {
            e = ec; ang = Math.PI / 2;
            // Smoothly blend canal personality into Nile right at the mouth
            kind = dr < rLim + 2 ? TYPE_CANAL + (TYPE_NILE - TYPE_CANAL) * Math.max(0, Math.min(1, 1 - (dr - 5.5) / 4)) : TYPE_CANAL;
          }
        }
      }
      for (let s = 0; s < act.length; s++) {
        const g = act[s];
        if (x < g[6] || x > g[7]) continue;
        let t = ((x - g[0]) * g[2] + (z - g[1]) * g[3]) * g[4];
        if (t < 0) t = 0; else if (t > 1) t = 1;
        const px = x - g[0] - g[2] * t, pz = z - g[1] - g[3] * t, d = Math.sqrt(px * px + pz * pz);
        if (d > ROAD_HW + 2) continue;
        const ec = 1 - d / ROAD_HW;
        if (ec > e) { e = ec; ang = g[5]; kind = TYPE_CANAL; }
      }
      const ox = x - OASIS.x, dO2 = ox * ox + oz2;
      if (dO2 < oLim2) {
        const dO = Math.sqrt(dO2), eo = 1 - dO / POND_R;
        if (eo > e) { e = eo; ang = Math.atan2(oz, ox) + Math.PI / 2; kind = TYPE_OASIS; }
      }

      let depthNorm = 0;
      if (e > -0.6) {
        const depth = WATER_Y - height(x, z);
        e = Math.min(Math.max(e, 0.04), depth / SHORE);
        depthNorm = Math.max(0, Math.min(1, depth / MAX_DEPTH));
      }
      const o = (row + i) * 4;
      data[o]     = Math.max(0, Math.min(1, e)) * 255;
      data[o + 1] = depthNorm * 255;
      data[o + 2] = (fold(ang) / Math.PI + 0.5) * 255;
      data[o + 3] = kind * 255;
    }
  }
  const t = new THREE.DataTexture(data, N, N, THREE.RGBAFormat, THREE.UnsignedByteType);
  t.minFilter = t.magFilter = THREE.LinearFilter;
  t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
  t.generateMipmaps = false;
  t.needsUpdate = true;
  bankCache.set(N, t);
  return t;
}
