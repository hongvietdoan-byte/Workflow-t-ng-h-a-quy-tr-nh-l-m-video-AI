"""S14.17 (người dùng duyệt 04/10): trước mỗi lần gen lại có lý do sửa (người từ chối kèm ghi chú / QC từ chối kèm fix), Đạo diễn (Claude)
viết lại prompt tiếng Anh của shot; bản cũ lưu thành phiên bản; job mới không nối "Fix:" nữa. Claude lỗi → hành vi cũ + diag. 0 USD."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import llm_runner, prompt_rewrite
from core.db import connect
from core.pipeline import AUTO_REGEN_LIMIT, Pipeline
from core.runner import RESEND_NOTE, model_fix

BAD = {"character": 0.5, "hands_face": 0.4, "composition": 0.6, "mood": 0.5}
OLD = "Kelly in a red jacket stands on the rooftop at dusk, medium shot"
NEW = "Kelly in a yellow jacket stands on the rooftop at dusk, medium shot"
ON = {"FEATURE_DIRECTOR_REWRITE": "1"}
OFF = {"FEATURE_DIRECTOR_REWRITE": "0"}


class FakeClient:
    name = "fake"

    def __init__(self, answer=None, error=None):
        self.calls = []
        self.answer = answer if answer is not None else {"new_prompt": NEW, "changed": ["Đổi 'red jacket' → 'yellow jacket'"],
                                                         "why": "Câu áo đỏ gây lỗi."}
        self.error = error

    def complete(self, prompt, images=()):
        self.calls.append((prompt, list(images)))
        if self.error is not None:
            raise self.error
        return llm_runner.LlmReply(json.dumps(self.answer, ensure_ascii=False), 100, 50)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        env = mock.patch.dict(os.environ, {"FEATURE_SETTINGS_FILE": os.path.join(self.tmp, "none.json")})
        env.start()
        self.addCleanup(env.stop)
        self.p = Pipeline(connect())
        self.client = FakeClient()
        patcher = mock.patch.object(prompt_rewrite, "client_for", lambda p: self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def make(self, mode="human_qc", kind="image_gen"):
        pid = self.p.create_project("t", mode, 0.85, 3)
        sid = self.p.create_scene(pid, 1, "S01")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": OLD, "characters": ["Kelly"]}), sid))
        self.p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, state) VALUES (?,?, 'approved')",
                            (sid, "Slow push-in, Kelly turns her head"))
        self.p.conn.commit()
        job = self.p.create_job(sid, kind)
        self.p.start(job)
        self.p.succeed(job)
        return pid, sid, job

    def child(self, job):
        return self.p.conn.execute("SELECT * FROM jobs WHERE parent_job_id=? ORDER BY id DESC", (job,)).fetchone()

    def image_prompt(self, sid):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"])["image_prompt"]


class FlagOff(Base):
    def test_flag_off_keeps_the_old_fix_behaviour(self):
        _, sid, job = self.make()
        with mock.patch.dict(os.environ, OFF):
            self.p.reject(job, "user", "đổi áo sang màu vàng")
        self.assertEqual(self.client.calls, [])
        self.assertEqual(self.child(job)["retry_reason"], "đổi áo sang màu vàng")
        self.assertEqual(self.image_prompt(sid), OLD)
        self.assertEqual(prompt_rewrite.versions(self.p.conn, sid, "image"), [])

    def test_flag_is_new_unverified_and_off_by_default(self):
        from core import features
        self.assertIn("director_rewrite", features.FEATURES)
        self.assertFalse(features.FEATURES["director_rewrite"]["verified"])
        with mock.patch.dict(os.environ, {"FEATURE_DIRECTOR_REWRITE": ""}):
            self.assertFalse(features.on("director_rewrite"))


class Rewrite(Base):
    def test_user_reject_with_note_rewrites_the_shot_prompt_and_keeps_the_old_one(self):
        _, sid, job = self.make()
        with mock.patch.dict(os.environ, ON):
            self.assertEqual(self.p.reject(job, "user", "đổi áo sang màu vàng"), "rejected")
        self.assertEqual(len(self.client.calls), 1)
        prompt, _ = self.client.calls[0]
        self.assertIn(OLD, prompt)
        self.assertIn("đổi áo sang màu vàng", prompt)
        self.assertEqual(self.image_prompt(sid), NEW)
        vers = prompt_rewrite.versions(self.p.conn, sid, "image")
        self.assertEqual([(v["version"], v["prompt"], v["source"]) for v in vers],
                         [(1, OLD, "original"), (2, NEW, "director_rewrite")])
        self.assertEqual(vers[-1]["changed"], ["Đổi 'red jacket' → 'yellow jacket'"])
        reason = self.child(job)["retry_reason"]
        self.assertTrue(reason.startswith(prompt_rewrite.REWRITE_NOTE))
        self.assertIsNone(model_fix(reason))                                 # job mới không còn "Fix:"

    def test_the_new_job_prompt_has_no_fix_sentence(self):
        from core.runner import build_image_prompt
        pid, sid, job = self.make()
        with mock.patch.dict(os.environ, ON):
            self.p.reject(job, "user", "đổi áo sang màu vàng")
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"])
        prompt, _ = build_image_prompt(self.p.conn, pid, data, fix=model_fix(self.child(job)["retry_reason"]))
        self.assertIn("yellow jacket", prompt)
        self.assertNotIn("Fix:", prompt)
        self.assertNotIn("red jacket", prompt)

    def test_qc_reject_rewrites_and_still_counts_on_the_auto_limit(self):
        _, sid, job = self.make("auto")
        with mock.patch.dict(os.environ, ON):
            self.assertEqual(self.p.apply_qc(job, BAD, issues="Draw the jacket yellow, not red."), "rejected")
        self.assertEqual(len(self.client.calls), 1)
        self.assertIn("Draw the jacket yellow, not red.", self.client.calls[0][0])
        child = self.child(job)
        self.assertEqual(child["retry_count"], 1)
        self.assertEqual(child["origin"], "auto")
        self.assertEqual(self.image_prompt(sid), NEW)

    def test_qc_scene_details_reach_the_director(self):
        _, sid, job = self.make()
        self.p.transition(job, __import__("core.states", fromlist=["JobState"]).JobState.PENDING_REVIEW, actor="ai_agent")
        with mock.patch.dict(os.environ, ON):
            self.p.reject(job, "ai_agent", "QC cảnh [image]: áo sai màu", fix="Make the jacket yellow.",
                          qc={"root_cause": "image", "problem": "áo sai màu", "fix": "Make the jacket yellow."})
        prompt = self.client.calls[0][0]
        self.assertIn("root_cause", prompt)
        self.assertIn("áo sai màu", prompt)

    def test_auto_limit_reached_no_rewrite_no_job(self):
        _, sid, job = self.make("auto")
        self.p.conn.execute("UPDATE jobs SET retry_count=? WHERE id=?", (AUTO_REGEN_LIMIT["image_gen"], job))
        self.p.conn.commit()
        with mock.patch.dict(os.environ, ON):
            self.p.reject(job, "ai_agent", "QC thấp", fix="Make the jacket yellow.")
        self.assertEqual(self.client.calls, [])
        self.assertIsNone(self.child(job))
        self.assertEqual(self.image_prompt(sid), OLD)

    def test_reopen_approved_with_note_rewrites_but_not_when_input_already_changed(self):
        _, sid, job = self.make()
        self.p.approve(job, "user")
        with mock.patch.dict(os.environ, ON):
            self.p.reopen_approved(job, "Nội dung cảnh đã đổi: x", fix="")
        self.assertEqual(self.client.calls, [])
        new = self.child(job)["id"]
        self.p.start(new)
        self.p.succeed(new)
        self.p.approve(new, "user")
        with mock.patch.dict(os.environ, ON):
            self.p.reopen_approved(new, "áo phải màu vàng")
        self.assertEqual(len(self.client.calls), 1)
        self.assertEqual(self.image_prompt(sid), NEW)

    def test_video_reject_rewrites_the_motion_prompt(self):
        _, sid, job = self.make(kind="video_gen")
        with mock.patch.dict(os.environ, ON):
            self.client.answer = {"new_prompt": "Static camera, Kelly turns her head slowly", "changed": ["bỏ push-in"], "why": "rung"}
            self.p.reject(job, "user", "máy quay rung quá, giữ máy đứng yên")
        mp = self.p.conn.execute("SELECT motion_prompt FROM motion_prompts WHERE scene_id=?", (sid,)).fetchone()
        self.assertEqual(mp["motion_prompt"], "Static camera, Kelly turns her head slowly")
        self.assertEqual([v["source"] for v in prompt_rewrite.versions(self.p.conn, sid, "video")], ["original", "director_rewrite"])
        self.assertIsNone(model_fix(self.child(job)["retry_reason"]))

    def test_regenerate_video_with_fix_rewrites(self):
        from core import regen
        _, sid, job = self.make(kind="video_gen")
        self.p.conn.execute("UPDATE motion_prompts SET motion_prompt='Fast whip pan' WHERE scene_id=?", (sid,))
        self.p.conn.commit()
        self.client.answer = {"new_prompt": "Slow pan", "changed": ["chậm lại"], "why": "nhanh quá"}
        with mock.patch.dict(os.environ, ON):
            new = regen.regenerate_video(self.p, self.tmp, job, "Đồng bộ cả bộ clip: quá nhanh", fix="Slow the pan down.")
        self.assertEqual(len(self.client.calls), 1)
        self.assertIsNone(model_fix(self.p.job(new)["retry_reason"]))
        self.assertEqual(self.p.conn.execute("SELECT motion_prompt FROM motion_prompts WHERE scene_id=?", (sid,)).fetchone()[0], "Slow pan")

    def test_revert_uses_the_old_prompt_again_for_free(self):
        _, sid, job = self.make()
        with mock.patch.dict(os.environ, ON):
            self.p.reject(job, "user", "đổi áo sang màu vàng")
        prompt_rewrite.revert(self.p, sid, "image")
        self.assertEqual(self.image_prompt(sid), OLD)
        vers = prompt_rewrite.versions(self.p.conn, sid, "image")
        self.assertEqual([v["source"] for v in vers], ["original", "director_rewrite", "revert"])
        self.assertEqual(len(self.client.calls), 1)                          # no Claude call, no job
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 2)

    def test_rules_kept_no_minor_age_and_no_new_character(self):
        _, sid, job = self.make()
        self.p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?,?,?)", (self.p.job(job)["project_id"], "Kelly", "x"))
        self.p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?,?,?)", (self.p.job(job)["project_id"], "Maxim", "y"))
        self.p.conn.commit()
        self.client.answer = {"new_prompt": "Kelly, 16-year-old girl, in a yellow jacket", "changed": ["x"], "why": "y"}
        with mock.patch.dict(os.environ, ON):
            self.p.reject(job, "user", "áo vàng")
        self.assertNotIn("16-year-old", self.image_prompt(sid))
        job2 = self.child(job)["id"]
        self.p.start(job2)
        self.p.succeed(job2)
        self.client.answer = {"new_prompt": "Kelly and Maxim in yellow jackets", "changed": ["x"], "why": "y"}
        with mock.patch.dict(os.environ, ON):
            self.p.reject(job2, "user", "áo vàng hơn")
        self.assertNotIn("Maxim", self.image_prompt(sid))                    # a character outside the shot: refused → old way
        self.assertEqual(self.child(job2)["retry_reason"], "áo vàng hơn")


LIVE = "'approved','queued','running','succeeded','pending_review','retryable','failed'"     # autopilot._images_phase / _videos_phase


class ReviewFixes(Base):
    """Phiên rà độc lập S14.17: (1) không có lúc nào cảnh mất job sống trong khi chờ Claude; (2) không gen lại bản cũ khi bản mới đã xếp hàng."""

    def watching(self, sid, kind):
        from core import autopilot
        seen = []
        real = self.client.complete

        def complete(prompt, images=()):
            seen.append(autopilot._has(self.p, sid, kind, LIVE))
            return real(prompt, images)
        self.client.complete = complete
        return seen

    def test_take_stays_alive_while_claude_writes_on_reject(self):
        _, sid, job = self.make()
        seen = self.watching(sid, "image_gen")
        with mock.patch.dict(os.environ, ON):
            self.p.reject(job, "user", "đổi áo sang màu vàng")
        self.assertEqual(seen, [True])
        self.assertEqual(self.image_prompt(sid), NEW)

    def test_take_stays_alive_while_claude_writes_on_reopen_and_regen(self):
        from core import regen
        _, sid, job = self.make()
        self.p.approve(job, "user")
        seen = self.watching(sid, "image_gen")
        with mock.patch.dict(os.environ, ON):
            self.p.reopen_approved(job, "áo phải màu vàng")
        self.assertEqual(seen, [True])
        _, sid2, vjob = self.make(kind="video_gen")
        self.client = FakeClient({"new_prompt": "Slow pan", "changed": ["chậm"], "why": "x"})
        seen_v = self.watching(sid2, "video_gen")
        with mock.patch.dict(os.environ, ON):
            regen.regenerate_video(self.p, self.tmp, vjob, "quá nhanh", fix="Slow the pan down.")
        self.assertEqual(seen_v, [True])

    def test_regen_checks_reviewable_before_paying_claude(self):
        from core import regen
        from core.states import InvalidTransition
        _, sid, job = self.make(kind="video_gen")
        self.p.conn.execute("UPDATE jobs SET state='queued' WHERE id=?", (job,))
        self.p.conn.commit()
        with mock.patch.dict(os.environ, ON), self.assertRaises(InvalidTransition):
            regen.regenerate_video(self.p, self.tmp, job, "x", fix="Slow down.")
        self.assertEqual(self.client.calls, [])

    def test_older_clip_made_outdated_by_the_rewrite_is_not_redone_while_the_new_take_waits(self):
        from core import batch, lineage
        pid, sid, img = self.make()
        self.p.approve(img, "user")
        lineage.stamp_motion(self.p.conn, sid)
        mp = self.p.conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (sid,)).fetchone()
        clips = []
        for state in ("approved", "pending_review"):            # hero take: two clips of the same shot
            j = self.p.create_job(sid, "video_gen")
            self.p.conn.execute("UPDATE jobs SET state=?, source_job_id=?, input_hash=? WHERE id=?",
                                (state, img, lineage.video_input_hash(mp, None), j))
            clips.append(j)
        self.p.conn.commit()
        self.client.answer = {"new_prompt": "Static camera, Kelly turns her head slowly", "changed": ["x"], "why": "y"}
        with mock.patch.dict(os.environ, ON):
            self.p.reject(clips[1], "user", "giữ máy đứng yên")
        self.assertTrue(lineage.scan(self.p.conn, pid)[sid]["video_stale"])     # clip 1 now looks outdated…
        before = self.p.conn.execute("SELECT COUNT(*) FROM jobs WHERE type='video_gen'").fetchone()[0]
        res = batch.queue_videos(self.p, pid, self.tmp)
        self.assertEqual(res, {"created": 0, "redo": 0})                         # …but the new take already waits: no second paid job
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs WHERE type='video_gen'").fetchone()[0], before)
        self.assertEqual(self.p.state(clips[0]).value, "approved")

class ReviewMinor(Base):
    def test_estimate_counts_the_rewrites_when_the_flag_is_on(self):
        from core import cost, project_budget
        pid, sid, job = self.make()
        with mock.patch.dict(os.environ, OFF):
            off = cost.estimate_run(self.p, pid)
            rem_off = project_budget.remaining(self.p, pid)
        with mock.patch.dict(os.environ, ON):
            on = cost.estimate_run(self.p, pid)
            rem_on = project_budget.remaining(self.p, pid)
        self.assertEqual(off["rewrite"], 0)
        self.assertGreater(on["rewrite"], 0)
        self.assertGreater(on["total"], off["total"])
        self.assertGreater(on["max"], off["max"])
        self.assertGreater(rem_on["claude_director"], rem_off["claude_director"])

    def test_clip_qc_reject_hands_root_cause_and_problem_to_the_director(self):
        _, sid, job = self.make("auto", kind="video_gen")
        with mock.patch.dict(os.environ, ON):
            self.p.apply_qc(job, BAD, issues="Camera shakes; keep it still.")
        prompt = self.client.calls[0][0]
        self.assertIn("root_cause", prompt)
        self.assertIn("hands_face 0.40", prompt)
        self.assertIn("Camera shakes", prompt)

    def test_clip_frames_folder_is_removed_after_the_call(self):
        _, sid, job = self.make(kind="video_gen")
        clip = os.path.join(self.tmp, "c.mp4")
        with open(clip, "wb") as f:
            f.write(b"x")
        self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (clip, job))
        self.p.conn.commit()
        made = []

        def frames(path, out_dir, count=8):
            made.append(out_dir)
            out = os.path.join(out_dir, "frame_01.jpg")
            with open(out, "wb") as f:
                f.write(b"j")
            return [out]
        self.client.answer = {"new_prompt": "Static camera", "changed": ["x"], "why": "y"}
        with mock.patch.dict(os.environ, ON), mock.patch("core.video_analysis.extract_frames", frames):
            self.p.reject(job, "user", "rung quá")
        self.assertEqual(len(self.client.calls[0][1]), 1)                     # the frame went to Claude
        self.assertTrue(made and not os.path.exists(made[0]))                 # …and its temporary folder is gone


class Fallback(Base):
    def diag_rows(self):
        return self.p.conn.execute("SELECT * FROM diag_events WHERE code=?", (prompt_rewrite.FALLBACK_CODE,)).fetchall()

    def test_claude_error_falls_back_to_fix_and_says_so(self):
        _, sid, job = self.make()
        self.client.error = llm_runner.LlmError("Anthropic hết tiền", code="out_of_credit")
        with mock.patch.dict(os.environ, ON):
            self.p.reject(job, "user", "đổi áo sang màu vàng")
        self.assertEqual(self.child(job)["retry_reason"], "đổi áo sang màu vàng")
        self.assertEqual(self.image_prompt(sid), OLD)
        rows = self.diag_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["severity"], "warn")
        self.assertIn("Fix", rows[0]["message"])

    def test_no_claude_configured_falls_back(self):
        _, sid, job = self.make()
        self.client = None
        with mock.patch.dict(os.environ, ON):
            self.p.reject(job, "user", "đổi áo sang màu vàng")
        self.assertEqual(self.child(job)["retry_reason"], "đổi áo sang màu vàng")
        self.assertEqual(len(self.diag_rows()), 1)

    def test_same_prompt_back_is_not_a_change(self):
        _, sid, job = self.make()
        self.client.answer = {"new_prompt": OLD, "changed": [], "why": ""}
        with mock.patch.dict(os.environ, ON):
            self.p.reject(job, "user", "đổi áo sang màu vàng")
        self.assertEqual(self.child(job)["retry_reason"], "đổi áo sang màu vàng")
        self.assertEqual(len(self.diag_rows()), 1)

    def test_provider_resend_never_calls_the_director(self):
        _, sid, job = self.make()
        new = self.p.create_job(sid)
        self.p.start(new)
        self.p.fail(new, "provider down")
        with mock.patch.dict(os.environ, ON):
            r = self.p.retry(new, "gửi lại (lỗi nhà cung cấp)")
            self.p.start(r)
            self.p.fail(r, "x")
            self.p.resend(r, f"{RESEND_NOTE} (1/3)")
        self.assertEqual(self.client.calls, [])
        self.assertEqual(self.diag_rows(), [])


class Ledger(unittest.TestCase):
    def test_the_rewrite_call_is_on_the_claude_ledger_under_its_own_stage(self):
        from core.adapters.http import HttpResponse
        tmp = tempfile.mkdtemp()
        db = os.path.join(tmp, "m.sqlite")
        p = Pipeline(connect(db))
        pid = p.create_project("t")
        sid = p.create_scene(pid, 1)
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": OLD}), sid))
        p.conn.commit()
        job = p.create_job(sid)
        p.start(job)
        p.succeed(job)

        def send(method, url, headers, body, timeout):
            answer = json.dumps({"new_prompt": NEW, "changed": ["áo vàng"], "why": "x"})
            return HttpResponse(200, json.dumps({"content": [{"type": "text", "text": answer}], "stop_reason": "end_turn",
                                                 "usage": {"input_tokens": 900, "output_tokens": 120}}).encode())
        client = llm_runner.AnthropicClient("sk-test", "claude-sonnet-5", transport=send, sleep=lambda s: None, ledger=db)
        with mock.patch.dict(os.environ, dict(ON, FEATURE_SETTINGS_FILE=os.path.join(tmp, "none.json"))), \
                mock.patch.object(prompt_rewrite, "client_for", lambda pp: client):
            p.reject(job, "user", "đổi áo sang màu vàng")
        rows = p.conn.execute("SELECT DISTINCT stage, project_id FROM usage_events WHERE kind='llm'").fetchall()
        self.assertEqual([(r["stage"], r["project_id"]) for r in rows], [(prompt_rewrite.STAGE, pid)])

    def test_stage_has_its_own_bounded_answer_and_estimate(self):
        from core import cost, project_budget
        self.assertIn(prompt_rewrite.STAGE, llm_runner.STAGE_SETTINGS)
        self.assertLessEqual(llm_runner.stage_settings(prompt_rewrite.STAGE)["max_tokens"], 8000)
        self.assertIn(prompt_rewrite.STAGE, cost.LLM_STAGE_TOKENS)
        self.assertEqual(project_budget.claude_stage(prompt_rewrite.STAGE), "claude_director")

    def test_short_wait_one_retry_then_old_way_with_the_note_kept(self):
        from core.adapters.http import ProviderError
        tmp = tempfile.mkdtemp()
        db = os.path.join(tmp, "m.sqlite")
        p = Pipeline(connect(db))
        pid = p.create_project("t")
        sid = p.create_scene(pid, 1)
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": OLD}), sid))
        p.conn.commit()
        job = p.create_job(sid)
        p.start(job)
        p.succeed(job)
        waits = []

        def send(method, url, headers, body, timeout):
            waits.append(timeout)
            raise ProviderError("timed out")
        client = llm_runner.AnthropicClient("sk-test", "claude-sonnet-5", transport=send, sleep=lambda s: None, ledger=db)
        with mock.patch.dict(os.environ, dict(ON, FEATURE_SETTINGS_FILE=os.path.join(tmp, "none.json"))), \
                mock.patch.object(prompt_rewrite, "client_for", lambda pp: client):
            p.reject(job, "user", "đổi áo sang màu vàng")
        self.assertEqual(len(waits), 2)                                       # one try + at most one retry
        self.assertTrue(all(60 <= w <= 90 for w in waits), waits)
        child = p.conn.execute("SELECT retry_reason FROM jobs WHERE parent_job_id=?", (job,)).fetchone()
        self.assertEqual(child["retry_reason"], "đổi áo sang màu vàng")       # the person's note is not lost: the old Fix: way
        self.assertTrue(p.conn.execute("SELECT 1 FROM diag_events WHERE code=?", (prompt_rewrite.FALLBACK_CODE,)).fetchone())

    def test_cli_client_wait_is_short_for_the_rewrite(self):
        self.assertLessEqual(llm_runner.stage_settings(prompt_rewrite.STAGE)["timeout"], 90)
        self.assertLessEqual(llm_runner.stage_settings(prompt_rewrite.STAGE)["retries"], 1)

    def test_mock_llm_answers_the_rewrite_prompt(self):
        p = Pipeline(connect())
        pid = p.create_project("t")
        sid = p.create_scene(pid, 1)
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": OLD}), sid))
        p.conn.commit()
        job = p.create_job(sid)
        p.start(job)
        p.succeed(job)
        with mock.patch.dict(os.environ, dict(ON, LLM_PROVIDER="mock", FEATURE_SETTINGS_FILE=os.path.join(tempfile.mkdtemp(), "n.json"))):
            p.reject(job, "user", "đổi áo sang màu vàng")
        new = json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"])["image_prompt"]
        self.assertNotEqual(new, OLD)
        self.assertIsNone(model_fix(p.conn.execute("SELECT retry_reason FROM jobs WHERE parent_job_id=?", (job,)).fetchone()[0]))


class Diff(unittest.TestCase):
    def test_word_diff_marks_the_changed_words(self):
        parts = prompt_rewrite.word_diff(OLD, NEW)
        self.assertIn(("del", "red"), parts)
        self.assertIn(("ins", "yellow"), parts)
        self.assertEqual("".join(t for op, t in parts if op != "del"), NEW)


if __name__ == "__main__":
    unittest.main()
