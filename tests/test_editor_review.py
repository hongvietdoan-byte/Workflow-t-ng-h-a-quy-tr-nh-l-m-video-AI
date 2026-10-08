"""KE_HOACH_DUYET_BAN_THO P2: the Editor and the Director review the rough cut — what the code allows, what the model sees, one call each."""
import os
import unittest
from unittest import mock

from core import director_two_pass, editor_review, llm_runner
from tests.test_rough_cut import RoughCutTests as Fixture, intent


def shot(n, scene, start, seconds, dialogue=False, lip=False):
    return {"n": n, "story_scene": scene, "start": start, "end": start + seconds, "seconds": seconds, "dialogue": dialogue, "lip_sync": lip,
            "money_shot": False, "speed": None, "transition_in": None}


RES = {"shots": [shot(1, 1, 0, 3, dialogue=True), shot(2, 1, 3, 2), shot(3, 2, 5, 4), shot(4, 2, 9, 0.8), shot(5, 3, 9.8, 3)],
       "scenes": [{"scene": 1, "target_s": 5, "shots": [1, 2]}, {"scene": 2, "target_s": 5, "shots": [3, 4]}, {"scene": 3, "target_s": None, "shots": [5]}]}


def f(**kw):
    base = {"at_s": 3.0, "scene": 1, "observed": "drag", "evidence": "shot 2 dài 2 s", "action": "shorten_shot", "target_shot": 2,
            "amount": 0.5, "value": "", "why": "kéo dài"}
    base.update(kw)
    return base


class EditorBookTests(unittest.TestCase):
    def test_only_the_judgment_blocks_of_the_editors_book_are_sent(self):
        text = editor_review.editor_text()
        self.assertIn("E1. Nghệ thuật cắt", text)
        self.assertIn("E4. Nhạc nền", text)
        self.assertIn("Ưu tiên khi xung đột", text)
        for numeric in ("E7. Chữ và vùng an toàn", "E8. Độ to và xuất bản", "E5. Chỉnh màu"):
            self.assertNotIn(numeric, text)
        self.assertNotIn("<!-- review -->", text)


class VetTests(unittest.TestCase):
    def vet(self, *findings):
        return editor_review.vet(list(findings), RES)

    def test_a_good_proposal_passes_with_an_id_and_a_rank(self):
        ok, no = self.vet(f())
        self.assertEqual((len(ok), len(no)), (1, 0))
        self.assertEqual((ok[0]["id"], ok[0]["rank"], ok[0]["applicable"]), ("F1", 3, True))

    def test_shots_with_speech_or_lip_sync_are_never_touched(self):
        for act in ("shorten_shot", "extend_hold", "slow_or_freeze"):
            ok, no = self.vet(f(action=act, target_shot=1, value="slow"))
            self.assertEqual(ok, [], act)
            self.assertIn("thoại", no[0]["reason"])

    def test_trim_head_drops_the_first_seconds_but_never_of_speech_lip_sync_or_a_chained_shot(self):
        # KLD-19 (#22: the join 254 → 255 jerked at 1,5 s of 255 and nothing could drop a clip's first seconds)
        ok, no = self.vet(f(action="trim_head", target_shot=3, amount=0.5, scene=2))
        self.assertEqual((len(ok), no), (1, []))
        self.assertTrue(ok[0]["applicable"])
        self.assertIn("đầu", editor_review.describe(ok[0]))
        ok, no = self.vet(f(action="trim_head", target_shot=1, amount=0.5))
        self.assertEqual(ok, [])
        self.assertIn("thoại", no[0]["reason"])
        res = {"shots": [dict(s) for s in RES["shots"]], "scenes": RES["scenes"]}
        res["shots"][2]["chained"] = True                       # starts on the previous clip's last frame (start_from_prev_clip)
        ok, no = editor_review.vet([f(action="trim_head", target_shot=3, amount=0.5, scene=2)], res)
        self.assertEqual(ok, [])
        self.assertIn("chọn cách xử lý chỗ nối", no[0]["reason"])
        self.assertTrue(self.vet(f(action="trim_head", target_shot=3, amount=9, scene=2))[1])
        self.assertIn("ngắn hơn", self.vet(f(action="trim_head", target_shot=4, amount=0.4, scene=2))[1][0]["reason"])
        self.assertIn("trim_head", open(os.path.join(os.path.dirname(__file__), "..", "prompts", "24_editor_review.md"), encoding="utf-8").read())

    def chained(self):
        res = {"shots": [dict(s) for s in RES["shots"]], "scenes": RES["scenes"]}
        res["shots"][2]["chained"] = True                       # shot 3 starts on shot 2's last frame
        return res

    def test_a_chained_shot_may_lose_its_head_when_the_tail_before_goes_too(self):
        # KLD-19 (c), người dùng 08/10: (1) cắt luôn đuôi shot trước để hai đầu khớp động tác
        ok, no = editor_review.vet([f(action="trim_head", target_shot=3, amount=0.5, scene=2, join="trim_tail", join_amount=0.5)],
                                   self.chained())
        self.assertEqual((len(ok), no), (1, []))
        self.assertEqual((ok[0]["join"], ok[0]["join_amount"], ok[0]["applicable"]), ("trim_tail", 0.5, True))
        self.assertIn("đuôi", editor_review.describe(ok[0]))
        # the tail of the shot before obeys the same limits: MIN_SHOT, no speech
        res = self.chained()
        res["shots"][1]["seconds"] = 0.8
        self.assertIn("ngắn hơn", editor_review.vet([f(action="trim_head", target_shot=3, amount=0.5, scene=2, join="trim_tail",
                                                       join_amount=0.5)], res)[1][0]["reason"])
        res = self.chained()
        res["shots"][1]["dialogue"] = True
        self.assertIn("thoại", editor_review.vet([f(action="trim_head", target_shot=3, amount=0.5, scene=2, join="trim_tail",
                                                    join_amount=0.5)], res)[1][0]["reason"])
        self.assertTrue(editor_review.vet([f(action="trim_head", target_shot=3, amount=0.5, scene=2, join="trim_tail", join_amount=9)],
                                          self.chained())[1])

    def test_a_chained_shot_may_lose_its_head_when_a_transition_or_effect_covers_the_join(self):
        # KLD-19 (c): (2) chuyển cảnh / hiệu ứng che chỗ nối — any kind the render can draw, not only at a scene change
        for kind in ("flash", "dip", "whip", "zoom_through", "shake"):
            ok, no = editor_review.vet([f(action="trim_head", target_shot=3, amount=0.5, scene=2, join=kind)], self.chained())
            self.assertEqual((len(ok), no), (1, []), kind)
            self.assertTrue(ok[0]["applicable"])
        ok, no = editor_review.vet([f(action="trim_head", target_shot=3, amount=0.5, scene=2, join="sparkles")], self.chained())
        self.assertEqual(ok, [])
        self.assertIn("chỗ nối", no[0]["reason"])

    def cut(self, **kw):
        base = dict(action="cut_segment", target_shot=3, scene=2, start=1.0, end=1.6, join="match_cut", amount=0)
        base.update(kw)
        return f(**base)

    def test_cut_segment_drops_a_bad_stretch_in_the_middle_of_a_clip(self):
        # TODO điểm 12 (người dùng 07/10): bỏ một đoạn lỗi GIỮA clip (tay biến dạng, giật), hai nửa nối bằng cắt khớp hoặc che bằng join
        ok, no = self.vet(self.cut())
        self.assertEqual((len(ok), no), (1, []))
        self.assertEqual((ok[0]["start"], ok[0]["end"], ok[0]["amount"], ok[0]["join"], ok[0]["applicable"]), (1.0, 1.6, 0.6, "match_cut", True))
        self.assertIn("giữa", editor_review.describe(ok[0]))
        for kind in editor_review.JOIN_COVERS:
            self.assertTrue(self.vet(self.cut(join=kind))[0], kind)
        self.assertIn("cut_segment", open(os.path.join(os.path.dirname(__file__), "..", "prompts", "24_editor_review.md"), encoding="utf-8").read())

    def test_cut_segment_is_checked_by_code(self):
        reason = lambda **kw: self.vet(self.cut(**kw))[1][0]["reason"]
        self.assertIn("thoại", reason(target_shot=1, scene=1))                           # speech / lip sync: never
        self.assertIn("nối", reason(join=""))                                             # how the halves meet must be said
        self.assertIn("nối", reason(join="sparkles"))
        self.assertIn("trim_head", reason(start=0.0, end=0.6))                             # at the head: that is trim_head
        self.assertIn("shorten_shot", reason(start=3.5, end=4.0))                         # at the end: that is shorten_shot
        self.assertIn("đoạn", reason(start=1.6, end=1.0))
        self.assertIn("ngoài", reason(start=0.5, end=3.7))                               # longer than AMOUNT_MAX
        self.assertIn("ngắn hơn", reason(target_shot=4, start=0.2, end=0.55))              # 0,8 s − 0,35 s < MIN_SHOT
        self.assertIn("target_s", reason(start=0.5, end=3.0))                             # scene 2 pushed from 5 s to 2,3 s
        ok, no = self.vet(f(action="trim_head", target_shot=3, amount=0.5, scene=2), self.cut())
        self.assertEqual(len(ok), 1)
        self.assertIn("trim_head", no[0]["reason"])                                       # the clip's seconds would move under the cut

    def test_glitch_hints_from_clip_measure_reach_the_editors_clock(self):
        # TODO điểm 12: the jumps clip_measure finds inside the used part of a clip are hints for cut_segment (code only, 0 USD)
        import tempfile
        from core import rough_cut
        d = tempfile.mkdtemp()
        paths = []
        for n in (1, 2, 3):
            paths.append(os.path.join(d, f"{n}.mp4"))
            open(paths[-1], "wb").close()
        shots = [dict(shot(1, 1, 0, 3), idx=1), dict(shot(2, 1, 3, 2), idx=2), dict(shot(3, 2, 5, 4, dialogue=True), idx=3)]
        man = {"clips": [{"path": p} for p in paths], "editor_fit": []}
        got = {paths[0]: {"jerks": [1.2, 3.5], "cuts": []}, paths[1]: {"jerks": [], "cuts": [0.9]}, paths[2]: {"jerks": [1.0]}}
        self.assertEqual(rough_cut.glitch_hints(man, shots, measure=lambda p: got[p]), 2)
        self.assertEqual(shots[0]["glitches"], {"jerks": [1.2]})                        # 3,5 s is past the 3 s the cut uses
        self.assertEqual(shots[1]["glitches"], {"cuts": [0.9]})
        self.assertNotIn("glitches", shots[2])                                           # speech: never cut, no hint
        man["editor_fit"] = [{"idx": 1, "how": "head"}]                                  # its seconds moved in an earlier edit
        shots[0].pop("glitches")
        rough_cut.glitch_hints(man, shots, measure=lambda p: got[p])
        self.assertNotIn("glitches", shots[0])
        self.assertIn("glitches", editor_review._CLOCK_KEYS)

    def test_numbers_are_bounded_by_the_clock(self):
        self.assertTrue(self.vet(f(amount=9))[1])                                   # above the largest cut
        self.assertTrue(self.vet(f(amount=0.05))[1])                                # below the smallest
        self.assertIn("ngắn hơn", self.vet(f(target_shot=4, amount=0.4))[1][0]["reason"])      # 0,8 s shot - 0,4 s < 0,5 s
        self.assertIn("không có trong bản dựng", self.vet(f(target_shot=99))[1][0]["reason"])

    def test_a_scene_is_not_pushed_further_from_the_directors_target(self):
        ok, no = self.vet(f(action="shorten_shot", target_shot=3, amount=2.0))       # scene 2: 4.8 s against 5 s -> 2.8 s: out of +-1 s
        self.assertEqual(ok, [])
        self.assertIn("target_s", no[0]["reason"])
        self.assertTrue(self.vet(f(action="extend_hold", target_shot=4, amount=0.4))[0])    # moves scene 2 TOWARDS its target

    def test_closed_lists_and_where_a_transition_may_go(self):
        self.assertTrue(self.vet(f(observed="bad"))[1])
        self.assertTrue(self.vet(f(action="delete_everything"))[1])
        self.assertTrue(self.vet(f(evidence=" "))[1])
        self.assertTrue(self.vet(f(action="music_cue", value="loud"))[1])
        self.assertTrue(self.vet(f(action="music_cue", value="breath"))[0])
        self.assertIn("đổi cảnh", self.vet(f(action="transition", target_shot=2, value="crossfade"))[1][0]["reason"])   # same scene as shot 1
        self.assertTrue(self.vet(f(action="transition", target_shot=3, value="crossfade"))[0])                          # first shot of scene 2
        self.assertTrue(self.vet(f(action="suggest_flag", target_shot=0, value="nonsense"))[1])

    def test_unverified_things_are_only_suggestions(self):
        ok, _ = self.vet(f(action="slow_or_freeze", target_shot=5, value="slow"))
        self.assertFalse(ok[0]["applicable"])                                        # speed_ramp is not verified
        ok, _ = self.vet(f(action="suggest_flag", target_shot=0, value="j_cut"))
        self.assertFalse(ok[0]["applicable"])
        ok, _ = self.vet(f(action="retrim_from_raw", target_shot=2))
        self.assertFalse(ok[0]["applicable"])

    def test_at_most_six_and_no_duplicates(self):
        ok, no = self.vet(f(action="music_cue", target_shot=2, value="keep"), f(action="music_cue", target_shot=2, value="cut"))
        self.assertEqual(len(ok), 1)                                                 # same action on the same shot is one proposal
        ok, no = self.vet(*[f(action="music_cue", target_shot=n, value="keep") for n in (2, 3, 4, 5)],
                          *[f(action="suggest_flag", target_shot=0, value=v) for v in editor_review.FLAG_HINTS],
                          f(action="none", target_shot=0))
        self.assertEqual(len(ok), editor_review.MAX_FINDINGS)
        self.assertTrue(any("quá" in r["reason"] for r in no))


class ReconcileTests(unittest.TestCase):
    def accepted(self):
        return editor_review.vet([f(), f(action="music_cue", target_shot=3, value="cut", observed="music_competes")], RES)[0]

    def test_agree_object_and_modify(self):
        a = self.accepted()
        out = editor_review.reconcile(a, [{"id": "F1", "verdict": "agree", "reason": ""}, {"id": "F2", "verdict": "object", "reason": "sound.music keep"}], RES)
        by = {x["id"]: x for x in out}
        self.assertEqual((by["F1"]["status"], by["F2"]["status"]), ("agreed", "contested"))
        self.assertEqual(out[0]["id"], "F2")                                         # music_competes (rank 1) is read before drag (rank 3)
        out = editor_review.reconcile(a, [{"id": "F1", "verdict": "modify", "reason": "ngắn hơn", "amount": 0.3},
                                          {"id": "F2", "verdict": "agree", "reason": ""}], RES)
        mod = [x for x in out if x["id"] == "F1"][0]
        self.assertEqual((mod["status"], mod["amount"], mod["editor_original"]["amount"]), ("modified", 0.3, 0.5))

    def test_a_modification_that_breaks_the_rules_becomes_contested_not_applied(self):
        out = editor_review.reconcile(self.accepted(), [{"id": "F1", "verdict": "modify", "reason": "x", "amount": 50}, {"id": "F2", "verdict": "agree"}], RES)
        bad = [x for x in out if x["id"] == "F1"][0]
        self.assertEqual(bad["status"], "contested")
        self.assertIn("không hợp lệ", bad["director"]["reason"])


class Recorder(llm_runner.MockLlm):
    """MockLlm that remembers what each call carried."""
    def __init__(self):
        self.calls = []

    def complete(self, prompt, images=()):
        self.calls.append((prompt, list(images)))
        return super().complete(prompt, images)


class RunTests(Fixture):
    def prepare(self):
        director_two_pass._save_raw(self.p, self.pid, intent([
            {"idx": 1, "emotional_intent": "a", "target_s": 5, "peak": 2}, {"idx": 2, "emotional_intent": "b", "target_s": 3, "peak": 3},
            {"idx": 3, "emotional_intent": "c", "target_s": 5}]))
        data = self.render([4, 3, 3], [1, 2, 3])
        self.p.conn.execute("UPDATE scenes SET data=json_set(COALESCE(data,'{}'),'$.dialogue',json('[]'),'$.lip_sync',json('false')) WHERE project_id=?",
                            (self.pid,))
        self.p.conn.commit()
        return data

    def test_one_call_each_pictures_in_the_first_and_never_in_the_second(self):
        data = self.prepare()
        llm = Recorder()
        res = editor_review.run(self.p, self.pid, llm, data)
        self.assertEqual(len(llm.calls), 2)
        (p1, images1), (p2, images2) = llm.calls
        self.assertTrue(p1.startswith("# Biên tập viên — duyệt bản dựng thô"))
        self.assertTrue(p2.startswith("# Đạo diễn — trả lời đề xuất của Biên tập viên"))
        self.assertTrue(0 < len(images1) <= llm_runner.MAX_IMAGES)
        self.assertTrue(all(os.path.exists(path) for _, path in images1))
        self.assertEqual(images2, [])
        self.assertIn("không nghe được", p1)
        self.assertIn("E4. Nhạc nền", p1)                                            # the book's review blocks travel with the call
        self.assertNotIn("E8. Độ to và xuất bản", p1)
        self.assertEqual([x["status"] for x in res["proposals"]], ["agreed"])
        self.assertEqual(res["proposals"][0]["action"], "shorten_shot")
        self.assertEqual(res["intent_source"], "director_intent_raw")
        self.assertTrue(os.path.exists(editor_review.path_of(data, self.pid)))

    def test_the_same_cut_and_intent_is_not_asked_again(self):
        data = self.prepare()
        llm = Recorder()
        editor_review.run(self.p, self.pid, llm, data)
        again = editor_review.run(self.p, self.pid, llm, data)
        self.assertEqual(len(llm.calls), 2)
        self.assertEqual(again["fingerprint"], editor_review.load(data, self.pid)["fingerprint"])
        editor_review.run(self.p, self.pid, llm, data, force=True)
        self.assertEqual(len(llm.calls), 4)

    def test_no_proposal_means_no_call_for_the_director(self):
        data = self.prepare()
        with mock.patch.object(llm_runner.MockLlm, "complete", return_value=llm_runner.LlmReply(
                '{"summary": "bản dựng ổn", "findings": []}', 50, 10)) as call:
            res = editor_review.run(self.p, self.pid, llm_runner.MockLlm(), data)
        self.assertEqual(call.call_count, 1)
        self.assertEqual(res["proposals"], [])

    def test_an_invalid_director_answer_twice_saves_nothing(self):
        data = self.prepare()

        class Wrong(Recorder):
            def complete(self, prompt, images=()):
                if prompt.startswith("# Đạo diễn — trả lời"):
                    return llm_runner.LlmReply('{"verdicts": []}', 20, 5)
                return super().complete(prompt, images)
        with self.assertRaises(llm_runner.LlmError):
            editor_review.run(self.p, self.pid, Wrong(), data)
        self.assertIsNone(editor_review.load(data, self.pid))

    def test_a_review_without_a_render_says_so(self):
        with self.assertRaises(ValueError):
            editor_review.run(self.p, self.pid, Recorder(), self.data)

    def test_the_estimate_is_shown_before_and_counts_the_pictures(self):
        few, many = editor_review.estimate(self.p.conn, 1), editor_review.estimate(self.p.conn, 12)
        self.assertGreater(few, 0)
        self.assertGreater(many, few)
        self.assertLess(many, editor_review.RUN_CAP_USD)                             # the lock leaves room above the estimate

    def test_lines_show_both_sides_of_a_contested_proposal(self):
        a = editor_review.vet([f(observed="music_competes", action="music_cue", target_shot=3, value="cut")], RES)[0]
        out = editor_review.reconcile(a, [{"id": "F1", "verdict": "object", "reason": "sound.music keep ở cảnh 2"}], RES)
        text = "\n".join(editor_review.lines({"summary": "x", "proposals": out, "rejected": [], "proposed": 1, "intent_source": "director_intent_raw",
                                               "cost": {"usd": 0.1, "calls": 2}}))
        self.assertIn("⚖️", text)
        self.assertIn("chứng cứ", text)
        self.assertIn("sound.music keep ở cảnh 2", text)


if __name__ == "__main__":
    unittest.main()
