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

    Keys: idx, title, path (None when missing), state (state of the shot's take — core.takes.used: the chosen one, else the latest
    video_gen job — or None), requested_sec, usable, extra (a file that is no shot's clip).
    """
    from . import takes
    rows = pipeline.conn.execute(
        "SELECT s.id, s.idx, s.title, m.duration_sec FROM scenes s LEFT JOIN motion_prompts m ON m.scene_id=s.id"
        " WHERE s.project_id=? ORDER BY s.idx", (project_id,)).fetchall()
    clips, known = [], set()
    for r in rows:
        path = clip_path(data_dir, project_id, r["idx"])
        job = takes.used(pipeline.conn, r["id"])        # KLD-2 (08/10): the take the person chose, not just the newest job
        if job is not None and _is_chosen(pipeline.conn, r["id"], job) and job["result_path"]:
            path = job["result_path"]                    # e.g. a stashed ⭐ take (NN_t4a.mp4) the person picked
        known.add(os.path.basename(path))
        state = job["state"] if job else None
        clips.append({"idx": r["idx"], "scene_id": r["id"], "title": r["title"], "path": path if os.path.exists(path) else None,
                      "state": state, "requested_sec": r["duration_sec"],
                      # a clip still waiting for its video check / a person, or thrown away, does not go into the cut by default
                      "usable": state in (None, "succeeded", "approved"), "extra": False})
    folder = os.path.dirname(clip_path(data_dir, project_id, 0))
    extras = sorted(n for n in (os.listdir(folder) if os.path.isdir(folder) else [])
                    if n.lower().endswith(".mp4") and n not in known
                    and not n.lower().endswith(("_raw.mp4", "_group.mp4")))   # v3: uncut / whole multi-shot originals of a shot
    for name in extras:
        # KLD-3 (08/10): bản dựng #33 của #22 gom 4 tệp phụ (bản sao, bản giữ tay) và thiếu shot 1, 2 — a file that is no shot's clip
        # is listed (⚠ at Step 5) but goes in only when the person ticks it
        clips.append({"idx": None, "scene_id": None, "title": name, "path": os.path.join(folder, name), "state": None,
                      "requested_sec": None, "usable": False, "extra": True})
    return clips


def _is_chosen(conn, scene_id: int, job) -> bool:
    from . import takes
    pick = takes.chosen(conn, scene_id)
    return pick is not None and pick["id"] == job["id"]


def extra_files(clips: List[Dict]) -> List[Dict]:
    """KLD-3: the .mp4 files in videos/ that are no shot's clip (not used unless ticked)."""
    return [c for c in clips if c.get("extra")]


def save_manual_clip(data_dir: str, project_id: int, filename: str, data: bytes) -> str:
    """A clip the person uploads by hand (named by shot order, e.g. 05.mp4). Only the file name is used (no folders), and a clip
    already there — possibly a paid generation — goes to the trash instead of being overwritten. Returns the saved path."""
    from . import trash
    name = os.path.basename((filename or "").replace("\\", "/")).strip()
    if not name.lower().endswith(".mp4") or name in (".mp4",):
        raise ValueError("chỉ nhận file .mp4 có tên, ví dụ 05.mp4")
    folder = os.path.dirname(clip_path(data_dir, project_id, 0))
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, name)
    trash.move_to_trash(dest, data_dir, project_id, "videos", "thay bằng clip tải lên tay")
    with open(dest, "wb") as f:
        f.write(data)
    return dest


def usable_clips(pipeline: Pipeline, data_dir: str, project_id: int) -> List[Dict]:
    """Clips that exist and may go into the final cut, in scene order."""
    return [c for c in collect_clips(pipeline, data_dir, project_id) if c["path"] and c["usable"]]


def collect_clips_for_render(conn, data_dir: str, project_id: int, clip_paths: Optional[List[str]] = None) -> List[Dict]:
    """The clips of a render in their order: the given paths (as chosen in Step 5), or every usable clip."""
    clips = collect_clips(Pipeline(conn), data_dir, project_id)
    if clip_paths is None:
        return [c for c in clips if c["path"] and c["usable"]]
    by_path = {os.path.normcase(os.path.abspath(c["path"])): c for c in clips if c["path"]}
    return [by_path.get(os.path.normcase(os.path.abspath(p)), {"idx": None, "scene_id": None, "title": os.path.basename(p),
                                                             "path": p, "state": None, "requested_sec": None, "usable": True})
            for p in clip_paths]


def clip_seconds(path: str, requested: Optional[float]) -> float:
    """Real length when ffmpeg can read it, else the requested length, else a default."""
    return ffmpeg_studio.probe_duration(path) or requested or DEFAULT_SECONDS


def preview_with_music(pipeline: Pipeline, data_dir: str, project_id: int, music_path: str, out_path: str,
                       volume: float = 0.6, keep_audio: bool = False) -> str:
    """Quick cut of the clips that exist, with the given music on top: to judge whether a track fits the picture."""
    clips = [c for c in collect_clips(pipeline, data_dir, project_id) if c["path"] and c["usable"]]
    if not clips:
        raise ValueError("chưa có clip nào để xem thử cùng nhạc")
    durations = [clip_seconds(c["path"], c["requested_sec"]) for c in clips]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    return ffmpeg_studio.render_final([c["path"] for c in clips], out_path, durations, "cut", 1.0, music_path, volume,
                                       keep_audio=keep_audio)


def draft_preview(pipeline: Pipeline, data_dir: str, project_id: int, out_path: Optional[str] = None) -> Dict:
    """09/10 (người dùng: "chưa có nút gộp xem bản draft"): ghép NHANH bản đang dùng của từng shot theo thứ tự — kể cả nháp / chờ
    duyệt (bản giao chỉ lấy clip duyệt) — để xem trọn bộ trước khi duyệt. Chỉ để xem: không ghi `outputs`, không nhạc, giữ khung dự án,
    0 USD (ffmpeg). {"path", "shots": [idx…], "missing": [idx…], "seconds"}."""
    from . import takes
    from .formats import canvas, project_aspect
    conn = pipeline.conn
    paths, shots, missing, durs = [], [], [], []
    for r in conn.execute("SELECT id, idx FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall():
        t = takes.used(conn, r["id"])
        path = t["result_path"] if t is not None else None
        if t is None or t["state"] in ("failed", "cancelled", "rejected", "queued", "running") or not path or not os.path.exists(path):
            missing.append(r["idx"])
            continue
        paths.append(path)
        shots.append(r["idx"])
        durs.append(clip_seconds(path, None))
    if not paths:
        raise ValueError("chưa có clip nào (kể cả nháp) để ghép xem")
    out = out_path or os.path.join(data_dir, str(project_id), "output", "xem_nhap.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    try:
        size = tuple(canvas(project_aspect(pipeline.project(project_id))))
    except Exception:  # noqa: BLE001 - no frame spec: the clips' own size
        size = None
    ffmpeg_studio.render_final(paths, out, durs, "cut", 1.0, None, keep_audio=False, size=size)
    return {"path": out, "shots": shots, "missing": missing, "seconds": round(sum(durs), 2)}


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
