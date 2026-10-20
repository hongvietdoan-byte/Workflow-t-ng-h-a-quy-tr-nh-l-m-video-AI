"""DP3 — V3.1 M4.4 (cloud-C 20/10): Final QC đoạn ĐEN (ffmpeg blackdetect) + ĐỨNG HÌNH (freezedetect) trên bản dựng cuối, mức REVIEW
(level "warn" — không chặn xuất, G2-5). Cờ `final_black_freeze` TẮT = như cũ. Đứng hình > 1,5 s (khớp M4.2) — quyết định 11/10 "video
không được đơ". Video tổng hợp do ffmpeg tạo trong test (lavfi testsrc / color), 0 USD."""
import os
import shutil
import subprocess
from unittest import mock

import pytest

from core import final_qc as F

FFMPEG = shutil.which("ffmpeg")
pytestmark = pytest.mark.skipif(FFMPEG is None, reason="cần ffmpeg")
ON = mock.patch.dict(os.environ, {"FEATURE_FINAL_BLACK_FREEZE": "1"})
OFF = mock.patch.dict(os.environ, {"FEATURE_FINAL_BLACK_FREEZE": ""})
SIZE = "160x120"


def _make(path, parts):
    """parts: [("move", s) | ("black", s) | ("still", s)] nối liền thành một mp4 24 fps."""
    args, n = [FFMPEG, "-y", "-v", "error"], 0
    for kind, sec in parts:
        src = {"move": f"testsrc=d={sec}:s={SIZE}:r=24", "black": f"color=c=black:s={SIZE}:d={sec}:r=24",
               "still": f"color=c=0x3366aa:s={SIZE}:d={sec}:r=24"}[kind]
        args += ["-f", "lavfi", "-i", src]
        n += 1
    args += ["-filter_complex", "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]", "-map", "[v]",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(args, check=True)
    return str(path)


TIMELINE = [{"idx": 1, "seconds": 2.0}, {"idx": 2, "seconds": 2.0}, {"idx": 3, "seconds": 2.0}]


def test_flag_is_off_by_default():
    from core import features
    assert F.BLACK_FREEZE_FLAG in features.FEATURES
    with OFF:
        assert not features.on(F.BLACK_FREEZE_FLAG)


def test_black_gap_is_found_with_its_shot(tmp_path):
    v = _make(tmp_path / "b.mp4", [("move", 2), ("black", 1), ("move", 3)])
    issues = F.check_black_freeze(v, TIMELINE)
    black = [i for i in issues if i["code"] == "black_frame"]
    assert len(black) == 1 and black[0]["level"] == "warn"
    assert 1.8 <= black[0]["at"] <= 2.2 and "shot 2" in black[0]["msg"]


def test_still_over_one_and_a_half_seconds_is_found(tmp_path):
    v = _make(tmp_path / "s.mp4", [("move", 2), ("still", 2), ("move", 2)])
    freeze = [i for i in F.check_black_freeze(v, TIMELINE) if i["code"] == "freeze_frame"]
    assert len(freeze) == 1 and freeze[0]["level"] == "warn" and 1.8 <= freeze[0]["at"] <= 2.2


def test_short_still_and_clean_cut_say_nothing(tmp_path):
    assert F.check_black_freeze(_make(tmp_path / "c.mp4", [("move", 5)]), TIMELINE) == []
    assert [i for i in F.check_black_freeze(_make(tmp_path / "t.mp4", [("move", 2), ("still", 1), ("move", 2)]), TIMELINE)
            if i["code"] == "freeze_frame"] == []


def test_fade_to_black_at_the_very_end_is_not_a_gap(tmp_path):
    v = _make(tmp_path / "e.mp4", [("move", 4), ("black", 1)])
    assert [i for i in F.check_black_freeze(v, TIMELINE) if i["code"] == "black_frame"] == []


def test_unreadable_video_is_said_not_passed(tmp_path):
    bad = tmp_path / "x.mp4"
    bad.write_bytes(b"not a video")
    issues = F.check_black_freeze(str(bad), TIMELINE)
    assert [i["code"] for i in issues] == ["black_freeze_unmeasured"] and issues[0]["level"] == "warn"


def test_run_only_with_the_flag(tmp_path):
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect(":memory:"))
    pid = p.create_project("dp3")
    v = _make(tmp_path / "f.mp4", [("move", 2), ("black", 1), ("move", 2)])
    fin = {"path": v, "manifest": '{"timeline": [{"idx": 1, "seconds": 2.0}, {"idx": 2, "seconds": 3.0}]}'}
    with mock.patch("core.lineage.latest_output", side_effect=lambda conn, pid_, kind: fin if kind == "final" else None), \
         mock.patch.object(F, "check_silence", return_value=[]):
        with OFF:
            off = F.run(p, pid, str(tmp_path))
        with ON:
            on = F.run(p, pid, str(tmp_path))
    assert "black_frame" not in [i["code"] for i in off["issues"]]
    assert "black_frame" in [i["code"] for i in on["issues"]] and on["blocks"] == off["blocks"]   # REVIEW, không thêm chặn
