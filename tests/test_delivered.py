"""S14.30 (người dùng chốt 05/10): dự án "hoàn thiện" = đã XUẤT BẢN GIAO (bước Bản giao — `delivery.deliver` chạy xong), không phải lần
ghép bản cuối đầu tiên (`outputs` 'final' / FINAL_VIDEO.mp4). Tín hiệu riêng: bảng `deliveries` (core/delivered.py), ghi đúng lúc xuất
thành công, xuất lỗi không ghi; dự án cũ chuyển đổi bằng `delivered.backfill` (idempotent, báo số dự án đổi trạng thái)."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import delivered, delivery, inbox
from core.db import connect
from core.pipeline import Pipeline


def fake_render(p, pid, data_dir, music_path):
    out = os.path.join(data_dir, str(pid), "output", "FINAL_VIDEO.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "wb") as f:
        f.write(b"FINAL")
    return out


QC_OK = {"ok": True, "blocks": 0, "warns": 0, "issues": []}


class DeliverWritesTheSignal(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("giao", "human_qc", 0.85, 2)
        self.patches = [mock.patch.object(delivery, n, return_value=None) for n in ("end_card_layer", "ai_label_layer")]
        self.patches.append(mock.patch("core.final_qc.run", return_value=QC_OK))
        for pt in self.patches:
            pt.start()
        self.addCleanup(lambda: [pt.stop() for pt in self.patches])

    def deliver(self, render_fn=fake_render):
        return delivery.deliver(self.p, self.pid, self.data, render_fn=render_fn, subtitle_fn=lambda *a: None)

    def test_a_rough_render_alone_is_not_delivered(self):
        delivery.record(self.p, self.pid, "final", fake_render(self.p, self.pid, self.data, None))
        self.assertFalse(delivered.is_delivered(self.p.conn, self.pid))
        self.assertTrue(delivered.rendered_not_delivered(self.p.conn, self.pid, self.data))

    def test_a_successful_delivery_is_recorded_with_path_time_and_person(self):
        self.p.actor = "nv@garena.vn"
        self.deliver()
        self.assertTrue(delivered.is_delivered(self.p.conn, self.pid))
        row = delivered.latest(self.p.conn, self.pid)
        self.assertTrue(row["path"].endswith("FINAL_VIDEO.mp4"))
        self.assertEqual(row["delivered_by"], "nv@garena.vn")
        self.assertEqual(row["source"], "deliver")
        self.assertTrue(row["delivered_at"])
        self.assertFalse(delivered.rendered_not_delivered(self.p.conn, self.pid, self.data))

    def test_a_failed_render_records_nothing(self):
        def broken(*a):
            raise RuntimeError("ffmpeg hỏng")
        with self.assertRaises(RuntimeError):
            self.deliver(broken)
        self.assertFalse(delivered.is_delivered(self.p.conn, self.pid))

    def test_a_failed_export_size_records_nothing(self):
        delivery.save_settings(self.p, self.pid, {**delivery.get_settings(self.p, self.pid), "exports": [{"w": 1080, "h": 1920}]})
        with mock.patch.object(delivery, "export_layer", side_effect=RuntimeError("hết đĩa")):
            res = self.deliver()
        self.assertTrue(any("xuất 1080x1920" in w for w in res["warnings"]))
        self.assertFalse(delivered.is_delivered(self.p.conn, self.pid))
        self.assertTrue(any("chưa tính là xong" in w for w in res["warnings"]))

    def test_inbox_says_deliver_to_count_as_done(self):
        delivery.record(self.p, self.pid, "final", fake_render(self.p, self.pid, self.data, None))
        with mock.patch.dict(os.environ, {"PIPELINE_DATA": self.data}):
            rows = [i for i in inbox.items(self.p.conn, "", True, False, False) if i["kind"] == "Bản giao"]
        self.assertEqual(len(rows), 1)
        self.assertIn("xuất bản giao để tính là xong", rows[0]["text"])
        self.assertEqual(rows[0]["screen"], "deliver")
        self.deliver()
        with mock.patch.dict(os.environ, {"PIPELINE_DATA": self.data}):
            self.assertFalse([i for i in inbox.items(self.p.conn, "", True, False, False) if i["kind"] == "Bản giao"])


class Backfill(unittest.TestCase):
    """Dự án cũ: đã có bản giao thật → ghi tín hiệu; chỉ có FINAL_VIDEO → KHÔNG còn tính xong (báo số dự án đổi trạng thái)."""

    def setUp(self):
        self.data, self.root = tempfile.mkdtemp(), tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.ids = [self.p.create_project(f"P{i}", "human_qc", 0.85, 2) for i in range(5)]
        a, b, c, d, e = self.ids
        os.makedirs(os.path.join(self.root, f"2026-09-28_du-an-{a}"))                       # a: bản giao ở thư mục giao
        open(os.path.join(self.root, f"2026-09-28_du-an-{a}", "FINAL.mp4"), "wb").close()
        fake_render(self.p, a, self.data, None)
        delivery.record(self.p, b, "final", fake_render(self.p, b, self.data, None),          # b: deliver() chạy xong (final_qc ghi cuối)
                        manifest={"final_qc": {"blocks": 0, "warns": 0, "issues": []}})
        self.p.conn.execute("UPDATE projects SET autopilot_state='done' WHERE id=?", (c,))    # c: chạy tự động xong bước Bản giao
        fake_render(self.p, c, self.data, None)
        delivery.record(self.p, d, "final", fake_render(self.p, d, self.data, None))          # d: chỉ bản ghép (Dựng thử)
        fake_render(self.p, e, self.data, None)                                               # e: chỉ FINAL_VIDEO kiểu cũ
        os.makedirs(os.path.join(self.root, f"2026-09-30_du-an-{e}"))                         # thư mục giao rỗng: không tính
        self.p.conn.commit()

    def test_backfill_marks_the_delivered_ones_and_reports_the_rest(self):
        a, b, c, d, e = self.ids
        dry = delivered.backfill(self.p.conn, self.data, self.root, apply=False)
        self.assertEqual(sorted(x["project_id"] for x in dry["marked"]), [a, b, c])
        self.assertEqual(sorted(dry["rendered_only"]), [d, e])
        self.assertFalse(delivered.is_delivered(self.p.conn, a))                              # chạy thử không ghi
        res = delivered.backfill(self.p.conn, self.data, self.root, apply=True)
        self.assertEqual({x["project_id"]: x["source"] for x in res["marked"]},
                         {a: "backfill_folder", b: "backfill_deliver", c: "backfill_autopilot_done"})
        self.assertTrue(all(delivered.is_delivered(self.p.conn, i) for i in (a, b, c)))
        self.assertFalse(any(delivered.is_delivered(self.p.conn, i) for i in (d, e)))
        self.assertIn("2 dự án", res["summary"])                                              # không im lặng: số dự án KHÔNG còn tính xong
        diag = self.p.conn.execute("SELECT message FROM diag_events WHERE code='delivered_backfill'").fetchall()
        self.assertEqual(len(diag), 1)
        again = delivered.backfill(self.p.conn, self.data, self.root, apply=True)              # idempotent
        self.assertEqual(again["marked"], [])
        self.assertEqual(sorted(again["already"]), [a, b, c])
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM deliveries").fetchone()[0], 3)

    def test_backfill_tool_dry_run_by_default(self):
        from tools import backfill_delivered
        db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        conn = connect(db)
        p = Pipeline(conn)
        pid = p.create_project("x", "human_qc", 0.85, 2)
        os.makedirs(os.path.join(self.root, f"2026-10-01_du-an-{pid}"), exist_ok=True)
        open(os.path.join(self.root, f"2026-10-01_du-an-{pid}", "v.mp4"), "wb").close()
        conn.close()
        out = backfill_delivered.main(["--db", db, "--data", self.data, "--output-root", self.root])
        self.assertEqual(json.loads(out)["apply"], False)
        conn = connect(db)
        self.assertFalse(delivered.is_delivered(conn, pid))
        conn.close()
        backfill_delivered.main(["--db", db, "--data", self.data, "--output-root", self.root, "--apply"])
        conn = connect(db)
        self.assertTrue(delivered.is_delivered(conn, pid))
        conn.close()


if __name__ == "__main__":
    unittest.main()
