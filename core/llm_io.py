"""Validation + persistence for JSON produced by the LLM (Director / QC Agent).

V0: the JSON is pasted from a Claude Desktop chat; V1: it comes from the API runner.
Either way it passes through the same validators, so the runner is swappable.
"""
import json
from typing import Any, Dict, List, Mapping, Optional

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


SCENE_FIELDS = ("location", "time", "mood", "lighting", "shot", "image_prompt")


def update_scene(pipeline: Pipeline, project_id: int, idx: int, fields: Mapping[str, Any],
                 text: Optional[str] = None) -> None:
    """Edit one scene's spec (and optionally its script text). `characters` must be names from the Character Bible.
    Images already generated keep the old look; only images generated afterwards use the new spec."""
    conn = pipeline.conn
    row = conn.execute("SELECT id, data FROM scenes WHERE project_id=? AND idx=?", (project_id, idx)).fetchone()
    if row is None:
        raise KeyError(f"scene {idx} does not exist")
    data = json.loads(row["data"] or "{}")
    for key in SCENE_FIELDS:
        if key in fields:
            value = fields[key]
            if not isinstance(value, str):
                raise SchemaError(f"{key}: expected text")
            data[key] = value.strip()
    if "image_prompt" in fields and not data.get("image_prompt"):
        raise SchemaError("image_prompt must not be empty")
    if "characters" in fields:
        names = {r["name"] for r in conn.execute("SELECT name FROM characters WHERE project_id=?", (project_id,))}
        cast = list(fields["characters"] or [])
        unknown = [c for c in cast if c not in names]
        if unknown:
            raise SchemaError(f"characters: {', '.join(unknown)} not in Character Bible")
        data["characters"] = cast
    if text is not None:
        data["text"] = text.strip()
    conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), row["id"]))
    conn.commit()


def update_character(pipeline: Pipeline, project_id: int, name: str, description: str,
                     wardrobe: Optional[str] = None, new_name: Optional[str] = None) -> None:
    """Edit one Character Bible entry (only while unlocked). A rename also updates the scene cast lists."""
    conn = pipeline.conn
    row = conn.execute("SELECT id, locked FROM characters WHERE project_id=? AND name=?", (project_id, name)).fetchone()
    if row is None:
        raise KeyError(f"character '{name}' does not exist")
    if row["locked"]:
        raise ValueError(f"character '{name}' is locked; unlock the Character Bible first")
    description = (description or "").strip()
    if not description:
        raise ValueError("description must not be empty")
    new_name = (new_name or name).strip()
    if not new_name:
        raise ValueError("name must not be empty")
    if new_name != name and conn.execute("SELECT 1 FROM characters WHERE project_id=? AND name=?",
                                         (project_id, new_name)).fetchone():
        raise ValueError(f"a character named '{new_name}' already exists")
    conn.execute("UPDATE characters SET name=?, description=?, wardrobe=? WHERE id=?",
                 (new_name, description, (wardrobe or "").strip() or None, row["id"]))
    if new_name != name:
        for scene in conn.execute("SELECT id, data FROM scenes WHERE project_id=?", (project_id,)).fetchall():
            data = json.loads(scene["data"] or "{}")
            cast = data.get("characters")
            if cast and name in cast:
                data["characters"] = [new_name if c == name else c for c in cast]
                conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), scene["id"]))
    conn.commit()


def unlock_character_bible(pipeline: Pipeline, project_id: int) -> int:
    """Allow editing again. Images already generated keep the old look; the caller should warn about that."""
    n = pipeline.conn.execute("UPDATE characters SET locked=0 WHERE project_id=?", (project_id,)).rowcount
    pipeline.conn.commit()
    return n


def store_motion_prompts(pipeline: Pipeline, project_id: int, data: Any) -> int:
    """Step 3: save motion prompts for scenes that have an approved image. Editing resets approval."""
    obj = validate_motion_prompts(data)
    conn = pipeline.conn
    for s in obj["scenes"]:
        row = conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?",
                           (project_id, s["idx"])).fetchone()
        if row is None:
            raise SchemaError(f"scene idx {s['idx']} does not exist in project {project_id}")
        approved = conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'",
                                (row["id"],)).fetchone()
        if approved is None:
            raise SchemaError(f"scene idx {s['idx']} has no approved image yet")
        conn.execute(
            "INSERT INTO motion_prompts (scene_id, motion_prompt, camera, duration_sec, negative_prompt, state)"
            " VALUES (?,?,?,?,?,'pending') ON CONFLICT(scene_id) DO UPDATE SET"
            " motion_prompt=excluded.motion_prompt, camera=excluded.camera,"
            " duration_sec=excluded.duration_sec, negative_prompt=excluded.negative_prompt, state='pending'",
            (row["id"], s["motion_prompt"], s.get("camera"), s.get("duration_sec", 5), s.get("negative_prompt")))
    conn.commit()
    return len(obj["scenes"])


def approve_motion_prompt(pipeline: Pipeline, scene_id: int) -> None:
    n = pipeline.conn.execute("UPDATE motion_prompts SET state='approved' WHERE scene_id=?", (scene_id,)).rowcount
    if n == 0:
        raise SchemaError(f"scene {scene_id} has no motion prompt")
    pipeline.conn.commit()


def ready_for_video(pipeline: Pipeline, project_id: int) -> List[Dict]:
    """Scenes with an approved motion prompt (input for the Step 4 video connector)."""
    rows = pipeline.conn.execute(
        "SELECT s.id AS scene_id, s.idx, m.motion_prompt, m.camera, m.duration_sec, m.negative_prompt"
        " FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id"
        " WHERE s.project_id=? AND m.state='approved' ORDER BY s.idx", (project_id,))
    return [dict(r) for r in rows]
