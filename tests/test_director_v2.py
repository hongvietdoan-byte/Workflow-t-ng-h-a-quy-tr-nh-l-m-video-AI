"""Director v2 (kế hoạch 2026-09-25): the offline report (H4) and the shot normaliser (H1), on the real Director answers of
"ANH CHỌN AI?" runs 3 and 4 (tests/fixtures) — no Claude call."""
import copy
import json
import os
import unittest

from core import director_report, shot_normalize

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _load(name):
    with open(os.path.join(ROOT, "tests", "fixtures", name), encoding="utf-8") as f:
        return json.load(f)


with open(os.path.join(ROOT, "samples", "anh_chon_ai.txt"), encoding="utf-8") as _f:
    SCRIPT = _f.read()
RUN3, RUN4 = _load("director_anh_chon_ai_run3.json"), _load("director_anh_chon_ai_run4.json")


def _lines(obj):
    return sorted(str(d.get("text")) for sc in obj["scenes"] for s in sc["shots"] for d in s.get("dialogue") or [])


class ReportTests(unittest.TestCase):
    def test_run3_faults_are_measured(self):
        r = director_report.report(RUN3, SCRIPT)
        self.assertEqual(r["shots"], 35)
        self.assertEqual(r["total_s"], 58.5)
        self.assertFalse(r["in_target"])                      # 55–58 s
        self.assertEqual(len(r["short_speech"]), 11)          # the 6,8 s squeeze found by hand
        self.assertEqual(r["dropped"], [])
        self.assertEqual(r["invented"], [])

    def test_run4_faults_are_measured(self):
        r = director_report.report(RUN4, SCRIPT)
        self.assertEqual((r["shots"], r["total_s"], r["in_target"]), (33, 57.3, True))
        self.assertEqual(r["short_speech"], [])
        self.assertEqual(len(r["silent_micro"]), 7)
        self.assertEqual(r["dropped_answered"], 2)            # both dropped lines had a reply right after them
        self.assertEqual(r["paid_s"]["per_shot"], 101.0)      # ~101 s billed for 57 s of film (Kling, 3 s minimum)
        self.assertLess(r["paid_s"]["per_scene"], r["paid_s"]["per_shot"])
        self.assertIn("Tổng lỗi đo được", director_report.text(r))


class NormalizeTests(unittest.TestCase):
    def test_run4_is_fixed_without_touching_a_line(self):
        fixed, changes = shot_normalize.normalize(RUN4, SCRIPT)
        r = director_report.report(fixed, SCRIPT)
        self.assertEqual((r["short_speech"], r["silent_micro"], r["wide_short"]), ([], [], []))
        self.assertEqual(_lines(fixed), _lines(RUN4))          # never adds, drops or rewords dialogue
        self.assertTrue(changes)
        self.assertEqual(fixed["normalized"], changes)
        self.assertLess(r["paid_s"]["per_shot"], 101.0)
        for sec in r["sections"]:                             # no section cut below its own script time to fit the total
            before = next(s for s in director_report.report(RUN4, SCRIPT)["sections"] if s["scene"] == sec["scene"])
            if before["planned"] and before["shots_s"] >= before["planned"]:
                self.assertGreaterEqual(sec["shots_s"] + 1e-6, before["planned"])
        self.assertEqual(RUN4, _load("director_anh_chon_ai_run4.json"))      # the input is not changed (copy)

    def test_run3_spoken_shots_get_time_to_say_their_line(self):
        fixed, _ = shot_normalize.normalize(RUN3, SCRIPT)
        self.assertEqual(director_report.report(fixed, SCRIPT)["short_speech"], [])

    def test_a_second_pass_changes_nothing(self):
        once, _ = shot_normalize.normalize(RUN4, SCRIPT)
        _, again = shot_normalize.normalize(once, SCRIPT)
        self.assertEqual(again, [])

    def test_known_enum_spellings_are_fixed_and_unknown_ones_left_for_claude(self):
        obj = {"scenes": [{"idx": 1, "shots": [
            {"size": "GAME_TPS", "angle": "behind", "role": "action", "duration_s": 2, "action": "a", "image_prompt": "x"},
            {"size": "close_up", "angle": "over_shoulder", "camera_move": "dolly_in", "role": "establishing", "duration_s": 2,
             "action": "b", "image_prompt": "x"},
            {"size": "MS", "angle": "sideways", "role": "action", "duration_s": 2, "action": "c", "image_prompt": "x"}]}]}
        fixed, changes = shot_normalize.normalize(obj)
        a, b, c = fixed["scenes"][0]["shots"]
        self.assertEqual(a["angle"], "high")                   # run 4 was sent back once for this
        self.assertEqual((b["size"], b["angle"], b["camera_move"], b["role"]), ("CU", "ots", "push_in", "setup"))
        self.assertEqual(c["angle"], "sideways")               # not guessed: the validator sends it back
        self.assertEqual(len(changes), 5)

    def test_a_silent_blink_is_merged_into_the_next_shot_of_the_same_person(self):
        obj = {"scenes": [{"idx": 1, "shots": [
            {"size": "MS", "role": "reaction", "duration_s": 0.6, "characters": ["KENTA"], "action": "Kenta quay lại", "image_prompt": "x"},
            {"size": "MS", "role": "dialogue", "duration_s": 2.5, "characters": ["KENTA", "KELLY"], "action": "Kenta nói",
             "image_prompt": "y", "dialogue": [{"speaker": "KENTA", "text": "Kelly, nghe anh giải thích…"}]}]}]}
        fixed, _ = shot_normalize.normalize(obj)
        shots = fixed["scenes"][0]["shots"]
        self.assertEqual(len(shots), 1)
        self.assertEqual(shots[0]["duration_s"], 3.1)
        self.assertTrue(shots[0]["action"].startswith("Kenta quay lại"))


class ValidatorUsesTheNormaliserTests(unittest.TestCase):
    def test_a_fixable_answer_is_not_sent_back(self):
        from core import llm_io, script_parser
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("t")
        p.set_project_field(pid, "shot_mode", "per_shot")
        p.set_project_field(pid, "dialogue_trim", 1)
        rows = [r for r in SCRIPT.splitlines() if r.strip()]
        _, story = script_parser.split_end_card(script_parser.split_scenes(rows))
        script_parser.import_scenes(p, pid, story, full_text=SCRIPT)
        p.conn.execute("UPDATE projects SET script_text=? WHERE id=?", (SCRIPT, pid))
        obj = copy.deepcopy(RUN4)
        shot = obj["scenes"][2]["shots"][1]                    # a spoken shot (never merged away)
        shot["size"], shot["angle"] = "GAME_TPS", "behind"
        llm_io.validate_for_project(p, pid)(obj)               # would raise SchemaError before H1
        self.assertEqual(shot["angle"], "high")
        self.assertTrue(obj["normalized"])


class MinorAgeTests(unittest.TestCase):
    def test_an_age_under_18_never_reaches_the_picture_or_video_model(self):
        """Trial 2A: GPT Image 2.5 refused "KELLY, 17-year-old young woman … in darkness, eyes red" (safety system); without the
        age the same shot passed."""
        from core.runner import no_minor_age
        self.assertEqual(no_minor_age("KELLY, 17-year-old young woman, dark bob"), "KELLY, young woman, dark bob")
        self.assertEqual(no_minor_age("a 17 year old boy"), "a boy")
        self.assertEqual(no_minor_age("KENTA, 38-year-old man"), "KENTA, 38-year-old man")      # adults keep their age


class FlagTests(unittest.TestCase):
    """1.4/1.5 behind flags (off until a real Director run passes)."""

    def setUp(self):
        from core import script_parser
        from core.db import connect
        from core.pipeline import Pipeline
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        self.p.set_project_field(self.pid, "shot_mode", "per_shot")
        _, story = script_parser.split_end_card(script_parser.split_scenes([r for r in SCRIPT.splitlines() if r.strip()]))
        script_parser.import_scenes(self.p, self.pid, story, full_text=SCRIPT)
        self.p.conn.execute("UPDATE projects SET script_text=? WHERE id=?", (SCRIPT, self.pid))
        self.addCleanup(os.environ.pop, "FEATURE_FILM_CREW", None)
        self.addCleanup(os.environ.pop, "FEATURE_CAMERA_SETUPS", None)

    def test_film_crew_swaps_the_scattered_documents_for_the_role_rule_books(self):
        from core import prompts
        off = prompts.build_director_bundle(self.p, self.pid)
        self.assertNotIn("Vai Đạo diễn — bộ nguyên tắc", off)
        os.environ["FEATURE_FILM_CREW"] = "1"
        on = prompts.build_director_bundle(self.p, self.pid)
        self.assertIn("Vai Đạo diễn — bộ nguyên tắc", on)
        self.assertIn("Vai Quay phim (DP)", on)
        self.assertNotIn("Phương pháp đạo diễn — ra quyết định hình ảnh", on)     # folded into the role book

    def test_camera_setups_ask_for_and_keep_the_setup_letter(self):
        from core import prompts, shots
        self.assertNotIn("camera_setup", prompts.duration_block(self.p, self.pid))
        os.environ["FEATURE_CAMERA_SETUPS"] = "1"
        self.assertIn("camera_setup", prompts.duration_block(self.p, self.pid))
        shot = {"size": "MS", "role": "dialogue", "duration_s": 2, "image_prompt": "x", "action": "y", "camera_setup": "b"}
        shots.validate([shot], "s", set())
        self.assertEqual(shots.shot_data({"idx": 2}, shot, 1)["camera_setup"], "B")
        with self.assertRaises(shots.ShotError):
            shots.validate([dict(shot, camera_setup="over the shoulder")], "s", set())


class ReplanOneSceneTests(unittest.TestCase):
    """1.4 "↻ Chia shot lại cảnh này": one call for one script scene, merged, checked as a whole, only that scene and later ones rewritten."""

    def setUp(self):
        from core import llm_io, script_parser
        from core.db import connect
        from core.pipeline import Pipeline
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        self.p.set_project_field(self.pid, "shot_mode", "per_shot")
        self.p.set_project_field(self.pid, "dialogue_trim", 1)
        _, story = script_parser.split_end_card(script_parser.split_scenes([r for r in SCRIPT.splitlines() if r.strip()]))
        script_parser.import_scenes(self.p, self.pid, story, full_text=SCRIPT)
        self.p.conn.execute("UPDATE projects SET script_text=? WHERE id=?", (SCRIPT, self.pid))
        stored = llm_io.store_scene_analysis(self.p, self.pid, copy.deepcopy(RUN4))
        self.p.set_project_field(self.pid, "director_raw", json.dumps(stored, ensure_ascii=False))

    def ids(self, pred):
        return [r["id"] for r in self.p.conn.execute("SELECT id, data FROM scenes WHERE project_id=? ORDER BY idx", (self.pid,))
                if pred(json.loads(r["data"])["story_scene"])]

    def fake(self, scene):
        class Reply:
            def __init__(self, text):
                self.text, self.input_tokens, self.output_tokens = text, 1000, 200

        class Client:
            prompts = []

            def complete(self, prompt, images=()):
                Client.prompts.append(prompt)
                return Reply(json.dumps({"characters": [], "scenes": [scene]}, ensure_ascii=False))
        return Client()

    def test_one_scene_is_replanned_and_earlier_rows_are_untouched(self):
        from core import llm_runner, prompts
        before = self.ids(lambda s: s < 4)
        scene4 = copy.deepcopy(next(s for s in RUN4["scenes"] if s["idx"] == 4))
        scene4["shots"].insert(3, {"size": "MS", "angle": "ots", "role": "dialogue", "duration_s": 2.6, "action": "Kenta cố giải thích",
                                   "image_prompt": "x", "characters": ["KENTA", "KELLY"],
                                   "dialogue": [{"speaker": "KENTA", "text": "Kelly, nghe anh giải thích…"}]})
        client = self.fake(scene4)
        r = llm_runner.run_director_scene(self.p, self.pid, 4, client)
        self.assertEqual(self.ids(lambda s: s < 4), before)                      # earlier scenes keep their rows (and any work)
        texts = [d["text"] for r_ in self.p.conn.execute("SELECT data FROM scenes WHERE project_id=?", (self.pid,))
                 for d in json.loads(r_["data"]).get("dialogue") or []]
        self.assertIn("Kelly, nghe anh giải thích…", texts)
        self.assertGreater(r["rows"], 0)
        self.assertIn(prompts.CACHE_BREAK, client.prompts[0])                    # the shared part is cached
        self.assertIn("CHỈ chia shot lại **Cảnh 4**", client.prompts[0].split(prompts.CACHE_BREAK)[-1])
        order = [json.loads(r_["data"])["story_scene"] for r_ in
                 self.p.conn.execute("SELECT data FROM scenes WHERE project_id=? ORDER BY idx", (self.pid,))]
        self.assertEqual(order, sorted(order))                                    # still in film order

    def test_a_scene_with_pictures_is_not_replanned(self):
        from core import llm_runner, shots
        sid = self.ids(lambda s: s == 5)[0]
        self.p.create_job(sid, "image_gen")
        scene4 = copy.deepcopy(next(s for s in RUN4["scenes"] if s["idx"] == 4))
        with self.assertRaises(shots.ShotError):
            llm_runner.run_director_scene(self.p, self.pid, 4, self.fake(scene4))


class NoFeetInFrameTests(unittest.TestCase):
    def test_a_medium_shot_is_not_marked_down_or_redone_for_feet(self):
        """Trial 2A: QC asked for "feet visible touching the ground" on medium shots (cut above the knees by design)."""
        from core.llm_runner import _no_feet_in_frame
        obj = {"criteria": {"grounding": 0.4, "character": 0.9},
               "issues": ["Kenta's feet are cropped out of frame; keep both feet with ground contact; Kenta's right hand is blurred"]}
        _no_feet_in_frame({"size": "MS"}, obj)
        self.assertEqual(obj["criteria"]["grounding"], 1.0)
        self.assertEqual(obj["issues"], ["Kenta's right hand is blurred"])
        wide = {"criteria": {"grounding": 0.4}, "issues": ["feet float above the ground"]}
        _no_feet_in_frame({"size": "WS"}, wide)                  # a wide shot shows feet: still judged
        self.assertEqual((wide["criteria"]["grounding"], wide["issues"]), (0.4, ["feet float above the ground"]))


if __name__ == "__main__":
    unittest.main()
