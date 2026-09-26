"""The crew's skill books raised to ≥ 45/50 (grader report 2026-09-26): the code each book now claims — one class per role.
Every ffmpeg test uses generated media (no provider, no money)."""
import json
import os
import re
import subprocess
import tempfile
import unittest
from unittest import mock

from core import continuity, delivery, director_report, ffmpeg_studio, lineage, performance, prompts, shots, subtitles, voice_direction
from core.db import connect
from core.pipeline import Pipeline

ROOT = os.path.join(os.path.dirname(__file__), "..")


def shot(**kw):
    return dict({"size": "MS", "angle": "eye", "camera_move": "static", "role": "action", "duration_s": 2.0, "characters": ["KELLY"],
                 "performance": {"intensity": 3}}, **kw)


# ---- Đạo diễn ----------------------------------------------------------------------------------------------------------------
class DirectorTests(unittest.TestCase):
    def test_a_rush_written_on_purpose_is_not_flagged(self):
        strong = [shot(performance={"intensity": 4}, duration_s=0.8) for _ in range(3)] + [shot(duration_s=0.8)]
        self.assertTrue(any("chưa kịp thấm" in w for w in performance.warnings(strong)))
        strong[1]["why"] = "cố ý dồn nhịp pha đấu súng"
        self.assertFalse(any("chưa kịp thấm" in w for w in performance.warnings(strong)))

    def test_flat_means_six_shots_in_a_row_on_screen(self):
        # six acted shots at 3 separated by shots without acting are not "in a row" (the old code counted acted shots only)
        broken = []
        for _ in range(6):
            broken += [shot(), shot(performance=None, characters=[])]
        self.assertFalse(any("đường cảm xúc phẳng" in w for w in performance.warnings(broken)))
        self.assertTrue(any("đường cảm xúc phẳng" in w for w in performance.warnings([shot() for _ in range(6)])))

    def test_a_tradeoff_about_something_else_does_not_excuse_a_dropped_line(self):
        gave_up = [("bỏ câu thoại", {2})]
        self.assertEqual(director_report._uncovered(gave_up, [{"chose": "nhạc", "gave_up": "nhạc nền", "why": "x", "scene": 2}]),
                         ["bỏ câu thoại"])
        self.assertEqual(director_report._uncovered(gave_up, [{"chose": "nhịp", "gave_up": "câu thoại của Maxim", "why": "x",
                                                               "scene": 2}]), [])
        self.assertEqual(director_report._uncovered(gave_up, [{"chose": "nhịp", "gave_up": "câu thoại", "why": "x", "scene": 5}]),
                         ["bỏ câu thoại"])                                   # the wrong scene

    def test_the_script_camera_words_are_checked(self):
        with open(os.path.join(ROOT, "samples", "anh_chon_ai.txt"), encoding="utf-8") as f:
            script = f.read()
        with open(os.path.join(ROOT, "tests", "fixtures", "director_anh_chon_ai_run4.json"), encoding="utf-8") as f:
            run = json.load(f)
        self.assertEqual(director_report.report(run, script)["script_angles"], [])      # run 4 kept "sau vai Kenta"
        for sc in run["scenes"]:
            for s in sc["shots"]:
                if s.get("angle") == "ots":
                    s["angle"] = "eye"
        r = director_report.report(run, script)
        self.assertTrue(any(a["wanted"] == "qua vai KENTA" for a in r["script_angles"]))
        self.assertIn("bỏ góc máy kịch bản ghi", r["unrecorded"])

    def test_a_long_film_needs_a_mid_hook(self):
        plan = [shot(duration_s=5.0) for _ in range(8)]                      # 40 s, nothing open after the first hook
        self.assertTrue(director_report.mid_hook_gaps(plan))
        for k in (2, 5):
            plan[k]["hook_mid"] = True
        self.assertEqual(director_report.mid_hook_gaps(plan), [])
        self.assertEqual(director_report.mid_hook_gaps(plan[:3]), [])        # ≤ 20 s: not asked

    def test_knowledge_gap_is_kept_only_with_a_known_value(self):
        scene = {"idx": 1, "knowledge_gap": "ahead", "characters": ["KELLY"]}
        base = {"size": "MS", "role": "action", "image_prompt": "x", "action": "x", "duration_s": 2}
        self.assertEqual(shots.shot_data(scene, base, 1)["knowledge_gap"], "ahead")
        self.assertNotIn("knowledge_gap", shots.shot_data(dict(scene, knowledge_gap="maybe"), base, 1))

    def test_the_intent_pass_reads_no_shot_orders(self):
        full, intent = prompts.role_text("director.md"), prompts.role_text("director.md", intent_only=True)
        self.assertNotIn("<!--", full)
        self.assertNotIn("<!--", intent)
        self.assertLess(len(intent), len(full))
        self.assertNotIn("Mỗi shot có người ghi `performance`", intent)
        self.assertIn("Mỗi shot có người ghi `performance`", full)

    def test_v3_pause_tags(self):
        self.assertEqual(voice_direction.spoken_text("Anh đã nói rồi mà", {"pause_before": "long"}), "[long pause] Anh đã nói rồi mà")
        self.assertEqual(voice_direction.spoken_text("Anh đã nói rồi mà", {"pause_before": True}), "… Anh đã nói rồi mà")
        self.assertEqual(voice_direction.spoken_text("Anh đã nói", {"pause_before": "short"}, model="eleven_multilingual_v2"),
                         "… Anh đã nói")
        self.assertIsNone(voice_direction.clean({"pause_before": "maybe"})[0])


# ---- Quay phim ---------------------------------------------------------------------------------------------------------------
class DpTests(unittest.TestCase):
    def test_mls_can_be_chosen(self):
        self.assertIn("MLS", shots.SIZES)
        self.assertIn("MLS", shots.SIZE_WORDS)
        from core.runner import FRAMING
        self.assertIn("knees", FRAMING["MLS"])
        from core import shot_normalize
        obj = {"scenes": [{"idx": 1, "shots": [{"size": "medium long shot"}]}]}
        shot_normalize.normalize_vocab(obj) if hasattr(shot_normalize, "normalize_vocab") else None
        self.assertEqual(shot_normalize.SIZE_SYN["MEDIUM_LONG_SHOT"], "MLS")

    def test_editing_why_lens_or_weather_makes_the_result_old(self):
        data = {"image_prompt": "x", "size": "MS", "action": "a", "text": "t"}
        self.assertNotEqual(lineage.motion_spec_hash(data), lineage.motion_spec_hash(dict(data, why="dolly zoom vào mặt Kelly")))
        self.assertNotEqual(lineage.image_spec_hash(data, [], "9:16"), lineage.image_spec_hash(dict(data, lens_mm=85), [], "9:16"))
        self.assertNotEqual(lineage.image_spec_hash(data, [], "9:16"), lineage.image_spec_hash(dict(data, weather="rain"), [], "9:16"))
        self.assertEqual(lineage.image_spec_hash(data, [], "9:16"), lineage.image_spec_hash(dict(data), [], "9:16"))   # absent = same

    def test_the_lighting_template_is_checked(self):
        good = {"idx": 1, "lighting": "moonlight from frame-right (cold, ~7000K look), key:fill 8:1, low-key"}
        self.assertEqual(continuity.lighting_warnings([good]), [])
        self.assertIn("thiếu", continuity.lighting_warnings([{"idx": 2, "lighting": "dramatic"}])[0])
        self.assertIn("chưa có", continuity.lighting_warnings([{"idx": 3}])[0])


# ---- Dựng --------------------------------------------------------------------------------------------------------------------
def _ff():
    return ffmpeg_studio.find_ffmpeg()


def _rms(src, a, b, filt):
    err = subprocess.run([_ff(), "-ss", str(a), "-t", str(b - a), "-i", src, "-af",
                          filt + ",astats=measure_perchannel=0:measure_overall=RMS_level", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    return float(re.findall(r"RMS level dB: (-?[\d.]+)", err)[-1])


class EditorTests(unittest.TestCase):
    def test_subtitle_readability_rules(self):
        cues = [subtitles.Cue(0.0, 0.5, "Ừ."), subtitles.Cue(0.52, 3.0, "Anh đi đây."), subtitles.Cue(3.5, 6.5, "Không được đâu, em ơi.")]
        flags = {d["i"]: d for d in subtitles.density(cues, cuts=[5.0])}
        self.assertTrue(flags[0]["brief"] and flags[0]["close"])        # 0,5 s on screen, 1 frame before the next line
        self.assertEqual(flags[2]["across_cut"], 5.0)                     # 1,5 s each side of a cut
        self.assertNotIn(1, flags)

    def test_the_default_subtitle_is_bigger_than_before(self):
        self.assertGreaterEqual(subtitles.SIZES["M"][1], 0.08)             # measured: 0,065 gave a 2,1 % cap height

    def test_karaoke_lines_share_the_time_by_letters(self):
        text = subtitles.karaoke_text(r"Anh đã nói\Nrồi mà", 2.0)
        self.assertIn(r"\N", text)
        total = sum(int(x) for x in re.findall(r"\\kf(\d+)", text))
        self.assertTrue(170 <= total <= 180, total)                          # 90 % of 2 s, rounded down word by word
        ass = subtitles.to_ass([subtitles.Cue(0, 2, "Anh đã nói")], 1080, 1920, subtitles.Font("x.ttf", "X", "X", True), karaoke=True)
        self.assertIn(subtitles._bgr(subtitles.KARAOKE_WAIT), ass)

    def test_breaths_of_the_same_moment_are_one(self):
        self.assertEqual(delivery.merge_breaths([12.0, 30.0], [12.4]), [12.4, 30.0])

    def test_speed_fields_only_on_a_silent_shot(self):
        self.assertEqual(shots.clean_retime({"speed": 0.5, "freeze_end_s": 0.4, "dialogue": []}), {"speed": 0.5, "freeze_end_s": 0.4})
        self.assertEqual(shots.clean_retime({"speed": 0.5, "dialogue": [{"speaker": "KELLY", "text": "Đi thôi"}]}), {})
        self.assertEqual(shots.clean_retime({"speed": 0.1, "freeze_end_s": 3}), {})

    def test_a_slowed_shot_fills_its_length_with_a_quarter_second_freeze(self):
        d = tempfile.mkdtemp()
        src, out = os.path.join(d, "s.mp4"), os.path.join(d, "o.mp4")
        subprocess.run([_ff(), "-y", "-f", "lavfi", "-i", "testsrc=size=90x160:rate=24:duration=5", "-pix_fmt", "yuv420p", src],
                       capture_output=True)
        want, speed, freeze = 2.0, 0.5, 0.25
        vf = shots.retime_filter(speed, freeze)
        subprocess.run([_ff(), "-y", "-t", f"{(want - freeze) * speed:.2f}", "-i", src, "-vf", vf, "-t", f"{want:.2f}", "-an", out],
                       capture_output=True)
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(out), want, delta=0.1)

    def test_a_still_is_converted_with_the_bt709_matrix(self):
        from PIL import Image
        d = tempfile.mkdtemp()
        Image.new("RGB", (64, 64), (255, 0, 0)).save(os.path.join(d, "r.png"))
        v, out = os.path.join(d, "v.mp4"), os.path.join(d, "o.mp4")
        subprocess.run([_ff(), "-y", "-f", "lavfi", "-i", "color=blue:s=64x64:d=0.5", *ffmpeg_studio._ENCODE, v], capture_output=True)
        ffmpeg_studio.append_still(v, os.path.join(d, "r.png"), 0.5, out)
        raw = subprocess.run([_ff(), "-v", "error", "-sseof", "-0.2", "-i", out, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "yuv420p",
                              "-"], capture_output=True).stdout
        self.assertAlmostEqual(raw[64 * 20 + 20], 63, delta=3)             # BT.709 red; BT.601 would be 81

    def test_music_ducks_8_to_12_db_under_a_voice(self):
        d = tempfile.mkdtemp()
        v = os.path.join(d, "v.mp4")
        subprocess.run([_ff(), "-y", "-f", "lavfi", "-i", "color=black:s=64x64:d=8", "-f", "lavfi", "-i",
                        "anoisesrc=color=brown:amplitude=0.3:d=8:seed=7,lowpass=f=250", "-shortest", "-c:v", "libx264", *ffmpeg_studio.AAC, v],
                       capture_output=True)
        for vol in (2.0, 2.5):                                            # voice at about −18 and −16 dBFS RMS, like the TTS lines
            voice, out = os.path.join(d, "voice.wav"), os.path.join(d, "o.mp4")
            subprocess.run([_ff(), "-y", "-f", "lavfi", "-i", f"sine=frequency=1000:d=3,volume={vol}", voice], capture_output=True)
            ffmpeg_studio.run(ffmpeg_studio.build_extras_mix_cmd(v, [{"path": voice, "start": 3.0, "volume": 1.0}], out, has_audio=True,
                                                                ffmpeg=_ff(), duck=True))
            low = "lowpass=f=250,lowpass=f=250"
            drop = _rms(out, 0.5, 2.5, low) - _rms(out, 3.8, 5.5, low)
            self.assertTrue(7.5 <= drop <= 12.5, (vol, drop))

    def test_text_under_an_interface_band_is_found(self):
        from PIL import Image, ImageDraw
        from core import viewer_check
        plain = Image.new("RGB", (108, 192), (40, 40, 40))
        texted = plain.copy()
        ImageDraw.Draw(texted).rectangle([20, 170, 80, 185], fill=(255, 255, 255))     # a line in the bottom 35 %
        self.assertEqual(viewer_check.text_bands(texted, plain), ["bottom"])
        mid = plain.copy()
        ImageDraw.Draw(mid).rectangle([20, 80, 70, 95], fill=(255, 255, 255))
        self.assertEqual(viewer_check.text_bands(mid, plain), [])

    def test_the_cover_is_the_hero_shot(self):
        p = Pipeline(connect())
        pid = p.create_project("cover")
        ids = []
        for i, role in enumerate(("normal", "hero", "normal"), 1):
            sid = p.create_scene(pid, i, f"s{i}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"characters": ["KELLY"], "shot_role": role}), sid))
            ids.append(sid)
        man = {"timeline": [{"scene_id": s, "seconds": 2.0} for s in ids], "transition": "cut"}
        p.conn.execute("INSERT INTO outputs (project_id, kind, path, manifest, created_at) VALUES (?,?,?,?,?)",
                       (pid, "final", "x.mp4", json.dumps(man), "2026-09-26"))
        self.assertEqual(delivery.cover_moment(p, pid), {"t": 3.0, "scene_id": ids[1], "why": "shot ⭐"})


if __name__ == "__main__":
    unittest.main()
