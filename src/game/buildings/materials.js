// Shared toon materials for everything built by hand (river bridge, oasis shelter, ruins):
// merged geometry carries its colour per vertex, the cel material lights it.
import { toonMaterial } from '../shaders/toon.js';

let mats;
export function builtMaterials() {
  mats ??= Object.fromEntries(['plaster', 'wood', 'stone', 'cloth', 'clay'].map(k => [k, toonMaterial('built_' + k, { vertexColors: true })]));
  return mats;
}
