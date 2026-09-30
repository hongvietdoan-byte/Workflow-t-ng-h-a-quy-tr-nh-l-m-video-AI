"""S4.11 / S4.12 — dò API 0 USD (chỉ đọc): user-info (tổng USD đã dùng của tài khoản) + các trường nháp / sửa trong video-list.

    cd D:/AI-Video-Pipeline && py "<worktree>/tools/experiments/s411_s412_probe.py" [task_id ...]

Không in token. Không gửi job nào."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

KEYS = ("id", "task_id", "cost", "final_video_id", "generation_method", "display_task_type", "extra_data", "task_status", "task_status_msg", "model_name", "is_draft", "draft_expired_at", "draft_video_id", "draft_video",
        "draft_request_params", "seedance_cost_usd", "duration", "resolution", "created_at", "video_url")


def main():
    from tools.experiments.group_test import load_env
    load_env(os.getcwd())
    from core.adapters.clipai import ClipAIVideoProvider, PATH_LIST
    p = ClipAIVideoProvider.from_env()
    from core.providers import ProviderError
    try:
        info = p.client.get("/api/kling/user-info")
        keep = {k: v for k, v in (info or {}).items() if "usage" in k or k in ("user_id",)}
        print("user-info:", json.dumps(keep, ensure_ascii=False))
    except ProviderError as e:              # 2026-10-01: token API → LoginErr (chỉ web)
        print("user-info không đọc được bằng token API:", e)
    want = set(sys.argv[1:])
    rows = (p.client.get(PATH_LIST, {"page": 1, "pageSize": 50, "task_type": 8, "order_by_desc": 1}) or {}).get("data") or []
    for t in rows[: (50 if want else 3)]:
        if want and str(t.get("task_id")) not in want and str(t.get("id")) not in want:
            continue
        rp = t.get("request_params")
        if isinstance(rp, str):
            try:
                rp = json.loads(rp)
            except ValueError:
                pass
        row = {k: t.get(k) for k in KEYS if k in t}
        if isinstance(rp, dict):
            row["request_params"] = {k: (v if k != "content" else [{kk: vv for kk, vv in c.items() if kk != "text"} for c in v])
                                     for k, v in rp.items()}
        print(json.dumps(row, ensure_ascii=False)[:1500])
    if not want and rows:
        print("mọi khóa của 1 dòng:", sorted(rows[0].keys()))


if __name__ == "__main__":
    main()
