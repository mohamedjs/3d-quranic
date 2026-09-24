// Canvas + adaptive quality. WebGL2 renderer (see README for why not WebGPU yet).
import { Suspense, Component } from 'react';
import { Canvas } from '@react-three/fiber';
import { PerformanceMonitor } from '@react-three/drei';
import * as THREE from 'three';
import { World } from '../world/World.jsx';
import { useGame, usePreset } from '../systems/store.js';
import { LEVELS } from '../systems/quality.js';

function step(dir) {
  const { qualitySetting, quality, setQuality, mode } = useGame.getState();
  if (qualitySetting !== 'auto') return;               // the player chose a level: respect it
  if (mode !== 'explore') return;                      // loading/cinematics aren't representative frames
  const i = LEVELS.indexOf(quality) + dir;
  if (i >= 0 && i < LEVELS.length) setQuality(LEVELS[i]);
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

export function Game() {
  const preset = usePreset();
  return (
    <Canvas
      shadows="percentage"
      dpr={Math.min(window.devicePixelRatio || 1, preset.dpr)}
      gl={{ antialias: false, powerPreference: 'high-performance', stencil: false }}
      camera={{ fov: 50, near: 0.1, far: 1600, position: [0, 3, -64] }}
      onCreated={({ gl }) => { gl.toneMapping = THREE.NoToneMapping; }}
      fallback={<p className="nogl">This game needs WebGL 2 (3D graphics). Try Chrome, Edge, Firefox or Safari with hardware acceleration on. — تحتاج اللعبة إلى WebGL.</p>}
    >
      <PerformanceMonitor bounds={() => [45, 58]} flipflops={4} onDecline={() => step(-1)} onIncline={() => step(1)} onFallback={() => useGame.getState().setQuality('low')} />
      <Boundary>
        <Suspense fallback={null}>
          <World />
        </Suspense>
      </Boundary>
    </Canvas>
  );
}
