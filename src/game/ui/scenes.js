// Story illustrations. Painted Blender renders (public/illustrations/<name>.webp, built by
// blender/illustrations.py) are shown full-bleed; the generated SVG silhouettes below are the
// fallback when an image is missing or fails to load. No prophets or companions are ever
// depicted; the dream scene shows only the sky, the "year" scene only Makkah at dawn, and the
// asbab-al-nuzul scenes only objects, places, light and animals (no people at all).
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

// ---- small silhouettes for the asbab (occasions of revelation) fallbacks — objects & places only
const palm = (c = '#2a1c14', h = 220) => `<path d="M-6 0 Q-14 ${-h * 0.5} 0 ${-h} L6 ${-h} Q-2 ${-h * 0.5} 8 0 Z" fill="${c}"/>` +
  [[-70, 30], [-40, -10], [40, -10], [70, 30], [0, -30]].map(([dx, dy]) => `<path d="M0 ${-h} Q${dx * 0.6} ${-h + dy - 40} ${dx} ${-h + dy + 20}" stroke="${c}" stroke-width="10" fill="none" stroke-linecap="round"/>`).join('');
const jugS = (c = '#b0643a') => `<path d="M-14 -96 L14 -96 L12 -80 Q46 -60 40 -20 Q36 0 0 0 Q-36 0 -40 -20 Q-46 -60 -12 -80 Z" fill="${c}"/><path d="M14 -84 Q52 -84 40 -40" stroke="${c}" stroke-width="7" fill="none"/>`;
const lampS = (lit = true) => `<path d="M-40 0 Q-40 -22 0 -22 Q30 -22 46 -12 L54 -10 L50 -2 Q20 4 -30 4 Z" fill="#9a5a34"/>` + (lit ? `<ellipse cx="54" cy="-24" rx="7" ry="15" fill="#ffd27a"/><circle cx="54" cy="-22" r="46" fill="#ffc861" opacity=".18"/>` : '');
const datesS = (r, n, cx, cy, rx, ry, cols, sz = 7) => Array.from({ length: n }, () => { const a = r() * 6.283, d = Math.sqrt(r()); return `<ellipse cx="${(cx + Math.cos(a) * rx * d).toFixed(1)}" cy="${(cy + Math.sin(a) * ry * d).toFixed(1)}" rx="${sz}" ry="${(sz * 1.4).toFixed(1)}" fill="${cols[(r() * cols.length) | 0]}"/>`; }).join('');
const basketS = (x, y, w, c = '#b48a4c') => `<path d="M${x - w} ${y} L${x + w} ${y} L${x + w * 0.8} ${y + w * 0.75} L${x - w * 0.8} ${y + w * 0.75} Z" fill="${c}"/><rect x="${x - w - 6}" y="${y - 8}" width="${w * 2 + 12}" height="14" rx="7" fill="#d9b06a"/>`;
const houseS = (x, y, w, h, c = '#c8966a') => `<rect x="${x}" y="${y - h}" width="${w}" height="${h}" fill="${c}"/><rect x="${x - 8}" y="${y - h - 10}" width="${w + 16}" height="14" fill="${c}"/>`;
const stars = (r, n, h = 420) => Array.from({ length: n }, () => `<circle cx="${(r() * W).toFixed(0)}" cy="${(r() * h).toFixed(0)}" r="${(0.6 + r() * 1.6).toFixed(1)}" fill="#fff4d6" opacity="${(0.4 + r() * 0.6).toFixed(2)}"/>`).join('');
const crescentS = (x, y, rr, bg) => `<circle cx="${x}" cy="${y}" r="${rr}" fill="#f6eed8"/><circle cx="${x - rr * 0.4}" cy="${y - rr * 0.15}" r="${rr * 0.88}" fill="${bg}"/>`;
const archWin = (x, y, w, h, fill) => `<path d="M${x} ${y} L${x} ${y - h + w / 2} A${w / 2} ${w / 2} 0 0 1 ${x + w} ${y - h + w / 2} L${x + w} ${y} Z" fill="${fill}"/>`;

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

  // ---- asbab al-nuzul (2:187, 2:267, 2:189, 2:144, 59:9) — never any people
  threads_dawn(r, id) {
    return `<defs>${sky(id + 's', [[0, '#0b1034'], [0.45, '#27336e'], [0.75, '#8594c8'], [0.86, '#f6dcaa'], [0.87, '#16182c'], [1, '#16182c']])}</defs>
      <rect width="${W}" height="${H}" fill="#2a1712"/>${archWin(560, 640, 480, 600, `url(#${id}s)`)}
      <g clip-path="none">${stars(r, 40, 300).replace(/cx="(\d+)"/g, (m, x) => `cx="${560 + (x % 480)}"`)}</g>${crescentS(660, 170, 22, '#1b2454')}
      ${g(650, 610, 0.5, palm('#12121c', 260))}${g(930, 610, 0.4, palm('#12121c', 260))}
      <rect x="540" y="160" width="520" height="12" rx="6" fill="#6a4428"/>
      <path d="M770 170 Q785 330 772 520" stroke="#fffaf0" stroke-width="7" fill="none" stroke-linecap="round"/>
      <path d="M830 170 Q815 330 828 510" stroke="#0c0a0a" stroke-width="7" fill="none" stroke-linecap="round"/>
      <rect x="520" y="630" width="560" height="22" fill="#6a4428"/>${g(960, 630, 1, lampS())}${g(620, 630, 0.8, jugS('#c98a55'))}`;
  },
  suhoor_table(r, id) {
    return `<rect width="${W}" height="${H}" fill="#3a2230"/>${archWin(520, 300, 300, 280, '#1a2452')}${stars(r, 12, 60).replace(/cy="(\d+)"/g, (m, y) => `cy="${80 + +y}"`).replace(/cx="(\d+)"/g, (m, x) => `cx="${540 + (x % 260)}"`)}${crescentS(600, 110, 16, '#1a2452')}
      <circle cx="560" cy="560" r="330" fill="#ff9a48" opacity=".22"/><rect y="440" width="${W}" height="${H - 440}" fill="#a88048"/>
      <ellipse cx="800" cy="560" rx="420" ry="110" fill="#c89a44"/><ellipse cx="800" cy="552" rx="400" ry="100" fill="#d9ab52"/>
      ${g(980, 560, 1.4, jugS())}<ellipse cx="700" cy="540" rx="90" ry="30" fill="#e0bc8c"/>${datesS(r, 18, 700, 528, 70, 16, ['#8a3a16', '#a04a1e'])}
      <ellipse cx="860" cy="610" rx="95" ry="26" fill="#d0944e"/>${g(470, 560, 1.4, lampS())}`;
  },
  qays_field(r, id) {
    return `<defs>${sky(id + 's', [[0, '#565284'], [0.45, '#e08a62'], [0.7, '#fbd08a'], [1, '#f3a860']])}${sunGlow(id + 'g')}</defs>
      <rect width="${W}" height="${H}" fill="url(#${id}s)"/><circle cx="860" cy="420" r="240" fill="url(#${id}g)"/>
      <rect y="440" width="${W}" height="${H}" fill="#7a4a2c"/>${Array.from({ length: 22 }, (_, i) => `<line x1="800" y1="440" x2="${-400 + i * 110}" y2="${H}" stroke="#5a3420" stroke-width="6"/>`).join('')}
      <path d="M1200 440 L1600 520 L1600 600 L1250 440 Z" fill="#6f8fb0"/>
      ${[[180, 470, 1.1], [420, 450, 0.7], [1100, 450, 0.8], [1350, 470, 1.2], [1500, 480, 1.3]].map(([x, y, k]) => g(x, y, k, palm('#3a2a1c'))).join('')}
      <line x1="300" y1="640" x2="360" y2="480" stroke="#5a3a26" stroke-width="8"/><path d="M290 640 L330 650 L320 670 Z" fill="#6a6a6a"/>
      <path d="M520 620 Q560 580 600 620 Z" fill="#b48a4c"/>`;
  },
  night_house(r, id) {
    return `<defs>${sky(id + 's', [[0, '#0a0f2c'], [0.7, '#202b5e'], [1, '#4e5e96']])}</defs>
      <rect width="${W}" height="${H}" fill="url(#${id}s)"/>${stars(r, 90, 360)}${g(260, 560, 1, palm('#141424'))}${g(1340, 560, 0.9, palm('#141424'))}
      <rect y="560" width="${W}" height="${H}" fill="#3a3a5a"/>${houseS(420, 580, 760, 380, '#7a6a80')}
      <rect x="520" y="360" width="150" height="220" fill="#3c5a66"/>${archWin(880, 400, 110, 150, '#ffc26a')}<circle cx="935" cy="340" r="120" fill="#ffc26a" opacity=".12"/>
      <rect x="490" y="578" width="210" height="18" fill="#8e7a66"/><path d="M560 578 Q590 555 620 578 Z" fill="#c87a44"/>`;
  },
  date_clusters(r, id) {
    const bunch = x => `<line x1="${x}" y1="235" x2="${x}" y2="280" stroke="#d0902e" stroke-width="6"/>` + datesS(r, 60, x, 360, 70, 90, ['#e8a826', '#b8321e', '#d86a1e', '#c0621e'], 8);
    return `<defs>${sky(id + 's', [[0, '#6f8fc0'], [0.6, '#d8c8b4'], [1, '#fbe3b4']])}</defs>
      <rect width="${W}" height="${H}" fill="url(#${id}s)"/><rect y="430" width="${W}" height="130" fill="#d0a070"/><rect y="560" width="${W}" height="${H}" fill="#c89a68"/>
      <rect x="200" y="60" width="1200" height="40" fill="#b89a5a"/><rect x="230" y="90" width="44" height="560" fill="#7a5a3a"/><rect x="1326" y="90" width="44" height="560" fill="#7a5a3a"/>
      <path d="M274 220 Q800 290 1326 220" stroke="#c4a46a" stroke-width="8" fill="none"/>${bunch(560)}${bunch(800)}${bunch(1040)}
      ${g(680, 246, 1.6, bird('#8a5a36'))}${g(1180, 230, 1.6, bird('#8a5a36'))}`;
  },
  best_dates(r, id) {
    return `<rect width="${W}" height="${H}" fill="#c9a06c"/><rect y="420" width="${W}" height="${H}" fill="#a88048"/>
      <ellipse cx="520" cy="470" rx="360" ry="200" fill="#ffe2a0" opacity=".35"/>
      ${basketS(520, 420, 220)}${datesS(r, 70, 520, 400, 200, 36, ['#d8962a', '#a8341a', '#c0621e'], 12)}
      ${basketS(1080, 440, 200, '#977040')}${datesS(r, 22, 1080, 440, 150, 16, ['#4a3020', '#6a4c34'], 8)}`;
  },
  house_door(r, id) {
    return `<defs>${sky(id + 's', [[0, '#7488b4'], [0.6, '#eaa878'], [1, '#fbd592']])}</defs>
      <rect width="${W}" height="${H}" fill="url(#${id}s)"/>${g(1350, 540, 1.1, palm('#4a3a24'))}<rect y="540" width="${W}" height="${H}" fill="#c89a68"/>
      ${houseS(300, 560, 1000, 420, '#d8a46e')}${archWin(700, 560, 200, 300, '#ffc070')}<path d="M700 560 L660 580 L660 330 L700 300 Z" fill="#3f7f8a"/><path d="M900 560 L940 580 L940 330 L900 300 Z" fill="#3f7f8a"/>
      <path d="M740 ${H} L780 560 L820 560 L860 ${H} Z" fill="#b8a488"/><ellipse cx="610" cy="560" rx="44" ry="34" fill="#c8862e"/><ellipse cx="990" cy="560" rx="40" ry="32" fill="#a83a28"/>`;
  },
  house_back(r, id) {
    const weeds = Array.from({ length: 40 }, () => { const x = r() * W; return `<path d="M${x} ${H} q${(r() - 0.5) * 30} -40 ${(r() - 0.5) * 20} -70" stroke="#6a7a30" stroke-width="5" fill="none"/>`; }).join('');
    return `<defs>${sky(id + 's', [[0, '#565284'], [0.5, '#e08a62'], [1, '#fbd08a']])}</defs>
      <rect width="${W}" height="${H}" fill="url(#${id}s)"/>${houseS(200, 600, 1200, 480, '#c89464')}
      <path d="M840 420 Q880 380 930 400 Q970 440 950 500 Q900 530 850 510 Q820 470 840 420 Z" fill="#2a1a12"/>
      ${g(885, 420, 1.6, bird('#8a5a36'))}<rect y="600" width="${W}" height="${H}" fill="#b8885a"/>${weeds}
      <line x1="420" y1="600" x2="470" y2="260" stroke="#8a6038" stroke-width="8"/><line x1="480" y1="600" x2="530" y2="260" stroke="#8a6038" stroke-width="8"/>`;
  },
  qibla_ground(r, id) {
    return `<defs>${sky(id + 's', [[0, '#6c86b8'], [0.6, '#e6b48a'], [1, '#fbe0a8']])}</defs>
      <rect width="${W}" height="${H}" fill="url(#${id}s)"/><rect y="420" width="${W}" height="${H}" fill="#d4a46c"/>
      <rect x="180" y="150" width="1240" height="36" fill="#b89a5a"/>${[220, 520, 820, 1120, 1380].map(x => `<rect x="${x}" y="186" width="30" height="${420 - 186 + 180}" fill="#7a5a3a"/>`).join('')}
      ${[480, 540, 610].map(y => `<rect x="260" y="${y}" width="1080" height="36" fill="#c8a060"/>`).join('')}
      <path d="M420 330 A420 150 0 0 0 1240 360" stroke="#ffe39a" stroke-width="22" fill="none" stroke-linecap="round" opacity=".85"/><circle cx="1240" cy="360" r="30" fill="#fff0c0" opacity=".8"/>`;
  },
  lamp_out(r, id) {
    return `<rect width="${W}" height="${H}" fill="#2a2438"/>${archWin(1180, 560, 280, 420, '#24326a')}${crescentS(1300, 220, 22, '#24326a')}
      <circle cx="560" cy="430" r="260" fill="#8fa4ff" opacity=".12"/><rect x="300" y="470" width="620" height="30" fill="#5a3a26"/>
      ${g(520, 470, 2.4, lampS(false))}<path d="M650 440 Q620 380 660 330 Q700 280 660 220 Q630 170 670 120" stroke="#d4dcf4" stroke-width="6" fill="none" opacity=".8" stroke-linecap="round"/>
      <circle cx="650" cy="440" r="5" fill="#ff7a2a"/>${g(820, 470, 1.2, jugS('#8a6a58'))}`;
  },
  guest_meal(r, id) {
    return `<rect width="${W}" height="${H}" fill="#4a2c2a"/>${archWin(900, 470, 300, 420, '#2e3d74')}${stars(r, 14, 200).replace(/cx="(\d+)"/g, (m, x) => `cx="${910 + (x % 280)}"`).replace(/cy="(\d+)"/g, (m, y) => `cy="${120 + +y}"`)}${crescentS(1120, 150, 16, '#2e3d74')}
      <circle cx="560" cy="250" r="220" fill="#ff9a48" opacity=".18"/>${g(560, 250, 1, lampS())}<rect y="470" width="${W}" height="${H}" fill="#6a4a36"/>
      <rect x="360" y="520" width="760" height="150" fill="#b08848"/><ellipse cx="700" cy="590" rx="150" ry="40" fill="#c07a44"/><ellipse cx="700" cy="584" rx="120" ry="28" fill="#8a4a22"/>
      ${g(940, 610, 1.4, jugS())}<rect x="220" y="520" width="140" height="90" rx="30" fill="#9a3a2a"/>`;
  },
  story_book(r, id) {
    const lines = side => Array.from({ length: 9 }, (_, i) => `<line x1="${side ? 820 : 620}" y1="${470 + i * 16}" x2="${(side ? 820 : 620) + 120 + r() * 50}" y2="${470 + i * 16}" stroke="#5a3a24" stroke-width="4" opacity=".7"/>`).join('');
    return `<defs>${sky(id + 's', [[0, '#6c7fae'], [0.55, '#e39a72'], [1, '#fbd592']])}${sunGlow(id + 'g')}</defs>
      <rect width="${W}" height="${H}" fill="#7a4a2e"/>${archWin(260, 560, 520, 520, `url(#${id}s)`)}<circle cx="430" cy="400" r="160" fill="url(#${id}g)"/>
      ${[[330, 560, 0.7], [520, 560, 0.9], [700, 560, 0.6]].map(([x, y, k]) => g(x, y, k, palm('#4a4a2a'))).join('')}
      <path d="M260 560 L1000 700 L1400 700 L780 560 Z" fill="#ffd890" opacity=".15"/><rect y="600" width="${W}" height="${H}" fill="#9a6a40"/>
      <path d="M800 700 L620 520 L660 500 L800 640 L940 500 L980 520 Z" fill="#8a5630"/>
      <path d="M800 560 L600 450 L600 610 L800 660 Z" fill="#f2e2bc"/><path d="M800 560 L1000 450 L1000 610 L800 660 Z" fill="#f2e2bc"/>${lines(0)}${lines(1)}`;
  },
};

function svgMarkup(name, lang) {
  const make = SCENES[name]; if (!make) return '';
  const id = 'sc' + (++uid);
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" role="img">${make(rng(name.length * 31 + 7), id, lang)}</svg>`;
}

// ---- painted illustrations -------------------------------------------------------------------
const ELEPHANT_STORY = ['kaaba', 'army', 'elephant', 'birds', 'straw', 'year'];   // story order
// asbab al-nuzul set (blender/illustrations/illustrations_asbab.py): cover, 2:187 (threads, suhoor, Qays),
// 2:267 (dates), 2:189 (doors), 2:144 (qibla), 59:9 (the guest and the lamp)
const ASBAB_STORY = ['story_book', 'threads_dawn', 'suhoor_table', 'qays_field', 'night_house', 'date_clusters', 'best_dates',
  'house_door', 'house_back', 'qibla_ground', 'guest_meal', 'lamp_out'];
const PAINTED = [...ELEPHANT_STORY, 'title', ...ASBAB_STORY];
const SEQUENCES = [ELEPHANT_STORY, ASBAB_STORY];
export const illustrationURL = name => new URL(`${import.meta.env.BASE_URL}illustrations/${name}.webp`, document.baseURI).href;

const preloaded = new Set();
export function preloadScene(name) {
  if (!PAINTED.includes(name) || preloaded.has(name) || typeof Image === 'undefined') return;
  preloaded.add(name);
  const img = new Image(); img.decoding = 'async'; img.src = illustrationURL(name);
}
// warm the cache for the illustration that most likely comes next (called when a step shows a scene)
function preloadNext(name) {
  const seq = SEQUENCES.find(q => q.includes(name));
  if (!seq) return;
  const next = seq[seq.indexOf(name) + 1];
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
