"""Project style bible (World Bible) drafted from reference images.

Claude looks at 1-6 reference pictures and drafts render_style / palette / texture_finish (+ optional lighting_logic and
candidate atmosphere elements). It is only a DRAFT: the person edits it in step 1 and saves it, and only then does it
reach the Director / Motion prompts (`prompts.world_bible_text`).
"""
import json
import os
from typing import Dict, List

from . import llm_runner
from .pipeline import Pipeline

MAX_REFS = 6
FIELDS = ("render_style", "palette", "texture_finish", "lighting_logic", "era_lore", "physics")


def _prompt() -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "prompts", "06_style_analyst.md")
    with open(path, encoding="utf-8") as f:
        return f.read()


def validate(obj) -> None:
    if not isinstance(obj, dict):
        raise ValueError("kết quả không phải một đối tượng JSON")
    for key in ("render_style", "palette", "texture_finish"):
        if not isinstance(obj.get(key), str) or not obj[key].strip():
            raise ValueError(f"thiếu mục '{key}'")
    if obj.get("candidate_elements") is not None and not isinstance(obj["candidate_elements"], list):
        raise ValueError("candidate_elements phải là danh sách")


def analyse(client, image_paths: List[str], note=None) -> Dict:
    """Draft a style bible from reference images. Returns the parsed JSON (fields + candidate_elements + check_flags)."""
    paths = [p for p in image_paths if os.path.exists(p)][:MAX_REFS]
    if not paths:
        raise llm_runner.LlmError("chưa có ảnh tham khảo để phân tích", code="config")
    images = [(f"Ảnh tham khảo {i}:", p) for i, p in enumerate(paths, 1)]
    obj, _, _ = llm_runner.ask_json(client, _prompt(), validate, images, note=note)
    if len(paths) == 1 and obj.get("confidence") == "high":
        obj["confidence"] = "medium"                     # one picture cannot separate style from accident
        obj.setdefault("check_flags", []).append("chỉ 1 ảnh tham khảo, nên bổ sung thêm ảnh")
    return obj


def load(pipeline: Pipeline, project_id: int) -> Dict[str, str]:
    try:
        row = pipeline.project(project_id)
        data = json.loads((row["world_bible"] if "world_bible" in row.keys() else None) or "{}")
    except ValueError:
        return {}
    return {k: str(data.get(k) or "") for k in FIELDS}


def save(pipeline: Pipeline, project_id: int, fields: Dict[str, str]) -> None:
    clean = {k: (fields.get(k) or "").strip() for k in FIELDS if (fields.get(k) or "").strip()}
    pipeline.conn.execute("UPDATE projects SET world_bible=? WHERE id=?", (json.dumps(clean, ensure_ascii=False) if clean else None,
                                                                            project_id))
    pipeline.conn.commit()


# ---- presets: a saved World Bible reused by other projects (style-analyst "preset library") -----------------------------
def list_presets(conn) -> List[Dict]:
    return [{"id": r["id"], "name": r["name"], "data": json.loads(r["data"] or "{}"), "created_by": r["created_by"]}
            for r in conn.execute("SELECT * FROM style_presets ORDER BY name")]


def save_preset(pipeline: Pipeline, project_id: int, name: str) -> None:
    from datetime import datetime, timezone
    name = (name or "").strip()
    data = load(pipeline, project_id)
    if not name:
        raise ValueError("cần đặt tên cho mẫu phong cách")
    if not any((v or "").strip() for v in data.values()):
        raise ValueError("World Bible của dự án đang trống: chưa có gì để lưu làm mẫu")
    pipeline.conn.execute("INSERT INTO style_presets (name, data, created_at, created_by) VALUES (?,?,?,?)"
                          " ON CONFLICT(name) DO UPDATE SET data=excluded.data", (name, json.dumps(data, ensure_ascii=False),
                                                                             datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                                                             pipeline.actor))
    pipeline.conn.commit()


def use_preset(pipeline: Pipeline, project_id: int, preset_id: int) -> None:
    row = pipeline.conn.execute("SELECT data FROM style_presets WHERE id=?", (preset_id,)).fetchone()
    if row is None:
        raise ValueError("không tìm thấy mẫu phong cách")
    save(pipeline, project_id, json.loads(row["data"] or "{}"))
