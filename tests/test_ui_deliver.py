"""UI v2 (S13, lane G) — Bản giao screen: hero card + three chips, final-check pills, every old control still reachable, flag OFF = classic."""
import os
import tempfile
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from core import delivery, subtitles
from core.db import connect
from core.pipeline import Pipeline
from tests.test_ui_video import APP, STEP_DELIVER, V2, md


class DeliverSeed(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        self.data = os.path.join(self.tmp, "projects")
        patcher = mock.patch.dict(os.environ, {"PIPELINE_DB": self.db, "PIPELINE_DATA": self.data,
                                               "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "k"), "AUDIO_PROVIDER": "mock"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.p = Pipeline(connect(self.db))
        self.pid = self.p.create_project("Demo giao")
        self.p.create_scene(self.pid, 1, "CẢNH 1")

    def with_clip(self):
        videos = os.path.join(self.data, str(self.pid), "videos")
        os.makedirs(videos, exist_ok=True)
        with open(os.path.join(videos, "01.mp4"), "wb") as f:
            f.write(b"not a real video")

    def open_deliver(self, v2=True, state=None) -> AppTest:
        with mock.patch.dict(os.environ, dict(V2) if v2 else {"FEATURE_UI_V2": "0"}):
            at = AppTest.from_file(APP, default_timeout=60)
            for k, v in (state or {}).items():
                at.session_state[k] = v
            at.session_state[f"fold_render_set_{self.pid}"] = True            # the folded render settings / clip list (S9 E5.1 / E5.6)
            at.session_state[f"fold_clips_{self.pid}"] = True
            at.run()
            at.radio(key="step").set_value(at.radio(key="step").options[STEP_DELIVER]).run()
        self.assertFalse(at.exception, at.exception)
        return at


class DeliverV2Tests(DeliverSeed):
    def test_hero_card_has_one_primary_export_button_and_the_tuning_card(self):
        self.with_clip()
        at = self.open_deliver()
        html = md(at)
        self.assertIn("Xuất bản đầy đủ", html)
        self.assertIn("Tinh chỉnh", html)
        deliver = next(b for b in at.button if b.key == f"deliver_{self.pid}")
        self.assertFalse(deliver.disabled)
        self.assertEqual(deliver.proto.type, "primary")
        self.assertEqual(deliver.label, "📦 Xuất bản đầy đủ")

    def test_three_chips_are_the_real_widgets_with_the_old_keys(self):
        self.with_clip()
        at = self.open_deliver()
        self.assertEqual(at.checkbox(key=f"sub_auto_{self.pid}").label, "Luôn thêm phụ đề khi xuất bản (cả chế độ tự động)")
        self.assertEqual(at.checkbox(key=f"card_on_{self.pid}").label, "Thêm card cuối khi xuất bản")
        self.assertTrue(at.selectbox(key=f"exp_preset_{self.pid}").options)
        # each key exists exactly once (the panels do not draw a second copy)
        self.assertEqual(sum(1 for c in at.checkbox if c.key == f"sub_auto_{self.pid}"), 1)

    def test_chips_save_into_the_project_settings(self):
        self.with_clip()
        at = self.open_deliver()
        at.checkbox(key=f"sub_auto_{self.pid}").set_value(True).run()
        at.checkbox(key=f"card_on_{self.pid}").set_value(True).run()
        self.assertFalse(at.exception)
        p = Pipeline(connect(self.db))
        self.assertTrue(subtitles.get_settings(p, self.pid)["enabled"])
        self.assertTrue(delivery.get_settings(p, self.pid)["end_card"]["enabled"])

    def test_every_old_control_group_is_still_reachable(self):
        self.with_clip()
        at = self.open_deliver()
        pid = self.pid
        for key in (f"sub_lang_{pid}", f"sub_font_{pid}", f"sub_size_{pid}", f"sub_pos_{pid}", f"sub_color_{pid}", f"sub_platform_{pid}",
                    f"exp_fit_{pid}", f"tr_{pid}", f"fade_{pid}", f"vol_{pid}"):
            self.assertTrue(any(getattr(w, "key", None) == key for w in list(at.selectbox) + list(at.radio) + list(at.slider)), key)
        buttons = {b.key for b in at.button}
        for key in (f"render_{pid}", f"sub_make_{pid}", f"card_go_{pid}", f"exp_add_{pid}", f"exp_now_{pid}", f"cover_go_{pid}", f"mbrief_ai_{pid}",
                    f"music_none_{pid}"):
            self.assertIn(key, buttons, key)
        self.assertIn(f"card_title_{pid}", {t.key for t in at.text_input})
        self.assertTrue(any(c.label.startswith("Cảnh 1") or "CẢNH 1" in c.label for c in at.checkbox))

    def test_expert_mode_keeps_the_extra_sound_tools(self):
        self.with_clip()
        with mock.patch.dict(os.environ, {"DASHBOARD_EXPERT": "1"}):
            at = self.open_deliver()
        self.assertIn(f"sfx_go_{self.pid}", {b.key for b in at.button})

    def test_final_check_is_shown_as_pills(self):
        self.with_clip()
        res = {"ok": False, "blocks": 1, "warns": 2, "issues": [{"level": "block", "msg": "nhạc tắt giữa chừng"},
                                                                {"level": "warn", "msg": "đỉnh âm lượng cao"},
                                                                {"level": "warn", "msg": "shot quá ngắn"}]}
        at = self.open_deliver(state={f"final_qc_{self.pid}": res})
        html = md(at)
        self.assertIn("1 lỗi chặn", html)
        self.assertIn("2 cảnh báo", html)
        self.assertIn("nhạc tắt giữa chừng", html)
        ok = self.open_deliver(state={f"final_qc_{self.pid}": {"ok": True, "blocks": 0, "warns": 0, "issues": []}})
        self.assertIn("Kiểm bản dựng: đạt", md(ok))

    def test_without_clips_the_export_is_disabled_with_an_empty_state(self):
        at = self.open_deliver()
        self.assertTrue(next(b for b in at.button if b.key == f"deliver_{self.pid}").disabled)
        self.assertIn("Chưa có clip nào để xuất", md(at))
        self.assertIn("Chưa có bản giao", md(at))


class DeliverClassicTests(DeliverSeed):
    def test_flag_off_keeps_the_classic_delivery_card(self):
        self.with_clip()
        at = self.open_deliver(v2=False)
        self.assertNotIn("v2-pill", md(at))
        self.assertTrue(any("Phụ đề" in e.label for e in at.expander))
        self.assertIn(f"deliver_{self.pid}", {b.key for b in at.button})
        self.assertEqual(at.checkbox(key=f"sub_auto_{self.pid}").label, "Luôn thêm phụ đề khi xuất bản (cả chế độ tự động)")


if __name__ == "__main__":
    unittest.main()
