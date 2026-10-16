"""16/10 cờ stage_handheld_props (#31 cảnh 3: súng SKORP hiện ra ở xe nôi rồi nằm trong tay Kelly — không phải vật dàn cảnh nên
không đo được 'thấy súng'): vũ khí Kho vào dàn cảnh như đạo cụ theo nhịp; `cam_tay` → code tính điểm tay; Blender mỗi chỗ một khối."""
import os
import unittest
from unittest import mock

from core import llm_io, stage_auto, stage_director as sd, stage_solver as ss
from tests.test_stage_auto import Base

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def blocking():
    return {"objects": [{"key": "kelly", "kind": "nguoi", "at": [0.0, 0.0], "H": 1.7, "facing": 0, "label": "Kelly"},
                        {"key": "xenoi", "kind": "dao_cu", "at": [1.0, 0.0], "h": 0.9, "d": 0.6},
                        {"key": "skorp", "kind": "dao_cu", "at": [1.0, 0.0], "z": 0.9, "h": 0.2, "d": 0.6, "cam_duoc": True}],
            "beats": {"n1": {"skorp": {"hidden": True}},
                      "n2": {},
                      "n3": {"skorp": {"cam_tay": "kelly", "tay": "phai"}},
                      "n4": {"kelly": {"H": 1.2, "tu_the": "quy"}, "skorp": {"cam_tay": "kelly", "tay": "phai"}},
                      "n5": {"skorp": {"at": [-1.0, 0.0]}}}}


class HandTests(unittest.TestCase):
    def test_hand_point_follows_facing_side_and_pose(self):
        x, y, z = ss.hand_point({"key": "k", "xy": [0.0, 0.0], "H": 1.7, "facing": 0})
        self.assertAlmostEqual((x, y, z), (0.0, ss.HAND_FWD_M, 0.55 * 1.7))
        x, y, _ = ss.hand_point({"key": "k", "xy": [0.0, 0.0], "H": 1.7, "facing": 0}, "phai")
        self.assertAlmostEqual((x, y), (ss.HAND_SIDE_M, ss.HAND_FWD_M))      # mặt về Bắc → tay phải ở phía Đông
        x, y, _ = ss.hand_point({"key": "k", "xy": [0.0, 0.0], "H": 1.7, "facing": 90}, "trai")
        self.assertAlmostEqual(x, ss.HAND_FWD_M)
        self.assertAlmostEqual(y, ss.HAND_SIDE_M)                            # mặt về Đông → tay trái ở phía Bắc
        with self.assertRaisesRegex(ValueError, "facing"):
            ss.hand_point({"key": "k", "xy": [0, 0], "H": 1.7, "facing": None})
        with self.assertRaisesRegex(ValueError, "tư thế nam"):
            ss.hand_point({"key": "k", "xy": [0, 0], "H": 1.7, "facing": 0, "tu_the": "nam"})

    def test_prop_per_beat_hidden_placed_held_put_down(self):
        bl = blocking()
        self.assertNotIn("skorp", ss.objects_from_blocking(bl, beat="n1"))   # chưa xuất hiện
        on_cot = ss.objects_from_blocking(bl, beat="n2")["skorp"]
        self.assertEqual((on_cot["xy"], on_cot["z"], on_cot.get("cam_duoc")), ([1.0, 0.0], 0.9, True))
        held = ss.objects_from_blocking(bl, beat="n3")["skorp"]
        self.assertEqual(held["held_by"], "kelly")
        self.assertAlmostEqual(held["xy"][0], ss.HAND_SIDE_M)
        self.assertAlmostEqual(held["z"], round(0.55 * 1.7 - 0.1, 3))        # z = đáy khối, tâm ở tay
        kneel = ss.objects_from_blocking(bl, beat="n4")["skorp"]
        self.assertAlmostEqual(kneel["z"], round(0.46 * 1.2 - 0.1, 3))
        down = ss.objects_from_blocking(bl, beat="n5")["skorp"]
        self.assertEqual((down["xy"], down.get("held_by")), ([-1.0, 0.0], None))   # `at` không `cam_tay` = đặt xuống

    def test_holder_absent_is_error(self):
        bl = blocking()
        bl["beats"]["n3"]["kelly"] = {"hidden": True}
        with self.assertRaisesRegex(ValueError, "cầm tay 'kelly'"):
            ss.objects_from_blocking(bl, beat="n3")

    def test_handheld_without_place_is_schema_error(self):
        from core import stage_crew as sc
        bl = blocking()
        bl["objects"][2].pop("at")
        bl["beats"]["n2"]["skorp"] = {"_ly_do": "quên chỗ"}
        bl["shot_nhip"] = {"1": "n2"}
        inputs = {"auto": True, "fixed": [{"key": "xenoi", "kind": "dao_cu", "h": 0.9, "d": 0.6},
                                          {"key": "skorp", "kind": "dao_cu", "h": 0.2, "d": 0.6, "cam_duoc": True}],
                  "shots": [{"shot": 1, "nhan_vat": ["kelly"]}]}
        with self.assertRaisesRegex(llm_io.SchemaError, "'skorp' không có `at`"):
            sc.validate_blocking({"blocking": bl}, inputs)

    def test_flag_needs_stage_auto_and_is_opt_in(self):
        from core import features
        self.assertEqual(features.REQUIRES["stage_handheld_props"], ("stage_auto",))
        self.assertIn("stage_handheld_props", features.OPT_IN_ONLY)          # bật = đầu vào cảnh có vũ khí đổi → chỉ bật tay
        self.assertFalse(features.FEATURES["stage_handheld_props"].get("default_on"))

    def test_blocking_errors_cam_tay_only_for_handheld(self):
        fixed = [{"key": "xenoi", "kind": "dao_cu", "h": 0.9, "d": 0.6},
                 {"key": "skorp", "kind": "dao_cu", "h": 0.2, "d": 0.6, "cam_duoc": True}]
        bl = blocking()
        bl["objects"][2].pop("cam_duoc")
        self.assertEqual(sd.blocking_errors(bl, {"auto": True, "fixed": fixed}), [])
        self.assertTrue(bl["objects"][2]["cam_duoc"])                        # code gắn lại dữ kiện của Kho
        bad = blocking()
        bad["beats"]["n2"]["xenoi"] = {"cam_tay": "kelly"}
        bad["beats"]["n3"]["skorp"]["tay"] = "chan"
        bad["beats"]["n4"]["skorp"]["cam_tay"] = "yeunu"
        errs = " | ".join(sd.blocking_errors(bad, {"auto": True, "fixed": fixed}))
        self.assertIn("'xenoi' không phải đồ cầm tay", errs)
        self.assertIn("tay 'chan'", errs)
        self.assertIn("cam_tay 'yeunu'", errs)

    def test_held_prop_not_an_overlap(self):
        objs = ss.objects_from_blocking(blocking(), beat="n3")
        self.assertEqual(sd.overlap_errors(objs), [])

    def test_blender_one_block_per_place(self):
        tool = stage_auto.tool()
        bl = blocking()
        beats = {n: ss.objects_from_blocking(bl, beat=n) for n in ("n2", "n3", "n5")}
        props = {p["name"]: p for p in tool.blender_props(beats) if p["kind"] == "block"}
        self.assertIn("PROP_XENOI", props)                                    # một chỗ: tên cũ
        sk = sorted(n for n in props if n.startswith("PROP_SKORP"))
        self.assertEqual(sk, ["PROP_SKORP_V0", "PROP_SKORP_V1", "PROP_SKORP_V2"])
        self.assertEqual(props["PROP_SKORP_V0"]["z"], 0.9)
        self.assertNotEqual(beats["n2"]["skorp"]["prop"], beats["n3"]["skorp"]["prop"])
        self.assertEqual(beats["n3"]["skorp"]["own"], f"STAGE_{beats['n3']['skorp']['prop']}_")

    def test_cameras_skip_handheld_blocks(self):
        objs = ss.objects_from_blocking(blocking(), beat="n3")
        v2 = {"shots": [{"shot": 1, "spec": {}, "objs": objs,
                         "best": {"ok": True, "tag": "t", "m": {"at": [2.0, 0.0, 1.0], "aim": [0.0, 0.0, 1.0], "lens": 35.0}}}]}
        stage = {"origin_model": [0, 0, 0], "factor": 1.0, "north": "+y", "east": "+x"}
        with mock.patch.object(stage_auto, "_model", side_effect=lambda st, p: list(p)):
            cams, _ = stage_auto.cameras_from(stage, v2, "doan_1", "rd")
        self.assertEqual([p["label"] for p in cams[1]["props"]], ["xenoi"])    # súng chỉ để đo, không vẽ vào ảnh nền


class InputsTests(Base):
    WEAPON = [{"id": 5, "name": "SKORP", "kind": "weapon", "size": {"height_m": 0.25, "length_m": 0.55, "width_m": 0.06}},
              {"id": 6, "name": "UMP", "kind": "weapon", "size": {}}]

    def inputs(self, on):
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        k1 = stage_auto.ensure_k1(seg["entry"], seg["main_spot"], stage_auto.base_dir(self.data, pid, seg["stage"]))
        with mock.patch("core.place_refs.shot_objects", return_value=self.WEAPON), \
                mock.patch.dict(os.environ, {"FEATURE_STAGE_HANDHELD_PROPS": "1" if on else "0"}):
            return stage_auto.inputs_for(self.p.conn, pid, seg, k1)

    def test_flag_off_unchanged(self):
        inputs, missing = self.inputs(False)
        self.assertEqual((missing, [o for o in inputs["fixed"] if o["kind"] == "dao_cu"]), ([], []))

    def test_flag_on_weapon_with_size_is_handheld_without_size_noted(self):
        inputs, missing = self.inputs(True)
        self.assertEqual(missing, [])                                         # thiếu cỡ không chặn cả cảnh …
        self.assertIn({"key": "skorp", "kind": "dao_cu", "label": "SKORP", "h": 0.25, "d": 0.55, "cam_duoc": True,
                       "source": "Kho #5 size"}, inputs["fixed"])
        notes = "\n".join(inputs["user_notes"])
        self.assertIn("UMP", notes)                                           # … nhưng nói rõ không đo được
        self.assertIn("cam_tay", notes)

    def test_size_from_kho_scale_sentence(self):
        # 16/10 người dùng: Kho có ảnh Kelly cầm SKORP → mô tả "≈ 3 head-heights long" (tập 1 dùng) — không có số đo thì suy từ đó
        self.WEAPON = [{"id": 7, "name": "SKORP", "kind": "weapon", "size": None,
                        "description": "Súng tiểu liên. In-game scale: compact SMG ≈ 3 head-heights long (stock to muzzle)."}]
        inputs, _ = self.inputs(True)                                       # id 7 không có hồ sơ → chỉ đọc mô tả
        sk = next(o for o in inputs["fixed"] if o["key"] == "skorp")
        H = next(p["H"] for p in inputs["people"])
        self.assertAlmostEqual(sk["d"], round(3 * H / 7.5, 3))
        self.assertAlmostEqual(sk["h"], round(0.3 * sk["d"], 3))
        self.assertIn("ước tính từ tỉ lệ Kho #7", sk["source"])
        for text, want in (("In-game scale: 3,5 head-heights long.", 3.5), ("Tỉ lệ: dài 2 đầu người.", 2.0),
                           ("In-game scale: 2–3 head-heights long.", None), ("Tỉ lệ: 1 đầu đạn đỏ.", None),
                           ("Súng OB55 heads.", None), ("no scale", None)):
            r = stage_auto.weapon_size_from_scale(self.p.conn, {"id": 999, "name": "X", "description": text}, 1.5)
            self.assertEqual(r and round(r[1] / (1.5 / 7.5), 3), want, text)

    def test_size_fills_only_missing_part(self):
        self.WEAPON = [{"id": 8, "name": "SKORP", "kind": "weapon", "size": {"height_m": 0.25},
                        "description": "In-game scale: compact SMG ≈ 3 head-heights long.", "characters": [{"x": 1}]}]
        inputs, _ = self.inputs(True)
        sk = next(o for o in inputs["fixed"] if o["key"] == "skorp")
        self.assertEqual(sk["h"], 0.25)                                       # số đo Kho giữ nguyên
        self.assertIn("Kho #8 size + ước tính", sk["source"])

    def test_scene_placed_before_flag_keeps_old_inputs(self):
        # người dùng 16/10: bật cờ cho cảnh MỚI, cảnh đã duyệt giữ nguyên (không đổi vân tay → không gỡ máy, không gọi API lại)
        import json as _j
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        base = stage_auto.base_dir(self.data, pid, seg["stage"])
        k1 = stage_auto.ensure_k1(seg["entry"], seg["main_spot"], base)
        seg_dir = os.path.join(base, f"doan_{stage_auto.key_of(seg['scene'])}")
        os.makedirs(os.path.join(seg_dir, "crew", "final"), exist_ok=True)
        with open(os.path.join(seg_dir, "crew", "final", "inputs.json"), "w", encoding="utf-8") as f:
            _j.dump({"fixed": []}, f)
        with open(os.path.join(seg_dir, "result.json"), "w", encoding="utf-8") as f:
            _j.dump({"cams": {"1": {}}, "round": "crew/final", "fp": "x"}, f)
        with mock.patch("core.place_refs.shot_objects", return_value=self.WEAPON), \
                mock.patch.dict(os.environ, {"FEATURE_STAGE_HANDHELD_PROPS": "1"}):
            old, _ = stage_auto.inputs_for(self.p.conn, pid, seg, k1)
            with mock.patch.dict(os.environ, {"FEATURE_STAGE_HANDHELD_PROPS": "0"}):
                off, _ = stage_auto.inputs_for(self.p.conn, pid, seg, k1)
            self.assertEqual(stage_auto.fingerprint(old), stage_auto.fingerprint(off))
            with open(os.path.join(seg_dir, "crew", "final", "inputs.json"), "w", encoding="utf-8") as f:
                _j.dump({"fixed": [{"key": "skorp", "cam_duoc": True}]}, f)            # lượt đã dựng CÓ đồ cầm tay → giữ bật
            again, _ = stage_auto.inputs_for(self.p.conn, pid, seg, k1)
        self.assertTrue(any(o.get("cam_duoc") for o in again["fixed"]))

class PlacedLockTests(unittest.TestCase):
    """placed_without_handheld: đoạn đã dàn (không đồ cầm tay) giữ đầu vào cũ; cảnh mới / --cam-tay thì bật."""

    def setUp(self):
        import tempfile
        self.base = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.base, True)
        self.k1 = os.path.join(self.base, "k1_x")
        self.seg_dir = os.path.join(self.base, "doan_3")
        os.makedirs(self.seg_dir)

    def write(self, rel, obj):
        import json as _j
        p = os.path.join(self.seg_dir, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            _j.dump(obj, f)

    def lock(self):
        return stage_auto.placed_without_handheld(self.k1, {"scene": "3"})

    def test_new_scene_or_no_cams_not_locked(self):
        self.assertFalse(self.lock())                                     # chưa có result.json
        self.write("result.json", {"cams": {}, "round": "r1"})
        self.assertFalse(self.lock())                                     # chưa gán máy nào

    def test_api_round_falls_back_to_segment_inputs(self):
        self.write("result.json", {"cams": {"1": {}}, "round": "r2"})       # lượt API: inputs.json ở thư mục đoạn
        self.write("inputs.json", {"fixed": [{"key": "skorp", "cam_duoc": True}]})
        self.assertFalse(self.lock())
        self.write("inputs.json", {"fixed": [{"key": "xenoi"}]})
        self.assertTrue(self.lock())

    def test_redo_env_unlocks(self):
        self.write("result.json", {"cams": {"1": {}}, "round": "r1"})
        self.assertTrue(self.lock())                                      # không có inputs nào → coi là dàn cũ
        with mock.patch.dict(os.environ, {stage_auto.HANDHELD_REDO_ENV: "1"}):
            self.assertFalse(self.lock())

if __name__ == "__main__":
    unittest.main()
