// Plain mutable references shared between systems (not React state: read every frame).
export const refs = { player: null, npcs: [], colliders: [], terrain: null, sunDir: null, clock: { wind: 0, water: 0, scale: 1 },
  // what the exploration camera frames: ground focus (x, z), boom length and 0..1 zoom-out amount
  // (0 = close follow, 1 = bird's-eye). Vegetation, shadows and NPC markers read it.
  view: { x: 0, z: 0, dist: 5, zoom: 0, height: 2 } };
