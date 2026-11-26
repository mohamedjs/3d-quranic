import { trackReady } from '../../telemetry.js';
import { perfFrame } from '../../perf.js';
// The scene graph. Suspends until the Blender models and story data are loaded, then
// builds everything once; the game loop starts when it mounts.
import { use, useMemo, useEffect, useRef, useState, lazy, Suspense } from 'react';
import * as THREE from 'three';
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
import { buildStorySets } from './storySets.js';
import { loadEnvModels } from './envAssets.js';
import { syncBuildingShading } from '../shaders/buildingMaterial.js';
import { syncPropShading } from '../shaders/propMaterial.js';
import { Props } from './Props.jsx';
import { Environment } from '../environment/Environment.jsx';
import { Player } from '../characters/Player.jsx';
import { Blobs } from '../characters/Blobs.jsx';
import { NPC } from '../npc/NPC.jsx';
import { DialogueSystem } from '../components/DialogueSystem.jsx';
import { usePreset, useGame, useDetail } from '../systems/store.js';
import { createGame } from '../systems/game.js';
import { refs } from '../systems/refs.js';
import { normalizeEncounters } from '../systems/cast.js';
import { height } from '../terrain/heightfield.js';
import { makeLantern } from './lantern.js';
import { PRESETS } from '../systems/quality.js';
import { LAYER_NO_REFLECT } from '../systems/layers.js';

// Small non-blocker village dressing props merged per chunk × material on every tier
const VILLAGE_DRESSING = new Set(['pot_plant', 'jar', 'jar_b', 'hay']);

// Post-processing is its own chunk, fetched only on levels that use it. Without it (LOW) the
// renderer does the neutral tone mapping itself, so colours stay the same.
const Effects = lazy(() => import('../effects/Effects.jsx').then(m => ({ default: m.Effects })));
function PostFX() {
  const post = usePreset().post, gl = useThree(s => s.gl);
  useEffect(() => { gl.toneMapping = post ? THREE.NoToneMapping : THREE.CustomToneMapping; }, [gl, post]);
  return post ? <Suspense fallback={null}><Effects /></Suspense> : null;
}

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
  const scene = useThree(s => s.scene);
  const bldShading = usePreset().shading ?? 'toon';
  const detail = useGame(s => s.detail);
  const lite = !!useDetail().lite;
  useEffect(() => {
    syncBuildingShading(assets, scene, bldShading);
    syncPropShading(assets, scene, bldShading);
  }, [assets, scene, bldShading, lite, detail]);

  const world = useMemo(() => {
    (window.__builds ??= []).push('world:' + useGame.getState().detail);   // test probe: the world must be built exactly once
    const terrain = buildTerrainGeometry(PRESETS[useGame.getState().detail].terrainSeg);
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
      if (p.model === 'lantern') {
        const lan = makeLantern({ x, z, y: height(x, z) + (p.y ?? 1.9), rot: p.rot ?? 0 });
        lan.traverse(o => o.layers.set(LAYER_NO_REFLECT));
        lanterns.push(lan);
        continue;
      }
      props.push({ model: p.model, x, y: height(x, z) + (p.dy ?? -0.03), z, rot: p.rot ?? 0, tilt: p.tilt, sx: s, sy: s, sz: s });
      if (p.collide) colliders.push({ x0: x - p.collide, x1: x + p.collide, z0: z - p.collide, z1: z + p.collide });
      clearings.push([x, z, 0.8]);
    }
    canal.overlays.traverse(o => o.layers.set(LAYER_NO_REFLECT));
    // v4 Poly Haven story-spot dressing for all 22 encounters (safe clearance + large-prop colliders)
    const storySets = buildStorySets(data.encounters, colliders);
    colliders.push(...storySets.colliders);
    clearings.push(...storySets.clearings);
    return { terrain, village, canal, storySets, colliders, clearings, props, lanterns };
  }, [data]);

  // LITE: every placed model (village, canal, story props and the trees from <Vegetation/>) goes
  // into ONE merged-chunk set, so a 24 m cell costs minimal draw calls whatever it holds
  const [treePl, setTreePl] = useState(null);
  const litePl = useMemo(() => (lite ? [
    ...world.village.placements.map(p => ({ ...p, blocker: !VILLAGE_DRESSING.has(p.model) })),
    ...world.canal.placements, ...world.props, ...world.storySets.placements, ...(treePl ?? []),
  ] : null), [lite, world, treePl]);

  // Non-Lite: split major village architecture (camera blockers) from dressing props, which are
  // merged per chunk × material on EVERY tier to keep draw calls down.
  const villageMajor = useMemo(() => (!lite ? world.village.placements.filter(p => !VILLAGE_DRESSING.has(p.model)) : null), [lite, world]);
  const dressingPl = useMemo(() => (!lite ? [
    ...world.village.placements.filter(p => VILLAGE_DRESSING.has(p.model)),
    ...world.canal.placements, ...world.props, ...world.storySets.placements,
  ] : null), [lite, world]);

  // order matters: meshes the player needs (terrain, walls) mount first; <Player/> updates
  // the camera before <Water/> renders its passes; <GameSystem/> starts once all exist
  return (
    <>
      <Environment env={env} />
      <Lighting env={env} />
      <Terrain data={world.terrain} />
      <Built geometries={world.village.geometries} blocker />
      {!lite && <Props assets={assets} placements={villageMajor} blocker lodDistance={40} />}
      <Built geometries={world.canal.geometries} />
      {!lite && dressingPl.length > 0 && <Props assets={assets} placements={dressingPl} mergeDressing />}
      {!lite && <primitive object={world.canal.overlays} />}{/* puddles + footprints: not on LITE */}
      {lite && <Props assets={assets} placements={litePl} />}
      {world.lanterns.map((l, i) => <primitive key={'lantern' + i} object={l} />)}
      <Vegetation colliders={world.colliders} clearings={world.clearings} assets={assets} gardens={world.village.gardens} onTrees={lite ? setTreePl : null} />
      <Player colliders={world.colliders} />
      <Blobs />
      {data.encounters.map(e => <NPC key={e.id} encounter={e} />)}
      <DialogueSystem />
      <GameSystem world={world} data={data} />
      <Water clock={refs.clock} />
      <PostFX />
    </>
  );
}

// Starts the imperative game (player, NPCs, story, UI) once the scene exists.
function GameSystem({ world, data }) {
  const camera = useThree(s => s.camera), gl = useThree(s => s.gl), scene = useThree(s => s.scene);
  const game = useRef(null);
  useEffect(() => {
    game.current = createGame({ camera, mapCanvas: world.terrain.mapCanvas, data, scene, colliders: world.colliders });
    if (window.__game) { window.__game.renderer = gl; window.__game.scene = scene; window.__game.store = useGame; }   // debug/perf probes (renderer.info)
    // Keep the loading screen up until the world is really ready: every shader compiled and
    // the first frames drawn and settled — so the title screen never stutters or freezes.
    let alive = true;
    (async () => {
      const l = document.getElementById('loading'), msg = l?.querySelector('p');
      if (msg) msg.textContent = 'نجهّز كل شيء… · Getting everything ready…';
      try { await (gl.compileAsync ? gl.compileAsync(scene, camera) : gl.compile(scene, camera)); } catch (e) { console.warn('[warm-up] compile', e); }
      const t0 = performance.now();
      await new Promise(done => {
        const check = () => {
          if (!alive) return done();
          const f = frames.current, recent = f.dts.slice(-10), avg = recent.reduce((a, b) => a + b, 0) / Math.max(1, recent.length);
          // 30+ frames drawn and the last ten smooth (< 70 ms), or give up waiting after 12 s
          if ((f.n >= 30 && recent.length === 10 && avg < 0.07) || performance.now() - t0 > 12000) return done();
          requestAnimationFrame(check);
        };
        check();
      });
      if (window.__game) window.__game.warmup = +(performance.now() - t0).toFixed(0);
      l.classList.add('gone'); setTimeout(() => { l.hidden = true; }, 900); trackReady();
    })();
    return () => { alive = false; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const frames = useRef({ n: 0, dts: [] });
  useFrame((state, dt) => { const f = frames.current; f.n++; f.dts.push(dt); if (f.dts.length > 20) f.dts.shift(); game.current?.tick(dt); perfFrame(dt, state.gl); });
  return null;
}
