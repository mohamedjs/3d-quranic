// The Quran experience: verse text, recorded recitation, word-by-word highlighting.
// Text and audio come only from QuranService. Nothing here is spoken by TTS.
import { QuranService } from './quran.js';

const SILENT = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=';
export const audio = new Audio();
audio.preload = 'auto';
// Called from the start tap so later play() calls are allowed (iOS needs the same element).
export function primeAudio() { audio.src = SILENT; audio.play().catch(() => {}); }

const fmt = s => (isFinite(s) ? `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}` : '0:00');
const PLAY = '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
const PAUSE = '<svg viewBox="0 0 24 24"><path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>';

export function playRecitation({ from, to }, { reciter, lang, meaning, S }) {
  const R = document.getElementById('quran'), $ = s => R.querySelector(s);
  const text = $('.q-text'), msg = $('.q-msg'), toggle = $('.q-toggle');
  R.hidden = false; R.dir = lang === 'ar' ? 'rtl' : 'ltr';
  requestAnimationFrame(() => R.classList.add('show'));
  msg.hidden = true; text.textContent = S.loading; text.classList.add('loading');
  $('.q-meaning').textContent = ''; $('.q-src').textContent = ''; $('.q-dots').innerHTML = ''; $('.q-progress i').style.width = '0';
  $('.q-retry').textContent = S.retry; $('.q-giveup').textContent = S.skip; $('.q-skip').title = S.skip;

  let verses = [], i = 0, raf = 0, done = false, spans = [], lastWord = -1;
  const preloader = new Audio(); preloader.preload = 'auto';

  return new Promise(resolve => {
    const finish = () => {
      if (done) return; done = true;
      cancelAnimationFrame(raf); audio.pause(); audio.onended = audio.onerror = audio.onplay = audio.onpause = null;
      R.classList.remove('show'); setTimeout(() => { R.hidden = true; resolve(); }, 700);
    };
    const fail = m => { audio.pause(); msg.hidden = false; msg.querySelector('p').textContent = m; };
    $('.q-retry').onclick = () => { msg.hidden = true; verses.length ? playVerse(i) : load(); };
    $('.q-giveup').onclick = finish; $('.q-skip').onclick = finish;
    toggle.onclick = () => (audio.paused ? audio.play().catch(() => {}) : audio.pause());
    $('.q-replay').onclick = () => verses.length && playVerse(0);
    audio.onplay = () => { toggle.innerHTML = PAUSE; }; audio.onpause = () => { toggle.innerHTML = PLAY; };
    audio.onended = () => {
      if (done) return;
      if (i + 1 < verses.length) setTimeout(() => !done && playVerse(i + 1), 450);
      else { spans.forEach(s => s.classList.add('read')); setTimeout(finish, 1600); }
    };
    audio.onerror = () => { if (!done && verses.length && audio.src !== SILENT) fail(`${S.audioErr} (${audio.error?.message || audio.src})`); };

    async function load() {
      try {
        const surahNo = +from.split(':')[0];
        const [surah, vs, reciters] = await Promise.all([
          QuranService.getSurah(surahNo), QuranService.getVerses(from, to, reciter), QuranService.getReciters().catch(() => []),
        ]);
        verses = vs;
        $('.q-surah').textContent = `سورة ${surah.nameArabic}`;
        $('.q-sub').textContent = `Surah ${surah.nameSimple} · ${surah.nameTranslated}`;
        const rc = reciters.find(r => r.id === reciter);
        $('.q-reciter').textContent = `${S.reciting}: ${rc ? rc.name + (rc.style ? ` (${rc.style})` : '') : '#' + reciter}`;
        $('.q-dots').innerHTML = verses.map(() => '<i></i>').join('');
        if (!verses.every(v => v.audioUrl)) return fail(S.noAudio);
        playVerse(0); tick();
      } catch (e) { fail(`${S.offline}\n${e.message}`); }
    }

    function render(k) {
      const v = verses[k];
      text.classList.remove('loading'); text.textContent = '';
      spans = v.words.map((w, n) => {
        const s = document.createElement('span'); s.className = 'w'; s.textContent = w;
        text.append(s); if (n < v.words.length - 1) text.append(' ');
        return s;
      });
      const end = document.createElement('span'); end.className = 'ayah-end'; end.textContent = v.end;
      text.append(' ', end);
      text.classList.toggle('whole', !v.timing.length);
      text.classList.remove('enter'); void text.offsetWidth; text.classList.add('enter');
      $('.q-vno').textContent = `${S.verse} ${v.verse} · ${k + 1} ${S.of} ${verses.length}`;
      [...$('.q-dots').children].forEach((d, n) => { d.className = n < k ? 'done' : n === k ? 'on' : ''; });
      const m = $('.q-meaning'), src = $('.q-src');
      m.textContent = ''; src.textContent = '';
      if (!meaning) return;
      if (lang === 'en') { m.textContent = `“${v.translation}”`; src.textContent = `${S.translation} · ${v.key}`; }
      else QuranService.getTafsir(v.key).then(t => { if (verses[i] === v) { m.textContent = t.text; src.textContent = `${S.tafsir} · ${v.key}`; } }).catch(() => {});
      lastWord = -1;
    }

    function playVerse(k) {
      i = k; render(k); msg.hidden = true;
      audio.src = verses[k].audioUrl; audio.currentTime = 0;
      audio.play().catch(e => fail(e.name === 'NotAllowedError' ? S.tapToPlay : `${S.audioErr} (${e.message})`));
      const next = verses[k + 1]; if (next) preloader.src = next.audioUrl;
    }

    function tick() {
      raf = requestAnimationFrame(tick);
      const v = verses[i]; if (!v) return;
      const t = audio.currentTime * 1000, dur = audio.duration;
      text.classList.toggle('playing', !audio.paused);
      if (v.timing.length) {
        let w = lastWord;
        for (const seg of v.timing) if (t >= seg.from && t < seg.to) { w = seg.word; break; }
        if (w !== lastWord) { spans.forEach((s, n) => { s.classList.toggle('on', n === w); s.classList.toggle('read', n < w); }); lastWord = w; }
      }
      const f = isFinite(dur) && dur > 0 ? audio.currentTime / dur : 0;
      $('.q-progress i').style.width = `${((i + f) / verses.length) * 100}%`;
      $('.q-time').textContent = `${fmt(audio.currentTime)} / ${fmt(dur)}`;
    }

    load();
  });
}
// exposed for the self-check in the browser console
window.__recitation = { audio };
