"""V3.1 M2.5 (C-M25B): người SỬA TAY motion prompt (Dashboard Bước 3 / Storyboard Bước 1, "↩ dùng lại prompt cũ") → trường `motion_prompt` của
shot = USER_LOCKED (+ provenance người + revision) — CHỈ khi cờ `field_guard` bật; cờ TẮT = byte giống, không ghi gì. AI / tự động ghi đè sau
đó → shadow chỉ ghi diag field_conflict (giá trị vẫn ghi như hôm nay — chặn thật = enforce C3-6), khóa của người giữ nguyên. CSDL tạm, 0 USD."""
import json
import os
import pathlib
from unittest import mock

import pytest

from core import llm_io, write_guard as G
from core.db import connect
from core.pipeline import Pipeline

ROOT = pathlib.Path(__file__).resolve().parent.parent
ON = mock.patch.dict(os.environ, {"FEATURE_FIELD_GUARD": "1"})
OFF = mock.patch.dict(os.environ, {"FEATURE_FIELD_GUARD": ""})
HUMAN = G.actor("human", "a@b.c")
AI = G.actor("ai", "director_motion")


@pytest.fixture
def shot(tmp_path):
    p = Pipeline(connect(str(tmp_path / "m.sqlite")))
    pid = p.create_project("m25b")
    sid = p.create_scene(pid, 1, "S1")
    img = p.create_job(sid)
    p.start(img)
    p.succeed(img)
    p.approve(img)
    llm_io.store_motion_prompts(p, pid, {"scenes": [{"idx": 1, "motion_prompt": "Director viết"}]})
    return p, pid, sid


def _save(p, pid, text, who=None):
    llm_io.store_motion_prompts(p, pid, {"scenes": [{"idx": 1, "motion_prompt": text}]}, actor=who)


def _data(p, sid):
    return json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()[0] or "{}")


def _mp(p, sid):
    return p.conn.execute("SELECT motion_prompt FROM motion_prompts WHERE scene_id=?", (sid,)).fetchone()[0]


def test_flag_off_hand_edit_writes_no_lock(shot):
    p, pid, sid = shot
    with OFF:
        _save(p, pid, "người sửa", HUMAN)
    got = _data(p, sid)
    with OFF:                                                                   # cùng lần lưu không actor (đường cũ) → dữ liệu như nhau
        _save(p, pid, "người sửa 2")
        _save(p, pid, "người sửa")
    old_way = _data(p, sid)
    got.pop("formula_check", None), old_way.pop("formula_check", None)          # sha kiểm công thức đóng dấu mỗi lần lưu (đã có)
    assert got == old_way and not {"_field_state", "_field_prov", "_rev"} & set(got)
    assert _mp(p, sid) == "người sửa"


def test_hand_edit_locks_with_provenance_and_revision(shot):
    p, pid, sid = shot
    with ON:
        _save(p, pid, "người sửa", HUMAN)
    d = _data(p, sid)
    assert G.state(d, "motion_prompt") == G.USER_LOCKED
    assert d["_field_prov"]["motion_prompt"]["by"] == "human:a@b.c" and d["_field_prov"]["motion_prompt"]["at"]
    assert d["_rev"] == 1


def test_same_text_is_not_a_new_edit(shot):
    p, pid, sid = shot
    with ON:
        _save(p, pid, "Director viết", HUMAN)
    assert G.state(_data(p, sid), "motion_prompt") == G.AUTO and "_rev" not in _data(p, sid)


def test_ai_overwrite_after_hand_edit_is_reported_and_lock_kept(shot):
    p, pid, sid = shot
    with ON:
        _save(p, pid, "người sửa", HUMAN)
        _save(p, pid, "AI viết lại", AI)
    rows = p.conn.execute("SELECT message FROM diag_events WHERE code='field_conflict'").fetchall()
    assert rows and "motion_prompt" in rows[0][0]
    assert _mp(p, sid) == "AI viết lại"                                         # shadow: vẫn ghi như hôm nay (chặn = C3-6)
    assert G.state(_data(p, sid), "motion_prompt") == G.USER_LOCKED              # khóa người giữ nguyên


def test_ai_save_never_locks(shot):
    p, pid, sid = shot
    with ON:
        _save(p, pid, "AI viết", AI)
        _save(p, pid, "AI viết nữa")                                             # không actor (đường cũ): không khóa
    assert G.state(_data(p, sid), "motion_prompt") == G.AUTO


def test_revert_of_a_motion_prompt_is_a_hand_choice(shot):
    from core import prompt_rewrite
    p, _, sid = shot
    with ON:
        prompt_rewrite._set_prompt(p.conn, sid, "video", "bản cũ người chọn", actor=HUMAN)
    assert G.state(_data(p, sid), "motion_prompt") == G.USER_LOCKED and _mp(p, sid) == "bản cũ người chọn"


def test_lock_is_a_noop_when_off_and_never_raises(shot):
    p, _, sid = shot
    with OFF:
        assert G.lock(p.conn, sid, "motion_prompt", HUMAN) is None
    with ON, mock.patch.object(G, "_load", side_effect=RuntimeError("x")):
        assert G.lock(p.conn, sid, "motion_prompt", HUMAN) is None
    with ON:
        assert G.lock(p.conn, sid, "motion_prompt", AI) is None                  # chỉ người khóa


@pytest.mark.parametrize("path,count", [("dashboard/steps/step3.py", 2), ("dashboard/steps/step1.py", 1)])
def test_dashboard_hand_edits_pass_a_human_actor(path, count):
    src = (ROOT / path).read_text(encoding="utf-8")
    assert src.count('actor=write_guard.actor("human"') >= count


def test_pasted_claude_json_is_ai_not_a_hand_edit():
    src = (ROOT / "dashboard/steps/step3.py").read_text(encoding="utf-8")
    assert 'llm_io.store_motion_prompts(p, pid, raw, actor=write_guard.actor("ai", "claude_paste"))' in src
