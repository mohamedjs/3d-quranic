import * as THREE from 'three';
import { Sky } from 'three/addons/objects/Sky.js';
import { buildTerrain, buildWater, SPAWN, groundAt, waterDist, onBridge, pathDist } from './terrain.js';
import { buildNature, Birds, Motes, wind } from './nature.js';
import { buildVillage } from './buildings.js';
import { makeChild, makeElder, makeCamel } from './characters.js';
import { Player } from './player.js';
import { Sound, Voice } from './audio.js';
import { primeAudio, playRecitation } from './recitation.js';
import { DEFAULT_RECITER } from './quran.js';
import { Story } from './story.js';
import { UI, STR, MEDAL } from './ui.js';

// ---- save ---------------------------------------------------------------
const SAVE_KEY = 'quran-journey-v1';
const fresh = () => ({ done: [], points: 0, discovered: [], pos: null, seenHint: false,
  settings: { lang: 'ar', reciter: DEFAULT_RECITER, voice: true, meaning: true, volume: 0.7, music: false } });
function loadSave() {
  const f = fresh();
  try { const s = JSON.parse(localStorage.getItem(SAVE_KEY)); if (s) return { ...f, ...s, settings: { ...f.settings, ...s.settings } }; } catch { /* private mode */ }
  return f;
}
let save = loadSave();
const persist = () => { try { localStorage.setItem(SAVE_KEY, JSON.stringify(save)); } catch { /* not fatal */ } };

// ---- renderer, sky, light ---------------------------------------------------
const canvas = document.getElementById('c');
const low = matchMedia('(pointer: coarse)').matches || innerWidth < 800;
let renderer;
try { renderer = new THREE.WebGLRenderer({ canvas, antialias: !low, powerPreference: 'high-performance' }); }
catch (e) {
  document.querySelector('#loading .spin').hidden = true;
  document.querySelector('#loading p').textContent = 'This game needs WebGL (3D graphics), which is turned off in this browser. Try Chrome, Edge, Firefox or Safari with hardware acceleration on. — تحتاج اللعبة إلى WebGL؛ جرّب متصفحًا آخر.';
  throw e;
}
renderer.setPixelRatio(Math.min(devicePixelRatio, low ? 1.25 : 1.75));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
const EXPOSURE = 0.6; renderer.toneMappingExposure = EXPOSURE;

const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0xe9b88a, 90, 620);
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.1, 5000);

const sunDir = new THREE.Vector3(-0.5, 0.13, 0.86).normalize();
const makeSky = () => {
  const s = new Sky(); s.scale.setScalar(4500);
  const u = s.material.uniforms;
  u.turbidity.value = 9; u.rayleigh.value = 2.6; u.mieCoefficient.value = 0.008; u.mieDirectionalG.value = 0.88;
  u.sunPosition.value.copy(sunDir);
  return s;
};
scene.add(makeSky());
const pmrem = new THREE.PMREMGenerator(renderer), envScene = new THREE.Scene();
envScene.add(makeSky());
scene.environment = pmrem.fromScene(envScene).texture;
scene.environmentIntensity = 0.55;

const hemi = new THREE.HemisphereLight(0xffd9b0, 0x5a4a30, 0.7);
const sun = new THREE.DirectionalLight(0xffc27a, 3.4);
sun.castShadow = true; sun.shadow.mapSize.setScalar(low ? 1024 : 2048);
Object.assign(sun.shadow.camera, { left: -45, right: 45, top: 45, bottom: -45, near: 1, far: 320 });
sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.03;
scene.add(hemi, sun, sun.target);

const status = document.querySelector('#loading p');
const frame = () => new Promise(r => requestAnimationFrame(() => setTimeout(r, 0)));

// ---- build --------------------------------------------------------------
status.textContent = STR[save.settings.lang].building;
await frame();
const data = await fetch('data/encounters.json').then(r => { if (!r.ok) throw new Error('encounters.json ' + r.status); return r.json(); });
const terrain = buildTerrain(); scene.add(terrain.mesh);
const water = buildWater(sunDir); scene.add(water);
await frame();
const village = buildVillage(scene), colliders = village.colliders;

// NPCs from data: no encounter-specific code below this point
const markerTex = (glyph, bg) => {
  const c = document.createElement('canvas'); c.width = c.height = 128; const x = c.getContext('2d');
  const g = x.createRadialGradient(64, 64, 10, 64, 64, 64); g.addColorStop(0, 'rgba(255,220,120,.9)'); g.addColorStop(1, 'rgba(255,200,80,0)');
  x.fillStyle = g; x.fillRect(0, 0, 128, 128);
  x.fillStyle = bg; x.strokeStyle = '#4a3210'; x.lineWidth = 5; x.beginPath(); x.arc(64, 64, 34, 0, 7); x.fill(); x.stroke();
  x.fillStyle = '#3a2408'; x.font = 'bold 48px Nunito, sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(glyph, 64, 66);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
};
const MARK = { open: markerTex('!', '#ffcc4d'), done: markerTex('✓', '#f3ecd8') };
const npcs = data.encounters.map(enc => {
  const ch = enc.character, [x, z] = ch.position, rig = makeElder(ch.look);
  rig.root.position.set(x, groundAt(x, z), z); rig.root.rotation.y = ch.facing; scene.add(rig.root);
  const marker = new THREE.Sprite(new THREE.SpriteMaterial({ map: MARK.open, depthWrite: false, fog: false }));
  marker.scale.setScalar(0.75); marker.position.set(x, rig.root.position.y + rig.headY + 0.75, z); scene.add(marker);
  colliders.push({ x0: x - 0.35, x1: x + 0.35, z0: z - 0.35, z1: z + 0.35 });
  let camel = null;
  if (ch.camel) {
    const [cx, cz] = ch.camel; camel = makeCamel(); camel.position.set(cx, groundAt(cx, cz), cz); camel.rotation.y = ch.facing + 1.3; scene.add(camel);
    camel.traverse(o => { if (o.isMesh) o.castShadow = true; });
    colliders.push({ x0: cx - 1.1, x1: cx + 1.1, z0: cz - 1.1, z1: cz + 1.1 });
  }
  return { enc, rig, marker, camel, x, z, baseYaw: ch.facing, state: 'locked', greeted: 0 };
});
const refreshNpcs = () => npcs.forEach(n => {
  n.state = save.done.includes(n.enc.id) ? 'done' : n.enc.requires.every(r => save.done.includes(r)) ? 'open' : 'locked';
  n.marker.visible = n.state !== 'locked'; n.marker.material.map = MARK[n.state] ?? MARK.open; n.marker.material.opacity = n.state === 'done' ? 0.6 : 1;
});

await frame();
buildNature(scene, colliders, low ? 1 : 2);
const birds = new Birds(scene), motes = new Motes(scene, low ? 150 : 350);

const child = makeChild(); scene.add(child.root);
const player = new Player(child, camera, canvas, colliders, terrain.mesh);
const startPos = () => save.pos ?? [SPAWN.x, SPAWN.z, 0];
player.place(...startPos());

// ---- UI + story -----------------------------------------------------------
const ui = new UI({ mapCanvas: terrain.mapCanvas, data, save, persist, onSettings: applySettings });
function applySettings() {
  Voice.enabled = save.settings.voice; Sound.setVolume(save.settings.volume); Sound.setMusic(save.settings.music);
  ui.applyLang(); updateObjective();
}
const S = () => STR[save.settings.lang];
const t = o => o?.[save.settings.lang] ?? o?.ar ?? '';

let state = 'loading', timeScale = 1, timeTarget = 1, exposureTarget = EXPOSURE, worldTime = 0;
const story = new Story({ lang: () => save.settings.lang, hooks: { verses: step => recite(step), reward: enc => grant(enc) } });

function updateObjective() {
  const open = npcs.filter(n => n.state === 'open');
  if (!open.length) { ui.objective([S().explore, S().exploreSub]); return; }
  const near = open.reduce((a, b) => (Math.hypot(a.x - player.pos.x, a.z - player.pos.z) < Math.hypot(b.x - player.pos.x, b.z - player.pos.z) ? a : b));
  ui.objective(t(near.enc.objective));
}

async function recite(step, standalone = false) {
  const prev = state; state = 'quran';
  Voice.cancel(); Sound.mode('quran'); timeTarget = 0.15; exposureTarget = EXPOSURE * 0.72; ui.deep(true);
  if (!standalone && cine.npc) cine.wide();
  await playRecitation(step, { reciter: save.settings.reciter, lang: save.settings.lang, meaning: save.settings.meaning, S: S() });
  ui.deep(false); exposureTarget = EXPOSURE;
  if (!standalone && cine.npc) cine.close();
  state = prev; Sound.mode(standalone ? 'explore' : 'dialogue'); timeTarget = standalone ? 1 : 0.6;
}

async function grant(enc) {
  if (!save.done.includes(enc.id)) { save.done.push(enc.id); save.points += enc.reward.points; persist(); }
  await ui.reward(enc);
  ui.setPoints();
  const before = npcs.filter(n => n.state === 'open').map(n => n.enc.id);
  refreshNpcs();
  const fresh = npcs.filter(n => n.state === 'open' && !before.includes(n.enc.id));
  if (fresh.length) setTimeout(() => ui.toast(`${S().nextStory}: ${fresh.map(n => t(n.enc.title)).join(' · ')}`, 5000), 900);
}

// ---- cinematic framing ---------------------------------------------------------
const cine = {
  npc: null,
  frame(npc) {
    this.npc = npc;
    const p = player.pos, n = npc.rig.root.position;
    this.dir = new THREE.Vector3(n.x - p.x, 0, n.z - p.z).normalize();
    this.side = new THREE.Vector3(this.dir.z, 0, -this.dir.x);
    this.close();
  },
  close() {
    const p = player.pos, n = this.npc.rig.root.position;
    player.camGoal = { speed: 1.6,
      pos: p.clone().addScaledVector(this.dir, -1.9).addScaledVector(this.side, 0.95).add(new THREE.Vector3(0, 1.5, 0)),
      look: n.clone().addScaledVector(this.side, -0.25).add(new THREE.Vector3(0, this.npc.rig.headY - 0.15, 0)) };
  },
  wide() {
    const mid = player.pos.clone().lerp(this.npc.rig.root.position, 0.5);
    player.camGoal = { speed: 0.35,
      pos: mid.clone().addScaledVector(this.dir, -6).addScaledVector(this.side, 4).add(new THREE.Vector3(0, 3.2, 0)),
      look: mid.clone().addScaledVector(this.dir, 30).add(new THREE.Vector3(0, 7, 0)) };
  },
  end() { this.npc = null; player.camGoal = null; },
};

async function startEncounter(npc) {
  if (state !== 'explore') return;
  state = 'dialogue'; player.enabled = false; player.target = null; player.vel.set(0, 0, 0);
  ui.talk(false); ui.bubble(null); ui.showHud(false); ui.letterbox(true);
  Sound.mode('dialogue'); timeTarget = 0.6;
  // stand the child a comfortable distance away, facing the storyteller
  const n = npc.rig.root.position, away = new THREE.Vector3(player.pos.x - n.x, 0, player.pos.z - n.z);
  if (away.lengthSq() < 0.01) away.set(0, 0, -1);
  away.setLength(2.1);
  player.pos.set(n.x + away.x, groundAt(n.x + away.x, n.z + away.z), n.z + away.z);
  player.facing = Math.atan2(-away.x, -away.z);
  npc.rig.root.rotation.y = Math.atan2(away.x, away.z);
  cine.frame(npc);
  try { await story.run(npc.enc, npc.rig); }
  catch (e) { console.error(e); ui.toast(e.message); }
  cine.end(); ui.letterbox(false); ui.showHud(true);
  Sound.mode('explore'); timeTarget = 1;
  player.yaw = player.facing + Math.PI; player.enabled = true; state = 'explore';
  refreshNpcs(); updateObjective(); persist();
}

async function panel(kind) {
  if (state !== 'explore') return;
  state = 'panel'; player.enabled = false; player.target = null;
  let replay = null;
  if (kind === 'map') await ui.worldMap(player, npcs);
  if (kind === 'journal') await ui.journal(v => { replay = v; });
  if (kind === 'settings') await ui.settings(() => { const st = save.settings; save = fresh(); save.settings = st; ui.save = save; persist(); location.reload(); });
  state = 'explore'; player.enabled = true;
  if (replay) { player.enabled = false; await recite(replay, true); player.enabled = true; }
}

// ---- input --------------------------------------------------------------------
let nearNpc = null;
addEventListener('keydown', e => {
  if (state === 'explore' && e.code === 'KeyE' && nearNpc) startEncounter(nearNpc);
  else if (state === 'explore' && e.code === 'KeyM') panel('map');
  else if (state === 'explore' && e.code === 'KeyJ') panel('journal');
  else if (state === 'panel' && e.code === 'Escape') ui.closePanel?.();
});
document.getElementById('talk').onclick = () => nearNpc && startEncounter(nearNpc);
document.getElementById('dock').onclick = e => { const b = e.target.closest('button'); if (b) panel(b.dataset.open); };

// ---- title ------------------------------------------------------------------------
function begin(newGame) {
  if (newGame) { const st = save.settings; save = fresh(); save.settings = st; ui.save = save; persist(); player.place(SPAWN.x, SPAWN.z, 0); }
  Sound.start(save.settings); primeAudio(); window.speechSynthesis?.getVoices();
  applySettings(); refreshNpcs(); updateObjective();
  document.getElementById('title').classList.add('gone');
  setTimeout(() => { document.getElementById('title').hidden = true; }, 1200);
  player.camGoal = null; player.yaw = player.facing + Math.PI; player.enabled = true; state = 'explore';
  ui.showHud(true); ui.setPoints();
  if (!save.seenHint) { setTimeout(() => ui.toast(S().controls, 6500), 1500); save.seenHint = true; persist(); }
  setTimeout(() => {
    if (Voice.enabled && window.speechSynthesis && !Voice.pick(save.settings.lang)) ui.toast(S().noVoice, 5000);
  }, 9000);
}
document.getElementById('btn-continue').onclick = () => begin(false);
document.getElementById('btn-new').onclick = () => begin(true);
document.getElementById('btn-settings').onclick = () => ui.settings(() => { localStorage.removeItem(SAVE_KEY); location.reload(); });
document.getElementById('btn-continue').hidden = !(save.done.length || save.pos);
document.querySelector('#reward .medal').innerHTML = MEDAL;

// ---- loop -------------------------------------------------------------------------
const clock = new THREE.Clock(), v3 = new THREE.Vector3();
let lastArea = null, saveTimer = 0, miniTimer = 0;
function areaAt(x, z) { return data.areas.find(a => Math.hypot(a.x - x, a.z - z) < a.r); }

function tick() {
  const dt = Math.min(clock.getDelta(), 0.05), now = clock.elapsedTime;
  timeScale += (timeTarget - timeScale) * (1 - Math.exp(-dt * 2));
  worldTime += dt * timeScale;
  wind.uTime.value = worldTime; water.material.uniforms.uTime.value = worldTime;
  renderer.toneMappingExposure += (exposureTarget - renderer.toneMappingExposure) * (1 - Math.exp(-dt * 1.5));

  if (state === 'title') { // slow drifting establishing shot behind the child
    const s = Math.sin(now * 0.08);
    player.camGoal = { speed: 0.8, pos: new THREE.Vector3(player.pos.x + 2.2 + s * 1.5, player.pos.y + 1.7, player.pos.z - 4.8), look: new THREE.Vector3(player.pos.x - 6, player.pos.y + 7, player.pos.z + 60) };
  }
  player.update(dt, now);
  if (player.footfall(dt)) {
    const p = player.pos;
    Sound.step(onBridge(p.x, p.z) ? 'wood' : p.x > 95 || pathDist(p.x, p.z) < 2 || Math.hypot(p.x, p.z) < 30 ? 'sand' : 'grass');
  }

  nearNpc = null; let bubble = null;
  for (const n of npcs) {
    const r = n.rig.root, d = Math.hypot(r.position.x - player.pos.x, r.position.z - player.pos.z);
    n.rig.animate(dt * timeScale, worldTime, 0);
    n.marker.position.y = r.position.y + n.rig.headY + 0.7 + Math.sin(now * 2 + n.x) * 0.08;
    n.camel?.userData.animate(worldTime);
    if (state !== 'explore') continue;
    const want = d < 10 ? Math.atan2(player.pos.x - r.position.x, player.pos.z - r.position.z) : n.baseYaw;
    let dy = want - r.rotation.y; dy = Math.atan2(Math.sin(dy), Math.cos(dy)); r.rotation.y += dy * (1 - Math.exp(-dt * 3));
    if (d < 9) {
      if (n.greeted === 0 && n.state === 'open') { n.greeted = now; }
      if (n.greeted && now - n.greeted < 1.4) n.rig.wave(now);
      bubble = { n, text: t(n.state === 'open' ? n.enc.greeting : n.state === 'done' ? n.enc.after : n.enc.locked) };
      if (d < 3.4 && n.state === 'open') nearNpc = n;
    } else if (d > 16) n.greeted = 0;
  }
  if (state === 'explore') {
    ui.talk(!!nearNpc);
    if (bubble) {
      const r = bubble.n.rig.root; v3.set(r.position.x, r.position.y + bubble.n.rig.headY + 0.35, r.position.z).project(camera);
      ui.bubble(bubble.text, v3.z < 1 ? { x: (v3.x + 1) / 2 * innerWidth, y: (1 - v3.y) / 2 * innerHeight } : null);
    } else ui.bubble(null);
    const area = areaAt(player.pos.x, player.pos.z);
    if (area && area !== lastArea) {
      const first = !save.discovered.includes(area.id);
      if (first) { save.discovered.push(area.id); persist(); }
      ui.banner(first ? S().discovered : '', t(area));
    }
    lastArea = area ?? lastArea;
    if ((miniTimer += dt) > 0.05) { miniTimer = 0; ui.minimap(player, npcs); }
    if ((saveTimer += dt) > 4) { saveTimer = 0; save.pos = [+player.pos.x.toFixed(1), +player.pos.z.toFixed(1), +player.facing.toFixed(2)]; persist(); updateObjective(); }
    Sound.setWater(waterDist(player.pos.x, player.pos.z));
  }

  sun.position.copy(player.pos).addScaledVector(sunDir, 150); sun.target.position.copy(player.pos);
  birds.update(dt * timeScale); motes.update(dt * timeScale, player.pos);
  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}

addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });

ui.applyLang(); refreshNpcs();
state = 'title';
document.getElementById('loading').classList.add('gone');
setTimeout(() => { document.getElementById('loading').hidden = true; }, 900);
tick();
// handy for debugging / automated checks
window.__game = { player, npcs, startEncounter, get state() { return state; }, save: () => save };
