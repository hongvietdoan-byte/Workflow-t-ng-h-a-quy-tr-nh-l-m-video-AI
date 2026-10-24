"""Kiểm sự hiện diện bằng chứng trên snapshot độc lập, không nghiệm thu thay người.

Không nạp runtime pipeline, môi trường, nhà cung cấp hay bảng giá. usage_events là
sổ lượt sử dụng theo contract core.cost; công cụ không tự quy đổi thành tiền.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sqlite3

try:
    from tools.kpi_goc import open_db_readonly, _reject_reparse_ancestors
except ModuleNotFoundError:  # chạy trực tiếp py tools/kiem_cong.py
    from kpi_goc import open_db_readonly, _reject_reparse_ancestors

PASS = "ĐẠT"
FAIL = "CHƯA ĐẠT"
MISSING = "THIẾU DỮ LIỆU"
EVIDENCE = ("jobs", "sent_package", "diag_events", "ui_step", "ledger", "qc", "overrides")
DEFAULT_CATALOG = Path(__file__).resolve().parents[1] / "docs/kiem_cong_catalog.json"
TABLES = {"jobs", "scenes", "diag_events", "usage_events", "qc_results", "qc_runs", "qc_findings", "overrides"}


def _time(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp_requires_timezone")
    return value.astimezone(timezone.utc)


def _json(raw):
    def reject(_):
        raise ValueError("invalid_json")
    value = json.loads(raw, parse_constant=reject)
    if not isinstance(value, dict):
        raise ValueError("invalid_json")
    def finite(v):
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError("invalid_json")
        if isinstance(v, dict):
            for item in v.values():
                finite(item)
        elif isinstance(v, list):
            for item in v:
                finite(item)
    finite(value)
    return value


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _cols(conn, table):
    if table not in TABLES:
        return set()
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def _records(conn, table, project):
    """Chỉ đọc bảng trong allowlist; không suy đoán quyền sở hữu từ nội dung JSON."""
    cols = _cols(conn, table)
    if not cols:
        return None, "missing_table"
    if "project_id" in cols:
        rows = conn.execute(f"SELECT * FROM {table} WHERE project_id=?", (project,))
    elif "job_id" in cols and {"id", "project_id"} <= _cols(conn, "jobs"):
        rows = conn.execute(f"SELECT e.* FROM {table} e JOIN jobs j ON j.id=e.job_id WHERE j.project_id=?", (project,))
    elif table == "qc_findings" and "qc_run_id" in cols and {"qc_run_id", "project_id"} <= _cols(conn, "qc_runs"):
        rows = conn.execute("SELECT e.* FROM qc_findings e JOIN qc_runs q ON q.qc_run_id=e.qc_run_id WHERE q.project_id=?", (project,))
    else:
        return None, "missing_scope"
    names = [d[0] for d in rows.description]
    records = [dict(zip(names, row)) for row in rows]
    # Cột project_id không được che một khóa ngoại thuộc dự án khác.
    for record in records:
        for fk, parent, ident in (("job_id", "jobs", "id"), ("scene_id", "scenes", "id"), ("qc_run_id", "qc_runs", "qc_run_id")):
            if table == parent or record.get(fk) is None:
                continue
            if not {ident, "project_id"} <= _cols(conn, parent):
                record["_scope_missing"] = True
                continue
            owners = conn.execute(f"SELECT project_id FROM {parent} WHERE {ident}=?", (record[fk],)).fetchall()
            if len(owners) != 1 or owners[0][0] != project:
                record["_scope_error"] = True
    return records, None


def _fact(records, validator, times, since, now, missing=None):
    reasons = set()
    valid = invalid = count = unavailable = 0
    if records is None:
        return {"status": MISSING, "count": 0, "valid": 0, "invalid": 0, "reasons": [missing or "missing_schema"]}
    for row in records:
        if row.get("_scope_error"):
            count += 1; invalid += 1; reasons.add("invalid_scope"); continue
        if row.get("_scope_missing"):
            count += 1; unavailable += 1; reasons.add("missing_scope"); continue
        raw = next((row[k] for k in times if row.get(k) not in (None, "")), None)
        if raw is not None:
            try:
                at = _time(raw)
            except (TypeError, ValueError, OverflowError):
                count += 1; invalid += 1; reasons.add("invalid_timestamp"); continue
            if at > now:
                count += 1; invalid += 1; reasons.add("future_timestamp"); continue
            if since is not None and at < since:
                continue
        elif since is not None:
            count += 1; unavailable += 1; reasons.add("missing_timestamp"); continue
        count += 1
        try:
            error = validator(row)
        except (TypeError, ValueError, KeyError, json.JSONDecodeError, OverflowError):
            error = "invalid_schema"
        if error:
            if error == "missing_resolution_audit":
                unavailable += 1
            else:
                invalid += 1
            reasons.add(error)
        else:
            valid += 1
    if not count:
        reasons.add("no_evidence")
    status = FAIL if invalid else MISSING if unavailable or not valid else PASS
    return {"status": status, "count": count, "valid": valid, "invalid": invalid, "reasons": sorted(reasons)}


def _job(r):
    if not {"id", "type", "state", "created_at"} <= r.keys():
        return "missing_schema"
    if not r.get("created_at"):
        return "invalid_timestamp"
    if r["state"] in ("failed", "error", "rejected", "cancelled"):
        return "job_failed"
    if r["type"] not in ("image_gen", "video_gen", "render", "music"):
        return "invalid_job_type"
    # Contract core/states.py: JobState; không import core runtime.
    return None if r["state"] in ("queued", "running", "retryable", "succeeded", "approved", "pending_review") else "invalid_job_state"


def _package(r):
    p = _json(r.get("sent_package"))
    if type(p.get("v")) is not int or p["v"] not in (1, 2):
        return "invalid_schema"
    if not isinstance(p.get("prompt"), str) or not isinstance(p.get("refs"), list) or not isinstance(p.get("params"), dict):
        return "invalid_schema"
    if not all(isinstance(ref, dict) and all(isinstance(ref.get(k), str) and ref[k] for k in ("param", "role", "path", "file"))
               and isinstance(ref.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", ref["sha256"]) for ref in p["refs"]):
        return "invalid_reference"
    if not all(isinstance(p.get(k), str) and p[k] for k in ("provider", "model")):
        return "invalid_schema"
    _time(p.get("at"))
    return None


def _diag(r):
    _time(r.get("last_at") or r.get("at"))
    if not {"stage", "severity", "code"} <= r.keys() or not r["stage"] or not r["code"]:
        return "invalid_schema"
    if r["severity"] in ("error", "critical", "fatal"):
        return "diagnostic_error"
    return None if r["severity"] in ("info", "warning", "warn", "debug") else "invalid_schema"


def _ledger(r):
    _time(r.get("at"))
    return None if r.get("kind") in ("image", "video", "audio", "llm") and _number(r.get("quantity")) and r["quantity"] >= 0 else "invalid_ledger"


def _qc(r):
    if not all(_number(r.get(k)) for k in ("score", "threshold_at_time")):
        return "invalid_qc"
    if r["score"] < r["threshold_at_time"] or r.get("auto_decision") in ("reject", "fail"):
        return "qc_failed"
    return None if r.get("criterion") and r.get("auto_decision") == "approve" else "invalid_qc"


def _override(r):
    p = r["_override"]
    _time(p.get("updated_at"))
    if type(p.get("schema_version")) is not int or p["schema_version"] != 1:
        return "invalid_schema"
    if p.get("project_id") != r["project_id"] or p.get("scene_id") != r.get("scene_id", r.get("id")):
        return "invalid_scope"
    if not all(type(p.get(k)) is int and p[k] > 0 for k in ("revision",)):
        return "invalid_schema"
    if not all(isinstance(p.get(k), str) and re.fullmatch(r"[0-9a-f]{64}", p[k]) for k in ("base_scene_revision", "base_package_hash")):
        return "invalid_schema"
    if not isinstance(p.get("edits"), list) or not all(isinstance(e, dict) and e.get("op") in ("add", "exclude", "pin") and e.get("role") for e in p["edits"]):
        return "invalid_schema"
    return None if p.get("reason") and p.get("updated_by") and p.get("updated_at") else "invalid_schema"


def _qc_run(r):
    _time(r.get("finished_at"))
    if r.get("status") in ("failed", "partial"):
        return "qc_failed"
    if r.get("status") != "ok" or r.get("error"):
        return "invalid_qc"
    return None


def _finding(r):
    _time(r.get("created_at"))
    if r.get("severity") not in ("BLOCK", "REVIEW", "INFO") or r.get("status") not in ("open", "overridden", "resolved", "false_positive") or not r.get("qc_code"):
        return "invalid_qc"
    if r["status"] == "open" and r["severity"] in ("BLOCK", "REVIEW"):
        return "qc_failed"
    # Contract hiện có chỉ lưu status/created_at, không có dấu người/lúc xử lý.
    if r["status"] != "open":
        return "missing_resolution_audit"
    return None


def _merge_facts(facts):
    return {"status": FAIL if any(f["status"] == FAIL for f in facts) else MISSING if any(f["status"] == MISSING for f in facts) else PASS,
            **{k: sum(f[k] for f in facts) for k in ("count", "valid", "invalid")},
            "reasons": sorted({r for f in facts for r in f["reasons"]})}


def collect_evidence(conn, project_id, since=None, now=None):
    if type(project_id) is not int or project_id <= 0:
        raise ValueError("invalid_project")
    since = _time(since) if since is not None else None
    now = _time(now) if now is not None else datetime.now(timezone.utc)
    if since and since > now:
        raise ValueError("future_since")
    facts = {}
    for name, table, validator, times in (
        ("jobs", "jobs", _job, ("created_at",)),
        ("diag_events", "diag_events", _diag, ("last_at", "at")),
        ("ui_step", "diag_events", _diag, ("last_at", "at")),
        ("ledger", "usage_events", _ledger, ("at",)),
        ("qc", "qc_results", _qc, ("created_at", "at", "decided_at")),
    ):
        records, missing = _records(conn, table, project_id)
        if name == "ui_step" and records is not None:
            records = [r for r in records if r.get("stage") == "ui_step"]
        facts[name] = _fact(records, validator, times, since, now, missing)
    jobs, missing = _records(conn, "jobs", project_id)
    packages = None if jobs is None else []
    for job in jobs or []:
        try:
            p = _json(job.get("sent_package"))
            packages.append({**job, "_at": p.get("at")})
        except (TypeError, ValueError):
            packages.append({"sent_package": None, "_at": None, "_scope_error": job.get("_scope_error"), "_scope_missing": job.get("_scope_missing")})
    facts["sent_package"] = _fact(packages, _package, ("_at",), since, now, missing)
    # Hai thế hệ QC có contract khác nhau; không lấy timestamp job làm QC time.
    qc_sources = [facts["qc"]] if _cols(conn, "qc_results") else []
    for table, validator, times in (("qc_runs", _qc_run, ("finished_at",)), ("qc_findings", _finding, ("created_at",))):
        if _cols(conn, table):
            records, missing_qc = _records(conn, table, project_id)
            # Không có finding là bình thường; run vẫn phải có bằng chứng hoàn tất.
            if records or table == "qc_runs" or records is None:
                qc_sources.append(_fact(records, validator, times, since, now, missing_qc))
    if qc_sources:
        facts["qc"] = _merge_facts(qc_sources)
    scenes, missing = _records(conn, "scenes", project_id)
    overrides = None if scenes is None else []
    for scene in scenes or []:
        try:
            data = _json(scene.get("data"))
            if "package_overrides" not in data:
                continue
            p = data["package_overrides"]
            if not isinstance(p, dict):
                raise ValueError("invalid_schema")
            overrides.append({**scene, "_override": p, "_at": p.get("updated_at")})
        except (TypeError, ValueError):
            overrides.append({"_override": {}, "_scope_error": scene.get("_scope_error"), "_scope_missing": scene.get("_scope_missing")})
    facts["overrides"] = _fact(overrides, _override, ("_at",), since, now, missing)
    if _cols(conn, "overrides"):
        records, missing_override = _records(conn, "overrides", project_id)
        parsed = None if records is None else []
        for row in records or []:
            try:
                p = _json(row.get("data") or row.get("package_overrides"))
                parsed.append({**row, "_override": p, "_at": p.get("updated_at")})
            except (ValueError, TypeError):
                parsed.append({"_override": {}, "_scope_error": row.get("_scope_error"),
                               "_scope_missing": row.get("_scope_missing")})
        extra = _fact(parsed, _override, ("_at",), since, now, missing_override)
        facts["overrides"] = _merge_facts([facts["overrides"], extra]) if overrides else extra
    return {k: facts[k] for k in EVIDENCE}


def evaluate_catalog(rows, facts):
    result = []
    for row in rows:
        keys = row.get("evidence", [])
        states = [facts.get(k, {}).get("status", MISSING) for k in keys]
        checks = FAIL if FAIL in states else PASS if states and all(s == PASS for s in states) else MISSING
        status = checks
        reasons = set()
        for key in keys:
            fact = facts.get(key, {})
            if fact.get("status") != PASS:
                reasons.add("evidence_failed" if fact.get("status") == FAIL else "evidence_missing")
        if not keys:
            reasons.add("evidence_missing")
        if row.get("manual", True) is not False:
            reasons.add("manual_acceptance_required")
        if row.get("one_project") is not True:
            reasons.add("not_one_project")
        if checks == PASS and (row.get("manual", True) is not False or row.get("one_project") is not True):
            status = MISSING
        result.append({"id": row["id"], "status": status, "checks": checks, "reasons": sorted(reasons)})
    return result


def run_report(db, project_id, catalog_path=DEFAULT_CATALOG, since=None, now=None):
    catalog = _json(Path(catalog_path).read_text(encoding="utf-8-sig"))
    rows = catalog.get("rows")
    if not isinstance(rows, list) or not rows or not all(isinstance(r, dict) and isinstance(r.get("id"), str) and re.fullmatch(r"[A-Za-z0-9_.-]+", r["id"]) and isinstance(r.get("evidence"), list) and all(k in EVIDENCE for k in r["evidence"]) for r in rows):
        raise ValueError("invalid_catalog")
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("invalid_catalog")
    conn = open_db_readonly(db)
    try:
        conn.execute("BEGIN")  # cùng một snapshot cho mọi nguồn bằng chứng
        facts = collect_evidence(conn, project_id, since, now)
    finally:
        conn.close()
    return {"project": project_id, "since": _time(since).isoformat() if since else None,
            "evidence": facts, "rows": evaluate_catalog(rows, facts)}


def render_markdown(report):
    lines = [f"# Kiểm cổng dự án {report['project']}", "", "Chỉ kiểm cấu trúc và sự hiện diện; cổng cần nghiệm thu tay/EP/benchmark vẫn THIẾU DỮ LIỆU.", "", "| Nguồn | Trạng thái | Số | Hợp lệ | Lỗi | Mã lý do |", "|---|---|---:|---:|---:|---|"]
    for key, f in report["evidence"].items():
        lines.append(f"| {key} | {f['status']} | {f['count']} | {f['valid']} | {f['invalid']} | {', '.join(f['reasons'])} |")
    lines += ["", "| Việc | Cổng | Kiểm bằng chứng | Mã lý do |", "|---|---|---|---|"]
    lines += [f"| {r['id']} | {r['status']} | {r['checks']} | {', '.join(r['reasons'])} |" for r in report["rows"]]
    return "\n".join(lines) + "\n"


def _output(raw, db, catalog):
    path = Path(raw)
    _reject_reparse_ancestors(path)
    target = path.resolve()
    if any(p.name.casefold() == "data" for p in (target, *target.parents)):
        raise ValueError("unsafe_output")
    if target in (Path(db).resolve(), Path(catalog).resolve()) or target.suffix.lower() != ".md":
        raise ValueError("unsafe_output")
    if target.exists():
        raise ValueError("output_exists")
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Snapshot ngoài data/, bắt buộc chỉ định")
    parser.add_argument("--project", required=True, type=int)
    parser.add_argument("--since")
    parser.add_argument("--md")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    args = parser.parse_args(argv)
    try:
        output = _output(args.md, args.db, args.catalog) if args.md else None
        report = run_report(args.db, args.project, args.catalog, args.since)
        markdown = render_markdown(report)
        if output:
            with output.open("x", encoding="utf-8") as stream:
                stream.write(markdown)
        else:
            print(markdown)
        return 0
    except (OSError, ValueError, sqlite3.Error):
        print("Không đọc được snapshot/catalog hoặc đường dẫn kết quả không an toàn.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
