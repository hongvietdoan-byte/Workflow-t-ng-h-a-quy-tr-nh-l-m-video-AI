"""Hợp đồng A trên dữ liệu giả; không cần môi trường thật."""
import copy
import importlib
import os
from unittest.mock import patch

import pytest

with patch.object(os, "environ", {}):
    schema = importlib.import_module("core.stage_registry_schema")


def envelope(kind, ident, **fields):
    return dict(schema_version=1, project_id=123, id=ident, revision=1,
                parent_revision=None, author_id="fake-author", created_at_utc="2026-10-14T00:00:00Z",
                reason="fixture", source={}, provenance={}, _user_locked={}, **fields)


def bundle():
    pin = lambda ident: {"id": ident, "revision": 1}
    return dict(schema_version=1, project_id=123, stages=[envelope("stage", "stage",
        source_asset_id=1234, asset_revision=1, world_frame={"units": "m", "east": "+x", "north": "+y", "up": "+z", "facing": "clockwise_from_+y", "scale": {"value": None, "confidence": "unknown", "source": ""}},
        geometry={"dimensions": None, "confidence": "unknown", "source": ""},
        spots=[{"id": "spot", "xyz": [0, 0, 0], "facing": 0}],
        objects=[{"id": "actor", "kind": "actor", "asset_id": 1235, "asset_revision": 1, "height": None}, {"id": "well", "kind": "prop"}, {"id": "wall", "kind": "prop"}])],
        segments=[envelope("segment", "segment", stage=pin("stage"), time=[0, 9], initial_state=pin("start"), continuation_from_state=None)],
        states=[envelope("state", "start", segment=pin("segment"), parent_state=None, story_time=0, beat="start", patches=[{"object_id": "actor", "op": "spawn", "xyz": [0, 0, 0], "pose": "standing", "hidden": False}, {"object_id": "well", "op": "spawn", "xyz": [1, 1, 0]}]),
                envelope("state", "end", segment=pin("segment"), parent_state=pin("start"), story_time=2, beat="end", patches=[{"object_id": "actor", "op": "update", "pose": "lying", "facing": 90, "relation": {"in": "well"}}])],
        cameras=[envelope("camera", "camera", stage=pin("stage"), state=pin("start"), spot_id="spot", location=[0, -4, 2], target=[0, 0, 1], lens_mm=35, sensor_mm=[36, 24], aspect=1.5, angles=[0, 0, 0], pov_subject_id="actor", move={"end_location": [0, -3, 2], "end_target": [0, 0, 1], "seconds": 2, "path": []})],
        shots=[envelope("shot", "shot", scene_id=456, stage=pin("stage"), segment=pin("segment"), state_start=pin("start"), state_end=pin("end"), spot_id="spot", camera=pin("camera"), private_camera=None, beats=[pin("end")], time_clip=[0, 2])])


def errors(b):
    return {e["code"] for e in schema.validate_bundle(b)["errors"]}

def test_manifest_ids_fit_sqlite():
    b = bundle(); b["stages"][0]["source_asset_id"] = 2**63
    assert "number" in errors(b)


def test_valid_unknown_is_warning():
    result = schema.validate_bundle(bundle())
    assert result["errors"] == []
    assert result["warnings"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True])
def test_numeric_invalid(value):
    b = bundle(); b["states"][0]["patches"][0]["xyz"][0] = value
    assert "number" in errors(b)


@pytest.mark.parametrize("change,code", [
    (lambda b: b["states"][0].update(project_id="foreign"), "scope"),
    (lambda b: b["shots"][0]["state_end"].update(revision=99), "pin"),
    (lambda b: b["states"][0].update(parent_state={"id": "end", "revision": 1}), "cycle"),
    (lambda b: b["states"].append(copy.deepcopy(b["states"][0])), "duplicate"),
    (lambda b: b["cameras"][0].update(spot_id="absent"), "reference"),
    (lambda b: b["cameras"][0].update(pov_subject_id="absent"), "reference"),
    (lambda b: b["stages"][0].update(typo="sensitive-value"), "field"),
])
def test_reject(change, code):
    b = bundle(); change(b)
    assert code in errors(b)


def test_continuation_cycle():
    b = bundle(); b["segments"][0]["continuation_from_state"] = {"id": "end", "revision": 1}
    assert "cycle" in errors(b)


def test_sanitized_errors_and_budget():
    b = bundle(); b["stages"][0]["private-token"] = "do-not-echo"
    assert "do-not-echo" not in str(schema.validate_bundle(b))
    assert "private-token" not in str(schema.validate_bundle(b))
    assert schema.validate_bundle(b, max_nodes=2)["errors"][0]["code"] == "budget"


@pytest.mark.parametrize("change", [
    lambda b: b.update(project_id=True),
    lambda b: b["shots"][0].update(scene_id=True),
    lambda b: b["stages"][0].update(source_asset_id=True),
    lambda b: b["stages"][0]["objects"][0].update(asset_id=-1),
    lambda b: b["cameras"][0]["move"].update(seconds=True),
    lambda b: b["states"][0]["patches"][0].update(op=[]),
    lambda b: b["states"][0].update(parent_state={"id": "absent", "revision": 1}),
])
def test_malformed_and_orphan(change):
    b = bundle(); change(b)
    assert schema.validate_bundle(b)["errors"]


def test_deep_input_budget_and_raw_preserved():
    b = bundle(); raw = {}; node = raw
    for _ in range(60): node["child"] = {}; node = node["child"]
    b["stages"][0]["provenance"]["raw"] = raw
    assert "budget" in errors(b)
    b = bundle(); b["stages"][0]["provenance"]["raw"] = {"legacy-unknown": "fake-value"}
    assert not errors(b)


@pytest.fixture(autouse=True)
def fake_environment():
    with patch.object(os, "environ", {}):
        yield


def test_email_author_contract():
    b = bundle(); b["states"][0]["author_id"] = "fake@example.invalid"
    assert not errors(b)


@pytest.mark.parametrize("change", [
    lambda b: b["states"].append(envelope("state", "orphan", segment={"id": "segment", "revision": 1}, parent_state=None, story_time=1, beat="orphan", patches=[])),
    lambda b: b["shots"][0].update(state_start={"id": "end", "revision": 1}, state_end={"id": "start", "revision": 1}),
    lambda b: b["shots"][0].update(beats=[{"id": "end", "revision": 1}, {"id": "start", "revision": 1}]),
    lambda b: b["stages"][0]["objects"][0].update(geometry={"unrecognized": 1}),
    lambda b: b["stages"][0]["geometry"].update(shapes="invalid"),
    lambda b: b["states"][0].update(_user_locked={"../escape": {"author_id": "fake", "created_at_utc": "2026-10-14T00:00:00Z", "reason": "manual"}}),
])
def test_review_semantic_and_nested_rejections(change):
    b = bundle(); change(b)
    assert errors(b)

@pytest.mark.parametrize("change", [
    lambda b: b["cameras"][0].update(state={"id": "end", "revision": 1}),
    lambda b: b["states"][0].update(story_time=10**400),
    lambda b: b["shots"][0].update(state_start={"id": [], "revision": 1}),
    lambda b: b["stages"][0]["geometry"].update(shapes=[{"kind": "box", "dimensions": [1, 2, 3], "confidence": "measured", "source": ""}]),
])
def test_review_malformed_sanitized(change):
    b = bundle(); change(b)
    assert errors(b)


def test_strict_nested_geometry_valid_and_budget_options():
    b = bundle(); b["stages"][0]["geometry"]["shapes"] = [{"kind": "box", "dimensions": [1, 2, 3], "confidence": "assumed", "source": "fixture", "transform": [1]*16}]
    assert not errors(b)
    assert schema.validate_bundle(b, max_depth=10**100)["errors"][0]["code"] == "budget"
