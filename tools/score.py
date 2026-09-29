import re, sys, json, glob, os, numpy as np, librosa
from gradio_client import Client, handle_file
import jiwer
def norm(s):
    s = s.replace('ﷺ', 'صلى الله عليه وسلم')
    s = re.sub(r'[ً-ْٰـ]', '', s)
    s = re.sub('[إأآٱ]', 'ا', s).replace('ى', 'ي').replace('ة', 'ه').replace('ؤ', 'و').replace('ئ', 'ي')
    s = re.sub(r'[^ء-ي\s]', ' ', s)
    return ' '.join(s.split())
def cer(ref, hyp): return jiwer.cer(norm(ref), norm(hyp)) if norm(hyp) else 1.0
def f0(path):
    y, sr = librosa.load(path, sr=16000)
    f, v, _ = librosa.pyin(y, fmin=60, fmax=500, sr=sr)
    f = f[~np.isnan(f)]; return float(np.median(f)) if len(f) else 0.0, len(y) / sr
_c = None
def asr(path):
    global _c
    for i in range(4):
        try:
            _c = _c or Client('mrfakename/fast-whisper-turbo', verbose=False)
            return _c.predict(handle_file(path), 'transcribe', api_name='/transcribe')
        except Exception as e:
            _c = None; import time; time.sleep(5)
    return ''
