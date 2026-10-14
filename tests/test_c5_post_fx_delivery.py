"""C5a (Đ13v1 mục 2 + 4, gộp vào C5 14/10): post_fx áp trên độ dài THẬT của clip trước khung giữ cuối (`end_hold`), và bản dựng bị coi
là cũ khi `post_fx` của shot hoặc cờ `post_fx_render` đổi (cờ tắt / không shot nào có post_fx → khóa dựng như trước)."""
import json
import os
import subprocess
from unittest import mock

import pytest

from core import delivery, final_cut, post_fx
from core import ffmpeg_studio as f
from core.db import connect
from core.pipeline import Pipeline

SPEC = {"loai": "nhap_nhay", "vi_tri": "cuoi", "thoi_luong_s": 0.5, "cuong_do": 0.8}


def _project(tmp_path, last_seconds=2, spec=SPEC):
    ffmpeg = f.find_ffmpeg()
    p = Pipeline(connect(":memory:"))
    pid = p.create_project("c5 post fx")
    for idx, secs in ((1, 2), (2, last_seconds)):
        sid = p.create_scene(pid, idx, f"s{idx}")
        if idx == 2 and spec is not None:
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"post_fx": spec}), sid))
        path = final_cut.clip_path(str(tmp_path), pid, idx)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        subprocess.run([ffmpeg, "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"testsrc=d={secs}:s=128x72:r=24", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", path], check=True)
    p.conn.commit()
    return p, pid


@pytest.fixture
def ffmpeg_ok():
    try:
        f.find_ffmpeg()
    except f.FFmpegNotFound:
        pytest.skip("ffmpeg not installed")


def _render(p, pid, tmp_path, flags):
    with mock.patch("core.features.on", side_effect=lambda name: name in flags), \
            mock.patch("core.formats.spec", return_value={"render": None}), mock.patch("core.delivery._loudness", return_value={}):
        return delivery.render(p, pid, str(tmp_path), music_path=None, settings=delivery.get_settings(p, pid))


def test_post_fx_runs_on_the_clip_before_the_end_hold(tmp_path, ffmpeg_ok):
    p, pid = _project(tmp_path, last_seconds=1)
    order, seen = [], {}
    real_apply, real_hold = post_fx.apply, delivery._hold_end

    def apply(p_, rows, paths, durations, work_dir):
        order.append("post_fx")
        seen["last"] = durations[-1]
        return real_apply(p_, rows, paths, durations, work_dir)

    def hold(paths, durations, work_dir):
        order.append("end_hold")
        seen["held_from"] = paths[-1]
        return real_hold(paths, durations, work_dir)

    with mock.patch.object(post_fx, "apply", side_effect=apply), mock.patch.object(delivery, "_hold_end", side_effect=hold):
        res = _render(p, pid, tmp_path, {"post_fx_render", "end_hold"})
    assert order == ["post_fx", "end_hold"]
    assert abs(seen["last"] - 1.0) < 0.1                      # "cuoi" = the last 0,5 s of the clip itself, not of the held frame
    assert "post_fx_" in os.path.basename(seen["held_from"])  # the hold freezes the effected clip's last frame
    man = json.loads(p.conn.execute("SELECT manifest FROM outputs WHERE id=?", (res["output_id"],)).fetchone()["manifest"])
    assert [r["muc"] for r in man["post_fx"]] == ["xanh"]
    assert abs(res["seconds"] - (2 + delivery.END_HOLD_S)) < 0.15


def test_render_key_unchanged_when_flag_off_or_no_shot_has_post_fx(tmp_path, ffmpeg_ok):
    p, pid = _project(tmp_path, spec=None)
    settings = delivery.get_settings(p, pid)
    with mock.patch("core.features.on", side_effect=lambda name: name == "post_fx_render"):
        self_key = delivery._render_hash(p, pid, settings)
    assert self_key == delivery.render_hash(settings)          # nothing asks for an effect: the old key
    p.conn.execute("UPDATE scenes SET data=? WHERE project_id=? AND idx=2", (json.dumps({"post_fx": SPEC}), pid))
    with mock.patch("core.features.on", return_value=False):
        assert delivery._render_hash(p, pid, settings) == delivery.render_hash(settings)   # flag off: the old key


def test_changed_post_fx_or_flag_makes_the_cut_stale(tmp_path, ffmpeg_ok):
    p, pid = _project(tmp_path)
    _render(p, pid, tmp_path, {"post_fx_render"})

    def state(flags):
        with mock.patch("core.features.on", side_effect=lambda name: name in flags):
            return delivery.status(p, pid, str(tmp_path))["final"]

    assert state({"post_fx_render"})["state"] == "fresh"
    p.conn.execute("UPDATE scenes SET data=? WHERE project_id=? AND idx=2", (json.dumps({"post_fx": {**SPEC, "cuong_do": 0.3}}), pid))
    p.conn.commit()
    got = state({"post_fx_render"})
    assert got["state"] == "stale" and "thiết lập dựng đã đổi" in got["reasons"]
    p.conn.execute("UPDATE scenes SET data=? WHERE project_id=? AND idx=2", (json.dumps({"post_fx": SPEC}), pid))
    p.conn.commit()
    assert state({"post_fx_render"})["state"] == "fresh"
    assert state(set())["state"] == "stale"                    # the flag went off: the cut still carries the effect
