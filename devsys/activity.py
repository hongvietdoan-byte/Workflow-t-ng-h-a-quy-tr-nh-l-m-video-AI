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


def _sections(text):
    markers = list(re.finditer(r'^# ĐỢT (\d+)\b.*$', text, re.M))
    starts = [(1, 0)] + [(int(m[1]), m.end()) for m in markers]
    for i, (wave, start) in enumerate(starts):
        end = markers[i].start() if i < len(markers) else len(text)
        yield wave, text[start:end]


def parse_codex(text):
    rows = []
    for wave, part in _sections(text):
        result = re.search(r'^## Kết quả Codex[^\n]*\n(.*)', part, re.M | re.S)
        done = {}
        for m in re.finditer(r'^- Việc (\d+)\b([^\n]*)|^\|\s*(\d+)\s*\|([^\n]*)', result[1] if result else '', re.M):
            task, body = int(m[1] or m[3]), m[2] or m[4]
            branch, commit = re.search(r'`(codex/[^`]+)`', body), re.search(r'`([0-9a-f]{7,40})`', body)
            if branch and commit:
                done[task] = {'branch': branch[1], 'commit': commit[1]}
        for m in re.finditer(r'^## Việc (\d+)\s*[—-]\s*(.+)$', part, re.M):
            task = int(m[1])
            rows.append({'wave': wave, 'task': task, 'title': m[2], 'has_result': task in done,
                         'branch': done.get(task, {}).get('branch'), 'commit': done.get(task, {}).get('commit')})
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
    for ref in refs:
        try:
            short = ref.split('/', 1)[-1]
            owner = 'Codex' if short.startswith('codex/') else ('Claude' if short.startswith(('claude/', 'worktree-agent-')) else 'người')
            commit, date, message = _git(root, 'log', '-1', '--format=%H%x00%cI%x00%B', ref, '--').strip().split('\x00', 2)
            ahead = int(_git(root, 'rev-list', '--count', f'origin/main..{ref}', '--').strip())
            stat = _git(root, 'diff', '--no-ext-diff', '--stat', f'origin/main...{ref}', '--').strip()
            reviewed = bool(re.search(r'\brà\b', message, re.I))
            evidence = 'message commit cuối có rà' if reviewed else ''
            texts = [codex_text]
            report_error = ''
            if owner == 'Codex':
                try:
                    texts.append(_git(root, 'show', '--no-ext-diff', '--end-of-options', f'{ref}:docs/CODEX_TASKS.md'))
                except ValueError as error:
                    report_error = f'không đọc được kết quả trên nhánh: {error}'
            for text in texts:
                for row in parse_codex(text):
                    if row['has_result'] and row['branch'] == short:
                        data['branch_results'].append(dict(row, source=ref))
                        reviewed, evidence = True, f'Kết quả Codex nhắc {short} (không phải rà độc lập)'
            data['branches'].append({'branch': ref, 'owner': owner, 'commit': commit[:12], 'date': date, 'ahead': ahead,
                                     'stat': stat, 'reviewed': reviewed, 'review_evidence': evidence,
                                     'report_error': report_error,
                                     'subject': message.splitlines()[0] if message else ''})
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            data['errors'].append(f'không đọc được {ref}: {error}')
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
