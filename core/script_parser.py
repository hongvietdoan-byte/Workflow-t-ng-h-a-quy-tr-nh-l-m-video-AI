import json
import re
import zipfile
from dataclasses import dataclass, field
from typing import List, Optional
from xml.etree import ElementTree as ET

from .pipeline import Pipeline

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_HEADING = re.compile(
    r"^\s*((cảnh|canh|scene|sc|s)\s*\.?\s*\d+\b.*|(int|ext|nội|noi|ngoại|ngoai)[\./\s].*)$", re.IGNORECASE)
_DIALOGUE = re.compile(r"^\s*([^\W\d_][^:\n]{0,28}?)\s*:\s*\S")


@dataclass
class ParsedScene:
    idx: int
    heading: str
    text: str
    characters: List[str] = field(default_factory=list)


def read_docx_paragraphs(path: str) -> List[str]:
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    paragraphs = []
    for p in root.iter(f"{_W}p"):
        text = "".join(t.text or "" for t in p.iter(f"{_W}t")).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def _characters(lines: List[str]) -> List[str]:
    seen = {}
    for line in lines:
        m = _DIALOGUE.match(line)
        if not m:
            continue
        name = m.group(1).strip()
        if len(name.split()) > 3 or _HEADING.match(line):
            continue
        seen[name.upper()] = seen.get(name.upper(), 0) + 1
    return sorted(seen, key=lambda n: (-seen[n], n))


def split_scenes(paragraphs: List[str]) -> List[ParsedScene]:
    groups, current = [], None
    for para in paragraphs:
        if _HEADING.match(para):
            current = {"heading": para, "lines": []}
            groups.append(current)
        elif current is None:
            current = {"heading": "Mở đầu", "lines": [para]}
            groups.append(current)
        else:
            current["lines"].append(para)
    if len(groups) > 1 and groups[0]["heading"] == "Mở đầu":
        groups = groups[1:]  # title/preamble before the first scene heading is not a scene
    return [ParsedScene(i, g["heading"], "\n".join(g["lines"]), _characters(g["lines"]))
            for i, g in enumerate(groups, start=1)]


def parse_docx(path: str) -> List[ParsedScene]:
    return split_scenes(read_docx_paragraphs(path))


def import_scenes(pipeline: Pipeline, project_id: int, scenes: List[ParsedScene],
                  full_text: Optional[str] = None) -> List[int]:
    """Create the scenes of a parsed script. Refuses when the project already has scenes with the same numbers
    (press Reset first) instead of failing halfway; `full_text` keeps the whole script for the side-by-side view."""
    existing = {r["idx"] for r in pipeline.conn.execute("SELECT idx FROM scenes WHERE project_id=?", (project_id,))}
    clash = sorted(existing & {s.idx for s in scenes})
    if clash:
        raise ValueError("Dự án đã có cảnh " + ", ".join(f"S{i:02d}" for i in clash[:5]) + (" …" if len(clash) > 5 else "")
                         + ". Bấm Reset (xóa cảnh chưa có ảnh) rồi phân tích lại.")
    if not scenes:
        raise ValueError("Không tách được cảnh nào: kịch bản cần có dòng tiêu đề như “Cảnh 1”, “Scene 2” hoặc “INT./EXT.”. "
                         "Có thể thêm cảnh thủ công.")
    if full_text is not None:
        pipeline.set_script_text(project_id, full_text)
    ids = []
    for s in scenes:
        scene_id = pipeline.create_scene(project_id, s.idx, s.heading)
        pipeline.conn.execute(
            "UPDATE scenes SET data=? WHERE id=?",
            (json.dumps({"text": s.text, "characters": s.characters}, ensure_ascii=False), scene_id))
        ids.append(scene_id)
    pipeline.conn.commit()
    return ids
