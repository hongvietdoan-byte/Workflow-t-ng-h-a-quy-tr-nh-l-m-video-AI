"""Người dùng 08/10 (ảnh màn Tất cả dự án): #22 Khủng Long Đỏ đã có video cuối, 9/9 clip đã DUYỆT nhưng thẻ hiện 67 % và 'Chờ bạn'
không rõ chờ gì — (1) đếm clip chỉ theo 'succeeded', bỏ sót 'approved'; (2) video cuối xong mà chưa xuất bản giao → nói rõ."""
import unittest

from core import perf
from core.db import connect
from core.pipeline import Pipeline
from dashboard import home


class HomeCardTests(unittest.TestCase):
    def test_approved_clips_count_as_finished(self):
        p = Pipeline(connect(":memory:"))
        pid = p.create_project("t")
        for i in (1, 2):
            sid = p.create_scene(pid, i, "s")
            j = p.create_job(sid, "video_gen")
            p.conn.execute("UPDATE jobs SET state=? WHERE id=?", ("approved" if i == 1 else "succeeded", j))
        p.conn.commit()
        self.assertEqual(perf._progress(p.conn, pid)[3], 2)

    def test_a_finished_cut_not_yet_delivered_says_what_it_waits_for(self):
        r = {"status": "wait", "done": True, "delivered": False}
        self.assertEqual(home.pill_of(r)[0], "Chờ xuất bản giao")
        self.assertEqual(home.pill_of({"status": "wait", "done": False, "delivered": False})[0], "Chờ bạn")


if __name__ == "__main__":
    unittest.main()
