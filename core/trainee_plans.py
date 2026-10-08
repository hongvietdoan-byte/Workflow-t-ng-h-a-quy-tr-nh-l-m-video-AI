"""B4 🎓 học việc (08/10 — docs/KE_HOACH_HOC_VIEC_2026-10-08.md mục 2): "kế hoạch nó sẽ làm" of three roles, 0 USD, NO effect.

Once every shot has its approved picture (end of autopilot `_motion_phase`, or a button later — B7), write in trainee_log what
- `camera_setups` would group into one clip (shots.setup_groups: the Director's `camera_setup` labels, or — the Director is not asked
  for them while học việc — a guess: same script scene + size + angle + same people, next to each other),
- `continuous_takes` would film as one stretch (shots.stretch_of; needs camera_setups on or học việc),
- `end_frames` would draw an end frame for (end_frames.needed(ignore_route=True)).
Nothing is queued, drawn, sent or regrouped: shots.group_of, the Director prompt, last_frame and the cost estimate stay as with the
flag off. One subject = one row per project; a changed plan updates its row (and clears its old score)."""
import json
from typing import Dict, List

from . import features, shots, trainee


def _all_pictures_approved(conn, pid: int) -> bool:
    rows = conn.execute("SELECT id FROM scenes WHERE project_id=?", (pid,)).fetchall()
    if not rows:
        return False
    for r in rows:
        sid = shots.image_scene(conn, r["id"])
        if conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved' LIMIT 1", (sid,)).fetchone() is None:
            return False
    return True


def _labelled_rows(conn, pid: int) -> List[Dict]:
    """The shots with a camera set-up: the Director's labels when it wrote any, else a guessed one (marked `guessed`)."""
    rows = [r for r in shots._rows(conn, pid) if r["data"].get("shot_no")]
    for r in rows:
        r["project_id"] = pid
    if any(r["data"].get("camera_setup") for r in rows):
        return rows
    out, prev_key, n = [], None, {}
    for r in rows:
        d = r["data"]
        key = (d.get("story_scene"), d.get("size"), d.get("angle"), tuple(sorted(d.get("characters") or [])))
        if key != prev_key:
            n[d.get("story_scene")] = n.get(d.get("story_scene"), 0) + 1
        prev_key = key
        out.append(dict(r, data=dict(d, camera_setup=f"H{n[d.get('story_scene')]}"), guessed=True))
    return out


def _upsert(conn, feature: str, pid: int, subject: str, decision: str, would_do: Dict, **kw) -> str:
    """'new' / 'updated' / 'same' — one row per (feature, project, subject)."""
    row = conn.execute("SELECT id, decision, would_do FROM trainee_log WHERE feature=? AND project_id=? AND subject=? ORDER BY id DESC LIMIT 1",
                       (feature, pid, subject)).fetchone()
    js = json.dumps(would_do, ensure_ascii=False)
    if row is None:
        trainee.record(conn, feature, pid, subject, decision, would_do=would_do, **kw)
        return "new"
    if row["decision"] == decision and row["would_do"] == js:
        return "same"
    conn.execute("UPDATE trainee_log SET at=?, decision=?, would_do=?, truth=NULL, truth_source=NULL, match=NULL, scored_at=NULL "
                 "WHERE id=?", (trainee._now(), decision, js, row["id"]))
    conn.commit()
    return "updated"


def record_plans(conn, pid: int) -> Dict[str, Dict[str, int]]:
    """Write the plans of the 🎓 roles (only those in học việc). Returns {feature: {"new", "updated", "same"}}; {} when a shot still
    has no approved picture or no role is học việc."""
    want = [f for f in ("camera_setups", "continuous_takes", "end_frames") if features.shadow(f)]
    if not want or not _all_pictures_approved(conn, pid):
        return {}
    out: Dict[str, Dict[str, int]] = {}

    def note(feat, res):
        out.setdefault(feat, {"new": 0, "updated": 0, "same": 0})[res] += 1

    groups = []
    if features.shadow("camera_setups") or (features.shadow("continuous_takes") and features.active("camera_setups")):
        groups = shots.setup_groups_of(_labelled_rows(conn, pid))
    if features.shadow("camera_setups"):
        for g in groups:
            d0 = g[0]["data"]
            secs = [float(r["data"].get("duration_s") or 0) for r in g]
            alone = sum(shots.billed_shot_seconds(r["data"]) for r in g)
            together = max(shots.MULTISHOT_MIN_SHOT, int(-(-sum(secs) // 1)))
            would = {"shots": [r["data"].get("shot_no") for r in g], "scene_ids": [r["id"] for r in g],
                     "seconds": round(sum(secs), 2), "saved_s": max(0, alone - together), "guessed": bool(g[0].get("guessed"))}
            note("camera_setups", _upsert(conn, "camera_setups", pid, f"group:{d0.get('story_scene')}:{d0['camera_setup']}", "group",
                                          would, scene_id=g[0]["id"], story_scene=d0.get("story_scene")))
    if features.shadow("continuous_takes") and features.active("camera_setups"):
        for g in groups:
            st = shots.stretch_of(conn, g)
            if st is None:
                continue
            rows = st["rows"]
            story = rows[0]["data"].get("story_scene")
            first, last = rows[0]["data"].get("shot_no"), rows[-1]["data"].get("shot_no")
            would = {"shots": [r["data"].get("shot_no") for r in rows], "scene_ids": [r["id"] for r in rows],
                     "seconds": round(sum(st["seconds"]), 2), "setup": g[0]["data"]["camera_setup"]}
            note("continuous_takes", _upsert(conn, "continuous_takes", pid, f"stretch:{story}:{first}-{last}", "stretch", would,
                                             scene_id=rows[0]["id"], story_scene=story))
    if features.shadow("end_frames"):
        from . import end_frames
        proj = conn.execute("SELECT shot_mode FROM projects WHERE id=?", (pid,)).fetchone()
        mode = proj["shot_mode"] if proj is not None else None
        for s in conn.execute("SELECT id, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall():
            data = json.loads(s["data"] or "{}")
            if not end_frames.needed(data, mode, ignore_route=True):
                continue
            would = {"end_state": (data.get("end_state") or "").strip(), "route": end_frames.route(data)}
            note("end_frames", _upsert(conn, "end_frames", pid, f"end:{s['id']}", "need_end", would,
                                       scene_id=s["id"], story_scene=data.get("story_scene")))
    return out
