"""V3.1 M2.1 (C-M21): BYĐ v2 theo docs/V3_1_M2_1_M2_2_THIET_KE_2026-10-20.md (phần M2.1) — `byd_v`, `vat[]` object, nhóm `khung`, provenance
`_p`, mức BLOCK / REVIEW / WARN (chỉ ghi: cờ `byd_v2_levels` TẮT = byd_kiem y cũ; không chặn gen), hàm đọc chung `shot_intent.read`
(value, provenance, warn) + `byd_of`; mọi caller đọc BYĐ trong core/ đi qua adapter (test AST, ngoại lệ có lý do). Không gọi model, 0 USD."""
import ast
import json
import os
import pathlib
from unittest import mock

import pytest

from core import shot_intent as S

ROOT = pathlib.Path(__file__).resolve().parent.parent
ON = mock.patch.dict(os.environ, {"FEATURE_BYD_V2_LEVELS": "1", "FEATURE_SHOT_INTENT": "1"})
OFF = mock.patch.dict(os.environ, {"FEATURE_BYD_V2_LEVELS": "", "FEATURE_SHOT_INTENT": "1"})


def _v2(**over):
    b = {"byd_v": 2, "shot": 7, "thanh_phan": [{"vat": "KELLY", "kho_id": 12, "vai": "chinh", "vung": "giua"}],
         "may": {"co": "MS", "do_cao": "ngang", "goc": "ngang", "chuyen_dong": "dung_yen"},
         "noi_chon": {"kho_id": 41, "spot": None, "trong_nha": None},
         "vat": [{"vat": "BOM_KEO", "kho_id": 367, "nguoi": "KELLY", "cach": "nem"}],
         "khung": {"moc_nen": {"kho_id": 88, "y_do": "trong_khung", "ly_do": ""}},
         "_p": {"by": "director", "revision": 1}}
    b.update(over)
    return b


def _v1():
    return {"shot": 3, "thanh_phan": [{"vat": "KELLY", "vai": "chinh", "vung": "giua"}],
            "may": {"co": "MS", "do_cao": "ngang", "goc": "ngang", "chuyen_dong": "dung_yen"}, "noi_chon": {"kho_id": 41},
            "vat": ["AWM"]}


def _codes(issues, muc="do"):
    return sorted(i["truong"] for i in issues if i["muc"] == muc)


# ---- cờ ----------------------------------------------------------------------------------------------------------------------
def test_flag_registered_off_and_in_golden_inputs():
    from core import features
    assert S.LEVELS_FLAG in features.FEATURES and features.FEATURES[S.LEVELS_FLAG]["verified"] is False
    with OFF:
        assert not S.levels_enabled()
    golden = json.load(open(ROOT / "tests" / "golden" / "package_inputs.json", encoding="utf-8"))
    for kind in ("image", "video"):
        assert golden[kind]["flags"][S.LEVELS_FLAG] is False


def test_registered_in_areas():
    areas = json.load(open(ROOT / "devsys" / "areas.json", encoding="utf-8"))
    hit = [a for a in areas["areas"] if "tests/test_v31_m21_byd_v2.py" in a["tests"]]
    assert hit and any(S.LEVELS_FLAG in a["flags"] for a in hit)


# ---- schema v2 ---------------------------------------------------------------------------------------------------------------
def test_version():
    assert S.version(_v2()) == 2 and S.version(_v1()) == 1 and S.version(None) is None and S.version(["x"]) is None


def test_v2_valid_is_clean():
    assert S.validate(_v2(), conn=None) == [{"muc": "vang", "truong": "kho_id", "loi": "chưa kiểm mã Kho (không có kết nối CSDL)"}]


def test_v1_unchanged_and_khung_is_v2_only():
    assert _codes(S.validate(_v1())) == []
    assert "khung" in _codes(S.validate(dict(_v1(), khung={"moc_nen": {"kho_id": 1, "y_do": "trong_khung"}})))


def test_unknown_byd_v_is_block():
    assert "byd_v" in _codes(S.validate(_v2(byd_v=3)))


@pytest.mark.parametrize("vat,field", [
    (["BOM_KEO"], "vat[0]"),                                                        # v2: chuỗi không còn hợp lệ
    ([{"vat": "BOM_KEO", "nguoi": "KELLY", "cach": "nem"}], "vat[0].kho_id"),
    ([{"vat": "BOM_KEO", "kho_id": 3, "nguoi": "SKORP", "cach": "cam"}], "vat[0].nguoi"),
    ([{"vat": "BOM_KEO", "kho_id": 3, "nguoi": "KELLY", "cach": "bay"}], "vat[0].cach"),
    ([{"kho_id": 3, "cach": "dat"}], "vat[0].vat"),
])
def test_v2_vat_errors_block(vat, field):
    assert field in _codes(S.validate(_v2(vat=vat)))


def test_v2_vat_without_owner_is_fine_when_put_down():
    assert _codes(S.validate(_v2(vat=[{"vat": "THUNG", "kho_id": 5, "cach": "dat"}]))) == []


def test_bien_the_is_unchecked_warning_not_block():
    issues = S.validate(_v2(vat=[{"vat": "BOM_KEO", "kho_id": 3, "nguoi": "KELLY", "cach": "nem", "bien_the": "curved_deployed"}]))
    assert _codes(issues) == [] and any(i["truong"] == "vat[0].bien_the" and "bien_the_khong_kiem_duoc" in i["loi"] for i in issues)


@pytest.mark.parametrize("khung,field", [({"moc_nen": {"kho_id": 88, "y_do": "giua"}}, "khung.moc_nen.y_do"),
                                         ({"moc_nen": {"y_do": "trong_khung"}}, "khung.moc_nen.kho_id"),
                                         ("x", "khung")])
def test_khung_errors(khung, field):
    assert field in _codes(S.validate(_v2(khung=khung)))


def test_trong_nha_and_provenance_types():
    assert "noi_chon.trong_nha" in _codes(S.validate(_v2(noi_chon={"kho_id": 41, "trong_nha": "co"})))
    assert "_p.by" in _codes(S.validate(_v2(_p={"by": "robot"})))


# ---- mức BLOCK / REVIEW / WARN -----------------------------------------------------------------------------------------------
def test_assess_maps_do_vang():
    got = S.assess(_v2(vat=["BOM_KEO"]))
    assert {i["level"] for i in got} >= {"BLOCK", "WARN"}
    assert all(i["level"] in S.LEVELS for i in got)
    assert S.level_of({"muc": "do"}) == "BLOCK" and S.level_of({"muc": "vang"}) == "WARN"


def test_v1_never_blocks_for_missing_v2_fields():
    assert [i for i in S.assess(_v1()) if i["level"] == "BLOCK"] == []


def test_v2_dang_unchecked_is_review():
    b = _v2(thanh_phan=[{"vat": "KELLY", "kho_id": 12, "vai": "chinh", "vung": "giua", "dang": "ghost_form"}])
    assert any(i["level"] == "REVIEW" and i["truong"] == "thanh_phan[0].dang" for i in S.assess(b))


# ---- hàm đọc chung -----------------------------------------------------------------------------------------------------------
def test_read_provenance():
    assert S.read({"byd": _v2()}, "noi_chon.kho_id") == (41, "byd_v2", None)
    assert S.read({"byd": _v1()}, "noi_chon.kho_id") == (41, "byd_v1", None)
    v, p, w = S.read({}, "noi_chon.kho_id")
    assert (v, p) == (None, "thieu") and w
    v, p, w = S.read({"byd": _v1()}, "khung.moc_nen", default={})
    assert (v, p) == ({}, "thieu") and "v1" in w
    assert S.read({"byd": "hỏng"}, "vat")[1] == "thieu"


def test_read_vat_goes_through_the_v1_v2_parser():
    assert S.read({"byd": _v1()}, "vat")[0] == [{"vat": "AWM", "_v": 1}]
    assert S.read({"byd": _v2()}, "vat")[0][0]["kho_id"] == 367
    assert S.read({"byd": {"shot": 1}}, "vat") == ([], "thieu", "BYĐ v1 thiếu `vat`")


def test_byd_of():
    b = _v1()
    assert S.byd_of({"byd": b}) is b and S.byd_of({"byd": []}) is None and S.byd_of(None) is None


# ---- chỉ ghi ----------------------------------------------------------------------------------------------------------------
def _plan(byd):
    return {"scenes": [{"idx": 1, "shots": [{"size": "MS", "byd": byd}]}]}


def test_settle_records_levels_only_with_the_flag():
    from core import director_byd
    with OFF, mock.patch("core.diag.record"):
        obj = _plan(_v2(vat=[{"vat": "X", "kho_id": 1, "cach": "dat", "bien_the": "a"}]))
        director_byd.settle(None, 1, obj, client=None)
        kiem = obj["scenes"][0]["shots"][0]["byd_kiem"]
    assert "muc_v2" not in kiem
    with ON, mock.patch("core.diag.record"):
        obj = _plan(_v2(vat=[{"vat": "X", "kho_id": 1, "cach": "dat", "bien_the": "a"}]))
        director_byd.settle(None, 1, obj, client=None)
        kiem = obj["scenes"][0]["shots"][0]["byd_kiem"]
    assert kiem["muc_v2"]["WARN"] >= 1 and kiem["muc_v2"]["BLOCK"] == 0 and kiem["byd_v"] == 2


# ---- mọi caller đọc BYĐ qua adapter -------------------------------------------------------------------------------------------
ALLOWED = {
    # (tệp, hàm): lý do được đọc thẳng
    ("core/director_byd.py", "problems"): "Đạo diễn điền / sửa: BYĐ là đầu ra của chính module này",
    ("core/director_byd.py", "build_repair_prompt"): "đề sửa chép nguyên BYĐ",
    ("core/director_byd.py", "_own_number"): "điền số shot vào BYĐ (ghi)",
    ("core/director_byd.py", "_parse"): "đọc câu trả lời của Đạo diễn",
    ("core/director_byd.py", "settle"): "vòng sửa ghi BYĐ",
    ("core/director_two_pass.py", "estimate_text"): "như trên",
    ("core/change_review.py", "build_prompt"): "đề rà chép nguyên BYĐ cho agent",
    ("core/film_grammar.py", "warnings"): "kiểm KIỂU BYĐ do Claude viết (sai kiểu → VÀNG, không im lặng) — cần giá trị thô",
    ("core/shot_lessons.py", "_cli_source"): "BYĐ sai kiểu phải báo 'BYĐ hỏng' — cần giá trị thô",
}


def _byd_reads():
    hits = []
    for path in sorted((ROOT / "core").rglob("*.py")):
        rel = str(path.relative_to(ROOT))
        if rel == "core/shot_intent.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        parents = {}
        for node in ast.walk(tree):
            for ch in ast.iter_child_nodes(node):
                parents[ch] = node

        def func_of(n):
            while n in parents:
                n = parents[n]
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    return n.name
            return "<module>"
        for node in ast.walk(tree):
            key = None
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" and node.args \
                    and isinstance(node.args[0], ast.Constant) and node.args[0].value == "byd":
                key = node
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value == "byd" \
                    and isinstance(node.ctx, ast.Load):
                key = node
            if key is not None:
                hits.append((rel, func_of(node), node.lineno))
    return hits


def test_every_core_reader_goes_through_the_adapter():
    bad = [h for h in _byd_reads() if (h[0], h[1]) not in ALLOWED]
    assert bad == [], "đọc BYĐ thẳng ngoài shot_intent (dùng shot_intent.read / byd_of / vat_items): " + repr(bad)


def test_allowlist_has_no_dead_entries():
    used = {(h[0], h[1]) for h in _byd_reads()}
    assert set(ALLOWED) <= used, sorted(set(ALLOWED) - used)
