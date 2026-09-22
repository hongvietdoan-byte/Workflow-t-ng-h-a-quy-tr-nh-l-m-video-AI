import os
import unittest

from streamlit.testing.v1 import AppTest

from core.providers import MockImageProvider
from core.runner import ImageRunner
from core.throttle import THROTTLE
from tests.test_step1_flow import APP, split_only


class ImageHistoryTests(unittest.TestCase):
    """A scene that was retried several times must still be ONE card in the grid, with old/new attempts reachable through ‹ › —
    not one grid card per attempt (that made a large project impossible to scan)."""

    def setUp(self):
        THROTTLE.reset()
        self.tmp, self.db, self.data, self.p, self.pid = split_only()
        self.scenes = self.p.conn.execute("SELECT id, idx FROM scenes WHERE project_id=?", (self.pid,)).fetchall()
        self.provider = MockImageProvider(polls_to_finish=1, transient_failures=0)
        self.runner = ImageRunner(self.p, self.provider, self.data)
        for r in self.scenes:
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", ('{"image_prompt": "a hero"}', r["id"]))
        self.p.conn.commit()
        os.environ.update({"PIPELINE_DB": self.db, "PIPELINE_DATA": self.data})

    def tearDown(self):
        os.environ.pop("PIPELINE_DB", None)
        os.environ.pop("PIPELINE_DATA", None)

    def generate(self, scene_id):
        """Create and run through to 'succeeded' the first queued job of this scene."""
        self.p.create_job(scene_id, "image_gen")
        self.runner.submit_pending(self.pid)
        self.runner.poll_once(self.pid)
        return self.p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='succeeded'"
                                   " ORDER BY id DESC LIMIT 1", (scene_id,)).fetchone()["id"]

    def reject_and_regenerate(self, jid, scene_id, reason):
        """What "✖ Reject" does: `Pipeline.reject` already spawns the next attempt (queued) on its own."""
        self.p.reject(jid, "user", reason)
        self.runner.submit_pending(self.pid)
        self.runner.poll_once(self.pid)
        return self.p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='succeeded'"
                                   " ORDER BY id DESC LIMIT 1", (scene_id,)).fetchone()["id"]

    def app(self):
        at = AppTest.from_file(APP, default_timeout=60)
        at.query_params["step"] = "2"
        at.run()
        self.assertFalse(at.exception)
        return at

    def test_two_retries_of_one_scene_still_render_as_a_single_card(self):
        sid1 = self.scenes[0]["id"]
        jid = self.generate(sid1)
        for _ in range(2):                                                             # split_only's project allows 2 retries
            jid = self.reject_and_regenerate(jid, sid1, "không đúng nhân vật")         # 3 attempts total for this one scene
        for r in self.scenes[1:]:
            self.generate(r["id"])                                                     # every other scene: one plain attempt
        at = self.app()
        idx1 = self.scenes[0]["idx"]
        headers = [m.value for m in at.markdown if f"<b>Cảnh {idx1}</b>" in (m.value or "")]
        self.assertEqual(len(headers), 1)                                              # not 3: one card for the whole history
        self.assertTrue(any("Bản 3/3" in c.value for c in at.markdown))

    def test_the_navigator_moves_between_attempts_and_only_the_latest_is_actionable(self):
        sid1 = self.scenes[0]["id"]
        first = self.generate(sid1)
        second = self.reject_and_regenerate(first, sid1, "sai trang phục")
        at = self.app()
        self.assertTrue(any(b.key == f"hist_{self.pid}_{sid1}_prev" for b in at.button))
        self.assertTrue(any(b.key == f"a_{second}" for b in at.button))                # latest attempt: approve button present
        self.assertFalse(any(b.key == f"a_{first}" for b in at.button))                # older attempt not shown yet: no approve button for it
        prev = next(b for b in at.button if b.key == f"hist_{self.pid}_{sid1}_prev")
        at = prev.click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any("Bản 1/2 · bản cũ" in c.value for c in at.markdown))
        self.assertFalse(any(b.key == f"a_{first}" for b in at.button))                # still no approve, now that the old attempt is showing
        self.assertTrue(any(b.key == f"sel_btn_{first}" for b in at.button))           # only a "Chi tiết" button
        self.assertTrue(any("sai trang phục" in c.value for c in at.caption))          # why it was retried, visible without opening detail

    def test_filter_counts_are_per_scene_not_per_attempt(self):
        for r in self.scenes:
            self.generate(r["id"])
        sid1 = self.scenes[0]["id"]
        jid = self.p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND state='succeeded'", (sid1,)).fetchone()["id"]
        self.reject_and_regenerate(jid, sid1, "thử lại")                               # +2 more attempts on the same scene
        at = self.app()
        options = at.radio(key=f"filter_{self.pid}").options
        self.assertIn(f"Tất cả {len(self.scenes)}", options)                            # counts scenes, not the extra attempt

    def test_switching_scene_filter_does_not_crash_with_a_multi_attempt_history(self):
        sid1 = self.scenes[0]["id"]
        jid = self.generate(sid1)
        self.reject_and_regenerate(jid, sid1, "gen lại")
        at = self.app()
        at.radio(key=f"filter_{self.pid}").set_value(at.radio(key=f"filter_{self.pid}").options[1]).run()
        self.assertFalse(at.exception)


if __name__ == "__main__":
    unittest.main()
