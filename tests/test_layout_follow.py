"""Hộp thư 12/10 19:17 (#27 shot 15/17 giữ bố cục theo shot 18): cờ layout_from_follow — (1) ảnh shot giữ bố cục CHỜ ảnh shot nguồn đang
gen (gửi trước thì thiếu ảnh bố cục), (2) thử mẫu kéo theo shot nguồn, (3) shot nguồn vẽ lại + duyệt → ảnh giữ bố cục "⚠ cũ"; Tổ rà soát
rà ngược shot giữ bố cục. Cờ TẮT = y cũ. Không API."""
import json
import os
import tempfile
from unittest import mock

from core import change_review, layout_follow, lineage, pilot
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockImageProvider
from core.runner import ImageRunner

ON = {"FEATURE_LAYOUT_FROM_FOLLOW": "1"}
OFF = {"FEATURE_LAYOUT_FROM_FOLLOW": "0"}


def _project():
    p = Pipeline(connect(":memory:"))
    pid = p.create_project("p27")
    ids = []
    for i in (1, 2, 3):
        sid = p.create_scene(pid, i, f"shot {i}")
        d = {"image_prompt": f"shot {i}", "characters": []}
        if i == 1:
            d["continuity_from"] = 3                             # shot 1 keeps the layout of a LATER shot (as #27 15 → 18)
        p.conn.execute("UPDATE scenes SET state='ready', data=? WHERE id=?", (json.dumps(d), sid))
        ids.append(sid)
    p.conn.commit()
    return p, pid, ids


def _job(p, sid, state):
    j = p.create_job(sid, "image_gen")
    p.conn.execute("UPDATE jobs SET state=? WHERE id=?", (state, j))
    p.conn.commit()
    return j


def test_the_shot_waits_while_its_layout_shot_is_being_drawn():
    p, pid, ids = _project()
    data = json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (ids[0],)).fetchone()[0])
    assert layout_follow.wait_reason(p.conn, pid, data) is None           # shot 3 has no job: sent as before (+ warned by the runner)
    src = _job(p, ids[2], "queued")
    assert "chờ ảnh shot 3" in layout_follow.wait_reason(p.conn, pid, data)
    p.conn.execute("UPDATE jobs SET state='succeeded' WHERE id=?", (src,))
    p.conn.commit()
    assert layout_follow.wait_reason(p.conn, pid, data) is None           # a picture exists now: no wait


def test_runner_holds_it_only_with_the_flag():
    p, pid, ids = _project()
    me = _job(p, ids[0], "queued")
    _job(p, ids[2], "running")
    r = ImageRunner(p, MockImageProvider(), tempfile.mkdtemp())
    job = p.job(me)
    with mock.patch.dict(os.environ, ON):
        assert r._wait(job) is True
    with mock.patch.dict(os.environ, OFF):
        assert r._wait(job) is False


def test_pilot_draws_the_layout_shot_too():
    p, pid, ids = _project()
    with mock.patch.dict(os.environ, ON):
        assert pilot.anchors_needed(p, pid, [ids[0]]) == [ids[2]]
        assert pilot.anchors_needed(p, pid, [ids[0], ids[2]]) == []
    with mock.patch.dict(os.environ, OFF):
        assert pilot.anchors_needed(p, pid, [ids[0]]) == []


def test_redrawn_layout_shot_makes_the_follower_outdated():
    p, pid, ids = _project()
    old_src = _job(p, ids[2], "approved")
    pkg = {"refs": [{"role": "layout_from", "path": f"/x/{pid}/images/job_{old_src}.png"}]}
    mine = _job(p, ids[0], "approved")
    p.conn.execute("UPDATE jobs SET sent_package=?, input_hash=? WHERE id=?",
                   (json.dumps(pkg), lineage.current_image_hash(p.conn, pid, ids[0]), mine))
    p.conn.commit()
    with mock.patch.dict(os.environ, ON):
        assert not lineage.scan(p.conn, pid)[ids[0]]["image_stale"]
        new_src = _job(p, ids[2], "pending_review")                     # redrawn, not chosen yet: still the old one
        assert not lineage.scan(p.conn, pid)[ids[0]]["image_stale"]
        p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (new_src,))
        p.conn.commit()
        assert "shot 3" in lineage.scan(p.conn, pid)[ids[0]]["image_stale"]
    with mock.patch.dict(os.environ, OFF):
        assert not lineage.scan(p.conn, pid)[ids[0]]["image_stale"]


def test_no_package_on_record_raises_no_alarm():
    p, pid, ids = _project()
    _job(p, ids[2], "approved")
    mine = _job(p, ids[0], "approved")
    p.conn.execute("UPDATE jobs SET input_hash=? WHERE id=?", (lineage.current_image_hash(p.conn, pid, ids[0]), mine))
    p.conn.commit()
    _job(p, ids[2], "approved")
    with mock.patch.dict(os.environ, ON):
        assert not lineage.scan(p.conn, pid)[ids[0]]["image_stale"]


def test_change_review_checks_the_shots_keeping_its_layout():
    p, pid, ids = _project()
    ev = {"kind": "scene", "scene_id": ids[2]}
    with mock.patch.dict(os.environ, ON):
        assert ids[0] in change_review.affected_scenes(p.conn, ev)
    with mock.patch.dict(os.environ, OFF):
        assert ids[0] not in change_review.affected_scenes(p.conn, ev)
