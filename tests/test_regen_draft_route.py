"""Lỗi 8 của #27 (13/10, docs/handoff/P27_TAP1_TONG_KET_2026-10-13.md mục 6): "Gen lại" shot 18 (scene 286) sau bản cao 872 ra job
`direct` 896 → 901, gửi Seedance 2.5 480p KHÔNG kèm draft=True — không nâng 1080p được, phải tạo tay nháp 904 → bản cao 906.
Gốc: bậc của job (lúc tạo, quality_tier.tier_for_new_job) và độ phân giải gửi đi (lúc gửi, model_router.scene_choice → e1_choice) tính
độc lập từ group_path — đường nhóm trôi (nhóm Seedance tách/gộp theo độ dài prompt) thì job `direct` bị gửi 480p của đường nháp; và gen
lại từ bản cao mà ảnh đã vẽ lại kế thừa `final` + nháp cũ (bị chặn "đầu vào đã đổi")."""
import json
import unittest

from core import model_router, quality_tier, regen
from core.runner import VideoRunner
from core.states import JobState
from tests.test_quality_tier import ON, Base, _provider


class RegenDraftRouteTests(Base):
    def final_waiting(self):
        """Như #27 shot 18: nháp 799 người duyệt → bản cao 872 làm xong, chờ duyệt."""
        d = self.approved_draft()
        f = quality_tier.request_final(self.p, self.s1)
        self.made(f)
        self.p.transition(f, JobState.PENDING_REVIEW)
        return d, f

    def redraw_picture(self):
        """Người vẽ lại ảnh (894, cha 781): ảnh mới được duyệt → nháp cũ thành cũ."""
        img = self.p.create_job(self.s1)
        self.p.start(img)
        self.p.succeed(img)
        self.p.approve(img)
        return img

    def auto_model(self):
        """Như 286: không chọn model tay — model theo đề xuất (ưu tiên 'cân bằng' → họ Seedance, E1 chọn 2.0 / 2.5 theo đường)."""
        self.p.conn.execute("UPDATE projects SET model_priority='balanced' WHERE id=?", (self.pid,))
        self.p.conn.execute("UPDATE motion_prompts SET video_model=NULL WHERE scene_id=?", (self.s1,))
        self.p.conn.commit()

    def kwargs(self, jid):
        return VideoRunner(self.p, _provider(), self.data)._submit_kwargs(self.p.job(jid))

    def test_regen_of_a_final_after_the_picture_was_redrawn_starts_a_new_draft(self):
        with ON:
            _, f = self.final_waiting()
            self.redraw_picture()
            new = regen.regenerate_video(self.p, self.data, f, note="làm lại vì làm từ ảnh cũ")
            self.assertEqual((self.tier(new), self.p.job(new)["draft_job_id"]), ("draft", None))
            kw = self.kwargs(new)
            self.assertEqual((kw.get("draft"), kw.get("resolution")), (True, "480p"))

    def test_regen_of_a_final_when_the_auto_path_drifted_to_direct_stays_on_the_draft_route(self):
        with ON:
            self.auto_model()
            _, f = self.final_waiting()
            self.redraw_picture()
            self.set_difficulty("easy")          # như 286: nhãn 'easy', trước đi nháp vì nhóm có shot khó — nhóm tách → đường tự 'direct'
            new = regen.regenerate_video(self.p, self.data, f, note="làm lại vì làm từ ảnh cũ")
            self.assertEqual(self.tier(new), "draft")
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")
            choice = model_router.scene_choice(self.p.conn, self.s1)
            self.assertEqual((choice["model"], choice.get("e1")), ("seedance-2.5", "draft_first"))
            kw = self.kwargs(new)
            self.assertEqual((kw.get("draft"), kw.get("resolution")), (True, "480p"))
            # tự gen lại (QC) job nháp mới vẫn nháp
            self.made(new)
            self.assertEqual(self.p.reject(new, "user", "Keep the glue wall in frame"), "rejected")
            again = self.p.conn.execute("SELECT MAX(id) FROM jobs").fetchone()[0]
            self.assertEqual(self.tier(again), "draft")

    def test_the_persons_direct_choice_still_wins(self):
        with ON:
            _, f = self.final_waiting()
            self.redraw_picture()
            quality_tier.set_path(self.p.conn, self.s1, "direct")       # người chọn rõ "gen thẳng"
            new = regen.regenerate_video(self.p, self.data, f, note="gen thẳng")
            self.assertEqual(self.tier(new), "direct")
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "direct")

    def test_a_direct_job_is_never_sent_as_a_2_5_480p_without_draft(self):
        with ON:
            self.auto_model()
            self.set_difficulty("easy")
            j = self.p.create_job(self.s1, "video_gen")
            self.assertEqual(self.tier(j), "direct")
            self.set_difficulty("unknown")       # đường trôi sang nháp giữa lúc tạo và lúc gửi (896/901: 2.5 480p, không draft)
            kw = self.kwargs(j)
            self.assertFalse(kw.get("resolution") == "480p" and not kw.get("draft"), kw)
            self.assertEqual((kw.get("draft"), kw.get("resolution")), (True, "480p"))
            self.assertEqual(self.tier(j), "draft")                     # sổ / báo giá / nâng bản cao thấy đúng bậc

    def test_the_persons_own_480p_pick_stays_a_direct_480p(self):
        with ON:
            model_router.set_resolution(self.p.conn, self.s1, "480p")
            j = self.p.create_job(self.s1, "video_gen")
            kw = self.kwargs(j)
            self.assertEqual((self.tier(j), kw.get("resolution"), kw.get("draft")), ("direct", "480p", None))

    def test_the_persons_720p_direct_pick_is_unchanged(self):
        with ON:
            model_router.set_resolution(self.p.conn, self.s1, "720p")
            j = self.p.create_job(self.s1, "video_gen")
            kw = self.kwargs(j)
            self.assertEqual((self.tier(j), kw.get("resolution"), kw.get("draft")), ("direct", "720p", None))

    def test_old_jobs_without_a_tier_still_run(self):
        with ON:
            old = self.p.create_job(self.s1, "video_gen")
            self.p.conn.execute("UPDATE jobs SET quality_tier=NULL WHERE id=?", (old,))
            self.p.conn.commit()
            self.assertIsInstance(self.kwargs(old), dict)
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")
            self.made(old)
            self.assertEqual(self.p.reject(old, "user", "Keep the red hood on"), "rejected")
            again = self.p.conn.execute("SELECT MAX(id) FROM jobs").fetchone()[0]
            self.assertEqual(self.tier(again), "draft")                 # theo đường hiện tại, như trước

    def test_a_failed_or_untiered_latest_job_does_not_pin_the_draft_route(self):
        with ON:
            self.set_difficulty("easy")
            d = self.p.create_job(self.s1, "video_gen")
            self.p.conn.execute("UPDATE jobs SET quality_tier='draft' WHERE id=?", (d,))
            self.p.conn.commit()
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")
            self.p.start(d)
            self.p.fail(d, "provider error")                             # nháp hỏng ở nhà cung cấp: không dính tuyến nháp
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "direct")
            old = self.p.create_job(self.s1, "video_gen")
            self.p.conn.execute("UPDATE jobs SET quality_tier='draft' WHERE id=?", (d,))
            self.p.conn.execute("UPDATE jobs SET quality_tier=NULL WHERE id=?", (old,))   # job mới nhất không bậc (cờ tắt lúc tạo)
            self.p.conn.commit()
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "direct")

    def test_easy_shot_never_drafted_still_goes_direct_720p(self):
        with ON:
            self.auto_model()
            self.set_difficulty("easy")
            j = self.p.create_job(self.s1, "video_gen")
            self.assertEqual(self.tier(j), "direct")
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "direct")
            kw = self.kwargs(j)
            self.assertEqual((kw.get("resolution"), kw.get("draft")), ("720p", None))   # E1: 2.0 720p gen thẳng, giữ nguyên


if __name__ == "__main__":
    unittest.main()
