// Hand-placed details around the canal where the farmer works. Composed on purpose:
// the sluice at the canal head, a shaduf lifting water, tools left mid-task, a palm-rib
// fence along the road, puddles where water spilled and footprints leading to him.
import * as THREE from 'three';
import { height, groundAt, rng, FOOTBRIDGES, FOOTBRIDGE_DECK } from '../terrain/heightfield.js';
import { paint, merge, lump } from '../vegetation/plants.js';


export function buildCanalScene(npcPos, home = null) {
  const r = rng(77), parts = { wood: [], clay: [], stone: [], cloth: [] }, colliders = [];
  const at = (x, z) => new THREE.Matrix4().setPosition(x, height(x, z), z);
  const put = (group, geo, color, M, rot) => { if (rot) geo.applyMatrix4(rot); const g = paint(geo, color); g.applyMatrix4(M); parts[group].push(g); };
  const collide = (x, z, hw, hd = hw) => colliders.push({ x0: x - hw, x1: x + hw, z0: z - hd, z1: z + hd });
  const CX = -15;

  // Blender models, placed with intent: sluice at the canal head, a shaduf lifting water,
  // a footbridge upstream, the farmer's tools and produce beside him, a palm-rib fence
  const placements = [];
  const place = (model, x, z, rot = 0, s = 1, dy = 0) => placements.push({ model, x, y: height(x, z) + dy, z, rot, sx: s, sy: s, sz: s });
  place('sluice', CX, 18.4, 0, 1, -0.05); collide(CX - 1.45, 18.4, 0.2); collide(CX + 1.45, 18.4, 0.2);
  const sx = CX - 1.9, sz = 24;
  place('shaduf', sx, sz, 0); collide(sx, sz, 0.3, 0.7);   // sweep (model +X) reaches out over the canal
  place('footbridge', CX, 34.5, 0, 1, 0.05);   // planks span the canal (model X)
  for (const b of FOOTBRIDGES) placements.push({ model: 'footbridge', x: b.x, y: FOOTBRIDGE_DECK - 0.14, z: b.z, rot: b.rot });   // across the road canals
  const [nx, nz] = npcPos;
  if (home) {                                  // at grandma's door: water jars past the doorway, her basket by the bench
    const w = (mx, mz) => [home.x + mx * Math.cos(home.rot) + mz * Math.sin(home.rot), home.z - mx * Math.sin(home.rot) + mz * Math.cos(home.rot)];
    const [jx, jz] = w(-1.55, 2.75), [bx, bz] = w(-2.1, 2.7), [kx, kz] = w(2.95, 2.75);
    place('jar', jx, jz, 0.3); collide(jx, jz, 0.3);
    place('jar_b', bx, bz, 1.2, 0.9);
    place('basket', kx, kz, 0.5);
  } else {
    place('jar', nx + 1.1, nz + 0.9, 0.3); collide(nx + 1.1, nz + 0.9, 0.3);
    place('jar_b', nx + 1.55, nz + 0.35, 1.2, 0.9);
    place('basket', nx - 1.2, nz + 1.1, 0.5);
  }
  place('hoe', CX + 1.25, 18.75, 0.2);
  placements[placements.length - 1].tilt = -0.3;                       // leaning on the sluice post
  for (const [a, b] of [[-42, -17.8], [-9.5, -3]]) {                  // gap: the canal path up to the farmer
    for (let x = a + 1.1; x < b; x += 2.25) place('fence', x, 15.4 + (r() - 0.5) * 0.1, (r() - 0.5) * 0.05);
    collide((a + b) / 2, 15.4, (b - a) / 2, 0.12);
  }

  // stones lining the canal banks
  for (let i = 0; i < 26; i++) {
    const z = 18.5 + r() * 20, s = r() < 0.5 ? -1 : 1, x = CX + s * (1.35 + r() * 0.5), sc = 0.12 + r() * 0.25;
    put('stone', lump(40 + i, 1, 0.6).scale(sc, sc, sc), 0xa89880, at(x, z));
  }

  // puddles and footprints are thin overlays, not merged into the lit geometry
  const overlays = new THREE.Group();
  const puddleMat = new THREE.MeshPhysicalMaterial({ color: 0x2a2018, roughness: 0.04, metalness: 0, clearcoat: 1, polygonOffset: true, polygonOffsetFactor: -2 });
  for (const [x, z, s] of [[CX + 2.1, 17.6, 0.9], [CX + 3.2, 16.9, 0.5], ...(home ? [] : [[nx + 0.6, nz - 1.4, 0.6]]), [-1.6, 6, 0.8]]) {
    const g = new THREE.CircleGeometry(1, 20), p = g.attributes.position;
    for (let i = 1; i < p.count; i++) { const k = 0.7 + r() * 0.45; p.setXY(i, p.getX(i) * k, p.getY(i) * k * 0.7); }
    const m = new THREE.Mesh(g, puddleMat); m.rotation.x = -Math.PI / 2; m.scale.setScalar(s);
    m.position.set(x, groundAt(x, z) + 0.015, z); m.receiveShadow = true; overlays.add(m);
  }
  const printMat = new THREE.MeshStandardMaterial({ color: 0x3b2a18, transparent: true, opacity: 0.4, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -3, roughness: 1 });
  const printGeo = new THREE.CircleGeometry(1, 10).scale(0.07, 0.13, 1);
  const trail = [];
  for (let z = -52; z < nz - 1.6; z += 0.55) trail.push([0.35 * Math.sin(z * 0.2) + Math.max(0, (z - nz + 8) / 8) * (nx - 0.3), z]);   // up the street to him
  const prints = new THREE.InstancedMesh(printGeo, printMat, trail.length);
  const q = new THREE.Quaternion(), e = new THREE.Euler(), one = new THREE.Vector3(1, 1, 1);
  trail.forEach(([x, z], i) => {
    const side = i % 2 ? 0.12 : -0.12, next = trail[Math.min(i + 1, trail.length - 1)], yaw = Math.atan2(next[0] - x, next[1] - z);
    const px = x + Math.cos(yaw) * side, pz = z - Math.sin(yaw) * side;
    prints.setMatrixAt(i, new THREE.Matrix4().compose(new THREE.Vector3(px, groundAt(px, pz) + 0.02, pz), q.setFromEuler(e.set(-Math.PI / 2, 0, yaw, 'YXZ')), one));
  });
  overlays.add(prints);

  const geometries = Object.fromEntries(Object.entries(parts).filter(([, l]) => l.length).map(([k, l]) => [k, merge(l)]));
  return { geometries, colliders, overlays, placements, clearings: [[nx, nz, 3.2], [CX, 18.4, 2.4], [sx, sz, 1.6], [CX, 35, 2]] };
}
