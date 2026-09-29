"""S3.8 (kế hoạch sau #8): a place changed after the Director's plan is said at Step 1; a new project starts from the way of working
settled in the person's latest project."""
import json
import unittest

from core import project_defaults
from core.db import connect
from core.pipeline import Pipeline


class ProjectDefaultsTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.conn = self.p.conn

    def _place(self, pid, name, description):
        cur = self.conn.execute("INSERT INTO assets (game, kind, name, description) VALUES ('FF', 'location', ?, ?)", (name, description))
        self.conn.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?, ?)", (pid, cur.lastrowid))
        self.conn.commit()
        return cur.lastrowid

    def test_a_place_changed_after_the_plan_names_its_scenes(self):
        pid = self.p.create_project("a")
        aid = self._place(pid, "Tháp Đồng Hồ", "quảng trường nhiều tầng")
        sid = self.p.create_scene(pid, 1, "S1")
        self.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"story_scene": 1, "location": "Tháp Đồng Hồ, quảng trường"}), sid))
        self.conn.execute("UPDATE projects SET director_raw=? WHERE id=?",
                          (json.dumps({"scenes": [], "places_at_plan": project_defaults.places_fingerprint(self.conn, pid)}), pid))
        self.conn.commit()
        self.assertEqual(project_defaults.changed_places(self.conn, pid), [])
        self.conn.execute("UPDATE assets SET description='quảng trường phẳng, tường thấp' WHERE id=?", (aid,))
        self.conn.commit()
        changed = project_defaults.changed_places(self.conn, pid)
        self.assertEqual([(c["name"], c["what"], c["scenes"]) for c in changed], [("Tháp Đồng Hồ", "đổi mô tả / ảnh", [1])])

    def test_an_old_plan_without_a_fingerprint_says_nothing(self):
        pid = self.p.create_project("b")
        self.conn.execute("UPDATE projects SET director_raw=? WHERE id=?", (json.dumps({"scenes": []}), pid))
        self.assertEqual(project_defaults.changed_places(self.conn, pid), [])

    def test_a_new_project_inherits_the_latest_projects_way_of_working(self):
        old = self.p.create_project("old", created_by="a@x.vn")
        self.p.set_project_field(old, "shot_mode", "per_shot")
        self.p.set_project_field(old, "style_profile", "DRAMA_DOC,MV_NARRATIVE")
        other = self.p.create_project("someone else", created_by="b@x.vn")
        self.p.set_project_field(other, "shot_mode", "multishot")
        new = self.p.create_project("new", created_by="a@x.vn")
        copied = project_defaults.inherit(self.conn, new, "a@x.vn")
        self.assertIn("shot_mode", copied)
        row = self.p.project(new)
        self.assertEqual((row["shot_mode"], row["style_profile"]), ("per_shot", "DRAMA_DOC,MV_NARRATIVE"))
        self.assertEqual(project_defaults.inherit(self.conn, self.p.create_project("first", created_by="c@x.vn"), "c@x.vn"), [])


if __name__ == "__main__":
    unittest.main()
