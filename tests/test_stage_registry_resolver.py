import copy
import importlib
import os
from unittest.mock import patch

import pytest

with patch.object(os, "environ", {}):
    from tests.test_stage_registry_schema import bundle, envelope
    resolver = importlib.import_module("core.stage_registry_resolver")


def test_inheritance_end_beats_and_isolation():
    b = bundle(); original = copy.deepcopy(b)
    snap = resolver.resolve_shot(b, "shot", 1)
    assert snap["end"]["objects"]["actor"]["pose"] == "lying"
    assert snap["beats"][0]["objects"]["actor"]["relation"]["in"] == "well"
    assert snap["start"]["objects"]["actor"]["pose"] == "standing"
    snap["end"]["objects"]["actor"]["xyz"][0] = 999
    assert b == original


def test_hash_dependencies_and_order():
    b = bundle(); first = resolver.resolve_shot(b, "shot", 1)["hash"]
    b["states"].reverse()
    assert resolver.resolve_shot(b, "shot", 1)["hash"] == first
    b["states"][0]["patches"][0]["pose"] = "crouching"
    assert resolver.resolve_shot(b, "shot", 1)["hash"] != first
    b = bundle(); b["stages"][0]["source"] = {"fingerprint": "changed"}
    assert resolver.resolve_shot(b, "shot", 1)["hash"] != first


def test_camera_does_not_move_actor_locks_kept():
    b = bundle(); b["states"][1]["_user_locked"] = {"patches": {"author_id": "fake", "created_at_utc": "2026-10-14T00:00:00Z", "reason": "manual"}}
    first = resolver.resolve_shot(b, "shot", 1)
    b["cameras"][0]["location"][0] = 10
    second = resolver.resolve_shot(b, "shot", 1)
    assert first["end"]["objects"] == second["end"]["objects"]
    assert first["end"]["locks"]


def test_spawn_hidden_despawn_and_explicit_respawn():
    b = bundle(); end = b["states"][1]
    end["patches"].append({"object_id": "wall", "op": "spawn", "xyz": [2, 0, 0]})
    assert "wall" not in resolver.resolve_state(b, "start", 1)["objects"]
    assert "wall" in resolver.resolve_state(b, "end", 1)["objects"]
    end["patches"][0].update(hidden=True)
    assert resolver.resolve_state(b, "end", 1)["objects"]["actor"]["hidden"] is True
    end["patches"] = [{"object_id": "actor", "op": "despawn"}]
    third = envelope("state", "third", segment={"id": "segment", "revision": 1}, parent_state={"id": "end", "revision": 1}, story_time=3, beat="after", patches=[{"object_id": "actor", "op": "update", "pose": "standing"}])
    b["states"].append(third)
    with pytest.raises(resolver.RegistryValidationError):
        resolver.resolve_state(b, "third", 1)
    third["patches"][0]["op"] = "spawn"
    assert "actor" in resolver.resolve_state(b, "third", 1)["objects"]


def test_continuation_retains_fallen_actor():
    b = bundle(); pin = lambda ident: {"id": ident, "revision": 1}
    b["segments"].append(envelope("segment", "return", stage=pin("stage"), time=[3, 9], initial_state=pin("return-start"), continuation_from_state=pin("end")))
    b["states"].append(envelope("state", "return-start", segment=pin("return"), parent_state=None, story_time=3, beat="return", patches=[]))
    assert resolver.resolve_state(b, "return-start", 1)["objects"]["actor"]["pose"] == "lying"


def test_no_latest_fallback():
    with pytest.raises(resolver.RegistryValidationError):
        resolver.resolve_state(bundle(), "end", 99)


def test_historical_revision_and_unknown_snapshot():
    b = bundle(); newer = copy.deepcopy(b["states"][1]); newer.update(revision=2, parent_revision=1)
    newer["patches"][0]["pose"] = "standing"
    b["states"].append(newer)
    assert resolver.resolve_state(b, "end", 1)["objects"]["actor"]["pose"] == "lying"
    snap = resolver.resolve_shot(b, "shot", 1)
    assert snap["warnings"] and snap["measurement"] == "unknown"


def test_relation_explicit_clear_keeps_world_position():
    b = bundle(); pin = lambda ident: {"id": ident, "revision": 1}
    b["states"].append(envelope("state", "out", segment=pin("segment"), parent_state=pin("end"), story_time=3, beat="out", patches=[{"object_id": "actor", "op": "update", "xyz": [2, 2, 0], "relation": {"in": None}}]))
    obj = resolver.resolve_state(b, "out", 1)["objects"]["actor"]
    assert obj["xyz"] == [2, 2, 0] and "in" not in obj["relation"]

@pytest.fixture(autouse=True)
def fake_environment():
    with patch.object(os, "environ", {}):
        yield


def test_warning_dependency_order_and_irrelevant_stage():
    b = bundle(); first = resolver.resolve_shot(b, "shot", 1)
    unrelated = copy.deepcopy(b["stages"][0]); unrelated["id"] = "unused"
    b["stages"].insert(0, unrelated)
    assert resolver.resolve_shot(b, "shot", 1)["hash"] == first["hash"]
    b["stages"].reverse()
    assert resolver.resolve_shot(b, "shot", 1)["hash"] == first["hash"]


def test_semantic_public_validation_and_budget():
    b = bundle(); b["states"][0]["patches"][0]["op"] = "update"
    assert resolver.validate_registry(b)["errors"]
    with pytest.raises(resolver.RegistryValidationError):
        resolver.resolve_shot(bundle(), "shot", 1, max_work=1)


def test_missing_height_warns_and_object_geometry_is_dependency():
    b = bundle(); result = resolver.resolve_state(b, "end", 1)
    assert any("height" in w["path"] for w in result["warnings"])
    b["stages"][0]["objects"][0]["geometry"] = {"dimensions": [1, 1, 2], "confidence": "assumed", "source": "fixture"}
    assert resolver.resolve_state(b, "end", 1)["hash"] != result["hash"]


def test_snapshot_beats_cache_has_no_aliases():
    b = bundle(); b["shots"][0]["beats"] = [{"id": "start", "revision": 1}, {"id": "end", "revision": 1}, {"id": "end", "revision": 1}]
    snap = resolver.resolve_shot(b, "shot", 1)
    snap["beats"][1]["objects"]["actor"]["xyz"][0] = 42
    assert snap["start"]["objects"]["actor"]["xyz"][0] == 0
    assert snap["end"]["objects"]["actor"]["xyz"][0] == 0
    assert snap["beats"][2]["objects"]["actor"]["xyz"][0] == 0
    assert b["states"][0]["patches"][0]["xyz"][0] == 0


@pytest.mark.parametrize("change,code", [
    (lambda b: b["states"][0]["patches"][0].update(op="update"), "lifecycle"),
    (lambda b: b["states"][0]["patches"][0].update(relation={"in": "wall"}), "reference"),
    (lambda b: (b["states"][0]["patches"][0].update(relation={"in": "well"}), b["states"][0]["patches"][1].update(relation={"held_by": "actor"})), "cycle"),
])
def test_safe_semantic_validator_rejects(change, code):
    b = bundle(); change(b)
    assert code in {e["code"] for e in resolver.validate_registry(b)["errors"]}


def test_public_validation_malformed_and_request_exact_pin():
    assert resolver.validate_registry(None)["errors"]
    index, _ = resolver._prepare(bundle())
    with pytest.raises(resolver.RegistryValidationError):
        resolver._get(index, "states", {"id": "start", "revision": 1, "extra": 1})

@pytest.mark.parametrize("bad_id", [None, [], {}])
def test_bad_state_request_is_sanitized(bad_id):
    with pytest.raises(resolver.RegistryValidationError): resolver.resolve_state(bundle(), bad_id, 1)
