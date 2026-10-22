"""V3.1 M2.2 (CX21-M22): field readers BYĐ A2a–A2f + `byd` vào lineage — docs/V3_1_M2_1_M2_2_THIET_KE_2026-10-20.md mục 4, 4.1.
Mỗi reader: cờ TẮT = đường cũ byte giống; BẬT + v2 = đọc trường; BẬT + v1 / thiếu = đường cũ + diag byd_fallback. Dữ liệu giả, 0 USD."""
import json
import os
import pathlib
from unittest import mock

import pytest

from core import byd_fields, lineage

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHILD = [f"byd_fields_a2{x}" for x in "abcdef"]
ALL = ["byd_fields"] + CHILD


def env(*on):
    """Bật đúng các cờ trong `on` (tên ngắn: "mother", "a2e"…); mọi cờ M2.2 khác TẮT rõ ràng."""
    names = {"byd_fields" if x == "mother" else f"byd_fields_{x}" for x in on}
    return mock.patch.dict(os.environ, {f"FEATURE_{n.upper()}": ("1" if n in names else "0") for n in ALL})


def v2_scene(**byd_over):
    byd = {"byd_v": 2, "shot": 4, "thanh_phan": [{"vat": "KELLY", "kho_id": 12, "vai": "chinh", "vung": "giua"}],
           "may": {"co": "MS", "do_cao": "ngang", "goc": "ngang", "chuyen_dong": "dung_yen"},
           "noi_chon": {"kho_id": 41, "trong_nha": None, "thoi_gian": "dusk", "thoi_tiet": "fog"},
           "vat": [{"vat": "BOM_KEO", "kho_id": 367, "nguoi": "KELLY", "cach": "nem"}],
           "khung": {"moc_nen": {"kho_id": 88, "y_do": "trong_khung", "ly_do": ""}},
           "hanh_dong": [{"ai": "KELLY", "bat_dau": {"tu_the": "dung"}}]}
    byd.update(byd_over)
    return {"text": "Kelly ném bom keo", "image_prompt": "Kelly throws", "characters": ["KELLY"], "weather": "fog", "byd": byd}


# ---- cờ --------------------------------------------------------------------------------------------------------------------
def test_flags_registered_off_opt_in_requires_mother_and_golden():
    from core import features
    for n in ALL:
        meta = features.FEATURES[n]
        assert meta["verified"] is False and meta.get("costs") is False and not meta.get("default_on")
        assert n in features.OPT_IN_ONLY                          # đổi gói gửi model → preset Thử nghiệm không tự bật
    for n in CHILD:
        assert features.REQUIRES[n] == ("byd_fields",)
    golden = json.load(open(ROOT / "tests" / "golden" / "package_inputs.json", encoding="utf-8"))
    for kind in ("image", "video"):
        assert all(golden[kind]["flags"][n] is False for n in ALL)
    with mock.patch.dict(os.environ, {f"FEATURE_{n.upper()}": "" for n in ALL}):
        assert not any(features.on(n) for n in ALL)


def test_child_needs_mother():
    with env("a2e"):
        assert not byd_fields.enabled("a2e")
    with env("mother"):
        assert not byd_fields.enabled("a2e")
    with env("mother", "a2e"):
        assert byd_fields.enabled("a2e") and not byd_fields.enabled("a2a")
    with pytest.raises(ValueError):
        byd_fields.flag("a2z")


def test_registered_in_areas():
    areas = json.load(open(ROOT / "devsys" / "areas.json", encoding="utf-8"))["areas"]
    hit = [a for a in areas if "core/byd_fields.py" in a["code"]]
    assert hit and "tests/test_v31_m22_byd_fields.py" in hit[0]["tests"] and set(ALL) <= set(hit[0]["flags"])


def test_kho_ids_v2_only_and_never_guesses_partial():
    assert byd_fields.kho_ids(v2_scene()) == [367, 12]
    assert byd_fields.kho_ids(v2_scene(), ("vat",)) == [367]
    assert byd_fields.kho_ids({"byd": {"shot": 1, "vat": ["AWM"]}}) is None                 # v1
    assert byd_fields.kho_ids({}) is None
    assert byd_fields.kho_ids(v2_scene(vat=[{"vat": "AWM", "nguoi": "KELLY", "cach": "cam"}])) is None   # v2 thiếu kho_id → không đoán
    assert byd_fields.kho_ids(v2_scene(vat=[{"vat": "AWM", "kho_id": True, "nguoi": "KELLY", "cach": "cam"}])) is None   # bool ≠ mã


# ---- lineage (G22) ---------------------------------------------------------------------------------------------------------
def test_lineage_off_is_old_hash_and_on_tracks_byd():
    s = v2_scene()
    edited = json.loads(json.dumps(s))
    edited["byd"]["vat"][0]["kho_id"] = 999
    with env():
        old_img, old_mo = lineage.image_spec_hash(s, [], "9:16"), lineage.motion_spec_hash(s)
        no_byd = {k: v for k, v in s.items() if k != "byd"}
        assert old_img == lineage.image_spec_hash(no_byd, [], "9:16")          # cờ tắt: BYĐ không vào hash (y main)
        assert old_mo == lineage.motion_spec_hash(no_byd)
        assert lineage.image_spec_hash(edited, [], "9:16") == old_img          # sửa BYĐ khi cờ tắt: không "⚠ cũ" (hành vi cũ)
    with env("mother"):
        assert lineage.image_spec_hash(s, [], "9:16") != old_img
        assert lineage.image_spec_hash(edited, [], "9:16") != lineage.image_spec_hash(s, [], "9:16")   # G22
        assert lineage.image_spec_hash(no_byd, [], "9:16") == old_img         # chưa có BYĐ (#27): hash cũ, không báo cũ giả
        assert lineage.motion_spec_hash(no_byd) == old_mo
        moved = json.loads(json.dumps(s))
        moved["byd"]["may"]["chuyen_dong"] = "tien"
        assert lineage.motion_spec_hash(moved) != lineage.motion_spec_hash(s)
        # thời gian / thời tiết của noi_chon là bản chép (trigger) — đã có trong hash qua `weather`, không đếm hai lần
        copied = json.loads(json.dumps(s))
        copied["byd"]["noi_chon"]["thoi_tiet"] = "rain"
        assert lineage.image_spec_hash(copied, [], "9:16") == lineage.image_spec_hash(s, [], "9:16")


# ---- dữ liệu Kho giả dùng chung ------------------------------------------------------------------------------------------------
@pytest.fixture
def kho(tmp_path):
    from core import assets
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect())
    pid = p.create_project("m22")
    c = p.conn
    c.execute("UPDATE projects SET game='FF' WHERE id=?", (pid,))

    def add(kind, name, aliases, file, link=True, desc=""):
        aid = c.execute("INSERT INTO assets (game, kind, name, aliases, description) VALUES ('FF',?,?,?,?)",
                        (kind, name, aliases, desc)).lastrowid
        path = tmp_path / file
        path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
        c.execute("INSERT INTO asset_images (asset_id, path, label, sort, status) VALUES (?,?,?,?,?)", (aid, str(path), file, 1, "approved"))
        if link:
            c.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?,?)", (pid, aid))
        return aid

    ids = {"glue": add("prop", "Bom keo", "Gloowall", "glue.png"),
           "grenade": add("prop", "Lựu đạn", "bom", "grenade.png"),     # bí danh chung "bom" — G4: khớp nhầm vào "bom keo"
           "outside": add("prop", "Thùng thính", "airdrop", "drop.png", link=False),
           "ghost": add("style", "Bóng mờ", "ghost form", "ghost.png", desc="Dạng của nhân vật: KELLY\nA glowing translucent ghost.")}
    c.commit()

    def refs(scene, *flags):
        base = {"FEATURE_PROJECT_PROP_LOCK": "0"}
        with env(*flags), mock.patch.dict(os.environ, base), mock.patch.object(assets, "scene_location", return_value=None):
            return [r["label"] for r in assets.scene_references(c, pid, dict(scene))]

    def diags(code):
        return [r["message"] for r in c.execute("SELECT message FROM diag_events WHERE code=? ORDER BY id", (code,))]

    def forms(scene, *flags):
        from core import kho_profile
        with env(*flags):
            return {k: v["form"] for k, v in kho_profile.forms_for_shot(c, pid, dict(scene)).items()}

    def form_rows(scenes, *flags):
        from core import kho_profile
        with env(*flags):
            return {k: v["shots"] for k, v in kho_profile.forms_for_rows(c, pid, [{"data": d} for d in scenes]).items()}

    return {"conn": c, "pid": pid, "ids": ids, "refs": refs, "diags": diags, "forms": forms, "form_rows": form_rows}


def _a2e_scene(kho, vat_ids=None, v1=False):
    s = {"text": "Kelly ném bom keo", "image_prompt": "Kelly throws a glue grenade", "characters": []}
    if v1:
        s["byd"] = {"shot": 4, "vat": ["BOM_KEO"]}
    elif vat_ids is not None:
        s["byd"] = v2_scene(thanh_phan=[], vat=[{"vat": "BOM_KEO", "kho_id": k, "nguoi": "KELLY", "cach": "nem"} for k in vat_ids])["byd"]
    return s


# ---- A2e: ảnh Kho theo kho_id (G4) -----------------------------------------------------------------------------------------
def test_a2e_off_is_old_alias_path_byte_equal(kho):
    v2 = _a2e_scene(kho, [kho["ids"]["glue"]])
    old = kho["refs"](_a2e_scene(kho))
    assert set(old) == {"Bom keo", "Lựu đạn"}                                # đường cũ: bí danh "bom" kéo cả lựu đạn (G4)
    assert kho["refs"](v2) == old and kho["refs"](v2, "a2e") == old and kho["refs"](v2, "mother") == old   # tắt / thiếu mẹ / thiếu con
    assert kho["diags"](byd_fields.FALLBACK) == []


def test_a2e_on_v2_picks_by_kho_id_and_says_skipped_alias(kho):
    got = kho["refs"](_a2e_scene(kho, [kho["ids"]["glue"]]), "mother", "a2e")
    assert got == ["Bom keo"]
    assert any("Lựu đạn" in m for m in kho["diags"](byd_fields.FALLBACK))


def test_a2e_on_v1_or_no_byd_falls_back_with_warning(kho):
    old = kho["refs"](_a2e_scene(kho))
    assert kho["refs"](_a2e_scene(kho, v1=True), "mother", "a2e") == old
    assert kho["refs"](_a2e_scene(kho), "mother", "a2e") == old
    assert len(kho["diags"](byd_fields.FALLBACK)) >= 1


def test_a2e_declared_id_not_in_project_is_review_not_substituted(kho):
    got = kho["refs"](_a2e_scene(kho, [kho["ids"]["outside"]]), "mother", "a2e")
    assert "Thùng thính" not in got and "Lựu đạn" not in got and "Bom keo" not in got
    assert any(str(kho["ids"]["outside"]) in m for m in kho["diags"](byd_fields.MISMATCH))



# ---- A2a: dạng nhân vật theo thanh_phan[].dang (G37) -------------------------------------------------------------------------
def _a2a_scene(dang=None, v1=False, text="Kelly ghost form bước ra khỏi cổng"):
    s = {"text": text, "image_prompt": "", "characters": ["KELLY"]}
    if v1:
        s["byd"] = {"shot": 3, "thanh_phan": [{"vat": "KELLY", "vai": "chinh", "dang": "thuong"}]}
    elif dang is not None:
        tp = {"vat": "KELLY", "kho_id": 12, "vai": "chinh"}
        if dang != "-":
            tp["dang"] = dang
        s["byd"] = v2_scene(thanh_phan=[tp])["byd"]
    return s


def test_a2a_off_is_old_text_path(kho):
    old = kho["forms"](_a2a_scene())
    assert old == {"KELLY": "ghost form"}
    for flags in ((), ("a2a",), ("mother",)):
        assert kho["forms"](_a2a_scene("thuong"), *flags) == old
        assert kho["form_rows"]([_a2a_scene("thuong"), _a2a_scene()], *flags) == {"KELLY": [1, 2]}
    assert kho["diags"](byd_fields.FALLBACK) == []


def test_a2a_on_v2_dang_decides_not_the_text(kho):
    on = ("mother", "a2a")
    assert kho["forms"](_a2a_scene("thuong"), *on) == {}                                   # G37: BYĐ nói dạng thường, chữ nói ghost
    assert kho["forms"](_a2a_scene("ghost_form", text="Kelly bước ra"), *on) == {"KELLY": "ghost form"}   # BYĐ chốt, chữ không nhắc
    assert kho["form_rows"]([_a2a_scene("thuong"), _a2a_scene()], *on) == {"KELLY": [2]}   # theo từng shot, đi qua cùng adapter


def test_a2a_many_forms_or_unknown_never_guessed(kho):
    on = ("mother", "a2a")
    assert kho["forms"](_a2a_scene(["ghost_form", "thuong"]), *on) == {}
    assert kho["forms"](_a2a_scene({"bat_dau": "thuong", "ket_thuc": "ghost_form"}), *on) == {}
    assert kho["forms"](_a2a_scene("ghost"), *on) == {}                                     # "ghost" ≠ "ghost form": không khớp nửa tên
    assert kho["forms"](_a2a_scene("lua"), *on) == {}
    msgs = kho["diags"](byd_fields.MISMATCH)
    assert any("nhiều dạng" in m for m in msgs) and any("lua" in m for m in msgs) and any("'ghost'" in m for m in msgs)


def test_a2a_on_v1_or_no_dang_falls_back_with_warning(kho):
    on = ("mother", "a2a")
    old = kho["forms"](_a2a_scene())
    assert kho["forms"](_a2a_scene(v1=True), *on) == old
    assert kho["forms"](_a2a_scene("-"), *on) == old                                        # v2 không khai dang cho KELLY
    assert len(kho["diags"](byd_fields.FALLBACK)) >= 2



# ---- A2b: đạo cụ cầm theo vat[].kho_id / nguoi / cach (G1, G38) ---------------------------------------------------------------
@pytest.fixture
def guns(kho):
    from core import prop_lock
    c, pid = kho["conn"], kho["pid"]
    ids = {}
    for key, name, desc in (("skorp", "SKORP", "Súng tiểu liên SKORP"), ("awm", "AWM", "Súng bắn tỉa AWM sniper rifle")):
        aid = c.execute("INSERT INTO assets (game, kind, name, aliases, description) VALUES ('FF','weapon',?,?,?)", (name, "", desc)).lastrowid
        c.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?,?)", (pid, aid))
        ids[key] = aid
    c.execute("INSERT INTO characters (project_id, name, description) VALUES (?, 'KELLY', 'cô gái')", (pid,))
    c.commit()
    prop_lock.set_weapon(c, pid, "KELLY", ids["skorp"])

    def holders(scene, *flags):
        with env(*flags):
            pool, _, _, _ = prop_lock._scan(c, pid, scene)
            return prop_lock._holders(c, pid, scene, pool)

    return dict(kho, guns=ids, holders=holders)


def _a2b_scene(vat=None, v1=False, text="Kelly bắn súng"):
    s = {"text": text, "image_prompt": "", "characters": ["KELLY"]}
    if v1:
        s["byd"] = {"shot": 2, "vat": ["AWM"]}
    elif vat is not None:
        s["byd"] = v2_scene(vat=vat)["byd"]
    return s


def test_a2b_off_is_default_weapon_table(guns):
    awm = [{"vat": "AWM", "kho_id": guns["guns"]["awm"], "nguoi": "KELLY", "cach": "cam"}]
    old = guns["holders"](_a2b_scene())
    assert old == {guns["guns"]["skorp"]: ["KELLY"]}
    for flags in ((), ("a2b",), ("mother",)):
        assert guns["holders"](_a2b_scene(awm), *flags) == old
    assert guns["diags"](byd_fields.FALLBACK) == []


def test_a2b_on_v2_vat_overrides_default_gun(guns):
    on = ("mother", "a2b")
    awm = [{"vat": "AWM", "kho_id": guns["guns"]["awm"], "nguoi": "KELLY", "cach": "cam"}]
    assert guns["holders"](_a2b_scene(awm), *on) == {guns["guns"]["awm"]: ["KELLY"]}
    put_down = [{"vat": "AWM", "kho_id": guns["guns"]["awm"], "nguoi": "KELLY", "cach": "dat"}]   # đặt xuống: không phải cầm
    assert guns["holders"](_a2b_scene(put_down), *on) == {guns["guns"]["skorp"]: ["KELLY"]}
    gone = [{"vat": "AWM", "kho_id": 99999, "nguoi": "KELLY", "cach": "cam"}]
    assert guns["holders"](_a2b_scene(gone), *on) == {guns["guns"]["skorp"]: ["KELLY"]}         # mã lạ: không đổi súng, nói ra
    assert any("99999" in m for m in guns["diags"](byd_fields.MISMATCH))


def test_a2b_on_v1_falls_back_with_warning(guns):
    on = ("mother", "a2b")
    assert guns["holders"](_a2b_scene(v1=True), *on) == {guns["guns"]["skorp"]: ["KELLY"]}
    assert any("KELLY" in m for m in guns["diags"](byd_fields.FALLBACK))


def test_a2b_storyboard_uses_held_reads_vat(kho):
    from core import scene_storyboard as sb
    c, pid = kho["conn"], kho["pid"]
    fires = {"image_prompt": "Kelly fires", "characters": ["KELLY"]}
    held = [{"vat": "AWM", "kho_id": 5, "nguoi": "KELLY", "cach": "cam"}]
    with env():
        assert sb._uses_held(c, pid, fires) is True and sb._uses_held(c, pid, None) is False
        assert sb._uses_held(c, pid, dict(fires, byd=v2_scene(vat=[])["byd"])) is True      # tắt: chữ quyết như cũ
    with env("mother", "a2b"):
        assert sb._uses_held(c, pid, dict(fires, byd=v2_scene(vat=[])["byd"])) is False     # v2: không ai cầm gì
        assert sb._uses_held(c, pid, {"image_prompt": "Kelly đứng", "byd": v2_scene(vat=held)["byd"]}) is True
        assert sb._uses_held(c, pid, fires) is True                                        # chưa BYĐ → regex + cảnh báo
    assert any("cầm" in m for m in kho["diags"](byd_fields.FALLBACK))



# ---- A2d: mốc nền theo khung.moc_nen.y_do (G26, G40) ------------------------------------------------------------------------
ENTRY = {"anchor": [0.0, 10.0, 30.0], "landmark": "the Clock Tower", "spots": {"plaza": {"at": [0.0, 0.0], "facing": 0}}}
SPOT = {"name": "plaza", "at": [0.0, 0.0], "facing": 0}


def _a2d_scene(view="landmark", y_do=None, v1=False):
    s = {"text": "Kelly đứng ở quảng trường", "characters": ["KELLY"], "plate_view": {"background": view, "why": "theo kịch bản"}}
    if v1:
        s["byd"] = {"shot": 1, "thanh_phan": [{"vat": "KELLY", "vai": "chinh"}]}
    elif y_do is not None:
        s["byd"] = v2_scene(khung={"moc_nen": {"kho_id": 88, "y_do": y_do, "ly_do": ""}})["byd"]
    return s


def test_a2d_off_is_old_plate_view_word(kho):
    from core import plate_choice as pc
    for flags in ((), ("a2d",), ("mother",)):
        with env(*flags):
            assert pc.landmark_off_frame(_a2d_scene("landmark", "ngoai_khung"), kho["conn"], kho["pid"]) is False
            assert pc.landmark_off_frame(_a2d_scene("away", "trong_khung"), kho["conn"], kho["pid"]) is True
            v = pc.view_of(ENTRY, SPOT, _a2d_scene("landmark", "ngoai_khung"))
            assert v["problem"] is None and v["needs"] is None and v["background_deg"] == 0.0
    assert kho["diags"](byd_fields.FALLBACK) == [] and kho["diags"](byd_fields.MISMATCH) == []


def test_a2d_on_v2_y_do_decides_and_mismatch_is_review(kho):
    from core import plate_choice as pc
    with env("mother", "a2d"):
        assert pc.landmark_off_frame(_a2d_scene("landmark", "ngoai_khung"), kho["conn"], kho["pid"]) is True
        assert pc.landmark_off_frame(_a2d_scene("away", "trong_khung"), kho["conn"], kho["pid"]) is False
        v = pc.view_of(ENTRY, SPOT, _a2d_scene("landmark", "ngoai_khung"))
        assert v["background_deg"] == 0.0 and v["needs"] is None                 # không đổi nền / không chặn render — chỉ nói ra
        assert "khung.moc_nen" in (v["problem"] or "")
        assert pc.view_of(ENTRY, SPOT, _a2d_scene("landmark", "trong_khung"))["problem"] is None
    assert len(kho["diags"](byd_fields.MISMATCH)) == 2


def test_a2d_on_v1_falls_back_with_warning(kho):
    from core import plate_choice as pc
    with env("mother", "a2d"):
        assert pc.landmark_off_frame(_a2d_scene("away", v1=True), kho["conn"], kho["pid"]) is True
        assert pc.landmark_off_frame(_a2d_scene("landmark"), kho["conn"], kho["pid"]) is False
    assert len(kho["diags"](byd_fields.FALLBACK)) == 2



# ---- A2c: trong nhà / ngoài trời cho câu ánh sáng theo noi_chon.trong_nha ----------------------------------------------------
def _a2c_scene(trong_nha="-", v1=False):
    s = {"text": "Kelly ngồi bên cửa sổ", "characters": ["KELLY"], "time": "night"}
    if v1:
        s["byd"] = {"shot": 1, "noi_chon": {"kho_id": 41}}
    elif trong_nha != "-":
        s["byd"] = v2_scene(noi_chon={"kho_id": 41, "trong_nha": trong_nha})["byd"]
    return s


def _indoor(kho, scene, flags, spot=None):
    from core import runner
    with env(*flags), mock.patch.object(runner, "indoor_spot", return_value=spot), \
            mock.patch.object(runner, "_has_3d_spot", return_value=spot is not None or flags == ("3d",)):
        return runner.indoor_light(kho["conn"], kho["pid"], scene)


def test_a2c_off_is_old_spot_only(kho):
    for flags in ((), ("a2c",), ("mother",)):
        assert _indoor(kho, _a2c_scene(True), flags) is False                    # không chỗ đứng 3D → ngoài trời (y main)
        assert _indoor(kho, _a2c_scene(False), flags, spot="phòng ngủ") is True
    assert kho["diags"](byd_fields.FALLBACK) == []


def test_a2c_on_v2_reads_trong_nha_only_without_3d_spot(kho):
    from core import runner
    on = ("mother", "a2c")
    assert _indoor(kho, _a2c_scene(True), on) is True
    assert _indoor(kho, _a2c_scene(False), on) is False
    assert _indoor(kho, _a2c_scene(False), on, spot="phòng ngủ") is True              # chỗ đứng 3D (code) thắng
    with env(*on), mock.patch.object(runner, "indoor_spot", return_value=None), mock.patch.object(runner, "_has_3d_spot", return_value=True):
        assert runner.indoor_light(kho["conn"], kho["pid"], _a2c_scene(True)) is False   # chỗ đứng 3D ngoài trời: code thắng, nói ra
    assert len(kho["diags"](byd_fields.MISMATCH)) == 2


def test_a2c_on_v1_or_missing_falls_back_with_warning(kho):
    on = ("mother", "a2c")
    assert _indoor(kho, _a2c_scene(v1=True), on) is False
    assert _indoor(kho, _a2c_scene(None), on) is False                                     # v2 nhưng trong_nha null
    assert len(kho["diags"](byd_fields.FALLBACK)) >= 1


def test_a2c_light_call_sites_use_one_helper():
    src = (ROOT / "core" / "runner.py").read_text(encoding="utf-8") + (ROOT / "core" / "scene_storyboard.py").read_text(encoding="utf-8")
    assert "light_sentence(data, indoor=bool(indoor_spot(" not in src and "indoor=bool(datas and indoor_spot(" not in src
    assert src.count("indoor_light(") >= 3



# ---- A2f: tên tiếng Anh của nơi chốn theo noi_chon.kho_id (G12) -----------------------------------------------------------------
def _places(kho):
    c, pid = kho["conn"], kho["pid"]

    def add(name, aliases, link=True):
        aid = c.execute("INSERT INTO assets (game, kind, name, aliases) VALUES ('FF','location',?,?)", (name, aliases)).lastrowid
        if link:
            c.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?,?)", (pid, aid))
        return aid
    ids = {"tower": add("Tháp Đồng Hồ", "Clock Tower"), "villa": add("Biệt thự", ""), "far": add("Bermuda", "", link=False)}
    c.commit()
    from core import assets
    return ids, {k: assets.get(c, v) for k, v in ids.items()}


def _a2f_scene(kho_id="-", v1=False):
    s = {"text": "Kelly đứng dưới tháp", "characters": ["KELLY"], "location": "Tháp Đồng Hồ"}
    if v1:
        s["byd"] = {"shot": 1, "noi_chon": "Tháp Đồng Hồ"}
    elif kho_id != "-":
        s["byd"] = v2_scene(noi_chon={"kho_id": kho_id, "trong_nha": False})["byd"]
    return s


def _name(kho, scene, place, *flags):
    from core import runner
    with env(*flags):
        return runner.place_name_for_model(kho["conn"], kho["pid"], scene, place)


def test_a2f_off_is_old_model_place_name(kho):
    ids, pl = _places(kho)
    for flags in ((), ("a2f",), ("mother",)):
        assert _name(kho, _a2f_scene(ids["villa"]), pl["villa"], *flags) == "biet thu"        # bỏ dấu như cũ
        assert _name(kho, _a2f_scene(ids["villa"]), pl["tower"], *flags) == "Clock Tower"
        assert _name(kho, _a2f_scene(ids["tower"]), None, *flags) == ""
    assert kho["diags"](byd_fields.FALLBACK) == [] and kho["diags"](byd_fields.MISMATCH) == []


def test_a2f_on_v2_english_name_of_kho_item(kho):
    ids, pl = _places(kho)
    on = ("mother", "a2f")
    assert _name(kho, _a2f_scene(ids["tower"]), pl["tower"], *on) == "Clock Tower"
    assert _name(kho, _a2f_scene(ids["tower"]), None, *on) == "Clock Tower"                    # cảnh không dò ra nơi: BYĐ cho tên
    assert _name(kho, _a2f_scene(ids["villa"]), pl["villa"], *on) == ""                        # không có tên Anh: không gửi chữ Việt bỏ dấu
    assert _name(kho, _a2f_scene(ids["villa"]), pl["tower"], *on) == "Clock Tower"             # khác nơi của cảnh (3D/ảnh): code thắng
    assert _name(kho, _a2f_scene(ids["far"]), pl["tower"], *on) == "Clock Tower"               # mã không thuộc dự án
    assert len(kho["diags"](byd_fields.MISMATCH)) == 3


def test_a2f_on_v1_or_missing_falls_back_with_warning(kho):
    ids, pl = _places(kho)
    on = ("mother", "a2f")
    assert _name(kho, _a2f_scene(v1=True), pl["villa"], *on) == "biet thu"
    assert _name(kho, _a2f_scene(None), pl["villa"], *on) == "biet thu"                       # v2 nhưng kho_id null
    assert kho["diags"](byd_fields.FALLBACK) and all("noi_chon.kho_id" in m for m in kho["diags"](byd_fields.FALLBACK))   # diag gộp dòng trùng


def test_a2f_setting_and_background_use_one_helper():
    src = (ROOT / "core" / "runner.py").read_text(encoding="utf-8")
    assert src.count("assets.model_place_name(place)") == 1                     # chỉ còn trong place_name_for_model (đường cũ)
    assert src.count("place_name_for_model(") >= 3



# ---- Vòng sửa sau RÀ KỸ (23/10) ------------------------------------------------------------------------------------------------
def test_fix1_v1_byd_never_enters_hash():
    v1 = {"text": "Kelly", "image_prompt": "Kelly", "characters": [], "byd": {"shot": 1, "vat": ["AWM"], "khung": "MS"}}
    with env():
        img, mo = lineage.image_spec_hash(v1, [], "9:16"), lineage.motion_spec_hash(v1)
    with env("mother"):
        assert lineage.image_spec_hash(v1, [], "9:16") == img and lineage.motion_spec_hash(v1) == mo   # #24 (v1): bật cờ không "⚠ cũ"
        assert byd_fields.image_part(v1) is None and byd_fields.motion_part(v1) is None


def _stamped_project():
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect(":memory:"))
    pid = p.create_project("m22-restamp")
    sid = p.create_scene(pid, 1, "shot 1")
    d = v2_scene()
    p.conn.execute("UPDATE scenes SET state='ready', data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), sid))
    j = p.create_job(sid, "image_gen")
    with env():                                                    # ảnh + motion làm khi cờ TẮT (dấu cũ, không có byd)
        p.conn.execute("UPDATE jobs SET state='approved', input_hash=? WHERE id=?", (lineage.current_image_hash(p.conn, pid, sid), j))
        p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, image_job_id, spec_hash) VALUES (?,?,?,?)",
                       (sid, "Kelly throws", j, lineage.motion_spec_hash(d)))
    p.conn.commit()
    return p, pid, sid, j


def test_fix1_turning_mother_on_restamps_fresh_work_once():
    p, pid, sid, j = _stamped_project()
    with env("mother"):
        row = lineage.scan(p.conn, pid)[sid]
        assert row["image_stale"] is None and row["motion_stale"] is None              # ảnh đang mới vẫn mới (không gen lại tốn tiền)
        assert p.conn.execute("SELECT input_hash FROM jobs WHERE id=?", (j,)).fetchone()[0] == lineage.current_image_hash(p.conn, pid, sid)
        d = json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()[0])
        d["byd"]["vat"][0]["kho_id"] = 999                                               # sửa BYĐ SAU khi bật cờ → "⚠ cũ" (G22)
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), sid))
        p.conn.commit()
        assert lineage.scan(p.conn, pid)[sid]["image_stale"]
    with env():
        assert lineage.restamp_byd(p.conn, pid) == 0                                    # cờ tắt: không đụng gì


def test_fix2_background_name_never_vietnamese(kho):
    from core import runner
    ids, pl = _places(kho)
    s = _a2f_scene(ids["villa"])
    with env("mother", "a2f"):
        assert runner.plate_place_name(kho["conn"], kho["pid"], s, pl["villa"], "Biệt thự") == "the place"
        assert runner.plate_place_name(kho["conn"], kho["pid"], s, None, "Villa yard") == "Villa yard"
    with env():
        assert runner.plate_place_name(kho["conn"], kho["pid"], s, None, "Biệt thự") == "Biệt thự"      # TẮT: y cũ
        assert runner.plate_place_name(kho["conn"], kho["pid"], s, pl["villa"], "Biệt thự") == "biet thu"
    src = (ROOT / "core" / "runner.py").read_text(encoding="utf-8")
    assert 'or render.get("label") or "the place"' not in src


def test_fix3_outdoor_setting_uses_the_same_name(kho):
    from core import runner, assets
    ids, pl = _places(kho)
    for key, place_render in (("villa", True), ("villa", False), ("tower", True)):
        s = _a2f_scene(ids[key])
        with mock.patch.object(runner, "indoor_spot", return_value=None):
            with env():
                off = runner._place_part(kho["conn"], kho["pid"], s, pl[key], place_render, [])
                assert off == (assets.render_place_text(kho["conn"], pl[key]) if place_render else assets.location_text(kho["conn"], pl[key]))
            with env("mother", "a2f"):
                on = runner._place_part(kho["conn"], kho["pid"], s, pl[key], place_render, [])
        if key == "villa":
            assert "biet thu" in off and "biet thu" not in on and "Setting: the place" in on
        else:
            assert on == off and "Setting: Clock Tower" in on


def test_fix4_landmark_calls_pass_conn():
    src = (ROOT / "core" / "runner.py").read_text(encoding="utf-8") + (ROOT / "core" / "scene_storyboard.py").read_text(encoding="utf-8")
    for bad in ("landmark_off_frame(data)", "landmark_off_frame(own)", "landmark_off_frame(_shot_data(g, scene_id))",
                "turned_away(g, job[\"scene_id\"])", "away = turned_away(g, scene_id)\n"):
        assert bad not in src, bad


def test_fix5_change_review_watches_byd_only_when_mother_on():
    from core import change_review as cr
    before, after = v2_scene(), v2_scene(vat=[{"vat": "AWM", "kho_id": 5, "nguoi": "KELLY", "cach": "cam"}])
    with env():
        assert cr.changed_keys(before, after, list(cr.watch())) == []                     # TẮT: y cũ (byd không phải khóa WATCH)
        assert cr.watch() is cr.WATCH
    with env("mother"):
        assert cr.changed_keys(before, after, list(cr.watch())) == ["byd.vat"]
        assert "anh" in cr.watch()["byd.vat"] and "byd.khung" in cr.watch() and "byd.thanh_phan" in cr.watch()
