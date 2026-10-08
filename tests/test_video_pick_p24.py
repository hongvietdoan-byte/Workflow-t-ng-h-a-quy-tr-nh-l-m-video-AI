"""#24 (08/10): màn Video không cho gen thử vài cảnh mới (nút gửi mọi cảnh mới) và dòng 'Sẽ gửi' ghi 720p trong khi lần đầu của shot
nháp-trước (cờ two_tier_quality) đi ở bậc thấp 480p. Nay: danh sách ghi '(nháp)' + độ phân giải bậc thấp; giá theo đúng các cảnh đã chọn."""
from unittest import mock

from core import batch, cost, llm_io, llm_runner, quality_tier
from tests.test_v2 import Base


class VideoPickTests(Base):
    def ready(self):
        self.approve_images()
        llm_runner.run_motion(self.p, self.pid, llm_runner.MockLlm(), self.data)
        for i in (1, 2, 3):
            llm_io.approve_motion_prompt(self.p, self.sid(i))

    def test_draft_first_shot_is_listed_at_the_low_tier(self):
        self.ready()
        with mock.patch.object(quality_tier, "enabled", return_value=True), \
                mock.patch.object(quality_tier, "path", return_value="draft_first"):
            plan = batch.video_plan(self.p, self.pid)
        self.assertTrue(plan and all("(nháp)" in r["model_name"] for r in plan), [r["label"] for r in plan])

    def test_flag_off_keeps_the_plan_resolution(self):
        self.ready()
        with mock.patch.object(quality_tier, "enabled", return_value=False):
            plan = batch.video_plan(self.p, self.pid)
        self.assertTrue(all("(nháp)" not in r["model_name"] for r in plan))

    def test_direct_shot_is_not_a_draft(self):
        self.ready()
        with mock.patch.object(quality_tier, "enabled", return_value=True), \
                mock.patch.object(quality_tier, "path", return_value="direct"):
            plan = batch.video_plan(self.p, self.pid)
        self.assertTrue(all("(nháp)" not in r["model_name"] for r in plan))

    def test_price_follows_the_picked_scenes(self):
        self.ready()
        rows = [r for r in batch.video_plan(self.p, self.pid)][:2]
        with mock.patch.object(cost, "clip_estimate", return_value=0.6):
            tag = batch.picked_tag(self.p, rows)
        self.assertIn("2 clip ≈ 1.20 USD", tag)
        self.assertEqual(batch.picked_tag(self.p, []), "")
        with mock.patch.object(cost, "clip_estimate", return_value=None):
            self.assertIn("chưa có giá", batch.picked_tag(self.p, rows))


class ClipGroupPickTests(Base):
    def ready(self):
        self.approve_images()
        llm_runner.run_motion(self.p, self.pid, llm_runner.MockLlm(), self.data)
        for i in (1, 2, 3):
            llm_io.approve_motion_prompt(self.p, self.sid(i))

    def test_label_names_the_group_and_a_pick_brings_its_group(self):
        """#24: shot 7 picked alone queued a job that waited forever — its group clip (S06–S07) goes from S06, not picked."""
        self.ready()
        from core import shots
        group = [{"id": self.sid(2)}, {"id": self.sid(3)}]
        with mock.patch.object(shots, "group_of", side_effect=lambda conn, sid: group if sid in (self.sid(2), self.sid(3)) else None):
            plan = batch.video_plan(self.p, self.pid)
            labels = {r["scene_id"]: r["label"] for r in plan}
            self.assertIn("clip nhóm S02–S03", labels[self.sid(3)])
            self.assertNotIn("clip nhóm", labels[self.sid(1)])
            self.assertEqual(batch.with_groups(self.p.conn, plan, [self.sid(3)]), [self.sid(2), self.sid(3)])
            self.assertEqual(batch.with_groups(self.p.conn, plan, [self.sid(1)]), [self.sid(1)])
