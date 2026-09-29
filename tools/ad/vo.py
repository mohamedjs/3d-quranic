import sys, shutil, json, time
sys.path.insert(0, '/root/omni/tools')
from gradio_client import Client, handle_file
from score import asr, cer
URL = 'https://cc6b8e54f77bc75eac.gradio.live/'
A = '/root/omni/tools/voice_design_omni/'
REF = {'narrator': ('narrator-2', 'يلا بينا نبدأ مغامرة جديدة! روح للجدّة زينب عند الترعة، مستنياك على المصطبة.'),
       'player': ('player-2', 'يا جدّي، احكِ لي الحكاية من فضلك! أنا أحبّ قصص القرآن كثيرًا.')}
L = [('n1','narrator','يلا بينا نبدأ مغامرة جديدة!'),
     ('n2','narrator','امشي ورا السهم الدهبي… واجمع العملات اللي على الطريق!'),
     ('n3','narrator','وأهل القرية مستنيينك… كل واحد عنده حكاية.'),
     ('n4','narrator','حكايات من القرآن، وقصص الأنبياء، وقصص الصحابة.'),
     ('n5','narrator','وتسمع الآيات بصوت الشيخ المنشاوي، ومعناها ببساطة.'),
     ('n6','narrator','تلات مستويات، وبتشتغل من غير نت، على أي موبايل.'),
     ('n7','narrator','رحلة القرآن… العبها دلوقتي ببلاش!')]
c = Client(URL, verbose=False); out = {}
for k, sp, text in L:
    anchor, rt = REF[sp]; best = None
    for take in range(3):
        wav, _ = c.predict(text, 'Egyptian Arabic', handle_file(A + anchor + '.wav'), rt, '', 32, 2.0, True, 0.95, None, True, True, api_name='/_clone_fn')
        h = asr(wav); e = cer(text, h)
        if best is None or e < best: best = e; shutil.copy(wav, f'/tmp/ad/vo/{k}.wav')
        if e <= 0.12: break
    out[k] = best; print(k, round(best, 2), h, flush=True)
print('DONE', out)
