"""C-T12 (cloud-C, 20/10): test còn thiếu của M1.2 / M1.3 (cờ poll_claim + pause_before_submit đang BẬT máy chính).
(1) đường VIDEO sau khi tải: tách clip nhóm / cắt độ dài shot không để người đọc thấy tệp dở ở tên cuối (core/safe_download);
(2) core/bg_poll.poll_all ở 2 TIẾN TRÌNH thật cùng hỏi một job → đúng 1 lần succeeded, 1 lần tải;
(3) khung cuối (core/end_frames) lúc dự án Tạm dừng → 0 lần gửi. Không API, không mạng: provider giả, ffmpeg giả, CSDL tạm."""
import json
import multiprocessing
import os
from types import SimpleNamespace
from unittest import mock

import pytest

from core import end_frames, seedance_refs, shots
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockImageProvider

HALF = b"HALF-WRITTEN"


def _fake_ffmpeg(seen, finals):
    """subprocess.run giả: ghi dở vào tệp ra (đối số cuối) rồi xem lúc đó tên CUỐI có đang chứa tệp dở không."""
    def run(cmd, **kw):
        out = cmd[-1]
        with open(out, "wb") as f:
            f.write(HALF)
        seen.append({"out": out, "half_at_final": [d for d in finals if os.path.exists(d) and open(d, "rb").read() == HALF]})
        with open(out, "ab") as f:
            f.write(b"-DONE")
        return SimpleNamespace(returncode=0, stderr="")
    return run


# ---- (1) đường video: tách clip nhóm + cắt độ dài ---------------------------------------------------------------------------------
def test_group_split_parts_never_appear_half_written(tmp_path):
    whole = tmp_path / "03_group.mp4"
    whole.write_bytes(b"WHOLE")
    finals = [str(tmp_path / "03.mp4"), str(tmp_path / "04.mp4")]
    seen = []
    with mock.patch.object(seedance_refs.subprocess, "run", _fake_ffmpeg(seen, finals)), \
         mock.patch("core.ffmpeg_studio.has_audio", return_value=False):
        out = seedance_refs._cut_parts(str(whole), [0.0, 2.0, 4.0], finals, "ffmpeg")
    assert out == finals
    assert [s["half_at_final"] for s in seen] == [[], []]               # không lúc nào tên cuối chứa tệp dở
    assert all(s["out"] not in finals and ".part-" in s["out"] for s in seen)
    assert [open(d, "rb").read() for d in finals] == [HALF + b"-DONE"] * 2
    assert not [n for n in os.listdir(tmp_path) if ".part-" in n]        # không để lại tệp tạm


def test_group_split_failure_copies_the_whole_clip_in_one_step(tmp_path):
    whole = tmp_path / "03_group.mp4"
    whole.write_bytes(b"WHOLE")
    dest = str(tmp_path / "03.mp4")
    with mock.patch.object(seedance_refs.subprocess, "run", return_value=SimpleNamespace(returncode=1, stderr="x")), \
         mock.patch("core.ffmpeg_studio.has_audio", return_value=False):
        seedance_refs._cut_parts(str(whole), [0.0, 2.0], [dest], "ffmpeg")
    assert open(dest, "rb").read() == b"WHOLE"
    assert not [n for n in os.listdir(tmp_path) if ".part-" in n]


def test_kling_multishot_split_parts_never_appear_half_written(tmp_path):
    path = tmp_path / "05.mp4"
    path.write_bytes(b"WHOLE")
    finals = [str(path), str(tmp_path / "06.mp4")]
    seen = []
    import subprocess
    with mock.patch.object(subprocess, "run", _fake_ffmpeg(seen, finals)), \
         mock.patch("core.ffmpeg_studio.find_ffmpeg", return_value="ffmpeg"), \
         mock.patch("core.ffmpeg_studio.has_audio", return_value=False), \
         mock.patch.object(shots, "group_parts", return_value=[(0.0, 2.0), (2.0, 2.0)]):
        shots.split_group_clip(str(path), [{}, {}], finals)
    assert [s["half_at_final"] for s in seen] == [[], []]
    assert all(s["out"] not in finals for s in seen)
    assert open(finals[1], "rb").read() == HALF + b"-DONE"


def test_trim_never_leaves_a_half_clip_at_the_shot_name(tmp_path):
    db = str(tmp_path / "m.sqlite")
    p = Pipeline(connect(db))
    pid = p.create_project("t12")
    sid = p.create_scene(pid, 1, "S1")
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_no": 1}), sid))
    p.conn.commit()
    clip = tmp_path / "01.mp4"
    clip.write_bytes(b"FULL")
    seen = []
    import subprocess
    with mock.patch.object(subprocess, "run", _fake_ffmpeg(seen, [str(clip)])), \
         mock.patch.object(shots, "planned_seconds", return_value=2.0), \
         mock.patch("core.ffmpeg_studio.probe_duration", return_value=5.0), \
         mock.patch("core.ffmpeg_studio.find_ffmpeg", return_value="ffmpeg"), \
         mock.patch("core.ffmpeg_studio.has_audio", return_value=False):
        assert shots.trim_clip(p, sid, str(clip), at=0.0) is True
    assert seen and seen[0]["half_at_final"] == [] and seen[0]["out"] != str(clip)
    assert clip.read_bytes() == HALF + b"-DONE"
    assert (tmp_path / "01_raw.mp4").read_bytes() == b"FULL"            # bản đầy đủ giữ như trước
    assert not [n for n in os.listdir(tmp_path) if ".part-" in n]


def test_trim_failure_puts_the_uncut_clip_back(tmp_path):
    db = str(tmp_path / "m.sqlite")
    p = Pipeline(connect(db))
    pid = p.create_project("t12")
    sid = p.create_scene(pid, 1, "S1")
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_no": 1}), sid))
    p.conn.commit()
    clip = tmp_path / "01.mp4"
    clip.write_bytes(b"FULL")
    import subprocess
    with mock.patch.object(subprocess, "run", return_value=SimpleNamespace(returncode=1, stderr="bad")), \
         mock.patch.object(shots, "planned_seconds", return_value=2.0), \
         mock.patch("core.ffmpeg_studio.probe_duration", return_value=5.0), \
         mock.patch("core.ffmpeg_studio.find_ffmpeg", return_value="ffmpeg"), \
         mock.patch("core.ffmpeg_studio.has_audio", return_value=False), pytest.raises(RuntimeError):
        shots.trim_clip(p, sid, str(clip), at=0.0)
    assert clip.read_bytes() == b"FULL"
    assert not [n for n in os.listdir(tmp_path) if ".part-" in n]


# ---- (2) bg_poll.poll_all ở 2 tiến trình thật ----------------------------------------------------------------------------------
class StatelessImages(MockImageProvider):
    """Tiến trình nào cũng thấy task đã xong (provider thật trả trạng thái từ máy chủ, không từ bộ nhớ tiến trình); tải chậm 0,6 s để
    hai tiến trình chồng nhau; mỗi lần tải ghi một dòng vào sổ chung."""

    def __init__(self, log=None):
        super().__init__()
        self.log = log

    def status(self, task_id):
        from core.providers import TaskStatus
        return TaskStatus("succeeded")

    def download(self, task_id, dest_path):
        import time
        with open(self.log, "a", encoding="utf-8") as f:
            f.write(f"{os.getpid()}\n")
        time.sleep(0.6)
        return super().download(task_id, dest_path)


def _poll_process(db, data, log, barrier):
    os.environ["FEATURE_POLL_CLAIM"] = "1"
    from core import bg_poll
    from core.runner import ImageRunner
    conn = connect(db)
    barrier.wait(timeout=30)
    bg_poll.poll_all(conn, lambda c, kind: ImageRunner(Pipeline(c), StatelessImages(log), data) if kind == "image" else None)
    conn.close()


@pytest.mark.slow
def test_two_real_processes_poll_one_job_once(tmp_path):
    db, data, log = str(tmp_path / "m.sqlite"), str(tmp_path / "data"), str(tmp_path / "downloads.log")
    p = Pipeline(connect(db))
    pid = p.create_project("t12")
    sid = p.create_scene(pid, 1, "S1")
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": "a hero"}), sid))
    p.conn.commit()
    jid = p.create_job(sid, "image_gen")
    from core.runner import ImageRunner
    with mock.patch.dict(os.environ, {"FEATURE_POLL_CLAIM": "1"}):
        ImageRunner(p, StatelessImages(log), data).submit_pending(pid)
    assert p.job(jid)["state"] == "running"
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    procs = [ctx.Process(target=_poll_process, args=(db, data, log, barrier)) for _ in range(2)]
    [x.start() for x in procs]
    [x.join(60) for x in procs]
    assert [x.exitcode for x in procs] == [0, 0]
    assert len(open(log, encoding="utf-8").read().split()) == 1          # một lần tải (lần kia thấy claim, bỏ qua)
    fresh = Pipeline(connect(db))
    assert fresh.job(jid)["state"] == "succeeded"
    assert fresh.conn.execute("SELECT COUNT(*) FROM job_events WHERE job_id=? AND to_state='succeeded'", (jid,)).fetchone()[0] == 1
    assert os.path.isfile(fresh.job(jid)["result_path"])


# ---- (3) khung cuối lúc dự án Tạm dừng -------------------------------------------------------------------------------------------
class _Counting(MockImageProvider):
    def __init__(self):
        super().__init__()
        self.sent = 0

    def submit(self, *a, **k):
        self.sent += 1
        return super().submit(*a, **k)


def _end_frame_project(tmp_path):
    from core import llm_runner
    from tests.test_end_frames import _shot_with_end_state
    from tests.test_v3 import _approve_all_images, kenta_project
    p, pid = kenta_project()
    llm_runner.run_director(p, pid, llm_runner.MockLlm())
    sid = _shot_with_end_state(p, pid)
    data = str(tmp_path)
    _approve_all_images(p, pid, data)
    assert sid in end_frames.queue(p, pid)
    return p, pid, data


@pytest.mark.parametrize("flag", ["1", "0"])
def test_paused_project_sends_no_end_frame(tmp_path, flag, monkeypatch):
    monkeypatch.setenv("FEATURE_SEEDANCE_REF_GROUPS", "0")      # C-FLAGTEST8: shot lẻ cần khung cuối — đường nhóm ref TẮT, không dựa mặc định
    p, pid, data = _end_frame_project(tmp_path)
    p.set_paused(pid, True)
    img = _Counting()
    with mock.patch.dict(os.environ, {"FEATURE_PAUSE_BEFORE_SUBMIT": flag}):
        end_frames.tick(p, pid, img, data)
    assert img.sent == 0
    rows = p.conn.execute("SELECT state, note FROM end_frames WHERE project_id=?", (pid,)).fetchall()
    assert rows and all(r["state"] == "queued" for r in rows)
    assert all("tạm dừng" in (r["note"] or "").lower() for r in rows)    # nói lý do, không im lặng


def test_pause_pressed_while_the_end_frame_is_being_prepared_sends_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_SEEDANCE_REF_GROUPS", "0")      # C-FLAGTEST8: như trên
    p, pid, data = _end_frame_project(tmp_path)
    img = _Counting()
    real = end_frames.prompt_for

    def pause_now(*a, **k):                    # người bấm ⏸ đúng lúc khung cuối đang dựng prompt / ảnh tham chiếu
        p.set_paused(pid, True)
        return real(*a, **k)
    with mock.patch.dict(os.environ, {"FEATURE_PAUSE_BEFORE_SUBMIT": "1"}), mock.patch.object(end_frames, "prompt_for", pause_now):
        end_frames.tick(p, pid, img, data)
    assert img.sent == 0
    p.set_paused(pid, False)                   # bỏ tạm dừng → lượt sau gửi bình thường (job không mất)
    with mock.patch.dict(os.environ, {"FEATURE_PAUSE_BEFORE_SUBMIT": "1"}):
        end_frames.tick(p, pid, img, data)
    assert img.sent >= 1
