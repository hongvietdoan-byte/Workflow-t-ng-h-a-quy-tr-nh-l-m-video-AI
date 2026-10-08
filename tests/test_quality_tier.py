"""N1 — lõi 2 bậc chất lượng video (người dùng chốt 08/10, docs/THIET_KE_2_BAC_CHAT_LUONG_VA_NHAC_2026-10-08.md mục 5a).

Cờ two_tier_quality TẮT = hành vi y như cũ (kể cả "Thử rẻ"); BẬT = bỏ qua test_quality, nháp → duyệt → bản cao, trần nháp 2 / bản cao 1,
gen lại y nguyên bị từ chối (CHUAN_XAY_DUNG luật 3)."""
import json
import tempfile
import time
import unittest
from unittest import mock

from core import cost, diag, lineage, llm_io, quality_tier, regen
from core.adapters.clipai import ClipAIVideoProvider
from core.db import connect
from core.pipeline import AUTO_LIMIT_CODE, Pipeline
from core.runner import VideoRunner
from core.states import InvalidTransition

ON = mock.patch("core.quality_tier.enabled", return_value=True)
OFF = mock.patch("core.quality_tier.enabled", return_value=False)


def _provider():
    return ClipAIVideoProvider("tok", "https://example.invalid", lambda *a, **k: None)


class Base(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("N1")
        self.s1 = self.p.create_scene(self.pid, 1, "Shot 1")
        self.img = self.p.create_job(self.s1)
        self.p.start(self.img)
        self.p.succeed(self.img)
        self.p.approve(self.img)
        llm_io.store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": 1, "motion_prompt": "she dances", "duration_sec": 4}]})
        llm_io.approve_motion_prompt(self.p, self.s1)
        self.p.conn.execute("UPDATE motion_prompts SET video_model='seedance-2.5' WHERE scene_id=?", (self.s1,))
        self.p.conn.commit()

    def set_difficulty(self, level, sid=None):
        sid = sid or self.s1
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()[0] or "{}")
        data.update(difficulty=level, difficulty_why="test")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), sid))
        self.p.conn.commit()

    def stamp(self, jid, model="seedance-2.5", ext=None):
        """What the runner writes when a clip is sent: the input stamp, the picture, the model, the task id."""
        mp = self.p.conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (self.s1,)).fetchone()
        self.p.conn.execute("UPDATE jobs SET input_hash=?, source_job_id=?, model=?, external_id=? WHERE id=?",
                            (lineage.video_input_hash(mp, None), self.img, model, ext or f"seedance:t{jid}", jid))
        self.p.conn.commit()

    def made(self, jid):
        self.stamp(jid)
        self.p.start(jid)
        self.p.succeed(jid)

    def approved_draft(self):
        jid = self.p.create_job(self.s1, "video_gen")
        self.made(jid)
        self.p.approve(jid, "user")
        return jid

    def tier(self, jid):
        return self.p.job(jid)["quality_tier"]


class FlagOffTests(Base):
    def test_flag_is_off_and_unverified(self):
        from core import features
        self.assertFalse(features.FEATURES["two_tier_quality"]["verified"])

    def test_off_changes_nothing(self):
        with OFF:
            self.p.conn.execute("UPDATE projects SET test_quality=1 WHERE id=?", (self.pid,))
            self.p.conn.commit()
            jid = self.p.create_job(self.s1, "video_gen")
            self.assertIsNone(self.tier(jid))
            self.assertEqual(self.p.auto_limit(self.p.job(jid)), 2)
            proj = self.p.project(self.pid)
            self.assertTrue(quality_tier.cheap_mode(proj))                       # "Thử rẻ" still works
            kw = VideoRunner(self.p, _provider(), self.data)._submit_kwargs(self.p.job(jid))
            self.assertEqual(kw.get("kling_mode"), "std")
            self.assertNotIn("draft", kw)
            self.made(jid)
            self.assertEqual(self.p.reject(jid, "user"), "rejected")            # a plain redo is not refused with the flag off


class PathAndStateTests(Base):
    def test_on_ignores_cheap_mode(self):
        with ON:
            self.p.conn.execute("UPDATE projects SET test_quality=1 WHERE id=?", (self.pid,))
            self.p.conn.commit()
            self.assertFalse(quality_tier.cheap_mode(self.p.project(self.pid)))
            from core import model_router
            self.assertEqual(model_router.scene_choice(self.p.conn, self.s1)["model"], "seedance-2.5")

    def test_path_from_director_label_and_person_override(self):
        with ON:
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")       # no label → draft first
            self.set_difficulty("unknown")
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")
            self.set_difficulty("complex")
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")
            self.set_difficulty("easy")
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "direct")
            self.assertEqual(self.tier(self.p.create_job(self.s1, "video_gen")), "direct")
            quality_tier.set_path(self.p.conn, self.s1, "draft_first")                    # the person wins
            self.assertEqual(self.tier(self.p.create_job(self.s1, "video_gen")), "draft")

    def test_eight_states(self):
        with ON:
            st = lambda: quality_tier.state(self.p.conn, self.s1)   # noqa: E731
            self.assertEqual(st(), "none")
            d = self.p.create_job(self.s1, "video_gen")
            self.assertEqual(self.tier(d), "draft")
            self.assertEqual(st(), "draft_running")
            self.made(d)
            self.assertEqual(st(), "draft_review")
            self.p.approve(d, "user")
            self.assertEqual(st(), "draft_ok")
            self.p.conn.execute("UPDATE motion_prompts SET motion_prompt='she dances and jumps' WHERE scene_id=?", (self.s1,))
            self.p.conn.commit()
            self.assertEqual(st(), "draft_stale")
            self.p.conn.execute("UPDATE motion_prompts SET motion_prompt='she dances' WHERE scene_id=?", (self.s1,))
            self.p.conn.commit()
            f = quality_tier.request_final(self.p, self.s1)
            self.assertEqual((self.tier(f), self.p.job(f)["draft_job_id"], self.p.job(f)["retry_count"]), ("final", d, 0))
            self.assertEqual(st(), "final_running")
            self.made(f)
            self.p.approve(f, "user")
            self.assertEqual(st(), "final_ok")
            s2 = self.p.create_scene(self.pid, 2, "Shot 2")
            self.set_difficulty("easy", s2)
            j = self.p.create_job(s2, "video_gen")
            self.assertEqual(self.tier(j), "direct")
            self.p.start(j)
            self.p.succeed(j)
            self.p.approve(j, "user")
            self.assertEqual(quality_tier.state(self.p.conn, s2), "direct_ok")

    def test_a_draft_only_the_qc_approved_still_waits_for_the_person(self):
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            self.made(d)
            self.p.approve(d, "ai_agent")
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "draft_review")


class FinalGateTests(Base):
    def test_no_final_before_the_draft_is_approved(self):
        with ON:
            with self.assertRaises(ValueError):
                quality_tier.request_final(self.p, self.s1)
            d = self.p.create_job(self.s1, "video_gen")
            self.made(d)
            with self.assertRaises(ValueError) as e:
                quality_tier.request_final(self.p, self.s1)
            self.assertIn("chưa được người duyệt", str(e.exception))

    def test_no_final_from_an_outdated_draft_and_the_runner_blocks_it(self):
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            self.p.conn.execute("UPDATE motion_prompts SET duration_sec=6 WHERE scene_id=?", (self.s1,))
            self.p.conn.commit()
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "final_running")
            why = VideoRunner(self.p, _provider(), self.data)._blocked(self.p.job(f))
            self.assertIn("bản cao bị chặn", why)
            self.assertIn("đầu vào đã đổi", why)
            with self.assertRaises(ValueError):
                quality_tier.request_final(self.p, self.s1)


class RunnerTierTests(Base):
    def test_draft_goes_as_the_seedance_2_5_sample_at_480p(self):
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            vr = VideoRunner(self.p, _provider(), self.data)
            kw = vr._submit_kwargs(self.p.job(d))
            self.assertEqual((kw.get("draft"), kw.get("resolution")), (True, "480p"))
            self.assertEqual(vr._usage(("i", "p", None, 4, "seedance-2.5"), kw)[1], "480p")      # ledger tier

    def test_other_models_draft_at_their_lowest_tier(self):
        self.assertEqual(quality_tier.low_tier({}, "kling")["kling_mode"], "std")
        self.assertEqual(quality_tier.low_tier({"resolution": "1080p"}, "seedance")["resolution"], "480p")
        self.assertNotIn("draft", quality_tier.low_tier({}, "seedance"))

    def test_final_from_a_live_2_5_draft_uses_draft_task_at_1080p(self):
        with ON:
            d = self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            prov = _provider()
            prov.task_usage = mock.Mock(return_value={"is_draft": True, "draft_expired_at": (time.time() + 3600) * 1000})
            prov.submit_final_from_sample = mock.Mock(return_value="seedance:final")
            prov.submit = mock.Mock(return_value="seedance:resend")
            vr = VideoRunner(self.p, prov, self.data)
            kw = vr._submit_kwargs(self.p.job(f))
            self.assertEqual(kw["_from_sample"], f"seedance:t{d}")
            self.assertEqual(self.send(vr), 1)
            self.assertEqual(self.p.job(f)["external_id"], "seedance:final")
            prov.submit_final_from_sample.assert_called_once_with(f"seedance:t{d}", resolution="1080p")
            prov.submit.assert_not_called()
            row = self.p.conn.execute("SELECT model, tier FROM usage_events WHERE job_id=?", (f,)).fetchone()
            self.assertEqual((row["model"], row["tier"]), (quality_tier.SAMPLE_MODEL, "1080p"))   # booked at the final's tier

    def send(self, vr):
        """The runner's real send loop, with the inputs (picture file, lint, stamp, money check) stubbed."""
        with mock.patch.object(vr, "_submit_args", return_value=("i.png", "she dances", None, 4, "seedance-2.5")), \
                mock.patch.object(vr, "_blocked", return_value=None), mock.patch.object(vr, "_stamp", return_value={}), \
                mock.patch.object(vr, "_over_budget", return_value=None), mock.patch.object(vr, "_wait", return_value=False):
            return vr._submit_pending(self.pid)

    def test_expired_draft_is_not_resent_unasked(self):
        """F3 (#24): an expired 2.5 sample cannot be upgraded — the final is NOT resent on its own (it was, at 720p, other content);
        it fails with the reason, and the next request needs the person's explicit yes (request_final confirm_new)."""
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            prov = _provider()
            prov.task_usage = mock.Mock(return_value={"is_draft": True, "draft_expired_at": time.time() - 10})
            prov.submit = mock.Mock(return_value="seedance:resend")
            prov.submit_final_from_sample = mock.Mock()
            vr = VideoRunner(self.p, prov, self.data)
            kw = vr._submit_kwargs(self.p.job(f))
            self.assertNotIn("_from_sample", kw)
            self.assertIn(quality_tier.NEED_CONFIRM, kw["_hold"])
            self.assertEqual(self.send(vr), 0)
            prov.submit.assert_not_called()
            prov.submit_final_from_sample.assert_not_called()
            self.assertEqual(self.p.job(f)["state"], "failed")
            with self.assertRaises(ValueError) as e:                          # the draft is now known not upgradable
                quality_tier.request_final(self.p, self.s1)
            self.assertIn(quality_tier.NEW_GEN, str(e.exception))
            self.assertIn("USD", str(e.exception))
            f2 = quality_tier.request_final(self.p, self.s1, confirm_new=True)
            self.assertTrue(json.loads(self.p.job(f2)["confirm_new"])["usd"] > 0)
            vr = VideoRunner(self.p, prov, self.data)
            self.assertEqual(self.send(vr), 1)
            self.assertEqual(self.p.job(f2)["external_id"], "seedance:resend")
            # the highest tier the model's rules allow for a direct send (provider_rules.json) — not the draft's 480p
            self.assertEqual(prov.submit.call_args.kwargs.get("resolution"), quality_tier.final_resolution("seedance-2.5"))
            self.assertNotEqual(prov.submit.call_args.kwargs.get("resolution"), "480p")
            self.assertNotIn("draft", prov.submit.call_args.kwargs)
            row = self.p.conn.execute("SELECT severity, message FROM diag_events WHERE code='final_resend' ORDER BY id DESC").fetchone()
            self.assertEqual(row["severity"], "warn")
            self.assertIn(quality_tier.NEW_GEN, row["message"])

    def test_final_of_another_model_needs_the_persons_yes(self):
        with ON:
            d = self.approved_draft()
            self.p.conn.execute("UPDATE jobs SET model='kling' WHERE id=?", (d,))
            self.p.conn.commit()
            with self.assertRaises(ValueError):
                quality_tier.request_final(self.p, self.s1)
            f = quality_tier.request_final(self.p, self.s1, confirm_new=True)
            route = quality_tier.final_route(self.p.conn, self.p.job(f), _provider())
            self.assertIsNone(route["from_sample"])
            self.assertIn("kling", route["why"])
            self.assertIsNone(quality_tier.needs_confirm(self.p.job(f), route))


class RetryCapTests(Base):
    def test_draft_chain_stops_after_two_redos_and_tells_the_person(self):
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            self.made(d)
            self.assertEqual(self.p.reject(d, "ai_agent", "QC 0.6", fix="Keep the red hood on"), "rejected")
            d2 = self.p.conn.execute("SELECT MAX(id) FROM jobs").fetchone()[0]
            self.assertEqual((self.tier(d2), self.p.job(d2)["retry_count"]), ("draft", 1))
            self.p.conn.execute("UPDATE jobs SET retry_count=2 WHERE id=?", (d2,))
            self.p.conn.commit()
            self.made(d2)
            self.assertEqual(self.p.reject(d2, "ai_agent", "QC 0.6", fix="Hands stay on the rail"), "escalated")
            self.assertEqual(self.p.conn.execute("SELECT MAX(id) FROM jobs").fetchone()[0], d2)        # no third redo
            said = self.p.conn.execute("SELECT message FROM diag_events WHERE code=?", (AUTO_LIMIT_CODE,)).fetchall()
            self.assertTrue(said and "bản NHÁP" in said[-1]["message"])
            self.assertEqual(self.p.conn.execute("SELECT state FROM scenes WHERE id=?", (self.s1,)).fetchone()[0],
                             "needs_attention")

    def test_final_is_redone_at_most_once(self):
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            self.assertEqual(self.p.auto_limit(self.p.job(f)), 1)
            self.made(f)
            self.assertEqual(self.p.reject(f, "ai_agent", "QC 0.6", fix="Keep the red hood on"), "rejected")
            f2 = self.p.conn.execute("SELECT MAX(id) FROM jobs").fetchone()[0]
            self.assertEqual((self.tier(f2), self.p.job(f2)["retry_count"]), ("final", 1))
            self.made(f2)
            self.assertEqual(self.p.reject(f2, "ai_agent", "QC 0.6", fix="Hands stay on the rail"), "escalated")
            # the redo of a final carries a fix → resent from the input, not from the draft (draft_task takes no prompt)
            self.assertIsNone(quality_tier.final_route(self.p.conn, self.p.job(f2), _provider())["from_sample"])


class SameInputRedoTests(Base):
    def test_person_redo_without_any_fix_on_the_same_input_is_refused(self):
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            self.made(d)
            with self.assertRaises(InvalidTransition) as e:
                self.p.reject(d, "user")
            self.assertIn("luật 3", str(e.exception))
            self.assertEqual(self.p.state(d).value, "succeeded")                  # nothing moved
            with self.assertRaises(ValueError):
                regen.regenerate_video(self.p, self.data, d)
            self.assertEqual(self.p.reject(d, "user", "Keep the red hood on"), "rejected")   # with the person's fix: fine

    def test_redo_after_the_input_changed_needs_no_fix(self):
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            self.made(d)
            self.p.conn.execute("UPDATE motion_prompts SET motion_prompt='she dances slowly' WHERE scene_id=?", (self.s1,))
            self.p.conn.commit()
            self.assertEqual(self.p.reject(d, "user"), "rejected")

    def test_the_same_fix_again_on_the_same_input_is_refused_and_the_qc_holds_it(self):
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            self.p.conn.execute("UPDATE jobs SET retry_reason='Keep the red hood on' WHERE id=?", (d,))
            self.p.conn.commit()
            self.made(d)
            self.assertEqual(self.p.reject(d, "ai_agent", "QC 0.6", fix="Keep the red hood on"), "needs_review")
            self.assertEqual(self.p.state(d).value, "pending_review")
            self.assertEqual(self.p.job(d)["escalated"], 1)

    def test_a_provider_failure_is_still_resent_unchanged(self):
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            self.stamp(d)
            self.p.start(d)
            self.p.fail(d, "timeout: provider busy")
            self.assertIsNotNone(self.p.retry(d, "gửi lại", by_user=True))

    def test_restart_of_a_stopped_draft_chain_needs_a_changed_input(self):
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            self.made(d)
            self.p.reject(d, "user", "Keep the hood", respawn=False)
            self.p.conn.execute("UPDATE jobs SET escalated=1 WHERE id=?", (d,))
            self.p.conn.commit()
            with self.assertRaises(InvalidTransition):
                self.p.restart_job(d)
            self.p.conn.execute("UPDATE motion_prompts SET motion_prompt='she waves' WHERE scene_id=?", (self.s1,))
            self.p.conn.commit()
            self.assertEqual(self.tier(self.p.restart_job(d)), "draft")


class FinalEstimateTests(Base):
    def test_sum_of_the_finals_still_to_make(self):
        with ON:
            self.approved_draft()
            s2 = self.p.create_scene(self.pid, 2, "Shot 2")
            self.set_difficulty("easy", s2)
            self.p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, duration_sec, state) VALUES (?,?,?,?)",
                                (s2, "walks", 4, "approved"))
            self.p.conn.commit()
            est = quality_tier.final_estimate(self.p.conn, self.pid)
            self.assertEqual([s["scene_id"] for s in est["scenes"]], [self.s1])     # the easy shot goes direct: no final to make
            want = cost.seedance_estimate(quality_tier.SAMPLE_MODEL, "1080p", "16:9", 4.0)
            self.assertAlmostEqual(est["usd"], round(want, 4))
            f = quality_tier.request_final(self.p, self.s1)
            self.assertTrue(f)
            self.assertEqual(quality_tier.final_estimate(self.p.conn, self.pid)["scenes"], [])


if __name__ == "__main__":
    unittest.main()
