"""#24 (08/10): clip nhóm S04–S05 bị đánh lỗi ngay 'Shot 1 thiếu render địa điểm 3D; tạo lại render trước khi gửi video' — người dùng
không có nút nào để 'tạo lại render'. Nay clip chờ, nền được dựng / đo lại MỘT lần ở nền (0 USD), xong tự gửi; vẫn thiếu thì bước kiểm
gửi báo lý do như cũ."""
from unittest import mock

from core import place_refs, runner, seedance_refs
from core.providers import MockVideoProvider
from core.runner import VideoRunner
from tests.test_v2 import Base


class RenderGapTests(Base):
    def setUp(self):
        super().setUp()
        runner._RENDER_RETRIED.clear()
        self.vr = VideoRunner(self.p, MockVideoProvider(), self.data)
        self.job = {"id": 1, "project_id": self.pid, "scene_id": self.sid(1)}
        self.rows = [{"id": self.sid(1), "data": {}}, {"id": self.sid(2), "data": {}}]

    def patches(self, rendered_shots, running=False):
        thread = mock.Mock(is_alive=mock.Mock(return_value=running)) if running else None
        return [mock.patch.object(self.vr, "_ref_rows", return_value=self.rows),
                mock.patch.object(self.vr, "_sends_group", return_value=self.rows),
                mock.patch.object(seedance_refs, "place_pictures",
                                  return_value=[{"path": "x.png", "shots": rendered_shots}] if rendered_shots else []),
                mock.patch.object(place_refs, "wants_render", return_value=True),
                mock.patch.dict(place_refs._RUNNING, {self.pid: thread} if thread else {}, clear=True),
                mock.patch.object(place_refs, "ensure_async", return_value=True)]

    def run_gap(self, rendered_shots, running=False):
        ps = self.patches(rendered_shots, running)
        for p in ps:
            p.start()
        try:
            return self.vr._render_gap(self.job), place_refs.ensure_async
        finally:
            for p in reversed(ps):
                p.stop()

    def test_missing_render_is_made_again_once_then_the_check_decides(self):
        reason, ensure = self.run_gap([2])
        self.assertIn("shot 1", reason)
        self.assertIn("sẽ tự gửi", reason)
        ensure.assert_called_once()
        reason2, ensure2 = self.run_gap([2])                     # second round: not again (the send check says why)
        self.assertIsNone(reason2)
        ensure2.assert_not_called()

    def test_waits_while_the_render_is_running(self):
        reason, ensure = self.run_gap([2], running=True)
        self.assertIn("đang dựng nền 3D", reason)
        ensure.assert_not_called()

    def test_every_shot_rendered_no_wait(self):
        reason, ensure = self.run_gap([1, 2])
        self.assertIsNone(reason)
        ensure.assert_not_called()
