"""S14.19 Đợt 0 (KE_HOACH_BO_NAO_PROMPT_TU_HOC): the three new tables, core/feedback.py and the compare scores moved to user_feedback."""
import json
import os
import shutil
import sqlite3
import tempfile
import unittest

from core import compare, db, feedback
from core.db import connect
from core.pipeline import Pipeline

NEW_TABLES = ("lesson_reviews", "effectiveness_snapshots", "user_feedback")


def _tables(conn):
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "old.sqlite")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_an_old_database_gains_the_three_tables_and_keeps_its_rows(self):
        conn = connect(self.path)
        pid = Pipeline(conn).create_project("cũ")
        conn.close()
        raw = sqlite3.connect(self.path)                   # make it look like a database from before S14.19
        for t in NEW_TABLES:
            raw.execute(f"DROP TABLE IF EXISTS {t}")
        raw.execute("PRAGMA user_version = 0")
        raw.commit()
        raw.close()
        db._MIGRATED.clear()
        for _ in range(2):                                 # migrating twice is harmless
            conn = connect(self.path)
            self.assertTrue(set(NEW_TABLES) <= _tables(conn))
            self.assertEqual(conn.execute("SELECT name FROM projects WHERE id=?", (pid,)).fetchone()[0], "cũ")
            conn.close()

    def test_snapshot_unique_and_feedback_checks(self):
        conn = connect(":memory:")
        conn.execute("INSERT INTO effectiveness_snapshots (at, project_id, trigger) VALUES ('2026-10-05T10:00', NULL, 'manual')")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO user_feedback (at, kind) VALUES ('x', 'bogus')")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO user_feedback (at, kind, rating) VALUES ('x', 'screen', 9)")


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        self.p = Pipeline(self.conn)
        self.pid = self.p.create_project("fb")
        self.sid = self.p.create_scene(self.pid, 1, "S1")

    def test_three_kinds_are_recorded(self):
        a = feedback.add(self.conn, "delivery", project_id=self.pid, rating=5, text="dùng được", stage="render", created_by="a@x")
        b = feedback.add(self.conn, "scene", project_id=self.pid, scene_id=self.sid, rating=2, text="mặt lệch", stage="image")
        c = feedback.add(self.conn, "screen", screen="Bản giao", text="nút khó tìm", stage="ui")
        self.assertEqual(len({a, b, c}), 3)
        rows = feedback.list(self.conn)
        self.assertEqual({r["kind"] for r in rows}, {"delivery", "scene", "screen"})
        self.assertEqual(len(feedback.list(self.conn, project_id=self.pid)), 2)
        self.assertEqual([r["text"] for r in feedback.list(self.conn, kind="screen")], ["nút khó tìm"])

    def test_deleting_a_scene_or_the_project_keeps_the_remark_unlinked(self):
        sid2 = self.p.create_scene(self.pid, 2, "S2")
        feedback.add(self.conn, "scene", project_id=self.pid, scene_id=sid2, text="cảnh 2 tối")
        self.p.delete_scene(self.pid, 2)
        feedback.add(self.conn, "scene", project_id=self.pid, scene_id=self.sid, text="cảnh 1 lệch")
        self.conn.execute("INSERT INTO effectiveness_snapshots (at, project_id, trigger) VALUES ('2026-10-05T10:00', ?, 'manual')",
                          (self.pid,))
        self.p.delete_project(self.pid)
        rows = feedback.list(self.conn)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["scene_id"] is None and r["project_id"] is None for r in rows))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM effectiveness_snapshots").fetchone()[0], 0)

    def test_bad_input_is_refused_not_silently_dropped(self):
        with self.assertRaises(ValueError):
            feedback.add(self.conn, "bogus", text="x")
        with self.assertRaises(ValueError):
            feedback.add(self.conn, "screen", rating=7)
        with self.assertRaises(ValueError):
            feedback.add(self.conn, "screen")                     # nothing said at all
        with self.assertRaises(ValueError):
            feedback.add(self.conn, "screen", text="x", stage="nope")

    def test_satisfaction_and_summary(self):
        self.assertEqual(feedback.satisfaction(self.conn, self.pid), {"satisfaction": None, "n": 0})
        feedback.add(self.conn, "delivery", project_id=self.pid, rating=5)
        feedback.add(self.conn, "delivery", project_id=self.pid, rating=1, text="nhạc to", stage="audio")
        feedback.add(self.conn, "screen", screen="x", text="y", stage="ui")
        s = feedback.satisfaction(self.conn, self.pid)
        self.assertEqual(s["n"], 2)
        self.assertAlmostEqual(s["satisfaction"], 0.5)
        summ = feedback.summary(self.conn, days=30)
        self.assertEqual(summ["n"], 3)
        self.assertEqual(summ["by_stage"]["audio"]["n"], 1)
        self.assertEqual(feedback.summary(self.conn, stage="audio")["n"], 1)


class CompareScoresTests(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        self.pid = Pipeline(self.conn).create_project("cmp")

    def test_save_scores_writes_user_feedback(self):
        compare.save_scores(self.conn, self.pid, {"characters": 4, "overall": 5, "note": "ổn", "bogus": 9})
        rows = feedback.list(self.conn, project_id=self.pid)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "delivery")
        self.assertEqual(rows[0]["screen"], compare.FEEDBACK_SCREEN)
        self.assertEqual(rows[0]["rating"], 5)
        self.assertIsNone(self.conn.execute("SELECT 1 FROM app_settings WHERE key=?", (f"eval:{self.pid}",)).fetchone())
        self.assertEqual(compare.get_scores(self.conn, self.pid), {"characters": 4, "overall": 5, "note": "ổn"})

    def test_old_scores_in_app_settings_still_read(self):
        self.conn.execute("INSERT INTO app_settings (key, value) VALUES (?, ?)",
                          (f"eval:{self.pid}", json.dumps({"rhythm": 3, "note": "cũ"}, ensure_ascii=False)))
        self.assertEqual(compare.get_scores(self.conn, self.pid), {"rhythm": 3, "note": "cũ"})
        compare.save_scores(self.conn, self.pid, {"rhythm": 4})          # a new save wins over the old one
        self.assertEqual(compare.get_scores(self.conn, self.pid), {"rhythm": 4})


class FeedbackUiTests(unittest.TestCase):
    """AppTest, UI v2: the 💬 button of the top bar and the "Bản này dùng được chứ?" block of Bước 5."""

    def setUp(self):
        from unittest import mock
        from tests.test_ui_deliver import DeliverSeed
        self.seed = DeliverSeed("run")
        self.seed.setUp()
        self.addCleanup(self.seed.doCleanups)
        self.addCleanup(shutil.rmtree, self.seed.tmp, True)
        self.mock = mock

    def deliver(self):
        out = os.path.join(self.seed.data, str(self.seed.pid), "output")
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "FINAL_VIDEO.mp4"), "wb") as f:      # a delivered video (pre-v2 location, no lineage needed)
            f.write(b"not a real video")
        self.seed.with_clip()

    def rows(self):
        conn = connect(self.seed.db)
        try:
            return feedback.list(conn)
        finally:
            conn.close()

    def test_delivery_block_records_a_verdict_text_and_stage(self):
        self.deliver()
        at = self.seed.open_deliver()
        pid = self.seed.pid
        self.assertIn("Bản này dùng được chứ?", "\n".join(m.value for m in at.markdown))
        at.radio(key=f"fb_verdict_{pid}").set_value("👎")
        at.text_area(key=f"fb_text_{pid}").set_value("nhạc át giọng")
        at.selectbox(key=f"fb_stage_{pid}").set_value("audio")
        next(b for b in at.button if b.key == f"fb_send_{pid}").click().run()
        self.assertFalse(at.exception, at.exception)
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["kind"], rows[0]["project_id"], rows[0]["rating"], rows[0]["stage"], rows[0]["text"]),
                         ("delivery", pid, 1, "audio", "nhạc át giọng"))

    def test_delivery_block_waits_for_a_delivery_and_old_keys_stay(self):
        self.seed.with_clip()
        at = self.seed.open_deliver()
        self.assertNotIn(f"fb_send_{self.seed.pid}", {b.key for b in at.button})
        self.assertIn(f"deliver_{self.seed.pid}", {b.key for b in at.button})

    def test_empty_delivery_remark_says_so(self):
        self.deliver()
        at = self.seed.open_deliver()
        next(b for b in at.button if b.key == f"fb_send_{self.seed.pid}").click().run()
        self.assertEqual(self.rows(), [])
        self.assertTrue(any("trống" in w.value for w in at.warning))

    def test_screen_button_in_the_top_bar_records_a_screen_remark(self):
        at = self.seed.open_deliver()
        self.assertTrue(any("Góp ý màn này" in e.label for e in at.expander))
        at.text_area(key="fb_screen_text").set_value("màn này rối")
        next(b for b in at.button if b.key == "fb_screen_send").click().run()
        self.assertFalse(at.exception, at.exception)
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["kind"], rows[0]["stage"], rows[0]["text"], rows[0]["project_id"]),
                         ("screen", "ui", "màn này rối", self.seed.pid))
        self.assertTrue(rows[0]["screen"])


class ReviewFixTests(unittest.TestCase):
    """S14.19 rà soát: ↺ Làm lại keeps scene remarks, ⚖ re-save updates instead of adding."""

    def setUp(self):
        self.conn = connect(":memory:")
        self.p = Pipeline(self.conn)
        self.pid = self.p.create_project("rà")

    def test_reset_script_keeps_scene_remarks_unlinked(self):
        from dashboard.steps.step1 import reset_unworked_scenes
        sid = self.p.create_scene(self.pid, 1, "S1")
        feedback.add(self.conn, "scene", project_id=self.pid, scene_id=sid, text="cảnh tối")
        reset_unworked_scenes(self.p, self.pid)                      # FOREIGN KEY failed before the fix
        self.assertIsNone(self.conn.execute("SELECT 1 FROM scenes WHERE id=?", (sid,)).fetchone())
        rows = feedback.list(self.conn)
        self.assertEqual((len(rows), rows[0]["scene_id"], rows[0]["project_id"]), (1, None, self.pid))

    def test_compare_resave_updates_the_same_row(self):
        compare.save_scores(self.conn, self.pid, {"overall": 2})
        compare.save_scores(self.conn, self.pid, {"overall": 5, "note": "đã sửa"})
        rows = feedback.list(self.conn, project_id=self.pid)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["rating"], 5)
        self.assertEqual(feedback.satisfaction(self.conn, self.pid)["n"], 1)
        self.assertEqual(compare.get_scores(self.conn, self.pid), {"overall": 5, "note": "đã sửa"})
        other = self.p.create_project("khác")
        compare.save_scores(self.conn, other, {"overall": 3})
        self.assertEqual(len(feedback.list(self.conn)), 2)

if __name__ == "__main__":
    unittest.main()