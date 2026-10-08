"""F1-B (09/10, dự án #24 — teaser kinh dị Kelly + yêu nữ trồi từ giếng): 3 câu ghép prompt sai, sửa cho MỌI dự án.
1. "Natural human eyes, no glowing eyes." gắn cho cả quái mà Đạo diễn tả "eyes: glowing red" → chỉ gắn khi mọi nhân vật trong khung
   là người và không ai được tả mắt phát sáng; gắn thì nói rõ cho ai.
2. Luật tầng 1 (người dùng chốt 09/10): dự án game FF — máu, tóc bết, vết thương, xác chỉ được GỢI (bóng tối, ngoài nét, bị che),
   ảnh thì "everything in focus" không áp cho các chi tiết đó.
3. Shot có render 3D chỗ đứng: câu địa điểm chung chung ("… grass, palms, sea") kéo ảnh trái render → câu KHÓA NỀN theo công thức #22."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import assets, looks, seedance_refs as sr
from core.db import connect
from core.pipeline import Pipeline

CREATURE = "YÊU NỮ TÀ LINH DẠNG 1"
CREATURE_DESC = "faceless black-skinned female creature with glowing red eyes"


def _project(game: str = "FF"):
    p = Pipeline(connect())
    pid = p.create_project("f1b")
    p.conn.execute("UPDATE projects SET game=? WHERE id=?", (game, pid))
    p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?,?,?)", (pid, "KELLY", "young woman, black hair"))
    p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?,?,?)", (pid, CREATURE, CREATURE_DESC))
    p.conn.commit()
    return p, pid


class EyesGuardTest(unittest.TestCase):
    STRONG = {"intensity": 4, "face": "mouth opens wide", "eyes": "wide, fixed on the well"}

    def test_creature_in_frame_gets_no_human_eyes_rule(self):
        p, pid = _project()
        d = {"size": "MS", "characters": ["KELLY", CREATURE], "performance": dict(self.STRONG), "action": "the creature rises from the well"}
        humans = assets.cast_humans(p.conn, pid, d["characters"])
        self.assertTrue(humans["KELLY"])
        self.assertFalse(humans[CREATURE])
        text = sr.shot_motion(d, humans=humans)
        self.assertNotIn("no glowing eyes", text)
        self.assertNotIn("Natural human eyes", text)
        group = sr.prompt([(text, 3.0)], [("KELLY", "k.png"), (CREATURE, "y.png")])
        self.assertNotIn("glowing eyes", group)

    def test_creature_known_by_name_even_without_the_profile(self):
        d = {"size": "MS", "characters": [CREATURE], "performance": dict(self.STRONG), "action": "rises"}
        self.assertNotIn("no glowing eyes", sr.shot_motion(d))

    def test_glowing_eyes_written_by_the_director_win(self):
        d = {"size": "CU", "characters": ["KELLY"], "performance": dict(self.STRONG, eyes="glowing red"), "action": "x"}
        self.assertNotIn("no glowing eyes", sr.shot_motion(d, humans={"KELLY": True}))

    def test_people_only_keep_the_guard_and_it_names_them(self):
        p, pid = _project()
        d = {"size": "CU", "characters": ["KELLY"], "performance": dict(self.STRONG), "action": "Kelly stares"}
        text = sr.shot_motion(d, humans=assets.cast_humans(p.conn, pid, ["KELLY"]))
        self.assertIn("KELLY: natural human eyes, no glowing eyes", text)

    def test_code_motion_reads_the_profiles(self):
        p, pid = _project()
        self.assertFalse(assets.is_human(p.conn, pid, CREATURE))
        self.assertTrue(assets.is_human(p.conn, pid, "KELLY"))
        self.assertTrue(assets.looks_non_human("Bóng ma áo trắng"))
        self.assertFalse(assets.looks_non_human("cô gái mặc áo màu đỏ"))
        self.assertTrue(assets.looks_non_human("a ghost girl"))
        self.assertFalse(assets.looks_non_human("Kelly, ghostwriter? no — a girl in a red jacket"))


class GoreRestraintTest(unittest.TestCase):
    PROMPT = ("Close-up of the stone well rim at night, black hair strands and blood stains on the rim, moss, everything in focus.")

    def test_ff_image_prompt_hints_the_gore(self):
        p, pid = _project("FF")
        text, _ = __import__("core.runner", fromlist=["x"]).build_image_prompt(p.conn, pid, {"image_prompt": self.PROMPT})
        self.assertIn("only hinted", text)
        self.assertIn("in deep shadow", text)
        self.assertIn("everything in focus except those hinted details", text)

    def test_other_game_is_unchanged(self):
        p, pid = _project("PUBG")
        from core.runner import build_image_prompt
        text, _ = build_image_prompt(p.conn, pid, {"image_prompt": self.PROMPT})
        self.assertNotIn("only hinted", text)
        self.assertIn("everything in focus.", text)

    def test_no_gore_no_sentence_and_vietnamese_without_folding(self):
        proj = {"game": "FF"}
        self.assertEqual(looks.gore_restraint(proj, "Kelly in a red jacket, màu đỏ, everything in focus."),
                         "Kelly in a red jacket, màu đỏ, everything in focus.")
        self.assertIn("only hinted", looks.gore_restraint(proj, "vũng máu dưới giếng"))
        self.assertEqual(looks.gore_restraint(proj, "chính xác vị trí"), "chính xác vị trí")     # "xác" ≠ xác chết
        self.assertEqual(looks.gore_restraint(proj, "bloodline legend"), "bloodline legend")    # \b

    def test_video_runner_adds_it_within_the_limit_and_says_so(self):
        from core.providers import MockVideoProvider
        from core.runner import VideoRunner
        p, pid = _project("FF")
        job = {"id": 1, "project_id": pid, "scene_id": 1}
        vr = VideoRunner(p, MockVideoProvider(), tempfile.mkdtemp())
        group = [{"data": {"image_prompt": self.PROMPT, "action": "Kelly steps back"}}]
        out = vr._gore_restraint(job, p.project(pid), "Shot 1: Kelly steps back from the well.", group, "dreamina-seedance-2-0-260128")
        self.assertIn("only hinted", out)
        self.assertFalse(sr.has_vietnamese(out))
        self.assertTrue(p.conn.execute("SELECT 1 FROM diag_events WHERE code='gore_restraint'").fetchone())
        long = "x" * 3990
        self.assertEqual(vr._gore_restraint(job, p.project(pid), long, group, "dreamina-seedance-2-0-260128"), long)   # never past 4000
        q, qid = _project("PUBG")
        self.assertEqual(vr._gore_restraint(job, q.project(qid), "Shot 1: x.", group, "kling"), "Shot 1: x.")

    def test_vietnamese_gore_gives_an_english_sentence(self):
        out = looks.gore_restraint({"game": "FF"}, "Shot 1: x.", video=True, scan="vũng máu dưới giếng")
        self.assertIn("the blood and wounds only hinted", out)
        self.assertFalse(sr.has_vietnamese(out))

    def test_video_prompt_gets_the_short_sentence(self):
        out = looks.gore_restraint({"game": "FF"}, "Shot 1: the creature drags a corpse.", video=True)
        self.assertIn("only hinted", out)
        self.assertLess(len(out) - len("Shot 1: the creature drags a corpse."), 200)


class RenderLockTest(unittest.TestCase):
    PLACE = {"id": 5, "name": "Tháp Đồng Hồ", "images": [],
             "description": "Real map: the clock tower stands directly on a wide, flat, open stone plaza; 1-2 storey red-roof houses, "
                            "grass, palms, sea around."}

    def _prompt(self, place_render: bool):
        from core.runner import build_image_prompt
        p, pid = _project()
        with mock.patch.object(assets, "scene_location", return_value=self.PLACE):
            text, _ = build_image_prompt(p.conn, pid, {"image_prompt": "Kelly walks to the well"}, place_render=place_render)
        return text

    def test_render_shot_gets_the_background_lock(self):
        text = self._prompt(True)
        self.assertNotIn("grass, palms, sea", text)
        self.assertIn("Background: exactly the 3D render picture of this place", text)
        self.assertIn("keep the scale of the objects as in that picture", text)

    def test_shot_without_render_keeps_the_place_words(self):
        self.assertIn("grass, palms, sea", self._prompt(False))

    def test_runner_names_the_render_picture_by_number(self):
        from core import place_refs, shots, llm_runner
        from core.providers import MockImageProvider
        from core.runner import ImageRunner
        from tests.test_v3 import kenta_project
        p, pid = kenta_project(shot_mode="per_shot")
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        row = shots.shots_of(p, pid)[0]
        d = tempfile.mkdtemp()
        plate = os.path.join(d, "plate.png")
        with open(plate, "wb") as f:
            f.write(b"x")
        ref = {"path": plate, "label": "Tháp Đồng Hồ", "role": "place_render", "_rec": {}}
        job = p.create_job(row["id"], "image_gen")
        with mock.patch.object(place_refs, "enabled", return_value=True), \
                mock.patch.object(place_refs, "shot_ref", return_value=ref), \
                mock.patch.object(place_refs, "geometry_sentence", return_value=""), \
                mock.patch.object(assets, "scene_location", return_value=self.PLACE):
            args = ImageRunner(p, MockImageProvider(), d)._submit_args(p.job(job))
        prompt, paths = args[0], args[1]
        n = paths.index(plate) + 1
        self.assertIn(f"3D render picture of this place (Image {n})", prompt)
        self.assertNotIn("{{", prompt)                                    # the placeholder never reaches the model
        self.assertNotIn("PLACE_RENDER", prompt)
        self.assertNotIn("grass, palms, sea", prompt)


if __name__ == "__main__":
    unittest.main()
