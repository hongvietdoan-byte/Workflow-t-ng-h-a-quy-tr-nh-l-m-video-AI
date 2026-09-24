"""Bàn đo Director (H4): chấm câu trả lời Director bằng code — không gọi Claude, không tốn tiền.

    py tools/director_report.py --json tests/fixtures/director_anh_chon_ai_run4.json --script samples/anh_chon_ai.txt
    py tools/director_report.py --project 6            # câu trả lời Director cuối (projects.director_raw) + kịch bản của dự án
    thêm --normalize để chấm cả bản sau bộ chuẩn hóa shot (core/shot_normalize.py)
"""
import argparse
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import director_report  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", help="file JSON câu trả lời Director")
    ap.add_argument("--script", help="file kịch bản (chữ)")
    ap.add_argument("--project", type=int, help="đọc director_raw + script_text của dự án (CSDL chỉ đọc)")
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--model", default="kling", help="model video để tính giây trả tiền (data/video_models.json)")
    ap.add_argument("--normalize", action="store_true", help="chấm thêm bản sau bộ chuẩn hóa shot")
    a = ap.parse_args(argv)
    if a.project:
        conn = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
        raw, script = conn.execute("SELECT director_raw, script_text FROM projects WHERE id=?", (a.project,)).fetchone()
        obj = json.loads(raw)
    elif a.json and a.script:
        with open(a.json, encoding="utf-8") as f:
            obj = json.load(f)
        with open(a.script, encoding="utf-8") as f:
            script = f.read()
    else:
        ap.error("cần --project hoặc --json + --script")
    if obj.get("truncated"):
        print("Câu trả lời Director bị cắt (không chấm được):", obj.get("error"))
        return 1
    print(director_report.text(director_report.report(obj, script, a.model)))
    if a.normalize:
        from core import shot_normalize
        fixed, changes = shot_normalize.normalize(obj, script)
        print(f"\n--- Sau bộ chuẩn hóa ({len(changes)} thay đổi) ---")
        for c in changes:
            print("  •", c)
        print(director_report.text(director_report.report(fixed, script, a.model)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
