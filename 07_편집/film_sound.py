"""소리: 대사 공간감, 원본 현장음, 배경음, 효과음, 음악을 만들고 섞는다. film_build.py가 부른다."""
import os, subprocess, math
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt, fftconvolve, resample_poly
from film_spec import *
os.chdir(ROOT)
SR = 48000
RNG = np.random.default_rng(7)
OUT = '07_편집/film/소리/'
os.makedirs(OUT, exist_ok=True)


def db(x):
    return 10 ** (x / 20)


def load(p):
    r = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2).astype(np.float64)


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output='sos'), x, axis=0)


def ir(dur, rt, lp, pre, er):
    n = int(dur * SR)
    t = np.arange(n) / SR
    h = RNG.normal(size=(n, 2)) * np.exp(-6.9 * t / rt)[:, None]
    h = filt(filt(h, 'low', lp), 'high', 180)
    h /= np.sqrt((h ** 2).sum(0)).mean()
    out = np.zeros((n + int(pre * SR), 2))
    out[int(pre * SR):] = h
    for ms, g in er:
        k = int(ms / 1000 * SR)
        out[k, 0] += g * RNG.uniform(.6, 1); out[k + 37, 1] += g * RNG.uniform(.6, 1)
    return out


IR = {'room': (ir(.5, .32, 4500, .008, [(6, .25), (11, .2), (17, .12)]), .16), 'alley': (ir(1.1, .9, 3200, .03, [(38, .16), (71, .1)]), .15),
      'class': (ir(1.0, .75, 4200, .015, [(13, .2), (23, .16), (37, .1)]), .20), 'far': (ir(1.2, 1.0, 2600, .02, [(20, .2)]), .6),
      'close': (ir(.4, .25, 5000, .01, []), .05), 'hall': (ir(3.2, 2.8, 3800, .02, []), .4)}


def space(x, k):
    if not k:
        return x
    if k == 'phone':
        y = filt(filt(x, 'high', 420, 4), 'low', 3600, 4)
        y = np.tanh(y * 2.2) / 2.0
        return space(y, 'room')
    h, w = IR[k]
    y = np.stack([fftconvolve(x[:, c], h[:, c]) for c in (0, 1)], 1)
    d = np.zeros_like(y)
    d[:len(x)] = x
    return d * (1 - w * .4) + y * w * (1.0 if k != 'far' else 1.2)


def fade(x, a, b):
    x = x.copy()
    n, m = int(a * SR), int(b * SR)
    if n:
        n = min(n, len(x)); x[:n] *= (np.sin(np.linspace(0, np.pi / 2, n)) ** 2)[:, None]
    if m:
        m = min(m, len(x)); x[-m:] *= (np.cos(np.linspace(0, np.pi / 2, m)) ** 2)[:, None]
    return x


def limit(x, c):
    from scipy.ndimage import maximum_filter1d, uniform_filter1d
    pk = maximum_filter1d(np.abs(x).max(1), 721)
    g = np.minimum(1, c / (pk + 1e-9))
    g = uniform_filter1d(-maximum_filter1d(-g, 721), 721)
    return x * g[:, None]


def rms(x):
    return 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9)


def loopn(x, n):
    """겹쳐 이어 길게 만든다."""
    xf = int(1.0 * SR)
    x = x[int(.2 * SR):len(x) - int(.2 * SR)]
    out = x
    while len(out) < n:
        a = np.linspace(0, 1, xf)[:, None]
        out = np.concatenate([out[:-xf], out[-xf:] * np.sqrt(1 - a) + x[:xf] * np.sqrt(a), x[xf:]])
    return out[:n]


# ---------- 음악: 오르골과 낮은 지속음을 직접 합성
def mtof(m):
    return 440 * 2 ** ((m - 69) / 12)


def bell(f, vel=1., dur=2.6, det=0.):
    t = np.arange(int(dur * SR)) / SR
    f = f * 2 ** (det / 1200)
    y = np.zeros_like(t)
    for r, a, d in ((1, 1, 1.5), (2.0, .22, .9), (3.01, .10, .5), (5.4, .13, .22), (8.9, .05, .09)):
        if f * r < 15000:
            y += a * np.sin(2 * np.pi * f * r * t + r) * np.exp(-t / d * 2.1)
    y += .03 * RNG.normal(size=len(t)) * np.exp(-t / .004)
    y *= np.minimum(1, t / .0015)
    return y * vel * .22


def pad(ms, dur, lp=900, a=2., r=2.5, wob=.0):
    n = int(dur * SR); t = np.arange(n) / SR
    o = np.zeros((n, 2))
    for m in ms:
        for c, dt in ((0, -5), (1, 5), (0, 3), (1, -3)):
            f = mtof(m) * 2 ** (dt / 1200)
            ph = 2 * np.pi * f * t + wob * np.sin(2 * np.pi * .23 * t + m)
            o[:, c] += (np.sin(ph) + .35 * np.sin(2 * ph) + .16 * np.sin(3 * ph)) / len(ms)
    o = filt(o, 'low', lp)
    e = np.minimum(1, t / a) * np.minimum(1, (dur - t) / r)
    return o * e[:, None] * .10


MOT = [(76, 1), (69, 1), (72, 1), (71, 1), (69, 1), (64, 1), (65, 1), (69, 1), (72, 1), (71, 3),
       (76, 1), (68, 1), (71, 1), (72, 1), (71, 1), (68, 1), (69, 1.5), (71, .5), (68, 1), (69, 3)]
BAS = [(45, 3), (40, 3), (41, 3), (40, 3), (40, 3), (44, 3), (41, 3), (45, 3)]


def box(dur, beat, t0=0., notes=None, det=lambda t: 0, vel=1., bass=True, tr=0, skip=0., slow=0., bright=True):
    n = int((dur + 4) * SR)
    o = np.zeros((n, 2))
    notes = notes or MOT

    def put(t, m, v, pan):
        if t < 0 or t > dur:
            return
        y = bell(mtof(m + tr), v, 2.8, det(t) + RNG.normal() * 3)
        k = int((t + RNG.normal() * .006 + .01) * SR)
        e = min(len(y), n - k)
        o[k:k + e, 0] += y[:e] * math.cos(pan); o[k:k + e, 1] += y[:e] * math.sin(pan)
    t = t0; b = beat
    while t < dur:
        for m, l in notes:
            if t >= dur:
                break
            if RNG.random() >= skip:
                put(t, m + (12 if bright else 0), vel * RNG.uniform(.8, 1), .72)
            t += l * b; b *= 1 + slow * l
    if bass:
        t = t0
        while t < dur:
            for m, l in BAS:
                put(t, m + 12, vel * .55, .9); put(t + beat, m + 24, vel * .28, .6); put(t + 2 * beat, m + 24 + 3, vel * .25, .65)
                t += l * beat
    y = space(o, 'hall')
    return y[:int((dur + 3.5) * SR)]


def drone(dur, root=33, grow=1., lp=260):
    n = int(dur * SR); t = np.arange(n) / SR
    o = np.zeros((n, 2))
    for c in (0, 1):
        o[:, c] = np.sin(2 * np.pi * mtof(root) * t) + .5 * np.sin(2 * np.pi * mtof(root) * 1.0035 * t + c) + .28 * np.sin(2 * np.pi * mtof(root + 13) * t * 1.001 + c)
    nz = filt(RNG.normal(size=(n, 2)), 'band', [90, lp]) * 1.4
    o = o * .5 + nz * (.6 + .4 * np.sin(2 * np.pi * .11 * t))[:, None]
    e = (t / dur) ** grow
    return o * e[:, None] * .09


def music(T, total):
    """T(컷, 시점) -> 초. (이름, 시작초, 소리) 목록."""
    cues = []

    def add(name, t, y, level, a=.02, b=1.5):
        y = fade(y, a, b)
        y = y * db(level - rms(y[np.abs(y).max(1) > 1e-4]))
        cues.append((name, t, y))
    # M1 휴대폰에서 나오는 밝은 오르골 (화면 안의 소리). 화면이 꺼지면 끊긴다
    a, b = T('01', 2.1), T('04', .5)
    y = box(b - a, .40, vel=1, bass=True)[:int((b - a) * SR)]
    add('M1_휴대폰', a, space(filt(y, 'high', 300), 'phone'), -37, .4, .03)
    # M2 발견: 낮은 지속음 + 제목에서 주제가 온전히 나옴
    a = T('07', 0)
    add('M2a_발견', a, pad([45, 52, 57], T('09', 2.5) - a + 3, 600, 2.5, 4), -42, .5, 3)
    a = T('09', 3.4)
    add('M2b_제목', a, np.concatenate([box(T('10', .9) - a, .62, det=lambda t: 0, vel=1, bass=False)]), -33, .02, 2.5)
    # M3 첫 성공: 가장 따뜻하게
    a, b = T('13', .6), T('15b', 2.4)
    y = box(b - a, .48, vel=1, bass=True)
    p = pad([57, 60, 64, 69], (b - a) + 1.5, 1400, 1.5, 2.5)
    n = max(len(y), len(p)); z = np.zeros((n, 2)); z[:len(y)] += y; z[:len(p)] += p * 2.2
    add('M3_첫성공', a, z, -34, .05, 2.2)
    # M4 의존: 조금 빠르고 기계적인 반복, 19에서 멈춤
    a, b = T('17', .6), T('19', 2.2)
    y = box(b - a, .30, vel=1, bass=True, det=lambda t: -4 * t)
    add('M4_의존', a, y[:int((b - a + .6) * SR)], -33, .02, .6)
    # M5 변화: 어긋난 음정, 빈 자리가 생김
    a, b = T('20', .2), T('23', 3.3)
    y = box(b - a, .56, vel=.9, bass=False, det=lambda t: -18 - 2.2 * t + 10 * math.sin(t), skip=.18)
    p = pad([44, 45, 52], b - a + 2, 420, 2, 2.5, .6)
    n = max(len(y), len(p)); z = np.zeros((n, 2)); z[:len(y)] += y; z[:len(p)] += p * 2.4
    add('M5_변화', a, z, -35, .3, 2.0)
    # M6 잠식: 커지는 저음, 끊긴 주제. 실이 끊어지는 순간 모두 멈춤
    a, b = T('24', 2.2), T('29', 4.65)
    d = drone(b - a, 33, 1.3)
    y = box(b - a, .9, vel=.7, bass=False, det=lambda t: -35 - 4 * t, skip=.55, tr=-12)
    p = pad([45, 46, 51], b - a, 380, 6, .3, 1.2) * np.linspace(.4, 2.6, int((b - a) * SR))[:, None]
    z = d * 2.2 + p; y = y[:len(z)]; z[:len(y)] += y * .9
    add('M6_잠식', a, z, -32, 1.5, .03)
    # M7 등교: 겉으로는 평온한 얇은 화음
    a, b = T('30', 1.0), T('36b', .05)
    p = pad([57, 64, 71], b - a, 1100, 4, .4, .25)
    y = box(b - a, 1.05, vel=.6, bass=False, det=lambda t: -10 + 12 * math.sin(t * .5), skip=.45)
    z = p * 1.6; y = y[:len(z)]; z[:len(y)] += y * .55
    add('M7_등교', a, z, -41, 2.5, .25)
    # M8 거울: 36b 뒤의 저음이 거울까지, 교차에서 맥박이 빨라짐
    a, b = T('36b', 2.5), T('40_거울', 0)
    add('M8a_거울', a, drone(b - a, 31, 1.6, 220), -34, .6, .4)
    a = T('40_거울', 0); e = total['end40']
    d = drone(e - a, 33, .7) * 1.4
    t = np.arange(len(d)) / SR
    k, per = 2.9, .62  # 맥박
    while a + k < e - 1.5:
        n0 = int(k * SR); L = min(int(.35 * SR), len(d) - n0)
        tt = np.arange(L) / SR
        d[n0:n0 + L] += (np.sin(2 * np.pi * (46 + 40 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 11))[:, None] * .22
        k += per; per = max(.10, per * .86)
    s = filt(RNG.normal(size=d.shape), 'band', [1800, 5200]) * np.clip((t - 4) / 5, 0, 1)[:, None] ** 2 * .03
    hi = pad([88, 89], e - a, 6000, 4, .05, 2.) * np.clip((t - 3) / 5, 0, 1)[:, None] ** 2 * 1.2
    add('M8b_교차', a, d + s + hi[:len(d)], -28, .2, .015)
    # M9 끝: 늘어진 주제 네 음
    a = T('제목끝', .4)
    o = box(4.2, .8, notes=[(76, 1), (69, 1), (72, 1.4), (71, 9)], det=lambda t: -30 - 9 * t, bass=False, slow=.06)
    add('M9_끝', a, o, -35, .02, 2.5)
    return cues


def build(T, span, total, vo, log=print):
    """T(컷,시점)=초, span(컷)=(시작초,끝초). 트랙별 (이름, 시작초, 소리)"""
    tr = {'대사': [], '현장음': [], '배경음': [], '효과음': [], '음악': []}
    N = int(math.ceil(total['dur'] * SR))
    for i, (c, n, s, e, t, txt, sp, g) in enumerate(DLG):
        x = load(vo(n)); e = len(x) / SR if e is None else e
        y = fade(x[int(s * SR):int(e * SR)], .008, .02)
        y = filt(y, 'high', 90)
        y = space(y, sp)
        tr['대사'].append((f'{n}_{i}', T(c, t), fade(y, 0, .05) * db(g - 2.5)))
    for c, a, b, g in ORIG:
        x = load(f'07_편집/film/원본소리/CUT{c}.wav')[int(a * SR):int(b * SR)]
        x = filt(x, 'high', 60)
        if c in ('14', '15b', '16', '17', '20', '25', '24', '28'):  # 지직거리는 높은 잡음을 줄인다
            x = filt(x, 'low', 4200)
        tr['현장음'].append((f'CUT{c}', T(c, a), fade(x, .12 if c not in ('09',) else .03, .15) * db(g)))
    for n, f, a, b, lv, fi, fo, flt in AMB:
        t0, t1 = T(*a), T(*b)
        x = load(f'07_편집/효과음/{f}.mp3')
        x = loopn(x, int((t1 - t0) * SR))
        if flt == 'window':
            x = filt(x, 'low', 1900) ; x = filt(x, 'high', 250)
        x = x * db(lv - rms(x))
        if flt == 'class':  # 36b부터 먹먹해진다
            k0, k1 = int((T('36b', 1.6) - t0) * SR), int((T('37A', 3.5) - t0) * SR)
            m = np.zeros(len(x)); m[k0:k1] = np.linspace(0, 1, k1 - k0); m[k1:] = 1
            lo = filt(filt(x, 'low', 380, 4), 'high', 60)
            x = x * (1 - m)[:, None] + lo * (m * 1.5)[:, None]
        tr['배경음'].append((n, t0, fade(x, fi, fo)))
    for i, (c, t, f, pk, sp) in enumerate(SFX):
        x = load(f'07_편집/효과음/{f}.mp3')
        th = np.abs(x).max(1); on = np.where(th > th.max() * .04)[0]
        x = x[max(0, on[0] - 400):on[-1] + 2400] if len(on) else x
        x = filt(x, 'high', 45)
        y = space(fade(x, .004, .08), sp)
        y *= db(pk) / (np.abs(y).max() + 1e-9)
        if f.startswith('실당김') and c == '29' and t > 3:
            y = y[:int((4.68 - t) * SR)]; y = fade(y, 0, .006)
        if f == '알람_1':
            lim = {'18a': 2.2, '30': 2.2}[c]; y = fade(y[:int(lim * SR)], 0, .12)
        if f.startswith('발소리'):
            c1 = span(c)[1]; y = fade(y[:int(max(.3, c1 - T(c, t)) * SR)], .02, .15)
        if f.startswith('연필_'):
            y = fade(y[:int((span(c)[1] - T(c, t)) * SR)], .05, .2)
        tr['효과음'].append((f'{f}_{i}', T(c, t), y))
    mus = music(T, total)
    # 대사 구간에서 음악과 강의실 소리를 낮춘다
    env = np.zeros(N)
    for n, t, y in tr['대사']:
        a, b = int((t - .15) * SR), int((t + len(y) / SR) * SR)
        env[max(0, a):b] = 1
    w = int(.25 * SR); env = np.clip(fftconvolve(env, np.hanning(w) / np.hanning(w).sum(), 'same'), 0, 1)

    def duck(t, y, d):
        k = int(t * SR); e = env[k:k + len(y)]
        e = np.pad(e, (0, len(y) - len(e)))
        return y * (10 ** (-d * e / 20))[:, None]
    tr['음악'] = [(n, t, duck(t, y, 0 if n == 'M1_휴대폰' else 4.5)) for n, t, y in mus]
    tr['배경음'] = [(n, t, duck(t, y, 4) if n == '강의실' else y) for n, t, y in tr['배경음']]
    for k in ('대사', '현장음'):  # 갑자기 튀는 소리를 부드럽게 누른다
        tr[k] = [(n, t, limit(y, db(-10.5 if k == '대사' else -16))) for n, t, y in tr[k]]
    stems = {}
    for k, l in tr.items():
        m = np.zeros((N, 2))
        for j, (n, t, y) in enumerate(l):
            a = int(round(t * FPS)) / FPS if k != '대사' else t
            a = round(t * SR)
            e = min(len(y), N - a)
            if e <= 0:
                continue
            if e < len(y):
                y = fade(y[:e], 0, min(1.8, e / SR / 2))
            m[a:a + e] += y[:e]
            l[j] = (n, t, y[:e])
        stems[k] = m
        log(f'{k}: {len(l)}개, 최고 {20*np.log10(np.abs(m).max()+1e-9):.1f} dB')
    return tr, stems, N
