"""Nghiệm thu CLI độc lập: các lượt đọc không thể ack hộ phiên khác."""
import io
import json
import os
import socket
import subprocess
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from unittest import mock

import pytest

with mock.patch.object(os, "environ", {}):
    from tools import hop_thu as ht


@pytest.fixture(autouse=True)
def isolated(tmp_path):
    with mock.patch.object(os, "environ", {"PYTHONUTF8": "1", "HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}), \
            mock.patch.object(socket.socket, "connect", side_effect=AssertionError("fixture only")), \
            mock.patch.object(subprocess, "Popen", side_effect=AssertionError("fixture only")), \
            mock.patch.object(ht, "git_pull", return_value=None), \
            mock.patch.object(ht, "is_git_repo", return_value=False):
        yield


def event(root, name, ts, **fields):
    path = root / "hop_thu/su_kien" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"ts": ts, "lane": "phien-chinh", "kind": "tin", "to": "codex", "text": "fixture", **fields}
    path.write_text(json.dumps(data), encoding="utf-8")


def cli(root, *args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = ht.main(["--goc", str(root), *args])
    return code, out.getvalue(), err.getvalue()


def test_cli_board_does_not_expand_seen_snapshot_or_ack_other_codex(tmp_path):
    event(tmp_path, "seen.json", "2026-10-23T12:00:00+07:00")
    code, out, _ = cli(tmp_path, "chua-doc", "--lane", "codex", "--reader", "codex1")
    assert code == 0 and "seen.json" in out
    # Đến muộn nhưng có timestamp CŨ HƠN. bang chỉ được đếm, không đánh dấu đã đọc.
    event(tmp_path, "late.json", "2026-10-22T12:00:00+07:00")
    assert cli(tmp_path, "bang", "--lane", "codex")[0] == 0
    assert cli(tmp_path, "da-doc", "--lane", "codex", "--reader", "codex1", "--den", "seen.json")[0] == 0
    code, out, _ = cli(tmp_path, "chua-doc", "--lane", "codex", "--reader", "codex1")
    assert code == 0 and "late.json" in out and "seen.json" not in out
    for reader in ("codex2", "codex3"):
        code, out, _ = cli(tmp_path, "chua-doc", "--lane", "codex", "--reader", reader)
        assert code == 0 and "seen.json" in out and "late.json" in out
    assert cli(tmp_path, "da-doc", "--lane", "codex")[0] == 1


def test_cli_to_all_does_not_retroactively_add_future_lane(tmp_path):
    broadcast = ht.write_event(tmp_path, "phien-chinh", "tin", to="all", text="fixture",
                              now=datetime.fromisoformat("2026-10-22T12:00:00+07:00"))
    event(tmp_path, "assign.json", "2026-10-23T12:00:00+07:00", kind="giao", task="FUTURE", to="cloud-Z", title="fixture")
    code, out, _ = cli(tmp_path, "chua-doc", "--lane", "cloud-Z")
    assert code == 0 and "assign.json" in out and broadcast.name not in out


def test_legacy_broadcast_without_recipient_snapshot_is_not_hidden(tmp_path):
    # Legacy chưa có bằng chứng người nhận: giữ unread bảo thủ, không giả đã biết.
    event(tmp_path, "legacy.json", "2026-10-22T12:00:00+07:00", to="all")
    for lane, extra in (("codex", ("--reader", "codex1")), ("cloud-Z", ())):
        code, out, _ = cli(tmp_path, "chua-doc", "--lane", lane, *extra)
        assert code == 0 and "legacy.json" in out


def test_new_broadcast_recipients_survive_backdated_lane_arrival(tmp_path):
    broadcast = ht.write_event(tmp_path, "phien-chinh", "tin", to="all", text="fixture broadcast",
                              now=datetime.fromisoformat("2026-10-23T12:00:00+07:00"))
    code, out, _ = cli(tmp_path, "chua-doc", "--lane", "codex", "--reader", "codex1")
    assert code == 0 and broadcast.name in out
    assigned = ht.write_event(tmp_path, "phien-chinh", "giao", to="cloud-Z", task="EARLY", title="fixture",
                             now=datetime.fromisoformat("2026-10-22T12:00:00+07:00"))
    code, out, _ = cli(tmp_path, "chua-doc", "--lane", "cloud-Z")
    assert code == 0 and assigned.name in out and broadcast.name not in out


def test_malformed_control_field_does_not_echo_fake_payload(tmp_path):
    sentinel = "FAKE_PRIORITY_SENTINEL"
    event(tmp_path, "bad.json", "2026-10-22T12:00:00+07:00", kind="giao", task="BAD", priority=sentinel)
    code, out, err = cli(tmp_path, "bang", "--lane", "codex")
    assert sentinel not in out + err
    assert "bad.json" in out + err
