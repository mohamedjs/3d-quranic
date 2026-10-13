// Frame-rate statistics for the play-time report (telemetry "time" rows) and an on-screen
// overlay for testing on a phone: open the game with ?perf in the URL.
// Collected only while the page is visible; cheap (a few numbers per frame).
const MAX = 1200;                      // recent frame times kept for percentiles (~40 s at 30 fps)
const S = { frames: 0, time: 0, slow: 0, worst: 0, recent: [], calls: 0, tris: 0, tex: 0, geo: 0 };
let overlay = null, olT = 0;
export const perfOn = typeof location !== 'undefined' && /[?&]perf\b/.test(location.search);

export function perfFrame(dt, gl) {
  if (!(dt > 0) || dt > 2 || document.visibilityState !== 'visible') return;   // skip resume gaps
  S.frames++; S.time += dt; if (dt > 0.05) S.slow++; if (dt > S.worst) S.worst = dt;
  S.recent.push(dt); if (S.recent.length > MAX) S.recent.shift();
  if (gl && (S.frames & 15) === 0) { const r = gl.info.render, m = gl.info.memory; S.calls = r.calls; S.tris = r.triangles; S.tex = m.textures; S.geo = m.geometries; }
  if (perfOn && (olT += dt) > 0.5) { olT = 0; drawOverlay(gl); }
}
function pct(p) { if (!S.recent.length) return 0; const a = [...S.recent].sort((x, y) => x - y); return a[Math.min(a.length - 1, Math.floor(a.length * p))]; }
// summary sent with telemetry (and reset so every report covers its own stretch of play)
export function perfSummary(reset = true) {
  if (S.frames < 30) return null;
  const out = { fps: +(S.frames / S.time).toFixed(1), p95ms: Math.round(pct(0.95) * 1000), worstms: Math.round(S.worst * 1000),
    slowPct: +(100 * S.slow / S.frames).toFixed(1), calls: S.calls, tris: S.tris, tex: S.tex, geo: S.geo,
    dpr: +(window.__game?.dpr ?? devicePixelRatio).toFixed?.(2) };
  if (reset) Object.assign(S, { frames: 0, time: 0, slow: 0, worst: 0, recent: [] });
  return out;
}
function drawOverlay(gl) {
  if (!overlay) { overlay = document.createElement('div'); overlay.style.cssText = 'position:fixed;left:6px;top:6px;z-index:99999;font:12px/1.35 ui-monospace,monospace;color:#0f0;background:rgba(0,0,0,.7);padding:6px 8px;border-radius:6px;pointer-events:none;white-space:pre;direction:ltr'; document.body.appendChild(overlay); }
  const fps = S.recent.length ? (S.recent.slice(-30).length / S.recent.slice(-30).reduce((a, b) => a + b, 0)) : 0;
  overlay.textContent = `fps ${fps.toFixed(0)}  p95 ${Math.round(pct(0.95) * 1000)}ms  slow ${(100 * S.slow / Math.max(1, S.frames)).toFixed(0)}%\ncalls ${S.calls}  tris ${(S.tris / 1000).toFixed(0)}k  tex ${S.tex}  geo ${S.geo}\nq ${window.__game?.store?.getState?.().quality ?? '?'}  dpr ${gl ? gl.getPixelRatio().toFixed(2) : '?'}`;
}
