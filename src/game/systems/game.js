// Game flow: title → explore → dialogue → Quran → reward → explore. Framework-free; the
// React layer builds the world, then calls createGame() and tick() every frame.
import * as THREE from 'three';
import { SPAWN, LOOKOUT, groundAt, waterDist, onBridge, pathDist } from '../terrain/heightfield.js';
import { markers } from '../npc/NPC.jsx';
import { Sound, Voice } from './audio.js';
import { primeAudio, playRecitation } from './recitation.js';
import { DEFAULT_RECITER } from './quran.js';
import { UI, STR, MEDAL, arDigits } from '../ui/ui.js';
import { useGame } from './store.js';
import { refs } from './refs.js';
import { wind } from '../shaders/wind.js';
import { ZOOM_DEFAULT, ZOOM_MIN, ZOOM_MAX } from '../camera/CameraRig.js';
import { createGuide } from './guide.js';
import { createCoins } from '../world/coins.js';
import { createAutowalk } from './autowalk.js';
import { PRESETS } from './quality.js';
import { initPWA } from '../../pwa/pwa.js';
import { createProgress, gateMarker, needFor, DIFFICULTY } from './progress.js';

const SAVE_KEY = 'quran-journey-v1';
const fresh = () => ({ done: [], points: 0, discovered: [], pos: null, seenHint: false, seenStickHint: false, coins: [], chosen: null, unlocked: [],
  difficulty: 'easy', opened: [], category: null,
  settings: { lang: 'ar', reciter: DEFAULT_RECITER, voice: true, meaning: true, auto: true, volume: 0.7, music: false, quality: 'auto', zoom: ZOOM_DEFAULT, path: true } });
function loadSave() {
  const f = fresh();
  try { const s = JSON.parse(localStorage.getItem(SAVE_KEY)); if (s) return { ...f, ...s, settings: { ...f.settings, ...s.settings } }; } catch { /* private mode */ }
  return f;
}
const $ = id => document.getElementById(id);

export function createGame({ camera, mapCanvas, data, scene, colliders }) {
  let save = loadSave();
  const persist = () => { try { localStorage.setItem(SAVE_KEY, JSON.stringify(save)); } catch { /* not fatal */ } };
  useGame.getState().setQualitySetting(save.settings.quality);   // no-op unless it differs
  const setMode = m => { mode = m; useGame.getState().setMode(m); };
  let mode = 'title';

  // player, camera rig, NPCs and the dialogue runner are mounted by <Player/>, <NPC/> and
  // <DialogueSystem/>; this system drives the flow between them
  const player = refs.player, rig = refs.cameraRig, npcs = refs.npcs;
  const MARK = markers();
  const prog = createProgress({ data });
  const npcById = id => npcs.find(n => n.enc.id === id);
  // Story states: done · locked (the story before it in its category isn't done) · gated (its
  // turn has come, but the child hasn't collected the difficulty's share of its coin set yet) ·
  // open. A pick (save.chosen) skips the chain but never the coins; a done pick reopens for a
  // replay. Reaching the coin share opens a story for good (save.opened), so changing the
  // difficulty only applies to stories that are still closed.
  const avail = n => n.state === 'open' || n.state === 'gated';
  function refreshNpcs(celebrate = false) {
    save.opened ??= [];
    for (const n of npcs) {
      const id = n.enc.id, done = save.done.includes(id);
      let st;
      if (done) st = id === save.chosen ? 'open' : 'done';
      else if (id !== save.chosen && !save.opened.includes(id) && !prog.prereq(id).every(r => save.done.includes(r))) st = 'locked';
      else {
        const g = coins.progress(id);
        n.gate = g ? { have: g.have, total: g.total, need: needFor(g.total, save.difficulty) } : null;
        if (!save.opened.includes(id) && g && g.have >= n.gate.need) {
          save.opened.push(id); persist();
          if (celebrate) opened(n);
        }
        st = save.opened.includes(id) ? 'open' : 'gated';
      }
      n.state = st;
      n.marker.visible = st !== 'locked';
      if (st === 'gated') {
        (n.gateMark ??= gateMarker()).draw(n.gate, save.settings.lang);
        n.marker.material.map = n.gateMark.tex; n.markerScale = 1.9; n.marker.material.opacity = 1; n.marker.renderOrder = 5;   // over the beacon
      } else {
        n.marker.material.map = MARK[st] ?? MARK.open; n.markerScale = 1; n.marker.material.opacity = st === 'done' ? 0.55 : 1;
      }
    }
  }
  // the coin share of a story was just reached: fanfare, toast, the marker turns into "!"
  function opened(n) {
    Sound.unlock?.();
    n.greeted = 0;
    setTimeout(() => ui.toast(S().gateOpen, 3500), 250);
    ui.floatText(innerWidth / 2, innerHeight * 0.3, S().gateOpen, true);
  }
  player.place(LOOKOUT.x, LOOKOUT.z, LOOKOUT.facing);   // title screen: on the hill, looking over the village

  // ---- UI + story ---------------------------------------------------------------------
  const ui = new UI({ mapCanvas, data, save, persist, onSettings: applySettings });
  ui.prog = prog;
  function applySettings() {
    if (refs.dialogue) refs.dialogue.autoAdvance = save.settings.auto !== false;
    Voice.enabled = save.settings.voice; Sound.setVolume(save.settings.volume); Sound.setMusic(save.settings.music);
    useGame.getState().setQualitySetting(save.settings.quality);
    ui.applyLang(); refreshNpcs(); updateObjective();
    if (mode !== 'title') prepareVoice();
  }
  const S = () => STR[save.settings.lang];
  // guided path + collectibles
  const guide = createGuide({ scene, colliders });
  // every story's own coin set: along the route from the story before it in its category (or the
  // spawn) to its storyteller
  const endpoints = id => {
    const n = npcById(id); if (!n) return null;
    const p = prog.prereq(id).map(npcById).find(Boolean);
    return { from: p ? [p.x, p.z] : [SPAWN.x, SPAWN.z], to: [n.x, n.z], r: (n.enc.stage?.talkRadius ?? 3.4) * 0.8 };
  };
  const coins = createCoins({ scene, camera, grid: guide.grid, ui, npcs, getSave: () => save, persist, S, lite: useGame.getState().detail === 'lite', endpoints,
    onCollect: () => { refreshNpcs(true); updateObjective(); },
    onBuilt: () => { refreshNpcs(false); if (mode !== 'title') updateObjective(); } });
  coins.load();
  coins.want(prog.categories.flatMap(c => c.ids));
  // "walk to the story" button / F: autopilot along the guided route; manual input cancels it
  const auto = createAutowalk({ player, guide, onChange: (on, why) => {
    ui.walkButton(true, on);
    if (why === 'stuck' || why === 'lost') ui.toast(S().walkStuck, 3500);
  } });
  player.onManual = () => auto.stop('manual');
  const toggleWalk = () => { if (mode === 'explore') auto.toggle(); };
  const t = o => o?.[save.settings.lang] ?? o?.ar ?? '';
  let timeScale = 1, timeTarget = 1;

  // Narrator: tells the child where to go (voiced lines in public/audio, text from encounters.json)
  let narrating = 0;
  async function narrate(parts) {
    if (!Voice.enabled) return;
    const my = ++narrating;
    for (const p of parts.filter(Boolean)) {
      if (my !== narrating || mode !== 'explore') return;
      await Voice.speak(t(p), save.settings.lang);
      await new Promise(r => setTimeout(r, 350));
    }
  }
  // The story the objective (and the guided path) points at: the one the narrator just announced,
  // else the nearest open one — kept unless another is clearly (15 m) closer, so it doesn't flicker.
  // The story the objective (and the guided path) points at: the child's pick, else the next
  // story of the category they are in (the last one picked / finished; the first category by
  // default) — an open one first, else the first in order still waiting for its coins. A
  // finished category hands over to the next one that has something to do.
  let target = null;
  const curCategory = () => (prog.category(save.category) ? save.category : prog.categories[0]?.id);
  function nextStory() {
    const chosen = save.chosen && npcById(save.chosen);
    if (chosen && avail(chosen)) return chosen;
    const cur = curCategory(), order = [cur, ...prog.categories.map(c => c.id).filter(c => c !== cur)];
    for (const cid of order) {
      const list = prog.category(cid).ids.map(npcById).filter(n => n && avail(n));
      if (list.length) return list.find(n => n.state === 'open') ?? list[0];
    }
    return null;
  }
  const lines = o => { const v = t(o); return Array.isArray(v) ? v : [v]; };
  const num = n => (save.settings.lang === 'ar' ? arDigits(n) : String(n));
  function updateObjective() {
    target = nextStory();
    if (!target) { ui.objective([S().explore, S().exploreSub]); return; }
    coins.want([target.enc.id], true);
    if (target.state === 'gated') {
      const g = target.gate;
      ui.objective(g ? [`${S().gateObj}: ${num(g.have)} / ${num(g.need)} 🪙`, t(target.enc.title) || lines(target.enc.objective)[0]] : [S().gatePrep, t(target.enc.title)]);
    } else ui.objective(lines(target.enc.objective));
  }
  // what a storyteller says while their story still waits for coins (text only, no new audio)
  const gateLine = n => (n.gate ? S().gateLine(Math.max(0, n.gate.need - n.gate.have)) : S().gatePrep);

  // ---- cinematic shots --------------------------------------------------------------------
  // One NPC or a group: the camera sits by the child's shoulder and frames whoever is
  // speaking; when the child speaks it swings round to show the child's face.
  const up = y => new THREE.Vector3(0, y, 0);
  const cine = {
    npc: null, current: null,
    center() { const c = new THREE.Vector3(); this.npc.members.forEach(m => c.add(m.pos)); return c.divideScalar(this.npc.members.length); },
    frame(npc) {
      this.npc = npc;
      const c = this.center();
      this.dir = new THREE.Vector3(c.x - player.pos.x, 0, c.z - player.pos.z).normalize();
      this.side = new THREE.Vector3(this.dir.z, 0, -this.dir.x);
      this.speaker(npc.enc.host);
      if (camera.position.distanceTo(rig.shot.pos) > 12) rig.snap();   // far away (e.g. teleported): cut, don't fly
    },
    member(id) { return this.npc.members.find(m => m.id === id) ?? this.npc.host; },
    head(m) { return new THREE.Vector3(m.pos.x, m.headY - 0.12, m.pos.z); },
    // look point that puts `target` at screen height ndcY — heads sit in the upper third,
    // clear of the dialogue box along the bottom of the screen
    aim(pos, target, ndcY = 0.32) {
      return target.clone().sub(up(pos.distanceTo(target) * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) * ndcY));
    },
    // how clear a shot is: the closest any other body (or the camera itself) comes to the
    // camera→subject line, so nobody stands in front of the one who is talking
    clearance(pos, target, bodies) {
      const seg = new THREE.Line3(pos, target), q = new THREE.Vector3();
      let m = 9;
      for (const b of bodies) { seg.closestPointToPoint(b, true, q); m = Math.min(m, Math.hypot(q.x - b.x, q.z - b.z), pos.distanceTo(b)); }
      return m - (player.blocked(pos.x, pos.z) ? 5 : 0);
    },
    best(cands, target, bodies) {
      return cands.reduce((a, c) => (this.clearance(c, target, bodies) > this.clearance(a, target, bodies) + 0.05 ? c : a));
    },
    speaker(id) {
      if (!this.npc) return;
      this.current = id;
      const p = player.pos, chest = v => new THREE.Vector3(v.x, v.y + 0.9, v.z);
      if (id === 'player') {        // reverse shot: in front of the child, to whichever side is clear of the cast
        const face = p.clone().add(up(1.02)), bodies = this.npc.members.map(m => chest(m.pos));
        const pos = this.best([1, -1].map(k => p.clone().addScaledVector(this.dir, 1.25).addScaledVector(this.side, 1.45 * k).add(up(1.3))), face, bodies);
        rig.shot = { stiffness: 1.6, pos, look: this.aim(pos, face) };
        useGame.setState({ focus: face });
        return;
      }
      // over the child's shoulder toward the speaker, on the side where no one else blocks the view
      const m = this.member(id), h = this.head(m), bodies = this.npc.members.filter(o => o !== m).map(o => chest(o.pos));
      const d = new THREE.Vector3(m.pos.x - p.x, 0, m.pos.z - p.z).normalize(), sd = new THREE.Vector3(d.z, 0, -d.x);
      const pos = this.best([1, -1].map(k => p.clone().addScaledVector(d, -1.7).addScaledVector(sd, 0.95 * k).add(up(1.42))), h, bodies);
      rig.shot = { stiffness: 1.8, pos, look: this.aim(pos, h) };
      useGame.setState({ focus: h });
    },
    close() { this.speaker(this.current ?? this.npc.enc.host); },
    wide() {
      const mid = player.pos.clone().lerp(this.center(), 0.5);
      rig.shot = { stiffness: 0.5, pos: mid.clone().addScaledVector(this.dir, -6.5).addScaledVector(this.side, 4.2).add(up(2.6)), look: mid.clone().addScaledVector(this.dir, 30).add(up(6)) };
      useGame.setState({ focus: mid.clone().add(up(1)) });
    },
    end() { this.npc = null; this.current = null; rig.shot = null; useGame.setState({ focus: null }); },
  };

  async function recite(step, standalone = false) {
    const prev = mode; setMode('quran');
    Voice.cancel(); Sound.mode('quran'); timeTarget = 0.15; ui.deep(true);
    if (!standalone && cine.npc) cine.wide();
    await playRecitation(step, { reciter: save.settings.reciter, lang: save.settings.lang, meaning: save.settings.meaning, S: S() });
    ui.deep(false);
    if (!standalone && cine.npc) cine.close();
    setMode(prev); Sound.mode(standalone ? 'explore' : 'dialogue'); timeTarget = standalone ? 1 : 0.6;
  }

  async function grant(enc) {
    if (!save.done.includes(enc.id)) { save.done.push(enc.id); save.points += enc.reward.points; }
    if (save.chosen === enc.id) save.chosen = null;                // finished the pick: back to the default order
    save.category = prog.catOf(enc.id) ?? save.category;          // carry on in this story's category
    persist();
    await ui.reward(enc);
    ui.setPoints();
    const before = npcs.filter(avail).map(n => n.enc.id);
    refreshNpcs();
    target = null; updateObjective();                              // the path re-targets to the next story
    const next = npcs.filter(n => avail(n) && !before.includes(n.enc.id)).sort((a, b) => (a === target ? -1 : b === target ? 1 : 0));
    if (next.length) setTimeout(() => ui.toast(`${S().nextStory}: ${next.map(n => t(n.enc.title)).join(' · ')}`, 5000), 900);
    if (next.length) setTimeout(() => narrate([data.narrator?.next, next[0].enc.narration]), 1600);
  }

  async function startEncounter(npc) {
    if (mode !== 'explore') return;
    if (npc.state === 'gated') { ui.toast(gateLine(npc), 4000); npc.rig.wave?.(now); return; }   // friendly nudge, story stays closed
    if (npc.state !== 'open') return;
    setMode('dialogue'); player.enabled = false; player.target = null; player.vel.set(0, 0, 0);
    ui.talk(false); ui.bubble(null); ui.showHud(false); ui.letterbox(true); $('toast').classList.remove('show');
    Sound.mode('dialogue'); timeTarget = 0.6;
    // stand the child in front of the group (the way the seated/standing cast faces),
    // or — for a single standing NPC — 2 m from them on the side the child came from
    const n = npc.rig.root.position, C = new THREE.Vector3();
    npc.members.forEach(m => C.add(m.pos)); C.divideScalar(npc.members.length);
    const front = new THREE.Vector3();
    npc.members.forEach(m => front.add(new THREE.Vector3(Math.sin(m.def.facing), 0, Math.cos(m.def.facing))));
    let spot = null;
    if (npc.members.length > 1 || npc.host.sitting) {
      front.normalize().multiplyScalar(npc.enc.stage?.distance ?? 2.3);
      const sx = C.x + front.x, sz = C.z + front.z;
      if (!player.blocked(sx, sz)) spot = [sx, sz];
    }
    if (!spot) {
      const away = new THREE.Vector3(player.pos.x - n.x, 0, player.pos.z - n.z);
      if (away.lengthSq() < 0.01) away.set(0, 0, -1);
      away.setLength(2.0);
      if (!player.blocked(n.x + away.x, n.z + away.z)) spot = [n.x + away.x, n.z + away.z];
    }
    if (spot) player.pos.set(spot[0], groundAt(spot[0], spot[1]), spot[1]);
    player.facing = Math.atan2(C.x - player.pos.x, C.z - player.pos.z);
    for (const m of npc.members) if (m.turns) m.rig.root.rotation.y = Math.atan2(player.pos.x - m.pos.x, player.pos.z - m.pos.z);
    const group = { setTalking(id) { for (const m of npc.members) m.rig.talking = m.id === id; player.rig.talking = id === 'player'; } };
    npc.marker.visible = false;                                   // refreshNpcs() restores it afterwards
    cine.frame(npc);
    try { await refs.dialogue.run(npc.enc, group); }
    catch (e) { console.error(e); ui.toast(e.message); }
    group.setTalking(null);
    cine.end(); ui.letterbox(false); ui.showHud(true);
    Sound.mode('explore'); timeTarget = 1;
    player.yaw = player.facing + Math.PI; player.enabled = true; setMode('explore');
    refreshNpcs(); updateObjective(); persist();
  }

  async function panel(kind) {
    if (mode !== 'explore') return;
    setMode('panel'); player.enabled = false; player.target = null;
    let replay = null, pick = null;
    if (kind === 'map') await ui.worldMap(player, npcs, guide.mapRoute, guide.progress, id => { pick = id; });
    let cat = null;
    if (kind === 'stories') await ui.stories(player, npcs, target?.enc.id ?? null, id => { pick = id; }, { prog, category: target ? prog.catOf(target.enc.id) : curCategory(), onCategory: c => { cat = c; } });
    if (kind === 'journal') await ui.journal(v => { replay = v; });
    if (kind === 'settings') await ui.settings(resetProgress);
    setMode('explore'); player.enabled = true;
    if (pick) chooseStory(pick);
    else if (cat && cat !== (target ? prog.catOf(target.enc.id) : curCategory())) switchCategory(cat);
    if (replay) { player.enabled = false; await recite(replay, true); player.enabled = true; }
  }
  // Neural Arabic voice for browsers without one (e.g. Chrome on Linux): download in the
  // background, report progress, never block play.
  let lastPct = -10;
  Voice.onStatus = (st, pct, err) => {
    if (st === 'download' && pct - lastPct >= 10) { lastPct = pct; if (mode === 'explore') ui.toast(`${S().voiceDl} · ${pct}%`, 2500); }
    else if (st === 'ready' && lastPct >= 0) ui.toast(S().voiceReady, 3000);
    else if (st === 'failed') ui.toast(`${S().voiceFail}${err ? ' (' + err + ')' : ''}`, 6000);
  };
  const prepareVoice = () => { if (save.settings.voice) Voice.prepare(save.settings.lang); };
  // Story picker / world-map pin: make any story the target (unlocking a locked one, reopening a
  // done one for a replay). The trail, beacon, minimap, objective and 👣 all follow `target`.
  // Story picker / world-map pin: make any story the target. A done one reopens for a replay; one
  // that isn't open yet becomes the target with its coins laid out, but still opens only with its
  // coin share. The trail, beacon, minimap, objective and 👣 all follow `target`.
  function chooseStory(id) {
    const npc = npcById(id);
    if (!npc || mode !== 'explore') return;
    save.chosen = id; save.category = prog.catOf(id) ?? save.category; persist();
    coins.want([id], true);
    refreshNpcs(); target = null; updateObjective();
    ui.toast(`${S().headingTo}: ${t(npc.enc.title)}`, 3000);
    narrate([npc.enc.narration]);
  }
  // a category tab left open in the story sheet: carry on with that category's next story
  function switchCategory(cid) {
    if (!prog.category(cid) || mode !== 'explore') return;
    save.category = cid;
    if (save.chosen && prog.catOf(save.chosen) !== cid) save.chosen = null;
    persist(); refreshNpcs(); target = null; updateObjective();
    if (target && prog.catOf(target.enc.id) === cid) { ui.toast(`${S().headingTo}: ${t(target.enc.title)}`, 3000); narrate([target.enc.narration]); }
  }
  function setDifficulty(d) { if (DIFFICULTY[d]) { save.difficulty = d; persist(); refreshNpcs(); updateObjective(); } }
  function resetProgress() { const st = save.settings, d = save.difficulty; save = fresh(); save.settings = st; save.difficulty = d; ui.save = save; persist(); location.reload(); }

  // ---- input ---------------------------------------------------------------------------------
  let nearNpc = null;
  addEventListener('keydown', e => {
    if (mode === 'explore' && e.code === 'KeyE' && nearNpc) startEncounter(nearNpc);
    else if (mode === 'explore' && e.code === 'KeyM') panel('map');
    else if (mode === 'explore' && e.code === 'KeyJ') panel('journal');
    else if (mode === 'explore' && e.code === 'KeyK') panel('stories');
    else if (mode === 'explore' && e.code === 'KeyF' && !e.repeat) toggleWalk();
    else if (mode === 'panel' && e.code === 'Escape') ui.closePanel?.();
  });
  $('talk').onclick = () => nearNpc && startEncounter(nearNpc);
  // HUD zoom buttons: a tap steps, holding keeps zooming (smoothly, via the controller)
  $('walk').onclick = toggleWalk;
  $('walk').addEventListener('contextmenu', e => e.preventDefault());
  for (const b of document.querySelectorAll('#zoom button[data-zoom]')) {
    const dir = b.dataset.zoom === 'out' ? 1 : -1;
    const stop = () => { player.zoomHold = 0; };
    b.addEventListener('pointerdown', e => { e.preventDefault(); if (!player.enabled) return; player.zoomBy(dir > 0 ? 1.35 : 1 / 1.35); player.zoomHold = dir; });
    for (const ev of ['pointerup', 'pointerleave', 'pointercancel']) b.addEventListener(ev, stop);
    b.addEventListener('contextmenu', e => e.preventDefault());
  }
  const rememberZoom = () => { save.settings.zoom = +player.dist.toFixed(2); };
  addEventListener('pagehide', () => { if (mode !== 'title') { rememberZoom(); persist(); } });
  $('dock').onclick = e => { const b = e.target.closest('button'); if (b) panel(b.dataset.open); };

  // ---- title ------------------------------------------------------------------------------------
  function begin(newGame, difficulty) {
    if (newGame) { const st = save.settings; save = fresh(); save.settings = st; save.difficulty = DIFFICULTY[difficulty] ? difficulty : 'easy'; ui.save = save; persist(); target = null; }
    coins.load();
    player.place(...(save.pos ?? [SPAWN.x, SPAWN.z, 0]));
    player.dist = THREE.MathUtils.clamp(+save.settings.zoom || ZOOM_DEFAULT, ZOOM_MIN, ZOOM_MAX);
    Sound.start(save.settings); primeAudio(); window.speechSynthesis?.getVoices();
    applySettings(); refreshNpcs(); updateObjective();
    $('title').classList.add('gone'); setTimeout(() => { $('title').hidden = true; }, 1200);
    rig.shot = null; player.yaw = player.facing + Math.PI; rig.snap(); player.enabled = true; setMode('explore');
    ui.showHud(true); ui.setPoints();
    if (player.touch && !save.seenStickHint) { setTimeout(() => ui.toast(S().controlsTouch, 7000), 1500); save.seenStickHint = save.seenHint = true; persist(); }
    else if (!save.seenHint) { setTimeout(() => ui.toast(S().controls, 6500), 1500); save.seenHint = true; persist(); }
    prepareVoice();
    setTimeout(() => narrate([data.narrator?.intro, nextStory()?.enc.narration]), 1400);
  }
  $('btn-continue').onclick = () => begin(false);
  // New Journey: pick the difficulty first (Easy 20 % · Medium 50 % · Hard 90 % of each story's coins)
  $('btn-new').onclick = () => ui.difficultyPicker(d => begin(true, d));
  $('btn-settings').onclick = () => ui.settings(() => { try { localStorage.removeItem(SAVE_KEY); } catch { /* ignore */ } location.reload(); });
  $('btn-continue').hidden = !(save.done.length || save.pos);
  document.querySelector('#reward .medal').innerHTML = MEDAL;
  ui.applyLang(); refreshNpcs();
  const titleShot = () => {
    const p = player.pos, f = new THREE.Vector3(Math.sin(player.facing), 0, Math.cos(player.facing)), s = new THREE.Vector3(f.z, 0, -f.x);
    return { stiffness: 0.6, pos: p.clone().addScaledVector(f, -4.2).addScaledVector(s, -1.6).add(new THREE.Vector3(0, 1.55, 0)), look: p.clone().addScaledVector(f, 40).add(new THREE.Vector3(0, 5, 0)) };
  };
  rig.shot = titleShot(); rig.snap();
  setMode('title');
  initPWA({ S, toast: (text, ms) => ui.toast(text, ms) });   // offline cache, update toast, install button

  // ---- per frame --------------------------------------------------------------------------------
  const v3 = new THREE.Vector3();
  let lastArea = null, saveTimer = 0, miniTimer = 0, now = 0, goal = null;
  const areaAt = (x, z) => data.areas.find(a => Math.hypot(a.x - x, a.z - z) < a.r);

  function tick(dt) {
    dt = Math.min(dt, 0.05); now += dt;
    timeScale += (timeTarget - timeScale) * (1 - Math.exp(-dt * 2));
    refs.clock.scale = timeScale; refs.clock.wind += dt * timeScale; refs.clock.water += dt * Math.max(timeScale, 0.35);
    wind.uTime.value = refs.clock.wind;
    wind.uSunDirV.value.copy(refs.sunDir).transformDirection(camera.matrixWorldInverse);

    if (player.footfall(dt)) {
      const p = player.pos;
      Sound.step(onBridge(p.x, p.z) ? 'wood' : p.x > 95 || pathDist(p.x, p.z) < 2 || Math.hypot(p.x, p.z) < 30 ? 'sand' : 'grass');
    }

    nearNpc = null; let bubble = null;
    for (const n of npcs) {
      const r = n.rig.root, d = Math.hypot(r.position.x - player.pos.x, r.position.z - player.pos.z);
      if (mode !== 'explore') continue;
      for (const m of n.members) {                          // standing cast members turn to the child
        if (!m.turns) continue;
        const mr = m.rig.root, md = Math.hypot(mr.position.x - player.pos.x, mr.position.z - player.pos.z);
        const want = md < 10 ? Math.atan2(player.pos.x - mr.position.x, player.pos.z - mr.position.z) : m.def.facing;
        let dy = want - mr.rotation.y; dy = Math.atan2(Math.sin(dy), Math.cos(dy)); mr.rotation.y += dy * (1 - Math.exp(-dt * 2.5));
      }
      if (d < 9) {
        if (n.greeted === 0 && n.state === 'open') n.greeted = now;
        if (n.greeted && now - n.greeted < 1.4) n.rig.wave(now);
        bubble = { n, text: n.state === 'gated' ? gateLine(n) : t(n.state === 'open' ? n.enc.greeting : n.state === 'done' ? n.enc.after : n.enc.locked) };
        if (d < (n.enc.stage?.talkRadius ?? 3.4) && n.state === 'open') nearNpc = n;   // a story still waiting for coins shows no talk button
      } else if (d > 16) n.greeted = 0;
    }
    if (mode === 'title') rig.shot = titleShot();
    const preset = PRESETS[useGame.getState().quality], explore = mode === 'explore';
    if (explore && target && !avail(target)) updateObjective();
    // the golden trail always leads to the target storyteller's house, open or still waiting for
    // coins — it never turns off to chase coins; the child gathers them on their own
    goal = null;
    guide.update(dt, now, { explore, show: save.settings.path !== false, target, player, outlines: preset.outlines, goal });
    auto.update(dt, { explore });
    ui.walkButton(explore && !!guide.route && !!guide.target, auto.active);
    coins.update(dt, now, { explore, player, show: target && !save.done.includes(target.enc.id) ? target.enc.id : null, preset });
    if (mode === 'explore') {
      ui.talk(!!nearNpc);
      if (bubble) {
        // over a storyteller still waiting for coins the bubble sits above the lock-and-count marker
        const r = bubble.n.rig.root, lift = bubble.n.state === 'gated' ? 0.6 * Math.max(1, refs.view.dist / 9) * (bubble.n.markerScale ?? 1) * 1.6 + 0.1 : 0.3;
        v3.set(r.position.x, bubble.n.host.headY + lift, r.position.z).project(camera);
        ui.bubble(bubble.text, v3.z < 1 ? { x: (v3.x + 1) / 2 * innerWidth, y: (1 - v3.y) / 2 * innerHeight } : null);
      } else ui.bubble(null);
      const area = areaAt(player.pos.x, player.pos.z);
      if (area && area !== lastArea) {
        const first = !save.discovered.includes(area.id);
        if (first) { save.discovered.push(area.id); persist(); }
        ui.banner(first ? S().discovered : '', t(area));
      }
      lastArea = area ?? lastArea;
      if ((miniTimer += dt) > 0.05) { miniTimer = 0; ui.minimap(player, npcs, guide.mapRoute, guide.progress); }
      if ((saveTimer += dt) > 4) { saveTimer = 0; save.pos = [+player.pos.x.toFixed(1), +player.pos.z.toFixed(1), +player.facing.toFixed(2)]; rememberZoom(); persist(); updateObjective(); }
      Sound.setWater(waterDist(player.pos.x, player.pos.z));
    }
  }

  refs.game = { recite, grant, speaker: id => cine.speaker(id), lang: () => save.settings.lang };
  window.__game = { THREE, player, npcs, camera, cameraRig: rig, startEncounter, chooseStory, panel, guide, coins, autowalk: auto, recite: step => recite(step, true), get target() { return target; }, get state() { return mode; }, save: () => save,
    progress: prog, setDifficulty, switchCategory, begin, get goal() { return goal; }, balance: o => coins.balance(o), refreshNpcs };
  return { tick };
}
