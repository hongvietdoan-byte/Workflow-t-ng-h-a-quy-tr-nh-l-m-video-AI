"""C-3D-GOC-B — gốc R1 (vị trí xuyên shot theo MỘT bản đồ cảnh), người dùng 22/10: sửa GỐC, đặt chỗ khác / cách khác không lặp lại.

Test BIẾN THỂ: cả cảnh (máy + vật) được xoay / tịnh tiến ngẫu nhiên có seed — bất biến phải cho cùng kết luận ở mọi chỗ đặt máy, không chỉ
toạ độ của #31. Ca gốc #31 (G1 / G41 / G43 / G44) dựng lại bằng số trong docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md."""
import json
import math
import os
import random
import sqlite3

import pytest

from core import layout_facts, position_invariants as pi, world_map
from core.db import connect
from core.pipeline import Pipeline

SEEDS = list(range(24))


@pytest.fixture(autouse=True)
def flags(monkeypatch):
    monkeypatch.setenv("FEATURE_STAGE_CAMERA", "1")
    monkeypatch.setenv("FEATURE_STORYBOARD_API", "1")


def rot(p, th, t=(0.0, 0.0)):
    c, s = math.cos(th), math.sin(th)
    return [p[0] * c - p[1] * s + t[0], p[0] * s + p[1] * c + t[1]]


def cam(loc, look, th=0.0, t=(0.0, 0.0)):
    a, b = rot(loc, th, t), rot(look, th, t)
    return {"location": [a[0], a[1], 1.6], "look_at": [b[0], b[1], 1.6], "lens": 35, "props": []}


def ent(eid, xy, kind="vat", th=0.0, t=(0.0, 0.0), label=None, vf=None, vt=None):
    p = rot(xy, th, t)
    return {"entity_id": eid, "label": label or eid, "kho_id": None, "kind": kind, "transform": {"xyz": [p[0], p[1], 0.0], "yaw_deg": None},
            "dimensions": None, "valid_from": vf, "valid_to": vt, "state": None, "source": "stage_blocking", "confidence": "do"}


def map3d(ents, scene=1):
    m = world_map._base(scene, "3d", None, {}, ["stage.json"], "code")
    m["origin"] = {"stage": "t", "xyz": [0.0, 0.0, 0.0], "model_xyz": [0.0, 0.0, 0.0]}
    m["entities"] = ents
    return m


def transform(seed):
    r = random.Random(seed)
    return r.uniform(-math.pi, math.pi), (r.uniform(-50, 50), r.uniform(-50, 50))


# ---- R1-SIDE: trái/phải trong chữ ↔ map theo máy của shot ---------------------------------------------------------------------
@pytest.mark.parametrize("seed", SEEDS)
def test_side_mismatch_is_found_wherever_the_scene_is_placed(seed):
    th, t = transform(seed)
    # máy ở (0,-8) nhìn bắc: thùng ở x = +2 là bên PHẢI khung — đúng ở mọi phép xoay/tịnh tiến của cả cảnh
    m = map3d([ent("BARREL", (2.0, 0.0), th=th, t=t), ent("KELLY", (-2.0, 0.0), kind="nguoi", th=th, t=t)])
    c = cam((0, -8), (0, 0), th, t)
    wrong = pi.check_text_sides(m, 1, {"image_prompt": "KELLY stands on the right. The BARREL sits on the left."}, c)
    right = pi.check_text_sides(m, 1, {"image_prompt": "KELLY stands on the left; the BARREL is on the right."}, c)
    assert {f["numbers"]["entity"] for f in wrong} == {"KELLY", "BARREL"} and all(f["code"] == "R1-SIDE" for f in wrong)
    assert wrong[0]["fix"] and "frame" in wrong[0]["fix"]                       # câu thay SINH từ map
    assert right == []


# ---- R1-AXIS-JUMP: hai shot liền nhau cùng phía trục mà vật đổi bên --------------------------------------------------------
@pytest.mark.parametrize("seed", SEEDS)
def test_axis_jump_only_when_both_cameras_on_the_same_side(seed):
    th, t = transform(seed)
    m = map3d([ent("CORPSE", (0.5, 0.0), th=th, t=t)])
    a = cam((-1.5, -6), (-1.5, 0), th, t)        # nhìn bắc, xác bên phải
    b = cam((2.5, -6), (2.5, 0), th, t)          # nhìn bắc, máy dời sang phải xác → xác bên trái: NHẢY TRỤC
    rev = cam((0.0, 6), (0.0, 0), th, t)         # nhìn nam (ngược trục): đổi bên là đúng
    jump = pi.check_axis_jumps(m, [{"shot": 1, "camera": a}, {"shot": 2, "camera": b}])
    ok = pi.check_axis_jumps(m, [{"shot": 1, "camera": a}, {"shot": 2, "camera": rev}])
    assert [f["code"] for f in jump] == ["R1-AXIS-JUMP"] and jump[0]["numbers"]["side_a"] == "right"
    assert ok == []


def test_axis_jump_needs_both_cameras_not_a_guess():
    m = map3d([ent("CORPSE", (0.5, 0.0))])
    assert pi.check_axis_jumps(m, [{"shot": 1, "camera": cam((-1.5, -6), (-1.5, 0))}, {"shot": 2, "camera": None}]) == []
    assert pi.same_side_of_axis(None, cam((0, 0), (0, 1))) is None


# ---- R1-TRAVEL: hướng đi ↔ vị trí của thứ "về phía" / "rời khỏi" ------------------------------------------------------------
@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("corpse_y, bad", [(5.0, True), (-3.0, False)])
def test_walk_away_from_x_but_x_is_ahead(seed, corpse_y, bad):
    """G43 (#31 shot 29): 'quay người rời khỏi cái xác và đi tiếp' vào nền — xác nằm ở NỀN (phía trước hướng đi) → sai."""
    th, t = transform(seed)
    m = map3d([ent("KELLY", (0.0, 0.0), kind="nguoi", th=th, t=t), ent("corpse", (0.3, corpse_y), th=th, t=t)])
    c = cam((0, -6), (0, 0), th, t)
    got = pi.check_travel(m, 1, "KELLY", "Kelly turns and walks away from the corpse into the background.", c)
    assert bool([f for f in got if f["level"] == "vang"]) is bad
    if bad:
        assert "P31-G43" in got[0]["errors"]


@pytest.mark.parametrize("seed", SEEDS[:8])
def test_run_toward_x_must_have_x_ahead(seed):
    th, t = transform(seed)
    m = map3d([ent("KELLY", (0.0, 0.0), kind="nguoi", th=th, t=t), ent("tower", (-6.0, 0.5), th=th, t=t)])
    c = cam((0, -6), (0, 0), th, t)
    assert pi.check_travel(m, 1, "KELLY", "Kelly runs toward the tower, exiting frame left.", c) == []
    bad = pi.check_travel(m, 1, "KELLY", "Kelly runs toward the tower, exiting frame right.", c)
    assert [f["code"] for f in bad] == ["R1-TRAVEL"] and "P31-G41" in bad[0]["errors"]


def test_travel_target_missing_from_map_is_said_not_guessed():
    m = map3d([ent("KELLY", (0.0, 0.0), kind="nguoi")])
    got = pi.check_travel(m, 1, "KELLY", "Kelly runs away from the enemies into the background.", cam((0, -6), (0, 0)))
    assert got and got[0]["level"] == "khong_ro" and "enemies" in got[0]["msg"]


def test_no_direction_words_no_claim():
    m = map3d([ent("KELLY", (0.0, 0.0), kind="nguoi"), ent("corpse", (0.0, 5.0))])
    assert pi.check_travel(m, 1, "KELLY", "Kelly looks at the corpse.", cam((0, -6), (0, 0))) == []


def test_vietnamese_direction_words():
    m = map3d([ent("KELLY", (0.0, 0.0), kind="nguoi"), ent("xac", (0.0, 5.0), label="cái xác")])
    got = pi.check_travel(m, 1, "KELLY", "Kelly quay lưng rời khỏi cái xác, đi sâu vào nền.", cam((0, -6), (0, 0)))
    assert [f["code"] for f in got] == ["R1-TRAVEL"]


# ---- R1-PROP-SCENE (G1) ------------------------------------------------------------------------------------------------------
def test_placeholder_from_another_scene_is_flagged_only_when_absent_here():
    """G1: xác bay cảnh 6 mang sang cảnh 8 (thực tại) → VÀNG; tường cố định cùng sân khấu có ở cảnh này → không báo (stage_auto cố ý)."""
    sc = {"location": [0, 0, 1.6], "look_at": [0, 5, 1.6], "lens": 35,
          "props": [{"kind": "block", "label": "XÁC ĐEN BIẾT BAY", "source": "cảnh 6 (cùng sân khấu)"},
                    {"kind": "block", "label": "tường đá", "source": "cảnh 6 (cùng sân khấu)"}, {"kind": "block", "label": "cột"}]}
    got = pi.check_props_scene(sc, 8, ["KELLY", "tường đá"])
    assert [(f["numbers"]["prop"], f["level"]) for f in got] == [("XÁC ĐEN BIẾT BAY", "vang")]
    assert pi.check_props_scene(sc, 6, []) == []
    assert {f["level"] for f in pi.check_props_scene(sc, 8, [])} == {"khong_ro"}      # không map / BYĐ: không đoán


# ---- R1-MAP + layout_facts.positions (một nguồn) ----------------------------------------------------------------------------
def test_scene_without_map_says_so_once():
    got = pi.scene_report(None, 4, [{"shot": 1, "data": {}}, {"shot": 2, "data": {}}])
    assert [(f["code"], f["level"]) for f in got] == [("R1-MAP", "khong_ro")]
    assert pi.scene_report(None, 4, [{"shot": 1, "data": {}}]) == []


def _project(tmp_path, shots, m=None):
    db = str(tmp_path / "manifest.sqlite")
    p = Pipeline(connect(db))
    pid = p.create_project("r1")
    ids = []
    for i, extra in enumerate(shots, 1):
        sid = p.create_scene(pid, i, f"s{i}")
        d = {"story_scene": 1, "shot_no": i, "characters": ["KELLY"], "plate_spot": "a"}
        d.update(extra)
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), sid))
        ids.append(sid)
    p.conn.commit()
    data = str(tmp_path / "projects")
    if m is not None:
        os.makedirs(world_map.world_dir(data, pid), exist_ok=True)
        with open(world_map.path(data, pid, 1), "w", encoding="utf-8") as f:
            json.dump(m, f)
    return p, pid, ids, db, data


def test_layout_facts_positions_come_from_the_map(tmp_path):
    m = map3d([ent("KELLY", (1.0, 2.0), kind="nguoi"), ent("corpse", (0.0, 5.0), vf=2, vt=3)])
    p, pid, ids, _, data = _project(tmp_path, [{}, {}], m)
    f1, f2 = (layout_facts.facts_for_shot(p.conn, pid, i, data) for i in ids)
    assert f1["positions"] == {"KELLY": [1.0, 2.0]} and set(f2["positions"]) == {"KELLY", "corpse"}
    assert "world_map r1" in f1["provenance"]["positions"]
    m["invalidated"] = {"why": "stage.json đổi"}
    with open(world_map.path(data, pid, 1), "w", encoding="utf-8") as fh:
        json.dump(m, fh)
    f = layout_facts.facts_for_shot(p.conn, pid, ids[0], data)
    assert f["positions"] == {} and any("đã cũ" in w for w in f["missing"])


def test_tool_reads_a_copy_reports_and_exit_code(tmp_path, capsys):
    from tools import position_invariants as tool
    m = map3d([ent("KELLY", (-2.0, 0.0), kind="nguoi")])
    p, pid, _, db, data = _project(tmp_path, [{"stage_camera": cam((0, -8), (0, 0)), "image_prompt": "KELLY on the right"},
                                              {"stage_camera": cam((0, -8), (0, 0)), "image_prompt": "KELLY on the left"}], m)
    p.conn.close()            # gộp 22/10: kết nối ghi để GC đóng giữa chừng → WAL checkpoint đổi mtime/size (lỗi test theo thứ tự chạy)
    before = os.path.getmtime(db), os.path.getsize(db)
    assert tool.main(["--project", str(pid), "--db", db, "--data", data]) == 1
    out = capsys.readouterr().out
    assert "R1-SIDE" in out and "shot 1" in out and "shot 2 ·" not in out
    assert (os.path.getmtime(db), os.path.getsize(db)) == before
    sqlite3.connect(db).close()


def test_flag_off_ignores_stage_cameras(monkeypatch):
    """stage_camera chỉ dùng khi cờ bật (như ảnh / QC / layout_facts) — cờ tắt: không phán bên theo máy cũ còn trong data."""
    monkeypatch.setenv("FEATURE_STAGE_CAMERA", "0")
    m = map3d([ent("KELLY", (-2.0, 0.0), kind="nguoi"), ent("X", (0.0, 9.0))])
    shots = [{"shot": 1, "data": {"stage_camera": cam((0, -8), (0, 0)), "image_prompt": "KELLY on the right", "characters": ["KELLY"]}},
             {"shot": 2, "data": {"stage_camera": cam((0, -8), (0, 0)), "characters": ["KELLY"]}}]
    assert [f for f in pi.scene_report(m, 1, shots) if f["code"] == "R1-SIDE"] == []


# ---- rà quy ước 7 (22/10): số shot của map = scenes.idx; câu nhìn không phải đi; người đi theo câu; khớp tên mơ hồ; map hỏng ------
def test_map_shot_numbers_are_project_idx_not_shot_no(tmp_path):
    """valid_from/valid_to của map = shot_specs 'shot' = scenes.idx (stage_auto). Cảnh 2 có idx 3–4 mà shot_no 1–2."""
    m = map3d([ent("KELLY", (1.0, 2.0), kind="nguoi", vf=3, vt=3), ent("KELLY_B", (5.0, 5.0), kind="nguoi", vf=4, vt=4)], scene=2)
    db = str(tmp_path / "m.sqlite")
    p = Pipeline(connect(db))
    pid = p.create_project("idx")
    ids = []
    for idx, (sc, no) in enumerate([(1, 1), (1, 2), (2, 1), (2, 2)], 1):
        sid = p.create_scene(pid, idx, f"s{idx}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"story_scene": sc, "shot_no": no, "characters": ["KELLY"]}), sid))
        ids.append(sid)
    p.conn.commit()
    data = str(tmp_path / "projects")
    os.makedirs(world_map.world_dir(data, pid), exist_ok=True)
    with open(world_map.path(data, pid, 2), "w", encoding="utf-8") as f:
        json.dump(m, f)
    assert layout_facts.facts_for_shot(p.conn, pid, ids[2], data)["positions"] == {"KELLY": [1.0, 2.0]}
    assert set(layout_facts.facts_for_shot(p.conn, pid, ids[3], data)["positions"]) == {"KELLY_B"}
    rep = pi.project_report(p.conn, pid, data)
    assert rep["scenes"]["2"] == [] and rep["scenes"]["1"][0]["code"] == "R1-MAP"


@pytest.mark.parametrize("text", ["Kelly runs away from camera, glancing back toward the corpse.",
                                  "Kelly aims toward the corpse.", "Kelly looks toward the corpse while walking into the background."])
def test_looking_toward_is_not_travelling_toward(text):
    m = map3d([ent("KELLY", (0.0, 0.0), kind="nguoi"), ent("corpse", (0.0, -4.0))])
    assert [f for f in pi.check_travel(m, 1, ["KELLY"], text, cam((0, -6), (0, 0))) if f["level"] == "vang"] == []


def test_mover_is_the_person_named_in_the_sentence():
    m = map3d([ent("KELLY", (0.0, 0.0), kind="nguoi"), ent("MAXIM", (0.0, 8.0), kind="nguoi"), ent("corpse", (0.0, 6.0))])
    c = cam((0, -6), (0, 0))
    # MAXIM ở sau xác: MAXIM 'rời khỏi xác, đi vào nền' là đúng; nếu lấy KELLY (characters[0]) sẽ báo nhầm
    assert pi.check_travel(m, 1, ["KELLY", "MAXIM"], "Maxim walks away from the corpse into the background.", c) == []
    assert pi.check_travel(m, 1, ["KELLY", "MAXIM"], "The figure walks away from the corpse into the background.", c) == []


def test_ambiguous_partial_name_is_not_guessed():
    m = map3d([ent("soldier_a", (1.0, 1.0), label="soldier"), ent("soldier_b", (2.0, 2.0), label="soldier crate")])
    assert pi.find_entity(m, "enemy soldiers hiding behind crates", None) is None
    assert pi.find_entity(m, "the soldier", None)["entity_id"] == "soldier_a"


def test_broken_map_is_said_not_crashing(tmp_path):
    _, pid, ids, db, data = _project(tmp_path, [{}, {}], map3d([]))
    with open(world_map.path(data, pid, 1), "w", encoding="utf-8") as f:
        f.write("{broken")
    p = Pipeline(connect(db))
    f = layout_facts.facts_for_shot(p.conn, pid, ids[0], data)
    assert f["positions"] == {} and any("bản đồ" in w for w in f["missing"])


# ---- rà gộp GOC-B vào main (22/10) ------------------------------------------------------------------------------------------
def test_shots_without_story_scene_are_said_not_skipped(tmp_path):
    """Luật 1 CHUAN_XAY_DUNG: shot thiếu story_scene không thuộc map nào — báo KHÔNG RÕ kèm số shot, không bỏ qua im lặng."""
    _, pid, _, db, data = _project(tmp_path, [{}, {"story_scene": None}, {"story_scene": None}], map3d([]))
    rep = pi.project_report(Pipeline(connect(db)).conn, pid, data)
    got = rep["scenes"][pi.NO_SCENE_KEY]
    assert [(f["code"], f["level"]) for f in got] == [("R1-MAP", "khong_ro")] and got[0]["numbers"]["shots"] == [2, 3]
    assert rep["n"] == 0


@pytest.mark.parametrize("vat", [["CORPSE"], [{"vat": "CORPSE", "kho_id": None, "nguoi": None, "cach": "", "bien_the": None}]])
def test_byd_vat_v1_and_v2_count_as_known(vat):
    """BYĐ `vat` đọc qua shot_intent.vat_items (v1 = chuỗi, v2 = bảng {vat…}) — trước đọc `ten` (không có ở cả hai) → xác có ở cảnh này
    vẫn bị báo R1-PROP-SCENE."""
    sc = {"location": [0, -6, 1.6], "look_at": [0, 0, 1.6], "lens": 35, "props": [{"label": "corpse", "source": "Sân khấu 3D cảnh 6"}]}
    names = pi._known_names(None, 1, {"byd": {"vat": vat}, "characters": []})
    assert pi.check_props_scene(sc, 8, names) == []


def test_move_verb_must_start_a_word():
    """'di' (đi) chỉ là động từ khi đứng đầu từ — 'kandi toward …' không phải đi về phía."""
    assert pi._targets("kandi toward the corpse", pi._TOWARD) == []
    assert pi._targets("kelly di ve phia corpse", pi._TOWARD) == ["corpse"]


def test_map_positions_are_not_fed_into_gen_or_qc():
    """test_v31_dp8 cho core/layout_facts đọc map vì chỉ để BÁO: không module nào ngoài layout_facts / position_invariants dùng
    facts['positions'] (không vào gói gửi / mệnh đề QC) — muốn dùng phải sau cờ + sửa test này."""
    import pathlib
    import re
    root = pathlib.Path(__file__).resolve().parent.parent
    use = re.compile(r"""\[\s*["']positions["']\s*\]|\.get\(\s*["']positions["']""")
    allowed = {"core/layout_facts.py", "core/position_invariants.py"}
    users = [str(p.relative_to(root)).replace("\\", "/") for d in ("core", "dashboard") for p in (root / d).rglob("*.py")
             if use.search(p.read_text(encoding="utf-8", errors="replace"))]
    assert [u for u in users if u not in allowed] == []
