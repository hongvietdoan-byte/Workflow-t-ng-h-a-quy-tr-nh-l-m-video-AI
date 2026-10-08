"""08/10 (#24 shot 7): ảnh vẽ lại v2 tệ hơn v1 (v1 đã bị loại khi bấm ↻ Vẽ lại, tệp vào thùng rác) — dải phiên bản cho XEM v1 nhưng không
chọn lại được; Claude phải chữa tay (trash.restore + reject v2 + v1 → approved). #22 07/10 tương tự cho clip (job 560/569).
`Pipeline.use_older_take` làm việc đó cho người dùng, không tốn tiền (không tạo job)."""
import os
import tempfile
import unittest

from core import final_cut, takes, trash
from core.db import connect
from core.pipeline import Pipeline
from core.states import InvalidTransition, JobState


def _write(path, content: bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    return path


def _read(path):
    with open(path, "rb") as f:
        return f.read()


class Base(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("UOT")
        self.sid = self.p.create_scene(self.pid, 7, "Shot 7")

    def jobs(self):
        return self.p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    def image(self, content: bytes, review=True):
        jid = self.p.create_job(self.sid, "image_gen")
        self.p.start(jid)
        path = _write(os.path.join(self.data, str(self.pid), "images", f"job_{jid}.png"), content)
        self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (path, jid))
        self.p.conn.commit()
        self.p.succeed(jid)
        if review:
            self.p.transition(jid, JobState.PENDING_REVIEW)
        return jid

    def video(self, content: bytes):
        jid = self.p.create_job(self.sid, "video_gen")
        self.p.start(jid)
        dest = final_cut.clip_path(self.data, self.pid, 7)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        takes.make_room(self.p.conn, self.data, self.p.job(jid), dest)
        _write(dest, content)
        self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (dest, jid))
        self.p.conn.commit()
        self.p.succeed(jid)
        return jid


class ImageTests(Base):
    def redrawn(self):
        """#24 shot 7: v1 rejected by ↻ Vẽ lại (file swept into the trash), v2 waiting for review."""
        v1 = self.image(b"v1")
        self.p.reject(v1, "user", "vẽ lại", respawn=False)
        self.assertEqual(trash.sweep_rejected(self.p, self.data, self.pid), 1)
        self.assertFalse(os.path.exists(os.path.join(self.data, str(self.pid), "images", f"job_{v1}.png")))
        v2 = self.image(b"v2")
        return v1, v2

    def test_case_24_old_rejected_take_in_trash_comes_back_approved(self):
        v1, v2 = self.redrawn()
        before = self.jobs()
        path = self.p.use_older_take(v1, data_dir=self.data)
        self.assertEqual(path, os.path.join(self.data, str(self.pid), "images", f"job_{v1}.png"))
        self.assertEqual(_read(path), b"v1")                                    # back where it was
        self.assertIsNone(trash.find_for_job(self.data, self.pid, "images", v1))
        self.assertEqual(self.p.state(v1).value, "approved")
        self.assertEqual(self.p.state(v2).value, "rejected")
        self.assertEqual(self.jobs(), before)                                   # no new take: costs nothing
        notes = [r["note"] for r in self.p.conn.execute("SELECT note FROM review_log WHERE job_id=? ORDER BY id", (v2,))]
        self.assertIn("dùng lại bản v1", notes)
        last = self.p.conn.execute("SELECT decision FROM review_log WHERE job_id=? ORDER BY id DESC LIMIT 1", (v1,)).fetchone()
        self.assertEqual(last["decision"], "approve")

    def test_data_dir_is_read_from_the_result_path(self):
        v1, v2 = self.redrawn()
        self.p.use_older_take(v1)
        self.assertEqual(self.p.state(v1).value, "approved")

    def test_newer_take_running_is_refused_and_nothing_changes(self):
        v1, v2 = self.redrawn()
        v3 = self.p.create_job(self.sid, "image_gen")
        self.p.start(v3)
        with self.assertRaises(InvalidTransition) as e:
            self.p.use_older_take(v1, data_dir=self.data)
        self.assertIn("■ Hủy", str(e.exception))
        self.assertEqual([self.p.state(j).value for j in (v1, v2, v3)], ["rejected", "pending_review", "running"])
        self.assertIsNotNone(trash.find_for_job(self.data, self.pid, "images", v1))   # the file stayed in the trash

    def test_newer_approved_is_reopened_and_queued_cancelled_without_new_takes(self):
        v1 = self.image(b"v1")
        self.p.reject(v1, "user", "vẽ lại", respawn=False)
        v2 = self.image(b"v2")
        self.p.approve(v2)
        v3 = self.p.create_job(self.sid, "image_gen")
        before = self.jobs()
        self.p.use_older_take(v1, data_dir=self.data)                          # v1 file never swept: still in place
        self.assertEqual([self.p.state(j).value for j in (v1, v2, v3)], ["approved", "rejected", "cancelled"])
        self.assertEqual(self.jobs(), before)

    def test_file_gone_for_good_is_a_clear_error_and_nothing_changes(self):
        v1, v2 = self.redrawn()
        for e in trash.items(self.data, self.pid, "images"):
            os.remove(e["path"])
        with self.assertRaises(ValueError) as e:
            self.p.use_older_take(v1, data_dir=self.data)
        self.assertIn("không còn", str(e.exception))
        self.assertEqual([self.p.state(j).value for j in (v1, v2)], ["rejected", "pending_review"])

    def test_only_old_takes_with_a_result_can_be_used(self):
        v1 = self.image(b"v1")
        self.p.approve(v1)
        with self.assertRaises(InvalidTransition):
            self.p.use_older_take(v1, data_dir=self.data)
        q = self.p.create_job(self.sid, "image_gen")
        with self.assertRaises(InvalidTransition):
            self.p.use_older_take(q, data_dir=self.data)


class VideoTests(Base):
    def test_older_clip_becomes_the_shots_take(self):
        v1 = self.video(b"clip-1")
        self.p.reject(v1, "user", "gen lại", respawn=False)
        v2 = self.video(b"clip-2")                                             # make_room moved clip-1 into the trash
        self.p.transition(v2, JobState.PENDING_REVIEW)
        before = self.jobs()
        path = self.p.use_older_take(v1, data_dir=self.data)
        dest = final_cut.clip_path(self.data, self.pid, 7)
        self.assertEqual(os.path.normcase(os.path.abspath(path)), os.path.normcase(os.path.abspath(dest)))
        self.assertEqual(_read(dest), b"clip-1")
        self.assertEqual(self.p.state(v1).value, "approved")
        self.assertEqual(self.p.state(v2).value, "rejected")
        self.assertEqual(takes.chosen(self.p.conn, self.sid)["id"], v1)          # takes.mark: chain / cut use v1
        self.assertEqual(takes.used(self.p.conn, self.sid)["id"], v1)
        self.assertEqual(self.jobs(), before)

    def test_newer_clip_running_is_refused(self):
        v1 = self.video(b"clip-1")
        self.p.reject(v1, "user", "gen lại", respawn=False)
        v2 = self.p.create_job(self.sid, "video_gen")
        self.p.start(v2)
        with self.assertRaises(InvalidTransition):
            self.p.use_older_take(v1, data_dir=self.data)
        self.assertEqual(self.p.state(v1).value, "rejected")
        self.assertIsNone(takes.chosen(self.p.conn, self.sid))

    def test_newer_approved_clip_is_rejected(self):
        v1 = self.video(b"clip-1")
        self.p.reject(v1, "user", "gen lại", respawn=False)
        v2 = self.video(b"clip-2")
        self.p.approve(v2)
        self.p.use_older_take(v1, data_dir=self.data)
        self.assertEqual([self.p.state(j).value for j in (v1, v2)], ["approved", "rejected"])
        self.assertEqual(_read(final_cut.clip_path(self.data, self.pid, 7)), b"clip-1")


if __name__ == "__main__":
    unittest.main()
