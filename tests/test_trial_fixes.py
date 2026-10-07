"""Regressions for the audit before the paid trial ($10, cheap quality, 2026-09-26) — one class per audit item; each test fails on the
code before the fix. No real provider is called."""
import json
import os
import shutil
import struct
import tempfile
import threading
import unittest
import zlib
from unittest import mock

from core import assets, autopilot, audio_lib, batch, budget, cost, diag, image_models, lipsync, regen, voice
from core.db import connect
from core.llm_io import approve_motion_prompt, store_motion_prompts
from core.pipeline import PLAIN_RESEND, Pipeline
from core.providers import MockImageProvider, MockVideoProvider, ProviderError, TaskStatus
from core.runner import ImageRunner, VideoRunner, model_fix, sendable_references


def png(seed):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00" + bytes([seed, 0, 0]))) + chunk(b"IEND", b""))


def codes(p, code):
    return [r["message"] for r in p.conn.execute("SELECT message FROM diag_events WHERE code=?", (code,))]


class Base(unittest.TestCase):
    """One scene with an approved picture and an approved motion prompt."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("trial")
        self.sid = self.p.create_scene(self.pid, 1, "S1")
        self.set_data({"image_prompt": "Kelly on the rooftop at night", "characters": []})
        self.img = self.p.create_job(self.sid)
        self.p.start(self.img)
        self.p.succeed(self.img)
        self.p.approve(self.img)
        os.makedirs(os.path.join(self.dir, str(self.pid), "images"), exist_ok=True)
        with open(os.path.join(self.dir, str(self.pid), "images", f"job_{self.img}.png"), "wb") as f:
            f.write(png(1))
        store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": 1, "motion_prompt": "slow push in", "duration_sec": 5}]})
        approve_motion_prompt(self.p, self.sid)

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def set_data(self, data, sid=None):
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), sid or self.sid))
        self.p.conn.commit()

    def finished_clip(self):
        jid = self.p.create_job(self.sid, "video_gen")
        self.p.start(jid)
        path = os.path.join(self.dir, str(self.pid), "videos", "01.mp4")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(b"ORIGINAL-CLIP")
        self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (path, jid))
        self.p.conn.commit()
        self.p.succeed(jid)
        return jid, path


# ---- 1 ---------------------------------------------------------------------------------------------------------------------
class RegenCarriesTheFixTests(Base):
    def test_regenerating_a_clip_from_the_clip_set_check_sends_the_english_fix(self):
        jid, _ = self.finished_clip()
        new = regen.regenerate_video(self.p, self.dir, jid, "Đồng bộ cả bộ clip: lệch màu", fix="Match the cold blue night grade.")
        self.assertEqual(self.p.job(new)["retry_reason"], "Match the cold blue night grade.")
        motion = VideoRunner(self.p, MockVideoProvider(), self.dir)._submit_args(self.p.job(new))[1]
        self.assertIn("Fix: Match the cold blue night grade.", motion)            # not the same paid input again
        self.assertNotIn("Đồng bộ", motion)                                       # never the Vietnamese note

    def test_a_redo_whose_input_changed_sends_no_fix(self):
        jid, _ = self.finished_clip()
        new = regen.regenerate_video(self.p, self.dir, jid, "làm lại vì ảnh đổi")
        self.assertNotIn("Fix:", VideoRunner(self.p, MockVideoProvider(), self.dir)._submit_args(self.p.job(new))[1])


# ---- 2 ---------------------------------------------------------------------------------------------------------------------
class NoVietnameseNoteToTheModelTests(Base):
    def failed_image(self):
        jid = self.p.create_job(self.sid)
        self.p.start(jid)
        self.p.fail(jid, "timeout: server busy")
        return jid

    def test_a_manual_resend_of_a_failed_picture_adds_nothing_to_the_prompt(self):
        for reason in ("gen lại", "autopilot: thử lại sau lỗi tạm thời", None):
            new = self.p.retry(self.failed_image(), reason)
            self.assertTrue(self.p.job(new)["retry_reason"].startswith(PLAIN_RESEND))
            prompt = ImageRunner(self.p, MockImageProvider(), self.dir)._submit_args(self.p.job(new))[0]
            self.assertNotIn("Fix:", prompt)
            self.assertNotIn("gen lại", prompt)
            self.p.conn.execute("UPDATE jobs SET state='cancelled' WHERE id=?", (new,))
            self.p.conn.commit()

    def test_the_persons_english_fix_is_sent(self):
        new = self.p.retry(self.failed_image(), "người dùng gen lại", fix="Kelly wears the yellow jacket")
        prompt = ImageRunner(self.p, MockImageProvider(), self.dir)._submit_args(self.p.job(new))[0]
        self.assertIn("Fix: Kelly wears the yellow jacket", prompt)

    def test_a_failed_clip_resend_keeps_the_motion_prompt_unchanged(self):
        jid = self.p.create_job(self.sid, "video_gen")
        self.p.start(jid)
        self.p.fail(jid, "server_error: busy")
        new = self.p.retry(jid, "gen lại")
        self.assertNotIn("Fix:", VideoRunner(self.p, MockVideoProvider(), self.dir)._submit_args(self.p.job(new))[1])
        self.assertIsNone(model_fix(self.p.job(new)["retry_reason"]))

    def test_system_redos_send_only_the_english_fix_or_nothing(self):
        from core import claude_tasks
        claude_tasks.redo_from_set_check(self.p, self.pid, 1, "Night light, blue rim")
        row = self.p.conn.execute("SELECT retry_reason FROM jobs WHERE scene_id=? ORDER BY id DESC LIMIT 1", (self.sid,)).fetchone()
        self.assertEqual(row["retry_reason"], "Night light, blue rim")
        with self.assertRaises(ValueError):                                     # no fix = the same input again
            claude_tasks.redo_from_set_check(self.p, self.pid, 1, "")
        last = self.p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' ORDER BY id DESC LIMIT 1",
                                   (self.sid,)).fetchone()["id"]
        self.p.start(last)
        self.p.succeed(last)
        self.p.approve(last)
        self.p.reopen_approved(last, "Nội dung cảnh đã đổi: prompt", fix="")
        row = self.p.conn.execute("SELECT retry_reason FROM jobs WHERE scene_id=? ORDER BY id DESC LIMIT 1", (self.sid,)).fetchone()
        self.assertIsNone(row["retry_reason"])


# ---- 3 ---------------------------------------------------------------------------------------------------------------------
class SameFrameRedrawTests(Base):
    """07/10 Khủng Long Đỏ: the 'same frame as shot 3' redraw of a bedroom shot came out in another frame, outdoors, in the wrong cap."""

    def failed_image(self):
        jid = self.p.create_job(self.sid)
        self.p.start(jid)
        self.p.fail(jid, "timeout: server busy")
        return jid

    def test_an_automatic_redraw_keeps_the_fix_the_take_was_made_with(self):
        first = self.p.retry(self.failed_image(), "người dùng vẽ lại", fix="Same frame as the previous shot.", by_user=True)
        self.p.start(first)
        self.p.fail(first, "redraw: QC")
        auto = self.p.retry(first, "QC lớp 0", fix="Frame as a medium close-up.")
        self.assertEqual(self.p.job(auto)["retry_reason"], "Same frame as the previous shot. Frame as a medium close-up.")
        self.p.start(auto)
        self.p.fail(auto, "x")
        again = self.p.retry(auto, "người dùng", fix="Only the clothes change.", by_user=True)   # a person's new sentence replaces
        self.assertEqual(self.p.job(again)["retry_reason"], "Only the clothes change.")

    def test_a_costumed_character_takes_its_clothes_only_from_the_outfit(self):
        from core.runner import lock_note
        self.p.conn.execute("INSERT INTO characters (project_id, name, description, lock_rules, outfit_image_ids) VALUES (?,?,?,?,?)",
                            (self.pid, "MAXIM KL", "x", json.dumps({"must_keep": "black baseball cap worn backwards"}), "7"))
        self.p.conn.commit()
        note = lock_note(self.p.conn, self.pid, ["MAXIM KL"])
        self.assertIn("ONLY from the OUTFIT image", note)
        self.assertNotIn("black baseball cap", note)

    def test_a_reference_only_video_also_sends_the_outfit_picture(self):
        """07/10 Khủng Long Đỏ shot 7: the Seedance clip got only the library face picture of MAXIM KL (everyday clothes) and danced
        in them — the costume picture has to go with it, and the face picture must not dictate the clothes."""
        from core import assets, seedance_refs as sr
        pic = os.path.join(self.dir, "kl.png")
        open(pic, "wb").write(b"x")
        aid = assets.create(self.p.conn, "FF", "outfit", "KL TEST")
        cur = self.p.conn.execute("INSERT INTO asset_images (asset_id, path, label, sort, status) VALUES (?,?,?,?,?)",
                                  (aid, pic, "x", 1, "approved"))
        self.p.conn.execute("INSERT INTO characters (project_id, name, description, outfit_image_ids) VALUES (?,?,?,?)",
                            (self.pid, "MAXIM KL", "x", str(cur.lastrowid)))
        self.p.conn.commit()
        ids = sr.identity_pictures(self.p.conn, self.pid, [{"data": {"characters": ["MAXIM KL"]}}], 8)
        self.assertIn(("MAXIM KL OUTFIT", pic), ids)
        text = sr.prompt([("dance", 3)], [("MAXIM KL", "face.png"), ("MAXIM KL OUTFIT", pic)])
        self.assertIn("Image 3 is the OUTFIT MAXIM KL wears", text)
        self.assertIn("Image 2 is MAXIM KL: identity only (face, hair, body build) — NOT the clothes", text)

    def test_clipai_account_balance_not_enough_is_out_of_credit(self):
        from core.adapters.http import out_of_credit
        self.assertTrue(out_of_credit("Account balance not enough"))      # 07/10: ClipAI's words; the queue kept re-sending

    def test_an_indoor_spot_gets_no_outdoor_words_nor_the_outdoor_wide_picture(self):
        from core import location_pack, runner, scene_establish
        from core.runner import build_image_prompt
        place = {"id": 5, "name": "Tháp Đồng Hồ", "images": [], "description": "the clock tower stands on a wide open stone plaza, palms, sea"}
        entry = {"default_spot": "plaza_front", "spots": {
            "plaza_front": {"at": [0, 0, 0], "label": "quảng trường trước tháp"},
            "trong_nha_dong_t2": {"at": [1, 0, 0], "label": "trong nhà lớn phía đông — tầng 2", "indoor": {"exposure": 1.5}}}}
        room = {"image_prompt": "Maxim holds the hoodie", "location": "Phòng ngủ tầng 2 nhà lớn phía Đông, Tháp Đồng Hồ"}
        square = {"image_prompt": "Maxim waves", "location": "Quảng trường trước tháp, Tháp Đồng Hồ"}
        with mock.patch.object(assets, "scene_location", return_value=place), \
                mock.patch.object(location_pack, "model3d", return_value=entry), \
                mock.patch("core.place_refs.enabled", return_value=True):
            inside, _ = build_image_prompt(self.p.conn, self.pid, room)
            outside, _ = build_image_prompt(self.p.conn, self.pid, square)
            self.assertEqual(runner.indoor_spot(self.p.conn, self.pid, room), "trong nhà lớn phía đông — tầng 2")
            self.assertIsNone(runner.indoor_spot(self.p.conn, self.pid, square))
        self.assertIn("INSIDE a room — trong nhà lớn phía đông — tầng 2", inside)
        self.assertNotIn("stone plaza", inside)
        self.assertIn("stone plaza", outside)
        self.assertTrue(callable(scene_establish.reference))

    def test_the_shot_right_before_is_named_as_the_frame_to_keep(self):
        note = assets.reference_note([{"path": "a.png", "label": "previous shot (same camera)", "role": "same_frame"},
                                      {"path": "b.png", "label": "frame 1 (scene anchor)", "role": "previous_scene"}])
        self.assertIn("RIGHT BEFORE this one: keep exactly its camera position", note)
        self.assertIn("draw a NEW moment", note)                        # the anchor keeps its own sentence


class VoiceLoopTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("voice")
        sid = self.p.create_scene(self.pid, 1, "s")
        lines = [{"speaker": "KELLY", "text": "Đi thôi."}, {"speaker": "MAXIM", "text": "Chờ đã."}]
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_no": 1, "dialogue": lines}, ensure_ascii=False), sid))
        for n in ("KELLY", "MAXIM"):
            self.p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, ?, 'x')", (self.pid, n))
        self.p.conn.commit()
        voice.set_profile(self.p.conn, self.pid, "KELLY", {"voice_id": 71, "voice_name": "Kelly"})   # MAXIM has no voice
        self.data = tempfile.mkdtemp()

    def test_a_failed_line_is_resent_at_most_twice_and_the_missing_voice_is_a_diag(self):
        calls = []

        class Busy:
            name = "clipai-audio"

            def generate_tts(self, text, vid, model, lang, name="tts", params=None):
                calls.append(text)
                raise ProviderError("server busy", code="server", transient=True)

            def status(self, kind, asset_id):
                return TaskStatus("running")

        ctx = autopilot.Context(self.data, None, None, None, audio=Busy())
        for _ in range(8):                                                        # eight ticks of the automatic run
            autopilot._voice_phase(self.p, self.pid, ctx)
        self.assertEqual(len(calls), 1 + voice.MAX_RESENDS)                       # used to be one paid resend per tick
        self.assertTrue(codes(self.p, "no_voice"))
        self.assertTrue(codes(self.p, "voice_not_resent"))

    def test_a_refused_request_is_not_resent_unchanged_and_no_audio_provider_is_said(self):
        calls = []

        class Refuses:
            name = "clipai-audio"

            def generate_tts(self, text, vid, model, lang, name="tts", params=None):
                calls.append(text)
                raise ProviderError("HTTP 400 bad voice", code="bad_request", transient=False)

        for _ in range(4):
            voice.generate(self.p.conn, self.pid, Refuses(), self.data, ledger=False)
        self.assertEqual(len(calls), 1)                                           # a refusal needs a changed input
        voice.generate(self.p.conn, self.pid, Refuses(), self.data, ledger=False, by_person=True)
        self.assertEqual(len(calls), 2)                                           # the person's click may resend
        autopilot._voice_phase(self.p, self.pid, autopilot.Context(self.data, None, None, None, audio=None))
        self.assertTrue(codes(self.p, "no_audio_provider"))


# ---- 4 ---------------------------------------------------------------------------------------------------------------------
class BudgetPriceTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.conn = self.p.conn

    def test_a_clip_without_a_price_is_warned_while_the_limit_is_on(self):
        # S14.16 (chính sách tiền 04/10): was "refused" — estimated high and warned (warn_video); check_video refuses nothing here
        budget.restart(self.conn, usd=10.0)
        self.assertIsNone(budget.check_video(self.conn, "clipai", "kling-video-o1", "std", 5))
        self.assertIn("thiếu giá: kling-video-o1:std", budget.warn_video(self.conn, "clipai", "kling-video-o1", "std", 5))
        self.assertIsNone(budget.warn_video(self.conn, "clipai", "kling-v3-omni", "std", 5))
        budget.stop(self.conn)
        self.assertIsNone(budget.warn_video(self.conn, "clipai", "kling-video-o1", "std", 5))     # no trial round: nothing to say

    def test_a_broken_price_table_is_an_error_and_warns_on_paid_sends(self):
        # S14.16: was "refuses paid sends" — the broken table is still an error (pricing_problem) and every paid send warns
        path = os.path.join(tempfile.mkdtemp(), "pricing.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write('{"per_image": {"x": 0.05,')
        with mock.patch.dict(os.environ, {"PIPELINE_PRICING": path}):
            self.assertIn("hỏng", cost.load_pricing()["_error"])
            self.assertIsNone(budget.check_video(self.conn, "clipai", "kling-v3-omni", "std", 5))
            self.assertIn("VẪN GỬI", budget.warn_video(self.conn, "clipai", "kling-v3-omni", "std", 5))
            self.assertIsNotNone(budget.warn_image(self.conn, "deepix", "gpt-image-2.5-sunburst"))
            self.assertIsNotNone(budget.warn_audio(self.conn, "clipai-audio"))
            self.assertIsNone(budget.warn_video(self.conn, "mock", "kling-v3-omni", "std", 5))

    def test_pictures_count_against_the_usd_cap_and_audio_says_it_is_counted(self):
        budget.restart(self.conn, usd=0.1)
        budget.save(self.conn, image_cap=100, audio_cap=0)
        pid = self.p.create_project("x")
        self.assertIsNone(budget.warn_image(self.conn, "deepix", "gpt-image-2.5-sunburst"))
        cost.record_usage(self.conn, None, "image", "deepix", "gpt-image-2.5-sunburst", "image", 1, "image", project_id=pid)
        # S14.16: the same numbers, now as warnings (warn_*) — check_* refuse nothing here
        self.assertIn("vượt", budget.warn_image(self.conn, "deepix", "gpt-image-2.5-sunburst"))             # 2 × $0.052 > $0.10
        self.assertIsNone(budget.check_image(self.conn, "deepix", "gpt-image-2.5-sunburst"))
        self.assertIn("thiếu giá", budget.warn_image(self.conn, "deepix", "unknown-model"))
        self.assertIn("SỐ LƯỢT", budget.warn_audio(self.conn, "clipai-audio"))
        self.assertIsNone(budget.check_audio(self.conn, "clipai-audio"))

    def test_the_automatic_run_sends_an_unpriced_model_and_stops_only_when_out_of_credit(self):
        # S14.16: was "stops with the reason when the limit refuses" — an unpriced model is warned and sent; the run stops (with the
        # reason) only when the service is out of credit
        pid = self.p.create_project("run")
        sid = self.p.create_scene(pid, 1, "s")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": "x"}), sid))
        self.p.conn.commit()
        budget.restart(self.conn, usd=10.0)
        jid = self.p.create_job(sid)

        class Unpriced(MockImageProvider):
            name = "deepix"

            def usage_info(self):
                return "unknown-model", "image"
        ImageRunner(self.p, Unpriced(), tempfile.mkdtemp()).submit_pending(pid)
        self.assertEqual(self.p.state(jid).value, "running")                         # sent (warned in diag)
        self.assertTrue(codes(self.p, "money_warning"))
        autopilot._budget_stop(self.p, pid, "image_gen")                              # nothing to stop for
        jid2 = self.p.create_job(sid)
        budget.halt(self.conn, "deepix", "insufficient balance")
        self.p.conn.execute("UPDATE jobs SET state='succeeded' WHERE id=?", (jid,))
        self.p.conn.commit()
        ImageRunner(self.p, Unpriced(), tempfile.mkdtemp()).submit_pending(pid)
        self.assertEqual(self.p.state(jid2).value, "queued")                         # out of credit: not sent
        with self.assertRaises(autopilot._Stop) as stop:
            autopilot._budget_stop(self.p, pid, "image_gen")
        self.assertIn("HẾT TIỀN", str(stop.exception))

    def test_every_model_the_router_picks_in_cheap_mode_has_a_price(self):
        pricing = cost.load_pricing()
        for model, tier in (("dreamina-seedance-2-0-fast-260128", "720p"), ("kling-v3-omni", "std")):
            self.assertIsNotNone(cost.clip_price(pricing, model, tier, 5), f"{model}:{tier}")
        for model in image_models.models():
            self.assertIsNotNone(cost._number(pricing["per_image"].get(model)), model)


# ---- 5 ---------------------------------------------------------------------------------------------------------------------
class LipSyncPostTickTests(Base):
    def setUp(self):
        super().setUp()
        self.set_data({"image_prompt": "x", "characters": ["KELLY"], "size": "MS", "shot_no": 1,
                       "dialogue": [{"speaker": "KELLY", "text": "Em hiểu rồi."}]})
        self.jid, self.clip = self.finished_clip()
        self.seg = os.path.join(self.dir, "seg.wav")
        open(self.seg, "wb").close()
        self.patches = [mock.patch("core.lipsync.shot_audio", return_value={"path": self.seg, "offsets": [0.3], "lines": [1], "seconds": 4}),
                        mock.patch("core.final_cut.clip_seconds", return_value=4.0)]
        for x in self.patches:
            x.start()

    def tearDown(self):
        for x in self.patches:
            x.stop()
        super().tearDown()

    def provider(self, status=None, download=None, submit=None):
        class Sync:
            name, model = "mock-sync", "lipsync-2-pro"

            def submit(self, video, audio):
                if submit:
                    raise submit
                return "T1"

            def status(self, task):
                if isinstance(status, Exception):
                    raise status
                return status or TaskStatus("running")

            def download(self, task, dest):
                if download:
                    raise download
                with open(dest, "wb") as f:
                    f.write(b"SYNCED")
                return dest
        return Sync()

    def test_a_failed_download_keeps_the_clip_and_a_network_error_is_not_fatal(self):
        c = lipsync.post_tick(self.p, self.pid, self.dir, self.provider(), "ffmpeg")
        self.assertEqual(c["sent"], 1)
        c = lipsync.post_tick(self.p, self.pid, self.dir, self.provider(status=ProviderError("reset", code="network", transient=True)),
                              "ffmpeg")
        self.assertEqual(c["running"], 1)                                         # used to raise → autopilot ERROR
        c = lipsync.post_tick(self.p, self.pid, self.dir, self.provider(status=TaskStatus("succeeded"),
                                                                        download=ProviderError("no url", code="no_result")), "ffmpeg")
        self.assertEqual(c["failed"], 1)
        with open(self.clip, "rb") as f:
            self.assertEqual(f.read(), b"ORIGINAL-CLIP")                          # the clip was moved away BEFORE the download
        self.assertTrue(codes(self.p, "no_result"))

    def test_a_good_download_replaces_the_clip_and_keeps_the_original(self):
        lipsync.post_tick(self.p, self.pid, self.dir, self.provider(), "ffmpeg")
        lipsync.post_tick(self.p, self.pid, self.dir, self.provider(status=TaskStatus("succeeded")), "ffmpeg")
        with open(self.clip, "rb") as f:
            self.assertEqual(f.read(), b"SYNCED")
        self.assertTrue(os.path.exists(os.path.splitext(self.clip)[0] + "_prelipsync.mp4"))

    def test_the_limit_is_checked_inside_the_spend_lock_and_a_submit_error_is_caught(self):
        held = []
        real = budget.check_video

        def check(*a, **k):
            held.append(budget.SPEND_LOCK._is_owned())
            return real(*a, **k)
        prov = self.provider(submit=ProviderError("400", code="bad"))
        prov.name = "syncso-test"                 # S14.1 A1b: the money gate treats a mock* provider as free (no check at all)
        with mock.patch("core.budget.check_video", side_effect=check):
            c = lipsync.post_tick(self.p, self.pid, self.dir, prov, "ffmpeg")
        self.assertEqual(held, [True])
        self.assertEqual(c["failed"], 1)

    @mock.patch.dict(os.environ, {"FEATURE_LIP_SYNC": "1", "SYNC_API_KEY": ""})
    def test_without_a_sync_key_the_step_is_skipped_per_shot_with_a_note(self):
        self.assertNotEqual(lipsync.method_for(json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?",
                                                                              (self.sid,)).fetchone()["data"])), "post")
        with mock.patch("core.adapters.syncso.from_env_or_none", side_effect=AssertionError("no provider may be made")):
            self.assertIsNone(autopilot._lipsync_phase(self.p, self.pid, autopilot.Context(self.dir, None, None, None)))
        notes = codes(self.p, "lipsync_no_post")
        self.assertEqual(len(notes), 1)
        self.assertIn("khớp môi sau cần sync.so — không dùng", notes[0])
        self.assertFalse(self.p.conn.execute("SELECT 1 FROM usage_events").fetchone())

    @mock.patch.dict(os.environ, {"FEATURE_LIP_SYNC": "1", "SYNC_API_KEY": ""})
    def test_a_lip_sync_shot_takes_its_whole_continuity_group_to_seedance(self):
        from core import llm_runner, model_router, shots
        from tests.test_v3 import kenta_project
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        group = next(g for g in (shots.sequence_rows(p.conn, r["id"]) for r in shots.shots_of(p, pid)) if len(g) > 1)
        data = dict(group[0]["data"], size="CU", characters=["KELLY"], dialogue=[{"speaker": "KELLY", "text": "Em hiểu rồi."}])
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), group[0]["id"]))
        p.conn.commit()
        self.assertEqual({model_router.scene_choice(p.conn, r["id"])["model"] for r in group}, {"seedance"})   # one model per group

    @mock.patch.dict(os.environ, {"FEATURE_LIP_SYNC": "1", "SYNC_API_KEY": ""})
    def test_a_lip_sync_shot_sent_on_kling_is_said_not_silently_skipped(self):
        self.set_data({"image_prompt": "x", "characters": ["KELLY"], "size": "CU", "shot_no": 1, "lip_sync": True,
                       "dialogue": [{"speaker": "KELLY", "text": "Em hiểu rồi."}]})
        from core import model_router
        model_router.set_override(self.p.conn, self.sid, "kling")               # the person picked Kling for this shot
        jid = self.p.create_job(self.sid, "video_gen")
        VideoRunner(self.p, MockVideoProvider(), self.dir)._submit_kwargs(self.p.job(jid))
        self.assertTrue(codes(self.p, "lipsync_not_applied"))

    @mock.patch.dict(os.environ, {"FEATURE_LIP_SYNC": "1", "SYNC_API_KEY": ""})
    def test_the_director_is_steered_to_the_seedance_with_voice_path(self):
        from core import prompts
        self.assertIn("chỉ bằng cách tạo video KÈM GIỌNG", prompts.duration_block(self.p, self.pid))


# ---- 6 ---------------------------------------------------------------------------------------------------------------------
class ManualGateTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("gates")
        self.sid = self.p.create_scene(self.pid, 1, "s")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": "Kelly runs", "characters": ["KELLY"]}),
                                                                     self.sid))
        self.p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, 'KELLY', 'girl')", (self.pid,))
        self.p.conn.commit()

    def test_the_manual_gen_button_stops_where_the_automatic_run_stops(self):
        with self.assertRaises(batch.GateError) as e:
            batch.queue_images(self.p, self.pid)
        self.assertIn("Character Lock", str(e.exception))
        self.assertFalse(self.p.conn.execute("SELECT 1 FROM jobs").fetchone())      # nothing queued, nothing paid
        r = batch.queue_images(self.p, self.pid, confirmed=True)                    # the person decides
        self.assertEqual(r["created"], 1)
        self.assertTrue(codes(self.p, "gate_override"))
        self.assertTrue(codes(self.p, "no_reference"))

    def test_the_automatic_run_stops_when_the_bible_check_cannot_run(self):
        from core import claude_tasks, llm_runner
        self.p.conn.execute("UPDATE characters SET lock_rules=? WHERE project_id=?", (json.dumps({"must_keep": "red hair"}), self.pid))
        self.p.conn.commit()
        with mock.patch.object(claude_tasks, "bible_check", side_effect=llm_runner.LlmError("Hết ngân sách Claude API", code="budget")):
            with self.assertRaises(autopilot._Wait) as w:
                autopilot._director_phase(self.p, self.pid, autopilot.Context("", None, None, None))
        self.assertIn("Không kiểm được Character Bible", str(w.exception))


# ---- 7 ---------------------------------------------------------------------------------------------------------------------
class MissingInputTests(Base):
    def test_a_character_without_a_picture_is_said_at_generation_time(self):
        self.set_data({"image_prompt": "Kelly runs", "characters": ["KELLY"]})
        self.p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, 'KELLY', 'girl')", (self.pid,))
        self.p.conn.commit()
        jid = self.p.create_job(self.sid)
        ImageRunner(self.p, MockImageProvider(), self.dir)._submit_args(self.p.job(jid))
        self.assertTrue(any("KELLY không có ảnh tham chiếu" in m for m in codes(self.p, "missing_reference")))

    def test_a_library_picture_whose_file_is_gone_is_said(self):
        a = assets.create(self.p.conn, "FF", "character", "KELLY", "", "", None, "x")
        assets.add_image(self.p.conn, a, "k1.png", png(1))
        assets.add_image(self.p.conn, a, "k2.png", png(2))
        assets.attach(self.p.conn, self.pid, a)
        gone = assets.get(self.p.conn, a)["images"][1]["path"]
        os.remove(gone)
        self.p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, 'KELLY', 'girl')", (self.pid,))
        self.p.conn.commit()
        gaps = assets.reference_gaps(self.p.conn, self.pid, {"characters": ["KELLY"]})
        self.assertTrue(any("mất file" in g for g in gaps))

    def test_the_picture_numbering_matches_what_is_really_sent(self):
        d = tempfile.mkdtemp()
        good, big = os.path.join(d, "good.png"), os.path.join(d, "big.png")
        with open(good, "wb") as f:
            f.write(png(3))
        with open(big, "wb") as f:
            f.seek(10 * 1024 * 1024 + 10)
            f.write(b"0")
        refs = [{"path": big, "label": "KELLY", "role": "character"}, {"path": os.path.join(d, "gone.png"), "label": "KENTA", "role": "character"},
                {"path": good, "label": "MAXIM", "role": "character"}]
        kept, dropped = sendable_references(refs, "dola-seedream-5-0-pro-260628")
        self.assertEqual([r["label"] for r in kept], ["MAXIM"])
        self.assertEqual(len(dropped), 2)
        self.assertIn("Image 1 is MAXIM", assets.reference_note(kept))           # used to say "Image 3 is MAXIM" with 1 picture sent

    @mock.patch.dict(os.environ, {"FEATURE_SETCHECK_AUTOFIX": "1"})       # an old env line: S14.9 removed the flag, it does nothing
    def test_the_set_check_only_reports_even_with_an_old_autofix_line(self):
        # S14.9 (06/10): setcheck_autofix removed (GĐ6 R3/I4) — outliers are said for the storyboard, never redrawn automatically
        from core import claude_tasks
        sid2 = self.p.create_scene(self.pid, 2, "S2")
        self.set_data({"image_prompt": "y"}, sid2)
        issues = {"issues": [{"idx": 1, "problem": "lệch", "fix": "Night light."}, {"idx": 2, "problem": "lệch", "fix": ""}]}
        ctx = autopilot.Context(self.dir, mock.Mock(provider=MockImageProvider()), None, None)
        with mock.patch.object(claude_tasks, "set_consistency", return_value=issues),                 mock.patch.object(claude_tasks, "redo_from_set_check") as redo:
            autopilot._setcheck_phase(self.p, self.pid, ctx)
        redo.assert_not_called()
        self.assertTrue(codes(self.p, "set_check_report"))
        self.assertFalse(hasattr(autopilot, "_setcheck_block"))


# ---- 8 ---------------------------------------------------------------------------------------------------------------------
class EndFrameTests(Base):
    def setUp(self):
        super().setUp()
        self.p.set_project_field(self.pid, "shot_mode", "per_shot")
        self.p.set_project_field(self.pid, "look", "FF_INGAME")
        self.set_data({"image_prompt": "Kelly stands", "characters": ["KELLY"], "shot_no": 1, "size": "MS",
                       "end_state": "KELLY, 17-year-old girl, falls to her knees", "location": "Tháp đồng hồ"})

    def test_the_end_frame_prompt_has_the_start_pictures_safeguards(self):
        from core import end_frames, looks
        prompt = end_frames.prompt_for(self.p, self.pid, self.sid)
        self.assertIn(looks.image_sentence(self.p.project(self.pid)).strip(), prompt)   # the in-game look (was missing)
        self.assertNotIn("17-year-old", prompt)
        self.assertIn("falls to her knees", prompt)

    @mock.patch.dict(os.environ, {"FEATURE_END_FRAMES": "1"})
    def test_sent_pictures_are_kept_a_missing_start_picture_is_said_and_redos_are_capped(self):
        from core import end_frames
        end_frames.queue(self.p, self.pid)
        prov = MockImageProvider()
        end_frames.tick(self.p, self.pid, prov, self.dir)
        row = end_frames.current(self.p.conn, self.sid)
        self.assertEqual(json.loads(row["sent_refs"])[0]["label"], "start frame")
        # S14.16 (mục 6c.3): was "≤ 2 redos" for everyone — a person's redo is never capped; the run's own redos follow
        # pipeline.AUTO_REGEN_LIMIT (picture: 3) and a person's redo starts the count again
        from core.pipeline import AUTO_REGEN_LIMIT
        for _ in range(4):
            end_frames.redo(self.p, self.sid)                                       # the person: no limit
            end_frames.tick(self.p, self.pid, prov, self.dir)
        for _ in range(AUTO_REGEN_LIMIT["image_gen"]):
            end_frames.redo(self.p, self.sid, auto=True)
            end_frames.tick(self.p, self.pid, prov, self.dir)
        with self.assertRaises(ValueError):
            end_frames.redo(self.p, self.sid, auto=True)                            # the run: ≤ 3 automatic redos
        end_frames.redo(self.p, self.sid)                                           # the person again: allowed, count reset
        end_frames.tick(self.p, self.pid, prov, self.dir)
        end_frames.redo(self.p, self.sid, auto=True)
        os.remove(os.path.join(self.dir, str(self.pid), "images", f"job_{self.img}.png"))
        self.p.conn.execute("INSERT INTO end_frames (project_id, scene_id, start_job_id, state, created_at, updated_at)"
                            " VALUES (?,?,?,'queued',datetime('now'),datetime('now'))", (self.pid, self.sid, self.img))
        self.p.conn.commit()
        end_frames.tick(self.p, self.pid, prov, self.dir)
        self.assertTrue(any("thiếu file ảnh khung đầu" in m for m in codes(self.p, "missing_input")))


# ---- 9 ---------------------------------------------------------------------------------------------------------------------
class CloneRerunsTheDirectorTests(unittest.TestCase):
    def test_a_clone_to_run_the_director_again_really_runs_it(self):
        from core import compare, llm_runner
        from tests.test_v3 import kenta_project
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        p.conn.execute("UPDATE characters SET locked=1, lock_rules=? WHERE project_id=?", (json.dumps({"must_keep": "old"}), pid))
        p.conn.commit()
        autopilot.set_gates(p, pid, {"bible_done": True, "storyboard": False})
        new = compare.clone_project(p, pid, "chạy lại Director", None, with_rows=False)
        rows = p.conn.execute("SELECT description, locked, lock_rules FROM characters WHERE project_id=?", (new,)).fetchall()
        self.assertTrue(rows and all(r["description"] == "" and not r["locked"] and r["lock_rules"] is None for r in rows))
        self.assertFalse(autopilot.get_gates(p, new)["bible_done"])                # the old approval is not copied
        self.assertFalse(autopilot.get_gates(p, new)["storyboard"])                # the person's switch is
        self.assertIsNone(p.project(new)["director_raw"])
        with self.assertRaises((autopilot._Wait, autopilot._Stop)):
            autopilot._director_phase(p, new, autopilot.Context(tempfile.mkdtemp(), None, None, llm_runner.MockLlm()))
        self.assertTrue(p.conn.execute("SELECT 1 FROM characters WHERE project_id=? AND description!=''", (new,)).fetchone())
        self.assertTrue(all((json.loads(r["data"] or "{}").get("image_prompt") or "").strip()
                            for r in p.conn.execute("SELECT data FROM scenes WHERE project_id=?", (new,))))


# ---- 10 --------------------------------------------------------------------------------------------------------------------
class EstimateTests(Base):
    def test_claude_batch_estimates_use_the_ledger_average_when_there_is_one(self):
        self.assertGreater(cost.llm_estimate(self.p.conn, "motion", 1), 0)
        cost.record_usage(self.p.conn, None, "llm", "anthropic", "claude-sonnet-5", "input", 1_000_000, "token", stage="motion")
        cost.record_usage(self.p.conn, None, "llm", "anthropic", "claude-sonnet-5", "output", 0, "token", stage="motion")
        with mock.patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-sonnet-5"}):
            self.assertAlmostEqual(cost.llm_estimate(self.p.conn, "motion", 2), 4.0)       # 2 calls × 1M input tokens × $2/M
        self.assertIn("Claude ≈", cost.llm_tag(0.05))

    @mock.patch.dict(os.environ, {"FEATURE_END_FRAMES": "1"})
    def test_the_picture_estimate_counts_end_frames_and_the_run_estimate_has_usd(self):
        self.p.set_project_field(self.pid, "shot_mode", "per_shot")
        sid2 = self.p.create_scene(self.pid, 2, "S2")
        self.set_data({"image_prompt": "y", "shot_no": 2, "end_state": "the door is open"}, sid2)
        est = cost.estimate_images(self.p, self.pid, cost.load_pricing(), "gpt-image-2.5-sunburst")
        self.assertEqual(est["end_frames"], 1)
        self.assertEqual(est["items"], 2)                                           # the new shot's picture + its end frame
        run = cost.estimate_run(self.p, self.pid)
        self.assertGreater(run["total"], 0)
        self.assertIn("USD", cost.format_run_estimate(run))

    def test_picture_qc_calls_follow_the_qc_that_will_really_run(self):
        """#8 2026-09-27: the estimate counted one call per stage (1.37 USD) and the Claude cap ran out — re-looks after redraws,
        the margin and what is left of the cap are now in it; scene QC without Claude costs no call."""
        self.p.set_project_field(self.pid, "shot_mode", "per_shot")
        self.set_data({"image_prompt": "x", "shot_no": 1, "story_scene": 1})
        self.assertEqual(cost._picture_qc_calls(self.p.conn, self.pid, 4), 4)                    # old QC: one per picture
        with mock.patch.dict(os.environ, {"FEATURE_SCENE_QC": "1"}):
            self.assertEqual(cost._picture_qc_calls(self.p.conn, self.pid, 4), 0)                # layer 1 off: code only
            with mock.patch.dict(os.environ, {"FEATURE_SCENE_QC_CLAUDE": "1"}):
                self.assertEqual(cost._picture_qc_calls(self.p.conn, self.pid, 4), 1 + cost.REDRAW_SHARE)   # one scene + re-looks
        from core import budget
        budget.save(self.p.conn, enabled=True, llm_usd=0.01)
        run = cost.estimate_run(self.p, self.pid)
        self.assertIsNotNone(run["llm_left"])
        text = cost.format_run_estimate(run)
        self.assertIn("trần Claude còn", text)
        if run["llm"] > run["llm_left"]:
            self.assertIn("KHÔNG ĐỦ", text)


# ---- 11 --------------------------------------------------------------------------------------------------------------------
class CheapModeTests(Base):
    def test_the_smallest_valid_picture_size_per_model(self):
        self.assertEqual(image_models.cheapest_size("gpt-image-2.5-sunburst", "9:16"), "608x1088")
        self.assertEqual(image_models.cheapest_size("dola-seedream-5-0-pro-260628", "9:16"), "720x1280")
        for model in image_models.models():
            for aspect in ("9:16", "16:9", "1:1"):
                size = image_models.cheapest_size(model, aspect)
                self.assertIsNone(image_models.size_problem(model, size), f"{model} {aspect} {size}")

    def test_cheap_mode_lowers_the_picture_size_and_starts_on_during_a_test_round(self):
        self.p.set_project_field(self.pid, "aspect", "9:16")
        self.p.set_project_field(self.pid, "image_model", "gpt-image-2.5-sunburst")
        jid = self.p.create_job(self.sid)
        runner = ImageRunner(self.p, MockImageProvider(), self.dir)
        self.assertEqual(runner._submit_kwargs(self.p.job(jid))["size"], "1152x2048")
        self.p.set_project_field(self.pid, "test_quality", 1)
        # #8 (2026-09-27): a flat price a picture → a smaller picture saves nothing, the size stays
        self.assertEqual(runner._submit_kwargs(self.p.job(jid))["size"], "1152x2048")
        from unittest import mock
        from core import cost
        priced = dict(cost.load_pricing(), per_image_by_size={"gpt-image-2.5-sunburst": {"608x1088": 0.02}})
        with mock.patch.object(cost, "load_pricing", return_value=priced):
            self.assertEqual(runner._submit_kwargs(self.p.job(jid))["size"], "608x1088")
        self.assertEqual(self.p.project(self.p.create_project("normal"))["test_quality"], 0)
        budget.restart(self.p.conn, usd=10)
        self.assertEqual(self.p.project(self.p.create_project("during the trial"))["test_quality"], 1)


if __name__ == "__main__":
    unittest.main()
