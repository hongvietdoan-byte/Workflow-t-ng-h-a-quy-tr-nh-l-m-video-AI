"""Kiểm dây nối bố cục giữa các shot cùng chỗ đứng — chạy TRƯỚC khi bấm Gen ảnh (người dùng 14/10, tập 2). 0 USD, chỉ đọc.

    py tools/scene_layout_audit.py --project 31            in bảng + lưu data/projects/<id>/layout_audit.md
    py tools/scene_layout_audit.py --project 31 --db data/manifest.sqlite

Đọc trên BẢN SAO của CSDL (sqlite backup vào thư mục tạm) — không ghi gì vào CSDL thật. Cờ đọc theo cài đặt thật của máy
(data/feature_settings.json), nên bảng nói đúng cái Dashboard sẽ gửi. Cách đọc: core/layout_audit.py.
"""
import argparse
import os
import shutil
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import layout_audit  # noqa: E402
from core.db import connect  # noqa: E402


def _utf8_console() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def run(db: str, pid: int, data_dir: str, out: str = "") -> str:
    tmp = tempfile.mkdtemp(prefix="layout_audit_")
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
            text = layout_audit.report(layout_audit.audit(conn, pid, data_dir), f"#{pid} {row['name']}")
        finally:
            conn.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if out:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
    return text


def main(argv=None) -> int:
    _utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join(ROOT, "data", "manifest.sqlite")))
    ap.add_argument("--data", default=os.environ.get("PIPELINE_DATA", os.path.join(ROOT, "data", "projects")))
    ap.add_argument("--out", default="", help="tệp .md (mặc định data/projects/<id>/layout_audit.md)")
    a = ap.parse_args(argv)
    if not os.path.exists(a.db):
        print(f"không thấy CSDL {a.db}")
        return 2
    out = a.out or os.path.join(a.data, str(a.project), "layout_audit.md")
    text = run(a.db, a.project, a.data, out)
    print(text)
    print(f"(đã lưu: {out})")
    return 1 if "🔴" in text.split("| Mức |", 1)[-1] else 0


if __name__ == "__main__":
    sys.exit(main())
