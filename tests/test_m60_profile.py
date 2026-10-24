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
