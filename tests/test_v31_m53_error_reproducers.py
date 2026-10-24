"""Fixture-only reproducers for high-cost/repeated open entries in the V3.1 error ledger."""
import os
from unittest.mock import patch

import pytest

_IMPORT_ENV = {"PATH": "fixture-path", "SYSTEMROOT": "fixture-system", "TEMP": "fixture-temp", "PYTHONUTF8": "1"}
with patch.object(os, "environ", _IMPORT_ENV):
    from core import batch, cost, model_router, quality_tier, runner
    from core.db import connect
    from core import llm_io
    from core.pipeline import Pipeline


def _fake_env(**extra):
    return {**_IMPORT_ENV, "FEATURE_SEND_ESTIMATE": "0", "LLM_PROVIDER": "claude_cli", **extra}


def _fake_pricing():
    return {
        "currency": "USD",
        "per_video_clip": {},
        "per_video_second": {
            "dreamina-seedance-2-5-260628:480p": 0.01,
            "dreamina-seedance-2-5-260628:720p": 0.02,
        },
        "per_million_tokens": {"fixture-claude": {"input": 1.0, "output": 2.0}},
    }


@pytest.fixture
def ready_fixture(tmp_path):
    """A one-scene in-memory workflow; no project files, credentials, or provider calls."""
    with patch.object(os, "environ", _fake_env()):
        pipeline = Pipeline(connect(str(tmp_path / "fixture.sqlite")))
        project_id = pipeline.create_project("fixture", aspect="9:16")
        scene_id = pipeline.create_scene(project_id, 1, "fixture")
        image_job = pipeline.create_job(scene_id)
        pipeline.start(image_job)
        pipeline.succeed(image_job)
        pipeline.approve(image_job)
        llm_io.store_motion_prompts(pipeline, project_id, {"scenes": [{"idx": 1, "motion_prompt": "fixture", "duration_sec": 4}]})
        llm_io.approve_motion_prompt(pipeline, scene_id)
        pipeline.conn.execute("UPDATE projects SET max_retry_count=1 WHERE id=?", (project_id,))
        pipeline.conn.commit()
        yield pipeline, project_id, scene_id
        pipeline.conn.close()


@pytest.mark.xfail(strict=True, reason="P31-G56: current _diag_once de-duplicates by job id, not (code, scene)")
def test_p31_g56_same_code_same_scene_is_one_diagnostic():
    sent = []
    video_runner = object.__new__(runner.VideoRunner)
    video_runner._diag = lambda job, severity, code, message: sent.append((job["scene_id"], code, message))

    video_runner._diag_once({"id": 1, "scene_id": 7}, "warn", "plate_stale", "same fixture diagnostic")
    video_runner._diag_once({"id": 2, "scene_id": 7}, "warn", "plate_stale", "same fixture diagnostic")

    assert sent == [(7, "plate_stale", "same fixture diagnostic")]


@pytest.mark.xfail(strict=True, reason="P33-A7: old estimate path omits the synthetic reference-video surcharge")
def test_p33_a7_batch_estimate_matches_price_for_reference_video(ready_fixture):
    pipeline, project_id, scene_id = ready_fixture
    choice = {"model": "seedance-2.5", "resolution": "480p", "e1": "draft_first"}
    fake_reference = {"seconds": 3.0, "warnings": []}
    with patch.object(os, "environ", _fake_env()), \
            patch.object(cost, "load_pricing", return_value=_fake_pricing()), \
            patch.object(model_router, "scene_choice", return_value=choice), \
            patch.object(cost, "video_reference_seconds", return_value=fake_reference), \
            patch.object(cost, "chat_prompt_estimate", return_value=0.0), \
            patch.object(quality_tier, "enabled", return_value=False):
        estimate = cost.estimate_videos_by_scene(pipeline, project_id, cost.load_pricing())
        sent_price = cost.send_clip_usd(pipeline.conn, scene_id, cost.load_pricing(), seconds=4.0)

    assert estimate["min"] == pytest.approx(sent_price)


@pytest.mark.xfail(strict=True, reason="P33-A8: with the flag off, estimator falls back to model-profile tier instead of draft 480p")
def test_p33_a8_batch_estimate_uses_draft_tier_when_scene_resolution_is_missing(ready_fixture):
    pipeline, project_id, scene_id = ready_fixture
    choice = {"model": "seedance-2.5", "resolution": None, "e1": "draft_first"}
    with patch.object(os, "environ", _fake_env()), \
            patch.object(cost, "load_pricing", return_value=_fake_pricing()), \
            patch.object(model_router, "scene_choice", return_value=choice), \
            patch.object(cost, "video_reference_seconds", return_value={"seconds": 0.0, "warnings": []}), \
            patch.object(cost, "chat_prompt_estimate", return_value=0.0), \
            patch.object(batch, "_draft_tier", return_value="480p"), \
            patch.object(quality_tier, "enabled", return_value=True), \
            patch.object(quality_tier, "tier_for_new_job", return_value={"quality_tier": "draft"}):
        estimate = cost.estimate_videos_by_scene(pipeline, project_id, cost.load_pricing())
        sent_price = cost.send_clip_usd(pipeline.conn, scene_id, cost.load_pricing(), seconds=4.0)

    assert estimate["min"] == pytest.approx(sent_price)


@pytest.mark.xfail(strict=True, reason="P33-A9: with send_estimate off, claude_cli is priced as Anthropic API")
def test_p33_a9_claude_cli_has_zero_api_estimate_without_paid_calls():
    with patch.object(os, "environ", _fake_env()), \
            patch.object(cost, "send_estimate_on", return_value=False), \
            patch.object(cost, "load_pricing", return_value=_fake_pricing()), \
            patch.object(cost, "llm_model", return_value="fixture-claude"):
        assert cost.llm_call_usd(None, "qc", cost.load_pricing()) == 0.0
