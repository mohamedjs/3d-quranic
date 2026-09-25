#!/usr/bin/env python3
"""Voice every Arabic dialogue line with Azure Neural TTS (free tier F0: 500k chars/month;
   the whole game is ~15k chars). No SDK needed — plain REST.
   Setup: .env in the project root with
       AZURE_SPEECH_KEY=...        (Azure portal → your Speech resource → Keys and Endpoint)
       AZURE_SPEECH_REGION=westeurope   (the resource's region)
   Run:   python3 tools/azure_tts.py            (only missing lines)
          python3 tools/azure_tts.py --all      (re-voice everything, e.g. after changing VOICES)
   → public/audio/<encounter>/<speaker>-<hash>.mp3 + public/audio/manifest.json"""
import json, os, sys, time, urllib.request, urllib.error
from xml.sax.saxutils import escape
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = {}
if os.path.exists(os.path.join(ROOT, '.env')):
    for l in open(os.path.join(ROOT, '.env')):
        if '=' in l and not l.lstrip().startswith('#'):
            k, v = l.strip().split('=', 1); env[k.strip()] = v.strip()
KEY = os.environ.get('AZURE_SPEECH_KEY') or env.get('AZURE_SPEECH_KEY')
REGION = os.environ.get('AZURE_SPEECH_REGION') or env.get('AZURE_SPEECH_REGION')
if not KEY or not REGION: sys.exit('Put AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in .env')

# character → Azure voice + prosody (Egyptian voices where possible; the boy is Salma pitched up)
VOICES = {
    'farmer': dict(voice='ar-EG-ShakirNeural', rate='-8%',  pitch='-8%'),    # Grandpa Salim: slow, deep
    'hamdan': dict(voice='ar-SA-HamedNeural',  rate='-2%',  pitch='-2%'),    # Uncle Hamdan
    'zainab': dict(voice='ar-EG-SalmaNeural',  rate='-12%', pitch='-7%'),    # Grandma Zainab: old, gentle
    'amina':  dict(voice='ar-SA-ZariyahNeural', rate='-10%', pitch='-5%'),   # Grandma Amina
    'player': dict(voice='ar-EG-SalmaNeural',  rate='+4%',  pitch='+16%'),   # the boy
}
lines = json.load(open(os.path.join(ROOT, 'tools/voice_lines.json')))
mpath = os.path.join(ROOT, 'public/audio/manifest.json')
manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
redo = '--all' in sys.argv
url = f'https://{REGION}.tts.speech.microsoft.com/cognitiveservices/v1'
done = 0
for i, L in enumerate(lines):
    rel = 'audio/' + L['id'] + '.mp3'; out = os.path.join(ROOT, 'public', rel)
    if not redo and os.path.exists(out) and manifest.get(L['text']) == rel and os.path.getsize(out) > 0 and L['id'] in manifest.get('_azure', []): continue
    v = VOICES[L['speaker']]
    text = escape(L['text'].replace('ﷺ', 'صلى الله عليه وسلم'))
    ssml = (f"<speak version='1.0' xml:lang='ar-EG' xmlns='http://www.w3.org/2001/10/synthesis'>"
            f"<voice name='{v['voice']}'><prosody rate='{v['rate']}' pitch='{v['pitch']}'>{text}</prosody></voice></speak>")
    req = urllib.request.Request(url, data=ssml.encode(), method='POST', headers={
        'Ocp-Apim-Subscription-Key': KEY, 'Content-Type': 'application/ssml+xml',
        'X-Microsoft-OutputFormat': 'audio-24khz-48kbitrate-mono-mp3', 'User-Agent': 'quran-journey'})
    for attempt in range(4):
        try:
            data = urllib.request.urlopen(req, timeout=30).read(); break
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 3: time.sleep(3 * (attempt + 1)); continue
            sys.exit(f'Azure error {e.code}: {e.read()[:300]!r}')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'wb').write(data)
    manifest[L['text']] = rel; manifest.setdefault('_azure', []).append(L['id']) if L['id'] not in manifest.get('_azure', []) else None
    done += 1; print(f'{i + 1}/{len(lines)} {L["speaker"]:7s} {len(data) // 1024} KB  {L["text"][:50]}')
    time.sleep(0.15)
json.dump(manifest, open(mpath, 'w'), ensure_ascii=False, indent=0)
print('voiced', done, 'lines · manifest', len([k for k in manifest if not k.startswith('_')]), 'entries')
