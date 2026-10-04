"""S14.1 A1a — one money gate for every paid send outside the runners (core.spend_gate). Each class of regression fails on the code before
the gate: the character set skipped every cap, the end frame / establishing picture / multi-shot try skipped the project's locked budget.
Fake providers and a temporary database only — 0 USD, no real API."""
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import assets, budget, costume, end_frames, experiments, llm_runner, project_budget, scene_establish, shots
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockImageProvider, ProviderError
from tests.test_costume import picture

ON = {"FEATURE_PROJECT_BUDGET": "1"}


def lock(p, pid, images=5.0, videos=5.0):
    project_budget.approve(p, pid, "a@x", {"stages": {k: {"cap": images if k == "images" else videos if k == "videos" else 5.0}
                                                      for k in project_budget.STAGES}, "total": 100.0})


def usage(conn, pid):
    return conn.execute("SELECT COUNT(*) FROM usage_events WHERE project_id=?", (pid,)).fetchone()[0]


class FakeImage(MockImageProvider):
    """A provider that is NOT named mock*: the caps apply to it as to Deepix."""
    name = "deepix-fake"
    supports_model = True

    def __init__(self, fail_on=None, fail_code="server_error", **kw):
        super().__init__(**kw)
        self.fail_on = fail_on
        self.fail_code = fail_code

    def usage_info(self, model=None):
        return model or "gpt-image-2", "1k"

    def submit(self, prompt, references=None, size=None, model=None):
        if self.fail_on is not None and self._counter + 1 == self.fail_on:
            self._counter += 1
            raise ProviderError("boom", code=self.fail_code)
        return super().submit(prompt, references, size)


class CostumeGateTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.data = os.path.join(self.dir, "projects")
        self.conn = connect(os.path.join(self.dir, "m.sqlite"))
        self.p = Pipeline(self.conn)
        self.pid = self.p.create_project("costume")
        kelly = assets.create(self.conn, "FF", "character", "KELLY", "", "", None, "x")
        assets.add_image(self.conn, kelly, "k.png", picture(550, 800, 10))
        assets.attach(self.conn, self.pid, kelly)
        self.conn.execute("INSERT INTO characters (project_id, name, description, wardrobe) VALUES (?,?,?,?)",
                          (self.pid, "Kelly", "Kelly, athletic", "summer armour"))
        self.conn.commit()

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    @mock.patch.dict(os.environ, ON)
    def test_a_locked_project_budget_refuses_the_set_and_nothing_is_sent(self):
        lock(self.p, self.pid, images=0.06)                       # room for 1 picture, the set costs 2
        provider = FakeImage()
        with self.assertRaises(ValueError) as e:
            costume.make_character_set(self.p, self.pid, "Kelly", provider, self.data, sleep=lambda s: None)
        self.assertIn("Ảnh", str(e.exception))
        self.assertEqual(provider.prompts, {})
        self.assertEqual(usage(self.conn, self.pid), 0)

    def test_the_trial_cap_refuses_the_set_too(self):
        budget.restart(self.conn, usd=0.05)                       # 2 × 0.052 > 0.05
        provider = FakeImage()
        with self.assertRaises(ValueError):
            costume.make_character_set(self.p, self.pid, "Kelly", provider, self.data, sleep=lambda s: None)
        self.assertEqual(provider.prompts, {})

    def test_the_first_picture_is_recorded_even_when_the_second_send_fails(self):
        provider = FakeImage(fail_on=2)
        with self.assertRaises(ProviderError):
            costume.make_character_set(self.p, self.pid, "Kelly", provider, self.data, sleep=lambda s: None)
        self.assertEqual(len(provider.prompts), 1)
        self.assertEqual(usage(self.conn, self.pid), 1)            # paid once → one ledger row, written right after the send
        stage = self.conn.execute("SELECT stage FROM usage_events WHERE project_id=?", (self.pid,)).fetchone()[0]
        self.assertEqual(stage, "character_set")

    def test_out_of_credit_halts_the_service(self):
        provider = FakeImage(fail_on=1, fail_code="out_of_credit")
        with self.assertRaises(ProviderError):
            costume.make_character_set(self.p, self.pid, "Kelly", provider, self.data, sleep=lambda s: None)
        self.assertIsNotNone(budget.halted(self.conn, provider.name))
        self.assertEqual(usage(self.conn, self.pid), 0)

    def test_a_paused_project_sends_nothing(self):
        self.conn.execute("UPDATE projects SET paused=1 WHERE id=?", (self.pid,))
        self.conn.commit()
        provider = FakeImage()
        from core.pipeline import PipelinePaused
        with self.assertRaises(PipelinePaused):
            costume.make_character_set(self.p, self.pid, "Kelly", provider, self.data, sleep=lambda s: None)
        self.assertEqual(provider.prompts, {})


class EndFrameGateTests(unittest.TestCase):
    @mock.patch.dict(os.environ, ON)
    def test_a_locked_project_budget_keeps_the_end_frame_waiting(self):
        from tests.test_end_frames import _shot_with_end_state
        from tests.test_v3 import _approve_all_images, kenta_project
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        _shot_with_end_state(p, pid)
        data = tempfile.mkdtemp()
        _approve_all_images(p, pid, data)
        self.assertTrue(end_frames.queue(p, pid))
        lock(p, pid, images=0.0)
        provider = FakeImage()
        counts = end_frames.tick(p, pid, provider, data)
        self.assertEqual(counts["sent"], 0)
        self.assertEqual([t for t, pr in provider.prompts.items()], [])
        note = p.conn.execute("SELECT note, state FROM end_frames WHERE project_id=?", (pid,)).fetchone()
        self.assertEqual(note["state"], "queued")
        self.assertIn("chờ", note["note"])


class EstablishGateTests(unittest.TestCase):
    @mock.patch.dict(os.environ, {**ON, "FEATURE_SCENE_ESTABLISHING": "1"})
    def test_a_locked_project_budget_skips_the_wide_picture(self):
        from tests.test_v3 import kenta_project
        p, pid = kenta_project(shot_mode="per_shot")
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        first = shots.shots_of(p, pid)[0]
        lock(p, pid, images=0.0)
        provider = FakeImage()
        said = []
        got = scene_establish.step(p.conn, pid, first["data"]["story_scene"], provider, tempfile.mkdtemp(), model="gpt-image-2",
                                   say=lambda sev, code, msg: said.append((code, msg)))
        self.assertEqual(got, "skipped")
        self.assertEqual(provider.prompts, {})
        self.assertTrue(any(code == "budget" for code, _ in said))


class ExperimentGateTests(unittest.TestCase):
    @mock.patch.dict(os.environ, {**ON, "CLIPAI_KLING_MODE": "std"})
    def test_a_locked_project_budget_refuses_the_multishot_try(self):
        p = Pipeline(connect())
        pid = p.create_project("exp", aspect="9:16")
        sent = []

        class Provider:
            name = "clipai"

            def submit(self, *a, **k):
                sent.append(1)
                return "clipai:video:1"
        plan = ([{"idx": 1, "jid": 1}, {"idx": 2, "jid": 2}], [{"prompt": "a", "duration": 10}, {"prompt": "b", "duration": 5}], 15)
        lock(p, pid, videos=1.0)                                   # 15 s × 0.08 = 1.20 > 1.00
        with mock.patch.object(experiments, "_plan", return_value=plan), self.assertRaises(ValueError) as e:
            experiments.kling_multishot(p, pid, 1, Provider(), tempfile.mkdtemp())
        self.assertIn("Video", str(e.exception))
        self.assertEqual(sent, [])


class GateUnitTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("g")

    def test_an_unknown_budget_stage_is_a_programming_error(self):
        from core import spend_gate
        with self.assertRaises(ValueError):
            with spend_gate.spend(self.p.conn, "image", "deepix", project_id=self.pid, model="gpt-image-2", budget_stage="character_set"):
                pass

    @mock.patch.dict(os.environ, ON)
    def test_a_price_the_table_does_not_know_is_refused_when_locked(self):
        from core import spend_gate
        lock(self.p, self.pid)
        with spend_gate.spend(self.p.conn, "image", "deepix", project_id=self.pid, model="model-without-price") as slot:
            self.assertIn("chưa có giá", (slot.over or "").lower())

    def test_record_writes_the_ledger_stage_and_mock_is_free(self):
        from core import spend_gate
        with spend_gate.spend(self.p.conn, "image", "mock-image", project_id=self.pid, model="mock-image", tier="default",
                              ledger_stage="character_set") as slot:
            self.assertIsNone(slot.over)
            slot.record()
        row = self.p.conn.execute("SELECT * FROM usage_events WHERE project_id=?", (self.pid,)).fetchone()
        self.assertEqual((row["kind"], row["stage"], row["unit"]), ("image", "character_set", "image"))

    def test_refused_raises_spend_refused_a_value_error(self):
        from core import spend_gate
        budget.restart(self.p.conn, usd=0.01)
        with spend_gate.spend(self.p.conn, "image", "deepix", project_id=self.pid, model="gpt-image-2") as slot:
            with self.assertRaises(spend_gate.SpendRefused) as e:
                slot.raise_if_over("Không tạo")
        self.assertIsInstance(e.exception, ValueError)
        self.assertIn("Không tạo", str(e.exception))


if __name__ == "__main__":
    unittest.main()
