import json
import re
import zipfile
from dataclasses import dataclass, field
from typing import List
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
    return [ParsedScene(i, g["heading"], "\n".join(g["lines"]), _characters(g["lines"]))
            for i, g in enumerate(groups, start=1)]


def parse_docx(path: str) -> List[ParsedScene]:
    return split_scenes(read_docx_paragraphs(path))


def import_scenes(pipeline: Pipeline, project_id: int, scenes: List[ParsedScene]) -> List[int]:
    ids = []
    for s in scenes:
        scene_id = pipeline.create_scene(project_id, s.idx, s.heading)
        pipeline.conn.execute(
            "UPDATE scenes SET data=? WHERE id=?",
            (json.dumps({"text": s.text, "characters": s.characters}, ensure_ascii=False), scene_id))
        ids.append(scene_id)
    pipeline.conn.commit()
    return ids
