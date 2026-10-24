"""G3: cảnh báo chỉ đọc, branch tường minh và Git fixture; không suy owner."""
import os
import subprocess
from datetime import timedelta
from pathlib import Path
from unittest import mock

import pytest

with mock.patch.object(os, "environ", {"PYTHONUTF8": "1"}):
    from tools import hop_thu as ht


@pytest.fixture(autouse=True)
def isolated(tmp_path):
    with mock.patch.object(os, "environ", {"PYTHONUTF8": "1", "HOME": str(tmp_path)}):
        yield


def state(tmp_path, hours=13, branch="codex/test", lane="codex"):
    now = ht.now_vn()
    ht.write_event(tmp_path, "phien-chinh", "giao", now=now-timedelta(hours=hours+1), task="T1", to=lane)
    ht.write_event(tmp_path, lane, "nhan", now=now-timedelta(hours=hours), task="T1", branch=branch)
    events, errors = ht.load_events(tmp_path)
    assert not errors
    return ht.compute_state(events), now


def test_no_commit_over_12h_only_suggests_wait(tmp_path):
    st, now = state(tmp_path)
    with mock.patch.object(ht, "branch_commit_time", return_value=(None, "")):
        warnings = ht.stale_warnings(tmp_path, st, now=now)
    assert len(warnings) == 1
    assert "CHỜ" in warnings[0] and "T1" in warnings[0]
    assert st["tasks"]["T1"].status == ht.DANG_LAM


def test_recent_commit_and_young_claim_do_not_warn(tmp_path):
    st, now = state(tmp_path)
    with mock.patch.object(ht, "branch_commit_time", return_value=(now-timedelta(hours=1), "")):
        assert not ht.stale_warnings(tmp_path, st, now=now)


def test_old_commit_and_same_claimer_assignment_do_not_reset_age(tmp_path):
    st, now = state(tmp_path)
    claimed = st["tasks"]["T1"].ts_claim
    ht.write_event(tmp_path, "phien-chinh", "giao", now=now, task="T1", to="codex")
    events, _ = ht.load_events(tmp_path)
    st = ht.compute_state(events)
    assert st["tasks"]["T1"].ts_claim == claimed
    with mock.patch.object(ht, "branch_commit_time", return_value=(claimed-timedelta(hours=1), "")):
        assert "CHỜ" in ht.stale_warnings(tmp_path, st, now=now)[0]
    st["tasks"]["T1"].ts_claim = now-timedelta(hours=12)
    with mock.patch.object(ht, "branch_commit_time", side_effect=AssertionError("không cần Git")):
        assert not ht.stale_warnings(tmp_path, st, now=now)


def test_unknown_branch_not_inferred_from_text_and_lane_filter(tmp_path):
    st, now = state(tmp_path, branch=None)
    st["news"].append({"task": "T1", "text": "nhánh codex/guess", "lane": "codex"})
    with mock.patch.object(ht, "branch_commit_time", side_effect=AssertionError("không suy nhánh")):
        warning = ht.stale_warnings(tmp_path, st, now=now)
        assert "chưa xác minh" in warning[0]
        assert not ht.stale_warnings(tmp_path, st, now=now, lane_filter="cloud-B")


def test_completed_and_reassigned_tasks_do_not_keep_old_branch(tmp_path):
    st, now = state(tmp_path)
    ht.write_event(tmp_path, "phien-chinh", "giao", now=now, task="T1", to="cloud-B")
    ht.write_event(tmp_path, "cloud-B", "nhan", now=now+timedelta(seconds=1), task="T1")
    events, _ = ht.load_events(tmp_path)
    st = ht.compute_state(events)
    assert st["tasks"]["T1"].branch is None
    with mock.patch.object(ht, "branch_commit_time", side_effect=AssertionError("không dùng nhánh cũ")):
        assert "chưa xác minh" in ht.stale_warnings(tmp_path, st, now=now+timedelta(hours=14))[0]
    st["tasks"]["T1"].status = ht.XONG
    assert not ht.stale_warnings(tmp_path, st, now=now+timedelta(hours=14))


def test_branch_progress_metadata_only_from_current_claimer(tmp_path):
    st, now = state(tmp_path, branch=None)
    ht.write_event(tmp_path, "cloud-B", "tin", now=now, task="T1", branch="codex/wrong")
    ht.write_event(tmp_path, "codex", "tin", now=now+timedelta(seconds=1), task="T1", branch="codex/right")
    events, _ = ht.load_events(tmp_path)
    assert ht.compute_state(events)["tasks"]["T1"].branch == "codex/right"


def test_git_probe_only_reads_safe_refs_and_distinguishes_unknown(tmp_path):
    now = ht.now_vn()
    result = mock.Mock(returncode=0, stdout=str(int(now.timestamp()))+"\n")
    with mock.patch.object(ht, "_git", return_value=result) as git:
        stamp, why = ht.branch_commit_time(tmp_path, "codex/test")
    assert stamp.timestamp() == int(now.timestamp()) and not why
    calls = [call.args[1:] for call in git.call_args_list]
    assert any("--not" in args and "refs/remotes/origin/main" in args for args in calls)
    assert not any(args[0] in ("fetch", "pull", "checkout", "reset") for args in calls)
    with mock.patch.object(ht, "_git", side_effect=AssertionError("không gửi ref nguy hiểm")):
        assert ht.branch_commit_time(tmp_path, "--all")[1]
    with mock.patch.object(ht, "_git", side_effect=ht.HopThuError("fixture")):
        assert ht.branch_commit_time(tmp_path, "codex/test")[1]
    with mock.patch.object(ht, "_git", return_value=mock.Mock(returncode=1)):
        assert "origin/main" in ht.branch_commit_time(tmp_path, "codex/test")[1]


def test_future_commit_is_unknown_not_silent(tmp_path):
    st, now = state(tmp_path)
    with mock.patch.object(ht, "branch_commit_time", return_value=(now+timedelta(hours=1), "")):
        assert "chưa xác minh" in ht.stale_warnings(tmp_path, st, now=now)[0]


def test_bang_includes_warnings_without_writes(tmp_path, capsys):
    st, now = state(tmp_path)
    with mock.patch.object(ht, "_load", return_value=(st, [])), \
            mock.patch.object(ht, "stale_warnings", return_value=["T1: thử CHỜ, không tự đổi"]), \
            mock.patch.object(ht, "write_event", side_effect=AssertionError("chỉ đọc")):
        ht.cmd_bang(mock.Mock(lane="codex"), tmp_path)
    assert "thử CHỜ" in capsys.readouterr().out


def test_optional_branch_cli_metadata_is_backward_compatible(tmp_path):
    assert ht.main(["--goc", str(tmp_path), "giao", "T1", "--lane", "phien-chinh", "--to", "codex", "--title", "fake"]) == 0
    assert ht.main(["--goc", str(tmp_path), "nhan", "T1", "--lane", "codex", "--branch", "codex/test", "--khong-pull"]) == 0
    assert ht.main(["--goc", str(tmp_path), "tin", "--lane", "codex", "--task", "T1", "--branch", "codex/next", "--text", "Codex 1 fake"]) == 0
    events, errors = ht.load_events(tmp_path)
    assert not errors
    assert ht.compute_state(events)["tasks"]["T1"].branch == "codex/next"
    assert ht.main(["--goc", str(tmp_path), "giao", "T2", "--lane", "phien-chinh", "--to", "codex", "--title", "fake"]) == 0
    assert ht.main(["--goc", str(tmp_path), "ke", "--lane", "codex", "--nhan", "--branch", "codex/second", "--khong-pull"]) == 0
    events, _ = ht.load_events(tmp_path)
    assert ht.compute_state(events)["tasks"]["T2"].branch == "codex/second"


def test_native_private_git_distinguishes_base_from_task_commits(tmp_path):
    git = Path("C:/Program Files/Git/cmd/git.exe") if os.name == "nt" else Path("/usr/bin/git")
    if not git.is_file():
        pytest.skip("chưa có Git native đã xác định")
    env = {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path), "TEMP": str(tmp_path), "TMP": str(tmp_path),
           "SystemRoot": "C:/Windows", "PATH": str(git.parent), "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_DATE": "2026-10-23T00:00:00+07:00", "GIT_COMMITTER_DATE": "2026-10-23T00:00:00+07:00"}
    def run(*args, check=True):
        result = subprocess.run([str(git), *args], cwd=tmp_path, env=env, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=15)
        assert not check or result.returncode == 0, "Git fixture không chạy được"
        return result
    run("init", "-q")
    run("-c", "user.name=Fixture", "-c", "user.email=fake@example.invalid", "commit", "-q", "--allow-empty", "-m", "base")
    run("update-ref", "refs/remotes/origin/main", "HEAD")
    run("checkout", "-q", "-b", "codex/probe")
    def readonly(root, *args, check=True, **kwargs):
        assert args[0] in ("show-ref", "log")
        return run(*args, check=check)
    with mock.patch.object(ht, "_git", side_effect=readonly):
        assert ht.branch_commit_time(tmp_path, "codex/probe") == (None, "")
        assert ht.branch_commit_time(tmp_path, "codex/missing")[1]
    run("-c", "user.name=Fixture", "-c", "user.email=fake@example.invalid", "commit", "-q", "--allow-empty", "-m", "task")
    with mock.patch.object(ht, "_git", side_effect=readonly):
        stamp, why = ht.branch_commit_time(tmp_path, "codex/probe")
        assert stamp.year == 2026 and not why
