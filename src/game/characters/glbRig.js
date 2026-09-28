// GLB characters. If public/models/<name>.glb exists it replaces the procedural rig:
// the model is scaled to the character's height, and idle / walk / run / talk (and, for a
// seated character, sit / sit_talk) clips are blended by movement speed and speech (found by name, so Mixamo-style exports work as-is).
// Draco- and Meshopt-compressed files are supported.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { toonMaterial, outlineMaterial } from '../shaders/toon.js';
import { useGame } from '../systems/store.js';
import { PRESETS } from '../systems/quality.js';

import { gltfLoader } from '../world/loaders.js';

// Resolves to a rig, or null when the file is absent (so the caller falls back quietly).
export async function loadGlbRig(url, targetHeight) {
  try {
    const head = await fetch(url, { method: 'HEAD' });
    if (!head.ok || !/model|octet|gltf/.test(head.headers.get('content-type') || 'model/gltf-binary')) return null;
  } catch { return null; }
  const gltf = await gltfLoader().loadAsync(url);   // a present-but-broken file should fail loudly
  return new GlbRig(gltf, targetHeight);
}

// clip names the character files use: player idle/walk/run/talk · farmer idle/walk/talk ·
// grandma sit/sit_talk (+ idle). Mixamo-style names still match the looser patterns.
const CLIPS = {
  sit_talk: [/^sit_?talk$/i, /sit.*talk|talk.*sit/i],
  sit: [/^sit(ting)?$/i, /sit/i],
  idle: [/^idle$/i, /idle|breath|stand/i],
  walk: [/^walk$/i, /walk/i],
  run: [/^run$/i, /run|jog/i],
  talk: [/^talk$/i, /talk|explain|conversation/i],
};

class GlbRig {
  constructor(gltf, targetHeight) {
    const model = gltf.scene;
    // toon_* materials → the shared cel material (keeping face/eye textures); `outline` → ink hull.
    // Character hulls are exported with flipped normals, so their front faces are the far side.
    const outlines = PRESETS[useGame.getState().detail]?.outlines !== false;
    const hulls = [];
    model.traverse(o => {
      if (!o.isMesh) return;
      o.frustumCulled = false;                             // skinned: bounds move with the pose
      const m = o.material; if (!m) return;
      const name = m.name.replace(/\.\d+$/, '');
      if (name === 'outline') {
        o.material = outlineMaterial('char'); o.castShadow = false; o.receiveShadow = false; o.visible = outlines;
        o.userData.outline = true; hulls.push(o); return;
      }
      o.castShadow = true; o.receiveShadow = true;
      const cut = m.transparent || m.alphaTest > 0 || /lash|brow/.test(name);
      o.material = toonMaterial(`char_${name}_${m.map ? m.map.uuid : m.color.getHexString()}`, {
        color: m.color.getHex(), map: m.map ?? null, side: m.side, rim: /skin|face/.test(name) ? 0.3 : 0.22,
        alphaTest: cut ? 0.35 : 0,
      });
      if (cut) o.castShadow = false;
    });
    this.hulls = hulls;
    if (PRESETS[useGame.getState().detail]?.lite) mergeSkinned(model);
    const box = new THREE.Box3().setFromObject(model), h = box.max.y - box.min.y || 1;
    model.scale.setScalar(targetHeight / h);
    model.position.y = -box.min.y * (targetHeight / h);
    this.root = new THREE.Group(); this.root.add(model);
    this.headY = targetHeight; this.talking = false; this.phase = 0;
    this.mixer = new THREE.AnimationMixer(model);
    const clips = gltf.animations, used = new Set();
    this.actions = {};
    // exact name first ("sit", "talk"…), then a looser match; each clip is used once, so
    // "sit_talk" never doubles as "talk" or "sit". Any subset of clips works.
    for (const [k, res] of Object.entries(CLIPS)) {
      const clip = res.map(re => clips.find(c => !used.has(c) && re.test(c.name.replace(/^.*\|/, '')))).find(Boolean);
      if (clip) { used.add(clip); const a = this.mixer.clipAction(clip); a.play(); a.setEffectiveWeight(0); this.actions[k] = a; }
    }
    if (!this.actions.idle && !this.actions.sit && clips[0]) { this.actions.idle = this.mixer.clipAction(clips[0]); this.actions.idle.play(); }
    this.weights = Object.fromEntries(Object.keys(this.actions).map(k => [k, 0]));
    if (this.actions.idle) this.weights.idle = 1; else if (this.actions.sit) this.weights.sit = 1;   // start posed, not faded in from bind pose
    this.pose = 'stand';
    this.head = model.getObjectByName('head') || model.getObjectByName('Head') || model.getObjectByName('mixamorigHead') || null;
  }
  get canSit() { return !!this.actions.sit; }
  // the clip currently dominating the blend (debug / tests)
  get clip() { let best = null, w = 0.05; for (const [k, v] of Object.entries(this.weights)) if (v > w) { best = k; w = v; } return best; }
  // 'sit' uses the sit / sit_talk clips (only when the file has a sit clip), 'stand' idle / talk
  setPose(pose) {
    this.pose = pose === 'sit' && this.canSit ? 'sit' : 'stand';
    if (this.pose === 'sit') { this.weights.sit = 1; if (this.actions.idle) this.weights.idle = 0; }
  }
  animate(dt, t, speed) {
    const A = this.actions, sit = this.pose === 'sit';
    const walk = sit ? 0 : THREE.MathUtils.clamp(speed / 1.2, 0, 1), run = sit ? 0 : THREE.MathUtils.clamp((speed - 2.6) / 1.6, 0, 1);
    const base = sit ? 'sit' : A.idle ? 'idle' : 'sit';
    const talkClip = sit ? (A.sit_talk ? 'sit_talk' : null) : (A.talk ? 'talk' : null);
    const talk = talkClip && this.talking && speed < 0.2 ? 1 : 0;
    const target = { walk: A.walk ? walk * (1 - run) : 0, run: A.run ? run : 0 };
    if (talkClip) target[talkClip] = talk;
    target[base] = Math.max(0, 1 - target.walk - target.run - talk);
    const k = 1 - Math.exp(-dt * 8);                     // smooth crossfade
    for (const [name, a] of Object.entries(A)) {
      this.weights[name] += ((target[name] ?? 0) - this.weights[name]) * k;
      a.setEffectiveWeight(this.weights[name]);
    }
    // clip playback matched to ground speed (walk: ~1.1 m per cycle, run: ~2.7 m/s at 1×) — no foot sliding
    if (A.walk) A.walk.timeScale = Math.max(0.5, speed / 1.1);
    if (A.run) A.run.timeScale = Math.max(0.8, speed / 2.7);
    this.phase += dt * (5 + speed * 2.2);                // keeps footstep timing working
    this.mixer.update(dt);
  }
  wave() {}
}

// LITE: a character's primitives (skin, clothes, hair, lashes…) are one draw call each; merge
// every untextured part sharing a skeleton into a single skinned mesh with its colour baked as
// a vertex colour (textured parts — face, patterned cloth — merge per texture). ~10 → 2–3 calls.
function mergeSkinned(model) {
  const groups = new Map();
  model.traverse(o => {
    if (!o.isSkinnedMesh || o.userData.outline || o.morphTargetInfluences) return;
    const m = o.material, key = `${o.parent.uuid}|${o.skeleton.uuid}|${m.map ? m.map.uuid : '-'}|${m.side}|${m.alphaTest > 0 && m.map ? 'cut' : ''}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(o);
  });
  for (const list of groups.values()) {
    if (list.length < 2) continue;
    const first = list[0];
    if (!list.every(o => o.bindMatrix.equals(first.bindMatrix) && o.matrix.equals(first.matrix))) continue;
    const names = ['position', 'normal', 'uv', 'skinIndex', 'skinWeight'];
    if (!list.every(o => names.every(n => o.geometry.attributes[n]))) continue;
    const geos = list.map(o => {
      const g = new THREE.BufferGeometry(), src = o.geometry, n = src.attributes.position.count;
      for (const a of names) g.setAttribute(a, a === 'skinIndex' ? new THREE.BufferAttribute(Uint16Array.from(src.attributes.skinIndex.array), 4) : src.attributes[a]);
      if (src.index) g.setIndex(src.index);
      const c = o.material.color, col = new Float32Array(n * 3);
      for (let i = 0; i < n; i++) { col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b; }
      g.setAttribute('color', new THREE.BufferAttribute(col, 3));
      return g;
    });
    const merged = mergeGeometries(geos.every(g => g.index) ? geos : geos.map(g => (g.index ? g.toNonIndexed() : g)));
    if (!merged) continue;
    const m0 = first.material;
    const mat = toonMaterial(`charlite_${m0.map ? m0.map.uuid : 'vc'}_${m0.side}_${m0.alphaTest}`, { vertexColors: true, map: m0.map ?? null, side: m0.side, rim: 0.24, alphaTest: m0.map ? m0.alphaTest : 0 });
    const mesh = new THREE.SkinnedMesh(merged, mat);
    mesh.name = first.name + '_lite'; mesh.frustumCulled = false; mesh.castShadow = true; mesh.receiveShadow = true;
    mesh.position.copy(first.position); mesh.quaternion.copy(first.quaternion); mesh.scale.copy(first.scale);
    first.parent.add(mesh);
    mesh.bind(first.skeleton, first.bindMatrix);
    for (const o of list) { o.parent.remove(o); o.geometry.dispose(); }
  }
}
