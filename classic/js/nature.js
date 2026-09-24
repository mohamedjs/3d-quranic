// Vegetation, rocks, birds and sun motes. Everything repeated is instanced.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { height, fieldPlot, pathDist, riverZ, OASIS, RUINS, rng, fbm, smooth } from './terrain.js';

export const wind = { uTime: { value: 0 }, uWind: { value: 1 } };

// Give a geometry a flat vertex colour, optionally graded along y.
export function paint(geo, bottom, top = bottom, y0 = 0, y1 = 1) {
  const g = geo.index ? geo.toNonIndexed() : geo;
  const p = g.attributes.position, col = new Float32Array(p.count * 3);
  const a = new THREE.Color(bottom), b = new THREE.Color(top), c = new THREE.Color();
  for (let i = 0; i < p.count; i++) {
    c.copy(a).lerp(b, THREE.MathUtils.clamp((p.getY(i) - y0) / (y1 - y0 || 1), 0, 1));
    col.set([c.r, c.g, c.b], i * 3);
  }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  return g;
}
export const merge = list => mergeGeometries(list.map(g => g.index ? g.toNonIndexed() : g));

// Sway in the vertex shader; `factor` is a GLSL expression that is 0 at the root.
function windy(mat, key, strength, factor) {
  mat.customProgramCacheKey = () => key;
  mat.onBeforeCompile = sh => {
    sh.uniforms.uTime = wind.uTime; sh.uniforms.uWind = wind.uWind;
    sh.vertexShader = 'uniform float uTime; uniform float uWind;\n' + sh.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
      vec4 ip = instanceMatrix * vec4(0., 0., 0., 1.);
      float k = pow(clamp(${factor}, 0., 2.), 1.6) * ${strength.toFixed(3)} * uWind;
      float w = sin(uTime * 1.6 + ip.x * .23 + ip.z * .17) + .5 * sin(uTime * 2.7 + ip.x * .7 + ip.z * .3);
      transformed.x += w * k; transformed.z += w * k * .6;`);
  };
  return mat;
}

function instanced(geo, mat, mats, colors) {
  const m = new THREE.InstancedMesh(geo, mat, mats.length);
  mats.forEach((mx, i) => m.setMatrixAt(i, mx));
  if (colors) colors.forEach((c, i) => m.setColorAt(i, c));
  m.computeBoundingSphere();
  return m;
}
const _q = new THREE.Quaternion(), _e = new THREE.Euler(), _s = new THREE.Vector3(), _p = new THREE.Vector3();
const place = (x, y, z, ry, s, sy = s, tilt = 0) =>
  new THREE.Matrix4().compose(_p.set(x, y, z), _q.setFromEuler(_e.set(tilt, ry, tilt * 0.6)), _s.set(s, sy, s));

// ---- geometry builders -------------------------------------------------
function clumpGeo(h, w, blades) {
  const parts = [];
  for (let i = 0; i < blades; i++) {
    const p = new THREE.PlaneGeometry(w, h, 1, 2), a = p.attributes.position;
    for (let v = 0; v < a.count; v++) { const t = (a.getY(v) + h / 2) / h; a.setX(v, a.getX(v) * (1 - t * 0.85)); a.setY(v, a.getY(v) + h / 2); }
    p.rotateY((i / blades) * Math.PI + i * 0.3);
    p.translate(Math.sin(i * 2.1) * w * 0.3, 0, Math.cos(i * 2.1) * w * 0.3);
    parts.push(p);
  }
  const g = paint(merge(parts), 0x3a5a1c, 0xb4c060, 0, h);
  const n = g.attributes.normal;
  for (let i = 0; i < n.count; i++) n.setXYZ(i, 0, 1, 0); // lit like a lawn, not like cards
  return g;
}

const palmCurve = t => new THREE.Vector3(t * t * 0.9, t * 7, 0);
function palmGeos() {
  const trunk = [], up = new THREE.Vector3(0, 1, 0);
  for (let i = 0; i < 12; i++) {
    const a = palmCurve(i / 12), b = palmCurve((i + 1) / 12), len = a.distanceTo(b), r = THREE.MathUtils.lerp(0.3, 0.17, i / 12);
    const c = new THREE.CylinderGeometry(r * 0.86, r * 1.1, len * 1.04, 7);
    c.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(up, b.clone().sub(a).normalize()));
    c.translate((a.x + b.x) / 2, (a.y + b.y) / 2, 0);
    trunk.push(paint(c, i % 2 ? 0x7a5c3e : 0x6b4f35));
  }
  const crown = palmCurve(1);
  for (let i = 0; i < 5; i++) { // date clusters
    const d = new THREE.SphereGeometry(0.22, 6, 4); d.scale(1, 1.4, 1);
    d.translate(crown.x + Math.cos(i * 1.3) * 0.35, crown.y - 0.45, Math.sin(i * 1.3) * 0.35);
    trunk.push(paint(d, 0xb8641f));
  }
  const fronds = [], L = 3.3;
  for (let i = 0; i < 13; i++) {
    const f = new THREE.PlaneGeometry(0.75, L, 2, 10); f.rotateX(-Math.PI / 2); f.translate(0, 0, L / 2);
    const a = f.attributes.position, young = i >= 10, lift = young ? 0.9 : 0.5 + (i % 3) * 0.12;
    for (let v = 0; v < a.count; v++) {
      const z = a.getZ(v), t = z / L, x = a.getX(v) * Math.min(1, t * 4) * (1 - t ** 1.6) * 1.8;
      a.setX(v, x); a.setY(v, lift * z - (young ? 0.05 : 0.2) * z * z - Math.abs(x) * 0.45);
    }
    f.rotateY((i / (young ? 3 : 10)) * Math.PI * 2 + i * 0.4);
    f.translate(crown.x, crown.y, 0);
    fronds.push(paint(f, 0x6f7f2c, 0x4d7a28, crown.y - 1, crown.y + 0.8));
  }
  return { trunk: merge(trunk), fronds: merge(fronds), crown };
}

function treeGeo(r) {
  const parts = [paint(new THREE.CylinderGeometry(0.12, 0.2, 1.6, 6).translate(0, 0.8, 0), 0x5e4630)];
  for (let i = 0; i < 4; i++) {
    const b = new THREE.IcosahedronGeometry(0.9 + r() * 0.4, 1), a = b.attributes.position;
    for (let v = 0; v < a.count; v++) a.setXYZ(v, a.getX(v) * (1 + (r() - 0.5) * 0.25), a.getY(v) * 0.75, a.getZ(v) * (1 + (r() - 0.5) * 0.25));
    b.translate(Math.cos(i * 1.7) * 0.7, 2 + (i % 2) * 0.5, Math.sin(i * 1.7) * 0.7);
    parts.push(paint(b, 0x3f5e22, 0x6e8a36, 1.3, 3));
  }
  const g = merge(parts); g.computeVertexNormals(); return g;
}
function lumpGeo(r, detail, yScale) {
  const g = new THREE.IcosahedronGeometry(1, detail), a = g.attributes.position;
  for (let v = 0; v < a.count; v++) { const k = 0.8 + fbm(a.getX(v) * 2 + r, a.getZ(v) * 2) * 0.5; a.setXYZ(v, a.getX(v) * k, a.getY(v) * k * yScale, a.getZ(v) * k); }
  g.computeVertexNormals(); return g;
}

// ---- scatter ----------------------------------------------------------
export function buildNature(scene, colliders, quality) {
  const r = rng(7), group = new THREE.Group();
  const blocked = (x, z, pad) => colliders.some(c => x > c.x0 - pad && x < c.x1 + pad && z > c.z0 - pad && z < c.z1 + pad);
  const lush = (x, z, h) => h > 0.25 && h < 7 && x < 95 && fieldPlot(x, z) < 0 && pathDist(x, z) > 2.4 && Math.hypot(x, z) > 24;

  // grass
  const grassM = [], grassC = [], c = new THREE.Color(), N = quality > 1 ? 42000 : 14000;
  for (let i = 0; i < N * 3 && grassM.length < N; i++) {
    const x = (r() - 0.5) * 380, z = (r() - 0.5) * 380 - 20, h = height(x, z);
    if (!lush(x, z, h) || blocked(x, z, 0.2) || fbm(x * 0.04, z * 0.04) < -0.35) continue;
    grassM.push(place(x, h - 0.05, z, r() * 6.3, 0.7 + r() * 0.8, 0.6 + r() * 0.9));
    grassC.push(c.setHSL(0.2 + r() * 0.06, 0.35 + r() * 0.2, 0.42 + r() * 0.2).clone());
  }
  const grass = instanced(clumpGeo(0.55, 0.45, 3),
    windy(new THREE.MeshStandardMaterial({ vertexColors: true, side: THREE.DoubleSide, roughness: 1 }), 'grass', 0.22, 'position.y / .55'), grassM, grassC);
  grass.receiveShadow = true; group.add(grass);

  // crops in rows (wheat, greens, clover)
  const cropM = [], cropC = [];
  for (let x = -74.5; x < 75; x += 0.85) for (let z = 16.5; z < 100; z += 0.7) {
    const t = fieldPlot(x, z); if (t < 0 || t === 2 || t === 4) continue;
    const jx = x + (r() - 0.5) * 0.25, h = height(jx, z);
    const tall = t === 1 ? 1.05 : t === 0 ? 0.65 : 0.28;
    cropM.push(place(jx, h - 0.05, z, r() * 6.3, 0.9 + r() * 0.3, tall * (0.8 + r() * 0.4)));
    cropC.push(t === 1 ? c.setHSL(0.12, 0.62, 0.62 + r() * 0.08).clone() : c.setHSL(0.24 + r() * 0.03, 0.55, 0.36 + r() * 0.08).clone());
  }
  const crops = instanced(clumpGeo(1, 0.4, 4),
    windy(new THREE.MeshStandardMaterial({ vertexColors: true, side: THREE.DoubleSide, roughness: 1 }), 'crops', 0.18, 'position.y'), cropM, cropC);
  crops.receiveShadow = true; group.add(crops);

  // palms: village, oasis ring, river banks, scattered
  const palmSpots = [];
  const tryPalm = (x, z) => {
    const h = height(x, z);
    if (h < 0.1 || h > 8 || pathDist(x, z) < 2.5 || fieldPlot(x, z) >= 0 || blocked(x, z, 1.2)) return;
    if (palmSpots.some(p => Math.hypot(p[0] - x, p[1] - z) < 3)) return;
    palmSpots.push([x, z, h]);
  };
  for (let i = 0; i < 90; i++) { const a = r() * 6.3, d = 16 + r() * 22; tryPalm(OASIS.x + Math.cos(a) * d, OASIS.z + Math.sin(a) * d); }
  for (let i = 0; i < 60; i++) { const a = r() * 6.3, d = 12 + r() * 30; tryPalm(Math.cos(a) * d, Math.sin(a) * d); }
  for (let i = 0; i < 90; i++) { const x = -200 + r() * 290, s = r() < 0.5 ? -1 : 1; tryPalm(x, riverZ(x) + s * (9 + r() * 8)); }
  for (let i = 0; i < 60; i++) tryPalm((r() - 0.5) * 300, (r() - 0.5) * 200 - 20);
  for (let i = 0; i < 14; i++) { const a = r() * 6.3, d = 20 + r() * 20; tryPalm(RUINS.x + Math.cos(a) * d, RUINS.z + Math.sin(a) * d); }
  const pg = palmGeos(), palmM = palmSpots.map(([x, z, h]) => place(x, h - 0.1, z, r() * 6.3, 0.8 + r() * 0.45));
  const trunks = instanced(pg.trunk, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9 }), palmM);
  const fronds = instanced(pg.fronds, windy(new THREE.MeshStandardMaterial({ vertexColors: true, side: THREE.DoubleSide, roughness: 0.8 }),
    'fronds', 0.28, `length(position.xz - vec2(${pg.crown.x.toFixed(2)}, 0.)) / 3.3`), palmM);
  trunks.castShadow = fronds.castShadow = true; trunks.receiveShadow = fronds.receiveShadow = true;
  group.add(trunks, fronds);
  palmSpots.forEach(([x, z]) => colliders.push({ x0: x - 0.4, x1: x + 0.4, z0: z - 0.4, z1: z + 0.4 }));

  // broadleaf trees and bushes
  const treeM = [];
  for (let i = 0; i < 900 && treeM.length < 110; i++) {
    const x = (r() - 0.5) * 360, z = (r() - 0.5) * 300 - 10, h = height(x, z);
    if (!lush(x, z, h) || blocked(x, z, 1.5) || palmSpots.some(p => Math.hypot(p[0] - x, p[1] - z) < 4)) continue;
    treeM.push(place(x, h - 0.1, z, r() * 6.3, 0.9 + r() * 0.7)); colliders.push({ x0: x - 0.4, x1: x + 0.4, z0: z - 0.4, z1: z + 0.4 });
  }
  const trees = instanced(treeGeo(r), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9, flatShading: true }), treeM);
  trees.castShadow = trees.receiveShadow = true; group.add(trees);

  const bushM = [], bushC = [];
  for (let i = 0; i < 3000 && bushM.length < 420; i++) {
    const x = (r() - 0.5) * 380, z = (r() - 0.5) * 320 - 10, h = height(x, z), dry = smooth(85, 130, x);
    if (h < 0.2 || h > 10 || pathDist(x, z) < 2 || fieldPlot(x, z) >= 0 || blocked(x, z, 0.8) || Math.hypot(x, z) < 20) continue;
    bushM.push(place(x, h + 0.1, z, r() * 6.3, 0.5 + r() * 0.7, 0.4 + r() * 0.5));
    bushC.push(new THREE.Color().setHSL(THREE.MathUtils.lerp(0.25, 0.12, dry), THREE.MathUtils.lerp(0.45, 0.3, dry), 0.28 + r() * 0.1));
  }
  const bushes = instanced(lumpGeo(1, 1, 0.8), new THREE.MeshStandardMaterial({ roughness: 1, flatShading: true }), bushM, bushC);
  bushes.castShadow = bushes.receiveShadow = true; group.add(bushes);

  // rocks: mountain feet, desert, ruins
  const rockM = [], rockC = [];
  for (let i = 0; i < 4000 && rockM.length < 320; i++) {
    const x = (r() - 0.5) * 480, z = (r() - 0.5) * 480, h = height(x, z);
    const wild = x > 90 || z > 110 || Math.max(Math.abs(x), Math.abs(z)) > 170;
    if (!wild || h < 0.3 || pathDist(x, z) < 2.5 || blocked(x, z, 1)) continue;
    const s = 0.3 + r() ** 3 * 3.5;
    rockM.push(place(x, h + s * 0.15, z, r() * 6.3, s, s * (0.5 + r() * 0.4), (r() - 0.5) * 0.4));
    rockC.push(new THREE.Color().setHSL(0.08, 0.15 + r() * 0.1, 0.42 + r() * 0.12));
  }
  const rocks = instanced(lumpGeo(3, 1, 0.7), new THREE.MeshStandardMaterial({ roughness: 0.95, flatShading: true }), rockM, rockC);
  rocks.castShadow = rocks.receiveShadow = true; group.add(rocks);

  // wild flowers near the village and oasis
  const flM = [], flC = [], hues = [0.95, 0.13, 0.0, 0.75, 0.55];
  for (let i = 0; i < 12000 && flM.length < 3500; i++) {
    const near = r() < 0.5 ? [0, 0] : [OASIS.x, OASIS.z], a = r() * 6.3, d = 14 + r() * 50;
    const x = near[0] + Math.cos(a) * d + fbm(i, 1) * 4, z = near[1] + Math.sin(a) * d, h = height(x, z);
    if (!lush(x, z, h) || blocked(x, z, 0.3) || fbm(x * 0.07, z * 0.07) < 0.05) continue;
    flM.push(place(x, h + 0.32 + r() * 0.15, z, r() * 6.3, 0.05 + r() * 0.04));
    flC.push(new THREE.Color().setHSL(hues[(r() * hues.length) | 0], 0.75, r() < 0.3 ? 0.9 : 0.62));
  }
  const flowers = instanced(new THREE.IcosahedronGeometry(1, 0), new THREE.MeshStandardMaterial({ roughness: 0.7, emissive: 0x221100 }), flM, flC);
  group.add(flowers);

  scene.add(group);
  return { group, palmSpots };
}

// ---- birds --------------------------------------------------------------
export class Birds {
  constructor(scene, n = 26) {
    const r = rng(99), mat = new THREE.MeshStandardMaterial({ color: 0x3a3028, side: THREE.DoubleSide, roughness: 1 });
    const wing = new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute([0, 0, -0.12, 0, 0, 0.14, 0.75, 0, 0], 3));
    wing.computeVertexNormals();
    this.list = [];
    const centers = [[OASIS.x, OASIS.z], [0, 40], [-40, 70], [30, -10]];
    for (let i = 0; i < n; i++) {
      const g = new THREE.Group(), body = new THREE.Mesh(new THREE.ConeGeometry(0.1, 0.5, 5).rotateX(Math.PI / 2), mat);
      const L = new THREE.Mesh(wing, mat), R = new THREE.Mesh(wing, mat); R.scale.x = -1;
      g.add(body, L, R); scene.add(g);
      const [cx, cz] = centers[i % centers.length];
      this.list.push({ g, L, R, cx: cx + (r() - 0.5) * 20, cz: cz + (r() - 0.5) * 20, rad: 12 + r() * 25, y: 16 + r() * 18, sp: (0.15 + r() * 0.12) * (r() < 0.5 ? -1 : 1), a: r() * 6.3, f: r() * 6 });
    }
  }
  update(dt) {
    for (const b of this.list) {
      b.a += b.sp * dt; b.f += dt * (7 + Math.sin(b.a * 3) * 3);
      const x = b.cx + Math.cos(b.a) * b.rad, z = b.cz + Math.sin(b.a) * b.rad, y = b.y + Math.sin(b.a * 2) * 2;
      b.g.position.set(x, y, z);
      const sg = Math.sign(b.sp);
      b.g.rotation.y = Math.atan2(-Math.sin(b.a) * sg, Math.cos(b.a) * sg);
      const flap = Math.sin(b.f) > -0.2 ? Math.sin(b.f) * 0.7 : -0.1; // glide now and then
      b.L.rotation.z = flap; b.R.rotation.z = -flap;
    }
  }
}

// ---- floating motes catching the low sun ----------------------------------
export class Motes {
  constructor(scene, n = 350) {
    const pos = new Float32Array(n * 3);
    for (let i = 0; i < n * 3; i++) pos[i] = (Math.random() - 0.5) * 50;
    const geo = new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(pos, 3));
    this.points = new THREE.Points(geo, new THREE.PointsMaterial({ color: 0xffe2a8, size: 0.09, transparent: true, opacity: 0.7, depthWrite: false, blending: THREE.AdditiveBlending }));
    this.points.frustumCulled = false;
    scene.add(this.points); this.t = 0;
  }
  update(dt, center) {
    this.t += dt;
    const a = this.points.geometry.attributes.position;
    for (let i = 0; i < a.count; i++) {
      let x = a.getX(i) + Math.sin(this.t * 0.5 + i) * dt * 0.3, y = a.getY(i) + dt * 0.12, z = a.getZ(i) + Math.cos(this.t * 0.4 + i) * dt * 0.3;
      if (x - center.x > 25) x -= 50; if (center.x - x > 25) x += 50;
      if (z - center.z > 25) z -= 50; if (center.z - z > 25) z += 50;
      if (y - center.y > 8) y -= 10; if (y < center.y - 2) y += 10;
      a.setXYZ(i, x, y, z);
    }
    a.needsUpdate = true;
  }
}
