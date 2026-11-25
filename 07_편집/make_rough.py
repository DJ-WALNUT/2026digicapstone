"""가편집 생성: python -X utf8 07_편집/make_rough.py
CUTS(컷 순서·사용 구간·확대)와 대사 시점을 고치고 다시 실행하면 mp4, XML, srt가 새로 나온다.
시점은 모두 '원본 컷 영상의 0초'부터 잰 초. 초당 24프레임."""
import os, re, json, hashlib, subprocess
from urllib.parse import quote
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
OUT = '07_편집/'
VER = 'v1'
B, FPS, W, H = '05_본제작/', 24, 1920, 1080
for d in ('클립', '대사', '_tmp'):
    os.makedirs(OUT + d, exist_ok=True)


def V(c, d=None):
    return f'{B}CUT{d or c}/CUT{c}_영상_FINAL.mp4'


def I(d, n):
    return f'{B}CUT{d}/{n}.png'


# (이름, 파일, 시작, 끝, 확대(시작배율, 끝배율, x, y) 또는 None, [대사: (파일, 음성시작, 음성끝, 컷 안 시점, 자막)])
# 파일 None = 검은 화면
P = (.708, .50)
CUTS = [
    ('검정_시작', None, 0, 1.2, None, []),
    ('01', I('01', 'CUT01_합성_게시물'), 0, 3.0, (1.0, 1.3, .708, .47), []),
    ('02_1', I('02', 'CUT02_합성_후기1'), 0, 1.8, (1.5, 1.55, *P),
     [('CUT02_SNS_걱정은인형이', 0, None, .2, '자기 전에, 할 일을 인형 옆에 두세요.\n걱정은… 인형이 대신해 줄 거예요.')]),
    ('02_2', I('02', 'CUT02_합성_후기2'), 0, 1.4, (1.5, 1.55, *P), []),
    ('02_3', I('02', 'CUT02_합성_후기3'), 0, 1.4, (1.5, 1.55, *P), []),
    ('03', I('03', 'CUT03_합성_댓글'), 0, 4.2, (1.7, 2.5, .708, .56), []),
    ('04', V('04'), 0, 5.0, None, [('CUT04_서연_나도누가', 0, None, 1.0, '…나도 누가 대신 해줬으면 좋겠다.')]),
    ('05', V('05'), 0, 2.3, None, []),
    ('06', V('06'), 0, 4.4, None, [('CUT06_서연_뭐야', 0, None, 3.35, '…뭐야?')]),
    ('07', V('07'), 0, 2.5, None, []),
    ('08a', V('08a'), 0, 4.8, None, 'CUT08'),
    ('08b', V('08b'), .5, 2.8, None, []),
    ('09', V('09'), 0, 4.5, None, []),
    ('10', V('10'), 0, 4.2, None, []),
    ('11', V('11'), .5, 5.0, None, [('CUT11_서연_소원이없겠다', 0, None, 1.15, '진짜로 해주면… 소원이 없겠다.')]),
    ('12', V('12'), 0, 4.4, None, []),
    ('13', V('13'), 0, 3.5, None, []),
    ('14', V('14'), 0, 4.8, None, []),
    ('15a', V('15a'), 1.0, 5.0, None, [('CUT15_서연_진짜야고마워', 0, 1.6, 1.75, '너, 진짜야?'),
                                      ('CUT15_서연_진짜야고마워', 1.6, None, 3.75, '…고마워.')]),
    ('15b', V('15b'), 0, 2.6, None, []),
    ('16', V('16'), 0, 4.4, None, [('CUT16_서연_부탁해', 0, None, .3, '오늘은 이거랑… 이것도. 부탁해.')]),
    ('17', V('17'), 0, 4.0, None, []),
    ('18a', I('18a', 'CUT18a_첫장면_FINAL'), 0, 1.1, (1.0, 1.04, .5, .5), []),
    ('18b', I('18b', 'CUT18b_첫장면_FINAL'), 0, .8, (1.0, 1.03, .5, .5), []),
    ('18c', I('18c', 'CUT18c_첫장면_FINAL'), 0, .8, (1.0, 1.03, .5, .5), []),
    ('19', V('19'), 2.2, 5.0, None, [('CUT19_서연_알아서해줘', 0, None, 2.4, '알아서 해 줘.')]),
    ('20', V('20'), .2, 1.8, (1.6, 1.6, .38, .42), []),
    ('21', V('21'), .3, 3.6, None, []),
    ('22_전', I('22', 'CUT22_전_FINAL'), 0, 1.3, None, []),
    ('22_후', I('22', 'CUT22_후_FINAL'), 0, 1.8, None, []),
    ('23', V('23'), 0, 3.3, None, [('CUT23_서연_다녀올게', 0, None, 1.0, '다녀올게.')]),
    ('24', V('24'), 2.2, 5.0, None, [('CUT24_서연_목이왜이러지', 0, None, 2.6, '아… 목이 왜 이러지.')]),
    ('24b', I('24', 'CUT24b_첫장면_FINAL'), 0, 1.4, (1.0, 1.05, .48, .7), []),
    ('25', V('25'), 0, 2.2, None, []),
    ('26', V('26'), 0, 5.0, None, [('CUT26_서연_피곤해서그런가', 0, None, 3.3, '…피곤해서 그런가.')]),
    ('27', V('27'), 0, 4.0, (1.0, 1.45, .40, .53), []),
    ('28', V('28'), 0, 5.0, (1.45, 1.0, .72, .66), []),
    ('29', V('29'), 0, 5.0, None, []),
    ('검정_대체', None, 0, 1.6, None, []),
    ('30', V('30'), 0, 4.0, None, []),
    ('31', V('31'), 0, 2.7, None, [('CUT31_대체품_다녀올게', 0, None, .4, '다녀올게.')]),
    ('32', V('32'), 2.0, 4.0, None, []),
    ('33', V('33'), 2.0, 5.0, None, [('CUT33_민준_서연이왔다', 0, .4, 3.15, '어,'),
                                    ('CUT33_민준_서연이왔다', .4, None, 4.0, '서연이 왔다!')]),
    ('34', V('34'), 0, 3.4, None, [('CUT34_수빈_여기앉아', 0, .68, .40, '서연아,'),
                                  ('CUT34_수빈_여기앉아', .68, None, 1.17, '여기 앉아.')]),
    ('34b', I('34', 'CUT34b_첫장면_FINAL'), 0, 1.0, (1.0, 1.03, .5, .7), []),
    ('35', V('35'), .3, 4.5, None, [('CUT35_잡담_다돼있던데', 0, None, 1.6, '자고 일어났더니 다 돼 있던데.')]),
    ('35b', I('35', 'CUT35b_첫장면_FINAL'), 0, 1.3, None, []),
    ('36a', V('36a', '36'), .5, 4.3, None, [('CUT36a_수빈_과제잘하더라', 0, None, 1.03, '너도 요즘 과제 진짜 잘하더라.')]),
    ('36b', V('36b', '36'), 0, 3.8, None, [('CUT36b_수빈_하나구했구나', 0, None, .25, '…너도 하나 구했구나?')]),
    ('37A', V('37A'), 0, 4.05, None, []),
    ('38A', I('38A', 'CUT38A_첫장면_FINAL'), 0, 4.0, None, []),
    ('39', I('39', 'CUT39_첫장면_FINAL'), 0, 3.5, (1.0, 1.06, .5, .45), []),
]
# 08a: 화면의 입은 1.4초와 2.8초에 열린다. 음성을 쉼에서 나눠 두 곳에 맞춘다
CUT08 = [('CUT08_서연_너나닮았다', 0, 1.0, 1.4, '너…'), ('CUT08_서연_너나닮았다', 1.0, None, 2.8, '나 닮았다.')]
CFG = os.path.join(OUT, 'cut08.json')
if os.path.exists(CFG):
    CUT08 = [tuple(x) for x in json.load(open(CFG, encoding='utf8'))]
# 40: 거울 3초 → 인형 2초 → 점점 빠른 교차 3초(72프레임) → 거울 1.6초 → 암전
MIR, DOL = I('40', 'CUT40_거울속대체품_맞춤'), I('40', 'CUT40_인형서연_맞춤')
seq = [12, 10, 9, 8, 7, 6, 5, 4, 3, 3, 2, 2, 1]
assert sum(seq) == 72 and len(seq) % 2 == 1
CUTS += [('40_거울', MIR, 0, 3.0, None, []), ('40_인형', DOL, 0, 2.0, None, [])]
CUTS += [('40_거울' if i % 2 == 0 else '40_인형', MIR if i % 2 == 0 else DOL, 0, n / FPS, None, []) for i, n in enumerate(seq[:-1])]
CUTS += [('40_거울', MIR, 0, seq[-1] / FPS + 1.6, None, []), ('검정_끝', None, 0, 2.5, None, [])]
GAIN = {'CUT35_잡담_다돼있던데': -7, 'CUT36b_수빈_하나구했구나': -1}


def run(*a):
    r = subprocess.run(a, capture_output=True, text=True, encoding='utf8')
    if r.returncode:
        raise SystemExit(' '.join(a) + '\n' + r.stderr)
    return r.stdout + r.stderr


def ff(*a):
    return run('ffmpeg', '-nostdin', '-v', 'error', '-y', *a)


ENC = ['-an', '-c:v', 'libx264', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-video_track_timescale', '24000']


def nframes(p):
    return int(run('ffprobe', '-v', 'error', '-select_streams', 'v', '-count_packets', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', p).strip().strip(','))


clips = {}


def clip(name, src, a, b, z):
    """원본 전체를 1080p 24fps로 바꾼 편집용 클립. 확대는 사용 구간 동안 일어난다."""
    key = hashlib.md5(json.dumps([src, os.path.getmtime(src), a if z else 0, b if z else 0, z, 3]).encode()).hexdigest()[:8]
    img = src.endswith('.png')
    if img and not z:
        key = hashlib.md5(json.dumps([src, os.path.getmtime(src), 3]).encode()).hexdigest()[:8]
    p = f'{OUT}클립/CUT{name}.mp4'
    tag = p + '.key'
    if not (os.path.exists(p) and os.path.exists(tag) and open(tag).read() == key):
        n = 240 if img else nframes(src)
        fa, fb = round(a * FPS), round(b * FPS)
        base = 'scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080' if img else 'crop=1920:1080'
        if n == 240 and not img:
            pre, n = 'fps=24', 96
        else:
            pre = f'setpts=N/{FPS}/TB'
        vf = f'{pre},{base},setsar=1'
        if z:
            z0, z1, x, y = z
            up = ('scale=3840:2160:force_original_aspect_ratio=increase:flags=lanczos,crop=3840:2160' if img
                  else 'crop=1920:1080,scale=3840:2160:flags=lanczos')
            e = f'({z0}+({z1}-{z0})*clip((on-{fa})/{max(1, fb-fa-1)},0,1))'
            vf = f"{pre},{up},setsar=1,zoompan=z='{e}':x='clip(iw*{x}-iw/zoom/2,0,iw-iw/zoom)':y='clip(ih*{y}-ih/zoom/2,0,ih-ih/zoom)':d=1:s=1920x1080:fps=24"
        inp = ['-loop', '1', '-framerate', '24', '-i', src] if img else ['-i', src]
        ff(*inp, '-vf', vf, '-r', '24', '-frames:v', str(n), *ENC, '-crf', '13', '-g', '12', p)
        open(tag, 'w').write(key)
    clips[name] = (p, nframes(p))


voices = {}


def voice(n):
    if n in voices:
        return voices[n]
    s = f'03_대본/tts_최종/{n}_FINAL.wav'
    o = f'{OUT}대사/{n}.wav'
    t = run('ffmpeg', '-nostdin', '-hide_banner', '-i', s, '-af', 'apad=whole_dur=3,ebur128', '-f', 'null', '-')
    lufs = float(re.findall(r'I:\s+(-[\d.]+) LUFS', t)[-1])
    g = -20 - lufs + GAIN.get(n, 0)
    ff('-i', s, '-af', f'volume={g:.2f}dB,alimiter=limit=0.8:level=false,aresample=48000', '-ac', '2', '-c:a', 'pcm_s16le', o)
    d = float(run('ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', o).strip())
    voices[n] = (o, d)
    return voices[n]


vt, at, subs, pos = [], [], [], 0
for name, src, a, b, z, dl in CUTS:
    n = round((b - a) * FPS)
    if src:
        assert os.path.exists(src), src
        clip(name, src, a, b, z)
        i = round(a * FPS)
        p, total = clips[name]
        assert i + n <= total, (name, i, n, total)
        vt.append((name, pos, n, p, i, total))
    else:
        vt.append((name, pos, n, None, 0, 0))
    for (vn, s, e, t, txt) in (CUT08 if dl == 'CUT08' else dl):
        vp, vd = voice(vn)
        e = vd if e is None else e
        st = pos + round((t - a) * FPS)
        si, sn = round(s * FPS), round((e - s) * FPS)
        sn = min(sn, int(vd * FPS) - si) or 1
        at.append((vn, st, sn, vp, si, vd))
        subs.append([st, st + sn, txt])
    pos += n
TOTAL = pos

# ---- mp4
seglist = []
for k, (name, st, n, p, i, total) in enumerate(vt):
    o = f'{OUT}_tmp/s{k:03d}.mp4'
    if p:
        ff('-i', p, '-vf', f'trim=start_frame={i}:end_frame={i+n},setpts=PTS-STARTPTS', '-frames:v', str(n), *ENC, '-bf', '0', '-crf', '16', o)
    else:
        ff('-f', 'lavfi', '-i', f'color=black:s={W}x{H}:r=24', '-frames:v', str(n), *ENC, '-bf', '0', '-crf', '16', o)
    assert nframes(o) == n, (name, n, nframes(o))
    seglist.append(f"file 's{k:03d}.mp4'")
open(OUT + '_tmp/list.txt', 'w', encoding='utf8').write('\n'.join(seglist))
ff('-f', 'concat', '-safe', '0', '-i', OUT + '_tmp/list.txt', '-c', 'copy', '-bsf:v', 'setts=ts=N*1000:duration=1000', '-video_track_timescale', '24000', OUT + '_tmp/video.mp4')
assert nframes(OUT + '_tmp/video.mp4') == TOTAL
inp, fc = [], ''
ff('-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', str(TOTAL / FPS), OUT + '_tmp/sil.wav')
inp += ['-i', OUT + '_tmp/sil.wav']
for k, (vn, st, sn, p, si, vd) in enumerate(at):
    inp += ['-i', p]
    fc += f'[{k+2}:a]atrim={si/FPS}:{(si+sn)/FPS},asetpts=PTS-STARTPTS,afade=t=in:d=0.008,areverse,afade=t=in:d=0.02,areverse,adelay={round(st*1000/FPS)}:all=1[a{k}];'
fc += '[1:a]' + ''.join(f'[a{k}]' for k in range(len(at))) + f'amix=inputs={len(at)+1}:normalize=0:duration=first[o]'
M = f'{OUT}대체품_가편집_{VER}.mp4'
ff('-i', OUT + '_tmp/video.mp4', *inp, '-filter_complex', fc, '-map', '0:v', '-map', '[o]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', M)

# ---- srt (나눈 대사는 따로 표시)


def tc(f):
    ms = round(f * 1000 / FPS)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'


open(f'{OUT}대체품_가편집_{VER}.srt', 'w', encoding='utf-8-sig').write('\n'.join(f'{i+1}\n{tc(a)} --> {tc(b)}\n{t}\n' for i, (a, b, t) in enumerate(subs)))

# ---- 확인용: 컷 이름, 시간, 자막을 넣은 mp4
ass = ['[Script Info]', 'PlayResX: 1920', 'PlayResY: 1080', '[V4+ Styles]',
       'Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,BackColour,Bold,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV',
       'Style: S,Malgun Gothic,50,&H00FFFFFF,&H00000000,&H00000000,1,1,3,0,2,40,40,60',
       'Style: N,Malgun Gothic,34,&H0000FFFF,&H00000000,&H00000000,1,1,2,0,7,30,30,24', '[Events]', 'Format: Start,End,Style,Text']


def at_(f):
    c = round(f * 100 / FPS)
    return f'{c//360000}:{c//6000%60:02d}:{c//100%60:02d}.{c%100:02d}'


for name, st, n, *_ in vt:
    ass.append(f'Dialogue: {at_(st)},{at_(st+n)},N,{name}  {st/FPS//60:.0f}:{st/FPS%60:04.1f}')
for a, b, t in subs:
    ass.append(f'Dialogue: {at_(a)},{at_(b)},S,' + t.replace('\n', '\\N'))
open(OUT + '_tmp/o.ass', 'w', encoding='utf8').write('\n'.join(ass))
ff('-i', M, '-vf', f'ass={OUT}_tmp/o.ass,scale=1280:720', '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'copy', f'{OUT}대체품_가편집_{VER}_컷번호.mp4')
ff('-i', M, '-vf', 'fps=12', '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', '-c:a', 'copy', f'{OUT}대체품_가편집_{VER}_12fps.mp4')

# ---- Premiere XML (FCP7)


def url(p):
    return 'file://localhost/' + quote(os.path.abspath(p).replace('\\', '/'), safe='/').replace('D%3A', 'D%3a')


RATE = '<rate><timebase>24</timebase><ntsc>FALSE</ntsc></rate>'
seen = set()


def fl(p, total, kind):
    fid = 'f' + hashlib.md5(p.encode()).hexdigest()[:10]
    if fid in seen:
        return f'<file id="{fid}"/>'
    seen.add(fid)
    media = (f'<video><samplecharacteristics>{RATE}<width>{W}</width><height>{H}</height><pixelaspectratio>square</pixelaspectratio></samplecharacteristics></video>' if kind == 'v'
             else '<audio><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics><channelcount>2</channelcount></audio>')
    return f'<file id="{fid}"><name>{escape(os.path.basename(p))}</name><pathurl>{escape(url(p))}</pathurl>{RATE}<duration>{total}</duration><media>{media}</media></file>'


def item(k, nm, st, n, p, i, total, kind, ch=1):
    src = '' if kind == 'v' else f'<sourcetrack><mediatype>audio</mediatype><trackindex>{ch}</trackindex></sourcetrack>'
    return (f'<clipitem id="{kind}{ch}_{k}"><name>{escape(nm)}</name><enabled>TRUE</enabled><duration>{total}</duration>{RATE}'
            f'<start>{st}</start><end>{st+n}</end><in>{i}</in><out>{i+n}</out>{fl(p, total, kind)}{src}</clipitem>')


vx = ''.join(item(k, 'CUT' + nm, st, n, p, i, t, 'v') for k, (nm, st, n, p, i, t) in enumerate(vt) if p)
ax = ['', '']
for ch in (1, 2):
    ax[ch - 1] = ''.join(item(k, nm, st, n, p, i, max(i + n, int(d * FPS)), 'a', ch) for k, (nm, st, n, p, i, d) in enumerate(at))
marks = ''.join(f'<marker><name>CUT{escape(nm)}</name><comment></comment><in>{st}</in><out>-1</out></marker>' for nm, st, n, p, *_ in vt if not nm.startswith('40_') or st == 0)
xml = (f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4"><sequence id="seq1"><name>대체품_가편집_{VER}</name><duration>{TOTAL}</duration>{RATE}'
       f'<timecode>{RATE}<string>00:00:00:00</string><frame>0</frame><displayformat>NDF</displayformat></timecode>{marks}<media><video><format><samplecharacteristics>{RATE}<width>{W}</width><height>{H}</height>'
       f'<anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio><fielddominance>none</fielddominance></samplecharacteristics></format><track>{vx}</track></video>'
       f'<audio><numOutputChannels>2</numOutputChannels><format><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics></format>'
       f'<track>{ax[0]}<outputchannelindex>1</outputchannelindex></track><track>{ax[1]}<outputchannelindex>2</outputchannelindex></track></audio></media></sequence></xmeml>')
open(f'{OUT}대체품_가편집_{VER}.xml', 'w', encoding='utf8').write(xml)

D = run('ffprobe', '-v', 'error', '-show_entries', 'stream=duration', '-of', 'csv=p=0', M).split()
print('mp4 길이(영상, 소리):', D)
assert all(abs(float(x.strip(',')) - TOTAL / FPS) < .06 for x in D), D
print(f'길이 {TOTAL/FPS:.2f}초, 컷 {len(vt)}, 대사 조각 {len(at)}')
for nm, st, n, *_ in vt:
    print(f'{nm}\t{st/FPS:.2f}\t{n/FPS:.2f}')
# 대사 겹침 확인
s = sorted(at, key=lambda x: x[1])
for x, y in zip(s, s[1:]):
    if x[1] + x[2] > y[1]:
        print('겹침', x[0], y[0])
