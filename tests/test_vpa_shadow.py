"""M6.5 VPA thuần: chỉ đọc snapshot/kiểm proposal, không ghi store hay gọi provider trong test."""
from copy import deepcopy
import hashlib
import json
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
             "sha256": "a" * 64, "role_clause": "Image 1 is Kelly identity only."},
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


def _handoff_context():
    image_hash = "a" * 64
    return {
        "scene_id": 41,
        "shot_no": 4,
        "from_role": "director",
        "revision": {"scene_rev": 7, "byd_v": 2, "fields": {"motion_context": 1}},
        "dependencies": [
            {"kind": "byd", "revision": 2},
            {"kind": "approved_image", "input_hash": image_hash, "source": "snapshot"},
        ],
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


def test_approved_image_requires_full_sha256_provenance():
    snapshot = _snapshot()
    snapshot["approved_images"][0]["sha256"] = "abc123"
    with mock.patch.object(features, "on", return_value=True):
        result = vpa_shadow.propose(snapshot, lambda *_: _candidate())
    assert result["status"] == "INCOMPLETE_INPUT"
    assert result["cause_code"] == "APPROVED_IMAGE_PROVENANCE"


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


def test_run_shadow_off_performs_no_callback_or_filesystem_io(tmp_path):
    def forbidden(*_args):
        raise AssertionError("cờ TẮT không được gọi generator")

    with mock.patch.object(features, "on", return_value=False):
        result = vpa_shadow.run_shadow(
            _snapshot(), forbidden, data_dir=str(tmp_path), handoff_context=_handoff_context()
        )

    assert result["status"] == "OFF"
    assert list(tmp_path.iterdir()) == []


def test_run_shadow_waits_for_handoff_flag_before_generator_or_write(tmp_path):
    def flag(name):
        return name == "vpa_shadow"

    def forbidden(*_args):
        raise AssertionError("không gọi generator khi sink M6.2 đang TẮT")

    with mock.patch.object(features, "on", side_effect=flag):
        result = vpa_shadow.run_shadow(
            _snapshot(), forbidden, data_dir=str(tmp_path), handoff_context=_handoff_context()
        )

    assert result["status"] == "WAITING_FOR_HANDOFF_SHADOW"
    assert result["cause_code"] == "HANDOFF_SHADOW_OFF"
    assert list(tmp_path.iterdir()) == []


def test_run_shadow_rejects_unpinned_handoff_dependencies_before_generator(tmp_path):
    def enabled(_name):
        return True

    def forbidden(*_args):
        raise AssertionError("thiếu dependency phải HOLD trước khi gọi generator")

    context = _handoff_context()
    context["dependencies"] = []
    with mock.patch.object(features, "on", side_effect=enabled):
        result = vpa_shadow.run_shadow(
            _snapshot(), forbidden, data_dir=str(tmp_path), handoff_context=context
        )

    assert result["status"] == "INCOMPLETE_INPUT"
    assert result["cause_code"] == "HANDOFF_BYD_DEPENDENCY_MISSING"
    assert list(tmp_path.iterdir()) == []


def test_run_shadow_holds_when_handoff_byd_revision_disagrees(tmp_path):
    def enabled(_name):
        return True

    context = _handoff_context()
    context["dependencies"][0]["revision"] = 1
    with mock.patch.object(features, "on", side_effect=enabled):
        result = vpa_shadow.run_shadow(
            _snapshot(), lambda *_args: (_ for _ in ()).throw(AssertionError("must hold")),
            data_dir=str(tmp_path), handoff_context=context,
        )

    assert result["status"] == "INCOMPLETE_INPUT"
    assert result["cause_code"] == "HANDOFF_BYD_DEPENDENCY_MISSING"
    assert list(tmp_path.iterdir()) == []


def test_run_shadow_writes_artifact_and_handoff_only_keeps_pointer_and_hash(tmp_path):
    def enabled(name):
        return name in {"vpa_shadow", "crew_handoff_shadow"}

    with mock.patch.object(features, "on", side_effect=enabled):
        result = vpa_shadow.run_shadow(
            _snapshot(), lambda *_args: _candidate(),
            data_dir=str(tmp_path), handoff_context=_handoff_context(),
        )

    artifact_ref = result["artifact"]
    assert result["status"] == "SHADOW_ONLY"
    assert artifact_ref["path"].startswith("12/vpa_shadow/")
    artifact_path = tmp_path.joinpath(*artifact_ref["path"].split("/"))
    artifact_bytes = artifact_path.read_bytes()
    assert hashlib.sha256(artifact_bytes).hexdigest() == artifact_ref["sha256"]
    artifact = json.loads(artifact_bytes.decode("utf-8"))
    assert artifact["proposal"]["motion_prompt"] == _candidate()["motion_prompt"]
    assert artifact["coverage"] == _candidate()["coverage"]
    assert artifact["status"] == "SHADOW_ONLY"
    assert list((tmp_path / "12" / "vpa_shadow").glob("*.tmp")) == []

    handoff_path = tmp_path / "12" / "crew" / "handoffs.jsonl"
    rows = [json.loads(line) for line in handoff_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row["approval_state"] == "shadow_only"
    assert row["products"] == [artifact_ref]
    assert "proposal" not in row and "coverage" not in row and "motion_prompt" not in row


def test_run_shadow_reuses_matching_snapshot_without_calling_generator(tmp_path):
    calls = []
    enabled = lambda name: name in {"vpa_shadow", "crew_handoff_shadow"}

    with mock.patch.object(features, "on", side_effect=enabled):
        first = vpa_shadow.run_shadow(
            _snapshot(), lambda *_args: _candidate(),
            data_dir=str(tmp_path), handoff_context=_handoff_context(),
        )

        def should_not_run(*_args):
            calls.append("called")
            raise AssertionError("snapshot đã có artifact/handoff hợp lệ")

        second = vpa_shadow.run_shadow(
            _snapshot(), should_not_run,
            data_dir=str(tmp_path), handoff_context=_handoff_context(),
        )

    assert second["deduplicated"] is True
    assert second["artifact"] == first["artifact"]
    assert calls == []
    handoff_path = tmp_path / "12" / "crew" / "handoffs.jsonl"
    assert len(handoff_path.read_text(encoding="utf-8").splitlines()) == 1


def test_run_shadow_persists_validation_finding_without_approving_candidate(tmp_path):
    invalid = _candidate()
    invalid["coverage"] = []
    enabled = lambda name: name in {"vpa_shadow", "crew_handoff_shadow"}

    with mock.patch.object(features, "on", side_effect=enabled):
        result = vpa_shadow.run_shadow(
            _snapshot(), lambda *_args: invalid,
            data_dir=str(tmp_path), handoff_context=_handoff_context(),
        )

    assert result["status"] == "RETURNED"
    artifact_path = tmp_path.joinpath(*result["artifact"]["path"].split("/"))
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["findings"][0]["code"] == "BYD_COVERAGE_INCOMPLETE"
    row = json.loads((tmp_path / "12" / "crew" / "handoffs.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["approval_state"] == "shadow_only"


def test_run_shadow_filters_handoff_exception_details(tmp_path):
    from core import handoff

    enabled = lambda name: name in {"vpa_shadow", "crew_handoff_shadow"}
    with mock.patch.object(features, "on", side_effect=enabled), mock.patch.object(
        handoff, "record", side_effect=RuntimeError("fixture-private-path")
    ):
        result = vpa_shadow.run_shadow(
            _snapshot(), lambda *_args: _candidate(),
            data_dir=str(tmp_path), handoff_context=_handoff_context(),
        )

    assert result["status"] == "SHADOW_STORAGE_FAILED"
    assert result["cause_code"] == "HANDOFF_WRITE_FAILED"
    assert result["error_type"] == "RuntimeError"
    assert "fixture-private-path" not in repr(result)
    assert "artifact" in result

