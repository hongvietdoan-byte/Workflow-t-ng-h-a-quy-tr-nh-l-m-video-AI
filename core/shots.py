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
SIZES = ("ECU", "CU", "MCU", "MS", "WS", "EWS", "GAME_TPS")          # same vocabulary as the reference analysis (no GRAPHIC:
ANGLES = ("eye", "low", "high", "overhead", "dutch", "ots", "pov")   # titles / cards are made in post, not by the video model)
MOVES = ("static", "push_in", "pull_out", "pan", "tilt", "track", "orbit", "handheld", "crane", "whip", "zoom")
ROLES = ("hook", "setup", "action", "reaction", "insert", "dialogue", "transition", "ending")
SIZE_WORDS = {"ECU": "extreme close-up", "CU": "close-up", "MCU": "medium close-up", "MS": "medium shot", "WS": "wide shot",
              "EWS": "extreme wide shot", "GAME_TPS": "third-person game camera behind the character, slightly above the shoulder"}
MIN_SHOT, MAX_SHOT = 0.5, 15.0
# what a shot row keeps from its script scene (Director fields of the whole scene)
SCENE_KEYS = ("location", "time", "mood", "lighting", "location_asset", "emotional_intent", "beat")


class ShotError(ValueError):
    pass


def mode(proj) -> Optional[str]:
    value = proj["shot_mode"] if proj is not None and "shot_mode" in proj.keys() else None
    return value if value in MODES and value else None


def active(pipeline: Pipeline, project_id: int) -> bool:
    return mode(pipeline.project(project_id)) is not None


def style(proj) -> Optional[str]:
    value = proj["style_profile"] if proj is not None and "style_profile" in proj.keys() else None
    return value or None


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
        for key in ("start_frame", "end_state"):
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
    from .dialogue import NOT_SPEAKERS
    spoken, screen = [], [str(x).strip() for x in s.get("on_screen_text") or [] if str(x).strip()]
    for d in s.get("dialogue") or []:
        who, said = str(d.get("speaker") or "").strip(), str(d["text"]).strip()
        (screen.append(said) if who.upper() in NOT_SPEAKERS else spoken.append({"speaker": who, "text": said}))
    return spoken, screen


def shot_data(scene: Dict, s: Dict, k: int) -> Dict:
    """The data of one shot row: the script scene's setting + the shot's own camera, action and lines."""
    spoken, screen = _split_lines(s)
    data = {key: scene[key] for key in SCENE_KEYS if key in scene}
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
    for key in ("weather", "plate_spot", "plate_mode"):
        value = s.get(key) or scene.get(key)
        if isinstance(value, str) and value.strip():
            data[key] = value.strip()
    return data


def has_work(conn, project_id: int) -> bool:
    return bool(conn.execute("SELECT 1 FROM jobs WHERE project_id=? AND scene_id IS NOT NULL LIMIT 1", (project_id,)).fetchone())


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
        conn.execute(f"DELETE FROM scenes WHERE id IN ({marks})", [r["id"] for r in gone])
    n = conn.execute("SELECT COALESCE(MAX(idx), 0) FROM scenes WHERE project_id=?", (project_id,)).fetchone()[0]
    written = 0
    for s in sorted((x for x in scenes if x["idx"] >= from_scene), key=lambda x: x["idx"]):
        heading = (story.get(s["idx"]) or {}).get("heading") or f"CẢNH {s['idx']}"
        for k, shot in enumerate(s["shots"], 1):
            n += 1
            data = shot_data(s, shot, k)
            if s["idx"] != from_scene:                   # only the re-planned scene may lose its hand edits (its shots changed)
                data.update(kept.get((data.get("story_scene"), data.get("shot_no")), {}))
            conn.execute("INSERT INTO scenes (project_id, idx, title, data) VALUES (?,?,?,?)",
                         (project_id, n, f"{heading} · shot {k}", json.dumps(data, ensure_ascii=False)))
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
    conn.execute("DELETE FROM scenes WHERE project_id=?", (project_id,))
    n = 0
    for s in sorted(scenes, key=lambda x: x["idx"]):
        heading = (story.get(s["idx"]) or {}).get("heading") or f"CẢNH {s['idx']}"
        for k, shot in enumerate(s["shots"], 1):
            n += 1
            data = shot_data(s, shot, k)
            data.update(kept.get((data.get("story_scene"), data.get("shot_no")), {}))
            conn.execute("INSERT INTO scenes (project_id, idx, title, data) VALUES (?,?,?,?)",
                         (project_id, n, f"{heading} · shot {k}", json.dumps(data, ensure_ascii=False)))
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


def trim_clip(pipeline: Pipeline, scene_id: int, path: str) -> bool:
    """Cut a downloaded clip of a SHOT row to the shot's planned length: the full clip is kept next to it as <name>_raw.mp4.
    Nothing happens for v2 rows, clips already short enough, or files ffmpeg cannot read. Returns True when cut."""
    import os
    import shutil
    import subprocess
    from .ffmpeg_studio import find_ffmpeg, has_audio, probe_duration
    row = pipeline.conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    if row is None or not json.loads(row["data"] or "{}").get("shot_no"):
        return False
    want = planned_seconds(pipeline.conn, scene_id)
    have = probe_duration(path) if os.path.exists(path) else None
    if not want or not have or have <= want + TRIM_SLACK:
        return False
    raw = os.path.splitext(path)[0] + "_raw.mp4"
    shutil.move(path, raw)
    audio = ["-c:a", "aac"] if has_audio(raw) else ["-an"]
    proc = subprocess.run([find_ffmpeg(), "-y", "-i", raw, "-t", f"{want:.2f}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                           "-preset", "veryfast", *audio, path], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0 or not os.path.exists(path):
        shutil.move(raw, path)             # keep the uncut clip rather than losing it
        raise RuntimeError((proc.stderr or "")[-300:])
    return True


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
        audio = ["-c:a", "aac"] if has_audio(whole) else ["-an"]
    except Exception:  # noqa: BLE001 - no ffmpeg: every shot keeps the whole clip
        ffmpeg = None
    for r, dest in zip(group, dest_paths):
        # a multi-shot generation gives each shot its billed length (>= 3 s); an H5 set-up clip is cut at the shots' own seconds
        sec = float(r["data"]["duration_s"]) if r["data"].get("exact") else billed_shot_seconds(r["data"])
        ok = False
        if ffmpeg:
            proc = subprocess.run([ffmpeg, "-y", "-ss", f"{start:.2f}", "-i", whole, "-t", f"{sec:.2f}", "-c:v", "libx264",
                                   "-pix_fmt", "yuv420p", "-preset", "veryfast", *audio, dest],
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
    by_key: Dict = {}
    for r in _rows(conn, project_id):
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
    if setups_on(conn, row["project_id"]):
        return next((g for g in setup_groups(conn, row["project_id"]) if any(x["id"] == scene_id for x in g)), None)
    return None


def needs_own_image(conn, scene_id: int) -> bool:
    """Kling multi-shot (and an H5 camera set-up) makes the later shots of a group from the group's first picture: only that first
    shot needs a picture."""
    group = group_of(conn, scene_id) or []
    return len(group) < 2 or group[0]["id"] == scene_id


def image_scene(conn, scene_id: int) -> int:
    """The shot whose picture this shot's video starts from (itself, or the first shot of its group)."""
    if needs_own_image(conn, scene_id):
        return scene_id
    return (group_of(conn, scene_id) or [{"id": scene_id}])[0]["id"]


def setup_motion(prompts_and_seconds: List[tuple]) -> str:
    """H5: one continuous-take prompt from the set-up's shots in film order — what happens in each stretch of the clip."""
    t, parts = 0.0, []
    for mp, sec in prompts_and_seconds:
        parts.append(f"{t:.1f}–{t + sec:.1f}s: {str(mp).strip().rstrip('.')}.")
        t += sec
    return ("One continuous take from a single fixed camera set-up — the same framing and camera position all the way through, no cuts. "
            + " ".join(parts))
