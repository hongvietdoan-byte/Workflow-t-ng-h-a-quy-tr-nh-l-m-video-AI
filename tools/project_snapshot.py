"""Snapshot of one project's run (scene spec, prompts, models, settings, clips) from a database file → JSON + a short Markdown.

Used to compare runs of the same project (Khủng Long Đỏ 07/10: trial 1, trial 2, high quality) and keep what was learnt.
    py tools/project_snapshot.py <db> <project_id> <label> <out_dir> [--git <commit>]
"""
import json
import os
import sqlite3
import sys


def snapshot(db: str, pid: int, label: str, commit: str = "") -> dict:
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    cols = lambda t: {r[1] for r in c.execute(f"PRAGMA table_info({t})")}  # noqa: E731
    proj = dict(c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone())
    keep = ("name", "aspect", "genre", "image_model", "test_quality", "shot_mode", "render_settings", "model_priority", "look")
    out = {"label": label, "db": os.path.basename(db), "git": commit,
           "project": {k: proj.get(k) for k in keep if k in proj},
           "characters": [dict(r) for r in c.execute("SELECT name, description, lock_rules, outfit_image_ids FROM characters "
                                                       "WHERE project_id=? ORDER BY name", (pid,))],
           "shots": []}
    has_mp = "motion_prompts" in {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for s in c.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)):
        d = json.loads(s["data"] or "{}")
        mp = c.execute("SELECT motion_prompt, duration_sec, state FROM motion_prompts WHERE scene_id=?", (s["id"],)).fetchone() if has_mp else None
        jobs = []
        for t in ("image_gen", "video_gen"):
            for j in c.execute("SELECT id, state, model, retry_count, retry_reason, result_path FROM jobs WHERE scene_id=? AND type=? "
                               "ORDER BY id", (s["id"], t)):
                jobs.append({"type": t, **dict(j)})
        approved = {t: next((j for j in reversed(jobs) if j["type"] == t and j["state"] == "approved"), None)
                    for t in ("image_gen", "video_gen")}
        out["shots"].append({
            "idx": s["idx"], "scene_id": s["id"],
            "spec": {k: d.get(k) for k in ("text", "dialogue", "characters", "location", "size", "angle", "move", "video_route",
                                           "transition_in", "shake_in", "start_from_prev_clip", "duration_s", "image_prompt")},
            "motion_prompt": dict(mp) if mp else None,
            "approved_image": approved["image_gen"], "approved_video": approved["video_gen"],
            "takes": {"image": sum(1 for j in jobs if j["type"] == "image_gen"), "video": sum(1 for j in jobs if j["type"] == "video_gen")},
        })
    return out


def markdown(snap: dict) -> str:
    p = snap["project"]
    lines = [f"# {snap['label']} — {p.get('name')}", "",
             f"- Model ảnh: `{p.get('image_model') or 'mặc định (Seedream 5 Pro)'}` · thử rẻ: {p.get('test_quality')} · git: `{snap['git']}`",
             f"- Thiết lập dựng: `{p.get('render_settings')}`", "", "| Shot | Đường | Video duyệt (model) | Số lượt ảnh/video | Thoại | Ghi chú |",
             "|---|---|---|---|---|---|"]
    for s in snap["shots"]:
        sp, v = s["spec"], s["approved_video"] or {}
        dl = "; ".join(f"{x.get('speaker')}: {x.get('text')}" for x in (sp.get("dialogue") or []))
        flags = ", ".join(k for k in ("transition_in", "shake_in", "start_from_prev_clip") if sp.get(k))
        lines.append(f"| {s['idx']} | {sp.get('video_route') or 'tự động'} | {v.get('model') or '—'} | {s['takes']['image']}/{s['takes']['video']} "
                     f"| {dl or '—'} | {flags or '—'} |")
    lines += ["", "Chi tiết prompt ảnh / motion: file JSON cùng tên."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    db, pid, label, out_dir = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    commit = sys.argv[sys.argv.index("--git") + 1] if "--git" in sys.argv else ""
    os.makedirs(out_dir, exist_ok=True)
    snap = snapshot(db, pid, label, commit)
    base = os.path.join(out_dir, label)
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    with open(base + ".md", "w", encoding="utf-8") as f:
        f.write(markdown(snap))
    print(base + ".json", base + ".md")
