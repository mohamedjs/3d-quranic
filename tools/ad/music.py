import numpy as np, soundfile as sf
SR=44100; T=43.0; N=int(SR*T); rng=np.random.default_rng(3)
mix=np.zeros((N,2))
bpm=100; beat=60/bpm
def add(sig,t,pan=0.0,g=1.0):
    i=int(t*SR); j=min(N,i+len(sig))
    if i>=N: return
    l=np.sqrt((1-pan)/2); r=np.sqrt((1+pan)/2)
    mix[i:j,0]+=sig[:j-i]*g*l; mix[i:j,1]+=sig[:j-i]*g*r
def ks(freq,dur=1.2,bright=0.5):   # Karplus-Strong pluck (oud / qanun-ish)
    n=int(SR*dur); p=int(SR/freq); buf=rng.uniform(-1,1,p)
    # soften the excitation
    for _ in range(2): buf=0.5*(buf+np.roll(buf,1))
    out=np.zeros(n); dec=0.996-0.004*(1-bright)
    for i in range(n):
        out[i]=buf[i%p]; buf[i%p]=dec*0.5*(buf[i%p]+buf[(i+1)%p])
    env=np.minimum(1,np.arange(n)/60); return out*env
def hz(m): return 440*2**((m-69)/12)
# D major pentatonic-ish with a little oriental colour
scale=[62,64,66,69,71,74,76,78,81]
def pad(ms,dur):
    n=int(SR*dur); t=np.arange(n)/SR; s=np.zeros(n)
    for m in ms:
        f=hz(m)
        for det in (-0.004,0.004): s+=np.sin(2*np.pi*f*(1+det)*t)+0.25*np.sin(2*np.pi*2*f*(1+det)*t)
    env=np.minimum(1,t/1.2)*np.minimum(1,(dur-t)/1.2); return s*env/len(ms)/4
def doum():
    n=int(SR*0.35); t=np.arange(n)/SR; f=110*np.exp(-t*9)+55
    return np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*9)
def tek():
    n=int(SR*0.09); t=np.arange(n)/SR; x=rng.uniform(-1,1,n)
    x=np.diff(np.concatenate([[0],x]))  # brighter
    return x*np.exp(-t*55)*0.5
def shaker():
    n=int(SR*0.06); t=np.arange(n)/SR; x=rng.uniform(-1,1,n); x=np.diff(np.concatenate([[0],np.diff(np.concatenate([[0],x]))]))
    return x*np.exp(-t*70)*0.12
chords=[[62,66,69],[67,71,74],[64,67,71],[69,73,76]]   # D G Em A
bar=4*beat
# pad through the whole piece (quiet)
t=0; k=0
while t<T:
    add(pad(chords[k%4],bar+1.2),t,0,0.55); t+=bar; k+=1
# drums from 3.8 s (after the intro), stop at 36.2, hit on 36.2
t=3.8
while t<36.1:
    b=int(round((t-3.8)/beat))%8
    if b in (0,3,4): add(doum(),t,0,0.9)
    if b in (1,2,5,6,7): add(tek(),t,0.25,0.55)
    for s in (0,0.5): add(shaker(),t+s*beat,-0.4,1)
    t+=beat
# melody: playful motif over the bars
motif=[0,2,4,5,4,2,3,2, 1,2,4,6,5,4,2,1]
t=3.8; i=0
while t<35.8:
    m=scale[motif[i%len(motif)]]
    if i%8 not in (7,): add(ks(hz(m),0.9,0.7),t,0.15,0.32)
    if i%4==0: add(ks(hz(m-12),1.4,0.4),t,-0.2,0.28)
    t+=beat/2; i+=1
# intro sparkle (0–3.8): rising plucks
for j,m in enumerate([62,66,69,74,78,81]): add(ks(hz(m),1.6,0.8),0.25+j*0.28,(-0.5+j*0.2),0.3)
# outro: big D chord at 36.2 + gentle arpeggio, fade to 43
for m in (50,62,66,69,74): add(ks(hz(m),3.5,0.6),36.2,0,0.35)
add(doum(),36.2,0,1.2)
for j,m in enumerate([74,78,81,86,81,78,74,69]): add(ks(hz(m),1.2,0.8),37.0+j*beat/2,(-0.4+j*0.1),0.22)
# fade
fade=np.ones(N); fs=int(SR*41.5); fade[fs:]=np.linspace(1,0,N-fs); mix*=fade[:,None]
mix/=np.max(np.abs(mix))*1.12
sf.write('/tmp/ad/audio/music.wav',mix,SR)
# ---- sfx
def chime():
    n=int(SR*0.5); t=np.arange(n)/SR
    s=(np.sin(2*np.pi*1568*t)+0.6*np.sin(2*np.pi*2349*t)+0.3*np.sin(2*np.pi*3136*t))*np.exp(-t*9)
    return s*0.35
def pop():
    n=int(SR*0.12); t=np.arange(n)/SR; f=600+900*np.exp(-t*40)
    return np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*30)*0.5
def whoosh(d=0.5):
    n=int(SR*d); t=np.arange(n)/SR; x=rng.uniform(-1,1,n)
    # crude band sweep via moving average widths
    env=np.sin(np.pi*t/d)**2; y=np.convolve(x,np.ones(8)/8,'same')
    return y*env*0.35
for name,s in (('chime',chime()),('pop',pop()),('whoosh',whoosh())): sf.write(f'/tmp/ad/audio/{name}.wav',s,SR)
print('ok')
