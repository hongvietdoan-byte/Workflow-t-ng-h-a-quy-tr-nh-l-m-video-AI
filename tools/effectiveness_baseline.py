"""Ghi MỐC NỀN hiệu quả workflow (S14.19, KE_HOACH_BO_NAO_PROMPT_TU_HOC Đợt 1) — 0 USD, không gọi API, chỉ đọc CSDL và ghi vào
bảng effectiveness_snapshots: 1 mốc toàn hệ (project_id trống) + 1 mốc cho mỗi dự án đã xong (có bản giao 'final'), trigger 'manual'.

  py tools/effectiveness_baseline.py [--db PATH]          chỉ in ra SẼ ghi gì (không ghi)
  py tools/effectiveness_baseline.py [--db PATH] --yes    ghi thật

Mặc định --db = biến PIPELINE_DB hoặc data/manifest.sqlite (của thư mục chạy). Chạy 2 lần trong cùng một phút vẫn chỉ 1 mốc mỗi dự án.
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import cost, effectiveness  # noqa: E402
from core.db import connect  # noqa: E402


def _fmt(v, pct=False) -> str:
    if v is None:
        return "—"
    return f"{v:.0%}" if pct else f"{v:.2f}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Ghi mốc nền hiệu quả workflow (0 USD)")
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB") or os.path.join("data", "manifest.sqlite"))
    ap.add_argument("--yes", action="store_true", help="ghi thật (không có thì chỉ in ra sẽ ghi gì)")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    if not os.path.exists(a.db):              # connect() would create an empty database: say it instead
        print(f"✖ Không thấy CSDL: {os.path.abspath(a.db)} — truyền --db <đường dẫn manifest.sqlite>.")
        return 2
    pricing = cost.load_pricing()
    if pricing.get("_error"):
        print(f"⚠ Bảng giá lỗi ({pricing['_error']}) — chi phí/giây sẽ trống trong mốc.")
    conn = connect(a.db)
    try:
        done = effectiveness.finished_projects(conn)
        names = {r[0]: r[1] for r in conn.execute("SELECT id, name FROM projects").fetchall()}
        print(f"CSDL: {os.path.abspath(a.db)}")
        print(f"Cờ đang bật ({len(effectiveness.flags_on())}): {', '.join(effectiveness.flags_on()) or '—'}")
        print(f"Kiến thức: {effectiveness.knowledge_fp()}")
        print(f"Sẽ ghi {1 + len(done)} mốc (trigger 'manual'): 1 toàn hệ + {len(done)} dự án đã xong:")
        print("  - toàn hệ (gộp các dự án đã xong)")
        for pid in done:
            print(f"  - #{pid} {names.get(pid, '?')}")
        if not a.yes:
            print("Chưa ghi gì. Thêm --yes để ghi thật (0 USD).")
            return 0
        sid = effectiveness.snapshot(conn, None, pricing, "manual")
        print(f"✔ toàn hệ → mốc #{sid}")
        for pid in done:
            sid = effectiveness.snapshot(conn, pid, pricing, "manual")
            row = effectiveness.history(conn, pid, limit=1)[-1]
            print(f"✔ #{pid} {names.get(pid, '?')} → mốc #{sid}: đạt lần đầu ảnh {_fmt(row['image_first_pass'], True)}, "
                  f"video {_fmt(row['video_first_pass'], True)}, chi phí/giây {_fmt(row['cost_per_sec'])}, hài lòng "
                  f"{_fmt(row['satisfaction'], True)} ({row['feedback_n']} góp ý)")
        print(f"Xong: {1 + len(done)} mốc, 0 USD.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
