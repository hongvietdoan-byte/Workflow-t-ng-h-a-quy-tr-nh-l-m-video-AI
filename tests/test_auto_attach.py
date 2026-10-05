"""The library resources a script names are attached before the Director runs (người dùng chốt 2026-09-27) — stricter than the Step 1
suggestions because nobody confirms. Dry-run on a copy of the real database (#6 script) found two traps these tests keep closed:
"Nỏ" (a weapon) matched the word "nó" once accents were folded, and a "kenta" prop shared the name of the character KENTA."""
import unittest
from unittest import mock

from core import assets
from core.db import connect
from core.pipeline import Pipeline

SCRIPT = "Cảnh 1 — Đảo Quân Sự, đêm.\nKELLY: Nó đâu rồi?\nKENTA nhìn về phía Kelly.\nMAXIM cười."


class AutoAttachTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.conn = self.p.conn
        self.pid = self.p.create_project("thu", game="FF")
        self.conn.execute("UPDATE projects SET script_text=? WHERE id=?", (SCRIPT, self.pid))
        self.conn.commit()
        make = lambda kind, name, aliases="": assets.create(self.conn, "FF", kind, name, aliases=aliases)  # noqa: E731
        self.kelly, self.kenta, self.maxim = make("character", "KELLY"), make("character", "KENTA"), make("character", "MAXIM")
        self.island = make("location", "Đảo Quân Sự")
        self.bow = make("weapon", "Nỏ")                              # "nó" in the script is not this
        self.prop = make("prop", "kenta")                           # shares the character's name

    def attached(self):
        return {a["id"] for a in assets.project_assets(self.conn, self.pid)}

    def test_the_named_resources_are_attached_with_their_accents(self):
        r = assets.auto_attach(self.conn, self.pid)
        self.assertEqual(self.attached(), {self.kelly, self.kenta, self.maxim, self.island})
        self.assertEqual(r["ambiguous"], [])
        self.assertNotIn(self.bow, self.attached())
        self.assertNotIn(self.prop, self.attached())

    def test_a_removed_resource_is_not_put_back(self):
        assets.auto_attach(self.conn, self.pid)
        assets.detach(self.conn, self.pid, self.maxim)
        assets.auto_attach(self.conn, self.pid)
        self.assertNotIn(self.maxim, self.attached())

    def test_two_characters_with_one_name_are_left_to_a_person(self):
        other = assets.create(self.conn, "FF", "character", "Kelly thức tỉnh", aliases="Kelly", allow_duplicate=True,
                              duplicate_reason="test: hai nhân vật cố ý chung tên gọi khác")       # S14.43B: refused without it
        r = assets.auto_attach(self.conn, self.pid)
        self.assertEqual(sorted(r["ambiguous"]), ["KELLY", "Kelly thức tỉnh"])
        self.assertNotIn(other, self.attached())
        self.assertNotIn(self.kelly, self.attached())

    def test_the_director_attaches_before_it_is_asked(self):
        from core import llm_runner
        with mock.patch.object(llm_runner, "ask_json", side_effect=llm_runner.LlmError("stop", code="test")):
            with self.assertRaises(llm_runner.LlmError):
                llm_runner.run_director(self.p, self.pid, client=None)
        self.assertIn(self.island, self.attached())
        self.assertTrue(self.conn.execute("SELECT 1 FROM diag_events WHERE code='auto_attach'").fetchone())


if __name__ == "__main__":
    unittest.main()
