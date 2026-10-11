"""Trang Đang chạy: chỉ đọc Git/việc giao, không fetch hay đổi nhánh/worktree."""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def _git(root, *args):
    result = subprocess.run(['git', *args], cwd=root, capture_output=True, encoding='utf-8', errors='replace', timeout=15)
    if result.returncode:
        raise ValueError(result.stderr.strip() or f'git {args[0]} thất bại')
    return result.stdout


_HASH = re.compile(r'`([0-9a-f]{7,40})`')
# Dòng giữ chỗ/khung bảng trong mục kết quả — không tính là "đã có kết quả".
_PLACEHOLDER = re.compile(r'^[ \t]*(\(Codex ghi[^\n]*\)|-{3,}|\|[\s|:-]*\||\|\s*Việc\s*\|[^\n]*)[ \t]*$', re.M)


def _sections(text):
    markers = list(re.finditer(r'^# ĐỢT (\d+)\b[ \t]*(?:[—-][ \t]*)?(.*)$', text, re.M))
    starts = [(1, 0, '')] + [(int(m[1]), m.end(), m[2].strip()) for m in markers]
    for i, (wave, start, title) in enumerate(starts):
        end = markers[i].start() if i < len(markers) else len(text)
        yield wave, title, text[start:end]


def _branch(text):
    """Nhánh = chuỗi backtick đầu tiên không phải mã commit (không bắt buộc tiền tố codex/)."""
    for m in re.finditer(r'`([^`\s]+)`', text):
        if not re.fullmatch(r'[0-9a-f]{7,40}', m[1]):
            return m[1]
    return None


def _result_entry(cells):
    """Ô [nhánh, commit, ...] của một dòng kết quả; commit "—" → None nhưng vẫn là có kết quả."""
    branch_cell = cells[0] if cells else ''
    commit = _HASH.search(cells[1]) if len(cells) > 1 else None
    return {'branch': _branch(branch_cell), 'commit': commit[1] if commit else None}


def parse_codex(text):
    rows = []
    for wave, wave_title, part in _sections(text):
        if not part.strip():
            continue
        result = re.search(r'^## Kết quả Codex[^\n]*\n(.*)', part, re.M | re.S)
        body = result[1] if result else ''
        done = {}
        for m in re.finditer(r'^- Việc (\d+)\b([^\n]*)|^\|\s*(\d+)\s*\|([^\n]*)', body, re.M):
            cells = [c.strip() for c in (m[2].split('·')[1:] if m[1] else m[4].strip().strip('|').split('|'))]
            done.setdefault(int(m[1] or m[3]), _result_entry(cells))
        tasks = [(int(m[1]), m[2].strip()) for m in re.finditer(r'^## Việc (\d+)\s*[—-]\s*(.+)$', part, re.M)]
        seen = {task for task, _ in tasks}
        tasks += [(task, f'(kết quả nhắc việc {task} nhưng không có mục "## Việc {task}")') for task in sorted(done) if task not in seen]
        for task, title in tasks:
            entry = done.get(task, {})
            rows.append({'wave': wave, 'task': task, 'title': title, 'has_result': task in done,
                         'branch': entry.get('branch'), 'commit': entry.get('commit')})
        if not tasks:
            # Đợt không chia "## Việc N": vẫn hiện một dòng cho cả đợt, không bỏ im lặng.
            filled = bool(_PLACEHOLDER.sub('', body).strip(' \n-'))
            commit = _HASH.search(body) if filled else None
            rows.append({'wave': wave, 'task': None,
                         'title': f'{wave_title or f"Đợt {wave}"} (không tách được việc — đợt không có mục "## Việc N")',
                         'has_result': filled, 'branch': _branch(body) if filled else None,
                         'commit': commit[1] if commit else None})
    return rows


def _worktrees(text):
    rows = []
    for block in text.strip().split('\n\n'):
        row = {}
        for line in block.splitlines():
            key, _, value = line.partition(' ')
            row[key] = value if value else True
        if 'worktree' in row:
            rows.append(row)
    return rows


def git_activity(root=ROOT, codex_text=''):
    data = {'branches': [], 'worktrees': [], 'errors': [], 'branch_results': []}
    try:
        refs = _git(root, 'branch', '-r', '--no-merged', 'origin/main', '--format=%(refname:short)').splitlines()
        data['worktrees'] = _worktrees(_git(root, 'worktree', 'list', '--porcelain'))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        data['errors'].append(f'không đọc được Git: {error}')
        return data
    git_errors = (OSError, ValueError, subprocess.SubprocessError)
    for ref in refs:
        short = ref.split('/', 1)[-1]
        owner = 'Codex' if short.startswith('codex/') else ('Claude' if short.startswith(('claude/', 'worktree-agent-')) else 'người')
        # Mỗi cột đọc riêng: một lệnh Git lỗi (clone shallow, nhánh không tổ tiên chung) chỉ để trống cột đó + ghi lý do,
        # không làm mất cả dòng nhánh.
        problems = []
        commit = date = None
        message = ''
        try:
            commit, date, message = _git(root, 'log', '-1', '--format=%H%x00%cI%x00%B', ref, '--').strip().split('\x00', 2)
        except git_errors as error:
            problems.append(f'không đọc được commit cuối: {error}')
        ahead = stat = None
        try:
            ahead = int(_git(root, 'rev-list', '--count', f'origin/main..{ref}', '--').strip())
        except git_errors as error:
            problems.append(f'không đếm được commit chưa gộp: {error}')
        try:
            stat = _git(root, 'diff', '--no-ext-diff', '--stat', f'origin/main...{ref}', '--').strip()
        except git_errors as error:
            problems.append(f'không tính được file đổi (shallow / không tổ tiên chung?): {error}')
        reviewed = bool(re.search(r'\brà\b', message, re.I))
        evidence = 'message commit cuối có rà' if reviewed else ''
        texts = [codex_text]
        report_error = ''
        if owner == 'Codex':
            try:
                texts.append(_git(root, 'show', '--no-ext-diff', '--end-of-options', f'{ref}:docs/CODEX_TASKS.md'))
            except git_errors as error:
                report_error = f'không đọc được kết quả trên nhánh: {error}'
        seen = set()
        for text in texts:
            for row in parse_codex(text):
                key = (row['wave'], row['task'], row['branch'], row['commit'])
                if row['has_result'] and row['branch'] == short and key not in seen:
                    seen.add(key)
                    data['branch_results'].append(dict(row, source=ref))
                    reviewed, evidence = True, f'Kết quả Codex nhắc {short} (không phải rà độc lập)'
        data['branches'].append({'branch': ref, 'owner': owner, 'commit': commit[:12] if commit else None, 'date': date,
                                 'ahead': ahead, 'stat': stat, 'reviewed': reviewed, 'review_evidence': evidence,
                                 'git_errors': problems,
                                 'report_error': '; '.join([*problems, report_error] if report_error else problems),
                                 'subject': message.splitlines()[0] if message else ''})
    return data


def snapshot(root=ROOT):
    try:
        text = (Path(root) / 'docs/CODEX_TASKS.md').read_text(encoding='utf-8')
        tasks, error = parse_codex(text), None
    except (OSError, UnicodeError) as reason:
        text, tasks, error = '', [], f'không đọc được CODEX_TASKS: {reason}'
    result = git_activity(root, text)
    if error:
        result['errors'].append(error)
    for row in tasks:
        candidates = [r for r in result['branch_results'] if (r['wave'], r['task']) == (row['wave'], row['task'])]
        row['unmerged_results'] = [{k: r[k] for k in ('branch', 'commit', 'source')} for r in candidates]
    result['tasks'] = tasks
    return result
