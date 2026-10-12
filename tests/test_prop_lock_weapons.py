"""Đ16 việc 3 (người dùng 12/10 13:19, #27): KHÓA SÚNG THEO NHÂN VẬT — "khóa sẵn nhiều súng, tránh tự ý dùng và gán sai". Dữ liệu
giả dựng lại bảng gán #27 người dùng đã duyệt (KELLY → SKORP, LÍNH ĐỊCH ÁO CHOÀNG → M7, SỨ GIẢ BÓNG ĐÊM → HAWK, XÚC TU ĐỎ → RPK,
YÊU NỮ TÀ LINH DẠNG 1 → M7). Không gọi API."""
import os
import unittest
from unittest import mock

from core import assets, prop_lock, prompt_formula as pf
from tests import test_prop_lock as base

FLAG_ON, FLAG_OFF = base.FLAG_ON, base.FLAG_OFF

SCALE = "In-game scale: about {} head-heights long, held two-handed with the stock to the shoulder."


class WeaponLockTest(unittest.TestCase):
    """Uses base.PropLockTest's fixture (project + SKORP + Bom keo) without re-running its tests."""
    tearDown, _asset, _prompt, _refs = base.PropLockTest.tearDown, base.PropLockTest._asset, base.PropLockTest._prompt, base.PropLockTest._refs

    def setUp(self):
        base.PropLockTest.setUp(self)
        self.m7 = self._asset("weapon", "M7", "súng trường M7", "Súng trường M7 màu xám đen. " + SCALE.format("1.6"), "m7.png", None)
        self.hawk = self._asset("weapon", "HAWK", "súng hawk", "Súng HAWK báng gỗ. " + SCALE.format("1.4"), "hawk.png", None)
        self.rpk = self._asset("weapon", "RPK", "súng máy RPK", "Súng máy RPK hộp đạn tròn. " + SCALE.format("2.0"), "rpk.png", None)
        c = self.p.conn
        c.execute("UPDATE assets SET description=? WHERE id=?",
                  ("Súng tiểu liên SKORP màu đen, báng gập. " + SCALE.format("1.1"), self.skorp))
        for n in ("KELLY", "LÍNH ĐỊCH ÁO CHOÀNG", "SỨ GIẢ BÓNG ĐÊM", "XÚC TU ĐỎ", "YÊU NỮ TÀ LINH DẠNG 1", "MAXIM"):
            c.execute("INSERT INTO characters (project_id, name, description) VALUES (?,?,?)", (self.pid, n, n))
        c.commit()
        for n, a in (("KELLY", self.skorp), ("LÍNH ĐỊCH ÁO CHOÀNG", self.m7), ("SỨ GIẢ BÓNG ĐÊM", self.hawk), ("XÚC TU ĐỎ", self.rpk),
                     ("YÊU NỮ TÀ LINH DẠNG 1", self.m7)):
            prop_lock.set_weapon(c, self.pid, n, a)

    def _issues(self, shot):
        with mock.patch.dict(os.environ, FLAG_ON):
            return prop_lock.issues(self.p.conn, self.pid, shot)

    def test_each_character_gets_their_own_locked_gun_by_name_with_whole_scale(self):
        shot = {"characters": ["KELLY", "LÍNH ĐỊCH ÁO CHOÀNG", "SỨ GIẢ BÓNG ĐÊM"],
                "image_prompt": "Kelly and two enemies fire assault rifles at each other across the plaza."}
        prompt = self._prompt(shot, FLAG_ON)
        self.assertIn("the gun of KELLY in this shot is SKORP", prompt)
        self.assertIn("the gun of LÍNH ĐỊCH ÁO CHOÀNG in this shot is M7", prompt)
        self.assertIn("the gun of SỨ GIẢ BÓNG ĐÊM in this shot is HAWK", prompt)
        self.assertNotIn("RPK", prompt)                                    # not in the shot
        self.assertIn("Weapon scale: SKORP — about 1.1 head-heights long, held two-handed with the stock to the shoulder.", prompt)
        self.assertNotIn("In-game", prompt)                                # the scale said once, whole
        self.assertFalse([i for i in self._issues(shot) if "chung chung" in i["msg"]])   # no more "several guns → guess" YELLOW

    def test_two_characters_sharing_a_gun_get_one_sentence_and_one_picture(self):
        shot = {"characters": ["LÍNH ĐỊCH ÁO CHOÀNG", "YÊU NỮ TÀ LINH DẠNG 1"], "image_prompt": "Both aim their guns at the well."}
        prompt = self._prompt(shot, FLAG_ON)
        self.assertIn("the gun of LÍNH ĐỊCH ÁO CHOÀNG and YÊU NỮ TÀ LINH DẠNG 1 in this shot is M7", prompt)
        self.assertEqual(sum(r["label"] == "M7" for r in self._refs(shot, FLAG_ON)), 1)

    def test_a_named_gun_locked_to_nobody_in_the_shot_is_red(self):
        shot = {"characters": ["KELLY"], "image_prompt": "Kelly fires her RPK at the door."}
        red = [i for i in self._issues(shot) if i["level"] == "red"]
        self.assertTrue(red and "RPK" in red[0]["msg"] and "KELLY → SKORP" in red[0]["msg"])
        ok = {"characters": ["KELLY", "XÚC TU ĐỎ"], "image_prompt": "Kelly ducks while the tentacle fires the RPK."}
        self.assertFalse([i for i in self._issues(ok) if i["level"] == "red"])

    def test_a_character_without_a_locked_gun_is_yellow_never_guessed(self):
        shot = {"characters": ["KELLY", "MAXIM"], "image_prompt": "Kelly and Maxim hold guns."}
        warn = [i for i in self._issues(shot) if i["level"] == "warn" and "MAXIM" in i["msg"]]
        self.assertTrue(warn)
        self.assertNotIn("gun of MAXIM", self._prompt(shot, FLAG_ON))

    def test_slung_on_the_back_is_said_at_true_size(self):
        shot = {"characters": ["KELLY"], "image_prompt": "Kelly walks with her gun slung on her back."}
        self.assertIn("slung on the back it is this same gun at its true size", self._prompt(shot, FLAG_ON))

    def test_no_gun_word_no_lock_and_flag_off_unchanged(self):
        calm = {"characters": ["KELLY"], "image_prompt": "Kelly waves at the camera."}
        self.assertNotIn("Prop lock", self._prompt(calm, FLAG_ON))
        shot = {"characters": ["KELLY"], "image_prompt": "Kelly fires her assault rifle."}
        with mock.patch.dict(os.environ, FLAG_OFF):
            self.assertEqual(prop_lock.issues(self.p.conn, self.pid, shot), [])
        self.assertNotIn("Prop lock", self._prompt(shot, FLAG_OFF))

    def test_no_table_keeps_the_old_one_gun_rules(self):
        for n in ("KELLY", "LÍNH ĐỊCH ÁO CHOÀNG", "SỨ GIẢ BÓNG ĐÊM", "XÚC TU ĐỎ", "YÊU NỮ TÀ LINH DẠNG 1"):
            prop_lock.set_weapon(self.p.conn, self.pid, n, None)
        shot = {"characters": ["KELLY"], "image_prompt": "Kelly fires her assault rifle."}
        self.assertTrue([i for i in self._issues(shot) if "chung chung" in i["msg"]])     # several guns, no table → YELLOW as before

    def test_red_gun_mismatch_blocks_the_paid_send(self):
        sid = self.p.create_scene(self.pid, 1, "s")
        import json
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                            (json.dumps({"characters": ["KELLY"], "image_prompt": "Kelly fires her RPK at the door."}), sid))
        self.p.conn.commit()
        with mock.patch.dict(os.environ, dict(FLAG_ON, FEATURE_PROMPT_FORMULA="0")):
            red = pf.red_issues(self.p.conn, sid, "image")
        self.assertTrue(red and "RPK" in red[0])
        with mock.patch.dict(os.environ, dict(FLAG_OFF, FEATURE_PROMPT_FORMULA="0")):
            self.assertEqual(pf.red_issues(self.p.conn, sid, "image"), [])

    def test_a_gun_name_not_used_as_a_gun_is_only_yellow(self):
        """Rà Đ16v3 CAO-1: 'a hawk circles', a gun lying around, a line of dialogue — never a paid-send stop."""
        for text in ("A hawk circles overhead while Kelly fires her gun.", "An RPK lies on the ground. Kelly looks at it.",
                     'Kelly shouts: "Where is my M7?"'):
            shot = {"characters": ["KELLY"], "image_prompt": text}
            self.assertFalse([i for i in self._issues(shot) if i["level"] == "red"], text)

    def test_a_character_named_in_the_text_counts_as_present(self):
        """Rà Đ16v3 CAO-2: 'Xúc Tu Đỏ fires the RPK' with characters=['KELLY'] — the tentacle is in the shot; its RPK is right."""
        shot = {"characters": ["KELLY"], "image_prompt": "Kelly ducks as Xúc Tu Đỏ fires the RPK."}
        self.assertFalse([i for i in self._issues(shot) if i["level"] == "red"])
        self.assertIn("the gun of XÚC TU ĐỎ in this shot is RPK", self._prompt(shot, FLAG_ON))

    def test_clip_of_an_approved_picture_is_not_held_by_the_picture_words(self):
        import json
        sid = self.p.create_scene(self.pid, 2, "s")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                            (json.dumps({"characters": ["KELLY"], "image_prompt": "Kelly fires her RPK at the door."}), sid))
        self.p.conn.commit()
        with mock.patch.dict(os.environ, dict(FLAG_ON, FEATURE_PROMPT_FORMULA="0")):
            self.assertEqual(pf.red_issues(self.p.conn, sid, "motion"), [])

    def test_four_people_four_guns_keep_every_face(self):
        names = ["KELLY", "LÍNH ĐỊCH ÁO CHOÀNG", "SỨ GIẢ BÓNG ĐÊM", "XÚC TU ĐỎ"]
        people = [(n, [(f"/{i}.png", "identity")]) for i, n in enumerate(names)]
        with mock.patch.dict(os.environ, FLAG_ON):
            room_people = max(8 - 1 - 1 - 4, 0)
        self.assertLess(room_people, len(people))      # the old rule: 2 slots for 4 faces
        # the new rule keeps one per person (assets.scene_references): checked through the real function below
        shot = {"characters": names, "image_prompt": "They all fire their guns."}
        with mock.patch.dict(os.environ, FLAG_ON), mock.patch.object(assets, "scene_location", return_value=None):
            for n in names:
                self.p.conn.execute("INSERT INTO assets (game, kind, name, description) VALUES ('FF','character',?, 'x')", (n,))
                aid = self.p.conn.execute("SELECT id FROM assets WHERE name=? AND kind='character'", (n,)).fetchone()[0]
                path = os.path.join(self.tmp, f"face_{aid}.png")
                open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
                self.p.conn.execute("INSERT INTO asset_images (asset_id, path, label, sort, status) VALUES (?,?,?,?,?)",
                                    (aid, path, "f", 1, "approved"))
                self.p.conn.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?,?)", (self.pid, aid))
            self.p.conn.commit()
            refs = assets.scene_references(self.p.conn, self.pid, shot, limit=6)
        labels = [r["label"] for r in refs]
        self.assertTrue(all(any(assets.fold(n) == assets.fold(l) for l in labels) for n in names), labels)


    def test_a_named_prop_keeps_its_slot_over_second_face_pictures(self):
        # 12/10 (#27 shot 2): 4 people × 2 pictures filled the slots and the named torii portal (Kho prop) was dropped silently
        names = ["KELLY", "MAXIM", "SỨ GIẢ BÓNG ĐÊM", "XÚC TU ĐỎ"]
        c = self.p.conn
        for n in names:
            c.execute("INSERT INTO assets (game, kind, name, description) VALUES ('FF','character',?, 'x')", (n,))
            aid = c.execute("SELECT id FROM assets WHERE name=? AND kind='character'", (n,)).fetchone()[0]
            for k in (1, 2):
                path = os.path.join(self.tmp, f"face_{aid}_{k}.png")
                open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
                c.execute("INSERT INTO asset_images (asset_id, path, label, sort, status) VALUES (?,?,?,?,?)", (aid, path, "f", k, "approved"))
            c.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?,?)", (self.pid, aid))
        c.commit()
        gate = self._asset("prop", "CỔNG PORTAL TORII", "torii portal gate", "Cổng torii trong mờ.", "gate.png", None)
        shot = {"characters": names, "image_prompt": "Two torii portal gate frames stand on the grass, the team lies in front."}
        with mock.patch.dict(os.environ, FLAG_ON), mock.patch.object(assets, "scene_location", return_value=None):
            refs = assets.scene_references(c, self.pid, shot, limit=8)
        labels = [r["label"] for r in refs]
        self.assertIn("CỔNG PORTAL TORII", labels)
        self.assertTrue(all(any(assets.fold(n) == assets.fold(l) for l in labels) for n in names), labels)   # still one face each
        self.assertTrue(all("_paths" not in r for r in refs))
        self.assertIsNotNone(gate)


def test_weapon_select_saves_the_choice(tmp_path, monkeypatch):
    """Bước 1: one select per character (flag on, project has guns) — picking a gun locks it."""
    from streamlit.testing.v1 import AppTest
    from core.db import connect
    from core.pipeline import Pipeline
    db = str(tmp_path / "m.sqlite")
    p = Pipeline(connect(db))
    pid = p.create_project("t")
    aid = p.conn.execute("INSERT INTO assets (game, kind, name, aliases, description) VALUES ('FF','weapon','SKORP','súng tiểu liên','SMG')").lastrowid
    p.conn.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?,?)", (pid, aid))
    p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?,?,?)", (pid, "KELLY", "x"))
    p.conn.commit()
    monkeypatch.setenv("FEATURE_PROJECT_PROP_LOCK", "1")
    app = (f"import streamlit as st\nfrom core.db import connect\nfrom core.pipeline import Pipeline\n"
           f"from dashboard.steps.step1_characters import weapon_select\n"
           f"weapon_select(Pipeline(connect({db!r})), {pid}, 'KELLY', st)\n")
    at = AppTest.from_string(app).run()
    assert not at.exception
    at.selectbox(key=f"weapon_{pid}_KELLY").set_value(aid).run()
    assert prop_lock.weapon_table(connect(db), pid) == {"KELLY": aid}


class ReviewFixesTest(unittest.TestCase):
    """Rà gộp Đ16v2 (12/10): a negation keeps its meaning; the scale sentence is taken whole; "Damage scale" is not a size."""
    setUp, tearDown, _asset, _prompt = base.PropLockTest.setUp, base.PropLockTest.tearDown, base.PropLockTest._asset, base.PropLockTest._prompt

    def test_negated_colour_is_not_cut(self):
        with mock.patch.dict(os.environ, FLAG_ON):
            for text in ("Fix: no translucent amber glue wall, plain white.", "Never a translucent amber glue wall."):
                out, cut = prop_lock.clean_prompt(self.p.conn, self.pid, {"image_prompt": text}, text)
                self.assertEqual((out, cut), (text, []))

    def test_scale_sentence_whole_and_damage_scale_ignored(self):
        self.assertEqual(prop_lock._scale_span("SMG. In-game scale: approx. 3.0 head-heights; held two-handed. Fires fast")[2],
                         "approx. 3.0 head-heights; held two-handed")
        self.assertIsNone(prop_lock._scale_span("Damage scale: 1.2. Fast."))
