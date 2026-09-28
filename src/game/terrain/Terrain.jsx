import { useMemo, useEffect, useRef } from 'react';
import * as THREE from 'three';
import { useFrame, useThree } from '@react-three/fiber';
import { createTerrainMaterial } from '../shaders/terrainMaterial.js';
import { useDetail, usePreset } from '../systems/store.js';
import { refs } from '../systems/refs.js';
import { SIZE } from './heightfield.js';

// LITE draws the terrain as 4×4 tiles that share one vertex buffer (each tile only has its own
// index list), so frustum culling and the fog distance skip most of the 520 m ground; the full
// mesh stays in the scene, hidden, for tap-to-walk ray casts.
const TILES = 4;
function tiles(geo, seg) {
  const row = seg + 1, n = Math.ceil(seg / TILES), pos = geo.attributes.position, out = [];
  for (let tz = 0; tz < TILES; tz++) for (let tx = 0; tx < TILES; tx++) {
    const r0 = tz * n, r1 = Math.min(seg, r0 + n), c0 = tx * n, c1 = Math.min(seg, c0 + n), idx = [];
    let y0 = Infinity, y1 = -Infinity;
    for (let r = r0; r < r1; r++) for (let c = c0; c < c1; c++) {
      const a = r * row + c, b = a + row;
      idx.push(a, b, a + 1, b, b + 1, a + 1);                      // PlaneGeometry's winding
      y0 = Math.min(y0, pos.getY(a)); y1 = Math.max(y1, pos.getY(a));
    }
    const g = new THREE.BufferGeometry();
    for (const [k, v] of Object.entries(geo.attributes)) g.setAttribute(k, v);   // shared: uploaded once
    g.setIndex(idx);
    const x0 = -SIZE / 2 + c0 * SIZE / seg, x1 = -SIZE / 2 + c1 * SIZE / seg, z0 = -SIZE / 2 + r0 * SIZE / seg, z1 = -SIZE / 2 + r1 * SIZE / seg;
    g.boundingBox = new THREE.Box3(new THREE.Vector3(x0, y0 - 1, z0), new THREE.Vector3(x1, y1 + 1, z1));
    g.boundingSphere = g.boundingBox.getBoundingSphere(new THREE.Sphere());
    out.push({ g, x0, x1, z0, z1 });
  }
  return out;
}

export function Terrain({ data, onReady }) {
  const material = useMemo(() => createTerrainMaterial(), []);
  const lite = !!useDetail().lite && data.seg;
  const parts = useMemo(() => (lite ? tiles(data.geometry, data.seg) : null), [lite, data]);
  const fog = usePreset().fog, camera = useThree(s => s.camera), group = useRef(), acc = useRef(0);
  useEffect(() => { onReady?.(); }, [onReady]);
  useFrame((_, dt) => {
    if (!parts || !group.current || (acc.current += dt) < 0.25) return; acc.current = 0;
    const far = (fog?.[1] ?? 620) + refs.view.dist * 3 + 20, p = camera.position;
    group.current.children.forEach((m, i) => {
      const t = parts[i], dx = Math.max(t.x0 - p.x, 0, p.x - t.x1), dz = Math.max(t.z0 - p.z, 0, p.z - t.z1);
      m.visible = Math.hypot(dx, dz) < far;
    });
  });
  if (!parts) return <mesh name="terrain" geometry={data.geometry} material={material} receiveShadow />;
  return (
    <>
      <mesh name="terrain" geometry={data.geometry} material={material} visible={false} />
      <group ref={group} name="terrain-tiles">
        {parts.map((t, i) => <mesh key={i} geometry={t.g} material={material} receiveShadow />)}
      </group>
    </>
  );
}
