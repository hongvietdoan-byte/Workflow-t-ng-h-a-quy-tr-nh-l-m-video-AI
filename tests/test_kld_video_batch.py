"""Việc để sau Khủng Long Đỏ (người dùng 07/10), phần cloud làm được (0 USD):
  2. nút '▶ Gen video' không tự gửi kèm cảnh 'đã cũ' — chỉ cảnh mới + cảnh cũ người dùng tích chọn (07/10 gửi nhầm scene 248, 249 ≈ 1,2 USD);
  3. tên model THẬT + độ phân giải hiện ở danh sách gửi (alias 'seedance' = Seedance 2.0, không phải 2.5 — gen nhầm 2 lần ≈ 3,6 USD);
  7. clip nối cảnh trước (start_from_prev_clip) nói rõ 'chờ duyệt clip cảnh trước' thay vì đứng im."""
import json
import unittest
from unittest import mock

from core import batch, llm_io, llm_runner
from core.adapters import clipai
from core.providers import MockVideoProvider
from core.runner import VideoRunner
from tests.test_v2 import Base


class ModelNameTests(unittest.TestCase):
    def test_aliases_show_the_real_model(self):
        self.assertEqual(clipai.display_name("seedance"), "Seedance 2.0")
        self.assertEqual(clipai.display_name("seedance-2.5", "1080p"), "Seedance 2.5 · 1080p")
        self.assertEqual(clipai.display_name("seedance-fast"), "Seedance 2.0 Fast")
        self.assertEqual(clipai.display_name("kling", "std"), "Kling 3.0 Omni · std")
        self.assertIn("lạ", clipai.display_name("không-có"))


class BatchTests(Base):
    def ready(self):
        self.approve_images()
        llm_runner.run_motion(self.p, self.pid, llm_runner.MockLlm(), self.data)
        for i in (1, 2, 3):
            llm_io.approve_motion_prompt(self.p, self.sid(i))

    def test_plan_lists_new_scenes_with_model_names(self):
        self.ready()
        plan = batch.video_plan(self.p, self.pid)
        self.assertEqual([r["kind"] for r in plan], ["new", "new", "new"])
        self.assertTrue(all(r["model_name"] and "·" in r["label"] for r in plan))
        self.assertTrue(all(not r["model_name"].startswith("seedance") for r in plan))     # never the bare alias

    def test_only_sends_the_chosen_scenes(self):
        self.ready()
        out = batch.queue_videos(self.p, self.pid, self.data, only={self.sid(2)})
        self.assertEqual(out["created"], 1)
        jobs = [r["scene_id"] for r in self.p.conn.execute("SELECT scene_id FROM jobs WHERE type='video_gen'")]
        self.assertEqual(jobs, [self.sid(2)])
        self.assertEqual(batch.queue_videos(self.p, self.pid, self.data)["created"], 2)   # no `only` = old behaviour (autopilot)

    def test_stale_clip_is_listed_but_not_sent_unless_chosen(self):
        self.ready()
        batch.queue_videos(self.p, self.pid, self.data)                                # every scene has its clip job already
        stale = [{"scene_id": self.sid(1), "job_id": 999, "why": "ảnh đổi"}]
        with mock.patch.object(batch, "_stale_redos", return_value=stale), \
                mock.patch.object(batch.regen, "regenerate_video") as redo:
            plan = batch.video_plan(self.p, self.pid)
            self.assertEqual([(r["scene_id"], r["kind"]) for r in plan], [(self.sid(1), "stale")])
            self.assertIn("đã cũ", plan[0]["label"])
            self.assertEqual(batch.queue_videos(self.p, self.pid, self.data, only=set())["redo"], 0)   # not ticked → not remade
            redo.assert_not_called()
            self.assertEqual(batch.queue_videos(self.p, self.pid, self.data, only={self.sid(1)})["redo"], 1)
            redo.assert_called_once()

    def test_chain_wait_names_the_previous_scene(self):
        self.ready()
        llm_io.update_scene(self.p, self.pid, 2, {"start_from_prev_clip": True})
        batch.queue_videos(self.p, self.pid, self.data)
        waits = batch.chain_waits(self.p, self.pid)
        self.assertIn(self.sid(2), waits)
        self.assertIn("chờ duyệt clip cảnh", waits[self.sid(2)])
        self.assertNotIn(self.sid(1), waits)


if __name__ == "__main__":
    unittest.main()
