// Bakes the world-space "bank" texture the toon water reads (the water plane has no UVs):
//   r  e — 0 at the bank, 1 mid-stream (analytic centre-line distance per water body,
//          clamped by the real water depth so the foam line hugs the actual shore)
//   b  flow direction, angle / π + .5 (river along its course, canals along their axis)
//   a  flow speed (still oasis pond: slow)
import * as THREE from 'three';
import { SIZE, HALF, WATER_Y, height, riverZ, CANALS, ROAD_CANALS, OASIS } from '../terrain/heightfield.js';

const RIVER_HW = 6.7, CANAL_HW = 1.15, ROAD_HW = 1.55, POND_R = 12.2, SHORE = 0.3;
const SEGS = ROAD_CANALS.flatMap(p => p.slice(1).map((b, i) => [p[i], b]));
const fold = a => { while (a > Math.PI / 2) a -= Math.PI; while (a <= -Math.PI / 2) a += Math.PI; return a; };

export function buildWaterBank(N = 1024) {
  const data = new Uint8Array(N * N * 4), step = SIZE / N;
  for (let j = 0; j < N; j++) {
    const z = -HALF + (j + 0.5) * step;
    for (let i = 0; i < N; i++) {
      const x = -HALF + (i + 0.5) * step;
      let e = -1, ang = 0, spd = 1;
      const rz = riverZ(x), dr = Math.abs(z - rz);
      if (dr < RIVER_HW + 2) { e = 1 - dr / RIVER_HW; ang = Math.atan(0.294 * Math.cos(x * 0.021) + 0.342 * Math.cos(x * 0.057 + 1.3)); }
      if (z > 15 && z < rz + 2) for (const c of CANALS) {
        const d = Math.abs(x - c); if (d > CANAL_HW + 2) continue;
        const ec = 1 - d / CANAL_HW; if (ec > e) { e = ec; ang = Math.PI / 2; }
      }
      for (const [[ax, az], [bx, bz]] of SEGS) {
        const dx = bx - ax, dz = bz - az, t = Math.max(0, Math.min(1, ((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz)));
        const d = Math.hypot(x - ax - dx * t, z - az - dz * t); if (d > ROAD_HW + 2) continue;
        const ec = 1 - d / ROAD_HW; if (ec > e) { e = ec; ang = Math.atan2(dz, dx); }
      }
      const dO = Math.hypot(x - OASIS.x, z - OASIS.z);
      if (dO < POND_R + 4) { const eo = 1 - dO / POND_R; if (eo > e) { e = eo; ang = Math.atan2(z - OASIS.z, x - OASIS.x) + Math.PI / 2; spd = 0.25; } }
      const o = (j * N + i) * 4;
      if (e > -0.6) {                                   // near water: clamp by the real depth
        const depth = WATER_Y - height(x, z);
        e = Math.min(Math.max(e, 0.04), depth / SHORE);
      }
      data[o] = Math.max(0, Math.min(1, e)) * 255;
      data[o + 2] = (fold(ang) / Math.PI + 0.5) * 255;
      data[o + 3] = spd * 255;
    }
  }
  const t = new THREE.DataTexture(data, N, N);
  t.minFilter = t.magFilter = THREE.LinearFilter; t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
  t.needsUpdate = true;
  return t;
}
