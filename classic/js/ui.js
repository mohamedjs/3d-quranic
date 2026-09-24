// HUD, minimap, world map, journal, settings, title, reward card, toasts.
import { toMap } from './terrain.js';
import { QuranService } from './quran.js';

export const STR = {
  ar: {
    title: 'رحلة القرآن', tagline: 'استكشف · استمع · تعلّم · انمُ', cont: 'متابعة الرحلة', newGame: 'رحلة جديدة', settings: 'الإعدادات',
    talk: 'تحدّث', journal: 'دفتر المعرفة', map: 'خريطة العالم', mapSub: 'اكتشف المزيد من قصص القرآن', unlocked: 'فُتحت المعرفة!',
    points: 'نقطة معرفة', continue: 'متابعة', nextStory: 'قصة جديدة متاحة', discovered: 'مكان جديد', explore: 'استكشف العالم',
    exploreSub: 'قصص جديدة قريبًا إن شاء الله', soon: 'قريبًا', empty: 'لم تفتح أي قصة بعد. تجوّل وتحدّث مع أهل القرية!',
    listenAgain: 'استمع مرة أخرى', lang: 'اللغة', reciter: 'القارئ', voice: 'صوت الشخصيات (قراءة آلية)', meaning: 'إظهار المعنى تحت الآية',
    volume: 'صوت الطبيعة', music: 'نغمة هادئة (بدون موسيقى افتراضيًا)', reset: 'مسح التقدّم', resetQ: 'هل تريد مسح كل التقدّم؟',
    controls: 'امشِ بالأسهم أو WASD · اسحب لتدير الكاميرا · اضغط على الأرض لتمشي إليها', loading: 'جارٍ تحميل الآيات من Quran.com…',
    offline: 'تعذّر الاتصال بموقع Quran.com. تأكّد من الاتصال بالإنترنت ثم أعد المحاولة.', noAudio: 'لا يتوفّر تسجيل لهذا القارئ لهذه الآيات. جرّب قارئًا آخر من الإعدادات.',
    audioErr: 'تعذّر تشغيل التلاوة.', tapToPlay: 'اضغط «إعادة المحاولة» لتشغيل التلاوة.', retry: 'إعادة المحاولة', skip: 'تخطٍّ', reciting: 'القارئ',
    verse: 'الآية', of: 'من', tafsir: 'التفسير الميسّر', translation: 'Saheeh International', sources: 'المصادر', building: 'نبني العالم…', you: 'أنت',
    close: 'إغلاق', noVoice: 'لا يوجد صوت عربي مثبّت في المتصفح — سيظهر الكلام مكتوبًا.',
  },
  en: {
    title: 'Quran Journey', tagline: 'Explore · Listen · Learn · Grow', cont: 'Continue', newGame: 'New Journey', settings: 'Settings',
    talk: 'Talk', journal: 'Knowledge Book', map: 'Explore the World', mapSub: 'Discover more Quranic stories', unlocked: 'Knowledge Unlocked!',
    points: 'Knowledge Points', continue: 'Continue', nextStory: 'Next story available', discovered: 'Discovered', explore: 'Explore the world',
    exploreSub: 'More stories coming soon, in sha Allah', soon: 'Coming soon', empty: 'No stories unlocked yet. Walk around and talk to the villagers!',
    listenAgain: 'Listen again', lang: 'Language', reciter: 'Reciter', voice: 'Character voices (speech synthesis)', meaning: 'Show meaning under the verse',
    volume: 'Nature sounds', music: 'Soft pad (off by default)', reset: 'Reset progress', resetQ: 'Erase all progress?',
    controls: 'Walk with WASD / arrows · drag to look · tap the ground to walk there', loading: 'Loading verses from Quran.com…',
    offline: 'Could not reach Quran.com. Check your internet connection and try again.', noAudio: 'This reciter has no recording for these verses. Try another reciter in Settings.',
    audioErr: 'The recitation could not be played.', tapToPlay: 'Press “Try again” to start the recitation.', retry: 'Try again', skip: 'Skip', reciting: 'Reciting',
    verse: 'Verse', of: 'of', tafsir: 'Tafsir al-Muyassar', translation: 'Saheeh International', sources: 'Sources', building: 'Building the world…', you: 'You',
    close: 'Close', noVoice: 'No English voice installed — lines will show as text.',
  },
};

const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export class UI {
  constructor({ mapCanvas, data, save, persist, onSettings }) {
    Object.assign(this, { mapCanvas, data, save, persist, onSettings });
    this.mini = $('minimap').querySelector('canvas').getContext('2d');
    this.toastTimer = 0; this.bannerTimer = 0;
  }
  get S() { return STR[this.save.settings.lang]; }
  t(o) { return o?.[this.save.settings.lang] ?? o?.ar ?? ''; }

  applyLang() {
    const ar = this.save.settings.lang === 'ar';
    document.documentElement.lang = ar ? 'ar' : 'en'; document.documentElement.dir = ar ? 'rtl' : 'ltr';
    const S = this.S;
    $('title').querySelector('h1').textContent = S.title;
    $('title').querySelector('.tagline').textContent = S.tagline;
    $('btn-continue').textContent = S.cont; $('btn-new').textContent = S.newGame; $('btn-settings').textContent = S.settings;
    $('talk').querySelector('span').textContent = S.talk;
    for (const b of $('dock').children) b.title = S[b.dataset.open === 'settings' ? 'settings' : b.dataset.open];
    this.setPoints();
  }

  // ---- HUD --------------------------------------------------------------
  showHud(on) { $('hud').hidden = !on; }
  objective(lines) {
    const o = $('objective'); o.querySelector('b').textContent = lines[0]; o.querySelector('small').textContent = lines[1] ?? '';
    o.classList.remove('pulse'); void o.offsetWidth; o.classList.add('pulse');
  }
  setPoints() { $('points').querySelector('b').textContent = this.save.points; $('points').title = this.S.points; }
  talk(show) { $('talk').hidden = !show; }
  toast(text, ms = 3200) {
    const t = $('toast'); t.textContent = text; t.classList.add('show');
    clearTimeout(this.toastTimer); this.toastTimer = setTimeout(() => t.classList.remove('show'), ms);
  }
  banner(small, big) {
    const b = $('banner'); b.querySelector('small').textContent = small; b.querySelector('b').textContent = big;
    b.classList.remove('show'); void b.offsetWidth; b.classList.add('show');
    clearTimeout(this.bannerTimer); this.bannerTimer = setTimeout(() => b.classList.remove('show'), 3800);
  }
  bubble(text, screen) {
    const b = $('bubble');
    if (!text || !screen) { b.hidden = true; return; }
    if (b.textContent !== text) b.textContent = text;
    b.hidden = false; b.style.transform = `translate(${screen.x}px, ${screen.y}px) translate(-50%, -100%)`;
  }
  letterbox(on) { document.body.classList.toggle('cinema', on); }
  deep(on) { document.body.classList.toggle('deep', on); }

  // Compass-style minimap: rotates with the camera, north marker on the ring.
  minimap(player, npcs) {
    const ctx = this.mini, size = ctx.canvas.width, c = size / 2, map = this.mapCanvas, n = map.width;
    const k = 2.4 * (size / 180) / (n / 520);      // ~2.4 px per metre
    const [px, py] = toMap(player.pos.x, player.pos.z, n);
    const rot = -Math.PI / 2 - Math.atan2(Math.cos(player.yaw), -Math.sin(player.yaw));
    ctx.clearRect(0, 0, size, size);
    ctx.save(); ctx.beginPath(); ctx.arc(c, c, c - 2, 0, Math.PI * 2); ctx.clip();
    ctx.fillStyle = '#c9a877'; ctx.fillRect(0, 0, size, size);
    ctx.translate(c, c); ctx.rotate(rot); ctx.scale(k, k); ctx.translate(-px, -py);
    ctx.imageSmoothingEnabled = true; ctx.drawImage(map, 0, 0);
    for (const npc of npcs) {
      if (npc.state === 'locked') continue;
      const [x, y] = toMap(npc.x, npc.z, n);
      ctx.save(); ctx.translate(x, y); ctx.rotate(-rot); ctx.scale(1 / k, 1 / k);
      ctx.fillStyle = npc.state === 'open' ? '#ffc94a' : '#e8e2d0'; ctx.strokeStyle = '#3a2a14'; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(0, 0, 7, 0, 7); ctx.fill(); ctx.stroke();
      ctx.fillStyle = '#3a2a14'; ctx.font = 'bold 11px Nunito, sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(npc.state === 'open' ? '!' : '✓', 0, 0.5); ctx.restore();
    }
    ctx.restore();
    // player arrow always points up the screen relative to its facing
    ctx.save(); ctx.translate(c, c);
    ctx.rotate(rot + Math.atan2(-Math.cos(player.facing), Math.sin(player.facing)) + Math.PI / 2);
    ctx.fillStyle = '#fff'; ctx.strokeStyle = '#1e4f73'; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(0, -9); ctx.lineTo(7, 7); ctx.lineTo(0, 3); ctx.lineTo(-7, 7); ctx.closePath(); ctx.stroke(); ctx.fill(); ctx.restore();
    const a = -Math.PI / 2 + rot, r = c - 12;
    $('minimap').querySelector('.n').style.transform = `translate(${c + Math.cos(a) * r}px, ${c + Math.sin(a) * r}px) translate(-50%, -50%)`;
  }

  // ---- panels -----------------------------------------------------------
  openPanel(title, body) {
    const p = $('panel'); p.hidden = false; p.querySelector('h2').textContent = title;
    const b = p.querySelector('.body'); b.innerHTML = ''; b.append(body);
    requestAnimationFrame(() => p.classList.add('show'));
    return new Promise(res => { this.closePanel = () => { p.classList.remove('show'); setTimeout(() => { p.hidden = true; }, 250); this.closePanel = null; res(); }; p.querySelector('.x').onclick = () => this.closePanel(); });
  }

  worldMap(player, npcs) {
    const S = this.S, wrap = document.createElement('div'); wrap.className = 'worldmap';
    const cv = document.createElement('canvas'); cv.width = cv.height = 720; wrap.append(cv);
    const ctx = cv.getContext('2d'), n = this.mapCanvas.width, k = 720 / n;
    ctx.imageSmoothingEnabled = true; ctx.drawImage(this.mapCanvas, 0, 0, 720, 720);
    const g = ctx.createRadialGradient(360, 360, 250, 360, 360, 520); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(40,24,8,.55)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, 720, 720);
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.direction = this.save.settings.lang === 'ar' ? 'rtl' : 'ltr';
    for (const a of this.data.areas) {
      const [x, y] = toMap(a.x, a.z, n).map(v => v * k), known = this.save.discovered.includes(a.id);
      const hasStory = this.data.encounters.some(e => e.area === a.id);
      const label = known ? this.t(a) + (hasStory ? '' : ` · ${S.soon}`) : '؟';
      ctx.font = `700 ${known ? 20 : 26}px Tajawal, Nunito, sans-serif`;
      const w = ctx.measureText(label).width + 28;
      ctx.fillStyle = 'rgba(16,26,34,.78)'; ctx.strokeStyle = 'rgba(240,195,90,.8)'; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.roundRect(x - w / 2, y - 18, w, 36, 18); ctx.fill(); ctx.stroke();
      ctx.fillStyle = known ? '#fbeccc' : '#b9b09a'; ctx.fillText(label, x, y + 1);
    }
    for (const npc of npcs) {
      const [x, y] = toMap(npc.x, npc.z, n).map(v => v * k);
      ctx.fillStyle = npc.state === 'open' ? '#ffc94a' : npc.state === 'done' ? '#e8e2d0' : '#7d7564';
      ctx.beginPath(); ctx.arc(x, y + 34, 9, 0, 7); ctx.fill();
      ctx.fillStyle = '#2a1c0c'; ctx.font = 'bold 13px Nunito'; ctx.fillText(npc.state === 'open' ? '!' : npc.state === 'done' ? '✓' : '…', x, y + 35);
    }
    const [px, py] = toMap(player.pos.x, player.pos.z, n).map(v => v * k);
    ctx.save(); ctx.translate(px, py); ctx.rotate(Math.atan2(-Math.cos(player.facing), Math.sin(player.facing)) + Math.PI / 2);
    ctx.fillStyle = '#fff'; ctx.strokeStyle = '#1e4f73'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(0, -13); ctx.lineTo(10, 10); ctx.lineTo(0, 5); ctx.lineTo(-10, 10); ctx.closePath(); ctx.stroke(); ctx.fill(); ctx.restore();
    const sub = document.createElement('p'); sub.className = 'sub'; sub.textContent = S.mapSub; wrap.prepend(sub);
    return this.openPanel(S.map, wrap);
  }

  journal(onReplay) {
    const S = this.S, list = document.createElement('div'); list.className = 'journal';
    const done = this.data.encounters.filter(e => this.save.done.includes(e.id));
    if (!done.length) list.innerHTML = `<p class="empty">${esc(S.empty)}</p>`;
    for (const e of done) {
      const v = e.steps.find(s => s.type === 'verses'), card = document.createElement('article');
      card.innerHTML = `<div class="medal sm">${MEDAL}</div><div><h3>${esc(this.t(e.title))}</h3>
        <p>${esc(this.t(e.character.name))} · ${esc(v.from)}–${esc(v.to.split(':')[1])}</p>
        <small>${esc(S.sources)}: ${e.sources.map(esc).join(' · ')}</small></div><button>${esc(S.listenAgain)}</button>`;
      card.querySelector('button').onclick = () => { this.closePanel?.(); onReplay(v); };
      list.append(card);
    }
    return this.openPanel(S.journal, list);
  }

  settings(onReset) {
    const S = this.S, st = this.save.settings, f = document.createElement('form'); f.className = 'settings';
    f.innerHTML = `
      <label>${esc(S.lang)}<select name="lang"><option value="ar">العربية</option><option value="en">English</option></select></label>
      <label>${esc(S.reciter)}<select name="reciter"><option value="${st.reciter}">…</option></select></label>
      <label class="row"><input type="checkbox" name="voice"> ${esc(S.voice)}</label>
      <label class="row"><input type="checkbox" name="meaning"> ${esc(S.meaning)}</label>
      <label>${esc(S.volume)}<input type="range" name="volume" min="0" max="1" step="0.05"></label>
      <label class="row"><input type="checkbox" name="music"> ${esc(S.music)}</label>
      <button type="button" class="danger">${esc(S.reset)}</button>`;
    f.lang.value = st.lang; f.voice.checked = st.voice; f.meaning.checked = st.meaning; f.volume.value = st.volume; f.music.checked = st.music;
    QuranService.getReciters().then(rs => {
      f.reciter.innerHTML = rs.map(r => `<option value="${r.id}">${esc(r.name)}${r.style ? ' — ' + esc(r.style) : ''}</option>`).join('');
      f.reciter.value = st.reciter;
    }).catch(e => { f.reciter.innerHTML = `<option value="${st.reciter}">${esc(e.message)}</option>`; });
    f.onchange = () => {
      Object.assign(st, { lang: f.lang.value, reciter: +f.reciter.value, voice: f.voice.checked, meaning: f.meaning.checked, volume: +f.volume.value, music: f.music.checked });
      this.persist(); this.onSettings();
    };
    f.querySelector('.danger').onclick = () => { if (confirm(S.resetQ)) onReset(); };
    return this.openPanel(S.settings, f);
  }

  reward(enc) {
    const S = this.S, R = $('reward');
    R.querySelector('h2').textContent = S.unlocked;
    R.querySelector('p').textContent = this.t(enc.reward);
    R.querySelector('.pts').textContent = `+${enc.reward.points} ${S.points}`;
    R.querySelector('button').textContent = S.continue;
    R.hidden = false; requestAnimationFrame(() => R.classList.add('show'));
    return new Promise(res => {
      const go = () => { removeEventListener('keydown', key); R.classList.remove('show'); setTimeout(() => { R.hidden = true; res(); }, 400); };
      const key = e => { if (e.code === 'Enter' || e.code === 'Space') { e.preventDefault(); go(); } };
      R.querySelector('button').onclick = go; addEventListener('keydown', key);
    });
  }
}

export const MEDAL = `<svg viewBox="0 0 120 120"><defs><radialGradient id="mg"><stop offset="0" stop-color="#fff2c0"/><stop offset=".6" stop-color="#f0c35a"/><stop offset="1" stop-color="#9a6a1c"/></radialGradient></defs>
  <circle cx="60" cy="60" r="54" fill="none" stroke="#f0c35a" stroke-width="2" opacity=".6"/><circle cx="60" cy="60" r="46" fill="url(#mg)"/>
  <path d="M30 44 Q45 38 60 46 Q75 38 90 44 L90 82 Q75 76 60 84 Q45 76 30 82 Z" fill="#5a3a12"/><path d="M34 47 Q46 42 58 49 L58 79 Q46 73 34 78 Z M62 49 Q74 42 86 47 L86 78 Q74 73 62 79 Z" fill="#fff6dc"/>
  <path d="M60 22 l4 10 -4 4 -4 -4 z" fill="#fff6dc"/></svg>`;
