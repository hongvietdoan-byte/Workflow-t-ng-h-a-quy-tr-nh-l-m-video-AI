"""Lỗi #34 (24/10): N5 "Dựng tấm ghép" khi chưa có lượt lưu lấy lặng lần đo ĐẦY ĐỦ ĐẦU (crew/m1), bỏ qua lần đo sửa máy sau (crew/m3)
và lựa chọn N14 — EP duyệt nhìn máy cũ trong khi N6 ghi máy lần đo mới. Tấm ghép phải ghép TỪNG SHOT theo đúng lần đo N6 chốt.
Blender / vẽ giả (khung DeskBase), không gọi API, CSDL + thư mục tạm."""
import json
import os

from core import stage_auto, stage_desk as D
from tests.test_stage_crew import blocking, review, specs
from tests.test_v31_m48_desk_core import EP, HUMAN, DeskBase


def _fix(n):
    return {"shot": n, "ket_luan": "sua_may", "ly_do": "x", "shot_spec": dict(specs()["shot_specs"][n - 1], co="MS", do_cao="thap")}


OK23 = [{"shot": 2, "ket_luan": "khop"}, {"shot": 3, "ket_luan": "khop"}]


class SheetPicksTests(DeskBase):
    def to_m3(self):
        """m1 = lần đo đầy đủ; m2, m3 = Quay phim sửa máy CHỈ shot 1 → phase duyet (chờ EP)."""
        self.answer(blocking(), specs(), review(_fix(1), *OK23), review(_fix(1), *OK23))
        st = self.crew_state()
        self.assertEqual((st["phase"], st["full_measure"], st["measure"]), ("duyet", "crew/m1", "crew/m3"))
        self.assertEqual(st["shot_hist"]["2"], ["crew/m1"])

    def sheet(self):
        """(lần đo từng shot của thư mục tấm ghép đã vẽ, tiêu đề, kết quả N5)."""
        pr = self.bg(D.build_sheet(self.p.conn, self.pid, self.data, "1", HUMAN))
        self.assertEqual(pr["state"], "done", pr)
        rd, title, _out = stage_auto.tool().stage_sheet.call_args.args
        with open(os.path.join(rd, "v2.json"), encoding="utf-8") as f:
            v2 = json.load(f)
        rel = os.path.relpath(rd, D.seg_dir(self.data, self.pid, self.seg)).replace(os.sep, "/")
        got = v2.get("picked") or {str(s["shot"]): rel for s in v2.get("shots") or []}   # cả thư mục = một lần đo (đường cũ)
        return got, title, pr["result"]

    def approved_picks(self):
        r = D.approve(self.p.conn, self.pid, self.data, "1", HUMAN, EP)
        self.assertTrue(r["ok"], r)
        with open(os.path.join(D.seg_dir(self.data, self.pid, self.seg), "result.json"), encoding="utf-8") as f:
            return json.load(f)["crew"]["picked"]

    def test_partial_remeasure_uses_m3_for_shot1_and_m1_for_the_rest(self):
        self.to_m3()
        got, title, res = self.sheet()
        self.assertEqual(got, {"1": "crew/m3", "2": "crew/m1", "3": "crew/m1"})
        self.assertIn("1←m3", title)
        self.assertEqual(res["lan_do"], got)
        self.assertTrue(any("shot 1 ← crew/m3" in n for n in res["notes"]), res["notes"])
        self.assertEqual(self.approved_picks(), got)                        # đúng máy N6 ghi

    def test_n14_pick_wins(self):
        self.to_m3()
        r = D.crew_user_pick(self.p.conn, self.pid, self.data, "1", 1, "crew/m2", who=HUMAN, user=EP)
        self.assertTrue(r["ok"], r)
        got, title, _ = self.sheet()
        self.assertEqual(got, {"1": "crew/m2", "2": "crew/m1", "3": "crew/m1"})
        self.assertIn("1←m2", title)
        self.assertEqual(self.approved_picks(), got)

    def test_shot_without_a_measure_is_reported(self):
        self.to_m3()
        path = os.path.join(D.seg_dir(self.data, self.pid, self.seg), "crew", "state.json")
        st = self.crew_state()
        st["shot_measure"].pop("2")
        st["measure_errors"] = {"2": "lần đo crew/m3: bộ giải không đặt được máy"}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False)
        got, _, res = self.sheet()
        self.assertNotIn("2", got)
        self.assertTrue(any(n.startswith("shot 2: không xác định được lần đo") for n in res["notes"]), res["notes"])
