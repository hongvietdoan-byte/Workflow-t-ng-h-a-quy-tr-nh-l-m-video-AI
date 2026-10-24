"""CX24-M82B: giá selected dùng DB giả và cùng chính sách giá hiện hành."""
import json
import os
from contextlib import ExitStack
from unittest.mock import patch
import pytest

@pytest.fixture
def case(tmp_path):
    with ExitStack() as stack:
        stack.enter_context(patch.object(os, "environ", {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path), "TEMP": str(tmp_path), "TMP": str(tmp_path), "PYTHONUTF8": "1"}))
        from core import batch, cost, features, llm_provider, pilot, shots, scene_establish, end_frames, qc_scene, qc_agent, qc_team
        from core.db import connect
        from core.pipeline import Pipeline
        stack.enter_context(patch.object(features, "on", return_value=False))
        stack.enter_context(patch.object(llm_provider, "snapshot_job"))
        scan = stack.enter_context(patch.object(batch.lineage, "scan", return_value={}))
        allowed = stack.enter_context(patch.object(pilot, "allowed_scenes", side_effect=lambda p, pid, ids: list(ids)))
        stack.enter_context(patch.object(shots, "needs_own_image", return_value=True))
        stack.enter_context(patch.object(scene_establish, "enabled", return_value=False))
        stack.enter_context(patch.object(end_frames, "enabled", return_value=False))
        stack.enter_context(patch.object(qc_scene, "active", return_value=False))
        stack.enter_context(patch.object(qc_agent, "enabled", return_value=False))
        stack.enter_context(patch.object(qc_team, "active", return_value=False))
        stack.enter_context(patch.object(cost, "llm_estimate", side_effect=lambda conn, stage, calls, pricing, **kw: calls * .2))
        stack.enter_context(patch.object(cost, "chat_prompt_estimate", side_effect=lambda conn, n, pricing: n * .1))
        p = Pipeline(connect())
        pid = p.create_project("Giả", max_retry=2)
        ids = [p.create_scene(pid, n, "Giả") for n in range(1, 5)]
        for n, sid in enumerate(ids):
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"story_scene": n // 2 + 1}), sid))
        p.conn.commit()
        pricing = {"currency": "USD", "per_image": {"fake": 3}}
        yield p, pid, ids, pricing, cost, stack, scan, allowed
        p.conn.close()

# Baseline lấy từ core/cost.py tại ce04503a (c2a79019^), nạp module riêng
# trong môi trường giả, DB fixture và cùng mock D6/QC; không chạy mã cũ ở production.
LEGACY_QUOTE_BYTES = b'{"kind":"image","items":4,"seconds":0,"unit_price":3.0,"known":true,"unit_over":3.0,"currency":"USD","max_retry":2,"end_frames":0,"establishing":0,"chat_prompt":0.4,"min":13.44,"max":40.32,"outside_note":"","parts":[{"label":"\\u1ea3nh khung \\u0111\\u1ea7u c\\u00e1c shot","count":4,"usd":12.0},{"label":"Claude vi\\u1ebft l\\u1ea1i prompt tr\\u01b0\\u1edbc khi g\\u1eedi (D6)","count":4,"usd":0.4},{"label":"Claude ch\\u1ea5m \\u1ea3nh (QC)","count":4,"usd":1.04}],"qc":1.04,"outside":0.0,"total":13.44}'

def test_none_preserves_exact_serialized_quote(case):
    p, pid, ids, pricing, cost, *_ = case
    for kwargs in ({}, {"scene_ids": None}):
        actual = cost.estimate_images(p, pid, pricing, "fake", **kwargs)
        assert json.dumps(actual, separators=(",", ":")).encode("ascii") == LEGACY_QUOTE_BYTES

def test_two_selected_keep_existing_d6_qc_and_retry_formula(case):
    p, pid, ids, pricing, cost, *_ = case
    result = cost.estimate_images(p, pid, pricing, "fake", scene_ids=iter([ids[0], ids[2], ids[0]]))
    assert result["items"] == 2 and result["chat_prompt"] == .2
    assert result["qc"] == pytest.approx(.4 * cost.LLM_MARGIN)
    assert result["total"] == 6.72 and result["max"] == pytest.approx(20.16)

def test_pilot_and_project_scope_exclude_other_shots(case):
    p, pid, ids, pricing, cost, stack, scan, allowed = case
    other = p.create_project("Khác giả")
    foreign = p.create_scene(other, 1, "Giả")
    allowed.side_effect = lambda p, pid, values: [sid for sid in values if sid == ids[0]]
    assert cost.estimate_images(p, pid, pricing, "fake", scene_ids=ids + [foreign])["items"] == 1

@pytest.mark.parametrize("selected", [[], [True], ["1"], [0]])
def test_empty_or_invalid_selection_never_prices_whole_project(case, selected):
    p, pid, ids, pricing, cost, *_ = case
    if selected:
        with pytest.raises(ValueError):
            cost.estimate_images(p, pid, pricing, "fake", scene_ids=selected)
    else:
        result = cost.estimate_images(p, pid, pricing, "fake", scene_ids=selected)
        assert result["items"] == 0 and result["total"] == 0

def test_redo_is_priced_but_preexisting_queued_job_is_not_new_batch(case):
    p, pid, ids, pricing, cost, stack, scan, allowed = case
    old = p.create_job(ids[0], "image_gen")
    p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (old,))
    p.conn.commit()
    p.create_job(ids[1], "image_gen")
    scan.return_value = {ids[0]: {"image_stale": "đổi giả", "image_job_id": old}}
    assert cost.estimate_images(p, pid, pricing, "fake", scene_ids=ids[:2])["items"] == 1

def test_end_frames_and_shared_establishing_only_for_selected_targets(case):
    p, pid, ids, pricing, cost, stack, *_ = case
    from core import end_frames, scene_establish, place_refs
    stack.enter_context(patch.object(end_frames, "enabled", return_value=True))
    stack.enter_context(patch.object(end_frames, "wanted", return_value=True))
    stack.enter_context(patch.object(end_frames, "current", return_value=None))
    stack.enter_context(patch.object(scene_establish, "enabled", return_value=True))
    stack.enter_context(patch.object(scene_establish, "picture", return_value=None))
    stack.enter_context(patch.object(place_refs, "enabled", return_value=False))
    result = cost.estimate_images(p, pid, pricing, "fake", data_dir="fake", scene_ids=ids[:2])
    assert result["items"] == 5 and result["end_frames"] == 2 and result["establishing"] == 1

def test_unknown_model_uses_same_existing_money_policy_fallback(case):
    p, pid, ids, pricing, cost, stack, *_ = case
    from core import money_policy
    fallback = stack.enter_context(patch.object(money_policy, "estimate", return_value={"usd": 7}))
    result = cost.estimate_images(p, pid, pricing, "unpriced-fake", scene_ids=ids[:1])
    assert result["known"] is False and result["unit_over"] == 7 and result["total"] == 7.36
    assert fallback.call_count == 1

@pytest.mark.parametrize("mode", ["scene", "agent"])
def test_selected_qc_shared_scene_once_and_no_outside_scene(case, mode):
    p, pid, ids, pricing, cost, stack, *_ = case
    from core import qc_scene, qc_agent
    stack.enter_context(patch.object(qc_scene, "active", return_value=True))
    stack.enter_context(patch.object(qc_scene, "claude_on", return_value=True))
    stack.enter_context(patch.object(qc_agent, "enabled", return_value=mode == "agent"))
    result = cost.estimate_images(p, pid, pricing, "fake", scene_ids=ids[:2])
    # Hai shot đầu chung story_scene=1; story_scene=2 ngoài lựa chọn không được tính.
    expected = cost.AGENT_SCENE_USD if mode == "agent" else .2 * (1 + cost.REDRAW_SHARE)
    assert result["qc"] == pytest.approx(expected * cost.LLM_MARGIN)
    assert result["total"] == round(6 + .2 + expected * cost.LLM_MARGIN, 4)

@pytest.mark.parametrize("reused", ["ready_picture", "free_3d"])
def test_selected_establishing_reuses_existing_picture_or_free_render(case, reused):
    p, pid, ids, pricing, cost, stack, *_ = case
    from core import scene_establish, place_refs
    stack.enter_context(patch.object(scene_establish, "enabled", return_value=True))
    picture = stack.enter_context(patch.object(scene_establish, "picture", return_value="fake-ready" if reused == "ready_picture" else None))
    stack.enter_context(patch.object(place_refs, "enabled", return_value=True))
    rows = stack.enter_context(patch.object(scene_establish, "scene_rows", return_value=[{"fake": "rows"}]))
    render = stack.enter_context(patch.object(place_refs, "scene_render_rec", return_value={"fake": "render"}))
    result = cost.estimate_images(p, pid, pricing, "fake", data_dir="fake-root", scene_ids=ids[:2])
    assert result["establishing"] == 0 and result["items"] == 2
    assert picture.call_count == 1 and picture.call_args.args == ("fake-root", pid, 1)
    assert rows.call_count == (0 if reused == "ready_picture" else 1)
    assert render.call_count == (0 if reused == "ready_picture" else 1)
