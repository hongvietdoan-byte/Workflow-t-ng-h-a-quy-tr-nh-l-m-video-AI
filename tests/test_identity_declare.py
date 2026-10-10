"""core/identity_declare (A18 / A20, K0b): khóa nhận diện bằng chữ — có / thiếu / thiếu màu / sai màu, đồng nghĩa màu, họa tiết bỏ qua."""
import pytest

from core import identity_declare as idd
from tests import golden

KELLY = "yellow tracksuit, black spiked choker"
KELLY_MUST_KEEP = ("dark brown chin-length bob with straight blunt bangs (hair down, never tied), black choker, white crop top under a "
                   "bright yellow zip-up track jacket with a high collar, grey sleeve stripes with small black stars and thin black edge "
                   "lines, matching bright yellow track pants with a black side stripe, white sneakers, youthful face with light makeup")


def _by(rows):
    return {r["mon"]: r for r in rows}


def test_declare_items_colors_sign():
    d = _by(idd.declare_from_text(KELLY))
    assert d["tracksuit"]["mau_chinh"] == ["yellow"]
    assert d["choker"]["mau_chinh"] == ["black"] and d["choker"]["dau_hieu"] == "spiked"
    assert all(x["nguon"] == "suy" for x in d.values())


def test_all_present():
    rows = idd.check(idd.declare_from_text(KELLY), "Kelly in her yellow-white-black tracksuit with black spiked choker")
    assert [r["trang_thai"] for r in rows] == ["co", "co"]
    assert all(r["muc"] is None for r in rows)
    assert rows[1]["dau_hieu_thay"] is True


def test_missing_choker_is_red_when_blocking_is_on():
    r = _by(idd.check(idd.declare_from_text(KELLY), "Kelly in a yellow tracksuit runs across the plaza", chan_do=True))
    assert r["choker"]["trang_thai"] == "thieu" and r["choker"]["muc"] == "do"
    assert r["tracksuit"]["trang_thai"] == "co"


def test_wrong_color_is_red_only_when_blocking_is_on():
    # A18 (kế hoạch dòng 33): "thiếu / sai màu → ĐỎ" chỉ SAU KHI đo báo nhầm → chưa bật chặn thì sai màu cũng VÀNG
    for chan, muc in ((True, "do"), (False, "vang")):
        r = _by(idd.check(idd.declare_from_text(KELLY), "Kelly in a red tracksuit and a black choker", chan_do=chan))
        assert r["tracksuit"]["trang_thai"] == "sai_mau" and r["tracksuit"]["mau_thay"] == ["red"] and r["tracksuit"]["muc"] == muc


def test_color_synonyms_and_missing_color():
    r = _by(idd.check(idd.declare_from_text(KELLY), "Kelly in a golden track suit with a jet-black choker"))
    assert r["tracksuit"]["trang_thai"] == "co" and r["choker"]["trang_thai"] == "co"
    r = _by(idd.check(idd.declare_from_text(KELLY), "Kelly in her tracksuit and black choker", chan_do=True))
    assert r["tracksuit"]["trang_thai"] == "thieu_mau" and r["tracksuit"]["muc"] == "do"


def test_must_keep_merges_tracksuit_and_skips_patterns():
    decl = idd.declare_from_text(KELLY_MUST_KEEP)
    d = _by([x for x in decl if not x.get("hoa_tiet")])
    assert d["tracksuit"]["mau_chinh"] == ["yellow"]          # track jacket + track pants → một món
    assert d["hair"]["mau_chinh"] == ["brown"] and "face" not in d
    assert any(x.get("hoa_tiet") for x in decl)
    r = _by(idd.check(decl, "Kelly with short dark bob, yellow tracksuit, black choker"))
    assert r["hair"]["trang_thai"] == "co"                    # 'dark' khớp nâu đậm, không tính sai màu
    assert r["sneakers"]["trang_thai"] == "thieu"


def test_vietnamese_description():
    d = _by(idd.declare_from_text("váy trắng trễ vai rách tả tơi; tóc đen dài rối, nửa dưới chuyển đỏ; giày cao gót đỏ"))
    assert d["dress"]["mau_chinh"] == ["white"]
    assert d["hair"]["mau_chinh"] == ["black", "red"]
    assert d["heels"]["mau_chinh"] == ["red"]
    r = _by(idd.check(list(d.values()), "a creature in a torn black dress with long black hair, red high heels"))
    assert r["dress"]["trang_thai"] == "sai_mau" and r["hair"]["trang_thai"] == "co" and r["heels"]["trang_thai"] == "co"


def test_segment_keeps_other_figure_hair_off_kelly():
    p = ("Kelly in the foreground standing at the rim of an ancient stone well, a dark blurred shadow figure with long trailing black "
         "hair glides past her")
    seg = idd.segment(p, {"KELLY": ["kelly"]})
    assert "black" not in seg["KELLY"]
    seg = idd.segment("Kelly small seated on the left, a white-haired red-tipped female creature in a torn black dress kneeling",
                      {"KELLY": ["kelly"], "D2": ["creature"]})
    assert "dress" in seg["D2"] and "dress" not in seg["KELLY"]


def test_hyphenated_compound_items():
    d = idd.declare_from_text("váy trắng; tóc đen")
    r = _by(idd.check(d, "shifting from black-haired tattered-white-dress form"))
    assert r["dress"]["trang_thai"] == "co" and r["hair"]["trang_thai"] == "co"


GOLDEN = [c for c in golden.load_cases() if "identity_declare" in (c.get("ky_vong") or {})]


def test_golden_has_identity_cases():
    assert len(GOLDEN) >= 2


@pytest.mark.parametrize("case", GOLDEN, ids=[c["id"] for c in GOLDEN])
def test_golden_identity(case):
    """Ca hồi quy K0b (#24): khóa Kho của nhân vật × đoạn prompt nói về nó → đúng trạng thái từng món."""
    exp = case["ky_vong"]["identity_declare"]
    assert exp.get("vat"), f"{case['id']}: ky_vong.identity_declare thiếu 'vat' (khóa sân khấu trong BYĐ thanh_phan)"
    seg = idd.segment(case["goi"]["image_prompt"], {exp["nhan_vat"]: [exp["nhan_vat"].lower()]})
    view = idd.byd_view(case.get("byd"), exp["vat"])                    # lọc theo BYĐ của ca (thẩm định 4 #1)
    rows = idd.check(idd.declare_from_text(exp["khoa"]), seg[exp["nhan_vat"]], view=view)
    assert {r["mon"]: r["trang_thai"] for r in rows} == exp["trang_thai"]
    assert all(r.get("ly_do") for r in rows if r["trang_thai"] == "khong_can")      # lọc phải nói lý do


def test_golden_has_anti_false_alarm_cases():
    """Thẩm định 4 #1: ≥ 2 ca chống báo nhầm — giày ở cỡ cận, quay lưng không đòi mặt nạ / choker; không lọc thì báo nhầm thật."""
    want = {"chong_bao_nham_giay_o_can_mcu": {"sneakers"}, "chong_bao_nham_lung_mat_na_choker": {"mask", "choker"}}
    got = {c["id"]: c for c in GOLDEN}
    assert set(want) <= set(got)
    for cid, items in want.items():
        exp = got[cid]["ky_vong"]["identity_declare"]
        assert {m for m, v in exp["trang_thai"].items() if v == "khong_can"} == items
        raw = idd.check(idd.declare_from_text(exp["khoa"]), got[cid]["goi"]["image_prompt"])
        assert {r["mon"] for r in raw if r["trang_thai"] == "thieu"} == items


# --- Rà soát quy ước 7 (10/10): 11 lỗi — mỗi lỗi một test ---

def test_r1_non_ascii_english_must_keep_stays_english():
    mons = [d["mon"] for d in idd.declare_from_text("black choker, yellow tracksuit — never tied")]
    assert "choker" in mons and "tracksuit" in mons


def test_r2_pattern_word_not_substring_of_vang():
    decl = idd.declare_from_text("áo khoác vàng")
    assert not any(d.get("hoa_tiet") for d in decl)


def test_r3_missing_input_is_reported_not_silent():
    rows = idd.check(idd.declare_from_text(""), "Kelly in a yellow tracksuit")
    assert rows[0]["trang_thai"] == "khong_co_khoa" and rows[0]["muc"] == "do"
    assert idd.summary(rows)["khong_co_khoa"] == 1
    assert _by(idd.declare_from_text("choker đen"))["choker"]["mau_chinh"] == ["black"]
    assert idd.unrecognized(idd.declare_from_text("áo khoác vàng")) == ["áo khoác vàng"]


def test_r4_dryrun_reports_character_not_in_kho():
    import importlib.util
    import os
    import sqlite3
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "dryrun_k0b_p24.py")
    spec = importlib.util.spec_from_file_location("dryrun_k0b_p24", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert os.path.isabs(mod.SPECS)
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE assets (id INTEGER, profile TEXT, description TEXT)")
    rows = mod.identity_rows(conn, ["KELLY", "NGƯỜI LẠ"], "Kelly in a yellow tracksuit", {"kelly"})
    loi = {r["nhan_vat"]: r["loi"] for r in rows}
    assert loi == {"NGƯỜI LẠ": "khong_co_STAGE_KEY", "KELLY": "khong_co_trong_Kho"}


def test_dryrun_identity_rows_filter_by_byd():
    """Thẩm định 4 #1: người gọi chạy khô truyền BYĐ → món phần dưới ở MCU thành 'khong_can' (có lý do), không còn 'thieu'."""
    import importlib.util
    import json
    import os
    import sqlite3
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "dryrun_k0b_p24.py")
    spec = importlib.util.spec_from_file_location("dryrun_k0b_p24", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE assets (id INTEGER, profile TEXT, description TEXT)")
    conn.execute("INSERT INTO assets VALUES (23, ?, '')", (json.dumps({"must_keep": KELLY_MUST_KEEP}),))
    prompt = "Kelly close up, dark brown bob, black choker, white crop top under a yellow track jacket"
    before = {m["mon"]: m["trang_thai"] for m in mod.identity_rows(conn, ["KELLY"], prompt, {"kelly"})[0]["mon"]}
    row = mod.identity_rows(conn, ["KELLY"], prompt, {"kelly"}, byd=BYD_MCU)[0]
    after = {m["mon"]: m["trang_thai"] for m in row["mon"]}
    assert before["sneakers"] == "thieu" and after["sneakers"] == "khong_can"
    assert row["tong"]["khong_can"] == 1 and row["loc_byd"]["co"] == "MCU"


def test_dryrun_old_shot4_prompt_uses_same_byd_filter():
    """Rà độc lập #5: prompt CŨ shot 4 phải lọc bằng cùng BYĐ shot 4 như prompt mới (so cũ ↔ mới không lẫn hiệu ứng lọc)."""
    import importlib.util
    import json
    import os
    import sqlite3
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "dryrun_k0b_p24.py")
    spec = importlib.util.spec_from_file_location("dryrun_k0b_p24", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE assets (id INTEGER, profile TEXT, description TEXT)")
    conn.execute("INSERT INTO assets VALUES (23, ?, '')", (json.dumps({"must_keep": KELLY_MUST_KEEP}),))
    old = {"characters": ["KELLY"], "image_prompt": "Kelly close up, dark brown bob, black choker, white crop top, yellow track jacket"}
    row = mod.old_prompt_identity(conn, old, BYD_MCU)[0]
    assert {m["mon"]: m["trang_thai"] for m in row["mon"]}["sneakers"] == "khong_can" and row["loc_byd"]["co"] == "MCU"


def test_default_mode_is_yellow_until_false_alarms_are_measured():
    """A18 + thẩm định 4 #1: chưa đo báo nhầm (docs/NHAN_BAO_NHAM_A18_2026-10-10.md) → CHAN_DO = False: 'thieu' / 'thieu_mau' là
    VÀNG; bật chặn (chan_do=True) mới ĐỎ. 'sai_mau' cũng theo chế độ (A18); 'khong_co_khoa' (thiếu đầu vào) ĐỎ ở cả hai chế độ."""
    assert idd.CHAN_DO is False
    assert "A18" in idd.__doc__ and "CHAN_DO" in idd.__doc__
    decl = idd.declare_from_text(KELLY)
    prompt = "Kelly in her tracksuit runs across the plaza"
    soft = _by(idd.check(decl, prompt))
    hard = _by(idd.check(decl, prompt, chan_do=True))
    assert (soft["choker"]["trang_thai"], soft["choker"]["muc"]) == ("thieu", "vang")
    assert (soft["tracksuit"]["trang_thai"], soft["tracksuit"]["muc"]) == ("thieu_mau", "vang")
    assert (hard["choker"]["muc"], hard["tracksuit"]["muc"]) == ("do", "do")
    assert idd.check([], "x")[0]["muc"] == "do" and idd.check([], "x", chan_do=True)[0]["muc"] == "do"


BYD_MCU = {"shot": 1, "thanh_phan": [{"vat": "kelly", "vai": "chinh", "vung": "giua", "thay": "mat"}], "may": {"co": "MCU"}}


def test_byd_filter_framing_drops_lower_body_items_with_reason():
    decl = idd.declare_from_text(KELLY_MUST_KEEP)
    view = idd.byd_view(BYD_MCU, "kelly")
    assert view == {"vat": "kelly", "co": "MCU", "thay": ["mat"], "trong_khung": True}
    r = _by(idd.check(decl, "Kelly, short dark bob, black choker, white crop top, yellow track jacket", view=view))
    assert r["sneakers"]["trang_thai"] == "khong_can" and r["sneakers"]["muc"] is None and "MCU" in r["sneakers"]["ly_do"]
    assert r["tracksuit"]["trang_thai"] == "co" and r["choker"]["trang_thai"] == "co"
    assert idd.summary(list(r.values()))["khong_can"] == 1
    ws = idd.byd_view(dict(BYD_MCU, may={"co": "WS"}), "kelly")
    assert _by(idd.check(decl, "Kelly, short dark bob", view=ws))["sneakers"]["trang_thai"] == "thieu"   # WS thấy cả người → vẫn đòi
    ms = idd.byd_view(dict(BYD_MCU, may={"co": "MS"}), "kelly")
    r = _by(idd.check(idd.declare_from_text("black belt, white heels, black stockings"), "Kelly", view=ms))
    assert (r["belt"]["trang_thai"], r["heels"]["trang_thai"], r["stockings"]["trang_thai"]) == ("thieu", "khong_can", "khong_can")


def test_byd_filter_unknown_region_or_framing_still_required():
    """Món không biết vùng thân (glitch, món ngoài ITEMS) và cỡ cảnh không biết → VẪN đòi, kèm ghi chú `khong_loc` (không im lặng)."""
    view = idd.byd_view(dict(BYD_MCU, may={"co": "ECU"}), "kelly")
    r = _by(idd.check([{"mon": "glitch", "mau_chinh": ["red"], "nguon": "suy"}, {"mon": "cape", "mau_chinh": ["red"], "nguon": "suy"}],
                      "Kelly's eyes", view=view))
    assert r["glitch"]["trang_thai"] == "thieu" and "vùng" in r["glitch"]["khong_loc"]
    assert r["cape"]["trang_thai"] == "thieu" and "vùng" in r["cape"]["khong_loc"]
    view = idd.byd_view(dict(BYD_MCU, may={"co": None}), "kelly")
    r = _by(idd.check(idd.declare_from_text("white sneakers"), "Kelly", view=view))
    assert r["sneakers"]["trang_thai"] == "thieu" and "cỡ" in r["sneakers"]["khong_loc"]


def test_byd_filter_back_view_drops_front_only_items():
    decl = idd.declare_from_text("black face mask, black choker, yellow tracksuit")
    back = idd.byd_view({"thanh_phan": [{"vat": "kelly", "vai": "chinh", "thay": "lung"}], "may": {"co": "WS"}}, "kelly")
    r = _by(idd.check(decl, "Kelly from behind in a yellow tracksuit", view=back))
    assert r["mask"]["trang_thai"] == "khong_can" and r["choker"]["trang_thai"] == "khong_can" and "lưng" in r["mask"]["ly_do"]
    assert r["tracksuit"]["trang_thai"] == "co"
    side = idd.byd_view({"thanh_phan": [{"vat": "kelly", "vai": "chinh", "thay": "lung|nghieng"}], "may": {"co": "WS"}}, "kelly")
    assert _by(idd.check(decl, "Kelly in a yellow tracksuit", view=side))["mask"]["trang_thai"] == "thieu"   # nghiêng thấy mặt


def test_byd_filter_character_not_in_frame():
    gone = idd.byd_view({"thanh_phan": [{"vat": "gieng", "vai": "chinh"}], "may": {"co": "WS"}}, "kelly")
    assert gone["trong_khung"] is False
    rows = idd.check(idd.declare_from_text(KELLY), "the well at night", view=gone)
    assert {r["trang_thai"] for r in rows} == {"khong_can"} and all("khung" in r["ly_do"] for r in rows)
    banned = idd.byd_view({"thanh_phan": [{"vat": "kelly", "vai": "khong_duoc_co"}], "may": {"co": "WS"}}, "kelly")
    assert banned["trong_khung"] is False
    assert idd.byd_view(None, "kelly") is None                          # không có BYĐ → không lọc


def test_byd_filter_missing_stage_key_or_cast_is_not_silent():
    """Rà độc lập #1: thiếu khóa sân khấu / BYĐ chưa có thanh_phan → KHÔNG lọc 'ngoài khung' (vẫn đòi, kèm khong_loc); khóa so
    không phân biệt hoa/thường."""
    byd = {"may": {"co": "WS"}, "thanh_phan": [{"vat": "kelly", "vai": "chinh", "thay": "mat"}]}
    decl = idd.declare_from_text("black choker, white sneakers")
    for view in (idd.byd_view(byd, None), idd.byd_view(byd, ""), idd.byd_view({"may": {"co": "WS"}}, "kelly")):
        rows = idd.check(decl, "nothing here", view=view)
        assert {r["trang_thai"] for r in rows} == {"thieu"}, rows
        assert all(r.get("khong_loc") for r in rows)
    v = idd.byd_view(byd, "Kelly")
    assert v["trong_khung"] is True and v["thay"] == ["mat"]
    assert idd.check(idd.declare_from_text(KELLY), "Kelly", view=None)[0]["trang_thai"] == "thieu"


def test_body_table_follows_stage_grid_framing():
    from core import stage_grid as sg
    for co in sg.FRAMING:
        assert idd.framing_body(co) == sg.FRAMING[co][0]
    assert idd.framing_body("XL") is None and idd.framing_body(None) is None
    assert set(idd.BODY_FROM_TOP) <= set(idd.ITEMS) and set(idd.FRONT_ONLY) <= set(idd.ITEMS)


def test_r5_vietnamese_compared_with_diacritics():
    assert "belt" not in _by(idd.declare_from_text("khăn choàng dài màu đen"))
    d = _by(idd.declare_from_text("mắt xanh dương, tóc đến vai màu nâu"))
    assert d["eyes"]["mau_chinh"] == ["blue"] and "face" not in d
    assert d["hair"]["mau_chinh"] == ["brown"]


def test_r6_item_outside_items_no_keyerror():
    r = idd.check([{"mon": "cap", "mau_chinh": ["red"]}], "Kelly in a red cap")
    assert r[0]["trang_thai"] == "co"


def test_r7_color_after_noun():
    decl = idd.declare_from_text("yellow tracksuit")
    assert idd.check(decl, "Kelly wears a tracksuit in bright yellow")[0]["trang_thai"] == "co"
    assert idd.check(decl, "a tracksuit in the plaza, red light")[0]["trang_thai"] == "thieu_mau"


def test_r8_main_color_required():
    decl = [{"mon": "hair", "mau_chinh": ["black", "red"], "nguon": "suy"}]
    assert idd.check(decl, "long red hair")[0]["trang_thai"] == "thieu_mau"
    r = idd.check(decl, "long black hair")[0]
    assert r["trang_thai"] == "co" and r["mau_phu_thieu"] == ["red"]


def test_r9_mask_is_its_own_item():
    r = _by(idd.check(idd.declare_from_text("black face mask"), "her youthful black face"))
    assert r["mask"]["trang_thai"] == "thieu"


def test_r10_segment_boundaries():
    seg = idd.segment("Kelly and a ghost girl in a white dress", {"KELLY": ["kelly"]})
    assert "dress" not in seg["KELLY"]
    seg = idd.segment("Kelly waves, Miami street glows red", {"MIA": ["mia"], "K": ["kelly"]})
    assert "glows" not in seg["MIA"]


def test_r11_two_colors_sign_window_and_false_synonyms():
    assert len(idd.declare_from_text("red white black dress")[0]["mau_chinh"]) == 2
    r = _by(idd.check(idd.declare_from_text(KELLY), "Kelly in yellow tracksuit and black choker, spiked hair"))
    assert r["choker"]["dau_hieu_thay"] is False
    assert _by(idd.declare_from_text("ash-blonde hair"))["hair"]["mau_chinh"] != ["grey"]
    assert _by(idd.declare_from_text("rose gold choker"))["choker"]["mau_chinh"] == ["yellow"]


# --- K0b phần 2 (A20): ô `khai_bao_chu` trong hồ sơ Kho (assets.profile JSON, cùng chỗ must_keep — không migration) ---

YN1_KBC = [{"mon": "belt", "dong_nghia": ["spiked belt", "waist belt"], "mau_chinh": ["black"], "mau_dong_nghia": {"black": ["charcoal"]},
            "dau_hieu": "red triangle buckle", "cach_viet": ["red triangular buckle"], "hoa_tiet": ["gai kim loại"]},
           {"mon": "dress", "dong_nghia": ["gown"], "mau_chinh": ["white"], "dau_hieu": None, "cach_viet": [], "hoa_tiet": []}]


def test_kbc_schema_valid_and_errors_reported():
    assert idd.validate_khai_bao_chu(YN1_KBC) == []
    bad = [{"mon": "", "mau_chinh": []}, {"mon": "hat", "mau_chinh": ["red", "blue", "green"]}, {"mon": "cap", "mau_chinh": ["rouge"]},
           {"mon": "scarf", "mau_chinh": ["red"], "dau_hieu": ["a", "b"]}, {"mon": "veil", "mau_chinh": ["red"], "cach_viet": ["x y"]},
           {"mon": "boots", "mau_chinh": ["red"], "dong_nghia": ["đai"]}, {"mon": "gloves", "mau_chinh": ["red"], "dong_nghia": ["ab"]},
           {"mon": "cape", "mau_chinh": ["red"], "mau_dong_nghia": {"blue": ["navy"]}}, {"mon": "hat", "mau_chinh": ["red"], "la": 1},
           "khong_phai_bang"]
    got = idd.validate_khai_bao_chu(bad)
    loi = " | ".join(f"{i['mon']}: {i['loi']}" for i in got)
    for word in ("mon", "hat", "rouge", "scarf", "veil", "boots", "gloves", "cape", "la"):
        assert word in loi, word
    assert all(i["muc"] == "do" for i in got)
    assert idd.validate_khai_bao_chu("x")[0]["muc"] == "do"


def test_declare_prefers_kbc_over_must_keep():
    prof = {"must_keep": "red belt, white dress, long black hair", "khai_bao_chu": YN1_KBC}
    decl, issues = idd.declare_from_profile(prof)
    d = _by(decl)
    assert d["belt"]["mau_chinh"] == ["black"] and d["belt"]["nguon"] == "khai_bao_chu"
    assert d["hair"]["nguon"] == "suy"                                   # món chưa có ô → vẫn kiểm theo suy …
    vang = [i for i in issues if i["muc"] == "vang"]
    assert [i["mon"] for i in vang] == ["hair"] and "một lần" in vang[0]["loi"]   # … và VÀNG nhắc điền, không im lặng


def test_declare_without_kbc_is_yellow_per_item():
    decl, issues = idd.declare_from_profile({"must_keep": KELLY})
    assert {d["nguon"] for d in decl} == {"suy"}
    assert sorted(i["mon"] for i in issues if i["muc"] == "vang") == ["choker", "tracksuit"]
    decl, issues = idd.declare_from_profile({})
    assert decl == [] and issues and issues[0]["muc"] == "vang"         # check([]) sẽ ĐỎ khong_co_khoa
    assert idd.check(decl, "Kelly")[0]["trang_thai"] == "khong_co_khoa"


def test_invalid_kbc_item_is_red_and_falls_back():
    prof = {"must_keep": "red belt", "khai_bao_chu": [{"mon": "belt", "mau_chinh": ["rouge"]}]}
    decl, issues = idd.declare_from_profile(prof)
    assert any(i["muc"] == "do" for i in issues)
    assert _by(decl)["belt"]["nguon"] == "suy"


def test_check_uses_kbc_synonyms_and_sign_wording():
    decl, _ = idd.declare_from_profile({"khai_bao_chu": YN1_KBC})
    r = _by(idd.check(decl, "a creature in a white gown, a charcoal waist belt with a red triangular buckle"))
    assert r["belt"]["trang_thai"] == "co" and r["belt"]["dau_hieu_thay"] is True
    assert r["dress"]["trang_thai"] == "co"
    r = _by(idd.check(decl, "a creature in a white gown, a red waist belt"))
    assert r["belt"]["trang_thai"] == "sai_mau"                          # #24 shot 5/6: prompt viết đai đỏ theo mô tả Kho cũ


def test_kbc_item_matches_canonical_item_words():
    """Món khai_bao_chu 'spiked belt' che món suy 'belt' (cùng loại ITEMS) → khi so prompt cũng phải nhận từ của loại đó ('belt'),
    không báo ĐỎ oan 'thieu' khi prompt viết 'black belt with spikes' (đường must_keep cũ ra 'co')."""
    kbc = [{"mon": "spiked belt", "mau_chinh": ["black"], "dau_hieu": "spikes"}]
    decl, issues = idd.declare_from_profile({"khai_bao_chu": kbc, "must_keep": "black belt with spikes"})
    assert [d["mon"] for d in decl] == ["spiked belt"] and issues == []
    rows = idd.check(decl, "Kelly wears a black belt with spikes.")
    assert [(r["mon"], r["trang_thai"]) for r in rows] == [("spiked belt", "co")]
    assert idd.check(decl, "Kelly wears a red belt.")[0]["trang_thai"] == "sai_mau"     # vẫn bắt sai màu
    assert idd.check(decl, "Kelly wears a black dress.")[0]["trang_thai"] == "thieu"   # không có thắt lưng → vẫn thiếu


def test_description_color_conflict_is_yellow():
    """#24 shot 5/6: mô tả Kho cũ 'đai đỏ ngang eo' lệch ảnh mẫu (đai gai đen + khóa tam giác đỏ) → VÀNG trước khi viết prompt."""
    decl, _ = idd.declare_from_profile({"khai_bao_chu": YN1_KBC})
    got = idd.color_conflicts("váy trắng rách; đai đỏ ngang eo", decl)
    assert [(g["mon"], g["muc"]) for g in got] == [("belt", "vang")]
    assert "red" in got[0]["loi"] and "black" in got[0]["loi"]
    assert idd.color_conflicts("váy trắng; đai đen gai", decl) == []
    assert idd.color_conflicts("đai ngang eo", decl) == []               # mô tả không nói màu → không có gì để so
    assert idd.color_conflicts("", decl) == []


def test_kbc_survives_profile_save():
    """set_profile chỉ giữ PROFILE_KEYS → ô khai_bao_chu phải được GIỮ khi người dùng lưu hồ sơ (không mất dữ liệu), và kiểm khi ghi."""
    from core import assets
    from core.db import connect
    conn = connect()
    aid = assets.create(conn, "FF", "character", "YEU NU 1")
    conn.execute("UPDATE assets SET profile=? WHERE id=?",
                 ('{"must_keep": "red belt", "khai_bao_chu": [{"mon": "belt", "mau_chinh": ["black"]}]}', aid))
    assets.set_profile(conn, aid, {"identity": "x", "must_keep": "black belt"}, approved=True)
    assert assets.get_profile(conn, aid)["khai_bao_chu"] == [{"mon": "belt", "mau_chinh": ["black"]}]
    assets.set_profile(conn, aid, {"must_keep": "black belt", "khai_bao_chu": YN1_KBC}, approved=True)
    assert assets.get_profile(conn, aid)["khai_bao_chu"] == YN1_KBC
    with pytest.raises(assets.AssetError):
        assets.set_profile(conn, aid, {"must_keep": "x", "khai_bao_chu": [{"mon": "belt", "mau_chinh": ["rouge"]}]}, approved=True)
    assert assets.get_profile(conn, aid)["khai_bao_chu"] == YN1_KBC     # ghi hỏng → không đổi gì
    other = assets.create(conn, "FF", "character", "KHAC")
    assets.set_profile(conn, other, {"must_keep": "black belt"}, approved=True)
    assert "khai_bao_chu" not in assets.get_profile(conn, other)        # không tự sinh ô rỗng cho hồ sơ chưa có


# --- Thẩm định 5 (#4/#5, A25): ca hồi quy segment + tham số hóa dự án của chạy khô / bảng gán nhãn ---

P24_SHOT7 = ("Point-of-view shot from Kelly's eyes low on the ground, looking slightly up, Free Fire in-game 3D render style, the faceless "
             "dark female creature standing in front of an ancient eight-sided stone well in the center of the frame, turning her head "
             "to stare straight at the camera, engulfed in flickering red digital glitch noise mid-transformation, shifting from "
             "black-haired tattered-white-dress form into white-haired red-tipped comic-style crosshatch form, foggy plaza at night")


def test_segment_shared_marker_belongs_to_both_forms():
    """docs/NHAN_BAO_NHAM_A18 cuối tệp: #24 shot 7 hai dạng yêu nữ cùng từ đánh dấu 'creature' → trước đây chữ thuộc dạng 1 (thứ tự
    tên), dạng 2 rỗng → mọi món dạng 2 'thieu' (báo nhầm do tách đoạn). Từ đánh dấu y hệt (không phân biệt được) → mệnh đề thuộc CẢ HAI."""
    mk = {"YÊU NỮ TÀ LINH DẠNG 1": ["creature", "yêu nữ"], "YÊU NỮ TÀ LINH DẠNG 2": ["creature", "yêu nữ"]}
    seg = idd.segment(P24_SHOT7, mk)
    assert "faceless dark female creature" in seg["YÊU NỮ TÀ LINH DẠNG 2"]
    assert "white-haired" in seg["YÊU NỮ TÀ LINH DẠNG 2"]
    assert seg["YÊU NỮ TÀ LINH DẠNG 1"] == seg["YÊU NỮ TÀ LINH DẠNG 2"]
    seg = idd.segment(P24_SHOT7, dict(mk, KELLY=["kelly"]))              # chữ trước 'creature' vẫn là của Kelly, không chia cho yêu nữ
    assert "Point-of-view" in seg["KELLY"] and "Point-of-view" not in seg["YÊU NỮ TÀ LINH DẠNG 2"]


def test_segment_longer_marker_wins_same_start():
    """#22: 'MAXIM KL' và 'MAXIM' cùng bắt đầu ở một chỗ — từ đánh dấu DÀI hơn (cụ thể hơn) thắng, không theo thứ tự tên."""
    mk = {"MAXIM": ["maxim"], "MAXIM KL": ["maxim kl", "maxim"]}
    seg = idd.segment("MAXIM KL in the male Red Dinosaur outfit, black shark-tooth mask", mk)
    assert "mask" in seg["MAXIM KL"] and seg["MAXIM"] == ""
    seg = idd.segment("Maxim in a silver bomber jacket", mk)            # chỉ 'maxim' → hai tên trùng từ → của cả hai (không đoán)
    assert "bomber" in seg["MAXIM"] and "bomber" in seg["MAXIM KL"]


def _load_tool(name):
    import importlib.util
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dryrun_project_config_paths_anchor_repo_not_cwd(tmp_path, monkeypatch):
    import os
    monkeypatch.chdir(tmp_path)
    mod = _load_tool("dryrun_k0b_p24")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    c22, c24 = mod.project_config(22), mod.project_config("24")
    assert c22["pid"] == 22 and c22["out"] == os.path.join(root, "data_out", "k0b_p22") and os.path.isabs(c22["out"])
    assert c24["out"] == os.path.join(root, "data_out", "k0b_p24") and c24["specs"] == mod.SPECS and mod.PID == 24
    assert c22["specs"] is None and c22["old_prompt"] is None and c22["outfit"] == {"MAXIM KL": 416, "KELLY KL": 417}
    with pytest.raises(SystemExit, match="#99 chưa có cấu hình"):
        mod.project_config(99)
    with pytest.raises(SystemExit, match="phải là số"):
        mod.project_config("abc")


def test_dryrun_spec_from_scene_without_hand_specs():
    """#22 không có shot_specs → spec dựng từ chữ kịch bản; mọi ô ghi suy; không người → thanh_phan rỗng (validate ĐỎ, không bịa)."""
    from core import shot_intent
    mod = _load_tool("dryrun_k0b_p24")
    cfg = mod.project_config(22)
    data = {"size": "WS", "angle": "high", "characters": ["MAXIM KL", "KELLY KL"],
            "blocking": "Maxim Khủng Long frame-left, Kelly Khủng Long frame-right, both facing camera, mid dance step"}
    spec, suy = mod.spec_from_scene(7, data, cfg)
    assert (spec["shot"], spec["co"], spec["do_cao"], spec["goc"]) == (7, "WS", "cao", "cui")
    assert {c["vat"]: c.get("vung") for c in spec["thanh_phan"]} == {"maxim": "trai", "kelly": "phai"}
    assert any("angle" in s for s in suy) and any("thanh_phan[maxim]" in s for s in suy)
    b = shot_intent.from_shot_spec(spec)
    b["noi_chon"]["kho_id"] = 263                                      # build_byd điền từ location_asset
    assert not [i for i in shot_intent.validate(b) if i["muc"] == "do"]
    empty, suy0 = mod.spec_from_scene(2, {"size": "CU", "angle": "ots", "characters": [], "blocking": "no person in frame"}, cfg)
    assert empty["thanh_phan"] == [] and empty["goc"] is None and any("rỗng" in s for s in suy0)
    assert any(i["truong"] == "thanh_phan" and i["muc"] == "do" for i in shot_intent.validate(shot_intent.from_shot_spec(empty)))


def test_dryrun_outfit_lock_keeps_character_identity_items_only():
    """#22 'MAXIM KL': khóa = tóc/mặt/mắt của Maxim (Kho 33) + đồ của bộ Khủng Long (Kho 416) — không đòi sneakers của Maxim, không lấy
    'tóc' từ mô tả trang phục. Trang phục không có trong Kho → ĐỎ 'khong_co_trong_Kho'."""
    import json
    import sqlite3
    mod = _load_tool("dryrun_k0b_p24")
    cfg = mod.project_config(22)
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE assets (id INTEGER, profile TEXT, description TEXT)")
    conn.execute("INSERT INTO assets VALUES (33, ?, '')", (json.dumps({"must_keep": "messy silver-white hair, black sneakers"}),))
    conn.execute("INSERT INTO assets VALUES (416, NULL, 'khẩu trang đen in răng cá mập; tóc đỏ của người mẫu')")
    row = mod.identity_rows(conn, ["MAXIM KL"], "MAXIM KL with silver-white hair and a black shark-tooth mask", {"maxim"}, cfg=cfg)[0]
    got = {m["mon"]: (m["trang_thai"], m.get("mau_chinh")) for m in row["mon"]}
    assert got["hair"] == ("co", ["white", "grey"]) and got["mask"][0] == "co" and "sneakers" not in got
    assert row["trang_phuc_kho_id"] == 416 and "trang_phuc_416" in row["nguon_khoa"]
    conn.execute("DELETE FROM assets WHERE id=416")
    assert mod.identity_rows(conn, ["MAXIM KL"], "MAXIM KL", {"maxim"}, cfg=cfg)[0]["loi"] == "khong_co_trong_Kho"


def test_nhan_bao_nham_balanced_pick_and_paths(tmp_path, monkeypatch):
    """A25: bảng gộp #22 + #24 chia đều; dự án này thiếu thì bù từ dự án kia; trong một dự án lấy xoay vòng theo shot. Dữ liệu chạy
    khô thiếu → SystemExit nói rõ (không bảng câm)."""
    import os
    monkeypatch.chdir(tmp_path)
    mod = _load_tool("nhan_bao_nham_a18")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert mod.data_dir(22) == os.path.join(root, "data_out", "k0b_p22")
    a = [{"shot": s, "i": i} for s in (1, 2) for i in range(10)]          # #22: 20 mục, 2 shot
    b = [{"shot": 1, "i": i} for i in range(6)]                           # #24: 6 mục
    got = mod.pick({22: a, 24: b}, 20)
    assert len(got) == 20 and sum(1 for p, _ in got if p == 24) == 6      # #24 chỉ có 6 → #22 bù 14
    assert {it["shot"] for p, it in got if p == 22}.issuperset({1, 2})
    assert [it["shot"] for p, it in got if p == 22][:2] == [1, 2]          # xoay vòng shot, không dồn shot đầu
    even = mod.pick({22: a, 24: [{"shot": 1, "i": i} for i in range(20)]}, 30)
    assert sum(1 for p, _ in even if p == 22) == 15 and sum(1 for p, _ in even if p == 24) == 15
    with pytest.raises(SystemExit, match="chưa chạy khô"):
        mod.load_summary(77)
    assert "A25" in mod.NGUONG and "n ≥ 30" in mod.NGUONG and "#22 + #24" in mod.NGUONG
