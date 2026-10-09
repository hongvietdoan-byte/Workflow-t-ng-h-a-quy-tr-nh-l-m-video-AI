"""F5-A (09/10): ô "sẵn sàng gen" từng shot (core.readiness) + kích thước thật của vật Kho (gốc lỗi tỉ lệ giếng #24).

#24: bản đồ 3D Tháp Đồng Hồ KHÔNG có giếng — giếng là vật Kho, model ảnh tự vẽ → thành giếng cao thấp khác nhau giữa các shot.
Không gọi dịch vụ nào: Blender giả (tests.test_plate_stale_kld6), ảnh/video không gửi."""
import json
import os
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from core import assets, location_pack, place_refs, prompt_formula, readiness, seedance_refs
from core.runner import build_image_prompt
from tests.test_plate_stale_kld6 import Base, OLD_FIELDS
from tests.test_ui_video import VideoSeed, V2, APP

FLAGS = {"FEATURE_PROMPT_FORMULA": "1", "FEATURE_PLACE_RENDER_REFS": "1"}
GOOD = ("Free Fire in-game 3D render, stylized proportions. Medium shot, Kelly stands beside the old stone well, looking down into "
        "it, cold moonlight from above.")
# #24 shot 3 kiểu: bóng lao sát mặt, không đường đi, không câu không chạm → đỏ
RUSH = ("Free Fire in-game 3D render, stylized proportions. Medium shot, Kelly stands beside the old stone well, a black shadow "
        "streaks right in front of her face, cold moonlight from above.")


def _by(res, label):
    return next((i for i in res["items"] if i["label"].startswith(label)), None)


class ImageReadyTests(Base):
    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, FLAGS)
        env.start()
        self.addCleanup(env.stop)
        self.set_data(dict(OLD_FIELDS, plate_spot="plaza_front", size="MS", image_prompt=GOOD))

    def ready(self, kind="image"):
        return readiness.shot_ready(self.p.conn, self.data, self.pid, self.sid, kind)

    def test_shot24_rush_near_face_is_red_formula_and_says_where(self):
        self.render()
        self.set_data(dict(self.data_of(), image_prompt=RUSH))
        res = self.ready()
        self.assertFalse(res["ok"])
        item = _by(res, "Công thức prompt")
        self.assertEqual(item["state"], "red")
        self.assertIn("Bước 1/2", item["fix_where"])
        self.assertIn("lao sát", item["why"])
        # cùng luật với chỗ chặn gửi (ImageRunner._blocked → red_issues)
        reds = prompt_formula.red_issues(self.p.conn, self.sid, "image")
        self.assertTrue(reds and all(r.split(" · ", 1)[1] in item["why"] for r in reds))
        self.assertTrue(readiness.summary(res).startswith("⛔ 1 việc cần sửa"))
        self.assertIn("Bước 1/2", readiness.blocked_reason(res))

    def test_broken_plate_is_red(self):
        with mock.patch.object(location_pack.plate_env, "plate_problem", return_value="nền 3D gần như MỘT MÀU"):
            self.render()
        res = self.ready()
        self.assertFalse(res["ok"])
        item = _by(res, "Nền 3D")
        self.assertEqual(item["state"], "red")
        self.assertIn("Render lại nền 3D", item["fix_where"])
        self.assertIn("MỘT MÀU", item["why"])

    def test_everything_in_place_is_ok(self):
        self.render()
        res = self.ready()
        self.assertTrue(res["ok"], res)
        self.assertEqual(_by(res, "Nền 3D")["state"], "ok")
        self.assertEqual(_by(res, "Công thức prompt")["state"], "ok")
        self.assertTrue(readiness.summary(res).startswith("✅ Sẵn sàng"))
        self.assertEqual(readiness.blocked_reason(res), "")
        self.assertIn("USD", _by(res, "Model")["why"])

    def test_not_rendered_yet_is_only_a_warning(self):
        res = self.ready()
        self.assertTrue(res["ok"])
        self.assertEqual(_by(res, "Nền 3D")["state"], "warn")
        self.assertIn("0 USD", _by(res, "Nền 3D")["why"])

    def test_flags_off_still_runs(self):
        with mock.patch.dict(os.environ, {"FEATURE_PROMPT_FORMULA": "0", "FEATURE_PLACE_RENDER_REFS": "0"}):
            self.set_data(dict(self.data_of(), image_prompt=RUSH))
            res = self.ready()
        self.assertTrue(res["ok"])
        self.assertIsNone(_by(res, "Nền 3D"))
        self.assertIn("tắt", _by(res, "Công thức prompt")["why"])

    def test_video_without_approved_first_frame_is_red(self):
        self.p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, duration_sec, state) VALUES (?, ?, 5, 'approved')",
                            (self.sid, "Clip starts on the first frame: Kelly looks down into the well, then steps back. Static camera. "
                                       "Ends holding still."))
        self.p.conn.commit()
        res = self.ready("video")
        self.assertFalse(res["ok"])
        item = _by(res, "Ảnh khung đầu")
        self.assertEqual(item["state"], "red")
        self.assertIn("Bước 2", item["fix_where"])
        jid = self.p.create_job(self.sid, "image_gen")
        self.p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (jid,))
        self.p.conn.commit()
        self.assertEqual(_by(self.ready("video"), "Ảnh khung đầu")["state"], "ok")


class KhoObjectSizeTests(Base):
    """Vật Kho 'Giếng đá' (alias stone well) ở 2 shot: có 0.9 m → câu tỉ lệ trong prompt cả 2 shot; không số → không câu, warn."""

    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, FLAGS)
        env.start()
        self.addCleanup(env.stop)
        self.well = assets.create(self.p.conn, "FF", "prop", "Giếng đá", aliases="stone well")
        assets.attach(self.p.conn, self.pid, self.well)
        self.sid2 = self.p.create_scene(self.pid, 2, "s2")
        for sid in (self.sid, self.sid2):
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                                (json.dumps({"size": "MS", "characters": ["KELLY"], "image_prompt": GOOD}), sid))
        self.p.conn.commit()

    def sdata(self, sid):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"])

    def test_measured_well_goes_into_both_image_prompts_and_the_seedance_motion(self):
        assets.set_size(self.p.conn, self.well, 0.9)
        self.assertEqual(assets.get(self.p.conn, self.well)["size"], {"height_m": 0.9})
        for sid in (self.sid, self.sid2):
            prompt, _ = build_image_prompt(self.p.conn, self.pid, self.sdata(sid))
            self.assertIn("stone well is 0.9 m high", prompt)
            self.assertIn("waist height of a 1.7 m adult", prompt)
        short = place_refs.object_scale_sentence(self.p.conn, self.pid, self.sdata(self.sid), short=True)
        motion = seedance_refs.prompt([("Kelly looks into the well.", 4)], [], scales=[short])
        self.assertIn("0.9 m high", motion)
        res = readiness.shot_ready(self.p.conn, self.data, self.pid, self.sid, "image")
        self.assertEqual(_by(res, "Kích thước vật mốc")["state"], "ok")

    def test_unmeasured_well_says_nothing_in_the_prompt_and_warns(self):
        prompt, _ = build_image_prompt(self.p.conn, self.pid, self.sdata(self.sid))
        self.assertNotIn("Real sizes", prompt)
        self.assertNotIn(" m high", prompt)
        res = readiness.shot_ready(self.p.conn, self.data, self.pid, self.sid, "image")
        item = _by(res, "Kích thước vật mốc")
        self.assertEqual(item["state"], "warn")
        self.assertIn("vật mốc Giếng đá chưa có kích thước thật", item["why"])
        self.assertIn("Kho", item["fix_where"])
        self.assertTrue(res["ok"])                                            # a warning, never a stop

    def test_one_shot_only_is_not_warned_and_bad_numbers_are_refused(self):
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"size": "MS", "image_prompt": "a quiet street"}),
                                                                   self.sid2))
        self.p.conn.commit()
        res = readiness.shot_ready(self.p.conn, self.data, self.pid, self.sid, "image")
        self.assertIsNone(_by(res, "Kích thước vật mốc"))
        with self.assertRaises(assets.AssetError):
            assets.set_size(self.p.conn, self.well, 90 * 100)                 # cm typed as m

    def test_ten_shot_project_is_not_n_plus_1(self):
        for i in range(3, 11):
            sid = self.p.create_scene(self.pid, i, f"s{i}")
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"size": "MS", "image_prompt": GOOD}), sid))
            self.p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, duration_sec, state) VALUES (?, 'x', 5, 'approved')",
                                (sid,))
        self.p.conn.commit()
        from core import memo
        counts = {}
        for kind in ("image", "video"):
            seen = []
            self.p.conn.set_trace_callback(seen.append)
            with memo.per_rerun():
                res = readiness.project_ready(self.p.conn, self.data, self.pid, kind, lines={} if kind == "video" else None)
            self.p.conn.set_trace_callback(None)
            self.assertEqual(len(res), 10)
            counts[kind] = len(seen)
        self.assertLess(counts["image"], 80, counts)
        self.assertLess(counts["video"], 200, counts)


class CardLineUiTests(VideoSeed):
    def test_video_and_storyboard_cards_have_the_ready_line(self):
        at = self.open_video()
        caps = "\n".join(c.value for c in at.caption)
        self.assertIn("việc cần sửa", caps)                                   # no approved first frame → red line
        self.assertIn("Gen sẽ bị giữ/chặn", caps)
        self.assertIn("Chi tiết sẵn sàng gen", [e.label for e in at.expander])
        self.assertIn(f"va_{self.jobs['succeeded']}", {b.key for b in at.button})   # old widget keys kept
        with mock.patch.dict(os.environ, dict(V2)):
            at = AppTest.from_file(APP, default_timeout=40).run()
            at.radio(key="step").set_value(at.radio(key="step").options[2]).run()
        self.assertFalse(at.exception, at.exception)
        caps = "\n".join(c.value for c in at.caption)
        self.assertTrue("Sẵn sàng" in caps or "việc cần sửa" in caps, caps[:500])


if __name__ == "__main__":
    unittest.main()


def _kho_setup(self):
    Base.setUp(self)
    env = mock.patch.dict(os.environ, FLAGS)
    env.start()
    self.addCleanup(env.stop)
    self.well = assets.create(self.p.conn, "FF", "prop", "Giếng đá", aliases="stone well")
    assets.attach(self.p.conn, self.pid, self.well)
    self.sid2 = self.p.create_scene(self.pid, 2, "s2")
    for sid in (self.sid, self.sid2):
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                            (json.dumps({"size": "MS", "characters": ["KELLY"], "image_prompt": GOOD}), sid))
    self.p.conn.commit()


class ReviewFixesF5(Base):
    """Rà độc lập F5 (09/10): readiness khớp chỗ chặn thật (bố cục nơi chốn, cả nhóm gửi chung); set_profile giữ kích thước vật Kho;
    câu kích thước bỏ trước khi prompt Seedance vượt giới hạn; chữ '[mũ]' (KLD-32) không vào prompt video."""

    setUp = _kho_setup

    def test_missing_layout_is_red_like_the_image_runner(self):
        with mock.patch.object(assets, "missing_layout", return_value="Tháp Đồng Hồ có bố cục trong Kho nhưng dự án chưa gắn"):
            res = readiness.shot_ready(self.p.conn, self.data, self.pid, self.sid, "image")
        self.assertFalse(res["ok"])
        self.assertEqual(_by(res, "Bố cục nơi chốn")["state"], "red")

    def test_clean_shot_grouped_with_a_red_shot_is_red(self):
        from core import shots
        for sid in (self.sid, self.sid2):
            self.p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, duration_sec, state) VALUES (?, ?, 5, 'approved')",
                                (sid, "Kelly looks down into the well. Static camera. Ends holding still."))
        self.p.conn.commit()
        group = [{"id": self.sid, "idx": 1}, {"id": self.sid2, "idx": 2}]
        real = prompt_formula.red_issues
        fake = lambda conn, sid, kind=None, gore_hinted=None: (["Prompt motion · Luật FF: máu"] if sid == self.sid2 else [])
        with mock.patch.object(shots, "group_of", return_value=group), mock.patch.object(prompt_formula, "red_issues", side_effect=fake):
            res = readiness.shot_ready(self.p.conn, self.data, self.pid, self.sid, "video")
        self.assertIs(prompt_formula.red_issues, real)
        item = _by(res, "Nhóm gửi chung")
        self.assertEqual(item["state"], "red")
        self.assertIn(f"shot #{self.sid2}", item["why"])
        self.assertFalse(res["ok"])

    def test_set_profile_keeps_the_real_size_of_an_object(self):
        assets.set_size(self.p.conn, self.well, 0.1, 0.5)
        assets.set_profile(self.p.conn, self.well, {"identity": "old stone well"}, approved=True)
        self.assertEqual(assets.get(self.p.conn, self.well)["size"], {"height_m": 0.1, "width_m": 0.5})
        assets.set_profile(self.p.conn, self.well, {"identity": "old stone well", "height_m": 0.9}, approved=True)
        self.assertEqual(assets.get(self.p.conn, self.well)["size"], {"height_m": 0.9, "width_m": 0.5})

    def test_sizes_go_first_when_the_seedance_prompt_would_pass_its_limit(self):
        scale = "Real sizes: the stone well is 0.9 m high — about waist height of a 1.7 m adult."
        parts = [("Kelly looks into the well.", 4)]
        self.assertIn("0.9 m high", seedance_refs.prompt(parts, [], scales=[scale]))
        limit = seedance_refs.prompt_limit(None)
        base = len(seedance_refs.prompt(parts, [], scales=None))
        text = seedance_refs.prompt(parts, [], scales=[scale], reserve=limit - base - 5)
        self.assertNotIn("0.9 m high", text)
        self.assertEqual(len(text), base)

    def test_kept_vietnamese_word_never_reaches_the_video_prompt(self):
        from core import claude_tasks
        data = {"action": "Kelly đội mũ", "motion_en": {"action": "Kelly puts on a hat [mũ]"}}
        action = seedance_refs._en(data, "action")
        self.assertEqual(action, "Kelly puts on a hat")
        text = seedance_refs.prompt([(action, 4)], [])
        self.assertNotIn("[", text)
        self.assertFalse(any("chưa dịch" in x for x in seedance_refs.lint_group(text, 1, 1, 1, [4], False)))
        self.assertFalse(claude_tasks._vi(claude_tasks._unbracketed({"1": "a hat [mũ]"})))
        self.assertTrue(claude_tasks._vi(claude_tasks._unbracketed({"1": "a hat [đội mũ đi ra ngoài]"})))   # a sentence: not English
