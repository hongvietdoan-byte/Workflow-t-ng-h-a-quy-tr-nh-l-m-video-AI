"""Build copy-paste prompt bundles for V0 (Claude Desktop chat). V1 sends the same text via API."""
import json
import os
from typing import List

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


def build_director_bundle(pipeline: Pipeline, project_id: int) -> str:
    rows = pipeline.conn.execute(
        "SELECT idx, title, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall()
    scenes = "\n\n".join(
        f"### Cảnh {r['idx']} — {r['title']}\n{json.loads(r['data'] or '{}').get('text', '')}" for r in rows)
    return _SEP.join([
        _read("prompts", "01_director_scene_analysis.md"),
        _read("knowledge", "cinematography_basics.md"),
        _read("knowledge", "genre_guides.md"),
        _read("knowledge", "research_notes.md"),
        few_shot_text(),
        "# Kịch bản đã tách cảnh\n\n" + scenes,
    ])


def build_qc_bundle(pipeline: Pipeline, scene_id: int) -> str:
    scene = pipeline.conn.execute("SELECT * FROM scenes WHERE id=?", (scene_id,)).fetchone()
    chars = pipeline.conn.execute(
        "SELECT name, description, wardrobe FROM characters WHERE project_id=?",
        (scene["project_id"],)).fetchall()
    bible = "\n".join(f"- {c['name']}: {c['description']} {c['wardrobe'] or ''}".strip() for c in chars)
    data = json.loads(scene["data"] or "{}")
    spec = {k: data.get(k) for k in _SCENE_KEYS}
    return _SEP.join([
        _read("prompts", "02_qc_agent.md"),
        _read("knowledge", "ai_image_failure_modes.md"),
        "# Character Bible\n" + bible,
        "# Thông số cảnh\n" + json.dumps(spec, ensure_ascii=False, indent=2),
        "(Đính kèm ảnh cần chấm điểm.)",
    ])


def video_family(pipeline: Pipeline, project_id: int):
    """'omni' (Kling), 'seedance', or None when the project's video model is unset/unknown."""
    from .adapters.clipai import resolve_model
    from .providers import ProviderError
    try:
        return resolve_model(pipeline.project(project_id)["video_model"])[1]
    except ProviderError:
        return None


def build_motion_bundle(pipeline: Pipeline, project_id: int) -> str:
    """Step 3: scenes that have an approved image, with their spec and the character descriptions."""
    conn = pipeline.conn
    rows = conn.execute(
        "SELECT s.idx, s.data FROM scenes s WHERE s.project_id=? AND EXISTS (SELECT 1 FROM jobs j WHERE"
        " j.scene_id=s.id AND j.type='image_gen' AND j.state='approved') ORDER BY s.idx", (project_id,)).fetchall()
    chars = conn.execute("SELECT name, description FROM characters WHERE project_id=?", (project_id,)).fetchall()
    payload = {
        "characters": [dict(c) for c in chars],
        "scenes": [{"idx": r["idx"], **{k: v for k, v in json.loads(r["data"] or "{}").items() if k in _SCENE_KEYS}}
                   for r in rows],
    }
    parts = [
        _read("prompts", "03_video_motion.md"),
        _read("knowledge", "video_motion_vocab.md"),
        _read("knowledge", "research_notes.md"),
    ]
    if video_family(pipeline, project_id) == "seedance":
        parts.append(_read("knowledge", "seedance_prompting.md"))
    return _SEP.join(parts + [
        "# Cảnh đã có ảnh được duyệt\n```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```",
    ])
