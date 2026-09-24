// Ambience is synthesised (wind, water, birds, footsteps) so the game ships no audio files.
// Character voices use the browser's speech synthesis. Quran recitation NEVER goes
// through here — it is recorded audio played by recitation.js.
let ctx, master, amb, water, music, noiseBuf;
const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

export const Sound = {
  get ready() { return !!ctx; },
  start(settings) {
    if (ctx) return;
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    master = ctx.createGain(); master.gain.value = settings.volume; master.connect(ctx.destination);
    amb = ctx.createGain(); amb.connect(master);
    noiseBuf = ctx.createBuffer(1, ctx.sampleRate * 3, ctx.sampleRate);
    const d = noiseBuf.getChannelData(0); let last = 0;
    for (let i = 0; i < d.length; i++) { last = (last + 0.02 * (Math.random() * 2 - 1)) / 1.02; d[i] = last * 3.5; }
    // wind: brown noise, low-passed, slowly breathing
    const wind = this.loop(), lp = ctx.createBiquadFilter(), wg = ctx.createGain(), lfo = ctx.createOscillator(), lg = ctx.createGain();
    lp.type = 'lowpass'; lp.frequency.value = 380; wg.gain.value = 0.22; lfo.frequency.value = 0.07; lg.gain.value = 0.12;
    lfo.connect(lg).connect(wg.gain); wind.connect(lp).connect(wg).connect(amb); lfo.start();
    // flowing water: band-passed, faded in near the river and canals
    const wsrc = this.loop(), bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 900; bp.Q.value = 0.6;
    water = ctx.createGain(); water.gain.value = 0; wsrc.playbackRate.value = 3; wsrc.connect(bp).connect(water).connect(amb);
    // optional soft pad (off by default)
    music = ctx.createGain(); music.gain.value = 0; music.connect(master);
    const mf = ctx.createBiquadFilter(); mf.type = 'lowpass'; mf.frequency.value = 700; mf.connect(music);
    for (const f of [110, 164.81, 220.5]) { const o = ctx.createOscillator(); o.type = 'triangle'; o.frequency.value = f; const g = ctx.createGain(); g.gain.value = 0.05; o.connect(g).connect(mf); o.start(); }
    this.setMusic(settings.music);
    const birdLoop = () => { if (Math.random() < 0.55) this.chirp(); setTimeout(birdLoop, 600 + Math.random() * 2200); };
    birdLoop();
  },
  loop() { const s = ctx.createBufferSource(); s.buffer = noiseBuf; s.loop = true; s.start(); return s; },
  chirp() {
    if (!ctx || amb.gain.value < 0.05) return;
    const t = ctx.currentTime, o = ctx.createOscillator(), g = ctx.createGain(), p = ctx.createStereoPanner();
    p.pan.value = Math.random() * 1.6 - 0.8;
    const base = 2600 + Math.random() * 1800, notes = 2 + ((Math.random() * 4) | 0);
    for (let i = 0; i < notes; i++) {
      const s = t + i * 0.11;
      o.frequency.setValueAtTime(base * (1 + Math.random() * 0.2), s);
      o.frequency.exponentialRampToValueAtTime(base * (0.7 + Math.random() * 0.6), s + 0.08);
      g.gain.setValueAtTime(0, s); g.gain.linearRampToValueAtTime(0.035, s + 0.015); g.gain.exponentialRampToValueAtTime(0.001, s + 0.09);
    }
    o.connect(g).connect(p).connect(amb); o.start(t); o.stop(t + notes * 0.11 + 0.1);
  },
  step(surface) {
    if (!ctx) return;
    const t = ctx.currentTime, s = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain();
    s.buffer = noiseBuf; s.playbackRate.value = 4;
    f.type = 'bandpass'; f.frequency.value = { wood: 350, sand: 700, grass: 1400 }[surface] ?? 900; f.Q.value = 1.2;
    g.gain.setValueAtTime(0.25, t); g.gain.exponentialRampToValueAtTime(0.001, t + 0.09);
    s.connect(f).connect(g).connect(amb); s.start(t, Math.random() * 2, 0.1);
  },
  setWater(dist) { if (ctx) water.gain.setTargetAtTime(0.35 * (1 - smooth(3, 28, dist)), ctx.currentTime, 0.5); },
  // explore: full ambience · dialogue: softened · quran: silence so only the recitation is heard
  mode(m) {
    if (!ctx) return;
    const t = ctx.currentTime;
    amb.gain.setTargetAtTime({ explore: 1, dialogue: 0.4, quran: 0 }[m] ?? 1, t, 0.4);
    music.gain.setTargetAtTime(m === 'quran' || !this.musicOn ? 0 : 0.5, t, 0.4);
  },
  setVolume(v) { if (ctx) master.gain.value = v; },
  setMusic(on) { this.musicOn = on; if (ctx) music.gain.setTargetAtTime(on ? 0.5 : 0, ctx.currentTime, 0.5); },
};

export const Voice = {
  enabled: true,
  pick(lang) {
    const vs = window.speechSynthesis?.getVoices() ?? [];
    return vs.find(v => v.lang.toLowerCase().startsWith(lang) && /google|natural|premium/i.test(v.name)) || vs.find(v => v.lang.toLowerCase().startsWith(lang));
  },
  speak(text, lang) {
    this.cancel();
    if (!this.enabled || !window.speechSynthesis) return;
    const v = this.pick(lang); if (!v) return;   // no voice installed: the text box still carries the line
    const u = new SpeechSynthesisUtterance(text.replace(/ﷺ/g, lang === 'ar' ? 'صلى الله عليه وسلم' : 'peace be upon him'));
    u.voice = v; u.lang = v.lang; u.rate = 0.92;
    speechSynthesis.speak(u);
  },
  cancel() { window.speechSynthesis?.cancel(); },
};
