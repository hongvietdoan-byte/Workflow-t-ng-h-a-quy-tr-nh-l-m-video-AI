"""Ghi MỐC NỀN hiệu quả workflow (S14.19, KE_HOACH_BO_NAO_PROMPT_TU_HOC Đợt 1) — 0 USD, không gọi API, chỉ đọc CSDL và ghi vào
bảng effectiveness_snapshots: 1 mốc toàn hệ (project_id trống) + 1 mốc cho mỗi dự án đã xong, trigger 'manual'. "Đã xong" = có bản giao
'final' trong bảng outputs HOẶC file kiểu cũ <data>/<id>/output/FINAL_VIDEO.mp4; --project N (lặp được) thêm dự án N vào danh sách.

  py tools/effectiveness_baseline.py [--db PATH] [--data DIR] [--project N]          chỉ in ra SẼ ghi gì (không ghi)
  py tools/effectiveness_baseline.py [--db PATH] [--data DIR] [--project N] --yes    ghi thật

Mặc định --db = biến PIPELINE_DB hoặc data/manifest.sqlite; --data = PIPELINE_DATA hoặc data/projects (của thư mục chạy);
--env = dashboard.env ở gốc repo (để đọc đúng cờ đang bật). Chạy 2 lần trong cùng một phút vẫn chỉ 1 mốc mỗi dự án.
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
    ap.add_argument("--data", default=os.environ.get("PIPELINE_DATA") or os.path.join("data", "projects"),
                    help="thư mục dự án (tìm FINAL_VIDEO.mp4 kiểu cũ)")
    ap.add_argument("--project", type=int, action="append", default=[], help="thêm dự án N vào danh sách (lặp được)")
    ap.add_argument("--yes", action="store_true", help="ghi thật (không có thì chỉ in ra sẽ ghi gì)")
    ap.add_argument("--env", default=os.path.join(ROOT, "dashboard.env"),
                    help="file cài đặt Dashboard để đọc đúng cờ đang bật (mặc định dashboard.env ở gốc repo)")
    a = ap.parse_args(argv)
    from core.adapters.check import load_dashboard_env
    load_dashboard_env(a.env)              # the FEATURE_* switches the Dashboard runs with (without it: only the verified flags)
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
        names = {r[0]: r[1] for r in conn.execute("SELECT id, name FROM projects").fetchall()}
        unknown = [n for n in a.project if n not in names]
        if unknown:
            print(f"✖ Không có dự án: {', '.join(f'#{n}' for n in unknown)}")
            return 2
        done = sorted(set(effectiveness.finished_projects(conn, a.data)) | set(a.project))
        print(f"CSDL: {os.path.abspath(a.db)}")
        print(f"Cờ đang bật ({len(effectiveness.flags_on())}): {', '.join(effectiveness.flags_on()) or '—'}")
        print(f"Kiến thức: {effectiveness.knowledge_fp()}")
        print(f"Sẽ ghi {1 + len(done)} mốc (trigger 'manual'): 1 toàn hệ + {len(done)} dự án ({len(a.project)} thêm bằng --project):")
        print("  - toàn hệ (gộp các dự án trên)")
        for pid in done:
            print(f"  - #{pid} {names.get(pid, '?')}")
        if not a.yes:
            print("Chưa ghi gì. Thêm --yes để ghi thật (0 USD).")
            return 0
        sid = effectiveness.snapshot(conn, None, pricing, "manual", system_projects=done)
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
