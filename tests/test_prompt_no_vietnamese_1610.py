"""16/10 #31 (rà đầu vào ảnh 0 USD, docs/handoff/RA_DAU_VAO_ANH_P31_2026-10-16.md): Vietnamese notes of the library / the Director
reached the paid picture prompt — the indoor spot label with camera notes, landmark names of the set analyses, "listener: không áp dụng"."""
import unittest
from unittest import mock

from core import assets, performance, runner


class PromptNoVietnamese(unittest.TestCase):
    def test_landmark_heights_stay_names_lose_their_accents_for_the_image_model(self):
        text = assets._sizes_sentence([("hàng rào cây bụi", 1.0), ("clock tower", 28.0)])
        self.assertIn("hang rao cay bui about 1 m tall", text)          # the heights stay (B1 scale of people)
        self.assertIn("clock tower about 28 m tall", text)
        self.assertNotIn("hàng rào", text)
        self.assertIn("hàng rào cây bụi about 1 m tall", assets._sizes_sentence([("hàng rào cây bụi", 1.0)], keep_vi=True))
        self.assertEqual(assets._sizes_sentence([]), "")

    def test_a_vietnamese_library_light_is_not_sent_to_the_image_model(self):
        with mock.patch.object(assets, "_landmark_heights", return_value=([], "ánh sáng ban ngày dịu, trời quang")):
            image = assets.location_text(None, {"name": "Cổng Trời", "description": ""})
            claude = assets.location_text(None, {"name": "Cổng Trời", "description": ""}, for_llm=True)
        self.assertNotIn("Light:", image)
        self.assertIn("Light: ánh sáng ban ngày dịu", claude)

    def test_a_vietnamese_performance_note_is_not_acting(self):
        p = {"intensity": 3, "face": "a tight grin", "eyes": "narrowed", "body": "leaning in", "listener": "không áp dụng"}
        text = performance.image_sentence({"performance": p, "characters": ["KELLY", "XÚC TU ĐỎ"]})
        self.assertIn("face: a tight grin", text)
        self.assertNotIn("không áp dụng", text)
        self.assertNotIn("listener", text)

    def test_cast_names_with_accents_do_not_drop_an_english_field(self):
        p = {"intensity": 3, "face": "a tight grin", "eyes": "fixed on XÚC TU ĐỎ", "listener": "XÚC TU ĐỎ recoils"}
        text = performance.image_sentence({"performance": p, "characters": ["KELLY", "XÚC TU ĐỎ"]})
        self.assertIn("eyes: fixed on XUC TU DO", text)
        self.assertIn("listener: XUC TU DO recoils", text)

    def test_the_english_translation_of_the_acting_wins(self):
        p = {"intensity": 3, "face": "cười nhếch mép", "eyes": "nheo lại"}
        data = {"performance": p, "characters": ["KELLY"], "motion_en": {"performance": {"face": "a smirk", "eyes": "narrowed"}}}
        text = performance.image_sentence(data)
        self.assertIn("face: a smirk", text)
        self.assertIn("eyes: narrowed", text)

    def test_an_english_indoor_label_is_still_sent(self):
        place = {"id": 5, "name": "ROOM", "images": [], "description": ""}
        entry = {"default_spot": "a", "spots": {"a": {"at": [0, 0, 0], "label": "upstairs bedroom", "indoor": {"exposure": 1.5}}}}
        with mock.patch.object(assets, "scene_location", return_value=place), \
                mock.patch("core.location_pack.model3d", return_value=entry), \
                mock.patch("core.place_refs.enabled", return_value=True):
            text = runner._place_part(None, 1, {}, place, True, [])
        self.assertIn("INSIDE a room — upstairs bedroom (ROOM map)", text)


if __name__ == "__main__":
    unittest.main()
