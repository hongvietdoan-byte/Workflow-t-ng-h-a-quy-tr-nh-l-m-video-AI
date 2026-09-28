"""Reference styles are suggestions to mix (người dùng 2026-09-28, after S0): several styles per project, the Director told it may pick,
mix and depart; the reference numbers only give 💡 hints in the cut's check, never a block."""
import unittest

from core import final_qc, prompts, shots
from core.db import connect
from core.pipeline import Pipeline


class StyleMixTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("mix")

    def test_several_styles_are_kept_in_order_and_one_style_still_reads(self):
        self.p.set_project_field(self.pid, "style_profile", "DRAMA_DOC,SHORT_FILM")
        proj = self.p.project(self.pid)
        self.assertEqual(shots.styles(proj), ["DRAMA_DOC", "SHORT_FILM"])
        self.assertEqual(shots.style(proj), "DRAMA_DOC")
        self.p.set_project_field(self.pid, "style_profile", "INGAME")                    # projects saved before: one style
        self.assertEqual(shots.styles(self.p.project(self.pid)), ["INGAME"])
        self.p.set_project_field(self.pid, "style_profile", None)
        self.assertEqual(shots.styles(self.p.project(self.pid)), [])

    def test_the_director_reads_the_styles_as_suggestions_it_may_mix(self):
        self.p.set_project_field(self.pid, "style_profile", "DRAMA_DOC,SHORT_FILM")
        block = prompts.shot_style_block(self.p.project(self.pid))
        self.assertIn("GỢI Ý, KHÔNG BẮT BUỘC", block)
        self.assertIn("trộn các phong cách", block)
        self.assertIn("## Phong cách tham khảo: DRAMA_DOC", block)
        self.assertIn("## Phong cách tham khảo: SHORT_FILM", block)
        self.assertNotIn("Phong cách dựng của dự án (", block)                         # the old "the project's style" wording

    def test_reference_numbers_are_hints_never_blocks_nor_warnings(self):
        tl = [{"seconds": 3.5}] * 8 + [{"seconds": 5.0}] * 2
        hints = final_qc.style_hints(["DRAMA_DOC"], tl)
        self.assertEqual({h["level"] for h in hints}, {"hint"})
        self.assertTrue(any("trung vị 3.5 s" in h["msg"] for h in hints))
        self.assertEqual(final_qc.style_hints([], tl), [])                              # no style picked: nothing said
        self.assertEqual(final_qc.style_hints(["SHORT_FILM"], tl), [])                   # no numbers for that style yet
        res = {"ok": True, "blocks": 0, "warns": 0, "issues": hints}
        self.assertIn("💡", final_qc.summary(res))


if __name__ == "__main__":
    unittest.main()
