from pathlib import Path
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
