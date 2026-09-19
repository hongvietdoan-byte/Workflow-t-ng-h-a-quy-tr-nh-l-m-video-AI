"""Build copy-paste prompt bundles for V0 (Claude Desktop chat). V1 sends the same text via API."""
import json
import os
from typing import List

from .pipeline import Pipeline

_ROOT = os.path.join(os.path.dirname(__file__), "..")


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
    return "\n\n---\n\n".join([
        _read("prompts", "01_director_scene_analysis.md"),
        _read("knowledge", "cinematography_basics.md"),
        "# Kịch bản đã tách cảnh\n\n" + scenes,
    ])


def build_qc_bundle(pipeline: Pipeline, scene_id: int) -> str:
    scene = pipeline.conn.execute("SELECT * FROM scenes WHERE id=?", (scene_id,)).fetchone()
    chars = pipeline.conn.execute(
        "SELECT name, description, wardrobe FROM characters WHERE project_id=?",
        (scene["project_id"],)).fetchall()
    bible = "\n".join(f"- {c['name']}: {c['description']} {c['wardrobe'] or ''}".strip() for c in chars)
    data = json.loads(scene["data"] or "{}")
    spec = {k: data.get(k) for k in ("location", "time", "characters", "mood", "lighting", "shot", "image_prompt")}
    return "\n\n---\n\n".join([
        _read("prompts", "02_qc_agent.md"),
        "# Character Bible\n" + bible,
        "# Thông số cảnh\n" + json.dumps(spec, ensure_ascii=False, indent=2),
        "(Đính kèm ảnh cần chấm điểm.)",
    ])
