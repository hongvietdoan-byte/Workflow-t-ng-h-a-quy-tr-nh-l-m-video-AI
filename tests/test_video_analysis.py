import os
import subprocess
import tempfile
import unittest
from unittest import mock

from core import llm_runner, video_analysis as va
from core.ffmpeg_studio import FFmpegNotFound
from tests.test_keep_audio import ffmpeg_available


@unittest.skipUnless(ffmpeg_available(), "ffmpeg not installed")
class RealVideoTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ff = va.find_ffmpeg()
        self.src = os.path.join(self.dir, "src.mp4")
        subprocess.run([self.ff, "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=d=6:s=320x180:r=24",
                        "-pix_fmt", "yuv420p", self.src], check=True)

    def test_probe_reads_duration_and_resolution(self):
        meta = va.probe(self.src)
        self.assertAlmostEqual(meta["duration_sec"], 6.0, delta=0.5)
        self.assertEqual((meta["width"], meta["height"]), (320, 180))

    def test_extract_frames_samples_the_requested_count_spread_across_the_clip(self):
        frames = va.extract_frames(self.src, os.path.join(self.dir, "frames"), count=5)
        self.assertEqual(len(frames), 5)
        for f in frames:
            self.assertTrue(os.path.exists(f))
            self.assertGreater(os.path.getsize(f), 0)

    def test_extract_frames_clamps_to_max_frames(self):
        frames = va.extract_frames(self.src, os.path.join(self.dir, "frames2"), count=999)
        self.assertLessEqual(len(frames), va.MAX_FRAMES)

    def test_a_non_video_file_raises_a_clear_error(self):
        bad = os.path.join(self.dir, "not_a_video.mp4")
        with open(bad, "wb") as f:
            f.write(b"hello, not a video")
        with self.assertRaises(va.VideoAnalysisError) as ctx:
            va.extract_frames(bad, os.path.join(self.dir, "frames3"))
        self.assertEqual(ctx.exception.code, "bad_video")


class PromptAndAnalyzeTests(unittest.TestCase):
    def test_prompt_names_the_character_and_requires_evidence_tags_on_every_claim(self):
        text = va.build_prompt("KELLY", {"duration_sec": 12.0, "width": 1280, "height": 720})
        self.assertIn("KELLY", text)
        for tag in ("[OBSERVED]", "[EXPLICIT]", "[INFERRED]", "[UNKNOWN]"):
            self.assertIn(tag, text)
        self.assertIn("không tự suy diễn", text)

    def test_prompt_asks_for_phases_ui_marks_and_a_never_draw_list(self):
        text = va.build_prompt("KENTA", {"duration_sec": 30.0})
        for part in ("Các giai đoạn theo thời gian", "Chỉ báo giao diện", "Danh sách không được vẽ", "Tương tác"):
            self.assertIn(part, text)

    def test_prompt_appends_the_viewers_note_when_given(self):
        text = va.build_prompt("KELLY", {}, note="chỉ nhìn skill chủ động, bỏ qua trang phục")
        self.assertIn("chỉ nhìn skill chủ động", text)

    def test_analyze_sends_every_frame_as_a_labelled_image_and_returns_the_reply_text(self):
        seen = {}

        class Spy:
            def complete(self, prompt, images=()):
                seen["images"] = list(images)
                return llm_runner.LlmReply("phân tích giả lập", 10, 5)

        frames = ["a.jpg", "b.jpg", "c.jpg"]
        text = va.analyze(Spy(), "KELLY", frames, {"duration_sec": 9.0})
        self.assertEqual(text, "phân tích giả lập")
        self.assertEqual(len(seen["images"]), 3)
        self.assertEqual([p for _, p in seen["images"]], frames)

    def test_analyze_rejects_an_empty_reply(self):
        class Empty:
            def complete(self, prompt, images=()):
                return llm_runner.LlmReply("   ", 10, 5)

        with self.assertRaises(llm_runner.LlmError):
            va.analyze(Empty(), "KELLY", ["a.jpg"], {})

    def test_analyze_needs_at_least_one_frame(self):
        with self.assertRaises(va.VideoAnalysisError):
            va.analyze(llm_runner.MockLlm(), "KELLY", [], {})

    def test_the_mock_provider_answers_this_prompt_shape_too(self):
        text = va.analyze(llm_runner.MockLlm(), "KELLY", ["a.jpg"], {"duration_sec": 5.0})
        self.assertIn("[OBSERVED]", text)


class WithBlockTests(unittest.TestCase):
    def test_first_write_appends_after_existing_description_and_keeps_the_source_note(self):
        out = va.with_block("Mô tả gốc từ ff.garena.com.", "Tóc đen, áo vàng.", "video kenta_skill.mp4, 2026-09-22")
        self.assertTrue(out.startswith("Mô tả gốc từ ff.garena.com."))
        self.assertIn(va.MARK, out)
        self.assertIn("kenta_skill.mp4", out)
        self.assertIn("Tóc đen, áo vàng.", out)

    def test_re_running_replaces_only_its_own_block_not_the_rest_of_the_description(self):
        first = va.with_block("Mô tả gốc.", "bản đầu", "video A")
        second = va.with_block(first, "bản hai", "video B")
        self.assertEqual(second.count(va.MARK), 1)
        self.assertIn("Mô tả gốc.", second)
        self.assertNotIn("bản đầu", second)
        self.assertIn("bản hai", second)


class ProbeErrorTests(unittest.TestCase):
    def test_missing_ffmpeg_raises_a_config_error(self):
        with mock.patch.object(va, "find_ffmpeg", side_effect=FFmpegNotFound("nope")):
            with self.assertRaises(va.VideoAnalysisError) as ctx:
                va.probe("whatever.mp4")
        self.assertEqual(ctx.exception.code, "config")


class DescriptionBlocksTests(unittest.TestCase):
    def test_writing_one_tool_block_keeps_the_person_text_and_the_other_blocks(self):
        from core import asset_vision, assets, ff_site
        desc = "Tay viết của người dùng."
        desc = va.with_block(desc, "kỹ năng từ video", "v.mp4")
        desc = asset_vision._with_block(desc, "ngoại hình đọc từ ảnh")
        desc = ff_site._with_block(desc, "tiểu sử chính thức")                    # written LAST: used to cut the two blocks above
        self.assertIn("Tay viết của người dùng.", desc)
        for mark in assets.BLOCK_MARKS:
            self.assertIn(mark, desc)
        again = ff_site._with_block(desc, "tiểu sử mới")
        self.assertEqual(again.count("[ff.garena.com]"), 1)
        self.assertIn("tiểu sử mới", again)
        self.assertNotIn("tiểu sử chính thức", again)
        self.assertIn("kỹ năng từ video", again)
        self.assertTrue(again.startswith("Tay viết của người dùng."))
