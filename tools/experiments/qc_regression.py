r"""Nghiệm thu QC theo cảnh trên lỗi CŨ đã biết (người dùng 2026-09-27: "QC phải loại bỏ hoàn toàn lỗi nhìn bằng mắt thấy ngay").

Dựng lại từng cảnh của #8 bằng đúng các ảnh GHÉP đã có nhãn bằng mắt (15 ảnh lỗi rõ còn file gốc: khung chữ nhật dán, nền là sàn, đè
cột, vẽ cả cảnh, tháp Big Ben), chạy QC lớp 1 (1 lượt Claude / cảnh) — CHỈ ĐỌC: không đổi trạng thái ảnh nào — rồi đếm: bắt được bao
nhiêu lỗi (verdict fix / doubt), báo nhầm bao nhiêu ảnh không lỗi. Chuẩn nghiệm thu: bắt 15/15.

    py tools/experiments/qc_regression.py --project 8            chỉ in kế hoạch (các cảnh, ảnh nào lỗi)
    py tools/experiments/qc_regression.py --project 8 --yes      chạy (≈ 6 lượt Claude)
Kết quả: data/projects/<id>/qc_scene/regression.json
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "experiments"))

BAD = {268: "nền là sàn nhìn từ trên", 289: "nền là sàn nhìn từ trên", 283: "Kenta đè lên khối tường", 297: "vẽ cả cảnh thay phông xanh",
       300: "tháp Big Ben giữa ảnh", **{j: "khung chữ nhật dán lên nền" for j in (273, 275, 276, 278, 279, 288, 290, 298, 299, 302)}}
LAST_COMPOSITE_JOB = 317


def picture_path(data_dir, pid, job_id):
    """The job's picture — in images/, or in the project's trash when the picture was rejected (trash.move_to_trash). None = gone.
    (First run 2026-09-27 took the images/ path of rejected pictures without checking: the sheet drew black cells and the QC judged
    black squares, not the faults.)"""
    import glob
    path = os.path.join(data_dir, str(pid), "images", f"job_{job_id}.png")
    if os.path.exists(path):
        return path
    hits = sorted(glob.glob(os.path.join(data_dir, str(pid), "trash", "images", f"job_{job_id}__*.png")))
    return hits[-1] if hits else None


def frames_of(p, pid, data_dir):
    """story scene -> frames (the composited pictures of the trial, the labelled faulty one where a shot had one)."""
    out = {}
    for s in p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall():
        d = json.loads(s["data"] or "{}")
        jobs = [r["id"] for r in p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND id<=? ORDER BY id",
                                                (s["id"], LAST_COMPOSITE_JOB))]
        bad = [j for j in jobs if j in BAD and picture_path(data_dir, pid, j)]
        pick = bad[-1] if bad else next((j for j in reversed(jobs) if picture_path(data_dir, pid, j)), None)
        if pick is None:
            continue
        out.setdefault(d.get("story_scene"), []).append({"scene_id": s["id"], "idx": s["idx"], "data": d, "job_id": pick,
                                                         "state": "pending_review", "path": picture_path(data_dir, pid, pick)})
    for fr in out.values():
        for r in fr:
            if not (r["path"] and os.path.exists(r["path"])):
                raise SystemExit(f"thiếu tệp ảnh job {r['job_id']} — dừng (không chấm ô trống)")
    return out


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--db", default=os.path.join("data", "manifest.sqlite"))
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    from group_test import load_env
    load_env(".")
    from core import llm_runner, qc_scene
    from core.claude_tasks import _run
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect(a.db))
    data_dir = os.path.join(os.path.dirname(os.path.abspath(a.db)), "projects")
    scenes = frames_of(p, a.project, data_dir)
    for s, fr in scenes.items():
        print(f"cảnh {s}: {len(fr)} khung, lỗi đã biết: " + ", ".join(f"K{k} {BAD[r['job_id']]}" for k, r in enumerate(fr, 1) if r["job_id"] in BAD))
    if not a.yes:
        print("(chưa chạy — thêm --yes)")
        return
    client = llm_runner.client_from_env(ledger=a.db)
    results, caught, missed, false_alarm, good = {}, [], [], [], 0
    for s, fr in scenes.items():
        prompt, images, labels = qc_scene.build_request(p, a.project, fr, data_dir)
        obj = _run(p, a.project, "qc", prompt, lambda o: qc_scene.validate(o, labels), client, images)
        results[str(s)] = {"jobs": [r["job_id"] for r in fr], "answer": obj}
        by_k = {f["k"]: f for f in obj["frames"]}
        for k, r in enumerate(fr, 1):
            f = by_k[k]
            flagged = f["verdict"] in ("fix", "doubt")
            tag = f"cảnh {s} K{k} job {r['job_id']}"
            if r["job_id"] in BAD:
                (caught if flagged else missed).append(f"{tag} ({BAD[r['job_id']]}) → {f['verdict']}: {f.get('problem') or ''}")
            else:
                good += 1
                if flagged:
                    false_alarm.append(f"{tag} → {f['verdict']}: {f.get('problem') or ''}")
        print(f"cảnh {s}: xong", flush=True)
    summary = {"bad_total": len(caught) + len(missed), "caught": caught, "missed": missed, "good_total": good, "false_alarm": false_alarm}
    os.makedirs(os.path.join(data_dir, str(a.project), "qc_scene"), exist_ok=True)
    with open(os.path.join(data_dir, str(a.project), "qc_scene", "regression.json"), "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
