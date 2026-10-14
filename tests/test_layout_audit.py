"""core/layout_audit + tools/scene_layout_audit (người dùng 14/10, tập 2): báo shot cùng chỗ đứng mà không dây nối bố cục nào.
Ca dựng lại: thử D6 #28 — shot 1 rộng ở A (neo cả cảnh), shot 2–4 cùng ở B."""
import json
import os
import sqlite3

import pytest

from core import layout_audit
from core.db import connect
from core.pipeline import Pipeline


def _project(p, spots=(("a", "WS"), ("b", "MS"), ("b", "WS"), ("b", "CU")), extra=None):
    pid = p.create_project("d6")
    ids = []
    for i, (spot, size) in enumerate(spots, 1):
        sid = p.create_scene(pid, i, f"shot {i}")
        d = {"story_scene": 1, "shot_no": i, "size": size, "plate_spot": spot, "image_prompt": "x"}
        d.update((extra or {}).get(i, {}))
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), sid))
        ids.append(sid)
    p.conn.commit()
    return pid, ids


@pytest.fixture
def flags(monkeypatch):
    monkeypatch.setenv("FEATURE_STORYBOARD_API", "1")
    monkeypatch.setenv("FEATURE_ANCHOR_BY_SPOT", "0")
    return monkeypatch


def by_idx(res):
    return {r["idx"]: r for r in res["rows"]}


def test_flag_off_same_spot_shots_without_tie_are_red(flags, tmp_path):
    p = Pipeline(connect(":memory:"))
    pid, _ = _project(p)
    res = layout_audit.audit(p.conn, pid, str(tmp_path))
    rows = by_idx(res)
    assert [rows[i]["level"] for i in (1, 2, 3, 4)] == ["", "do", "do", "do"]
    assert rows[2]["mates"] == [3, 4] and "KHÔNG dây nối" in rows[2]["why"]
    assert any("anchor_by_spot TẮT" in n for n in res["notes"])
    text = layout_audit.report(res, "#1 d6")
    assert "**3 shot ĐỎ**" in text and "| 🔴 | 1 | 2 |" in text


def test_flag_on_ties_them_to_the_widest_shot_at_the_spot(flags, tmp_path):
    flags.setenv("FEATURE_ANCHOR_BY_SPOT", "1")
    p = Pipeline(connect(":memory:"))
    pid, ids = _project(p)
    rows = by_idx(layout_audit.audit(p.conn, pid, str(tmp_path)))
    assert rows[3]["anchor"] == "chính là neo"
    assert rows[2]["anchor"] == "shot 3" and rows[4]["anchor"] == "shot 3"
    assert all(rows[i]["level"] in ("vang", "xanh") for i in (2, 3, 4))
    assert rows[2]["level"] == "vang"                     # ảnh neo shot 3 chưa có / chưa duyệt
    assert rows[3]["linked"] == [2, 4]


def test_continuity_from_is_a_tie(flags, tmp_path):
    p = Pipeline(connect(":memory:"))
    pid, _ = _project(p, extra={4: {"continuity_from": 3}})
    rows = by_idx(layout_audit.audit(p.conn, pid, str(tmp_path)))
    assert rows[4]["level"] == "xanh" and "bố cục" in rows[4]["why"]
    assert rows[3]["level"] == "xanh" and rows[2]["level"] == "do"


def test_tool_reads_a_copy_and_never_writes_the_real_db(flags, tmp_path):
    from tools import scene_layout_audit
    db = str(tmp_path / "manifest.sqlite")
    p = Pipeline(connect(db))
    pid, _ = _project(p)
    p.conn.close()
    before = os.path.getmtime(db), os.path.getsize(db)
    out = str(tmp_path / "audit.md")
    text = scene_layout_audit.run(db, pid, str(tmp_path / "projects"), out)
    assert "**3 shot ĐỎ**" in text and open(out, encoding="utf-8").read() == text
    assert (os.path.getmtime(db), os.path.getsize(db)) == before
    assert scene_layout_audit.main(["--project", str(pid), "--db", db, "--data", str(tmp_path / "projects")]) == 1
    sqlite3.connect(db).close()
