"""F1-C (09/10): ghép prompt ảnh + motion Seedance theo KHUÔN công thức (docs/CONG_THUC_PROMPT_F0_NHAP_2026-10-09.md mục 3–4):
phong cách → khung → nhân vật + hành động (+ câu sửa) → nền → ánh sáng → khóa/luật → chốt chất lượng; ngắt câu đúng; bỏ câu trùng
nghĩa; trang phục một nguồn (hồ sơ Kho); tả cái đúng thay vì liệt kê vật cấm (bài học L2). Test đỏ trước khi sửa."""
import json
import unittest
from unittest import mock

from core import assets, prompt_formula as pf, seedance_refs as sr
from core.db import connect
from core.pipeline import Pipeline

KELLY = "KELLY KL"
CREATURE = "YÊU NỮ TÀ LINH DẠNG 1"
KELLY_LOCK = {"must_keep": "red hoodie with the GREEN fire-breathing dinosaur print, black sleeves, black mask worn up over mouth and nose",
              "forbidden": "mask pulled down"}


def _project(game="FF", look="FF_INGAME"):
    p = Pipeline(connect())
    pid = p.create_project("f1c")
    p.conn.execute("UPDATE projects SET game=?, look=? WHERE id=?", (game, look, pid))
    p.conn.execute("INSERT INTO characters (project_id, name, description, lock_rules) VALUES (?,?,?,?)",
                   (pid, KELLY, "young woman", json.dumps(KELLY_LOCK)))
    p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?,?,?)",
                   (pid, CREATURE, "faceless black-skinned female creature with glowing red eyes"))
    p.conn.commit()
    return p, pid


BEDROOM = {"id": 7, "name": "Nhà Kelly", "images": [], "description": "Kelly's house by the sea, palms and a plaza outside."}
PLAZA = {"id": 5, "name": "Tháp Đồng Hồ", "images": [],
         "description": "Real map: the clock tower stands on a wide, flat stone plaza; red-roof houses, grass, palms, sea around."}

SHOT_22 = {"size": "MS", "angle": "eye", "characters": [KELLY],
           "image_prompt": "Free Fire in-game 3D render, stylized proportions, moderate texture detail, KELLY KL, 17-year-old girl, "
                           "stands beside the bed in her red hoodie, everything in focus, not blurred background",
           "blocking": "KELLY KL frame-left, facing right toward the bed",
           "action_peak": "mid-step toward the bed"}
SHOT_24 = {"size": "WS", "angle": "low", "characters": [KELLY, CREATURE],
           "image_prompt": "Night plaza, the creature rises from the well, blood stains on the rim, KELLY KL steps back, everything "
                           "in focus",
           "blocking": "KELLY KL frame-right looking at the well frame-left",
           "performance": {"face": "fear", "eyes": "wide, fixed on the well", "body": "leaning back"}}


def _build(shot, place, indoor=None, render=False, fix=None, light=""):
    from core import runner
    p, pid = _project()
    with mock.patch.object(assets, "scene_location", return_value=place), \
            mock.patch.object(runner, "indoor_spot", return_value=indoor):
        text, _ = runner.build_image_prompt(p.conn, pid, dict(shot), fix=fix, place_render=render, light=light)
    return text


class ImageOrderTest(unittest.TestCase):
    def test_parts_follow_the_formula_order_and_the_fix_follows_the_action(self):
        text = _build(SHOT_22, BEDROOM, indoor="Kelly's bedroom", fix="keep the mask up over the nose",
                      light="Soft window light from the left.")
        order = [text.index("Render style"), text.index("Framing:"), text.index("stands beside the bed"), text.index("Blocking:"),
                 text.index("Fix: keep the mask"), text.index("Setting: INSIDE a room"), text.index("Soft window light"),
                 text.index("Identity lock"), text.index("Background in focus")]
        self.assertEqual(order, sorted(order), text)

    def test_every_part_ends_its_sentence(self):
        text = _build(SHOT_22, BEDROOM, indoor="Kelly's bedroom", fix="keep the mask up")
        self.assertEqual([m.group(0) for m in pf._RUNON.finditer(text) if m.group(1).lower() not in pf._RUNON_STOP], [])
        self.assertNotIn("..", text)
        self.assertIn("facing right toward the bed.", text)               # the blocking part is closed before the next one

    def test_same_meaning_said_once(self):
        text = _build(SHOT_22, BEDROOM, indoor="Kelly's bedroom")
        self.assertEqual(text.lower().count("stylized"), 1, text)          # the Director's style clause gives way to the look sentence
        self.assertEqual(text.lower().count("everything in focus"), 1)
        self.assertNotIn("not blurred background", text)                   # = the look's "background in focus"
        self.assertIn("KELLY KL", text)

    def test_other_project_keeps_the_director_words(self):
        from core import runner
        p, pid = _project("PUBG", None)
        text, _ = runner.build_image_prompt(p.conn, pid, {"image_prompt": "Free Fire in-game 3D render, Kelly waves, everything in focus"})
        self.assertIn("Free Fire in-game 3D render, Kelly waves, everything in focus.", text)


class ProtectionsKeptTest(unittest.TestCase):
    def test_22_bedroom_outfit(self):
        text = _build(SHOT_22, BEDROOM, indoor="Kelly's bedroom")
        self.assertNotIn("17-year-old", text)                                      # no_minor_age
        self.assertIn("Render style: Garena Free Fire in-game 3D character art", text)   # look sentence
        self.assertIn("Identity lock — KELLY KL", text)
        self.assertIn("any other colour word for these garments is wrong", text)
        self.assertIn("INSIDE a room — Kelly's bedroom", text)
        self.assertNotIn("palms", text)                                            # indoor: the outdoor words stay out
        self.assertIn("mid-motion, not a standing pose", text)                     # action_peak
        self.assertIn("The gaze follows the blocking exactly", text)

    def test_24_night_plaza_creature(self):
        text = _build(SHOT_24, PLAZA, render=True)
        self.assertIn("Gore restraint:", text)
        self.assertIn("everything in focus except those hinted details", text)
        self.assertIn("Background: exactly the 3D render picture of this place", text)
        self.assertNotIn("grass, palms, sea", text)
        self.assertIn("Acting", text)
        self.assertLess(text.index("Gore restraint:"), text.index("Background in focus"))
        self.assertLess(text.index("Background: exactly"), text.index("Identity lock"))


class MotionTemplateTest(unittest.TestCase):
    OUTFIT = "KELLY KL wears the red hoodie with the GREEN dinosaur print, black sleeves and the black mask up."

    def test_shot_text_puts_the_action_before_the_camera(self):
        t = sr.shot_motion({"size": "MS", "angle": "eye", "camera_move": "static", "action": "Kenta runs to the tower",
                            "end_state": "he stops at the door"})
        self.assertLess(t.index("Kenta runs"), t.index("camera static"))
        self.assertLess(t.index("camera static"), t.index("no sliding"))

    def test_group_says_the_costume_once_and_stays_in_the_limit(self):
        parts = [(f"Kelly spins {k}. {self.OUTFIT} The bedroom walls stay still.", 2.0) for k in ("once", "twice", "again")]
        text = sr.prompt(parts, [(KELLY, "k.png"), (KELLY + sr.OUTFIT_TAG, "o.png")], model="seedance")
        self.assertEqual(text.count("GREEN dinosaur print"), 1, text)
        self.assertLessEqual(len(text), sr.prompt_limit("seedance"))
        self.assertLess(text.index("Shot 3:"), text.index("GREEN dinosaur print"))          # what changes first
        self.assertLess(text.index("Image 1 is the storyboard frame"), text.index("Shot 1:"))  # the start point first
        self.assertIn("any other colour word for these garments is wrong", text)
        self.assertEqual(sr._estimated_len([{"data": {"characters": [KELLY], "action": "x"}}] * 2, dressed={KELLY}) >
                         sr._estimated_len([{"data": {"characters": [KELLY], "action": "x"}}] * 2), True)

    def test_limit_comes_from_the_model_rules(self):
        self.assertEqual(sr.prompt_limit("dreamina-seedance-2-5-260628"), 5000)
        self.assertEqual(sr.prompt_limit("seedance"), 4000)


class OutfitVsProfileTest(unittest.TestCase):
    PROFILE = {KELLY: "red hoodie with the GREEN fire-breathing dinosaur print, black sleeves"}

    def test_other_colour_is_red(self):
        out = pf.outfit_vs_profile("KELLY KL in the red hoodie with the blue dinosaur print", [KELLY], self.PROFILE)
        self.assertEqual([i["level"] for i in out], ["red"])
        self.assertIn("dinosaur print", out[0]["msg"])

    def test_same_colour_passes(self):
        self.assertEqual(pf.outfit_vs_profile("KELLY KL, red hoodie with a green dinosaur print", [KELLY], self.PROFILE), [])

    def test_lint_reads_the_profile_from_the_lock(self):
        p, pid = _project()
        chars = pf._chars(p.conn, pid)
        data = {"characters": [KELLY], "blocking": "KELLY KL frame-left in the blue dinosaur print hoodie"}
        found = pf.lint_image("Free Fire in-game 3D render, KELLY KL by the bed, soft window light.", data, chars)
        self.assertTrue(any(i["part"] == "nhan_vat" and i["level"] == "red" for i in found), found)


class NegativeListTest(unittest.TestCase):
    def test_listing_forbidden_things_warns(self):
        found = pf.lint_image("Free Fire in-game 3D render, Kelly on the stairs, sunlight. Do NOT add palm trees, grass fields, cars.", {})
        self.assertTrue(any(i["part"] == "ta_cai_dung" and i["level"] == "warn" for i in found), found)
        found = pf.lint_motion("The clip starts on the first image. Kelly walks, static camera. No trees, no cars.", {})
        self.assertTrue(any(i["part"] == "ta_cai_dung" for i in found))

    def test_one_negation_or_a_style_negation_is_fine(self):
        for ok in ("Kelly on the stairs, sunlight, no legs or full body.", "Kelly, sunlight; not anime, no depth-of-field blur, no film "
                   "colour grading."):
            self.assertFalse(any(i["part"] == "ta_cai_dung" for i in pf.lint_image(ok, {})), ok)

    def test_code_indoor_sentence_names_what_is_right(self):
        text = _build(SHOT_22, BEDROOM, indoor="Kelly's bedroom")
        self.assertNotIn("no plaza", text)
        self.assertFalse(any(i["part"] == "ta_cai_dung" for i in pf.lint_image(text, {})))


if __name__ == "__main__":
    unittest.main()
