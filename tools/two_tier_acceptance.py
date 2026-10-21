"""V3.1 M7.4 (F-Q4): nghiệm thu cờ two_tier_quality trên MỘT dự án thật — 0 USD, chỉ đọc CSDL (mode=ro).

  1. TRƯỚC khi gen bản cao:  py tools/two_tier_acceptance.py --project 34 --snapshot      (ghi dự toán <data>/<pid>/two_tier_estimate.json)
  2. Sau khi bản cao xong + đối soát ClipAI:  py tools/clipai_cost_reconcile.py --json > rec.json
                              py tools/two_tier_acceptance.py --project 34 --reconcile rec.json
Đạt khi chi thực (mọi job bậc final, kể cả gen lại) lệch dự toán ≤ ±5 % VÀ ≥ 80 % cảnh duyệt bản cao ngay lần đầu, không cảnh nào gen lại
bản cao quá 1 lần. Thiếu số (giá / tiền thật) → KHÔNG RÕ, mã thoát 2. Không đạt → mã thoát 1."""
import argparse
import datetime
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _ro(db: str):
    conn = sqlite3.connect("file:" + os.path.abspath(db).replace("\\", "/") + "?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def snapshot_path(data_dir: str, pid: int) -> str:
    return os.path.join(data_dir, str(pid), "two_tier_estimate.json")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join(ROOT, "data", "manifest.sqlite")))
    ap.add_argument("--data-dir", default=os.environ.get("PIPELINE_DATA", os.path.join(ROOT, "data", "projects")))
    ap.add_argument("--snapshot", action="store_true", help="chụp dự toán bản cao còn phải gen (trước khi gen)")
    ap.add_argument("--reconcile", help="JSON của tools/clipai_cost_reconcile.py --json (tiền thật từng task)")
    a = ap.parse_args(argv)
    from core import quality_tier
    conn = _ro(a.db)
    try:
        if a.snapshot:
            est = quality_tier.final_estimate(conn, a.project)
            path = snapshot_path(a.data_dir, a.project)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(dict(est, at=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")), f, ensure_ascii=False,
                          indent=1)
            print(f"Dự toán bản cao #{a.project}: {est['usd']:.2f} USD · {len(est['scenes'])} cảnh · thiếu giá {len(est['unknown'])} → {path}")
            return 0
        if not a.reconcile:
            ap.error("cần --snapshot hoặc --reconcile")
        with open(snapshot_path(a.data_dir, a.project), encoding="utf-8") as f:
            est = json.load(f)
        with open(a.reconcile, encoding="utf-8") as f:
            rec = json.load(f)
        rows = [r for r in (rec.get("tasks") or rec.get("rows") or []) if r.get("project_id") == a.project]   # reconcile() → "tasks"
        jobs = [dict(r) for r in conn.execute("SELECT id, scene_id, state FROM jobs WHERE project_id=? AND type='video_gen' "
                                              "AND quality_tier='final'", (a.project,))]
    finally:
        conn.close()
    res = quality_tier.acceptance(est, rows, jobs)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if res["cost_ok"] is None or res["quality_ok"] is None:
        return 2
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
