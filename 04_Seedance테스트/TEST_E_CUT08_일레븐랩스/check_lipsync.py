"""립싱크 확인 자료 만들기 (합격 여부는 사람이 보고 판단)

uv run --no-project --python 3.12 --with numpy check_lipsync.py <영상.mp4> [--start 초] [--wav 음성.wav]
1) <영상>_TTS덮음.mp4 : 영상 소리를 원본 TTS로 교체 (말 시작 시점에 맞춤)
2) <영상>_입모양.png  : 말하기 전 1장 / 말하는 중 6장 / 말한 뒤 1장
말 시작은 추정값. 어긋나면 --start 로 직접 지정. ffmpeg 필요.
"""
import argparse
import subprocess
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SR = 16000


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR),
                          "-af", "highpass=f=150,lowpass=f=3000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(float)


def onset(y):
    """주변 소음보다 커진 소리가 80ms 이상 이어지는 첫 시점"""
    e = np.array([np.sqrt((y[i:i + 160] ** 2).mean()) for i in range(0, len(y) - 160, 160)])
    on = e > max(e.max() * 0.2, np.median(e) * 2)
    for i in range(len(on) - 8):
        if on[i:i + 8].all():
            return i * 0.01
    return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--start", type=float)
    ap.add_argument("--wav", type=Path, default=HERE / "audio" / "CUT08_서연_너나닮았다_FINAL.wav")
    a = ap.parse_args()
    ref = load(a.wav)
    lead = onset(ref)
    start = a.start if a.start is not None else onset(load(a.video))
    vdur = float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=duration",
                                 "-of", "csv=p=0", str(a.video)], capture_output=True, text=True).stdout.strip().strip(","))
    speech = len(ref) / SR - lead
    print(f"영상 속 말 시작 {'지정' if a.start is not None else '추정'}: {start:.2f}초 / 음성 길이(말 시작부터) {speech:.2f}초 / 영상 {vdur:.2f}초")
    if start + speech > vdur:
        print("주의: 음성이 영상 끝을 넘습니다. 시작 시점이나 영상 길이를 확인하세요.")
    stem = a.video.stem[:30].strip()
    delay = max(0, int((start - lead) * 1000))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(a.video), "-i", str(a.wav), "-filter_complex",
                    f"[1:a]adelay={delay}:all=1,apad[a]", "-map", "0:v", "-map", "[a]", "-t", str(vdur), "-c:v", "copy", "-c:a", "aac",
                    str(a.video.with_name(stem + "_TTS덮음.mp4"))], check=True)
    pts = [start - .3] + [start + speech * q for q in (.08, .25, .42, .58, .75, .92)] + [start + speech + .2]
    pts = [min(max(0, t), vdur - .1) for t in pts]
    inp = sum((["-ss", f"{t:.3f}", "-i", str(a.video)] for t in pts), [])
    flt = "".join(f"[{i}:v]trim=end_frame=1,setpts=PTS-STARTPTS,scale=480:270,setsar=1[v{i}];" for i in range(8))
    flt += "".join(f"[v{i}]" for i in range(8)) + "xstack=inputs=8:layout=" + "|".join(
        f"{480 * (i % 4)}_{270 * (i // 4)}" for i in range(8))
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inp, "-filter_complex", flt, "-frames:v", "1",
                    str(a.video.with_name(stem + "_입모양.png"))], check=True)
    print("입모양 추출 시점(초):", ", ".join(f"{t:.2f}" for t in pts))


if __name__ == "__main__":
    main()
