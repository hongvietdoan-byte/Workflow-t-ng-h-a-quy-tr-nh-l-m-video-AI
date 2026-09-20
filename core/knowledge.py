"""Knowledge base of the Claude steps (Director, QC, motion prompt): what ships with the project and what the
user adds.

Built-in documents live in the repo (`knowledge/`, `prompts/`, `eval/golden.json`) and are versioned with the code.
Documents the user uploads live OUTSIDE git in `data/knowledge_user/<step>/` (override: KNOWLEDGE_USER_DIR) and are
appended to that step's prompt while they are switched on, so the step improves without touching code.

Every enabled document is sent to Claude on every run of the step, so size costs tokens: per-document and per-step
limits keep prompts (and the bill) bounded.
"""
import json
import os
import re
import tempfile
import time
from typing import Dict, List, Optional

ROOT = os.path.join(os.path.dirname(__file__), "..")
MAX_DOC_CHARS = 50_000       # one uploaded document
MAX_USER_CHARS = 150_000     # all uploaded documents of one step
ALLOWED = (".md", ".txt", ".docx")

# step -> (label, what it does, built-in files [(relative path, title, note)])
GROUPS: Dict[str, tuple] = {
    "director": ("Director — phân tích kịch bản (Bước 1)",
                 "Lập Character Bible và thông số từng cảnh (địa điểm, ánh sáng, cỡ cảnh, prompt ảnh).",
                 [("prompts/01_director_scene_analysis.md", "Prompt Director", "vai trò, cách suy nghĩ, định dạng JSON"),
                  ("knowledge/cinematography_basics.md", "Cơ bản điện ảnh", "cỡ cảnh, góc máy, ánh sáng, chuyển động"),
                  ("knowledge/genre_guides.md", "Hướng dẫn 7 thể loại", "công thức viết prompt ảnh theo thể loại"),
                  ("knowledge/research_notes.md", "Nguyên tắc từ nguồn nghiên cứu", "16 nguyên tắc, 8 chiều điện ảnh"),
                  ("eval/golden.json", "Ví dụ mẫu (few-shot)", "3 cặp đầu vào → kết quả chuẩn")]),
    "qc": ("QC — chấm điểm ảnh (Bước 2)",
           "Chấm ảnh theo 5 tiêu chí so với Character Bible và thông số cảnh.",
           [("prompts/02_qc_agent.md", "Prompt QC", "tiêu chí và định dạng chấm"),
            ("knowledge/ai_image_failure_modes.md", "Lỗi thường gặp của ảnh AI", "tay, mặt, chữ, chi tiết thừa…")]),
    "motion": ("Motion prompt — chuyển động video (Bước 3)",
               "Viết câu lệnh chuyển động cho từng cảnh có ảnh đã duyệt.",
               [("prompts/03_video_motion.md", "Prompt motion", "quy tắc và định dạng JSON"),
                ("knowledge/video_motion_vocab.md", "Từ vựng camera / chuyển động", ""),
                ("knowledge/research_notes.md", "Nguyên tắc từ nguồn nghiên cứu", "dùng chung với Director"),
                ("knowledge/seedance_prompting.md", "Cách viết prompt Seedance", "chỉ gắn khi model video là Seedance")]),
}


def user_root() -> str:
    return os.environ.get("KNOWLEDGE_USER_DIR") or os.path.join(ROOT, "data", "knowledge_user")


def group_dir(group: str) -> str:
    if group not in GROUPS:
        raise ValueError(f"unknown knowledge group '{group}'")
    path = os.path.join(user_root(), group)
    os.makedirs(path, exist_ok=True)
    return path


def approx_tokens(chars: int) -> int:
    """Rough token count for Vietnamese-heavy text (about 2.5 characters per token)."""
    return round(chars / 2.5)


def _manifest(group: str) -> str:
    return os.path.join(group_dir(group), "docs.json")


def _load(group: str) -> List[Dict]:
    try:
        with open(_manifest(group), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _save(group: str, docs: List[Dict]) -> None:
    with open(_manifest(group), "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=1)


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def builtin_docs(group: str) -> List[Dict]:
    out = []
    for rel, title, note in GROUPS[group][2]:
        path = os.path.join(ROOT, *rel.split("/"))
        text = _read(path)
        out.append({"source": "builtin", "title": title, "note": note, "file": rel, "path": os.path.abspath(path),
                    "chars": len(text), "enabled": True, "exists": bool(text)})
    return out


def user_docs(group: str) -> List[Dict]:
    out = []
    for d in _load(group):
        path = os.path.join(group_dir(group), d["file"])
        if os.path.exists(path):
            out.append({"source": "user", "title": d["title"], "note": d.get("note", ""), "file": d["file"],
                        "path": os.path.abspath(path), "chars": d["chars"], "enabled": d.get("enabled", True),
                        "added_at": d.get("added_at"), "exists": True})
    return out


def overview(group: str) -> Dict:
    """Everything the step knows: documents (built-in + user) and how much text one run sends to Claude."""
    docs = builtin_docs(group) + user_docs(group)
    sent = sum(d["chars"] for d in docs if d["enabled"])
    user_sent = sum(d["chars"] for d in docs if d["enabled"] and d["source"] == "user")
    return {"docs": docs, "chars": sent, "tokens": approx_tokens(sent), "user_chars": user_sent,
            "user_dir": group_dir(group), "builtin_dir": os.path.abspath(os.path.join(ROOT, "knowledge"))}


def read_doc(group: str, source: str, file: str) -> str:
    base = ROOT if source == "builtin" else group_dir(group)
    path = os.path.join(base, *file.split("/"))
    if os.path.commonpath([os.path.abspath(path), os.path.abspath(base)]) != os.path.abspath(base):
        raise ValueError("path outside the knowledge folders")
    return _read(path)


def _slug(name: str) -> str:
    stem = os.path.splitext(os.path.basename(name))[0]
    stem = re.sub(r"[^\w\-]+", "_", stem, flags=re.UNICODE).strip("_")
    return stem[:60] or "tai_lieu"


def _extract(filename: str, data: bytes) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED:
        raise ValueError("Chỉ nhận file .md, .txt hoặc .docx")
    if ext == ".docx":
        from .script_parser import read_docx_paragraphs
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(data)
        try:
            return "\n\n".join(read_docx_paragraphs(f.name))
        finally:
            os.remove(f.name)
    for enc in ("utf-8-sig", "utf-16"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def add_doc(group: str, filename: str, data: bytes, title: Optional[str] = None, note: str = "") -> Dict:
    """Add an uploaded document to a step's knowledge base (enabled at once)."""
    text = _extract(filename, data).strip()
    if not text:
        raise ValueError("Tài liệu rỗng")
    if len(text) > MAX_DOC_CHARS:
        raise ValueError(f"Tài liệu dài {len(text):,} ký tự; tối đa {MAX_DOC_CHARS:,} (≈ {approx_tokens(MAX_DOC_CHARS):,} token). "
                         "Hãy rút gọn hoặc tách nhỏ.")
    docs = _load(group)
    used = sum(d["chars"] for d in docs if d.get("enabled", True))
    if used + len(text) > MAX_USER_CHARS:
        raise ValueError(f"Tổng tài liệu bổ sung của bước này sẽ vượt {MAX_USER_CHARS:,} ký tự "
                         f"(đang dùng {used:,}). Tắt hoặc xóa bớt tài liệu cũ trước.")
    folder = group_dir(group)
    stem, n = _slug(filename), 1
    file = f"{stem}.md"
    while os.path.exists(os.path.join(folder, file)):
        n += 1
        file = f"{stem}_{n}.md"
    with open(os.path.join(folder, file), "w", encoding="utf-8") as f:
        f.write(text)
    entry = {"file": file, "title": (title or "").strip() or os.path.splitext(os.path.basename(filename))[0],
             "note": note.strip(), "original": os.path.basename(filename), "chars": len(text), "enabled": True,
             "added_at": time.strftime("%Y-%m-%d %H:%M")}
    docs.append(entry)
    _save(group, docs)
    return entry


def set_enabled(group: str, file: str, enabled: bool) -> None:
    docs = _load(group)
    for d in docs:
        if d["file"] == file:
            d["enabled"] = bool(enabled)
            _save(group, docs)
            return
    raise KeyError(f"'{file}' is not an uploaded document of this step")


def remove_doc(group: str, file: str) -> None:
    docs = _load(group)
    if not any(d["file"] == file for d in docs):
        raise KeyError(f"'{file}' is not an uploaded document of this step")
    _save(group, [d for d in docs if d["file"] != file])
    try:
        os.remove(os.path.join(group_dir(group), file))
    except OSError:
        pass


def user_text(group: str) -> str:
    """The enabled uploaded documents as one block appended to the step's prompt ('' when there are none)."""
    parts = [f"## {d['title']}\n\n{_read(d['path']).strip()}" for d in user_docs(group) if d["enabled"]]
    if not parts:
        return ""
    return ("# Tài liệu bổ sung do người dùng cung cấp\n\nÁp dụng các tài liệu dưới đây cùng với hướng dẫn ở trên; "
            "nếu mâu thuẫn, ưu tiên tài liệu bổ sung.\n\n" + "\n\n".join(parts))
