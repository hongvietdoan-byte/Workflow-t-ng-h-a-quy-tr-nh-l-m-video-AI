"""C2 (14/10): "Chờ bạn" thừa ở dự án đã xong — ca dựng lại từ CSDL thật 13/10 (#27: bản chờ duyệt cũ khi shot đã có bản mới được duyệt,
lỗi gen cũ khi shot đã có bản dùng, mục Tổ rà soát cũ hơn kết quả được duyệt; #24: dự án đã giao)."""
import os
import tempfile
import unittest
from unittest import mock

from core import delivered, inbox, inbox_clean, perf
from core.db import connect
from core.pipeline import Pipeline


class InboxCleanTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp(prefix="inbox_clean_")          # never the real data/projects
        env = mock.patch.dict(os.environ, {"PIPELINE_DATA": self.data})
        env.start()
        self.addCleanup(env.stop)
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("p27")
        self.sids = [self.p.create_scene(self.pid, i, f"s{i}") for i in range(1, 6)]

    # ---- helpers -------------------------------------------------------------------------------------------------------------------
    def job(self, sid, typ, state, approved_at=None):
        jid = self.p.create_job(sid, typ)
        self.p.conn.execute("UPDATE jobs SET state=? WHERE id=?", (state, jid))
        if state == "approved":
            self.p.conn.execute("INSERT INTO job_events (job_id, from_state, to_state, actor, note, at) VALUES (?,?,?,?,?,?)",
                                (jid, "pending_review", "approved", "user", None, approved_at or "2026-10-13T10:00:00+00:00"))
        self.p.conn.commit()
        return jid

    def finding(self, sid, at, level="do"):
        cur = self.p.conn.execute("INSERT INTO change_findings (project_id, scene_id, source, level, khau, msg, at) VALUES (?,?,?,?,?,?,?)",
                                  (self.pid, sid, "claude", level, "motion", "lệch", at))
        self.p.conn.commit()
        return cur.lastrowid

    def texts(self):
        return [i["text"] for i in inbox.items(self.p.conn, "", can_money=False) if i["project_id"] == self.pid]

    def needs_review(self):
        return next(r["needs_review"] for r in perf.portfolio_rows(self.p.conn, self.data) if r["id"] == self.pid)

    def state(self, jid):
        return self.p.conn.execute("SELECT state FROM jobs WHERE id=?", (jid,)).fetchone()[0]

    # ---- ca ------------------------------------------------------------------------------------------------------------------------
    def test_older_pending_take_when_the_shot_has_a_newer_approved_one_is_not_counted_and_is_rejected_on_clean(self):
        old = self.job(self.sids[0], "video_gen", "pending_review")
        new = self.job(self.sids[0], "video_gen", "approved")
        real = self.job(self.sids[1], "video_gen", "pending_review")        # a shot with nothing approved: real work
        self.assertEqual(self.needs_review(), 1)
        self.assertIn("Duyệt 1 clip đang chờ", self.texts())
        self.assertTrue(any(f"job {old}" in x and f"job {new}" in x for x in inbox_clean.preview(self.p.conn, self.pid)))
        res = inbox_clean.clean(self.p, self.pid, "viet@garena.vn")
        self.assertEqual(res["rejected"], 1)
        self.assertEqual((self.state(old), self.state(new), self.state(real)), ("rejected", "approved", "pending_review"))
        ev = self.p.conn.execute("SELECT actor, note FROM job_events WHERE job_id=? AND to_state='rejected'", (old,)).fetchone()
        self.assertEqual(ev["actor"], "viet@garena.vn")
        self.assertIn("dọn việc thừa", ev["note"])

    def test_newer_pending_take_after_an_older_approved_one_still_counts(self):
        self.job(self.sids[0], "video_gen", "approved")
        newer = self.job(self.sids[0], "video_gen", "pending_review")      # e.g. a replacement the person asked for
        self.assertEqual(self.needs_review(), 1)
        self.assertEqual(inbox_clean.action_ids(self.p.conn, self.pid), [])
        inbox_clean.clean(self.p, self.pid)
        self.assertEqual(self.state(newer), "pending_review")

    def test_old_generation_error_is_not_counted_when_the_shot_has_a_usable_take_but_is_kept(self):
        self.job(self.sids[0], "video_gen", "approved")
        failed = self.job(self.sids[0], "video_gen", "failed")
        lone = self.job(self.sids[1], "video_gen", "failed")
        line = next(x for x in self.texts() if x.startswith("Gen clip lỗi"))
        self.assertIn("1 shot", line)
        self.assertIn("clip shot 2", line)
        inbox_clean.clean(self.p, self.pid)
        self.assertEqual((self.state(failed), self.state(lone)), ("failed", "failed"))

    def test_review_finding_older_than_the_shots_approved_result_is_closed_newer_one_stays(self):
        old = self.finding(self.sids[0], "2026-10-13T09:00:00Z")
        self.job(self.sids[0], "video_gen", "approved", approved_at="2026-10-13T09:30:00+00:00")
        clip_hold = self.finding(self.sids[2], "2026-10-13T09:00:00Z")       # motion item: a later approved PICTURE does not answer it
        self.job(self.sids[2], "image_gen", "approved", approved_at="2026-10-13T09:30:00+00:00")
        later = self.finding(self.sids[1], "2026-10-13T12:00:00Z")
        self.job(self.sids[1], "image_gen", "approved", approved_at="2026-10-13T11:00:00+00:00")
        self.assertIn("🔴 Giữ gen — 2 mục lệch sau thay đổi (shot 2,3)", self.texts())
        res = inbox_clean.clean(self.p, self.pid, "viet@garena.vn")
        self.assertEqual(res["resolved"], 1)
        st = dict(self.p.conn.execute("SELECT id, status FROM change_findings").fetchall())
        self.assertEqual((st[old], st[later], st[clip_hold]), ("resolved", "open", "open"))
        by = self.p.conn.execute("SELECT resolved_by FROM change_findings WHERE id=?", (old,)).fetchone()[0]
        self.assertIn("viet@garena.vn", by)

    def test_delivered_project_counts_nothing_and_only_changes_takes_that_have_a_replacement(self):
        approved = self.job(self.sids[0], "video_gen", "approved")
        older_than_used = self.job(self.sids[0], "image_gen", "approved")
        stray = self.job(self.sids[0], "video_gen", "pending_review")      # newer than the approved clip, but the project shipped
        alone = self.job(self.sids[1], "video_gen", "pending_review")      # no other take: may be in the delivered cut
        self.finding(self.sids[2], "2026-10-13T12:00:00Z", level="vang")
        delivered.mark(self.p.conn, self.pid, os.path.join(self.data, "out.mp4"))
        self.assertEqual(self.needs_review(), 0)
        self.assertFalse([x for x in self.texts() if x.startswith(("Duyệt", "🔴", "Gen"))] + [x for x in self.texts() if "mục lệch" in x])
        inbox_clean.clean(self.p, self.pid)
        self.assertEqual((self.state(stray), self.state(alone), self.state(approved), self.state(older_than_used)),
                         ("rejected", "pending_review", "approved", "approved"))

    def test_preview_is_empty_for_a_project_with_only_real_work_and_a_broken_check_counts_everything(self):
        self.job(self.sids[0], "image_gen", "pending_review")
        self.assertEqual(inbox_clean.preview(self.p.conn, self.pid), [])
        old = self.job(self.sids[1], "video_gen", "pending_review")
        self.job(self.sids[1], "video_gen", "approved")
        with mock.patch.object(inbox_clean, "stale", side_effect=RuntimeError("x")):
            self.assertIn("Duyệt 1 clip đang chờ", self.texts())             # never hides real work when the check breaks
            self.assertEqual(self.needs_review(), 2)
        self.assertEqual(self.state(old), "pending_review")


if __name__ == "__main__":
    unittest.main()
