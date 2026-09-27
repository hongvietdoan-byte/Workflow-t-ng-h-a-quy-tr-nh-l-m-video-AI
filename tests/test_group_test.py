"""Grouped generation tests (docs/PHAN_TICH_GOP_SHOT_2026-09-27.md): Seedance "reference only" (P2) sends every picture as
reference_image and no first frame (Seedance refuses the two mixed); the test tool builds its prompts from the Director's fields with
no Claude call and keeps each model's rules (2–4 shots a generation, Kling ≥ 3 s a shot, Seedance ≥ 4 s a clip)."""
import json
import os
import tempfile
import unittest

from core.adapters.clipai import ClipAIVideoProvider
from core.db import connect
from core.pipeline import Pipeline
from core.providers import ProviderError
from tests.test_adapters import TOKEN, FakeTransport, ctx_of, ok
from tools.experiments import group_test


def pngs(n):
    d = tempfile.mkdtemp()
    out = []
    for i in range(n):
        path = os.path.join(d, f"{i}.png")
        with open(path, "wb") as f:
            f.write(b"\x89PNG-" + str(i).encode())
        out.append(path)
    return out


class ReferenceOnlyTests(unittest.TestCase):
    def test_every_picture_is_a_reference_and_no_first_frame(self):
        t = FakeTransport()
        t.on("POST", "/api/kling/seedance-video-submit", ok({"tasks": [{"task_id": "S", "task_status": "submitted"}]}))
        refs = pngs(5)
        task = ClipAIVideoProvider(TOKEN, "https://clipai.example", t).submit(
            "", "Shot 1: … Shot 2: …", None, 7, "seedance-fast", reference_only=refs)
        self.assertEqual(task, "seedance:S")
        roles = [c.get("role") for c in ctx_of(t.calls[0])["content"] if c["type"] == "image_url"]
        self.assertEqual(roles, ["reference_image"] * 5)
        self.assertEqual(t.calls[0]["body"].count(b'name="image_files"'), 5)

    def test_refused_where_the_api_would_refuse(self):
        provider = ClipAIVideoProvider(TOKEN, "https://clipai.example", FakeTransport())
        for kwargs in ({"model": "kling"}, {"model": "seedance-fast", "last_frame": pngs(1)[0]}):
            with self.assertRaises(ProviderError):
                provider.submit("", "x", None, 5, reference_only=pngs(2), **kwargs)
        with self.assertRaises(ProviderError):
            provider.submit("", "x", None, 5, "seedance-fast", reference_only=pngs(10))       # 2.0: at most 9


class FindByPromptTests(unittest.TestCase):
    """Trial 2026-09-27: 6 shot prompts opened with the same 200+ character look sentence; the 200-character prefix match tied the
    six clips to the wrong shots (shot 1 got shot 5's clip …)."""
    LOOK = "Match the look of the reference in-game photo, not a different 3D style. " * 4

    def provider(self, rows):
        p = ClipAIVideoProvider(TOKEN, "https://clipai.example", FakeTransport())
        p._page = lambda family, page: rows
        return p

    def test_whole_prompt_decides_even_with_a_long_shared_opening(self):
        rows = [{"task_id": f"9{k}", "created_at": "2000", "prompt": self.LOOK + f"Shot {k} runs. Avoid: blur"} for k in (5, 1, 3)]
        p = self.provider(rows)
        for k in (1, 3, 5):
            self.assertEqual(p.find_by_prompt("omni:123456789012", self.LOOK + f"Shot {k} runs.", 1990), f"omni:9{k}")

    def test_two_matching_tasks_is_no_answer(self):
        rows = [{"task_id": t, "created_at": "2000", "prompt": self.LOOK + "Shot 1 runs."} for t in ("91", "92")]
        self.assertIsNone(self.provider(rows).find_by_prompt("omni:123456789012", self.LOOK + "Shot 1 runs.", 1990))


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("g", aspect="9:16")
        self.data = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.data, str(self.pid), "images"))
        for k, dur in enumerate((1.5, 3.1, 2.0, 2.3, 1.4, 2.2), 1):
            sid = self.p.create_scene(self.pid, k, f"s{k}")
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(
                {"story_scene": 2, "shot_no": k, "size": "MS", "duration_s": dur, "image_prompt": f"frame {k}", "action": f"hành động {k}",
                 "characters": []}), sid))
            jid = self.p.create_job(sid, "image_gen")
            self.p.conn.execute("UPDATE jobs SET state='succeeded' WHERE id=?", (jid,))
            with open(os.path.join(self.data, str(self.pid), "images", f"job_{jid}.png"), "wb") as f:
                f.write(b"\x89PNG")
        self.p.conn.commit()

    def test_groups_of_three_and_each_model_rule(self):
        rows = group_test.shots_of_scene(self.p, self.pid, 2)
        gs = group_test.groups(rows)
        self.assertEqual([len(g) for g in gs], [3, 3])
        kw1, s1, prompt1 = group_test.build(self.p, self.data, self.pid, gs[0], "P1", "")
        self.assertEqual(s1, 7)                                              # 6,6 s of film, one clip
        self.assertIn("last_frame", kw1)
        self.assertIn("Shot 3", prompt1)
        _, s3, _ = group_test.build(self.p, self.data, self.pid, gs[0], "P3", "")
        self.assertEqual(s3, 3 + 4 + 3)                                      # Kling: every shot at least 3 s
        kw2, _, prompt2 = group_test.build(self.p, self.data, self.pid, gs[1], "P2", "")
        self.assertEqual(len(kw2["reference_only"]), 3)
        self.assertIn("Image 3 is the storyboard frame of Shot 3", prompt2)
        _, s4, prompt4 = group_test.build(self.p, self.data, self.pid, gs[1], "P4", "")
        self.assertEqual(s4, 6)
        self.assertLessEqual(len(prompt4), group_test.KLING_PROMPT)

    def test_s2_one_clip_a_shot_and_s3_groups_by_cast(self):
        rows = group_test.shots_of_scene(self.p, self.pid, 2)
        kw, secs, prompt = group_test.build(self.p, self.data, self.pid, [rows[0]], "S2", "")
        self.assertEqual(secs, 3)                                            # 1,5 s → Kling floor 3 s
        self.assertNotIn("multi_prompt", kw)
        for r, cast in zip(rows, (["A"], ["A"], ["B"], ["B"], ["B"], ["B"])):
            r["data"]["characters"] = cast
        self.assertEqual([len(g) for g in group_test.s3_groups(rows)], [2, 3, 1])

    def test_queue_id_relinked_by_prompt(self):
        from core import experiments

        class P:
            def find_by_prompt(self, ext, prompt, sent, taken):
                return "omni:900000000000000001" if prompt == "shot 1" and "omni:900000000000000001" not in taken else None
        experiments._save(self.data, self.pid, [
            {"kind": "group_test", "method": "S2", "group": 1, "state": "failed", "external_id": "omni:123456789012",
             "prompt": "shot 1", "at": "2026-09-27T01:38:39+00:00", "message": "không thấy task trong danh sách ClipAI"},
            {"kind": "group_test", "method": "S2", "group": 2, "state": "failed", "external_id": "omni:123456789013",
             "prompt": "shot 2", "at": "2026-09-27T01:38:40+00:00", "message": "[content] bị chặn"}])
        self.assertEqual(group_test.relink(P(), self.data, self.pid), 1)
        e1, e2 = experiments.load(self.data, self.pid)
        self.assertEqual((e1["state"], e1["external_id"], e1["queue_id"]), ("running", "omni:900000000000000001", "omni:123456789012"))
        self.assertEqual(e2["state"], "failed")                              # a real refusal is left alone

    def test_marked_reference_keeps_size(self):
        from PIL import Image
        src = os.path.join(tempfile.mkdtemp(), "f.png")
        Image.new("RGB", (360, 640), (40, 90, 40)).save(src)
        out = group_test.mark_reference(src)
        im = Image.open(out)
        self.assertEqual(im.size, (360, 640))
        self.assertEqual(im.getpixel((5, 5)), (255, 255, 255))               # the banner


if __name__ == "__main__":
    unittest.main()
