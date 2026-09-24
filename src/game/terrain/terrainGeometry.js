// Builds the terrain mesh data from the analytic heightfield: positions, normals, the
// painted toon ground colour, masks for the crisp features the shader draws (farm plots,
// paths), plus the painted minimap image.
import * as THREE from 'three';
import { SIZE, height, groundColor, groundMask, colorAt, mapImage } from './heightfield.js';

export function buildTerrainGeometry(seg = 360) {
  const step = SIZE / seg, row = seg + 1;
  const geo = new THREE.PlaneGeometry(SIZE, SIZE, seg, seg);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position, n = pos.count, H = new Float32Array(n);
  for (let i = 0; i < n; i++) { H[i] = height(pos.getX(i), pos.getZ(i)); pos.setY(i, H[i]); }
  const color = new Float32Array(n * 3), mask = new Float32Array(n * 2), m = new Float32Array(2), c = new THREE.Color();
  // minimap only needs one colour per map pixel: sample on a 257² sub-grid
  const mapSeg = 256, mapH = new Float32Array((mapSeg + 1) ** 2), mapC = new Float32Array((mapSeg + 1) ** 2 * 3);
  for (let i = 0; i < n; i++) {
    const r = Math.floor(i / row), k = i % row, x = pos.getX(i), z = pos.getZ(i);
    const hx = H[r * row + Math.min(k + 1, seg)] - H[r * row + Math.max(k - 1, 0)];
    const hz = H[Math.min(r + 1, seg) * row + k] - H[Math.max(r - 1, 0) * row + k];
    const slope = Math.hypot(hx, hz) / (2 * step);
    groundColor(x, z, H[i], slope, c); color.set([c.r, c.g, c.b], i * 3);
    mask.set(groundMask(x, z, m), i * 2);
  }
  for (let r = 0, i = 0; r <= mapSeg; r++) for (let k = 0; k <= mapSeg; k++, i++) {
    const x = -SIZE / 2 + k * SIZE / mapSeg, z = -SIZE / 2 + r * SIZE / mapSeg, h = height(x, z);
    mapH[i] = h; colorAt(x, z, h, 0, c); mapC.set([c.r, c.g, c.b], i * 3);
  }
  geo.setAttribute('color', new THREE.BufferAttribute(color, 3));
  geo.setAttribute('toonMask', new THREE.BufferAttribute(mask, 2));
  geo.deleteAttribute('uv');
  geo.computeVertexNormals();
  geo.computeBoundingSphere();
  return { geometry: geo, mapCanvas: mapImage(mapH, mapC, mapSeg) };
}
