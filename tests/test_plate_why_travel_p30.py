"""14/10 #30 shot 1: Quay phim ghi `plate_view` 'scenery' + lý do "tháp nằm phía sau máy" nhưng 'scenery' = hướng nhìn đã đăng ký của chỗ
đứng = NHÌN VỀ tháp → Kelly chạy xuống. Code đối chiếu lý do ↔ hướng; travel_truth không viết chiều so với máy theo nền sai."""
import unittest
import unittest.mock

from core import location_pack, plate_choice, plate_view_check as V, travel_truth
from tests.test_plate_choice import ENTRY

WHY = "camera đối mặt Kelly khi cô chạy lên, tháp nằm phía sau máy nên chưa vào khung"


def spot(name):
    return location_pack.spot_for(ENTRY, {"plate_spot": name})


class WhyVsDirectionTests(unittest.TestCase):
    def test_scenery_with_landmark_behind_camera_becomes_away(self):
        s = {"plate_spot": "plaza", "angle": "eye", "plate_view": {"background": "scenery", "why": WHY}}
        said = V.fix_reverse_landmark([(1, 1, s)])
        self.assertEqual(len(said), 1)
        self.assertEqual(s["plate_view"]["background"], "away")
        self.assertIn("scenery→away", s["plate_view"]["why"])

    def test_landmark_in_background_reason_is_untouched(self):
        s = {"plate_spot": "plaza", "plate_view": {"background": "landmark", "why": "giữ tháp phía sau Kelly"}}
        self.assertEqual(V.fix_reverse_landmark([(1, 1, s)]), [])
        self.assertEqual(s["plate_view"]["background"], "landmark")

    def test_view_of_blocks_a_direction_that_contradicts_the_reason(self):
        data = {"plate_view": {"background": "landmark", "why": WHY}}
        got = plate_choice.view_of(ENTRY, spot("plaza"), data)
        self.assertIsNotNone(got["needs"])
        ok = plate_choice.view_of(ENTRY, spot("plaza"), {"plate_view": {"background": "away", "why": WHY}})
        self.assertIsNone(ok["needs"])


class TravelConflictTests(unittest.TestCase):
    def _run(self, text):
        a = {"name": "a", "at": [0, 0, 0], "label": "chân cầu thang"}
        b = {"name": "b", "at": [0, 10, 5], "label": "đỉnh"}
        rec = {"camera_plan": {"location": [0, -2, 1], "look_at": [0, 10, 1]}}      # máy sau lưng hướng chạy → 'away'
        with unittest.mock.patch.object(travel_truth, "_spot", return_value=a), \
                unittest.mock.patch.object(travel_truth, "_next_spot", return_value=b), \
                unittest.mock.patch("core.assets.scene_location", return_value={"id": 1}), \
                unittest.mock.patch("core.location_pack.model3d", return_value={"spots": {"a": a}}):
            return travel_truth.for_shot(None, 1, 1, {"action": text, "characters": ["KELLY"]}, rec)

    def test_conflicting_words_drop_the_camera_relation(self):
        got = self._run("Kelly runs up the stairs toward the camera")
        self.assertIn("UP the stairs", got["sentence"])
        self.assertNotIn("AWAY from the camera", got["sentence"])
        self.assertTrue(got["warn"])

    def test_no_conflict_keeps_the_relation(self):
        got = self._run("Kelly runs up the stairs")
        self.assertIn("AWAY from the camera", got["sentence"])


if __name__ == "__main__":
    unittest.main()


class RegexGuardTests(unittest.TestCase):
    def test_negated_or_unrelated_reasons_do_not_match(self):
        for why in ("tháp không nằm sau máy, ở trước mặt", "landmark is not behind the camera", "tháp sau lưng Kelly",
                    "mốc chưa vào khung, sẽ lộ ra khi máy xoay"):
            self.assertIsNone(V.LANDMARK_BEHIND_CAMERA.search(why), why)
        self.assertIsNotNone(V.LANDMARK_BEHIND_CAMERA.search(WHY))

    def test_script_sentence_is_silent_when_the_view_is_blocked(self):
        from unittest import mock
        data = {"plate_spot": "plaza", "plate_view": {"background": "landmark", "why": WHY}}
        with mock.patch("core.assets.scene_location", return_value={"id": 1}), \
                mock.patch.object(location_pack, "model3d", return_value=ENTRY):
            self.assertEqual(location_pack.script_sentence(None, 1, data), "")
