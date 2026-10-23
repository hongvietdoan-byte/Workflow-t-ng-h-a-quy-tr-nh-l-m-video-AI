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
              "autoqc.clear_video_error", "Chat.send", "P.schedule_resume", "paid_confirm.schedule_resume", "autopilot.start",
              "C.llm", "llm_client", "p.retry", "p.reject", "p.reopen_approved", "p.restart_job",
              "regen.regenerate_video", "voice.generate", "voice.preview", "music.submit_drafts",
              "end_frames.redo"}   # rà M8.0c: vẽ (lại) khung cuối = gen ảnh trả phí
# Đuôi tên lời gọi tốn tiền bất kể gốc: nhả việc đã xếp hàng, khởi chạy autopilot nền.
PAID_SUFFIXES = (".submit_pending", "autopilot_manager().start")
MONEY_ARGS = {"client", "llm", "runner"}
CONFIRM_FUNCS = ("paid_button", "paid_batch_button", "confirm_all", "_confirm_all_primary")
PRICE_RE = re.compile(r"tag|price|estimate|usd|credit", re.I)

# Ngoại lệ: "<file>::<key>" → lý do. Mục không còn khớp nút nào → test đỏ (danh sách không được cũ).
# M8.0b (23/10): ~35 nút "chỉ có giá" (_PRICE_ONLY cũ) đã chuyển sang paid_button (giá + xác nhận một lần) khi cờ BẬT — không còn ngoại lệ
# "chỉ giá". Còn lại chỉ nút 0 USD hoặc nút có sẵn cách xác nhận riêng.
_FREE = "0 USD: chỉ hỏi trạng thái / tải về / hủy / nối lại task đã trả tiền (không gửi việc mới)"
EXCEPTIONS = {
    "admin.py::'meshy_go'": "ô tick 'Tôi đồng ý trả ≈ N credit' bắt buộc trước khi nút bật (xác nhận + giá có sẵn)",
    "admin.py::'meshy_refresh'": _FREE,
    "send_preview_ui.py::f'sendpv_btn_{jid}'": ("0 USD: 'Dựng gói (0 USD)' chỉ DỰNG gói xem trước bằng đường của nút Gen — không gửi, không gọi "
                                                "Claude / nhà cung cấp, không ghi gì (send_preview.video_package)"),
    "steps/step4.py::f'vc_{jid}'": _FREE, "steps/step4.py::f'vrl_{jid}'": _FREE, "steps/step4.py::f'ms_refresh_{pid}'": _FREE,
    "steps/step4.py::f'quality_refresh_{pid}'": _FREE,
    "quality_ui.py::f'qfinal_new_{scene_id}'": "giá + xác nhận có sẵn: nhãn/câu hỏi do new_final_texts dựng (chứa _usd_text) + confirm_all",
    "quality_ui.py::f'qfinal_allnew_{pid}'": "giá + xác nhận có sẵn: nhãn/câu hỏi do new_final_texts dựng (chứa _usd_text) + confirm_all",
    "design/screens/money_days.py::'md_new_go'": "0 USD: mở đợt ngân sách mới; `llm` ở đây là trần USD (số), không phải client",
    "steps/step5.py::f'sub_burn_{pid}'":"0 USD: in phụ đề với cues đã dịch truyền vào (delivery.subtitle_layer không gọi localize khi có cues)",
    "steps/step2.py::f'dd_{jid}'": "0 USD: p.reject(..., respawn=False) chỉ xóa ảnh vào thùng rác, không tạo job mới",
    "design/screens/storyboard_cards.py::f'dd_{jid}'": "0 USD: p.reject(..., respawn=False) chỉ xóa ảnh vào thùng rác, không tạo job mới",
}
# M8.0b: các nút trước chỉ có giá — nay PHẢI là paid_button (giá + xác nhận), không được quay lại EXCEPTIONS.
M80B_CONVERTED = [
    ("admin.py", "ls_judge"), ("admin.py", "ls_mine"), ("admin.py", "ls_research"), ("admin.py", "kb_distill_"), ("admin.py", "va_go"),
    ("admin.py", "meshy_rig"), ("end_frame_ui.py", "efoff_"), ("quality_ui.py", "f'qfinal_{scene_id}'"),
    ("steps/step1_characters.py", "outfit_set_"), ("steps/step1_characters.py", "_ai'"), ("steps/step1_characters.py", "bcheck_"),
    ("steps/step1_characters.py", "cast_"), ("steps/step1_checklist.py", "asset_chk_"), ("steps/step1_director.py", "dlg_ai_"),
    ("steps/step1_director.py", "replan_"), ("steps/step1_director.py", "llm_dir_"), ("steps/step1_idea.py", "idea_redo_d_"),
    ("steps/step1_intake.py", "ci_style_"), ("steps/step1_prep.py", "wb_run_"), ("steps/step1_v2.py", "script-cta_"),
    ("steps/step2.py", "gen_img_"), ("steps/step2.py", "setqc_"), ("steps/step3.py", "llm_mot_"), ("steps/step3.py", "lint_"),
    ("steps/step4.py", "btn_bad_retry"), ("steps/step4.py", "clipqc_"), ("steps/step4.py", "seqlogic_"), ("steps/step4.py", "vr_rej_"),
    ("steps/step4.py", "gen_vid_"), ("steps/step4.py", "stale_requeue_"), ("steps/step5.py", "deliver_"), ("steps/step5.py", "mbrief_ai_"),
    ("steps/step5.py", "sub_make_"), ("steps/step5.py", "sfx_ai_go_"), ("steps/step5.py", "editor_review_")]
# 6 chỗ thiếu giá + xác nhận (kế hoạch dòng 21) + nút duyệt gửi tiền (mục 8.4): phải có GIÁ + XÁC NHẬN, không được là ngoại lệ.
M80_SPOTS = [("steps/step1_prep.py", "pv_plan_"), ("steps/step1_prep.py", "pv_review_"), ("change_review_ui.py", "_rerun_"),
             ("steps/step2.py", "autoqc_retry_"), ("steps/step4.py", "vqc_retry_"),
             ("design/screens/storyboard_cards.py", "board_ok_"), ("steps/step2.py", "board_ok_"), ("steps/step1_run.py", "ap_resume_")]
# M8.0c: toàn bộ nút thủ công còn lại có thể tạo job/chi phí. `dd_` được quét riêng và
# ngoại lệ chỉ hợp lệ khi chứng minh `respawn=False` (xóa ảnh vào thùng rác, 0 USD).
M80C_SPOTS = [
    ("steps/step2.py", "reject_all"), ("steps/step2.py", "f'r_{jid}'"), ("steps/step2.py", "f'retry_{jid}'"),
    ("steps/step2.py", "f'stale_{jid}'"), ("steps/step2.py", "f'rs_{jid}'"), ("steps/step2.py", "f'dr_{jid}'"),
    ("steps/step2.py", "f'dretry_{jid}'"), ("steps/step2.py", "f'drs_{jid}'"), ("steps/step2.py", "f'reopen_{jid}'"),
    ("design/screens/storyboard_cards.py", "f'r_{jid}'"), ("design/screens/storyboard_cards.py", "f'dretry_{jid}'"),
    ("design/screens/storyboard_cards.py", "f'reopen_{jid}'"),
    ("design/screens/storyboard_cards.py", "f'rs_{jid}'"),
    ("steps/step4.py", "btn_bad_retry"), ("steps/step4.py", "stale_requeue_"), ("steps/step4.py", "f'vregen_{jid}'"),
    ("steps/step4.py", "f'vr_rej_{jid}'"), ("steps/step4.py", "f'vrs_{jid}'"),
    ("steps/step3.py", "tts_gen_"), ("steps/step1_characters.py", "vprev_"), ("steps/step5.py", "mdraft_"),
    ("end_frame_ui.py", "efr_"),                     # rà M8.0c: nút vẽ khung cuối còn sót (chỉ có giá, chưa xác nhận)
]
# M8.0b E2: nút "Duyệt tất cả" (duyệt hết) — (file, khóa, loại approve_preview.KINDS)
APPROVE_SITES = [("steps/step2.py", "approve_all", "images"), ("design/screens/storyboard_cards.py", "approve_all", "images"),
                 ("steps/step3.py", "btn_ok_all", "motion"), ("steps/step4.py", "vid_ok_all_", "clips")]
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
    last = name.split(".")[-1]
    return last in ("button", "form_submit_button", "cta") or last in CONFIRM_FUNCS


def _paid_calls(body) -> set:
    """Lời gọi tốn tiền trong thân nút: tên ở PAID_CALLS / PAID_SUFFIXES, hoặc tên client/llm/runner xuất hiện ở BẤT KỲ đâu trong lời
    gọi — kể cả làm gốc (`runner.submit_images(pid)`) — và `llm_client()`."""
    hits = set()
    for stmt in body:
        for n in ast.walk(stmt):
            if not isinstance(n, ast.Call):
                continue
            name = dotted(n.func)
            if name == "p.reject" and any(k.arg == "respawn" and isinstance(k.value, ast.Constant) and k.value.value is False
                                           for k in n.keywords):
                hits.add("p.reject(respawn=False)")
            elif name in PAID_CALLS or name.endswith(PAID_SUFFIXES):
                hits.add(name)
            for a in [n.func] + list(n.args) + [k.value for k in n.keywords]:
                for m in ast.walk(a):
                    if isinstance(m, ast.Name) and m.id in MONEY_ARGS:
                        hits.add(f"{name}({m.id})")
                    if isinstance(m, ast.Call) and dotted(m.func) in ("llm_client", "C.llm"):
                        hits.add(f"{name}({dotted(m.func)})")
    return hits


def _kw(call, name):
    return next((k.value for k in call.keywords if k.arg == name), None)


def _priced(call: ast.Call) -> bool:
    if dotted(call.func).split(".")[-1] in ("paid_button", "paid_batch_button"):
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
    name = dotted(call.func).split(".")[-1]
    if k is None and name in CONFIRM_FUNCS + ("paid_button",) and call.args:
        k = call.args[1] if name in ("paid_button", "paid_batch_button") and len(call.args) > 1 else call.args[0]
    return ast.unparse(k) if k is not None else "?"


def _scopes(tree):
    return [tree] + [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


def _scope_of(tree, node):
    """Hàm trong cùng chứa `node` (module nếu không có)."""
    cache = getattr(tree, "_scope_cache", None)
    if cache is None:
        cache = {}
        for sc in _scopes(tree):                       # duyệt từ ngoài vào trong → hàm trong cùng ghi đè sau
            for n in ast.walk(sc):
                cache[id(n)] = sc
        tree._scope_cache = cache
    return cache.get(id(node), tree)


def _buttons_in(expr) -> list:
    return [c for c in ast.walk(expr) if isinstance(c, ast.Call) and _is_button(c)]


def _assigned_buttons(tree) -> dict:
    """`go = st.button(...)` → {(id phạm vi, "go"): [lời gọi nút]} để `if go:` được tính là nút. M8.0b: cả `go = ok and st.button(...)`,
    `go = confirm_all(...) if x else st.button(...)` và nhiều lần gán cùng tên (mọi nhánh đều phải có giá + xác nhận)."""
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            calls = _buttons_in(n.value)
            if not calls:
                continue
            for t in n.targets:
                if isinstance(t, ast.Name):
                    out.setdefault((id(_scope_of(tree, n)), t.id), []).extend(calls)
    return out


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
            assigned = _assigned_buttons(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.If):
                    continue
                buttons = _buttons_in(node.test)
                for m in ast.walk(node.test):
                    if isinstance(m, ast.Name):
                        buttons += assigned.get((id(_scope_of(tree, node)), m.id), [])
                if not buttons:
                    continue
                calls = _paid_calls(node.body)
                if not calls:
                    continue
                lasts = [dotted(b.func).split(".")[-1] for b in buttons]
                asks = [(_kw(b, "ask"), last) for b, last in zip(buttons, lasts)]
                frees = [(_kw(b, "free"), last) for b, last in zip(buttons, lasts)]
                out.append({"file": rel, "line": node.lineno, "key": _key(buttons[0]), "calls": calls,
                            "priced": all(_priced(b) for b in buttons),
                            "confirmed": all(last in CONFIRM_FUNCS for last in lasts),
                            "ask_false": any(last == "paid_button" and isinstance(a, ast.Constant) and a.value is False for a, last in asks),
                            "free_const": any(last == "paid_button" and isinstance(f, ast.Constant) and f.value for f, last in frees)})
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

    def test_m80b_price_only_buttons_now_confirmed(self):
        """M8.0b: mọi nút trước chỉ có giá (danh sách _PRICE_ONLY cũ) nay có giá + xác nhận một lần, không nằm trong ngoại lệ."""
        for file, frag in M80B_CONVERTED:
            rows = [r for r in self.rows if r["file"] == file and frag in r["key"]]
            self.assertTrue(rows, f"không thấy nút {frag} ở {file}")
            for r in rows:
                self.assertTrue(r["priced"] and r["confirmed"], f"{file}:{r['line']} {r['key']}: thiếu giá hoặc xác nhận")
                self.assertNotIn(f"{file}::{r['key']}", EXCEPTIONS)

    def test_m80c_remaining_paid_buttons_are_priced_and_confirmed(self):
        """M8.0c: mọi đường retry/reject-gen/reopen/restart/TTS/nhạc còn lại phải qua xác nhận có giá."""
        for file, frag in M80C_SPOTS:
            rows = [r for r in self.rows if r["file"] == file and frag in r["key"]]
            self.assertTrue(rows, f"không thấy nút M8.0c {frag} ở {file}")
            for r in rows:
                exc = EXCEPTIONS.get(f"{file}::{r['key']}", "").strip()
                self.assertTrue((r["priced"] and r["confirmed"]) or exc,
                                f"{file}:{r['line']} {r['key']}: thiếu giá/xác nhận")

    def test_m80c_delete_buttons_are_proven_free(self):
        """dd_ chỉ xóa khỏi hàng chờ; mọi đường p.reject có gen lại đã được test riêng."""
        keys = [("steps/step2.py", "f'dd_{jid}'"), ("design/screens/storyboard_cards.py", "f'dd_{jid}'")]
        for file, key in keys:
            rows = [r for r in self.rows if r["file"] == file and r["key"] == key]
            self.assertTrue(rows, f"không thấy nút xóa {key} ở {file}")
            for row in rows:
                self.assertIn("p.reject(respawn=False)", row["calls"], f"{file}:{row['line']} không chứng minh xóa 0 USD")
                self.assertIn(f"{file}::{key}", EXCEPTIONS)

    def test_free_never_constant(self):
        """`paid_button(..., free=…)` chỉ được là ĐIỀU KIỆN lần này 0 USD (vd phụ đề không dịch) — `free=True` cố định = bỏ xác nhận."""
        self.assertEqual([f"{r['file']}:{r['line']}" for r in self.rows if r["free_const"]], [])

    def test_approve_all_sites_preview_when_flag_on(self):
        """M8.0b E2: mọi nút "Duyệt tất cả" (duyệt hết) có đường cờ BẬT qua approve_preview.approve_all_box (xem trước + giá + HOLD +
        hẹn 30 s hoàn tác) trước confirm_all cũ."""
        for file, key, kind in APPROVE_SITES:
            with open(os.path.join(DASH, file), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            boxes = [ast.unparse(c) for c in ast.walk(tree) if isinstance(c, ast.Call) and dotted(c.func).endswith("approve_all_box")]
            self.assertTrue(any(key in b and repr(kind) in b for b in boxes), f"{file}: thiếu approve_all_box({kind!r}, {key})")

    def test_pilot_release_goes_through_undo(self):
        """M8.0b: '✔ Mẫu thử ổn — gen phần còn lại' cờ BẬT = giá + xác nhận + hẹn 30 s (P.schedule 'pilot_release')."""
        src = open(os.path.join(DASH, "steps", "step2.py"), encoding="utf-8").read()
        frag = src[src.index("def pilot_panel"):src.index("def animatic_box")]
        self.assertIn("paid_button(", frag)
        self.assertIn('"pilot_release"', frag)

    def test_approve_and_send_goes_through_undo(self):
        """'✔ Duyệt storyboard → gửi video' / '✔ Đã duyệt — tiếp tục': thân nút hẹn qua hàng chờ hoàn tác, không gọi autopilot.resume."""
        for file, frag in [("design/screens/storyboard_cards.py", "board_ok_"), ("steps/step2.py", "board_ok_"),
                           ("steps/step1_run.py", "ap_resume_")]:
            for r in (r for r in self.rows if r["file"] == file and frag in r["key"]):
                self.assertNotIn("autopilot.resume", r["calls"], f"{file}:{r['line']}")
                self.assertTrue({"P.schedule_resume", "paid_confirm.schedule_resume"} & r["calls"], f"{file}:{r['line']}")


class ScannerCatchesPatterns(unittest.TestCase):
    """Rà kỹ M8.0: máy quét cũ bắt 0/5 mẫu dưới — mỗi mẫu phải ra đúng một hàng."""
    SAMPLES = {
        "a_root.py": "def f(st, runner, pid):\n    if st.button('Gen', key='a'):\n        runner.submit_images(pid)\n",
        "b_assigned.py": ("def f(st, previz, p, pid, client):\n    go = st.button('Dựng', key='b')\n    if go:\n"
                          "        previz.plan_layouts(p, pid, client)\n"),
        "c_form.py": "def f(st, runner, pid):\n    if st.form_submit_button('Gửi'):\n        runner.submit_pending(pid)\n",
        "d_manager.py": "def f(st, C, pid):\n    if st.button('Chạy', key='d'):\n        C.autopilot_manager(C.DB, C.DATA).start(pid)\n",
        "e_llm.py": "def f(st, llm_io, C, p, pid):\n    if st.button('Hỏi', key='e'):\n        llm_io.x(p, pid, C.llm(pid))\n",
        # M8.0b: gán qua and / if-else (nút "↻ Chỉ hỏi lại N cảnh lỗi", nút Director khi Bible khóa) — máy quét cũ bỏ sót
        "f_boolop.py": "def f(st, runner, pid, ok):\n    go = ok and st.button('Gen', key='f')\n    if go:\n        runner.submit_images(pid)\n",
        "g_ifexp.py": ("def f(st, runner, pid, x, confirm_all):\n    go = confirm_all('k', [1], 'L · ≈ 1 USD', 'Q') if x else st.button('Gen', key='g')\n"
                       "    if go:\n        runner.submit_pending(pid)\n"),
    }

    def test_scanner_reports_all_five_patterns(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            for name, src in self.SAMPLES.items():
                with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
                    fh.write(src)
            rows = scan(d)
        self.assertEqual(sorted(r["file"] for r in rows), sorted(self.SAMPLES))
        g = next(r for r in rows if r["file"] == "g_ifexp.py")
        self.assertFalse(g["confirmed"], "một nhánh là st.button trần → chưa xác nhận dù nhánh kia là confirm_all")


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

    def test_send_now_rechecks_and_runs_once(self):
        ss = {}
        uid = self.P.schedule(ss, "resume", 7, "Duyệt storyboard", now=1000.0,
                              waiting_for="storyboard", fp=[1, 2], user={"email": "a"})
        (queued,) = self.P.take_due(ss, now=1001.0, force=uid)
        why, resume, started = self._run("khac", [1, 2], queued)
        self.assertIn("Không gửi", why)
        resume.assert_not_called()
        self.assertEqual(started, [])
        self.assertEqual(self.P.take_due(ss, now=99999.0, force=uid), [])

        ss = {}
        uid = self.P.schedule(ss, "resume", 7, "Duyệt storyboard", now=1000.0,
                              waiting_for="storyboard", fp=[1, 2], user={"email": "a"})
        (queued,) = self.P.take_due(ss, now=1001.0, force=uid)
        why, resume, started = self._run("storyboard", [1, 2], queued)
        self.assertEqual(why, "")
        resume.assert_called_once()
        self.assertEqual(started, [(7, {"email": "a"})])
        self.assertEqual(self.P.take_due(ss, now=99999.0, force=uid), [])

        # Gửi clip ngay vẫn so lại hàng chờ và tập HOLD tại thời điểm chạy.
        from dashboard import approve_preview as A
        ss = {}
        uid = self.P.schedule(ss, "approve_clips", 7, "Duyệt clip", now=1000.0,
                              ids=[21], ok=[21], kind="clips")
        (queued,) = self.P.take_due(ss, now=1001.0, force=uid)
        clip = mock.Mock(actor="ep")
        with mock.patch.object(A, "pending_ids", return_value=[21]), \
                mock.patch.object(A, "rows", return_value=[{"id": 21, "scene_id": 11, "hold": "clip đang cũ"}]), \
                mock.patch("dashboard.quality_ui.approve_clip") as approve:
            why = self.P.run_item(clip, queued, lambda pid, user: None)
        self.assertIn("Không duyệt", why)
        approve.assert_not_called()

        # Mở lô ngay vẫn kiểm tra trạng thái mẫu hiện tại trước khi giải phóng các cảnh còn lại.
        ss = {}
        uid = self.P.schedule(ss, "pilot_release", 7, "Gen phần còn lại", now=1000.0, scenes=[1])
        (queued,) = self.P.take_due(ss, now=1001.0, force=uid)
        pilot_project = mock.Mock(actor="ep")
        with mock.patch("core.pilot.get", return_value={"enabled": False, "released": False, "scenes": [1]}), \
                mock.patch("core.pilot.release") as release:
            why = self.P.run_item(pilot_project, queued, lambda pid, user: None)
        self.assertIn("Không mở gen cả lô", why)
        release.assert_not_called()

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


    def test_start_error_says_not_started(self):
        """Rà kỹ M8.0 #4: khởi chạy nền lỗi → nói 'chưa khởi chạy', không báo đã gửi."""
        from core import autopilot, storyboard_gate
        it = {"action": "resume", "pid": 7, "waiting_for": "storyboard", "fp": None}

        def boom(pid, user):
            raise RuntimeError("hết slot")
        with mock.patch.object(autopilot, "get_gates", return_value={"waiting_for": "storyboard"}), \
                mock.patch.object(storyboard_gate, "fingerprint", return_value=[]), mock.patch.object(autopilot, "resume"):
            why = self.P.run_item(mock.Mock(actor="ep"), it, boom)
            already = self.P.run_item(mock.Mock(actor="ep"), it, lambda pid, user: False)
        self.assertIn("chưa khởi chạy", why)
        self.assertIn("đang chạy sẵn", already)

    def test_due_item_closes_its_connection(self):
        """Rà kỹ M8.0 #7: mỗi lần tới hạn mở một kết nối CSDL → phải đóng."""
        src = open(os.path.join(DASH, "paid_confirm.py"), encoding="utf-8").read()
        frag = src[src.index("def _undo_fragment"):]
        self.assertIn("conn.close()", frag)
        self.assertIn("finally:", frag)


class ChatBoxFixes(unittest.TestCase):
    def test_cancel_clears_both_ask_and_held_message(self):
        """Rà kỹ M8.0 #6: 'hủy' bỏ cả tin hỏi lại lẫn tin chờ gửi (trước: ngắt mạch, kẹt chatsend)."""
        from dashboard.steps import step1_box as B
        k = B._keys(5)
        ss = {k["chatask"]: "a", k["chatsend"]: "b"}
        with mock.patch.object(B.st, "session_state", ss), mock.patch("core.script_chat.append"):
            B._command(mock.Mock(), 5, "cancel")
        self.assertNotIn(k["chatask"], ss)
        self.assertNotIn(k["chatsend"], ss)

    def test_chat_branch_checks_edit_right_before_writing(self):
        """Rà kỹ M8.0 #5: nhánh kind=='chat' kiểm access.need_edit TRƯỚC Chat.append (người 'Chỉ xem' không ghi được tin)."""
        src = open(os.path.join(DASH, "steps", "step1_box.py"), encoding="utf-8").read()
        branch = src[src.index('elif kind == "chat":'):]
        branch = branch[:branch.index("else:")]
        self.assertIn("access.need_edit", branch)
        self.assertLess(branch.index("access.need_edit"), branch.index("Chat.append"))


class Flag(unittest.TestCase):
    def test_stable_preset_keeps_safety_flag_on(self):
        """Rà kỹ M8.0 #3: preset Ổn định giữ cờ an toàn BẬT; cờ khác không đổi (đã thử thật / khóa → bật, còn lại tắt)."""
        from core import features as F
        s = {"preset": "stable", "flags": {}, "modes": {}}
        self.assertEqual(F._state("safe_paid_buttons", s), "on")
        for name, meta in F.FEATURES.items():
            if name in F.REMOVED or name == "safe_paid_buttons":
                continue
            want = "on" if (F.locked(name) or meta["verified"] or meta.get("safety")) else "off"
            self.assertEqual(F._state(name, s), want, name)
        self.assertEqual([n for n, m in F.FEATURES.items() if m.get("safety")], ["safe_paid_buttons"])

    def test_flag_declared_default_on_free(self):
        from core import features
        meta = features.FEATURES["safe_paid_buttons"]
        self.assertTrue(meta.get("default_on"))
        self.assertFalse(meta.get("costs"))
        with mock.patch.object(os, "environ", {"FEATURE_SAFE_PAID_BUTTONS": ""}):
            self.assertEqual(features.default_state("safe_paid_buttons"), "on")


def _app_paid():
    import streamlit as st
    from dashboard import paid_confirm as P
    if P.paid_button("🎬 Dựng", "t_paid", " · Claude ≈ 0.10 USD (ước tính)"):
        st.session_state["ran"] = st.session_state.get("ran", 0) + 1
    st.write(f"ran={st.session_state.get('ran', 0)}")


def _app_paid_batch():
    import streamlit as st
    from unittest import mock
    from dashboard import paid_batch_preview as B
    from dashboard import paid_confirm as P
    p = mock.Mock(actor="ep")
    B.paid_batch_button("↻ Gửi lại ảnh lỗi (2)", key="t_batch", tag=" · ≈ 2 USD", p=p, pid=7,
                        action="retry_images", items=[11, 12], preview=["Ảnh job 11", "Ảnh job 12"])
    st.write(f"pending={len(P.pending(st.session_state, 7))}")
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


class PaidBatchButtonApp(unittest.TestCase):
    def _texts(self, at):
        return " ".join(m.value for m in [*at.markdown, *at.caption])

    def _patches(self):
        from dashboard import paid_confirm
        return (mock.patch.object(paid_confirm, "enabled", return_value=True),
                mock.patch("dashboard.paid_batch_preview.fingerprint", return_value="same-state"),
                mock.patch("dashboard.common.access_user", return_value={}))

    def test_batch_yes_schedules_preview_and_executes_each_item_once(self):
        from streamlit.testing.v1 import AppTest
        from dashboard import paid_confirm as P
        from core import batch, access
        enabled, fingerprint, user = self._patches()
        with enabled, fingerprint, user:
            at = AppTest.from_function(_app_paid_batch).run()
            self.assertIn("USD", at.button(key="t_batch").label)
            at.button(key="t_batch").click().run()
            self.assertIn("Ảnh job 11", self._texts(at))
            self.assertIn("Ảnh job 12", self._texts(at))
            at.button(key="t_batch_yes").click().run()
            self.assertIn("pending=1", self._texts(at))
            item, = P.pending(at.session_state, 7)
            self.assertEqual(item["action"], "paid_batch")
            self.assertEqual(item["items"], [11, 12])
            self.assertEqual(item["batch_action"], "retry_images")
            self.assertGreaterEqual(item["not_before"], __import__("time").time() + P.UNDO_SEC - 1)

            due, = P.take_due(at.session_state, force=item["id"])
            pipeline = mock.Mock(actor="ep")
            with mock.patch.object(access, "need_edit"), mock.patch.object(batch, "provider_failures", return_value=[11, 12]), \
                    mock.patch("dashboard.paid_batch_preview.fingerprint", return_value="same-state"):
                self.assertEqual(P.run_item(pipeline, due, lambda *args: None), "")
                self.assertEqual(P.take_due(at.session_state), [])
            self.assertEqual(pipeline.retry.call_count, 2)
            self.assertEqual([call.args[0] for call in pipeline.retry.call_args_list], [11, 12])

    def test_batch_no_cancels_without_scheduling(self):
        from streamlit.testing.v1 import AppTest
        with self._patches()[0], self._patches()[1], self._patches()[2]:
            at = AppTest.from_function(_app_paid_batch).run()
            at.button(key="t_batch").click().run()
            at.button(key="t_batch_no").click().run()
            self.assertIn("pending=0", self._texts(at))
            self.assertIn("ran=0", self._texts(at))

    def test_batch_due_state_change_sends_nothing(self):
        from dashboard import paid_confirm as P
        from dashboard import paid_batch_preview as B
        from core import access, batch
        session = {}
        uid = P.schedule(session, "paid_batch", 7, "retry images", batch_action="retry_images", items=[11, 12],
                         params={}, fp="old-state", data_dir="fake")
        (due,) = P.take_due(session, force=uid)
        pipeline = mock.Mock(actor="ep")
        with mock.patch.object(access, "need_edit"), mock.patch.object(B, "fingerprint", return_value="new-state"), \
                mock.patch.object(batch, "provider_failures") as eligible:
            message = P.run_item(pipeline, due, lambda *args: None)
        self.assertIn("đã đổi", message)
        eligible.assert_not_called()
        pipeline.retry.assert_not_called()


class M80cReviewFixes(unittest.TestCase):
    """Rà kỹ M8.0c (phiên chính 23/10): xem trước 🎙 = đúng tập voice.generate gửi; lô khác loại không bị nuốt; nhạc không bị chặn
    nhầm khi người dùng đã rời màn."""

    def _voice_project(self):
        import json as _json
        import shutil
        import tempfile
        from core import audio_lib, music, voice
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("m80c")
        for i, (who, text) in enumerate([("KELLY", "Đi thôi."), ("KELLY", "Nhanh lên."), ("BOB", "Chờ đã.")], 1):
            sid = p.create_scene(pid, i, f"s{i}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                           (_json.dumps({"shot_no": i, "dialogue": [{"speaker": who, "text": text}]}, ensure_ascii=False), sid))
        for name in ("KELLY", "BOB"):
            p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, ?, 'x')", (pid, name))
        p.conn.commit()
        voice.set_profile(p.conn, pid, "KELLY", {"voice_id": 71, "voice_name": "Kelly"})
        data = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, data, True)
        audio = music.MockAudioProvider()
        voice.generate(p.conn, pid, audio, data, ledger=False, scene_ids=[p.conn.execute(
            "SELECT id FROM scenes WHERE project_id=? AND idx=1", (pid,)).fetchone()["id"]])
        audio_lib.refresh(audio, audio_lib.assets_dir(data, pid))
        return p, pid, data, audio

    def test_voice_preview_is_exactly_what_generate_sends(self):
        from core import audio_lib, voice
        from dashboard import paid_batch_preview as B
        p, pid, data, audio = self._voice_project()
        before = audio_lib.load(audio_lib.assets_dir(data, pid))
        sent = mock.Mock(side_effect=AssertionError("plan_only không được gọi nhà cung cấp"))
        with mock.patch.object(audio_lib, "submit_tts", sent):
            items = B.voice_items(p.conn, pid, data)
        self.assertEqual(audio_lib.load(audio_lib.assets_dir(data, pid)), before, "xem trước không được sửa thư viện âm thanh")
        self.assertEqual(len(items), 1, items)                 # BOB chưa có giọng → không gửi, không nằm trong xem trước
        self.assertIn("Nhanh lên.", items[0])
        r = voice.generate(p.conn, pid, audio, data, ledger=False, by_person=True)
        self.assertEqual(r["sent"], len(items))

    def test_voice_batch_refuses_when_list_changed(self):
        from core import access, audio_lib, music
        from dashboard import paid_batch_preview as B
        p, pid, data, audio = self._voice_project()
        it = {"pid": pid, "batch_action": "voice", "data_dir": data, "fp": "x", "items": ["câu khác"], "params": {}}
        with mock.patch.object(access, "need_edit"), mock.patch.object(B, "fingerprint", return_value="x"),                 mock.patch.object(music, "audio_provider", return_value=audio),                 mock.patch.object(audio_lib, "submit_tts") as sent:
            msg = B.run(p, it)
            self.assertIn("đã đổi", msg)
            sent.assert_not_called()
            it["items"] = B.voice_items(p.conn, pid, data)          # đúng tập đã xem → gửi đúng 1 câu
            self.assertEqual(B.run(p, it), "")
            self.assertEqual(sent.call_count, 1)

    def test_two_batch_kinds_same_project_both_scheduled(self):
        from dashboard import paid_confirm as P
        ss = {}
        a = P.schedule(ss, "paid_batch", 7, "ảnh", batch_action="retry_images", items=[1])
        b = P.schedule(ss, "paid_batch", 7, "giọng", batch_action="voice", items=["x"])
        self.assertNotEqual(a, b, "lô giọng không được bị nuốt vào lô ảnh đang chờ")
        self.assertEqual(P.schedule(ss, "paid_batch", 7, "ảnh", batch_action="retry_images", items=[1]), a)   # bấm 2 lần = 1 mục
        self.assertEqual(P.schedule(ss, "resume", 7, "r"), P.schedule(ss, "resume", 7, "r"))

    def test_music_not_refused_after_leaving_screen(self):
        from core import access, music
        from dashboard import paid_batch_preview as B
        it = {"pid": 7, "batch_action": "music", "data_dir": "d", "fp": "x", "items": ["b"],
              "params": {"prompt": "p", "length_ms": 3000, "instrumental": True, "count": 1,
                         "settings": {"prompt": "p"}, "session_keys": {"prompt": "mprompt_7"}}}
        pipe = mock.Mock(actor="ep")
        with mock.patch.object(access, "need_edit"), mock.patch.object(B, "fingerprint", return_value="x"),                 mock.patch.object(music, "audio_provider", return_value=object()),                 mock.patch.object(music, "project_dirs", return_value=("dr", "x")),                 mock.patch.object(music, "submit_drafts") as sub, mock.patch.object(B.st, "session_state", {}):
            self.assertEqual(B.run(pipe, it), "")
        sub.assert_called_once()
        with mock.patch.object(access, "need_edit"), mock.patch.object(B, "fingerprint", return_value="x"),                 mock.patch.object(music, "audio_provider", return_value=object()),                 mock.patch.object(music, "submit_drafts") as sub2, mock.patch.object(B.st, "session_state", {"mprompt_7": "khác"}):
            self.assertIn("đã đổi", B.run(pipe, it))
        sub2.assert_not_called()


if __name__ == "__main__":
    unittest.main()
