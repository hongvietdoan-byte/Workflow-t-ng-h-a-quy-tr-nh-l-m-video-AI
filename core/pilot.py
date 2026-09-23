"""Pilot before the batch (game-asset-set-generator skill: "pilot run of 3-5 assets"): generate a few representative scenes first,
let the person (or QC) confirm the look, then the rest. Saves credit when a style / character problem would repeat in every scene."""
import json
from typing import Dict, List

from .pipeline import Pipeline

MIN_SCENES = 6          # below this a pilot saves little
SIZE = 3


def get(p: Pipeline, project_id: int) -> Dict:
    try:
        data = json.loads(p.project(project_id)["pilot"] or "{}")
    except (ValueError, KeyError, IndexError, TypeError):
        data = {}
    return {"enabled": bool(data.get("enabled")), "scenes": list(data.get("scenes") or []), "released": bool(data.get("released"))}


def save(p: Pipeline, project_id: int, state: Dict) -> None:
    p.set_project_field(project_id, "pilot", json.dumps(state, ensure_ascii=False))


def pick(p: Pipeline, project_id: int, size: int = SIZE) -> List[int]:
    """Representative scenes: the 'hero' ones first, then the first shot of each sequence, then the first scenes."""
    rows = p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall()
    chosen: List[int] = []
    for r in rows:
        if json.loads(r["data"] or "{}").get("shot_role") == "hero" and len(chosen) < size:
            chosen.append(r["id"])
    seen = set()
    for r in rows:
        seq = json.loads(r["data"] or "{}").get("sequence")
        if seq and seq not in seen and r["id"] not in chosen and len(chosen) < size:
            seen.add(seq)
            chosen.append(r["id"])
    for r in rows:
        if r["id"] not in chosen and len(chosen) < size:
            chosen.append(r["id"])
    return chosen


def active(p: Pipeline, project_id: int) -> bool:
    """A pilot is running: only its scenes may be generated until the person releases the rest."""
    state = get(p, project_id)
    return state["enabled"] and not state["released"] and bool(state["scenes"])


def start(p: Pipeline, project_id: int) -> List[int]:
    scenes = pick(p, project_id)
    save(p, project_id, {"enabled": True, "scenes": scenes, "released": False})
    return scenes


def release(p: Pipeline, project_id: int) -> None:
    state = get(p, project_id)
    state["released"] = True
    save(p, project_id, state)


def done(p: Pipeline, project_id: int) -> bool:
    """Every pilot scene has an approved picture."""
    state = get(p, project_id)
    if not state["scenes"]:
        return False
    for sid in state["scenes"]:
        if not p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'", (sid,)).fetchone():
            return False
    return True


def allowed_scenes(p: Pipeline, project_id: int, scene_ids: List[int]) -> List[int]:
    if not active(p, project_id):
        return scene_ids
    keep = set(get(p, project_id)["scenes"])
    return [s for s in scene_ids if s in keep]
