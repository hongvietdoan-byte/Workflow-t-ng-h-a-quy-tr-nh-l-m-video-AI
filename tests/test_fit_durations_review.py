"""V3.1 M2.9 G14 (cờ fit_durations_review, TẮT): kéo thời lượng clip theo giọng thật = ĐỀ XUẤT + DUYỆT. Chỉ mock (giọng / Claude giả)."""
import json
import os
from unittest import mock

from core import audio_lib, llm_runner, voice
from core.music import MockAudioProvider
from tests.test_v2 import Base


class FitReviewTests(Base):
    def setUp(self):
        super().setUp()
        for name in ("KENTA", "KELLY", "MAXIM"):
            voice.set_profile(self.p.conn, self.pid, name, {"voice_id": 1, "voice_name": "Mock"})
        audio = MockAudioProvider()
        voice.generate(self.p.conn, self.pid, audio, self.data)
        audio_lib.refresh(audio, audio_lib.assets_dir(self.data, self.pid))
        self.approve_images()
        llm_runner.run_motion(self.p, self.pid, llm_runner.MockLlm(), self.data)
        self.p.conn.execute("UPDATE motion_prompts SET duration_sec=1")
        self.p.conn.commit()
        self.voiced = sorted(voice.scene_seconds(self.p.conn, self.pid, self.data))
        self.assertGreaterEqual(len(self.voiced), 2)
        self.narr, self.talk = self.voiced[0], self.voiced[1:]
        row = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.narr,)).fetchone()
        data = json.loads(row["data"] or "{}")
        for d in data.get("dialogue") or []:
            d["speaker"] = "LỜI DẪN"                     # shot chỉ lời dẫn (giọng đã có, giây giữ nguyên)
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), self.narr))
        self.p.conn.commit()

    def _durations(self):
        return {r["scene_id"]: r["duration_sec"] for r in self.p.conn.execute("SELECT scene_id, duration_sec FROM motion_prompts")}

    def test_plan_fit_writes_nothing_and_gives_the_reason(self):
        before = self._durations()
        plan = voice.plan_fit(self.p.conn, self.pid, self.data)
        self.assertEqual(self._durations(), before)
        by = {c["scene_id"]: c for c in plan}
        self.assertEqual(by[self.narr]["ly_do"], "chi_loi_dan")
        self.assertFalse(by[self.narr]["tick"])
        for sid in self.talk:
            self.assertEqual(by[sid]["ly_do"], "thoai_trong_khung")
            self.assertTrue(by[sid]["tick"])
        for c in plan:
            self.assertEqual(set(c), {"scene_id", "idx", "from", "to", "short", "ly_do", "tien_them_usd", "tick"})
            self.assertGreater(c["to"], c["from"])

    def test_apply_fit_changes_only_the_chosen_shots(self):
        plan = voice.plan_fit(self.p.conn, self.pid, self.data)
        chosen = [c for c in plan if c["scene_id"] == self.talk[0]]
        ch = voice.apply_fit(self.p.conn, chosen)
        self.assertEqual([c["scene_id"] for c in ch], [self.talk[0]])
        d = self._durations()
        self.assertEqual(d[self.talk[0]], chosen[0]["to"])
        self.assertEqual(d[self.narr], 1)

    def test_flag_on_automatic_fit_leaves_narration_only_shots(self):
        with mock.patch.dict(os.environ, {"FEATURE_FIT_DURATIONS_REVIEW": "1"}):
            ch = voice.fit_durations(self.p.conn, self.pid, self.data)
        self.assertEqual(sorted(c["scene_id"] for c in ch), self.talk)
        self.assertEqual(self._durations()[self.narr], 1)

    def test_flag_off_is_the_old_fit(self):
        with mock.patch.dict(os.environ, {"FEATURE_FIT_DURATIONS_REVIEW": "0"}):
            ch = voice.fit_durations(self.p.conn, self.pid, self.data)
        self.assertEqual(sorted(c["scene_id"] for c in ch), self.voiced)
        self.assertEqual(set(ch[0]), {"scene_id", "from", "to", "short"})

    def test_review_panel_ticks_only_talking_shots_and_writes_only_on_apply(self):
        from dashboard.steps import step3
        with mock.patch.object(step3, "st") as st, mock.patch.object(step3.C, "DATA", self.data):
            st.checkbox.side_effect = lambda label, value, key: value
            st.button.return_value = False
            step3._fit_review(self.p, self.pid, mock.Mock())
            ticks = {c.kwargs["key"]: c.kwargs["value"] for c in st.checkbox.call_args_list}
            self.assertFalse(ticks[f"fit_{self.pid}_{self.narr}"])
            self.assertTrue(all(ticks[f"fit_{self.pid}_{sid}"] for sid in self.talk))
            self.assertTrue(all("(ước tính)" in c.args[0] or "chưa có giá" in c.args[0] for c in st.checkbox.call_args_list))
            self.assertEqual(self._durations()[self.narr], 1)                 # chưa bấm Áp dụng: không ghi
            st.button.return_value = True
            step3._fit_review(self.p, self.pid, mock.Mock())
        d = self._durations()
        self.assertEqual(d[self.narr], 1)
        self.assertTrue(all(d[sid] > 1 for sid in self.talk))

    def test_flag_on_narration_shot_with_a_clip_does_not_hold_the_automatic_run(self):
        """Cờ BẬT: shot chỉ lời dẫn không được tự kéo → khi đã có clip, pending_fits không được giữ chạy tự động (_Wait voice_fit) vì
        nó; shot thoại trong khung vẫn hỏi người như cũ."""
        for sid in self.voiced:
            jid = self.p.create_job(sid, "video_gen")
            self.p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (jid,))
        self.p.conn.commit()
        with mock.patch.dict(os.environ, {"FEATURE_FIT_DURATIONS_REVIEW": "0"}):
            self.assertIn(self.narr, [c["scene_id"] for c in voice.pending_fits(self.p.conn, self.pid, self.data)])
        with mock.patch.dict(os.environ, {"FEATURE_FIT_DURATIONS_REVIEW": "1"}):
            late = [c["scene_id"] for c in voice.pending_fits(self.p.conn, self.pid, self.data)]
        self.assertNotIn(self.narr, late)
        self.assertEqual(sorted(late), self.talk)
