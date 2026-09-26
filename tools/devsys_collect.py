"""Bộ gom số đo miễn phí của AI Development System (không AI, không tiền).

    py tools/devsys_collect.py            gom số đo → devsys/data/snapshot.json (git, TODO.md, cờ, diag, bản đồ khu vực)
    py tools/devsys_collect.py --tests    chạy thêm toàn bộ test (pytest --junitxml, ~4 phút) → devsys/data/runs/<giờ>.json
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from devsys import collect  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Gom số đo miễn phí của AI Development System")
    ap.add_argument("--tests", action="store_true", help="chạy toàn bộ test (pytest --junitxml) và lưu kết quả")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    if args.tests:
        if collect.tests_running(ROOT):
            print("Đang có một lần chạy test khác — bỏ qua.")
            return 1
        run = collect.run_tests(ROOT)
        t = run.get("totals") or {}
        print(f"Test: {t.get('tests')} test, {t.get('failed')} lỗi, {t.get('errors')} lỗi chạy, {t.get('skipped')} bỏ qua "
              f"({run['duration_s']} s, mã thoát {run['returncode']})")
        collect.append_event("tests", ROOT, totals=t, duration_s=run["duration_s"], commit=run.get("short"))
    snap = collect.collect(ROOT)
    path = collect.save_snapshot(snap, ROOT)
    if not args.quiet:
        cov = snap["coverage"]
        print(f"Ảnh chụp → {os.path.relpath(path, ROOT)} ({snap['collect_s']} s): {len(cov['files'])} file code, "
              f"{len(cov['unmapped'])} chưa thuộc khu vực nào, {len(snap['todo'])} dòng TODO còn mở, {len(snap['working'])} file đang sửa.")
        for f in cov["unmapped"]:
            print(f"  ⚠ chưa thuộc khu vực nào: {f} (thêm vào devsys/areas.json)")
    return 0


if __name__ == "__main__":
    os.chdir(ROOT)
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")   # the web redirects the output to a log file
        except (AttributeError, ValueError):
            pass
    sys.exit(main())
