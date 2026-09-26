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
  // coin pickup: a bright two-note "ding"; `step` climbs a pentatonic scale for quick pickups
  coin(step = 0, big = false) {
    if (!ctx) return;
    const PENTA = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24], t = ctx.currentTime;
    const f = (big ? 660 : 988) * Math.pow(2, PENTA[Math.min(step, PENTA.length - 1)] / 12);
    const out = ctx.createGain(); out.gain.value = big ? 0.2 : 0.14; out.connect(master);
    [[f, 0, 0.16], [f * 1.5, 0.07, 0.34]].forEach(([fr, d, len]) => {
      for (const [type, mul, v] of [['sine', 1, 1], ['triangle', 2, 0.25]]) {
        const o = ctx.createOscillator(), g = ctx.createGain();
        o.type = type; o.frequency.value = fr * mul;
        g.gain.setValueAtTime(0, t + d); g.gain.linearRampToValueAtTime(v, t + d + 0.006); g.gain.exponentialRampToValueAtTime(0.001, t + d + len);
        o.connect(g).connect(out); o.start(t + d); o.stop(t + d + len + 0.02);
      }
    });
    if (big) setTimeout(() => this.combo(0.6), 90);
  },
  // ten in a row: a soft rising arpeggio
  combo(vol = 1) {
    if (!ctx) return;
    const t = ctx.currentTime, out = ctx.createGain(); out.gain.value = 0.12 * vol; out.connect(master);
    [1046.5, 1318.5, 1568, 2093].forEach((fr, i) => {
      const o = ctx.createOscillator(), g = ctx.createGain(), s = t + i * 0.075;
      o.type = 'triangle'; o.frequency.value = fr;
      g.gain.setValueAtTime(0, s); g.gain.linearRampToValueAtTime(1, s + 0.01); g.gain.exponentialRampToValueAtTime(0.001, s + 0.45);
      o.connect(g).connect(out); o.start(s); o.stop(s + 0.5);
    });
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

// Character voices (never Quran). Order of preference:
//  1. a good installed system voice for the language (Windows/macOS/Android usually have one)
//  2. for Arabic: Piper neural TTS running in the page (ar_JO-kareem), downloaded once
//     (~63 MB) into the browser's private storage — this is what makes Linux Chrome talk,
//     since it ships no Arabic voice and speech-dispatcher only offers robotic eSpeak
//  3. nothing: the dialogue box always shows the text, so the game never waits on speech
const PIPER_VOICE = { ar: 'ar_JO-kareem-medium' };
const voiceAudio = new Audio();   // separate element: recitation has its own, they never mix
let piper = null, piperState = 'idle', token = 0;
const sentences = t => t.match(/[^.!?؟،,:«»"“”]+[.!?؟،,:«»"“”]*/g)?.map(x => x.trim()).filter(Boolean) ?? [t];

export const Voice = {
  enabled: true,
  onStatus: null,                     // (state, percent) → UI toast
  system(lang) {
    const vs = window.speechSynthesis?.getVoices() ?? [];
    const mine = vs.filter(v => v.lang.toLowerCase().startsWith(lang) && !/espeak/i.test(v.name));
    return mine.find(v => /google|natural|premium|online/i.test(v.name)) || mine[0] || null;
  },
  pick(lang) { return this.system(lang) || (PIPER_VOICE[lang] && piperState !== 'failed') ; },
  // Start fetching the neural voice early (called once the player presses start).
  async prepare(lang) {
    if (!PIPER_VOICE[lang] || this.system(lang) || piperState !== 'idle') return;
    piperState = 'loading';
    try {
      const { TtsSession } = await import('@mintplex-labs/piper-tts-web');
      piper = await TtsSession.create({
        voiceId: PIPER_VOICE[lang],
        progress: p => { if (p.total) this.onStatus?.('download', Math.round(p.loaded * 100 / p.total)); },
      });
      piperState = 'ready'; this.onStatus?.('ready', 100);
    } catch (e) {
      piperState = 'failed'; console.error('Piper TTS:', e); this.onStatus?.('failed', 0, e.message);
    }
  },
  // Recorded voice lines (public/audio/manifest.json: { "<exact text>": "audio/<file>" }),
  // made offline with tools/voice_lines.py + Habibi-TTS. Played first; TTS is the fallback.
  manifest: null,
  async recorded(text) {
    if (!this.manifest) this.manifest = fetch('./audio/manifest.json').then(r => (r.ok ? r.json() : {})).catch(() => ({}));
    const m = await this.manifest; return m[text] || null;
  },
  // Resolves when the line has been spoken: true = a voice played to the end,
  // false = nothing was voiced (disabled, still downloading, blocked, or interrupted).
  async speak(text, lang) {
    this.cancel();
    if (!this.enabled) return false;
    const my0 = token, file = lang === 'ar' ? await this.recorded(text) : null;
    if (my0 !== token) return false;                             // a newer line started meanwhile
    if (file) {
      voiceAudio.src = './' + file; voiceAudio.playbackRate = 1;
      try {
        await voiceAudio.play();
        return await new Promise(r => { voiceAudio.onended = () => r(my0 === token); voiceAudio.onpause = () => r(false); });
      } catch (e) { /* autoplay blocked / missing → fall back */ }
    }
    const clean = text.replace(/ﷺ/g, lang === 'ar' ? 'صلى الله عليه وسلم' : 'peace be upon him');
    const v = this.system(lang);
    if (v && window.speechSynthesis) {
      const u = new SpeechSynthesisUtterance(clean); u.voice = v; u.lang = v.lang; u.rate = 0.92;
      const my = token;
      return new Promise(r => {
        u.onend = () => r(my === token); u.onerror = () => r(false);
        speechSynthesis.speak(u);
      });
    }
    if (piperState !== 'ready' || !PIPER_VOICE[lang]) return false;   // still downloading: text only
    // synthesise sentence by sentence; the next one renders while the current one plays
    const my = ++token, parts = sentences(clean);
    let next = piper.predict(parts[0]);
    for (let i = 0; i < parts.length; i++) {
      let wav; try { wav = await next; } catch (e) { console.error('Piper TTS:', e); return false; }
      if (my !== token) return false;
      if (i + 1 < parts.length) next = piper.predict(parts[i + 1]);
      const url = URL.createObjectURL(wav);
      voiceAudio.src = url; voiceAudio.playbackRate = 0.95;
      await voiceAudio.play().then(() => new Promise(r => { voiceAudio.onended = voiceAudio.onpause = r; })).catch(() => {});
      URL.revokeObjectURL(url);
      if (my !== token) return false;
    }
    return true;
  },
  cancel() { token++; window.speechSynthesis?.cancel(); voiceAudio.pause(); },
};
