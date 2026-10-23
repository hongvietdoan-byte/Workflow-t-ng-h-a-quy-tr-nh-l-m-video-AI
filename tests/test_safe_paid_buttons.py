"""M8.0 An toàn tiền (cờ `safe_paid_buttons`, sổ ep-2210-qf-money-safety-first): quét mã dashboard/ tìm mọi nút gọi đường tốn tiền
(gen ảnh/video/âm thanh qua `runner`, lời gọi Claude qua `client` / `llm` / `llm_client()`, và các hàm tốn tiền gián tiếp ở PAID_CALLS)
— mỗi nút phải có GIÁ trên nhãn + XÁC NHẬN (paid_button / confirm_all), hoặc nằm trong EXCEPTIONS kèm lý do. Sáu chỗ kế hoạch nêu
(docs/KE_HOACH_DASHBOARD_DON_GIAN_2026-10-21.md dòng 21) + nút duyệt gửi tiền KHÔNG được nằm trong ngoại lệ.
Chạy: PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_safe_paid_buttons.py"""
import ast
import os
import re
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASH = os.path.join(ROOT, "dashboard")

# Hàm tốn tiền gián tiếp (không nhận client/runner trong lời gọi ở nút): gỡ chặn vòng nền Claude, nhả autopilot gửi video…
PAID_CALLS = {"autopilot.resume", "previz.plan_layouts", "previz.review_storyboard", "CR.rerun_failed", "autoqc.clear_error",
              "autoqc.clear_video_error", "Chat.send", "P.schedule_resume", "paid_confirm.schedule_resume"}
MONEY_ARGS = {"client", "llm", "runner"}
CONFIRM_FUNCS = ("paid_button", "confirm_all", "_confirm_all_primary")
PRICE_RE = re.compile(r"tag|price|estimate|usd|credit", re.I)

# Ngoại lệ: "<file>::<key>" → lý do. Mục không còn khớp nút nào → test đỏ (danh sách không được cũ).
_PRICE_ONLY = ("giá trên nút (D01b: thao tác EP bấm tay = cảnh báo + giá, ep-2210-qd2); ngoài 6 chỗ M8.0 — xác nhận thêm khi gộp ở M8.6 "
               "(chế độ Đơn giản ẩn / tự động)")
_FREE = "0 USD: chỉ hỏi trạng thái / tải về / hủy / nối lại task đã trả tiền (không gửi việc mới)"
EXCEPTIONS = {
    "admin.py::'ls_judge'": _PRICE_ONLY, "admin.py::'ls_mine'": _PRICE_ONLY, "admin.py::'ls_research'": _PRICE_ONLY,
    "admin.py::f'kb_distill_{group}'": _PRICE_ONLY, "admin.py::'va_go'": _PRICE_ONLY,
    "admin.py::'meshy_go'": "ô tick 'Tôi đồng ý trả ≈ N credit' bắt buộc trước khi nút bật (xác nhận + giá có sẵn)",
    "admin.py::f\"meshy_rig{r['id']}\"": _PRICE_ONLY + " (màn quản trị Kho 3D)",
    "admin.py::'meshy_refresh'": _FREE,
    "end_frame_ui.py::f'efoff_{scene_id}'": _PRICE_ONLY, "quality_ui.py::f'qfinal_{scene_id}'": _PRICE_ONLY,
    "send_preview_ui.py::f'sendpv_btn_{jid}'": _PRICE_ONLY,
    "steps/step1_characters.py::f'outfit_set_{pid}_{name}'": _PRICE_ONLY, "steps/step1_characters.py::f'{k}_ai'": _PRICE_ONLY,
    "steps/step1_characters.py::f'bcheck_{pid}'": _PRICE_ONLY, "steps/step1_characters.py::f'cast_{pid}'": _PRICE_ONLY,
    "steps/step1_checklist.py::f'asset_chk_{scope}_{pid}'": _PRICE_ONLY, "steps/step1_director.py::f'dlg_ai_{pid}'": _PRICE_ONLY,
    "steps/step1_director.py::f'replan_{pid}_{scene_idx}'": _PRICE_ONLY, "steps/step1_idea.py::f'idea_redo_d_{pid}'": _PRICE_ONLY,
    "steps/step1_intake.py::f'ci_style_{pid}'": _PRICE_ONLY, "steps/step1_prep.py::f'wb_run_{pid}'": _PRICE_ONLY,
    "steps/step1_v2.py::f'script-cta_{pid}'": _PRICE_ONLY + " ('🤖 Lập kế hoạch' — gộp vào 'Được, làm tiếp' ở M8.6)",
    "steps/step2.py::f'gen_img_{pid}'": _PRICE_ONLY + " + show_estimate: lô lớn bắt tick xác nhận (confirm_batch_at)",
    "steps/step2.py::f'setqc_{pid}'": _PRICE_ONLY, "steps/step3.py::f'llm_mot_{pid}'": _PRICE_ONLY,
    "steps/step3.py::f'lint_{pid}'": _PRICE_ONLY, "steps/step4.py::'btn_bad_retry'": _PRICE_ONLY,
    "steps/step4.py::f'clipqc_{pid}'": _PRICE_ONLY, "steps/step4.py::f'seqlogic_{pid}'": _PRICE_ONLY,
    "steps/step4.py::f'vr_rej_{jid}'": _PRICE_ONLY + " (gen lại một clip, lý do bắt buộc)",
    "steps/step4.py::f'vc_{jid}'": _FREE, "steps/step4.py::f'vrl_{jid}'": _FREE, "steps/step4.py::f'ms_refresh_{pid}'": _FREE,
    "steps/step4.py::f'quality_refresh_{pid}'": _FREE,
    "steps/step5.py::f'deliver_{pid}'": _PRICE_ONLY + " ('📦 Xuất bản' — Claude chỉ khi dịch phụ đề)",
    "steps/step5.py::f'mbrief_ai_{pid}'": _PRICE_ONLY, "steps/step5.py::f'sub_make_{pid}'": _PRICE_ONLY,
    "steps/step5.py::f'sfx_ai_go_{pid}'": _PRICE_ONLY, "steps/step5.py::f'editor_review_{pid}'": _PRICE_ONLY,
    "quality_ui.py::f'qfinal_new_{scene_id}'": "giá + xác nhận có sẵn: nhãn/câu hỏi do new_final_texts dựng (chứa _usd_text) + confirm_all",
    "quality_ui.py::f'qfinal_allnew_{pid}'": "giá + xác nhận có sẵn: nhãn/câu hỏi do new_final_texts dựng (chứa _usd_text) + confirm_all",
    "design/screens/money_days.py::'md_new_go'": "0 USD: mở đợt ngân sách mới; `llm` ở đây là trần USD (số), không phải client",
    "steps/step5.py::f'sub_burn_{pid}'":"0 USD: in phụ đề với cues đã dịch truyền vào (delivery.subtitle_layer không gọi localize khi có cues)",
}
# 6 chỗ thiếu giá + xác nhận (kế hoạch dòng 21) + nút duyệt gửi tiền (mục 8.4): phải có GIÁ + XÁC NHẬN, không được là ngoại lệ.
M80_SPOTS = [("steps/step1_prep.py", "pv_plan_"), ("steps/step1_prep.py", "pv_review_"), ("change_review_ui.py", "_rerun_"),
             ("steps/step2.py", "autoqc_retry_"), ("steps/step4.py", "vqc_retry_"),
             ("design/screens/storyboard_cards.py", "board_ok_"), ("steps/step2.py", "board_ok_"), ("steps/step1_run.py", "ap_resume_")]
# `paid_button(..., ask=False)`: chính nút là bước xác nhận của việc người dùng vừa làm (tin chat đã gõ + Enter) — chỉ được dùng ở đây.
ASK_FALSE_OK = {("steps/step1_box.py", "box_chatsend_go_"), ("steps/step1_box.py", "box_chatask_chat_")}


def dotted(n) -> str:
    if isinstance(n, ast.Name):
        return n.id
    if isinstance(n, ast.Attribute):
        base = dotted(n.value)
        return (base + "." if base else "") + n.attr
    if isinstance(n, ast.Call):
        return dotted(n.func) + "()"
    return ""


def _is_button(call: ast.Call) -> bool:
    name = dotted(call.func)
    return name.endswith(".button") or name in ("button", "cta", "D.cta") or name.split(".")[-1] in CONFIRM_FUNCS


def _paid_calls(body) -> set:
    hits = set()
    for stmt in body:
        for n in ast.walk(stmt):
            if not isinstance(n, ast.Call):
                continue
            name = dotted(n.func)
            if name in PAID_CALLS:
                hits.add(name)
            for a in list(n.args) + [k.value for k in n.keywords]:
                for m in ast.walk(a):
                    if isinstance(m, ast.Name) and m.id in MONEY_ARGS:
                        hits.add(f"{name}({m.id})")
                    if isinstance(m, ast.Call) and dotted(m.func) == "llm_client":
                        hits.add(f"{name}(llm_client)")
    return hits


def _kw(call, name):
    return next((k.value for k in call.keywords if k.arg == name), None)


def _priced(call: ast.Call) -> bool:
    if dotted(call.func).split(".")[-1] == "paid_button":
        tag = call.args[2] if len(call.args) > 2 else _kw(call, "tag")
        return tag is not None and not (isinstance(tag, ast.Constant) and not tag.value)
    label = call.args[0] if call.args else _kw(call, "label")
    if call.args and dotted(call.func).split(".")[-1] in CONFIRM_FUNCS and len(call.args) > 2:
        label = call.args[2]                                    # confirm_all(key, ids, label, …)
    for m in ast.walk(label) if label is not None else []:
        if isinstance(m, ast.Call) and PRICE_RE.search(dotted(m.func)):
            return True
        if isinstance(m, ast.Constant) and isinstance(m.value, str) and re.search(r"USD|\$|credit", m.value):
            return True
        if isinstance(m, ast.Name) and PRICE_RE.search(m.id):
            return True
    return False


def _key(call: ast.Call) -> str:
    k = _kw(call, "key")
    if k is None and dotted(call.func).split(".")[-1] in CONFIRM_FUNCS + ("paid_button",) and call.args:
        k = call.args[1] if dotted(call.func).split(".")[-1] == "paid_button" and len(call.args) > 1 else call.args[0]
    return ast.unparse(k) if k is not None else "?"


def scan(root: str = DASH) -> list:
    """[{file, line, key, calls, priced, confirmed, ask_false}] cho mọi `if <nút>:` có thân gọi đường tốn tiền."""
    out = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(dirpath, f)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            for node in ast.walk(tree):
                if not isinstance(node, ast.If):
                    continue
                buttons = [c for c in ast.walk(node.test) if isinstance(c, ast.Call) and _is_button(c)]
                if not buttons:
                    continue
                calls = _paid_calls(node.body)
                if not calls:
                    continue
                b = buttons[0]
                last = dotted(b.func).split(".")[-1]
                ask = _kw(b, "ask")
                out.append({"file": rel, "line": node.lineno, "key": _key(b), "calls": calls, "priced": _priced(b),
                            "confirmed": last in CONFIRM_FUNCS,
                            "ask_false": last == "paid_button" and isinstance(ask, ast.Constant) and ask.value is False})
    return out


class PaidButtonScan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = scan()

    def test_scanner_finds_paid_buttons(self):
        self.assertGreater(len(self.rows), 30, "máy quét không thấy nút tốn tiền nào — quét hỏng")

    def test_every_paid_button_priced_and_confirmed_or_excepted(self):
        bad = [f"{r['file']}:{r['line']} {r['key']} {sorted(r['calls'])[:2]} (giá={r['priced']}, xác nhận={r['confirmed']})"
               for r in self.rows if not (r["priced"] and r["confirmed"]) and not EXCEPTIONS.get(f"{r['file']}::{r['key']}", "").strip()]
        self.assertEqual(bad, [], "nút tốn tiền thiếu giá / xác nhận (thêm paid_button, hoặc ghi ngoại lệ kèm lý do)")

    def test_exceptions_not_stale(self):
        live = {f"{r['file']}::{r['key']}" for r in self.rows}
        self.assertEqual(sorted(set(EXCEPTIONS) - live), [], "ngoại lệ không còn khớp nút nào — xóa khỏi EXCEPTIONS")

    def test_m80_spots_priced_and_confirmed(self):
        for file, frag in M80_SPOTS:
            rows = [r for r in self.rows if r["file"] == file and frag in r["key"]]
            self.assertTrue(rows, f"không thấy nút {frag} ở {file}")
            for r in rows:
                self.assertTrue(r["priced"] and r["confirmed"], f"{file}:{r['line']} {r['key']}: thiếu giá hoặc xác nhận")
                self.assertNotIn(f"{file}::{r['key']}", EXCEPTIONS)

    def test_ask_false_only_for_typed_chat(self):
        for r in self.rows:
            if r["ask_false"]:
                self.assertTrue(any(r["file"] == f and frag in r["key"] for f, frag in ASK_FALSE_OK),
                                f"{r['file']}:{r['line']} paid_button(ask=False) ngoài chỗ cho phép")

    def test_approve_and_send_goes_through_undo(self):
        """'✔ Duyệt storyboard → gửi video' / '✔ Đã duyệt — tiếp tục': thân nút hẹn qua hàng chờ hoàn tác, không gọi autopilot.resume."""
        for file, frag in [("design/screens/storyboard_cards.py", "board_ok_"), ("steps/step2.py", "board_ok_"),
                           ("steps/step1_run.py", "ap_resume_")]:
            for r in (r for r in self.rows if r["file"] == file and frag in r["key"]):
                self.assertNotIn("autopilot.resume", r["calls"], f"{file}:{r['line']}")
                self.assertTrue({"P.schedule_resume", "paid_confirm.schedule_resume"} & r["calls"], f"{file}:{r['line']}")


class ChatNoSendOnEnter(unittest.TestCase):
    def test_chat_send_only_inside_a_confirmed_button(self):
        """Enter chỉ giữ chữ: mọi Chat.send ở step1_box nằm trong thân một nút có giá + xác nhận (paid_button)."""
        path = os.path.join(DASH, "steps", "step1_box.py")
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        parent = {}
        for n in ast.walk(tree):
            for c in ast.iter_child_nodes(n):
                parent[c] = n
        sends = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and dotted(n.func) == "Chat.send"]
        self.assertTrue(sends)
        for s in sends:
            n, ok = s, False
            while n in parent:
                child, n = n, parent[n]
                if isinstance(n, ast.If) and child in n.body and any(
                        isinstance(c, ast.Call) and dotted(c.func).split(".")[-1] == "paid_button" for c in ast.walk(n.test)):
                    ok = True
                    break
            self.assertTrue(ok, f"step1_box.py:{s.lineno}: Chat.send chạy không qua nút 'Gửi · ≈ X USD'")


class UndoQueue(unittest.TestCase):
    def setUp(self):
        from dashboard import paid_confirm as P
        self.P = P
        self.ss = {}

    def test_nothing_due_before_deadline_then_once(self):
        uid = self.P.schedule(self.ss, "resume", 7, "Duyệt storyboard", " · ≈ 1.00 USD", now=1000.0)
        self.assertEqual(self.P.take_due(self.ss, now=1000.0 + self.P.UNDO_SEC - 1), [])
        self.assertTrue(self.P.waiting(self.ss, "resume", 7))
        due = self.P.take_due(self.ss, now=1000.0 + self.P.UNDO_SEC)
        self.assertEqual([d["id"] for d in due], [uid])
        self.assertEqual(self.P.take_due(self.ss, now=99999.0), [], "một mục chỉ chạy một lần")

    def test_undo_removes(self):
        uid = self.P.schedule(self.ss, "resume", 7, "x", now=1000.0)
        self.assertTrue(self.P.cancel(self.ss, uid))
        self.assertEqual(self.P.take_due(self.ss, now=99999.0), [])

    def test_double_click_schedules_once(self):
        a = self.P.schedule(self.ss, "resume", 7, "x", now=1000.0)
        b = self.P.schedule(self.ss, "resume", 7, "x", now=1005.0)
        self.assertEqual(a, b)
        self.assertEqual(len(self.P.pending(self.ss)), 1)

    def test_send_now(self):
        uid = self.P.schedule(self.ss, "resume", 7, "x", now=1000.0)
        self.assertEqual([d["id"] for d in self.P.take_due(self.ss, now=1001.0, force=uid)], [uid])

    def _run(self, gate_now, fp_now, it):
        from core import autopilot, storyboard_gate
        p = mock.Mock(actor="ep")
        started = []
        with mock.patch.object(autopilot, "get_gates", return_value={"waiting_for": gate_now}), \
                mock.patch.object(storyboard_gate, "fingerprint", return_value=fp_now), \
                mock.patch.object(autopilot, "resume") as resume:
            why = self.P.run_item(p, it, lambda pid, user: started.append((pid, user)))
        return why, resume, started

    def test_run_resume_when_unchanged(self):
        it = {"action": "resume", "pid": 7, "waiting_for": "storyboard", "fp": [1, 2], "user": {"email": "a"}}
        why, resume, started = self._run("storyboard", [1, 2], it)
        self.assertEqual(why, "")
        resume.assert_called_once()
        self.assertEqual(started, [(7, {"email": "a"})])

    def test_no_send_when_storyboard_changed(self):
        it = {"action": "resume", "pid": 7, "waiting_for": "storyboard", "fp": [1, 2]}
        why, resume, started = self._run("storyboard", [1, 3], it)
        self.assertIn("Không gửi", why)
        resume.assert_not_called()
        self.assertEqual(started, [])

    def test_no_send_when_gate_changed(self):
        it = {"action": "resume", "pid": 7, "waiting_for": "storyboard", "fp": None}
        why, resume, started = self._run(None, [], it)
        self.assertIn("Không gửi", why)
        resume.assert_not_called()


class Flag(unittest.TestCase):
    def test_flag_declared_default_on_free(self):
        from core import features
        meta = features.FEATURES["safe_paid_buttons"]
        self.assertTrue(meta.get("default_on"))
        self.assertFalse(meta.get("costs"))
        with mock.patch.dict(os.environ, {"FEATURE_SAFE_PAID_BUTTONS": ""}):
            self.assertEqual(features.default_state("safe_paid_buttons"), "on")


def _app_paid():
    import streamlit as st
    from dashboard import paid_confirm as P
    if P.paid_button("🎬 Dựng", "t_paid", " · Claude ≈ 0.10 USD (ước tính)"):
        st.session_state["ran"] = st.session_state.get("ran", 0) + 1
    st.write(f"ran={st.session_state.get('ran', 0)}")


class PaidButtonApp(unittest.TestCase):
    def _texts(self, at):
        return " ".join(m.value for m in at.markdown)

    def test_two_clicks_needed_when_on(self):
        from streamlit.testing.v1 import AppTest
        with mock.patch("dashboard.paid_confirm.enabled", return_value=True):
            at = AppTest.from_function(_app_paid).run()
            self.assertIn("USD", at.button(key="t_paid").label)
            at.button(key="t_paid").click().run()
            self.assertIn("ran=0", self._texts(at))
            at.button(key="t_paid_yes").click().run()
            self.assertIn("ran=1", self._texts(at))

    def test_no_cancels(self):
        from streamlit.testing.v1 import AppTest
        with mock.patch("dashboard.paid_confirm.enabled", return_value=True):
            at = AppTest.from_function(_app_paid).run()
            at.button(key="t_paid").click().run()
            at.button(key="t_paid_no").click().run()
            self.assertIn("ran=0", self._texts(at))
            self.assertEqual([b for b in at.button if b.key == "t_paid_yes"], [])

    def test_flag_off_one_click(self):
        from streamlit.testing.v1 import AppTest
        with mock.patch("dashboard.paid_confirm.enabled", return_value=False):
            at = AppTest.from_function(_app_paid).run()
            at.button(key="t_paid").click().run()
            self.assertIn("ran=1", self._texts(at))


if __name__ == "__main__":
    unittest.main()
