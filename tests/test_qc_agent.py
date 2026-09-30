"""The QC agent (flag qc_agent, 2026-09-27): a multi-turn tool-use loop — it looks at frames, crops, lays details of several frames side by
side, must record every frame before it may finish, and its verdicts wait for a person until the QC is trusted."""
import copy
import json
import os
import tempfile
import unittest

from core import llm_runner, qc_agent, qc_scene, shots
from tests.test_qc_scene import picture
from tests.test_v3 import _approve_all_images, kenta_project


class Scripted:
    """A fake Claude that plays a list of turns; each turn = list of (tool name, input). Remembers what it was sent."""
    name = "scripted"

    def __init__(self, turns):
        self.turns, self.seen = list(turns), []

    def converse(self, messages, tools, system="", max_tokens=None):
        self.seen.append(copy.deepcopy(messages[-1]))    # a restart replaces the conversation
        self.tool_sets = getattr(self, "tool_sets", []) + [[t["name"] for t in tools]]
        calls = self.turns.pop(0) if self.turns else []
        blocks = [{"type": "tool_use", "id": f"t{len(self.seen)}_{i}", "name": n, "input": inp} for i, (n, inp) in enumerate(calls)]
        return llm_runner.LlmReply("", 100, 20, "tool_use", blocks=blocks or [{"type": "text", "text": "…"}])


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.p, self.pid = kenta_project(shot_mode="per_shot")
        self.data = tempfile.mkdtemp()
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        _approve_all_images(self.p, self.pid, self.data)
        rows = shots.shots_of(self.p, self.pid)
        self.scene = rows[0]["data"]["story_scene"]
        for r in rows:
            j = self.p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'", (r["id"],)).fetchone()
            self.p.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (j["id"],))
            picture(os.path.join(self.data, str(self.pid), "images", f"job_{j['id']}.png"))
        self.p.conn.commit()
        self.frames = qc_scene.scene_frames(self.p, self.pid, self.scene, self.data)
        self.n = len(self.frames)

    def record(self, k, verdict="pass", fix=""):
        issues = [] if verdict == "pass" else [{"type": "tay", "description": "sáu ngón", "evidence": "cắt vùng tay K%d" % k, "severity": "block"}]
        return ("record", {"k": k, "verdict": verdict, "issues": issues, "root_cause": "model" if verdict == "block" else "none",
                           "fix_en": fix})

    def test_it_investigates_then_records_every_frame_and_its_verdicts_wait_for_a_person(self):
        turns = [[("view_frame", {"k": 1}), ("view_frame", {"k": 1, "region": [0.2, 0.1, 0.6, 0.4]})],
                 [("strip", {"items": [{"k": 1, "region": [0, 0, 0.5, 0.5]}, {"k": 2, "region": [0, 0, 0.5, 0.5]}], "title": "vai trái"})],
                 [("finish", {"summary": "sớm"})],                       # refused: frames not recorded yet
                 [self.record(1, "block", "The left hand has exactly five fingers.")] + [self.record(k) for k in range(2, self.n + 1)],
                 [("finish", {"summary": "xong", "new_fault_types": ["tay sáu ngón"]})]]
        c = Scripted(turns)
        res = qc_agent.review_scene(self.p, self.pid, self.scene, c, self.data, self.frames)
        self.assertEqual(res["summary"]["summary"], "xong")
        kinds = [b["type"] for r in c.seen[1]["content"] for b in r["content"]]
        self.assertIn("image", kinds)                                   # the tools answered with pictures
        refused = [b["text"] for r in c.seen[3]["content"] for b in r["content"] if b["type"] == "text"]
        self.assertTrue(any("chưa được kết thúc" in t for t in refused))
        self.assertEqual(res["records"][0]["verdict"], "block")
        states = {self.p.job(f["job_id"])["state"] for f in self.frames}
        self.assertEqual(states, {"pending_review"})                    # not trusted yet: a person decides

    def test_the_last_turns_offer_only_the_record_tools(self):
        """S7.1 01/10: cảnh 2 #8 spent every turn looking (text "record now" answers ignored) — the closing turns cannot look at all."""
        c = Scripted([[("view_frame", {"k": 1})]] * (qc_agent.MAX_STEPS + 2))
        qc_agent.QcAgent(self.p, self.pid, self.data, c, self.frames).run()
        steps = qc_agent.max_steps(len(self.frames))
        self.assertIn("view_frame", c.tool_sets[0])
        for names in c.tool_sets[steps - qc_agent.CLOSING_TURNS:]:
            self.assertEqual(sorted(names), sorted(qc_agent.RECORD_TOOLS))
        self.assertEqual(qc_agent.max_steps(6), 16)
        self.assertEqual(qc_agent.max_steps(2), qc_agent.MAX_STEPS)

    def test_out_of_steps_the_unchecked_frames_are_doubts_not_passes(self):
        c = Scripted([[("view_frame", {"k": 1})]] * (qc_agent.MAX_STEPS + 2))
        res = qc_agent.QcAgent(self.p, self.pid, self.data, c, self.frames).run()
        self.assertEqual({r["verdict"] for r in res["records"]}, {"doubt"})
        self.assertEqual(res["steps"], qc_agent.max_steps(len(self.frames)))

    def test_old_pictures_are_never_cut_the_session_restarts_from_a_recap(self):
        """S7.0: changing an earlier picture invalidates the cache after it — pictures stay; past the limit a new session starts from the
        cached brief + a recap + the tool answers the agent has not seen yet."""
        img = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "x"}}
        first = [{"type": "text", "text": "brief"}, dict(img, cache_control={"type": "ephemeral"})]
        msgs = [{"role": "user", "content": first}]
        def turns(n):
            for i in range(n):
                msgs.append({"role": "assistant", "content": [{"type": "text", "text": f"K{i} nền có hai tầng"},
                                                               {"type": "tool_use", "id": str(i), "name": "view_frame", "input": {}}]})
                msgs.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": str(i),
                                                          "content": [{"type": "text", "text": f"K{i}"}, dict(img)]}]})
        turns(qc_agent.MAX_SESSION_IMAGES)
        before = copy.deepcopy(msgs)
        self.assertFalse(qc_agent.too_long(msgs))
        self.assertEqual(msgs, before)                                         # nothing rewritten: the cache survives
        turns(1)
        self.assertTrue(qc_agent.too_long(msgs))
        agent = qc_agent.QcAgent(self.p, self.pid, self.data, None, self.frames)
        agent.records[1] = {"k": 1, "verdict": "block", "issues": [{"description": "sáu ngón"}]}
        new = qc_agent.restart(msgs, agent._recap(msgs))
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0]["content"][:2], first)                         # the cached prefix is byte-identical
        recap = new[0]["content"][2]["text"]
        self.assertIn("hai tầng", recap)                                       # its own notes
        self.assertIn("K1: block — sáu ngón", recap)
        self.assertEqual(new[0]["content"][-1]["type"], "image")               # the last answer it asked for is still shown
        self.assertEqual(sum(1 for b in new[0]["content"] if b.get("cache_control")), 1)

    def test_a_long_run_restarts_instead_of_pruning(self):
        looks = [[("view_frame", {"k": 1}), ("view_frame", {"k": 2})]] * (qc_agent.MAX_SESSION_IMAGES // 2 + 1)
        c = Scripted(looks + [[self.record(k) for k in range(1, self.n + 1)], [("finish", {"summary": "xong"})]])
        res = qc_agent.QcAgent(self.p, self.pid, self.data, c, self.frames).run()
        self.assertEqual(res["summary"]["summary"], "xong")
        self.assertEqual(res["sessions"], 2)

    def test_a_rolling_cache_mark_on_the_newest_message_only(self):
        msgs = [{"role": "user", "content": [{"type": "text", "text": "brief", "cache_control": {"type": "ephemeral"}}]},
                {"role": "assistant", "content": [{"type": "text", "text": "a"}]},
                {"role": "user", "content": [{"type": "text", "text": "b"}]}]
        qc_agent.mark_cache(msgs)
        msgs += [{"role": "assistant", "content": [{"type": "text", "text": "c"}]}, {"role": "user", "content": [{"type": "text", "text": "d"}]}]
        qc_agent.mark_cache(msgs)
        marked = [i for i, m in enumerate(msgs) for b in m["content"] if "cache_control" in b]
        self.assertEqual(marked, [0, 2, 4])                                    # the brief + the two newest user messages (≤ 4 with system)

    def test_at_the_scene_lock_it_stops_and_keeps_what_it_recorded(self):
        """28/09: the lock raised inside the loop lost everything the agent had recorded for scene 2."""
        class Capped(Scripted):
            def converse(inner, messages, tools, system="", max_tokens=None):
                if len(inner.seen) >= 2:
                    raise llm_runner.LlmError("chạm trần 'agent QC cảnh 1'", code="budget")
                return super().converse(messages, tools, system, max_tokens)
        c = Capped([[self.record(1, "block", "The left hand has exactly five fingers.")], [self.record(2)]])
        res = qc_agent.QcAgent(self.p, self.pid, self.data, c, self.frames).run()
        self.assertEqual(res["records"][0]["verdict"], "block")
        self.assertEqual(res["records"][1]["verdict"], "pass")
        self.assertTrue(all(r["verdict"] == "doubt" for r in res["records"][2:]))
        self.assertIn("chạm trần", res["stopped"])
        self.assertTrue(os.path.exists(os.path.join(self.data, str(self.pid), "qc_scene", f"agent_scene_{self.scene}", "result.json"))
                        or res["summary"])

    def test_the_brief_carries_the_limits_and_the_real_place(self):
        agent = qc_agent.QcAgent(self.p, self.pid, self.data, None, self.frames)
        brief = agent._brief()
        self.assertIn(f"${qc_agent.scene_cap(len(self.frames)):.2f}", brief)
        self.assertIn("BÊN THÂN NGƯỜI", brief)                               # the playbook's body-side rule (A1, 28/09)
        self.assertIn("G1", brief)

    def test_a_block_without_a_fix_sentence_is_refused(self):
        agent = qc_agent.QcAgent(self.p, self.pid, self.data, None, self.frames)
        out = agent.tool("record", {"k": 1, "verdict": "block", "issues": [{"type": "a", "description": "b", "evidence": "c",
                                                                               "severity": "block"}], "root_cause": "model", "fix_en": ""})
        self.assertIn("fix_en", out[0]["text"])
        self.assertNotIn(1, agent.records)

    def test_left_right_is_decided_by_code_from_measurements(self):
        """S7.1 01/10: the agent blocked #8 S1·2 / S1·3 (Kenta from behind, star shoulder frame-left of his body = LEFT arm = right)."""
        agent = qc_agent.QcAgent(self.p, self.pid, self.data, None, self.frames)
        flip = {"type": "A1 lateral-flip", "description": "tay gần máy (khung-phải) mang găng giáp", "evidence": "strip K1",
                "severity": "block"}
        rec = {"k": 1, "verdict": "block", "root_cause": "model", "fix_en": "Keep his left arm on the frame-left side of his body."}
        out = agent.tool("record", dict(rec, issues=[flip]))                      # no measurements: refused
        self.assertIn("side", out[0]["text"])
        self.assertNotIn(1, agent.records)
        right = dict(flip, side={"who": "KENTA", "view": "behind", "body_center_x": 0.62, "detail_x": 0.35, "detail": "gauntlet",
                                 "expected_arm": "LEFT"})
        out = agent.tool("record", dict(rec, issues=[right]))                     # the measurements say LEFT arm = where it belongs
        self.assertIn("không phải lỗi lật", out[0]["text"])
        self.assertNotIn(1, agent.records)
        wrong = dict(flip, side=dict(right["side"], detail_x=0.85))               # frame-right of the body seen from behind = RIGHT
        out = agent.tool("record", dict(rec, issues=[wrong]))
        self.assertIn("đã ghi K1", out[0]["text"])
        self.assertEqual(qc_agent.arm_from_side({"view": "camera", "body_center_x": 0.5, "detail_x": 0.7}), "LEFT")
        self.assertIsNone(qc_agent.arm_from_side({"view": "behind", "body_center_x": 0.5, "detail_x": 0.51}))
        self.assertFalse(qc_agent.lateral_issue({"type": "shot_size", "description": "MCU thay vì CU"}))

    def test_the_inspection_plan_comes_from_the_profiles(self):
        from unittest import mock
        prof = {"approved": True, "must_keep": "gauntlet on the LEFT arm", "view_notes": {"from_behind": "…"}}
        frames = [{"k": 1, "data": {"characters": ["KENTA"]}}, {"k": 2, "data": {"characters": ["KENTA"]}}]
        with mock.patch("core.assets.standard_for", return_value=prof):
            plan = qc_agent.inspection_plan(self.p.conn, self.pid, frames)
        self.assertTrue(any("KENTA" in x and "[1, 2]" in x for x in plan))

    def test_the_plan_never_hands_the_agent_a_cut_left_right_sentence(self):
        """Review 28/09: a regex cut dropped "Seen from behind" and gave a rule wrong for the facing frames."""
        from unittest import mock
        prof = {"approved": True, "view_notes": {"facing_camera": "Facing the camera, the red tab on his LEFT sleeve is on the frame-right "
                                                                  "side of HIS OWN BODY", "from_behind": "Seen from behind, the red tab on "
                                                                  "his LEFT sleeve is on the frame-left side of HIS OWN BODY"}}
        frames = [{"k": 1, "data": {"characters": ["MAXIM"]}}, {"k": 2, "data": {"characters": ["MAXIM"]}}]
        with mock.patch("core.assets.standard_for", return_value=prof):
            plan = " ".join(qc_agent.inspection_plan(self.p.conn, self.pid, frames))
        self.assertNotIn("red tab", plan)                                     # the rule stays whole in the view notes section
        self.assertIn("BÊN THÂN", plan)

    def test_a_network_error_keeps_what_was_recorded(self):
        """Review 28/09: a timeout was a ProviderError, not an LlmError — it went round the agent's handling and lost the records."""
        from core.adapters.http import ProviderError

        class Flaky(Scripted):
            def converse(inner, messages, tools, system="", max_tokens=None):
                if len(inner.seen) >= 1:
                    raise ProviderError("network error: timed out", code="network", transient=True)
                return super().converse(messages, tools, system, max_tokens)
        c = Flaky([[self.record(1)]])
        res = qc_agent.QcAgent(self.p, self.pid, self.data, c, self.frames).run()
        self.assertEqual(res["records"][0]["verdict"], "pass")
        self.assertIn("dừng", res["stopped"])
        self.assertFalse(res["blocked"])

    def test_a_cut_answer_keeps_its_complete_records_and_goes_on(self):
        """28/09 scene 6: three cut answers were thrown away with the records already complete in them — nothing was recorded."""
        class Cut(Scripted):
            def converse(inner, messages, tools, system="", max_tokens=None):
                r = super().converse(messages, tools, system, max_tokens)
                if len(inner.seen) <= 2:
                    r.stop_reason = "max_tokens"
                    r.blocks = [{"type": "text", "text": "phân tích dài…"}] + list(r.blocks) + [
                        {"type": "tool_use", "id": f"cut{len(inner.seen)}", "name": "record", "input": {"k": 2}}]   # half-written
                return r
        turns = [[self.record(1)], [self.record(k) for k in range(2, self.n + 1)], [("finish", {"summary": "xong"})]]
        c = Cut(turns)
        res = qc_agent.QcAgent(self.p, self.pid, self.data, c, self.frames).run()
        self.assertEqual(res["summary"]["summary"], "xong")
        self.assertEqual({r["verdict"] for r in res["records"]}, {"pass"})     # the complete records of the cut turns were kept
        self.assertEqual(res["stopped"], "")

    def test_an_empty_answer_asks_to_call_tools(self):
        class Empty(Scripted):
            def converse(inner, messages, tools, system="", max_tokens=None):
                r = super().converse(messages, tools, system, max_tokens)
                if len(inner.seen) == 1:
                    r.blocks, r.stop_reason = [], "end_turn"
                return r
        c = Empty([[], [self.record(k) for k in range(1, self.n + 1)], [("finish", {"summary": "xong"})]])
        res = qc_agent.QcAgent(self.p, self.pid, self.data, c, self.frames).run()
        self.assertIn("gọi công cụ ngay", json.dumps(c.seen[1], ensure_ascii=False))
        self.assertEqual(res["summary"]["summary"], "xong")

    def test_with_a_focus_only_the_new_frames_must_be_recorded_but_all_are_seen(self):
        focus = [self.frames[-1]["job_id"]]
        k_last = len(self.frames)
        c = Scripted([[self.record(1)], [self.record(k_last)], [("finish", {"summary": "xong"})]])
        agent = qc_agent.QcAgent(self.p, self.pid, self.data, c, self.frames, focus=focus)
        res = agent.run()
        self.assertEqual([r["job"] for r in res["records"]], focus)             # K1 (reference) was refused, the new frame recorded
        self.assertIn("tham khảo", agent._brief())

    def test_a_block_needs_a_cause_and_an_english_fix(self):
        agent = qc_agent.QcAgent(self.p, self.pid, self.data, None, self.frames)
        issue = [{"type": "a", "description": "b", "evidence": "c", "severity": "block"}]
        out = agent.tool("record", {"k": 1, "verdict": "block", "issues": issue, "root_cause": "none", "fix_en": "Draw five fingers."})
        self.assertIn("root_cause", out[0]["text"])
        out = agent.tool("record", {"k": 1, "verdict": "block", "issues": issue, "root_cause": "model", "fix_en": "Vẽ lại bàn tay năm ngón."})
        self.assertIn("tiếng Anh", out[0]["text"])
        self.assertNotIn(1, agent.records)

    def test_an_approved_frame_the_agent_blocks_is_said(self):
        j = self.frames[0]["job_id"]
        self.p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (j,))
        self.p.conn.commit()
        c = Scripted([[self.record(1, "block", "The left hand has exactly five fingers.")] + [self.record(k) for k in range(2, self.n + 1)],
                      [("finish", {"summary": "xong"})]])
        qc_agent.review_scene(self.p, self.pid, self.scene, c, self.data, self.frames)
        self.assertTrue(self.p.conn.execute("SELECT 1 FROM diag_events WHERE code='qc_agent_approved_flag'").fetchone())
        self.assertEqual(self.p.job(j)["state"], "approved")                    # not changed by an untrusted QC — said instead

    def test_past_half_the_scene_money_it_may_only_record_and_it_always_sees_where_it_stands(self):
        """28/09: 8 turns and 46 pictures spent looking, nothing recorded, then the lock stopped it — all frames 'doubt'."""
        class Paid(Scripted):
            def converse(inner, messages, tools, system="", max_tokens=None):
                llm_runner._count_caps(qc_agent.scene_cap(len(self.frames)) * 0.3)      # each turn costs 30 % of the cap
                return super().converse(messages, tools, system, max_tokens)
        many = [("view_frame", {"k": 1})] * (qc_agent.LOOKS_PER_TURN + 2)
        c = Paid([many, [("view_frame", {"k": 2})], [self.record(k) for k in range(1, self.n + 1)], [("finish", {"summary": "xong"})]])
        res = qc_agent.QcAgent(self.p, self.pid, self.data, c, self.frames).run()
        first = json.dumps(c.seen[1], ensure_ascii=False)
        self.assertEqual(first.count('"type": "image"'), qc_agent.LOOKS_PER_TURN)     # extra looks refused
        self.assertIn("[Trạng thái]", first)
        self.assertIn("HẾT phần điều tra", json.dumps(c.seen[2], ensure_ascii=False))  # 60 % spent: looking refused
        self.assertEqual(res["summary"]["summary"], "xong")

    def test_one_batch_records_every_frame_short_and_the_speed_is_measured(self):
        long = "x" * 500
        items = [{"k": 1, "verdict": "block", "issues": [{"type": "tay", "description": long, "evidence": long, "severity": "block"}],
                  "root_cause": "model", "fix_en": "Draw the left hand with exactly five fingers. " * 10}]
        items += [{"k": k, "verdict": "pass", "issues": [], "root_cause": "none"} for k in range(2, self.n + 1)]
        c = Scripted([[("record_batch", {"items": items})], [("finish", {"summary": "xong"})]])
        res = qc_agent.QcAgent(self.p, self.pid, self.data, c, self.frames).run()
        self.assertEqual(res["steps"], 2)
        r1 = res["records"][0]
        self.assertLessEqual(len(r1["issues"][0]["description"]), qc_agent.TEXT_LIMITS["description"])
        self.assertLessEqual(len(r1["fix_en"]), qc_agent.TEXT_LIMITS["fix_en"])
        self.assertEqual(res["speed"]["frames_judged"], self.n)
        self.assertGreater(res["speed"]["frames_per_minute"], 0)

    def test_a_client_without_tool_use_is_refused_clearly(self):
        with self.assertRaises(llm_runner.LlmError) as e:
            qc_agent.QcAgent(self.p, self.pid, self.data, llm_runner.MockLlm(), self.frames).run()
        self.assertEqual(e.exception.code, "config")


if __name__ == "__main__":
    unittest.main()
