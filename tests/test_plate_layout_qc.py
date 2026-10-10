"""Không coi thiếu số đo bố cục là đạt (không gọi model)."""
import json
from unittest.mock import patch

import pytest
from PIL import Image

from core import plate_layout_qc as qc


@pytest.mark.parametrize("missing", ["plate", "image"])
def test_unreadable_layout_is_unmeasured(tmp_path, missing):
    plate, image = tmp_path / "plate.png", tmp_path / "image.png"
    Image.new("RGB", (100, 100), "white").save(plate)
    Image.new("RGB", (100, 100), "white").save(image)
    (plate if missing == "plate" else image).unlink()
    res = qc.compare(str(image), str(plate))
    assert res["measured"] is False and res["muc"] == "vang"
    assert res["mismatch"] is False and res["reasons"]


def test_no_horizon_is_not_a_layout_pass(tmp_path):
    plate = tmp_path / "flat.png"
    Image.new("RGB", (100, 100), "white").save(plate)
    res = qc.compare(str(plate), str(plate))
    assert res["measured"] is False and res["muc"] == "vang"
    assert res["reasons"] and not res["mismatch"]


def test_check_job_records_yellow_when_unmeasured(tmp_path):
    with patch("core.camera_plan.enabled", return_value=True), \
            patch("core.place_refs.shot_ref", return_value={"path": "missing.png", "_rec": {}}), \
            patch.object(qc, "_stage_horizon", return_value=None):
        severity, words = qc.check_job(None, str(tmp_path), 1, 2, 3, "missing.png")
    assert severity == "warn" and "không đo được bố cục" in words
    assert "khớp" not in words
    rows = json.loads((tmp_path / "1" / "plate_layout.json").read_text(encoding="utf-8"))
    assert rows[0]["measured"] is False and rows[0]["muc"] == "vang"


def test_readable_horizon_keeps_matching_result(tmp_path):
    plate = tmp_path / "horizon.png"
    im = Image.new("RGB", (100, 100), "white")
    im.paste("black", (0, 50, 100, 100))
    im.save(plate)
    res = qc.compare(str(plate), str(plate))
    assert res["measured"] is True and res["muc"] == "xanh"
    assert res["mismatch"] is False and not res["reasons"]


def test_bright_render_without_horizon_but_edge_is_partly_measured(tmp_path):
    """Rà 10/10 lỗi 3: render SÁNG không chân trời (tường/nhà che) mà F1 đường nét đo được → đã đo một phần, không VÀNG oan."""
    plate = tmp_path / "wall.png"
    Image.new("RGB", (100, 100), "white").save(plate)
    with patch("core.place_refs.background_match", return_value=0.8):
        res = qc.compare(str(plate), str(plate))
    assert res["measured"] is True and res["partial"] is True and res["muc"] == "xanh" and not res["mismatch"]
    assert any("đo được một phần" in r for r in res["reasons"])
    with patch("core.camera_plan.enabled", return_value=True), \
            patch("core.place_refs.shot_ref", return_value={"path": str(plate), "_rec": {}}), \
            patch("core.place_refs.background_match", return_value=0.8), \
            patch.object(qc, "_stage_horizon", return_value=None):
        severity, words = qc.check_job(None, str(tmp_path), 1, 2, 3, str(plate))
    assert severity == "info" and "đo được một phần" in words and "khớp render" not in words
    dark = tmp_path / "night.png"                                    # render TỐI không chân trời: vẫn VÀNG dù có F1
    Image.new("RGB", (100, 100), "black").save(dark)
    with patch("core.place_refs.background_match", return_value=0.8):
        assert qc.compare(str(dark), str(dark))["measured"] is False
