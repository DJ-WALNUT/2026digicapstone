"""CUT 15 연기 지시 비교 (일레븐랩스): 태그·안정도만 바꿔 감정 기복 확인

.venv/Scripts/python 03_대본/elevenlabs_cut15.py  → tts_비교/CUT15_*.mp3 + CUT15_듣기.html
"""
import html
from elevenlabs_compare import HERE, MODEL, OUT, VOICES, ElevenLabs, VoiceSettings

VARIANTS = [
    ("A-태그없음", "너, 진짜야? …고마워.", 0.5),
    ("B-태그없음-안정", "너, 진짜야? …고마워.", 0.8),
    ("C-약한지시", "[quietly] 너, 진짜야? …고마워.", 0.8),
]
BASE = "CUT15_서연_진짜야고마워"


def main():
    client = ElevenLabs()
    items = [("타입캐스트 " + p.stem[-2:], f"../tts/{p.name}") for p in sorted((HERE / "tts").glob(BASE + "_t?.wav"))]
    for name, vid in VOICES["서연"]:
        items += [(f"{name} 기존(강한 지시) t{t}", f"{BASE}_EL-{name}_t{t}.mp3") for t in (1, 2)]
        for key, text, stab in VARIANTS:
            for t in (1, 2):
                p = OUT / f"{BASE}_EL-{name}_{key}_t{t}.mp3"
                if not p.exists():
                    p.write_bytes(b"".join(client.text_to_speech.convert(
                        text=text, voice_id=vid, model_id=MODEL, language_code="ko",
                        output_format="mp3_44100_128",
                        voice_settings=VoiceSettings(stability=stab, similarity_boost=0.75))))
                items.append((f"{name} {key} t{t}", p.name))
    body = "".join(f'<p>{html.escape(l)}<br><audio controls src="{html.escape(s)}"></audio></p>' for l, s in items)
    (OUT / "CUT15_듣기.html").write_text('<!doctype html><meta charset="utf-8"><title>CUT15 비교</title>' + body, encoding="utf-8")


if __name__ == "__main__":
    main()
