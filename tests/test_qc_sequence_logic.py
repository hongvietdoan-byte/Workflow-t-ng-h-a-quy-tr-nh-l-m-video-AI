"""QC logic cả chuỗi clip (core/sequence_logic.py, cờ qc_sequence_logic) — client giả, 0 USD."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from core import llm_io, sequence_logic
from core.db import connect
from core.llm_runner import LlmReply
from core.pipeline import Pipeline

ON = {"FEATURE_QC_SEQUENCE_LOGIC": "1"}
OFF = {"FEATURE_QC_SEQUENCE_LOGIC": "0"}


class FakeClient:
    """Records every call; answers the given JSON (or a function of the prompt)."""
    name = "fake"

    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def complete(self, prompt, images=()):
        self.calls.append((prompt, list(images)))
        obj = self.answer(prompt) if callable(self.answer) else self.answer
        return LlmReply("```json\n" + json.dumps(obj, ensure_ascii=False) + "\n```", 100, 50)


def _png(path, color):
    from PIL import Image
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.new("RGB", (64, 36), color).save(path)


def project(data, shots):
    """shots: [(sequence, action, has_image)] in story order → (pipeline, project id)."""
    p = Pipeline(connect())
    pid = p.create_project("seq", aspect="16:9")
    for n, (seq, action, has_image) in enumerate(shots, start=1):
        sid = p.add_scene_next(pid, f"shot {n}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"sequence": seq, "action": action, "location": "mê cung"},
                                                                         ensure_ascii=False), sid))
        if has_image:
            jid = p.create_job(sid, "image_gen")
            p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (jid,))
            _png(os.path.join(data, str(pid), "images", f"job_{jid}.png"), (n * 20, 40, 40))
    p.conn.commit()
    return p, pid


class SequenceLogicTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.data, True)

    def test_flag_off_changes_nothing(self):
        p, pid = project(self.data, [(2, "a", True), (2, "b", True)])
        client = FakeClient({"ok": True, "summary": "", "issues": []})
        with mock.patch.dict(os.environ, OFF):
            self.assertEqual(sequence_logic.check(p, pid, client, self.data), {"skipped": "flag_off"})
        self.assertEqual(client.calls, [])
        self.assertFalse(os.path.exists(os.path.join(self.data, str(pid), "qc_set")))
        self.assertIsNone(sequence_logic.last_result(self.data, pid))

    def test_flag_is_declared_off_by_default(self):
        from core import features
        self.assertIn(sequence_logic.FLAG, features.FEATURES)
        self.assertFalse(features.FEATURES[sequence_logic.FLAG]["verified"])
        self.assertFalse(features.FEATURES[sequence_logic.FLAG].get("default_on"))

    def test_sheet_rows_follow_story_order_three_cells_per_shot(self):
        shots = [(2, f"hành động {n}", True) for n in range(1, 7)] + [(3, "x", True), (3, "y", True), (4, "lẻ", True)]
        p, pid = project(self.data, shots)
        seen = []

        def fake_storyboard(frames, out_path, cols=3, cell=(480, 270)):
            seen.append((os.path.basename(out_path), cols, [c for _, c in frames]))
            return out_path
        with mock.patch("core.layout.storyboard", side_effect=fake_storyboard):
            groups = sequence_logic.sequence_sheets(p, pid, self.data)
        self.assertEqual(sorted(groups), ["2", "3"])                  # nhóm 4 chỉ 1 shot: không có gì để nối
        self.assertEqual(len(groups["2"]["sheets"]), 2)               # 6 shot / 4 mỗi tờ
        self.assertEqual([r["idx"] for r in groups["2"]["rows"]], [1, 2, 3, 4, 5, 6])
        first = seen[0]
        self.assertEqual(first[1], 3)                                 # một hàng = một shot
        self.assertEqual(len(first[2]), 3 * sequence_logic.SHOTS_PER_SHEET)
        labels = [c for c in first[2] if c]
        self.assertEqual(labels, [f"S{n:02d} ANH DUYET (chua co clip)" for n in range(1, 5)])
        self.assertEqual([c for c in seen[1][2] if c], [f"S{n:02d} ANH DUYET (chua co clip)" for n in (5, 6)])

    def test_clip_gives_start_middle_end_in_order(self):
        if not shutil.which("ffmpeg"):
            from core.ffmpeg_studio import find_ffmpeg
            if not find_ffmpeg():
                self.skipTest("ffmpeg not installed")
        from core.ffmpeg_studio import find_ffmpeg
        p, pid = project(self.data, [(2, "a", True), (2, "b", True)])
        clip = os.path.join(self.data, str(pid), "videos", "01.mp4")
        os.makedirs(os.path.dirname(clip), exist_ok=True)
        subprocess.run([find_ffmpeg(), "-y", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=10", "-t", "2", "-pix_fmt", "yuv420p", clip],
                       capture_output=True)
        if not os.path.exists(clip):
            self.skipTest("ffmpeg could not make a test clip")
        seen = []
        with mock.patch("core.layout.storyboard", side_effect=lambda frames, out, cols=3, cell=None: seen.append(frames) or out):
            sequence_logic.sequence_sheets(p, pid, self.data)
        caps = [c for _, c in seen[0]]
        self.assertEqual(caps[:3], ["S01 dau", "S01 giua", "S01 cuoi"])
        self.assertTrue(all(os.path.exists(path) for path, _ in seen[0][:3]))
        self.assertEqual(caps[3], "S02 ANH DUYET (chua co clip)")

    def test_check_sends_sheets_and_rows_and_saves_result(self):
        p, pid = project(self.data, [(2, "Kelly nhặt súng ở mặt đất", True), (2, "Kelly bắn", True), (2, "vừa hạ gục Xúc Tu Đỏ", False)])
        answer = {"ok": False, "summary": "thiếu shot", "issues": [{"idx": 3, "kind": "thieu_shot", "problem": "không có shot hạ gục",
                                                                     "fix": "KỊCH BẢN: thêm shot"}]}
        client = FakeClient(answer)
        with mock.patch.dict(os.environ, ON):
            out = sequence_logic.check(p, pid, client, self.data)
        self.assertEqual(len(client.calls), 1)                        # một lời gọi / nhóm
        prompt, images = client.calls[0]
        self.assertIn("QC logic cả chuỗi clip", prompt)
        self.assertIn("vừa hạ gục Xúc Tu Đỏ", prompt)                # shot không có hình vẫn vào bảng (has_picture false)
        self.assertIn('"has_picture": false', prompt)
        self.assertEqual(len(images), 1)
        self.assertTrue(os.path.exists(images[0][1]))
        self.assertFalse(out["ok"])
        self.assertEqual(out["sequences"]["2"]["issues"][0]["idx"], 3)
        self.assertEqual(sequence_logic.last_result(self.data, pid)["sequences"]["2"]["summary"], "thiếu shot")

    def test_prompt_names_the_real_31_cases(self):
        """#31 19/10 (người dùng): mỗi ca lỗi thật phải có trong prompt 22 — vật đổi độ cao, địch tạo dáng / không gục, bắn khi hết
        mục tiêu + tường keo vỡ tan, shot không mục đích / không nối tư thế, việc thoại nhắc tới không có shot."""
        from core import claude_tasks
        text = claude_tasks._read("prompts", "22_sequence_logic.md")
        for case in ("thềm cỏ", "S03-2 → S03-3", "S04-3", "không gục", "S04-5", "hết mục tiêu", "VỠ TAN", "S04-6/7/8",
                     "mục đích kể chuyện", "nối được tư thế", "vừa hạ gục"):
            self.assertIn(case, text)
        for kind in ("vat", "het_ly_do", "muc_dich", "noi_tu_the"):
            self.assertIn(f"`{kind}`", text)

    def test_schema(self):
        v = sequence_logic._validator([1, 2])
        v({"ok": True, "summary": "", "issues": []})
        v({"ok": False, "issues": [{"idx": 2, "problem": "p", "fix": "f"}]})
        for bad in ({"issues": []}, {"ok": True, "issues": [{"idx": "2", "problem": "p"}]},
                    {"ok": False, "issues": [{"idx": 9, "problem": "p", "fix": ""}]},      # idx ngoài nhóm
                    {"ok": False, "issues": [{"idx": 1, "problem": "p", "fix": 3}]}):
            with self.assertRaises(llm_io.SchemaError):
                v(bad)

    def test_bad_idx_is_retried_once(self):
        p, pid = project(self.data, [(2, "a", True), (2, "b", True)])
        answers = iter([{"ok": False, "issues": [{"idx": 7, "problem": "p", "fix": ""}]}, {"ok": True, "summary": "", "issues": []}])
        client = FakeClient(lambda prompt: next(answers))
        with mock.patch.dict(os.environ, ON):
            out = sequence_logic.check(p, pid, client, self.data)
        self.assertEqual(len(client.calls), 2)
        self.assertTrue(out["ok"])

    def test_estimate_before_spending(self):
        p, pid = project(self.data, [(2, "a", True)] * 5 + [(3, "b", True), (3, "c", False)])
        calls, usd = sequence_logic.estimate(p, pid, self.data)
        self.assertEqual(calls, 1)                                    # nhóm 3 chỉ 1 shot có hình
        self.assertIsNotNone(usd)
        self.assertGreater(usd, 0)
        self.assertFalse(os.path.exists(os.path.join(self.data, str(pid), "qc_set")))   # ước tính không trích khung


if __name__ == "__main__":
    unittest.main()
