"""Step 5b helpers: which clips exist for the final cut, in scene order, with a duration for each."""
import os
from typing import Dict, List, Optional

from . import ffmpeg_studio
from .pipeline import Pipeline

DEFAULT_SECONDS = 5.0


def clip_path(data_dir: str, project_id: int, idx: int) -> str:
    return os.path.join(data_dir, str(project_id), "videos", f"{idx:02d}.mp4")


def collect_clips(pipeline: Pipeline, data_dir: str, project_id: int) -> List[Dict]:
    """One row per scene (clip present or not), then any extra .mp4 files in the folder, ordered by name.

    Keys: idx, title, path (None when missing), state (latest video_gen job state or None), requested_sec.
    """
    rows = pipeline.conn.execute(
        "SELECT s.id, s.idx, s.title, m.duration_sec FROM scenes s LEFT JOIN motion_prompts m ON m.scene_id=s.id"
        " WHERE s.project_id=? ORDER BY s.idx", (project_id,)).fetchall()
    clips, known = [], set()
    for r in rows:
        path = clip_path(data_dir, project_id, r["idx"])
        job = pipeline.conn.execute("SELECT state FROM jobs WHERE scene_id=? AND type='video_gen'"
                                    " AND state!='cancelled' ORDER BY id DESC LIMIT 1", (r["id"],)).fetchone()
        known.add(os.path.basename(path))
        clips.append({"idx": r["idx"], "title": r["title"], "path": path if os.path.exists(path) else None,
                      "state": job["state"] if job else None, "requested_sec": r["duration_sec"]})
    folder = os.path.dirname(clip_path(data_dir, project_id, 0))
    extras = sorted(n for n in (os.listdir(folder) if os.path.isdir(folder) else [])
                    if n.lower().endswith(".mp4") and n not in known)
    for name in extras:
        clips.append({"idx": None, "title": name, "path": os.path.join(folder, name), "state": None,
                      "requested_sec": None})
    return clips


def clip_seconds(path: str, requested: Optional[float]) -> float:
    """Real length when ffmpeg can read it, else the requested length, else a default."""
    return ffmpeg_studio.probe_duration(path) or requested or DEFAULT_SECONDS


def total_seconds(durations: List[float], transition: str, fade: float) -> float:
    total = sum(durations)
    return total - fade * (len(durations) - 1) if transition == "crossfade" and durations else total


def render_problems(durations: List[float], transition: str, fade: float) -> List[str]:
    """Reasons the current choice cannot be rendered (shown before pressing Render)."""
    if not durations:
        return ["chưa chọn clip nào"]
    if transition == "crossfade":
        if len(durations) < 2:
            return ["crossfade cần ít nhất 2 clip"]
        short = [f"{d:.1f}s" for d in durations if d <= fade]
        if short:
            return [f"clip ngắn hơn hoặc bằng thời gian crossfade ({fade}s): {', '.join(short)}"]
    return []
