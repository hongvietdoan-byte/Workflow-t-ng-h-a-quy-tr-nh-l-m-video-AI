"""GĐ-A4: a paid Director answer is not thrown away or half-saved, and a re-run never overwrites what the person edited by hand."""
import copy
import json
import unittest
import unittest.mock

from core import llm_io, llm_runner, prompts
from core.db import connect
from core.llm_io import SchemaError, store_scene_analysis, update_character
from core.pipeline import Pipeline
from tests.test_llm_io_preflight import ANALYSIS


def shot(**extra):
    return {"size": "MS", "role": extra.pop("role", "setup"), "duration_s": 3, "image_prompt": "p", "action": "a", **extra}


class DirectorSafetyTest(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        self.p.create_scene(self.pid, 1, "CẢNH 1")

    def test_an_unknown_scene_is_sent_back_to_claude_not_refused_after_payment(self):
        bad = copy.deepcopy(ANALYSIS)
        bad["scenes"][0]["idx"] = 9
        with self.assertRaises(SchemaError):
            llm_io.validate_for_project(self.p, self.pid)(bad)

    def test_a_refused_answer_leaves_the_bible_untouched(self):
        store_scene_analysis(self.p, self.pid, ANALYSIS)
        bad = copy.deepcopy(ANALYSIS)
        bad["characters"][0]["description"] = "ghi đè"
        bad["scenes"][0]["idx"] = 9                                                   # refused while saving
        with self.assertRaises(SchemaError):
            store_scene_analysis(self.p, self.pid, bad)
        self.p.conn.commit()                                                          # a later commit must not save half of it
        self.assertEqual(self.p.conn.execute("SELECT description FROM characters WHERE name='Lyra'").fetchone()[0],
                         "Nữ, tóc bạc, giáp cobalt")

    def test_hand_edits_to_a_character_survive_a_director_rerun(self):
        store_scene_analysis(self.p, self.pid, ANALYSIS)
        update_character(self.p, self.pid, "Lyra", "Tóc bob đen ngắn, vòng cổ", "bộ thể thao vàng")
        again = copy.deepcopy(ANALYSIS)
        again["characters"][0]["description"] = "đuôi ngựa cao"
        store_scene_analysis(self.p, self.pid, again)
        row = self.p.conn.execute("SELECT description, wardrobe FROM characters WHERE name='Lyra'").fetchone()
        self.assertEqual(tuple(row), ("Tóc bob đen ngắn, vòng cổ", "bộ thể thao vàng"))
        amazon = self.p.conn.execute("SELECT wardrobe FROM characters WHERE name='Nữ chiến binh Amazon'").fetchone()[0]
        del again["characters"][1]["wardrobe"]
        store_scene_analysis(self.p, self.pid, again)                                 # a missing wardrobe no longer wipes it
        self.assertEqual(self.p.conn.execute("SELECT wardrobe FROM characters WHERE name='Nữ chiến binh Amazon'").fetchone()[0], amazon)

    def test_the_director_sees_the_current_bible(self):
        store_scene_analysis(self.p, self.pid, ANALYSIS)
        text = prompts.bible_block(self.p, self.pid)
        self.assertIn("- Lyra", text)
        self.assertIn(text, prompts.build_director_bundle(self.p, self.pid))

    def test_the_paid_answer_is_kept_even_when_saving_fails(self):
        class Bad(llm_runner.MockLlm):
            pass
        store_scene_analysis(self.p, self.pid, ANALYSIS)
        obj = copy.deepcopy(ANALYSIS)
        with unittest.mock.patch.object(llm_runner, "ask_json", return_value=(obj, 1, 1)), \
                unittest.mock.patch.object(llm_io, "store_scene_analysis", side_effect=SchemaError("boom")):
            with self.assertRaises(SchemaError):
                llm_runner.run_director(self.p, self.pid, Bad())
        self.assertEqual(json.loads(self.p.project(self.pid)["director_raw"])["scenes"][0]["idx"], 1)


class ShotModeRerunTest(unittest.TestCase):
    def test_fields_set_by_hand_on_a_shot_survive_a_director_rerun(self):
        from core import shots
        p = Pipeline(connect())
        pid = p.create_project("t")
        p.set_project_field(pid, "shot_mode", "per_shot")
        p.create_scene(pid, 1, "CẢNH 1")
        plan = copy.deepcopy(ANALYSIS)
        plan["scenes"][0]["shots"] = [shot(), shot()]
        store_scene_analysis(p, pid, plan)
        row = p.conn.execute("SELECT id, idx FROM scenes WHERE project_id=? ORDER BY idx LIMIT 1", (pid,)).fetchone()
        llm_io.update_scene(p, pid, row["idx"], {"image_prompt": "chỉnh tay"})
        plan["scenes"][0]["shots"][0]["image_prompt"] = "Director viết lại"
        store_scene_analysis(p, pid, plan)
        first = json.loads(p.conn.execute("SELECT data FROM scenes WHERE project_id=? ORDER BY idx LIMIT 1", (pid,)).fetchone()["data"])
        self.assertEqual(first["image_prompt"], "chỉnh tay")
        self.assertIn("chỉnh tay", prompts.locked_block(p, pid))
        self.assertTrue(shots.active(p, pid))


if __name__ == "__main__":
    import unittest.mock  # noqa: F401
    unittest.main()
