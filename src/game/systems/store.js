// Shared state between React components and the imperative game systems.
// `detail` sets what is *built* (grass/tree counts) and only changes from Settings;
// `quality` sets per-frame costs (resolution, AO, bloom, water passes…) and is what AUTO
// adjusts from measured frame rate — so adapting never freezes the game with a rebuild.
import { create } from 'zustand';
import { guessLevel, PRESETS } from './quality.js';

// AUTO remembers when this device had to fall back to LITE (measured, not guessed), so the
// next visit builds the light world straight away instead of building Low and rebuilding.
const HINT = 'quran-journey-perf';
export const autoLevel = () => { try { if (localStorage.getItem(HINT) === 'lite') return 'lite'; } catch { /* private mode */ } return guessLevel(); };
export const rememberLite = on => { try { on ? localStorage.setItem(HINT, 'lite') : localStorage.removeItem(HINT); } catch { /* ignore */ } };

// Start from the saved choice (same key as systems/game.js) so the world is built once at the
// right level instead of being built at the guess and rebuilt when the save is applied.
const savedQuality = (() => {
  try { const q = JSON.parse(localStorage.getItem('quran-journey-v1'))?.settings?.quality; return PRESETS[q] || q === 'auto' ? q : null; } catch { return null; }
})();
const startLevel = savedQuality && savedQuality !== 'auto' ? savedQuality : autoLevel();

export const useGame = create(set => ({
  mode: 'loading',             // loading | title | explore | dialogue | quran | panel
  qualitySetting: savedQuality ?? 'auto',   // auto | lite | low | medium | high | ultra
  quality: startLevel,
  detail: startLevel,
  dprScale: 1,                 // adaptive resolution (PerformanceMonitor factor), applied on top of the preset
  focus: null,                 // THREE.Vector3 the DoF focuses on during dialogue
  setMode: mode => set({ mode }),
  setQuality: q => set({ quality: q }),
  // AUTO dropping to LITE also rebuilds the world light (merged props, less grass): LITE's
  // savings are mostly in what is built, and it happens once, not back and forth
  dropToLite: () => set(st => (st.quality === 'lite' && st.detail === 'lite' ? {} : { quality: 'lite', detail: 'lite' })),
  setDprScale: k => set(st => (Math.abs(st.dprScale - k) < 0.05 ? {} : { dprScale: k })),
  setQualitySetting: s => set(st => {
    if (s === st.qualitySetting) return {};
    const level = s === 'auto' ? autoLevel() : s;
    return { qualitySetting: s, quality: level, detail: level };
  }),
}));
export const usePreset = () => useGame(s => PRESETS[s.quality]);
export const useDetail = () => useGame(s => PRESETS[s.detail]);
