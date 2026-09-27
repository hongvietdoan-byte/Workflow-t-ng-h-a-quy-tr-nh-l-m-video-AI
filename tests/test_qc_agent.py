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
        self.seen.append(copy.deepcopy(messages[-1]))    # prune() later rewrites old turns in place
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

    def test_out_of_steps_the_unchecked_frames_are_doubts_not_passes(self):
        c = Scripted([[("view_frame", {"k": 1})]] * (qc_agent.MAX_STEPS + 2))
        res = qc_agent.QcAgent(self.p, self.pid, self.data, c, self.frames).run()
        self.assertEqual({r["verdict"] for r in res["records"]}, {"doubt"})
        self.assertEqual(res["steps"], qc_agent.MAX_STEPS)

    def test_old_pictures_leave_the_conversation(self):
        img = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "x"}}
        msgs = [{"role": "user", "content": [{"type": "text", "text": "brief"}, img]}]
        def turns(n):
            for i in range(n):
                msgs.append({"role": "assistant", "content": [{"type": "tool_use", "id": str(i), "name": "view_frame", "input": {}}]})
                msgs.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": str(i),
                                                          "content": [{"type": "text", "text": "K"}, dict(img)]}]})

        def with_img():
            return [m for m in msgs[1:] if m["role"] == "user" and any(b.get("type") == "image" for b in m["content"][0]["content"])]
        turns(qc_agent.MAX_HISTORY_IMAGES)
        self.assertFalse(qc_agent.prune(msgs))                                 # in a batch only: the cache survives until then
        self.assertEqual(len(with_img()), qc_agent.MAX_HISTORY_IMAGES)
        turns(1)
        self.assertTrue(qc_agent.prune(msgs))
        self.assertEqual(len(with_img()), qc_agent.KEEP_IMAGE_TURNS)
        self.assertTrue(any(b.get("type") == "image" for b in msgs[0]["content"]))     # the overview stays

    def test_a_rolling_cache_mark_on_the_newest_message_only(self):
        msgs = [{"role": "user", "content": [{"type": "text", "text": "brief", "cache_control": {"type": "ephemeral"}}]},
                {"role": "assistant", "content": [{"type": "text", "text": "a"}]},
                {"role": "user", "content": [{"type": "text", "text": "b"}]}]
        qc_agent.mark_cache(msgs)
        msgs += [{"role": "assistant", "content": [{"type": "text", "text": "c"}]}, {"role": "user", "content": [{"type": "text", "text": "d"}]}]
        qc_agent.mark_cache(msgs)
        marked = [i for i, m in enumerate(msgs) for b in m["content"] if "cache_control" in b]
        self.assertEqual(marked, [0, 4])                                       # the brief + the newest message (≤ 4 breakpoints)

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
        self.assertIn(f"${qc_agent.SCENE_CAP_USD:.2f}", brief)
        self.assertIn("BÊN THÂN NGƯỜI", brief)                               # the playbook's body-side rule (A1, 28/09)
        self.assertIn("G1", brief)

    def test_a_block_without_a_fix_sentence_is_refused(self):
        agent = qc_agent.QcAgent(self.p, self.pid, self.data, None, self.frames)
        out = agent.tool("record", {"k": 1, "verdict": "block", "issues": [{"type": "a", "description": "b", "evidence": "c",
                                                                               "severity": "block"}], "root_cause": "model", "fix_en": ""})
        self.assertIn("fix_en", out[0]["text"])
        self.assertNotIn(1, agent.records)

    def test_the_inspection_plan_comes_from_the_profiles(self):
        from unittest import mock
        prof = {"approved": True, "must_keep": "gauntlet on the LEFT arm", "view_notes": {"from_behind": "…"}}
        frames = [{"k": 1, "data": {"characters": ["KENTA"]}}, {"k": 2, "data": {"characters": ["KENTA"]}}]
        with mock.patch("core.assets.standard_for", return_value=prof):
            plan = qc_agent.inspection_plan(self.p.conn, self.pid, frames)
        self.assertTrue(any("KENTA" in x and "[1, 2]" in x for x in plan))


if __name__ == "__main__":
    unittest.main()
