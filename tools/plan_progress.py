"""In / ghi lại bảng tiến độ của kế hoạch đang chạy (docs/KE_HOACH_SUA_SAU_DU_AN_8.md). Miễn phí, không gọi API.

  py tools/plan_progress.py           in bảng tiến độ
  py tools/plan_progress.py --write   ghi bảng vào file kế hoạch (giữa <!-- tien-do --> … <!-- /tien-do -->)
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from devsys import plan_progress  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Tiến độ kế hoạch đang chạy (% do code tính)")
    ap.add_argument("--file", default=plan_progress.PLAN_FILE)
    ap.add_argument("--write", action="store_true", help="ghi bảng tiến độ vào file kế hoạch")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    plan = plan_progress.load(a.file)
    if plan is None:
        print(f"Không thấy {a.file}")
        return 1
    if plan["bad"]:
        print("Dòng việc không đọc được:\n" + "\n".join(plan["bad"]))
        return 1
    if a.write:
        print("Đã ghi bảng tiến độ." if plan_progress.write_table(a.file) else "Bảng tiến độ đã đúng, không đổi.")
    print(plan_progress.table(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
