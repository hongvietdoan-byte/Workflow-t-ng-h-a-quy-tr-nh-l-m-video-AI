"""Điểm A21 đọc từ thẩm định; thiếu/sai là None kèm lý do, không điền 0.

Số lỗ hổng còn lại đọc được ba dạng có thật trong docs/THAM_DINH_KE_HOACH_KIEM_SOAT_2026-10-10.md:
  - tiêu đề "## Lỗ hổng (mức)" (lần 1) / "Lỗ hổng còn lại (…):" / "Lỗ hổng:" + danh sách "1." hoặc "(1) CAO";
  - dòng "Còn lại: CAO — …; TRUNG — …" (lần 2, 3, 7): mỗi cụm "MỨC —" là một lỗ hổng, trừ khi trong cụm có
    mục đánh số "(1)…(2)…" hoặc nhiều ý cách nhau bằng ";" (lần 2, 3 gộp nhiều lỗ hổng cùng mức vào một cụm).
Đoạn có "Đã sửa cùng ngày" thì vẫn giữ số theo bản thẩm định và ghi chú rõ phần đã sửa chưa được xác nhận.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / 'docs/THAM_DINH_KE_HOACH_KIEM_SOAT_2026-10-10.md'
THRESHOLD = 8.5
NUMBER = r'([0-9]+(?:[,.][0-9]+)?)\s*/\s*10\b'
SEVERITY = r'(?:CAO|TRUNG|THẤP)'
_END = r'(?=^Kết luận|^Đã sửa|^Câu hỏi|^Agent\b|^Điểm mạnh|^#{1,3} |\Z)'
HOLES_HEADING = re.compile(r'^(?:#{1,3}\s*)?Lỗ hổng(?: còn lại)?(?: \([^\n]*?\))?[ \t]*(?::|$)(.*?)' + _END, re.M | re.S | re.I)
HOLES_REST = re.compile(r'^Còn lại\s*:(.*?)' + _END, re.M | re.S | re.I)
SAME_DAY_FIX = re.compile(r'Đã sửa cùng ngày', re.I)


def _value(match):
    if not match:
        return None
    value = float(match[1].replace(',', '.'))
    return value if 0 <= value <= 10 else None


def _count_rest(body):
    """'Còn lại: CAO — a; TRUNG — b; …' → số lỗ hổng (mỗi cụm mức ≥ 1)."""
    parts = re.split(r'\b' + SEVERITY + r'\s*—', body)[1:]
    total = 0
    for part in parts:
        numbered = set(re.findall(r'\(([0-9]+)\)', part))
        items = [s for s in part.strip().rstrip('.;').split(';') if s.strip()]
        total += len(numbered) if len(numbered) > 1 else max(1, len(items))
    return total


def _holes(cleaned):
    """(số | None, lý do khi None)."""
    found = HOLES_HEADING.search(cleaned)
    if found:
        listed = found[1]
        holes = len({a or b for a, b in re.findall(r'^\s*([0-9]+)\.\s+|\(([0-9]+)\)\s*' + SEVERITY + r'\b', listed, re.M)})
        if holes or re.search(r'không (?:có|còn)', listed, re.I):
            return holes, None
        return None, 'mục Lỗ hổng có nhưng không có mục đánh số ("1." hoặc "(1) MỨC") hay câu "không còn"'
    found = HOLES_REST.search(cleaned)
    if found:
        holes = _count_rest(found[1])
        if holes or re.search(r'không (?:có|còn)', found[1], re.I):
            return holes, None
        return None, 'dòng "Còn lại:" không có cụm "CAO — / TRUNG — / THẤP —"'
    return None, 'không thấy mục Lỗ hổng ("Lỗ hổng còn lại:", "## Lỗ hổng (mức)" hoặc "Còn lại:")'


def parse(text):
    markers = list(re.finditer(r'^# Lần (\d+)\b[^\n]*', text, re.M))
    chunks = []
    if (not markers or int(markers[0][1]) > 1) and text[:markers[0].start() if markers else len(text)].strip():
        chunks.append((1, text.splitlines()[0], text[:markers[0].start() if markers else len(text)]))
    for i, m in enumerate(markers):
        chunks.append((int(m[1]), m[0], text[m.end():markers[i + 1].start() if i + 1 < len(markers) else len(text)]))
    rows = []
    for number, title, body in chunks:
        plain = title.replace('*', '').replace('`', '')
        plan = _value(re.search(r'kế hoạch\s+' + NUMBER, plain, re.I))
        if plan is None and number == 2:
            plan = _value(re.search(NUMBER, plain))
        cleaned = body.replace('*', '').replace('`', '')
        if plan is None and number == 1:
            plan = _value(re.search(r'^Tổng\b[^\n]*?≈\s*' + NUMBER, cleaned, re.M | re.I))
        build_match = re.search(r'(build|K0a)\s+' + NUMBER, plain, re.I)
        build = _value(re.search(NUMBER, build_match[0])) if build_match else None
        build_scope = None if build is None else ('K0a' if build_match[1].upper() == 'K0A' else 'build')
        errors = []
        if plan is None:
            errors.append('không đọc được điểm kế hoạch (thiếu hoặc ngoài 0–10)')
        if build is None:
            errors.append('không đọc được điểm build (chưa ghi hoặc ngoài 0–10)')
        holes, reason = _holes(cleaned)
        holes_note = None
        if holes is None:
            errors.append(reason)
        else:
            holes_note = 'theo bản thẩm định'
            if SAME_DAY_FIX.search(cleaned):
                holes_note += '; phần đã sửa cùng ngày chưa xác nhận'
            else:
                holes_note += '; phần đã sửa cần lần thẩm định tiếp xác nhận'
        if plan is None or build is None:
            status = 'CHƯA ĐẠT' if any(v is not None and v < THRESHOLD for v in (plan, build)) else 'KHÔNG ĐỦ SỐ ĐO'
        else:
            status = 'ĐẠT' if min(plan, build) >= THRESHOLD else 'CHƯA ĐẠT'
        rows.append({'round': number, 'title': title, 'plan': plan, 'build': build, 'build_scope': build_scope,
                     'holes': holes, 'holes_note': holes_note, 'holes_error': reason if holes is None else None,
                     'status': status, 'errors': errors})
    return {'rows': rows, 'error': None if rows else 'không đọc được: không có lần thẩm định'}


def load(path=FILE):
    try:
        return parse(Path(path).read_text(encoding='utf-8'))
    except (OSError, UnicodeError) as error:
        return {'rows': [], 'error': f'không đọc được: {error}'}


# ---- chữ hiển thị (thuần, để test; app.py chỉ in) ----------------------------------------------------------------------
def score_text(value):
    """8.5 → '8,5/10' (dấu phẩy tiếng Việt); None → 'không đọc được'."""
    return 'không đọc được' if value is None else f'{value:g}'.replace('.', ',') + '/10'


def holes_text(row):
    if row.get('holes') is None:
        return f"Lỗ hổng còn lại: không đọc được: {row.get('holes_error') or 'không rõ lý do'}"
    return f"Lỗ hổng còn lại: {row['holes']}" + (f" ({row['holes_note']})" if row.get('holes_note') else '')


def _rounds(numbers):
    """[1, 2, 4] → '1–2, 4'."""
    spans, out = [], []
    for n in sorted(numbers):
        if spans and n == spans[-1][1] + 1:
            spans[-1][1] = n
        else:
            spans.append([n, n])
    for a, b in spans:
        out.append(str(a) if a == b else f'{a}–{b}')
    return ', '.join(out)


def build_note(rows):
    """Chú thích tính từ dữ liệu: lần nào thiếu điểm build, lần nào điểm build là phạm vi K0a. '' khi không có gì để nói."""
    missing = [r['round'] for r in rows if r.get('build') is None]
    k0a = [r['round'] for r in rows if r.get('build_scope') == 'K0a']
    parts = []
    if missing:
        parts.append(f'Lần {_rounds(missing)} chưa ghi điểm build; không điền 0.')
    if k0a:
        parts.append(f'Build lần {_rounds(k0a)} là phạm vi K0a theo nguồn, chưa đại diện toàn pipeline.')
    return ' '.join(parts)
