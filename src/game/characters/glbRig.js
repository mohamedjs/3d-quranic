// GLB characters. If public/models/<name>.glb exists it replaces the procedural rig:
// the model is scaled to the character's height, and idle / walk / run / talk (and, for a
// seated character, sit / sit_talk) clips are blended by movement speed and speech (found by name, so Mixamo-style exports work as-is).
// Draco- and Meshopt-compressed files are supported.
import * as THREE from 'three';
import { pbrSet } from '../systems/textures.js';

let loader;
async function gltfLoader() {   // loaded only when a model file actually exists
  if (!loader) {
    const [{ GLTFLoader }, { DRACOLoader }, { MeshoptDecoder }] = await Promise.all([
      import('three/addons/loaders/GLTFLoader.js'), import('three/addons/loaders/DRACOLoader.js'), import('three/addons/libs/meshopt_decoder.module.js')]);
    const draco = new DRACOLoader().setDecoderPath('./draco/');
    loader = new GLTFLoader().setDRACOLoader(draco).setMeshoptDecoder(MeshoptDecoder);
  }
  return loader;
}

// Resolves to a rig, or null when the file is absent (so the caller falls back quietly).
export async function loadGlbRig(url, targetHeight) {
  try {
    const head = await fetch(url, { method: 'HEAD' });
    if (!head.ok || !/model|octet|gltf/.test(head.headers.get('content-type') || 'model/gltf-binary')) return null;
  } catch { return null; }
  const gltf = await (await gltfLoader()).loadAsync(url);   // a present-but-broken file should fail loudly
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
    const cotton = pbrSet('cotton_jersey', 6);
    model.traverse(o => {
      if (!o.isMesh) return;
      o.castShadow = true; o.receiveShadow = true; o.frustumCulled = false;   // skinned: bounds move with the pose
      const m = o.material; if (!m) return;
      if (/^cloth_/.test(m.name)) {                       // woven fabric: real normal/roughness detail
        m.normalMap = cotton.normalMap; m.roughnessMap = cotton.roughnessMap; m.roughness = 1; m.normalScale = new THREE.Vector2(0.7, 0.7);
      }
      if (/beard/.test(m.name)) m.roughness = 1;
      if (/hair_clumps/.test(m.name)) { m.roughness = 0.42; m.envMapIntensity = 1.2; }          // sculpted, softly glossy hair
      if (/^leather/.test(m.name)) { m.roughness = 0.55; m.normalMap = cotton.normalMap; m.normalScale = new THREE.Vector2(0.25, 0.25); }
      if (/\.body/.test(m.name) && !m.isMeshPhysicalMaterial) {                                  // warm, glowing skin
        o.material = new THREE.MeshPhysicalMaterial({ map: m.map, normalMap: m.normalMap, color: m.color, roughness: 0.55,
          sheen: 0.6, sheenRoughness: 0.45, sheenColor: new THREE.Color(0xff8a6a), clearcoat: 0.04, clearcoatRoughness: 0.6 });
        o.material.name = m.name; return;
      }
      if (m.transparent) {                                 // eyebrows/lashes/hair cards: cut-out, no sorting artefacts
        m.transparent = false; m.alphaTest = 0.35; m.depthWrite = true; o.castShadow = false;
      }
      m.needsUpdate = true;
    });
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
