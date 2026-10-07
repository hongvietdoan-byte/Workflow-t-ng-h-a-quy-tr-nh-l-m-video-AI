"""Validation + persistence for JSON produced by the LLM (Director / QC Agent).

V0: the JSON is pasted from a Claude Desktop chat; V1: it comes from the API runner.
Either way it passes through the same validators, so the runner is swappable.
"""
import json
from typing import Any, Dict, List, Mapping, Optional

from . import access
from .pipeline import Pipeline


class SchemaError(ValueError):
    pass


_TYPE_VI = {str: "chữ", int: "số nguyên", float: "số", list: "danh sách", dict: "object {…}", bool: "true/false"}


def _req(obj: Mapping, key: str, typ, where: str):
    if key not in obj:
        raise SchemaError(f"{where}: thiếu trường '{key}'")
    if not isinstance(obj[key], typ) or isinstance(obj[key], bool) and typ is not bool:
        raise SchemaError(f"{where}.{key}: sai kiểu — cần {_TYPE_VI.get(typ, getattr(typ, '__name__', typ))}")
    return obj[key]


def _load(data: Any) -> Dict:
    obj = json.loads(data) if isinstance(data, str) else data
    if not isinstance(obj, dict):
        raise SchemaError("gốc JSON phải là một object {…}")
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
        raise SchemaError("root.genre: cần chữ")
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
                raise SchemaError(f"{w}.{key}: cần chữ")
        _check_choice(s.get("camera_complexity"), COMPLEXITY, f"{w}.camera_complexity")
        _check_choice(s.get("shot_role"), SHOT_ROLES, f"{w}.shot_role")
        s["beat"] = _clean_beat(s.get("beat")) if "beat" in s else None
        if s["beat"] is None:
            s.pop("beat")
        _check_dialogue(s.get("dialogue"), f"{w}.dialogue")
        _check_duration(s.get("duration_s"), f"{w}.duration_s")
        for name in _req(s, "characters", list, w):
            if name not in names:
                raise SchemaError(f"{w}.characters: '{name}' không có trong Character Bible")
        if s.get("shots") is not None:                  # v3: the scene split into shots (core.shots)
            from .shots import ShotError, validate as _validate_shots
            try:
                _validate_shots(s["shots"], f"{w}.shots", names)
            except ShotError as e:
                raise SchemaError(str(e)) from e
    return obj


def validate_for_project(pipeline: Pipeline, project_id: int):
    """The Director validator plus the checks that need the project (so a wrong answer is sent back to Claude once, instead of
    being refused after it was paid for): every scene exists, and a shot-mode project gets a `shots` list for every scene."""
    def check(data: Any) -> Dict:
        obj = _normalized(pipeline, project_id, _load(data))
        validate_scene_analysis(obj)
        from . import shots as _shots
        if _shots.active(pipeline, project_id):
            missing = [s["idx"] for s in obj["scenes"] if not s.get("shots")]
            if missing:
                raise SchemaError("dự án chia shot: cảnh " + ", ".join(map(str, missing)) + " thiếu danh sách `shots`")
            _check_lines(pipeline, project_id, obj)
        else:
            have = {r["idx"] for r in pipeline.conn.execute("SELECT idx FROM scenes WHERE project_id=?", (project_id,))}
            unknown = [s["idx"] for s in obj["scenes"] if s["idx"] not in have]
            if unknown:
                raise SchemaError("scenes: idx " + ", ".join(map(str, unknown)) + " không có trong kịch bản đã tách (chỉ dùng số cảnh đã cho)")
        return obj
    return check


def _normalized(pipeline: Pipeline, project_id: int, obj: Dict) -> Dict:
    """H1: in a shot project, code fixes what it can measure (enum spellings, a spoken shot shorter than its line, 0,5 s silent
    shots, the total) in place, before validating — a fixable answer is no longer sent back to Claude. Changes: obj["normalized"]."""
    from . import shots as _shots
    if isinstance(obj.get("scenes"), list) and _shots.active(pipeline, project_id):
        from .shot_normalize import normalize
        proj = pipeline.project(project_id)
        normalize(obj, (proj["script_text"] if "script_text" in proj.keys() else None) or "", in_place=True)
    return obj


def _norm_line(text: str) -> str:
    from .dialogue import norm
    return norm(text)


def _check_lines(pipeline: Pipeline, project_id: int, obj: Dict) -> None:
    """Spoken lines are the script's own words (rule 3: the prompt says so, the code checks it): a line that is not in the script is
    sent back; every line of the script must be there unless the person allowed dropping lines (projects.dialogue_trim)."""
    from . import dialogue as _dlg, shots as _shots
    script = [_norm_line(said) for s in _shots.story_scenes(pipeline, project_id) for _, said in _dlg.lines(s["text"])]
    if not script:
        return
    used = [_norm_line(d.get("text")) for sc in obj["scenes"] for sh in sc.get("shots") or [] for d in sh.get("dialogue") or []
            if isinstance(d, dict) and not _dlg.is_non_speaker(str(d.get("speaker") or ""))]
    from collections import Counter               # S14.4 C1b: counted, not a set — a line written twice must be said twice
    have, said = Counter(script), Counter(t for t in used if t)
    invented = [t for t in said if said[t] > have[t]]
    if invented:
        raise SchemaError("dialogue: câu không có nguyên văn trong kịch bản (không thêm, không sửa chữ): " + "; ".join(invented[:3]))
    proj = pipeline.project(project_id)
    if not ("dialogue_trim" in proj.keys() and proj["dialogue_trim"]):
        dropped = [t for t in have if have[t] > said[t]]
        if dropped:
            raise SchemaError("dialogue: thiếu câu thoại của kịch bản (không được bỏ): " + "; ".join(dropped[:3]))


def _check_choice(value: Any, allowed, where: str) -> None:
    if value is not None and value not in allowed:
        raise SchemaError(f"{where}: chỉ nhận một trong {', '.join(allowed)} hoặc null")


BEAT_KEYS = ("want", "obstacle", "turn", "value", "plant", "payoff", "cause")   # GĐ4 director.md Đ1: value shift + set-up / pay-off;
                                                                                 # S3.1: what makes the turn and where it is seen


def _clean_beat(value: Any) -> Optional[Dict]:
    """The scene's beat with the known keys as text (unknown keys dropped, null = empty); not an object → None. Never refuses."""
    if not isinstance(value, dict):
        return None
    return {k: ("" if value.get(k) is None else str(value[k])) for k in BEAT_KEYS if k in value}


def _check_beat(value: Any, where: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict) or any(k not in BEAT_KEYS or not isinstance(v, str) for k, v in value.items()):
        raise SchemaError(f"{where}: cần object {{{', '.join(BEAT_KEYS)}}}, mỗi giá trị là chữ")


def _check_dialogue(value: Any, where: str) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        raise SchemaError(f"{where}: cần danh sách {{speaker, text}}")
    for j, d in enumerate(value):
        if not isinstance(d, dict) or not isinstance(d.get("speaker", ""), str) or not isinstance(d.get("text"), str) \
                or not d["text"].strip():
            raise SchemaError(f"{where}[{j}]: cần {{speaker, text}} với text không rỗng")


def _check_duration(value: Any, where: str) -> None:
    if value is None:
        return
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 1 <= value <= 30:
        raise SchemaError(f"{where}: cần số giây từ 1 đến 30")


LOCK_KEYS = ("must_keep", "may_change", "forbidden")


def _check_lock(value: Any, where: str) -> None:
    """Character Lock (game-character-consistency-designer skill): traits that must never change, what may vary per shot,
    and the drifts that are forbidden."""
    if not isinstance(value, dict) or any(k not in LOCK_KEYS or not isinstance(v, str) for k, v in value.items()):
        raise SchemaError(f"{where}: cần object {{must_keep, may_change, forbidden}}, mỗi giá trị là chữ")


def _check_location_asset(value: Any, where: str) -> None:
    """`location_asset` is optional: null, or the id (a positive whole number) of a place in the resource library."""
    if value is None:
        return
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise SchemaError(f"{where}.location_asset: chỉ nhận null hoặc mã tài nguyên (số nguyên dương)")


def _check_sequence(value: Any, where: str) -> None:
    """`sequence` is optional: null, or a positive whole number shared by consecutive scenes in the same place/continuous action."""
    if value is None:
        return
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise SchemaError(f"{where}.sequence: chỉ nhận null hoặc số nguyên dương")


def validate_qc_result(data: Any, required_criteria: List[str]) -> Dict:
    obj = _load(data)
    criteria = _req(obj, "criteria", dict, "root")
    for name in required_criteria:
        if name not in criteria:
            raise SchemaError(f"criteria: thiếu tiêu chí '{name}'")
    for name, score in criteria.items():
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 1:
            raise SchemaError(f"criteria.{name}: điểm phải là số trong [0, 1]")
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
            raise SchemaError(f"{w}.duration_sec: cần từ 1 đến 30 giây")
        flags = s.get("check_flags")
        if flags is not None and (not isinstance(flags, list) or not all(isinstance(f, str) for f in flags)):
            raise SchemaError(f"{w}.check_flags: cần danh sách chữ")
        if s.get("spatial_state") is not None and not isinstance(s.get("spatial_state"), str):
            raise SchemaError(f"{w}.spatial_state: cần chữ")
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
    access.need_edit(pipeline, project_id, "lưu phân tích của Director")
    obj = validate_scene_analysis(_normalized(pipeline, project_id, _load(data)))
    conn = pipeline.conn
    try:
        _store(pipeline, project_id, obj)
    except Exception:
        conn.rollback()                          # all or nothing: a refused answer must not leave half the Bible overwritten
        raise
    from . import voice_casting                  # S14.26: voice traits of the speaking roles → voices cast by rule (0 USD, flag)
    cast = voice_casting.after_analysis(conn, project_id, obj)
    if cast is not None:
        obj["voice_cast"] = cast
    return obj


def _store(pipeline: Pipeline, project_id: int, obj: Dict) -> None:
    conn = pipeline.conn
    for c in obj["characters"]:
        row = conn.execute("SELECT locked, user_edited FROM characters WHERE project_id=? AND name=?", (project_id, c["name"])).fetchone()
        if row is None:
            conn.execute("INSERT INTO characters (project_id, name, description, wardrobe) VALUES (?,?,?,?)",
                         (project_id, c["name"], c["description"], c.get("wardrobe")))
        elif not row["locked"]:
            edited = set(json.loads(row["user_edited"] or "[]"))
            if "description" not in edited:
                conn.execute("UPDATE characters SET description=? WHERE project_id=? AND name=?", (c["description"], project_id, c["name"]))
            if "wardrobe" not in edited and (c.get("wardrobe") or "").strip():
                conn.execute("UPDATE characters SET wardrobe=? WHERE project_id=? AND name=?", (c["wardrobe"], project_id, c["name"]))
        if c.get("lock"):
            conn.execute("UPDATE characters SET lock_rules=? WHERE project_id=? AND name=? AND (lock_rules IS NULL OR lock_rules='')",
                         (json.dumps({k: c["lock"].get(k, "") for k in LOCK_KEYS}, ensure_ascii=False), project_id, c["name"]))
    if obj.get("genre"):
        conn.execute("UPDATE projects SET genre=? WHERE id=? AND genre_locked=0", (obj["genre"].strip().upper(), project_id))
    from . import shots as _shots
    if _shots.active(pipeline, project_id):             # v3: rows become the Director's shots
        missing = [s["idx"] for s in obj["scenes"] if not s.get("shots")]
        if missing:
            raise SchemaError("dự án chia shot: cảnh " + ", ".join(map(str, missing)) + " thiếu danh sách `shots`")
        try:
            _shots.store_plan(pipeline, project_id, obj["scenes"])
        except _shots.ShotError as e:
            raise SchemaError(str(e)) from e
        conn.commit()
        return
    for s in obj["scenes"]:
        row = conn.execute("SELECT id, data FROM scenes WHERE project_id=? AND idx=?",
                           (project_id, s["idx"])).fetchone()
        if row is None:
            raise SchemaError(f"Cảnh số {s['idx']} không có trong dự án #{project_id} (chỉ dùng số cảnh đã tách từ kịch bản)")
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


def locked_fields(conn, project_id: int) -> List[Dict]:
    """[{idx, fields: {key: value}}] the person set by hand — told to the Director so it plans around them."""
    out = []
    for r in conn.execute("SELECT idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)):
        d = json.loads(r["data"] or "{}")
        keys = [k for k in d.get("_user_locked") or [] if k in d]
        if keys:
            label = f"Cảnh {d['story_scene']} · shot {d['shot_no']}" if d.get("shot_no") and d.get("story_scene") else None
            out.append({"idx": r["idx"], "fields": {k: d[k] for k in keys}, **({"label": label} if label else {})})
    return out


def unlock_scene_fields(pipeline: Pipeline, project_id: int, idx: int, keys: Optional[List[str]] = None) -> None:
    """Let the Director fill these fields again (all of them when keys is None)."""
    conn = pipeline.conn
    row = conn.execute("SELECT id, data FROM scenes WHERE project_id=? AND idx=?", (project_id, idx)).fetchone()
    if row is None:
        raise KeyError(f"Cảnh {idx} không có trong dự án — tải lại trang (có thể cảnh vừa bị xóa).")
    data = json.loads(row["data"] or "{}")
    data["_user_locked"] = [] if keys is None else [k for k in data.get("_user_locked") or [] if k not in keys]
    conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), row["id"]))
    conn.commit()


def lock_character_bible(pipeline: Pipeline, project_id: int) -> int:
    """Approve & Lock (Step 1): freeze characters and mark scenes 'ready' for image generation."""
    access.need_edit(pipeline, project_id, "khóa Character Bible")
    conn = pipeline.conn
    conn.execute("UPDATE characters SET locked=1 WHERE project_id=?", (project_id,))
    n = conn.execute("UPDATE scenes SET state='ready' WHERE project_id=? AND state!='needs_attention'",
                     (project_id,)).rowcount
    conn.commit()
    return n


SCENE_FIELDS = ("location", "time", "mood", "lighting", "shot", "image_prompt", "blocking", "emotional_intent")


BULK_FIELDS = ("video_route", "transition_in", "shake_in", "start_from_prev_clip")


def update_scenes_bulk(pipeline: Pipeline, project_id: int, idxs, fields: Mapping[str, Any]) -> Dict[int, List[str]]:
    """07/10 (Khủng Long Đỏ, 'BỐ CỤC GỌN' 3): the same values on several shots at once — one box for 6 shots was ~30 clicks. Only the
    BULK_FIELDS; each scene goes through update_scene (same checks, same 🔒 hand-edit lock, same ⚠ cũ). {idx: changed fields}."""
    idxs = [int(i) for i in idxs or []]
    if not idxs:
        raise SchemaError("chọn ít nhất một shot")
    extra = sorted(set(fields) - set(BULK_FIELDS))
    if extra:
        raise SchemaError(f"sửa hàng loạt chỉ nhận {', '.join(BULK_FIELDS)} (không nhận: {', '.join(extra)})")
    if fields.get("transition_in") not in (None, "") + tuple(_transitions()):
        raise SchemaError(f"transition_in: chọn một trong {', '.join(_transitions())}")
    return {i: update_scene(pipeline, project_id, i, dict(fields)) for i in idxs}


def _transitions():
    from .delivery import TRANSITIONS_IN
    return TRANSITIONS_IN


def update_scene(pipeline: Pipeline, project_id: int, idx: int, fields: Mapping[str, Any],
                 text: Optional[str] = None) -> List[str]:
    """Edit one scene's spec (and optionally its script text). `characters` must be names from the Character Bible.
    Every field whose value really changes is remembered as set by hand (`_user_locked`), so a later Director run keeps it.
    Results made from the old spec are then shown as outdated (core.lineage). Returns the changed field names."""
    access.need_edit(pipeline, project_id, "sửa cảnh")
    conn = pipeline.conn
    row = conn.execute("SELECT id, data FROM scenes WHERE project_id=? AND idx=?", (project_id, idx)).fetchone()
    if row is None:
        raise KeyError(f"Cảnh {idx} không có trong dự án — tải lại trang (có thể cảnh vừa bị xóa).")
    data = json.loads(row["data"] or "{}")
    before = json.loads(row["data"] or "{}")
    for key in SCENE_FIELDS:
        if key in fields:
            value = fields[key]
            if not isinstance(value, str):
                raise SchemaError(f"{key}: cần chữ")
            data[key] = value.strip()
    if "image_prompt" in fields and not data.get("image_prompt"):
        raise SchemaError("Prompt ảnh (image_prompt) không được để trống — nhập lại rồi lưu.")
    if "characters" in fields:
        names = {r["name"] for r in conn.execute("SELECT name FROM characters WHERE project_id=?", (project_id,))}
        cast = list(fields["characters"] or [])
        unknown = [c for c in cast if c not in names]
        if unknown:
            raise SchemaError(f"Nhân vật {', '.join(unknown)} không có trong Character Bible — thêm vào Character Bible trước, rồi chọn lại.")
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
        from .voice_direction import clean as clean_delivery
        old_lines = [d for d in before.get("dialogue") or [] if isinstance(d, dict)]
        rows = [d for d in (fields["dialogue"] or []) if isinstance(d, dict) and str(d.get("text") or "").strip()]
        kept = []
        for n, d in enumerate(rows):
            line = {"speaker": str(d.get("speaker") or "").strip(), "text": str(d["text"]).strip()}
            # GĐ4: the Director's voice direction stays with its line — the same place with the same words, else the first unused
            # old line with those words (two people saying "Đi thôi." keep their own) — unless the edit gives a new one
            if "delivery" in d:
                how_src = d["delivery"]
            else:
                same = [k for k, o in enumerate(old_lines) if str(o.get("text") or "").strip() == line["text"]]
                pick = n if n in same else next((k for k in same if k >= n), same[0] if same else None)
                how_src = old_lines[pick].get("delivery") if pick is not None else None
            how, _ = clean_delivery(how_src)
            if how:
                line["delivery"] = how
            kept.append(line)
        _check_dialogue(kept, "dialogue")
        data["dialogue"] = kept or None
    for key, allowed in (("size", "SIZES"), ("angle", "ANGLES"), ("move", "MOVES")):   # a v3 shot's camera, set by hand (07/10:
        if key in fields:                                  # "same frame as the previous shot" needs the same size — no box before)
            from . import shots as _shots
            value = fields[key] or None
            if value is not None and value not in getattr(_shots, allowed):
                raise SchemaError(f"{key}: chọn một trong {', '.join(getattr(_shots, allowed))}")
            if value is None:
                data.pop(key, None)
            else:
                data[key] = value
    if "video_route" in fields:                            # 07/10: one clip per shot / Kling chosen by hand (was only set by refusals)
        from .seedance_refs import ROUTES
        if fields["video_route"] not in ROUTES:
            raise SchemaError("video_route: chọn tự động (nhóm), 'single' hoặc 'kling'")
        if fields["video_route"] is None:
            data.pop("video_route", None)
        else:
            data["video_route"] = fields["video_route"]
    if "transition_in" in fields:                          # 07/10: the cut INTO the shot (flash on a "hô biến") — no box before
        from .delivery import TRANSITIONS_IN
        value = fields["transition_in"] or None
        if value is not None and value not in TRANSITIONS_IN:
            raise SchemaError(f"transition_in: chọn một trong {', '.join(TRANSITIONS_IN)}")
        if value is None or value == "cut":
            data.pop("transition_in", None)
        else:
            data["transition_in"] = value
    if "start_from_prev_clip" in fields:                   # 07/10: the clip starts on the previous clip's last frame (dance cuts)
        if fields["start_from_prev_clip"]:
            data["start_from_prev_clip"] = True
        else:
            data.pop("start_from_prev_clip", None)
    if "shake_in" in fields:                               # 07/10: the frame shakes as the shot starts (no impact sound needed)
        if fields["shake_in"]:
            data["shake_in"] = True
        else:
            data.pop("shake_in", None)
    if "performance" in fields:
        from .performance import clean as clean_performance
        acting, _ = clean_performance(fields["performance"])
        if acting:
            data["performance"] = acting
        else:
            data.pop("performance", None)
    if "why" in fields:
        if fields["why"] is not None and not isinstance(fields["why"], str):
            raise SchemaError("why: cần chữ")
        if (fields["why"] or "").strip():
            data["why"] = fields["why"].strip()
        else:
            data.pop("why", None)
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
    access.need_edit(pipeline, project_id, "thêm nhân vật")
    name, description = (name or "").strip(), (description or "").strip()
    if not name or not description:
        raise ValueError("Tên và mô tả nhân vật không được để trống — điền đủ cả hai rồi bấm lại.")
    if pipeline.conn.execute("SELECT 1 FROM characters WHERE project_id=? AND name=?", (project_id, name)).fetchone():
        raise ValueError(f"'{name}' đã có trong Character Bible — sửa mục đó thay vì thêm mới, hoặc đặt tên khác.")
    pipeline.conn.execute("INSERT INTO characters (project_id, name, description, wardrobe) VALUES (?,?,?,?)",
                          (project_id, name, description, (wardrobe or "").strip() or None))
    pipeline.conn.commit()


def update_character(pipeline: Pipeline, project_id: int, name: str, description: str,
                     wardrobe: Optional[str] = None, new_name: Optional[str] = None) -> None:
    """Edit one Character Bible entry (only while unlocked). A rename also updates the scene cast lists."""
    access.need_edit(pipeline, project_id, "sửa nhân vật")
    conn = pipeline.conn
    row = conn.execute("SELECT id, locked FROM characters WHERE project_id=? AND name=?", (project_id, name)).fetchone()
    if row is None:
        raise KeyError(f"Không tìm thấy nhân vật '{name}' — tải lại trang (có thể vừa bị đổi tên hoặc xóa).")
    if row["locked"]:
        raise ValueError(f"Nhân vật '{name}' đang khóa. Mở khóa Character Bible trước (nút 🔓 ở Bước 1), sửa xong khóa lại.")
    description = (description or "").strip()
    if not description:
        raise ValueError("Mô tả nhân vật không được để trống — nhập mô tả rồi lưu lại.")
    new_name = (new_name or name).strip()
    if not new_name:
        raise ValueError("Tên nhân vật không được để trống — nhập tên rồi lưu lại.")
    if new_name != name and conn.execute("SELECT 1 FROM characters WHERE project_id=? AND name=?",
                                         (project_id, new_name)).fetchone():
        raise ValueError(f"Đã có nhân vật tên '{new_name}' — chọn tên khác.")
    old = conn.execute("SELECT description, wardrobe, user_edited FROM characters WHERE id=?", (row["id"],)).fetchone()
    edited = set(json.loads(old["user_edited"] or "[]"))
    if description != (old["description"] or ""):
        edited.add("description")
    if ((wardrobe or "").strip() or None) != (old["wardrobe"] or None):
        edited.add("wardrobe")
    conn.execute("UPDATE characters SET name=?, description=?, wardrobe=?, user_edited=? WHERE id=?",
                 (new_name, description, (wardrobe or "").strip() or None, json.dumps(sorted(edited)) if edited else None, row["id"]))
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
    access.need_edit(pipeline, project_id, "mở khóa Character Bible")
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
            raise SchemaError(f"Cảnh số {s['idx']} không có trong dự án #{project_id} (chỉ dùng số cảnh đã tách từ kịch bản)")
        from .shots import image_scene
        approved = conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'",
                                (image_scene(conn, row["id"]),)).fetchone()
        if approved is None:
            raise SchemaError(f"scene idx {s['idx']} has no approved image yet")
        scene_data = json.loads(conn.execute("SELECT data FROM scenes WHERE id=?", (row["id"],)).fetchone()["data"] or "{}")
        duration = s.get("duration_sec") or scene_data.get("duration_s") or 5
        if "duration_s" in set(scene_data.get("_user_locked") or []) and scene_data.get("duration_s"):
            duration = scene_data["duration_s"]          # length the person set (e.g. sized to the dialogue) wins
        elif scene_data.get("shot_no") and scene_data.get("duration_s"):
            duration = scene_data["duration_s"]          # v3 shot: the film length the Director planned (the clip is cut to it)
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
