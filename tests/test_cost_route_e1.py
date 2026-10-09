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
    def test_easy_shot_goes_seedance_2_0_at_720p(self):
        self.label("easy")
        with ON:
            ch = model_router.scene_choice(self.p.conn, self.s1)
            self.assertEqual((ch["model"], ch["resolution"], ch["e1"]), ("seedance", "720p", "direct"))
            self.assertIn("E1: shot dễ — 2.0 720p, dựng phóng 1080p", ch["reason"])
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
                want = cost.seedance_estimate(quality_tier.SAMPLE_MODEL, "1080p", "9:16", 6.0)
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
        est = quality_tier.e1_estimate(self.p.conn, self.pid)
        direct = cost.seedance_estimate(quality_tier.SEEDANCE_20, "720p", "9:16", 4.0)
        draft = cost.seedance_estimate(quality_tier.SAMPLE_MODEL, "480p", "9:16", 4.0)
        final = cost.seedance_estimate(quality_tier.SAMPLE_MODEL, "1080p", "9:16", 4.0)
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
                want = round(cost.seedance_estimate(quality_tier.SAMPLE_MODEL, "1080p", "9:16", 6.0), 4)
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
