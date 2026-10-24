"""Kiểm thử giám sát kế hoạch bằng fixture tạm, không chạy provider hay dữ liệu live."""
import json
import os
from pathlib import Path
from unittest import mock

import pytest

_FAKE_ENV = {
    "PATH": r"C:\fixture\bin", "PATHEXT": ".COM;.EXE;.BAT;.CMD", "SYSTEMROOT": r"C:\fixture\windows",
    "WINDIR": r"C:\fixture\windows", "TEMP": r"C:\fixture\temp", "TMP": r"C:\fixture\temp",
    "USERPROFILE": r"C:\fixture\user", "APPDATA": r"C:\fixture\user\appdata",
    "LOCALAPPDATA": r"C:\fixture\user\local", "PROGRAMDATA": r"C:\fixture\programdata",
    "HOME": r"C:\fixture\user", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
}
with mock.patch.object(os, "environ", _FAKE_ENV):
    from devsys import plan_map, plan_monitor as PM


def _bundle():
    return {"area": PM.AREA_ID, "prompt": "fixture prompt", "facts": {}, "input_hash": "old", "fingerprint": "base"}


def _score_record(findings=None):
    return {
        "area": PM.AREA_ID,
        "criteria": {
            "chuc_nang": {"max": 10, "deductions": [{"points": 2}, {"points": 7, "auto": True}]},
            "tin_cay": {"max": 10, "deductions": [{"points": 4}]},
            "trai_nghiem": {"max": 10, "deductions": [{"points": 6}]},
        },
        "raw": {"plan_findings": findings or []},
    }


def _finding(**overrides):
    return {
        "axis": "errors", "severity": "LỚN", "type": "regression", "evidence": ["tests/test_fake.py:7"],
        "task_id": "M4.1", "title": "Lỗi hồi quy trong fixture", "source": "test giả", "weight": 2,
        **overrides,
    }


def test_config_keeps_auto_off_and_rejects_unapproved_provider(tmp_path):
    devsys = tmp_path / "devsys"
    devsys.mkdir()
    assert PM.load_config(str(tmp_path))["auto_enabled"] is False
    (devsys / "giam_sat_config.json").write_text(
        json.dumps({"auto_enabled": True, "provider": "anthropic", "publish_plan": False}), encoding="utf-8"
    )
    config = PM.load_config(str(tmp_path))
    assert config == {"auto_enabled": True, "provider": "claude_cli", "publish_plan": False}


def test_child_environment_is_an_explicit_allowlist():
    fake = {"PATH": "fixture-path", "SECRET_TOKEN": "fixture-secret", "PYTHONUTF8": "0"}
    with mock.patch.object(PM.os, "environ", fake):
        env = PM._child_env()
    assert env["PATH"] == "fixture-path"
    assert env["PYTHONUTF8"] == "1"
    assert "SECRET_TOKEN" not in env


def test_bundle_reuses_scorer_and_hashes_plan_evidence(monkeypatch, tmp_path):
    cfg, snap = {"areas": []}, {"fixture": True}
    monkeypatch.setattr(PM.collect, "area_health", lambda _snap, _cfg: {})
    monkeypatch.setattr(PM.scorer, "plan", lambda *_a, **_k: {"todo": [_bundle()]})
    evidence = {"goals": "fixture goals", "mailbox": "untrusted fixture message", "rubric": "fixture rubric"}
    monkeypatch.setattr(PM, "evidence_text", lambda *_a, **_k: evidence)
    result = PM.build_bundle(str(tmp_path), provider="mock", snap=snap, cfg=cfg)
    assert result["area"] == PM.AREA_ID
    assert "fixture goals" in result["prompt"]
    assert result["facts"]["plan_evidence"] == list(evidence)
    assert result["input_hash"] != "old"
    with pytest.raises(PM.PlanMonitorError):
        PM.build_bundle(str(tmp_path), provider="anthropic", snap=snap, cfg=cfg)


def test_score_axes_are_computed_from_shared_deductions():
    score = PM.aggregate_score(_score_record([_finding(severity="CHẶN")]))
    assert score["axes"] == {"direction": 8.0, "errors": 6.0, "dashboard": 4.0}
    assert score["overall"] == 6.3
    assert score["label"] == "CHẶN"
    assert score["open_blockers"] == 1


def test_major_findings_overlay_only_matching_task_wave_and_stage():
    task = {"id": "M4.1", "status": "🔄", "commit": "", "title": "fixture", "gate_status": "⬜"}
    model = {"current": "M4", "next": None, "total": 0.0, "total_gate": 0.0,
             "waves": [{"id": "M4", "name": "Fixture", "pct": 0.0, "pct_gate": 0.0, "tasks": [task]}],
             "rows": [{"id": "L1", "ten": "fixture", "kind": "ok", "open_errors": 0,
                       "pct": 0.0, "pct_gate": 0.0, "tasks": [task]}]}
    overlay = PM.annotate_plan_map(model, [_finding(severity="CHẶN")], {"M4.1": ["L1"]})
    assert "monitor_severity" not in model["waves"][0]["tasks"][0]
    assert overlay["waves"][0]["monitor_tasks"] == ["M4.1"]
    assert overlay["rows"][0]["monitor_severity"] == "CHẶN"
    roadmap = plan_map.roadmap_svg(overlay, "Fixture")
    stage_svg = plan_map.stages_svg(overlay, "Fixture")
    assert "GIÁM SÁT CHẶN" in roadmap
    assert "GIÁM SÁT CHẶN" in stage_svg


def test_proposal_command_is_escaped_and_only_a_draft_for_main():
    command = PM.proposal_command(_finding(title="mô tả 'fixture'"))
    assert command.startswith("$env:PYTHONUTF8='1'; py tools/hop_thu.py giao CX24-GS-")
    assert "--to phien-chinh" in command
    assert "LỚN: mô tả ''fixture'''" in command
    assert "--lane codex" in command


def test_manual_control_estimates_only_on_request_and_passes_the_hash(monkeypatch, tmp_path):
    class UI:
        def __init__(self, pressed=()):
            self.pressed = set(pressed)
            self.session_state = {}
            self.messages = []

        def button(self, label, key):
            return key in self.pressed

        def caption(self, value):
            self.messages.append(value)

        def warning(self, value):
            self.messages.append(value)

        def error(self, value):
            self.messages.append(value)

        def success(self, value):
            self.messages.append(value)

    calls, spawned = [], []
    monkeypatch.setattr(PM, "prepare", lambda *_a, **_k: calls.append("estimate") or {
        "bundle": {"input_hash": "fixture-hash"}, "estimate": {"input_tokens": 17, "usd_api": 0.0}
    })
    ui = UI({"plan_monitor_estimate"})
    PM.render_manual_control(ui, str(tmp_path), lambda args, _log: spawned.append(list(args)) or 321)
    assert calls == ["estimate"] and not spawned
    assert any("17 token" in message for message in ui.messages)
    ui.pressed = {"plan_monitor_run"}
    PM.render_manual_control(ui, str(tmp_path), lambda args, _log: spawned.append(list(args)) or 321)
    assert calls == ["estimate"]
    assert spawned[0][-1] == "fixture-hash"
    assert any("PID 321" in message for message in ui.messages)


def test_publish_preflight_only_allows_clean_main_and_the_configured_plan(monkeypatch, tmp_path):
    devsys = tmp_path / "devsys"
    docs = tmp_path / "docs"
    devsys.mkdir()
    docs.mkdir()
    (devsys / "plans.json").write_text('[{"kieu":"viec_s","file":"docs/plan.md","chinh":true}]', encoding="utf-8")
    plan = docs / "plan.md"
    plan.write_text("fixture", encoding="utf-8")
    monkeypatch.setattr(PM.plan_progress, "main_plan_file", lambda _root: str(plan))
    state = {"branch --show-current": "main", "rev-parse HEAD": "same", "rev-parse origin/main": "same",
             "diff --cached --name-only": "", "status --porcelain=v1 --untracked-files=no": ""}
    monkeypatch.setattr(PM, "_git_output", lambda _root, *args: state[" ".join(args)])
    assert PM._publish_preflight(str(tmp_path), plan, allow_plan_modified=False) == "docs/plan.md"
    state["status --porcelain=v1 --untracked-files=no"] = " M docs/unrelated.md"
    with pytest.raises(PM.PlanMonitorError):
        PM._publish_preflight(str(tmp_path), plan, allow_plan_modified=True)
    state["status --porcelain=v1 --untracked-files=no"] = ""
    state["branch --show-current"] = "codex/v31-giam-sat"
    with pytest.raises(PM.PlanMonitorError):
        PM._publish_preflight(str(tmp_path), plan, allow_plan_modified=False)


def test_trigger_detection_emits_new_done_and_first_milestone_once():
    previous = {"tasks": {"M4.1": "🔄"}, "waves": [{"id": "M4", "percent": 24}]}
    current = {"tasks": {"M4.1": "✅"}, "waves": [{"id": "M4", "percent": 26}]}
    triggers = PM.detect_triggers(previous, current)
    assert {row["id"] for row in triggers} == {"task:M4.1:done", "wave:M4:25"}
    assert PM.detect_triggers(previous, current, {"task:M4.1:done"}) == [
        {"id": "wave:M4:25", "kind": "milestone", "wave_id": "M4", "percent": 26, "threshold": 25}
    ]
    assert PM.detect_triggers(current, current) == []


def test_auto_trigger_spawns_once_and_persists_seen_state(monkeypatch, tmp_path):
    devsys = tmp_path / "devsys"
    devsys.mkdir()
    (devsys / "giam_sat_config.json").write_text(
        json.dumps({"auto_enabled": True, "provider": "mock", "publish_plan": False}), encoding="utf-8"
    )
    previous = {"tasks": {"M4.1": "🔄"}, "waves": [{"id": "M4", "percent": 24}]}
    current = {"tasks": {"M4.1": "✅"}, "waves": [{"id": "M4", "percent": 26}]}
    state_path = PM.history_dir(str(tmp_path)) / "trigger_state.json"
    PM._save_json(state_path, {"snapshot": previous, "seen": [], "pending": []})
    monkeypatch.setattr(PM, "progress_snapshot", lambda _root: current)
    monkeypatch.setattr(PM, "prepare", lambda *_a, **_k: {"bundle": {"input_hash": "fixture-hash"}, "estimate": {"input_tokens": 7, "usd_api": 0.0}})
    spawned = []

    def fake_spawn(args, log_name):
        spawned.append((list(args), log_name))
        return 123

    first = PM.check_auto_triggers(str(tmp_path), fake_spawn)
    second = PM.check_auto_triggers(str(tmp_path), fake_spawn)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert first["state"] == "spawned" and len(first["spawned"]) == 2
    assert len(spawned) == 1
    assert second["state"] == "no_change"
    assert set(state["seen"]) == {"task:M4.1:done", "wave:M4:25"}
    assert "--provider" in spawned[0][0] and "mock" in spawned[0][0]


def test_auto_trigger_keeps_failed_work_pending_for_retry(monkeypatch, tmp_path):
    devsys = tmp_path / "devsys"
    devsys.mkdir()
    (devsys / "giam_sat_config.json").write_text(json.dumps({"auto_enabled": True, "provider": "mock"}), encoding="utf-8")
    previous = {"tasks": {"M4.1": "🔄"}, "waves": []}
    current = {"tasks": {"M4.1": "✅"}, "waves": []}
    state_path = PM.history_dir(str(tmp_path)) / "trigger_state.json"
    PM._save_json(state_path, {"snapshot": previous, "seen": [], "pending": []})
    monkeypatch.setattr(PM, "progress_snapshot", lambda _root: current)
    monkeypatch.setattr(PM, "prepare", lambda *_a, **_k: {"bundle": {"input_hash": "fixture-hash"}, "estimate": {"input_tokens": 7, "usd_api": 0.0}})
    failed = PM.check_auto_triggers(str(tmp_path), lambda *_a: (_ for _ in ()).throw(OSError("fixture")))
    assert failed["state"] == "failed"
    assert json.loads(state_path.read_text(encoding="utf-8"))["pending"][0]["id"] == "task:M4.1:done"
    retried = PM.check_auto_triggers(str(tmp_path), lambda *_a: 456)
    assert retried["state"] == "spawned"
    assert json.loads(state_path.read_text(encoding="utf-8"))["seen"] == ["task:M4.1:done"]


def test_monitor_lock_rejects_a_second_holder(tmp_path):
    with PM.monitor_lock(str(tmp_path)) as first:
        assert first is True
        with PM.monitor_lock(str(tmp_path)) as second:
            assert second is False
    assert not PM._lock_path(str(tmp_path)).exists()


def test_run_monitor_writes_only_the_fake_plan_and_saves_report(monkeypatch, tmp_path):
    devsys = tmp_path / "devsys"
    devsys.mkdir()
    (devsys / "rubric_plan.md").write_text("# fixture rubric", encoding="utf-8")
    (devsys / "plans.json").write_text(
        json.dumps([{"kieu": "viec_s", "file": "docs/plan.md", "chinh": True}]), encoding="utf-8"
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    plan_path = docs / "plan.md"
    plan_path.write_text(
        "<!-- tien-do -->\n<!-- /tien-do -->\n\n### M4 — Fake\n- [ ] M4.1 · Fake task · nặng:2 · 🔄\n\n### M9 — Giám sát\n- [ ] M9.0 · Quy tắc · nặng:1 · ✅\n\n## 6. Nhật ký\n",
        encoding="utf-8",
    )
    cfg, snap = {"areas": []}, {"fixture": True}
    monkeypatch.setattr(PM, "_score_area_config", lambda _root: cfg)
    monkeypatch.setattr(PM.collect, "collect", lambda *_a, **_k: snap)
    monkeypatch.setattr(PM, "build_bundle", lambda *_a, **_k: {
        **_bundle(), "plan_evidence": {"goals": "fixture evidence"}
    })
    monkeypatch.setattr(PM, "estimate", lambda *_a, **_k: {"input_tokens": 99, "usd_api": 0.0})
    saved = tmp_path / "scored.json"
    saved.write_text(json.dumps(_score_record([_finding()])), encoding="utf-8")

    def fake_run(*_args, **_kwargs):
        return {"failed": [], "saved": [str(saved)]}

    monkeypatch.setattr(PM.scorer, "run", fake_run)
    before = plan_path.read_text(encoding="utf-8")
    with pytest.raises(PM.PlanMonitorError):
        PM.run_monitor(str(tmp_path), provider="mock", publish_plan=False, expected_input_hash="stale-fixture-hash")
    assert plan_path.read_text(encoding="utf-8") == before
    result = PM.run_monitor(str(tmp_path), provider="mock", publish_plan=False)
    text = plan_path.read_text(encoding="utf-8")
    parsed = PM.plan_progress.parse(text)
    assert result["busy"] is False, result.get("error")
    assert result["record"]["score"]["label"] == "ĐẠT RÀ SOÁT", result["record"]["score"]
    assert result["plan_write"]["changed"] is True, result["plan_write"]
    assert any(task["id"] == "M9.1" for wave in parsed["waves"] if wave["id"] == "M9" for task in wave["tasks"])
    assert "fixture evidence" in result["report"] or Path(result["report"]).is_file()
    assert list((tmp_path / "devsys" / "data" / "giam_sat").glob("*.md"))






def test_writer_rejects_path_traversal_evidence_without_mutating_plan(tmp_path):
    from devsys import plan_writer

    fixture = "\n".join([
        "### M4 — Fake",
        "- [ ] M4.1 · Fake task · nặng:2 · 🔄",
        "",
        "### M9 — Giám sát",
        "- [ ] M9.0 · Quy tắc · nặng:1 · ✅",
        "",
        "## 6. Nhật ký",
        "",
    ])
    plan = tmp_path / "plan.md"
    plan.write_text(fixture, encoding="utf-8")
    with pytest.raises(plan_writer.PlanWriterError):
        plan_writer.apply_findings(str(plan), [_finding(evidence="../outside.py:1")])
    assert plan.read_text(encoding="utf-8") == fixture


def test_monitor_refuses_main_plan_fallback_outside_fixture_root(tmp_path):
    devsys = tmp_path / "devsys"
    devsys.mkdir()
    (devsys / "plans.json").write_text(
        '[{"kieu":"viec_s","file":"../../outside-plan.md","chinh":true}]', encoding="utf-8"
    )
    with pytest.raises(PM.PlanMonitorError):
        PM._main_plan_path(str(tmp_path))
