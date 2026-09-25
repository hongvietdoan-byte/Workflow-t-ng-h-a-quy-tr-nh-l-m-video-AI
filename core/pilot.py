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


_SIZE_CLASS = {"ECU": "close", "CU": "close", "MCU": "close", "MS": "medium", "MLS": "medium", "WS": "wide", "EWS": "wide",
               "GAME_TPS": "wide"}


def _traits(data: Dict) -> Dict[str, set]:
    """What a shot would test if it were in the pilot: its people, its place and its kind of framing."""
    place = data.get("location_asset") or (data.get("location") or "").strip().lower()
    size = _SIZE_CLASS.get(str(data.get("size") or data.get("shot_size") or "").upper(), "")
    return {"people": {str(c).upper() for c in (data.get("characters") or [])}, "place": {str(place)} if place else set(),
            "size": {size} if size else set()}


def pick(p: Pipeline, project_id: int, size: int = SIZE) -> List[int]:
    """W2: the few shots that test the most — every main character, every place and close / medium / wide framing at least once
    (a problem with a character, a place or a framing repeats in every shot that has it). Greedy: each next shot is the one that
    adds the most not yet covered (people count double, then places, then framing; a 'hero' shot wins a tie, then the earlier
    shot); when nothing new is left, the first shots of each sequence, then the first shots."""
    rows = p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall()
    info = [(r, json.loads(r["data"] or "{}")) for r in rows]
    covered = {"people": set(), "place": set(), "size": set()}
    chosen: List[int] = []
    while len(chosen) < size:
        best, best_score = None, 0.0
        for r, data in info:
            if r["id"] in chosen:
                continue
            t = _traits(data)
            score = (2 * len(t["people"] - covered["people"]) + 1.5 * len(t["place"] - covered["place"])
                     + len(t["size"] - covered["size"]))
            if score and data.get("shot_role") == "hero":
                score += 0.5
            if score > best_score:
                best, best_score = (r, t), score
        if best is None:
            break
        chosen.append(best[0]["id"])
        for k in covered:
            covered[k] |= best[1][k]
    seen = set()
    for r, data in info:
        seq = data.get("sequence")
        if seq and seq not in seen and r["id"] not in chosen and len(chosen) < size:
            seen.add(seq)
            chosen.append(r["id"])
    for r, _ in info:
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
