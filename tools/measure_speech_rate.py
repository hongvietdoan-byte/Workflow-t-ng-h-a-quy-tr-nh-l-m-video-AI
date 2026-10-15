"""Đo tốc độ nói thật của giọng TTS đã tạo — MIỄN PHÍ, CHỈ ĐỌC (director.md N2, dialogue.RATE).

    py tools/measure_speech_rate.py                    (mọi dự án trong data/projects)
    py tools/measure_speech_rate.py --data D:/AI-Video-Pipeline/data/projects
    py tools/measure_speech_rate.py --data D:/AI-Video-Pipeline/data/projects --write data/speech_rates.json   (15/10: bảng theo giọng)
        [--samples tests/fixtures/speech_samples.json]   (mẫu đo — giọng, âm tiết, giây file, giây nói — cho test sai số theo giọng)

Đọc `audio_assets/assets.json` của từng dự án (câu TTS đã xong: chữ + `duration_ms`), đếm âm tiết như code (`dialogue.syllables`),
đo khoảng lặng đầu/cuối file bằng ffmpeg `silencedetect` và in: tốc độ nói (âm tiết/giây) theo từng giọng và chung, sai số của công
thức hiện tại (âm tiết ÷ tốc độ giọng + BREATH, dialogue.voice_rate) so với độ dài thật, và số câu bị ước tính THIẾU hơn 0,5 s.
Không gọi dịch vụ nào; chỉ ghi khi có --write / --samples (vào tệp được chỉ, không ghi vào thư mục --data).
15/10 (rà vòng gop-1510): bảng đo trên GIÂY NÓI (`speech_s`, đã cắt lặng đầu/cuối) — BREATH của dialogue.needed_seconds là phần lặng,
không đếm hai lần; trước đây đo trên độ dài cả file + p10 → giọng 70 câu 23 âm tiết ước 14,4 s.
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

from core import dialogue, pacing, voice_direction  # noqa: E402
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
            n = pacing.syllables(e.get("text") or re.sub(r"^\[[^\]]*\]\s*", "", e.get("label") or ""))   # = dialogue.line_seconds
            path = e.get("file") or ""
            path = path if os.path.isabs(path) else os.path.join(folder, path)
            if n < MIN_SYLLABLES or not os.path.exists(path):
                continue
            total = e["duration_ms"] / 1000.0
            pace = voice_direction.PACES.get((e.get("delivery") or {}).get("pace") or "normal") or 1.0
            rows.append({"project": project, "voice": str(e.get("voice_name") or e.get("voice_id") or "?"), "syllables": n,
                         "voice_id": e.get("voice_id"), "speed": round(pace * float(e.get("profile_speed") or 1.0), 3),   # speed sent
                         "file_s": total, "speech_s": speech_seconds(ffmpeg, path, total)})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default=os.path.join(os.path.dirname(__file__), "..", "data", "projects"))
    ap.add_argument("--write", help="ghi bảng theo giọng (p10/p25/p50 âm tiết/giây theo GIÂY NÓI đã cắt lặng) vào tệp JSON này "
                                    "(giữ speed_follows)")
    ap.add_argument("--samples", help="ghi mẫu đo (voice_id, syllables, file_s, speech_s — không chữ, không đường dẫn) vào tệp JSON này")
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
    errors = [r["syllables"] / dialogue.voice_rate(r["voice_id"]) + dialogue.BREATH - r["file_s"] for r in rows]
    short = sum(1 for e in errors if e < -0.5)
    by_speed = {}
    for r in rows:
        by_speed.setdefault((r["voice_id"], r["speed"]), []).append(r["syllables"] / r["file_s"])
    print("Theo giọng × tốc độ gửi (âm tiết/giây theo độ dài file — so xem model có đọc nhanh hơn khi speed > 1 không):")
    for (v, sp), xs in sorted(by_speed.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        print(f"  giọng {v} speed {sp:g}: {len(xs)} câu, trung vị {statistics.median(xs):.2f}")
    if a.write:
        write_table(a.write, rows)
    if a.samples:
        write_samples(a.samples, rows)
    print(f"Công thức hiện tại (âm tiết ÷ tốc độ giọng + {dialogue.BREATH:g} s): lệch trung bình {statistics.mean(errors):+.2f} s · "
          f"{short}/{len(rows)} câu bị ước tính THIẾU > 0,5 s")


def _q(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def write_table(path: str, rows) -> None:
    """{basis: "speech_s", voices: {voice_id: {n, p10, p25, p50}}} theo GIÂY NÓI (đã cắt lặng đầu/cuối) — dialogue.voice_rate dùng p50
    (sàn 0,8 × RATE) khi n ≥ min_n; phần lặng là BREATH của needed_seconds (không đếm hai lần). speed_follows / ghi chú cũ được giữ."""
    import datetime
    old = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = json.load(f)
    voices = {}
    for r in rows:
        if r["voice_id"] is not None:
            voices.setdefault(str(r["voice_id"]), []).append(r["syllables"] / r["speech_s"])
    out = {**old, "measured": datetime.date.today().isoformat(), "min_n": old.get("min_n", 8), "basis": "speech_s",
           "voices": {v: {"n": len(xs), "p10": round(_q(xs, 0.1), 2), "p25": round(_q(xs, 0.25), 2), "p50": round(_q(xs, 0.5), 2)}
                      for v, xs in sorted(voices.items())}}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"Đã ghi {path} ({len(voices)} giọng)")


def write_samples(path: str, rows) -> None:
    """Mẫu đo cho test sai số theo giọng (tests/test_speech_time.py): chỉ số, không chữ thoại / đường dẫn máy."""
    keep = [{"voice_id": None if r["voice_id"] is None else str(r["voice_id"]), "syllables": r["syllables"],
             "file_s": round(r["file_s"], 3), "speech_s": round(r["speech_s"], 3)} for r in rows]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(keep, f, ensure_ascii=False, indent=0)
    print(f"Đã ghi {path} ({len(keep)} mẫu)")


if __name__ == "__main__":
    main()
