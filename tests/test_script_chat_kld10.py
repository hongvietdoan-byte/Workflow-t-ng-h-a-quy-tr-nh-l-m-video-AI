"""KLD-10 (09/10) nối lõi dialogue_chat vào khung chat Kịch bản: đề xuất lưu trong tin, "ok áp dụng câu 1" là sửa (không nút),
"↩ Hoàn tác" khôi phục cả 3 nơi lưu thoại. Không gọi dịch vụ thật (client giả)."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import llm_runner
from core import script_chat as C
from core.db import connect
from core.pipeline import Pipeline

OLD = "Hô biến! Đồ mới nè!"
NEW = "Ủa, đồ này ở đâu ra mà nhìn hay zậy?"
SCRIPT = "CẢNH 1\nMaxim ướm áo.\nMAXIM: Hô biến! Đồ mới nè!\nKELLY: Đi thôi."


class FakeClient:
    def __init__(self, *answers):
        self.answers, self.prompts = list(answers), []

    def complete(self, prompt, images=()):
        self.prompts.append(prompt)
        self.tag = llm_runner.current_tag()
        return llm_runner.LlmReply(self.answers.pop(0), 10, 5)


def answer(reply, proposals=(), apply=()):
    return json.dumps({"reply": reply, "proposals": list(proposals), "apply": list(apply)}, ensure_ascii=False)


def setup_project(test):
    tmp = tempfile.mkdtemp()
    test.addCleanup(shutil.rmtree, tmp, True)
    patcher = mock.patch.dict(os.environ, {"PIPELINE_DB": os.path.join(tmp, "m.sqlite"), "PIPELINE_DATA": os.path.join(tmp, "p"),
                                           "KNOWLEDGE_USER_DIR": os.path.join(tmp, "k")})
    patcher.start()
    test.addCleanup(patcher.stop)
    p = Pipeline(connect(os.environ["PIPELINE_DB"]))
    pid = p.create_project("KLD10")
    p.set_script_text(pid, SCRIPT)
    sid = p.create_scene(pid, 1, "C1")
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({
        "action": "Maxim ướm áo hoodie đỏ", "text": "Maxim ướm áo.\nMAXIM: Hô biến! Đồ mới nè!",
        "dialogue": [{"speaker": "MAXIM", "text": OLD, "delivery": {"emotion": "hào hứng"}}, {"speaker": "KELLY", "text": "Đi thôi."}]},
        ensure_ascii=False), sid))
    p.conn.commit()
    return p, pid


def scene(p, pid):
    return json.loads(p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=1", (pid,)).fetchone()[0])


class IntentTests(unittest.TestCase):
    def test_dialogue_talk_and_approval_go_to_chat(self):
        for text in ("câu thoại 2 nghe cứng quá", "thoại của Maxim ở cảnh 1 có ổn không", "sửa lại câu 3 cho tự nhiên hơn"):
            self.assertEqual(C.intent(text), "chat", text)
        # rà 09/10: lời đồng ý / mã Px, Lx chỉ là "chat" khi dự án có đề xuất mở / có mã đó (cần p, pid)
        p, pid = setup_project(self)
        C.send(p, pid, "câu thoại 1 nghe cứng quá", FakeClient(answer("Thử nhé.", [{"line": "L1", "new": NEW, "why": "B12"}])))
        for text in ("ok áp dụng câu 1 và 3", "Ok áp dụng hết", "chốt hết", "đồng ý P1", "áp dụng L1"):
            self.assertEqual(C.intent(text, p, pid), "chat", text)
        self.assertNotEqual(C.intent("đồng ý P2"), "chat")                     # không có dự án / không có P2 → không phải mã

    def test_short_words_do_not_match_by_accident(self):
        self.assertEqual(C.intent("ok"), "ask")                               # một chữ "ok" chưa rõ ý → vẫn hỏi lại
        self.assertEqual(C.intent("Kenta thoải mái nằm võng ở Bermuda"), "ask")   # 'thoải' ≠ 'thoại'
        self.assertEqual(C.intent("Kelly đọc book ở Đảo Quân Sự"), "ask")         # 'ok' trong 'book'
        self.assertEqual(C.intent("sửa cảnh 2 cho vui hơn"), "edit")
        self.assertEqual(C.intent("CẢNH 1 - NHÀ\nKENTA: Chào."), "script")

    def test_chat_max_tokens_is_3000(self):
        self.assertEqual(llm_runner.STAGE_SETTINGS["script_chat"]["max_tokens"], 3000)


class SendApplyUndoTests(unittest.TestCase):
    def setUp(self):
        self.p, self.pid = setup_project(self)

    def propose(self):
        client = FakeClient(answer("Câu L1 hơi cứng, thử câu này nhé.", [{"line": "L1", "new": NEW, "why": "B12 GenZ"}]))
        C.send(self.p, self.pid, "câu thoại 1 nghe cứng quá", client)
        return client

    def test_proposals_are_saved_in_the_message_and_nothing_changes(self):
        client = self.propose()
        self.assertEqual(client.tag, ("script_chat", self.pid))
        self.assertIn("L1 · cảnh 1 · MAXIM: " + OLD, client.prompts[0])           # prompt của lõi dialogue_chat
        last = C.history(self.p, self.pid)[-1]
        self.assertEqual(last["text"], "Câu L1 hơi cứng, thử câu này nhé.")
        self.assertEqual(last["proposals"], [{"id": "P1", "line": "L1", "speaker": "MAXIM", "old": OLD, "new": NEW, "why": "B12 GenZ",
                                              "state": "open"}])
        self.assertEqual(scene(self.p, self.pid)["dialogue"][0]["text"], OLD)

    def test_unknown_line_is_said_not_dropped_silently(self):
        C.send(self.p, self.pid, "thoại ổn chưa", FakeClient(answer("Sửa L9.", [{"line": "L9", "new": "x", "why": "y"}])))
        last = C.history(self.p, self.pid)[-1]
        self.assertEqual(last.get("proposals") or [], [])
        self.assertIn("L9", last["text"])
        self.assertIn("không có", last["text"])

    def test_ok_applies_then_undo_restores_three_places(self):
        self.propose()
        C.send(self.p, self.pid, "ok áp dụng câu 1", FakeClient(answer("Đã chốt câu 1.", apply=["P1"])))
        hist = C.history(self.p, self.pid)
        self.assertEqual(hist[1]["proposals"][0]["state"], "applied")
        done = hist[-1]
        self.assertEqual(done["applied"], ["P1"])
        self.assertTrue(done["text"].startswith("Đã áp dụng"))
        data = scene(self.p, self.pid)
        self.assertEqual((data["dialogue"][0]["text"], data["dialogue"][0].get("delivery")), (NEW, {"emotion": "hào hứng"}))
        self.assertIn("MAXIM: " + NEW, data["text"])
        self.assertIn("MAXIM: " + NEW, self.p.project(self.pid)["script_text"])
        # a second "ok" for the same proposal never applies twice
        C.send(self.p, self.pid, "ok áp dụng câu 1", FakeClient(answer("Ok.", apply=["P1"])))
        self.assertEqual(sum(1 for m in C.history(self.p, self.pid) if m.get("applied")), 1)
        i = len(hist) - 1
        C.undo(self.p, self.pid, i)
        data = scene(self.p, self.pid)
        self.assertEqual(data["dialogue"][0]["text"], OLD)
        self.assertEqual(data["text"], "Maxim ướm áo.\nMAXIM: Hô biến! Đồ mới nè!")
        self.assertEqual(self.p.project(self.pid)["script_text"], SCRIPT)
        hist = C.history(self.p, self.pid)
        self.assertTrue(hist[i]["undone"])
        self.assertEqual(hist[1]["proposals"][0]["state"], "undone")
        self.assertTrue(hist[-1]["text"].startswith("↩ Đã hoàn tác"))
        with self.assertRaises(ValueError):                                     # undo twice → refused, said
            C.undo(self.p, self.pid, i)

    def test_apply_without_clear_approval_does_nothing(self):
        self.propose()
        C.send(self.p, self.pid, "câu 1 thế nào", FakeClient(answer("Câu 1 ổn hơn.", apply=["P1"])))
        self.assertEqual(scene(self.p, self.pid)["dialogue"][0]["text"], OLD)
        hist = C.history(self.p, self.pid)
        self.assertFalse(any(m.get("applied") for m in hist))
        self.assertEqual(hist[1]["proposals"][0]["state"], "open")
        self.assertIn("Chưa áp dụng", hist[-1]["text"])

    def test_undo_refused_when_dialogue_changed_after(self):
        self.propose()
        C.send(self.p, self.pid, "ok áp dụng câu 1", FakeClient(answer("Ok.", apply=["P1"])))
        i = len(C.history(self.p, self.pid)) - 1
        self.p.set_script_text(self.pid, SCRIPT.replace(OLD, "Câu khác hẳn"))
        with self.assertRaises(ValueError):
            C.undo(self.p, self.pid, i)
        self.assertIn("Câu khác hẳn", self.p.project(self.pid)["script_text"])


class ChatUiTests(unittest.TestCase):
    def setUp(self):
        self.p, self.pid = setup_project(self)
        self.propose_and_apply()

    def propose_and_apply(self):
        C.send(self.p, self.pid, "câu thoại 1 nghe cứng quá",
               FakeClient(answer("Thử câu này.", [{"line": "L1", "new": NEW, "why": "B12 GenZ"}])))
        C.send(self.p, self.pid, "ok áp dụng câu 1", FakeClient(answer("Chốt.", apply=["P1"])))

    def test_card_shows_old_struck_new_why_state_and_undo_works(self):
        from streamlit.testing.v1 import AppTest

        def page():
            import os as _os
            from core.db import connect as _connect
            from core.pipeline import Pipeline as _Pipeline
            from core import script_chat as _C
            from dashboard.steps import step1_box as _box
            p = _Pipeline(_connect(_os.environ["PIPELINE_DB"]))
            pid = int(_os.environ["KLD10_PID"])
            _box._messages(p, pid, _C.history(p, pid))

        with mock.patch.dict(os.environ, {"KLD10_PID": str(self.pid)}):
            at = AppTest.from_function(page, default_timeout=30).run()
            self.assertFalse(at.exception, at.exception)
            shown = " ".join(m.value for m in at.markdown)
            self.assertIn("~~" + OLD + "~~", shown)
            self.assertIn(NEW, shown)
            self.assertIn("B12 GenZ", shown)
            self.assertIn("đã áp dụng", shown)
            undo = [b for b in at.button if b.label.startswith("↩ Hoàn tác")]
            self.assertEqual(len(undo), 1)
            undo[0].click().run()
            self.assertFalse(at.exception, at.exception)
        self.assertEqual(scene(self.p, self.pid)["dialogue"][0]["text"], OLD)
        self.assertEqual(self.p.project(self.pid)["script_text"], SCRIPT)


class ReviewFixTests(unittest.TestCase):
    """Rà độc lập 09/10 (KLD-10): ý tưởng không lạc vào chat, đề xuất cũ không bị áp dụng nhầm, đề xuất bị thay thế, áp dụng trùng."""

    def setUp(self):
        self.p, self.pid = setup_project(self)

    def test_2_idea_sentences_do_not_go_to_paid_chat(self):
        self.assertNotEqual(C.intent("Kelly nhặt điện thoại của Kenta rồi bỏ chạy", self.p, self.pid), "chat")
        self.assertEqual(C.intent("ý tưởng: Kenta cầm P90 đi bo", self.p, self.pid), "idea")
        self.assertNotEqual(C.intent("Kenta cầm P90 đi bo", self.p, self.pid), "chat")
        self.assertNotEqual(C.intent("Kelly chốt cửa rồi chạy hết sức", self.p, self.pid), "chat")   # không có đề xuất mở
        from core import idea_to_script as I
        I.save_state(self.p.conn, self.pid, {"inputs": {"idea": "Kelly tranh thùng thính"}})
        self.assertNotEqual(C.intent("thêm câu thoại Kelly chọc Kenta", self.p, self.pid), "chat")   # đang viết ý tưởng → 'nói thêm'

    def test_1_old_proposal_needs_its_code_named(self):
        C.send(self.p, self.pid, "câu thoại 1 nghe cứng quá", FakeClient(answer("Thử.", [{"line": "L1", "new": NEW, "why": "B12"}])))
        C.send(self.p, self.pid, "còn câu thoại 2 thì sao", FakeClient(answer("Thử.", [{"line": "L2", "new": "Lẹ lên!", "why": "B12"}])))
        C.send(self.p, self.pid, "ok áp dụng", FakeClient(answer("Ok.", apply=["P1"])))           # P1 ở lượt cũ, không gọi tên
        self.assertEqual(scene(self.p, self.pid)["dialogue"][0]["text"], OLD)
        self.assertIn("P1", C.history(self.p, self.pid)[-1]["text"])
        C.send(self.p, self.pid, "ok áp dụng P1", FakeClient(answer("Ok.", apply=["P1"])))        # gọi đích danh → áp dụng
        self.assertEqual(scene(self.p, self.pid)["dialogue"][0]["text"], NEW)

    def test_1_negative_reply_never_applies_even_if_claude_says_apply(self):
        C.send(self.p, self.pid, "câu thoại 1 nghe cứng quá", FakeClient(answer("Thử.", [{"line": "L1", "new": NEW, "why": "B12"}])))
        for text in ("không ok câu 1", "ok nhưng bỏ chữ trời", "ok?"):
            C.send(self.p, self.pid, text, FakeClient(answer("Ok.", apply=["P1"])))
            self.assertEqual(scene(self.p, self.pid)["dialogue"][0]["text"], OLD, text)

    def test_6_superseded_proposal_is_marked_and_shown(self):
        C.send(self.p, self.pid, "câu thoại 1 nghe cứng quá", FakeClient(answer("Thử.", [{"line": "L1", "new": NEW, "why": "B12"}])))
        C.send(self.p, self.pid, "câu 1 ngắn hơn", FakeClient(answer("Vậy nè.", [{"line": "L1", "new": "Ủa, đồ mới hả?", "why": "B12"}])))
        hist = C.history(self.p, self.pid)
        self.assertEqual(hist[1]["proposals"][0]["state"], "superseded")
        self.assertEqual(hist[-1]["proposals"][0]["state"], "open")
        from dashboard.steps import step1_box
        self.assertIn("superseded", step1_box._PROP_STATE)

    def test_7_duplicate_apply_and_same_turn_new_proposal(self):
        C.send(self.p, self.pid, "câu thoại 1 nghe cứng quá", FakeClient(answer("Thử.", [{"line": "L1", "new": NEW, "why": "B12"}])))
        C.send(self.p, self.pid, "ok áp dụng câu 1", FakeClient(answer(
            "Chốt, và thử thêm bản này.", [{"line": "L1", "new": "Ủa, đồ mới hả?", "why": "B12"}], apply=["P1", "P1"])))
        hist = C.history(self.p, self.pid)
        self.assertEqual(scene(self.p, self.pid)["dialogue"][0]["text"], NEW)
        reply = next(m for m in reversed(hist) if m.get("proposals"))
        self.assertNotIn("đã đổi", reply["text"])                               # P1 trùng không sinh cảnh báo giả
        self.assertEqual(reply["proposals"][0]["old"], NEW)                     # câu cũ đọc SAU khi áp dụng
        C.send(self.p, self.pid, "ok áp dụng câu 1", FakeClient(answer("Ok.", apply=[reply["proposals"][0]["id"]])))
        self.assertEqual(scene(self.p, self.pid)["dialogue"][0]["text"], "Ủa, đồ mới hả?")


if __name__ == "__main__":
    unittest.main()
