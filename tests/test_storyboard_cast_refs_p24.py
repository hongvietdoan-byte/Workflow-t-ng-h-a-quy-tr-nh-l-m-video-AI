"""#24 shot 9 (11/10, jobs 645/646/647/648/649/650/651): YÊU NỮ TÀ LINH DẠNG 2 is in the frame (characters + byd.thanh_phan) and has two
library pictures (asset 419), yet the storyboard package held only KELLY (4 pictures) + the well + place renders. Cause:
scene_storyboard.shared_references walked the scene's shots in order with an 8-picture cap and de-duplicated by FILE only — KELLY got a
different 2nd picture per shot (scene-aware pick: 12.png, 16.png, 15.png) and each shot added another place picture (1/2/3.png), so the
cap was full before shot 7 (the first shot with DẠNG 2) was reached. Now every person of the frame being drawn comes first, with the
pictures picked for THIS shot; places and props of the scene fill the rest."""
import unittest
from unittest import mock

from core import scene_storyboard

KELLY_2ND = {1: "12.png", 2: "16.png", 3: "15.png", 4: "15.png", 9: "16.png", 10: "16.png"}
FILES = {"YÊU NỮ TÀ LINH DẠNG 1": ("418/1.jpg", "418/2.jpg"), "YÊU NỮ TÀ LINH DẠNG 2": ("419/1.jpg", "419/2.jpg")}


def fake_refs(conn, pid, data, limit=8, **kw):
    """assets.scene_references as it answered for #24 (scene-aware 2nd picture of KELLY, a different place picture per shot)."""
    out = []
    for n in data.get("characters") or []:
        files = ("10.png", KELLY_2ND[data["shot_no"]]) if n == "KELLY" else FILES[n]
        out += [{"path": f, "label": n, "role": "character"} for f in files]
    out.append({"path": f"263/{data['shot_no'] % 3 + 1}.png", "label": "Tháp Đồng Hồ", "role": "location"})
    out.append({"path": "420/2.png", "label": "GIẾNG ĐÁ CỔ", "role": "object"})
    return out[:limit]


def p24_shots():
    cast = {1: ["KELLY"], 2: ["KELLY"], 3: ["KELLY"], 4: ["KELLY"], 5: ["YÊU NỮ TÀ LINH DẠNG 1"], 6: ["YÊU NỮ TÀ LINH DẠNG 1"],
            7: ["YÊU NỮ TÀ LINH DẠNG 1", "YÊU NỮ TÀ LINH DẠNG 2"], 8: ["YÊU NỮ TÀ LINH DẠNG 2"],
            9: ["KELLY", "YÊU NỮ TÀ LINH DẠNG 2"], 10: ["KELLY", "YÊU NỮ TÀ LINH DẠNG 2"]}
    return [{"id": 256 + n, "idx": n, "data": {"shot_no": n, "characters": who, "location": "Tháp Đồng Hồ"}} for n, who in cast.items()]


class P24CastRefsTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("core.assets.scene_references", side_effect=fake_refs)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_every_person_of_the_frame_gets_its_pictures_even_late_in_a_long_scene(self):
        shots = p24_shots()
        for n in (9, 10):
            own = shots[n - 1]["data"]
            refs = scene_storyboard.shared_references(None, 24, shots, cast_of=own)
            people = [(r["label"], r["path"]) for r in refs if r["role"] in scene_storyboard.PERSON_ROLES]
            self.assertEqual(people, [("KELLY", "10.png"), ("KELLY", KELLY_2ND[n]),
                                      ("YÊU NỮ TÀ LINH DẠNG 2", "419/1.jpg"), ("YÊU NỮ TÀ LINH DẠNG 2", "419/2.jpg")])
            self.assertIn("GIẾNG ĐÁ CỔ", [r["label"] for r in refs])            # the well (a prop of the scene) still goes
            self.assertLessEqual(len(refs), 8)

    def test_one_person_gets_one_set_of_pictures_not_one_per_shot(self):
        shots = p24_shots()
        refs = scene_storyboard.shared_references(None, 24, shots, cast_of=shots[8]["data"])
        self.assertEqual([r["path"] for r in refs if r["label"] == "KELLY"], ["10.png", "16.png"])

    def test_the_frames_own_place_and_props_come_before_other_shots(self):
        shots = p24_shots()
        refs = scene_storyboard.shared_references(None, 24, shots, cast_of=shots[8]["data"], limit=6)
        self.assertEqual([r["path"] for r in refs][4:], ["263/1.png", "420/2.png"])   # shot 9's own place picture + the well

    def test_cast_missing_names_a_person_with_library_pictures_left_out(self):
        own = p24_shots()[8]["data"]
        sent = [{"path": "10.png", "label": "KELLY", "role": "character"}, {"path": "420/2.png", "label": "GIẾNG ĐÁ CỔ", "role": "object"}]
        self.assertEqual(scene_storyboard.cast_missing(None, 24, own, sent), ["YÊU NỮ TÀ LINH DẠNG 2"])
        self.assertEqual(scene_storyboard.cast_missing(None, 24, own, fake_refs(None, 24, own)), [])


if __name__ == "__main__":
    unittest.main()
