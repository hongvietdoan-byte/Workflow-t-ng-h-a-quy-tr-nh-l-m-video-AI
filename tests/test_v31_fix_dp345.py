"""C-FIX-DP345 (cloud-D 21/10) — sửa rà DP3 / DP4 / DP5 (cờ giữ TẮT).
(1) VỪA final_qc.check_black_freeze: đứng hình CỐ Ý của bản dựng (giữ khung cuối `end_hold` delivery.END_HOLD_S, popup cuối giữ khung,
    người sửa kéo dài shot = editor_fit "hold") không báo freeze_frame; phần đứng ngoài đoạn cố ý > 1,5 s vẫn báo. THẤP: một lượt ffmpeg
    cho blackdetect + freezedetect, có timeout (quá giờ = "không đo được", không treo).
(2) THẤP qc_evidence: QC-A4-BLACK_FRAME / FREEZE_FRAME trần REVIEW (G2-5: không chặn xuất) — validate báo mức vượt trần của mã.
(3) THẤP pipeline: repair_router TẮT → không gọi observe (không đọc auto_limit / không dựng danh sách mã)."""
import json
import os
import shutil
import subprocess
from unittest import mock

import pytest

from core import final_qc as F
from core import qc_evidence as E
from tests.test_v31_dp3_final_black_freeze import _make

FFMPEG = shutil.which("ffmpeg")
needs_ffmpeg = pytest.mark.skipif(FFMPEG is None, reason="cần ffmpeg")
SHA = "a" * 64


def _freeze(issues):
    return [i for i in issues if i["code"] == "freeze_frame"]


# ---- (1) đứng hình cố ý -----------------------------------------------------------------------------------------------------
@needs_ffmpeg
def test_end_hold_of_a_short_last_shot_is_not_a_freeze(tmp_path):
    """Shot cuối 0,8 s + end_hold → 2,5 s: 1,7 s khung cuối giữ có chủ đích (delivery._hold_end)."""
    v = _make(tmp_path / "e.mp4", [("move", 3), ("move", 0.8), ("still", 1.7)])
    timeline = [{"idx": 1, "seconds": 3.0}, {"idx": 2, "seconds": 2.5}]
    assert _freeze(F.check_black_freeze(v, timeline)), "không có manifest: vẫn là đứng hình (như DP3)"
    assert _freeze(F.check_black_freeze(v, timeline, {"end_hold": {"held_s": 1.7}})) == []


@needs_ffmpeg
def test_end_popup_hold_is_not_a_freeze(tmp_path):
    v = _make(tmp_path / "p.mp4", [("move", 3), ("still", 2.0)])
    timeline = [{"idx": 1, "seconds": 3.0}]                       # popup giữ khung cuối 2 s SAU timeline (end_popup.apply, hold)
    assert _freeze(F.check_black_freeze(v, timeline, {"end_popup": {"held_s": 2.0, "start_s": 3.0, "seconds": 2.0}})) == []


@needs_ffmpeg
def test_editor_fit_hold_mid_film_is_not_a_freeze(tmp_path):
    v = _make(tmp_path / "f.mp4", [("move", 2), ("still", 2), ("move", 2)])
    timeline = [{"idx": 1, "seconds": 4.0}, {"idx": 2, "seconds": 2.0}]
    fit = [{"idx": 1, "from_s": 2.0, "to_s": 4.0, "how": "hold", "path": "x"}]
    assert _freeze(F.check_black_freeze(v, timeline, {"editor_fit": fit})) == []


@needs_ffmpeg
def test_a_still_longer_than_the_hold_is_still_said(tmp_path):
    """Clip tự đứng 2 s rồi mới tới 1 s giữ cố ý: phần không cố ý (2 s) > 1,5 s → vẫn báo."""
    v = _make(tmp_path / "l.mp4", [("move", 2), ("still", 3)])
    timeline = [{"idx": 1, "seconds": 5.0}]
    got = _freeze(F.check_black_freeze(v, timeline, {"end_hold": {"held_s": 1.0}}))
    assert got and "cố ý" in got[0]["msg"]


def test_one_ffmpeg_pass_with_a_timeout():
    calls = []

    def fake_run(cmd, **kw):
        calls.append((cmd, kw))
        return subprocess.CompletedProcess(cmd, 0, "", "black_start:1 black_end:2\nlavfi.freezedetect.freeze_start: 3\n"
                                                         "lavfi.freezedetect.freeze_end: 5\n")
    with mock.patch.object(F.subprocess, "run", side_effect=fake_run), mock.patch.object(F.ffmpeg_studio, "find_ffmpeg", return_value="ff"), \
            mock.patch.object(F.ffmpeg_studio, "probe_duration", return_value=6.0):
        spans = F.black_freeze_spans("v.mp4")
    assert len(calls) == 1 and "blackdetect" in " ".join(calls[0][0]) and "freezedetect" in " ".join(calls[0][0])
    assert calls[0][1].get("timeout")
    assert spans == {"black": [(1.0, 2.0)], "freeze": [(3.0, 5.0)]}


def test_a_hung_ffmpeg_is_unmeasured_not_stuck():
    with mock.patch.object(F.subprocess, "run", side_effect=subprocess.TimeoutExpired("ff", 1)), \
            mock.patch.object(F.ffmpeg_studio, "find_ffmpeg", return_value="ff"):
        issues = F.check_black_freeze("v.mp4", [])
    assert [i["code"] for i in issues] == ["black_freeze_unmeasured"]


def test_run_passes_the_manifest(tmp_path):
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect(":memory:"))
    pid = p.create_project("fix-dp345")
    v = tmp_path / "f.mp4"
    v.write_bytes(b"x")
    man = {"timeline": [{"idx": 1, "seconds": 2.5}], "end_hold": {"held_s": 1.7}}
    fin = {"path": str(v), "manifest": json.dumps(man)}
    with mock.patch("core.lineage.latest_output", side_effect=lambda conn, pid_, kind: fin if kind == "final" else None), \
            mock.patch.object(F, "check_silence", return_value=[]), mock.patch.object(F.ffmpeg_studio, "probe_duration", return_value=2.5), \
            mock.patch.object(F, "check_black_freeze", return_value=[]) as chk, \
            mock.patch.dict(os.environ, {"FEATURE_FINAL_BLACK_FREEZE": "1"}):
        F.run(p, pid, str(tmp_path))
    assert chk.call_args.args[2] == man or chk.call_args.kwargs.get("manifest") == man


# ---- (2) trần REVIEW --------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("code", ["QC-A4-BLACK_FRAME", "QC-A4-FREEZE_FRAME"])
def test_black_and_freeze_never_block(code):
    assert E.CODES[code][2] == "REVIEW"
    assert E.finding(code, "BLOCK", "segment", {"at": 2}, "x", "final:1", SHA, "x")["severity"] == "REVIEW"
    hand = E.finding(code, "REVIEW", "segment", {"at": 2}, "x", "final:1", SHA, "x")
    hand.update(severity="BLOCK", confidence_calibration={"benchmark_id": "m46-1", "precision": 0.99})
    assert any("trần" in p for p in E.validate(hand))


# ---- (3) repair_router TẮT không đọc gì -------------------------------------------------------------------------------------
def test_repair_router_off_is_not_called():
    import inspect
    from core import pipeline
    src = inspect.getsource(pipeline)
    i = src.index("repair_router.observe(")
    assert "repair_router.enabled()" in src[max(0, i - 400):i]
