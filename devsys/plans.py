"""Sổ mọi kế hoạch: chỉ đọc file/git, số tính từ nguồn; lỗi đọc không biến thành 0%."""
import json
from pathlib import Path
import re
import subprocess
from . import plan_progress, stages

ROOT = Path(__file__).resolve().parents[1]
KINDS = {'viec_s', 'dot_bang', 'codex', 'ghi_chu', 'phuong_phap'}
STATES = {'dang_chay', 'cho', 'xong', 'chua_lam'}


def parse_control(text):
    section = re.search(r'^## 8\..*?\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    found, errors = {}, []
    for line in section.group(1).splitlines() if section else []:
        match = re.match(r'^\|\s*\**(K\d+[ab]?)\**\b(.*)', line)
        if not match:
            continue
        key = match.group(1)
        if key not in stages.DOT or key in found:
            errors.append(f'đợt không hợp lệ hoặc trùng: {key}')
            continue
        # K0b có nhắc trạng thái cũ phía sau: chỉ lấy dấu đầu tiên ở ô tên đợt.
        first_cell = line.split('|')[1]
        state = re.search(r'✅|🟡', first_cell)
        found[key] = {'id': key, 'status': state.group() if state else 'chưa',
                      'commits': list(dict.fromkeys(re.findall(r'`([0-9a-f]{7,40})`', line)))}
    missing = [d for d in stages.DOT if d not in found]
    if missing:
        errors.append('thiếu đợt: ' + ', '.join(missing))
    section_a = re.search(r'^## A\..*?\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    decisions = [{'id': f'A{m[0]}', 'text': m[1].strip()} for m in
                 re.findall(r'^\|\s*A(\d+)\s*\|\s*(.*?)\s*\|\s*$', section_a.group(1) if section_a else '', re.M)]
    if not section_a or not decisions:
        errors.append('không đọc được bảng chốt mục A')
    waves = [found[d] for d in stages.DOT if d in found]
    percent = None if errors else round(100 * sum({'✅': 1, '🟡': .5, 'chưa': 0}[d['status']] for d in waves) / len(stages.DOT), 1)
    latest = max(decisions, key=lambda d: int(d['id'][1:])) if decisions else None
    return {'waves': waves, 'percent': percent, 'decision_count': len(decisions), 'latest_decision': latest,
            'error': 'không đọc được: ' + '; '.join(errors) if errors else None}


def read_control(path):
    try:
        return parse_control(Path(path).read_text(encoding='utf-8'))
    except (OSError, UnicodeError) as error:
        return {'waves': [], 'percent': None, 'decision_count': None, 'latest_decision': None,
                'error': f'không đọc được: {error}'}


def read_source(record, root=ROOT):
    path = Path(record['file'])
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('file phải nằm trong repo')
    if record.get('nhanh'):
        proc = subprocess.run(['git', 'show', '--no-ext-diff', '--end-of-options', f"{record['nhanh']}:{path.as_posix()}"],
                              cwd=root, capture_output=True, encoding='utf-8', errors='replace', timeout=15)
        if proc.returncode:
            raise ValueError(proc.stderr.strip() or 'git show thất bại')
        return proc.stdout
    return (Path(root) / path).read_text(encoding='utf-8')


def progress_for(record, text):
    kind = record['kieu']
    if kind == 'viec_s':
        parsed = plan_progress.parse(text)
        if parsed['bad'] or not parsed['waves']:
            raise ValueError('không đọc được danh sách việc S: ' + '; '.join(parsed['bad']))
        return {'percent': plan_progress.summary(parsed)['total'], 'error': None}
    if kind == 'dot_bang':
        return parse_control(text)
    if kind == 'codex':
        wave = int(record['dot'])
        headings = list(re.finditer(r'^# ĐỢT (\d+)\b.*$', text, re.M))
        start = 0 if wave == 1 else next((h.end() for h in headings if int(h[1]) == wave), None)
        if start is None:
            raise ValueError(f'không thấy ĐỢT {wave}')
        end = next((h.start() for h in headings if h.start() > start), len(text))
        part = text[start:end]
        tasks = re.findall(r'^## Việc (\d+)\b', part, re.M)
        if not tasks:
            raise ValueError('không có mục Việc trong đợt')
        results = re.split(r'^## Kết quả Codex.*$', part, flags=re.M)[-1] if '## Kết quả Codex' in part else ''
        done = {m[0] for m in re.findall(r'^\|\s*(\d+)\s*\|(.+)$', results, re.M) if re.search(r'`[0-9a-f]{7,40}`', m[1])}
        done.update(m[0] for m in re.findall(r'^- Việc (\d+)\b(.+)$', results, re.M) if re.search(r'`[0-9a-f]{7,40}`', m[1]))
        return {'percent': round(100 * len(set(tasks) & done) / len(set(tasks)), 1), 'error': None}
    return {'percent': None, 'error': None}  # ghi chú/phương pháp không có mẫu số tiến độ


def inventory(root=ROOT):
    try:
        records = json.loads((Path(root) / 'devsys/plans.json').read_text(encoding='utf-8'))
        if not isinstance(records, list):
            raise ValueError('plans.json phải là danh sách')
        ids = set()
        for record in records:
            if not isinstance(record, dict) or any(not isinstance(record.get(k), str) or not record[k].strip()
                                                  for k in ('id', 'ten', 'file', 'kieu', 'trang_thai')) or 'ghi_chu' not in record:
                raise ValueError('mục kế hoạch thiếu trường hoặc sai kiểu')
            if record['id'] in ids:
                raise ValueError('mã kế hoạch trùng: ' + record['id'])
            ids.add(record['id'])
    except (OSError, UnicodeError, ValueError) as error:
        return {'items': [], 'error': f'không đọc được: {error}'}
    items = []
    for record in records:
        try:
            if record.get('kieu') not in KINDS or record.get('trang_thai') not in STATES:
                raise ValueError('kieu/trang_thai không hợp lệ')
            result = progress_for(record, read_source(record, root))
        except (OSError, UnicodeError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
            result = {'percent': None, 'error': f'không đọc được: {error}'}
        items.append(dict(record, **result))
    return {'items': items, 'error': None}
