"""전체 대사 생성 (일레븐랩스 eleven_v4)

.venv/Scripts/python 03_대본/elevenlabs_batch.py [CUT06 ...]
입력: EL_디렉팅.tsv (컷별 스토리보드 상황 scene, 연기 의도 intent, 태그 포함 text)
결과: tts_EL/<컷>_<인물>_<슬러그><variant>_t1.wav … + 듣기.html
앞뒤 무음은 잘라 냄. 이미 있는 파일은 건너뜀 (다시 만들려면 해당 wav를 다른 곳으로 옮기기).
"""
import csv
import html
import subprocess
import sys

from elevenlabs_compare import HERE, MODEL, ElevenLabs, VoiceSettings

VOICES = {
    "Sora": "JpGoUJuLFthrFkcdBy4k",     # 서연·대체품 (확정)
    "Yeonhee": "vhhJX7dyal9WlYW2UAsj",  # 수빈 (확정)
    "JunHo": "HrAPO433QYkPmU4F4CHw", "Jinho": "nrHAD53jYEGsNyVoQiv6",  # 민준 후보
    "Jiae": "3TIJuP53f43TXi08ZJE1", "Aria": "O2KReOFLpoR65nz6C9Se",    # SNS 후보
    "Han": "8jHHF8rMqMlg8if2mOUe", "Bee": "FhznnhFhq61uh1kbvfw1",      # 잡담 후보
}
OUT = HERE / "tts_EL"
TAKES = 2
TRIM = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.1"


def main():
    only = sys.argv[1:]
    with open(HERE / "EL_디렉팅.tsv", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f, delimiter="\t") if not only or r["cut"] in only]
    client = ElevenLabs()
    OUT.mkdir(exist_ok=True)
    page, last = ['<!doctype html><meta charset="utf-8"><title>일레븐랩스 전체 대사</title>'], None
    for r in rows:
        if r["cut"] != last:
            page.append(f"<h2>{r['cut']} {r['speaker']}</h2><p>상황: {html.escape(r['scene'])}</p>")
            last = r["cut"]
        base = f"{r['cut']}_{r['speaker']}_{r['slug']}"
        finals = sorted(OUT.glob(f"{base}*FINAL*.wav"))
        for t in range(1, TAKES + 1):
            p = OUT / f"{base}{r['variant']}_t{t}.wav"
            if not p.exists() and finals:
                continue  # 이미 FINAL을 정한 컷은 빠진 테이크를 다시 만들지 않음
            if not p.exists():
                mp3 = b"".join(client.text_to_speech.convert(
                    text=r["text"], voice_id=VOICES[r["voice"]], model_id=MODEL, language_code="ko",
                    output_format="mp3_44100_128",
                    voice_settings=VoiceSettings(stability=float(r["stability"]), similarity_boost=0.75)))
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "-", "-af",
                                f"{TRIM},areverse,{TRIM},areverse", str(p)], input=mp3, check=True)
                print("생성", p.name)
            page.append(f"<p>{html.escape(p.stem)} ({r['voice']}) {html.escape(r['text'])}<br>"
                        f'<audio controls src="{html.escape(p.name)}"></audio></p>')
    if not only:
        (OUT / "듣기.html").write_text("\n".join(page), encoding="utf-8")


if __name__ == "__main__":
    main()
