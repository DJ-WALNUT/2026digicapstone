"""제목 타이포그래피: 자모를 천 조각으로 잘라 꿰맨다. (글꼴을 쓰지 않고 직접 지은 글자)
uv run --no-project --with opencv-python-headless --with numpy --with scipy python -X utf8 07_편집/film_title.py [시험]"""
import os, sys, subprocess, math
import numpy as np, cv2
from scipy.ndimage import gaussian_filter, map_coordinates
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
OUT = '07_편집/film/소스/'
W, H = 1920, 1080
rng = np.random.default_rng(11)


def rd(p):
    return cv2.imdecode(np.fromfile(p, np.uint8), 1)


# ---- 천: 영화 이미지의 결(밝기 무늬)을 뽑아 쓴다
def grain(path, box, sc=1.0):
    x0, y0, x1, y1 = box
    g = cv2.cvtColor(rd(path)[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).astype(np.float32)
    g = g / (cv2.GaussianBlur(g, (0, 0), 22) + 1)
    g = cv2.resize(g, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
    row = np.concatenate([g, g[:, ::-1]], 1); til = np.concatenate([row, row[::-1]], 0)
    ny, nx = H // til.shape[0] + 2, W // til.shape[1] + 2
    return np.tile(til, (ny, nx))[:H, :W]


C39 = '05_본제작/CUT39/CUT39_첫장면_FINAL.png'
felt = grain(C39, (1235, 440, 1430, 600), 2.0)
knit = grain('05_본제작/CUT36/CUT36a_첫장면_FINAL.png', (1480, 1230, 1900, 1420), 1.5)
fleece = grain('05_본제작/CUT26/CUT26_첫장면_FINAL.png', (60, 460, 440, 860), 1.5)


def fibers(n, ln, seed, amp):
    r = np.random.default_rng(seed)
    a = np.zeros((H, W), np.float32)
    for _ in range(n):
        x, y = r.uniform(0, W), r.uniform(0, H)
        t = r.uniform(0, 2 * math.pi); c = r.normal() * .05
        pts = []
        for _ in range(int(ln * r.uniform(.5, 1.4))):
            pts.append((x, y)); x += 3 * math.cos(t); y += 3 * math.sin(t); t += c
        if len(pts) > 1:
            cv2.polylines(a, [np.int32(np.array(pts) * 8)], False, float(r.choice([-1, 1])) * r.uniform(.4, 1), 1, cv2.LINE_AA, 3)
    return gaussian_filter(a, .6) * amp


fib = fibers(15000, 12, 3, .10)
weave = .5 + .5 * np.sin(np.arange(W)[None, :] * 2 * math.pi / 7 + (np.arange(H)[:, None] // 4 % 2) * math.pi)
weave = gaussian_filter(weave, .8) - .5
# 이름: (BGR 바탕색, 결, 결의 세기)
CL = {'olive': ((60, 104, 108), felt, 1.5), 'skin': ((142, 178, 212), felt, 1.0), 'jacket': ((104, 138, 162), felt, .6),
      'hair': ((30, 40, 78), felt, 1.4), 'red': ((30, 28, 112), felt, 1.1), 'knit': ((112, 128, 138), felt, 1.5)}


def R(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# ---- 글자: 굵은 천 조각으로 지은 자모 (화면 좌표)
PIECES = [
    ('ㄷ', 'olive', [R(84, 196, 368, 306), R(84, 196, 196, 872), R(84, 760, 376, 872)], -1.6),
    ('ㅐ', 'skin', [R(404, 150, 500, 900), R(480, 470, 590, 574), R(566, 124, 664, 946)], .9),
    ('ㅊ', 'red', [R(834, 120, 948, 214), R(722, 262, 1050, 366), [(842, 350), (940, 350), (880, 600), (806, 884), (694, 858), (790, 580)], [(850, 470), (940, 420), (1072, 820), (968, 872)]], 1.4),
    ('ㅔ', 'jacket', [R(1010, 486, 1120, 588), R(1090, 150, 1178, 900), R(1228, 124, 1318, 946)], -.8),
    ('ㅍ', 'hair', [R(1368, 112, 1846, 206), R(1352, 352, 1862, 448), R(1468, 190, 1556, 368), R(1660, 190, 1748, 368)], 1.0),
    ('ㅜ', 'knit', [R(1338, 490, 1876, 584), R(1562, 560, 1656, 664)], -1.2),
    ('ㅁ', 'skin', None, .8),
]
MU = (1398, 672, 1816, 968, 84)  # ㅁ 바깥과 굵기
EYES = [(1552, 821), (1662, 821)]


def wob(mask, seed, amp=5.0):
    r = np.random.default_rng(seed)
    dx = gaussian_filter(r.normal(size=(H, W)), 26) * 26 * amp * 1.4
    dy = gaussian_filter(r.normal(size=(H, W)), 26) * 26 * amp * 1.4
    fx = gaussian_filter(r.normal(size=(H, W)), 2.0) * 2.0 * 2.2
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    return cv2.remap(mask, (xx + dx + fx).astype(np.float32), (yy + dy + fx).astype(np.float32), cv2.INTER_LINEAR)


def piece(i):
    n, col, polys, rot = PIECES[i]
    m = np.zeros((H, W), np.uint8)
    if polys is None:
        x0, y0, x1, y1, s = MU
        cv2.rectangle(m, (x0, y0), (x1, y1), 255, -1)
        cv2.rectangle(m, (x0 + s, y0 + s - 12), (x1 - s, y1 - s + 12), 0, -1)
    else:
        for p in polys:
            cv2.fillPoly(m, [np.int32(p)], 255)
    # 모서리를 가위로 자른 듯 둥글린다
    m = ((cv2.GaussianBlur(m, (0, 0), 9) > 127) * 255).astype(np.uint8)
    m = cv2.GaussianBlur(wob(m, 40 + i), (0, 0), .8)
    ys, xs = np.where(m > 127)
    c = (xs.mean(), ys.mean())
    m = cv2.warpAffine(m, cv2.getRotationMatrix2D(c, rot, 1), (W, H))
    a = m.astype(np.float32) / 255
    base, tex, k = CL[col]
    th = rng.uniform(-30, 30)
    Mx = cv2.getRotationMatrix2D((W / 2, H / 2), th, 1.25)
    tx = cv2.warpAffine(tex, Mx, (W, H), borderMode=cv2.BORDER_REFLECT)
    fb = cv2.warpAffine(fib, Mx, (W, H), borderMode=cv2.BORDER_REFLECT)
    t = 1 + (tx - 1) * k * 1.3 + fb * 2.3
    # 도톰함: 가장자리가 눌린다
    d = cv2.distanceTransform((a > .5).astype(np.uint8), cv2.DIST_L2, 5)
    hgt = 14 * (1 - np.exp(-d / 15)) + gaussian_filter((t - 1) * 5, 1.0)
    # 바느질: 가장자리를 넘는 짧은 땀
    cs, _ = cv2.findContours((a > .5).astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    st = []
    for cc in sorted(cs, key=len, reverse=True):
        p = cc[:, 0, :].astype(np.float32)
        if len(p) < 120:
            continue
        for q in range(2):
            p[:, q] = np.convolve(np.r_[p[-6:, q], p[:, q], p[:6, q]], np.ones(13) / 13, 'valid')
        L = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
        N = int(L[-1] / 41)
        for j in range(N):
            u = np.searchsorted(L, (j + .5) * L[-1] / N + rng.normal() * 3) % len(p)
            tg = p[(u + 6) % len(p)] - p[u - 6]; tg /= np.hypot(*tg) + 1e-6
            nn = np.array([-tg[1], tg[0]])
            o = p[u] + nn * 8
            if a[int(np.clip(o[1], 0, H - 1)), int(np.clip(o[0], 0, W - 1))] < .5:
                nn = -nn
            sl = tg * rng.normal(0, 6)
            st.append((p[u] + nn * rng.uniform(21, 27) + sl, p[u] - nn * rng.uniform(9, 14) - sl))
    return dict(a=a, t=t, hgt=hgt, base=np.float32(base), st=st, c=c)


PC = [piece(i) for i in range(len(PIECES))]
Ldir = np.array([.62, -.62, .48]); Ldir /= np.linalg.norm(Ldir)


def shade(hgt, k=1.0):
    gy, gx = np.gradient(hgt)
    n = np.stack([-gx * k, -gy * k, np.ones_like(gx) * 1.6], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return np.clip((n * Ldir).sum(-1), 0, 1)


yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
lamp = np.exp(-(((xx - 1380) / 1250) ** 2 + ((yy - 330) / 820) ** 2))
bgh = weave * 2.2 + gaussian_filter(rng.normal(size=(H, W)), 60) * 60 * 10
BG = np.float32([40, 37, 38]) * ((1 + weave * .35 + fib * 1.2)[..., None]) * (.35 + 1.05 * shade(bgh, .6))[..., None]


def draw_st(img, sts, off=(0, 0), M=None, dark=1.0):
    """실땀 하나하나에 그림자와 윗면 빛을 그린다."""
    sh = np.zeros((H, W), np.uint8); bd = np.zeros((H, W), np.uint8); hi = np.zeros((H, W), np.uint8); pn = np.zeros((H, W), np.uint8)
    P = lambda v: (int(round(v[0] * 8)), int(round(v[1] * 8)))
    for p, q in sts:
        if M is not None:
            p = M[:, :2] @ p + M[:, 2]; q = M[:, :2] @ q + M[:, 2]
        cv2.line(sh, P(p + (-4, 5)), P(q + (-4, 5)), 255, 10, cv2.LINE_AA, 3)
        cv2.line(bd, P(p), P(q), 255, 9, cv2.LINE_AA, 3)
        m1, m2 = p * .8 + q * .2, p * .25 + q * .75
        cv2.line(hi, P(m1 + (1.2, -1.6)), P(m2 + (1.2, -1.6)), 255, 2, cv2.LINE_AA, 3)
        for e in (p, q):
            cv2.circle(pn, P(e), 4 * 8, 255, -1, cv2.LINE_AA, 3)
    f = lambda m, s=0: (cv2.GaussianBlur(m, (0, 0), s) if s else m).astype(np.float32)[..., None] / 255
    img = img * (1 - .55 * f(sh, 3)) * (1 - .5 * f(pn, 1.2))
    b = f(bd)
    img = img * (1 - b) + np.float32([26, 20, 24]) * b * dark
    return img + f(hi, 1.3) * np.float32([24, 26, 38]) * dark


def eye(img, c, r, op):
    if op <= 0:
        return img
    ry = max(1.5, r * op)
    d = np.sqrt(((xx - c[0]) / r) ** 2 + ((yy - c[1]) / ry) ** 2)
    m = np.clip((1 - d) * r / 1.5, 0, 1)[..., None]
    sh = np.clip(1.35 - np.sqrt(((xx - c[0] + 6) / r) ** 2 + ((yy - c[1] - 8) / ry) ** 2), 0, .35)[..., None] / .35
    img = img * (1 - .6 * sh)
    body = np.float32([9, 8, 9]) + 26 * np.clip(d - .55, 0, 1)[..., None]
    img = img * (1 - m) + body * m
    if op > .6:
        h = np.exp(-(((xx - c[0] - r * .34) / (r * .20)) ** 2 + ((yy - c[1] + r * .38) / (r * .16)) ** 2))
        h2 = np.exp(-(((xx - c[0] + r * .3) / (r * .16)) ** 2 + ((yy - c[1] - r * .42) / (r * .10)) ** 2)) * .25
        img = img + (h + h2)[..., None] * np.float32([205, 228, 245])
    return img


def frame(state, eyes, light, cam, imprint=0):
    """state[i] = (보임, 들린 높이, 기울기, 꿰맨 비율)"""
    img = BG.copy()
    if imprint:
        for i, p in enumerate(PC):
            k = (1 - state[i][0]) * imprint
            if k > 0:
                img = img * (1 + .30 * k * gaussian_filter(p['a'], 3)[..., None])
    for i, p in enumerate(PC):
        vis, lift, tilt, sew = state[i]
        M = cv2.getRotationMatrix2D(p['c'], tilt, 1 + lift * .10)
        M[0, 2] += lift * 26; M[1, 2] -= lift * 34
        if vis > 0:
            a, hg, t = p['a'], p['hgt'], p['t']
            if lift or tilt:
                a, hg, t = (cv2.warpAffine(q.astype(np.float32), M, (W, H)) for q in (a, hg, t))
            for dx, dy, s, k in ((-5, 6, 4, .55), (-12 - 40 * lift, 15 + 52 * lift, 13 + 20 * lift, .6)):
                s_ = cv2.GaussianBlur(cv2.warpAffine(a, np.float32([[1, 0, dx], [0, 1, dy]]), (W, H)), (0, 0), s)
                img = img * (1 - k * s_)[..., None]
            lum = .16 + 1.02 * shade(hg, 1.25)
            col = p['base'] * (np.clip(t, .3, 1.9) * lum)[..., None]
            fz = np.clip(a + (fib * 2.2) * ((a > .02) & (a < .98)), 0, 1)[..., None]
            img = img * (1 - fz) + col * fz
        n = int(round(sew * len(p['st'])))
        if n:
            img = draw_st(img, p['st'][:n], M=M if (lift or tilt) else None, dark=1 if vis else 1.5)
    img = img * (.20 + 1.0 * lamp)[..., None] * np.float32([.94, .99, 1.05]) * light
    for k, c in enumerate(EYES):
        img = eye(img, c, 41, eyes[k])
    z, cx, cy = cam
    s = z
    img = cv2.warpAffine(img.astype(np.float32), np.float32([[s, 0, W / 2 - s * cx], [0, s, H / 2 - s * cy]]), (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    v = 1 - .35 * np.clip(((xx - W / 2) / (W * .68)) ** 2 + ((yy - H / 2) / (H * .75)) ** 2, 0, 1)
    return img * v[..., None] * 1.28


def ease(t):
    t = min(1, max(0, t)); return t * t * (3 - 2 * t)


# 순서와 시각 (제목 5.4초)
LAND = [.30, .52, .86, 1.08, 1.42, 1.62, 1.82]
SEW = .95
EYE_T = [3.45, 3.62]


def title(t):
    st = []
    for i, l in enumerate(LAND):
        d = t - l
        tl = (-9, 7, 10, -7, 6, -8, 9)[i]
        if d < 0:
            st.append((0, 0, 0, 0))
        elif d < .07:
            st.append((1, 1.0, tl, 0))
        elif d < .15:
            st.append((1, .28, tl * .3, 0))
        else:
            st.append((1, 0, 0, ease((d - .22) / SEW)))
    e = [0 if t < x else (.45 if t < x + .085 else 1) for x in EYE_T]
    if 4.28 <= t < 4.37:
        e = [.12, .12]   # 한 번 깜빡인다
    L = ease(t / .35) * (1 - ease((t - 4.55) / .55))
    k = ease((t - 2.6) / 2.6)
    return frame(st, e, L, (.965 + .035 * ease(t / 5) + .055 * k, W / 2 + 70 * k, H / 2 + 30 * k))


REM = [.95, 1.2, 1.45, 1.68, 1.90, 2.10, 2.42]


def title_end(t):
    st = []
    order = [0, 2, 4, 1, 3, 5, 6]
    for i in range(7):
        r = REM[order.index(i)]
        d = t - r
        tl = (9, -8, -10, 8, -7, 9, -6)[i]
        if d < 0:
            st.append((1, 0, 0, 1))
        elif d < .085:
            st.append((1, .5, tl * .6, 0))
        else:
            st.append((0, 0, 0, 1))
    e = [1, 1]
    if 3.55 <= t < 3.64:
        e = [.12, .12]
    if t > 4.25:
        e = [0, 0]
    L = ease(t / .6) * (1 - .55 * ease((t - 2.5) / .8)) * (1 - ease((t - 3.75) / .5))
    k = ease((t - 2.2) / 2.2)
    return frame(st, e, L, (1.03 + .12 * k, W / 2 + 120 * k, H / 2 + 60 * k), imprint=1)


if '시험' in sys.argv:
    S = sys.argv[-1]
    fs = [title(t) for t in (.6, 1.3, 2.3, 4.0)] + [title_end(t) for t in (1.7, 3.2)]
    g = np.concatenate([np.concatenate(fs[k:k + 2], 1) for k in (0, 2, 4)], 0)
    cv2.imencode('.jpg', cv2.resize(np.clip(g, 0, 255).astype(np.uint8), (1920, 1620), interpolation=cv2.INTER_AREA))[1].tofile(S)
else:
    for name, fn, D in (('title', title, 5.4), ('title_end', title_end, 5.0)):
        p = subprocess.Popen(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', '24', '-i', '-', '-vf', 'scale=out_color_matrix=bt709:out_range=tv,noise=c0s=4:c0f=t+u',
                              '-c:v', 'libx264', '-crf', '11', '-pix_fmt', 'yuv420p', '-g', '12', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', OUT + name + '.mp4'], stdin=subprocess.PIPE)
        f = None
        for n in range(round(D * 24)):
            if n % 2 == 0:
                f = np.clip(fn(n / 24) * (1 + .012 * math.sin(n * 1.15) * math.cos(n * .55)), 0, 255).astype(np.uint8).tobytes()
            p.stdin.write(f)
        p.stdin.close(); assert p.wait() == 0
        print(name)
