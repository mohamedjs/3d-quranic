// Subtle life in the air: sunlit dust/pollen around the player, gnat swarms over water and
// crops, and soaring birds wheeling over the Nile & oasis as ONE instanced draw call.
import { useMemo, useEffect } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { OASIS, rng, height, WATER_Y } from '../terrain/heightfield.js';
import { usePreset } from '../systems/store.js';
import { refs } from '../systems/refs.js';
import { LAYER_NO_REFLECT } from '../systems/layers.js';
import { injectAerialFog } from '../shaders/stylizedPbr.js';

function Motes({ count }) {
  const pts = useMemo(() => {
    const pos = new Float32Array(count * 3), seed = new Float32Array(count);
    for (let i = 0; i < count; i++) { pos.set([(Math.random() - 0.5) * 40, Math.random() * 8, (Math.random() - 0.5) * 40], i * 3); seed[i] = Math.random() * 100; }
    const g = new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(pos, 3)).setAttribute('seed', new THREE.BufferAttribute(seed, 1));
    const m = new THREE.PointsMaterial({ color: 0xffe6b8, size: 0.05, transparent: true, opacity: 0.55, depthWrite: false, blending: THREE.AdditiveBlending });
    const p = new THREE.Points(g, m); p.frustumCulled = false; p.layers.set(LAYER_NO_REFLECT);
    return p;
  }, [count]);
  useEffect(() => () => { pts.geometry.dispose(); pts.material.dispose(); }, [pts]);
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
  useEffect(() => () => { pts.geometry.dispose(); pts.material.dispose(); }, [pts]);
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

// Sculpted gliding Nile kite / egret geometry with GPU-hinged flapping wings (1 InstancedMesh draw call!).
function buildBirdGeometry(count) {
  // Body (2 slender diamond triangles) + swept inner/outer left & right wing panels (10 tris total)
  const pos = new Float32Array([
    // sleek body + tail along +Z (nose) -> -Z (tail)
    0, 0.03, 0.34,   -0.08, 0, -0.04,   0.08, 0, -0.04,
    -0.08, 0, -0.04,  0.08, 0, -0.04,   0, 0.02, -0.34,
    // left inner wing (x > 0)
    0.05, 0.01, 0.14,  0.05, 0.01, -0.12,  0.42, 0.03, 0.02,
    0.05, 0.01, -0.12, 0.42, 0.03, -0.10,  0.42, 0.03, 0.02,
    // left outer swept tip
    0.42, 0.03, 0.02,  0.42, 0.03, -0.10,  0.84, 0.01, -0.14,
    // right inner wing (x < 0)
    -0.05, 0.01, 0.14, -0.42, 0.03, 0.02, -0.05, 0.01, -0.12,
    -0.05, 0.01, -0.12, -0.42, 0.03, 0.02, -0.42, 0.03, -0.10,
    // right outer swept tip
    -0.42, 0.03, 0.02, -0.84, 0.01, -0.14, -0.42, 0.03, -0.10,
  ]);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.computeVertexNormals();
  // Instanced per-bird flap angle (radians) updated lightly per frame
  const flaps = new Float32Array(count);
  g.setAttribute('aFlap', new THREE.InstancedBufferAttribute(flaps, 1));
  return g;
}

const _m = new THREE.Matrix4(), _p = new THREE.Vector3(), _q = new THREE.Quaternion(), _e = new THREE.Euler(), _s = new THREE.Vector3();

function Birds({ count }) {
  const flock = useMemo(() => {
    const r = rng(99);
    const geo = buildBirdGeometry(count);
    const mat = new THREE.MeshBasicMaterial({ color: 0x4d3728, side: THREE.DoubleSide, fog: true });
    mat.name = 'instanced_birds';
    mat.customProgramCacheKey = () => 'birds_v3_instanced';
    mat.onBeforeCompile = sh => {
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nattribute float aFlap;')
        .replace('#include <begin_vertex>', `#include <begin_vertex>
          {
            // Hinge left/right wings smoothly at shoulder (|x| > 0.06) with gentle outer tip flex
            float wx = abs(transformed.x);
            if (wx > 0.06) {
              float sgn = sign(transformed.x);
              float span = wx - 0.05;
              float ang = aFlap * (1.0 + span * 0.35);
              float c = cos(ang), s = sin(ang);
              float nx = span * c;
              float ny = span * s;
              transformed.x = sgn * (0.05 + nx);
              transformed.y += ny;
            }
          }`);
      injectAerialFog(sh);
    };

    const mesh = new THREE.InstancedMesh(geo, mat, count);
    mesh.name = 'birds';
    mesh.frustumCulled = false;
    mesh.castShadow = false;
    mesh.receiveShadow = false;
    mesh.layers.set(LAYER_NO_REFLECT);

    const centers = [[OASIS.x, OASIS.z], [0, 60], [-50, 90], [40, -20], [120, 60]];
    const list = [];
    for (let i = 0; i < count; i++) {
      const [cx, cz] = centers[i % centers.length];
      list.push({
        cx: cx + (r() - 0.5) * 32,
        cz: cz + (r() - 0.5) * 32,
        rad: 15 + r() * 35,
        y: 22 + r() * 28,
        sp: (0.10 + r() * 0.10) * (r() < 0.5 ? -1 : 1),
        a: r() * 6.3,
        f: r() * 6.0,
        sc: 0.85 + r() * 0.35,
      });
    }
    mesh.userData.list = list;
    return mesh;
  }, [count]);

  useEffect(() => () => { flock.geometry.dispose(); flock.material.dispose(); flock.dispose(); }, [flock]);

  useFrame((_, dt) => {
    dt *= refs.clock.scale;
    const list = flock.userData.list;
    const flapAttr = flock.geometry.attributes.aFlap;
    for (let i = 0; i < list.length; i++) {
      const b = list[i];
      b.a += b.sp * dt;
      b.f += dt * (7 + Math.sin(b.a * 3) * 3);
      const sg = Math.sign(b.sp);
      _p.set(b.cx + Math.cos(b.a) * b.rad, b.y + Math.sin(b.a * 2) * 2, b.cz + Math.sin(b.a) * b.rad);
      _e.set(0, Math.atan2(-Math.sin(b.a) * sg, Math.cos(b.a) * sg), -0.25 * sg, 'YXZ');
      _q.setFromEuler(_e);
      _s.setScalar(b.sc);
      _m.compose(_p, _q, _s);
      flock.setMatrixAt(i, _m);
      flapAttr.array[i] = Math.sin(b.f) > -0.2 ? Math.sin(b.f) * 0.68 : -0.10;   // flap, then soar
    }
    flock.instanceMatrix.needsUpdate = true;
    flapAttr.needsUpdate = true;
  });

  return <primitive object={flock} />;
}

export function Atmosphere() {
  const { particles: q, birds } = usePreset();
  // Now 1 instanced draw call total — Low gets 14 wheeling birds, Med 24, High 28, Ultra 36 (Lite: 0)
  const nBirds = birds ?? (q > 0 ? Math.max(14, Math.round(30 * q)) : 0);
  return (
    <>
      {q > 0 && <Motes count={Math.round(420 * q)} />}
      {q > 0 && <Swarms count={Math.round(22 * q)} />}
      {nBirds > 0 && <Birds count={nBirds} />}
    </>
  );
}
