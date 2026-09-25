// The scene graph. Suspends until the Blender models and story data are loaded, then
// builds everything once; the game loop starts when it mounts.
import { use, useMemo, useEffect, useRef } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import { Lighting } from '../lighting/Lighting.jsx';
import { loadEnvironment } from '../lighting/environmentMap.js';
import { Terrain } from '../terrain/Terrain.jsx';
import { buildTerrainGeometry } from '../terrain/terrainGeometry.js';
import { Water } from '../water/Water.jsx';
import { Vegetation } from '../vegetation/Vegetation.jsx';
import { Built } from '../buildings/Buildings.jsx';
import { buildVillage } from '../buildings/village.js';
import { buildCanalScene } from './details.js';
import { loadEnvModels } from './envAssets.js';
import { Props } from './Props.jsx';
import { Environment } from '../environment/Environment.jsx';
import { Player } from '../characters/Player.jsx';
import { NPC } from '../npc/NPC.jsx';
import { DialogueSystem } from '../components/DialogueSystem.jsx';
import { Effects } from '../effects/Effects.jsx';
import { createGame } from '../systems/game.js';
import { refs } from '../systems/refs.js';
import { normalizeEncounters } from '../systems/cast.js';
import { height } from '../terrain/heightfield.js';
import { makeLantern } from './lantern.js';

let dataPromise;
const loadData = () => (dataPromise ??= fetch('./data/encounters.json').then(r => {
  if (!r.ok) throw new Error('encounters.json: HTTP ' + r.status);
  return r.json();
}).then(normalizeEncounters));

export function World() {
  const env = use(loadEnvironment());
  const data = use(loadData());
  const assets = use(loadEnvModels());
  refs.sunDir = env.sunDir;

  const world = useMemo(() => {
    const terrain = buildTerrainGeometry();
    const village = buildVillage();
    const first = data.encounters[0], farmer = (first.characters.find(c => c.pose !== 'sit') ?? first.character).position;
    const canal = buildCanalScene(farmer, first.characters.some(c => c.pose === 'sit') ? village.home : null);
    const colliders = [...village.colliders, ...canal.colliders];
    const clearings = [...canal.clearings];
    for (const e of data.encounters) for (const c of e.characters) {
      const [x, z] = c.position;
      colliders.push({ x0: x - 0.35, x1: x + 0.35, z0: z - 0.35, z1: z + 0.35 });
      clearings.push([x, z, 2.2]);
      if (c.camel) { const [cx, cz] = c.camel; colliders.push({ x0: cx - 1.1, x1: cx + 1.1, z0: cz - 1.1, z1: cz + 1.1 }); clearings.push([cx, cz, 2]); }
    }
    clearings.push([village.home.x + 2.5, village.home.z, 5.5]);   // grandma's yard: no bushes on the stage
    // encounter set dressing: `props: [{ model, position:[x,z], rot, scale, tilt, dy, collide }]`,
    // `model` is an env GLB (models/env) or "lantern" (procedural, hung at `y` m above ground)
    const props = [], lanterns = [];
    for (const e of data.encounters) {                              // stage.clear: an open patch (no bushes/grass) round the cast
      const r = e.stage?.clear; if (!r) continue;
      const cx = e.characters.reduce((a, c) => a + c.position[0], 0) / e.characters.length, cz = e.characters.reduce((a, c) => a + c.position[1], 0) / e.characters.length;
      clearings.push([cx, cz, r]);
    }
    for (const e of data.encounters) for (const p of e.props ?? []) {
      const [x, z] = p.position, s = p.scale ?? 1;
      if (p.model === 'lantern') { lanterns.push(makeLantern({ x, z, y: height(x, z) + (p.y ?? 1.9), rot: p.rot ?? 0 })); continue; }
      props.push({ model: p.model, x, y: height(x, z) + (p.dy ?? -0.03), z, rot: p.rot ?? 0, tilt: p.tilt, sx: s, sy: s, sz: s });
      if (p.collide) colliders.push({ x0: x - p.collide, x1: x + p.collide, z0: z - p.collide, z1: z + p.collide });
      clearings.push([x, z, 0.8]);
    }
    return { terrain, village, canal, colliders, clearings, props, lanterns };
  }, [data]);

  // order matters: meshes the player needs (terrain, walls) mount first; <Player/> updates
  // the camera before <Water/> renders its passes; <GameSystem/> starts once all exist
  return (
    <>
      <Environment env={env} />
      <Lighting env={env} />
      <Terrain data={world.terrain} />
      <Built geometries={world.village.geometries} blocker />
      <Props assets={assets} placements={world.village.placements} blocker lodDistance={55} />
      <Built geometries={world.canal.geometries} />
      <Props assets={assets} placements={world.canal.placements} lodDistance={40} />
      <primitive object={world.canal.overlays} />
      {world.props.length > 0 && <Props assets={assets} placements={world.props} lodDistance={40} />}
      {world.lanterns.map((l, i) => <primitive key={'lantern' + i} object={l} />)}
      <Vegetation colliders={world.colliders} clearings={world.clearings} assets={assets} gardens={world.village.gardens} />
      <Player colliders={world.colliders} />
      {data.encounters.map(e => <NPC key={e.id} encounter={e} />)}
      <DialogueSystem />
      <GameSystem world={world} data={data} />
      <Water clock={refs.clock} />
      <Effects />
    </>
  );
}

// Starts the imperative game (player, NPCs, story, UI) once the scene exists.
function GameSystem({ world, data }) {
  const camera = useThree(s => s.camera), gl = useThree(s => s.gl);
  const game = useRef(null);
  useEffect(() => {
    game.current = createGame({ camera, mapCanvas: world.terrain.mapCanvas, data });
    if (window.__game) window.__game.renderer = gl;   // debug/perf probes (renderer.info)
    const l = document.getElementById('loading');
    l.classList.add('gone'); setTimeout(() => { l.hidden = true; }, 900);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useFrame((_, dt) => game.current?.tick(dt));
  return null;
}
