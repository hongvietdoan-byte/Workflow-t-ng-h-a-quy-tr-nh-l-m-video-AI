"""Đ11v4: hình học giả, không mạng/model/dữ liệu sản xuất."""
from unittest.mock import patch
import pytest

from core import film_grammar as G


def shot(x=0):
    return {"stage_camera": {"location": [x, -5, 1.6], "look_at": [0, 0, 1], "lens": 35},
            "size": "MS", "byd": {"hanh_dong": [{"ai": "A", "bat_dau": {"nhin": "B"}}]}}


OBJECTS = {"A": {"kind": "nguoi", "xy": [0, 0], "z": 0, "H": 1.7, "facing": 90},
           "B": {"kind": "nguoi", "xy": [-2, 0], "z": 0, "H": 1.7, "facing": 270}}


def test_off_does_not_inspect():
    with patch("core.features.on", return_value=False):
        assert G.warnings([(1, 1, shot())], objects=OBJECTS) == []


def test_same_angle_and_wrong_eyeline():
    with patch("core.features.on", return_value=True):
        out = G.warnings([(1, 1, shot()), (1, 2, shot(.1))], objects=OBJECTS)
    assert any("30°" in w for w in out)
    assert any("hướng nhìn" in w for w in out)


def test_missing_is_yellow():
    with patch("core.features.on", return_value=True):
        assert any("không kiểm" in w for w in G.warnings([(1, 1, {})]))


def test_intentional_jump_only_suppresses_jump():
    s = shot(.1)
    s["byd"]["ngoai_le"] = [{"doi_tuong": "may", "dieu_trai": "cắt nhảy", "cach_hien": "cố ý", "ly_do": "phong_cach", "pham_vi": [2]}]
    with patch("core.features.on", return_value=True):
        out = G.warnings([(1, 1, shot()), (1, 2, s)], objects=OBJECTS)
    assert not any("shot 1·2" in w and "30°" in w for w in out)
    assert any("shot 1·2" in w and "hướng nhìn" in w for w in out)


def test_projection_back_of_camera_is_unknown():
    s = shot()
    s["stage_camera"]["look_at"] = [0, -10, 1]
    with patch("core.features.on", return_value=True):
        assert any("không kiểm" in w for w in G.warnings([(1, 1, s)], objects=OBJECTS))


def test_lead_and_head_room_measured_by_projection():
    s = shot()
    # Người nằm sát mép phải, nhìn tiếp sang phải; đầu nằm quá thấp trong khung.
    def project(*args):
        point = args[-1]
        return (.9 + point[0] * .1, .45)
    with patch("core.features.on", return_value=True), patch("core.plate_camera.project", side_effect=project):
        out = G.warnings([(1, 1, s)], objects=OBJECTS)
    assert any("phía trước mặt" in w for w in out)
    assert any("trên đầu" in w for w in out)


def test_flags_default_and_experimental_off_with_fake_environment():
    import os
    from core import features
    original = os.environ
    for preset in ("custom", "experimental", "stable"):
        fake = {}
        with patch.object(os, "environ", fake), patch.object(features, "settings", return_value={"preset": preset, "flags": {}}):
            assert not features.on("film_grammar_check")
            assert not features.on("camera_match_qc")
            with patch.dict(fake, {"FEATURE_FILM_GRAMMAR_CHECK": "1"}):
                assert features.on("film_grammar_check") == (preset != "stable")
            assert "FEATURE_FILM_GRAMMAR_CHECK" not in fake
        assert os.environ is original


def test_existing_axis_golden_not_reimplemented():
    from core import continuity
    with patch("core.features.on", return_value=False):
        out = continuity.axis_warnings([(1, 1, {"characters": ["A", "B"], "start_frame": "A frame-left, B frame-right"}),
                                        (1, 2, {"characters": ["A", "B"], "start_frame": "B frame-left, A frame-right"})])
    assert any("180°" in w for w in out)


def test_actor_move_uses_previous_actor_position():
    a = shot()
    first = {"A": dict(OBJECTS["A"], xy=[-4, 0])}
    second = {"A": dict(OBJECTS["A"], xy=[4, 0])}
    with patch("core.features.on", return_value=True):
        out = G.warnings([(1, 1, a), (1, 2, shot())], objects=lambda _, s: first if s is a else second)
    assert not any("30°" in w for w in out)


@pytest.mark.parametrize("field,value", [("facing", float("nan")), ("xy", [float("nan"), 0]), ("H", float("inf")), ("z", float("nan"))])
def test_nonfinite_actor_is_yellow_even_closeup(field, value):
    s = shot()
    s["size"] = "CU"
    objects = {"A": dict(OBJECTS["A"], **{field: value}), "B": dict(OBJECTS["B"])}
    with patch("core.features.on", return_value=True):
        out = G.warnings([(1, 1, s)], objects=objects)
    assert any("không hợp lệ" in w for w in out)


def test_nonfinite_look_target_is_yellow():
    objects = {"A": dict(OBJECTS["A"]), "B": dict(OBJECTS["B"], xy=[float("nan"), 0])}
    with patch("core.features.on", return_value=True):
        out = G.warnings([(1, 1, shot())], objects=objects)
    assert any("không hợp lệ" in w for w in out)


def test_declared_actor_missing_from_stage_is_yellow():
    with patch("core.features.on", return_value=True):
        out = G.warnings([(1, 1, shot())], objects={"B": OBJECTS["B"]})
    assert any("thiếu" in w and "A" in w for w in out)


@pytest.mark.parametrize("bad", [{"byd": "A nhìn B"}, {"byd": {"hanh_dong": "A"}}, {"byd": {"may": "MS"}, "size": ""}])
def test_malformed_byd_is_yellow_not_crash(bad):
    # Rà gộp Đ11v2+v4: BYĐ do Claude viết có thể sai kiểu — báo VÀNG, không ném AttributeError làm vỡ report/khung Trước khi chạy.
    s = dict(shot(), **bad)
    with patch("core.features.on", return_value=True):
        out = G.warnings([(1, 1, s)], objects=OBJECTS)
    assert out and all(isinstance(w, str) for w in out)


def test_before_run_survives_film_grammar_failure():
    # Khung "Trước khi chạy": một phần lỗi chỉ thành mục info, không làm vỡ Bước 1 (hợp đồng core/before_run._collect).
    from core import before_run, continuity
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect())
    pid = p.create_project("t")
    p.add_scene_next(pid, "s1")
    with patch.object(continuity, "film_warnings", side_effect=RuntimeError("hỏng")):
        res = before_run._collect(p.conn, "unused", pid)
    texts = [it["text"] for g in res["groups"] for it in g["items"]]
    assert any("luật quay" in t and "RuntimeError" in t for t in texts)
