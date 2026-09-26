"""Comparing production variants of the same script (kế hoạch v3, GĐ5–6): V0 one clip per scene (v2), V1 one clip per shot,
V2 Kling multi-shot per group.

- clone_project: a copy that starts from the same point (script, script scenes, scene / shot rows, Character Bible with its
  Lock, voices and references, World Bible, render / subtitle / end card settings) — without pictures, prompts or clips.
- metrics: the numbers of one project for the comparison table.
- scores: the person's 1–5 marks per criterion, kept in app_settings (key 'eval:<project id>').
- report_markdown: the table for docs/V3_AB_REPORT.md.
"""
import json
import os
from typing import Dict, List, Optional

from .pipeline import Pipeline

SKIP_PROJECT = {"id", "name", "created_at", "created_by", "paused", "autopilot_state", "autopilot_note", "autopilot_beat",
                "autopilot_log", "autopilot_user", "autopilot_saved_cfg", "pilot"}
FRESH_BIBLE = {"description": "", "wardrobe": None, "locked": 0, "lock_rules": None, "bible_check": None, "user_edited": None,
               "anchor_approved": 0}
"""Character columns reset in a "chạy lại Director" clone: the Director writes a new Bible (an empty description = never written, see
autopilot._director_phase); the person's choices — voice, reference pictures, outfit, Seedance subject — are kept. The old Lock is not
copied: the approved library profile (T1, assets.standard_for) still applies by itself, a project Lock is written again."""
CRITERIA = {"characters": "Nhân vật nhất quán", "setting": "Bối cảnh nhất quán", "rhythm": "Nhịp dựng",
            "ff_feel": "“Chất” Free Fire", "overall": "Tổng thể"}


def _cols(conn, table: str) -> List[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]


def clone_project(p: Pipeline, project_id: int, name: str, shot_mode: Optional[str] = "keep", with_rows: bool = True) -> int:
    """A new project with the same starting point. shot_mode: 'keep' or a new value (None / 'per_shot' / 'multishot').
    with_rows: copy the scene / shot rows (same Director plan) — False keeps only the script scenes (run the Director again)."""
    conn = p.conn
    src = p.project(project_id)
    skip = SKIP_PROJECT | ({"director_raw"} if not with_rows else set())    # the old plan must not seed "chia shot lại một cảnh"
    cols = [c for c in _cols(conn, "projects") if c not in skip]
    values = [src[c] for c in cols]
    if shot_mode != "keep":
        values[cols.index("shot_mode")] = shot_mode
    if "autopilot_gates" in cols:          # the person's checkpoint switches carry over; the run state (Bible approved…) does not
        try:
            gates = json.loads(src["autopilot_gates"] or "{}")
        except ValueError:
            gates = {}
        values[cols.index("autopilot_gates")] = json.dumps({k: v for k, v in gates.items() if k in ("bible", "pilot", "storyboard")}) \
            if gates else None
    cur = conn.execute(f"INSERT INTO projects (name, created_at, created_by, {', '.join(cols)}) VALUES (?, datetime('now'), ?, "
                       + ", ".join("?" for _ in cols) + ")", [name, p.actor] + values)
    new = cur.lastrowid
    ccols = [c for c in _cols(conn, "characters") if c not in ("id", "project_id")]
    fresh = {} if with_rows else FRESH_BIBLE        # "chạy lại Director": a fresh Bible (T1 standard profiles still apply from the Kho)
    for r in conn.execute("SELECT * FROM characters WHERE project_id=?", (project_id,)).fetchall():
        conn.execute(f"INSERT INTO characters (project_id, {', '.join(ccols)}) VALUES (?, " + ", ".join("?" for _ in ccols) + ")",
                     [new] + [fresh[c] if c in fresh else r[c] for c in ccols])
    conn.execute("INSERT INTO project_assets (project_id, asset_id) SELECT ?, asset_id FROM project_assets WHERE project_id=?",
                 (new, project_id))
    conn.execute("INSERT INTO story_scenes (project_id, idx, heading, text, data) SELECT ?, idx, heading, text, data"
                 " FROM story_scenes WHERE project_id=?", (new, project_id))
    if with_rows:
        conn.execute("INSERT INTO scenes (project_id, idx, title, state, data) SELECT ?, idx, title, 'ready', data"
                     " FROM scenes WHERE project_id=?", (new, project_id))
    else:                                 # one row per script scene, as right after the import: the Director starts again
        from .shots import story_scenes
        for s in story_scenes(p, project_id):
            conn.execute("INSERT INTO scenes (project_id, idx, title, data) VALUES (?,?,?,?)",
                         (new, s["idx"], s["heading"], json.dumps({"text": s["text"], "characters": s["data"].get("characters") or []},
                                                                  ensure_ascii=False)))
    conn.commit()
    from .pipeline import cheap_while_testing
    cheap_while_testing(conn, new)          # a copy made during a budget test round is cheap too
    return new


def _q(conn, sql: str, args) -> Optional[float]:
    row = conn.execute(sql, args).fetchone()
    return row[0] if row else None


def metrics(p: Pipeline, project_id: int, data_dir: str) -> Dict:
    """Numbers of one variant: shots, film length and shot length, cost, generation time, retries, QC scores, consistency
    check result, dialogue problems."""
    from . import claude_tasks, cost, delivery, dialogue, ffmpeg_studio, shots
    conn = p.conn
    proj = p.project(project_id)
    rows = conn.execute("SELECT id FROM scenes WHERE project_id=?", (project_id,)).fetchall()
    best = delivery.status(p, project_id, data_dir).get("best")
    film = ffmpeg_studio.probe_duration(best) if best and os.path.exists(best) else None
    spend = cost.spend_summary(conn, project_id, cost.load_pricing())
    first = _q(conn, "SELECT MIN(created_at) FROM jobs WHERE project_id=?", (project_id,))
    last = _q(conn, "SELECT MAX(updated_at) FROM jobs WHERE project_id=?", (project_id,))
    minutes = None
    if first and last:
        from datetime import datetime
        try:
            fmt = lambda s: datetime.fromisoformat(str(s).replace("Z", "+00:00"))  # noqa: E731
            minutes = round((fmt(last) - fmt(first)).total_seconds() / 60, 1)
        except ValueError:
            minutes = None

    def qc(kind: str) -> Optional[float]:
        v = _q(conn, "SELECT AVG(q.score) FROM qc_results q JOIN jobs j ON j.id=q.job_id WHERE j.project_id=? AND j.type=?",
               (project_id, kind))
        return round(v, 3) if v is not None else None
    clip_check = claude_tasks.last_clip_set_check(data_dir, project_id)
    return {
        "project_id": project_id, "name": proj["name"], "mode": shots.MODES.get(shots.mode(proj)), "style": shots.style(proj),
        "shots": len(rows), "film_sec": round(film, 1) if film else None,
        "avg_shot_sec": round(film / len(rows), 2) if film and rows else None,
        "usd": round(spend["credits"], 2), "images": spend["images"], "clips": spend["clips"], "video_sec": spend["seconds"],
        "unknown_prices": spend["unknown_prices"], "minutes": minutes,
        "image_jobs": int(_q(conn, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen'", (project_id,)) or 0),
        "video_jobs": int(_q(conn, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='video_gen' AND group_leader IS NULL",
                             (project_id,)) or 0),
        "retries": int(_q(conn, "SELECT COALESCE(SUM(retry_count), 0) FROM jobs WHERE project_id=?", (project_id,)) or 0),
        "qc_image": qc("image_gen"), "qc_video": qc("video_gen"),
        "clip_set_issues": None if clip_check is None else len(clip_check.get("issues") or []),
        "dialogue_problems": len(dialogue.problems(dialogue.check(p, project_id))),
        "final": best, "scores": get_scores(conn, project_id),
    }


def get_scores(conn, project_id: int) -> Dict:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (f"eval:{project_id}",)).fetchone()
    try:
        return json.loads(row["value"]) if row else {}
    except ValueError:
        return {}


def save_scores(conn, project_id: int, scores: Dict) -> None:
    clean = {k: int(v) for k, v in scores.items() if k in CRITERIA and v}
    if scores.get("note"):
        clean["note"] = str(scores["note"])[:2000]
    conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (f"eval:{project_id}", json.dumps(clean, ensure_ascii=False)))
    conn.commit()


def report_markdown(rows: List[Dict]) -> str:
    """Comparison table (Vietnamese) for docs/V3_AB_REPORT.md."""
    def v(x, fmt="{}"):
        return "—" if x is None else fmt.format(x)
    head = ["Chỉ số"] + [f"{r['name']} ({r['mode'] or 'v2'})" for r in rows]
    lines = [("Số shot / clip", [v(r["shots"]) for r in rows]),
             ("Độ dài phim (s)", [v(r["film_sec"]) for r in rows]),
             ("Độ dài shot trung bình (s)", [v(r["avg_shot_sec"]) for r in rows]),
             ("Chi phí video + âm thanh (USD, theo bảng giá)", [v(r["usd"], "${:.2f}") for r in rows]),
             ("Số ảnh / số lần gen video", [f"{r['images']} / {r['video_jobs']}" for r in rows]),
             ("Giây video bị tính", [v(r["video_sec"]) for r in rows]),
             ("Thời gian làm (phút)", [v(r["minutes"]) for r in rows]),
             ("Số lần gen lại", [v(r["retries"]) for r in rows]),
             ("QC ảnh / QC video (trung bình)", [f"{v(r['qc_image'])} / {v(r['qc_video'])}" for r in rows]),
             ("Clip lệch (QC đồng bộ cả bộ)", [v(r["clip_set_issues"]) for r in rows]),
             ("Cảnh/shot thoại không vừa clip", [v(r["dialogue_problems"]) for r in rows])]
    lines += [(f"Điểm của bạn — {label}", [v(r["scores"].get(k)) for r in rows]) for k, label in CRITERIA.items()]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join([name] + vals) + " |" for name, vals in lines]
    return "\n".join(out)
