"""C2 (15/10, docs/handoff/RA_QUYET_DINH_LOI_LAP_2026-10-15.md mục C.2): #27 had 53/78 rejects without a reason and 0 `mistakes` rows
for #24/#27 — the lesson loop was dead. A reject now carries a reason from one fixed list (core/lessons.REJECT_REASONS); the Dashboard
buttons cannot be pressed without one; old code / the machine without one still works and is recorded as 'chua_ghi' + diag."""
import os
import shutil
import tempfile
import unittest

from core import lessons
from core.db import connect
from core.pipeline import Pipeline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _job(p, pid, kind="image_gen"):
    idx = p.conn.execute("SELECT COALESCE(MAX(idx), 0) + 1 FROM scenes WHERE project_id=?", (pid,)).fetchone()[0]
    p.conn.execute("INSERT INTO scenes (project_id, idx, data, state) VALUES (?,?,?,?)", (pid, idx, '{"image_prompt": "a hero"}', "ready"))
    sid = p.conn.execute("SELECT MAX(id) FROM scenes").fetchone()[0]
    jid = p.create_job(sid, kind)
    p.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (jid,))
    p.conn.commit()
    return jid


class RejectReasonTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["KNOWLEDGE_USER_DIR"] = self.dir
        self.p = Pipeline(connect())
        self.conn = self.p.conn
        self.pid = self.p.create_project("p", "human_qc", 0.85, 2)

    def tearDown(self):
        os.environ.pop("KNOWLEDGE_USER_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_one_list_reuses_the_lesson_tags(self):
        for code, (label, tag) in lessons.REJECT_REASONS.items():
            self.assertTrue(label)
            if tag is not None:
                self.assertIn(tag, {**lessons.TAGS, **{t: v[:2] for t, v in lessons.RISK_TAGS.items()}})   # no second catalogue
        self.assertIn("khac", lessons.REJECT_REASONS)
        self.assertNotIn(lessons.NO_REASON, lessons.REJECT_REASONS)                 # never offered on the button

    def test_the_ui_check_blocks_a_reject_without_a_reason(self):
        self.assertIsNotNone(lessons.reject_reason_error(None, ""))
        self.assertIsNotNone(lessons.reject_reason_error("", "x"))
        self.assertIsNotNone(lessons.reject_reason_error("khac", "  "))            # 'khác' needs words
        self.assertIsNotNone(lessons.reject_reason_error("chua_ghi", ""))         # the system value is not a choice
        self.assertIsNone(lessons.reject_reason_error("nen_lech_map3d", ""))
        self.assertIsNone(lessons.reject_reason_error("khac", "tay cầm ngược súng"))

    def test_every_dashboard_reject_button_is_disabled_without_a_reason(self):
        """The person (and Claude driving ?op=claude) cannot press Loại / Vẽ lại / Loại & gen lại without a reason."""
        for rel in ("dashboard/steps/step2.py", "dashboard/steps/step4.py", "dashboard/design/screens/storyboard_cards.py"):
            with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
                src = f.read()
            for line in [ln for ln in src.splitlines() if "p.reject(" in ln]:
                self.assertIn("reason=", line, f"{rel}: {line.strip()}")
            self.assertIn("reject_reason_ui.pick(", src, rel)
            self.assertIn("disabled=", src, rel)

    def test_a_reject_with_a_reason_is_kept_on_the_job_and_becomes_a_mistake(self):
        jid = _job(self.p, self.pid)
        self.p.reject(jid, "user", "Kelly đứng sai chỗ", respawn=False, reason="bo_cuc_cho_dung")
        self.assertEqual(self.p.job(jid)["reject_reason"], "bo_cuc_cho_dung")
        log = self.conn.execute("SELECT id, reason FROM review_log WHERE job_id=? AND decision='reject'", (jid,)).fetchone()
        self.assertEqual(log["reason"], "bo_cuc_cho_dung")
        m = self.conn.execute("SELECT * FROM mistakes WHERE source='review' AND ref_id=?", (log["id"],)).fetchone()
        self.assertIsNotNone(m)                                                    # at once, no harvest needed
        self.assertEqual(m["reason"], "bo_cuc_cho_dung")
        self.assertEqual(m["stage"], "image")
        self.assertEqual(lessons.harvest(self.conn), 0)                             # never twice
        kinds = {c["tag"] for c in lessons.clusters(self.conn)}
        self.assertIn("composition", kinds)                                         # the enum decides the kind, not keywords

    def test_khac_keeps_the_words(self):
        jid = _job(self.p, self.pid, "video_gen")
        with self.assertRaises(ValueError):
            self.p.reject(jid, "user", None, respawn=False, reason="khac")
        self.assertEqual(self.p.job(jid)["state"], "pending_review")                # nothing done before the check
        self.p.reject(jid, "user", None, respawn=False, reason="khac", reason_text="súng cầm ngược tay")
        m = self.conn.execute("SELECT * FROM mistakes").fetchone()
        self.assertIn("súng cầm ngược tay", m["text"])
        self.assertEqual(m["stage"], "video")

    def test_an_unknown_reason_raises_before_anything(self):
        jid = _job(self.p, self.pid)
        with self.assertRaises(ValueError):
            self.p.reject(jid, "user", "x", respawn=False, reason="xau_qua")
        self.assertEqual(self.p.job(jid)["state"], "pending_review")

    def test_old_code_without_a_reason_still_works_and_says_so(self):
        jid = _job(self.p, self.pid)
        self.assertEqual(self.p.reject(jid, "user", "sai tay", respawn=False), "rejected")
        self.assertEqual(self.p.job(jid)["reject_reason"], lessons.NO_REASON)
        self.assertEqual(self.conn.execute("SELECT reason FROM review_log WHERE job_id=?", (jid,)).fetchone()[0], lessons.NO_REASON)
        self.assertTrue(self.conn.execute("SELECT 1 FROM diag_events WHERE code='reject_no_reason'").fetchone())
        self.assertIsNone(self.conn.execute("SELECT 1 FROM mistakes").fetchone())   # left to harvest's keywords, as before
        jid2 = _job(self.p, self.pid)
        self.assertIn(self.p.reject(jid2, "ai_agent", "QC 0.4 < 0.7 — tay thừa ngón"), ("rejected", "escalated"))   # the machine too
        self.assertEqual(self.p.job(jid2)["reject_reason"], lessons.NO_REASON)

    def test_not_a_fault_is_not_a_mistake(self):
        jid = _job(self.p, self.pid)
        self.p.reject(jid, "user", "đã xóa", respawn=False, reason=lessons.NOT_A_FAULT)
        self.assertIsNone(self.conn.execute("SELECT 1 FROM diag_events WHERE code='reject_no_reason'").fetchone())
        self.assertEqual(lessons.harvest(self.conn), 0)
        self.assertIsNone(self.conn.execute("SELECT 1 FROM mistakes").fetchone())

    def test_rates_by_reason_and_project(self):
        other = self.p.create_project("q", "human_qc", 0.85, 2)
        for reason in ("nen_lech_map3d", "nen_lech_map3d", "nhan_vat_sai"):
            self.p.reject(_job(self.p, self.pid), "user", None, respawn=False, reason=reason)
        self.p.reject(_job(self.p, self.pid), "user", "x", respawn=False)                        # chua_ghi
        self.p.reject(_job(self.p, self.pid, "video_gen"), "user", None, respawn=False, reason="chuyen_dong_sai")
        self.p.reject(_job(self.p, other), "user", None, respawn=False, reason="dao_cu_kho_sai")
        rows = lessons.reject_rates(self.conn)
        get = {(r["project_id"], r["kind"], r["reason"]): r for r in rows}
        r = get[(self.pid, "image", "nen_lech_map3d")]
        self.assertEqual((r["n"], r["total"]), (2, 4))
        self.assertAlmostEqual(r["share"], 0.5)
        self.assertEqual(get[(self.pid, "image", lessons.NO_REASON)]["n"], 1)
        self.assertEqual(get[(self.pid, "video", "chuyen_dong_sai")]["share"], 1.0)
        self.assertEqual(get[(other, "image", "dao_cu_kho_sai")]["total"], 1)
        self.assertEqual({r["project_id"] for r in lessons.reject_rates(self.conn, project_id=other)}, {other})


if __name__ == "__main__":
    unittest.main()
