"""KLD-1, KLD-2, KLD-3 (người dùng duyệt 08/10 — docs/TONG_HOP_3_LUOT_KHUNG_LONG_DO.md mục 4.8, 4.12, 5).

KLD-1: job 559 của #22 hỏng vì `stale_input` vẫn nằm trong nút "↻ Gửi lại clip lỗi (lỗi nhà cung cấp)" → gửi lại y nguyên đầu vào cũ
       thành job 566. Nút chỉ còn lỗi nhà cung cấp; `Pipeline.retry` không `fix` từ chối job `stale_input`.
KLD-2: chuỗi nối / dựng lấy job số lớn nhất, nên phải hoán đổi dòng 560 ↔ 569 (qc_results lệch tệp). Trường `chosen_video_job`.
KLD-3: bản dựng #33 gom 4 tệp phụ trong videos/ (thiếu shot 1, 2) — tệp .mp4 lạ mặc định không dùng."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import batch, final_cut, lineage, stage_map, takes
from core.db import connect
from core.pipeline import Pipeline
from core.states import InvalidTransition


def _read(path):
    with open(path, "rb") as f:
        return f.read()


class Base(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("KLD")
        self.s1 = self.p.create_scene(self.pid, 1, "Shot 1")
        self.s2 = self.p.create_scene(self.pid, 2, "Shot 2")
        os.makedirs(os.path.join(self.data, str(self.pid), "videos"), exist_ok=True)

    def dest(self, idx=1):
        return final_cut.clip_path(self.data, self.pid, idx)

    def download(self, jid, content: bytes, idx=1):
        """What VideoRunner does when a take finishes: make room in NN.mp4, write the file, link it, succeed."""
        job = self.p.job(jid)
        takes.make_room(self.p.conn, self.data, job, self.dest(idx))
        with open(self.dest(idx), "wb") as f:
            f.write(content)
        self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (self.dest(idx), jid))
        self.p.conn.commit()
        self.p.succeed(jid)

    def fail_with(self, sid, note):
        jid = self.p.create_job(sid, "video_gen")
        self.p.start(jid)
        self.p.fail(jid, note)
        return jid


class Kld1StaleInputTests(Base):
    def test_retry_without_fix_refuses_a_job_failed_on_stale_input(self):
        jid = self.fail_with(self.s1, "stale_input: ảnh đã duyệt đã đổi")
        with self.assertRaises(InvalidTransition) as e:
            self.p.retry(jid, "gửi lại clip lỗi (lỗi nhà cung cấp)", by_user=True)
        self.assertIn("đầu vào", str(e.exception))
        self.assertEqual(self.p.state(jid).value, "failed")                 # nothing moved, nothing queued
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 1)
        self.assertIsNotNone(self.p.retry(jid, "người dùng sửa", fix="Keep the red hood on.", by_user=True))

    def test_a_provider_failure_is_still_resent(self):
        jid = self.fail_with(self.s1, "timeout: provider overloaded")
        self.assertIsNotNone(self.p.retry(jid, "gửi lại", by_user=True))

    def test_resend_list_holds_only_provider_failures(self):
        stale = self.fail_with(self.s1, "stale_input: motion prompt đã đổi")
        missing = self.fail_with(self.s2, "missing inputs (approved image / motion prompt / image prompt)")
        s3 = self.p.create_scene(self.pid, 3, "Shot 3")
        net = self.fail_with(s3, "timeout: server busy")
        self.assertEqual(batch.provider_failures(self.p, self.pid), [net])
        self.assertEqual(sorted(r["id"] for r in batch.input_failures(self.p, self.pid)), sorted([stale, missing]))

    def test_requeue_from_new_inputs_closes_the_old_job_and_queues_a_fresh_one(self):
        stale = self.fail_with(self.s1, "stale_input: ảnh đã đổi")
        other = self.fail_with(self.s2, "stale_input: ảnh đã đổi")
        with mock.patch("core.llm_io.ready_for_video", return_value=[{"scene_id": self.s1}]):
            out = batch.requeue_input_failures(self.p, self.pid)
        self.assertEqual(out["created"], 1)
        self.assertEqual(out["not_ready"], [2])                              # shot 2's inputs are not approved: said, not sent
        self.assertEqual(self.p.state(stale).value, "cancelled")
        self.assertEqual(self.p.state(other).value, "failed")
        new = self.p.conn.execute("SELECT * FROM jobs WHERE scene_id=? AND state='queued'", (self.s1,)).fetchone()
        self.assertIsNotNone(new)
        self.assertIsNone(new["retry_reason"])                               # a fresh job from the current inputs, not a resend
        self.assertEqual(batch.input_failures(self.p, self.pid)[0]["id"], other)


class Kld2ChosenTakeTests(Base):
    def kld22(self):
        """#22 shot 8: take 560 (QC 0.81 rejects it) → automatic take 569 (worse, approved by the run)."""
        a = self.p.create_job(self.s1, "video_gen")
        self.p.start(a)
        self.download(a, b"take-560")
        self.p.reject(a, "ai_agent", "QC 0.81 < 0.82")
        b = self.p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND id>?", (self.s1, a)).fetchone()["id"]
        self.p.start(b)
        self.download(b, b"take-569")
        self.p.approve(b, "ai_agent")
        return a, b

    def test_a_new_take_keeps_the_old_take_file_reachable(self):
        a, b = self.kld22()
        old = self.p.job(a)["result_path"]
        self.assertNotEqual(os.path.normcase(old), os.path.normcase(self.dest()))
        self.assertEqual(_read(old), b"take-560")
        self.assertEqual(_read(self.dest()), b"take-569")
        self.assertEqual([r["id"] for r in takes.candidates(self.p.conn, self.s1)], [a])

    def test_choosing_an_older_take_needs_no_row_swap_and_every_reader_follows(self):
        from core import llm_io
        img = self.p.create_job(self.s1)                                       # an approved picture + motion prompt (stage map: done)
        self.p.start(img)
        self.p.succeed(img)
        self.p.approve(img)
        llm_io.store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": 1, "motion_prompt": "dance", "duration_sec": 4}]})
        llm_io.approve_motion_prompt(self.p, self.s1)
        a, b = self.kld22()
        self.p.conn.execute("INSERT INTO qc_results (job_id, criterion, score, threshold_at_time, auto_decision) VALUES (?,?,?,?,?)",
                            (a, "identity", 0.81, 0.82, "fail"))
        takes.choose(self.p, self.data, a)
        self.assertEqual(_read(self.dest()), b"take-560")                     # the shot's clip IS the chosen take
        self.assertEqual(_read(self.p.job(b)["result_path"]), b"take-569")    # the other take keeps its own file
        self.assertEqual(self.p.state(a).value, "approved")
        self.assertEqual(self.p.state(b).value, "rejected")
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.s1,)).fetchone()[0] or "{}")
        self.assertEqual(data["chosen_video_job"], a)
        self.assertEqual(self.p.conn.execute("SELECT job_id FROM qc_results").fetchone()[0], a)   # the score stays with its file
        clip = final_cut.collect_clips(self.p, self.data, self.pid)[0]
        self.assertEqual((clip["state"], clip["usable"]), ("approved", True))
        self.assertEqual(lineage.scan(self.p.conn, self.pid)[self.s1]["video_job_id"], a)
        self.assertEqual(stage_map.build(self.p.conn, self.pid)[0]["video"], "done")
        self.assertEqual(takes.used(self.p.conn, self.s1)["id"], a)
        takes.choose(self.p, self.data, b)                                    # and back again
        self.assertEqual(_read(self.dest()), b"take-569")
        self.assertEqual(takes.used(self.p.conn, self.s1)["id"], b)

    def test_the_chain_starts_from_the_chosen_take(self):
        from core.runner import VideoRunner
        from core.providers import MockVideoProvider
        a, _b = self.kld22()
        takes.choose(self.p, self.data, a)
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"start_from_prev_clip": True}), self.s2))
        self.p.conn.commit()
        vr = VideoRunner(self.p, MockVideoProvider(), self.data)

        def fake_run(cmd, **_kw):
            with open(cmd[-1], "wb") as f:
                f.write(b"png")
        with mock.patch("core.ffmpeg_studio.find_ffmpeg", return_value="ffmpeg"), mock.patch("subprocess.run", side_effect=fake_run):
            frame = vr._chain_frame(self.pid, self.s2)
        self.assertIsNotNone(frame)
        self.assertIn(f"from_job_{a}", os.path.basename(frame))
        self.assertEqual(batch.chain_waits(self.p, self.pid), {})

    def test_a_take_without_its_own_file_cannot_be_chosen(self):
        old = self.p.create_job(self.s1, "video_gen")                         # data from before KLD-2: both rows point at 01.mp4
        new = self.p.create_job(self.s1, "video_gen")
        open(self.dest(), "wb").write(b"take-new")
        for j in (old, new):
            self.p.start(j)
            self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (self.dest(), j))
            self.p.succeed(j)
        with self.assertRaises(ValueError):
            takes.choose(self.p, self.data, old)
        self.assertEqual(takes.candidates(self.p.conn, self.s1), [])

    def test_no_choice_while_another_take_is_being_made(self):
        a, b = self.kld22()
        running = self.p.create_job(self.s1, "video_gen")
        self.p.start(running)
        with self.assertRaises(ValueError):
            takes.choose(self.p, self.data, a)

    def test_keeping_a_rejected_take_marks_it_as_the_shot_take(self):
        a = self.p.create_job(self.s1, "video_gen")
        self.p.start(a)
        self.download(a, b"take")
        self.p.reject(a, "ai_agent", "QC 0.6")
        self.p.keep_rejected(a)
        self.assertEqual(takes.chosen(self.p.conn, self.s1)["id"], a)

    def test_a_new_download_ends_the_old_choice(self):
        a, b = self.kld22()
        takes.choose(self.p, self.data, a)
        c = self.p.create_job(self.s1, "video_gen")                           # the person asks for another take later
        self.p.start(c)
        self.download(c, b"take-new")
        self.assertIsNone(takes.chosen(self.p.conn, self.s1))
        self.assertEqual(_read(self.p.job(a)["result_path"]), b"take-560")
        self.assertEqual(takes.used(self.p.conn, self.s1)["id"], c)


class Kld3ExtraFilesTests(Base):
    def test_stray_mp4_files_are_listed_but_not_used_by_default(self):
        for name in ("01.mp4", "02.mp4", "01_seedance20_job562.mp4", "08_job560_giu.mp4", "01_t4a.mp4", "01_raw_t4a.mp4"):
            open(os.path.join(self.data, str(self.pid), "videos", name), "wb").write(b"x")
        clips = final_cut.collect_clips(self.p, self.data, self.pid)
        extras = [c for c in clips if c["idx"] is None]
        self.assertEqual(len(extras), 4)
        self.assertTrue(all(c["extra"] and not c["usable"] for c in extras))
        self.assertEqual([c["idx"] for c in final_cut.usable_clips(self.p, self.data, self.pid)], [1, 2])
        self.assertEqual([c["idx"] for c in final_cut.collect_clips_for_render(self.p.conn, self.data, self.pid)], [1, 2])
        ticked = final_cut.collect_clips_for_render(self.p.conn, self.data, self.pid, [self.dest(1), extras[0]["path"]])
        self.assertEqual(len(ticked), 2)                                       # the person ticked it: it goes in


if __name__ == "__main__":
    unittest.main()
