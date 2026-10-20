"""V3.1 M1.6 — ước tính giá ĐÚNG gói gửi (cờ send_estimate, TẮT mặc định; A7–A9 #33, G31 #31).

Hiệu chuẩn (docs/V3_1_GOI_SUA_VA_RUI_RO_2026-10-20.md mục 5 — task ClipAI GET, 0 USD; KHÔNG đổi data/pricing.json, không đổi bảng
SEEDANCE_USD_PER_1K_TOKENS): 2 điểm tiền thật — nháp Seedance 2.5 480p 9:16 có video vào 9 s (1,150336 USD / task, 179 740 token;
3 task cùng loại) và bước nâng 1080p của nó (6,364575 USD, 909 225 token). Giây video vào ≈ 9,706 s suy từ token nháp; token 1080p
dùng lại số đó làm phép kiểm ĐỘC LẬP công thức token. Ca 3 = một lần gửi `video_num: 2` (2 nháp, 2,300672 USD; ClipAI ước 2,52).
Không gọi dịch vụ tốn tiền."""
import inspect
import os
import sys
import unittest
from unittest import mock

from core import cost, model_router, quality_tier as qt
from tests.test_cost_route_e1 import ON, Base

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

FLAG_ON = mock.patch.dict(os.environ, {"FEATURE_SEND_ESTIMATE": "1"})
FLAG_OFF = mock.patch.dict(os.environ, {"FEATURE_SEND_ESTIMATE": "0"})
REF_S = 9.706                      # giây video vào suy từ 179 740 token nháp 480p 9:16 (9 s ra)
REAL_DRAFT, REAL_UPGRADE, REAL_PAIR = 1.150336, 6.364575, 2 * 1.150336
TOL = 0.10                         # kế hoạch V3.1 M1.6–M1.7: lệch ước tính ≤ 10 % khi đủ dữ liệu giá


def rel(est, real):
    return abs(est - real) / real


class Calibration(unittest.TestCase):
    def test_token_formula_matches_both_billed_tasks(self):
        self.assertLess(rel(cost.seedance_tokens("480p", "9:16", 9, REF_S), 179740), 0.001)
        self.assertLess(rel(cost.seedance_tokens("1080p", "9:16", 9, REF_S), 909225), 0.001)   # kiểm độc lập (số giây lấy từ 480p)

    def test_draft_480p_with_video_input_within_10_percent(self):
        est = cost.seedance_estimate(qt.SAMPLE_MODEL, "480p", "9:16", 9, REF_S)
        self.assertLess(rel(est, REAL_DRAFT), TOL, est)

    def test_two_draft_send_within_10_percent(self):
        est = 2 * cost.seedance_estimate(qt.SAMPLE_MODEL, "480p", "9:16", 9, REF_S)
        self.assertLess(rel(est, REAL_PAIR), TOL, est)

    def test_1080p_upgrade_counts_the_video_input(self):
        with FLAG_OFF:                     # cũ: giá đo #24 (không video vào) → thấp ~26 % (A7 "sổ chi cao hơn ~24 %")
            old = qt.upgrade_price("9:16", 9, REF_S)
        self.assertGreater(rel(old, REAL_UPGRADE), TOL)
        with FLAG_ON:
            new = qt.upgrade_price("9:16", 9, REF_S)
            self.assertLess(rel(new, REAL_UPGRADE), TOL, new)
            self.assertEqual(qt.upgrade_price("9:16", 9), old)          # không video vào → giá đo #24 như cũ

    def test_upgrade_input_seconds_is_zero_with_the_flag_off(self):
        with FLAG_OFF, mock.patch.object(cost, "video_reference_seconds") as probe:
            self.assertEqual(qt.upgrade_input_seconds(None, 1), 0.0)
        probe.assert_not_called()


class ButtonPricesWhatIsSent(Base):
    REF = {"seconds": REF_S, "warnings": []}

    def test_batch_button_adds_the_reference_video_like_the_card(self):
        # A7: nút gom (estimate_videos_by_scene) tính bảng giá, thẻ shot (clip_estimate) tính token có ref — hai số khác nhau
        with ON, mock.patch.object(cost, "video_reference_seconds", return_value=self.REF):
            with FLAG_OFF:
                old = cost.estimate_videos_by_scene(self.p, self.pid, cost.load_pricing())["min"]
            with FLAG_ON:
                new = cost.estimate_videos_by_scene(self.p, self.pid, cost.load_pricing())["min"]
                card = cost.clip_estimate(self.p.conn, self.s1)
        want = max(cost.seedance_estimate(qt.SAMPLE_MODEL, "480p", "9:16", 4.0, REF_S),
                   cost.clip_price(cost.load_pricing(), qt.SAMPLE_MODEL, "480p", 4.0) or 0.0)
        self.assertAlmostEqual(new, want, places=6)
        self.assertAlmostEqual(card, want, places=6)
        self.assertNotAlmostEqual(old, want, places=3)

    def test_a_draft_first_shot_is_priced_at_the_draft_tier(self):
        # A8: lựa chọn không ghi độ phân giải → cũ lấy mức hồ sơ model (720p); gửi thật là nháp 480p (batch._draft_tier)
        choice = {"model": "seedance-2.5", "resolution": None, "e1": "draft_first"}
        with ON, mock.patch.object(model_router, "scene_choice", return_value=choice), \
                mock.patch.object(cost, "video_reference_seconds", return_value={"seconds": 0.0, "warnings": []}):
            with FLAG_OFF:
                old = cost.estimate_videos_by_scene(self.p, self.pid, cost.load_pricing())["min"]
            with FLAG_ON:
                new = cost.estimate_videos_by_scene(self.p, self.pid, cost.load_pricing())["min"]
        table = cost.clip_price(cost.load_pricing(), qt.SAMPLE_MODEL, "480p", 4.0) or 0.0
        self.assertAlmostEqual(new, max(cost.seedance_estimate(qt.SAMPLE_MODEL, "480p", "9:16", 4.0, 0.0), table), places=6)
        self.assertGreater(old, new)

    def test_final_estimate_upgrade_includes_the_reference_video(self):
        with ON, mock.patch.object(cost, "video_reference_seconds", return_value=self.REF):
            self.approved_draft()
            with FLAG_OFF:
                old = qt.final_estimate(self.p.conn, self.pid)["usd"]
            with FLAG_ON:
                new = qt.final_estimate(self.p.conn, self.pid)["usd"]
        self.assertGreater(new, old)


class FlagOffAndFloor(Base):
    def test_flag_off_is_exactly_the_old_function(self):
        # rà quy ước 7: cờ TẮT = số cũ — so với chính hàm khi send_estimate_on bị ép False (không nhánh mới nào chạy)
        with ON, FLAG_OFF, mock.patch.object(cost, "video_reference_seconds", return_value={"seconds": REF_S, "warnings": []}):
            a = (cost.estimate_videos_by_scene(self.p, self.pid, cost.load_pricing()), cost.clip_estimate(self.p.conn, self.s1))
            with mock.patch.object(cost, "send_clip_usd", side_effect=AssertionError("nhánh mới chạy khi cờ tắt")):
                b = (cost.estimate_videos_by_scene(self.p, self.pid, cost.load_pricing()), cost.clip_estimate(self.p.conn, self.s1))
        self.assertEqual(a, b)

    def test_never_under_the_price_table(self):
        # rà quy ước 7 (MED): Seedance 2.0 480p — bảng giá 0,75 / 5 s > công thức 0,34 → không được hạ giá khi bật cờ
        choice = {"model": "seedance", "resolution": "480p"}
        with ON, FLAG_ON, mock.patch.object(model_router, "scene_choice", return_value=choice), \
                mock.patch.object(cost, "video_reference_seconds", return_value={"seconds": 0.0, "warnings": []}):
            got = cost.send_clip_usd(self.p.conn, self.s1, cost.load_pricing(), 5)
        from core.adapters.clipai import effective_duration, resolve_model
        canonical, family = resolve_model("seedance")
        table = cost.clip_price(cost.load_pricing(), canonical, "480p", effective_duration(canonical, family, 5))
        self.assertGreaterEqual(got, table or 0.0)


class ClaudeCliIsFree(unittest.TestCase):
    def test_claude_cli_costs_nothing_only_with_the_flag(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "claude_cli"}):
            with FLAG_OFF:
                self.assertGreater(cost.llm_call_usd(None, "qc") or 0, 0)
            with FLAG_ON:
                self.assertEqual(cost.llm_call_usd(None, "qc"), 0.0)
                self.assertTrue(cost.claude_free())

    def test_anthropic_api_keeps_its_price(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "anthropic"}), FLAG_ON:
            self.assertFalse(cost.claude_free())
            self.assertGreater(cost.llm_call_usd(None, "qc") or 0, 0)


class PregenCheckPricesVideo(Base):
    def test_check_reads_the_video_button_function_and_never_blocks_on_it(self):
        import pregen_check
        src = inspect.getsource(pregen_check.video_prices)
        self.assertIn("cost.estimate_videos_by_scene(pipe, pid, cost.load_pricing())", src)
        self.assertIn("quality_tier.final_estimate(pipe.conn, pid)", src)
        self.assertNotIn("video", inspect.getsource(pregen_check.check).split('"blocked"')[1])
        with ON, FLAG_ON, mock.patch.object(cost, "video_reference_seconds", return_value={"seconds": REF_S, "warnings": []}):
            out = pregen_check.video_prices(self.p, self.pid)
        self.assertTrue(out["send_estimate"])
        self.assertEqual(out["estimate"]["items"], 1)
        self.assertIn("ước tính", out["text"])

    def test_a_video_price_error_is_said_not_hidden(self):
        import pregen_check
        with mock.patch.object(cost, "estimate_videos_by_scene", side_effect=RuntimeError("hỏng")):
            out = pregen_check.video_prices(self.p, self.pid)
        self.assertIn("không tính được giá video (RuntimeError: hỏng)", out["text"])


if __name__ == "__main__":
    unittest.main()
