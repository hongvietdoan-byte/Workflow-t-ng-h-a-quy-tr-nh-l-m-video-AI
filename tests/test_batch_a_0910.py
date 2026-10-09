"""Đợt A 09/10: A1 — motion prompt rỗng bị CHẶN ở chỗ gửi video (khớp ô "sẵn sàng" báo đỏ, CHUAN luật 1). Không gọi dịch vụ."""
import unittest

from core.runner import VideoRunner
from tests import test_model_line_f4 as F4


class EmptyMotionBlocked(unittest.TestCase):
    setUp = F4.ShotLineTests.setUp

    def runner(self):
        r = VideoRunner.__new__(VideoRunner)
        r.p = self.p
        return r

    def job(self, sid):
        jid = self.p.create_job(sid, "video_gen")
        return self.p.job(jid)

    def test_empty_prompt_is_blocked_and_a_written_one_goes(self):
        sid = self.sids[0]
        self.p.conn.execute("UPDATE motion_prompts SET motion_prompt='  ' WHERE scene_id=?", (sid,))
        self.p.conn.commit()
        why = self.runner()._blocked(self.job(sid))
        self.assertIsNotNone(why)
        self.assertIn("chưa có motion prompt", why)
        self.p.conn.execute("UPDATE motion_prompts SET motion_prompt='A girl walks to the well, slow push in.' WHERE scene_id=?", (sid,))
        self.p.conn.commit()
        why = self.runner()._blocked(self.job(sid)) or ""
        self.assertNotIn("chưa có motion prompt", why)


if __name__ == "__main__":
    unittest.main()


class BatchBFindings(unittest.TestCase):
    """Đợt B 09/10 — lỗi bắt được khi chạy thử toàn tuyến #24 bằng provider giả (bản sao CSDL)."""
    setUp = F4.ShotLineTests.setUp

    def test_mock_provider_takes_every_option_of_the_real_one(self):
        import inspect
        from core.adapters.clipai import ClipAIVideoProvider
        from core.providers import MockVideoProvider
        real = set(inspect.signature(ClipAIVideoProvider.submit).parameters) - {"self"}
        mock_ = set(inspect.signature(MockVideoProvider.submit).parameters) - {"self"}
        self.assertEqual(real - mock_, set())
        self.assertTrue(hasattr(MockVideoProvider, "submit_final_from_sample"))

    def test_redo_follows_the_new_path_not_the_old_tier(self):
        import os
        from unittest import mock
        from core import model_router, quality_tier
        with mock.patch.dict(os.environ, {"FEATURE_TWO_TIER_QUALITY": "1"}):
            sid = self.sids[1]                                                # shot khó → nháp
            old = self.p.create_job(sid, "video_gen")
            self.p.conn.execute("UPDATE jobs SET quality_tier='final' WHERE id=?", (old,))
            self.p.conn.commit()
            self.assertEqual(quality_tier.tier_for_new_job(self.p.conn, sid, old)["quality_tier"], "final")   # same path: kept
            model_router.set_resolution(self.p.conn, sid, "720p")             # the person picks 720p → gen thẳng
            self.assertEqual(quality_tier.tier_for_new_job(self.p.conn, sid, old)["quality_tier"], "direct")

    def test_quality_pick_covers_the_whole_group_clip(self):
        from unittest import mock
        from core import model_router
        with mock.patch.object(model_router, "group_members", return_value=self.sids[:2]):
            model_router.set_resolution(self.p.conn, self.sids[0], "480p")
        got = [r[0] for r in self.p.conn.execute("SELECT video_resolution FROM motion_prompts WHERE scene_id IN (?,?) ORDER BY scene_id",
                                                  tuple(self.sids[:2]))]
        self.assertEqual(got, ["480p", "480p"])


class ReloadKeepsProject(unittest.TestCase):
    """09/10 (người dùng): F5 luôn về dự án đầu — dự án + màn đang mở nằm trên địa chỉ trang (?pid=…&step=…)."""

    def setUp(self):
        import os
        import tempfile
        from unittest import mock
        from core.db import connect
        from core.pipeline import Pipeline
        tmp = tempfile.mkdtemp()
        patcher = mock.patch.dict(os.environ, {"PIPELINE_DB": os.path.join(tmp, "m.sqlite"), "PIPELINE_DATA": os.path.join(tmp, "projects"),
                                               "KNOWLEDGE_USER_DIR": os.path.join(tmp, "k"), "FEATURE_UI_V2": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.p = Pipeline(connect(os.environ["PIPELINE_DB"]))
        self.first = self.p.create_project("Dự án đầu")
        self.second = self.p.create_project("Dự án đang làm")

    def app(self):
        import os
        from streamlit.testing.v1 import AppTest
        return AppTest.from_file(os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py"), default_timeout=60)

    def test_reload_opens_the_project_and_screen_in_the_address(self):
        at = self.app()
        at.query_params["pid"] = str(self.second)
        at.query_params["step"] = "4"
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(at.session_state["global_pid"], self.second)
        self.assertEqual(at.radio(key="step").value, at.radio(key="step").options[3])     # Video

    def test_picking_a_project_and_screen_writes_the_address(self):
        at = self.app().run()
        at.selectbox(key="global_pid").set_value(self.second).run()
        at.radio(key="step").set_value(at.radio(key="step").options[2]).run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(at.query_params["pid"], [str(self.second)] if isinstance(at.query_params["pid"], list) else str(self.second))
        self.assertIn(at.query_params["step"], ("2", ["2"]))

    def test_a_bad_or_archived_pid_falls_back_quietly(self):
        at = self.app()
        at.query_params["pid"] = "99999"
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertIn(at.session_state["global_pid"], (self.first, self.second))


from tests.test_ui_quality_tier import TwoTierSeed as _Seed, md as _md   # noqa: E402


class VideoHeroAndQcLine(_Seed):
    """09/10 (người dùng): tiến độ màn Video theo 2 bậc; không hiện ngân sách đợt thử CHUNG; điểm QC + tiêu chí một dòng."""

    def test_hero_counts_tiers_and_hides_the_shared_trial_budget(self):
        from unittest import mock
        self.on()
        from core import budget
        real = budget.status
        with mock.patch("core.budget.status", side_effect=lambda *a, **k: dict(real(*a, **k), enabled=True, usd=74.5, spent=66.49)):
            at = self.open(3)
        html = _md(at)
        self.assertIn("Bản cao xong", html)
        self.assertIn("Tiến độ clip (2 bậc)", html)
        self.assertNotIn("Ngân sách đợt thử", html)

    def test_qc_score_and_its_criteria_are_one_line(self):
        sid = self.sids[0]
        jid = self.p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='video_gen' ORDER BY id LIMIT 1", (sid,)).fetchone()[0]
        for crit, score in (("identity", 0.9), ("motion_match", 0.25)):
            self.p.conn.execute("INSERT INTO qc_results (job_id, criterion, score, threshold_at_time) VALUES (?,?,?,0.82)", (jid, crit, score))
        self.p.conn.commit()
        self.on()
        html = _md(self.open(3))
        self.assertRegex(html, r"QC 0\.57[^\n]*Tiêu chí QC · thấp nhất: Đúng hành động \(motion prompt\) 0\.25")


class Layer0RedrawGoesThroughDirector(unittest.TestCase):
    """Đợt C 09/10 (người dùng duyệt): ảnh bị đo lớp 0 bắt lỗi → vẽ lại qua Đạo diễn viết lại prompt (cờ director_rewrite)."""
    setUp = F4.ShotLineTests.setUp

    def _runner(self):
        from core.runner import ImageRunner
        r = ImageRunner.__new__(ImageRunner)
        r.p = self.p
        r._diag = lambda *a, **k: None
        return r

    def test_rewrite_gets_the_layer0_finding_and_the_faulty_picture(self):
        from unittest import mock
        from core.runner import RedrawWithFix
        sid = self.sids[0]
        jid = self.p.create_job(sid, "image_gen")
        plan = mock.Mock()
        with mock.patch.object(self.p, "_rewrite_before_retry", return_value=plan) as rw:
            got = self._runner()._rewrite_redraw(self.p.job(jid), "x.png", RedrawWithFix("QC lớp 0: cỡ cảnh MS, shot xin CU", "Frame as CU."))
        self.assertIs(got, plan)
        kw = rw.call_args.kwargs
        self.assertEqual((kw["qc"]["root_cause"], kw["qc"]["fix"], kw["by"]), ("layer0", "Frame as CU.", "qc"))
        self.assertEqual(self.p.job(jid)["result_path"], "x.png")

    def test_no_paid_rewrite_when_no_take_will_be_made(self):
        from unittest import mock
        from core.runner import RedrawWithFix
        jid = self.p.create_job(self.sids[0], "image_gen")
        with mock.patch.object(self.p, "_retries_exhausted", return_value=True), \
                mock.patch.object(self.p, "_rewrite_before_retry") as rw:
            self.assertIsNone(self._runner()._rewrite_redraw(self.p.job(jid), "x.png", RedrawWithFix("a", "b")))
        rw.assert_not_called()

    def test_a_rewritten_take_does_not_glue_the_old_fix_in_front(self):
        from core.pipeline import REWRITE_NOTE
        jid = self.p.create_job(self.sids[0], "image_gen")
        self.p.conn.execute("UPDATE jobs SET retry_reason='Frame as CU.' WHERE id=?", (jid,))
        self.p.conn.commit()
        self.p.start(jid)
        self.p.fail(jid, "redraw: x")
        new = self.p.retry(jid, "redraw", fix=REWRITE_NOTE + " (lớp 0)")
        self.assertTrue(self.p.job(new)["retry_reason"].startswith(REWRITE_NOTE))


class MusicCoversTheHeldEndCard(unittest.TestCase):
    """09/10 (#24): popup giữ khung cuối 3,5 s → brief nhạc thêm đoạn giữ âm dưới popup, bản nhạc dài thêm 3,5 s."""

    def test_end_card_tail(self):
        from unittest import mock
        from core import music_timing
        b = {"prompt": "Score. Cut off on a sharp unresolved final hit at 0:22.0, no tail.", "film_s": 22.0, "length_ms": 23000}
        popup = {"end_popup": {"items": [{"path": "x.png", "label": "a"}], "headline": "Sắp ra mắt", "seconds": 3.5}}
        with mock.patch("core.delivery.get_settings", return_value=popup):
            out = music_timing._end_card(None, 24, b)
        self.assertEqual(out["length_ms"], 26500)
        self.assertIn("0:22.0-0:25.5: the end title card", out["prompt"])
        self.assertIn("final hit at 0:22.0", out["prompt"])                         # music_fit still finds the end mark
        with mock.patch("core.delivery.get_settings", return_value={"end_popup": dict(popup["end_popup"], hold=False)}):
            self.assertEqual(music_timing._end_card(None, 24, b), b)
        with mock.patch("core.delivery.get_settings", return_value={}):
            self.assertEqual(music_timing._end_card(None, 24, b), b)


class FragmentOwnConnection(unittest.TestCase):
    """09/10 (người dùng bấm chip v3 → v2: SQLite khác luồng): lượt chạy riêng của fragment khung phát ở luồng khác."""

    def test_other_thread_gets_its_own_connection(self):
        import os
        import tempfile
        import threading
        from unittest import mock
        from core.db import connect
        from core.pipeline import Pipeline
        from dashboard import common as C
        from dashboard.steps import step4
        db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        p = Pipeline(connect(db))
        p.actor = "a@b"
        self.assertIs(step4._own_pipeline(p), p)                           # same thread: kept
        out = {}

        def run():
            try:
                q = step4._own_pipeline(p)
                out["ok"] = q is not p and q.conn.execute("SELECT 1").fetchone()[0] == 1 and q.actor == "a@b"
            except Exception as e:  # noqa: BLE001
                out["err"] = repr(e)
        with mock.patch.object(C, "DB", db):
            t = threading.Thread(target=run)
            t.start()
            t.join()
        self.assertEqual(out, {"ok": True})
