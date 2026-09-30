import sys, os, json, shutil, time, re, unicodedata
sys.path.insert(0, '/root/omni/tools')
from gradio_client import Client, handle_file
from score import asr
import jiwer
URL = 'https://cc6b8e54f77bc75eac.gradio.live/'
OUT = '/tmp/ad/i18n/vo'; os.makedirs(OUT, exist_ok=True)
def norm(s):
    s = unicodedata.normalize('NFKC', s.lower()).replace('ё', 'е')
    s = re.sub(r"[^\w\s]", ' ', s); return ' '.join(s.split())
def cer(a, b): return jiwer.cer(norm(a), norm(b)) if norm(b) else 1.0
LANG = {'en': 'English', 'ru': 'Russian'}
DESIGN = {  # role: (gender, age, pitch)
 'narrator': ('Male / 男', 'Middle-aged / 中年', 'Moderate Pitch / 中音调'),
 'farmer':   ('Male / 男', 'Elderly / 老年', 'Low Pitch / 低音调'),
 'player':   ('Male / 男', 'Child / 儿童', 'High Pitch / 高音调'),
}
ANCHOR = {
 'en': {'narrator': "Let's go on a new adventure! Walk to grandma's house by the canal, she is waiting for you.",
        'farmer': "Come here, my dear, sit next to me. I will tell you a beautiful story from the Quran.",
        'player': "Grandpa, please tell me the story! I love the stories of the Quran so much."},
 'ru': {'narrator': "Давай отправимся в новое приключение! Иди к дому бабушки у канала, она тебя ждёт.",
        'farmer': "Иди сюда, мой дорогой, садись рядом. Я расскажу тебе прекрасную историю из Корана.",
        'player': "Дедушка, расскажи мне историю, пожалуйста! Я очень люблю истории из Корана."},
}
LINES = json.load(open('/tmp/ad/i18n/lines.json'))
c = Client(URL, verbose=False)
def call(fn, *a):
    for i in range(4):
        try: return c.predict(*a, api_name=fn)[0]
        except Exception as e: print('retry', e, flush=True); time.sleep(8)
best = {}
for lg in ('en', 'ru'):
    for role, (g, age, p) in DESIGN.items():
        text = ANCHOR[lg][role]; takes = []
        for n in range(3):
            w = call('/_design_fn', text, LANG[lg], 32, 2.0, True, 1.0, None, True, True, g, age, p, 'Auto', 'Auto', 'Auto')
            f = f'{OUT}/anchor_{lg}_{role}_{n}.wav'; shutil.copy(w, f)
            e = cer(text, asr(f)); takes.append((e, n)); print(lg, role, n, round(e, 3), flush=True)
        e, n = min(takes); best[(lg, role)] = (f'{OUT}/anchor_{lg}_{role}_{n}.wav', text)
json.dump({f'{k[0]}:{k[1]}': v for k, v in best.items()}, open(f'{OUT}/anchors.json', 'w'), ensure_ascii=False, indent=1)
# lines, cloned from the chosen anchors, Whisper-checked (up to 3 takes)
for lg in ('en', 'ru'):
    for key, (role, text) in LINES[lg].items():
        ref, rtxt = best[(lg, role)]; out = f'{OUT}/{lg}_{key}.wav'; bst = None
        for take in range(3):
            w = call('/_clone_fn', text, LANG[lg], handle_file(ref), rtxt, '', 32, 2.0, True, 0.95 if role != 'player' else 1.0, None, True, True)
            e = cer(text, asr(w))
            if bst is None or e < bst: bst = e; shutil.copy(w, out)
            if e <= 0.08: break
        print('LINE', lg, key, round(bst, 3), flush=True)
print('DONE')
