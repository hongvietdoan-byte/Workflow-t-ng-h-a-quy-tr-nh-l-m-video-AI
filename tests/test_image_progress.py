import os
import unittest

from streamlit.testing.v1 import AppTest

from tests.test_step1_flow import APP, split_only


class ImageProgressTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.db, self.data, self.p, self.pid = split_only()
        for r in self.p.conn.execute("SELECT id FROM scenes WHERE project_id=?", (self.pid,)).fetchall():
            self.p.create_job(r["id"], "image_gen")
        os.environ.update({"PIPELINE_DB": self.db, "PIPELINE_DATA": self.data, "IMAGE_PROVIDER": ""})
        os.environ.pop("DEEPIX_TOKEN", None)
        # S14.14 G-a: ui_v2 is ON by default now; these tests describe the classic Storyboard screen (nhóm nặng, G-b converts them)
        from unittest import mock
        flag = mock.patch.dict(os.environ, {"FEATURE_UI_V2": "0"})
        flag.start()
        self.addCleanup(flag.stop)

    def tearDown(self):
        for k in ("PIPELINE_DB", "PIPELINE_DATA", "IMAGE_PROVIDER"):
            os.environ.pop(k, None)

    def text(self):
        at = AppTest.from_file(APP, default_timeout=40)
        at.query_params["step"] = "2"
        at.run()
        self.assertFalse(at.exception)
        return " ".join(m.value for m in list(at.warning) + list(at.info) + list(at.success)), at

    def test_a_paused_project_says_so_and_what_to_press(self):
        self.p.set_paused(self.pid, True)
        said, at = self.text()
        self.assertIn("tạm dừng", said)
        self.assertIn("chưa gửi", said)
        self.assertIn("Tiếp tục", said)
        self.assertTrue(any("Chờ / đang gen" in o for o in at.radio(key=f"filter_{self.pid}").options))

    def test_without_deepix_it_says_nothing_is_generating_and_why(self):
        said, _ = self.text()
        self.assertIn("Deepix chưa được cấu hình", said)
        self.assertIn("ảnh đang chờ", said)

    def test_with_a_provider_but_no_submit_it_says_to_press_submit(self):
        os.environ["IMAGE_PROVIDER"] = "mock"
        said, _ = self.text()
        self.assertIn("chưa gửi", said)
        self.assertIn("Gen ảnh", said)


class AutoRefreshTests(ImageProgressTests):
    def test_finished_images_are_collected_and_shown_without_pressing_anything(self):
        from unittest import mock
        from core.adapters import factory
        from core.providers import MockImageProvider
        from core.runner import ImageRunner
        from core.throttle import THROTTLE
        THROTTLE.reset()                                                         # a limit learned by another test must not leak in
        provider = MockImageProvider(polls_to_finish=1)
        self.p.conn.execute("UPDATE scenes SET data='{\"image_prompt\": \"a hero\"}' WHERE project_id=?", (self.pid,))
        self.p.conn.commit()
        ImageRunner(self.p, provider, self.data).submit_pending(self.pid)       # what "Submit" does; nothing pressed after that
        states = lambda: {r["state"] for r in self.p.conn.execute("SELECT state FROM jobs WHERE project_id=?", (self.pid,))}
        self.assertEqual(states(), {"running", "queued"})                        # 4 submitted (the limit), the rest waits for a slot
        with mock.patch.object(factory, "image_provider", return_value=provider):
            at = AppTest.from_file(APP, default_timeout=60)
            at.query_params["step"] = "2"
            at.run()
        self.assertFalse(at.exception)
        self.assertTrue(states() <= {"succeeded", "pending_review", "approved"})   # the page collected the first 4, sent the other 2 as slots freed, collected those

    def test_nothing_running_means_no_polling_and_the_text_says_it_updates_by_itself_otherwise(self):
        said, _ = self.text()
        self.assertNotIn("Tự cập nhật", said)


class StatusTableTests(ImageProgressTests):
    def test_the_per_scene_status_table_lists_every_scene_with_its_state(self):
        _, at = self.text()
        table = next(d for d in at.dataframe if list(d.value.columns) == ["Cảnh", "Trạng thái", "Điểm QC", "Đã gen lại"])
        rows = table.value.to_dict("records")
        self.assertGreater(len(rows), 0)
        self.assertTrue(all(r["Trạng thái"] for r in rows))
        self.assertTrue(all(r["Điểm QC"] == "—" for r in rows))                # nothing scored yet


if __name__ == "__main__":
    unittest.main()
