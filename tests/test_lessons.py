import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from core import knowledge, lessons, llm_runner, research
from core.db import connect
from core.pipeline import Pipeline


def make_rejects(p, projects, notes):
    """`notes` rejected images spread over `projects` projects (each with one scene)."""
    scene_ids = []
    for i in range(projects):
        pid = p.create_project(f"p{i}", "human_qc", 0.85, 2)
        p.conn.execute("INSERT INTO scenes (project_id, idx, data, state) VALUES (?,?,?,?)",
                       (pid, 1, '{"image_prompt": "a hero on a roof"}', "ready"))
        scene_ids.append((pid, p.conn.execute("SELECT MAX(id) FROM scenes").fetchone()[0]))
    for n, note in enumerate(notes):
        pid, sid = scene_ids[n % projects]
        job = p.create_job(sid, "image_gen")
        p.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (job,))
        p.conn.commit()
        p.reject(job, "user", note, respawn=False)
    return scene_ids


class LessonTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["KNOWLEDGE_USER_DIR"] = self.dir
        self.p = Pipeline(connect())
        self.conn = self.p.conn

    def tearDown(self):
        os.environ.pop("KNOWLEDGE_USER_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_harvest_is_idempotent_and_classifies_the_mistake(self):
        make_rejects(self.p, 2, ["bàn tay sai, thừa ngón", "sai tay trái"])
        self.assertEqual(lessons.harvest(self.conn), 2)
        self.assertEqual(lessons.harvest(self.conn), 0)                          # nothing is counted twice
        kinds = {c["tag"]: c for c in lessons.clusters(self.conn)}
        self.assertEqual(kinds["hands"]["events"], 2)
        self.assertFalse(kinds["hands"]["ready"])                                # 2 < 3 events: not enough evidence yet

    def test_a_mistake_repeating_across_projects_becomes_a_proposal_only_a_person_can_apply(self):
        make_rejects(self.p, 3, ["bàn tay bị méo", "tay có 6 ngón", "sai bàn tay", "QC 0.61 < mức tối thiểu 0.7 — hand deformed"])
        self.assertEqual(lessons.propose(self.conn, llm_runner.MockLlm()), 1)
        self.assertEqual(lessons.propose(self.conn, llm_runner.MockLlm()), 0)    # not proposed twice
        row = lessons.list_lessons(self.conn, "proposed")[0]
        self.assertEqual(row["group_name"], "director")
        self.assertIn("Quy tắc mẫu", row["body"])
        self.assertEqual(knowledge.user_docs("director"), [])                     # proposing changes nothing yet
        lessons.decide(self.conn, row["id"], True)
        docs = knowledge.user_docs("director")
        self.assertEqual([d["title"] for d in docs], [lessons.DOC_TITLE])
        self.assertIn("Quy tắc mẫu", knowledge.read_doc("director", "user", docs[0]["file"]))
        lessons.decide(self.conn, row["id"], False)                              # withdrawing removes it again
        self.assertEqual(knowledge.user_docs("director"), [])

    def _approved_one(self):
        make_rejects(self.p, 3, ["bàn tay bị méo", "tay có 6 ngón", "sai bàn tay"])
        lessons.propose(self.conn, llm_runner.MockLlm())
        row = lessons.list_lessons(self.conn, "proposed")[0]
        lessons.decide(self.conn, row["id"], True)
        return row

    def test_a_too_big_new_document_keeps_the_old_one_and_the_proposal(self):
        """S14.4 C1b (04/10): the old document was deleted BEFORE the new one was checked → a failure lost both."""
        first = self._approved_one()
        before = knowledge.user_docs("director")
        self.conn.execute("INSERT INTO lessons (created_at, group_name, key, title, body, source, evidence, state)"
                          " VALUES ('x','director','k2','To','" + "x" * (knowledge.MAX_DOC_CHARS + 10) + "','mistakes','{}','proposed')")
        self.conn.commit()
        big = self.conn.execute("SELECT id FROM lessons WHERE key='k2'").fetchone()["id"]
        with self.assertRaises(lessons.LessonError) as cm:
            lessons.decide(self.conn, big, True)
        self.assertIn("ký tự", str(cm.exception))                                  # Vietnamese, says what to do
        self.assertEqual(self.conn.execute("SELECT state FROM lessons WHERE id=?", (big,)).fetchone()["state"], "proposed")
        after = knowledge.user_docs("director")
        self.assertEqual([d["file"] for d in after], [d["file"] for d in before])  # the old document is still there
        self.assertIn(first["body"][:20], knowledge.read_doc("director", "user", after[0]["file"]))

    def test_the_cap_check_does_not_count_the_document_being_replaced(self):
        self._approved_one()
        used = sum(d["chars"] for d in knowledge.user_docs("director"))
        filler = "y" * (knowledge.MAX_USER_CHARS - used - 5)                        # room left: 5 chars + the old doc itself
        for i in range(0, len(filler), knowledge.MAX_DOC_CHARS):
            knowledge.add_doc("director", f"f{i}.md", filler[i:i + knowledge.MAX_DOC_CHARS].encode())
        lessons.sync_knowledge(self.conn, "director")                              # same text again: fits once the old one goes
        self.assertEqual(sum(1 for d in knowledge.user_docs("director") if d["title"] == lessons.DOC_TITLE), 1)

    def test_the_lessons_buttons_go_through_act(self):
        src = open(os.path.join(os.path.dirname(__file__), "..", "dashboard", "admin.py"), encoding="utf-8").read()
        calls = [ln for ln in src.splitlines() if "lessons.decide(" in ln]
        self.assertTrue(calls)
        self.assertEqual([ln for ln in calls if "act(lambda" not in ln], [])     # an error shows a message, not a crash

    def test_rejected_proposals_are_not_proposed_again(self):
        make_rejects(self.p, 3, ["tay sai"] * 4)
        lessons.propose(self.conn)
        lessons.decide(self.conn, lessons.list_lessons(self.conn)[0]["id"], False)
        self.assertEqual(lessons.propose(self.conn), 0)

    def test_risk_control_blocks_are_learned_from_too(self):
        scenes = make_rejects(self.p, 3, [])
        for pid, sid in scenes:
            job = self.p.create_job(sid, "video_gen")
            self.conn.execute("INSERT INTO content_moderation_failures (job_id, provider, error_message, at) VALUES (?,?,?,?)",
                              (job, "clipai", "content policy violation", "2026-09-20T00:00:00+00:00"))
        self.conn.commit()
        self.assertEqual(lessons.propose(self.conn), 1)
        row = lessons.list_lessons(self.conn, "proposed")[0]
        self.assertEqual((row["group_name"], row["key"]), ("motion", "mistake:risk_control"))


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["KNOWLEDGE_USER_DIR"] = self.dir
        self.conn = connect()

    def tearDown(self):
        os.environ.pop("KNOWLEDGE_USER_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_research_only_proposes_and_never_applies(self):
        r = research.run(self.conn, llm_runner.MockLlm())
        self.assertGreater(r["proposed"], 0)
        self.assertEqual(r["errors"], [])
        for row in lessons.list_lessons(self.conn):
            self.assertEqual((row["state"], row["source"]), ("proposed", "research"))
        self.assertEqual(knowledge.user_docs("director"), [])
        again = research.run(self.conn, llm_runner.MockLlm())
        self.assertEqual(again["proposed"], 0)                                   # same findings are not duplicated

    def test_a_finding_that_is_not_an_object_is_counted_not_fatal(self):
        """S14.4 C1b (04/10): 'findings': ["text", {...}] crashed the whole round on f.get()."""
        class Mixed:
            def complete_with_search(self, prompt, max_uses=3):
                return llm_runner.LlmReply('{"findings": ["chỉ là chữ", {"title": "Ánh sáng ven", "rule": "Dùng rim light", '
                                           '"url": "https://x"}]}', 1, 1)

        r = research.run(self.conn, Mixed(), {"director": ["ánh sáng"]})
        self.assertEqual(r["proposed"], 1)
        self.assertEqual(len(r["errors"]), 1)
        self.assertIn("director", r["errors"][0])

    def test_a_bad_answer_is_reported_not_fatal(self):
        class Junk:
            def complete_with_search(self, prompt, max_uses=3):
                return llm_runner.LlmReply("không phải json", 1, 1)

        r = research.run(self.conn, Junk())
        self.assertEqual(r["proposed"], 0)
        self.assertTrue(r["errors"])

    def test_monthly_schedule_needs_the_switch_and_waits_thirty_days(self):
        self.assertFalse(research.enabled(self.conn))                            # off by default (it costs money)
        self.assertTrue(research.due(self.conn))
        research.run(self.conn, llm_runner.MockLlm())
        self.assertFalse(research.due(self.conn))
        old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(timespec="seconds")
        lessons.set_meta(self.conn, "research_last_run", old)
        self.assertTrue(research.due(self.conn))

    def test_background_round_runs_only_when_switched_on_and_due(self):
        import time
        db = os.path.join(self.dir, "m.sqlite")
        conn = connect(db)
        self.assertFalse(research.maybe_run_in_background(db, lambda: llm_runner.MockLlm()))   # switch is off
        lessons.set_meta(conn, "research_monthly", "1")
        self.assertFalse(research.maybe_run_in_background(db, lambda: None))                   # no API key
        self.assertTrue(research.maybe_run_in_background(db, lambda: llm_runner.MockLlm()))
        deadline = time.time() + 10
        while time.time() < deadline and not lessons.list_lessons(connect(db)):
            time.sleep(0.05)
        self.assertTrue(lessons.list_lessons(connect(db), "proposed"))
        self.assertFalse(research.maybe_run_in_background(db, lambda: llm_runner.MockLlm()))   # not due again


class SearchRequestTests(unittest.TestCase):
    def test_search_request_carries_the_web_search_tool(self):
        seen = {}

        def transport(method, url, headers, body, timeout):
            import json
            from core.adapters.http import HttpResponse
            seen["body"] = json.loads(body)
            return HttpResponse(200, json.dumps({"content": [{"type": "text", "text": "ok"}],
                                                 "usage": {"input_tokens": 1, "output_tokens": 1}}).encode())

        client = llm_runner.AnthropicClient("k" * 20, transport=transport)
        self.assertEqual(client.complete_with_search("hỏi", 2).text, "ok")
        self.assertEqual(seen["body"]["tools"][0]["max_uses"], 2)
        client.complete("hỏi")
        self.assertNotIn("tools", seen["body"])                                   # normal calls stay unchanged


if __name__ == "__main__":
    unittest.main()
