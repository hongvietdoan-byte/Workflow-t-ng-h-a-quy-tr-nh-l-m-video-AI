"""S13 nhánh F: màn Storyboard v2 (cờ ui_v2) — thẻ ảnh kính với pill/QC/dải phiên bản/4 nút luôn hiện, thanh hành động dính,
các nút gọi đúng hàm pipeline như cũ; cờ tắt = giao diện cũ (các test cũ của màn này chạy ở test_dashboard / test_storyboard_gate)."""
import os
import tempfile
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from core.db import connect
from core.llm_io import lock_character_bible, store_motion_prompts, store_scene_analysis
from core.pipeline import Pipeline
from tests.test_llm_io_preflight import ANALYSIS

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")


class StoryboardV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        self.env = mock.patch.dict(os.environ, {"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(self.tmp, "projects"),
                                                "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "ku"), "FEATURE_UI_V2": "1",
                                                "DASHBOARD_EXPERT": "1"})
        self.env.start()
        self.addCleanup(self.env.stop)

    # -- seed ------------------------------------------------------------------------------------------------------------------
    def seed(self, scenes=5):
        p = Pipeline(connect(self.db))
        pid = p.create_project("Demo")
        p.create_scene(pid, 1, "CẢNH 1")
        store_scene_analysis(p, pid, ANALYSIS)
        lock_character_bible(p, pid)
        for idx in range(2, scenes + 1):
            p.create_scene(pid, idx, f"CẢNH {idx}")
        ids = [r["id"] for r in p.conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx", (pid,))]
        return p, pid, ids

    @staticmethod
    def job_in(p, scene, state):
        jid = p.create_job(scene)
        if state == "queued":
            return jid
        p.start(jid)
        if state == "running":
            return jid
        if state == "failed":
            p.fail(jid, "lỗi thử") if hasattr(p, "fail") else None
            return jid
        p.succeed(jid)
        p.apply_qc(jid, {"a": 0.9, "b": 0.9})            # human_qc: waits for a person
        if state == "approved":
            p.approve(jid, "user")
        return jid

    def board(self):
        at = AppTest.from_file(APP, default_timeout=60).run()
        at.radio(key="step").set_value(at.radio(key="step").options[2]).run()
        self.assertFalse(at.exception, at.exception)
        return at

    @staticmethod
    def text(at):
        return " ".join(m.value for m in at.markdown)

    @staticmethod
    def inside(at):
        """Text held by the ⓘ popovers (de-duplicated: the test tree reports nested blocks more than once)."""
        return " ".join(sorted({m.value for pop in at.get("popover") for m in pop.markdown}))

    @staticmethod
    def states(db):
        return [(r["id"], r["state"]) for r in Pipeline(connect(db)).conn.execute("SELECT id, state FROM jobs ORDER BY id")]

    # -- grid ------------------------------------------------------------------------------------------------------------------
    def test_grid_shows_a_card_per_scene_with_the_right_pill_and_four_visible_actions(self):
        p, pid, sc = self.seed(4)
        approved = self.job_in(p, sc[0], "approved")
        review = self.job_in(p, sc[1], "pending_review")
        queued = self.job_in(p, sc[2], "queued")
        running = self.job_in(p, sc[3], "running")
        at = self.board()
        txt = self.text(at)
        for label in ("Đã duyệt", "Cần duyệt", "Chờ gen", "Đang làm"):
            self.assertIn(label, txt)
        self.assertIn("QC 0.90", txt)                                           # the QC chip from the real scores
        keys = {b.key for b in at.button}
        for k in (f"a_{review}", f"dd_{review}", f"r_{review}", f"sel_btn_{review}",           # ✔ Duyệt · ✖ Loại · ↻ Vẽ lại · ✎ Sửa
                  f"a_{approved}", f"reopen_{approved}", f"c_{queued}", f"c_{running}"):
            self.assertIn(k, keys, k)
        labels = {b.key: b.label for b in at.button}
        self.assertEqual([labels[f"a_{review}"], labels[f"dd_{review}"], labels[f"r_{review}"], labels[f"sel_btn_{review}"]],
                         ["✔ Duyệt", "✖ Loại", "↻ Vẽ lại", "✎ Sửa"])
        self.assertTrue(next(b for b in at.button if b.key == f"a_{review}").proto.type == "primary")
        self.assertTrue(next(b for b in at.button if b.key == f"a_{approved}").disabled)     # an approved card cannot be approved twice
        self.assertIn(f"note_{review}", {t.key for t in at.text_input})                       # the reason input sits on the card
        self.assertIn(f"filter_{pid}", {r.key for r in at.radio})                              # filters unchanged

    def test_failed_card_has_the_fix_input_and_a_failed_pill(self):
        p, pid, sc = self.seed(2)
        j = p.create_job(sc[0])
        p.start(j)
        p.fail(j, "429") if hasattr(p, "fail") else p.transition(j, __import__("core.states", fromlist=["JobState"]).JobState.FAILED)
        at = self.board()
        self.assertIn("Lỗi", self.text(at))
        self.assertIn(f"dfix_{j}", {t.key for t in at.text_input})
        self.assertIn(f"dretry_{j}", {b.key for b in at.button})

    def test_hero_and_sticky_bar_are_there(self):
        p, pid, sc = self.seed(3)
        self.job_in(p, sc[0], "approved")
        self.job_in(p, sc[1], "pending_review")
        at = self.board()
        txt = self.text(at)
        self.assertIn("Đã duyệt", txt)
        self.assertIn("1 / 3", txt)                                                 # stat: approved n / N
        self.assertIn("1 ảnh chờ duyệt", txt)                                       # the action bar summary
        bar = next(b for b in at.button if b.key == "approve_all")
        self.assertEqual(bar.proto.type, "primary")                                 # the primary button of the one action bar
        self.assertEqual(bar.label, "✔ Duyệt tất cả (1 ảnh)")
        self.assertFalse(any("Duyệt tất cả" in b.label and b.key not in ("approve_all", "btn_ok_all") for b in at.button))   # one in the image tab (btn_ok_all = the Motion tab)

    # -- the buttons still do what they did ----------------------------------------------------------------------------------------
    def test_approve_all_asks_then_approves(self):
        p, pid, sc = self.seed(2)
        a, b = self.job_in(p, sc[0], "pending_review"), self.job_in(p, sc[1], "pending_review")
        at = self.board()
        next(x for x in at.button if x.key == "approve_all").click().run()
        self.assertEqual({s for _, s in self.states(self.db)}, {"pending_review"})          # a question first
        self.assertTrue(any("Duyệt tất cả 2 ảnh" in w.value for w in at.warning))
        next(x for x in at.button if x.key == "approve_all_yes").click().run()
        self.assertEqual({s for _, s in self.states(self.db)}, {"approved"})

    def test_approve_reject_and_redraw_call_the_same_pipeline_functions(self):
        p, pid, sc = self.seed(3)
        a, b, c = (self.job_in(p, sc[i], "pending_review") for i in range(3))
        at = self.board()
        next(x for x in at.button if x.key == f"a_{a}").click().run()                       # ✔ Duyệt
        at.text_input(key=f"note_{c}").set_value("Kelly wears the yellow jacket").run()
        next(x for x in at.button if x.key == f"r_{c}").click().run()                       # ↻ Vẽ lại = reject + a new job with the reason
        at = self.board()
        next(x for x in at.button if x.key == f"dd_{b}").click().run()                      # ✖ Loại = reject, no new job
        rows = dict(self.states(self.db))
        self.assertEqual((rows[a], rows[b], rows[c]), ("approved", "rejected", "rejected"))
        new = [i for i, s in rows.items() if i not in (a, b, c)]
        self.assertEqual(len(new), 1)                                                        # only the redraw spawned a job
        reason = Pipeline(connect(self.db)).conn.execute("SELECT retry_reason FROM jobs WHERE id=?", (new[0],)).fetchone()["retry_reason"]
        self.assertIn("yellow jacket", reason or "")

    def test_version_strip_walks_the_history_like_the_old_pager(self):
        p, pid, sc = self.seed(1)
        first = self.job_in(p, sc[0], "pending_review")
        p.reject(first, "user", "sai")                                                       # → a retry job (queued)
        second = [i for i, s in self.states(self.db) if i != first][0]
        at = self.board()
        keys = {b.key for b in at.button}
        self.assertIn(f"sbvon_{pid}_{sc[0]}_1", keys)                                        # v2 is the current chip
        self.assertIn(f"sbv_{pid}_{sc[0]}_0", keys)
        self.assertIn(f"hist_{pid}_{sc[0]}_prev", keys)                                      # the old pager keys still work
        self.assertIn(f"c_{second}", keys)                                                   # latest = live card
        next(x for x in at.button if x.key == f"sbv_{pid}_{sc[0]}_0").click().run()
        keys = {b.key for b in at.button}
        self.assertIn(f"sel_btn_{first}", keys)                                              # an old take: look only
        self.assertNotIn(f"c_{second}", keys)
        self.assertIn("bản cũ", self.text(at))

    def test_clicking_edit_opens_the_detail_without_error(self):
        p, pid, sc = self.seed(1)
        j = self.job_in(p, sc[0], "pending_review")
        at = self.board()
        next(x for x in at.button if x.key == f"sel_btn_{j}").click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(at.session_state[f"sel_{pid}"], j)

    def test_empty_project_shows_an_empty_state(self):
        self.seed(1)
        at = self.board()
        self.assertIn("Chưa có ảnh nào", self.text(at))

    # -- Motion tab -------------------------------------------------------------------------------------------------------------------
    def test_motion_cards_have_prompt_voice_and_animatic_pills(self):
        p, pid, sc = self.seed(1)
        self.job_in(p, sc[0], "approved")
        store_motion_prompts(p, pid, {"scenes": [{"idx": 1, "motion_prompt": "push in slowly", "camera": "push", "duration_sec": 5,
                                                  "negative_prompt": ""}]})
        at = AppTest.from_file(APP, default_timeout=60)
        at.session_state["sb_tab"] = "🎞 Motion, giọng & animatic"
        at.run()
        at.radio(key="step").set_value(at.radio(key="step").options[2]).run()
        self.assertFalse(at.exception, at.exception)
        txt = self.text(at)
        self.assertIn("Prompt cần duyệt", txt)
        self.assertIn("Animatic", txt)
        self.assertIn(f"mp_{sc[0]}", {t.key for t in at.text_area})                          # every control still there
        self.assertIn(f"mpa_{sc[0]}", {b.key for b in at.button})


    # -- bớt chữ: chi tiết trong ⓘ (QUY_TAC §5) ---------------------------------------------------------------------------------------
    def test_card_keeps_p1_and_moves_details_into_an_info_popover(self):
        p, pid, sc = self.seed(2)
        review = self.job_in(p, sc[0], "pending_review")
        at = self.board()
        txt = self.text(at)
        self.assertIn("QC 0.90", txt)                                           # P1: the QC chip stays
        keys = {b.key for b in at.button}
        for k in (f"a_{review}", f"dd_{review}", f"r_{review}", f"sel_btn_{review}"):
            self.assertIn(k, keys)                                              # the 4 main buttons stay
        pops = [b for b in at.get("popover") if b.proto.popover.label == "ⓘ"]
        self.assertGreaterEqual(len(pops), 2)                                   # one ⓘ per card (2 scenes); the card's own "⋯ Thêm" is gone
        inside = self.inside(at)
        self.assertIn("Điểm QC từng tiêu chí", inside)                          # criterion scores live in the ⓘ

    def test_old_take_reason_is_in_the_info_not_outside(self):
        p, pid, sc = self.seed(1)
        first = self.job_in(p, sc[0], "pending_review")
        p.reject(first, "user", "sai tay trái hoàn toàn")
        at = self.board()
        self.assertNotIn("sai tay trái hoàn toàn", " ".join(c.value for c in at.caption))    # no loose caption outside ...
        self.assertIn("sai tay trái hoàn toàn", self.inside(at))                             # ... the full reason is in the ⓘ
        next(x for x in at.button if x.key == f"sbv_{pid}_{sc[0]}_0").click().run()          # an old take: look only, still no caption
        self.assertFalse(any("Lý do gen lại" in c.value for c in at.caption))

    def test_gen_bar_estimate_is_one_line_with_info(self):
        p, pid, sc = self.seed(2)
        at = self.board()
        txt = self.text(at)
        self.assertNotIn("Ước tính chi phí:", txt)                              # the long st.info is gone
        self.assertFalse(any("Ước tính chi phí" in i.value for i in at.info))
        self.assertTrue(any(b.proto.popover.label == "ⓘ" for b in at.get("popover")))

    def test_panels_under_the_grid_are_closed_expanders(self):
        p, pid, sc = self.seed(3)
        self.job_in(p, sc[0], "approved")
        self.job_in(p, sc[1], "approved")
        at = self.board()
        panels = [e for e in at.expander if e.label.startswith(("⚙ Chính sách QC", "🎨 Kiểm tra đồng bộ"))]
        self.assertTrue(panels)
        for e in panels:
            self.assertFalse(e.proto.expanded, e.label)                         # default closed

    # -- cổng storyboard đang chờ: nút board_ok_<pid> trên thanh dính -------------------------------------------------------------------
    def test_board_ok_button_when_the_gate_waits(self):
        import json
        from core import autopilot
        p, pid, sc = self.seed(1)
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_no": 1, "characters": ["Kelly"], "duration_s": 4}), sc[0]))
        jid = self.job_in(p, sc[0], "approved")
        p.conn.execute("UPDATE projects SET autopilot_state='waiting' WHERE id=?", (pid,))
        p.conn.commit()
        autopilot.set_gates(p, pid, {"waiting_for": "storyboard"})
        at = self.board()
        self.assertIn(f"board_ok_{pid}", {b.key for b in at.button})            # the button is on the sticky bar
        self.assertEqual(sum(1 for b in at.button if b.key == f"board_ok_{pid}"), 1)   # and only there (not duplicated in the closed panel)
        self.assertIn("Chờ bạn duyệt storyboard", self.text(at))
        with mock.patch("dashboard.design.screens.storyboard_cards.autopilot_manager") as mgr:
            next(b for b in at.button if b.key == f"board_ok_{pid}").click().run()
        self.assertFalse(at.exception, at.exception)
        mgr.return_value.start.assert_called_once_with(pid)                     # the background run starts again
        gates = autopilot.get_gates(Pipeline(connect(self.db)), pid)
        self.assertIsNone(gates["waiting_for"])
        self.assertEqual(gates["storyboard_ok"], [jid])

    def test_no_board_ok_button_when_nothing_waits(self):
        p, pid, sc = self.seed(1)
        self.job_in(p, sc[0], "approved")
        at = self.board()
        self.assertNotIn(f"board_ok_{pid}", {b.key for b in at.button})

    # -- Motion: chi tiết vào ⓘ -------------------------------------------------------------------------------------------------------
    def test_motion_card_details_go_into_the_info(self):
        import json
        p, pid, sc = self.seed(1)
        self.job_in(p, sc[0], "approved")
        store_motion_prompts(p, pid, {"scenes": [{"idx": 1, "motion_prompt": "push in slowly", "camera": "push", "duration_sec": 5,
                                                  "negative_prompt": ""}]})
        p.conn.execute("UPDATE motion_prompts SET check_flags=?, lint=? WHERE scene_id=?",
                       (json.dumps(["thiếu hướng máy"]), json.dumps({"ok": False, "issues": ["mơ hồ vị trí"], "revised_prompt": "push in from left"}), sc[0]))
        p.conn.commit()
        at = AppTest.from_file(APP, default_timeout=60)
        at.session_state["sb_tab"] = "🎞 Motion, giọng & animatic"
        at.run()
        at.radio(key="step").set_value(at.radio(key="step").options[2]).run()
        self.assertFalse(at.exception, at.exception)
        outside = " ".join(c.value for c in at.caption)
        self.assertNotIn("thiếu hướng máy", outside)                            # flags are not loose captions any more
        self.assertNotIn("mơ hồ vị trí", outside)
        inside = self.inside(at)
        self.assertIn("thiếu hướng máy", inside)
        self.assertIn("mơ hồ vị trí", inside)
        self.assertIn("push in from left", inside)
        self.assertIn(f"lint_apply_{sc[0]}", {b.key for b in at.button})        # the "use the revision" action stays reachable
        self.assertIn("⚑ 1 cờ", self.text(at))


class FlagOffTest(unittest.TestCase):
    def test_flag_off_keeps_the_old_cards(self):
        tmp = tempfile.mkdtemp()
        with mock.patch.dict(os.environ, {"PIPELINE_DB": os.path.join(tmp, "m.sqlite"), "PIPELINE_DATA": os.path.join(tmp, "projects"),
                                          "KNOWLEDGE_USER_DIR": os.path.join(tmp, "ku"), "FEATURE_UI_V2": "0"}):
            p = Pipeline(connect(os.environ["PIPELINE_DB"]))
            pid = p.create_project("Demo")
            sid = p.create_scene(pid, 1, "CẢNH 1")
            j = p.create_job(sid)
            p.start(j), p.succeed(j), p.apply_qc(j, {"a": 0.9, "b": 0.9})
            at = AppTest.from_file(APP, default_timeout=60).run()
            at.radio(key="step").set_value(at.radio(key="step").options[2]).run()
            self.assertFalse(at.exception)
            labels = {b.key: b.label for b in at.button}
            self.assertEqual(labels[f"r_{j}"], "✖ Loại")                                     # the old wording / keys
            self.assertFalse(any("sbv" in b.key for b in at.button))


if __name__ == "__main__":
    unittest.main()
