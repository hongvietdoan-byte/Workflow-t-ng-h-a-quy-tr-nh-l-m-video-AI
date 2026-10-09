"""08/10 (#24 S08–S09): a Seedance group clip whose cut scdet does not see. Before: cut at the planned seconds (3.024 s) while the real
hard cut was at 3.875 s → 0.83 s of shot 8 opened shot 9's file, the clip QC rejected S09 and paid a new take. Now: (1) the cut is looked
for again around the planned seconds (seedance_refs.refine_cuts), (2) every part is measured as the QC will measure it and a cut near a
part's edge moves the bound before QC (inner_cut_moves), (3) the person can set the cut seconds in Bước 4 (seedance_refs.recut, 0 USD).

The fixture tests/fixtures/p24_group_s08_s09_small.mp4 is #24's real group clip (job 593) scaled to 124×216, no sound. 0 USD."""
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from core import clip_measure, ffmpeg_studio, seedance_refs
from core.db import connect
from core.pipeline import Pipeline

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "p24_group_s08_s09_small.mp4")
REAL_CUT = 3.875               # measured on the full-size 08_group.mp4 (histogram correlation 0.26 between frames 92 and 93)


def _ffmpeg():
    try:
        return ffmpeg_studio.find_ffmpeg()
    except ffmpeg_studio.FFmpegNotFound:
        raise unittest.SkipTest("no ffmpeg")


def _cv_or_skip():
    try:
        clip_measure._cv()
    except Exception:  # noqa: BLE001
        raise unittest.SkipTest("no OpenCV")


def _two_colours(path, ff, a=3.0, b=2.0):
    """Two 'shots' (noisy red, noisy blue) of a and b seconds at 24 fps."""
    subprocess.run([ff, "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=red:s=96x160:r=24:d={a}", "-f", "lavfi", "-i",
                    f"color=c=blue:s=96x160:r=24:d={b}", "-filter_complex", "[0][1]concat=n=2:v=1:a=0,noise=alls=20:allf=t", "-r", "24",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", path], check=True)


def _group(d1=3.0, d2=2.0):
    return [{"id": 1, "idx": 8, "data": {"duration_s": d1}}, {"id": 2, "idx": 9, "data": {"duration_s": d2}}]


class RefineTests(unittest.TestCase):
    def setUp(self):
        self.ff = _ffmpeg()
        _cv_or_skip()
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)

    def test_scdet_misses_the_p24_cut(self):
        """The cause: scdet (threshold 12) shows no cut in this clip — the old code then cut by the plan."""
        self.assertIsNone(seedance_refs.cut_points(FIXTURE, 2, self.ff))

    def test_p24_group_is_cut_at_the_real_cut(self):
        clip = os.path.join(self.d, "08.mp4")
        shutil.copyfile(FIXTURE, clip)
        res = seedance_refs.split(clip, _group(), [clip, os.path.join(self.d, "09.mp4")], self.ff)
        self.assertEqual(res["by"], "refined")
        self.assertAlmostEqual(res["planned"][0], 3.024, delta=0.01)
        self.assertAlmostEqual(res["cuts"][0], REAL_CUT, delta=0.05)
        self.assertEqual(res["moved"], [])
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(res["paths"][0]), REAL_CUT, delta=0.06)
        for part in res["paths"]:                     # what the clip QC measures: no cut left inside either shot's file
            self.assertEqual(clip_measure.jerks(part).get("cuts") or [], [], part)
        notes = seedance_refs.split_notes(res, 2)
        self.assertEqual([n[0] for n in notes], ["group_cut_refined"])
        self.assertIn("3.875 s (dự kiến 3.024 s)", notes[0][2])
        saved = seedance_refs.saved_cuts(os.path.join(self.d, "08_group.mp4"))
        self.assertEqual((saved["by"], saved["cuts"]), ("refined", res["cuts"]))

    def test_window_is_one_and_a_half_seconds(self):
        """A plan 2 s off the real cut does not reach it: the cut stays at the plan, said as a warning."""
        res = seedance_refs.refine_cuts(FIXTURE, [REAL_CUT - 2.0])
        self.assertEqual(res["found"], [None])
        self.assertEqual(res["cuts"], [REAL_CUT - 2.0])

    def test_no_clear_cut_keeps_the_plan_and_says_so(self):
        clip = os.path.join(self.d, "01.mp4")
        subprocess.run([self.ff, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=s=96x160:d=5:r=24", "-c:v", "libx264", "-pix_fmt",
                        "yuv420p", clip], check=True)
        res = seedance_refs.split(clip, _group(), [clip, os.path.join(self.d, "02.mp4")], self.ff)
        self.assertEqual(res["by"], "plan")
        notes = seedance_refs.split_notes(res, 2)
        self.assertEqual([(n[0], n[1]) for n in notes], [("group_cut_by_plan", "warn")])
        self.assertIn("Bước 4", notes[0][2])

    def test_cut_near_a_part_edge_moves_the_bound_before_qc(self):
        """(2) a wrong cut (here 0.8 s early) leaves a cut 0.8 s into shot 2's part: the group is cut again at the real cut."""
        clip = os.path.join(self.d, "01.mp4")
        _two_colours(clip, self.ff)
        with mock.patch.object(seedance_refs, "cut_points", return_value=[2.2]):
            res = seedance_refs.split(clip, _group(), [clip, os.path.join(self.d, "02.mp4")], self.ff)
        self.assertEqual(res["by"], "detected")
        self.assertEqual(len(res["moved"]), 1)
        self.assertAlmostEqual(res["moved"][0][1], 3.0, delta=0.05)
        self.assertAlmostEqual(res["cuts"][0], 3.0, delta=0.05)
        self.assertEqual(clip_measure.jerks(res["paths"][1]).get("cuts") or [], [])
        self.assertEqual([n[0] for n in seedance_refs.split_notes(res, 2)], ["group_cut_moved"])

    def test_cut_far_from_the_edges_is_left_to_qc(self):
        """A cut in the middle of a part (> 1.2 s from both ends) is not a mis-cut of the group: nothing moves."""
        self.assertEqual(seedance_refs.inner_cut_moves([0.0, 6.0, 8.0], [FIXTURE, FIXTURE], edge=0.5), {})


class RecutTests(unittest.TestCase):
    def setUp(self):
        self.ff = _ffmpeg()
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("recut")
        self.s8 = self.p.create_scene(self.pid, 8, "S8")
        self.s9 = self.p.create_scene(self.pid, 9, "S9")
        self.lead = self.p.create_job(self.s8, "video_gen")
        self.follow = self.p.create_job(self.s9, "video_gen")
        p8, p9 = os.path.join(self.d, "08.mp4"), os.path.join(self.d, "09.mp4")
        shutil.copyfile(FIXTURE, os.path.join(self.d, "08_group.mp4"))
        for path in (p8, p9):
            shutil.copyfile(FIXTURE, path)
        self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (p8, self.lead))
        self.p.conn.execute("UPDATE jobs SET result_path=?, group_leader=? WHERE id=?", (p9, self.lead, self.follow))
        self.p.conn.commit()

    def test_person_sets_the_cut(self):
        res = seedance_refs.recut(self.p, self.lead, [REAL_CUT])
        self.assertEqual(res["skipped"], [])
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(res["paths"][0]), REAL_CUT, delta=0.06)
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(res["paths"][1]), 5.042 - REAL_CUT, delta=0.08)
        self.assertEqual(seedance_refs.saved_cuts(os.path.join(self.d, "08_group.mp4"))["by"], "user")
        codes = [r["code"] for r in self.p.conn.execute("SELECT code FROM diag_events WHERE project_id=?", (self.pid,))]
        self.assertIn("group_recut_by_user", codes)
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0], 0)   # nothing sent, nothing billed

    def test_wrong_cuts_are_refused(self):
        with self.assertRaises(ValueError):
            seedance_refs.recut(self.p, self.lead, [1.0, 2.0])          # 2 shots → 1 cut
        with self.assertRaises(ValueError):
            seedance_refs.recut(self.p, self.lead, [5.0])               # leaves < 0.3 s for shot 9

    def test_a_newer_take_is_never_overwritten(self):
        newer = self.p.create_job(self.s9, "video_gen")
        mine = os.path.join(self.d, "09_new.mp4")
        _two_colours(mine, self.ff, 1.0, 1.0)
        self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (mine, newer))
        self.p.conn.commit()
        before = os.path.getsize(os.path.join(self.d, "09.mp4"))
        res = seedance_refs.recut(self.p, self.lead, [REAL_CUT])
        self.assertEqual(res["skipped"], [9])
        self.assertEqual(os.path.getsize(os.path.join(self.d, "09.mp4")), before)
        self.assertTrue(res["paths"][1].endswith("_recut_unused.mp4"))


class RunnerNotesTests(unittest.TestCase):
    def test_finish_group_says_how_it_was_cut(self):
        from tests.test_job_lifecycle_b1a import _Base
        from core.providers import MockVideoProvider
        from core.runner import VideoRunner

        class T(_Base):
            def runTest(self):
                pass
        t = T()
        t.setUp()
        s1, s2 = t.scene_ready_for_video(1), t.scene_ready_for_video(2)
        leader = t.p.create_job(s1, "video_gen")
        t.p.conn.execute("UPDATE jobs SET external_id='mock-1', model='seedance' WHERE id=?", (leader,))
        t.p.start(leader)
        r = VideoRunner(t.p, MockVideoProvider(), t.dir)
        group = [{"id": s1, "idx": 1, "refs": True, "data": {}}, {"id": s2, "idx": 2, "refs": True, "data": {}}]
        res = {"paths": [], "cuts": [3.875], "by": "refined", "planned": [3.024], "found": [3.875], "moved": []}
        with mock.patch("core.seedance_refs.split", return_value=res), mock.patch("core.shots.trim_clip"), \
                mock.patch.object(r, "_clean_edges"):
            r._finish_group(t.p.job(leader), os.path.join(t.dir, "01.mp4"), group)
        rows = t.p.conn.execute("SELECT code, message FROM diag_events WHERE job_id=?", (leader,)).fetchall()
        self.assertEqual([x["code"] for x in rows], ["group_cut_refined"])
        self.assertIn("3.875", rows[0]["message"])


class Step4PanelTests(unittest.TestCase):
    """(3) Bước 4: '✂ Điểm cắt clip nhóm' on the group's shot cards — the person types the second and cuts again, 0 USD."""

    def test_person_recuts_from_the_video_step(self):
        from streamlit.testing.v1 import AppTest
        _ffmpeg()
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        db, data = os.path.join(tmp, "m.sqlite"), os.path.join(tmp, "projects")
        patcher = mock.patch.dict(os.environ, {"PIPELINE_DB": db, "PIPELINE_DATA": data, "KNOWLEDGE_USER_DIR": os.path.join(tmp, "k"),
                                               "FEATURE_UI_V2": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)
        p = Pipeline(connect(db))
        pid = p.create_project("Nhóm cắt")
        vdir = os.path.join(data, str(pid), "videos")
        os.makedirs(vdir)
        jobs = []
        for idx in (8, 9):
            scene = p.create_scene(pid, idx, f"S{idx}")
            jid = p.create_job(scene, "video_gen")
            path = os.path.join(vdir, f"{idx:02d}.mp4")
            shutil.copyfile(FIXTURE, path)
            p.conn.execute("UPDATE jobs SET state='pending_review', result_path=?, model='seedance', group_leader=? WHERE id=?",
                           (path, jobs[0] if jobs else None, jid))
            jobs.append(jid)
        shutil.copyfile(FIXTURE, os.path.join(vdir, "08_group.mp4"))
        p.conn.commit()
        at = AppTest.from_file(os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py"), default_timeout=60).run()
        at.radio(key="step").set_value(at.radio(key="step").options[3]).run()
        self.assertFalse(at.exception, at.exception)
        # 09/10 (người dùng): the "✂ Điểm cắt clip nhóm" bar is no longer on the clip card (seedance_refs.recut stays — tested above)
        self.assertFalse([w for w in at.number_input if str(w.key).startswith("gcut_")])
        self.assertFalse([b for b in at.button if str(b.key).startswith("gcut_go_")])


if __name__ == "__main__":
    unittest.main()


class DraftPreviewTests(unittest.TestCase):
    """09/10 (người dùng): "chưa có nút gộp xem bản draft" — clips still in review are put together to watch (0 USD, not a delivery)."""
    def test_pending_clips_are_put_together(self):
        import tempfile
        from core import final_cut
        p = Pipeline(connect())
        pid = p.create_project("t", aspect="9:16")
        data = tempfile.mkdtemp()
        vdir = os.path.join(data, str(pid), "videos")
        os.makedirs(vdir)
        for idx in (1, 2):
            sid = p.create_scene(pid, idx, f"S{idx}")
            jid = p.create_job(sid, "video_gen")
            path = os.path.join(vdir, f"{idx:02d}.mp4")
            shutil.copyfile(FIXTURE, path)
            p.conn.execute("UPDATE jobs SET state='pending_review', result_path=? WHERE id=?", (path, jid))
        p.create_scene(pid, 3, "S3")                                        # no clip yet
        p.conn.commit()
        res = final_cut.draft_preview(p, data, pid)
        self.assertTrue(os.path.exists(res["path"]))
        self.assertEqual(res["shots"], [1, 2])
        self.assertEqual(res["missing"], [3])
        self.assertGreater(ffmpeg_studio.probe_duration(res["path"]), 0)
        self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM outputs").fetchone()[0], 0)   # never a delivery
