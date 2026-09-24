import json
import re
import zipfile
from dataclasses import dataclass, field
from typing import List, Optional
from xml.etree import ElementTree as ET

from .pipeline import Pipeline

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_HEADING = re.compile(
    r"^\s*((cảnh|canh|scene|sc|s)\s*\.?\s*\d+\b.*|(int|ext)[\./\s].*|(nội|noi|ngoại|ngoai)\s*[\./-].*)$", re.IGNORECASE)
# A20: "Nội dung: …" / "Ngoại hình: …" are body lines, not scene headings (a Vietnamese heading is "NỘI. NHÀ KELLY - NGÀY")
_DIALOGUE = re.compile(r"^\s*([^\W\d_][^:\n]{0,28}?)\s*:\s*\S")
# A section of a short-video script named by its time on screen: "CINEMATIC MỞ ĐẦU – 0–8 GIÂY", "TWIST – 44–50 GIÂY" (a line like
# "THỜI LƯỢNG: 55–58 GIÂY" has no dash before the first number and stays a body line)
_TIMED_HEADING = re.compile(r"^\s*[^:\n]{1,48}?\s[–—-]\s*\d{1,3}\s*[–—-]\s*\d{1,3}\s*(giây|giay|s|sec|secs|seconds)\b\.?\s*$",
                            re.IGNORECASE)
_SEPARATOR = re.compile(r"^\s*[-=_*~·•—–]{3,}\s*$")
_SPEAKER_ONLY = re.compile(r"^\s*([^\W\d_][^:\n]{0,28}?)\s*:\s*$")
_QUOTE_START = ("“", '"', "«", "‘", "'", "„")


def is_heading(line: str) -> bool:
    return bool(_HEADING.match(line) or _TIMED_HEADING.match(line))


def normalise(paragraphs: List[str]) -> List[str]:
    """Drop separator rows (-----) and join a speaker written on its own line with the quoted line under it:
    'Kelly:' + '“Anh nói đi.”' -> 'Kelly: “Anh nói đi.”' (the way `dialogue.lines` and the subtitles read a line)."""
    out: List[str] = []
    for para in paragraphs:
        if _SEPARATOR.match(para):
            continue
        if out and _SPEAKER_ONLY.match(out[-1]) and para.lstrip().startswith(_QUOTE_START):
            out[-1] = out[-1].rstrip() + " " + para.strip()
            continue
        out.append(para)
    return out


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
        from .dialogue import NOT_SPEAKERS
        if len(name.split()) > 3 or is_heading(line) or name.upper() in NOT_SPEAKERS:
            continue
        seen[name.upper()] = seen.get(name.upper(), 0) + 1
    return sorted(seen, key=lambda n: (-seen[n], n))


def split_scenes(paragraphs: List[str]) -> List[ParsedScene]:
    groups, current = [], None
    for para in normalise(paragraphs):
        if is_heading(para):
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
                         + ". Bấm “↺ Làm lại” (xóa cảnh chưa có ảnh) rồi phân tích lại.")
    if not scenes:
        raise ValueError("Không tách được cảnh nào: kịch bản cần có dòng tiêu đề như “Cảnh 1”, “Scene 2” hoặc “INT./EXT.”. "
                         "Có thể thêm cảnh thủ công.")
    if full_text is not None:
        pipeline.set_script_text(project_id, full_text)
    card, scenes = split_end_card(scenes)
    if card:
        store_end_card(pipeline, project_id, card)
    from .dialogue import lines as _dialogue_lines
    if any(_dialogue_lines(s.text) for s in scenes):
        _subtitles_on_by_default(pipeline, project_id)
    ids = []
    for s in scenes:
        scene_id = pipeline.create_scene(project_id, s.idx, s.heading)
        pipeline.conn.execute(
            "UPDATE scenes SET data=? WHERE id=?",
            (json.dumps({"text": s.text, "characters": s.characters}, ensure_ascii=False), scene_id))
        ids.append(scene_id)
    pipeline.conn.commit()
    from .shots import save_story_scenes          # v3: the script's own scenes, kept apart from the shot rows
    save_story_scenes(pipeline, project_id, scenes)
    return ids


_END_CARD = re.compile(r"^\s*(text cuối|card cuối|chữ cuối|khung chữ cuối|end ?card|title card|chữ kết)\s*:?\s*(.*)$", re.IGNORECASE)


def split_end_card(scenes: List[ParsedScene]):
    """A 'TEXT CUỐI:' / 'END CARD:' block at the end of the last scene is the closing card of the video, not part of the scene.
    Returns (card text or None, scenes with that block removed)."""
    if not scenes:
        return None, scenes
    last = scenes[-1]
    rows = last.text.splitlines()
    for i, row in enumerate(rows):
        m = _END_CARD.match(row)
        if m:
            parts = [m.group(2)] + rows[i + 1:]
            card = " ".join(x.strip().strip('"“”*').strip() for x in parts if x.strip())
            if not card:
                return None, scenes
            trimmed = ParsedScene(last.idx, last.heading, chr(10).join(rows[:i]).rstrip(), last.characters)
            return card, scenes[:-1] + [trimmed]
    return None, scenes


def _subtitles_on_by_default(pipeline: Pipeline, project_id: int) -> None:
    """A script with dialogue gets subtitles in its delivery unless the person already chose (Step 5 · Phụ đề)."""
    row = pipeline.project(project_id)
    if "sub_settings" in row.keys() and row["sub_settings"]:
        return
    from . import subtitles
    subtitles.save_settings(pipeline, project_id, {**subtitles.get_settings(pipeline, project_id), "enabled": True})


def store_end_card(pipeline: Pipeline, project_id: int, card: str) -> None:
    """Switch the end card on with the script's text (render settings, core.delivery); the person can change it in Step 5."""
    row = pipeline.project(project_id)
    try:
        settings = json.loads((row["render_settings"] if "render_settings" in row.keys() else None) or "{}")
    except ValueError:
        settings = {}
    end = dict(settings.get("end_card") or {})
    end.update(enabled=True, title=card)
    settings["end_card"] = end
    pipeline.conn.execute("UPDATE projects SET render_settings=? WHERE id=?", (json.dumps(settings, ensure_ascii=False), project_id))
    pipeline.conn.commit()
