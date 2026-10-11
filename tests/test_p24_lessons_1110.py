"""Bài học duyệt ảnh #24 (người dùng 11/10: "rút kinh nghiệm tính toán, đánh giá tương tự cho các dự án sau") — kiểm bằng code ở chỗ
đo được, mức VÀNG (không chặn) trừ khi đã có lớp đỏ. Mỗi lớp một nhóm test; dữ liệu là bản rút gọn của #24 (không đọc data/)."""
import json
import os
import sqlite3

import pytest

from core import change_audit, features, prompt_formula as pf, shot_lessons as sl, stage_facts as sf
from tests import golden

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _case(name):
    return next(c for c in golden.stage_facts_cases() if c["name"] == name)


# ---- (1) thấy-được theo độ cao máy: blocking cũng vào prompt ảnh → cũng phải quét ---------------------------------------------
SHOT5 = _case("p24_shot5_blocking_never_inside")


def test_negated_clause_is_not_a_contradiction():
    facts = sf.derive({"stage_camera": SHOT5["stage_camera"]})["facts"]
    assert sf.contradictions(SHOT5["image_prompt"], facts) == []
    assert sf.contradictions("The inside of the well is not visible from here.", facts) == []
    # phủ định ở mệnh đề KHÁC / không gắn với cụm khớp không cứu câu trái sự thật (rà 11/10: 6 câu từng lọt)
    for s in ("Kelly, not scared, peers into the dark inside of the old well.", "Kelly peers into the well without fear.",
              "Kelly peers into the well with no hesitation.", "No one sees Kelly peering into the well.",
              "Kelly cannot stop peering into the well.", "Kelly never blinks while peering into the well.",
              "The well, its mouth not lit, facing us."):
        assert sf.contradictions(s, facts), s


def test_negation_after_the_match_must_be_about_seeing_it():
    """Rà tích hợp 11/10: "not"/"never" ngay SAU cụm khớp chỉ cứu câu khi nói về việc thấy vật ("is not visible", "hidden") —
    "peers into the well not knowing …" vẫn là câu khẳng định trái sự thật; cụm khớp lần hai (không phủ định) trong cùng câu cũng bắt."""
    facts = sf.derive({"stage_camera": SHOT5["stage_camera"]})["facts"]
    for s in ("Kelly peers into the well not knowing what waits below.", "Kelly peers into the well never looking away.",
              "Never the inside of the well at first, later the inside of the well fills the frame."):
        assert sf.contradictions(s, facts), s
    for s in ("The inside of the well is not visible from here.", "The inside of the well stays hidden.",
              "The inside of the well not visible, only the rim."):
        assert sf.contradictions(s, facts) == [], s


def test_blocking_and_action_peak_are_scanned_too():
    facts = sf.derive({"stage_camera": SHOT5["stage_camera"]})["facts"]
    data = {"image_prompt": "Medium shot of the creature by the well.",
            "blocking": "Low camera; the creature climbs out, the well's dark mouth behind her hands.",
            "action_peak": "she rises over the rim"}
    found = sf.prompt_contradictions(data, facts)
    assert [c["field"] for c in found] == ["blocking"] and found[0]["level"] == "do"
    assert sf.prompt_contradictions({"image_prompt": data["image_prompt"]}, facts) == []


def _db(data):
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript("CREATE TABLE scenes(id INTEGER PRIMARY KEY, project_id INT, idx INT, data TEXT);"
                    "CREATE TABLE assets(id INTEGER PRIMARY KEY, kind TEXT, name TEXT, profile TEXT);"
                    "CREATE TABLE jobs(id INTEGER PRIMARY KEY, scene_id INT, type TEXT, state TEXT, sent_refs TEXT);")
    c.execute("INSERT INTO scenes VALUES (1, 24, 5, ?)", (json.dumps(data),))
    return c


def test_change_audit_names_the_blocking_field(monkeypatch, tmp_path):
    monkeypatch.setattr(features, "on", lambda n: n == "stage_camera")
    data = {"stage_camera": SHOT5["stage_camera"], "size": "MS", "image_prompt": "Medium shot, low camera looking up at the creature.",
            "blocking": "the creature grips the rim, the well's dark mouth behind her."}
    res = change_audit.audit_shot(_db(data), str(tmp_path), 24, 1)
    geo = [r for r in res if "sự thật hình học" in r["msg"]]
    assert geo and "trường blocking" in geo[0]["msg"] and geo[0]["muc"] == "do"


# ---- (2) vị trí sau động tác di chuyển — dàn cảnh r11 #24 rút gọn ------------------------------------------------------------
def _bl(yeunu_after):
    return {"objects": [{"key": "kelly", "kind": "nguoi", "at": [0.14, -0.79], "H": 1.7, "facing": 350},
                        {"key": "gieng", "kind": "gieng", "at": [-0.278, 1.576], "h": 0.9, "d": 1.5, "hollow": True},
                        {"key": "yeunu", "kind": "nguoi", "in": "gieng", "H": 1.7, "facing": 170}],
            "beats": {"bam_mep": {"yeunu": {"at": [-0.191, 1.084], "in": "gieng", "_ly_do": "bám mép gần của giếng"}},
                      "bo": {"yeunu": {"at": [-0.104, 0.591], "tu_the": "bo", "H": 0.6,
                                       "_ly_do": "emote: vừa trườn qua thành giếng, bò về phía trước", **yeunu_after.get("bo", {})}},
                      "dung_khom": {"yeunu": {"at": yeunu_after["dung_khom"], "tu_the": "dung", "_ly_do": "đứng khom tại chỗ"}},
                      "quy": {"yeunu": {"at": yeunu_after["dung_khom"], "tu_the": "quy", "H": 1.19, "_ly_do": "quỳ khóc"}}}}


ORDER = ["bam_mep", "bo", "dung_khom", "quy"]


def test_beat_after_crawl_kept_in_place_is_amber():
    found = sl.movement_gaps(_bl({"dung_khom": [-0.104, 0.591]}), ORDER)
    msgs = " | ".join(f["msg"] for f in found)
    assert found and all(f["muc"] == "vang" and f["level"] == "warn" for f in found)
    assert "giữ nguyên vị trí" in msgs and "dung_khom" in msgs
    assert "cách thành 0.25 m" in msgs                       # đúng con số người dùng bắt (0,25 m)


def test_end_point_declared_and_taken_is_clean():
    bl = _bl({"bo": {"den": [0.069, -0.394]}, "dung_khom": [0.069, -0.394]})
    assert sl.movement_gaps(bl, ORDER) == []
    bl = _bl({"bo": {"den": [0.069, -0.394]}, "dung_khom": [-0.104, 0.591]})
    assert any("phải bắt đầu từ điểm cuối" in f["msg"] for f in sl.movement_gaps(bl, ORDER))


def test_short_vietnamese_words_need_their_marks():
    bl = _bl({"dung_khom": [-0.104, 0.591]})
    bl["beats"]["bo"]["yeunu"]["_ly_do"] = "bỏ qua, giữ chỗ cũ"         # "bỏ" ≠ "bò" — không phải động tác
    assert not [f for f in sl.movement_gaps(bl, ORDER[1:]) if "giữ nguyên vị trí" in f["msg"]]   # (bỏ nhịp 'trong giếng' trước đó)


def test_odd_blocking_never_breaks_the_check():
    bl = _bl({"dung_khom": [-0.104, 0.591]})
    bl["objects"][1]["d"] = None
    assert sl.movement_gaps(bl, ORDER)                               # d = null → 1 m mặc định, vẫn kiểm
    bl["beats"]["quy"] = ["x"]
    bl["beats"]["bo"]["kelly"] = "walk"
    assert isinstance(sl.movement_gaps(bl, ORDER), list)


def test_order_comes_from_shot_numbers():
    bl = _bl({"dung_khom": [-0.104, 0.591]})
    specs = [{"shot": 8, "nhip": "quy"}, {"shot": 6, "nhip": "bo"}, {"shot": 7, "nhip": "dung_khom"}]
    assert sl.beat_order(bl, specs, rest=False) == ["bo", "dung_khom", "quy"]
    assert sl.beat_order(bl, specs)[:3] == ["bo", "dung_khom", "quy"]


def test_solve_scene_reports_continuity_without_changing_the_solution():
    from core import stage_solver as ss
    bl = _bl({"dung_khom": [-0.104, 0.591]})
    specs = [{"shot": 6, "nhip": "bo", "co": "MS", "thanh_phan": [{"vat": "yeunu", "vai": "chinh", "vung": "giua"}]},
             {"shot": 7, "nhip": "dung_khom", "co": "MS", "thanh_phan": [{"vat": "yeunu", "vai": "chinh", "vung": "giua"}]}]
    res = ss.solve_scene(specs, bl, 9 / 16)
    assert res["continuity"] and all(w["muc"] == "vang" for w in res["continuity"])
    assert {"objs", "beats", "axis", "s0", "shots"} <= set(res)


def test_stage_director_feedback_and_prompt_follow_the_flag(monkeypatch):
    from core import knowledge, stage_director as sd
    solve = {"shots": [], "continuity": [{"part": "vi_tri_sau_di_chuyen", "msg": "nhịp X giữ nguyên vị trí"},
                                         {"part": "loi_kiem", "msg": "không kiểm được nhịp di chuyển: x"}]}   # lỗi code: không gửi
    monkeypatch.setattr(features, "on", lambda n: False)
    assert sd.feedback_from(solve, None) == [] and knowledge.p24_blocks() == []
    monkeypatch.setattr(features, "on", lambda n: n == "p24_lessons")
    assert sd.feedback_from(solve, None) == ["dàn cảnh: nhịp X giữ nguyên vị trí"]
    assert "Động tác di chuyển làm đổi chỗ đứng" in knowledge.p24_blocks()[0]


# ---- (3) sửa vị trí một người → shot đã duyệt giữ bố cục ------------------------------------------------------------------
def test_layout_drift_names_the_approved_shot():
    old = _bl({"dung_khom": [0.069, -0.394]})
    new = json.loads(json.dumps(old))
    new["beats"]["quy"]["kelly"] = {"at": [0.391, -2.216]}           # sửa Kelly lùi xa hơn ở nhịp quỳ khóc
    found = sl.layout_drift(old, new, {8: "quy", 7: "dung_khom"}, moved=["yeunu"])
    assert {f["shot"] for f in found} == {8} and any("'kelly' bị đổi chỗ" in f["msg"] for f in found)
    cams = {8: {"at": [0.0, -4.0], "aim": [0.0, 0.0]}}
    new["beats"]["quy"]["kelly"] = {"at": [-1.5, -0.39]}             # sang hẳn bên trái yêu nữ
    assert any("đổi bên trái/phải" in f["msg"] for f in sl.layout_drift(old, new, {8: "quy"}, ["kelly"], cams))
    assert sl.layout_drift(old, old, {8: "quy"}, ["yeunu"], cams) == []


# ---- (4) độ phủ nhịp + chi tiết của ref emote ------------------------------------------------------------------------------
CRY = {"nhip": [{"ten": "om_mat", "mo_ta": "quỳ ôm mặt nấc", "tu_khoa": ["ôm mặt", "hands over her face"], "bien_do": "nua_tren"},
                {"ten": "dang_tay", "mo_ta": "dang tay gào lên trời", "tu_khoa": ["dang tay", "arms spread", "spreads her arms"],
                 "bien_do": "toan_than"},
                {"ten": "guc", "mo_ta": "gục rạp chống tay", "tu_khoa": ["gục rạp", "bows down"], "bien_do": "toan_than"}],
       "chi_tiet": [{"ten": "nuoc_mat", "mo_ta": "dòng mảnh ánh xanh từ kẽ tay", "tu_khoa": ["tears", "nước mắt"]}]}


def test_ref_beats_not_covered_are_amber(tmp_path):
    vid = tmp_path / "scene_8_quy_khoc.mp4"
    vid.write_bytes(b"")
    data = {"size": "MS", "action": "yêu nữ quỳ ôm mặt nấc", "image_prompt": "she kneels with her hands over her face"}
    assert sl.load_ref_beats(str(vid))["_missing"].endswith("scene_8_quy_khoc.beats.json")
    assert "chưa ghi các nhịp" in sl.ref_coverage(sl.load_ref_beats(str(vid)), data)[0]["msg"]
    (tmp_path / "scene_8_quy_khoc.beats.json").write_text(json.dumps(CRY, ensure_ascii=False), encoding="utf-8")
    doc = sl.load_ref_beats(str(vid))
    miss = " | ".join(i["msg"] for i in sl.ref_coverage(doc, data))
    assert "dang tay gào" in miss and "gục rạp" in miss and "dòng mảnh ánh xanh" in miss and "ôm mặt nấc" not in miss
    data["ref_luoc"] = [{"nhip": "dang_tay", "ly_do": "shot sau"}, "guc", {"nhip": "nuoc_mat", "ly_do": "shot cận"}]
    assert sl.ref_coverage(doc, data) == []


def test_lint_image_reads_the_reference_of_the_shot(tmp_path):
    vid = tmp_path / "ref.mp4"
    vid.write_bytes(b"")
    (tmp_path / "ref.beats.json").write_text(json.dumps(CRY, ensure_ascii=False), encoding="utf-8")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE motion_prompts(scene_id INT, motion_prompt TEXT, ref_video_path TEXT)")
    conn.execute("INSERT INTO motion_prompts VALUES (1, 'she sobs', ?)", (str(vid),))
    data = pf._with_ref(conn, 1, {"size": "MCU", "image_prompt": "x"}, "she sobs")
    assert data["_ref_motion"] == str(vid) and data["_ref_beats"]["nhip"]
    parts = {i["part"] for i in pf.lint_image("Medium close-up, she kneels with her hands over her face, moonlight.", data)}
    assert {"phu_nhip_ref", "bien_do_khung"} <= parts
    assert pf._with_ref(conn, 2, {"a": 1}, None) == {"a": 1}             # shot không có ref: data y nguyên


# ---- (5) cỡ khung theo biên độ động tác -----------------------------------------------------------------------------------
def test_wide_gesture_in_close_up_is_amber():
    found = sl.framing_amplitude({"size": "CU"}, "Close-up, she spreads her arms and screams at the sky.")
    assert found and found[0]["part"] == "bien_do_khung"
    assert sl.framing_amplitude({"size": "MS"}, "Medium shot, she spreads her arms and screams at the sky.") == []


def test_tears_need_a_big_enough_figure():
    byd = {"hanh_dong": [{"bat_dau": {"tu_the": "quy"}}], "may": {"co": "WS"}}
    found = sl.framing_amplitude({"byd": byd}, "Wide shot, thin tears seep between her fingers.")
    assert found and "tears" in found[0]["msg"] and "38 %" in found[0]["msg"]
    assert sl.framing_amplitude({"size": "MCU"}, "thin tears seep between her fingers") == []
    assert sl.framing_amplitude({"size": "EWS", "_ref_motion": "x.mp4"}, "a dancer in the plaza")      # ref + người < 25 %
    assert sl.framing_amplitude({"size": "WS"}, "a dancer in the plaza") == []
    # rà 11/10: cỡ cận không nhân hệ số tư thế; "tears" động từ / "whole body trembling" không phải biên độ lớn
    lying = {"hanh_dong": [{"bat_dau": {"tu_the": "nam"}}]}
    assert sl.framing_amplitude({"size": "MCU", "byd": lying, "_ref_motion": "x.mp4"}, "tears roll down her cheeks") == []
    assert sl.framing_amplitude({"byd": byd}, "Wide shot, he tears the poster off the wall.") == []
    assert sl.framing_amplitude({"size": "MCU"}, "Medium close-up, her whole body trembling.") == []


# ---- (6) hiệu ứng màn hình là hậu kỳ ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("prompt", ["Wide shot, the whole frame breaks into heavy glitch noise like a lost TV signal.",
                                    "Night plaza, VHS scan lines and static interference across the frame.",
                                    "Toàn cảnh, nhiễu sóng toàn khung như mất kết nối."])
def test_full_frame_screen_effect_is_amber(prompt):
    found = sl.post_fx_in_image(prompt)
    assert found and found[0]["part"] == "hieu_ung_hau_ky" and "post_fx" in found[0]["msg"]


@pytest.mark.parametrize("prompt", ["constant red glitch noise around her wrists and ankles, cold moonlight",
                                    "clean frame with no screen noise, no glitch lines and no distortion",
                                    "the static camera holds the frame",
                                    "Static camera shows her phone screen glowing.", "A static full-frame composition.",
                                    "Low signal noise hum in the alley.", "The TV in the corner shows noise."])
def test_local_or_negated_effect_is_not_reported(prompt):
    assert sl.post_fx_in_image(prompt) == []


def test_bg_poll_starts_once_per_process_even_after_a_module_reload(monkeypatch):
    import threading
    from core import bg_poll
    monkeypatch.setenv("BG_POLL", "1")
    monkeypatch.setattr(bg_poll, "_started", False)
    stop = threading.Event()
    t = threading.Thread(target=stop.wait, name=bg_poll.THREAD_NAME, daemon=True)
    t.start()
    try:
        assert bg_poll.running() and bg_poll.start("x.sqlite", "x") is False      # vòng của serve.py còn sống: không mở vòng 2
    finally:
        stop.set()
        t.join()
    monkeypatch.setenv("BG_POLL", "0")
    assert bg_poll.start("x.sqlite", "x") is False


def test_serve_starts_the_background_round_before_streamlit(monkeypatch):
    import sys
    from core import bg_poll
    from dashboard import serve
    calls = []
    from core import plates3d
    monkeypatch.setattr(plates3d, "set_reporter", lambda fn: calls.append(("rep",)))
    monkeypatch.setattr(bg_poll, "start", lambda db, data: calls.append(("bg", db, data)) or True)
    monkeypatch.setattr(sys, "argv", list(sys.argv))
    out = serve.main(["--server.port", "8599"], run=lambda: calls.append(("st", list(sys.argv))) or 0)
    assert calls[0] == ("rep",)                                     # khóa Blender cũ báo diag cả khi chưa mở trang
    calls = calls[1:]
    assert out == 0 and calls[0][0] == "bg" and calls[1][0] == "st"
    assert calls[1][1][:3] == ["streamlit", "run", serve.APP] and calls[1][1][-2:] == ["--server.port", "8599"]
    assert open(os.path.join(ROOT, "tools", "launch_dashboard.ps1"), encoding="utf-8").read().count('"dashboard.serve"') == 1


def test_app_starts_the_round_before_the_project_check():
    src = open(os.path.join(ROOT, "dashboard", "app.py"), encoding="utf-8").read()
    body = src[src.index("def main():"):]
    assert body.index("start_background_watch()") < body.index("if pid is None:")


def test_lint_image_adds_only_warnings():
    data = {"size": "WS", "characters": ["KELLY"]}
    prompt = ("Wide shot, Free Fire in-game 3D render, Kelly stands in the plaza, moonlight. The whole screen glitches like a lost "
              "signal.")
    issues = pf.lint_image(prompt, data)
    assert [i for i in issues if i["part"] == "hieu_ung_hau_ky"][0]["level"] == "warn"
    assert not [i for i in issues if i["level"] == "red"]
