from pathlib import Path
import re
import subprocess
from devsys import activity


def git(root, *args):
    return subprocess.run(['git', '-c', 'user.name=T', '-c', 'user.email=t@x', '-c', 'commit.gpgsign=false', *args],
                          cwd=root, check=True, capture_output=True, text=True).stdout


def test_git_branches_worktree_and_review(tmp_path):
    git(tmp_path, 'init')
    (tmp_path / 'file.txt').write_text('base')
    git(tmp_path, 'add', '.'); git(tmp_path, 'commit', '-m', 'base')
    base = git(tmp_path, 'rev-parse', 'HEAD').strip()
    git(tmp_path, 'update-ref', 'refs/remotes/origin/main', base)
    git(tmp_path, 'switch', '-c', 'codex/test')
    (tmp_path / 'file.txt').write_text('Codex change')
    git(tmp_path, 'commit', '-am', 'Đã rà thay đổi')
    git(tmp_path, 'update-ref', 'refs/remotes/origin/codex/test', 'HEAD')
    git(tmp_path, 'switch', '-c', 'claude/test', base)
    (tmp_path / 'file.txt').write_text('Claude change')
    git(tmp_path, 'commit', '-am', 'Thay đổi khác')
    git(tmp_path, 'update-ref', 'refs/remotes/origin/claude/test', 'HEAD')
    git(tmp_path, 'worktree', 'add', '--detach', str(tmp_path / 'work'), base)
    result = activity.git_activity(tmp_path)
    assert not result['errors']
    assert {b['branch'] for b in result['branches']} == {'origin/codex/test', 'origin/claude/test'}
    assert {b['owner'] for b in result['branches']} == {'Codex', 'Claude'}
    assert all(b['ahead'] == 1 and 'file.txt' in b['stat'] and b['date'] and b['commit'] for b in result['branches'])
    assert next(b for b in result['branches'] if b['owner'] == 'Codex')['reviewed']
    assert not next(b for b in result['branches'] if b['owner'] == 'Claude')['reviewed']
    assert len(result['worktrees']) == 2


def test_codex_results_keep_rounds_separate():
    text = '## Việc 1 — một\n## Kết quả Codex\n- Việc 1 · `codex/one` · `abcdef1` · rà\n# ĐỢT 2 — hai\n## Việc 1 — mới\n## Việc 2 — kế\n## Kết quả Codex — đợt 2\n| 1 | `codex/two` | `123abcd` | rà |\n# ĐỢT 3 — ba\n## Việc 1 — cuối\n## Kết quả Codex — đợt 3\n(Codex ghi)'
    rows = activity.parse_codex(text)
    assert [(r['wave'], r['task'], r['has_result']) for r in rows] == [(1, 1, True), (2, 1, True), (2, 2, False), (3, 1, False)]
    assert rows[1]['branch'] == 'codex/two' and rows[1]['commit'] == '123abcd'


def test_git_error_is_explicit(tmp_path):
    result = activity.git_activity(tmp_path)
    assert result['errors'] and 'không đọc được' in result['errors'][0]


def test_orphan_branch_keeps_row_with_reason(tmp_path):
    git(tmp_path, 'init')
    (tmp_path / 'file.txt').write_text('base')
    git(tmp_path, 'add', '.'); git(tmp_path, 'commit', '-m', 'base')
    git(tmp_path, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
    git(tmp_path, 'switch', '--orphan', 'mo-coi')
    (tmp_path / 'other.txt').write_text('orphan')
    git(tmp_path, 'add', 'other.txt'); git(tmp_path, 'commit', '-m', 'nhánh mồ côi')
    git(tmp_path, 'update-ref', 'refs/remotes/origin/mo-coi', 'HEAD')
    result = activity.git_activity(tmp_path)
    row = next(b for b in result['branches'] if b['branch'] == 'origin/mo-coi')
    assert row['commit'] and row['date'] and row['subject'] == 'nhánh mồ côi' and row['owner'] == 'người'
    assert row['stat'] is None and row['git_errors'] and 'file đổi' in row['git_errors'][0]
    assert 'file đổi' in row['report_error']
    assert not result['errors']


def test_codex_results_without_prefix_or_hash_and_wave_without_tasks():
    text = ('## Việc 1 — một\n## Kết quả Codex\n- Việc 1 · `codex/one` · `abcdef1` · rà\n'
            '# ĐỢT 4 — bốn\n## Việc 1 — a\n## Việc 2 — b\n## Việc 3 — c\n## Kết quả Codex — đợt 4\n'
            '| Việc | Nhánh | Commit | Bằng chứng |\n|---|---|---|---|\n'
            '| 1 | `codex/d4` | `025b346` (riêng `d571899`) | ok |\n| 2 | `d4-viec2-byd-flaky` (Claude) | `06b4a38` | ok |\n'
            '| 3 | (Claude, cùng lần chạy) | — | 4004 passed |\n'
            '# ĐỢT 5 — NGHIÊN CỨU\nmô tả\n## Kết quả Codex — đợt 5\n✅ xong, nhánh `codex/d5-x`.\n- Commit nội dung `39c290a`.\n'
            '# ĐỢT 6 — chưa làm\nmô tả\n## Kết quả Codex — đợt 6\n(Codex ghi)\n')
    rows = activity.parse_codex(text)
    got = {(r['wave'], r['task']): r for r in rows}
    assert got[(4, 1)]['branch'] == 'codex/d4' and got[(4, 1)]['commit'] == '025b346'
    assert got[(4, 2)]['has_result'] and got[(4, 2)]['branch'] == 'd4-viec2-byd-flaky' and got[(4, 2)]['commit'] == '06b4a38'
    assert got[(4, 3)]['has_result'] and got[(4, 3)]['commit'] is None
    assert got[(5, None)]['has_result'] and got[(5, None)]['branch'] == 'codex/d5-x' and got[(5, None)]['commit'] == '39c290a'
    assert 'không tách được việc' in got[(5, None)]['title']
    assert not got[(6, None)]['has_result']


def test_repo_codex_tasks_every_wave_listed():
    text = (Path(activity.ROOT) / 'docs/CODEX_TASKS.md').read_text(encoding='utf-8')
    rows = activity.parse_codex(text)
    waves = {int(w) for w in re.findall(r'^# ĐỢT (\d+)', text, re.M)}
    assert {1} | waves <= {r['wave'] for r in rows}
    got = {(r['wave'], r['task']): r for r in rows}
    assert got[(4, 2)]['has_result'] and got[(4, 3)]['has_result']
    assert any(r['wave'] == 5 and r['has_result'] for r in rows)


def test_branch_results_not_duplicated(tmp_path):
    git(tmp_path, 'init')
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs/CODEX_TASKS.md').write_text('## Việc 1 — một\n## Kết quả Codex\n(trống)\n', encoding='utf-8')
    git(tmp_path, 'add', '.'); git(tmp_path, 'commit', '-m', 'base')
    git(tmp_path, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
    git(tmp_path, 'switch', '-c', 'codex/one')
    report = '## Việc 1 — một\n## Kết quả Codex\n- Việc 1 · `codex/one` · `abcdef1` · rà\n'
    (tmp_path / 'docs/CODEX_TASKS.md').write_text(report, encoding='utf-8')
    git(tmp_path, 'commit', '-am', 'kết quả')
    git(tmp_path, 'update-ref', 'refs/remotes/origin/codex/one', 'HEAD')
    result = activity.git_activity(tmp_path, report)
    assert len(result['branch_results']) == 1
