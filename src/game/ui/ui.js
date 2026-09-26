// HUD, minimap, world map, journal, settings, title, reward card, toasts.
import { toMap, HALF, SIZE } from '../terrain/heightfield.js';
import { QuranService } from '../systems/quran.js';
import { PAINTED, illustrationURL } from './scenes.js';

// ---- UI kit assets (public/ui) -------------------------------------------------------------
// The icon + ornament sprites are injected inline so <use href="#i-…"> works everywhere and
// their gradients render. Paths are relative to the page, so the build runs from any sub-path.
const asset = p => new URL(p, document.baseURI).href;
export const spritesReady = typeof document === 'undefined' ? Promise.resolve() : Promise.all(['ui/icons.svg', 'ui/ornaments.svg'].map(p =>
  fetch(asset(p)).then(r => (r.ok ? r.text() : '')).catch(() => ''))).then(svgs => {
  const host = document.getElementById('sprites') ?? document.body.appendChild(Object.assign(document.createElement('div'), { id: 'sprites' }));
  host.innerHTML = svgs.join('').replace(/style="display:none"/g, '');
});
if (typeof document !== 'undefined') document.documentElement.style.setProperty('--title-img', `url("${asset('illustrations/title.webp')}")`);
export const icon = (name, cls = 'ic') => `<svg class="${cls}" aria-hidden="true"><use href="#i-${name}"/></svg>`;
// Speaker portrait for the dialogue name tag: by character id, else guessed from the look.
const PORTRAITS = ['grandma', 'farmer', 'player'];
export function portrait(id, who) {
  const hw = who?.look?.headwear;
  const p = PORTRAITS.includes(id) ? id : hw === 'hijab' ? 'grandma' : hw === 'turban' ? 'farmer' : 'default';
  return `<svg viewBox="0 0 64 64" aria-hidden="true"><use href="#p-${p}"/></svg>`;
}
// World-map painting (public/ui/world-map.webp) covers this world rectangle (metres):
const MAP_X0 = -235, MAP_X1 = 265, MAP_Z0 = -178, MAP_Z1 = 179;
const mapPct = (x, z) => [(x - MAP_X0) / (MAP_X1 - MAP_X0) * 100, (MAP_Z1 - z) / (MAP_Z1 - MAP_Z0) * 100];
// Region pins as named on the concept board (falls back to the area's own name).
const REGIONS = {
  oasis: { ar: 'الواحة', en: 'Oasis', g: 'oasis' },
  village: { ar: 'القرية', en: 'Village', g: 'village' },
  fields: { ar: 'النهر والمزارع', en: 'River & Farms', g: 'fields' },
  mountains: { ar: 'الجبال', en: 'Mountains', g: 'mountains' },
  ruins: { ar: 'المدينة القديمة', en: 'Ancient Settlement', g: 'ruins' },
  desert: { ar: 'طريق الصحراء', en: 'Desert Path', g: 'desert' },
};

export const STR = {
  ar: {
    title: 'رحلة القرآن', alt: 'Quran Journey', tagline: 'استكشف · استمع · تعلّم · انمُ', tagline2: 'Explore · Listen · Learn · Grow', cont: 'متابعة الرحلة', newGame: 'رحلة جديدة', settings: 'الإعدادات',
    talk: 'تحدّث', journal: 'دفتر المعرفة', map: 'خريطة العالم', mapSub: 'اكتشف المزيد من قصص القرآن', unlocked: 'فتحتَ كنزًا من المعرفة!', unlockedAlt: 'Knowledge Unlocked', lesson: 'ماذا نتعلّم؟', here: 'أنت هنا',
    points: 'نقطة معرفة', continue: 'متابعة', nextStory: 'قصة جديدة متاحة', discovered: 'مكان جديد', explore: 'استكشف العالم',
    exploreSub: 'قصص جديدة قريبًا إن شاء الله', soon: 'قريبًا', empty: 'لم تفتح أي قصة بعد. تجوّل وتحدّث مع أهل القرية!',
    listenAgain: 'استمع مرة أخرى', lang: 'اللغة', reciter: 'القارئ', voice: 'صوت الشخصيات (قراءة آلية)', meaning: 'إظهار المعنى تحت الآية', auto: 'الحوار يتقدّم تلقائيًا',
    volume: 'صوت الطبيعة', music: 'نغمة هادئة (بدون موسيقى افتراضيًا)', reset: 'مسح التقدّم', resetQ: 'هل تريد مسح كل التقدّم؟',
    controls: 'امشِ بالأسهم أو WASD · F يمشي بك إلى القصة · اسحب لتدير الكاميرا · اضغط على الأرض لتمشي إليها · العجلة أو + / − أو إصبعان للتقريب والارتفاع', zoomIn: 'تقريب', zoomOut: 'ابتعاد (منظر من أعلى)', centerMe: 'مكاني', mapZoom: 'اسحب لتحريك الخريطة · العجلة أو إصبعان للتكبير', loading: 'جارٍ تحميل الآيات من Quran.com…',
    offline: 'تعذّر الاتصال بموقع Quran.com. تأكّد من الاتصال بالإنترنت ثم أعد المحاولة.', noAudio: 'لا يتوفّر تسجيل لهذا القارئ لهذه الآيات. جرّب قارئًا آخر من الإعدادات.',
    audioErr: 'تعذّر تشغيل التلاوة.', tapToPlay: 'اضغط «إعادة المحاولة» لتشغيل التلاوة.', retry: 'إعادة المحاولة', skip: 'تخطٍّ', reciting: 'القارئ',
    verse: 'الآية', of: 'من', tafsir: 'التفسير الميسّر', translation: 'Saheeh International', sources: 'المصادر', building: 'نبني العالم…', you: 'أنت',
    voiceDl: 'نجهّز صوت الشخصيات العربي لأول مرة', voiceReady: 'صوت الشخصيات جاهز', voiceFail: 'تعذّر تحميل الصوت العربي — سيظهر الكلام مكتوبًا.', quality: 'جودة الرسوم', qAuto: 'تلقائي', close: 'إغلاق', partOf: 'جزء من الآية', simple: 'شرح مبسّط', noVoice: 'لا يوجد صوت عربي مثبّت في المتصفح — سيظهر الكلام مكتوبًا.', showPath: 'إظهار الطريق إلى القصة التالية', combo: 'رائع!',
    walk: 'امشِ إلى القصة', stories: 'القصص', storiesSub: 'اختر القصة التي تريد أن تذهب إليها — أي قصة تحبّ!', stDone: 'أنهيتها', stOpen: 'متاحة', stLocked: 'لم تُفتح بعد', stCurrent: 'وجهتك الآن', headingTo: 'وجهتك', surah: 'سورة', meters: 'م', mapPick: 'اضغط على علامة قصة لتذهب إليها', walkStuck: 'تعذّر إكمال الطريق — امشِ قليلًا ثم جرّب مرة أخرى', controlsTouch: 'اسحب يسار لتمشي · اسحب يمين لتلفّ الكاميرا · 👣 يمشي بك إلى القصة',
  },
  en: {
    title: 'Quran Journey', alt: 'رحلة القرآن', tagline: 'Explore · Listen · Learn · Grow', tagline2: 'استكشف · استمع · تعلّم · انمُ', cont: 'Continue', newGame: 'New Journey', settings: 'Settings',
    talk: 'Talk', journal: 'Knowledge Book', map: 'Explore the World', mapSub: 'Discover more Quranic stories', unlocked: 'Knowledge Unlocked!', unlockedAlt: 'فتحتَ كنزًا من المعرفة', lesson: 'What do we learn?', here: 'You are here',
    points: 'Knowledge Points', continue: 'Continue', nextStory: 'Next story available', discovered: 'Discovered', explore: 'Explore the world',
    exploreSub: 'More stories coming soon, in sha Allah', soon: 'Coming soon', empty: 'No stories unlocked yet. Walk around and talk to the villagers!',
    listenAgain: 'Listen again', lang: 'Language', reciter: 'Reciter', voice: 'Character voices (speech synthesis)', meaning: 'Show meaning under the verse', auto: 'Auto-advance dialogue',
    volume: 'Nature sounds', music: 'Soft pad (off by default)', reset: 'Reset progress', resetQ: 'Erase all progress?',
    controls: 'Walk with WASD / arrows · F walks you to the story · drag to look · tap the ground to walk there · wheel, + / − or pinch to zoom out and fly up', zoomIn: 'Zoom in', zoomOut: 'Zoom out (bird\'s-eye)', centerMe: 'Center on me', mapZoom: 'Drag to move the map · wheel or pinch to zoom', loading: 'Loading verses from Quran.com…',
    offline: 'Could not reach Quran.com. Check your internet connection and try again.', noAudio: 'This reciter has no recording for these verses. Try another reciter in Settings.',
    audioErr: 'The recitation could not be played.', tapToPlay: 'Press “Try again” to start the recitation.', retry: 'Try again', skip: 'Skip', reciting: 'Reciting',
    verse: 'Verse', of: 'of', tafsir: 'Tafsir al-Muyassar', translation: 'Saheeh International', sources: 'Sources', building: 'Building the world…', you: 'You',
    voiceDl: 'Preparing the Arabic character voice (first time only)', voiceReady: 'Character voice ready', voiceFail: 'Could not load the Arabic voice — lines will show as text.', quality: 'Graphics quality', qAuto: 'Auto', close: 'Close', partOf: 'Part of verse', simple: 'Simple explanation', noVoice: 'No English voice installed — lines will show as text.', showPath: 'Show the path to the next story', combo: 'Great!',
    walk: 'Walk to the story', stories: 'Stories', storiesSub: 'Choose the story you want to go to — any one you like!', stDone: 'Done', stOpen: 'Open', stLocked: 'Not yet', stCurrent: 'Heading here', headingTo: 'Heading to', surah: 'Surah', meters: 'm', mapPick: 'Tap a story marker to go there', walkStuck: 'Couldn’t finish the walk — move a little and try again', controlsTouch: 'Drag on the left to walk · drag on the right to turn the camera · 👣 walks you to the story',
  },
};

const $ = id => document.getElementById(id);
// surah names for the verse references on the story cards (fallback: the number)
const SURAHS = { 2: ['البقرة', 'Al-Baqarah'], 12: ['يوسف', 'Yusuf'], 59: ['الحشر', 'Al-Hashr'], 105: ['الفيل', 'Al-Fil'], 106: ['قريش', 'Quraysh'] };
const arDigits = n => String(n).replace(/\d/g, d => '٠١٢٣٤٥٦٧٨٩'[d]);
// the painted illustration that stands for a story on its card: its first painted scene, else a stand-in
const THUMBS = { 'people-of-the-elephant': 'elephant', 'the-guest-and-the-lamp': 'guest_meal' };   // a painting that reads better small
const storyThumb = e => THUMBS[e.id] ?? e.steps.map(s => s.scene).find(n => PAINTED.includes(n)) ?? null;
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
    const alt = $('title').querySelector('.alt'); if (alt) alt.textContent = S.alt;
    const tg2 = $('title').querySelector('.tagline2'); if (tg2) tg2.textContent = S.tagline2;
    const lesson = document.querySelector('#dialogue .lesson span'); if (lesson) lesson.textContent = S.lesson;
    $('btn-continue').textContent = S.cont; $('btn-new').textContent = S.newGame; $('btn-settings').textContent = S.settings;
    $('talk').querySelector('span').textContent = S.talk;
    for (const b of $('dock').children) b.title = S[b.dataset.open === 'settings' ? 'settings' : b.dataset.open];
    $('walk').title = S.walk; $('walk').setAttribute('aria-label', S.walk);
    for (const b of document.querySelectorAll('#zoom button[data-zoom]')) { b.title = S[b.dataset.zoom === 'in' ? 'zoomIn' : 'zoomOut']; b.setAttribute('aria-label', b.title); }
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
  // walk-to-the-story button: shown while a guided route exists, gold while walking
  walkButton(show, on) {
    const b = $('walk');
    if (b.hidden === show) b.hidden = !show;
    if (b.classList.contains('on') !== on) { b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); }
  }
  // ---- coin pickups: a coin flies in an arc to the points pill, "+1" floats up ----------------
  fxHost() { return (this._fx ??= document.body.appendChild(Object.assign(document.createElement('div'), { id: 'fx' }))); }
  bumpPoints() { const p = $('points'); p.classList.remove('bump'); void p.offsetWidth; p.classList.add('bump'); }
  coinFly(sx, sy, big = false) {
    const host = this.fxHost(), el = (this._pool ??= []).pop() ?? document.createElement('i');
    el.className = big ? 'fly big' : 'fly'; host.append(el);
    const r = $('points').querySelector('.ico').getBoundingClientRect(), tx = r.left + r.width / 2, ty = r.top + r.height / 2;
    const cx = (sx + tx) / 2, cy = Math.min(sy, ty) - 90, frames = [];
    for (let k = 0; k <= 8; k++) {
      const t = k / 8, u = 1 - t, x = u * u * sx + 2 * u * t * cx + t * t * tx, y = u * u * sy + 2 * u * t * cy + t * t * ty;
      frames.push({ transform: `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) scale(${(1.15 - 0.6 * t).toFixed(2)}) rotateY(${Math.round(t * 720)}deg)`, opacity: t > 0.92 ? 0.6 : 1 });
    }
    const a = el.animate(frames, { duration: big ? 800 : 620, easing: 'cubic-bezier(.4,.1,.8,.7)' });
    a.onfinish = () => { el.remove(); this._pool.push(el); this.setPoints(); this.bumpPoints(); };
  }
  floatText(sx, sy, text, big = false) {
    const el = document.createElement('b'); el.className = big ? 'plus big' : 'plus'; el.textContent = text; el.dir = 'auto';
    this.fxHost().append(el);
    const at = (dy, s) => `translate(${sx.toFixed(1)}px, ${(sy + dy).toFixed(1)}px) translate(-50%, -50%) scale(${s})`;
    el.animate([{ transform: at(0, 0.5), opacity: 0 }, { transform: at(-14, 1.15), opacity: 1, offset: 0.2 }, { transform: at(-56, 1), opacity: 0 }],
      { duration: big ? 1300 : 900, easing: 'ease-out' }).onfinish = () => el.remove();
  }
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
    b.hidden = false;
    // keep the whole bubble on screen (phones): slide it in and point the tail at the speaker
    const half = Math.min(b.offsetWidth, innerWidth - 16) / 2 + 8, x = Math.min(Math.max(screen.x, half), innerWidth - half);
    b.style.setProperty('--ax', `${Math.max(-half + 22, Math.min(half - 22, screen.x - x)).toFixed(0)}px`);
    b.style.transform = `translate(${x}px, ${screen.y}px) translate(-50%, -100%)`;
  }
  letterbox(on) { document.body.classList.toggle('cinema', on); }
  deep(on) { document.body.classList.toggle('deep', on); }

  // Compass-style minimap: rotates with the camera, north marker on the ring.
  minimap(player, npcs, route = null, from = 0) {
    const ctx = this.mini, size = ctx.canvas.width, c = size / 2, map = this.mapCanvas, n = map.width;
    const k = 2.4 * (size / 180) / (n / 520);      // ~2.4 px per metre
    const [px, py] = toMap(player.pos.x, player.pos.z, n);
    const rot = -Math.PI / 2 - Math.atan2(Math.cos(player.yaw), -Math.sin(player.yaw));
    ctx.clearRect(0, 0, size, size);
    ctx.save(); ctx.beginPath(); ctx.arc(c, c, c - 2, 0, Math.PI * 2); ctx.clip();
    ctx.fillStyle = '#c9a877'; ctx.fillRect(0, 0, size, size);
    ctx.translate(c, c); ctx.rotate(rot); ctx.scale(k, k); ctx.translate(-px, -py);
    ctx.imageSmoothingEnabled = true; ctx.drawImage(map, 0, 0);
    if (route && from < route.n - 2) {                // the guided path: a dashed gold line flowing toward the story
      const m = n / SIZE;
      ctx.beginPath(); ctx.moveTo((route.x[from] + HALF) * m, (HALF - route.z[from]) * m);
      for (let i = from + 3; i < route.n; i += 3) ctx.lineTo((route.x[i] + HALF) * m, (HALF - route.z[i]) * m);
      ctx.lineTo((route.x[route.n - 1] + HALF) * m, (HALF - route.z[route.n - 1]) * m);
      ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      ctx.setLineDash([]); ctx.strokeStyle = 'rgba(43, 26, 16, .8)'; ctx.lineWidth = 7 / k; ctx.stroke();
      ctx.setLineDash([7 / k, 5 / k]); ctx.lineDashOffset = -(performance.now() / 1000) * 14 / k;
      ctx.strokeStyle = '#ffd23f'; ctx.lineWidth = 4 / k; ctx.stroke(); ctx.setLineDash([]);
    }
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
    const mm = $('minimap'), ring = mm.querySelector('.ring');
    if (ring && !ring.dataset.built) {             // cardinal ticks: every 15°, long + gold on the cardinals
      ring.dataset.built = 1;
      ring.querySelector('.ticks').innerHTML = Array.from({ length: 24 }, (_, i) => {
        const a = i * Math.PI / 12, major = i % 6 === 0, r0 = major ? 40 : 44.5, r1 = 48.5;
        return `<line class="${major ? 'major' : ''}" x1="${50 + Math.sin(a) * r0}" y1="${50 - Math.cos(a) * r0}" x2="${50 + Math.sin(a) * r1}" y2="${50 - Math.cos(a) * r1}" stroke-width="${major ? 2 : 1}"/>`;
      }).join('');
    }
    if (ring) ring.style.transform = `rotate(${rot}rad)`;
    if (ring) for (const t of ring.querySelectorAll('.cards text')) t.setAttribute('transform', `rotate(${(-rot * 180 / Math.PI).toFixed(1)} ${t.getAttribute('x')} ${t.getAttribute('y')})`);
    const half = mm.clientWidth / 2 || c, a = -Math.PI / 2 + rot, r = half - 4;
    mm.querySelector('.n').style.transform = `translate(${half + Math.cos(a) * r}px, ${half + Math.sin(a) * r}px) translate(-50%, -50%)`;
  }

  // ---- panels -----------------------------------------------------------
  openPanel(title, body) {
    const p = $('panel'); p.hidden = false; p.querySelector('h2').textContent = title;
    const b = p.querySelector('.body'); b.innerHTML = ''; b.append(body);
    requestAnimationFrame(() => p.classList.add('show'));
    p.onclick = e => { if (e.target === p) this.closePanel?.(); };                // tap outside the sheet closes it
    return new Promise(res => { this.closePanel = () => { p.classList.remove('show'); setTimeout(() => { p.hidden = true; }, 250); this.closePanel = null; res(); }; p.querySelector('.x').onclick = () => this.closePanel(); });
  }

  // Painted world map (public/ui/world-map.webp) with region pins, story markers and the live
  // player arrow on top. Falls back to the terrain colour map if the painting can't load.
  worldMap(player, npcs, route = null, from = 0, onPick = null) {
    const S = this.S, lang = this.save.settings.lang, wrap = document.createElement('div'); wrap.className = 'worldmap';
    const stage = document.createElement('div'); stage.className = 'stage'; wrap.append(stage);
    const img = new Image(); img.alt = ''; img.decoding = 'async'; img.draggable = false; img.src = asset('ui/world-map.webp');
    img.onerror = () => {                             // fallback: crop the live terrain map to the same rectangle
      const cv = document.createElement('canvas'); cv.width = 1400; cv.height = 1000;
      const n = this.mapCanvas.width, [sx, sy] = toMap(MAP_X0, MAP_Z1, n), [ex, ey] = toMap(MAP_X1, MAP_Z0, n);
      const ctx = cv.getContext('2d'); ctx.fillStyle = '#6f8a3c'; ctx.fillRect(0, 0, 1400, 1000);
      ctx.drawImage(this.mapCanvas, sx, sy, ex - sx, ey - sy, 0, 0, 1400, 1000); img.replaceWith(cv);
    };
    // zoom + pan: the painting sits in a scaled layer; markers stay in the unscaled stage
    // (so pins and labels keep their size) and are re-positioned from their map percentages
    const layer = document.createElement('div'); layer.className = 'layer'; layer.append(img); stage.append(layer);
    let routeG = null;                                // the guided path, dashed gold (same transform as the painting)
    if (route && from < route.n - 2) {
      const NS = 'http://www.w3.org/2000/svg', svg = document.createElementNS(NS, 'svg');
      svg.setAttribute('class', 'route'); svg.setAttribute('viewBox', '0 0 100 100'); svg.setAttribute('preserveAspectRatio', 'none');
      let d = '';
      for (let i = from; i < route.n; i += 4) { const [l, t] = mapPct(route.x[i], route.z[i]); d += `${d ? 'L' : 'M'}${l.toFixed(2)} ${t.toFixed(2)}`; }
      const [el, et] = mapPct(route.x[route.n - 1], route.z[route.n - 1]); d += `L${el.toFixed(2)} ${et.toFixed(2)}`;
      routeG = document.createElementNS(NS, 'g');
      routeG.innerHTML = `<path class="ink" d="${d}" vector-effect="non-scaling-stroke"/><path class="dash" d="${d}" vector-effect="non-scaling-stroke"/>`;
      svg.append(routeG); stage.append(svg);
    }
    const marks = [];
    const place = (el, x, z, clampY = 0) => { const [l, t] = mapPct(x, z); el._p = [Math.min(97, Math.max(3, l)), Math.min(92, Math.max(clampY, t))]; marks.push(el); return el; };
    const here = this.data.areas.find(a => Math.hypot(a.x - player.pos.x, a.z - player.pos.z) < a.r);
    for (const a of this.data.areas) {
      const known = this.save.discovered.includes(a.id), R = REGIONS[a.id], hasStory = this.data.encounters.some(e => e.area === a.id);
      const name = R ? R[lang] : this.t(a), other = R ? R[lang === 'ar' ? 'en' : 'ar'] : '';
      const pin = document.createElement('div'); pin.className = `pin${known ? '' : ' unknown'}${here === a ? ' here' : ''}`;
      pin.innerHTML = `<svg class="p" viewBox="0 0 44 56" aria-hidden="true"><use href="#o-pin"/></svg>
        <svg class="g" aria-hidden="true"><use href="#${known ? `r-${R?.g ?? 'village'}` : 'i-lock'}"/></svg>
        <span class="lbl">${known ? esc(name) + (hasStory ? '' : `<span class="soon"> · ${esc(S.soon)}</span>`) : '؟'}${known && other ? `<small>${esc(other)}</small>` : ''}</span>`;
      const [px] = mapPct(a.x, a.z); if (px < 18) pin.classList.add('edge-l'); if (px > 82) pin.classList.add('edge-r');
      stage.append(place(pin, a.x, a.z, 11));
    }
    for (const npc of npcs) {
      const m = document.createElement(onPick ? 'button' : 'div'); m.className = `npc badge ${npc.state}`;
      m.innerHTML = icon(npc.state === 'open' ? 'alert' : npc.state === 'done' ? 'check' : 'lock');
      if (onPick) {                                   // tap a story marker: go there (like the story picker)
        m.type = 'button'; m.title = this.t(npc.enc.title); m.setAttribute('aria-label', m.title);
        m.addEventListener('pointerdown', e => e.stopPropagation());   // not a map drag
        m.onclick = () => { onPick(npc.enc.id); this.closePanel?.(); };
      }
      stage.append(place(m, npc.x, npc.z));
    }
    const me = document.createElement('div'); me.className = 'me'; me.title = S.here;
    const heading = Math.atan2(-Math.cos(player.facing), Math.sin(player.facing)) + Math.PI / 2;
    me.innerHTML = `<svg viewBox="-20 -20 40 40" style="transform:rotate(${heading}rad)"><circle r="17" fill="#0f2a33" fill-opacity=".55" stroke="#f4c766" stroke-width="2"/><path d="M0-13L10 10 0 5-10 10z" fill="#fff" stroke="#1e4f73" stroke-width="2.5" stroke-linejoin="round"/></svg>`;
    stage.append(place(me, player.pos.x, player.pos.z));

    const view = { s: 1, x: 0, y: 0 }, MAXS = 5;             // scale, offset (in % of the stage)
    const layout = (ease = false) => {
      view.s = Math.min(MAXS, Math.max(1, view.s));
      view.x = Math.min(0, Math.max(100 * (1 - view.s), view.x)); view.y = Math.min(0, Math.max(100 * (1 - view.s), view.y));
      stage.classList.toggle('ease', ease); stage.classList.toggle('zoomed', view.s > 1.01);
      layer.style.transform = `translate(${view.x}%, ${view.y}%) scale(${view.s})`;
      if (routeG) routeG.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.s})`;
      for (const el of marks) { el.style.left = `${view.x + el._p[0] * view.s}%`; el.style.top = `${view.y + el._p[1] * view.s}%`; }
      tools.querySelector('[data-z="out"]').disabled = view.s <= 1.01; tools.querySelector('[data-z="in"]').disabled = view.s >= MAXS - 0.01;
    };
    const zoomAt = (k, cx = 50, cy = 50, ease = false) => {     // keep the map point under (cx, cy) fixed
      const s1 = Math.min(MAXS, Math.max(1, view.s * k)), r = s1 / view.s;
      view.x = cx - (cx - view.x) * r; view.y = cy - (cy - view.y) * r; view.s = s1; layout(ease);
    };
    const centerOnMe = () => { view.s = Math.max(view.s, 2.5); view.x = 50 - me._p[0] * view.s; view.y = 50 - me._p[1] * view.s; layout(true); };
    const pct = (cx, cy) => { const r = stage.getBoundingClientRect(); return [(cx - r.left) / r.width * 100, (cy - r.top) / r.height * 100, r]; };
    const tools = document.createElement('div'); tools.className = 'tools';
    tools.innerHTML = `<button type="button" data-z="in" title="${esc(S.zoomIn)}" aria-label="${esc(S.zoomIn)}">${icon('zoom-in')}</button>
      <button type="button" data-z="out" title="${esc(S.zoomOut)}" aria-label="${esc(S.zoomOut)}">${icon('zoom-out')}</button>
      <button type="button" data-z="me" title="${esc(S.centerMe)}" aria-label="${esc(S.centerMe)}">${icon('locate')}</button>`;
    tools.onclick = e => { const b = e.target.closest('button'); if (!b) return; const z = b.dataset.z;
      if (z === 'me') centerOnMe(); else zoomAt(z === 'in' ? 1.6 : 1 / 1.6, 50, 50, true); };
    tools.addEventListener('pointerdown', e => e.stopPropagation());
    tools.addEventListener('dblclick', e => e.stopPropagation());
    stage.append(tools);
    stage.addEventListener('wheel', e => {
      e.preventDefault();
      const [cx, cy] = pct(e.clientX, e.clientY), d = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1);
      zoomAt(Math.exp(-Math.max(-300, Math.min(300, d)) * (e.ctrlKey ? 0.012 : 0.0022)), cx, cy);
    }, { passive: false });
    stage.addEventListener('dblclick', e => { const [cx, cy] = pct(e.clientX, e.clientY); if (view.s >= MAXS - 0.01) { view.s = 1; layout(true); } else zoomAt(2, cx, cy, true); });
    const pts = new Map(); let pinch = null;
    const mid = () => { const [a, b] = [...pts.values()]; return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, d: Math.hypot(a.x - b.x, a.y - b.y) || 1 }; };
    stage.addEventListener('pointerdown', e => {
      pts.set(e.pointerId, { x: e.clientX, y: e.clientY }); try { stage.setPointerCapture(e.pointerId); } catch { /* ignore */ }
      if (pts.size === 2) pinch = mid();
      stage.classList.add('drag'); stage.classList.remove('ease');
    });
    stage.addEventListener('pointermove', e => {
      const p = pts.get(e.pointerId); if (!p) return;
      const r = stage.getBoundingClientRect();
      if (pts.size >= 2 && pinch) {
        p.x = e.clientX; p.y = e.clientY;
        const m = mid(), [cx, cy] = pct(m.x, m.y);
        view.x += (m.x - pinch.x) / r.width * 100; view.y += (m.y - pinch.y) / r.height * 100;
        zoomAt(m.d / pinch.d, cx, cy); pinch = m; return;
      }
      view.x += (e.clientX - p.x) / r.width * 100; view.y += (e.clientY - p.y) / r.height * 100;
      p.x = e.clientX; p.y = e.clientY; layout();
    });
    const lift = e => { pts.delete(e.pointerId); if (pts.size < 2) pinch = null; if (!pts.size) stage.classList.remove('drag'); };
    stage.addEventListener('pointerup', lift); stage.addEventListener('pointercancel', lift);
    layout();
    const sub = document.createElement('p'); sub.className = 'sub'; sub.innerHTML = `${esc(S.mapSub)}<small>${esc(S.mapZoom)}${onPick ? ` · ${esc(S.mapPick)}` : ''}</small>`; wrap.prepend(sub);
    return this.openPanel(S.map, wrap);
  }

  // Story picker: every story as a card (painting, title, storytellers, place, verses, status,
  // distance). Tapping one hands its id to onPick and closes the sheet.
  stories(player, npcs, current, onPick) {
    const S = this.S, lang = this.save.settings.lang, ar = lang === 'ar', wrap = document.createElement('div'); wrap.className = 'stories';
    const sub = document.createElement('p'); sub.className = 'sub'; sub.textContent = S.storiesSub; wrap.append(sub);
    const list = document.createElement('div'); list.className = 'st-list'; wrap.append(list);
    const num = n => (ar ? arDigits(n) : String(n));
    for (const e of this.data.encounters) {
      const npc = npcs.find(n => n.enc === e || n.enc.id === e.id); if (!npc) continue;
      const status = this.save.done.includes(e.id) ? 'done' : npc.state === 'locked' ? 'locked' : 'open';
      const v = e.steps.find(s => s.type === 'verses');
      let ref = '';
      if (v) {
        const [su, a0] = v.from.split(':'), a1 = v.to.split(':')[1], name = SURAHS[su]?.[ar ? 0 : 1];
        ref = `${S.surah} ${name ?? num(su)} ${num(a0)}${a1 !== a0 ? `–${num(a1)}` : ''}`;
      }
      const area = this.data.areas.find(a => a.id === e.area), R = REGIONS[e.area];
      const place = R ? R[lang] : this.t(area);
      const d = Math.hypot(npc.x - player.pos.x, npc.z - player.pos.z), dist = d < 15 ? num(Math.max(1, Math.round(d))) : num(Math.round(d / 10) * 10);
      const cast = e.characters ?? [e.character];
      const faces = cast.slice(0, 2).map(c => `<i class="face">${portrait(c.id, c)}</i>`).join('');
      const names = cast.map(c => esc(this.t(c.name))).join(' · ');
      const thumb = storyThumb(e);
      const other = e.title?.[ar ? 'en' : 'ar'];
      const b = document.createElement('button'); b.type = 'button';
      b.className = `story ${status}${e.id === current ? ' current' : ''}`;
      b.innerHTML = `<span class="thumb">${thumb ? `<img alt="" loading="lazy" decoding="async" src="${illustrationURL(thumb)}">` : ''}<svg class="orn" viewBox="0 0 200 124" aria-hidden="true"><use href="#o-emblem"/></svg></span>
        <span class="info"><b class="ttl">${esc(this.t(e.title))}</b>${other ? `<small class="alt" lang="${ar ? 'en' : 'ar'}">${esc(other)}</small>` : ''}
          <span class="who"><span class="faces">${faces}</span><span>${names}</span></span>
          <span class="meta"><span>${icon('compass')}${esc(place)}</span>${ref ? `<span>${icon('quran')}${esc(ref)}</span>` : ''}<span class="dist">≈ ${dist} ${esc(S.meters)}</span></span></span>
        <span class="st">${icon(status === 'done' ? 'check' : status === 'open' ? 'alert' : 'lock')}<em>${esc(e.id === current ? S.stCurrent : S[status === 'done' ? 'stDone' : status === 'open' ? 'stOpen' : 'stLocked'])}</em></span>`;
      const img = b.querySelector('img');
      if (img) { img.onload = () => b.querySelector('.thumb').classList.add('ok'); img.onerror = () => img.remove(); }
      b.onclick = () => { onPick(e.id); this.closePanel?.(); };
      list.append(b);
    }
    const p = this.openPanel(S.stories, wrap);
    requestAnimationFrame(() => list.querySelector('.current')?.scrollIntoView({ block: 'nearest' }));
    return p;
  }

  journal(onReplay) {
    const S = this.S, list = document.createElement('div'); list.className = 'journal';
    const done = this.data.encounters.filter(e => this.save.done.includes(e.id));
    if (!done.length) list.innerHTML = `<p class="empty">${esc(S.empty)}</p>`;
    for (const e of done) {
      const v = e.steps.find(s => s.type === 'verses'), card = document.createElement('article');
      card.innerHTML = `<div class="medal sm">${medalSVG()}</div><div><h3>${esc(this.t(e.title))}</h3>
        <p>${esc(this.t(e.character.name))} · ${esc(v.from === v.to ? v.from : `${v.from}–${v.to.split(':')[1]}`)}${v.words ? ` (${esc(S.partOf)})` : ''}</p>
        <small>${esc(S.sources)}: ${e.sources.map(esc).join(' · ')}</small></div><button>${icon('speaker')}${esc(S.listenAgain)}</button>`;
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
      <label>${esc(S.quality)}<select name="quality"><option value="auto">${esc(S.qAuto)}</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="ultra">Ultra</option></select></label>
      <label class="row"><input type="checkbox" name="voice"> ${esc(S.voice)}</label>
      <label class="row"><input type="checkbox" name="meaning"> ${esc(S.meaning)}</label>
      <label class="row"><input type="checkbox" name="auto"> ${esc(S.auto)}</label>
      <label class="row"><input type="checkbox" name="path"> ${esc(S.showPath)}</label>
      <label>${esc(S.volume)}<input type="range" name="volume" min="0" max="1" step="0.05"></label>
      <label class="row"><input type="checkbox" name="music"> ${esc(S.music)}</label>
      <button type="button" class="danger">${esc(S.reset)}</button>`;
    f.lang.value = st.lang; f.quality.value = st.quality ?? 'auto'; f.voice.checked = st.voice; f.meaning.checked = st.meaning; f.auto.checked = st.auto !== false; f.path.checked = st.path !== false; f.volume.value = st.volume; f.music.checked = st.music;
    QuranService.getReciters().then(rs => {
      f.reciter.innerHTML = rs.map(r => `<option value="${r.id}">${esc(r.name)}${r.style ? ' — ' + esc(r.style) : ''}</option>`).join('');
      f.reciter.value = st.reciter;
    }).catch(e => { f.reciter.innerHTML = `<option value="${st.reciter}">${esc(e.message)}</option>`; });
    f.onchange = () => {
      Object.assign(st, { lang: f.lang.value, reciter: +f.reciter.value, voice: f.voice.checked, meaning: f.meaning.checked, auto: f.auto.checked, path: f.path.checked, volume: +f.volume.value, music: f.music.checked, quality: f.quality.value });
      this.persist(); this.onSettings();
    };
    f.querySelector('.danger').onclick = () => { if (confirm(S.resetQ)) onReset(); };
    return this.openPanel(S.settings, f);
  }

  reward(enc) {
    const S = this.S, R = $('reward');
    R.querySelector('h2').textContent = S.unlocked;
    const k = R.querySelector('.kicker'); if (k) k.textContent = S.unlockedAlt;
    R.querySelector('p').textContent = this.t(enc.reward);
    R.querySelector('.pts').innerHTML = `${icon('star')}<b dir="ltr">+${esc(enc.reward.points)}</b> ${esc(S.points)}`;
    R.querySelector('button').textContent = S.continue;
    R.hidden = false; requestAnimationFrame(() => R.classList.add('show'));
    return new Promise(res => {
      const go = () => { removeEventListener('keydown', key); R.classList.remove('show'); setTimeout(() => { R.hidden = true; res(); }, 400); };
      const key = e => { if (e.code === 'Enter' || e.code === 'Space') { e.preventDefault(); go(); } };
      R.querySelector('button').onclick = go; addEventListener('keydown', key);
    });
  }
}

// Gold "Knowledge Unlocked" medal: scalloped rim, open book, star. Unique gradient ids per use.
let medalN = 0;
export const medalSVG = () => { const k = `m${++medalN}`; return `<svg viewBox="0 0 160 160" aria-hidden="true"><defs>
  <radialGradient id="${k}a" cx=".38" cy=".3" r=".8"><stop offset="0" stop-color="#fff4c8"/><stop offset=".45" stop-color="#f4c766"/><stop offset="1" stop-color="#b3741f"/></radialGradient>
  <linearGradient id="${k}b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe7a3"/><stop offset="1" stop-color="#a86a1c"/></linearGradient>
  <radialGradient id="${k}c" cx=".5" cy=".4" r=".7"><stop offset="0" stop-color="#1f5664"/><stop offset="1" stop-color="#0c2530"/></radialGradient>
  <linearGradient id="${k}d" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fffaf0"/><stop offset="1" stop-color="#f1dcae"/></linearGradient></defs>
  <path fill="url(#${k}b)" d="${Array.from({ length: 24 }, (_, i) => { const a = i / 24 * Math.PI * 2, r = i % 2 ? 70 : 76; return `${i ? 'L' : 'M'}${(80 + Math.sin(a) * r).toFixed(1)} ${(80 - Math.cos(a) * r).toFixed(1)}`; }).join('')}Z"/>
  <circle cx="80" cy="80" r="62" fill="url(#${k}a)" stroke="#fff0c0" stroke-opacity=".7" stroke-width="1.5"/>
  <circle cx="80" cy="80" r="51" fill="url(#${k}c)" stroke="#8a5a1c" stroke-width="2"/>
  <circle cx="80" cy="80" r="46" fill="none" stroke="#f4c766" stroke-opacity=".55" stroke-width="1" stroke-dasharray="2 4"/>
  <g stroke="#f4c766" stroke-opacity=".5" stroke-width="1.6" stroke-linecap="round">${Array.from({ length: 9 }, (_, i) => { const a = (-70 + i * 17.5) * Math.PI / 180; return `<path d="M${(80 + Math.sin(a) * 24).toFixed(1)} ${(78 - Math.cos(a) * 24).toFixed(1)}L${(80 + Math.sin(a) * 38).toFixed(1)} ${(78 - Math.cos(a) * 38).toFixed(1)}"/>`; }).join('')}</g>
  <path d="M46 70c11-5 23-4 34 3 11-7 23-8 34-3v36c-11-5-23-4-34 3-11-7-23-8-34-3z" fill="#7a4e17"/>
  <path d="M49 71c10-4 20-3 29 3v32c-9-6-19-7-29-3z M82 74c9-6 19-7 29-3v32c-10-4-20-3-29 3z" fill="url(#${k}d)"/>
  <path d="M54 79c7-2 13-1 19 2M54 86c7-2 13-1 19 2M54 93c7-2 13-1 19 2M87 81c6-3 12-4 19-2M87 88c6-3 12-4 19-2M87 95c6-3 12-4 19-2" stroke="#c9a46a" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M80 44l3.4 7.2 7.8.9-5.8 5.3 1.6 7.7L80 61.2l-7 3.9 1.6-7.7-5.8-5.3 7.8-.9z" fill="url(#${k}a)" stroke="#fff4c8" stroke-width="1"/>
  <path d="M44 52a44 44 0 0 1 26-22" fill="none" stroke="#fff8e0" stroke-opacity=".75" stroke-width="3" stroke-linecap="round"/></svg>`; };
export const MEDAL = medalSVG();
