"""V3.1 M1.3 (G36 — docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md): pausing a project did not stop a job already being prepared —
paused 03:42:31, job 1075 sent to Kling 03:42:41; the runner only checked `paused` at the start of a pass (and after a first send).
Cờ pause_before_submit: `paused` is read again right before provider.submit (inside SPEND_LOCK), for every job — a plain one, a retry
and a retry switched to another model (Seedance → Kling). Paused → the job stays queued with its reason, nothing is sent, nothing lost.
Không API: provider giả."""
import json
import os
from unittest import mock

from core import runner as R
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockImageProvider, MockVideoProvider, RISK_CONTROL, ProviderError
from core.runner import ImageRunner, VideoRunner

ON = {"FEATURE_PAUSE_BEFORE_SUBMIT": "1"}
OFF = {"FEATURE_PAUSE_BEFORE_SUBMIT": "0"}


def _setup(tmp_path, n=1):
    p = Pipeline(connect(str(tmp_path / "m.sqlite")))
    pid = p.create_project("#31 thử")
    jobs = []
    for i in range(1, n + 1):
        sid = p.create_scene(pid, i, f"S{i}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": f"a hero on a rooftop {i}"}), sid))
        p.conn.commit()
        jobs.append(p.create_job(sid, "image_gen"))
    return p, pid, jobs


def _pause_while_preparing(runner, p, pid):
    """The person presses ⏸ while the runner builds the request (after the start-of-pass check)."""
    orig = type(runner)._submit_args

    def args(self, job):
        out = orig(self, job)
        other = connect(p.conn.execute("PRAGMA database_list").fetchone()["file"])   # pressed in another process (the Dashboard)
        other.execute("UPDATE projects SET paused=1 WHERE id=?", (pid,))
        other.commit()
        return out
    return mock.patch.object(type(runner), "_submit_args", args)


class Counting(MockImageProvider):
    def __init__(self):
        super().__init__()
        self.sent = 0

    def submit(self, *a, **k):
        self.sent += 1
        return super().submit(*a, **k)


def test_flag_off_pause_during_preparation_still_sends(tmp_path):
    """ĐỎ khi tắt cờ = hành vi cũ (G36 như trên #31): bấm tạm dừng lúc đang chuẩn bị → job vẫn gửi."""
    p, pid, (jid,) = _setup(tmp_path)
    r = ImageRunner(p, Counting(), str(tmp_path / "data"))
    with mock.patch.dict(os.environ, OFF), _pause_while_preparing(r, p, pid):
        r.submit_pending(pid)
    assert r.provider.sent == 1


def test_pause_during_preparation_sends_nothing_and_keeps_the_job(tmp_path):
    p, pid, jobs = _setup(tmp_path, n=2)
    r = ImageRunner(p, Counting(), str(tmp_path / "data"))
    with mock.patch.dict(os.environ, ON), _pause_while_preparing(r, p, pid):
        assert r.submit_pending(pid) == 0
    assert r.provider.sent == 0
    assert [p.job(j)["state"] for j in jobs] == ["queued", "queued"]
    assert not p.job(jobs[0])["external_id"]
    assert "tạm dừng" in R.wait_reason(jobs[0])
    assert p.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='paused_before_submit'").fetchone()[0] == 1
    p.conn.execute("UPDATE projects SET paused=0 WHERE id=?", (pid,))
    p.conn.commit()
    with mock.patch.dict(os.environ, ON):
        assert r.submit_pending(pid) == 2                         # unpaused: sent as usual, nothing lost
    assert r.provider.sent == 2


def test_pause_after_a_first_send_stops_the_next_one_already_in_preparation(tmp_path):
    p, pid, jobs = _setup(tmp_path, n=2)
    r = ImageRunner(p, Counting(), str(tmp_path / "data"))
    orig = ImageRunner._submit_args
    seen = []

    def args(self, job):
        seen.append(job["id"])
        if len(seen) == 2:                                        # pressed while the SECOND job is being prepared
            p.conn.execute("UPDATE projects SET paused=1 WHERE id=?", (pid,))
            p.conn.commit()
        return orig(self, job)
    with mock.patch.dict(os.environ, ON), mock.patch.object(ImageRunner, "_submit_args", args):
        assert r.submit_pending(pid) == 1
    assert r.provider.sent == 1 and p.job(jobs[1])["state"] == "queued"


def test_pause_stops_a_retry_job(tmp_path):
    p, pid, (jid,) = _setup(tmp_path)
    r = ImageRunner(p, Counting(), str(tmp_path / "data"))
    r.submit_pending(pid)
    p.fail(jid, "server_error: temporary")
    new = p.retry(jid, "thử lại sau lỗi tạm")
    with mock.patch.dict(os.environ, ON), _pause_while_preparing(r, p, pid):
        assert r.submit_pending(pid) == 0
    assert r.provider.sent == 1 and p.job(new)["state"] == "queued"


# ---- video: a refusal switched to another model (Seedance → Kling), then paused while the new try is prepared ---------------------

def _video_scene(p, pid, idx=1):
    from core.llm_io import approve_motion_prompt, store_motion_prompts
    scene = p.create_scene(pid, idx, f"S{idx}")
    img = p.create_job(scene)
    p.start(img)
    p.succeed(img)
    p.approve(img)
    store_motion_prompts(p, pid, {"scenes": [{"idx": idx, "motion_prompt": "slow push-in"}]})
    approve_motion_prompt(p, scene)
    return scene


class RefusedOnce(MockVideoProvider):
    def __init__(self):
        super().__init__()
        self.sent = []

    def submit(self, *a, **k):
        self.sent.append(k.get("model") if "model" in k else (a[4] if len(a) > 4 else None))
        if len(self.sent) == 1:
            raise ProviderError("Failure to pass the risk control system (real person)", code=RISK_CONTROL)
        return super().submit(*a, **k)


def test_pause_stops_the_model_switched_retry(tmp_path):
    p = Pipeline(connect(str(tmp_path / "v.sqlite")))
    pid = p.create_project("#31 video", max_retry=3)
    vid = p.create_job(_video_scene(p, pid), "video_gen")
    r = VideoRunner(p, RefusedOnce(), str(tmp_path / "data"))
    switched = []
    with mock.patch.object(VideoRunner, "_record_provider_failure", lambda self, job, code, msg: switched.append(code) or True):
        r.submit_pending(pid)                                     # refused → the new try is queued (model switched)
    assert switched == [RISK_CONTROL] and len(r.provider.sent) == 1
    retry = p.conn.execute("SELECT id FROM jobs WHERE parent_job_id=? AND state='queued'", (vid,)).fetchone()
    assert retry is not None
    with mock.patch.dict(os.environ, ON), _pause_while_preparing(r, p, pid):
        r.submit_pending(pid)
    assert len(r.provider.sent) == 1                              # 0 sends of the retry while paused
    assert p.job(retry["id"])["state"] == "queued"
