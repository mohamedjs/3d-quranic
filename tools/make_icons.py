#!/usr/bin/env python3
"""PWA icons from the title emblem (public/ui/ornaments.svg #o-emblem).

    python3 tools/make_icons.py        # → public/icons/*.png (+ icon.svg)

Deep-teal tile (the UI's --teal palette, g-teal radial) with the gold emblem (g-gold) and a
thin gold ring. "maskable" variants keep the art inside the 80 % safe zone. Rendering uses
headless Chromium via Playwright when it is installed (exact gradients), else ImageMagick
(`convert`); Pillow then down-samples for clean edges.
"""
import os, re, subprocess, tempfile, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'public/ui/ornaments.svg')
OUT = os.path.join(ROOT, 'public/icons')

svg = open(SRC, encoding='utf-8').read()
def block(tag_id, end):
    i = svg.find(f'id="{tag_id}"'); st = svg.rfind('<', 0, i); en = svg.find(end, i) + len(end)
    return svg[st:en]
emblem = block('o-emblem', '</symbol>')
emblem = re.sub(r'<!--.*?-->', '', emblem, flags=re.S)
inner = emblem[emblem.find('>') + 1: emblem.rfind('</symbol>')]
gold = block('g-gold', '</linearGradient>')

def icon(maskable):
    # 512 canvas; emblem viewBox 200×124 scaled to fit the safe zone
    s = 0.66 if maskable else 0.74          # share of the width used by the emblem
    w = 512 * s; k = w / 200; h = 124 * k
    x = (512 - w) / 2; y = (512 - h) / 2 + 10
    bg = ('<rect width="512" height="512" fill="url(#bgt)"/>' if maskable else
          '<rect x="8" y="8" width="496" height="496" rx="112" fill="url(#bgt)"/>')
    ring_r = 196 if maskable else 222
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
<defs>{gold}
<radialGradient id="bgt" cx="256" cy="190" r="380" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#2c6a78"/><stop offset="1" stop-color="#0f2a33"/></radialGradient>
<radialGradient id="glow" cx="256" cy="250" r="200" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#f4c766" stop-opacity=".28"/><stop offset="1" stop-color="#f4c766" stop-opacity="0"/></radialGradient>
</defs>
{bg}
<circle cx="256" cy="256" r="200" fill="url(#glow)"/>
<circle cx="256" cy="256" r="{ring_r}" fill="none" stroke="#f4c766" stroke-opacity=".55" stroke-width="4"/>
<circle cx="256" cy="256" r="{ring_r - 10}" fill="none" stroke="#f4c766" stroke-opacity=".25" stroke-width="2" stroke-dasharray="3 9"/>
<g transform="translate({x:.1f} {y:.1f}) scale({k:.4f})">{inner}</g>
</svg>'''

def chromium():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    pw = sync_playwright().start()
    exe = os.environ.get('CHROMIUM')
    return pw.chromium.launch(**({'executable_path': exe} if exe else {}))
BROWSER = chromium()

def render(svg_text, size, path):
    with tempfile.TemporaryDirectory() as d:
        big = os.path.join(d, 'i.png')
        if BROWSER:
            pg = BROWSER.new_page(viewport={'width': 1024, 'height': 1024})
            pg.set_content('<html><body style="margin:0;background:transparent">' + svg_text.replace('width="512" height="512"', 'width="1024" height="1024"', 1) + '</body></html>')
            pg.screenshot(path=big, omit_background=True, clip={'x': 0, 'y': 0, 'width': 1024, 'height': 1024}); pg.close()
            Image.open(big).convert('RGBA').resize((size, size), Image.LANCZOS).save(path, optimize=True)
            return
        src = os.path.join(d, 'i.svg'); big = os.path.join(d, 'i.png')
        open(src, 'w', encoding='utf-8').write(svg_text)
        subprocess.run(['convert', '-background', 'none', '-density', '288', src, '-resize', '1024x1024', big], check=True)
        Image.open(big).convert('RGBA').resize((size, size), Image.LANCZOS).save(path, optimize=True)

os.makedirs(OUT, exist_ok=True)
plain, mask = icon(False), icon(True)
open(os.path.join(OUT, 'icon.svg'), 'w', encoding='utf-8').write(plain)
for size in (192, 512):
    render(plain, size, os.path.join(OUT, f'icon-{size}.png'))
    render(mask, size, os.path.join(OUT, f'maskable-{size}.png'))
render(mask, 180, os.path.join(OUT, 'apple-touch-icon.png'))   # iOS draws its own rounded mask
render(plain, 32, os.path.join(OUT, 'favicon-32.png'))
print('icons →', OUT, sorted(os.listdir(OUT)), '(chromium)' if BROWSER else '(imagemagick)')
