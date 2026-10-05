"""Knowledge base of the Claude steps (Director, QC, motion prompt): what ships with the project and what the
user adds.

Built-in documents live in the repo (`knowledge/`, `prompts/`, `eval/golden.json`) and are versioned with the code.
Documents the user uploads live OUTSIDE git in `data/knowledge_user/<step>/` (override: KNOWLEDGE_USER_DIR) and are
appended to that step's prompt while they are switched on, so the step improves without touching code.

Every enabled document is sent to Claude on every run of the step, so size costs tokens: per-document and per-step
limits keep prompts (and the bill) bounded.
"""
import hashlib
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
                  ("knowledge/ff_gameplay_visual.md", "Free Fire gameplay thật trông thế nào",
                   "tư liệu tham khảo: máy gameplay, bối cảnh, HUD, chữ cấm khi look in-game (PDF Visual Replication Plan v1.0)"),
                  ("knowledge/cinematography_basics.md", "Cơ bản điện ảnh", "cỡ cảnh, góc máy, ánh sáng, chuyển động"),
                  ("knowledge/genre_guides.md", "Hướng dẫn 7 thể loại", "công thức viết prompt ảnh theo thể loại"),
                  ("knowledge/research_notes.md", "Nguyên tắc từ nguồn nghiên cứu", "16 nguyên tắc, 8 chiều điện ảnh"),
                  ("knowledge/film_director_method.md", "Phương pháp đạo diễn", "ý định cảm xúc, 3 trục quan hệ, dàn dựng, nhịp phủ cảnh"),
                  ("knowledge/ff_character_skills_visual.md", "Dịch skill → hình ảnh (67 nhân vật FF)",
                   "chỉ gửi mục của nhân vật có trong dự án (v2)"),
                  ("knowledge/character_lock.md", "Character Lock", "nét bắt buộc giữ / được đổi / cấm lệch (skill consistency designer)"),
                  ("knowledge/dialogue_craft.md", "Viết thoại", "6 lỗi thoại (skill narration-writer)"),
                  ("knowledge/genre/SHORT_FORM.md", "Thể loại theo dự án", "chỉ gửi file đúng thể loại của dự án (skill film-director)"),
                  ("eval/golden.json", "Ví dụ mẫu (few-shot)", "3 cặp đầu vào → kết quả chuẩn")]),
    "qc": ("QC — chấm điểm ảnh (Bước 2)",
           "Chấm ảnh theo 5 tiêu chí so với Character Bible và thông số cảnh.",
           [("prompts/02_qc_agent.md", "Prompt QC", "tiêu chí và định dạng chấm"),
            ("knowledge/ai_image_failure_modes.md", "Lỗi thường gặp của ảnh AI", "tay, mặt, chữ, chi tiết thừa…"),
            ("knowledge/character_lock.md", "Character Lock + thứ tự rà", "7 bước rà nhất quán nhân vật")]),
    "motion": ("Motion prompt — chuyển động video (Bước 3)",
               "Viết câu lệnh chuyển động cho từng cảnh có ảnh đã duyệt.",
               [("prompts/03_video_motion.md", "Prompt motion", "quy tắc và định dạng JSON"),
                ("knowledge/video_motion_vocab.md", "Từ vựng camera / chuyển động", ""),
                ("knowledge/research_notes.md", "Nguyên tắc từ nguồn nghiên cứu", "dùng chung với Director"),
                ("knowledge/t2v_prompt_structure.md", "Cấu trúc prompt video (World Bible + 7 đoạn)", "nguồn sáng, chất liệu, nhất quán giữa cảnh"),
                ("knowledge/motion_complex_shots.md", "Cảnh hành động phức tạp", "khóa không gian, chia nhịp, whip pan đúng chỗ"),
                ("knowledge/seedance_prompting.md", "Cách viết prompt Seedance", "chỉ gắn khi model video là Seedance"),
                ("knowledge/seedance_director_workflow.md", "Quy trình Seedance Director", "chỉ gắn khi model video là Seedance"),
                ("knowledge/motion_prompt_lint.md", "Checklist rà motion prompt", "Seedance Final QC + 4 kiểm tra mơ hồ của slide ClipAI"),
                ("knowledge/ff_character_skills_visual.md", "Dịch skill → hình ảnh (67 nhân vật FF)",
                 "chỉ gửi mục của nhân vật có trong dự án (v2)")]),
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
    path = _manifest(group)
    tmp = path + ".tmp"                      # S14.4 C1b: atomic — a failure never leaves a half-written manifest
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


# S14.4 C1b (04/10): with the `film_crew` flag the Director reads the role books instead of 3 scattered documents
# (core/prompts.py build_director_bundle / dp_common) — the knowledge page shows the same thing.
CREW_REPLACES = ("knowledge/cinematography_basics.md", "knowledge/film_director_method.md", "knowledge/dialogue_craft.md")
CREW_DOCS = {"director": [
    ("knowledge/roles/director.md", "Bộ nguyên tắc vai Đạo diễn", "cờ film_crew: thay 3 tài liệu cũ", False),
    ("knowledge/roles/dp.md", "Bộ nguyên tắc vai Quay phim (DP)", "cờ film_crew: gửi khi dự án chia shot (Tầng B)", False),
    ("knowledge/editor/editing.md", "Bộ nguyên tắc vai Editor (dựng)",
     "cờ film_crew: gửi ở khâu Editor duyệt bản thô (Bước 5), không gửi kèm Director", True)]}


def _film_crew() -> bool:
    from . import features
    try:
        return features.on("film_crew")
    except KeyError:                                     # an old feature table without the flag: as before
        return False


# S14.20 (Bộ não prompt Đợt 2, cờ `murch_knowledge`, TẮT mặc định): the Murch priority scale for the Director AND the motion writer,
# the I2V discipline (+ the motion prompt's addendum) for motion, the sound method for the Director. Flag off → nothing sent, nothing listed.
MURCH_DOCS = {
    "director": [("knowledge/craft/uu_tien_cam_xuc.md", "Thứ tự ưu tiên cảm xúc (trục Murch)",
                  "cờ murch_knowledge: thang chung khi phải đánh đổi (tách từ editing.md E1)"),
                 ("knowledge/sound_design_method.md", "Phương pháp thiết kế âm thanh",
                  "cờ murch_knowledge: dẫn → đập → đuôi, ý đồ → chất âm, khoảng lặng, chống lạm dụng")],
    "motion": [("prompts/03_video_motion_murch.md", "Bổ sung quy tắc motion",
                "cờ murch_knowledge: giữ trước, ưu tiên cảm xúc, check_flags gọi tên rủi ro"),
               ("knowledge/craft/uu_tien_cam_xuc.md", "Thứ tự ưu tiên cảm xúc (trục Murch)",
                "cờ murch_knowledge: dùng chung với Director"),
               ("knowledge/i2v_motion_discipline.md", "Kỷ luật chuyển động I2V",
                "cờ murch_knowledge: 6 rủi ro + cách chữa, giữ trước, hỏng thì giảm chuyển động (P0→P5)")],
}


def _murch_on() -> bool:
    from . import features
    try:
        return features.on("murch_knowledge")
    except KeyError:
        return False


def murch_blocks(group: str) -> List[str]:
    """The texts of MURCH_DOCS[group] when the flag is on, else []. A listed file that cannot be read is said aloud (CHUAN luật 1)."""
    if not _murch_on():
        return []
    out = []
    for rel, title, _ in MURCH_DOCS.get(group, []):
        text = _read(os.path.join(ROOT, *rel.split("/"))).strip()
        if not text:
            raise FileNotFoundError(f"Cờ murch_knowledge bật nhưng không đọc được '{rel}' ({title}) — tắt cờ hoặc khôi phục file.")
        out.append(text)
    return out


def builtin_docs(group: str) -> List[Dict]:
    out = []
    crew = _film_crew()
    for rel, title, note in GROUPS[group][2]:
        path = os.path.join(ROOT, *rel.split("/"))
        text = _read(path)
        item = {"source": "builtin", "title": title, "note": note, "file": rel, "path": os.path.abspath(path),
                "chars": len(text), "enabled": True, "exists": bool(text), "crew_replaced": crew and rel in CREW_REPLACES}
        if item["crew_replaced"]:
            item["note"] = "cờ film_crew: KHÔNG gửi — bộ nguyên tắc vai thay thế"
        out.append(item)
    for rel, title, note, elsewhere in (CREW_DOCS.get(group, []) if crew else []):
        path = os.path.join(ROOT, *rel.split("/"))
        text = _read(path)
        out.append({"source": "builtin", "title": title, "note": note, "file": rel, "path": os.path.abspath(path),
                    "chars": len(text), "enabled": True, "exists": bool(text), "crew_replaced": False, "elsewhere": elsewhere})
    for rel, title, note in (MURCH_DOCS.get(group, []) if _murch_on() else []):
        path = os.path.join(ROOT, *rel.split("/"))
        text = _read(path)
        out.append({"source": "builtin", "title": title, "note": note, "file": rel, "path": os.path.abspath(path),
                    "chars": len(text), "enabled": True, "exists": bool(text), "crew_replaced": False})
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
    raw = sum(d["chars"] for d in docs if d["enabled"])            # everything, as the documents are
    playbook = distilled_active(group)
    folded = folded_builtin(group)
    for d in docs:
        d["folded"] = d["source"] == "builtin" and d["file"] in folded
        d["replaced"] = bool(playbook) and (d["source"] == "user" or d["folded"])  # not sent: the playbook stands in
    sent = sum(d["chars"] for d in docs if d["enabled"] and not d["replaced"] and not d.get("crew_replaced")
               and not d.get("elsewhere")) + (playbook["chars"] if playbook else 0)
    user_sent = sum(d["chars"] for d in docs if d["enabled"] and d["source"] == "user" and not d["replaced"])
    return {"docs": docs, "chars": sent, "tokens": approx_tokens(sent), "user_chars": user_sent,
            "raw_chars": raw, "raw_tokens": approx_tokens(raw), "distilled": distilled_status(group),
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


def _checked_text(group: str, filename: str, data: bytes, docs: List[Dict], replacing=frozenset()) -> str:
    """The document's text after the size checks; documents in `replacing` (files about to be swapped out) do not count."""
    text = _extract(filename, data).strip()
    if not text:
        raise ValueError("Tài liệu rỗng")
    if len(text) > MAX_DOC_CHARS:
        raise ValueError(f"Tài liệu dài {len(text):,} ký tự; tối đa {MAX_DOC_CHARS:,} (≈ {approx_tokens(MAX_DOC_CHARS):,} token). "
                         "Hãy rút gọn hoặc tách nhỏ.")
    used = sum(d["chars"] for d in docs if d.get("enabled", True) and d["file"] not in replacing)
    if used + len(text) > MAX_USER_CHARS:
        raise ValueError(f"Tổng tài liệu bổ sung của bước này sẽ vượt {MAX_USER_CHARS:,} ký tự "
                         f"(đang dùng {used:,}). Tắt hoặc xóa bớt tài liệu cũ trước.")
    return text


def add_doc(group: str, filename: str, data: bytes, title: Optional[str] = None, note: str = "") -> Dict:
    """Add an uploaded document to a step's knowledge base (enabled at once)."""
    docs = _load(group)
    text = _checked_text(group, filename, data, docs)
    return _write_new(group, filename, text, docs, title, note)


def replace_doc(group: str, old_title: str, filename: str, data: bytes, title: Optional[str] = None, note: str = "") -> Dict:
    """S14.4 C1b (04/10): swap the uploaded document(s) titled `old_title` for a new one. The new text is built and checked
    against the limits (not counting the documents it replaces) BEFORE anything is removed: a failure keeps the old ones."""
    docs = _load(group)
    old = {d["file"] for d in docs if d.get("title") == old_title}
    text = _checked_text(group, filename, data, docs, old)          # raises ValueError → nothing changed
    entry = _write_new(group, filename, text, docs, title, note, drop=old)   # ONE manifest write: add new + drop old together
    for f in old:
        try:
            os.remove(os.path.join(group_dir(group), f))
        except OSError:
            pass                                                     # the manifest no longer lists it: never sent again
    return entry


def _write_new(group: str, filename: str, text: str, docs: List[Dict], title: Optional[str], note: str,
               drop=frozenset()) -> Dict:
    """Write the new document's file, then the manifest once (with the entries in `drop` left out). A failed manifest write removes
    the new file again: the knowledge base stays exactly as it was."""
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
    try:
        _save(group, [d for d in docs if d["file"] not in drop] + [entry])
    except Exception:
        try:
            os.remove(os.path.join(folder, file))
        except OSError:
            pass
        raise
    docs.append(entry)
    return entry


def set_enabled(group: str, file: str, enabled: bool) -> None:
    docs = _load(group)
    for d in docs:
        if d["file"] == file:
            d["enabled"] = bool(enabled)
            _save(group, docs)
            return
    raise KeyError(f"Không tìm thấy tài liệu '{file}' trong tài liệu bổ sung của bước này — tải lại trang (có thể vừa bị xóa).")


def remove_doc(group: str, file: str) -> None:
    docs = _load(group)
    if not any(d["file"] == file for d in docs):
        raise KeyError(f"Không tìm thấy tài liệu '{file}' trong tài liệu bổ sung của bước này — tải lại trang (có thể vừa bị xóa).")
    _save(group, [d for d in docs if d["file"] != file])
    try:
        os.remove(os.path.join(group_dir(group), file))
    except OSError:
        pass


def user_text(group: str) -> str:
    """What is appended to the step's prompt: the distilled playbook when one is active, else the enabled uploaded
    documents as they are ('' when there is nothing)."""
    active = distilled_active(group)
    if active:
        return ("# Cẩm nang kiến thức đã chắt lọc (từ tài liệu do người dùng cung cấp)\n\nÁp dụng cẩm nang dưới đây cùng "
                "với hướng dẫn ở trên; nếu mâu thuẫn, ưu tiên cẩm nang.\n\n" + active["text"])
    parts = [f"## {d['title']}\n\n{_read(d['path']).strip()}" for d in user_docs(group) if d["enabled"]]
    if not parts:
        return ""
    return ("# Tài liệu bổ sung do người dùng cung cấp\n\nÁp dụng các tài liệu dưới đây cùng với hướng dẫn ở trên; "
            "nếu mâu thuẫn, ưu tiên tài liệu bổ sung.\n\n" + "\n\n".join(parts))


# ---- distillation: read everything once, keep a short structured playbook ---------------------------------
MAX_DISTILLED_CHARS = 12_000
TARGET_CHARS = {"director": 6_000, "qc": 3_500, "motion": 4_500}
# the topic areas the playbook must have, in order (the same for every run so results are comparable)
DISTILL_SECTIONS = {
    "director": ["Phong cách & tông chung", "Nhân vật & đối tượng", "Bố cục, cỡ cảnh, góc máy", "Ánh sáng & màu sắc",
                 "Công thức viết prompt ảnh", "Nhịp & cảm xúc theo thể loại", "Điều cần tránh", "Ví dụ ngắn tiêu biểu",
                 "Mâu thuẫn / chưa rõ"],
    "qc": ["Tiêu chí & cách cho điểm", "Lỗi thường gặp cần bắt", "Nhất quán nhân vật", "Cách ghi lỗi (issues) rõ ràng",
           "Ví dụ ngắn tiêu biểu", "Mâu thuẫn / chưa rõ"],
    "motion": ["Camera & chuyển động", "Nhịp & thời lượng", "Hành động & cảm xúc", "Viết theo từng model (Kling, Seedance)",
               "Điều cần tránh", "Ví dụ ngắn tiêu biểu", "Mâu thuẫn / chưa rõ"],
}
# built-in documents that may be folded into the playbook (the prompt files and few-shot examples never are)
_FOLDABLE = {"director": {"knowledge/cinematography_basics.md", "knowledge/genre_guides.md", "knowledge/research_notes.md",
                          "knowledge/film_director_method.md", "knowledge/ff_character_skills_visual.md",
                          "knowledge/dialogue_craft.md", "knowledge/character_lock.md"},
             "qc": {"knowledge/ai_image_failure_modes.md"},
             "motion": {"knowledge/video_motion_vocab.md", "knowledge/research_notes.md", "knowledge/seedance_prompting.md",
                        "knowledge/t2v_prompt_structure.md", "knowledge/motion_complex_shots.md",
                        "knowledge/seedance_director_workflow.md", "knowledge/ff_character_skills_visual.md"}}


def _distilled_path(group: str) -> str:
    return os.path.join(group_dir(group), "distilled.json")


def _load_distilled(group: str) -> Optional[Dict]:
    try:
        with open(_distilled_path(group), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def distill_inputs(group: str, include_builtin: bool) -> List[tuple]:
    """(title, text) of every document that would be folded into the playbook."""
    docs = []
    for d in user_docs(group):
        if d["enabled"]:
            docs.append((d["title"], _read(d["path"]).strip()))
    if include_builtin:
        for rel, title, _ in GROUPS[group][2]:
            if rel in _FOLDABLE[group]:
                docs.append((title, _read(os.path.join(ROOT, *rel.split("/"))).strip()))
    return [(t, x) for t, x in docs if x]


def fingerprint(inputs: List[tuple]) -> str:
    h = hashlib.sha1()
    for title, text in sorted(inputs):
        h.update(title.encode("utf-8") + b"\0" + text.encode("utf-8") + b"\0")
    return h.hexdigest()


def build_distill_bundle(group: str, include_builtin: bool = False) -> str:
    """The prompt for Claude: instructions + required sections + every source document."""
    inputs = distill_inputs(group, include_builtin)
    if not inputs:
        raise ValueError("Chưa có tài liệu nào để chắt lọc: hãy thêm tài liệu (hoặc chọn gồm cả tài liệu có sẵn).")
    sections = "\n".join(f"{i}. {name}" for i, name in enumerate(DISTILL_SECTIONS[group], 1))
    head = _read(os.path.join(ROOT, "prompts", "05_knowledge_distill.md"))
    docs = "\n\n".join(f"### Tài liệu: {title}\n\n{text}" for title, text in inputs)
    return (f"{head}\n\n---\n\n# Bước cần dạy: {GROUPS[group][0]}\n{GROUPS[group][1]}\n\n"
            f"# Mục bắt buộc (giữ nguyên tên và thứ tự, mỗi mục là một tiêu đề `## `)\n{sections}\n\n"
            f"# Độ dài mục tiêu\nKhoảng {TARGET_CHARS[group]:,} ký tự (tối đa {MAX_DISTILLED_CHARS:,}).\n\n---\n\n"
            f"# Tài liệu nguồn ({len(inputs)} tài liệu, {sum(len(t) for _, t in inputs):,} ký tự)\n\n{docs}")


def validate_distilled(group: str, text: str) -> str:
    text = re.sub(r"^```(?:markdown|md)?\s*|\s*```$", "", (text or "").strip()).strip()
    if not text:
        raise ValueError("Bản chắt lọc rỗng")
    if len(text) > MAX_DISTILLED_CHARS:
        raise ValueError(f"Bản chắt lọc dài {len(text):,} ký tự; tối đa {MAX_DISTILLED_CHARS:,}. Cần rút gọn thêm.")
    headings = re.findall(r"^## .+$", text, flags=re.M)
    if len(headings) < 3:
        raise ValueError("Bản chắt lọc cần chia thành các mục có tiêu đề `## ` (ít nhất 3 mục).")
    have = {_fold_heading(h[3:]) for h in headings}
    missing = [name for name in DISTILL_SECTIONS.get(group, []) if _fold_heading(name) not in have]
    if missing:        # Q2: a cut answer (the last sections missing) must not replace the source documents
        raise ValueError("Bản chắt lọc thiếu mục bắt buộc: " + ", ".join(missing) + " (có thể bị cắt giữa chừng).")
    return text


def _fold_heading(text: str) -> str:
    return re.sub(r"^[\d.\s]+", "", text.strip().lower()).strip(" :")


def store_distilled(group: str, text: str, include_builtin: bool = False, use: bool = True) -> Dict:
    text = validate_distilled(group, text)
    inputs = distill_inputs(group, include_builtin)
    record = {"text": text, "created_at": time.strftime("%Y-%m-%d %H:%M"), "include_builtin": bool(include_builtin),
              "use": bool(use), "fingerprint": fingerprint(inputs), "source_chars": sum(len(t) for _, t in inputs),
              "sources": [t for t, _ in inputs]}
    with open(_distilled_path(group), "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=1)
    return record


def set_use_distilled(group: str, use: bool) -> None:
    record = _load_distilled(group)
    if record is None:
        raise KeyError("chưa có bản chắt lọc")
    record["use"] = bool(use)
    with open(_distilled_path(group), "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=1)


def clear_distilled(group: str) -> None:
    try:
        os.remove(_distilled_path(group))
    except OSError:
        pass


def distilled_status(group: str) -> Dict:
    """exists / fresh (sources unchanged since it was made) / active (will really be used in prompts)."""
    record = _load_distilled(group)
    if record is None:
        return {"exists": False, "fresh": False, "active": False, "use": False, "chars": 0, "tokens": 0}
    fresh = fingerprint(distill_inputs(group, record["include_builtin"])) == record["fingerprint"]
    return {"exists": True, "fresh": fresh, "use": record["use"], "active": record["use"] and fresh,
            "chars": len(record["text"]), "tokens": approx_tokens(len(record["text"])), "text": record["text"],
            "created_at": record["created_at"], "include_builtin": record["include_builtin"],
            "source_chars": record["source_chars"], "sources": record["sources"]}


def distilled_active(group: str) -> Optional[Dict]:
    """The playbook to use instead of the raw documents, or None (raw documents are used: no playbook, switched
    off, or the sources changed since it was made and it has to be redone)."""
    status = distilled_status(group)
    return status if status["active"] else None


def folded_builtin(group: str) -> set:
    """Built-in documents already summarised in the active playbook (so prompts leave them out)."""
    status = distilled_active(group)
    return set(_FOLDABLE[group]) if status and status["include_builtin"] else set()


# ---- v2: send only the part that applies ------------------------------------------------------------------------------
GENRE_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge", "genre")


def genre_text(genre: Optional[str]) -> str:
    """The film-director reference of the project's genre (SHORT_FORM, COMMERCIAL, ...), or '' when unknown."""
    if not genre:
        return ""
    path = os.path.join(GENRE_DIR, f"{genre.strip().upper()}.md")
    return _read(path) if os.path.exists(path) else ""


def _norm_name(name: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFD", name or "")
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn").upper().replace(" ", "").replace("-", "").replace(".", "")


def ff_skills_for(names) -> str:
    """ff_character_skills_visual.md cut down to its general notes + the sections of the characters named (67 characters,
    ~34k characters in full, most of it about people not in the video)."""
    path = os.path.join(os.path.dirname(__file__), "..", "knowledge", "ff_character_skills_visual.md")
    text = _read(path)
    wanted = {_norm_name(n) for n in names if n}
    if not text or not wanted:
        return ""
    blocks, cur = [], []
    for line in text.splitlines():
        if line.startswith("## ") and cur:
            blocks.append(cur)
            cur = []
        cur.append(line)
    if cur:
        blocks.append(cur)
    head, keep = [], []
    for block in blocks:
        title = block[0][3:] if block[0].startswith("## ") else ""
        who = _norm_name(title.split("—")[0].split(" - ")[0].strip()) if title else ""
        if not title or title.startswith(("Chủ động", "⚠")):
            head.append(chr(10).join(block))
        elif any(w and (w == who or (len(w) > 2 and w in who)) for w in wanted):
            keep.append(chr(10).join(block))
    if not keep:
        return ""
    return (chr(10) * 2).join(head + keep)
