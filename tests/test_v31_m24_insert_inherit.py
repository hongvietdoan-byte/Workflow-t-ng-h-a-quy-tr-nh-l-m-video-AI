"""V3.1 M2.4 (cloud-C 21/10, G6 / G21 / G1 — docs/V3_1_M2_THIET_KE_CON_LAI_2026-10-20.md §1):
- cờ `insert_inherit`: shot chèn (llm_io.insert_scene_after) thừa kế bối cảnh của shot `after_idx` (location_asset, location, time, weather,
  lighting, mood) khi người không truyền — không 🔒 (người không gõ), diag `insert_inherit` nói rõ; BYĐ NHÁP từ BYĐ shot trước
  (giữ noi_chon, thanh_phan lọc theo characters; bỏ hanh_dong / may / vat), `_p = {by: code, draft: true, from: <scene_id>}`;
  `byd.shot` của các shot sau theo shot_no; cổng video nói "BYĐ nháp" (VÀNG byd_draft) thay vì "chưa có BYĐ".
- cờ `stage_props_byd`: đạo cụ cảnh trước (cùng sân khấu) chỉ mang khi CÙNG thế giới (location_asset + time) VÀ BYĐ / chữ shot nhắc
  tên; bỏ thì ghi note "bỏ đạo cụ …".
Cờ TẮT = y cũ (dữ liệu không đổi một byte)."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import llm_io, shot_intent, video_pregen
from tests import test_insert_scene as _ti
from tests import test_stage_auto as _tsa

INHERIT_ON = {"FEATURE_INSERT_INHERIT": "1"}
INHERIT_OFF = {"FEATURE_INSERT_INHERIT": ""}
CTX = {"location_asset": 7, "location": "Mê cung", "time": "night", "weather": "rain", "lighting": "đèn đường", "mood": "căng"}
BYD = {"shot": 2, "thanh_phan": [{"vat": "KELLY", "vai": "chinh"}, {"vat": "MAX", "vai": "phu"}, {"vat": "xe", "vai": "phu"}],
       "noi_chon": {"kho_id": 7, "spot": "giua", "thoi_gian": "night", "thoi_tiet": "rain", "anh_sang": None},
       "hanh_dong": [{"ai": "KELLY", "bat_dau": "dung"}], "may": {"co": "MS", "chuyen_dong": "dung_yen"}, "vat": ["AWM"]}


class InsertInheritTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p, self.pid, self.ids = _ti.project()
        d = self.data_of(self.ids[6])
        d.update(CTX, byd=json.loads(json.dumps(BYD)))
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), self.ids[6]))
        for i, no in ((7, 3), (8, 4)):                  # cùng cảnh kịch bản 3: shot_no 3, 4 → BYĐ shot 3, 4
            d = self.data_of(self.ids[i])
            d["byd"] = {"shot": no, "thanh_phan": [{"vat": "KELLY", "vai": "chinh"}], "noi_chon": {}, "may": {}}
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), self.ids[i]))
        self.p.conn.commit()

    def data_of(self, sid):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"])

    def new_data(self, idx=7):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=?", (self.pid, idx)).fetchone()["data"])

    def insert(self, fields=None, env=INHERIT_ON):
        with mock.patch.dict(os.environ, env):
            return llm_io.insert_scene_after(self.p, self.pid, 6, dict(fields or _ti.NEW), data_dir=self.data)

    def test_flag_registered_off_golden_and_areas(self):
        from core import features
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        golden = json.load(open(os.path.join(root, "tests", "golden", "package_inputs.json"), encoding="utf-8"))
        areas = {a["id"]: a for a in json.load(open(os.path.join(root, "devsys", "areas.json"), encoding="utf-8"))["areas"]}
        for flag, area in (("insert_inherit", "step1"), ("stage_props_byd", "plates3d")):
            self.assertIs(features.FEATURES[flag]["verified"], False)
            with mock.patch.dict(os.environ, {f"FEATURE_{flag.upper()}": ""}):
                self.assertFalse(features.on(flag))
            self.assertTrue(all(golden[k]["flags"][flag] is False for k in ("image", "video")))
            self.assertIn(flag, areas[area]["flags"])
            self.assertIn("tests/test_v31_m24_insert_inherit.py", areas[area]["tests"])

    def test_flag_off_new_shot_has_no_context_and_no_byd(self):
        self.insert(env=INHERIT_OFF)
        d = self.new_data()
        self.assertFalse(set(CTX) & set(d))
        self.assertNotIn("byd", d)
        self.assertEqual(self.data_of(self.ids[7])["byd"]["shot"], 3)          # cũ: byd.shot không theo

    def test_context_is_inherited_not_locked_and_said(self):
        self.insert()
        d = self.new_data()
        for k, v in CTX.items():
            self.assertEqual(d[k], v, k)
        self.assertFalse(set(CTX) & set(d["_user_locked"]))
        msg = self.p.conn.execute("SELECT message FROM diag_events WHERE code='insert_inherit'").fetchone()
        self.assertIsNotNone(msg)
        self.assertIn("shot 6", msg["message"])
        self.assertIn("location_asset", msg["message"])

    def test_given_field_wins_over_the_inherited_one(self):
        self.insert(dict(_ti.NEW, time="day", weather="clear"))
        d = self.new_data()
        self.assertEqual((d["time"], d["weather"], d["location"]), ("day", "clear", "Mê cung"))
        self.assertIn("time", d["_user_locked"])

    def test_draft_byd_from_previous_shot(self):
        self.insert(dict(_ti.NEW, characters=["KELLY"]))
        b = self.new_data()["byd"]
        self.assertEqual(b["shot"], 3)                 # shot_no mới (cảnh 3 · shot 3)
        self.assertEqual(b["noi_chon"], dict(BYD["noi_chon"], spot=_ti.NEW["plate_spot"]))   # chỗ đứng = plate_spot shot mới
        self.assertEqual([c["vat"] for c in b["thanh_phan"]], ["KELLY"])     # lọc theo characters
        self.assertEqual(b["hanh_dong"], [])
        self.assertNotIn("vat", b)                     # vật phải khai lại: thiếu khóa = chưa rõ (không phải "không cầm gì")
        self.assertNotIn("co", b.get("may") or {})
        self.assertEqual({k: b["_p"][k] for k in ("by", "draft", "from")}, {"by": "code", "draft": True, "from": self.ids[6]})
        self.assertTrue(shot_intent.is_draft(b))

    def test_without_characters_all_parts_kept(self):
        self.insert()
        self.assertEqual([c["vat"] for c in self.new_data()["byd"]["thanh_phan"]], ["KELLY", "MAX", "xe"])

    def test_no_byd_on_previous_shot_means_no_draft_and_said(self):
        d = self.data_of(self.ids[6])
        d.pop("byd")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), self.ids[6]))
        self.p.conn.commit()
        self.insert()
        self.assertNotIn("byd", self.new_data())
        msg = self.p.conn.execute("SELECT message FROM diag_events WHERE code='insert_inherit'").fetchone()["message"]
        self.assertIn("không có BYĐ", msg)

    def test_later_byd_shot_numbers_follow(self):
        self.insert()
        self.assertEqual(self.data_of(self.ids[7])["byd"]["shot"], 4)
        self.assertEqual(self.data_of(self.ids[8])["byd"]["shot"], 5)
        self.assertEqual(self.data_of(self.ids[6])["byd"]["shot"], 2)

    def test_exception_scope_follows_the_shot_number(self):
        from core import lock_exceptions
        d = self.data_of(self.ids[7])
        d["byd"]["ngoai_le"] = [{"doi_tuong": "KELLY", "pham_vi": [3], "dieu_trai": "không có glitch", "cach_hien": "ảnh sạch"}]
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), self.ids[7]))
        self.p.conn.commit()
        before = lock_exceptions.for_shot(d)
        self.assertTrue(before)
        self.insert()
        after = self.data_of(self.ids[7])
        self.assertEqual(after["byd"]["ngoai_le"][0]["pham_vi"], [4])
        self.assertEqual(lock_exceptions.for_shot(after), before)

    def test_new_place_and_spot_override_the_drafted_place(self):
        self.insert(dict(_ti.NEW, location_asset=9))
        nc = self.new_data()["byd"]["noi_chon"]
        self.assertEqual((nc["kho_id"], nc["spot"]), (9, _ti.NEW["plate_spot"]))
        self.assertEqual(nc["thoi_gian"], "night")

    def test_draft_is_schema_known_and_picked_for_repair(self):
        self.insert()
        issues = shot_intent.validate(self.new_data()["byd"])
        self.assertFalse([i for i in issues if i["truong"] == "_p"])
        self.assertTrue(issues)                        # máy chưa điền → vẫn lỗi → vòng điền BYĐ nhận shot này

    def test_filled_draft_is_checked_as_usual(self):
        self.insert()
        sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=7", (self.pid,)).fetchone()["id"]
        d = self.new_data()
        d["byd"]["may"] = {"co": "MS"}                 # điền máy nhưng quên chuyển động
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), sid))
        out = []
        video_pregen._check_motion(self.p.conn, sid, {}, out)
        self.assertEqual([i["ma"] for i in out], ["byd_draft", "chuyen_dong"])

    def test_video_gate_says_draft_not_missing(self):
        self.insert()
        sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=7", (self.pid,)).fetchone()["id"]
        out = []
        video_pregen._check_motion(self.p.conn, sid, {}, out)
        self.assertEqual([i["ma"] for i in out], ["byd_draft"])
        self.assertIn("nháp", out[0]["ly_do"])
        self.assertIn("shot 6", out[0]["ly_do"])
        self.assertEqual(out[0]["muc"], video_pregen.VANG)


class StagePropsBydTests(_tsa.Base):
    PREV = {"scene": "1", "objects": {"xenoi": {"at_model": [4.4, 2.6, 0.0], "kind": "dao_cu", "h": 1.0, "d": 0.6, "label": "Xe nôi"},
                                      "kelly": {"at_model": [3.4, 2.1, 0.0], "kind": "nguoi", "facing": 0}}}

    def inputs(self, pid, env):
        from core import stage_auto
        seg = stage_auto.segments(self.p.conn, pid)[1]
        k1 = stage_auto.ensure_k1(seg["entry"], seg["main_spot"], stage_auto.base_dir(self.data, pid, seg["stage"]))
        with mock.patch.dict(os.environ, env):
            return stage_auto.inputs_for(self.p.conn, pid, seg, k1, json.loads(json.dumps(self.PREV)))[0]

    def keys(self, inputs):
        return [o["key"] for o in inputs["fixed"]]

    def set_shot(self, pid, idx, **kw):
        d = self.shot(pid, idx)
        d.update(kw)
        self.p.conn.execute("UPDATE scenes SET data=? WHERE project_id=? AND idx=?", (json.dumps(d, ensure_ascii=False), pid, idx))
        self.p.conn.commit()

    def test_flag_off_still_carries_every_prop(self):
        pid = self.project(((1, "giua_phong"), (2, "giua_phong")))
        self.assertIn("xenoi", self.keys(self.inputs(pid, {"FEATURE_STAGE_PROPS_BYD": ""})))

    def test_prop_not_named_is_dropped_with_a_note(self):
        pid = self.project(((1, "giua_phong"), (2, "giua_phong")))
        got = self.inputs(pid, {"FEATURE_STAGE_PROPS_BYD": "1"})
        self.assertNotIn("xenoi", self.keys(got))
        self.assertTrue(any("bỏ đạo cụ" in n and "Xe nôi" in n and "cảnh 1" in n for n in got["user_notes"]))
        self.assertFalse(any("`xenoi`" in n and "GIỮ" in n for n in got["user_notes"]))     # không còn "GIỮ chỗ" cho vật đã bỏ

    def test_prop_named_in_shot_text_or_byd_is_kept(self):
        pid = self.project(((1, "giua_phong"), (2, "giua_phong")))
        self.set_shot(pid, 2, action="Kelly đẩy xe nôi qua phòng")
        self.assertIn("xenoi", self.keys(self.inputs(pid, {"FEATURE_STAGE_PROPS_BYD": "1"})))
        self.set_shot(pid, 2, action="Kelly đứng", byd={"shot": 1, "vat": ["xenoi"]})
        self.assertIn("xenoi", self.keys(self.inputs(pid, {"FEATURE_STAGE_PROPS_BYD": "1"})))
        self.set_shot(pid, 2, byd={"shot": 1, "thanh_phan": [{"vat": "xenoi", "vai": "phu"}]})
        self.assertIn("xenoi", self.keys(self.inputs(pid, {"FEATURE_STAGE_PROPS_BYD": "1"})))

    def test_unknown_or_synonym_time_is_not_another_world(self):
        pid = self.project(((1, "giua_phong"), (2, "giua_phong")))
        self.set_shot(pid, 2, action="Kelly đẩy xe nôi", time=None)
        self.assertIn("xenoi", self.keys(self.inputs(pid, {"FEATURE_STAGE_PROPS_BYD": "1"})))
        self.set_shot(pid, 2, time="ban ngày")                                 # = day (plate_env.time_of)
        self.assertIn("xenoi", self.keys(self.inputs(pid, {"FEATURE_STAGE_PROPS_BYD": "1"})))

    def test_flag_on_without_a_drop_keeps_the_inputs(self):
        pid = self.project(((1, "giua_phong"), (2, "giua_phong")))
        self.set_shot(pid, 2, action="Kelly đẩy xe nôi")
        self.assertEqual(self.inputs(pid, {"FEATURE_STAGE_PROPS_BYD": "1"}), self.inputs(pid, {"FEATURE_STAGE_PROPS_BYD": ""}))

    def test_other_world_drops_the_prop_even_if_named(self):
        pid = self.project(((1, "giua_phong"), (2, "giua_phong")))
        self.set_shot(pid, 2, action="Kelly đẩy xe nôi", time="night")         # thực tại ↔ song song: đổi giờ = thế giới khác
        got = self.inputs(pid, {"FEATURE_STAGE_PROPS_BYD": "1"})
        self.assertNotIn("xenoi", self.keys(got))
        self.assertTrue(any("bỏ đạo cụ" in n and "thế giới" in n for n in got["user_notes"]))


if __name__ == "__main__":
    unittest.main()


class DraftProvenanceTests(unittest.TestCase):
    """Tích hợp M2 VỪA-2 (DP9/M2.4 × M2.1): BYĐ nháp dùng MỘT nguồn provenance — `_p` của M2.1 {by, model, at, revision} thêm
    `draft` (bool) + `from` (scene id); nháp là BYĐ v2 (`_p` chỉ hợp lệ ở v2); mọi nơi đọc nháp qua shot_intent.is_draft / draft_source."""

    def draft(self):
        return shot_intent.draft_of({"byd": dict(BYD)}, 3, 41)

    def test_draft_is_v2_and_its_provenance_is_valid(self):
        b = self.draft()
        self.assertEqual(shot_intent.version(b), shot_intent.BYD_V)
        self.assertFalse([i for i in shot_intent.validate(b) if i["truong"].startswith("_p")])
        self.assertEqual(shot_intent.draft_source(b), 41)
        self.assertIsNone(shot_intent.draft_source(dict(BYD)))

    def test_bad_draft_keys_are_said(self):
        b = self.draft()
        b["_p"].update(draft="có", **{"from": "shot 6"})
        bad = {i["truong"] for i in shot_intent.validate(b)}
        self.assertTrue({"_p.draft", "_p.from"} <= bad)

    def test_image_gate_reads_the_draft_through_shot_intent(self):
        from core import image_pregen
        out = []
        conn = mock.Mock()
        conn.execute.return_value.fetchone.return_value = {"idx": 7}
        with mock.patch.object(shot_intent, "draft_source", return_value=99) as src:
            image_pregen._check_byd(conn, 1, {}, {"byd": self.draft()}, out)
        self.assertTrue(src.called)
        self.assertEqual(conn.execute.call_args[0][1], (99,))
        self.assertEqual([i["ma"] for i in out], ["byd_draft"])
        self.assertIn("từ shot 7", out[0]["ly_do"])                       # số shot như cổng video, không phải scene id

    def test_moved_place_drops_the_inferred_indoor_flag(self):
        src = {"byd": dict(BYD, noi_chon=dict(BYD["noi_chon"], trong_nha=True))}
        self.assertTrue(shot_intent.draft_of(src, 3, 41)["noi_chon"]["trong_nha"])
        self.assertNotIn("trong_nha", shot_intent.draft_of(src, 3, 41, spot="ngoai_troi")["noi_chon"])
