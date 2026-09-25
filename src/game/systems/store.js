// Shared state between React components and the imperative game systems.
// `detail` sets what is *built* (grass/tree counts) and only changes from Settings;
// `quality` sets per-frame costs (resolution, AO, bloom, water passes…) and is what AUTO
// adjusts from measured frame rate — so adapting never freezes the game with a rebuild.
import { create } from 'zustand';
import { guessLevel, PRESETS } from './quality.js';

// Start from the saved choice (same key as systems/game.js) so the world is built once at the
// right level instead of being built at the guess and rebuilt when the save is applied.
const savedQuality = (() => {
  try { const q = JSON.parse(localStorage.getItem('quran-journey-v1'))?.settings?.quality; return PRESETS[q] || q === 'auto' ? q : null; } catch { return null; }
})();
const startLevel = savedQuality && savedQuality !== 'auto' ? savedQuality : guessLevel();

export const useGame = create(set => ({
  mode: 'loading',             // loading | title | explore | dialogue | quran | panel
  qualitySetting: savedQuality ?? 'auto',   // auto | low | medium | high | ultra
  quality: startLevel,
  detail: startLevel,
  dprScale: 1,                 // adaptive resolution (PerformanceMonitor factor), applied on top of the preset
  focus: null,                 // THREE.Vector3 the DoF focuses on during dialogue
  setMode: mode => set({ mode }),
  setQuality: q => set({ quality: q }),
  setDprScale: k => set(st => (Math.abs(st.dprScale - k) < 0.05 ? {} : { dprScale: k })),
  setQualitySetting: s => set(st => {
    if (s === st.qualitySetting) return {};
    const level = s === 'auto' ? guessLevel() : s;
    return { qualitySetting: s, quality: level, detail: level };
  }),
}));
export const usePreset = () => useGame(s => PRESETS[s.quality]);
export const useDetail = () => useGame(s => PRESETS[s.detail]);
