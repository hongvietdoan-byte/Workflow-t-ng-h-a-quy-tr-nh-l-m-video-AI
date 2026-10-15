"""15/10 #31 mê cung (docs/handoff/CHAN_DOAN_ME_CUNG_P31_2026-10-15.md mục 5c): 3 sửa code — hướng mốc từ mỗi chỗ đứng cho Đạo diễn,
lý do "không có mốc" trái hướng nền nhìn về mốc, chỗ đứng ngoài khu vực shot nói = VÀNG. Dữ liệu dựng tay theo Kho #265 (không đọc
CSDL thật)."""
import unittest
from unittest import mock

from core import location_pack, plate_choice
from core.plate_view_check import LANDMARK_NOT_IN_FRAME

# Kho #265 Cổng Trời (rút gọn): biệt thự ở phía tây của mê cung; chỗ đứng `me_cung` là bãi cỏ NGOÀI mê cung (5a: group ngoai_me_cung)
ENTRY = {"anchor": [-660.0, -75.0, 70.0], "landmark": "the villa (biệt thự)", "default_spot": "me_cung",
         "spots": {"me_cung": {"at": [-598.0, -75.0, 67.88], "facing": 270, "label": "bãi cỏ ngoài mê cung", "group": "ngoai_me_cung"},
                   "me_cung_loi_vao_dong": {"at": [-607.2, -74.7, 67.884], "facing": 0, "label": "lối vào đông", "group": "me_cung",
                                            "view": [-607.2, -60.0, 67.884]},
                   "trung_tam_me_cung": {"at": [-621.5, -74.6, 67.884], "facing": 90, "label": "tâm mê cung", "group": "me_cung"}}}


class DirectorBearingsTests(unittest.TestCase):
    def test_spot_line_says_where_the_landmark_is(self):
        s = location_pack._spot_bearings(ENTRY, ENTRY["spots"]["me_cung"])
        self.assertIn("the villa (biệt thự) ở hướng 270° từ đây", s)

    def test_default_view_bearing(self):
        s = location_pack._spot_bearings(ENTRY, ENTRY["spots"]["me_cung_loi_vao_dong"])
        self.assertIn("hướng nhìn mặc định 0°", s)

    def test_director_block_lists_bearing_and_group(self):
        with mock.patch("core.place_refs.enabled", return_value=True), \
                mock.patch.object(location_pack.assets, "project_assets", return_value=[{"id": 265, "kind": "location", "name": "Cổng Trời"}]), \
                mock.patch.object(location_pack, "model3d", return_value=ENTRY):
            text = location_pack.director_block(None, 31)
        self.assertIn("khu vực `ngoai_me_cung`", text)
        self.assertIn("ở hướng 270° từ đây", text)


class NoLandmarkWhyTests(unittest.TestCase):
    def test_patterns(self):
        for s in ("không có mốc trong khung", "no landmark visible", "biệt thự ngoài khung", "không thấy được biệt thự trong khung"):
            self.assertTrue(LANDMARK_NOT_IN_FRAME.search(s), s)
        for s in ("không có cây che mốc", "mốc ở nền sau Kelly", "không có ai", "Kelly không thấy tháp sau lưng"):
            self.assertFalse(LANDMARK_NOT_IN_FRAME.search(s), s)

    def test_shot5_background_at_villa_with_no_landmark_reason_waits(self):
        spot = dict(ENTRY["spots"]["me_cung"], name="me_cung")
        data = {"plate_spot": "me_cung", "plate_view": {"background": 270, "why": "lối mê cung trước mặt, không có mốc trong khung"}}
        v = plate_choice.view_of(ENTRY, spot, data)
        self.assertIsNotNone(v["needs"])
        self.assertIn("không được có trong khung", v["needs"])

    def test_away_from_landmark_passes(self):
        spot = dict(ENTRY["spots"]["me_cung"], name="me_cung")
        data = {"plate_spot": "me_cung", "plate_view": {"background": 90, "why": "nhìn về đông, không có mốc trong khung"}}
        self.assertIsNone(plate_choice.view_of(ENTRY, spot, data)["needs"])

    def test_behind_camera_wording_kept(self):
        spot = dict(ENTRY["spots"]["me_cung"], name="me_cung")
        data = {"plate_spot": "me_cung", "plate_view": {"background": 270, "why": "mốc sau lưng máy"}}
        self.assertIn("SAU LƯNG MÁY", plate_choice.view_of(ENTRY, spot, data)["needs"])


class GroupProblemTests(unittest.TestCase):
    def test_spot_outside_named_area_is_yellow(self):
        msg = location_pack.spot_problem(ENTRY, {"plate_spot": "me_cung", "location": "Cổng Trời — mê cung, thế giới song song"})
        self.assertIn("ngoài khu vực shot nói (`me_cung`)", msg)

    def test_spot_inside_named_area_ok(self):
        self.assertIsNone(location_pack.spot_problem(ENTRY, {"plate_spot": "trung_tam_me_cung", "location": "Cổng Trời — mê cung"}))

    def test_longer_group_name_wins(self):
        self.assertIsNone(location_pack.spot_problem(ENTRY, {"plate_spot": "me_cung", "location": "bãi cỏ ngoài mê cung"}))

    def test_no_group_data_no_check(self):
        entry = {"default_spot": "a", "spots": {"a": {"at": [0, 0, 0]}, "b": {"at": [5, 0, 0]}}}
        self.assertIsNone(location_pack.spot_problem(entry, {"plate_spot": "a", "location": "mê cung"}))


if __name__ == "__main__":
    unittest.main()
