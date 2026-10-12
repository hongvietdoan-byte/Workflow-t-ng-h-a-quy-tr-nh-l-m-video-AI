"""Ca thật #27 (12/10, 21 shot): bộ viết motion BẰNG CODE (seedance_refs.shot_motion / code_motion) lưu prompt hỏng rồi tự duyệt.

1. câu hành động / kết thúc còn TIẾNG VIỆT (bước dịch hết tiền Anthropic → vẫn lưu + duyệt im lặng);
2. 'LỜI DẪN speaks (mouth moving, no sound)' — giọng dẫn ngoài khung bị coi là người nói trong khung;
3. thiếu câu điểm bắt đầu (cờ prompt_formula) + lớp chuyển động nền (cờ ambient_motion) → VÀNG 21/21;
4. prompt có VÀNG / tiếng Việt vẫn state='approved' ngay.
Dữ liệu dựng giống #27 (đọc chỉ-đọc manifest: shot 3 ngoài trời đồng cỏ, weather clear, time day; shot 12 thoại LỜI DẪN)."""
import json
import os
import unittest

from core import prompt_formula as pf
from core import seedance_refs as sr
from core import speaker_lint
import tests.test_seedance_refs as base

CAST = ["KELLY", "MAXIM", "WOLFRAHH", "KAPELLA"]
SHOT3 = {"size": "MS", "angle": "eye", "camera_move": "static", "characters": CAST, "duration_s": 2.0,
         "location": "Tháp Đồng Hồ — đồng cỏ phía bắc nhìn lên tháp", "weather": "clear", "time": "day",
         "action": "Kelly chạy trên đồng cỏ (cùng chỗ shot 2) về phía cổng PHẢI trong hai cổng portal torii",
         "end_state": "Kelly a few steps closer to the portal threshold, portal glow larger in frame",
         "performance": {"face": "jaw set, eyes fixed forward on the portal", "body": "full sprint, arms driving"}}
SHOT12 = dict(SHOT3, location="Tháp Đồng Hồ — cổng portal thế giới thực tại",
              action="Kelly quay lưng về máy, bước vào cổng TRÁI",
              motion_en={"action": "Kelly turns her back to the camera and steps into the LEFT portal"},
              dialogue=[{"speaker": "LỜI DẪN", "text": "Còn nếu bạn từ chối sự cám dỗ của thế giới song song…",
                         "delivery": {"emotion": "dứt khoát"}}])
EN3 = dict(SHOT3, motion_en={"action": "Kelly runs across the meadow toward the RIGHT torii portal"})

# chụp TRƯỚC khi sửa (base: cờ prompt_formula + ambient_motion TẮT) — cờ tắt phải ra y từng byte
OFF_SHOT = {"size": "MS", "angle": "eye", "camera_move": "static", "characters": ["KELLY", "MAXIM"],
            "location": "Tháp Đồng Hồ — đồng cỏ phía bắc", "weather": "clear", "time": "day",
            "action": "Kelly chạy trên đồng cỏ", "end_state": "Kelly gần cổng",
            "motion_en": {"action": "Kelly runs across the meadow toward the right portal", "end_state": "Kelly a few steps from the portal"},
            "performance": {"face": "jaw set", "body": "full sprint", "intensity": 3},
            "dialogue": [{"speaker": "KELLY", "text": "Đi thôi"}]}
OFF_TEXT = ("Kelly runs across the meadow toward the right portal. It ends with Kelly a few steps from the portal. Acting — face: jaw set; "
            "body: full sprint. KELLY speaks (mouth moving, no sound). Medium shot, eye angle, camera static. Each foot lands under the "
            "body with no sliding, the arms swing opposite the legs, the body leans forward, and hair and loose clothes trail behind.")
OFF_VOICE = OFF_TEXT.replace("KELLY speaks (mouth moving, no sound).", "KELLY says the line of the attached voice, lips in sync.")


class _Flags(unittest.TestCase):
    def flags(self, formula: bool, ambient: bool):
        for k, v in (("FEATURE_PROMPT_FORMULA", formula), ("FEATURE_AMBIENT_MOTION", ambient)):
            old = os.environ.get(k)
            os.environ[k] = "1" if v else "0"
            self.addCleanup(lambda k=k, old=old: os.environ.__setitem__(k, old) if old is not None else os.environ.pop(k, None))


class NarratorIsNotInFrame(_Flags):
    def test_narrator_line_never_opens_a_mouth(self):
        text = sr.shot_motion(SHOT12)
        self.assertNotIn("LỜI DẪN speaks", text)
        self.assertNotIn("LỜI DẪN says", sr.shot_motion(SHOT12, voice=True))
        self.assertNotIn("speaks", text)

    def test_only_speakers_present_in_the_shot(self):
        d = dict(SHOT3, dialogue=[{"speaker": "KELLY", "text": "Đi thôi"}, {"speaker": "KENTA", "text": "Chờ đã"}])
        text = sr.shot_motion(d)
        self.assertIn("KELLY speaks (mouth moving, no sound).", text)
        self.assertNotIn("KENTA speaks", text)                       # KENTA is not in characters: an off-frame voice
        self.assertEqual(speaker_lint.speakers(d), ["KELLY"])
        self.assertEqual(speaker_lint.speakers(SHOT12), [])
        # no `characters` written (older shots): everyone but a narrator still speaks
        old = {"dialogue": [{"speaker": "KENTA", "text": "Chờ"}, {"speaker": "NARRATOR", "text": "Then…"}]}
        self.assertEqual(speaker_lint.speakers(old), ["KENTA"])
        # accents are compared as written: a character named 'VÕ' is not the 'VO' (voice-over) label
        self.assertFalse(speaker_lint.is_narrator("VÕ"))
        self.assertTrue(speaker_lint.is_narrator("V.O."))
        self.assertTrue(speaker_lint.is_narrator("Lời dẫn"))
        self.assertFalse(speaker_lint.is_narrator("LỜI"))

    def test_narrator_only_dialogue_is_not_a_missing_speaker(self):
        self.flags(True, False)
        issues = pf.lint_motion(sr.shot_motion(SHOT12), SHOT12)
        self.assertNotIn("thoai", [i["part"] for i in issues])


class StartAndAmbient(_Flags):
    def test_flags_off_byte_exact(self):
        self.flags(False, False)
        self.assertEqual(sr.shot_motion(OFF_SHOT).encode("utf-8"), OFF_TEXT.encode("utf-8"))
        self.assertEqual(sr.shot_motion(OFF_SHOT, voice=True).encode("utf-8"), OFF_VOICE.encode("utf-8"))

    def test_formula_on_says_the_start_point(self):
        self.flags(True, False)
        text = sr.shot_motion(EN3)
        self.assertTrue(text.startswith(sr.START_SENTENCE), text)
        self.assertNotIn("diem_bat_dau", [i["part"] for i in pf.lint_motion(text, EN3)])

    def test_ambient_outdoor_meadow_sunny_day(self):
        self.flags(True, True)
        text = sr.shot_motion(EN3)
        self.assertRegex(text, r"[Gg]rass[^.]*sway")
        self.assertEqual(pf.ambient_issues(text, EN3), [])
        self.assertNotRegex(text, r"(?i)rain|storm|fog|mist|snow")   # nothing against the weather written

    def test_ambient_never_guessed_indoors_or_unknown(self):
        self.flags(True, True)
        indoor = dict(EN3, location="Thế giới song song — trong nhà Tháp Đồng Hồ", weather="storm", time="night")
        self.assertEqual(pf.ambient_sentence(indoor)[0], "")
        self.assertTrue(pf.ambient_issues(sr.shot_motion(indoor), indoor))            # VÀNG stays, nothing invented
        unknown = {k: v for k, v in EN3.items() if k not in ("weather", "time")}
        self.assertEqual(pf.ambient_sentence(unknown)[0], "")
        clock = dict(EN3, location="Tháp Đồng Hồ — sân lát đá")                       # 'đồng hồ' is a clock, not a lake ('hồ')
        self.assertNotRegex(pf.ambient_sentence(clock)[0], r"(?i)water|ripple")
        storm = dict(EN3, location="Cổng Trời ngoài trời", weather="storm", time="night")
        self.assertRegex(pf.ambient_sentence(storm)[0], r"(?i)storm clouds")

    def test_group_prompt_says_the_start_once(self):
        self.flags(True, False)
        a, b = sr.shot_motion(EN3), sr.shot_motion(SHOT12)
        text = sr.prompt([(a, 2.0), (b, 2.0)], [])
        self.assertNotIn(sr.START_SENTENCE, text)                                     # the group's own start block says it


class CodeMotionHoldsWhatIsWrong(_Flags):
    def setUp(self):
        base.SeedanceRefTests.setUp(self)
        base.SeedanceRefTests._ready(self)
        self.p.conn.execute("DELETE FROM motion_prompts WHERE scene_id IN (%s)" % ",".join(map(str, self.ids)))
        self.p.conn.commit()

    def _set(self, sid, data):
        row = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()
        d = dict(json.loads(row["data"] or "{}"), **data)
        for k in [k for k, v in data.items() if v is None]:
            d.pop(k, None)
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), sid))
        self.p.conn.commit()

    def _state(self, sid):
        return self.p.conn.execute("SELECT motion_prompt, state FROM motion_prompts WHERE scene_id=?", (sid,)).fetchone()

    def test_vietnamese_left_by_a_failed_translation_is_held_and_said(self):
        self.flags(True, False)
        vi, en = self.ids[0], self.ids[1]
        self._set(vi, {"action": SHOT3["action"], "motion_en": None, "motion_en_src": None})
        self._set(en, {"action": "Kelly runs toward the portal", "end_state": "Kelly stops at the gate", "performance": None,
                       "motion_en": None, "dialogue": [], "location": "Cổng Trời ngoài trời"})

        class Down:
            def __getattr__(self, name):
                from core import llm_runner
                raise llm_runner.LlmError("credit balance is too low")
        res = sr.write_by_code(self.p, self.pid, Down())
        self.assertIn("không dịch được", res["warn"])
        self.assertEqual(self._state(vi)["state"], "pending")                     # never approved with Vietnamese in it
        self.assertIn(vi, [h["scene_id"] for h in res["held"]])
        self.assertIn("tiếng Việt", " ".join(h["why"] for h in res["held"] if h["scene_id"] == vi))
        msgs = [r["message"] for r in self.p.conn.execute("SELECT message FROM diag_events WHERE project_id=? AND stage='motion'",
                                                          (self.pid,))]
        self.assertTrue(any("tiếng Việt" in m and "chờ duyệt" in m for m in msgs), msgs)
        self.assertEqual(self._state(en)["state"], "approved", (self._state(en)["motion_prompt"], res["held"]))   # a clean English shot still goes through

    def test_no_claude_means_no_translation_and_it_is_said(self):
        self.flags(True, False)
        self._set(self.ids[0], {"action": SHOT3["action"], "motion_en": None, "motion_en_src": None})
        res = sr.write_by_code(self.p, self.pid, None)
        self.assertTrue(res["warn"] and "chưa dịch" in res["warn"], res)
        self.assertEqual(self._state(self.ids[0])["state"], "pending")

    def test_a_yellow_formula_check_is_not_approved_silently(self):
        self.flags(True, True)
        indoor = {"action": "Kelly walks to the door", "end_state": "Kelly at the door", "motion_en": None, "dialogue": [],
                  "performance": None, "location": "trong nhà Tháp Đồng Hồ", "weather": "storm", "time": "night"}
        self._set(self.ids[0], indoor)
        res = sr.write_by_code(self.p, self.pid, None)
        self.assertEqual(self._state(self.ids[0])["state"], "pending")
        self.assertIn("Chuyển động nền", " ".join(h["why"] for h in res["held"] if h["scene_id"] == self.ids[0]))

    def test_the_automatic_run_stops_instead_of_approving_vietnamese(self):
        """Rà 12/10: the automatic run approved every pending prompt; a held Vietnamese one must stop the run with a note (not stay
        'running' and pay the translation again every tick)."""
        from core import autopilot, llm_runner
        self.flags(True, False)
        self._set(self.ids[0], {"action": SHOT3["action"], "motion_en": None, "motion_en_src": None})

        class Down:
            def __getattr__(self, name):
                raise llm_runner.LlmError("credit balance is too low")
        ctx = autopilot.Context(data_dir=self.data, image_runner=None, video_runner=None, llm=Down())
        with self.assertRaises(autopilot._Stop) as stop:
            autopilot._motion_phase(self.p, self.pid, ctx)
        self.assertIn("tiếng Việt", str(stop.exception))
        self.assertEqual(self._state(self.ids[0])["state"], "pending")

    def test_translation_cost_is_estimated_for_the_button(self):
        self._set(self.ids[0], {"action": SHOT3["action"], "motion_en": None, "motion_en_src": None})
        self.assertGreater(sr.translate_estimate(self.p.conn, self.pid), 0)
        for sid in self.ids:
            self._set(sid, {"action": "Kelly runs", "end_state": "Kelly stops", "motion_en": None, "performance": None})
        self.p.conn.execute("UPDATE scenes SET data=json_set(data, '$.action', 'x', '$.end_state', 'y') WHERE project_id=?", (self.pid,))
        self.p.conn.commit()
        self.assertEqual(sr.translate_estimate(self.p.conn, self.pid), 0)


class VideoReviewFixes1210(_Flags):
    """Rà khâu video #27 (12/10, D:/AI-Video-Output/2026-10-12_du-an-27/ra_video_21_shot.md, lỗi code #1, #3, #7)."""

    def test_game_name_free_fire_is_not_a_flame(self):          # lỗi #1: S13–S21 "The flames flicker softly" giữa trời quang
        d = {"weather": "clear", "location": "Tháp Đồng Hồ", "image_prompt": "Free Fire in-game 3D render, Kelly on a stone plaza"}
        self.assertEqual(pf.ambient_sentence(d)[0], "")
        self.assertEqual(pf.ambient_sentence(dict(d, action="Kelly fires continuously"))[0], "")   # bắn súng không phải lửa
        self.assertEqual(pf.ambient_sentence(dict(d, action="a campfire burns beside Kelly"))[0], "The flames flicker softly.")
        self.assertEqual(pf.ambient_sentence(dict(d, action="the car is on fire"))[0], "The flames flicker softly.")
        self.assertEqual(pf.ambient_sentence(dict(d, image_prompt="Kelly holds a torch"))[0], "The flames flicker softly.")

    def test_pov_free_fire_hands_are_empty(self):               # lỗi #3: S1/S2 "hands tense around the rifle grip" ở góc POV
        s1 = {"size": "MS", "angle": "pov", "camera_move": "handheld", "action": "Kelly looks through the gap in the door",
              "performance": {"body": "hands tense around the rifle grip, barrel trembling"}}
        parts = [i for i in pf.lint_motion(sr.shot_motion(s1), s1) if i["part"] == "pov_tay_khong"]
        self.assertEqual([i["level"] for i in parts], ["red"])
        vi = dict(s1, performance={"body": "tay siết chặt báng súng"})
        self.assertTrue([i for i in pf.lint_motion("Static camera.", vi) if i["part"] == "pov_tay_khong"])
        ok = dict(s1, performance={"body": "both hands open, fingers flex slightly"})
        self.assertFalse([i for i in pf.lint_motion(sr.shot_motion(ok), ok) if i["part"] == "pov_tay_khong"])
        eye = dict(s1, angle="eye")                               # không phải POV: cầm súng là đúng
        self.assertFalse([i for i in pf.lint_motion(sr.shot_motion(eye), eye) if i["part"] == "pov_tay_khong"])
        self.assertFalse([i for i in pf.lint_motion(sr.shot_motion(s1), s1, ff=False) if i["part"] == "pov_tay_khong"])
        text = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge", "roles",
                                 "director_p24_1110.md"), encoding="utf-8").read()            # the Director's POV rule 13
        self.assertIn("Cả `performance` / `action` của shot POV cũng tay trống", text)

    def test_pov_gun_on_the_ground_is_not_held(self):            # rà 12/10: ĐỎ only for a gun in the hands
        s = {"size": "MS", "angle": "pov", "camera_move": "static", "action": "looks at the gun on the ground",
             "image_prompt": "a rifle lying in the grass, oil barrels behind",
             "performance": {"body": "both hands open", "timing": "triggers a trap after a beat"}}
        self.assertFalse([i for i in pf.lint_motion(sr.shot_motion(s), s) if i["part"] == "pov_tay_khong"])
        held = dict(s, performance={"body": "hand tightens on the gun grip"})
        self.assertTrue([i for i in pf.lint_motion(sr.shot_motion(held), held) if i["part"] == "pov_tay_khong"])
        held2 = dict(s, performance={"body": "holds the SKORP ready"})
        self.assertTrue([i for i in pf.lint_motion(sr.shot_motion(held2), held2) if i["part"] == "pov_tay_khong"])

    def test_pov_english_version_wins_over_the_director_field(self):   # 12/10 #27 S1/S2: motion_en sửa tay trống → hết ĐỎ giả
        s = {"size": "MS", "angle": "pov", "camera_move": "static", "action": "nhìn ba đồng đội gục",
             "performance": {"body": "tay siết chặt báng súng"},
             "motion_en": {"action": "looks at three fallen teammates",
                           "performance": {"body": "both empty hands open, fingers flex slightly"}}}
        self.assertFalse([i for i in pf.lint_motion(sr.shot_motion(s), s) if i["part"] == "pov_tay_khong"])
        gun_en = dict(s, motion_en={"action": "looks on", "performance": {"body": "hand tightens on the gun grip"}})
        self.assertTrue([i for i in pf.lint_motion(sr.shot_motion(gun_en), gun_en) if i["part"] == "pov_tay_khong"])
        no_en = dict(s, motion_en={"action": "looks at three fallen teammates"})   # chưa dịch performance: trường gốc vẫn bị kiểm
        self.assertTrue([i for i in pf.lint_motion(sr.shot_motion(no_en), no_en) if i["part"] == "pov_tay_khong"])

    def test_clear_sky_written_in_the_shot_gives_drifting_clouds(self):   # rà 12/10: "video không đơ" — mây trôi
        d = {"weather": "clear", "location": "Tháp Đồng Hồ", "image_prompt": "Free Fire in-game 3D render, stone plaza under a blue sky"}
        self.assertEqual(pf.ambient_sentence(d)[0], "Clouds drift slowly across the sky in the background.")
        self.assertEqual(pf.ambient_sentence(dict(d, weather="calm, no wind"))[0],
                         "Clouds drift slowly across the sky in the background.")
        inside = {"weather": "clear", "location": "phòng trong nhà", "image_prompt": "a room, window shows the sky"}
        self.assertNotIn("Clouds", pf.ambient_sentence(inside)[0])          # indoors: a flame only

    def test_eyes_guard_writes_names_without_accents(self):     # lỗi #7: "KELLY, XÚC TU ĐỎ: natural human eyes" lưu có dấu
        self.assertEqual(sr.eyes_guard({"characters": ["XÚC TU ĐỎ"]}, {"XÚC TU ĐỎ": True}),
                         " XUC TU DO: natural human eyes, no glowing eyes.")
        self.assertEqual(sr.eyes_guard({"characters": ["KELLY"]}), " KELLY: natural human eyes, no glowing eyes.")


class IdentityPictureFollowsClipaiRules(unittest.TestCase):    # lỗi #4: KAPELLA 21/2.png 220×394 bị adapter từ chối lúc gửi
    def setUp(self):
        import tempfile
        from PIL import Image
        from core import assets
        from core.db import connect
        from core.pipeline import Pipeline
        self.tmp = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("ids27")
        self.aid = assets.create(self.p.conn, "FF", "character", "KAPELLA")
        self.img = {}
        for name, size in (("2.png", (220, 394)), ("3.png", (550, 800)), ("1.png", (1116, 2929))):
            path = os.path.join(self.tmp, name)
            Image.new("RGB", size, (90, 90, 90)).save(path)
            self.img[name] = path

    def _pic(self, name, sort):
        cur = self.p.conn.execute("INSERT INTO asset_images (asset_id, path, label, sort, status) VALUES (?,?,?,?,?)",
                                  (self.aid, self.img[name], name, sort, "approved"))
        return cur.lastrowid

    def _link(self, image_id):
        self.p.conn.execute("INSERT INTO characters (project_id, name, description, ref_asset_id, ref_image_id) VALUES (?,?,?,?,?)",
                            (self.pid, "KAPELLA", "x", self.aid, image_id))
        self.p.conn.commit()

    def _said(self):
        return [r["message"] for r in self.p.conn.execute("SELECT message FROM diag_events WHERE code='identity_picture_rule'")]

    def test_first_picture_passing_the_rules_is_sent(self):
        small = self._pic("2.png", 1)
        self._pic("3.png", 2)
        self._link(small)                                           # ảnh đã chọn 2.png (cạnh 220 < 300)
        ids = sr.identity_pictures(self.p.conn, self.pid, [{"data": {"characters": ["KAPELLA"]}}], 8)
        self.assertEqual(ids, [("KAPELLA", self.img["3.png"])])
        self.assertTrue(self._said() and "KAPELLA" in self._said()[0], self._said())   # đổi ảnh thì nói ra, không im lặng

    def test_no_picture_passing_keeps_the_old_one_and_says_it(self):
        tall = self._pic("1.png", 1)                                # tỉ lệ 0,38 < 0,4 (Lính địch áo choàng 425/1.png)
        self._link(tall)
        ids = sr.identity_pictures(self.p.conn, self.pid, [{"data": {"characters": ["KAPELLA"]}}], 8)
        self.assertEqual(ids, [("KAPELLA", self.img["1.png"])])
        self.assertTrue(self._said() and "0.38" in self._said()[0], self._said())

    def test_a_good_picture_is_kept_silently(self):
        good = self._pic("3.png", 1)
        self._pic("2.png", 2)
        self._link(good)
        ids = sr.identity_pictures(self.p.conn, self.pid, [{"data": {"characters": ["KAPELLA"]}}], 8)
        self.assertEqual(ids, [("KAPELLA", self.img["3.png"])])
        self.assertEqual(self._said(), [])


if __name__ == "__main__":
    unittest.main()
