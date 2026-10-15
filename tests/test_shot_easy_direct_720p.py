"""Quy ước người dùng (nhắc lại 15/10, sửa chỗ phiên 13/10 ghi nhầm "MỌI shot nháp 480p → 1080p"): video hết Seedance 2.5;
shot ĐƠN GIẢN (nhãn Đạo diễn 'easy', code không thấy dấu hiệu khó) → gen thẳng Seedance 2.5 720p, lúc dựng phóng ffmpeg lên 1080p;
shot KHÓ / quan trọng / chưa rõ / THIẾU nhãn → nháp 2.5 480p → duyệt → nâng 1080p. Code ép khó khi có video ref, kỹ năng, khớp môi,
≥ 3 nhân vật, shot hero. Người chọn tay thắng; shot đã có nháp đang dùng giữ đường cũ. Không gọi dịch vụ tốn tiền."""
import json
import unittest
from unittest import mock

from core import cost, model_router, quality_tier, shot_complexity
from tests.test_cost_route_e1 import ON, Base


class EasyShotGoesDirect720(Base):
    N = 2

    def set_data(self, sid=None, **fields):
        sid = sid or self.s1
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()[0] or "{}")
        data.update(fields)
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), sid))
        self.p.conn.commit()

    def test_a_easy_single_shot_is_direct_seedance25_720p(self):
        self.label("easy")
        with ON:
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "direct")
            ch = model_router.scene_choice(self.p.conn, self.s1)
            self.assertEqual((ch["model"], ch["resolution"], ch["e1"]), ("seedance-2.5", "720p", "direct"))
            self.assertIn("phóng ffmpeg", ch["reason"])
            jid = self.p.create_job(self.s1, "video_gen")
            self.assertEqual(self.p.job(jid)["quality_tier"], "direct")

    def test_b_complex_shot_is_draft_first_480p(self):
        self.label("complex")
        with ON:
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")
            ch = model_router.scene_choice(self.p.conn, self.s1)
            self.assertEqual((ch["model"], ch["resolution"], ch["e1"]), ("seedance-2.5", "480p", "draft_first"))
            self.assertEqual(self.p.job(self.p.create_job(self.s1, "video_gen"))["quality_tier"], "draft")

    def test_c_easy_label_with_a_hard_sign_is_forced_hard(self):
        cases = [("ref", "video tham chiếu"), ("skill_phase", "kỹ năng"), ("characters", "3 nhân vật"),
                 ("lip_sync", "khớp môi"), ("shot_role", "quan trọng")]
        for key, word in cases:
            with self.subTest(key):
                self.label("easy")
                if key == "ref":
                    self.p.conn.execute("UPDATE motion_prompts SET ref_video_path='ref.mp4' WHERE scene_id=?", (self.s1,))
                elif key == "skill_phase":
                    self.set_data(skill_phase="cast")
                elif key == "characters":
                    self.set_data(characters=["A", "B", "C"])
                elif key == "lip_sync":
                    self.set_data(lip_sync=True)
                else:
                    self.set_data(shot_role="hero")
                self.p.conn.commit()
                with ON:
                    r = quality_tier.route(self.p.conn, self.s1)
                    self.assertEqual(r["path"], "draft_first")
                    self.assertIn(word, r["why"])
                    self.assertEqual(model_router.scene_choice(self.p.conn, self.s1)["resolution"], "480p")
                self.p.conn.execute("UPDATE motion_prompts SET ref_video_path=NULL WHERE scene_id=?", (self.s1,))
                self.p.conn.execute("UPDATE scenes SET data='{}' WHERE id=?", (self.s1,))
                self.p.conn.commit()

    def test_d_missing_director_label_is_hard_with_a_reason(self):
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"characters": ["A"]}), self.s1))
        self.p.conn.commit()
        with ON:
            r = quality_tier.route(self.p.conn, self.s1)
            self.assertEqual(r["path"], "draft_first")
            self.assertIn("chưa gắn nhãn", r["why"])
            self.assertIn("chưa gắn nhãn", model_router.scene_choice(self.p.conn, self.s1)["reason"])
        # nhãn 'dễ' do CODE điền khi Đạo diễn bỏ trống (kiểm chéo) không phải nhãn Đạo diễn → vẫn khó
        data = shot_complexity.apply({"characters": ["A"]})
        self.assertEqual((data["difficulty"], data["difficulty_by"]), ("easy", "check"))
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), self.s1))
        self.p.conn.commit()
        with ON:
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")
        # dữ liệu cũ (trước difficulty_by): ghi chú "Đạo diễn chưa ghi độ khó" cũng nhận ra
        data.pop("difficulty_by")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), self.s1))
        self.p.conn.commit()
        with ON:
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")

    def test_d2_reapplying_the_check_keeps_the_check_label_and_a_director_label_counts(self):
        once = shot_complexity.apply({"characters": ["A"]})
        twice = shot_complexity.apply(dict(once))
        self.assertEqual(twice["difficulty_by"], "check")
        by_director = shot_complexity.apply({"characters": ["A"], "difficulty": "easy"})
        self.assertEqual((by_director["difficulty"], by_director["difficulty_by"]), ("easy", "director"))

    def test_e_person_override_wins(self):
        self.label("complex")
        quality_tier.set_path(self.p.conn, self.s1, "direct")
        with ON:
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "direct")
            self.assertEqual(model_router.scene_choice(self.p.conn, self.s1)["resolution"], "720p")
        self.label("easy", self.sids[1])
        quality_tier.set_path(self.p.conn, self.sids[1], "draft_first")
        with ON:
            self.assertEqual(quality_tier.path(self.p.conn, self.sids[1]), "draft_first")

    def test_group_with_one_hard_shot_drafts_the_whole_group(self):
        self.label("easy", self.sids[0])
        self.label("complex", self.sids[1])
        group = [{"id": sid} for sid in self.sids]
        with ON, mock.patch("core.shots.group_of", return_value=group):
            self.assertEqual(quality_tier.path(self.p.conn, self.sids[0]), "direct")          # the shot alone is easy
            self.assertEqual(quality_tier.group_path(self.p.conn, self.sids[0]), "draft_first")
            ch = model_router.scene_choice(self.p.conn, self.sids[0])
            self.assertEqual((ch["resolution"], ch["e1"]), ("480p", "draft_first"))
            self.assertIn(f"#{self.sids[1]}", ch["reason"])

    def test_old_project_shot_with_a_draft_keeps_the_draft_route(self):
        self.label("easy")
        jid = self.p.create_job(self.s1, "video_gen")
        self.p.conn.execute("UPDATE jobs SET quality_tier='draft' WHERE id=?", (jid,))
        self.p.conn.commit()
        with ON:
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")

    def test_estimate_prices_easy_at_720p_and_hard_as_draft_plus_upgrade(self):
        self.label("easy", self.sids[0])
        self.label("complex", self.sids[1])
        with ON:
            est = quality_tier.e1_estimate(self.p.conn, self.pid)
        direct = cost.seedance_estimate(quality_tier.SAMPLE_MODEL, "720p", "9:16", 4.0)
        draft = cost.seedance_estimate(quality_tier.SAMPLE_MODEL, "480p", "9:16", 4.0)
        final = quality_tier.upgrade_price("9:16", 4.0)
        self.assertEqual((est["direct"], est["draft_first"]), (1, 1))
        self.assertAlmostEqual(est["usd"], round(direct + draft + final, 2))


class RoundGop1510(Base):
    """Vòng sửa gop-1510 (docs/handoff/VONG_SUA_GOP_1510.md) mục 3–6, 8 + quyết định người dùng 15/10."""
    N = 2
    set_data = EasyShotGoesDirect720.set_data

    def test_two_people_talking_with_hands_is_not_forced_hard(self):
        """15/10: code KHÔNG ép khó chỉ vì 2 nhân vật / thoại + cử động tay (điểm kiểm chéo chỉ để hiển thị)."""
        self.label("easy")
        self.set_data(characters=["A", "B"], action="hai người cầm tay nhau", dialogue=[{"speaker": "A", "text": "Đi thôi nào"}])
        with ON:
            r = quality_tier.route(self.p.conn, self.s1)
            self.assertEqual(r["path"], "direct", r["why"])
        # qua reconcile (Director ghi 'dễ', kiểm chéo điểm cao): nhãn hiển thị 'chưa rõ' + ghi chú, đường đi vẫn theo nhãn Đạo diễn
        data = shot_complexity.apply({"characters": ["A", "B"], "action": "hai người cầm tay nhau", "difficulty": "easy",
                                      "difficulty_why": "hai người đứng nói"})
        self.assertEqual((data["difficulty"], data["difficulty_by"]), ("unknown", "director"))
        self.assertIn("kiểm chéo", data["difficulty_check"]["note"])
        self.assertEqual(quality_tier.label_from_director(data), "easy")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), self.s1))
        self.p.conn.commit()
        with ON:
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "direct")

    def test_item3_old_check_label_without_by_stays_a_check_label(self):
        old = {"characters": ["A"], "difficulty": "easy",
               "difficulty_check": {"score": 0, "factors": [], "suggest": "easy",
                                    "note": "Đạo diễn chưa ghi độ khó → theo kiểm chéo: 'dễ' (điểm 0) — thiếu nhãn Đạo diễn nên vẫn nháp trước"}}
        out = shot_complexity.apply(dict(old))
        self.assertEqual(out["difficulty_by"], "check")
        self.assertIsNone(quality_tier.label_from_director(out))

    def test_item4_easy_needs_a_reason_and_the_prompt_example_is_unknown(self):
        import os
        self.assertIsNone(quality_tier.label_from_director({"difficulty": "easy", "difficulty_by": "director"}))
        self.assertIsNone(quality_tier.label_from_director({"difficulty": "easy", "difficulty_why": " ", "difficulty_by": "director"}))
        self.assertEqual(quality_tier.label_from_director({"difficulty": "easy", "difficulty_why": "một người đứng",
                                                           "difficulty_by": "director"}), "easy")
        self.assertEqual(quality_tier.label_from_director({"difficulty": "complex", "difficulty_by": "director"}), "complex")
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "prompts", "01_director_scene_analysis.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn('"difficulty": "easy"', text)
        self.assertIn('"difficulty": "unknown"', text)

    def test_item5_label_without_by_director_is_hard_with_a_reason(self):
        self.assertIsNone(quality_tier.label_from_director({"difficulty": "easy", "difficulty_why": "x"}))
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                            (json.dumps({"characters": ["A"], "difficulty": "easy", "difficulty_why": "x"}), self.s1))
        self.p.conn.commit()
        with ON:
            r = quality_tier.route(self.p.conn, self.s1)
        self.assertEqual(r["path"], "draft_first")
        self.assertIn("trước 15/10", r["why"])

    def _direct_clip(self):
        from core.states import JobState
        self.label("easy")
        with ON:
            jid = self.p.create_job(self.s1, "video_gen")
        self.assertEqual(self.p.job(jid)["quality_tier"], "direct")
        self.p.start(jid)
        self.p.succeed(jid)
        return jid, JobState

    def test_item6_direct_720p_clip_waits_for_the_person(self):
        from core import autopilot
        jid, JobState = self._direct_clip()
        self.p.transition(jid, JobState.PENDING_REVIEW)
        with ON:
            self.assertEqual(autopilot._approve_unflagged(self.p, self.pid, "video_gen"), [])
            self.assertEqual(self.p.job(jid)["state"], "pending_review")
            self.assertEqual(autopilot._drafts_waiting(self.p, self.pid), ["S01"])           # the run WAITS, with a reason
            self.assertEqual(autopilot._approve_held(self.p, self.pid, "video_gen", "giữ sau khi xem"), 0)
            self.assertFalse(self.p.approve(jid, "ai_agent", "QC cảnh: đạt"))
            self.assertEqual(self.p.job(jid)["state"], "pending_review")
            self.assertTrue(self.p.approve(jid, "user"))
            self.assertEqual(autopilot._drafts_waiting(self.p, self.pid), [])

    def test_item6_qc_pass_on_a_direct_clip_is_held_for_the_person(self):
        jid, _ = self._direct_clip()
        self.p.conn.execute("UPDATE projects SET operating_mode='auto' WHERE id=?", (self.pid,))
        self.p.conn.commit()
        with ON:
            self.assertEqual(self.p.apply_qc(jid, {"motion": 0.99}), "pending_review")
        self.assertEqual(self.p.job(jid)["state"], "pending_review")
        with mock.patch("core.quality_tier.enabled", return_value=False):            # flag off: as before (QC approves)
            jid2 = self.p.create_job(self.sids[1], "video_gen")
            self.p.start(jid2)
            self.p.succeed(jid2)
            self.assertEqual(self.p.apply_qc(jid2, {"motion": 0.99}), "approved")

    def test_item8_a_take_group_makes_every_shot_hard(self):
        self.label("easy", self.sids[0])
        self.label("easy", self.sids[1])
        self.set_data(self.sids[0], shot_no=1, take_line=True)
        self.set_data(self.sids[1], shot_no=2)
        group = [{"id": sid, "data": json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()[0])}
                 for sid in self.sids]
        with ON, mock.patch("core.shots.group_of", return_value=group), mock.patch("core.lipsync.enabled", return_value=True), \
                mock.patch("core.lipsync.method_for", side_effect=lambda d, *a, **k: "take" if d.get("take_line") else "skip"):
            r = quality_tier.route(self.p.conn, self.sids[1])                 # the wide shot itself has no line
            self.assertEqual(r["path"], "draft_first")
            self.assertIn("take", r["why"])


class DeliveryUpscalesOnly720(unittest.TestCase):
    def test_f_720p_clip_is_scaled_to_1080_and_480p_is_blocked(self):
        from core import ffmpeg_studio, final_cut
        with mock.patch("core.ffmpeg_studio.probe_size", return_value=(720, 1280)):
            self.assertTrue(ffmpeg_studio.needs_upscale("a.mp4", (1080, 1920)))
            self.assertIsNone(final_cut.require_delivery_resolution([{"title": "Shot 01", "path": "a.mp4"}], (1080, 1920)))
        with mock.patch("core.ffmpeg_studio.probe_size", return_value=(480, 854)):
            with self.assertRaisesRegex(ValueError, "Shot 02.*dưới 720p"):
                final_cut.require_delivery_resolution([{"title": "Shot 02", "path": "b.mp4"}], (1080, 1920))


if __name__ == "__main__":
    unittest.main()
