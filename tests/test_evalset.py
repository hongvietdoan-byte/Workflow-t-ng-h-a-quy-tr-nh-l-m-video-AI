import copy
import unittest

from core import evalset as ev


class EvalSetTests(unittest.TestCase):
    def test_cases_are_well_formed(self):
        cases = ev.load_cases()
        self.assertGreaterEqual(len(cases), 12)
        ids = [c["id"] for c in cases]
        self.assertEqual(len(ids), len(set(ids)))
        for c in cases:
            for key in ("shot_any", "lighting_any", "mood_any", "motion_camera_any", "characters", "must_not"):
                self.assertIn(key, c["expect"], f"{c['id']} missing {key}")
            self.assertTrue(c["review_questions"])

    def test_golden_outputs_pass_all_hard_checks(self):
        cases = {c["id"]: c for c in ev.load_cases()}
        for case_id, out in ev.load_golden().items():
            res = ev.run_case(cases[case_id], out)
            self.assertEqual(res["failed"], [], f"{case_id}: {res['failed']}")
            self.assertEqual(res["score"], 1.0)

    def golden(self, case_id="action_chase"):
        return copy.deepcopy(ev.load_golden()[case_id]), ev.get_case(case_id)

    def test_vietnamese_prompt_fails_english_check(self):
        out, case = self.golden()
        out["analysis"]["scenes"][0]["image_prompt"] = "Cảnh rộng, Mira chạy qua khu chợ đông đúc dưới ánh nắng gắt " * 3
        self.assertTrue(any("English" in f for f in ev.run_case(case, out)["failed"]))

    def test_missing_character_description_reuse_fails(self):
        out, case = self.golden()
        out["analysis"]["scenes"][0]["image_prompt"] = (
            "Wide low angle shot of a runner sprinting through a market in harsh midday sun with dust, "
            "rim light, teal and orange palette, cinematic, no text, motion blur on background")
        failed = ev.run_case(case, out)["failed"]
        self.assertTrue(any("description reused" in f for f in failed))

    def test_ip_term_and_missing_ip_note_fail(self):
        out, case = self.golden("ip_trap_amazon")
        out["analysis"]["scenes"][0]["image_prompt"] += " like Wonder Woman"
        out["analysis"]["ip_risk_notes"] = []
        failed = " | ".join(ev.run_case(case, out)["failed"])
        self.assertIn("banned", failed)
        self.assertIn("IP risk flagged", failed)

    def test_ip_name_allowed_inside_ip_risk_notes(self):
        out, case = self.golden("ip_trap_amazon")
        out["analysis"]["ip_risk_notes"] = ["Resembled Wonder Woman; redesigned."]
        self.assertEqual(ev.run_case(case, out)["failed"], [])

    def test_motion_appearance_and_camera_checks(self):
        out, case = self.golden()
        out["motion"]["scenes"][0]["motion_prompt"] = (
            "A woman wearing a silver leather jacket stands still while nothing else happens in the frame at all")
        res = ev.run_case(case, out)
        self.assertTrue(any("camera move fits genre" in f for f in res["failed"]))
        self.assertTrue(any("appearance" in w for w in res["warnings"]))

    def test_vague_praise_words_are_warned_not_failed(self):
        out, case = self.golden()
        out["analysis"]["scenes"][0]["image_prompt"] += ", stunning masterpiece"
        res = ev.run_case(case, out)
        self.assertEqual(res["failed"], [])
        self.assertTrue(any("praise" in w for w in res["warnings"]))

    def test_invalid_json_shape_reports_schema_failure(self):
        case = ev.get_case("action_chase")
        res = ev.run_case(case, {"analysis": {"characters": "nope"}})
        self.assertEqual(res["score"], 0.0)

    def test_bundles_and_review_sheet(self):
        case = ev.get_case("horror_corridor")
        text = ev.director_bundle(case)
        self.assertIn("HÀNH LANG BỆNH VIỆN BỎ HOANG", text)
        self.assertIn("Ví dụ mẫu", text)
        self.assertIn("Hướng dẫn theo thể loại", text)
        sheet = ev.review_sheet({"horror_corridor": ev.load_golden()["horror_corridor"]})
        self.assertIn("- [ ] Có cảm giác bất an", sheet)
        self.assertIn("image_prompt (cảnh 1)", sheet)


if __name__ == "__main__":
    unittest.main()
