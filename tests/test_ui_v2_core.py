"""S13 nhánh A: token giao diện v2 đạt tương phản đã hứa, thành phần escape đúng, cờ ui_v2 nạp lớp thiết kế, trang G1 dựng được."""
import os
import re
import tempfile
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from dashboard.design import components as D
from dashboard.design import tokens

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")


class TokenTests(unittest.TestCase):
    def test_promised_contrast_holds_in_both_themes(self):
        for theme in ("dark", "light"):
            for name, fg, bg, need in tokens.promised_pairs(theme):
                self.assertGreaterEqual(tokens.contrast_ratio(fg, bg), need, f"{theme}: {name} {fg} on {bg}")

    def test_ratio_function_matches_known_values(self):
        self.assertAlmostEqual(tokens.contrast_ratio("#000000", "#FFFFFF"), 21.0, places=1)
        self.assertAlmostEqual(tokens.contrast_ratio("#777777", "#FFFFFF"), 4.48, places=1)

    def test_css_vars_cover_every_token_and_no_size_below_12(self):
        css = tokens.css_vars("dark")
        for k in tokens.DARK:
            self.assertIn(f"--{k}:", css)
        self.assertIn("--grad-primary:", css)
        self.assertTrue(all(float(v.replace("px", "")) >= 12 for v in tokens.TYPE.values()))

    def test_theme_css_uses_only_stable_hooks(self):
        path = os.path.join(os.path.dirname(__file__), "..", "dashboard", "design", "theme.css")
        css = open(path, encoding="utf-8").read()
        self.assertNotIn("st-emotion-cache", css)                 # emotion class names change with every Streamlit version
        self.assertNotRegex(css, r"font-size:\s*(\d|1[01])(\.\d+)?px")      # nothing under 12 px

    def test_no_font_size_below_the_caption_token_anywhere(self):
        """S14.8 U7 (người dùng 04/10: chữ tối thiểu 12,5 px = tokens.TYPE['caption']): mọi CSS của dashboard (ui.py, theme.css,
        shell.css) không có cỡ chữ px nhỏ hơn; `.badge` chỉ khai một lần."""
        from dashboard import ui
        floor = float(tokens.TYPE["caption"].replace("px", ""))
        self.assertEqual(floor, 12.5)
        here = os.path.join(os.path.dirname(__file__), "..", "dashboard", "design")
        sources = {"ui.py": ui.CSS}
        for name in ("theme.css", os.path.join("screens", "shell.css")):
            sources[name] = open(os.path.join(here, name), encoding="utf-8").read()
        small = [(name, m.group(0)) for name, css in sources.items()
                 for m in re.finditer(r"font-size:\s*(\d+(?:\.\d+)?)px", css) if float(m.group(1)) < floor]
        self.assertEqual(small, [])
        self.assertEqual(len(re.findall(r"(?:^|[}\n])\.badge\{", ui.CSS)), 1)

    def test_chat_input_follows_the_theme(self):
        """S14.47 (người dùng 06/10, ảnh chụp màn Kịch bản tối): ô st.chat_input giữ nền trắng của theme gốc Streamlit trong khi
        `textarea` đã nhận chữ sáng → dán kịch bản vào KHÔNG thấy chữ. Ô chat phải lấy nền đặc theo token (--surface, đủ tương phản
        với --text ở cả 2 theme) và chữ/con trỏ/placeholder theo token — ở cả lớp v2 (theme.css) lẫn nền tối cũ (ui.DARK_CSS)."""
        from dashboard import ui
        css = re.sub(r"/\*.*?\*/", "", open(os.path.join(os.path.dirname(__file__), "..", "dashboard", "design", "theme.css"),
                                            encoding="utf-8").read(), flags=re.S)
        for name, src in (("theme.css", css), ("DARK_CSS", ui.DARK_CSS)):
            with self.subTest(name):
                self.assertRegex(src, r'\[data-testid="stChatInput"\][^{]*\{[^}]*background:\s*var\(--surface\)')
                self.assertRegex(src, r'\[data-testid="stChatInput"\] textarea[^{]*\{[^}]*color:\s*var\(--text\)[^}]*caret-color:\s*var\(--text\)')
                self.assertRegex(src, r'\[data-testid="stChatInput"\] textarea::placeholder[^{]*\{[^}]*color:\s*var\(--muted\)')
        for theme in ("dark", "light"):
            t = tokens.DARK if theme == "dark" else tokens.LIGHT
            self.assertGreaterEqual(tokens.contrast_ratio(t["text"], t["surface"]), 4.5)

    def test_portals_and_folds_follow_the_theme(self):
        """Rà soát 02/10: hộp thoại st.dialog / menu nằm ngoài .stApp (cổng) → phải nhận token, nếu không ở nền tối chữ sáng nằm trên
        nền sáng = tàng hình (tiêu đề mục gập, ô chọn ▾, nhãn trong ⚙ → Kho tài nguyên / Tính năng thử)."""
        path = os.path.join(os.path.dirname(__file__), "..", "dashboard", "design", "theme.css")
        css = open(path, encoding="utf-8").read()
        self.assertRegex(css, r"body\s*\{[^}]*background:\s*var\(--bg\)[^}]*color:\s*var\(--text\)")
        self.assertRegex(css, r'\[data-testid="stDialog"\] > div\s*\{[^}]*background:\s*var\(--raised\)')
        self.assertRegex(css, r'\[data-testid="stExpander"\] summary:hover[^{]*\{[^}]*color:\s*var\(--text\)')
        self.assertRegex(css, r'\[data-testid="stCaptionContainer"\]\s*\{\s*opacity:\s*1')
        self.assertIn("filter: var(--canvas-filter)", css)
        self.assertEqual(tokens.LIGHT["canvas-filter"], "none")
        self.assertIn("invert", tokens.DARK["canvas-filter"])
        # 02/10: danh sách thả xuống của selectbox gắn thẳng vào body, chữ từng dòng ở thẻ con mang màu theme gốc → phải ép cả thẻ con
        self.assertRegex(css, r'\[data-testid="stSelectboxVirtualDropdown"\] \[role="option"\] \*[^{]*\{[^}]*color:\s*var\(--text\)')
        # 02/10: mũi tên ▾ (fill currentColor), nét icon "?" (stroke) và tooltip (cổng gắn body) mang màu theme gốc → tàng hình ở nền tối
        self.assertRegex(css, r'\[data-testid="stSelectbox"\], \[data-testid="stMultiSelect"\]\) svg[^{]*\{[^}]*color:\s*var\(--text\)')
        self.assertRegex(css, r'\[data-testid="stTooltipIcon"\] svg \*\s*\{[^}]*stroke:\s*var\(--muted\)')
        self.assertRegex(css, r'\[data-testid="stTooltipContent"\]\s*\{[^}]*background:\s*var\(--raised\)')
        # 02/10: Streamlit 1.64 bỏ thuộc tính data-baseweb → không còn luật nào dựa vào nó (ngoài ghi chú); thay bằng data-testid
        rules = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        self.assertNotIn("data-baseweb", rules)
        self.assertIn('[data-testid="stTab"] .react-aria-SelectionIndicator', rules)
        self.assertRegex(rules, r'\[data-testid="stMultiSelect"\] \[data-tag\]\s*\{[^}]*var\(--primary-soft\)')
        # popover ⚙ / 💵 không đè lên hộp thoại nó mở; lớp phủ sau hộp thoại theo token
        self.assertIn('body:has([data-testid="stDialog"]) [data-testid="stPopoverBody"]:has(.st-key-dark_toggle', rules)
        self.assertRegex(rules, r'\[data-testid="stDialog"\]\s*\{\s*background:\s*var\(--scrim\)')
        self.assertEqual(set(tokens.LIGHT), set(tokens.DARK))
        # 02/10: không còn nút tròn ⓘ — chú thích gắn ngay trên dòng/nhãn (infoa-), liên kết chữ nhỏ (info-) hoặc tooltip CSS (.v2-tip)
        self.assertNotIn("border-radius: 50%", re.search(r'\[class\*="st-key-info-"\] \[data-testid="stPopoverButton"\]\s*\{[^}]*\}', rules).group(0))
        self.assertRegex(rules, r'\[class\*="st-key-infoa-"\] \[data-testid="stPopoverButton"\]\s*\{[^}]*position:\s*absolute[^}]*inset:\s*0')
        self.assertRegex(rules, r'\.v2-tip:focus::after')                                  # tooltip cũng hiện khi focus bàn phím / chạm
        # người dùng 02/10: chú thích thường KHÔNG có gạch chân / nháy; chỉ biến thể attention (mặc định tắt) có vầng sáng hữu hạn 3 nhịp, tắt khi giảm chuyển động
        self.assertNotIn("underline dotted", rules)
        self.assertRegex(rules, r'\.v2-tip-anchor\.v2-attention[^{]*\{[^}]*animation:\s*v2-glow 2s ease-in-out 3\b')
        self.assertNotIn("infinite", re.search(r"@keyframes v2-glow.*?\n\}", rules, flags=re.S).group(0))
        self.assertRegex(rules, r'@media \(prefers-reduced-motion: reduce\)\s*\{\s*\.v2-tip-anchor\.v2-attention[^}]*animation:\s*none')
        self.assertNotRegex(rules, r'\.v2-tip-anchor\s*\{[^}]*animation')
        self.assertRegex(rules, r'\.v2-tip-anchor\[data-tip\]::after\s*\{[^}]*background:\s*var\(--raised\)[^}]*color:\s*var\(--text\)[^}]*font-size:\s*13px')
        for path in (os.path.join(os.path.dirname(__file__), "..", "dashboard", "ui.py"),
                     os.path.join(os.path.dirname(__file__), "..", "dashboard", "design", "screens", "shell.css")):
            self.assertNotIn("data-baseweb", re.sub(r"/\*.*?\*/", "", open(path, encoding="utf-8").read(), flags=re.S))


class SharedComponentTests(unittest.TestCase):
    """02/10: thành phần dùng chung còn thiếu ở lõi (note / version_strip / confirm_all / cta / grid / tip / md_plain / data_table)."""

    def test_tip_is_escaped_flat_and_plain(self):
        html = D.tip("<b>Nhãn</b>", '**Đậm** "trích"\n\n- một\n- <script>x</script>')
        self.assertIn('class="v2-tip"', html)
        self.assertIn('tabindex="0"', html)                         # keyboard / touch focus shows it
        self.assertNotIn("<script", html)
        self.assertNotIn("\n", html)                                # a newline/blank line would end the Markdown HTML block
        self.assertIn("&#10;• một", html)
        self.assertEqual(D.md_plain("**a**\n`b`\n- c"), "a\nb\n• c")
        self.assertLessEqual(len(D.md_plain("x " * 600)), 430)

    def test_tip_attention_is_opt_in(self):
        def app():
            import streamlit as st
            from dashboard.design import components as D
            st.markdown(D.tip("a", "b", key="k1"), unsafe_allow_html=True)
            st.markdown(D.tip("a", "b", key="k2", attention=True), unsafe_allow_html=True)
            st.markdown(D.tip("a", "b", key="k2", attention=True), unsafe_allow_html=True)      # second time the same key: no glow again
        at = AppTest.from_function(app, default_timeout=30).run()
        vals = [m.value for m in at.markdown]
        self.assertNotIn("v2-attention", vals[0])
        self.assertIn("v2-attention", vals[1])
        self.assertNotIn("v2-attention", vals[2])

    def test_attention_glow_plays_once_per_session_not_on_every_rerun(self):
        def app():
            from dashboard.design import components as D
            D.line("<b>x</b>", "chi tiết", key="warn", attention=True)
        at = AppTest.from_function(app, default_timeout=30).run()
        first = [m.value for m in at.markdown if "v2-tip-anchor" in m.value]
        self.assertTrue(any("v2-attention" in v for v in first))
        at.run()                                                    # autopilot_progress refresh = a rerun of the same session
        again = [m.value for m in at.markdown if "v2-tip-anchor" in m.value]
        self.assertTrue(again and not any("v2-attention" in v for v in again))

    def test_keys_of_a_self_refreshing_fragment_are_stable_so_an_open_popover_survives(self):
        """autopilot_progress reruns itself every 5 s: a changed popover/tooltip key = a remounted element = an open popover closes."""
        def app():
            import streamlit as st
            from dashboard.steps import step1_v2 as S
            S.reset_scope("ap")
            st.session_state.setdefault("seen_keys", []).append([S._uniq("script-cap-abc", "ap"), S._uniq("script-cap-abc", "ap")])
        at = AppTest.from_function(app, default_timeout=30).run()
        at.run()
        at.run()
        runs = at.session_state["seen_keys"]
        self.assertEqual(runs[0], runs[1])
        self.assertEqual(runs[1], runs[2])                          # same keys at every refresh
        self.assertNotEqual(runs[0][0], runs[0][1])                 # two equal captions in ONE run still get different keys

    def test_note_one_line_with_full_text_behind_it(self):
        def app():
            from dashboard.design import components as D
            D.note("warning", "Câu đầu tiên của ghi chú dài này. Câu thứ hai nói thêm nhiều điều nữa để vượt giới hạn.", key="n1")
            D.note("success", "Ngắn", key="n2")
        at = AppTest.from_function(app, default_timeout=30).run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(len(at.get("popover")), 1)                 # only the long one gets a popover; the short one is printed as is
        self.assertTrue(any("Câu thứ hai" in m.value for p in at.get("popover") for m in p.markdown))
        self.assertTrue(any("Lưu ý" in m.value for m in at.markdown))

    def test_version_strip_marks_current_and_wraps(self):
        html = D.version_strip(4, 2)
        self.assertEqual(html.count("v2-ver"), 5)                   # 4 chips + the "v2-vers" wrapper class name
        self.assertIn('class="v2-ver on">v3<', html)
        self.assertIn('class="v2-ver">v1<', html)
        self.assertIn("v1", D.version_strip(0, 5))                  # clamps
        css = open(os.path.join(os.path.dirname(__file__), "..", "dashboard", "design", "theme.css"), encoding="utf-8").read()
        self.assertRegex(css, r"\.v2-vers\s*\{[^}]*flex-wrap:\s*wrap")

    def test_confirm_all_asks_again_when_the_set_changes_and_returns_true_only_on_yes(self):
        def app():
            import streamlit as st
            from dashboard.design import components as D
            ids = st.session_state.get("ids", ("a", "b"))
            st.session_state["ok"] = D.confirm_all("ca", ids, "Duyệt hết", "Chắc chưa?", st, primary=True, stretch=True)
        at = AppTest.from_function(app, default_timeout=30).run()
        btn = next(b for b in at.button if b.key == "ca")
        self.assertEqual(btn.proto.type, "primary")
        btn.click().run()
        self.assertTrue(any("Chắc chưa?" in w.value for w in at.warning))
        at.session_state["ids"] = ("a",)                            # the set changed → the old question is forgotten
        at.run()
        self.assertFalse(any("Chắc chưa?" in w.value for w in at.warning))
        next(b for b in at.button if b.key == "ca").click().run()
        next(b for b in at.button if b.key == "ca_yes").click().run()
        self.assertTrue(at.session_state["ok"])

    def test_common_confirm_all_is_the_shared_one(self):
        import inspect
        from dashboard import common
        self.assertIn("components.confirm_all", inspect.getsource(common.confirm_all))

    def test_cta_and_grid(self):
        def app():
            import streamlit as st
            from dashboard.design import components as D
            D.cta("Bắt đầu", "go")
            cols = D.grid(5, 3)
            for i, c in enumerate(cols):
                c.write(f"thẻ {i}")
            st.session_state["n_cols"] = len(cols)
        at = AppTest.from_function(app, default_timeout=30).run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(at.session_state["n_cols"], 5)
        self.assertEqual(next(b for b in at.button if b.key == "go").proto.type, "primary")
        self.assertEqual(len(at.columns), 6)                        # a row of 3 + a row of 3 (the last row keeps the same width)
        css = open(os.path.join(os.path.dirname(__file__), "..", "dashboard", "design", "theme.css"), encoding="utf-8").read()
        self.assertRegex(css, r'\[class\*="st-key-cta-"\] \[data-testid="stBaseButton-primary"\]\s*\{[^}]*min-height:\s*3\.5rem')

    def test_tooltip_of_later_columns_grows_to_the_left(self):
        """Tooltips in the 2nd+ column anchor to their right edge, so they are not clipped at the window edge (≤ 1100 px)."""
        css = open(os.path.join(os.path.dirname(__file__), "..", "dashboard", "design", "theme.css"), encoding="utf-8").read()
        self.assertRegex(css, r'\[data-testid="stColumn"\]:not\(:first-child\) \.v2-tip::after[^{]*\{[^}]*left:\s*auto;\s*right:\s*0')
        self.assertRegex(css, r'\[data-testid="stColumn"\]:not\(:first-child\)[^{]*\.v2-tip-anchor\[data-tip\]::after')

    def test_data_table_follows_the_flag(self):
        def app():
            from dashboard.design import components as D
            D.data_table([{"A": "<b>x</b>", "B": 2}], hide_index=True)
        with mock.patch.dict(os.environ, {"FEATURE_UI_V2": "1"}):
            at = AppTest.from_function(app, default_timeout=30).run()
        html = " ".join(m.value for m in at.markdown)
        self.assertIn("v2-table", html)
        self.assertIn("&lt;b&gt;", html)                            # cells are escaped
        self.assertEqual(len(at.dataframe), 0)
        with mock.patch.dict(os.environ, {"FEATURE_UI_V2": "0"}):
            at = AppTest.from_function(app, default_timeout=30).run()
        self.assertEqual(len(at.dataframe), 1)                      # flag off: exactly the old st.dataframe


class ComponentTests(unittest.TestCase):
    def test_everything_user_supplied_is_escaped(self):
        self.assertNotIn("<script", D.pill("<script>x</script>", "ok"))
        self.assertNotIn("<img", D.hero_html("<img src=x>", "<b>", [("<i>", "ok")]))
        self.assertIn("&lt;", D.empty_state("<b>", "<i>"))

    def test_meter_colour_follows_completion_and_inverts_for_money(self):
        self.assertIn("var(--bad)", D.meter(0.1))
        self.assertIn("var(--warn)", D.meter(0.5))
        self.assertIn("var(--info)", D.meter(0.8))
        self.assertIn("var(--ok)", D.meter(1.0))
        self.assertIn("var(--ok)", D.meter(0.3, invert=True))
        self.assertIn("var(--bad)", D.meter(0.95, invert=True))
        self.assertIn("100%", D.meter(7))                          # clamped

    def test_frame_states_are_the_fixed_vocabulary(self):
        for key, label in (("review", "Cần duyệt"), ("approved", "Đã duyệt"), ("rejected", "Từ chối"), ("failed", "Lỗi")):
            self.assertIn(label, D.frame_state_pill(key))
        self.assertIn("v2-run", D.frame_state_pill("working"))      # only a running job pulses


class FlagTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        self.env = mock.patch.dict(os.environ, {"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(self.tmp, "projects"),
                                                "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "ku")})
        self.env.start()
        self.addCleanup(self.env.stop)
        from core.db import connect
        from core.pipeline import Pipeline
        Pipeline(connect(self.db)).create_project("v2")

    def test_flag_is_off_by_default_and_loads_nothing_new(self):
        at = AppTest.from_file(APP, default_timeout=60).run()
        self.assertFalse(at.exception, at.exception)
        self.assertFalse(any("--grad-primary" in (m.value or "") for m in at.markdown))

    def test_flag_on_injects_the_design_layer_and_the_g1_slice_renders(self):
        with mock.patch.dict(os.environ, {"FEATURE_UI_V2": "1"}):
            at = AppTest.from_file(APP, default_timeout=90)
            at.query_params["step"] = "design"
            at.run()
            self.assertFalse(at.exception, at.exception)
            self.assertTrue(any("--grad-primary" in (m.value or "") for m in at.markdown))      # tokens injected
            self.assertTrue(any(b.key == "v2d_ok_3" for b in at.button))                         # a frame card with real widgets
            self.assertTrue(any("G1" in m.value for m in at.markdown))


if __name__ == "__main__":
    unittest.main()


class InfoTests(unittest.TestCase):
    def test_info_popover_and_summary_line_render_with_the_details_inside(self):
        def app():
            import streamlit as st
            from dashboard.design import components as D
            D.line("<b>3 khung cần duyệt</b>", "Chi tiết dài\n\n- khung 3\n- khung 5", key="demo")
            with D.info("other"):
                st.markdown("nội dung phụ")
        at = AppTest.from_function(app, default_timeout=30).run()
        self.assertFalse(at.exception, at.exception)
        labels = [x.proto.popover.label for x in at.get("popover")]
        self.assertNotIn("ⓘ", labels)                               # 02/10: no round ⓘ button any more
        self.assertEqual(labels.count("Chi tiết"), 2)               # the trigger has a text name (screen readers); visually it is the line itself
        keys = [x.key for x in at.get("popover")]
        self.assertEqual(len(keys), 2)
        # the hover/focus tooltip is drawn by CSS from data-tip on the anchor line: the details as plain text, escaped, no blank lines
        tips = [m.value for m in at.markdown if "v2-tip-anchor" in (m.value or "")]
        self.assertTrue(any('data-tip="Chi tiết dài&#10;• khung 3&#10;• khung 5"' in t for t in tips), tips)
        self.assertFalse(any("v2-attention" in t for t in tips))   # the attention glow is OFF by default
        self.assertTrue(any("khung cần duyệt" in m.value for m in at.markdown))
        self.assertTrue(any("khung 5" in m.value for m in at.markdown))         # the details are in the popover, not dropped
