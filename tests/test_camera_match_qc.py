from unittest.mock import patch

from core import camera_match_qc as Q


def test_off_no_detector():
    with patch("core.features.on", return_value=False), patch("core.clip_measure._faces", side_effect=AssertionError):
        assert Q.check_image("missing", {}, {}) == []


def test_missing_inputs_not_green():
    with patch("core.features.on", return_value=True):
        out = Q.check_image("missing", {}, {})
    assert out and all(i["muc"] == "vang" for i in out)
    assert any("không đo" in i["loi"] for i in out)


def test_measured_mismatch():
    measured = {"face_height": .3, "eyes": [.8, .2], "horizon": .9}
    expected = {"face_height": .12, "eyes": [.5, .4], "horizon": .5}
    out = Q.compare(measured, expected)
    assert len(out) == 3
    assert all("chưa hiệu chỉnh" in i["loi"] for i in out)


def test_missing_measurements_do_not_pass():
    assert len(Q.compare({}, {"face_height": .1, "eyes": [.5, .4], "horizon": .5})) == 3


def test_image_local_measure_and_no_real_detector(tmp_path):
    import os
    import numpy as np
    from PIL import Image
    path = tmp_path / "fake.png"
    Image.new("RGB", (80, 100), "gray").save(path)
    model = tmp_path / "fake.onnx"
    model.write_bytes(b"fake")
    original = os.environ
    for initial in ({}, {"FACE_MODEL": str(model)}):
        fake = dict(initial)
        with patch.object(os, "environ", fake), patch("core.features.on", return_value=True), patch("core.text_placement.FACE_MODEL", str(model)), patch("core.clip_measure._faces", return_value=[(20, 10, 30, 20, [(25, 15), (45, 15), (35, 20), (25, 25), (45, 25)])]), patch("core.plate_layout_qc.horizon_row", return_value=.9):
            out = Q.check_image(str(path), {"location": [0, -5, 1.6], "look_at": [0, 0, 1], "lens": 35}, {"xy": [0, 0], "z": 0, "H": 1.7})
            assert any("chân trời" in i["loi"] for i in out)
            assert out[0]["measured"]["face_height"] == .2
        assert os.environ is original
        assert ("FACE_MODEL" in fake) == ("FACE_MODEL" in initial)


def test_unc_and_url_never_touch_detector():
    with patch("core.features.on", return_value=True), patch("core.clip_measure._cv", side_effect=AssertionError):
        assert Q.check_image("https://invalid/x.png", {})
        assert Q.check_clip("\\\\server\\fake.mp4", {})


def test_clip_reads_only_two_frames_and_releases(tmp_path):
    import os
    import numpy as np
    from unittest.mock import MagicMock
    path = tmp_path / "fake.mp4"
    path.write_bytes(b"fake")
    cv = MagicMock()
    cv.CAP_PROP_FRAME_COUNT = 1
    cv.CAP_PROP_POS_FRAMES = 2
    cap = cv.VideoCapture.return_value
    cap.get.return_value = 100000
    cap.read.return_value = (True, np.zeros((30, 20, 3), dtype=np.uint8))
    with patch.object(os, "environ", {}), patch("core.features.on", return_value=True), patch("core.clip_measure._cv", return_value=cv), patch.object(Q, "_measure", return_value={}):
        assert Q.check_clip(str(path), {"move": "dolly"})
    assert cap.read.call_count == 2
    assert [c.args[1] for c in cap.set.call_args_list] == [0, 99999]
    cap.release.assert_called_once()


def test_failed_seek_is_unknown_not_frame_from_wrong_position(tmp_path):
    from unittest.mock import MagicMock
    path = tmp_path / "fake.mp4"
    path.write_bytes(b"fake")
    cv = MagicMock()
    cap = cv.VideoCapture.return_value
    cap.get.return_value = 200
    cap.set.return_value = False
    cap.read.return_value = (True, object())
    with patch("core.features.on", return_value=True), patch("core.clip_measure._cv", return_value=cv), patch.object(Q, "_measure", return_value={"horizon": .5}):
        out = Q.check_clip(str(path), {})
    assert cap.read.call_count == 0
    assert out and all(i["muc"] == "vang" for i in out)


def test_last_frame_without_end_actor_cannot_reuse_start_state(tmp_path):
    from unittest.mock import MagicMock
    path = tmp_path / "fake.mp4"
    path.write_bytes(b"fake")
    cv = MagicMock()
    cap = cv.VideoCapture.return_value
    cap.get.return_value = 2
    cap.read.return_value = (True, object())
    camera = {"location": [0, -5, 1.6], "look_at": [0, 0, 1], "lens": 35}
    actor = {"xy": [0, 0], "z": 0, "H": 1.7}
    measured = Q.expected(camera, actor)
    with patch("core.features.on", return_value=True), patch("core.clip_measure._cv", return_value=cv), patch.object(Q, "_measure", return_value=measured):
        out = Q.check_clip(str(path), camera, actor)
    final = [i for i in out if i["loi"].startswith("Khung cuối")]
    assert len(final) == 2
    assert all(i["expected"].get("eyes") is None and i["expected"].get("face_height") is None for i in final)
    assert all("chân trời" not in i["loi"] for i in final)
