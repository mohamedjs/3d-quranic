// Story illustrations. Painted Blender renders (public/illustrations/<name>.webp, built by
// blender/illustrations.py) are shown full-bleed; the generated SVG silhouettes below are the
// fallback when an image is missing or fails to load. No prophets or companions are ever
// depicted; the dream scene shows only the sky, the "year" scene only Makkah at dawn.
import { rng } from '../terrain/heightfield.js';

const W = 1600, H = 700;
let uid = 0;

const sky = (id, stops) => `<linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1">${stops.map(([o, c]) => `<stop offset="${o}" stop-color="${c}"/>`).join('')}</linearGradient>`;
const sunGlow = id => `<radialGradient id="${id}"><stop offset="0" stop-color="#fff4d0"/><stop offset=".25" stop-color="#ffd27a" stop-opacity=".9"/><stop offset="1" stop-color="#ff9a3c" stop-opacity="0"/></radialGradient>`;

function ridge(r, y, amp, color, step = 80, opacity = 1) {
  let d = `M0 ${H} L0 ${y}`;
  for (let x = 0; x <= W + step; x += step) d += ` L${x} ${y - r() * amp}`;
  return `<path d="${d} L${W} ${H} Z" fill="${color}" opacity="${opacity}"/>`;
}
function dunes(y, color, amp = 30) {
  let d = `M0 ${H} L0 ${y}`;
  for (let x = 0; x <= W; x += 200) d += ` Q${x + 100} ${y - amp * (x % 400 ? 1 : -0.3)} ${x + 200} ${y}`;
  return `<path d="${d} L${W} ${H} Z" fill="${color}"/>`;
}
const g = (x, y, s, inner, flip = false) => `<g transform="translate(${x} ${y}) scale(${flip ? -s : s} ${s})">${inner}</g>`;

function elephant(kneel = false, c = '#3a281d') {
  const legY = kneel ? 20 : 25, legH = kneel ? 22 : 58;
  return `<ellipse cx="0" cy="${kneel ? 18 : 0}" rx="72" ry="46" fill="${c}"/>
    <circle cx="66" cy="${kneel ? 0 : -18}" r="33" fill="${c}"/>
    <ellipse cx="48" cy="${kneel ? 0 : -14}" rx="22" ry="30" fill="${c}" stroke="#5a4030" stroke-width="3"/>
    <path d="M92 ${kneel ? 0 : -12} Q116 ${kneel ? 40 : 30} 104 ${kneel ? 68 : 62} L94 ${kneel ? 64 : 58} Q102 ${kneel ? 34 : 28} 80 ${kneel ? 14 : 4} Z" fill="${c}"/>
    <path d="M86 ${kneel ? 18 : 8} Q102 ${kneel ? 32 : 24} 114 ${kneel ? 26 : 16}" stroke="#e8dcc0" stroke-width="5" fill="none" stroke-linecap="round"/>
    ${[-52, -26, 22, 46].map((x, i) => kneel && i > 1 ? `<rect x="${x}" y="52" width="30" height="16" rx="7" fill="${c}"/>` : `<rect x="${x}" y="${legY}" width="21" height="${legH}" rx="6" fill="${c}"/>`).join('')}
    <path d="M-70 -4 Q-86 14 -80 34" stroke="${c}" stroke-width="5" fill="none"/>`;
}
const soldier = (c = '#2e2018') => `<circle cx="0" cy="-34" r="6" fill="${c}"/><path d="M-8 -26 L8 -26 L11 0 L-11 0 Z" fill="${c}"/><line x1="10" y1="-58" x2="10" y2="0" stroke="${c}" stroke-width="2.5"/>`;
const banner = c => `<line x1="0" y1="-80" x2="0" y2="0" stroke="#2e2018" stroke-width="3"/><path d="M0 -80 L34 -70 L0 -60 Z" fill="${c}"/>`;
const camel = (c = '#3a281d') => `<ellipse cx="0" cy="0" rx="42" ry="20" fill="${c}"/><path d="M-22 -12 Q-4 -46 16 -12 Z" fill="${c}"/>
  <path d="M34 -6 Q52 -20 56 -46" stroke="${c}" stroke-width="12" fill="none" stroke-linecap="round"/><ellipse cx="64" cy="-48" rx="14" ry="7" fill="${c}"/>
  ${[-30, -16, 18, 32].map(x => `<line x1="${x}" y1="10" x2="${x + (x % 4 ? 3 : -3)}" y2="56" stroke="${c}" stroke-width="5" stroke-linecap="round"/>`).join('')}
  <rect x="-24" y="-38" width="30" height="14" rx="4" fill="#7a2e22"/>`;
const bird = (c = '#2a1c14') => `<path d="M-14 0 Q-7 -9 0 0 Q7 -9 14 0" stroke="${c}" stroke-width="3" fill="none" stroke-linecap="round"/>`;
const kaaba = () => `<rect x="-40" y="-60" width="80" height="60" fill="#141414"/><rect x="-40" y="-48" width="80" height="7" fill="#c9a24a"/><rect x="10" y="-30" width="14" height="24" fill="#c9a24a" opacity=".8"/><path d="M-40 -60 L-28 -68 L52 -68 L40 -60 Z" fill="#262626"/><path d="M40 -60 L52 -68 L52 -8 L40 0 Z" fill="#0b0b0b"/>`;
const star = (x, y, r) => { let d = ''; for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, k = i % 2 ? r * 0.45 : r; d += `${i ? 'L' : 'M'}${(x + Math.cos(a) * k).toFixed(1)} ${(y + Math.sin(a) * k).toFixed(1)} `; } return `<path d="${d}Z" fill="#fff1b8"/>`; };
const houses = (r, x0, y, n) => Array.from({ length: n }, (_, i) => { const w = 26 + r() * 30, h = 18 + r() * 26; return `<rect x="${x0 + i * 42 + r() * 10}" y="${y - h}" width="${w}" height="${h}" fill="#4a3526"/>`; }).join('');

const SCENES = {
  kaaba(r, id) {
    return `<defs>${sky(id + 's', [[0, '#3b3f6e'], [0.45, '#d9795a'], [0.8, '#f4b56a'], [1, '#f8d49a']])}${sunGlow(id + 'g')}</defs>
      <rect width="${W}" height="${H}" fill="url(#${id}s)"/><circle cx="1150" cy="430" r="220" fill="url(#${id}g)"/>
      ${ridge(r, 470, 160, '#7a5a78', 90, 0.8)}${ridge(r, 540, 120, '#5a3d3c', 70)}
      <rect y="560" width="${W}" height="${H - 560}" fill="#6b4a32"/>
      ${houses(r, 520, 590, 5)}${houses(r, 880, 592, 5)}${g(800, 600, 1.4, kaaba())}
      <g class="drift">${[0, 1, 2, 3, 4].map(i => g(300 + i * 60, 160 + (i % 2) * 30, 1, bird())).join('')}</g>`;
  },
  army(r, id) {
    const soldiers = Array.from({ length: 70 }, (_, i) => g(80 + (i % 35) * 44 + r() * 12, 600 + ((i / 35) | 0) * 45 + r() * 8, 0.9 + r() * 0.3, soldier())).join('');
    return `<defs>${sky(id + 's', [[0, '#5a3b52'], [0.5, '#e0874f'], [1, '#f7c97c']])}${sunGlow(id + 'g')}</defs>
      <rect width="${W}" height="${H}" fill="url(#${id}s)"/><circle cx="1250" cy="330" r="260" fill="url(#${id}g)"/>
      ${ridge(r, 470, 100, '#8a5a52', 110, 0.7)}<rect y="480" width="${W}" height="${H}" fill="#a0683e"/>
      <rect y="440" width="${W}" height="120" fill="#f0b070" opacity=".35"/>
      ${g(260, 520, 1.1, elephant(), true)}${g(560, 505, 0.8, elephant(), true)}${g(820, 500, 0.6, elephant(), true)}${g(1060, 495, 0.45, elephant(), true)}
      ${g(250, 470, 1, banner('#b33a2a'))}${g(700, 520, 1, banner('#d9a441'))}${g(1180, 520, 0.8, banner('#b33a2a'))}${soldiers}
      <rect y="560" width="${W}" height="140" fill="#c8844a" opacity=".3"/>`;
  },
  elephant(r, id) {
    return `<defs>${sky(id + 's', [[0, '#4a3f6a'], [0.55, '#e59a5c'], [1, '#f6cf8d']])}${sunGlow(id + 'g')}</defs>
      <rect width="${W}" height="${H}" fill="url(#${id}s)"/><circle cx="1180" cy="400" r="240" fill="url(#${id}g)"/>
      ${ridge(r, 480, 150, '#7d5870', 90, 0.8)}${g(1200, 520, 0.5, kaaba())}${ridge(r, 560, 60, '#6b4a36', 120)}
      <rect y="590" width="${W}" height="${H}" fill="#7a5236"/>
      ${g(620, 560, 2, elephant(true), true)}${[0, 1, 2, 3].map(i => g(250 + i * 70, 640, 1.2, soldier())).join('')}`;
  },
  birds(r, id) {
    const flock = Array.from({ length: 70 }, () => g(r() * W, 60 + r() * 330, 0.6 + r() * 0.9, bird('#1d140e'))).join('');
    const stones = Array.from({ length: 40 }, () => { const x = r() * W, y = 200 + r() * 300; return `<line x1="${x}" y1="${y}" x2="${x - 10}" y2="${y + 40}" stroke="#ffe0a0" stroke-width="1.5" opacity=".5"/><circle cx="${x - 10}" cy="${y + 42}" r="3" fill="#8a5a3a"/>`; }).join('');
    return `<defs>${sky(id + 's', [[0, '#2e2442'], [0.5, '#b0583c'], [1, '#e8a060']])}</defs>
      <rect width="${W}" height="${H}" fill="url(#${id}s)"/>${ridge(r, 540, 90, '#4a2e28', 100)}
      <rect y="580" width="${W}" height="${H}" fill="#5a3a26"/><g class="drift">${flock}</g>${stones}
      ${g(900, 600, 0.6, elephant(), true)}${Array.from({ length: 25 }, (_, i) => g(100 + i * 60, 650, 0.9, soldier('#24180f'))).join('')}`;
  },
  caravan(r, id, lang) {
    const yemen = lang === 'ar' ? 'الشتاء ← اليمن' : 'Winter → Yemen', sham = lang === 'ar' ? 'الصيف ← الشام' : 'Summer → Ash-Sham';
    return `<defs>${sky(id + 's', [[0, '#6a5a8a'], [0.5, '#ef9a5a'], [1, '#fbd99a']])}${sunGlow(id + 'g')}</defs>
      <rect width="${W}" height="${H}" fill="url(#${id}s)"/><circle cx="300" cy="420" r="230" fill="url(#${id}g)"/>
      ${dunes(520, '#c98a52', 40)}${dunes(590, '#a86a3c', 30)}
      ${[0, 1, 2, 3, 4, 5].map(i => g(560 + i * 130, 560 - i * 6, 1 - i * 0.07, camel())).join('')}
      <g font-family="Tajawal, Nunito, sans-serif" font-size="34" font-weight="700" fill="#fff6e0">
        <text x="120" y="640">${yemen}</text><text x="${W - 120}" y="120" text-anchor="end">${sham}</text></g>`;
  },
  straw(r, id) {
    const stalks = Array.from({ length: 160 }, () => { const x = r() * W, y = 470 + r() * 230, h = 14 + r() * 40, a = (r() - 0.5) * 50;
      return `<line x1="${x}" y1="${y}" x2="${x + a}" y2="${y - h}" stroke="${r() < 0.5 ? '#d9b36a' : '#b58c4a'}" stroke-width="3" stroke-linecap="round"/>`; }).join('');
    return `<defs>${sky(id + 's', [[0, '#9fa9c4'], [0.55, '#f4d49a'], [1, '#fbe3b4']])}${sunGlow(id + 'g')}</defs>
      <rect width="${W}" height="${H}" fill="url(#${id}s)"/><circle cx="220" cy="300" r="200" fill="url(#${id}g)"/>
      ${ridge(r, 420, 50, '#b9a2a8', 140, 0.8)}<rect y="450" width="${W}" height="${H - 450}" fill="#a57a4c"/>${stalks}
      <path d="M1000 640 a70 60 0 0 1 140 0 Z" fill="#6a5038"/><line x1="560" y1="660" x2="640" y2="520" stroke="#5a3a26" stroke-width="7" stroke-linecap="round"/>`;
  },
  year(r, id) {
    return `<defs>${sky(id + 's', [[0, '#6f86b8'], [0.45, '#eea88e'], [0.8, '#fbc486'], [1, '#ffe0a8']])}${sunGlow(id + 'g')}</defs>
      <rect width="${W}" height="${H}" fill="url(#${id}s)"/><circle cx="780" cy="400" r="260" fill="url(#${id}g)"/>
      ${ridge(r, 470, 150, '#8a7a96', 90, 0.8)}${ridge(r, 540, 110, '#5a4448', 70)}
      <rect y="560" width="${W}" height="${H - 560}" fill="#a87a52"/>${houses(r, 480, 600, 7)}${houses(r, 900, 602, 7)}${g(800, 610, 1.3, kaaba())}`;
  },
  dream(r, id) {
    const stars = Array.from({ length: 11 }, (_, i) => { const a = Math.PI * (0.12 + i * 0.076); return star(800 - Math.cos(a) * 520, 470 - Math.sin(a) * 330, 16); }).join('');
    const tiny = Array.from({ length: 120 }, () => `<circle cx="${r() * W}" cy="${r() * 520}" r="${r() * 1.6}" fill="#fff" opacity="${0.3 + r() * 0.6}"/>`).join('');
    return `<defs>${sky(id + 's', [[0, '#0b1030'], [0.6, '#27306a'], [1, '#5a4a7a']])}<radialGradient id="${id}g"><stop offset="0" stop-color="#fff6c8"/><stop offset=".3" stop-color="#ffc861"/><stop offset="1" stop-color="#ff9a3c" stop-opacity="0"/></radialGradient></defs>
      <rect width="${W}" height="${H}" fill="url(#${id}s)"/>${tiny}
      <circle cx="660" cy="300" r="120" fill="url(#${id}g)"/><circle cx="660" cy="300" r="46" fill="#ffd97a"/>
      <circle cx="950" cy="290" r="44" fill="#f5f0dc"/><circle cx="972" cy="276" r="40" fill="#27306a"/>
      <g class="twinkle">${stars}</g>${ridge(r, 640, 40, '#0a0c1e', 120)}`;
  },
};

function svgMarkup(name, lang) {
  const make = SCENES[name]; if (!make) return '';
  const id = 'sc' + (++uid);
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" role="img">${make(rng(name.length * 31 + 7), id, lang)}</svg>`;
}

// ---- painted illustrations -------------------------------------------------------------------
const PAINTED = ['kaaba', 'army', 'elephant', 'birds', 'straw', 'year', 'title'];   // story order
const STORY = PAINTED.slice(0, -1);
export const illustrationURL = name => new URL(`${import.meta.env.BASE_URL}illustrations/${name}.webp`, document.baseURI).href;

const preloaded = new Set();
export function preloadScene(name) {
  if (!PAINTED.includes(name) || preloaded.has(name) || typeof Image === 'undefined') return;
  preloaded.add(name);
  const img = new Image(); img.decoding = 'async'; img.src = illustrationURL(name);
}
// warm the cache for the illustration that most likely comes next (called when a step shows a scene)
function preloadNext(name) {
  const i = STORY.indexOf(name);
  if (i < 0) return;
  const next = STORY[i + 1];
  const go = () => { preloadScene(next); };
  if (next) (typeof requestIdleCallback === 'function' ? requestIdleCallback(go, { timeout: 1500 }) : setTimeout(go, 300));
}

// If a painted image fails, swap in its SVG fallback (kept hidden right after the <img>).
if (typeof document !== 'undefined') {
  document.addEventListener('error', e => {
    const img = e.target;
    if (!(img instanceof HTMLImageElement) || !img.dataset.scene) return;
    const svg = img.nextElementSibling;
    if (svg && svg.tagName.toLowerCase() === 'svg') svg.style.display = '';
    img.remove();
  }, true);
}

const IMG_STYLE = 'position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;animation:kenburns 16s ease-out forwards';

// Returns the markup for #scene: a full-bleed painted image with the SVG as fallback
// (or just the SVG for scenes that have no painting yet).
export function sceneSVG(name, lang) {
  const svg = svgMarkup(name, lang);
  if (!PAINTED.includes(name)) return svg;
  preloaded.add(name); preloadNext(name);
  const fallback = svg ? svg.replace('<svg ', '<svg style="display:none" ') : '';
  return `<img data-scene="${name}" src="${illustrationURL(name)}" alt="" decoding="async" draggable="false" style="${IMG_STYLE}">${fallback}`;
}
