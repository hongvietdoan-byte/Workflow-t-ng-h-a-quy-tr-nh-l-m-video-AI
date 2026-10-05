"""S14.42 — duyệt tài nguyên Kho theo 3 tầng: pending -> claude_ok (Claude duyệt sơ bộ, dùng được) -> approved (người dùng xác nhận).

Chỉ kiểm LOGIC trạng thái (không phụ thuộc pixel)."""
import os
import shutil
import tempfile
import unittest

from core import asset_checklist, asset_vision, assets, kho_review, sound_lib
from core.db import connect
from tests.test_new_skills import PNG


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.conn = connect()
        self.pid = self.conn.execute("INSERT INTO projects (name, created_at) VALUES ('t', datetime('now'))").lastrowid
        self.conn.commit()

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def image(self, name="HUD A", kind="prop", status="pending", role=None):
        aid = assets.create(self.conn, "FF", kind, name, created_by="S14.33")
        assets.add_image(self.conn, aid, "a.png", PNG, status=status, role=role)
        iid = self.conn.execute("SELECT id FROM asset_images WHERE asset_id=?", (aid,)).fetchone()[0]
        return aid, iid

    def status(self, iid):
        return self.conn.execute("SELECT status FROM asset_images WHERE id=?", (iid,)).fetchone()[0]


class ImageStates(Base):
    def test_claude_ok_is_a_known_status(self):
        self.assertIn("claude_ok", assets.STATUSES)
        _, iid = self.image(status="claude_ok")
        self.assertEqual(self.status(iid), "claude_ok")        # not turned into 'pending' by add_image

    def test_pending_is_not_usable_claude_ok_is_and_is_marked(self):
        a1, _ = self.image("Chờ", status="pending")
        a2, i2 = self.image("Claude", status="claude_ok")
        a3, _ = self.image("Người", status="approved")
        self.assertEqual(assets.get(self.conn, a1)["images"], [])               # pending of someone else: still not usable
        got = assets.get(self.conn, a2)["images"]
        self.assertEqual([i["id"] for i in got], [i2])
        self.assertEqual(got[0]["status"], "claude_ok")                          # the screen can show the 'Claude duyệt' mark
        self.assertEqual(assets.get(self.conn, a3)["images"][0]["status"], "approved")
        self.assertTrue(assets.get(self.conn, a2)["claude_only"] == 1 and not assets.get(self.conn, a3)["claude_only"])

    def test_standard_set_takes_claude_ok_front(self):
        a, _ = self.image("Nhân vật", kind="character", status="claude_ok", role="front_standard")
        self.assertEqual(len(assets.standard_set(assets.get(self.conn, a), False)), 1)

    def test_checklist_library_counts_claude_ok(self):
        self.image("Kelly", kind="character", status="claude_ok")
        self.image("Maxim", kind="character", status="pending")
        lib = {a["name"]: a["images"] for a in asset_checklist.library(self.conn, self.pid)}
        self.assertEqual(lib["Kelly"], 1)
        self.assertEqual(lib["Maxim"], 0)


class Transitions(Base):
    def test_claude_approve_only_moves_pending_and_logs_why(self):
        _, p = self.image(status="pending")
        _, a = self.image("B", status="approved")
        n = kho_review.claude_approve(self.conn, [p, a], "nền sạch, đúng loại HUD")
        self.assertEqual(n, 1)
        self.assertEqual(self.status(p), "claude_ok")
        self.assertEqual(self.status(a), "approved")                              # a person's approval is never lowered
        log = kho_review.history(self.conn, "image", p)
        self.assertIn("Claude S14.42 duyệt sơ bộ: nền sạch, đúng loại HUD", log[-1]["note"])

    def test_revoke_goes_back_to_pending_and_unusable(self):
        aid, i = self.image(status="claude_ok")
        kho_review.revoke(self.conn, "image", i)
        self.assertEqual(self.status(i), "pending")
        self.assertEqual(assets.get(self.conn, aid)["images"], [])

    def test_confirm_makes_approved_and_refuses_pending(self):
        _, i = self.image(status="claude_ok")
        _, j = self.image("B", status="pending")
        kho_review.confirm(self.conn, "image", i)
        self.assertEqual(self.status(i), "approved")
        with self.assertRaises(kho_review.ReviewError):
            kho_review.confirm(self.conn, "image", j)                             # a person must look at a pending one in the normal box
        self.assertEqual(self.status(j), "pending")

    def test_reject_keeps_the_item_and_lists_it(self):
        _, i = self.image(status="pending")
        kho_review.reject(self.conn, "image", i, "mờ")
        self.assertEqual(self.status(i), "pending")                               # not deleted, not usable
        self.assertEqual([r["item_id"] for r in kho_review.rejected(self.conn, "image")], [i])
        kho_review.claude_approve(self.conn, [i], "xem lại")                      # a later pass can approve it: no longer rejected
        self.assertEqual(kho_review.rejected(self.conn, "image"), [])

    def test_other_pending_never_touched_by_game_filter(self):
        _, mine = self.image("Của S14.33", status="pending")
        self.conn.execute("UPDATE assets SET created_by='S14.33' WHERE id=(SELECT asset_id FROM asset_images WHERE id=?)", (mine,))
        _, other = self.image("Của người khác", status="pending")
        self.conn.execute("UPDATE assets SET created_by=NULL WHERE id=(SELECT asset_id FROM asset_images WHERE id=?)", (other,))
        got = [r["id"] for r in kho_review.pending_of(self.conn, "S14.33")]
        self.assertEqual(got, [mine])


class Sounds(Base):
    def sound(self, name, kind="music"):
        self.conn.execute("INSERT OR IGNORE INTO sound_sources (id, path) VALUES (2, ?)", (self.dir,))
        cur = self.conn.execute("INSERT INTO sounds (source_id, path, name, kind, mood, ext) VALUES (2,?,?,?,?,?)",
                                (os.path.join(self.dir, name + ".mp3"), name, kind, "vui vẻ", ".mp3"))
        self.conn.commit()
        return cur.lastrowid

    def test_sound_states(self):
        s = self.sound("a")
        self.assertEqual(kho_review.sound_state(self.conn, s), "pending")
        kho_review.claude_approve_sound(self.conn, s, "có tiếng, 13 s, nhạc")
        self.assertEqual(kho_review.sound_state(self.conn, s), "claude_ok")
        kho_review.confirm(self.conn, "sound", s)
        self.assertEqual(kho_review.sound_state(self.conn, s), "user_ok")
        kho_review.revoke(self.conn, "sound", s)
        self.assertEqual(kho_review.sound_state(self.conn, s), "pending")

    def test_rejected_sound_is_not_suggested(self):
        good, bad = self.sound("good"), self.sound("bad")
        kho_review.reject(self.conn, "sound", bad, "chỉ có ồn")
        ids = [r["id"] for r in sound_lib.suggest_music(self.conn, ["vui"], limit=5)]
        self.assertIn(good, ids)
        self.assertNotIn(bad, ids)


class Warnings(Base):
    def test_delivery_warns_for_claude_only_items_of_the_project(self):
        pid = self.pid
        a1, _ = self.image("Dùng", status="claude_ok")
        a2, _ = self.image("Đã xác nhận", status="approved")
        a3, _ = self.image("Không gắn", status="claude_ok")
        assets.attach(self.conn, pid, a1)
        assets.attach(self.conn, pid, a2)
        text = kho_review.delivery_warnings(self.conn, pid)
        self.assertEqual(len(text), 1)
        self.assertIn("Dùng", text[0])
        self.assertNotIn("Không gắn", text[0])
        kho_review.confirm_asset(self.conn, a1)
        self.assertEqual(kho_review.delivery_warnings(self.conn, pid), [])


if __name__ == "__main__":
    unittest.main()
