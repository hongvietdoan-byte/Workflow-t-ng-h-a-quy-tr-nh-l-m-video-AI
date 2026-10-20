"""Đối soát ClipAI chỉ đọc; mọi số tiền không biết giữ là None."""
import argparse
import json
import math
import re
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def number(value):
    # Trần 1e15 cho mỗi lượng/tiền: dữ liệu ngoại lai không làm tràn tính toán/tổng 5000 task.
    try:
        return value if type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1e15 else None
    except OverflowError:
        return None


MAX_ROWS = 5000
MAX_FILE_BYTES = 16 * 1024 * 1024


def read_json(path):
    # Đọc có trần ngay trên stream, kể cả file tăng kích thước sau khi mở.
    with Path(path).open("rb") as source:
        data = source.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("input_too_large")
    return json.loads(data)


def validate_pricing(pricing):
    if not isinstance(pricing, dict) or pricing.get("_error"):
        raise ValueError("invalid_pricing")
    for key in ("per_video_second", "per_video_clip"):
        values = pricing.get(key)
        if not isinstance(values, dict) or any(number(v) is None for v in values.values()):
            raise ValueError("invalid_pricing")


def difference_percent(expected, actual):
    if expected is None or actual is None or actual <= 0:
        return None
    value = (expected / actual - 1) * 100
    return round(value, 3) if math.isfinite(value) else None


def identifier(value):
    return value if type(value) is int and value > 0 else None


def label(value):
    # Chỉ mã kỹ thuật, không chuyển prompt / lỗi nhà cung cấp ra báo cáo.
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", value) else None


def mapping(value, warnings, field):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            warnings.append("bad_type:" + field)
            value = None
    if value is None:
        return {}
    if not isinstance(value, dict):
        warnings.append("bad_type:" + field)
        return {}
    return value


def task_id(value):
    value = label(value)
    if value and value.startswith("seedance:"):
        value = value.partition(":")[2]
    return value if value and ":" not in value else None


def open_readonly(path):
    """Chỉ file tồn tại, URI tự dựng tránh URI caller chèn mode khác."""
    target = Path(path).resolve(strict=True)
    if not target.is_file():
        raise ValueError("invalid_db")
    conn = sqlite3.connect(target.as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def collect_tasks(provider, max_pages=10):
    """provider phải được inject; chỉ _page GET. Không giữ cache vô hạn."""
    if type(max_pages) is not int or not 1 <= max_pages <= 100:
        raise ValueError("invalid_pages")
    rows, warnings = [], []
    for page in range(1, max_pages + 1):
        batch = provider._page("seedance", page)
        if not isinstance(batch, list) or len(batch) > 50:
            raise ValueError("invalid_page")
        rows.extend(batch)
        if len(batch) < 50:
            break
    else:
        warnings.append("coverage_incomplete:page_limit")
    return rows, warnings


def reconcile(conn, tasks, pricing, warnings=()):
    from core import cost
    if not isinstance(tasks, list) or len(tasks) > MAX_ROWS:
        raise ValueError("invalid_tasks")
    validate_pricing(pricing)
    warnings = list(warnings)
    jobs = {}
    for raw in conn.execute("SELECT id,project_id,external_id,quality_tier,draft_job_id FROM jobs WHERE type='video_gen'"):
        job = dict(raw)
        if identifier(job["id"]) is None or identifier(job["project_id"]) is None:
            warnings.append("bad_type:job_identifiers")
            continue
        if job["draft_job_id"] is not None and identifier(job["draft_job_id"]) is None:
            warnings.append("bad_type:draft_job_id")
            job["draft_job_id"] = None
        tid = task_id(job["external_id"])
        if tid:
            jobs.setdefault(tid, []).append(job)
    events = {}
    for raw in conn.execute("SELECT id,job_id,project_id,model,tier,quantity,unit FROM usage_events WHERE kind='video' AND provider='clipai'"):
        events.setdefault(raw["job_id"], []).append(dict(raw))
    rows, seen = [], set()
    originals = {}
    for task in tasks:
        if not isinstance(task, dict):
            warnings.append("bad_type:task")
            continue
        tid = task_id(task.get("task_id"))
        if tid is None:
            warnings.append("missing_or_invalid:task_id")
            continue
        if tid in seen:
            warnings.append("duplicate_task:" + tid)
            if task != originals[tid]:
                row = next(r for r in rows if r["task_id"] == tid)
                row["warnings"].append("conflicting_duplicate_task")
                for field in ("actual_usd", "token_usd", "ledger_usd", "request_estimate_usd"):
                    row[field] = None
            continue
        seen.add(tid)
        originals[tid] = task
        notes = []
        if task.get("task_status") not in (2, "succeed", "success", "completed"):
            notes.append("task_incomplete_or_unknown_status")
        extra = mapping(task.get("extra_data"), notes, "extra_data")
        params = mapping(task.get("request_params"), notes, "request_params")
        usage = mapping(extra.get("usage"), notes, "usage")
        tokens = number(usage.get("total_tokens"))
        video = extra.get("has_video_input")
        video = video if type(video) is bool else None
        resolution = label(extra.get("resolution") or task.get("resolution") or params.get("resolution"))
        seconds = number(task.get("duration"))
        model = label(task.get("model_name") or params.get("model_name"))
        matched = jobs.get(tid, [])
        job = matched[0] if len(matched) == 1 else None
        if not matched:
            notes.append("unmatched_task")
        elif len(matched) > 1:
            notes.append("ambiguous_job")
        tier = label(job["quality_tier"]) if job else None
        content = params.get("content", [])
        if not isinstance(content, list):
            notes.append("bad_type:content")
            content = []
        upgrade = any(isinstance(c, dict) and c.get("type") == "draft_task" for c in content)
        draft = task.get("is_draft")
        if draft is not None and type(draft) is not bool:
            notes.append("bad_type:is_draft")
            draft = None
        kind = "upgrade" if upgrade or (job and job["draft_job_id"] is not None) else "draft" if draft is True or tier == "draft" else "direct" if draft is False and "bad_type:request_params" not in notes and "bad_type:content" not in notes else "unknown"
        if kind == "unknown":
            notes.append("missing_or_invalid:task_kind")
        actual = number(task.get("seedance_cost_usd"))
        estimate = number(params.get("seedance_cost_usd"))
        if estimate is None:
            notes.append("missing_or_invalid:request_estimate_usd")
        token_usd = number(cost.seedance_token_usd(model, tokens, video)) if model and tokens is not None and video is not None else None
        ledger = events.get(job["id"], []) if job else []
        ledger_usd = None
        ledger_seconds = None
        ledger_tier = None
        if len(ledger) == 1:
            event = ledger[0]
            ledger_tier = label(event["tier"])
            if event["project_id"] != job["project_id"]:
                notes.append("ledger_project_mismatch")
            elif event["unit"] not in ("second", "seconds", "s") or number(event["quantity"]) is None:
                notes.append("bad_type:ledger_seconds")
            elif not label(event["model"]) or not ledger_tier:
                notes.append("bad_type:ledger_model_tier")
            else:
                ledger_seconds = event["quantity"]
                ledger_usd = cost.clip_price(pricing, event["model"], ledger_tier, ledger_seconds)
                ledger_usd = number(ledger_usd)
        else:
            notes.append("ledger_missing" if not ledger else "ledger_multiple_events")
        for field, value in (("total_tokens", tokens), ("has_video_input", video), ("seconds", seconds), ("resolution", resolution), ("actual_usd", actual), ("token_usd", token_usd), ("ledger_usd", ledger_usd)):
            if value is None:
                notes.append("missing_or_invalid:" + field)
        rows.append(dict(task_id=tid, job_id=job["id"] if job else None, project_id=job["project_id"] if job else None,
                         quality_tier=tier, draft_job_id=job["draft_job_id"] if job else None, kind=kind,
                         resolution=resolution, has_video_input=video, seconds=seconds, total_tokens=tokens,
                         model=model, token_usd=token_usd, actual_usd=actual, request_estimate_usd=estimate,
                         ledger_seconds=ledger_seconds, ledger_tier=ledger_tier, ledger_usd=ledger_usd, warnings=notes))
    for tid in jobs.keys() - seen:
        warnings.append("job_missing_task:" + tid)
    totals = []
    for project in sorted({r["project_id"] for r in rows}, key=lambda p: (p is None, p or 0)):
        for kind in ("draft", "upgrade", "direct", "unknown"):
            group = [r for r in rows if r["project_id"] == project and r["kind"] == kind]
            if not group:
                continue
            total = dict(project_id=project, kind=kind, count=len(group))
            for field in ("actual_usd", "token_usd", "ledger_usd"):
                values = [r[field] for r in group if r[field] is not None]
                total[field + "_known"] = round(sum(values), 9) if values else None
                total[field + "_missing"] = len(group) - len(values)
            totals.append(total)
    samples = [dict(task_id=r["task_id"], model=r["model"], has_video_input=r["has_video_input"], resolution=r["resolution"], actual_usd=r["actual_usd"], token_usd=r["token_usd"],
                    difference_percent=difference_percent(r["token_usd"], r["actual_usd"]))
               for r in rows if r["actual_usd"] is not None]
    valid = [s for s in samples if s["difference_percent"] is not None and s["model"] and s["has_video_input"] is not None
             and "task_incomplete_or_unknown_status" not in next(r["warnings"] for r in rows if r["task_id"] == s["task_id"])]
    groups = []
    for model, video, resolution in sorted({(s["model"], s["has_video_input"], s["resolution"] or "") for s in valid}):
        groups.append(dict(model=model, has_video_input=video, resolution=resolution or None,
                           count=sum((s["model"], s["has_video_input"], s["resolution"] or "") == (model, video, resolution) for s in valid)))
    count = sum(s["resolution"] == "1080p" for s in valid)
    return dict(tasks=rows, totals=totals, calibration=samples, actual_1080p_points=count,
                calibration_groups=groups,
                warnings=warnings + (["calibration_insufficient:need_at_least_5_1080p_points"] if not any(g["resolution"] == "1080p" and g["count"] >= 5 for g in groups) else []))


def markdown(report):
    columns = ("task_id", "job_id", "project_id", "kind", "quality_tier", "resolution", "has_video_input", "seconds", "total_tokens", "token_usd", "ledger_usd", "actual_usd", "request_estimate_usd")
    lines = ["# Đối soát ClipAI (chỉ đọc)", "", "Tiền nháp và bước nâng tính riêng. Dấu ? = chưa biết, không phải 0.", "", "| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in report["tasks"]:
        lines.append("| " + " | ".join(str(row[c]) if row[c] is not None else "?" for c in columns) + " |")
    lines += ["", "## Tổng theo dự án / loại (chỉ cộng tiền đã biết)", "", "```json", json.dumps(report["totals"], ensure_ascii=False, indent=2), "```", "", "Điểm 1080p có tiền thật: " + str(report["actual_1080p_points"]) + ". Cần ≥ 5 điểm trước khi cân nhắc đổi giá.", "", "## Điểm hiệu chuẩn", "```json", json.dumps(report["calibration"], ensure_ascii=False, indent=2), "```", "", "## Cảnh báo"]
    lines.extend("- " + w for w in report["warnings"])
    lines += ["", "## Nhóm hiệu chuẩn (model / video vào / độ phân giải)", "```json", json.dumps(report["calibration_groups"], ensure_ascii=False, indent=2), "```"]
    for row in report["tasks"]:
        lines.extend("- " + row["task_id"] + ": " + w for w in row["warnings"])
    return "\n".join(lines)


def main(argv=None, *, live_provider=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--pricing", required=True, help="Bảng giá JSON chỉ định rõ; không đọc env")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--tasks-json", help="Danh sách task offline")
    source.add_argument("--live", action="store_true", help="Opt-in GET ClipAI; chỉ khi chọn mới đọc cấu hình provider từ môi trường")
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    stage = "pricing_input"
    try:
        pricing = read_json(args.pricing)
        validate_pricing(pricing)
        if args.live:
            stage = "provider_read"
            if live_provider is None:
                from core.adapters.clipai import ClipAIVideoProvider
                live_provider = ClipAIVideoProvider.from_env()
            tasks, warnings = collect_tasks(live_provider, args.max_pages)
        else:
            stage = "tasks_input"
            tasks = read_json(args.tasks_json)
            warnings = []
        stage = "database_or_reconcile"
        with closing(open_readonly(args.db)) as conn:
            report = reconcile(conn, tasks, pricing, warnings)
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) if args.json else markdown(report))
        return 0
    except Exception:
        # Không xuất exception: SQLite / transport / JSON có thể chứa đường dẫn hoặc nội dung nhạy cảm.
        print("Không đối soát được [" + stage + "]: kiểm tra file đầu vào, schema và provider chỉ đọc.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
