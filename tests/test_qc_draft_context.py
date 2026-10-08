"""08/10 (#24): QC clip NHÁP chỉ gợi ý + QC clip hiểu ngữ cảnh shot (biến hình / nhiễu chủ ý).

Dữ liệu thật dự án #24 (manifest.sqlite, chỉ đọc): job 592 (shot 7, scene 263) và 594 (shot 9, scene 265) là bản nháp
(quality_tier='draft'); QC chấm 0,59 / 0,65 → 'tự sửa' → rejected + xếp gen lại 596/597 (origin auto), Claude phải hủy tay. Lời QC:
592 "identity/style break … crosshatch comic-style linework" (đúng hồ sơ YÊU NỮ TÀ LINH DẠNG 2), 594 "artifacts 0.30 < 0.50 …
jerks" trên shot kịch bản ghi "màn hình nhòe, nhấp nháy, nhiễu sóng toàn khung như mất kết nối"."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import claude_tasks, experience, video_qc_context as vqc
from core.db import connect
from core.pipeline import Pipeline

ON = mock.patch("core.quality_tier.enabled", return_value=True)
OFF = mock.patch("core.quality_tier.enabled", return_value=False)

# scenes 263 / 265 of #24 (the fields QC reads)
SHOT7 = {"characters": ["YÊU NỮ TÀ LINH DẠNG 1", "YÊU NỮ TÀ LINH DẠNG 2"], "shot": "medium shot, eye angle, static",
         "action": "Yêu nữ đứng thẳng, chậm rãi quay đầu nhìn về phía Kelly đang ngồi bệt dưới đất, rồi biến hình từ dạng 1 sang "
                   "dạng 2, hiệu ứng glitch phủ toàn thân",
         "end_state": "the figure now in dạng 2 form: white hair with red tips, black face with round red eyes, crosshatch linework visible",
         "emotional_intent": "Người xem rùng mình theo đúng nhịp giật mình của Kelly",
         "motion_en": {"action": "the demoness stands upright, slowly turns her head to look toward KELLY sitting on the ground, then "
                                 "transforms from form 1 to form 2, glitch effect sweeping over her entire body"}}
MP7 = ("medium shot, eye angle, camera static: framing the creature right of center. the demoness stands upright, slowly turns her "
       "head to look toward KELLY sitting on the ground, then transforms from form 1 to form 2, glitch effect sweeping over her entire body.")
SHOT9 = {"characters": ["KELLY", "YÊU NỮ TÀ LINH DẠNG 2"], "shot": "wide shot, eye angle, whip",
         "action": "màn hình nhòe, nhấp nháy, nhiễu sóng toàn khung như mất kết nối",
         "motion_en": {"action": "the screen blurs, flickers, full-frame static distortion like a lost connection"}}
MP9 = ("wide shot, high angle, camera whip: Kelly small, seated on the ground frame-left. the screen blurs, flickers, full-frame "
       "static distortion like a lost connection.")
PLAIN = {"characters": ["KELLY"], "action": "Kelly bước tới giếng", "motion_en": {"action": "Kelly walks to the well"}}
QC592 = {"identity": 0.6, "physics": 0.75, "motion_match": 0.5, "artifacts": 0.5}
QC594 = {"identity": 0.9, "physics": 0.8, "motion_match": 0.6, "artifacts": 0.3}
ISSUES592 = "Fix identity/style break: the demoness's face shows crosshatch comic-style linework — unify render style."
ISSUES594 = "Increase digital noise/glitch intensity gradually; jerks were measured near 1.29-1.58s."
DESC2 = ("Chính yêu nữ tà linh sau khi biến hình: tóc trắng rất dài ngọn đỏ, mặt đen với hai mắt tròn đỏ, nét vẽ gạch chéo kiểu truyện "
         "tranh đen–trắng–đỏ; quanh toàn thân luôn có hiệu ứng nhiễu/glitch.")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("#24")
        self.p.conn.execute("UPDATE projects SET operating_mode='human_qc', qc_autofix=1, qc_auto_pass_threshold=0.82, "
                            "qc_reject_floor=0.5, max_retry_count=2 WHERE id=?", (self.pid,))
        for name, desc, lock in (("KELLY", "cô gái áo vàng", None),
                                 ("YÊU NỮ TÀ LINH DẠNG 1", "yêu nữ tóc đen váy trắng rách", None),
                                 ("YÊU NỮ TÀ LINH DẠNG 2", DESC2,
                                  {"must_keep": "comic-style black-white-red crosshatch linework, full-body glitch/noise effect",
                                   "may_change": "pose", "forbidden": "removing crosshatch linework"})):
            self.p.conn.execute("INSERT INTO characters (project_id, name, description, lock_rules) VALUES (?,?,?,?)",
                                (self.pid, name, desc, json.dumps(lock) if lock else None))
        self.p.conn.commit()

    def clip(self, data, tier="draft", mp="she moves"):
        sid = self.p.create_scene(self.pid, len(self.p.conn.execute("SELECT id FROM scenes").fetchall()) + 1, "shot")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), sid))
        self.p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, state) VALUES (?,?, 'approved')", (sid, mp))
        jid = self.p.create_job(sid, "video_gen")
        self.p.conn.execute("UPDATE jobs SET quality_tier=? WHERE id=?", (tier, jid))
        self.p.conn.commit()
        self.p.start(jid)
        self.p.succeed(jid)
        return sid, jid

    def jobs(self):
        return self.p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]


class DraftSuggestOnly(Base):
    def test_592_draft_below_threshold_waits_for_the_person_no_redo(self):
        with ON:
            _, j = self.clip(SHOT7, mp=MP7)
            before = self.jobs()
            self.assertEqual(self.p.apply_qc(j, QC592, issues=ISSUES592, autofix=True), "pending_review")
        self.assertEqual(self.p.state(j).value, "pending_review")
        self.assertEqual(self.jobs(), before)                                   # no 596 queued
        self.assertEqual(self.p.job(j)["escalated"], 0)
        note = self.p.history(j)[-1]["note"]
        self.assertIn("chỉ gợi ý", note)
        self.assertIn("crosshatch", note)                                       # the QC's issues stay readable for the person
        rows = self.p.conn.execute("SELECT criterion, score, auto_decision FROM qc_results WHERE job_id=?", (j,)).fetchall()
        self.assertEqual({r["criterion"]: r["score"] for r in rows}, QC592)
        self.assertTrue(all(r["auto_decision"] is None for r in rows))
        said = self.p.conn.execute("SELECT * FROM diag_events WHERE code='qc_draft_suggest'").fetchall()
        self.assertEqual(len(said), 1)
        self.assertEqual(said[0]["job_id"], j)

    def test_594_hard_floor_below_reject_floor_still_waits(self):
        with ON:
            _, j = self.clip(SHOT9, mp=MP9)
            before = self.jobs()
            self.assertEqual(self.p.apply_qc(j, QC594, issues=ISSUES594, autofix=True), "pending_review")
        self.assertEqual((self.p.state(j).value, self.jobs()), ("pending_review", before))

    def test_draft_in_auto_mode_is_not_approved_or_rejected_by_the_machine(self):
        self.p.conn.execute("UPDATE projects SET operating_mode='auto' WHERE id=?", (self.pid,))
        self.p.conn.commit()
        with ON:
            _, good = self.clip(PLAIN)
            _, bad = self.clip(PLAIN)
            self.assertEqual(self.p.apply_qc(good, {"identity": 0.95, "physics": 0.9, "motion_match": 0.9, "artifacts": 0.9}),
                             "pending_review")
            self.assertEqual(self.p.apply_qc(bad, {"identity": 0.2, "physics": 0.2, "motion_match": 0.2, "artifacts": 0.2},
                                             issues="Fix everything."), "pending_review")
        self.assertEqual(self.p.state(good).value, "pending_review")
        self.assertEqual(self.p.state(bad).value, "pending_review")

    def test_final_and_direct_keep_the_old_automatic_redo(self):
        with ON:
            for tier in ("final", "direct"):
                _, j = self.clip(PLAIN, tier=tier)
                before = self.jobs()
                self.assertEqual(self.p.apply_qc(j, QC592, issues="Keep the yellow jacket.", autofix=True), "auto_fix")
                self.assertEqual(self.p.state(j).value, "rejected")
                self.assertEqual(self.jobs(), before + 1)

    def test_flag_off_draft_label_changes_nothing(self):
        with OFF:
            _, j = self.clip(PLAIN)
            self.assertEqual(self.p.apply_qc(j, QC592, issues="Keep the yellow jacket.", autofix=True), "auto_fix")

    def test_images_are_untouched(self):
        with ON:
            sid = self.p.create_scene(self.pid, 99, "img")
            j = self.p.create_job(sid)
            self.p.start(j)
            self.p.succeed(j)
            self.assertEqual(self.p.apply_qc(j, {"pose": 0.2}, issues="Fix pose.", autofix=True), "auto_fix")


class Context(Base):
    def test_shot7_gets_both_forms_with_profiles_and_the_transformation(self):
        data = dict(SHOT7, characters=["YÊU NỮ TÀ LINH DẠNG 1"])      # the form after the transformation is NOT listed
        names = vqc.shot_characters(self.p.conn, self.pid, data, MP7)
        self.assertEqual(names, ["YÊU NỮ TÀ LINH DẠNG 1", "KELLY", "YÊU NỮ TÀ LINH DẠNG 2"])   # Kelly: named in the action
        block = vqc.profiles_block(self.p.conn, self.pid, names)
        self.assertIn("nét vẽ gạch chéo kiểu truyện tranh", block)
        self.assertIn("YÊU NỮ TÀ LINH DẠNG 1 → YÊU NỮ TÀ LINH DẠNG 2", block)
        intent = vqc.intent_block(SHOT7, MP7)
        self.assertIn("BIẾN HÌNH", intent)
        self.assertIn("KHÔNG phải lỗi", intent)

    def test_noise_is_recognised_by_code_and_artifacts_is_soft(self):
        self.assertEqual(vqc.soft_criteria(SHOT9, MP9), ("artifacts",))
        self.assertIn("NHIỄU CHỦ Ý", vqc.intent_block(SHOT9, MP9))
        self.assertEqual(vqc.soft_criteria(PLAIN, "medium shot, camera static: Kelly walks"), ())   # "camera static" ≠ noise
        self.assertEqual(vqc.intended_effects(PLAIN, "camera static")["transform"], [])
        # a character called "… DẠNG 2" in a plain shot is not a transformation
        self.assertEqual(vqc.intended_effects({"action": "YÊU NỮ TÀ LINH DẠNG 2 quỳ khóc"})["transform"], [])

    def test_soft_artifacts_does_not_hard_block_a_final(self):
        with ON:
            _, j = self.clip(SHOT9, tier="final", mp=MP9)
            self.p.apply_qc(j, QC594, issues=ISSUES594, autofix=True, soft=vqc.soft_criteria(SHOT9, MP9))
        notes = " ".join(r["note"] or "" for r in self.p.history(j))
        self.assertNotIn("chặn cứng", notes)


class QcVideoPrompt(Base):
    def run_qc(self, data, mp, answer, tier="draft"):
        sid, j = self.clip(data, tier=tier, mp=mp)
        clip = os.path.join(self.tmp, f"c{j}.mp4")
        with open(clip, "wb") as f:
            f.write(b"x")
        self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (clip, j))
        self.p.conn.commit()
        seen = {}

        def fake_run(p, pid, stage, prompt, validate, client, images=()):
            seen["prompt"] = prompt
            validate(answer)
            return answer

        def frames(path, out_dir, count=8):
            os.makedirs(out_dir, exist_ok=True)
            out = os.path.join(out_dir, "frame_01.jpg")
            with open(out, "wb") as f:
                f.write(b"j")
            return [out]
        with ON, mock.patch("core.claude_tasks._run", fake_run), mock.patch("core.video_analysis.extract_frames", frames), \
                mock.patch("core.video_analysis.probe", return_value={"duration_sec": 2.5}), \
                mock.patch("core.claude_tasks._measure_clip", return_value=None):
            out = claude_tasks.qc_video(self.p, j, object(), self.tmp)
        return j, out, seen["prompt"]

    def test_592_prompt_has_profiles_intent_and_draft_waits(self):
        j, out, prompt = self.run_qc(SHOT7, MP7, {"criteria": QC592, "issues": ISSUES592})
        self.assertEqual(out["decision"], "pending_review")
        self.assertIn("Hồ sơ nhân vật trong shot", prompt)
        self.assertIn("nét vẽ gạch chéo", prompt)
        self.assertIn("- **YÊU NỮ TÀ LINH DẠNG 2** — giữ: comic-style", prompt)   # its Character Lock too
        self.assertIn("Hành động & ý đồ của shot", prompt)
        self.assertIn("biến hình từ dạng 1 sang dạng 2", prompt)
        self.assertIn("Hiệu ứng CHỦ Ý của kịch bản không phải lỗi", prompt)      # prompts/12_video_qc.md lesson
        case = self.p.conn.execute("SELECT * FROM experience_cases WHERE key=?", (f"intended_effect:{j}",)).fetchone()
        self.assertIsNotNone(case)
        self.assertEqual((case["outcome"], case["kind"], case["confirmed_by"]), ("false_alarm", "intended_effect", None))

    def test_594_final_artifacts_not_hard_blocked(self):
        j, out, prompt = self.run_qc(SHOT9, MP9, {"criteria": QC594, "issues": ISSUES594}, tier="final")
        self.assertIn("NHIỄU CHỦ Ý", prompt)
        notes = " ".join(r["note"] or "" for r in self.p.history(j))
        self.assertNotIn("chặn cứng", notes)

    def test_plain_shot_records_no_case(self):
        j, _, prompt = self.run_qc(PLAIN, "Kelly walks to the well", {"criteria": QC592, "issues": "Keep the jacket."})
        self.assertNotIn("NHIỄU CHỦ Ý", prompt)
        experience.ensure(self.p.conn)
        self.assertIsNone(self.p.conn.execute("SELECT 1 FROM experience_cases WHERE key=?", (f"intended_effect:{j}",)).fetchone())


if __name__ == "__main__":
    unittest.main()
