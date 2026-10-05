"""Đợt 3 (01/10): vai dựng sẵn, tiền theo người, hạn mức cảnh báo, ai đang mở, hộp 📥 Việc cần bạn."""
import json
import unittest

from core import budget, inbox, team
from core.db import connect
from core.pipeline import Pipeline


class RoleTests(unittest.TestCase):
    def test_roles_map_to_existing_permissions_and_back(self):
        from core import auth
        for key, r in team.ROLES.items():
            self.assertTrue(set(r["perms"]) <= set(auth.PERM_LABELS), key)         # no new permission invented
            self.assertEqual(team.role_of(r["perms"]), key)
        self.assertEqual(team.role_of(["knowledge"]), "custom")
        self.assertEqual(team.role_label({"role": "owner", "perms": []}), "Owner")
        self.assertEqual(team.role_label({"role": "member", "perms": ["knowledge"]}), "Tùy chỉnh")
        self.assertEqual(team.perms_for("manager"), team.ROLES["manager"]["perms"])


class MoneyTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t", created_by="lan@garena.vn")
        sid = self.p.create_scene(self.pid, 1, "s1")
        self.job = self.p.create_job(sid, "image_gen", created_by="lan@garena.vn") if "created_by" in self.p.create_job.__code__.co_varnames else self.p.create_job(sid, "image_gen")
        self.p.conn.execute("UPDATE jobs SET created_by='lan@garena.vn' WHERE id=?", (self.job,))
        self.p.conn.commit()

    def test_spend_is_counted_per_person_from_the_price_table(self):
        from core import cost
        pricing = cost.load_pricing()
        model = next(iter(pricing.get("per_image", {})))
        self.p.conn.execute("INSERT INTO usage_events (job_id, project_id, kind, provider, model, tier, quantity, unit, at)"
                            " VALUES (?,?,?,?,?,?,?,?,datetime('now'))", (self.job, self.pid, "image", "deepix", model, "std", 2, "image"))
        self.p.conn.commit()
        got = team.spend_by_user(self.p.conn, 30)
        self.assertGreater(got.get("lan@garena.vn", 0), 0)
        self.assertEqual(team.spend_by_user(self.p.conn, 30).get("nobody@x"), None)

    def test_limit_is_a_warning_only(self):
        self.assertIsNone(team.limit_status(self.p.conn, "lan@garena.vn"))
        team.set_limit(self.p.conn, "lan@garena.vn", 0.0001)
        self.assertEqual(team.get_limit(self.p.conn, "Lan@Garena.vn"), 0.0001)
        team.set_limit(self.p.conn, "lan@garena.vn", None)
        self.assertIsNone(team.get_limit(self.p.conn, "lan@garena.vn"))


class PresenceTests(unittest.TestCase):
    def test_other_people_seen_for_two_minutes(self):
        conn = connect()
        team.touch(conn, 7, "lan@garena.vn", now=1000.0)
        team.touch(conn, 7, "minh@garena.vn", now=1010.0)
        self.assertEqual(team.open_by(conn, 7, exclude="minh@garena.vn", now=1060.0), ["lan@garena.vn"])
        self.assertEqual(team.open_by(conn, 7, exclude="lan@garena.vn", now=1060.0), ["minh@garena.vn"])
        self.assertEqual(team.open_by(conn, 7, exclude="x", now=1000.0 + team.PRESENCE_SECONDS + 5), ["minh@garena.vn"])
        team.touch(conn, 7, "lan@garena.vn", now=1005.0)                          # < 30 s later: not rewritten
        self.assertEqual(json.loads(conn.execute("SELECT value FROM app_settings WHERE key='presence:7'").fetchone()[0])["lan@garena.vn"], 1000.0)


class InboxTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.mine = self.p.create_project("của Việt", created_by="viet@garena.vn")
        self.other = self.p.create_project("của Lan", created_by="lan@garena.vn")
        for pid in (self.mine, self.other):
            sid = self.p.create_scene(pid, 1, "s")
            jid = self.p.create_job(sid, "image_gen")
            self.p.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (jid,))
            vid = self.p.create_job(sid, "video_gen")
            self.p.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (vid,))
        self.p.conn.commit()

    def test_a_member_sees_only_own_projects_and_the_owner_can_see_the_team(self):
        got = inbox.items(self.p.conn, "viet@garena.vn", is_owner=False, can_money=False, auth_on=True)
        self.assertEqual({i["project_id"] for i in got}, {self.mine})
        self.assertEqual({i["kind"] for i in got}, {"Ảnh", "Video"})
        team_all = inbox.items(self.p.conn, "viet@garena.vn", is_owner=True, auth_on=True, team_wide=True)
        self.assertEqual({i["project_id"] for i in team_all if i["project_id"]}, {self.mine, self.other})
        self.assertTrue(any(i["who"] == "lan@garena.vn" for i in team_all))

    def test_sign_in_off_everything_is_mine(self):
        got = inbox.items(self.p.conn, "", auth_on=False)
        self.assertEqual({i["project_id"] for i in got}, {self.mine, self.other})

    def test_out_of_credit_and_limit_warnings_only_for_money_people(self):
        budget.halt(self.p.conn, "clipai", "no money")
        a = inbox.items(self.p.conn, "m@garena.vn", is_owner=False, can_money=False, auth_on=True)
        self.assertFalse([i for i in a if i["kind"] == "Tiền"])
        b = inbox.items(self.p.conn, "viet@garena.vn", is_owner=True, can_money=True, auth_on=True)
        self.assertTrue([i for i in b if i["kind"] == "Tiền" and "clipai" in i["text"]])

    def test_failed_generation_is_listed_only_for_the_latest_job_of_a_shot(self):
        """S14.8 U4: job ảnh/video lỗi (failed/retryable) mới nhất của mỗi cảnh → mục "Lỗi gen" (ảnh → storyboard, video → video);
        cảnh đã có job mới hơn không lỗi thì không nhắc."""
        sid2 = self.p.create_scene(self.mine, 2, "s2")
        sid3 = self.p.create_scene(self.mine, 3, "s3")
        img = self.p.create_job(sid2, "image_gen")
        vid = self.p.create_job(sid3, "video_gen")
        old = self.p.create_job(sid3, "image_gen")
        self.p.conn.execute("UPDATE jobs SET state='failed' WHERE id IN (?,?)", (img, old))
        self.p.conn.execute("UPDATE jobs SET state='retryable' WHERE id=?", (vid,))
        self.p.create_job(sid3, "image_gen")                                     # cảnh 3: ảnh lỗi cũ đã có lượt mới → không nhắc
        self.p.conn.commit()
        self.assertIn("Lỗi gen", inbox.KINDS)
        got = [i for i in inbox.items(self.p.conn, "viet@garena.vn", is_owner=False, can_money=False, auth_on=True) if i["kind"] == "Lỗi gen"]
        self.assertEqual(sorted((i["screen"], i["level"]) for i in got), [("storyboard", "bad"), ("video", "bad")])
        texts = " | ".join(i["text"] for i in got)
        self.assertIn("ảnh shot 2", texts)
        self.assertIn("clip shot 3", texts)
        self.assertNotIn("ảnh shot 3", texts)

    def test_archived_projects_are_not_listed(self):
        from core import archive
        archive.archive(self.p, self.mine)
        got = inbox.items(self.p.conn, "viet@garena.vn", is_owner=True, auth_on=True, team_wide=True)
        self.assertNotIn(self.mine, {i["project_id"] for i in got})


if __name__ == "__main__":
    unittest.main()


class AutomationLevelTests(unittest.TestCase):
    def setUp(self):
        from core import qc_policy
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("lv")
        qc_policy.apply(self.p, self.pid, "balanced")

    def test_a_new_project_is_the_main_gates_level_and_each_level_reads_back(self):
        from core import automation
        self.assertEqual(automation.current(self.p, self.pid), "main")
        for key in ("all", "auto", "main"):
            automation.apply(self.p, self.pid, key)
            self.assertEqual(automation.current(self.p, self.pid), key)

    def test_changing_one_underlying_setting_by_hand_shows_as_custom(self):
        from core import automation, autopilot
        automation.apply(self.p, self.pid, "all")
        autopilot.set_gates(self.p, self.pid, {"pilot": False})
        self.assertEqual(automation.current(self.p, self.pid), "custom")
        with self.assertRaises(ValueError):
            automation.apply(self.p, self.pid, "nope")
