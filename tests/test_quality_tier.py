"""N1 — lõi 2 bậc chất lượng video (người dùng chốt 08/10, docs/THIET_KE_2_BAC_CHAT_LUONG_VA_NHAC_2026-10-08.md mục 5a).

Cờ two_tier_quality TẮT = hành vi y như cũ (kể cả "Thử rẻ"); BẬT = bỏ qua test_quality, nháp → duyệt → bản cao, trần nháp 2 / bản cao 1,
gen lại y nguyên bị từ chối (CHUAN_XAY_DUNG luật 3)."""
import json
import os
import tempfile
import time
import unittest
from unittest import mock

from core import cost, diag, lineage, llm_io, quality_tier, regen
from core.adapters.clipai import ClipAIVideoProvider
from core.db import connect
from core.pipeline import AUTO_LIMIT_CODE, Pipeline
from core.runner import VideoRunner
from core.states import InvalidTransition, JobState

ON = mock.patch("core.quality_tier.enabled", return_value=True)
OFF = mock.patch("core.quality_tier.enabled", return_value=False)


def _provider():
    return ClipAIVideoProvider("tok", "https://example.invalid", lambda *a, **k: None)


class Base(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("N1")
        self.s1 = self.p.create_scene(self.pid, 1, "Shot 1")
        self.img = self.p.create_job(self.s1)
        self.p.start(self.img)
        self.p.succeed(self.img)
        self.p.approve(self.img)
        llm_io.store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": 1, "motion_prompt": "she dances", "duration_sec": 4}]})
        llm_io.approve_motion_prompt(self.p, self.s1)
        self.p.conn.execute("UPDATE motion_prompts SET video_model='seedance-2.5' WHERE scene_id=?", (self.s1,))
        self.p.conn.commit()
        self.set_difficulty("unknown")      # 09/10: chưa có nhãn → gen thẳng; các test này thử đường nháp → nhãn 'chưa rõ' của Đạo diễn

    def set_difficulty(self, level, sid=None):
        sid = sid or self.s1
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()[0] or "{}")
        data.update(difficulty=level, difficulty_why="test")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), sid))
        self.p.conn.commit()

    def stamp(self, jid, model="seedance-2.5", ext=None):
        """What the runner writes when a clip is sent: the input stamp, the picture, the model, the task id."""
        mp = self.p.conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (self.s1,)).fetchone()
        self.p.conn.execute("UPDATE jobs SET input_hash=?, source_job_id=?, model=?, external_id=? WHERE id=?",
                            (lineage.video_input_hash(mp, None), self.img, model, ext or f"seedance:t{jid}", jid))
        self.p.conn.commit()

    def made(self, jid):
        self.stamp(jid)
        self.p.start(jid)
        self.p.succeed(jid)

    def approved_draft(self):
        jid = self.p.create_job(self.s1, "video_gen")
        self.made(jid)
        self.p.approve(jid, "user")
        return jid

    def tier(self, jid):
        return self.p.job(jid)["quality_tier"]


class FlagOffTests(Base):
    def test_flag_is_off_and_unverified(self):
        from core import features
        self.assertFalse(features.FEATURES["two_tier_quality"]["verified"])

    def test_off_changes_nothing(self):
        with OFF:
            self.p.conn.execute("UPDATE projects SET test_quality=1 WHERE id=?", (self.pid,))
            self.p.conn.commit()
            jid = self.p.create_job(self.s1, "video_gen")
            self.assertIsNone(self.tier(jid))
            self.assertEqual(self.p.auto_limit(self.p.job(jid)), 2)
            proj = self.p.project(self.pid)
            self.assertTrue(quality_tier.cheap_mode(proj))                       # "Thử rẻ" still works
            kw = VideoRunner(self.p, _provider(), self.data)._submit_kwargs(self.p.job(jid))
            self.assertEqual(kw.get("kling_mode"), "std")
            self.assertNotIn("draft", kw)
            self.made(jid)
            self.assertEqual(self.p.reject(jid, "user"), "rejected")            # a plain redo is not refused with the flag off


class PathAndStateTests(Base):
    def test_on_ignores_cheap_mode(self):
        with ON:
            self.p.conn.execute("UPDATE projects SET test_quality=1 WHERE id=?", (self.pid,))
            self.p.conn.commit()
            self.assertFalse(quality_tier.cheap_mode(self.p.project(self.pid)))
            from core import model_router
            self.assertEqual(model_router.scene_choice(self.p.conn, self.s1)["model"], "seedance-2.5")

    def test_path_from_director_label_and_person_override(self):
        with ON:
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")       # no label → draft first
            self.set_difficulty("unknown")
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")
            self.set_difficulty("complex")
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")
            self.set_difficulty("easy")                                                   # 13/10: easy no longer means direct
            self.assertEqual(quality_tier.path(self.p.conn, self.s1), "draft_first")
            self.assertEqual(self.tier(self.p.create_job(self.s1, "video_gen")), "draft")
            quality_tier.set_path(self.p.conn, self.s1, "direct")                         # the person wins
            self.assertEqual(self.tier(self.p.create_job(self.s1, "video_gen")), "direct")
            quality_tier.set_path(self.p.conn, self.s1, "draft_first")
            self.assertEqual(self.tier(self.p.create_job(self.s1, "video_gen")), "draft")

    def test_eight_states(self):
        with ON:
            st = lambda: quality_tier.state(self.p.conn, self.s1)   # noqa: E731
            self.assertEqual(st(), "none")
            d = self.p.create_job(self.s1, "video_gen")
            self.assertEqual(self.tier(d), "draft")
            self.assertEqual(st(), "draft_running")
            self.made(d)
            self.assertEqual(st(), "draft_review")
            self.p.approve(d, "user")
            self.assertEqual(st(), "draft_ok")
            self.p.conn.execute("UPDATE motion_prompts SET motion_prompt='she dances and jumps' WHERE scene_id=?", (self.s1,))
            self.p.conn.commit()
            self.assertEqual(st(), "draft_stale")
            self.p.conn.execute("UPDATE motion_prompts SET motion_prompt='she dances' WHERE scene_id=?", (self.s1,))
            self.p.conn.commit()
            f = quality_tier.request_final(self.p, self.s1)
            self.assertEqual((self.tier(f), self.p.job(f)["draft_job_id"], self.p.job(f)["retry_count"]), ("final", d, 0))
            self.assertEqual(st(), "final_running")
            self.made(f)
            self.assertEqual(st(), "final_review")              # 09/10: gen xong, chờ duyệt — không còn "đang gen"
            self.p.approve(f, "user")
            self.p.conn.execute("UPDATE jobs SET result_path='fixture-final-720.mp4' WHERE id=?", (f,))
            with mock.patch('core.ffmpeg_studio.probe_size', return_value=(720, 1280)):
                self.assertEqual(st(), "final_ok")
            s2 = self.p.create_scene(self.pid, 2, "Shot 2")
            j = self.p.create_job(s2, "video_gen")
            self.p.conn.execute("UPDATE jobs SET quality_tier='direct' WHERE id=?", (j,))      # a direct job (E1, before 13/10)
            self.p.conn.commit()
            self.assertEqual(self.tier(j), "direct")
            self.p.start(j)
            self.p.succeed(j)
            self.p.approve(j, "user")
            self.p.conn.execute("UPDATE jobs SET result_path='fixture-direct-720.mp4' WHERE id=?", (j,))
            with mock.patch('core.ffmpeg_studio.probe_size', return_value=(720, 1280)):
                self.assertEqual(quality_tier.state(self.p.conn, s2), "direct_ok")

    def test_a_draft_only_the_qc_approved_still_waits_for_the_person(self):
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            self.made(d)
            self.p.approve(d, "ai_agent")
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "draft_review")


class FinalGateTests(Base):
    def test_no_final_before_the_draft_is_approved(self):
        with ON:
            with self.assertRaises(ValueError):
                quality_tier.request_final(self.p, self.s1)
            d = self.p.create_job(self.s1, "video_gen")
            self.made(d)
            with self.assertRaises(ValueError) as e:
                quality_tier.request_final(self.p, self.s1)
            self.assertIn("chưa được người duyệt", str(e.exception))

    def test_no_final_from_an_outdated_draft_and_the_runner_blocks_it(self):
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            self.p.conn.execute("UPDATE motion_prompts SET duration_sec=6 WHERE scene_id=?", (self.s1,))
            self.p.conn.commit()
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "final_running")
            why = VideoRunner(self.p, _provider(), self.data)._blocked(self.p.job(f))
            self.assertIn("bản cao bị chặn", why)
            self.assertIn("đầu vào đã đổi", why)
            with self.assertRaises(ValueError):
                quality_tier.request_final(self.p, self.s1)


class SupersededFinalTests(Base):
    """13/10 #27 shot 5: final 855 (từ nháp cũ 788) kẹt chờ duyệt → nháp mới 878 đã duyệt vẫn hiện final_review, request_final từ chối."""

    def _final_of_draft_a_then_draft_b(self):
        a = self.approved_draft()
        f = quality_tier.request_final(self.p, self.s1)
        self.made(f)
        self.p.transition(f, JobState.PENDING_REVIEW)                         # như job 855: chờ người duyệt
        self.assertEqual(quality_tier.state(self.p.conn, self.s1), "final_review")
        b = self.approved_draft()
        return a, f, b

    def test_a_newer_approved_draft_retires_the_old_final_and_allows_a_new_one(self):
        with ON:
            a, f, b = self._final_of_draft_a_then_draft_b()
            self.assertEqual(self.p.job(f)["state"], "rejected")
            note = self.p.conn.execute("SELECT note FROM job_events WHERE job_id=? ORDER BY id DESC LIMIT 1", (f,)).fetchone()["note"]
            self.assertIn(f"nháp cũ #{a}", note)
            self.assertIn(f"#{b}", note)
            self.assertIsNone(self.p.conn.execute("SELECT 1 FROM review_log WHERE job_id=? AND decision='reject'", (f,)).fetchone())
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "draft_ok")
            f2 = quality_tier.request_final(self.p, self.s1)
            self.assertEqual(self.p.job(f2)["draft_job_id"], b)
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "final_running")

    def test_old_data_a_stuck_final_of_an_older_draft_does_not_count(self):
        with ON:
            a, f, b = self._final_of_draft_a_then_draft_b()
            self.p.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (f,))   # dữ liệu cũ: job 855 chưa được cho nghỉ
            self.p.conn.commit()
            self.assertIn("nháp cũ", quality_tier.superseded_by(self.p.conn, self.p.job(f)))
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "draft_ok")
            f2 = quality_tier.request_final(self.p, self.s1)
            self.assertEqual(self.p.job(f2)["draft_job_id"], b)

    def test_queued_final_of_an_older_draft_is_cancelled_and_the_runner_blocks_one_left_over(self):
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)                    # chưa gửi
            self.approved_draft()
            self.assertEqual(self.p.job(f)["state"], "cancelled")
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "draft_ok")
            self.p.conn.execute("UPDATE jobs SET state='queued' WHERE id=?", (f,))            # dữ liệu cũ còn sót
            self.p.conn.commit()
            why = VideoRunner(self.p, _provider(), self.data)._blocked(self.p.job(f))
            self.assertIn("bản cao bị chặn", why)
            self.assertIn("nháp cũ", why)

    def test_a_final_already_running_at_the_provider_still_counts(self):
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            self.stamp(f)
            self.p.start(f)                                                       # đã gửi, đang tốn tiền
            self.approved_draft()
            self.assertEqual(self.p.job(f)["state"], "running")
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "final_running")

    def test_retired_final_is_no_longer_escalated(self):
        """rà 13/10: autopilot._blocked_scenes đếm job escalated + rejected = 'hết số lần thử' — bản cao cho nghỉ không được kẹt cờ đó."""
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            self.made(f)
            self.p._hold(f, "giữ cho người")
            self.approved_draft()
            self.assertEqual((self.p.job(f)["state"], self.p.job(f)["escalated"]), ("rejected", 0))

    def test_approving_a_stuck_final_of_an_older_draft_retires_it(self):
        with ON:
            a, f, b = self._final_of_draft_a_then_draft_b()
            self.p.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (f,))   # dữ liệu cũ
            self.p.conn.commit()
            self.p.approve(f, "ai_agent", "QC cảnh: đạt")
            self.assertEqual(self.p.job(f)["state"], "rejected")
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "draft_ok")

    def test_final_of_a_newer_draft_that_lost_its_approval_does_not_count(self):
        with ON:
            a = self.approved_draft()
            b = self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            self.assertEqual(self.p.job(f)["draft_job_id"], b)
            self.p.conn.execute("UPDATE jobs SET state='rejected' WHERE id=?", (b,))      # nháp B mất duyệt, còn nháp A
            self.p.conn.commit()
            self.assertIn(f"#{b}", quality_tier.superseded_by(self.p.conn, self.p.job(f)))
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "draft_ok")

    def test_a_final_finishing_after_a_newer_draft_is_kept_aside_not_over_the_shot_clip(self):
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            self.stamp(f)
            self.p.start(f)                                                       # đang chạy ở nhà cung cấp
            self.approved_draft()
            prov = _provider()
            prov.status = mock.Mock(return_value=mock.Mock(state="succeeded"))

            def download(ext, target):
                with open(target, "wb") as fh:
                    fh.write(b"clip")
                return target
            prov.download = download
            vr = VideoRunner(self.p, prov, self.data)
            with mock.patch.object(vr, "_after_download", side_effect=lambda job, path: path):
                vr._poll_once(self.pid)
            job = self.p.job(f)
            self.assertEqual(job["state"], "rejected")
            self.assertTrue(job["result_path"].endswith(f"01_final{f}_nhap_cu.mp4"))
            self.assertFalse(os.path.exists(os.path.join(os.path.dirname(job["result_path"]), "01.mp4")))
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "draft_ok")

    def test_the_person_choosing_a_final_take_approves_it(self):
        """rà vòng 2: takes.choose loại các take khác (cả nháp gốc) TRƯỚC khi duyệt bản được chọn — bản cao được chọn không bị cho nghỉ."""
        from core import takes
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            self.made(f)
            self.p.transition(f, JobState.PENDING_REVIEW)
            path = os.path.join(self.data, "final.mp4")
            with open(path, "wb") as fh:
                fh.write(b"clip")
            self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (path, f))
            self.p.conn.commit()
            takes.choose(self.p, self.data, f)
            self.assertEqual(self.p.job(f)["state"], "approved")
            self.assertEqual(takes.used(self.p.conn, self.s1)["id"], f)

    def test_keeping_a_qc_rejected_newer_draft_retires_the_old_final(self):
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            self.made(f)
            self.p.transition(f, JobState.PENDING_REVIEW)
            b = self.p.create_job(self.s1, "video_gen")
            self.made(b)
            path = os.path.join(self.data, "b.mp4")
            with open(path, "wb") as fh:
                fh.write(b"clip")
            self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (path, b))
            self.p.conn.commit()
            self.p.reject(b, "ai_agent", "QC: chưa đạt", respawn=False)
            self.p.keep_rejected(b)
            self.assertEqual(self.p.job(b)["state"], "approved")
            self.assertEqual(self.p.job(f)["state"], "rejected")
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "draft_ok")

    def test_a_group_final_of_an_older_draft_keeps_the_followers_parts_aside(self):
        from core import shots, takes
        with ON:
            s2 = self.p.create_scene(self.pid, 2, "Shot 2")
            old = self.p.create_job(s2, "video_gen")                        # the follower's own approved clip
            self.p.start(old)
            self.p.succeed(old)
            self.p.approve(old, "user")
            mine = os.path.join(self.data, "old_02.mp4")
            with open(mine, "wb") as fh:
                fh.write(b"clip")
            self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (mine, old))
            self.p.conn.commit()
            q = self.p.create_job(s2, "video_gen")                          # a queued take the group clip covered
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            self.stamp(f)
            self.p.start(f)
            b = self.approved_draft()
            vr = VideoRunner(self.p, _provider(), self.data)
            lead = os.path.join(self.data, "01_lead.mp4")

            def split(path, group, dests):
                for d in dests[1:]:
                    with open(d, "wb") as fh:
                        fh.write(b"part")
            group = [{"id": self.s1, "idx": 1, "data": {"duration_s": 2}}, {"id": s2, "idx": 2, "data": {"duration_s": 2}}]
            with mock.patch.object(shots, "split_group_clip", side_effect=split), \
                    mock.patch.object(shots, "group_parts", return_value=[(0.0, 2.0), (2.0, 2.0)]), \
                    mock.patch.object(shots, "trim_clip"), mock.patch.object(vr, "_clean_edges", return_value=None):
                vr._finish_group(self.p.job(f), lead, group, whole=4.0)
            part = self.p.conn.execute("SELECT * FROM jobs WHERE scene_id=? AND id NOT IN (?,?) AND type='video_gen'", (s2, q, old)).fetchone()
            self.assertEqual(part["state"], "cancelled")
            self.assertTrue(part["result_path"].endswith(f"02_final{f}_nhap_cu.mp4"))
            self.assertFalse(os.path.exists(os.path.join(os.path.dirname(part["result_path"]), "02.mp4")))
            self.assertEqual(self.p.job(q)["state"], "cancelled")           # never sent alone (paid, unasked)
            self.assertEqual(takes.used(self.p.conn, s2)["id"], old)
            self.assertEqual(takes.used(self.p.conn, s2, skip_cancelled=False)["id"], old)   # chain_waits / _chain_frame
            self.assertEqual(self.p.job(b)["state"], "approved")

    def test_the_dashboard_says_why_a_stuck_final_was_not_approved(self):
        from dashboard import quality_ui
        with ON:
            a, f, b = self._final_of_draft_a_then_draft_b()
            self.p.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (f,))   # dữ liệu cũ
            self.p.conn.commit()
            with mock.patch("streamlit.toast") as toast:
                self.assertFalse(quality_ui.approve_clip(self.p, f))
            self.assertIn(f"nháp cũ #{a}", toast.call_args[0][0])
            self.assertEqual(self.p.job(f)["state"], "rejected")

    def _approved_final(self):
        a = self.approved_draft()
        f = quality_tier.request_final(self.p, self.s1)
        self.made(f)
        self.p.approve(f, "user")
        self.p.conn.execute("UPDATE jobs SET result_path='fixture-final-1080.mp4' WHERE id=?", (f,))
        self.p.conn.commit()
        return a, f

    def test_newer_approved_draft_reopens_final_after_old_final_approved(self):
        """C1/U1 (#27 shot 17, scene 285): nháp 903 duyệt → bản cao 905 duyệt → nháp 915 duyệt, đang dùng → shot về draft_ok (nút ⬆),
        request_final gắn nháp mới; bản cao cũ giữ nguyên làm take; bản dựng tính shot là nháp (_DRAFT)."""
        from dashboard import quality_ui
        with ON, mock.patch('core.ffmpeg_studio.probe_size', return_value=(1080, 1920)):
            a, f = self._approved_final()
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "final_ok")
            b = self.approved_draft()
            self.assertEqual(self.p.job(f)["state"], "approved")                      # không xóa / không đổi bản cao cũ
            self.assertIn(f"nháp cũ #{a}", quality_tier.outdated_final(self.p.conn, self.p.job(f)))
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "draft_ok")
            self.assertIsNone(quality_tier.final_source_problem(self.p.conn, self.s1))
            self.assertEqual(quality_ui.draft_scenes(self.p.conn, self.pid), [(self.s1, 1)])
            f2 = quality_tier.request_final(self.p, self.s1)
            self.assertEqual(self.p.job(f2)["draft_job_id"], b)

    def test_used_draft_take_newer_than_the_approved_final_marks_the_shot_draft(self):
        """C1: take đang dùng là một nháp mới hơn bản cao đã duyệt (chưa được người duyệt) → không phải final_ok."""
        with ON, mock.patch('core.ffmpeg_studio.probe_size', return_value=(1080, 1920)):
            a, f = self._approved_final()
            d = self.p.create_job(self.s1, "video_gen")
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "final_ok")    # nháp đang chạy chưa là clip đang dùng
            self.made(d)
            self.assertEqual(self.tier(d), "draft")
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "draft_review")

    def test_the_qc_approving_a_draft_retires_nothing(self):
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            d = self.p.create_job(self.s1, "video_gen")
            self.made(d)
            self.p.approve(d, "ai_agent")
            self.assertEqual(self.p.job(f)["state"], "queued")


class ChainFixS1Tests(Base):
    """Rà gom chuỗi ảnh→video 13/10 (docs/handoff/DANH_SACH_SUA_CHUOI_2026-10-13.md, phiên S1): C2, C3, C7, V6, U4, U5."""

    def test_video_phase_never_approves_draft_as_ai(self):
        """C2: autopilot / QC cảnh không duyệt NHÁP bằng ai_agent (shot kẹt 'Nháp · chờ duyệt' không nút) — chờ người, có _Wait."""
        from core import autopilot
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            self.made(d)
            self.p.transition(d, JobState.PENDING_REVIEW)
            self.assertEqual(autopilot._approve_unflagged(self.p, self.pid, "video_gen"), [])
            self.assertEqual(self.p.job(d)["state"], "pending_review")
            self.assertIsNone(self.p.conn.execute("SELECT 1 FROM review_log WHERE job_id=? AND decision='approve'", (d,)).fetchone())
            self.assertEqual(autopilot._drafts_waiting(self.p, self.pid), ["S01"])
            self.assertFalse(self.p.approve(d, "ai_agent", "QC cảnh: đạt"))          # phòng thủ: máy không duyệt nháp
            self.assertEqual(self.p.job(d)["state"], "pending_review")
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "draft_review")
            self.assertTrue(self.p.approve(d, "user"))
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "draft_ok")
            self.assertEqual(autopilot._drafts_waiting(self.p, self.pid), [])

    def _final_needing_confirm(self):
        self.approved_draft()
        f = quality_tier.request_final(self.p, self.s1)
        vr = VideoRunner(self.p, _provider(), self.data)
        with mock.patch.object(quality_tier, "final_route",
                               return_value={"from_sample": None, "why": "bản nháp đã hết hạn ở nhà cung cấp"}):
            why = vr._blocked(self.p.job(f))
        self.assertIn(quality_tier.NEED_CONFIRM, why)
        prefix = vr._hold_prefix(self.p.job(f), why)
        self.p.start(f)                                       # như runner: RUNNING rồi FAILED (chưa gửi gì)
        self.p.fail(f, f"{prefix}: {why}")
        return f, prefix

    def test_requeue_input_failures_skips_final_needing_confirm(self):
        """C3: bản cao chờ xác nhận gen mới không phải 'đầu vào cũ' — ↻ Xếp hàng lại không tạo NHÁP mới tốn tiền, ↻ Gửi lại từ chối."""
        from core import batch, pipeline
        with ON:
            f, prefix = self._final_needing_confirm()
            self.assertEqual(prefix, pipeline.FINAL_HOLD)
            self.assertEqual(batch.input_failures(self.p, self.pid), [])
            self.assertNotIn(f, batch.provider_failures(self.p, self.pid))
            jobs_before = self.p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            self.assertEqual(batch.requeue_input_failures(self.p, self.pid)["created"], 0)
            self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], jobs_before)
            with self.assertRaises(InvalidTransition):
                self.p.retry(f, "gửi lại", by_user=True)
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "draft_ok")     # nút ⬆ Gen MỚI bản cao vẫn được đề xuất
            self.assertFalse(quality_tier.final_offer(self.p.conn, self.s1)["upgrade"])

    def test_old_stale_input_note_of_a_final_needing_confirm_is_not_requeued(self):
        from core import batch
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            self.p.start(f)
            self.p.fail(f, f"stale_input: bản cao bị chặn: {quality_tier.NEED_CONFIRM} — {quality_tier.NEW_GEN} (x)")   # dữ liệu trước 13/10
            self.assertEqual(batch.input_failures(self.p, self.pid), [])

    def test_a_final_of_a_changed_draft_input_stays_stale_input(self):
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            self.p.conn.execute("UPDATE motion_prompts SET duration_sec=6 WHERE scene_id=?", (self.s1,))
            self.p.conn.commit()
            vr = VideoRunner(self.p, _provider(), self.data)
            why = vr._blocked(self.p.job(f))
            self.assertEqual(vr._hold_prefix(self.p.job(f), why), "stale_input")    # nháp mới từ đầu vào mới là đúng tuyến

    def test_final_below_threshold_never_autofixes(self):
        """V6: bản cao dưới ngưỡng không bao giờ tự sửa / tự loại (không job con final) — giữ cho người, so lỗi với nháp đã duyệt."""
        with ON:
            d = self.approved_draft()
            self.p.conn.execute("INSERT INTO qc_results (job_id, criterion, score, threshold_at_time) VALUES (?,?,?,?)",
                                (d, "motion", 0.6, 0.85))
            self.p.conn.commit()
            f = quality_tier.request_final(self.p, self.s1)
            self.made(f)
            jobs_before = self.p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            out = self.p.apply_qc(f, {"motion": 0.6, "identity": 0.9}, issues="Make the jump higher", autofix=True)
            self.assertEqual(out, "needs_review")
            self.assertEqual(self.p.job(f)["state"], "pending_review")
            self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], jobs_before)
            note = self.p.conn.execute("SELECT note FROM job_events WHERE job_id=? ORDER BY id DESC LIMIT 1", (f,)).fetchone()["note"]
            self.assertIn("bản cao: không tự sửa", note)
            self.assertIn(f"nháp #{d} đã có cùng lỗi (motion)", note)

    def test_final_far_below_the_floor_is_not_rejected_either(self):
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            self.made(f)
            self.p.conn.execute("UPDATE projects SET qc_reject_floor=0.5 WHERE id=?", (self.pid,))
            self.p.conn.commit()
            self.assertEqual(self.p.apply_qc(f, {"motion": 0.1}, issues="Fix all"), "needs_review")
            self.assertIn("chưa có điểm QC để so", self.p.conn.execute(
                "SELECT note FROM job_events WHERE job_id=? ORDER BY id DESC LIMIT 1", (f,)).fetchone()["note"])

    def test_queued_video_shows_wait_reason(self):
        """C7: lý do giữ job video (Tổ rà soát / kiểm trước gen / bản cao chờ) đọc được cho thẻ Bước 4 — cả khi runner đã khởi động lại."""
        from core import diag, runner
        jid = self.p.create_job(self.s1, "video_gen")
        self.assertIsNone(runner.held_reason(self.p.conn, jid))
        diag.record(self.p.conn, "video", "warn", "chưa gửi — kiểm trước gen chặn: thiếu khung cuối", code="video_pregen_hold",
                    project_id=self.pid, scene_id=self.s1, job_id=jid)
        self.assertIn("thiếu khung cuối", runner.held_reason(self.p.conn, jid))
        runner.WAIT_REASONS[jid] = ("Tổ rà soát giữ: shot lệch", time.time())
        try:
            self.assertEqual(runner.held_reason(self.p.conn, jid), "Tổ rà soát giữ: shot lệch")
        finally:
            runner.WAIT_REASONS.pop(jid, None)

    def test_inbox_lists_drafts_waiting_for_final_and_held_clips(self):
        """C7/U2: hộp thư có 'nháp đã duyệt chờ gen bản cao', 'bản cao chờ xác nhận' (không phải Lỗi gen), clip bị giữ."""
        from core import diag, inbox
        with ON:
            self.approved_draft()
            texts = [i["text"] for i in inbox.items(self.p.conn, "")]
            self.assertTrue(any("nháp đã duyệt chờ gen bản cao: shot 1" in t for t in texts), texts)
            f, _ = self._final_needing_confirm()
            texts = [i["text"] for i in inbox.items(self.p.conn, "")]
            self.assertTrue(any("Bản cao chờ bạn xác nhận gen mới ở shot 1" in t for t in texts), texts)
            self.assertFalse(any(t.startswith("Gen clip lỗi") for t in texts), texts)
            s2 = self.p.create_scene(self.pid, 2, "Shot 2")
            q = self.p.create_job(s2, "video_gen")
            diag.record(self.p.conn, "video", "warn", "chưa gửi — kiểm trước gen chặn: prompt sai công thức", code="video_pregen_hold",
                        project_id=self.pid, scene_id=s2, job_id=q)
            texts = [i["text"] for i in inbox.items(self.p.conn, "")]
            self.assertTrue(any("Clip bị giữ chưa gửi ở shot 2" in t and "prompt sai công thức" in t for t in texts), texts)

    def test_measured_size_tries_the_working_folder_first(self):
        """U5: đường tương đối theo cwd trước (worktree / bản sao), rồi gốc repo — như assets._resolved."""
        from core import final_cut
        here = os.getcwd()
        os.chdir(self.data)
        try:
            with open("clip_u5.mp4", "wb") as fh:
                fh.write(b"clip")
            with mock.patch("core.ffmpeg_studio.probe_size", return_value=(1080, 1920)) as probe:
                self.assertEqual(final_cut.measured_size("clip_u5.mp4"), (1080, 1920))
            self.assertEqual(os.path.normcase(os.path.abspath(probe.call_args[0][0])),
                             os.path.normcase(os.path.join(os.path.realpath(self.data), "clip_u5.mp4")))
        finally:
            os.chdir(here)

    def test_card_meta_line_says_the_current_clip_model(self):
        """U4: dòng model của clip trên thẻ là model ĐÃ dùng cho clip ('clip hiện tại'), khác dòng 'Lần gen tới'."""
        from dashboard.design.screens import video_ui
        self.assertIn("clip hiện tại: Kling std", video_ui.meta_line("Kling std", 1.5, 0.2, 0, current=True))
        self.assertNotIn("clip hiện tại", video_ui.meta_line("Kling std", 1.5, 0.2, 0))


class ReviewRoundS1Tests(Base):
    """Vòng sửa sau rà S1 13/10 (docs/handoff/RA_S1_S2_2026-10-13.md mục 10, 11, 12)."""

    def test_continue_after_clips_wait_never_approves_a_draft(self):
        """Mục 10: người bấm Tiếp tục ở chờ 'clips' → _approve_held không duyệt NHÁP thay người (nháp phải ✔ Duyệt trên thẻ)."""
        from core import autopilot
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            self.made(d)
            self.p.transition(d, JobState.PENDING_REVIEW)
            s2 = self.p.create_scene(self.pid, 2, "Shot 2")
            g = self.p.create_job(s2, "video_gen")
            self.p.conn.execute("UPDATE jobs SET quality_tier='direct' WHERE id=?", (g,))
            self.p.conn.commit()
            self.p.start(g)
            self.p.succeed(g)
            self.p.transition(g, JobState.PENDING_REVIEW)
            self.assertEqual(autopilot._approve_held(self.p, self.pid, "video_gen", "giữ sau khi xem"), 1)
            self.assertEqual(self.p.job(d)["state"], "pending_review")
            self.assertEqual(self.p.job(g)["state"], "approved")
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), "draft_review")

    def test_drafts_waiting_ignores_an_old_draft_after_a_newer_approved_one(self):
        """Mục 11: nháp cũ còn 'succeeded' khi người đã duyệt nháp mới hơn → không chờ mãi."""
        from core import autopilot
        with ON:
            old = self.p.create_job(self.s1, "video_gen")
            self.made(old)
            self.approved_draft()
            self.assertEqual(self.p.job(old)["state"], "succeeded")
            self.assertEqual(autopilot._drafts_waiting(self.p, self.pid), [])

    def test_scene_qc_fix_on_a_final_holds_instead_of_a_paid_child(self):
        """Mục 12 (V6 đường QC cảnh): verdict 'fix' trên bản cao → giữ cho người, không job con bản cao tốn tiền."""
        from core import qc_scene
        with ON, mock.patch.object(qc_scene, "trusted", return_value=True):
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            self.made(f)
            jobs_before = self.p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            obj = {"frames": [{"k": 1, "verdict": "fix", "root_cause": "render", "problem": "tay méo", "fix": "Fix the hands.",
                               "checks": {c: {"ok": c != "artifacts", "evidence": "tay méo"} for c in qc_scene.CHECKS}}]}
            out = qc_scene.apply(self.p, self.pid, [{"job_id": f}], obj, self.data)
            self.assertEqual(self.p.job(f)["state"], "pending_review")
            self.assertEqual(self.p.job(f)["escalated"], 1)
            self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], jobs_before)
            self.assertIn("giữ cho người", out["K1"])
            note = self.p.conn.execute("SELECT note FROM job_events WHERE job_id=? ORDER BY id DESC LIMIT 1", (f,)).fetchone()["note"]
            self.assertIn("bản cao: không tự sửa", note)

    def test_a_person_rejecting_a_final_still_gets_a_new_take(self):
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            self.made(f)
            self.p.transition(f, JobState.PENDING_REVIEW)
            self.p.reject(f, "user", "tay méo", fix="Fix the hands.")
            self.assertEqual(self.p.job(f)["state"], "rejected")


class RunnerTierTests(Base):
    def test_draft_goes_as_the_seedance_2_5_sample_at_480p(self):
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            vr = VideoRunner(self.p, _provider(), self.data)
            kw = vr._submit_kwargs(self.p.job(d))
            self.assertEqual((kw.get("draft"), kw.get("resolution")), (True, "480p"))
            self.assertEqual(vr._usage(("i", "p", None, 4, "seedance-2.5"), kw)[1], "480p")      # ledger tier

    def test_other_models_draft_at_their_lowest_tier(self):
        self.assertEqual(quality_tier.low_tier({}, "kling")["kling_mode"], "std")
        self.assertEqual(quality_tier.low_tier({"resolution": "1080p"}, "seedance")["resolution"], "480p")
        self.assertNotIn("draft", quality_tier.low_tier({}, "seedance"))

    def test_final_from_a_live_2_5_draft_uses_draft_task_at_1080p(self):
        with ON:
            d = self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            prov = _provider()
            prov.task_usage = mock.Mock(return_value={"is_draft": True, "draft_expired_at": (time.time() + 3600) * 1000})
            prov.submit_final_from_sample = mock.Mock(return_value="seedance:final")
            prov.submit = mock.Mock(return_value="seedance:resend")
            vr = VideoRunner(self.p, prov, self.data)
            kw = vr._submit_kwargs(self.p.job(f))
            self.assertEqual(kw["_from_sample"], f"seedance:t{d}")
            self.assertEqual(self.send(vr), 1)
            self.assertEqual(self.p.job(f)["external_id"], "seedance:final")
            prov.submit_final_from_sample.assert_called_once_with(f"seedance:t{d}", resolution="1080p")
            prov.submit.assert_not_called()
            row = self.p.conn.execute("SELECT model, tier FROM usage_events WHERE job_id=?", (f,)).fetchone()
            self.assertEqual((row["model"], row["tier"]), (quality_tier.SAMPLE_MODEL, "1080p"))   # booked at the final's tier

    def send(self, vr):
        """The runner's real send loop, with the inputs (picture file, lint, stamp, money check) stubbed."""
        with mock.patch.object(vr, "_submit_args", return_value=("i.png", "she dances", None, 4, "seedance-2.5")), \
                mock.patch.object(vr, "_blocked", return_value=None), mock.patch.object(vr, "_stamp", return_value={}), \
                mock.patch.object(vr, "_over_budget", return_value=None), mock.patch.object(vr, "_wait", return_value=False):
            return vr._submit_pending(self.pid)

    def test_expired_draft_is_not_resent_unasked(self):
        """F3 (#24): an expired 2.5 sample cannot be upgraded — the final is NOT resent on its own (it was, at 720p, other content);
        it fails with the reason, and the next request needs the person's explicit yes (request_final confirm_new)."""
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            prov = _provider()
            prov.task_usage = mock.Mock(return_value={"is_draft": True, "draft_expired_at": time.time() - 10})
            prov.submit = mock.Mock(return_value="seedance:resend")
            prov.submit_final_from_sample = mock.Mock()
            vr = VideoRunner(self.p, prov, self.data)
            kw = vr._submit_kwargs(self.p.job(f))
            self.assertNotIn("_from_sample", kw)
            self.assertIn(quality_tier.NEED_CONFIRM, kw["_hold"])
            self.assertEqual(self.send(vr), 0)
            prov.submit.assert_not_called()
            prov.submit_final_from_sample.assert_not_called()
            self.assertEqual(self.p.job(f)["state"], "failed")
            with self.assertRaises(ValueError) as e:                          # the draft is now known not upgradable
                quality_tier.request_final(self.p, self.s1)
            self.assertIn(quality_tier.NEW_GEN, str(e.exception))
            self.assertIn("USD", str(e.exception))
            f2 = quality_tier.request_final(self.p, self.s1, confirm_new=True)
            self.assertTrue(json.loads(self.p.job(f2)["confirm_new"])["usd"] > 0)
            vr = VideoRunner(self.p, prov, self.data)
            self.assertEqual(self.send(vr), 1)
            self.assertEqual(self.p.job(f2)["external_id"], "seedance:resend")
            # the highest tier the model's rules allow for a direct send (provider_rules.json) — not the draft's 480p
            self.assertEqual(prov.submit.call_args.kwargs.get("resolution"), quality_tier.final_resolution("seedance-2.5"))
            self.assertNotEqual(prov.submit.call_args.kwargs.get("resolution"), "480p")
            self.assertNotIn("draft", prov.submit.call_args.kwargs)
            row = self.p.conn.execute("SELECT severity, message FROM diag_events WHERE code='final_resend' ORDER BY id DESC").fetchone()
            self.assertEqual(row["severity"], "warn")
            self.assertIn(quality_tier.NEW_GEN, row["message"])

    def test_final_of_another_model_needs_the_persons_yes(self):
        with ON:
            d = self.approved_draft()
            self.p.conn.execute("UPDATE jobs SET model='kling' WHERE id=?", (d,))
            self.p.conn.commit()
            with self.assertRaises(ValueError):
                quality_tier.request_final(self.p, self.s1)
            f = quality_tier.request_final(self.p, self.s1, confirm_new=True)
            route = quality_tier.final_route(self.p.conn, self.p.job(f), _provider())
            self.assertIsNone(route["from_sample"])
            self.assertIn("kling", route["why"])
            self.assertIsNone(quality_tier.needs_confirm(self.p.job(f), route))


class RetryCapTests(Base):
    def test_draft_chain_stops_after_two_redos_and_tells_the_person(self):
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            self.made(d)
            self.assertEqual(self.p.reject(d, "ai_agent", "QC 0.6", fix="Keep the red hood on"), "rejected")
            d2 = self.p.conn.execute("SELECT MAX(id) FROM jobs").fetchone()[0]
            self.assertEqual((self.tier(d2), self.p.job(d2)["retry_count"]), ("draft", 1))
            self.p.conn.execute("UPDATE jobs SET retry_count=2 WHERE id=?", (d2,))
            self.p.conn.commit()
            self.made(d2)
            self.assertEqual(self.p.reject(d2, "ai_agent", "QC 0.6", fix="Hands stay on the rail"), "escalated")
            self.assertEqual(self.p.conn.execute("SELECT MAX(id) FROM jobs").fetchone()[0], d2)        # no third redo
            said = self.p.conn.execute("SELECT message FROM diag_events WHERE code=?", (AUTO_LIMIT_CODE,)).fetchall()
            self.assertTrue(said and "bản NHÁP" in said[-1]["message"])
            self.assertEqual(self.p.conn.execute("SELECT state FROM scenes WHERE id=?", (self.s1,)).fetchone()[0],
                             "needs_attention")

    def test_final_is_never_redone_by_the_machine_only_by_the_person(self):
        """Rà 13/10 mục 12 (V6): trước đây máy loại bản cao → 1 job con bản cao (trần 1). Nay máy không bao giờ loại bản cao thành job
        con tốn tiền (giữ cho người); người loại kèm sửa → bản cao mới gửi từ đầu vào (không từ nháp). Đổi hành vi có chủ đích."""
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            self.assertEqual(self.p.auto_limit(self.p.job(f)), 1)
            self.made(f)
            jobs_before = self.p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            self.assertEqual(self.p.reject(f, "ai_agent", "QC 0.6", fix="Keep the red hood on"), "needs_review")
            self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], jobs_before)
            self.assertEqual(self.p.job(f)["state"], "pending_review")
            self.assertEqual(self.p.reject(f, "user", "giữ áo choàng đỏ", fix="Keep the red hood on"), "rejected")
            f2 = self.p.conn.execute("SELECT MAX(id) FROM jobs").fetchone()[0]
            self.assertEqual(self.tier(f2), "final")
            # the redo of a final carries a fix → resent from the input, not from the draft (draft_task takes no prompt)
            self.assertIsNone(quality_tier.final_route(self.p.conn, self.p.job(f2), _provider())["from_sample"])

class SameInputRedoTests(Base):
    def test_person_redo_without_any_fix_on_the_same_input_is_refused(self):
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            self.made(d)
            with self.assertRaises(InvalidTransition) as e:
                self.p.reject(d, "user")
            self.assertIn("luật 3", str(e.exception))
            self.assertEqual(self.p.state(d).value, "succeeded")                  # nothing moved
            with self.assertRaises(ValueError):
                regen.regenerate_video(self.p, self.data, d)
            self.assertEqual(self.p.reject(d, "user", "Keep the red hood on"), "rejected")   # with the person's fix: fine

    def test_redo_after_the_input_changed_needs_no_fix(self):
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            self.made(d)
            self.p.conn.execute("UPDATE motion_prompts SET motion_prompt='she dances slowly' WHERE scene_id=?", (self.s1,))
            self.p.conn.commit()
            self.assertEqual(self.p.reject(d, "user"), "rejected")

    def test_the_same_fix_again_on_the_same_input_is_refused_and_the_qc_holds_it(self):
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            self.p.conn.execute("UPDATE jobs SET retry_reason='Keep the red hood on' WHERE id=?", (d,))
            self.p.conn.commit()
            self.made(d)
            self.assertEqual(self.p.reject(d, "ai_agent", "QC 0.6", fix="Keep the red hood on"), "needs_review")
            self.assertEqual(self.p.state(d).value, "pending_review")
            self.assertEqual(self.p.job(d)["escalated"], 1)

    def test_a_provider_failure_is_still_resent_unchanged(self):
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            self.stamp(d)
            self.p.start(d)
            self.p.fail(d, "timeout: provider busy")
            self.assertIsNotNone(self.p.retry(d, "gửi lại", by_user=True))

    def test_restart_of_a_stopped_draft_chain_needs_a_changed_input(self):
        with ON:
            d = self.p.create_job(self.s1, "video_gen")
            self.made(d)
            self.p.reject(d, "user", "Keep the hood", respawn=False)
            self.p.conn.execute("UPDATE jobs SET escalated=1 WHERE id=?", (d,))
            self.p.conn.commit()
            with self.assertRaises(InvalidTransition):
                self.p.restart_job(d)
            self.p.conn.execute("UPDATE motion_prompts SET motion_prompt='she waves' WHERE scene_id=?", (self.s1,))
            self.p.conn.commit()
            self.assertEqual(self.tier(self.p.restart_job(d)), "draft")


class FinalEstimateTests(Base):
    def test_sum_of_the_finals_still_to_make(self):
        with ON:
            self.approved_draft()
            s2 = self.p.create_scene(self.pid, 2, "Shot 2")
            self.set_difficulty("easy", s2)
            self.p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, duration_sec, state) VALUES (?,?,?,?)",
                                (s2, "walks", 4, "approved"))
            self.p.conn.commit()
            quality_tier.set_path(self.p.conn, s2, "direct")                         # 13/10: direct only when the person picks it
            est = quality_tier.final_estimate(self.p.conn, self.pid)
            self.assertEqual([s["scene_id"] for s in est["scenes"]], [self.s1])     # the direct shot: no final to make
            want = quality_tier.upgrade_price("16:9", 4.0)
            self.assertAlmostEqual(est["usd"], round(want, 4))
            f = quality_tier.request_final(self.p, self.s1)
            self.assertTrue(f)
            self.assertEqual(quality_tier.final_estimate(self.p.conn, self.pid)["scenes"], [])


if __name__ == "__main__":
    unittest.main()
