#!/usr/bin/env python3
"""Generate every Arabic dialogue line with Habibi-TTS (Hugging Face Space, runs on HF's GPUs).
   Needs: network access to huggingface.co + *.hf.space, `pip install gradio_client`,
   and HF_TOKEN=hf_... in the project's .env (your own read token, for your ZeroGPU quota).
   python3 tools/habibi_generate.py        → tools/voice_raw/<enc>__<speaker>-<hash>.wav (resumable)
   python3 tools/voice_import.py tools/voice_raw   → public/audio/*.mp3 + manifest.json"""
import json, os, shutil, sys, time
from gradio_client import Client, handle_file
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = dict(l.strip().split('=', 1) for l in open(os.path.join(ROOT, '.env')) if '=' in l and not l.startswith('#')) if os.path.exists(os.path.join(ROOT, '.env')) else {}
token = os.environ.get('HF_TOKEN') or env.get('HF_TOKEN')
lines = json.load(open(os.path.join(ROOT, 'tools/voice_lines.json')))
voices = json.load(open(os.path.join(ROOT, 'tools/voices.json')))
REFTXT = {'EGY.mp3': 'ايه الكلام. بقولك ايه. استخدم صوتي في المحادثات. استخدمه هيعجبك اوي.',
          'MSA.mp3': 'كان اللعيب حاضرًا في العديد من الأنشطة والفعاليات المرتبطة بكأس العالم، مما سمح للجماهير بالتفاعل معه والتقاط الصور التذكارية.',
          'MAR.mp3': 'إذا بغيتي شي صوت باللهجة المغربية للإعلانات ديالك هذا أحسن واحد غادي تلقاه.',
          'IRQ.wav': 'يعني ااا ما نقدر ناخذ وقت أكثر، ااا لأنه شروط كلش يحتاجلها وقت.',
          'ALG.wav': 'أنيا هكا باغية ناكل هكا أني ن نشوف فيها الحاجة هذيكا.'}
BASE = 'https://huggingface.co/spaces/chenxie95/Habibi-TTS/resolve/main/assets/'
out = os.path.join(ROOT, 'tools/voice_raw'); os.makedirs(out, exist_ok=True)
client = Client('chenxie95/Habibi-TTS', token=token)
todo = [L for L in lines if not os.path.exists(os.path.join(out, L['id'].replace('/', '__') + '.wav'))]
print(len(todo), 'lines to generate')
for i, L in enumerate(todo):
    v = voices[L['speaker']]; ref = v['ref']
    text = L['text'].replace('ﷺ', 'صلى الله عليه وسلم')
    for attempt in range(3):
        try:
            wav, _, _ = client.predict(v['lang'], v['model'], handle_file(BASE + ref), v.get('ref_text') or REFTXT[ref], text, False, 7, api_name='/basic_tts')
            shutil.copy(wav, os.path.join(out, L['id'].replace('/', '__') + '.wav')); break
        except Exception as e:
            msg = str(e); print('  retry', attempt, msg[:160])
            if 'quota' in msg.lower(): sys.exit('ZeroGPU quota used up for today — run again later; finished files are kept.')
            time.sleep(5)
    print(f'{i + 1}/{len(todo)}', L['id'])
