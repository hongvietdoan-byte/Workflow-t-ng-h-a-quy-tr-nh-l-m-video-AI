"""Monthly research from the command line (for the Windows Task Scheduler): py tools/monthly_research.py --max-usd 1.0 [--force]

Does the same as the dashboard's monthly round: only when "Tự nghiên cứu hàng tháng" is switched on and due (or --force);
needs ANTHROPIC_API_KEY. Findings become PROPOSED lessons; a person approves them in the dashboard tab "🎓 Bài học".
S14.2: --max-usd is REQUIRED (hard lock of this run, core/script_cap.py) — nobody sees a warning on a scheduled run.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import llm_runner, research, script_cap  # noqa: E402
from core.db import connect  # noqa: E402

DB = os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite"))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true")
    script_cap.add_argument(ap)
    a = ap.parse_args()
    cap = script_cap.require(a, "nghiên cứu hàng tháng")      # refuse before reading anything when the lock is missing
    conn = connect(DB)
    force = a.force
    if not force and not (research.enabled(conn) and research.due(conn)):
        print("Chưa đến hạn hoặc chưa bật 'Tự nghiên cứu hàng tháng'. Dùng --force để chạy ngay.")
        return
    client = llm_runner.client_from_env(ledger=llm_runner.db_file(conn))
    if client is None:
        print("Thiếu ANTHROPIC_API_KEY: không nghiên cứu được.")
        return
    with cap:
        result = research.run(conn, client)
        print(f"Xong: {result['proposed']} đề xuất mới từ {result['topics']} chủ đề; lỗi: {result['errors'] or 'không'}")
        return
    print("Dừng vì chạm trần --max-usd: các đề xuất đã có được giữ (xem 🎓 Bài học).")


if __name__ == "__main__":
    main()
