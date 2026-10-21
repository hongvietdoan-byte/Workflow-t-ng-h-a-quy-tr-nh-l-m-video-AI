"""Nhánh tích hợp M2 (C-M2-TICHHOP, 21/10) — sửa lỗi VỪA của 2 lượt rà chéo.
M21-1 (docs RA_CLOUD_RA_M21_M25): BYĐ sai kiểu (chuỗi / danh sách) trên main làm vỡ nơi đọc (AttributeError → QC dừng trước lượt VLM,
lock_exceptions lỗi); adapter byd_of() trả None → `or {}` nuốt IM LẶNG. Cờ byd_v2_levels TẮT → y hệt main (vẫn vỡ như cũ);
BẬT → BydTypeError (ValueError) mức REVIEW, mã byd_sai_kieu — nói ra, không im lặng (qc_observe._prepare bắt thành VÀNG)."""
import os
from unittest import mock

import pytest

from core import film_grammar, lock_exceptions, qc_observe, shot_intent

OFF = {"FEATURE_BYD_V2_LEVELS": ""}
ON = {"FEATURE_BYD_V2_LEVELS": "1"}
BAD = ("BOM", ["BOM_KEO"])


def _qc(data):
    return qc_observe.compile_checks(None, 24, 1, dict(data, characters=["GIRL"]), ["set_match"], profiles={})


CALLS = {
    "qc_observe": _qc,
    "lock_exceptions.for_shot": lock_exceptions.for_shot,
    "lock_exceptions.shot_label": lock_exceptions.shot_label,
    "film_grammar._exception": lambda d: film_grammar._exception(d, 1, "jump"),
}


@pytest.mark.parametrize("bad", BAD)
@pytest.mark.parametrize("name", sorted(CALLS))
def test_flag_off_wrong_type_breaks_like_main(name, bad):
    with mock.patch.dict(os.environ, OFF), pytest.raises(AttributeError):
        CALLS[name]({"byd": bad})


@pytest.mark.parametrize("bad", BAD)
@pytest.mark.parametrize("name", sorted(CALLS))
def test_flag_on_wrong_type_is_said_as_review(name, bad):
    with mock.patch.dict(os.environ, ON), pytest.raises(shot_intent.BydTypeError) as e:
        CALLS[name]({"byd": bad})
    assert e.value.code == "byd_sai_kieu" and e.value.level == "REVIEW" and "sai kiểu" in str(e.value)
    assert isinstance(e.value, ValueError)              # qc_observe._prepare bắt ValueError → VÀNG, không gọi VLM


@pytest.mark.parametrize("env", (OFF, ON))
@pytest.mark.parametrize("empty", (None, "", [], {}, 0))
def test_empty_or_missing_byd_reads_as_none(env, empty):
    with mock.patch.dict(os.environ, env):
        assert lock_exceptions.for_shot({"byd": empty}) == {}
        assert lock_exceptions.shot_label({"byd": empty, "shot_no": 4}) == 4
        assert film_grammar._exception({"byd": empty}, 1, "jump") is False


# ---- M25-1: shadow write guard không được commit hộ nơi gọi (nửa lô) ------------------------------------------------------------
def _three_shots(tmp_path):
    import json
    from core.db import connect
    from core.pipeline import Pipeline
    db = str(tmp_path / "m.sqlite")
    p = Pipeline(connect(db))
    pid = p.create_project("m25-1")
    sids = []
    for i in (1, 2, 3):
        sid = p.create_scene(pid, i, f"S{i}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"characters": ["KELLY"], "size": "MS"}), sid))
        if i < 3:                                         # shot 3 chưa có ảnh duyệt → store_motion_prompts ném SchemaError giữa lô
            img = p.create_job(sid)
            p.start(img)
            p.succeed(img)
            p.approve(img)
        sids.append(sid)
    p.conn.commit()
    from core import llm_io
    llm_io.store_motion_prompts(p, pid, {"scenes": [{"idx": 1, "motion_prompt": "cũ 1"}, {"idx": 2, "motion_prompt": "người viết 2"}]})
    d = json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (sids[1],)).fetchone()[0])
    d["_user_locked"] = ["motion_prompt"]
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), sids[1]))
    p.conn.commit()
    return p, pid, sids, db


@pytest.mark.parametrize("flag", ("", "1"))
def test_shadow_never_commits_half_a_batch(tmp_path, flag):
    import sqlite3
    from core import llm_io, write_guard
    from core.llm_io import SchemaError
    p, pid, sids, db = _three_shots(tmp_path)
    batch = {"scenes": [{"idx": i, "motion_prompt": f"AI {i}"} for i in (1, 2, 3)]}
    with mock.patch.dict(os.environ, {"FEATURE_FIELD_GUARD": flag}), pytest.raises(SchemaError):
        llm_io.store_motion_prompts(p, pid, batch, actor=write_guard.actor("ai", "director"))
    other = sqlite3.connect(db)
    seen = other.execute("SELECT motion_prompt FROM motion_prompts WHERE scene_id=?", (sids[0],)).fetchone()[0]
    other.close()
    assert seen == "cũ 1"                                  # kết nối khác không thấy nửa lô
    p.conn.rollback()
    assert p.conn.execute("SELECT motion_prompt FROM motion_prompts WHERE scene_id=?", (sids[0],)).fetchone()[0] == "cũ 1"
    if flag:                                               # điều lẽ ra đã chặn vẫn được nói — sau khi nơi gọi xong giao dịch
        with mock.patch.dict(os.environ, {"FEATURE_FIELD_GUARD": flag}):
            write_guard.flush(p.conn)
        assert p.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='field_conflict'").fetchone()[0] == 1


def test_shadow_diag_written_after_the_callers_commit(tmp_path):
    from core import llm_io, write_guard
    p, pid, sids, _ = _three_shots(tmp_path)
    with mock.patch.dict(os.environ, {"FEATURE_FIELD_GUARD": "1"}):
        llm_io.store_motion_prompts(p, pid, {"scenes": [{"idx": i, "motion_prompt": f"AI {i}"} for i in (1, 2)]},
                                    actor=write_guard.actor("ai", "director"))
    assert not p.conn.in_transaction
    assert p.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='field_conflict'").fetchone()[0] == 1


def test_lock_does_not_commit_the_callers_transaction(tmp_path):
    import sqlite3
    from core import write_guard
    p, pid, sids, db = _three_shots(tmp_path)
    p.conn.execute("UPDATE motion_prompts SET motion_prompt='đang sửa' WHERE scene_id=?", (sids[0],))
    with mock.patch.dict(os.environ, {"FEATURE_FIELD_GUARD": "1"}):
        write_guard.lock(p.conn, sids[0], "motion_prompt", write_guard.actor("human", "a@b.c"))
    other = sqlite3.connect(db)
    seen = other.execute("SELECT motion_prompt FROM motion_prompts WHERE scene_id=?", (sids[0],)).fetchone()[0]
    other.close()
    assert seen == "cũ 1" and p.conn.in_transaction
    p.conn.commit()
