// Canvas + adaptive quality. WebGL2 renderer (see README for why not WebGPU yet).
import { Suspense, Component, useEffect, useRef } from 'react';
import { Canvas, useThree, useFrame } from '@react-three/fiber';
import { PerformanceMonitor } from '@react-three/drei';
import * as THREE from 'three';
import { World } from '../world/World.jsx';
import { useGame, usePreset, rememberLite } from '../systems/store.js';
import { LEVELS, PRESETS, isMobile, liteDpr } from '../systems/quality.js';
import { reportCrash } from '../../telemetry.js';

function step(dir, fps = 0) {
  const { qualitySetting, quality, setQuality, mode } = useGame.getState();
  if (qualitySetting !== 'auto') return false;         // the player chose a level: respect it
  if (mode !== 'explore') return false;                // loading/cinematics aren't representative frames
  const i = LEVELS.indexOf(quality) + dir;
  if (i < 0 || i >= LEVELS.length) return false;
  if (LEVELS[i] === 'lite') {                          // Low → Lite only when it's really struggling
    if (fps >= 28) return false;
    useGame.getState().dropToLite(); rememberLite(true); return true;
  }
  if (quality === 'lite' && dir > 0) return false;     // Lite is sticky: its 30 fps cap would always read as 'fast enough'
  setQuality(LEVELS[i]); return true;
}

// Any load/build failure is written, verbatim, on the loading screen — never a silent spinner.
export function showError(msg) {
  const l = document.getElementById('loading'); if (!l) return;
  l.hidden = false; l.classList.remove('gone');
  l.querySelector('.spin').hidden = true;
  l.querySelector('p').textContent = 'Something went wrong while loading — تعذّر تحميل اللعبة:\n' + msg;
  l.querySelector('p').style.whiteSpace = 'pre-line';
}
class Boundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(e) { console.error(e); reportCrash(e, 'react'); showError(e?.message || String(e)); }
  render() { return this.state.failed ? null : this.props.children; }
}
addEventListener('error', e => { if (document.getElementById('loading')?.hidden === false) showError(e.message); });
addEventListener('unhandledrejection', e => { if (document.getElementById('loading')?.hidden === false) showError(e.reason?.message || String(e.reason)); });

// Resolution: the preset's scale, capped by the screen (and at 1.5 on phones, whose 3x
// screens would otherwise render 9x the pixels), times the adaptive factor the monitor sets.
const DPR_CAP = isMobile() ? 1.5 : 2;
function useDpr() {
  const preset = usePreset(), k = useGame(s => s.dprScale);
  const want = preset.lite ? liteDpr() : preset.dpr;   // Lite: never above 1, 0.75 on tiny GPUs
  return Math.max(0.5, Math.min(window.devicePixelRatio || 1, want, DPR_CAP) * k);
}

// Menus and hidden tabs don't need 60 fps: while a panel covers the world the scene is only
// redrawn ~12 times a second, and not at all in a background tab.
// LITE caps the frame rate (preset.fps, 30): the scene renders on every other refresh of a
// 60 Hz screen, which halves GPU + CPU work and keeps the phone cool; under the Quran overlay
// (which covers the world) it drops to ~8 fps.
function FrameGovernor() {
  const setFrameloop = useThree(s => s.setFrameloop), invalidate = useThree(s => s.invalidate);
  const mode = useGame(s => s.mode), fps = usePreset().fps;
  useEffect(() => {
    let timer = 0, raf = 0;
    const capped = hz => {
      setFrameloop('demand');
      let last = 0; const gap = 1000 / hz - 3;          // a little slack: a 60 Hz rAF lands every 16.7 ms
      const loop = t => { raf = requestAnimationFrame(loop); if (t - last >= gap) { last = t; invalidate(); } };
      raf = requestAnimationFrame(loop);
    };
    const apply = () => {
      clearInterval(timer); cancelAnimationFrame(raf);
      if (document.hidden) { setFrameloop('never'); return; }
      if (mode === 'panel') { setFrameloop('demand'); timer = setInterval(invalidate, fps ? 125 : 80); return; }
      if (fps && mode === 'quran') { capped(8); return; }
      if (fps) { capped(fps); return; }
      setFrameloop('always');
    };
    apply();
    document.addEventListener('visibilitychange', apply);
    return () => { clearInterval(timer); cancelAnimationFrame(raf); document.removeEventListener('visibilitychange', apply); };
  }, [mode, fps, setFrameloop, invalidate]);
  return null;
}

// AUTO: measure the first seconds on the title / first steps; a device that can't reach
// 25 fps there switches to LITE's per-frame settings now (no rebuild) and is remembered, so the
// next visit builds the light world from the start.
function EarlyProbe() {
  const s = useRef({ t: 0, n: 0, done: false });
  useFrame((_, dt) => {
    const p = s.current; if (p.done) return;
    const { mode, qualitySetting, quality } = useGame.getState();
    if (qualitySetting !== 'auto' || quality === 'lite') { p.done = true; return; }
    if (mode !== 'title' && mode !== 'explore') { p.t = 0; p.n = 0; return; }
    p.t += Math.min(dt, 0.5); p.n++;
    if (p.t < 1.5) { p.n = 0; p.t0 = p.t; return; }            // skip shader compiles / first uploads
    if (p.t - p.t0 >= 3) {
      p.done = true;
      const fps = p.n / (p.t - p.t0);
      if (fps < 25) { console.info(`[quality] ${fps.toFixed(1)} fps in the first seconds → Lite`); useGame.getState().dropToLite(); rememberLite(true); }
    }
  });
  return null;
}

// PerformanceMonitor: `factor` (0..1) trims the resolution first (down to 70 %); only when that
// isn't enough does AUTO step the quality level (see step()).
function onChange({ factor }) {
  const { qualitySetting, mode } = useGame.getState();
  if (qualitySetting !== 'auto' || mode !== 'explore') return;
  useGame.getState().setDprScale(Math.round((0.7 + 0.3 * factor) * 20) / 20);
}

export function Game() {
  const dpr = useDpr();
  return (
    <Canvas
      shadows="percentage"
      dpr={dpr}
      gl={{ antialias: false, powerPreference: 'high-performance', stencil: false }}
      camera={{ fov: 50, near: 0.1, far: 1600, position: [0, 3, -64] }}
      onCreated={({ gl }) => { gl.toneMapping = THREE.NoToneMapping; }}
      fallback={<p className="nogl">This game needs WebGL 2 (3D graphics). Try Chrome, Edge, Firefox or Safari with hardware acceleration on. — تحتاج اللعبة إلى WebGL.</p>}
    >
      {/* resolution first; at the bottom of the range drop a level (and start it at full res),
          at the top climb one (starting it at reduced res) */}
      <PerformanceMonitor bounds={() => (PRESETS[useGame.getState().quality].fps ? [22, 28] : [45, 58])} flipflops={14} factor={1} step={0.2} onChange={onChange}
        onDecline={api => { api.top = false; if (api.factor > 0.001) api.bottom = false; else if (!api.bottom) api.bottom = true; else if (step(-1, api.fps)) { api.factor = 1; api.bottom = false; } }}
        onIncline={api => { api.bottom = false; if (api.factor < 0.999) api.top = false; else if (!api.top) api.top = true; else if (step(1)) { api.factor = 0.4; api.top = false; } }}
        onFallback={() => { if (useGame.getState().qualitySetting === 'auto') useGame.getState().setDprScale(0.8); }} />
      <FrameGovernor />
      <EarlyProbe />
      <Boundary>
        <Suspense fallback={null}>
          <World />
        </Suspense>
      </Boundary>
    </Canvas>
  );
}
