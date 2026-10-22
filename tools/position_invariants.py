"""Báo cáo bất biến R1 (vị trí xuyên shot theo bản đồ cảnh) cho một dự án — C-3D-GOC-B. 0 USD, CHỈ ĐỌC.

    PYTHONUTF8=1 py tools/position_invariants.py --project 31 [--db data/manifest.sqlite] [--data data/projects] [--json out.json]

Đọc BẢN SAO CSDL (sqlite backup vào thư mục tạm) + bản đồ cảnh `<data>/<pid>/world/scene_<cảnh>.json` (không dựng / không ghi map).
Cờ đọc theo cài đặt thật của máy (stage_camera quyết máy 3D có được dùng). Cách kiểm: core/position_invariants.py.
Mã thoát: 0 = không có phát hiện VÀNG; 1 = có VÀNG (báo, không chặn gì); 2 = không đọc được CSDL.
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import position_invariants as pi  # noqa: E402
from core.db import connect  # noqa: E402

ICON = {"vang": "🟡", "khong_ro": "⚪"}


def _utf8_console() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def report_text(res: dict, title: str) -> str:
    lines = [f"# Bất biến R1 — vị trí xuyên shot theo bản đồ cảnh · {title}", "",
             f"**{res['n']} phát hiện VÀNG** (không chặn gì; KHÔNG RÕ = thiếu map / toạ độ, có lý do).", ""]
    for sc, items in sorted(res["scenes"].items(), key=lambda kv: (len(kv[0]), kv[0])):
        lines.append(f"## Cảnh {sc}")
        if not items:
            lines += ["- ✅ không phát hiện", ""]
            continue
        for f in items:
            lines.append(f"- {ICON.get(f['level'], '·')} `{f['code']}` {f['msg']}" + (f" → {f['fix']}" if f.get("fix") else ""))
        lines.append("")
    return "\n".join(lines)


def run(db: str, pid: int, data_dir: str) -> dict:
    tmp = tempfile.mkdtemp(prefix="pos_inv_")
    try:
        copy = os.path.join(tmp, "manifest.sqlite")
        src = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        dst = sqlite3.connect(copy)
        src.backup(dst)
        src.close()
        dst.close()
        conn = connect(copy)
        try:
            row = conn.execute("SELECT name FROM projects WHERE id=?", (pid,)).fetchone()
            if row is None:
                raise SystemExit(f"không có dự án #{pid} trong {db}")
            res = pi.project_report(conn, pid, data_dir)
            res["title"] = f"#{pid} {row['name']}"
        finally:
            conn.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return res


def main(argv=None) -> int:
    _utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join(ROOT, "data", "manifest.sqlite")))
    ap.add_argument("--data", default=os.environ.get("PIPELINE_DATA", os.path.join(ROOT, "data", "projects")))
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)
    if not os.path.exists(a.db):
        print(f"không thấy CSDL {a.db}")
        return 2
    res = run(a.db, a.project, a.data)
    print(report_text(res, res["title"]))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
    return 1 if res["n"] else 0


if __name__ == "__main__":
    sys.exit(main())
