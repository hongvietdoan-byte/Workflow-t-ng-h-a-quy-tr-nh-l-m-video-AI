"""M60: bộ đo chỉ xuất số và vị trí source, không SQL/payload."""
import sqlite3


def test_sql_record_never_exports_literals():
    from tools.m60_profile import Timings
    t = Timings()
    t.sql("SELECT secret FROM projects WHERE name='fake-private'", .1)
    assert t.rows()[0]["label"] == "SELECT projects"
    assert "fake-private" not in str(t.rows())


def test_sql_unknown_is_not_raw_sql():
    from tools.m60_profile import Timings
    t = Timings()
    t.sql("PRAGMA user_version", .1)
    assert t.rows()[0]["label"] == "PRAGMA"


def test_sql_string_or_comment_cannot_become_exported_table():
    from tools.m60_profile import Timings
    t = Timings()
    t.sql("SELECT 'FROM fake_private' /* FROM fake_comment */ FROM projects", .1)
    assert t.rows()[0]["label"] == "SELECT projects"


def test_copy_is_readonly_and_wal_complete(tmp_path):
    from tools.m60_profile import copy_database
    src, dst = tmp_path / "s.db", tmp_path / "d.db"
    c = sqlite3.connect(src)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("CREATE TABLE sample(n)")
    c.execute("INSERT INTO sample VALUES(42)")
    c.commit()
    copy_database(src, dst)
    with sqlite3.connect(dst) as d:
        assert d.execute("SELECT n FROM sample").fetchone()[0] == 42
    assert c.execute("SELECT count(*) FROM sample").fetchone()[0] == 1
    c.close()


def test_refuse_existing_destination(tmp_path):
    import pytest
    from tools.m60_profile import copy_database
    p = tmp_path / "existing"
    p.write_bytes(b"fake")
    with pytest.raises(FileExistsError):
        copy_database(p, p)


def test_measured_function_error_has_no_message():
    from tools.m60_profile import Timings
    t = Timings()
    def f():
        raise ValueError("fake-private")
    t.measure("fixture", f)
    assert t.errors == [{"label": "fixture", "type": "ValueError"}]
    assert "fake-private" not in str(t.errors)


def test_report_replaces_hardlink_not_linked_source(tmp_path):
    import os
    from tools.m60_profile import save_report
    src, out = tmp_path / "source", tmp_path / "out.json"
    src.write_bytes(b"fake")
    os.link(src, out)
    save_report(out, {"calls": 1})
    assert src.read_bytes() == b"fake"
    assert out.read_bytes() != b"fake"


def test_sql_probe_covers_connection_cursor_and_fetch_without_double_count():
    from tools.m60_profile import Timings, measured_connection
    t = Timings()
    c = sqlite3.connect(":memory:", factory=measured_connection(t))
    c.execute("CREATE TABLE projects(n)")
    c.executemany("INSERT INTO projects VALUES(?)", [(1,), (2,)])
    cur = c.cursor()
    cur.execute("SELECT n FROM projects")
    assert cur.fetchone() == (1,)
    assert cur.fetchmany(2) == [(2,)]
    assert c.execute("SELECT n FROM projects").fetchall() == [(1,), (2,)]
    assert list(c.execute("SELECT n FROM projects")) == [(1,), (2,)]
    rows = {r["label"]: r["calls"] for r in t.rows()}
    assert rows["connection.execute SELECT projects"] == 2
    assert rows["cursor.execute SELECT projects"] == 1
    assert rows["connection.executemany INSERT projects"] == 1
    assert rows["cursor.fetchone SELECT projects"] == 1
    assert rows["cursor.fetchmany SELECT projects"] == 1
    assert rows["cursor.fetchall SELECT projects"] == 1
    assert rows["cursor.next SELECT projects"] == 3  # includes terminal StopIteration
    c.close()


def test_sql_probe_script_does_not_export_script_or_binds():
    from tools.m60_profile import Timings, measured_connection
    t = Timings()
    c = sqlite3.connect(":memory:", factory=measured_connection(t))
    c.executescript("CREATE TABLE projects(n); INSERT INTO projects VALUES('fake-private');")
    c.cursor().executescript("UPDATE projects SET n='fake-private-2';")
    rows = t.rows()
    assert {r["label"] for r in rows} == {"connection.executescript SCRIPT", "cursor.executescript SCRIPT"}
    assert all("fake-private" not in r["label"] for r in rows)
    c.close()


def test_coverage_lists_unreached_functions_and_conditions(tmp_path):
    from tools.m60_profile import coverage_manifest
    d = tmp_path / "dashboard"
    d.mkdir()
    (d / "demo.py").write_text("def view():\n    if True:\n        return 1\ndef callback():\n    return 2\n", encoding="utf-8")
    items = coverage_manifest(tmp_path, [{"label": "dashboard/demo.py:1:view", "calls": 1}])
    assert any(x["status"] == "EXECUTED" and x["source"] == "dashboard/demo.py:1:view" for x in items)
    assert any(x["status"] == "NOT_REACHED" and x["source"] == "dashboard/demo.py:4:callback" for x in items)
    assert any(x["status"] == "BRANCH_NOT_PROVEN" and x["source"] == "dashboard/demo.py:2:If" for x in items)


def test_network_scope_denies_nonowned_loopback_but_owned_pair_works():
    import socket
    import pytest
    from unittest.mock import patch
    from tools.m60_profile import isolated_network
    # A broken guard must never emit a real DNS lookup during this regression.
    with patch.object(socket, "getaddrinfo", side_effect=AssertionError("FAKE_RESOLVER_REACHED")), isolated_network():
        with socket.socket() as other:
            with pytest.raises(RuntimeError, match="M60_EXTERNAL_OPERATION_BLOCKED"):
                other.connect(("127.0.0.1", 54321))
        with pytest.raises(RuntimeError, match="M60_EXTERNAL_OPERATION_BLOCKED"):
            socket.getaddrinfo("fake.invalid", 443)
        a, b = socket.socketpair()
        try:
            a.sendall(b"fake")
            assert b.recv(4) == b"fake"
        finally:
            a.close()
            b.close()


def test_profile_refuses_output_outside_docs_before_fixture(tmp_path):
    import pytest
    from tools.m60_profile import validate_output
    (tmp_path / "docs").mkdir()
    assert validate_output(tmp_path, tmp_path / "docs" / "fake.json") == tmp_path / "docs" / "fake.json"
    with pytest.raises(ValueError, match="M60_REPORT_OUTSIDE_DOCS"):
        validate_output(tmp_path, tmp_path / "data" / "fake.json")


def test_cli_passes_bounded_args_and_only_prints_summary(monkeypatch, capsys):
    from tools import m60_profile as m
    called = []
    def fake(root, output, projects, shots):
        called.append((root, output, projects, shots))
        return {"screens": [{"exception_count": 0}]}
    monkeypatch.setattr(m, "profile_fixture", fake)
    assert m.main(["--out", "docs/fake-profile.json", "--projects", "2", "--shots", "3"]) == 0
    assert called[0][2:] == (2, 3)
    assert "fake-profile.json" in capsys.readouterr().out


def test_cli_filters_errors_and_refuses_data_path(monkeypatch, capsys):
    from tools import m60_profile as m
    called = []
    def fake(*args, **kwargs):
        called.append(True)
        raise ValueError("fake-private")
    monkeypatch.setattr(m, "profile_fixture", fake)
    assert m.main(["--out", "data/fake.json"]) == 2
    assert not called
    assert m.main(["--projects", "11"]) == 2
    assert not called
    assert m.main(["--out", "docs/fake.json"]) == 2
    assert called
    output = capsys.readouterr().out
    assert "ValueError" in output
    assert "fake-private" not in output


def test_cli_returns_failure_for_ui_or_lineage_errors(monkeypatch, capsys):
    from tools import m60_profile as m
    for result in ({"screens": [{"exception_count": 1}]},
                   {"screens": [{"exception_count": 0}], "errors": [{"type": "FakeError"}]}):
        monkeypatch.setattr(m, "profile_fixture", lambda *a, **kw: result)
        assert m.main(["--out", "docs/fake.json"]) == 1
    assert '"exceptions": 1' in capsys.readouterr().out
