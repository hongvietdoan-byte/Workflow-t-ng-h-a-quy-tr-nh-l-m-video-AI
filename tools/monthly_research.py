"""Monthly research from the command line (for the Windows Task Scheduler): py tools/monthly_research.py [--force]

Does the same as the dashboard's monthly round: only when "Tự nghiên cứu hàng tháng" is switched on and due (or --force);
needs ANTHROPIC_API_KEY. Findings become PROPOSED lessons; a person approves them in the dashboard tab "🎓 Bài học".
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import llm_runner, research  # noqa: E402
from core.db import connect  # noqa: E402

DB = os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite"))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    conn = connect(DB)
    force = "--force" in sys.argv
    if not force and not (research.enabled(conn) and research.due(conn)):
        print("Chưa đến hạn hoặc chưa bật 'Tự nghiên cứu hàng tháng'. Dùng --force để chạy ngay.")
        return
    client = llm_runner.client_from_env()
    if client is None:
        print("Thiếu ANTHROPIC_API_KEY: không nghiên cứu được.")
        return
    result = research.run(conn, client)
    print(f"Xong: {result['proposed']} đề xuất mới từ {result['topics']} chủ đề; lỗi: {result['errors'] or 'không'}")


if __name__ == "__main__":
    main()
