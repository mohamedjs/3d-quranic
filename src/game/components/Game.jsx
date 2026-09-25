// Canvas + adaptive quality. WebGL2 renderer (see README for why not WebGPU yet).
import { Suspense, Component, useEffect } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { PerformanceMonitor } from '@react-three/drei';
import * as THREE from 'three';
import { World } from '../world/World.jsx';
import { useGame, usePreset } from '../systems/store.js';
import { LEVELS, isMobile } from '../systems/quality.js';

function step(dir) {
  const { qualitySetting, quality, setQuality, mode } = useGame.getState();
  if (qualitySetting !== 'auto') return false;         // the player chose a level: respect it
  if (mode !== 'explore') return false;                // loading/cinematics aren't representative frames
  const i = LEVELS.indexOf(quality) + dir;
  if (i >= 0 && i < LEVELS.length) { setQuality(LEVELS[i]); return true; }
  return false;
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
  componentDidCatch(e) { console.error(e); showError(e?.message || String(e)); }
  render() { return this.state.failed ? null : this.props.children; }
}
addEventListener('error', e => { if (document.getElementById('loading')?.hidden === false) showError(e.message); });
addEventListener('unhandledrejection', e => { if (document.getElementById('loading')?.hidden === false) showError(e.reason?.message || String(e.reason)); });

// Resolution: the preset's scale, capped by the screen (and at 1.5 on phones, whose 3x
// screens would otherwise render 9x the pixels), times the adaptive factor the monitor sets.
const DPR_CAP = isMobile() ? 1.5 : 2;
function useDpr() {
  const preset = usePreset(), k = useGame(s => s.dprScale);
  return Math.max(0.5, Math.min(window.devicePixelRatio || 1, preset.dpr, DPR_CAP) * k);
}

// Menus and hidden tabs don't need 60 fps: while a panel covers the world the scene is only
// redrawn ~12 times a second, and not at all in a background tab.
function FrameGovernor() {
  const setFrameloop = useThree(s => s.setFrameloop), invalidate = useThree(s => s.invalidate);
  const mode = useGame(s => s.mode);
  useEffect(() => {
    let timer = 0;
    const apply = () => {
      clearInterval(timer);
      if (document.hidden) { setFrameloop('never'); return; }
      if (mode === 'panel') { setFrameloop('demand'); timer = setInterval(invalidate, 80); return; }
      setFrameloop('always');
    };
    apply();
    document.addEventListener('visibilitychange', apply);
    return () => { clearInterval(timer); document.removeEventListener('visibilitychange', apply); };
  }, [mode, setFrameloop, invalidate]);
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
      <PerformanceMonitor bounds={() => [45, 58]} flipflops={14} factor={1} step={0.2} onChange={onChange}
        onDecline={api => { api.top = false; if (api.factor > 0.001) api.bottom = false; else if (!api.bottom) api.bottom = true; else if (step(-1)) { api.factor = 1; api.bottom = false; } }}
        onIncline={api => { api.bottom = false; if (api.factor < 0.999) api.top = false; else if (!api.top) api.top = true; else if (step(1)) { api.factor = 0.4; api.top = false; } }}
        onFallback={() => { if (useGame.getState().qualitySetting === 'auto') useGame.getState().setDprScale(0.8); }} />
      <FrameGovernor />
      <Boundary>
        <Suspense fallback={null}>
          <World />
        </Suspense>
      </Boundary>
    </Canvas>
  );
}
