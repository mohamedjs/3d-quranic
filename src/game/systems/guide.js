// Guided path to the next story. A walkability grid (1.5 m cells, filled lazily) feeds an A*
// search that runs a few milliseconds per frame; the route prefers roads and village lanes,
// crosses water only on bridges and steers round houses. It is drawn as a flowing line of soft
// golden chevrons on the ground (one instanced draw call), with a light beacon and a bobbing
// arrow over the storyteller, and handed to the minimap / world map as a dashed line.
import * as THREE from 'three';
import { HALF, groundAt, waterDist, pathDist, fieldPlot, FOOTBRIDGES, BRIDGE, riverZ, smooth } from '../terrain/heightfield.js';
import { INK } from '../shaders/toonPalette.js';
import { refs } from './refs.js';
import { noReflect } from './layers.js';

export const CELL = 1.5;
const EXT = HALF - 20, N = Math.floor((2 * EXT) / CELL), NN = N * N;
const cellX = g => -EXT + (g + 0.5) * CELL;
const gridOf = v => Math.max(0, Math.min(N - 1, Math.floor((v + EXT) / CELL)));
export const cellIndex = (x, z) => gridOf(z) * N + gridOf(x);
const STEP = 0.5;                      // resampled route spacing (m)

// ---- walkability grid ---------------------------------------------------------------------
export function createNavGrid(colliders) {
  const cost = new Float32Array(NN).fill(-1), hgt = new Float32Array(NN);
  const solid = new Uint8Array(NN), bridge = new Uint8Array(NN);
  const pad = 0.55;                    // child radius + a little: the route keeps off walls
  for (const c of colliders) {
    for (let gz = gridOf(c.z0 - pad); gz <= gridOf(c.z1 + pad); gz++) for (let gx = gridOf(c.x0 - pad); gx <= gridOf(c.x1 + pad); gx++) {
      const x = cellX(gx), z = cellX(gz);
      if (x > c.x0 - pad && x < c.x1 + pad && z > c.z0 - pad && z < c.z1 + pad) solid[gz * N + gx] = 1;
    }
  }
  // bridges: stamp a line of cells along each deck so the search can cross the water there
  for (const b of FOOTBRIDGES) {
    const ux = Math.cos(b.rot), uz = -Math.sin(b.rot);
    for (let t = -3.4; t <= 3.4; t += 0.3) bridge[cellIndex(b.x + ux * t, b.z + uz * t)] = 1;
  }
  for (let t = -BRIDGE.halfL - 1.5; t <= BRIDGE.halfL + 1.5; t += 0.5) bridge[cellIndex(BRIDGE.x, riverZ(BRIDGE.x) + t)] = 1;

  function evalCell(i) {
    const x = cellX(i % N), z = cellX((i / N) | 0), g = groundAt(x, z);
    hgt[i] = g;
    if (bridge[i]) return (cost[i] = 0.45);
    if (solid[i] || g > 15) return (cost[i] = Infinity);
    const wd = waterDist(x, z);
    if (g < -0.3 || wd < 0.35) return (cost[i] = Infinity);
    const pd = pathDist(x, z);
    let c = pd < 1.8 ? 0.35 : pd < 3.2 ? 0.55 : 1;
    if (c === 1 && Math.abs(x) < 5 && z > -60 && z < -8) c = 0.45;          // the village street
    else if (c === 1 && Math.hypot(x, z) < 36) c = 0.7;                      // village lanes and square
    else if (c === 1 && fieldPlot(x, z) >= 0) c = 1.35;                      // round the crops when a lane will do
    if (wd < 1.5) c += 0.8;                                                  // keep off the canal edge
    return (cost[i] = c);
  }
  const at = i => (cost[i] < 0 ? evalCell(i) : cost[i]);
  return {
    N, cost: at, height: i => (cost[i] < 0 && evalCell(i), hgt[i]),
    walkable: (x, z) => Math.abs(x) < EXT && Math.abs(z) < EXT && at(cellIndex(x, z)) < 5,
    costAt: (x, z) => at(cellIndex(x, z)),
  };
}

// ---- time-sliced A* ----------------------------------------------------------------------
const DX = [1, -1, 0, 0, 1, 1, -1, -1], DZ = [0, 0, 1, -1, 1, -1, 1, -1], DL = [1, 1, 1, 1, Math.SQRT2, Math.SQRT2, Math.SQRT2, Math.SQRT2];
function createSearch(grid) {
  const g = new Float32Array(NN), parent = new Int32Array(NN), seen = new Uint32Array(NN), closed = new Uint32Array(NN);
  const CAP = NN * 2, heapI = new Int32Array(CAP), heapF = new Float32Array(CAP);
  let size = 0, id = 0, goalX = 0, goalZ = 0, goalR2 = 0, best = -1, bestH = Infinity, expanded = 0, found = -1, startI = 0, active = false;
  const H = i => { const dx = cellX(i % N) - goalX, dz = cellX((i / N) | 0) - goalZ; return Math.sqrt(dx * dx + dz * dz); };
  function push(i, f) {
    if (size >= CAP) return;
    let k = size++;
    while (k > 0) { const p = (k - 1) >> 1; if (heapF[p] <= f) break; heapI[k] = heapI[p]; heapF[k] = heapF[p]; k = p; }
    heapI[k] = i; heapF[k] = f;
  }
  function pop() {
    const top = heapI[0], li = heapI[--size], lf = heapF[size];
    let k = 0;
    for (;;) {
      let c = 2 * k + 1; if (c >= size) break;
      if (c + 1 < size && heapF[c + 1] < heapF[c]) c++;
      if (heapF[c] >= lf) break;
      heapI[k] = heapI[c]; heapF[k] = heapF[c]; k = c;
    }
    heapI[k] = li; heapF[k] = lf;
    return top;
  }
  return {
    get active() { return active; },
    start(sx, sz, tx, tz, r) {
      id++; size = 0; goalX = tx; goalZ = tz; goalR2 = r * r; best = -1; bestH = Infinity; expanded = 0; found = -1; active = true;
      startI = cellIndex(sx, sz); seen[startI] = id; g[startI] = 0; parent[startI] = -1; grid.cost(startI);
      push(startI, H(startI) * 0.5);
    },
    cancel() { active = false; },
    // → null while running, else the list of cells (start … goal) or [] when nothing was found
    step(ms) {
      if (!active) return null;
      const t0 = performance.now();
      let n = 0;
      while (size > 0) {
        if ((++n & 63) === 0 && performance.now() - t0 > ms) return null;
        const i = pop();
        if (closed[i] === id) continue;
        closed[i] = id; expanded++;
        const x = i % N, z = (i / N) | 0, h = H(i);
        if (h < bestH) { bestH = h; best = i; }
        if (h * h < goalR2 && i !== startI || h < 0.8) { found = i; break; }
        if (expanded > 90000) break;
        const ci = grid.cost(i), hi = grid.height(i);
        for (let k = 0; k < 8; k++) {
          const nx = x + DX[k], nz = z + DZ[k];
          if (nx < 0 || nz < 0 || nx >= N || nz >= N) continue;
          const j = nz * N + nx;
          if (closed[j] === id) continue;
          const cj = grid.cost(j);
          if (cj === Infinity) continue;
          if (k >= 4 && (grid.cost(z * N + nx) === Infinity || grid.cost(nz * N + x) === Infinity)) continue;   // no corner cutting
          const ng = g[i] + DL[k] * CELL * ((ci === Infinity ? 1 : ci) + cj) * 0.5 + Math.abs(grid.height(j) - hi) * 1.5;
          if (seen[j] === id && ng >= g[j]) continue;
          seen[j] = id; g[j] = ng; parent[j] = i;
          push(j, ng + H(j) * 0.5);
        }
      }
      active = false;
      let end = found >= 0 ? found : best;
      if (end < 0) return [];
      const cells = [];
      for (let i = end; i !== -1 && cells.length < NN; i = parent[i]) cells.push(i);
      cells.reverse();
      cells.reached = found >= 0;
      return cells;
    },
  };
}

// cells → smooth polyline: string-pull (only across cells no costlier than the ends, so the
// route stays on the street instead of cutting over fields), two rounds of Chaikin, then
// resampled every 0.5 m with ground heights
function buildRoute(grid, cells, sx, sz) {
  const P = cells.map(i => [cellX(i % N), cellX((i / N) | 0)]);
  P[0] = [sx, sz];
  const los = (a, b) => {
    const limit = Math.max(grid.costAt(a[0], a[1]), grid.costAt(b[0], b[1])) + 0.05;
    const d = Math.hypot(b[0] - a[0], b[1] - a[1]), n = Math.ceil(d / 0.5);
    for (let k = 1; k < n; k++) { const c = grid.costAt(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n); if (!(c <= limit)) return false; }
    return true;
  };
  let pts = [P[0]];
  for (let i = 0; i < P.length - 1;) {
    let j = Math.min(P.length - 1, i + 30);
    while (j > i + 1 && !los(P[i], P[j])) j--;
    pts.push(P[j]); i = j;
  }
  for (let it = 0; it < 2; it++) {
    const o = [pts[0]];
    for (let i = 0; i < pts.length - 1; i++) {
      const [ax, az] = pts[i], [bx, bz] = pts[i + 1];
      o.push([ax * 0.75 + bx * 0.25, az * 0.75 + bz * 0.25], [ax * 0.25 + bx * 0.75, az * 0.25 + bz * 0.75]);
    }
    o.push(pts[pts.length - 1]); pts = o;
  }
  let len = 0; for (let i = 1; i < pts.length; i++) len += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
  const n = Math.max(2, Math.floor(len / STEP) + 1), x = new Float32Array(n), z = new Float32Array(n), y = new Float32Array(n);
  let seg = 0, acc = 0;
  for (let k = 0; k < n; k++) {
    const s = Math.min(k * STEP, len);
    while (seg < pts.length - 2) {
      const l = Math.hypot(pts[seg + 1][0] - pts[seg][0], pts[seg + 1][1] - pts[seg][1]);
      if (acc + l >= s) break;
      acc += l; seg++;
    }
    const [ax, az] = pts[seg], [bx, bz] = pts[Math.min(seg + 1, pts.length - 1)], l = Math.hypot(bx - ax, bz - az) || 1, t = Math.min(1, (s - acc) / l);
    x[k] = ax + (bx - ax) * t; z[k] = az + (bz - az) * t; y[k] = groundAt(x[k], z[k]);
  }
  return { x, z, y, n, len: (n - 1) * STEP };
}

// ---- visuals -----------------------------------------------------------------------------
const TRAIL_MAX = 110;
function trailMesh() {
  const geo = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
  const fade = new THREE.InstancedBufferAttribute(new Float32Array(TRAIL_MAX), 1); fade.setUsage(THREE.DynamicDrawUsage);
  geo.setAttribute('aFade', fade);
  const mat = new THREE.ShaderMaterial({
    uniforms: { uCore: { value: new THREE.Color(0xfff1a8) }, uGlow: { value: new THREE.Color(0xffc21f) }, uInk: { value: new THREE.Color(0x6e3a06) } },
    vertexShader: /* glsl */`
      attribute float aFade; varying vec2 vUv; varying float vFade;
      void main() { vUv = uv * 2. - 1.; vFade = aFade; gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(position, 1.); }`,
    fragmentShader: /* glsl */`
      uniform vec3 uCore, uGlow, uInk; varying vec2 vUv; varying float vFade;
      float seg(vec2 p, vec2 a, vec2 b) { vec2 pa = p - a, ba = b - a; return length(pa - ba * clamp(dot(pa, ba) / dot(ba, ba), 0., 1.)); }
      void main() {
        vec2 p = vUv;
        float d = min(seg(p, vec2(-.6, -.28), vec2(0., .32)), seg(p, vec2(.6, -.28), vec2(0., .32)));
        // a bold toon chevron: gold body with a light centre stripe and an ink rim, soft glow round it
        float body = 1. - smoothstep(.15, .18, d), rim = 1. - smoothstep(.22, .25, d), stripe = 1. - smoothstep(.04, .07, d);
        float glow = exp(-d * d * 10.) * .45 * (1. - smoothstep(.5, 1., length(p)));
        vec3 col = mix(uGlow, uInk, clamp(rim - body, 0., 1.));
        col = mix(col, uCore, stripe * .9);
        float a = max(rim, glow) * vFade;
        if (a < .01) discard;
        gl_FragColor = vec4(col, a);
        #include <colorspace_fragment>
      }`,
    transparent: true, depthWrite: false, side: THREE.DoubleSide, toneMapped: false, fog: false,
    polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2,
  });
  const m = new THREE.InstancedMesh(geo, mat, TRAIL_MAX);
  m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  m.frustumCulled = false; m.count = 0; m.renderOrder = 2; m.name = 'guide-trail';
  return noReflect(m);
}
function beacon() {
  const group = new THREE.Group(); group.name = 'guide-beacon';
  const pillar = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 1, 20, 1, true).translate(0, 0.5, 0), new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 }, uColor: { value: new THREE.Color(0xffc53d) } },
    vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }',
    fragmentShader: /* glsl */`uniform float uTime; uniform vec3 uColor; varying vec2 vUv;
      void main() {
        float a = pow(1. - vUv.y, 1.4) * smoothstep(0., .04, vUv.y) * (.75 + .25 * sin(vUv.y * 26. - uTime * 3.));
        gl_FragColor = vec4(mix(uColor, vec3(1., .97, .85), .3 * (1. - vUv.y)), a * .7);
        #include <colorspace_fragment>
      }`,
    transparent: true, depthWrite: false, side: THREE.DoubleSide, toneMapped: false, fog: false,
  }));
  pillar.frustumCulled = false; pillar.renderOrder = 3;
  const cone = new THREE.ConeGeometry(0.34, 0.62, 12).rotateX(Math.PI);
  const arrow = new THREE.Mesh(cone, new THREE.MeshBasicMaterial({ color: 0xffc94a, toneMapped: false, fog: false }));
  const ink = new THREE.Mesh(cone, new THREE.MeshBasicMaterial({ color: INK, side: THREE.BackSide, toneMapped: false, fog: false }));
  ink.scale.setScalar(1.22); arrow.add(ink);
  // a pulsing gold ring on the ground round the storyteller
  const ring = new THREE.Mesh(new THREE.RingGeometry(0.82, 1, 40).rotateX(-Math.PI / 2), new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 } },
    vertexShader: 'varying vec2 vP; void main() { vP = position.xz; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }',
    fragmentShader: /* glsl */`uniform float uTime; varying vec2 vP;
      void main() { float r = length(vP);
        float band = 1. - smoothstep(.0, .05, abs(r - .91) - .035), inkr = 1. - smoothstep(.0, .03, abs(r - .91) - .08);
        vec3 col = mix(vec3(.43, .23, .02), vec3(1., .8, .2), band);
        gl_FragColor = vec4(col, max(band, inkr * .8));
        #include <colorspace_fragment>
      }`,
    transparent: true, depthWrite: false, toneMapped: false, fog: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2,
  }));
  ring.frustumCulled = false; ring.renderOrder = 2;
  group.add(pillar, arrow, ring);
  group.traverse(o => noReflect(o));
  group.visible = false;
  return { group, pillar, arrow, ink, ring };
}

// ---- the guide -------------------------------------------------------------------------------
export function createGuide({ scene, colliders }) {
  const grid = createNavGrid(colliders), search = createSearch(grid);
  const trail = trailMesh(), bc = beacon();
  scene.add(trail, bc.group);
  const fade = trail.geometry.attributes.aFade;
  const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _p = new THREE.Vector3(), _s = new THREE.Vector3(), _up = new THREE.Vector3(0, 1, 0);

  let route = null, routeTarget = null, pendingTarget = null, pendingFrom = [0, 0], lastReq = -9, prog = 0, stray = 0, version = 0;
  const api = {
    grid, get route() { return route; }, get progress() { return prog; }, get version() { return version; }, get target() { return routeTarget; },
    get searching() { return search.active; },
    // route for the minimap / world map (null when hidden)
    mapRoute: null,
  };

  function request(target, px, pz, now) {
    const r = (target.enc.stage?.talkRadius ?? 3.4) * 0.8;
    search.start(px, pz, target.x, target.z, r);
    pendingTarget = target; pendingFrom = [px, pz]; lastReq = now;
  }
  function track(px, pz) {
    if (!route) return;
    let best = prog, bd = Infinity;
    for (let i = Math.max(0, prog - 30), e = Math.min(route.n - 1, prog + 140); i <= e; i++) {
      const dx = route.x[i] - px, dz = route.z[i] - pz, d = dx * dx + dz * dz;
      if (d < bd) { bd = d; best = i; }
    }
    prog = best; stray = Math.sqrt(bd);
  }

  // show: the path setting and the mode allow drawing · target: the npc the objective points at
  api.update = (dt, now, { explore, show, target, player, outlines = true }) => {
    const px = player.pos.x, pz = player.pos.z;
    if (explore) {
      if (!target) { if (route || search.active) { route = null; routeTarget = null; search.cancel(); version++; } }
      else if (target !== routeTarget && target !== pendingTarget) request(target, px, pz, now);
      else if (!search.active && now - lastReq > 1.5 && (!route || stray > 6)) request(target, px, pz, now);
      if (search.active) {
        const cells = search.step(3);
        if (cells) {
          const t = pendingTarget; pendingTarget = null;
          if (cells.length > 1) { route = buildRoute(grid, cells, pendingFrom[0], pendingFrom[1]); route.reached = cells.reached; routeTarget = t; prog = 0; stray = 0; version++; }
          else if (t !== routeTarget) { route = null; routeTarget = t; version++; }
        }
      }
      track(px, pz);
    }
    const visible = explore && show && !!route && !!target;
    api.mapRoute = visible ? route : null;
    trail.visible = visible; bc.group.visible = explore && show && !!target;
    if (bc.group.visible) {
      const k = Math.max(1, refs.view.dist / 9), host = target.host, r = target.rig.root.position;
      bc.pillar.position.set(r.x, groundAt(r.x, r.z), r.z); bc.pillar.scale.set(0.8 * k, 6 * k, 0.8 * k);
      bc.pillar.material.uniforms.uTime.value = now;
      bc.arrow.position.set(r.x, host.headY + 1.3 * k + Math.sin(now * 3) * 0.12 * k, r.z);
      bc.arrow.scale.setScalar(k); bc.arrow.rotation.y = now * 1.5;
      const rr = (target.enc.stage?.talkRadius ?? 3.4) * 0.75;
      bc.ring.position.set(target.x, groundAt(target.x, target.z) + 0.12, target.z); bc.ring.scale.setScalar(rr * (0.92 + 0.08 * Math.sin(now * 3)));
      bc.ink.visible = outlines;
    }
    if (!visible) return;
    // chevrons anchored to the route, flowing forward; bigger and sparser as the camera rises
    const k = THREE.MathUtils.clamp(refs.view.dist / 5.2, 1, 7), size = 0.8 * k, spacing = 1.25 * k;
    const s0 = prog * STEP, range = 38 + refs.view.dist * 2.2, end = Math.min(route.len - 1.2, s0 + range);
    const phase = (now * 1.3 * Math.min(k, 3)) % spacing;
    let s = Math.ceil((s0 + 0.6 - phase) / spacing) * spacing + phase, count = 0;
    const lift = 0.09 + 0.05 * k;
    while (s < end && count < TRAIL_MAX) {
      const f = s / STEP, i = Math.min(route.n - 2, Math.floor(f)), t = f - i;
      const x = route.x[i] + (route.x[i + 1] - route.x[i]) * t, z = route.z[i] + (route.z[i + 1] - route.z[i]) * t, y = route.y[i] + (route.y[i + 1] - route.y[i]) * t;
      const a = Math.max(0, i - 2), b = Math.min(route.n - 1, i + 3), tx = route.x[b] - route.x[a], tz = route.z[b] - route.z[a];
      const ds = s - s0;
      const fa = smooth(0.4, 1.8 * Math.min(k, 2), ds) * (1 - smooth(range * 0.7, range, ds)) * (1 - smooth(route.len - 4, route.len - 1.2, s));
      _q.setFromAxisAngle(_up, Math.atan2(-tx, -tz));
      _m.compose(_p.set(x, y + lift, z), _q, _s.set(size, 1, size * 1.25));   // stretched along the way: reads at grazing angles
      trail.setMatrixAt(count, _m); fade.array[count] = fa;
      count++; s += spacing;
    }
    trail.count = count; trail.instanceMatrix.needsUpdate = true; fade.needsUpdate = true;
  };
  return api;
}
