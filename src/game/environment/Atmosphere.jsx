// Subtle life in the air: sunlit dust/pollen around the player, gnat swarms over water and
// crops and birds wheeling in the distance.
import { useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { OASIS, rng, height, WATER_Y } from '../terrain/heightfield.js';
import { usePreset } from '../systems/store.js';
import { refs } from '../systems/refs.js';
import { LAYER_NO_REFLECT } from '../systems/layers.js';

function Motes({ count }) {
  const pts = useMemo(() => {
    const pos = new Float32Array(count * 3), seed = new Float32Array(count);
    for (let i = 0; i < count; i++) { pos.set([(Math.random() - 0.5) * 40, Math.random() * 8, (Math.random() - 0.5) * 40], i * 3); seed[i] = Math.random() * 100; }
    const g = new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(pos, 3)).setAttribute('seed', new THREE.BufferAttribute(seed, 1));
    const m = new THREE.PointsMaterial({ color: 0xffe6b8, size: 0.05, transparent: true, opacity: 0.55, depthWrite: false, blending: THREE.AdditiveBlending });
    const p = new THREE.Points(g, m); p.frustumCulled = false; p.layers.set(LAYER_NO_REFLECT);
    return p;
  }, [count]);
  useFrame((_, dt) => {
    const c = refs.player?.pos; if (!c) return;
    const a = pts.geometry.attributes.position, s = pts.geometry.attributes.seed, t = refs.clock.wind;
    dt *= refs.clock.scale;
    for (let i = 0; i < a.count; i++) {
      const k = s.array[i];
      let x = a.getX(i) + Math.sin(t * 0.4 + k) * dt * 0.25 + dt * 0.15, y = a.getY(i) + Math.sin(t * 0.7 + k * 2) * dt * 0.1 + dt * 0.03, z = a.getZ(i) + Math.cos(t * 0.3 + k) * dt * 0.25;
      if (x - c.x > 20) x -= 40; if (c.x - x > 20) x += 40; if (z - c.z > 20) z -= 40; if (c.z - z > 20) z += 40;
      if (y - c.y > 8) y -= 8; if (y < c.y) y += 8;
      a.setXYZ(i, x, y, z);
    }
    a.needsUpdate = true;
  });
  return <primitive object={pts} />;
}

// Small swarms of gnats hovering at fixed spots over the canal, river and crops.
function Swarms({ count }) {
  const pts = useMemo(() => {
    const r = rng(5), centers = [[-15, 22], [-15, 30], [-9, 26], [4, 64], [-30, 60], [OASIS.x + 12, OASIS.z + 4], [-5, 18]];
    const n = centers.length * count, pos = new Float32Array(n * 3), home = new Float32Array(n * 4);
    centers.forEach(([x, z], ci) => {
      const y = Math.max(height(x, z), WATER_Y) + 0.9;
      for (let j = 0; j < count; j++) { const i = ci * count + j; home.set([x, y, z, r() * 50], i * 4); pos.set([x, y, z], i * 3); }
    });
    const g = new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const p = new THREE.Points(g, new THREE.PointsMaterial({ color: 0x1a140e, size: 0.025, transparent: true, opacity: 0.8, depthWrite: false }));
    p.userData.home = home; p.frustumCulled = false; p.layers.set(LAYER_NO_REFLECT);
    return p;
  }, [count]);
  useFrame(() => {
    const a = pts.geometry.attributes.position, h = pts.userData.home, t = refs.clock.wind;
    for (let i = 0; i < a.count; i++) {
      const k = h[i * 4 + 3];
      a.setXYZ(i, h[i * 4] + Math.sin(t * 3.1 + k) * 0.35 + Math.sin(t * 7.3 + k * 3) * 0.08,
        h[i * 4 + 1] + Math.sin(t * 2.3 + k * 1.7) * 0.25, h[i * 4 + 2] + Math.cos(t * 2.7 + k) * 0.35 + Math.cos(t * 6.1 + k) * 0.08);
    }
    a.needsUpdate = true;
  });
  return <primitive object={pts} />;
}

function Birds({ count }) {
  const flock = useMemo(() => {
    const r = rng(99), g = new THREE.Group(), mat = new THREE.MeshBasicMaterial({ color: 0x4a3526, side: THREE.DoubleSide });
    const wing = new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute([0, 0, -0.12, 0, 0, 0.14, 0.75, 0.02, -0.05], 3));
    wing.computeVertexNormals();
    const body = new THREE.ConeGeometry(0.09, 0.5, 5).rotateX(Math.PI / 2), centers = [[OASIS.x, OASIS.z], [0, 60], [-50, 90], [40, -20], [120, 60]];
    const list = [];
    for (let i = 0; i < count; i++) {
      const b = new THREE.Group(), L = new THREE.Mesh(wing, mat), R = new THREE.Mesh(wing, mat); R.scale.x = -1;
      b.add(new THREE.Mesh(body, mat), L, R); g.add(b);
      const [cx, cz] = centers[i % centers.length];
      list.push({ b, L, R, cx: cx + (r() - 0.5) * 30, cz: cz + (r() - 0.5) * 30, rad: 15 + r() * 35, y: 22 + r() * 30, sp: (0.1 + r() * 0.1) * (r() < 0.5 ? -1 : 1), a: r() * 6.3, f: r() * 6 });
    }
    g.userData.list = list;
    return g;
  }, [count]);
  useFrame((_, dt) => {
    dt *= refs.clock.scale;
    for (const b of flock.userData.list) {
      b.a += b.sp * dt; b.f += dt * (7 + Math.sin(b.a * 3) * 3);
      const sg = Math.sign(b.sp);
      b.b.position.set(b.cx + Math.cos(b.a) * b.rad, b.y + Math.sin(b.a * 2) * 2, b.cz + Math.sin(b.a) * b.rad);
      b.b.rotation.set(0, Math.atan2(-Math.sin(b.a) * sg, Math.cos(b.a) * sg), -0.25 * sg);
      const flap = Math.sin(b.f) > -0.2 ? Math.sin(b.f) * 0.7 : -0.1;   // flap, then glide
      b.L.rotation.z = flap; b.R.rotation.z = -flap;
    }
  });
  return <primitive object={flock} />;
}

export function Atmosphere() {
  const q = usePreset().particles;
  return (
    <>
      <Motes count={Math.round(420 * q)} />
      <Swarms count={Math.round(22 * q)} />
      <Birds count={Math.round(28 * Math.max(q, 0.5))} />
    </>
  );
}
