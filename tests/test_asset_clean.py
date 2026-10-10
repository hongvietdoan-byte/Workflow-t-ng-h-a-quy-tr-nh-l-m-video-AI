"""K1a R1 — ảnh mẫu Kho bẩn / mô tả Kho lệch ảnh mẫu (`core/asset_clean.py`, kế hoạch kiểm soát mục 4b dòng 4–5)."""
import json
import os

from core import asset_clean as ac

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# hồ sơ #418 (CSDL thật 10/10): must_keep đúng ảnh mẫu (đai gai đen + khóa tam giác đỏ), mô tả Kho cũ ghi "đai đỏ ngang eo"
MK_418 = ("faceless smooth black face with two glowing red eyes, long messy black hair turning red in the lower half, white "
          "off-the-shoulder dress torn to jagged shreds at the hem, black thorny vine belt with a red triangle buckle, black arms "
          "wrapped in black thorny vines with red claw nails, black stockings fading to red down the legs, red high heels, constant "
          "red glitch noise around wrists and legs")
MO_TA_418 = ("Nữ, mặt đen trơn không nét mặt, hai mắt đỏ phát sáng; tóc đen dài rối, nửa dưới chuyển đỏ; váy trắng trễ vai rách tả tơi "
             "gấu răng cưa, đai đỏ ngang eo; hai tay đen có gai/vân đen bám, móng đỏ; tất đen chuyển đỏ dần xuống chân, giày cao gót "
             "đỏ; quanh cổ tay và chân có hiệu ứng nhiễu glitch đỏ thường trực. Look in-game Free Fire 3D.")
KBC_418_BELT = [{"mon": "belt", "dong_nghia": ["thorny vine belt"], "mau_chinh": ["black"], "dau_hieu": "red triangle buckle"}]
MK_23 = ("dark brown chin-length bob with straight blunt bangs (hair down, never tied), black choker, white crop top under a bright "
         "yellow zip-up track jacket with a high collar, grey sleeve stripes with small black stars and thin black edge lines, matching "
         "bright yellow track pants with a black side stripe, white sneakers, youthful face with light makeup")
MO_TA_23 = ("[ff.garena.com] Nhân vật: Vận Động Viên. (giới tính nữ, 17 tuổi, sinh nhật 01/04). Thời thơ ấu, cô là một đứa trẻ hồn "
            "nhiên sống cùng với mẹ nuôi. Kelly luôn chạy rất nhanh, và đến thời trung học, huấn luyện viên điền kinh đã phát hiện "
            "tài năng của cô. Kỹ năng Phát Bắn Gia Tốc: Chạy nước rút trong 4 giây để kích hoạt.")
GIENG = {"must_keep": "old stone well with a wooden roof and a rope bucket"}


def _codes(rows):
    return [(r["ma"], r["muc"]) for r in rows]


def test_enum_matches_error_table():
    with open(os.path.join(ROOT, "devsys", "error_types.json"), encoding="utf-8") as fh:
        r1 = next(t for t in json.load(fh)["types"] if t["id"] == "R1")
    assert r1["claude_khai"][0]["enum"] == list(ac.THAY)


def test_dirty_well_image_is_yellow():
    """#24 job 623: ảnh giếng `1.png` có máu + tóc → không có trong hồ sơ giếng → VÀNG, ảnh chưa sạch."""
    rows = ac.check([{"loai": "mau", "mo_ta": "vết máu trên thành giếng"}, {"loai": "toc", "mo_ta": "tóc rủ trên miệng giếng"}],
                    GIENG)
    assert _codes(rows) == [("ngoai_ho_so", "vang"), ("ngoai_ho_so", "vang")]
    assert ac.verdict(rows) == "vang"


def test_things_in_profile_pass():
    rows = ac.check([{"loai": "toc", "mo_ta": "long black hair"}, {"loai": "khac", "mo_ta": "red glitch noise"}],
                    {"must_keep": MK_418})
    assert rows == []
    assert ac.verdict(rows) == "qua"


def test_other_person_and_clutter_always_yellow():
    rows = ac.check([{"loai": "nguoi_khac", "mo_ta": "mảnh ảnh người khác ở mép phải"},
                     {"loai": "nen_roi", "mo_ta": "nét vẽ khoanh đỏ quanh tóc"}], {"must_keep": MK_418}, MO_TA_418)
    assert ("ngoai_ho_so", "vang") in _codes(rows)
    assert [r["loai"] for r in rows if r["ma"] == "ngoai_ho_so"] == ["nguoi_khac", "nen_roi"]


def test_missing_or_bad_declaration_is_yellow_not_silent():
    assert _codes(ac.check(None, GIENG)) == [("chua_khai", "vang")]
    assert _codes(ac.check([{"loai": "vet_ban", "mo_ta": "x"}, "khong_phai_bang"], GIENG)) == [("ngoai_enum", "vang")] * 2
    assert _codes(ac.check([], {})) == [("khong_co_ho_so", "vang")]


def test_418_red_belt_description_mismatch():
    """Ca #418: mô tả Kho 'đai đỏ' lệch ảnh mẫu (khai_bao_chu: đai đen + khóa tam giác đỏ) → VÀNG mo_ta_lech."""
    rows = ac.check([], {"must_keep": MK_418, "khai_bao_chu": KBC_418_BELT}, MO_TA_418)
    lech = [r for r in rows if r["ma"] == "mo_ta_lech"]
    assert [(r["mon"], r["muc"]) for r in lech] == [("belt", "vang")]
    assert "red" in lech[0]["loi"] and "black" in lech[0]["loi"]
    # chưa có khai_bao_chu: must_keep (đai gai đen) vẫn bắt
    assert [r["mon"] for r in ac.check([], {"must_keep": MK_418}, MO_TA_418) if r["ma"] == "mo_ta_lech"] == ["belt"]
    assert [r for r in ac.check([], {"must_keep": MK_418}, MO_TA_418.replace("đai đỏ", "đai đen")) if r["ma"] == "mo_ta_lech"] == []


def test_kelly_description_matches_no_false_alarm():
    """0 báo nhầm trên #23 Kelly (mô tả Kho là cốt truyện, không nói màu món)."""
    assert ac.check([], {"must_keep": MK_23}, MO_TA_23) == []


def test_clean_state_is_recorded_not_blocking():
    p = {"must_keep": MK_418}
    st = ac.ref_status(p, "data/assets/418/1.jpg")
    assert st["trang_thai"] == "chua_duyet" and st["goi_nhan"] is False and st["chan"] is False   # cờ TẮT: chỉ ghi, không chặn
    p2 = ac.with_state(p, "data/assets/418/1.jpg", "sach", nguoi="user", ngay="2026-10-10")
    assert ac.KEY not in p                                             # hàm thuần: không sửa hồ sơ gốc
    st2 = ac.ref_status(p2, "data\\assets\\418\\1.jpg")                # đường dẫn Windows / POSIX là một ảnh
    assert st2["trang_thai"] == "sach" and st2["goi_nhan"] is True
    assert ac.ref_status(p2, "data/assets/418/3.jpg")["goi_nhan"] is False
    assert ac.ref_status(p2, "data/assets/418/3.jpg", chan=True)["chan"] is True
    try:
        ac.with_state(p, "x.png", "sạch")
    except ValueError:
        pass
    else:
        raise AssertionError("trạng thái ngoài enum phải báo lỗi")
