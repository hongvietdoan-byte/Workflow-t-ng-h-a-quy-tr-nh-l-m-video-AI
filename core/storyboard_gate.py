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
    return conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved' ORDER BY id DESC LIMIT 1",
                        (scene_id,)).fetchone()


def _scores(conn, job_id: int) -> Dict[str, float]:
    return {r["criterion"]: r["score"] for r in conn.execute("SELECT criterion, score FROM qc_results WHERE job_id=? ORDER BY id",
                                                             (job_id,))}


def _cast(data: Dict) -> List[str]:
    return [str(c) for c in data.get("characters") or []]


def flags(p: Pipeline, project_id: int) -> Dict[int, List[str]]:
    """{scene_id: [what looks wrong]} for every shot (empty list = nothing flagged)."""
    from . import shots
    floors = hard_floors("image")
    rows = p.conn.execute("SELECT id, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall()
    data = {r["id"]: json.loads(r["data"] or "{}") for r in rows}
    out: Dict[int, List[str]] = {}
    for r in rows:
        sid = r["id"]
        own = shots.image_scene(p.conn, sid)
        found: List[str] = []
        if own != sid:                              # later shot of a Kling multi-shot group: the clip only sees the group's picture
            missing = [c for c in _cast(data[sid]) if c not in _cast(data.get(own, {}))]
            if missing:
                found.append("ảnh đầu nhóm không có " + ", ".join(missing))
        else:
            img = _approved_image(p.conn, sid)
            if img is None:
                found.append("chưa có ảnh đã duyệt")
            else:
                sc = _scores(p.conn, img["id"])
                found += [f"{LABELS.get(k, k)} {v:.2f} dưới mức sàn" for k, v in sc.items() if k in floors and v < floors[k]]
                found += [f"{LABELS.get(k, k)} {v:.2f}" for k, v in sc.items() if k in FRAMING and v < VISIBLE]
        out[sid] = found
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


def summary(p: Pipeline, project_id: int) -> str:
    f = flags(p, project_id)
    bad = sum(1 for v in f.values() if v)
    return f"{bad}/{len(f)} shot có cờ cần xem" if bad else f"{len(f)} shot, không có cờ"
