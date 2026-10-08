"""Khủng Long Đỏ (#22) — 3 thay đổi P1 người dùng duyệt 08/10 (docs/TONG_HOP_3_LUOT_KHUNG_LONG_DO.md mục 4–5):
KLD-4 khóa nhận dạng của nhân vật có ảnh OUTFIT chỉ gồm mặt/tóc/dáng; KLD-5 không tự gen lại clip khi lỗi duy nhất là look_drift trên
đường Seedance chỉ-ảnh-tham-chiếu; KLD-7 câu "bỏ tóc/mặt/dáng người mẫu, phụ kiện đeo đúng như ảnh" sau cờ outfit_strip_model (TẮT).
Không gọi nhà cung cấp thật."""
import json
import os
import unittest
from unittest import mock

from core import assets, features, prompts, seedance_refs
from core.db import connect
from core.pipeline import Pipeline

PROFILE = {"approved": True, "asset": "MAXIM", "identity": "Maxim — lean young man, black baseball cap worn backwards",
           "must_keep": "short black hair, sharp jaw, black baseball cap worn backwards, bomber jacket",
           "may_change": "expression", "forbidden": "no beard, never without the bomber jacket", "height_m": 1.8, "build": "lean"}


class OutfitLockTextTests(unittest.TestCase):
    """KLD-4: qc_team blocked 6/9 frames the user approved — lock_text gave MAXIM KL the everyday clothes of MAXIM's profile."""

    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("kld")
        for name, outfit in (("MAXIM KL", "7"), ("MAXIM", None)):
            self.p.conn.execute("INSERT INTO characters (project_id, name, description, outfit_image_ids) VALUES (?,?,?,?)",
                                (self.pid, name, "x", outfit))
        self.p.conn.commit()

    def lock(self, names):
        with mock.patch.object(assets, "standard_for", return_value=dict(PROFILE)):
            return prompts.lock_text(self.p.conn, self.pid, names)

    def test_a_costumed_character_is_locked_on_face_hair_build_only(self):
        text = self.lock(["MAXIM KL"])
        self.assertIn("MAXIM KL", text)
        self.assertNotIn("bomber jacket", text)
        self.assertNotIn("black baseball cap", text)
        self.assertIn("ảnh OUTFIT", text)
        self.assertIn("không theo đồ thường của hồ sơ", text)
        self.assertIn("1.8", text)                     # the body build stays locked
        self.assertIn("lean", text)

    def test_the_everyday_character_keeps_the_whole_profile(self):
        text = self.lock(["MAXIM"])
        self.assertIn("black baseball cap worn backwards", text)
        self.assertNotIn("ảnh OUTFIT", text)


class LookDriftNoRetryTests(unittest.TestCase):
    """KLD-5: clip 255 was regenerated for a smooth face (0,81 < 0,82) on the reference-only route — the new take scored 0,72, 2,76 USD lost."""

    BAD = {"identity": .55, "physics": .85, "motion_match": .85, "artifacts": .85}     # only identity fails (overall 0,78 < 0,82)
    LOOK = {"look": {"flag": "look_drift", "why": "mặt mịn × 0,2"}, "flags": ["look_drift"]}

    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("kld", operating_mode="auto", threshold=0.82, max_retry=2)
        self.sid = self.p.create_scene(self.pid, 1)
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"characters": ["KELLY KL"]}), self.sid))
        self.p.conn.commit()

    def clip(self):
        jid = self.p.create_job(self.sid, "video_gen")
        self.p.start(jid)
        self.p.succeed(jid)
        return jid

    def queued(self):
        return self.p.conn.execute("SELECT COUNT(*) FROM jobs WHERE scene_id=? AND state='queued'", (self.sid,)).fetchone()[0]

    def test_look_drift_alone_on_the_reference_route_is_kept_for_the_person(self):
        jid = self.clip()
        with mock.patch.object(seedance_refs, "uses_refs", return_value=True):
            out = self.p.apply_qc(jid, self.BAD, issues="Fix: smooth face.", measured=self.LOOK)
        self.assertEqual(out, "needs_review")
        self.assertEqual(self.queued(), 0)                              # no paid take with the same route
        note = self.p.conn.execute("SELECT note FROM job_events WHERE job_id=? ORDER BY id DESC LIMIT 1", (jid,)).fetchone()["note"]
        self.assertIn("đặc tính model", note)
        case = self.p.conn.execute("SELECT * FROM experience_cases WHERE job_id=?", (jid,)).fetchone()
        self.assertEqual(case["kind"], "model_property")
        self.assertEqual(case["stage"], "video")

    def test_the_kling_route_still_retries(self):
        with mock.patch.object(seedance_refs, "uses_refs", return_value=False):
            self.assertEqual(self.p.apply_qc(self.clip(), self.BAD, issues="Fix: smooth face.", measured=self.LOOK), "rejected")
        self.assertEqual(self.queued(), 1)

    def test_another_fault_besides_look_drift_still_retries(self):
        bad = dict(self.BAD, motion_match=.4)
        with mock.patch.object(seedance_refs, "uses_refs", return_value=True):
            self.assertEqual(self.p.apply_qc(self.clip(), bad, issues="Kelly turns left.", measured=self.LOOK), "rejected")

    def test_without_the_measured_flag_it_still_retries(self):
        with mock.patch.object(seedance_refs, "uses_refs", return_value=True):
            self.assertEqual(self.p.apply_qc(self.clip(), self.BAD, issues="Keep Kelly's face.", measured={"flags": []}), "rejected")


class OutfitStripModelTests(unittest.TestCase):
    """KLD-7: Kelly KL's hair took the silver of the model wearing the OUTFIT (544/545 rejected, ≈ 2,8 USD)."""

    IDS = [("KELLY", "k.png"), ("KELLY" + seedance_refs.OUTFIT_TAG, "o.png")]
    REFS = [{"path": "k.png", "label": "KELLY", "role": "character"}, {"path": "o.png", "label": "KELLY", "role": "outfit"}]

    def texts(self, on):
        with mock.patch.dict(os.environ, {"FEATURE_OUTFIT_STRIP_MODEL": "1" if on else "0"}):
            return seedance_refs.prompt([("Kelly spins", 5)], self.IDS), assets.reference_note(self.REFS)

    def test_the_flag_is_off_and_unverified(self):
        self.assertIn("outfit_strip_model", features.FEATURES)
        self.assertFalse(features.FEATURES["outfit_strip_model"]["verified"])
        self.assertIn("KLD-7", features.FEATURES["outfit_strip_model"]["why"])

    def test_off_the_prompts_stay_as_they_were(self):
        for text in self.texts(False):
            self.assertNotIn("modelling these clothes", text)

    def test_on_the_model_wearing_the_outfit_is_dropped_and_accessories_stay_on(self):
        video, image = self.texts(True)
        for text in (video, image):
            self.assertIn("ignore the hair, face and body of any person modelling these clothes", text)
            self.assertIn("wear each accessory exactly as the picture shows it", text)
        self.assertIn("as the picture shows it, for the whole clip", video)     # a still picture has no "whole clip"


if __name__ == "__main__":
    unittest.main()
