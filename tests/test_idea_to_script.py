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

    def test_a_failed_turn_still_counts_what_it_cost(self):
        """S14.4 C1b (04/10): two bad answers were paid but not added to the idea's spend → the cap never closed."""
        class PaidJunk:
            def complete(self, prompt, images=()):
                llm_runner._CAPS.stack[-1]["spent"] += 0.05                    # what the ledger adds for a real call
                return llm_runner.LlmReply("không phải json", 10, 10)

        I.start(self.p.conn, self.pid, IDEA)
        with self.assertRaises(llm_runner.LlmError):
            I.questions(self.p.conn, self.pid, PaidJunk())
        self.assertAlmostEqual(I.get_state(self.p.conn, self.pid)["spent"], 0.10)

    def test_a_turn_fits_under_the_per_idea_cap(self):
        """01/10 S11.2: without its own max_tokens the stage used 32k → turn 1 estimated 0.43 USD > 0.3 cap, every idea refused."""
        model = llm_runner.DEFAULT_MODEL
        mt = llm_runner.stage_settings(I.STAGE)["max_tokens"]
        turn = llm_runner._price(model, "cache_write", 15000) + llm_runner._price(model, "output", mt)
        self.assertLess(turn * llm_runner.TASK_MARGIN + 4 * I.TURN_USD, I.RUN_CAP_USD)   # the last turn's estimate after 4 spent turns

    def test_the_project_budget_counts_the_writer_with_the_director(self):
        from core import project_budget
        self.assertEqual(project_budget.claude_stage("screenwriter"), "claude_director")


def _legacy_build_prompt(conn, pid, state, turn):
    """build_prompt as it was before S14.21 (01/10, the version that recorded the S11.2 replay) — frozen here on purpose."""
    from core.prompts import _read
    inp = state["inputs"]
    lib = I.library(conn, pid)
    parts = [f"# Biên kịch — Lượt {turn}", I._section("CHUNG"), "## Vai của bạn", _read("knowledge", "roles", "screenwriter.md"),
             "## Viết thoại", _read("knowledge", "dialogue_craft.md"), "## Thể loại", _read("knowledge", "genre_guides.md"),
             "## Đầu vào của người dùng",
             f"Ý tưởng: {inp['idea']}\nThời lượng mục tiêu: {inp['duration_s']} s · khung {inp['aspect']} · nền tảng {inp['platform']}"
             + (f"\nGiọng điệu: {inp['tone']}" if inp.get("tone") else "")
             + (f"\nNhân vật người dùng chọn: {', '.join(inp['characters'])}" if inp.get("characters") else "")
             + (f"\nCTA (đúng chữ, ở cảnh cuối): {inp['cta']}" if inp.get("cta") else ""),
             "## Kho FF (ưu tiên dùng)\nNhân vật: " + (", ".join(sorted(set(lib["characters"]))) or "(trống)")
             + "\nNơi: " + (", ".join(sorted(set(lib["places"]))) or "(trống)")]
    tb = I.trend_block(conn, inp.get("trend", "off"))
    if tb:
        parts.append(tb)
    if turn >= 2 and state.get("answers"):
        parts.append("## Trả lời của người dùng (câu ghi [mặc định] = người dùng để trống, dùng đáp án mặc định)\n" + "\n".join(
            f"- {a['q']} → {a['a']}" + (" [mặc định]" if a.get("defaulted") else "") for a in state["answers"]))
    if turn >= 3 and state.get("chosen") is not None:
        d = state["directions"][state["chosen"]]
        parts.append(f"## Hướng người dùng chọn\n{d['title']}: {d['logline']} — hook 3 s: {d['hook_3s']} — chốt: {d['payoff']}"
                     + (f"\nGhi chú của người dùng: {state['choice_note']}" if state.get("choice_note") else ""))
    if turn >= 4 and state.get("beats"):
        parts.append("## Dàn ý đã duyệt\n" + json.dumps(state["beats"], ensure_ascii=False, indent=0))
    parts.append(I._section(f"LƯỢT {turn}"))
    return "\n\n".join(parts)


class WishTests(unittest.TestCase):
    """S14.21 (Đợt 3, C3): the free "nói thêm" box. An empty wish must leave the prompt byte-identical (the S11.2 replay keys on
    sha256(prompt) — a changed prompt = a replay miss = the 0,438 USD already paid lost)."""

    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("ý tưởng", operating_mode="human_qc")
        for name in ("KELLY", "MAXIM"):
            assets.create(self.p.conn, "FF", "character", name)
        assets.create(self.p.conn, "FF", "location", "Đảo Quân Sự")
        self.m = Recorder()

    def run_all(self, wishes=None):
        wishes = wishes or {}
        I.start(self.p.conn, self.pid, IDEA, cta="Tải Free Fire ngay")
        I.questions(self.p.conn, self.pid, self.m, wish=wishes.get(1, ""))
        I.answer(self.p.conn, self.pid, ["vui", ""])
        I.directions(self.p.conn, self.pid, self.m, wish=wishes.get(2, ""))
        I.outline(self.p.conn, self.pid, self.m, 1, "nhấn mạnh cú chốt", wish=wishes.get(3, ""))
        return I.write(self.p.conn, self.pid, self.m, wish=wishes.get(4, ""))

    def test_empty_wish_keeps_every_turn_prompt_byte_identical(self):
        self.run_all()
        st = I.get_state(self.p.conn, self.pid)
        self.assertNotIn("wishes", st)                                        # nothing stored when nothing was said
        for turn in (1, 2, 3, 4):
            old = _legacy_build_prompt(self.p.conn, self.pid, st, turn)
            self.assertEqual(I.build_prompt(self.p.conn, self.pid, st, turn), old)
            self.assertEqual(I.build_prompt(self.p.conn, self.pid, st, turn, wish=""), old)
            self.assertEqual(I.build_prompt(self.p.conn, self.pid, st, turn, wish="   \n"), old)
            self.assertEqual(I.build_prompt(self.p.conn, self.pid, dict(st, wishes={}), turn), old)
        self.assertNotIn("Yêu cầu thêm", "".join(self.m.prompts))

    def test_wish_goes_right_before_the_turn_block_and_is_remembered_later(self):
        self.run_all({2: "cho Maxim thắng ở cuối"})
        p2, p4 = self.m.prompts[1], self.m.prompts[3]
        block = "## Yêu cầu thêm của người dùng (ưu tiên làm theo)"
        self.assertIn(block, p2)
        self.assertIn("cho Maxim thắng ở cuối", p2)
        self.assertLess(p2.index("## Trả lời của người dùng"), p2.index(block))   # after what the turn reads …
        self.assertLess(p2.index(block), p2.index("# Việc lần này: 3 HƯỚNG"))      # … right before the turn's own job
        self.assertIn("không phá ràng buộc cứng", p2)                              # the rule from prompts/23 comes with the wish
        self.assertNotIn(block, self.m.prompts[0])                                 # turn 1 was before the wish
        self.assertIn("cho Maxim thắng ở cuối", p4)                                # turn 4 still remembers turn 2
        self.assertEqual(I.get_state(self.p.conn, self.pid)["wishes"], {"2": "cho Maxim thắng ở cuối"})

    def test_rerunning_a_turn_drops_the_wishes_of_later_turns(self):
        self.run_all({2: "hài hơn", 4: "thêm câu chốt"})
        I.directions(self.p.conn, self.pid, self.m, wish="nghiêm túc")
        self.assertEqual(I.get_state(self.p.conn, self.pid)["wishes"], {"2": "nghiêm túc"})

    def test_ask_again_for_directions_only_when_the_input_changed(self):
        """C8: "↻ Hỏi lại 3 hướng khác" used to resend the very same prompt (0,03 USD for nothing)."""
        self.run_all()
        st = I.get_state(self.p.conn, self.pid)
        self.assertFalse(I.directions_input_changed(st, ["vui", ""], ""))
        self.assertTrue(I.directions_input_changed(st, ["vui", ""], "đổi cảm xúc chính"))
        self.assertTrue(I.directions_input_changed(st, ["buồn", ""], ""))
        self.assertTrue(I.directions_input_changed(st, ["vui", "có"], ""))


if __name__ == "__main__":
    unittest.main()
