r"""Nghiệm thu agent QC trong app (core/qc_agent.py) trên bộ nhãn đã được người xác nhận (docs/AGENT_QC_THIET_KE_2026-09-27.md mục 4).

Bộ nhãn #8: 33 khung storyboard LƯỢT ĐẦU (trước khi vẽ lại) + kết luận agent QC đã được người dùng xác nhận 27/09
(docs/qc_agent_2026-09-27/verdicts.json: 11 chặn, 13 nhỏ, 9 đạt). Ảnh của khung đã bị loại nằm trong thùng rác dự án.
CHỈ ĐỌC: chạy QcAgent theo cảnh, không đổi trạng thái ảnh nào. Đo: bắt được bao nhiêu khung `chặn` (verdict block/doubt), báo nhầm bao nhiêu
khung `đạt`/`nhỏ` thành block. Chuẩn cổng tin cậy: bắt 100 % khung chặn, báo nhầm ≤ 10 %.

    py tools/experiments/qc_agent_eval.py --project 8 --scenes 1             kế hoạch
    py tools/experiments/qc_agent_eval.py --project 8 --scenes 1 --yes       chạy (tốn Claude API)
Khóa cứng: --max-usd (BẮT BUỘC khi --yes, core/script_cap.py) cho CẢ lần chạy + trần mỗi cảnh của agent (qc_agent.SCENE_CAP_USD); chạm trần thì dừng, kết quả
các cảnh đã xong vẫn được ghi (28/09: lần chạy không khóa tốn ~2 USD và mất kết quả cảnh 2).
Kết quả: data/projects/<id>/qc_scene/agent_eval.json (ghi sau MỖI cảnh)
"""
import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "experiments"))
LABELS = os.path.join(ROOT, "docs", "qc_agent_2026-09-27", "verdicts.json")
EVAL_PROJECT = "Nghiệm thu agent QC"


def picture(data_dir, pid, job):
    path = os.path.join(data_dir, str(pid), "images", f"job_{job}.png")
    if os.path.exists(path):
        return path
    hits = sorted(glob.glob(os.path.join(data_dir, str(pid), "trash", "images", f"job_{job}__*.png")))
    return hits[-1] if hits else None


from core import script_cap  # noqa: E402  (S14.2: trần cứng --max-usd)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--scenes", type=int, nargs="*")
    ap.add_argument("--db", default=os.path.join("data", "manifest.sqlite"))
    ap.add_argument("--yes", action="store_true")
    script_cap.add_argument(ap)          # S14.2: trần CỨNG cả lần chạy, bắt buộc khi --yes
    ap.add_argument("--bill-project", default=None, help="dự án nhận tiền của lần nghiệm thu: số, hoặc 'new' = dự án riêng "
                                                       "'Nghiệm thu agent QC' (tạo một lần) — không tính vào dự án đã giao đang được chấm")
    a = ap.parse_args()
    hard = script_cap.from_args(a, "nghiệm thu agent QC")
    labels = json.load(open(LABELS, encoding="utf-8"))
    labels = labels if isinstance(labels, list) else labels.get("frames") or labels.get("verdicts")
    fix = os.path.join(os.path.dirname(LABELS), "labels_v2.json")       # 28/09: left/right labels judged by the frame edge, corrected
    if os.path.exists(fix):
        over = json.load(open(fix, encoding="utf-8")).get("overrides") or {}
        labels = [dict(lab, verdict=over[str(lab["job"])]["verdict"]) if str(lab["job"]) in over else lab for lab in labels]
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect(a.db))
    data_dir = os.path.join(os.path.dirname(os.path.abspath(a.db)), "projects")
    bill = a.project
    if a.bill_project == "new":
        row = p.conn.execute("SELECT id FROM projects WHERE name=?", (EVAL_PROJECT,)).fetchone()
        bill = row["id"] if row else p.create_project(EVAL_PROJECT, created_by="qc_agent_eval", game="FF", aspect="9:16")
    elif a.bill_project:
        bill = int(a.bill_project)
    if bill != a.project:
        print(f"tiền nghiệm thu tính vào dự án #{bill} (không vào #{a.project})")
    by_scene = {}
    for lab in labels:
        row = p.conn.execute("SELECT s.id, s.data FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.id=?", (lab["job"],)).fetchone()
        d = json.loads(row["data"] or "{}")
        path = picture(data_dir, a.project, lab["job"])
        if not path:
            raise SystemExit(f"thiếu ảnh job {lab['job']} — dừng")
        by_scene.setdefault(d.get("story_scene"), []).append({"scene_id": row["id"], "data": d, "job_id": lab["job"], "state": "pending_review",
                                                                "path": path, "label_verdict": lab["verdict"]})
    scenes = [s for s in sorted(by_scene) if not a.scenes or s in a.scenes]
    for s in scenes:
        print(f"cảnh {s}: {len(by_scene[s])} khung — nhãn: " + ", ".join(f"{f['data'].get('shot_no')}:{f['label_verdict']}" for f in by_scene[s]))
    if not a.yes:
        print("(chưa chạy — thêm --yes --max-usd <USD>; tốn Claude API)")
        return
    from group_test import load_env
    load_env(".")
    from core import llm_runner, qc_agent
    client = llm_runner.client_from_env(ledger=a.db)
    caught, missed, false_block, ok = [], [], [], 0
    out = {}
    path = os.path.join(data_dir, str(a.project), "qc_scene", "agent_eval.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    print(f"trần cứng cả lần chạy: ${a.max_usd:.2f} · mỗi cảnh: " + ", ".join(
        f"cảnh {s} ${qc_agent.scene_cap(len(by_scene[s])):.2f}" for s in scenes), flush=True)
    hard.start()
    with llm_runner.spend_cap(a.max_usd, "nghiệm thu agent QC") as total:
        for s in scenes:
            if not hard.allow(qc_agent.scene_cap(len(by_scene[s])), f"cảnh {s} (trần agent)"):   # a whole scene must fit
                break
            from core import project_budget                   # S7.1 01/10: the project's QC-stage cap stopped a scene midway (0,224 USD
            over = project_budget.check(p.conn, bill, "claude_qc", qc_agent.scene_cap(len(by_scene[s])))   # for nothing): ask first
            if over:
                print(f"dừng trước cảnh {s}: {over}", flush=True)
                break
            try:
                res = qc_agent.QcAgent(p, a.project, data_dir, client, by_scene[s], s,
                                       work_dir=os.path.join(data_dir, str(a.project), "qc_scene", f"agent_eval_scene_{s}"),
                                       bill_pid=bill).run()
            except script_cap.CapReached:          # chạm --max-usd giữa cảnh: các cảnh đã xong đã ghi ở agent_eval.json
                break
            out[str(s)] = res
            _score(s, by_scene[s], res, caught, missed, false_block)
            _learn(p, a.project, data_dir, by_scene[s], res)
            ok = sum(1 for sc in out for f in by_scene[int(sc)] if f["label_verdict"] != "chặn")
            summary = {"block_total": len(caught) + len(missed), "caught": caught, "missed": missed, "ok_total": ok,
                       "false_block": false_block, "usd": round(total["spent"], 4)}
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"summary": summary, "results": out}, fh, ensure_ascii=False, indent=1)
            print(f"cảnh {s}: {res['steps']} lượt · ${res.get('usd', 0):.3f}" + (f" · {res['stopped']}" if res.get("stopped") else ""),
                  flush=True)
    print(json.dumps({"caught": caught, "missed": missed, "false_block": false_block, "usd": round(total["spent"], 4)},
                     ensure_ascii=False, indent=1))


def _score(s, frames, res, caught, missed, false_block):
    for f, r in zip(frames, res["records"]):
        unseen = any((i.get("type") == "chưa soi") for i in r.get("issues") or [])
        if unseen:                                     # stopped by a lock before looking: neither caught nor missed (review 28/09)
            missed.append(f"cảnh {s} shot {f['data'].get('shot_no')} (nhãn {f['label_verdict']}) → CHƯA SOI (dừng: {res.get('stopped')})")
            continue
        flagged = r["verdict"] in ("block", "doubt")
        tag = f"cảnh {s} shot {f['data'].get('shot_no')} (nhãn {f['label_verdict']}) → {r['verdict']}"
        if f["label_verdict"] == "chặn":
            (caught if flagged else missed).append(tag + ": " + "; ".join(i["description"] for i in r.get("issues") or [])[:160])
        elif r["verdict"] == "block":
            false_block.append(tag)


def _learn(p, pid, data_dir, frames, res):
    """Sổ kinh nghiệm (core/experience): every frame where the agent and the human label disagree becomes a confirmed case the next
    run is shown — a false alarm (agent block, person pass/minor) or a miss (person block, agent pass/minor)."""
    from core import experience
    for f, r in zip(frames, res["records"]):
        if any(i.get("type") == "chưa soi" for i in r.get("issues") or []):
            continue
        said = "; ".join(f"{i.get('type')}: {i.get('description')}" for i in r.get("issues") or [])[:300]
        if r["verdict"] == "block" and f["label_verdict"] != "chặn":
            outcome = "false_alarm"
        elif f["label_verdict"] == "chặn" and r["verdict"] in ("pass", "minor"):
            outcome = "missed"
        else:
            continue
        ctx = experience.job_context(p.conn, f["job_id"])
        experience.record(p.conn, key=f"qc_eval:{f['job_id']}:{r['verdict']}", stage="qc_image", outcome=outcome, source="qc_agent_eval",
                          note=f"Agent chấm '{r['verdict']}' ({said or 'không lỗi'}) — nhãn người '{f['label_verdict']}'",
                          project_id=pid, job_id=f["job_id"], shot=ctx["shot"], subjects=ctx["subjects"], view=ctx["view"],
                          kind=next((i.get("type") for i in r.get("issues") or []), None),
                          evidence=experience.job_picture(data_dir, pid, f["job_id"]), confirmed_by="nhãn người")


if __name__ == "__main__":
    main()
