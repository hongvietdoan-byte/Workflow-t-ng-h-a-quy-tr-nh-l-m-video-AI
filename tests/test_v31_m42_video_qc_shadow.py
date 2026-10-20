"""V3.1 M4.2 (C-M42): QC video SHADOW — đứng yên ≥ 1,5 s, khung 0 khác ảnh đầu, chuyển cảnh chép từ video ref, vật cầm (chưa kiểm được).
Video tổng hợp tạo trong test (OpenCV, OpenCL tắt trong clip_measure._cv). Không mạng, 0 USD."""
import json
import os
from unittest import mock

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from core import video_qc_shadow as V  # noqa: E402

FPS = 24
W, H = 320, 240


def _texture(seed):
    rng = np.random.default_rng(seed)
    small = rng.integers(0, 255, (H // 8, W // 8, 3), dtype=np.uint8)
    img = cv2.resize(small, (W, H), interpolation=cv2.INTER_NEAREST)
    for k in range(25):                                          # đường nét để có điểm đặc trưng ORB
        cv2.circle(img, (int(rng.integers(0, W)), int(rng.integers(0, H))), int(rng.integers(4, 20)),
                   tuple(int(c) for c in rng.integers(0, 255, 3)), 2)
    return img


def _write(path, frames):
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for f in frames:
        w.write(f)
    w.release()
    return str(path)


def _moving(img, n, start=0):
    return [np.roll(img, (start + i) * 3, axis=1) for i in range(n)]


def test_flag_is_off_by_default():
    from core import features
    assert V.FLAG in features.FEATURES
    with mock.patch.dict(os.environ, {"FEATURE_VIDEO_QC_SHADOW": ""}):
        assert not V.enabled()


def test_still_spans_pure():
    series = [1.0] * 10 + [0.01] * 48 + [1.0] * 10                 # 48 cặp khung yên = 2 s ở 24 fps
    assert V.still_spans(series, 24.0) == [(0.42, 2.42)]
    assert V.still_spans([0.01] * 30, 24.0) == []                  # 1,25 s < 1,5 s
    cut = [1.0] * 40                                               # cảnh cắt giữa đoạn yên: hai đoạn ngắn, không phải đứng yên
    assert V.still_spans([0.01] * 40, 24.0, same=[1.0] * 20 + [0.1] + [1.0] * 19) == []
    assert V.still_spans(cut, 24.0) == []


def test_clip_standing_still_two_seconds_is_reported(tmp_path):
    a = _texture(1)
    frames = _moving(a, 24) + [_moving(a, 1, 24)[0]] * 48 + _moving(a, 24, 25)
    res = V.check(_write(tmp_path / "still.mp4", frames))
    stills = [f for f in res["findings"] if f["qc_code"] == "QC-V2-STILL_OVER_1_5S"]
    assert len(stills) == 1 and stills[0]["severity"] == "REVIEW" and stills[0]["registry_ids"] == ["P31-G51"]
    assert 1.8 <= stills[0]["evidence"]["t1"] - stills[0]["evidence"]["t0"] <= 2.1


def test_moving_clip_has_no_still_finding(tmp_path):
    res = V.check(_write(tmp_path / "move.mp4", _moving(_texture(2), 72)))
    assert res["measured"] and not [f for f in res["findings"] if f["qc_code"] == "QC-V2-STILL_OVER_1_5S"]


def test_first_frame_other_than_the_approved_picture(tmp_path):
    a, b = _texture(3), _texture(4)
    pic = str(tmp_path / "start.png")
    cv2.imwrite(pic, a)
    bad = V.check(_write(tmp_path / "other.mp4", _moving(b, 30)), picture=pic)
    assert [f["qc_code"] for f in bad["findings"]] == ["QC-V1-FIRST_FRAME_MISMATCH"]
    assert bad["findings"][0]["registry_ids"] == ["P31-G28"]
    good = V.check(_write(tmp_path / "same.mp4", _moving(a, 30)), picture=pic)
    assert not [f for f in good["findings"] if f["qc_code"] == "QC-V1-FIRST_FRAME_MISMATCH"]


def test_missing_picture_is_said_not_passed(tmp_path):
    res = V.check(_write(tmp_path / "c.mp4", _moving(_texture(5), 30)), picture=str(tmp_path / "none.png"))
    assert any("không có ảnh khung đầu" in n for n in res["notes"])


def test_ref_transition_copied_into_the_clip(tmp_path):
    x, y = _texture(6), _texture(7)
    y[:, :, 1:] //= 5                                             # cảnh sau tông xanh lam: một cảnh khác hẳn (như khúc mở đầu ref #33)
    ref = _write(tmp_path / "ref.mp4", _moving(x, 12) + _moving(y, 60))           # cắt cảnh ở 0,5 s
    copied = V.check(_write(tmp_path / "clip.mp4", _moving(x, 12, 5) + _moving(y, 60, 5)), ref_video=ref)
    found = [f for f in copied["findings"] if f["qc_code"] == "QC-V2-REF_TRANSITION"]
    assert len(found) == 1 and found[0]["registry_ids"] == ["P33-B8"]
    clean = V.check(_write(tmp_path / "clean.mp4", _moving(y, 72)), ref_video=ref)
    assert not [f for f in clean["findings"] if f["qc_code"] == "QC-V2-REF_TRANSITION"]
    assert any("video ref có chuyển cảnh" in n for n in clean["notes"])


def test_held_prop_is_listed_as_unchecked_never_as_passed(tmp_path):
    data = {"byd": {"vat": [{"vat": "SUNG", "nguoi": "KELLY", "cach": "cam"}, "MU"]}}
    res = V.check(_write(tmp_path / "c.mp4", _moving(_texture(8), 30)), data=data)
    assert [u["vat"] for u in res["chua_kiem"]] == ["SUNG"]
    assert all(f["qc_code"] != "QC-L7-PROP_HELD" for f in res["findings"])


def test_unreadable_clip_is_not_a_pass(tmp_path):
    bad = tmp_path / "x.mp4"
    bad.write_bytes(b"not a video")
    res = V.check(str(bad))
    assert res["measured"] is False and res["notes"]


class _Conn:
    def __init__(self, ref=None):
        self.ref = ref

    def execute(self, *a, **k):
        ref = self.ref
        return mock.Mock(fetchone=lambda: {"ref_video_path": ref})


def test_observe_flag_off_writes_nothing(tmp_path):
    clip = _write(tmp_path / "c.mp4", _moving(_texture(9), 30))
    with mock.patch.dict(os.environ, {"FEATURE_VIDEO_QC_SHADOW": ""}):
        assert V.observe(_Conn(), str(tmp_path), {"id": 1, "project_id": 5, "scene_id": 2}, clip, {}) is None
    assert not os.path.exists(tmp_path / "5" / "qc_shadow")


def test_observe_flag_on_writes_one_record_per_run(tmp_path):
    a = _texture(10)
    clip = _write(tmp_path / "c.mp4", _moving(a, 12) + [a] * 48)
    with mock.patch.dict(os.environ, {"FEATURE_VIDEO_QC_SHADOW": "1"}):
        rec = V.observe(_Conn(), str(tmp_path), {"id": 1, "project_id": 5, "scene_id": 2}, clip, {})
    assert rec["mode"] == "shadow" and rec["artifact_id"] == "job:1" and len(rec["artifact_sha"]) == 64
    assert [r["qc_run_id"] for r in V.read(str(tmp_path), 5)] == [rec["qc_run_id"]]
    assert json.loads(open(tmp_path / "5" / "qc_shadow" / "video_qc.jsonl", encoding="utf-8").read())["findings"]


def test_observe_never_raises(tmp_path):
    with mock.patch.dict(os.environ, {"FEATURE_VIDEO_QC_SHADOW": "1"}), mock.patch.object(V, "check", side_effect=RuntimeError("boom")), \
         mock.patch("core.diag.record") as rec:
        assert V.observe(_Conn(), str(tmp_path), {"id": 1, "project_id": 5, "scene_id": 2}, "x.mp4", {}) is None
    assert rec.call_args.args[4] == "video_qc_shadow"


def test_real_qc_path_calls_the_shadow_and_keeps_its_result(tmp_path):
    """_measure_clip trả đúng số đo cũ; shadow chỉ được gọi thêm (không đổi kết quả)."""
    from core import claude_tasks
    p = mock.Mock()
    with mock.patch("core.clip_measure.measure", return_value={"flags": []}) as measure, \
         mock.patch.object(V, "observe") as observe, mock.patch("core.shots.approved_image_path", return_value=None):
        out = claude_tasks._measure_clip(p, {"project_id": 1, "scene_id": 2, "id": 3}, "c.mp4", {}, None, str(tmp_path))
    assert out == {"flags": []} and measure.called and observe.call_count == 1
