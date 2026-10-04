r"""Đo Tổ QC (GĐ2: chuyên viên C1 Nhân vật) trên bộ đo vàng — docs/THIET_KE_TO_QC_2026-10-01.md mục 15, 18.

    py tools/experiments/qc_team_eval.py --set dev                                    kế hoạch (0 USD): số khung, ước tính
    py tools/experiments/qc_team_eval.py --set dev --replay <calls.jsonl>              chạy lại offline từ bản ghi (0 USD)
    py tools/experiments/qc_team_eval.py --set dev --yes --max-usd 0.5 --bill-project new   chạy thật (Claude), ghi calls.jsonl

--set dev = #8 lượt 1 (bộ phát triển); --set independent = nhãn người dùng từ Google Sheet (data/qc_golden/independent.json).
--category: chỉ tính recall trên khung chặn có loại lỗi này (mặc định "Nhân vật" — C1 không chấm hướng nhìn / ánh sáng).
Kết quả: data/qc_golden/runs/<giờ>/result.json + calls.jsonl. Tiền tính vào dự án riêng 'Nghiệm thu agent QC' (--bill-project new).
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "experiments"))
EVAL_PROJECT = "Nghiệm thu agent QC"


from core import script_cap  # noqa: E402  (S14.2: trần cứng --max-usd)


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=("dev", "independent"), default="dev")
    ap.add_argument("--category", default="Nhân vật")
    ap.add_argument("--limit", type=int, default=0, help="chỉ N khung đầu (thử nhỏ)")
    ap.add_argument("--db", default=os.path.join("data", "manifest.sqlite"))
    ap.add_argument("--yes", action="store_true")
    script_cap.add_argument(ap)          # S14.2: trần CỨNG cả lần chạy, bắt buộc khi --yes
    ap.add_argument("--bill-project", default="new")
    ap.add_argument("--replay", default=None)
    a = ap.parse_args(argv)
    hard = script_cap.from_args(argparse.Namespace(yes=a.yes and not a.replay, max_usd=a.max_usd), "đo Tổ QC")
    from core import qc_golden, qc_team
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect(a.db))
    data_dir = os.path.join(os.path.dirname(os.path.abspath(a.db)), "projects")
    items = qc_golden.dev_set() if a.set == "dev" else qc_golden.independent_set()
    if a.limit:
        items = items[:a.limit]
    frames = []
    for it in items:
        row = p.conn.execute("SELECT s.data FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.id=?", (it["job"],)).fetchone()
        path = qc_golden.picture(data_dir, it["project"], it["job"])
        if row is None or path is None:
            print(f"bỏ job {it['job']}: thiếu {'ảnh' if row else 'shot'}")
            continue
        frames.append({"job_id": it["job"], "project": it["project"], "path": path, "data": json.loads(row["data"] or "{}"),
                       "label": it.get("shot")})
    usd = qc_team.estimate_usd(len(frames))
    print(f"bộ {a.set}: {len(items)} khung có nhãn, {len(frames)} chạy được · ước tính C1 ≈ ${usd:.2f} (chưa đo, mục 16)")
    if not a.yes and not a.replay:
        print("(chưa chạy — thêm --yes để chạy thật, hoặc --replay <calls.jsonl> để chạy lại 0 USD)")
        return
    run_dir = os.path.join(os.path.dirname(os.path.abspath(a.db)), "qc_golden", "runs", time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)
    from core import llm_runner, project_budget
    if a.replay:
        client = qc_team.ReplayClient(a.replay)
        bill = None
    else:
        from group_test import load_env
        load_env(".")
        real = llm_runner.client_from_env(ledger=a.db)
        if real is None or not hasattr(real, "ask_json"):
            raise SystemExit("cần Claude API (LLM_PROVIDER=anthropic)")
        client = qc_team.RecordingClient(real, os.path.join(run_dir, "calls.jsonl"))
        if a.bill_project == "new":
            row = p.conn.execute("SELECT id FROM projects WHERE name=?", (EVAL_PROJECT,)).fetchone()
            bill = row["id"] if row else p.create_project(EVAL_PROJECT, created_by="qc_team_eval", game="FF", aspect="9:16")
        else:
            bill = int(a.bill_project)
        over = project_budget.check(p.conn, bill, "claude_qc", usd)
        if over:
            raise SystemExit(f"dừng trước khi chạy: {over}")
        print(f"tiền tính vào dự án #{bill}; trần cứng ${a.max_usd:.2f}")
        hard.start()
    results, errors = {}, []
    entities = {}
    with llm_runner.tagged("qc_team", bill), llm_runner.spend_cap(a.max_usd or float("inf"), "đo Tổ QC") as cap:
        for f in frames:
            if not hard.allow(qc_team.estimate_usd(1), f"khung job {f['job_id']}"):
                break
            d = f["data"]
            scene_key = (f["project"], d.get("story_scene"))
            if scene_key not in entities:                       # one cached entity block per scene: same people, all its frames excluded
                same = [g for g in frames if (g["project"], g["data"].get("story_scene")) == scene_key]
                names = sorted({str(c).upper() for g in same for c in g["data"].get("characters") or []})
                from core import qc_spec
                views = sorted({qc_spec.view_of(g["data"], n) or "" for g in same for n in g["data"].get("characters") or []} - {""})
                entities[scene_key] = qc_team.entity_blocks(p, f["project"], names, views, [g["job_id"] for g in same], data_dir,
                                                            [f"S{g['data'].get('story_scene')}·{g['data'].get('shot_no')}" for g in same])
            try:
                res = qc_team.review_frame(p, f["project"], data_dir, f, client, entity=entities[scene_key])
            except script_cap.CapReached as e:      # chạm --max-usd giữa khung: giữ kết quả các khung đã xong
                errors.append({"job": f["job_id"], "error": str(e), "code": "script_cap"})
                break
            except llm_runner.LlmError as e:
                errors.append({"job": f["job_id"], "error": str(e), "code": e.code})
                print(f"job {f['job_id']}: lỗi {e.code}: {e}")
                if e.code in ("budget", "auth", "config"):
                    break
                continue
            results[f["job_id"]] = res
            print(f"job {f['job_id']} {f.get('label')}: {res['verdict']}" + (f" · cần trọng tài {len(res['arbiter'])}" if res["arbiter"] else "")
                  + (f" · {res['problems']}" if res["problems"] else ""), flush=True)
        spent = cap["spent"]
    sc = qc_golden.score(items, results, a.category)
    sc_all = qc_golden.score(items, results, None)
    out = {"set": a.set, "category": a.category, "score": sc, "score_all_categories": sc_all, "usd": round(spent, 4),
           "errors": errors, "replay_misses": getattr(client, "misses", 0), "results": {str(k): v for k, v in results.items()}}
    json.dump(out, open(os.path.join(run_dir, "result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("score", "score_all_categories", "usd", "replay_misses")}, ensure_ascii=False, indent=1))
    print("ghi:", run_dir)


if __name__ == "__main__":
    main()
