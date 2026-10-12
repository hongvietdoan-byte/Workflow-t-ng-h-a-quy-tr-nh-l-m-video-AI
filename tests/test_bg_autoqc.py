"""Hộp thư 12/10 17:58 (#27 job 756, 762–771 nằm 'succeeded' ~1 giờ): QC tự động chỉ chạy khi mở trang dự án. Cờ bg_autoqc: vòng nền
tự bắt đầu kiểm tra — cùng luật với trang (không khi chạy tự động sở hữu dự án, ảnh không khi chế độ 'auto', không chạy trùng). Không API."""
import os
from unittest import mock

from core import autoqc, bg_poll
from core.db import connect
from core.pipeline import Pipeline

ON = {"FEATURE_BG_AUTOQC": "1"}


def _project(tmp_path, **cols):
    db = str(tmp_path / "m.sqlite")
    p = Pipeline(connect(db))
    pid = p.create_project("t")
    sid = p.create_scene(pid, 1, "s")
    jid = p.create_job(sid, "image_gen")
    p.conn.execute("UPDATE jobs SET state='succeeded' WHERE id=?", (jid,))
    for k, v in cols.items():
        p.conn.execute(f"UPDATE projects SET {k}=? WHERE id=?", (v, pid))
    p.conn.commit()
    return db, p.conn, pid


def _round(conn, db, env, video=False, image=None):
    started = []
    image = image or (lambda d, data, pid, *a, **k: started.append(("image", pid)) or True)
    with mock.patch.dict(os.environ, env), mock.patch.object(autoqc, "start", image), \
            mock.patch.object(autoqc, "start_video", lambda d, data, pid, *a, **k: video and (started.append(("video", pid)) or True)):
        out = bg_poll.autoqc_round(conn, db, "/tmp/data")
    return out, started


def _notes(conn, code):
    return conn.execute("SELECT COUNT(*) FROM diag_events WHERE code=?", (code,)).fetchone()[0]


def test_flag_off_starts_nothing(tmp_path):
    db, conn, pid = _project(tmp_path)
    assert _round(conn, db, {"FEATURE_BG_AUTOQC": "0"}) == ({}, [])


def test_flag_on_starts_the_picture_check_without_the_page(tmp_path):
    db, conn, pid = _project(tmp_path)
    out, started = _round(conn, db, ON)
    assert out == {pid: "image"} and started == [("image", pid)]


def test_same_rules_as_the_page(tmp_path):
    for i, cols in enumerate(({"autopilot_state": "running"}, {"autopilot_state": "queued"}, {"paused": 1}, {"archived": 1})):
        d = tmp_path / f"c{i}"
        d.mkdir()
        db, conn, pid = _project(d, **cols)
        assert _round(conn, db, ON)[1] == [], cols
    d = tmp_path / "auto"
    d.mkdir()
    db, conn, pid = _project(d, operating_mode="auto")
    assert _round(conn, db, ON)[1] == []                      # pictures: not in operating mode 'auto' (as the page)


def test_preset_experimental_never_turns_it_on(tmp_path):
    from core import features
    assert "bg_autoqc" in features.OPT_IN_ONLY


def test_waiting_run_is_checked_like_the_page(tmp_path):
    """Rà 12/10: a run WAITING at a gate does not check its redrawn pictures; the page checks them, so the loop does too."""
    db, conn, pid = _project(tmp_path, autopilot_state="waiting")
    assert _round(conn, db, ON)[1] == [("image", pid)]


def test_video_check_runs_in_auto_mode_too(tmp_path):
    db, conn, pid = _project(tmp_path, operating_mode="auto")
    conn.execute("UPDATE jobs SET type='video_gen'")
    conn.commit()
    out, started = _round(conn, db, ON, video=True)
    assert out == {pid: "video"} and started == [("video", pid)]


def test_same_pictures_are_not_restarted_forever(tmp_path):
    """Rà 12/10 (CAO): a check that leaves the same jobs 'succeeded' (bad Claude answer, scene not complete) is started at most twice,
    then said once; a new job starts it again."""
    db, conn, pid = _project(tmp_path)
    runs = [_round(conn, db, ON)[1] for _ in range(6)]
    assert [len(r) for r in runs] == [1, 1, 0, 0, 0, 0]
    assert _notes(conn, "bg_autoqc_stuck") == 1
    sid = conn.execute("SELECT id FROM scenes").fetchone()[0]
    jid = Pipeline(conn).create_job(sid, "image_gen")
    conn.execute("UPDATE jobs SET state='succeeded' WHERE id=?", (jid,))
    conn.commit()
    assert _round(conn, db, ON)[1] == [("image", pid)]


def test_a_failing_start_is_said_and_capped(tmp_path):
    db, conn, pid = _project(tmp_path)
    def boom(*a, **k):
        raise RuntimeError("hỏng")
    for _ in range(4):
        assert _round(conn, db, ON, image=boom)[0] == {}
    assert _notes(conn, "bg_autoqc_error") >= 1 and _notes(conn, "bg_autoqc_stuck") == 1


def test_round_once_runs_it_and_its_failure_keeps_the_round(tmp_path):
    db, conn, pid = _project(tmp_path)
    def boom(*a, **k):
        raise RuntimeError("x")
    with mock.patch.dict(os.environ, ON), mock.patch.object(bg_poll, "change_review_round", lambda *a: None), \
            mock.patch.object(bg_poll, "poll_all", lambda *a: {(pid, "poll"): 1}), mock.patch.object(bg_poll, "send_ready", lambda *a: {}), \
            mock.patch.object(bg_poll, "autoqc_round", lambda *a: {pid: "image"}):
        assert bg_poll.round_once(db, str(tmp_path)) == {(pid, "poll"): 1, (pid, "autoqc"): "image"}
    with mock.patch.dict(os.environ, ON), mock.patch.object(bg_poll, "change_review_round", lambda *a: None), \
            mock.patch.object(bg_poll, "poll_all", lambda *a: {(pid, "poll"): 1}), mock.patch.object(bg_poll, "send_ready", lambda *a: {}), \
            mock.patch.object(bg_poll, "autoqc_round", boom):
        assert bg_poll.round_once(db, str(tmp_path)) == {(pid, "poll"): 1}


def test_check_lock_is_held_across_processes(tmp_path):
    """Rà 12/10: a second Dashboard process (or a reloaded module) must not check the same project at the same time."""
    import subprocess, sys
    db = str(tmp_path / "m.sqlite")
    assert autoqc._claim(db, "image", 7)
    try:
        code = "import sys; from core import autoqc; sys.exit(0 if autoqc._claim(sys.argv[1], 'image', 7) else 3)"
        r = subprocess.run([sys.executable, "-c", code, db], cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        assert r.returncode == 3
        assert not autoqc._claim(db, "image", 7)          # same process, second claim
        assert autoqc._claim(db, "image", 8) and (autoqc._release(db, "image", 8) or True)
    finally:
        autoqc._release(db, "image", 7)
    assert autoqc._claim(db, "image", 7)
    autoqc._release(db, "image", 7)
