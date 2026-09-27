r"""Nghiệm thu agent QC trong app (core/qc_agent.py) trên bộ nhãn đã được người xác nhận (docs/AGENT_QC_THIET_KE_2026-09-27.md mục 4).

Bộ nhãn #8: 33 khung storyboard LƯỢT ĐẦU (trước khi vẽ lại) + kết luận agent QC đã được người dùng xác nhận 27/09
(docs/qc_agent_2026-09-27/verdicts.json: 11 chặn, 13 nhỏ, 9 đạt). Ảnh của khung đã bị loại nằm trong thùng rác dự án.
CHỈ ĐỌC: chạy QcAgent theo cảnh, không đổi trạng thái ảnh nào. Đo: bắt được bao nhiêu khung `chặn` (verdict block/doubt), báo nhầm bao nhiêu
khung `đạt`/`nhỏ` thành block. Chuẩn cổng tin cậy: bắt 100 % khung chặn, báo nhầm ≤ 10 %.

    py tools/experiments/qc_agent_eval.py --project 8 --scenes 1             kế hoạch
    py tools/experiments/qc_agent_eval.py --project 8 --scenes 1 --yes       chạy (tốn Claude API)
Khóa cứng: --max-usd (mặc định 0,6) cho CẢ lần chạy + trần mỗi cảnh của agent (qc_agent.SCENE_CAP_USD); chạm trần thì dừng, kết quả
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


def picture(data_dir, pid, job):
    path = os.path.join(data_dir, str(pid), "images", f"job_{job}.png")
    if os.path.exists(path):
        return path
    hits = sorted(glob.glob(os.path.join(data_dir, str(pid), "trash", "images", f"job_{job}__*.png")))
    return hits[-1] if hits else None


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
    ap.add_argument("--max-usd", type=float, default=0.6, help="trần cứng Claude cho cả lần chạy")
    a = ap.parse_args()
    labels = json.load(open(LABELS, encoding="utf-8"))
    labels = labels if isinstance(labels, list) else labels.get("frames") or labels.get("verdicts")
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect(a.db))
    data_dir = os.path.join(os.path.dirname(os.path.abspath(a.db)), "projects")
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
        print("(chưa chạy — thêm --yes; tốn Claude API)")
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
    with llm_runner.spend_cap(a.max_usd, "nghiệm thu agent QC") as total:
        for s in scenes:
            if total["spent"] + qc_agent.scene_cap(len(by_scene[s])) > a.max_usd:   # a whole scene must fit, not the last turn
                print(f"dừng trước cảnh {s}: chạm trần cả lần chạy (${total['spent']:.3f})", flush=True)
                break
            res = qc_agent.QcAgent(p, a.project, data_dir, client, by_scene[s], s,
                                   work_dir=os.path.join(data_dir, str(a.project), "qc_scene", f"agent_eval_scene_{s}")).run()
            out[str(s)] = res
            _score(s, by_scene[s], res, caught, missed, false_block)
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


if __name__ == "__main__":
    main()
