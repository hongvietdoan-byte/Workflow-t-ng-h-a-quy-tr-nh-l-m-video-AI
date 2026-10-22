"""C-M48-DESK-CORE (M4.8 Đợt 1): tầng lõi bàn đạo diễn 3D core/stage_desk.py + stage_auto.apply(who) / run(manual). Test theo kế hoạch
docs/KE_HOACH_BAN_DAO_DIEN_3D_DASHBOARD_2026-10-21.md mục 10 (1–10, 12–13). Không gọi API, Blender giả (khung tests/test_stage_auto), CSDL
TỆP tạm (luồng nền mở kết nối riêng)."""
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from unittest import mock

from core import autopilot, stage_auto, stage_desk as D, write_guard
from core.db import connect as _real_connect
from tests import test_location_pack as _tlp
from tests.test_stage_auto import Base
from tests.test_stage_crew import CREW_ON, blocking, review, specs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EP = None                                                    # đăng nhập TẮT = chủ máy (Executive Producer)
HUMAN = write_guard.actor("human", "ep@x")
OK_REVIEW = review(*[{"shot": n, "ket_luan": "khop"} for n in (1, 2, 3)])


class DeskBase(Base):
    def setUp(self):
        self._dbdir = tempfile.mkdtemp()
        db = os.path.join(self._dbdir, "m.sqlite")
        p = mock.patch.object(_tlp, "connect", lambda *a, **k: _real_connect(db))
        p.start()
        self.addCleanup(p.stop)
        super().setUp()
        env = mock.patch.dict(os.environ, dict(CREW_ON, PLATES3D_LOCK=os.path.join(self._dbdir, "blender.lock")))
        env.start()
        self.addCleanup(env.stop)
        tool = stage_auto.tool()
        for name, fn in (("top_cut", lambda rd, log=print: None), ("draw_beats", lambda rd: None),
                         ("stage_sheet", lambda rd, title, out: (open(out, "wb").write(b"png"), out)[1])):
            patch = mock.patch.object(tool, name, side_effect=fn, create=True)
            patch.start()
            self.addCleanup(patch.stop)
        self.pid = self.project()
        self.seg = stage_auto.segments(self.p.conn, self.pid)[0]

    def tearDown(self):
        D.wait(self.pid, 30)
        super().tearDown()

    def answer(self, *objs):
        for obj in objs:
            r = stage_auto.crew_answer(self.p.conn, self.pid, self.seg, self.data, obj)
            self.assertTrue(r["ok"], r)

    def to_duyet(self):
        self.answer(blocking(), specs(), OK_REVIEW)

    def scenes_sha(self):
        rows = self.p.conn.execute("SELECT id, data FROM scenes WHERE project_id=? ORDER BY id", (self.pid,)).fetchall()
        return hashlib.sha1(json.dumps([tuple(r) for r in rows]).encode()).hexdigest()

    def st(self):
        return D.scene_status(self.p.conn, self.pid, self.data, "1")

    def same(self, a, b, twin):
        """So hai bản ghi của hai dự án sinh đôi: chỉ khác id dự án trong đường dẫn ảnh + vân tay đầu vào (có tên dự án)."""
        import re

        def norm(v, pid):
            text = json.dumps(v, sort_keys=True, ensure_ascii=False)
            text = text.replace(os.sep + "projects" + os.sep + str(pid) + os.sep, "/P/").replace("/projects/" + str(pid) + "/", "/P/")
            return re.sub(r'"inputs_fp": "[0-9a-f]+"', '"inputs_fp": "-"', text)
        self.assertEqual(norm(a, self.pid), norm(b, twin))

    def crew_state(self):
        with open(os.path.join(D.seg_dir(self.data, self.pid, self.seg), "crew", "state.json"), encoding="utf-8") as f:
            return json.load(f)

    def bg(self, r):
        self.assertTrue(r.get("ok"), r)
        self.assertTrue(D.wait(self.pid, 30))
        return D.progress(self.data, self.pid, "1", self.p.conn)


# ---- 1 / 8: không thêm cờ UI, không đụng os.environ, run(manual) -----------------------------------------------------------
class FlagsAndEnvTests(DeskBase):
    def test_core_never_sets_feature_env_and_has_no_streamlit(self):
        src = open(os.path.join(ROOT, "core", "stage_desk.py"), encoding="utf-8").read()
        self.assertNotIn('os.environ["FEATURE_', src)
        self.assertNotIn("os.environ['FEATURE_", src)
        self.assertNotIn("import streamlit", src)

    def test_run_manual_runs_with_flag_off_and_leaves_it_off(self):
        from core import features
        from tests.test_stage_auto import FakeClaude
        client = FakeClaude(blocking(), specs(), OK_REVIEW)
        with mock.patch.dict(os.environ, {"FEATURE_STAGE_AUTO": "0"}):
            self.assertIsNone(stage_auto.run(self.p.conn, self.pid, self.data, client=client))      # autopilot: cờ tắt → không làm gì
            r = stage_auto.run(self.p.conn, self.pid, self.data, client=client, manual=True)
            self.assertIsNotNone(r)
            self.assertEqual(len(client.prompts), 3)
            self.assertFalse(features.on("stage_auto"))
            self.assertEqual(os.environ.get("FEATURE_STAGE_AUTO"), "0")


# ---- 2: nút theo phase ------------------------------------------------------------------------------------------------------
class ButtonsTests(DeskBase):
    def test_buttons_follow_the_phase(self):
        self.assertEqual(self.st()["phase"], None)
        self.assertNotIn("N6", self.st()["buttons"])
        self.answer(blocking())
        self.assertIn("N4", self.st()["buttons"])
        self.assertNotIn("N6", self.st()["buttons"])
        self.answer(specs(), OK_REVIEW)
        st = self.st()
        self.assertEqual(st["phase"], "duyet")
        self.assertTrue({"N6", "N7"} <= set(st["buttons"]))

    def test_changed_inputs_leave_only_reset(self):
        self.to_duyet()
        state = self.crew_state()
        state["fp"] = "khac"
        with open(os.path.join(D.seg_dir(self.data, self.pid, self.seg), "crew", "state.json"), "w", encoding="utf-8") as f:
            json.dump(state, f)
        st = self.st()
        self.assertTrue(st["inputs_changed"])
        self.assertEqual(set(st["buttons"]) - {"N1", "N2"}, {"N8"})

    def test_user_approve_flag_off_hides_approve(self):
        self.to_duyet()
        with mock.patch.dict(os.environ, {"FEATURE_STAGE_CREW_USER_APPROVE": "0"}):
            self.assertNotIn("N6", self.st()["buttons"])

    def test_status_never_runs_blender(self):
        tool = stage_auto.tool()
        with mock.patch.object(tool, "k1_run", side_effect=AssertionError("K1 khi vẽ trạng thái")):
            st = D.status(self.p.conn, self.pid, self.data)
        self.assertEqual(st[0]["k1"], False)


# ---- 3: N6 duyệt (S-B) ------------------------------------------------------------------------------------------------------
class ApproveTests(DeskBase):
    def test_only_a_human_executive_producer_approves(self):
        self.to_duyet()
        r = D.approve(self.p.conn, self.pid, self.data, "1", write_guard.actor("ai", "director"), EP)
        self.assertFalse(r["ok"])
        self.assertIn("S-B", r["errors"][0])
        r = D.approve(self.p.conn, self.pid, self.data, "1", HUMAN, {"email": "ban@x", "role": "member"})
        self.assertFalse(r["ok"])
        self.assertIn("Executive Producer", r["errors"][0])
        self.assertNotIn("stage_camera", self.shot(self.pid, 1))
        self.assertEqual(self.crew_state()["phase"], "duyet")

    def test_approve_writes_cameras_as_the_person_and_keeps_user_locked(self):
        self.to_duyet()
        d = self.shot(self.pid, 2)
        d.update(stage_camera={"tay": True}, _user_locked=["stage_camera"])
        self.p.conn.execute("UPDATE scenes SET data=? WHERE project_id=? AND idx=2", (json.dumps(d), self.pid))
        self.p.conn.commit()
        r = D.approve(self.p.conn, self.pid, self.data, "1", HUMAN, EP)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["applied"], [1, 3])
        self.assertIn("nguoi_dung", self.shot(self.pid, 1)["stage_camera"]["source"])
        self.assertEqual(self.shot(self.pid, 2)["stage_camera"], {"tay": True})            # khóa tay giữ nguyên
        self.assertEqual(self.crew_state()["approved_by"], "nguoi_dung")

    def test_drawn_shot_needs_confirmation(self):
        self.to_duyet()
        sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=1", (self.pid,)).fetchone()[0]
        job = self.p.create_job(sid)
        self.p.conn.execute("UPDATE jobs SET result_path='x.png' WHERE id=?", (job,))
        self.p.conn.commit()
        sha = self.scenes_sha()
        r = D.approve(self.p.conn, self.pid, self.data, "1", HUMAN, EP)
        self.assertFalse(r["ok"])
        self.assertEqual(r["needs_confirm"], [1])
        self.assertEqual(self.scenes_sha(), sha)
        r = D.approve(self.p.conn, self.pid, self.data, "1", HUMAN, EP, confirm_drawn=True)
        self.assertTrue(r["ok"], r)


# ---- 4: N7 trả lại ----------------------------------------------------------------------------------------------------------
class ReturnTests(DeskBase):
    def test_return_needs_intent_and_never_touches_the_database(self):
        self.to_duyet()
        sha = self.scenes_sha()
        r = D.return_(self.p.conn, self.pid, self.data, "1", [{"shot": 2, "y_do": " "}], HUMAN, EP)
        self.assertFalse(r["ok"])
        self.assertEqual(self.crew_state()["phase"], "duyet")
        for i in range(3):
            r = D.return_(self.p.conn, self.pid, self.data, "1", [{"shot": 2, "y_do": f"Kelly lùi {i + 1} m"}], HUMAN, EP)
            self.assertTrue(r["ok"], r)
            self.assertEqual(self.scenes_sha(), sha)
            self.answer(OK_REVIEW)
        self.assertEqual(self.crew_state()["phase"], "duyet")

    def test_return_is_executive_producer_only(self):
        self.to_duyet()
        r = D.return_(self.p.conn, self.pid, self.data, "1", [{"shot": 2, "y_do": "lùi"}], write_guard.actor("tool", "x"), EP)
        self.assertFalse(r["ok"])


# ---- 5: N4 nạp câu trả lời --------------------------------------------------------------------------------------------------
class LoadAnswerTests(DeskBase):
    def test_bad_answer_keeps_state(self):
        pr = self.bg(D.load_answer(self.p.conn, self.pid, self.data, "1", specs(), HUMAN))        # sai vai: đang chờ Đạo diễn
        self.assertEqual(pr["state"], "error")
        self.assertTrue(pr["error"])
        self.assertEqual(stage_auto.crew_prompt(self.p.conn, self.pid, self.seg, self.data)[2]["phase"], "dao_dien")

    def test_good_answer_moves_on(self):
        pr = self.bg(D.load_answer(self.p.conn, self.pid, self.data, "1", blocking(), HUMAN))
        self.assertEqual(pr["state"], "done", pr)
        self.assertEqual(self.crew_state()["phase"], "quay_phim")
        self.assertTrue(pr["log"])

    def test_desk_never_takes_a_user_verdict(self):
        self.to_duyet()
        r = D.load_answer(self.p.conn, self.pid, self.data, "1", {"duyet": True}, HUMAN)
        self.assertFalse(r["ok"])
        self.assertIn("S-B", r["errors"][0])
        pr = self.bg(D.load_answer(self.p.conn, self.pid, self.data, "1", OK_REVIEW, HUMAN))
        self.assertEqual(pr["state"], "error")                                                  # phase duyet: crew_answer từ chối
        self.assertEqual(self.crew_state()["phase"], "duyet")
        self.assertNotIn("stage_camera", self.shot(self.pid, 1))

    def test_measure_error_keeps_state(self):
        self.answer(blocking())
        before = self.crew_state()
        tool = stage_auto.tool()
        with mock.patch.object(tool, "v2_run", side_effect=RuntimeError("Blender chết")):
            pr = self.bg(D.load_answer(self.p.conn, self.pid, self.data, "1", specs(), HUMAN))
        self.assertEqual(pr["state"], "error")
        self.assertIn("không đo được", pr["error"])
        self.assertEqual(self.crew_state()["phase"], before["phase"])


# ---- 6: không ghi CSDL trước duyệt --------------------------------------------------------------------------------------------
class NoWriteBeforeApprovalTests(DeskBase):
    def test_every_non_approval_button_leaves_scenes_untouched(self):
        sha = self.scenes_sha()
        self.bg(D.check_inputs(self.p.conn, self.pid, self.data, "1", HUMAN))
        self.assertTrue(D.write_prompt(self.p.conn, self.pid, self.data, "1", HUMAN)["ok"])
        self.bg(D.load_answer(self.p.conn, self.pid, self.data, "1", blocking(), HUMAN))
        self.bg(D.load_answer(self.p.conn, self.pid, self.data, "1", specs(), HUMAN))
        self.bg(D.build_sheet(self.p.conn, self.pid, self.data, "1", HUMAN))
        self.assertTrue(D.score(self.p.conn, self.pid, self.data, "1")["ok"])
        self.answer(OK_REVIEW)
        self.assertTrue(D.return_(self.p.conn, self.pid, self.data, "1", [{"shot": 1, "y_do": "xa hơn"}], HUMAN, EP)["ok"])
        self.assertTrue(D.reset(self.p.conn, self.pid, self.data, "1", HUMAN, confirm=True)["ok"])
        self.assertEqual(self.scenes_sha(), sha)

    def test_prompt_lands_in_the_segment_folder(self):
        r = D.write_prompt(self.p.conn, self.pid, self.data, "1", HUMAN)
        self.assertTrue(r["path"].endswith(os.path.join("crew", "de_bai_dao_dien.md")))
        self.assertIn("Bạn là **Đạo diễn**", open(r["path"], encoding="utf-8").read())


# ---- 7: khóa S ----------------------------------------------------------------------------------------------------------------
class LockTests(DeskBase):
    def test_one_background_thread_per_project(self):
        import threading
        gate = threading.Event()
        tool = stage_auto.tool()
        orig = tool.k1_run

        def slow(*a, **k):
            gate.wait(10)
            return orig(*a, **k)
        with mock.patch.object(tool, "k1_run", side_effect=slow):
            first = D.check_inputs(self.p.conn, self.pid, self.data, "1", HUMAN)
            second = D.check_inputs(self.p.conn, self.pid, self.data, "1", HUMAN)
            sync = D.write_prompt(self.p.conn, self.pid, self.data, "1", HUMAN)
            self.assertTrue(first["ok"])
            self.assertFalse(second["ok"])
            self.assertIn("đang chạy", second["errors"][0])
            self.assertFalse(sync["ok"])
            gate.set()
            self.assertTrue(D.wait(self.pid, 30))

    def _hold_lock(self, pid_proc=None):
        path = os.path.join(D.seg_dir(self.data, self.pid, self.seg), D.LOCK_FILE)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"pid": pid_proc or os.getpid(), "owner": "human:ep@x", "action": "N4", "since_ts": __import__("time").time(),
                       "since": "bây giờ"}, f)
        return path

    def test_autopilot_waits_with_a_sentence(self):
        self._hold_lock()
        with self.assertRaises(autopilot._Wait) as e:
            autopilot._stage_phase(self.p, self.pid, mock.Mock(data_dir=self.data, llm=None))
        self.assertIn("đang thao tác sân khấu", str(e.exception))

    def test_dead_process_lock_is_removed_and_said(self):
        path = self._hold_lock(pid_proc=2 ** 22 + 12345)
        with mock.patch.object(D, "_pid_alive", return_value=False):
            self.assertIsNone(D.lock_holder(self.data, self.pid, "1", self.p.conn))
        self.assertFalse(os.path.exists(path))
        said = self.p.conn.execute("SELECT message FROM diag_events WHERE code=?", (D.CODE,)).fetchall()
        self.assertTrue(any("gỡ khóa" in r[0] for r in said))

    def test_cli_refuses_a_locked_segment(self):
        self._hold_lock()
        db = self.p.conn.execute("PRAGMA database_list").fetchone()[2]
        env = dict(os.environ, PYTHONUTF8="1", PIPELINE_DATA=self.data, FEATURE_STAGE_CAMERA="1", FEATURE_PLACE_RENDER_REFS="1")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "stage_auto.py"), "--db", db, "--project", str(self.pid),
                            "--scene", "1", "--crew", "--crew-approve", "--data-dir", self.data], capture_output=True, text=True,
                           env=env, cwd=ROOT, timeout=120)
        self.assertIn("đang thao tác sân khấu", r.stdout + r.stderr)
        self.assertEqual(self.crew_state_or_none(), None)

    def crew_state_or_none(self):
        try:
            return self.crew_state()
        except OSError:
            return None


# ---- 9: write guard ---------------------------------------------------------------------------------------------------------
class GuardTests(DeskBase):
    def field_diags(self):
        return [r[0] for r in self.p.conn.execute("SELECT code FROM diag_events WHERE code IN ('field_conflict','field_review',"
                                                  "'stale_write')").fetchall()]

    def test_guard_on_human_approval_is_silent_auto_overwrite_is_reported(self):
        self.to_duyet()
        with mock.patch.dict(os.environ, {"FEATURE_FIELD_GUARD": "1"}):
            self.assertTrue(D.approve(self.p.conn, self.pid, self.data, "1", HUMAN, EP)["ok"])
            self.assertEqual(self.field_diags(), [])
            cams = {1: {"auto": True, "khac": 1}}
            stage_auto.apply(self.p.conn, self.seg, cams, who=write_guard.actor("auto", "autopilot.stage"))
            self.assertIn("field_review", self.field_diags())

    def test_stale_expected_rev_is_reported(self):
        self.to_duyet()
        with mock.patch.dict(os.environ, {"FEATURE_FIELD_GUARD": "1"}):
            r = D.approve(self.p.conn, self.pid, self.data, "1", HUMAN, EP, expected_revs={1: 99})
            self.assertTrue(r["ok"], r)
            self.assertIn("stale_write", self.field_diags())

    def test_guard_off_writes_exactly_like_before(self):
        self.to_duyet()
        twin = self.project()
        seg2 = stage_auto.segments(self.p.conn, twin)[0]
        for obj in (blocking(), specs(), OK_REVIEW):
            stage_auto.crew_answer(self.p.conn, twin, seg2, self.data, obj)
        stage_auto.crew_user_verdict(self.p.conn, twin, seg2, self.data, approve=True)          # đường cũ (CLI), không who
        self.assertTrue(D.approve(self.p.conn, self.pid, self.data, "1", HUMAN, EP)["ok"])
        for i in (1, 2, 3):
            self.same(self.shot(self.pid, i), self.shot(twin, i), twin)
        self.assertEqual(self.field_diags(), [])


# ---- 10: tiến độ ------------------------------------------------------------------------------------------------------------
class ProgressTests(DeskBase):
    def test_progress_has_steps_and_errors_are_said(self):
        pr = self.bg(D.check_inputs(self.p.conn, self.pid, self.data, "1", HUMAN))
        self.assertEqual(pr["state"], "done")
        self.assertTrue(pr["log"])
        tool = stage_auto.tool()
        with mock.patch.object(stage_auto, "k1_cached", return_value=None), \
                mock.patch.object(stage_auto, "ensure_k1_seg", side_effect=ValueError("không tìm thấy Blender")):
            pr = self.bg(D.check_inputs(self.p.conn, self.pid, self.data, "1", HUMAN))
        self.assertEqual(pr["state"], "error")
        self.assertIn("không tìm thấy Blender", pr["error"])
        self.assertTrue(tool)

    def test_interrupted_task_is_said(self):
        path = os.path.join(D.seg_dir(self.data, self.pid, self.seg), D.PROGRESS_FILE)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"action": "N4", "state": "running", "process": os.getpid(), "thread": "stage_desk_x|N4", "started": "lúc nãy",
                       "log": []}, f)
        pr = D.progress(self.data, self.pid, "1", self.p.conn)
        self.assertEqual(pr["state"], "interrupted")
        self.assertIn("bị ngắt", pr["error"])

    def test_in_memory_database_is_refused(self):
        from core.db import connect
        from core.pipeline import Pipeline
        mem = Pipeline(connect())
        with mock.patch.object(D, "segment", return_value=self.seg):
            r = D.check_inputs(mem.conn, self.pid, self.data, "1", HUMAN)
        self.assertFalse(r["ok"])
        self.assertIn("bộ nhớ", r["errors"][0])


# ---- 12: đường dẫn ----------------------------------------------------------------------------------------------------------
class PathTests(DeskBase):
    def test_sheet_lands_in_the_segment_beats_folder_whatever_the_cwd(self):
        self.answer(blocking(), specs())
        old = os.getcwd()
        os.chdir(tempfile.mkdtemp())
        try:
            pr = self.bg(D.build_sheet(self.p.conn, self.pid, self.data, "1", HUMAN))
        finally:
            os.chdir(old)
        self.assertEqual(pr["state"], "done", pr)
        want = os.path.join(D.seg_dir(self.data, self.pid, self.seg), "beats", "san_khau_canh1.png")
        self.assertTrue(os.path.isabs(pr["result"]["path"]))
        self.assertEqual(os.path.normpath(pr["result"]["path"]), os.path.normpath(want))
        self.assertEqual(self.st()["sheet"], want)


# ---- 13: ma trận CLI ↔ nút ----------------------------------------------------------------------------------------------------
class MatrixTests(DeskBase):
    def test_cli_approve_and_desk_approve_give_the_same_result(self):
        twin = self.project()
        seg2 = stage_auto.segments(self.p.conn, twin)[0]
        for pid, seg in ((self.pid, self.seg), (twin, seg2)):
            for obj in (blocking(), specs(), OK_REVIEW):
                self.assertTrue(stage_auto.crew_answer(self.p.conn, pid, seg, self.data, obj)["ok"])
        stage_auto.crew_user_verdict(self.p.conn, twin, seg2, self.data, approve=True)            # = --crew-approve
        self.assertTrue(D.approve(self.p.conn, self.pid, self.data, "1", HUMAN, EP)["ok"])

        def result(pid, seg):
            with open(os.path.join(D.seg_dir(self.data, pid, seg), "result.json"), encoding="utf-8") as f:
                r = json.load(f)
            return {k: v for k, v in r.items() if k not in ("fp",)}
        a, b = result(self.pid, self.seg), result(twin, seg2)
        self.same(a["cams"], b["cams"], twin)
        self.assertEqual(a["bad"], b["bad"])
        self.assertEqual(a["crew"]["approved_by"], b["crew"]["approved_by"])
        for i in (1, 2, 3):
            self.same(self.shot(self.pid, i)["stage_camera"], self.shot(twin, i)["stage_camera"], twin)


# ---- S-C / S-D ----------------------------------------------------------------------------------------------------------------
class PolicyTests(DeskBase):
    def sid(self, idx):
        return self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (self.pid, idx)).fetchone()[0]

    def test_paid_gate_warns_by_default_and_holds_required_unapproved_plates(self):
        self.answer(blocking())
        g = D.paid_gate(self.p.conn, self.pid, self.data, [self.sid(1), self.sid(2)])
        self.assertEqual({x["level"] for x in g}, {"warn"})                                    # mặc định VÀNG
        self.assertFalse(D.require_plate(self.p.conn, self.pid, self.data, self.sid(1), True, write_guard.actor("ai", "d"), EP)["ok"])
        self.assertTrue(D.require_plate(self.p.conn, self.pid, self.data, self.sid(1), True, HUMAN, EP)["ok"])
        g = {x["idx"]: x for x in D.paid_gate(self.p.conn, self.pid, self.data, [self.sid(1), self.sid(2)])}
        self.assertEqual((g[1]["level"], g[2]["level"]), ("hold", "warn"))
        self.assertFalse(D.allow_exception(self.p.conn, self.pid, self.data, self.sid(1), "", HUMAN, EP)["ok"])
        self.assertTrue(D.allow_exception(self.p.conn, self.pid, self.data, self.sid(1), "gấp, chấp nhận lệch", HUMAN, EP)["ok"])
        g = {x["idx"]: x for x in D.paid_gate(self.p.conn, self.pid, self.data, [self.sid(1)])}
        self.assertEqual(g[1]["level"], "warn")
        self.assertIn("ngoại lệ", g[1]["why"])

    def test_paid_gate_releases_after_approval(self):
        self.to_duyet()
        D.require_plate(self.p.conn, self.pid, self.data, self.sid(1), True, HUMAN, EP)
        self.assertEqual(D.paid_gate(self.p.conn, self.pid, self.data, [self.sid(1)])[0]["level"], "hold")
        self.assertTrue(D.approve(self.p.conn, self.pid, self.data, "1", HUMAN, EP)["ok"])
        self.assertEqual(D.paid_gate(self.p.conn, self.pid, self.data, [self.sid(1)]), [])

    def test_reset_asks_and_previews_then_marks_dependents(self):
        self.to_duyet()
        self.assertTrue(D.approve(self.p.conn, self.pid, self.data, "1", HUMAN, EP)["ok"])
        r = D.reset(self.p.conn, self.pid, self.data, "1", HUMAN)
        self.assertFalse(r["ok"])
        self.assertTrue(r["needs_confirm"])
        self.assertEqual(r["preview"]["cams_kept"], [1, 2, 3])
        self.assertEqual(r["preview"]["plates_stale_after"], [1, 2, 3])
        self.assertEqual(self.crew_state()["phase"], "xong")                                    # chưa xác nhận: không đổi gì
        r = D.reset(self.p.conn, self.pid, self.data, "1", HUMAN, confirm=True)
        self.assertTrue(r["ok"])
        self.assertIn("stage_camera", self.shot(self.pid, 1))                                   # máy cũ giữ tới lượt duyệt mới
        st = self.st()
        self.assertEqual(st["phase"], None)
        self.assertEqual(st["reset"]["plates_stale_after"], [1, 2, 3])
        olds = [d for d in os.listdir(D.seg_dir(self.data, self.pid, self.seg)) if d.startswith("crew_cu_")]
        self.assertEqual(len(olds), 1)


def test_decision_checks_pass():
    from tests import test_decisions as T
    for name in ("check_stage_desk_ep_only", "check_stage_desk_paid_gate", "check_stage_desk_reset_confirm"):
        getattr(T, name)()


def test_public_api_is_documented_at_the_top_of_the_module():
    doc = D.__doc__
    for name in ("status", "scene_status", "progress", "is_executive_producer", "paid_gate", "lock_holder", "busy", "check_inputs",
                 "estimate", "write_prompt", "load_answer", "build_sheet", "approve", "return_", "reset", "rerender", "score",
                 "render_plates", "require_plate", "allow_exception"):
        assert name + "(" in doc, name
        assert callable(getattr(D, name)), name
