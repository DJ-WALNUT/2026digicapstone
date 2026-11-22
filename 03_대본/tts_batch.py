"""대사 일괄 TTS 생성 (타입캐스트)

python tts_batch.py            # TTS_대사목록.tsv 전체, 대사당 2테이크 → tts/
python tts_batch.py CUT15 CUT34 --takes 3   # 특정 컷만
이미 있는 파일은 건너뜀 (다시 만들려면 해당 wav 삭제)

API 키: 이 폴더 또는 04_Seedance테스트/TEST_C_CUT08 의 .env (TYPECAST_API_KEY)
결과: tts/<컷>_<인물>_<슬러그>_t1.wav … + tts/길이표.tsv
고른 테이크는 이름 끝을 _FINAL.wav 로 바꿔서 사용
말 속도: tsv 의 tempo 열 (일상 1.1~1.15 / 차분·지침·대체품 1.0)
"""
import csv, json, sys, wave, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = "ssfm-v31"
# 인물별 목소리 (voice_id, 감정 방식)
VOICES = {
    "서연":  ("tc_6837dec48fc46637a9272b88", "smart"),      # 소예
    "대체품": ("tc_6837dec48fc46637a9272b88", "tonedown"),   # 소예 + tonedown
    "수빈":  ("tc_62c3de188bb43a2b3ab3ef08", "smart"),      # 소라
    "민준":  ("tc_6a3350f8e5a50a4abe948fa8", "smart"),      # 도윤
    "SNS":   ("tc_61e748d0fd9fb2d2cacbb04d", "smart"),      # 예나
    "잡담":  ("tc_68785db8ba9cd7503f27d921", "smart"),      # 고운
}


def api_key():
    for f in (HERE / ".env", HERE.parent / "04_Seedance테스트" / "TEST_C_CUT08" / ".env"):
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.startswith("TYPECAST_API_KEY="):
                    return line.split("=", 1)[1].strip()
    sys.exit("TYPECAST_API_KEY 를 찾을 수 없습니다 (.env)")


def tts(key, voice, text, prompt, tempo=1.0):
    body = {"voice_id": voice, "text": text, "model": MODEL, "language": "kor",
            "prompt": prompt, "output": {"audio_format": "wav", "audio_tempo": tempo}}
    req = urllib.request.Request("https://api.typecast.ai/v1/text-to-speech", data=json.dumps(body).encode(),
                                 method="POST", headers={"X-API-KEY": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"[오류 {e.code}] {e.read().decode('utf-8', 'replace')}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    takes = int(sys.argv[sys.argv.index("--takes") + 1]) if "--takes" in sys.argv else 2
    if "--takes" in sys.argv:
        args.remove(str(takes))
    key = api_key()
    out = HERE / "tts"
    out.mkdir(exist_ok=True)
    rows = list(csv.DictReader(open(HERE / "TTS_대사목록.tsv", encoding="utf-8"), delimiter="\t"))
    table = []
    for r in rows:
        if args and r["cut"] not in args:
            continue
        voice, mode = VOICES[r["speaker"]]
        if mode == "smart":
            prompt = {"emotion_type": "smart", "previous_text": r["prev"], "next_text": r["next"]}
        else:
            prompt = {"emotion_type": "preset", "emotion_preset": mode, "emotion_intensity": 1.0}
        for t in range(1, takes + 1):
            p = out / f"{r['cut']}_{r['speaker']}_{r['slug']}_t{t}.wav"
            if not p.exists():
                p.write_bytes(tts(key, voice, r["text"], prompt, float(r.get("tempo") or 1.0)))
            with wave.open(str(p)) as w:
                sec = round(w.getnframes() / w.getframerate(), 2)
            table.append((r["cut"], r["speaker"], p.name, sec, r["lipsync"], r["text"]))
            print(f"{p.name}\t{sec}s")
    with open(out / "길이표.tsv", "w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f, delimiter="\t")
        wr.writerow(["cut", "speaker", "file", "sec", "lipsync", "text"])
        wr.writerows(table)


if __name__ == "__main__":
    main()
