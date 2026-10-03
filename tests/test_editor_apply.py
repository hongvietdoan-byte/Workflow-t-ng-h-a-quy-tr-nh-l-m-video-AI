"""KE_HOACH_DUYET_BAN_THO P3: apply the ticked proposals, render again, check, keep or put the old cut back — 0 USD, no Claude."""
import json
import os
import tempfile
import unittest

from core import delivery, director_two_pass, editor_apply, editor_review, final_qc, lineage, rough_cut
from tests.test_rough_cut import make_video, intent
from tests.test_v2 import Base


def prop(i, action, shot, amount=0.0, value="", status="agreed", applicable=True, scene=1):
    return {"id": i, "at_s": 0.0, "scene": scene, "observed": "drag", "rank": 3, "evidence": "e", "action": action, "target_shot": shot, "amount": amount,
            "value": value, "why": "w", "applicable": applicable, "status": status, "director": {"verdict": "agree", "reason": ""}}


def shot(n, scene, start, seconds, scene_id=None):
    return {"n": n, "story_scene": scene, "scene_id": scene_id or n * 10, "start": start, "end": start + seconds, "seconds": seconds,
            "dialogue": False, "lip_sync": False, "money_shot": False, "speed": None, "transition_in": None}


class PlanTests(unittest.TestCase):
    """plan() with a fake render row — the clock, the manifest and real clip files, no database."""
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.clips = []
        for n, secs in enumerate((3, 3, 3.5), 1):
            path = os.path.join(self.dir, f"{n:02d}.mp4")
            make_video(path, secs)
            self.clips.append(path)
        man = {"timeline": [{"idx": n, "scene_id": n * 10, "seconds": s} for n, s in enumerate((3, 3, 3.0), 1)],
               "clips": [{"path": c} for c in self.clips]}
        self.row = {"manifest": json.dumps(man)}
        self.rc = {"shots": [shot(1, 1, 0, 3), shot(2, 1, 3, 3), shot(3, 2, 6, 3)],
                   "scenes": [{"scene": 1, "target_s": 6, "shots": [1, 2]}, {"scene": 2, "target_s": 3, "shots": [3]}]}

    def plan(self, proposals, ids):
        return editor_apply.plan(None, 1, self.dir, {"proposals": proposals}, self.rc, ids, self.row)

    def test_durations_and_music_follow_the_ticked_proposals(self):
        pl = self.plan([prop("F1", "shorten_shot", 1, 0.5), prop("F2", "music_cue", 3, value="cut", scene=2), prop("F3", "extend_hold", 3, 0.4, scene=2)],
                       ["F1", "F2", "F3"])
        self.assertEqual(pl["durations"], [2.5, 3.0, 3.4])
        self.assertEqual(pl["music"], {30: "cut"})
        self.assertEqual([a["id"] for a in pl["applied"]], ["F1", "F2", "F3"])
        self.assertEqual(pl["clips"], self.clips)

    def test_the_end_hold_already_in_the_timeline_is_taken_off(self):
        man = json.loads(self.row["manifest"])
        man["timeline"][-1]["seconds"] = 2.5
        man["end_hold"] = {"held_s": 1.5}
        self.assertEqual(editor_apply.base_durations(man), [3, 3, 1.0])

    def test_only_what_was_ticked_and_only_what_can_be_applied(self):
        pl = self.plan([prop("F1", "shorten_shot", 1, 0.5), prop("F2", "suggest_flag", 0, value="j_cut", applicable=False)], ["F1", "F2", "F9"])
        self.assertEqual([a["id"] for a in pl["applied"]], ["F1"])
        reasons = {r["id"]: r["reason"] for r in pl["refused"]}
        self.assertIn("gợi ý", reasons["F2"])
        self.assertIn("không có", reasons["F9"])
        with self.assertRaises(ValueError):
            self.plan([prop("F2", "suggest_flag", 0, value="j_cut", applicable=False)], ["F2"])

    def test_changed_shots_are_marked_to_get_a_clip_of_their_new_length(self):
        pl = self.plan([prop("F1", "shorten_shot", 1, 0.5), prop("F2", "extend_hold", 3, 1.0, scene=2), prop("F3", "music_cue", 2, value="cut")],
                       ["F1", "F2", "F3"])
        self.assertEqual(pl["fit"], [10, 30])                                                         # the music cue changes no length
        self.assertEqual(pl["durations"], [2.5, 3.0, 4.0])

    def test_a_shot_without_a_scene_row_is_refused(self):
        self.rc["shots"][1]["scene_id"] = None
        pl = self.plan([prop("F1", "shorten_shot", 1, 0.5), prop("F2", "music_cue", 2, value="cut")], ["F1", "F2"])
        self.assertEqual([a["id"] for a in pl["applied"]], ["F1"])
        self.assertIn("dòng cảnh", pl["refused"][0]["reason"])

    def test_the_ticked_proposals_are_checked_together_not_one_by_one(self):
        # scene 1 has 6 s against 6 s: each cut of 0.9 s passes alone (5.1 s); both together make 4.2 s, further from the target than the limit
        pl = self.plan([prop("F1", "shorten_shot", 1, 0.9), prop("F2", "shorten_shot", 2, 0.9)], ["F1", "F2"])
        self.assertEqual([a["id"] for a in pl["applied"]], ["F1"])
        self.assertIn("target_s", pl["refused"][0]["reason"])

    def test_an_old_cut_without_clips_in_its_manifest_is_refused(self):
        self.row = {"manifest": json.dumps({"timeline": [{"idx": 1, "scene_id": 10, "seconds": 3}]})}
        with self.assertRaises(ValueError):
            self.plan([prop("F1", "shorten_shot", 1, 0.5)], ["F1"])


class QualityGateTests(unittest.TestCase):
    def test_more_of_any_check_is_worse(self):
        before = {"issues": [{"code": "silence", "level": "warn"}, {"code": "hint", "level": "hint"}]}
        self.assertFalse(editor_apply.qc_worse(before, {"issues": [{"code": "silence", "level": "warn"}]})[0])
        self.assertFalse(editor_apply.qc_worse(before, {"issues": []})[0])
        worse, why = editor_apply.qc_worse(before, {"issues": [{"code": "silence", "level": "warn"}, {"code": "silence", "level": "warn"}]})
        self.assertTrue(worse)
        self.assertIn("silence: 1 → 2", why[0])
        self.assertTrue(editor_apply.qc_worse(before, {"issues": [{"code": "music_hole", "level": "block"}]})[0])      # a new kind counts


class RenderOverrideTests(Base):
    def test_a_music_edit_changes_the_render_not_the_plan(self):
        rows = [{"path": "x.mp4", "scene_id": self.sid(i)} for i in (1, 2, 3)]
        before = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.sid(2),)).fetchone()["data"]
        edits = {"music": {self.sid(2): "cut"}}
        self.assertEqual(delivery.scene_data(self.p, self.sid(2), edits)["sound"]["music"], "cut")
        self.assertNotEqual(delivery.scene_data(self.p, self.sid(2))["sound"].get("music") if delivery.scene_data(self.p, self.sid(2)).get("sound") else None, "cut")
        plain = delivery.sound_plan(self.p, rows, [4.0, 4.0, 4.0])
        edited = delivery.sound_plan(self.p, rows, [4.0, 4.0, 4.0], edits=edits)
        self.assertFalse(plain["planned"])
        self.assertTrue(edited["planned"])
        self.assertEqual(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.sid(2),)).fetchone()["data"], before)       # the plan is untouched


class ApplyTests(Base):
    """apply() end to end with a stand-in for delivery.render (the real one needs the whole project's clips and sound)."""
    def setUp(self):
        super().setUp()
        self.dir = tempfile.mkdtemp()
        self.out_dir = delivery.output_dir(self.dir, self.pid)
        self.out = os.path.join(self.out_dir, "FINAL_VIDEO.mp4")
        director_two_pass._save_raw(self.p, self.pid, intent([
            {"idx": 1, "emotional_intent": "a", "target_s": 4, "peak": 2}, {"idx": 2, "emotional_intent": "b", "target_s": 3, "peak": 2},
            {"idx": 3, "emotional_intent": "c", "target_s": 3}]))
        self.p.conn.execute("UPDATE scenes SET data=json_set(COALESCE(data,'{}'),'$.dialogue',json('[]'),'$.lip_sync',json('false')) WHERE project_id=?",
                            (self.pid,))
        self.p.conn.commit()
        self.clips = []
        for n, secs in enumerate((4, 3, 3), 1):
            path = os.path.join(self.dir, f"clip{n}.mp4")
            make_video(path, secs)
            self.clips.append(path)
        rows = list(self.p.conn.execute("SELECT id, idx FROM scenes WHERE project_id=? ORDER BY idx", (self.pid,)))
        self.timeline = [{"idx": r["idx"], "scene_id": r["id"], "seconds": float(s)} for r, s in zip(rows, (4, 3, 3))]
        make_video(self.out, 10)
        self.a_id = delivery.record(self.p, self.pid, "final", self.out, None, {"timeline": self.timeline, "transition": "cut", "fade": 0,
                                                                              "clips": [{"path": c} for c in self.clips]})
        self.rc = rough_cut.build(self.p, self.pid, self.dir)
        self.review = {"fingerprint": "rv1", "rough_cut": self.rc["fingerprint"], "summary": "x", "intent_source": "director_intent_raw",
                       "proposals": [prop("F1", "shorten_shot", 2, 0.5, scene=2), prop("F2", "music_cue", 3, value="cut", scene=3),
                                     prop("F3", "extend_hold", 1, 0.2, status="contested")], "rejected": [], "proposed": 3,
                       "cost": {"usd": 0.0, "calls": 2}}
        with open(editor_review.path_of(self.dir, self.pid), "w", encoding="utf-8") as f:
            json.dump(self.review, f)
        self.seen = {}

    def render_stub(self, p, pid, data_dir, music, clips=None, durations=None, edits=None):
        self.seen = {"clips": clips, "durations": list(durations), "edits": edits}
        make_video(self.out, max(1, sum(durations)), sound="sine=frequency=880")
        timeline = [dict(t, seconds=d) for t, d in zip(self.timeline, durations)]
        oid = delivery.record(p, pid, "final", self.out, None, {"timeline": timeline, "transition": "cut", "fade": 0,
                                                                "clips": [{"path": c} for c in clips], "editor_apply": (edits or {}).get("meta")})
        return {"output_id": oid, "path": self.out, "seconds": sum(durations)}

    def qc(self, blocks=0, warns=0):
        return lambda: {"ok": not blocks, "blocks": blocks, "warns": warns,
                        "issues": [{"code": "silence", "level": "warn"}] * warns + [{"code": "x", "level": "block"}] * blocks}

    def latest(self):
        return lineage.latest_output(self.p.conn, self.pid, "final")

    def test_a_kept_application_renders_with_the_new_numbers_and_keeps_the_old_cut(self):
        a_size = os.path.getsize(self.out)
        res = editor_apply.apply(self.p, self.pid, self.dir, ["F1", "F2"], render_fn=self.render_stub, qc_fn=self.qc())
        self.assertTrue(res["kept"])
        self.assertEqual(self.seen["durations"], [4.0, 2.5, 3.0])
        self.assertEqual(self.seen["clips"], self.clips)
        self.assertEqual(self.seen["edits"]["music"], {self.timeline[2]["scene_id"]: "cut"})
        self.assertEqual(self.seen["edits"]["fit"], [self.timeline[1]["scene_id"]])                  # only the shortened shot gets a new clip
        self.assertEqual(self.latest()["id"], res["to_output"])
        self.assertEqual(self.latest()["path"], self.out)                                         # the known name is the current cut
        old = self.p.conn.execute("SELECT path FROM outputs WHERE id=?", (self.a_id,)).fetchone()["path"]
        self.assertNotEqual(old, self.out)
        self.assertEqual(os.path.getsize(old), a_size)                                            # the old cut survived the overwrite
        self.assertEqual(json.loads(self.latest()["manifest"])["editor_apply"]["round"], 1)
        self.assertEqual(editor_apply.load_log(self.dir, self.pid)[0]["kept"], True)
        self.assertEqual(res["before"]["seconds"], 10.0)

    def test_a_worse_cut_is_not_kept_the_old_one_is_put_back(self):
        a_size = os.path.getsize(self.out)
        calls = iter([self.qc(0, 0), self.qc(0, 2)])
        res = editor_apply.apply(self.p, self.pid, self.dir, ["F1"], render_fn=self.render_stub, qc_fn=lambda: next(calls)())
        self.assertFalse(res["kept"])
        self.assertIn("silence: 0 → 2", res["why"][0])
        cur = self.latest()
        self.assertEqual(cur["path"], self.out)
        self.assertEqual(os.path.getsize(self.out), a_size)                                       # the old picture is the current file again
        self.assertNotIn("editor_apply", json.loads(cur["manifest"]))
        self.assertIsNone(res["to_output"])                                                       # the rejected cut is no output row, only a file
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) n FROM outputs WHERE kind='final'").fetchone()["n"], 2)
        self.assertTrue(os.path.exists(res["b_path"]))

    def test_a_failed_render_puts_the_old_cut_back_and_says_so(self):
        a_size = os.path.getsize(self.out)

        def boom(*args, **kwargs):
            make_video(self.out, 1)                                                                # half-written file under the known name
            raise RuntimeError("ffmpeg died")
        with self.assertRaises(RuntimeError):
            editor_apply.apply(self.p, self.pid, self.dir, ["F1"], render_fn=boom, qc_fn=self.qc())
        self.assertEqual(os.path.getsize(self.out), a_size)
        self.assertEqual(self.latest()["path"], self.out)
        self.assertIn("ffmpeg died", editor_apply.load_log(self.dir, self.pid)[0]["error"])

    def test_the_person_can_go_back_to_the_old_cut(self):
        editor_apply.apply(self.p, self.pid, self.dir, ["F1"], render_fn=self.render_stub, qc_fn=self.qc())
        a_size = 0
        old = self.p.conn.execute("SELECT path FROM outputs WHERE id=?", (self.a_id,)).fetchone()["path"]
        a_size = os.path.getsize(old)
        res = editor_apply.revert(self.p, self.pid, self.dir)
        self.assertEqual(self.latest()["id"], res["restored_output"])
        self.assertEqual(os.path.getsize(self.out), a_size)
        self.assertNotIn("editor_apply", json.loads(self.latest()["manifest"]))
        with self.assertRaises(ValueError):                                                       # nothing left to go back to
            editor_apply.revert(self.p, self.pid, self.dir)

    def test_limits_old_reviews_and_nothing_to_apply(self):
        with self.assertRaises(ValueError):
            editor_apply.apply(self.p, self.pid, self.dir, [], render_fn=self.render_stub, qc_fn=self.qc())              # nothing ticked
        editor_apply.apply(self.p, self.pid, self.dir, ["F1"], render_fn=self.render_stub, qc_fn=self.qc(0, 0))
        # a kept round makes the cut a new one: the review no longer belongs to it
        with self.assertRaises(ValueError) as e:
            editor_apply.apply(self.p, self.pid, self.dir, ["F2"], render_fn=self.render_stub, qc_fn=self.qc())
        self.assertIn("cũ", str(e.exception))

    def test_at_most_two_applications_per_review(self):
        worse = iter([self.qc(0, 0), self.qc(0, 1)] * 3)
        for _ in range(2):
            editor_apply.apply(self.p, self.pid, self.dir, ["F1"], render_fn=self.render_stub, qc_fn=lambda: next(worse)())
        with self.assertRaises(ValueError) as e:
            editor_apply.apply(self.p, self.pid, self.dir, ["F1"], render_fn=self.render_stub, qc_fn=self.qc())
        self.assertIn(str(editor_apply.MAX_ATTEMPTS), str(e.exception))

    def test_a_review_of_another_intent_is_not_applied(self):
        director_two_pass._save_raw(self.p, self.pid, intent([{"idx": 1, "emotional_intent": "đổi", "target_s": 9}]))
        with self.assertRaises(ValueError) as e:
            editor_apply.apply(self.p, self.pid, self.dir, ["F1"], render_fn=self.render_stub, qc_fn=self.qc())
        self.assertIn("cũ", str(e.exception))

    def test_lines_say_what_happened(self):
        res = editor_apply.apply(self.p, self.pid, self.dir, ["F1"], render_fn=self.render_stub, qc_fn=self.qc())
        text = "\n".join(editor_apply.lines(res))
        self.assertIn("Đã áp", text)
        self.assertIn("10 s", text)


class RealRenderTests(unittest.TestCase):
    """The real delivery.render: the numbers P3 passes (new lengths, a music edit) reach the film itself."""
    def setUp(self):
        import subprocess
        from core import ffmpeg_studio, final_cut
        from core.db import connect
        from core.pipeline import Pipeline
        ff = ffmpeg_studio.find_ffmpeg()
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("real", aspect="9:16")
        self.sids = []
        for idx in (1, 2, 3):
            sid = self.p.create_scene(self.pid, idx, f"s{idx}")
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"story_scene": 1, "shot_no": idx, "size": "MS"}), sid))
            path = final_cut.clip_path(self.data, self.pid, idx)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=0x808080:s=270x480:d=3", "-pix_fmt", "yuv420p", path],
                           check=True)
            self.sids.append(sid)
        self.p.conn.commit()
        self.music = os.path.join(self.data, "m.m4a")
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=14", "-c:a", "aac", self.music], check=True)
        self.settings = dict(delivery.get_settings(self.p, self.pid), keep_audio=False, transition="cut")

    def render(self, durations, edits=None):
        from unittest import mock
        with mock.patch.dict(os.environ, {"FEATURE_SOUND_INTENT": "1"}):
            res = delivery.render(self.p, self.pid, self.data, music_path=self.music, settings=self.settings, durations=durations, edits=edits)
        row = self.p.conn.execute("SELECT manifest FROM outputs WHERE id=?", (res["output_id"],)).fetchone()
        return res, json.loads(row["manifest"])

    def test_shorter_shots_get_a_shorter_clip_and_the_music_edit_reaches_the_film(self):
        from core import ffmpeg_studio
        plain, man_a = self.render([3.0, 3.0, 3.0])
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(plain["path"]), 9.0, delta=0.3)
        info = {"round": 1, "from_output": plain["output_id"], "applied": [{"id": "F1"}]}
        edited, man_b = self.render([2.5, 2.0, 3.0], {"music": {self.sids[1]: "cut"}, "fit": [self.sids[0], self.sids[1]], "meta": info})
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(edited["path"]), 7.5, delta=0.3)       # a cut joins whole files: the lengths live in the clips
        self.assertEqual([t["seconds"] for t in man_b["timeline"]], [2.5, 2.0, 3.0])
        self.assertEqual([f["how"] for f in man_b["editor_fit"]], ["trim", "trim"])
        self.assertEqual(man_b["editor_apply"], info)
        self.assertNotIn("editor_apply", man_a)
        self.assertNotIn("editor_fit", man_a)
        self.assertFalse(man_a.get("sound_intent"))                                                # no music silence planned without the edit
        self.assertTrue(man_b["sound_intent"]["applied"])
        self.assertTrue(man_b["sound_intent"]["off"])                                              # the edit's `cut` on shot 2 is in the film
        self.assertNotIn("sound", json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.sids[1],)).fetchone()["data"]))
        for sid_idx in (1, 2, 3):                                                                  # the shots' own clips are untouched
            from core import final_cut
            self.assertAlmostEqual(ffmpeg_studio.probe_duration(final_cut.clip_path(self.data, self.pid, sid_idx)), 3.0, delta=0.2)

    def test_a_longer_shot_holds_its_last_frame(self):
        from core import ffmpeg_studio
        held, man = self.render([3.0, 3.0, 4.5], {"fit": [self.sids[2]], "meta": {"round": 1}})
        self.assertEqual([(f["from_s"], f["to_s"], f["how"]) for f in man["editor_fit"]], [(3.0, 4.5, "hold")])
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(held["path"]), 10.5, delta=0.4)


if __name__ == "__main__":
    unittest.main()
