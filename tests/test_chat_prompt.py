"""D6 'đường như chat' (cờ chat_prompts, TẮT): một lượt Claude NHÌN đúng các ảnh sẽ gửi + ý đồ + mô tả người dùng viết lại bản code ghép
thành một prompt liền mạch; code chỉ kiểm; lưu theo đầu vào (không trả tiền lặp); không dùng được → bản cũ + nói ra."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import chat_prompt
from core.db import connect
from core.llm_runner import LlmReply
from core.pipeline import Pipeline

ASSEMBLED = ("Image 1 is the 3D PLACE render. Image 2 is KELLY. Scene: Kelly holds an assault rifle near the tower. "
             "Fix: tower is too big. Prop lock: the gun is SKORP.")


class FakeClaude:
    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []

    def complete(self, prompt, images=()):
        self.calls.append({"prompt": prompt, "images": list(images)})
        a = self.answers.pop(0)
        return LlmReply(text=a if isinstance(a, str) else json.dumps(a), input_tokens=100, output_tokens=50)


class ChatPromptTests(unittest.TestCase):
    def setUp(self):
        flags = mock.patch("core.features.on", side_effect=lambda n: n == chat_prompt.FLAG)
        flags.start()
        self.addCleanup(flags.stop)
        self.p = Pipeline(connect())
        pid = self.p.create_project("d6")
        self.sid = self.p.create_scene(pid, 1, "s1")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                            (json.dumps({"action": "Kelly đứng sau tường keo, ló mép bên", "end_state": "Kelly ló ra"}), self.sid))
        self.jid = self.p.create_job(self.sid, "image_gen")
        self.p.conn.commit()
        d = tempfile.mkdtemp()
        self.pics = []
        for n in ("plate.png", "kelly.png"):
            path = os.path.join(d, n)
            with open(path, "wb") as f:
                f.write(b"png" + n.encode())
            self.pics.append(path)
        self.said = []

    def _job(self):
        return self.p.job(self.jid)

    def _rewrite(self, client, images=None, assembled=ASSEMBLED, limit=4000):
        imgs = images if images is not None else [("Image 1: plate", self.pics[0]), ("Image 2: KELLY", self.pics[1])]
        return chat_prompt.rewrite(self.p, self._job(), "image", assembled, imgs, model="gpt-image", limit=limit, client=client,
                                   say=lambda lv, code, msg: self.said.append((lv, code, msg)))

    def test_claude_sees_the_pictures_and_its_coherent_prompt_is_sent(self):
        good = ("Image 1 is the 3D PLACE render, Image 2 is KELLY. Kelly crouches behind the glue wall at frame-left, holding her SKORP "
                "with both hands; the tower stays small in the distance as in Image 1.")
        claude = FakeClaude([{"prompt": good, "changes": ["bỏ 'Fix:', gộp khóa SKORP vào câu tả"]}])
        self.p.conn.execute("INSERT INTO review_log (job_id, reviewer_type, decision, note, decided_at) VALUES (?,?,?,?,datetime('now'))",
                            (self.jid, "user", "reject", "tháp to quá, Kelly phải núp sau tường keo"))
        self.p.conn.commit()
        self.assertEqual(self._rewrite(claude), good)
        call = claude.calls[0]
        self.assertEqual([p for _, p in call["images"]], self.pics)                 # exactly the pictures that will be sent
        for part in ("Bản code ghép", ASSEMBLED, "tháp to quá", "Kelly đứng sau tường keo", "Hướng dẫn model đích"):
            self.assertIn(part, call["prompt"])
        self.assertTrue(any(code == "chat_prompt" for _, code, _ in self.said))
        self.assertEqual(self._rewrite(FakeClaude([])), good)                        # same inputs: stored answer, no second call

    def test_new_note_or_picture_asks_again(self):
        a = FakeClaude([{"prompt": "Image 1 and Image 2: v1"}])
        self._rewrite(a)
        b = FakeClaude([{"prompt": "Image 1 and Image 2: v2"}])
        self.p.conn.execute("INSERT INTO review_log (job_id, reviewer_type, decision, note, decided_at) VALUES (?,?,?,?,datetime('now'))",
                            (self.jid, "user", "reject", "đổi góc máy"))
        self.p.conn.commit()
        self.assertEqual(self._rewrite(b), "Image 1 and Image 2: v2")
        self.assertEqual(len(b.calls), 1)

    def test_answer_losing_a_picture_number_or_too_long_keeps_the_old_prompt_and_says_so(self):
        lost = FakeClaude([{"prompt": "Kelly behind the wall, as in Image 1."}])
        self.assertEqual(self._rewrite(lost), ASSEMBLED)
        self.assertTrue(any(code == "chat_prompt_refused" and "Image 2" in msg for _, code, msg in self.said))
        long = FakeClaude([{"prompt": "Image 1 Image 2 " + "x" * 200}])
        self.assertEqual(self._rewrite(long, limit=100), ASSEMBLED)
        viet = FakeClaude([{"prompt": "Image 1 Image 2 Kelly núp sau tường"}])
        self.assertEqual(self._rewrite(viet), ASSEMBLED)

    def test_no_claude_or_claude_error_keeps_the_old_prompt_and_says_so(self):
        with mock.patch("core.prompt_rewrite.client_for", return_value=None):
            self.assertEqual(self._rewrite(None), ASSEMBLED)
        self.assertTrue(any(code == "chat_prompt_noclaude" for _, code, _ in self.said))
        broken = FakeClaude(["not json", "still not json"])
        self.assertEqual(self._rewrite(broken), ASSEMBLED)
        self.assertTrue(any(code == "chat_prompt_fail" for _, code, _ in self.said))

    def test_flag_off_changes_nothing_and_calls_nobody(self):
        claude = FakeClaude([])
        with mock.patch("core.features.on", return_value=False):
            self.assertEqual(self._rewrite(claude), ASSEMBLED)
        self.assertEqual(claude.calls, [])

    def test_guides_exist_for_each_target(self):
        for kind, model in (("image", None), ("video", "dreamina-seedance-2-5-260628"), ("video", "kling")):
            self.assertIn("prompt", chat_prompt.guide_for(kind, model).lower())
        self.assertIn("Kling", chat_prompt.guide_for("video", "kling-v2"))


class RunnerHookTests(unittest.TestCase):
    def test_image_runner_sends_the_rewritten_prompt_only_with_the_flag(self):
        from types import SimpleNamespace
        from core.runner import chat_rewrite
        r = SimpleNamespace(p=mock.Mock())                       # any runner-like object (tests use bare namespaces)
        job = {"id": 1}
        with mock.patch("core.chat_prompt.enabled", return_value=False), mock.patch("core.chat_prompt.rewrite") as rw:
            self.assertEqual(chat_rewrite(r, job, "image", "old", [], None), "old")
            rw.assert_not_called()
        with mock.patch("core.chat_prompt.enabled", return_value=True), mock.patch("core.chat_prompt.rewrite", return_value="new") as rw:
            self.assertEqual(chat_rewrite(r, job, "image", "old", [("a", "b")], "m", limit=99), "new")
            self.assertEqual(rw.call_args.kwargs["limit"], 99)

    def test_glue_wall_code_sentences_survive_the_rewrite(self):
        """14/10 #30: the ban / shape-size / skin / mannequin sentences were added BEFORE D6 — a rewrite dropping them sent a wall
        with no size and no 'never draw the mannequin'. They come back word for word (as side_truth / travel_truth)."""
        from types import SimpleNamespace
        from core import skill_objects
        from core.runner import chat_rewrite
        ban = skill_objects.forbid_sentence(["the glue wall"])
        shape = skill_objects.SHAPE["glue"]
        skin = "The glue wall skin is the pattern shown in Image 3: printed on one solid block, never separate metal plates."
        dummy = skill_objects.mannequin_line(3)
        old = f"Scene: Kelly behind a glue wall (Image 3). {ban} {shape} {skin} {dummy}"
        r = SimpleNamespace(p=mock.Mock())
        with mock.patch("core.chat_prompt.enabled", return_value=True), \
                mock.patch("core.chat_prompt.rewrite", return_value="Kelly crouches behind the glue wall from Image 3."):
            out = chat_rewrite(r, {"id": 1}, "image", old, [("a", "b")], "m")
        for line in (ban, shape, skin, dummy):
            self.assertIn(line, out)
        self.assertTrue(out.startswith("Kelly crouches"))
        with mock.patch("core.chat_prompt.enabled", return_value=True), \
                mock.patch("core.chat_prompt.rewrite", return_value="Kelly crouches behind the glue wall from Image 3."):
            self.assertEqual(chat_rewrite(r, {"id": 1}, "image", old, [("a", "b")], "m", limit=60), old)   # no room → the assembled one

    def test_kept_glue_lines_take_odd_names_whole_and_d6_writes_within_the_room_left(self):
        """rà 14/10: a Kho name with '–' / brackets kept whole, the capital word before it never swallowed; D6 gets limit − kept lines
        (else every rewrite overflowed and fell back silently), and a fall-back is said."""
        from types import SimpleNamespace
        from core import skill_objects
        from core.runner import chat_rewrite
        odd = skill_objects.FORBID.format(names="Bom keo – skin (OB55), v2")
        self.assertEqual(skill_objects.kept_lines(f"Kelly runs. {odd}"), [odd])
        glue = skill_objects.forbid_sentence(["the glue wall"])
        self.assertEqual(skill_objects.kept_lines(f"Kelly runs left. Then Kelly turns: {glue}"), [glue])   # starts at the sentence
        run_on = f"Kelly runs Left {glue}"             # no sentence end before it: the assembled sentence word for word, never cut
        self.assertEqual(skill_objects.kept_lines("Scene. " + run_on), [run_on])
        ban = skill_objects.forbid_sentence(["the glue wall"])
        old = "Scene: Kelly behind a glue wall. " + ban + " " + skill_objects.SHAPE["glue"]
        room = len(ban) + 1 + len(skill_objects.SHAPE["glue"]) + 1
        r = SimpleNamespace(p=mock.Mock(), _diag=mock.Mock())
        with mock.patch("core.chat_prompt.enabled", return_value=True), \
                mock.patch("core.chat_prompt.rewrite", return_value="Kelly crouches behind the glue wall.") as rw:
            out = chat_rewrite(r, {"id": 1}, "image", old, [("a", "b")], "m", limit=4000)
        self.assertEqual(rw.call_args.kwargs["limit"], 4000 - room)
        self.assertTrue(out.startswith("Kelly crouches") and ban in out)
        with mock.patch("core.chat_prompt.enabled", return_value=True), \
                mock.patch("core.chat_prompt.rewrite", return_value="K" * (len(old) - 20)):
            self.assertEqual(chat_rewrite(r, {"id": 1}, "image", old, [("a", "b")], "m", limit=len(old) + 5), old)
        self.assertIn("d6_kept_overflow", [c.args[2] for c in r._diag.call_args_list])


if __name__ == "__main__":
    unittest.main()


class PilotToolTests(unittest.TestCase):
    """tools/d6_pilot.py: prompt cũ ↔ D6 trên bản SAO của CSDL (CSDL thật không đổi), báo giá khi chưa có --yes."""

    def setUp(self):
        import sqlite3
        from core import batch, llm_runner
        from tests.test_v3 import _approve_all_images, _approve_all_motion, kenta_project
        p, self.pid = kenta_project()
        llm_runner.run_director(p, self.pid, llm_runner.MockLlm())
        self.data = tempfile.mkdtemp()
        _approve_all_images(p, self.pid, self.data)
        _approve_all_motion(p, self.pid, self.data)
        batch.queue_videos(p, self.pid, self.data)
        self.db = os.path.join(self.data, "real.sqlite")
        out = sqlite3.connect(self.db)
        p.conn.backup(out)
        out.close()
        self.idx = p.conn.execute("SELECT s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE s.project_id=? AND j.type='image_gen' "
                                  "AND j.state='approved' ORDER BY s.idx LIMIT 1", (self.pid,)).fetchone()[0]

    def _run(self, *extra):
        import importlib.util
        spec = importlib.util.spec_from_file_location("d6_pilot", os.path.join(os.path.dirname(__file__), "..", "tools", "d6_pilot.py"))
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        out = os.path.join(self.data, "pilot.md")
        tool.main(["--project", str(self.pid), "--shots", str(self.idx), "--kind", "image", "--db", self.db, "--data", self.data,
                   "--out", out, *extra])
        with open(out, encoding="utf-8") as f:
            return f.read()

    def test_dry_run_prices_and_shows_the_old_prompt_without_calling(self):
        with mock.patch("core.prompt_rewrite.client_for") as cf:
            text = self._run()
            cf.assert_not_called()
        self.assertIn("chưa gọi", text)
        self.assertIn("CŨ (code ghép", text)

    def test_yes_writes_old_and_new_side_by_side_and_leaves_the_real_database_alone(self):
        import sqlite3
        before = sqlite3.connect(self.db).execute("SELECT COUNT(*) FROM app_settings").fetchone()[0]

        class Echo:
            def complete(self, prompt, images=()):
                old = prompt.split("# Bản code ghép", 1)[1].split("\n", 1)[1].split("\n\n# Bắt buộc", 1)[0]
                return LlmReply(text=json.dumps({"prompt": "D6 VERSION " + old.strip(), "changes": ["gộp câu"]}))

        with mock.patch("core.prompt_rewrite.client_for", return_value=Echo()):
            text = self._run("--yes")
        self.assertIn("D6 VERSION", text)
        self.assertIn("CŨ (code ghép", text)
        after = sqlite3.connect(self.db).execute("SELECT COUNT(*) FROM app_settings").fetchone()[0]
        self.assertEqual(before, after)                                          # nothing written to the real database


class NoteLabelTests(unittest.TestCase):
    def test_reject_box_asks_for_a_description_only_with_the_flag(self):
        with mock.patch("core.features.on", return_value=False):
            self.assertEqual(chat_prompt.note_label("cũ"), "cũ")
        with mock.patch("core.features.on", side_effect=lambda n: n == chat_prompt.FLAG):
            self.assertIn("Mô tả", chat_prompt.note_label("cũ"))


class SafetyTests(ChatPromptTests):
    def test_same_picture_rewritten_on_disk_is_not_paid_again(self):
        self._rewrite(FakeClaude([{"prompt": "Image 1 Image 2 once"}]))
        with open(self.pics[0], "rb") as f:
            same = f.read()
        os.utime(self.pics[0], (1, 1))                                   # re-extracted file: new date, same content
        with open(self.pics[0], "wb") as f:
            f.write(same)
        self.assertEqual(self._rewrite(FakeClaude([])), "Image 1 Image 2 once")

    def test_inputs_changing_every_poll_stop_after_the_cap(self):
        for i in range(chat_prompt.MAX_CALLS_PER_JOB):
            self._rewrite(FakeClaude([{"prompt": f"Image 1 Image 2 v{i}"}]), assembled=ASSEMBLED + f" t{i}")
        nobody = FakeClaude([])
        got = self._rewrite(nobody, assembled=ASSEMBLED + " changed again")
        self.assertEqual(got, f"Image 1 Image 2 v{chat_prompt.MAX_CALLS_PER_JOB - 1}")    # the last D6 prompt, no new call
        self.assertEqual(nobody.calls, [])
        self.assertTrue(any(code == "chat_prompt_cap" for _, code, _ in self.said))

    def test_block_tags_must_survive(self):
        self.assertTrue(chat_prompt.check("[Event] Image 1 run", "Image 1 run", 999))
        self.assertEqual(chat_prompt.check("[Event] Image 1 run", "[Event] Image 1 she runs", 999), [])


class D6TrialFixes(unittest.TestCase):
    """Thử D6 #28/#29 (14/10): 2/5 prompt ảnh + 2/3 lượt video bị code chặn; D6 thêm 'clock tower' → mặt đồng hồ."""

    def test_grouped_image_code_counts_per_picture(self):
        old = "Images 2/3 are KELLY. Image 1 is the render."
        self.assertEqual(chat_prompt.check(old, "Image 1 is the render; Image 2 and Image 3 show KELLY.", 999), [])
        self.assertTrue(chat_prompt.check(old, "Image 1 is the render; Image 2 shows KELLY.", 999))
        self.assertEqual(chat_prompt.required_codes(old), ["Image 1", "Image 2", "Image 3"])

    def test_claude_is_told_the_exact_codes_and_the_limit(self):
        text = chat_prompt.build_text("video", "seedance", "Shot 1 runs. Shot 2 throws. Images 2/3 KELLY.", [], {}, [], 4000)
        self.assertIn("Image 2, Image 3, Shot 1, Shot 2", text)
        self.assertIn("Tối đa 4000 ký tự", text)
        self.assertIn("clock tower", text)

    def test_added_clock_tower_goes_back_to_a_neutral_word(self):
        new, fixed = chat_prompt.no_added_features("The buildings and the tower stay.", "The buildings, clock tower and steps stay.")
        self.assertEqual(new, "The buildings, stone tower and steps stay.")
        self.assertEqual(fixed, ["clock tower"])
        kept, none = chat_prompt.no_added_features("no clock tower in frame", "no clock tower in frame, fog")
        self.assertEqual((kept, none), ("no clock tower in frame, fog", []))


class M71QuotaAndPayload(unittest.TestCase):
    """C-M71 A5 (P31-G29): (1) pregen_check --payload nói rõ gói D6 thật (bản D6 đã lưu của job, hoặc 'chưa xem được') thay vì in
    im lặng bản code ghép; (2) Claude hết tiền / hết lượt → bản code ghép + MỘT diag có mã, không đếm vào trần lượt của job, không gọi
    lại mỗi nhịp."""
    setUp, _job, _rewrite = ChatPromptTests.setUp, ChatPromptTests._job, ChatPromptTests._rewrite

    def _quota(self):
        from core.llm_runner import LlmError

        class Broke(FakeClaude):
            def complete(self, prompt, images=()):
                self.calls.append(prompt)
                raise LlmError("credit balance is too low", code="out_of_credit")
        return Broke([])

    def test_out_of_credit_is_one_coded_diag_and_not_counted(self):
        broke = self._quota()
        self.assertEqual(self._rewrite(broke), ASSEMBLED)
        self.assertEqual([c for _, c, _ in self.said], [chat_prompt.QUOTA_CODE])
        calls = self.p.conn.execute("SELECT value FROM app_settings WHERE key=?", (chat_prompt.CALLS_KEY.format(self.jid),)).fetchone()
        self.assertEqual(json.loads(calls[0])["n"] if calls else 0, 0)        # trước: 1 (2 nhịp hết tiền = hết trần job vĩnh viễn)
        again = self._quota()
        self.assertEqual(self._rewrite(again), ASSEMBLED)                     # nhịp sau: không gọi lại trong lúc tạm ngừng
        self.assertEqual(again.calls, [])
        self.assertEqual({c for _, c, _ in self.said}, {chat_prompt.QUOTA_CODE})
        self.assertEqual(len({m for _, c, m in self.said if c == chat_prompt.QUOTA_CODE}), 1)   # cùng lời → _diag_once gộp 1 dòng/job

    def test_after_pause_claude_is_asked_again(self):
        self._rewrite(self._quota())
        good = FakeClaude([{"prompt": "Image 1 and Image 2: ok"}])
        with mock.patch.object(chat_prompt.time, "time", return_value=chat_prompt.time.time() + chat_prompt.QUOTA_PAUSE_S + 1):
            self.assertEqual(self._rewrite(good), "Image 1 and Image 2: ok")

    def test_saved_view_for_pregen_payload(self):
        self.assertEqual(chat_prompt.saved_view(self.p.conn, self.jid, "image")["state"], "unseen")
        self.assertIn("chưa xem được", chat_prompt.saved_view(self.p.conn, self.jid, "image")["note"])
        self._rewrite(FakeClaude([{"prompt": "Image 1 and Image 2: d6 text"}]))
        view = chat_prompt.saved_view(self.p.conn, self.jid, "image")
        self.assertEqual((view["state"], view["prompt"]), ("saved", "Image 1 and Image 2: d6 text"))

    def test_replay_payload_prints_d6_state(self):
        import contextlib
        import io
        from tools import replay_payload as rp
        res = [{"idx": 1, "scene_id": self.sid, "job_id": self.jid, "refs": [], "real_sent": None, "vs_package": None,
                "prompt": ASSEMBLED, "diags": []}]
        rp.annotate_d6(self.p.conn, res)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rp._print(res, 0)
        self.assertIn("D6", out.getvalue())
        self.assertIn("chưa xem được", out.getvalue())
