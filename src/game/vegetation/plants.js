// Procedural plant geometry. Each builder returns one merged BufferGeometry (with vertex
// colours) meant to be instanced; variants differ in structure, not just scale.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { rng } from '../terrain/heightfield.js';

const C = new THREE.Color();
export function paint(geo, bottom, top = bottom, y0 = 0, y1 = 1) {
  const g = geo.index ? geo.toNonIndexed() : geo;
  const p = g.attributes.position, col = new Float32Array(p.count * 3), a = new THREE.Color(bottom), b = new THREE.Color(top);
  for (let i = 0; i < p.count; i++) { C.copy(a).lerp(b, THREE.MathUtils.clamp((p.getY(i) - y0) / (y1 - y0 || 1), 0, 1)); col.set([C.r, C.g, C.b], i * 3); }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  return g;
}
export const merge = list => {
  const g = mergeGeometries(list.map(x => {
    const n = x.index ? x.toNonIndexed() : x;
    if (!n.attributes.uv) n.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(n.attributes.position.count * 2), 2));
    return n;
  }));
  g.computeBoundingSphere();
  return g;
};

// A tapered, curved strip (blade, leaf, leaflet) from (0,0,0) along +y, bending toward +z.
function strip(len, width, segs, bend, taper = 1, twist = 0) {
  const pos = [], idx = [];
  for (let i = 0; i <= segs; i++) {
    const t = i / segs, w = width * (1 - t * taper) * 0.5, y = len * t * (1 - bend * t * 0.35), z = bend * len * t * t, a = twist * t;
    pos.push(-w * Math.cos(a), y, z - w * Math.sin(a), w * Math.cos(a), y, z + w * Math.sin(a));
    if (i < segs) { const k = i * 2; idx.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

export function grassClump(seed = 1, dry = false) {
  const r = rng(seed), parts = [];
  for (let i = 0; i < 7; i++) {
    const s = strip(0.35 + r() * 0.35, 0.05 + r() * 0.03, 3, 0.3 + r() * 0.6, 0.95, (r() - 0.5) * 0.6);
    s.rotateY(r() * Math.PI * 2); s.translate((r() - 0.5) * 0.18, 0, (r() - 0.5) * 0.18);
    parts.push(dry ? paint(s, 0x6b5a32, 0xd9c48a, 0, 0.6) : paint(s, 0x2f4a17, 0x9fb553, 0, 0.6));
  }
  const g = merge(parts), n = g.attributes.normal;
  for (let i = 0; i < n.count; i++) { const y = n.getY(i); n.setXYZ(i, n.getX(i) * 0.35, Math.abs(y) * 0.35 + 0.65, n.getZ(i) * 0.35); } // soft, lawn-like shading
  return g;
}

export function wheatClump(seed = 2) {
  const r = rng(seed), parts = [];
  for (let i = 0; i < 6; i++) {
    const h = 0.85 + r() * 0.3, x = (r() - 0.5) * 0.2, z = (r() - 0.5) * 0.2, lean = (r() - 0.5) * 0.15;
    const stalk = new THREE.CylinderGeometry(0.006, 0.01, h, 3).translate(0, h / 2, 0).rotateZ(lean);
    const ear = new THREE.CylinderGeometry(0.018, 0.012, 0.12, 5).translate(0, h + 0.05, 0).rotateZ(lean);
    const leaf = strip(0.35, 0.025, 3, 0.8, 1).rotateY(r() * 6.28).translate(0, 0.15 + r() * 0.2, 0);
    parts.push(paint(stalk.translate(x, 0, z), 0x8f8a3c, 0xd6b865, 0, h), paint(ear.translate(x, 0, z), 0xd8b45a), paint(leaf.translate(x, 0, z), 0x9a9848, 0xcdb46a, 0, 0.5));
  }
  return merge(parts);
}

export function leafyCrop(seed = 3) {
  const r = rng(seed), parts = [];
  for (let i = 0; i < 9; i++) {
    const s = strip(0.22 + r() * 0.12, 0.09, 4, 1.1, 0.7);
    s.rotateY(i / 9 * 6.28 + r() * 0.4); parts.push(paint(s, 0x2d5a1c, 0x6f9a3a, 0, 0.25));
  }
  return merge(parts);
}

export function reedClump(seed = 4) {
  const r = rng(seed), parts = [];
  for (let i = 0; i < 9; i++) {
    const h = 1.2 + r() * 0.8, s = strip(h, 0.035, 5, 0.15 + r() * 0.25, 0.9, r() * 0.8);
    s.rotateY(r() * 6.28); s.translate((r() - 0.5) * 0.35, 0, (r() - 0.5) * 0.35);
    parts.push(paint(s, 0x40552a, 0x9aa25a, 0, h));
    if (r() < 0.3) parts.push(paint(new THREE.CylinderGeometry(0.03, 0.03, 0.2, 5).translate(0, h * 0.9, 0).translate((r() - 0.5) * 0.3, 0, (r() - 0.5) * 0.3), 0x5a3a22));
  }
  return merge(parts);
}

const palmCurve = (t, lean) => new THREE.Vector3(t * t * lean, t, 0);
// Palm: textured trunk (real UVs for the bark), fronds made of spine + paired leaflets.
export function palm(seed, { height = 7, lean = 0.9, fronds = 13, droop = 1 } = {}) {
  const r = rng(seed), trunk = [], up = new THREE.Vector3(0, 1, 0);
  for (let i = 0; i < 14; i++) {
    const a = palmCurve(i / 14, lean).multiply(new THREE.Vector3(1, height, 1)), b = palmCurve((i + 1) / 14, lean).multiply(new THREE.Vector3(1, height, 1));
    const rad = THREE.MathUtils.lerp(0.3, 0.18, i / 14) * (i === 0 ? 1.25 : 1);
    const c = new THREE.CylinderGeometry(rad * 0.9, rad * 1.08, a.distanceTo(b) * 1.03, 9, 1);
    const uv = c.attributes.uv; for (let k = 0; k < uv.count; k++) uv.setXY(k, uv.getX(k) * 1.5, (uv.getY(k) + i) * 0.55);
    c.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(up, b.clone().sub(a).normalize()));
    c.translate((a.x + b.x) / 2, (a.y + b.y) / 2, 0);
    trunk.push(paint(c, 0xb09a80));
  }
  const crown = palmCurve(1, lean).multiply(new THREE.Vector3(1, height, 1));
  for (let i = 0; i < 6; i++) {
    const d = new THREE.SphereGeometry(0.2, 7, 5); d.scale(1, 1.5, 1);
    d.translate(crown.x + Math.cos(i * 1.2) * 0.34, crown.y - 0.55 - r() * 0.15, Math.sin(i * 1.2) * 0.34);
    trunk.push(paint(d, 0xa4561c));
  }
  const leaves = [];
  for (let i = 0; i < fronds; i++) {
    const young = i >= fronds - 3, L = (young ? 2.4 : 3.2 + r() * 0.6);
    const lift = young ? 1.1 : 0.45 + r() * 0.3, sag = (young ? 0.05 : 0.2) * droop;
    const yaw = (young ? i / 3 : i / (fronds - 3)) * Math.PI * 2 + r() * 0.3, parts = [];
    const spinePt = t => new THREE.Vector3(0, lift * t * L - sag * (t * L) ** 2, t * L);
    for (let k = 0; k < 26; k++) {
      const t = 0.08 + k / 26 * 0.9, p = spinePt(t), len = 0.55 * Math.sin(Math.PI * Math.min(1, t * 1.1)) + 0.12;
      for (const side of [-1, 1]) {
        // leaflet points sideways, toward the tip and drooping; its face stays roughly skyward
        const lf = strip(len, 0.07, 2, 0.25, 0.9).rotateY(Math.PI / 2);
        const dir = new THREE.Vector3(side, -0.3 - t * 0.35 + (r() - 0.5) * 0.2, 0.55).normalize();
        lf.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(up, dir));
        lf.translate(p.x, p.y, p.z); parts.push(lf);
      }
    }
    const f = merge(parts);
    f.rotateY(yaw); f.translate(crown.x, crown.y, 0);
    leaves.push(paint(f, 0x55662a, 0x3f6a24, crown.y - 1.5, crown.y + 1));
  }
  return { trunk: merge(trunk), fronds: merge(leaves), crown };
}

// Broadleaf tree: recursive branches (bark UVs) with leaf clusters at the tips.
export function tree(seed, { height = 4, spread = 1, leafHue = 0 } = {}) {
  const r = rng(seed), wood = [], leaves = [], up = new THREE.Vector3(0, 1, 0);
  const branch = (from, dir, len, rad, depth) => {
    const to = from.clone().addScaledVector(dir, len);
    const c = new THREE.CylinderGeometry(rad * 0.7, rad, len, 6);
    const uv = c.attributes.uv; for (let k = 0; k < uv.count; k++) uv.setXY(k, uv.getX(k), uv.getY(k) * len);
    c.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(up, dir)); c.translate((from.x + to.x) / 2, (from.y + to.y) / 2, (from.z + to.z) / 2);
    wood.push(paint(c, 0x9c8a74));
    if (depth === 0 || rad < 0.03) {
      for (let k = 0; k < 42; k++) {
        const l = strip(0.16 + r() * 0.08, 0.09, 2, 0.4, 0.8);
        l.rotateX(r() * 6.28); l.rotateY(r() * 6.28); l.rotateZ(r() * 6.28);
        l.translate(to.x + (r() - 0.5) * 1.1 * spread, to.y + (r() - 0.3) * 0.8, to.z + (r() - 0.5) * 1.1 * spread);
        leaves.push(l);
      }
      return;
    }
    const n = 2 + (r() < 0.5 ? 1 : 0);
    for (let k = 0; k < n; k++) {
      const d = dir.clone().applyAxisAngle(new THREE.Vector3(1, 0, 0), (r() - 0.5) * 1.3).applyAxisAngle(up, r() * 6.28);
      d.y = Math.abs(d.y) * 0.8 + 0.25; d.normalize();
      branch(to, d, len * (0.62 + r() * 0.15), rad * 0.62, depth - 1);
    }
  };
  branch(new THREE.Vector3(0, -0.2, 0), new THREE.Vector3((r() - 0.5) * 0.2, 1, (r() - 0.5) * 0.2).normalize(), height * 0.4, 0.18 * height / 4, 3);
  const lg = merge(leaves);
  const col = new Float32Array(lg.attributes.position.count * 3), p = lg.attributes.position;
  for (let i = 0; i < p.count; i++) { C.setHSL(0.22 + leafHue + (r() - 0.5) * 0.04, 0.45, 0.2 + p.getY(i) / height * 0.14 + r() * 0.04); col.set([C.r, C.g, C.b], i * 3); }
  lg.setAttribute('color', new THREE.BufferAttribute(col, 3));
  return { wood: merge(wood), leaves: lg };
}

export function bush(seed) {
  const r = rng(seed), leaves = [];
  for (let k = 0; k < 72; k++) {
    const l = strip(0.17 + r() * 0.07, 0.1, 2, 0.4, 0.8), a = r() * 6.28, rr = Math.sqrt(r()) * 0.6;
    l.rotateX(r() * 6.28); l.rotateY(r() * 6.28);
    l.translate(Math.cos(a) * rr, 0.1 + r() * 0.6 * (1 - rr), Math.sin(a) * rr);
    leaves.push(paint(l, 0x3A6424, 0x7FAE44, 0, 0.7));   // toon_leaf_dark → toon_leaf_light
  }
  return merge(leaves);
}

export function lump(seed, detail = 1, yScale = 0.7) {
  const r = rng(seed), g = new THREE.IcosahedronGeometry(1, detail), a = g.attributes.position;
  const offs = Array.from({ length: 6 }, () => new THREE.Vector3(r() - 0.5, r() - 0.5, r() - 0.5).normalize());
  const v = new THREE.Vector3();
  for (let i = 0; i < a.count; i++) {
    v.fromBufferAttribute(a, i);
    let k = 1; for (const o of offs) k -= Math.max(0, v.dot(o) - 0.55) * 0.9;   // flat facets like a real stone
    a.setXYZ(i, v.x * k, v.y * k * yScale, v.z * k);
  }
  const m = mergeGeometries([g.toNonIndexed()]); m.computeVertexNormals();
  return paint(m, 0xffffff);
}

// Bougainvillea-style flowering shrub: leafy mound with clusters of pink/magenta bracts.
export function flowerBush(seed, hue = 0.92) {
  const r = rng(seed), parts = [];
  for (let k = 0; k < 150; k++) {
    const l = strip(0.13 + r() * 0.06, 0.08, 2, 0.4, 0.8), a = r() * 6.28, rr = Math.sqrt(r()) * 0.75;
    l.rotateX(r() * 6.28); l.rotateY(r() * 6.28);
    l.translate(Math.cos(a) * rr, 0.15 + r() * 1.1 * (1 - rr * 0.6), Math.sin(a) * rr);
    const bloom = r() < 0.55;
    const g = paint(l, 0x2c4a1a);
    if (bloom) { const c = new THREE.Color().setHSL(hue + (r() - 0.5) * 0.05, 0.75, 0.5 + r() * 0.12); const col = g.attributes.color; for (let i = 0; i < col.count; i++) col.setXYZ(i, c.r, c.g, c.b); }
    parts.push(g);
  }
  return merge(parts);
}
