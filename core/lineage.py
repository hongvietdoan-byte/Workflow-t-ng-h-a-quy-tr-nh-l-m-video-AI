"""Which results are outdated ("⚠ cũ"): every product keeps a fingerprint of what it was made from, and is compared with what
its inputs are now. Nothing has to remember to "invalidate" anything when a scene, a character or a picture changes — the next
look at the data finds it.

Chain: scene spec + characters + aspect → approved image → motion prompt → video → final render → subtitles / end card / exports.
A NULL fingerprint (a result made before v2) counts as up to date, so old projects raise no false alarms.
"""
import hashlib
import json
import os
from typing import Dict, List, Optional

USABLE_VIDEO = ("succeeded", "approved")              # a clip that may go into the final cut (pending_review waits for a person)
IMAGE_KEYS = ("image_prompt", "blocking", "location", "location_asset", "layout")
MOTION_KEYS = ("text", "dialogue", "camera_complexity", "duration_s", "emotional_intent", "beat")
CAST_KEYS = ("name", "description", "wardrobe", "ref_asset_id", "ref_image_ids", "outfit_image_ids", "lock_rules")


def _hash(obj) -> str:
    return hashlib.sha1(json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


def image_spec_hash(scene_data: Dict, cast_rows, aspect: Optional[str]) -> str:
    """What the image generator is given for a scene: its prompt/blocking/place/layout and the look of everyone in it."""
    cast = set(scene_data.get("characters") or [])
    people = sorted(({k: (r[k] if k in r.keys() else None) for k in CAST_KEYS} for r in cast_rows if r["name"] in cast),
                    key=lambda d: d["name"])
    return _hash({"scene": {k: scene_data.get(k) for k in IMAGE_KEYS}, "cast": people, "aspect": aspect or ""})


def motion_spec_hash(scene_data: Dict) -> str:
    return _hash({k: scene_data.get(k) for k in MOTION_KEYS})


def video_input_hash(mp_row, aspect: Optional[str]) -> str:
    keys = ("motion_prompt", "negative_prompt", "duration_sec", "ref_video_path", "ref_video_type")
    return _hash({"mp": {k: mp_row[k] for k in keys if k in mp_row.keys()}, "aspect": aspect or ""})


def _aspect(conn, project_id: int) -> Optional[str]:
    row = conn.execute("SELECT aspect FROM projects WHERE id=?", (project_id,)).fetchone()
    return row["aspect"] if row else None


def current_image_hash(conn, project_id: int, scene_id: int) -> str:
    data = json.loads(conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()["data"] or "{}")
    cast_rows = conn.execute("SELECT * FROM characters WHERE project_id=?", (project_id,)).fetchall()
    return image_spec_hash(data, cast_rows, _aspect(conn, project_id))


def approved_image_id(conn, scene_id: int) -> Optional[int]:
    row = conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved' ORDER BY id DESC LIMIT 1",
                       (scene_id,)).fetchone()
    return row["id"] if row else None


def stamp_motion(conn, scene_id: int) -> None:
    """A motion prompt was (re)written or approved: it now belongs to the current approved image and scene spec."""
    data = json.loads(conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()["data"] or "{}")
    conn.execute("UPDATE motion_prompts SET image_job_id=?, spec_hash=? WHERE scene_id=?",
                 (approved_image_id(conn, scene_id), motion_spec_hash(data), scene_id))


# ---- per-scene scan ---------------------------------------------------------------------------------------------------
def scan(conn, project_id: int) -> Dict[int, Dict]:
    """scene_id -> {idx, image_job_id, image_stale, motion_stale, video_job_id, video_stale}; a *_stale value is None (fresh or
    nothing to judge) or a short Vietnamese reason."""
    aspect = _aspect(conn, project_id)
    cast_rows = conn.execute("SELECT * FROM characters WHERE project_id=?", (project_id,)).fetchall()
    scenes = conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall()
    images = {r["scene_id"]: r for r in conn.execute(
        "SELECT j.scene_id, j.id, j.input_hash FROM jobs j WHERE j.project_id=? AND j.type='image_gen' AND j.state='approved'"
        " AND j.id=(SELECT MAX(k.id) FROM jobs k WHERE k.scene_id=j.scene_id AND k.type='image_gen' AND k.state='approved')",
        (project_id,))}
    motions = {r["scene_id"]: r for r in conn.execute(
        "SELECT m.* FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id WHERE s.project_id=?", (project_id,))}
    videos = {r["scene_id"]: r for r in conn.execute(
        "SELECT j.scene_id, j.id, j.input_hash, j.source_job_id, j.state FROM jobs j WHERE j.project_id=? AND j.type='video_gen'"
        f" AND j.state IN {USABLE_VIDEO + ('pending_review',)} AND j.id=(SELECT MAX(k.id) FROM jobs k WHERE k.scene_id=j.scene_id"
        f" AND k.type='video_gen' AND k.state IN {USABLE_VIDEO + ('pending_review',)})", (project_id,))}
    out = {}
    for s in scenes:
        data = json.loads(s["data"] or "{}")
        img, mp, vid = images.get(s["id"]), motions.get(s["id"]), videos.get(s["id"])
        image_stale = None
        if img is not None and img["input_hash"] and img["input_hash"] != image_spec_hash(data, cast_rows, aspect):
            image_stale = "nội dung cảnh / nhân vật / tỉ lệ khung đã đổi"
        motion_stale = None
        if mp is not None:
            if img is None:
                motion_stale = "ảnh của cảnh đã bị bỏ duyệt"
            elif mp["image_job_id"] and mp["image_job_id"] != img["id"]:
                motion_stale = "ảnh đã được thay"
            elif mp["spec_hash"] and mp["spec_hash"] != motion_spec_hash(data):
                motion_stale = "thoại / ý đồ cảnh đã đổi"
            elif image_stale:
                motion_stale = "ảnh đang cũ"
        video_stale = None
        if vid is not None:
            if img is None:
                video_stale = "ảnh của cảnh đã bị bỏ duyệt"
            elif vid["source_job_id"] and vid["source_job_id"] != img["id"]:
                video_stale = "làm từ ảnh cũ"
            elif mp is None:
                video_stale = "motion prompt đã bị xóa"
            elif vid["input_hash"] and vid["input_hash"] != video_input_hash(mp, aspect):
                video_stale = "motion prompt / thời lượng đã đổi"
            elif motion_stale or image_stale:
                video_stale = "ảnh hoặc motion prompt đang cũ"
        out[s["id"]] = {"idx": s["idx"], "image_job_id": img["id"] if img else None, "image_stale": image_stale,
                        "motion_state": mp["state"] if mp else None, "motion_stale": motion_stale,
                        "video_job_id": vid["id"] if vid else None, "video_state": vid["state"] if vid else None,
                        "video_stale": video_stale}
    return out


def summary(conn, project_id: int) -> Dict:
    """Counts per stage over scenes: done (fresh), stale, total — for the step bar and progress lines."""
    rows = scan(conn, project_id).values()
    total = len(rows)
    img_done = sum(1 for r in rows if r["image_job_id"] and not r["image_stale"])
    img_stale = sum(1 for r in rows if r["image_stale"])
    mot_done = sum(1 for r in rows if r["motion_state"] == "approved" and not r["motion_stale"])
    mot_stale = sum(1 for r in rows if r["motion_stale"])
    vid_done = sum(1 for r in rows if r["video_state"] in USABLE_VIDEO and not r["video_stale"])
    vid_stale = sum(1 for r in rows if r["video_stale"])
    return {"total": total, "images": (img_done, img_stale), "motion": (mot_done, mot_stale), "videos": (vid_done, vid_stale)}


def stale_scene_ids(conn, project_id: int) -> List[int]:
    return [sid for sid, r in scan(conn, project_id).items() if r["image_stale"] or r["motion_stale"] or r["video_stale"]]


# ---- final render and the layers made from it -------------------------------------------------------------------------
def _mtime(path: Optional[str]) -> Optional[float]:
    try:
        return round(os.path.getmtime(path), 2) if path else None
    except OSError:
        return None


def clip_manifest(conn, data_dir: str, project_id: int, clip_paths: List[str]) -> List[Dict]:
    """For each clip path in the render: which scene / video job it is and the file time (a regenerated clip overwrites the
    same file name, so the time tells the versions apart)."""
    by_path = {}
    for r in conn.execute("SELECT id, idx FROM scenes WHERE project_id=?", (project_id,)):
        by_path[os.path.normcase(os.path.abspath(os.path.join(data_dir, str(project_id), "videos", f"{r['idx']:02d}.mp4")))] = r
    out = []
    for path in clip_paths:
        scene = by_path.get(os.path.normcase(os.path.abspath(path)))
        job = None
        if scene is not None:
            job = conn.execute(f"SELECT id FROM jobs WHERE scene_id=? AND type='video_gen' AND state IN {USABLE_VIDEO}"
                               " ORDER BY id DESC LIMIT 1", (scene["id"],)).fetchone()
        out.append({"path": path, "scene_id": scene["id"] if scene else None, "idx": scene["idx"] if scene else None,
                    "video_job_id": job["id"] if job else None, "mtime": _mtime(path)})
    return out


def settings_hash(settings: Dict) -> str:
    return _hash(settings)


def latest_output(conn, project_id: int, kind: str):
    return conn.execute("SELECT * FROM outputs WHERE project_id=? AND kind=? ORDER BY id DESC LIMIT 1", (project_id, kind)).fetchone()


def final_status(conn, data_dir: str, project_id: int, current_settings_hash: Optional[str] = None,
                 current_audio_hash: Optional[str] = None) -> Dict:
    """{"state": "missing"|"fresh"|"stale", "reasons": [...], "output_id", "path"} of the latest final render."""
    row = latest_output(conn, project_id, "final")
    if row is None or not os.path.exists(row["path"]):
        legacy = os.path.join(data_dir, str(project_id), "output", "FINAL_VIDEO.mp4")
        if row is None and os.path.exists(legacy):
            return {"state": "fresh", "reasons": [], "output_id": None, "path": legacy}   # rendered before v2: nothing to compare with
        return {"state": "missing", "reasons": [], "output_id": None, "path": None}
    man = json.loads(row["manifest"] or "{}")
    reasons = []
    stale = scan(conn, project_id)
    for c in man.get("clips", []):
        if c.get("path") and _mtime(c["path"]) != c.get("mtime"):
            reasons.append(f"clip cảnh {c.get('idx')} đã thay")
        elif c.get("scene_id") and (stale.get(c["scene_id"]) or {}).get("video_stale"):
            reasons.append(f"clip cảnh {c.get('idx')} đang cũ")
    in_render = {c.get("scene_id") for c in man.get("clips", [])}
    new = [r["idx"] for sid, r in stale.items() if sid not in in_render and r["video_state"] in USABLE_VIDEO
           and not r["video_stale"]]
    if new:
        reasons.append("có clip mới chưa ghép: cảnh " + ", ".join(str(i) for i in sorted(new)))
    if current_settings_hash and man.get("settings_hash") and current_settings_hash != man["settings_hash"]:
        reasons.append("thiết lập dựng đã đổi")
    if current_audio_hash and man.get("audio_hash") and current_audio_hash != man["audio_hash"]:
        reasons.append("nhạc / hiệu ứng / giọng đọc đã đổi")
    return {"state": "stale" if reasons else "fresh", "reasons": reasons, "output_id": row["id"], "path": row["path"]}


def layer_status(conn, output_row, final_state: Dict) -> Optional[str]:
    """Reason a subtitle / end card / export is outdated, else None: its parent is not the latest version, or the final is stale."""
    if output_row is None:
        return None
    parent = output_row["parent_id"]
    if output_row["kind"] in ("subtitle", "endcard", "export") and parent is not None:
        chain = [parent]
        while chain[-1] is not None:
            r = conn.execute("SELECT parent_id FROM outputs WHERE id=?", (chain[-1],)).fetchone()
            chain.append(r["parent_id"] if r else None)
        if final_state.get("output_id") and final_state["output_id"] not in chain:
            return "video cuối đã được dựng lại"
    if final_state.get("state") == "stale":
        return "video cuối đang cũ"
    return None
