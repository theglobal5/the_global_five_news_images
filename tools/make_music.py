import numpy as np, wave, sys

SR = 44100
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 29.6
INTRO, STORY, N = 3.0, 4.6, 5
BAR = STORY / 2            # one chord per half-story -> 2.3 s bars
BEAT = BAR / 4             # ~104 BPM
n = int(SR * DUR)
t = np.arange(n) / SR
L = np.zeros(n); R = np.zeros(n)
rng = np.random.default_rng(7)

def midi(m): return 440.0 * 2 ** ((m - 69) / 12)
def env_adsr(length, a, d, s, r):
    e = np.ones(length); ai, di, ri = int(a*SR), int(d*SR), int(r*SR)
    ai = min(ai, length); e[:ai] = np.linspace(0, 1, ai)
    de = min(ai+di, length); e[ai:de] = np.linspace(1, s, de-ai); e[de:] = s
    if ri > 0 and ri < length: e[-ri:] *= np.linspace(1, 0, ri)
    return e
def lowpass(x, cutoff):
    a = np.exp(-2*np.pi*cutoff/SR); y = np.empty_like(x); acc = 0.0
    for i in range(len(x)): acc = (1-a)*x[i] + a*acc; y[i] = acc
    return y
def add(sig, start, gain=1.0, pan=0.0):
    i = int(start*SR)
    if i >= n: return
    sig = sig[:n-i]
    L[i:i+len(sig)] += sig*gain*(1 - max(pan, 0))
    R[i:i+len(sig)] += sig*gain*(1 + min(pan, 0))

# A minor news-style progression: Am  F  C  G
CHORDS = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
ROOTS = [45, 41, 48, 43]

# --- pads (warm, detuned, slow attack)
bar = 0; start = 0.0
while start < DUR:
    ch = CHORDS[bar % 4]; ln = int(BAR*SR)+int(0.4*SR); tt = np.arange(ln)/SR
    sig = np.zeros(ln)
    for m in ch:
        f = midi(m+12)
        for det in (-0.12, 0.12):
            ff = f*2**(det/12)
            for h, amp in ((1, 1.0), (2, 0.35), (3, 0.15)):
                sig += amp*np.sin(2*np.pi*ff*h*tt + rng.uniform(0, 6.28))
    sig *= env_adsr(ln, 0.5, 0.3, 0.8, 0.6) * 0.018
    add(sig, start, pan=-0.15); add(sig, start, gain=0.9, pan=0.15)
    bar += 1; start += BAR

# --- pulse arpeggio (8th notes) from the first story on
arp_i = 0; tb = INTRO - 2*BEAT
while tb < DUR - 1.2:
    b = int(max(0, tb) // BAR); ch = CHORDS[b % 4]
    m = (ch + [ch[0]+12])[arp_i % 4] + 12
    ln = int(0.32*SR); tt = np.arange(ln)/SR
    sig = (np.sin(2*np.pi*midi(m)*tt) + 0.3*np.sin(2*np.pi*midi(m)*2*tt)) * np.exp(-tt*11)
    add(sig*0.05, max(0, tb), pan=0.25 if arp_i % 2 else -0.25)
    arp_i += 1; tb += BEAT/2

# --- bass on every beat (after intro)
tb = INTRO
while tb < DUR - 1.0:
    b = int(tb // BAR); f = midi(ROOTS[b % 4]-12)
    ln = int(0.5*SR); tt = np.arange(ln)/SR
    sig = (np.sin(2*np.pi*f*tt) + 0.25*np.sin(2*np.pi*f*2*tt)) * np.exp(-tt*5)
    add(sig*0.11, tb); tb += BEAT

# --- soft kick (beats 1 & 3) and hat (offbeats)
tb = INTRO; k = 0
while tb < DUR - 1.0:
    if k % 2 == 0:
        ln = int(0.25*SR); tt = np.arange(ln)/SR
        f = 110*np.exp(-tt*18) + 45
        kick = np.sin(2*np.pi*np.cumsum(f)/SR) * np.exp(-tt*14)
        add(kick*0.22, tb)
    ln = int(0.05*SR); hat = rng.standard_normal(ln)*np.exp(-np.arange(ln)/SR*90)
    hat = hat - lowpass(hat, 6000)
    add(lowpass(hat, 9000)*0.022, tb + BEAT/2, pan=0.3)
    tb += BEAT; k += 1

# --- transition swoosh + low hit at each story start and the outro
marks = [INTRO + i*STORY for i in range(N)] + [INTRO + N*STORY]
for m in marks:
    ln = int(0.6*SR); tt = np.arange(ln)/SR
    noise = rng.standard_normal(ln)
    bp = lowpass(noise - lowpass(noise, 800), 4000)
    sw = bp * (tt/0.6)**3 * 0.035
    add(sw, m-0.6, pan=-0.2)
    ln = int(1.2*SR); tt = np.arange(ln)/SR
    hit = np.sin(2*np.pi*55*tt) * np.exp(-tt*3.5) * 0.18
    add(hit, m)

# --- short rising intro sting
ln = int(1.0*SR); tt = np.arange(ln)/SR
f = 220 + 220*tt
sting = np.sin(2*np.pi*np.cumsum(f)/SR) * np.sin(np.pi*tt) * 0.03
add(sting, 0.2)

# master: fade in/out, gentle saturation, normalise
fade = np.ones(n); fi, fo = int(0.6*SR), int(2.0*SR)
fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo)
st = np.stack([L*fade, R*fade], axis=1)
st = np.tanh(st*1.4)
st = st / np.max(np.abs(st)) * 0.7
pcm = (st*32767).astype(np.int16)
with wave.open(sys.argv[2] if len(sys.argv) > 2 else "music.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("ok", DUR)
