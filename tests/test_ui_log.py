"""Nhật ký thao tác Dashboard (core/ui_log.py, bảng ui_actions — 14/10 tập 2 #27)."""
import os
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from core import ui_log  # noqa: E402
from core.db import connect  # noqa: E402


def _conn():
    return connect(":memory:")


def _put(conn, action, at, **kw):
    ui_log.record(conn, action, **kw)
    conn.execute("UPDATE ui_actions SET at=? WHERE id=(SELECT MAX(id) FROM ui_actions)", (at,))
    conn.commit()


def test_record_writes_row_with_redacted_short_detail():
    conn = _conn()
    assert ui_log.record(conn, "gen_anh", email="a@garena.vn", source="CLAUDE ", page="storyboard", project_id=27,
                         job_id="5", result="weird", detail="key sk-ant-api03-" + "x" * 40 + " " + "y" * 500, ms=12.7)
    r = dict(conn.execute("SELECT * FROM ui_actions").fetchone())
    assert r["source"] == "claude" and r["result"] == "ok" and r["job_id"] == 5 and r["ms"] == 12
    assert len(r["detail"]) <= ui_log.DETAIL_MAX and "sk-ant-api03-xxxx" not in r["detail"]


def test_record_never_raises_when_table_missing_or_conn_broken(monkeypatch):
    ui_log._warned.clear()
    calls = []
    from core import diag
    monkeypatch.setattr(diag, "record", lambda *a, **k: calls.append(a))
    bare = sqlite3.connect(":memory:")                       # no ui_actions table
    assert ui_log.record(bare, "gen_anh") is False
    assert ui_log.record(bare, "gen_video") is False
    assert ui_log.record(None, "gen_video") is False
    assert len(calls) == 1                                   # diag once per process, not on every click
    closed = _conn()
    closed.close()
    assert ui_log.record(closed, "duyet_anh") is False
    assert ui_log.summary(bare)["total"] == 0


def test_migration_adds_table_to_old_database(tmp_path):
    path = str(tmp_path / "old.sqlite")
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT)")
    old.execute("INSERT INTO projects (name) VALUES ('cũ')")
    old.commit()
    old.close()
    conn = connect(path)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(ui_actions)")}
    assert {"at", "email", "source", "page", "action", "project_id", "scene_id", "job_id", "result", "detail", "ms"} <= cols
    assert conn.execute("SELECT name FROM projects").fetchone()[0] == "cũ"
    assert ui_log.record(conn, "ban_giao", project_id=1)


def test_source_from_query_param_sticks_for_session():
    assert ui_log.source_from("claude", None) == "claude"
    assert ui_log.source_from(["claude"], None) == "claude"
    assert ui_log.source_from(None, "claude") == "claude"        # after sign-in the ?op= param is gone: keeps the session's source
    assert ui_log.source_from("", "claude") == "claude"
    assert ui_log.source_from(None, None) == "nguoi"
    assert ui_log.source_from("nguoi", "claude") == "nguoi"
    assert ui_log.source_from("admin", None) == "nguoi"          # anything else = người (no rights change by source)


def test_summary_finds_flip_flops_and_double_clicks():
    conn = _conn()
    t = 1_000_000.0
    _put(conn, "duyet_anh", t, project_id=1, job_id=10, email="a")
    _put(conn, "loai_anh", t + 120, project_id=1, job_id=10, email="a")          # đổi ý ≤ 5 phút
    _put(conn, "duyet_anh", t, project_id=1, job_id=11, email="a")
    _put(conn, "loai_anh", t + 900, project_id=1, job_id=11, email="a")          # quá 5 phút: không tính
    _put(conn, "duyet_video", t, project_id=1, job_id=12, email="a", source="claude")
    _put(conn, "loai_anh", t + 10, project_id=1, job_id=12, email="a")           # khác loại nội dung: không tính
    _put(conn, "gen_video", t + 1000, project_id=2, email="a")
    _put(conn, "huy_job", t + 1100, project_id=2, job_id=20, email="a")          # gen → hủy
    _put(conn, "gen_anh", t + 2000, project_id=3, email="b", result="noop")
    _put(conn, "gen_anh", t + 2004, project_id=3, email="b")                     # bấm đôi, lần 1 noop
    _put(conn, "gen_anh", t + 3000, project_id=3, email="b")
    _put(conn, "gen_anh", t + 3003, project_id=3, email="b")                     # lần 1 ok: không tính bấm hụt
    _put(conn, "gen_anh", t + 4000, project_id=3, email="b", result="noop")
    _put(conn, "gen_anh", t + 4030, project_id=3, email="b")                     # quá 10 s
    s = ui_log.summary(conn)
    kinds = sorted((f["kind"], f["job_id"]) for f in s["flips"])
    assert kinds == [("duyet_anh→loai_anh", 10), ("gen_video→huy_job", 20)]
    assert [(d["action"], d["seconds"]) for d in s["doubles"]] == [("gen_anh", 4.0)]
    assert s["by_source"] == {"nguoi": 13, "claude": 1}
    assert ui_log.summary(conn, project_id=3)["total"] == 6
    assert ui_log.summary(conn, source="claude")["total"] == 1


def test_report_tool_is_read_only(tmp_path):
    from tools import ui_actions_report as rep
    path = str(tmp_path / "m.sqlite")
    c = connect(path)
    ui_log.record(c, "duyet_anh", project_id=4, job_id=1, ms=50)
    c.close()
    ro = rep.open_ro(path)
    text = rep.report(ro, project_id=4)
    assert "dự án #4" in text and "duyet_anh" in text and "~50 ms" in text
    try:
        ro.execute("INSERT INTO ui_actions (at, action) VALUES (1, 'x')")
        raise AssertionError("ghi được vào CSDL chỉ đọc")
    except sqlite3.OperationalError:
        pass
