"""Tổ rà soát tác động (người dùng 10/10): trigger bắt MỌI thay đổi → lọc trường có nghĩa → luật code + agent Claude (giả) → mục lệch;
mục đỏ giữ gen tốn tiền của shot; Việc cần bạn; đóng mục."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import change_review as CR, inbox, llm_runner
from core.db import connect
from core.pipeline import Pipeline


class FakeClient:
    name = "fake"

    def __init__(self, answer):
        self.answer, self.calls, self.tags = answer, [], []

    def complete(self, prompt, images=()):
        self.calls.append(prompt)
        self.tags.append(llm_runner.current_tag())
        return llm_runner.LlmReply(json.dumps(self.answer, ensure_ascii=False), 1000, 200)


class ChangeReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        env = mock.patch.dict(os.environ, {"FEATURE_SETTINGS_FILE": os.path.join(self.tmp, "none.json"), "FEATURE_CHANGE_REVIEW": "1"})
        env.start()
        self.addCleanup(env.stop)
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        self.ids = []
        for k in range(1, 4):
            sid = self._new_scene(self.pid, f"s{k}")
            self.ids.append(sid)
            self._set(sid, {"size": "MS", "image_prompt": "Medium shot, Kelly at the well", "characters": ["KELLY"]})
        self.p.conn.execute("UPDATE change_events SET state='skipped'")      # các lần dựng mẫu ở trên
        self.p.conn.commit()

    def _new_scene(self, pid, title):
        idx = self.p.add_scene_next(pid, title)          # trả về SỐ THỨ TỰ shot, không phải id
        return self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (pid, idx)).fetchone()[0]

    def _set(self, sid, data):
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), sid))
        self.p.conn.commit()

    def pending(self):
        return self.p.conn.execute("SELECT * FROM change_events WHERE state='pending'").fetchall()

    def test_trigger_catches_every_write_path(self):
        self._set(self.ids[1], {"size": "WS", "image_prompt": "Medium shot, Kelly at the well", "characters": ["KELLY"]})
        ev = self.pending()
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["kind"], "scene")
        self.assertEqual(json.loads(ev[0]["before"])["size"], "MS")

    def test_bookkeeping_change_is_skipped_free(self):
        self._set(self.ids[1], {"size": "MS", "image_prompt": "Medium shot, Kelly at the well", "characters": ["KELLY"], "qc_note": "x"})
        client = FakeClient({"muc": []})
        res = CR.process_pending(self.p.conn, self.tmp, client=client)
        self.assertEqual(res["skipped"], 1)
        self.assertEqual(client.calls, [])                     # không tốn tiền Claude cho trường sổ sách

    def test_claude_reviews_each_change_and_code_decides_level(self):
        self._set(self.ids[1], {"size": "WS", "image_prompt": "Medium shot, Kelly at the well", "characters": ["KELLY"]})
        ans = {"muc": [{"khau": "anh", "shot": 2, "quan_sat": "lech", "muc_do": "do", "ly_do": "cỡ WS mà prompt 'Medium shot'",
                        "de_xuat": "đổi 'Medium shot' → 'Wide shot'"},
                       {"khau": "lien_tuc", "shot": 3, "quan_sat": "khop", "muc_do": "vang", "ly_do": "ok"},
                       {"khau": "thoai", "shot": 2, "quan_sat": "lech", "muc_do": "do", "ly_do": "x"}]}
        client = FakeClient(ans)
        res = CR.process_pending(self.p.conn, self.tmp, client=client)
        self.assertEqual(res["reviewed"], 1)
        self.assertEqual(len(client.calls), 1)                 # MỖI thay đổi một lời gọi
        self.assertEqual(client.tags[0][0], CR.STAGE)          # qua sổ chi (tagged)
        self.assertIn("`size`", client.calls[0])
        f = CR.open_findings(self.p.conn, self.pid)
        lv = {(r["khau"], r["level"]) for r in f}
        self.assertIn(("anh", "do"), lv)                       # lệch + khâu tốn tiền → đỏ
        self.assertIn(("thoai", "vang"), lv)                   # khâu thoại → code hạ vàng
        self.assertNotIn("lien_tuc", {r["khau"] for r in f})   # 'khop' không thành mục
        self.assertIn("Tổ rà soát", CR.blocking(self.p.conn, self.ids[1]))
        self.assertIsNone(CR.blocking(self.p.conn, self.ids[0]))
        items = [i for i in inbox.items(self.p.conn, "x") if i["kind"] == "Rà soát"]
        self.assertTrue(any("Giữ gen" in i["text"] for i in items))
        red = next(r for r in f if r["level"] == "do")
        CR.close(self.p.conn, red["id"], "dismissed", "u@x")
        self.assertIsNone(CR.blocking(self.p.conn, self.ids[1]))

    def test_flag_off_never_blocks(self):
        with mock.patch.dict(os.environ, {"FEATURE_CHANGE_REVIEW": "0"}):
            self.p.conn.execute("INSERT INTO change_findings(project_id, scene_id, source, level, khau, msg, at) VALUES (?,?,?,?,?,?,?)",
                                (self.pid, self.ids[0], "code", "do", "anh", "x", "t"))
            self.assertIsNone(CR.blocking(self.p.conn, self.ids[0]))

    def test_asset_profile_change_reaches_every_shot_with_that_character(self):
        self.p.conn.execute("INSERT INTO assets(id, game, kind, name, profile) VALUES (500, 'FF', 'character', 'KELLY', '{}')")
        self.p.conn.execute("UPDATE assets SET profile=? WHERE id=500", (json.dumps({"must_keep": "áo đỏ"}),))
        self.p.conn.commit()
        ev = [e for e in self.pending() if e["kind"] == "asset"]
        self.assertEqual(len(ev), 1)
        self.assertEqual(sorted(CR.affected_scenes(self.p.conn, ev[0])), sorted(self.ids))

    def test_one_bad_change_does_not_stop_others(self):
        self._set(self.ids[0], {"size": "WS", "characters": ["KELLY"]})
        self._set(self.ids[2], {"size": "WS", "characters": ["KELLY"]})
        bad = FakeClient({"muc": "khong phai list"})
        res = CR.process_pending(self.p.conn, self.tmp, client=bad)
        self.assertEqual(res["failed"], 2)
        self.assertTrue(self.p.conn.execute("SELECT 1 FROM diag_events WHERE code='change_review_fail'").fetchone())

    # ---- gộp theo shot (người dùng 10/10): mọi thay đổi đang chờ của CÙNG shot trong một lượt = một lần rà ----
    def test_same_shot_changes_merge_into_one_review(self):
        base = {"size": "MS", "image_prompt": "Medium shot, Kelly at the well", "characters": ["KELLY"]}
        self._set(self.ids[1], dict(base, size="WS"))
        self._set(self.ids[1], dict(base, size="WS", angle="low"))
        self._set(self.ids[1], dict(base, size="WS", angle="low", image_prompt="Wide shot, Kelly at the well"))
        self._set(self.ids[2], dict(base, size="CU"))
        client = FakeClient({"muc": []})
        res = CR.process_pending(self.p.conn, self.tmp, client=client)
        self.assertEqual(len(client.calls), 2)                    # shot 2 (3 lần ghi) một lời gọi + shot 3 một lời gọi
        call = next(c for c in client.calls if "`angle`" in c)
        self.assertIn("TRƯỚC = MS", call)                         # trước = bản của lần ghi cũ nhất
        self.assertIn("Wide shot, Kelly", call)                   # sau = bản của lần ghi mới nhất
        rows = self.p.conn.execute("SELECT state, cost_usd FROM change_events WHERE scene_id=? AND state<>'skipped' ORDER BY id",
                                   (self.ids[1],)).fetchall()
        self.assertEqual([r[0] for r in rows], ["reviewed"] * 3)  # cả nhóm đánh dấu đã rà
        self.assertEqual([r[1] > 0 for r in rows], [False, False, True])   # tiền ghi vào lần cuối
        self.assertEqual(res["reviewed"], 4)
        self.assertEqual(self.pending(), [])

    def test_change_then_revert_on_same_shot_costs_nothing(self):
        base = {"size": "MS", "image_prompt": "Medium shot, Kelly at the well", "characters": ["KELLY"]}
        self._set(self.ids[1], dict(base, size="WS"))
        self._set(self.ids[1], base)
        client = FakeClient({"muc": []})
        res = CR.process_pending(self.p.conn, self.tmp, client=client)
        self.assertEqual(client.calls, [])
        self.assertEqual(res["skipped"], 2)

    def test_limit_counts_shots_not_writes(self):
        base = {"size": "MS", "image_prompt": "Medium shot, Kelly at the well", "characters": ["KELLY"]}
        for k in range(6):
            self._set(self.ids[1], dict(base, size="WS", lens_mm=20 + k))
        self._set(self.ids[2], dict(base, size="CU"))
        CR.process_pending(self.p.conn, self.tmp, client=FakeClient({"muc": []}), limit=2)
        self.assertEqual(self.pending(), [])

    def test_code_only_then_new_write_merges_from_original(self):
        base = {"size": "MS", "image_prompt": "Medium shot, Kelly at the well", "characters": ["KELLY"]}
        self._set(self.ids[1], dict(base, size="WS"))
        CR.process_pending(self.p.conn, self.tmp, client=None)              # lượt không có Claude → code_only
        self._set(self.ids[1], dict(base, size="WS", angle="high"))
        client = FakeClient({"muc": []})
        CR.process_pending(self.p.conn, self.tmp, client=client)
        self.assertEqual(len(client.calls), 1)
        self.assertIn("TRƯỚC = MS", client.calls[0])
        states = {r[0] for r in self.p.conn.execute("SELECT state FROM change_events WHERE scene_id=? AND id > 0 AND state<>'skipped'",
                                                     (self.ids[1],))}
        self.assertEqual(states, {"reviewed"})

    def test_write_during_review_stays_pending(self):
        base = {"size": "MS", "image_prompt": "Medium shot, Kelly at the well", "characters": ["KELLY"]}
        self._set(self.ids[1], dict(base, size="WS"))
        outer = self

        class Writing(FakeClient):
            def complete(self, prompt, images=()):
                outer._set(outer.ids[1], dict(base, size="CU"))          # Dashboard ghi trong lúc Claude đang rà
                return super().complete(prompt, images)
        CR.process_pending(self.p.conn, self.tmp, client=Writing({"muc": []}))
        ev = self.pending()
        self.assertEqual(len(ev), 1)
        self.assertEqual(json.loads(ev[0]["after"])["size"], "CU")

    # ---- sửa theo agent rà 10/10 ----
    def test_pending_change_holds_until_reviewed(self):
        self._set(self.ids[1], {"size": "WS", "image_prompt": "Wide shot", "characters": ["KELLY"]})
        self.assertIn("đang rà", CR.blocking(self.p.conn, self.ids[1]))       # lỗi 6: sửa xong bấm Gen ngay → chờ rà
        CR.process_pending(self.p.conn, self.tmp, client=None)
        self.assertIsNone(CR.blocking(self.p.conn, self.ids[1]))
        self.assertEqual(self.p.conn.execute("SELECT state FROM change_events ORDER BY id DESC LIMIT 1").fetchone()[0], "code_only")
        client = FakeClient({"muc": []})                                      # lỗi 13: có Claude lại → rà nốt
        CR.process_pending(self.p.conn, self.tmp, client=client)
        self.assertEqual(len(client.calls), 1)

    def test_code_redraw_findings_never_block_the_redraw(self):
        self.assertEqual(CR._code_level({"khau": "anh", "muc": "do", "msg": "ảnh mới nhất vẽ trên nền cũ"}), "vang")
        self.assertEqual(CR._code_level({"khau": "nen", "muc": "do", "msg": "render nền 3D chưa theo máy hiện tại"}), "vang")
        self.assertEqual(CR._code_level({"khau": "nen", "muc": "do", "msg": "cờ stage_camera TẮT → nền dựng bằng máy cũ"}), "do")
        self.assertEqual(CR._code_level({"khau": "neo", "muc": "do", "msg": "x"}), "do")

    def test_asset_change_maps_shots_per_project(self):
        pid2 = self.p.create_project("u")
        sid2 = self._new_scene(pid2, "a")
        self._set(sid2, {"characters": ["KELLY"]})
        self.p.conn.execute("INSERT INTO assets(id, game, kind, name, profile) VALUES (501, 'FF', 'character', 'KELLY', '{}')")
        self.p.conn.execute("UPDATE change_events SET state='skipped'")
        self.p.conn.execute("UPDATE assets SET profile=? WHERE id=501", (json.dumps({"must_keep": "áo đỏ"}),))
        self.p.conn.commit()
        ans = {"muc": [{"khau": "anh", "shot": 1, "quan_sat": "lech", "muc_do": "do", "ly_do": "prompt còn tả áo cũ"}]}
        client = FakeClient(ans)
        CR.process_pending(self.p.conn, self.tmp, client=client)
        self.assertEqual(len(client.calls), 2)                                # lỗi 3: mỗi dự án một lời gọi
        rows = self.p.conn.execute("SELECT project_id, scene_id FROM change_findings WHERE source='claude'").fetchall()
        self.assertEqual({(r[0], r[1]) for r in rows}, {(self.pid, self.ids[0]), (pid2, sid2)})   # lỗi 2: có project, đúng shot
        self.assertTrue(CR.open_findings(self.p.conn, pid2))

    def test_kho_image_events_only_for_approved_pictures(self):
        self.p.conn.execute("INSERT INTO assets(id, game, kind, name) VALUES (502, 'FF', 'character', 'K2')")
        self.p.conn.execute("INSERT INTO asset_images(id, asset_id, path, status) VALUES (900, 502, 'a.png', 'pending')")
        self.p.conn.execute("UPDATE asset_images SET status='claude_ok' WHERE id=900")
        self.assertEqual(len([e for e in self.pending() if e["kind"] == "asset_image"]), 0)   # lỗi 4: duyệt trung gian không gọi
        self.p.conn.execute("UPDATE asset_images SET status='approved' WHERE id=900")
        self.assertEqual(len([e for e in self.pending() if e["kind"] == "asset_image"]), 1)


if __name__ == "__main__":
    unittest.main()
