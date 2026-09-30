import asyncio, sys, os
from playwright.async_api import async_playwright
fmt, mode = sys.argv[1], sys.argv[2]   # v|h , stills|video
W, H = (1080, 1920) if fmt[0] == 'v' else (1920, 1080)
import os as _o
TIM = _o.environ.get('TIMING', '/tmp/ad/timing.json'); CUES = _o.environ.get('CUES', '/tmp/ad/cues.json')
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': W, 'height': H})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(f'http://localhost:8765/ad/index.html#{fmt}', wait_until='load')
        import json as _j
        await pg.evaluate('window.initDone')
        await pg.evaluate('x => window.setTiming(x)', _j.load(open(TIM)))
        open(CUES,'w').write(_j.dumps(await pg.evaluate('window.cues()')))
        stage = await pg.query_selector('#stage')
        if mode == 'stills':
            ts = [float(x) for x in sys.argv[3].split(',')]
            os.makedirs('/tmp/ad/stills', exist_ok=True)
            for t in ts:
                await pg.evaluate(f'render({t})')
                await stage.screenshot(path=f'/tmp/ad/stills/{fmt}_{t:05.2f}.jpg', type='jpeg', quality=80)
        else:
            fps = int(sys.argv[3]); a = float(sys.argv[4]); z = float(sys.argv[5]) if sys.argv[5] != 'end' else _j.load(open(TIM))['total']; d = f'/tmp/ad/frames_{fmt}'; os.makedirs(d, exist_ok=True)
            i0 = int(round(a * fps)); i1 = int(round(z * fps))
            for i in range(i0, i1):
                await pg.evaluate(f'render({i / fps})')
                await stage.screenshot(path=f'{d}/{i:05d}.jpg', type='jpeg', quality=92)
        print('errors', errs[:3])
        await b.close()
asyncio.run(main())
