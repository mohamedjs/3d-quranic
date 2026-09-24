// QuranService — the only module that talks to the Quran source (Quran.com API v4).
// No Quran text or audio is hard-coded anywhere in the game: encounters reference verse
// keys only, and everything shown or played is fetched from here.
export const API = 'https://api.quran.com/api/v4';
const AUDIO_CDN = 'https://verses.quran.com/';
export const DEFAULT_RECITER = 9;  // Mohamed Siddiq al-Minshawi — Murattal
export const TRANSLATION_EN = 20;  // Saheeh International
export const TAFSIR_AR = 16;       // Tafsir al-Muyassar

const cache = new Map();
function get(path) {
  if (!cache.has(path)) {
    cache.set(path, fetch(API + path).then(async r => {
      if (!r.ok) throw new Error(`Quran.com ${r.status} ${r.statusText}: ${path}`);
      return r.json();
    }).catch(e => { cache.delete(path); throw e; }));
  }
  return cache.get(path);
}

// API HTML (footnote <sup>, tafsir <span>) → plain text. Never injected as HTML.
const plain = html => {
  const d = new DOMParser().parseFromString(html, 'text/html');
  d.querySelectorAll('sup').forEach(s => s.remove());
  return d.body.textContent.replace(/\s+/g, ' ').trim();
};
const absolute = u => /^https?:/.test(u) ? u : u.startsWith('//') ? 'https:' + u : AUDIO_CDN + u;

// Per-verse word timings. Quran.com returns [wordIdx, wordIdx + 1, startMs, endMs] (0-based),
// some reciters [position, startMs, endMs] (1-based), some nothing. Anything unrecognised
// yields [] and the player falls back to highlighting the whole verse.
export function normalizeSegments(segs, nWords) {
  if (!Array.isArray(segs)) return [];
  const out = [];
  for (const s of segs) {
    if (!Array.isArray(s)) continue;
    if (s.length === 4) out.push({ word: s[0], from: s[2], to: s[3] });
    else if (s.length === 3) out.push({ word: s[0] - 1, from: s[1], to: s[2] });
  }
  return out.filter(t => Number.isInteger(t.word) && t.word >= 0 && t.word < nWords && t.to > t.from);
}

export function verseKeys(from, to = from) {
  const [s, a] = from.split(':').map(Number), [s2, b] = to.split(':').map(Number);
  if (s !== s2 || !(a >= 1) || !(b >= a)) throw new Error(`Bad verse range ${from}–${to}`);
  return Array.from({ length: b - a + 1 }, (_, i) => `${s}:${a + i}`);
}

export const QuranService = {
  async getReciters() {
    const j = await get('/resources/recitations?language=en');
    return j.recitations.map(r => ({ id: r.id, name: r.translated_name?.name || r.reciter_name, style: r.style }));
  },
  async getSurah(n) {
    const j = await get(`/chapters/${n}?language=en`);
    const c = j.chapter;
    return { number: c.id, nameArabic: c.name_arabic, nameSimple: c.name_simple, nameTranslated: c.translated_name?.name, verses: c.verses_count, place: c.revelation_place };
  },
  async getVerse(key, reciter = DEFAULT_RECITER) {
    const j = await get(`/verses/by_key/${key}?words=true&word_fields=text_uthmani&fields=text_uthmani&translations=${TRANSLATION_EN}&audio=${reciter}`);
    const v = j.verse, words = v.words.filter(w => w.char_type_name === 'word').map(w => w.text_uthmani);
    return {
      key: v.verse_key, surah: +key.split(':')[0], verse: v.verse_number, arabicText: v.text_uthmani, words,
      end: v.words.find(w => w.char_type_name === 'end')?.text_uthmani ?? String(v.verse_number),
      translation: v.translations?.[0] ? plain(v.translations[0].text) : '',
      audioUrl: v.audio?.url ? absolute(v.audio.url) : null,
      timing: normalizeSegments(v.audio?.segments, words.length), reciter,
    };
  },
  getVerses(from, to, reciter) { return Promise.all(verseKeys(from, to).map(k => this.getVerse(k, reciter))); },
  async getVerseAudio(key, reciter) { const v = await this.getVerse(key, reciter); return { url: v.audioUrl, timing: v.timing }; },
  async getChapterAudio(n, reciter = DEFAULT_RECITER) {
    const f = (await get(`/chapter_recitations/${reciter}/${n}?segments=true`)).audio_file;
    return { url: f.audio_url, verseTimings: (f.timestamps || []).map(t => ({ key: t.verse_key, from: t.timestamp_from, to: t.timestamp_to })) };
  },
  async getTafsir(key, id = TAFSIR_AR) {
    const t = (await get(`/tafsirs/${id}/by_ayah/${key}`)).tafsir;
    return { name: t.translated_name?.name || t.resource_name, text: plain(t.text) };
  },
};
