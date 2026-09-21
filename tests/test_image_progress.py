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
        self.assertIn("Chưa tạo ảnh nào", said)
        self.assertIn("PAUSE", said)
        self.assertIn("Resume", said)
        self.assertTrue(any("Chờ / đang gen" in o for o in at.radio(key=f"filter_{self.pid}").options))

    def test_without_deepix_it_says_nothing_is_generating_and_why(self):
        said, _ = self.text()
        self.assertIn("Deepix chưa được cấu hình", said)
        self.assertIn("Chưa tạo ảnh nào", said)

    def test_with_a_provider_but_no_submit_it_says_to_press_submit(self):
        os.environ["IMAGE_PROVIDER"] = "mock"
        said, _ = self.text()
        self.assertIn("chưa được gửi đi", said)
        self.assertIn("Submit + Poll", said)


if __name__ == "__main__":
    unittest.main()
