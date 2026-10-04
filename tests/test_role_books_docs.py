"""Khóa các chỗ rà soát bộ kỹ năng 3 vai (02/10/2026): Tầng A của Đạo diễn không đọc lệnh shot, tài liệu không ghi sai trạng thái cờ,
ống kính không bị gán nghĩa cố định, kho `knowledge/editor/` không được nạp vào prompt nào."""
import os
import re
import unittest

from core import features, prompts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n")


class IntentPassTests(unittest.TestCase):
    def test_markers_are_balanced_and_closed(self):
        for name in ("director.md", "dp.md"):
            raw = _read("knowledge", "roles", name)
            self.assertEqual(raw.count("<!-- shot -->"), raw.count("<!-- /shot -->"), name)
            for part in raw.split("<!-- intent:")[1:]:
                self.assertIn(" -->", part.split("<!--")[0], name)       # each intent note closes before any other marker
            # every shot block closes before the next opens (no nesting)
            depth = 0
            for m in re.finditer(r"<!-- (/?)shot -->", raw):
                depth += -1 if m.group(1) else 1
                self.assertIn(depth, (0, 1), name)

    def test_the_director_intent_text_carries_no_shot_orders(self):
        full = prompts.role_text("director.md")
        intent = prompts.role_text("director.md", intent_only=True)
        self.assertNotIn("<!--", full)
        self.assertNotIn("<!--", intent)
        for shot_only in ("freeze_end_s", "Quay phim ghi shot `speed`", "Đ11 chọn khoảnh khắc", "Shot đó ghi `\"lip_sync\": true`",
                          "Mỗi shot có người ghi `performance`", "**`money_shot: true`**"):
            self.assertNotIn(shot_only, intent, shot_only)
        # a literal marker in the prose once swallowed Tầng 1, Tầng 2, Đ1 and half of Đ2 out of this version
        for kept in ("## Tầng 1", "## Tầng 2", "### Đ1.", "### Đ2.", "### Đ3.", "### Đ7.", "## Tầng 4", "## Tầng 5"):
            self.assertIn(kept, intent, kept)
        # the full book (one-pass Director) keeps them
        self.assertIn("freeze_end_s", full)
        self.assertIn("Quay phim ghi shot `speed`", full)
        self.assertIn("Shot đó ghi `\"lip_sync\": true`", full)
        # the intent version says what to write instead
        self.assertIn("`dp_notes`", intent[intent.index("### Đ11"):intent.index("### Đ12")])

    def test_blocks_join_on_their_own_lines(self):
        raw = _read("knowledge", "roles", "director.md")
        self.assertNotIn("-->-", raw)                       # the Đ4 block once glued "-->" to the next bullet
        intent = prompts.role_text("director.md", intent_only=True)
        self.assertNotRegex(intent, r"\S- \*\*Kiểm\.\*\*")


class FlagStateInDocsTests(unittest.TestCase):
    DOCS = (("knowledge", "editor", "editing.md"), ("knowledge", "editor", "safe_zones.md"), ("knowledge", "roles", "README.md"),
            ("knowledge", "roles", "director.md"), ("knowledge", "roles", "dp.md"))

    def test_a_verified_flag_is_never_written_as_off(self):
        verified = [k for k, v in features.FEATURES.items() if v["verified"]]
        self.assertIn("music_breath", verified)
        for parts in self.DOCS:
            text = _read(*parts)
            for name in verified:
                self.assertNotRegex(text, r"`%s`[^\n|;)]{0,8}\bTẮT\b" % name, "%s: cờ %s verified True" % (parts[-1], name))
                self.assertNotRegex(text, r"`%s` TẮT tới" % name, "%s: cờ %s" % (parts[-1], name))

    def test_the_title_lines_no_longer_wait_for_approval(self):
        for parts in self.DOCS:
            self.assertNotIn("chờ người dùng duyệt", _read(*parts).splitlines()[0], parts[-1])

    def test_nothing_claims_the_editor_books_reach_a_prompt(self):
        # P2 (02/10): only the <!-- review --> blocks of editing.md are loaded, and only by core/editor_review.py (role_text still reads
        # director.md + dp.md); safe_zones.md is loaded by nothing
        self.assertIn("chỉ các khối `<!-- review -->`", _read("knowledge", "editor", "editing.md").splitlines()[0])
        src = _read("core", "prompts.py")
        self.assertNotIn("editing.md", src.replace("knowledge/ff_directing", ""), "core/prompts.py")
        for path in ("core/prompts.py", "core/knowledge.py"):
            self.assertNotIn("safe_zones", _read(*path.split("/")), path)
        # S14.4 C1b: the knowledge page lists editing.md under film_crew (plan 3.3) — but marked "elsewhere" (not counted as sent)
        import os
        from unittest import mock
        from core import knowledge
        with mock.patch.dict(os.environ, {"FEATURE_FILM_CREW": "1"}):
            ov = knowledge.overview("director")
        ed = [d for d in ov["docs"] if d["file"].endswith("editing.md")]
        self.assertEqual(len(ed), 1)
        self.assertTrue(ed[0]["elsewhere"])
        self.assertEqual(ov["chars"], sum(d["chars"] for d in ov["docs"] if d["enabled"] and not d["replaced"]
                                          and not d.get("crew_replaced") and not d.get("elsewhere")))

    def test_default_subtitle_box_is_tiktok(self):
        from core import subtitles
        self.assertEqual(subtitles.DEFAULTS["platform"], "tiktok")
        box = subtitles.PLATFORMS["tiktok"]
        self.assertEqual((box["top"], box["bottom"], box["left"], box["right"]), (0.08, 0.27, 0.135, 0.135))
        e7 = _read("knowledge", "editor", "editing.md")
        self.assertIn("Phụ đề mặc định dùng hộp TikTok", e7)
        self.assertIn("8% / dưới 27% / hai bên 13,5%", e7)


class LensMeaningTests(unittest.TestCase):
    def test_lens_effects_are_optical_and_the_intent_is_per_scene(self):
        p17 = _read("prompts", "17_director_shots.md")
        self.assertNotIn("anh hùng/ngợp", p17)
        self.assertIn("tùy cảnh", p17[p17.index("`lens_mm`"):p17.index("`lens_mm`") + 400])
        plate = _read("core", "plate_camera.py")
        self.assertNotIn("hero / distorted", plate)

    def test_eye_positions_in_the_dp_book_match_the_virtual_camera(self):
        from core import plate_camera as pc
        eyes = {}
        for size in ("WS", "MLS", "MS", "MCU", "CU"):
            cam = pc.camera_for({"size": size}, (0, 0, 0), 0)["camera"]
            eyes[size] = pc.project(cam["location"], cam["look_at"], cam["lens"], 9 / 16, (0, 0, 1.75 * 0.93))[1]
        self.assertAlmostEqual(eyes["MLS"], 0.207, delta=0.005)
        self.assertAlmostEqual(eyes["WS"], 0.166, delta=0.005)
        dp = _read("knowledge", "roles", "dp.md")
        self.assertIn("MLS 20,7", dp)
        self.assertIn("**đỉnh đầu**", dp)


if __name__ == "__main__":
    unittest.main()
