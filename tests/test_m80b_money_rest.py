"""M8.0b — phần còn của M8.0 "An toàn tiền" (cờ `safe_paid_buttons`): khóa hỏi treo `paid_ask_<key>` được dọn theo số lượt chạy,
"Duyệt tất cả" xem trước + giá + HOLD + hẹn 30 s hoàn tác (E2, sổ ep-2210-e2-approve-all-preview), "✔ Mẫu thử ổn" (pilot_release) hẹn
hoàn tác, `paid_button(free=…)` và nhãn cờ TẮT giữ y như cũ.
Chạy: PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_m80b_money_rest.py"""
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest


# ---- 4. khóa hỏi treo -------------------------------------------------------------------------------------------------------------
class StaleAskSweep(unittest.TestCase):
    def setUp(self):
        from dashboard import paid_confirm as P
        self.P = P

    def test_key_not_drawn_for_a_whole_run_is_dropped(self):
        ss = {}
        self.P.begin_run(ss)                                   # lượt 1: nút vẽ + bấm → hỏi
        self.P.mark_drawn(ss, "gen")
        ss["paid_ask_gen"] = True
        self.P.begin_run(ss)                                   # lượt 2: vẫn giữ (vẽ ở lượt 1)
        self.assertTrue(ss.get("paid_ask_gen"))
        self.P.begin_run(ss)                                   # lượt 3: lượt 2 không vẽ → bỏ
        self.assertNotIn("paid_ask_gen", ss)

    def test_key_drawn_every_run_is_kept(self):
        ss = {}
        for _ in range(5):
            self.P.begin_run(ss)
            self.P.mark_drawn(ss, "gen")
            ss["paid_ask_gen"] = True
        self.P.begin_run(ss)
        self.assertTrue(ss.get("paid_ask_gen"))

    def test_untracked_ask_key_is_dropped(self):
        ss = {"paid_ask_old": True, "other": 1}
        self.P.begin_run(ss)
        self.assertNotIn("paid_ask_old", ss)
        self.assertEqual(ss["other"], 1)


def _app_sweep():
    import streamlit as st
    from dashboard import paid_confirm as P
    P.begin_run(st.session_state)
    if st.session_state.get("show", True):
        if P.paid_button("🎬 Dựng", "t_sw", " · Claude ≈ 0.10 USD (ước tính)"):
            st.session_state["ran"] = st.session_state.get("ran", 0) + 1
    st.write(f"ran={st.session_state.get('ran', 0)}")


class StaleAskApp(unittest.TestCase):
    def test_question_gone_after_the_button_left_the_screen(self):
        with mock.patch("dashboard.paid_confirm.enabled", return_value=True):
            at = AppTest.from_function(_app_sweep).run()
            at.button(key="t_sw").click().run()
            self.assertIn("t_sw_yes", {b.key for b in at.button})
            at.session_state["show"] = False                  # đổi màn: nút không còn được vẽ
            at.run()
            at.run()
            at.session_state["show"] = True                   # quay lại: nút thường, KHÔNG còn hộp hỏi cũ
            at.run()
            keys = {b.key for b in at.button}
            self.assertIn("t_sw", keys)
            self.assertNotIn("t_sw_yes", keys)
            self.assertIn("ran=0", " ".join(m.value for m in at.markdown))


# ---- free + nhãn cờ TẮT -------------------------------------------------------------------------------------------------------------
class PaidButtonLabels(unittest.TestCase):
    def _call(self, on, **kw):
        from dashboard import paid_confirm as P
        box = mock.Mock()
        box.button.return_value = False
        with mock.patch.object(P, "enabled", return_value=on):
            P.paid_button("🤖 Lập kế hoạch", "k", kw.pop("tag", ""), box, **kw)
        return box

    def test_flag_off_label_is_exactly_label_plus_tag(self):
        """Cờ TẮT: nhãn = nhãn cũ (label + tag), không thêm 'chưa có giá' khi nút cũ không có giá."""
        box = self._call(False, tag="")
        self.assertEqual(box.button.call_args.args[0], "🤖 Lập kế hoạch")
        box = self._call(False, tag=" (≈ 0.30 USD, ước tính)")
        self.assertEqual(box.button.call_args.args[0], "🤖 Lập kế hoạch (≈ 0.30 USD, ước tính)")

    def test_flag_on_empty_tag_says_no_price(self):
        box = self._call(True, tag="")
        self.assertIn("chưa có giá", box.button.call_args.args[0])

    def test_free_is_a_plain_button_without_question(self):
        from dashboard import paid_confirm as P
        box = mock.Mock()
        box.button.return_value = True
        with mock.patch.object(P, "enabled", return_value=True):
            self.assertTrue(P.paid_button("📝 Tạo phụ đề", "s", "", box, free=True))
        self.assertEqual(box.button.call_args.args[0], "📝 Tạo phụ đề")


# ---- 2. "Duyệt tất cả": xem trước + HOLD + hẹn ------------------------------------------------------------------------------------
class ApproveRun(unittest.TestCase):
    def setUp(self):
        from dashboard import approve_preview as A, paid_confirm as P
        self.A, self.P = A, P

    def _rows(self, ids, hold=()):
        return [{"id": i, "scene_id": 100 + i, "idx": i, "text": f"S{i:02d}", "hold": "ảnh cũ" if i in hold else None} for i in ids]

    def _run(self, it, now_ids, now_rows):
        p = mock.Mock(actor="ep")
        with mock.patch.object(self.A, "pending_ids", return_value=now_ids), mock.patch.object(self.A, "rows", return_value=now_rows):
            return self.P.run_item(p, it, lambda pid, user: None), p

    def test_unchanged_approves_only_eligible_ids(self):
        it = {"action": "approve_images", "pid": 7, "kind": "images", "ids": [1, 2, 3], "ok": [1, 3]}
        why, p = self._run(it, [1, 2, 3], self._rows([1, 2, 3], hold={2}))
        self.assertEqual(why, "")
        self.assertEqual([c.args[0] for c in p.approve.call_args_list], [1, 3])          # mục HOLD (2) không duyệt

    def test_list_changed_no_approval(self):
        it = {"action": "approve_images", "pid": 7, "kind": "images", "ids": [1, 2], "ok": [1, 2]}
        why, p = self._run(it, [1, 2, 4], self._rows([1, 2, 4]))
        self.assertIn("Không duyệt", why)
        p.approve.assert_not_called()

    def test_hold_changed_no_approval(self):
        it = {"action": "approve_images", "pid": 7, "kind": "images", "ids": [1, 2], "ok": [1, 2]}
        why, p = self._run(it, [1, 2], self._rows([1, 2], hold={2}))
        self.assertIn("Không duyệt", why)
        p.approve.assert_not_called()

    def test_motion_and_clips_use_their_approve(self):
        it = {"action": "approve_motion", "pid": 7, "kind": "motion", "ids": [5], "ok": [5]}
        with mock.patch("core.llm_io.approve_motion_prompt") as amp:
            why, p = self._run(it, [5], self._rows([5]))
        self.assertEqual(why, "")
        amp.assert_called_once_with(p, 5)
        it = {"action": "approve_clips", "pid": 7, "kind": "clips", "ids": [9], "ok": [9]}
        with mock.patch("dashboard.quality_ui.approve_clip") as ac:
            why, p = self._run(it, [9], self._rows([9]))
        self.assertEqual(why, "")
        ac.assert_called_once_with(p, 9, note="gate_bulk")

    def test_hold_rules(self):
        """HOLD = mục chưa đủ điều kiện: motion cũ / cảnh chưa có ảnh duyệt; clip làm từ đầu vào cũ."""
        conn = mock.Mock()
        scan = {11: {"idx": 1, "image_job_id": 3, "motion_stale": None, "video_job_id": 21, "video_stale": None},
                12: {"idx": 2, "image_job_id": 4, "motion_stale": "ảnh đã được thay", "video_job_id": 22, "video_stale": "ảnh đã được thay"},
                13: {"idx": 3, "image_job_id": None, "motion_stale": None, "video_job_id": None, "video_stale": None}}
        with mock.patch("core.lineage.scan", return_value=scan), \
                mock.patch.object(self.A, "_scene_of", side_effect=lambda conn, kind, i: {11: 11, 12: 12, 13: 13, 21: 11, 22: 12}[i]):
            mot = {r["id"]: r["hold"] for r in self.A.rows(conn, 7, "motion", [11, 12, 13])}
            clip = {r["id"]: r["hold"] for r in self.A.rows(conn, 7, "clips", [21, 22])}
        self.assertIsNone(mot[11])
        self.assertIn("ảnh đã được thay", mot[12])
        self.assertIn("chưa có ảnh", mot[13])
        self.assertIsNone(clip[21])
        self.assertIn("ảnh đã được thay", clip[22])

    def test_clip_and_motion_lineage_fail_closed_for_each_job_and_on_recheck(self):
        """Clip cũ không mượn dấu của job mới nhất; thiếu scan/lineage hoặc lỗi khi quét đều là HOLD cả lúc xem lẫn lúc chạy."""
        conn = mock.Mock()
        newest_stale = {11: {"idx": 1, "image_job_id": 3, "motion_stale": None,
                             "video_job_id": 22, "video_stale": "motion prompt đã đổi"}}
        scene_for = {11: 11, 21: 11, 22: 11}
        with mock.patch("core.lineage.scan", return_value=newest_stale), \
                mock.patch.object(self.A, "_scene_of", side_effect=lambda _c, _k, i: scene_for[i]):
            clips = {r["id"]: r["hold"] for r in self.A.rows(conn, 7, "clips", [21, 22])}
        self.assertIn("lineage", clips[21])                         # job cũ không khớp job mà scan đã kiểm
        self.assertIn("motion prompt", clips[22])                   # job mới có lý do cũ riêng

        for failed_scan in ({}, RuntimeError("scan unavailable")):
            scan_patch = mock.patch("core.lineage.scan", side_effect=failed_scan) if isinstance(failed_scan, Exception) \
                else mock.patch("core.lineage.scan", return_value=failed_scan)
            with scan_patch, mock.patch.object(self.A, "_scene_of", side_effect=lambda _c, _k, i: scene_for[i]):
                held = self.A.rows(conn, 7, "clips", [21, 22])
                motion = self.A.rows(conn, 7, "motion", [11])
            self.assertTrue(all("lineage" in r["hold"] for r in held))
            self.assertIn("lineage", motion[0]["hold"])

        it = {"kind": "clips", "pid": 7, "ids": [21], "ok": [21]}
        with mock.patch.object(self.A, "pending_ids", return_value=[21]), \
                mock.patch("core.lineage.scan", return_value={}), \
                mock.patch.object(self.A, "_scene_of", side_effect=lambda _c, _k, i: scene_for[i]), \
                mock.patch("dashboard.quality_ui.approve_clip") as approve:
            why = self.A.run(mock.Mock(actor="ep"), it)
        self.assertIn("Không duyệt", why)
        approve.assert_not_called()

    def test_image_lineage_exception_is_hold_and_legacy_null_hash_stays_allowed(self):
        conn = mock.Mock()
        with mock.patch("core.lineage.scan", return_value={}), \
                mock.patch.object(self.A, "_scene_of", return_value=11), \
                mock.patch.object(self.A, "_image_hold", side_effect=ValueError("invalid lineage data")):
            item = self.A.rows(conn, 7, "images", [51])[0]
        self.assertIn("không xác minh được lineage", item["hold"])

        legacy = mock.Mock()
        legacy.execute.return_value.fetchone.return_value = (None, "{}")
        self.assertIsNone(self.A._image_hold(legacy, 7, 51))

    def test_price_line_says_approve_is_free(self):
        with mock.patch("core.cost.clip_estimate", return_value=0.5):
            line = self.A.price_line(mock.Mock(), "images", self._rows([1, 2], hold={2}))
        self.assertIn("0 USD", line)
        self.assertIn("0.50", line)                           # bước kế (video) chỉ tính mục được duyệt
        self.assertIn("0 USD", self.A.price_line(mock.Mock(), "clips", self._rows([1])))


def _app_approve():
    import streamlit as st
    from dashboard import approve_preview as A
    A.approve_all_box(st.session_state["p"], 7, "images", "approve_all", [1, 2], "✔ Duyệt tất cả (2 ảnh)")


class ApproveBoxApp(unittest.TestCase):
    def test_preview_lists_items_and_hold_then_schedules_not_approves(self):
        from dashboard import approve_preview as A, paid_confirm as P
        rows = [{"id": 1, "scene_id": 11, "idx": 1, "text": "S01 · ảnh job 1", "hold": None},
                {"id": 2, "scene_id": 12, "idx": 2, "text": "S02 · ảnh job 2", "hold": "đầu vào cảnh đã đổi"}]
        p = mock.Mock(actor="ep")
        with mock.patch.object(A, "rows", return_value=rows), mock.patch.object(A, "price_line", return_value="Duyệt: 0 USD"), \
                mock.patch.object(P, "enabled", return_value=True), mock.patch("dashboard.common.log_ui"):
            at = AppTest.from_function(_app_approve)
            at.session_state["p"] = p
            at.run()
            at.button(key="approve_all").click().run()
            self.assertFalse(at.exception, at.exception)
            text = " ".join(m.value for m in at.markdown) + " ".join(w.value for w in at.warning)
            self.assertIn("S01", text)
            self.assertIn("HOLD", text)
            self.assertIn("0 USD", text)
            at.button(key="approve_all_yes").click().run()
            self.assertFalse(at.exception, at.exception)
            items = list(at.session_state[P.UNDO_KEY].values())
        self.assertEqual(len(items), 1)
        self.assertEqual((items[0]["action"], items[0]["ids"], items[0]["ok"]), ("approve_images", [1, 2], [1]))
        p.approve.assert_not_called()                                              # chỉ hẹn — chưa duyệt


# ---- 3. pilot_release -----------------------------------------------------------------------------------------------------------
class PilotRelease(unittest.TestCase):
    def _run(self, state, done=True):
        from core import pilot
        from dashboard import paid_confirm as P
        it = {"action": "pilot_release", "pid": 7, "scenes": [1, 2]}
        with mock.patch.object(pilot, "get", return_value=state), mock.patch.object(pilot, "done", return_value=done), \
                mock.patch.object(pilot, "release") as rel:
            why = P.run_item(mock.Mock(actor="ep"), it, lambda pid, user: None)
        return why, rel

    def test_unchanged_releases(self):
        why, rel = self._run({"enabled": True, "scenes": [1, 2], "released": False})
        self.assertEqual(why, "")
        rel.assert_called_once()

    def test_changed_does_not_release(self):
        for state, done in (({"enabled": True, "scenes": [1, 3], "released": False}, True),
                            ({"enabled": True, "scenes": [1, 2], "released": True}, True),
                            ({"enabled": False, "scenes": [], "released": False}, True),
                            ({"enabled": True, "scenes": [1, 2], "released": False}, False)):
            why, rel = self._run(state, done)
            self.assertIn("Không", why, state)
            rel.assert_not_called()


if __name__ == "__main__":
    unittest.main()
