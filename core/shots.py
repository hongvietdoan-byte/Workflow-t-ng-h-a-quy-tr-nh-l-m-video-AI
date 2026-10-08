"""Shots (kế hoạch v3, GĐ2): the Director splits each script scene into short shots.

Storage reuses the whole v2 pipeline: every shot is ONE row of `scenes` (so image / motion / video jobs, lineage, QC, the model
router, voice lines and subtitles all work per shot unchanged). The script's own scenes live in `story_scenes`; a shot row
carries `story_scene` (the script scene number), `shot_no` and `sequence` (the continuity group) in its data. `scenes.idx` is
the running shot number of the whole film — rows are only ever appended (file names such as videos/{idx}.mp4 depend on it).

A project with `shot_mode` NULL keeps the v2 behaviour (one script scene = one row = one clip).
"""
import json
from typing import Any, Dict, List, Optional

from .pipeline import Pipeline

MODES = {None: "Mỗi cảnh một clip (v2)", "per_shot": "Chia shot — gen từng shot", "multishot": "Chia shot — Kling multi-shot theo nhóm"}
SIZES = ("ECU", "CU", "MCU", "MS", "MLS", "WS", "EWS", "GAME_TPS")   # the reference analysis vocabulary + MLS (dp.md Q2; no GRAPHIC:
ANGLES = ("eye", "low", "high", "overhead", "dutch", "ots", "pov")   # titles / cards are made in post, not by the video model)
MOVES = ("static", "push_in", "pull_out", "pan", "tilt", "track", "orbit", "handheld", "crane", "whip", "zoom")
ROLES = ("hook", "setup", "action", "reaction", "insert", "dialogue", "transition", "ending")
SIZE_WORDS = {"ECU": "extreme close-up", "CU": "close-up", "MCU": "medium close-up", "MS": "medium shot",
              "MLS": "medium long shot", "WS": "wide shot",
              "EWS": "extreme wide shot", "GAME_TPS": "third-person game camera behind the character, slightly above the shoulder"}
MIN_SHOT, MAX_SHOT = 0.5, 15.0
# what a shot row keeps from its script scene (Director fields of the whole scene)
SCENE_KEYS = ("location", "time", "mood", "lighting", "location_asset", "emotional_intent", "beat", "knowledge_gap")
# director.md Đ3 "ai biết gì": the viewer knows more than the character (suspense), the same (tension) or less (surprise)
KNOWLEDGE_GAPS = ("ahead", "same", "behind")
# editing.md E10 / dp.md Q11: time on screen — slow motion (speed < 1) and a freeze at the end of a shot, done in the cut
SPEED_MIN, SPEED_MAX, FREEZE_MAX = 0.25, 0.9, 1.5


class ShotError(ValueError):
    pass


def mode(proj) -> Optional[str]:
    value = proj["shot_mode"] if proj is not None and "shot_mode" in proj.keys() else None
    return value if value in MODES and value else None


def active(pipeline: Pipeline, project_id: int) -> bool:
    return mode(pipeline.project(project_id)) is not None


def styles(proj) -> List[str]:
    """The reference styles picked for the project, in order (stored comma-separated in `style_profile`). Người dùng 2026-09-28: a
    style is a set of SUGGESTIONS the Director may mix with others or depart from — never one fixed frame for every script."""
    value = proj["style_profile"] if proj is not None and "style_profile" in proj.keys() else None
    return [s.strip() for s in str(value or "").split(",") if s.strip()]


def style(proj) -> Optional[str]:
    """The first reference style (older callers that know one style only)."""
    picked = styles(proj)
    return picked[0] if picked else None


def label(data: Dict, idx: int) -> str:
    """'S02·3' for shot 3 of script scene 2, else the v2 'S02'."""
    if data.get("shot_no") and data.get("story_scene"):
        return f"S{int(data['story_scene']):02d}·{int(data['shot_no'])}"
    return f"S{idx:02d}"


def row_label(row) -> str:
    return label(json.loads(row["data"] or "{}"), row["idx"])


# ---- script scenes ---------------------------------------------------------------------------------------------------------
def save_story_scenes(pipeline: Pipeline, project_id: int, scenes) -> None:
    """The script's scenes as parsed (script_parser.import_scenes): kept apart from the shot rows."""
    conn = pipeline.conn
    conn.execute("DELETE FROM story_scenes WHERE project_id=?", (project_id,))
    for s in scenes:
        conn.execute("INSERT INTO story_scenes (project_id, idx, heading, text, data) VALUES (?,?,?,?,?)",
                     (project_id, s.idx, s.heading, s.text, json.dumps({"characters": s.characters}, ensure_ascii=False)))
    conn.commit()


def story_scenes(pipeline: Pipeline, project_id: int) -> List[Dict]:
    """[{idx, heading, text, data}] — from `story_scenes`, or (a project imported before v3) from its v2 scene rows."""
    conn = pipeline.conn
    rows = conn.execute("SELECT idx, heading, text, data FROM story_scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall()
    if rows:
        return [{"idx": r["idx"], "heading": r["heading"], "text": r["text"] or "", "data": json.loads(r["data"] or "{}")} for r in rows]
    out = []
    for r in conn.execute("SELECT idx, title, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)):
        d = json.loads(r["data"] or "{}")
        if d.get("shot_no"):
            continue
        out.append({"idx": r["idx"], "heading": r["title"], "text": d.get("text", ""), "data": d})
    return out


# ---- validation of the Director's shots ------------------------------------------------------------------------------------
def _choice(value, allowed, where):
    if value not in allowed:
        raise ShotError(f"{where}: phải là một trong {', '.join(allowed)}")


def validate(shots: Any, where: str, names) -> None:
    """One scene's `shots` list from the Director (v3)."""
    if not isinstance(shots, list) or not shots:
        raise ShotError(f"{where}: cần danh sách shot (ít nhất 1)")
    for k, s in enumerate(shots):
        w = f"{where}[{k}]"
        if not isinstance(s, dict):
            raise ShotError(f"{w}: expected object")
        _choice(s.get("size"), SIZES, f"{w}.size")
        _choice(s.get("angle", "eye"), ANGLES, f"{w}.angle")
        _choice(s.get("camera_move", "static"), MOVES, f"{w}.camera_move")
        _choice(s.get("role"), ROLES, f"{w}.role")
        dur = s.get("duration_s")
        if not isinstance(dur, (int, float)) or isinstance(dur, bool) or not MIN_SHOT <= dur <= MAX_SHOT:
            raise ShotError(f"{w}.duration_s: số giây từ {MIN_SHOT:g} đến {MAX_SHOT:g}")
        for key in ("image_prompt", "action"):
            if not isinstance(s.get(key), str) or not s[key].strip():
                raise ShotError(f"{w}.{key}: expected non-empty text")
        for key in ("start_frame", "end_state", "action_peak"):
            if s.get(key) is not None and not isinstance(s[key], str):
                raise ShotError(f"{w}.{key}: expected text")
        for key in ("continuous_with_next", "hero"):
            if s.get(key) is not None and not isinstance(s[key], bool):
                raise ShotError(f"{w}.{key}: true/false")
        setup = s.get("camera_setup")
        if setup is not None and (not isinstance(setup, str) or not 1 <= len(setup.strip()) <= 3):
            raise ShotError(f"{w}.camera_setup: chữ cái ngắn (A, B, C…)")
        chars = s.get("characters") or []
        if not isinstance(chars, list) or any(c not in names for c in chars):
            raise ShotError(f"{w}.characters: chỉ dùng tên trong Character Bible")
        lines = s.get("dialogue") or []
        if not isinstance(lines, list) or any(not isinstance(d, dict) or not str(d.get("text") or "").strip() for d in lines):
            raise ShotError(f"{w}.dialogue: [{{speaker, text}}]")


def pacing_warnings(shots: List[Dict]) -> List[str]:
    """Soft checks only — pacing follows the script (decision 3): a spoken line longer than its shot, a silent shot under 1 s, a wide
    shot too short to read, the same size many times in a row."""
    from .dialogue import needed_seconds
    out = []
    for k, s in enumerate(shots, 1):
        need = needed_seconds([(d.get("speaker", ""), d["text"]) for d in s.get("dialogue") or []])
        if need and need > float(s["duration_s"]) + 0.3:
            out.append(f"shot {k}: thoại cần ~{need:g}s nhưng shot dài {s['duration_s']:g}s")
        dur = float(s["duration_s"])
        if not need and dur < 1 and s.get("role") != "insert":   # "ANH CHỌN AI?" run 4: six silent 0,5–0,6 s shots, each paid as a 3 s clip
            out.append(f"shot {k}: {dur:g}s không thoại — gộp vào shot bên cạnh (model vẫn tính tiền clip tối thiểu)")
        elif s.get("size") in ("WS", "EWS") and dur < 1.5:
            out.append(f"shot {k}: toàn cảnh {dur:g}s — người xem không kịp đọc, nên ≥ 1,5s hoặc bỏ")
    run = 1
    for k in range(1, len(shots)):
        run = run + 1 if shots[k]["size"] == shots[k - 1]["size"] else 1
        if run == 4:
            out.append(f"shot {k - 2}–{k + 1}: bốn shot liền cùng cỡ {shots[k]['size']}")
    return out


# ---- storing ----------------------------------------------------------------------------------------------------------------
def _shot_text(s: Dict) -> str:
    lines = [f"{d.get('speaker') or ''}: {d['text']}".strip(": ") for d in _split_lines(s)[0]]
    return "\n".join([s["action"].strip()] + lines)


def _split_lines(s: Dict):
    """(spoken lines, on-screen text): a 'line' of the system / HUD / a text card is shown on screen, never voiced (kịch bản
    "ANH CHỌN AI?": "HỆ THỐNG: Maxim đã bị hạ" came back as a NARRATOR line)."""
    from .dialogue import is_non_speaker
    from .voice_direction import clean as clean_delivery
    spoken, screen = [], [str(x).strip() for x in s.get("on_screen_text") or [] if str(x).strip()]
    for d in s.get("dialogue") or []:
        who, said = str(d.get("speaker") or "").strip(), str(d["text"]).strip()
        if is_non_speaker(who):
            screen.append(said)
            continue
        line = {"speaker": who, "text": said}
        how, _ = clean_delivery(d.get("delivery"))       # GĐ4: the Director's voice direction of the line (director.md Đ5)
        if how:
            line["delivery"] = how
        spoken.append(line)
    return spoken, screen


def shot_data(scene: Dict, s: Dict, k: int) -> Dict:
    """The data of one shot row: the script scene's setting + the shot's own camera, action and lines."""
    spoken, screen = _split_lines(s)
    data = {key: scene[key] for key in SCENE_KEYS if key in scene}
    if data.get("knowledge_gap") not in KNOWLEDGE_GAPS:
        data.pop("knowledge_gap", None)
    data.update({
        "story_scene": scene["idx"], "shot_no": k,
        "sequence": scene.get("sequence") or scene["idx"],
        # A16: a shot that lists nobody (an insert, an empty establishing shot) stays empty instead of taking the whole cast
        "characters": list(s["characters"] if isinstance(s.get("characters"), list) else scene.get("characters") or []),
        "image_prompt": s["image_prompt"].strip(),
        "blocking": (s.get("start_frame") or "").strip(),
        "shot": f"{SIZE_WORDS[s['size']]}, {s.get('angle', 'eye')} angle, {s.get('camera_move', 'static').replace('_', ' ')}",
        "size": s["size"], "angle": s.get("angle", "eye"), "camera_move": s.get("camera_move", "static"), "role": s["role"],
        "action": s["action"].strip(), "end_state": (s.get("end_state") or "").strip() or None,
        "action_peak": (s.get("action_peak") or "").strip()[:200] or None if isinstance(s.get("action_peak"), (str, type(None))) else None,
        "continuous_with_next": bool(s.get("continuous_with_next")),
        "camera_setup": (str(s["camera_setup"]).strip().upper() if s.get("camera_setup") else None),   # H5: one clip per set-up
        "dialogue": spoken,
        "on_screen_text": screen,   # HUD / system message / caption: added in post, never voiced nor drawn by the image model
        "duration_s": round(float(s["duration_s"]), 2),
        "camera_complexity": s.get("camera_complexity") or scene.get("camera_complexity") or "simple",
        "shot_role": "hero" if s.get("hero") else ("transition" if s["role"] == "transition" else "normal"),
        "text": _shot_text(s),      # the shot's own action + lines; the script scene's text stays in story_scenes (never copied)
    })
    # V4 fields the Director may write (dropped before — only the listed keys were kept): lip sync of a key close-up (GĐ3), the
    # weather of the shot / its scene and the spot / mode on a location pack (GĐ2)
    if isinstance(s.get("lip_sync"), bool):
        data["lip_sync"] = s["lip_sync"]
    # S14.44: `plate_mode` (green-screen plates, removed in S14.9) is never stored on a new row — see _drop_plate_mode
    for key in ("weather", "plate_spot"):
        value = s.get(key) or scene.get(key)
        if isinstance(value, str) and value.strip():
            data[key] = value.strip()
    # S5.7 (người dùng 29/09): the camera direction on a 3D place and the extra lights of a night shot are the DP's choice per shot
    # (lights may be written once on the scene); kept as written — core/plate_choice checks them and reports what is missing
    view = s.get("plate_view") if s.get("plate_view") not in (None, "") else scene.get("plate_view")
    if isinstance(view, (dict, str)) or (isinstance(view, (int, float)) and not isinstance(view, bool)):
        data["plate_view"] = view
    lights = s.get("practical_lights") if isinstance(s.get("practical_lights"), list) else scene.get("practical_lights")
    if isinstance(lights, list):
        data["practical_lights"] = lights
    # GĐ4 (the crew's skill books): the acting of the shot (director.md Đ4 → image + motion prompts), the DP's reason for the camera
    # (dp.md Q7 — the Director approves the shot by it), the lens of the virtual camera on a 3D place (dp.md Q2 → plate_camera)
    from . import performance
    acting, _ = performance.clean(s.get("performance"))
    if acting:
        data["performance"] = acting
    if isinstance(s.get("why"), str) and s["why"].strip():
        data["why"] = s["why"].strip()
    if isinstance(s.get("motif"), str) and s["motif"].strip():
        data["motif"] = s["motif"].strip()[:60]           # director.md Đ3: a short tag the shots that rhyme share
    from . import sound_intent
    sound, _ = sound_intent.clean(s.get("sound"))
    if sound:
        data["sound"] = sound                             # director.md Đ9: music cut/in/breath + the sounds the moment needs
    lens = s.get("lens_mm")
    if isinstance(lens, (int, float)) and not isinstance(lens, bool) and 14 <= lens <= 200:
        data["lens_mm"] = int(round(lens))
    from .delivery import TRANSITIONS_IN
    if s.get("transition_in") in TRANSITIONS_IN and s.get("transition_in") != "cut":
        data["transition_in"] = s["transition_in"]       # S3.6: the cut into this shot (the editor draws flash / dip / whip / zoom)
    if s.get("hook_mid") is True:
        data["hook_mid"] = True                           # director.md Đ2: the open detail that carries the viewer to the next part
    if s.get("money_shot") is True:
        data["money_shot"] = True                         # director.md Đ10: what the video promotes, shown best (the cover frame)
    retime = clean_retime(s, spoken)
    data.update(retime)
    # N2 (người dùng chốt 08/10): the Director's difficulty of the shot (the scene's when the shot has none), cross-checked by
    # core/shot_complexity — missing / misspelt → "unknown", never a refused answer; N1 reads it to pick draft-first or high tier
    for key in ("difficulty", "difficulty_why"):
        if s.get(key) not in (None, ""):
            data[key] = s[key]
        elif scene.get(key) not in (None, ""):
            data[key] = scene[key]
    from . import shot_complexity
    shot_complexity.apply(data)
    return data


def clean_retime(s: Dict, spoken=None) -> Dict:
    """`speed` (SPEED_MIN–1, slow motion) and `freeze_end_s` (0–FREEZE_MAX) of a shot, kept only on a shot nobody speaks in and that
    is not lip-synced (a slowed voice / mouth is wrong) — {} otherwise."""
    if spoken is None:
        spoken, _ = _split_lines(s)
    if spoken or s.get("lip_sync"):
        return {}
    out = {}
    speed = s.get("speed")
    if isinstance(speed, (int, float)) and not isinstance(speed, bool) and SPEED_MIN <= speed <= SPEED_MAX:
        out["speed"] = round(float(speed), 2)
    freeze = s.get("freeze_end_s")
    if isinstance(freeze, (int, float)) and not isinstance(freeze, bool) and 0 < freeze <= FREEZE_MAX:
        out["freeze_end_s"] = round(float(freeze), 2)
    return out


def has_work(conn, project_id: int) -> bool:
    return bool(conn.execute("SELECT 1 FROM jobs WHERE project_id=? AND scene_id IS NOT NULL LIMIT 1", (project_id,)).fetchone())


def _drop_plate_mode(conn, project_id: int, scenes: List[Dict], rows: List[Dict]) -> None:
    """S14.44 (người dùng 06/10): the green-screen plates are gone (S14.9) — a `plate_mode` the Director still writes (on a shot or a
    scene, or a hand-locked one carried over from a replaced row) is not stored, so a new row never has the field and nothing can
    switch the old behaviour back on from it. Said once per stored plan (diag), not silently."""
    found = any(s.get("plate_mode") not in (None, "") for s in scenes) or any(
        isinstance(sh, dict) and sh.get("plate_mode") not in (None, "") for s in scenes for sh in s.get("shots") or [])
    for d in rows:
        found = d.pop("plate_mode", None) is not None or found
    if found:
        from . import diag
        diag.record(conn, "director", "info", "Đạo diễn ghi `plate_mode` (phông xanh) — đã bỏ từ S14.9, không lưu vào shot; "
                    "ảnh/video làm như shot không có trường này.", "plate_mode_ignored", project_id)


def replace_from(pipeline: Pipeline, project_id: int, scenes: List[Dict], from_scene: int) -> int:
    """1.4 "↻ Chia shot lại cảnh này": replace the shot rows of script scene `from_scene` and every later scene with the plan in `scenes`
    (the whole plan), keeping the rows of earlier scenes untouched — they may already have pictures and clips. Rows are appended in
    film order (row numbers must keep the film order and are never reused), so the later scenes are rewritten too. Refused when any
    of the replaced rows already has a picture or a clip. Returns the number of rows written."""
    conn = pipeline.conn
    rows = conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall()
    gone = [r for r in rows if (json.loads(r["data"] or "{}").get("story_scene") or 0) >= from_scene]
    if gone and conn.execute("SELECT 1 FROM jobs WHERE scene_id IN (" + ",".join("?" * len(gone)) + ") LIMIT 1",
                             [r["id"] for r in gone]).fetchone():
        raise ShotError(f"Cảnh {from_scene} (hoặc cảnh sau) đã có ảnh/video — không chia shot lại được; làm lại các cảnh đó trước.")
    story = {s["idx"]: s for s in story_scenes(pipeline, project_id)}
    for s in scenes:
        if s["idx"] >= from_scene and s["idx"] in story:
            extra = {k: s[k] for k in ("location", "time", "mood", "lighting", "location_asset", "sequence", "emotional_intent", "beat",
                                       "characters", "camera_complexity") if k in s}
            conn.execute("UPDATE story_scenes SET data=? WHERE project_id=? AND idx=?",
                         (json.dumps({**story[s["idx"]]["data"], **extra}, ensure_ascii=False), project_id, s["idx"]))
    kept = {}
    for r in gone:
        d = json.loads(r["data"] or "{}")
        locked = [k for k in d.get("_user_locked") or [] if k in d]
        if locked and d.get("shot_no"):
            kept[(d.get("story_scene"), d["shot_no"])] = {"_user_locked": locked, **{k: d[k] for k in locked}}
    if gone:
        marks = ",".join("?" * len(gone))
        conn.execute(f"DELETE FROM motion_prompts WHERE scene_id IN ({marks})", [r["id"] for r in gone])
        from .feedback import detach
        detach(conn, scene_ids=[r["id"] for r in gone])
        conn.execute(f"DELETE FROM scenes WHERE id IN ({marks})", [r["id"] for r in gone])
    n = conn.execute("SELECT COALESCE(MAX(idx), 0) FROM scenes WHERE project_id=?", (project_id,)).fetchone()[0]
    written = 0
    new = sorted((x for x in scenes if x["idx"] >= from_scene), key=lambda x: x["idx"])
    built = []
    for s in new:
        heading = (story.get(s["idx"]) or {}).get("heading") or f"CẢNH {s['idx']}"
        for k, shot in enumerate(s["shots"], 1):
            data = shot_data(s, shot, k)
            if s["idx"] != from_scene:                   # only the re-planned scene may lose its hand edits (its shots changed)
                data.update(kept.get((data.get("story_scene"), data.get("shot_no")), {}))
            built.append((f"{heading} · shot {k}", data))
    _drop_plate_mode(conn, project_id, new, [d for _, d in built])
    for title, data in built:
        n += 1
        conn.execute("INSERT INTO scenes (project_id, idx, title, data) VALUES (?,?,?,?)",
                     (project_id, n, title, json.dumps(data, ensure_ascii=False)))
        written += 1
    conn.commit()
    return written


def store_plan(pipeline: Pipeline, project_id: int, scenes: List[Dict], force: bool = False) -> int:
    """Replace the project's rows with the Director's shots (every scene of `scenes` has a validated `shots` list). Refused when
    pictures or videos were already made from the current rows (they would lose their scene) unless `force` (tests / the person
    confirmed a full redo). Returns the number of shots."""
    conn = pipeline.conn
    if has_work(conn, project_id) and not force:
        raise ShotError("Dự án đã có ảnh/video làm theo các cảnh hiện tại — bấm “↺ Làm lại” (hoặc tạo dự án mới) trước khi chia shot lại.")
    story = {s["idx"]: s for s in story_scenes(pipeline, project_id)}
    for s in scenes:                                     # the scene-level Director fields go to the script scene
        extra = {k: s[k] for k in ("location", "time", "mood", "lighting", "location_asset", "sequence", "emotional_intent", "beat",
                                   "characters", "camera_complexity") if k in s}
        if s["idx"] in story:
            data = {**story[s["idx"]]["data"], **extra}
            conn.execute("UPDATE story_scenes SET data=? WHERE project_id=? AND idx=?",
                         (json.dumps(data, ensure_ascii=False), project_id, s["idx"]))
        else:
            conn.execute("INSERT INTO story_scenes (project_id, idx, heading, text, data) VALUES (?,?,?,?,?)",
                         (project_id, s["idx"], f"CẢNH {s['idx']}", "", json.dumps(extra, ensure_ascii=False)))
    kept = {}                                            # fields the person set by hand, per (script scene, shot number)
    for r in conn.execute("SELECT data FROM scenes WHERE project_id=?", (project_id,)).fetchall():
        d = json.loads(r["data"] or "{}")
        locked = [k for k in d.get("_user_locked") or [] if k in d]
        if locked and d.get("shot_no"):
            kept[(d.get("story_scene"), d["shot_no"])] = {"_user_locked": locked, **{k: d[k] for k in locked}}
    conn.execute("DELETE FROM motion_prompts WHERE scene_id IN (SELECT id FROM scenes WHERE project_id=?)", (project_id,))
    from .feedback import detach
    detach(conn, project_id=project_id)
    conn.execute("DELETE FROM scenes WHERE project_id=?", (project_id,))
    n = 0
    built = []
    for s in sorted(scenes, key=lambda x: x["idx"]):
        heading = (story.get(s["idx"]) or {}).get("heading") or f"CẢNH {s['idx']}"
        for k, shot in enumerate(s["shots"], 1):
            data = shot_data(s, shot, k)
            data.update(kept.get((data.get("story_scene"), data.get("shot_no")), {}))
            built.append((f"{heading} · shot {k}", data))
    _drop_plate_mode(conn, project_id, scenes, [d for _, d in built])
    for title, data in built:
        n += 1
        conn.execute("INSERT INTO scenes (project_id, idx, title, data) VALUES (?,?,?,?)",
                     (project_id, n, title, json.dumps(data, ensure_ascii=False)))
    conn.commit()
    return n


def shots_of(pipeline: Pipeline, project_id: int) -> List[Dict]:
    """All shot rows in film order: [{id, idx, title, data, label}]."""
    out = []
    for r in pipeline.conn.execute("SELECT id, idx, title, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)):
        d = json.loads(r["data"] or "{}")
        out.append({"id": r["id"], "idx": r["idx"], "title": r["title"], "data": d, "label": label(d, r["idx"])})
    return out


def dialogue_cuts(pipeline: Pipeline, project_id: int) -> List[Dict]:
    """Script lines that no shot says (projects.dialogue_trim), worked out from the shots themselves — not from the Director's own
    `dropped_lines` list. `answered`: the next line of the same script scene is kept and said by someone else, so it probably
    answers the dropped one ("ANH CHỌN AI?": dropping "Kelly, nghe anh giải thích…" left "Không cần." answering nothing)."""
    from . import dialogue
    used = {dialogue.norm(d.get("text")) for s in shots_of(pipeline, project_id) for d in s["data"].get("dialogue") or []}
    out = []
    for sc in story_scenes(pipeline, project_id):
        rows = dialogue.lines(sc["text"])
        for i, (who, said) in enumerate(rows):
            if dialogue.norm(said) in used:
                continue
            nxt = rows[i + 1] if i + 1 < len(rows) else None
            out.append({"scene": sc["idx"], "speaker": who, "text": said,
                        "answered": bool(nxt and nxt[0] != who and dialogue.norm(nxt[1]) in used),
                        "next": f"{nxt[0]}: {nxt[1]}" if nxt else ""})
    return out


def story_scene_count(pipeline: Pipeline, project_id: int) -> int:
    n = pipeline.conn.execute("SELECT COUNT(*) FROM story_scenes WHERE project_id=?", (project_id,)).fetchone()[0]
    return n or pipeline.conn.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (project_id,)).fetchone()[0]


# ---- clip length ------------------------------------------------------------------------------------------------------------
TRIM_SLACK = 0.2           # a clip at most this much longer than the shot is kept as it is


def planned_seconds(conn, scene_id: int) -> float:
    """The length the shot should have on the film (its motion prompt's duration, else the Director's duration_s); 0 = unknown."""
    mp = conn.execute("SELECT duration_sec FROM motion_prompts WHERE scene_id=?", (scene_id,)).fetchone()
    if mp is not None and mp["duration_sec"]:
        return float(mp["duration_sec"])
    row = conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    return float(json.loads(row["data"] or "{}").get("duration_s") or 0) if row else 0.0


MOTION_MAX_SHIFT = 1.0      # D2: the cut may start at most this late in the clip (the approved first frame is what the shot was made from)
MOTION_GAIN = 1.5           # ... and only when the later window moves clearly more than the start (the action happened late)


def motion_profile(path: str, fps: int = 8) -> List[float]:
    """Mean frame-to-frame change (0..1) of a clip, sampled small and grey — how much happens at each moment."""
    import subprocess
    import numpy as np
    from .ffmpeg_studio import find_ffmpeg
    proc = subprocess.run([find_ffmpeg(), "-v", "error", "-i", path, "-vf", f"scale=48:84,fps={fps},format=gray", "-f", "rawvideo", "-"],
                          capture_output=True)
    frames = np.frombuffer(proc.stdout, np.uint8)
    n = len(frames) // (48 * 84)
    if n < 3:
        return []
    frames = frames[: n * 48 * 84].reshape(n, 84, 48).astype(np.float32) / 255
    return [float(x) for x in np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))]


def motion_start(conn, scene_id: int, raw: str, want: float, have: float, fps: int = 8, max_shift: float = MOTION_MAX_SHIFT) -> float:
    """D2 (knowledge/editor/editing.md E1, cờ `motion_trim`): where the cut of a long clip starts — 0 (the start, as the DP planned:
    "the main action happens early") unless the feature is on, the shot does not continue another one, and a window up to
    MOTION_MAX_SHIFT later moves MOTION_GAIN times more than the start window (the model made the action late)."""
    from . import features
    if not features.on("motion_trim"):
        return 0.0
    data = json.loads(conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()["data"] or "{}")
    if data.get("continuous_with_next") or data.get("role") in ("dialogue",) or data.get("lip_sync") or data.get("dialogue"):
        return 0.0                         # a continuing / spoken / lip-synced shot keeps its first frame and its seconds
    prev = conn.execute("SELECT data FROM scenes WHERE project_id=(SELECT project_id FROM scenes WHERE id=?) AND idx<"
                        "(SELECT idx FROM scenes WHERE id=?) ORDER BY idx DESC LIMIT 1", (scene_id, scene_id)).fetchone()
    if prev and json.loads(prev["data"] or "{}").get("continuous_with_next"):
        return 0.0
    prof = motion_profile(raw, fps)
    win = max(int(want * fps), 1)
    if len(prof) < win + 1:
        return 0.0
    most = min(int(min(max_shift, have - want) * fps), len(prof) - win)
    score = lambda k: sum(prof[k:k + win]) / win  # noqa: E731
    first = score(0)
    best = max(range(most + 1), key=score)
    return round(best / fps, 2) if best and score(best) > first * MOTION_GAIN + 1e-4 else 0.0


def retime_filter(speed: float, freeze: float, fps: int = 30) -> Optional[str]:
    """ffmpeg video filter of a retimed shot: slowed by `speed` (frames made in between by motion interpolation, so a 24 fps clip at
    half speed does not stutter at 12 fps) and/or holding its last frame `freeze` seconds. None when nothing changes."""
    parts = []
    if speed < 1:
        parts.append(f"setpts=PTS/{speed:g}")
        parts.append(f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:vsbmc=1")
    if freeze > 0:
        parts.append(f"tpad=stop_mode=clone:stop_duration={freeze:g}")
    return ",".join(parts) or None


def _encode():
    from .ffmpeg_studio import _ENCODE
    return _ENCODE


def trim_clip(pipeline: Pipeline, scene_id: int, path: str, lone_ref: bool = False) -> bool:
    """Cut a downloaded clip of a SHOT row to the shot's planned length: the full clip is kept next to it as <name>_raw.mp4.
    Nothing happens for v2 rows, clips already short enough, or files ffmpeg cannot read. Returns True when cut.
    Cờ `speed_ramp` (editing.md E10): a shot with `speed` < 1 takes (length − freeze) × speed seconds of the clip and plays them
    slowed to fill the shot, then holds its last frame `freeze_end_s`; its sound is dropped (a slowed sound is wrong; the shot has no
    line by construction — shots.clean_retime).
    lone_ref (S2.5, cờ `motion_trim`): a lone Seedance reference-only clip (≥ 4 s, the prompt spreads the action over the whole clip)
    is cut to at least the group floor of its action (seedance_refs.floored — never the bare 1–2 s plan that lost S5·1's fall) at the
    window where it moves most, anywhere in the clip; a spoken / lip-synced shot keeps its start (motion_start)."""
    import os
    import shutil
    import subprocess
    from . import features
    from .ffmpeg_studio import find_ffmpeg, has_audio, probe_duration
    row = pipeline.conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    data = json.loads(row["data"] or "{}") if row else {}
    if row is None or not data.get("shot_no"):
        return False
    want = planned_seconds(pipeline.conn, scene_id)
    shift = MOTION_MAX_SHIFT
    if lone_ref:
        from . import seedance_refs
        if not features.on("motion_trim"):
            return False                   # without the feature a lone reference clip is kept whole, as before
        want = seedance_refs.floored(data, want) if want else 0.0
        shift = 30.0                       # the action may sit anywhere in a clip whose prompt spread it over the whole length
    have = probe_duration(path) if os.path.exists(path) else None
    speed = float(data.get("speed") or 1) if features.on("speed_ramp") else 1.0
    freeze = min(float(data.get("freeze_end_s") or 0), max(want - 0.5, 0)) if features.on("speed_ramp") and want else 0.0
    vf = retime_filter(speed, freeze)
    source = round((want - freeze) * speed, 2) if want else 0
    if not want or not have or (vf is None and have <= want + TRIM_SLACK):
        return False
    try:
        start = motion_start(pipeline.conn, scene_id, path, source, have, max_shift=shift) if vf is None else 0.0
    except Exception:  # noqa: BLE001 - a clip whose motion cannot be read is cut from its start, as always
        start = 0.0
    raw = os.path.splitext(path)[0] + "_raw.mp4"
    shutil.move(path, raw)
    audio = ["-c:a", "aac", "-b:a", "256k"] if has_audio(raw) and vf is None else ["-an"]
    source_cut = ["-t", f"{min(source, have):.2f}"] if vf else []           # slowed: read only the part that fills the shot
    proc = subprocess.run([find_ffmpeg(), "-y", *(["-ss", f"{start:.2f}"] if start else []), *source_cut, "-i", raw,
                           *(["-vf", vf] if vf else []), "-t", f"{want:.2f}", *_encode(), *audio, path], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0 or not os.path.exists(path):
        shutil.move(raw, path)             # keep the uncut clip rather than losing it
        raise RuntimeError((proc.stderr or "")[-300:])
    return True


def clean_edges(path: str) -> Optional[Dict]:
    """S4.5: drop the neighbouring shot's frames left at the start / end of a shot clip cut from a group clip (clip_measure.stray_edges).
    The uncleaned clip is kept as <name>_edges.mp4. Returns {"head", "tail"} seconds dropped, or None (nothing to drop / unreadable)."""
    import os
    import shutil
    import subprocess
    from . import clip_measure
    from .ffmpeg_studio import find_ffmpeg, has_audio, probe_duration
    try:
        head, tail = clip_measure.stray_edges(path)
    except Exception:  # noqa: BLE001 - OpenCV missing / unreadable clip: kept as it is
        return None
    have = probe_duration(path) or 0.0
    if (head <= 0 and tail <= 0) or have - head - tail < 0.5:
        return None
    keep = os.path.splitext(path)[0] + "_edges.mp4"
    shutil.move(path, keep)
    audio = ["-c:a", "aac", "-b:a", "256k"] if has_audio(keep) else ["-an"]
    proc = subprocess.run([find_ffmpeg(), "-y", "-ss", f"{head:.3f}", "-i", keep, "-t", f"{have - head - tail:.3f}", *_encode(), *audio,
                           path], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0 or not os.path.exists(path):
        shutil.move(keep, path)
        return None
    return {"head": head, "tail": tail}


# ---- continuity groups (GĐ3) -------------------------------------------------------------------------------------------------
MULTISHOT_MAX = 15          # Kling Omni: one multi-shot generation is at most 15 s, each shot at least 3 s
MULTISHOT_MIN_SHOT = 3


def _rows(conn, project_id: int) -> List[Dict]:
    return [{"id": r["id"], "idx": r["idx"], "data": json.loads(r["data"] or "{}")}
            for r in conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,))]


def _group_key(data: Dict):
    return (data.get("story_scene"), data.get("sequence"))


def sequence_rows(conn, scene_id: int) -> List[Dict]:
    """The shots of the same continuity group (same script scene and `sequence`) as this shot, in order; [] for a v2 row."""
    row = conn.execute("SELECT project_id, data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    data = json.loads(row["data"] or "{}") if row else {}
    if not data.get("shot_no"):
        return []
    return [r for r in _rows(conn, row["project_id"]) if _group_key(r["data"]) == _group_key(data)]


def next_in_sequence(conn, scene_id: int) -> Optional[Dict]:
    rows = sequence_rows(conn, scene_id)
    ids = [r["id"] for r in rows]
    if scene_id not in ids or ids.index(scene_id) == len(ids) - 1:
        return None
    return rows[ids.index(scene_id) + 1]


def previous_in_sequence(conn, scene_id: int) -> Optional[Dict]:
    rows = sequence_rows(conn, scene_id)
    ids = [r["id"] for r in rows]
    if scene_id not in ids or ids.index(scene_id) == 0:
        return None
    return rows[ids.index(scene_id) - 1]


def approved_image_path(conn, data_dir: str, project_id: int, scene_id: int) -> Optional[str]:
    import os
    j = conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved' ORDER BY id DESC LIMIT 1",
                     (scene_id,)).fetchone()
    path = j and os.path.join(data_dir, str(project_id), "images", f"job_{j['id']}.png")
    return path if path and os.path.exists(path) else None


def last_frame_for(conn, data_dir: str, scene_id: int) -> Optional[str]:
    """A shot marked `continuous_with_next` ends on the approved start picture of the next shot of its group (Seedance
    first + last frame): the cut between the two shots then matches. None when there is no such picture yet."""
    row = conn.execute("SELECT project_id, data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    if row is None or not json.loads(row["data"] or "{}").get("continuous_with_next"):
        return None
    nxt = next_in_sequence(conn, scene_id)
    return approved_image_path(conn, data_dir, row["project_id"], nxt["id"]) if nxt else None


def waits_for_previous_image(conn, scene_id: int) -> bool:
    """Image of a shot that CONTINUES the previous one: made only once the previous shot's picture is approved, so it can be
    sent along as the reference (runner.chain_previous) — otherwise the batch would send both at once and lose the link."""
    prev = previous_in_sequence(conn, scene_id)
    if prev is None or not prev["data"].get("continuous_with_next"):
        return False
    approved = conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'", (prev["id"],)).fetchone()
    return approved is None


def billed_shot_seconds(data: Dict) -> int:
    import math
    return max(MULTISHOT_MIN_SHOT, math.ceil(float(data.get("duration_s") or MULTISHOT_MIN_SHOT) - 1e-6))


def multishot_groups(conn, project_id: int) -> List[List[Dict]]:
    """Kling multi-shot: consecutive shots of one continuity group, cut into generations of at most 15 s (each shot >= 3 s).
    A shot longer than 15 s on its own stays a group of one."""
    groups: List[List[Dict]] = []
    for r in _rows(conn, project_id):
        if not r["data"].get("shot_no"):
            continue
        sec = billed_shot_seconds(r["data"])
        last = groups[-1] if groups else None
        cast = {str(c) for c in r["data"].get("characters") or []}
        first_cast = {str(c) for c in (last[0]["data"].get("characters") or [])} if last else set()
        # F4 (GĐ6 R4): the whole group is made from its FIRST shot's picture — a later shot with someone not in that picture got an
        # invented person, so such a shot starts a new group (with its own picture)
        if (last and _group_key(last[-1]["data"]) == _group_key(r["data"]) and cast <= first_cast
                and sum(billed_shot_seconds(x["data"]) for x in last) + sec <= MULTISHOT_MAX):
            last.append(r)
        else:
            groups.append([r])
    return groups


def multishot_group_of(conn, scene_id: int) -> Optional[List[Dict]]:
    row = conn.execute("SELECT project_id FROM scenes WHERE id=?", (scene_id,)).fetchone()
    if row is None:
        return None
    for g in multishot_groups(conn, row["project_id"]):
        if any(x["id"] == scene_id for x in g):
            return g
    return None


def split_group_clip(path: str, group: List[Dict], dest_paths: List[str]) -> List[str]:
    """Cut a Kling multi-shot clip into one file per shot (each shot's billed length, in order). The whole clip is kept as
    <name>_group.mp4. Returns the paths written; a shot whose part cannot be cut gets a copy of the whole clip."""
    import os
    import shutil
    import subprocess
    from .ffmpeg_studio import find_ffmpeg, has_audio
    whole = os.path.splitext(path)[0] + "_group.mp4"
    shutil.copyfile(path, whole)
    start, out = 0.0, []
    try:
        ffmpeg = find_ffmpeg()
        audio = ["-c:a", "aac", "-b:a", "256k"] if has_audio(whole) else ["-an"]
    except Exception:  # noqa: BLE001 - no ffmpeg: every shot keeps the whole clip
        ffmpeg = None
    for r, dest in zip(group, dest_paths):
        # a multi-shot generation gives each shot its billed length (>= 3 s); an H5 set-up clip is cut at the shots' own seconds
        sec = float(r["data"]["duration_s"]) if r["data"].get("exact") else billed_shot_seconds(r["data"])
        if r["data"].get("offset") is not None:        # S3.4: a whole-stretch take — each shot at its own place in the stretch
            start = float(r["data"]["offset"])
        ok = False
        if ffmpeg:
            proc = subprocess.run([ffmpeg, "-y", "-ss", f"{start:.2f}", "-i", whole, "-t", f"{sec:.2f}", *_encode(), *audio, dest],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace")
            ok = proc.returncode == 0 and os.path.exists(dest)
        if not ok:
            shutil.copyfile(whole, dest)
        out.append(dest)
        start += sec
    return out


SETUP_MAX = 15.0            # one camera-set-up clip (H5) is at most this long (Kling / Seedance limit)


def setups_on(conn, project_id: int) -> bool:
    """H5 "quay theo vị trí máy": per-shot projects with the camera_setups feature (off until its real test passes)."""
    from . import features
    row = conn.execute("SELECT shot_mode FROM projects WHERE id=?", (project_id,)).fetchone()
    return row is not None and row["shot_mode"] == "per_shot" and features.on("camera_setups")


def setup_groups(conn, project_id: int) -> List[List[Dict]]:
    """H5: the shots of one script scene that share a camera set-up (`camera_setup` A, B…) — made as ONE continuous clip from the first
    shot's picture and cut into the shots (trial 2A: shots 9+10 as one 4 s clip = 33% fewer paid seconds than two 3 s clips). The
    shots need not be next to each other (A B A B); a set-up longer than SETUP_MAX is split. Only groups of 2+ shots."""
    return setup_groups_of(_rows(conn, project_id))


def setup_groups_of(rows: List[Dict]) -> List[List[Dict]]:
    """setup_groups on given rows ({id, idx, data}) — B4 học việc passes rows whose `camera_setup` it guessed (core/trainee_plans)."""
    by_key: Dict = {}
    for r in rows:
        d = r["data"]
        if d.get("shot_no") and d.get("camera_setup"):
            by_key.setdefault((d.get("story_scene"), str(d["camera_setup"]).upper()), []).append(r)
    out: List[List[Dict]] = []
    for members in by_key.values():
        cur, total = [], 0.0
        for r in members:
            sec = float(r["data"].get("duration_s") or 0)
            if cur and total + sec > SETUP_MAX:
                out.append(cur)
                cur, total = [], 0.0
            cur.append(r)
            total += sec
        if cur:
            out.append(cur)
    return sorted((g for g in out if len(g) > 1), key=lambda g: g[0]["idx"])


def group_of(conn, scene_id: int) -> Optional[List[Dict]]:
    """The group whose single generation makes this shot's clip: its Kling multi-shot group, or (H5) its camera-set-up group."""
    row = conn.execute("SELECT s.project_id, p.shot_mode FROM scenes s JOIN projects p ON p.id=s.project_id WHERE s.id=?",
                       (scene_id,)).fetchone()
    if row is None:
        return None
    if row["shot_mode"] == "multishot":
        return multishot_group_of(conn, scene_id)
    from . import seedance_refs
    if seedance_refs.enabled(conn, row["project_id"]):   # Seedance reference-only groups replace H5 set-ups (2026-09-27)
        return seedance_refs.group_of(conn, scene_id)
    if setups_on(conn, row["project_id"]):
        return next((g for g in setup_groups(conn, row["project_id"]) if any(x["id"] == scene_id for x in g)), None)
    return None


def needs_own_image(conn, scene_id: int) -> bool:
    """Kling multi-shot (and an H5 camera set-up) makes the later shots of a group from the group's first picture: only that first
    shot needs a picture."""
    from . import seedance_refs
    if seedance_refs.uses_refs(conn, scene_id):
        return True                                   # a Seedance reference group sends EVERY shot's own storyboard picture
    group = group_of(conn, scene_id) or []
    return len(group) < 2 or group[0]["id"] == scene_id


def image_scene(conn, scene_id: int) -> int:
    """The shot whose picture this shot's video starts from (itself, or the first shot of its group)."""
    if needs_own_image(conn, scene_id):
        return scene_id
    return (group_of(conn, scene_id) or [{"id": scene_id}])[0]["id"]


def stretch_of(conn, group: List[Dict], seconds_of=None) -> Optional[Dict]:
    """S3.4 (kế hoạch sau #8, feature `continuous_takes`): the continuous stretch a camera set-up belongs to — every shot of its script
    scene and sequence from the set-up's first shot to its last, whatever set-up those between were drawn from — so this camera films
    the WHOLE performance and the cut to it lands mid-action (#8: each shot made alone, the movement restarted at every cut; the
    reference drama films one run of acting from several angles and cuts between them). {"rows", "seconds", "offsets": {id: s}}; None
    when the stretch is longer than one clip can be (SETUP_MAX) or the group is not one stretch."""
    if not group:
        return None
    first = group[0]["data"]
    key = (first.get("story_scene"), first.get("sequence"))
    rows = [r for r in _rows(conn, group[0].get("project_id") or conn.execute(
        "SELECT project_id FROM scenes WHERE id=?", (group[0]["id"],)).fetchone()["project_id"])
            if (r["data"].get("story_scene"), r["data"].get("sequence")) == key]
    ids = [r["id"] for r in rows]
    if any(g["id"] not in ids for g in group):
        return None
    a, b = ids.index(group[0]["id"]), max(ids.index(g["id"]) for g in group)
    rows = rows[a:b + 1]
    secs = [float(seconds_of(r) if seconds_of else r["data"].get("duration_s") or 0) for r in rows]
    if sum(secs) > SETUP_MAX:
        return None
    offsets, t = {}, 0.0
    for r, s in zip(rows, secs):
        offsets[r["id"]] = round(t, 2)
        t += s
    return {"rows": rows, "seconds": secs, "offsets": offsets}


def stretch_motion(stretch: Dict, members: List[int], framing: str) -> str:
    """One take of the whole stretch from one camera: what happens in each stretch of time (the actions, English), the camera fixed."""
    from .seedance_refs import _en
    t, parts = 0.0, []
    for r, sec in zip(stretch["rows"], stretch["seconds"]):
        d = r["data"]
        action = str(_en(d, "action") or "").strip().rstrip(".")
        talk = " ".join(f"{x.get('speaker')} speaks." for x in d.get("dialogue") or [] if isinstance(x, dict) and x.get("speaker"))
        parts.append(f"{t:.1f}–{t + sec:.1f}s: {action}{'. ' + talk if talk else '.'}")
        t += sec
    return ("One continuous take: the actors perform the whole stretch below without stopping, filmed from ONE fixed camera set-up "
            f"({framing.strip().rstrip('.') or 'the framing of the first picture'}) — the same framing and camera position all the way "
            "through, no cuts; movements flow from one moment into the next. " + " ".join(parts))


def setup_motion(prompts_and_seconds: List[tuple]) -> str:
    """H5: one continuous-take prompt from the set-up's shots in film order — what happens in each stretch of the clip."""
    t, parts = 0.0, []
    for mp, sec in prompts_and_seconds:
        parts.append(f"{t:.1f}–{t + sec:.1f}s: {str(mp).strip().rstrip('.')}.")
        t += sec
    return ("One continuous take from a single fixed camera set-up — the same framing and camera position all the way through, no cuts. "
            + " ".join(parts))
