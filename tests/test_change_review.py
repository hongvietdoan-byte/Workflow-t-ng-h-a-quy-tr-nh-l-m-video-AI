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

    def test_review_reads_the_motion_prompt_sent_not_old_motion_en(self):
        """Lỗi 5 (#27 shot 16): người sửa tay motion prompt (motion_prompts) — motion_en (bản dịch trường Đạo diễn) còn tả bản cũ →
        agent so bản cũ, giữ oan. Nguồn sự thật cho khâu motion = motion prompt GỬI ĐI; motion_en chỉ hiện khi chưa có motion prompt."""
        sid = self.ids[1]
        self._set(sid, {"size": "MS", "characters": ["KELLY"], "action": "Kelly ném bom keo",
                        "motion_en": {"action": "Kelly throws, green glue crystals grow"}})
        self.p.conn.execute("INSERT INTO motion_prompts(scene_id, motion_prompt, state) VALUES (?,?, 'approved')",
                            (sid, "Kelly throws; a metal elevator-door wall rises from the ground in two beats"))
        self.p.conn.execute("UPDATE change_events SET state='skipped'")
        self._set(sid, {"size": "MS", "characters": ["KELLY"], "action": "Kelly ném bom keo, tường thang máy mọc",
                        "motion_en": {"action": "Kelly throws, green glue crystals grow"}})
        ev = self.pending()[0]
        text = CR.build_prompt(self.p.conn, ev, ["action"], [sid], [])
        self.assertIn("elevator-door wall rises", text)            # bản gửi đi
        self.assertNotIn("green glue crystals", text.split("## Các shot liên quan")[1])
        # chưa có motion prompt (shot kề) → motion_en vẫn là nguồn của bản code sắp viết
        self._set(self.ids[2], {"size": "MS", "characters": ["KELLY"], "motion_en": {"action": "Kelly waits"}})
        text = CR.build_prompt(self.p.conn, ev, ["action"], [sid, self.ids[2]], [])
        self.assertIn("Kelly waits", text)

    # ---- C4 (rà chuỗi 13/10): sửa motion prompt là một thay đổi của shot (cờ change_review_motion) ----------------------------------
    def _motion(self, sid, text):
        from core.llm_io import store_motion_prompts
        idx = self.p.conn.execute("SELECT idx FROM scenes WHERE id=?", (sid,)).fetchone()[0]
        if not self.p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'", (sid,)).fetchone():
            jid = self.p.create_job(sid, "image_gen")
            self.p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (jid,))
        store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": idx, "motion_prompt": text}]})

    def _old_red(self, sid):
        CR._add(self.p.conn, None, self.pid, sid, "claude", "do", "motion", "motion tả trạng thái cuối cũ")
        self.p.conn.commit()

    def test_editing_motion_prompt_requeues_review_and_lifts_old_red(self):
        os.environ["FEATURE_CHANGE_REVIEW_MOTION"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_CHANGE_REVIEW_MOTION", None)
        sid = self.ids[1]
        self._motion(sid, "Kelly kneels by the well")
        self.p.conn.execute("UPDATE change_events SET state='skipped'")
        self._old_red(sid)
        self.assertIn("motion tả trạng thái cuối cũ", CR.blocking(self.p.conn, sid))
        self._motion(sid, "Kelly stands up and walks to the well")                # người sửa prompt ở Bước 3
        ev = [e for e in self.pending() if e["kind"] == "motion"]                  # (+ dòng sổ sách scenes.data của công thức)
        self.assertEqual([e["scene_id"] for e in ev], [sid])
        self.assertEqual(ev[0]["project_id"], self.pid)
        self.assertIn("đang rà", CR.blocking(self.p.conn, sid))                   # chờ rà bản mới, không giữ vì mục cũ
        client = FakeClient({"muc": [{"khau": "motion", "shot": 2, "quan_sat": "khop", "ly_do": "khớp end_state"}]})
        CR.process_pending(self.p.conn, self.tmp, client=client)
        self.assertEqual(len(client.calls), 1)
        self.assertIn("`motion_prompt`", client.calls[0])
        self.assertIn("SAU = Kelly stands up", client.calls[0])
        self.assertIsNone(CR.blocking(self.p.conn, sid))                           # Claude thấy khớp → mục đỏ cũ tự đóng

    def test_motion_edit_and_shot_edit_merge_per_source(self):
        os.environ["FEATURE_CHANGE_REVIEW_MOTION"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_CHANGE_REVIEW_MOTION", None)
        sid = self.ids[1]
        self._motion(sid, "push in")
        self.p.conn.execute("UPDATE change_events SET state='skipped'")
        self._set(sid, {"size": "WS", "image_prompt": "Medium shot, Kelly at the well", "characters": ["KELLY"]})
        self._motion(sid, "slow push in")
        client = FakeClient({"muc": []})
        CR.process_pending(self.p.conn, self.tmp, client=client)
        self.assertEqual(len(client.calls), 1)                                     # một shot = một lời gọi
        self.assertIn("`size`: TRƯỚC = MS", client.calls[0])
        self.assertIn("`motion_prompt`: TRƯỚC = push in", client.calls[0])
        change = client.calls[0].split("## Thay đổi #")[1].split("## Các shot liên quan")[0]
        self.assertNotIn("`image_prompt`", change)                                 # không trộn ảnh chụp đầy đủ với khóa lẻ

    def test_motion_edit_flag_off_costs_nothing_and_never_holds(self):
        sid = self.ids[1]
        self._motion(sid, "push in")
        self.p.conn.execute("UPDATE change_events SET state='skipped'")
        self._motion(sid, "slow push in")
        self.p.conn.execute("UPDATE change_events SET state='skipped' WHERE kind='scene'")   # dòng sổ sách scenes.data (như trước)
        self.assertEqual(len([e for e in self.pending() if e["kind"] == "motion"]), 1)
        self.assertIsNone(CR.blocking(self.p.conn, sid))                           # cờ tắt: lần sửa motion không giữ (như trước)
        client = FakeClient({"muc": []})
        CR.process_pending(self.p.conn, self.tmp, client=client)
        self.assertEqual(client.calls, [])
        self.assertEqual(self.pending(), [])

    # ---- vòng sửa sau rà S4 ----------------------------------------------------------------------------------------------------------
    def test_motion_edit_keeps_open_image_finding(self):
        # R9: lần rà một sửa motion chỉ hỏi về motion_prompt → Claude không nhắc lại mục 'anh' cũ KHÔNG có nghĩa là đã sửa
        os.environ["FEATURE_CHANGE_REVIEW_MOTION"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_CHANGE_REVIEW_MOTION", None)
        sid = self.ids[1]
        self._motion(sid, "Kelly kneels by the well")
        self.p.conn.execute("UPDATE change_events SET state='skipped'")
        CR._add(self.p.conn, None, self.pid, sid, "claude", "do", "anh", "ảnh sai trang phục")
        self._old_red(sid)
        self.p.conn.commit()
        self._motion(sid, "Kelly stands up and walks to the well")
        CR.process_pending(self.p.conn, self.tmp, client=FakeClient({"muc": []}))
        st = dict(self.p.conn.execute("SELECT khau, status FROM change_findings WHERE scene_id=? AND source='claude'", (sid,)).fetchall())
        self.assertEqual(st, {"anh": "open", "motion": "resolved"})
        self.assertIn("ảnh sai trang phục", CR.blocking(self.p.conn, sid) or "")

    def test_before_run_does_not_count_motion_when_flag_off(self):
        # R13: cờ change_review_motion tắt → sửa motion prompt không bao giờ được rà → không báo "đang chờ Tổ rà soát"
        from core import before_run as BR
        sid = self.ids[1]
        self._motion(sid, "push in")
        self.p.conn.execute("UPDATE change_events SET state='skipped'")
        self._motion(sid, "slow push in")
        self.p.conn.execute("UPDATE change_events SET state='skipped' WHERE kind='scene'")
        self.p.conn.commit()
        self.assertEqual(len([e for e in self.pending() if e["kind"] == "motion"]), 1)
        self.assertFalse([i for i in BR._review_items(self.p.conn, self.pid) if "đang chờ Tổ rà soát" in i["text"]])
        os.environ["FEATURE_CHANGE_REVIEW_MOTION"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_CHANGE_REVIEW_MOTION", None)
        self.assertTrue([i for i in BR._review_items(self.p.conn, self.pid) if "1 thay đổi đang chờ Tổ rà soát" in i["text"]])

    def _rewrite_setup(self):
        os.environ["FEATURE_CHANGE_REVIEW_MOTION"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_CHANGE_REVIEW_MOTION", None)
        from core import prompt_rewrite as PR
        sid = self.ids[1]
        self._motion(sid, "push in")
        self.p.conn.execute("UPDATE change_events SET state='skipped'")
        self.p.conn.commit()
        jid = self.p.create_job(sid, "video_gen")
        job = self.p.conn.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
        return PR, sid, job

    def test_director_rewrite_is_reviewed_now_and_green_sends_at_once(self):
        # C1 (người dùng 14/10 bật R14, sửa tối ưu): bản motion máy tự viết lại được rà NGAY tại chỗ (một lời gọi, nhãn change_review)
        # — xanh thì không còn thay đổi chờ, lần gen lại không bị giữ tới vòng nền sau
        PR, sid, job = self._rewrite_setup()
        client = FakeClient({"muc": []})
        with mock.patch.object(PR, "client_for", return_value=client):
            PR.save_rewrite(self.p, job, PR.RewriteResult("slow push in, Kelly turns", ["thêm quay người"], "QC", 0, "push in"))
        self.assertEqual(PR.current_prompt(self.p.conn, sid, "video"), "slow push in, Kelly turns")
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.tags[0][0], CR.STAGE)
        self.assertEqual([e for e in self.pending() if e["kind"] == "motion"], [])
        self.assertIsNone(CR.blocking(self.p.conn, sid))
        CR.process_pending(self.p.conn, self.tmp, client=FakeClient({"muc": []}))      # vòng nền không rà lại lần nữa
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM change_events WHERE kind='motion' AND state='reviewed'")
                         .fetchone()[0], 1)

    def test_director_rewrite_red_holds_with_reason(self):
        PR, sid, job = self._rewrite_setup()
        ans = {"muc": [{"khau": "motion", "shot": 2, "quan_sat": "lech", "muc_do": "do", "ly_do": "bỏ mất trạng thái cuối 'đứng sau tường'"}]}
        with mock.patch.object(PR, "client_for", return_value=FakeClient(ans)):
            PR.save_rewrite(self.p, job, PR.RewriteResult("slow push in, Kelly turns", ["thêm quay người"], "QC", 0, "push in"))
        reason = CR.blocking(self.p.conn, sid)
        self.assertIsNotNone(reason)
        self.assertIn("trạng thái cuối", reason)

    def test_director_rewrite_red_gets_one_more_rewrite_then_sends(self):
        # ĐỎ → Đạo diễn viết lại thêm MỘT lần với lời Tổ rà soát làm ghi chú; bản hai xanh → gửi được
        PR, sid, job = self._rewrite_setup()
        red = {"muc": [{"khau": "motion", "shot": 2, "quan_sat": "lech", "muc_do": "do", "ly_do": "bỏ mất trạng thái cuối"}]}
        answers = iter([red, {"muc": []}])

        class Seq(FakeClient):
            def complete(self, prompt, images=()):
                self.answer = next(answers)
                return super().complete(prompt, images)
        client = Seq(None)
        second = PR.RewriteResult("slow push in, Kelly turns, ends behind the wall", ["giữ trạng thái cuối"], "Tổ rà soát", 0,
                                  "slow push in, Kelly turns")
        with mock.patch.object(PR, "client_for", return_value=client), \
                mock.patch.object(PR, "propose_rewrite", return_value=second) as again:
            plan = PR.Plan(self.p, job, "Fix: x", PR.RewriteResult("slow push in, Kelly turns", ["thêm quay người"], "QC", 0, "push in"),
                           "x")
            plan.apply()
        self.assertEqual(again.call_count, 1)
        self.assertIn("trạng thái cuối", again.call_args.kwargs.get("fix") or "")
        self.assertEqual(PR.current_prompt(self.p.conn, sid, "video"), "slow push in, Kelly turns, ends behind the wall")
        self.assertEqual(len(client.calls), 2)
        self.assertIsNone(CR.blocking(self.p.conn, sid))

    def test_director_rewrite_red_on_image_stage_does_not_rewrite_motion_again(self):
        # ĐỎ thuộc khâu ảnh / nền: viết lại motion lần hai vô ích → không gọi, runner giữ kèm lý do như thường
        PR, sid, job = self._rewrite_setup()
        red = {"muc": [{"khau": "anh", "shot": 2, "quan_sat": "lech", "muc_do": "do", "ly_do": "ảnh khung đầu sai nền"}]}
        with mock.patch.object(PR, "client_for", return_value=FakeClient(red)), \
                mock.patch.object(PR, "propose_rewrite") as again:
            PR.Plan(self.p, job, "Fix: x", PR.RewriteResult("slow push in, Kelly turns", ["x"], "QC", 0, "push in"), "x").apply()
        again.assert_not_called()
        self.assertIn("ảnh khung đầu sai nền", CR.blocking(self.p.conn, sid) or "")

    def test_director_rewrite_without_claude_does_not_hold_and_says_so(self):
        # không gọi được Claude → luật code chạy, thay đổi thành 'code_only' (không giữ gen), VÀNG nói rõ — không im lặng
        PR, sid, job = self._rewrite_setup()
        with mock.patch.object(PR, "client_for", return_value=None):
            PR.save_rewrite(self.p, job, PR.RewriteResult("slow push in, Kelly turns", ["thêm quay người"], "QC", 0, "push in"))
        self.assertIsNone(CR.blocking(self.p.conn, sid))
        self.assertEqual(self.p.conn.execute("SELECT state FROM change_events WHERE kind='motion' ORDER BY id DESC").fetchone()[0],
                         "code_only")
        self.assertTrue(self.p.conn.execute("SELECT 1 FROM diag_events WHERE code='rewrite_review_noclaude'").fetchone())

    def test_director_rewrite_not_reviewed_when_motion_flag_off(self):
        # cờ change_review_motion tắt: như trước — không rà, không gọi Claude, không giữ
        from core import prompt_rewrite as PR
        sid = self.ids[1]
        self._motion(sid, "push in")
        self.p.conn.execute("UPDATE change_events SET state='skipped'")
        self.p.conn.commit()
        jid = self.p.create_job(sid, "video_gen")
        job = self.p.conn.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
        client = FakeClient({"muc": []})
        with mock.patch.object(PR, "client_for", return_value=client):
            PR.save_rewrite(self.p, job, PR.RewriteResult("slow push in, Kelly turns", ["thêm quay người"], "QC", 0, "push in"))
        self.assertEqual(client.calls, [])
        self.assertIsNone(CR.blocking(self.p.conn, sid))
        self._motion(sid, "hand edit")                                               # người sửa tay: vẫn ghi để rà khi bật cờ
        self.assertEqual(len([e for e in self.pending() if e["kind"] == "motion"]), 1)

if __name__ == "__main__":
    unittest.main()


class BeforeDirectorTests(unittest.TestCase):
    """Thử D6 #28 (14/10): tách cảnh ghi characters null → [] → Tổ rà soát báo ĐỎ 'chữ có Kelly mà mảng rỗng' trước khi Đạo diễn chạy."""

    def test_split_change_without_plan_fields_is_not_reviewed(self):
        split = {"before": json.dumps({"text": "Kelly chạy", "characters": None}), "after": json.dumps({"text": "Kelly chạy", "characters": []})}
        plan = {"before": json.dumps({"image_prompt": "x", "characters": ["KELLY"]}), "after": json.dumps({"image_prompt": "x", "characters": []})}
        self.assertTrue(CR._before_director(None, split))
        self.assertFalse(CR._before_director(None, plan))



class FailedReview(unittest.TestCase):
    """G35 (#31 19/10): rà LỖI (Claude hết tiền) mà cổng vẫn mở → job 1061 tự gửi khi chưa được rà. Rà lỗi = mục ĐỎ có lý do."""
    setUp, _new_scene, _set = ChangeReview.setUp, ChangeReview._new_scene, ChangeReview._set

    def _fail_review(self, sid):
        self._set(sid, {"size": "WS", "image_prompt": "Wide shot, Kelly", "characters": ["KELLY"]})

        class Broke(FakeClient):
            def complete(self, prompt, images=()):
                raise llm_runner.LlmError("credit balance is too low")
        res = CR.process_pending(self.p.conn, self.tmp, client=Broke({}))
        self.assertEqual(res["failed"], 1)

    def test_failed_review_holds_with_reason_and_skip_releases(self):
        self._fail_review(self.ids[1])
        why = CR.blocking(self.p.conn, self.ids[1])
        self.assertIsNotNone(why)                                            # trước sửa: None → job tốn tiền gửi đi
        self.assertIn("rà soát lỗi", why)
        self.assertIn("credit balance", why)
        self.assertIn("Bỏ qua", why)
        fid = [r for r in CR.open_findings(self.p.conn, self.pid) if r["khau"] == "ra_soat"][0]["id"]
        CR.close(self.p.conn, fid, "dismissed", "test")                      # nút Bỏ qua ở 📥
        self.assertIsNone(CR.blocking(self.p.conn, self.ids[1]))
        self.assertIsNone(CR.blocking(self.p.conn, self.ids[1]))             # bỏ qua rồi không ghi lại mục đó

    def test_failed_review_rerun_then_ok_releases(self):
        self._fail_review(self.ids[1])
        self.assertIn("rà soát lỗi", CR.blocking(self.p.conn, self.ids[1]))
        fid = [r for r in CR.open_findings(self.p.conn, self.pid) if r["khau"] == "ra_soat"][0]["id"]
        CR.rerun_failed(self.p.conn, fid, "test")                            # nút Rà lại (đã nạp tiền)
        self.assertIn("đang rà", CR.blocking(self.p.conn, self.ids[1]))
        CR.process_pending(self.p.conn, self.tmp, client=FakeClient({"muc": []}))
        self.assertIsNone(CR.blocking(self.p.conn, self.ids[1]))

    def test_failed_review_older_than_a_good_review_does_not_hold(self):
        self._fail_review(self.ids[1])
        self._set(self.ids[1], {"size": "CU", "image_prompt": "Close up, Kelly", "characters": ["KELLY"]})
        CR.process_pending(self.p.conn, self.tmp, client=FakeClient({"muc": []}))
        self.assertIsNone(CR.blocking(self.p.conn, self.ids[1]))

    def test_failed_review_upgrade_from_approved_draft_goes_to_notes(self):
        self._fail_review(self.ids[1])
        notes = []
        self.assertIsNone(CR.blocking(self.p.conn, self.ids[1], since="2000-01-01T00:00:00Z", notes=notes))   # C9 giữ nguyên
        self.assertTrue(any("rà soát lỗi" in n for n in notes))

    def test_failed_review_rerun_when_event_gone_keeps_hold(self):
        self._fail_review(self.ids[1])
        CR.blocking(self.p.conn, self.ids[1])
        fid = [r for r in CR.open_findings(self.p.conn, self.pid) if r["khau"] == "ra_soat"][0]["id"]
        self.p.conn.execute("DELETE FROM change_events WHERE state='failed'")          # dọn KEEP_DAYS
        with self.assertRaises(ValueError):
            CR.rerun_failed(self.p.conn, fid, "test")
        self.assertIn("rà soát lỗi", CR.blocking(self.p.conn, self.ids[1]))

    def test_failed_review_hold_error_never_opens_gate(self):
        self._fail_review(self.ids[1])
        with mock.patch.object(CR, "_hold_failed", side_effect=RuntimeError("database is locked")):
            self.assertIn("không đọc được", CR.blocking(self.p.conn, self.ids[1]))

    def test_inbox_clean_does_not_close_failed_review(self):
        from core import inbox_clean
        self._fail_review(self.ids[1])
        CR.blocking(self.p.conn, self.ids[1])
        self.p.conn.execute("INSERT INTO jobs(project_id, scene_id, type, state, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                            (self.pid, self.ids[1], "image_gen", "approved", "2026-10-19T00:00:00Z", "2026-10-19T00:00:00Z"))
        with mock.patch.object(inbox_clean, "_approved_at", return_value="2999-01-01T00:00:00Z"):
            self.assertFalse([f for f in inbox_clean.stale(self.p.conn, self.pid)["findings"] if "ra_soat" in str(f)])
            inbox_clean.clean(self.p, self.pid)
        self.assertIn("rà soát lỗi", CR.blocking(self.p.conn, self.ids[1]))


class M71FailClosed(unittest.TestCase):
    """C-M71 A1 (G35/B3, docs/KE_HOACH_SUA_20_CO_2026-10-21.md mục 1): rà LỖI — Claude hết tiền / hết lượt, timeout, trả rỗng — thì cổng
    giữ phải ĐÓNG (job ở 'queued' + lý do), có diag mã; không tự gửi. Cờ change_review tắt → như cũ (không giữ)."""
    setUp, _new_scene, _set = ChangeReview.setUp, ChangeReview._new_scene, ChangeReview._set
    _motion, _rewrite_setup = ChangeReview._motion, ChangeReview._rewrite_setup

    def test_director_rewrite_loop_quota_holds(self):
        # B3 vòng change_review ↔ director_rewrite (core/prompt_rewrite.py Plan._second_try / save_rewrite → _review_now): rà ngay bản
        # motion Đạo diễn vừa viết mà Claude hết tiền → giữ (trước: code_only → gửi khi chưa rà)
        PR, sid, job = self._rewrite_setup()

        class Q(FakeClient):
            def complete(self, prompt, images=()):
                raise llm_runner.LlmError("credit", code="out_of_credit")
        with mock.patch.object(PR, "client_for", return_value=Q({})):
            PR.save_rewrite(self.p, job, PR.RewriteResult("slow push in, Kelly turns", ["x"], "QC", 0, "push in"))
        self.assertIsNotNone(CR.blocking(self.p.conn, sid))

    def test_director_rewrite_loop_client_error_holds(self):
        # gọi client lỗi (khác "chưa cấu hình" = None) → thay đổi còn 'pending' (giữ "đang rà"), vòng nền rà sau; diag có mã
        PR, sid, job = self._rewrite_setup()
        with mock.patch.object(PR, "client_for", side_effect=RuntimeError("provider table broken")):
            PR.save_rewrite(self.p, job, PR.RewriteResult("slow push in, Kelly turns", ["x"], "QC", 0, "push in"))
        self.assertIn("đang rà", CR.blocking(self.p.conn, sid) or "")
        self.assertTrue(self.p.conn.execute("SELECT 1 FROM diag_events WHERE code='rewrite_review_fail'").fetchone())

    def _review_with(self, sid, exc=None, answer=None):
        self._set(sid, {"size": "WS", "image_prompt": "Wide shot, Kelly", "characters": ["KELLY"]})

        class C(FakeClient):
            def complete(self, prompt, images=()):
                if exc is not None:
                    raise exc
                return llm_runner.LlmReply(answer, 10, 0)
        return CR.process_pending(self.p.conn, self.tmp, client=C({}))

    def test_quota_out_of_credit_holds_gate(self):
        res = self._review_with(self.ids[1], llm_runner.LlmError("credit balance is too low", code="out_of_credit"))
        self.assertTrue(res.get("halted"))
        why = CR.blocking(self.p.conn, self.ids[1])
        self.assertIsNotNone(why)                                  # trước C-M71: code_only → None → job tự gửi (G35)
        self.assertIn("Claude", why)
        self.assertIn("Bỏ qua", why)

    def test_quota_usage_limit_holds_then_claude_review_releases(self):
        self._review_with(self.ids[1], llm_runner.LlmError("session limit", code="usage_limit"))
        self.assertIsNotNone(CR.blocking(self.p.conn, self.ids[1]))
        CR.process_pending(self.p.conn, self.tmp, client=FakeClient({"muc": []}))    # Claude mở lại: vòng nền tự rà lại
        self.assertIsNone(CR.blocking(self.p.conn, self.ids[1]))

    def test_quota_hold_skip_releases_and_rerun_works(self):
        self._review_with(self.ids[1], llm_runner.LlmError("credit", code="out_of_credit"))
        CR.blocking(self.p.conn, self.ids[1])
        fid = [r for r in CR.open_findings(self.p.conn, self.pid) if r["khau"] == CR.FAIL_KHAU][0]["id"]
        CR.rerun_failed(self.p.conn, fid, "test")                           # nút Rà lại
        self.assertIn("đang rà", CR.blocking(self.p.conn, self.ids[1]))
        import time as _t
        _t.sleep(1.1)                                                       # reviewed_at mới (giây) cho lần rà dừng thứ hai

        class Q(FakeClient):
            def complete(self, prompt, images=()):
                raise llm_runner.LlmError("credit", code="out_of_credit")
        CR.process_pending(self.p.conn, self.tmp, client=Q({}))             # vẫn hết tiền → giữ lại, mục mới
        self.assertIsNotNone(CR.blocking(self.p.conn, self.ids[1]))
        fid = [r for r in CR.open_findings(self.p.conn, self.pid) if r["khau"] == CR.FAIL_KHAU][0]["id"]
        CR.close(self.p.conn, fid, "dismissed", "test")                     # nút Bỏ qua ở 📥
        self.assertIsNone(CR.blocking(self.p.conn, self.ids[1]))

    def test_no_claude_round_still_does_not_hold(self):
        self._set(self.ids[1], {"size": "WS", "image_prompt": "Wide shot, Kelly", "characters": ["KELLY"]})
        CR.process_pending(self.p.conn, self.tmp, client=None)               # không cấu hình Claude: thiết kế cũ, không giữ
        self.assertIsNone(CR.blocking(self.p.conn, self.ids[1]))

    def test_timeout_and_empty_answer_hold(self):
        self._review_with(self.ids[1], llm_runner.LlmError("timed out", code="timeout"))
        self.assertIn("rà soát lỗi", CR.blocking(self.p.conn, self.ids[1]) or "")
        self._review_with(self.ids[2], answer="")
        self.assertIn("rà soát lỗi", CR.blocking(self.p.conn, self.ids[2]) or "")

    def test_flag_off_never_holds(self):
        self._review_with(self.ids[1], llm_runner.LlmError("credit", code="out_of_credit"))
        with mock.patch.dict(os.environ, {"FEATURE_CHANGE_REVIEW": "0"}):
            self.assertIsNone(CR.blocking(self.p.conn, self.ids[1]))

    def test_unreadable_table_holds_instead_of_raising(self):
        class Broken:
            def __init__(self, conn):
                self.conn = conn

            def execute(self, sql, *a):
                if "change_events" in sql:
                    raise RuntimeError("database disk image is malformed")
                return self.conn.execute(sql, *a)
        why = CR.blocking(Broken(self.p.conn), self.ids[1])
        self.assertIn("không đọc được", why or "")

    def test_scene_now_quota_says_diag_with_code(self):
        self._set(self.ids[1], {"size": "WS", "image_prompt": "Wide shot, Kelly", "characters": ["KELLY"]})

        class Q(FakeClient):
            def complete(self, prompt, images=()):
                raise llm_runner.LlmError("credit", code="out_of_credit")
        CR.review_scene_now(self.p.conn, self.tmp, self.ids[1], client=Q({}))
        self.assertTrue(self.p.conn.execute("SELECT 1 FROM diag_events WHERE code='change_review_halt'").fetchone())
        self.assertIsNotNone(CR.blocking(self.p.conn, self.ids[1]))

    def test_runner_keeps_job_queued_with_reason(self):
        from core.providers import MockImageProvider
        from core.runner import ImageRunner, WAIT_REASONS
        self._review_with(self.ids[1], llm_runner.LlmError("credit", code="out_of_credit"))
        jid = self.p.create_job(self.ids[1], "image_gen")
        runner = ImageRunner(self.p, MockImageProvider(), self.tmp)
        sent = runner.submit_pending(self.pid)
        self.assertEqual(sent, 0)
        self.assertEqual(self.p.conn.execute("SELECT state FROM jobs WHERE id=?", (jid,)).fetchone()[0], "queued")
        self.assertIn("Tổ rà soát", WAIT_REASONS.get(jid, ("",))[0])
        self.assertTrue(self.p.conn.execute("SELECT 1 FROM diag_events WHERE code='change_review_hold' AND job_id=?", (jid,)).fetchone())


class M71DeepReview(unittest.TestCase):
    """Rà kỹ C-M71 (@c03ae66b): lỗi CAO/VỪA của A1 — mỗi lỗi một test đúng kịch bản."""
    setUp, _new_scene, _set = ChangeReview.setUp, ChangeReview._new_scene, ChangeReview._set
    _review_with = M71FailClosed._review_with

    def test_failed_motion_review_finding_closes_when_the_motion_flag_is_turned_off(self):
        # C-FIX3-THAP 1: rà sửa motion LỖI (timeout) khi cờ change_review_motion BẬT → mục ĐỎ; tắt cờ → vòng nền (process_pending) bỏ
        # sự kiện motion failed → mục tự đóng, không chặn nữa (trước: chỉ pending / code_only → mục kẹt)
        os.environ["FEATURE_CHANGE_REVIEW_MOTION"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_CHANGE_REVIEW_MOTION", None)
        sid = self.ids[1]
        ChangeReview._motion(self, sid, "Kelly kneels by the well")
        self.p.conn.execute("UPDATE change_events SET state='skipped'")
        ChangeReview._motion(self, sid, "Kelly stands up and walks to the well")              # SỬA motion → sự kiện kind 'motion'
        self.p.conn.execute("UPDATE change_events SET state='skipped' WHERE kind<>'motion'")
        self.p.conn.commit()

        class Boom(FakeClient):
            def complete(self, prompt, images=()):
                raise llm_runner.LlmError("timed out", code="timeout")
        CR.process_pending(self.p.conn, self.tmp, client=Boom({}))
        self.assertEqual([r[0] for r in self.p.conn.execute("SELECT state FROM change_events WHERE kind='motion'")], ["failed"])
        self.assertIn("rà soát lỗi", CR.blocking(self.p.conn, sid) or "")
        os.environ["FEATURE_CHANGE_REVIEW_MOTION"] = "0"
        CR.process_pending(self.p.conn, self.tmp, client=None)
        self.assertIsNone(CR.blocking(self.p.conn, sid))
        self.assertFalse([r for r in CR.open_findings(self.p.conn, self.pid) if r["khau"] == "ra_soat"])

    def test_failed_change_not_released_by_later_good_review(self):
        # CAO 1: X rà lỗi (timeout) → mục ĐỎ; người sửa tiếp Y; nền rà Y đạt — Y.before = sau X nên Claude không thấy X → vẫn giữ
        self._review_with(self.ids[1], llm_runner.LlmError("timed out", code="timeout"))
        self.assertIn("rà soát lỗi", CR.blocking(self.p.conn, self.ids[1]) or "")
        self._set(self.ids[1], {"size": "CU", "image_prompt": "Close up, Kelly", "characters": ["KELLY"]})
        CR.process_pending(self.p.conn, self.tmp, client=FakeClient({"muc": []}))
        self.assertIn("rà soát lỗi", CR.blocking(self.p.conn, self.ids[1]) or "")

    def test_quota_change_rereviewed_through_project_client(self):
        # VỪA 2: máy không có Claude chung (client None), dự án có Claude riêng (client_for) → code_only hết tiền được rà lại
        self._review_with(self.ids[1], llm_runner.LlmError("credit", code="out_of_credit"))
        self.assertIsNotNone(CR.blocking(self.p.conn, self.ids[1]))
        good = FakeClient({"muc": []})
        CR.process_pending(self.p.conn, self.tmp, client=None, client_for=lambda pid: good)
        self.assertEqual(len(good.calls), 1)
        self.assertIsNone(CR.blocking(self.p.conn, self.ids[1]))

    def test_project_without_claude_does_not_loop_code_only(self):
        self._review_with(self.ids[1], llm_runner.LlmError("credit", code="out_of_credit"))
        before = self.p.conn.execute("SELECT state, note, reviewed_at FROM change_events WHERE state='code_only'").fetchall()
        CR.process_pending(self.p.conn, self.tmp, client=None, client_for=lambda pid: None)
        after = self.p.conn.execute("SELECT state, note, reviewed_at FROM change_events WHERE state='code_only'").fetchall()
        self.assertEqual([tuple(r) for r in before], [tuple(r) for r in after])      # không đụng, không quay vòng

    def test_failed_finding_closes_when_its_event_is_skipped(self):
        # C-M71-FIX (THẤP 2): cờ change_review_motion tắt → process_pending đổi motion code_only (kể cả dòng hết tiền) sang 'skipped';
        # rà lại ra keys rỗng cũng 'skipped' → mục ĐỎ của chính thay đổi đó phải tự đóng (trước chỉ 'reviewed' → kẹt tới khi bấm Bỏ qua)
        self._review_with(self.ids[1], llm_runner.LlmError("credit", code="out_of_credit"))
        self.assertIsNotNone(CR.blocking(self.p.conn, self.ids[1]))
        self.p.conn.execute("UPDATE change_events SET state='skipped', reviewed_at=? WHERE scene_id=? AND state='code_only'",
                            ("2026-10-22T00:00:00Z", self.ids[1]))
        self.p.conn.commit()
        self.assertIsNone(CR.blocking(self.p.conn, self.ids[1]))
        self.assertFalse([r for r in CR.open_findings(self.p.conn, self.pid) if r["khau"] == "ra_soat"])

    def test_limit_is_not_eaten_by_projects_without_claude(self):
        # C-M71-FIX (THẤP 3): ≥ LIMIT nhóm code_only hết tiền của dự án KHÔNG có Claude (id nhỏ hơn) không được ăn suất của dự án CÓ Claude
        for i in range(6):
            self.p.conn.execute("INSERT INTO change_events (at, kind, project_id, scene_id, state, note, cost_usd) VALUES "
                                "('2026-10-21T00:00:00Z', 'scene', 999, ?, 'code_only', ?, 0)", (90001 + i, CR.QUOTA_NOTE + " hết tiền"))
        self.p.conn.commit()
        self._review_with(self.ids[1], llm_runner.LlmError("credit", code="out_of_credit"))
        good = FakeClient({"muc": []})
        CR.process_pending(self.p.conn, self.tmp, client=None, client_for=lambda pid: good if pid == self.pid else None, limit=5)
        self.assertEqual(len(good.calls), 1)
        self.assertIsNone(CR.blocking(self.p.conn, self.ids[1]))

    def test_blocking_writes_nothing_when_nothing_to_do(self):
        # VỪA 3: blocking() mỗi nhịp không được ghi / commit khi không có gì đổi
        self._review_with(self.ids[1], llm_runner.LlmError("timed out", code="timeout"))
        CR.blocking(self.p.conn, self.ids[1])                                 # mục ĐỎ đã ghi
        n = self.p.conn.total_changes
        for _ in range(3):
            CR.blocking(self.p.conn, self.ids[1])
            CR.blocking(self.p.conn, self.ids[2])
        self.assertEqual(self.p.conn.total_changes, n)

    def test_blocking_never_commits_callers_transaction(self):
        self._review_with(self.ids[1], llm_runner.LlmError("timed out", code="timeout"))
        self.p.conn.execute("UPDATE projects SET name='dở' WHERE id=?", (self.pid,))          # giao dịch dở của người gọi
        self.assertTrue(self.p.conn.in_transaction)
        self.assertIsNotNone(CR.blocking(self.p.conn, self.ids[1]))           # ghi mục ĐỎ trong giao dịch, không commit hộ
        self.p.conn.rollback()
        self.assertNotEqual(self.p.conn.execute("SELECT name FROM projects WHERE id=?", (self.pid,)).fetchone()[0], "dở")

    def test_autopilot_treats_unreadable_as_temporary(self):
        from core import autopilot
        jid = self.p.create_job(self.ids[1], "image_gen")
        self.assertTrue(jid)
        with mock.patch.object(CR, "blocking", return_value=CR.READ_FAIL + " (OperationalError: database is locked) — thử lại sau"):
            autopilot._review_wait(self.p, self.pid, "image_gen")              # không ném _Wait (chờ người)
        with mock.patch.object(CR, "blocking", return_value="Tổ rà soát tác động: anh: sai"):
            with self.assertRaises(autopilot._Wait):
                autopilot._review_wait(self.p, self.pid, "image_gen")
