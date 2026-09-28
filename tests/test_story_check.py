"""S3.2 (kế hoạch sau #8): the first-time viewer reads only what will be on screen and tells the story back, with the places a viewer
would be lost — before any picture is paid for."""
import json
import tempfile
import unittest
from unittest import mock

from core import autopilot, llm_runner, story_check
from tests.test_v2 import Base


class StoryCheckTests(Base):
    def test_the_viewer_never_reads_the_directors_intent(self):
        film = story_check.digest(self.p, self.pid)
        self.assertTrue(film)
        text = json.dumps(film, ensure_ascii=False)
        for field in ("emotional_intent", "beat", "why", "motive", "tradeoffs", "image_prompt"):
            self.assertNotIn(f'"{field}"', text)
        self.assertTrue(all("shot" in f and "action" in f for f in film))

    def test_one_call_per_shot_plan_and_the_reading_is_kept(self):
        data = tempfile.mkdtemp()
        llm = llm_runner.MockLlm()
        with mock.patch.object(llm, "complete", wraps=llm.complete) as calls:
            res = story_check.run(self.p, self.pid, llm, data)
            self.assertEqual(res["understood"], 4)
            story_check.run(self.p, self.pid, llm, data)                  # same plan on screen: no second call
            self.assertEqual(calls.call_count, 1)
        self.assertTrue(any(line.startswith("❓") for line in story_check.lines(story_check.load(data, self.pid))))

    def test_the_run_reads_the_plan_only_when_the_feature_is_on(self):
        ctx = autopilot.Context(self.data, None, None, llm_runner.MockLlm(), None, None)
        self.assertIsNone(autopilot._story_check_phase(self.p, self.pid, ctx))
        self.assertIsNone(story_check.load(self.data, self.pid))
        with mock.patch.dict("os.environ", {"FEATURE_STORY_CHECK": "1"}):
            self.assertIsNone(autopilot._story_check_phase(self.p, self.pid, ctx))      # never stops the run
        self.assertIsNotNone(story_check.load(self.data, self.pid))


if __name__ == "__main__":
    unittest.main()
