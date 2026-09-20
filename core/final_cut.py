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
        clips.append({"idx": r["idx"], "scene_id": r["id"], "title": r["title"], "path": path if os.path.exists(path) else None,
                      "state": job["state"] if job else None, "requested_sec": r["duration_sec"]})
    folder = os.path.dirname(clip_path(data_dir, project_id, 0))
    extras = sorted(n for n in (os.listdir(folder) if os.path.isdir(folder) else [])
                    if n.lower().endswith(".mp4") and n not in known)
    for name in extras:
        clips.append({"idx": None, "scene_id": None, "title": name, "path": os.path.join(folder, name), "state": None,
                      "requested_sec": None})
    return clips


def clip_seconds(path: str, requested: Optional[float]) -> float:
    """Real length when ffmpeg can read it, else the requested length, else a default."""
    return ffmpeg_studio.probe_duration(path) or requested or DEFAULT_SECONDS


def preview_with_music(pipeline: Pipeline, data_dir: str, project_id: int, music_path: str, out_path: str,
                       volume: float = 0.6) -> str:
    """Quick cut of the clips that exist, with the given music on top: to judge whether a track fits the picture."""
    clips = [c for c in collect_clips(pipeline, data_dir, project_id) if c["path"]]
    if not clips:
        raise ValueError("chưa có clip nào để xem thử cùng nhạc")
    durations = [clip_seconds(c["path"], c["requested_sec"]) for c in clips]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    return ffmpeg_studio.render_final([c["path"] for c in clips], out_path, durations, "cut", 1.0, music_path, volume)


def total_seconds(durations: List[float], transition: str, fade: float) -> float:
    total = sum(durations)
    return total - fade * (len(durations) - 1) if transition in ffmpeg_studio.OVERLAP_STYLES and durations else total


def render_problems(durations: List[float], transition: str, fade: float) -> List[str]:
    """Reasons the current choice cannot be rendered (shown before pressing Render)."""
    if not durations:
        return ["chưa chọn clip nào"]
    if transition in ffmpeg_studio.OVERLAP_STYLES:
        if len(durations) < 2:
            return [f"{transition} cần ít nhất 2 clip"]
        short = [f"{d:.1f}s" for d in durations if d <= fade]
        if short:
            return [f"clip ngắn hơn hoặc bằng thời gian chuyển cảnh ({fade}s): {', '.join(short)}"]
    return []
