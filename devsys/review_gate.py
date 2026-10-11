"""Điểm A21 đọc từ thẩm định; thiếu/sai là None kèm lý do, không điền 0."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / 'docs/THAM_DINH_KE_HOACH_KIEM_SOAT_2026-10-10.md'
THRESHOLD = 8.5
NUMBER = r'([0-9]+(?:[,.][0-9]+)?)\s*/\s*10\b'


def _value(match):
    if not match:
        return None
    value = float(match[1].replace(',', '.'))
    return value if 0 <= value <= 10 else None


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
        build = _value(re.search(r'(?:build|K0a)\s+' + NUMBER, plain, re.I))
        errors = []
        if plan is None:
            errors.append('không đọc được điểm kế hoạch (thiếu hoặc ngoài 0–10)')
        if build is None:
            errors.append('không đọc được điểm build (chưa ghi hoặc ngoài 0–10)')
        holes_text = re.search(r'^Lỗ hổng(?: còn lại(?: \([^\n]*?\))?)?\s*:\s*(.*?)(?=^Kết luận|^Đã sửa ngay|^# |\Z)',
                               cleaned, re.M | re.S | re.I)
        holes = len({a or b for a, b in re.findall(r'^\s*([0-9]+)\.\s+|\(([0-9]+)\)\s*(?:CAO|TRUNG|THẤP)\b', holes_text[1], re.M)}) if holes_text else None
        if holes == 0 and not re.search(r'không (?:có|còn)', holes_text[1], re.I):
            holes = None
        if holes is None:
            errors.append('không đọc được danh sách Lỗ hổng còn lại')
        if plan is None or build is None:
            status = 'CHƯA ĐẠT' if any(v is not None and v < THRESHOLD for v in (plan, build)) else 'KHÔNG ĐỦ SỐ ĐO'
        else:
            status = 'ĐẠT' if min(plan, build) >= THRESHOLD else 'CHƯA ĐẠT'
        rows.append({'round': number, 'title': title, 'plan': plan, 'build': build, 'holes': holes, 'status': status, 'errors': errors})
    return {'rows': rows, 'error': None if rows else 'không đọc được: không có lần thẩm định'}


def load(path=FILE):
    try:
        return parse(Path(path).read_text(encoding='utf-8'))
    except (OSError, UnicodeError) as error:
        return {'rows': [], 'error': f'không đọc được: {error}'}
