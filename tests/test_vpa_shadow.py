"""M6.5 VPA thuần: chỉ đọc snapshot/kiểm proposal, không ghi store hay gọi provider trong test."""
from copy import deepcopy
from unittest import mock

from core import features, vpa_shadow


def _snapshot():
    return {
        "project_id": 12,
        "source_fingerprint": "sha256:fixture-snapshot",
        "source_revisions": {"scene:41": 7, "refs:41": "rev-fixture-2"},
        "byd": {"byd_v": 2, "shot": 4, "hanh_dong": [{"ai": "Kelly", "bat_dau": {"tu_the": "dung"}}]},
        "motion_context": "Shot 4: Kelly stands, then turns toward the doorway.",
        "approved_images": [
            {"id": "asset-fixture-1", "project_id": 12, "approved": True,
             "sha256": "abc123", "role_clause": "Image 1 is Kelly identity only."},
        ],
        "coverage_sources": {"hanh_dong[0].bat_dau": '{"ai":"Kelly","tu_the":"dung"}'},
        "model_target": "fixture-motion-model",
        "prompt_limit": 4000,
    }


def _candidate(prompt="Kelly turns toward the doorway and stops."):
    return {
        "motion_prompt": prompt + " Image 1 is Kelly identity only.",
        "coverage": [{
            "beat_id": "hanh_dong[0].bat_dau",
            "source_excerpt": '{"ai":"Kelly","tu_the":"dung"}',
        }],
    }


def test_flag_is_registered_off_and_excluded_from_experimental_preset():
    meta = features.FEATURES["vpa_shadow"]
    assert meta["verified"] is False
    assert meta.get("default_on") is not True
    assert "vpa_shadow" in features.OPT_IN_ONLY
    with mock.patch.object(features, "settings", return_value={"preset": "experimental", "flags": {}, "modes": {}}):
        assert not features.on("vpa_shadow")


def test_disabled_flag_does_not_call_generator():
    with mock.patch.object(features, "on", return_value=False):
        result = vpa_shadow.propose(_snapshot(), lambda *_: (_ for _ in ()).throw(AssertionError("must stay off")))
    assert result["status"] == "OFF"
    assert result["cause_code"] == "VPA_SHADOW_OFF"


def test_incomplete_snapshot_holds_without_calling_generator():
    snapshot = _snapshot()
    snapshot["byd"]["byd_v"] = 1
    with mock.patch.object(features, "on", return_value=True):
        result = vpa_shadow.propose(snapshot, lambda *_: (_ for _ in ()).throw(AssertionError("must not run")))
    assert result["status"] == "INCOMPLETE_INPUT"
    assert result["cause_code"] == "BYD_V2_REQUIRED"


def test_valid_proposal_is_shadow_only_and_keeps_snapshot_unchanged():
    snapshot = _snapshot()
    snapshot["approved_images"][0]["path"] = "C:\\fixture\\private.png"
    before = deepcopy(snapshot)
    calls = []

    def fake_claude_cli(request, approved_images):
        calls.append((request, approved_images))
        return _candidate()

    with mock.patch.object(features, "on", return_value=True):
        result = vpa_shadow.propose(snapshot, fake_claude_cli)

    assert result["status"] == "SHADOW_ONLY"
    assert result["cause_code"] is None
    assert result["proposal"]["motion_prompt"] == _candidate()["motion_prompt"]
    expected_ref = {key: value for key, value in snapshot["approved_images"][0].items() if key != "path"}
    assert result["refs_actual_snapshot"] == [expected_ref]
    assert len(calls) == 1
    assert list(calls[0][1]) == [expected_ref]
    assert "path" not in calls[0][1][0] and "path" not in result["refs_actual_snapshot"][0]
    assert snapshot == before


def test_prompt_limit_failure_is_reported_without_rewriting_candidate():
    snapshot = _snapshot()
    snapshot["prompt_limit"] = 12
    raw = _candidate()
    with mock.patch.object(features, "on", return_value=True):
        result = vpa_shadow.propose(snapshot, lambda *_: raw)
    assert result["status"] == "RETURNED"
    assert result["cause_code"] == "PROMPT_TOO_LONG"
    assert result["proposal"] == raw


def test_missing_or_conflicting_image_role_is_returned():
    snapshot = _snapshot()
    missing = _candidate()
    missing["motion_prompt"] = "Kelly turns."
    with mock.patch.object(features, "on", return_value=True):
        result = vpa_shadow.propose(snapshot, lambda *_: missing)
    assert result["cause_code"] == "IMAGE_ROLE_MISSING"

    conflict = _candidate("Image 1 shows the doorway.")
    with mock.patch.object(features, "on", return_value=True):
        result = vpa_shadow.propose(snapshot, lambda *_: conflict)
    assert result["cause_code"] == "IMAGE_ROLE_CONFLICT"


def test_coverage_must_match_each_byd_source_once():
    snapshot = _snapshot()
    raw = _candidate()
    raw["coverage"] = []
    with mock.patch.object(features, "on", return_value=True):
        result = vpa_shadow.propose(snapshot, lambda *_: raw)
    assert result["cause_code"] == "BYD_COVERAGE_INCOMPLETE"

    raw = _candidate()
    raw["coverage"][0]["source_excerpt"] = "made up"
    with mock.patch.object(features, "on", return_value=True):
        result = vpa_shadow.propose(snapshot, lambda *_: raw)
    assert result["cause_code"] == "BYD_COVERAGE_MISMATCH"


def test_candidate_cannot_change_byd_model_or_refs():
    raw = _candidate()
    raw["byd"] = {"byd_v": 2, "shot": 99}
    with mock.patch.object(features, "on", return_value=True):
        result = vpa_shadow.propose(_snapshot(), lambda *_: raw)
    assert result["cause_code"] == "UNEXPECTED_PROPOSAL_FIELDS"


def test_generator_failure_has_filtered_explicit_cause():
    with mock.patch.object(features, "on", return_value=True):
        result = vpa_shadow.propose(_snapshot(), lambda *_: 1 / 0)
    assert result["status"] == "RETURNED"
    assert result["cause_code"] == "VPA_GENERATION_FAILED"
    assert result["error_type"] == "ZeroDivisionError"

