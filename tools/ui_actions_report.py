"""Đọc nhật ký thao tác Dashboard (bảng ui_actions, core/ui_log.py) — CHỈ ĐỌC, in tóm tắt tiếng Việt theo dự án / nguồn.

    py tools/ui_actions_report.py                    # mọi dự án, mọi nguồn
    py tools/ui_actions_report.py --project 27 --source claude --hours 24
    py tools/ui_actions_report.py --db D:/khac/manifest.sqlite

Mở CSDL ở chế độ chỉ đọc (mode=ro); không tạo bảng, không ghi gì. CSDL cũ chưa có bảng → báo "chưa có dữ liệu".
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from core import ui_log  # noqa: E402

SOURCE_NAME = {"nguoi": "người", "claude": "Claude"}


def open_ro(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{os.path.abspath(path)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def report(conn, project_id=None, source=None, hours=None) -> str:
    since = time.time() - hours * 3600 if hours else None
    s = ui_log.summary(conn, project_id=project_id, since=since, source=source)
    scope = (f"dự án #{project_id}" if project_id is not None else "mọi dự án") + \
            (f" · nguồn {SOURCE_NAME.get(ui_log.norm_source(source))}" if source else "") + \
            (f" · {hours:g} giờ qua" if hours else "")
    if not s["total"]:
        return f"Nhật ký thao tác ({scope}): chưa có dữ liệu."
    out = [f"Nhật ký thao tác ({scope}): {s['total']} thao tác — "
           + ", ".join(f"{SOURCE_NAME.get(k, k)} {v}" for k, v in sorted(s["by_source"].items()))
           + f" · lỗi {s['errors']} · không tác dụng {s['noops']}"]
    out.append("Theo nút (kết quả · nguồn · số lần · thời gian xử lý TB):")
    for c in s["counts"]:
        ms = s["avg_ms"].get(c["action"])
        out.append(f"  - {c['action']}: {c['result']} · {SOURCE_NAME.get(c['source'], c['source'])} · {c['n']}"
                   + (f" · ~{ms} ms" if ms is not None else ""))
    out.append(f"Đổi ý: {len(s['flips'])}")
    for f in s["flips"][:30]:
        out.append(f"  - {f['kind']} · dự án #{f['project_id']} · job {f['job_id']} · sau {f['seconds']} s · "
                   f"{SOURCE_NAME.get(f['source'], f['source'])}")
    out.append(f"Bấm đôi / bấm hụt (lần 1 không tác dụng): {len(s['doubles'])}")
    for d in s["doubles"][:30]:
        out.append(f"  - {d['action']} · dự án #{d['project_id']} · sau {d['seconds']} s · {SOURCE_NAME.get(d['source'], d['source'])}")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Tóm tắt nhật ký thao tác Dashboard (chỉ đọc)")
    ap.add_argument("--db", default=os.path.join(ROOT, "data", "manifest.sqlite"))
    ap.add_argument("--project", type=int)
    ap.add_argument("--source", choices=ui_log.SOURCES)
    ap.add_argument("--hours", type=float)
    a = ap.parse_args(argv)
    if not os.path.exists(a.db):
        print(f"Không thấy CSDL: {a.db}")
        return 1
    print(report(open_ro(a.db), a.project, a.source, a.hours))
    return 0


if __name__ == "__main__":
    sys.exit(main())
