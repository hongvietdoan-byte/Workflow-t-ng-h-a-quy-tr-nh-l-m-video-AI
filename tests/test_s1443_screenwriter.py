"""S14.43 nhánh A (chấm phiếu 05d, người dùng 06/10, TB 4,20): Biên kịch dùng tên thật FF, thoại vui GenZ + khớp hành động, màn hình
điện thoại nhìn từ xa không chặn / lộ màn hình = cần tài nguyên màn hình mô phỏng, `idea_to_script` bật mặc định + hỏi khi kịch bản sơ sài,
kho khuôn hài. 0 USD (MockLlm / hàm thuần, không gọi API thật)."""
import json
import os
import unittest
from unittest import mock

from core import assets, idea_buildable as B, idea_to_script as I
from core.db import connect
from core.pipeline import Pipeline
from tests.test_idea_to_script import ANCHORS, IDEA, Recorder, make_kit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAD = "CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\n"
INP = {"duration_s": 15, "anchors": dict(ANCHORS, characters=["KELLY", "MAXIM"], plot="", ending="")}


class PhoneScreenS1443(unittest.TestCase):
    """Mục 4: nhìn TỪ XA (không đọc được) → không chặn; LỘ góc nhìn màn hình → không chặn, 'cần tài nguyên màn hình mô phỏng' (bảng kê +
    ước tính); nhắc màn hình mà không rõ xa/cận → nói ra (coi là từ xa), không im lặng."""

    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("màn hình", operating_mode="human_qc")
        make_kit(self.p.conn)

    def check(self, body):
        return I.check_script(self.p.conn, self.pid, HEAD + body, INP)

    def test_view_rules_far_close_content_unclear(self):
        cases = {
            "Toàn cảnh: Kelly và Maxim cúi nhìn điện thoại, màn hình nhìn từ xa không đọc được.": "far",
            "Máy đặt từ xa, Kelly chỉ vào màn hình điện thoại của Maxim.": "far",
            "Ánh sáng màn hình hắt lên mặt Kelly.": "far",
            "Cận màn hình điện thoại: huy hiệu hạng Huyền Thoại xoay.": "exposed",
            "Cận cảnh điện thoại trên tay Kelly.": "exposed",
            "Kelly giơ điện thoại về phía máy quay khoe rank.": "exposed",
            "Màn hình hiện dòng chữ 'Up next in 3'.": "exposed",
            "Quay màn hình: bảng xếp hạng bạn bè.": "exposed",
            "Trung cảnh, Kelly chỉ tay vào màn hình điện thoại của Maxim.": "unclear",
            "Maxim cau mày nhìn xuống màn hình mình.": "unclear",
            "Kelly đứng ở bãi cỏ, thanh máu hiện trên đầu.": "",
            "CHỮ TRÊN MÀN HÌNH: Tải Free Fire ngay": "",
        }
        for line, want in cases.items():
            with self.subTest(line=line):
                self.assertEqual(B.screen_view(line), want)

    def test_far_or_unclear_screen_is_not_blocked_and_unclear_is_said(self):
        far = self.check("Toàn cảnh từ xa: Kelly và Maxim cúi nhìn điện thoại.\nKELLY: Rớt rồi kìa!")
        self.assertEqual(far["blocked_scenes"], [])
        self.assertFalse(any("màn hình" in f for f in far["flags"]))
        unclear = self.check("Trung cảnh, Kelly chỉ tay vào màn hình điện thoại của Maxim.\nMAXIM: Xui thật đó mà.")
        self.assertEqual(unclear["blocked_scenes"], [])                    # phiếu 05d ý 2: không chặn nữa
        self.assertTrue(any("từ xa" in f.lower() for f in unclear["flags"]), unclear["flags"])   # nói ra, không im lặng

    def test_exposed_screen_is_a_resource_not_a_block(self):
        c = self.check("Cận màn hình điện thoại: huy hiệu hạng Huyền Thoại xoay, lớp 'Up next in 3' bật lên.\nKELLY: Ơ…")
        self.assertEqual(c["blocked_scenes"], [])
        self.assertTrue(any("cần tài nguyên màn hình mô phỏng" in f for f in c["flags"]), c["flags"])
        # game interface on the exposed phone screen = what the simulated screen shows (not a set to build)
        c2 = self.check("Cận màn hình điện thoại hiện bảng xếp hạng Free Fire.\nKELLY: Hạng nhất!")
        self.assertEqual(c2["blocked_scenes"], [])

    def test_game_interface_without_a_phone_is_still_blocked(self):
        c = self.check("Cận giao diện game Free Fire, minimap và bảng xếp hạng.\nMAXIM: Hạng nhất!")
        self.assertEqual(c["blocked_scenes"][0]["scene"], 1)
        c2 = self.check("Kelly nhảy dù xuống, vòng bo thu hẹp.\nKELLY: Đi!")
        self.assertEqual(c2["blocked_scenes"][0]["scene"], 1)                # combat gameplay off the phone: still blocked

    def test_screen_needs_go_into_the_asset_checklist_with_an_estimate(self):
        script = (HEAD + "Cận màn hình điện thoại: huy hiệu hạng Huyền Thoại.\nKELLY: Đỉnh chưa?\n\n"
                  "CẢNH 2 - NGÀY, ĐẢO QUÂN SỰ\nToàn cảnh từ xa, Kelly cúi nhìn điện thoại.\nKELLY: Ơ…")
        self.p.conn.execute("UPDATE projects SET script_text=? WHERE id=?", (script, self.pid))
        self.p.conn.commit()
        need = B.screen_needs(self.p.conn, self.pid)
        self.assertEqual([n["scene"] for n in need], [1])
        self.assertGreater(need[0]["est_usd"], 0)
        from core import asset_checklist
        with mock.patch.dict(os.environ, {"FEATURE_ASSET_CHECKLIST": "1"}):
            res = asset_checklist.get(self.p, self.pid)
        row = next(r for r in res["rows"] if r["status"] == "to_create")
        self.assertIn("màn hình", row["status_label"])
        self.assertIn("USD", row["status_label"])
        self.assertEqual(row["scenes"], [1])

    def test_writer_is_told_the_new_screen_rule(self):
        self.assertIn("TỪ XA", B.RULES)
        self.assertIn("màn hình mô phỏng", B.RULES)


SPARSE = ("CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\nKelly khoe rank.\n\nCẢNH 2 - NGÀY, ĐẢO QUÂN SỰ\nMàn hình lộ.\n\n"
          "CẢNH 3 - NGÀY, ĐẢO QUÂN SỰ\nKelly tắt máy.")
RICH = ("CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ — BÃI CỎ TRƯỚC NHÀ KHO\nMáy trung cảnh: Kelly ngồi trên thùng gỗ, giơ điện thoại khoe với Maxim, mặt tỉnh "
        "bơ như chuyện thường; Maxim ghé sát, mắt tròn xoe, tay cầm dở ổ bánh mì.\nKELLY: Cày nhẹ thôi mà, lên hạng rồi nè.\n"
        "MAXIM: Thật hả? Cho tớ xem với!\n\nCẢNH 2 - NGÀY, ĐẢO QUÂN SỰ — BÃI CỎ TRƯỚC NHÀ KHO\nMaxim chộp lấy điện thoại, nhấc cao khỏi tầm "
        "với của Kelly, cười khoái trí; Kelly nhảy lên với theo, tóc bay, dép tuột một chiếc.\nMAXIM: Haha, để tớ xem kỹ nhé!")


class SparseScriptS1443(unittest.TestCase):
    """Mục 5: kịch bản có tiêu đề cảnh nhưng sơ sài (0 USD, ngưỡng có căn cứ) → hỏi trong khung chat; ý định 'viết chi tiết từ dàn ý' nhận
    bằng luật; `idea_to_script` bật mặc định (người dùng duyệt 06/10, TB 4,20 phiếu 05d)."""

    def test_sparse_outline_is_detected_with_numbers(self):
        s = I.sparse(SPARSE)
        self.assertTrue(s["sparse"])
        self.assertTrue(any(ch.isdigit() for ch in " ".join(s["why"])), s["why"])     # lý do có số liệu
        self.assertFalse(I.sparse(RICH)["sparse"])
        self.assertFalse(I.sparse("Kelly khoe rank rồi bị lộ.")["sparse"])            # an idea is not a 'sparse script'

    def test_scripts_people_wrote_and_the_scored_scripts_are_not_sparse(self):
        import glob
        import re
        for f in glob.glob(os.path.join(ROOT, "samples", "*.md")) + glob.glob(os.path.join(ROOT, "samples", "*.txt")):
            with self.subTest(f=os.path.basename(f)):
                self.assertFalse(I.sparse(open(f, encoding="utf-8").read())["sparse"])
        doc = open(os.path.join(ROOT, "docs", "DO_S11_2_Y_TUONG_2026-10-05d.md"), encoding="utf-8").read()
        blocks = re.findall(r"\*\*Kịch bản\*\*.*?```\n(.*?)```", doc, re.S)
        self.assertGreaterEqual(len(blocks), 3)
        for b in blocks:
            text = "\n".join(re.sub(r"^\+ ?", "", ln) for ln in b.splitlines())
            self.assertFalse(I.sparse(text)["sparse"], text[:80])

    def test_expand_request_in_the_chat_is_recognised_by_rule(self):
        for said in ("viết kịch bản chi tiết từ dàn ý này", "Viết chi tiết từ dàn ý này giúp mình", "hãy viết bổ sung cho chi tiết",
                     "Phát triển dàn ý này thành kịch bản đầy đủ", "mở rộng kịch bản này cho chi tiết hơn", "giúp mình viết lại chi tiết hơn"):
            with self.subTest(said=said):
                self.assertIsNotNone(I.expand_request(said))
        r = I.expand_request("viết kịch bản chi tiết từ dàn ý này:\n" + SPARSE)
        self.assertEqual(r["rest"].strip(), SPARSE)
        for not_said in ("KELLY: Viết chi tiết đi!", "Kelly viết nhật ký chi tiết về trận đấu ở Đảo Quân Sự.", SPARSE, RICH,
                         "cho Maxim thắng ở cuối", ""):
            with self.subTest(not_said=not_said[:30]):
                self.assertIsNone(I.expand_request(not_said))

    def test_feature_is_verified_on_by_default_with_the_gate_result(self):
        from core import features
        f = features.FEATURES["idea_to_script"]
        self.assertTrue(f["verified"])
        self.assertIn("4,20", f["why"])
        self.assertIn("05d", f["why"])

    def test_expand_estimate_is_the_four_paid_turns_within_the_cap(self):
        self.assertAlmostEqual(I.expand_usd(), 4 * I.TURN_USD)
        self.assertLessEqual(I.expand_usd(), I.RUN_CAP_USD)

    def test_writer_given_a_script_keeps_its_scenes_and_an_idea_prompt_is_unchanged(self):
        p = Pipeline(connect())
        pid = p.create_project("dàn ý", operating_mode="human_qc")
        make_kit(p.conn)
        m = Recorder()
        I.start(p.conn, pid, IDEA, anchors=ANCHORS)
        self.assertNotIn("from_script", I.get_state(p.conn, pid)["inputs"])
        I.questions(p.conn, pid, m)
        self.assertNotIn("DÀN Ý SƠ SÀI", m.prompts[-1])
        I.start(p.conn, pid, SPARSE, anchors=ANCHORS)
        self.assertTrue(I.get_state(p.conn, pid)["inputs"]["from_script"])
        I.questions(p.conn, pid, m)
        self.assertIn("DÀN Ý SƠ SÀI", m.prompts[-1])
        self.assertIn("Kelly khoe rank.", m.prompts[-1])


class RealFFNamesS1443(unittest.TestCase):
    """Mục 1: Biên kịch nhận TÊN THẬT + tên khác của các mục Kho mà ý tưởng nhắc tới (gọn: chỉ mục liên quan), và danh sách 'dựng được'
    có cả tên khác — để gọi 'Mr. Waggor' thay vì 'chim cánh cụt'. Không thêm lời gọi Claude."""

    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("tên thật", operating_mode="human_qc")
        make_kit(self.p.conn)
        assets.create(self.p.conn, "FF", "pet", "Mr. Waggor", "pet chim cánh cụt", aliases="chim cánh cụt, Waggor")
        assets.create(self.p.conn, "FF", "weapon", "M1887", "shotgun hai nòng", aliases="súng hai nòng")
        kid = self.p.conn.execute("SELECT id FROM assets WHERE name='KELLY'").fetchone()[0]
        self.p.conn.execute("UPDATE assets SET aliases='Kelly Tốc Độ' WHERE id=?", (kid,))
        self.p.conn.commit()
        self.m = Recorder()

    def test_kho_entries_named_in_the_idea_go_in_with_real_name_and_aliases(self):
        idea = "Kelly và Maxim tranh nhau một thùng thính ở Đảo Quân Sự, chim cánh cụt lẻn tới ăn mất, mở ra thì trống trơn."
        I.start(self.p.conn, self.pid, idea, anchors=ANCHORS)
        I.questions(self.p.conn, self.pid, self.m)
        pr = self.m.prompts[0]
        self.assertIn("Tên thật trong Kho FF", pr)
        block = pr.split("Tên thật trong Kho FF", 1)[1].split("\n## ", 1)[0]
        self.assertIn("Mr. Waggor", block)
        self.assertIn("chim cánh cụt", block)
        self.assertNotIn("M1887", pr)                                       # gọn: only what the idea is about

    def test_buildable_list_carries_aliases(self):
        self.assertIn("Kelly Tốc Độ", B.kit_block(B.kit(self.p.conn, self.pid)))

    def test_no_named_entry_no_block(self):
        self.assertEqual(B.names_block(self.p.conn, self.pid, {"idea": "Hai người ngồi uống trà."}), "")


KHUON = os.path.join(ROOT, "knowledge", "craft", "khuon_hai.md")


class RoleAndPatternsS1443(unittest.TestCase):
    """Mục 1/2/3: luật Biên kịch (tên thật FF, thoại vui GenZ vẫn sạch, thoại khớp hành động — có lý do + ví dụ, có trong Kiểm);
    mục 6: kho khuôn hài nạp như GỢI Ý ở lượt chọn hướng + dàn ý, gọn."""

    def setUp(self):
        self.role = open(os.path.join(ROOT, "knowledge", "roles", "screenwriter.md"), encoding="utf-8").read()

    def test_role_has_the_three_new_rules_with_reasons_and_examples(self):
        for word in ("Tên thật", "Mr. Waggor", "GenZ", "Haha, của tớ nhé!", "khớp hành động", "05d"):
            self.assertIn(word, self.role)
        kiem = self.role.split("## Kiểm", 1)[1]
        self.assertIn("khớp hành động", kiem)
        from core import clean_dialogue as C
        examples = self.role.split("B12", 1)[1].split("**B13", 1)[0]
        self.assertEqual(C.find(examples.replace("mày/tao", "")), [])        # GenZ examples stay clean (S14.41)

    def test_pattern_book_has_the_first_pattern_with_every_field_and_is_small(self):
        text = open(KHUON, encoding="utf-8").read()
        for field in ("Khoe giả bị lộ bởi chính đạo cụ", "Cấu trúc theo giây", "Hài ở đâu", "Twist", "Manh mối", "Khi nào hợp", "Nguồn",
                      "fb_2649190858829247"):
            self.assertIn(field, text)
        self.assertIn("GỢI Ý", text)
        self.assertLess(len(text), 4500)                                     # gọn: không phình prompt

    def test_pattern_book_goes_into_directions_and_outline_not_questions(self):
        p = Pipeline(connect())
        pid = p.create_project("khuôn", operating_mode="human_qc")
        make_kit(p.conn)
        m = Recorder()
        I.start(p.conn, pid, IDEA, anchors=ANCHORS)
        I.questions(p.conn, pid, m)
        I.answer(p.conn, pid, [])
        I.directions(p.conn, pid, m)
        I.outline(p.conn, pid, m, 0)
        self.assertNotIn("Khoe giả bị lộ bởi chính đạo cụ", m.prompts[0])
        self.assertIn("Khoe giả bị lộ bởi chính đạo cụ", m.prompts[1])
        self.assertIn("Khoe giả bị lộ bởi chính đạo cụ", m.prompts[2])
        self.assertIn("không bắt buộc", m.prompts[1])


try:
    from tests.test_ui_script import ScriptBoxTests, tree_keys
except Exception:  # noqa: BLE001 - streamlit testing missing → the pure tests above still run
    ScriptBoxTests = None

if ScriptBoxTests is not None:
    class SparseChatS1443(unittest.TestCase):
        """The question in the chat (no model call — ScriptBoxTests' setUp fails any MockLlm call). Borrows its helpers, not its tests."""
        setUp, app, say, html = ScriptBoxTests.setUp, ScriptBoxTests.app, ScriptBoxTests.say, ScriptBoxTests.html

        def test_sparse_script_asks_in_the_chat_and_yes_goes_to_the_writer_without_paying(self):
            pid = self.p.create_project("Sơ sài")
            at = self.say(self.app(pid), SPARSE)
            html = self.html(at)
            self.assertIn("sơ sài", html)
            self.assertIn("muốn mình viết bổ sung", html)
            self.assertIn(f"{I.expand_usd():.2f}", html)
            at.button(key=f"box_expand_yes_{pid}").click().run()
            self.assertFalse(at.exception, at.exception)
            self.assertEqual(at.session_state[f"in_mode_{pid}"], "idea")
            self.assertIn(f"idea_form_{pid}", tree_keys(at))                    # the Biên kịch path, every turn behind a priced button
            self.assertEqual(I.get_state(self.p.conn, pid), {})                  # nothing started, nothing paid

        def test_rich_script_is_not_asked(self):
            pid = self.p.create_project("Đủ")
            at = self.say(self.app(pid), RICH)
            self.assertNotIn(f"box_expand_yes_{pid}", tree_keys(at))

        def test_typed_expand_request_takes_the_outline_to_the_writer(self):
            pid = self.p.create_project("Yêu cầu")
            at = self.say(self.app(pid), "viết kịch bản chi tiết từ dàn ý này:\n" + SPARSE)
            self.assertEqual(at.session_state[f"in_mode_{pid}"], "idea")
            self.assertEqual(at.session_state[f"box_text_{pid}"].strip(), SPARSE)
            self.assertIn(f"idea_form_{pid}", tree_keys(at))
            self.assertEqual(I.get_state(self.p.conn, pid), {})


if __name__ == "__main__":
    unittest.main()
