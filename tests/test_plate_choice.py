"""S5.7 (người dùng 29/09): camera direction at a 3D spot + extra night lights are chosen per shot from the script (core/plate_choice),
go into the plate's camera (so the cache key), the picture's fingerprint (frame "cũ") and the picture prompt; missing information is
said — a script-view spot (the covered yard) without a direction gets no plate at all. No Blender: the render is faked."""
import json
import math
import os
import tempfile
import unittest
from unittest import mock

from core import assets, lineage, location_pack, plate_camera, plate_choice, shots
from core.db import connect
from core.pipeline import Pipeline
from tests.test_location_pack import H, W, PackTests

ENTRY = {"anchor": [0.0, 10.0, 0.0], "landmark": "the clock tower", "default_spot": "plaza",
         "spots": {"plaza": {"at": [0.0, 0.0, 0.0], "facing": 180.0, "label": "plaza"},
                   "yard": {"at": [10.0, 0.0, -3.0], "facing": 0.0, "label": "covered yard", "direction": "script",
                            "view": [30.0, 0.0, 0.0]},
                   "stairs": {"at": [-10.0, 0.0, 0.0], "facing": 0.0, "label": "stairs"}}}


def spot(name):
    return location_pack.spot_for(ENTRY, {"plate_spot": name})


class ViewTests(unittest.TestCase):
    def test_landmark_away_left_right_are_bearings_from_the_spot(self):
        got = {v: plate_choice.view_of(ENTRY, spot("plaza"), {"plate_view": {"background": v, "why": "trục"}})
               for v in ("landmark", "away", "left", "right")}
        self.assertEqual(got["landmark"]["background_deg"], 0.0)                 # the tower is due +y of the plaza
        self.assertEqual(got["away"]["background_deg"], 180.0)
        self.assertEqual(got["left"]["background_deg"], 270.0)
        self.assertEqual(got["right"]["background_deg"], 90.0)
        self.assertEqual(got["landmark"]["facing_deg"], 180.0)                  # the character faces the camera, back to the tower
        self.assertTrue(all(g["source"] == "script" and g["problem"] is None and g["needs"] is None for g in got.values()))
        self.assertIn("NOT in the frame", got["away"]["words_en"])

    def test_the_camera_in_front_really_sees_the_chosen_background(self):
        v = plate_choice.view_of(ENTRY, spot("plaza"), {"plate_view": {"background": "landmark", "why": "x"}})
        cam = plate_camera.camera_for({"size": "MS"}, [0, 0, 0], v["facing_deg"])["camera"]
        look = (cam["look_at"][0] - cam["location"][0], cam["look_at"][1] - cam["location"][1])
        self.assertGreater(look[1], 0.9 * math.hypot(*look))                   # looking +y, towards the tower

    def test_over_the_shoulder_keeps_the_background_the_script_chose(self):
        data = {"angle": "ots", "plate_view": {"background": "landmark", "why": "x"}}
        v = plate_choice.view_of(ENTRY, spot("plaza"), data)
        cam = plate_camera.camera_for(data, [0, 0, 0], v["facing_deg"])["camera"]
        self.assertGreater(cam["look_at"][1] - cam["location"][1], 0)           # still looking towards the tower

    def test_towards_another_spot_and_a_bearing(self):
        v = plate_choice.view_of(ENTRY, spot("plaza"), {"plate_view": {"background": "spot:stairs", "why": "x"}})
        self.assertEqual(v["background_deg"], 270.0)
        v = plate_choice.view_of(ENTRY, spot("plaza"), {"plate_view": 45})
        self.assertEqual(v["background_deg"], 45.0)
        self.assertIn("lý do", v["problem"])                                   # a number without a reason is reported

    def test_scenery_looks_at_the_registered_view_point(self):
        v = plate_choice.view_of(ENTRY, spot("yard"), {"plate_view": {"background": "scenery", "why": "cảnh quan"}})
        self.assertEqual((v["background_deg"], v["needs"]), (90.0, None))
        v = plate_choice.view_of(ENTRY, spot("plaza"), {"plate_view": {"background": "scenery", "why": "x"}})
        self.assertIn("cảnh quan", v["problem"])                               # no view point there: said, the default used

    def test_a_script_view_spot_without_a_direction_needs_one(self):
        v = plate_choice.view_of(ENTRY, spot("yard"), {})
        self.assertIsNotNone(v["needs"])
        self.assertIn("plate_view", v["needs"])
        v = plate_choice.view_of(ENTRY, spot("yard"), {"plate_view": "sideways"})
        self.assertIn("không hiểu", v["needs"])
        ok = plate_choice.view_of(ENTRY, spot("yard"), {"plate_view": {"background": "away", "why": "Kelly nhìn ra phố"}})
        self.assertIsNone(ok["needs"])

    def test_an_ordinary_spot_without_a_direction_says_it_used_the_default(self):
        v = plate_choice.view_of(ENTRY, spot("plaza"), {})
        self.assertIsNone(v["needs"])
        self.assertIn("mặc định", v["problem"])
        self.assertEqual(v["facing_deg"], 180.0)                                # the registered facing, unchanged
        self.assertEqual(v["source"], "spot_default")


class LightTests(unittest.TestCase):
    def test_night_without_a_decision_is_reported_and_an_empty_list_is_a_decision(self):
        self.assertIn("chưa quyết", plate_choice.lights_of({}, {"time": "night"})["problem"])
        self.assertIsNone(plate_choice.lights_of({}, {"time": "day"})["problem"])
        none = plate_choice.lights_of({"practical_lights": []}, {"time": "night"})
        self.assertEqual((none["lights"], none["decided"], none["problem"]), ([], True, None))
        self.assertIn("moonlight", plate_choice.light_sentence([], True, "night"))

    def test_a_lit_night_plate_keeps_its_warm_light_through_the_grade(self):
        import numpy as np
        from core import plate_env
        warm = np.array([[[0.40, 0.36, 0.30]]])
        cold = plate_env.grade(warm, {"time": "night", "weather": "clear"})[0, 0]
        lit = plate_env.grade(warm, {"time": "night", "weather": "clear", "practical": True})[0, 0]
        self.assertLess(cold[0], cold[2])                                      # the plain night grade turns a lamp blue-grey
        self.assertGreater(lit[0], lit[2])                                     # with the shot's lamps it stays warm

    def test_bad_entries_are_dropped_with_a_reason_and_colours_parsed(self):
        lit = plate_choice.lights_of({"practical_lights": [
            {"kind": "fire", "where": "behind-left", "color": "#ff8800", "why": "lửa trại"},
            {"kind": "laser", "where": "left", "why": "x"}, {"kind": "lamp", "where": "nowhere", "why": "x"}]}, {"time": "night"})
        self.assertEqual([lt["kind"] for lt in lit["lights"]], ["fire"])
        self.assertEqual(lit["lights"][0]["rgb"], [1.0, 0.533, 0.0])
        self.assertIn("laser", lit["problem"])
        self.assertIn("nowhere", lit["problem"])

    def test_rigs_sit_where_the_words_say_seen_from_the_camera(self):
        lights = plate_choice.lights_of({"practical_lights": [{"kind": "lamp", "where": "behind", "why": "x"},
                                                              {"kind": "screen", "where": "left", "why": "x"}]}, {"time": "night"})["lights"]
        rigs = plate_choice.light_rigs(lights, [0, 0, 0], [0, -4, 1.6])          # camera south of the character, looking +y
        self.assertGreater(rigs[0]["location"][1], 0)                          # behind = beyond the character
        self.assertLess(rigs[1]["location"][0], 0)                             # frame left = -x for a camera looking +y
        self.assertEqual(rigs[1]["type"], "AREA")
        text = plate_choice.light_sentence(lights, True, "night")
        self.assertIn("rim light", text)
        self.assertIn("left of the frame", text)


class ShotFieldTests(unittest.TestCase):
    def test_the_fields_survive_into_the_shot_and_lights_come_from_the_scene(self):
        scene = {"idx": 1, "characters": ["KELLY"], "practical_lights": [{"kind": "lamp", "where": "behind", "why": "đèn đường"}]}
        s = {"size": "MS", "angle": "eye", "role": "main", "action": "a", "image_prompt": "p", "duration_s": 3, "lines": [],
             "plate_view": {"background": "away", "why": "nền gọn"}}
        data = shots.shot_data(scene, s, 1)
        self.assertEqual(data["plate_view"]["background"], "away")
        self.assertEqual(data["practical_lights"][0]["kind"], "lamp")

    def test_a_changed_direction_or_light_makes_the_frame_outdated(self):
        base = {"image_prompt": "p", "plate_spot": "yard"}
        h0 = lineage.image_spec_hash(base, [], "9:16")
        h1 = lineage.image_spec_hash(dict(base, plate_view={"background": "away", "why": "x"}), [], "9:16")
        h2 = lineage.image_spec_hash(dict(base, plate_view={"background": "landmark", "why": "x"}), [], "9:16")
        h3 = lineage.image_spec_hash(dict(base, plate_view={"background": "landmark", "why": "x"}, practical_lights=[]), [], "9:16")
        self.assertEqual(len({h0, h1, h2, h3}), 4)


class PlanTests(PackTests):
    """The project-level plan: direction + lights are in the camera and the cache key; a script-view spot waits for the script."""
    def setUp(self):
        super().setUp()
        location_pack.set_model3d(self.p.conn, self.place, self.model,
                                  {"plaza_front": {"at": [12.68, -19.0, 25.93], "facing": 0},
                                   "lower_yard": {"at": [20.0, -25.0, 22.4], "facing": 0}}, "plaza_front", anchor=[12.68, -31.13, 33.5])
        location_pack.set_script_view(self.p.conn, self.place, ["lower_yard"], landmark="the clock tower")

    def one_shot(self, data):
        pid = self.p.create_project(f"p{len(self.calls)}{id(data)}", aspect="9:16")
        sid = self.p.create_scene(pid, 1, "s1")
        base = {"size": "MS", "characters": ["KELLY"], "location_asset": self.place, "image_prompt": "Kelly waits"}
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(dict(base, **data)), sid))
        self.p.conn.commit()
        return pid, sid

    def test_register_keeps_the_mark_and_the_director_is_told(self):
        entry = location_pack.model3d(self.p.conn, self.place)
        self.assertEqual(entry["spots"]["lower_yard"]["direction"], "script")
        self.assertEqual(entry["landmark"], "the clock tower")
        with mock.patch.dict(os.environ, {"FEATURE_PLACE_RENDER_REFS": "1"}):     # S14.9: location_plates removed
            pid, _ = self.one_shot({})
            assets.attach(self.p.conn, pid, self.place)
            block = location_pack.director_block(self.p.conn, pid)
        self.assertIn("bắt buộc `plate_view`", block)
        self.assertIn("practical_lights", block)

    def test_the_old_default_keeps_its_cache_key_and_a_choice_changes_it(self):
        pid, _ = self.one_shot({"plate_spot": "plaza_front", "time": "day"})
        default = location_pack.plan(self.p.conn, pid)[0]
        self.assertIn("mặc định", default["view_problem"])
        entry = location_pack.model3d(self.p.conn, self.place)
        sp = location_pack.spot_for(entry, {"plate_spot": "plaza_front"})
        cam = plate_camera.camera_for({"size": "MS", "characters": ["KELLY"]}, sp["at"], sp["facing"], 1.75, 1152 / 2048,
                                      name="shot")["camera"]
        self.assertEqual(default["camera"]["location"], cam["location"])        # same camera as before S5.7 → cached plates kept
        pid2, _ = self.one_shot({"plate_spot": "plaza_front", "time": "day", "plate_view": {"background": "away", "why": "x"}})
        away = location_pack.plan(self.p.conn, pid2)[0]
        self.assertNotEqual(away["key"], default["key"])
        pid3, _ = self.one_shot({"plate_spot": "plaza_front", "time": "night", "plate_view": {"background": "away", "why": "x"},
                                 "practical_lights": [{"kind": "fire", "where": "behind_left", "why": "lửa trại"}]})
        lit = location_pack.plan(self.p.conn, pid3)[0]
        self.assertEqual(lit["camera"]["lights"][0]["type"], "POINT")
        self.assertIsNone(lit["light_problem"])
        pid4, _ = self.one_shot({"plate_spot": "plaza_front", "time": "night", "plate_view": {"background": "away", "why": "x"},
                                 "practical_lights": []})
        dark = location_pack.plan(self.p.conn, pid4)[0]
        self.assertNotEqual(lit["key"], dark["key"])
        self.assertNotIn("lights", dark["camera"])
        self.assertTrue(lit["env"].get("practical"))
        self.assertNotIn("practical", dark["env"])

    def test_a_covered_spot_without_direction_is_not_rendered_and_the_picture_waits(self):
        pid, sid = self.one_shot({"plate_spot": "lower_yard", "time": "night", "practical_lights": []})
        data = os.path.join(self.tmp, "projects")
        idx = location_pack.ensure_plates(self.p.conn, pid, data, self.tmp, (W, H), blender="x", render=self.fake_render)
        self.assertEqual(self.calls, [])                                        # Blender never ran for a guessed direction
        self.assertIn("plate_view", idx[str(sid)]["needs"])
        self.assertIsNone(location_pack.plate_of(data, pid, sid))
        self.assertIsNone(location_pack.plate_failed(data, pid, sid))           # not "failed": the shot waits (runner._wait)
        self.assertIn("plate_view", location_pack.plate_needs(data, pid, sid))
        self.p.conn.execute("UPDATE scenes SET data=json_set(data, '$.plate_view', json(?)) WHERE id=?",
                            (json.dumps({"background": "away", "why": "Kelly nhìn ra phía biển"}), sid))
        self.p.conn.commit()
        idx = location_pack.ensure_plates(self.p.conn, pid, data, self.tmp, (W, H), blender="x", render=self.fake_render)
        rec = idx[str(sid)]
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(os.path.exists(rec["plate"]))
        self.assertEqual(rec["view"]["view"], "away")
        self.assertIn("quay lưng về mốc", rec["layout_vi"])
        self.assertIn("không thêm", rec["layout_vi"])
        self.assertIn("moonlight", location_pack.green_prompt({"size": "MS"}, rec))

    def test_the_render_reference_route_holds_the_shot_and_says_why(self):
        from core import place_refs
        pid, sid = self.one_shot({"plate_spot": "lower_yard", "time": "day"})
        data = os.path.join(self.tmp, "projects")
        shot = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"])
        self.assertTrue(place_refs.missing(self.p.conn, data, pid, sid, shot))          # not planned yet: the render is started
        location_pack.ensure_plates(self.p.conn, pid, data, self.tmp, (W, H), blender="x", render=self.fake_render)
        self.assertFalse(place_refs.missing(self.p.conn, data, pid, sid, shot))         # planned: not re-started at every tick …
        self.assertIn("plate_view", place_refs.needs(data, pid, sid))                   # … held, with what to write

    def test_the_green_prompt_names_the_chosen_light(self):
        pid, sid = self.one_shot({"plate_spot": "lower_yard", "time": "night", "plate_view": {"background": "landmark", "why": "x"},
                                  "practical_lights": [{"kind": "screen", "where": "front", "color": "cool", "why": "đọc tin nhắn"}]})
        data = os.path.join(self.tmp, "projects")
        idx = location_pack.ensure_plates(self.p.conn, pid, data, self.tmp, (W, H), blender="x", render=self.fake_render)
        self.assertEqual(self.calls[0]["cameras"][0]["lights"][0]["type"], "AREA")   # the light goes to Blender with the camera
        text = location_pack.green_prompt({"size": "MS"}, idx[str(sid)])
        self.assertIn("glow of a screen", text)
        self.assertIn("#00FF00", text)

    def test_without_a_plate_the_prompt_still_says_direction_and_light(self):
        pid, _ = self.one_shot({})
        d = {"location_asset": self.place, "plate_spot": "lower_yard", "time": "night",
             "plate_view": {"background": "away", "why": "x"}, "practical_lights": [{"kind": "lamp", "where": "behind", "why": "x"}]}
        text = location_pack.script_sentence(self.p.conn, pid, d)
        self.assertIn("the clock tower is NOT in the frame", text)
        self.assertIn("street / wall lamp", text)
        self.assertEqual(location_pack.script_sentence(self.p.conn, pid, {"location_asset": self.place, "time": "day"}), "")


if __name__ == "__main__":
    unittest.main()
