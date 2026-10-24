"""CX23-M62 M6.2 handoff shadow contract; synthetic files and replay only."""
import hashlib
import json
from pathlib import Path

import pytest

from core import features, handoff


def _args(tmp_path, dependencies=None):
    digest = hashlib.sha256(b"synthetic frame").hexdigest()
    return {
        "data_dir": str((tmp_path / "data").resolve()),
        "project_id": 24,
        "scene_id": 7,
        "shot_no": 3,
        "from_role": "storyboard_artist",
        "to_role": "video_prompt_artist",
        "revision": {"scene_rev": 12, "byd_v": 2, "fields": {"image_prompt": 5}},
        "dependencies": dependencies if dependencies is not None else [{"kind": "byd", "revision": 2}],
        "products": [{"path": "data/projects/24/images/shot-7.png", "sha256": digest, "kind": "image"}],
        "qc_evidence": [{"id": "qc-run:42", "status": "passed", "sha256": digest}],
        "approval_state": "approved_by_director",
    }


def _replay_package(tmp_path):
    fixture = Path(__file__).parent / "golden" / "package_inputs.json"
    snapshot = json.loads(fixture.read_text(encoding="utf-8"))["image"]
    refs = tmp_path / "refs"
    refs.mkdir()
    (refs / "ref.bin").write_bytes(b"synthetic")
    from tools import golden_capture

    package_bytes = golden_capture.replay_builder(snapshot, ref_root=refs)
    return snapshot, refs, package_bytes


def test_flag_is_registered_off_and_non_costly(monkeypatch):
    monkeypatch.delenv("FEATURE_CREW_HANDOFF_SHADOW", raising=False)

    assert handoff.FLAG in features.FEATURES
    assert features.FEATURES[handoff.FLAG]["verified"] is False
    assert features.FEATURES[handoff.FLAG]["costs"] is False
    assert handoff.enabled() is False


def test_flag_off_writes_no_file_and_preserves_m19_m26_golden_bytes(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_CREW_HANDOFF_SHADOW", "0")
    args = _args(tmp_path)
    fixture = Path(__file__).parent / "golden" / "package_inputs.json"
    before = fixture.read_bytes()
    snapshot, refs, package_before = _replay_package(tmp_path)

    assert handoff.record(**args) is None
    assert not Path(args["data_dir"]).exists()
    assert fixture.read_bytes() == before
    assert package_before == snapshot["baseline"].encode("utf-8")
    assert handoff.dependencies_from_package(package_before)[0]["sha256"] == json.loads(package_before)["refs"][0]["sha256"]


def test_flag_on_appends_one_schema_valid_line_per_handoff_from_replay_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_CREW_HANDOFF_SHADOW", "1")
    snapshot, _refs, package = _replay_package(tmp_path)
    package_data = json.loads(package)
    package_data["refs"][0]["asset_id"] = 1149  # M2.6 relpath projection
    package = json.dumps(package_data, ensure_ascii=False).encode("utf-8")
    dependencies = handoff.dependencies_from_package(package)
    args = _args(tmp_path, dependencies=dependencies)
    path = Path(args["data_dir"]) / "24" / "crew" / "handoffs.jsonl"

    first = handoff.record(**args, handoff_id="handoff-1", at="2026-10-24T10:00:00+00:00")
    second = handoff.record(**args, handoff_id="handoff-2", at="2026-10-24T10:01:00+00:00")

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows == [first, second]
    assert set(first) == {
        "schema_version", "handoff_id", "created_at", "project_id", "scene_id", "shot_no",
        "from_role", "to_role", "revision", "dependencies", "products", "qc_evidence", "approval_state",
    }
    assert first["schema_version"] == 1
    assert first["from_role"] == "storyboard_artist"
    assert first["to_role"] == "video_prompt_artist"
    assert first["revision"] == args["revision"]
    assert first["products"] == args["products"]
    assert first["dependencies"] == dependencies
    assert first["dependencies"][0]["rel_path"] == json.loads(package)["refs"][0]["path"]
    assert first["dependencies"][0]["sha256"] == json.loads(package)["refs"][0]["sha256"]
    assert first["dependencies"][0]["asset_id"] == 1149
    assert first["qc_evidence"] == args["qc_evidence"]
    assert handoff.latest(args["data_dir"], 24, 7, to_role="video_prompt_artist") == second


def test_flag_on_requires_absolute_output_root_before_creating_files(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_CREW_HANDOFF_SHADOW", "1")
    args = _args(tmp_path)
    args["data_dir"] = "relative-shadow"

    with pytest.raises(handoff.HandoffInputError, match="tuyệt đối"):
        handoff.record(**args)

    assert not Path("relative-shadow").exists()


def test_flag_on_rejects_product_without_sha_before_appending(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_CREW_HANDOFF_SHADOW", "1")
    args = _args(tmp_path)
    args["products"] = [{"path": "projects/24/shot-7.png"}]

    with pytest.raises(handoff.HandoffInputError, match="sha256"):
        handoff.record(**args)

    assert not Path(args["data_dir"]).exists()


def test_flag_on_rejects_noncanonical_absolute_product_path(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_CREW_HANDOFF_SHADOW", "1")
    args = _args(tmp_path)
    args["products"][0]["path"] = str((tmp_path / "absolute.png").resolve())

    with pytest.raises(handoff.HandoffInputError, match="M2.6 rel_path"):
        handoff.record(**args)

    assert not Path(args["data_dir"]).exists()


def test_package_projection_rejects_missing_reference_hash(tmp_path):
    package = {"refs": [{"param": "references", "path": "data/ref.png", "sha256": None}]}

    with pytest.raises(handoff.HandoffInputError, match="sha256"):
        handoff.dependencies_from_package(package)


def test_revision_must_be_pinned_source_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_CREW_HANDOFF_SHADOW", "1")
    args = _args(tmp_path)
    args["revision"] = 3

    with pytest.raises(handoff.HandoffInputError, match="scene_rev, byd_v và fields"):
        handoff.record(**args)

    assert not Path(args["data_dir"]).exists()
