"""Khóa đạo cụ dự án (cờ project_prop_lock, lỗi thật #27 12/10): Kho gắn dự án có súng SKORP + Bom keo, nhưng Đạo diễn viết
"assault rifle" / "glue wall" chung chung → ảnh ra AK, tường keo mỗi shot một kiểu, ảnh Kho không được gửi. Dữ liệu giả, không gọi API."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import assets, prompt_formula as pf
from core.db import connect
from core.pipeline import Pipeline

FLAG_ON = {"FEATURE_PROJECT_PROP_LOCK": "1"}
FLAG_OFF = {"FEATURE_PROJECT_PROP_LOCK": "0"}

SKORP_DESC = ("[Halloween OB55 — Kho thử] Súng tiểu liên SKORP màu đen: báng gập, ống ngắm đỏ nhỏ trên ray, băng đạn cong mảnh, "
              "ống nòng ngắn.")
GLUE_DESC = ("Tường keo FF (bom keo ném ra dựng thành bức tường chắn đạn). 2 DẠNG: (a) MẶC ĐỊNH — tường keo màu TRẮNG trơn, "
             "không họa tiết, không hình; (b) skin Gloowall OB55 (ID 1) — tường dạng cửa thang máy kim loại xám có khung, theo ảnh "
             "Kho. Shot không nói dạng nào → dạng mặc định. [ff.garena.com] Vũ khí (Projectiles): chỉ số 0.")


class PropLockTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("prop lock")
        c = self.p.conn
        c.execute("UPDATE projects SET game='FF' WHERE id=?", (self.pid,))
        self.skorp = self._asset("weapon", "SKORP", "súng tiểu liên skorp, Scorpion", SKORP_DESC, "skorp.png", None)
        self.glue = self._asset("weapon", "Bom keo", "Gloowall", GLUE_DESC, "gloowall.png", "skin Gloowall OB55")
        c.commit()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _asset(self, kind, name, aliases, desc, file, variant):
        c = self.p.conn
        aid = c.execute("INSERT INTO assets (game, kind, name, aliases, description) VALUES ('FF',?,?,?,?)",
                        (kind, name, aliases, desc)).lastrowid
        path = os.path.join(self.tmp, file)
        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
        c.execute("INSERT INTO asset_images (asset_id, path, label, sort, status, variant) VALUES (?,?,?,?,?,?)",
                  (aid, path, file, 1, "approved", variant))
        c.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?,?)", (self.pid, aid))
        return aid

    def _prompt(self, shot, env):
        from core import runner
        with mock.patch.dict(os.environ, env), mock.patch.object(assets, "scene_location", return_value=None), \
                mock.patch.object(runner, "indoor_spot", return_value=None):
            return runner.build_image_prompt(self.p.conn, self.pid, dict(shot))[0]

    def _refs(self, shot, env):
        with mock.patch.dict(os.environ, env), mock.patch.object(assets, "scene_location", return_value=None):
            return assets.scene_references(self.p.conn, self.pid, dict(shot))

    RIFLE = {"size": "MS", "image_prompt": "Kelly aims her assault rifle at the doorway, tense.", "blocking": "Kelly frame-left"}
    WALL = {"size": "WS", "image_prompt": "Kelly crouches behind a glue wall while bullets hit it."}
    SKIN = {"size": "WS", "image_prompt": "Kelly crouches behind a Gloowall OB55 wall."}

    def test_generic_gun_gets_the_project_weapon_and_its_picture(self):
        text = self._prompt(self.RIFLE, FLAG_ON)
        self.assertIn("SKORP", text)
        self.assertIn("Súng tiểu liên SKORP màu đen", text)       # mô tả đọc từ assets.description, bỏ nhãn nguồn [..]
        self.assertNotIn("[Halloween", text)
        labels = [r["label"] for r in self._refs(self.RIFLE, FLAG_ON)]
        self.assertIn("SKORP", labels)
        self.assertNotIn("Bom keo", labels)

    def test_generic_glue_wall_gets_the_default_white_form_and_no_skin_picture(self):
        text = self._prompt(self.WALL, FLAG_ON)
        self.assertIn("Bom keo", text)
        self.assertIn("TRẮNG trơn", text)
        self.assertNotIn("cửa thang máy", text)
        self.assertNotIn("Bom keo", [r["label"] for r in self._refs(self.WALL, FLAG_ON)])   # ảnh variant OB55 không gửi

    def test_named_skin_gets_the_skin_form_and_its_picture(self):
        text = self._prompt(self.SKIN, FLAG_ON)
        self.assertIn("cửa thang máy", text)
        self.assertNotIn("TRẮNG trơn", text)
        refs = self._refs(self.SKIN, FLAG_ON)
        self.assertIn("Bom keo", [r["label"] for r in refs])

    def test_variant_picture_never_sent_without_its_variant_named_even_by_name(self):
        shot = {"size": "WS", "image_prompt": "Kelly throws a Bom keo and crouches behind it."}
        self.assertNotIn("Bom keo", [r["label"] for r in self._refs(shot, FLAG_ON)])
        self.assertIn("TRẮNG trơn", self._prompt(shot, FLAG_ON))

    def test_two_guns_attached_warns_and_does_not_guess(self):
        self._asset("weapon", "M1887", "shotgun M1887", "Súng shotgun M1887 nòng đôi.", "m1887.png", None)
        self.p.conn.commit()
        text = self._prompt(self.RIFLE, FLAG_ON)
        self.assertNotIn("SKORP", text)
        self.assertNotIn("M1887", text)
        with mock.patch.dict(os.environ, FLAG_ON):
            from core import prop_lock
            issues = prop_lock.issues(self.p.conn, self.pid, dict(self.RIFLE))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["level"], "warn")
        self.assertIn("SKORP", issues[0]["msg"])
        self.assertIn("M1887", issues[0]["msg"])

    def test_two_guns_warning_reaches_formula_check(self):
        self._asset("weapon", "M1887", "shotgun M1887", "Súng shotgun M1887 nòng đôi.", "m1887.png", None)
        sid = self.p.conn.execute("INSERT INTO scenes (project_id, idx, data) VALUES (?,?,?)",
                                  (self.pid, 1, json.dumps(self.RIFLE))).lastrowid
        self.p.conn.commit()
        with mock.patch.dict(os.environ, dict(FLAG_ON, FEATURE_PROMPT_FORMULA="1")):
            pf.after_director(self.p.conn, self.pid)
        fc = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"])["formula_check"]
        self.assertTrue(any(i["part"] == "dao_cu" and i["level"] == "warn" for i in fc["image"]), fc["image"])
        self.assertFalse(fc["red"])

    def test_flag_off_changes_nothing_byte_for_byte(self):
        from core import prop_lock
        for shot in (self.RIFLE, self.WALL, self.SKIN):
            off = self._prompt(shot, FLAG_OFF)
            with mock.patch.object(prop_lock, "enabled", return_value=False):
                untouched = self._prompt(shot, FLAG_ON)
            self.assertEqual(off, untouched)
            self.assertNotIn("Prop lock", off)
        self.assertNotIn("SKORP", [r["label"] for r in self._refs(self.RIFLE, FLAG_OFF)])
        # cờ tắt: ảnh variant vẫn đi như cũ khi chữ có tên món
        self.assertIn("Bom keo", [r["label"] for r in self._refs({"image_prompt": "behind the Bom keo"}, FLAG_OFF)])

    def test_word_boundaries_and_accents(self):
        from core import prop_lock
        with mock.patch.dict(os.environ, FLAG_ON):
            self.assertEqual(prop_lock.issues(self.p.conn, self.pid, {"image_prompt": "Kelly kéo cửa, keoxyz, gunsmoke drifts"}), [])
            self.assertEqual(prop_lock.locks(self.p.conn, self.pid, {"image_prompt": "Kelly kéo cửa, keoxyz, gunsmoke drifts"}), [])
            names = [l["asset"]["name"] for l in prop_lock.locks(self.p.conn, self.pid, {"image_prompt": "nấp sau tường keo"})]
        self.assertEqual(names, ["Bom keo"])

    # --- rà 12/10: các lỗi phiên rà bắt ---
    def _person(self, name):
        c = self.p.conn
        aid = c.execute("INSERT INTO assets (game, kind, name, aliases, description) VALUES ('FF','character',?, '', '')",
                        (name,)).lastrowid
        for i, role in enumerate(("front_standard", "design_sheet", "related")):
            path = os.path.join(self.tmp, f"{name}_{role}.png")
            with open(path, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
            c.execute("INSERT INTO asset_images (asset_id, path, label, sort, status, role) VALUES (?,?,?,?,?,?)",
                      (aid, path, role, i, "approved", role))
        c.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?,?)", (self.pid, aid))

    def _glue(self):
        return next(a for a in assets.project_assets(self.p.conn, self.pid) if a["id"] == self.glue)

    def test_locked_prop_keeps_its_slot_in_a_crowded_shot(self):
        for n in ("Kelly", "Kenta", "Maxim", "Alok"):
            self._person(n)
        self.p.conn.commit()
        shot = dict(self.RIFLE, characters=["Kelly", "Kenta", "Maxim", "Alok"])
        with mock.patch.dict(os.environ, FLAG_ON), mock.patch.object(assets, "scene_location", return_value=None):
            refs = assets.scene_references(self.p.conn, self.pid, dict(shot), limit=12, reserve=1, sheets=True)
        labels = [r["label"] for r in refs]
        self.assertEqual(sum(1 for l in labels if l in ("Kelly", "Kenta", "Maxim", "Alok")), 10, labels)   # people filled the rest
        self.assertIn("SKORP", labels)
        self.assertLessEqual(len(refs), 11)

    def test_prompt_never_points_at_a_reference_picture_that_was_not_sent(self):
        from core import prop_lock
        text = self._prompt(self.RIFLE, FLAG_ON)
        self.assertIn("reference picture", text)
        with mock.patch.dict(os.environ, FLAG_ON), mock.patch.object(assets, "scene_location", return_value=None):
            refs = assets.scene_references(self.p.conn, self.pid, dict(self.RIFLE), limit=0)   # no slot at all
        self.assertNotIn("SKORP", [r["label"] for r in refs])
        fixed = prop_lock.match_refs(text, refs)
        self.assertNotIn("reference picture", fixed)
        self.assertIn("SKORP", fixed)
        sent = [{"label": "SKORP", "role": "object", "path": "x.png"}]
        self.assertEqual(prop_lock.match_refs(text, sent), text)

    def test_variant_needs_its_whole_distinct_phrase(self):
        from core import prop_lock
        glue = self._glue()
        self.assertIsNone(prop_lock.chosen_variant(glue, "Kelly throws a Gloowall"))
        self.assertIsNone(prop_lock.chosen_variant(glue, "glue wall, Halloween OB55 event plaza"))
        self.assertEqual(prop_lock.chosen_variant(glue, "Gloowall OB55 skin wall"), "skin Gloowall OB55")
        self.assertEqual(prop_lock.chosen_variant(glue, "Kelly crouches behind a Gloowall OB55 wall."), "skin Gloowall OB55")
        self.assertEqual(prop_lock.chosen_variant(glue, "behind her skin Gloowall"), "skin Gloowall OB55")

    def test_lock_overrides_other_colour_words_and_warns(self):
        from core import prop_lock
        shot = {"size": "WS", "image_prompt": "Kelly crouches behind a translucent amber glue-grenade wall."}
        text = self._prompt(shot, FLAG_ON)
        self.assertIn("TRẮNG trơn", text)
        self.assertIn("overrides any other colour", text)
        with mock.patch.dict(os.environ, FLAG_ON):
            warns = prop_lock.issues(self.p.conn, self.pid, dict(shot))
            plain = prop_lock.issues(self.p.conn, self.pid, dict(self.WALL))
        self.assertTrue(any(w["level"] == "warn" and "amber" in w["msg"] for w in warns), warns)
        self.assertEqual(plain, [])

    def test_description_full_stop_not_glued_to_semicolon(self):
        text = self._prompt(self.RIFLE, FLAG_ON)
        self.assertNotIn(".;", text)
        self.assertIn("ống nòng ngắn;", text)


if __name__ == "__main__":
    unittest.main()
