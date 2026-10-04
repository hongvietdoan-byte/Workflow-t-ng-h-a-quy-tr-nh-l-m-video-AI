"""GĐ-G phần 2 (âm thanh & xuất bản): D5 nhớ "không dùng nhạc", D6 render ra file tạm + khóa, D7 lớp phụ đề/card/xuất bản bị đánh
dấu cũ, D8 dùng lại bản dịch + câu sửa tay, D2 phụ đề theo đúng timeline đã dựng, AU-g cờ cận mặt người nói, AU-f kiểm giọng."""
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
import wave
from types import SimpleNamespace
from unittest import mock

from core import autopilot, delivery, ffmpeg_studio, music, storyboard_gate, subtitles, voice_check
from core.subtitles import Cue
from tests.test_autopilot import Setup
from tests.test_keep_audio import ffmpeg_available
from tests.test_subtitles import clips_with_dialogue


class CountingLlm:
    """Translates by upper-casing; counts calls (a call = money)."""
    def __init__(self):
        self.calls = 0

    def complete(self, prompt, images=()):
        from core.llm_runner import LlmReply
        self.calls += 1
        body = json.loads(prompt.split("```json\n", 1)[1].split("\n```", 1)[0])
        return LlmReply(json.dumps({"cues": [{"id": x["id"], "text": x["text"].upper()} for x in body]}), 10, 10)


class NoMusicTests(Setup):
    def test_no_music_is_remembered_and_the_automatic_run_does_not_pay_for_a_track(self):
        ctx = self.build()
        music.set_off(self.p, self.pid, True)
        with mock.patch.object(ctx.audio, "generate_music", side_effect=AssertionError("paid music generated")):
            self.assertIsNone(autopilot._music_phase(self.p, self.pid, ctx))
        drafts_dir, selected = music.project_dirs(self.data, self.pid)
        self.assertEqual(music.load_drafts(drafts_dir), [])
        self.assertEqual(os.listdir(selected), [])
        self.assertIn(("Nhạc nền", 1, 1), autopilot.progress(self.p, self.pid, self.data))   # a choice, not a gap

    def test_choosing_a_track_again_turns_music_back_on_but_keeps_the_library_mode(self):
        self.build()
        music.set_off(self.p, self.pid, True)
        music.set_off(self.p, self.pid, False)
        self.assertFalse(music.is_off(self.p, self.pid))
        self.p.conn.execute("UPDATE projects SET music_mode='library' WHERE id=?", (self.pid,))
        music.set_off(self.p, self.pid, False)
        self.assertEqual(self.p.project(self.pid)["music_mode"], "library")


class AtomicRenderTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.out = os.path.join(self.dir, "FINAL_VIDEO.mp4")
        with open(self.out, "wb") as f:
            f.write(b"old good render")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_a_failed_render_keeps_the_old_file_and_leaves_no_temp(self):
        def half_written_then_fail(cmd):
            with open(cmd[-1], "wb") as f:
                f.write(b"half")
            raise ffmpeg_studio.FFmpegError("boom")
        with mock.patch.object(ffmpeg_studio, "find_ffmpeg", return_value="ffmpeg"), \
                mock.patch.object(ffmpeg_studio, "run", side_effect=half_written_then_fail):
            with self.assertRaises(ffmpeg_studio.FFmpegError):
                ffmpeg_studio.render_final(["a", "b"], self.out, [5, 5])
        self.assertEqual(open(self.out, "rb").read(), b"old good render")
        self.assertEqual(sorted(os.listdir(self.dir)), ["FINAL_VIDEO.mp4"])

    def test_a_finished_render_replaces_the_file_and_moves_its_srt(self):
        with ffmpeg_studio.atomic_output(self.out) as staged:
            self.assertNotEqual(staged, self.out)
            open(staged, "wb").write(b"new")
            open(os.path.splitext(staged)[0] + ".srt", "w").write("1")
        self.assertEqual(open(self.out, "rb").read(), b"new")
        self.assertEqual(sorted(os.listdir(self.dir)), ["FINAL_VIDEO.mp4", "FINAL_VIDEO.srt"])

    def test_an_empty_result_is_not_taken_for_a_render(self):
        with self.assertRaises(ffmpeg_studio.FFmpegError):
            with ffmpeg_studio.atomic_output(self.out) as staged:
                open(staged, "wb").close()
        self.assertEqual(open(self.out, "rb").read(), b"old good render")


class RenderLockTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.data, ignore_errors=True)

    def test_one_render_per_project_nested_calls_share_it_and_it_is_released(self):
        with delivery.render_lock(self.data, 1):
            with delivery.render_lock(self.data, 1):          # deliver → render → subtitles in one thread
                pass
            import threading
            err = []
            t = threading.Thread(target=lambda: err.append(self._try()))
            t.start()
            t.join()
            self.assertIn("đang được dựng", err[0])
        self.assertIsNone(self._try())                         # released after the block
        with delivery.render_lock(self.data, 2):               # another project is not blocked
            pass

    def _try(self):
        try:
            with delivery.render_lock(self.data, 1):
                return None
        except ValueError as e:
            return str(e)

    def test_a_lock_left_by_a_dead_render_is_taken_over(self):
        path = os.path.join(delivery.output_dir(self.data, 1), ".render.lock")
        open(path, "w").write("123 old")
        old = time.time() - delivery.LOCK_STALE_SEC - 5
        os.utime(path, (old, old))
        with delivery.render_lock(self.data, 1):
            pass
        self.assertFalse(os.path.exists(path))


class StaleLayerTests(Setup):
    def _rows(self, final_state):
        p, pid = self.p, self.pid
        out = delivery.output_dir(self.data, pid)
        paths = {k: os.path.join(out, n) for k, n in (("final", "FINAL_VIDEO.mp4"), ("subtitle", "FINAL_VIDEO_sub_src.mp4"),
                                                      ("endcard", "FINAL_VIDEO_end.mp4"), ("export", "FINAL_VIDEO_1080x1080.mp4"))}
        for path in paths.values():
            open(path, "wb").write(b"x")
        fin = delivery.record(p, pid, "final", paths["final"], None, {})
        sub = delivery.record(p, pid, "subtitle", paths["subtitle"], fin, {"settings": subtitles.get_settings(p, pid)})
        card = delivery.record(p, pid, "endcard", paths["endcard"], sub, {"card": delivery.get_settings(p, pid)["end_card"]})
        delivery.record(p, pid, "export", paths["export"], card, {"spec": {"w": 1080, "h": 1080}})
        return paths

    def _stale(self):
        with mock.patch.object(delivery.lineage, "final_status", return_value={"state": "fresh", "reasons": [], "output_id": None,
                                                                               "path": None}):
            st = delivery.status(self.p, self.pid, self.data)
        return {x["kind"]: x["stale"] for x in st["layers"]}, st

    def test_changing_subtitles_or_the_card_marks_the_layers_made_from_them_old(self):
        self.build()
        subtitles.save_settings(self.p, self.pid, {**subtitles.DEFAULTS, "enabled": True})
        s = delivery.get_settings(self.p, self.pid)
        s["end_card"] = {**s["end_card"], "enabled": True, "title": "Hết"}
        delivery.save_settings(self.p, self.pid, s)
        self._rows(None)
        stale, _ = self._stale()
        self.assertEqual(stale, {"subtitle": None, "endcard": None, "export": None})
        subtitles.save_settings(self.p, self.pid, {**subtitles.DEFAULTS, "enabled": True, "color": "yellow"})
        stale, st = self._stale()
        self.assertEqual(stale["subtitle"], "thiết lập phụ đề đã đổi")
        self.assertEqual(stale["export"], "card cuối của bản gốc đã cũ")      # export ← card ← old subtitles
        self.assertTrue(st["best_stale"])                                      # the deliverable itself says "⚠ cũ"
        s["end_card"]["title"] = "The End"
        delivery.save_settings(self.p, self.pid, s)
        self.assertEqual(self._stale()[0]["endcard"], "card cuối đã đổi")


class SubtitleTextTests(Setup):
    def test_translations_are_reused_and_hand_fixes_win(self):
        self.build()
        cues = [Cue(0, 1, "xin chào", "KELLY", 1), Cue(1, 2, "đi thôi", "KENTA", 1)]
        llm = CountingLlm()
        first = subtitles.localize(llm, cues, "en", self.data, self.pid)
        self.assertEqual([c.text for c in first], ["XIN CHÀO", "ĐI THÔI"])
        self.assertEqual(llm.calls, 1)
        again = subtitles.localize(None, cues, "en", self.data, self.pid)       # no Claude needed: nothing new
        self.assertEqual([c.text for c in again], ["XIN CHÀO", "ĐI THÔI"])
        self.assertEqual(subtitles.remember_edits(self.data, self.pid, "en", [(cues[0], "Hello there")]), 1)
        fixed = subtitles.localize(None, cues, "en", self.data, self.pid)
        self.assertEqual(fixed[0].text, "Hello there")
        changed = [Cue(0, 1, "xin chào", "KELLY", 1), Cue(1, 2, "chạy đi", "KENTA", 1)]   # only the changed line is sent
        subtitles.localize(llm, changed, "en", self.data, self.pid)
        self.assertEqual(llm.calls, 2)

    def test_a_source_language_fix_is_kept_too(self):
        self.build()
        cue = Cue(0, 1, "Boo yah", "KELLY", 1)
        subtitles.remember_edits(self.data, self.pid, "src", [(cue, "Booyah!")])
        self.assertEqual(subtitles.localize(None, [cue], "src", self.data, self.pid)[0].text, "Booyah!")


class RenderedTimelineTests(Setup):
    def test_subtitles_follow_the_render_s_own_clips_and_seconds(self):
        clips_with_dialogue(self, {1: "LYRA: Một.", 2: "KAEL: Hai.", 3: "ORIN: Ba."})
        rows = self.p.conn.execute("SELECT id, idx FROM scenes WHERE project_id=? ORDER BY idx", (self.pid,)).fetchall()
        out = os.path.join(delivery.output_dir(self.data, self.pid), "FINAL_VIDEO.mp4")
        open(out, "wb").write(b"x")
        # the person left clip 2 out and gave clip 1 only 2 seconds
        timeline = [{"idx": rows[0]["idx"], "scene_id": rows[0]["id"], "seconds": 2.0},
                    {"idx": rows[2]["idx"], "scene_id": rows[2]["id"], "seconds": 6.0}]
        delivery.record(self.p, self.pid, "final", out, None, {"timeline": timeline, "transition": "cut", "fade": 1.0})
        cues = delivery.subtitle_cues(self.p, self.pid, self.data)
        self.assertEqual([c.speaker for c in cues], ["LYRA", "ORIN"])          # no line of the clip that is not in the video
        self.assertLess(cues[0].end, 2.0)
        self.assertTrue(2.0 <= cues[1].start < 8.0)                             # clip 3 starts at 2 s, not at 12 s

    def test_a_clip_waiting_for_review_is_left_out_like_the_render_does(self):
        clips_with_dialogue(self, {1: "LYRA: Một.", 2: "KAEL: Hai.", 3: "ORIN: Ba."})
        sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=2", (self.pid,)).fetchone()["id"]
        self.p.conn.execute("INSERT INTO jobs (project_id, scene_id, type, state, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                            (self.pid, sid, "video_gen", "pending_review", "t", "t"))
        self.p.conn.commit()
        self.assertEqual([c.speaker for c in subtitles.build_cues(self.p, self.data, self.pid)], ["LYRA", "ORIN"])


class LipSyncFlagTests(unittest.TestCase):
    def test_a_close_shot_of_the_speaker_is_flagged_other_framings_are_not(self):
        line = [{"speaker": "KELLY", "text": "Đi thôi!"}]
        self.assertTrue(storyboard_gate.lip_sync_risk({"size": "CU", "angle": "eye", "characters": ["KELLY"], "dialogue": line}))
        self.assertFalse(storyboard_gate.lip_sync_risk({"size": "WS", "angle": "eye", "characters": ["KELLY"], "dialogue": line}))
        self.assertFalse(storyboard_gate.lip_sync_risk({"size": "MCU", "angle": "ots", "characters": ["KELLY"], "dialogue": line}))
        self.assertFalse(storyboard_gate.lip_sync_risk({"size": "CU", "angle": "eye", "characters": ["KENTA"], "dialogue": line}))  # reaction
        self.assertFalse(storyboard_gate.lip_sync_risk({"size": "CU", "angle": "eye", "characters": ["KELLY"], "dialogue": []}))

    def test_the_director_is_told_there_is_no_lip_sync(self):
        text = open(os.path.join(os.path.dirname(__file__), "..", "prompts", "17_director_shots.md"), encoding="utf-8").read()
        self.assertIn("Không có khớp môi", text)


class VoiceCheckTests(unittest.TestCase):
    def test_length_rules(self):
        self.assertEqual(voice_check.length_problems("xin chào các bạn", 1.2, []), [])
        self.assertIn("quá ngắn", voice_check.length_problems("một hai ba bốn năm sáu bảy tám chín mười", 0.6, [])[0])
        self.assertIn("quá dài", voice_check.length_problems("xin chào", 6.0, [])[0])
        self.assertIn("ngắt quãng", voice_check.length_problems("một hai ba bốn năm sáu", 3.0, [(1.0, 2.1)])[0])
        self.assertEqual(voice_check.length_problems("một hai ba bốn năm sáu", 3.0, [(2.5, None)]), [])   # trailing silence is fine

    def test_heard_words_against_the_line(self):
        self.assertEqual(voice_check.compare("Loot xong rồi leo rank thôi", "loot xong rồi leo rank thôi")["problems"], [])
        cut = voice_check.compare("Kelly, Kenta và Maxim, tập trung ở tháp đồng hồ ngay", "Kelly Kenta và Maxim tập trung")
        self.assertTrue(cut["missing_end"])
        wrong = voice_check.compare("trận này phải Booyah", "chạn nầy phai bu da")
        self.assertTrue(any("khác câu gốc" in x for x in wrong["problems"]))

    @unittest.skipUnless(ffmpeg_available(), "ffmpeg not installed")
    def test_project_check_flags_a_cut_voice_keeps_it_and_does_not_recheck(self):
        data = tempfile.mkdtemp()
        from core import audio_lib
        directory = audio_lib.assets_dir(data, 1)

        def tone(name, seconds):
            path = os.path.join(directory, name)
            subprocess.run([ffmpeg_studio.find_ffmpeg(), "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"sine=f=300:d={seconds}",
                            path], check=True)
            return name
        audio_lib._save(directory, [
            {"kind": "tts", "dialogue": True, "state": "succeeded", "file": tone("ok.wav", 1.5), "text": "xin chào các bạn nhé",
             "scene_id": 1, "line": 1},
            {"kind": "tts", "dialogue": True, "state": "succeeded", "file": tone("cut.wav", 0.4),
             "text": "một hai ba bốn năm sáu bảy tám chín mười", "scene_id": 1, "line": 2}])
        heard = mock.Mock(side_effect=lambda path: "xin chào các bạn nhé" if path.endswith("ok.wav") else "một hai")
        res = voice_check.check_project(data, 1, asr=heard)
        self.assertEqual((res["checked"], res["bad"]), (2, 1))
        bad = voice_check.bad_lines(data, 1)
        self.assertEqual([b["file"] for b in bad], ["cut.wav"])
        self.assertTrue(os.path.exists(os.path.join(directory, "cut.wav")))            # flagged, never deleted
        self.assertEqual(voice_check.check_project(data, 1, asr=heard)["checked"], 0)   # unchanged files are not checked again
        shutil.rmtree(data, ignore_errors=True)

    def test_the_automatic_run_does_not_pay_to_redo_voices_before_the_real_test(self):
        from core import features
        self.assertFalse(features.FEATURES["voice_check_redo"]["verified"])
        p = SimpleNamespace()
        ctx = SimpleNamespace(data_dir=tempfile.mkdtemp(), audio=object())
        with mock.patch.object(voice_check, "check_project", return_value={"checked": 1, "bad": 1, "asr": False}), \
                mock.patch.object(voice_check, "redo", side_effect=AssertionError("paid redo")), \
                mock.patch.object(autopilot, "_d") as warn, mock.patch.dict(os.environ, {"FEATURE_VOICE_CHECK_REDO": ""}):
            autopilot._check_voices(p, 1, ctx)
        self.assertIn("nghi lỗi", warn.call_args[0][4])       # _d(p, pid, stage, severity, message, code)


class VoiceRedoTests(unittest.TestCase):
    """S14.3 B1b (T7): the 🔁 redo of flagged voices deleted the finished line BEFORE the new one existed (a failed / refused redo lost
    the voice) and had no count of its own (MAX_RESENDS is for provider errors; the person's button skipped it)."""

    def setUp(self):
        from core import audio_lib, voice
        from core.db import connect
        from core.pipeline import Pipeline
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("redo")
        sid = self.p.create_scene(self.pid, 1, "s")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                            (json.dumps({"shot_no": 1, "dialogue": [{"speaker": "KELLY", "text": "Đi thôi."}]}, ensure_ascii=False), sid))
        self.p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, 'KELLY', 'x')", (self.pid,))
        self.p.conn.commit()
        voice.set_profile(self.p.conn, self.pid, "KELLY", {"voice_id": 71, "voice_name": "Kelly"})
        self.data = tempfile.mkdtemp()
        self.dir = audio_lib.assets_dir(self.data, self.pid)
        self.audio = self.Audio()
        voice.generate(self.p.conn, self.pid, self.audio, self.data, ledger=False)
        audio_lib.refresh(self.audio, self.dir)
        self.first = self.lines()[0]["file"]
        self.flag()

    def tearDown(self):
        shutil.rmtree(self.data, ignore_errors=True)

    class Audio(music.MockAudioProvider):
        def __init__(self):
            super().__init__()
            self.calls, self.fail_send, self.fail_make = 0, False, False

        def generate_tts(self, *a, **k):
            from core.providers import ProviderError
            self.calls += 1
            if self.fail_send:
                raise ProviderError("HTTP 400", code="bad_request")
            return super().generate_tts(*a, **k)

        def status(self, category, asset_id):
            from core.adapters.clipai_audio import AudioStatus
            if self.fail_make:
                return AudioStatus("failed", None, None, "voice failed")
            return super().status(category, asset_id)

    def lines(self):
        from core import audio_lib
        return [e for e in audio_lib.load(self.dir) if e["kind"] == "tts" and e.get("scene_id")]

    def flag(self):
        from core import audio_lib
        items = audio_lib.load(self.dir)
        for e in items:
            if e["kind"] == "tts" and e.get("state") == "succeeded":
                e["check"] = {"ok": False, "problems": ["quá ngắn"]}
        audio_lib._save(self.dir, items)

    def test_a_failed_redo_keeps_the_old_voice(self):
        self.audio.fail_send = True
        voice_check.redo(self.p.conn, self.pid, self.audio, self.data)
        lines = self.lines()
        self.assertEqual([(e["state"], e["file"]) for e in lines], [("succeeded", self.first)])   # used to be gone
        self.assertTrue(os.path.exists(os.path.join(self.dir, self.first)))
        self.assertIn("HTTP 400", lines[0].get("redo_error") or "")

    def test_the_old_voice_stays_until_the_new_one_is_made(self):
        from core import audio_lib, voice
        self.audio.fail_make = True
        r = voice_check.redo(self.p.conn, self.pid, self.audio, self.data)
        self.assertEqual(r["sent"], 1)
        self.assertTrue(os.path.exists(os.path.join(self.dir, self.first)))                 # the new one is still being made
        audio_lib.refresh(self.audio, self.dir)                                             # … and fails at the provider
        voice.generate(self.p.conn, self.pid, self.audio, self.data, ledger=False)          # any later pass settles it
        self.assertEqual([(e["state"], e["file"]) for e in self.lines()], [("succeeded", self.first)])
        self.audio.fail_make = False
        self.flag()
        voice_check.redo(self.p.conn, self.pid, self.audio, self.data)
        audio_lib.refresh(self.audio, self.dir)
        voice_check.settle_redos(self.dir)
        lines = self.lines()
        self.assertEqual(len(lines), 1)                                                     # the new voice replaced the old one
        self.assertNotEqual(lines[0]["file"], self.first)
        self.assertFalse(os.path.exists(os.path.join(self.dir, self.first)))
        self.assertEqual(lines[0]["redos"], 2)

    def superseded(self):
        from core import audio_lib
        items = audio_lib.load(self.dir)
        items[0].update(state="superseded", use=True, start=0.0, duration_ms=1500)
        audio_lib._save(self.dir, items)
        return items

    def test_an_old_voice_waiting_for_its_redo_is_not_a_flagged_line(self):
        self.superseded()
        self.assertEqual(voice_check.bad_lines(self.data, self.pid), [])          # the 🔁 button and "X/Y" skip it
        self.assertEqual(voice_check.redo_counts(self.data, self.pid), (0, 0))

    def test_the_final_check_ignores_an_old_voice_waiting_for_its_redo(self):
        from core import final_qc
        items = self.superseded() + [{"kind": "sound_effect", "use": True, "label": "AI: boom", "anchor_idx": 1, "start": 0.5,
                                      "duration_ms": 500, "state": "succeeded"}]
        self.assertEqual([i["code"] for i in final_qc.check_effects(items)], [])

    def test_the_mix_list_hides_an_old_voice_waiting_for_its_redo(self):
        from core import audio_lib
        items = self.superseded()
        self.assertEqual(audio_lib.mix_rows(items), [])
        src = open(os.path.join(os.path.dirname(__file__), "..", "dashboard", "steps", "step5.py"), encoding="utf-8").read()
        self.assertIn("audio_lib.mix_rows(items)", src)                         # the Bước 5 list (with its Xóa button) uses it

    def test_the_redo_count_is_kept_per_line_and_capped(self):
        from core import audio_lib
        for n in range(voice_check.MAX_REDOS):
            r = voice_check.redo(self.p.conn, self.pid, self.audio, self.data)
            self.assertEqual(r["sent"], 1)
            audio_lib.refresh(self.audio, self.dir)
            voice_check.settle_redos(self.dir)
            self.assertEqual(self.lines()[0]["redos"], n + 1)
            self.flag()
        self.assertEqual(voice_check.redo_counts(self.data, self.pid), (voice_check.MAX_REDOS, voice_check.MAX_REDOS))
        calls = self.audio.calls
        r = voice_check.redo(self.p.conn, self.pid, self.audio, self.data)
        self.assertEqual((r["sent"], self.audio.calls), (0, calls))                        # refused: nothing paid
        self.assertEqual(len(r["refused"]), 1)
        self.assertIn(f"{voice_check.MAX_REDOS} lần", r["refused"][0])
        self.assertEqual(self.lines()[0]["state"], "succeeded")                             # the old voice is still there


class PreferredVietnameseVoiceTests(unittest.TestCase):
    """User choice 2026-09-24: the 4 team clones with the 'VN' suffix first (2 male, 2 female) — the API gives them no language."""
    OFFICIAL = [{"id": 30002, "name": "Xinghe Jiang", "languages": ["en", "vi"], "labels": {"gender": "male"}},
                {"id": 11, "name": "Rachel", "languages": ["en"], "labels": {"gender": "female"}}]
    TEAM = [{"id": 64, "name": "ClipAI_KELLY", "languages": [], "labels": {}},
            {"id": 70, "name": "ClipAI_Voice Kelly VN", "languages": [], "labels": {}},
            {"id": 69, "name": "ClipAI_voice Hip VN", "languages": [], "labels": {}},
            {"id": 30168, "name": "ClipAI_Voice Hip VN 2", "languages": [], "labels": {}},
            {"id": 71, "name": "ClipAI_Voice girl ingame VN", "languages": [], "labels": {}},
            {"id": 72, "name": "ClipAI_voice boy ingame VN", "languages": [], "labels": {}}]

    def test_the_four_vn_voices_lead_with_their_gender_then_other_vietnamese_voices(self):
        from core import voice
        pool = voice.casting_pool(self.OFFICIAL + self.TEAM)
        self.assertEqual([v["id"] for v in pool], [72, 30168, 71, 70, 30002])     # KELLY (no 'VN', no language) is not offered;
        self.assertNotIn(69, [v["id"] for v in voice.library(type("P", (), {                # voice Hip VN retired 2026-09-29 (hum)
            "voice_actors": lambda s, owner=None, game_code=None, **_: list(self.TEAM)})())])
        self.assertEqual([voice.voice_gender(v) for v in pool[:4]], ["male", "male", "female", "female"])
        self.assertEqual(voice.display_name(pool[3]), "Voice Kelly VN")

    def test_library_reads_the_official_voices_and_the_team_voices(self):
        from core import voice
        from core.providers import ProviderError
        calls = []

        class Provider:
            def voice_actors(inner, owner=None, game_code=None, **_):
                calls.append((owner, game_code))
                return list(self.TEAM) if game_code == "FF" else list(self.OFFICIAL)
        lib = voice.library(Provider())
        self.assertIn(("official", None), calls)
        self.assertIn((None, "FF"), calls)
        self.assertEqual(lib[0]["id"], 72)
        self.assertEqual(lib[0]["team"], "FF")

        class NoTeam(Provider):
            def voice_actors(inner, owner=None, game_code=None, **_):
                if game_code:
                    raise ProviderError("down")
                return list(self.OFFICIAL)
        self.assertEqual([v["id"] for v in voice.library(NoTeam())], [30002, 11])   # official voices still shown

    def test_the_adapter_reads_every_page(self):
        from core.adapters.clipai_audio import ClipAIAudioProvider
        prov = ClipAIAudioProvider("t", transport=lambda *a, **k: None)
        pages = {1: [{"id": i} for i in range(100)], 2: [{"id": i} for i in range(100, 118)]}
        prov.client.get = lambda path, params: {"items": pages.get(params["page"], []), "total": 118}
        self.assertEqual(len(prov.voice_actors(owner="official")), 118)


if __name__ == "__main__":
    unittest.main()
