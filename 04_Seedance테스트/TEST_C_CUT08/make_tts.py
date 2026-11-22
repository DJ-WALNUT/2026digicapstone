"""타입캐스트 API로 CUT 08 대사 음성 생성 (Seedance TEST C 준비)

준비
  1. 타입캐스트 API 콘솔(https://studio.typecast.ai/developers/api)에서 API 키 발급
  2. 이 폴더의 .env.example 을 복사해 .env 로 이름을 바꾸고 키를 붙여넣기
     (.env 는 .gitignore 에 걸려 있어 레포에 올라가지 않음)

사용
  python make_tts.py voices              # 서연용 후보 목소리 목록 (여성·청년)
  python make_tts.py voices --all        # 전체 목록
  python make_tts.py make --voice tc_xxx # CUT 08 테이크 3개 생성 → audio/
  python make_tts.py make                # .env 의 TYPECAST_VOICE_ID 사용

생성되는 테이크 (같은 목소리, 감정 설정만 다름 → 마음에 드는 1개를 Seedance에 첨부)
  take1_smart   : 앞뒤 대사 맥락으로 감정 자동 (ssfm-v30/v31 전용)
  take2_normal  : 기본 감정
  take3_happy   : 가볍게 웃는 느낌 (happy, 강도 0.6)

API 사양: POST https://api.typecast.ai/v1/text-to-speech (X-API-KEY), GET /v3/voices
"""
import json
import os
import sys
import urllib.error
import urllib.request
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = "https://api.typecast.ai"
MODEL_DEFAULT = "ssfm-v31"

# CUT 08 — 워드 스토리보드 기준
CUT = "CUT08"
SPEAKER = "서연"
SLUG = "너나닮았다"
TEXT = "너… 나 닮았다."
PREV = "…뭐야?"            # CUT 06 서연 대사 (smart 모드 맥락)
NEXT = ""


def load_env():
    env = {}
    f = HERE / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("TYPECAST_API_KEY", "TYPECAST_VOICE_ID", "TYPECAST_MODEL", "TYPECAST_PITCH"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def call(method, path, key, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method,
                                 headers={"X-API-KEY": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.read(), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")
        hints = {401: "API 키 확인", 402: "크레딧 부족 또는 계정 비활성", 404: "voice_id 확인",
                 422: "텍스트에 합성 불가 문자", 429: "요청이 너무 많음, 잠시 후 다시"}
        sys.exit(f"[오류 {e.code}] {hints.get(e.code, '')}\n{msg}")


def voices(key, model, show_all):
    raw, _ = call("GET", f"/v3/voices?model={model}", key)
    items = json.loads(raw)
    if not show_all:
        items = [v for v in items if v.get("gender") == "female" and v.get("age") in ("young_adult", "teenager")]
    print(f"{len(items)}개 (model={model}{'' if show_all else ', 여성·청년/10대'})\n")
    for v in items:
        name = v.get("voice_name", {})
        emo = next((m.get("emotions") for m in v.get("models", []) if m.get("version") == model), [])
        print(f"{v['voice_id']}  {name.get('kor') or name.get('eng')}  "
              f"[{v.get('gender')}/{v.get('age')}]  {', '.join(v.get('use_cases', [])[:3])}")
        print(f"    감정: {', '.join(emo)}  미리듣기: {v.get('preview_url') or '-'}")


def wav_seconds(p):
    try:
        with wave.open(str(p)) as w:
            return w.getnframes() / w.getframerate()
    except Exception:
        return None


def make(key, voice, model, pitch=0):
    out = HERE / "audio"
    out.mkdir(exist_ok=True)
    takes = [
        ("take1_smart", {"emotion_type": "smart", "previous_text": PREV, "next_text": NEXT}),
        ("take2_normal", {"emotion_type": "preset", "emotion_preset": "normal", "emotion_intensity": 1.0}),
        ("take3_happy", {"emotion_type": "preset", "emotion_preset": "happy", "emotion_intensity": 0.6}),
    ]
    if model == "ssfm-v21":
        takes = takes[1:]  # v21은 smart 미지원
    for tag, prompt in takes:
        body = {
            "voice_id": voice, "text": TEXT, "model": model, "language": "kor",
            "prompt": prompt,
            "output": {"audio_format": "wav", "volume": 100, "audio_pitch": pitch, "audio_tempo": 1.0},
        }
        raw, ctype = call("POST", "/v1/text-to-speech", key, body)
        if "json" in ctype:
            sys.exit(f"[예상 밖 응답] {raw[:300]!r}")
        p = out / f"{CUT}_{SPEAKER}_{SLUG}_{tag}.wav"
        p.write_bytes(raw)
        sec = wav_seconds(p)
        print(f"저장: {p.name}  ({sec:.2f}초)" if sec else f"저장: {p.name}")
    meta = {"cut": CUT, "text": TEXT, "voice_id": voice, "model": model, "audio_pitch": pitch}
    (out / f"{CUT}_tts_info.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n마음에 드는 테이크 1개를 Seedance TEST C의 Audio 1로 첨부하세요. 같은 voice_id를 대체품(CUT 31~)에도 사용합니다.")


def main():
    env = load_env()
    key = env.get("TYPECAST_API_KEY")
    if not key:
        sys.exit("TYPECAST_API_KEY 가 없습니다. .env.example 을 .env 로 복사하고 키를 넣어 주세요.")
    model = env.get("TYPECAST_MODEL") or MODEL_DEFAULT
    args = sys.argv[1:]
    if not args or args[0] not in ("voices", "make"):
        sys.exit(__doc__)
    if args[0] == "voices":
        voices(key, model, "--all" in args)
    else:
        voice = args[args.index("--voice") + 1] if "--voice" in args else env.get("TYPECAST_VOICE_ID")
        if not voice:
            sys.exit("목소리를 정해 주세요: python make_tts.py voices 로 고른 뒤 --voice tc_xxx 또는 .env 의 TYPECAST_VOICE_ID")
        make(key, voice, model, int(env.get("TYPECAST_PITCH") or 0))


if __name__ == "__main__":
    main()
