"""Tổ QC GĐ2 (docs/THIET_KE_TO_QC_2026-10-01.md): bộ dịch đặc tả, tầng 0, bảng luật, C1 có cấu trúc, ghi / chạy lại, bộ đo vàng."""
import json
import os
import tempfile
import unittest

from core import llm_runner, qc_golden, qc_measure, qc_rules, qc_spec, qc_team

KENTA = {"must_keep": "black high ponytail, glowing star emblem on the LEFT shoulder, RIGHT arm: black sleeve, white-grey bandage, "
                      "black fingerless glove; LEFT arm: brown leather armband, forearm in a black armored gauntlet, blue scarf",
         "forbidden": "the old purple armor, a gauntlet on the right arm"}
MAXIM = {"must_keep": "silver-white hair, black baseball cap worn backwards, bomber jacket with a red detail on the left sleeve",
         "forbidden": "removing the cap or turning it forward"}


def shot(**kw):
    d = {"characters": ["KENTA", "MAXIM"], "size": "MS", "angle": "eye", "time": "day", "weather": "clear",
         "blocking": "medium shot, Maxim frame-left looking off toward frame-left, Kenta frame-right standing still",
         "dialogue": [{"speaker": "MAXIM", "text": "Ông làm cô ấy khóc rồi."}], "story_scene": 3, "shot_no": 4}
    d.update(kw)
    return d


class SpecTests(unittest.TestCase):
    def compile(self, data):
        return qc_spec.compile_frame(None, 8, 341, data, profiles={"KENTA": KENTA, "MAXIM": MAXIM})

    def test_asymmetric_details_keep_their_side(self):
        got = qc_spec.asym_details(KENTA["must_keep"])
        self.assertIn(("LEFT", "glowing star emblem on the LEFT shoulder"), got)
        self.assertIn(("RIGHT", "RIGHT arm: black fingerless glove"), got)
        self.assertIn(("LEFT", "LEFT arm: forearm in a black armored gauntlet"), got)
        self.assertFalse(any("scarf" in d for _, d in got))

    def test_headwear_question_follows_the_view(self):
        front = [a for a in self.compile(shot())["assertions"] if a["type"] == "headwear"][0]
        behind = [a for a in self.compile(shot(blocking="over Maxim's shoulder, Kenta frame-right"))["assertions"]
                  if a["type"] == "headwear"][0]
        self.assertIn("trán", front["claim_vi"])
        self.assertIn("lưỡi trai che gáy", behind["claim_vi"])
        self.assertEqual(behind["view"], "behind")

    def test_gaze_is_a_block_only_with_a_line_and_ids_are_stable(self):
        a1 = [a for a in self.compile(shot())["assertions"] if a["type"] == "gaze"]
        a2 = [a for a in self.compile(shot(dialogue=[]))["assertions"] if a["type"] == "gaze"]
        self.assertEqual(a1[0]["severity_if_false"], "block")
        self.assertEqual(a2[0]["severity_if_false"], "minor")
        self.assertEqual([a["id"] for a in self.compile(shot())["assertions"]], [a["id"] for a in self.compile(shot())["assertions"]])

    def test_priority_order_and_plan_conflicts(self):
        r = self.compile(shot())
        self.assertEqual([a["priority"] for a in r["assertions"]], sorted(a["priority"] for a in r["assertions"]))
        self.assertIn("góc qua vai (OTS) mà bảng shot chỉ có 1 người", qc_spec.plan_conflicts({"angle": "ots", "characters": ["KELLY"]}))

    def test_off_frame_names_are_not_conflicts(self):
        ok = {"characters": ["MAXIM"], "angle": "eye", "blocking": "MAXIM centered frame, looking toward KENTA off-frame left"}
        self.assertEqual(qc_spec.plan_conflicts(ok), [])
        bad = {"characters": ["MAXIM"], "angle": "eye", "blocking": "MAXIM centered, KELLY visible frame-right background"}
        self.assertEqual(qc_spec.plan_conflicts(bad), ["blocking đặt KELLY trong khung nhưng `characters` không có"])
        self.assertEqual(qc_measure._target_side("KENTA off-frame left", ["MAXIM"], {}), "left")

    def test_a_person_without_an_approved_profile_is_said(self):
        r = qc_spec.compile_frame(None, 8, 1, shot(characters=["ORION"]), profiles={})
        self.assertEqual(r["missing_profiles"], ["ORION"])


class RulesTests(unittest.TestCase):
    def A(self, type_="asym", sev="block", how="code+model", view="camera"):
        return {"id": f"x#{type_}", "type": type_, "severity_if_false": sev, "how": how, "view": view, "subject": "K", "claim_vi": "c"}

    def test_a_confident_false_on_a_block_assertion_blocks_and_asks_the_arbiter(self):
        a = self.A()
        v = qc_rules.frame_verdict([a], {a["id"]: {"answer": "false", "confidence": "high", "note_vi": "găng sai bên", "fix_en": "x"}}, {})
        self.assertEqual(v["verdict"], "block")
        self.assertTrue(v["arbiter"])

    def test_unclear_or_low_confidence_is_a_doubt_not_a_block(self):
        a = self.A()
        for ans in ({"answer": "unclear", "confidence": "high"}, {"answer": "false", "confidence": "low"}, None):
            v = qc_rules.frame_verdict([a], {a["id"]: ans} if ans else {}, {})
            self.assertEqual(v["verdict"], "doubt", ans)

    def test_code_and_model_disagreeing_goes_to_the_arbiter(self):
        a = self.A(type_="gaze")
        v = qc_rules.frame_verdict([a], {a["id"]: {"answer": "true", "confidence": "high"}}, {a["id"]: {"status": "certain_fail"}})
        self.assertEqual(v["verdict"], "doubt")
        self.assertIn("code ≠ chuyên viên", " ".join(v["arbiter"]))

    def test_a_pass_seen_from_behind_on_a_risky_detail_is_still_rechecked(self):
        a = self.A(view="behind")
        v = qc_rules.frame_verdict([a], {a["id"]: {"answer": "true", "confidence": "high"}}, {})
        self.assertEqual(v["verdict"], "pass")
        self.assertTrue(v["arbiter"])

    def side(self, expected="LEFT", **kw):
        return dict({"id": "x#asym", "type": "asym", "severity_if_false": "block", "how": "code+model", "view": None, "subject": "KENTA",
                     "claim_vi": "c", "expected": expected, "observe": "side", "cast_n": 2, "close": False}, **kw)

    def test_the_code_turns_what_was_seen_into_the_side(self):
        # GĐ3 #8 job 337: Kenta facing the camera, gauntlet (own LEFT) on the image right — the model had called it wrong
        self.assertEqual(qc_rules.own_side("front", "image_right_of_body"), "LEFT")
        self.assertEqual(qc_rules.own_side("back", "image_right_of_body"), "RIGHT")
        self.assertEqual(qc_rules.own_side("profile_facing_image_right", "near_side"), "RIGHT")
        self.assertEqual(qc_rules.own_side("profile_facing_image_left", "far_side"), "RIGHT")
        self.assertIsNone(qc_rules.own_side("front", "near_side"))
        self.assertIsNone(qc_rules.own_side("back", "not_visible"))

    def test_the_models_own_conclusion_is_ignored(self):
        a = self.side()
        seen = {"answer": "false", "confidence": "high", "facing": "front", "seen_at": "image_right_of_body"}
        r = qc_rules.frame_verdict([a], {a["id"]: seen}, {})
        self.assertEqual(r["verdict"], "pass")                    # the model said false; what it saw says LEFT = right
        self.assertIn("bên LEFT", r["results"][a["id"]]["why"])
        seen = dict(seen, answer="true", seen_at="image_left_of_body")
        self.assertEqual(qc_rules.frame_verdict([a], {a["id"]: seen}, {})["verdict"], "block")

    def test_a_facing_the_face_detector_contradicts_is_a_doubt(self):
        a = self.side(cast_n=1)
        seen = {"answer": "true", "confidence": "high", "facing": "back", "seen_at": "image_left_of_body"}
        r = qc_rules.frame_verdict([a], {a["id"]: seen}, {"_faces": {"count": 1}})
        self.assertEqual(r["verdict"], "doubt")

    def test_cap_from_what_is_at_the_nape(self):
        a = {"id": "x#headwear", "type": "headwear", "severity_if_false": "block", "how": "model", "view": "behind", "subject": "MAXIM",
             "claim_vi": "c", "expected": True, "observe": "cap"}
        # GĐ3 #8 job 330: "buckle at the nape, no brim" was judged "worn backwards" — it is a cap worn forward
        seen = {"answer": "true", "confidence": "high", "cap_marks": "strap_or_buckle_at_nape"}
        self.assertEqual(qc_rules.frame_verdict([a], {a["id"]: seen}, {})["verdict"], "block")
        seen = dict(seen, cap_marks="brim_at_nape")
        r = qc_rules.frame_verdict([a], {a["id"]: seen}, {})
        self.assertEqual(r["verdict"], "pass")

    def test_an_extra_person_only_partly_seen_is_minor(self):
        a = {"id": "x#count", "type": "count", "severity_if_false": "block", "how": "code+model", "view": None, "subject": "KELLY",
             "claim_vi": "c", "expected": 1, "observe": "count"}
        seen = {"answer": "false", "confidence": "high", "extra_people": "partial_or_background"}
        r = qc_rules.frame_verdict([a], {a["id"]: seen}, {})
        self.assertEqual((r["verdict"], r["fails"][0]["severity"]), ("minor", "minor"))
        self.assertEqual(qc_rules.frame_verdict([a], {a["id"]: dict(seen, extra_people="clear")}, {})["verdict"], "block")

    def test_a_certain_code_result_counts_without_a_model_answer(self):
        a = self.A(type_="gaze")                                   # #8 job 325: a C2 assertion while only C1 runs
        v = qc_rules.frame_verdict([a], {}, {a["id"]: {"status": "certain_fail", "note": "mắt nhìn về right khung, cần left"}})
        self.assertEqual(v["verdict"], "block")

    def test_minor_only(self):
        a = self.A(sev="minor")
        self.assertEqual(qc_rules.frame_verdict([a], {a["id"]: {"answer": "false", "confidence": "high"}}, {})["verdict"], "minor")


class GoldenTests(unittest.TestCase):
    def test_a_doubt_is_not_a_catch(self):
        items = [{"job": 1, "label": "chặn", "categories": ["Nhân vật"]}, {"job": 2, "label": "chặn", "categories": ["Nhân vật"]},
                 {"job": 3, "label": "đạt", "categories": []}, {"job": 4, "label": "chặn", "categories": ["Hướng nhìn / diễn xuất"]}]
        s = qc_golden.score(items, {1: {"verdict": "block"}, 2: {"verdict": "doubt"}, 3: {"verdict": "block"}, 4: {"verdict": "pass"}},
                            "Nhân vật")
        self.assertEqual((s["blocks"], s["caught"], s["blocks_as_doubt"], s["false_block"]), (2, 1, 1, 1))
        self.assertEqual(s["recall"], 0.5)

    def test_dev_set_reads_the_corrected_labels(self):
        dev = {i["job"]: i for i in qc_golden.dev_set()}
        self.assertEqual(dev[319]["label"], "đạt")                  # labels_v2: Kenta from behind was right
        self.assertEqual(dev[324]["label"], "chặn")                 # Maxim's cap forward
        self.assertIn("Nhân vật", dev[324]["categories"])

    def test_independent_rows_without_a_label_are_left_out(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "independent.json")
        json.dump([{"id": "P13-J481", "label": "Chặn", "category": "Nhân vật"}, {"id": "P1-J2", "label": ""}], open(path, "w"))
        self.assertEqual(qc_golden.independent_set(path), [{"job": 481, "project": 13, "shot": None, "label": "chặn",
                                                           "categories": ["Nhân vật"], "note": ""}])


class FakeClient:
    """Answers every asked assertion 'true' except the ones in `false_types` (by type). Observation assertions get the observation
    that makes the code decide true / false (`spec`: the frame's assertions, to know the expected side — the request does not say it)."""

    def __init__(self, false_types=(), spec=None):
        self.false_types, self.calls = set(false_types), []
        self.spec = {a["id"]: a for a in spec or []}

    def observe(self, aid, ok):
        a = self.spec.get(aid) or {}
        out = {"facing": "na", "seen_at": "na", "cap_marks": "na", "extra_people": "na"}
        if a.get("observe") == "side":
            right_of_image = (a["expected"] == "LEFT") == ok                 # facing the camera: own LEFT is on the image right
            out.update(facing="front", seen_at="image_right_of_body" if right_of_image else "image_left_of_body")
        elif a.get("observe") == "cap":
            out["cap_marks"] = "strap_or_buckle_at_forehead" if ok else "strap_or_buckle_at_nape"
        elif a.get("observe") == "count":
            out["extra_people"] = "none" if ok else "clear"
        return out

    def ask_json(self, messages, system, schema, max_tokens, thinking=None, effort=None):
        text = " ".join(b.get("text", "") for b in messages[0]["content"] if b.get("type") == "text")
        self.calls.append({"thinking": thinking, "max_tokens": max_tokens, "text": text})
        ans = []
        for x in listed(text):
            ok = x["id"].split("#")[1].split(":")[0] not in self.false_types
            ans.append(dict({"id": x["id"], "answer": "true" if ok else "false", "confidence": "high", "note_vi": "thấy rõ",
                             "fix_en": ""}, **self.observe(x["id"], ok)))
        return llm_runner.LlmReply(json.dumps({"answers": ans, "other_issues": []}), 1000, 200, "end_turn")


def listed(text):
    return json.loads(text.split("# Mệnh đề cần trả lời (đủ mọi id)\n", 1)[1].split("Khung đầy đủ:")[0])


class TeamTests(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "f.png")
        Image.new("RGB", (360, 640), (120, 160, 220)).save(self.path)
        self.frame = {"job_id": 341, "path": self.path, "data": shot(), "label": "S3·4"}

    class P:
        conn = None

    def run_frame(self, client):
        return qc_team.review_frame(self.P(), 8, self.dir, self.frame, client, entity=[{"type": "text", "text": "ảnh chuẩn"}],
                                    profiles={"KENTA": KENTA, "MAXIM": MAXIM})

    def spec(self):
        return qc_spec.compile_frame(None, 8, 341, self.frame["data"], profiles={"KENTA": KENTA, "MAXIM": MAXIM})["assertions"]

    def test_one_structured_call_and_code_decides(self):
        c = FakeClient(spec=self.spec())
        r = self.run_frame(c)
        self.assertEqual(len(c.calls), 1)
        self.assertEqual(c.calls[0]["thinking"], {"type": "disabled"})
        self.assertEqual(r["verdict"], "pass")
        c2 = FakeClient(false_types={"headwear"}, spec=self.spec())
        r2 = self.run_frame(c2)
        self.assertEqual(r2["verdict"], "block")
        self.assertEqual(r2["fails"][0]["type"], "headwear")

    def test_record_then_replay_answers_the_same_request_for_free(self):
        rec = os.path.join(self.dir, "calls.jsonl")
        first = self.run_frame(qc_team.RecordingClient(FakeClient(false_types={"asym"}, spec=self.spec()), rec))
        again = self.run_frame(qc_team.ReplayClient(rec))
        self.assertEqual(first["verdict"], again["verdict"])
        replay = qc_team.ReplayClient(rec)
        with self.assertRaises(llm_runner.LlmError):
            replay.ask_json([{"role": "user", "content": "khác"}], "s", {}, 10)
        self.assertEqual(replay.misses, 1)

    def test_missing_answers_are_said_and_become_doubts(self):
        a = [{"id": "a"}, {"id": "b"}]
        got = qc_team.parse_answers(json.dumps({"answers": [{"id": "a", "answer": "true"}, {"id": "zz"}], "other_issues": []}), a)
        self.assertEqual(list(got["answers"]), ["a"])
        self.assertEqual(got["problems"], ["thiếu câu trả lời: b"])
        self.assertEqual(qc_team.parse_answers("not json", a)["problems"], ["câu trả lời không phải JSON"])

    def test_the_request_hides_the_expected_side_from_the_model(self):
        c = FakeClient(spec=self.spec())
        self.run_frame(c)
        sides = [x for x in listed(c.calls[0]["text"]) if "#asym:" in x["id"]]
        self.assertTrue(sides)
        for x in sides:
            self.assertEqual(x["khai"], ["facing", "seen_at"])
            self.assertNotRegex(x["question"], r"LEFT|RIGHT")
            self.assertNotIn("mệnh đề", x)

    def test_looking_off_screen_frame_left_is_a_gaze_assertion(self):
        d = {"characters": ["KELLY"], "blocking": "close-up on KELLY's face, looking off-screen frame-left toward Maxim and Kenta"}
        a = [x for x in qc_spec.compile_frame(None, 8, 352, d, profiles={})["assertions"] if x["type"] == "gaze"]
        self.assertEqual(qc_measure._target_side(a[0]["expected"], ["KELLY"], {}), "left")

    def test_sky_reads_a_warm_top_band(self):
        from PIL import Image
        warm = os.path.join(self.dir, "w.png")
        Image.new("RGB", (100, 200), (200, 150, 90)).save(warm)
        self.assertEqual(qc_measure.sky(warm)["reading"], "warm")
        self.assertEqual(qc_measure.sky(self.path)["reading"], "day")

    def test_schema_objects_are_closed(self):
        def walk(s):
            if s.get("type") == "object":
                self.assertIs(s.get("additionalProperties"), False)
                for v in s.get("properties", {}).values():
                    walk(v)
            if s.get("type") == "array":
                walk(s["items"])
        walk(qc_team.ANSWER_SCHEMA)


if __name__ == "__main__":
    unittest.main()
