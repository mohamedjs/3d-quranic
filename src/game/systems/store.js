// Shared state between React components and the imperative game systems.
// `detail` sets what is *built* (grass/tree counts) and only changes from Settings;
// `quality` sets per-frame costs (resolution, AO, bloom, water passes…) and is what AUTO
// adjusts from measured frame rate — so adapting never freezes the game with a rebuild.
import { create } from 'zustand';
import { guessLevel, PRESETS } from './quality.js';

export const useGame = create(set => ({
  mode: 'loading',             // loading | title | explore | dialogue | quran | panel
  qualitySetting: 'auto',      // auto | low | medium | high | ultra
  quality: guessLevel(),
  detail: guessLevel(),
  focus: null,                 // THREE.Vector3 the DoF focuses on during dialogue
  setMode: mode => set({ mode }),
  setQuality: q => set({ quality: q }),
  setQualitySetting: s => set(st => {
    if (s === st.qualitySetting) return {};
    const level = s === 'auto' ? guessLevel() : s;
    return { qualitySetting: s, quality: level, detail: level };
  }),
}));
export const usePreset = () => useGame(s => PRESETS[s.quality]);
export const useDetail = () => useGame(s => PRESETS[s.detail]);
