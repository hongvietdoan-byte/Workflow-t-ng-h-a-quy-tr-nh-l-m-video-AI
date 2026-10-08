"""08/10 dự án #24 (việc 15/16): Director + Quay phim không ghi `plate_view` → 9 nền 3D cùng nhìn về tháp; shot ngược vẫn có tháp; hai góc
ngang hai bên trục; "Kelly ngã ra sau" mà không ghi mặt hướng về đâu. Fixture: câu trả lời Director THẬT (director_raw #24) và bản người
dùng đã sửa tay theo sơ đồ trục (scenes #24 sau 08/10)."""
import json
import os
import unittest

from core import director_report, plate_choice, plate_view_check as V

HERE = os.path.join(os.path.dirname(__file__), "fixtures")


def shots(name):
    obj = json.load(open(os.path.join(HERE, name), encoding="utf-8"))
    return obj, [(sc["idx"], k, s) for sc in obj["scenes"] for k, s in enumerate(sc["shots"], 1)]


class PlateViewCheckTests(unittest.TestCase):
    def test_the_real_director_answer_is_flagged(self):
        _, rows = shots("director_p24_shots.json")
        found = " | ".join(V.warnings(rows))
        self.assertIn("thiếu `plate_view`", found)
        self.assertIn("hậu cảnh lặp", found)
        self.assertIn("động tác phản xạ", found)              # shot 4 "Kelly ngã ra sau" without where she faces

    def test_the_hand_fixed_plan_raises_no_axis_or_repeat_warning(self):
        _, rows = shots("director_p24_shots_fixed.json")
        found = " | ".join(V.warnings(rows))
        self.assertNotIn("hậu cảnh lặp", found)
        self.assertNotIn("hai bên trục", found)
        self.assertNotIn("góc ngược", found)
        self.assertNotIn("động tác phản xạ", found)

    def test_both_sides_without_a_reason_and_reverse_on_landmark(self):
        rows = [(1, 1, {"plate_spot": "p", "plate_view": {"background": "left", "why": "ngang"}}),
                (1, 2, {"plate_spot": "p", "plate_view": {"background": "right", "why": "ngang"}}),
                (1, 3, {"plate_spot": "p", "angle": "eye", "blocking": "Reverse angle, Kelly facing camera",
                        "plate_view": {"background": "landmark", "why": "x"}})]
        found = " | ".join(V.warnings(rows))
        self.assertIn("CẢ hai bên trục", found)
        self.assertIn("góc ngược", found)
        rows[1][2]["plate_view"]["why"] = "cố ý vượt trục khi yêu nữ xuất hiện"
        self.assertNotIn("CẢ hai bên trục", " | ".join(V.warnings(rows)))

    def test_director_report_carries_the_warnings(self):
        obj, _ = shots("director_p24_shots.json")
        script = open(os.path.join(HERE, "p24_script.txt"), encoding="utf-8").read()
        r = director_report.report(obj, script)
        self.assertTrue(any("plate_view" in w for w in r["continuity"]))


class LandmarkPictureTests(unittest.TestCase):
    def test_away_and_side_views_drop_the_landmark_picture(self):
        self.assertTrue(plate_choice.landmark_off_frame({"plate_view": {"background": "away"}}))
        self.assertTrue(plate_choice.landmark_off_frame({"plate_view": {"background": "left"}}))
        self.assertFalse(plate_choice.landmark_off_frame({"plate_view": {"background": "landmark"}}))
        self.assertFalse(plate_choice.landmark_off_frame({}))

    def test_scene_references_skip_the_place_picture_for_an_away_shot(self):
        from core import assets
        from core.db import connect
        from core.pipeline import Pipeline
        import tempfile
        p = Pipeline(connect())
        pid = p.create_project("p24", game="FF")
        tower = assets.create(p.conn, "FF", "location", "Tháp Đồng Hồ")
        pic = os.path.join(tempfile.mkdtemp(), "tower.png")
        open(pic, "wb").write(b"x")
        p.conn.execute("INSERT INTO asset_images (asset_id, path, role, status) VALUES (?, ?, 'detail', 'approved')", (tower, pic))
        p.conn.commit()
        assets.attach(p.conn, pid, tower)
        base = {"location": "Tháp Đồng Hồ", "location_asset": tower, "size": "MCU", "text": "Kelly ngã"}
        with_mark = assets.scene_references(p.conn, pid, dict(base, plate_view={"background": "landmark"}))
        away = assets.scene_references(p.conn, pid, dict(base, plate_view={"background": "away"}))
        self.assertTrue(any(r["label"] == "Tháp Đồng Hồ" for r in with_mark), with_mark)
        self.assertFalse(any(r["label"] == "Tháp Đồng Hồ" for r in away), away)


if __name__ == "__main__":
    unittest.main()
