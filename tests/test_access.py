"""Đợt F (02/10): quyền theo DỰ ÁN — chủ / Owner / người theo dõi (chỉ xem · được sửa) / người lạ, thực thi cứng ở lõi (core/access.py).

Ma trận: 5 vai × (xem · sửa · gửi job · duyệt · chạy tự động · cất · xóa · đổi người theo dõi · inbox · danh sách ⌂)."""
import os
import sqlite3
import tempfile
import unittest

from core import access, archive, auth, autopilot, batch, compare, delivery, end_frames, inbox, llm_runner, pilot, project_budget
from core import (audio_lib, claude_tasks, costume, editor_apply, editor_review, experiments, llm_io, model_router, music, previz, qc_agent,
                  voice, voice_check)
from core.access import AccessDenied
from core.auth import Identity
from core.db import connect
from core.pipeline import Pipeline

OWNER = auth.OWNER_EMAIL
_TMP = tempfile.mkdtemp(prefix="access_matrix_")          # data dir for the core calls of the matrix: never the repo folder
CREATOR, WVIEW, WEDIT, STRANGER = "chu@garena.vn", "xem@garena.vn", "sua@garena.vn", "la@garena.vn"
WHO = {"owner": {"email": OWNER, "role": "owner"}, "creator": {"email": CREATOR, "role": "member"},
       "watch_edit": {"email": WEDIT, "role": "member"}, "watch_view": {"email": WVIEW, "role": "member"},
       "stranger": {"email": STRANGER, "role": "member"}}
ROLES = list(WHO)
# who may do what (the policy the user decided): True = allowed
CAN = {
    "view":    {"owner": True, "creator": True, "watch_edit": True, "watch_view": True, "stranger": False},
    "edit":    {"owner": True, "creator": True, "watch_edit": True, "watch_view": False, "stranger": False},
    "manage":  {"owner": True, "creator": True, "watch_edit": False, "watch_view": False, "stranger": False},
}


def owner_identity() -> Identity:
    return Identity(OWNER, "owner", "owner", [])


def make_world(conn=None):
    """A database with the 5 people, one project (made by CREATOR) with a scene and an image waiting for review, watchers set."""
    conn = conn or connect()
    auth.ensure_owner(conn)
    for email in (CREATOR, WVIEW, WEDIT, STRANGER):
        auth.add_user(conn, owner_identity(), email, [])
    system = Pipeline(conn)
    pid = system.create_project("dự án của chủ", created_by=CREATOR)
    sid = system.create_scene(pid, 1, "cảnh 1")
    jid = system.create_job(sid, "image_gen")
    conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (jid,))
    conn.commit()
    access.set_watcher(conn, WHO["owner"], pid, WVIEW, "view")
    access.set_watcher(conn, WHO["creator"], pid, WEDIT, "edit")
    return conn, pid, sid, jid


def as_user(conn, role: str) -> Pipeline:
    p = Pipeline(conn)
    p.user = dict(WHO[role])
    p.actor = WHO[role]["email"]
    return p


def outcome(fn) -> str:
    """'denied' when the rights refuse, 'ok' otherwise (any other error means the call got past the rights check)."""
    try:
        fn()
    except AccessDenied:
        return "denied"
    except Exception:  # noqa: BLE001 - past the guard; the call itself may fail for lack of a provider / script
        return "ok"
    return "ok"


class ConnFunctionsWithoutPTests(unittest.TestCase):
    """S14.7 (D1): p=None (autopilot / hệ thống) = hành vi cũ — không kiểm quyền."""

    def test_no_p_means_no_check(self):
        conn, pid, sid, _jid = make_world()
        project_budget.set_target(conn, pid, 5.0)
        model_router.set_override(conn, sid, None)
        self.assertEqual(outcome(lambda: voice.generate(conn, pid, None, _TMP)), "ok")


class WriteFunctionScanTests(unittest.TestCase):
    """S14.7 (D1, nguyên tắc 3 — test quét): một hàm lõi công khai nhận `p`/`pipeline` + mã dự án và GHI vào CSDL phải kiểm quyền
    (access.need_* / access.require, hoặc đi qua claude_tasks._run). Danh sách KNOWN = các hàm cũ chưa kiểm (ghi nhận 05/10, chỉ được
    co lại): hàm MỚI ghi mà thiếu kiểm quyền làm test đỏ."""
    KNOWN = {"hero_takes.step", "llm_io.unlock_scene_fields", "llm_io.store_motion_prompts", "music.set_off", "previz.compose_scene",
             "script_parser.import_scenes", "script_parser.store_end_card", "seedance_refs.code_motion", "shots.save_story_scenes",
             "shots.replace_from", "shots.store_plan", "style.save", "style.save_preset", "subjects.link", "subjects.unlink",
             "subtitles.save_settings"}

    def test_new_write_functions_check_the_right(self):
        import ast
        import glob
        import re
        write = re.compile(r"^\s*(INSERT|UPDATE|DELETE|REPLACE)\b")
        root = os.path.join(os.path.dirname(__file__), "..", "core")
        found = set()
        for path in sorted(glob.glob(os.path.join(root, "*.py"))):
            mod = os.path.splitext(os.path.basename(path))[0]
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            for n in tree.body:
                if not isinstance(n, ast.FunctionDef) or n.name.startswith("_"):
                    continue
                args = [a.arg for a in n.args.args]
                if len(args) < 2 or args[0] not in ("p", "pipeline") or args[1] not in ("pid", "project_id"):
                    continue
                if not any(isinstance(c, ast.Constant) and isinstance(c.value, str) and write.match(c.value) for c in ast.walk(n)):
                    continue
                src = ast.unparse(n)
                if "need_" in src or "access.require" in src or "_run(" in src:
                    continue
                found.add(f"{mod}.{n.name}")
        self.assertEqual(sorted(found - self.KNOWN), [], "hàm ghi mới thiếu access.need_* (thêm kiểm quyền ở đầu hàm)")


class LevelTests(unittest.TestCase):
    def setUp(self):
        self.conn, self.pid, self.sid, self.jid = make_world()

    def test_levels_of_the_five_people(self):
        got = {r: access.level(self.conn, self.pid, WHO[r]) for r in ROLES}
        self.assertEqual(got, {"owner": "admin", "creator": "own", "watch_edit": "edit", "watch_view": "view", "stranger": None})

    def test_can_view_edit_manage_matrix(self):
        for role in ROLES:
            self.assertEqual(access.can_view(self.conn, self.pid, WHO[role]), CAN["view"][role], role)
            self.assertEqual(access.can_edit(self.conn, self.pid, WHO[role]), CAN["edit"][role], role)
            self.assertEqual(access.can_manage(self.conn, self.pid, WHO[role]), CAN["manage"][role], role)

    def test_system_and_sign_in_off_are_unrestricted(self):
        self.assertTrue(access.can_edit(self.conn, self.pid, None))
        self.assertTrue(access.can_manage(self.conn, self.pid, {"email": "local", "role": "owner"}))
        p = Pipeline(self.conn)                                             # no user: background / tests / sign-in off
        p.set_paused(self.pid, True)

    def test_e_mail_case_does_not_matter(self):
        self.assertEqual(access.level(self.conn, self.pid, {"email": CREATOR.upper(), "role": "member"}), "own")
        self.assertEqual(access.level(self.conn, self.pid, {"email": WEDIT.upper(), "role": "member"}), "edit")

    def test_an_unknown_project_is_refused_for_a_member(self):
        self.assertIsNone(access.level(self.conn, 999, WHO["creator"]))
        self.assertEqual(access.level(self.conn, 999, WHO["owner"]), "admin")


class CoreEntryPointMatrix(unittest.TestCase):
    """Every way to send a job / edit / approve / run / put away / delete refuses the wrong people with a Vietnamese message."""

    def entry_points(self, p, pid, sid, jid):
        return {
            "edit": {
                "set_script_text": lambda: p.set_script_text(pid, "x"),
                "set_paused": lambda: p.set_paused(pid, True),
                "set_mode": lambda: p.set_mode(pid, "auto"),
                "set_project_field": lambda: p.set_project_field(pid, "look", "x"),
                "cancel_all_active": lambda: p.cancel_all_active(pid),
                "create_scene": lambda: p.create_scene(pid, 9, "mới"),
                "create_job (gửi job)": lambda: p.create_job(sid, "video_gen"),
                "approve (duyệt)": lambda: p.approve(jid),
                "reject (loại)": lambda: p.reject(jid, respawn=False),
                "cancel": lambda: p.cancel(jid),
                "autopilot.start": lambda: autopilot.start(p, pid),
                "autopilot.resume": lambda: autopilot.resume(p, pid),
                "autopilot.stop": lambda: autopilot.stop(p, pid),
                "autopilot.set_gates": lambda: autopilot.set_gates(p, pid, {"bible": False}),
                "batch.queue_images": lambda: batch.queue_images(p, pid),
                "batch.queue_videos": lambda: batch.queue_videos(p, pid, "."),
                "llm_runner.run_director": lambda: llm_runner.run_director(p, pid, llm_runner.MockLlm()),
                "llm_runner.run_motion": lambda: llm_runner.run_motion(p, pid, llm_runner.MockLlm(), "."),
                "delivery.render": lambda: delivery.render(p, pid, "."),
                "delivery.deliver": lambda: delivery.deliver(p, pid, "."),
                "project_budget.approve": lambda: project_budget.approve(p, pid, "x"),
                "pilot.start": lambda: pilot.start(p, pid),
                "end_frames.queue": lambda: end_frames.queue(p, pid),
                # S14.7 (D1, kế hoạch 3.5 ý 2): lớp lõi — hàm nhận `p`
                "llm_io.update_scene": lambda: llm_io.update_scene(p, pid, 1, {"title": "y"}),
                "llm_io.add_character": lambda: llm_io.add_character(p, pid, "Mới", "mô tả"),
                "llm_io.update_character": lambda: llm_io.update_character(p, pid, "Mới", "mô tả"),
                "llm_io.lock_character_bible": lambda: llm_io.lock_character_bible(p, pid),
                "llm_io.unlock_character_bible": lambda: llm_io.unlock_character_bible(p, pid),
                "llm_io.store_scene_analysis": lambda: llm_io.store_scene_analysis(p, pid, {}),
                "previz.plan_layouts": lambda: previz.plan_layouts(p, pid, None, _TMP),
                "qc_agent.review_scene": lambda: qc_agent.review_scene(p, pid, 1, None, _TMP),
                "costume.make_character_set": lambda: costume.make_character_set(p, pid, "Mới", None, _TMP),
                "editor_review.run": lambda: editor_review.run(p, pid, None, _TMP),
                "editor_apply.apply": lambda: editor_apply.apply(p, pid, _TMP, []),
                "experiments.kling_multishot": lambda: experiments.kling_multishot(p, pid, 1, None, _TMP),
                "claude_tasks._run (cả nhóm)": lambda: claude_tasks._run(p, pid, "director", "x", None, None),
                # hàm nhận conn/provider: dashboard truyền p=p (autopilot / hệ thống không truyền → như cũ)
                "voice.generate(p=p)": lambda: voice.generate(p.conn, pid, None, _TMP, p=p),
                "voice_check.redo(p=p)": lambda: voice_check.redo(p.conn, pid, None, _TMP, p=p),
                "model_router.set_override(p=p)": lambda: model_router.set_override(p.conn, sid, None, p=p),
                "project_budget.set_target(p=p)": lambda: project_budget.set_target(p.conn, pid, 5.0, p=p),
                "project_budget.raise_cap(p=p)": lambda: project_budget.raise_cap(p.conn, pid, "image", 1.0, "x", "lý do", p=p),
                "music.submit_drafts(p=p)": lambda: music.submit_drafts(None, _TMP, "x", None, True, p=p, project_id=pid),
                "audio_lib.submit_sfx(p=p)": lambda: audio_lib.submit_sfx(None, _TMP, "x", p=p, project_id=pid),
                "audio_lib.submit_tts(p=p)": lambda: audio_lib.submit_tts(None, _TMP, "x", 1, p=p, project_id=pid),
            },
            "view": {"compare.clone_project (nhân bản)": lambda: compare.clone_project(p, pid, "bản sao")},
            "manage": {
                "archive.archive (cất)": lambda: archive.archive(p, pid),
                "archive.restore": lambda: archive.restore(p, pid),
                "delete_project (xóa)": lambda: p.delete_project(pid),
            },
        }

    def test_every_entry_point_for_every_role(self):
        for role in ROLES:
            for need in ("edit", "view", "manage"):
                conn, pid, sid, jid = make_world()                      # fresh world: a delete / archive must not break the next case
                p = as_user(conn, role)
                for name, fn in self.entry_points(p, pid, sid, jid)[need].items():
                    # each call on its own fresh world so one allowed call cannot hide a later one
                    conn, pid, sid, jid = make_world()
                    p = as_user(conn, role)
                    fn = self.entry_points(p, pid, sid, jid)[need][name]
                    got = outcome(fn)
                    self.assertEqual(got == "ok", CAN[need][role], f"{role} · {need} · {name} -> {got}")

    def test_the_refusal_is_clear_vietnamese_never_silent(self):
        conn, pid, sid, jid = make_world()
        with self.assertRaises(AccessDenied) as e:
            as_user(conn, "stranger").set_paused(pid, True)
        self.assertIn("không có quyền", str(e.exception))
        self.assertIn("chu@garena.vn", str(e.exception))                    # says whose project it is
        self.assertIn("theo dõi", str(e.exception))                         # and how to get access
        with self.assertRaises(AccessDenied) as e:
            as_user(conn, "watch_view").approve(jid)
        self.assertIn("XEM", str(e.exception))
        self.assertIn("chỉ xem", str(e.exception))
        self.assertIn("duyệt", str(e.exception))                            # names the refused action
        with self.assertRaises(AccessDenied) as e:
            as_user(conn, "watch_edit").delete_project(pid)
        self.assertIn("Owner hoặc chủ dự án", str(e.exception))
        for role in ("stranger", "watch_view"):                             # nothing was written
            self.assertEqual(conn.execute("SELECT state FROM jobs WHERE id=?", (jid,)).fetchone()[0], "pending_review")
            self.assertEqual(conn.execute("SELECT paused FROM projects WHERE id=?", (pid,)).fetchone()[0], 0, role)

    def test_a_refused_job_is_not_created(self):
        conn, pid, sid, jid = make_world()
        n = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        for role in ("stranger", "watch_view"):
            with self.assertRaises(AccessDenied):
                as_user(conn, role).create_job(sid, "video_gen")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], n)

    def test_allowed_people_really_do_the_work(self):
        for role in ("owner", "creator", "watch_edit"):
            conn, pid, sid, jid = make_world()
            p = as_user(conn, role)
            p.approve(jid)
            self.assertEqual(conn.execute("SELECT state FROM jobs WHERE id=?", (jid,)).fetchone()[0], "approved", role)
            new = p.create_job(sid, "video_gen")
            self.assertEqual(conn.execute("SELECT created_by FROM jobs WHERE id=?", (new,)).fetchone()[0], WHO[role]["email"])  # job keeps its sender
            p.set_paused(pid, True)
            self.assertEqual(conn.execute("SELECT paused FROM projects WHERE id=?", (pid,)).fetchone()[0], 1)

    def test_only_manage_people_can_archive_and_restore(self):
        for role, ok in (("owner", True), ("creator", True), ("watch_edit", False), ("watch_view", False), ("stranger", False)):
            conn, pid, sid, jid = make_world()
            p = as_user(conn, role)
            if ok:
                archive.archive(p, pid)
                self.assertEqual(conn.execute("SELECT archived FROM projects WHERE id=?", (pid,)).fetchone()[0], 1)
                archive.restore(p, pid)
                self.assertEqual(conn.execute("SELECT archived FROM projects WHERE id=?", (pid,)).fetchone()[0], 0)
            else:
                with self.assertRaises(AccessDenied):
                    archive.archive(p, pid)
                self.assertEqual(conn.execute("SELECT archived FROM projects WHERE id=?", (pid,)).fetchone()[0], 0, role)

    def test_a_member_cannot_create_a_project_in_someone_elses_name(self):
        conn, *_ = make_world()
        p = as_user(conn, "creator")
        with self.assertRaises(AccessDenied):
            p.create_project("giả danh", created_by=WEDIT)
        with self.assertRaises(AccessDenied):
            p.create_project("không tên chủ")
        mine = p.create_project("của tôi", created_by=CREATOR)
        self.assertEqual(access.level(conn, mine, WHO["creator"]), "own")
        as_user(conn, "owner").create_project("owner làm hộ", created_by=WEDIT)       # the Owner may

    def test_clone_belongs_to_the_person_who_clones(self):
        conn, pid, sid, jid = make_world()
        new = compare.clone_project(as_user(conn, "watch_view"), pid, "bản của người xem")
        self.assertEqual(conn.execute("SELECT created_by FROM projects WHERE id=?", (new,)).fetchone()[0], WVIEW)
        self.assertEqual(access.level(conn, new, WHO["watch_view"]), "own")


class WatcherTests(unittest.TestCase):
    def setUp(self):
        self.conn, self.pid, self.sid, self.jid = make_world()

    def test_owner_and_creator_manage_watchers_others_do_not(self):
        extra = "them@garena.vn"
        auth.add_user(self.conn, owner_identity(), extra, [])
        for role in ("watch_edit", "watch_view", "stranger"):
            with self.assertRaises(AccessDenied):
                access.set_watcher(self.conn, WHO[role], self.pid, extra, "view")
            with self.assertRaises(AccessDenied):
                access.remove_watcher(self.conn, WHO[role], self.pid, WVIEW)
        access.set_watcher(self.conn, WHO["creator"], self.pid, extra, "view")
        access.set_watcher(self.conn, WHO["owner"], self.pid, extra, "edit")            # change the level
        self.assertEqual({w["email"]: w["level"] for w in access.list_watchers(self.conn, self.pid)},
                         {WVIEW: "view", WEDIT: "edit", extra: "edit"})
        access.remove_watcher(self.conn, WHO["owner"], self.pid, extra)
        self.assertEqual(access.level(self.conn, self.pid, {"email": extra, "role": "member"}), None)

    def test_a_level_change_applies_at_once(self):
        self.assertEqual(outcome(lambda: as_user(self.conn, "watch_view").approve(self.jid)), "denied")
        access.set_watcher(self.conn, WHO["owner"], self.pid, WVIEW, "edit")
        self.assertEqual(outcome(lambda: as_user(self.conn, "watch_view").approve(self.jid)), "ok")
        access.remove_watcher(self.conn, WHO["owner"], self.pid, WVIEW)
        self.assertEqual(outcome(lambda: as_user(self.conn, "watch_view").set_paused(self.pid, True)), "denied")
        self.assertFalse(access.can_view(self.conn, self.pid, WHO["watch_view"]))

    def test_refusals_are_explained(self):
        for who, text in ((OWNER, "Owner"), (CREATOR, "người tạo"), ("ghost@garena.vn", "chưa có tài khoản"), ("không-phải-mail", "E-mail")):
            with self.assertRaises(AccessDenied) as e:
                access.set_watcher(self.conn, WHO["owner"], self.pid, who, "view")
            self.assertIn(text, str(e.exception), who)
        with self.assertRaises(AccessDenied):
            access.set_watcher(self.conn, WHO["owner"], self.pid, STRANGER, "admin")
        auth.set_user(self.conn, owner_identity(), STRANGER, [], False)
        with self.assertRaises(AccessDenied) as e:
            access.set_watcher(self.conn, WHO["owner"], self.pid, STRANGER, "view")
        self.assertIn("chưa có tài khoản đang hoạt động", str(e.exception))

    def test_changes_are_in_the_audit_log(self):
        access.remove_watcher(self.conn, WHO["owner"], self.pid, WVIEW)
        log = " ".join(f"{r['action']} {r['detail']}" for r in auth.recent_audit(self.conn, 20))
        self.assertIn("watch_set", log)
        self.assertIn("watch_remove", log)
        self.assertIn(WVIEW, log)


class LegacyProjectTests(unittest.TestCase):
    """A project with no recorded creator (an older one): only the Owner sees it until the Owner gives it an owner."""

    def setUp(self):
        self.conn, self.pid, self.sid, self.jid = make_world()
        self.conn.execute("UPDATE projects SET created_by=NULL WHERE id=?", (self.pid,))
        self.conn.execute("DELETE FROM project_watchers")
        self.conn.commit()

    def test_only_the_owner_sees_it(self):
        for role in ROLES:
            self.assertEqual(access.can_view(self.conn, self.pid, WHO[role]), role == "owner", role)
        self.assertEqual([o["id"] for o in access.orphans(self.conn)], [self.pid])
        self.assertEqual([r["id"] for r in archive.active_projects(self.conn, WHO["creator"])], [])
        self.assertEqual([r["id"] for r in archive.active_projects(self.conn, WHO["owner"])], [self.pid])

    def test_assigning_a_creator_hands_it_over(self):
        for role in ("creator", "watch_edit"):
            with self.assertRaises(AccessDenied):
                access.assign_creator(self.conn, WHO[role], self.pid, CREATOR)
        with self.assertRaises(AccessDenied):
            access.assign_creator(self.conn, WHO["owner"], self.pid, "ghost@garena.vn")
        access.assign_creator(self.conn, WHO["owner"], self.pid, CREATOR)
        self.assertEqual(access.level(self.conn, self.pid, WHO["creator"]), "own")
        self.assertFalse(access.can_view(self.conn, self.pid, WHO["stranger"]))
        self.assertEqual(access.orphans(self.conn), [])

    def test_a_watcher_can_be_added_by_the_owner_on_a_legacy_project(self):
        access.set_watcher(self.conn, WHO["owner"], self.pid, WVIEW, "view")
        self.assertTrue(access.can_view(self.conn, self.pid, WHO["watch_view"]))
        self.assertFalse(access.can_edit(self.conn, self.pid, WHO["watch_view"]))


class ListsFollowRights(unittest.TestCase):
    def setUp(self):
        self.conn, self.pid, self.sid, self.jid = make_world()
        self.other = Pipeline(self.conn).create_project("dự án của người lạ", created_by=STRANGER)
        osid = Pipeline(self.conn).create_scene(self.other, 1, "c")
        ojid = Pipeline(self.conn).create_job(osid, "image_gen")
        self.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (ojid,))
        self.conn.commit()

    def test_project_picker_per_role(self):
        want = {"owner": [self.pid, self.other], "creator": [self.pid], "watch_edit": [self.pid], "watch_view": [self.pid],
                "stranger": [self.other]}
        for role, ids in want.items():
            self.assertEqual([r["id"] for r in archive.active_projects(self.conn, WHO[role])], ids, role)

    def test_archived_list_follows_rights_too(self):
        archive.archive(as_user(self.conn, "creator"), self.pid)
        self.assertEqual([r["id"] for r in archive.archived_projects(self.conn, WHO["watch_view"])], [self.pid])
        self.assertEqual(archive.archived_projects(self.conn, WHO["stranger"]), [])

    def test_inbox_per_role(self):
        def ids(role, team_wide=False):
            is_owner = role == "owner"
            got = inbox.items(self.conn, WHO[role]["email"], is_owner=is_owner, can_money=False, auth_on=True, team_wide=team_wide)
            return {i["project_id"] for i in got if i["project_id"]}
        self.assertEqual(ids("owner"), set())                          # the Owner's "mine" = own + legacy: none here
        self.assertEqual(ids("owner", True), {self.pid, self.other})
        self.assertEqual(ids("creator"), {self.pid})
        self.assertEqual(ids("watch_edit"), {self.pid})                # can act on it
        self.assertEqual(ids("watch_view"), set())                     # nothing there is theirs to do
        self.assertEqual(ids("stranger"), {self.other})
        self.assertEqual(ids("stranger", True), {self.other})          # team_wide widens nothing for a member
        self.assertEqual(ids("watch_view", True), set())
        item = next(i for i in inbox.items(self.conn, WEDIT, is_owner=False, can_money=False, auth_on=True) if i["project_id"] == self.pid)
        self.assertEqual(item["who"], CREATOR)                         # shows whose project it is

    def test_sign_in_off_nothing_changes(self):
        got = inbox.items(self.conn, "", auth_on=False)
        self.assertEqual({i["project_id"] for i in got}, {self.pid, self.other})
        self.assertEqual(len(archive.active_projects(self.conn)), 2)


class MigrationTests(unittest.TestCase):
    def test_an_older_database_gets_the_table_and_loses_nothing(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "old.sqlite")
        conn, pid, sid, jid = make_world(connect(path))
        conn.execute("DROP TABLE project_watchers")                    # what a database from before this change looks like
        conn.commit()
        conn.close()
        again = connect(path)                                          # migration is idempotent and runs on connect
        self.assertEqual(again.execute("SELECT name FROM projects WHERE id=?", (pid,)).fetchone()[0], "dự án của chủ")
        self.assertEqual(again.execute("SELECT state FROM jobs WHERE id=?", (jid,)).fetchone()[0], "pending_review")
        self.assertEqual(access.list_watchers(again, pid), [])
        access.set_watcher(again, WHO["owner"], pid, WVIEW, "view")
        again.close()
        third = connect(path)                                          # a second migration keeps the watcher
        self.assertEqual([w["email"] for w in access.list_watchers(third, pid)], [WVIEW])
        self.assertEqual(third.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_the_level_column_only_accepts_the_two_levels(self):
        conn, pid, *_ = make_world()
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO project_watchers (project_id, email, level, added_at) VALUES (?,?,?,?)", (pid, "x@y.vn", "root", "now"))


class ManagerRightsTests(unittest.TestCase):
    def test_starting_the_background_run_needs_the_edit_right(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "m.sqlite")
        conn, pid, *_ = make_world(connect(path))
        conn.commit()
        mgr = autopilot.Manager(path, tmp, poll_sec=999)
        for role in ("watch_view", "stranger"):
            with self.assertRaises(AccessDenied):
                mgr.start(pid, user=WHO[role])
            with self.assertRaises(AccessDenied):
                mgr.wake(pid, user=WHO[role])
        self.assertFalse(mgr.alive(pid))


if __name__ == "__main__":
    unittest.main()
