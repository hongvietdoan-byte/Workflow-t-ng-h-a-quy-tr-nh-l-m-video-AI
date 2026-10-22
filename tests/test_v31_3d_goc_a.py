"""C-3D-GOC-A (22/10) — bất biến R2 / R3 / R4 của khâu 3D (core/camera_invariants.py), sổ lỗi V31-GOC2/3/4.

Ba lớp test:
  1. BIẾN THỂ sinh bằng code (seed cố định): 5 bối cảnh giả lập hình học (mê cung #31, tháp + bậc thềm #33, phòng kín, ngoài trời,
     sàn bậc) × chỗ đứng / hướng / cỡ cảnh / góc / ống kính / chiều cao ngẫu nhiên. "Blender giả" = hàm sàn floor_at + mốc (đáy, đỉnh);
     oracle độc lập (plate_camera.project — phép chiếu thứ hai, không phải stage_grid.project mà module dùng).
  2. REPLAY 0 USD các ca gốc #31 / #33 bằng số trong tài liệu lỗi (DANH_GIA_P31…, DANH_GIA_P33…): cái cũ bị bắt, cái máy sinh ra qua.
  3. Công cụ báo cáo tools/camera_invariants.py trên CSDL tạm (chỉ đọc).
"""
import hashlib
import json
import math
import os
import random
import sqlite3
import subprocess
import sys
from unittest import mock

import pytest

from core import camera_invariants as ci
from core import plate_camera as pc
from core import prompt_formula as pf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAG_ON = mock.patch.dict(os.environ, {"FEATURE_WHITEBOX_HEIGHT_DUMMY": "1"})
FLAG_OFF = mock.patch.dict(os.environ, {"FEATURE_WHITEBOX_HEIGHT_DUMMY": ""})
ANGLES = ("eye", "slightly_high", "high", "low", "overhead")
SEEDS = (1, 2, 3, 4, 5)


# ---- bối cảnh giả lập (Blender giả) ---------------------------------------------------------------------------------------------
def _maze31(x, y):                       # lối đi z 0; ô cỏ (Fence001) cao 0,13 m — G49
    return 0.13 if (math.floor(x / 2) + math.floor(y / 2)) % 2 and abs(x) > 1 and abs(y) > 1 else 0.0


def _tower33(x, y):                      # thềm + cầu thang lên tháp: 5 bậc 0,3 m từ y = 5 tới y = 10 — B5
    return 0.0 if y < 5 else min(5, int(y - 5) + 1) * 0.3


def _room(x, y):                         # phòng kín 4 × 5 m — ngoài tường không có sàn
    return 0.0 if abs(x) <= 2 and abs(y) <= 2.5 else None


def _outdoor(x, y):
    return 0.0


def _stepped(x, y):                      # sàn bậc 0,3 m mỗi 1,5 m theo x
    return 0.3 * math.floor(x / 1.5)


SCENES = {
    "me_cung_31": (_maze31, [{"key": "thap", "name": "clock tower", "words": ["tower", "tháp"], "base": [0, 30, 0], "top": [0, 30, 42]},
                             {"key": "biet_thu", "name": "villa", "words": ["villa", "biệt thự"], "base": [-55, 0, 0], "top": [-55, 0, 12]}]),
    "thap_33": (_tower33, [{"key": "thap", "name": "clock tower", "words": ["tower", "tháp"], "base": [0, 15, 1.5], "top": [0, 15, 21.5]}]),
    "phong_kin": (_room, [{"key": "ke", "name": "bookshelf", "words": ["bookshelf", "kệ sách"], "base": [0, 2.4, 0], "top": [0, 2.4, 2.2]}]),
    "ngoai_troi": (_outdoor, [{"key": "cay", "name": "old tree", "words": ["tree", "cây"], "base": [8, 12, 0], "top": [8, 12, 9]}]),
    "san_bac": (_stepped, [{"key": "cot", "name": "stone pillar", "words": ["pillar", "cột"], "base": [-6, 6, 0], "top": [-6, 6, 5]}]),
}


def _variants(seed, n=120):
    rnd = random.Random(seed)
    for _ in range(n):
        scene = rnd.choice(sorted(SCENES))
        floor, marks = SCENES[scene]
        x, y = rnd.uniform(-1.8, 1.8), rnd.uniform(-2.2, 2.2)
        z = floor(x, y)
        yield {"scene": scene, "floor": floor, "marks": marks, "spot": [x, y, z if z is not None else 0.0],
               "facing": rnd.uniform(0, 360), "H": rnd.uniform(1.1, 2.0), "size": rnd.choice(sorted(pc.FRAMING)),
               "angle": rnd.choice(ANGLES), "side": rnd.choice(("left", "center", "right")), "lens": rnd.choice((None, None, 18, 28, 50, 85))}


def _cam(v):
    c = pc.camera_for({"size": v["size"], "angle": v["angle"], "side": v["side"], "lens": v["lens"]}, v["spot"], v["facing"], v["H"])
    return c["camera"]["location"], c["camera"]["look_at"], c["camera"]["lens"]


# ==== 1. biến thể ================================================================================================================
@pytest.mark.parametrize("seed", SEEDS)
def test_variants_camera_for_meets_r2_or_says_why(seed):
    """Bất biến R2 (cờ whitebox_height_dummy BẬT): mọi máy camera_for nghiêng trong dải của góc khai và người chiếm đúng % khung của cỡ
    cảnh theo HÌNH CHIẾU. Ngoại lệ duy nhất có chủ đích: giàn GAME_TPS (cúi 12° cố định) khai high/overhead → bộ kiểm NÓI ra (không im)."""
    with FLAG_ON:
        for v in _variants(seed):
            cam, aim, lens = _cam(v)
            found = ci.check_pitch(v["angle"], ci.pitch_of(cam, aim)) + ci.check_framing(v["size"], cam, aim, lens, v["spot"], v["H"])
            if v["size"] == "GAME_TPS" and v["angle"] in ("high", "overhead"):
                assert [f["code"] for f in found] == ["R2-PITCH"] and "P31-G3" in found[0]["errors"] and found[0]["fix"], v
            else:
                assert found == [], (v, found)


@pytest.mark.parametrize("seed", SEEDS)
def test_variants_old_high_camera_is_caught(seed):
    """Gốc cũ (cờ TẮT): máy high giữ khoảng cách NGANG → người nhỏ hơn cỡ cảnh 20–30 %; bộ kiểm bắt ở mọi biến thể high cỡ MLS → ECU
    (WS / EWS toàn thân: lệch nằm trong ±15 % — đo thực nghiệm, không bắt; TPS: giàn game)."""
    hit = 0
    with FLAG_OFF:
        for v in _variants(seed):
            if v["angle"] != "high" or v["size"] not in ("MLS", "MS", "MCU", "CU", "ECU"):
                continue
            cam, aim, lens = _cam(v)
            f = ci.check_framing(v["size"], cam, aim, lens, v["spot"], v["H"], angle="high")
            assert f and f[0]["code"] == "R2-FRAMING" and "quá xa" in f[0]["msg"], v
            hit += 1
    assert hit > 0


def test_flag_off_slightly_high_is_the_old_eye_camera():
    with FLAG_OFF:
        old = pc.camera_for({"size": "WS", "angle": "slightly_high"}, [0, 0, 0], 0, 1.75)
        eye = pc.camera_for({"size": "WS", "angle": "eye"}, [0, 0, 0], 0, 1.75)
    assert old["camera"]["location"] == eye["camera"]["location"]
    assert ci.check_pitch("slightly_high", old["pitch_deg"])[0]["code"] == "R2-PITCH"       # máy cũ không khớp mức khai → nói ra
    with FLAG_ON:
        new = pc.camera_for({"size": "WS", "angle": "slightly_high"}, [0, 0, 0], 0, 1.75)
    assert -12 <= new["pitch_deg"] <= -8 and ci.check_pitch("slightly_high", new["pitch_deg"]) == []


@pytest.mark.parametrize("seed", SEEDS)
def test_variants_landmark_sentence_follows_what_the_camera_sees(seed):
    """R3: câu "X rises in the background" bị bắt ⇔ máy không thấy X. Oracle: plate_camera.project (phép chiếu độc lập) trên đáy/giữa/đỉnh."""
    seen_cases = unseen_cases = 0
    for v in _variants(seed):
        cam, aim, lens = _cam(v)
        view = ci.view_of(cam, aim, lens, v["marks"])
        for m in v["marks"]:
            pts = [m["base"], [(a + b) / 2 for a, b in zip(m["base"], m["top"])], m["top"]]
            oracle = any(p is not None and 0 <= p[0] <= 1 and 0 <= p[1] <= 1 for p in (pc.project(cam, aim, lens, 9 / 16, q) for q in pts))
            text = f"The {m['words'][0]} rises in the background."
            got = [f for f in ci.text_vs_view(text, view) if f["code"] == "R3-NOT-IN-FRAME"]
            assert bool(got) == (not oracle), (v["scene"], m["key"], cam, aim)
            if got:
                assert got[0]["fix"].endswith("\"The " + m["name"] + " is outside this frame (not visible).\"")
            seen_cases += oracle
            unseen_cases += not oracle
    assert seen_cases and unseen_cases                              # cả hai nhánh đều được thử


@pytest.mark.parametrize("seed", SEEDS)
def test_variants_side_words_follow_the_projection(seed):
    checked = 0
    for v in _variants(seed, 200):
        cam, aim, lens = _cam(v)
        view = ci.view_of(cam, aim, lens, v["marks"])
        for m in v["marks"]:
            mid = pc.project(cam, aim, lens, 9 / 16, m["base"])
            if mid is None or not (0 <= mid[1] <= 1) or not (0.02 < mid[0] < 0.3 or 0.7 < mid[0] < 0.98):
                continue
            real = "left" if mid[0] < 0.5 else "right"
            for said in ("left", "right"):
                got = ci.text_vs_view(f"The {m['words'][0]} stands on the {said} of the frame.", view)
                assert any(f["code"] == "R3-SIDE" for f in got) == (said != real), (v, said, mid)
            checked += 1
    assert checked


@pytest.mark.parametrize("height,expect", [(0.03, False), (0.13, True), (0.3, True)])
def test_variants_floor_step_between_camera_and_feet(height, expect):
    """R2 sàn (G49): mép sàn giữa máy và chân, cao hơn chỗ đứng ≥ 5 cm, lọt khung → nói ra; 3 cm (sàn hơi gồ) → không."""
    def floor(x, y):
        return height if 1.0 < y < 1.6 else 0.0                     # dải cao trước mặt nhân vật (về phía máy)
    for size in ("WS", "MLS", "MS"):
        c = pc.camera_for({"size": size, "angle": "eye"}, [0, 0, 0], 0, 1.68)
        cam, aim, lens = c["camera"]["location"], c["camera"]["look_at"], c["camera"]["lens"]
        if cam[1] < 1.7:
            continue                                                # máy đứng trong dải: không phải ca này
        got = [f for f in ci.check_floor(cam, aim, lens, [0, 0, 0], 1.68, floor) if "mép sàn" in f["msg"]]
        assert bool(got) == expect, (size, height, got)


@pytest.mark.parametrize("scene", sorted(SCENES))
def test_variants_feet_and_camera_on_the_measured_floor(scene):
    floor, _ = SCENES[scene]
    rnd = random.Random(scene)
    for _ in range(40):
        x, y = rnd.uniform(-1.8, 1.8), rnd.uniform(-2.2, 2.2)
        zf = floor(x, y)
        if zf is None:
            continue
        c = pc.camera_for({"size": "MS", "angle": "eye"}, [x, y, zf], rnd.uniform(0, 360), 1.7)
        cam, aim, lens = c["camera"]["location"], c["camera"]["look_at"], c["camera"]["lens"]
        ok = ci.check_floor(cam, aim, lens, [x, y, zf], 1.7, floor)
        assert not any("chân nhân vật" in f["msg"] for f in ok)
        lifted = ci.check_floor(cam, aim, lens, [x, y, zf + 0.4], 1.7, floor)
        assert any("lơ lửng" in f["msg"] for f in lifted)            # chân không trên sàn đo được → nói ra
        if floor(cam[0], cam[1]) is None:
            assert any(f["level"] == ci.KHONG_RO and "dưới máy" in f["msg"] for f in ok)   # máy ngoài phòng: không đoán


def test_camera_too_low_over_a_raised_floor():
    def floor(x, y):
        return 1.2 if y > 1.0 else 0.0                              # máy đứng trên bục cao 1,2 m
    c = pc.camera_for({"size": "MS", "angle": "eye"}, [0, 0, 0], 0, 1.7)
    cam, aim, lens = c["camera"]["location"], c["camera"]["look_at"], c["camera"]["lens"]
    got = ci.check_floor(cam, aim, lens, [0, 0, 0], 1.7, floor)
    assert any("cách sàn dưới nó" in f["msg"] and "P31-G49" in f["errors"] for f in got)


@pytest.mark.parametrize("pct,expect", [(60, True), (30, False), (35, False), (45, True)])
def test_frame_pct_sentence_follows_projection(pct, expect):
    """G2: câu "N% of the frame height" ↔ hình chiếu (WS ≈ 55 % toàn thân); câu thay sinh từ hình chiếu."""
    c = pc.camera_for({"size": "WS", "angle": "eye"}, [0, 0, 0], 0, 1.7)
    cam, aim, lens = c["camera"]["location"], c["camera"]["look_at"], c["camera"]["lens"]
    share = ci.body_share(cam, aim, lens, 9 / 16, [0, 0, 0], 1.7) * 0.6     # đo trên máy xa hơn: 60 % của WS ≈ 33 %
    got = ci.check_frame_pct(f"her whole body about {pct}% of frame height, never resize her", share)
    assert bool(got) == expect
    if got:
        assert ci.pct_sentence(share) in got[0]["fix"] and "P31-G2" in got[0]["errors"]


# ==== 2. replay ca gốc #31 / #33 (0 USD, số trong tài liệu lỗi) ===================================================================
def _aim_from(cam, bearing_deg, pitch_deg, dist=2.0):
    b, p = math.radians(bearing_deg), math.radians(pitch_deg)
    return [cam[0] + math.sin(b) * dist * math.cos(p), cam[1] + math.cos(b) * dist * math.cos(p), cam[2] + dist * math.sin(p)]


@pytest.mark.parametrize("shot,pitch", [(28, 17.3), (35, 11.1)])
def test_replay_p31_g3_eye_camera_tilted(shot, pitch):
    cam = [0.0, 0.0, 10.85]
    f = ci.check_pitch("eye", ci.pitch_of(cam, _aim_from(cam, 90, pitch)))
    assert f and f[0]["code"] == "R2-PITCH" and "P31-G3" in f[0]["errors"] and "ngửa" in f[0]["msg"]


def test_replay_p31_g49_shot13_camera_over_grass_too_close():
    """#31 shot 13 (16/10): máy cao 1,9 m, cúi −27°, cách Kelly (1,68 m) 0,9 m, đứng trên ô cỏ 0,13 m. Bắt: quá sát cho cỡ + cúi quá dải eye.
    Máy camera_for (cờ BẬT) cùng chỗ / cùng cỡ: qua mọi bất biến R2."""
    spot, H = [0.55, 0.1, 0.0], 1.68
    cam = [0.55, 1.0, 1.9]
    aim = _aim_from(cam, 180, -27)
    found = ci.check_pitch("eye", ci.pitch_of(cam, aim)) + ci.check_framing("MS", cam, aim, 35, spot, H, angle="eye")
    assert {f["code"] for f in found} == {"R2-PITCH", "R2-FRAMING"}
    fr = next(f for f in found if f["code"] == "R2-FRAMING")
    assert "nghiêng -27°" in fr["msg"] and "P31-G49" in fr["errors"] and "độ nghiêng trước" in fr["fix"]
    with FLAG_ON:
        c = pc.camera_for({"size": "MS", "angle": "eye"}, spot, 0, H)
    cam2, aim2, lens2 = c["camera"]["location"], c["camera"]["look_at"], c["camera"]["lens"]
    assert ci.check_pitch("eye", ci.pitch_of(cam2, aim2)) == []
    assert ci.check_framing("MS", cam2, aim2, lens2, spot, H) == []
    assert ci.check_floor(cam2, aim2, lens2, spot, H, _maze31) == []


def test_replay_p33_a10_high_is_not_one_fixed_tilt():
    """#33: 'high' chúc cố định 30° → nền chỉ còn sàn đá; không có mức hơi cao. Cờ BẬT: slightly_high cúi 10°, high giữ % khung."""
    with FLAG_ON:
        sh = pc.camera_for({"size": "WS", "angle": "slightly_high"}, [0, 0, 0], 0, 1.2)
        hi = pc.camera_for({"size": "MS", "angle": "high"}, [0, 0, 0], 0, 1.2)
    assert ci.check_pitch("slightly_high", sh["pitch_deg"]) == [] and sh["pitch_deg"] > -12
    assert ci.check_framing("MS", hi["camera"]["location"], hi["camera"]["look_at"], hi["camera"]["lens"], [0, 0, 0], 1.2) == []
    with FLAG_OFF:
        old = pc.camera_for({"size": "MS", "angle": "high"}, [0, 0, 0], 0, 1.2)
    assert ci.check_framing("MS", old["camera"]["location"], old["camera"]["look_at"], old["camera"]["lens"], [0, 0, 0], 1.2)


def test_replay_p31_g26_tower_behind_the_camera():
    """#31 S31: nền là tường / lan can, tháp sau lưng máy; motion + D6 "the tower rising in the background" → clip có tháp đen."""
    floor, marks = SCENES["me_cung_31"]
    cam = [0.0, 2.0, 1.6]
    aim = [0.0, -3.0, 1.4]                                           # nhìn về NAM, tháp ở BẮC (y = 30)
    view = ci.view_of(cam, aim, 35, marks)
    assert view["thap"]["in"] is False
    t = ci.text_vs_view("Kelly walks along the rail, the tower rising in the background.", view, "image_prompt")
    m = ci.motion_vs_view("The tower rising in the background as Kelly walks.", view, "static")
    assert [f["code"] for f in t] == ["R3-NOT-IN-FRAME"] and "P31-G26" in t[0]["errors"]
    assert [f["code"] for f in m] == ["R3-MOTION-UNSEEN"]
    assert ci.text_vs_view("No tower in frame; Kelly walks along the rail.", view) == []          # câu phủ định không bị bắt


def test_replay_p31_g11_motion_reveals_what_the_first_frame_shows():
    doors = [{"key": "cua", "name": "two wooden doors", "words": ["doors", "door", "cửa"], "base": [0, 4, 0], "top": [0, 4, 2.2]}]
    cam, aim = [0, 0, 1.5], [0, 4, 1.2]
    view = ci.view_of(cam, aim, 28, doors)
    got = ci.motion_vs_view("The doors are not yet visible; as she turns, the two doors are revealed.", view, "pan")
    assert got and got[0]["code"] == "R3-MOTION-REVEAL" and "P31-G11" in got[0]["errors"] and "two wooden doors" in got[0]["fix"]


def test_replay_p33_b5_tower_top_cut_and_b3_placed_by_words():
    floor, marks = SCENES["thap_33"]
    cam = [-3.0, 3.0, 0.7]                                           # máy thấp ở thềm nhìn lên cầu thang
    low = ci.view_of(cam, [-1.0, 15.0, 4.0], 24, marks)
    assert low["thap"]["in"] and not low["thap"]["top_in"]
    got = ci.text_vs_view("The top of the clock tower glows against the clouds.", low)
    assert any(f["code"] == "R3-TOP-CUT" and "P33-B5" in f["errors"] for f in got)
    wide = ci.view_of([0.0, -40.0, 3.0], [0.0, 15.0, 10.0], 24, marks)
    assert wide["thap"]["top_in"]
    got = ci.text_vs_view("A swirling vortex eye hangs right above the tower top.", wide)
    rel = [f for f in got if f["code"] == "R3-RELATIVE"]
    assert rel and "P33-B3" in rel[0]["errors"] and "exactly where the render shows it" in rel[0]["fix"]
    assert not any(f["code"] == "R3-SIDE" for f in got)               # "right above" không phải "bên phải"


def test_replay_p31_g9_its_whole_body_is_not_a_pose():
    issues = pf.lint_image("Medium close-up of Kelly holding the SKORP, a golden aura along its whole body.", {"size": "MCU"})
    assert not any(i["part"] == "khung_hinh" and i["level"] == "red" for i in issues)
    issues = pf.lint_image("Medium close-up of Kelly, her whole body visible.", {"size": "MCU"})
    assert any(i["part"] == "khung_hinh" and i["level"] == "red" for i in issues)


def test_replay_p33_b7_vietnamese_names_get_a_replacement():
    got = ci.vi_leaks("RỐI ĐỎ A waves at Tháp Đồng Hồ.", {"Tháp Đồng Hồ": "the Clock Tower"})
    assert [(f["numbers"]["said"], f["numbers"]["replace"]) for f in got] == [("RỐI ĐỎ A", "ROI DO A"), ("Tháp Đồng Hồ", "the Clock Tower")]
    assert all("P33-B7" in f["errors"] for f in got)
    assert ci.vi_leaks("ROI DO A waves at the Clock Tower.") == []


def test_replay_p33_b10_reference_subject_outside_the_guard():
    guard = "The cats in the reference only give the motion and timing, never draw cats."
    assert ci.ref_leaks(guard + " The puppets dance like the reference video.", ["cats"]) == []
    got = ci.ref_leaks(guard + " The puppets dance like the cats.", ["cats"])
    assert len(got) == 1 and got[0]["code"] == "R3-REF-LEAK" and "like the reference video" in got[0]["fix"]


def test_replay_p31_g18_byd_still_but_camera_pans():
    shot2 = {"size": "MS", "angle": "eye", "camera_move": "pan", "characters": ["KELLY"],
             "byd": {"may": {"co": "MS", "do_cao": "ngang", "goc": "ngang", "chuyen_dong": "dung_yen"},
                     "thanh_phan": [{"vat": "KELLY", "vai": "chinh"}]}}
    got = ci.byd_vs_fields(shot2)
    assert [f["code"] for f in got] == ["R4-MOVE"] and "P31-G18" in got[0]["errors"]
    shot2["camera_move"] = "static"
    assert ci.byd_vs_fields(shot2) == []


@pytest.mark.parametrize("field,value,code", [("size", "WS", "R4-SIZE"), ("angle", "low", "R4-ANGLE"), ("characters", ["SKORP"], "R4-CAST")])
def test_byd_vs_each_field(field, value, code):
    shot = {"size": "MS", "angle": "eye", "camera_move": "static", "characters": ["KELLY"],
            "byd": {"may": {"co": "MS", "do_cao": "ngang", "goc": "ngang", "chuyen_dong": "dung_yen"},
                    "thanh_phan": [{"vat": "KELLY", "vai": "chinh"}]}}
    shot[field] = value
    assert code in [f["code"] for f in ci.byd_vs_fields(shot)]


def test_replay_p33_a12_one_line_for_a_project_without_byd():
    shots = [{"shot": i} for i in range(1, 23)]
    got = ci.byd_coverage(shots)
    assert len(got) == 1 and got[0]["numbers"] == {"missing": 22, "total": 22} and "P33-A12" in got[0]["errors"]
    assert ci.byd_coverage([{"shot": 1, "byd": {}}]) == []


def test_missing_input_is_said_not_guessed():
    assert ci.check_pitch("eye", None)[0]["level"] == ci.KHONG_RO
    assert ci.check_framing("XYZ", [0, 0, 1], [0, 1, 1], 35, [0, 1, 0], 1.7)[0]["level"] == ci.KHONG_RO
    assert ci.check_frame_pct("about 50% of the frame height", None)[0]["level"] == ci.KHONG_RO
    assert ci.check_pitch("ots", -40.0) == []                       # qua vai: không có dải chung (nói trong docstring)


def test_one_source_for_bands():
    """Dải nghiêng lấy ngưỡng có sẵn (stage_grid.RULE_TH L7 + whitebox), không hằng mới."""
    from core import stage_grid as sg, whitebox as wb
    assert ci.pitch_band("eye")[:2] == (-sg.RULE_TH["L7_ngang"][0], wb.EYE_MAX_DEG)
    assert ci.pitch_band("high")[:2] == (sg.RULE_TH["L7_tren_dau"][0], sg.RULE_TH["L7_cui"][0])
    assert ci.pitch_band("slightly_high")[:2] == (-wb.SLIGHTLY_HIGH_RANGE[1], -wb.SLIGHTLY_HIGH_RANGE[0])


# ==== 3. công cụ báo cáo (chỉ đọc) ================================================================================================
def _db(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE scenes (id INTEGER PRIMARY KEY, project_id INTEGER, idx INTEGER, title TEXT, state TEXT, data TEXT)")
    cam = [0.0, 0.0, 10.85]
    rows = [
        (1, {"angle": "eye", "camera_move": "pan", "motion_en": {"hanh_dong": "RỐI ĐỎ A waves."},
             "stage_camera": {"location": cam, "look_at": _aim_from(cam, 90, 17.3), "lens": 35},
             "byd": {"may": {"co": "MS", "chuyen_dong": "dung_yen"}, "thanh_phan": [{"vat": "KELLY", "vai": "chinh"}]}}),
        (2, {"angle": "eye", "size": "MS"}),
    ]
    for idx, d in rows:
        conn.execute("INSERT INTO scenes (project_id, idx, data) VALUES (31, ?, ?)", (idx, json.dumps(d, ensure_ascii=False)))
    conn.commit()
    conn.close()


def test_tool_reports_and_never_writes(tmp_path):
    db = tmp_path / "m.sqlite"
    _db(str(db))
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    out = tmp_path / "r.json"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "camera_invariants.py"), "--project", "31", "--db", str(db),
                        "--json", str(out)], capture_output=True, text=True, env=dict(os.environ, PYTHONUTF8="1"), cwd=ROOT)
    assert r.returncode == 1, r.stdout + r.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    codes = {f["code"] for f in res["per_shot"]["1"]}
    assert {"R2-PITCH", "R4-MOVE", "R3-VI-TEXT"} <= codes
    assert [f["code"] for f in res["project_findings"]] == ["R4-NO-BYD"] and "1/2 shot" in res["project_findings"][0]["msg"]
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "camera_invariants.py"), "--project", "31", "--db",
                        str(tmp_path / "none.sqlite")], capture_output=True, text=True, env=dict(os.environ, PYTHONUTF8="1"), cwd=ROOT)
    assert r.returncode == 2 and "không đọc được" in r.stdout
