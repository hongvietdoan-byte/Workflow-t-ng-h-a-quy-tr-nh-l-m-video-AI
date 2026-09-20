"""Print (and save) the diagnostics report from the command line: py tools/diagnose.py [hours]

Same text as the dashboard's "Báo cáo chẩn đoán": no tokens, no personal paths. Paste it into the chat.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import diag  # noqa: E402
from core.db import connect  # noqa: E402

DB = os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite"))
DATA = os.environ.get("PIPELINE_DATA", os.path.join("data", "projects"))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 24
    text = diag.report(connect(DB), DATA, hours=hours)
    out = os.path.join("data", "bao_cao_chan_doan.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"(đã lưu: {out})")


if __name__ == "__main__":
    main()
