"""S11.1 💡 Ý tưởng thô → kịch bản (core/idea_to_script.py): 4 lượt, mặc định được ghi, code kiểm, tô phần thêm, đưa vào Bước 1 — 0 USD."""
import json
import unittest

from core import assets, idea_to_script as I, llm_runner
from core.db import connect
from core.pipeline import Pipeline

IDEA = "Kelly và Maxim tranh nhau một thùng thính ở Đảo Quân Sự, cuối cùng mở ra thì trống trơn."


class Recorder:
    """Wraps the mock model and keeps every prompt (to check what the Biên kịch was told)."""

    def __init__(self):
        self.inner, self.prompts = llm_runner.MockLlm(), []

    def complete(self, prompt, images=()):
        self.prompts.append(prompt)
        return self.inner.complete(prompt, images)


class IdeaTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("ý tưởng", operating_mode="human_qc")
        for name in ("KELLY", "MAXIM"):
            assets.create(self.p.conn, "FF", "character", name)
        assets.create(self.p.conn, "FF", "location", "Đảo Quân Sự")
        self.m = Recorder()

    def run_all(self, **kw):
        I.start(self.p.conn, self.pid, IDEA, **kw)
        I.questions(self.p.conn, self.pid, self.m)
        I.answer(self.p.conn, self.pid, ["vui", ""])
        I.directions(self.p.conn, self.pid, self.m)
        I.outline(self.p.conn, self.pid, self.m, 1, "nhấn mạnh cú chốt")
        return I.write(self.p.conn, self.pid, self.m)

    def test_four_turns_then_the_script_goes_into_step_one(self):
        st = self.run_all(duration_s=30, cta="Tải Free Fire ngay")
        self.assertEqual([p.split("\n")[0] for p in self.m.prompts], [f"# Biên kịch — Lượt {n}" for n in (1, 2, 3, 4)])
        self.assertEqual(st["answers"][1], {"q": "Có Kenta không?", "a": "không", "defaulted": True})   # a default is said
        self.assertIn("[mặc định]", self.m.prompts[1])
        self.assertIn("Hướng người dùng chọn", self.m.prompts[2])
        self.assertIn("Dàn ý đã duyệt", self.m.prompts[3])
        self.assertIn("Đảo Quân Sự", self.m.prompts[0])                       # the library is in the prompt
        self.assertEqual(st["script_checks"]["scenes"], 2)
        self.assertIn('CTA "Tải Free Fire ngay" chưa có ở cảnh cuối', st["script_checks"]["problems"])
        with self.assertRaises(I.IdeaError):
            I.use_script(self.p, self.pid)                                     # a blocking check stops it
        I.edit(self.p.conn, self.pid, st["script"] + "\nKELLY: Tải Free Fire ngay!")
        self.assertEqual(I.use_script(self.p, self.pid), 2)
        rows = self.p.conn.execute("SELECT data FROM scenes WHERE project_id=? ORDER BY idx", (self.pid,)).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertIn("KELLY", json.loads(rows[0][0])["text"])

    def test_trend_off_puts_no_trend_in_the_prompt_and_on_says_there_is_none_yet(self):
        self.run_all(trend="off")
        self.assertNotIn("## Xu hướng dùng được", "".join(self.m.prompts))
        self.m.prompts.clear()
        I.start(self.p.conn, self.pid, IDEA, trend="suggest")
        I.questions(self.p.conn, self.pid, self.m)
        self.assertIn("Chưa có thẻ trend nào được duyệt", self.m.prompts[0])

    def test_outline_checks_length_hook_and_dialogue_per_beat(self):
        beats = [{"name": "hook", "start": 0, "end": 5, "dialogue": [{"speaker": "K", "line": " ".join(["chữ"] * 20)}]},
                 {"name": "climax", "start": 5, "end": 20}]
        got = " | ".join(c["text"] for c in I.check_outline(beats, 30))
        self.assertIn("hook dài 5", got)
        self.assertIn("thiếu nhịp kết", got)
        self.assertIn("tổng 20 s", got)
        self.assertIn("20 âm tiết", got)                                      # 20 / 2.86 ≈ 7 s > 5 s

    def test_script_checks_new_people_places_and_age(self):
        script = "CẢNH 1 - ĐÊM, NGÔI ĐỀN BỎ HOANG\nMột cậu bé 12 tuổi chạy qua.\nLUNA: Đi thôi!"
        c = I.check_script(self.p.conn, self.pid, script, {"duration_s": 15})
        self.assertIn("nhân vật mới — cần ảnh: LUNA", c["flags"])
        self.assertTrue(any("NGÔI ĐỀN BỎ HOANG" in f for f in c["flags"]))
        self.assertIn("có số tuổi dưới 18 — bỏ đi (luật cứng)", c["problems"])
        self.assertFalse(I.check_script(self.p.conn, self.pid, "Chỉ là một đoạn văn không có cảnh.", {"duration_s": 15})["ok"])

    def test_what_the_writer_added_is_marked(self):
        lines = I.marked_lines(IDEA, "CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\nKELLY: Của tôi!\nLUNA: Chào!")
        self.assertFalse(lines[0]["new"])                                     # the place was in the idea
        self.assertTrue(lines[1]["new"])                                      # a new line of dialogue
        self.assertEqual(lines[1]["new_words"], [])                           # Kelly was named in the idea
        self.assertEqual(lines[2]["new_words"], ["LUNA"])
        self.assertTrue(I.marked_lines(IDEA, "KELLY: Ủa?")[0]["new"])            # "ủa" is not a word of the idea ("Quân" ≠ "ủa")

    def test_the_run_has_a_hard_cap_and_bad_inputs_are_refused(self):
        with self.assertRaises(I.IdeaError):
            I.start(self.p.conn, self.pid, "ngắn")
        I.start(self.p.conn, self.pid, IDEA)
        st = I.get_state(self.p.conn, self.pid)
        st["spent"] = I.RUN_CAP_USD
        I.save_state(self.p.conn, self.pid, st)
        with self.assertRaisesRegex(I.IdeaError, "trần"):
            I.questions(self.p.conn, self.pid, self.m)

    def test_the_project_budget_counts_the_writer_with_the_director(self):
        from core import project_budget
        self.assertEqual(project_budget.claude_stage("screenwriter"), "claude_director")


if __name__ == "__main__":
    unittest.main()
