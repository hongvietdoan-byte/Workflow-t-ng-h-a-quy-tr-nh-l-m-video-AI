"""Validation + persistence for JSON produced by the LLM (Director / QC Agent).

V0: the JSON is pasted from a Claude Desktop chat; V1: it comes from the API runner.
Either way it passes through the same validators, so the runner is swappable.
"""
import json
from typing import Any, Dict, List, Mapping

from .pipeline import Pipeline


class SchemaError(ValueError):
    pass


def _req(obj: Mapping, key: str, typ, where: str):
    if key not in obj:
        raise SchemaError(f"{where}: missing '{key}'")
    if not isinstance(obj[key], typ) or isinstance(obj[key], bool) and typ is not bool:
        raise SchemaError(f"{where}.{key}: expected {typ.__name__ if isinstance(typ, type) else typ}")
    return obj[key]


def _load(data: Any) -> Dict:
    obj = json.loads(data) if isinstance(data, str) else data
    if not isinstance(obj, dict):
        raise SchemaError("root must be an object")
    return obj


def validate_scene_analysis(data: Any) -> Dict:
    obj = _load(data)
    chars = _req(obj, "characters", list, "root")
    for i, c in enumerate(chars):
        w = f"characters[{i}]"
        _req(c, "name", str, w)
        _req(c, "description", str, w)
    names = {c["name"] for c in chars}
    scenes = _req(obj, "scenes", list, "root")
    for i, s in enumerate(scenes):
        w = f"scenes[{i}]"
        _req(s, "idx", int, w)
        for key in ("location", "time", "mood", "lighting", "shot", "image_prompt"):
            _req(s, key, str, w)
        for name in _req(s, "characters", list, w):
            if name not in names:
                raise SchemaError(f"{w}.characters: '{name}' not in Character Bible")
    return obj


def validate_qc_result(data: Any, required_criteria: List[str]) -> Dict:
    obj = _load(data)
    criteria = _req(obj, "criteria", dict, "root")
    for name in required_criteria:
        if name not in criteria:
            raise SchemaError(f"criteria: missing '{name}'")
    for name, score in criteria.items():
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 1:
            raise SchemaError(f"criteria.{name}: score must be a number in [0, 1]")
    return obj


def validate_motion_prompts(data: Any) -> Dict:
    obj = _load(data)
    for i, s in enumerate(_req(obj, "scenes", list, "root")):
        w = f"scenes[{i}]"
        _req(s, "idx", int, w)
        _req(s, "motion_prompt", str, w)
        dur = s.get("duration_sec", 5)
        if not isinstance(dur, (int, float)) or not 1 <= dur <= 15:
            raise SchemaError(f"{w}.duration_sec: must be between 1 and 15")
    return obj


# ---- persistence -------------------------------------------------------
def store_scene_analysis(pipeline: Pipeline, project_id: int, data: Any) -> Dict:
    obj = validate_scene_analysis(data)
    conn = pipeline.conn
    for c in obj["characters"]:
        conn.execute(
            "INSERT INTO characters (project_id, name, description, wardrobe) VALUES (?,?,?,?)"
            " ON CONFLICT(project_id, name) DO UPDATE SET description=excluded.description,"
            " wardrobe=excluded.wardrobe WHERE locked=0",
            (project_id, c["name"], c["description"], c.get("wardrobe")))
    for s in obj["scenes"]:
        row = conn.execute("SELECT id, data FROM scenes WHERE project_id=? AND idx=?",
                           (project_id, s["idx"])).fetchone()
        if row is None:
            raise SchemaError(f"scene idx {s['idx']} does not exist in project {project_id}")
        merged = json.loads(row["data"] or "{}")
        merged.update({k: s[k] for k in ("location", "time", "characters", "mood", "lighting",
                                          "shot", "image_prompt")})
        conn.execute("UPDATE scenes SET data=? WHERE id=?",
                     (json.dumps(merged, ensure_ascii=False), row["id"]))
    conn.commit()
    return obj


def lock_character_bible(pipeline: Pipeline, project_id: int) -> int:
    """Approve & Lock (Step 1): freeze characters and mark scenes 'ready' for image generation."""
    conn = pipeline.conn
    conn.execute("UPDATE characters SET locked=1 WHERE project_id=?", (project_id,))
    n = conn.execute("UPDATE scenes SET state='ready' WHERE project_id=? AND state!='needs_attention'",
                     (project_id,)).rowcount
    conn.commit()
    return n
