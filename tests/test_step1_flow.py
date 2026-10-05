import json
import os
import tempfile
import unittest

from streamlit.testing.v1 import AppTest

from core import autopilot, llm_runner, script_parser
from core.db import connect
from core.music import MockAudioProvider
from core.pipeline import Pipeline
from core.providers import MockImageProvider, MockVideoProvider
from core.runner import ImageRunner, VideoRunner
from tests.test_autopilot import SAMPLE, fake_render

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")


def split_only():
    """A project whose script was only split into scenes: no Director run, no Character Bible yet."""
    tmp = tempfile.mkdtemp()
    db, data = os.path.join(tmp, "m.sqlite"), os.path.join(tmp, "projects")
    p = Pipeline(connect(db))
    pid = p.create_project("flow", "human_qc", 0.85, 2)
    paragraphs = script_parser.read_docx_paragraphs(SAMPLE)
    script_parser.import_scenes(p, pid, script_parser.split_scenes(paragraphs), full_text="\n".join(paragraphs))
    return tmp, db, data, p, pid


class AutomaticFromSplitScenesTests(unittest.TestCase):
    def test_automatic_mode_runs_the_director_itself_when_only_the_split_is_approved(self):
        tmp, db, data, p, pid = split_only()
        ctx = autopilot.Context(data, ImageRunner(p, MockImageProvider(), data), VideoRunner(p, MockVideoProvider(polls_to_finish=1), data),
                                llm_runner.MockLlm(), MockAudioProvider(), fake_render)
        self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM characters").fetchone()[0], 0)
        self.assertEqual(autopilot.problems(p, pid, ctx), [])                # a missing Character Bible is no longer a blocker
        autopilot.start(p, pid)
        self.assertEqual(autopilot.run_until_done(p, pid, ctx), autopilot.WAITING)     # v2: stops for the Character Bible review
        self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 0)
        autopilot.resume(p, pid)                                                     # the person approved it
        self.assertEqual(autopilot.run_until_done(p, pid, ctx), autopilot.WAITING)     # W1: stops at the storyboard before video
        autopilot.resume(p, pid)
        self.assertEqual(autopilot.run_until_done(p, pid, ctx), autopilot.DONE)
        self.assertGreater(p.conn.execute("SELECT COUNT(*) FROM characters WHERE locked=1").fetchone()[0], 0)
        self.assertTrue(any("Director" in e["msg"] for e in autopilot.status(p, pid)["log"]))

    def test_scenes_the_director_could_not_fill_stop_the_run_without_asking_claude_again(self):
        tmp, db, data, p, pid = split_only()

        class Lazy:
            calls = 0
            inner = llm_runner.MockLlm()

            def complete(self, prompt, images=()):
                Lazy.calls += 1
                reply = self.inner.complete(prompt, images)
                if "Kịch bản đã tách cảnh" not in prompt:
                    return reply
                data = llm_runner.extract_json(reply.text)
                data["scenes"] = [x for x in data["scenes"] if x["idx"] != 50]     # forgets the hand-made scene
                return llm_runner.LlmReply(json.dumps(data, ensure_ascii=False), reply.input_tokens, reply.output_tokens)

        ctx = autopilot.Context(data, ImageRunner(p, MockImageProvider(), data), VideoRunner(p, MockVideoProvider(), data), Lazy(),
                                MockAudioProvider(), fake_render)
        p.create_scene(pid, 50, "CẢNH 50")                                    # added by hand after the split; Director will not know it
        p.conn.execute("UPDATE scenes SET data='{}' WHERE project_id=? AND idx=50", (pid,))
        p.conn.commit()
        autopilot.start(p, pid)
        state = autopilot.run_until_done(p, pid, ctx)
        self.assertEqual(state, autopilot.STOPPED)
        self.assertIn("Cảnh chưa có prompt ảnh", autopilot.status(p, pid)["note"])
        calls = Lazy.calls
        autopilot.run_until_done(p, pid, ctx)
        self.assertEqual(Lazy.calls, calls)                                    # no second Director call


class Step1LayoutTests(unittest.TestCase):
    def test_script_comes_first_then_the_choice_between_automatic_and_step_by_step(self):
        tmp, db, data, p, pid = split_only()
        os.environ.update({"PIPELINE_DB": db, "PIPELINE_DATA": data})
        try:
            at = AppTest.from_file(APP, default_timeout=40).run()
            self.assertFalse(at.exception)
            texts = [m.value for m in at.markdown]
            index = lambda needle: next(i for i, t in enumerate(texts) if needle in t)  # noqa: E731
            script, prep, choice = index("1a · 📜 Kịch bản"), index("1b · 🧰 Chuẩn bị"), index("1c · Chọn cách chạy")
            self.assertLess(script, prep)                                       # v2: style/format are set before the Director
            self.assertLess(prep, choice)
            self.assertLess(choice, index('cardtitle">🚀 Tự động hoàn toàn'))     # (the "next thing" band may name it earlier, in plain words)
            self.assertLess(index('cardtitle">🚀 Tự động hoàn toàn'), index("1d · 🎬 Director"))
            # S9 E1.10 (người dùng sau #8): the step-by-step path is one caption line, no card of its own
            self.assertTrue(any("Hoặc lần lượt từng bước" in c.value for c in at.caption))
            self.assertFalse(any("Lần lượt từng bước" in t and "cardtitle" in t for t in texts))
        finally:
            os.environ.pop("PIPELINE_DB", None)
            os.environ.pop("PIPELINE_DATA", None)

    def test_no_choice_is_offered_before_the_script_is_split(self):
        tmp = tempfile.mkdtemp()
        os.environ.update({"PIPELINE_DB": os.path.join(tmp, "m.sqlite"), "PIPELINE_DATA": os.path.join(tmp, "projects")})
        try:
            Pipeline(connect(os.environ["PIPELINE_DB"])).create_project("empty")
            at = AppTest.from_file(APP, default_timeout=40).run()
            self.assertFalse(at.exception)
            self.assertFalse(any("Chọn cách chạy" in m.value for m in at.markdown))
        finally:
            os.environ.pop("PIPELINE_DB", None)
            os.environ.pop("PIPELINE_DATA", None)


class ClassifyTests(unittest.TestCase):
    """S14.21 (Đợt 3): script or idea, decided by code for 0 USD with the same test the Biên kịch trusts (idea_to_script.parse)."""

    def test_a_script_with_scene_headings_is_a_script(self):
        from core import idea_to_script as I
        got = I.classify("CẢNH 1 - ĐÊM, RỪNG\nSương mù.\nLYRA: Đi thôi.\n\nCẢNH 2 - NGÀY, LÀNG\nKAEL: Về rồi.\n\nCẢNH 3 - ĐÊM, LÀNG\nYên lặng.")
        self.assertEqual(got["kind"], "script")
        self.assertEqual(got["scenes"], 3)
        self.assertTrue(any("3 tiêu đề cảnh" in w for w in got["why"]))

    def test_two_lines_without_heading_go_to_the_writer(self):
        from core import idea_to_script as I
        got = I.classify("Kelly và Maxim tranh một thùng thính ở Đảo Quân Sự.\nCuối cùng mở ra thì trống trơn.")
        self.assertEqual(got["kind"], "idea")

    def test_grey_zone_asks_instead_of_guessing(self):
        from core import idea_to_script as I
        talk = "Hai người cãi nhau.\nKELLY: Của tôi!\nMAXIM: Không, của tôi!"
        self.assertEqual(I.classify(talk)["kind"], "unsure")                  # ≥ 2 dialogue lines but no heading
        self.assertEqual(I.classify("Một ý tưởng rất dài. " * 90)["kind"], "unsure")   # > 1500 characters
        self.assertEqual(I.classify("   ")["kind"], "unsure")                 # nothing to read — nothing guessed
        for kind in ("script", "idea", "unsure"):
            self.assertIn(kind, I.CLASSIFY_KINDS)


if __name__ == "__main__":
    unittest.main()
