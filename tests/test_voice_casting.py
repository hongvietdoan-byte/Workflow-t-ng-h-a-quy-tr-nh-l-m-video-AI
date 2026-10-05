"""S14.26 (05/10): giọng tiếng Việt tự gắn từ lúc phân tích cảnh — Director ghi giới tính / tuổi / tính cách mỗi vai có thoại (cùng lời
gọi), luật 0 USD gắn giọng theo data/voices_vi.json (nam ↔ 2 giọng nam, nữ ↔ 2 giọng nữ, vai chính lấy giọng đầu), không ghi đè lựa
chọn của người dùng, quá 2 vai cùng giới → dùng lại giọng kèm biến thể cao độ (ffmpeg sau TTS) + tốc độ ClipAI. Không gọi API thật."""
import copy
import json
import os
import tempfile
import unittest
from unittest import mock

from core import audio_lib, prompts, voice, voice_casting
from core.db import connect
from core.llm_io import store_scene_analysis
from core.pipeline import Pipeline

CONFIG = {"game_codes": ["FF"], "retired": [{"id": 69, "name": "voice Hip VN"}],
          "preferred": [{"id": 72, "name": "voice boy ingame VN", "gender": "male"},
                        {"id": 30168, "name": "Voice Hip VN 2", "gender": "male"},
                        {"id": 71, "name": "Voice girl ingame VN", "gender": "female"},
                        {"id": 70, "name": "Voice Kelly VN", "gender": "female"}]}
ON = {"FEATURE_AUTO_VOICE_CAST": "1"}


def person(name, gender, age="khoảng 25", personality="nóng tính"):
    c = {"name": name, "description": f"{name} mô tả"}
    if gender is not None:
        c["voice_traits"] = {"gender": gender, "age": age, "personality": personality}
    return c


def analysis(people, lines):
    """people: [(name, gender)], lines: [speaker, ...] — one scene whose lines are said in this order."""
    return {"characters": [person(n, g) for n, g in people],
            "scenes": [{"idx": 1, "location": "Bermuda", "time": "Ngày", "characters": [n for n, _ in people], "mood": "căng",
                        "lighting": "nắng", "shot": "MS", "image_prompt": "p",
                        "dialogue": [{"speaker": who, "text": f"Câu {i} của {who}."} for i, who in enumerate(lines, 1)]}]}


class Base(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        self.p.create_scene(self.pid, 1, "CẢNH 1")
        patcher = mock.patch.object(voice, "voice_config", return_value=CONFIG)
        patcher.start()
        self.addCleanup(patcher.stop)

    def prof(self, name):
        return voice.get_profile(self.p.conn.execute("SELECT voice_profile FROM characters WHERE project_id=? AND name=?",
                                                     (self.pid, name)).fetchone())


class TraitParseTests(unittest.TestCase):
    def test_gender_is_checked_against_the_enum_and_synonyms_are_normalised(self):
        self.assertEqual(voice_casting.clean_traits({"gender": "Male", "age": "30", "personality": "lì"})[0]["gender"], "nam")
        self.assertEqual(voice_casting.clean_traits({"gender": "nữ"})[0]["gender"], "nữ")
        self.assertEqual(voice_casting.clean_traits({"gender": "không rõ"})[0]["gender"], "không rõ")
        traits, problems = voice_casting.clean_traits({"gender": "robot", "age": 25})
        self.assertEqual(traits["gender"], "không rõ")
        self.assertTrue(any("robot" in x for x in problems))
        self.assertEqual(traits["age"], "25")

    def test_not_an_object_is_reported_not_silently_dropped(self):
        traits, problems = voice_casting.clean_traits("nam")
        self.assertIsNone(traits)
        self.assertTrue(problems)


class MissingTraitTests(Base):
    def test_a_speaker_without_traits_is_reported(self):
        obj = analysis([("KENTA", "nam"), ("KELLY", None)], ["KENTA", "KELLY"])
        with mock.patch.dict(os.environ, ON):
            store_scene_analysis(self.p, self.pid, obj)
        report = obj["voice_cast"]
        self.assertTrue(any("KELLY" in x and "thiếu" in x for x in report["problems"]))
        self.assertIn("KELLY", report["unknown"])
        self.assertIsNone(self.prof("KELLY").get("voice_id"))            # no guess for an unknown gender
        rows = self.p.conn.execute("SELECT message FROM diag_events WHERE project_id=?", (self.pid,)).fetchall()
        self.assertTrue(any("KELLY" in r["message"] for r in rows))

    def test_a_traits_failure_with_the_flag_off_is_written_not_raised(self):
        with mock.patch.dict(os.environ, {"FEATURE_AUTO_VOICE_CAST": "0"}),                 mock.patch.object(voice_casting, "store_traits", side_effect=RuntimeError("hỏng")):
            obj = store_scene_analysis(self.p, self.pid, analysis([("KENTA", "nam")], ["KENTA"]))
        self.assertEqual(obj["characters"][0]["name"], "KENTA")
        rows = self.p.conn.execute("SELECT message FROM diag_events WHERE project_id=?", (self.pid,)).fetchall()
        self.assertTrue(any("hỏng" in r["message"] for r in rows))

    def test_traits_are_stored_on_the_character(self):
        with mock.patch.dict(os.environ, ON):
            store_scene_analysis(self.p, self.pid, analysis([("KENTA", "nam")], ["KENTA"]))
        row = self.p.conn.execute("SELECT voice_traits FROM characters WHERE name='KENTA'").fetchone()
        self.assertEqual(json.loads(row["voice_traits"])["gender"], "nam")

    def test_flag_off_changes_nothing(self):
        with mock.patch.dict(os.environ, {"FEATURE_AUTO_VOICE_CAST": "0"}):
            obj = analysis([("KENTA", "nam")], ["KENTA"])
            store_scene_analysis(self.p, self.pid, obj)
            self.assertIsNone(self.prof("KENTA").get("voice_id"))
            self.assertNotIn(voice_casting.PROMPT_MARK, prompts.build_director_bundle(self.p, self.pid))
        with mock.patch.dict(os.environ, ON):
            self.assertIn(voice_casting.PROMPT_MARK, prompts.build_director_bundle(self.p, self.pid))


class RuleTests(Base):
    def test_male_and_female_get_their_voices_and_the_main_role_gets_the_first(self):
        # KELLY speaks most among the women, MAXIM most among the men
        lines = ["KENTA", "MAXIM", "MAXIM", "KELLY", "KELLY", "MISA"]
        with mock.patch.dict(os.environ, ON):
            store_scene_analysis(self.p, self.pid, analysis([("KENTA", "nam"), ("MAXIM", "nam"), ("KELLY", "nữ"), ("MISA", "nữ")], lines))
        self.assertEqual(self.prof("MAXIM")["voice_id"], 72)
        self.assertEqual(self.prof("KENTA")["voice_id"], 30168)
        self.assertEqual(self.prof("KELLY")["voice_id"], 71)
        self.assertEqual(self.prof("MISA")["voice_id"], 70)
        for n in ("KENTA", "MAXIM", "KELLY", "MISA"):
            self.assertTrue(self.prof(n)["auto"])
            self.assertNotIn("variant", self.prof(n))
        self.assertIn("nam", self.prof("MAXIM")["persona"])

    def test_more_than_two_of_one_gender_reuse_a_voice_with_different_pitch(self):
        people = [("A", "nam"), ("B", "nam"), ("C", "nam"), ("D", "nam"), ("E", "nam")]
        with mock.patch.dict(os.environ, ON):
            obj = analysis(people, ["A", "A", "A", "A", "B", "B", "B", "C", "C", "D", "E"])
            store_scene_analysis(self.p, self.pid, obj)
        profs = {n: self.prof(n) for n, _ in people}
        self.assertEqual(profs["A"]["voice_id"], 72)
        self.assertEqual(profs["B"]["voice_id"], 30168)
        by_voice = {}
        for n, pr in profs.items():
            by_voice.setdefault(pr["voice_id"], []).append((pr.get("variant") or {}).get("pitch", 0))
        for vid, pitches in by_voice.items():
            self.assertEqual(len(pitches), len(set(pitches)), f"giọng {vid} trùng cao độ: {pitches}")
        for n in ("C", "D", "E"):
            self.assertTrue(2 <= abs(profs[n]["variant"]["pitch"]) <= 3)
        self.assertTrue(obj["voice_cast"]["shared"])
        shared = voice_casting.shared_voices(self.p.conn, self.pid)
        self.assertIn("A", shared[72]) and self.assertIn("C", shared[72])

    def test_a_person_s_choice_is_never_overwritten_even_by_a_new_analysis(self):
        obj = analysis([("KENTA", "nam"), ("KELLY", "nữ")], ["KENTA", "KELLY"])
        with mock.patch.dict(os.environ, ON):
            store_scene_analysis(self.p, self.pid, copy.deepcopy(obj))
            voice.set_profile(self.p.conn, self.pid, "KENTA", {"voice_id": 70, "voice_name": "Voice Kelly VN", "persona": "tự chọn"})
            store_scene_analysis(self.p, self.pid, copy.deepcopy(obj))
            voice_casting.apply(self.p.conn, self.pid)
        self.assertEqual(self.prof("KENTA")["voice_id"], 70)
        self.assertNotIn("auto", self.prof("KENTA"))
        self.assertEqual(self.prof("KENTA")["persona"], "tự chọn")

    def test_an_auto_voice_stays_put_on_a_new_analysis(self):
        obj = analysis([("A", "nam"), ("B", "nam")], ["A", "B", "B"])
        with mock.patch.dict(os.environ, ON):
            store_scene_analysis(self.p, self.pid, copy.deepcopy(obj))
            first = {n: self.prof(n)["voice_id"] for n in ("A", "B")}
            again = analysis([("A", "nam"), ("B", "nam")], ["A", "A", "A", "B"])      # now A speaks more
            store_scene_analysis(self.p, self.pid, again)
        self.assertEqual({n: self.prof(n)["voice_id"] for n in ("A", "B")}, first)     # no re-paid TTS for a reshuffle

    def test_the_rule_skips_a_voice_the_person_already_gave_someone(self):
        with mock.patch.dict(os.environ, ON):
            store_scene_analysis(self.p, self.pid, analysis([("A", "nam"), ("B", "nam")], ["A"]))   # B no line yet
            voice.set_profile(self.p.conn, self.pid, "A", {"voice_id": 30168, "voice_name": "Voice Hip VN 2"})
            store_scene_analysis(self.p, self.pid, analysis([("A", "nam"), ("B", "nam")], ["A", "B"]))
        self.assertEqual(self.prof("B")["voice_id"], 72)
        self.assertNotIn("variant", self.prof("B"))

    def test_an_auto_voice_whose_gender_became_unknown_is_kept_and_counted(self):
        with mock.patch.dict(os.environ, ON):
            store_scene_analysis(self.p, self.pid, analysis([("A", "nam"), ("B", "nam")], ["A", "A", "B"]))
            obj = analysis([("A", "không rõ"), ("B", "nam"), ("C", "nam")], ["A", "A", "B", "C"])
            store_scene_analysis(self.p, self.pid, obj)
        self.assertEqual(self.prof("A")["voice_id"], 72)                       # kept: no re-paid TTS
        self.assertIn("A", obj["voice_cast"]["kept"])
        self.assertNotIn("A", obj["voice_cast"]["unknown"])
        self.assertFalse(any(x.startswith("A:") and "chưa tự gắn" in x for x in obj["voice_cast"]["problems"]))
        self.assertEqual(self.prof("C")["voice_id"], 72)                       # 72 counted as used by A → C gets a variant
        self.assertIn("variant", self.prof("C"))

    def test_no_preferred_voice_file_is_reported(self):
        with mock.patch.dict(os.environ, ON), mock.patch.object(voice, "voice_config", return_value={}):
            obj = analysis([("A", "nam")], ["A"])
            store_scene_analysis(self.p, self.pid, obj)
        self.assertTrue(any("voices_vi.json" in x for x in obj["voice_cast"]["problems"]))
        self.assertIsNone(self.prof("A").get("voice_id"))


def fake_ffmpeg(cmd):
    """Writes the input + the filter, so pitching twice from the original gives the same bytes and pitching a pitched file does not."""
    with open(cmd[cmd.index("-i") + 1], "rb") as f:
        data = f.read()
    with open(cmd[-1], "wb") as f:
        f.write(data + b"|" + cmd[cmd.index("-af") + 1].encode())


def read(d, name):
    with open(os.path.join(d, name), "rb") as f:
        return f.read()


class Prov:
    name = "mock"

    def status(self, kind, asset_id):
        return mock.Mock(state="succeeded", url="u", duration_ms=1200)

    def download(self, url, dest):
        with open(dest, "wb") as f:
            f.write(b"x")


class PitchTests(unittest.TestCase):
    def test_the_pitch_command_keeps_the_length(self):
        cmd = voice_casting.build_pitch_cmd("in.mp3", "out.mp3", 3, ffmpeg="ffmpeg")
        spec = cmd[cmd.index("-af") + 1]
        ratio = 2 ** (3 / 12)
        self.assertIn(f"asetrate={44100 * ratio:.0f}", spec)
        self.assertIn(f"atempo={1 / ratio:.6f}", spec)
        self.assertEqual(cmd[-1], "out.mp3")

    def test_rendering_twice_gives_the_same_file_from_the_kept_original(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "tts_1.mp3"), "wb") as f:
            f.write(b"raw")
        e = {"file": "tts_1.mp3", "pitch_semitones": -2.5}
        with mock.patch("core.ffmpeg_studio.run", side_effect=fake_ffmpeg) as run,                 mock.patch("core.ffmpeg_studio.find_ffmpeg", return_value="ff"):
            self.assertTrue(voice_casting.render_pitch(d, e))
            first = read(d, "tts_1.mp3")
            self.assertTrue(voice_casting.render_pitch(d, e))           # a second refresh (UI + autopilot at once)
        self.assertEqual(read(d, "tts_1.mp3"), first)                   # not pitched twice
        self.assertEqual(read(d, e["raw_file"]), b"raw")                 # the download stays untouched
        self.assertIn(f"asetrate={44100 * 2 ** (-2.5 / 12):.0f}".encode(), first)
        tmps = [c.args[0][-1] for c in run.call_args_list]
        self.assertEqual(len(set(tmps)), 2)                              # each run its own temp file
        self.assertEqual(sorted(os.listdir(d)), ["tts_1.mp3", "tts_1.raw.mp3"])
        e["pitch_semitones"] = None                                      # back to the plain voice: copied from the original
        voice_casting.render_pitch(d, e)
        self.assertEqual(read(d, "tts_1.mp3"), b"raw")

    def test_a_finished_line_with_a_variant_is_pitched_after_download(self):
        d = tempfile.mkdtemp()
        audio_lib._add(d, "tts", "l", "a1", extra={"pitch_semitones": 3})
        audio_lib._add(d, "tts", "l2", "a2")
        with mock.patch("core.ffmpeg_studio.run", side_effect=fake_ffmpeg), mock.patch("core.ffmpeg_studio.find_ffmpeg", return_value="ff"):
            audio_lib.refresh(Prov(), d)
        e = audio_lib.load(d)[0]
        self.assertEqual(e["pitch_applied"], 3)
        self.assertEqual(read(d, e["raw_file"]), b"x")
        self.assertNotEqual(read(d, e["file"]), b"x")
        self.assertEqual(read(d, audio_lib.load(d)[1]["file"]), b"x")      # no variant: untouched, no raw copy
        self.assertNotIn("raw_file", audio_lib.load(d)[1])

    def test_a_failed_pitch_is_written_on_the_line_cleaned_up_and_retried_later(self):
        d = tempfile.mkdtemp()
        audio_lib._add(d, "tts", "l", "a1", extra={"pitch_semitones": -3})

        def broken(cmd):
            with open(cmd[-1], "wb") as f:
                f.write(b"half")
            raise RuntimeError("ffmpeg hỏng")
        with mock.patch("core.ffmpeg_studio.run", side_effect=broken), mock.patch("core.ffmpeg_studio.find_ffmpeg", return_value="ff"):
            audio_lib.refresh(Prov(), d)
        e = audio_lib.load(d)[0]
        self.assertTrue(e["pitch_failed"])
        self.assertIn("cao độ", e["message"])
        self.assertEqual(read(d, e["file"]), b"x")                        # the plain voice is there meanwhile
        self.assertFalse([n for n in os.listdir(d) if ".tmp" in n])       # no temp file left behind
        with mock.patch("core.ffmpeg_studio.run", side_effect=fake_ffmpeg), mock.patch("core.ffmpeg_studio.find_ffmpeg", return_value="ff"):
            audio_lib.refresh(Prov(), d)                                  # 0 USD: re-pitched from the original
        e = audio_lib.load(d)[0]
        self.assertFalse(e["pitch_failed"])
        self.assertEqual(e["pitch_applied"], -3)



class GenerateTests(Base):
    def test_a_variant_line_goes_to_tts_with_its_speed_and_pitch_tag(self):
        sent = []

        class Prov:
            name = "mock"

            def generate_tts(self, text, voice_id, model, lang, name="", params=None):
                sent.append((voice_id, params))
                return f"t{len(sent)}"
        with mock.patch.dict(os.environ, ON):
            store_scene_analysis(self.p, self.pid, analysis([("A", "nam"), ("B", "nam"), ("C", "nam")], ["A", "A", "B", "C"]))
            d = tempfile.mkdtemp()
            voice.generate(self.p.conn, self.pid, Prov(), d, ledger=False, settle=False)
        items = audio_lib.load(audio_lib.assets_dir(d, self.pid))
        c = [e for e in items if e.get("speaker") == "C"][0]
        self.assertEqual(c["voice_id"], 72)
        self.assertEqual(c["pitch_semitones"], self.prof("C")["variant"]["pitch"])
        self.assertEqual(sent[-1][1]["speed"], self.prof("C")["variant"]["speed"])
        a = [e for e in items if e.get("speaker") == "A"][0]
        self.assertNotIn("pitch_semitones", a)

    def test_only_a_changed_pitch_is_re_pitched_never_sent_to_tts_again(self):
        sent = []

        class Tts(Prov):
            def generate_tts(self, text, voice_id, model, lang, name="", params=None):
                sent.append(text)
                return f"t{len(sent)}"
        d = tempfile.mkdtemp()
        with mock.patch.dict(os.environ, ON), mock.patch("core.ffmpeg_studio.run", side_effect=fake_ffmpeg),                 mock.patch("core.ffmpeg_studio.find_ffmpeg", return_value="ff"):
            store_scene_analysis(self.p, self.pid, analysis([("A", "nam"), ("B", "nam"), ("C", "nam")], ["A", "A", "B", "C"]))
            voice.generate(self.p.conn, self.pid, Tts(), d, ledger=False, settle=False)
            audio_lib.refresh(Tts(), audio_lib.assets_dir(d, self.pid))
            paid = len(sent)
            # the person saves C's voice again (same voice, persona edited) through the screen's helper → the variant stays
            prof = self.prof("C")
            voice.set_profile(self.p.conn, self.pid, "C", voice_casting.saved_profile(prof, prof["voice_id"], prof["voice_name"], "khác"))
            self.assertEqual(self.prof("C")["variant"], prof["variant"])
            self.assertNotIn("auto", self.prof("C"))
            voice.generate(self.p.conn, self.pid, Tts(), d, ledger=False, settle=False)
            self.assertEqual(len(sent), paid)
            # defence: the variant itself changes (or is lost) → only re-pitched from the original, 0 USD
            voice.set_profile(self.p.conn, self.pid, "C", {"voice_id": prof["voice_id"], "voice_name": prof["voice_name"]})
            out = voice.generate(self.p.conn, self.pid, Tts(), d, ledger=False, settle=False)
        self.assertEqual(len(sent), paid)
        self.assertEqual(out["sent"], 0)
        c = [e for e in audio_lib.load(audio_lib.assets_dir(d, self.pid)) if e.get("speaker") == "C"][0]
        self.assertIsNone(c.get("pitch_semitones"))
        self.assertEqual(read(audio_lib.assets_dir(d, self.pid), c["file"]), b"x")   # back to the plain download


class ScreenTests(unittest.TestCase):
    """Character Bible (giao diện cũ và v2 dùng chung step1_characters): vai dùng chung giọng được nói rõ; nút luật 0 USD chỉ gắn vai
    chưa có giọng; nút '🤖 Claude chọn giọng' không đổi (khóa cast_{pid})."""

    def page(db, pid):  # noqa: N805 - run by AppTest.from_function
        import os
        import streamlit as st
        from core import voice
        from core.db import connect
        from core.pipeline import Pipeline
        from dashboard.steps import step1_characters as S
        p = Pipeline(connect(db))
        rows = p.conn.execute("SELECT * FROM characters WHERE project_id=?", (pid,)).fetchall()
        speakers = {ln["speaker"].upper() for ln in voice.planned_lines(p.conn, pid) if ln["speaker"]}
        S.voice_rule_box(p, pid, rows, speakers, data_dir=os.path.dirname(db))
        for r in rows:
            S.voice_cast_note(p, pid, r, voice.get_profile(r))
        st.session_state["_profiles"] = {r["name"]: voice.get_profile(r).get("voice_id") for r in
                                         p.conn.execute("SELECT * FROM characters WHERE project_id=?", (pid,))}

    def test_shared_voices_are_named_and_the_rule_button_fills_only_empty_roles(self):
        from streamlit.testing.v1 import AppTest
        db = os.path.join(tempfile.mkdtemp(), "v.sqlite")
        p = Pipeline(connect(db))
        pid = p.create_project("t")
        p.create_scene(pid, 1, "CẢNH 1")
        with mock.patch.object(voice, "voice_config", return_value=CONFIG), mock.patch.dict(os.environ, {"FEATURE_AUTO_VOICE_CAST": "0"}):
            store_scene_analysis(p, pid, analysis([("A", "nam"), ("B", "nam"), ("C", "nam")], ["A", "A", "B", "C"]))
        voice.set_profile(p.conn, pid, "A", {"voice_id": 72, "voice_name": "voice boy ingame VN", "persona": "tự chọn"})
        voice.set_profile(p.conn, pid, "B", {"voice_id": 72, "voice_name": "voice boy ingame VN",
                                             "auto": True, "variant": {"pitch": 3, "speed": 1.05}})
        audio_lib._add(audio_lib.assets_dir(os.path.dirname(db), pid), "tts", "l", "a1",
                       extra={"speaker": "B", "dialogue": True, "scene_id": 1, "pitch_semitones": 3, "pitch_failed": True})
        with mock.patch.object(voice, "voice_config", return_value=CONFIG), mock.patch.dict(os.environ, ON):
            at = AppTest.from_function(ScreenTests.page, args=(db, pid), default_timeout=40).run()
            self.assertFalse(at.exception)
            text = " ".join(c.value for c in at.caption)
            self.assertIn("Vai dùng chung giọng", text)
            self.assertIn("B (biến thể +3 nửa cung", text)
            self.assertIn("A (gốc)", text)
            self.assertTrue(any("chưa chỉnh được cao độ" in w.value and "B" in w.value for w in at.warning))
            at.button(key=f"vrule_{pid}").click().run()
            self.assertFalse(at.exception)
        self.assertEqual(at.session_state["_profiles"]["A"], 72)            # the person's choice kept
        self.assertEqual(at.session_state["_profiles"]["C"], 30168)         # the empty role got the free male voice


if __name__ == "__main__":
    unittest.main()
