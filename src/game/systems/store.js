// Shared state between React components and the imperative game systems.
// `detail` sets what is *built* (grass/tree counts) and only changes from Settings;
// `quality` sets per-frame costs (resolution, AO, bloom, water passes…) and is what AUTO
// adjusts from measured frame rate — so adapting never freezes the game with a rebuild.
import { create } from 'zustand';
import { guessLevel, resolvedQuality, PRESETS } from './quality.js';

// AUTO remembers when this device had to fall back to LITE (measured, not guessed), so the
// next visit builds the light world straight away instead of building Low and rebuilding.
const HINT = 'quran-journey-perf';
// AUTO = the level main.jsx resolved on the loading screen (GPU guess + device age), else the plain guess
export const autoLevel = () => { try { if (localStorage.getItem(HINT) === 'lite') return 'lite'; } catch { /* private mode */ } return resolvedQuality()?.level ?? guessLevel(); };
export const rememberLite = on => { try { on ? localStorage.setItem(HINT, 'lite') : localStorage.removeItem(HINT); } catch { /* ignore */ } };

// Start from the saved choice (same key as systems/game.js) so the world is built once at the
// right level instead of being built at the guess and rebuilt when the save is applied.
const savedQuality = (() => {
  try {
    const st = JSON.parse(localStorage.getItem('quran-journey-v1'))?.settings, q = st?.quality;
    if (q === 'auto' && !st.autoPicked) return 'lite';          // the game starts on Lite; AUTO only when the player picked it
    return PRESETS[q] || q === 'auto' ? q : null;
  } catch { return null; }
})();
const startLevel = !savedQuality ? 'lite' : savedQuality !== 'auto' ? savedQuality : autoLevel();   // first visit: Lite — the player raises it in Settings

export const useGame = create(set => ({
  mode: 'loading',             // loading | title | explore | dialogue | quran | panel
  qualitySetting: savedQuality ?? 'lite',   // auto | lite | low | medium | high | ultra
  quality: startLevel,
  detail: startLevel,
  dprScale: 1,                 // adaptive resolution (PerformanceMonitor factor), applied on top of the preset
  focus: null,                 // THREE.Vector3 the DoF focuses on during dialogue
  setMode: mode => set({ mode }),
  setQuality: q => set({ quality: q }),
  // AUTO dropping to LITE mid-play switches only the per-frame costs (30 fps cap, DPR ≤ 1, baked
  // shadow, simple water…) — never a world rebuild while the child plays. It is remembered
  // (rememberLite), so the next launch BUILDS the light world from the start.
  dropToLite: () => set(st => (st.quality === 'lite' ? {} : { quality: 'lite' })),
  setDprScale: k => set(st => (Math.abs(st.dprScale - k) < 0.05 ? {} : { dprScale: k })),
  setQualitySetting: s => set(st => {
    if (s === st.qualitySetting) return {};
    const level = s === 'auto' ? autoLevel() : s;
    return { qualitySetting: s, quality: level, detail: level };
  }),
}));
export const usePreset = () => useGame(s => PRESETS[s.quality]);
export const useDetail = () => useGame(s => PRESETS[s.detail]);
