"""Nhánh tích hợp M2 (C-M2-TICHHOP, 21/10) — sửa lỗi VỪA của 2 lượt rà chéo.
M21-1 (docs RA_CLOUD_RA_M21_M25): BYĐ sai kiểu (chuỗi / danh sách) trên main làm vỡ nơi đọc (AttributeError → QC dừng trước lượt VLM,
lock_exceptions lỗi); adapter byd_of() trả None → `or {}` nuốt IM LẶNG. Cờ byd_v2_levels TẮT → y hệt main (vẫn vỡ như cũ);
BẬT → BydTypeError (ValueError) mức REVIEW, mã byd_sai_kieu — nói ra, không im lặng (qc_observe._prepare bắt thành VÀNG)."""
import os
from unittest import mock

import pytest

from core import film_grammar, lock_exceptions, qc_observe, shot_intent

OFF = {"FEATURE_BYD_V2_LEVELS": ""}
ON = {"FEATURE_BYD_V2_LEVELS": "1"}
BAD = ("BOM", ["BOM_KEO"])


def _qc(data):
    return qc_observe.compile_checks(None, 24, 1, dict(data, characters=["GIRL"]), ["set_match"], profiles={})


CALLS = {
    "qc_observe": _qc,
    "lock_exceptions.for_shot": lock_exceptions.for_shot,
    "lock_exceptions.shot_label": lock_exceptions.shot_label,
    "film_grammar._exception": lambda d: film_grammar._exception(d, 1, "jump"),
}


@pytest.mark.parametrize("bad", BAD)
@pytest.mark.parametrize("name", sorted(CALLS))
def test_flag_off_wrong_type_breaks_like_main(name, bad):
    with mock.patch.dict(os.environ, OFF), pytest.raises(AttributeError):
        CALLS[name]({"byd": bad})


@pytest.mark.parametrize("bad", BAD)
@pytest.mark.parametrize("name", sorted(CALLS))
def test_flag_on_wrong_type_is_said_as_review(name, bad):
    with mock.patch.dict(os.environ, ON), pytest.raises(shot_intent.BydTypeError) as e:
        CALLS[name]({"byd": bad})
    assert e.value.code == "byd_sai_kieu" and e.value.level == "REVIEW" and "sai kiểu" in str(e.value)
    assert isinstance(e.value, ValueError)              # qc_observe._prepare bắt ValueError → VÀNG, không gọi VLM


@pytest.mark.parametrize("env", (OFF, ON))
@pytest.mark.parametrize("empty", (None, "", [], {}, 0))
def test_empty_or_missing_byd_reads_as_none(env, empty):
    with mock.patch.dict(os.environ, env):
        assert lock_exceptions.for_shot({"byd": empty}) == {}
        assert lock_exceptions.shot_label({"byd": empty, "shot_no": 4}) == 4
        assert film_grammar._exception({"byd": empty}, 1, "jump") is None
