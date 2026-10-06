"""place_render_refs (người dùng 2026-09-29): 3D renders of the real place as reference pictures, real numbers in the prompt, and
the background agreement measured after the picture comes back."""
import json
import os
import shutil
import tempfile
import threading
import unittest
from unittest import mock

import numpy as np
from PIL import Image, ImageDraw

from core import assets, place_refs, scene_establish

ON = {"FEATURE_PLACE_RENDER_REFS": "1"}
REC = {"plate": "", "place": "Tháp Đồng Hồ", "subject_box": [0.40, 0.20, 0.60, 0.80], "distance_m": 6.5,
       "camera": {"height_m": 14.3, "horizon_y": 0.55},        # the render's height is after the model's lift — not used for the sentence
       "camera_plan": {"lens": 35, "location": [-217.0, 116.0, 11.0], "look_at": [-217.0, 132.0, 20.0],
                       "subject": {"location": [-217.0, 122.0, 9.4]}}}


def town(path, shift=0, other=False):
    img = Image.new("RGB", (360, 640), (150, 190, 230))
    d = ImageDraw.Draw(img)
    if other:
        for i in range(8):
            d.ellipse([20 + i * 40, 300 + (i % 3) * 60, 60 + i * 40, 340 + (i % 3) * 60], fill=(60, 60, 60))
    else:
        d.rectangle([150 + shift, 80, 210 + shift, 500], fill=(120, 80, 60))          # the tower
        d.rectangle([20 + shift, 380, 130 + shift, 520], fill=(200, 200, 190))        # a house
        d.polygon([(20 + shift, 380), (75 + shift, 330), (130 + shift, 380)], fill=(170, 60, 40))
        d.rectangle([240 + shift, 400, 340 + shift, 520], fill=(210, 205, 195))
    d.rectangle([0, 520, 360, 640], fill=(110, 150, 90))                              # ground
    img.save(path)
    return path


class PlaceRefsTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_off_by_default_and_only_its_own_flag_decides(self):
        with mock.patch.dict(os.environ, {"FEATURE_PLACE_RENDER_REFS": "0"}):
            self.assertFalse(place_refs.enabled())
        with mock.patch.dict(os.environ, ON):
            self.assertTrue(place_refs.enabled())
        with mock.patch.dict(os.environ, {"FEATURE_PLACE_RENDER_REFS": "1", "FEATURE_LOCATION_PLATES": "1"}):
            self.assertTrue(place_refs.enabled())          # S14.9: location_plates removed — an old line no longer turns this off

    def test_render_takes_the_place_slot_but_the_establishing_picture_stays(self):
        refs = [{"path": "k.png", "label": "KELLY", "role": "character"},
                {"path": "lib.png", "label": "Tháp Đồng Hồ", "role": "location"},
                {"path": "mark.png", "label": "Tháp Đồng Hồ", "role": "landmark"},
                {"path": "est.png", "label": scene_establish.LABEL, "role": "location"}]
        ref = {"path": "render.png", "label": "Tháp Đồng Hồ", "role": place_refs.ROLE, "_rec": REC}
        out = place_refs.swap_in(refs, ref, 6)
        self.assertEqual([r["path"] for r in out], ["k.png", "render.png", "est.png"])
        self.assertNotIn("_rec", out[1])
        self.assertEqual(place_refs.swap_in(refs, None, 6), refs)
        self.assertEqual(len(place_refs.swap_in(refs, ref, 2)), 2)

    def test_the_render_wins_over_place_words(self):
        """S5.5' 30/09: 5/5 shots drew the "stone plaza + tower" words instead of the attached render — the prompt now says the render
        decides the place, before the scene text."""
        import inspect
        from core import runner
        self.assertIn("draw what the render shows and ignore those words", place_refs.PRECEDENCE)
        self.assertIn("place_refs.PRECEDENCE", inspect.getsource(runner.ImageRunner._submit_args))

    def test_geometry_sentence_has_the_real_numbers(self):
        s = place_refs.geometry_sentence(REC, {"characters": ["KELLY"]}, 250.0)
        self.assertIn("35 mm lens, camera 1.6 m above the ground", s)
        self.assertIn("6.5 m from the camera", s)
        self.assertIn("head top at about 20%", s)
        self.assertIn("feet at about 80%", s)
        self.assertIn("horizon line at 55%", s)
        no_people = place_refs.geometry_sentence(REC, {"characters": []})
        self.assertNotIn("head top", no_people)
        self.assertIn("horizon line", no_people)

    def test_background_match_same_shifted_unrelated(self):
        plate = town(os.path.join(self.dir, "plate.png"))
        same = town(os.path.join(self.dir, "same.png"))
        shifted = town(os.path.join(self.dir, "shift.png"), shift=40)
        other = town(os.path.join(self.dir, "other.png"), other=True)
        s_same = place_refs.background_match(same, plate)
        s_shift = place_refs.background_match(shifted, plate)
        s_other = place_refs.background_match(other, plate)
        self.assertGreater(s_same, 0.9)
        self.assertLess(s_shift, s_same)
        self.assertLess(s_other, place_refs.LOW_MATCH)
        self.assertEqual(place_refs.match_note(s_other)[0], "warn")
        self.assertEqual(place_refs.match_note(s_same)[0], "info")
        self.assertIsNone(place_refs.background_match(os.path.join(self.dir, "none.png"), plate))

    def test_person_box_is_left_out_of_the_match(self):
        plate = town(os.path.join(self.dir, "plate.png"))
        drawn = os.path.join(self.dir, "drawn.png")
        img = Image.open(plate).copy()
        ImageDraw.Draw(img).rectangle([140, 150, 220, 520], fill=(20, 20, 200))      # a person over the tower
        img.save(drawn)
        box = [140 / 360, 150 / 640, 220 / 360, 520 / 640]
        self.assertGreater(place_refs.background_match(drawn, plate, box), place_refs.background_match(drawn, plate))

    def test_the_model_is_told_what_the_render_is(self):
        note = assets.reference_note([{"path": "r.png", "label": "Tháp Đồng Hồ", "role": place_refs.ROLE}])
        self.assertIn("Image 1 is the EXACT background of this shot", note)
        self.assertIn("never move, add or remove a building", note)

    def test_scene_establishing_puts_the_widest_render_first(self):
        pid, data_dir = 7, self.dir
        plates = {}
        for sid, size in ((11, "MCU"), (12, "WS")):
            p = town(os.path.join(self.dir, f"plate_{sid}.png"))
            plates[str(sid)] = dict(REC, plate=p)
        os.makedirs(os.path.join(data_dir, str(pid), "plates"))
        with open(os.path.join(data_dir, str(pid), "plates", "index.json"), "w", encoding="utf-8") as f:
            json.dump(plates, f)
        rows = [{"id": 11, "data": {"shot_size": "MCU", "location_asset": None}}, {"id": 12, "data": {"shot_size": "WS", "location_asset": None}}]
        self.assertEqual(place_refs.scene_render(data_dir, pid, rows), plates["12"]["plate"])
        with mock.patch.dict(os.environ, ON):
            pics = scene_establish.scene_pictures(None, pid, rows, data_dir)
        self.assertEqual(pics, [plates["12"]["plate"]])
        with mock.patch.dict(os.environ, {"FEATURE_PLACE_RENDER_REFS": "0"}):
            self.assertEqual(scene_establish.scene_pictures(None, pid, rows, data_dir), [])
        self.assertIn("exact 3D model of the real game map", scene_establish.RENDER_NOTE)

    def test_spot_follows_the_shot_words_when_no_plate_spot(self):
        from core import location_pack
        entry = {"default_spot": "plaza_front", "spots": {
            "plaza_front": {"at": [0, 0, 0], "label": "quảng trường trước tháp (cách 16 m)"},
            "nha_do_nam": {"at": [1, 0, 0], "label": "dãy nhà mái đỏ phía nam", "group": "canh_quan"},
            "rang_dua": {"at": [2, 0, 0], "label": "rặng dừa phía đông", "group": "canh_quan"},
            "trong_nha_nam_t2": {"at": [3, 0, 0], "label": "trong nhà phía nam — tầng 2 (phòng ngủ giường 4 cột)", "indoor": {"exposure": 1.5}}}}
        houses = {"location": "Quanh Tháp Đồng Hồ (Đảo Quân Sự) — khu nhà ở dưới chân tháp"}
        self.assertEqual(location_pack.spot_for(entry, houses)["name"], "nha_do_nam")
        self.assertEqual(location_pack.spot_for(entry, {"location": "Tháp Đồng Hồ (Đảo Quân Sự)"})["name"], "plaza_front")
        self.assertEqual(location_pack.spot_for(entry, {"location": "trong nhà, phòng ngủ tầng 2"})["name"], "trong_nha_nam_t2")
        self.assertEqual(location_pack.spot_for(entry, dict(houses, plate_spot="rang_dua"))["name"], "rang_dua")
        old = dict(houses, plate_spot="level_26_0")                        # an FFXN spot name: the words decide, and it is said
        self.assertEqual(location_pack.spot_for(entry, old)["name"], "nha_do_nam")
        self.assertIn("'nha_do_nam' (khớp chữ mô tả shot)", location_pack.spot_problem(entry, old))

    def test_every_shot_of_a_scene_stands_at_the_same_spot(self):
        """S5.5' 30/09: the scene's place words decide before each shot's prompt words; a spot NAMED by the words beats one that only
        mentions them in its side description."""
        from core import location_pack
        entry = {"default_spot": "plaza_front", "spots": {
            "plaza_front": {"at": [0, 0, 0], "label": "quảng trường trước tháp (cách 16 m)"},
            "dong_co_tay_nam": {"at": [1, 0, 0], "label": "đồng cỏ tây nam — bậc thang, dãy nhà, tháp phía sau"},
            "nha_do_nam": {"at": [2, 0, 0], "label": "dãy nhà mái đỏ phía nam"}}}
        place = "Quanh Tháp Đồng Hồ (Đảo Quân Sự) — khu nhà dưới chân tháp"
        shots = [{"location": place, "image_prompt": "wide shot, stone plaza, the clock tower in background"},
                 {"location": place, "image_prompt": "over the shoulder, daytime yard, grass"},
                 {"location": place, "blocking": "quảng trường trước tháp, Kelly chạy"}]
        self.assertEqual({location_pack.spot_for(entry, d)["name"] for d in shots}, {"nha_do_nam"})
        self.assertEqual(location_pack.auto_spot(entry, {"location": "Tháp Đồng Hồ", "image_prompt": "rặng dừa"}), None)
        self.assertEqual(location_pack.auto_spot(entry, {"location": "Tháp Đồng Hồ", "blocking": "đồng cỏ"}), "dong_co_tay_nam")

    def test_background_render_runs_once_per_project(self):
        gate, calls = threading.Event(), []

        def slow(pid):
            calls.append(pid)
            gate.wait(5)

        self.assertTrue(place_refs.ensure_async(None, 901, self.dir, (720, 1280), run=slow))
        self.assertTrue(place_refs.ensure_async(None, 901, self.dir, (720, 1280), run=slow))
        gate.set()
        place_refs._RUNNING[901].join(5)
        self.assertEqual(calls, [901])


if __name__ == "__main__":
    unittest.main()
