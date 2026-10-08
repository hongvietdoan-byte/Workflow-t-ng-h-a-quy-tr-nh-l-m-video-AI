"""Mục 6 (sau Khủng Long Đỏ): so số token ClipAI THẬT tính cho từng clip Seedance đã gen với công thức `cost.seedance_tokens` —
CHỈ ĐỌC (GET danh sách task, 0 USD). Ra bảng theo (model, độ phân giải, có video tham chiếu): tỉ lệ thật / công thức.

    py tools/clipai_price_check.py <manifest.sqlite> [project_id ...]
"""
import json
import os
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import cost  # noqa: E402
from core.adapters.clipai import DEEP_PAGES, ClipAIVideoProvider  # noqa: E402


def main(db: str, pids) -> None:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    q = ("SELECT j.id, j.project_id, j.external_id, p.aspect FROM jobs j JOIN projects p ON p.id=j.project_id "
         "WHERE j.type='video_gen' AND j.external_id LIKE 'seedance:%'")
    rows = c.execute(q + (f" AND j.project_id IN ({','.join('?' * len(pids))})" if pids else ""), tuple(pids)).fetchall()
    prov = ClipAIVideoProvider.from_env()
    groups = defaultdict(list)
    for r in rows:
        try:
            u = prov.task_usage(r["external_id"])
        except Exception as e:  # noqa: BLE001 - one bad row does not stop the check
            print(f"job {r['id']}: không đọc được ({e})")
            continue
        if not u or not u.get("tokens"):
            continue
        task, _ = prov._find_ex(r["external_id"], pages=DEEP_PAGES)
        model = (task or {}).get("model_name") or "?"
        res = u.get("resolution") or "?"
        ratio = (r["aspect"] or "9:16")
        dur = float(u.get("duration") or 0)
        formula = cost.seedance_tokens(res, ratio, dur) if not u["has_video_input"] else None
        groups[(model, res, u["has_video_input"])].append((r["id"], dur, u["tokens"], formula, u["usd"]))
    print("| Model | Độ phân giải | Có video ref | Số clip | Token thật / công thức (không video ref) | USD thật theo bảng token |")
    print("|---|---|---|---|---|---|")
    for (model, res, vid), items in sorted(groups.items()):
        ratios = [t / f for _, _, t, f, _ in items if f]
        r_txt = f"{min(ratios):.2f}–{max(ratios):.2f}" if ratios else "—"
        usd = sum(u or 0 for *_, u in items)
        print(f"| {model} | {res} | {'có' if vid else 'không'} | {len(items)} | {r_txt} | {usd:.2f} |")
    print(json.dumps({f"{k[0]}|{k[1]}|{k[2]}": [(i, d, t, f) for i, d, t, f, _ in v] for k, v in groups.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], [int(x) for x in sys.argv[2:]])
