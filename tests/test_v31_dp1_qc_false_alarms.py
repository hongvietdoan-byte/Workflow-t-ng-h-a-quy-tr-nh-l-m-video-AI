"""DP1 — V3.1 M4.5 (cloud-C 20/10): sửa báo nhầm P33-A5 + P33-A6 (docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md). Cờ `qc_false_alarm_fix`
TẮT = như cũ (byte). Fixture tổng hợp theo ca thật; không gọi model, 0 USD.

A5: QC lớp 0 (qc_scene.check_frame) đo cỡ cảnh theo mặt LỚN nhất — #33 S2 máy thấp SAU LƯNG nhóm mèo: mặt con tím ở xa → "WS, shot xin MS"
    → tự tạo job gen lại ép "từ thắt lưng trở lên". Bố cục qua vai / sau lưng: mặt đo được không phải cỡ của shot → bỏ kiểm cỡ, nói lý do.
A6: Tổ rà soát (change_review.build_prompt) không đưa motion_prompts.ref_video_path vào đề → agent báo "shot 6 không có video tham chiếu"."""
import json
import os
from unittest import mock

import pytest

from core import change_review, qc_scene
from core.db import connect
from core.pipeline import Pipeline

ON = mock.patch.dict(os.environ, {"FEATURE_QC_FALSE_ALARM_FIX": "1"})
OFF = mock.patch.dict(os.environ, {"FEATURE_QC_FALSE_ALARM_FIX": ""})
S2 = {"size": "MS", "angle": "low", "characters": ["MEO_CAM", "MEO_TIM", "MEO_XAM"],
      "image_prompt": "Low camera behind the group: the backs of two cats fill the left and right foreground, the purple cat faces us far away"}


def _check(data, face_h=0.08):
    """check_frame với một mặt cao face_h khung (mặt con tím ở xa)."""
    with mock.patch.object(qc_scene, "_blank", return_value=None), \
         mock.patch("core.text_placement.face_boxes", return_value=[(0.45, 0.30, 0.52, 0.30 + face_h)]):
        measure = {}
        return qc_scene.check_frame("x.png", data, measure=measure), measure


def test_flag_off_keeps_the_old_false_alarm():
    with OFF:
        out, _ = _check(S2)
    assert [o["code"] for o in out] == ["shot_size"]                     # lỗi A5 như #33 (cờ tắt = y cũ)


def test_behind_the_group_skips_the_size_check_and_says_why():
    with ON:
        out, measure = _check(S2)
    assert "shot_size" not in [o["code"] for o in out]
    assert "sau lưng" in measure.get("size_skipped", "") or "qua vai" in measure.get("size_skipped", "")
    assert measure["measured"] and measure["planned"] == "MS"           # số đo vẫn ghi (hiệu chuẩn), chỉ không phán


@pytest.mark.parametrize("words", ["over-the-shoulder on Kelly", "máy đặt SAU LƯNG Kelly", "camera behind her shoulders",
                                   "quay lưng về máy", "rear view of the squad"])
def test_behind_words_in_any_field(words):                   # C-FIX-THAP-2: chữ về MÁY ở mọi trường (cả image_prompt / action)
    with ON:
        out, _ = _check({"size": "MS", "characters": ["KELLY"], "action": words})
    assert "shot_size" not in [o["code"] for o in out]


def test_a_front_shot_is_still_checked():
    with ON:
        out, measure = _check({"size": "MS", "characters": ["KELLY"], "image_prompt": "Kelly faces the camera, a tower behind her"})
    assert [o["code"] for o in out] == ["shot_size"] and "size_skipped" not in measure      # "tower behind her" không phải sau lưng nhân vật


def _review_db(tmp_path, ref):
    p = Pipeline(connect(str(tmp_path / "m.sqlite")))
    pid = p.create_project("p33")
    sid = p.create_scene(pid, 6, "S6")
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"characters": ["MEO"], "action": "nhảy", "size": "MLS"}), sid))
    p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, state, ref_video_path) VALUES (?,?,?,?)",
                   (sid, "cats dance", "approved", ref))
    p.conn.commit()
    ev = {"id": 877, "kind": "scene", "scene_id": sid, "before": "{}", "after": "{}", "asset_id": None}
    return p.conn, ev, sid


def test_review_prompt_carries_the_reference_video(tmp_path):
    conn, ev, sid = _review_db(tmp_path, str(tmp_path / "motion_ref" / "shot6_ref.mp4"))
    with OFF:
        old = change_review.build_prompt(conn, ev, [], [sid], [])
    with ON:
        new = change_review.build_prompt(conn, ev, [], [sid], [])
    assert "shot6_ref.mp4" not in old                                    # A6: agent không biết có ref → "không có video tham chiếu"
    assert "shot6_ref.mp4" in new and "video tham chiếu" in new
    assert str(tmp_path) not in new                                      # chỉ tên tệp, không lộ đường dẫn máy


def test_review_prompt_says_when_there_is_none(tmp_path):
    conn, ev, sid = _review_db(tmp_path, None)
    with ON:
        new = change_review.build_prompt(conn, ev, [], [sid], [])
    assert "video tham chiếu: (không có)" in new


def test_flag_off_review_prompt_is_byte_identical(tmp_path):
    conn, ev, sid = _review_db(tmp_path, "x.mp4")
    with OFF:
        a = change_review.build_prompt(conn, ev, [], [sid], [])
    with mock.patch.dict(os.environ, {"FEATURE_QC_FALSE_ALARM_FIX": "0"}):
        b = change_review.build_prompt(conn, ev, [], [sid], [])
    conn.execute("UPDATE motion_prompts SET ref_video_path=NULL")
    with OFF:
        c = change_review.build_prompt(conn, ev, [], [sid], [])
    assert a == b == c
