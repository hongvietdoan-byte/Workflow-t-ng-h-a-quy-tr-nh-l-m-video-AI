"""Character Lock written as a list instead of one text (Director #27, 12/10/2026: `characters[8].lock` refused twice -> 3 paid
calls lost). Code joins the list itself instead of sending the answer back to Claude; a lock that cannot be read stays refused."""
import unittest

from core import llm_io


def _answer(lock):
    return {"characters": [{"name": "KELLY", "description": "x", "lock": lock}],
            "scenes": [{"idx": 1, "location": "l", "time": "t", "mood": "m", "lighting": "li", "shot": "s",
                        "image_prompt": "p", "characters": ["KELLY"]}]}


class LockNormalizeTests(unittest.TestCase):
    def test_list_values_are_joined(self):
        obj = llm_io.validate_scene_analysis(_answer({"must_keep": ["tóc ngắn đen", "áo vàng"], "may_change": "tư thế",
                                                      "forbidden": ["đổi màu áo"]}))
        lock = obj["characters"][0]["lock"]
        self.assertEqual(lock["must_keep"], "tóc ngắn đen; áo vàng")
        self.assertEqual(lock["forbidden"], "đổi màu áo")
        self.assertEqual(lock["may_change"], "tư thế")

    def test_null_value_becomes_empty_text(self):
        obj = llm_io.validate_scene_analysis(_answer({"must_keep": "a", "may_change": None, "forbidden": "b"}))
        self.assertEqual(obj["characters"][0]["lock"]["may_change"], "")

    def test_string_lock_unchanged(self):
        lock = {"must_keep": "a", "may_change": "b", "forbidden": "c"}
        obj = llm_io.validate_scene_analysis(_answer(dict(lock)))
        self.assertEqual(obj["characters"][0]["lock"], lock)

    def test_unknown_key_or_nested_object_still_refused(self):
        with self.assertRaises(llm_io.SchemaError):
            llm_io.validate_scene_analysis(_answer({"must_keep": "a", "note": "x"}))
        with self.assertRaises(llm_io.SchemaError):
            llm_io.validate_scene_analysis(_answer({"must_keep": {"hair": "black"}}))
        with self.assertRaises(llm_io.SchemaError):
            llm_io.validate_scene_analysis(_answer("tóc đen"))


if __name__ == "__main__":
    unittest.main()


class LockFromPicturesTests(unittest.TestCase):
    def test_character_lock_task_cleans_list_in_place(self):
        from core import claude_tasks
        obj = {"must_keep": ["a", "b"], "may_change": None, "forbidden": "c"}
        claude_tasks._check_lock(obj)
        self.assertEqual(obj, {"must_keep": "a; b", "may_change": "", "forbidden": "c"})


class EmptyLockNotStoredTests(unittest.TestCase):
    def test_all_null_lock_is_not_stored(self):
        from core import script_parser
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("t", aspect="9:16", genre="SHORT_FORM", model_priority="balanced")
        script_parser.import_scenes(p, pid, script_parser.split_scenes(["CẢNH 1 - NGÀY, LÀNG", "KELLY: Đi thôi."]))
        idx = p.conn.execute("SELECT idx FROM scenes WHERE project_id=?", (pid,)).fetchone()["idx"]
        ans = _answer({"must_keep": None, "may_change": None, "forbidden": None})
        ans["scenes"][0]["idx"] = idx
        llm_io.store_scene_analysis(p, pid, ans)
        row = p.conn.execute("SELECT lock_rules FROM characters WHERE project_id=? AND name='KELLY'", (pid,)).fetchone()
        self.assertFalse(row["lock_rules"])             # empty lock = no lock: a later Director run may still fill it
        ans["characters"][0]["lock"] = {"must_keep": ["tóc đen"], "may_change": "", "forbidden": ""}
        llm_io.store_scene_analysis(p, pid, ans)
        row = p.conn.execute("SELECT lock_rules FROM characters WHERE project_id=? AND name='KELLY'", (pid,)).fetchone()
        self.assertIn("tóc đen", row["lock_rules"])
