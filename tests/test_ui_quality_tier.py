"""N4 (08/10) — UI 2 bậc chất lượng + thanh tiến độ + bản dựng DRAFT (docs/THIET_KE_2_BAC_CHAT_LUONG_VA_NHAC_2026-10-08.md mục 1, 5a.5, 5a.8).

core/quality_tier.py (N1) is faked through sys.modules so the screens are tested against the contract only."""
import json
import os
import sys
import types
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from core import features
from core.db import connect
from core.pipeline import Pipeline
from dashboard import quality_ui as Q
from tests.test_ui_video import APP, STEP_DELIVER, V2, VideoSeed, md

FLAG_META = {"label": "Video 2 bậc chất lượng (nháp → bản cao)", "verified": True, "why": "test"}


def fake_module(states: dict, usd_per_scene: float = 0.9):
    m = types.ModuleType("core.quality_tier")
    m.calls = []
    m.state = lambda conn, sid: states.get(sid, "none")

    def final_estimate(conn, pid):
        ids = [r["id"] for r in conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx", (pid,))
               if states.get(r["id"]) == "draft_ok"]
        return {"usd": usd_per_scene * len(ids), "scenes": ids}
    m.final_estimate = final_estimate
    m.request_final = lambda p, sid, actor: m.calls.append((sid, actor))
    return m


class TwoTierSeed(VideoSeed):
    """VideoSeed's five scenes: 1 draft_ok · 2 draft_review · 3 draft_stale · 4 none · 5 final_ok."""

    def setUp(self):
        super().setUp()
        self.sids = [r["id"] for r in self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx", (self.pid,))]
        self.states = dict(zip(self.sids, ["draft_ok", "draft_review", "draft_stale", "none", "final_ok"]))
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                            (json.dumps({"difficulty": "complex", "difficulty_why": "hai người nhảy cùng lúc",
                                         "difficulty_check": {"score": 4, "factors": ["2 người", "nhảy"], "suggest": "complex",
                                                              "note": "dữ liệu shot đồng ý"}}), self.sids[0]))
        self.p.conn.commit()
        self.qt = fake_module(self.states)

    def on(self):
        """Flag ON + the fake core.quality_tier (a context for AppTest / direct calls)."""
        stack = [mock.patch.dict(sys.modules, {"core.quality_tier": self.qt}),
                 mock.patch.dict(features.FEATURES, {Q.FLAG: FLAG_META}),
                 mock.patch.dict(os.environ, {"FEATURE_TWO_TIER_QUALITY": "1"})]
        for s in stack:
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
        self.assertFalse(Q.enabled())                                       # no flag in FEATURES yet (N1 not merged)
        with mock.patch.dict(features.FEATURES, {Q.FLAG: FLAG_META}), mock.patch.dict(os.environ, {"FEATURE_TWO_TIER_QUALITY": "1"}), \
                mock.patch.object(Q, "module", return_value=None):
            self.assertFalse(Q.enabled())                                   # flag but no core module → old UI
        self.assertEqual(Q.draft_render_note(self.p.conn, self.pid), "")

    def test_video_screen_unchanged_when_off(self):
        with mock.patch.dict(sys.modules, {"core.quality_tier": self.qt}):  # module there, flag absent
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
        self.assertTrue({f"qpath_{s}" for s in self.sids} <= {s.key for s in at.selectbox})

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
        self.assertEqual(self.qt.calls, [(self.sids[0], "user")])

    def test_batch_button_shows_total_and_asks_first(self):
        self.states[self.sids[3]] = "draft_ok"
        self.on()
        at = self.open(3)
        btn = next(b for b in at.button if b.key and b.key.startswith(f"qfinal_all_{self.pid}"))
        self.assertIn("Gen bản cao 2 cảnh", btn.label)
        self.assertIn("≈ 1.80 USD (tham khảo)", btn.label)
        btn.click().run()
        self.assertEqual(self.qt.calls, [])                                  # first click only asks
        next(b for b in at.button if b.label.startswith("Có, gen bản cao")).click().run()
        self.assertEqual(sorted(c[0] for c in self.qt.calls), sorted([self.sids[0], self.sids[3]]))

    def test_path_choice_writes_quality_path(self):
        self.p.conn.execute("ALTER TABLE motion_prompts ADD COLUMN quality_path TEXT NOT NULL DEFAULT 'auto'")
        self.p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, state) VALUES (?, 'x', 'approved')", (self.sids[0],))
        self.p.conn.commit()
        self.assertTrue(Q.set_quality_path(self.p.conn, self.sids[0], "direct"))
        self.assertEqual(Q.quality_path(connect(self.db), self.sids[0]), "direct")
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
            self.states[sid] = "draft_ok"
        done_all = [("done", "")] * 5 + [("todo", "")]
        with mock.patch("core.lineage.summary", return_value={"total": 5, "images": (5, 0), "motion": (5, 0), "videos": (5, 0)}):
            self.assertEqual(shell_parts.overall_progress(self.p, self.pid, done_all), 1.0)   # flag off: as before
            self.on()
            frac = shell_parts.overall_progress(self.p, self.pid, done_all)
            self.assertLess(frac, 1.0)
            self.assertIn("nháp", shell_parts.progress_details(self.pid, done_all, self.p))
            for sid in self.sids:
                self.states[sid] = "final_ok"
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
            self.states[sid] = "direct_ok"
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
