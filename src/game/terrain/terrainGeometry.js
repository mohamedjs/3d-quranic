// Builds the terrain mesh data from the analytic heightfield: positions, normals,
// PBR splat weights, a tint, plus the painted minimap image.
import * as THREE from 'three';
import { SIZE, height, splatAt, tintAt, colorAt, mapImage } from './heightfield.js';

export function buildTerrainGeometry(seg = 360) {
  const step = SIZE / seg, row = seg + 1;
  const geo = new THREE.PlaneGeometry(SIZE, SIZE, seg, seg);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position, n = pos.count, H = new Float32Array(n);
  for (let i = 0; i < n; i++) { H[i] = height(pos.getX(i), pos.getZ(i)); pos.setY(i, H[i]); }
  const sA = new Float32Array(n * 3), sB = new Float32Array(n * 3), tint = new Float32Array(n * 3);
  const w = new Float32Array(6), t = new Float32Array(3);
  // minimap only needs one colour per map pixel: sample on a 257² sub-grid
  const mapSeg = 256, mapH = new Float32Array((mapSeg + 1) ** 2), mapC = new Float32Array((mapSeg + 1) ** 2 * 3), c = new THREE.Color();
  for (let i = 0; i < n; i++) {
    const r = Math.floor(i / row), k = i % row, x = pos.getX(i), z = pos.getZ(i);
    const hx = H[r * row + Math.min(k + 1, seg)] - H[r * row + Math.max(k - 1, 0)];
    const hz = H[Math.min(r + 1, seg) * row + k] - H[Math.max(r - 1, 0) * row + k];
    const slope = Math.hypot(hx, hz) / (2 * step);
    splatAt(x, z, H[i], slope, w);
    sA.set([w[0], w[1], w[2]], i * 3); sB.set([w[3], w[4], w[5]], i * 3);
    tint.set(tintAt(x, z, H[i], t), i * 3);
  }
  for (let r = 0, i = 0; r <= mapSeg; r++) for (let k = 0; k <= mapSeg; k++, i++) {
    const x = -SIZE / 2 + k * SIZE / mapSeg, z = -SIZE / 2 + r * SIZE / mapSeg, h = height(x, z);
    mapH[i] = h; colorAt(x, z, h, 0, c); mapC.set([c.r, c.g, c.b], i * 3);
  }
  geo.setAttribute('splatA', new THREE.BufferAttribute(sA, 3));
  geo.setAttribute('splatB', new THREE.BufferAttribute(sB, 3));
  geo.setAttribute('tint', new THREE.BufferAttribute(tint, 3));
  geo.computeVertexNormals();
  geo.computeBoundingSphere();
  return { geometry: geo, mapCanvas: mapImage(mapH, mapC, mapSeg) };
}
