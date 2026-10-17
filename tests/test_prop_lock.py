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

    def test_storyboard_mapping_and_sent_paths_use_recovered_gun(self):
        from types import SimpleNamespace
        from core import runner, scene_storyboard, scene_establish, place_refs, skill_dossier
        shot = {"image_prompt": "Kelly holds SKORP"}
        sid = self.p.create_scene(self.pid, 1, "priority")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(shot), sid))
        self.p.conn.commit()
        anchor = {"id": sid, "idx": 1, "data": shot}
        group = {"anchor": anchor, "shots": [anchor], "story_scene": 1, "index": 1}
        widepath = os.path.join(self.tmp, "wide.png")
        with open(widepath, "wb") as stream:
            stream.write(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
        shared = [{"path": widepath, "role": "place_wide", "label": "wide map"}]
        obj = object.__new__(runner.ImageRunner)
        obj.p, obj.provider, obj.data_dir = self.p, SimpleNamespace(supports_storyboard=True), self.tmp
        obj._diag = mock.Mock()
        job = {"id": 222, "project_id": self.pid, "scene_id": sid}
        with mock.patch.dict(os.environ, FLAG_ON), mock.patch.object(scene_storyboard, "enabled", return_value=True), \
                mock.patch.object(scene_storyboard, "group_of", return_value=group), \
                mock.patch.object(scene_storyboard, "shared_references", return_value=shared), \
                mock.patch.object(scene_establish, "reference", return_value=None), \
                mock.patch.object(place_refs, "enabled", return_value=False), \
                mock.patch.object(skill_dossier, "enabled", return_value=False):
            result = obj._finish_args(job, "prompt", shared)
        expected = next(a for a in assets.project_assets(self.p.conn, self.pid) if a["id"] == self.skorp)["images"][0]["path"]
        self.assertEqual(result[1], [expected])
        self.assertIn("Image 1 (SKORP)", obj._storyboard[222]["image_mapping"])
        self.assertNotIn("wide map", obj._storyboard[222]["image_mapping"])
        self.assertEqual(obj._sent[222][0]["label"], "SKORP")
        self.assertNotIn(widepath, result[1])

    def test_pov_gun_warns_without_lock_sentence_or_named_ref(self):
        from core import prop_lock
        shot = {"angle": "pov", "image_prompt": "Kelly holds SKORP and throws a glue wall"}
        with mock.patch.dict(os.environ, FLAG_ON):
            self.assertNotIn("SKORP", prop_lock.prompt_part(self.p.conn, self.pid, shot))
            self.assertIn("Bom keo", prop_lock.prompt_part(self.p.conn, self.pid, shot))
            self.assertTrue(any(i["level"] == "warn" and "POV" in i["msg"] for i in prop_lock.issues(self.p.conn, self.pid, shot)))
        self.assertNotIn("SKORP", [r["label"] for r in self._refs(shot, FLAG_ON)])
        self.assertIn("SKORP", [r["label"] for r in self._refs(shot, FLAG_OFF)])

    def test_negated_ots_does_not_override_affirmative_pov(self):
        from core import prop_lock
        angles = ("not over-the-shoulder; POV", "Không qua vai; góc nhìn thứ nhất",
                  "not third-person; first-person view", "Not OTS, POV with a gun")
        with mock.patch.dict(os.environ, FLAG_ON):
            for angle in angles:
                shot = {"angle": angle, "image_prompt": "Kelly holds SKORP"}
                with self.subTest(angle=angle):
                    self.assertTrue(prop_lock.is_pov(shot))
                    self.assertIsNotNone(prop_lock.pov_gun_issue(self.p.conn, self.pid, shot))
                    prompt = self._prompt(shot, FLAG_ON)
                    self.assertNotIn("Prop lock:", prompt)
                    self.assertNotIn("Weapon scale:", prompt)
                    self.assertNotIn("SKORP", [r["label"] for r in self._refs(shot, FLAG_ON)])
                    self.assertIn("SKORP", [r["label"] for r in self._refs(shot, FLAG_OFF)])
            for angle in ("not POV; OTS", "No first-person view; third-person", "Không góc nhìn thứ nhất; qua vai"):
                with self.subTest(angle=angle):
                    self.assertFalse(prop_lock.is_pov({"angle": angle}))
            self.assertFalse(prop_lock.is_pov({"angle": "ots", "image_prompt": "POV with a gun"}))

    def test_pov_detection_respects_negation_dialogue_ots_and_boundaries(self):
        from core import prop_lock
        cases = [({"angle": "pov"}, True), ({"camera": {"angle": "first-person"}}, True),
                 ({"shot": "POV shot of Kelly"}, True), ({"image_prompt": "First-person view, hands visible"}, True),
                 ({"image_prompt": "No first-person view; camera at eye level"}, False),
                 ({"image_prompt": "Do not use POV"}, False), ({"image_prompt": "POVish camera"}, False),
                 ({"text": "LỜI DẪN: first-person view with a gun"}, False),
                 ({"angle": "ots", "image_prompt": "POV from over the shoulder"}, False),
                 # rà 12/10: someone else's POV / game genre / a screen feed is not this camera; a written angle wins over free text
                 ({"image_prompt": "Reverse shot from Maxim's POV: Kelly fires the SKORP at him"}, False),
                 ({"image_prompt": "Kelly aims her SKORP; the enemy POV shows her through the smoke"}, False),
                 ({"image_prompt": "a first-person shooter feel, Kelly holds SKORP"}, False),
                 ({"angle": "eye", "image_prompt": "Kelly in first-person shooter game Free Fire style"}, False),
                 ({"image_prompt": "Kelly looks at the screen showing a POV feed"}, False),
                 ({"angle": "eye level", "image_prompt": "POV shot"}, False),
                 ({"image_prompt": "POV shot, hands hold SKORP"}, True)]
        for shot, expected in cases:
            with self.subTest(shot=shot):
                self.assertEqual(prop_lock.is_pov(shot), expected)

    def test_locked_gun_replaces_only_wide_and_only_if_sendable(self):
        from core import prop_lock
        shot = {"image_prompt": "Kelly holds SKORP"}
        refs = [{"path": "face", "label": "Kelly", "role": "character"},
                {"path": "main", "label": "map", "role": "place_render"},
                {"path": "wide", "label": "wide", "role": "place_wide"},
                {"path": "previous", "label": "previous", "role": "previous_scene"}]
        with mock.patch.dict(os.environ, FLAG_ON):
            recovered = prop_lock.prioritize_gun_refs(self.p.conn, self.pid, shot, refs, lambda ref: True)
            self.assertEqual(len(recovered), len(refs))
            self.assertEqual([r["path"] for r in recovered if r["role"] != "object"], ["face", "main", "previous"])
            self.assertEqual(recovered[2]["label"], "SKORP")
            self.assertEqual(prop_lock.prioritize_gun_refs(self.p.conn, self.pid, shot, refs, lambda ref: False), refs)
            protected = [r for r in refs if r["role"] != "place_wide"]
            self.assertEqual(prop_lock.prioritize_gun_refs(self.p.conn, self.pid, shot, protected, lambda ref: True), protected)
            self.assertEqual(prop_lock.prioritize_gun_refs(self.p.conn, self.pid, shot, recovered, lambda ref: True), recovered)
        with mock.patch.dict(os.environ, FLAG_OFF):
            self.assertEqual(prop_lock.prioritize_gun_refs(self.p.conn, self.pid, shot, refs, lambda ref: True), refs)

    def test_runner_warns_from_final_package_and_dashboard_displays_it(self):
        from core import runner, diag
        from dashboard import common
        sid = self.p.create_scene(self.pid, 1, "refs")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": "Kelly holds SKORP"}), sid))
        self.p.conn.commit()
        obj = object.__new__(runner.ImageRunner)
        obj.p, obj.provider = self.p, object()
        obj._diag = lambda job, severity, code, message: diag.record(self.p.conn, "image", severity, message, code, self.pid, scene_id=sid, job_id=job["id"])
        job = {"id": 123, "project_id": self.pid, "scene_id": sid}
        with mock.patch.dict(os.environ, FLAG_ON), mock.patch.object(runner, "sendable_references", return_value=([], [])):
            result = obj._finish_args(job, "prompt", [])
        self.assertEqual(result, ("prompt",))
        with mock.patch.dict(os.environ, FLAG_ON), mock.patch.object(common, "st") as ui, mock.patch.object(common.ui, "html"):
            common.scene_expander(self.p, sid)
        self.assertTrue(any("SKORP" in str(call) for call in ui.warning.call_args_list))

    def test_final_refs_report_only_locked_picture_actually_missing(self):
        from core import prop_lock
        shot = {"image_prompt": "Kelly holds SKORP"}
        with mock.patch.dict(os.environ, FLAG_ON):
            self.assertTrue(prop_lock.missing_refs(self.p.conn, self.pid, shot, []))
            lock = prop_lock.reference_images(self.p.conn, self.pid, shot)[0]
            refs = [{"path": lock["image"]["path"], "label": "SKORP", "role": "object"}]
            self.assertEqual(prop_lock.missing_refs(self.p.conn, self.pid, shot, refs), [])
            self.assertTrue(prop_lock.missing_refs(self.p.conn, self.pid, shot, [dict(refs[0], path="different.png")]))
        with mock.patch.dict(os.environ, FLAG_OFF):
            self.assertEqual(prop_lock.missing_refs(self.p.conn, self.pid, shot, []), [])

    def test_skin_conflict_attributes_belong_to_prop(self):
        from core import prop_lock
        cases = {
            "A white car passes; Kelly hides behind skin Gloowall OB55.": False,
            "Kelly uses skin Gloowall OB55; a white lamp shines.": False,
            "Kelly uses skin Gloowall OB55, without white paint.": False,
            "A plain white glue wall with OB55 skin, no pattern.": True,
            "A plain white skin Gloowall OB55 wall, no pattern.": True,
            "A no white skin Gloowall OB55 wall.": False,
        }
        with mock.patch.dict(os.environ, FLAG_ON):
            for text, expected in cases.items():
                with self.subTest(text=text):
                    found = any("mâu thuẫn dạng" in i["msg"] for i in prop_lock.issues(self.p.conn, self.pid, {"image_prompt": text}))
                    self.assertEqual(found, expected)

    def test_skin_named_with_default_material_warns(self):
        from core import prop_lock
        with mock.patch.dict(os.environ, FLAG_ON):
            issues = prop_lock.issues(self.p.conn, self.pid, {"image_prompt": "A plain white skin Gloowall OB55 wall, no pattern."})
        self.assertTrue(any(i["level"] == "warn" and "mâu thuẫn dạng" in i["msg"] for i in issues))

    def test_sent_prompt_removes_only_default_prop_modifiers_keeps_source(self):
        shot = {"size": "WS", "image_prompt": "A translucent amber lamp glows. Kelly hides behind a translucent amber glue-grenade wall; a red car passes.",
                "blocking": "Kelly behind the translucent amber Bom keo"}
        original = dict(shot)
        sent = self._prompt(shot, FLAG_ON)
        self.assertIn("translucent amber lamp", sent)
        self.assertIn("red car", sent)
        self.assertNotIn("translucent amber glue", sent)
        self.assertNotIn("translucent amber Bom keo", sent)
        self.assertEqual(shot, original)
        self.assertEqual(self.p.conn.execute("SELECT description FROM assets WHERE id=?", (self.glue,)).fetchone()[0], GLUE_DESC)

    def test_cleanup_clause_boundaries_skin_and_off(self):
        from core import prop_lock
        for raw in ("Amber light falls; Kelly raises a glue wall.", "Kelly hides behind the glue wall, next to translucent amber glass.",
                    "A translucent amber skin Gloowall OB55 wall.", "A translucent amber glue wall."):
            shot = {"image_prompt": raw}
            with mock.patch.dict(os.environ, FLAG_OFF):
                clean, removed = prop_lock.clean_prompt(self.p.conn, self.pid, shot, raw)
            self.assertEqual((clean, removed), (raw, []))
        with mock.patch.dict(os.environ, FLAG_ON):
            for raw in ("Amber light falls; Kelly raises a glue wall.", "Kelly hides behind the glue wall, next to translucent amber glass.",
                        "A translucent amber skin Gloowall OB55 wall."):
                self.assertEqual(prop_lock.clean_prompt(self.p.conn, self.pid, {"image_prompt": raw}, raw), (raw, []))
            self.assertEqual(prop_lock.clean_prompt(self.p.conn, self.pid, {"image_prompt": "A glue wall is translucent amber."},
                                                   "A glue wall is translucent amber."), ("A glue wall.", ["is translucent amber"]))
            raw = "A translucent amber glue wall."
            self.assertEqual(prop_lock.clean_prompt(self.p.conn, self.pid, {"image_prompt": raw}, raw), ("A glue wall.", ["translucent amber"]))

    def test_cleanup_multiple_props_does_not_guess_generic(self):
        from core import prop_lock
        self._asset("prop", "Keo Hai", "glue wall two", GLUE_DESC, "two.png", None)
        self.p.conn.commit()
        raw = "A translucent amber glue wall stands near a red car."
        with mock.patch.dict(os.environ, FLAG_ON):
            self.assertEqual(prop_lock.clean_prompt(self.p.conn, self.pid, {"image_prompt": raw}, raw), (raw, []))
            raw = "A translucent amber Bom keo stands near a red Keo Hai."
            clean, removed = prop_lock.clean_prompt(self.p.conn, self.pid, {"image_prompt": raw}, raw)
            self.assertNotIn("translucent amber", clean)
            self.assertNotIn("red Keo Hai", clean)

    def test_weapon_scale_actual_builder_type_and_only_when_present(self):
        sent = self._prompt(self.RIFLE, FLAG_ON)
        self.assertIn("Weapon scale: SKORP", sent)
        self.assertIn("forearm-to-shoulder", sent)
        self.assertIn("Estimated", sent)
        self.assertNotIn("Weapon scale: SKORP", self._prompt(self.WALL, FLAG_ON))
        self.assertNotIn("Weapon scale:", self._prompt(self.RIFLE, FLAG_OFF))

    def test_weapon_scale_explicit_description_and_profile_win(self):
        c = self.p.conn
        c.execute("UPDATE assets SET description=? WHERE id=?", (SKORP_DESC + " Scale: exactly forearm-to-shoulder length.", self.skorp))
        c.commit()
        self.assertIn("exactly forearm-to-shoulder length", self._prompt(self.RIFLE, FLAG_ON))
        c.execute("UPDATE assets SET profile=? WHERE id=?", (json.dumps({"must_keep": "Tỉ lệ: length equal to Kelly forearm."}), self.skorp))
        c.commit()
        sent = self._prompt(self.RIFLE, FLAG_ON)
        self.assertIn("length equal to Kelly forearm", sent)
        self.assertNotIn("Estimated", sent)
        self.assertNotIn("forearm-to-shoulder", sent)

    def test_weapon_scale_unknown_conflicting_types_and_negation(self):
        from core import prop_lock
        c = self.p.conn
        for desc in ("A gun.", "An SMG or pistol."):
            c.execute("UPDATE assets SET aliases='', description=? WHERE id=?", (desc, self.skorp))
            c.commit()
            with mock.patch.dict(os.environ, FLAG_ON):
                warns = prop_lock.issues(c, self.pid, {"image_prompt": "Kelly holds SKORP."})
            self.assertTrue(any("thiếu tỉ lệ" in w["msg"] for w in warns), warns)
            self.assertNotIn("Weapon scale:", self._prompt({"image_prompt": "Kelly holds SKORP."}, FLAG_ON))
        c.execute("UPDATE assets SET description=? WHERE id=?", ("An SMG, not a pistol.", self.skorp))
        c.commit()
        self.assertIn("Estimated SMG", self._prompt({"image_prompt": "Kelly holds SKORP."}, FLAG_ON))

    def test_scale_measured_dimensions_and_off_prompt_byte_contract(self):
        from core import prop_lock, runner
        assets.set_size(self.p.conn, self.skorp, 0.45, 0.12)
        self.assertIn("Library measured dimensions: height 0.45 m, width 0.12 m", self._prompt(self.RIFLE, FLAG_ON))
        raw = "Kelly behind a translucent amber glue wall."
        with mock.patch.dict(os.environ, FLAG_OFF), mock.patch.object(assets, "scene_location", return_value=None), \
                mock.patch.object(runner, "indoor_spot", return_value=None):
            actual = runner.build_image_prompt(self.p.conn, self.pid, {"image_prompt": raw})
            with mock.patch.object(prop_lock, "clean_prompt", side_effect=lambda conn, pid, data, text: (text, [])):
                baseline = runner.build_image_prompt(self.p.conn, self.pid, {"image_prompt": raw})
        self.assertEqual(actual, baseline)
        with mock.patch.dict(os.environ, FLAG_ON), mock.patch.object(assets, "scene_location", return_value=None), \
                mock.patch.object(runner, "indoor_spot", return_value=None):
            _, realism_removed = runner.build_image_prompt(self.p.conn, self.pid, {"image_prompt": raw})
        self.assertEqual(realism_removed, [])  # return thứ 2 chỉ dành cho realism, giữ hợp đồng caller

    def test_dashboard_shows_removed_phrase_and_off_has_no_diff(self):
        from dashboard import common
        d = {"image_prompt": "Kelly behind a translucent amber glue wall; red car.", "size": "WS"}
        sid = self.p.conn.execute("INSERT INTO scenes (project_id, idx, data) VALUES (?,?,?)", (self.pid, 16, json.dumps(d))).lastrowid
        self.p.conn.commit()
        for env, expect in ((FLAG_ON, True), (FLAG_OFF, False)):
            with mock.patch.dict(os.environ, env), mock.patch.object(common.st, "expander"), \
                    mock.patch.object(common.st, "caption") as caption, mock.patch.object(common.ui, "html"):
                common.scene_expander(self.p, sid)
                matches = [call.args[0] for call in caption.call_args_list if "sẽ bỏ:" in call.args[0]]
                self.assertEqual(bool(matches), expect)
                if expect:
                    self.assertIn("sẽ bỏ: translucent amber", matches[0])
                    self.assertNotIn("red", matches[0])

    def test_review_semantic_correct_attributes(self):
        from core import prop_lock
        raw = "Kelly holds a black SKORP."
        with mock.patch.dict(os.environ, FLAG_ON):
            self.assertEqual(prop_lock.clean_prompt(self.p.conn, self.pid, {"image_prompt": raw}, raw), (raw, []))

    def test_review_partial_descriptor_prefix_and_suffix(self):
        from core import prop_lock
        self.p.conn.execute("UPDATE assets SET description=? WHERE id=?", (GLUE_DESC.replace("TRẮNG trơn", "TRẮNG ĐỤC trơn"), self.glue))
        with mock.patch.dict(os.environ, FLAG_ON):
            for raw, expected in (("A translucent white glue wall.", "A white glue wall."),
                                  ("A glue wall is translucent white.", "A glue wall is white."),
                                  ("A glue wall is white translucent.", "A glue wall is white."),
                                  ("An opaque white glue wall.", "An opaque white glue wall.")):
                self.assertEqual(prop_lock.clean_prompt(self.p.conn, self.pid, {"image_prompt": raw}, raw)[0], expected)

    def test_review_other_noun_heads_keep_colour(self):
        from core import prop_lock
        with mock.patch.dict(os.environ, FLAG_ON):
            for noun in ("gun-shaped toy", "gun case", "gun rack", "glue bottle"):
                raw = f"A red {noun} stands beside SKORP and Bom keo."
                self.assertEqual(prop_lock.clean_prompt(self.p.conn, self.pid, {"image_prompt": raw}, raw), (raw, []))

    def test_review_decimal_scale_preserved(self):
        self.p.conn.execute("UPDATE assets SET description=? WHERE id=?", ("An SMG. Scale: 0.45 m long, 0.12 m wide.", self.skorp))
        sent = self._prompt({"image_prompt": "Kelly holds SKORP."}, FLAG_ON)
        self.assertIn("Weapon scale: SKORP — 0.45 m long, 0.12 m wide.", sent)

    def test_review_selected_form_scale(self):
        self.p.conn.execute("UPDATE assets SET description=? WHERE id=?", ("(a) DEFAULT — SMG with black stock; (b) skin Tiny — Scale: pistol-sized.", self.skorp))
        self.p.conn.execute("UPDATE asset_images SET variant='skin Tiny' WHERE asset_id=?", (self.skorp,))
        sent = self._prompt({"image_prompt": "Kelly holds SKORP."}, FLAG_ON)
        self.assertIn("Estimated SMG", sent)
        self.assertNotIn("— pistol-sized", sent)
        skin = self._prompt({"image_prompt": "Kelly holds SKORP skin Tiny."}, FLAG_ON)
        self.assertIn("Weapon scale: SKORP — pistol-sized", skin)

    def test_review_scale_does_not_override_pose(self):
        for action in ("with one hand", "lowered", "slung over shoulder"):
            sent = self._prompt({"image_prompt": f"Kelly carries SKORP {action}."}, FLAG_ON)
            self.assertIn(action, sent)
            self.assertNotIn("hold two-handed", sent)
            self.assertNotIn("stock at the shoulder", sent)

    RIFLE = {"size": "MS", "image_prompt": "Kelly aims her assault rifle at the doorway, tense.", "blocking": "Kelly frame-left"}
    WALL = {"size": "WS", "image_prompt": "Kelly crouches behind a glue wall while bullets hit it."}
    SKIN = {"size": "WS", "image_prompt": "Kelly crouches behind a Gloowall OB55 wall."}

    def test_generic_gun_gets_the_project_weapon_and_its_picture(self):
        text = self._prompt(self.RIFLE, FLAG_ON)
        self.assertIn("SKORP", text)
        self.assertIn("SKORP from the project library", text)
        self.assertNotIn("Súng tiểu liên", text)       # G4 17/10: mô tả Kho tiếng Việt không gửi model ảnh (ảnh Kho + tên nói thay)
        self.assertNotIn("[Halloween", text)
        labels = [r["label"] for r in self._refs(self.RIFLE, FLAG_ON)]
        self.assertIn("SKORP", labels)
        self.assertNotIn("Bom keo", labels)

    def test_generic_glue_wall_gets_the_default_white_form_and_no_skin_picture(self):
        text = self._prompt(self.WALL, FLAG_ON)
        self.assertIn("Bom keo", text)
        self.assertIn("its default form (white)", text)                  # G4: dạng mặc định nói bằng tiếng Anh
        self.assertNotIn("skin Gloowall OB55 form", text)
        self.assertNotIn("Bom keo", [r["label"] for r in self._refs(self.WALL, FLAG_ON)])   # ảnh variant OB55 không gửi

    def test_named_skin_gets_the_skin_form_and_its_picture(self):
        text = self._prompt(self.SKIN, FLAG_ON)
        self.assertIn("its skin Gloowall OB55 form (metal, grey)", text)   # G4: tên dạng + màu/chất liệu tiếng Anh
        self.assertNotIn("default form", text)
        refs = self._refs(self.SKIN, FLAG_ON)
        self.assertIn("Bom keo", [r["label"] for r in refs])

    def test_variant_picture_never_sent_without_its_variant_named_even_by_name(self):
        shot = {"size": "WS", "image_prompt": "Kelly throws a Bom keo and crouches behind it."}
        self.assertNotIn("Bom keo", [r["label"] for r in self._refs(shot, FLAG_ON)])
        self.assertIn("its default form (white)", self._prompt(shot, FLAG_ON))

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
        self.assertIn("its default form (white)", text)
        self.assertIn("overrides any other colour", text)
        with mock.patch.dict(os.environ, FLAG_ON):
            warns = prop_lock.issues(self.p.conn, self.pid, dict(shot))
            plain = prop_lock.issues(self.p.conn, self.pid, dict(self.WALL))
        self.assertTrue(any(w["level"] == "warn" and "amber" in w["msg"] for w in warns), warns)
        # G4 17/10: the only note of a plain wall is the one saying its Vietnamese Kho form is not sent word for word
        self.assertEqual([w for w in plain if "mô tả dạng viết tiếng Việt" not in w["msg"]], [])
        self.assertEqual(len(plain), 1)

    def test_description_full_stop_not_glued_to_semicolon(self):
        # G4 17/10: a Vietnamese description is no longer sent — the joining is checked on an English one
        self.p.conn.execute("UPDATE assets SET description=? WHERE id=?",
                            ("[Kho thử] Black SKORP SMG: folding stock, small red scope, short barrel.", self.skorp))
        text = self._prompt(self.RIFLE, FLAG_ON)
        self.assertNotIn(".;", text)
        self.assertIn("short barrel;", text)


if __name__ == "__main__":
    unittest.main()
