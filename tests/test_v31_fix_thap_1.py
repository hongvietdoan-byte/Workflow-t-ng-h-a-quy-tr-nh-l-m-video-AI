"""C-FIX-THAP-1 (cloud-C 20/10): 6 mục THẤP sau rà gộp 20/10 (QC shadow M4.2/M4.3/M4.5/M3.5 + M1.6/M1.7). Mỗi mục test đỏ → xanh, cờ giữ TẮT.
0 USD, không mạng."""
import json
import os
from unittest import mock

import pytest

from core import code_version, continuity_shadow as C, cost, plate_layout_qc as Q, qc_scene

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")


# ---- (1) video_qc_shadow: một khung đầu, không giải mã cả clip; dùng lại motion_series của measure --------------------------------
def test_video_shadow_reads_one_frame_not_the_whole_clip(tmp_path):
    from core import clip_measure, video_qc_shadow as V
    path = str(tmp_path / "c.mp4")
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 24, (64, 48))
    for i in range(48):
        w.write(np.full((48, 64, 3), i * 5 % 255, np.uint8))
    w.release()
    with mock.patch.object(clip_measure, "frames", side_effect=AssertionError("giải mã cả clip")) as whole:
        f0 = V.first_frame(path)
    assert f0 is not None and f0.shape[1] == 640 and not whole.called


def test_motion_series_is_computed_once_for_measure_and_shadow(tmp_path):
    from core import clip_measure
    path = str(tmp_path / "c.mp4")
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 24, (64, 48))
    for i in range(30):
        w.write(np.roll(np.random.default_rng(1).integers(0, 255, (48, 64, 3), dtype=np.uint8), i, axis=1))
    w.release()
    real = clip_measure.frames
    with mock.patch.object(clip_measure, "frames", side_effect=real) as decode:
        a = clip_measure.motion_series(path)
        b = clip_measure.motion_series(path)
    assert a == b and decode.call_count == 1


# ---- (2) qc_scene: chỉ dò trường góc / shot / blocking ---------------------------------------------------------------------------
def _size_check(data):
    with mock.patch.dict(os.environ, {"FEATURE_QC_FALSE_ALARM_FIX": "1"}), mock.patch.object(qc_scene, "_blank", return_value=None), \
         mock.patch("core.text_placement.face_boxes", return_value=[(0.45, 0.30, 0.52, 0.38)]):
        return [o["code"] for o in qc_scene.check_frame("x.png", data, measure={})]


@pytest.mark.parametrize("field,words", [("image_prompt", "Kelly faces the camera, the sun behind her shoulders"),
                                         ("action", "Kelly rút súng sau lưng ra"), ("image_prompt", "Kelly faces us, a tower behind her"),
                                         ("action", "the sun behind her")])
def test_character_words_never_skip_the_size_check(field, words):   # C-FIX-THAP-2: trường nào cũng vậy — regex chỉ khớp chữ về MÁY
    assert "shot_size" in _size_check({"size": "MS", "characters": ["KELLY"], field: words})


@pytest.mark.parametrize("field,words", [("blocking", "camera behind the group, the backs of two cats in front"),
                                         ("image_prompt", "Low camera behind the group: the backs of two cats fill the foreground"),
                                         ("angle", "ots"), ("shot", "over-the-shoulder on Kelly"), ("blocking", "máy đặt SAU LƯNG Kelly")])
def test_camera_fields_still_skip(field, words):
    assert "shot_size" not in _size_check({"size": "MS", "characters": ["KELLY"], field: words})


# ---- (3) plate_layout_qc: "sân khấu" không phải ngoài trời -----------------------------------------------------------------------
def test_stage_is_not_outdoor(tmp_path):
    with mock.patch.dict(os.environ, {"FEATURE_HORIZON_NEEDS_SKY": "1"}):
        assert Q.no_sky_reason(None, None, None, None, {"location": "INT. sân khấu nhà hát — tối"}) == "bối cảnh ghi trong nhà"
        assert Q.no_sky_reason(None, None, None, None, {"location": "INT. sân sau nhà kho"}) is None      # "sân" thật vẫn là ngoài trời


# ---- (4) code_version: câu báo theo dấu vân tay, không "≠ HEAD <sha>" --------------------------------------------------------------
def test_stale_messages_speak_of_changed_code_not_head(tmp_path):
    with mock.patch.dict(os.environ, {"FEATURE_STALE_CODE_ALARM": "1"}), \
         mock.patch.dict(code_version.BOOT, {"sha": "o" * 40, "port": "8503", "code": "oldcode0aaaa"}), \
         mock.patch.object(code_version, "code_fingerprint", return_value="newcode1bbbb"), \
         mock.patch.object(code_version, "head_sha", return_value="n" * 40), \
         mock.patch.object(code_version, "stale_instances", return_value=[{"port": "8503", "pid": 7, "sha": "o" * 40, "head": "n" * 40,
                                                                         "code": "oldcode0aaaa"}]):
        mine = code_version.self_stale()
        band = code_version.banner()
    for text in (mine, band):
        assert "≠ HEAD" not in text and "nnnnnnnn" not in text
        assert "code" in text and "đổi" in text


# ---- (5) estimate_images: claude_cli + send_estimate → phần Claude = 0 (hành vi, không so chuỗi nguồn) --------------------------
from tests.test_pregen_root_fix_1710 import Base  # noqa: E402


class ClaudeCliCostsNothingInTheImageQuote(Base):
    def setUp(self):
        super().setUp()
        self.p.conn.execute("UPDATE scenes SET state='ready' WHERE id=?", (self.sid,))
        self.p.conn.commit()
        self.pricing = dict(cost.load_pricing(), per_image={"m": 0.05})

    def _est(self, provider):
        env = {"FEATURE_SEND_ESTIMATE": "1", "FEATURE_CHAT_PROMPTS": "1", "FEATURE_DIRECTOR_REWRITE": "0", "FEATURE_CHANGE_REVIEW": "0",
               "LLM_PROVIDER": provider}
        with mock.patch.dict(os.environ, env), mock.patch.object(cost, "_picture_qc_calls", return_value=1):
            return cost.estimate_images(self.p, self.pid, self.pricing, "m", data_dir=self.data)

    def test_claude_parts_are_zero_with_claude_cli(self):
        cli, api = self._est("claude_cli"), self._est("anthropic")
        self.assertEqual((cli["chat_prompt"], cli["qc"]), (0.0, 0.0))
        self.assertGreater((api["chat_prompt"] or 0) + (api["qc"] or 0), 0)
        self.assertLess(cli["total"], api["total"])


# ---- (6) continuity_shadow: "mất" trần quá rộng --------------------------------------------------------------------------------
GUN = [{"vat": "AWM", "nguoi": "KELLY", "cach": "cam"}]


def _pair(action_b):
    return [{"idx": 1, "sequence": "1", "data": {"characters": ["KELLY"], "byd": {"vat": GUN}}, "motion": ""},
            {"idx": 2, "sequence": "1", "data": {"characters": ["KELLY"], "byd": {"vat": []}, "action": action_b}, "motion": ""}]


@pytest.mark.parametrize("action", ["Kelly mất thăng bằng, vẫn chạy", "Kelly mất bình tĩnh", "Kelly biến mất sau bức tường",
                                    "Kelly trở về nhà"])
def test_unrelated_words_do_not_explain_a_vanished_gun(action):
    assert [f["evidence"]["attribute"] for f in C.build(_pair(action))["findings"]] == ["cam"]


@pytest.mark.parametrize("action", ["Kelly đánh rơi súng", "Kelly bị giật mất súng", "Kelly làm mất khẩu AWM", "Kelly drops the rifle"])
def test_real_drops_still_explain(action):
    assert C.build(_pair(action))["findings"] == []


def test_shift_words_are_narrow():
    assert C._SHIFT.search("Kelly trở về thực tại") and not C._SHIFT.search("Kelly trở về nhà")


# ---- C-FIX-THAP-2 --------------------------------------------------------------------------------------------------------------
def test_series_cache_is_thread_safe_under_eviction(tmp_path):
    import threading
    from core import clip_measure
    assert isinstance(clip_measure._SERIES_LOCK, type(threading.Lock()))
    paths = []
    for i in range(12):
        f = tmp_path / f"{i}.mp4"
        f.write_bytes(b"x" * (i + 1))
        paths.append(str(f))
    errors = []

    def hammer(k):
        try:
            for j in range(200):
                clip_measure.motion_series(paths[(k + j) % len(paths)])
        except Exception as e:  # noqa: BLE001
            errors.append(e)
    with mock.patch.object(clip_measure, "_motion_series", return_value=([0.1], 24.0, [1.0])):
        ts = [threading.Thread(target=hammer, args=(k,)) for k in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
    assert errors == [] and len(clip_measure._SERIES) <= clip_measure._SERIES_KEEP


def test_banner_says_what_an_old_sha_only_record_really_compared():
    with mock.patch.dict(os.environ, {"FEATURE_STALE_CODE_ALARM": "1"}), \
         mock.patch.object(code_version, "stale_instances", return_value=[
             {"port": "8503", "pid": 7, "sha": "o" * 40, "head": "n" * 40, "code": None},
             {"port": "8504", "pid": 8, "sha": "o" * 40, "head": "n" * 40, "code": "oldcode0aaaa"}]):
        band = code_version.banner()
    old, new = band.split("8504")
    assert "bản ghi cũ chỉ có sha" in old and "chưa biết tệp .py có đổi" in old and "tệp .py" in new and "đã đổi" in new
