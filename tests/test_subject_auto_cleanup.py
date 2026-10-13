"""Kho chủ thể ClipAI 13/10: (1) xóa hàng loạt không bị ClipAI chặn 'Too many requests' (code 1130) — đọc danh sách 1 lần trước +
1 lần sau cả lô, 1130 → chờ đúng số giây ClipAI báo rồi thử lại (tối đa 3 lần, có trần); (2) giao bản cuối / cất dự án → tự xóa khỏi Kho
các khung ảnh ĐÃ BỊ LOẠI của dự án đó (cờ subject_auto_cleanup), chạy nền, lỗi chỉ ghi chẩn đoán VÀNG. Thư viện giả lập, không gọi API thật."""
import json
import os
import unittest
from unittest import mock

from core import archive, delivered, subjects
from core.adapters.clipai_subjects import ClipAISubjectLibrary
from core.adapters.http import call_rate_limited, retry_after_seconds
from core.db import connect
from core.pipeline import Pipeline
from core.providers import ProviderError
from tests.test_adapters import TOKEN, FakeTransport, HttpResponse, ok
from tests.test_subject_library_cleanup import FullLibrary, asset

BUSY = {"code": 1130, "msg": "Too many requests, please retry after 2s", "data": None}


def busy():
    return HttpResponse(200, json.dumps(BUSY).encode())


class RateLimitRetryTests(unittest.TestCase):
    def test_retry_after_seconds_reads_the_clipai_message(self):
        self.assertEqual(retry_after_seconds("API error (code=1130): Too many requests, please retry after 7s"), 7.0)
        self.assertIsNone(retry_after_seconds("API error (code=400): bad input"))

    def test_waits_what_clipai_said_then_succeeds(self):
        slept, calls = [], []

        def fn():
            calls.append(1)
            if len(calls) < 3:
                raise ProviderError("API error (code=1130): Too many requests, please retry after 2s", code="api_error", transient=True)
            return "ok"
        self.assertEqual(call_rate_limited(fn, slept.append), "ok")
        self.assertEqual(len(slept), 2)
        self.assertTrue(all(2 <= s <= 4 for s in slept))

    def test_still_busy_after_three_retries_is_said_not_swallowed(self):
        slept = []

        def fn():
            raise ProviderError("API error (code=1130): Too many requests, please retry after 1s", code="api_error", transient=True)
        with self.assertRaises(ProviderError) as e:
            call_rate_limited(fn, slept.append)
        self.assertEqual(len(slept), 3)
        self.assertEqual(e.exception.code, "rate_limited")

    def test_total_wait_is_capped(self):
        slept = []

        def fn():
            raise ProviderError("API error (code=1130): Too many requests, please retry after 500s", code="api_error", transient=True)
        with self.assertRaises(ProviderError):
            call_rate_limited(fn, slept.append, max_total=60)
        self.assertEqual(slept, [])

    def test_other_errors_are_not_retried(self):
        slept = []

        def fn():
            raise ProviderError("invalid token", code="auth")
        with self.assertRaises(ProviderError) as e:
            call_rate_limited(fn, slept.append)
        self.assertEqual((e.exception.code, slept), ("auth", []))


class BatchDeleteTests(unittest.TestCase):
    def setUp(self):
        self.t = FakeTransport()
        self.slept = []
        self.lib = ClipAISubjectLibrary(TOKEN, "https://clipai.example", self.t, sleep=self.slept.append, poll_sec=1, timeout_sec=5)
        self.assets = [asset(i) for i in range(1, 8)]
        self.t.on("GET", "/api/kling/seedance-user-asset-list", lambda call: ok({"count": len(self.assets), "assets": list(self.assets)}))
        self.n = 0

        def drop(call):
            self.n += 1
            if self.n % 3 == 0:                     # every third call: ClipAI says slow down
                return busy()
            aid = json.loads(call["body"].decode("utf-8"))["asset_id"]
            self.assets = [a for a in self.assets if a["asset_id"] != aid]
            return HttpResponse(200, json.dumps({"status": "success", "msg": "ok", "data": None}).encode())
        self.t.on("POST", "/api/kling/seedance-user-asset-delete", drop)

    def lists(self):
        return len([c for c in self.t.calls if c["method"] == "GET"])

    def test_batch_lists_once_before_and_once_after_and_rides_out_1130(self):
        conn = connect()
        res = subjects.delete_assets(conn, self.lib, [f"asset-{i}" for i in range(1, 6)])
        self.assertEqual(res["deleted"], [f"asset-{i}" for i in range(1, 6)])
        self.assertEqual(res["errors"], [])
        self.assertEqual(self.lists(), 2)                           # overview (before) + one check after the whole batch
        self.assertTrue(self.slept and all(s >= 2 for s in self.slept))

    def test_asset_still_listed_after_the_batch_is_delete_unverified(self):
        self.t.on("POST", "/api/kling/seedance-user-asset-delete", ok(None))   # says done, deletes nothing
        res = subjects.delete_assets(connect(), self.lib, ["asset-1", "asset-2"])
        self.assertEqual(res["deleted"], [])
        self.assertEqual([(a, "delete_unverified" in m) for a, m in res["errors"]], [("asset-1", True), ("asset-2", True)])
        self.assertEqual(self.lists(), 2)

    def test_single_delete_keeps_its_checks(self):
        self.assertEqual(self.lib.delete("asset-1")["asset_id"], "asset-1")
        with self.assertRaises(ProviderError) as e:
            self.lib.delete("asset-404")
        self.assertEqual(e.exception.code, "not_found")


class AutoCleanupTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.conn = self.p.conn
        self.pid = self.p.create_project("giao")
        self.other = self.p.create_project("khác")
        sid = self.p.create_scene(self.pid, 1, "CẢNH 1")
        osid = self.p.create_scene(self.other, 1, "CẢNH 1")
        self.rej = self.p.create_job(sid)
        self.ok = self.p.create_job(sid)
        self.orej = self.p.create_job(osid)
        self.conn.execute("UPDATE jobs SET state='rejected' WHERE id IN (?,?)", (self.rej, self.orej))
        self.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (self.ok,))
        subjects._pictures_table(self.conn)
        pics = [("s1", f"P{self.pid}_S1_frame_aaa", "asset-1", f"data/projects/{self.pid}/refs_clean/job_{self.rej}_ab12_marked_none.png"),
                ("s2", f"P{self.pid}_S1_frame_bbb", "asset-2", f"data/projects/{self.pid}/refs_clean/job_{self.ok}_cd34_marked_none.png"),
                ("s3", f"P{self.pid}_place_ccc", "asset-3", f"data/projects/{self.pid}/places/plate.png"),
                ("s4", f"P{self.other}_S1_frame_ddd", "asset-4", f"data/projects/{self.other}/refs_clean/job_{self.orej}_ef_marked_none.png")]
        for sha, name, aid, path in pics:
            self.conn.execute("INSERT INTO seedance_subject_pictures (sha, name, asset_id, asset_uri, status, path) VALUES (?,?,?,?,?,?)",
                              (sha, name, aid, f"asset://{aid}", "active", path))
        self.conn.execute("INSERT INTO characters (project_id, name, description, subject_asset_id, subject_asset_uri, subject_status) "
                          "VALUES (?,?,'',?,?,?)", (self.pid, "Kelly", "asset-5", "asset://asset-5", "active"))
        self.conn.commit()
        self.lib = FullLibrary([asset(i) for i in range(1, 6)], full=False)
        self.patches = [mock.patch("core.adapters.factory.subject_library", return_value=self.lib),
                        mock.patch.dict(os.environ, {"FEATURE_SUBJECT_AUTO_CLEANUP": ""})]
        for pt in self.patches:
            pt.start()
            self.addCleanup(pt.stop)

    def diags(self):
        return [(r["severity"], r["message"]) for r in self.conn.execute(
            "SELECT severity, message FROM diag_events WHERE code='subject_cleanup' AND project_id=?", (self.pid,))]

    def test_delivery_deletes_only_the_rejected_frames_of_that_project(self):
        delivered.mark(self.conn, self.pid, "D:/out/x.mp4")
        self.assertEqual(self.lib.deleted, ["asset-1"])
        self.assertIsNone(subjects.picture_row(self.conn, "s1"))
        self.assertTrue(any("asset-1" in m for s, m in self.diags() if s == "info"))

    def test_archive_does_the_same(self):
        archive._move(self.p, put_away=self.pid)
        self.assertEqual(self.lib.deleted, ["asset-1"])

    def test_flag_off_touches_nothing(self):
        with mock.patch.dict(os.environ, {"FEATURE_SUBJECT_AUTO_CLEANUP": "0"}):
            delivered.mark(self.conn, self.pid, "D:/out/x.mp4")
        self.assertEqual(self.lib.deleted, [])

    def test_network_error_is_a_yellow_note_and_the_delivery_still_counts(self):
        def boom(asset_id):
            raise ProviderError("network error: timed out", code="network", transient=True)
        self.lib.delete = boom
        delivered.mark(self.conn, self.pid, "D:/out/x.mp4")
        self.assertTrue(delivered.is_delivered(self.conn, self.pid))
        self.assertTrue(any(s == "warn" and "asset-1" in m for s, m in self.diags()))
        self.assertIsNotNone(subjects.picture_row(self.conn, "s1"))          # kept → tried again next time

    def test_no_token_is_a_yellow_note(self):
        with mock.patch("core.adapters.factory.subject_library", side_effect=ProviderError("CLIPAI_TOKEN is not set", code="config")):
            delivered.mark(self.conn, self.pid, "D:/out/x.mp4")
        self.assertTrue(delivered.is_delivered(self.conn, self.pid))
        self.assertTrue(any(s == "warn" for s, _ in self.diags()))

    def test_frame_shared_with_another_live_project_is_kept(self):
        self.conn.execute("UPDATE seedance_subject_pictures SET name=? WHERE sha='s1'", (f"P{self.other}_S1_frame_aaa",))
        self.conn.commit()
        delivered.mark(self.conn, self.pid, "D:/out/x.mp4")
        self.assertEqual(self.lib.deleted, [])

    def test_rejected_frame_that_is_the_source_of_a_kept_video_is_kept(self):
        sid = self.conn.execute("SELECT scene_id FROM jobs WHERE id=?", (self.rej,)).fetchone()[0]
        vid = self.p.create_job(sid, "video_gen")
        self.conn.execute("UPDATE jobs SET state='approved', source_job_id=? WHERE id=?", (self.rej, vid))
        self.conn.commit()
        delivered.mark(self.conn, self.pid, "D:/out/x.mp4")
        self.assertEqual(self.lib.deleted, [])

    def test_asset_with_another_picture_row_that_is_not_a_rejected_frame_is_kept(self):
        self.conn.execute("INSERT INTO seedance_subject_pictures (sha, name, asset_id, asset_uri, status, path) VALUES (?,?,?,?,?,?)",
                          ("s1b", f"P{self.pid}_S1_frame_zzz", "asset-1", "asset://asset-1", "active",
                           f"data/projects/{self.pid}/refs_clean/job_{self.ok}_zz_marked_none.png"))
        self.conn.commit()
        self.assertEqual(subjects.rejected_frame_assets(self.conn, self.pid), [])

    def test_a_second_schedule_while_one_runs_for_the_project_is_skipped(self):
        started = []
        with mock.patch("core.place_refs._db_path", return_value="X:/fake.db"),                 mock.patch.object(subjects, "_spawn", side_effect=lambda fn: started.append(fn)):
            self.assertTrue(subjects.schedule_auto_cleanup(self.conn, self.pid, "giao"))
            self.assertFalse(subjects.schedule_auto_cleanup(self.conn, self.pid, "cất"))
        self.assertEqual(len(started), 1)
        subjects._RUNNING.discard(self.pid)


if __name__ == "__main__":
    unittest.main()
