"""Lỗi 6 (#27 tổng kết 13/10, cờ end_state_fresh): end_state sửa sau khi dịch → motion_en.end_state là bản dịch CŨ. Cờ bật: bản cũ
không gửi im lặng (prompt code viết để CHỜ DUYỆT, nói rõ) và lần bấm 'Viết motion prompt' kế tiếp dịch lại (Claude giả, qua sổ chi).
Cờ tắt: như cũ."""
import json
import os
import re
import tempfile
import unittest
from unittest import mock

from core import claude_tasks, llm_runner, seedance_refs, shots
from tests.test_v3 import _approve_all_images, kenta_project


def _data(p, sid):
    return json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"] or "{}")


def _put(p, sid, d):
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), sid))
    p.conn.commit()


class StaleKeysTests(unittest.TestCase):
    BASE = {"action": "Kelly quay người", "end_state": "Kelly quỳ xuống",
            "motion_en": {"action": "Kelly turns", "end_state": "Kelly kneels"}}

    def _with_src(self, d):
        d = json.loads(json.dumps(d))
        d["motion_en_src"] = claude_tasks._src_key(claude_tasks._translate_item(d))
        return d

    def test_fresh_translation_is_used(self):
        d = self._with_src(self.BASE)
        self.assertEqual(claude_tasks.stale_en_keys(d), [])
        with mock.patch.dict(os.environ, {"FEATURE_END_STATE_FRESH": "1"}):
            self.assertEqual(seedance_refs._en(d, "end_state"), "Kelly kneels")

    def test_edited_end_state_is_stale_and_not_sent(self):
        d = self._with_src(self.BASE)
        d["end_state"] = "Kelly ngồi bên giếng"
        self.assertIn("end_state", claude_tasks.stale_en_keys(d))
        with mock.patch.dict(os.environ, {"FEATURE_END_STATE_FRESH": "1"}):
            self.assertEqual(seedance_refs._en(d, "end_state"), "Kelly ngồi bên giếng")     # Vietnamese → untranslated() holds
            self.assertIn("end_state", seedance_refs.untranslated(d))
        with mock.patch.dict(os.environ, {"FEATURE_END_STATE_FRESH": "0"}):
            self.assertEqual(seedance_refs._en(d, "end_state"), "Kelly kneels")             # flag off: as before

    def test_end_state_rewritten_in_english_is_used_as_written(self):
        d = self._with_src(self.BASE)
        d["end_state"] = "Kelly sits by the well"
        with mock.patch.dict(os.environ, {"FEATURE_END_STATE_FRESH": "1"}):
            self.assertEqual(seedance_refs._en(d, "end_state"), "Kelly sits by the well")

    def test_per_field_record_keeps_the_untouched_field(self):
        d = json.loads(json.dumps(self.BASE))
        d["motion_en_src_fields"] = {"action": claude_tasks._src_key(d["action"]), "end_state": claude_tasks._src_key(d["end_state"])}
        d["end_state"] = "Kelly ngồi bên giếng"
        self.assertEqual(claude_tasks.stale_en_keys(d), ["end_state"])                     # action's translation still holds

    def test_no_record_or_emptied_field_is_trusted_as_before(self):
        self.assertEqual(claude_tasks.stale_en_keys(dict(self.BASE)), [])                  # no motion_en_src: nothing to judge by
        d = self._with_src(self.BASE)
        d.pop("end_state")
        d["motion_en_src"] = claude_tasks._src_key(claude_tasks._translate_item(d))
        self.assertEqual(claude_tasks.stale_en_keys(d), [])


class WriteByCodeTests(unittest.TestCase):
    """The real Step 3 path: write_by_code → translate_motion_fields (fake Claude) → code_motion → store / approve."""

    def setUp(self):
        env = mock.patch.dict(os.environ, {"FEATURE_SEEDANCE_REF_GROUPS": "1", "FEATURE_END_STATE_FRESH": "1"})
        env.start()
        self.addCleanup(env.stop)
        self.p, self.pid = kenta_project(shot_mode="per_shot")
        self.dir = tempfile.mkdtemp()
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        _approve_all_images(self.p, self.pid, self.dir)
        self.sid = next(r["id"] for r in shots.shots_of(self.p, self.pid) if seedance_refs.eligible(r["data"]))
        self.idx = self.p.conn.execute("SELECT idx FROM scenes WHERE id=?", (self.sid,)).fetchone()["idx"]
        self.p.conn.execute("DELETE FROM motion_prompts")
        self.p.conn.commit()

    def client(self, end_en):
        calls = []
        idx = str(self.idx)

        class C:
            name = "fake"

            def complete(self, prompt, images=()):
                calls.append(llm_runner.current_tag())
                fields = json.loads(re.search(r"```json\n(.*)\n```", prompt, re.S).group(1))
                out = {}
                for k, item in fields.items():
                    out[k] = {f: ({x: "calm" for x in v} if isinstance(v, dict) else "the person moves") for f, v in item.items()}
                    if k == idx and "end_state" in item:
                        out[k]["end_state"] = end_en
                return llm_runner.LlmReply(json.dumps(out), 10, 5)
        return C(), calls

    def prompt(self):
        return self.p.conn.execute("SELECT motion_prompt, state FROM motion_prompts WHERE scene_id=?", (self.sid,)).fetchone()

    def test_edited_end_state_is_translated_again_or_held(self):
        d = _data(self.p, self.sid)
        d["end_state"] = "Kelly quỳ xuống"
        _put(self.p, self.sid, d)
        c, calls = self.client("Kelly kneels on one knee")
        seedance_refs.write_by_code(self.p, self.pid, c)
        self.assertTrue(calls and calls[0][0] == "translate")                    # through the spend book (tagged stage)
        self.assertIn("Kelly kneels on one knee", self.prompt()["motion_prompt"])
        # the person edits end_state; Claude is down → the old English is NOT sent: held, said
        d = _data(self.p, self.sid)
        d["end_state"] = "Kelly ngồi xuống bên giếng"
        _put(self.p, self.sid, d)

        class Down:
            name = "down"

            def complete(self, prompt, images=()):
                raise llm_runner.LlmError("Claude không trả lời")
        res = seedance_refs.write_by_code(self.p, self.pid, Down())
        mp = self.prompt()
        self.assertNotIn("Kelly kneels on one knee", mp["motion_prompt"])
        self.assertEqual(mp["state"], "pending")
        held = next(h for h in res["held"] if h["scene_id"] == self.sid)
        self.assertIn("bản dịch cũ của end_state", held["why"])
        # Claude back → translated again, the new end state sent
        c, calls = self.client("Kelly sits down by the well")
        seedance_refs.write_by_code(self.p, self.pid, c)
        self.assertEqual(len(calls), 1)
        self.assertIn("Kelly sits down by the well", self.prompt()["motion_prompt"])
        self.assertNotIn("kneels", self.prompt()["motion_prompt"])

    def test_end_state_rewritten_in_english_replaces_the_old_translation(self):
        d = _data(self.p, self.sid)
        d["end_state"] = "Kelly quỳ xuống"
        _put(self.p, self.sid, d)
        c, _ = self.client("Kelly kneels on one knee")
        seedance_refs.write_by_code(self.p, self.pid, c)
        d = _data(self.p, self.sid)
        d["end_state"] = "Kelly sits by the well, back to the camera"
        _put(self.p, self.sid, d)
        c, _ = self.client("unused")
        seedance_refs.write_by_code(self.p, self.pid, c)
        text = self.prompt()["motion_prompt"]
        self.assertIn("Kelly sits by the well", text)
        self.assertNotIn("kneels", text)


if __name__ == "__main__":
    unittest.main()
