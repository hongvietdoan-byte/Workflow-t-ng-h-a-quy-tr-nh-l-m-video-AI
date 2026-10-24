"""Hai tiến trình thật, remote bare riêng; metadata không được mang theo code."""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

SOURCE = Path(__file__).resolve().parents[1]
GIT = Path("C:/Program Files/Git/cmd/git.exe") if os.name == "nt" else Path("/usr/bin/git")


@pytest.mark.skipif(not GIT.is_file(), reason="chưa có Git native đã xác định")
def test_two_process_batches_keep_all_mail_and_do_not_publish_checkout_code(tmp_path):
    home = tmp_path / "fake-home"
    home.mkdir()
    env = {"HOME": str(home), "USERPROFILE": str(home), "TEMP": str(tmp_path), "TMP": str(tmp_path),
           "PATH": str(GIT.parent) + (";C:/Windows/System32" if os.name == "nt" else ":/usr/bin:/bin"),
           "SystemRoot": "C:/Windows", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_TERMINAL_PROMPT": "0", "GIT_ALLOW_PROTOCOL": "file", "PYTHONUTF8": "1"}
    with mock.patch.object(os, "environ", env):
        def git(root, *args):
            result = subprocess.run([str(GIT), *args], cwd=root, env=env, capture_output=True,
                                    text=True, encoding="utf-8", errors="replace", timeout=30)
            assert result.returncode == 0, "Git fixture thất bại"
            return result.stdout.strip()

        remote, seed = tmp_path / "remote.git", tmp_path / "seed"
        git(tmp_path, "init", "--bare", "-q", "-b", "main", str(remote))
        git(tmp_path, "clone", "-q", str(remote), str(seed))
        events = seed / "hop_thu/su_kien"
        events.mkdir(parents=True)
        initial = [
            {"ts": "2026-10-20T10:00:00+07:00", "kind": "giao", "lane": "phien-chinh", "to": "codex", "task": "T1", "title": "fixture"},
            {"ts": "2026-10-20T10:01:00+07:00", "kind": "nhan", "lane": "codex", "task": "T1"},
        ]
        for index, data in enumerate(initial):
            (events / f"seed{index}.json").write_text(json.dumps(data), encoding="utf-8")
        git(seed, "add", "hop_thu")
        git(seed, "-c", "user.name=Fixture", "-c", "user.email=fake@example.invalid", "commit", "-q", "-m", "base")
        git(seed, "push", "-q", "origin", "HEAD:main")
        a, b = tmp_path / "a", tmp_path / "b"
        for repo in (a, b):
            git(tmp_path, "clone", "-q", "-b", "main", str(remote), str(repo))
        git(a, "checkout", "-q", "-b", "codex/private-code")
        (a / "must_not_publish.py").write_text("fixture = True\n", encoding="utf-8")
        git(a, "add", "must_not_publish.py")
        git(a, "-c", "user.name=Fixture", "-c", "user.email=fake@example.invalid", "commit", "-q", "-m", "private code")
        for repo in (a, b):
            (repo / "staged.py").write_text("fixture_staged = True\n", encoding="utf-8")
            git(repo, "add", "staged.py")
        before = {repo: (git(repo, "rev-parse", "HEAD"), git(repo, "write-tree")) for repo in (a, b)}
        baseline = int(git(remote, "rev-list", "--count", "main"))
        script = """
import sys
sys.path.insert(0, sys.argv[1])
from tools import hop_thu as ht
root, prefix, number = sys.argv[2], sys.argv[3], int(sys.argv[4])
for index in range(number):
    code = ht.main(['--goc', root, 'tin', '--lane', 'codex', '--to', 'phien-chinh', '--text', prefix + str(index)])
    if code: raise SystemExit(code)
if prefix == 'A':
    args = ['xong', 'T1', '--lane', 'codex', '--branch', 'codex/fixture', '--commit', 'abcdef1', '--text', 'fixture done', '--push']
else:
    args = ['hoi', '--lane', 'codex', '--to', 'phien-chinh', '--task', 'T1', '--text', 'fixture question', '--push']
raise SystemExit(ht.main(['--goc', root, *args]))
"""
        processes = []
        try:
            for repo, prefix, count in ((a, "A", 4), (b, "B", 3)):
                processes.append(subprocess.Popen([sys.executable, "-c", script, str(SOURCE), str(repo), prefix, str(count)],
                                                  cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
            for process in processes:
                process.communicate(timeout=90)
                assert process.returncode == 0, "CLI fixture hai tiến trình chưa hoàn tất"
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=15)
        names = git(remote, "ls-tree", "-r", "--name-only", "main").splitlines()
        assert "must_not_publish.py" not in names and "staged.py" not in names
        assert len([name for name in names if name.startswith("hop_thu/su_kien/")]) == 11
        assert int(git(remote, "rev-list", "--count", "main")) - baseline == 2
        for repo in (a, b):
            assert (git(repo, "rev-parse", "HEAD"), git(repo, "write-tree")) == before[repo]
