"""Previz 2D, Claude side: one reading per background picture (cached), one call to lay out the script, the layouts and the
storyboard composed, Claude's storyboard review, and Step 2 sending the layout as the first reference."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from PIL import Image, ImageDraw

from core import assets, llm_io, previz
from core.db import connect
from core.llm_runner import LlmError, LlmReply, MockLlm
from core.pipeline import Pipeline
from core.providers import MockImageProvider
from core.runner import ImageRunner


class CountingLlm(MockLlm):
    def __init__(self):
        self.calls = []

    def complete(self, prompt, images=()):
        self.calls.append((prompt.splitlines()[0], len(images)))
        return super().complete(prompt, images)


class PrevizTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.data = os.path.join(self.dir, "projects")
        self.conn = connect(os.path.join(self.dir, "m.sqlite"))
        self.p = Pipeline(self.conn)
        self.pid = self.p.create_project("previz")
        self.loc = assets.create(self.conn, "FF", "location", "Đảo Quân Sự", "", "", None, "x")
        for shade in (90, 120):
            img = Image.new("RGB", (1280, 720), (150, 190, 230))
            ImageDraw.Draw(img).rectangle([0, 300, 1280, 720], fill=(shade, 150, 110))
            path = os.path.join(self.dir, f"bg{shade}.png")
            img.save(path)
            assets.add_image(self.conn, self.loc, f"bg{shade}.png", open(path, "rb").read())
        assets.attach(self.conn, self.pid, self.loc)
        for idx in (1, 2, 3):
            self.p.create_scene(self.pid, idx, f"S{idx}")
        llm_io.store_scene_analysis(self.p, self.pid, {
            "characters": [{"name": "Kelly", "description": "d"}, {"name": "Alok", "description": "d"}],
            "scenes": [dict({"location": "beach", "time": "day", "mood": "m", "lighting": "l", "shot": "medium shot",
                             "image_prompt": f"shot {i}", "sequence": 1, "blocking": "Kelly left, Alok right"}, idx=i,
                            characters=["Kelly", "Alok"] if i < 3 else ["Kelly"], location_asset=self.loc if i < 3 else None)
                       for i in (1, 2, 3)]})

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def scene(self, idx):
        return json.loads(self.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=?", (self.pid, idx)).fetchone()["data"])

    def test_the_script_is_laid_out_with_few_claude_calls_and_a_storyboard(self):
        llm = CountingLlm()
        result = previz.plan_layouts(self.p, self.pid, llm, self.data)
        self.assertEqual(result["laid_out"], [1, 2])
        self.assertEqual(result["skipped"], [3])                                # no place picture: keeps the old way
        self.assertEqual([c[0] for c in llm.calls].count("# Phân tích ảnh nền (previz 2D)"), 2)   # one per background picture
        self.assertEqual([c[0] for c in llm.calls].count("# Dựng layout từng shot (previz 2D)"), 1)  # one for the whole script
        for idx in (1, 2):
            self.assertTrue(os.path.exists(previz.layout_path(self.data, self.pid, idx)))
            self.assertTrue(os.path.exists(previz.layout_path(self.data, self.pid, idx, board=True)))
            self.assertEqual([x["name"] for x in self.scene(idx)["layout_people"]], ["Kelly", "Alok"])
        self.assertTrue(os.path.exists(result["storyboard"]))
        self.assertEqual(self.scene(1)["blocking"], "Kelly left, Alok right")   # the scene's other data is kept

    def test_a_background_is_read_only_once_across_runs_and_projects(self):
        previz.plan_layouts(self.p, self.pid, MockLlm(), self.data)
        again = CountingLlm()
        previz.plan_layouts(self.p, self.pid, again, self.data)
        self.assertNotIn("# Phân tích ảnh nền (previz 2D)", [c[0] for c in again.calls])

    def test_an_answer_with_an_unknown_background_is_asked_again_then_refused(self):
        class Wrong(MockLlm):
            def complete(self, prompt, images=()):
                if prompt.startswith("# Dựng layout"):
                    return LlmReply(json.dumps({"shots": [{"idx": 1, "background": 999, "redraw": False, "people": []}]}), 1, 1)
                return super().complete(prompt, images)
        with self.assertRaises(LlmError):
            previz.plan_layouts(self.p, self.pid, Wrong(), self.data)
        self.assertTrue(self.conn.execute("SELECT COUNT(*) FROM diag_events WHERE stage='previz'").fetchone()[0])

    def test_claude_reviews_the_storyboard_and_the_answer_is_kept(self):
        previz.plan_layouts(self.p, self.pid, MockLlm(), self.data)
        self.assertEqual(previz.review_storyboard(self.p, self.pid, MockLlm(), self.data), {"ok": True, "issues": []})
        self.assertEqual(previz.last_review(self.data, self.pid)["ok"], True)

    @mock.patch.dict(os.environ, {"FEATURE_LAYOUT_TO_MODEL": "1"})   # mechanism test; off by default until a real test (core/features.py)
    def test_step_2_sends_the_layout_first_and_tells_the_model_to_follow_it(self):
        previz.plan_layouts(self.p, self.pid, MockLlm(), self.data)
        sid = self.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=1", (self.pid,)).fetchone()["id"]
        self.p.create_job(sid, "image_gen")
        provider = MockImageProvider()
        ImageRunner(self.p, provider, self.data).submit_pending(self.pid)
        sent = next(iter(provider.references.values()))
        self.assertEqual(sent[0], previz.layout_path(self.data, self.pid, 1))
        prompt = next(iter(provider.prompts.values()))
        self.assertIn("Image 1 is the LAYOUT", prompt)
        self.assertIn("the red figure is Kelly", prompt)
        self.assertIn("Image 2 is the location Đảo Quân Sự", prompt)

    def test_the_qc_agent_compares_the_picture_with_the_layout_too(self):
        from core import llm_runner
        previz.plan_layouts(self.p, self.pid, MockLlm(), self.data)
        sid = self.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=1", (self.pid,)).fetchone()["id"]
        jid = self.p.create_job(sid, "image_gen")
        folder = os.path.join(self.data, str(self.pid), "images")
        os.makedirs(folder, exist_ok=True)
        Image.new("RGB", (64, 36)).save(os.path.join(folder, f"job_{jid}.png"))
        for state in ("running", "succeeded"):
            self.conn.execute("UPDATE jobs SET state=? WHERE id=?", (state, jid))
        self.conn.commit()

        class Seeing(MockLlm):
            seen = []

            def complete(self, prompt, images=()):
                Seeing.seen = [label for label, _ in images]
                Seeing.prompt = prompt
                return super().complete(prompt, images)
        llm_runner.run_qc(self.p, jid, Seeing(), self.data)
        self.assertEqual(Seeing.seen[1], "Ảnh tham chiếu 1 — layout:")
        self.assertIn("1. layout (LAYOUT", Seeing.prompt)
        self.assertIn("set_match", Seeing.prompt)


if __name__ == "__main__":
    unittest.main()
