// Story progression: categories, the chain inside each category, difficulty and the coin gate.
// encounters.json may carry `categories: [{id, title, icon}]` and per-story `category` / `order`;
// without them every story is in "quran" and the order is the file order.
import * as THREE from 'three';

// share of a story's coin set the child collects before the story opens
export const DIFFICULTY = { easy: 0.2, medium: 0.5, hard: 0.9 };
export const DIFF_KEYS = ['easy', 'medium', 'hard'];
export const needFor = (total, diff) => (total ? Math.max(1, Math.ceil((DIFFICULTY[diff] ?? DIFFICULTY.easy) * total - 1e-9)) : 0);

const DEFAULT_TITLES = {
  quran: { ar: 'قصص من القرآن', en: 'Stories from the Quran' },
  prophets: { ar: 'قصص الأنبياء', en: 'Stories of the Prophets' },
  companions: { ar: 'قصص الصحابة', en: 'Stories of the Companions' },
};
// sprite icon for a category: its own `icon` if the sprite has it, else guessed from the id
export function categoryIcon(c) {
  const has = n => typeof document !== 'undefined' && !!document.getElementById(`i-${n}`);
  if (c.icon && /^[a-z0-9-]+$/.test(c.icon) && has(c.icon)) return { sprite: c.icon };
  if (c.icon && !/^[a-z0-9-]+$/.test(c.icon)) return { text: c.icon };           // an emoji
  const id = String(c.id).toLowerCase();
  if (/prophet|anbiya|nabi|rusul/.test(id)) return { sprite: 'prophets' };
  if (/compan|sahab/.test(id)) return { sprite: 'companions' };
  if (/quran/.test(id)) return { sprite: 'quran' };
  return { sprite: 'stories' };
}

export function createProgress({ data }) {
  const encs = data.encounters, byId = new Map(encs.map((e, i) => [e.id, { e, i }]));
  const catId = e => e.category ?? 'quran';
  const declared = Array.isArray(data.categories) ? data.categories.filter(c => c && c.id) : [];
  const categories = declared.map(c => ({ id: c.id, title: c.title ?? c.name ?? DEFAULT_TITLES[c.id] ?? { ar: c.id, en: c.id }, icon: c.icon, ids: [] }));
  for (const e of encs) {
    let c = categories.find(k => k.id === catId(e));
    if (!c) { c = { id: catId(e), title: DEFAULT_TITLES[catId(e)] ?? { ar: catId(e), en: catId(e) }, ids: [] }; categories.push(c); }
    c.ids.push(e.id);
  }
  const ord = id => { const { e, i } = byId.get(id); return [Number.isFinite(+e.order) && e.order !== null ? +e.order : 1e6, i]; };
  for (const c of categories) c.ids.sort((a, b) => { const [oa, ia] = ord(a), [ob, ib] = ord(b); return oa - ob || ia - ib; });
  const catOf = id => (byId.has(id) ? catId(byId.get(id).e) : null);
  const category = cid => categories.find(c => c.id === cid) ?? null;
  // the stories that must be done first — only ones of the same category (each category is its
  // own chain): the story's `requires` inside its category, else the one before it in `order`
  function prereq(id) {
    const e = byId.get(id)?.e; if (!e) return [];
    const c = category(catId(e)), same = (e.requires ?? []).filter(r => c.ids.includes(r) && r !== id);
    if (same.length) return same;
    if (Array.isArray(e.requires) && e.requires.length === 0) return [];
    const k = c.ids.indexOf(id);
    return k > 0 ? [c.ids[k - 1]] : [];
  }
  return { categories, catOf, category, prereq };
}

// The marker over a storyteller whose story still waits for coins: a padlock inside a gold
// progress ring, and a «12 / 20» pill with a coin under it. Redrawn only when the count changes.
const arDigits = n => String(n).replace(/\d/g, d => '٠١٢٣٤٥٦٧٨٩'[d]);
export function gateMarker() {
  const c = document.createElement('canvas'); c.width = c.height = 256;
  const x = c.getContext('2d'), tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  let last = '';
  function draw(g, lang) {
    const key = `${g?.have}/${g?.need}/${lang}`; if (key === last) return; last = key;
    const f = g ? Math.min(1, g.have / Math.max(1, g.need)) : 0;
    x.clearRect(0, 0, 256, 256);
    const glow = x.createRadialGradient(128, 92, 20, 128, 92, 96); glow.addColorStop(0, 'rgba(255,220,120,.7)'); glow.addColorStop(1, 'rgba(255,200,80,0)');
    x.fillStyle = glow; x.fillRect(0, 0, 256, 190);
    // ring: dark track, gold progress from the top, clockwise
    x.lineCap = 'round';
    x.beginPath(); x.arc(128, 92, 54, 0, Math.PI * 2); x.fillStyle = '#0f2a33'; x.fill();
    x.lineWidth = 16; x.strokeStyle = '#4a3a22'; x.beginPath(); x.arc(128, 92, 54, 0, Math.PI * 2); x.stroke();
    if (f > 0) { x.strokeStyle = '#ffc93c'; x.beginPath(); x.arc(128, 92, 54, -Math.PI / 2, -Math.PI / 2 + f * Math.PI * 2); x.stroke(); }
    x.lineWidth = 4; x.strokeStyle = '#3a2408'; x.beginPath(); x.arc(128, 92, 63, 0, Math.PI * 2); x.stroke();
    // padlock
    x.strokeStyle = '#f4d58a'; x.lineWidth = 9; x.beginPath(); x.arc(128, 84, 15, Math.PI, 0); x.lineTo(143, 94); x.moveTo(113, 84); x.lineTo(113, 94); x.stroke();
    x.fillStyle = '#f4c766'; x.beginPath(); x.roundRect(104, 88, 48, 36, 7); x.fill();
    x.fillStyle = '#6a4410'; x.beginPath(); x.arc(128, 102, 5.5, 0, 7); x.fill(); x.fillRect(125.5, 104, 5, 11);
    // count pill with a coin
    // Arabic reads right to left: what the child has on the right («١٢ / ٢٠» as in the HUD)
    const txt = !g ? '…' : lang === 'ar' ? `${arDigits(g.need)} / ${arDigits(g.have)}` : `${g.have} / ${g.need}`;
    x.font = 'bold 44px Nunito, Tajawal, sans-serif'; x.textBaseline = 'middle'; x.textAlign = 'center';
    const tw = x.measureText(txt).width, w = tw + 78, px = 128 - w / 2;
    x.fillStyle = 'rgba(15,42,51,.92)'; x.strokeStyle = '#f4c766'; x.lineWidth = 4; x.beginPath(); x.roundRect(px, 164, w, 60, 30); x.fill(); x.stroke();
    const cx = px + 34; x.fillStyle = '#edb136'; x.beginPath(); x.arc(cx, 194, 17, 0, 7); x.fill(); x.lineWidth = 3; x.strokeStyle = '#ffe08a'; x.stroke();
    x.fillStyle = '#fff0b8'; x.beginPath(); x.arc(cx, 194, 7, 0, 7); x.fill();
    x.fillStyle = '#fff4dc'; x.direction = 'ltr'; x.fillText(txt, cx + 22 + tw / 2, 196);
    tex.needsUpdate = true;
  }
  return { tex, draw };
}
