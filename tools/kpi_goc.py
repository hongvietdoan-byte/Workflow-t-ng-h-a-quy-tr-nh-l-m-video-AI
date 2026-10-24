"""Measure five V3 targets from an explicitly selected isolated-copy bundle.

No default database, environment lookup, subprocess, network, or DB writes.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path, PurePosixPath
import sqlite3
import sys
from typing import Any

MANIFEST_NAME = "kpi_goc_manifest.json"
SCHEMA_VERSION = 1
REQUIRED_MT3_BASELINE = (24, 27, 31)
TABLES = ("jobs", "usage_events", "scenes", "qc_results", "diag_events")


class KpiInputError(ValueError):
    """Unsafe or invalid copy-bundle input."""


def _is_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    checker = getattr(path, "is_junction", None)
    return bool(checker and checker())


def _reject_reparse_ancestors(path: Path) -> None:
    absolute = path.absolute()
    for candidate in reversed((absolute, *absolute.parents)):
        if _is_reparse(candidate):
            raise KpiInputError("input path cannot use symlinks or junctions")


def _is_live_data_path(path: Path) -> bool:
    return any(
        ancestor.name.casefold() == "data"
        and ancestor.parent.name.casefold() == "ai-video-pipeline"
        for ancestor in (path, *path.parents)
    )


def _relative_file(root: Path, raw: Any, suffixes: tuple[str, ...] | None = None) -> Path:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise KpiInputError("manifest path must be a POSIX relative path")
    rel = PurePosixPath(raw)
    if rel.is_absolute() or any(part in ("", ".", "..") for part in rel.parts):
        raise KpiInputError("manifest path escapes the isolated bundle")
    candidate = root.joinpath(*rel.parts)
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        if _is_reparse(cursor):
            raise KpiInputError("bundle cannot contain symlinks or junctions")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        raise KpiInputError("a declared snapshot file is missing") from None
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise KpiInputError("manifest path escapes the isolated bundle")
    if suffixes and resolved.suffix.casefold() not in suffixes:
        raise KpiInputError("snapshot input has an unsupported file type")
    return resolved


def open_db_readonly(path: str | Path) -> sqlite3.Connection:
    """Open an existing SQLite snapshot in URI read-only and query-only modes."""
    _reject_reparse_ancestors(Path(path))
    try:
        db = Path(path).resolve(strict=True)
    except OSError:
        raise KpiInputError("snapshot database is missing") from None
    if not db.is_file() or db.suffix.casefold() not in {".sqlite", ".sqlite3", ".db"}:
        raise KpiInputError("snapshot database must be an existing SQLite file")
    if _is_live_data_path(db):
        raise KpiInputError("the live project data directory is forbidden; use an isolated copy outside it")
    conn = None
    try:
        conn = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=3)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        return conn
    except sqlite3.Error:
        if conn is not None:
            conn.close()
        raise KpiInputError("snapshot database could not be opened read-only") from None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    if table not in TABLES:
        return set()
    return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})")}


def _count_project(conn: sqlite3.Connection, table: str, project_id: int) -> int | None:
    columns = _columns(conn, table)
    if not columns:
        return None
    if "project_id" in columns:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE project_id = ?", (project_id,)).fetchone()[0])
    tables = {str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if table == "usage_events" and "job_id" in columns and "jobs" in tables:
        if {"id", "project_id"} <= _columns(conn, "jobs"):
            return int(conn.execute(
                "SELECT COUNT(*) FROM usage_events u JOIN jobs j ON j.id=u.job_id WHERE j.project_id = ?",
                (project_id,),
            ).fetchone()[0])
    if table == "qc_results" and "job_id" in columns and "jobs" in tables:
        if not {"id", "project_id"} <= _columns(conn, "jobs"):
            return None
        return int(conn.execute(
            "SELECT COUNT(*) FROM qc_results q JOIN jobs j ON j.id=q.job_id WHERE j.project_id = ?",
            (project_id,),
        ).fetchone()[0])
    return None


def read_db_facts(path: str | Path, project_id: int) -> dict[str, Any]:
    """Return aggregate counts only; never return database rows or user content."""
    conn = open_db_readonly(path)
    try:
        tables = {str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        facts = {
            "project_id": project_id,
            "available_tables": sorted(tables.intersection(TABLES)),
            "job_count": _count_project(conn, "jobs", project_id),
            "scene_count": _count_project(conn, "scenes", project_id),
            "qc_result_count": _count_project(conn, "qc_results", project_id),
            "diagnostic_count": _count_project(conn, "diag_events", project_id),
            "paid_usage_events": None,
        }
        columns = _columns(conn, "usage_events")
        if "usage_events" in tables and "provider" in columns:
            if "project_id" in columns:
                facts["paid_usage_events"] = int(conn.execute(
                    "SELECT COUNT(*) FROM usage_events WHERE project_id = ? AND lower(provider) NOT LIKE 'mock%'",
                    (project_id,),
                ).fetchone()[0])
            elif "job_id" in columns and "jobs" in tables:
                facts["paid_usage_events"] = int(conn.execute(
                    "SELECT COUNT(*) FROM usage_events u JOIN jobs j ON j.id=u.job_id "
                    "WHERE j.project_id = ? AND lower(u.provider) NOT LIKE 'mock%'",
                    (project_id,),
                ).fetchone()[0])
        return facts
    except sqlite3.Error:
        raise KpiInputError("snapshot database schema could not be read") from None
    finally:
        conn.close()


def _json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise KpiInputError(f"{label} is missing or invalid JSON") from None
    if not isinstance(value, dict):
        raise KpiInputError(f"{label} must be a JSON object")
    return value


def _load_entry(raw: Any, root: Path, seen: set[int]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise KpiInputError("snapshot entry must be an object")
    project_id = raw.get("project_id")
    if type(project_id) is not int or project_id <= 0 or project_id in seen:
        raise KpiInputError("snapshot project_id must be unique and positive")
    seen.add(project_id)
    label = raw.get("label")
    if not isinstance(label, str) or not label.strip() or len(label) > 40:
        raise KpiInputError("snapshot label is missing or too long")
    db_path = _relative_file(root, raw.get("db"), (".sqlite", ".sqlite3", ".db"))
    live_db = None
    for ancestor in (root, *root.parents):
        if ancestor.name.casefold() == "ai-video-pipeline":
            live_db = ancestor / "data" / "manifest.sqlite"
            break
    if live_db is not None and db_path == live_db.resolve():
        raise KpiInputError("the live database is forbidden; pass an isolated copy")
    evidence_path = raw.get("evidence")
    if evidence_path is not None:
        evidence_path = _relative_file(root, evidence_path, (".json",))
        evidence = _json_object(evidence_path, "snapshot evidence")
        if evidence.get("schema_version") != SCHEMA_VERSION or evidence.get("project_id") != project_id:
            raise KpiInputError("snapshot evidence version or project_id does not match")
        for metric in ("mt1", "mt2", "mt3", "mt4", "mt5"):
            if evidence.get(metric) is not None and not isinstance(evidence[metric], dict):
                raise KpiInputError("metric evidence must be an object")
    else:
        evidence = None
    return {
        "project_id": project_id,
        "label": label.strip(),
        "db_facts": read_db_facts(db_path, project_id),
        "evidence": evidence,
    }


def _cohort(raw: Any, root: Path, name: str) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise KpiInputError(f"{name} must be a list")
    seen: set[int] = set()
    return [_load_entry(item, root, seen) for item in raw]


def _metric(entry: dict[str, Any], key: str) -> dict[str, Any] | None:
    evidence = entry.get("evidence")
    value = evidence.get(key) if evidence else None
    return value if isinstance(value, dict) else None


def _is_complete(value: dict[str, Any] | None) -> bool:
    return bool(value is not None and value.get("coverage_complete") is True)


def _status(summary: dict[str, Any] | None) -> str:
    if summary is None:
        return "NOT_MEASURABLE"
    if summary.get("coverage_complete") is True:
        return "MEASURED"
    return "PARTIAL" if summary.get("has_evidence") else "NOT_MEASURABLE"


def _mt1(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not entries:
        return None
    paid = sum(entry["db_facts"]["paid_usage_events"] or 0 for entry in entries)
    extras, complete, has_evidence, missing = 0, True, False, []
    for entry in entries:
        data = _metric(entry, "mt1")
        count = data.get("system_error_paid_count") if data else None
        if type(count) is not int or count < 0:
            complete = False
            missing.append(entry["project_id"])
            continue
        if entry["db_facts"]["paid_usage_events"] is not None and count > entry["db_facts"]["paid_usage_events"]:
            raise KpiInputError("MT1 evidence exceeds the paid-event count")
        has_evidence = True
        extras += count
        complete = complete and _is_complete(data)
    return {
        "project_ids": [entry["project_id"] for entry in entries],
        "paid_usage_events": paid,
        "system_error_paid_count": extras if has_evidence else None,
        "coverage_complete": complete and not missing,
        "has_evidence": has_evidence,
        "missing_evidence_project_ids": missing,
        "target_met": bool(complete and not missing and extras == 0),
        "reason": None if complete and not missing else
            "thiếu evidence đối chiếu nguyên nhân; paid usage_events tự nó không chứng minh khoản nào là tiền thừa do lỗi",
    }


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def _mt2(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not entries:
        return None
    samples, missing, complete, has_evidence = [], [], True, False
    for entry in entries:
        data = _metric(entry, "mt2")
        rows = data.get("samples") if data else None
        if not isinstance(rows, list):
            complete = False
            missing.append(entry["project_id"])
            continue
        has_evidence = True
        complete = complete and _is_complete(data)
        for row in rows:
            if not isinstance(row, dict) or row.get("kind") not in {"draft", "high"}:
                raise KpiInputError("MT2 sample type is invalid")
            estimate, actual = row.get("estimate_usd"), row.get("actual_usd")
            if not _number(estimate) or not _number(actual) or estimate < 0 or actual <= 0:
                raise KpiInputError("MT2 sample needs finite estimate and positive actual")
            samples.append((row["kind"], abs(float(estimate) - float(actual)) / float(actual) * 100))
    if not samples:
        return {
            "project_ids": [entry["project_id"] for entry in entries], "samples": 0, "by_kind": {},
            "max_abs_error_percent": None, "mean_abs_error_percent": None, "coverage_complete": False,
            "has_evidence": has_evidence, "missing_evidence_project_ids": missing, "target_met": False,
            "reason": "chưa có cặp ước tính trước gen và tiền thực đã đối chiếu cùng mẫu",
        }
    by_kind: dict[str, list[float]] = {}
    for kind, error in samples:
        by_kind.setdefault(kind, []).append(error)
    maximum = max(error for _, error in samples)
    return {
        "project_ids": [entry["project_id"] for entry in entries],
        "samples": len(samples),
        "by_kind": {kind: {
            "samples": len(values),
            "max_abs_error_percent": round(max(values), 3),
            "mean_abs_error_percent": round(sum(values) / len(values), 3),
        } for kind, values in sorted(by_kind.items())},
        "max_abs_error_percent": round(maximum, 3),
        "mean_abs_error_percent": round(sum(error for _, error in samples) / len(samples), 3),
        "coverage_complete": complete and not missing,
        "has_evidence": has_evidence,
        "missing_evidence_project_ids": missing,
        "target_met": bool(complete and not missing and maximum <= 10),
        "reason": None if complete and not missing else "thiếu mẫu hoặc chưa xác nhận độ phủ toàn bộ",
    }


def _records(entries: list[dict[str, Any]], metric: str, field: str) -> dict[str, Any]:
    rows, missing, complete, has_evidence = [], [], True, False
    for entry in entries:
        data = _metric(entry, metric)
        items = data.get(field) if data else None
        if not isinstance(items, list):
            complete = False
            missing.append(entry["project_id"])
            continue
        has_evidence = True
        complete = complete and _is_complete(data)
        rows.extend((entry["project_id"], item) for item in items)
    return {
        "rows": rows, "project_ids": [entry["project_id"] for entry in entries],
        "coverage_complete": complete and not missing, "has_evidence": has_evidence,
        "missing_evidence_project_ids": missing,
    }


def _mt3(baseline: list[dict[str, Any]], current: list[dict[str, Any]]) -> dict[str, Any]:
    required = list(REQUIRED_MT3_BASELINE)
    baseline_ids = sorted(entry["project_id"] for entry in baseline)
    missing_required = sorted(set(required) - set(baseline_ids))
    base_data = _records(baseline, "mt3", "checks")
    current_data = _records(current, "mt3", "checks")

    def summary(data: dict[str, Any]) -> dict[str, Any]:
        checks = []
        for _pid, row in data["rows"]:
            if (not isinstance(row, dict) or type(row.get("free_text_used")) is not bool
                    or type(row.get("unsafe_pass")) is not bool):
                raise KpiInputError("MT3 gate evidence row is invalid")
            checks.append(row)
        leaks = sum(row["free_text_used"] and row["unsafe_pass"] for row in checks)
        return {
            "project_ids": data["project_ids"],
            "gate_checks": len(checks),
            "free_text_gate_leaks": leaks,
            "leak_rate": round(leaks / len(checks), 6) if checks else None,
            "coverage_complete": data["coverage_complete"],
            "has_evidence": data["has_evidence"],
            "missing_evidence_project_ids": data["missing_evidence_project_ids"],
        }

    base, now = summary(base_data), summary(current_data)
    reason = None
    if missing_required:
        base["required_missing_project_ids"] = missing_required
        reason = "MT3 bắt buộc có baseline #24/#27/#31; không thay bằng riêng #31"
    elif not base["gate_checks"] or not base["coverage_complete"] or not now["gate_checks"] or not now["coverage_complete"]:
        reason = "thiếu đủ mẫu replay có nhãn cho baseline hoặc hiện tại"
    elif base["leak_rate"] in (None, 0):
        reason = "baseline không có lỗi lọt cổng để tính phần trăm giảm"
    reduction = round((1 - now["leak_rate"] / base["leak_rate"]) * 100, 3) if reason is None else None
    has_labeled_checks = bool(base["gate_checks"] or now["gate_checks"])
    status = "MEASURED" if reason is None else ("PARTIAL" if has_labeled_checks else "NOT_MEASURABLE")
    return {
        "title": "Lỗi lọt cổng do free-text",
        "target": "giảm tỷ lệ ít nhất 50%",
        "baseline": {**base, "required_project_ids": required, "reason": reason if missing_required or not base["coverage_complete"] else None},
        "current": {**now, "reason": None if now["coverage_complete"] and now["gate_checks"] else "thiếu độ phủ replay hiện tại"},
        "reduction_percent": reduction,
        "target_met": bool(reduction is not None and reduction >= 50),
        "status": status,
        "reason": reason,
    }


def _mt4(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    data = _records(entries, "mt4", "scenes")
    if not entries:
        return None
    maps, checks, complete = [], [], data["coverage_complete"]
    multi_shot_count = 0
    for _pid, row in data["rows"]:
        if not isinstance(row, dict) or type(row.get("multi_shot")) is not bool:
            raise KpiInputError("MT4 scene evidence row is invalid")
        if not row["multi_shot"]:
            continue
        multi_shot_count += 1
        if type(row.get("shared_map")) is bool:
            maps.append(row["shared_map"])
        else:
            complete = False
        position_checks = row.get("position_checks")
        if not isinstance(position_checks, list) or not position_checks:
            complete = False
        else:
            if any(
                not isinstance(item, dict) or type(item.get("consistent")) is not bool for item in position_checks
            ):
                raise KpiInputError("MT4 position evidence row is invalid")
            checks.extend(item["consistent"] for item in position_checks)
    mismatches = sum(not item for item in checks)
    complete = complete and multi_shot_count > 0 and len(maps) == multi_shot_count and bool(checks)
    return {
        "project_ids": data["project_ids"],
        "multi_shot_scenes": multi_shot_count,
        "shared_map_scenes": sum(maps),
        "shared_map_coverage": round(sum(maps) / multi_shot_count, 6) if multi_shot_count else None,
        "position_checks": len(checks),
        "position_mismatches": mismatches if checks else None,
        "position_consistency": round((len(checks) - mismatches) / len(checks), 6) if checks else None,
        "coverage_complete": complete, "has_evidence": data["has_evidence"],
        "missing_evidence_project_ids": data["missing_evidence_project_ids"],
        "target_met": bool(complete and all(maps) and mismatches == 0),
        "reason": None if complete else "cần đủ cảnh nhiều shot, map chung và kiểm tra vị trí có bằng chứng độc lập",
    }


def _mt5(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not entries:
        return None
    data = _records(entries, "mt5", "clips")
    bad, good = [], []
    by_kind: dict[str, dict[str, list[bool]]] = {
        "freeze": {"bad": [], "good": []},
        "wrong_first_frame": {"bad": [], "good": []},
    }
    for _pid, row in data["rows"]:
        if (not isinstance(row, dict) or row.get("kind") not in {"freeze", "wrong_first_frame"}
                or type(row.get("bad")) is not bool or type(row.get("detected_before_user")) is not bool):
            raise KpiInputError("MT5 clip evidence row is invalid")
        group = "bad" if row["bad"] else "good"
        (bad if row["bad"] else good).append(row["detected_before_user"])
        by_kind[row["kind"]][group].append(row["detected_before_user"])
    recall = sum(bad) / len(bad) if bad else None
    false_positive = sum(good) / len(good) if good else None
    complete = data["coverage_complete"] and bool(bad) and bool(good) and all(
        by_kind[kind]["bad"] and by_kind[kind]["good"] for kind in by_kind
    )
    per_kind = {}
    for kind, labels in by_kind.items():
        kind_bad, kind_good = labels["bad"], labels["good"]
        per_kind[kind] = {
            "bad_clips": len(kind_bad),
            "bad_detected_before_user": sum(kind_bad),
            "recall": round(sum(kind_bad) / len(kind_bad), 6) if kind_bad else None,
            "good_clips": len(kind_good),
            "good_flagged": sum(kind_good),
            "false_positive_rate": round(sum(kind_good) / len(kind_good), 6) if kind_good else None,
        }
    return {
        "project_ids": data["project_ids"], "bad_clips": len(bad), "bad_detected_before_user": sum(bad),
        "freeze_or_first_frame_recall": round(recall, 6) if recall is not None else None,
        "by_kind": per_kind,
        "freeze_recall": per_kind["freeze"]["recall"],
        "wrong_first_frame_recall": per_kind["wrong_first_frame"]["recall"],
        "good_clips": len(good), "good_flagged": sum(good),
        "false_positive_rate": round(false_positive, 6) if false_positive is not None else None,
        "coverage_complete": complete, "has_evidence": data["has_evidence"],
        "missing_evidence_project_ids": data["missing_evidence_project_ids"],
        "reason": None if complete else "cần nhãn độc lập về clip lỗi/đạt và kết quả QC trước khi người dùng thấy",
    }


def _with_status(value: dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {"status": "NOT_MEASURABLE", "reason": "không có cohort"}
    result = dict(value)
    result["status"] = _status(value)
    return result


def measure_bundle(bundle_dir: str | Path) -> dict[str, Any]:
    """Measure only files declared below an explicit isolated-copy directory."""
    _reject_reparse_ancestors(Path(bundle_dir))
    try:
        root = Path(bundle_dir).resolve(strict=True)
    except OSError:
        raise KpiInputError("isolated-copy bundle directory is missing") from None
    if not root.is_dir() or _is_live_data_path(root):
        raise KpiInputError("isolated-copy bundle must be a real directory")
    manifest_path = root / MANIFEST_NAME
    if _is_reparse(manifest_path):
        raise KpiInputError("manifest cannot be a symlink or junction")
    manifest = _json_object(manifest_path, "copy manifest")
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("snapshot_kind") != "isolated_copy":
        raise KpiInputError("manifest must declare schema_version=1 and snapshot_kind=isolated_copy")
    baseline = _cohort(manifest.get("baseline"), root, "baseline")
    current = _cohort(manifest.get("current"), root, "current")
    mt3_baseline = _cohort(manifest.get("mt3_baseline", []), root, "mt3_baseline")
    if not baseline or not current:
        raise KpiInputError("baseline and current cohorts must both be non-empty")

    mt1_base, mt1_now = _with_status(_mt1(baseline)), _with_status(_mt1(current))
    mt2_base, mt2_now = _with_status(_mt2(baseline)), _with_status(_mt2(current))
    mt3 = _mt3(mt3_baseline, current)
    mt4_base, mt4_now = _with_status(_mt4(baseline)), _with_status(_mt4(current))
    mt5_base, mt5_now = _with_status(_mt5(baseline)), _with_status(_mt5(current))
    metrics = {
        "MT1": {"title": "Không trả tiền thừa do lỗi hệ thống", "target": "0 lượt trả thừa có bằng chứng",
                "baseline": mt1_base, "current": mt1_now, "status": mt1_now["status"], "reason": mt1_now.get("reason")},
        "MT2": {"title": "Sai lệch ước tính giá trước gen", "target": "mọi mẫu sai lệch tuyệt đối <= 10%",
                "baseline": mt2_base, "current": mt2_now, "status": mt2_now["status"], "reason": mt2_now.get("reason")},
        "MT3": mt3,
        "MT4": {"title": "Vị trí liên tục từ một sơ đồ mặt bằng", "target": "bao phủ map chung 100%, 0 mismatch có nhãn",
                "baseline": mt4_base, "current": mt4_now, "status": mt4_now["status"], "reason": mt4_now.get("reason")},
        "MT5": {"title": "QC bắt clip đơ / sai khung đầu trước người dùng", "target": "báo recall và false-positive; V3 không đặt ngưỡng số",
                "baseline": mt5_base, "current": mt5_now, "status": mt5_now["status"], "reason": mt5_now.get("reason")},
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_kind": "isolated_copy",
        "baseline_project_ids": [item["project_id"] for item in baseline],
        "current_project_ids": [item["project_id"] for item in current],
        "metrics": metrics,
        "method": {
            "MT1": "Chỉ tính lượt trả thừa khi có nguyên nhân đã đối chiếu; số paid usage_events không chứng minh lãng phí.",
            "MT2": "Sai lệch mẫu = abs(ước tính trước gen - tiền thực) / tiền thực; báo max và trung bình để mẫu không bù trừ nhau.",
            "MT3": "Free-text gate leak = free_text_used AND unsafe_pass; so tỷ lệ trên tổng gate checks của #24/#27/#31 với #33.",
            "MT4": "Báo độ phủ map chung trong cảnh nhiều shot và nhất quán vị trí trên các kiểm tra có nhãn.",
            "MT5": "Báo recall trên clip lỗi và false-positive trên clip đạt có nhãn độc lập.",
        },
    }


def _show(value: Any) -> str:
    if value is None:
        return "chưa đo"
    if isinstance(value, bool):
        return "đạt" if value else "chưa đạt"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    if isinstance(value, dict):
        return "; ".join(f"{key}: {_show(item)}" for key, item in value.items())
    return str(value)


def render_markdown(result: dict[str, Any]) -> str:
    rows = []
    for key in ("MT1", "MT2", "MT3", "MT4", "MT5"):
        metric = result["metrics"][key]
        baseline, current = metric.get("baseline"), metric.get("current")
        if key == "MT3":
            before = _show(baseline.get("leak_rate") if baseline else None)
            after = _show(current.get("leak_rate") if current else None)
            detail = f"lỗi lọt cổng: {_show(baseline.get('free_text_gate_leaks') if baseline else None)} → {_show(current.get('free_text_gate_leaks') if current else None)}; giảm {_show(metric.get('reduction_percent'))}%"
        else:
            before = _show(baseline.get("target_met") if baseline else None)
            after = _show(current.get("target_met") if current else None)
            detail = metric.get("reason") or "có số đo; xem JSON kết quả để biết độ phủ"
        rows.append(f"| {key} | {before} | {after} | {metric.get('status')} | {detail} |")
    return "\n".join((
        "# Đo 5 mục tiêu gốc V3 §2",
        "",
        f"Baseline: {', '.join(map(str, result['baseline_project_ids']))}; hiện tại: {', '.join(map(str, result['current_project_ids']))}.",
        "Chỉ đọc bản sao khai trong manifest isolated_copy; không có đường dẫn mặc định tới dữ liệu production.",
        "",
        "| KPI | Baseline | Hiện tại | Trạng thái | Lý do / ghi chú |",
        "|---|---|---|---|---|",
        *rows,
        "",
        "MT3 dùng tỷ lệ lỗi lọt cổng do free-text trên tổng gate checks; baseline bắt buộc #24/#27/#31, hiện tại #33.",
        "Thiếu bằng chứng hoặc nhãn độc lập thì trả NOT_MEASURABLE/PARTIAL, không suy ra đạt từ trạng thái cờ.",
        "SQLite mở mode=ro và query-only; không API, mạng hay subprocess.",
        "",
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True),
        "",
    ))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="py tools/kpi_goc.py",
        description="Đo KPI V3 từ bundle bản sao được chỉ định; không có đường dẫn dữ liệu mặc định.",
    )
    parser.add_argument("--ban-sao", type=Path, help="thư mục isolated copy có kpi_goc_manifest.json")
    parser.add_argument("--out", type=Path, help="tệp Markdown; phải nằm ngoài bundle")
    args = parser.parse_args(argv)
    if args.ban_sao is None:
        print("Cần --ban-sao <thư-mục-bản-sao>; không tự tìm dữ liệu production.", file=sys.stderr)
        return 2
    try:
        result = measure_bundle(args.ban_sao)
        report = render_markdown(result)
        if args.out:
            bundle = Path(args.ban_sao).resolve(strict=True)
            output = args.out.resolve()
            if output.is_relative_to(bundle):
                raise KpiInputError("report output must be outside the input bundle")
            if not output.parent.is_dir() or _is_reparse(output.parent):
                raise KpiInputError("report parent directory must already exist")
            output.write_text(report, encoding="utf-8")
        print(report, end="")
        return 0
    except KpiInputError as exc:
        print(f"Không thể đo an toàn: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
