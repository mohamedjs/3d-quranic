// Plain mutable references shared between systems (not React state: read every frame).
export const refs = { player: null, npcs: [], colliders: [], terrain: null, sunDir: null, clock: { wind: 0, water: 0, scale: 1 } };
