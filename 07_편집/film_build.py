"""영화 편집 v2 만들기 (화면 → 소리 → 섞기 → Premiere XML)
uv run --no-project --with numpy --with scipy --with soundfile python -X utf8 07_편집/film_build.py [소리만]"""
import sys, os, json, hashlib, subprocess, re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
from xml.sax.saxutils import escape
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from film_spec import *
os.chdir(ROOT)
import numpy as np, soundfile as sf
import film_sound as snd
F = '07_편집/film/'
VER = 'v3'
W, H = 1920, 1080
for d in ('클립', f'소리_{VER}', '_tmp'):
    os.makedirs(F + d, exist_ok=True)
SOUND_ONLY = '소리만' in sys.argv


def run(*a):
    r = subprocess.run(a, capture_output=True, text=True, encoding='utf8')
    if r.returncode:
        raise SystemExit(' '.join(map(str, a))[:1500] + '\n' + r.stderr[-1500:])
    return r.stdout + r.stderr


def ff(*a):
    return run('ffmpeg', '-nostdin', '-v', 'error', '-y', '-filter_threads', '2', *a)


def nfr(p):
    return int(run('ffprobe', '-v', 'error', '-select_streams', 'v', '-count_packets', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', p).strip().strip(','))


ENC = ['-an', '-c:v', 'libx264', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-bf', '0', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-video_track_timescale', '24000']
GRAIN = "vignette=angle=PI/11:mode=forward,noise=c0s=5:c0f=t+u"
FLICK = "eq=brightness='0.0045*sin(floor(n/2)*2.3)*cos(floor(n/2)*1.1)':eval=frame"


def even(a):
    return 2 * round(a * FPS / 2)


def clip(it):
    """색, 12fps, 확대, 그레인을 넣은 컷 전체(앞뒤 여분 포함). fi/fo는 여기서 하지 않는다."""
    name, src, a, b, gr, o = it
    img = src.endswith('.png')
    fa, n = even(a), round((b - a) * FPS)
    p = f'{F}클립/CUT{name}{"_" + VER if name.startswith("제목") else ""}.mp4'
    key = hashlib.md5(json.dumps([src, os.path.getmtime(src), fa, n, G[gr], {k: v for k, v in o.items() if k not in ('fi', 'fo')}, GRAIN, FLICK, 7], default=str).encode()).hexdigest()
    if os.path.exists(p) and os.path.exists(p + '.txt') and open(p + '.txt').read() == key:
        return name, (p, nfr(p))
    N = 240 if img else nfr(src)
    pre = f'setpts=N/{FPS}/TB'
    if not img and N == 240:
        pre, N = 'fps=24', 96
    hold = round(o.get('hold', 0) * FPS)
    N = min(N, 168) if img else N
    v = [pre]
    z = o.get('z')
    if z:
        z0, z1, x, y = z
        big = 'scale=3840:2160:force_original_aspect_ratio=increase:flags=lanczos,crop=3840:2160' if img else 'crop=1920:1080,scale=3840:2160:flags=lanczos'
        t = f'clip((on-{fa})/{max(1, n-1)},0,1)'
        e = f'({z0}+({z1}-{z0})*({t})*({t})*(3-2*({t})))'
        v += [big, 'setsar=1', f"zoompan=z='{e}':x='clip(iw*{x}-iw/zoom/2,0,iw-iw/zoom)':y='clip(ih*{y}-ih/zoom/2,0,ih-ih/zoom)':d=1:s=1920x1080:fps=24"]
    else:
        v += ['scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080' if img else 'crop=1920:1080', 'setsar=1']
    if hold:  # 마지막 화면을 멈춰 여백을 만든다
        v += [f'trim=end_frame={fa+n}', f'tpad=stop_mode=clone:stop={hold + 2}']
        N = fa + n + hold + (fa + n + hold) % 2
    if o.get('two', True):
        v += ['shuffleframes=0 0', f'setpts=N/{FPS}/TB']
        N -= N % 2
    if G[gr]:
        v.append(G[gr])
    if gr != 'none':
        if o.get('two', True):
            v.append(FLICK)
        v.append(GRAIN)
    vf = ','.join(v)
    if o.get('blur'):
        vf += f",split[p][q];[q]gblur=sigma=22,format=yuva420p,fade=t=out:st={fa/FPS+.5}:d={o['blur']}:alpha=1[r];[p][r]overlay"
    inp = ['-loop', '1', '-framerate', '24', '-i', src] if img else ['-i', src]
    ff(*inp, '-filter_complex', vf + ',format=yuv420p[o]', '-map', '[o]', '-r', '24', '-frames:v', str(N), *ENC, '-crf', '14', '-g', '12', p)
    open(p + '.txt', 'w').write(key)
    return name, (p, nfr(p))


uniq = {}
for it in CUTS:
    if it[1]:
        assert os.path.exists(it[1]), it[1]
        uniq.setdefault(it[0], it)
with ThreadPoolExecutor(1) as ex:
    clips = dict(ex.map(clip, uniq.values()))

# 시간표
tl, pos, first = [], 0, {}
for name, src, a, b, gr, o in CUTS:
    n = round((b - a) * FPS) + round(o.get('hold', 0) * FPS)
    i = even(a)
    if src:
        assert i + n <= clips[name][1], (name, i, n, clips[name])
    tl.append(dict(name=name, pos=pos, n=n, src=src, i=i, a=a, fi=round(o.get('fi', 0) * FPS), fo=round(o.get('fo', 0) * FPS)))
    first.setdefault(name, tl[-1])
    pos += n
TOTAL = pos


def T(c, t):
    k = first[c]
    return (k['pos'] - k['i']) / FPS + t


def span(c):
    k = first[c]
    return k['pos'] / FPS, (k['pos'] + k['n']) / FPS


end40 = first['검정3']['pos'] / FPS
total = dict(dur=TOTAL / FPS, end40=end40)

# ---- 화면
if not SOUND_ONLY:
    def seg(k):
        x = tl[k]; o = f'{F}_tmp/s{k:03d}.mp4'
        if x['src']:
            p = clips[x['name']][0]
            vf = f"trim=start_frame={x['i']}:end_frame={x['i']+x['n']},setpts=N/{FPS}/TB,fps=24"
            if x['fi']:
                vf += f",fade=t=in:s=0:n={x['fi']}"
            if x['fo']:
                vf += f",fade=t=out:s={x['n']-x['fo']}:n={x['fo']}"
            ff('-i', p, '-vf', vf, '-r', '24', '-frames:v', str(x['n']), *ENC, '-crf', '15', o)
        else:
            ff('-f', 'lavfi', '-i', f'color=black:s={W}x{H}:r=24', '-frames:v', str(x['n']), *ENC, '-crf', '15', o)
        assert nfr(o) == x['n'], (x, nfr(o))
    with ThreadPoolExecutor(1) as ex:
        list(ex.map(seg, range(len(tl))))
    open(F + '_tmp/list.txt', 'w').write('\n'.join(f"file 's{k:03d}.mp4'" for k in range(len(tl))))
    ff('-f', 'concat', '-safe', '0', '-i', F + '_tmp/list.txt', '-c', 'copy', '-bsf:v', 'setts=ts=N*1000:duration=1000', '-video_track_timescale', '24000', F + '_tmp/video.mp4')
    assert nfr(F + '_tmp/video.mp4') == TOTAL

# ---- 소리
tr, stems, N = snd.build(T, span, total, lambda n: f'07_편집/대사/{n}.wav')
mix = sum(stems.values())
sf.write(F + '_tmp/mix.wav', mix, snd.SR, subtype='FLOAT')
t = run('ffmpeg', '-nostdin', '-hide_banner', '-i', F + '_tmp/mix.wav', '-af', 'ebur128=peak=true', '-f', 'null', '-')
lu = float(re.findall(r'I:\s+(-[\d.]+) LUFS', t)[-1])
gain = min(8, -18 - lu)
print('믹스 LUFS', lu, '보정', round(gain, 1))
ff('-i', F + '_tmp/mix.wav', '-af', f'volume={gain:.2f}dB,alimiter=limit=0.8:attack=3:release=80:level=false', '-c:a', 'pcm_s16le', '-ar', '48000', F + f'소리_{VER}/전체믹스.wav')
g = snd.db(gain)
for f in os.listdir(F + f'소리_{VER}'):
    if f.endswith('.wav') and f != '전체믹스.wav':
        os.remove(F + f'소리_{VER}/' + f)
place = {}
for k, l in tr.items():
    place[k] = []
    for n, t0, y in l:
        st = int(np.floor(t0 * FPS + 1e-6))
        pad = int(round((t0 - st / FPS) * snd.SR))
        z = np.concatenate([np.zeros((pad, 2)), y * g])
        nf = int(np.ceil(len(z) / snd.SR * FPS))
        z = np.pad(z, ((0, int(nf / FPS * snd.SR) - len(z) if nf / FPS * snd.SR > len(z) else 0), (0, 0)))
        p = f'{F}소리_{VER}/{k}_{n}.wav'
        sf.write(p, np.clip(z, -1, 1), snd.SR, subtype='PCM_16')
        place[k].append((n, st, min(nf, TOTAL - st), p))
for k, m in stems.items():
    sf.write(f'{F}소리_{VER}/스템_{k}.wav', np.clip(m * g, -1, 1), snd.SR, subtype='PCM_16')

M = f'07_편집/대체품_{VER}.mp4'
ff('-i', F + '_tmp/video.mp4', '-i', F + f'소리_{VER}/전체믹스.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '256k', '-t', f'{TOTAL/FPS:.4f}', '-movflags', '+faststart', M)

# ---- 자막, 확인용
def tc(x):
    ms = round(x * 1000)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'


subs = []
for (c, n, s, e, t0, txt, sp, gg) in DLG:
    d = sf.info(f'07_편집/대사/{n}.wav').duration
    e = d if e is None else e
    subs.append((T(c, t0), T(c, t0) + e - s, txt))
open(f'07_편집/대체품_{VER}.srt', 'w', encoding='utf-8-sig').write('\n'.join(f'{i+1}\n{tc(a)} --> {tc(b)}\n{x}\n' for i, (a, b, x) in enumerate(subs)))


def at(x):
    c = round(x * 100)
    return f'{c//360000}:{c//6000%60:02d}:{c//100%60:02d}.{c%100:02d}'


ass = ['[Script Info]', 'PlayResX: 1920', 'PlayResY: 1080', '[V4+ Styles]', 'Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,BackColour,Bold,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV',
       'Style: S,Malgun Gothic,48,&H00FFFFFF,&H00000000,&H00000000,1,1,3,0,2,40,40,60', 'Style: N,Malgun Gothic,32,&H0000FFFF,&H00000000,&H00000000,1,1,2,0,7,30,30,24', '[Events]', 'Format: Start,End,Style,Text']
for x in tl:
    s = x['pos'] / FPS
    ass.append(f"Dialogue: {at(s)},{at(s+x['n']/FPS)},N,{x['name']}  {int(s//60)}:{s%60:04.1f}")
for a, b, x in subs:
    ass.append(f'Dialogue: {at(a)},{at(b)},S,' + x.replace('\n', '\\N'))
open(F + '_tmp/o.ass', 'w', encoding='utf8').write('\n'.join(ass))
ff('-i', M, '-vf', f'ass={F}_tmp/o.ass,scale=1280:720', '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'copy', f'07_편집/대체품_{VER}_컷번호.mp4')

# ---- Premiere XML: 화면 1트랙, 소리는 종류별 트랙
RATE = '<rate><timebase>24</timebase><ntsc>FALSE</ntsc></rate>'
seen = set()


def url(p):
    return 'file://localhost/' + quote(os.path.abspath(p).replace('\\', '/'), safe='/')


def fl(p, tot, kind):
    fid = 'f' + hashlib.md5(p.encode()).hexdigest()[:10]
    if fid in seen:
        return f'<file id="{fid}"/>'
    seen.add(fid)
    md = (f'<video><samplecharacteristics>{RATE}<width>{W}</width><height>{H}</height><pixelaspectratio>square</pixelaspectratio></samplecharacteristics></video>' if kind == 'v'
          else '<audio><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics><channelcount>2</channelcount></audio>')
    return f'<file id="{fid}"><name>{escape(os.path.basename(p))}</name><pathurl>{escape(url(p))}</pathurl>{RATE}<duration>{tot}</duration><media>{md}</media></file>'


def opac(x):
    if not (x['fi'] or x['fo']):
        return ''
    i, n = x['i'], x['n']
    ks = []
    if x['fi']:
        ks += [(i, 0), (i + x['fi'], 100)]
    if x['fo']:
        ks += [(i + n - x['fo'], 100), (i + n - 1, 0)]
    kf = ''.join(f'<keyframe><when>{w}</when><value>{v}</value></keyframe>' for w, v in ks)
    return ('<filter><effect><name>Opacity</name><effectid>opacity</effectid><effectcategory>motion</effectcategory><effecttype>motion</effecttype><mediatype>video</mediatype>'
            f'<parameter><parameterid>opacity</parameterid><name>opacity</name><valuemin>0</valuemin><valuemax>100</valuemax><value>100</value>{kf}</parameter></effect></filter>')


vx = ''
for k, x in enumerate(tl):
    if not x['src']:
        continue
    p, tot = clips[x['name']]
    vx += (f'<clipitem id="v{k}"><name>CUT{escape(x["name"])}</name><enabled>TRUE</enabled><duration>{tot}</duration>{RATE}<start>{x["pos"]}</start><end>{x["pos"]+x["n"]}</end>'
           f'<in>{x["i"]}</in><out>{x["i"]+x["n"]}</out>{fl(p, tot, "v")}{opac(x)}</clipitem>')
atr = ''
cid = 0
for k, l in place.items():
    # 겹치지 않게 트랙을 나눈다
    lanes = []
    for it in sorted(l, key=lambda z: z[1]):
        for ln in lanes:
            if ln[-1][1] + ln[-1][2] <= it[1]:
                ln.append(it); break
        else:
            lanes.append([it])
    for li, ln in enumerate(lanes):
        for ch in (1, 2):
            items = ''
            for j, (n, st, nf, p) in enumerate(ln):
                base = f'{k}{li}_{j}'
                tot = int(round(sf.info(p).duration * FPS))
                items += (f'<clipitem id="{base}_{ch}" premiereChannelType="stereo"><name>{escape(k)}_{escape(n)}</name><enabled>TRUE</enabled><duration>{tot}</duration>{RATE}<start>{st}</start><end>{st+nf}</end><in>0</in><out>{nf}</out>'
                          f'{fl(p, tot, "a")}<sourcetrack><mediatype>audio</mediatype><trackindex>{ch}</trackindex></sourcetrack>'
                          + ''.join(f'<link><linkclipref>{base}_{c}</linkclipref><mediatype>audio</mediatype><groupindex>1</groupindex></link>' for c in (1, 2)) + '</clipitem>')
            atr += f'<track currentExplodedTrackIndex="{ch-1}" totalExplodedTrackCount="2" premiereTrackType="Stereo"><name>{escape(k)}</name>{items}<outputchannelindex>{ch}</outputchannelindex></track>'
    print(k, '트랙', len(lanes))
mk = ''.join(f'<marker><name>CUT{escape(x["name"])}</name><comment></comment><in>{x["pos"]}</in><out>-1</out></marker>' for x in tl if not (x['name'].startswith('40_') and x is not first[x['name']]))
xml = (f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4"><sequence id="seq2"><name>대체품_영화편집_{VER}</name><duration>{TOTAL}</duration>{RATE}<timecode>{RATE}<string>00:00:00:00</string><frame>0</frame><displayformat>NDF</displayformat></timecode>{mk}'
       f'<media><video><format><samplecharacteristics>{RATE}<width>{W}</width><height>{H}</height><anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio><fielddominance>none</fielddominance></samplecharacteristics></format><track>{vx}</track></video>'
       f'<audio><numOutputChannels>2</numOutputChannels><format><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics></format>{atr}</audio></media></sequence></xmeml>')
open(f'07_편집/대체품_{VER}.xml', 'w', encoding='utf8').write(xml)
print(f'길이 {TOTAL/FPS:.2f}초')
for x in tl:
    if not x['name'].startswith('40_') or x is first[x['name']]:
        print(x['name'], f"{x['pos']/FPS:.2f}", end=' | ')
