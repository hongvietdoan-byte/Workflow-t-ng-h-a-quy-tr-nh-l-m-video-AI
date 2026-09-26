"""core.memo: per-rerun memo for the dashboard, JSON files cached by mtime, db.connect migrating once per schema version."""
import json
import os
import sqlite3
import tempfile
import time
import unittest
from unittest import mock

from core import assets, cost, db, lineage, memo, model_router
from core.db import connect
from core.llm_io import store_scene_analysis
from core.pipeline import Pipeline
from tests.test_llm_io_preflight import ANALYSIS


def _old(path: str, seconds: float = 60) -> None:
    """Move a file's time into the past so the 'written just now' re-read rule does not apply."""
    t = time.time() - seconds
    os.utime(path, (t, t))


class PerRerunMemoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "m.sqlite")
        self.p = Pipeline(connect(self.path))
        self.pid = self.p.create_project("Memo")
        self.p.create_scene(self.pid, 1, "CẢNH 1")
        store_scene_analysis(self.p, self.pid, ANALYSIS)

    def test_outside_a_rerun_nothing_is_cached(self):
        with mock.patch.object(lineage, "_scan", wraps=lineage._scan) as spy:
            lineage.scan(self.p.conn, self.pid)
            lineage.scan(self.p.conn, self.pid)
        self.assertEqual(spy.call_count, 2)

    def test_inside_a_rerun_the_scan_runs_once_until_the_database_changes(self):
        with mock.patch.object(lineage, "_scan", wraps=lineage._scan) as spy, memo.per_rerun():
            first = lineage.scan(self.p.conn, self.pid)
            lineage.scan(self.p.conn, self.pid)
            lineage.summary(self.p.conn, self.pid)
            self.assertEqual(spy.call_count, 1)
            self.p.conn.execute("UPDATE scenes SET data=data WHERE project_id=?", (self.pid,))     # a write on this connection
            lineage.scan(self.p.conn, self.pid)
            self.assertEqual(spy.call_count, 2)
            other = sqlite3.connect(self.path)                                                    # a write by another process
            self.p.conn.commit()
            other.execute("UPDATE projects SET name='Memo 2' WHERE id=?", (self.pid,))
            other.commit()
            other.close()
            lineage.scan(self.p.conn, self.pid)
            self.assertEqual(spy.call_count, 3)
        self.assertFalse(memo.active())
        self.assertTrue(first)

    def test_callers_get_copies(self):
        with memo.per_rerun():
            a = lineage.scan(self.p.conn, self.pid)
            sid = next(iter(a))
            a[sid]["image_stale"] = "sửa bậy"
            b = lineage.scan(self.p.conn, self.pid)
        self.assertIsNone(b[sid]["image_stale"])

    def test_project_assets_memo(self):
        os.environ["ASSET_DIR"] = os.path.join(self.tmp, "assets")
        self.addCleanup(os.environ.pop, "ASSET_DIR", None)
        aid = assets.create(self.p.conn, "FF", "character", "KELLY")
        assets.attach(self.p.conn, self.pid, aid)
        with mock.patch.object(assets, "_project_assets", wraps=assets._project_assets) as spy, memo.per_rerun():
            self.assertEqual([a["name"] for a in assets.project_assets(self.p.conn, self.pid)], ["KELLY"])
            assets.project_assets(self.p.conn, self.pid)
            self.assertEqual(spy.call_count, 1)
            aid2 = assets.create(self.p.conn, "FF", "location", "Tháp")
            assets.attach(self.p.conn, self.pid, aid2)                      # attaching changes the answer at once
            self.assertEqual(len(assets.project_assets(self.p.conn, self.pid)), 2)

    def test_dashboard_step_bar_scans_once_per_click(self):
        """app.py wraps main() in per_rerun: the step bar (summary + final status) and the step share one scan."""
        from streamlit.testing.v1 import AppTest
        os.environ.update({"PIPELINE_DB": self.path, "PIPELINE_DATA": os.path.join(self.tmp, "projects"),
                           "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "ku")})
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in ("PIPELINE_DB", "PIPELINE_DATA", "KNOWLEDGE_USER_DIR")])
        app = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
        at = AppTest.from_file(app, default_timeout=60).run()
        from dashboard.common import STEPS
        at.session_state["step"] = STEPS[1]
        at.run()
        with mock.patch.object(lineage, "_scan", wraps=lineage._scan) as spy:
            at.run()
        self.assertFalse(at.exception)
        self.assertEqual(spy.call_count, 1)


class JsonCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "p.json")

    def write(self, data, old=True):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(data if isinstance(data, str) else json.dumps(data))
        if old:
            _old(self.path)

    def test_parsed_once_while_the_file_is_unchanged(self):
        self.write({"a": 1})
        with mock.patch("json.load", wraps=json.load) as spy:
            self.assertEqual(memo.read_json(self.path), {"a": 1})
            got = memo.read_json(self.path)
            got["a"] = 99                                   # a caller changing its copy does not change the cache
            self.assertEqual(memo.read_json(self.path), {"a": 1})
        self.assertEqual(spy.call_count, 1)

    def test_a_changed_file_is_picked_up(self):
        self.write({"a": 1})
        memo.read_json(self.path)
        self.write({"a": 2})
        t = time.time() - 30                                # a different, still old, file time
        os.utime(self.path, (t, t))
        self.assertEqual(memo.read_json(self.path), {"a": 2})

    def test_a_file_written_just_now_is_always_read_again(self):
        self.write({"a": 1}, old=False)
        memo.read_json(self.path)
        self.write({"a": 3}, old=False)                     # same size, maybe the same coarse file time
        self.assertEqual(memo.read_json(self.path), {"a": 3})

    def test_a_broken_file_raises_and_is_never_cached(self):
        self.write({"a": 1})
        memo.read_json(self.path)
        self.write("{broken")
        t = time.time() - 20
        os.utime(self.path, (t, t))
        with self.assertRaises(ValueError):
            memo.read_json(self.path)
        with self.assertRaises(ValueError):
            memo.read_json(self.path)
        self.write({"a": 4})
        self.assertEqual(memo.read_json(self.path), {"a": 4})

    def test_load_pricing_uses_the_cache_and_sees_saved_prices(self):
        self.write({"currency": "USD", "per_image": {"x": 1}})
        first = cost.load_pricing(self.path)
        first["per_image"]["x"] = 7                         # the price editor changes its copy…
        self.assertEqual(cost.load_pricing(self.path)["per_image"]["x"], 1)
        cost.save_pricing(first, self.path)                 # …and saving it is seen at once
        self.assertEqual(cost.load_pricing(self.path)["per_image"]["x"], 7)

    def test_load_profiles_missing_file_is_not_cached(self):
        self.assertEqual(model_router.load_profiles(self.path)["models"], {})
        self.write({"models": {"kling": {"api": True}}})
        self.assertIn("kling", model_router.load_profiles(self.path)["models"])


class ConnectMigratesOnceTests(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "m.sqlite")

    def test_second_connect_skips_the_migration(self):
        connect(self.path).close()
        with mock.patch.object(db, "_migrate", wraps=db._migrate) as spy:
            c = connect(self.path)
        self.assertEqual(spy.call_count, 0)
        self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], db.schema_stamp())
        self.assertIn("archived", {r["name"] for r in c.execute("PRAGMA table_info(projects)")})

    def test_an_older_database_is_migrated(self):
        """A database stamped by older code (or never stamped) gets the missing columns once."""
        raw = sqlite3.connect(self.path)
        raw.execute("CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL)")
        raw.execute("PRAGMA user_version = 12345")
        raw.commit()
        raw.close()
        c = connect(self.path)
        cols = {r["name"] for r in c.execute("PRAGMA table_info(projects)")}
        self.assertTrue({"archived", "paused", "look"} <= cols)
        self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], db.schema_stamp())

    def test_memory_database_is_always_fresh(self):
        c = connect()
        self.assertIsNotNone(c.execute("SELECT COUNT(*) FROM projects").fetchone())


class ShapeCacheTests(unittest.TestCase):
    def test_replaced_picture_is_read_again(self):
        from PIL import Image
        path = os.path.join(tempfile.mkdtemp(), "a.png")
        Image.new("RGB", (40, 20)).save(path)
        self.assertEqual(assets._shape(path), (40, 20))
        Image.new("RGB", (1600, 900)).save(path)
        t = time.time() + 5
        os.utime(path, (t, t))
        self.assertEqual(assets._shape(path), (1600, 900))
        self.assertIsNone(assets._shape(path + ".missing"))


if __name__ == "__main__":
    unittest.main()
