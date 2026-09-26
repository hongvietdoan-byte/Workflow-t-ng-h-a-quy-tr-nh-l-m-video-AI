"""Đo tốc độ nói thật của giọng TTS đã tạo — MIỄN PHÍ, CHỈ ĐỌC (director.md N2, dialogue.RATE).

    py tools/measure_speech_rate.py                    (mọi dự án trong data/projects)
    py tools/measure_speech_rate.py --data D:/AI-Video-Pipeline/data/projects

Đọc `audio_assets/assets.json` của từng dự án (câu TTS đã xong: chữ + `duration_ms`), đếm âm tiết như code (`dialogue.syllables`),
đo khoảng lặng đầu/cuối file bằng ffmpeg `silencedetect` và in: tốc độ nói (âm tiết/giây) theo từng giọng và chung, sai số của công
thức hiện tại (âm tiết ÷ RATE + BREATH) so với độ dài thật, và số câu bị ước tính THIẾU hơn 0,5 s (những câu làm shot thoại quá ngắn).
Không gọi dịch vụ nào, không ghi gì.
"""
import argparse
import glob
import json
import os
import re
import statistics
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import dialogue  # noqa: E402
from core.ffmpeg_studio import find_ffmpeg  # noqa: E402

MIN_SYLLABLES = 3          # a one-word line is mostly the voice's attack and release — not a speaking speed


def speech_seconds(ffmpeg: str, path: str, total: float) -> float:
    """The file's length minus its leading / trailing silence (−40 dB, ≥ 0,15 s)."""
    out = subprocess.run([ffmpeg, "-hide_banner", "-i", path, "-af", "silencedetect=n=-40dB:d=0.15", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    lead = ends[0] if starts and starts[0] < 0.05 and ends else 0.0
    tail = total - starts[-1] if starts and len(ends) < len(starts) else 0.0
    return max(total - lead - tail, 0.1)


def collect(data: str):
    ffmpeg = find_ffmpeg()
    rows = []
    for manifest in sorted(glob.glob(os.path.join(data, "*", "audio_assets", "assets.json"))):
        project = os.path.basename(os.path.dirname(os.path.dirname(manifest)))
        folder = os.path.dirname(manifest)
        with open(manifest, encoding="utf-8") as f:
            items = json.load(f)
        for e in items:
            if e.get("kind") != "tts" or e.get("state") != "succeeded" or not e.get("duration_ms"):
                continue
            n = dialogue.syllables(e.get("text") or e.get("label") or "")
            path = e.get("file") or ""
            path = path if os.path.isabs(path) else os.path.join(folder, path)
            if n < MIN_SYLLABLES or not os.path.exists(path):
                continue
            total = e["duration_ms"] / 1000.0
            rows.append({"project": project, "voice": str(e.get("voice_name") or e.get("voice_id") or "?"), "syllables": n,
                         "file_s": total, "speech_s": speech_seconds(ffmpeg, path, total)})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default=os.path.join(os.path.dirname(__file__), "..", "data", "projects"))
    a = ap.parse_args()
    rows = collect(a.data)
    if not rows:
        sys.exit("Chưa có câu TTS nào đã xong (≥ 3 âm tiết) để đo.")
    rates = sorted(r["syllables"] / r["speech_s"] for r in rows)
    pick = lambda q: rates[min(int(q * len(rates)), len(rates) - 1)]  # noqa: E731
    print(f"{len(rows)} câu · dự án {', '.join(sorted({r['project'] for r in rows}))}")
    print(f"Tốc độ nói (âm tiết/giây, bỏ lặng đầu/cuối): trung vị {statistics.median(rates):.2f} · 10% chậm nhất ≤ {pick(0.1):.2f} · "
          f"10% nhanh nhất ≥ {pick(0.9):.2f}")
    by_voice = {}
    for r in rows:
        by_voice.setdefault(r["voice"], []).append(r["syllables"] / r["speech_s"])
    for v, xs in sorted(by_voice.items(), key=lambda kv: -len(kv[1])):
        print(f"  giọng {v}: {len(xs)} câu, trung vị {statistics.median(xs):.2f}")
    errors = [r["syllables"] / dialogue.RATE + dialogue.BREATH - r["file_s"] for r in rows]
    short = sum(1 for e in errors if e < -0.5)
    print(f"Công thức hiện tại (âm tiết ÷ {dialogue.RATE:g} + {dialogue.BREATH:g} s): lệch trung bình {statistics.mean(errors):+.2f} s · "
          f"{short}/{len(rows)} câu bị ước tính THIẾU > 0,5 s")


if __name__ == "__main__":
    main()
