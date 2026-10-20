"""DP2 — V3.1 M3.5 (cloud-C 20/10): P31-G20 — cổng ảnh→video (plate_layout_qc.verdict / check_strict) báo nhầm "lệch nền 3D" khi ảnh
không có trời: S22 trong phòng, S39 nhìn từ trên cao — "chân trời" đo được chỉ là mép tường / sàn (7 % / 14 % khung). Cờ `horizon_needs_sky`
TẮT = như cũ. Bật: nền KHÔNG có trời (chỗ đứng 3D trong nhà / BYĐ trong nhà / góc overhead / render sáng không có trời) → bỏ kiểm chân
trời, nói lý do (VÀNG, không ĐỎ); có trời hoặc KHÔNG RÕ (render tối, không khai gì) → giữ kiểm. Ảnh tổng hợp, 0 USD."""
import json
import os
from unittest import mock

import pytest

np = pytest.importorskip("numpy")
from PIL import Image  # noqa: E402

from core import plate_layout_qc as Q  # noqa: E402

ON = mock.patch.dict(os.environ, {"FEATURE_HORIZON_NEEDS_SKY": "1"})
OFF = mock.patch.dict(os.environ, {"FEATURE_HORIZON_NEEDS_SKY": ""})


def _room(path, edge, top=(200, 190, 170), bottom=(90, 70, 50)):
    """Trong phòng: tường sáng trên, sàn tối dưới — bước sáng/tối mạnh nhất ở `edge` (không phải trời)."""
    a = np.zeros((256, 144, 3), np.uint8)
    cut = int(edge * 256)
    a[:cut] = top
    a[cut:] = bottom
    Image.fromarray(a).save(path)
    return str(path)


def _outdoor(path, edge):
    return _room(path, edge, top=(110, 160, 235), bottom=(70, 90, 60))        # trời xanh trên, đất dưới


def _horizon_reasons(res):
    return [r for r in res["reasons"] if "chân trời" in r and "khác render" in r or "nền khác" in r]


def test_flag_off_keeps_the_false_alarm(tmp_path):
    plate, img = _room(tmp_path / "p.png", 0.07), _room(tmp_path / "i.png", 0.40)
    with OFF:
        res = Q.verdict(img, plate, no_sky=Q.no_sky_reason(None, None, None, plate, {"angle": "overhead"}))
    assert _horizon_reasons(res)                                       # G20 như #31 S22/S39


@pytest.mark.parametrize("data", [{"angle": "overhead"}, {"byd": {"noi_chon": {"trong_nha": True}}},
                                  {"location": "INT. phòng ngủ Kelly — ban đêm"}])
def test_declared_no_sky_skips_the_horizon_with_a_reason(tmp_path, data):
    plate, img = _room(tmp_path / "p.png", 0.07), _room(tmp_path / "i.png", 0.40)
    with ON:
        why = Q.no_sky_reason(None, None, None, plate, data)
        res = Q.verdict(img, plate, no_sky=why)
    assert why and not _horizon_reasons(res)
    assert res["muc"] != "do"
    assert any(r.startswith("bỏ kiểm chân trời") for r in res["reasons"])     # nói lý do, không im lặng


def test_bright_render_without_sky_is_no_sky(tmp_path):
    plate = _room(tmp_path / "p.png", 0.14)
    with ON:
        assert "render 3D không có trời" in (Q.no_sky_reason(None, None, None, plate, {}) or "")


def test_sky_in_the_render_keeps_the_check(tmp_path):
    plate, img = _outdoor(tmp_path / "p.png", 0.30), _outdoor(tmp_path / "i.png", 0.60)
    with ON:
        why = Q.no_sky_reason(None, None, None, plate, {})
        res = Q.verdict(img, plate, no_sky=why)
    assert why is None and _horizon_reasons(res)


def test_unknown_dark_render_keeps_the_check(tmp_path):
    plate = _room(tmp_path / "p.png", 0.20, top=(40, 40, 50), bottom=(10, 10, 12))   # đêm tối: không đo được trời → KHÔNG RÕ
    with ON:
        assert Q.no_sky_reason(None, None, None, plate, {}) is None


def test_outdoor_location_text_is_not_indoor(tmp_path):
    plate = _outdoor(tmp_path / "p.png", 0.30)
    with ON:
        assert Q.no_sky_reason(None, None, None, plate, {"location": "EXT. sân trước nhà — chiều"}) is None


def test_check_strict_passes_the_reason(tmp_path):
    plate, img = _room(tmp_path / "p.png", 0.07), _room(tmp_path / "i.png", 0.40)
    conn = mock.Mock()
    conn.execute.return_value.fetchone.return_value = (json.dumps({"angle": "overhead"}),)
    ref = {"path": plate, "_rec": {}, "plate_key": "k"}
    with ON, mock.patch("core.place_refs.shot_ref", return_value=ref), mock.patch.object(Q, "_stage_horizon", return_value=None), \
         mock.patch.object(Q, "_record"):
        sev, words = Q.check_strict(conn, str(tmp_path), 1, 2, 3, img)
    assert sev != "error" and "bỏ kiểm chân trời" in words
