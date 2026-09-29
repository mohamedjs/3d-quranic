#!/usr/bin/env python3
"""Design a native-Arabic anchor voice per character with OmniVoice voice design (several takes each).
   python3 tools/omnivoice_anchors.py <gradio-url> [takes]  → tools/voice_design_omni/<speaker>-<n>.wav"""
import os, sys, shutil
from gradio_client import Client
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'tools/voice_design_omni'); os.makedirs(OUT, exist_ok=True)
TAKES = int(sys.argv[2]) if len(sys.argv) > 2 else 4
ANCHOR = {  # speaker: (gender, age, pitch, sentence)
 'farmer':  ('Male / 男', 'Elderly / 老年', 'Low Pitch / 低音调', 'تعالَ يا حبيبي، اقعد جنبي هنا. سأحكي لك حكايةً جميلةً من القرآن الكريم.'),
 'hamdan':  ('Male / 男', 'Middle-aged / 中年', 'Moderate Pitch / 中音调', 'أهلًا يا صغيري! القافلة وصلت من السوق، تعالَ أحكي لك عن رحلةٍ عظيمة.'),
 'zainab':  ('Female / 女', 'Elderly / 老年', 'Low Pitch / 低音调', 'يا حبيبي، تعالَ اقعد معنا على المصطبة. عندي لك حكايةٌ حلوةٌ عن الصبر.'),
 'amina':   ('Female / 女', 'Elderly / 老年', 'Moderate Pitch / 中音调', 'سؤالٌ جميل يا حبيبي! اسمع القصة من أوّلها، وستعرف الجواب بنفسك.'),
 'player':  ('Male / 男', 'Child / 儿童', 'High Pitch / 高音调', 'يا جدّي، احكِ لي الحكاية من فضلك! أنا أحبّ قصص القرآن كثيرًا.'),
 'narrator':('Male / 男', 'Middle-aged / 中年', 'Moderate Pitch / 中音调', 'يلا بينا نبدأ مغامرة جديدة! روح للجدّة زينب عند الترعة، مستنياك على المصطبة.'),
}
only = [a for a in sys.argv[3:]] or list(ANCHOR)
c = Client(sys.argv[1], verbose=False)
for sp in only:
    g, a, p, text = ANCHOR[sp]
    for n in range(TAKES):
        out = f'{OUT}/{sp}-{n}.wav'
        if os.path.exists(out): continue
        wav, st = c.predict(text, 'Standard Arabic', 32, 2.0, True, 1.0, None, True, True, g, a, p, 'Auto', 'Auto', 'Auto', api_name='/_design_fn')
        shutil.copy(wav, out); print(sp, n, st, flush=True)
print('DONE')
