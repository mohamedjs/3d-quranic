// "Walk to the story" autopilot: the child walks along the guide's golden route (the same
// polyline the chevrons, coins and minimap use) toward the next storyteller, at walking pace,
// steering through the controller's `target` so collisions, terrain and coin pickups work as
// usual. Stops a couple of metres short so the "Talk" prompt appears (the dialogue is never
// started for the child). Any manual input cancels it (PlayerController.interrupt → stop).
import * as THREE from 'three';

const AHEAD = 5;            // route samples (0.5 m each) to aim ahead of the child: smooth corners
const STUCK_S = 2;          // no progress for this long → nudge onward; twice more → give up

export function createAutowalk({ player, guide, onChange }) {
  const aim = new THREE.Vector3();
  let active = false, best = Infinity, stuckT = 0, nudges = 0, nudgeT = 0, lostT = 0, version = -1;

  function stop(why = 'manual') {
    if (!active) return;
    active = false;
    if (player.target === aim) player.target = null;
    onChange?.(false, why);
  }
  function start() {
    if (active || !player.enabled || !guide.route || !guide.target) return false;
    player.interrupt();                     // drop a tap-to-walk target (onManual is a no-op while inactive)
    active = true; best = Infinity; stuckT = 0; nudges = 0; nudgeT = 0; lostT = 0; version = guide.version;
    onChange?.(true);
    return true;
  }

  function update(dt, { explore }) {
    if (!active) return;
    if (!explore || !player.enabled) return stop('mode');
    const npc = guide.target, route = guide.route;
    if (!npc) return stop('none');
    const r = npc.rig.root.position, px = player.pos.x, pz = player.pos.z;
    const d = Math.hypot(r.x - px, r.z - pz), talkR = npc.enc.stage?.talkRadius ?? 3.4;
    if (d < Math.min(2.2, talkR - 0.6)) return stop('arrived');
    // the route is being rebuilt (target changed): wait for it, don't wander off
    if (!route) { player.target = null; if ((lostT += dt) > 5) stop('lost'); return; }
    lostT = 0;
    if (guide.version !== version) { version = guide.version; best = Infinity; stuckT = 0; }   // re-routed: start measuring again
    const end = route.n - 1, prog = guide.progress, left = (end - prog) * 0.5;
    if (prog >= end - 1 && Math.hypot(route.x[end] - px, route.z[end] - pz) < 0.7) return stop(d < talkR ? 'arrived' : 'end');
    if (left < best - 0.25) { best = left; stuckT = 0; nudges = nudgeT > 0 ? nudges : 0; }
    else if ((stuckT += dt) > STUCK_S) {
      if (++nudges > 2) return stop('stuck');
      stuckT = 0; nudgeT = 1.4;                 // aim further along the route for a moment to slip round the snag
    }
    nudgeT = Math.max(0, nudgeT - dt);
    const i = Math.min(end, prog + AHEAD + (nudgeT > 0 ? 6 * nudges : 0));
    player.target = aim.set(route.x[i], route.y[i], route.z[i]);
    // the camera drifts gently round behind the child while nobody is steering it
    const steering = [...(player.pointers?.values() ?? [])].some(p => p.role === 'look') || player.lookVel.yaw;
    if (!steering && player.speed > 0.6) {
      let dy = player.facing + Math.PI - player.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy));
      player.yaw += dy * (1 - Math.exp(-dt * 0.7));
    }
  }
  return { start, stop, update, toggle: () => (active ? (stop('manual'), false) : start()), get active() { return active; } };
}
