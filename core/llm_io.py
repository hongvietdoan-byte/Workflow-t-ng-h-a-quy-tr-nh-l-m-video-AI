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


GENRES = {"SHORT_FORM": "Video ngắn mạng xã hội", "COMMERCIAL": "Quảng cáo / trailer", "CINEMA_DRAMA": "Phim / kịch tính",
          "MUSIC_VIDEO": "Music video", "ANIMATION": "Hoạt hình"}
SHOT_ROLES = ("hero", "normal", "transition")
COMPLEXITY = ("simple", "complex")


def validate_scene_analysis(data: Any) -> Dict:
    """Director JSON. v2 adds optional fields (from the film-director skill contract); JSON without them stays valid:
    root `genre`; per character `lock` {must_keep, may_change, forbidden}; per scene `emotional_intent`, `beat`
    {want, obstacle, turn}, `camera_complexity` simple|complex, `shot_role` hero|normal|transition, `dialogue`
    [{speaker, text}], `duration_s` (1-30; each model clamps to its own limit)."""
    obj = _load(data)
    if obj.get("genre") is not None and not isinstance(obj.get("genre"), str):
        raise SchemaError("root.genre: expected text")
    chars = _req(obj, "characters", list, "root")
    for i, c in enumerate(chars):
        w = f"characters[{i}]"
        _req(c, "name", str, w)
        _req(c, "description", str, w)
        if c.get("lock") is not None:
            _check_lock(c["lock"], f"{w}.lock")
    names = {c["name"] for c in chars}
    scenes = _req(obj, "scenes", list, "root")
    for i, s in enumerate(scenes):
        w = f"scenes[{i}]"
        _req(s, "idx", int, w)
        for key in ("location", "time", "mood", "lighting", "shot", "image_prompt"):
            _req(s, key, str, w)
        _check_location_asset(s.get("location_asset"), w)
        _check_sequence(s.get("sequence"), w)
        for key in ("blocking", "emotional_intent"):
            if s.get(key) is not None and not isinstance(s.get(key), str):
                raise SchemaError(f"{w}.{key}: expected text")
        _check_choice(s.get("camera_complexity"), COMPLEXITY, f"{w}.camera_complexity")
        _check_choice(s.get("shot_role"), SHOT_ROLES, f"{w}.shot_role")
        _check_beat(s.get("beat"), f"{w}.beat")
        _check_dialogue(s.get("dialogue"), f"{w}.dialogue")
        _check_duration(s.get("duration_s"), f"{w}.duration_s")
        for name in _req(s, "characters", list, w):
            if name not in names:
                raise SchemaError(f"{w}.characters: '{name}' not in Character Bible")
    return obj


def _check_choice(value: Any, allowed, where: str) -> None:
    if value is not None and value not in allowed:
        raise SchemaError(f"{where}: must be one of {', '.join(allowed)} or null")


def _check_beat(value: Any, where: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict) or any(k not in ("want", "obstacle", "turn") or not isinstance(v, str) for k, v in value.items()):
        raise SchemaError(f"{where}: expected {{want, obstacle, turn}} as text")


def _check_dialogue(value: Any, where: str) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        raise SchemaError(f"{where}: expected a list of {{speaker, text}}")
    for j, d in enumerate(value):
        if not isinstance(d, dict) or not isinstance(d.get("speaker", ""), str) or not isinstance(d.get("text"), str) \
                or not d["text"].strip():
            raise SchemaError(f"{where}[{j}]: expected {{speaker, text}} with non-empty text")


def _check_duration(value: Any, where: str) -> None:
    if value is None:
        return
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 1 <= value <= 30:
        raise SchemaError(f"{where}: must be a number of seconds between 1 and 30")


LOCK_KEYS = ("must_keep", "may_change", "forbidden")


def _check_lock(value: Any, where: str) -> None:
    """Character Lock (game-character-consistency-designer skill): traits that must never change, what may vary per shot,
    and the drifts that are forbidden."""
    if not isinstance(value, dict) or any(k not in LOCK_KEYS or not isinstance(v, str) for k, v in value.items()):
        raise SchemaError(f"{where}: expected {{must_keep, may_change, forbidden}} as text")


def _check_location_asset(value: Any, where: str) -> None:
    """`location_asset` is optional: null, or the id (a positive whole number) of a place in the resource library."""
    if value is None:
        return
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise SchemaError(f"{where}.location_asset: must be null or a resource id (positive whole number)")


def _check_sequence(value: Any, where: str) -> None:
    """`sequence` is optional: null, or a positive whole number shared by consecutive scenes in the same place/continuous action."""
    if value is None:
        return
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise SchemaError(f"{where}.sequence: must be null or a positive whole number")


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
    """v2: optional `check_flags` (list of short warnings the model raises about its own prompt, motion-director skill) and
    `spatial_state` (where everyone ends up, carried to the next shot of the same sequence)."""
    obj = _load(data)
    for i, s in enumerate(_req(obj, "scenes", list, "root")):
        w = f"scenes[{i}]"
        _req(s, "idx", int, w)
        _req(s, "motion_prompt", str, w)
        dur = s.get("duration_sec", 5)
        if not isinstance(dur, (int, float)) or not 1 <= dur <= 30:
            raise SchemaError(f"{w}.duration_sec: must be between 1 and 30")
        flags = s.get("check_flags")
        if flags is not None and (not isinstance(flags, list) or not all(isinstance(f, str) for f in flags)):
            raise SchemaError(f"{w}.check_flags: expected a list of text")
        if s.get("spatial_state") is not None and not isinstance(s.get("spatial_state"), str):
            raise SchemaError(f"{w}.spatial_state: expected text")
    return obj


# ---- persistence -------------------------------------------------------
DIRECTOR_KEYS = ("location", "time", "characters", "mood", "lighting", "shot", "image_prompt", "location_asset", "sequence",
                 "blocking", "emotional_intent", "beat", "camera_complexity", "shot_role", "dialogue", "duration_s")


def _empty(value: Any) -> bool:
    return value is None or (isinstance(value, (str, list, dict)) and not value)


def store_scene_analysis(pipeline: Pipeline, project_id: int, data: Any) -> Dict:
    """Save the Director's analysis. Never overwrites what the person set by hand: a field listed in the scene's `_user_locked`
    is kept, and an empty / null value from the Director never replaces a value that is there (re-running the Director used to
    wipe a hand-picked Background). A locked character keeps its description; a Character Lock is only filled in when empty."""
    obj = validate_scene_analysis(data)
    conn = pipeline.conn
    for c in obj["characters"]:
        conn.execute(
            "INSERT INTO characters (project_id, name, description, wardrobe) VALUES (?,?,?,?)"
            " ON CONFLICT(project_id, name) DO UPDATE SET description=excluded.description,"
            " wardrobe=excluded.wardrobe WHERE locked=0",
            (project_id, c["name"], c["description"], c.get("wardrobe")))
        if c.get("lock"):
            conn.execute("UPDATE characters SET lock_rules=? WHERE project_id=? AND name=? AND (lock_rules IS NULL OR lock_rules='')",
                         (json.dumps({k: c["lock"].get(k, "") for k in LOCK_KEYS}, ensure_ascii=False), project_id, c["name"]))
    if obj.get("genre"):
        conn.execute("UPDATE projects SET genre=? WHERE id=? AND genre_locked=0", (obj["genre"].strip().upper(), project_id))
    for s in obj["scenes"]:
        row = conn.execute("SELECT id, data FROM scenes WHERE project_id=? AND idx=?",
                           (project_id, s["idx"])).fetchone()
        if row is None:
            raise SchemaError(f"scene idx {s['idx']} does not exist in project {project_id}")
        merged = json.loads(row["data"] or "{}")
        locked = set(merged.get("_user_locked") or [])
        for key in DIRECTOR_KEYS:
            if key not in s or key in locked:
                continue
            if _empty(s[key]) and not _empty(merged.get(key)):
                continue
            merged[key] = s[key]
        conn.execute("UPDATE scenes SET data=? WHERE id=?",
                     (json.dumps(merged, ensure_ascii=False), row["id"]))
    conn.commit()
    return obj


def locked_fields(conn, project_id: int) -> List[Dict]:
    """[{idx, fields: {key: value}}] the person set by hand — told to the Director so it plans around them."""
    out = []
    for r in conn.execute("SELECT idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)):
        d = json.loads(r["data"] or "{}")
        keys = [k for k in d.get("_user_locked") or [] if k in d]
        if keys:
            out.append({"idx": r["idx"], "fields": {k: d[k] for k in keys}})
    return out


def unlock_scene_fields(pipeline: Pipeline, project_id: int, idx: int, keys: Optional[List[str]] = None) -> None:
    """Let the Director fill these fields again (all of them when keys is None)."""
    conn = pipeline.conn
    row = conn.execute("SELECT id, data FROM scenes WHERE project_id=? AND idx=?", (project_id, idx)).fetchone()
    if row is None:
        raise KeyError(f"scene {idx} does not exist")
    data = json.loads(row["data"] or "{}")
    data["_user_locked"] = [] if keys is None else [k for k in data.get("_user_locked") or [] if k not in keys]
    conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), row["id"]))
    conn.commit()


def lock_character_bible(pipeline: Pipeline, project_id: int) -> int:
    """Approve & Lock (Step 1): freeze characters and mark scenes 'ready' for image generation."""
    conn = pipeline.conn
    conn.execute("UPDATE characters SET locked=1 WHERE project_id=?", (project_id,))
    n = conn.execute("UPDATE scenes SET state='ready' WHERE project_id=? AND state!='needs_attention'",
                     (project_id,)).rowcount
    conn.commit()
    return n


SCENE_FIELDS = ("location", "time", "mood", "lighting", "shot", "image_prompt", "blocking", "emotional_intent")


def update_scene(pipeline: Pipeline, project_id: int, idx: int, fields: Mapping[str, Any],
                 text: Optional[str] = None) -> List[str]:
    """Edit one scene's spec (and optionally its script text). `characters` must be names from the Character Bible.
    Every field whose value really changes is remembered as set by hand (`_user_locked`), so a later Director run keeps it.
    Results made from the old spec are then shown as outdated (core.lineage). Returns the changed field names."""
    conn = pipeline.conn
    row = conn.execute("SELECT id, data FROM scenes WHERE project_id=? AND idx=?", (project_id, idx)).fetchone()
    if row is None:
        raise KeyError(f"scene {idx} does not exist")
    data = json.loads(row["data"] or "{}")
    before = json.loads(row["data"] or "{}")
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
    if "location_asset" in fields:
        _check_location_asset(fields["location_asset"], "scene")
        data["location_asset"] = fields["location_asset"]
    if "sequence" in fields:
        _check_sequence(fields["sequence"], "scene")
        data["sequence"] = fields["sequence"]
    if "camera_complexity" in fields:
        _check_choice(fields["camera_complexity"] or None, COMPLEXITY, "camera_complexity")
        data["camera_complexity"] = fields["camera_complexity"] or None
    if "shot_role" in fields:
        _check_choice(fields["shot_role"] or None, SHOT_ROLES, "shot_role")
        data["shot_role"] = fields["shot_role"] or None
    if "duration_s" in fields:
        _check_duration(fields["duration_s"] or None, "duration_s")
        data["duration_s"] = fields["duration_s"] or None
    if "dialogue" in fields:
        rows = [d for d in (fields["dialogue"] or []) if isinstance(d, dict) and str(d.get("text") or "").strip()]
        rows = [{"speaker": str(d.get("speaker") or "").strip(), "text": str(d["text"]).strip()} for d in rows]
        _check_dialogue(rows, "dialogue")
        data["dialogue"] = rows or None
    if text is not None:
        data["text"] = text.strip()
        if (data["text"] != (before.get("text") or "") and "dialogue" not in fields
                and "dialogue" not in set(data.get("_user_locked") or [])):
            from .dialogue import lines as _lines         # script text changed: the structured dialogue follows it
            rows = _lines(data["text"])
            data["dialogue"] = [{"speaker": w, "text": t} for w, t in rows] or None
    changed = [k for k in set(before) | set(data) if k not in ("_user_locked", "text") and before.get(k) != data.get(k)
               and not (k == "dialogue" and "dialogue" not in fields)]
    data["_user_locked"] = sorted(set(data.get("_user_locked") or []) | set(changed))
    conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), row["id"]))
    conn.commit()
    return sorted(changed)


def add_character(pipeline: Pipeline, project_id: int, name: str, description: str,
                  wardrobe: Optional[str] = None) -> None:
    """Add an entry to the Character Bible by hand: not only people, also creatures, mascots, props or anything else
    that must look the same in every scene. New entries start unlocked."""
    name, description = (name or "").strip(), (description or "").strip()
    if not name or not description:
        raise ValueError("name and description must not be empty")
    if pipeline.conn.execute("SELECT 1 FROM characters WHERE project_id=? AND name=?", (project_id, name)).fetchone():
        raise ValueError(f"'{name}' already exists in the Character Bible")
    pipeline.conn.execute("INSERT INTO characters (project_id, name, description, wardrobe) VALUES (?,?,?,?)",
                          (project_id, name, description, (wardrobe or "").strip() or None))
    pipeline.conn.commit()


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
        scene_data = json.loads(conn.execute("SELECT data FROM scenes WHERE id=?", (row["id"],)).fetchone()["data"] or "{}")
        duration = s.get("duration_sec") or scene_data.get("duration_s") or 5
        if "duration_s" in set(scene_data.get("_user_locked") or []) and scene_data.get("duration_s"):
            duration = scene_data["duration_s"]          # length the person set (e.g. sized to the dialogue) wins
        conn.execute(
            "INSERT INTO motion_prompts (scene_id, motion_prompt, camera, duration_sec, negative_prompt, state, check_flags)"
            " VALUES (?,?,?,?,?,'pending',?) ON CONFLICT(scene_id) DO UPDATE SET"
            " motion_prompt=excluded.motion_prompt, camera=excluded.camera,"
            " duration_sec=excluded.duration_sec, negative_prompt=excluded.negative_prompt, state='pending',"
            " check_flags=excluded.check_flags, lint=NULL",
            (row["id"], s["motion_prompt"], s.get("camera"), duration, s.get("negative_prompt"),
             json.dumps(s.get("check_flags") or [], ensure_ascii=False)))
        if s.get("spatial_state"):
            scene_data["spatial_state"] = s["spatial_state"]
            conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(scene_data, ensure_ascii=False), row["id"]))
        from .lineage import stamp_motion
        stamp_motion(conn, row["id"])
    conn.commit()
    return len(obj["scenes"])


def approve_motion_prompt(pipeline: Pipeline, scene_id: int) -> None:
    """A person (or the automatic run) accepts the prompt as valid for the scene's current image and spec."""
    n = pipeline.conn.execute("UPDATE motion_prompts SET state='approved' WHERE scene_id=?", (scene_id,)).rowcount
    if n == 0:
        raise SchemaError(f"scene {scene_id} has no motion prompt")
    from .lineage import stamp_motion
    stamp_motion(pipeline.conn, scene_id)
    pipeline.conn.commit()


def ready_for_video(pipeline: Pipeline, project_id: int, include_stale: bool = False) -> List[Dict]:
    """Scenes with an approved motion prompt that is still valid for the scene's current image (input for Step 4). A prompt
    written for an image that has since been replaced, or for a changed scene, is left out until it is redone."""
    from .lineage import scan
    stale = {sid for sid, r in scan(pipeline.conn, project_id).items() if r["motion_stale"]} if not include_stale else set()
    rows = pipeline.conn.execute(
        "SELECT s.id AS scene_id, s.idx, m.motion_prompt, m.camera, m.duration_sec, m.negative_prompt"
        " FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id"
        " WHERE s.project_id=? AND m.state='approved' ORDER BY s.idx", (project_id,))
    return [dict(r) for r in rows if r["scene_id"] not in stale]
