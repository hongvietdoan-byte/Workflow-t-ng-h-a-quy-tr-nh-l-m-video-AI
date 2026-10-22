"""Đề xuất sổ lỗi WS0 từ bản sao SQLite; chỉ đọc, không gọi provider.

Không xuất message/note/payload tự do: bằng chứng là bảng + id bản ghi.
Chi phí chưa có đơn vị USD thật được giữ UNKNOWN, không đoán theo bảng giá.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.states import JobState, TRANSITIONS

STAGES = {"director": "L3", "previz": "L6", "image": "L9", "image_gen": "L9",
          "motion": "L11", "video": "L13", "video_gen": "L13"}


def _code(value, fallback):
    # Chỉ nhận mã máy ngắn, không lấy nguyên câu báo lỗi có thể chứa thông tin riêng.
    value = str(value or "").split(":", 1)[0].strip()
    return value if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", value) else fallback


def _sources(project, code):
    found = []
    for path in sorted((ROOT / "docs").glob("DANH_GIA_*.md")):
        if not re.search(rf"(?:P|DU_AN_){project}(?:_|\b)", path.stem, re.I):
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = re.match(r"\|\s*([GAB]\d+)\s*\|", line)
            if match and (f"`{code}`" in line or (code == "duplicate_succeeded" and "succeeded 2 lần" in line)):
                found.append({"id": f"P{project}-{match[1]}", "alias": match[1],
                              "source_document": path.relative_to(ROOT).as_posix(), "line": number})
    return found


def build_report(db_path, project):
    warnings, groups = [], {}
    with sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")  # Một snapshot cho toàn bộ bảng, kể cả khi DB đang được ghi.
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = sorted({"jobs", "diag_events", "job_events"} - tables)
        if missing:
            raise ValueError("Thiếu bảng bắt buộc: " + ", ".join(missing))
        required = {"jobs": {"id", "project_id", "state"}, "diag_events": {"id", "project_id", "code", "at"},
                    "job_events": {"id", "job_id", "from_state", "to_state", "at"}}
        for table, columns in required.items():
            absent = columns - {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
            if absent:
                raise ValueError(f"Thiếu cột {table}: " + ", ".join(sorted(absent)))
        jobs = {r["id"]: dict(r) for r in db.execute("SELECT * FROM jobs WHERE project_id=?", (project,))}
        events = [dict(r) for r in db.execute("SELECT e.* FROM job_events e JOIN jobs j ON j.id=e.job_id WHERE j.project_id=? ORDER BY e.id", (project,))]
        costs = {}
        if "usage_events" in tables:
            cols = {r[1] for r in db.execute("PRAGMA table_info(usage_events)")}
            if "job_id" not in cols:
                warnings.append("usage_events thiếu job_id: chi phí UNKNOWN")
            else:
                for row in db.execute("SELECT u.* FROM usage_events u JOIN jobs j ON j.id=u.job_id WHERE j.project_id=?", (project,)):
                    r = dict(row)
                    value = r.get("cost_usd")
                    if value is None and str(r.get("unit", "")).lower() == "usd":
                        value = r.get("quantity")
                    costs.setdefault(r["job_id"], []).append(value)
                if "cost_usd" not in cols:
                    warnings.append("usage_events không có cost_usd: chỉ cộng dòng unit=USD; còn lại UNKNOWN")
        else:
            warnings.append("Thiếu bảng tùy chọn usage_events: chi phí UNKNOWN")

        def add(key, code, category, source, record, job_id=None, stage=None, count=1, first=None, last=None):
            if key not in groups:
                suggestions = _sources(project, code)
                groups[key] = dict(id=f"P{project}-PROPOSAL-{hashlib.sha256(key.encode()).hexdigest()[:12]}",
                    alias=[], root_cause_id=None, title=code, source_document=[], project_ids=[project], shot_ids=[], scene_ids=[], job_ids=[],
                    stage=STAGES.get(stage), category=category, root_cause_hypothesis=None, root_cause_confirmed=None,
                    evidence=[], severity="REVIEW", status="OPEN", first_seen=first, last_seen=last,
                    affected_flows=[], owner=None, fix_commit=None, tests=[], real_run_evidence=[], plan_workstream="WS0",
                    dependencies=[], reopen_history=[], group_key=key, count=0, suggested_error_codes=suggestions,
                    failed_job_cost_usd=None)
            item = groups[key]
            item["count"] += count
            item["first_seen"] = min(filter(None, (item["first_seen"], first)), default=None)
            item["last_seen"] = max(filter(None, (item["last_seen"], last)), default=None)
            item["evidence"].append({"table": source, "record_id": record})
            if job_id in jobs:
                item["job_ids"] = sorted(set(item["job_ids"]) | {job_id})
                # CSDL hiện tại: mỗi scenes.id chính là một shot; không nhầm với scenes.idx.
                scene = jobs[job_id].get("scene_id")
                if scene is not None:
                    item["scene_ids"] = sorted(set(item["scene_ids"]) | {scene})
                shot = jobs[job_id].get("shot_id", scene)
                if shot is not None:
                    item["shot_ids"] = sorted(set(item["shot_ids"]) | {shot})

        for row in db.execute("SELECT * FROM diag_events WHERE project_id=? ORDER BY id", (project,)):
            r = dict(row)
            if r.get("severity") == "info" or r.get("stage") in ("ui_step", "cli_step"):   # bước bấm / lệnh CLI: quan sát, không phải lỗi
                continue
            code = _code(r["code"], "unknown_diag")
            add("diag:" + code, code, "diagnostic", "diag_events", r["id"], r.get("job_id"), r.get("stage"),
                max(1, r.get("count") or 1), r["at"], r.get("last_at") or r["at"])
        failed_events = {}
        succeeded = set()
        for r in events:
            if r["to_state"] == "failed":
                failed_events.setdefault(r["job_id"], []).append(r)
            duplicate = r["to_state"] == "succeeded" and r["job_id"] in succeeded
            if r["to_state"] == "succeeded":
                succeeded.add(r["job_id"])
            try:
                invalid = JobState(r["to_state"]) not in TRANSITIONS[JobState(r["from_state"])]
            except ValueError:
                invalid = r["from_state"] is not None  # Sự kiện khởi tạo chưa có trạng thái trước.
            invalid = invalid or "InvalidTransition" in str(r.get("note") or "") or duplicate
            if invalid:
                transition = _code(r["from_state"], "unknown") + "->" + _code(r["to_state"], "unknown")
                code = "duplicate_succeeded" if duplicate or transition == "succeeded->succeeded" else "InvalidTransition"
                add("transition:" + transition, code, "transition", "job_events", r["id"], r["job_id"], first=r["at"], last=r["at"])
        for job_id, job in jobs.items():
            attempts = failed_events.get(job_id, [])
            if not attempts and job["state"] == "failed":
                attempts = [None]  # Trạng thái lỗi cũ không có lịch sử: một bằng chứng jobs.
            for event in attempts:
                code = _code((event or {}).get("note") or job.get("error"), "failed")
                at = (event or {}).get("at") or job.get("updated_at") or job.get("created_at")
                add("job:" + code, code, "job_failure", "job_events" if event else "jobs",
                    event["id"] if event else job_id, job_id, job.get("type"), first=at, last=at)
        for item in groups.values():
            values = [v for j in item["job_ids"] if jobs[j]["state"] == "failed" or j in failed_events for v in costs.get(j, [None])]
            if values and all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in values):
                total = sum(values)
                if math.isfinite(total):
                    item["failed_job_cost_usd"] = round(total, 8)
    return {"schema_version": 1, "project_id": project, "proposal_only": True, "warnings": warnings,
            "errors": [groups[k] for k in sorted(groups)]}


def render_markdown(report):
    lines = [f"# Đề xuất sổ lỗi dự án {report['project_id']}", "", "Chỉ đề xuất OPEN; chưa xác nhận nguyên nhân/chạy thật. Chi phí giữa các nhóm có thể trùng job, không cộng dồn.", ""]
    lines += ["Cảnh báo: " + w for w in report["warnings"]]
    lines += ["", "| Nhóm | Số lần | Đầu / cuối | Job | Shot | USD job hỏng | Gợi ý có nguồn |", "|---|---:|---|---|---|---:|---|"]
    for r in report["errors"]:
        cost = r["failed_job_cost_usd"]
        suggestions = "; ".join(f"{s['id']} ({s['source_document']}:{s['line']})" for s in r["suggested_error_codes"])
        lines.append(f"| {r['group_key']} | {r['count']} | {r['first_seen']} / {r['last_seen']} | {r['job_ids']} | {r['shot_ids']} | {cost if cost is not None else 'UNKNOWN'} | {suggestions} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True, help="Bản sao SQLite chỉ đọc")
    parser.add_argument("--project", type=int, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = build_report(args.db, args.project)
    except (sqlite3.Error, ValueError) as exc:
        print(f"Không thể lập báo cáo: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) if args.json else render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
