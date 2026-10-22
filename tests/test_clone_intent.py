"""C-CLONE-INTENT (TODO 🐞 13/10, tập 2 = dự án mới sạch, ý 5): bản sao "chạy lại Đạo diễn" (compare.clone_project with_rows=False)
không mang ý đồ Tầng A (director_intent_raw) và mốc dựng riêng của phim cũ (render_settings: mốc nhạc, popup cuối, chữ card cuối) —
render_settings theo đúng luật dự án mới (core/project_defaults._carried: giữ cách dựng). with_rows=True giữ nguyên như cũ.
CSDL tạm (tests.test_v3.kenta_project), không đụng data/ thật."""
import json
import unittest

from core import compare, delivery
from tests.test_v3 import kenta_project

OLD_RENDER = {"transition": "cut", "fade": 0.4, "music_volume": 0.6, "music_start": 12.5, "music2_start": 40.0,
              "end_popup": {"enabled": True, "text": "XEM TẬP 2"},
              "end_card": {"enabled": True, "seconds": 3, "color": "#fff", "title": "Tập 1", "subtitle": "Kelly"}}
OLD_INTENT = {"scenes": [{"idx": 1, "y_do": "ý đồ của phim cũ"}]}


class CloneIntentTests(unittest.TestCase):
    def setUp(self):
        self.p, self.pid = kenta_project()
        self.p.conn.execute("UPDATE projects SET director_raw=?, director_intent_raw=?, render_settings=? WHERE id=?",
                            (json.dumps({"scenes": []}), json.dumps(OLD_INTENT, ensure_ascii=False),
                             json.dumps(OLD_RENDER, ensure_ascii=False), self.pid))
        self.p.conn.commit()

    def test_rerun_director_clone_drops_old_intent_and_film_marks(self):
        new = compare.clone_project(self.p, self.pid, "chạy lại Đạo diễn", None, with_rows=False)
        proj = self.p.project(new)
        self.assertIsNone(proj["director_raw"])
        self.assertIsNone(proj["director_intent_raw"])
        rs = json.loads(proj["render_settings"] or "{}")
        for mark in ("music_start", "music2_start", "end_popup"):
            self.assertNotIn(mark, rs)
        self.assertNotIn("title", rs.get("end_card") or {})
        self.assertNotIn("subtitle", rs.get("end_card") or {})
        # cách dựng giữ như một dự án mới (project_defaults.RENDER_WAY / END_CARD_STYLE)
        self.assertEqual((rs["transition"], rs["fade"], rs["music_volume"]), ("cut", 0.4, 0.6))
        self.assertEqual(rs["end_card"], {"enabled": True, "seconds": 3, "color": "#fff"})
        delivery.get_settings(self.p, new)                                # code đọc render_settings vẫn chạy (dict hợp lệ)

    def test_keep_rows_clone_keeps_everything(self):
        new = compare.clone_project(self.p, self.pid, "bản so sánh", None, with_rows=True)
        proj = self.p.project(new)
        self.assertEqual(json.loads(proj["director_intent_raw"]), OLD_INTENT)
        self.assertEqual(json.loads(proj["render_settings"]), OLD_RENDER)
        self.assertIsNotNone(proj["director_raw"])

    def test_rerun_clone_without_render_settings_stays_empty(self):
        self.p.conn.execute("UPDATE projects SET render_settings=NULL WHERE id=?", (self.pid,))
        self.p.conn.commit()
        new = compare.clone_project(self.p, self.pid, "trống", None, with_rows=False)
        self.assertIsNone(self.p.project(new)["render_settings"])
        delivery.get_settings(self.p, new)

    def test_pilot_trial_keeps_same_plan_intent(self):
        """Gộp cloud-E 22/10: tools/pilot_setup cắt CÙNG kế hoạch Đạo diễn (director_raw nguồn) → giữ ý đồ + render_settings của phim
        (card cuối tắt), dù clone_project(with_rows=False) đã bỏ chúng cho ca chạy lại Đạo diễn thật."""
        from tools import pilot_setup
        new = compare.clone_project(self.p, self.pid, "thử", None, with_rows=False)
        pilot_setup.carry_same_plan(self.p, self.p.project(self.pid), new)
        proj = self.p.project(new)
        self.assertEqual(json.loads(proj["director_intent_raw"]), OLD_INTENT)
        rs = json.loads(proj["render_settings"])
        self.assertEqual(rs["music_start"], 12.5)
        self.assertFalse(rs["end_card"]["enabled"])
        self.assertEqual(json.loads(self.p.project(self.pid)["render_settings"]), OLD_RENDER)   # dự án gốc không đổi


if __name__ == "__main__":
    unittest.main()
