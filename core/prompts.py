"""Build copy-paste prompt bundles for V0 (Claude Desktop chat). V1 sends the same text via API."""
import json
import os
from typing import List, Optional

from . import assets, dialogue, knowledge
from .evalset import few_shot_text
from .pipeline import Pipeline

_ROOT = os.path.join(os.path.dirname(__file__), "..")
_SEP = "\n\n---\n\n"
CACHE_BREAK = "\n\n<<<cache>>>\n\n"   # C2: parts before it repeat between calls (Claude API prompt cache); shown to people as _SEP


def _cached(*groups: List[str]) -> str:
    """Join prompt groups (each a list of parts, empty parts dropped) with a cache mark after every group but the last."""
    return CACHE_BREAK.join(_SEP.join(x for x in g if x) for g in groups if any(g))
_SCENE_KEYS = ("location", "time", "characters", "mood", "lighting", "shot", "blocking", "image_prompt", "emotional_intent", "beat",
               "camera_complexity", "shot_role", "dialogue", "duration_s", "sequence")
# v3 shot rows: what the shot contract adds (only present on shot rows, so v2 prompts do not change)
_SHOT_KEYS = ("story_scene", "shot_no", "size", "angle", "camera_move", "role", "action", "end_state", "continuous_with_next")


def _read(*parts: str) -> str:
    with open(os.path.join(_ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def qc_criteria() -> List[str]:
    return [c["key"] for c in json.loads(_read("data", "qc_checklist.json"))["criteria"]]


WORLD_BIBLE_FIELDS = (("render_style", "Phong cách dựng hình"), ("palette", "Bảng màu"), ("lighting_logic", "Logic ánh sáng"),
                      ("texture_finish", "Chất liệu/hoàn thiện hình ảnh"), ("era_lore", "Thời đại/thế giới"),
                      ("physics", "Vật lý/thời tiết"))


def world_bible_text(pipeline: Pipeline, project_id: int) -> str:
    """The project's style bible (set in step 1), as a block every step must inherit; empty when not set."""
    row = pipeline.project(project_id)
    raw = row["world_bible"] if "world_bible" in row.keys() else None   # old database not migrated yet
    try:
        data = json.loads(raw or "{}")
    except ValueError:
        return ""
    lines = [f"- **{label}:** {str(data[key]).strip()}" for key, label in WORLD_BIBLE_FIELDS if str(data.get(key) or "").strip()]
    if not lines:
        return ""
    return ("# World Bible của dự án (BẮT BUỘC kế thừa, không mâu thuẫn)\n" + "\n".join(lines) +
            "\nMọi prompt ảnh/video của dự án dùng lại cách diễn đạt này để các cảnh nhất quán (không cần chép nguyên văn ở mỗi cảnh).")


def people_in_project(pipeline: Pipeline, project_id: int) -> List[str]:
    """Names the FF skill notes are filtered by: Character Bible, the project's character resources, capitalised speakers."""
    conn = pipeline.conn
    names = [r["name"] for r in conn.execute("SELECT name FROM characters WHERE project_id=?", (project_id,))]
    names += [a["name"] for a in assets.project_assets(conn, project_id) if a["kind"] in ("character", "pet")]
    for r in conn.execute("SELECT data FROM scenes WHERE project_id=?", (project_id,)):
        names += [who for who, _ in dialogue.scene_lines(json.loads(r["data"] or "{}")) if who]
    return sorted(set(names))


def bible_block(pipeline: Pipeline, project_id: int) -> str:
    """The Character Bible as it stands: the Director reuses these exact names (a re-run returning "KELLY" for "Kelly" used to add a
    duplicate) and does not rewrite a locked or hand-edited entry."""
    rows = pipeline.conn.execute("SELECT name, description, wardrobe, locked, user_edited FROM characters WHERE project_id=? ORDER BY id",
                                 (project_id,)).fetchall()
    if not rows:
        return ""
    lines = []
    for r in rows:
        keep = "đã khóa" if r["locked"] else ("người dùng đã sửa tay" if r["user_edited"] else "")
        lines.append(f"- {r['name']}" + (f" ({keep} — giữ nguyên mô tả)" if keep else "") + f": {r['description']}"
                     + (f" | trang phục: {r['wardrobe']}" if r["wardrobe"] else ""))
    return ("# Character Bible hiện có (dùng ĐÚNG các tên này, không tạo bản trùng khác hoa/thường hay khác cách viết)\n" + "\n".join(lines))


def locked_block(pipeline: Pipeline, project_id: int) -> str:
    from .llm_io import locked_fields
    rows = locked_fields(pipeline.conn, project_id)
    if not rows:
        return ""
    return ("# Giá trị người dùng đã khóa (GIỮ NGUYÊN, lên kế hoạch xung quanh)\n"
            + "\n".join(f"- {r.get('label') or 'Cảnh ' + str(r['idx'])}: " + json.dumps(r["fields"], ensure_ascii=False) for r in rows))


def project_frame_block(pipeline: Pipeline, project_id: int) -> str:
    from . import formats
    proj = pipeline.project(project_id)
    bits = [formats.director_line(formats.project_aspect(proj))]
    genre = proj["genre"] if "genre" in proj.keys() else None
    if genre:
        bits.append(f"Thể loại của dự án: {genre}" + (" (người dùng đã chọn — giữ nguyên)" if proj["genre_locked"] else ""))
    bits = [b for b in bits if b]
    return ("# Khung hình và thể loại\n" + "\n".join(f"- {b}" for b in bits)) if bits else ""


def shot_style_block(proj) -> str:
    """v3: how Free Fire videos are cut (knowledge/ff_directing.md) + the project's editing style (knowledge/ff_styles/<STYLE>.md)."""
    from . import shots
    parts = [_read("prompts", "17_director_shots.md"), _read("knowledge", "ff_directing.md")]
    st_name = shots.style(proj)
    if st_name:
        path = os.path.join(_ROOT, "knowledge", "ff_styles", f"{st_name}.md")
        if os.path.exists(path):
            parts.append("# Phong cách dựng của dự án (" + st_name + ")\n\n" + _read("knowledge", f"ff_styles/{st_name}.md"))
    return _SEP.join(p for p in parts if p)


def build_director_bundle(pipeline: Pipeline, project_id: int) -> str:
    from . import shots
    proj = pipeline.project(project_id)
    if shots.mode(proj):         # v3: the Director reads the script's scenes (story_scenes) and splits each into shots
        scenes = "\n\n".join(f"### Cảnh {s['idx']} — {s['heading']}\n{s['text']}" for s in shots.story_scenes(pipeline, project_id))
    else:
        rows = pipeline.conn.execute(
            "SELECT idx, title, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall()
        scenes = "\n\n".join(
            f"### Cảnh {r['idx']} — {r['title']}\n{json.loads(r['data'] or '{}').get('text', '')}" for r in rows)
    folded = knowledge.folded_builtin("director")
    keep = lambda rel: "" if f"knowledge/{rel}" in folded else _read("knowledge", rel)  # noqa: E731
    ff = "" if "knowledge/ff_character_skills_visual.md" in folded else knowledge.ff_skills_for(people_in_project(pipeline, project_id))
    return _SEP.join(x for x in [
        _read("prompts", "01_director_scene_analysis.md"),
        project_frame_block(pipeline, project_id),
        keep("cinematography_basics.md"),
        keep("genre_guides.md"),
        knowledge.genre_text(proj["genre"] if "genre" in proj.keys() else None),
        shot_style_block(proj) if shots.mode(proj) else "",
        keep("research_notes.md"),
        keep("film_director_method.md"),
        keep("character_lock.md"),
        keep("dialogue_craft.md"),
        ff,
        assets.context_text(pipeline.conn, project_id),
        standard_block(pipeline, project_id),
        bible_block(pipeline, project_id),
        world_bible_text(pipeline, project_id),
        knowledge.user_text("director"),
        few_shot_text(),
        locked_block(pipeline, project_id),
        script_preamble(proj),
        "# Kịch bản đã tách cảnh\n\n" + scenes,
    ] if x)


def script_preamble(proj) -> str:
    """What the script says before its first scene (title, length, cast, setting such as "Map Đảo Quân Sự — Tháp Đồng Hồ"): it
    applies to every scene, so the Director gets it too."""
    from .script_parser import _HEADING
    text = (proj["script_text"] if "script_text" in proj.keys() else None) or ""
    head = []
    for row in text.splitlines():
        if _HEADING.match(row):
            break
        if row.strip():
            head.append(row.strip())
    return ("# Thông tin chung của kịch bản (trước cảnh đầu tiên — áp dụng cho mọi cảnh)\n" + "\n".join(head)) if head else ""


def standard_block(pipeline: Pipeline, project_id: int) -> str:
    """T1: characters whose look is fixed in the library. The Director writes the story around them, never a new appearance."""
    rows = []
    for r in pipeline.conn.execute("SELECT name FROM characters WHERE project_id=?", (project_id,)):
        prof = assets.standard_for(pipeline.conn, project_id, r["name"])
        if prof:
            rows.append(f"- **{r['name']}** ({prof['asset']}): {prof.get('identity') or ''} — giữ: {prof.get('must_keep') or ''}"
                        + (f"; cao ~{prof['height_m']:g} m" if prof.get("height_m") else ""))
    return ("# Hồ sơ chuẩn nhân vật (Kho — đã duyệt, KHÔNG viết lại ngoại hình; chỉ ghi biến thể của video này như trang phục/bị thương)\n"
            + "\n".join(rows)) if rows else ""


def lock_text(conn, project_id: int, names=None) -> str:
    """Character Lock of the characters (all, or the given names) as a readable block."""
    rows = []
    for r in conn.execute("SELECT name, lock_rules FROM characters WHERE project_id=?", (project_id,)):
        if names is not None and r["name"] not in names:
            continue
        lock, source = assets.standard_for(conn, project_id, r["name"]), " (hồ sơ chuẩn Kho)"   # T1: the library profile wins
        if lock is None:
            source = ""
            try:
                lock = json.loads(r["lock_rules"]) if r["lock_rules"] else None
            except ValueError:
                lock = None
        if not lock:
            continue
        size = f"; cao ~{lock['height_m']:g} m" if lock.get("height_m") else ""
        size += f", {lock['build']}" if lock.get("build") else ""
        rows.append(f"- **{r['name']}**{source} — giữ: {lock.get('must_keep', '')}; được đổi: {lock.get('may_change', '')}; "
                    f"cấm lệch: {lock.get('forbidden', '')}{size}")
    return ("# Character Lock\n" + "\n".join(rows)) if rows else ""


_ROLE_LABEL = {"location": "địa điểm", "object": "đạo cụ", "character": "nhân vật",
               "layout": "LAYOUT — bố cục dựng sẵn: góc máy, vị trí, cỡ và hướng mặt mong muốn; người là hình nộm/ảnh cắt dán"}


def qc_references(pipeline: Pipeline, project_id: int, idx: int, scene_data: dict, data_dir: Optional[str] = None) -> List[dict]:
    """The reference pictures the QC agent compares against: the scene's layout first (when it was laid out), then the same
    character/place/object pictures the image model got."""
    from .layout import layout_reference
    lay = layout_reference(data_dir, project_id, idx, scene_data) if data_dir else None
    return ([lay] if lay else []) + assets.scene_references(pipeline.conn, project_id, scene_data)


def _reference_block(refs: List[dict]) -> str:
    if not refs:
        return ""
    return "# Ảnh tham chiếu (đính kèm sau ảnh cần chấm, theo thứ tự)\n" + "\n".join(
        f"{i}. {r['label']} ({_ROLE_LABEL.get(r['role'], 'nhân vật')})" for i, r in enumerate(refs, 1))


def build_qc_bundle(pipeline: Pipeline, scene_id: int, data_dir: Optional[str] = None) -> str:
    scene = pipeline.conn.execute("SELECT * FROM scenes WHERE id=?", (scene_id,)).fetchone()
    chars = pipeline.conn.execute(
        "SELECT name, description, wardrobe FROM characters WHERE project_id=?",
        (scene["project_id"],)).fetchall()
    bible = "\n".join(f"- {c['name']}: {c['description']} {c['wardrobe'] or ''}".strip() for c in chars)
    data = json.loads(scene["data"] or "{}")
    refs = qc_references(pipeline, scene["project_id"], scene["idx"], data, data_dir)
    spec = {k: data.get(k) for k in _SCENE_KEYS}
    spec.update({k: data[k] for k in _SHOT_KEYS if k in data})
    return _cached([                                     # same for every picture of every project
        _read("prompts", "02_qc_agent.md"),
        "" if "knowledge/ai_image_failure_modes.md" in knowledge.folded_builtin("qc")
        else _read("knowledge", "ai_image_failure_modes.md"),
        _read("knowledge", "character_lock.md"),
        knowledge.user_text("qc"),
    ], [                                                 # same for every picture of this project
        world_bible_text(pipeline, scene["project_id"]),
        "# Character Bible\n" + bible,
    ], [                                                 # this shot
        lock_text(pipeline.conn, scene["project_id"], data.get("characters")),
        "# Thông số cảnh\n" + json.dumps(spec, ensure_ascii=False, indent=2),
        _reference_block(refs),
        "(Đính kèm ảnh cần chấm điểm" + (", rồi các ảnh tham chiếu." if refs else ".") + ")",
    ])


def video_family(pipeline: Pipeline, project_id: int):
    """'omni' (Kling), 'seedance', or None when the project's video model is unset/unknown."""
    from .adapters.clipai import resolve_model
    from .providers import ProviderError
    try:
        return resolve_model(pipeline.project(project_id)["video_model"])[1]
    except ProviderError:
        return None


def motion_scene_rows(pipeline: Pipeline, project_id: int, only_missing: bool = False, only_idx=None):
    """Scenes with an approved image; only_missing: without a motion prompt yet; only_idx: exactly these scenes (e.g. the ones
    whose prompt is outdated)."""
    from .shots import image_scene
    conn = pipeline.conn
    rows = conn.execute(
        "SELECT s.id, s.idx, s.data FROM scenes s WHERE s.project_id=?"
        + (" AND NOT EXISTS (SELECT 1 FROM motion_prompts m WHERE m.scene_id=s.id)" if only_missing else "")
        + " ORDER BY s.idx", (project_id,)).fetchall()
    rows = [r for r in rows if conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'",
                                             (image_scene(conn, r["id"]),)).fetchone()]   # v3 multi-shot: the group's picture
    return [r for r in rows if only_idx is None or r["idx"] in only_idx]


def build_motion_bundle(pipeline: Pipeline, project_id: int, only_missing: bool = False, only_idx=None) -> str:
    """Step 3: scenes that have an approved image, with their spec, the model each will use and the character descriptions.
    only_missing: skip scenes that already have a motion prompt (used by the API runner); only_idx: just these scenes."""
    from . import model_router
    conn = pipeline.conn
    rows = motion_scene_rows(pipeline, project_id, only_missing, only_idx)
    chars = conn.execute("SELECT name, description, wardrobe FROM characters WHERE project_id=?", (project_id,)).fetchall()
    profiles = model_router.load_profiles()["models"]
    all_scenes = {r["idx"]: json.loads(r["data"] or "{}") for r in conn.execute(
        "SELECT idx, data FROM scenes WHERE project_id=?", (project_id,))}

    def extra(r) -> dict:
        data = json.loads(r["data"] or "{}")
        out = {}
        need = dialogue.needed_seconds(dialogue.scene_lines(data))
        if need:
            out["dialogue_min_sec"] = need
        choice = model_router.scene_choice(conn, r["id"])
        out["video_model"] = choice["model"]
        out["max_sec"] = (profiles.get(choice["model"]) or {}).get("max_sec", 15)
        prev = all_scenes.get(r["idx"] - 1) or {}
        if data.get("sequence") and prev.get("sequence") == data.get("sequence") and prev.get("spatial_state"):
            out["previous_spatial_state"] = prev["spatial_state"]
        return out

    scenes = [{"idx": r["idx"], **{k: v for k, v in json.loads(r["data"] or "{}").items() if k in _SCENE_KEYS or k in _SHOT_KEYS},
               **extra(r)}
              for r in rows]
    payload = {"characters": [dict(c) for c in chars], "scenes": scenes}
    folded = knowledge.folded_builtin("motion")
    complexity_known = any(s.get("camera_complexity") for s in scenes)
    any_complex = any(s.get("camera_complexity") == "complex" for s in scenes)
    uses_seedance = any("seedance" in (s.get("video_model") or "") for s in scenes) or video_family(pipeline, project_id) == "seedance"
    parts = [_read("prompts", "03_video_motion.md")]
    for rel in ("video_motion_vocab.md", "research_notes.md", "t2v_prompt_structure.md"):
        if f"knowledge/{rel}" not in folded:
            parts.append(_read("knowledge", rel))
    if (any_complex or not complexity_known) and "knowledge/motion_complex_shots.md" not in folded:
        parts.append(_read("knowledge", "motion_complex_shots.md"))
    if any_complex:
        parts.append(_read("knowledge", "motion_prompt_lint.md"))
    if "knowledge/ff_character_skills_visual.md" not in folded:
        ff = knowledge.ff_skills_for(people_in_project(pipeline, project_id))
        if ff:
            parts.append(ff)
    lock = lock_text(conn, project_id)
    if lock:
        parts.append(lock)
    if uses_seedance:
        for rel in ("seedance_prompting.md", "seedance_director_workflow.md"):
            if f"knowledge/{rel}" not in folded:
                parts.append(_read("knowledge", rel))
    wb = world_bible_text(pipeline, project_id)
    if wb:
        parts.append(wb)
    extra = knowledge.user_text("motion")
    return _SEP.join(parts + ([extra] if extra else [])) + CACHE_BREAK + (       # rules repeat between batches (C2)
        "# Cảnh đã có ảnh được duyệt\n```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```")
