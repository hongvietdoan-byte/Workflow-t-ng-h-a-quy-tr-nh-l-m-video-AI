"""tools/recover_clips.py (W14): finds paid ClipAI tasks the dashboard wrongly marked failed, beyond the first list page, shows the
provider's own failure reason, downloads finished clips to recovered/ — never submits, never writes the database."""
import importlib.util
import json
import os
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse

from core.adapters.clipai import ClipAIVideoProvider
from core.adapters.http import HttpResponse
from core.cost import record_usage
from core.db import connect
from core.pipeline import Pipeline

_spec = importlib.util.spec_from_file_location("recover_clips", os.path.join(os.path.dirname(__file__), "..", "tools", "recover_clips.py"))
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)


def fake_clipai(tasks_by_type, calls):
    """video-list pages of 50 (newest first) + a download host."""
    def transport(method, url, headers, body, timeout):
        calls.append((method, url))
        if "cdn.example" in url:
            return HttpResponse(200, b"MP4DATA")
        q = parse_qs(urlparse(url).query)
        assert method == "GET" and "video-list" in url, url      # nothing is ever submitted or deleted
        rows = tasks_by_type.get(int(q["task_type"][0]), [])
        page, size = int(q["page"][0]), int(q["pageSize"][0])
        return HttpResponse(200, json.dumps({"code": 0, "data": {"data": rows[(page - 1) * size: page * size]}}).encode())
    return transport


class RecoverClipsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "m.sqlite")
        c = connect(self.db)
        p = Pipeline(c)
        pid = p.create_project("V2")
        s1, s2, s3 = (p.create_scene(pid, i) for i in (1, 2, 3))

        def sent(scene, ext, note):
            jid = p.create_job(scene, "video_gen")
            c.execute("UPDATE jobs SET external_id=?, model='kling' WHERE id=?", (ext, jid))
            record_usage(c, jid, "video", "clipai", "kling-v3-omni", "std", 15, "second")
            p.start(jid)
            p.fail(jid, note)
            return jid

        self.lost = sent(s1, "omni:T-OLD", "not_found: task not found in the first list page")
        self.copyright = sent(s2, "omni:T-CR", "risk_control: The request failed because the output video may be related to copyright")
        self.gone = sent(s3, "omni:T-GONE", "not_found: task not found in the first list page")
        c.commit()
        c.close()
        filler = [{"task_id": f"F{i}", "task_status": 2, "video_url": "https://cdn.example/f.mp4"} for i in range(60)]
        self.tasks = {6: filler + [{"task_id": "T-OLD", "task_status": 2, "video_url": "https://cdn.example/old.mp4", "id": 7},
                                   {"task_id": "T-CR", "task_status": 3, "task_status_msg": "output video may be related to copyright "
                                    "restrictions: character 'Kelly' (Free Fire)", "fail_code": "OutputVideoSensitiveContentDetected"}]}

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_tasks_past_the_first_page_and_downloads_only_finished_ones(self):
        calls = []
        provider = ClipAIVideoProvider("tok", transport=fake_clipai(self.tasks, calls))
        before = os.path.getmtime(self.db)
        conn = rc.open_ro(self.db)
        data = os.path.join(self.tmp.name, "projects")
        res = rc.recover(conn, provider, data, max_pages=5, download=True, pause=0, log=lambda *_: None)
        conn.close()
        by_job = {r["job"]: r for r in res["rows"]}
        self.assertEqual(by_job[self.lost]["clipai"], "XONG")                   # on page 2: the dashboard only looked at page 1
        self.assertTrue(by_job[self.lost]["paid"])
        self.assertTrue(os.path.exists(os.path.join(data, "1", "recovered", f"job_{self.lost}_S01.mp4")))
        self.assertEqual(by_job[self.copyright]["clipai"], "thất bại")
        self.assertIn("character 'Kelly' (Free Fire)", res["text"])            # the provider's own words, in full
        self.assertIn("fail_code=OutputVideoSensitiveContentDetected", res["text"])
        self.assertEqual(by_job[self.gone]["clipai"], "không thấy")
        self.assertIsNone(by_job[self.gone]["file"])
        self.assertTrue(all(m == "GET" for m, _ in calls))                      # read-only towards ClipAI
        self.assertEqual(os.path.getmtime(self.db), before)                    # and towards the database
        self.assertFalse(os.path.exists(os.path.join(data, "1", "videos")))    # never slipped into the final cut's folder

    def test_without_download_nothing_is_fetched(self):
        calls = []
        provider = ClipAIVideoProvider("tok", transport=fake_clipai(self.tasks, calls))
        conn = rc.open_ro(self.db)
        res = rc.recover(conn, provider, os.path.join(self.tmp.name, "p"), max_pages=5, pause=0, log=lambda *_: None)
        conn.close()
        self.assertFalse(any("cdn.example" in u for _, u in calls))
        self.assertIn("**ClipAI đã làm XONG: 1**", res["text"])
        self.assertIn("omni 2 trang / 62 task", res["text"])                    # how far the list was read
        self.assertIn("đã hết danh sách", res["text"])

    def test_reconcile_compares_the_ledger_with_the_real_clipai_cost(self):
        self.tasks[6][-2]["cost"] = 90                                          # finished: ClipAI charged it
        self.tasks[6][-1]["cost"] = 0                                           # copyright block: free
        provider = ClipAIVideoProvider("tok", transport=fake_clipai(self.tasks, []))
        conn = rc.open_ro(self.db)
        res = rc.reconcile(conn, provider, max_pages=5, pause=0, log=lambda *_: None)
        conn.close()
        m = res["models"]["kling"]
        self.assertEqual((m["n"], m["cost"], m["free"], m["unseen"]), (3, 90.0, 1, 1))
        self.assertAlmostEqual(m["usd"], 3 * 15 * 0.08)
        self.assertIn("| kling | 3 | $3.60 | 90 | 0.01333 | 1 | 1 |", res["text"])   # $1.20 of the ledger for 90 units
        self.assertIn("Task lệch giữa hai bên", res["text"])


if __name__ == "__main__":
    unittest.main()
