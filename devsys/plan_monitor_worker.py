"""CLI worker được spawn từ AI Dev System cho một lần giám sát kế hoạch."""
from __future__ import annotations

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from devsys import plan_monitor  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Giám sát kế hoạch V3.1, 0 USD API")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--provider", choices=("claude_cli", "mock"), default="claude_cli")
    parser.add_argument("--trigger-id", default="manual")
    parser.add_argument("--expected-input-hash")
    args = parser.parse_args(argv)
    for _ in range(40):
        try:
            result = plan_monitor.run_monitor(args.root, args.provider, publish_plan=plan_monitor.load_config(args.root)["publish_plan"],
                                              expected_input_hash=args.expected_input_hash,
                                              note=lambda message: print(message, flush=True))
        except plan_monitor.PlanMonitorError as error:
            print(f"Dừng an toàn: {error}", flush=True)
            return 2
        except Exception as error:
            print(f"Không hoàn tất ({type(error).__name__}); xem lỗi đã lọc.", flush=True)
            return 2
        if not result.get("busy"):
            if result.get("record"):
                record = result["record"]
                print(f"Xong giám sát {args.trigger_id}: {record['score']['label']} {record['score']['overall']}/10; "
                      f"báo cáo {result['report']}; kế hoạch={record.get('plan_write')}", flush=True)
                return 0
            print(f"Không hoàn tất: {result.get('error', 'không có kết quả')}", flush=True)
            return 2
        time.sleep(0.25)
    print("Dừng: khóa giám sát vẫn bận sau 10 giây.", flush=True)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
