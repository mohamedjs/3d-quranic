import { builtMaterials } from './materials.js';

// One merged mesh per material group. `blocker`: the camera won't pass through it.
export function Built({ geometries, blocker = false }) {
  const mats = builtMaterials();
  return Object.entries(geometries).map(([k, g]) => (
    <mesh key={k} geometry={g} material={mats[k]} castShadow receiveShadow userData={{ blocker: blocker && k !== 'cloth' }} />
  ));
}
