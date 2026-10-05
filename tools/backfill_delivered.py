"""S14.30 — chuyển đổi dự án CŨ sang định nghĩa mới "hoàn thiện" = đã XUẤT BẢN GIAO (core/delivered.py). Chạy MỘT lần (idempotent: chạy lại
không ghi thêm), 0 USD, chỉ đọc/ghi CSDL.

Ghi tín hiệu "đã giao" cho dự án có bằng chứng (mạnh trước): (1) thư mục giao <gốc>/<ngày>_du-an-<id> có video; (2) dòng outputs 'final' có
'final_qc' (chỉ delivery.deliver ghi, ở cuối chuỗi); (3) chạy tự động đã DONE và có bản cuối. Dự án chỉ có bản ghép → KHÔNG còn tính là xong
(liệt kê, báo số lượng). Khi ghi thật: tóm tắt vào diag mã 'delivered_backfill'.

  py tools/backfill_delivered.py [--db PATH] [--data DIR] [--output-root DIR]            chạy thử: chỉ in SẼ ghi gì (mặc định)
  py tools/backfill_delivered.py [--db PATH] [--data DIR] [--output-root DIR] --apply    ghi thật (sao lưu CSDL trước!)

Mặc định --db = PIPELINE_DB hoặc data/manifest.sqlite; --data = PIPELINE_DATA hoặc data/projects; --output-root = DELIVERY_OUTPUT_ROOT
hoặc D:\\AI-Video-Output. Sao lưu: cp data/manifest.sqlite data/backup/manifest.before_s14_30_<ngày>.sqlite
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import delivered  # noqa: E402
from core.db import connect  # noqa: E402


def main(argv=None) -> str:
    ap = argparse.ArgumentParser(description="S14.30: ghi tín hiệu 'đã xuất bản giao' cho dự án cũ (0 USD)")
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--data", default=os.environ.get("PIPELINE_DATA", os.path.join("data", "projects")))
    ap.add_argument("--output-root", default=os.environ.get("DELIVERY_OUTPUT_ROOT", delivered.DEFAULT_OUTPUT_ROOT))
    ap.add_argument("--apply", action="store_true", help="ghi thật (mặc định chỉ chạy thử)")
    a = ap.parse_args(argv)
    if not os.path.exists(a.db):
        raise SystemExit(f"Không thấy CSDL {a.db}")
    conn = connect(a.db)
    try:
        res = delivered.backfill(conn, a.data, a.output_root, apply=a.apply)
    finally:
        conn.close()
    print(res["summary"])
    for m in res["marked"]:
        print(f"  + #{m['project_id']} ← {m['source']}: {m['path']}")
    for pid in res["rendered_only"]:
        print(f"  - #{pid}: có bản cuối, chưa xuất bản giao → không còn tính là xong")
    if not a.apply:
        print("(chạy thử — thêm --apply để ghi)")
    return json.dumps(res, ensure_ascii=False)


if __name__ == "__main__":
    main()
