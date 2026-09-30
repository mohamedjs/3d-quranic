"""python3 habibi.py <habibi-gradio-url>  — Arabic (MSA) game lines with Habibi-TTS, cloning the designed anchors."""
import sys, os, json, shutil, time
sys.path.insert(0, '/root/omni/tools')
from gradio_client import Client, handle_file
from score import asr, cer
URL = sys.argv[1]; D = '/root/gv'; OUT = f'{D}/ar_habibi'; RAW = f'{OUT}/raw'; os.makedirs(RAW, exist_ok=True)
A = json.load(open(f'{D}/ar/anchors.json'))
LANG, MODEL = 'MSA (Modern Standard Arabic)', 'Specialized'
lines = json.load(open(f'{D}/voice_lines_ar.json')) if os.path.exists(f'{D}/voice_lines_ar.json') else json.load(open(f'{D}/voice_lines.json'))
extra = f'{D}/extra_ar.json'
if os.path.exists(extra): lines += json.load(open(extra))
qcp = f'{OUT}/qc.json'; qc = json.load(open(qcp)) if os.path.exists(qcp) else {}
c = Client(URL, verbose=False); t0 = time.time()
def call(*a):
    global c
    for i in range(6):
        try: return c.predict(*a, api_name='/basic_tts')[0]
        except Exception as e:
            print('retry', str(e)[:150], flush=True); time.sleep(10)
            try: c = Client(URL, verbose=False)
            except Exception: pass
for i, L in enumerate(lines):
    out = f"{RAW}/{L['id'].replace('/', '__')}.wav"
    if L['id'] in qc and os.path.exists(out) and qc[L['id']]['cer'] <= 0.15: continue
    a = A[L['speaker']]; text = L['text'].replace('ﷺ', 'صلى الله عليه وسلم'); best = None
    for take in range(4):
        w = call(LANG, ('Specialized', 'Unified')[take % 2], handle_file(a['ref']), a['text'], text, True, 0)
        if not w: continue
        e = cer(text, asr(w))
        if best is None or e < best: best = e; shutil.copy(w, out); qc[L['id'] + '#m'] = take % 2
        if e <= 0.12: break
    if best is None: print('FAILED', L['id'], flush=True); continue
    qc[L['id']] = {'cer': round(best, 3), 'takes': take + 1}
    json.dump(qc, open(qcp, 'w'), ensure_ascii=False, indent=0)
    print(f"{i+1}/{len(lines)} {L['id']} cer={best:.2f} t={take+1} ({time.time()-t0:.0f}s)", flush=True)
print('DONE', flush=True)
