"""효과음 생성(일레븐랩스 Sound Effects). 이미 있는 파일은 건너뛴다."""
import re, json, os, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
KEY = re.search(r'ELEVENLABS_API_KEY=["\']?([^"\'\s]+)', open(os.path.join(HERE, '..', '.env.local'), encoding='utf8').read()).group(1)
L = [
 ('알림', 1.0, 'single soft smartphone notification chime, close, dry'),
 ('화면넘김', .7, 'subtle soft finger swipe on smartphone glass screen, very quiet short whoosh, dry'),
 ('화면터치', .5, 'single soft smartphone UI tap tick, dry, quiet'),
 ('화면끔', .6, 'smartphone screen lock click, small soft mechanical click, dry'),
 ('방_밤', 12, 'quiet bedroom room tone at night, very faint distant city hum, no voices, no music, seamless ambience'),
 ('방_아침', 12, 'quiet bedroom in the early morning, faint birds chirping outside a closed window, soft room tone, no voices, seamless ambience'),
 ('골목_밤', 12, 'quiet residential alley at night, distant crickets, faint distant traffic, light breeze, no voices, seamless ambience'),
 ('거리_아침', 12, 'calm residential street on a sunny morning, sparrows chirping, soft breeze, very distant cars, no voices, seamless ambience'),
 ('강의실', 14, 'university classroom before lecture, indistinct soft murmur of a few students chatting far away, occasional chair and paper sounds, room reverb, no clear words'),
 ('웃음', 3, 'small group of students chuckling softly in a classroom, distant, natural'),
 ('시계', 10, 'small alarm clock ticking steadily on a desk in a quiet room, close, dry'),
 ('발소리_골목', 4, 'one person walking slowly on asphalt in sneakers at night, tired pace, light footsteps, no other sounds'),
 ('발소리_거리', 4, 'first person walking on a paved street in sneakers, steady relaxed footsteps, no other sounds'),
 ('발소리_방', 3, 'soft footsteps walking away on a wooden floor, then out of the room'),
 ('가방뒤적', 4, 'hand rummaging inside a canvas tote bag, fabric rustle, keys and small tools jingle softly'),
 ('현관문', 2.5, 'heavy metal front door closing gently with a solid latch click, outdoors'),
 ('방문', 2, 'wooden room door closing softly indoors'),
 ('문열림', 2.5, 'metal front door unlatching and opening from inside, short soft creak'),
 ('연필', 6, 'pencil sketching on paper, gentle strokes, close, quiet room'),
 ('연필떨어짐', 1.5, 'wooden pencil dropping onto a wooden desk and rolling briefly, close, dry'),
 ('종이', 3, 'sheets of paper being slid and stacked on a wooden desk, close'),
 ('책더미', 1.5, 'thick stack of paper and books dropped softly on a wooden desk'),
 ('가방챙김', 3, 'putting a paper folder into a canvas bag, fabric and paper rustle'),
 ('옷스침', 2.5, 'fleece sleeve being pulled up, soft fabric rustle, close'),
 ('이불', 2.5, 'person lying down in bed, blanket rustle, soft mattress creak'),
 ('쓰다듬기', 2, 'hand gently patting and stroking yarn hair of a felt doll, soft textile sound, close'),
 ('알람', 3, 'small digital alarm clock beeping, muffled, bedroom'),
 ('실당김', 3, 'single thick sewing thread being slowly pulled taut through felt fabric, quiet tense creaking friction, very close, horror foley'),
 ('실당김_짧게', 1.2, 'short tiny thread pulled tight through cloth, quick quiet friction, very close'),
 ('바늘', 1.5, 'needle piercing felt fabric and thread pulling through, small close foley'),
 ('관절', 1.2, 'single tiny creak of a stiff cloth and wooden doll joint turning, dry, very close'),
 ('찌름', 2, 'deep soft low boom hit with dark reverb, subtle cinematic impact'),
 ('역재생', 2, 'short subtle reverse swell, dark airy riser, cinematic'),
]


def gen():
    for n, d, p in L:
        for t in (1, 2):
            o = os.path.join(HERE, '효과음', f'{n}_{t}.mp3')
            if os.path.exists(o):
                continue
            r = urllib.request.Request('https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_192',
                                       data=json.dumps({'text': p, 'duration_seconds': max(.5, d), 'prompt_influence': .6}).encode(),
                                       headers={'xi-api-key': KEY, 'Content-Type': 'application/json'})
            try:
                b = urllib.request.urlopen(r, timeout=90).read()
            except urllib.error.HTTPError as e:
                print(n, e.code, e.read()[:200])
                if e.code in (401, 402, 403):
                    return
                if e.code == 400:
                    r = None
                continue
            open(o, 'wb').write(b)
            print(n, t, len(b), flush=True)


if __name__ == '__main__':
    gen()
