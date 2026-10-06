"""S4.6 (#10, 2026-09-29): a KELLY-only and a KENTA-only storyboard frame were sent the pictures of Kelly, Kenta and Maxim (the whole
scene's cast — jobs 453-456 sent_refs) and came back with all three people. Each frame now gets only its own people's pictures; the
place stays shared, and the anchor frame sent with a later frame is said to give the place, not its people."""
import unittest
from unittest import mock

from core import scene_storyboard

PICS = {"KELLY": ("KELLY", "10.png"), "KENTA": ("Kenta ở OB55", "1.png"), "MAXIM": ("MAXIM", "7.png")}


def fake_refs(conn, pid, data, limit=8, **kw):
    """assets.scene_references as it answered for #10: each named person (asset label), then the place."""
    out = [{"path": PICS[n][1], "label": PICS[n][0], "role": "character"} for n in data.get("characters") or []]
    if data.get("location"):
        out.append({"path": "4.png", "label": "Tháp Đồng Hồ", "role": "location"})
    return out[:limit]


def scene():
    place = "Tháp Đồng Hồ, quảng trường tầng trên, ban ngày"
    shots = [{"id": 171, "idx": 1, "data": {"characters": ["KELLY"], "location": place, "size": "WS"}},
             {"id": 172, "idx": 2, "data": {"characters": ["KENTA"], "location": place, "size": "MS"}},
             {"id": 173, "idx": 3, "data": {"characters": ["MAXIM"], "location": place, "size": "MCU"}}]
    return {"shots": shots, "anchor": shots[0], "index": 0, "story_scene": 1}


class CastRefsTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("core.assets.scene_references", side_effect=fake_refs)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_without_cast_of_every_person_of_the_scene_goes(self):       # the old behaviour, still the scene-wide list
        labels = [r["label"] for r in scene_storyboard.shared_references(None, 10, scene()["shots"])]
        self.assertEqual(labels, ["KELLY", "Tháp Đồng Hồ", "Kenta ở OB55", "MAXIM"])

    def test_a_one_person_frame_gets_only_that_persons_picture(self):
        g = scene()
        for shot, who in zip(g["shots"], ("KELLY", "Kenta ở OB55", "MAXIM")):
            refs = scene_storyboard.shared_references(None, 10, g["shots"], cast_of=shot["data"])
            people = [r["label"] for r in refs if r["role"] in scene_storyboard.PERSON_ROLES]
            self.assertEqual(people, [who])
            self.assertIn("Tháp Đồng Hồ", [r["label"] for r in refs])                   # the place stays shared

    def test_a_group_frame_keeps_its_whole_cast(self):
        g = scene()
        three = {"characters": ["KELLY", "KENTA", "MAXIM"], "location": "x"}
        refs = scene_storyboard.shared_references(None, 10, g["shots"], cast_of=three)
        self.assertEqual({r["label"] for r in refs if r["role"] == "character"}, {"KELLY", "Kenta ở OB55", "MAXIM"})

    def test_the_anchor_frame_is_said_to_give_the_place_not_its_people(self):
        g = scene()
        note = scene_storyboard.anchor_note(g, 172, 3)
        self.assertIn("Image 3 is frame 1", note)
        self.assertIn("KELLY is in frame 1 but NOT in this frame", note)
        self.assertEqual(scene_storyboard.anchor_note(g, 171, 3), "")                # the anchor itself
        g["shots"][1]["data"]["characters"] = ["KELLY", "KENTA"]
        self.assertEqual(scene_storyboard.anchor_note(g, 172, 3), "")                # same people as the anchor

    def test_cast_note_no_longer_says_the_others_pictures_are_sent(self):
        note = scene_storyboard.cast_note(scene(), 171)
        self.assertIn("Only KELLY is in this frame", note)
        self.assertNotIn("pictures are references", note)


if __name__ == "__main__":
    unittest.main()
