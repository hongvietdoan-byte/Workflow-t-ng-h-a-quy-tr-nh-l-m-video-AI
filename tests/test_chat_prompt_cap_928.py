"""D6 #29 job 928 (14/10): clip GHÉP 2 shot (shot 3+4) chạm trần "đã gọi Claude 2 lần mà đầu vào vẫn đổi" — dựng lại bằng dữ liệu thật
(bản sao CSDL, Claude giả, 0 USD): vân tay đầu vào ỔN ĐỊNH qua hai lần dựng liền; hai lượt Claude (sổ llm_calls 04:56:38 + 04:57:06, cùng
8294 token vào) là CÙNG đầu vào, cả hai bị code từ chối ("mất mã Shot 1, Shot 2") — code lúc đó không lưu bản bị từ chối nên vòng chờ sau
trả tiền lại, chạm trần, và câu báo nói sai lý do. Ở đây: cùng đầu vào không trả tiền lại; trần nói ĐÚNG lý do (cùng đầu vào / phần nào đổi);
câu báo D6 có số job (diag gộp theo câu chữ trong 10 phút — lời từ chối của 928 từng bị gộp vào dòng của 926)."""
import json
import os
import shutil
import tempfile
from unittest import mock

from core import chat_prompt
from tests.test_chat_prompt import ChatPromptTests, FakeClaude

GROUP = ("Image 1 is the storyboard frame of Shot 1. Image 2 is KELLY. Shot 1 (0-3 s): KELLY crouches behind the glue wall. "
         "Shot 2 (3-6 s): KELLY darts to the stairs.")
GOOD = ("Image 1 is Shot 1's first frame; Image 2 is KELLY. Shot 1 (0-3 s): KELLY crouches low behind the curved glue wall. "
        "Shot 2 (3-6 s): she darts for the stairs.")
DROPS_SHOT_2 = "Image 1 and Image 2 show KELLY. Shot 1: she crouches behind the wall, then darts for the stairs."


class GroupClipFingerprint(ChatPromptTests):
    def _frame_copy(self):
        """The start frame cut again into a NEW temp folder on the next poll: same file name, same bytes, other path."""
        d = tempfile.mkdtemp(prefix="chain_")
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, os.path.basename(self.pics[0]))
        shutil.copyfile(self.pics[0], path)
        return path

    def _video(self, client, frame=None, assembled=GROUP):
        imgs = [("Ảnh khung đầu (clip bắt đầu từ đúng ảnh này)", frame or self.pics[0]), ("Ảnh tham chiếu: KELLY", self.pics[1])]
        return chat_prompt.rewrite(self.p, self._job(), "video", assembled, imgs, model="seedance-2.5", limit=4000, client=client,
                                   say=lambda lv, code, msg: self.said.append((lv, code, msg)))

    def test_two_builds_in_a_row_same_fingerprint_second_from_cache(self):
        seen = []
        real = chat_prompt.fingerprint
        with mock.patch.object(chat_prompt, "fingerprint", side_effect=lambda *a: seen.append(real(*a)) or seen[-1]):
            self.assertEqual(self._video(FakeClaude([{"prompt": GOOD}])), GOOD)
            nobody = FakeClaude([])
            self.assertEqual(self._video(nobody, frame=self._frame_copy()), GOOD)
        self.assertEqual(len(set(seen)), 1)
        self.assertEqual(nobody.calls, [])

    def test_928_same_inputs_refused_is_not_paid_again_on_later_polls(self):
        claude = FakeClaude([{"prompt": DROPS_SHOT_2}, {"prompt": DROPS_SHOT_2}])        # first answer + its one fix turn
        self.assertEqual(self._video(claude), GROUP)
        self.assertEqual(len(claude.calls), 2)
        for _ in range(3):                                                                 # the runner's next polls
            nobody = FakeClaude([])
            self.assertEqual(self._video(nobody, frame=self._frame_copy()), GROUP)
            self.assertEqual(nobody.calls, [])
        codes = [c for _, c, _ in self.said]
        self.assertIn("chat_prompt_refused", codes)
        self.assertNotIn("chat_prompt_cap", codes)

    def test_cap_on_unchanged_inputs_says_so_not_inputs_changed(self):
        for _ in range(chat_prompt.MAX_CALLS_PER_JOB):                                   # Claude down twice, same inputs
            self._video(FakeClaude(["not json", "still not json"]))
        nobody = FakeClaude([])
        self.assertEqual(self._video(nobody), GROUP)
        self.assertEqual(nobody.calls, [])
        cap = [m for _, c, m in self.said if c == "chat_prompt_cap"]
        self.assertTrue(cap)
        self.assertNotIn("đầu vào vẫn đổi", cap[-1])
        self.assertIn("cùng đầu vào", cap[-1])

    def test_cap_on_changed_inputs_names_the_part_that_changed(self):
        for i in range(chat_prompt.MAX_CALLS_PER_JOB):
            self._video(FakeClaude([{"prompt": GOOD + f" v{i}"}]), assembled=GROUP + f" t{i}")
        self._video(FakeClaude([]), assembled=GROUP + " changed again")
        cap = [m for _, c, m in self.said if c == "chat_prompt_cap"]
        self.assertTrue(cap)
        self.assertIn("bản code ghép", cap[-1])
        self.assertNotIn("ảnh", cap[-1].split("đổi:")[-1].split("—")[0])

    def test_d6_notes_carry_the_job_number(self):
        self._video(FakeClaude([{"prompt": GOOD}]))
        self._video(FakeClaude(["not json", "still not json"]), assembled=GROUP + " other")
        jid = f"job {self.jid}"
        for code in ("chat_prompt", "chat_prompt_fail"):
            msgs = [m for _, c, m in self.said if c == code]
            self.assertTrue(msgs, code)
            self.assertIn(jid, msgs[-1], code)

    def test_fingerprint_formula_unchanged_so_stored_prompts_stay_valid(self):
        with mock.patch.object(chat_prompt, "guide_for", return_value="G"):
            self.assertEqual(chat_prompt.fingerprint("video", "seedance-2.5", "Shot 1: a. Shot 2: b.", [], {"action": "x"}, ["n"], 4000),
                             "2f5c9ee5523d74345782e265")


class CodesAnyCase(ChatPromptTests):
    """#29 926/928: 'mất mã Shot 1, Shot 2' — a code written in other capitals is the same code; another number is not."""

    def test_codes_in_other_capitals_are_kept(self):
        old = "Image 1 is Shot 1. Images 2/3 are KELLY. Shot 2 throws."
        self.assertEqual(chat_prompt.check(old, "IMAGE 1 is SHOT 1; images 2 AND 3 show KELLY; shot 2 throws.", 999), [])

    def test_another_number_is_still_a_lost_code(self):
        problems = chat_prompt.check("Shot 1 runs. Shot 2 throws. Image 3 KELLY.", "SHOT 1 runs. SHOT 12 throws. IMAGE 30 KELLY.", 999)
        self.assertTrue(problems)
        self.assertIn("Shot 2", problems[-1])
        self.assertIn("Image 3", problems[-1])


class D6SeesTheSentPictures(GroupClipFingerprint):
    """#29 job 928: D6 was shown start frame + the scene's Kho pictures; the request sent storyboard Shot 1, storyboard Shot 2, KELLY,
    place renders (and its prompt's Image N meant those) — one list now for the send and for D6."""

    def _runner(self, sources, end=None):
        from core.runner import VideoRunner
        r = VideoRunner.__new__(VideoRunner)
        r.p, r.data_dir = self.p, tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, r.data_dir, True)
        r._refs = lambda job: True
        r._reference_sources = mock.Mock(return_value=sources)
        r._end_frame = lambda job, model, chain=True: end
        return r

    def test_group_clip_d6_pictures_are_the_reference_pictures_in_image_order(self):
        src = [{"host": "P1_S3_frame", "path": "a.png", "say": "storyboard frame of Shot 1 (khung đầu Shot 1)"},
               {"host": "P1_S4_frame", "path": "b.png", "say": "storyboard frame of Shot 2 (khung đầu Shot 2)"},
               {"host": "P1_KELLY", "path": "k.png", "say": "nhân vật KELLY"},
               {"host": "P1_place_1", "path": "p.png", "say": "PLACE render 3D cho Shot 1, Shot 2"}]
        r = self._runner(src, end="end.png")
        group = [{"id": 3, "data": {}}, {"id": 4, "data": {}}]
        pics = r._d6_pictures(self._job(), group, "seedance-2.5", "start.png", None)
        self.assertEqual([p for _, p in pics], ["a.png", "b.png", "k.png", "p.png"])          # no end frame for a group
        self.assertTrue(pics[1][0].startswith("Image 2: storyboard frame of Shot 2"))
        single = r._d6_pictures(self._job(), None, "seedance-2.5", "start.png", None)
        self.assertEqual(single[-1], ("Image 5: khung cuối (end state của shot)", "end.png"))

    def test_send_uses_the_same_source(self):
        src = [{"host": "P1_S3_frame", "path": "a.png", "say": "x"}, {"host": "P1_KELLY", "path": "k.png", "say": "y"}]
        r = self._runner(src)
        seen = []
        r._hosted_pictures = lambda job, pictures, clean=False: seen.append(pictures) or [{"uri": "asset://1"}, {"uri": "asset://2"}]
        with mock.patch("core.seedance_refs.note_sent"), mock.patch("core.seedance_refs.mark_style", return_value="none"):
            out = r._reference_pictures(self._job(), [{"id": 3, "data": {}}])
        self.assertEqual(seen, [[("P1_S3_frame", "a.png"), ("P1_KELLY", "k.png")]])
        self.assertEqual(out, [{"uri": "asset://1"}, {"uri": "asset://2"}])
