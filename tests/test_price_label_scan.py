"""S14.2 A2 — scan test (docs/KE_HOACH_NANG_CAP_DASHBOARD_2026-10-03.md mục 4 A2, mục 6c ý 4): a paid button must show its price.

Every `st.button` / `form_submit_button` / `confirm_all` (and its `on_click=` callback) in dashboard/ whose branch (the body of the `if` it sits in, or the `if` that tests the name it is
assigned to) calls a paid function (PAID below: runner/provider sends, Claude tasks, TTS/music/SFX sends, delivery…) must carry the
estimated price ON its label (regex PRICE: "≈ <số>" or "chưa có giá" — f-string fields read as 0; or a call of a price helper — cost.price_tag / llm_tag /
llm_button_tag / image_button_tag, budget.audio_tag) or in the nearest plain statement (a caption / an assignment) before it in the same block — sibling
`if …button` rows in between are skipped, so one caption can price a row of small card buttons. Otherwise it must be in ALLOWED below,
named by (file, key) with the reason. Entries that no longer match a paid button are reported too (a stale list hides nothing)."""
import ast
import fnmatch
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PRICE = re.compile(r"≈\s*\$?[\d,.]+|chưa có giá")      # rà soát A2 (e): a real figure (f-string fields read as 0), not a lone "$"
PRICE_FUNCS = {"price_tag", "llm_tag", "audio_tag", "llm_button_tag", "llm_tokens_tag", "image_button_tag", "video_button_tag",
               "video_batch_tag"}

# dotted call text (receiver.attr, or a bare name) → paid. fnmatch patterns.
PAID = ("runner.submit_pending", "*.submit_pending", "costume.make_character_set", "voice.preview", "voice.generate",
        "claude_tasks.*", "llm_runner.run_*", "voice_check.redo", "voice.fit_durations", "run_director_now", "music.submit_*", "audio_lib.submit_*", "meshy.submit_*",
        "research.run", "video_analysis.analyze", "style.analyse", "editor_review.run", "sfx_plan.propose", "subtitles.localize",
        "delivery.deliver", "regen.regenerate_video", "p.reject", "p.retry", "p.reopen_approved", "p.restart_job",
        "autopilot_manager(*).start", "idea_to_script.*", "asset_checklist.run", "lesson_judge.judge_all")
FREE = {   # matched by a PAID pattern but costs nothing (each with why)
    "claude_tasks.set_lock": "chỉ ghi Lock vào DB",
    "claude_tasks.apply_dialogue_fix": "chỉ áp câu thoại đã có",
    "claude_tasks.apply_lint": "chỉ áp bản sửa đã có",
}

# (file, key source text) → why the label carries no price
ALLOWED = {
    ("dashboard/steps/step1_characters.py", "f\"bdis_{pid}_{r['name']}_{it['index']}\""):
        "bỏ cờ kiểm Bible sai — chỉ ghi quyết định của người, 0 USD (claude_tasks.dismiss_bible_flag không gọi Claude)",
}


def _dotted(call: ast.Call) -> str:
    f = call.func
    if isinstance(f, ast.Attribute):
        return f"{ast.unparse(f.value)}.{f.attr}"
    return f.id if isinstance(f, ast.Name) else ""


def _paid_calls(nodes):
    out = []
    for nd in nodes:
        for c in ast.walk(nd):
            if not isinstance(c, ast.Call):
                continue
            name = _dotted(c)
            if name in FREE:
                continue
            if name == "voice.fit_durations" and not any(k.arg == "with_clips" for k in c.keywords):
                continue                              # chỉ kéo dài clip chưa có video — không gọi gì trả tiền
            if name == "p.reject" and any(k.arg == "respawn" and isinstance(k.value, ast.Constant) and k.value.value is False
                                          for k in c.keywords):
                continue                              # xóa vào thùng rác, không gen lại
            if any(fnmatch.fnmatchcase(name, pat) for pat in PAID):
                out.append(name)
    return out


def _is_button(n) -> bool:
    if not isinstance(n, ast.Call):
        return False
    f = n.func
    name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
    return name in ("button", "confirm_all", "form_submit_button")


def _label(call: ast.Call):
    for k in call.keywords:
        if k.arg == "label":
            return k.value
    name = call.func.attr if isinstance(call.func, ast.Attribute) else call.func.id
    i = 2 if name == "confirm_all" else 0
    return call.args[i] if len(call.args) > i else None


def _key(call: ast.Call) -> str:
    for k in call.keywords:
        if k.arg == "key":
            return ast.unparse(k.value)
    if _dotted(call).endswith("confirm_all") and call.args:
        return ast.unparse(call.args[0])
    return "?"


def _priced(expr, assigns, depth=0) -> bool:
    if expr is None:
        return False
    for n in ast.walk(expr):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and PRICE.search(n.value):
            return True
        if isinstance(n, ast.JoinedStr):              # f"≈ {usd:.2f} USD" → "≈ 0 USD"
            text = "".join(v.value if isinstance(v, ast.Constant) else "0" for v in n.values)
            if PRICE.search(text):
                return True
        if isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
            if name in PRICE_FUNCS:
                return True
        if isinstance(n, ast.Name) and depth < 2:
            for value in assigns.get(n.id, []):
                if _priced(value, assigns, depth + 1):
                    return True
    return False


def _assigns(func) -> dict:
    out = {}
    for n in ast.walk(func):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    out.setdefault(t.id, []).append(n.value)
        elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):     # label += " · ≈ … USD"
            out.setdefault(n.target.id, []).append(n.value)
    return out


def _blocks(tree):
    for n in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(n, field, None)
            if isinstance(block, list) and block and isinstance(block[0], ast.stmt):
                yield block


def _names(expr):
    return {n.id for n in ast.walk(expr) if isinstance(n, ast.Name)}


def scan(root: Path = ROOT):
    """[(file, line, key, paid calls, priced?)] for every button whose branch calls something paid."""
    found = []
    for path in sorted((root / "dashboard").rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

        def scope(line):
            inner = [f for f in funcs if f.lineno <= line <= (f.end_lineno or f.lineno)]
            return _assigns(min(inner, key=lambda f: (f.end_lineno or 0) - f.lineno)) if inner else _assigns(tree)

        for block in _blocks(tree):
            for i, st in enumerate(block):
                # the price line "right before": the nearest earlier plain statement of the block (sibling `if button` rows skipped)
                prev = next((s for s in reversed(block[:i]) if not isinstance(s, ast.If)), None)
                if isinstance(st, ast.If):
                    buttons, body = [c for c in ast.walk(st.test) if _is_button(c)], st.body
                elif isinstance(st, ast.Assign) and any(_is_button(c) for c in ast.walk(st.value)):
                    buttons = [c for c in ast.walk(st.value) if _is_button(c)]
                    targets = {t.id for t in st.targets if isinstance(t, ast.Name)}
                    body = [s for later in block[i + 1:] if isinstance(later, ast.If) and targets & _names(later.test)
                            for s in later.body]
                else:
                    continue
                if not buttons:
                    continue
                paid = _paid_calls(body)
                if not paid:
                    continue
                assigns = scope(st.lineno)
                for b in buttons:
                    ok = _priced(_label(b), assigns) or (isinstance(prev, (ast.Expr, ast.Assign)) and _priced(prev, assigns))
                    found.append((rel, b.lineno, _key(b), sorted(set(paid)), ok))
        # rà soát A2 (e): a paid call in the on_click= callback (a lambda, or a def of this file)
        defs = {f.name: f for f in funcs}
        for b in (c for c in ast.walk(tree) if _is_button(c)):
            cb = next((k.value for k in b.keywords if k.arg == "on_click"), None)
            target = cb.body if isinstance(cb, ast.Lambda) else defs.get(cb.id) if isinstance(cb, ast.Name) else None
            paid = _paid_calls([target]) if target is not None else []
            if paid:
                found.append((rel, b.lineno, _key(b), sorted(set(paid)), _priced(_label(b), scope(b.lineno))))
    return found


class PriceLabelScan(unittest.TestCase):
    def test_every_paid_button_shows_its_price(self):
        rows = scan()
        missing = [r for r in rows if not r[4] and (r[0], r[2]) not in ALLOWED]
        self.assertEqual([], [f"{f}:{ln} key={k} gọi {', '.join(c)}" for f, ln, k, c, _ in missing],
                         "Nút tốn tiền thiếu giá ước tính trên nhãn (cost.price_tag / llm_button_tag / image_button_tag / "
                         "budget.audio_tag) — hoặc thêm vào ALLOWED kèm lý do")

    def test_allowed_list_is_not_stale(self):
        rows = {(f, k) for f, _, k, _, ok in scan() if not ok}
        self.assertEqual([], [k for k in ALLOWED if k not in rows], "Mục ALLOWED không còn khớp nút nào — xóa đi")

    def test_scanner_catches_an_unpriced_paid_button(self):
        src = ("def f(p, jid):\n"
               "    if st.button('Gen lại', key='x'):\n"
               "        p.retry(jid, 'r')\n"
               "    if st.button('Gen lại' + cost.price_tag(0.1), key='y'):\n"
               "        p.retry(jid, 'r')\n"
               "    if st.button('Xóa', key='z'):\n"
               "        p.reject(jid, 'u', respawn=False)\n")
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "dashboard").mkdir()
            (Path(d) / "dashboard" / "x.py").write_text(src, encoding="utf-8")
            rows = scan(Path(d))
        self.assertEqual([("'x'", False), ("'y'", True)], [(r[2], r[4]) for r in rows])

    def test_scanner_sees_forms_callbacks_idea_to_script_and_wants_a_real_price(self):
        """Rà soát A2 (e): form_submit_button, on_click= callbacks and idea_to_script were not looked at; a lone '$' counted as a price."""
        src = ("def go(p):\n"
               "    p.retry(1, 'r')\n"
               "def f(p, jid, usd):\n"
               "    if st.form_submit_button('Viết kịch bản', key='form'):\n"
               "        idea_to_script.run(p, 1)\n"
               "    st.button('Gen lại', key='cb', on_click=go, args=(p,))\n"
               "    st.button('Gen lại', key='lam', on_click=lambda: p.retry(jid, 'r'))\n"
               "    if st.button('Gen lại (tốn $)', key='dollar'):\n"
               "        p.retry(jid, 'r')\n"
               "    if st.button(f'Gen lại · ≈ {usd:.2f} USD', key='real'):\n"
               "        p.retry(jid, 'r')\n")
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "dashboard").mkdir()
            (Path(d) / "dashboard" / "x.py").write_text(src, encoding="utf-8")
            rows = {r[2]: r[4] for r in scan(Path(d))}
        self.assertEqual({"'form'": False, "'cb'": False, "'lam'": False, "'dollar'": False, "'real'": True}, rows)


class CostButtonTags(unittest.TestCase):
    """The label helpers (core.cost): exact price → '≈ … USD (ước tính)'; unpriced → 'chưa có giá — ước tính dư ≈ …' (mục 6c)."""
    PRICING = {"currency": "USD", "per_image": {"img-a": 0.05}, "per_video_second": {}, "per_video_clip": {},
               "per_million_tokens": {"claude-x": {"input": 2.0, "output": 10.0}}}

    def test_image_tag_exact_and_unpriced(self):
        from core import cost
        self.assertEqual(" · ≈ 0.10 USD (ước tính)", cost.image_button_tag("img-a", 2, self.PRICING))
        self.assertEqual(" · chưa có giá — ước tính dư ≈ 0.15 USD", cost.image_button_tag("img-new", 2, self.PRICING))  # 0.05×2×1.5
        self.assertEqual(" · chưa có giá", cost.image_button_tag("img-a", 1, {"per_image": {}}))
        self.assertEqual("", cost.image_button_tag("img-a", 0, self.PRICING))

    def test_llm_tag_counts_the_margin_and_estimates_an_unpriced_model_high(self):
        from unittest import mock
        from core import cost
        with mock.patch.dict("os.environ", {"ANTHROPIC_MODEL": "claude-x"}):
            self.assertEqual(" · Claude ≈ 0.04 USD (ước tính)", cost.llm_tokens_tag(10000, 1000, self.PRICING))   # (0.02+0.01)×1.3
        with mock.patch.dict("os.environ", {"ANTHROPIC_MODEL": "claude-new"}):
            self.assertEqual(" · Claude chưa có giá — ước tính dư ≈ 0.06 USD", cost.llm_tokens_tag(10000, 1000, self.PRICING))
            self.assertIn("chưa có giá — ước tính dư", cost.llm_button_tag(None, "qc", 1, pricing=self.PRICING))
        self.assertEqual(" · Claude: chưa có giá", cost.llm_tokens_tag(10, 10, {"per_million_tokens": {}}))

    def test_llm_tag_says_it_is_an_estimate(self):
        from core import cost
        self.assertEqual(" · Claude ≈ 0.05 USD (ước tính)", cost.llm_tag(0.05))

    def _video_project(self):
        from unittest import mock
        from core import cost
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("v")
        est = {"items": 2, "min": 0.5, "max": 1.5}
        return p, pid, mock.patch.object(cost, "estimate_videos_by_scene", return_value=est)

    def test_video_batch_counts_the_automatic_retakes_high(self):
        from core import cost
        from core.pipeline import AUTO_REGEN_LIMIT
        p, pid, patch = self._video_project()
        with patch:
            tag = cost.video_batch_tag(p, pid)
        top = 0.5 * (1 + AUTO_REGEN_LIMIT["video_gen"])
        self.assertEqual(f" · 2 clip ≈ 0.50 USD (ước tính; tự gen lại tối đa {AUTO_REGEN_LIMIT['video_gen']} lần ≈ {top:.2f})", tag)

    def test_video_batch_tag_is_computed_once_per_draw(self):
        """(f) 194 ms on #8 for every rerun: the result is kept until the database changes."""
        from core import cost
        p, pid, patch = self._video_project()
        with patch as est:
            cost.video_batch_tag(p, pid)
            cost.video_batch_tag(p, pid)
            self.assertEqual(est.call_count, 1)
            p.create_scene(pid, 1, "S1")                                       # any write → computed again
            cost.video_batch_tag(p, pid)
            self.assertEqual(est.call_count, 2)

    def test_retake_rewrite_estimate_is_computed_once_per_draw(self):
        from unittest import mock
        from core import cost
        from core.db import connect
        conn = connect()
        with mock.patch.object(cost, "rewrite_estimate", return_value=(0.01, 0.04)) as rw:
            for _ in range(5):                                                  # five picture cards on one page
                cost.image_button_tag("img-a", 1, self.PRICING, retake_conn=conn)
        self.assertEqual(rw.call_count, 1)


class EditorReviewWithoutClaude(unittest.TestCase):
    """J6 (mục 8): the rough-cut review button said nothing when Claude was not set up — now it says why and what to do."""

    def test_button_without_claude_says_why_and_how(self):
        from unittest import mock
        from dashboard.steps import step5
        fake = mock.MagicMock()
        fake.button.return_value = True
        conn = mock.MagicMock()
        p = mock.MagicMock(conn=conn)
        with mock.patch.object(step5, "st", fake), mock.patch.object(step5.C, "llm_client", return_value=None),                 mock.patch("core.editor_review.estimate", return_value=0.1),                 mock.patch("core.editor_review.load", return_value=None),                 mock.patch.object(step5, "editor_apply_state", lambda *a: None):
            step5.editor_review_panel(p, 7, {"sheets": ["a.png"]})
        said = " ".join(str(c.args[0]) for c in fake.error.call_args_list)
        self.assertIn("Claude", said)
        self.assertIn("ANTHROPIC_API_KEY", said)          # how to fix
        self.assertIn("chưa", said.lower())


if __name__ == "__main__":
    unittest.main()
