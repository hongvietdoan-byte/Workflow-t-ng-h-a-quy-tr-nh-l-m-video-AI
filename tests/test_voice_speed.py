"""14/10 (#31 tập 2): tốc độ đọc riêng của hồ sơ giọng (lời dẫn 1,2). Hồ sơ giữ `speed` không cần pitch, kẹp 0,7–1,2 + diag VÀNG;
lời gọi TTS gửi speed (× pace câu khi cờ voice_direction bật, × tốc độ biến thể, rồi kẹp); đổi tốc độ làm câu cũ thành CŨ; hồ sơ không
đặt tốc độ gửi payload y hệt trước. Không gọi API thật (nhà cung cấp giả)."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import audio_lib, voice, voice_casting
from core.db import connect
from core.pipeline import Pipeline


class Prov:
    name = "mock"

    def __init__(self):
        self.sent = []

    def generate_tts(self, text, voice_id, model, lang, name="", params=None):
        self.sent.append({"text": text, "voice_id": voice_id, "model": model, "params": params})
        return f"t{len(self.sent)}"


class Base(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        sid = self.p.create_scene(self.pid, 1, "CẢNH 1")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"dialogue": [
            {"speaker": "LỜI DẪN", "text": "Bốn đối thủ ập tới."},
            {"speaker": "KELLY", "text": "Chạy mau lên!", "delivery": {"pace": "fast"}}]}, ensure_ascii=False), sid))
        for n in ("LỜI DẪN", "KELLY"):
            self.p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, ?, ?)", (self.pid, n, n))
        self.p.conn.commit()
        self.d = tempfile.mkdtemp()
        env = mock.patch.dict(os.environ, {"FEATURE_VOICE_DIRECTION": "0"})
        env.start()
        self.addCleanup(env.stop)

    def prof(self, name):
        return voice.get_profile(self.p.conn.execute("SELECT voice_profile FROM characters WHERE project_id=? AND name=?",
                                                     (self.pid, name)).fetchone())

    def gen(self, prov, by_person=False):
        return voice.generate(self.p.conn, self.pid, prov, self.d, ledger=False, settle=False, by_person=by_person)

    def by(self, prov, voice_id):
        return [s for s in prov.sent if s["voice_id"] == voice_id]


class ProfileTests(Base):
    def test_speed_is_kept_without_a_pitch(self):
        voice.set_profile(self.p.conn, self.pid, "LỜI DẪN", {"voice_id": 30169, "voice_name": "dẫn", "speed": 1.2})
        self.assertEqual(self.prof("LỜI DẪN")["speed"], 1.2)

    def test_a_speed_only_variant_is_no_longer_lost(self):
        voice.set_profile(self.p.conn, self.pid, "KELLY", {"voice_id": 70, "variant": {"speed": 1.1}})
        self.assertEqual(self.prof("KELLY")["variant"], {"speed": 1.1})

    def test_out_of_range_is_clamped_and_reported_yellow(self):
        warns = voice.set_profile(self.p.conn, self.pid, "LỜI DẪN", {"voice_id": 30169, "speed": 1.5})
        self.assertEqual(self.prof("LỜI DẪN")["speed"], 1.2)
        self.assertTrue(warns and "1.5" in warns[0])
        row = self.p.conn.execute("SELECT severity, code, stage FROM diag_events WHERE code='voice_speed_clamped'").fetchone()
        self.assertEqual((row["severity"], row["stage"]), ("warn", "voice"))
        voice.set_profile(self.p.conn, self.pid, "KELLY", {"voice_id": 70, "speed": 0.5})
        self.assertEqual(self.prof("KELLY")["speed"], 0.7)

    def test_not_a_number_is_dropped_with_a_warning(self):
        warns = voice.set_profile(self.p.conn, self.pid, "KELLY", {"voice_id": 70, "speed": "nhanh"})
        self.assertNotIn("speed", self.prof("KELLY"))
        self.assertEqual(len(warns), 1)

    def test_default_speed_is_not_saved_and_a_profile_without_speed_key_keeps_the_saved_one(self):
        voice.set_profile(self.p.conn, self.pid, "LỜI DẪN", {"voice_id": 30169, "speed": 1.2})
        voice.set_profile(self.p.conn, self.pid, "LỜI DẪN", {"voice_id": 30169, "persona": "trầm"})   # casting / Claude: no key
        self.assertEqual(self.prof("LỜI DẪN")["speed"], 1.2)
        voice.set_profile(self.p.conn, self.pid, "LỜI DẪN", {"voice_id": 30169, "speed": 1.0})        # the box back to 1,0
        self.assertNotIn("speed", self.prof("LỜI DẪN"))

    def test_saved_profile_carries_the_speed_box(self):
        out = voice_casting.saved_profile({}, 30169, "dẫn", "", speed=1.2)
        self.assertEqual(out["speed"], 1.2)
        self.assertNotIn("speed", voice_casting.saved_profile({}, 30169, "dẫn", ""))


class TtsTests(Base):
    def test_profile_speed_is_sent_to_tts(self):
        voice.set_profile(self.p.conn, self.pid, "LỜI DẪN", {"voice_id": 30169, "speed": 1.2})
        voice.set_profile(self.p.conn, self.pid, "KELLY", {"voice_id": 70})
        prov = Prov()
        self.gen(prov)
        self.assertEqual(self.by(prov, 30169)[0]["params"], {"speed": 1.2})
        self.assertIsNone(self.by(prov, 70)[0]["params"])               # no speed: called exactly as before (no params)

    def test_old_profile_payload_is_unchanged(self):
        """A profile without speed sends the same calls as the code before 14/10 (old rule: tts_params(params(how), variant))."""
        from core import voice_direction
        voice.set_profile(self.p.conn, self.pid, "LỜI DẪN", {"voice_id": 30169})
        voice.set_profile(self.p.conn, self.pid, "KELLY", {"voice_id": 70, "variant": {"pitch": 2.0, "speed": 1.1}})
        for flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FEATURE_VOICE_DIRECTION": flag}):
                for name, how in (("LỜI DẪN", None), ("KELLY", {"pace": "fast"}), ("KELLY", None)):
                    prof = self.prof(name)
                    old = voice_casting.tts_params(voice_direction.params(how, "eleven_v3"), prof.get("variant") or None)
                    self.assertEqual(voice.line_params(how, "eleven_v3", prof), old)

    def test_pace_times_profile_speed_is_clamped(self):
        prof = {"voice_id": 70, "speed": 1.2}
        self.assertEqual(voice.line_params({"pace": "fast"}, "eleven_v3", prof)["speed"], 1.2)       # 1,1 × 1,2 = 1,32 → 1,2
        self.assertEqual(voice.line_params({"pace": "slow"}, "eleven_v3", prof)["speed"], 1.08)      # 0,9 × 1,2
        self.assertEqual(voice.line_params(None, "eleven_v3", {"voice_id": 70, "speed": 0.8,
                                                               "variant": {"pitch": -3.0, "speed": 0.8}})["speed"], 0.7)

    def test_directed_pace_with_flag_on_reaches_the_call(self):
        voice.set_profile(self.p.conn, self.pid, "LỜI DẪN", {"voice_id": 30169})
        voice.set_profile(self.p.conn, self.pid, "KELLY", {"voice_id": 70, "speed": 0.8})
        prov = Prov()
        with mock.patch.dict(os.environ, {"FEATURE_VOICE_DIRECTION": "1"}):
            self.gen(prov)
        self.assertEqual(self.by(prov, 70)[0]["params"]["speed"], 0.88)                                # 1,1 × 0,8

    def test_changing_the_speed_makes_the_old_voice_stale_and_same_speed_is_not_resent(self):
        voice.set_profile(self.p.conn, self.pid, "LỜI DẪN", {"voice_id": 30169})
        voice.set_profile(self.p.conn, self.pid, "KELLY", {"voice_id": 70})
        prov = Prov()
        self.gen(prov)
        self.assertEqual(len(prov.sent), 2)
        self.gen(prov)
        self.assertEqual(len(prov.sent), 2)                                # nothing changed: nothing re-paid
        voice.set_profile(self.p.conn, self.pid, "LỜI DẪN", {"voice_id": 30169, "speed": 1.2})
        stat = voice.status(self.p.conn, self.pid, self.d)
        self.assertEqual(stat["speed_changed"], 1)
        self.assertEqual(stat["missing"], 0)                               # shown, never 'missing' (no automatic re-pay)
        self.assertEqual(self.gen(prov)["sent"], 0)                        # the automatic run keeps the old voice (no re-pay)
        out = self.gen(prov, by_person=True)
        self.assertEqual(out["sent"], 1)
        self.assertEqual(prov.sent[-1]["params"], {"speed": 1.2})
        items = [e for e in audio_lib.load(audio_lib.assets_dir(self.d, self.pid)) if e.get("speaker") == "LỜI DẪN"]
        self.assertEqual([e.get("profile_speed") for e in items], [1.2])
        self.gen(prov)
        self.assertEqual(len(prov.sent), 3)
        voice.set_profile(self.p.conn, self.pid, "LỜI DẪN", {"voice_id": 30169, "speed": 1.0})          # back to default: stale again
        self.assertEqual(self.gen(prov, by_person=True)["sent"], 1)
        self.assertIsNone(prov.sent[-1]["params"])

    def test_automatic_run_for_another_missing_line_does_not_re_pay_a_speed_change(self):
        """Rà 14/10 (1): autopilot / pilot_run call generate when ANOTHER line is missing — the line whose only change is the profile's
        speed must stay as it is (re-read only on the person's 🎙 click), else a speed change is paid without anyone pressing."""
        voice.set_profile(self.p.conn, self.pid, "LỜI DẪN", {"voice_id": 30169})
        voice.set_profile(self.p.conn, self.pid, "KELLY", {"voice_id": 70})
        prov = Prov()
        self.gen(prov)
        directory = audio_lib.assets_dir(self.d, self.pid)
        kelly = [i for i, e in enumerate(audio_lib.load(directory)) if e.get("speaker") == "KELLY"][0]
        audio_lib.remove(directory, kelly)                                 # KELLY's line now missing
        voice.set_profile(self.p.conn, self.pid, "LỜI DẪN", {"voice_id": 30169, "speed": 1.2})
        out = self.gen(prov)
        self.assertEqual([s["voice_id"] for s in prov.sent[2:]], [70])   # only the missing line
        self.assertEqual(out["sent"], 1)
        stat = voice.status(self.p.conn, self.pid, self.d)
        self.assertEqual(stat["speed_changed"], 1)                         # still shown to the person
        self.assertEqual(len(stat["speed_changed_scenes"]), 1)

    def test_clips_made_on_the_old_speed_are_named(self):
        """Rà 14/10 (2): a scene with a clip (lip sync follows the old timing) is named beside the speed warning, not silent."""
        voice.set_profile(self.p.conn, self.pid, "LỜI DẪN", {"voice_id": 30169})
        voice.set_profile(self.p.conn, self.pid, "KELLY", {"voice_id": 70})
        self.gen(Prov())
        sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=?", (self.pid,)).fetchone()["id"]
        voice.set_profile(self.p.conn, self.pid, "LỜI DẪN", {"voice_id": 30169, "speed": 1.2})
        self.assertEqual(voice.speed_changed_clips(self.p.conn, self.pid, self.d), [])
        self.p.conn.execute("INSERT INTO jobs (project_id, scene_id, type, state, created_at, updated_at) "
                            "VALUES (?, ?, 'video_gen', 'succeeded', 'x', 'x')", (self.pid, sid))
        self.p.conn.commit()
        self.assertEqual(voice.speed_changed_clips(self.p.conn, self.pid, self.d), ["S01"])

    def test_pace_variant_and_profile_are_multiplied_then_clamped_once(self):
        """Rà 14/10 (5): 1,1 (fast) × 1,2 (variant) × 0,7 (profile) = 0,924 — not 1,2 (clamped first) × 0,7 = 0,84."""
        prof = {"voice_id": 70, "speed": 0.7, "variant": {"pitch": 2.0, "speed": 1.2}}
        self.assertEqual(voice.line_params({"pace": "fast"}, "eleven_v3", prof)["speed"], 0.924)

    def test_preview_uses_the_profile_speed_and_none_keeps_the_old_call(self):
        prov = Prov()
        voice.preview(prov, self.d, self.pid, 30169, "dẫn", "LỜI DẪN", speed=1.2)
        voice.preview(prov, self.d, self.pid, 30169, "dẫn", "LỜI DẪN")
        self.assertEqual([s["params"] for s in prov.sent], [{"speed": 1.2}, None])
        items = audio_lib.load(voice.previews_dir(self.d, self.pid))
        self.assertEqual([e.get("speed") for e in items], [1.2, None])


class ScreenTests(unittest.TestCase):
    """Character Bible (step1_characters.character_detail_panel): ô 'Tốc độ đọc' 0,7–1,2 bước 0,05 ghi vào hồ sơ."""

    def page(db, pid):  # noqa: N805 - run by AppTest.from_function
        from core.db import connect
        from core.pipeline import Pipeline
        from dashboard.steps import step1_characters as S
        p = Pipeline(connect(db))
        row = p.conn.execute("SELECT * FROM characters WHERE project_id=? AND name='LỜI DẪN'", (pid,)).fetchone()
        S.character_detail_panel(p, pid, row, [{"id": 30169, "name": "Voice dẫn VN"}], None, False)

    def test_speed_box_writes_the_profile(self):
        from streamlit.testing.v1 import AppTest
        db = os.path.join(tempfile.mkdtemp(), "v.sqlite")
        p = Pipeline(connect(db))
        pid = p.create_project("t")
        p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, 'LỜI DẪN', 'dẫn')", (pid,))
        p.conn.commit()
        voice.set_profile(p.conn, pid, "LỜI DẪN", {"voice_id": 30169, "voice_name": "Voice dẫn VN"})
        at = AppTest.from_function(ScreenTests.page, args=(db, pid), default_timeout=40).run()
        self.assertFalse(at.exception)
        box = at.number_input(key=f"voice_speed_{pid}_LỜI DẪN")
        self.assertEqual((box.value, box.min, box.max, box.step), (1.0, 0.7, 1.2, 0.05))
        box.set_value(1.2).run()
        at.button(key=f"voice_save_{pid}_LỜI DẪN").click().run()
        self.assertFalse(at.exception)
        prof = voice.get_profile(Pipeline(connect(db)).conn.execute(
            "SELECT voice_profile FROM characters WHERE project_id=? AND name='LỜI DẪN'", (pid,)).fetchone())
        self.assertEqual((prof["voice_id"], prof["speed"]), (30169, 1.2))


if __name__ == "__main__":
    unittest.main()
