"""Build copy-paste prompt bundles for V0 (Claude Desktop chat). V1 sends the same text via API."""
import json
import os
from typing import List

from . import knowledge
from .evalset import few_shot_text
from .pipeline import Pipeline

_ROOT = os.path.join(os.path.dirname(__file__), "..")
_SEP = "\n\n---\n\n"
_SCENE_KEYS = ("location", "time", "characters", "mood", "lighting", "shot", "image_prompt")


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
    raw = pipeline.project(project_id)["world_bible"]
    try:
        data = json.loads(raw or "{}")
    except ValueError:
        return ""
    lines = [f"- **{label}:** {str(data[key]).strip()}" for key, label in WORLD_BIBLE_FIELDS if str(data.get(key) or "").strip()]
    if not lines:
        return ""
    return ("# World Bible của dự án (BẮT BUỘC kế thừa, không mâu thuẫn)\n" + "\n".join(lines) +
            "\nMọi prompt ảnh/video của dự án dùng lại cách diễn đạt này để các cảnh nhất quán (không cần chép nguyên văn ở mỗi cảnh).")


def build_director_bundle(pipeline: Pipeline, project_id: int) -> str:
    rows = pipeline.conn.execute(
        "SELECT idx, title, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall()
    scenes = "\n\n".join(
        f"### Cảnh {r['idx']} — {r['title']}\n{json.loads(r['data'] or '{}').get('text', '')}" for r in rows)
    folded = knowledge.folded_builtin("director")
    keep = lambda rel: "" if f"knowledge/{rel}" in folded else _read("knowledge", rel)  # noqa: E731
    return _SEP.join(x for x in [
        _read("prompts", "01_director_scene_analysis.md"),
        keep("cinematography_basics.md"),
        keep("genre_guides.md"),
        keep("research_notes.md"),
        keep("film_director_method.md"),
        world_bible_text(pipeline, project_id),
        knowledge.user_text("director"),
        few_shot_text(),
        "# Kịch bản đã tách cảnh\n\n" + scenes,
    ] if x)


def build_qc_bundle(pipeline: Pipeline, scene_id: int) -> str:
    scene = pipeline.conn.execute("SELECT * FROM scenes WHERE id=?", (scene_id,)).fetchone()
    chars = pipeline.conn.execute(
        "SELECT name, description, wardrobe FROM characters WHERE project_id=?",
        (scene["project_id"],)).fetchall()
    bible = "\n".join(f"- {c['name']}: {c['description']} {c['wardrobe'] or ''}".strip() for c in chars)
    data = json.loads(scene["data"] or "{}")
    spec = {k: data.get(k) for k in _SCENE_KEYS}
    return _SEP.join(x for x in [
        _read("prompts", "02_qc_agent.md"),
        "" if "knowledge/ai_image_failure_modes.md" in knowledge.folded_builtin("qc")
        else _read("knowledge", "ai_image_failure_modes.md"),
        knowledge.user_text("qc"),
        "# Character Bible\n" + bible,
        "# Thông số cảnh\n" + json.dumps(spec, ensure_ascii=False, indent=2),
        "(Đính kèm ảnh cần chấm điểm.)",
    ] if x)


def video_family(pipeline: Pipeline, project_id: int):
    """'omni' (Kling), 'seedance', or None when the project's video model is unset/unknown."""
    from .adapters.clipai import resolve_model
    from .providers import ProviderError
    try:
        return resolve_model(pipeline.project(project_id)["video_model"])[1]
    except ProviderError:
        return None


def build_motion_bundle(pipeline: Pipeline, project_id: int, only_missing: bool = False) -> str:
    """Step 3: scenes that have an approved image, with their spec and the character descriptions.
    only_missing: skip scenes that already have a motion prompt (used by the API runner)."""
    conn = pipeline.conn
    rows = conn.execute(
        "SELECT s.idx, s.data FROM scenes s WHERE s.project_id=? AND EXISTS (SELECT 1 FROM jobs j WHERE"
        " j.scene_id=s.id AND j.type='image_gen' AND j.state='approved')"
        + (" AND NOT EXISTS (SELECT 1 FROM motion_prompts m WHERE m.scene_id=s.id)" if only_missing else "")
        + " ORDER BY s.idx", (project_id,)).fetchall()
    chars = conn.execute("SELECT name, description FROM characters WHERE project_id=?", (project_id,)).fetchall()
    payload = {
        "characters": [dict(c) for c in chars],
        "scenes": [{"idx": r["idx"], **{k: v for k, v in json.loads(r["data"] or "{}").items() if k in _SCENE_KEYS}}
                   for r in rows],
    }
    folded = knowledge.folded_builtin("motion")
    parts = [_read("prompts", "03_video_motion.md")]
    for rel in ("video_motion_vocab.md", "research_notes.md", "t2v_prompt_structure.md", "motion_complex_shots.md"):
        if f"knowledge/{rel}" not in folded:
            parts.append(_read("knowledge", rel))
    if video_family(pipeline, project_id) == "seedance":
        for rel in ("seedance_prompting.md", "seedance_director_workflow.md"):
            if f"knowledge/{rel}" not in folded:
                parts.append(_read("knowledge", rel))
    wb = world_bible_text(pipeline, project_id)
    if wb:
        parts.append(wb)
    extra = knowledge.user_text("motion")
    return _SEP.join(parts + ([extra] if extra else []) + [
        "# Cảnh đã có ảnh được duyệt\n```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```",
    ])
