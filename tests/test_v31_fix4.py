"""C-FIX4 (sau C-FIX3-THAP-B): mục rà LỖI (review_fail) — khung Rà soát tác động không còn "✓ Đã sửa" (trước: bấm là âm thầm gọi Claude rà
lại, không báo giá); "↻ Rà lại" hiện ước tính Claude TRƯỚC khi bấm; mục thường giữ "✓ Đã sửa". AppTest trên khung thật."""
import json
import os
from unittest import mock

import pytest
from streamlit.testing.v1 import AppTest

from core import change_review as CR
from core.db import connect
from core.pipeline import Pipeline


def _page(db):
    import streamlit as st
    from core.db import connect as _c
    from core.pipeline import Pipeline as _P
    from dashboard import change_review_ui
    p = _P(_c(db))
    pid = p.conn.execute("SELECT MIN(id) FROM projects").fetchone()[0]
    change_review_ui.render(p, pid, who="tester@x")
    st.session_state["_states"] = [r[0] for r in p.conn.execute("SELECT state FROM change_events ORDER BY id")]
    st.session_state["_open"] = [r[0] for r in p.conn.execute("SELECT status FROM change_findings ORDER BY id")]


@pytest.fixture
def db(monkeypatch, tmp_path):
    tmp = str(tmp_path)
    monkeypatch.setenv("FEATURE_SETTINGS_FILE", os.path.join(tmp, "none.json"))
    monkeypatch.setenv("FEATURE_CHANGE_REVIEW", "1")
    path = os.path.join(tmp, "m.sqlite")
    p = Pipeline(connect(path))
    pid = p.create_project("t")
    sid = p.create_scene(pid, 1, "s1")
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"size": "WS", "image_prompt": "Wide shot, Kelly"}), sid))
    p.conn.commit()
    ev = p.conn.execute("SELECT MAX(id) FROM change_events").fetchone()[0]
    p.conn.execute("UPDATE change_events SET state='skipped' WHERE id<>?", (ev,))
    p.conn.execute("UPDATE change_events SET state='failed', note='LlmError: timed out', reviewed_at='2026-10-22T00:00:00Z' WHERE id=?",
                   (ev,))
    p.conn.commit()
    assert "rà soát lỗi" in (CR.blocking(p.conn, sid) or "")          # ra mục rà lỗi
    CR._add(p.conn, None, pid, sid, "claude", "do", "motion", "motion tả trạng thái cuối cũ")   # một mục thường để so
    p.conn.commit()
    p.conn.close()
    return path


def _keys(at, prefix):
    return [b.key for b in at.button if (b.key or "").startswith(prefix)]


def test_failure_finding_has_no_fixed_button_and_the_rerun_button_shows_the_estimate(db):
    with mock.patch("core.cost.llm_estimate", return_value=0.0123):
        at = AppTest.from_function(_page, args=(db,)).run()
    assert not at.exception
    conn = connect(db)
    fail_id = conn.execute("SELECT id FROM change_findings WHERE source=?", (CR.FAIL_SOURCE,)).fetchone()[0]
    other_id = conn.execute("SELECT id FROM change_findings WHERE source='claude'").fetchone()[0]
    conn.close()
    assert f"cr_ok_{fail_id}" not in _keys(at, "cr_ok_")                    # không "✓ Đã sửa" trên mục rà lỗi
    assert f"cr_ok_{other_id}" in _keys(at, "cr_ok_")                       # mục thường vẫn có
    rerun = at.button(key=f"cr_rerun_{fail_id}")
    from core import cost
    assert f"Claude ≈ {0.0123 * cost.LLM_MARGIN:.2f} USD" in rerun.label    # ước tính TRƯỚC khi bấm, tính dư như mọi nút Claude
    assert at.session_state["_states"][-1] == "failed"                      # vẽ khung không gọi rà lại


def test_skip_on_a_failure_finding_does_not_call_claude(db):
    at = AppTest.from_function(_page, args=(db,)).run()
    conn = connect(db)
    fail_id = conn.execute("SELECT id FROM change_findings WHERE source=?", (CR.FAIL_SOURCE,)).fetchone()[0]
    conn.close()
    with mock.patch.object(CR, "rerun_failed", side_effect=AssertionError("không được gọi")):
        at.button(key=f"cr_skip_{fail_id}").click().run()
    assert not at.exception
    assert at.session_state["_states"][-1] == "failed"                      # không đưa về chờ rà (không tốn Claude)


@pytest.mark.parametrize("safe", [False, True])
def test_rerun_button_puts_the_change_back_in_the_queue(db, safe, monkeypatch):
    if not safe:
        monkeypatch.setenv("FEATURE_SAFE_PAID_BUTTONS", "0")             # M8.0 cờ tắt: bấm là rà lại như cũ
    at = AppTest.from_function(_page, args=(db,)).run()
    conn = connect(db)
    fail_id = conn.execute("SELECT id FROM change_findings WHERE source=?", (CR.FAIL_SOURCE,)).fetchone()[0]
    conn.close()
    at.button(key=f"cr_rerun_{fail_id}").click().run()
    assert not at.exception
    if safe:                                                             # M8.0 cờ bật: mới hỏi (giá trên nút Có), chưa đưa lại hàng chờ
        assert at.session_state["_states"][-1] != "pending"
        assert "USD" in at.button(key=f"cr_rerun_{fail_id}_yes").label or "chưa có giá" in at.button(key=f"cr_rerun_{fail_id}_yes").label
        at.button(key=f"cr_rerun_{fail_id}_yes").click().run()
        assert not at.exception
    assert at.session_state["_states"][-1] == "pending"                     # chỉ khi NGƯỜI bấm nút có giá


def test_failure_finding_whose_changes_are_gone_offers_fixed_not_a_priced_rerun(db):
    # rà C-FIX4 THẤP: lần lỗi đã bị dọn (KEEP_DAYS) → không còn gì để rà: không nút "Rà lại" báo giá giả; "✓ Đã sửa" (0 USD) đóng được
    conn = connect(db)
    conn.execute("DELETE FROM change_events WHERE state='failed'")
    conn.commit()
    fail_id = conn.execute("SELECT id FROM change_findings WHERE source=?", (CR.FAIL_SOURCE,)).fetchone()[0]
    conn.close()
    at = AppTest.from_function(_page, args=(db,)).run()
    assert f"cr_rerun_{fail_id}" not in _keys(at, "cr_rerun_")
    at.button(key=f"cr_ok_{fail_id}").click().run()
    assert not at.exception
    assert at.session_state["_open"][0] == "resolved"


def test_fixed_on_a_failure_finding_that_gained_changes_meanwhile_says_why(db):
    # C-FIX5: trang vẽ lúc lần lỗi đã bị dọn (hiện "✓ Đã sửa"), phiên khác vừa thêm lần lỗi mới cho shot → bấm ✓ thì close() từ chối:
    # trang nói lý do (st.error), không traceback
    conn = connect(db)
    conn.execute("DELETE FROM change_events WHERE state='failed'")
    conn.commit()
    fail_id = conn.execute("SELECT id FROM change_findings WHERE source=?", (CR.FAIL_SOURCE,)).fetchone()[0]
    conn.close()
    at = AppTest.from_function(_page, args=(db,)).run()
    assert f"cr_ok_{fail_id}" in _keys(at, "cr_ok_")
    with mock.patch.object(CR, "close", side_effect=ValueError(CR.FIXED_ON_FAIL)):
        at.button(key=f"cr_ok_{fail_id}").click().run()
    assert not at.exception
    assert any("Rà lại" in e.value for e in at.error)
