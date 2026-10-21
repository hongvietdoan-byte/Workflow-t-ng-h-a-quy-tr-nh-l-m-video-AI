"""C-FIX-THAP-4 (cloud-C 21/10, rà phiên chính nhánh fix-thap-2):
VỪA core/qc_scene._behind_any — image_prompt / action quét bằng cùng regex trường máy, nên câu HÀNH ĐỘNG ("hides the grenade behind her back",
"grabs him from behind", "vác súng qua vai"…) bị coi là bố cục sau lưng → khi bật cờ qc_false_alarm_fix bỏ kiểm cỡ shot sai. Nay 2 regex:
trường máy giữ như cũ; chữ tả cảnh chỉ khớp chữ gắn với MÁY.
THẤP core/code_version.banner — bản ghi có dấu code nhưng máy không tính được dấu hiện tại (so bằng sha) vẫn nói "tệp .py đã đổi"."""
import json
import os
from unittest import mock

import pytest

from core import code_version, qc_scene
from tests.test_v31_dp1_qc_false_alarms import ON, S2, _check


@pytest.mark.parametrize("field,words", [
    ("action", "Kelly hides the grenade behind her back"),
    ("action", "an enemy grabs him from behind"),
    ("action", "Kelly sneaks up from behind the wall"),
    ("action", "Kelly vác súng qua vai"),
    ("image_prompt", "Kelly nhìn qua vai về phía địch"),
    ("image_prompt", "Kelly glances over the shoulder at the tower"),
])
def test_action_words_are_not_a_camera_behind(field, words):
    assert not qc_scene._behind_any({field: words})
    with ON:
        out, measure = _check({"size": "MS", "characters": ["KELLY"], field: words})
    assert [o["code"] for o in out] == ["shot_size"] and "size_skipped" not in measure


@pytest.mark.parametrize("field,words", [
    ("image_prompt", S2["image_prompt"]),                                  # ca thật P33-A5 (#33 S2)
    ("action", "over-the-shoulder on Kelly"), ("action", "máy đặt SAU LƯNG Kelly"), ("action", "camera behind her shoulders"),
    ("action", "quay lưng về máy"), ("action", "rear view of the squad"), ("image_prompt", "OTS of Kelly aiming"),
    ("image_prompt", "Kelly seen from behind, running to the tower"), ("image_prompt", "góc qua vai Kelly nhìn tháp"),
    ("image_prompt", "over-the-shoulder shot on the sniper"),
])
def test_camera_words_in_prose_still_count(field, words):
    assert qc_scene._behind_any({field: words})


@pytest.mark.parametrize("field,words", [("angle", "from behind"), ("shot", "qua vai"), ("blocking", "behind her back to camera"),
                                         ("start_frame", "from behind the group")])
def test_camera_fields_keep_the_wide_regex(field, words):
    assert qc_scene._behind_any({field: words})


def test_banner_never_says_py_changed_when_compared_by_sha(tmp_path):
    db = str(tmp_path / "data" / "m.sqlite")
    os.makedirs(os.path.dirname(db))
    run = code_version.run_dir(db)
    os.makedirs(run)
    with open(os.path.join(run, "dashboard_8501.json"), "w", encoding="utf-8") as f:
        json.dump({"port": "8501", "pid": os.getpid(), "sha": "a" * 40, "code": "c" * 16, "at": 0}, f)
    with mock.patch.dict(os.environ, {"FEATURE_STALE_CODE_ALARM": "1"}), \
         mock.patch.object(code_version, "code_fingerprint", return_value=None), \
         mock.patch.object(code_version, "head_sha", return_value="b" * 40), \
         mock.patch.object(code_version, "_same_process", return_value=True):
        text = code_version.banner(db)
    assert "8501" in text and "tệp .py" not in text and "aaaaaaaa" in text
