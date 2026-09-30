"""python3 gen.py <url> <lang> anchors|lines   — OmniVoice game voices (en/ru lines; ar anchors for Habibi refs)"""
import sys, os, json, shutil, time, re, unicodedata
sys.path.insert(0, '/root/omni/tools')
from gradio_client import Client, handle_file
from score import asr, f0, cer as cer_ar
import jiwer
URL, LG, PH = sys.argv[1], sys.argv[2], sys.argv[3]
D = '/root/gv'; OUT = f'{D}/{LG}'; os.makedirs(OUT, exist_ok=True)
def norm(s):
    s = unicodedata.normalize('NFKC', s.lower()).replace('ё', 'е'); s = re.sub(r"[^\w\s]", ' ', s); return ' '.join(s.split())
def cer(a, b):
    if LG == 'ar': return cer_ar(a, b)
    return jiwer.cer(norm(a), norm(b)) if norm(b) else 1.0
LANG = {'en': 'English', 'ru': 'Russian', 'ar': 'Standard Arabic'}[LG]
PBUH = {'en': 'peace be upon him', 'ru': 'мир ему', 'ar': 'صلى الله عليه وسلم'}[LG]
M, F = 'Male / 男', 'Female / 女'
CH, YA, MA, EL = 'Child / 儿童', 'Young Adult / 青年', 'Middle-aged / 中年', 'Elderly / 老年'
LO, MO, HI = 'Low Pitch / 低音调', 'Moderate Pitch / 中音调', 'High Pitch / 高音调'
DESIGN = {'farmer': (M, EL, LO), 'zainab': (F, EL, MO), 'hamdan': (M, MA, MO), 'amina': (F, YA, HI), 'player': (M, CH, HI), 'narrator': (F, MA, MO)}
SPEED = {'player': 1.0}
ANCHOR = {
 'en': {'farmer': "Come here, my dear, sit next to me. I will tell you a beautiful story from the Quran.",
        'zainab': "Come, my little one, sit with us. I have a lovely story for you about patience.",
        'hamdan': "Welcome, young friend! The caravan has just arrived from the market. Let me tell you about a great journey.",
        'amina': "What a wonderful question! Listen to the story from the beginning, and you will find the answer yourself.",
        'player': "Grandpa, please tell me the story! I love the stories of the Quran so much.",
        'narrator': "Let's begin a new adventure! Walk to the next house in the village, someone is waiting for you."},
 'ru': {'farmer': "Иди сюда, мой дорогой, садись рядом. Я расскажу тебе прекрасную историю из Корана.",
        'zainab': "Иди ко мне, малыш, садись с нами. У меня есть для тебя чудесная история о терпении.",
        'hamdan': "Добро пожаловать, юный друг! Караван только что вернулся с рынка. Я расскажу тебе о великом путешествии.",
        'amina': "Какой замечательный вопрос! Послушай историю с самого начала, и ты сам найдёшь ответ.",
        'player': "Дедушка, расскажи мне историю, пожалуйста! Я очень люблю истории из Корана.",
        'narrator': "Начнём новое приключение! Иди к следующему дому в деревне, там тебя ждут."},
 'ar': {'farmer': "تعالَ يا بُنيّ، اجلس بجانبي. سأحكي لك قصةً جميلةً من القرآن الكريم.",
        'zainab': "تعالَ يا صغيري، اجلس معنا. عندي لك قصةٌ جميلةٌ عن الصبر.",
        'hamdan': "أهلًا بك يا صديقي الصغير! وصلت القافلة الآن من السوق، سأحدّثك عن رحلةٍ عظيمة.",
        'amina': "يا له من سؤالٍ جميل! استمع إلى القصة من أولها، وستعرف الجواب بنفسك.",
        'player': "يا جدّي، احكِ لي القصة من فضلك! أنا أحبّ قصص القرآن كثيرًا.",
        'narrator': "هيا نبدأ مغامرةً جديدة! امشِ إلى البيت التالي في القرية، هناك من ينتظرك."},
}
c = Client(URL, verbose=False)
def call(fn, *a):
    global c
    for i in range(6):
        try: return c.predict(*a, api_name=fn)[0]
        except Exception as e:
            print('retry', str(e)[:120], flush=True); time.sleep(10)
            try: c = Client(URL, verbose=False)
            except Exception: pass
AP = f'{OUT}/anchors.json'
if PH == 'anchors':
    res = json.load(open(AP)) if os.path.exists(AP) else {}
    for sp, (g, age, p) in DESIGN.items():
        if sp in res: continue
        text = ANCHOR[LG][sp]; takes = []
        for n in range(4):
            w = call('/_design_fn', text, LANG, 32, 2.0, True, 1.0, None, True, True, g, age, p, 'Auto', 'Auto', 'Auto')
            if not w: continue
            f = f'{OUT}/anchor_{sp}_{n}.wav'; shutil.copy(w, f)
            e = cer(text, asr(f)); hz = f0(f)[0]; takes.append((round(e, 3), n, round(hz))); print(LG, sp, n, e, hz, flush=True)
        e, n, hz = min(takes)
        res[sp] = {'ref': f'{OUT}/anchor_{sp}_{n}.wav', 'text': text, 'cer': e, 'f0': hz, 'takes': takes}
        json.dump(res, open(AP, 'w'), ensure_ascii=False, indent=1)
    print('ANCHORS DONE', flush=True); sys.exit()
A = json.load(open(AP))
lines = json.load(open(f'{D}/voice_lines_{LG}.json'))
qcp = f'{OUT}/qc.json'; qc = json.load(open(qcp)) if os.path.exists(qcp) else {}
RAW = f'{OUT}/raw'; os.makedirs(RAW, exist_ok=True); t0 = time.time()
for i, L in enumerate(lines):
    out = f"{RAW}/{L['id'].replace('/', '__')}.wav"
    if L['id'] in qc and os.path.exists(out): continue
    a = A[L['speaker']]; text = L['text'].replace('ﷺ', PBUH); best = None
    for take in range(3):
        w = call('/_clone_fn', text, LANG, handle_file(a['ref']), a['text'], '', 32, 2.0, True, SPEED.get(L['speaker'], 0.95), None, True, True)
        if not w: continue
        e = cer(text, asr(w))
        if best is None or e < best: best = e; shutil.copy(w, out)
        if e <= 0.1: break
    if best is None: print('FAILED', L['id'], flush=True); continue
    qc[L['id']] = {'cer': round(best, 3), 'takes': take + 1}
    json.dump(qc, open(qcp, 'w'), ensure_ascii=False, indent=0)
    print(f"{i+1}/{len(lines)} {L['id']} cer={best:.2f} t={take+1} ({time.time()-t0:.0f}s)", flush=True)
print('DONE', flush=True)
