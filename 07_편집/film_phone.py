"""휴대폰 장면(01~03)과 제목 화면을 새로 그린다.
uv run --no-project --with opencv-python-headless --with pillow --with numpy python -X utf8 07_편집/film_phone.py"""
import os, subprocess, math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
OUT = '07_편집/film/소스/'
os.makedirs(OUT, exist_ok=True)
W, H = 1920, 1080


def rd(p):
    return cv2.imdecode(np.fromfile(p, np.uint8), 1)


def ease(t):
    t = min(1, max(0, t))
    return t * t * t * (t * (6 * t - 15) + 10)


def out3(t):
    t = min(1, max(0, t))
    return 1 - (1 - t) ** 3


class Enc:
    def __init__(s, name):
        s.p = subprocess.Popen(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', '24', '-i', '-',
                                '-vf', 'scale=out_color_matrix=bt709:out_range=tv', '-c:v', 'libx264', '-crf', '11', '-pix_fmt', 'yuv420p', '-g', '12', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', OUT + name + '.mp4'], stdin=subprocess.PIPE)

    def w(s, f):
        s.p.stdin.write(np.clip(f, 0, 255).astype(np.uint8).tobytes())

    def close(s):
        s.p.stdin.close()
        assert s.p.wait() == 0


B = '05_본제작/'
post = rd(B + 'CUT01/CUT01_게시물_FINAL.png')
rev = [rd(B + f'CUT02/CUT02_후기{i}_FINAL.png') for i in (1, 2, 3)]
com = rd(B + 'CUT03/CUT03_댓글_FINAL.png')
UW, UH = 1000, 1778


def ui(im):
    return cv2.resize(im, (UW, UH), interpolation=cv2.INTER_AREA if im.shape[1] > UW else cv2.INTER_CUBIC)


post, com = ui(post), ui(com)
rev = [ui(r) for r in rev]

# ---- 1) 어깨 너머: 초록 화면에 화면 내용을 붙인다
ots = rd(B + 'CUT01/CUT01_휴대폰_FINAL.png').astype(np.float32)
g = ots[..., 1] - np.maximum(ots[..., 0], ots[..., 2])
mask = np.clip((g - 25) / 90, 0, 1)
ys, xs = np.where(mask > .9)
pts = np.stack([xs, ys], 1).astype(np.float32)
# 모서리가 둥글어 변에 직선을 맞춰 네 꼭짓점을 구한다
yy0, yy1, xx0, xx1 = ys.min(), ys.max(), xs.min(), xs.max()


def fit(samples, swap):
    a = np.array(samples, float)
    u, v = (a[:, 1], a[:, 0]) if swap else (a[:, 0], a[:, 1])
    return np.polyfit(u, v, 1)


L, R_, T_, Bm = [], [], [], []
for y in range(int(yy0 + .2 * (yy1 - yy0)), int(yy0 + .8 * (yy1 - yy0)), 8):
    r = np.where(mask[y] > .5)[0]
    L.append((r.min(), y)); R_.append((r.max(), y))
for x in list(range(int(xx0 + .18 * (xx1 - xx0)), int(xx0 + .82 * (xx1 - xx0)), 6)):
    c = np.where(mask[:, x] > .5)[0]
    Bm.append((x, c.max()))
for x in list(range(int(xx0 + .12 * (xx1 - xx0)), int(xx0 + .2 * (xx1 - xx0)), 3)) + list(range(int(xx0 + .82 * (xx1 - xx0)), int(xx0 + .88 * (xx1 - xx0)), 3)):
    c = np.where(mask[:, x] > .5)[0]
    T_.append((x, c.min()))
l, r, b, t = fit(L, True), fit(R_, True), fit(Bm, False), fit(T_, False)


def inter(v, h):  # x=v0*y+v1, y=h0*x+h1
    x = (v[0] * h[1] + v[1]) / (1 - v[0] * h[0])
    return [x, h[0] * x + h[1]]


quad = np.float32([inter(l, t), inter(r, t), inter(r, b), inter(l, b)])
print('quad', quad.tolist())
HM = cv2.getPerspectiveTransform(np.float32([[0, 0], [UW, 0], [UW, UH], [0, UH]]), quad)
m3 = cv2.GaussianBlur(mask, (0, 0), 1.0)[..., None]
spill = ots.copy()
spill[..., 1] = np.minimum(spill[..., 1], np.maximum(spill[..., 0], spill[..., 2]) * 1.02 + 2)


def ots_frame(u, on, t, dur):
    wr = cv2.warpPerspective(u, HM, (ots.shape[1], ots.shape[0]), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    scr = wr * (.96 * on) + 7 * (1 - on)
    f = spill * (1 - m3) + scr * m3
    # 화면 빛이 손과 주변에 번진다
    glow = cv2.GaussianBlur(cv2.resize(scr * m3, (320, 180)), (0, 0), 16)
    glow = cv2.resize(glow, (ots.shape[1], ots.shape[0]))
    f = f + glow * .22 * on
    e = ease(t / dur)
    z = 1.16 + .10 * e
    cw, ch = ots.shape[1] / z, ots.shape[0] / z
    cx = .60 * ots.shape[1] + 24 * e + 2.4 * math.sin(t * 1.3) + 1.2 * math.sin(t * 2.9 + 1)
    cy = .50 * ots.shape[0] + 1.8 * math.sin(t * 1.7 + .6) + 1.0 * math.sin(t * 3.3)
    cx = min(max(cx, cw / 2), ots.shape[1] - cw / 2)
    cy = min(max(cy, ch / 2), ots.shape[0] - ch / 2)
    s = W / cw
    M = np.float32([[s, 0, W / 2 - s * cx], [0, s, H / 2 - s * cy]])
    return cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_CUBIC)


dark = np.zeros_like(post) + 6
# 잠금 화면 알림
lock = np.zeros_like(post); lock[:] = (26, 20, 18)
pl = Image.fromarray(lock[..., ::-1]); d = ImageDraw.Draw(pl)
F = lambda n, s: ImageFont.truetype('C:/Windows/Fonts/' + n, s)
d.text((UW / 2, 420), '2:47', font=F('malgunsl.ttf', 210), fill=(235, 232, 228), anchor='mm')
d.rounded_rectangle((60, 720, UW - 60, 960), 46, fill=(58, 52, 50))
d.ellipse((100, 772, 236, 908), fill=(196, 150, 96))
d.text((168, 840), '실', font=F('malgunbd.ttf', 72), fill=(40, 28, 20), anchor='mm')
d.text((280, 770), '#걱정인형', font=F('malgunbd.ttf', 50), fill=(245, 240, 235))
d.text((280, 850), '걱정을 대신해주는 인형 – 지금 인기 게시물', font=F('malgun.ttf', 33), fill=(205, 198, 192))
lock = np.array(pl)[..., ::-1].copy()

en = Enc('phone_ots')
D = 4.6
for n in range(int(D * 24)):
    t = n / 24
    on = ease((t - .25) / .35)
    u = lock
    if t > 1.75:
        k = ease((t - 1.75) / .45)
        u = (lock * (1 - k) + post * k).astype(np.uint8)
    en.w(ots_frame(u, on, t, D))
en.close()

# ---- 2) 화면 접사: 화면이 프레임을 채우고 게시물이 넘어간다
bgb = cv2.resize(cv2.GaussianBlur(cv2.resize(spill, (480, 270)), (0, 0), 9), (W, H)) * .55


def ecu(content_h, get, name, D, w0, w1, y0, y1, tilt=1.3):
    """get(t) -> 화면 그림(UW x content_h). 폭 w(px)로 놓고 y 위치를 부드럽게 옮긴다."""
    en = Enc(name)
    yv, xv = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = 1 - .42 * np.clip((((xv - W / 2) / (W * .62)) ** 2 + ((yv - H / 2) / (H * .75)) ** 2), 0, 1) ** 1.4
    for n in range(int(round(D * 24))):
        t = n / 24
        img, cy = get(t)
        e = ease(t / D)
        w = w0 + (w1 - w0) * e
        s = w / UW
        ang = math.radians(tilt - .5 * e)
        cxs = W * .5 + 2.2 * math.sin(t * 1.4)
        cys = H * .5 + 2.0 * math.sin(t * 1.9 + .8)
        # 약한 원근
        hh = H / s / 2 + 60
        src = np.float32([[0, cy - hh], [UW, cy - hh], [UW, cy + hh], [0, cy + hh]])
        dst = []
        for (x, y), k in zip([(-w / 2, -hh * s), (w / 2, -hh * s), (w / 2, hh * s), (-w / 2, hh * s)], (.965, .985, 1.035, 1.015)):
            X, Y = x * k, y * k
            dst.append([cxs + X * math.cos(ang) - Y * math.sin(ang), cys + X * math.sin(ang) + Y * math.cos(ang)])
        M = cv2.getPerspectiveTransform(src, np.float32(dst))
        pad = 34
        canvas = cv2.copyMakeBorder(img, 0, 0, pad, pad, cv2.BORDER_CONSTANT, value=(10, 10, 12))
        M2 = M @ np.float32([[1, 0, -pad], [0, 1, 0], [0, 0, 1]])
        warp = cv2.warpPerspective(canvas, M2, (W, H), flags=cv2.INTER_AREA).astype(np.float32)
        al = cv2.warpPerspective(np.full(canvas.shape[:2], 255, np.uint8), M2, (W, H), flags=cv2.INTER_AREA)[..., None] / 255.
        f = bgb * (1 - al) + warp * al
        bl = cv2.resize(cv2.GaussianBlur(cv2.resize(f, (240, 135)), (0, 0), 7), (W, H))
        f = f + bl * .16
        soft = cv2.GaussianBlur(f, (0, 0), 5)
        k = np.clip((np.abs(yv - H / 2) / (H / 2) - .62) / .38, 0, 1)[..., None] ** 1.3
        f = f * (1 - k) + soft * k
        en.w(f * vig[..., None] + 2)
    en.close()


# 후기 세 개를 위로 넘긴다
seq = [post] + rev
strip = np.concatenate(seq, 0)
SW = [.55, 2.15, 3.75]  # 넘기는 시점
CENT = [UH * .52, UH * .55, UH * .50, UH * .46]


def feed(t):
    y = CENT[0]
    for i, s in enumerate(SW):
        a, b_ = i * UH + CENT[i], (i + 1) * UH + CENT[i + 1]
        if t >= s:
            y = a + (b_ - a) * out3((t - s) / .42)
    # 넘길 때 세로 흐림
    lo = int(max(0, y - 900)); hi = int(min(strip.shape[0], y + 900))
    v = any(0 < t - s < .2 for s in SW)
    im = strip[lo:hi]
    if v:
        im = cv2.blur(im, (1, 61))
    return im, y - lo


ecu(None, feed, 'phone_feed', 5.5, 860, 900, 0, 0)

# 댓글: 위에서 아래로 훑고 마지막 댓글에 멈춘다
LAST = UH * (528 / 689)


def comments(t):
    a, b_ = UH * .30, LAST - 60
    k = ease((t - .9) / 2.6)
    im = com
    if t < .35:  # 아래에서 올라오는 댓글창
        off = int((1 - out3(t / .35)) * 700)
        im = np.concatenate([rev[2][:off], com[:UH - off]], 0) if off > 0 else com
    return im, a + (b_ - a) * k


ecu(None, comments, 'phone_comments', 6.2, 1060, 1240, 0, 0, tilt=.9)
# 제목은 film_title.py에서 만든다
print('ok')
