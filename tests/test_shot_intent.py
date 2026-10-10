"""K0a: schema BYĐ tối thiểu (core/shot_intent.py, kế hoạch kiểm soát mục 3.1). Enum TÁI DÙNG shot_specs V3 — test giữ khớp với
core/stage_solver.validate / core/stage_grid / core/plate_env để hai nơi không trôi xa nhau."""
import sqlite3
import unittest

from core import plate_env, shot_intent as si, stage_grid as sg, stage_solver


def _good():
    b = si.empty(4)
    b["thanh_phan"] = [{"vat": "kelly", "vai": "chinh", "vung": "trai-duoi", "thay": "lung|nghieng"},
                       {"vat": "gieng", "vai": "chinh", "vung": "giua+phai", "kho_id": 420}]
    b["may"].update(co="WS", do_cao="thap", goc="ngang")
    b["noi_chon"].update(kho_id=263, thoi_gian="night", thoi_tiet="fog")
    b["hanh_dong"] = [{"ai": "kelly", "bat_dau": {"tu_the": "dung", "nhin": "gieng"},
                       "ket_thuc": {"tu_the": "ngoi", "cham_dat": ["mong", "ban_tay"], "nhin": "gieng"}}]
    b["ngoai_le"] = [{"doi_tuong": "gieng", "dieu_trai": "phát sáng xanh", "ly_do": "hieu_ung_game", "cach_hien": "quầng xanh",
                      "pham_vi": [4, 5]}]
    return b


class EnumReuseTests(unittest.TestCase):
    def test_enums_come_from_the_stage_specs(self):
        self.assertEqual(si.CO, tuple(sg.FRAMING))
        self.assertEqual(si.VAI, sg.ROLES)
        self.assertEqual(si.THAY, sg.VIEWS)
        self.assertEqual(si.GOC, sg.GOC)
        self.assertEqual(si.THOI_GIAN, plate_env.TIMES)
        self.assertEqual(si.THOI_TIET, plate_env.WEATHERS)
        self.assertEqual(set(si.CHUYEN_DONG) - {"dung_yen"}, set(stage_solver.MOVES))

    def test_solver_accepts_every_height_and_angle(self):
        objs = {"kelly": {"kind": "nguoi", "xy": [0, 0]}}
        for h in si.DO_CAO:
            for g in si.GOC:
                spec = {"co": "WS", "do_cao": h, "goc": g, "thanh_phan": [{"vat": "kelly", "vai": "chinh", "vung": "giua"}]}
                self.assertEqual(stage_solver.validate(spec, objs), [], (h, g))

    def test_tu_the_matches_prompt_29(self):
        import os
        text = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts",
                                 "29_director_stage_specs.md"), encoding="utf-8").read()
        self.assertIn("tu_the", text)
        # Tư thế prompt 29 cho Director dùng phải là TẬP CON của TU_THE (Director không ra mã mà kiểm không biết). Ngược lại không bắt
        # buộc: 'nga_ngua', 'nam' — solver đã tính thân nằm (Codex việc 2) nhưng rà 10/10 HOÃN mở cho Director tới khi tools/stage_grid.py
        # dựng người nộm nằm (hiện dựng trụ đứng cao H = bề dài thân → số Blender trái solver). Gỡ assertNotIn khi người nộm nằm xong.
        in_prompt = {"dung": "đứng", "ngoi": "ngồi bệt", "quy": "quỳ", "bo": "bò"}
        for code, word in in_prompt.items():
            self.assertIn(word, text)
            self.assertIn(code, si.TU_THE)
        for code in ("nga_ngua", "nam"):
            self.assertNotIn(f"`{code}`", text)
            self.assertNotIn(code, text.split("`tu_the`", 1)[1].split("\n", 1)[0])

    def test_nga_ngua_is_a_pose(self):
        """#24 shot 4 job 635: Kelly phải NGÃ NGỬA hai tay chống sau, ảnh ra NGỒI thẳng — enum cũ chỉ ghi được 'ngoi' (không phân biệt)."""
        self.assertIn("nga_ngua", si.TU_THE)
        self.assertIn("nam", si.TU_THE)
        b = _good()
        b["hanh_dong"][0]["ket_thuc"]["tu_the"] = "nga_ngua"
        self.assertNotIn("hanh_dong[0].ket_thuc.tu_the", {i["truong"] for i in si.validate(b)})

    def test_dryrun_reads_fallen_back_as_nga_ngua(self):
        import importlib.util
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "dryrun_k0b_p24.py")
        spec = importlib.util.spec_from_file_location("dryrun_k0b_p24", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for _pat, tu_the, _cham in mod.POSE_WORDS:
            self.assertIn(tu_the, si.TU_THE)
        self.assertEqual(mod.pose_from_text("just fallen backward onto the stone ground")[0]["tu_the"], "nga_ngua")
        self.assertEqual(mod.pose_from_text("Kelly lying on her back")[0]["tu_the"], "nam")
        self.assertEqual(mod.pose_from_text("Kelly sitting on the ground")[0]["tu_the"], "ngoi")

    def test_golden_pose_expectations_use_the_enum(self):
        from tests import golden
        cases = [c for c in golden.load_cases() if "shot_intent" in (c.get("ky_vong") or {})]
        self.assertTrue(cases)
        for c in cases:
            for h in c["ky_vong"]["shot_intent"].get("hanh_dong") or []:
                for nhip in si.NHIP_HD:
                    if h.get(nhip):
                        self.assertIn(h[nhip]["tu_the"], si.TU_THE, c["id"])
        job635 = next(c for c in cases if c["id"] == "p24_shot4_pose_job635")
        self.assertEqual(job635["ky_vong"]["shot_intent"]["hanh_dong"][0]["bat_dau"]["tu_the"], "nga_ngua")


class ValidateTests(unittest.TestCase):
    def test_good_byd_without_conn_is_only_yellow_for_kho(self):
        got = si.validate(_good())
        self.assertEqual([i["muc"] for i in got], ["vang"])
        self.assertIn("kho", got[0]["truong"])

    def test_good_byd_with_kho(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE assets (id INTEGER PRIMARY KEY)")
        conn.executemany("INSERT INTO assets VALUES (?)", [(263,), (420,)])
        self.assertEqual(si.validate(_good(), conn), [])
        conn.execute("DELETE FROM assets WHERE id=420")
        got = si.validate(_good(), conn)
        self.assertEqual([(i["muc"], i["truong"]) for i in got], [("do", "thanh_phan[1].kho_id")])

    def test_wrong_enums_and_missing_fields_are_red(self):
        b = _good()
        b["may"].update(co="XL", do_cao="bay", goc="nghieng", chuyen_dong="lia")
        b["thanh_phan"][0].update(vai="vai_lon", vung="tren-trai-giua", thay="ben")
        b["hanh_dong"][0]["bat_dau"]["tu_the"] = "nhay"
        b["hanh_dong"].append({"ai": "nguoi_la", "bat_dau": {"tu_the": "dung"}})
        b["ngoai_le"][0]["ly_do"] = "vi_thich"
        b["noi_chon"].update(kho_id=None, thoi_tiet="bao_lua")
        b["la"] = 1
        got = {i["truong"] for i in si.validate(b) if i["muc"] == "do"}
        for t in ("may.co", "may.do_cao", "may.goc", "may.chuyen_dong", "thanh_phan[0].vai", "thanh_phan[0].vung", "thanh_phan[0].thay",
                  "hanh_dong[0].bat_dau.tu_the", "hanh_dong[1].ai", "ngoai_le[0].ly_do", "noi_chon.kho_id", "noi_chon.thoi_tiet", "la"):
            self.assertIn(t, got)

    def test_missing_groups_and_no_main_subject(self):
        got = {i["truong"] for i in si.validate({"shot": 1})}
        for t in ("thanh_phan", "may", "noi_chon"):
            self.assertIn(t, got)
        b = _good()
        for c in b["thanh_phan"]:
            c["vai"] = "phu"
        self.assertIn("thanh_phan", {i["truong"] for i in si.validate(b)})

    def test_camera_move_dict_uses_solver_rules(self):
        b = _good()
        b["may"]["chuyen_dong"] = {"kieu": "lui", "m": 1.0}
        self.assertNotIn("may.chuyen_dong", {i["truong"] for i in si.validate(b)})
        b["may"]["chuyen_dong"] = {"kieu": "lui", "m": 9}
        self.assertIn("may.chuyen_dong", {i["truong"] for i in si.validate(b)})

    def test_from_shot_spec(self):
        spec = {"shot": 2, "nhip": "nhip_a", "co": "MCU", "do_cao": "ngang", "goc": "cui", "muc_dich": "sợ",
                "thanh_phan": [{"vat": "kelly", "vai": "chinh", "vung": "giua", "thay": "mat"}]}
        b = si.from_shot_spec(spec)
        self.assertEqual((b["shot"], b["may"]["co"], b["truyen"]["nhip"]), (2, "MCU", "nhip_a"))
        self.assertEqual({i["truong"] for i in si.validate(b)}, {"noi_chon.kho_id"})
        self.assertEqual(b["hanh_dong"], [])                    # không có blocking → không bịa tư thế

    def test_from_shot_spec_carries_beat_poses_into_hanh_dong(self):
        """Thẩm định 3/4 (chưa đóng): tư thế từng nhịp (`blocking.beats[nhip][khoa].tu_the`) → BYĐ hanh_dong[].bat_dau.tu_the cho
        người trong thanh_phan; người không ghi tu_the ở nhịp lẫn objects → 'dung' (đứng = mặc định người nộm, prompt 29), đánh dấu."""
        blocking = {"objects": [{"key": "kelly", "kind": "nguoi", "at": [0, 0], "H": 1.7},
                                {"key": "yeunu", "kind": "nguoi", "at": [1, 0], "H": 1.7},
                                {"key": "gieng", "kind": "gieng", "at": [0, 1]}],
                    "beats": {"nga": {"kelly": {"at": [0, -0.2], "H": 1.0, "tu_the": "nga_ngua"}, "yeunu": {"hidden": True}},
                              "di": {"yeunu": {"at": [0.5, 0]}}}}
        spec = {"shot": 4, "nhip": "nga", "co": "WS", "thanh_phan": [{"vat": "kelly", "vai": "chinh", "vung": "trai"},
                                                                      {"vat": "gieng", "vai": "chinh", "vung": "giua"}]}
        b = si.from_shot_spec(spec, blocking)
        self.assertEqual(b["hanh_dong"], [{"ai": "kelly", "bat_dau": {"tu_the": "nga_ngua"}, "nguon": "blocking.beats.nga"}])
        self.assertNotIn("hanh_dong[0].bat_dau.tu_the", {i["truong"] for i in si.validate(b)})
        spec2 = {"shot": 2, "nhip": "di", "co": "MS", "thanh_phan": [{"vat": "yeunu", "vai": "chinh", "vung": "giua"}]}
        h = si.from_shot_spec(spec2, blocking)["hanh_dong"]
        self.assertEqual(h, [{"ai": "yeunu", "bat_dau": {"tu_the": "dung"}, "nguon": "mac_dinh_dung"}])
        blocking["beats"]["ngoi_khong_ghi"] = {"kelly": {"H": 1.0}}           # thấp hẳn mà không ghi tu_the → không đoán 'dung'
        b = si.from_shot_spec(dict(spec, nhip="ngoi_khong_ghi"), blocking)
        self.assertEqual(b["hanh_dong"][0]["nguon"], "thieu_tu_the")
        self.assertIn("hanh_dong[0].bat_dau.tu_the", {i["truong"] for i in si.validate(b) if i["muc"] == "do"})
        with self.assertRaises(ValueError):                    # nhịp không có trong blocking → báo, không im lặng bỏ
            si.from_shot_spec(dict(spec, nhip="khong_co"), blocking)


def test_k1a_optional_dang_and_che_fields():
    base = {"shot": 7, "thanh_phan": [{"vat": "yeunu", "vai": "chinh", "dang": {"bat_dau": "dang1", "ket_thuc": "dang2"}}],
            "may": {"co": "MLS"}, "noi_chon": {"kho_id": None},
            "hanh_dong": [{"ai": "yeunu", "bat_dau": {"tu_the": "quy", "che": ["mat", "eo"]}}]}
    fields = {i["truong"] for i in si.validate(base)}
    assert not any(f.startswith(("thanh_phan", "hanh_dong")) for f in fields)
    bad = dict(base, thanh_phan=[{"vat": "yeunu", "vai": "chinh", "dang": {"giua": "dang1"}}],
               hanh_dong=[{"ai": "yeunu", "bat_dau": {"tu_the": "quy", "che": ["bung_bu"]}}])
    fields = {i["truong"] for i in si.validate(bad) if i["muc"] == "do"}
    assert "thanh_phan[0].dang.giua" in fields and "hanh_dong[0].bat_dau.che" in fields
    b = si.from_shot_spec({"shot": 9, "thanh_phan": base["thanh_phan"], "hanh_dong": base["hanh_dong"]})
    assert b["hanh_dong"][0]["bat_dau"]["che"] == ["mat", "eo"] and b["hanh_dong"][0]["nguon"] == "shot_specs"


def _dryrun_mod():
    import importlib.util
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "dryrun_k0b_p24.py")
    spec = importlib.util.spec_from_file_location("dryrun_k0b_p24", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_k1a_dryrun_pose_is_per_character_not_shared():
    """Rà K1a: chạy khô suy tư thế từ chữ CHUNG cho mọi người trong shot → #24 S9 Kelly (ngồi) bị gán 'quy' vì chữ 'kneeling' của
    yêu nữ. Tư thế phải theo đoạn chữ gắn với từng nhân vật; chữ không gắn tên ai (nhiều người) → không suy, ghi lý do."""
    mod = _dryrun_mod()
    cfg = mod.project_config(24)
    spec = {"shot": 9, "thanh_phan": [{"vat": "kelly", "vai": "chinh"}, {"vat": "yeunu", "vai": "chinh"}], "co": "WS"}
    data = {"action": "Kelly sits on the ground on the left, the creature kneeling and crying on the right"}
    b, _i, _s, _n = mod.build_byd(spec, data, None, cfg)
    assert {h["ai"]: h["bat_dau"]["tu_the"] for h in b["hanh_dong"]} == {"kelly": "ngoi", "yeunu": "quy"}
    b, _i, suy, _n = mod.build_byd(spec, {"action": "kneeling in the fog"}, None, cfg)   # chữ không gọi tên ai, hai người
    assert not b["hanh_dong"] and any("không suy" in s for s in suy)
    one = dict(spec, thanh_phan=[{"vat": "kelly", "vai": "chinh"}])                      # một người → chữ là của người đó (như cũ)
    b, _i, _s, _n = mod.build_byd(one, {"action": "kneeling in the fog"}, None, cfg)
    assert [h["bat_dau"]["tu_the"] for h in b["hanh_dong"]] == ["quy"]


if __name__ == "__main__":
    unittest.main()
