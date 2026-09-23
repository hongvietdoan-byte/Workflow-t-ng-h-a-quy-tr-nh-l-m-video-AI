import json
import unittest

from core import autopilot, dialogue, prompts
from tests.test_autopilot import Setup

LONG = " ".join(["lời"] * 39)          # 39 syllables -> 39/3.5 + 0.5 = 11.6 s
TOO_LONG = " ".join(["lời"] * 70)      # 20.5 s: longer than any clip the models can make


def set_text(p, pid, idx, text):
    row = p.conn.execute("SELECT id, data FROM scenes WHERE project_id=? AND idx=?", (pid, idx)).fetchone()
    data = json.loads(row["data"] or "{}")
    data["text"] = text
    data.pop("dialogue", None)             # the script text is the source here (update_scene re-derives it the same way)
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), row["id"]))
    p.conn.commit()
    return row["id"]


class ExtractTests(unittest.TestCase):
    def test_only_speaker_lines_are_taken_and_quotes_are_stripped(self):
        text = ('Sương mù phủ kín khu rừng. Ánh trăng xanh.\nLYRA (25 tuổi): "Có thứ gì đó đang theo chúng ta."\n'
                "Ghi chú: cảnh này quay đêm\nKAEL: Ở yên sau lưng ta.")
        rows = dialogue.lines(text)
        self.assertEqual(rows, [("LYRA", "Có thứ gì đó đang theo chúng ta."), ("KAEL", "Ở yên sau lưng ta.")])
        self.assertEqual(dialogue.syllables("Ở yên sau lưng ta."), 5)

    def test_no_dialogue_means_no_time_needed(self):
        self.assertEqual(dialogue.needed_seconds([]), 0.0)
        self.assertEqual(dialogue.lines("Chỉ có mô tả cảnh, không có ai nói."), [])


class CheckTests(Setup):
    def test_statuses_follow_the_planned_duration_and_the_model_limit(self):
        self.build()
        p, pid = self.p, self.pid
        set_text(p, pid, 1, "LYRA: " + LONG)
        set_text(p, pid, 2, "KAEL: " + TOO_LONG)
        by_idx = {e["idx"]: e for e in dialogue.check(p, pid)}
        self.assertEqual(by_idx[1]["status"], "extend")
        self.assertEqual(by_idx[1]["target"], 12)
        self.assertEqual(by_idx[2]["status"], "split")
        self.assertEqual(by_idx[2]["max"], 15)
        short = [e for e in by_idx.values() if e["status"] == "ok"]
        self.assertTrue(all(e["needed"] <= e["planned"] for e in short))

    def test_extend_raises_only_the_clips_that_can_be_lengthened(self):
        ctx = self.build()
        p, pid = self.p, self.pid
        set_text(p, pid, 1, "LYRA: " + LONG)
        set_text(p, pid, 2, "KAEL: " + TOO_LONG)
        # give every scene an approved motion prompt so there is a duration to change
        for r in p.conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall():
            p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, duration_sec, state) VALUES (?,?,?,?)",
                           (r["id"], "push in", 5, "approved"))
        p.conn.commit()
        entries = dialogue.check(p, pid)
        self.assertEqual(dialogue.extend(p, entries), 1)
        after = {e["idx"]: e for e in dialogue.check(p, pid)}
        self.assertEqual(after[1]["planned"], 12.0)
        self.assertIn(after[1]["status"], ("ok", "tight"))                  # now fits (11.6 s in a 12 s clip)
        self.assertEqual(after[2]["status"], "split")                      # cannot be fixed by lengthening


class MotionBundleTests(Setup):
    def test_claude_is_told_the_minimum_length_for_scenes_with_dialogue(self):
        self.build()
        from core import llm_runner
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        set_text(self.p, self.pid, 1, "LYRA: " + LONG)
        for r in self.p.conn.execute("SELECT id FROM scenes WHERE project_id=?", (self.pid,)).fetchall():
            self.p.create_job(r["id"], "image_gen")
            job = self.p.conn.execute("SELECT MAX(id) FROM jobs").fetchone()[0]
            self.p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (job,))
        self.p.conn.commit()
        bundle = prompts.build_motion_bundle(self.p, self.pid)
        self.assertIn('"dialogue_min_sec": 11.6', bundle)


class AutopilotGateTests(Setup):
    def test_sound_on_lengthens_short_clips_and_stops_for_dialogue_that_cannot_fit(self):
        ctx = self.build()
        p, pid = self.p, self.pid
        p.set_video_audio(pid, True)
        set_text(p, pid, 1, "LYRA: " + LONG)
        autopilot.start(p, pid)
        self.assertEqual(autopilot.run_until_done(p, pid, ctx), autopilot.DONE)
        e = {x["idx"]: x for x in dialogue.check(p, pid)}
        self.assertEqual(e[1]["planned"], 12.0)                             # lengthened before the video was generated
        used = p.conn.execute("SELECT duration_sec FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id"
                              " WHERE s.project_id=? AND s.idx=1", (pid,)).fetchone()[0]
        self.assertEqual(used, 12)

    def test_dialogue_longer_than_any_clip_stops_before_spending_on_video(self):
        ctx = self.build()
        p, pid = self.p, self.pid
        p.set_video_audio(pid, True)
        set_text(p, pid, 2, "KAEL: " + TOO_LONG)
        autopilot.start(p, pid)
        self.assertEqual(autopilot.run_until_done(p, pid, ctx), autopilot.STOPPED)
        self.assertIn("Thoại quá dài", autopilot.status(p, pid)["note"])
        self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM jobs WHERE type='video_gen'").fetchone()[0], 0)

    def test_sound_off_only_reports(self):
        ctx = self.build()
        p, pid = self.p, self.pid
        set_text(p, pid, 2, "KAEL: " + TOO_LONG)
        autopilot.start(p, pid)
        self.assertEqual(autopilot.run_until_done(p, pid, ctx), autopilot.DONE)     # voiced later, so the run goes on
        self.assertTrue(p.conn.execute("SELECT 1 FROM diag_events WHERE code='dialogue_length'").fetchone())


if __name__ == "__main__":
    unittest.main()
