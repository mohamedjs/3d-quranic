// Shared triplanar PBR materials for everything built by hand (village, ruins, props).
import { triplanarMaterial } from '../shaders/triplanar.js';
import { pbrSet } from '../systems/textures.js';

let mats;
export function builtMaterials() {
  mats ??= {
    plaster: triplanarMaterial(pbrSet('clay_plaster'), { scale: 2.2, key: 'plaster' }),
    wood: triplanarMaterial(pbrSet('old_planks_02'), { scale: 1.2, key: 'wood', normalScale: 1.2 }),
    stone: triplanarMaterial(pbrSet('large_sandstone_blocks'), { scale: 2.6, key: 'stone' }),
    cloth: triplanarMaterial(pbrSet('cotton_jersey'), { scale: 0.35, key: 'cloth' }),
    clay: triplanarMaterial(pbrSet('clay_plaster'), { scale: 0.8, key: 'clay', roughness: 0.8 }),
  };
  return mats;
}
