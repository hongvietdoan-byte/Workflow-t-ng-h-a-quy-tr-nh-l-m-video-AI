"""KE_HOACH_DUYET_BAN_THO P0–P1: one reader of the Director's intent, and the rough cut measured against it (code only, 0 USD)."""
import json
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from core import cost, delivery, director_two_pass, features, ffmpeg_studio, llm_runner, project_budget, rough_cut
from tests.test_v2 import Base

FF = ffmpeg_studio.find_ffmpeg()


def make_video(path, seconds, w=180, h=320, sound="sine=frequency=440"):
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=0x3060C0:s={w}x{h}:d={seconds}", "-f", "lavfi", "-i",
                    f"{sound}:duration={seconds}", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", path], check=True)


def intent(scenes):
    return {"intent": {"scenes": scenes}}


class IntentReaderTests(Base):
    def test_two_pass_intent_is_read_from_the_raw_without_a_copy_in_scenes(self):
        director_two_pass._save_raw(self.p, self.pid, intent([{"idx": 1, "emotional_intent": "lo", "target_s": 5, "peak": 4, "focus": "KELLY",
                                                              "editor_notes": "giữ lâu", "dp_notes": "x", "sound": {"music": "keep"}}]))
        got = director_two_pass.intent_for(self.p, self.pid, 1)
        self.assertEqual((got["target_s"], got["peak"], got["focus"], got["editor_notes"]), (5, 4, "KELLY", "giữ lâu"))
        every = director_two_pass.intent_all(self.p, self.pid)
        self.assertEqual(every["source"], "director_intent_raw")
        self.assertFalse(every["stale"])
        for r in self.p.conn.execute("SELECT data FROM scenes WHERE project_id=?", (self.pid,)):     # the plan's one-source rule: no copy
            self.assertNotIn("peak", json.loads(r["data"] or "{}"))

    def test_the_fingerprint_follows_the_intent_and_a_replaced_plan_is_stale(self):
        director_two_pass._save_raw(self.p, self.pid, intent([{"idx": 1, "emotional_intent": "lo", "target_s": 5}]))
        a = director_two_pass.intent_all(self.p, self.pid)["fingerprint"]
        director_two_pass._save_raw(self.p, self.pid, intent([{"idx": 1, "emotional_intent": "lo", "target_s": 9}]))
        self.assertNotEqual(a, director_two_pass.intent_all(self.p, self.pid)["fingerprint"])
        director_two_pass.forget(self.p, self.pid)
        every = director_two_pass.intent_all(self.p, self.pid)
        self.assertTrue(every["stale"])
        self.assertNotIn(1, every["scenes"] if every["source"] == "director_intent_raw" else {})

    def test_a_single_call_project_says_it_has_no_tier_a_intent(self):
        every = director_two_pass.intent_all(self.p, self.pid)
        self.assertIn(every["source"], ("story_scene", "none"))
        self.assertEqual(director_two_pass.intent_for(self.p, self.pid, 99), {})


class StageConfigTests(unittest.TestCase):
    def test_the_editor_stage_has_its_own_ceiling_and_a_budget_line(self):
        self.assertEqual(llm_runner.stage_settings("editor")["max_tokens"], 12000)
        self.assertEqual(project_budget.claude_stage("editor"), "claude_qc")
        self.assertIn("editor", cost.LLM_STAGE_TOKENS)

    def test_the_flag_is_off_and_unverified(self):
        self.assertFalse(features.FEATURES["rough_cut_review"]["verified"])
        self.assertFalse(features.on("rough_cut_review"))


class RoughCutTests(Base):
    def render(self, durations, scenes, seconds=None):
        """A `final` output with a timeline of shots (one scene row each) and a real video of that length."""
        data = tempfile.mkdtemp()
        out = os.path.join(delivery.output_dir(data, self.pid), "FINAL_VIDEO.mp4")
        make_video(out, seconds or sum(durations))
        rows = list(self.p.conn.execute("SELECT id, idx FROM scenes WHERE project_id=? ORDER BY idx", (self.pid,)))
        timeline = []
        for r, d, sc in zip(rows, durations, scenes):
            self.p.conn.execute("UPDATE scenes SET data=json_set(COALESCE(data,'{}'),'$.story_scene',?) WHERE id=?", (sc, r["id"]))
            timeline.append({"idx": r["idx"], "scene_id": r["id"], "seconds": float(d)})
        self.p.conn.commit()
        delivery.record(self.p, self.pid, "final", out, None, {"timeline": timeline, "transition": "cut", "fade": 0,
                                                              "loudness": {"lufs": -14}})
        return data

    def test_clock_scene_seconds_and_flags_against_the_intent(self):
        director_two_pass._save_raw(self.p, self.pid, intent([
            {"idx": 1, "emotional_intent": "a", "target_s": 3, "peak": 2},
            {"idx": 2, "emotional_intent": "b", "target_s": 10, "peak": 5}]))        # target 10 s, got 3 s; peak 5 with a 1.5 s longest shot
        data = self.render([3, 1.5, 1.5], [1, 2, 2])
        res = rough_cut.build(self.p, self.pid, data)
        self.assertEqual([(s["start"], s["end"]) for s in res["shots"]], [(0.0, 3.0), (3.0, 4.5), (4.5, 6.0)])
        kinds = {(f["kind"], f.get("scene")) for f in res["flags"]}
        self.assertIn(("off_target", 2), kinds)
        self.assertIn(("peak_no_hold", 2), kinds)
        self.assertNotIn(("off_target", 1), kinds)
        self.assertEqual(res["source"], "director_intent_raw")

    def test_sheets_cover_every_cut_and_never_exceed_twelve_images(self):
        data = self.render([2, 2, 2], [1, 2, 3])
        res = rough_cut.build(self.p, self.pid, data)
        self.assertEqual(res["coverage"]["moments_total"], 2)                    # two cuts
        self.assertEqual(res["coverage"]["moments_seen"], 2)
        self.assertTrue(all(os.path.exists(x) for x in res["sheets"]))
        many = [{"label": f"m{i}", "times": [0.5], "at": i} for i in range(rough_cut.MAX_SHEETS * rough_cut.PAIRS_PER_SHEET + 5)]
        out = rough_cut.sheets(res["path"], many, os.path.join(data, "many"))
        self.assertEqual(len(out["paths"]), rough_cut.MAX_SHEETS)
        self.assertEqual(len(out["dropped"]), 5)                                 # counted and named, not dropped quietly
        self.assertEqual(out["seen"] + len(out["dropped"]), out["total"])

    def test_same_render_and_intent_come_back_from_the_saved_result(self):
        data = self.render([2, 2, 2], [1, 2, 3])
        first = rough_cut.build(self.p, self.pid, data)
        with mock.patch.object(rough_cut, "sheets", side_effect=AssertionError("ffmpeg ran again")):
            self.assertEqual(rough_cut.build(self.p, self.pid, data)["fingerprint"], first["fingerprint"])
        director_two_pass._save_raw(self.p, self.pid, intent([{"idx": 1, "emotional_intent": "x", "target_s": 2}]))
        self.assertNotEqual(rough_cut.fingerprint(self.p.conn.execute("SELECT * FROM outputs ORDER BY id DESC").fetchone(),
                                                   director_two_pass.intent_all(self.p, self.pid)), first["fingerprint"])

    def test_no_render_is_said_not_hidden(self):
        with self.assertRaises(ValueError):
            rough_cut.build(self.p, self.pid, tempfile.mkdtemp())

    def test_lines_say_what_was_seen(self):
        data = self.render([2, 2, 2], [1, 2, 3])
        text = "\n".join(rough_cut.lines(rough_cut.build(self.p, self.pid, data)))
        self.assertIn("thấy 2/2 khoảnh khắc", text)


if __name__ == "__main__":
    unittest.main()
