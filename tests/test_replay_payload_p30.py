"""Kiểm thật #30 (14/10, nhân bản #28, cảnh one-shot Tháp Đồng Hồ — docs/handoff/KIEM_THAT_TAP2_2026-10-14.md mục "Gốc lỗi" 1 và 3).
Dữ liệu trích từ CSDL thật (tests/fixtures/p30_payload.json, rút gọn trường), 0 USD, không gọi model.

1. Tường keo trắng: kịch bản CẢNH ghi "tường keo (skin thang máy)" mà không shot nào còn chữ dạng → gói gửi không có ảnh Kho #367.
   Sửa gốc: dạng món trong câu kịch bản cảnh được code mang xuống mọi shot dùng món đó (prop_lock.variant_source).
2. Shot 1 Kelly chạy XUỐNG: A chân cầu thang (z 3,93) → B bậc cao nhất (z 8,5). Sửa: câu hướng chạy do code viết từ độ cao 3D
   (core/travel_truth, cờ travel_truth).
"""
import json
import os
import shutil
import tempfile
import types
import unittest
from unittest import mock

from core import assets, prop_lock, runner
from core.db import connect
from core.pipeline import Pipeline

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "p30_payload.json")
ON = {"FEATURE_PROJECT_PROP_LOCK": "1", "FEATURE_TRAVEL_TRUTH": "1"}
SKIN = "skin Gloowall OB55 thang máy"


class P30Base(unittest.TestCase):
    def setUp(self):
        with open(FIX, encoding="utf-8") as f:
            self.fx = json.load(f)
        self.tmp = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.tmp, "projects")
        self.p = Pipeline(connect())
        c = self.p.conn
        self.pid = self.p.create_project("p30 replay")
        c.execute("UPDATE projects SET game='FF' WHERE id=?", (self.pid,))
        st = self.fx["story_scene"]
        c.execute("INSERT INTO story_scenes (project_id, idx, heading, text, data) VALUES (?,?,?,?,?)",
                  (self.pid, st["idx"], st["heading"], st["text"], "{}"))
        g = self.fx["glue"]
        c.execute("INSERT INTO assets (id, game, kind, name, aliases, description) VALUES (?, 'FF', ?,?,?,?)",
                  (g["id"], g["kind"], g["name"], g["aliases"], g["description"]))
        self.glue_paths = []
        for i, im in enumerate(self.fx["glue_images"]):
            path = self._png(f"glue_{i}.png")
            self.glue_paths.append(path)
            c.execute("INSERT INTO asset_images (asset_id, path, label, sort, status, variant) VALUES (?,?,?,?,?,?)",
                      (g["id"], path, im["label"], im["sort"], im["status"], im["variant"]))
        pl = self.fx["place"]
        c.execute("INSERT INTO assets (id, game, kind, name, aliases, description, profile) VALUES (?, 'FF', ?,?,?,?,?)",
                  (pl["id"], pl["kind"], pl["name"], pl["aliases"], pl["description"],
                   json.dumps({"model3d": self.fx["model3d"]}, ensure_ascii=False)))
        c.execute("INSERT INTO asset_images (asset_id, path, label, sort, status) VALUES (?,?,?,?,?)",
                  (pl["id"], self._png("tower.png"), "tower", 1, "approved"))
        for aid in (g["id"], pl["id"]):
            c.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?,?)", (self.pid, aid))
        self.ids = {}
        for s in self.fx["shots"]:
            self.ids[s["idx"]] = c.execute("INSERT INTO scenes (project_id, idx, title, data) VALUES (?,?,?,?)",
                                           (self.pid, s["idx"], f"shot {s['idx']}", json.dumps(s["data"], ensure_ascii=False))).lastrowid
        c.commit()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _png(self, name):
        path = os.path.join(self.tmp, name)
        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
        return path

    def shot(self, idx):
        return next(s["data"] for s in self.fx["shots"] if s["idx"] == idx)


class GlueSkinFromSceneTest(P30Base):
    def test_every_glue_shot_carries_the_scene_skin(self):
        """#30 shots 3–7 (jobs 938–942): no shot says 'skin' — the scene script does. Each gets #367's skin picture + skin words."""
        with mock.patch.dict(os.environ, ON):
            for idx in (3, 4, 5, 6, 7):
                data = self.shot(idx)
                self.assertNotIn("skin", prop_lock.shot_text(data).lower(), "dữ liệu thật: shot không ghi dạng")
                lk = next(x for x in prop_lock.locks(self.p.conn, self.pid, data) if x["category"] == "glue")
                self.assertEqual(lk["variant"], SKIN, f"shot {idx}")
                self.assertEqual(lk["variant_from"], "scene")
                self.assertIn(lk["image"]["path"], self.glue_paths)
                refs = assets.scene_references(self.p.conn, self.pid, dict(data))
                self.assertTrue(any(r["path"] in self.glue_paths for r in refs), f"shot {idx}: không có ảnh Kho #367 trong gói")
                part = prop_lock.prompt_part(self.p.conn, self.pid, data)
                self.assertIn("skin Gloowall", part)
                self.assertNotIn("TRẮNG", part)
                notes = prop_lock.variant_notes(self.p.conn, self.pid, data)
                self.assertTrue(notes and "kịch bản cảnh 1" in notes[0])

    def test_scene_words_like_cau_thang_do_not_pick_the_lift_skin(self):
        """'cầu thang' (stairs) shares 'thang' with 'thang máy' — only 'skin' next to the variant's words, in a sentence about the
        glue wall, chooses the skin."""
        self.p.conn.execute("UPDATE story_scenes SET text=? WHERE project_id=?",
                            ("Kelly chạy lên cầu thang máy bay. Kelly đặt bom keo, tường keo xuất hiện.", self.pid))
        with mock.patch.dict(os.environ, ON):
            lk = next(x for x in prop_lock.locks(self.p.conn, self.pid, self.shot(3)) if x["category"] == "glue")
        self.assertIsNone(lk["variant"])
        self.assertIsNone(lk["image"])                 # no plain picture in the Kho: the default form is said in words

    def test_flag_off_is_unchanged(self):
        with mock.patch.dict(os.environ, {"FEATURE_PROJECT_PROP_LOCK": "0"}):
            self.assertEqual(prop_lock.locks(self.p.conn, self.pid, self.shot(3)), [])
            self.assertEqual(prop_lock.variant_notes(self.p.conn, self.pid, self.shot(3)), [])


class TravelTruthTest(P30Base):
    def setUp(self):
        super().setUp()
        global travel_truth
        from core import travel_truth                  # import here: the glue tests above still run on code without the module

    def rec(self, idx):
        return self.fx["plates"][str(self.fx["shots"][idx - 1]["scene_id"])]

    def test_shot1_up_the_stairs_from_3d_heights(self):
        got = travel_truth.for_shot(self.p.conn, self.pid, self.ids[1], self.shot(1), self.rec(1))
        s = got["sentence"]
        self.assertIn("UP the stairs", s)
        self.assertIn("3.9 m", s)
        self.assertIn("8.5 m", s)
        self.assertIn("never going down", s)
        self.assertEqual(got["facts"]["relation"], "away")       # the render's camera looks along the run (uphill)
        self.assertTrue(any("VỀ PHÍA máy" in w and "298" in w for w in got["warn"]), got["warn"])

    def test_shot2_is_the_end_of_the_run(self):
        got = travel_truth.for_shot(self.p.conn, self.pid, self.ids[2], self.shot(2), self.rec(2))
        self.assertIn("UP the stairs", got["sentence"])
        self.assertTrue(got["facts"]["arriving"])

    def test_plaza_run_says_nothing(self):
        """Shot 5: five steps to the left on the top landing (same spot before and after) — no up/down sentence, no VÀNG."""
        got = travel_truth.for_shot(self.p.conn, self.pid, self.ids[5], self.shot(5), self.rec(5))
        self.assertEqual(got["sentence"], "")
        self.assertEqual(got["warn"], [])

    def test_no_3d_data_is_yellow_not_a_guess(self):
        data = dict(self.shot(1), location_asset=None, location="nơi khác")
        got = travel_truth.for_shot(self.p.conn, self.pid, self.ids[1], data, None)
        self.assertEqual(got["sentence"], "")
        self.assertTrue(got["warn"])

    def test_flat_move_says_nothing(self):
        spots = self.fx["model3d"]["spots"]
        flat = dict(self.fx["model3d"], spots=dict(spots, dinh_bac_thang_giua=dict(spots["dinh_bac_thang_giua"],
                                                                                   at=[-240.0, 136.82, 4.4])))
        self.p.conn.execute("UPDATE assets SET profile=? WHERE id=263", (json.dumps({"model3d": flat}),))
        got = travel_truth.for_shot(self.p.conn, self.pid, self.ids[1], self.shot(1), self.rec(1))
        self.assertEqual(got["sentence"], "")

    def test_runner_sentence_follows_flag(self):
        idx_dir = os.path.join(self.data_dir, str(self.pid), "plates")
        os.makedirs(idx_dir)
        plate = self._png("plate.png")
        with open(os.path.join(idx_dir, "index.json"), "w", encoding="utf-8") as f:
            json.dump({str(self.ids[1]): dict(self.rec(1), plate=plate)}, f)
        said = []
        fake = types.SimpleNamespace(p=self.p, data_dir=self.data_dir, _diag=lambda job, sev, code, msg: said.append((sev, code)))
        job = {"id": 1, "project_id": self.pid, "scene_id": self.ids[1]}
        with mock.patch.dict(os.environ, {"FEATURE_TRAVEL_TRUTH": "1"}):
            self.assertIn("UP the stairs", runner._travel_truth(fake, job))
        self.assertIn(("warn", "travel_truth"), said)
        with mock.patch.dict(os.environ, {"FEATURE_TRAVEL_TRUTH": "0"}):
            self.assertEqual(runner._travel_truth(fake, job), "")

    def test_sentence_survives_d6_rewrite(self):
        got = travel_truth.for_shot(self.p.conn, self.pid, self.ids[1], self.shot(1), self.rec(1))["sentence"]
        assembled = "Scene: Kelly runs. " + got
        self.assertIn(got, travel_truth.kept_after_rewrite(assembled, "Kelly runs down the steps."))


class ReplayGuardTest(unittest.TestCase):
    def test_writes_under_real_data_are_blocked(self):
        from tools.replay_payload import WriteGuard
        tmp = tempfile.mkdtemp()
        try:
            real = os.path.join(tmp, "data")
            os.makedirs(real)
            with WriteGuard(real):
                with self.assertRaises(PermissionError):
                    open(os.path.join(real, "x.txt"), "w").close()
                with self.assertRaises(PermissionError):
                    os.makedirs(os.path.join(real, "sub"))
                with open(os.path.join(tmp, "ok.txt"), "w") as f:    # outside: allowed
                    f.write("ok")
            self.assertFalse(os.path.exists(os.path.join(real, "x.txt")))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
