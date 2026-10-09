"""F5-B (09/10) — dọn việc tồn của `docs/TONG_HOP_3_LUOT_KHUNG_LONG_DO.md` mục 5 + "Còn tồn" của TODO. Mỗi lớp một mục KLD-n."""
import json
import os
import unittest
from unittest import mock

from core import claude_tasks, knowledge, llm_runner, shots

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _flags(**kw):
    return mock.patch.dict(os.environ, {f"FEATURE_{k.upper()}": v for k, v in kw.items()})


def _read(rel):
    return open(os.path.join(ROOT, *rel.split("/")), encoding="utf-8").read()


class DirectorLessons(unittest.TestCase):
    """KLD-9 / KLD-25 đã có ở `director_kld22.md` (cờ kld_lessons_prompts); KLD-31 thêm ở đây. Trần ký tự nhóm Đạo diễn còn ≥ 1 000."""

    def test_kld9_25_31_are_written_with_their_confidence(self):
        d = knowledge.kld_text("director")
        self.assertIn("Hô biến", d)                       # KLD-9: thoại dán tay đọc to → script_notes kind thoại
        self.assertIn('`kind: "thoại"`', d)
        self.assertIn("0,03 / 0,44", d)                   # KLD-25
        self.assertIn("dialogue_take", d)
        self.assertIn("KLD-31", d)                        # KLD-31: mỗi cảnh một clip 15 s → bịa áo; chia shot → đúng
        part = d[d.index("KLD-31"):]
        self.assertIn("15 s", part)
        self.assertIn("chia cảnh thành các", part)
        self.assertIn("1 mẫu", part)                      # độ tin ghi rõ, không thành luật
        self.assertIn("tradeoffs", part)

    def test_director_group_keeps_1000_chars_of_room(self):
        with _flags(kelly_knowledge="1", murch_knowledge="1", film_crew="1"):
            chars = knowledge.overview("director")["chars"]
        self.assertLess(chars, knowledge.MAX_USER_CHARS - 1000)


class AssetChecklistPrompt(unittest.TestCase):
    def test_kld33_outfit_accessory_state_and_model_hair(self):
        t = _read("prompts/27_asset_checklist.md")
        self.assertIn("trạng thái mặc", t)
        self.assertIn("khẩu trang đeo kín", t)
        self.assertIn("không đoán", t)
        self.assertIn("tóc của **nhân vật**", t)
        self.assertIn("người mẫu", t)


class TranslateAmbiguous(unittest.TestCase):
    """KLD-32: chữ nhiều nghĩa giữ nguyên chữ Việt trong ngoặc + báo, không đoán. Cờ tắt → prompt dịch y hệt trước."""

    def setUp(self):
        from tests.test_v3 import kenta_project
        self.p, self.pid = kenta_project(shot_mode="per_shot")
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        rows = shots.shots_of(self.p, self.pid)
        self.sid = rows[0]["id"]
        self.idx = str(self.p.conn.execute("SELECT idx FROM scenes WHERE id=?", (self.sid,)).fetchone()["idx"])
        for r in self.p.conn.execute("SELECT id, data FROM scenes WHERE project_id=?", (self.pid,)).fetchall():
            d = json.loads(r["data"] or "{}")
            for k in ("action", "end_state", "performance"):
                d.pop(k, None)
            if r["id"] == self.sid:
                d["action"] = "Maxim đội mũ rồi quay đi"
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), r["id"]))
        self.p.conn.commit()

    def _run(self, answer, flag):
        seen = []

        class C:
            name = "fake"

            def complete(self, prompt, images=()):
                seen.append(prompt)
                return llm_runner.LlmReply(json.dumps(answer, ensure_ascii=False), 10, 5)
        with _flags(kld_lessons_prompts=flag):
            n = claude_tasks.translate_motion_fields(self.p, self.pid, C())
        d = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.sid,)).fetchone()["data"])
        return n, d, seen[0]

    def test_flag_off_prompt_has_no_rule(self):
        n, d, prompt = self._run({self.idx: {"action": "Maxim puts on a cap and turns away"}}, "0")
        self.assertEqual(n, 1)
        self.assertNotIn(claude_tasks.TRANSLATE_AMBIGUOUS_RULE, prompt)
        self.assertNotIn("motion_en_ambiguous", d)

    def test_flag_on_keeps_the_word_and_reports_it(self):
        ans = {self.idx: {"action": "Maxim puts on a hat [mũ] and turns away"}, claude_tasks.AMBIGUOUS_KEY: {self.idx: ["mũ"]}}
        n, d, prompt = self._run(ans, "1")
        self.assertIn(claude_tasks.TRANSLATE_AMBIGUOUS_RULE, prompt)
        self.assertEqual(n, 1)
        self.assertEqual(d["motion_en"]["action"], "Maxim puts on a hat [mũ] and turns away")   # bracket accepted, not re-asked
        self.assertEqual(d["motion_en_ambiguous"], ["mũ"])
        row = self.p.conn.execute("SELECT message FROM diag_events WHERE code='translate_ambiguous' AND project_id=?",
                                  (self.pid,)).fetchone()
        self.assertIsNotNone(row)
        self.assertIn("mũ", row["message"])


class EndFrameLint(unittest.TestCase):
    """KLD-13: pull_out / crane / orbit mà prompt không tả khung giây cuối → ⚠ (chỉ cảnh báo)."""

    def test_big_moves_without_an_end_frame_are_flagged(self):
        from core import motion_prompt_lint as L
        for move in ("pull_out", "crane", "orbit"):
            msg = L.end_frame_problem({"camera_move": move}, "The camera pulls back slowly from Kelly.")
            self.assertIsNotNone(msg, move)
            self.assertIn(move, msg)
        self.assertIsNone(L.end_frame_problem({"camera_move": "pull_out"},
                                              "The camera pulls back from Kelly and ends on a wide shot of the empty yard."))
        self.assertIsNone(L.end_frame_problem({"camera_move": "crane"}, "Crane up; final frame: the tower fills the top half."))
        self.assertIsNone(L.end_frame_problem({"camera_move": "orbit"}, "Máy quay vòng, khung cuối thấy mặt Kelly."))
        self.assertIsNone(L.end_frame_problem({"camera_move": "push_in"}, "Push in on Kelly."))   # not concerned
        self.assertIsNone(L.end_frame_problem({}, ""))

    def test_step3_shows_it_as_a_flag(self):
        src = _read("dashboard/steps/step3.py")
        self.assertIn("motion_prompt_lint.end_frame_problem(data, r[\"motion_prompt\"])", src)


class ShakeBeforeMusic(unittest.TestCase):
    """KLD-26: rung đặt trước giây nhạc vào → cảnh báo trong báo cáo dựng; bản dựng giữ nguyên."""

    def test_only_shakes_before_the_music_are_reported(self):
        from core.delivery import shakes_before_music
        out = shakes_before_music([0.5, 1.79, 2.0, 6.0], 1.8)
        self.assertEqual(out["times"], [0.5])                     # 1,79 is within the 0,05 s margin
        self.assertEqual(out["music_in"], 1.8)
        self.assertIn("bản dựng không tự đổi", out["note"])
        self.assertIsNone(shakes_before_music([2.0, 3.0], 1.8))
        self.assertIsNone(shakes_before_music([0.5], None))      # no music in the render: nothing to compare with
        self.assertIsNone(shakes_before_music([], 1.8))

    def test_render_reports_without_dropping_the_shakes(self):
        src = _read("core/delivery.py")
        i = src.index("early = shakes_before_music(hits")
        block = src[i - 200:i + 500]
        self.assertIn('manifest["shakes"] = hits', block)          # the shakes stay in the render
        self.assertIn('manifest["shake_before_music"] = early', block)
        self.assertIn('"shake_before_music"', block)              # + diag


class Timestamps(unittest.TestCase):
    """KLD-30: usage_events.at ('YYYY-MM-DD HH:MM:SS') ↔ jobs.created_at (ISO có 'T' + múi) so sánh đúng."""

    def test_both_formats_compare_on_one_clock(self):
        from core.timestamps import utc_key
        self.assertEqual(utc_key("2026-10-07 06:00:00"), "2026-10-07 06:00:00")
        self.assertEqual(utc_key("2026-10-07T06:00:00+00:00"), "2026-10-07 06:00:00")
        self.assertEqual(utc_key("2026-10-07T13:00:00+07:00"), "2026-10-07 06:00:00")
        self.assertEqual(utc_key("2026-10-07"), "2026-10-07 00:00:00")
        self.assertLess("2026-10-07 06:00:00", "2026-10-07T05:00")       # the bug: raw text says 06:00 comes first
        self.assertGreater(utc_key("2026-10-07 06:00:00"), utc_key("2026-10-07T05:00"))
        self.assertLess(utc_key("2026-10-07T07:25"), utc_key("9999"))         # the sentinels of kld_round_stats still bound
        self.assertLess(utc_key("0000"), utc_key("2026-10-07 00:00:00"))
        self.assertEqual(utc_key(None), "")

    def test_round_stats_put_both_tables_in_the_same_round(self):
        import importlib
        import sys
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        stats = importlib.import_module("kld_round_stats")
        self.assertEqual(stats.rnd_of("2026-10-07 05:00:00"), 1)
        self.assertEqual(stats.rnd_of("2026-10-07T05:00:00+00:00"), 1)
        self.assertEqual(stats.rnd_of("2026-10-07T12:00:00+07:00"), 1)  # 05:00 UTC
        self.assertEqual(stats.rnd_of("2026-10-06 23:00:00"), 0)
        self.assertEqual(stats.rnd_of("2026-10-07 08:00:00"), 2)

    def test_audit_since_with_a_T_keeps_a_later_usage_row(self):
        import importlib
        import sqlite3
        import sys
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        audit = importlib.import_module("audit_run")
        c = sqlite3.connect(":memory:")
        c.execute("CREATE TABLE jobs (id INTEGER, project_id INTEGER)")
        c.execute("CREATE TABLE usage_events (job_id INTEGER, provider TEXT, at TEXT)")
        c.executemany("INSERT INTO jobs VALUES (?,?)", [(1, 7), (2, 8)])
        c.executemany("INSERT INTO usage_events VALUES (?,?,?)", [(1, "clipai", "2026-10-07 06:00:00"),
                                                                  (2, "clipai", "2026-10-07 04:00:00")])
        self.assertEqual(audit.pick_projects(c, "2026-10-07T05:00"), [7])
        self.assertEqual(audit.pick_projects(c, None), [7, 8])


class RewriteOnQcRetake(unittest.TestCase):
    """KLD-34 (kiểm, không đổi luồng tiền): đường tự gen lại VIDEO của QC đi qua `director_rewrite` khi cờ bật — cả chế độ auto
    (đã có test ở test_prompt_rewrite) lẫn human_qc + tự sửa (autofix). Cờ tắt → không gọi Claude, câu Fix cũ."""

    def _base(self):
        from tests.test_prompt_rewrite import Base
        b = Base("run")
        b.setUp()
        self.addCleanup(b.doCleanups)
        return b

    def test_human_qc_autofix_video_retake_is_rewritten_when_the_flag_is_on(self):
        from tests.test_prompt_rewrite import BAD, ON
        b = self._base()
        _, sid, job = b.make("human_qc", kind="video_gen")
        with mock.patch.dict(os.environ, ON):
            self.assertEqual(b.p.apply_qc(job, BAD, issues="Keep the camera still.", autofix=True), "auto_fix")
        self.assertEqual(len(b.client.calls), 1)
        self.assertIn("Keep the camera still.", b.client.calls[0][0])
        child = b.child(job)
        self.assertEqual(child["type"], "video_gen")
        self.assertEqual(child["origin"], "auto")

    def test_flag_off_keeps_the_fix_sentence_and_calls_nobody(self):
        from tests.test_prompt_rewrite import BAD, OFF
        b = self._base()
        _, sid, job = b.make("human_qc", kind="video_gen")
        with mock.patch.dict(os.environ, OFF):
            b.p.apply_qc(job, BAD, issues="Keep the camera still.", autofix=True)
        self.assertEqual(b.client.calls, [])
        self.assertIn("Keep the camera still.", b.child(job)["retry_reason"])


class RefVideoSound(unittest.TestCase):
    """Còn tồn TODO (#24 08/10): tiếng của video ref → SFX đề xuất của shot (use False), nén/giãn khi dựng nếu chênh ≤ 40 %."""

    def setUp(self):
        import shutil
        import subprocess
        import tempfile
        from core import ffmpeg_studio
        from core.db import connect
        from core.pipeline import Pipeline
        try:
            self.ff = ffmpeg_studio.find_ffmpeg()
        except ffmpeg_studio.FFmpegNotFound:
            self.skipTest("no ffmpeg")
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("ref", "human_qc")
        self.with_sound = os.path.join(self.tmp, "ref_sound.mp4")
        self.silent = os.path.join(self.tmp, "ref_silent.mp4")
        subprocess.run([self.ff, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=64x64:d=2", "-f", "lavfi", "-i",
                        "sine=frequency=440:duration=2", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                        self.with_sound], check=True)
        subprocess.run([self.ff, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=64x64:d=2", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", self.silent], check=True)
        for idx, ref in ((5, self.with_sound), (6, self.silent), (7, os.path.join(self.tmp, "gone.mp4"))):
            sid = self.p.create_scene(self.pid, idx, f"S{idx:02d}")
            self.p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, state, ref_video_path) VALUES (?,?,?,?)",
                                (sid, "x", "approved", ref))
        self.p.conn.commit()

    def test_propose_extracts_only_sound_and_never_switches_it_on(self):
        from core import audio_lib, ref_audio
        res = ref_audio.propose(self.p, self.tmp, self.pid)
        self.assertEqual((res["added"], res["no_audio"], res["missing"]), ([5], [6], [7]))
        directory = audio_lib.assets_dir(self.tmp, self.pid)
        self.assertTrue(os.path.isabs(directory) or directory.startswith(self.tmp))
        items = audio_lib.load(directory)
        self.assertEqual(len(items), 1)
        e = items[0]
        self.assertEqual((e["label"], e["use"], e["anchor_idx"], e["offset"], e["source"]), ("Tiếng video ref shot 5", False, 5, 0.0, "ref_video"))
        self.assertAlmostEqual(e["ref_seconds"], 2.0, delta=0.15)
        self.assertTrue(os.path.exists(os.path.join(directory, e["file"])))
        self.assertEqual(audio_lib.mix_list(directory), [])                        # proposal: not in the mix until ticked
        again = ref_audio.propose(self.p, self.tmp, self.pid)
        self.assertEqual((again["added"], again["already"]), ([], [5]))               # no duplicate

    def test_fit_stretches_within_40_percent_and_keeps_speed_beyond(self):
        from core import audio_lib, ffmpeg_studio, ref_audio
        ref_audio.propose(self.p, self.tmp, self.pid)
        directory = audio_lib.assets_dir(self.tmp, self.pid)
        e = audio_lib.load(directory)[0]
        ref_audio.fit(directory, e, 2.5)                       # 2,0 s → 2,5 s: −20 %, stretched
        self.assertAlmostEqual(e["fit_tempo"], round(e["ref_seconds"] / 2.5, 4))
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(os.path.join(directory, e["fit_file"])), 2.5, delta=0.15)
        ref_audio.fit(directory, e, 5.0)                       # 2,0 s → 5,0 s: 60 % off → kept as it is, said
        self.assertNotIn("fit_file", e)
        self.assertIn("40 %", e["fit_skipped"])

    def test_render_timeline_fits_a_ticked_sound_and_the_mix_uses_it(self):
        from core import audio_lib, sfx_plan, ref_audio
        ref_audio.propose(self.p, self.tmp, self.pid)
        directory = audio_lib.assets_dir(self.tmp, self.pid)
        rows = [{"idx": 4}, {"idx": 5}]
        sfx_plan.place_on_timeline(self.tmp, self.pid, rows, [3.0, 1.8])           # not ticked: untouched
        e = audio_lib.load(directory)[0]
        self.assertFalse(e["use"])
        self.assertNotIn("fit_file", e)
        audio_lib.set_mix(directory, 0, True, 0.0, 1.0)                             # the person ticks it
        sfx_plan.place_on_timeline(self.tmp, self.pid, rows, [3.0, 1.8])
        e = audio_lib.load(directory)[0]
        self.assertEqual(e["start"], 3.0)                                           # moves with shot 5
        self.assertTrue(e["fit_file"].endswith("_fit.wav"))
        self.assertEqual(os.path.basename(audio_lib.mix_list(directory)[0]["path"]), e["fit_file"])

    def test_one_broken_ref_does_not_stop_the_others(self):
        """Rà F5 mục 6 (09/10): ffmpeg lỗi ở một shot → ghi `failed`, shot khác vẫn tách."""
        import subprocess
        from core import ref_audio
        sid = self.p.create_scene(self.pid, 8, "S08")
        self.p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, state, ref_video_path) VALUES (?,?,?,?)",
                            (sid, "x", "approved", self.with_sound + ".copy.mp4"))
        self.p.conn.commit()
        import shutil
        shutil.copyfile(self.with_sound, self.with_sound + ".copy.mp4")
        real = ref_audio._extract

        def broken(src, dst, ff):
            if src.endswith(".copy.mp4"):
                raise subprocess.CalledProcessError(1, "ffmpeg", stderr=b"Invalid data found")
            return real(src, dst, ff)
        with mock.patch.object(ref_audio, "_extract", broken):
            res = ref_audio.propose(self.p, self.tmp, self.pid)
        self.assertEqual(res["added"], [5])
        self.assertEqual(res["failed"], [(8, "Invalid data found")])

    def test_changed_ref_removes_the_old_proposal_and_marks_a_used_one(self):
        """Rà F5 mục 7: đổi video ref → đề xuất chưa tích bị gỡ (cả tệp); đã tích → giữ + `ref_stale`; tệp _fit.wav cũ bị xóa."""
        from core import audio_lib, ref_audio
        ref_audio.propose(self.p, self.tmp, self.pid)
        directory = audio_lib.assets_dir(self.tmp, self.pid)
        old_file = os.path.join(directory, audio_lib.load(directory)[0]["file"])
        sid5 = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=5", (self.pid,)).fetchone()[0]
        self.p.conn.execute("UPDATE motion_prompts SET ref_video_path=? WHERE scene_id=?", (self.silent, sid5))
        self.p.conn.commit()
        res = ref_audio.propose(self.p, self.tmp, self.pid)
        self.assertEqual(res["removed"], [5])
        self.assertEqual(audio_lib.load(directory), [])
        self.assertFalse(os.path.exists(old_file))
        self.p.conn.execute("UPDATE motion_prompts SET ref_video_path=? WHERE scene_id=?", (self.with_sound, sid5))
        self.p.conn.commit()
        ref_audio.propose(self.p, self.tmp, self.pid)
        audio_lib.set_mix(directory, 0, True, 0.0, 1.0)
        e = audio_lib.load(directory)[0]
        ref_audio.fit(directory, e, 2.5)
        fitted = os.path.join(directory, e["fit_file"])
        self.assertTrue(os.path.exists(fitted))
        ref_audio.fit(directory, e, 5.0)                                     # no longer stretched → the old copy goes
        self.assertFalse(os.path.exists(fitted))
        audio_lib._save(directory, [e])
        self.p.conn.execute("UPDATE motion_prompts SET ref_video_path=NULL WHERE scene_id=?", (sid5,))
        self.p.conn.commit()
        res = ref_audio.propose(self.p, self.tmp, self.pid)
        self.assertEqual(res["stale_used"], [5])
        self.assertIn("video cũ", audio_lib.load(directory)[0]["ref_stale"])


if __name__ == "__main__":
    unittest.main()
