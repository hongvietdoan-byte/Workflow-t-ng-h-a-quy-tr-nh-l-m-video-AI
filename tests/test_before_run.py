"""Khung "🧭 Trước khi chạy" ở Bước 1 (người dùng 10/10): core.before_run.collect — chỉ đọc, 0 USD, không ném lỗi."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import before_run as BR
from core.db import connect
from core.pipeline import Pipeline


def _texts(res, group=None):
    return [it["text"] for g in res["groups"] if group in (None, g["key"]) for it in g["items"]]


def _items(res, group):
    return [it for g in res["groups"] if g["key"] == group for it in g["items"]]


class BeforeRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        env = mock.patch.dict(os.environ, {"FEATURE_SETTINGS_FILE": os.path.join(self.tmp, "none.json"),
                                           "FEATURE_CHANGE_REVIEW": "1", "FEATURE_DIRECTOR_REWRITE": "1",
                                           "FEATURE_TWO_TIER_QUALITY": "0", "FEATURE_STAGE_CAMERA": "0"})
        env.start()
        self.addCleanup(env.stop)
        self.p = Pipeline(connect())
        self.c = self.p.conn
        self.pid = self.p.create_project("t")
        self.kelly = self._asset("character", "Kelly", {"identity": "x"})                  # thiếu must_keep
        self.maxim = self._asset("character", "Maxim", {"must_keep": "áo xanh"})
        self.well = self._asset("prop", "Giếng cổ", {})                                      # thiếu kích thước
        self.place = self._asset("location", "Tháp đồng hồ", {})                             # chưa có model3d, hồ sơ rỗng
        idx = self.p.add_scene_next(self.pid, "s1")
        self.sid = self.c.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (self.pid, idx)).fetchone()[0]
        self.c.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({
            "characters": ["KELLY", "Maxim"], "location_asset": self.place, "image_prompt": "Kelly đứng cạnh Giếng cổ"}), self.sid))
        self.c.commit()

    def _asset(self, kind, name, profile):
        cur = self.c.execute("INSERT INTO assets(game, kind, name, aliases, profile) VALUES ('FF', ?, ?, '', ?)",
                             (kind, name, json.dumps(profile, ensure_ascii=False)))
        self.c.execute("INSERT INTO project_assets(project_id, asset_id) VALUES (?, ?)", (self.pid, cur.lastrowid))
        self.c.commit()
        return cur.lastrowid

    def collect(self):
        return BR.collect(self.c, self.tmp, self.pid)

    def test_paid_flags_on_are_listed(self):
        res = self.collect()
        cost = " ".join(_texts(res, "cost"))
        self.assertIn("change_review", cost)
        self.assertIn("director_rewrite", cost)
        self.assertNotIn("two_tier_quality", cost)                                     # cờ tắt: không hiện
        self.assertIn("không trần", cost)

    def test_missing_must_keep_size_and_3d_are_listed(self):
        inputs = _items(self.collect(), "inputs")
        text = " ".join(i["text"] for i in inputs)
        self.assertIn("Kelly", text)                 # nhân vật ghi 'KELLY' trong shot vẫn khớp Kho 'Kelly'
        self.assertNotIn("Maxim", text)              # có must_keep
        self.assertIn("Giếng cổ", text)              # vật thiếu kích thước
        self.assertIn("Tháp đồng hồ", text)          # bối cảnh chưa có 3D
        self.assertTrue(all(i["fix"] for i in inputs))
        place = [i["text"] for i in inputs if "Tháp đồng hồ" in i["text"]]
        self.assertFalse([t for t in place if "must_keep" in t])     # bối cảnh hồ sơ rỗng: không kiểm must_keep (như change_audit)

    def test_character_not_in_kho_is_listed(self):
        self.c.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"characters": ["Ghost"]}), self.sid))
        self.c.commit()
        text = " ".join(_texts(self.collect(), "inputs"))
        self.assertIn("'Ghost' không có trong Kho của dự án", text)

    def test_red_finding_without_shot_is_not_held(self):
        self.c.execute("INSERT INTO change_findings(event_id, project_id, scene_id, source, level, khau, msg, at) "
                       "VALUES (1, ?, NULL, 'claude', 'do', 'anh', 'x', '2026-10-10')", (self.pid,))
        self.c.commit()
        res = self.collect()
        self.assertEqual(res["counts"]["do"], 0)
        hold = " ".join(_texts(res, "hold"))
        self.assertNotIn("bị giữ", hold)
        self.assertIn("không gắn shot nào", hold)

    def test_pending_asset_event_is_not_a_wait(self):
        self.c.execute("UPDATE change_events SET state='skipped'")
        self.c.execute("INSERT INTO change_events(at, kind, project_id, asset_id, state) VALUES ('2026-10-10', 'asset', ?, ?, 'pending')",
                       (self.pid, self.kelly))
        self.c.commit()
        self.assertNotIn("chờ Tổ rà soát", " ".join(_texts(self.collect(), "hold")))
        self.c.execute("INSERT INTO change_events(at, kind, project_id, scene_id, state) VALUES ('2026-10-10', 'scene', ?, ?, 'pending')",
                       (self.pid, self.sid))
        self.c.commit()
        self.assertIn("chờ Tổ rà soát", " ".join(_texts(self.collect(), "hold")))

    def test_storyboard_anchor_without_running_job(self):
        from core import scene_storyboard
        ids = [self.sid]
        idx = self.p.add_scene_next(self.pid, "s2")
        ids.append(self.c.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (self.pid, idx)).fetchone()[0])
        for n, (sid, size) in enumerate(zip(ids, ("WS", "MS")), 1):
            self.c.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"story_scene": 1, "shot_no": n, "size": size}), sid))
        self.c.commit()
        with mock.patch.object(scene_storyboard, "enabled", return_value=True):
            red = [i["text"] for i in _items(self.collect(), "hold") if i["level"] == "do"]
        self.assertTrue(any("chưa có job gen đang chạy" in t for t in red))
        self.assertEqual(BR.LIVE_JOB, ("queued", "running", "retryable"))

    def test_stage_camera_text_has_no_stale_note(self):
        self.assertNotIn("chưa render nền thật", BR.PAID_FLAGS["stage_camera"]["text"])

    def test_collect_is_memoised_within_a_rerun(self):
        from core import memo
        calls = []
        real = BR._collect
        with mock.patch.object(BR, "_collect", side_effect=lambda *a: calls.append(1) or real(*a)), \
                mock.patch.object(memo._local, "memo", {}, create=True):
            self.collect()
            self.collect()
        self.assertEqual(len(calls), 1)

    def test_missing_change_findings_table_does_not_break(self):
        self.c.execute("DROP TABLE change_findings")
        res = self.collect()
        hold = " ".join(_texts(res, "hold"))
        self.assertIn("chưa có", hold)
        self.assertEqual({g["key"] for g in res["groups"]}, {"cost", "hold", "ops", "inputs"})

    def test_open_red_finding_is_shown(self):
        self.c.execute("INSERT INTO change_findings(event_id, project_id, scene_id, source, level, khau, msg, at) "
                       "VALUES (1, ?, ?, 'code', 'do', 'nen', 'nền cũ', '2026-10-10')", (self.pid, self.sid))
        self.c.commit()
        res = self.collect()
        red = [i for i in _items(res, "hold") if i["level"] == "do"]
        self.assertTrue(red)
        self.assertIn("1", red[0]["text"])
        self.assertGreaterEqual(res["counts"]["do"], 1)

    def test_operating_conditions_always_present(self):
        ops = " ".join(_texts(self.collect(), "ops"))
        self.assertIn("đăng nhập", ops)
        self.assertIn("khởi động lại", ops)
        self.assertIn("không chặn", ops)


if __name__ == "__main__":
    unittest.main()
