"""One action per step instead of "create jobs" + "submit": queue what is missing or outdated, then send it.
Shared by the dashboard buttons and the automatic run, so both redo exactly the parts a change affected (core.lineage)."""
from typing import Dict, List

from . import lineage, llm_io, pilot, regen
from .pipeline import Pipeline

LIVE = "('queued','running','succeeded','pending_review','approved','retryable')"


def queue_images(p: Pipeline, project_id: int) -> Dict:
    """Image jobs for ready scenes without a live picture, and a redo for approved pictures made from an outdated spec.
    While a pilot is running only its scenes are queued."""
    conn = p.conn
    fresh = [r["id"] for r in conn.execute(
        f"SELECT id FROM scenes WHERE project_id=? AND state='ready' AND id NOT IN (SELECT scene_id FROM jobs WHERE type='image_gen'"
        f" AND state IN {LIVE}) ORDER BY idx", (project_id,))]
    stale = {sid: r for sid, r in lineage.scan(conn, project_id).items() if r["image_stale"] and r["image_job_id"]}
    from . import shots
    fresh = [sid for sid in fresh if shots.needs_own_image(conn, sid)]   # v3 multi-shot: later shots of a group need no picture
    fresh = pilot.allowed_scenes(p, project_id, fresh)
    redo_ids = pilot.allowed_scenes(p, project_id, list(stale))
    for sid in fresh:
        p.create_job(sid, "image_gen")
    for sid in redo_ids:
        p.reopen_approved(stale[sid]["image_job_id"], f"Nội dung cảnh đã đổi: {stale[sid]['image_stale']}")
    return {"created": len(fresh), "redo": len(redo_ids), "pilot": pilot.active(p, project_id)}


def videos_to_make(p: Pipeline, project_id: int) -> List[Dict]:
    """Scenes ready for video (image + motion prompt approved and current) that have no clip made or in progress yet."""
    return [r for r in llm_io.ready_for_video(p, project_id)
            if not p.conn.execute(f"SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen' AND state IN {LIVE}",
                                  (r["scene_id"],)).fetchone()]


def queue_videos(p: Pipeline, project_id: int, data_dir: str) -> Dict:
    """Video jobs for scenes whose image + motion prompt are approved and current, and a redo for clips made from old inputs."""
    conn = p.conn
    created = 0
    for r in llm_io.ready_for_video(p, project_id):
        if not conn.execute(f"SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen' AND state IN {LIVE}", (r["scene_id"],)).fetchone():
            p.create_job(r["scene_id"], "video_gen")
            created += 1
    redo = 0
    for sid, r in lineage.scan(conn, project_id).items():
        if r["video_stale"] and r["video_job_id"] and not r["motion_stale"] and r["motion_state"] == "approved" \
                and r["video_state"] in ("succeeded", "approved", "pending_review"):
            regen.regenerate_video(p, data_dir, r["video_job_id"], f"làm lại vì {r['video_stale']}")
            redo += 1
    return {"created": created, "redo": redo}
