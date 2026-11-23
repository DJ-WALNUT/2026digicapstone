"""타입캐스트 ↔ 일레븐랩스 비교용 음성 생성 (CUT 04 · 15 · 36b)

.venv/Scripts/python 03_대본/elevenlabs_compare.py
결과: 03_대본/tts_비교/*.mp3 + 비교듣기.html (타입캐스트 테이크와 나란히 재생)
이미 있는 파일은 건너뜀. 기존 tts/ 파일은 읽기만 하고 바꾸지 않음.

API 키: 프로젝트 루트 .env.local (ELEVENLABS_API_KEY)
한국어 라이브러리 목소리 사용 → 유료 요금제(Starter 이상) 필요
"""
import html
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env.local")  # SDK가 import 때 키를 읽으므로 먼저 실행
from elevenlabs import ElevenLabs, VoiceSettings  # noqa: E402

MODEL = "eleven_v4"
OUT = HERE / "tts_비교"
TAKES = 2

# 인물별 후보 (모두 라이브러리의 한국어 여성)
VOICES = {
    "서연": [("Sora", "JpGoUJuLFthrFkcdBy4k"), ("Dain", "7kc4OBeoZqw3n2gxf0Bt")],
    "수빈": [("Yeonhee", "vhhJX7dyal9WlYW2UAsj"), ("Han", "8jHHF8rMqMlg8if2mOUe")],
}
# 컷, 인물, 슬러그, 태그를 넣은 대사 (v4는 speed/style 미지원 → 태그와 문장부호로 조절)
LINES = [
    ("CUT04", "서연", "나도누가", "[sighs] [tired] …나도 누가 대신 해줬으면 좋겠다."),
    ("CUT15", "서연", "진짜야고마워", "[surprised] 너, 진짜야? [softly, smiling] …고마워."),
    ("CUT36b", "수빈", "하나구했구나", "[calm, smiling] …너도 하나 구했구나?"),
]


def main():
    client = ElevenLabs()
    OUT.mkdir(exist_ok=True)
    page = ['<!doctype html><meta charset="utf-8"><title>TTS 비교</title>'
            '<body style="font-family:sans-serif;max-width:720px;margin:2em auto">']
    for cut, speaker, slug, text in LINES:
        page.append(f"<h2>{cut} {speaker}</h2><p>{html.escape(text)}</p>")
        items = [(f"타입캐스트 {p.stem.rsplit('_', 1)[-1]}", f"../tts/{p.name}")
                 for p in sorted((HERE / "tts").glob(f"{cut}_{speaker}_{slug}_*.wav"))]
        for name, voice_id in VOICES[speaker]:
            for t in range(1, TAKES + 1):
                p = OUT / f"{cut}_{speaker}_{slug}_EL-{name}_t{t}.mp3"
                if not p.exists():
                    audio = client.text_to_speech.convert(
                        text=text, voice_id=voice_id, model_id=MODEL, language_code="ko",
                        output_format="mp3_44100_128",
                        voice_settings=VoiceSettings(stability=0.5, similarity_boost=0.75))
                    p.write_bytes(b"".join(audio))
                print(p.name)
                items.append((f"일레븐랩스 {name} t{t}", p.name))
        for label, src in items:
            page.append(f'<p>{label}<br><audio controls src="{html.escape(src)}"></audio></p>')
    (OUT / "비교듣기.html").write_text("\n".join(page), encoding="utf-8")


if __name__ == "__main__":
    main()
