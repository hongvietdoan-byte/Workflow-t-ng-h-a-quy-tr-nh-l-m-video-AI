"""Sân khấu chia vai (cờ stage_crew, kế hoạch docs/KE_HOACH_CHIA_VAI_SAN_KHAU_2026-10-16.md). Không gọi API thật, không Blender: dùng
khung test của tests/test_stage_auto (Claude giả, K1 / K3+K4 giả)."""
import copy
import json
import os
import unittest
from unittest import mock

from core import features, llm_io, stage_auto, stage_crew as sc
from tests.test_stage_auto import Base, FakeClaude

CREW_ON = {"FEATURE_STAGE_CREW": "1"}


def blocking(shots=(1, 2, 3), nhip=None):
    bl = {"objects": [{"key": "kelly", "kind": "nguoi", "at": [0.0, 0.0], "H": 1.7, "facing": 0, "label": "Kelly"}],
          "beats": {"n1": {"kelly": {"at": [0.0, 0.0], "_ly_do": "đứng giữa phòng"}}},
          "beat_intent": {"n1": "thấy Kelly"}, "shot_nhip": {str(s): (nhip if nhip is not None else "n1") for s in shots}}
    return {"blocking": bl, "can_hoi": []}


def specs(shots=(1, 2, 3), **over):
    out = [{"shot": s, "muc_dich": "thấy Kelly", "co": "MS", "do_cao": ("ngang", "cao", "thap")[i % 3],
            "thanh_phan": [{"vat": "kelly", "vai": "chinh", "vung": "giua", "thay": "mat"}]} for i, s in enumerate(shots)]
    for s in out:
        s.update(over)
    return {"shot_specs": out}


def review(*verdicts):
    return {"shots": [dict(v) for v in verdicts]}


class PureTests(unittest.TestCase):
    """Bảng đối chiếu + máy trạng thái, không CSDL."""

    def shot10_v2(self):
        # #31 shot 10 (lượt cc_20261016_101134): máy (1.87, -0.50) cao 0,85 m chúc −6,5°, ống 65; xe nôi (0, 0), Kelly (0.65, 0.1)
        objs = {"xenoi": {"key": "xenoi", "kind": "dao_cu", "xy": [0.0, 0.0], "r": 0.5},
                "kelly": {"key": "kelly", "kind": "nguoi", "xy": [0.65, 0.1]}}
        m = {"at": [1.866, -0.496, 0.72], "aim": [0.94, -0.14, 0.61], "lens": 65.0, "cam_above_floor_m": 0.85, "pitch": -6.54,
             "obj": {"kelly": {"seen_pct": 28.6, "size_pct": 237.0}, "xenoi": {"seen_pct": 53.3, "size_pct": 92.9}}}
        spec = {"shot": 10, "co": "CU", "do_cao": "thap", "muc_dich": "cận thấp nhìn lên xe nôi, tay Kelly mép phải khung",
                "thanh_phan": [{"vat": "xenoi", "vai": "chinh", "vung": "trai"}, {"vat": "kelly", "vai": "phu", "vung": "phai"}]}
        return spec, {"shots": [{"shot": 10, "spec": spec, "objs": objs, "best": {"ok": True, "m": m, "clay": "v2_shot10_clay_raw.png"}}]}

    def test_table_catches_shot10_mismatches_as_facts(self):
        spec, v2 = self.shot10_v2()
        rows = sc.compare_table({"shots": [{"shot": 10}]}, [spec], v2)[10]
        text = "\n".join(rows)
        self.assertIn("`kelly` đứng GIỮA máy và `xenoi`", text)       # người chắn vật chính
        self.assertIn("nhìn lên", text)                                 # chữ trong ý đồ …
        self.assertIn("chúc", text)                                     # … ↔ máy chúc đo được
        self.assertIn("đo cỡ 237", text)                                # vai phụ phình to khung
        self.assertIn("Blender: ĐẠT", text)                             # bộ kiểm cũ vẫn đạt — bảng chỉ nêu sự thật, không phán

    def test_declared_che_shown_not_judged(self):
        spec, v2 = self.shot10_v2()
        spec["thanh_phan"][1].update(che="chuyen_canh", ly_do="Kelly lướt qua che máy để chuyển sang shot 11")
        text = "\n".join(sc.compare_table({"shots": []}, [spec], v2)[10])
        self.assertIn("ĐÃ KHAI che `chuyen_canh`", text)

    def run_machine(self, *steps):
        st = sc.new_state("fp")
        calls = []
        measure = lambda bl, sp: (calls.append(1) or (f"crew/m{len(calls)}", {}))
        for obj in steps:
            sc.ingest(st, obj, measure)
        return st, calls

    def test_happy_path_one_measure(self):
        st, calls = self.run_machine(blocking(), specs(), review({"shot": 1, "ket_luan": "khop"}, {"shot": 2, "ket_luan": "khop"},
                                                                 {"shot": 3, "ket_luan": "khop"}))
        self.assertEqual(st["phase"], "duyet")
        self.assertEqual(len(calls), 1)
        sc.ingest(st, {"duyet": True}, None, "nguoi_dung")
        self.assertEqual((st["phase"], st["approved_by"]), ("xong", "nguoi_dung"))

    def test_fix_camera_remeasures_then_cap(self):
        fix = lambda n: {"shot": n, "ket_luan": "sua_may", "ly_do": "x", "shot_spec": dict(specs()["shot_specs"][n - 1], co="MCU")}
        ok = [{"shot": 2, "ket_luan": "khop"}, {"shot": 3, "ket_luan": "khop"}]
        st, calls = self.run_machine(blocking(), specs(), review(fix(1), *ok), review(fix(1), *ok))
        self.assertEqual(len(calls), 3)
        self.assertEqual(st["phase"], "duyet")                          # MAX_REVIEWS: không tự duyệt vòng thứ ba
        self.assertTrue(st["verdicts"]["1"]["chua_duyet_lai"])
        self.assertEqual(st["specs"][0]["nhip"], "n1")                  # nhịp do Đạo diễn chọn, gắn lại vào đặc tả sửa

    def test_director_wins_and_asked_only_once(self):
        ask = {"shot": 1, "ket_luan": "de_nghi_doi_cho", "vat": "kelly", "goi_y_at": [1.0, 0.0], "ly_do": "chắn vật"}
        ok = [{"shot": 2, "ket_luan": "khop"}, {"shot": 3, "ket_luan": "khop"}]
        reply = dict(blocking(), tra_loi=[{"shot": 1, "dong_y": False, "ly_do": "Kelly phải đứng cạnh cũi"}])
        st, calls = self.run_machine(blocking(), specs(), review(ask, *ok), reply, review(ask, *ok))
        self.assertEqual(len(calls), 1)                                 # từ chối → dàn cảnh không đổi → không đo lại
        self.assertIn("1", st["unresolved"])                            # đề nghị lần hai: không hỏi lại, shot chưa giải quyết
        self.assertEqual(st["phase"], "duyet")

    def test_approve_returns_once(self):
        ok = [{"shot": n, "ket_luan": "khop"} for n in (1, 2, 3)]
        st, _ = self.run_machine(blocking(), specs(), review(*ok))
        sc.ingest(st, {"duyet": False, "tra_lai": [{"shot": 2, "y_do": "thấp hơn"}]}, None)
        self.assertEqual(st["phase"], "quay_phim_duyet")
        sc.ingest(st, review(*ok), None)
        sc.ingest(st, {"duyet": False, "tra_lai": [{"shot": 2, "y_do": "vẫn chưa"}]}, None)
        self.assertEqual(st["phase"], "xong")                          # Đạo diễn (API): trần 1 lần trả lại — chặn vòng gọi trả tiền
        self.assertIn("2", st["unresolved"])

    def test_user_returns_unlimited(self):
        # 16/10 #31 cảnh 3: người dùng trả lại lần 2 bị coi là chốt (ghi máy shot 10, gỡ 11–13) — người dùng trả lại bao nhiêu lần cũng được
        ok = [{"shot": n, "ket_luan": "khop"} for n in (1, 2, 3)]
        st, _ = self.run_machine(blocking(), specs(), review(*ok))
        for i in range(3):
            sc.ingest(st, {"duyet": False, "tra_lai": [{"shot": 2, "y_do": f"lần {i + 1}"}]}, None, "nguoi_dung")
            self.assertEqual(st["phase"], "quay_phim_duyet")
            self.assertEqual(st["unresolved"], {})
            self.assertEqual(st["n_returns"], i + 1)
            sc.ingest(st, review(*ok), None)
            self.assertEqual(st["phase"], "duyet")
        sc.ingest(st, {"duyet": True}, None, "nguoi_dung")
        self.assertEqual(st["phase"], "xong")

    def test_user_return_after_director_return(self):
        ok = [{"shot": n, "ket_luan": "khop"} for n in (1, 2, 3)]
        st, _ = self.run_machine(blocking(), specs(), review(*ok))
        st.pop("n_returns", None)                                        # state cũ chưa có khóa
        sc.ingest(st, {"duyet": False, "tra_lai": [{"shot": 2, "y_do": "Đạo diễn"}]}, None, "claude_api")
        sc.ingest(st, review(*ok), None)
        sc.ingest(st, {"duyet": False, "tra_lai": [{"shot": 3, "y_do": "người dùng"}]}, None, "nguoi_dung")
        self.assertEqual((st["phase"], st["unresolved"], st["n_returns"]), ("quay_phim_duyet", {}, 2))
        self.assertEqual(st["notes"], [{"shot": 3, "y_do": "người dùng"}])          # ý đồ lần này, không lẫn lần trước


class CrewDbTests(Base):
    def setUp(self):
        super().setUp()
        p = mock.patch.dict(os.environ, CREW_ON)
        p.start()
        self.addCleanup(p.stop)

    def ctx_inputs(self, pid):
        seg = stage_auto.segments(self.p.conn, pid)[0]
        return seg, stage_auto._crew_ctx(self.p.conn, pid, seg, self.data)["inputs"]

    def test_blocking_validator(self):
        pid = self.project()
        _, inputs = self.ctx_inputs(pid)
        sc.validate_blocking(copy.deepcopy(blocking()), inputs)
        bad = blocking(shots=(1, 2))
        with self.assertRaises(llm_io.SchemaError):
            sc.validate_blocking(bad, inputs)                          # thiếu shot 3
        hid = blocking()
        hid["blocking"]["beats"]["n1"]["kelly"] = {"hidden": True}
        with self.assertRaisesRegex(llm_io.SchemaError, "ẩn"):
            sc.validate_blocking(hid, inputs)                          # nhân vật kịch bản vắng ở nhịp của shot

    def test_specs_validator_nhip_from_director_and_che_reason(self):
        pid = self.project()
        _, inputs = self.ctx_inputs(pid)
        bl = blocking()["blocking"]
        obj = specs(nhip="khac")
        sc.validate_specs(obj, inputs, bl)
        self.assertEqual({s["nhip"] for s in obj["shot_specs"]}, {"n1"})   # Quay phim không đổi được nhịp
        che = specs()
        che["shot_specs"][0]["thanh_phan"][0]["che"] = "chuyen_canh"
        with self.assertRaisesRegex(llm_io.SchemaError, "ly_do"):
            sc.validate_specs(che, inputs, bl)

    def test_prompts_per_role(self):
        pid = self.project()
        seg, inputs = self.ctx_inputs(pid)
        st = sc.new_state("fp")
        p_dir = sc.prompt_for(st, inputs)
        self.assertIn("Bạn là **Đạo diễn**", p_dir)
        self.assertNotIn("## Bộ nguyên tắc Quay phim", p_dir)
        st.update(phase="quay_phim", blocking=blocking()["blocking"])
        p_dp = sc.prompt_for(st, inputs)
        self.assertIn("## Bộ nguyên tắc Quay phim", p_dp)
        self.assertIn("## Dàn cảnh của Đạo diễn", p_dp)

    def test_offline_flow_user_approves_then_applies(self):
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        text, problems, st = stage_auto.crew_prompt(self.p.conn, pid, seg, self.data)
        self.assertEqual(st["phase"], "dao_dien")
        self.assertEqual(problems, [])
        r = stage_auto.crew_answer(self.p.conn, pid, seg, self.data, blocking())
        self.assertEqual((r["ok"], r["phase"]), (True, "quay_phim"))
        r = stage_auto.crew_answer(self.p.conn, pid, seg, self.data, specs())
        self.assertEqual(r["phase"], "quay_phim_duyet")
        text, _, _ = stage_auto.crew_prompt(self.p.conn, pid, seg, self.data)
        self.assertIn("Bảng đối chiếu", text)
        self.assertIn("ảnh clay shot 1", text)
        r = stage_auto.crew_answer(self.p.conn, pid, seg, self.data, review(*[{"shot": n, "ket_luan": "khop"} for n in (1, 2, 3)]))
        self.assertEqual(r["phase"], "duyet")
        _, problems, _ = stage_auto.crew_prompt(self.p.conn, pid, seg, self.data)
        self.assertTrue(any("NGƯỜI DÙNG" in x for x in problems))      # mặc định: người dùng duyệt chốt, không có đề bài Đạo diễn
        self.assertNotIn("stage_camera", self.shot(pid, 1))
        r = stage_auto.crew_user_verdict(self.p.conn, pid, seg, self.data, approve=True)
        self.assertEqual(r["applied"], [1, 2, 3])
        cam = self.shot(pid, 1)["stage_camera"]
        self.assertIn("tổ sân khấu", cam["source"])
        self.assertIn("nguoi_dung", cam["source"])
        res = json.load(open(os.path.join(stage_auto.base_dir(self.data, pid, seg["stage"]), "doan_1", "result.json"), encoding="utf-8"))
        self.assertEqual(res["round"], "crew/final")
        self.assertTrue(stage_auto.result_round(self.data, pid, seg).replace(os.sep, "/").endswith("crew/final"))

    def test_user_returns_twice_db_untouched(self):
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        ok = review(*[{"shot": n, "ket_luan": "khop"} for n in (1, 2, 3)])
        for obj in (blocking(), specs(), ok):
            stage_auto.crew_answer(self.p.conn, pid, seg, self.data, obj)
        before = [self.shot(pid, n) for n in (1, 2, 3)]
        for i in range(2):
            r = stage_auto.crew_user_verdict(self.p.conn, pid, seg, self.data, approve=False,
                                             tra_lai=[{"shot": 2, "y_do": f"lần {i + 1}"}])
            self.assertEqual((r["ok"], r["phase"]), (True, "quay_phim_duyet"))
            self.assertNotIn("applied", r)
            self.assertEqual([self.shot(pid, n) for n in (1, 2, 3)], before)       # chưa duyệt → CSDL không đổi
            r = stage_auto.crew_answer(self.p.conn, pid, seg, self.data, ok)
            self.assertEqual(r["phase"], "duyet")
        r = stage_auto.crew_user_verdict(self.p.conn, pid, seg, self.data, approve=True)
        self.assertEqual(r["applied"], [1, 2, 3])

    def test_bad_answer_keeps_state(self):
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        r = stage_auto.crew_answer(self.p.conn, pid, seg, self.data, specs())    # sai vai: đang chờ Đạo diễn
        self.assertFalse(r["ok"])
        self.assertEqual(stage_auto.crew_prompt(self.p.conn, pid, seg, self.data)[2]["phase"], "dao_dien")

    def test_api_run_uses_crew_and_waits_for_user(self):
        pid = self.project()
        client = FakeClaude(blocking(), specs(), review(*[{"shot": n, "ket_luan": "khop"} for n in (1, 2, 3)]))
        r = stage_auto.run(self.p.conn, pid, self.data, client=client)
        self.assertEqual(len(client.prompts), 3)
        self.assertIn("Bạn là **Đạo diễn**", client.prompts[0])
        self.assertIn("Bạn là **Quay phim**", client.prompts[1])
        self.assertEqual(r["applied"], [])
        self.assertEqual(len(r["held"]), 1)                             # một dòng: chờ người dùng duyệt cả đoạn
        self.assertIn("chờ người dùng duyệt", r["held"][0][1])
        seg = stage_auto.segments(self.p.conn, pid)[0]
        stage_auto.crew_user_verdict(self.p.conn, pid, seg, self.data, approve=True)
        self.assertIn("stage_camera", self.shot(pid, 2))

    def test_api_run_director_approves_when_user_flag_off(self):
        pid = self.project()
        ok = review(*[{"shot": n, "ket_luan": "khop"} for n in (1, 2, 3)])
        client = FakeClaude(blocking(), specs(), ok, {"duyet": True})
        with mock.patch.dict(os.environ, {"FEATURE_STAGE_CREW_USER_APPROVE": "0"}):
            self.assertFalse(sc.user_approves())
            r = stage_auto.run(self.p.conn, pid, self.data, client=client)
        self.assertEqual(r["applied"], [1, 2, 3])
        self.assertEqual(len(client.prompts), 4)
        stage_auto.run(self.p.conn, pid, self.data, client=client)
        self.assertEqual(len(client.prompts), 4)                        # cùng đầu vào: dùng kết quả đã lưu

    def test_flag_off_keeps_single_role(self):
        pid = self.project()
        from tests.test_stage_auto import answer
        client = FakeClaude(answer([1, 2, 3]))
        with mock.patch.dict(os.environ, {"FEATURE_STAGE_CREW": "0"}):
            r = stage_auto.run(self.p.conn, pid, self.data, client=client)
        self.assertEqual(r["applied"], [1, 2, 3])
        self.assertIn("Đạo diễn kiêm Quay phim", client.prompts[0])

    def test_estimate_crew(self):
        pid = self.project()
        with mock.patch.object(stage_auto, "crew_usd", side_effect=lambda conn, worst=False: 2.0 if worst else 0.5):
            est = stage_auto.estimate(self.p.conn, pid, self.data)
        self.assertTrue(est["crew"])
        self.assertEqual((est["usd"], est["usd_max"]), (0.5, 2.0))


class ReviewFixTests(Base):
    """Rà quy ước 7 (16/10): lỗi đã sửa — không trả tiền lặp, duyệt chốt chỉ người dùng, lượt duyệt sau trả lời, rerender, ảnh, đoạn
    chờ duyệt, C1 khi vật trục ẩn."""

    def setUp(self):
        super().setUp()
        p = mock.patch.dict(os.environ, CREW_ON)
        p.start()
        self.addCleanup(p.stop)

    def test_bad_json_not_paid_again(self):
        pid = self.project()
        client = FakeClaude({"khong": "dung"})
        stage_auto.run(self.p.conn, pid, self.data, client=client)
        n = len(client.prompts)
        self.assertEqual(n, 2)                                          # một lượt + hỏi lại một lần
        stage_auto.run(self.p.conn, pid, self.data, client=client)
        self.assertEqual(len(client.prompts), n)                        # cùng đầu vào: không gọi lại

    def test_blender_error_keeps_state_and_not_paid_again(self):
        pid = self.project()
        client = FakeClaude(blocking(), specs())
        with mock.patch.object(stage_auto.tool(), "v2_run", side_effect=RuntimeError("Blender hỏng")):
            r = stage_auto.run(self.p.conn, pid, self.data, client=client)
        self.assertTrue(r["held"])
        seg = stage_auto.segments(self.p.conn, pid)[0]
        st = stage_auto._crew_load(stage_auto._crew_ctx(self.p.conn, pid, seg, self.data))
        self.assertEqual((st["phase"], st["specs"]), ("quay_phim", None))   # đo lỗi: state không bị sửa nửa vời
        stage_auto.run(self.p.conn, pid, self.data, client=client)
        self.assertEqual(len(client.prompts), 2)

    def offline_to_duyet(self, pid, seg):
        stage_auto.crew_answer(self.p.conn, pid, seg, self.data, blocking())
        stage_auto.crew_answer(self.p.conn, pid, seg, self.data, specs())
        stage_auto.crew_answer(self.p.conn, pid, seg, self.data, review(*[{"shot": n, "ket_luan": "khop"} for n in (1, 2, 3)]))

    def test_only_user_approves(self):
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        self.offline_to_duyet(pid, seg)
        r = stage_auto.crew_answer(self.p.conn, pid, seg, self.data, {"duyet": True}, source="claude_code")
        self.assertFalse(r["ok"])
        self.assertIn("người dùng", r["errors"][0])
        self.assertNotIn("stage_camera", self.shot(pid, 1))
        r = stage_auto.crew_user_verdict(self.p.conn, pid, seg, self.data, approve=True)
        self.assertEqual(r["result"]["nguon"], "claude_code")          # nguồn = người làm việc, không phải người duyệt
        self.assertEqual(r["result"]["usd"], 0.0)

    def test_rerender_after_crew(self):
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        self.offline_to_duyet(pid, seg)
        stage_auto.crew_user_verdict(self.p.conn, pid, seg, self.data, approve=True)
        out = stage_auto.rerender(self.p.conn, pid, seg, self.data)
        self.assertEqual(out["missing"], [])
        res = json.load(open(os.path.join(stage_auto.base_dir(self.data, pid, seg["stage"]), "doan_1", "result.json"), encoding="utf-8"))
        self.assertEqual(res["round"], "crew/final")
        self.assertIn("crew", res)

    def test_images_limited_not_silent(self):
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        stage_auto.crew_answer(self.p.conn, pid, seg, self.data, blocking())
        stage_auto.crew_answer(self.p.conn, pid, seg, self.data, specs())
        ctx = stage_auto._crew_ctx(self.p.conn, pid, seg, self.data)
        _, extra, imgs = stage_auto._crew_view(ctx, stage_auto._crew_load(ctx), limit=2)
        self.assertEqual(len(imgs), 2)
        self.assertTrue(any("KHÔNG gửi kèm" in x for x in extra))

    def test_waiting_segment_blocks_next_on_same_stage(self):
        pid = self.project(scenes=((1, "giua_phong"), (1, "giua_phong"), (1, "giua_phong"), (2, "giua_phong")))
        client = FakeClaude(blocking(shots=(1, 2, 3)), specs(shots=(1, 2, 3)),
                            review(*[{"shot": n, "ket_luan": "khop"} for n in (1, 2, 3)]))
        r = stage_auto.run(self.p.conn, pid, self.data, client=client)
        self.assertEqual(len(client.prompts), 3)                        # đoạn 2 không gọi Claude trên vị trí chưa chốt
        self.assertTrue(any("chờ người dùng duyệt đoạn trước" in line for _, line in r["held"]))

    def test_request_then_reply_gives_one_more_review(self):
        st = sc.new_state("fp")
        measure = lambda bl, sp: ("crew/m1", {})
        ok = [{"shot": n, "ket_luan": "khop"} for n in (2, 3)]
        ask = {"shot": 1, "ket_luan": "de_nghi_doi_cho", "vat": "kelly", "goi_y_at": [1.0, 0.0], "ly_do": "chắn"}
        for obj in (blocking(), specs(), review({"shot": 1, "ket_luan": "khop"}, *ok)):
            sc.ingest(st, obj, measure)
        st["phase"], st["reviews"] = "quay_phim_duyet", 1                # lượt duyệt thứ hai đề nghị dời người
        sc.ingest(st, review(ask, *ok), measure)
        sc.ingest(st, dict(blocking(), tra_loi=[{"shot": 1, "dong_y": False, "ly_do": "giữ"}]), measure)
        self.assertEqual(st["phase"], "quay_phim_duyet")                # vẫn có một lượt để làm với chỗ đứng đó

    def test_c1_ignored_when_axis_object_hidden(self):
        from core import stage_solver as ss
        bl = {"objects": [{"key": "kelly", "kind": "nguoi", "at": [0.0, 0.0], "H": 1.7, "facing": 0},
                          {"key": "xe", "kind": "dao_cu", "at": [1.0, 0.0], "h": 1.0, "d": 0.6}],
              "beats": {"n2": {"xe": {"hidden": True}}}, "axis": ["kelly", "xe"], "s0": "right"}
        sp = [{"shot": 1, "nhip": "n2", "co": "MS", "do_cao": "ngang",
               "thanh_phan": [{"vat": "kelly", "vai": "chinh", "vung": "giua", "thay": "mat"}]}]
        sol = ss.solve_scene(sp, bl, 9 / 16)
        self.assertTrue(any(c["c1_ok"] for c in sol["shots"][0]["cams"]))


class OptimizeTests(Base):
    """Tối ưu 16/10 (bản đánh giá mục 3): đo lại chỉ shot đổi, khóa lần đo đã duyệt / chốt lần tốt nhất, s0 của Quay phim, giữ phía máy."""

    def setUp(self):
        super().setUp()
        p = mock.patch.dict(os.environ, CREW_ON)
        p.start()
        self.addCleanup(p.stop)

    def run_to_review(self, pid, seg, s0=None):
        stage_auto.crew_answer(self.p.conn, pid, seg, self.data, blocking())
        sp = specs()
        if s0:
            sp["s0"] = s0
        return stage_auto.crew_answer(self.p.conn, pid, seg, self.data, sp)

    def state(self, pid, seg):
        return stage_auto._crew_load(stage_auto._crew_ctx(self.p.conn, pid, seg, self.data))

    def test_only_changed_shot_remeasured_with_near(self):
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        self.run_to_review(pid, seg)
        calls = []
        real = stage_auto.tool().v2_run.side_effect
        stage_auto.tool().v2_run.side_effect = lambda bl, sp, *a, **k: (calls.append(copy.deepcopy(sp)), real(bl, sp, *a, **k))[1]
        fix = dict(specs()["shot_specs"][1], co="MS", do_cao="thap")
        stage_auto.crew_answer(self.p.conn, pid, seg, self.data, review({"shot": 1, "ket_luan": "khop"},
                               {"shot": 2, "ket_luan": "sua_may", "ly_do": "x", "shot_spec": fix}, {"shot": 3, "ket_luan": "khop"}))
        self.assertEqual([s["shot"] for s in calls[0]], [2])            # chỉ đo lại shot 2
        self.assertIn("_near", calls[0][0])                             # giữ phía máy lần đo trước
        st = self.state(pid, seg)
        self.assertEqual(st["shot_measure"], {"1": "crew/m1", "2": "crew/m2", "3": "crew/m1"})
        self.assertEqual(st["accepted"], {"1": "crew/m1", "3": "crew/m1"})
        text, _, _ = stage_auto.crew_prompt(self.p.conn, pid, seg, self.data)
        self.assertIn("số đo giữ từ lần đo crew/m1", text)

    def test_finalize_picks_accepted_not_latest(self):
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        self.run_to_review(pid, seg)
        ok = [{"shot": 2, "ket_luan": "khop"}, {"shot": 3, "ket_luan": "khop"}]
        stage_auto.crew_answer(self.p.conn, pid, seg, self.data, review({"shot": 1, "ket_luan": "khop"}, *ok))
        st = self.state(pid, seg)
        self.assertEqual(st["phase"], "duyet")
        r = stage_auto.crew_user_verdict(self.p.conn, pid, seg, self.data, approve=True)
        self.assertEqual(r["result"]["crew"]["picked"], {"1": "crew/m1", "2": "crew/m1", "3": "crew/m1"})
        self.assertIn("crew", self.shot(pid, 1)["stage_camera"]["guide"].replace(os.sep, "/"))

    def test_best_measure_when_not_accepted(self):
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        self.run_to_review(pid, seg)
        ctx = stage_auto._crew_ctx(self.p.conn, pid, seg, self.data)
        st = self.state(pid, seg)
        st["shot_hist"] = {"1": ["crew/m1", "crew/m9"]}
        good, bad = {"best": {"ok": True, "check": {"fail": []}}}, {"best": {"ok": False, "check": {"fail": ["P3"]}}}
        with mock.patch.object(stage_auto, "_crew_v2", side_effect=lambda c, rel: {1: good if rel == "crew/m1" else bad}):
            self.assertEqual(stage_auto._crew_pick(ctx, st, "1"), "crew/m1")   # lần sau (m9) xấu hơn → giữ m1

    def test_s0_from_dp_and_director_s0_ignored(self):
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        bl = blocking()
        bl["blocking"]["s0"] = "left"                                   # Đạo diễn ghi s0 (cũ) → không dùng
        stage_auto.crew_answer(self.p.conn, pid, seg, self.data, bl)
        seen = []
        real = stage_auto.tool().v2_run.side_effect
        stage_auto.tool().v2_run.side_effect = lambda b, sp, *a, **k: (seen.append(b.get("s0")), real(b, sp, *a, **k))[1]
        sp = specs()
        sp["s0"] = "right"
        stage_auto.crew_answer(self.p.conn, pid, seg, self.data, sp)
        self.assertEqual(seen, ["right"])
        bad = specs()
        bad["s0"] = "trai"
        with self.assertRaises(llm_io.SchemaError):
            sc.validate_specs(bad, self.state_inputs(pid, seg), blocking()["blocking"])

    def test_waived_rule_gives_camera(self):
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        self.run_to_review(pid, seg)
        real = stage_auto._crew_v2

        def p2(ctx, rel):
            out = real(ctx, rel)
            out[1]["best"].update(ok=False, check={"ok": False, "fail": ["P2"], "why": {"P2": "mép bậc"}, "phu": {}, "miss": 0.0})
            return out
        with mock.patch.object(stage_auto, "_crew_v2", side_effect=p2):
            stage_auto.crew_answer(self.p.conn, pid, seg, self.data, review(
                {"shot": 1, "ket_luan": "giu_lech", "ly_do": "mép bậc thấp ở tiền cảnh", "bo_luat": ["P2"]},
                {"shot": 2, "ket_luan": "khop"}, {"shot": 3, "ket_luan": "khop"}))
            r = stage_auto.crew_user_verdict(self.p.conn, pid, seg, self.data, approve=True)
        self.assertIn(1, r["applied"])
        self.assertIn("miễn P2", self.shot(pid, 1)["stage_camera"]["source"])

    def state_inputs(self, pid, seg):
        return stage_auto._crew_ctx(self.p.conn, pid, seg, self.data)["inputs"]


class OptimizeFixTests(unittest.TestCase):
    """Rà quy ước 7 của tối ưu 16/10 (máy trạng thái thuần): lịch sử đo xóa khi đổi dàn cảnh / s0, shot không ra phương án không dùng lặng
    số đo cũ, lần đo bị bác, doi_phia một lần, lan_do / bo_luat."""

    def setUp(self):
        self.n = 0

    def measure(self, bl, sp, drop=()):
        self.n += 1
        return f"crew/m{self.n}", {"s0": "left", "shots": [{"shot": x["shot"], "best": {"m": {"at": [1.0, 2.0, 1.5]}}}
                                                         for x in sp if x["shot"] not in drop]}

    def to_review(self):
        st = sc.new_state("fp")
        sc.ingest(st, blocking(), self.measure)
        sc.ingest(st, specs(), self.measure)
        return st

    def test_s0_taken_from_first_full_measure(self):
        st = self.to_review()
        self.assertEqual(st["s0"], "left")

    def test_s0_change_resets_history(self):
        st = self.to_review()
        ok = [{"shot": n, "ket_luan": "khop"} for n in (1, 2, 3)]
        sc.ingest(st, dict(review(*ok), s0="right"), self.measure)
        self.assertEqual(st["shot_hist"], {"1": ["crew/m2"], "2": ["crew/m2"], "3": ["crew/m2"]})
        self.assertEqual(st["accepted"], {})

    def test_missing_shot_not_silently_old(self):
        st = self.to_review()
        fix = dict(specs()["shot_specs"][1], co="MS", do_cao="thap", doi_phia=True)
        m = lambda bl, sp: self.measure(bl, sp, drop=(2,))
        sc.ingest(st, review({"shot": 1, "ket_luan": "khop"}, {"shot": 2, "ket_luan": "sua_may", "ly_do": "x", "shot_spec": fix},
                             {"shot": 3, "ket_luan": "khop"}), m)
        self.assertNotIn("2", st["shot_measure"])
        self.assertIn("2", st["measure_errors"])
        self.assertEqual(st["rejected"], {"2": ["crew/m1"]})
        self.assertNotIn("doi_phia", st["specs"][1])                         # doi_phia chỉ áp một lần đo

    def test_lan_do_and_bo_luat_validation(self):
        st = self.to_review()
        inputs = {"shots": [{"shot": n} for n in (1, 2, 3)]}
        with self.assertRaises(llm_io.SchemaError):
            sc.validate_review(review({"shot": 1, "ket_luan": "giu_lech", "ly_do": "x", "bo_luat": ["P1"]},
                                      {"shot": 2, "ket_luan": "khop"}, {"shot": 3, "ket_luan": "khop"}), st, inputs)
        with self.assertRaises(llm_io.SchemaError):
            sc.validate_review(review({"shot": 1, "ket_luan": "khop", "lan_do": "crew/m9"},
                                      {"shot": 2, "ket_luan": "khop"}, {"shot": 3, "ket_luan": "khop"}), st, inputs)
        sc.ingest(st, review({"shot": 1, "ket_luan": "giu_lech", "ly_do": "mép bậc thấp tiền cảnh", "bo_luat": ["P2"], "lan_do": "crew/m1"},
                             {"shot": 2, "ket_luan": "khop"}, {"shot": 3, "ket_luan": "khop"}), self.measure)
        self.assertEqual((st["accepted"]["1"], st["waive"]["1"]), ("crew/m1", ["P2"]))


class SolverNearTests(unittest.TestCase):
    def test_near_ranks_same_side_first_among_equals(self):
        from core import stage_solver as ss
        mk = lambda ok, flip, nfail: {"check": {"ok": ok, "fail": ["P3"] * nfail, "miss": 0.0, "phu": {}}, "c1_ok": True, "flip": flip,
                                      "fallback": False}
        far_bad, near_bad, near_worse = mk(False, True, 1), mk(False, False, 1), mk(False, False, 3)
        self.assertEqual(sorted([far_bad, near_bad], key=ss._rank)[0], near_bad)    # ca thử m4: cùng hỏng → giữ phía cũ
        self.assertEqual(sorted([far_bad, near_worse], key=ss._rank)[0], near_worse)  # phía cũ trước cả khi ít lỗi hơn ở phía kia
        far_ok = mk(True, True, 0)
        self.assertEqual(sorted([near_bad, far_ok], key=ss._rank)[0], far_ok)        # phương án ĐẠT luôn thắng

    def test_flip_flag_computed_from_near(self):
        from core import stage_solver as ss
        objs = ss.objects_from_blocking({"objects": [{"key": "kelly", "kind": "nguoi", "at": [0.0, 0.0], "H": 1.7, "facing": 0}]})
        spec = {"shot": 1, "co": "MS", "do_cao": "ngang", "thanh_phan": [{"vat": "kelly", "vai": "chinh", "vung": "giua", "thay": "mat"}]}
        cams = ss.solve_shot(dict(spec, _near=[0.0, 5.0]), objs, 9 / 16)["cams"]      # mặt hướng Bắc → máy phía Bắc
        self.assertTrue(cams and not cams[0]["flip"])
        cams = ss.solve_shot(dict(spec, _near=[0.0, -5.0]), objs, 9 / 16)["cams"]
        self.assertTrue(all(c["flip"] for c in cams if c["at"][1] > 0.5))


class FlagTests(unittest.TestCase):
    def test_registered(self):
        self.assertTrue(features.FEATURES["stage_crew"]["costs"])
        self.assertFalse(features.FEATURES["stage_crew"].get("default_on"))
        self.assertTrue(features.FEATURES["stage_crew_user_approve"]["default_on"])
        self.assertEqual(features.REQUIRES["stage_crew"], ("stage_auto",))
        for stage, _ in sc.ROLES.values():
            from core import cost, llm_runner
            self.assertIn(stage, llm_runner.STAGE_SETTINGS)
            self.assertIn(stage, cost.LLM_STAGE_TOKENS)


if __name__ == "__main__":
    unittest.main()
