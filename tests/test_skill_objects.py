"""Lỗi hệ thống 3 (#27 13/10, cờ skill_object_guard): skin Gloowall OB55 'cửa thang máy' → model video vẽ thang máy thật. Chữ thật lấy
từ job 909 / scenes 284–287 của #27 (CSDL sản xuất, đọc). Dữ liệu giả, không gọi API."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import numpy as np

from core import assets, prop_lock, skill_objects
from core.db import connect
from core.pipeline import Pipeline

ON = {"FEATURE_SKILL_OBJECT_GUARD": "1"}
OFF = {"FEATURE_SKILL_OBJECT_GUARD": "0"}

GLUE_DESC = ("Tường keo FF (bom keo ném ra dựng thành bức tường chắn đạn). 2 DẠNG: (a) MẶC ĐỊNH — tường keo màu TRẮNG trơn, "
             "không họa tiết, không hình; (b) skin Gloowall OB55 (ID 907105556) — tường dạng cửa thang máy kim loại xám có khung, đèn "
             "và mảnh giấy dán, theo ảnh Kho. Shot không nói dạng nào → dạng mặc định.")
# job 909 (#27 shot 16, Kling) — the motion prompt really sent
JOB_909 = ("Kelly, out in the open, flicks the glue grenade toward the camera in one quick throw; the instant it hits the ground about one "
           "metre in front of her, the Gloowall OB55 glue wall POPS UP at once - in a fraction of a second it shoots straight up out of "
           "the ground to its full height, taller than Kelly standing: a thick, gently curved slab (only slightly bowed, not a deep "
           "curve) whose surface is the Gloowall OB55 skin of grey metal elevator-door panels with a row of small yellow lights and red "
           "side panels. As it pops up Kelly drops into a crouch behind it and is completely hidden. It ends with the tall, slightly "
           "curved elevator-skin glue wall filling the middle of the frame, Kelly hidden behind it, matching the last frame. Fix: right "
           "after the throw she crouches down where she stands while the wall shoots up out of the ground right in front of her, exactly "
           "like the last frame (grey metal elevator-door skin, closed doors, row of small yellow lights, red side panels).")
# scene 287 image prompt (shot 19)
SCENE_287 = ("A Gloowall OB55 skin glue wall (grey metal elevator-door style panel with a frame, small lights and paper stickers, as its "
             "reference picture) fills most of the frame, metal surface with stickers.")
# scene 285 (shot 17): "the tower rising out of the top of the frame" is not the wall appearing
SCENE_285 = ("Kelly crouched low behind a TALL Gloowall OB55 glue wall. The Clock Tower stands close by, its arched wooden door at ground "
             "level, the tower rising out of the top of the frame.")


class SkillObjectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("vat ky nang")
        c = self.p.conn
        c.execute("UPDATE projects SET game='FF' WHERE id=?", (self.pid,))
        aid = c.execute("INSERT INTO assets (game, kind, name, aliases, description) VALUES ('FF','weapon','Bom keo','Gloowall',?)",
                        (GLUE_DESC,)).lastrowid
        c.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?,?)", (self.pid, aid))
        c.commit()
        self.conn = c

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_flag_off_changes_nothing(self):
        with mock.patch.dict(os.environ, OFF):
            self.assertEqual(skill_objects.guard_prompt(self.conn, self.pid, JOB_909), (JOB_909, [], []))
            self.assertEqual(skill_objects.issues(self.conn, self.pid, {"action": JOB_909}), [])
            self.assertNotIn("VẬT KỸ NĂNG", assets.context_text(self.conn, self.pid))
            self.assertIn("cửa thang máy", assets.context_text(self.conn, self.pid))

    def test_job_909_prompt_loses_the_lift_words_and_gets_the_ban(self):
        with mock.patch.dict(os.environ, ON):
            new, removed, names = skill_objects.guard_prompt(self.conn, self.pid, JOB_909)
        self.assertEqual(names, ["Bom keo"])
        low = new.lower()
        for word in ("elevator", "door", "lift"):
            self.assertNotIn(word, low)
        self.assertIn("grey metal flat panels", new)
        self.assertIn("no opening of any kind", new)
        self.assertIn("nobody stands in it", new)
        self.assertIn("closed doors", removed)
        with mock.patch.dict(os.environ, ON):
            twice = skill_objects.guard_prompt(self.conn, self.pid, new)[0]
        self.assertEqual(twice.count("is a solid skill object"), 1)        # once, not stacked on a re-send

    def test_image_prompt_of_shot_19_and_a_house_door_stays(self):
        with mock.patch.dict(os.environ, ON):
            new, removed, _ = skill_objects.guard_prompt(self.conn, self.pid, SCENE_287 + " The pale house has a red front door.")
        self.assertIn("grey metal flat panel with a frame", new)
        self.assertIn("red front door", new)              # a sentence not about the skill object is untouched
        self.assertEqual(removed, ["elevator-door style panel"])

    def test_a_building_door_in_a_wall_sentence_stays(self):
        """Rà gộp 13/10: câu chỉ có 'wall' (không tên vật kỹ năng) mà nói tường/cửa nhà thật → giữ nguyên; câu 'the wall shoots up'
        (job 909) vẫn được sửa."""
        with mock.patch.dict(os.environ, ON):
            new, _, _ = skill_objects.guard_prompt(self.conn, self.pid, "Kelly throws the glue grenade. She then runs through the "
                                                   "warehouse door in the brick wall. The wall shoots up, grey elevator doors.")
        self.assertIn("warehouse door in the brick wall", new)
        self.assertIn("grey flat panels", new)

    def test_text_without_skill_object_is_untouched(self):
        with mock.patch.dict(os.environ, ON):
            text = "Kelly bursts out of the side doorway into the open air."
            self.assertEqual(skill_objects.guard_prompt(self.conn, self.pid, text), (text, [], []))

    def test_yellow_suggests_code_composite_only_when_the_wall_appears(self):
        with mock.patch.dict(os.environ, ON):
            rising = skill_objects.issues(self.conn, self.pid, {"action": JOB_909})
            standing = skill_objects.issues(self.conn, self.pid, {"image_prompt": SCENE_285})
            via_formula = prop_lock.issues(self.conn, self.pid, {"action": JOB_909})   # project_prop_lock off: still said
        self.assertTrue(all(i["level"] == "warn" for i in rising))
        plan = [i for i in rising if "suggest" in i]
        self.assertEqual(plan[0]["suggest"]["route"], "compose")
        self.assertEqual(plan[0]["suggest"]["tool"], "tools/skill_object_composite.py")
        self.assertFalse([i for i in standing if "suggest" in i])
        self.assertTrue([i for i in via_formula if "suggest" in i])

    def test_director_gets_shape_words_and_a_note(self):
        with mock.patch.dict(os.environ, ON):
            ctx = assets.context_text(self.conn, self.pid)
        self.assertNotIn("cửa thang máy", ctx)
        self.assertIn("tường dạng tấm phẳng kim loại xám", ctx)
        self.assertIn("VẬT KỸ NĂNG", ctx)

    def test_guard_keeps_skin_reference_not_plain_metal(self):
        """V4 (rà gốc 13/10, G8): 'metal-panel skin' made job 908 a plain steel slab — the skin is a pattern, taken from a picture."""
        with mock.patch.dict(os.environ, ON):
            new = skill_objects.guard_prompt(self.conn, self.pid, JOB_909)[0]
            mapped = skill_objects.guard_prompt(self.conn, self.pid, skill_objects.deployed_line(5, "Bom keo") + " " + JOB_909)[0]
        self.assertNotIn("metal-panel skin", new)
        self.assertIn("patterned skin glue wall", new)
        self.assertIn("The glue wall skin is a printed surface pattern on one solid block", new)
        self.assertIn("skin pattern shown in Image 5 glue wall", mapped)     # the DEPLOYED picture of the prompt is pointed at
        self.assertIn("The glue wall skin is the pattern shown in Image 5", mapped)
        for word in ("elevator", "door", "lift"):
            self.assertNotIn(word, mapped.lower())
        with mock.patch.dict(os.environ, ON):
            self.assertEqual(skill_objects.guard_prompt(self.conn, self.pid, new)[0].count("printed surface pattern"), 1)

    def _rising_scene(self):
        sid = self.p.create_scene(self.pid, 1)
        self.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"action": JOB_909, "shot_no": 1}), sid))
        self.conn.commit()
        return sid

    def test_thrown_glue_without_deployed_picture_is_yellow_never_red(self):
        """Rà S2 13/10 mục 1 (quyết định người dùng 21:31: tường XUẤT HIỆN LUÔN): shot ném keo không bao giờ ĐỎ vì vật kỹ năng; Kho
        thiếu ảnh dạng triển khai → chỉ VÀNG 'skin tả bằng chữ'."""
        from core import prompt_formula
        sid = self._rising_scene()
        with mock.patch.dict(os.environ, OFF):
            self.assertEqual(skill_objects.send_issues(self.conn, self.pid, {"action": JOB_909}), [])
        with mock.patch.dict(os.environ, ON):
            got = skill_objects.send_issues(self.conn, self.pid, {"action": JOB_909})
            thrown = skill_objects.send_issues(self.conn, self.pid, {"action": "Kelly throws the gloo grenade and ducks."})
            standing = skill_objects.send_issues(self.conn, self.pid, {"image_prompt": SCENE_285})
            motion_reds = prompt_formula.red_issues(self.conn, sid, "motion")
            yellow = skill_objects.issues(self.conn, self.pid, {"action": JOB_909})
        self.assertEqual([i["level"] for i in got], ["warn"])
        self.assertIn("chưa có ảnh dạng triển khai, skin tả bằng chữ", got[0]["msg"])
        self.assertEqual([i["level"] for i in thrown], ["warn"])
        self.assertEqual(standing, [])                                     # the wall already standing: the start frame shows it
        self.assertFalse([x for x in motion_reds if "Đạo cụ dự án" in x])  # the clip is not held for the skill object
        self.assertTrue([i for i in yellow if "skin tả bằng chữ" in i["msg"]])   # said where the prompt formula shows VÀNG
        tid = self.p.create_scene(self.pid, 2)
        self.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                          (json.dumps({"action": "Kelly throws gloo grenade at the gate", "shot_no": 2}), tid))
        self.conn.commit()
        with mock.patch.dict(os.environ, ON):
            self.assertEqual(prompt_formula.red_issues(self.conn, tid, "motion"), [])
        # the Kho gets a picture of the wall deployed → nothing said, and the picture goes with the shot
        aid = self.conn.execute("SELECT id FROM assets WHERE name='Bom keo'").fetchone()["id"]
        pic = os.path.join(self.tmp, "tuong_keo.png")
        from PIL import Image
        Image.new("RGB", (400, 400), (90, 90, 90)).save(pic)
        self.conn.execute("INSERT INTO asset_images (asset_id, path, label, status) VALUES (?,?,?, 'approved')",
                          (aid, pic, "Tường keo dạng triển khai (skin Gloowall OB55)"))
        self.conn.commit()
        with mock.patch.dict(os.environ, ON):
            self.assertEqual(skill_objects.send_issues(self.conn, self.pid, {"action": JOB_909}), [])
            pics = skill_objects.deployed_pictures(self.conn, self.pid, [{"data": {"action": JOB_909}}])
        self.assertEqual(pics, [("Bom keo", pic)])

    def test_wall_appears_at_once_never_described_rising(self):
        """Rà S2 13/10 mục 2: câu vật kỹ năng không tả quá trình mọc (rise/grow/emerge/shoots up/pops up) → 'already standing at full
        height'; câu cấm nói tường xuất hiện luôn; gửi lại không chồng câu."""
        import re
        with mock.patch.dict(os.environ, ON):
            new, removed, _ = skill_objects.guard_prompt(self.conn, self.pid, JOB_909)
            twice = skill_objects.guard_prompt(self.conn, self.pid, new)[0]
            vi = skill_objects.guard_prompt(self.conn, self.pid, "Kelly ném bom keo, tường keo mọc lên ngay trước mặt.")[0]
            house = skill_objects.guard_prompt(self.conn, self.pid, "Kelly throws the glue grenade. The sun rises over the hills.")[0]
        ban = "appears at once at full height, never grows, rises or emerges"
        self.assertIn(ban, skill_objects.FORBID)
        body = new.replace(skill_objects.forbid_sentence(["Bom keo"]), "")
        self.assertFalse(re.search(r"(?i)\b(?:ris(?:e|es|ing)|rose|grow(?:s|ing)?|emerg\w*|shoots?\s+(?:\w+\s+)?up|pops?\s+up)\b", body),
                         body)
        self.assertIn("already standing at full height", body)
        self.assertIn(ban, new)
        self.assertEqual(twice, new)                                     # idempotent: a re-send changes nothing
        self.assertNotIn("mọc", vi)
        self.assertIn("đã đứng sẵn đủ cao", vi)
        self.assertIn("The sun rises over the hills", house)            # not a sentence about the skill object
        self.assertTrue([w for w in removed if "up" in w.lower()])     # what was replaced is said (diag)

    def test_standing_words_keep_the_grammar_and_other_subjects(self):
        st = skill_objects.standing_text
        self.assertEqual(st("The glue wall has risen.")[0], "The glue wall has been already standing at full height.")
        self.assertEqual(st("The glue wall will rise.")[0], "The glue wall will stand at full height at once.")
        self.assertEqual(st("The glue wall rose.")[0], "The glue wall was already standing at full height.")
        for keep in ("The drone hovers, then it rises. Kelly throws the glue grenade.",
                     "The camera rises over the glue wall.", "Kelly rises behind the glue wall."):
            self.assertEqual(st(keep)[0], keep)
        self.assertIn("As it is already standing at full height Kelly",
                      st("The glue wall stands. As it pops up Kelly ducks.")[0])

    def test_yellow_says_appears_at_once_and_director_is_told(self):
        with mock.patch.dict(os.environ, ON):
            rising = skill_objects.issues(self.conn, self.pid, {"action": JOB_909})
            ctx = assets.context_text(self.conn, self.pid)
        plan = [i for i in rising if "suggest" in i]
        text = " ".join(i["msg"] for i in plan) + " " + " ".join(plan[0]["suggest"]["steps"])
        self.assertIn("xuất hiện luôn", text)
        for word in ("mọc lên", "trồi lên"):
            self.assertNotIn(word, text)
        self.assertIn("XUẤT HIỆN LUÔN", ctx)
        self.assertIn("không tả quá trình mọc", ctx)
        from core import features
        label = features.FEATURES["skill_object_guard"]["label"]
        self.assertNotIn("mọc lên", label)
        self.assertNotIn("ĐỎ", label)

    def test_skin_sentence_is_generic_and_clean(self):
        """Rà S2 13/10 mục 3: câu skin nói 'glue wall' chung, không lấy tên Kho / biến thể (chữ Việt, 'thang máy', elevator)."""
        items = [{"name": "Tường keo thang máy", "images": [{"variant": "skin Gloowall thang máy elevator", "path": "x.png"}]}]
        with mock.patch.object(prop_lock, "chosen_variant", return_value="skin Gloowall thang máy elevator"):
            s = skill_objects.skin_sentence(items, "the glue wall skin", [], None)
            shown = skill_objects.skin_sentence(items, "the glue wall skin", [], 4)
        for t in (s, shown):
            self.assertTrue(t.startswith("The glue wall skin is"), t)
            for word in ("thang", "elevator", "Tường", "Gloowall"):
                self.assertNotIn(word, t)
        self.assertIn("Image 4", shown)
        with mock.patch.dict(os.environ, ON):
            new = skill_objects.guard_prompt(self.conn, self.pid, JOB_909)[0]
        self.assertIn("The glue wall skin is a printed surface pattern on one solid block", new)

    def test_lone_elevator_word_becomes_patterned_not_metal(self):
        """Rà S2 13/10 mục 4: 'elevator' một mình → 'patterned' (không 'metal-panel', lỗi job 908 tấm thép trơn)."""
        with mock.patch.dict(os.environ, ON):
            new = skill_objects.guard_prompt(self.conn, self.pid, "The glue wall has a grey elevator look with small lights.")[0]
        self.assertIn("grey patterned look", new)
        self.assertNotIn("metal-panel", new)

    def test_composite_hard_cut_by_default(self):
        """Rà S2 13/10 mục 2: ghép mặc định CẮT CỨNG (tường xuất hiện luôn) — khung ngay sau điểm cắt đã là khung cuối."""
        import inspect
        h, w = 40, 20
        clip = [np.full((h, w, 3), 10 * i, np.uint8) for i in range(12)]
        end = np.full((h, w, 3), 200, np.uint8)
        frames = skill_objects.composite_frames(clip, end, cut_index=3, total=12, shake=0)
        self.assertTrue((frames[2] == clip[2]).all())
        self.assertTrue((frames[3] == end).all())          # no partial wall: it is there at once
        self.assertEqual(inspect.signature(skill_objects.compose).parameters["rise"].default, 0)
        from tools import skill_object_composite
        self.assertEqual(skill_object_composite.parser().get_default("rise"), 0)

    def test_composite_old_rise_still_possible_when_asked(self):
        h, w = 40, 20
        clip = [np.full((h, w, 3), 10 * i, np.uint8) for i in range(12)]
        end = np.full((h, w, 3), 200, np.uint8)
        end[:20] = clip[3][:20]                            # top half unchanged → the object is the lower half
        frames = skill_objects.composite_frames(clip, end, cut_index=3, total=24, rise=4, shake=3, shake_px=2)
        self.assertEqual(len(frames), 24)
        self.assertTrue((frames[2] == clip[2]).all())     # before the cut: the clip
        self.assertEqual(skill_objects.wall_top(end, clip[3]), 20)
        first = frames[3]
        self.assertTrue((first[-5:] == 200).all() and (first[:h - 5] != 200).all())   # 1/4 of the 20 rows risen
        self.assertTrue((frames[6][20:] == 200).all())    # fully up after `rise` frames
        self.assertTrue((frames[-1] == end).all())        # held to the end

    def test_shift_repeats_the_edge(self):
        img = np.arange(4 * 4 * 3, dtype=np.uint8).reshape(4, 4, 3)
        moved = skill_objects._shift(img, 1, 0)
        self.assertTrue((moved[:, 1:] == img[:, :-1]).all() and (moved[:, 0] == img[:, 0]).all())


if __name__ == "__main__":
    unittest.main()
