"""CX24-M82B: DB/provider giả; chọn shot không thay đường gửi mặc định."""
import os
from contextlib import ExitStack
from unittest.mock import patch

import pytest


@pytest.fixture
def case(tmp_path):
    with ExitStack() as stack:
        stack.enter_context(patch.object(os, "environ", {"PYTHONUTF8": "1", "HOME": str(tmp_path),
            "USERPROFILE": str(tmp_path), "TEMP": str(tmp_path), "TMP": str(tmp_path), "DASHBOARD_AUTH": "off"}))
        from core import batch, features, llm_provider, pilot, shots
        from core.db import connect
        from core.pipeline import Pipeline
        stack.enter_context(patch.object(features, "on", return_value=False))
        stack.enter_context(patch.object(llm_provider, "snapshot_job"))
        scan = stack.enter_context(patch.object(batch.lineage, "scan", return_value={}))
        stack.enter_context(patch.object(shots, "needs_own_image", return_value=True))
        allowed = stack.enter_context(patch.object(pilot, "allowed_scenes", side_effect=lambda p, pid, ids: list(ids)))
        stack.enter_context(patch.object(pilot, "active", return_value=False))
        gates = stack.enter_context(patch.object(batch, "image_gates", return_value={"block": [], "warn": []}))
        p = Pipeline(connect())
        pid = p.create_project("Dự án giả targeted")
        sids = [p.create_scene(pid, n, f"Cảnh {n}") for n in range(1, 5)]
        p.actor = "fixture@example.test"
        yield p, pid, sids, gates, scan, allowed, stack
        p.conn.close()


def _job_scenes(p):
    return [r[0] for r in p.conn.execute("SELECT scene_id FROM jobs WHERE type='image_gen' ORDER BY id")]


def test_none_keeps_old_job_creation_and_exposes_created_ids(case):
    from core import batch
    p, pid, sids, gates, *_ = case
    result = batch.queue_images(p, pid, scene_ids=None)
    assert _job_scenes(p) == sids
    assert result == {"created": 4, "redo": 0, "pilot": False,
                      "job_ids": [r[0] for r in p.conn.execute("SELECT id FROM jobs ORDER BY id")]}
    assert gates.call_args.kwargs["scene_ids"] == sids


def test_two_of_four_never_queues_the_other_hold_shots(case):
    from core import batch
    p, pid, sids, gates, *_ = case
    picked = [sids[0], sids[2]]
    result = batch.queue_images(p, pid, scene_ids=picked)
    assert _job_scenes(p) == picked
    assert result["created"] == 2 and len(result["job_ids"]) == 2
    assert gates.call_args.kwargs["scene_ids"] == picked


def test_targeted_selection_still_intersects_pilot(case):
    from core import batch
    p, pid, sids, gates, scan, allowed, _ = case
    allowed.side_effect = lambda p, pid, ids: [sid for sid in ids if sid == sids[0]]
    result = batch.queue_images(p, pid, scene_ids=sids[:2])
    assert _job_scenes(p) == [sids[0]]
    assert result["created"] == 1


def test_redo_outside_selection_stays_approved_and_selected_redo_returns_child(case):
    from core import batch
    p, pid, sids, gates, scan, allowed, stack = case
    old = [p.create_job(sid, "image_gen") for sid in sids[:2]]
    p.conn.execute("UPDATE jobs SET state='approved'")
    p.conn.commit()
    scan.return_value = {sid: {"image_stale": "đổi đầu vào", "image_job_id": jid} for sid, jid in zip(sids[:2], old)}
    stack.enter_context(patch.object(p, "_rewrite_before_retry", return_value=type("Keep", (), {"apply": lambda self: None})()))
    result = batch.queue_images(p, pid, scene_ids=[sids[0]])
    assert result["created"] == 0 and result["redo"] == 1
    assert p.job(old[1])["state"] == "approved"
    assert len(result["job_ids"]) == 1
    child = p.job(result["job_ids"][0])
    assert child["parent_job_id"] == old[0] and child["scene_id"] == sids[0] and child["state"] == "queued"


def test_gate_only_receives_chosen_shots_and_rejects_before_any_job(case):
    from core import batch
    p, pid, sids, gates, *_ = case
    def gate(p, pid, data_dir, scene_ids):
        return {"block": ["cảnh bị giữ"] if sids[1] in scene_ids else [], "warn": []}
    gates.side_effect = gate
    result = batch.queue_images(p, pid, scene_ids=[sids[0]])
    assert result["created"] == 1
    with pytest.raises(batch.GateError):
        batch.queue_images(p, pid, scene_ids=[sids[1]])
    assert _job_scenes(p) == [sids[0]]


def test_empty_or_unknown_selection_does_not_call_gates_or_create_jobs(case):
    from core import batch
    p, pid, sids, gates, *_ = case
    for selection in ([], [999999]):
        assert batch.queue_images(p, pid, scene_ids=selection)["job_ids"] == []
    assert not gates.called and _job_scenes(p) == []


@pytest.mark.parametrize("bad", [[True], ["1"], [1.5]])
def test_malformed_selection_fails_before_creating_jobs(case, bad):
    from core import batch
    p, pid, sids, gates, *_ = case
    with pytest.raises(ValueError):
        batch.queue_images(p, pid, scene_ids=bad)
    assert _job_scenes(p) == []


def test_generator_and_duplicate_scene_ids_are_consumed_once(case):
    from core import batch
    p, pid, sids, *_ = case
    result = batch.queue_images(p, pid, scene_ids=(sid for sid in [sids[2], sids[0], sids[2]]))
    assert _job_scenes(p) == [sids[0], sids[2]]
    assert len(result["job_ids"]) == 2


def test_legacy_none_does_not_add_a_new_failure_if_reopen_has_no_child(case):
    from core import batch
    p, pid, sids, gates, scan, allowed, stack = case
    old = p.create_job(sids[0], "image_gen")
    p.conn.execute("UPDATE jobs SET state='approved'")
    p.conn.commit()
    scan.return_value = {sids[0]: {"image_stale": "đổi đầu vào", "image_job_id": old}}
    stack.enter_context(patch.object(p, "reopen_approved", return_value="rejected"))
    # Caller cũ không yêu cầu selected job IDs, nên không thêm một GateError mới.
    result = batch.queue_images(p, pid)
    assert result["created"] == 3 and result["redo"] == 1
    assert len(result["job_ids"]) == 3


def test_existing_runner_only_sends_returned_job_ids_not_other_queued_shot(case, tmp_path):
    from core import batch
    from core.providers import MockImageProvider
    from core.runner import ImageRunner, THROTTLE
    p, pid, sids, gates, scan, allowed, stack = case
    excluded = p.create_job(sids[1], "image_gen")
    result = batch.queue_images(p, pid, scene_ids=[sids[0], sids[2]])
    provider = MockImageProvider()
    runner = ImageRunner(p, provider, str(tmp_path), max_concurrent=5)
    for name, value in (("_wait", False), ("_gate_hold", None), ("_blocked", None),
                        ("_submit_args", ("fixture image",)), ("_prepare_kwargs", {}), ("_pregen", False),
                        ("_over_budget", None), ("_stamp", {}), ("_write_sent_package", []),
                        ("_record_usage", None), ("_say_package", None), ("_remember_flags", None)):
        stack.enter_context(patch.object(runner, name, return_value=value))
    stack.enter_context(patch.object(THROTTLE, "allow", return_value=True))
    assert runner.submit_pending(pid, only=result["job_ids"]) == 2
    assert p.job(excluded)["state"] == "queued" and p.job(excluded)["external_id"] is None
    assert all(p.job(jid)["state"] == "running" for jid in result["job_ids"])
    assert len(provider.prompts) == 2


def test_failed_targeted_batch_leaves_no_sendable_jobs_and_keeps_competitor(case):
    from core import batch, bg_poll
    from core.pipeline import Pipeline
    p, pid, sids, gates, scan, allowed, stack = case
    competitor = p.create_job(sids[3], "image_gen")
    insert = Pipeline._insert_job
    def fail_second(self, project_id, scene_id, *args, **kwargs):
        if scene_id == sids[1]:
            raise RuntimeError("fixture second job failure")
        return insert(self, project_id, scene_id, *args, **kwargs)
    with patch.object(Pipeline, "_insert_job", fail_second):
        with pytest.raises(RuntimeError):
            batch.queue_images(p, pid, scene_ids=sids[:2])
    assert [r[0] for r in p.conn.execute("SELECT id FROM jobs WHERE state='queued'")] == [competitor]
    assert [jid for v in bg_poll.queued_by_person(p.conn).values() for jid in v["send"]] == [competitor]


def test_failed_redo_rolls_back_parent_review_and_fresh_job(case):
    from core import batch
    p, pid, sids, gates, scan, allowed, stack = case
    parent = p.create_job(sids[0], "image_gen")
    p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (parent,))
    p.conn.commit()
    scan.return_value = {sids[0]: {"image_stale": "fixture changed", "image_job_id": parent}}
    class FailPlan:
        def apply(self):
            raise RuntimeError("fixture redo failure")
    stack.enter_context(patch.object(p, "_rewrite_before_retry", return_value=FailPlan()))
    with pytest.raises(RuntimeError):
        batch.queue_images(p, pid, scene_ids=sids[:2])
    assert p.job(parent)["state"] == "approved"
    assert p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
    assert p.conn.execute("SELECT COUNT(*) FROM review_log").fetchone()[0] == 0


def test_reopen_can_return_its_actual_child_without_claiming_other_child(case):
    p, pid, sids, gates, scan, allowed, stack = case
    parent = p.create_job(sids[0], "image_gen")
    p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (parent,))
    p.conn.commit()
    competitor = p._insert_job(pid, sids[0], "image_gen", parent_job_id=parent)
    stack.enter_context(patch.object(p, "_rewrite_before_retry", return_value=type("Keep", (), {"apply": lambda self: None})()))
    child = p.reopen_approved(parent, fix="", reason="khong_phai_loi", return_job_id=True)
    assert isinstance(child, int) and child != competitor
    assert p.job(child)["parent_job_id"] == parent
    assert p.job(competitor)["state"] == "queued"


def test_targeted_success_preserves_outer_transaction_and_original_pipeline(case):
    from core import batch
    p, pid, sids, *_ = case
    original = p.conn
    p.conn.execute("BEGIN")
    result = batch.queue_images(p, pid, scene_ids=sids[:2])
    assert len(result["job_ids"]) == 2
    assert p.conn is original and p.conn.in_transaction
    p.conn.rollback()
    assert p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


def test_targeted_partial_jobs_are_invisible_to_other_connection(case, tmp_path):
    import sqlite3
    from core import batch
    from core.pipeline import Pipeline
    p, pid, sids, *_ = case
    original = p.conn
    path = str(tmp_path / "atomic-fixture.sqlite")
    writer = sqlite3.connect(path)
    original.backup(writer)
    writer.row_factory = sqlite3.Row
    observer = sqlite3.connect(path)
    insert = Pipeline._insert_job
    def observe_after_insert(self, *args, **kwargs):
        jid = insert(self, *args, **kwargs)
        assert observer.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
        return jid
    p.conn = writer
    try:
        with patch.object(Pipeline, "_insert_job", observe_after_insert):
            result = batch.queue_images(p, pid, scene_ids=sids[:2])
        assert len(result["job_ids"]) == 2
        assert observer.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 2
    finally:
        p.conn = original
        observer.close()
        writer.close()


def test_atomic_helper_cannot_commit_by_transaction_sql(case):
    p, pid, sids, *_ = case
    with pytest.raises(RuntimeError):
        with p.atomic_image_batch() as scoped:
            scoped.create_job(sids[0], "image_gen")
            scoped.conn.execute("COMMIT")
    assert p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
