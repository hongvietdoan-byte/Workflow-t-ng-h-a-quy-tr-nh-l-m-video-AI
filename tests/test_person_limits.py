"""S14.18 (mục 6d kế hoạch nâng cấp dashboard): giới hạn theo NGƯỜI, kiểm ở lõi (core/person_limits.py) — mọi đường tạo / cất dự án.

(a) tối đa 2 dự án DỞ song song (chưa XUẤT BẢN GIAO — S14.30; đã cất / đã xóa không tính) · (b) 2 dự án tạo mới / ngày, thứ 3 cần Owner duyệt
· tối đa 1 dự án DỞ đang cất (dự án xong cất vào "Kho dự án đã xong", không giới hạn) · Owner không giới hạn, Owner nâng mức riêng từng người
· trần job/ngày chung AUTOPILOT_DAILY_JOBS bỏ."""
import os
import sqlite3
import tempfile
import unittest
from unittest import mock

from core import archive, auth, compare, person_limits as PL
from core.auth import Identity
from core.db import connect
from core.pipeline import Pipeline

OWNER = auth.OWNER_EMAIL
MEM = "nv@garena.vn"
OTHER = "khac@garena.vn"


def owner_id() -> Identity:
    return Identity(OWNER, "owner", "owner", [])


def as_user(conn, email: str, role: str = "member") -> Pipeline:
    p = Pipeline(conn)
    p.user = {"email": email, "role": role}
    p.actor = email
    return p


def render_only(conn, pid: int) -> None:
    """Only the final render (Dựng thử / first cut) — S14.30: NOT finished any more."""
    conn.execute("INSERT INTO outputs (project_id, kind, path, manifest, created_at) VALUES (?, 'final', ?, '{}', datetime('now'))", (pid, f"/x/{pid}.mp4"))
    conn.commit()


def finish(conn, pid: int) -> None:
    """A delivered project (S14.30): the "Bản giao" step exported it — what the 📥 box and the limits call "xong"."""
    from core import delivered
    render_only(conn, pid)
    delivered.mark(conn, pid, f"/x/{pid}.mp4", by=MEM)


class Base(unittest.TestCase):
    def setUp(self):
        _data = __import__("tempfile").mkdtemp(prefix="limits_data_")      # 06/10: never the real data/projects of this computer
        _env = __import__("unittest.mock", fromlist=["patch"]).patch.dict(os.environ, {"PIPELINE_DATA": _data})
        _env.start(); self.addCleanup(_env.stop)
        self.conn = connect()
        auth.ensure_owner(self.conn)
        auth.add_user(self.conn, owner_id(), MEM, [])
        auth.add_user(self.conn, owner_id(), OTHER, [])
        self.me = as_user(self.conn, MEM)

    def make(self, name: str, p=None) -> int:
        p = p or self.me
        return p.create_project(name, created_by=p.user["email"])


class OpenProjectLimit(Base):
    def test_third_open_project_is_refused_with_the_list(self):
        a, b = self.make("A"), self.make("B")
        with self.assertRaises(PL.LimitReached) as e:
            self.make("C")
        err = e.exception
        self.assertEqual(err.kind, "open")
        self.assertEqual([r["id"] for r in err.projects], [a, b])
        self.assertIn("2/2", str(err))
        self.assertTrue(all("step" in r and "spent" in r for r in err.projects))     # tên, bước đang ở, đã chi ước tính
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0], 2)

    def test_archived_finished_or_deleted_projects_do_not_count(self):
        PL.set_limits(self.conn, {"email": OWNER, "role": "owner"}, MEM, daily=10)   # the daily limit is not what is tested here
        a, b = self.make("A"), self.make("B")
        archive.archive(self.me, a)                         # BỎ = cất: frees a place
        c = self.make("C")
        finish(self.conn, b)                                # hoàn thiện: not open any more
        self.make("D")
        with self.assertRaises(PL.LimitReached):
            self.make("E")                                  # C + D open
        self.me.delete_project(c)
        self.make("E")

    def test_someone_else_projects_do_not_count(self):
        o = as_user(self.conn, OTHER)
        self.make("O1", o), self.make("O2", o)
        self.make("A"), self.make("B")

    def test_clone_is_a_new_project_too(self):
        a, _ = self.make("A"), self.make("B")
        with self.assertRaises(PL.LimitReached):
            compare.clone_project(self.me, a, "bản sao")

    def test_restoring_a_parked_project_at_the_limit_is_refused_then_swap_works(self):
        a, b = self.make("A"), self.make("B")
        archive.archive(self.me, a)
        with mock.patch.object(PL, "_today", return_value="2099-01-01"):
            c = self.make("C")
        with self.assertRaises(PL.LimitReached) as e:
            archive.restore(self.me, a)
        self.assertEqual(e.exception.kind, "open")
        archive.swap(self.me, put_away=c, bring_back=a)       # GIỮ a, BỎ c in one go: never 3 open nor 2 parked
        self.assertFalse(archive.is_archived(self.me.project(a)))
        self.assertTrue(archive.is_archived(self.me.project(c)))
        self.assertEqual({r["id"] for r in PL.open_projects(self.conn, MEM)}, {a, b})


class DailyLimit(Base):
    def test_third_creation_of_the_day_needs_owner_approval(self):
        a = self.make("A")
        b = self.make("B")
        self.me.delete_project(a), self.me.delete_project(b)       # deleting does not give the day's places back
        with self.assertRaises(PL.LimitReached) as e:
            self.make("C")
        self.assertEqual(e.exception.kind, "daily")
        self.assertIn(f"Hôm nay bạn đã tạo 2/2 dự án: #{a}, #{b}", str(e.exception))
        with self.assertRaises(ValueError):
            PL.request(self.conn, self.me.user, "daily", "  ")       # a reason is required
        rid = PL.request(self.conn, self.me.user, "daily", "cần làm gấp bản cho sự kiện")
        self.assertEqual(PL.pending_count(self.conn), 1)
        with self.assertRaises(PL.LimitReached):
            self.make("C")                                          # still waiting
        with self.assertRaises(auth.AuthError):
            PL.approve(self.conn, {"email": OTHER, "role": "member"}, rid)
        PL.approve(self.conn, {"email": OWNER, "role": "owner"}, rid)
        c = self.make("C")
        row = self.conn.execute("SELECT status, used_project_id FROM limit_requests WHERE id=?", (rid,)).fetchone()
        self.assertEqual((row["status"], row["used_project_id"]), ("used", c))
        self.me.delete_project(c)
        with self.assertRaises(PL.LimitReached):
            self.make("D")                                          # one approval = one project
        actions = [r["action"] for r in auth.recent_audit(self.conn)]
        self.assertIn("limit_request", actions)
        self.assertIn("limit_approve", actions)

    def test_rejected_request_does_not_open_a_place(self):
        a, b = self.make("A"), self.make("B")
        archive.archive(self.me, a)
        finish(self.conn, b)
        rid = PL.request(self.conn, self.me.user, "daily", "thử")
        PL.reject(self.conn, {"email": OWNER, "role": "owner"}, rid)
        with self.assertRaises(PL.LimitReached) as e:
            self.make("C")
        self.assertEqual(e.exception.kind, "daily")
        self.assertEqual(PL.pending_count(self.conn), 0)

    def test_owner_inbox_lists_waiting_requests(self):
        from core import inbox
        self.make("A"), self.make("B")
        PL.request(self.conn, self.me.user, "daily", "lý do")
        rows = [i for i in inbox.items(self.conn, OWNER, True, True, True) if i["kind"] == "Yêu cầu"]
        self.assertEqual(len(rows), 1)
        self.assertIn("1 yêu cầu", rows[0]["text"])
        self.assertFalse([i for i in inbox.items(self.conn, MEM, False, False, True) if i["kind"] == "Yêu cầu"])


class ParkedLimit(Base):
    def test_second_unfinished_parked_project_is_refused_finished_ones_are_free(self):
        a, b = self.make("A"), self.make("B")
        archive.archive(self.me, a)
        with self.assertRaises(PL.LimitReached) as e:
            archive.archive(self.me, b)
        self.assertEqual(e.exception.kind, "parked")
        self.assertIn("1/1", str(e.exception))
        self.assertEqual([r["id"] for r in e.exception.projects], [a])
        self.assertFalse(archive.is_archived(self.me.project(b)))
        finish(self.conn, b)
        archive.archive(self.me, b)                                 # a finished project goes to the "Kho dự án đã xong": no limit
        self.assertEqual([r["id"] for r in archive.finished_projects(self.conn)], [b])
        self.assertEqual([r["id"] for r in archive.parked_projects(self.conn)], [a])

    def test_owner_approval_lets_one_more_be_parked(self):
        a, b = self.make("A"), self.make("B")
        archive.archive(self.me, a)
        rid = PL.request(self.conn, self.me.user, "parked", "giữ lại để so sánh", project_id=b)
        PL.approve(self.conn, {"email": OWNER, "role": "owner"}, rid)
        archive.archive(self.me, b)
        self.assertTrue(archive.is_archived(self.me.project(b)))
        self.assertEqual(self.conn.execute("SELECT status FROM limit_requests WHERE id=?", (rid,)).fetchone()[0], "used")


class OwnerAndOverrides(Base):
    def test_owner_has_no_limit(self):
        o = as_user(self.conn, OWNER, "owner")
        ids = [o.create_project(f"O{i}", created_by=OWNER) for i in range(4)]
        archive.archive(o, ids[0]), archive.archive(o, ids[1])

    def test_scripts_without_a_signed_in_person_are_not_limited(self):
        system = Pipeline(self.conn)
        for i in range(4):
            system.create_project(f"s{i}", created_by="claude-code-test")

    def test_owner_raises_one_person_limits(self):
        with self.assertRaises(auth.AuthError):
            PL.set_limits(self.conn, {"email": MEM, "role": "member"}, MEM, open=5)
        PL.set_limits(self.conn, {"email": OWNER, "role": "owner"}, MEM, open=3, daily=3, parked=2)
        self.assertEqual(PL.limits(self.conn, MEM), {"open": 3, "daily": 3, "parked": 2})
        self.assertEqual(PL.limits(self.conn, OTHER), PL.BASE)
        a, b, c = self.make("A"), self.make("B"), self.make("C")
        archive.archive(self.me, a), archive.archive(self.me, b)
        with self.assertRaises(PL.LimitReached) as e:
            self.make("D")
        self.assertIn("3/3", str(e.exception))
        self.assertIn("limit_set", [r["action"] for r in auth.recent_audit(self.conn)])


class DailyJobCapRemoved(unittest.TestCase):
    def test_autopilot_daily_jobs_no_longer_stops_anything(self):
        from core import autopilot, cost, perf
        p = Pipeline(connect())
        pid = p.create_project("d")
        for _ in range(5):
            cost.record_usage(p.conn, None, "image", "deepix", "gpt-image-2", "1k", 1, "image", project_id=pid)
        self.assertFalse(hasattr(autopilot, "_daily_cap"))
        self.assertFalse(hasattr(perf, "daily_limit"))
        with mock.patch.dict(os.environ, {"AUTOPILOT_DAILY_JOBS": "1"}):
            self.assertEqual(perf.snapshot(p.conn)["sends_today"], 5)
            self.assertNotIn("daily_limit", perf.snapshot(p.conn))


class MigrationOnAnOldDatabase(unittest.TestCase):
    def test_old_database_gets_the_new_tables_and_keeps_its_rows(self):
        path = os.path.join(tempfile.mkdtemp(), "old.sqlite")
        conn = connect(path)
        Pipeline(conn).create_project("cũ", created_by=MEM)
        conn.execute("DROP TABLE limit_requests")
        conn.execute("DROP TABLE project_creations")
        conn.commit()
        conn.close()
        raw = sqlite3.connect(path)
        self.assertEqual(raw.execute("SELECT COUNT(*) FROM sqlite_master WHERE name IN ('limit_requests','project_creations')").fetchone()[0], 0)
        raw.close()
        conn = connect(path)                                        # DROP changed schema_version: migrated again, like an old file
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"limit_requests", "project_creations"} <= names)
        self.assertEqual([r["name"] for r in conn.execute("SELECT name FROM projects")], ["cũ"])
        self.assertEqual([r["id"] for r in PL.open_projects(conn, MEM)], [1])


class ReviewFixes(Base):
    """Rà độc lập 05/10: các lỗ của S14.18."""

    def test_cloning_a_parked_project_gives_an_open_copy(self):
        a = self.make("A")
        archive.archive(self.me, a)
        new = compare.clone_project(self.me, a, "bản sao")
        self.assertFalse(archive.is_archived(self.me.project(new)))      # never a 2nd unfinished 📦 through a copy
        self.assertEqual([r["id"] for r in PL.parked_projects(self.conn, MEM)], [a])

    def test_one_approval_is_not_used_twice_by_two_creations_at_once(self):
        import threading
        import time
        path = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        conn = connect(path)
        auth.ensure_owner(conn)
        auth.add_user(conn, owner_id(), MEM, [])
        PL.set_limits(conn, {"email": OWNER, "role": "owner"}, MEM, open=10)
        me = as_user(conn, MEM)
        for name in ("A", "B"):
            me.create_project(name, created_by=MEM)
        rid = PL.request(conn, me.user, "daily", "gấp")
        PL.approve(conn, {"email": OWNER, "role": "owner"}, rid)
        real = PL._approved

        def slow(*a, **k):                      # both creations pass the check before either writes: the race window, made wide
            out = real(*a, **k)
            time.sleep(0.3)
            return out
        made, refused = [], []

        def worker(name):
            p = as_user(connect(path), MEM)
            try:
                made.append(p.create_project(name, created_by=MEM))
            except PL.LimitReached:
                refused.append(name)
        with mock.patch.object(PL, "_approved", side_effect=slow):
            threads = [threading.Thread(target=worker, args=(n,)) for n in ("C", "D")]
            [t.start() for t in threads]
            [t.join() for t in threads]
        self.assertEqual((len(made), len(refused)), (1, 1))
        check = connect(path)
        self.assertEqual(check.execute("SELECT COUNT(*) FROM project_creations WHERE email=?", (MEM,)).fetchone()[0], 3)
        self.assertEqual(check.execute("SELECT used_project_id FROM limit_requests WHERE id=?", (rid,)).fetchone()[0], made[0])

    def test_a_swap_that_fails_half_way_changes_nothing(self):
        a, b = self.make("A"), self.make("B")
        rid = PL.request(self.conn, self.me.user, "parked", "giữ", project_id=b)
        PL.approve(self.conn, {"email": OWNER, "role": "owner"}, rid)
        archive.archive(self.me, a)
        with mock.patch.object(PL, "_use", side_effect=RuntimeError("hỏng giữa chừng")), self.assertRaises(RuntimeError):
            archive.archive(self.me, b)
        self.assertFalse(archive.is_archived(self.me.project(b)))
        self.assertEqual(self.me.project(b)["paused"], 0)
        self.assertEqual(self.conn.execute("SELECT status FROM limit_requests WHERE id=?", (rid,)).fetchone()[0], "approved")
        c = self.conn.execute("SELECT 1").fetchone()                       # the connection is usable (no transaction left open)
        self.assertIsNotNone(c)
        PL.set_limits(self.conn, {"email": OWNER, "role": "owner"}, MEM, parked=0)   # the swap then needs the approval: _use runs
        with mock.patch.object(PL, "_use", side_effect=RuntimeError("hỏng")), self.assertRaises(RuntimeError):
            archive.swap(self.me, put_away=b, bring_back=a)
        self.assertTrue(archive.is_archived(self.me.project(a)))
        self.assertFalse(archive.is_archived(self.me.project(b)))
        self.assertEqual(len(PL.parked_projects(self.conn, MEM)), 1)

    def test_old_project_with_only_final_video_file_is_not_finished(self):
        """S14.30 (đổi từ S14.18): chỉ có FINAL_VIDEO.mp4 = mới ghép, chưa xuất bản giao → vẫn là dự án dở."""
        data = tempfile.mkdtemp()
        a = self.make("A")
        os.makedirs(os.path.join(data, str(a), "output"))
        open(os.path.join(data, str(a), "output", "FINAL_VIDEO.mp4"), "wb").close()
        with mock.patch.dict(os.environ, {"PIPELINE_DATA": data}):
            self.assertFalse(PL.is_finished(self.conn, a))
            self.assertEqual([r["id"] for r in PL.open_projects(self.conn, MEM)], [a])
            self.assertTrue(PL.open_projects(self.conn, MEM)[0]["rendered"])


class FinishedMeansDelivered(Base):
    """S14.30: "hoàn thiện" = đã xuất bản giao; bản ghép cuối đầu tiên chưa tính."""

    def test_a_rendered_but_not_delivered_project_still_takes_an_open_place(self):
        PL.set_limits(self.conn, {"email": OWNER, "role": "owner"}, MEM, daily=10)   # the daily limit is not what is tested here
        a, b = self.make("A"), self.make("B")
        render_only(self.conn, a)
        self.assertFalse(PL.is_finished(self.conn, a))
        with self.assertRaises(PL.LimitReached) as e:
            self.make("C")
        msg = str(e.exception)
        self.assertIn(f"#{a}", msg)
        self.assertIn("xuất bản giao để tính là xong", msg)          # nói rõ cách thoát giới hạn
        self.assertTrue(e.exception.projects[0]["rendered"])
        finish(self.conn, a)
        self.make("C")

    def test_message_without_a_rendered_project_does_not_mention_delivering(self):
        self.make("A"), self.make("B")
        with self.assertRaises(PL.LimitReached) as e:
            self.make("C")
        self.assertNotIn("để tính là xong", str(e.exception))

    def test_a_rendered_project_put_away_is_parked_not_in_the_finished_store(self):
        a, b = self.make("A"), self.make("B")
        archive.archive(self.me, a)
        render_only(self.conn, b)
        with self.assertRaises(PL.LimitReached) as e:
            archive.archive(self.me, b)
        self.assertEqual(e.exception.kind, "parked")
        self.assertIn(f"#{b}", str(e.exception))
        self.assertIn("xuất bản giao để tính là xong", str(e.exception))
        self.assertEqual(archive.finished_projects(self.conn), [])
        finish(self.conn, b)
        archive.archive(self.me, b)
        self.assertEqual([r["id"] for r in archive.finished_projects(self.conn)], [b])

    def test_an_old_daily_approval_shows_expired(self):
        self.make("A"), self.make("B")
        rid = PL.request(self.conn, self.me.user, "daily", "gấp")
        PL.approve(self.conn, {"email": OWNER, "role": "owner"}, rid)
        row = PL.requests(self.conn)[0]
        self.assertEqual(PL.status_label(row), PL.STATUS_LABELS["approved"])
        with mock.patch.object(PL, "_today", return_value="2099-01-01"):
            self.assertEqual(PL.status_label(PL.requests(self.conn)[0]), "⌛ hết hạn (duyệt cho ngày " + row["decided_day"] + ")")


if __name__ == "__main__":
    unittest.main()
