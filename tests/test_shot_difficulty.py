"""N2 (người dùng chốt 08/10, 5a.4/5a.6/5a.7): the Director labels each shot easy / complex / unknown with a reason; code cross-checks the
label from fields already in the shot (core/shot_complexity, 0 USD) — an "easy" label on a shot that scores high becomes "unknown",
"complex" is never lowered. N1 reads scenes.data["difficulty"]: easy → straight to the high tier, otherwise a draft first."""
import json
import os
import unittest

from core import llm_io, shot_complexity, shots

ROOT = os.path.join(os.path.dirname(__file__), "..")
NAMES = {"KENTA", "KELLY"}


def _shot(**kw):
    s = {"size": "MS", "role": "action", "duration_s": 3, "image_prompt": "x", "action": "Kenta đứng nhìn ra cửa sổ",
         "characters": ["KENTA"], "camera_move": "static"}
    s.update(kw)
    return s


class ScoreTests(unittest.TestCase):
    def test_a_still_shot_of_one_person_scores_easy(self):
        r = shot_complexity.score({"characters": ["KENTA"], "camera_move": "static", "action": "Kenta đứng nhìn ra cửa sổ"})
        self.assertEqual(r["suggest"], "easy")
        self.assertEqual(r["factors"], [])

    def test_dance_lip_sync_and_two_people_score_complex(self):
        r = shot_complexity.score({"characters": ["KENTA", "KELLY"], "camera_move": "orbit", "lip_sync": True,
                                   "dialogue": [{"speaker": "KENTA", "text": "đi thôi"}], "action": "Hai người nhảy theo nhạc"})
        self.assertEqual(r["suggest"], "complex")
        keys = {f["key"] for f in r["factors"]}
        self.assertTrue({"people", "dance", "lip_sync", "camera_big"} <= keys, keys)

    def test_skill_phase_and_reference_video_count(self):
        r = shot_complexity.score({"characters": ["KENTA"], "skill_phase": "KENTA:cast"}, ref_video=True)
        keys = {f["key"] for f in r["factors"]}
        self.assertIn("skill", keys)
        self.assertIn("ref_video", keys)
        self.assertNotEqual(r["suggest"], "easy")


class ReconcileTests(unittest.TestCase):
    def test_easy_on_a_hard_shot_is_lowered_to_unknown_with_a_note(self):
        out = shot_complexity.reconcile({"difficulty": "easy", "difficulty_why": "một người", "characters": ["KENTA", "KELLY"],
                                         "action": "Kenta và Kelly nhảy đối mặt", "lip_sync": True})
        self.assertEqual(out["difficulty"], "unknown")
        self.assertIn("kiểm chéo", out["difficulty_check"]["note"])

    def test_complex_is_never_lowered_and_easy_stays_easy_on_an_easy_shot(self):
        self.assertEqual(shot_complexity.reconcile({"difficulty": "complex", "characters": ["KENTA"]})["difficulty"], "complex")
        self.assertEqual(shot_complexity.reconcile({"difficulty": "easy", "characters": ["KENTA"], "camera_move": "static",
                                                    "action": "đứng yên"})["difficulty"], "easy")

    def test_missing_or_unknown_spelling_becomes_unknown(self):
        self.assertEqual(shot_complexity.reconcile({})["difficulty"], "unknown")
        self.assertEqual(shot_complexity.clean_label("dễ"), "easy")
        self.assertEqual(shot_complexity.clean_label("phức tạp"), "complex")
        self.assertEqual(shot_complexity.clean_label("very hard???"), "unknown")
        self.assertEqual(shot_complexity.clean_label(None), "unknown")


class SchemaTests(unittest.TestCase):
    def test_shot_with_and_without_difficulty_is_valid_and_stored(self):
        shots.validate([_shot(difficulty="easy", difficulty_why="1 người đứng yên"), _shot()], "s", NAMES)
        d1 = shots.shot_data({"idx": 1}, _shot(difficulty="easy", difficulty_why="1 người đứng yên"), 1)
        self.assertEqual((d1["difficulty"], d1["difficulty_why"]), ("easy", "1 người đứng yên"))
        d2 = shots.shot_data({"idx": 1}, _shot(), 2)
        self.assertEqual(d2["difficulty"], "unknown")

    def test_a_wrong_type_never_refuses_the_answer(self):
        shots.validate([_shot(difficulty=3, difficulty_why=["x"])], "s", NAMES)
        d = shots.shot_data({"idx": 1}, _shot(difficulty=3, difficulty_why=["x"]), 1)
        self.assertEqual(d["difficulty"], "unknown")
        self.assertNotIn("difficulty_why", d)

    def test_shot_data_lowers_an_easy_dance_shot(self):
        d = shots.shot_data({"idx": 1}, _shot(difficulty="easy", characters=["KENTA", "KELLY"], action="Hai người nhảy",
                                              lip_sync=True), 1)
        self.assertEqual(d["difficulty"], "unknown")

    def test_scene_mode_stores_difficulty_in_scene_data(self):
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("t")
        p.conn.execute("INSERT INTO scenes (project_id, idx, title, data) VALUES (?,?,?,?)", (pid, 1, "c1", "{}"))
        p.conn.execute("INSERT INTO scenes (project_id, idx, title, data) VALUES (?,?,?,?)", (pid, 2, "c2", "{}"))
        base = {"location": "a", "time": "day", "mood": "m", "lighting": "l", "shot": "MS", "image_prompt": "x", "characters": ["KENTA"]}
        llm_io.store_scene_analysis(p, pid, {"characters": [{"name": "KENTA", "description": "d"}],
                                             "scenes": [dict(base, idx=1, difficulty="complex", difficulty_why="đánh nhau"),
                                                        dict(base, idx=2)]})
        rows = {r["idx"]: json.loads(r["data"]) for r in p.conn.execute("SELECT idx, data FROM scenes WHERE project_id=?", (pid,))}
        self.assertEqual((rows[1]["difficulty"], rows[1]["difficulty_why"]), ("complex", "đánh nhau"))
        self.assertEqual(rows[2]["difficulty"], "unknown")


class MeasureTests(unittest.TestCase):
    def test_redo_sources_are_split_and_provider_errors_left_out(self):
        import sys
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import measure_redo_by_factor as m
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("t")
        c = p.conn
        c.execute("INSERT INTO scenes (project_id, idx, title, data) VALUES (?,?,?,?)",
                  (pid, 1, "a", json.dumps({"characters": ["A", "B"], "lip_sync": True})))
        c.execute("INSERT INTO scenes (project_id, idx, title, data) VALUES (?,?,?,?)", (pid, 2, "b", json.dumps({"characters": ["A"]})))
        s1, s2 = [r[0] for r in c.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx", (pid,))]
        job = lambda sid, state, reason=None: c.execute(  # noqa: E731
            "INSERT INTO jobs (project_id, scene_id, type, state, retry_reason, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (pid, sid, "video_gen", state, reason, "t", "t")).lastrowid
        j1 = job(s1, "rejected")
        c.execute("INSERT INTO review_log (job_id, reviewer_type, decision, decided_at) VALUES (?,?,?,?)", (j1, "user", "reject", "t"))
        job(s1, "failed")
        job(s1, "cancelled")
        job(s1, "approved", "gửi lại (lỗi nhà cung cấp)")
        job(s2, "approved")
        res = m.measure(c)
        g = res["groups"]
        self.assertEqual((g["tất cả"]["nguoi"], g["tất cả"]["ncc"], g["tất cả"]["shots"]), (1, 1, 2))
        self.assertEqual(g["yếu tố: khớp môi"]["r"], 1.0)
        self.assertEqual(g["yếu tố: không có"]["r"], 0.0)
        self.assertIn("| tất cả | 2 |", m.table(g))


class PromptTests(unittest.TestCase):
    def test_the_prompts_ask_for_difficulty(self):
        for rel in (("prompts", "17_director_shots.md"), ("prompts", "20_dp_scene_shots.md"), ("prompts", "01_director_scene_analysis.md")):
            text = open(os.path.join(ROOT, *rel), encoding="utf-8").read()
            self.assertIn("difficulty", text, rel)
            self.assertIn("difficulty_why", text, rel)

    def test_the_shot_bundle_carries_the_field(self):
        from core import prompts
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("t")
        p.set_project_field(pid, "shot_mode", "per_shot")
        self.assertIn('"difficulty"', prompts.shot_style_block(p.project(pid)))


if __name__ == "__main__":
    unittest.main()
