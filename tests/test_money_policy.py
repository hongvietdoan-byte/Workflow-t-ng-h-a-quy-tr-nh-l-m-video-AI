"""S14.16 — chính sách tiền mới (docs/KE_HOACH_NANG_CAP_DASHBOARD_2026-10-03.md mục 6c, người dùng chốt 04/10):
trần tiền chỉ CẢNH BÁO (có số liệu, ghi diag) — chặn chỉ khi hết tiền thật / dự án tạm dừng / trần job ngày của autopilot; ước tính
tính dư; tự gen lại ≤ 3 lần mỗi ẢNH, ≤ 2 lần mỗi VIDEO (người dùng bấm tay không giới hạn, đặt lại bộ đếm). 0 USD, không gọi API thật."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import budget, inbox, llm_runner, money_policy, money_reset, project_budget, spend_gate
from core.adapters.http import HttpResponse
from core.db import connect
from core import pipeline as _pipeline
from core.pipeline import Pipeline, PipelinePaused
from core.states import JobState

ON = {"FEATURE_PROJECT_BUDGET": "1"}
GOOD = {"character": 0.9, "hands_face": 0.9, "composition": 0.9, "mood": 0.9}


def lock(p, pid, images=5.0, videos=5.0, total=100.0):
    project_budget.approve(p, pid, "a@x", {"stages": {k: {"cap": images if k == "images" else videos if k == "videos" else 5.0}
                                                      for k in project_budget.STAGES}, "total": total})


def warnings(conn):
    return [r["message"] for r in conn.execute("SELECT message FROM diag_events WHERE code=? ORDER BY id", (money_policy.WARN_CODE,))]


class GateWarnsInsteadOfRefusing(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("g")

    def test_the_trial_cap_warns_with_numbers_and_the_send_goes(self):
        budget.restart(self.p.conn, usd=0.05)                        # 2 × 0.052 > 0.05
        with spend_gate.spend(self.p.conn, "image", "deepix", project_id=self.pid, model="gpt-image-2", units=2,
                              ledger_stage="character_set") as slot:
            self.assertIsNone(slot.over)
            slot.send(lambda: "task")
            slot.record()
        self.assertIn("đã chi ≈ $0.00", slot.warning)
        self.assertIn("mức dự tính $0.05", slot.warning)
        self.assertIn("lượt này ≈ $0.10 (ước tính)", slot.warning)
        self.assertIn("vượt 108 %", slot.warning)
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0], 1)
        self.assertTrue(warnings(self.p.conn))

    @mock.patch.dict(os.environ, ON)
    def test_a_locked_project_over_its_stage_warns_and_goes(self):
        lock(self.p, self.pid, videos=1.0)
        with spend_gate.spend(self.p.conn, "video", "clipai", project_id=self.pid, model="kling-v3-omni", tier="std",
                              units=15) as slot:                    # 15 s × 0.08 = 1.20 > 1.00
            self.assertIsNone(slot.over)
        self.assertIn("Video", slot.warning)
        self.assertIn("mức dự tính $1.00", slot.warning)

    @mock.patch.dict(os.environ, ON)
    def test_an_unpriced_model_of_a_locked_project_is_estimated_high_and_goes(self):
        lock(self.p, self.pid, videos=100.0)
        with spend_gate.spend(self.p.conn, "video", "clipai", project_id=self.pid, model="kling-v3-omni", tier="8k",
                              units=5) as slot:
            self.assertIsNone(slot.over)
        self.assertIn("thiếu giá: kling-v3-omni:8k", slot.warning)

    def test_out_of_credit_still_blocks_with_the_reason(self):
        budget.halt(self.p.conn, "clipai", "insufficient balance")
        with spend_gate.spend(self.p.conn, "video", "clipai", project_id=self.pid, model="kling-v3-omni", tier="std",
                              units=5) as slot:
            self.assertIn("HẾT TIỀN", slot.over)
            with self.assertRaises(spend_gate.SpendRefused):
                slot.send(lambda: "never")

    def test_a_paused_project_still_blocks(self):
        self.p.set_paused(self.pid, True)
        with spend_gate.spend(self.p.conn, "image", "deepix", project_id=self.pid, model="gpt-image-2") as slot:
            self.assertTrue(slot.paused)
            self.assertIn("đã chi ≈ $0.00", slot.over)                       # a stop says its numbers and how to open
            self.assertIn("lượt bị chặn: ảnh gpt-image-2 ≈ $0.05", slot.over)
            self.assertIn("bỏ tạm dừng", slot.over)
            with self.assertRaises(PipelinePaused):
                slot.raise_if_over("x")

    def test_budget_checks_only_block_out_of_credit(self):
        budget.restart(self.p.conn, usd=0.01)
        self.assertIsNone(budget.check_image(self.p.conn, "deepix", "gpt-image-2"))
        self.assertIsNone(budget.check_video(self.p.conn, "clipai", "kling-v3-omni", "std", 10))
        self.assertIn("vượt", budget.warn_image(self.p.conn, "deepix", "gpt-image-2"))
        self.assertIn("vượt", budget.warn_video(self.p.conn, "clipai", "kling-v3-omni", "std", 10))
        budget.halt(self.p.conn, "deepix", "no money")
        self.assertIn("HẾT TIỀN", budget.check_image(self.p.conn, "deepix", "gpt-image-2"))

    @mock.patch.dict(os.environ, ON)
    def test_project_budget_check_never_refuses_and_warning_says_the_numbers(self):
        lock(self.p, self.pid, images=0.0)
        self.assertIsNone(project_budget.check(self.p.conn, self.pid, "images", 0.05))
        self.assertIsNone(project_budget.check(self.p.conn, self.pid, "images", None))
        why = project_budget.warning(self.p.conn, self.pid, "images", 0.05)
        self.assertIn("Ảnh", why)
        self.assertIn("lượt này ≈ $0.05", why)


class Estimates(unittest.TestCase):
    PRICING = {"per_image": {"a": 0.05, "b": 0.10}, "per_video_second": {"kling:std": 0.08, "kling:pro": 0.1, "seed:720p": 0.12,
               "big:1080p": 0.5}, "per_video_clip": {}, "per_audio": {}, "_unverified_models": ["seed*"]}

    def test_a_missing_tier_takes_the_highest_price_of_the_model_times_the_safety_factor(self):
        e = money_policy.estimate("video", "kling", "4k", 5, self.PRICING)
        self.assertAlmostEqual(e["usd"], 0.1 * 5 * money_policy.SAFETY_FACTOR)
        self.assertEqual(e["missing"], "kling:4k")

    def test_a_missing_model_takes_the_highest_of_its_kind(self):
        self.assertAlmostEqual(money_policy.estimate("video", "new", "720p", 2, self.PRICING)["usd"], 0.5 * 2 * 1.5)
        self.assertAlmostEqual(money_policy.estimate("image", "z", None, 1, self.PRICING)["usd"], 0.10 * 1.5)

    def test_an_unverified_price_keeps_its_margin(self):
        e = money_policy.estimate("video", "seed", "720p", 5, self.PRICING)
        self.assertAlmostEqual(e["usd"], 0.12 * 5 * project_budget.UNVERIFIED_MARGIN)
        self.assertIsNone(e["missing"])
        self.assertAlmostEqual(money_policy.estimate("video", "seed", "1080p", 5, self.PRICING)["usd"],
                               0.12 * 5 * 1.5 * project_budget.UNVERIFIED_MARGIN)

    def test_levels(self):
        self.assertEqual(money_policy.level(0.9, 1.0), "ok")
        self.assertEqual(money_policy.level(1.0, 1.0), "warn")
        self.assertEqual(money_policy.level(1.5, 1.0), "danger")
        self.assertEqual(money_policy.level(5, None), "ok")


def _client(calls, db, usage=(20000, 2000)):
    def send(method, url, headers, body, timeout):
        calls.append(1)
        return HttpResponse(200, json.dumps({"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn",
                                             "usage": {"input_tokens": usage[0], "output_tokens": usage[1]}}).encode())
    return llm_runner.AnthropicClient("sk-test", "claude-sonnet-5", transport=send, sleep=lambda s: None, ledger=db)


class ClaudeCapsWarn(unittest.TestCase):
    def setUp(self):
        self.db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        self.conn = connect(self.db)
        self.msgs = [{"role": "user", "content": [{"type": "text", "text": "x"}]}]

    def test_the_claude_cap_warns_and_the_call_goes(self):
        budget.save(self.conn, llm_usd=0.01)
        calls = []
        _client(calls, self.db).converse(self.msgs, [], max_tokens=4000)
        self.assertEqual(len(calls), 1)
        self.assertIsNone(budget.check_llm(self.conn, 5.0))
        self.assertIn("Claude", budget.warn_llm(self.conn, 5.0))
        self.assertTrue(warnings(self.conn))

    def test_a_task_cap_warns_and_the_calls_go(self):
        calls = []
        c = _client(calls, self.db)
        with llm_runner.spend_cap(0.07, "một cảnh") as cap:
            for _ in range(3):
                c.converse(self.msgs, [], max_tokens=4000)
        self.assertEqual(len(calls), 3)
        self.assertAlmostEqual(cap["spent"], 0.18, places=3)
        self.assertTrue(any("một cảnh" in w for w in warnings(self.conn)))

    def test_a_call_over_the_per_call_mark_warns_and_goes(self):
        calls = []
        _client(calls, self.db).converse(self.msgs, [], max_tokens=200000)
        self.assertEqual(len(calls), 1)

    def test_an_unpriced_claude_model_is_estimated_high_and_goes(self):
        calls = []

        def send(method, url, headers, body, timeout):
            calls.append(1)
            return HttpResponse(200, json.dumps({"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn",
                                                 "usage": {"input_tokens": 10, "output_tokens": 10}}).encode())
        llm_runner.AnthropicClient("sk-test", "claude-unknown-9", transport=send, sleep=lambda s: None, ledger=self.db).complete("x")
        self.assertEqual(len(calls), 1)
        self.assertTrue(any("claude-unknown-9" in w for w in warnings(self.conn)))

    def test_anthropic_out_of_credit_still_blocks(self):
        budget.halt(self.conn, "anthropic", "credit balance too low")
        calls = []
        with self.assertRaises(llm_runner.LlmError) as e:
            _client(calls, self.db).complete("x")
        self.assertEqual(e.exception.code, "out_of_credit")
        self.assertEqual(calls, [])


class AutopilotStopsOnlyWhenClaudeCannotAnswer(unittest.TestCase):
    def test_a_budget_code_does_not_stop_the_run_but_out_of_credit_does(self):
        from core import autopilot
        autopilot._stop_if_claude_blocked([(1, llm_runner.fail_text(llm_runner.LlmError("trần", code="budget")))])
        with self.assertRaises(autopilot._Stop) as e:
            autopilot._stop_if_claude_blocked([(1, llm_runner.fail_text(llm_runner.LlmError("x", code="out_of_credit")))])
        self.assertIn("Hết tiền", str(e.exception))


class DailyCapSaysTheNumbers(unittest.TestCase):
    def test_the_daily_cap_stop_says_sends_cap_money_and_how_to_open(self):
        from core import autopilot, cost
        p = Pipeline(connect())
        pid = p.create_project("d")
        for _ in range(3):
            cost.record_usage(p.conn, None, "image", "deepix", "gpt-image-2", "1k", 1, "image", project_id=pid)
        with mock.patch.dict(os.environ, {"AUTOPILOT_DAILY_JOBS": "3"}), self.assertRaises(autopilot._Stop) as e:
            autopilot._daily_cap(p)
        text = str(e.exception)
        self.assertIn("trong ngày", text)
        self.assertIn("3 lượt", text)
        self.assertIn("trần 3", text)
        self.assertIn("đã chi hôm nay ≈ $0.16", text)
        self.assertIn("AUTOPILOT_DAILY_JOBS", text)


class AutoRegenLimit(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("r", "auto", 0.85, 9)

    def _done(self, scene, kind="image_gen", job=None):
        job = job or self.p.create_job(scene, kind)
        self.p.start(job)
        self.p.succeed(job)
        return job

    def _child(self, job):
        row = self.p.conn.execute("SELECT id FROM jobs WHERE parent_job_id=? ORDER BY id DESC", (job,)).fetchone()
        return row and row["id"]

    def test_the_limits_live_in_one_place(self):
        self.assertEqual(getattr(_pipeline, "AUTO_REGEN_LIMIT", None), {"image_gen": 3, "video_gen": 2})

    def test_qc_redraws_a_picture_at_most_three_times(self):
        job = self._done(self.p.create_scene(self.pid, 1))
        results = []
        for n, fault in enumerate(["character", "hands_face", "composition", "mood"]):
            results.append(self.p.apply_qc(job, dict(GOOD, **{fault: 0.1}), issues=f"fix {n}"))
            child = self._child(job)
            if not child:
                break
            job = self._done(None, job=child)
        self.assertEqual(results, ["rejected", "rejected", "rejected", "needs_review"])
        self.assertEqual(self.p.job(job)["escalated"], 1)
        self.assertTrue(self.p.conn.execute("SELECT 1 FROM diag_events WHERE code='auto_regen_limit'").fetchone())

    def test_a_clip_is_retried_by_the_machine_at_most_twice(self):
        job = self.p.create_job(self.p.create_scene(self.pid, 1), "video_gen")
        made = 0
        while True:
            self.p.start(job)
            self.p.fail(job, "timeout")
            nxt = self.p.retry(job, "timeout")
            if nxt is None:
                break
            made, job = made + 1, nxt
        self.assertEqual(made, 2)
        self.assertEqual(self.p.job(job)["escalated"], 1)

    def test_a_person_rejecting_by_hand_is_never_capped_and_resets_the_count(self):
        job = self._done(self.p.create_scene(self.pid, 1))
        for _ in range(6):
            self.assertEqual(self.p.reject(job, "user", "sai"), "rejected")
            job = self._done(None, job=self._child(job))
        self.assertEqual(self.p.job(job)["retry_count"], 0)
        self.assertEqual(self.p.apply_qc(job, dict(GOOD, mood=0.1), issues="fix"), "rejected")   # the machine may redraw again

    def test_a_person_pressing_resend_is_not_capped(self):
        job = self.p.create_job(self.p.create_scene(self.pid, 1), "video_gen")
        for _ in range(4):
            self.p.start(job)
            self.p.fail(job, "boom")
            job = self.p.retry(job, "gửi lại", by_user=True)
            self.assertIsNotNone(job)

    def test_the_inbox_asks_the_person_after_the_limit(self):
        job = self.p.create_job(self.p.create_scene(self.pid, 1), "video_gen")
        while job is not None:
            self.p.start(job)
            self.p.fail(job, "timeout")
            job = self.p.retry(job, "timeout")
        texts = [i["text"] for i in inbox.items(self.p.conn, "a@x")]
        self.assertTrue(any("Cần bạn quyết — đã tự gen lại 2 lần" in t for t in texts), texts)


class EveryAutoPathIsCounted(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("r", "human_qc", 0.85, 9)

    def test_every_retry_button_of_the_dashboard_is_a_persons(self):
        import re
        root = os.path.join(os.path.dirname(__file__), "..", "dashboard")
        bad = []
        for dirpath, _, files in os.walk(root):
            for f in files:
                if not f.endswith(".py"):
                    continue
                src = open(os.path.join(dirpath, f), encoding="utf-8").read()
                for m in re.finditer(r"p\.retry\((?:[^()]|\([^()]*\))*\)", src):
                    if "by_user=True" not in m.group(0):
                        bad.append(f"{f}: {m.group(0)[:80]}")
        self.assertEqual(bad, [])

    def test_the_automatic_plate_fallback_regeneration_is_counted(self):
        from core import regen
        sid = self.p.create_scene(self.pid, 1)
        job = self.p.create_job(sid, "video_gen")
        data = tempfile.mkdtemp()
        for n in range(3):
            self.p.start(job)
            self.p.succeed(job)
            if n < 2:
                job = regen.regenerate_video(self.p, data, job, "nền vẽ lại", auto=True)
        self.assertEqual(self.p.job(job)["retry_count"], 2)
        self.assertIsNone(regen.regenerate_video(self.p, data, job, "nền vẽ lại", auto=True))     # clip limit 2: none made
        self.assertTrue(self.p.conn.execute("SELECT 1 FROM diag_events WHERE code='auto_regen_limit' AND job_id=?", (job,)).fetchone())
        new = regen.regenerate_video(self.p, data, job, "người dùng gen lại")                     # a person: never capped
        self.assertEqual(self.p.job(new)["retry_count"], 0)

    def test_the_automatic_set_check_redo_is_counted(self):
        sid = self.p.create_scene(self.pid, 1)
        job = self.p.create_job(sid)
        for _ in range(3):
            self.p.start(job)
            self.p.succeed(job)
            self.p.approve(job)
            self.assertEqual(self.p.reopen_approved(job, "lệch bộ", fix="match the set", auto=True), "rejected")
            job = self.p.conn.execute("SELECT id FROM jobs WHERE parent_job_id=?", (job,)).fetchone()["id"]
        self.p.start(job)
        self.p.succeed(job)
        self.p.approve(job)
        self.assertEqual(self.p.reopen_approved(job, "lệch bộ", fix="match the set", auto=True), "escalated")
        self.assertEqual(self.p.state(job), JobState.APPROVED)                                     # nothing reopened


class InboxOnlyForTheLimit(unittest.TestCase):
    """Rà soát S14.16 #2/#3: 📥 "đã tự gen lại N lần" shows for a FINISHED job at the limit too, and never for a job held for another
    reason (QC without a fix, a failure that is not temporary)."""

    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("i", "human_qc", 0.85, 9)

    def limit_items(self):
        return [i["text"] for i in inbox.items(self.p.conn, "a@x") if "đã tự gen lại" in i["text"]]

    def test_a_finished_clip_at_its_limit_is_listed_and_its_scene_not_blocked(self):
        from core import regen
        sid = self.p.create_scene(self.pid, 1)
        job = self.p.create_job(sid, "video_gen")
        data = tempfile.mkdtemp()
        for n in range(3):
            self.p.start(job)
            self.p.succeed(job)
            if n < 2:
                job = regen.regenerate_video(self.p, data, job, "nền", auto=True)
        self.assertIsNone(regen.regenerate_video(self.p, data, job, "nền", auto=True))
        self.assertEqual(self.p.state(job), JobState.SUCCEEDED)                        # the finished clip is kept as it is
        self.assertEqual(self.p.conn.execute("SELECT state FROM scenes WHERE id=?", (sid,)).fetchone()[0], "ready")
        self.assertTrue(any("đã tự gen lại 2 lần" in t for t in self.limit_items()), self.limit_items())

    def test_an_approved_picture_at_its_limit_is_listed(self):
        sid = self.p.create_scene(self.pid, 1)
        job = self.p.create_job(sid)
        for _ in range(3):
            self.p.start(job)
            self.p.succeed(job)
            self.p.approve(job)
            self.p.reopen_approved(job, "lệch", fix="match", auto=True)
            job = self.p.conn.execute("SELECT id FROM jobs WHERE parent_job_id=?", (job,)).fetchone()["id"]
        self.p.start(job)
        self.p.succeed(job)
        self.p.approve(job)
        self.assertEqual(self.p.reopen_approved(job, "lệch", fix="match", auto=True), "escalated")
        self.assertTrue(any("đã tự gen lại 3 lần" in t for t in self.limit_items()), self.limit_items())

    def test_the_set_check_block_at_the_limit_goes_to_the_inbox(self):
        from core import autopilot
        sid = self.p.create_scene(self.pid, 1)
        job = self.p.create_job(sid)
        self.p.start(job)
        self.p.succeed(job)
        self.p.approve(job)
        self.p.conn.execute("UPDATE jobs SET retry_count=3 WHERE id=?", (job,))
        self.p.conn.commit()
        self.assertIn("Cần bạn quyết", autopilot._setcheck_block(self.p, self.pid, {"idx": 1, "fix": "x"}, "mock"))
        self.assertTrue(self.limit_items())

    def test_a_job_held_for_another_reason_is_not_said_to_be_at_the_limit(self):
        sid = self.p.create_scene(self.pid, 1)
        job = self.p.create_job(sid)
        self.p.start(job)
        self.p.succeed(job)
        self.p.reject(job, "ai_agent", "x", fix="fix a")                                # one automatic retry: retry_count 1
        child = self.p.conn.execute("SELECT id FROM jobs WHERE parent_job_id=?", (job,)).fetchone()["id"]
        self.p.start(child)
        self.p.succeed(child)
        self.p.set_qc_autofix(self.pid, True)
        self.assertEqual(self.p.apply_qc(child, dict(GOOD, mood=0.1), autofix=True), "needs_review")   # QC named no fix
        self.assertEqual(self.p.job(child)["escalated"], 1)
        self.assertEqual(self.limit_items(), [])


class PlateFallbackAtTheLimit(unittest.TestCase):
    def test_the_scene_is_not_switched_to_green_screen_when_no_new_clip_is_made(self):
        from core import autopilot, location_pack
        p = Pipeline(connect())
        pid = p.create_project("g", "human_qc", 0.85, 9)
        sid = p.create_scene(pid, 1)
        job = p.create_job(sid, "video_gen")
        p.start(job)
        p.succeed(job)
        p.conn.execute("UPDATE jobs SET retry_count=2 WHERE id=?", (job,))
        p.conn.commit()
        data = tempfile.mkdtemp()
        rec = {"ok": False, "mode": "first_frame", "job_id": job, "score": 0.2}
        from core import features
        with mock.patch.object(location_pack, "video_qc", return_value={str(sid): rec}),                 mock.patch.object(location_pack, "record_video_qc"), mock.patch.object(features, "on", return_value=True):
            self.assertIsNone(autopilot._plate_fallback_phase(p, pid, autopilot.Context(data, None, None, None)))
        self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 1)            # no new clip
        data_row = json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()[0] or "{}")
        self.assertNotEqual(data_row.get("plate_mode"), "green")


class InboxMoneyWarning(unittest.TestCase):
    def test_a_money_warning_shows_one_line_in_the_inbox(self):
        p = Pipeline(connect())
        pid = p.create_project("w")
        budget.restart(p.conn, usd=0.01)
        with spend_gate.spend(p.conn, "image", "deepix", project_id=pid, model="gpt-image-2"):
            pass
        rows = [i for i in inbox.items(p.conn, "a@x") if i["kind"] == "Tiền"]
        self.assertEqual(len(rows), 1)
        self.assertIn("Cảnh báo tiền", rows[0]["text"])
        self.assertEqual(rows[0]["level"], "warn")


class MoneyUi(unittest.TestCase):
    """UI v2: the 💵 bar's colour follows the planned amount (yellow ≥ 100 %, red ≥ 150 %); price labels say "(ước tính)"."""

    def test_the_money_meter_turns_yellow_then_red(self):
        from dashboard.design.screens import shell_parts as SP
        self.assertIn("var(--ok)", SP.money_meter(0.5, 1.0, "x"))
        warn = SP.money_meter(1.2, 1.0, "x")
        self.assertIn("var(--warn)", warn)
        self.assertIn("120%", warn)
        self.assertIn("var(--bad)", SP.money_meter(1.6, 1.0, "x"))
        self.assertEqual(SP.money_flag(1.6, 1.0), " 🔴")
        self.assertEqual(SP.money_flag(1.0, 1.0), " 🟡")
        self.assertEqual(SP.money_flag(0.2, 1.0), "")

    def test_price_labels_say_they_are_estimates(self):
        from dashboard.design.screens import storyboard_cards, video_ui
        self.assertIn("(ước tính)", storyboard_cards.estimate_short({"kind": "image", "known": True, "items": 3, "min": 0.15,
                                                                    "currency": "USD"}))
        self.assertIn("(ước tính)", video_ui.meta_line("kling", 5, 0.4, 0))


class ResetWithPlan(unittest.TestCase):
    OWNER = {"email": "o@x", "role": "owner"}

    @mock.patch.dict(os.environ, ON)
    def test_the_owner_sets_the_planned_amount_of_a_project_and_the_trial(self):
        p = Pipeline(connect())
        pid = p.create_project("plan")
        lock(p, pid)
        done = money_reset.set_planned(p.conn, self.OWNER, "project", 12.5, "đợt mới", project_id=pid)
        self.assertEqual(done["planned"], 12.5)
        self.assertEqual(project_budget.planned(p.conn, pid), 12.5)
        money_reset.set_planned(p.conn, self.OWNER, "trial", 20, "đợt mới")
        self.assertEqual(budget.get(p.conn)["usd"], 20)
        self.assertTrue(budget.get(p.conn)["enabled"])
        from core import auth
        with self.assertRaises(auth.AuthError):
            money_reset.set_planned(p.conn, {"email": "m@x", "role": "member"}, "trial", 1, "x")


if __name__ == "__main__":
    unittest.main()
