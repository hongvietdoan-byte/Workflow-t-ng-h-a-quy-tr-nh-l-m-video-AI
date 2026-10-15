"""F3 — đường chi phí video E1 (người dùng chốt 09/10, docs/CONG_THUC_PROMPT_F0_NHAP_2026-10-09.md mục 5–5b).

Cờ two_tier_quality BẬT: shot dễ → Seedance 2.0 720p (dựng phóng 1080p bằng ffmpeg); khó / chưa rõ → nháp Seedance 2.5 480p → nâng 1080p
từ nháp. #24: bản cao không nâng được từ nháp bị tự gửi lại (720p, nội dung khác) và clip nhóm ghi đè clip nháp của shot đi theo —
cả hai bị chặn ở đây. Không gọi dịch vụ tốn tiền (nhà cung cấp là Mock / bị thay)."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from core import cost, ffmpeg_studio, llm_io, model_router, quality_tier
from core.adapters.clipai import ClipAIVideoProvider
from core.db import connect
from core.pipeline import Pipeline
from core.runner import VideoRunner

ON = mock.patch("core.quality_tier.enabled", return_value=True)
OFF = mock.patch("core.quality_tier.enabled", return_value=False)


def _provider():
    return ClipAIVideoProvider("tok", "https://example.invalid", lambda *a, **k: None)


class Base(unittest.TestCase):
    N = 1

    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.data, True)
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("E1", aspect="9:16")
        self.p.conn.execute("UPDATE projects SET model_priority='balanced' WHERE id=?", (self.pid,))
        self.sids = []
        for i in range(1, self.N + 1):
            sid = self.p.create_scene(self.pid, i, f"Shot {i}")
            img = self.p.create_job(sid)
            self.p.start(img)
            self.p.succeed(img)
            self.p.approve(img)
            self.sids.append(sid)
        llm_io.store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": i, "motion_prompt": "she walks", "duration_sec": 4}
                                                                  for i in range(1, self.N + 1)]})
        for sid in self.sids:
            llm_io.approve_motion_prompt(self.p, sid)
        self.p.conn.commit()
        self.s1 = self.sids[0]
        for sid in self.sids:               # 09/10: chưa có nhãn → gen thẳng; các test này thử đường nháp → nhãn 'chưa rõ' của Đạo diễn
            self.label("unknown", sid)

    def label(self, level, sid=None):
        sid = sid or self.s1
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()[0] or "{}")
        data.update(difficulty=level, difficulty_why="test")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), sid))
        self.p.conn.commit()

    def approved_draft(self, sid=None, model="seedance-2.5", path=None):
        sid = sid or self.s1
        jid = self.p.create_job(sid, "video_gen")
        self.p.conn.execute("UPDATE jobs SET model=?, external_id=?, result_path=? WHERE id=?", (model, f"seedance:t{jid}", path, jid))
        self.p.conn.commit()
        self.p.start(jid)
        self.p.succeed(jid)
        self.p.approve(jid, "user")
        return jid


class RouteTests(Base):
    def test_a_person_chosen_direct_shot_goes_seedance_2_5_at_720p(self):
        self.label("easy")
        quality_tier.set_path(self.p.conn, self.s1, "direct")   # 13/10: nhãn 'easy' không còn ra gen thẳng — chỉ người chọn
        with ON:
            ch = model_router.scene_choice(self.p.conn, self.s1)
            self.assertEqual((ch["model"], ch["resolution"], ch["e1"]), ("seedance-2.5", "720p", "direct"))   # 13/10: bỏ Seedance 2.0
            self.assertIn("gen thẳng Seedance 2.5 720p", ch["reason"])
            jid = self.p.create_job(self.s1, "video_gen")
            self.assertEqual(self.p.job(jid)["quality_tier"], "direct")
            kw = VideoRunner(self.p, _provider(), self.data)._submit_kwargs(self.p.job(jid))
            self.assertEqual(kw.get("resolution"), "720p")
            self.assertNotIn("draft", kw)

    def test_complex_or_unknown_shot_drafts_on_seedance_2_5_at_480p(self):
        for level in ("complex", "unknown", None):
            if level:
                self.label(level)
            with ON:
                ch = model_router.scene_choice(self.p.conn, self.s1)
                self.assertEqual((ch["model"], ch["resolution"]), ("seedance-2.5", "480p"), level)
        with ON:
            jid = self.p.create_job(self.s1, "video_gen")
            kw = VideoRunner(self.p, _provider(), self.data)._submit_kwargs(self.p.job(jid))
            self.assertEqual((kw.get("draft"), kw.get("resolution")), (True, "480p"))

    def test_person_override_wins_and_a_non_2_5_pick_on_a_draft_shot_warns(self):
        self.label("complex")
        model_router.set_override(self.p.conn, self.s1, "seedance")
        with ON:
            ch = model_router.scene_choice(self.p.conn, self.s1)
            self.assertEqual(ch["model"], "seedance")
            self.assertIn(quality_tier.NEW_GEN, ch["warning"])
            self.assertIn(quality_tier.NEW_GEN, model_router.e1_warning(self.p.conn, self.s1))
        model_router.set_override(self.p.conn, self.s1, "seedance-2.5")
        with ON:
            self.assertIsNone(model_router.e1_warning(self.p.conn, self.s1))
        model_router.set_override(self.p.conn, self.s1, "kling")              # Kling keeps its old way
        with ON:
            ch = model_router.scene_choice(self.p.conn, self.s1)
            self.assertEqual(ch["model"], "kling")
            self.assertNotIn("e1", ch)
            self.assertIsNone(ch.get("warning"))

    def test_flag_off_changes_nothing(self):
        self.label("easy")
        with OFF:
            ch = model_router.scene_choice(self.p.conn, self.s1)
            self.assertNotIn("e1", ch)
            self.assertEqual(ch["model"], "seedance-fast")                    # the balanced ladder as before
            self.assertIsNone(model_router.e1_warning(self.p.conn, self.s1))


class FinalConfirmTests(Base):
    def test_a_final_that_cannot_come_from_its_draft_is_not_sent_unasked(self):
        self.label("complex")
        with ON:
            d = self.approved_draft(model="seedance")                          # #24: the draft was made with the alias = 2.0
            self.assertFalse(quality_tier.final_offer(self.p.conn, self.s1)["upgrade"])
            with self.assertRaises(ValueError) as e:
                quality_tier.request_final(self.p, self.s1)
            self.assertIn(quality_tier.NEW_GEN, str(e.exception))
            self.assertIn("USD", str(e.exception))
            self.assertIsNone(self.p.conn.execute("SELECT id FROM jobs WHERE quality_tier='final'").fetchone())
            # a final job made some other way (autopilot / old data) without the person's yes is held by the runner
            f = self.p._insert_job(self.pid, self.s1, "video_gen", quality_tier="final", draft_job_id=d)
            why = VideoRunner(self.p, _provider(), self.data)._blocked(self.p.job(f))
            self.assertIn(quality_tier.NEED_CONFIRM, why)
            self.p.cancel(f)
            f2 = quality_tier.request_final(self.p, self.s1, confirm_new=True)
            seen = json.loads(self.p.job(f2)["confirm_new"])
            self.assertEqual(seen["by"], "user")
            self.assertAlmostEqual(seen["usd"], quality_tier.scene_final_price(self.p.conn, self.s1), places=4)
            route = quality_tier.final_route(self.p.conn, self.p.job(f2), _provider())
            self.assertIsNone(quality_tier.needs_confirm(self.p.job(f2), route))

    def test_an_upgradable_draft_needs_no_extra_yes(self):
        with ON:
            self.approved_draft()
            self.assertTrue(quality_tier.final_offer(self.p.conn, self.s1)["upgrade"])
            f = quality_tier.request_final(self.p, self.s1)
            self.assertIsNone(self.p.job(f)["confirm_new"])


class GroupKeepsDraftsTests(Base):
    N = 3

    def test_group_final_keeps_the_followers_draft_clips(self):
        vids = os.path.join(self.data, str(self.pid), "videos")
        os.makedirs(vids, exist_ok=True)
        drafts = []
        for i, sid in enumerate(self.sids, 1):
            path = os.path.join(vids, f"{i:02d}.mp4")
            with open(path, "wb") as fh:
                fh.write(f"draft-{i}".encode())
            drafts.append(self.approved_draft(sid, path=path))
        leader = self.p.create_job(self.s1, "video_gen")
        self.p.conn.execute("UPDATE jobs SET external_id='seedance:final', model='seedance-2.5' WHERE id=?", (leader,))
        self.p.conn.commit()
        vr = VideoRunner(self.p, _provider(), self.data)
        group = [{"id": sid, "idx": i, "refs": False, "data": {"duration_s": 4}} for i, sid in enumerate(self.sids, 1)]

        def split(path, grp, dests):
            for i, dest in enumerate(dests[1:], 2):
                with open(dest, "wb") as fh:
                    fh.write(f"final-{i}".encode())

        from core import takes
        takes.make_room(self.p.conn, self.data, self.p.job(leader), os.path.join(vids, "01.mp4"))   # what poll does for the leader
        with open(os.path.join(vids, "01.mp4"), "wb") as fh:
            fh.write(b"final-1")
        with mock.patch("core.shots.split_group_clip", side_effect=split), mock.patch("core.shots.trim_clip"), \
                mock.patch.object(vr, "_clean_edges"), mock.patch.object(vr, "_motion", return_value=None):
            vr._finish_group(self.p.job(leader), os.path.join(vids, "01.mp4"), group)
        for i, d in enumerate(drafts, 1):
            rp = self.p.job(d)["result_path"]
            self.assertNotEqual(os.path.normcase(rp), os.path.normcase(os.path.join(vids, f"{i:02d}.mp4")), i)
            with open(rp, "rb") as fh:
                self.assertEqual(fh.read(), f"draft-{i}".encode(), i)          # the draft clip is still there, under its job
        with open(os.path.join(vids, "02.mp4"), "rb") as fh:
            self.assertEqual(fh.read(), b"final-2")
        back = self.p.use_older_take(drafts[1], data_dir=self.data)          # ↩ Dùng bản này on shot 2's approved draft
        with open(back, "rb") as fh:
            self.assertEqual(fh.read(), b"draft-2")


class GroupPriceTests(Base):
    N = 3

    def groups(self):
        for sid in self.sids:                                                 # 3 shots × 2 s = one 6 s group clip
            self.p.conn.execute("UPDATE motion_prompts SET duration_sec=2 WHERE scene_id=?", (sid,))
        self.p.conn.commit()
        rows = [{"id": sid, "idx": i, "data": {"duration_s": 2}} for i, sid in enumerate(self.sids, 1)]
        return mock.patch("core.seedance_refs.enabled", return_value=True), mock.patch("core.seedance_refs.groups", return_value=[rows])

    def test_gen_video_button_prices_one_group_clip(self):
        for sid in self.sids:
            self.p.conn.execute("UPDATE motion_prompts SET duration_sec=2 WHERE scene_id=?", (sid,))
        self.p.conn.commit()
        a, b = self.groups()
        with a, b:
            tag = cost.video_button_tag(self.p.conn, self.sids)
            self.assertIn(" 1 clip ≈", tag)                                   # was 3 clips × ≥ 4 s
            one = cost.clip_estimate(self.p.conn, self.s1, seconds=6.0)
            self.assertIn(f"{one:.2f}", tag)

    def test_final_price_follows_the_group_clip(self):
        with ON:
            for sid in self.sids:
                self.approved_draft(sid)
            a, b = self.groups()
            with a, b:
                lead = quality_tier.scene_final_price(self.p.conn, self.s1)
                want = quality_tier.upgrade_price("9:16", 6.0)
                self.assertAlmostEqual(lead, round(want, 4))
                # rà F3: a follower alone pulls the group clip → the group's price until the leader's final exists, then 0
                self.assertAlmostEqual(quality_tier.scene_final_price(self.p.conn, self.sids[1]), round(want, 4))
                quality_tier.request_final(self.p, self.s1)
                self.assertEqual(quality_tier.scene_final_price(self.p.conn, self.sids[1]), 0.0)


class FilmEstimateTests(Base):
    N = 3

    def test_e1_estimate_of_the_whole_film(self):
        self.label("easy", self.sids[0])
        self.label("easy", self.sids[1])
        self.label("complex", self.sids[2])
        quality_tier.set_path(self.p.conn, self.sids[0], "direct")      # người chọn gen thẳng; sids[1] 'easy' tự động gen thẳng (15/10)
        with ON:
            est = quality_tier.e1_estimate(self.p.conn, self.pid)
        direct = cost.seedance_estimate(quality_tier.SAMPLE_MODEL, "720p", "9:16", 4.0)   # 13/10: gen thẳng = Seedance 2.5 720p
        draft = cost.seedance_estimate(quality_tier.SAMPLE_MODEL, "480p", "9:16", 4.0)
        final = quality_tier.upgrade_price("9:16", 4.0)
        self.assertAlmostEqual(est["usd"], round(2 * direct + draft + final, 2))
        self.assertEqual((est["direct"], est["draft_first"], est["film_seconds"], est["target_usd"]), (2, 1, 12.0, 30.0))
        self.assertTrue(est["within"])
        self.assertIn("mục tiêu < 30 USD", est["line"])
        self.assertIn("ƯỚC TÍNH", est["line"])


class UpscaleRenderTests(unittest.TestCase):
    def test_fit_filter_upscales_with_lanczos_and_light_unsharp(self):
        self.assertNotIn("lanczos", ffmpeg_studio._fit((1080, 1920)))        # unchanged for a clip at the frame size
        f = ffmpeg_studio._fit((1080, 1920), upscale=True)
        self.assertIn(f"flags={ffmpeg_studio.UPSCALE_FLAGS}", f)
        self.assertIn("unsharp=", f)

    def test_a_720p_clip_is_rendered_at_1080x1920_and_listed(self):
        from core import delivery, final_cut
        try:
            ff = ffmpeg_studio.find_ffmpeg()
        except Exception:  # noqa: BLE001
            self.skipTest("ffmpeg missing")
        data = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, data, True)
        p = Pipeline(connect())
        pid = p.create_project("render", aspect="9:16")
        for idx, size in ((1, "720x1280"), (2, "1080x1920")):
            sid = p.create_scene(pid, idx, f"s{idx}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"story_scene": 1, "shot_no": idx}), sid))
            path = final_cut.clip_path(data, pid, idx)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=0x808080:s={size}:d=1", "-f", "lavfi",
                            "-i", "sine=frequency=440:duration=1", "-shortest", "-pix_fmt", "yuv420p", "-c:a", "aac", path], check=True)
        p.conn.commit()
        res = delivery.render(p, pid, data, music_path=None, settings=dict(delivery.get_settings(p, pid), keep_audio=True))
        self.assertEqual(ffmpeg_studio.probe_size(res["path"]), (1080, 1920))
        man = json.loads(p.conn.execute("SELECT manifest FROM outputs WHERE id=?", (res["output_id"],)).fetchone()["manifest"])
        self.assertEqual(man["upscaled"], [1])                                # only the 720p clip; the 1080p one stays as it is
        self.assertIn("lanczos", man["upscale"]["how"])


# ---- rà độc lập F3 (09/10): nhóm trộn dễ/khó, giá bản cao theo nhóm, lỗi đọc hạn nháp tạm thời, nhãn gen mới, gửi lại giữ xác nhận ----
def GROUP(sids):
    return mock.patch("core.shots.group_of", side_effect=lambda c, s: [{"id": x} for x in sids])


def _send(vr, pid):
    """The runner's real send loop, inputs stubbed (as tests/test_quality_tier.py RunnerTierTests.send)."""
    with mock.patch.object(vr, "_submit_args", return_value=("i.png", "she dances", None, 4, "seedance-2.5")), \
            mock.patch.object(vr, "_blocked", return_value=None), mock.patch.object(vr, "_stamp", return_value={}), \
            mock.patch.object(vr, "_over_budget", return_value=None), mock.patch.object(vr, "_wait", return_value=False):
        return vr._submit_pending(pid)


class MixedGroupTierTests(Base):
    N = 2

    def test_easy_leader_of_a_group_with_a_hard_shot_is_sent_as_a_2_5_draft(self):
        self.label("easy", self.sids[0])
        self.label("complex", self.sids[1])
        with ON, GROUP(self.sids):
            jid = self.p.create_job(self.sids[0], "video_gen")
            self.assertEqual(self.p.job(jid)["quality_tier"], "draft")
            kw = VideoRunner(self.p, _provider(), self.data)._submit_kwargs(self.p.job(jid))
            self.assertEqual((kw.get("draft"), kw.get("resolution")), (True, "480p"))

    def test_easy_follower_of_a_hard_group_is_a_draft_too(self):
        self.label("complex", self.sids[0])
        self.label("easy", self.sids[1])
        with ON, GROUP(self.sids):
            jid = self.p.create_job(self.sids[1], "video_gen")
            self.assertEqual(self.p.job(jid)["quality_tier"], "draft")


class MixedGroupPriceTests(Base):
    N = 3

    def groups(self):
        return GroupPriceTests.groups(self)

    def test_final_price_of_a_mixed_group_is_the_group_clip_not_zero(self):
        self.label("easy", self.sids[0])
        with ON, GROUP(self.sids):
            for sid in self.sids:
                self.approved_draft(sid)                                       # the easy leader's take is a draft too (group)
            a, b = self.groups()
            with a, b:
                want = round(quality_tier.upgrade_price("9:16", 6.0), 4)
                est = quality_tier.final_estimate(self.p.conn, self.pid)
                self.assertAlmostEqual(est["usd"], want, places=2)
                # a follower clicked alone pulls the whole group clip: priced as the group while the leader has no final
                self.assertAlmostEqual(quality_tier.scene_final_price(self.p.conn, self.sids[1]), want, places=4)
                self.assertAlmostEqual(quality_tier.batch_final_price(self.p.conn, self.sids), want, places=4)
                self.assertAlmostEqual(quality_tier.batch_final_price(self.p.conn, self.sids[1:]), want, places=4)
                quality_tier.request_final(self.p, self.sids[0])
                self.assertEqual(quality_tier.scene_final_price(self.p.conn, self.sids[1]), 0.0)


class TransientDraftReadTests(Base):
    def test_a_failed_expiry_read_keeps_the_final_queued_and_does_not_lock_the_upgrade(self):
        with ON:
            self.approved_draft()
            f = quality_tier.request_final(self.p, self.s1)
            prov = _provider()
            prov.task_usage = mock.Mock(side_effect=RuntimeError("timeout"))
            prov.submit = mock.Mock(return_value="seedance:new")
            prov.submit_final_from_sample = mock.Mock(return_value="seedance:up")
            vr = VideoRunner(self.p, prov, self.data)
            self.assertIsNone(quality_tier.needs_confirm(self.p.job(f), quality_tier.final_route(self.p.conn, self.p.job(f), prov)))
            self.assertEqual(_send(vr, self.pid), 0)
            self.assertEqual(self.p.job(f)["state"], "queued")
            prov.submit.assert_not_called()
            self.assertTrue(quality_tier.final_offer(self.p.conn, self.s1)["upgrade"])
            prov.task_usage = mock.Mock(return_value={"is_draft": True, "draft_expired_at": 9e12})
            self.assertEqual(_send(vr, self.pid), 1)
            prov.submit_final_from_sample.assert_called_once()
            prov.submit.assert_not_called()

    def test_old_failures_from_a_read_error_do_not_count_as_not_upgradable(self):
        with ON:
            d = self.approved_draft()
            f = self.p._insert_job(self.pid, self.s1, "video_gen", quality_tier="final", draft_job_id=d)
            self.p.start(f)
            self.p.fail(f, f"stale_input: bản cao bị chặn: {quality_tier.NEED_CONFIRM} — {quality_tier.NEW_GEN} "
                           "(không đọc được hạn bản nháp (timeout))")
            self.assertIsNone(quality_tier.upgrade_block(self.p.conn, self.p.job(d)))


class NewFinalLabelTests(Base):
    def test_the_new_final_offer_says_its_real_resolution(self):
        self.label("complex")
        with ON:
            self.approved_draft(model="seedance")
            offer = quality_tier.final_offer(self.p.conn, self.s1)
            self.assertFalse(offer["upgrade"])
            self.assertEqual(offer["res"], quality_tier.final_resolution("seedance-2.5"))
            self.assertIn("720p", offer["res_note"])
            self.assertIn("chưa có 1080p", offer["res_note"])
            from dashboard import quality_ui
            label, ask = quality_ui.new_final_texts(offer, 1.5)
            for text in (label, ask):
                self.assertIn("720p", text)
                self.assertIn("1.50 USD", text)


class ResendKeepsYesTests(Base):
    def test_a_plain_resend_of_a_confirmed_new_final_keeps_the_yes(self):
        from core.runner import RESEND_NOTE
        self.label("complex")
        with ON:
            self.approved_draft(model="seedance")
            f = quality_tier.request_final(self.p, self.s1, confirm_new=True)
            child = self.p._insert_job(self.pid, self.s1, "video_gen", parent_job_id=f, retry_count=1, retry_reason=RESEND_NOTE)
            self.assertEqual(self.p.job(child)["confirm_new"], self.p.job(f)["confirm_new"])
            other = self.p._insert_job(self.pid, self.s1, "video_gen", parent_job_id=f, retry_count=1, retry_reason="tay trái sai")
            self.assertIsNone(self.p.job(other)["confirm_new"])            # a fix sentence: its own rule (needs_confirm), not the old yes


class GroupRawTests(Base):
    N = 2

    def test_a_group_clip_moves_the_followers_old_raw_clip_too(self):
        vids = os.path.join(self.data, str(self.pid), "videos")
        os.makedirs(vids, exist_ok=True)
        drafts = []
        for i, sid in enumerate(self.sids, 1):
            path = os.path.join(vids, f"{i:02d}.mp4")
            for name, body in ((path, f"draft-{i}"), (os.path.join(vids, f"{i:02d}_raw.mp4"), f"raw-{i}")):
                with open(name, "wb") as fh:
                    fh.write(body.encode())
            drafts.append(self.approved_draft(sid, path=path))
        leader = self.p.create_job(self.s1, "video_gen")
        self.p.conn.execute("UPDATE jobs SET external_id='seedance:final', model='seedance-2.5' WHERE id=?", (leader,))
        self.p.conn.commit()
        vr = VideoRunner(self.p, _provider(), self.data)
        group = [{"id": sid, "idx": i, "refs": False, "data": {"duration_s": 4}} for i, sid in enumerate(self.sids, 1)]

        def split(path, grp, dests):
            with open(dests[1], "wb") as fh:
                fh.write(b"final-2")

        with mock.patch("core.shots.split_group_clip", side_effect=split), mock.patch("core.shots.trim_clip"), \
                mock.patch.object(vr, "_clean_edges"), mock.patch.object(vr, "_motion", return_value=None):
            vr._finish_group(self.p.job(leader), os.path.join(vids, "01.mp4"), group)
        self.assertFalse(os.path.exists(os.path.join(vids, "02_raw.mp4")))     # the old take's uncut clip is not left for the new one
        from core import trash
        raws = [e for e in trash.items(self.data, self.pid, "videos") if e["original"].endswith("02_raw.mp4")]
        self.assertEqual([e["job_id"] for e in raws], [drafts[1]])
        back = self.p.use_older_take(drafts[1], data_dir=self.data)           # the clip comes back, not its raw
        with open(back, "rb") as fh:
            self.assertEqual(fh.read(), b"draft-2")


if __name__ == "__main__":
    unittest.main()


class MeasuredUpgradeTests(Base):
    N = 3

    def test_upgrade_route_uses_measured_seconds_without_resending_ref(self):
        self.assertAlmostEqual(quality_tier.upgrade_price("9:16", 38), 19.9652)
        self.assertGreater(quality_tier.upgrade_price("16:9", 38), 0)

    def test_sent_group_survives_ref_flag_off_and_motion_edit(self):
        with ON:
            jid = self.approved_draft()
        group = [{"id": sid, "duration_s": n} for sid, n in zip(self.sids, (3, 2, 3))]
        self.p.conn.execute("UPDATE jobs SET sent_group=? WHERE id=?", (json.dumps(group), jid))
        self.p.conn.execute("UPDATE motion_prompts SET duration_sec=12 WHERE scene_id=?", (self.s1,))
        self.p.conn.commit()
        with mock.patch("core.seedance_refs.enabled", return_value=False):
            groups = quality_tier._clip_groups(self.p.conn, self.pid)
            self.assertEqual(groups[self.sids[1]], (self.s1, 8.0))
            self.assertAlmostEqual(quality_tier.scene_final_price(self.p.conn, self.s1), round(8 * .5254, 4))
            self.assertAlmostEqual(quality_tier.batch_final_price(self.p.conn, self.sids), round(8 * .5254, 4))

    def test_final_ledger_uses_original_group_seconds(self):
        with ON:
            draft = self.approved_draft()
        group = [{"id": sid, "duration_s": n} for sid, n in zip(self.sids, (3, 2, 3))]
        self.p.conn.execute("UPDATE jobs SET sent_group=? WHERE id=?", (json.dumps(group), draft))
        final = self.p.create_job(self.s1, "video_gen")
        self.p.conn.execute("UPDATE jobs SET quality_tier='final', draft_job_id=?, sent_package=? WHERE id=?", (draft, json.dumps({"call": "submit_final_from_sample"}), final))
        cost.record_usage(self.p.conn, final, "video", "mock-video", quality_tier.SAMPLE_MODEL, "1080p", 4, "second")
        self.assertEqual(self.p.conn.execute("SELECT quantity FROM usage_events WHERE job_id=?", (final,)).fetchone()[0], 8)

    def test_unknown_seedance_reference_is_conservative_and_other_models_ignore_it(self):
        self.p.conn.execute("UPDATE motion_prompts SET ref_video_path='missing.mp4' WHERE scene_id=?", (self.s1,))
        self.p.conn.commit()
        with mock.patch("core.model_router.scene_choice", return_value={"model": "seedance-2.5", "resolution": "720p"}):
            price = cost.clip_estimate(self.p.conn, self.s1)
        self.assertGreaterEqual(price, cost.seedance_estimate(quality_tier.SAMPLE_MODEL, "720p", "9:16", 4, 15))
        with mock.patch("core.model_router.scene_choice", return_value={"model": "kling", "resolution": "pro"}):
            self.assertIsNotNone(cost.clip_estimate(self.p.conn, self.s1))

    def test_new_generation_final_keeps_its_own_seconds(self):
        with ON:
            draft = self.approved_draft()
        group = [{"id": sid, "duration_s": n} for sid, n in zip(self.sids, (3, 2, 3))]
        self.p.conn.execute("UPDATE jobs SET sent_group=? WHERE id=?", (json.dumps(group), draft))
        final = self.p.create_job(self.s1, "video_gen")
        self.p.conn.execute("UPDATE jobs SET quality_tier='final', draft_job_id=?, sent_package=? WHERE id=?", (draft, json.dumps({"call": "submit"}), final))
        cost.record_usage(self.p.conn, final, "video", "mock-video", quality_tier.SAMPLE_MODEL, "1080p", 4, "second")
        self.assertEqual(self.p.conn.execute("SELECT quantity FROM usage_events WHERE job_id=?", (final,)).fetchone()[0], 4)

    def test_new_independent_draft_is_not_absorbed_by_historical_group(self):
        with ON:
            old = self.approved_draft()
            self.approved_draft(self.sids[1])
        group = [{"id": sid, "duration_s": 4} for sid in self.sids]
        self.p.conn.execute("UPDATE jobs SET sent_group=? WHERE id=?", (json.dumps(group), old))
        with mock.patch("core.seedance_refs.enabled", return_value=False):
            groups = quality_tier._clip_groups(self.p.conn, self.pid)
            self.assertNotIn(self.sids[1], groups)
            self.assertGreater(quality_tier.batch_final_price(self.p.conn, self.sids), 12 * .5254)
        planned = [{"id": sid, "data": {"duration_s": 4}} for sid in self.sids]
        with mock.patch("core.seedance_refs.enabled", return_value=True), mock.patch("core.seedance_refs.groups", return_value=[planned]):
            self.assertNotIn(self.sids[1], quality_tier._clip_groups(self.p.conn, self.pid))

    def test_new_leader_draft_supersedes_its_historical_group(self):
        with ON:
            old = self.approved_draft()
            self.approved_draft()
        group = [{"id": sid, "duration_s": 4} for sid in self.sids]
        self.p.conn.execute("UPDATE jobs SET sent_group=? WHERE id=?", (json.dumps(group), old))
        with mock.patch("core.seedance_refs.enabled", return_value=False):
            self.assertEqual(quality_tier._clip_groups(self.p.conn, self.pid), {})
        planned = [{"id": sid, "data": {"duration_s": 4}} for sid in self.sids]
        with mock.patch("core.seedance_refs.enabled", return_value=True), mock.patch("core.seedance_refs.groups", return_value=[planned]):
            self.assertEqual(quality_tier._clip_groups(self.p.conn, self.pid), {})

    def test_single_draft_uses_actual_local_clip_duration_before_submitted_seconds(self):
        path = os.path.join(self.data, 'draft.mp4')
        with open(path, 'wb') as f:
            f.write(b'local fixture')
        with ON:
            draft = self.approved_draft(path=path)
        self.p.conn.execute("UPDATE jobs SET sent_package=? WHERE id=?", (json.dumps({'params': {'duration_sec': 4}}), draft))
        cost.record_usage(self.p.conn, draft, 'video', 'mock', quality_tier.SAMPLE_MODEL, '480p', 4, 'second')
        with mock.patch('core.ffmpeg_studio.probe_duration', return_value=5.5):
            self.assertEqual(quality_tier.draft_seconds(self.p.conn, self.p.job(draft)), 5.5)
            self.assertAlmostEqual(quality_tier.scene_final_price(self.p.conn, self.s1), round(5.5 * .5254, 4))


# ---- 12/10 (#24): bản cao nâng từ nháp — cắt ĐÚNG đoạn nháp, follower ra 1080p từ clip nhóm cao, sổ chi = giây clip nhóm ----------------
def _ff():
    try:
        return ffmpeg_studio.find_ffmpeg()
    except Exception:  # noqa: BLE001
        return None


def _ramp(path, seconds, size):
    """A clip whose brightness rises 20 per second: the first frame of a cut says where in the task clip the cut started."""
    subprocess.run([_ff(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=black:s={size}:d={seconds}:r=24",
                    "-vf", "format=yuv420p,geq=lum='min(255,T*20)':cb=128:cr=128", "-pix_fmt", "yuv420p", path], check=True)


def _start_second(path):
    w, h = ffmpeg_studio.probe_size(path)                 # the Y plane as written by geq (no range conversion)
    out = subprocess.run([_ff(), "-v", "error", "-i", path, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"],
                         capture_output=True).stdout[:w * h]
    return sum(out) / len(out) / 20.0


class _Clips:
    """MockVideoProvider (no paid call) whose download writes a real ramp clip: 480p-ish for a draft, 1080p-ish for an upgrade."""
    def __init__(self, seconds):
        from core.providers import MockVideoProvider
        self.prov = MockVideoProvider(polls_to_finish=1)
        self.prov.task_usage = lambda ext: {"is_draft": True, "draft_expired_at": 9e12}
        self.prov.download = self.download
        self.seconds = seconds
        self.upgrades = []
        real = self.prov.submit_final_from_sample

        def upgrade(ext, resolution="1080p"):
            self.upgrades.append(ext)
            return real(ext, resolution=resolution)
        self.prov.submit_final_from_sample = upgrade

    def download(self, task_id, dest):
        task = self.prov._tasks.get(task_id) or {}
        _ramp(dest, self.seconds, "108x192" if task.get("from_sample") else "48x64")
        return dest


@unittest.skipUnless(_ff(), "ffmpeg missing")
class UpgradeCutsTheDraftPartTests(Base):
    """Runner thật (send + poll) với nhà cung cấp giả: nháp nhóm → duyệt → nâng 1080p từ task nháp."""
    N = 3

    def setUp(self):
        super().setUp()
        self.clips = _Clips(8)
        self.vr = VideoRunner(self.p, self.clips.prov, self.data)
        for pt in (ON, mock.patch("core.shots.clean_edges", return_value=None)):
            pt.start()
            self.addCleanup(pt.stop)

    def poll(self):
        return self.vr._poll_once(self.pid)

    def group_draft(self):
        """The leader's group draft (3 shots: 1–4 s, 4–6 s, 6–8 s of an 8 s task clip), downloaded by the runner and approved."""
        ext = self.clips.prov.submit("i.png", "group", None, 8, model="seedance-2.5", draft=True)
        lead = self.p.create_job(self.s1, "video_gen")
        sent = [{"id": self.sids[0], "idx": 1, "exact": True, "duration_s": 3, "offset": 1.0},
                {"id": self.sids[1], "idx": 2, "exact": True, "duration_s": 2},
                {"id": self.sids[2], "idx": 3, "exact": True, "duration_s": 2}]
        self.p.conn.execute("UPDATE jobs SET external_id=?, model='seedance-2.5', sent_group=? WHERE id=?", (ext, json.dumps(sent), lead))
        self.p.conn.commit()
        self.p.start(lead)
        self.poll()
        drafts = {r["scene_id"]: r["id"] for r in self.p.conn.execute("SELECT * FROM jobs WHERE type='video_gen' AND quality_tier='draft'")}
        self.assertEqual(len(drafts), 3)
        for jid in drafts.values():
            self.p.approve(jid, "user")
        return drafts

    def final(self, sid=None):
        f = quality_tier.request_final(self.p, sid or self.s1)
        _send(self.vr, self.pid)
        return f

    def test_leader_final_is_cut_at_the_drafts_part(self):
        self.group_draft()
        f = self.final()
        self.poll()
        job = self.p.job(f)
        self.assertEqual(job["state"], "succeeded")
        self.assertEqual(ffmpeg_studio.probe_size(job["result_path"]), (108, 192))
        self.assertAlmostEqual(_start_second(job["result_path"]), 1.0, delta=0.3)       # the draft's part started at 1 s, not 0 s
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(job["result_path"]), 3.0, delta=0.15)

    def test_followers_get_their_1080p_part_from_the_group_clip(self):
        drafts = self.group_draft()
        f = self.final()
        self.poll()
        self.assertEqual(self.clips.upgrades, [self.p.job(drafts[self.s1])["external_id"]])     # one paid upgrade for the group
        for sid, start in ((self.sids[1], 4.0), (self.sids[2], 6.0)):
            row = self.p.conn.execute("SELECT * FROM jobs WHERE scene_id=? AND quality_tier='final'", (sid,)).fetchone()
            self.assertIsNotNone(row, sid)
            self.assertEqual((row["state"], row["group_leader"], row["external_id"]), ("succeeded", f, self.p.job(f)["external_id"]))
            draft = self.p.job(drafts[sid])
            self.assertEqual((row["source_job_id"], row["input_hash"], row["draft_job_id"]),
                             (draft["source_job_id"], draft["input_hash"], draft["id"]))
            self.assertIsNotNone(row["input_hash"])
            self.assertEqual(ffmpeg_studio.probe_size(row["result_path"]), (108, 192))
            self.assertAlmostEqual(_start_second(row["result_path"]), start, delta=0.3)
            self.assertAlmostEqual(ffmpeg_studio.probe_duration(row["result_path"]), 2.0, delta=0.15)
            self.assertEqual(quality_tier.state(self.p.conn, sid), "final_review")

    def test_follower_whose_motion_changed_is_not_cut_silently(self):
        self.group_draft()
        llm_io.store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": 3, "motion_prompt": "she runs away", "duration_sec": 4}]})
        llm_io.approve_motion_prompt(self.p, self.sids[2])
        f = self.final()
        self.poll()
        self.assertIsNone(self.p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND quality_tier='final'", (self.sids[2],)).fetchone())
        notes = [m for (m,) in self.p.conn.execute("SELECT message FROM diag_events WHERE code='final_follower_skipped'")]
        self.assertEqual(len(notes), 1)
        self.assertIn("S03", notes[0])
        self.assertIn("đầu vào đã đổi", notes[0])
        self.assertIsNotNone(self.p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND quality_tier='final' AND state='succeeded'",
                                                 (self.sids[1],)).fetchone())
        self.assertEqual(self.p.job(f)["state"], "succeeded")

    def test_a_follower_final_asked_meanwhile_waits_and_is_not_paid_twice(self):
        self.group_draft()
        quality_tier.request_final(self.p, self.s1)
        f2 = quality_tier.request_final(self.p, self.sids[1])
        _send(self.vr, self.pid)
        self.assertEqual(len(self.clips.upgrades), 1)
        self.assertEqual(self.p.job(f2)["state"], "queued")
        self.poll()
        self.assertEqual(self.p.job(f2)["state"], "succeeded")                      # its part came with the group clip
        self.assertAlmostEqual(_start_second(self.p.job(f2)["result_path"]), 4.0, delta=0.3)
        _send(self.vr, self.pid)
        self.assertEqual(len(self.clips.upgrades), 1)

    def test_ledger_records_the_group_clip_seconds_once(self):
        self.group_draft()
        f = self.final()
        self.poll()
        rows = self.p.conn.execute("SELECT job_id, quantity FROM usage_events WHERE kind='video' AND job_id IN "
                                   "(SELECT id FROM jobs WHERE quality_tier='final')").fetchall()
        self.assertEqual([(r["job_id"], round(r["quantity"], 1)) for r in rows], [(f, 8.0)])


@unittest.skipUnless(_ff(), "ffmpeg missing")
class UpgradeLoneTrimmedDraftTests(Base):
    """#24 shot 05: a lone draft cut at 1,833–4,833 s of its 5 s clip; the final must be that very part, the ledger 5 s."""

    def setUp(self):
        super().setUp()
        self.clips = _Clips(5)
        self.vr = VideoRunner(self.p, self.clips.prov, self.data)
        ON.start()
        self.addCleanup(ON.stop)
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.s1,)).fetchone()[0] or "{}")
        data.update(shot_no=1)
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), self.s1))
        self.p.conn.execute("UPDATE motion_prompts SET duration_sec=3 WHERE scene_id=?", (self.s1,))
        self.p.conn.commit()

    def test_final_is_cut_where_the_draft_was_cut_and_billed_on_the_whole_clip(self):
        ext = self.clips.prov.submit("i.png", "lone", None, 5, model="seedance-2.5", draft=True)
        d = self.p.create_job(self.s1, "video_gen")
        self.p.conn.execute("UPDATE jobs SET external_id=?, model='seedance-2.5' WHERE id=?", (ext, d))
        self.p.conn.commit()
        self.p.start(d)
        with mock.patch("core.shots.motion_start", return_value=1.833):
            self.vr._poll_once(self.pid)
        self.assertAlmostEqual(_start_second(self.p.job(d)["result_path"]), 1.833, delta=0.3)
        self.p.approve(d, "user")
        f = quality_tier.request_final(self.p, self.s1)
        _send(self.vr, self.pid)
        with mock.patch("core.shots.motion_start", return_value=0.0):          # the 1080p clip read again would cut elsewhere
            self.vr._poll_once(self.pid)
        job = self.p.job(f)
        self.assertEqual(ffmpeg_studio.probe_size(job["result_path"]), (108, 192))
        self.assertAlmostEqual(_start_second(job["result_path"]), 1.833, delta=0.3)
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(job["result_path"]), 3.0, delta=0.15)
        q = self.p.conn.execute("SELECT quantity FROM usage_events WHERE job_id=?", (f,)).fetchone()[0]
        self.assertAlmostEqual(q, 5.0, delta=0.1)


# ---- 12/10 rà độc lập: sửa 6 lỗi của nhánh nâng bản cao clip nhóm ----------------------------------------------------------------------
@unittest.skipUnless(_ff(), "ffmpeg missing")
class UpgradeReviewFixTests(UpgradeCutsTheDraftPartTests):
    """Kế thừa dựng nháp nhóm 3 shot (1–4 s, 4–6 s, 6–8 s) — chỉ chạy các test mới dưới đây (các test cha chạy ở lớp cha)."""

    def _videos(self):
        return os.path.join(self.data, str(self.pid), "videos")

    def test_recut_by_hand_moves_where_the_final_is_cut(self):
        from core import seedance_refs
        drafts = self.group_draft()
        seedance_refs.recut(self.p, drafts[self.s1], [2.0, 5.0])
        f = self.final()
        self.poll()
        lead = self.p.job(f)
        # the person's cut (0 s), not the automatic 1 s — a re-encoded cut keeps Y >= 16 (limited range), so 0 s reads 16/20 = 0.8
        self.assertAlmostEqual(_start_second(lead["result_path"]), 0.8, delta=0.1)
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(lead["result_path"]), 2.0, delta=0.15)
        for sid, start, sec in ((self.sids[1], 2.0, 3.0), (self.sids[2], 5.0, 3.0)):
            row = self.p.conn.execute("SELECT * FROM jobs WHERE scene_id=? AND quality_tier='final'", (sid,)).fetchone()
            self.assertEqual(row["state"], "succeeded")
            self.assertAlmostEqual(_start_second(row["result_path"]), start, delta=0.3)
            self.assertAlmostEqual(ffmpeg_studio.probe_duration(row["result_path"]), sec, delta=0.15)

    def test_leader_final_whose_cut_fails_is_red_and_failed(self):
        from core import seedance_refs
        self.group_draft()
        f = self.final()

        def broken(whole, bounds, dests, ffmpeg):        # ffmpeg failing: _cut_parts copies the whole clip
            for d in dests:
                shutil.copyfile(whole, d)
            return list(dests)
        with mock.patch.object(seedance_refs, "_cut_parts", side_effect=broken):
            self.poll()
        self.assertEqual(self.p.job(f)["state"], "failed")
        sev = [s for (s,) in self.p.conn.execute("SELECT severity FROM diag_events WHERE code='final_cut' AND job_id=?", (f,))]
        self.assertEqual(sev, ["error"])
        self.assertTrue(os.path.isfile(os.path.join(self._videos(), "01_group.mp4")))      # the paid 1080p clip kept for ✂
        self.assertEqual(len(self.clips.upgrades), 1)

    def test_follower_cut_failure_keeps_the_drafts_file_in_place(self):
        from core import seedance_refs
        drafts = self.group_draft()
        self.final()
        real = seedance_refs._cut_parts

        def broken_02(whole, bounds, dests, ffmpeg):
            if os.path.basename(dests[0]) == "02.mp4":
                shutil.copyfile(whole, dests[0])
                return list(dests)
            return real(whole, bounds, dests, ffmpeg)
        with mock.patch.object(seedance_refs, "_cut_parts", side_effect=broken_02):
            self.poll()
        draft = self.p.job(drafts[self.sids[1]])
        self.assertEqual(os.path.normcase(os.path.abspath(draft["result_path"])),
                         os.path.normcase(os.path.abspath(os.path.join(self._videos(), "02.mp4"))))
        self.assertEqual(ffmpeg_studio.probe_size(draft["result_path"]), (48, 64))       # still the approved 480p draft part
        self.assertAlmostEqual(_start_second(draft["result_path"]), 4.0, delta=0.3)

    def test_no_whole_recorded_when_the_clip_cannot_be_measured(self):
        with mock.patch("core.runner._probe", return_value=None):
            drafts = self.group_draft()
        for jid in drafts.values():
            span = json.loads(self.p.job(jid)["clip_span"])
            self.assertIsNone(span["whole"], jid)


class SharedTaskGuardTests(Base):
    """_final_shared_task: chỉ chặn khi NÂNG THẬT từ task nháp 2.5; trong các final cùng task nháp, id nhỏ nhất gửi trước."""
    N = 2

    def setUp(self):
        super().setUp()
        from core.providers import MockVideoProvider
        self.vr = VideoRunner(self.p, MockVideoProvider(), self.data)

    def drafts(self, model):
        out = [self.approved_draft(sid, model=model) for sid in self.sids]
        self.p.conn.execute(f"UPDATE jobs SET external_id='T' WHERE id IN ({','.join(map(str, out))})")
        self.p.conn.commit()
        return out

    def final_row(self, sid, draft, state="queued", ext=None, call=None):
        jid = self.p.create_job(sid, "video_gen")
        self.p.conn.execute("UPDATE jobs SET quality_tier='final', draft_job_id=?, state=?, external_id=?, sent_package=? WHERE id=?",
                            (draft, state, ext, json.dumps({"call": call}) if call else None, jid))
        self.p.conn.commit()
        return jid

    def test_new_gen_finals_of_a_kling_group_are_not_held(self):
        d1, d2 = self.drafts("kling-v2-6")
        self.final_row(self.s1, d1, "running", "K1", "submit")
        b = self.final_row(self.sids[1], d2)
        self.assertIsNone(self.vr._final_shared_task(self.p.job(b)))
        self.p.conn.execute("UPDATE jobs SET state='succeeded' WHERE external_id='K1'")
        self.assertIsNone(self.vr._final_shared_task(self.p.job(b)))

    def test_upgrade_of_a_2_5_group_task_still_waits(self):
        d1, d2 = self.drafts("seedance-2.5")
        self.final_row(self.s1, d1, "running", "U1", "submit_final_from_sample")
        b = self.final_row(self.sids[1], d2)
        self.assertIn("_wait", self.vr._final_shared_task(self.p.job(b)) or {})

    def test_lowest_queued_final_of_a_draft_task_is_sent_first(self):
        d1, d2 = self.drafts("seedance-2.5")
        a = self.final_row(self.s1, d1)
        b = self.final_row(self.sids[1], d2)
        self.assertIsNone(self.vr._final_shared_task(self.p.job(a)))
        self.assertIn("_wait", self.vr._final_shared_task(self.p.job(b)) or {})
