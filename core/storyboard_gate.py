"""Storyboard checkpoint (W1, docs/PHAN_TICH_VONG_DASHBOARD_2026-09-24.md): before any video credit is spent, a person looks at every
start picture at once. Real run GĐ6: ~70% of the real video money bought clips made from pictures whose fault was visible BEFORE the
video (wrong character, wrong shot size, a multi-shot group whose first picture lacks people of the later shots) — and most of those
clips went into the final cut.

`flags()` marks what the person should look at first; `fingerprint()` identifies the set of pictures the person approved, so a
picture changed afterwards (redo, set check) puts the checkpoint back up.
"""
import json
from typing import Dict, List

from .pipeline import Pipeline, hard_floors

VISIBLE = 0.6                                   # framing / scale / set scores below this are plain to see on the picture
FRAMING = ("composition", "set_match", "scale")
LABELS = {"character": "nhân vật", "hands_face": "tay/mặt", "grounding": "chân chạm đất", "composition": "bố cục/cỡ cảnh",
          "set_match": "khớp bối cảnh", "scale": "tỉ lệ"}


def _approved_image(conn, scene_id: int):
    """The picture the storyboard shows: the approved one, else one held for the person (below a floor, W15)."""
    return (conn.execute("SELECT id, state FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved' ORDER BY id DESC LIMIT 1",
                         (scene_id,)).fetchone()
            or conn.execute("SELECT id, state FROM jobs WHERE scene_id=? AND type='image_gen' AND state='pending_review' ORDER BY id DESC"
                            " LIMIT 1", (scene_id,)).fetchone())


def picture_path(conn, data_dir: str, project_id: int, scene_id: int):
    """(path, held) of the picture shown for this shot, or (None, False)."""
    import os
    img = _approved_image(conn, scene_id)
    path = img and os.path.join(data_dir, str(project_id), "images", f"job_{img['id']}.png")
    return (path, img["state"] == "pending_review") if path and os.path.exists(path) else (None, False)


def _scores(conn, job_id: int) -> Dict[str, float]:
    return {r["criterion"]: r["score"] for r in conn.execute("SELECT criterion, score FROM qc_results WHERE job_id=? ORDER BY id",
                                                             (job_id,))}


def _cast(data: Dict) -> List[str]:
    return [str(c) for c in data.get("characters") or []]


CLOSE_SIZES = ("ECU", "CU", "MCU")
FACING_ANGLES = ("eye", "low", "high", "dutch")   # the speaker's face is seen (not ots / pov / overhead)


def lip_sync_risk(shot: Dict) -> bool:
    """AU-g: a close shot where a speaker of the line is on screen, face seen — there is no lip sync (the Vietnamese voice is laid
    on afterwards), so moving lips that say something else are plain to see. Director is told to avoid it; this catches it."""
    lines = shot.get("dialogue") or []
    if not lines or str(shot.get("size") or "").upper() not in CLOSE_SIZES or (shot.get("angle") or "eye") not in FACING_ANGLES:
        return False
    from . import lipsync
    if lipsync.enabled() and lipsync.method_for(shot) != "skip":
        return False                                         # V4 GĐ3: this mouth is matched to the voice (generation or post)
    on_screen = {str(c).strip().upper() for c in shot.get("characters") or []}
    return any(str(d.get("speaker") or "").strip().upper() in on_screen for d in lines if isinstance(d, dict))


def flags(p: Pipeline, project_id: int, data_dir: str = None) -> Dict[int, List[str]]:
    """{scene_id: [what looks wrong]} for every shot (empty list = nothing flagged). With `data_dir`, the whole-set check's findings
    are shown too (it only reports: features.setcheck_autofix)."""
    from . import shots
    set_issues: Dict[int, List[str]] = {}
    if data_dir:
        from .claude_tasks import last_set_check
        for it in (last_set_check(data_dir, project_id) or {}).get("issues") or []:
            if isinstance(it, dict) and it.get("idx") is not None:
                set_issues.setdefault(int(it["idx"]), []).append("QC đồng bộ: " + str(it.get("problem") or "")[:160])
    floors = hard_floors("image")
    rows = p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall()
    data = {r["id"]: json.loads(r["data"] or "{}") for r in rows}
    out: Dict[int, List[str]] = {}
    for r in rows:
        sid = r["id"]
        own = shots.image_scene(p.conn, sid)
        found: List[str] = []
        if lip_sync_risk(data[sid]):
            found.append("cận mặt người đang nói — không có khớp môi (giọng lồng sau): nên góc nghiêng/sau lưng/xa hơn hoặc chèn phản ứng")
        if own != sid:                            # later shot of a Kling multi-shot group: the clip only sees the group's picture
            missing = [c for c in _cast(data[sid]) if c not in _cast(data.get(own, {}))]
            if missing:
                found.append("ảnh đầu nhóm không có " + ", ".join(missing))
        else:
            dur = float(data[sid].get("duration_s") or 0)
            if not data[sid].get("shot_no") and dur > 10:     # F6: one long clip with several beats — a retry cannot fix the middle
                found.append(f"clip dài {dur:.0f}s nhiều nhịp — nên chia shot (gen lại không sửa được nhịp giữa)")
            img = _approved_image(p.conn, sid)
            if img is None:
                found.append("chưa có ảnh đã duyệt")
            else:
                sc = _scores(p.conn, img["id"])
                if img["state"] == "pending_review":
                    found.append("chờ bạn duyệt (QC không tự duyệt)")
                found += [f"{LABELS.get(k, k)} {v:.2f} dưới mức sàn" for k, v in sc.items() if k in floors and v < floors[k]]
                found += [f"{LABELS.get(k, k)} {v:.2f}" for k, v in sc.items() if k in FRAMING and v < VISIBLE]
        out[sid] = found + set_issues.get(r["idx"], [])
    return out


def fingerprint(p: Pipeline, project_id: int) -> List[int]:
    """The approved start pictures the storyboard shows (one per shot that needs its own picture)."""
    from . import shots
    ids = []
    for r in p.conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)):
        if shots.needs_own_image(p.conn, r["id"]):
            img = _approved_image(p.conn, r["id"])
            ids.append(img["id"] if img else 0)
    return ids


def summary(p: Pipeline, project_id: int, data_dir: str = None) -> str:
    f = flags(p, project_id, data_dir)
    bad = sum(1 for v in f.values() if v)
    return f"{bad}/{len(f)} shot có cờ cần xem" if bad else f"{len(f)} shot, không có cờ"
