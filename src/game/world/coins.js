// Collectibles: gold coins (crescent-and-star emboss) as a breadcrumb line along the guided
// route and in little clusters round the village, fields and canal banks, plus a few big stars
// (worth 5) in out-of-the-way spots. One InstancedMesh per kind (+ its ink hull off Low); picking
// one up pops it, flies a coin to the points pill, sparkles and dings — quicker pickups ring
// higher, every 10 in a row plays a chime and gives a small bonus. No timers, nothing to lose.
import * as THREE from 'three';
import { rng, LOOKOUT, OASIS, RUINS, ROAD_CANALS, riverZ, pathDist, groundAt } from '../terrain/heightfield.js';
import { paint, merge } from '../vegetation/plants.js';
import { toonMaterial, outlineMaterial } from '../shaders/toon.js';
import { Sound } from '../systems/audio.js';
import { noReflect } from '../systems/layers.js';
import { refs } from '../systems/refs.js';
import { createSearch, buildRoute } from '../systems/guide.js';

const PICK2 = 0.9 * 0.9, ROUTE_ID = 1e8, STATIC_ID = 2e8, STAR_ID = 3e8;
const IDLE = 1, POP = 2, GONE = 3;

function starShape(R, r, n = 5, cx = 0, cy = 0, rot = Math.PI / 2) {
  const s = new THREE.Shape();
  for (let i = 0; i < n * 2; i++) {
    const a = rot + i * Math.PI / n, k = i % 2 ? r : R;
    i ? s.lineTo(cx + Math.cos(a) * k, cy + Math.sin(a) * k) : s.moveTo(cx + Math.cos(a) * k, cy + Math.sin(a) * k);
  }
  s.closePath(); return s;
}
function crescentShape(R = 0.15, d = 0.07, r = 0.13) {
  const x = (d * d + R * R - r * r) / (2 * d), y = Math.sqrt(R * R - x * x), a1 = Math.atan2(y, x), b1 = Math.atan2(y, x - d);
  const s = new THREE.Shape();
  s.absarc(0, 0, R, a1, Math.PI * 2 - a1, false);
  s.absarc(d, 0, r, -b1, b1, true);
  return s;
}
function coinGeometry(seg = 18) {
  // lathe profile (radius, thickness): a flat face inside a raised rim — one cheap closed body
  const prof = [[0, 0.02], [0.19, 0.02], [0.205, 0.034], [0.26, 0.03], [0.265, 0], [0.26, -0.03], [0.205, -0.034], [0.19, -0.02], [0, -0.02]].map(([r, y]) => new THREE.Vector2(r, y));
  const body = new THREE.LatheGeometry(prof.reverse(), seg).rotateX(Math.PI / 2).toNonIndexed();
  const p = body.attributes.position, col = new Float32Array(p.count * 3), face = new THREE.Color(0xEDB136), rim = new THREE.Color(0xFFD25E);
  for (let i = 0; i < p.count; i++) { const c = Math.hypot(p.getX(i), p.getY(i)) > 0.196 ? rim : face; col.set([c.r, c.g, c.b], i * 3); }
  body.setAttribute('color', new THREE.BufferAttribute(col, 3));
  // flat crescent-and-star emboss on both faces (caps only: a few triangles)
  const emb = new THREE.ShapeGeometry([crescentShape(), starShape(0.055, 0.024, 5, 0.085, 0.0)], seg < 18 ? 3 : 5).rotateZ(0.5);
  const front = paint(emb.clone().translate(0, 0, 0.0215), 0xFFF0B8), back = paint(emb.clone().rotateY(Math.PI).translate(0, 0, -0.0215), 0xFFF0B8);
  return merge([body, front, back]);
}
function starGeometry() {
  const g = new THREE.ExtrudeGeometry(starShape(0.42, 0.19), { depth: 0.1, bevelEnabled: true, bevelThickness: 0.045, bevelSize: 0.04, bevelSegments: 1, curveSegments: 4 });
  g.translate(0, 0, -0.05);
  const inner = new THREE.ShapeGeometry(starShape(0.2, 0.09)).translate(0, 0, 0.1), innerB = inner.clone().rotateY(Math.PI);
  return merge([paint(g, 0xFFC93C), paint(inner, 0xFFF1B0), paint(innerB, 0xFFF1B0)]);
}
function goldMaterial(key, emissive) {
  const m = toonMaterial(key, { vertexColors: true, rim: 0.55 });
  m.emissive.setHex(emissive);
  return m;
}

// sparkle burst: one Points object, pooled particles (no allocations after start)
function sparkles() {
  const SP = 90, pos = new Float32Array(SP * 3), life = new Float32Array(SP), vel = new Float32Array(SP * 3);
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3).setUsage(THREE.DynamicDrawUsage));
  geo.setAttribute('aLife', new THREE.BufferAttribute(life, 1).setUsage(THREE.DynamicDrawUsage));
  geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e6);
  const mat = new THREE.ShaderMaterial({
    uniforms: { uProj: { value: 600 } },
    vertexShader: /* glsl */`attribute float aLife; uniform float uProj; varying float vL;
      void main() { vL = aLife; vec4 mv = modelViewMatrix * vec4(position, 1.); gl_Position = projectionMatrix * mv;
        gl_PointSize = aLife > 0. ? .16 * (.4 + .6 * aLife) * uProj / -mv.z : 0.; }`,
    fragmentShader: /* glsl */`varying float vL;
      void main() { vec2 p = gl_PointCoord * 2. - 1.;
        float star = max(0., 1. - abs(p.x * p.y) * 30.) * (1. - length(p)), glow = exp(-dot(p, p) * 5.);
        float a = clamp(star * 1.2 + glow * .5, 0., 1.) * min(1., vL * 2.);
        gl_FragColor = vec4(vec3(1., .88, .52) * a, a);
        #include <colorspace_fragment>
      }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false, fog: false,
  });
  const pts = noReflect(new THREE.Points(geo, mat)); pts.frustumCulled = false; pts.visible = false; pts.renderOrder = 4;
  let next = 0, alive = 0;
  return {
    object: pts,
    emit(x, y, z, n, seed) {
      for (let k = 0; k < n; k++) {
        const i = next; next = (next + 1) % SP;
        const a = (k / n) * Math.PI * 2 + seed, up = 0.35 + ((k * 7 + seed * 13) % 5) * 0.15, sp = 1.3 + ((k * 3) % 4) * 0.3;
        pos[i * 3] = x; pos[i * 3 + 1] = y; pos[i * 3 + 2] = z;
        vel[i * 3] = Math.cos(a) * sp; vel[i * 3 + 1] = up * 3.2; vel[i * 3 + 2] = Math.sin(a) * sp;
        if (life[i] <= 0) alive++;
        life[i] = 1;
      }
      pts.visible = true;
    },
    update(dt, proj) {
      if (!alive) { pts.visible = false; return; }
      mat.uniforms.uProj.value = proj;
      alive = 0;
      const drag = Math.exp(-dt * 2.5);
      for (let i = 0; i < SP; i++) {
        if (life[i] <= 0) continue;
        life[i] -= dt / 0.65;
        if (life[i] <= 0) { life[i] = 0; continue; }
        alive++;
        vel[i * 3] *= drag; vel[i * 3 + 2] *= drag; vel[i * 3 + 1] = vel[i * 3 + 1] * drag - 4 * dt;
        pos[i * 3] += vel[i * 3] * dt; pos[i * 3 + 1] += vel[i * 3 + 1] * dt; pos[i * 3 + 2] += vel[i * 3 + 2] * dt;
      }
      geo.attributes.position.needsUpdate = true; geo.attributes.aLife.needsUpdate = true;
    },
  };
}

// Deterministic exploration layout: clusters (rows, rings, little arches) and big-star spots.
// Every quality level gets the same layout (coin ids and the story coin sets depend on it).
function layout(grid, avoid) {
  const r = rng(4242), coins = [], stars = [];
  const free = (x, z) => grid.walkable(x, z) && !avoid.some(([ax, az]) => Math.hypot(ax - x, az - z) < 3.2);
  let cluster = 0;
  const add = (pts) => {
    cluster++;
    for (const [x, z, h = 0] of pts) if (free(x, z)) coins.push([x, z, h, cluster]);
  };
  const row = (x, z, dx, dz, n = 5, gap = 1.3, arch = false) => add(Array.from({ length: n }, (_, i) => {
    const t = i - (n - 1) / 2; return [x + dx * t * gap, z + dz * t * gap, arch ? 0.6 * Math.sin(Math.PI * i / (n - 1)) : 0];
  }));
  const ring = (x, z, rad = 1.5, n = 6) => add(Array.from({ length: n }, (_, i) => [x + Math.cos(i / n * Math.PI * 2) * rad, z + Math.sin(i / n * Math.PI * 2) * rad, 0]));
  // the village street and square
  for (let k = 0; k < 2; k++) row(1.4, -50 + k * 20 + r() * 5, 0, 1, 5, 1.4, k === 1);
  for (let k = 0; k < 5; k++) { const a = r() * Math.PI * 2, d = 14 + r() * 18; ring(Math.cos(a) * d, Math.sin(a) * d); }
  // the field road (z = 14) and the north road toward the river
  for (let k = 0; k < 4; k++) row((k % 2 ? 1 : -1) * (12 + r() * 55), 12.8, 1, 0, 6, 1.3, k === 2);
  for (let k = 0; k < 2; k++) row(-1.4, 24 + k * 16 + r() * 5, 0, 1, 5, 1.4);
  // canal banks: the far side of each road canal, along the water
  for (const c of ROAD_CANALS) {
    const [a, b] = [c[0], c[c.length - 1]], t = 0.3 + r() * 0.4, x = a[0] + (b[0] - a[0]) * t, z = a[1] + (b[1] - a[1]) * t;
    const L = Math.hypot(b[0] - a[0], b[1] - a[1]), dx = (b[0] - a[0]) / L, dz = (b[1] - a[1]) / L;
    const side = pathDist(x - dz * 2.6, z + dx * 2.6) > pathDist(x + dz * 2.6, z - dx * 2.6) ? 1 : -1;
    row(x - dz * 2.7 * side, z + dx * 2.7 * side, dx, dz, 5, 1.4, true);
  }
  // round the oasis pond, along the east road, on the lookout hill, by the river bridge
  for (let k = 0; k < 3; k++) { const a = r() * Math.PI * 2, d = OASIS.r + 5 + r() * 5, x = OASIS.x + Math.cos(a) * d, z = OASIS.z + Math.sin(a) * d; row(x, z, -Math.sin(a), Math.cos(a), 5, 1.3, true); }
  for (const t of [0.3, 0.75]) row(40 + 50 * t, -10 - 16 * t - 2.4, 0.95, -0.3, 5, 1.4);
  for (let k = 0; k < 2; k++) { const a = r() * Math.PI * 2; ring(LOOKOUT.x + Math.cos(a) * 9, LOOKOUT.z + Math.sin(a) * 9, 1.6, 7); }
  row(10, riverZ(10) - 9.5, 1, 0, 6, 1.3);
  // big stars (worth 5) in out-of-the-way spots; nudged to the nearest walkable ground
  const spots = [[LOOKOUT.x, LOOKOUT.z], [8.2, -88], [-9, riverZ(-9) - 8.5], [OASIS.x + OASIS.r + 3.5, OASIS.z + 2], [-121, -47], [RUINS.x + 2, RUINS.z - 5], [17.8, 62], [128, -45], [-58, 21]];
  for (const [sx, sz] of spots) {
    let got = null;
    for (let rad = 0; rad <= 8 && !got; rad += 1) for (let a = 0; a < 8 && !got; a++) {
      const x = sx + Math.cos(a * Math.PI / 4) * rad, z = sz + Math.sin(a * Math.PI / 4) * rad;
      if (free(x, z)) got = [x, z];
      if (rad === 0) break;
    }
    if (got) stars.push(got);
  }
  return { coins, stars };
}

// ---- story coin sets ------------------------------------------------------------------------
// Every story owns a deterministic set of coins: a line along the walkable (A*) route from the
// previous story of its category (or the spawn) to its storyteller, plus the exploration clusters
// and big stars that lie close to that route, topped up with little side arches on short routes.
// Route coins have string ids "<story>:<k>"; cluster coins/stars keep their numeric ids and may
// belong to several sets. Sets are computed a few ms per frame (title screen included) and
// cached in localStorage (they only depend on the world and the endpoints).
const SET_VERSION = 2, CACHE_KEY = 'quran-journey-coinsets', SLOTS = 64;
const MIN_SET = 20, ROUTE_COINS_MAX = 30, EXTRA_MAX = 14, NEAR_CLUSTER = 6, NEAR_STAR = 12;
// the story order of the old breadcrumb ids (ROUTE_ID + index·1e6 + cell) in saves before sets
const OLD_ORDER = ['people-of-the-elephant', 'quraysh-journeys', 'yusuf-dream', 'threads-of-dawn', 'qays-the-fasting-farmer', 'best-dates', 'houses-by-their-doors', 'the-new-qibla', 'the-guest-and-the-lamp'];

export function createCoins({ scene, camera, grid, ui, npcs, getSave, persist, S, lite = false, endpoints, onCollect, onBuilt }) {
  const avoid = npcs.flatMap(n => n.members.map(m => [m.def.position[0], m.def.position[1]]));
  const L = layout(grid, avoid);
  const nStatic = L.coins.length, nStar = L.stars.length, S0 = nStatic + nStar, total = S0 + SLOTS;
  const X = new Float32Array(total), Y = new Float32Array(total), Z = new Float32Array(total), Hh = new Float32Array(total);
  const KEY = new Array(total), ST = new Uint8Array(total), T0 = new Float32Array(total), BIG = new Uint8Array(total);
  L.coins.forEach(([x, z, h], k) => { X[k] = x; Z[k] = z; Hh[k] = h; Y[k] = groundAt(x, z); KEY[k] = STATIC_ID + k; });
  L.stars.forEach(([x, z], k) => { const i = nStatic + k; X[i] = x; Z[i] = z; Y[i] = groundAt(x, z); KEY[i] = STAR_ID + k; BIG[i] = 1; });
  const slotOfId = id => (id >= STAR_ID ? nStatic + (id - STAR_ID) : id - STATIC_ID);

  const coinMesh = new THREE.InstancedMesh(coinGeometry(lite ? 10 : 18), goldMaterial('coin_gold', 0x4a3000), nStatic + SLOTS);
  const coinInk = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.29, 0.29, 0.1, 14).rotateX(Math.PI / 2), outlineMaterial('env'), nStatic + SLOTS);
  const starMesh = new THREE.InstancedMesh(starGeometry(), goldMaterial('coin_star', 0x6a4400), Math.max(1, nStar));
  const starInk = new THREE.InstancedMesh(new THREE.ExtrudeGeometry(starShape(0.5, 0.25), { depth: 0.22, bevelEnabled: false }).translate(0, 0, -0.11), outlineMaterial('env'), Math.max(1, nStar));
  coinInk.instanceMatrix = coinMesh.instanceMatrix; starInk.instanceMatrix = starMesh.instanceMatrix;   // hulls share the matrices
  for (const m of [coinMesh, coinInk, starMesh, starInk]) {
    m.instanceMatrix.setUsage(THREE.DynamicDrawUsage); m.frustumCulled = false; m.count = 0;
    m.castShadow = false; m.receiveShadow = false; noReflect(m); scene.add(m);
  }
  coinMesh.name = 'coins'; starMesh.name = 'big-stars'; coinInk.name = 'coins-ink'; starInk.name = 'big-stars-ink';
  const fx = sparkles(); fx.object.name = 'sparkles'; scene.add(fx.object);

  let collected = new Set(), combo = 0, lastPick = -9, dirty = false, lastSave = 0, collectedCount = 0, shown = undefined, setsVersion = 0, shownVersion = -1;
  const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _p = new THREE.Vector3(), _s = new THREE.Vector3(), _up = new THREE.Vector3(0, 1, 0), _v = new THREE.Vector3();

  // ---- set building (time-sliced A*, cached) ----
  const sig = `${SET_VERSION}/${nStatic}/${nStar}`;
  let cache = { sig, sets: {} };
  try { const c = JSON.parse(localStorage.getItem(CACHE_KEY)); if (c?.sig === sig && c.sets) cache = c; } catch { /* private mode */ }
  const writeCache = () => { try { localStorage.setItem(CACHE_KEY, JSON.stringify(cache)); } catch { /* full / private */ } };
  const sets = new Map(), queue = [], search = createSearch(grid);
  let job = null;
  const near = (a, b) => a && b && Math.hypot(a[0] - b[0], a[1] - b[1]) < 0.3;
  const okAt = (x, z) => grid.walkable(x, z) && !avoid.some(([ax, az]) => Math.hypot(ax - x, az - z) < 2.2);
  // the nearest walkable spot (storytellers sit against walls: start the search just outside)
  const snap = ([x, z]) => {
    if (grid.walkable(x, z)) return [x, z];
    for (let rad = 1; rad <= 6; rad += 0.75) for (let a = 0; a < 16; a++) {
      const px = x + Math.cos(a * Math.PI / 8) * rad, pz = z + Math.sin(a * Math.PI / 8) * rad;
      if (grid.walkable(px, pz)) return [px, pz];
    }
    return [x, z];
  };

  function placeSet(id, route, ep) {
    const pts = [], path = [];
    const dist = (x, z) => { let m = Infinity; for (const [px, pz] of path) m = Math.min(m, Math.hypot(px - x, pz - z)); return m; };
    const taken = (x, z, r = 1.2) => pts.some(p => Math.hypot(p[0] - x, p[1] - z) < r);
    if (route) {
      for (let i = 0; i < route.n; i += 2) path.push([route.x[i], route.z[i]]);
      path.push([route.x[route.n - 1], route.z[route.n - 1]]);
      const L0 = 4, span = Math.max(0, route.len - 3.5 - L0);
      const n = Math.max(1, Math.min(ROUTE_COINS_MAX, Math.round(span / 4.5) + 1, Math.floor(span / 2) + 1)), gap = n > 1 ? span / (n - 1) : 0;
      for (let m = 0; m < n; m++) {
        const s = L0 + gap * m, i = Math.min(route.n - 2, Math.floor(s / 0.5)), a = Math.max(0, i - 2), b = Math.min(route.n - 1, i + 2);
        let tx = route.x[b] - route.x[a], tz = route.z[b] - route.z[a]; const tl = Math.hypot(tx, tz) || 1; tx /= tl; tz /= tl;
        const g = Math.floor(m / 6), j = m % 6, pat = g % 3, w = Math.sin(Math.PI * j / 5);
        let x = route.x[i], z = route.z[i];
        const lat = pat === 1 ? 0.7 * w * (g % 2 ? 1 : -1) : 0, h = pat === 2 ? 0.55 * w : 0;
        if (lat && okAt(x - tz * lat, z + tx * lat)) { x -= tz * lat; z += tx * lat; }
        if (!okAt(x, z) || taken(x, z, 1.6)) continue;
        pts.push([x, z, h]);
      }
    } else path.push(ep.to);
    // exploration clusters and big stars close to the route
    const extra = [], clusters = new Map();
    L.coins.forEach(([x, z, , c], k) => { const d = dist(x, z); const cl = clusters.get(c) ?? { d: Infinity, ks: [] }; cl.d = Math.min(cl.d, d); cl.ks.push(k); clusters.set(c, cl); });
    for (const cl of [...clusters.values()].filter(c => c.d < NEAR_CLUSTER).sort((a, b) => a.d - b.d)) {
      if (extra.length + cl.ks.length > EXTRA_MAX) continue;
      for (const k of cl.ks) extra.push(STATIC_ID + k);
    }
    L.stars.map(([x, z], k) => [dist(x, z), k]).filter(([d]) => d < NEAR_STAR).sort((a, b) => a[0] - b[0]).slice(0, 2).forEach(([, k]) => extra.push(STAR_ID + k));
    // no route coin right on top of a cluster coin
    for (let q = pts.length - 1; q >= 0; q--) if (extra.some(e => e < STAR_ID && Math.hypot(X[slotOfId(e)] - pts[q][0], Z[slotOfId(e)] - pts[q][1]) < 1.2)) pts.splice(q, 1);
    // short routes: little side arches just off the way, so exploring pays off
    for (const f of [0.35, 0.7, 0.15, 0.55, 0.85]) {
      if (pts.length + extra.length >= MIN_SET) break;
      let cx, cz, tx = 1, tz = 0;
      if (route) {
        const i = Math.min(route.n - 3, Math.floor(f * (route.n - 1))), a = Math.max(0, i - 3), b = Math.min(route.n - 1, i + 3);
        tx = route.x[b] - route.x[a]; tz = route.z[b] - route.z[a]; const tl = Math.hypot(tx, tz) || 1; tx /= tl; tz /= tl;
        cx = route.x[i]; cz = route.z[i];
      } else { const a = f * Math.PI * 2; cx = ep.to[0] + Math.cos(a) * 7; cz = ep.to[1] + Math.sin(a) * 7; tx = -Math.sin(a); tz = Math.cos(a); }
      for (const off of [4, -4, 5.5, -5.5]) {
        const ox = cx - tz * off, oz = cz + tx * off, row = [];
        for (let q = 0; q < 5; q++) { const t = (q - 2) * 1.3; row.push([ox + tx * t, oz + tz * t, 0.6 * Math.sin(Math.PI * q / 4)]); }
        if (row.every(([x, z]) => okAt(x, z) && !taken(x, z))) { pts.push(...row); break; }
      }
    }
    const r2 = v => Math.round(v * 100) / 100;
    return { from: ep.from, to: ep.to, len: route ? +route.len.toFixed(1) : 0, reached: route ? !!route.reached : false,
      route: pts.map(([x, z, h]) => [r2(x), r2(z), r2(h)]), extra, path: path.map(([x, z]) => [r2(x), r2(z)]) };
  }
  // saves from before coin sets: breadcrumb coins collected on the way to a story count for its set
  function migrate(id, keys, def) {
    const save = getSave(), t = OLD_ORDER.indexOf(id);
    if (t < 0 || !Array.isArray(save.coins)) return;
    let added = 0;
    for (const n of save.coins) {
      if (typeof n !== 'number' || n < ROUTE_ID || n >= STATIC_ID || Math.floor((n - ROUTE_ID) / 1e6) !== t) continue;
      const r = (n - ROUTE_ID) % 1e6, x = (Math.floor(r / 1000) - 150) * 2.5, z = (r % 1000 - 150) * 2.5;
      let best = -1, bd = 3;
      def.route.forEach(([px, pz], k) => { const d = Math.hypot(px - x, pz - z); if (d < bd && !collected.has(keys[k])) { bd = d; best = k; } });
      if (best >= 0) { collected.add(keys[best]); save.coins.push(keys[best]); added++; }
    }
    if (added) dirty = true;
  }
  function finish(id, def) {
    const keys = def.route.map((_, k) => `${id}:${k}`).concat(def.extra);
    sets.set(id, { ...def, keys });
    migrate(id, keys, def);
    setsVersion++;
    onBuilt?.(id);
  }
  function want(ids, front = false) {
    for (const id of ids) {
      if (sets.has(id) || job?.id === id) continue;
      const q = queue.indexOf(id);
      if (q >= 0) { if (front) { queue.splice(q, 1); queue.unshift(id); } }
      else front ? queue.unshift(id) : queue.push(id);
    }
  }
  function build(ms) {
    if (!job) {
      while (queue.length && !job) {
        const id = queue.shift(); if (sets.has(id)) continue;
        const ep = endpoints(id); if (!ep) continue;
        const c = cache.sets[id];
        if (c && near(c.from, ep.from) && near(c.to, ep.to)) { finish(id, c); continue; }
        const s = snap(ep.from);
        search.start(s[0], s[1], ep.to[0], ep.to[1], ep.r);
        job = { id, ep, s };
      }
      if (!job) return;
    }
    const cells = search.step(ms);
    if (!cells) return;
    const { id, ep, s } = job; job = null;
    const route = cells.length > 1 ? buildRoute(grid, cells, s[0], s[1]) : null;
    if (route) route.reached = cells.reached;
    const def = placeSet(id, route, ep);
    cache.sets[id] = def; writeCache();
    finish(id, def);
  }

  function load() {
    const save = getSave();
    if (!Array.isArray(save.coins)) save.coins = [];
    collected = new Set(save.coins);
    for (let i = 0; i < S0; i++) ST[i] = collected.has(KEY[i]) ? GONE : IDLE;
    for (let i = S0; i < total; i++) ST[i] = 0;
    shown = undefined;
    for (const [id, set] of sets) migrate(id, set.keys, set);
  }
  // lay out the route coins of one story's set (the current target), in the pool slots
  function show(id) {
    shown = id; shownVersion = setsVersion;
    for (let i = S0; i < total; i++) if (ST[i] !== POP) ST[i] = 0;
    const set = id ? sets.get(id) : null;
    if (!set) return;
    set.route.forEach(([x, z, h], k) => {
      const i = S0 + k; if (i >= total || ST[i] === POP) return;
      X[i] = x; Z[i] = z; Y[i] = groundAt(x, z); Hh[i] = h; KEY[i] = set.keys[k]; ST[i] = collected.has(KEY[i]) ? GONE : IDLE;
    });
  }
  // {have, total} of a story's set, or null while it is still being worked out
  function progress(id) {
    const set = sets.get(id); if (!set) return null;
    let have = 0; for (const k of set.keys) if (collected.has(k)) have++;
    return { have, total: set.keys.length };
  }
  // where the golden trail leads while a story is still locked: the nearest coin of its set that
  // is still lying there (kept until picked up unless another is clearly closer)
  function nextCoin(id, px, pz, keepKey = null) {
    const set = sets.get(id); if (!set) return null;
    let best = null, bd = Infinity, keep = null;
    const consider = (key, x, z) => {
      if (collected.has(key)) return;
      const d = Math.hypot(x - px, z - pz);
      if (key === keepKey) keep = { key, x, z, d };
      if (d < bd) { bd = d; best = { key, x, z, d }; }
    };
    set.route.forEach(([x, z], k) => consider(set.keys[k], x, z));
    for (const e of set.extra) { const i = slotOfId(e); consider(e, X[i], Z[i]); }
    return keep && keep.d < bd + 8 ? keep : best;
  }

  function collect(i, now, preset) {
    const save = getSave(), big = BIG[i] === 1, value = big ? 5 : 1, key = KEY[i];
    ST[i] = POP; T0[i] = now;
    save.points += value; save.coins.push(key); collected.add(key); dirty = true; collectedCount++;
    combo = now - lastPick < 1.6 ? combo + 1 : 1; lastPick = now;
    Sound.coin(Math.min(combo - 1, 10), big);
    _v.set(X[i], Y[i] + (big ? 0.9 : 0.55) + Hh[i], Z[i]).project(camera);
    const on = _v.z < 1 && Math.abs(_v.x) < 1.1 && Math.abs(_v.y) < 1.1;
    const sx = (_v.x + 1) / 2 * innerWidth, sy = (1 - _v.y) / 2 * innerHeight;
    if (on) { ui.coinFly(sx, sy, big); ui.floatText(sx, sy - 18, `+${value}`, big); } else ui.bumpPoints();
    if (preset.outlines) fx.emit(X[i], Y[i] + (big ? 0.9 : 0.55) + Hh[i], Z[i], big ? 18 : 9, i * 0.37);
    if (combo % 10 === 0) {                                  // ten in a row: a chime and a little bonus
      save.points += 5;
      setTimeout(() => Sound.combo(), 120);
      ui.floatText(innerWidth / 2, innerHeight * 0.32, `${S().combo} +5`, true);
    }
    onCollect?.(key);
  }

  function update(dt, now, { explore, player, show: showId = null, preset }) {
    build(explore ? 3 : 6);
    if (showId !== shown || (showId && shownVersion !== setsVersion)) show(showId);
    const px = player.pos.x, pz = player.pos.z, py = player.pos.y;
    const vd = refs.view.dist, R = 55 + vd * 1.6, RR = R * R, k = 1 + Math.max(0, vd - 10) / 25;
    let nc = 0, ns = 0;
    for (let i = 0; i < total; i++) {
      const st = ST[i]; if (st === 0 || st === GONE) continue;
      const dx = X[i] - px, dz = Z[i] - pz, d2 = dx * dx + dz * dz;
      if (st === IDLE && explore && d2 < PICK2 && Math.abs(Y[i] - py) < 2) collect(i, now, preset);
      if (d2 > RR) continue;
      const big = BIG[i] === 1;
      let y = Y[i] + (big ? 0.95 : 0.55) + Hh[i] + Math.sin(now * 2.4 + i) * (big ? 0.1 : 0.06), spin = now * (big ? 1.6 : 2.6) + i * 0.7, sc = k;
      if (ST[i] === POP) {
        const a = (now - T0[i]) / 0.4;
        if (a >= 1) { ST[i] = GONE; continue; }
        y += (1 - (1 - a) * (1 - a)) * 1.3; spin += a * a * 22; sc *= (1 + 0.6 * a) * (1 - a * a);
      }
      _q.setFromAxisAngle(_up, spin);
      _m.compose(_p.set(X[i], y, Z[i]), _q, _s.set(sc, sc, sc));
      if (big) starMesh.setMatrixAt(ns++, _m); else coinMesh.setMatrixAt(nc++, _m);
    }
    const ink = !!preset.outlines;
    coinMesh.count = coinInk.count = nc; starMesh.count = starInk.count = ns;
    coinMesh.visible = nc > 0; starMesh.visible = ns > 0; coinInk.visible = ink && nc > 0; starInk.visible = ink && ns > 0;
    if (nc) coinMesh.instanceMatrix.needsUpdate = true;
    if (ns) starMesh.instanceMatrix.needsUpdate = true;
    fx.update(dt, innerHeight / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2)));
    if (dirty && now - lastSave > 1) { dirty = false; lastSave = now; persist(); }
  }

  // balance check (console / tests): size of every set, its route, and that every coin can be
  // reached on foot from the route (A* from the coin back to the nearest route point)
  function balance({ verify = false } = {}) {
    const rows = [], check = verify ? createSearch(grid) : null;
    for (const [id, set] of sets) {
      const coords = set.route.map(([x, z]) => [x, z]).concat(set.extra.map(e => [X[slotOfId(e)], Z[slotOfId(e)]]));
      let off = 0, bad = 0, unreachable = 0;
      for (const [x, z] of coords) {
        let d = Infinity, nx = 0, nz = 0;
        for (const [px, pz] of set.path) { const q = Math.hypot(px - x, pz - z); if (q < d) { d = q; nx = px; nz = pz; } }
        off = Math.max(off, d);
        if (!grid.walkable(x, z)) bad++;
        if (check && d > 1.5) { check.start(x, z, nx, nz, 1.2); const c = check.step(1e9); if (!c?.reached) unreachable++; }
      }
      const N = set.keys.length;
      rows.push({ id, route_m: set.len, reached: set.reached, coins: N, routeCoins: set.route.length, clusterCoins: set.extra.filter(e => e < STAR_ID).length,
        stars: set.extra.filter(e => e >= STAR_ID).length, easy: Math.ceil(0.2 * N - 1e-9), medium: Math.ceil(0.5 * N - 1e-9), hard: Math.ceil(0.9 * N - 1e-9),
        maxOffRoute_m: +off.toFixed(1), notWalkable: bad, ...(verify ? { unreachable } : {}) });
    }
    return rows;
  }

  return { load, update, want, progress, nextCoin, balance, sets, get building() { return !!job || queue.length > 0; },
    get total() { return total; }, get collectedCount() { return collectedCount; },
    debug: () => ({ static: nStatic, stars: nStar, shown, slots: Array.from(ST.subarray(S0)).filter(s => s === IDLE).length, positions: { X, Z, ST, BIG, KEY } }) };
}
