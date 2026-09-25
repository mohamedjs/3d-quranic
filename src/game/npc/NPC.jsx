// <NPC encounter/>: a storyteller from encounters.json — rig (procedural or GLB), floating
// marker, optional camel. Idle breathing/gestures run here; proximity, greeting and the
// talk trigger live in the game system, which reads refs.npcs.
import { useMemo, useState, useLayoutEffect, useEffect } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { makeElder, makeCamel } from '../characters/procedural.js';
import { loadGlbRig } from '../characters/glbRig.js';
import { groundAt } from '../terrain/heightfield.js';
import { refs } from '../systems/refs.js';
import { useGame } from '../systems/store.js';
import { PRESETS } from '../systems/quality.js';

function markerTexture(glyph, bg) {
  const c = document.createElement('canvas'); c.width = c.height = 128; const x = c.getContext('2d');
  const g = x.createRadialGradient(64, 64, 10, 64, 64, 64); g.addColorStop(0, 'rgba(255,220,120,.85)'); g.addColorStop(1, 'rgba(255,200,80,0)');
  x.fillStyle = g; x.fillRect(0, 0, 128, 128);
  x.fillStyle = bg; x.strokeStyle = '#4a3210'; x.lineWidth = 5; x.beginPath(); x.arc(64, 64, 32, 0, 7); x.fill(); x.stroke();
  x.fillStyle = '#3a2408'; x.font = 'bold 46px Nunito, sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(glyph, 64, 66);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
const _m = new THREE.Matrix4(), _fr = new THREE.Frustum(), _s = new THREE.Sphere();
let MARK;
export const markers = () => (MARK ??= { open: markerTexture('!', '#ffcc4d'), done: markerTexture('✓', '#f3ecd8') });

// Places one cast member. `position` is where the character's root goes; for pose 'sit' it is
// the point on the bench under the pelvis and `seat` is the bench-top height above ground.
//  · GLB with a sit clip: root on the ground there (+ yOffset); the clip lowers the hips onto
//    the bench (author the sit clip in place, origin under the pelvis, feet on the floor).
//  · GLB without a sit clip: she stands just in front of the bench instead (idle / talk).
//  · procedural fallback: the robe is sunk into the bench so only the seated upper body shows.
function placeMember(m, rig, kind) {
  const d = m.def, [x, z] = d.position, h = d.look?.height ?? 1.72, seat = d.seat ?? 0.45, g = groundAt(x, z);
  let px = x, pz = z, y = g + (d.yOffset ?? 0);
  m.sitting = false;
  if (d.pose === 'sit') {
    if (kind === 'glb' && rig.canSit) { rig.setPose('sit'); m.sitting = true; }
    else if (kind === 'procedural') { m.sitting = true; y = g + seat + 0.45 * h - 1.55 * (h / 1.72) + (d.yOffset ?? 0); }
    else { const off = d.standOff ?? 0.6; px += Math.sin(d.facing) * off; pz += Math.cos(d.facing) * off; y = groundAt(px, pz); }
  }
  rig.root.position.set(px, y, pz); rig.root.rotation.y = d.facing;
  m.rig = rig; m.pos = rig.root.position;
  m.headY = m.sitting ? g + seat + 0.52 * h : y + rig.headY;        // world height of the top of the head
  m.turns = !m.sitting;                                            // seated people don't swivel on the bench
}

export function NPC({ encounter }) {
  const [, setVersion] = useState(0);
  const npc = useMemo(() => {
    const members = encounter.characters.map(def => {
      const m = { id: def.id, def };
      placeMember(m, makeElder(def.look), 'procedural');
      return m;
    });
    const host = members.find(m => m.id === encounter.host) ?? members[0];
    const marker = new THREE.Sprite(new THREE.SpriteMaterial({ map: markers().open, depthWrite: false, fog: false, toneMapped: false }));
    marker.scale.setScalar(0.6); marker.visible = false;
    const camels = members.filter(m => m.def.camel).map(m => {
      const [cx, cz] = m.def.camel, camel = makeCamel(); camel.position.set(cx, groundAt(cx, cz), cz); camel.rotation.y = m.def.facing + 1.3;
      camel.traverse(o => { if (o.isMesh && !o.userData.outline) { o.castShadow = true; o.receiveShadow = true; } });
      return camel;
    });
    const [x, z] = host.def.position;
    // `rig` / `baseYaw` / `x`,`z` refer to the host (marker, greeting, map pin)
    return { enc: encounter, members, host, get rig() { return host.rig; }, marker, camels, x, z, baseYaw: host.def.facing, state: 'locked', greeted: 0 };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useLayoutEffect(() => { refs.npcs.push(npc); return () => { refs.npcs = refs.npcs.filter(n => n !== npc); }; }, [npc]);
  useEffect(() => {
    for (const m of npc.members) {
      if (!m.def.model) continue;
      loadGlbRig(m.def.model, m.def.look?.height ?? 1.72).then(g => {
        if (!g) return;
        const yaw = m.rig.root.rotation.y;
        placeMember(m, g, 'glb'); if (m.turns) g.root.rotation.y = yaw;
        setVersion(v => v + 1);
      }).catch(e => console.error(m.def.model, e));
    }
  }, [npc]);

  // Skinned characters skip three's frustum culling (their bounds move with the pose), so
  // each cast member is culled here against a generous sphere round the body (its shadow can
  // reach into view), hidden and not animated at all beyond npcDist, and loses its ink hull
  // at a distance where it would be a pixel wide. Its "!" marker stays, and grows as the
  // camera zooms out so stories can be found from the bird's-eye view.
  useFrame(({ camera }, dt) => {
    const t = refs.clock.wind, r = npc.host.rig.root, preset = PRESETS[useGame.getState().quality];
    _m.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse); _fr.setFromProjectionMatrix(_m);
    let anyShown = false;
    for (const m of npc.members) {
      const root = m.rig.root, d = camera.position.distanceTo(root.position);
      _s.center.set(root.position.x, root.position.y + 1, root.position.z); _s.radius = 3.5;
      const show = d < preset.npcDist + refs.view.dist && _fr.intersectsSphere(_s);   // zoomed out: still shown round the child
      root.visible = show; anyShown ||= show;
      if (show) m.rig.animate(Math.min(dt, 0.05) * refs.clock.scale, t, 0);
      if (m.rig.hulls) { const ink = preset.outlines && d < Math.max(28, preset.outlineDist * 1.6); for (const h of m.rig.hulls) h.visible = ink; }
    }
    const k = Math.max(1, refs.view.dist / 9);
    npc.marker.scale.setScalar(0.6 * k);
    npc.marker.position.set(r.position.x, npc.host.headY + 0.6 * k + Math.sin(t * 2 + npc.x) * 0.06 * k, r.position.z);
    for (const c of npc.camels) { c.visible = anyShown; if (anyShown) c.userData.animate(t); }
  });
  return (
    <>
      {npc.members.map(m => <primitive key={m.id + (m.rig.canSit !== undefined ? ':glb' : '')} object={m.rig.root} />)}
      <primitive object={npc.marker} />
      {npc.camels.map((c, i) => <primitive key={'camel' + i} object={c} />)}
    </>
  );
}
