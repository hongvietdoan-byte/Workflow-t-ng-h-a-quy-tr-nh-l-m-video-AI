"""S14.35 — Biên kịch: nơi ngoài game cần tạo bối cảnh (ý 1), cú chốt twist trong sách Kelly (ý 2), gộp cảnh liền mạch bằng code (ý 3). 0 USD."""
import os
import unittest
from unittest import mock

from core import asset_checklist, assets, features, idea_buildable as B, idea_to_script as I, knowledge
from core.db import connect
from core.pipeline import Pipeline
from tests.test_idea_to_script import ANCHORS, IDEA, Recorder, make_kit

ROOT = os.path.join(os.path.dirname(__file__), "..")


class OutsideGamePlace(unittest.TestCase):
    """Nơi ngoài game chưa có trong Kho: không chặn cứng, 'cần tạo bối cảnh' (ảnh ref do Đạo diễn HOẶC Meshy 3D, chỉ ghi lựa chọn + ước giá),
    hiện trong bảng kê tài nguyên; map game không có 3D vẫn bị chặn; không rõ loại nơi -> hỏi lại 0 USD."""

    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("ngoài game", operating_mode="human_qc")
        make_kit(self.p.conn)
        assets.create(self.p.conn, "FF", "location", "Thành Phố")
        self.m = Recorder()

    def anchors(self, **kw):
        return dict(ANCHORS, place="Bếp căn tin", **kw)

    def test_place_not_in_kho_without_kind_is_asked_back_zero_usd(self):
        I.start(self.p.conn, self.pid, IDEA, anchors=self.anchors())
        with self.assertRaisesRegex(I.IdeaError, "Bếp căn tin.*(map game|đời thường)"):
            I.questions(self.p.conn, self.pid, self.m)
        self.assertEqual(self.m.prompts, [])

    def test_real_life_place_goes_on_and_the_writer_is_told(self):
        I.start(self.p.conn, self.pid, IDEA, anchors=self.anchors(place_kind="doi thuong", scene_choice="meshy"))
        I.questions(self.p.conn, self.pid, self.m)
        pr = self.m.prompts[0]
        self.assertIn("cần tạo bối cảnh", pr)
        self.assertIn("Bếp căn tin", pr)
        need = B.scene_needs(self.p.conn, self.pid)
        self.assertEqual([n["name"] for n in need], ["Bếp căn tin"])
        self.assertEqual(need[0]["choice"], "meshy")
        self.assertGreater(need[0]["est_usd"], 0)                       # ước giá Meshy, KHÔNG chạy

    def test_script_in_that_place_is_flagged_not_blocked_other_places_still_blocked(self):
        inp = {"duration_s": 15, "anchors": self.anchors(place_kind="doi thuong", plot="", ending="", characters=["KELLY"])}
        ok = "CẢNH 1 - NGÀY, BẾP CĂN TIN\nKelly mở tủ lạnh.\nKELLY: Gà đâu rồi?"
        c = I.check_script(self.p.conn, self.pid, ok, inp)
        self.assertEqual(c["blocked_scenes"], [])
        self.assertTrue(any("cần tạo bối cảnh" in f for f in c["flags"]))
        c2 = I.check_script(self.p.conn, self.pid, ok + "\n\nCẢNH 2 - NGÀY, THÀNH PHỐ\nKelly chạy.\nKELLY: Đi!", inp)
        self.assertEqual([b["scene"] for b in c2["blocked_scenes"]], [2])

    def test_game_map_without_3d_is_still_blocked(self):
        I.start(self.p.conn, self.pid, IDEA, anchors=dict(ANCHORS, place="Thành Phố", place_kind="doi thuong"))
        with self.assertRaisesRegex(I.IdeaError, "Thành Phố"):
            I.questions(self.p.conn, self.pid, self.m)
        I.start(self.p.conn, self.pid, IDEA, anchors=self.anchors(place_kind="map game"))
        with self.assertRaisesRegex(I.IdeaError, "map game"):
            I.questions(self.p.conn, self.pid, self.m)
        self.assertEqual(self.m.prompts, [])

    def test_to_create_row_shows_in_the_asset_checklist(self):
        I.start(self.p.conn, self.pid, IDEA, anchors=self.anchors(place_kind="doi thuong", scene_choice="ref_image"))
        with mock.patch.dict(os.environ, {"FEATURE_ASSET_CHECKLIST": "1"}):
            res = asset_checklist.get(self.p, self.pid)
        row = next(r for r in res["rows"] if r["status"] == "to_create")
        self.assertEqual(row["name"], "Bếp căn tin")
        self.assertIn("ảnh", row["status_label"])
        self.assertEqual(res["to_create"], ["Bếp căn tin"])
        self.assertNotIn("Bếp căn tin", res["missing"])

    def test_the_idea_form_has_the_choice(self):
        text = open(os.path.join(ROOT, "dashboard", "steps", "step1_idea.py"), encoding="utf-8").read()
        for word in ("place_kind", "scene_choice", "Meshy"):
            self.assertIn(word, text)


class KellyTwistBook(unittest.TestCase):
    def test_book_has_the_twist_ending_and_the_wow_in_suggestion_voice(self):
        text = open(os.path.join(ROOT, "knowledge", "craft", "kelly_bien_kich.md"), encoding="utf-8").read()
        for word in ("tiết lộ rõ", "twist", "chim cánh cụt", "wow", "15 s"):
            self.assertIn(word, text)
        self.assertLess(len(text), 6000)

    def test_director_and_dp_books_have_the_continuity_note(self):
        for name in ("kelly_dao_dien.md", "kelly_quay_phim.md"):
            text = open(os.path.join(ROOT, "knowledge", "craft", name), encoding="utf-8").read()
            self.assertIn("liền mạch", text, name)


class SceneMerge(unittest.TestCase):
    """Gộp CẢNH liền nhau cùng nơi bằng code: giữ thoại + thứ tự, ghi chú nối, không gộp khi khác nơi/ban đêm/đổi áo/chuyển cảnh."""
    A = "CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\nKelly đứng cạnh thùng thính.\nKELLY: Của tôi!\n\n"
    B = "CẢNH 2 - NGÀY, ĐẢO QUÂN SỰ\nMaxim chạy tới giằng thùng với Kelly.\nMAXIM: Còn lâu!\n\n"
    C = "CẢNH 3 - NGÀY, ĐẢO QUÂN SỰ\nKelly và Maxim mở thùng, trống trơn.\nKELLY: Ủa?"

    def merge(self, text):
        from core import scene_merge
        return scene_merge.merge_script(text)

    def test_adjacent_same_place_scenes_become_one_keeping_order_and_dialogue(self):
        new, rep = self.merge(self.A + self.B + self.C)
        scenes, _ = I.parse(new)
        self.assertEqual(len(scenes), 1)
        self.assertTrue(scenes[0].heading.startswith("CẢNH 1"))
        t = scenes[0].text
        self.assertLess(t.index("cạnh thùng"), t.index("Maxim chạy"))
        self.assertLess(t.index("Maxim chạy"), t.index("trống trơn"))
        for line in ("KELLY: Của tôi!", "MAXIM: Còn lâu!", "KELLY: Ủa?"):
            self.assertIn(line, t)
        self.assertEqual(rep["merged"], [[1, 2, 3]])
        self.assertEqual(len(rep["joins"]), 2)                                   # chỗ giao: vị trí + hành động cuối -> đầu
        self.assertIn("thùng", rep["joins"][0]["end_state"])
        self.assertIn("Maxim", rep["joins"][0]["start_state"])

    def test_not_merged_when_place_time_costume_or_transition_differs(self):
        for second in ("CẢNH 2 - NGÀY, THÀNH PHỐ\nKelly chạy.",
                       "CẢNH 2 - ĐÊM, ĐẢO QUÂN SỰ\nKelly ngủ.",
                       "CẢNH 2 - NGÀY, ĐẢO QUÂN SỰ\nKelly thay áo mới rồi quay lại.",
                       "CẢNH 2 - NGÀY, ĐẢO QUÂN SỰ\nChuyển cảnh mờ dần sang buổi chiều.\nKelly cười."):
            new, rep = self.merge(self.A + second)
            self.assertEqual(len(I.parse(new)[0]), 2, second)
            self.assertEqual(rep["merged"], [], second)

    def test_different_cast_is_not_merged_and_the_cut_is_continuous_only_in_the_same_place(self):
        a = "CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\nKelly đứng.\nKELLY: Hi\n\n"
        b = "CẢNH 2 - NGÀY, ĐẢO QUÂN SỰ\nAlvaro và Maxim chạy tới.\nALVARO: Chào\nMAXIM: Ê"
        new, rep = self.merge(a + b)
        self.assertEqual(len(I.parse(new)[0]), 2)
        self.assertTrue(rep["cuts"][0]["continuous"])
        self.assertIn("Liền mạch", new)
        _, rep2 = self.merge(a + "CẢNH 2 - NGÀY, THÀNH PHỐ\nKelly chạy.\nKELLY: Đi")
        self.assertFalse(rep2["cuts"][0]["continuous"])

    def test_note_line_is_not_read_as_a_speaker(self):
        from core.dialogue import lines
        new, _ = self.merge("CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\nKelly đứng.\nKELLY: Hi\n\n"
                            "CẢNH 2 - NGÀY, ĐẢO QUÂN SỰ\nAlvaro và Maxim chạy tới.\nALVARO: Chào")
        scenes, _ = I.parse(new)
        self.assertEqual([w for w, _ in lines(scenes[0].text)], ["KELLY"])

    def test_write_merges_and_keeps_the_original(self):
        p = Pipeline(connect())
        pid = p.create_project("gộp", operating_mode="human_qc")
        make_kit(p.conn)
        m = Recorder()
        I.start(p.conn, pid, IDEA, anchors=ANCHORS)
        I.questions(p.conn, pid, m)
        I.answer(p.conn, pid, ["vui", ""])
        I.directions(p.conn, pid, m)
        I.outline(p.conn, pid, m, 1)
        st = I.write(p.conn, pid, m)
        self.assertEqual(st["script_checks"]["scenes"], 1)                 # mock viết 2 cảnh cùng nơi
        self.assertTrue(st.get("script_unmerged"))
        self.assertTrue(st["merge"]["merged"])
        self.assertIn("Ủa?", st["script"])


if __name__ == "__main__":
    unittest.main()
