"""Sổ kinh nghiệm của nhà máy (core/experience, người dùng 2026-10-01): cases with evidence, read back by any stage."""
import json
import os
import tempfile
import unittest

from core import experience
from core.db import connect


class ExperienceTests(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")

    def add(self, key, outcome, subjects, view=None, confirmed="người", job=None):
        return experience.record(self.conn, key=key, stage="qc_image", outcome=outcome, note=key, source="test", subjects=subjects,
                                 view=view, confirmed_by=confirmed, job_id=job)

    def test_a_case_is_kept_once(self):
        self.assertTrue(self.add("a", "success", ["KENTA"]))
        self.assertFalse(self.add("a", "failure", ["KENTA"]))
        with self.assertRaises(ValueError):
            self.add("b", "maybe", ["KENTA"])

    def test_same_people_and_view_and_checker_mistakes_come_first(self):
        self.add("plain", "success", ["KENTA"], "behind")
        self.add("other_person", "false_alarm", ["MAXIM"], "behind")
        self.add("alarm_front", "false_alarm", ["KENTA"], "camera")
        self.add("alarm_back", "false_alarm", ["KENTA"], "behind")
        self.add("unconfirmed", "missed", ["KENTA"], "behind", confirmed=None)
        self.add("judged_now", "missed", ["KENTA"], "behind", job=7)
        keys = [c["key"] for c in experience.relevant(self.conn, ["qc_image"], ["KENTA"], ["behind"], limit=3, exclude_jobs=[7])]
        self.assertEqual(keys, ["alarm_back", "alarm_front", "plain"])
        experience.record(self.conn, key="same_shot", stage="qc_image", outcome="false_alarm", source="t", subjects=["KENTA"],
                          view="behind", note="x", confirmed_by="người", project_id=8, shot="S2·3")
        keys = [c["key"] for c in experience.relevant(self.conn, ["qc_image"], ["KENTA"], ["behind"], exclude_shots=[(8, "S2·3")])]
        self.assertNotIn("same_shot", keys)                                    # another take of a shot being judged = the answer

    def test_every_character_of_the_scene_gets_a_case(self):
        for n in range(4):
            self.add(f"kenta{n}", "false_alarm", ["KENTA"], "behind")
        self.add("kenta_with_maxim", "false_alarm", ["KENTA", "MAXIM"], "behind")
        experience.record(self.conn, key="maxim_cap", stage="qc_image", outcome="failure", source="t", subjects=["KENTA", "MAXIM"],
                          view="behind", note="MAXIM nhìn từ sau: mũ đội xuôi", confirmed_by="người")
        keys = [c["key"] for c in experience.relevant(self.conn, ["qc_image"], ["KENTA", "MAXIM"], ["behind"], limit=4)]
        self.assertIn("maxim_cap", keys)                                       # the case ABOUT Maxim, not one he only stands in

    def test_one_outcome_never_fills_the_whole_list(self):
        for n in range(4):
            self.add(f"alarm{n}", "false_alarm", ["KENTA"], "behind")
        self.add("real_flip", "failure", ["KENTA"], "behind")
        keys = [c["key"] for c in experience.relevant(self.conn, ["qc_image"], ["KENTA"], ["behind"], limit=4)]
        self.assertIn("real_flip", keys)
        self.assertEqual(sum(k.startswith("alarm") for k in keys), 3)

    def test_decisions_made_by_experiment_scripts_are_not_human_cases(self):
        from core.pipeline import Pipeline
        p = Pipeline(self.conn)
        pid = p.create_project("t")
        sid = p.create_scene(pid, 1, "s")
        ids = []
        for note in ("[thử tự động] Claude xem ảnh trước khi duyệt", "tay thừa ngón — vẽ lại"):
            j = p.create_job(sid, "image_gen")
            self.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (j,))
            p.reject(j, "user", note=note, respawn=False)
            ids.append(j)
        experience.import_review_log(self.conn, tempfile.mkdtemp())
        notes = [r["note"] for r in self.conn.execute("SELECT note FROM experience_cases")]
        self.assertEqual(notes, ["tay thừa ngón — vẽ lại"])

    def test_a_label_corrected_from_block_to_pass_is_a_false_alarm(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "verdicts.json"), "w", encoding="utf-8") as f:
            json.dump([{"job": 319, "shot": "S1·2", "verdict": "chặn", "issues": [{"loai": "A1 trái/phải", "mo_ta": "găng sai bên"}]},
                       {"job": 353, "shot": "S1·1", "verdict": "nhỏ", "issues": [{"loai": "cỡ cảnh", "mo_ta": "MCU thay vì CU"}]}], f)
        with open(os.path.join(d, "labels_v2.json"), "w", encoding="utf-8") as f:
            json.dump({"overrides": {"319": {"old": "chặn", "verdict": "đạt", "issues": [], "why": "xét theo bên thân người: đúng"}}}, f)
        self.assertEqual(experience.import_qc_labels(self.conn, d, labels_dir=d), 2)
        rows = {r["job_id"]: dict(r) for r in self.conn.execute("SELECT * FROM experience_cases")}
        self.assertEqual(rows[319]["outcome"], "false_alarm")
        self.assertIn("bên thân người", rows[319]["note"])
        self.assertEqual(rows[353]["outcome"], "success")
        self.assertIn("BÁO NHẦM", experience.text_line(rows[319]))


if __name__ == "__main__":
    unittest.main()
