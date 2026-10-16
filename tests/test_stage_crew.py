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
        self.assertEqual(st["phase"], "xong")
        self.assertIn("2", st["unresolved"])


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
        self.assertEqual(res["round"], "crew/m1")
        self.assertEqual(stage_auto.result_round(self.data, pid, seg).replace(os.sep, "/")[-7:], "crew/m1")

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
        self.assertEqual(res["round"], "crew/m1")
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
