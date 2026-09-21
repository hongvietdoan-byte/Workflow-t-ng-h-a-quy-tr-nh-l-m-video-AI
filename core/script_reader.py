"""Read a script from many kinds of files (or text typed / pasted in the dashboard) into the paragraphs that
`script_parser.split_scenes` understands.

Formats: .docx (paragraphs AND tables, in document order), .xlsx (every visible sheet), .csv / .tsv, .txt / .md, and pasted text
(including a block copied from Excel / Google Sheets, which arrives as tab-separated rows).

Tables (a script written as a sheet): the header row is recognised by column names in Vietnamese or English (Cảnh / Scene, Mô tả /
Description, Lời thoại / Dialogue, Nhân vật / Character, Bối cảnh / Location, Thời gian / Time, Góc máy / Camera, Thời lượng /
Duration...). Every scene becomes
    CẢNH n - <time>, <location>
    <description>
    NHÂN VẬT: <dialogue>
    (Góc máy: ...)   (other columns are kept as notes)
Rows with an empty scene cell continue the scene above (a scene with several dialogue rows).
"""
import csv
import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MAX_BYTES = 20 * 1024 * 1024
SUPPORTED = ("docx", "xlsx", "csv", "tsv", "txt", "md")


class ScriptReadError(ValueError):
    """Shown to the person as it is."""


@dataclass
class ScriptText:
    paragraphs: List[str]
    info: List[str] = field(default_factory=list)          # what was recognised, for the person to check


def fold(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").replace("đ", "d").replace("Đ", "D"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^\w#]+", " ", text.lower())).strip()


# column role -> header words (compared without accents, as whole words). Order = priority when a header fits several.
ROLES = [
    ("duration", ["thoi luong", "duration", "do dai", "length", "giay", "sec", "seconds"]),
    ("time", ["thoi gian", "time", "gio", "buoi", "ngay dem"]),
    ("location", ["boi canh", "dia diem", "location", "setting", "noi dien ra", "place", "khong gian"]),
    ("speaker", ["nhan vat", "character", "speaker", "nguoi noi", "ai noi", "vai", "who", "ten nhan vat"]),
    ("dialogue", ["loi thoai", "thoai", "dialogue", "dialog", "voice", "voiceover", "vo", "loi noi", "speech", "loi dan", "narration"]),
    ("description", ["mo ta", "noi dung", "hanh dong", "description", "action", "visual", "hinh anh", "dien bien", "content",
                     "kich ban", "cot truyen", "tom tat", "scene description"]),
    ("camera", ["goc may", "camera", "shot type", "shot", "khung hinh", "ong kinh", "cu ly"]),
    ("scene", ["canh", "scene", "stt", "no", "#", "so canh", "shot no", "shot number", "so thu tu", "phan canh", "sc", "id"]),
]
NOTE_LABEL = {"camera": "Góc máy", "duration": "Thời lượng"}


def _role_of(header: str, taken: set) -> Optional[str]:
    words = f" {fold(header)} "
    if not words.strip():
        return None
    for role, keys in ROLES:
        if role in taken:
            continue
        if any(f" {k} " in words for k in keys):
            return role
    return None


def _find_header(rows: List[List[str]]):
    for i, row in enumerate(rows[:6]):
        taken: set = set()
        mapping: Dict[int, str] = {}
        for j, cell in enumerate(row):
            role = _role_of(cell, taken)
            if role:
                mapping[j] = role
                taken.add(role)
        meaningful = taken & {"description", "dialogue", "speaker", "scene", "location"}
        if len(taken) >= 2 and meaningful:
            return i, mapping
    return None, {}


def _lines(cell: str) -> List[str]:
    return [x.strip() for x in re.split(r"[\r\n]+", cell or "") if x.strip()]


def table_to_paragraphs(rows: List[List[str]], start: int = 1, label: str = "") -> tuple:
    """(paragraphs, scenes_made, info_lines, recognised)"""
    rows = [[(c or "").strip() for c in r] for r in rows]
    rows = [r for r in rows if any(r)]
    if not rows:
        return [], 0, [], False
    head_i, mapping = _find_header(rows)
    info: List[str] = []
    scenes: List[dict] = []
    if head_i is None:
        for r in rows:
            scenes.append({"label": "", "time": "", "location": "", "desc": [" | ".join(c for c in r if c)], "talk": [], "notes": []})
        info.append(f"{label}bảng không có dòng tiêu đề cột nhận ra được: mỗi dòng thành một cảnh")
        recognised = False
    else:
        head = rows[head_i]
        info.append(f"{label}nhận ra cột: " + ", ".join(f"{head[j].strip() or '(trống)'} → {role}" for j, role in mapping.items()))
        extra = [j for j in range(len(head)) if j not in mapping and head[j].strip()]
        if extra:
            info.append(f"{label}cột khác giữ làm ghi chú: " + ", ".join(head[j] for j in extra))
        cur: Optional[dict] = None
        for r in rows[head_i + 1:]:
            get = lambda role: next((r[j] for j, ro in mapping.items() if ro == role and j < len(r)), "")  # noqa: E731
            scene_label, desc, talk, who = get("scene"), get("description"), get("dialogue"), get("speaker")
            has_scene_col = "scene" in mapping.values()
            new = cur is None or (has_scene_col and scene_label and scene_label != cur["label"]) or (not has_scene_col and desc)
            if new:
                cur = {"label": scene_label, "time": get("time"), "location": get("location"), "desc": [], "talk": [], "notes": []}
                scenes.append(cur)
            if desc:
                cur["desc"].extend(_lines(desc))
            if talk:
                for line in _lines(talk):
                    if re.match(r"^\s*[^\W\d_][^:\n]{0,28}:\s*\S", line):
                        cur["talk"].append(line)
                    else:
                        cur["talk"].append(f"{(who or 'LỜI THOẠI').strip().upper()}: {line}")
            for j in extra:
                if j < len(r) and r[j]:
                    cur["notes"].append(f"{head[j].strip()}: {r[j]}")
            for role, name in NOTE_LABEL.items():
                if get(role):
                    cur["notes"].append(f"{name}: {get(role)}")
            for role in ("time", "location"):
                if get(role) and not cur[role]:
                    cur[role] = get(role)
        recognised = True
    out: List[str] = []
    n = start
    for s in scenes:
        heading = f"CẢNH {n}" + (f" - {', '.join(x for x in (s['time'], s['location']) if x)}" if s["time"] or s["location"] else "")
        out.append(heading)
        out.extend(s["desc"])
        out.extend(s["talk"])
        out.extend(f"({note})" for note in s["notes"])
        n += 1
    info.append(f"{label}{len(scenes)} cảnh từ bảng")
    return out, len(scenes), info, recognised


# ---- readers ----------------------------------------------------------------------------------------------
def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16"):
        try:
            text = data.decode(enc)
            if enc == "utf-16" and not data[:2] in (b"\xff\xfe", b"\xfe\xff"):
                continue
            return text
        except UnicodeError:
            continue
    for enc in ("cp1258", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeError:
            continue
    return data.decode("latin-1")


def _paragraphs_of_text(text: str) -> List[str]:
    return [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]


def _delimited(text: str, delimiter: Optional[str] = None) -> List[List[str]]:
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(text[:4000], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    return [row for row in csv.reader(io.StringIO(text), delimiter=delimiter)]


def from_text(text: str) -> ScriptText:
    """Typed or pasted text. A block copied from Excel / Google Sheets (tab-separated) is read as a table."""
    text = (text or "").strip()
    if not text:
        raise ScriptReadError("Chưa có nội dung kịch bản")
    lines = _paragraphs_of_text(text)
    if len(lines) >= 2 and sum(1 for l in lines if "\t" in l) >= max(2, len(lines) // 2):
        paragraphs, n, info, ok = table_to_paragraphs(_delimited(text, "\t"))
        if ok or n:
            return ScriptText(paragraphs, ["Đọc như bảng dán từ Excel/Google Sheets"] + info)
    return ScriptText(lines, [f"Văn bản: {len(lines)} dòng"])


def _docx(data: bytes) -> ScriptText:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            root = ET.fromstring(z.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ET.ParseError):
        raise ScriptReadError("File .docx không đọc được (có thể bị hỏng hoặc không phải Word). Thử mở trong Word rồi Lưu lại.") from None
    body = root.find(f"{_W}body")
    if body is None:
        raise ScriptReadError("File .docx trống")
    paragraphs: List[str] = []
    info: List[str] = []
    counter = 1
    tables = 0

    def text_of(p) -> str:
        return "".join(t.text or "" for t in p.iter(f"{_W}t")).strip()

    for child in body:
        if child.tag == f"{_W}p":
            t = text_of(child)
            if t:
                paragraphs.append(t)
        elif child.tag == f"{_W}tbl":
            tables += 1
            rows = []
            for tr in child.findall(f"{_W}tr"):
                rows.append(["\n".join(x for x in (text_of(p) for p in tc.iter(f"{_W}p")) if x) for tc in tr.findall(f"{_W}tc")])
            got, n, tinfo, ok = table_to_paragraphs(rows, counter, f"Bảng {tables}: ")
            paragraphs.extend(got)
            counter += n
            info.extend(tinfo)
    if not paragraphs:
        raise ScriptReadError("File .docx không có chữ nào")
    return ScriptText(paragraphs, [f"Word: {len(paragraphs)} đoạn" + (f", {tables} bảng" if tables else "")] + info)


def _xlsx(data: bytes) -> ScriptText:
    try:
        import openpyxl
    except ImportError:
        raise ScriptReadError("Chưa cài thư viện đọc Excel (openpyxl). Chạy: py -m pip install openpyxl") from None
    try:
        book = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception:  # noqa: BLE001 - openpyxl raises many kinds
        raise ScriptReadError("File .xlsx không đọc được (bị hỏng, có mật khẩu hoặc không phải Excel).") from None
    paragraphs: List[str] = []
    info: List[str] = []
    counter, used, skipped = 1, 0, []
    sheets = [ws for ws in book.worksheets if ws.sheet_state == "visible"]
    for ws in sheets:
        rows = []
        for row in ws.iter_rows(values_only=True):
            cells = ["" if v is None else (str(int(v)) if isinstance(v, float) and v == int(v) else str(v)) for v in row]
            while cells and not cells[-1].strip():
                cells.pop()
            rows.append(cells)
        got, n, tinfo, ok = table_to_paragraphs(rows, counter, f"Sheet “{ws.title}”: ")
        if not n or (len(sheets) > 1 and not ok):
            if any(any(r) for r in rows):
                skipped.append(ws.title)
            continue
        paragraphs.extend(got)
        info.extend(tinfo)
        counter += n
        used += 1
    if not paragraphs:
        raise ScriptReadError("Không thấy bảng kịch bản trong file Excel: cần dòng tiêu đề cột như Cảnh, Mô tả, Lời thoại…")
    if skipped:
        info.append("Bỏ qua sheet không nhận ra là kịch bản: " + ", ".join(skipped))
    return ScriptText(paragraphs, [f"Excel: {used} sheet, {counter - 1} cảnh"] + info)


def read_script(filename: str, data: bytes) -> ScriptText:
    """Read an uploaded file (by its extension)."""
    name = filename or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if len(data) > MAX_BYTES:
        raise ScriptReadError(f"File lớn hơn {MAX_BYTES // 1024 // 1024} MB")
    if not data:
        raise ScriptReadError("File rỗng")
    if ext == "docx":
        return _docx(data)
    if ext == "xlsx":
        return _xlsx(data)
    if ext in ("csv", "tsv"):
        text = _decode(data)
        rows = _delimited(text, "\t" if ext == "tsv" else None)
        paragraphs, n, info, ok = table_to_paragraphs(rows)
        if not paragraphs:
            raise ScriptReadError("File không có nội dung")
        return ScriptText(paragraphs, [f"{ext.upper()}: {len(rows)} dòng"] + info)
    if ext in ("txt", "md"):
        return from_text(_decode(data))
    if ext == "pdf":
        raise ScriptReadError("Chưa đọc được PDF. Mở PDF, chọn và copy chữ, rồi dán vào tab “Gõ / dán văn bản”.")
    if ext in ("doc", "xls", "rtf", "odt"):
        raise ScriptReadError(f"Định dạng .{ext} cũ chưa hỗ trợ: hãy Lưu thành .docx / .xlsx / .csv rồi tải lại.")
    raise ScriptReadError(f"Chưa hỗ trợ file .{ext or '?'}. Dùng: " + ", ".join("." + s for s in SUPPORTED) + ", hoặc dán văn bản.")
