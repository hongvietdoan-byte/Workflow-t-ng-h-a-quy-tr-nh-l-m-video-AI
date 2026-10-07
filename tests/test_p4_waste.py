"""TODO Tồn đọng P4 (Data Pack 29/09): 'tiền lãng phí' — tiền đã chi cho ảnh / clip không dùng tới (bị loại, bị bản mới hơn thay, lỗi /
hủy sau khi gửi), chia theo loại + lý do, cạnh 'Chi phí / giây' ở khối Hiệu quả workflow. Job đang chạy chưa tính; job không có giá nói ra."""
import unittest

from core import effectiveness
from core.db import connect

PRICING = {"currency": "usd", "per_image": {"img": 0.05}, "per_video_second": {"vid:std": 0.1}, "per_video_clip": {}, "per_audio": {},
           "per_million_tokens": {}}


class WasteTests(unittest.TestCase):
    def setUp(self):
        self.conn = connect()
        self.conn.execute("INSERT INTO projects (id, name, created_at) VALUES (1, 'p', '2026-10-07T00:00:00Z')")
        for sid in (1, 2):
            self.conn.execute("INSERT INTO scenes (id, project_id, idx, data, state) VALUES (?, 1, ?, '{}', 'ready')", (sid, sid))
        self.conn.commit()

    def job(self, jid, sid, typ, state, model, tier, qty, kind):
        self.conn.execute("INSERT INTO jobs (id, scene_id, project_id, type, state, created_at, updated_at) VALUES (?,?,1,?,?,"
                          "'2026-10-07T00:00:00Z','2026-10-07T00:00:00Z')", (jid, sid, typ, state))
        if model:
            self.conn.execute("INSERT INTO usage_events (job_id, project_id, kind, provider, model, tier, quantity, unit, at)"
                              " VALUES (?,1,?,'x',?,?,?,'u','2026-10-07T00:00:00Z')", (jid, kind, model, tier, qty))
        self.conn.commit()

    def test_rejected_superseded_failed_are_waste_approved_and_running_are_not(self):
        self.job(1, 1, "image_gen", "rejected", "img", "std", 1, "image")          # bị loại: 0,05
        self.job(2, 1, "image_gen", "approved", "img", "std", 1, "image")          # dùng
        self.job(3, 2, "video_gen", "succeeded", "vid", "std", 5, "video")         # bị bản 4 thay: 0,5
        self.job(4, 2, "video_gen", "approved", "vid", "std", 5, "video")          # dùng
        self.job(5, 2, "video_gen", "failed", "vid", "std", 5, "video")            # lỗi sau khi gửi: 0,5
        self.job(6, 1, "image_gen", "running", "img", "std", 1, "image")          # chưa xong: chưa tính
        w = effectiveness.waste(self.conn, 1, PRICING)
        self.assertAlmostEqual(w["wasted"], 1.05)
        self.assertAlmostEqual(w["spent"], 1.65)
        self.assertAlmostEqual(w["share"], 1.05 / 1.65)
        self.assertAlmostEqual(w["by_reason"]["bị loại"], 0.05)
        self.assertAlmostEqual(w["by_reason"]["bị thay"], 0.5)
        self.assertAlmostEqual(w["by_reason"]["lỗi / hủy"], 0.5)
        self.assertAlmostEqual(w["by_kind"]["video"]["wasted"], 1.0)
        self.assertEqual(w["unpriced"], 0)

    def test_unpriced_rows_are_counted_not_valued(self):
        self.job(1, 1, "image_gen", "rejected", "lạ", "std", 1, "image")
        w = effectiveness.waste(self.conn, 1, PRICING)
        self.assertEqual((w["wasted"], w["unpriced"]), (0.0, 1))

    def test_report_and_summary_carry_it(self):
        self.job(1, 1, "image_gen", "rejected", "img", "std", 1, "image")
        r = effectiveness.report(self.conn, 1, PRICING)
        self.assertAlmostEqual(r["waste"]["wasted"], 0.05)
        self.assertTrue(any("lãng phí" in line for line in effectiveness.summary_lines(r)))


if __name__ == "__main__":
    unittest.main()
