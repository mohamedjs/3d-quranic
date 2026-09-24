// Draws placed models as instanced meshes (one per model × material × LOD) and moves each
// instance between the detailed and the simplified mesh by distance from the camera.
import * as THREE from 'three';

const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _e = new THREE.Euler(), _p = new THREE.Vector3(), _s = new THREE.Vector3();

export function instanceModels(assets, placements, { shadow = true, blocker = false, lodDistance = 45 } = {}) {
  const group = new THREE.Group(), sets = [];
  const byModel = new Map();
  for (const pl of placements) { if (!byModel.has(pl.model)) byModel.set(pl.model, []); byModel.get(pl.model).push(pl); }
  for (const [model, list] of byModel) {
    const a = assets[model]; if (!a) { console.warn('missing model', model); continue; }
    const matrices = list.map(pl => new THREE.Matrix4().compose(_p.set(pl.x, pl.y, pl.z), _q.setFromEuler(_e.set(pl.tilt ?? 0, pl.rot ?? 0, 0, 'YXZ')), _s.set(pl.sx ?? 1, pl.sy ?? pl.sx ?? 1, pl.sz ?? pl.sx ?? 1)));
    const mk = parts => parts?.map(({ geometry, material }) => {
      const m = new THREE.InstancedMesh(geometry, material, list.length);
      matrices.forEach((mx, i) => m.setMatrixAt(i, mx));
      m.computeBoundingSphere();                  // over all instances: stays valid as we re-sort
      m.castShadow = shadow; m.receiveShadow = true; m.userData.blocker = blocker; m.userData.shared = true; // geometry/material belong to the asset cache
      group.add(m); return m;
    });
    sets.push({ list, matrices, near: mk(a.lod0), far: mk(a.lod1) });
  }
  const cam = new THREE.Vector3();
  function update(cameraPos) {
    cam.copy(cameraPos);
    const d2 = lodDistance * lodDistance;
    for (const s of sets) {
      if (!s.far) continue;
      let n = 0, f = 0;
      s.list.forEach((pl, i) => {
        const near = (pl.x - cam.x) ** 2 + (pl.z - cam.z) ** 2 < d2;
        for (const m of near ? s.near : s.far) m.setMatrixAt(near ? n : f, s.matrices[i]);
        near ? n++ : f++;
      });
      for (const m of s.near) { m.count = n; m.instanceMatrix.needsUpdate = true; }
      for (const m of s.far) { m.count = f; m.instanceMatrix.needsUpdate = true; }
    }
  }
  return { group, update };
}
