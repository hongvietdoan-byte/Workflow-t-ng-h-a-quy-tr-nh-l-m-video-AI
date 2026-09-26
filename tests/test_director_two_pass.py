"""GĐ5 (kế hoạch V4): Director hai lượt behind the feature `director_two_pass` — Tầng A Đạo diễn (Bible + intent), Tầng B Quay phim (one
call per scene, shared part cached), code "Đạo diễn duyệt". Offline only (core.llm_runner.MockLlm and scripted fakes) — no paid call."""
import copy
import json
import os
import re
import unittest
from unittest import mock

from core import autopilot, budget, diag, director_two_pass as dtp, llm_io, llm_runner, prompts, shots
from core.llm_io import SchemaError
from tests.test_v3 import kenta_project

ON = {"FEATURE_DIRECTOR_TWO_PASS": "1"}
OFF = {"FEATURE_DIRECTOR_TWO_PASS": "0"}
_DP = re.compile(r"# Việc lần này: Quay phim chia shot Cảnh (\d+)")


class Recorder(llm_runner.MockLlm):
    """The offline model, recording every prompt; `edit(kind, scene, attempt, obj)` may change an answer (to script a bad one)."""

    def __init__(self, edit=None):
        self.prompts, self.edit, self.tries = [], edit, {}

    def complete(self, prompt, images=()):
        self.prompts.append(prompt)
        reply = super().complete(prompt, images)
        if self.edit is None:
            return reply
        text = llm_runner.plain(prompt)
        m = _DP.search(text)
        kind, scene = ("B", int(m.group(1))) if m else ("A" if text.startswith("# Đạo diễn — Tầng A") else "other", None)
        key = (kind, scene)
        self.tries[key] = self.tries.get(key, 0) + 1
        obj = self.edit(kind, scene, self.tries[key], llm_runner.extract_json(reply.text))
        return llm_runner.LlmReply(json.dumps(obj, ensure_ascii=False), reply.input_tokens, reply.output_tokens)

    def kinds(self):
        out = []
        for pr in self.prompts:
            text = llm_runner.plain(pr)
            m = _DP.search(text)
            out.append(f"B{m.group(1)}" if m else ("A" if text.startswith("# Đạo diễn — Tầng A") else "single"))
        return out


def _rows(p, pid):
    return shots.shots_of(p, pid)


def _spoken(p, pid):
    return [(d["speaker"], d["text"]) for r in _rows(p, pid) for d in r["data"].get("dialogue") or []]


class FlagOffTests(unittest.TestCase):
    def test_flag_off_keeps_the_single_call(self):
        with mock.patch.dict(os.environ, OFF):
            self.assertFalse(dtp.enabled(kenta_project()[0].project(1)))
            p, pid = kenta_project()
            client = Recorder()
            llm_runner.run_director(p, pid, client)
        self.assertEqual(client.kinds(), ["single"])
        self.assertGreater(len(_rows(p, pid)), 12)
        self.assertEqual(len(_spoken(p, pid)), 14)
        self.assertIsNone(p.project(pid)["director_intent_raw"])
        self.assertNotIn("review", json.loads(p.project(pid)["director_raw"]))

    def test_the_flag_is_off_by_default_and_says_why(self):
        from core import features
        self.assertFalse(features.FEATURES["director_two_pass"]["verified"])
        self.assertIn("chưa", features.FEATURES["director_two_pass"]["why"])

    def test_a_v2_project_keeps_the_single_call_even_with_the_flag(self):
        with mock.patch.dict(os.environ, ON):
            p, pid = kenta_project(shot_mode=None, style=None)
            client = Recorder()
            llm_runner.run_director(p, pid, client)
        self.assertEqual(client.kinds(), ["single"])


class TwoPassRunTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ, ON)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_one_director_call_plus_one_per_scene_and_the_same_stored_shape(self):
        p, pid = kenta_project()
        client = Recorder()
        r = llm_runner.run_director(p, pid, client)
        self.assertEqual(sorted(client.kinds()), ["A", "B1", "B2", "B3"])
        self.assertEqual(client.kinds()[:2], ["A", "B1"])               # scene 1 alone first: it writes the cache the others read
        self.assertEqual((r["calls"], r["two_pass"], r["characters"], r["scenes"]), (4, True, 3, 3))
        spoken = _spoken(p, pid)
        self.assertEqual(len(spoken), 14)                               # every script line exactly once
        self.assertEqual(len(set(spoken)), 14)
        with mock.patch.dict(os.environ, OFF):                          # the single call on the same script, for the shape
            p1, pid1 = kenta_project()
            llm_runner.run_director(p1, pid1, llm_runner.MockLlm())
        keys = lambda rows: set().union(*(set(r["data"]) for r in rows))  # noqa: E731
        self.assertEqual(keys(_rows(p, pid)), keys(_rows(p1, pid1)))
        self.assertEqual([r["idx"] for r in _rows(p, pid)], list(range(1, len(_rows(p, pid)) + 1)))
        self.assertEqual(set(shots.story_scenes(p, pid)[0]["data"]), set(shots.story_scenes(p1, pid1)[0]["data"]))
        stored = json.loads(p.project(pid)["director_raw"])
        self.assertEqual(set(json.loads(p1.project(pid1)["director_raw"])) - set(stored), set())
        self.assertIn("review", stored)
        self.assertIn("intent", stored["scenes"][0])
        raw = json.loads(p.project(pid)["director_intent_raw"])            # Tầng A's paid answer kept, like director_raw
        self.assertTrue(raw["done"])
        self.assertEqual(sorted(raw["parts"]), ["1", "2", "3"])
        self.assertEqual(len(raw["intent"]["scenes"]), 3)
        self.assertNotIn("shots", raw["intent"]["scenes"][0])
        self.assertEqual(stored["review"]["flagged"], [])

    def test_the_shared_part_is_identical_for_every_scene_and_cached(self):
        p, pid = kenta_project()
        client = Recorder()
        llm_runner.run_director(p, pid, client)
        dp = [pr for pr, k in zip(client.prompts, client.kinds()) if k.startswith("B")]
        heads = {pr.split(prompts.CACHE_BREAK)[0] for pr in dp}
        self.assertEqual(len(heads), 1)                                 # identical bytes: the cache hits
        self.assertTrue(all(pr.count(prompts.CACHE_BREAK) == 1 for pr in dp))
        self.assertIn("# Ý đồ của Đạo diễn cho mọi cảnh (Tầng A)", dp[0])

    def test_only_the_failing_scene_is_asked_again(self):
        def edit(kind, scene, attempt, obj):
            if kind == "B" and scene == 2 and attempt == 1:             # first answer of scene 2 drops a kept line
                for s in obj["shots"]:
                    if s.get("dialogue"):
                        s["dialogue"] = []
                        break
            return obj
        p, pid = kenta_project()
        client = Recorder(edit)
        llm_runner.run_director(p, pid, client)
        self.assertEqual(sorted(client.kinds()), ["A", "B1", "B2", "B2", "B3"])
        retry = [r["message"] for r in p.conn.execute("SELECT message FROM diag_events WHERE code='bad_json_retry'")]
        self.assertTrue(any("Cảnh 2" in m and "thoại" in m for m in retry), retry)
        self.assertEqual(len(_spoken(p, pid)), 14)

    def test_a_scene_that_keeps_failing_stops_the_run_keeps_the_rest_and_resume_asks_only_it(self):
        def bad3(kind, scene, attempt, obj):
            if kind == "B" and scene == 3:
                obj["shots"][1]["dialogue"][0]["text"] = "Câu bịa thêm không có trong kịch bản"
            return obj
        p, pid = kenta_project()
        with self.assertRaises(llm_runner.LlmError) as ctx:
            llm_runner.run_director(p, pid, Recorder(bad3))
        self.assertIn("cảnh 3", str(ctx.exception).lower())
        self.assertEqual(dtp.pending_scenes(p, pid), [3])
        self.assertEqual(_rows(p, pid)[0]["data"].get("shot_no"), None)   # nothing half-stored
        client = Recorder()
        r = llm_runner.run_director(p, pid, client, resume=True)
        self.assertEqual(client.kinds(), ["B3"])                         # Tầng A and scenes 1–2 reused (already paid)
        self.assertEqual((r["calls"], r["reused_scenes"]), (1, [1, 2]))
        self.assertEqual(len(_spoken(p, pid)), 14)
        self.assertEqual(dtp.pending_scenes(p, pid), [])

    def test_resume_does_not_reuse_answers_made_from_another_script(self):
        def bad3(kind, scene, attempt, obj):
            if kind == "B" and scene == 3:
                obj["shots"][1]["dialogue"] = []
            return obj
        p, pid = kenta_project()
        with self.assertRaises(llm_runner.LlmError):
            llm_runner.run_director(p, pid, Recorder(bad3))
        p.conn.execute("UPDATE story_scenes SET text=text || '\n*Gió thổi mạnh.*' WHERE project_id=? AND idx=1", (pid,))
        p.conn.commit()                                                   # the script the Director reads changed
        client = Recorder()
        llm_runner.run_director(p, pid, client, resume=True)
        self.assertEqual(sorted(client.kinds()), ["A", "B1", "B2", "B3"])

    def test_nothing_is_paid_when_the_plan_can_no_longer_be_replaced(self):
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        p.create_job(_rows(p, pid)[0]["id"])
        client = Recorder()
        with self.assertRaises(SchemaError):
            llm_runner.run_director(p, pid, client)
        self.assertEqual(client.prompts, [])

    def test_the_whole_run_is_refused_before_any_call_when_the_claude_money_left_is_too_small(self):
        p, pid = kenta_project()
        budget.save(p.conn, llm_usd=0.01)
        client = Recorder()
        client.ledger, client.model = "ledger.db", "claude-sonnet-5"
        with self.assertRaises(llm_runner.LlmError) as ctx:
            llm_runner.run_director(p, pid, client)
        self.assertEqual(ctx.exception.code, "budget")
        self.assertEqual(client.prompts, [])

    def test_the_director_references_diag_and_the_dp_calls_are_reported(self):
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        codes = {r["code"]: r["message"] for r in p.conn.execute("SELECT code, message FROM diag_events")}
        self.assertIn("Director xem 0 ảnh", codes["director_refs"])
        self.assertIn("không gửi ảnh", codes["dp_calls"])
        self.assertIn("director_review", codes)

    def test_replan_one_scene_asks_only_the_dp_from_the_stored_intent(self):
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        before = [r["id"] for r in _rows(p, pid) if r["data"]["story_scene"] < 3]
        client = Recorder()
        r = llm_runner.run_director_scene(p, pid, 3, client, note="thêm shot giữ ở cú twist")
        self.assertEqual(client.kinds(), ["B3"])
        self.assertIn("Lý do chia lại: thêm shot giữ ở cú twist", client.prompts[0])
        self.assertIn("Kế hoạch hiện tại của cảnh này", client.prompts[0])
        self.assertGreater(r["rows"], 0)
        self.assertEqual([x["id"] for x in _rows(p, pid) if x["data"]["story_scene"] < 3], before)
        self.assertEqual(len(_spoken(p, pid)), 14)

    def test_a_later_single_call_forgets_the_intent(self):
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        with mock.patch.dict(os.environ, OFF):
            llm_runner.run_director(p, pid, llm_runner.MockLlm())
        raw = json.loads(p.project(pid)["director_intent_raw"])
        self.assertTrue(raw["stale"])
        self.assertIsNotNone(raw["previous_intent"])
        client = Recorder()
        llm_runner.run_director_scene(p, pid, 2, client)                # flag on again: no stored intent → the single-call re-plan
        self.assertEqual(client.kinds(), ["single"])


class SafeguardTests(unittest.TestCase):
    """CHUAN luật 2: the two passes keep every safeguard of the single call."""

    def setUp(self):
        patcher = mock.patch.dict(os.environ, ON)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.p, self.pid = kenta_project()
        self.intent = llm_runner._mock_intent(llm_runner.plain(prompts.build_intent_bundle(self.p, self.pid)))

    def check(self, obj):
        return dtp.validate_intent(self.p, self.pid)(copy.deepcopy(obj))

    def test_the_mock_intent_is_valid(self):
        obj = self.check(self.intent)
        self.assertEqual([s["idx"] for s in obj["scenes"]], [1, 2, 3])

    def test_tier_a_lines_must_be_the_script_words_in_order_by_their_speaker(self):
        bad = copy.deepcopy(self.intent)
        bad["scenes"][0]["dialogue"][0]["text"] = "Một câu mới hay hơn"
        with self.assertRaisesRegex(SchemaError, "nguyên văn"):
            self.check(bad)
        swapped = copy.deepcopy(self.intent)
        d = swapped["scenes"][0]["dialogue"]
        d[0], d[1] = d[1], d[0]
        with self.assertRaisesRegex(SchemaError, "thứ tự"):
            self.check(swapped)
        who = copy.deepcopy(self.intent)
        who["scenes"][0]["dialogue"][0]["speaker"] = "KENTA"
        with self.assertRaisesRegex(SchemaError, "không phải KENTA"):
            self.check(who)

    def test_dropping_a_line_needs_the_trim_permission(self):
        cut = copy.deepcopy(self.intent)
        del cut["scenes"][1]["dialogue"][1]
        with self.assertRaisesRegex(SchemaError, "thiếu câu thoại"):
            self.check(cut)
        self.p.set_project_field(self.pid, "dialogue_trim", 1)
        self.assertEqual(len(self.check(cut)["scenes"][1]["dialogue"]), len(self.intent["scenes"][1]["dialogue"]) - 1)
        self.assertIn("dropped_lines", prompts.build_intent_bundle(self.p, self.pid))
        self.assertNotIn("Được phép bỏ bớt câu thoại",
                         prompts.dp_common(self.p, self.pid, self.intent))        # the DP never drops a line

    def test_tier_a_needs_intent_seconds_every_scene_and_a_known_focus(self):
        for key, value, words in (("emotional_intent", "", "emotional_intent"), ("target_s", None, "target_s"),
                                  ("focus", "AI ĐÓ", "focus"), ("peak", 9, "peak")):
            bad = copy.deepcopy(self.intent)
            bad["scenes"][0][key] = value
            with self.assertRaisesRegex(SchemaError, words):
                self.check(bad)
        missing = copy.deepcopy(self.intent)
        missing["scenes"].pop()
        with self.assertRaisesRegex(SchemaError, "thiếu"):
            self.check(missing)
        stray = copy.deepcopy(self.intent)
        stray["scenes"][0]["characters"] = ["NGƯỜI LẠ"]
        with self.assertRaises(SchemaError):                              # the single call's cast check, reused
            self.check(stray)

    def test_tier_b_lines_must_be_exactly_the_kept_lines_and_enums_are_normalised(self):
        sc = self.check(self.intent)["scenes"][0]
        names = {c["name"] for c in self.intent["characters"]}
        answer = llm_runner._mock_dp_scene("# Việc lần này: Quay phim chia shot Cảnh 1 (cảnh ĐẦU phim)\n# Ý đồ cảnh này\n```json\n"
                                           + json.dumps(sc, ensure_ascii=False) + "\n```")
        answer["shots"][1]["angle"] = "over_shoulder"
        part = dtp.check_scene(sc, names)(copy.deepcopy(answer))
        self.assertEqual(part["shots"][1]["angle"], "ots")
        self.assertTrue(any("ots" in c for c in part["normalized"]))
        extra = copy.deepcopy(answer)
        extra["shots"][0]["dialogue"] = [{"speaker": "KELLY", "text": "Maxim! Có địch bên kia! Ông xử lý đi!"}]
        with self.assertRaisesRegex(SchemaError, "đúng .* câu Đạo diễn giữ"):
            dtp.check_scene(sc, names)(extra)
        stranger = copy.deepcopy(answer)
        stranger["shots"][0]["characters"] = ["NGƯỜI LẠ"]
        with self.assertRaises(SchemaError):
            dtp.check_scene(sc, names)(stranger)
        other = dict(copy.deepcopy(answer), idx=2)
        with self.assertRaisesRegex(SchemaError, "idx"):
            dtp.check_scene(sc, names)(other)

    def test_a_locked_character_and_a_hand_edited_shot_field_survive_the_two_passes(self):
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        self.p.conn.execute("UPDATE characters SET description='mô tả người dùng khóa', locked=1 WHERE project_id=? AND name='KELLY'",
                            (self.pid,))
        self.p.conn.commit()
        first = _rows(self.p, self.pid)[0]
        llm_io.update_scene(self.p, self.pid, first["idx"], {"mood": "mood sửa tay"})
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        desc = self.p.conn.execute("SELECT description FROM characters WHERE project_id=? AND name='KELLY'", (self.pid,)).fetchone()[0]
        self.assertEqual(desc, "mô tả người dùng khóa")
        self.assertEqual(_rows(self.p, self.pid)[0]["data"]["mood"], "mood sửa tay")

    def test_the_prompts_split_the_knowledge_by_role_and_keep_the_protecting_blocks(self):
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())       # a stored Bible now exists
        a = prompts.build_intent_bundle(self.p, self.pid)
        self.assertTrue(a.startswith("# Đạo diễn — Tầng A"))
        self.assertNotIn("# Phân shot (dự án chia shot", a)                   # prompt 17 = the DP's
        self.assertNotIn("Vai Quay phim (DP)", a)
        self.assertIn("# Character Bible hiện có", a)                         # exact names, locked / hand-edited kept
        self.assertIn("# Khung thời lượng và quyết định thoại (Tầng A)", a)
        self.assertIn("45–55 giây", a)
        common = prompts.dp_common(self.p, self.pid, self.intent)
        self.assertIn("# Phân shot (dự án chia shot", common)
        self.assertIn("# Character Bible (Đạo diễn vừa chốt ở Tầng A", common)
        self.assertIn("Shot có thoại: `duration_s` ≥", common)               # the camera side of the duration block
        self.assertNotIn("Tổng `duration_s` của MỌI shot", common)
        with mock.patch.dict(os.environ, {"FEATURE_FILM_CREW": "1", "FEATURE_LIP_SYNC": "1"}):
            a = prompts.build_intent_bundle(self.p, self.pid)
            common = prompts.dp_common(self.p, self.pid, self.intent)
        self.assertIn("Vai Đạo diễn — bộ kỹ năng nghề", a)
        self.assertNotIn("Vai Quay phim (DP)", a)
        self.assertIn("Vai Quay phim (DP)", common)
        self.assertIn("Khớp môi đang BẬT", common)                            # lip sync block reaches the DP

    def test_standard_profiles_reach_both_passes(self):
        with mock.patch.object(prompts.assets, "standard_for",
                               lambda conn, pid, name: {"asset": "Kho " + name, "identity": "chuẩn", "must_keep": "áo xanh"}):
            self.p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, 'KELLY', 'x')", (self.pid,))
            self.p.conn.commit()
            self.assertIn("# Hồ sơ chuẩn nhân vật", prompts.build_intent_bundle(self.p, self.pid))
            self.assertIn("**KENTA** (Kho KENTA)", prompts.dp_common(self.p, self.pid, self.intent))

    def test_delivery_and_tradeoffs_are_carried_and_the_report_reads_the_plan(self):
        from core import director_report

        def edit(kind, scene, attempt, obj):
            if kind == "A":
                obj["scenes"][0]["dialogue"][0]["delivery"] = {"emotion": "urgent", "intensity": 4, "pace": "fast"}
                obj["tradeoffs"] = [{"chose": "giữ thoại", "gave_up": "thời lượng", "why": "ưu tiên 2 > 4", "scene": 2}]
            if kind == "B" and scene == 1:
                obj["tradeoffs"] = [{"chose": "qua vai", "gave_up": "cận", "why": "khớp môi tắt"}]
            return obj
        llm_runner.run_director(self.p, self.pid, Recorder(edit))
        first_line = next(d for r in _rows(self.p, self.pid) for d in r["data"].get("dialogue") or [])
        self.assertEqual(first_line["delivery"]["emotion"], "urgent")
        stored = json.loads(self.p.project(self.pid)["director_raw"])
        self.assertEqual({t.get("scene") for t in stored["tradeoffs"]}, {1, 2})
        rep = director_report.report(stored, self.p.project(self.pid)["script_text"])
        self.assertEqual(rep["invented"], [])
        self.assertEqual(len(rep["tradeoffs"]), 2)

    def test_the_review_flags_a_scene_that_misses_its_intent(self):
        def edit(kind, scene, attempt, obj):
            if kind == "A":
                obj["scenes"][1]["focus"] = "MAXIM"
                obj["scenes"][1]["peak"] = 5
            if kind == "B" and scene == 2:
                for s in obj["shots"]:
                    s["characters"] = [c for c in s.get("characters") or [] if c != "MAXIM"]
                    s["duration_s"] = min(float(s["duration_s"]), 1.9) if not s.get("dialogue") else s["duration_s"]
            return obj
        r = llm_runner.run_director(self.p, self.pid, Recorder(edit))
        self.assertEqual(r["flagged"], [2])
        rv = json.loads(self.p.project(self.pid)["director_raw"])["review"]
        flags = next(x for x in rv["scenes"] if x["idx"] == 2)["flags"]
        self.assertTrue(any("trọng tâm MAXIM" in f for f in flags), flags)
        self.assertIn("⚠", " ".join(dtp.review_text(rv)))


class EstimateTests(unittest.TestCase):
    def test_both_ways_are_estimated_from_the_real_prompts_and_the_price_table(self):
        with mock.patch.dict(os.environ, ON):
            p, pid = kenta_project()
            est = dtp.estimate(p, pid, model="claude-sonnet-5")
        self.assertEqual(est["active"], "two_pass")
        self.assertEqual((est["single"]["calls"], est["two_pass"]["calls"]), (1, 4))
        self.assertGreater(est["single"]["input"], 5000)
        self.assertGreater(est["two_pass"]["cache_read"], 0)
        self.assertIsNotNone(est["single"]["usd"])
        self.assertIsNotNone(est["two_pass"]["usd"])
        text = dtp.estimate_text(est)
        self.assertIn("USD", text)
        self.assertNotIn("$", text)                                       # Streamlit reads "$" as math
        self.assertIn("4 lượt", text)
        unknown = dtp.estimate(p, pid, model="claude-nobody-1")
        self.assertIsNone(unknown["single"]["usd"])
        self.assertIn("chưa có giá", dtp.estimate_text(unknown))

    def test_a_v2_project_has_only_the_single_estimate(self):
        p, pid = kenta_project(shot_mode=None, style=None)
        est = dtp.estimate(p, pid, model="claude-sonnet-5")
        self.assertIsNone(est["two_pass"])
        self.assertEqual(est["active"], "single")


class AutopilotTests(unittest.TestCase):
    def test_the_director_phase_uses_the_two_passes_when_the_flag_is_on(self):
        with mock.patch.dict(os.environ, ON):
            p, pid = kenta_project()
            client = Recorder()
            ctx = autopilot.Context(data_dir="", image_runner=None, video_runner=None, llm=client)
            try:
                autopilot._director_phase(p, pid, ctx)
            except (autopilot._Wait, autopilot._Stop):
                pass                                                      # the Bible gate waits for the person — expected
        kinds = [k for k in client.kinds() if k != "other"]
        self.assertEqual(sorted(k for k in kinds if k != "single"), ["A", "B1", "B2", "B3"])
        self.assertNotIn("single", kinds)
        self.assertTrue(json.loads(p.project(pid)["director_intent_raw"])["done"])
        log = p.project(pid)["autopilot_log"] or ""
        self.assertIn("hai lượt", log)

    def test_the_director_phase_resumes_after_a_failed_scene(self):
        def bad2(kind, scene, attempt, obj):
            if kind == "B" and scene == 2:
                obj["shots"][1]["dialogue"] = []
            return obj
        with mock.patch.dict(os.environ, ON):
            p, pid = kenta_project()
            with self.assertRaises(llm_runner.LlmError):
                autopilot._director_phase(p, pid, autopilot.Context(data_dir="", image_runner=None, video_runner=None, llm=Recorder(bad2)))
            client = Recorder()
            try:
                autopilot._director_phase(p, pid, autopilot.Context(data_dir="", image_runner=None, video_runner=None, llm=client))
            except (autopilot._Wait, autopilot._Stop):
                pass
        self.assertEqual([k for k in client.kinds() if k in ("A", "B1", "B2", "B3")], ["B2"])


class LedgerTests(unittest.TestCase):
    """Luật chi phí: every call of both passes goes through the Claude API client with its ledger — budget checked before each call,
    tokens recorded with stage 'director' + the project (also from the Tầng B threads), the shared Tầng B part sent as a cached block."""

    def test_every_call_is_checked_recorded_and_tagged_and_the_dp_part_is_cached(self):
        import tempfile
        from core.adapters.http import HttpResponse
        from core.db import connect
        from core.pipeline import Pipeline
        from core import script_parser
        from tests.test_v3 import SAMPLE
        db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        p = Pipeline(connect(db))
        pid = p.create_project("kenta", aspect="9:16", genre="SHORT_FORM", model_priority="balanced")
        p.set_project_field(pid, "shot_mode", "per_shot")
        with open(SAMPLE, encoding="utf-8") as f:
            text = f.read()
        script_parser.import_scenes(p, pid, script_parser.split_scenes([ln for ln in text.splitlines() if ln.strip()]), full_text=text)
        bodies = []

        def send(method, url, headers, body, timeout):
            payload = json.loads(body)
            bodies.append(payload)
            blocks = payload["messages"][0]["content"]
            prompt = "\n\n---\n\n".join(b["text"] for b in blocks if b["type"] == "text")
            answer = llm_runner.MockLlm().complete(prompt).text
            return HttpResponse(200, json.dumps({"content": [{"type": "text", "text": answer}], "stop_reason": "end_turn",
                                                 "usage": {"input_tokens": 1000, "output_tokens": 200}}).encode())
        client = llm_runner.AnthropicClient("sk-test", "claude-sonnet-5", transport=send, sleep=lambda s: None, ledger=db)
        checks = []
        real = client._check_budget
        with mock.patch.dict(os.environ, ON), mock.patch.object(client, "_check_budget", lambda: (checks.append(1), real())[1]):
            llm_runner.run_director(p, pid, client)
        self.assertEqual((len(bodies), len(checks)), (4, 4))
        rows = p.conn.execute("SELECT DISTINCT stage, project_id FROM usage_events WHERE kind='llm'").fetchall()
        self.assertEqual([(r["stage"], r["project_id"]) for r in rows], [("director", pid)])
        dp = [b for b in bodies if "Quay phim chia shot Cảnh" in b["messages"][0]["content"][-1]["text"]]
        self.assertEqual(len(dp), 3)
        self.assertTrue(all(b["messages"][0]["content"][0].get("cache_control") for b in dp))
        self.assertEqual(len({b["messages"][0]["content"][0]["text"] for b in dp}), 1)


class DashboardTests(unittest.TestCase):
    """Bước 1: the estimate before the button (both ways), the two-pass run from the button, the review panel."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()
        env = {"DASHBOARD_EXPERT": "1", "PIPELINE_DB": os.path.join(self.tmp, "m.sqlite"),
               "PIPELINE_DATA": os.path.join(self.tmp, "projects"), "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "knowledge_user"),
               "LLM_PROVIDER": "mock", **ON}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.db = env["PIPELINE_DB"]

    def test_the_button_shows_the_estimate_runs_two_passes_and_shows_the_review(self):
        from streamlit.testing.v1 import AppTest
        from core import script_parser
        from core.db import connect
        from core.pipeline import Pipeline
        from tests.test_v3 import SAMPLE
        p = Pipeline(connect(self.db))
        pid = p.create_project("kenta", aspect="9:16", genre="SHORT_FORM", model_priority="balanced")
        p.set_project_field(pid, "shot_mode", "per_shot")
        with open(SAMPLE, encoding="utf-8") as f:
            text = f.read()
        script_parser.import_scenes(p, pid, script_parser.split_scenes([ln for ln in text.splitlines() if ln.strip()]), full_text=text)
        app = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
        at = AppTest.from_file(app, default_timeout=60).run()
        self.assertFalse(at.exception)
        captions = " ".join(c.value for c in at.caption)
        self.assertIn("Ước tính Director hai lượt", captions)
        self.assertIn("một lượt như cũ", captions)
        self.assertNotIn("Chưa ước tính được", captions)
        next(b for b in at.button if b.key == f"llm_dir_{pid}").click().run()
        self.assertFalse(at.exception)
        self.assertFalse(at.error)
        q = Pipeline(connect(self.db))
        self.assertTrue(json.loads(q.project(pid)["director_intent_raw"])["done"])
        self.assertGreater(len(shots.shots_of(q, pid)), 12)
        at = AppTest.from_file(app, default_timeout=60).run()
        self.assertFalse(at.exception)
        self.assertTrue(any("Đạo diễn duyệt" in e.label for e in at.expander))


if __name__ == "__main__":
    unittest.main()
