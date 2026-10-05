"""S11.1 💡 Ý tưởng thô → kịch bản (core/idea_to_script.py): 4 lượt, mặc định được ghi, code kiểm, tô phần thêm, đưa vào Bước 1 — 0 USD."""
import json
import unittest

from core import assets, idea_to_script as I, llm_runner
from core.db import connect
from core.pipeline import Pipeline

IDEA = "Kelly và Maxim tranh nhau một thùng thính ở Đảo Quân Sự, cuối cùng mở ra thì trống trơn."
ANCHORS = {"characters": ["KELLY", "MAXIM"], "costume": "mặc định", "place": "Đảo Quân Sự",
           "plot": "Kelly và Maxim tranh nhau thùng thính", "ending": "mở thùng ra thì trống trơn", "gameplay_ui": "khong"}


def make_kit(conn):
    """S14.31: what the Biên kịch may use = a place with a 3D model + characters with an approved standard picture and a default outfit."""
    import os
    import tempfile
    pic = os.path.join(tempfile.mkdtemp(), "front.png")
    open(pic, "wb").write(b"x")
    for name, outfit in (("KELLY", "áo cam, quần jean"), ("MAXIM", "áo giáp xanh, không áo choàng")):
        aid = assets.create(conn, "FF", "character", name)
        conn.execute("INSERT INTO asset_images (asset_id, path, label, sort, status, role) VALUES (?,?,?,?,?,?)",
                     (aid, pic, name, 0, "approved", "front_standard"))
        conn.commit()
        assets.set_profile(conn, aid, {"identity": name, "must_keep": outfit}, True)
    lid = assets.create(conn, "FF", "location", "Đảo Quân Sự")
    conn.execute("UPDATE assets SET profile=? WHERE id=?", (json.dumps({"model3d": {"path": pic, "default_spot": "bai_co", "spots": {
        "bai_co": {"at": [0, 0, 0], "label": "bãi cỏ trước nhà kho"}}}}), lid))
    conn.commit()


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
        make_kit(self.p.conn)
        self.m = Recorder()

    def run_all(self, **kw):
        I.start(self.p.conn, self.pid, IDEA, anchors=ANCHORS, **kw)
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
        self.assertEqual(st["script_checks"]["scenes"], 1)                          # S14.35: the mock writes 2 scenes in one place -> the code joins them
        self.assertIn('CTA "Tải Free Fire ngay" chưa có ở cảnh cuối', st["script_checks"]["problems"])
        with self.assertRaises(I.IdeaError):
            I.use_script(self.p, self.pid)                                     # a blocking check stops it
        I.edit(self.p.conn, self.pid, st["script"] + "\nKELLY: Tải Free Fire ngay!")
        self.assertEqual(I.use_script(self.p, self.pid), 1)
        rows = self.p.conn.execute("SELECT data FROM scenes WHERE project_id=? ORDER BY idx", (self.pid,)).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertIn("KELLY", json.loads(rows[0][0])["text"])

    def test_trend_off_puts_no_trend_in_the_prompt_and_on_says_there_is_none_yet(self):
        self.run_all(trend="off")
        self.assertNotIn("## Xu hướng dùng được", "".join(self.m.prompts))
        self.m.prompts.clear()
        I.start(self.p.conn, self.pid, IDEA, trend="suggest", anchors=ANCHORS)
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
        I.start(self.p.conn, self.pid, IDEA, anchors=ANCHORS)
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

        I.start(self.p.conn, self.pid, IDEA, anchors=ANCHORS)
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
    parts = [f"# Biên kịch — Lượt {turn}", I._section("CHUNG"), I.buildable_blocks(conn, pid, inp), "## Vai của bạn", _read("knowledge", "roles", "screenwriter.md"),
             "## Viết thoại", _read("knowledge", "dialogue_craft.md"), "## Thể loại", _read("knowledge", "genre_guides.md"),
             "## Đầu vào của người dùng",
             f"Ý tưởng: {inp['idea']}\nThời lượng mục tiêu: {inp['duration_s']} s · khung {inp['aspect']} · nền tảng {inp['platform']}"
             + (f"\nGiọng điệu: {inp['tone']}" if inp.get("tone") else "")
             + (f"\nNhân vật người dùng chọn: {', '.join(inp['characters'])}" if inp.get("characters") else "")
             + (f"\nCTA (đúng chữ, ở cảnh cuối): {inp['cta']}" if inp.get("cta") else ""),
             ]
    tb = I.trend_block(conn, inp.get("trend", "off"))
    if tb:
        parts.append(tb)
    if turn in I.PATTERN_TURNS:                                          # S14.43 mục 6: kho khuôn hài (gợi ý) at turns 2–3
        parts.append(I.pattern_block())
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
        make_kit(self.p.conn)
        self.m = Recorder()

    def run_all(self, wishes=None):
        wishes = wishes or {}
        I.start(self.p.conn, self.pid, IDEA, cta="Tải Free Fire ngay", anchors=ANCHORS)
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


class ReviewFixesS1421(unittest.TestCase):
    """Rà độc lập S14.21 (05/10): khóa prompt bằng sha256 từng khối; lời "nói thêm" có dấu hai chấm; người chỉ xem không chi tiền."""

    PINNED = {"CHUNG": "6214cbec322cd630", "LƯỢT 1": "83dc981e224c7c48", "LƯỢT 2": "82d2f86afcee5e03",
              "LƯỢT 3": "abda8a0259d2fe91", "LƯỢT 4": "19179b6558f1e72e"}   # = prompts/23 at 43f5162 (the S11.2 replay recording)

    def test_the_prompt_blocks_are_pinned(self):
        import hashlib
        for name, want in self.PINNED.items():
            got = hashlib.sha256(I._section(name).encode("utf-8")).hexdigest()[:16]
            self.assertEqual(got, want, f"khối {name} của prompts/23 đổi → replay S11.2 sẽ miss (đổi có chủ ý thì ghi lại bản ghi)")

    def test_a_wish_with_a_colon_is_still_a_wish(self):
        from unittest import mock
        from dashboard.steps import step1_box
        p = Pipeline(connect())
        pid = p.create_project("ý", operating_mode="human_qc")
        I.start(p.conn, pid, "Kelly và Maxim tranh nhau hộp thính")
        fake = mock.MagicMock()
        fake.session_state = {f"in_mode_{pid}": "idea", f"box_text_{pid}": "Kelly và Maxim tranh nhau hộp thính"}
        with mock.patch.object(step1_box, "st", fake):
            step1_box._take(p, pid, "Lưu ý: cho Maxim thắng")
        self.assertEqual(fake.session_state.get(f"box_wish_{pid}"), "Lưu ý: cho Maxim thắng")
        self.assertEqual(fake.session_state[f"box_text_{pid}"], "Kelly và Maxim tranh nhau hộp thính")   # the idea is kept

    def test_a_viewer_cannot_spend_on_the_screenwriter(self):
        from core import access
        p = Pipeline(connect())
        pid = p.create_project("ý", operating_mode="human_qc")
        I.start(p.conn, pid, "Kelly và Maxim tranh nhau hộp thính")
        p.user = {"email": "la@garena.vn", "role": "member"}
        m = Recorder()
        with self.assertRaises(access.AccessDenied):
            I.questions(p.conn, pid, m, p=p)
        self.assertEqual(m.prompts, [])


class BuildableKitS1431(unittest.TestCase):
    """S14.31 (05/10, người dùng chấm CHƯA QUA): Biên kịch chỉ nhận 'thứ dựng chắc được'; cảnh giao diện/gameplay bị chặn; điểm then chốt
    người dùng chốt phải còn; thiếu điểm then chốt → hỏi lại 0 USD, không gọi Claude."""

    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("ý tưởng", operating_mode="human_qc")
        make_kit(self.p.conn)
        assets.create(self.p.conn, "FF", "location", "Thành Phố")                   # in the Kho but no 3D / plate / pack
        assets.create(self.p.conn, "FF", "character", "LUNA")                       # in the Kho but no standard picture
        self.m = Recorder()

    def test_missing_key_points_are_asked_back_and_claude_is_not_called(self):
        I.start(self.p.conn, self.pid, IDEA)
        with self.assertRaises(I.IdeaError) as cm:
            I.questions(self.p.conn, self.pid, self.m)
        for word in ("nhân vật", "nơi", "diễn biến", "cú chốt", "gameplay"):
            self.assertIn(word, str(cm.exception))
        self.assertEqual(self.m.prompts, [])
        self.assertEqual(I.get_state(self.p.conn, self.pid)["spent"], 0)
        part = dict(ANCHORS, ending="", gameplay_ui="")
        I.start(self.p.conn, self.pid, IDEA, anchors=part)
        self.assertEqual(len(I.missing_anchors(I.get_state(self.p.conn, self.pid)["inputs"]["anchors"])), 2)
        self.assertEqual(I.missing_anchors(ANCHORS), [])

    def test_key_point_outside_the_kit_is_asked_back_too(self):
        I.start(self.p.conn, self.pid, IDEA, anchors=dict(ANCHORS, place="Thành Phố"))
        with self.assertRaisesRegex(I.IdeaError, "Thành Phố"):
            I.questions(self.p.conn, self.pid, self.m)
        I.start(self.p.conn, self.pid, IDEA, anchors=dict(ANCHORS, characters=["KELLY", "LUNA"]))
        with self.assertRaisesRegex(I.IdeaError, "LUNA"):
            I.questions(self.p.conn, self.pid, self.m)
        self.assertEqual(self.m.prompts, [])

    def test_the_writer_reads_the_buildable_kit_not_the_whole_library(self):
        I.start(self.p.conn, self.pid, IDEA, anchors=ANCHORS)
        I.questions(self.p.conn, self.pid, self.m)
        pr = self.m.prompts[0]
        self.assertIn("Đảo Quân Sự", pr)
        self.assertIn("bãi cỏ trước nhà kho", pr)                                  # map + area (spot)
        self.assertIn("không áo choàng", pr)                                       # the default outfit of MAXIM
        self.assertNotIn("Thành Phố", pr)
        self.assertNotIn("LUNA", pr)
        self.assertIn("màn hình điện thoại", pr)                                   # the ban ...
        self.assertIn("thanh máu", pr)                                             # ... and the way around it
        self.assertIn("KHÔNG ĐƯỢC ĐỔI", pr)                                        # the user's key points
        self.assertIn("mở thùng ra thì trống trơn", pr)

    def test_scenes_with_the_game_interface_or_gameplay_are_blocked(self):
        # S14.43 mục 4 + rà: a phone screen alone is no longer blocked, but the FF interface / gameplay ON the screen still is
        bad = "CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\nCận màn hình điện thoại: Kelly bấm nút bắn trong giao diện Free Fire.\nKELLY: Trúng rồi!"
        ok = "CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\nMaxim đứng ở bãi cỏ, thanh máu, tên và số đội hiện trên đầu.\nMAXIM: Đội mình còn bốn người!"
        inputs = {"duration_s": 15, "anchors": dict(ANCHORS, characters=["MAXIM"], plot="", ending="")}
        c = I.check_script(self.p.conn, self.pid, bad, inputs)
        self.assertFalse(c["ok"])
        self.assertEqual(c["blocked_scenes"][0]["scene"], 1)
        self.assertTrue(any("giao diện" in t or "màn hình điện thoại" in t for t in c["problems"]))
        self.assertTrue(I.check_script(self.p.conn, self.pid, ok, inputs)["ok"])
        said_yes = dict(inputs, anchors=dict(ANCHORS, characters=["MAXIM"], plot="", ending="", gameplay_ui="co"))
        c2 = I.check_script(self.p.conn, self.pid, bad, said_yes)
        self.assertEqual(c2["blocked_scenes"], [])                                 # the user chose to have it: said, not blocked
        self.assertTrue(any("giao diện" in t or "màn hình điện thoại" in t for t in c2["flags"]))

    def test_a_place_without_3d_is_blocked_and_a_lost_key_point_is_blocked(self):
        script = "CẢNH 1 - NGÀY, THÀNH PHỐ\nKelly chạy qua phố.\nKELLY: Đi nào!"
        c = I.check_script(self.p.conn, self.pid, script, {"duration_s": 15, "anchors": ANCHORS})
        self.assertTrue(any("THÀNH PHỐ" in t.upper() and "3D" in t for t in c["problems"]))
        self.assertEqual(c["blocked_scenes"][0]["scene"], 1)
        self.assertTrue(any("điểm then chốt" in t for t in c["problems"]))         # no Đảo Quân Sự, no thùng thính, no ending
        good = ("CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\nThùng thính rơi giữa Kelly và Maxim.\nKELLY: Của tôi!\n\n"
                "CẢNH 2 - NGÀY, ĐẢO QUÂN SỰ\nHai người mở thùng ra thì trống trơn.\nMAXIM: Ủa?")
        self.assertTrue(I.check_script(self.p.conn, self.pid, good, {"duration_s": 15, "anchors": ANCHORS})["ok"])
        no_end = "CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\nThùng thính rơi giữa Kelly và Maxim.\nKELLY: Của tôi!\nMAXIM: Còn lâu!"
        got = I.check_script(self.p.conn, self.pid, no_end, {"duration_s": 15, "anchors": ANCHORS})["problems"]
        self.assertTrue(any("cú chốt" in t for t in got))

    def test_turn_estimate_covers_the_real_cost(self):
        self.assertGreaterEqual(I.TURN_USD, 0.045)                                 # real ≈ 0.037 / turn (05/10 record)

    # ---- rà S14.31 (coordinator review) -----------------------------------------------------------------------------------------------
    def _add_place(self, name, path=None, exist=True):
        import os
        import tempfile
        if path is None:
            path = os.path.join(tempfile.mkdtemp(), "m.glb")
            if exist:
                open(path, "wb").write(b"x")
        lid = assets.create(self.p.conn, "FF", "location", name)
        self.p.conn.execute("UPDATE assets SET profile=? WHERE id=?", (json.dumps({"model3d": {"path": path, "default_spot": "a", "spots": {
            "a": {"at": [0, 0, 0], "label": "khu A"}}}}), lid))
        self.p.conn.commit()

    def test_heading_with_only_a_time_is_a_scene_without_a_place(self):
        script = ("CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\nThùng thính rơi giữa Kelly và Maxim.\nKELLY: Của tôi!\n\n"
                  "CẢNH 2 - 5-10s\nHai người mở thùng ra thì trống trơn.")
        c = I.check_script(self.p.conn, self.pid, script, {"duration_s": 15, "anchors": ANCHORS})
        self.assertTrue(any("thiếu nơi" in t for t in c["problems"]))
        self.assertFalse(any("5-10s" in t and "chưa có" in t for t in c["problems"]))

    def test_exclamations_and_everyday_words_are_not_game_interface(self):
        inp = {"duration_s": 15, "anchors": dict(ANCHORS, characters=["MAXIM"], plot="", ending="")}
        for body in ("Maxim uống thuốc, ui da, đắng quá.\nMAXIM: Ui da!",
                     "Maxim bấm nút thang máy, hai bạn bắn nhau bằng súng nước.\nMAXIM: Giao tranh đi!",
                     "Maxim đứng trong bóng cover của tán cây.\nMAXIM: Bấm nút gọi đi!"):
            c = I.check_script(self.p.conn, self.pid, "CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\n" + body, inp)
            self.assertEqual(c["blocked_scenes"], [], body)
        real = "CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\nCận giao diện game Free Fire, minimap và bảng xếp hạng.\nMAXIM: Hạng nhất!"
        self.assertEqual(I.check_script(self.p.conn, self.pid, real, inp)["blocked_scenes"][0]["scene"], 1)

    def test_place_match_is_by_whole_phrase(self):
        self._add_place("Nhà thờ")
        I.start(self.p.conn, self.pid, IDEA, anchors=dict(ANCHORS, place="Nhà"))
        with self.assertRaisesRegex(I.IdeaError, "Nhà"):
            I.questions(self.p.conn, self.pid, self.m)
        c = I.check_script(self.p.conn, self.pid, "CẢNH 1 - NGÀY, NHÀ\nKelly.", {"duration_s": 15})
        self.assertTrue(any("chưa có mô hình 3D" in t for t in c["problems"]))

    def test_a_3d_file_missing_on_disk_leaves_the_kit_with_a_reason(self):
        self._add_place("Quảng Trường", path="Z:/khong/co/file.glb")
        from core import idea_buildable as B
        k = B.kit(self.p.conn, self.pid)
        self.assertNotIn("Quảng Trường", [x["name"] for x in k["places"]])
        self.assertTrue(any(x["name"] == "Quảng Trường" and "file 3D" in x["why"] for x in k["excluded"]))
        I.start(self.p.conn, self.pid, IDEA, anchors=dict(ANCHORS, place="Quảng Trường"))
        with self.assertRaisesRegex(I.IdeaError, "file 3D"):
            I.questions(self.p.conn, self.pid, self.m)

    def test_old_project_without_anchors_is_pointed_to_new_idea_and_the_check_says_it_did_not_run(self):
        I.start(self.p.conn, self.pid, IDEA)
        with self.assertRaisesRegex(I.IdeaError, "Ý tưởng mới"):
            I.directions(self.p.conn, self.pid, self.m)
        c = I.check_script(self.p.conn, self.pid, "CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\nKelly.\nKELLY: Hi", {"duration_s": 15})
        self.assertTrue(any("điểm then chốt" in f for f in c["flags"]))

    def test_unapproved_outfit_is_marked_in_the_kit(self):
        from core import idea_buildable as B
        aid = self.p.conn.execute("SELECT id FROM assets WHERE name='MAXIM'").fetchone()[0]
        self.p.conn.execute("UPDATE assets SET profile=NULL, description='áo xanh' WHERE id=?", (aid,))
        self.p.conn.commit()
        self.assertIn("hồ sơ chưa duyệt", B.kit_block(B.kit(self.p.conn, self.pid)))

    def test_characters_of_the_old_box_are_checked_too(self):
        I.start(self.p.conn, self.pid, IDEA, characters=["LUNA"], anchors=ANCHORS)
        with self.assertRaisesRegex(I.IdeaError, "LUNA"):
            I.questions(self.p.conn, self.pid, self.m)
