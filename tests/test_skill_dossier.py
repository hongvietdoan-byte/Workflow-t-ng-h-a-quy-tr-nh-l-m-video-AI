"""skill_dossier (người dùng 2026-09-30): the real Kenta dossier and how a skill shot picks up its phase, words and frame."""
import os
import unittest
from unittest import mock

from core import assets, skill_dossier

ON = {"FEATURE_SKILL_DOSSIER": "1"}


class KentaDossierTests(unittest.TestCase):
    def setUp(self):
        self.d = skill_dossier.load("Kenta")

    def test_the_dossier_is_whole(self):
        self.assertIsNotNone(self.d)
        self.assertIn("KENTA", skill_dossier.names())
        ids = [p["id"] for p in self.d["phases"]]
        self.assertIn(self.d["default_phase"], ids)
        for p in self.d["phases"]:
            self.assertTrue(os.path.exists(os.path.join(self.d["_dir"], p["frame"])), p["frame"])
            self.assertTrue(p["image_en"] and p["video_en"] and p["vi"])
        for seq in self.d["sequences"].values():
            self.assertTrue(set(seq) <= set(ids))
        self.assertTrue(set(self.d["phase_hints"]) <= set(ids))
        self.assertTrue(os.path.exists(os.path.join(self.d["_dir"], self.d["storyboard"])))
        self.assertIn("katana", self.d["never_en"])

    def test_skill_shot_and_its_phase(self):
        find = skill_dossier.shot_skill
        self.assertIsNone(find({"characters": ["KENTA"], "image_prompt": "Kenta walks across the plaza"}))
        self.assertIsNone(find({"characters": ["KELLY"], "image_prompt": "a tornado skill"}))      # not the one with the dossier
        hit = find({"characters": ["KENTA"], "image_prompt": "Kenta tung Đột Kích Lốc Xoáy, gió xuyên qua tường Bom Keo"})
        self.assertEqual(hit["phase"]["id"], "through_gloo")
        hit = find({"characters": ["KENTA"], "action_peak": "vào thế chuẩn bị, lưỡi năng lượng hiện trong tay phải"})
        self.assertEqual(hit["phase"]["id"], "prepare")
        self.assertEqual(find({"characters": ["KENTA"], "image_prompt": "Kenta uses his skill"})["phase"]["id"], "wind_fly")
        hit = find({"characters": ["KENTA", "KELLY"], "skill_phase": "KENTA:move_vortex", "image_prompt": "Kenta chạy"})
        self.assertEqual((hit["phase"]["id"], hit["how"]), ("move_vortex", "skill_phase"))
        only_wind = find({"characters": ["KELLY"], "skill_phase": "KENTA:through_gloo"})   # his wind reaches her, he is not in frame
        self.assertEqual(only_wind["phase"]["id"], "through_gloo")

    def test_words_frame_and_negative(self):
        hit = skill_dossier.shot_skill({"characters": ["KENTA"], "skill_phase": "prepare"})
        s = skill_dossier.image_sentence(hit)
        self.assertIn("horizontal stripes", s)
        self.assertIn("scabbard, worn horizontally across the back of his waist", s)
        self.assertIn("Never draw: drawn or unsheathed katana", s)
        self.assertIn("stays in its scabbard", skill_dossier.video_sentence(hit))
        self.assertTrue(skill_dossier.video_negative(hit, "blurry").startswith("blurry, drawn or unsheathed katana"))
        self.assertEqual(skill_dossier.video_negative(None, "blurry"), "blurry")
        ref = skill_dossier.reference(hit)
        self.assertEqual((ref["role"], ref["label"]), (skill_dossier.ROLE, "KENTA"))
        self.assertTrue(ref["path"].endswith("prepare_16.70.jpg"))

    def test_end_phase_for_the_end_frame_and_the_clip(self):
        data = {"characters": ["KENTA"], "skill_phase": "KENTA:prepare", "skill_phase_end": "KENTA:swing_vortex"}
        hit = skill_dossier.shot_skill(data)
        self.assertEqual(hit["end"]["id"], "swing_vortex")
        self.assertIn(" Then: He flicks the hologram blade in one horizontal sweep", skill_dossier.video_sentence(hit))
        end = skill_dossier.shot_skill(skill_dossier.at_end(data))
        self.assertEqual(end["phase"]["id"], "swing_vortex")
        self.assertTrue(skill_dossier.reference(end)["path"].endswith("swing_vortex_17.13.jpg"))
        self.assertIs(skill_dossier.at_end({"skill_phase": "prepare"})["skill_phase"], "prepare")

    def test_the_frame_replaces_the_skill_icon_and_sits_after_the_people(self):
        ref = {"path": "f.jpg", "label": "KENTA", "role": skill_dossier.ROLE}
        refs = [{"path": "k.png", "label": "KENTA", "role": "character"}, {"path": "icon.png", "label": "KENTA", "role": "related"},
                {"path": "e.png", "label": "EVA", "role": "character"}, {"path": "t.png", "label": "Tháp", "role": "location"}]
        out = skill_dossier.add_reference(refs, ref, 6)
        self.assertEqual([r["path"] for r in out], ["k.png", "e.png", "f.jpg", "t.png"])
        full = skill_dossier.add_reference(refs[:1] + refs[2:], ref, 3)       # full: the place gives up its slot, never a person
        self.assertEqual([r["path"] for r in full], ["k.png", "e.png", "f.jpg"])
        self.assertIs(skill_dossier.add_reference(refs, None, 6), refs)
        note = assets.reference_note(out)
        self.assertIn("Image 3 is a frame of the official game video of KENTA's skill", note)

    def test_contradictions_are_named(self):
        bad = {"characters": ["KENTA"], "image_prompt": "Kenta rút katana chém, cơn lốc xoáy làm tường keo vỡ tan"}
        problems = skill_dossier.shot_problems(bad)
        self.assertEqual(len(problems), 1)
        self.assertIn("rút katana", problems[0])
        self.assertIn("tường keo vỡ", problems[0])
        self.assertEqual(skill_dossier.shot_problems({"characters": ["KENTA"], "image_prompt": "Kenta rút katana"}), [])   # no skill

    def test_director_block_only_for_people_with_a_dossier(self):
        block = skill_dossier.director_block(["Kelly", "kenta"])
        self.assertIn("HỒ SƠ KỸ NĂNG KENTA", block)
        self.assertIn("`through_gloo`", block)
        self.assertIn("skill_phase", block)
        self.assertEqual(skill_dossier.director_block(["Kelly"]), "")

    def test_off_by_default(self):
        with mock.patch.dict(os.environ, {"FEATURE_SKILL_DOSSIER": "0"}):
            self.assertFalse(skill_dossier.enabled())
        with mock.patch.dict(os.environ, ON):
            self.assertTrue(skill_dossier.enabled())


if __name__ == "__main__":
    unittest.main()
