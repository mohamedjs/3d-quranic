// Story-spot set dressing for all 22 encounters (positions read from encounters.json at runtime).
// Places Poly Haven props (`ph_*`) plus occasional boulders, small rocks and shrubs so every
// storyteller inhabits a warm, fitting scene (e.g. stone fire pit for `ibrahim-and-the-fire` and
// `umar-and-the-widow`, water pots by Uthman's well, carved benches in village courtyards).
// Hard placement guards enforced at build time:
//   - >= 2.15 m clear of EVERY storyteller & camel across all 22 encounters
//   - off the roads (`pathDist > 1.75`) and out of the road->storyteller approach lane
//   - off water (`waterDist > 0.70`, `height > WATER_Y + 0.28`)
//   - clear of existing buildings, walls, stalls, well & other props
//   - ONLY large props (`ph_painted_wooden_bench`, `ph_stone_fire_pit`, `boulder`) emit colliders.
import { height, pathDist, waterDist, PATHS, WATER_Y } from '../terrain/heightfield.js';

const COLLIDER_RADII = {
  ph_painted_wooden_bench: [0.68, 0.36],
  ph_stone_fire_pit: [0.76, 0.76],
  boulder: [0.78, 0.62],
};

// Realistic scale defaults matching Poly Haven GLB real-world bounds (stool is 0.18 m raw, basket 0.11 m raw)
const DEFAULT_SCALE = {
  ph_brass_pot_01: 1.25,
  ph_brass_diya_lantern: 1.45,
  ph_ceramic_pot: 1.05,
  ph_painted_wooden_bench: 1.18,
  ph_wooden_stool_02: 2.15,
  ph_wicker_basket_01: 1.75,
  ph_stone_fire_pit: 1.12,
  boulder: 0.95,
  rock_small: 0.95,
  bush_a: 0.90,
  bush_b: 0.90,
};

// Table keyed by encounter id. Each item: [model, dx, dz, rot, scaleOverride?, dy?]
// Offsets (dx, dz) are relative to the encounter's character centroid read from encounters.json.
export const STORY_SETS = {
  // 1. Grandma's house & mastaba (house at x=-9.4, z=26; tellers at (-6.75,24.7), (-6,26.2); road x=0)
  'people-of-the-elephant': [
    ['ph_brass_diya_lantern', -1.8, -3.1, 0.4, 1.55],
    ['ph_brass_pot_01', -2.6, 2.7, 0.9, 1.3],
    ['ph_wooden_stool_02', -1.5, 3.1, 0.3, 2.1],
    ['ph_wicker_basket_01', -2.1, -3.6, 1.1, 1.7],
  ],
  // 2. Desert caravan camp (teller [112,-26.5], camel [114.8,-24.2], east road to north-west)
  'quraysh-journeys': [
    ['ph_stone_fire_pit', 3.4, -2.8, 0.5, 1.15],
    ['ph_brass_pot_01', 2.4, -3.5, 1.2, 1.3],
    ['ph_wicker_basket_01', 1.6, -2.9, 0.4, 1.85],
    ['ph_ceramic_pot', -2.8, -2.4, 2.1, 1.1],
    ['ph_wooden_stool_02', 4.3, -1.5, -0.7, 2.15],
    ['boulder', 5.2, -5.2, 0.9, 0.95],
    ['bush_b', -4.2, -3.8, 1.4, 0.95],
  ],
  // 3. Oasis arish storyteller ([-89.5,-7.5], arish at [-92,-9])
  'yusuf-dream': [
    ['ph_painted_wooden_bench', 3.0, 2.4, -2.4, 1.15],
    ['ph_brass_diya_lantern', 2.4, 1.3, 0.6, 1.45],
    ['ph_ceramic_pot', -3.6, 2.6, 0.8, 1.05],
    ['ph_wicker_basket_01', -2.5, 3.1, 1.9, 1.75],
    ['bush_a', 4.4, 3.2, 0.5, 0.95],
  ],
  // 4. Village dawn spot ([-27.2,18.2], field road z=14 to south)
  'threads-of-dawn': [
    ['ph_painted_wooden_bench', -3.1, 2.3, 0.9, 1.15],
    ['ph_brass_diya_lantern', -2.4, 1.2, 0.3, 1.45],
    ['ph_ceramic_pot', 2.7, 2.4, 1.4, 1.05],
    ['ph_wooden_stool_02', 2.2, 1.3, -0.5, 2.1],
    ['bush_a', -4.3, 3.5, 2.0, 0.9],
  ],
  // 5. Harvest fields farmer ([48,19.5], canal at x=45, road at z=14; keep props east/north!)
  'qays-the-fasting-farmer': [
    ['ph_ceramic_pot', 2.8, -1.6, 0.7, 1.15],
    ['ph_wicker_basket_01', 3.2, 1.8, 1.5, 1.85],
    ['ph_wooden_stool_02', 2.6, 2.4, 0.2, 2.1],
    ['ph_brass_pot_01', 3.5, -0.5, 2.2, 1.25],
    ['rock_small', 4.2, 1.2, 0.8, 1.0],
  ],
  // 6. Oasis west date-harvest grove ([-127.3,-38.6], [-129.1,-37])
  'best-dates': [
    ['ph_wicker_basket_01', -3.4, 2.2, 0.5, 1.9],
    ['ph_wicker_basket_01', -2.6, 2.9, 2.1, 1.7],
    ['ph_ceramic_pot', 3.4, -2.5, 1.1, 1.1],
    ['ph_wooden_stool_02', 2.9, -1.5, -0.4, 2.15],
    ['ph_brass_pot_01', 3.7, -1.8, 0.3, 1.25],
    ['bush_a', -4.6, -2.8, 1.3, 0.95],
  ],
  // 7. Village north-east courtyard ([20.4,24.6])
  'houses-by-their-doors': [
    ['ph_painted_wooden_bench', 3.2, 2.1, -1.1, 1.15],
    ['ph_brass_diya_lantern', 2.5, 1.0, 0.7, 1.45],
    ['ph_ceramic_pot', -2.8, 2.5, 1.6, 1.05],
    ['ph_wicker_basket_01', -2.1, 3.1, 0.4, 1.75],
    ['bush_a', 4.4, 3.2, 2.5, 0.9],
  ],
  // 8. Ancient sandstone ruins courtyard ([163,-139.4], [165,-139.9])
  'the-new-qibla': [
    ['boulder', -4.2, -3.5, 0.7, 1.05],
    ['ph_brass_diya_lantern', -3.0, -2.4, 0.2, 1.5],
    ['ph_ceramic_pot', 3.5, -2.9, 1.8, 1.1],
    ['ph_wooden_stool_02', 3.1, 2.7, -0.6, 2.15],
    ['rock_small', -2.9, 3.1, 1.4, 1.1],
    ['bush_b', 4.8, -4.1, 0.9, 0.95],
  ],
  // 9. Street hospitality lamp ([4.5,-40.9], [4.4,-44.1], street x=0, houses x>=5.5 -> place along front verge!)
  'the-guest-and-the-lamp': [
    ['ph_brass_diya_lantern', 0.3, 4.1, 0.4, 1.5],
    ['ph_brass_pot_01', 0.4, -3.9, 1.3, 1.3],
    ['ph_wooden_stool_02', -0.2, 4.9, -0.5, 2.1],
    ['ph_wicker_basket_01', 0.2, -4.8, 0.9, 1.75],
    ['ph_ceramic_pot', -0.4, -5.6, 1.6, 1.05],
  ],
  // 10. Northern rocky mountainside ([18,152])
  'companions-of-the-cave': [
    ['boulder', 3.6, 2.6, 0.4, 1.25],
    ['boulder', -3.8, 3.1, 2.2, 1.10],
    ['rock_small', 2.5, 2.9, 1.1, 1.15],
    ['ph_brass_diya_lantern', -2.4, 2.2, 0.5, 1.5],
    ['ph_ceramic_pot', 2.7, -1.9, 1.7, 1.05],
    ['bush_b', -4.6, -2.2, 0.8, 0.95],
  ],
  // 11. Village east wisdom square ([31,-5], [33.5,-6])
  'luqman-wisdom': [
    ['ph_painted_wooden_bench', 3.4, 2.9, -2.2, 1.18],
    ['ph_wooden_stool_02', -3.2, 2.6, 0.6, 2.15],
    ['ph_brass_pot_01', -2.5, 3.2, 1.2, 1.25],
    ['ph_ceramic_pot', 3.9, 1.4, 0.3, 1.05],
    ['bush_a', 4.8, 3.6, 1.7, 0.9],
  ],
  // 12. Ruins desert cave hillside ([156,-120])
  'abu-bakr-the-cave': [
    ['boulder', -3.6, -2.6, 1.1, 1.15],
    ['boulder', 3.9, -3.2, 2.6, 1.05],
    ['rock_small', -2.4, -3.1, 0.5, 1.1],
    ['ph_brass_diya_lantern', 2.5, -2.0, 0.3, 1.45],
    ['ph_wicker_basket_01', 2.9, 2.2, 1.8, 1.75],
    ['bush_b', -4.5, 2.4, 1.4, 0.95],
  ],
  // 13. Village square cooking hearth ([12,-4.2], [13.8,-6.4])
  'umar-and-the-widow': [
    ['ph_stone_fire_pit', 3.3, 2.4, 0.3, 1.08],
    ['ph_brass_pot_01', 2.5, 3.3, 1.1, 1.35],
    ['ph_wicker_basket_01', -3.2, 2.7, 0.8, 1.8],
    ['ph_ceramic_pot', -3.6, 1.5, 2.0, 1.05],
    ['ph_wooden_stool_02', 4.2, 1.1, -0.6, 2.1],
  ],
  // 14. Village square well ([-5,7.2], well is at [-5,4]!)
  'uthman-and-the-well': [
    ['ph_ceramic_pot', -2.6, -1.9, 0.6, 1.15],
    ['ph_brass_pot_01', -2.9, -2.9, 1.5, 1.3],
    ['ph_ceramic_pot', 2.5, -2.1, 2.3, 1.0],
    ['ph_wicker_basket_01', -2.8, 1.9, 0.9, 1.75],
    ['ph_wooden_stool_02', -3.4, 0.8, -0.4, 2.1],
    ['rock_small', -1.9, -4.4, 1.2, 0.85],
  ],
  // 15. Village west courtyard ([-26.7,-15.8], has lantern at [-27.95,-17.3])
  'ali-and-the-trusts': [
    ['ph_painted_wooden_bench', -3.1, 2.5, 0.7, 1.15],
    ['ph_wicker_basket_01', 2.6, -2.4, 1.4, 1.85],
    ['ph_brass_diya_lantern', 2.8, -1.4, 0.2, 1.45],
    ['ph_ceramic_pot', -2.5, -3.1, 1.9, 1.05],
    ['ph_wooden_stool_02', 2.9, 2.2, -0.8, 2.15],
  ],
  // 16. Nile bank east of bridge ([10,62], [7.5,62.8])
  'nuh-and-the-ark': [
    ['ph_painted_wooden_bench', 3.6, -2.4, -0.6, 1.18],
    ['ph_wooden_stool_02', 2.7, -3.2, 0.8, 2.15],
    ['ph_wicker_basket_01', -3.4, -2.6, 1.3, 1.85],
    ['ph_ceramic_pot', -2.8, -3.5, 0.4, 1.05],
    ['boulder', 4.9, 2.2, 1.7, 0.95],
    ['rock_small', -4.2, 1.9, 0.9, 1.0],
  ],
  // 17. Desert hearth — Ibrahim & the fire ([141,-50], [143,-51.2])
  'ibrahim-and-the-fire': [
    ['ph_stone_fire_pit', 3.5, 2.6, 0.4, 1.22],
    ['boulder', 5.2, 4.1, 1.2, 1.15],
    ['boulder', -4.4, -3.4, 2.5, 1.00],
    ['ph_brass_pot_01', 2.4, 3.6, 0.9, 1.35],
    ['ph_brass_diya_lantern', 4.5, 1.4, 0.2, 1.55],
    ['ph_ceramic_pot', -3.2, 2.4, 1.6, 1.1],
    ['ph_wooden_stool_02', 2.7, -2.8, -0.5, 2.15],
    ['bush_b', -4.8, 3.2, 0.7, 0.95],
    ['rock_small', 4.2, 3.8, 1.9, 1.0],
  ],
  // 18. Riverside canal cove ([-41.8,32], canal x=-45 to west -> stay east/south!)
  'musa-on-the-river': [
    ['ph_wicker_basket_01', 2.6, 1.6, 0.7, 1.85],
    ['ph_ceramic_pot', 2.9, -1.8, 1.5, 1.1],
    ['ph_wooden_stool_02', 2.5, -2.7, 0.3, 2.1],
    ['boulder', 4.5, 2.6, 2.1, 0.90],
    ['rock_small', 3.4, 2.8, 0.4, 0.95],
    ['bush_a', 4.6, -2.5, 1.2, 0.9],
  ],
  // 19. Oasis palm shade ([-95.96,-8.61], oasis pond south-west, arish east)
  'isa-in-the-cradle': [
    ['ph_wooden_stool_02', -2.7, 2.2, 0.5, 2.1],
    ['ph_ceramic_pot', -2.1, 3.0, 1.3, 1.05],
    ['ph_brass_diya_lantern', 2.4, 2.8, 0.2, 1.45],
    ['ph_wicker_basket_01', -3.4, 1.2, 2.1, 1.75],
    ['bush_a', -4.2, 3.4, 0.9, 0.9],
  ],
  // 20. North mountain hillside overlook ([5,125], [7.6,125.6])
  'muhammad-the-trustworthy': [
    ['ph_painted_wooden_bench', 3.4, -2.6, -2.6, 1.18],
    ['ph_brass_diya_lantern', 2.6, -1.6, 0.6, 1.5],
    ['ph_brass_pot_01', -2.8, -2.8, 1.4, 1.3],
    ['boulder', 5.0, 2.8, 0.8, 1.10],
    ['bush_b', -4.2, 2.6, 1.9, 0.95],
    ['rock_small', 4.1, 1.9, 0.3, 1.05],
  ],
  // 21. Nile bank west of bridge ([-9,62], [-11.6,61])
  'yunus-and-the-whale': [
    ['boulder', -4.2, -2.8, 1.4, 1.00],
    ['rock_small', -3.0, -3.5, 0.6, 1.05],
    ['ph_wicker_basket_01', 3.2, -2.4, 1.1, 1.85],
    ['ph_ceramic_pot', 3.7, -1.5, 2.2, 1.1],
    ['ph_wooden_stool_02', -2.9, -2.4, -0.4, 2.1],
    ['bush_a', -5.2, -1.6, 0.8, 0.95],
  ],
  // 22. Oasis south valley ([-88,-27.5], [-90.6,-28.5])
  'sulayman-and-the-ant': [
    ['boulder', 3.9, -2.8, 0.7, 1.00],
    ['rock_small', 2.8, -3.4, 1.5, 1.0],
    ['ph_wooden_stool_02', -3.2, -2.6, 0.4, 2.1],
    ['ph_ceramic_pot', -3.8, -1.8, 1.9, 1.05],
    ['ph_brass_pot_01', 2.9, -2.1, 0.8, 1.25],
    ['bush_a', 4.6, -1.4, 2.1, 0.95],
  ],
};

const SEGS = PATHS.flatMap(p => p.slice(1).map((b, i) => [p[i], b]));
function nearestRoadPoint(x, z) {
  let bestD = Infinity, bx = x, bz = z;
  for (const [[ax, az], [px, pz]] of SEGS) {
    const dx = px - ax, dz = pz - az, len2 = dx * dx + dz * dz;
    const t = Math.max(0, Math.min(1, ((x - ax) * dx + (z - az) * dz) / (len2 || 1)));
    const qx = ax + dx * t, qz = az + dz * t, d = Math.hypot(x - qx, z - qz);
    if (d < bestD) { bestD = d; bx = qx; bz = qz; }
  }
  return [bx, bz, bestD];
}

function segDist(x, z, ax, az, bx, bz) {
  const dx = bx - ax, dz = bz - az, len2 = dx * dx + dz * dz;
  if (len2 < 1e-4) return Math.hypot(x - ax, z - az);
  const t = Math.max(0, Math.min(1, ((x - ax) * dx + (z - az) * dz) / len2));
  return Math.hypot(x - (ax + dx * t), z - (az + dz * t));
}

export function buildStorySets(encounters, existingColliders = []) {
  const placements = [];
  const colliders = [];
  const clearings = [];

  // Collect ALL storyteller and camel positions across all 22 encounters for strict >= 2.0 m clearance
  const tellers = [];
  for (const e of encounters) {
    for (const c of e.characters ?? []) {
      tellers.push(c.position);
      if (c.camel) tellers.push(c.camel);
    }
  }

  const allCols = [...existingColliders];
  const placed = [];

  const isSafe = (x, z, model, sc, encCenter, roadPt) => {
    const h = height(x, z);
    if (h < WATER_Y + 0.30 || h > 15.0) return false;
    if (waterDist(x, z) < 0.75) return false;
    if (pathDist(x, z) <= 1.75) return false;
    // Stay >= 2.15 m away from EVERY storyteller & camel (spec: >= 2.0 m)
    for (const [tx, tz] of tellers) {
      if (Math.hypot(x - tx, z - tz) < 2.15) return false;
    }
    // Keep approach lane from the nearest road point to the encounter completely unobstructed
    if (roadPt[2] < 24 && segDist(x, z, encCenter[0], encCenter[1], roadPt[0], roadPt[1]) < 1.65) return false;
    // Avoid overlapping existing buildings/walls/props and previously placed storySet props
    const rad = COLLIDER_RADII[model] ? Math.max(COLLIDER_RADII[model][0], COLLIDER_RADII[model][1]) * sc : 0.45;
    const pad = rad + 0.40;
    for (const b of allCols) {
      if (x > b.x0 - pad && x < b.x1 + pad && z > b.z0 - pad && z < b.z1 + pad) return false;
    }
    for (const [px, pz, pr] of placed) {
      if (Math.hypot(x - px, z - pz) < Math.max(0.72, rad + pr + 0.15)) return false;
    }
    return true;
  };

  for (const e of encounters) {
    const items = STORY_SETS[e.id];
    if (!items?.length || !e.characters?.length) continue;
    const cx = e.characters.reduce((a, c) => a + c.position[0], 0) / e.characters.length;
    const cz = e.characters.reduce((a, c) => a + c.position[1], 0) / e.characters.length;
    const roadPt = nearestRoadPoint(cx, cz);

    for (const [model, dx, dz, rot = 0, sOverride, dy = -0.02] of items) {
      const sc = sOverride ?? DEFAULT_SCALE[model] ?? 1;
      let tx = cx + dx, tz = cz + dz;
      let ok = isSafe(tx, tz, model, sc, [cx, cz], roadPt);
      if (!ok) {
        // Gentle local nudge around the desired spot so the prop stays nearby while respecting every guard
        outer: for (const rad of [0.6, 1.2, 1.8, 2.5]) {
          for (let k = 0; k < 12; k++) {
            const a = (k / 12) * Math.PI * 2;
            const nx = cx + dx + Math.cos(a) * rad, nz = cz + dz + Math.sin(a) * rad;
            if (isSafe(nx, nz, model, sc, [cx, cz], roadPt)) { tx = nx; tz = nz; ok = true; break outer; }
          }
        }
      }
      if (!ok) continue;

      const y = height(tx, tz) + (model === 'boulder' ? -0.08 * sc : model === 'rock_small' ? -0.04 * sc : dy);
      placements.push({ model, x: tx, y, z: tz, rot, sx: sc, sy: sc, sz: sc });

      const cSpec = COLLIDER_RADII[model];
      const ownR = cSpec ? Math.max(cSpec[0], cSpec[1]) * sc : 0.42;
      placed.push([tx, tz, ownR]);
      clearings.push([tx, tz, Math.max(0.85, ownR + 0.45)]);

      // Only large props (bench, fire pit, boulder) emit colliders
      if (cSpec) {
        const c = Math.abs(Math.cos(rot)), s = Math.abs(Math.sin(rot));
        const hw = (c * cSpec[0] + s * cSpec[1]) * sc;
        const hd = (s * cSpec[0] + c * cSpec[1]) * sc;
        const box = { x0: tx - hw, x1: tx + hw, z0: tz - hd, z1: tz + hd };
        colliders.push(box);
        allCols.push(box);
      }
    }
  }

  return { placements, colliders, clearings };
}
