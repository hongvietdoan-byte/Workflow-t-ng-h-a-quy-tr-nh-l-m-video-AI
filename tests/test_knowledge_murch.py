"""S14.20 — Bộ não prompt Đợt 2 (docs/KE_HOACH_BO_NAO_PROMPT_TU_HOC_2026-10-04.md mục "Đợt 2"):
2a trục Murch (knowledge/craft/uu_tien_cam_xuc.md) cho Director + motion, 2b tách tag `motion` thành 6 trục rủi ro + "chưa phân loại",
2c knowledge/i2v_motion_discipline.md, 2d knowledge/sound_design_method.md.

Luật: mọi thứ mới nằm sau cờ (`murch_knowledge`, `risk_tags`), TẮT mặc định; cờ tắt → prompt Y HỆT trước."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import claude_tasks, features, knowledge, lessons, prompts, story_check
from core.db import connect
from core.llm_io import SchemaError, store_scene_analysis
from core.pipeline import Pipeline
from tests.test_llm_io_preflight import ANALYSIS

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flags(**kw):
    return mock.patch.dict(os.environ, {f"FEATURE_{k.upper()}": v for k, v in kw.items()})


class _Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"KNOWLEDGE_USER_DIR": self.dir})
        self.env.start()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        sid = self.p.create_scene(self.pid, 1, "CẢNH 1")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                            (json.dumps({"text": "Sương mù dày đặc."}, ensure_ascii=False), sid))
        store_scene_analysis(self.p, self.pid, ANALYSIS)

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.dir, ignore_errors=True)


class FlagTests(unittest.TestCase):
    def test_new_flags_are_off_and_unverified(self):
        for name in ("murch_knowledge", "risk_tags"):
            self.assertIn(name, features.FEATURES)
            self.assertFalse(features.FEATURES[name]["verified"])
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("FEATURE_" + name.upper(), None)
                self.assertFalse(features.on(name))


class PromptsUnchangedWhenOffTests(_Base):
    """Cờ tắt: prompt sinh ra bằng đúng chuỗi khi bỏ hẳn phần mới (móc nạp trả rỗng)."""

    def _bundles(self):
        return {"director": prompts.build_director_bundle(self.p, self.pid),
                "intent": prompts.build_intent_bundle(self.p, self.pid),
                "motion": prompts.build_motion_bundle(self.p, self.pid)}

    def test_bundles_identical_with_flag_off(self):
        for crew in ("0", "1"):
            with _flags(murch_knowledge="0", film_crew=crew):
                now = self._bundles()
                with mock.patch.object(knowledge, "murch_blocks", lambda group: []):
                    without = self._bundles()
            self.assertEqual(now, without, f"film_crew={crew}")
            for text in now.values():
                self.assertNotIn("Thứ tự ưu tiên cảm xúc", text)
                self.assertNotIn("Kỷ luật chuyển động I2V", text)
                self.assertNotIn("Phương pháp thiết kế âm thanh", text)

    def test_murch_blocks_empty_when_off(self):
        with _flags(murch_knowledge="0"):
            self.assertEqual(knowledge.murch_blocks("director"), [])
            self.assertEqual(knowledge.murch_blocks("motion"), [])
            files = {d["file"] for g in ("director", "motion") for d in knowledge.builtin_docs(g)}
        self.assertFalse(files & {"knowledge/craft/uu_tien_cam_xuc.md", "knowledge/i2v_motion_discipline.md",
                                  "knowledge/sound_design_method.md"})

    def test_first_viewer_prompt_identical_with_flag_off(self):
        seen = {}

        def fake(p, pid, group, prompt, check, client):
            seen["prompt"] = prompt
            return {"summary": "x", "understood": 3}

        with _flags(murch_knowledge="0"), mock.patch.object(claude_tasks, "_run", fake):
            story_check.run(self.p, self.pid, None, tempfile.mkdtemp(dir=self.dir))
        film = story_check.digest(self.p, self.pid)
        expected = claude_tasks._read("prompts", story_check.PROMPT) + "\n\n---\n\n" + claude_tasks._block(
            "Phim (theo thứ tự trên màn hình)", film)
        self.assertEqual(seen["prompt"], expected)
        self.assertNotIn("cam_xuc", seen["prompt"])


class PromptsWithFlagOnTests(_Base):
    def test_motion_bundle_reads_murch_i2v_and_the_addendum(self):
        with _flags(murch_knowledge="1"):
            text = prompts.build_motion_bundle(self.p, self.pid)
        rules = text.split(prompts.CACHE_BREAK)[0]           # knowledge sits in the cached rules part
        self.assertIn("Thứ tự ưu tiên cảm xúc", rules)
        self.assertIn("Kỷ luật chuyển động I2V", rules)
        self.assertIn(_read("prompts", "03_video_motion_murch.md").strip()[:80], rules)
        self.assertNotIn("Phương pháp thiết kế âm thanh", text)       # sound method is the Director's

    def test_director_bundles_read_murch_and_sound_method(self):
        for crew in ("0", "1"):
            with _flags(murch_knowledge="1", film_crew=crew):
                for text in (prompts.build_director_bundle(self.p, self.pid), prompts.build_intent_bundle(self.p, self.pid)):
                    self.assertIn("Thứ tự ưu tiên cảm xúc", text)
                    self.assertIn("Phương pháp thiết kế âm thanh", text)
                    self.assertNotIn("Kỷ luật chuyển động I2V", text)

    def test_knowledge_page_lists_the_new_docs(self):
        with _flags(murch_knowledge="1"):
            d = {x["file"] for x in knowledge.builtin_docs("director")}
            m = {x["file"] for x in knowledge.builtin_docs("motion")}
        self.assertTrue({"knowledge/craft/uu_tien_cam_xuc.md", "knowledge/sound_design_method.md"} <= d)
        self.assertTrue({"knowledge/craft/uu_tien_cam_xuc.md", "knowledge/i2v_motion_discipline.md",
                         "prompts/03_video_motion_murch.md"} <= m)

    def test_motion_group_stays_under_the_char_limit(self):
        with _flags(murch_knowledge="1", film_crew="1"):
            o = knowledge.overview("motion")
            self.assertTrue(o["chars"] < knowledge.MAX_USER_CHARS, o["chars"])
            self.assertTrue(o["raw_chars"] < knowledge.MAX_USER_CHARS, o["raw_chars"])

    def test_first_viewer_asks_for_cam_xuc_with_flag_on(self):
        seen = {}

        def fake(p, pid, group, prompt, check, client):
            seen["prompt"] = prompt
            return {"summary": "x", "understood": 3, "cam_xuc": 4}

        with _flags(murch_knowledge="1"), mock.patch.object(claude_tasks, "_run", fake):
            res = story_check.run(self.p, self.pid, None, tempfile.mkdtemp(dir=self.dir))
        self.assertIn("cam_xuc", seen["prompt"])
        self.assertEqual(res["cam_xuc"], 4)
        self.assertTrue(any("cảm xúc 4/5" in x for x in story_check.lines(res)))

    def test_cam_xuc_checked_when_present(self):
        story_check._check({"summary": "x", "understood": 3})                     # optional
        story_check._check({"summary": "x", "understood": 3, "cam_xuc": 5})
        with self.assertRaises(SchemaError):
            story_check._check({"summary": "x", "understood": 3, "cam_xuc": 7})


class KnowledgeTextTests(unittest.TestCase):
    def test_murch_axis_keeps_the_agreed_sentences(self):
        text = _read("knowledge", "craft", "uu_tien_cam_xuc.md")
        self.assertIn("cảm xúc nặng hơn năm tiêu chí còn lại cộng lại; phải hy sinh thì bỏ từ dưới lên", text)
        self.assertIn("ở khâu dựng, cảm xúc đứng dưới điều kiện nghe rõ thoại và đọc được chữ", text)
        order = ["cảm xúc", "câu chuyện", "nhịp", "hướng mắt", "mặt phẳng 2d", "không gian 3d"]
        body = text[text.index("## Thang"):].lower()
        pos = [body.find(x) for x in order]
        self.assertTrue(all(p >= 0 for p in pos), pos)
        self.assertEqual(pos, sorted(pos))
        self.assertIn("editor/editing.md", text)           # nguồn, không chép lại

    def test_i2v_doc_has_exactly_the_three_parts_and_every_risk_tag(self):
        text = _read("knowledge", "i2v_motion_discipline.md")
        self.assertEqual(len([ln for ln in text.splitlines() if ln.startswith("## ")]), 3)
        for tag in lessons.RISK_TAGS:
            self.assertIn(f"`{tag}`", text)
        self.assertIn("heuristic", text)
        for p in ("P0", "P1", "P2", "P3", "P4", "P5"):
            self.assertIn(p, text)

    def test_sound_method_has_four_parts_and_names_no_files(self):
        text = _read("knowledge", "sound_design_method.md")
        self.assertEqual(len([ln for ln in text.splitlines() if ln.startswith("## ")]), 4)
        self.assertNotRegex(text, r"\.(wav|mp3|ogg|flac)\b")
        self.assertIn("nhac_nen.md", text)

    def test_risk_tags_are_named_in_the_motion_addendum(self):
        text = _read("prompts", "03_video_motion_murch.md")
        for tag in ("face_morph", "body_deform", "wardrobe_drift", "background_drift", "motion_overload", "text_logo_corrupt"):
            self.assertIn(tag, text)


class RiskTagTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"KNOWLEDGE_USER_DIR": self.dir})
        self.env.start()
        self.conn = Pipeline(connect()).conn

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_six_risk_axes_plus_feedback_tags(self):
        self.assertEqual(list(lessons.RISK_TAGS)[:6], ["face_morph", "body_deform", "wardrobe_drift", "background_drift",
                                                       "motion_overload", "text_logo_corrupt"])
        for t in ("identity", "physics", "lipsync", "audio"):
            self.assertIn(t, lessons.RISK_TAGS)

    def test_off_keeps_the_single_motion_tag(self):
        with _flags(risk_tags="0"):
            self.assertIn("motion", lessons.tags_of("mặt biến dạng khi quay đầu"))
            self.assertNotIn("face_morph", lessons.tags_of("mặt biến dạng khi quay đầu"))

    def test_on_splits_motion_into_the_risk_axes(self):
        with _flags(risk_tags="1"):
            face = lessons.tags_of("mặt biến dạng khi quay đầu")
            bg = lessons.tags_of("nền trôi khi orbit")
            self.assertIn("face_morph", face)
            self.assertNotIn("motion", face)
            self.assertIn("background_drift", bg)
            self.assertNotIn("face_morph", bg)
            self.assertIn("wardrobe_drift", lessons.tags_of("áo choàng đổi màu giữa clip"))
            self.assertIn("text_logo_corrupt", lessons.tags_of("chữ trên biển hiệu nhòe"))
            self.assertIn("lipsync", lessons.tags_of("khớp môi lệch câu thoại"))

    def _mistakes(self, texts, stage="video"):
        for n, t in enumerate(texts):
            self.conn.execute("INSERT INTO mistakes (source, ref_id, at, project_id, stage, group_name, text)"
                              " VALUES (?,?,?,?,?,?,?)", ("review", 1000 + n, "2026-10-05", 1 + n % 2, stage,
                                                          lessons.GROUP_OF_STAGE[stage], t))
        self.conn.commit()

    def test_unclassified_mistakes_are_shown_and_warned_with_flag_on(self):
        self._mistakes(["clip này nhìn kỳ kỳ", "không ưng", "mặt biến dạng khi quay đầu"])
        with _flags(risk_tags="1"):
            rows = lessons.clusters(self.conn)
        un = [r for r in rows if r["tag"] == lessons.UNCLASSIFIED]
        self.assertEqual(len(un), 1)
        self.assertEqual(un[0]["events"], 2)
        self.assertEqual(un[0]["label"], "Chưa phân loại")
        self.assertFalse(un[0]["ready"])                          # never proposed as a lesson
        warn = self.conn.execute("SELECT severity, message FROM diag_events WHERE code='lesson_unclassified'").fetchall()
        self.assertTrue(warn and warn[0]["severity"] == "warn" and "2" in warn[0]["message"])

    def test_unclassified_never_becomes_a_lesson(self):
        self._mistakes(["không ưng"] * 6)
        with _flags(risk_tags="1"):
            self.assertEqual(lessons.ready_count(self.conn), 0)
            lessons.propose(self.conn)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0], 0)

    def test_off_clusters_as_before(self):
        self._mistakes(["clip này nhìn kỳ kỳ", "mặt biến dạng khi quay đầu"])
        with _flags(risk_tags="0"):
            rows = lessons.clusters(self.conn)
        self.assertEqual({r["tag"] for r in rows}, {"face", "motion"})
        self.assertFalse(self.conn.execute("SELECT 1 FROM diag_events WHERE code='lesson_unclassified'").fetchone())


if __name__ == "__main__":
    unittest.main()
