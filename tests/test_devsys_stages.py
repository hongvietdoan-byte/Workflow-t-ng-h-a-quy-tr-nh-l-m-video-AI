"""K0a kế hoạch kiểm soát (docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md mục 3.9, N3, N6, N7): hợp đồng của SỔ KHÂU
devsys/stages.json + BẢNG LOẠI LỖI devsys/error_types.json + định dạng ca hồi quy tests/golden/.

Đỏ đúng chỗ thiếu thật nhưng không làm đỏ cả bộ: chỗ thiếu ĐÃ BIẾT phải ghi `dot` (đợt kế hoạch sẽ lấp). Khâu tốn tiền đang chạy mà không có
lớp kiểm trước đang chạy / học việc, hoặc lớp kiểm đọc chữ tự do để kết luận → thiếu `dot` là đỏ. Chạy `-s` để in bảng khâu thiếu kiểm."""
import os
import tempfile
import unittest
from unittest import mock

from devsys import decisions, stages
from tests import golden

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class StagesBookTests(unittest.TestCase):
    def setUp(self):
        self.doc = stages.load_stages()
        self.deci = decisions.load()

    def test_book_has_no_problems(self):
        self.assertEqual(stages.stage_problems(self.doc, self.deci), [])

    def test_every_work_stage_l1_to_l16_is_listed(self):
        got = {stages.base_id(s["id"]) for s in self.doc["stages"]}
        self.assertEqual(got, {f"L{i}" for i in range(1, 17)})
        for sp in ("am_thanh", "phu_de", "dung"):                       # A11: âm / chữ / dựng có dòng riêng
            self.assertIn(sp, {s["san_pham"] for s in self.doc["stages"]})

    def test_code_stages_found_missing_by_the_review_are_now_in_decisions(self):
        wheres = " ".join(d["where"] for d in self.deci["items"])
        for path in ("core/prompt_formula.py", "core/stage_facts.py", "core/before_run.py", "core/stage_solver.py",
                     "tools/render_plates.py", "core/end_popup.py", "core/change_audit.py"):
            self.assertIn(path + ":", wheres)
        self.assertEqual(decisions.broken_wheres(self.deci, ROOT), [])

    def test_paid_stage_without_live_pre_check_needs_a_planned_wave(self):
        bad = {"stages": [dict(s) for s in self.doc["stages"]]}
        l9 = next(s for s in bad["stages"] if s["id"] == "L9")
        l9["dot"] = None
        got = " ".join(stages.stage_problems(bad, self.deci))
        self.assertIn("L9", got)
        self.assertIn("kiểm trước", got)

    def test_a_switched_off_pre_check_does_not_count(self):
        s = {"id": "L99", "ten": "x", "san_pham": "anh", "lam": [], "ton_tien": True, "khau_trang_thai": "chay",
             "kiem_truoc": ["d24"], "trang_thai_kiem": "tat", "kiem_sau": [], "trang_thai_sau": "khong_co", "doc_tu": "ket_qua",
             "nguoi_kiem": True, "dot": None}
        self.assertIn("L99", " ".join(stages.stage_problems({"stages": [s]}, self.deci)))
        self.assertEqual([x["id"] for x in stages.missing_pre_checks({"stages": [s]})], ["L99"])
        s2 = dict(s, khau_trang_thai="tat")                             # khâu không chạy: không đòi đợt
        self.assertEqual(stages.stage_problems({"stages": [s2]}, self.deci), [])

    def test_free_text_reading_needs_a_planned_wave(self):
        s = {"id": "L98", "ten": "x", "san_pham": "chu", "lam": [], "ton_tien": False, "khau_trang_thai": "chay",
             "kiem_truoc": ["d84"], "trang_thai_kiem": "chay", "kiem_sau": [], "trang_thai_sau": "khong_co", "doc_tu": "chu_tu_do",
             "nguoi_kiem": False, "dot": None}
        self.assertIn("chu_tu_do", " ".join(stages.stage_problems({"stages": [s]}, self.deci)))

    def test_unknown_ids_enums_and_inconsistent_states_are_reported(self):
        s = {"id": "L97", "ten": "x", "san_pham": "zz", "lam": ["d999"], "ton_tien": "yes", "khau_trang_thai": "chay",
             "kiem_truoc": [], "trang_thai_kiem": "chay", "kiem_sau": ["nope"], "trang_thai_sau": "??", "doc_tu": "mat_troi",
             "nguoi_kiem": True, "dot": "K99"}
        got = " ".join(stages.stage_problems({"stages": [s]}, self.deci))
        for word in ("d999", "nope", "zz", "ton_tien", "mat_troi", "??", "K99", "khong_co"):
            self.assertIn(word, got)

    def _row(self, sid):
        return next(dict(s) for s in self.doc["stages"] if s["id"] == sid)

    def test_check_lists_only_take_ids_whose_role_is_kiem(self):
        """Thẩm định 3: d85 (stage_facts.derive) là bộ SINH câu, d54/d19/d88 là cổng tiền / điều kiện vận hành, người duyệt ghi ở
        nguoi_kiem — không id nào trong ba nhóm đó được đếm là kiểm trước / kiểm sau."""
        vai = self.doc["vai"]
        for lst in ("kiem_truoc", "kiem_sau"):
            for s in self.doc["stages"]:
                for d in s[lst]:
                    self.assertIn(d, vai["kiem"], f"{s['id']}.{lst} {d}")
        for d, word in (("d85", "sinh"), ("d54", "kiem_chung"), ("d33", "nguoi_duyet"), ("d999x", "vai")):
            s = dict(self._row("L10"), kiem_truoc=["d84", d])
            got = " ".join(stages.stage_problems({"stages": [s], "vai": vai, "kiem_chung": self.doc["kiem_chung"]}, self.deci))
            self.assertIn(d, got)
            self.assertIn(word, got)

    def test_l8_has_no_pre_check_and_l3_says_d86_runs_only_on_change(self):
        l8 = self._row("L8")
        self.assertEqual((l8["kiem_truoc"], l8["trang_thai_kiem"]), ([], "khong_co"))
        self.assertIn("change_audit", self._row("L3")["ghi_chu"])

    def test_role_table_ids_exist_and_do_not_overlap(self):
        ids = {d["id"] for d in self.deci["items"]}
        seen = {}
        for role, lst in self.doc["vai"].items():
            self.assertIn(role, stages.VAI)
            for d in lst:
                self.assertIn(d, ids)
                self.assertNotIn(d, seen, f"{d} vừa {seen.get(d)} vừa {role}")
                seen[d] = role

    def test_new_check_ids_are_kiem_but_not_counted_until_wired(self):
        """Thẩm định 4 #3: identity_declare (d95) + world_rules (d96) có id vai 'kiem' để sổ trỏ được, nhưng CHƯA nối vào luồng gen →
        không nằm trong kiem_truoc / kiem_sau của khâu nào (không thổi số 'có kiểm')."""
        items = {d["id"]: d for d in self.deci["items"]}
        self.assertEqual(items["d95"]["where"], "core/identity_declare.py:check")
        self.assertEqual(items["d96"]["where"], "core/world_rules.py:tim")
        for d in ("d95", "d96"):
            self.assertIn(d, self.doc["vai"]["kiem"])
            self.assertIs(items[d].get("bat"), False)
            self.assertIn("CHƯA nối", items[d]["what"])
            for s in self.doc["stages"]:
                self.assertNotIn(d, s["kiem_truoc"] + s["kiem_sau"], s["id"])

    def test_wave_must_not_be_due(self):
        self.assertEqual(self.doc["dot_hien_tai"], "K0b")
        self.assertEqual(stages.stage_problems(self.doc, self.deci), [])           # đổi đợt không làm dòng nào quá hạn
        self.assertLess(stages.DOT.index("K4"), stages.DOT.index("K1b"))         # mục 8: K1b sau K4
        l9 = dict(self._row("L9"), dot="K0a")
        doc = {"stages": [l9], "vai": self.doc["vai"], "dot_hien_tai": "K0a"}
        got = " ".join(stages.stage_problems(doc, self.deci))
        self.assertIn("L9", got)
        self.assertIn("quá hạn", got)
        doc["dot_hien_tai"] = "K3"
        l9["dot"] = "K2"
        self.assertIn("quá hạn", " ".join(stages.stage_problems(doc, self.deci)))
        l9["dot"] = "K1b"                                                       # K1b sau K3 theo mục 8 → chưa tới hạn
        self.assertNotIn("quá hạn", " ".join(stages.stage_problems(doc, self.deci)))
        doc["dot_hien_tai"] = "K99"
        self.assertIn("dot_hien_tai", " ".join(stages.stage_problems(doc, self.deci)))

    def test_summary_table_prints(self):
        rows = stages.summary_rows(self.doc)
        self.assertEqual(len(rows), len(self.doc["stages"]))
        print("\n" + stages.summary_text(self.doc, stages.load_error_types()))


class FlagStateTests(unittest.TestCase):
    """Dòng có `co`: trạng thái đọc từ cờ thật (core.features.state) — đổi cờ không phải sửa sổ tay."""

    def setUp(self):
        self.doc = stages.load_stages()
        self.tmp = tempfile.mkdtemp()
        self.env = {"FEATURE_SETTINGS_FILE": os.path.join(self.tmp, "none.json")}

    def _row(self, doc, sid):
        return next(s for s in doc["stages"] if s["id"] == sid)

    def test_flag_on_and_off_change_the_state(self):
        with mock.patch.dict(os.environ, dict(self.env, FEATURE_CHANGE_REVIEW="1", FEATURE_ASSET_CHECKLIST="1")):
            eff = stages.effective(self.doc)
        self.assertEqual(self._row(eff, "L16")["trang_thai_kiem"], "chay")
        self.assertEqual(self._row(eff, "L2")["khau_trang_thai"], "chay")
        self.assertEqual(self._row(eff, "L2")["trang_thai_kiem"], "chay")
        with mock.patch.dict(os.environ, dict(self.env, FEATURE_CHANGE_REVIEW="0", FEATURE_ASSET_CHECKLIST="0")):
            eff = stages.effective(self.doc)
        self.assertEqual(self._row(eff, "L16")["trang_thai_kiem"], "tat")
        self.assertIn("change_review", " ".join(self._row(eff, "L16")["_co_ghi"]))   # khác ghi tay → nói ra
        self.assertEqual(self._row(eff, "L2")["khau_trang_thai"], "tat")
        self.assertEqual(self._row(self.doc, "L16")["trang_thai_kiem"], "chay")      # sổ gốc không bị sửa

    def test_unreadable_flag_keeps_the_hand_value_and_says_so(self):
        def boom(name):
            raise KeyError(name)
        eff = stages.effective(self.doc, state=boom)
        l16 = self._row(eff, "L16")
        self.assertEqual(l16["trang_thai_kiem"], "chay")
        self.assertIn("không đọc được cờ 'change_review'", " ".join(l16["_co_ghi"]))
        self.assertIn("không đọc được", stages.summary_rows(eff)[[r["id"] for r in stages.summary_rows(eff)].index("L16")]["ghi_co"])

    def test_empty_check_list_stays_khong_co(self):
        s = dict(self._row(self.doc, "L9"), co={"truoc": "scene_qc"})
        eff = stages.effective({"stages": [s]}, state=lambda n: "on")
        self.assertEqual(eff["stages"][0]["trang_thai_kiem"], "khong_co")

    def test_stage_camera_rows_follow_the_flag(self):
        """Thẩm định 3: L3 (d86), L6 (dàn cảnh + giải máy), L9 (d92) phụ thuộc cờ đang TẮT mặc định — đọc cờ thật, không ghi tay 'chay'."""
        self.assertEqual(self._row(self.doc, "L3")["co"].get("d86"), "stage_camera")
        self.assertEqual(self._row(self.doc, "L6")["co"].get("khau"), "stage_camera")
        self.assertIn("d92", self._row(self.doc, "L9")["co"])
        off = stages.effective(self.doc, state=lambda n: "off")
        l3 = self._row(off, "L3")
        self.assertNotIn("d86", l3["kiem_truoc"])                    # d86 tắt → không đếm; d10/d11/d84 vẫn chạy
        self.assertEqual(l3["trang_thai_kiem"], "chay")
        self.assertIn("d86", " ".join(l3["_co_ghi"]))
        self.assertEqual(self._row(off, "L6")["khau_trang_thai"], "tat")
        l9 = self._row(off, "L9")
        self.assertNotIn("d92", l9["kiem_sau"])
        self.assertNotIn("d24", l9["kiem_sau"])
        on = stages.effective(self.doc, state=lambda n: "on")
        self.assertIn("d86", self._row(on, "L3")["kiem_truoc"])
        self.assertEqual(self._row(on, "L6")["khau_trang_thai"], "chay")

    def test_every_id_flagged_off_makes_the_check_off(self):
        s = dict(self._row(self.doc, "L9"), kiem_sau=["d24", "d92"], trang_thai_sau="chay", co={"d24": "scene_qc", "d92": "x"})
        self.assertEqual(stages.effective({"stages": [s]}, state=lambda n: "off")["stages"][0]["trang_thai_sau"], "tat")
        self.assertEqual(stages.effective({"stages": [s]}, state=lambda n: "trainee")["stages"][0]["trang_thai_sau"], "hoc_viec")
        bad = dict(s, co={"d33": "scene_qc"})                        # cờ gắn cho id không có trong danh sách kiểm
        self.assertIn("d33", " ".join(stages.stage_problems({"stages": [bad]}, decisions.load())))

    def test_unknown_flag_is_reported(self):
        s = dict(self._row(self.doc, "L16"), co={"truoc": "khong_co_co_nay", "giua": "x"})
        got = " ".join(stages.stage_problems({"stages": [s]}, decisions.load()))
        self.assertIn("khong_co_co_nay", got)
        self.assertIn("co.giua", got)


class PageTests(unittest.TestCase):
    def test_page_renders_red_rows_and_error_types(self):
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError:  # pragma: no cover
            self.skipTest("streamlit.testing không có")
        at = AppTest.from_file(os.path.join(ROOT, "devsys", "app.py"), default_timeout=180)
        at.run()
        at.sidebar.radio[0].set_value("Làm ↔ Kiểm").run()
        self.assertEqual([e.value for e in at.exception], [])
        self.assertTrue(at.title[0].value.startswith("Làm ↔ Kiểm"))
        frames = [f.value for f in at.dataframe]
        first = frames[0].data if hasattr(frames[0], "data") else frames[0]
        self.assertIn("L9", list(first["Khâu"]))
        second = frames[1].data if hasattr(frames[1], "data") else frames[1]
        self.assertEqual(len(second), 24)
        text = " ".join(m.value for m in at.markdown)
        self.assertIn("Tốn tiền thiếu kiểm trước", text)


class ErrorTypeTests(unittest.TestCase):
    def setUp(self):
        self.doc = stages.load_error_types()

    def test_every_type_of_section_4_is_listed(self):
        want = {f"L{i}" for i in range(1, 16)} | {f"V{i}" for i in range(1, 5)} | {f"A{i}" for i in range(1, 5)} | {"R1"}
        self.assertEqual({t["id"] for t in self.doc["types"]}, want)

    def test_table_has_no_problems(self):
        self.assertEqual(stages.error_type_problems(self.doc, ROOT), [])

    def test_code_hoc_viec_is_shown_as_not_counted(self):
        """Rà độc lập #4: code_do 'hoc_viec' (L11 plate_layout_qc) không tính → nhãn nói rõ 'không tính', dòng vẫn chi_xay."""
        on = lambda f: "on"  # noqa: E731
        row = next(r for r in stages.error_type_rows(self.doc, state=on) if r["id"] == "L11")
        self.assertIn("học việc — không tính", row["co"])
        self.assertTrue(row["chi_xay"])
        t = {"types": [{"id": "X", "ten": "x", "ap_dung": ["anh"], "code_do": [],
                        "claude_khai": [{"mo_ta": "k", "enum": ["a"], "trang_thai": "hoc_viec", "dot": "K3", "co": "qc_team"}]}]}
        r = stages.error_type_rows(t, state=on)[0]
        self.assertIn("(học việc)", r["co"])
        self.assertNotIn("không tính", r["co"])
        self.assertFalse(r["chi_xay"])

    def test_a_product_without_any_check_is_red(self):
        bad = {"san_pham": ["anh", "video", "am_chu"],
               "types": [{"id": "L1", "ten": "x", "ap_dung": ["anh", "video"],
                          "code_do": [{"mo_ta": "m", "trang_thai": "co", "dot": None, "where": "core/qc_measure.py:faces", "san_pham": ["anh"]}],
                          "claude_khai": []}]}
        got = " ".join(stages.error_type_problems(bad, ROOT))
        self.assertIn("video", got)

    def test_building_without_wave_and_missing_where_are_red(self):
        bad = {"san_pham": ["anh"],
               "types": [{"id": "L1", "ten": "x", "ap_dung": ["anh"],
                          "code_do": [{"mo_ta": "m", "trang_thai": "xay", "dot": None, "where": None},
                                      {"mo_ta": "n", "trang_thai": "co", "dot": None, "where": "core/khong_co.py:f"},
                                      {"mo_ta": "o", "trang_thai": "co", "dot": None, "where": "core/qc_measure.py:khong_co_ham"}],
                          "claude_khai": [{"mo_ta": "k", "enum": [], "trang_thai": "gi_do", "dot": None, "where": None}]}]}
        got = " ".join(stages.error_type_problems(bad, ROOT))
        for word in ("dot", "core/khong_co.py", "khong_co_ham", "gi_do", "enum"):
            self.assertIn(word, got)

    def test_only_building_is_counted(self):
        ids = [t["id"] for t in stages.only_building(self.doc, state=lambda n: "on")]
        self.assertIn("L14", ids)
        self.assertNotIn("L7", ids)

    def test_switched_off_or_flagged_off_checks_do_not_count(self):
        """Thẩm định 3: mục `bat:false` và mục học việc / chạy phụ thuộc cờ đang TẮT không phải 'cách kiểm thật'."""
        off = [t["id"] for t in stages.only_building(self.doc, state=lambda n: "off")]
        on = [t["id"] for t in stages.only_building(self.doc, state=lambda n: "on")]
        self.assertGreater(len(off), len(on))
        for i in ("L7", "L9", "L2"):                                     # chỉ có kiểm dưới cờ (stage_camera / scene_qc / palette, qc_team)
            self.assertIn(i, off)
        self.assertNotIn("L8", off)                                      # plate_camera.subject_box chạy không cần cờ
        t = {"id": "X", "code_do": [{"mo_ta": "m", "trang_thai": "co", "where": "core/palette.py:check", "bat": False}], "claude_khai": []}
        self.assertEqual([x["id"] for x in stages.only_building({"types": [t]}, state=lambda n: "on")], ["X"])
        t2 = {"id": "Y", "code_do": [], "claude_khai": [{"mo_ta": "k", "enum": ["a"], "trang_thai": "hoc_viec", "co": "qc_team"}]}
        self.assertEqual([x["id"] for x in stages.only_building({"types": [t2]}, state=lambda n: "off")], ["Y"])
        self.assertEqual(stages.only_building({"types": [t2]}, state=lambda n: "trainee"), [])

    def test_l11_plate_layout_qc_is_trainee_and_not_counted(self):
        """Thẩm định 4 #3: chạy khô 10/10 đo plate_layout_qc MÙ khi render tối → học việc, KHÔNG tính kể cả khi cờ BẬT."""
        l11 = next(t for t in self.doc["types"] if t["id"] == "L11")
        e = next(e for e in l11["code_do"] if e["where"] == "core/plate_layout_qc.py:compare")
        self.assertEqual(e["trang_thai"], "hoc_viec")
        self.assertIn("mù", e["ghi_chu"].lower())
        self.assertIn("L11", [t["id"] for t in stages.only_building(self.doc, state=lambda n: "on")])
        t = {"id": "Z", "code_do": [{"mo_ta": "m", "trang_thai": "hoc_viec", "dot": "K3", "where": "core/palette.py:check", "co": "x"}],
             "claude_khai": []}
        self.assertEqual([x["id"] for x in stages.only_building({"types": [t]}, state=lambda n: "on")], ["Z"])

    def test_unwired_code_is_not_counted(self):
        """identity_declare (L2) / world_rules (L15): code có + test nhưng chưa nối → ghi 'xay' + đợt nối, không phải 'co'."""
        by = {t["id"]: t for t in self.doc["types"]}
        for tid, where, dot in (("L2", "core/identity_declare.py:check", "K1a"), ("L15", "core/world_rules.py:tim", "K3")):
            e = next(e for e in by[tid]["code_do"] if e.get("where") == where)
            self.assertEqual((e["trang_thai"], e["dot"]), ("xay", dot))

    def test_trainee_and_switched_off_entries_must_name_their_flag(self):
        for t in self.doc["types"]:
            for e in t.get("code_do", []) + t.get("claude_khai", []):
                if e.get("trang_thai") == "hoc_viec" or e.get("bat") is False:
                    self.assertTrue(e.get("co"), f"{t['id']} '{e['mo_ta']}' thiếu co")
        bad = {"san_pham": ["anh"], "types": [{"id": "L1", "ten": "x", "ap_dung": ["anh"], "code_do": [],
               "claude_khai": [{"mo_ta": "k", "enum": ["a"], "trang_thai": "hoc_viec", "dot": "K3", "where": None},
                               {"mo_ta": "q", "enum": ["a"], "trang_thai": "hoc_viec", "dot": "K3", "where": None, "co": "khong_co_co_nay"}]}]}
        got = " ".join(stages.error_type_problems(bad, ROOT))
        self.assertIn("'k'", got)
        self.assertIn("khong_co_co_nay", got)


class GoldenFormatTests(unittest.TestCase):
    def test_cases_follow_the_format(self):
        cases = golden.load_cases()
        self.assertGreaterEqual(len(cases), 8)                         # 8 ca stage_facts gộp từ tests/fixtures (K0a)
        types = [t["id"] for t in stages.load_error_types()["types"]]
        ids = [d["id"] for d in decisions.load()["items"]]
        kiem = stages.load_stages()["vai"]["kiem"]
        self.assertEqual([p for c in cases for p in golden.problems(c, types, ids, kiem)], [])
        self.assertEqual(len({c["id"] for c in cases}), len(cases))

    def test_k0b_coverage_targets(self):
        """K0b (kế hoạch dòng 307): ≥ 15 ca, ≥ 2 ca âm/chữ/dựng (A*: thoại sai người nói A1, popup không giữ khung cuối A4),
        ≥ 3 ca có BYĐ + gói; ca âm/chữ chưa có lớp chạy phải nói rõ ở ky_vong (lop_chay), không để trống."""
        cases = golden.load_cases()
        self.assertGreaterEqual(len(cases), 15)
        audio = [c for c in cases if any(t.startswith("A") for t in c["loai_loi"])]
        self.assertGreaterEqual(len(audio), 2)
        self.assertTrue({"A1", "A4"} <= {t for c in audio for t in c["loai_loi"]})
        for c in audio:
            kv = next(iter(c["ky_vong"].values()))
            self.assertTrue(str(kv.get("lop_chay") or "").strip(), c["id"])
        with_goi = [c for c in cases if c.get("byd") and any((c.get("goi") or {}).get(k) for k in ("image_prompt", "motion_prompt"))]
        self.assertGreaterEqual(len(with_goi), 3)
        known = {"stage_facts", "identity_declare", "shot_intent", "do_tu_the", "world_rules", "am_chu", "dung", "blockout"}
        readme = open(os.path.join(os.path.dirname(golden.__file__), "README.md"), encoding="utf-8").read()
        for c in cases:
            for k in c["ky_vong"]:
                self.assertIn(k, known, f"{c['id']}: khóa ky_vong '{k}' chưa ghi trong README")
        for k in known:
            self.assertIn(f"`{k}`", readme)

    def test_lop_phai_bat_only_names_check_layers(self):
        """Thẩm định 4 #3: lop_phai_bat phải là id vai 'kiem' (devsys/stages.json 'vai') — bộ SINH (d85) / bộ làm (d38, d91) ghi ở lop_lam."""
        kiem = set(stages.load_stages()["vai"]["kiem"])
        ids = {d["id"] for d in decisions.load()["items"]}
        for c in golden.load_cases():
            for d in c["lop_phai_bat"]:
                self.assertIn(d, kiem, f"{c['id']}: lop_phai_bat '{d}' không có vai kiem")
            for d in c.get("lop_lam") or []:
                self.assertIn(d, ids, c["id"])
                self.assertNotIn(d, kiem, f"{c['id']}: lop_lam '{d}' là lớp kiểm — chuyển sang lop_phai_bat")
        bad = dict(golden.load_cases()[0], lop_phai_bat=["d85"])
        self.assertIn("d85", " ".join(golden.problems(bad, kiem_ids=kiem)))
        bad = dict(golden.load_cases()[0], lop_lam=["d999"])                    # rà độc lập #6: lop_lam phải có trong decisions
        self.assertIn("d999", " ".join(golden.problems(bad, decision_ids=ids)))
        self.assertIn("lop_lam", " ".join(golden.problems(dict(bad, lop_lam="d85"), decision_ids=ids)))

    # khóa ky_vong → (tệp test chạy lớp đó trên ca, câu chọn ca phải có trong tệp)
    LOP_CHAY = {"stage_facts": ("tests/test_stage_facts.py", "GOLDEN = golden.stage_facts_cases()"),
                "identity_declare": ("tests/test_identity_declare.py", 'if "identity_declare" in (c.get("ky_vong") or {})]'),
                "world_rules": ("tests/test_world_rules.py", 'if "world_rules" in (c.get("ky_vong") or {})]'),
                "blockout": ("tests/test_blockout.py", 'if "blockout" in (c.get("ky_vong") or {})]')}

    def test_every_expectation_has_a_running_layer_or_says_which_wave(self):
        """Thẩm định 4 #4: kỳ vọng mà không lớp nào chạy (am_chu, dung, do_tu_the, shot_intent) phải ghi `chua_co_lop: "<đợt>"` —
        cấm kỳ vọng 'chết' trông như được kiểm."""
        for k, (path, needle) in self.LOP_CHAY.items():
            text = open(os.path.join(ROOT, *path.split("/")), encoding="utf-8").read()
            self.assertIn(needle, text, f"{path} không chạy ca có ky_vong.{k}")
            self.assertIn("parametrize", text, path)
        self.assertEqual(set(self.LOP_CHAY), set(golden.LOP_CHAY))
        for c in golden.load_cases():
            for k, v in c["ky_vong"].items():
                wave = v.get("chua_co_lop") if isinstance(v, dict) else None
                if k in self.LOP_CHAY:
                    self.assertIsNone(wave, f"{c['id']}.{k}: có lớp chạy mà ghi chua_co_lop")
                else:
                    self.assertIn(wave, stages.DOT, f"{c['id']}.{k}: không lớp nào chạy — ghi chua_co_lop = đợt (K…)")
        bad = dict(golden.load_cases()[0], ky_vong={"am_chu": {"thoai": []}})
        self.assertIn("chua_co_lop", " ".join(golden.problems(bad)))

    def test_format_problems_are_reported(self):
        bad = {"id": "x", "_file": "y.json", "ca_vang_tay": True, "byd": None, "loai_loi": ["L99"], "lop_phai_bat": ["d999"], "ky_vong": {}}
        got = " ".join(golden.problems(bad, ["L1"], ["d85"]))
        for word in ("nguon", "y.json", "L99", "d999", "ca_vang_tay", "ky_vong"):
            self.assertIn(word, got)

    def test_stage_facts_view_keeps_the_old_shape(self):
        c = golden.stage_facts_cases()[0]
        self.assertEqual(set(c), {"name", "source", "stage_camera", "objects", "image_prompt", "expect"})


if __name__ == "__main__":
    unittest.main()
