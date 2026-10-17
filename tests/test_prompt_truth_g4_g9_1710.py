"""17/10 (#31, replay_payload trước gen ảnh): 6 lỗi gốc của chữ prompt ảnh — dữ liệu giả, 0 USD.

G4 chữ Việt của mô tả dạng Kho lọt vào câu khóa đạo cụ ("… tấm kim loại … kịch bản gọi …"); G5 câu ánh sáng tự sinh trái chữ Đạo diễn
(shot không người vẫn "lights the character", đèn bàn thành "street / wall lamp", nắng/trăng trong phòng); G6 câu hướng máy cãi số đo
plate + chữ "villa silhouette … background" còn sót; G7 người ngoài danh sách nhân vật trong chữ; G8 giờ/thời tiết trong chữ trái trường;
G9 ảnh đạo cụ của shot KHÁC trong cảnh đi theo shot không nhắc nó (SKORP ở shot xe nôi)."""
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import assets
from core.db import connect
from core.pipeline import Pipeline
from core.seedance_refs import has_vietnamese

FLAG_ON = {"FEATURE_PROJECT_PROP_LOCK": "1"}
SKORP_DESC = ("[Halloween OB55] Súng tiểu liên SKORP màu đen: báng gập, ống ngắm đỏ nhỏ trên ray. In-game scale: compact SMG ≈ 3 "
              "head-heights long; held two-handed.")
GLUE_DESC = ("Tường keo FF. 2 DẠNG: (a) MẶC ĐỊNH — tường keo màu TRẮNG trơn, không họa tiết, không hình; (b) skin Gloowall OB55 thang "
             "máy (ID 907105556; kịch bản gọi \"skin thang máy\" / \"skin Gloowall\" = dạng này) — tường dạng cửa thang máy kim loại "
             "xám có khung, đèn và mảnh giấy dán, theo ảnh Kho. Shot không nói dạng nào → dạng mặc định.")


class _Db(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("g4-g9")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def asset(self, kind, name, aliases, desc="", variant=None, picture=True):
        c = self.p.conn
        aid = c.execute("INSERT INTO assets (game, kind, name, aliases, description) VALUES ('FF',?,?,?,?)",
                        (kind, name, aliases, desc)).lastrowid
        if picture:
            path = os.path.join(self.tmp, f"{aid}.png")
            with open(path, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
            c.execute("INSERT INTO asset_images (asset_id, path, label, sort, status, variant) VALUES (?,?,?,?,?,?)",
                      (aid, path, "x", 1, "approved", variant))
        c.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?,?)", (self.pid, aid))
        c.commit()
        return aid


class G4PropLockEnglish(_Db):
    def setUp(self):
        super().setUp()
        self.asset("weapon", "SKORP", "súng tiểu liên skorp, Scorpion", SKORP_DESC)
        self.asset("weapon", "Bom keo", "Gloowall", GLUE_DESC, variant="skin Gloowall OB55 thang máy")

    def part(self, prompt):
        from core import prop_lock
        with mock.patch.dict(os.environ, FLAG_ON):
            return prop_lock.prompt_part(self.p.conn, self.pid, {"image_prompt": prompt})

    def test_skin_form_is_sent_in_english_matching_its_picture(self):
        text = self.part("Kelly throws a curved glue wall with the Free Fire skin Gloowall behind her.")
        self.assertIn("Prop lock: Bom keo in this shot — its skin Gloowall OB55 form (metal, grey)", text)
        self.assertIn("as its reference picture shows", text)
        self.assertFalse(has_vietnamese(text), text)
        for vi in ("kịch bản", "tấm kim loại", "thang", "theo ảnh Kho"):
            self.assertNotIn(vi, text)

    def test_default_form_keeps_its_colour_in_english(self):
        text = self.part("Kelly crouches behind a glue wall.")
        self.assertIn("its default form (white)", text)
        self.assertFalse(has_vietnamese(text), text)

    def test_gun_vietnamese_description_is_not_sent_english_scale_is(self):
        text = self.part("Kelly holds the SKORP.")
        self.assertNotIn("Súng tiểu liên", text)
        self.assertNotIn("ice", text)                      # "băng đạn" (magazine) is never turned into a colour
        self.assertIn("Weapon scale: SKORP — compact SMG", text)
        self.assertFalse(has_vietnamese(text), text)

    def test_issues_say_what_goes_instead_of_the_vietnamese_form(self):
        from core import prop_lock
        with mock.patch.dict(os.environ, FLAG_ON):
            msgs = [i["msg"] for i in prop_lock.issues(self.p.conn, self.pid, {"image_prompt": "Kelly behind her skin Gloowall wall."})]
        self.assertTrue(any("mô tả dạng viết tiếng Việt" in m and "skin Gloowall OB55" in m for m in msgs), msgs)

    def test_an_english_form_is_unchanged(self):
        from core import prop_lock
        self.assertEqual(prop_lock.english_form("a grey metal panel wall", "skin X1", True), "a grey metal panel wall")


class G5LightTruth(unittest.TestCase):
    def test_nobody_in_frame_gets_no_character_light(self):
        from core import plate_choice
        data = {"characters": [], "time": "night",
                "practical_lights": [{"kind": "lamp", "where": "left", "color": "warm", "why": "đèn bàn ấm góc phòng"}]}
        lit = plate_choice.lights_of(data, {"time": "night"})
        text = plate_choice.light_sentence(lit["lights"], lit["decided"], "night", data)
        self.assertNotIn("character", text)
        self.assertNotIn("face", text)
        self.assertIn("a desk lamp", text)
        self.assertNotIn("street", text)

    def test_a_dropped_lamp_is_not_a_choice_of_moonlight(self):
        from core import plate_choice
        for chars in ([], ["Kelly"]):
            data = {"characters": chars, "practical_lights": [{"kind": "lamp", "where": "background_left", "why": "đèn bàn"}]}
            lit = plate_choice.lights_of(data, {"time": "night"})
            self.assertEqual(lit["lights"], [])
            self.assertEqual(plate_choice.light_sentence(lit["lights"], lit["decided"], "night", data), "")
        said = {"characters": ["Kelly"], "practical_lights": []}
        self.assertIn("moonlight", plate_choice.light_sentence([], True, "night", said))
        self.assertEqual(plate_choice.light_sentence([], True, "night", {"characters": [], "practical_lights": []}), "")

    def test_lamp_named_by_its_own_words_never_street_by_default(self):
        from core import plate_choice
        self.assertEqual(plate_choice.lamp_name({"why": "đèn bàn góc phòng"}), "a desk lamp")
        self.assertEqual(plate_choice.lamp_name({"why": "x"}, {"lighting": "đèn đường vàng hắt"}), "a street lamp")
        self.assertEqual(plate_choice.lamp_name({"why": "x"}), "a lamp")
        self.assertEqual(plate_choice.lamp_name({"why": "đen bán chạy"}), "a lamp")       # accents differ: not "đèn bàn"
        lit = plate_choice.lights_of({"characters": ["Kelly"], "practical_lights": [{"kind": "lamp", "where": "left", "why": "x"}]},
                                     {"time": "night"})
        self.assertNotIn("street / wall", plate_choice.light_sentence(lit["lights"], True, "night", {"characters": ["Kelly"]}))

    def test_sun_main_light_not_said_indoors_or_without_people(self):
        from core import location_pack
        rec = {"camera_plan": {"location": [0, 0, 1.6], "look_at": [0, 10, 1.6]}}
        self.assertTrue(location_pack.light_words(rec, 90.0, {"characters": ["Kelly"]}).startswith("Main light"))
        self.assertEqual(location_pack.light_words(rec, 90.0, {"characters": []}), "")
        indoor = {"camera_plan": dict(rec["camera_plan"], indoor={"exposure": 1.5})}
        self.assertEqual(location_pack.light_words(indoor, 90.0, {"characters": ["Kelly"]}), "")
        self.assertTrue(location_pack.light_words(indoor, 90.0).startswith("Main light"))        # no data: as before


class G6PlateTruth(unittest.TestCase):
    GROUND_OUT = ("Background — measured on the 3D map of Cổng Trời for this exact camera, as Image 1 shows it: the villa is outside this "
                  "frame (not visible); the horizon line at 33% from the top. Draw the background only as Image 1 shows it: the same "
                  "buildings, walls, trees and landmark in the same places and sizes, nothing added, moved or removed.")
    TOWARDS = (" Camera direction chosen for this shot: the camera looks towards the villa: the villa is behind the character (as far as "
               "the walls around let it be seen — the 3D render decides).")

    def test_direction_sentence_that_contradicts_the_measure_leaves(self):
        from core import plate_anchor
        refs = [{"role": plate_anchor.ROLE, "label": "r", "path": "p"}]
        out = plate_anchor.fit_ground("Scene: x. " + self.GROUND_OUT + self.TOWARDS + " Camera and scale: 32 mm lens.", refs)
        self.assertNotIn("Camera direction chosen", out)
        self.assertIn("the villa is outside this frame", out)
        self.assertIn("Camera and scale: 32 mm lens.", out)
        away = " Camera direction chosen for this shot: the camera looks away from the villa: the villa is NOT in the frame."
        self.assertIn("Camera direction chosen", plate_anchor.fit_ground("Scene: x. " + self.GROUND_OUT + away, refs))
        seen = self.GROUND_OUT.replace("the villa is outside this frame (not visible)",
                                       "the villa stands about 30 m from the main character, in the middle of the frame")
        self.assertNotIn("Camera direction chosen", plate_anchor.fit_ground("Scene: x. " + seen + away, refs))
        self.assertIn("Camera direction chosen", plate_anchor.fit_ground("Scene: x. " + seen + self.TOWARDS, refs))

    def test_landmark_silhouette_in_the_background_is_stripped(self):
        from core import plate_anchor
        cases = {
            "Kelly in her ghost form stepping through a gap in tall hedge walls, low ground fog, cold purple-red moonlight from behind, "
            "the villa silhouette faint in the far background between hedge tops.": "villa silhouette",
            "Thick fog drifts low around her legs, dark hedge walls and the villa's pale silhouette faint in the background.":
                "villa's pale silhouette",
            "The villa rooftop is faintly visible beyond the hedges under the dark swirling sky.": "villa rooftop",
        }
        for text, gone in cases.items():
            out, removed = plate_anchor.strip_scenery(text, ["Kelly"])
            self.assertNotIn(gone, out, out)
            self.assertTrue(removed)
        out, _ = plate_anchor.strip_scenery(list(cases)[0], ["Kelly"])
        self.assertIn("cold purple-red moonlight from behind", out)
        self.assertIn("Kelly in her ghost form", out)
        out, _ = plate_anchor.strip_scenery(list(cases)[1], ["Kelly"])
        self.assertIn("Thick fog drifts low around her legs", out)
        for keep in ("Kelly runs toward the villa in the distance.", "Warm light spills from the house beyond the hedge.",
                     "Enemies stand by the tower in the background.",
                     "Four enemy characters fight, far distance near the stone plaza of the Clock Tower."):
            self.assertEqual(plate_anchor.strip_scenery(keep, ["Kelly"])[0], keep)


class G7CastLeaks(_Db):
    def setUp(self):
        super().setUp()
        self.asset("character", "LÍNH ĐỊCH ÁO CHOÀNG", "Cloaked Terror, trang phục lính địch, Tai họa", picture=False)
        self.asset("character", "XÚC TU ĐỎ", "Red Slicker", picture=False)
        self.asset("character", "YÊU NỮ TÀ LINH DẠNG 1", "", picture=False)
        self.asset("character", "YÊU NỮ TÀ LINH DẠNG 2", "", picture=False)

    def test_a_person_outside_the_cast_is_reported(self):
        from core import shot_text_checks as st
        shot = {"characters": ["Kelly", "Xúc tu đỏ"], "image_prompt": "Kelly faces a figure in a black Cloaked Terror trenchcoat with a "
                                                                      "white mask; the Red Slicker waits."}
        leaks = st.cast_leaks(self.p.conn, self.pid, shot)
        self.assertEqual([x["who"] for x in leaks], ["LÍNH ĐỊCH ÁO CHOÀNG"])
        self.assertEqual(leaks[0]["said"], ["Cloaked Terror"])
        msgs = st.issues(self.p.conn, self.pid, shot)
        self.assertTrue(any(i["part"] == "nhan_vat" and "Cloaked Terror" in i["msg"] for i in msgs), msgs)

    def test_cast_members_and_near_names_are_not_reported(self):
        from core import shot_text_checks as st
        ok = {"characters": ["Kelly", "Lính địch áo choàng"], "image_prompt": "Kelly fights the Cloaked Terror."}
        self.assertEqual(st.cast_leaks(self.p.conn, self.pid, ok), [])
        two = {"characters": ["Yêu nữ tà linh dạng 2"], "image_prompt": "Yêu nữ tà linh dạng 2 floats; tài hoa xa."}
        self.assertEqual(st.cast_leaks(self.p.conn, self.pid, two), [])       # dạng 2 ≠ dạng 1; "tài hoa" ≠ "Tai họa" (accents)

    def test_formula_check_carries_it(self):
        from core import prompt_formula as pf
        shot = {"characters": ["Kelly"], "image_prompt": "Kelly and the Cloaked Terror.", "time": "dawn",
                "weather": "clear"}
        self.assertTrue(any("Cloaked Terror" in i["msg"] for i in pf._text_issues(self.p.conn, self.pid, shot)))


class G8TimeWeather(unittest.TestCase):
    def test_night_words_on_a_dawn_clear_shot(self):
        from core import shot_text_checks as st
        msgs = st.time_weather_conflicts({"time": "dawn", "weather": "clear",
                                          "image_prompt": "Kelly under a cold violet-red night sky, thin fog drifting low."})
        self.assertEqual(len(msgs), 2, msgs)
        self.assertIn("night", msgs[0])
        self.assertIn("fog", msgs[1])

    def test_no_false_alarms(self):
        from core import shot_text_checks as st
        for data in ({"time": "night", "weather": "fog", "image_prompt": "night sky, fog, the edge beginning to brighten with dawn"},
                     {"time": "day", "weather": "clear", "image_prompt": "A Red Slicker in a red rain coat, no fog, bright daylight."},
                     {"time": "", "weather": "", "image_prompt": "night, rain"},
                     {"time": "dawn", "weather": "fog", "image_prompt": "Kelly runs; mist everywhere."}):
            self.assertEqual(st.time_weather_conflicts(data), [], data)


class G9OwnShotProps(unittest.TestCase):
    def test_a_prop_named_only_by_another_shot_is_not_sent(self):
        from core import scene_storyboard

        def fake(conn, pid, data, limit=8, **kw):
            out = [{"path": "kelly.png", "label": "KELLY", "role": "character"}, {"path": "place.png", "label": "Cổng Trời",
                                                                                 "role": "location"}]
            if "SKORP" in data.get("image_prompt", ""):
                out.append({"path": "skorp.png", "label": "SKORP", "role": "object"})
            if "pram" in data.get("image_prompt", ""):
                out.append({"path": "pram.png", "label": "XE NÔI", "role": "object"})
            return out[:limit]
        shots = [{"id": 1, "idx": 10, "data": {"characters": ["KELLY"], "image_prompt": "the pram glows"}},
                 {"id": 2, "idx": 12, "data": {"characters": ["KELLY"], "image_prompt": "Kelly lifts the SKORP"}}]
        with mock.patch.object(assets, "scene_references", side_effect=fake):
            pram = scene_storyboard.shared_references(None, 31, shots, cast_of=shots[0]["data"])
            gun = scene_storyboard.shared_references(None, 31, shots, cast_of=shots[1]["data"])
            whole = scene_storyboard.shared_references(None, 31, shots)
        self.assertNotIn("SKORP", [r["label"] for r in pram])
        self.assertIn("XE NÔI", [r["label"] for r in pram])
        self.assertIn("Cổng Trời", [r["label"] for r in pram])
        self.assertIn("SKORP", [r["label"] for r in gun])
        self.assertNotIn("XE NÔI", [r["label"] for r in gun])
        self.assertIn("SKORP", [r["label"] for r in whole])        # the scene-wide list (no frame) is unchanged


if __name__ == "__main__":
    unittest.main()
