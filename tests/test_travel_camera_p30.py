"""14/10 #30 shot 1 (scene 302): Kelly chạy LÊN cầu thang A `bac_thang_giua` (z 3,9) → B `dinh_bac_thang_giua` (z 8,5), shot 2 đứng ở B.
Người dùng: "máy đi theo nhân vật còn nhân vật chạy lên, hoặc máy ở trên cao lùi, nhân vật chạy lên theo máy". Trước: máy 3D luôn đứng
tại chỗ đứng của shot (chân cầu thang) → travel_truth báo "chữ nói chạy VỀ PHÍA máy nhưng máy đứng sau lưng hướng chạy".
(b) máy đặt theo camera_move trên đường A→B · (c) chữ ↔ nền trái nhau → chặn trước gen · (d) không tiếng Việt trong câu hướng chạy ·
(e) ảnh Kho có hình nộm không làm ảnh đại diện vật. Dữ liệu: tests/fixtures/p30_payload.json (trích CSDL thật), 0 USD."""
import json
import math
import os
import unittest
from unittest import mock

from core import assets, location_pack, plate_choice, prop_lock, travel_truth
from tests.test_replay_payload_p30 import P30Base, SKIN

ON = {"FEATURE_TRAVEL_TRUTH": "1", "FEATURE_DIRECTOR_CAMERA_PLAN": "0", "FEATURE_STAGE_CAMERA": "0"}
OFF = dict(ON, FEATURE_TRAVEL_TRUTH="0")
WHY_AWAY = ("camera đối mặt Kelly khi cô chạy lên, tháp nằm phía sau máy nên chưa vào khung — giữ cho cú lật trục ở shot sau có tác "
            "dụng bất ngờ · code đổi scenery→away: mốc nằm sau lưng máy")


def _ang(a, b):
    return abs((a - b + 180) % 360 - 180)


class TravelCameraP30(P30Base):
    def setUp(self):
        super().setUp()
        m = dict(self.fx["model3d"], sha256="p30test")          # cache_key needs the model's hash
        self.p.conn.execute("UPDATE assets SET profile=? WHERE id=263", (json.dumps({"model3d": m}, ensure_ascii=False),))
        self.edit(1, camera_move="pull_out", plate_view={"background": "away", "why": WHY_AWAY})   # = CSDL thật hiện nay
        spots = self.fx["model3d"]["spots"]
        self.A, self.B = spots["bac_thang_giua"]["at"], spots["dinh_bac_thang_giua"]["at"]

    def edit(self, idx, **fields):
        row = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.ids[idx],)).fetchone()
        data = dict(json.loads(row["data"]), **fields)
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), self.ids[idx]))
        self.p.conn.commit()
        return data

    def data(self, idx):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.ids[idx],)).fetchone()["data"])

    def plan(self, env):
        with mock.patch.dict(os.environ, env):
            return {it["scene_id"]: it for it in location_pack.plan(self.p.conn, self.pid)}

    def t_of(self, cam):
        ax, ay, bx, by = self.A[0], self.A[1], self.B[0], self.B[1]
        return ((cam[0] - ax) * (bx - ax) + (cam[1] - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)

    # (b) ------------------------------------------------------------------------------------------------------------------------
    def test_shot1_camera_leads_up_the_stairs_and_looks_back_at_a(self):
        it = self.plan(ON)[self.ids[1]]
        cam = it["camera"]
        t = self.t_of(cam["location"])
        self.assertTrue(0 < t < 0.5, t)                                       # ON the run, ahead of Kelly (B side)
        side = math.hypot(*[c - (a + t * (b - a)) for c, a, b in zip(cam["location"][:2], self.A[:2], self.B[:2])])
        self.assertLess(side, 0.6)                                            # on the line A→B (frame centre: no side offset)
        ground = self.A[2] + t * (self.B[2] - self.A[2])
        self.assertGreater(cam["location"][2], self.A[2] + 1.7 * 0.93)        # higher than Kelly's eyes at A (stairs rise)
        self.assertTrue(0.8 < cam["location"][2] - ground < 2.0, cam["location"][2] - ground)   # eye height above ITS ground
        look = plate_choice.bearing(cam["location"], cam["look_at"])
        self.assertLess(_ang(look, plate_choice.bearing(self.B, self.A)), 3)    # looking back down at A
        self.assertIsNone(it["needs"])
        self.assertIsNone(it["travel_problem"])
        self.assertIn("travel", it["camera_why"])
        with mock.patch.dict(os.environ, ON):                                 # the conflict of the brief is gone
            got = travel_truth.for_shot(self.p.conn, self.pid, self.ids[1], self.data(1), {"camera_plan": cam})
        self.assertEqual(got["facts"]["relation"], "toward")
        self.assertEqual(got["warn"], [])
        self.assertIsNone(got["needs"])
        self.assertIn("TOWARD the camera", got["sentence"])
        self.assertIn("UP the stairs", got["sentence"])

    def test_flag_off_and_shots_without_a_run_keep_their_camera(self):
        on, off = self.plan(ON), self.plan(OFF)
        self.assertNotEqual(on[self.ids[1]]["camera"]["location"], off[self.ids[1]]["camera"]["location"])
        old = off[self.ids[1]]["camera"]                                       # flag off: at A, looking along the plate_view
        self.assertLess(math.hypot(old["location"][0] - self.A[0], old["location"][1] - self.A[1]), 2.0)
        for idx in range(2, 8):                                                # shot 2 orbit (arriving), 3–7 on the top landing
            sid = self.ids[idx]
            self.assertEqual(on[sid]["camera"], off[sid]["camera"], f"shot {idx}")
            self.assertEqual(on[sid]["key"], off[sid]["key"], f"shot {idx}")
            self.assertIsNone(on[sid]["travel_problem"], f"shot {idx}")

    def test_follow_camera_stands_behind_and_looks_towards_b(self):
        words = "Kelly runs up the stone stairs, the camera follows behind her"
        self.edit(1, camera_move="track", shot="medium long shot, tracking behind", image_prompt=words, blocking="Kelly center frame",
                  action=words, text=words,
                  action_peak="", plate_view={"background": "landmark", "why": "giữ tháp ở nền khi Kelly chạy lên"})
        it = self.plan(ON)[self.ids[1]]
        cam = it["camera"]
        self.assertLess(self.t_of(cam["location"]), 0)                        # behind A (on the line, A side)
        self.assertLess(_ang(plate_choice.bearing(cam["location"], cam["look_at"]), plate_choice.bearing(self.A, self.B)), 3)
        self.assertIsNone(it["needs"])
        with mock.patch.dict(os.environ, ON):
            got = travel_truth.for_shot(self.p.conn, self.pid, self.ids[1], self.data(1), {"camera_plan": cam})
        self.assertEqual(got["facts"]["relation"], "away")
        self.assertIsNone(got["needs"])

    def test_no_destination_keeps_the_camera_and_says_so(self):
        self.edit(1, continuous_with_next=False)
        on, off = self.plan(ON), self.plan(OFF)
        self.assertEqual(on[self.ids[1]]["camera"], off[self.ids[1]]["camera"])
        self.assertIn("giữ chỗ cũ", on[self.ids[1]]["travel_problem"])

    def test_both_meanings_is_yellow_not_a_guess(self):
        self.edit(1, shot="medium long shot, pull out, camera follows behind her")
        on, off = self.plan(ON), self.plan(OFF)
        self.assertEqual(on[self.ids[1]]["camera"], off[self.ids[1]]["camera"])
        self.assertIn("không đoán", on[self.ids[1]]["travel_problem"])

    def test_pulling_out_a_gun_is_not_a_camera_move(self):
        words = "Kelly pulls out her SKORP while running up the stairs"
        self.edit(1, camera_move="static", shot="medium long shot, eye angle", image_prompt=words, action=words, text=words,
                  blocking="", action_peak="")
        on, off = self.plan(ON), self.plan(OFF)
        self.assertEqual(on[self.ids[1]]["camera"], off[self.ids[1]]["camera"])
        self.assertIsNone(on[self.ids[1]]["travel_problem"])
        self.assertIsNone(on[self.ids[1]]["needs"])

    def test_plate_view_against_the_run_blocks(self):
        self.edit(1, plate_view={"background": "landmark", "why": "giữ tháp ở nền"})
        it = self.plan(ON)[self.ids[1]]
        self.assertIn("trái máy đặt theo đường chạy", it["needs"] or "")
        from core import autopilot
        self.assertEqual(autopilot.needs_code(it["needs"]), "travel_truth")     # rà 14/10: không phải mã plate_view

    # (c) ------------------------------------------------------------------------------------------------------------------------
    def test_words_against_the_render_block_before_generation(self):
        """No leading camera (orbit) + the plate looks along the run (landmark) while the words say 'toward camera' → needs."""
        self.edit(1, camera_move="orbit", plate_view={"background": "landmark", "why": "giữ tháp ở nền"})
        on, off = self.plan(ON), self.plan(OFF)
        self.assertIn("hướng chạy trái nền 3D", on[self.ids[1]]["needs"] or "")
        self.assertIsNone(off[self.ids[1]]["needs"])                          # flag off: as before
        from core import autopilot
        self.assertEqual(autopilot.needs_code(on[self.ids[1]]["needs"]), "travel_truth")
        self.assertEqual(autopilot.needs_code("shot chưa ghi hướng máy (`plate_view`)"), "plate_view")

    # (d) ------------------------------------------------------------------------------------------------------------------------
    def test_travel_sentence_has_no_vietnamese(self):
        rec = self.fx["plates"][str(self.fx["shots"][0]["scene_id"])]
        with mock.patch.dict(os.environ, ON):
            s = travel_truth.for_shot(self.p.conn, self.pid, self.ids[1], self.data(1), rec)["sentence"]
        self.assertIn("from the foot of the stairs (ground 3.9 m) to the top of the stairs (8.5 m)", s)
        self.assertFalse([ch for ch in s if ord(ch) > 127 and ch not in "—–°"], s)
        spots = self.fx["model3d"]["spots"]
        m = dict(self.fx["model3d"], sha256="p30test",
                 spots=dict(spots, bac_thang_giua=dict(spots["bac_thang_giua"], label_en="the foot of the long stone stairs")))
        self.p.conn.execute("UPDATE assets SET profile=? WHERE id=263", (json.dumps({"model3d": m}, ensure_ascii=False),))
        with mock.patch.dict(os.environ, ON):
            s = travel_truth.for_shot(self.p.conn, self.pid, self.ids[1], self.data(1), rec)["sentence"]
        self.assertIn("from the foot of the long stone stairs (ground 3.9 m)", s)

    def test_ascii_vietnamese_label_is_not_put_in_the_prompt(self):
        """rà 14/10: nhãn không dấu 'chan cau thang' vẫn là tiếng Việt — chỉ label_en, còn lại câu trung tính."""
        self.assertEqual(travel_truth._label_en({"label": "chan cau thang"}, True, True), "the foot of the stairs")
        self.assertEqual(travel_truth._label_en({"label": "dinh cau thang"}, False, True), "the top of the stairs")
        self.assertEqual(travel_truth._label_en({"label": "x", "label_en": "the old well"}, True, True), "the old well")

    # rà 14/10 (gộp tập 2) ---------------------------------------------------------------------------------------------------------
    def test_approved_stage_camera_is_yellow_not_blocked_nor_same_point(self):
        """Máy Sân khấu 3D đã duyệt nhìn DỌC đường chạy (sau lưng, về B) trong khi chữ nói chạy về phía máy → VÀNG, không chặn."""
        cam = [self.A[0] - 2 * (self.B[0] - self.A[0]) / 10, self.A[1] - 2 * (self.B[1] - self.A[1]) / 10, self.A[2] + 1.5]
        self.edit(1, stage_camera={"location": cam, "look_at": list(self.B), "lens": 28, "source": "stage_v2"})
        it = self.plan(dict(ON, FEATURE_STAGE_CAMERA="1"))[self.ids[1]]
        self.assertTrue(it["camera"].get("locked"))
        self.assertIsNone(it["needs"])
        self.assertNotIn("trùng nhau", it["travel_problem"] or "")
        if it["travel_problem"]:
            self.assertIn("máy Sân khấu 3D đã duyệt", it["travel_problem"])

    def test_travel_camera_without_plate_view_does_not_wait(self):
        row = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.ids[1],)).fetchone()
        d = json.loads(row["data"]); d.pop("plate_view", None)
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), self.ids[1]))
        self.p.conn.commit()
        it = self.plan(ON)[self.ids[1]]
        self.assertEqual(it["view"]["source"], "spot_default")
        self.assertIsNone(it["needs"])
        self.assertIn("travel", it["camera_why"])
        self.assertIn("travel_view", it["camera_why"])
        self.assertTrue(0 < self.t_of(it["camera"]["location"]) < 0.5)      # still on the run

    def test_for_shot_error_is_said_and_plan_keeps_every_shot(self):
        n = len(self.plan(ON))
        with mock.patch.object(travel_truth, "for_shot", side_effect=RuntimeError("hỏng")):
            got = self.plan(ON)
        self.assertEqual(len(got), n)
        self.assertIn("không kiểm được hướng chạy", got[self.ids[1]]["travel_problem"] or "")


class MannequinNotTheObjectPicture(P30Base):
    """(e) Kho #367 3.png (sort −1, 'triển khai có hình nộm so cỡ') was sent as 'the object Bom keo' — never the object's picture."""

    def setUp(self):
        super().setUp()
        self.mq = self._png("3.png")
        self.p.conn.execute("INSERT INTO asset_images (asset_id, path, label, sort, status, variant) VALUES (?,?,?,?,?,?)",
                            (self.fx["glue"]["id"], self.mq, "triển khai có hình nộm so cỡ", -1, "approved", SKIN))
        self.p.conn.commit()

    def test_lock_and_references_never_take_the_mannequin_picture(self):
        with mock.patch.dict(os.environ, {"FEATURE_PROJECT_PROP_LOCK": "1"}):
            for idx in (3, 4):
                lk = next(x for x in prop_lock.locks(self.p.conn, self.pid, self.shot(idx)) if x["category"] == "glue")
                self.assertIsNotNone(lk["image"])
                self.assertNotEqual(lk["image"]["path"], self.mq, f"shot {idx}")
                refs = assets.scene_references(self.p.conn, self.pid, dict(self.shot(idx)))
                self.assertNotIn(self.mq, [r["path"] for r in refs], f"shot {idx}")

    def test_only_the_mannequin_picture_left_is_said_yellow(self):
        """rà 14/10: lọc ảnh hình nộm làm hết ảnh dùng được → VÀNG nói rõ, không im lặng."""
        self.p.conn.execute("DELETE FROM asset_images WHERE asset_id=? AND path<>?", (self.fx["glue"]["id"], self.mq))
        self.p.conn.commit()
        with mock.patch.dict(os.environ, {"FEATURE_PROJECT_PROP_LOCK": "1"}):
            lk = next(x for x in prop_lock.locks(self.p.conn, self.pid, self.shot(3)) if x["category"] == "glue")
            self.assertIsNone(lk["image"])
            msgs = [i["msg"] for i in prop_lock.issues(self.p.conn, self.pid, self.shot(3))]
        self.assertTrue(any("bỏ ảnh hình nộm khỏi khóa vật — vật chỉ còn tả bằng chữ" in m for m in msgs), msgs)


if __name__ == "__main__":
    unittest.main()
