"""#24 (08/10): gen lại shot 3 (một phần của clip nhóm S01–S03) đứng 'queued' mãi, không lý do: VideoRunner._wait chờ shot đầu nhóm
'có clip' mà `_has_clip` chỉ tính succeeded/approved — clip shot 1 đang chờ người duyệt (pending_review) nên không bao giờ đủ."""
from unittest import mock

from core import runner, shots
from core.providers import MockVideoProvider
from core.runner import VideoRunner
from tests.test_v2 import Base


class GroupPartRedoTests(Base):
    def setUp(self):
        super().setUp()
        self.vr = VideoRunner(self.p, MockVideoProvider(), self.data)
        self.group = [{"id": self.sid(1)}, {"id": self.sid(2)}, {"id": self.sid(3)}]

    def job(self, sid, state):
        jid = self.p.create_job(sid, "video_gen")
        self.p.conn.execute("UPDATE jobs SET state=? WHERE id=?", (state, jid))
        self.p.conn.commit()
        return self.p.job(jid)

    def wait(self, job):
        with mock.patch.object(shots, "group_of", return_value=self.group), \
                mock.patch.object(self.vr, "_refs", return_value=False), \
                mock.patch.object(self.vr, "_redo_run", return_value=None):
            return self.vr._wait(job)

    def test_leader_clip_waiting_for_review_counts_as_a_clip(self):
        self.job(self.sid(1), "pending_review")
        redo = self.job(self.sid(3), "queued")
        self.assertFalse(self.wait(redo))

    def test_no_leader_clip_holds_with_a_reason(self):
        redo = self.job(self.sid(3), "queued")
        self.assertTrue(self.wait(redo))
        self.assertIn("shot đầu nhóm", runner.WAIT_REASONS[redo["id"]][0])
