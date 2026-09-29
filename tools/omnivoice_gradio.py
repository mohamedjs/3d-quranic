#!/usr/bin/env python3
"""Generate missing voice lines through a running OmniVoice Gradio demo (voice cloning from the game's own clips).
   python3 tools/omnivoice_gradio.py <gradio-url> [--test] [--lang "Standard Arabic"]
   → tools/voice_raw_omni/<id with / → __>.wav ; then: python3 tools/voice_import.py tools/voice_raw_omni --no-post"""
import json, os, sys, shutil, time
from gradio_client import Client, handle_file
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = sys.argv[1]; TEST = '--test' in sys.argv
LANG = sys.argv[sys.argv.index('--lang') + 1] if '--lang' in sys.argv else 'Standard Arabic'
OUT = os.path.join(ROOT, 'tools/voice_raw_omni'); os.makedirs(OUT, exist_ok=True)
REF = {'farmer': ('qays-the-fasting-farmer/farmer-a47f9748d6.mp3', 'أتى امرأته فقال لها: أعندكِ طعام؟ قالت: لا، ولكن أنطلق فأطلب لك.'),
       'zainab': ('people-of-the-elephant/zainab-99423973ed.mp3', 'بارك الله فيك يا حبيبي. تذكّر: الله أقوى من كل شيء، فتوكّل عليه.'),
       'player': ('people-of-the-elephant/player-7983631745.mp3', 'يا جدّي، سمعتُ اسم «أبرهة». مَن هو أبرهة؟'),
       'hamdan': ('quraysh-journeys/hamdan-bb744e8024.mp3', 'في مكة عاشت قبيلة قريش، قبيلة النبي صلى الله عليه وسلم. ومكة وادٍ جاف لا يكاد ينبت فيه زرع.'),
       'amina': ('threads-of-dawn/amina-bb0abdec7e.mp3', 'سؤالٌ جميل! وهذا بالضبط ما ظنّه بعض الناس أوّل مرة. اسمع القصة.'),
       'narrator': ('narrator/narrator-a5ce185b0c.mp3', 'روح لبيت الجدّة زينب عند الترعة، هي والجدّ سالم قاعدين على المصطبة ومستنيينك.')}
m = json.load(open(os.path.join(ROOT, 'public/audio/manifest.json')))
lines = [L for L in json.load(open(os.path.join(ROOT, 'tools/voice_lines.json'))) if L['text'] not in m]
if TEST:
    seen = set(); lines = [L for L in lines if not (L['speaker'] in seen or seen.add(L['speaker']))]
c = Client(URL, verbose=False)
t0 = time.time()
for i, L in enumerate(lines):
    out = os.path.join(OUT, L['id'].replace('/', '__') + '.wav')
    if os.path.exists(out) and not TEST: continue
    ref, rtxt = REF[L['speaker']]
    text = L['text'].replace('ﷺ', 'صلى الله عليه وسلم')
    for attempt in range(3):
        try:
            wav, status = c.predict(text, LANG, handle_file(os.path.join(ROOT, 'public/audio', ref)), rtxt, '',
                                    32, 2.0, True, 1.0, None, True, True, api_name='/_clone_fn')
            shutil.copy(wav, out); break
        except Exception as e:
            print('retry', L['id'], e, flush=True); time.sleep(5)
    print(f"{i + 1}/{len(lines)} {L['id']} ({time.time() - t0:.0f}s)", flush=True)
print('DONE')
