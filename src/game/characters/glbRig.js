// GLB characters. If public/models/<name>.glb exists it replaces the procedural rig:
// the model is scaled to the character's height, and idle / walk / run / talk (and, for a
// seated character, sit / sit_talk) clips are blended by movement speed and speech.
// Merges each v4 character into at most 3 skinned draws (skin+face+eye, garments, hair+metal)
// driven by characterMaterial.js (Poly Haven fabric DataArrayTexture + soft wrap PBR skin).
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import {
  FABRIC_LAYER_INDEX,
  ensureCharacterTextures,
  getGarmentMaterial,
  getHairMetalMaterial,
  getSkinFaceMaterial,
  registerCharacterMesh,
} from '../shaders/characterMaterial.js';
import { useGame } from '../systems/store.js';
import { PRESETS } from '../systems/quality.js';
import { gltfLoader } from '../world/loaders.js';

// Resolves to a rig, or null when the file is absent (so the caller falls back quietly).
export async function loadGlbRig(url, targetHeight) {
  try {
    const head = await fetch(url, { method: 'HEAD' });
    if (!head.ok || /text\/html/i.test(head.headers.get('content-type') || '')) return null;
  } catch { return null; }
  const gltf = await gltfLoader().loadAsync(url);   // a present-but-broken file should fail loudly
  return new GlbRig(gltf, targetHeight);
}

// clip names the character files use: player idle/walk/run/talk · farmer idle/walk/talk ·
// grandma_zainab sit/sit_talk (+ idle). Mixamo-style names still match the looser patterns.
const CLIPS = {
  sit_talk: [/^sit_?talk$/i, /sit.*talk|talk.*sit/i],
  sit: [/^sit(ting)?$/i, /sit/i],
  idle: [/^idle$/i, /idle|breath|stand/i],
  walk: [/^walk$/i, /walk/i],
  run: [/^run$/i, /run|jog/i],
  talk: [/^talk$/i, /talk|explain|conversation/i],
};

const _C = new THREE.Color();

function baseMatName(m) {
  return (m?.name || '').replace(/\.\d+$/, '');
}

function classifyMaterial(name, srcMat) {
  if (name === 'outline') return { bucket: 'outline' };
  const fIdx = FABRIC_LAYER_INDEX[name];
  if (fIdx !== undefined) return { bucket: 'garment', attr: 'aLayer', val: fIdx };
  if (name.startsWith('face_') || name.startsWith('toon_face_')) return { bucket: 'skinFace', attr: 'aPart', val: 0 };
  if (name === 'skin' || name.startsWith('toon_skin')) return { bucket: 'skinFace', attr: 'aPart', val: 1 };
  if (name === 'eye') return { bucket: 'skinFace', attr: 'aPart', val: 2 };
  if (name === 'metal') return { bucket: 'hairMetal', attr: 'aPart', val: 1 };
  if (name === 'hair') return { bucket: 'hairMetal', attr: 'aPart', val: 0 };
  if (srcMat?.map) return { bucket: 'skinFace', attr: 'aPart', val: 0 };
  return { bucket: 'hairMetal', attr: 'aPart', val: 0 };
}

function configureFaceMap(tex, pbr) {
  if (!tex) return null;
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.minFilter = THREE.LinearMipmapLinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.anisotropy = pbr ? 4 : 1;
  tex.needsUpdate = true;
  return tex;
}

// Copy skinned geometry with normalized attribute types (Float32 pos/normal/uv/skinWeight/color,
// Uint16 skinIndex) and per-vertex scalar attribute (aLayer or aPart) so mergeGeometries never fails.
function prepareSkinnedGeo(mesh, attrName, attrVal) {
  const src = mesh.geometry;
  const pos = src.attributes.position;
  if (!pos || !src.attributes.skinIndex || !src.attributes.skinWeight) return null;
  const n = pos.count;
  const g = new THREE.BufferGeometry();

  const pArr = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { pArr[i * 3] = pos.getX(i); pArr[i * 3 + 1] = pos.getY(i); pArr[i * 3 + 2] = pos.getZ(i); }
  g.setAttribute('position', new THREE.BufferAttribute(pArr, 3));

  const nrm = src.attributes.normal;
  const nArr = new Float32Array(n * 3);
  if (nrm) {
    for (let i = 0; i < n; i++) { nArr[i * 3] = nrm.getX(i); nArr[i * 3 + 1] = nrm.getY(i); nArr[i * 3 + 2] = nrm.getZ(i); }
  }
  g.setAttribute('normal', new THREE.BufferAttribute(nArr, 3));

  const uv = src.attributes.uv;
  const uvArr = new Float32Array(n * 2);
  if (uv) {
    for (let i = 0; i < n; i++) { uvArr[i * 2] = uv.getX(i); uvArr[i * 2 + 1] = uv.getY(i); }
  }
  g.setAttribute('uv', new THREE.BufferAttribute(uvArr, 2));

  const si = src.attributes.skinIndex;
  const siArr = new Uint16Array(n * 4);
  for (let i = 0; i < n; i++) {
    siArr[i * 4] = si.getX(i); siArr[i * 4 + 1] = si.getY(i); siArr[i * 4 + 2] = si.getZ(i); siArr[i * 4 + 3] = si.getW(i);
  }
  g.setAttribute('skinIndex', new THREE.BufferAttribute(siArr, 4));

  const sw = src.attributes.skinWeight;
  const swArr = new Float32Array(n * 4);
  for (let i = 0; i < n; i++) {
    swArr[i * 4] = sw.getX(i); swArr[i * 4 + 1] = sw.getY(i); swArr[i * 4 + 2] = sw.getZ(i); swArr[i * 4 + 3] = sw.getW(i);
  }
  g.setAttribute('skinWeight', new THREE.BufferAttribute(swArr, 4));

  const colArr = new Float32Array(n * 3);
  const srcCol = src.attributes.color;
  const mc = mesh.material?.color;
  const mr = mc ? mc.r : 1, mg = mc ? mc.g : 1, mb = mc ? mc.b : 1;
  if (srcCol) {
    for (let i = 0; i < n; i++) {
      _C.fromBufferAttribute(srcCol, i);
      colArr[i * 3] = _C.r * mr; colArr[i * 3 + 1] = _C.g * mg; colArr[i * 3 + 2] = _C.b * mb;
    }
  } else {
    for (let i = 0; i < n; i++) { colArr[i * 3] = mr; colArr[i * 3 + 1] = mg; colArr[i * 3 + 2] = mb; }
  }
  g.setAttribute('color', new THREE.BufferAttribute(colArr, 3));

  const tagArr = new Float32Array(n);
  tagArr.fill(attrVal);
  g.setAttribute(attrName, new THREE.BufferAttribute(tagArr, 1));

  if (src.index) {
    const idx = src.index;
    const iArr = new Uint32Array(idx.count);
    for (let i = 0; i < idx.count; i++) iArr[i] = idx.getX(i);
    g.setIndex(new THREE.BufferAttribute(iArr, 1));
  }
  if (!nrm) g.computeVertexNormals();
  return g;
}

// Merge character skinned primitives into at most 3 skinned draws (skin+face+eye, garments, hair+metal).
// Safely ignores and hides any legacy `outline` material if one ever appears.
function assembleCharacterMeshes(model, shading) {
  const pbr = shading === 'pbr';
  const buckets = new Map();
  const toRemove = [];
  let faceMap = null;

  model.traverse(o => {
    if (!o.isMesh) return;
    const m = o.material;
    if (!m) return;
    const name = baseMatName(m);
    const info = classifyMaterial(name, m);
    if (info.bucket === 'outline') {
      o.visible = false; o.castShadow = false; o.receiveShadow = false;
      toRemove.push(o);
      return;
    }
    if (!o.isSkinnedMesh || o.morphTargetInfluences) {
      o.frustumCulled = false; o.castShadow = true; o.receiveShadow = true;
      return;
    }
    if (info.bucket === 'skinFace' && m.map && !faceMap) faceMap = configureFaceMap(m.map, pbr);
    const skelKey = o.skeleton.bones.map(b => b.uuid).join(',');
    const key = `${o.parent.uuid}|${skelKey}|${info.bucket}`;
    if (!buckets.has(key)) buckets.set(key, { bucket: info.bucket, attr: info.attr, items: [] });
    buckets.get(key).items.push({ mesh: o, val: info.val });
  });

  for (const o of toRemove) { o.parent?.remove(o); o.geometry?.dispose(); }

  for (const { bucket, attr, items } of buckets.values()) {
    const first = items[0].mesh;
    const geos = [];
    for (const { mesh, val } of items) {
      const g = prepareSkinnedGeo(mesh, attr, val);
      if (g) geos.push(g);
    }
    if (!geos.length) continue;
    const indexed = geos.every(g => g.index);
    const merged = geos.length > 1
      ? mergeGeometries(indexed ? geos : geos.map(g => (g.index ? g.toNonIndexed() : g)))
      : geos[0];
    if (!merged) continue;
    merged.computeBoundingBox();
    merged.computeBoundingSphere();

    let mat;
    if (bucket === 'garment') mat = getGarmentMaterial(shading);
    else if (bucket === 'skinFace') mat = getSkinFaceMaterial(faceMap, shading);
    else mat = getHairMetalMaterial(shading);

    const skinned = new THREE.SkinnedMesh(merged, mat);
    skinned.name = `${first.name}_${bucket}`;
    skinned.frustumCulled = false;
    skinned.castShadow = true;
    skinned.receiveShadow = true;
    skinned.position.copy(first.position);
    skinned.quaternion.copy(first.quaternion);
    skinned.scale.copy(first.scale);
    first.parent.add(skinned);
    skinned.bind(first.skeleton, first.bindMatrix);
    registerCharacterMesh(skinned);

    for (const { mesh } of items) { mesh.parent?.remove(mesh); mesh.geometry?.dispose(); }
  }
}

class GlbRig {
  constructor(gltf, targetHeight) {
    const model = gltf.scene;
    const shading = PRESETS[useGame.getState().quality]?.shading ?? 'toon';
    ensureCharacterTextures(shading);
    assembleCharacterMeshes(model, shading);
    this.hulls = [];

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
