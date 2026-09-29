#!/usr/bin/env python3
"""Regenerate EVERY voice line with OmniVoice (Gradio demo), cloning each character from its designed
   native-Arabic anchor (tools/voice_design_omni/<pick>.wav). Each take is checked with Whisper; a take
   whose character error rate is > 0.2 is regenerated (up to 3 takes, best kept).
   python3 tools/omnivoice_all.py <gradio-url>   → tools/voice_raw_omni/<id with / → __>.wav + qc.json"""
import json, os, sys, shutil, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gradio_client import Client, handle_file
from score import asr, cer
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = sys.argv[1]
OUT = os.path.join(ROOT, 'tools/voice_raw_omni'); os.makedirs(OUT, exist_ok=True)
A = os.path.join(ROOT, 'tools/voice_design_omni')
PICK = {  # speaker: (anchor take, its text, speed)
 'farmer':   ('farmer-2',   'تعالَ يا حبيبي، اقعد جنبي هنا. سأحكي لك حكايةً جميلةً من القرآن الكريم.', 0.92),
 'hamdan':   ('hamdan-3',   'أهلًا يا صغيري! القافلة وصلت من السوق، تعالَ أحكي لك عن رحلةٍ عظيمة.', 0.95),
 'zainab':   ('zainab-2',   'يا حبيبي، تعالَ اقعد معنا على المصطبة. عندي لك حكايةٌ حلوةٌ عن الصبر.', 0.92),
 'amina':    ('amina-3',    'سؤالٌ جميل يا حبيبي! اسمع القصة من أوّلها، وستعرف الجواب بنفسك.', 0.95),
 'player':   ('player-2',   'يا جدّي، احكِ لي الحكاية من فضلك! أنا أحبّ قصص القرآن كثيرًا.', 0.95),
 'narrator': ('narrator-2', 'يلا بينا نبدأ مغامرة جديدة! روح للجدّة زينب عند الترعة، مستنياك على المصطبة.', 0.95),
}
lines = json.load(open(os.path.join(ROOT, 'tools/voice_lines.json')))
qcp = os.path.join(OUT, 'qc.json'); qc = json.load(open(qcp)) if os.path.exists(qcp) else {}
c = Client(URL, verbose=False); t0 = time.time()
for i, L in enumerate(lines):
    out = os.path.join(OUT, L['id'].replace('/', '__') + '.wav')
    if L['id'] in qc and os.path.exists(out): continue
    anchor, rtxt, sp = PICK[L['speaker']]
    text = L['text'].replace('ﷺ', 'صلى الله عليه وسلم')
    lang = 'Egyptian Arabic' if L['speaker'] == 'narrator' else 'Standard Arabic'
    best = None
    for take in range(3):
        wav = None
        for attempt in range(4):
            try:
                wav, _ = c.predict(text, lang, handle_file(f'{A}/{anchor}.wav'), rtxt, '', 32, 2.0, True, sp, None, True, True, api_name='/_clone_fn'); break
            except Exception as e:
                print('  retry', e, flush=True); time.sleep(10)
                try: c = Client(URL, verbose=False)
                except Exception: pass
        if not wav: continue
        hyp = asr(wav); e = cer(text, hyp)
        if best is None or e < best[0]: best = (e, hyp); shutil.copy(wav, out)
        if e <= 0.2: break
        time.sleep(3)
    if best is None: print('FAILED', L['id'], flush=True); continue
    qc[L['id']] = {'cer': round(best[0], 3), 'asr': best[1], 'takes': take + 1}
    json.dump(qc, open(qcp, 'w'), ensure_ascii=False, indent=0)
    print(f"{i + 1}/{len(lines)} {L['id']} cer={best[0]:.2f} takes={take + 1} ({time.time() - t0:.0f}s)", flush=True)
print('DONE')
