"""N4 (08/10) — UI 2 bậc chất lượng + thanh tiến độ + bản dựng DRAFT (docs/THIET_KE_2_BAC_CHAT_LUONG_VA_NHAC_2026-10-08.md mục 1, 5a.5, 5a.8).

Chạy với core/quality_tier.py THẬT (N1): trạng thái từng cảnh dựng bằng job video (quality_tier) + review_log người duyệt, như
tests/test_quality_tier.py. Không gọi API: VIDEO_PROVIDER=mock và runner.submit_pending được thay bằng Mock."""
import json
import os
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from core.db import connect
from dashboard import quality_ui as Q
from tests.test_ui_video import APP, STEP_DELIVER, V2, VideoSeed, md

# trạng thái → (quality_tier, jobs.state, người duyệt, gửi từ ảnh khác ảnh đã duyệt = đầu vào đã đổi)
RECIPE = {"none": ("draft", "failed", False, False), "draft_review": ("draft", "pending_review", False, False),
          "draft_ok": ("draft", "approved", True, False), "draft_stale": ("draft", "approved", True, True),
          "final_ok": ("final", "approved", False, False), "direct_ok": ("direct", "approved", False, False)}


class TwoTierSeed(VideoSeed):
    """VideoSeed's five scenes: 1 draft_ok · 2 draft_review · 3 draft_stale · 4 none · 5 final_ok."""

    def setUp(self):
        super().setUp()
        c = self.p.conn
        self.sids = [r["id"] for r in c.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx", (self.pid,))]
        for sid in self.sids:
            c.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, duration_sec, state) VALUES (?, 'x', 4, 'approved')", (sid,))
        self.other_img = self.p.create_job(self.sids[2], "image_gen")       # never approved: a draft sent from it is outdated
        c.execute("UPDATE scenes SET data=? WHERE id=?",
                  (json.dumps({"difficulty": "complex", "difficulty_why": "hai người nhảy cùng lúc",
                               "difficulty_check": {"score": 4, "factors": ["2 người", "nhảy"], "suggest": "complex",
                                                    "note": "dữ liệu shot đồng ý"}}), self.sids[0]))
        for sid in self.sids[1:]:          # 09/10: chưa có nhãn → gen thẳng; các cảnh mẫu này thử đường nháp → nhãn 'chưa rõ'
            c.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"difficulty": "unknown"}), sid))
        c.commit()
        for sid, st in zip(self.sids, ["draft_ok", "draft_review", "draft_stale", "none", "final_ok"]):
            self.put(sid, st)

    def put(self, sid, st):
        """Rewrite the scene's video job so core.quality_tier.state() reads `st` (real data, no fake module)."""
        tier, jstate, person, outdated = RECIPE[st]
        c = self.p.conn
        jid = c.execute("SELECT id FROM jobs WHERE scene_id=? AND type='video_gen' ORDER BY id LIMIT 1", (sid,)).fetchone()["id"]
        c.execute("UPDATE jobs SET quality_tier=?, state=?, source_job_id=?, input_hash=NULL WHERE id=?",
                  (tier, jstate, self.other_img if outdated else None, jid))
        if tier == "draft":           # F3: a Seedance 2.5 sample with its task id = the high tier comes FROM the draft (no new gen)
            c.execute("UPDATE jobs SET model='seedance-2.5', external_id=? WHERE id=?", (f"seedance:t{jid}", jid))
        c.execute("DELETE FROM review_log WHERE job_id=? AND reviewer_type='user'", (jid,))
        if person:
            c.execute("INSERT INTO review_log (job_id, reviewer_type, decision, note, decided_at) "
                      "VALUES (?, 'user', 'approve', '', datetime('now'))", (jid,))
        c.commit()

    def finals(self):
        """Scenes that got a NEW final job (scene 5's seeded final_ok is not counted)."""
        rows = self.p.conn.execute("SELECT DISTINCT scene_id FROM jobs WHERE type='video_gen' AND quality_tier='final' AND state='queued'")
        return sorted(r["scene_id"] for r in rows)

    def on(self):
        """Flag two_tier_quality ON for the real core module and the screens; sending is a Mock (never a provider call)."""
        self.submit = mock.Mock(return_value=0)
        for s in (mock.patch.dict(os.environ, {"FEATURE_TWO_TIER_QUALITY": "1", "VIDEO_PROVIDER": "mock"}),
                  mock.patch("core.runner.VideoRunner.submit_pending", self.submit)):
            s.start()
            self.addCleanup(s.stop)

    def open(self, step) -> AppTest:
        with mock.patch.dict(os.environ, dict(V2)):
            at = AppTest.from_file(APP, default_timeout=60).run()
            at.radio(key="step").set_value(at.radio(key="step").options[step]).run()
        self.assertFalse(at.exception, at.exception)
        return at


class FlagOffTests(TwoTierSeed):
    def test_no_module_or_no_flag_means_disabled(self):
        self.assertFalse(Q.enabled())                                       # flag two_tier_quality off by default
        with mock.patch.dict(os.environ, {"FEATURE_TWO_TIER_QUALITY": "1"}), mock.patch.object(Q, "module", return_value=None):
            self.assertFalse(Q.enabled())                                   # flag but no core module → old UI
        self.assertEqual(Q.draft_render_note(self.p.conn, self.pid), "")

    def test_video_screen_unchanged_when_off(self):
        at = self.open(3)
        keys = {b.key for b in at.button}
        self.assertFalse(any(k and k.startswith(("qfinal_", "qpath_")) for k in keys))
        self.assertFalse(any(s.key and s.key.startswith("qpath_") for s in at.selectbox))
        self.assertNotIn("Nháp đã duyệt", md(at))


class VideoScreenTests(TwoTierSeed):
    def test_badges_difficulty_and_path_choice(self):
        self.on()
        at = self.open(3)
        html = md(at)
        for text in ("Nháp đã duyệt", "Nháp · chờ duyệt", "Nháp đã cũ", "Bản cao ✓"):
            self.assertIn(text, html, text)
        self.assertIn("Phức tạp", html)
        self.assertIn("hai người nhảy cùng lúc", html)
        self.assertIn("dữ liệu shot đồng ý", "\n".join(c.value for c in at.caption))
        self.assertTrue({f"vres_{s}" for s in self.sids} <= {s.key for s in at.selectbox})   # 09/10: ô Chất lượng thay ô Cấu hình

    def test_gen_final_only_on_draft_ok_with_price(self):
        self.on()
        at = self.open(3)
        labels = {b.key: b.label for b in at.button}
        self.assertIn(f"qfinal_{self.sids[0]}", labels)
        self.assertRegex(labels[f"qfinal_{self.sids[0]}"], r"≈ \d|chưa có giá")
        for sid in self.sids[1:]:
            self.assertNotIn(f"qfinal_{sid}", labels)                       # draft_review / stale / none / final_ok: no high-tier button
        self.assertIn("không gen bản cao", "\n".join(w.value for w in at.warning))   # draft_stale says why
        next(b for b in at.button if b.key == f"qfinal_{self.sids[0]}").click().run()
        self.assertEqual(self.finals(), [self.sids[0]])                     # one final job, tied to the approved draft
        self.assertEqual(Q.state(self.p.conn, self.sids[0]), "final_running")
        self.assertEqual(self.submit.call_count, 1)                          # request_final only queues; the screen sends once

    def test_batch_button_shows_total_and_asks_first(self):
        self.put(self.sids[3], "draft_ok")
        self.on()
        est = Q.final_estimate(self.p.conn, self.pid)
        self.assertEqual(sorted(est["scenes"]), sorted([self.sids[0], self.sids[3]]))   # only approved, current drafts
        price = f"≈ {est['usd']:.2f} USD (tham khảo)" if est["usd"] is not None else "chưa có giá"
        at = self.open(3)
        btn = next(b for b in at.button if b.key and b.key.startswith(f"qfinal_all_{self.pid}"))
        self.assertIn("Gen bản cao 2 cảnh", btn.label)
        self.assertIn(price, btn.label)
        btn.click().run()
        self.assertEqual(self.finals(), [])                                  # first click only asks
        next(b for b in at.button if b.label.startswith("Có, gen bản cao")).click().run()
        self.assertEqual(self.finals(), sorted([self.sids[0], self.sids[3]]))
        self.assertEqual(self.submit.call_count, 1)

    def test_path_choice_writes_quality_path(self):
        self.on()
        from core import quality_tier
        self.assertTrue(Q.set_quality_path(self.p.conn, self.sids[0], "direct"))
        self.assertEqual(Q.quality_path(connect(self.db), self.sids[0]), "direct")
        self.assertEqual(quality_tier.path(self.p.conn, self.sids[0]), "direct")       # the core reads the person's choice
        self.assertTrue(Q.set_quality_path(self.p.conn, self.sids[0], "auto"))
        self.assertEqual(Q.quality_path(self.p.conn, self.sids[0]), "auto")
        self.assertEqual(quality_tier.path(self.p.conn, self.sids[0]), "draft_first")  # back to the Director's 'complex'
        with self.assertRaises(ValueError):
            Q.set_quality_path(self.p.conn, self.sids[0], "cheap")


class ProgressTests(TwoTierSeed):
    def test_clip_progress_counts_tiers(self):
        self.on()
        frac, counts = Q.clip_progress(self.p.conn, self.pid)
        self.assertLess(frac, 1.0)
        self.assertAlmostEqual(frac, (0.5 + 0.3 + 0.3 + 0 + 1.0) / 5)
        self.assertIn("1 nháp đã duyệt", Q.progress_lines(counts))

    def test_overall_never_100_while_a_draft_remains(self):
        from dashboard.design.screens import shell_parts
        for sid in self.sids:
            self.put(sid, "draft_ok")
        done_all = [("done", "")] * 5 + [("todo", "")]
        with mock.patch("core.lineage.summary", return_value={"total": 5, "images": (5, 0), "motion": (5, 0), "videos": (5, 0)}):
            self.assertEqual(shell_parts.overall_progress(self.p, self.pid, done_all), 1.0)   # flag off: as before
            self.on()
            frac = shell_parts.overall_progress(self.p, self.pid, done_all)
            self.assertLess(frac, 1.0)
            self.assertIn("nháp", shell_parts.progress_details(self.pid, done_all, self.p))
            for sid in self.sids:
                self.put(sid, "final_ok")
            self.assertEqual(shell_parts.overall_progress(self.p, self.pid, done_all), 1.0)

    def test_next_step_not_done_while_drafts(self):
        from dashboard import next_step
        self.on()
        with mock.patch.object(next_step.lineage, "summary", return_value={"total": 5, "images": (5, 0), "motion": (5, 0), "videos": (5, 0)}), \
                mock.patch.object(next_step, "_count", side_effect=lambda c, sql, a: 5 if "FROM scenes" in sql else 0):
            text, level = next_step.next_action(self.p, self.pid, 4, self.data)
        self.assertEqual(level, "todo")
        self.assertIn("nháp", text)


class DraftRenderTests(TwoTierSeed):
    def test_draft_note_and_file_name(self):
        self.on()
        note = Q.draft_render_note(self.p.conn, self.pid)
        self.assertTrue(note.startswith("DRAFT · 3 cảnh còn nháp"), note)
        self.assertEqual(Q.draft_file_name("final.mp4", self.p.conn, self.pid), "final_DRAFT.mp4")
        self.assertIn("DRAFT", Q.delivery_warning(self.p.conn, self.pid))
        for sid in self.sids:
            self.put(sid, "direct_ok")
        self.assertEqual(Q.draft_file_name("final.mp4", self.p.conn, self.pid), "final.mp4")
        self.assertEqual(Q.delivery_warning(self.p.conn, self.pid), "")

    def test_deliver_screen_shows_draft_label(self):
        self.on()
        at = self.open(STEP_DELIVER)
        self.assertIn("DRAFT · 3 cảnh còn nháp", md(at))

    def test_deliver_screen_without_flag_has_no_draft_label(self):
        at = self.open(STEP_DELIVER)
        self.assertNotIn("DRAFT ·", md(at))


if __name__ == "__main__":
    unittest.main()
