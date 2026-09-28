// Soft blob shadows under the cast — LITE's stand-in for their real (per-frame) shadows.
// One instanced quad with a radial-gradient texture, laid on the ground under the child
// and every visible storyteller (and camel): a single draw call, no shadow map updates.
import { useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { refs } from '../systems/refs.js';
import { groundAt } from '../terrain/heightfield.js';
import { usePreset } from '../systems/store.js';
import { LAYER_NO_REFLECT } from '../systems/layers.js';

const MAX = 24;
function blobTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 64; const x = c.getContext('2d');
  const g = x.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, 'rgba(0,0,0,1)'); g.addColorStop(0.45, 'rgba(0,0,0,.75)'); g.addColorStop(1, 'rgba(0,0,0,0)');
  x.fillStyle = g; x.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}

export function Blobs() {
  const on = !!usePreset().staticShadow;
  const mesh = useMemo(() => {
    // tinted like the hemisphere shade (the cel shadow colour), not black
    const mat = new THREE.MeshBasicMaterial({ color: 0x5a3f5c, alphaMap: blobTexture(), transparent: true, opacity: 0.42, depthWrite: false,
      polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2, toneMapped: false });
    const m = new THREE.InstancedMesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2), mat, MAX);
    m.frustumCulled = false; m.renderOrder = 1; m.count = 0; m.name = 'blob-shadows';
    m.instanceMatrix.setUsage(THREE.DynamicDrawUsage); m.layers.set(LAYER_NO_REFLECT);
    return m;
  }, []);
  useFrame(() => {
    mesh.visible = on; if (!on) return;
    let n = 0;
    const put = (x, z, r, y = groundAt(x, z)) => {
      if (n >= MAX) return;
      _m.makeScale(r * 2, 1, r * 2).setPosition(x, y + 0.035, z); mesh.setMatrixAt(n++, _m);
    };
    const p = refs.player;
    if (p?.rig?.root) put(p.pos.x, p.pos.z, 0.42, p.pos.y);
    for (const npc of refs.npcs) {
      for (const m of npc.members) {
        const r = m.rig.root; if (!r.visible) continue;
        const [x, z] = m.def.position;
        put(m.sitting ? x : r.position.x, m.sitting ? z : r.position.z, m.sitting ? 0.55 : 0.45);
      }
      for (const c of npc.camels) if (c.visible) put(c.position.x, c.position.z, 1.1);
    }
    mesh.count = n; mesh.instanceMatrix.needsUpdate = true;
  });
  return <primitive object={mesh} />;
}
const _m = new THREE.Matrix4();
