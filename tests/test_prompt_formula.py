"""F1-A (09/10, công thức prompt F0 người dùng đã duyệt): code kiểm PHẦN của prompt ảnh khung đầu / motion, không kiểm câu chữ.
Fixture là câu THẬT của #24 Teasing (bản cao 08/10) và #22 Khủng Long Đỏ (docs/CONG_THUC_PROMPT_F0_NHAP_2026-10-09.md mục 4,
docs/RA_SOAT_TRUOC_GEN_LAI_24_2026-10-08.md mục 1)."""
import copy
import json
import unittest
from unittest import mock

from core import prompt_formula as F

# ---- câu thật -------------------------------------------------------------------------------------------------------------------
P24_SHOT2_IMAGE = (
    "Medium shot, slightly high side view, Free Fire in-game 3D render style, Kelly in profile on the left facing right, leaning over "
    "the rim of an ancient octagonal stone well on the right, both hands on the stones, looking down into the dark well, black hair "
    "strands and blood stains on the rim, row of red-roof plaza houses behind, the clock tower only partly visible at the right edge, "
    "foggy plaza at night, cold moonlight, stylized proportions, moderate texture detail, clear gameplay lighting, everything in focus")
P24_SHOT3_IMAGE = (
    "Over-the-shoulder shot from behind Kelly, dutch angle, Free Fire in-game 3D render style, Kelly in the foreground leaning over the "
    "rim of an ancient stone well, a dark blurred shadow figure with long trailing black hair streaking fast across the well mouth right "
    "in front of her face, motion blur, foggy plaza at night, cold moonlight, stylized proportions, moderate texture detail, clear "
    "gameplay lighting")
P24_SHOT4_FRAMING = "Medium close-up — from mid-chest up, no legs, low angle looking up."
P24_SHOT4_ACTING = "body: sprawled on the ground, hands braced behind"
P24_SHOT5_MOTION = (
    "...the demoness in form 1 grips the rim of the well with her hands and crawls over the edge. ... Acting — face: faceless, no "
    "expression; eyes: glowing red, fixed forward; ... Natural human eyes, no glowing eyes.")
P22_SHOT6_IMAGE = (
    "Free Fire in-game 3D render, stylized proportions, medium close-up from mid-chest up, no legs, inside the 2nd-floor bedroom of the "
    "big east house exactly as the 3D render, same camera and same spot as the previous shot: KELLY KL leaning on the side of the same "
    "open doorway, wearing the female Red Dinosaur outfit (black cap, black shark-tooth mask worn UP over her mouth and nose (never "
    "pulled down), red croptop with a GREEN dinosaur print, red jacket with black striped sleeves), hands on hips, confident pose, eyes "
    "smiling above the mask, warm daylight, everything in focus, not blurred background KELLY KL keeps Kelly's OWN hair from her "
    "reference picture: a dark brown / black bob with blunt bangs, one solid colour — no silver, white or two-tone strands (the hair of "
    "the outfit picture is not hers).")
# mẫu sạch: ghép từ các câu #22 trong sổ công thức (F0 mục 3.1 / 3.2)
P22_CLEAN_IMAGE = (
    "Free Fire in-game 3D render, stylized proportions, moderate texture detail, clear gameplay lighting, wide shot, full bodies with "
    "feet visible, vertical frame, inside the stair landing exactly as the 3D render, the clock tower left of centre, the PLACE render "
    "picture decides the whole background, MAXIM frame-left mid-step, looking toward the bed off-screen right, wearing a red hoodie with "
    "the GREEN fire-breathing dinosaur print, black sleeves, bright warm midday sunlight from upper-front, everything in focus, not a "
    "movie still, not blurred background.")
P22_CLEAN_MOTION = (
    "The clip starts exactly on the pose and framing of the first image. KELLY KL spins once on the spot, flicks the brim of her cap, "
    "then lands a playful pose and holds it, weight shifting heel-to-toe with no foot sliding. Static camera, nothing else moves.")
P24_SHOT2_MOTION = ("medium shot, high angle, camera push in: framing side view... It ends with Kelly frozen mid-lean, eyes fixed down "
                    "into the well.")


def parts(issues, level=None):
    return [i["part"] for i in issues if level is None or i["level"] == level]


class ImageChecks(unittest.TestCase):
    def test_gore_without_restraint_is_red(self):                                   # (c) #24 shot 2
        found = F.check_image(P24_SHOT2_IMAGE, {"size": "MS", "characters": ["KELLY"]})
        self.assertIn("luat_ff", parts(found, "red"), found)
        self.assertTrue(any("blood" in i["msg"] for i in found if i["part"] == "luat_ff"))

    def test_gore_with_restraint_is_not_red(self):
        text = P24_SHOT2_IMAGE.replace("everything in focus", "the blood stains only hinted, in deep shadow")
        self.assertNotIn("luat_ff", parts(F.check_image(text, {"size": "MS", "characters": ["KELLY"]}), "red"))

    def test_colour_word_is_not_blood(self):                                        # "màu" ≠ "máu" (không bỏ dấu khi so)
        found = F.check_image("Free Fire in-game 3D render, medium shot, Kelly đứng, áo màu đỏ, mau chóng quay lại", {"characters": ["K"]})
        self.assertNotIn("luat_ff", parts(found))
        self.assertIn("luat_ff", parts(F.check_image("Free Fire in-game 3D render, medium shot, Kelly đứng, vệt máu trên tường", {}), "red"))

    def test_shadow_streaking_past_her_face_without_path_is_red(self):               # (d) #24 shot 3
        found = F.check_image(P24_SHOT3_IMAGE, {"size": "MS", "angle": "ots", "characters": ["KELLY"]})
        self.assertIn("duong_di_vat_gan_nguoi", parts(found, "red"), found)
        fixed = P24_SHOT3_IMAGE.replace("right in front of her face", "from the left edge of the well to the right edge, about one metre "
                                        "in front of her face, it never touches or passes through her")
        self.assertNotIn("duong_di_vat_gan_nguoi", parts(F.check_image(fixed, {"size": "MS", "characters": ["KELLY"]})))

    def test_close_framing_with_a_sprawled_body_is_red(self):                       # (b) #24 shot 4
        found = F.check_image(P24_SHOT4_FRAMING + " " + P24_SHOT4_ACTING, {"characters": ["KELLY"]})
        self.assertIn("khung_hinh", parts(found, "red"), found)
        # the same conflict when the pose sits in the Director's acting / size fields, not in the prompt
        found = F.check_image("Free Fire in-game 3D render, " + P24_SHOT4_FRAMING,
                              {"size": "MCU", "characters": ["KELLY"], "performance": {"body": "sprawled on the ground, hands braced behind"}})
        self.assertIn("khung_hinh", parts(found, "red"), found)
        self.assertNotIn("khung_hinh", parts(F.check_image(P22_CLEAN_IMAGE, {"size": "WS", "characters": ["MAXIM"]}), "red"))

    def test_run_on_sentence_is_only_a_warning(self):                               # (g) #22 shot 6
        found = F.check_image(P22_SHOT6_IMAGE, {"size": "MCU", "characters": ["KELLY KL"]})
        self.assertEqual(parts(found, "red"), [], found)
        self.assertIn("cau_chu", parts(found, "warn"), found)
        self.assertTrue(any("KELLY KL keeps" in i["msg"] for i in found))

    def test_missing_required_parts_warn(self):                                     # (a)
        found = F.check_image("Kelly by the well at night", {"characters": ["KELLY"]})
        self.assertIn("phong_cach", parts(found, "warn"))
        self.assertIn("khung_hinh", parts(found, "warn"))
        self.assertIn("khoanh_khac", parts(found, "warn"))

    def test_parts_the_code_adds_are_not_asked_of_the_director(self):           # runner.build_image_prompt adds framing + look
        found = F.check_image("Kelly leaning over the rim of the well, cold moonlight", {"size": "MS", "characters": ["KELLY"]},
                              style_by_code=True)
        self.assertEqual(found, [])

    def test_clean_prompt_has_no_false_alarm(self):
        self.assertEqual(F.check_image(P22_CLEAN_IMAGE, {"size": "WS", "characters": ["MAXIM"]}), [])
        self.assertEqual(F.check_motion(P22_CLEAN_MOTION, {"size": "WS", "characters": ["KELLY KL"], "end_state": "holds the pose"}), [])


class MotionChecks(unittest.TestCase):
    def test_human_eye_rule_on_the_demoness_is_red(self):                           # (e) + (f) #24 shot 5
        found = F.check_motion(P24_SHOT5_MOTION, {"characters": ["YÊU NỮ"]})
        self.assertIn("loai_nhan_vat", parts(found, "red"), found)
        self.assertIn("mau_thuan", parts(found, "red"), found)

    def test_human_eye_rule_on_a_creature_from_the_bible(self):                    # (e) from the character, not the prompt
        found = F.check_motion("The clip starts exactly on the first image. She turns her head slowly. Static camera. Natural human eyes, "
                               "no glowing eyes.", {"characters": ["YÊU NỮ"]},
                               [{"name": "YÊU NỮ", "description": "yêu nữ tóc dài che mặt, mắt đỏ phát sáng"}])
        self.assertIn("loai_nhan_vat", parts(found, "red"), found)
        self.assertNotIn("loai_nhan_vat", parts(F.check_motion("Kelly turns. Static camera. Natural human eyes, no glowing eyes.",
                                                               {"characters": ["KELLY"]}, [{"name": "KELLY", "description": "nữ, tóc đen"}])))

    def test_static_camera_and_push_in_in_one_prompt(self):                         # (f)
        found = F.check_motion("The clip starts on the first image. Kelly leans over the well. Static camera. The camera slowly pushes in.",
                               {"characters": ["KELLY"]})
        self.assertIn("mau_thuan", parts(found, "red"))

    def test_hidden_landmark_also_visible(self):                                    # (f)
        found = F.check_image("Free Fire in-game 3D render, medium shot, Kelly standing, no clock tower in frame, the clock tower visible "
                              "at the right edge", {"characters": ["KELLY"]})
        self.assertIn("mau_thuan", parts(found, "red"), found)

    def test_missing_motion_parts_warn(self):                                       # (a)
        found = F.check_motion("foggy plaza at night", {"characters": ["KELLY"], "dialogue": [{"speaker": "KELLY", "text": "Ai đó?"}]})
        for part in ("diem_bat_dau", "hanh_dong", "may_quay", "thoai"):
            self.assertIn(part, parts(found, "warn"), found)


class ShotKind(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(F.shot_kind({"characters": ["K"], "dialogue": [{"speaker": "K", "text": "a"}]}), "dialogue")
        self.assertEqual(F.shot_kind({"characters": [], "size": "WS"}), "establishing")
        self.assertEqual(F.shot_kind({"characters": [], "size": "ECU"}), "object")
        self.assertEqual(F.shot_kind({"characters": ["K"], "ref_video_path": "x.mp4", "action": "nhảy theo nhạc"}), "dance_ref")
        self.assertEqual(F.shot_kind({"characters": ["YÊU NỮ"], "action": "bò lên miệng giếng"},
                                     [{"name": "YÊU NỮ", "description": "yêu nữ, quái"}]), "creature")
        self.assertEqual(F.shot_kind({"characters": ["K"], "action": "Kelly ngã ra sau"}), "action")


class CrossShot(unittest.TestCase):
    def test_same_cap_in_two_colours(self):                                         # #22 shot 2 ↔ 7
        found = F.cross_shot([
            {"idx": 2, "image_prompt": "MAXIM wearing a red cap with two small white horns, red hoodie", "characters": ["MAXIM"]},
            {"idx": 7, "image_prompt": "MAXIM wearing a black cap with small red horns, red hoodie", "characters": ["MAXIM"]}])
        self.assertTrue(found)
        self.assertTrue(all(i["level"] == "warn" for i in found))
        text = " | ".join(i["msg"] for i in found)
        self.assertIn("2", text)
        self.assertIn("7", text)
        self.assertIn("cap", text)
        self.assertIn("horns", text)

    def test_print_colour_and_no_alarm_for_two_people(self):
        found = F.cross_shot([
            {"idx": 6, "image_prompt": "KELLY KL in a red croptop with a GREEN dinosaur print", "characters": ["KELLY KL"]},
            {"idx": 7, "motion_prompt": "KELLY KL keeps her blue dinosaur print visible", "characters": ["KELLY KL"]}])
        self.assertTrue(any("print" in i["msg"] for i in found), found)
        self.assertEqual(F.cross_shot([
            {"idx": 1, "image_prompt": "MAXIM in a red cap", "characters": ["MAXIM"]},
            {"idx": 2, "image_prompt": "KELLY in a black cap", "characters": ["KELLY"]}]), [])


class Growth(unittest.TestCase):
    def test_only_grown_and_contradicting(self):                                    # 4b: #24 shot 2 motion
        found = F.growth_check(P24_SHOT2_MOTION, P24_SHOT2_MOTION + " Static camera. Natural human eyes.")
        self.assertIn("warn", [i["level"] for i in found], found)
        self.assertTrue(any(i["level"] == "red" and "push in" in i["msg"].lower() for i in found), found)

    def test_a_real_rewrite_is_not_growth(self):
        new = "The clip starts on the first image. Kelly leans over the well and freezes, eyes down. Camera pushes in slowly."
        self.assertEqual(F.growth_check(P24_SHOT2_MOTION, new), [])
        self.assertEqual(F.growth_check(None, new), [])

    def test_review_shot(self):
        r = F.review_shot({"size": "MS", "characters": ["KELLY"]}, P24_SHOT2_IMAGE, P24_SHOT2_MOTION + " Static camera.",
                          previous={"motion": P24_SHOT2_MOTION})
        self.assertTrue(r["red"])
        self.assertTrue(r["image"])
        self.assertIn("growth", r)


# ---- tích hợp: Đạo diễn lưu kế hoạch → formula_check + diag; motion lưu → kiểm lại; red_issues --------------------------------
from core import llm_io  # noqa: E402
from core.db import connect  # noqa: E402
from core.pipeline import Pipeline  # noqa: E402
from tests.test_llm_io_preflight import ANALYSIS  # noqa: E402


def plan(image_prompt):
    obj = copy.deepcopy(ANALYSIS)
    obj["scenes"][0]["shots"] = [{"size": "MS", "role": "setup", "duration_s": 3, "image_prompt": image_prompt, "action": "Lyra cúi xuống giếng",
                                  "characters": ["Lyra"]}]
    return obj


class Integration(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        self.p.set_project_field(self.pid, "shot_mode", "per_shot")
        self.p.create_scene(self.pid, 1, "CẢNH 1")

    def row(self):
        r = self.p.conn.execute("SELECT id, data FROM scenes WHERE project_id=? ORDER BY idx LIMIT 1", (self.pid,)).fetchone()
        return r["id"], json.loads(r["data"])

    def diag(self):
        return [dict(r) for r in self.p.conn.execute("SELECT severity, message FROM diag_events WHERE code='prompt_formula'")]

    def test_director_plan_is_checked_and_recorded(self):
        with mock.patch.object(F, "enabled", return_value=True):
            llm_io.store_scene_analysis(self.p, self.pid, plan(P24_SHOT2_IMAGE))
            sid, data = self.row()
            fc = data["formula_check"]
            self.assertTrue(fc["red"])
            self.assertIn("at", fc)
            self.assertTrue(any(d["severity"] == "error" for d in self.diag()), self.diag())
            # a Free Fire project: the code adds the restraint sentence when sending (looks.gore_restraint) → not a stop
            self.assertEqual(F.red_issues(self.p.conn, sid), [])
            self.p.conn.execute("UPDATE projects SET game=? WHERE id=?", ("OTHER", self.pid))
            self.assertEqual(F.red_issues(self.p.conn, sid), [])          # F1 sửa #6: luật FF chỉ cảnh báo ở dự án khác
            self.p.conn.execute("UPDATE projects SET game=? WHERE id=?", ("FF", self.pid))
            # the Director writes again, only adding sentences that contradict → growth noted
            llm_io.store_scene_analysis(self.p, self.pid, plan(P24_SHOT2_IMAGE + ". Static camera. Natural human eyes."))
            _, data = self.row()
            self.assertTrue(any(i["level"] == "warn" for i in data["formula_check"]["growth"]), data["formula_check"])

    def test_motion_saved_is_checked_with_the_old_version(self):
        with mock.patch.object(F, "enabled", return_value=True):
            llm_io.store_scene_analysis(self.p, self.pid, plan(P22_CLEAN_IMAGE))
            sid, _ = self.row()
            self.assertEqual(F.red_issues(self.p.conn, sid), [])
            self.p.conn.execute("INSERT INTO jobs (project_id, scene_id, type, state, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                                (self.pid, sid, "image_gen", "approved", "x", "x"))
            idx = self.p.conn.execute("SELECT idx FROM scenes WHERE id=?", (sid,)).fetchone()["idx"]
            llm_io.store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": idx, "motion_prompt": P24_SHOT2_MOTION}]})
            llm_io.store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": idx, "motion_prompt": P24_SHOT2_MOTION + " Static camera. Natural human eyes."}]})
            _, data = self.row()
            fc = data["formula_check"]
            self.assertTrue(any(i["level"] == "red" for i in fc["growth"]), fc)
            self.assertTrue(F.red_issues(self.p.conn, sid, kind="motion"))
            self.assertEqual(F.red_issues(self.p.conn, sid, kind="image"), [])

    def test_red_issues_rechecks_a_prompt_changed_elsewhere(self):
        with mock.patch.object(F, "enabled", return_value=True):
            llm_io.store_scene_analysis(self.p, self.pid, plan(P22_CLEAN_IMAGE))
            sid, data = self.row()
            data["image_prompt"] = P24_SHOT3_IMAGE                     # changed without passing through a hook
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), sid))
            self.assertTrue(F.red_issues(self.p.conn, sid, kind="image"))

    def test_flag_off_checks_nothing(self):
        with mock.patch.object(F, "enabled", return_value=False):
            llm_io.store_scene_analysis(self.p, self.pid, plan(P24_SHOT2_IMAGE))
            sid, data = self.row()
            self.assertNotIn("formula_check", data)
            self.assertEqual(self.diag(), [])
            self.assertEqual(F.red_issues(self.p.conn, sid), [])

    def test_a_broken_check_never_loses_the_plan(self):
        with mock.patch.object(F, "enabled", return_value=True), mock.patch.object(F, "review_shot", side_effect=RuntimeError("boom")):
            llm_io.store_scene_analysis(self.p, self.pid, plan(P24_SHOT2_IMAGE))
        _, data = self.row()
        self.assertEqual(data["image_prompt"], P24_SHOT2_IMAGE)
        self.assertTrue(any("boom" in d["message"] for d in self.diag()), self.diag())

    def test_director_report_lists_formula_warnings(self):
        from core import director_report
        with mock.patch.object(F, "enabled", return_value=True):
            r = director_report.report(plan(P24_SHOT2_IMAGE), "CẢNH 1\nLyra cúi xuống giếng.")
        self.assertTrue(any("Công thức prompt" in w for w in r["continuity"]), r["continuity"])


class F1Fixes(unittest.TestCase):
    """Phiên sửa F1 (09/10): lỗi phiên rà xác nhận — mỗi test đỏ trước khi sửa."""

    def test_1_ghost_in_the_action_does_not_make_kelly_a_creature(self):
        from core import seedance_refs as sr
        d = {"size": "MS", "characters": ["KELLY"], "action": "Kelly freezes as the ghost streaks past far behind the well",
             "performance": {"intensity": 4, "face": "mouth opens wide", "eyes": "wide, fixed on the well"}}
        text = sr.shot_motion(d, humans={"KELLY": True})
        self.assertIn("KELLY: natural human eyes", text)
        self.assertNotIn("loai_nhan_vat", parts(F.check_motion(text, d), "red"))
        general = "The clip starts on the first image. Kelly turns. Static camera. Natural human eyes, no glowing eyes."
        self.assertNotIn("loai_nhan_vat", parts(F.check_motion(general, d), "red"))
        named = "The clip starts on the first image. Kelly turns. Static camera. YÊU NỮ: natural human eyes, no glowing eyes."
        self.assertIn("loai_nhan_vat", parts(F.check_motion(named, {"characters": ["KELLY", "YÊU NỮ"]}), "red"))

    def test_2_replaced_sentence_is_not_an_old_sentence(self):
        beats = [f"Kelly does beat number {i} slowly beside the old stone well." for i in range(9)]
        old = " ".join(beats + ["Static camera."])
        new = " ".join(beats + ["The camera slowly pushes in toward her."])
        self.assertEqual(F.growth_check(old, new), [])

    def test_6_blood_red_is_a_colour_and_other_games_only_warn(self):
        from core import looks
        self.assertEqual(looks.gore_words("a blood-red jacket, the bloodline"), [])
        self.assertEqual(looks.gore_words("a wound on his arm"), ["wound"])
        img = "Free Fire in-game 3D render, medium shot, Kelly stands in a blood-red jacket, cold moonlight"
        self.assertNotIn("luat_ff", parts(F.check_image(img, {"characters": ["KELLY"]})))
        found = F.check_image("Free Fire in-game 3D render, medium shot, Kelly stands, a wound on his arm, moonlight", {}, ff=False)
        self.assertIn("luat_ff", parts(found, "warn"))
        self.assertNotIn("luat_ff", parts(found, "red"))

    def test_9_legs_only_in_blocking_is_a_warning(self):
        img = "Free Fire in-game 3D render, medium close-up from mid-chest up, no legs, Kelly looks up, cold moonlight"
        found = F.check_image(img, {"size": "MCU", "characters": ["KELLY"], "blocking": "KELLY sprawled on the ground by the well"})
        self.assertNotIn("khung_hinh", parts(found, "red"), found)
        self.assertIn("khung_hinh", parts(found, "warn"), found)
        ref = "Free Fire in-game 3D render, medium close-up, no legs, Kelly looks up as in her full-body reference sheet, moonlight"
        self.assertNotIn("khung_hinh", parts(F.check_image(ref, {"characters": ["KELLY"]}), "red"))


class F1FixesDb(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        self.p.set_project_field(self.pid, "shot_mode", "per_shot")
        self.p.create_scene(self.pid, 1, "CẢNH 1")

    def test_3_red_issues_follows_the_plan_data_not_only_the_prompt(self):
        with mock.patch.object(F, "enabled", return_value=True):
            llm_io.store_scene_analysis(self.p, self.pid, plan(P22_CLEAN_IMAGE))
            r = self.p.conn.execute("SELECT id, data FROM scenes WHERE project_id=? LIMIT 1", (self.pid,)).fetchone()
            sid, data = r["id"], json.loads(r["data"])
            self.assertEqual(F.red_issues(self.p.conn, sid, "image"), [])
            data["size"] = "MCU"                                   # only the plan's size changes (prompt hash unchanged)
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), sid))
            self.assertTrue(F.red_issues(self.p.conn, sid, "image"))

    def _gore_motion(self, game):
        self.p.conn.execute("UPDATE projects SET game=? WHERE id=?", (game, self.pid))
        llm_io.store_scene_analysis(self.p, self.pid, plan(P22_CLEAN_IMAGE))
        sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? LIMIT 1", (self.pid,)).fetchone()["id"]
        self.p.conn.execute("INSERT INTO jobs (project_id, scene_id, type, state, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                            (self.pid, sid, "image_gen", "approved", "x", "x"))
        idx = self.p.conn.execute("SELECT idx FROM scenes WHERE id=?", (sid,)).fetchone()["idx"]
        llm_io.store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": idx, "motion_prompt": P22_CLEAN_MOTION + " A fresh wound on her arm."}]})
        return sid

    def test_5_gore_excused_only_when_the_sentence_really_goes(self):
        with mock.patch.object(F, "enabled", return_value=True):
            sid = self._gore_motion("FF")
            self.assertEqual(F.red_issues(self.p.conn, sid, "motion", gore_hinted=True), [])
            self.assertTrue(F.red_issues(self.p.conn, sid, "motion", gore_hinted=False))
            self.assertTrue(F.red_issues(self.p.conn, sid, "motion", gore_hinted=lambda: False))

    def test_6_other_game_gore_does_not_stop(self):
        with mock.patch.object(F, "enabled", return_value=True):
            sid = self._gore_motion("PUBG")
            self.assertEqual(F.red_issues(self.p.conn, sid, "motion", gore_hinted=False), [])


if __name__ == "__main__":
    unittest.main()


class RunnerGate(unittest.TestCase):
    """F1 (09/10): the picture runner does not pay for a prompt that breaks the formula (job → failed with the reason)."""
    def setUp(self):
        import tempfile
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        self.p.set_project_field(self.pid, "shot_mode", "per_shot")
        self.p.create_scene(self.pid, 1, "CẢNH 1")
        self.dir = tempfile.mkdtemp()

    def blocked(self, image_prompt):
        from core.runner import ImageRunner
        with mock.patch.object(F, "enabled", return_value=True):
            llm_io.store_scene_analysis(self.p, self.pid, plan(image_prompt))
            sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? LIMIT 1", (self.pid,)).fetchone()["id"]
            jid = self.p._insert_job(self.pid, sid, "image_gen")
            job = self.p.conn.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
            return ImageRunner(self.p, mock.Mock(), self.dir)._blocked(job)

    def test_shadow_past_her_face_is_held(self):
        reason = self.blocked(P24_SHOT3_IMAGE)
        self.assertIn("sai công thức", reason or "")

    def test_clean_prompt_goes(self):
        self.assertIsNone(self.blocked(P22_CLEAN_IMAGE))
