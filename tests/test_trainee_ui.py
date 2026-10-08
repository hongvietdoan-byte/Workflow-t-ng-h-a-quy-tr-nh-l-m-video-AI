"""B7 học việc (08/10, docs/KE_HOACH_HOC_VIEC_2026-10-08.md mục 1 + 3): màn 🧪 3 nút Tắt / 🎓 Học việc / Bật, bảng độ khớp + thẻ
chấm 👍/👎, expander bước 5 tách "chưa kiểm thật" khỏi "🎓 học việc", devsys flags_trainee, nút "Duyệt tất cả" ghi note gate_bulk."""
import os
import tempfile
import unittest
from unittest import mock

from core import features, trainee
from core.db import connect
from core.pipeline import Pipeline

T0 = "2026-10-08T10:00:00+00:00"


def _clean_env():
    return mock.patch.dict(os.environ, {"FEATURE_" + k.upper(): "" for k in features.FEATURES})


class _Base(unittest.TestCase):
    def setUp(self):
        self.db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        env = mock.patch.dict(os.environ, {"PIPELINE_DB": self.db, "PIPELINE_DATA": tempfile.mkdtemp(),
                                           "FEATURE_SETTINGS_FILE": os.path.join(tempfile.mkdtemp(), "fs.json")})
        env.start()
        self.addCleanup(env.stop)
        ce = _clean_env()
        ce.start()
        self.addCleanup(ce.stop)
        self.conn = connect(self.db)
        self.p = Pipeline(self.conn)

    def _deliver(self, pid):
        self.conn.execute("INSERT INTO deliveries (project_id, path, source, delivered_at) VALUES (?,?,?,?)",
                          (pid, "x.mp4", "deliver", T0))
        self.conn.commit()


class ModeControlTests(_Base):
    def test_apply_mode_writes_modes_or_flags(self):
        from dashboard.design.screens import trainee_ui as TU
        TU.apply_mode("camera_setups", "trainee")
        s = features.settings()
        self.assertEqual(s["modes"].get("camera_setups"), "trainee")
        self.assertNotIn("camera_setups", s["flags"])
        self.assertEqual(features.state("camera_setups"), "trainee")
        TU.apply_mode("camera_setups", "on")
        s = features.settings()
        self.assertIs(s["flags"].get("camera_setups"), True)
        self.assertNotIn("camera_setups", s.get("modes") or {})
        TU.apply_mode("camera_setups", "off")
        self.assertIs(features.settings()["flags"].get("camera_setups"), False)
        self.assertEqual(features.state("camera_setups"), "off")

    def test_three_buttons_in_apptest(self):
        from streamlit.testing.v1 import AppTest

        def app():
            from dashboard.design.screens import trainee_ui as TU
            TU.mode_control("end_frames")

        at = AppTest.from_function(app, default_timeout=30)
        at.run()
        self.assertFalse(at.exception, at.exception)
        seg = at.get("button_group")
        self.assertTrue(seg, "không thấy st.segmented_control")
        seg[0].set_value("trainee").run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(features.state("end_frames"), "trainee")
        self.assertNotIn("end_frames", features.settings()["flags"])

    def test_no_effect_note_when_seedance_groups_on(self):
        from dashboard.design.screens import trainee_ui as TU
        features.save_settings(flags={"camera_setups": True, "seedance_ref_groups": True})
        self.assertIn("seedance_ref_groups", TU.no_effect_note("camera_setups"))
        features.save_settings(flags={"seedance_ref_groups": False})
        self.assertEqual(TU.no_effect_note("camera_setups"), "")
        features.save_settings(modes={"camera_setups": "trainee"}, flags={"seedance_ref_groups": True})
        self.assertEqual(TU.no_effect_note("camera_setups"), "")       # học việc: nothing is changed anyway


class TableAndCardTests(_Base):
    def _ready_camera(self):
        pids = []
        for n in range(2):
            pid = self.p.create_project(f"P{n}")
            pids.append(pid)
            for k, (dec, truth) in enumerate([("group", "group")] * 2 + [("skip", "single")] * 2):
                i = trainee.record(self.conn, "camera_setups", pid, f"group:{k}", dec)
                trainee.label(self.conn, i, truth)
        return pids

    def test_table_says_ready_and_never_touches_verified(self):
        from dashboard.design.screens import trainee_ui as TU
        self._ready_camera()
        rows = {r["feature"]: r for r in TU.table_rows(self.conn)}
        self.assertEqual(set(rows), set(features.trainee_list()))
        self.assertTrue(rows["camera_setups"]["ready"])
        self.assertIn("🎓 đủ chuẩn — chờ bạn duyệt", rows["camera_setups"]["status"])
        self.assertFalse(rows["end_frames"]["ready"])
        self.assertTrue(rows["end_frames"]["missing"])
        self.assertFalse(features.FEATURES["camera_setups"]["verified"])

    def test_spend_from_usage_events_trainee_stages(self):
        from dashboard.design.screens import trainee_ui as TU
        pid = self.p.create_project("P")
        self.conn.execute("INSERT INTO usage_events (job_id, project_id, kind, provider, model, tier, quantity, unit, at, stage)"
                          " VALUES (NULL,?,?,?,?,?,?,?,?,?)", (pid, "image", "clipai", "m1", "std", 1, "image", T0, "trainee_establishing"))
        self.conn.execute("INSERT INTO usage_events (job_id, project_id, kind, provider, model, tier, quantity, unit, at, stage)"
                          " VALUES (NULL,?,?,?,?,?,?,?,?,?)", (pid, "image", "clipai", "m1", "std", 1, "image", T0, "establishing"))
        self.conn.commit()
        spent = TU.spent_by_feature(self.conn, {"currency": "USD", "per_image": {"m1": 0.05}})
        self.assertAlmostEqual(spent.get("scene_establishing", 0), 0.05)

    def test_cards_only_unscored_card_roles_of_delivered_projects(self):
        from dashboard.design.screens import trainee_ui as TU
        done, open_ = self.p.create_project("Đã giao"), self.p.create_project("Chưa giao")
        self._deliver(done)
        a = trainee.record(self.conn, "end_frames", done, "end:1", "need_end")
        b = trainee.record(self.conn, "end_frames", open_, "end:2", "need_end")
        c = trainee.record(self.conn, "scene_establishing", done, "scene:1", "skip")
        trainee.label(self.conn, c, True)
        d = trainee.record(self.conn, "qc_team", done, "job:1", "block")          # review-based role: no card
        ids = [r["id"] for r in TU.card_rows(self.conn)]
        self.assertEqual(ids, [a])
        self.assertNotIn(b, ids)
        self.assertNotIn(d, ids)

    def test_card_click_calls_label(self):
        from streamlit.testing.v1 import AppTest
        pid = self.p.create_project("Đã giao")
        self._deliver(pid)
        i = trainee.record(self.conn, "continuous_takes", pid, "stretch:1:3-6", "stretch")

        def app():
            import os
            from core.db import connect
            from dashboard.design.screens import trainee_ui as TU
            TU.render_cards(connect(os.environ["PIPELINE_DB"]))

        at = AppTest.from_function(app, default_timeout=30)
        at.run()
        self.assertFalse(at.exception, at.exception)
        with mock.patch.object(trainee, "label", wraps=trainee.label) as lab:
            at.button(key=f"trn_no_{i}").click().run()
        self.assertFalse(at.exception, at.exception)
        lab.assert_called()
        row = self.conn.execute("SELECT truth, truth_source, match FROM trainee_log WHERE id=?", (i,)).fetchone()
        self.assertEqual((row["truth"], row["truth_source"], row["match"]), ("cut", "card", 0))

    def test_rescore_calls_score_project_per_project(self):
        from dashboard.design.screens import trainee_ui as TU
        pid = self.p.create_project("P")
        trainee.record(self.conn, "qc_team", pid, "job:1", "block", job_id=None)
        with mock.patch.object(trainee, "score_project", return_value={}) as sp:
            TU.rescore(self.conn)
        sp.assert_called_once_with(self.conn, pid)


class Step5SplitTests(_Base):
    def test_split_unverified_from_trainee(self):
        from dashboard.design.screens import trainee_ui as TU
        other = next(k for k, v in features.FEATURES.items() if not v["verified"] and not v.get("trainee"))
        with mock.patch.dict(os.environ, {"FEATURE_CAMERA_SETUPS": "1", "FEATURE_" + other.upper(): "1"}):
            s = TU.build_split()
        self.assertIn(other, s["unverified"])
        self.assertNotIn("camera_setups", s["unverified"])
        self.assertIn("camera_setups", s["trainee"])
        self.assertNotIn("FEATURE_<TÊN>=1", TU.UNVERIFIED_NOTE)
        self.assertIn("🧪", TU.UNVERIFIED_NOTE)

    def test_snapshot_after_delivery_scores_trainee(self):
        from dashboard.steps import step5
        p = mock.Mock(conn=self.conn)
        with mock.patch("core.effectiveness.snapshot"), mock.patch("core.lessons.after_delivery"), \
                mock.patch.object(trainee, "score_project", return_value={}) as sp:
            step5.snapshot_after_delivery(p, 7)
        sp.assert_called_once_with(self.conn, 7)

    def test_snapshot_survives_scoring_error(self):
        from dashboard.steps import step5
        p = mock.Mock(conn=self.conn)
        with mock.patch("core.effectiveness.snapshot"), mock.patch("core.lessons.after_delivery"), \
                mock.patch.object(trainee, "score_project", side_effect=RuntimeError("hỏng")):
            step5.snapshot_after_delivery(p, 7)                  # never raises


class BulkApproveTests(_Base):
    def test_note_gate_bulk_is_bulk(self):
        pid = self.p.create_project("P")
        sid = self.p.create_scene(pid, 1, "c1")
        jid = self.p.create_job(sid, "image_gen")
        self.conn.execute("INSERT INTO review_log (job_id, reviewer_type, decision, note, decided_at) VALUES (?,?,?,?,?)",
                          (jid, "user", "approve", "gate_bulk", T0))
        self.conn.commit()
        self.assertEqual(len(trainee._bulk_ids(self.conn, pid)), 1)

    def test_approve_all_buttons_pass_the_note(self):
        root = os.path.join(os.path.dirname(__file__), "..", "dashboard")
        for rel in ("steps/step2.py", "steps/step4.py", "design/screens/storyboard_cards.py"):
            with open(os.path.join(root, rel), encoding="utf-8") as f:
                self.assertIn('p.approve(jid, "user", note="gate_bulk")', f.read(), rel)


class DevsysTraineeTests(unittest.TestCase):
    def test_flags_trainee_metric_and_no_deduction(self):
        from devsys import metrics
        snap = {"files": [], "test_map": {}, "tests_by_area": {}, "todo_by_area": {}, "line_counts": {},
                "flags": [{"name": "qc_team", "areas": ["a"], "on": False, "verified": False, "mode": "trainee", "trainee": True},
                          {"name": "x", "areas": ["a"], "on": True, "verified": False, "mode": "on", "trainee": False}]}
        m = metrics.area_metrics(".", {"areas": []}, {"id": "a"}, snap)
        self.assertEqual(m["flags_trainee"], ["qc_team"])
        self.assertEqual(m["flags_on_unverified"], ["x"])


if __name__ == "__main__":
    unittest.main()
