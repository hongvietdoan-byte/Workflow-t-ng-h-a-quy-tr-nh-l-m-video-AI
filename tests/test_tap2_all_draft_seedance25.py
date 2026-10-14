"""Quyết định người dùng 13/10 (tập 2 #27): video HẾT Seedance 2.5, mọi shot đi nháp 480p → duyệt → bản cao 1080p (bỏ E1 "shot dễ gen
thẳng"); Seedance 2.0 / 2.0 Fast không còn được đề xuất; Kling chỉ là đường lùi khi Seedance từ chối (bộ lọc người thật — runner tự
chuyển, VideoRunner._on_refused). Ghi đè của người (motion_prompts.quality_path / video_model) vẫn thắng. Shot đã có job gen thẳng đang
chạy / đã duyệt không bị đổi tuyến giữa chừng. Không gọi dịch vụ tốn tiền."""
import unittest

from core import cost, model_router, quality_tier
from tests.test_cost_route_e1 import OFF, ON, Base


class AutoPathIsAlwaysDraftFirst(Base):
    N = 2

    def test_easy_label_goes_draft_first(self):
        self.label("easy")
        with ON:
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")
            ch = model_router.scene_choice(self.p.conn, self.s1)
            self.assertEqual((ch["model"], ch["resolution"], ch["e1"]), ("seedance-2.5", "480p", "draft_first"))
            jid = self.p.create_job(self.s1, "video_gen")
            self.assertEqual(self.p.job(jid)["quality_tier"], "draft")

    def test_no_label_and_easy_cross_check_goes_draft_first(self):
        import json
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"characters": ["A"]}), self.s1))
        self.p.conn.commit()
        with ON:
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")

    def test_person_direct_override_still_wins(self):
        self.label("easy")
        quality_tier.set_path(self.p.conn, self.s1, "direct")
        with ON:
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "direct")

    def test_an_approved_direct_clip_keeps_its_route(self):
        self.label("easy")
        jid = self.p.create_job(self.s1, "video_gen")
        self.p.conn.execute("UPDATE jobs SET quality_tier='direct' WHERE id=?", (jid,))
        self.p.conn.commit()
        self.p.start(jid)
        with ON:                                    # running: the job is not switched to a draft mid-way
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "direct")
        self.p.succeed(jid)
        self.p.approve(jid, "user")
        with ON:                                    # approved 720p direct: no forced regen, route stays
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "direct")
            self.assertEqual(quality_tier.final_estimate(self.p.conn, self.pid)["scenes"][0]["scene_id"], self.sids[1])

    def test_a_rejected_direct_clip_goes_draft_first_next_time(self):
        self.label("easy")
        jid = self.p.create_job(self.s1, "video_gen")
        self.p.conn.execute("UPDATE jobs SET quality_tier='direct' WHERE id=?", (jid,))
        self.p.conn.commit()
        self.p.start(jid)
        self.p.succeed(jid)
        self.p.reject(jid, "user", "xấu", respawn=False)
        with ON:
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")

    def test_film_estimate_prices_every_shot_as_2_5_draft_plus_upgrade(self):
        for sid in self.sids:
            self.label("easy", sid)
        with ON:
            est = quality_tier.e1_estimate(self.p.conn, self.pid)
        draft = cost.seedance_estimate(quality_tier.SAMPLE_MODEL, "480p", "9:16", 4.0)
        final = quality_tier.upgrade_price("9:16", 4.0)
        self.assertEqual((est["direct"], est["draft_first"]), (0, 2))
        self.assertAlmostEqual(est["usd"], round(2 * (draft + final), 2))
        self.assertNotIn("2.0", est["line"])


class SeedanceQualityPicker(Base):
    def test_2_5_offers_a_480p_draft_and_picking_it_is_the_draft_route(self):
        with ON:
            opts = dict(model_router.resolution_options("seedance-2.5"))
            self.assertIn("480p", opts)
            self.assertIn("nháp", opts["480p"])
            model_router.set_resolution(self.p.conn, self.s1, "480p")
            row = self.p.conn.execute("SELECT quality_path FROM motion_prompts WHERE scene_id=?", (self.s1,)).fetchone()
            self.assertEqual(row[0], "draft_first")
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")


class RecommendIsSeedance25(unittest.TestCase):
    CASES = [{}, {"camera_complexity": "complex"}, {"shot_role": "hero"}, {"shot_role": "transition"},
             {"characters": ["a", "b", "c"]}, {"characters": ["a", "b"], "dialogue": [{"speaker": "a", "text": "x"}, {"speaker": "b", "text": "y"}]}]

    def test_every_priority_recommends_seedance_2_5_when_two_tier_is_on(self):
        with ON:
            for prio in model_router.PRIORITIES:
                for data in self.CASES:
                    for look in (None, "FF_INGAME"):
                        rec = model_router.recommend(data, prio, look=look)
                        self.assertEqual(rec["model"], "seedance-2.5", (prio, data, look, rec))
                        self.assertIn("Seedance 2.5", rec["reason"])

    def test_flag_off_keeps_the_old_ladder(self):
        with OFF:
            self.assertEqual(model_router.recommend({}, "balanced")["model"], "seedance-fast")


class ComparePrioritiesUse25(Base):
    def test_plan_for_another_priority_is_2_5_draft(self):
        with ON:
            for prio in model_router.PRIORITIES:
                rows = model_router.plan(self.p.conn, self.pid, cost.load_pricing(), priority=prio)
                self.assertEqual({(r["model"], r.get("resolution")) for r in rows}, {("seedance-2.5", "480p")}, prio)


    def test_compare_total_pays_the_draft_and_the_1080p_upgrade(self):
        # rà nhánh 14/10: dòng "So sánh tổng" (Bước 4, chuyên gia) cộng plan() = chỉ giá nháp 480p, thiếu bản cao 1080p nâng từ nháp
        draft = cost.seedance_estimate(quality_tier.SAMPLE_MODEL, "480p", "9:16", 4.0)
        final = quality_tier.upgrade_price("9:16", 4.0)
        with ON:
            for prio in model_router.PRIORITIES:
                got = model_router.compare_total(self.p.conn, self.pid, cost.load_pricing(), prio)
                self.assertAlmostEqual(got, len(self.sids) * (draft + final), places=3, msg=prio)
        with OFF:                                  # cờ tắt: như cũ, tổng các hàng plan
            rows = model_router.plan(self.p.conn, self.pid, cost.load_pricing(), priority="balanced")
            self.assertEqual(model_router.compare_total(self.p.conn, self.pid, cost.load_pricing(), "balanced"),
                             model_router.total(rows))


class QueuedDirectJobSentAsDraft(Base):
    """Lớp chặn 896/901 (runner._submit_kwargs): job gen thẳng đã vào hàng, sau đó người đặt quality_path='draft_first' → lúc gửi
    đường của shot là nháp 2.5 480p → gửi như NHÁP (draft=True, nâng 1080p được), ghi lại bậc 'draft' — không gửi 480p gen thẳng."""

    def test_person_switches_to_draft_first_after_a_direct_job_is_queued(self):
        from core.runner import VideoRunner
        from tests.test_cost_route_e1 import _provider
        quality_tier.set_path(self.p.conn, self.s1, "direct")
        with ON:
            jid = self.p.create_job(self.s1, "video_gen")
            self.assertEqual(self.p.job(jid)["quality_tier"], "direct")
            quality_tier.set_path(self.p.conn, self.s1, "draft_first")
            self.p.conn.commit()
            kw = VideoRunner(self.p, _provider(), self.data)._submit_kwargs(self.p.job(jid))
        self.assertEqual((kw.get("draft"), kw.get("resolution")), (True, "480p"))
        self.assertEqual(self.p.job(jid)["quality_tier"], "draft")


class DraftsNeverDelivered(unittest.TestCase):
    """Mục 4 rà 14/10: nháp 2.5 480p ĐÃ DUYỆT là clip "dùng được" (final_cut.collect_clips usable — cho bản XEM NHÁP), nhưng BẢN GIAO đo
    clip gốc (final_cut.require_delivery_resolution ở render / deliver / export / editor_apply / autopilot) → chặn, nêu tên shot."""

    def setUp(self):
        from tests.test_delivery_resolution import DeliveryEntryTests
        DeliveryEntryTests.setUp(self)
        self.p.conn.execute("UPDATE jobs SET quality_tier='draft' WHERE type='video_gen'")
        self.p.conn.commit()

    def test_approved_480p_drafts_are_usable_but_never_delivered(self):
        from unittest import mock
        from core import delivery, final_cut
        self.assertEqual(len(final_cut.collect_clips_for_render(self.p.conn, self.data, self.pid)), 3)   # dùng được cho bản xem
        with mock.patch("core.ffmpeg_studio.probe_size", return_value=(480, 854)),                 mock.patch("core.ffmpeg_studio.render_final") as render:
            with self.assertRaisesRegex(ValueError, "shot 2: Kelly 02.*nâng 1080p.*shot 9: Kelly 09"):
                delivery.render(self.p, self.pid, self.data, None)
            render.assert_not_called()


class DirectorPromptsNoLongerRouteEasyDirect(unittest.TestCase):
    """13/10: nhãn easy / complex chỉ là thông tin — prompt Đạo diễn / Quay phim không được nói 'easy → gen thẳng bản cao'."""
    FILES = ("01_director_scene_analysis.md", "17_director_shots.md", "20_dp_scene_shots.md")

    def test_prompts_say_every_shot_drafts_first(self):
        import os
        import re
        root = os.path.join(os.path.dirname(__file__), "..", "prompts")
        for name in self.FILES:
            text = open(os.path.join(root, name), encoding="utf-8").read()
            self.assertIsNone(re.search(r"gen thẳng bản (chất lượng )?cao", text), name)
            self.assertNotIn("quyết định đường làm clip", text, name)
            self.assertNotIn("còn lại gen thẳng", text, name)
            self.assertIn("mọi shot", text, name)


if __name__ == "__main__":
    unittest.main()
