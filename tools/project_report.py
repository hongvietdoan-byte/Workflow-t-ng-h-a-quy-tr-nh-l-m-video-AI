"""Báo cáo tuần chỉ đọc, 0 USD. Không nạp provider, credential hay bootstrap CSDL.

Chạy: py tools/project_report.py --root <worktree> --as-of YYYY-MM-DD
Nguồn nhạy cảm chỉ đọc khi chỉ định --db / --session-dir. Không tự tìm ~/.claude.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

# CLI chạy trực tiếp từ tools/, không cần PYTHONPATH của máy người dùng.
CODE_ROOT = str(Path(__file__).resolve().parents[1])
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

VN = timezone(timedelta(hours=7), "Asia/Saigon")
SCHEMA = 1
TOKEN_FIELDS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
SECTION_TITLES = ("Tóm tắt 1 phút", "Tiến độ V3.1 theo mốc M0–M8", "Khối lượng", "Chi phí — bốn loại riêng", "Chất lượng", "Rủi ro mở", "Việc cần EP quyết và kế hoạch hai tuần")
SOURCE_SUFFIXES = {".py", ".ps1", ".sh", ".js", ".ts", ".tsx", ".css", ".html"}


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0 else None


def _stamp(value, *, naive_utc=False):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            if not naive_utc:
                return None
            parsed = parsed.replace(tzinfo=timezone.utc)  # SQLite datetime('now'), theo schema budget.py.
        return parsed.astimezone(VN)
    except ValueError:
        return None


def _date(value):
    result = date.fromisoformat(value)
    if result.isoformat() != value:
        raise ValueError("Ngày báo cáo phải đúng YYYY-MM-DD")
    return result


def _inside(root, relative):
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()) or any(p.is_symlink() for p in (path, *path.parents) if p != root.parent):
        raise ValueError("Đường nguồn/đích vượt phạm vi hoặc có liên kết tượng trưng")
    return path


def _json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def _metric(value, source, measured, reason="", unit=""):
    return {"value": value, "source": source, "measured_at": measured, "delta": None, "reason": reason if value is None else "", "unit": unit}


def _token_data(folder, cutoff):
    coverage = {"files": 0, "records": 0, "missing_id": 0, "conflicts": 0, "incomplete": 0, "malformed": 0}
    if folder is None:
        return [], coverage, None, None, "chưa chỉ định thư mục phiên của đúng dự án"
    folder = Path(folder)
    if not folder.is_dir() or folder.is_symlink():
        return [], coverage, None, None, "nguồn phiên thiếu hoặc là liên kết"
    root = folder.resolve()
    records, conflicts, sessions, days = {}, set(), set(), set()
    for path in sorted(folder.rglob("*.jsonl")):
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            coverage["malformed"] += 1
            continue
        coverage["files"] += 1
        try:
            stream = path.open(encoding="utf-8")
        except OSError:
            coverage["malformed"] += 1
            continue
        with stream:
            for line in stream:
                try:
                    row = json.loads(line)
                except ValueError:
                    coverage["malformed"] += 1
                    continue
                if not isinstance(row, dict) or not isinstance(row.get("message"), dict):
                    continue  # user/tool/progress không phải mẫu usage của assistant.
                msg = row["message"]
                if not isinstance(msg.get("usage"), dict) and msg.get("role") == "user":
                    continue
                if "usage" not in msg and "model" not in msg:
                    continue
                stamp = _stamp(row.get("timestamp"))
                if stamp is None:
                    coverage["incomplete"] += 1
                    continue
                if stamp > cutoff:
                    continue
                coverage["records"] += 1
                mid, sid = msg.get("id"), row.get("sessionId")
                if not isinstance(mid, str) or not mid:
                    coverage["missing_id"] += 1
                    continue
                model = msg.get("model")
                if not isinstance(model, str) or not re.fullmatch(r"(?:claude-(?:sonnet|opus|haiku)-[0-9]{1,2}(?:-[0-9]{1,8}){0,3}|claude-[0-9](?:-[0-9])?-(?:sonnet|opus|haiku)-[0-9]{8}|gpt-[0-9](?:\.[0-9])?(?:-(?:mini|nano|codex))?(?:-[0-9]{4}-[0-9]{2}-[0-9]{2})?|o[134](?:-mini)?(?:-[0-9]{4}-[0-9]{2}-[0-9]{2})?)", model):
                    model = "UNKNOWN"
                role = "agent" if row.get("isSidechain") is True or row.get("agentId") or row.get("agent_id") else "main" if row.get("isSidechain") is False else "UNKNOWN"
                usage = msg.get("usage")
                counts = {key: usage.get(key) if isinstance(usage.get(key), int) and not isinstance(usage.get(key), bool) and usage[key] >= 0 else None for key in TOKEN_FIELDS} if isinstance(usage, dict) else {key: None for key in TOKEN_FIELDS}
                # Cache thiếu = UNKNOWN, không ngầm đổi thành 0 hay che thiếu độ phủ.
                identity = (sid, model, role, stamp.strftime("%Y-%m"))
                if mid in records and records[mid][0] != identity:
                    conflicts.add(mid)
                    continue
                if mid in records:
                    previous = records[mid][1]
                    counts = {k: max(previous[k], counts[k]) if previous[k] is not None and counts[k] is not None else previous[k] if counts[k] is None else counts[k] for k in TOKEN_FIELDS}
                records[mid] = (identity, counts, stamp)
    groups = {}
    for mid, (identity, counts, stamp) in records.items():
        if mid in conflicts:
            continue
        sid, model, role, month = identity
        if not isinstance(sid, str) or not sid or model == "UNKNOWN" or role == "UNKNOWN" or any(v is None for v in counts.values()):
            coverage["incomplete"] += 1
        if isinstance(sid, str) and sid:
            sessions.add(sid)
        days.add(stamp.date().isoformat())
        key = (month, model, role)
        group = groups.setdefault(key, {"month": month, "model": model, "role": role, **{k: 0 for k in TOKEN_FIELDS}, "messages": 0})
        group["messages"] += 1
        for k, v in counts.items():
            group[k] = None if v is None or group[k] is None else group[k] + v
    coverage["conflicts"] = len(conflicts)
    incomplete = any(coverage[k] for k in ("missing_id", "conflicts", "incomplete", "malformed")) or not coverage["files"] or not coverage["records"] or not groups
    total = None if incomplete else sum(sum(g[k] for k in TOKEN_FIELDS) for g in groups.values())
    return list(groups.values()), coverage, total, ({"sessions": len(sessions), "days": len(days)} if records and not incomplete else None), "mẫu token thiếu trường/cache, xung đột ID hoặc nguồn chưa đầy đủ" if incomplete else ""


def _git(root, args):
    git = shutil.which("git")
    if not git:
        return None
    env = {k: os.environ[k] for k in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP") if k in os.environ}
    env.update({"HOME": str(root / ".report-no-home"), "USERPROFILE": str(root / ".report-no-home"), "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_OPTIONAL_LOCKS": "0"})
    try:
        result = subprocess.run([git, "--no-pager", "-C", str(root), *args], env=env, capture_output=True, encoding="utf-8", errors="replace", timeout=30, check=False)
        return result.stdout if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _first_pass(conn, tables, cutoff):
    if not {"jobs", "job_events"} <= tables:
        return None, [], "thiếu jobs/job_events để đối chiếu attempt và phán quyết"
    required = {"jobs": {"id", "project_id", "scene_id", "type"}, "job_events": {"id", "job_id", "at", "to_state", "from_state"}}
    if any(not fields <= {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')} for table, fields in required.items()):
        return None, [], "schema lịch sử job không đủ trường"
    groups = defaultdict(lambda: {"jobs": set(), "created": set(), "events": [], "bad": False})
    for row in conn.execute("SELECT j.id jid,j.project_id,j.scene_id,j.type,e.id eid,e.at,e.to_state,e.from_state FROM jobs j LEFT JOIN job_events e ON e.job_id=j.id WHERE j.type IN ('image_gen','video_gen')"):
        key = (row["project_id"], row["scene_id"], row["type"])
        group = groups[key]
        stamp = _stamp(row["at"], naive_utc=True)
        if stamp is not None and stamp > cutoff:
            continue
        group["jobs"].add(row["jid"])
        if stamp is None:
            group["bad"] = True
            continue
        if row["from_state"] is None and row["to_state"] == "queued":
            group["created"].add(row["jid"])
        group["events"].append((stamp, row["eid"], row["to_state"]))
    details = {kind: {"kind": kind, "first_pass": 0, "reviewed": 0, "unknown": 0, "regenerated": 0} for kind in ("image_gen", "video_gen")}
    for (_, _, kind), group in groups.items():
        item = details[kind]
        events = sorted(group["events"])
        decisions = [ev for ev in events if ev[2] in ("approved", "rejected")]
        if sum(ev[2] == "running" for ev in events) > 1:
            item["regenerated"] += 1
        if not group["jobs"]:
            continue
        if group["bad"] or group["jobs"] != group["created"]:
            item["unknown"] += 1
            continue
        if not decisions:
            continue  # Chưa có phán quyết: không nằm trong mẫu số. Rejected-only vẫn phải tính.
        first = decisions[0]
        before = [ev for ev in events if ev <= first]
        attempts = sum(ev[2] == "running" for ev in before)
        if not attempts:
            item["unknown"] += 1
            continue
        item["reviewed"] += 1
        item["first_pass"] += first[2] == "approved" and attempts == 1 and not any(ev[2] in ("rejected", "failed") for ev in before)
    rows = list(details.values())
    reviewed = sum(r["reviewed"] for r in rows)
    unknown = sum(r["unknown"] for r in rows)
    value = None if unknown or not reviewed else 100 * sum(r["first_pass"] for r in rows) / reviewed
    return value, rows, f"mẫu duyệt={reviewed}, lịch sử thiếu={unknown}; tại phán quyết approved/rejected đầu cần approved, đúng 1 running và chưa rejected/failed"


def _database(db, cutoff, measured):
    unknown = "chưa chỉ định CSDL hoặc thiếu bảng/cột nguồn"
    out = {"actual_usd": (None, unknown), "estimated_usd": (None, unknown), "held_usd": (None, unknown), "final_outputs": (None, unknown), "delivered_projects": (None, unknown), "ledger_rows": (None, unknown), "first_pass_rate": (None, unknown)}
    projects = []
    quality = []
    if db is None or not Path(db).is_file():
        return out, projects, quality
    conn = None
    try:
        conn = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN")
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        def columns(table):
            return {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}
        if "usage_events" in tables:
            cols = columns("usage_events")
            if "at" in cols:
                stamps = [_stamp(r["at"], naive_utc=True) for r in conn.execute("SELECT at FROM usage_events")]
                out["ledger_rows"] = (sum(stamp <= cutoff for stamp in stamps) if all(stamp is not None for stamp in stamps) else None, "ledger có ngày không đọc được")
            else:
                out["ledger_rows"] = (None, "ledger thiếu ngày, không thể chốt theo as-of")
            if {"usd", "at", "project_id"} <= cols:
                totals = defaultdict(list)
                for row in conn.execute("SELECT project_id, usd, at FROM usage_events"):
                    stamp = _stamp(row["at"], naive_utc=True)
                    if stamp is None or stamp <= cutoff:
                        totals[row["project_id"]].append(_number(row["usd"]) if stamp else None)
                all_values = [v for values in totals.values() for v in values]
                out["actual_usd"] = (None if any(v is None for v in all_values) else sum(all_values), "sổ chi có USD null hoặc ngày không đọc được")
                projects += [{"project": pid if isinstance(pid, int) else "UNKNOWN", "actual_usd": None if any(v is None for v in values) else sum(values)} for pid, values in totals.items()]
            else:
                out["actual_usd"] = (None, "usage_events chỉ có lượng dùng/model; không có USD chi thực tế, không quy đổi giá hiện tại thành hóa đơn")
        if "app_settings" in tables and {"key", "value"} <= columns("app_settings"):
            estimates = []
            for row in conn.execute("SELECT key, value FROM app_settings WHERE key GLOB 'project_budget:[0-9]*'"):
                if not re.fullmatch(r"project_budget:\d+", row["key"]):
                    continue
                try:
                    obj = json.loads(row["value"])
                except (ValueError, TypeError):
                    estimates.append(None)
                    continue
                approved = _stamp(obj.get("approved_at")) if isinstance(obj, dict) and obj.get("approved_at") else None
                historical = cutoff.date() != _stamp(measured).date()
                val = _number(obj.get("total")) if isinstance(obj, dict) and not historical and not (approved and approved > cutoff) else None
                estimates.append(val)
                projects.append({"project": int(row["key"].split(":")[1]), "estimated_usd": val})
            out["estimated_usd"] = (sum(estimates) if estimates and all(v is not None for v in estimates) else None, "dự toán snapshot chỉ có tại lúc đo, không phục hồi ngày quá khứ hoặc approved_at tương lai; total thiếu/không hợp lệ cũng UNKNOWN")
        if "llm_holds" in tables and {"at", "usd"} <= columns("llm_holds"):
            # Snapshot hold chỉ có nghĩa lúc đo, không phục hồi lịch sử từ bảng đang sống.
            now = _stamp(measured)
            if cutoff.date() == now.date():
                values, invalid = [], False
                for row in conn.execute("SELECT at, usd FROM llm_holds"):
                    stamp = _stamp(row["at"], naive_utc=True)
                    if stamp is None:
                        invalid = True
                    elif now - timedelta(minutes=30) <= stamp <= now:
                        values.append(_number(row["usd"]))
                out["held_usd"] = (None if invalid or any(v is None for v in values) else sum(values), "hold có timestamp/USD thiếu; chỉ tính llm_holds TTL 30 phút, không tính queued/reserve")
            else:
                out["held_usd"] = (None, "không có snapshot hold lịch sử cho ngày báo cáo")
        for table, key, stamp_column in (("outputs", "final_outputs", "created_at"), ("deliveries", "delivered_projects", "delivered_at")):
            required = {"kind", "created_at"} if table == "outputs" else {"project_id", "delivered_at"}
            if table in tables and required <= columns(table):
                query = "SELECT created_at FROM outputs WHERE kind='final'" if table == "outputs" else "SELECT project_id,delivered_at FROM deliveries"
                rows = list(conn.execute(query))
                stamps = [_stamp(row[stamp_column]) for row in rows]
                # outputs dùng ISO UTC; deliveries legacy dùng giờ local không offset → UNKNOWN,
                # không tự giả định timezone lịch sử của máy đã ghi.
                if any(stamp is None for stamp in stamps):
                    out[key] = (None, "ngày artifact/giao thiếu timezone hoặc không đọc được; không suy lịch sử")
                elif table == "outputs":
                    out[key] = (sum(stamp <= cutoff for stamp in stamps), "")
                else:
                    out[key] = (len({row["project_id"] for row, stamp in zip(rows, stamps) if stamp <= cutoff}), "")
            elif table in tables:
                out[key] = (None, "thiếu cột ngày để chốt as-of, không đếm snapshot như lịch sử")
        first_pass, quality, quality_reason = _first_pass(conn, tables, cutoff)
        out["first_pass_rate"] = (first_pass, quality_reason)
        conn.rollback()
        conn.close()
    except (sqlite3.Error, OSError, ValueError):
        out = {k: (None, "không đọc được snapshot CSDL chỉ đọc; không xuất lỗi thô") for k in out}
        projects = []
    finally:
        if conn is not None:
            conn.close()
    return out, projects, quality


def _safe_id(value):
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", value) else "UNKNOWN"


def collect_report(root, *, as_of=None, db=None, session_dir=None, baseline=None):
    root = Path(root).resolve()
    day = _date(as_of or datetime.now(VN).date().isoformat())
    cutoff = datetime.combine(day, time.max, VN)
    measured = datetime.now(VN).isoformat(timespec="seconds")
    identities = {"root": str(root), "db": str(Path(db).resolve()) if db is not None else None, "sessions": str(Path(session_dir).resolve()) if session_dir is not None else None, "period": "7d-Asia/Saigon", "schema": SCHEMA}
    report = {"schema": SCHEMA, "scope": hashlib.sha256(json.dumps(identities, sort_keys=True).encode()).hexdigest(), "as_of": day.isoformat(), "measured_at": measured,
              "period": {"from": (day - timedelta(days=6)).isoformat(), "to": day.isoformat()}, "metrics": {}, "warnings": [], "sections": list(SECTION_TITLES), "token_groups": [], "project_costs": [], "waves": [], "workload": [], "open_error_items": [], "ep_pending": [], "pending_questions": []}
    def metric(key, value, source, reason="", unit=""):
        report["metrics"][key] = _metric(value, source, measured, reason, unit)
    records = _json(_inside(root, "devsys/plans.json"))
    main = [r for r in records if isinstance(r, dict) and r.get("chinh") is True and r.get("kieu") == "viec_s"] if isinstance(records, list) else []
    plan = None
    if len(main) == 1 and isinstance(main[0].get("file"), str):
        try:
            path = _inside(root, main[0]["file"])
            from devsys import plan_progress
            plan = plan_progress.load(str(path))
            if plan and plan["bad"]:
                plan = None
            if plan:
                summary = plan_progress.summary(plan)
                report["waves"] = [{k: w.get(k) for k in ("id", "n", "done", "doing", "waiting", "pct", "pct_gate")} for w in summary["waves"]]
        except (OSError, ValueError):
            plan = None
    for key, field in (("code_pct", "total_code"), ("gate_pct", "total_gate")):
        metric(key, summary[field] if plan else None, "devsys/plans.json → devsys.plan_progress, snapshot lúc đo", "thiếu kế hoạch chính hợp lệ; không tự chọn kế hoạch khác", "%")
    week = report["period"]["from"]
    count = _git(root, ["rev-list", "--count", f"--since={week}T00:00:00+07:00", f"--until={day.isoformat()}T23:59:59+07:00", "HEAD"])
    metric("commits_week", int(count.strip()) if count and count.strip().isdigit() else None, "git rev-list, kỳ 7 ngày Asia/Saigon", "không có metadata Git", "commit")
    tracked = _git(root, ["ls-files", "-z"])
    buckets, tests = defaultdict(lambda: {"files": 0, "lines": 0}), 0
    if tracked is not None:
        for name in tracked.split("\0"):
            if not name or Path(name).suffix not in SOURCE_SUFFIXES or any(x in name.lower() for x in ("secret", "credential", ".env", "data/", "node_modules/")):
                continue
            try:
                text = _inside(root, name).read_text(encoding="utf-8")
            except (OSError, ValueError, UnicodeError):
                continue
            directory = name.split("/")[0] if name.split("/")[0] in {"core", "dashboard", "devsys", "tests", "tools"} else "khác"
            buckets[directory]["files"] += 1
            buckets[directory]["lines"] += len(text.splitlines())
            if directory == "tests" and name.endswith(".py"):
                tests += len(re.findall(r"^\s*(?:async\s+)?def test_\w+\s*\(", text, re.M))
    report["workload"] = [{"directory": key, **value} for key, value in sorted(buckets.items())]
    metric("test_functions_static", tests if tracked is not None else None, "git ls-files + đếm định nghĩa test tĩnh", "không có metadata Git; không chạy test", "hàm, không phải cases xanh")
    groups, coverage, token_total, activity, reason = _token_data(session_dir, cutoff)
    report["token_groups"], report["coverage"] = groups, coverage
    metric("tokens", token_total, "JSONL thư mục dự án được chỉ định; message.id cumulative max xuyên file", reason, "token, không phải USD")
    for key in ("build_tokens", "video_operation_tokens"):
        metric(key, None, "JSONL không có liên kết dự án video/loại tác vụ đáng tin", "chưa tách được xây công cụ với vận hành video; không suy mọi phiên repo là build", "token")
    for key in ("sessions", "days"):
        metric(key, activity[key] if activity else None, "JSONL allowlist metadata đến ngày báo cáo", reason, "phiên" if key == "sessions" else "ngày")
    if reason:
        report["warnings"].append("Nguồn token chưa đầy đủ; không suy USD từ token hoặc hạn mức tài khoản")
    costs, report["project_costs"], report["quality_history"] = _database(db, cutoff, measured)
    for key, (value, reason) in costs.items():
        source = {"held_usd": "llm_holds TTL 30 phút, phần giữ chỗ LLM hiện tại, không phải tổng mọi job", "actual_usd": "usage_events.usd nếu có, không tự quy đổi quantity", "estimated_usd": "app_settings project_budget:<id>.total, snapshot", "ledger_rows": "usage_events COUNT metadata snapshot", "first_pass_rate": "jobs + job_events approved/rejected/running", "final_outputs": "outputs.kind=final, số bản ghi artifact, không kiểm file", "delivered_projects": "deliveries DISTINCT project_id, số dự án ghi đã giao"}.get(key, "snapshot CSDL mode=ro/query_only/BEGIN")
        metric(key, value, source, reason, "USD" if key.endswith("usd") else "%" if key == "first_pass_rate" else "dòng" if key == "ledger_rows" else "artifact" if key == "final_outputs" else "dự án")
    for key, reason in (("test_passed", "chưa có artifact test có cấu trúc; không chạy test để đếm"), ("test_failed", "chưa có artifact test có cấu trúc; không chạy test để đếm")):
        metric(key, None, "nguồn chất lượng chưa được nghiệm thu", reason)
    errors = _json(_inside(root, "devsys/errors.json"))
    errors = errors.get("items") if isinstance(errors, dict) else None
    metric("open_errors", sum(r.get("status") != "VERIFIED" for r in errors if isinstance(r, dict)) if isinstance(errors, list) else None, "devsys/errors.json snapshot lúc đo, status khác VERIFIED", "không có sổ lỗi có cấu trúc")
    if isinstance(errors, list):
        for row in errors:
            if isinstance(row, dict) and row.get("status") != "VERIFIED":
                report["open_error_items"].append({key: _safe_id(row.get(key)) for key in ("id", "stage", "category", "severity", "status")})
    decisions = _json(_inside(root, "data/decisions.json"))
    decisions = decisions.get("items", decisions.get("decisions")) if isinstance(decisions, dict) else decisions
    if isinstance(decisions, list):
        report["ep_pending"] = [{"id": _safe_id(row.get("id")), "phase": _safe_id(row.get("phase"))} for row in decisions if isinstance(row, dict) and isinstance(row.get("phase"), str) and row["phase"] != "APPROVED"]
    missing_phase = sum(not isinstance(row.get("phase"), str) for row in decisions if isinstance(row, dict)) if isinstance(decisions, list) else None
    metric("ep_decisions", len(report["ep_pending"]) if isinstance(decisions, list) else None, "data/decisions.json snapshot lúc đo, phase có khai báo và khác APPROVED", "không có sổ quyết định có cấu trúc")
    metric("decision_phase_unknown", missing_phase, "data/decisions.json, record legacy thiếu phase", "không có sổ quyết định; không đoán legacy đã duyệt hoặc đang chờ")
    mail = _inside(root, "hop_thu/su_kien")
    asks, replies, broken = set(), set(), False
    if mail.is_dir():
        for path in mail.glob("*.json"):
            row = _json(path) if not path.is_symlink() else None
            if not isinstance(row, dict):
                broken = True
                continue
            if row.get("kind") == "hoi":
                asks.add(path.name)
            elif row.get("kind") == "tra_loi":
                replies.add(str(row.get("reply_to", "")))
    report["pending_questions"] = [{"id": _safe_id(name.removesuffix(".json"))} for name in sorted(asks - replies)]
    metric("mail_questions", len(asks - replies) if mail.is_dir() and not broken else None, "hộp thư sự kiện snapshot lúc đo, hỏi chưa có reply_to", "thiếu hoặc hỏng sự kiện hộp thư")
    report["next_two_weeks"] = {"status": "ĐỀ XUẤT, chưa phải EP phê duyệt", "actions": ["Đối soát cổng nghiệm thu còn mở theo kế hoạch chính", "Ưu tiên quyết định EP và lỗi mở trước khi mở phạm vi mới"], "source": "devsys.plan_progress + số quyết định/lỗi; không tự giao việc", "measured_at": measured}
    if baseline is None:
        candidate = _inside(root, f"docs/reports/BAO_CAO_DU_AN_{(day - timedelta(days=7)).isoformat()}.json")
        baseline = candidate if candidate.is_file() else None
    if baseline is not None:
        previous = _json(Path(baseline))
        if isinstance(previous, dict) and previous.get("schema") == SCHEMA and previous.get("scope") == report["scope"] and isinstance(previous.get("metrics"), dict) and isinstance(previous.get("as_of"), str) and previous["as_of"] < report["as_of"]:
            for key, current in report["metrics"].items():
                old_metric = previous["metrics"].get(key)
                old = old_metric.get("value") if isinstance(old_metric, dict) else None
                if _number(old) is not None and _number(current["value"]) is not None:
                    current["delta"] = round(current["value"] - old, 6)
        else:
            report["warnings"].append("Không so kỳ trước: schema/scope/ngày không tương thích; không phân tích văn xuôi")
    return report


def render_markdown(report):
    def cell(value):
        return str(value).replace("|", "/").replace("\n", " ")
    lines = [f"# Báo cáo dự án — {report['as_of']}", "", f"Ngày đo: {report['measured_at']} · Asia/Saigon · kỳ {report['period']['from']} → {report['period']['to']}", "", "Chỉ đọc, 0 USD. UNKNOWN không phải 0. Nguồn phiên có thể chỉ bao phủ một phần hoạt động."]
    groups = (("code_pct", "gate_pct", "ep_decisions"), ("code_pct", "gate_pct"), ("commits_week", "test_functions_static", "sessions", "days"), ("tokens", "build_tokens", "video_operation_tokens", "estimated_usd", "actual_usd", "held_usd"), ("final_outputs", "delivered_projects", "first_pass_rate", "test_passed", "test_failed", "ledger_rows"), ("open_errors",), ("ep_decisions", "decision_phase_unknown", "mail_questions"))
    for i, (title, keys) in enumerate(zip(report["sections"], groups), 1):
        lines += ["", f"## {i}. {title}", "", "| Chỉ số | Giá trị | Đơn vị | So kỳ trước | Nguồn | Ngày đo |", "|---|---|---|---|---|---|"]
        for key in keys:
            m = report["metrics"][key]
            val = m["value"] if m["value"] is not None else "UNKNOWN — không có dữ liệu: " + m["reason"]
            lines.append("| " + " | ".join(cell(v) for v in (key, val, m["unit"], m["delta"] if m["delta"] is not None else "không có dữ liệu so sánh", m["source"], m["measured_at"])) + " |")
        if i == 1:
            errors = report["metrics"]["open_errors"]["value"]
            unknown = any(m["value"] is None for m in report["metrics"].values())
            state = "ĐỎ" if errors is not None and errors > 0 else "VÀNG" if unknown or report["metrics"]["gate_pct"]["value"] != 100 else "XANH"
            lines += ["", f"Trạng thái theo nguồn hiện có: {state}. Ba điểm: code khác cổng; token khác USD; khoản giữ chỗ khác chi thực tế. Không thay EP nghiệm thu."]
        if i == 2:
            lines += ["", f"Nguồn: devsys.plan_progress; ngày đo {report['measured_at']}. Các hàng mốc chưa có đối chiếu riêng ⇒ so kỳ trước: UNKNOWN."]
            lines += ["", "| Mốc | Việc | Code % | Cổng % |", "|---|---|---|---|"]
            lines += [f"| {w['id']} | {w['n']} | {w['pct']} | {w['pct_gate']} |" for w in report["waves"]]
        if i == 3:
            lines += ["", f"Nguồn: git ls-files và dòng mã tĩnh; ngày đo {report['measured_at']}. So kỳ trước từng thư mục: UNKNOWN."]
            lines += ["", "| Thư mục nguồn | File | Dòng tĩnh |", "|---|---|---|"]
            lines += [f"| {w['directory']} | {w['files']} | {w['lines']} |" for w in report["workload"]]
        if i == 4:
            lines += ["", f"Nguồn token: JSONL metadata được chỉ định; nguồn USD: snapshot CSDL. Ngày đo {report['measured_at']}. So kỳ trước từng model/dự án: UNKNOWN. Độ phủ token: {json.dumps(report['coverage'], ensure_ascii=False)}."]
            lines += ["", "Token phiên dự án/phạm vi nguồn; chưa tách được xây công cụ với vận hành video. Không phải giá USD; llm_calls production chưa dùng phân loại và không cộng trùng vào tổng JSONL:", "", "| Tháng Asia/Saigon | Model | Vai | Input | Output | Cache read | Cache write |", "|---|---|---|---|---|---|---|"]
            for g in report["token_groups"]:
                lines.append("| " + " | ".join(cell(g[k] if g[k] is not None else "UNKNOWN") for k in ("month", "model", "role", *TOKEN_FIELDS)) + " |")
            lines += ["", "Chi sản xuất theo dự án (không tự gán chi xây công cụ vào video):", "", "| Dự án | Dự toán USD | Chi thực USD |", "|---|---|---|"]
            lines += [f"| {p['project']} | {p.get('estimated_usd') if p.get('estimated_usd') is not None else 'UNKNOWN' } | {p.get('actual_usd') if p.get('actual_usd') is not None else 'UNKNOWN' } |" for p in report["project_costs"]]
        if i == 5:
            lines += ["", f"Nguồn: jobs + job_events snapshot mode=ro; ngày đo {report['measured_at']}. So kỳ trước từng loại: UNKNOWN."]
            lines += ["", "Lịch sử đạt lần đầu: mẫu số gồm shot đã có phán quyết approved/rejected; tử số approved ngay phán quyết đầu, đúng một running, không failed trước đó; thiếu lịch sử ⇒ UNKNOWN.", "", "| Loại | Đạt lần đầu | Đã phán quyết đủ lịch sử | Thiếu lịch sử | Có gen lại |", "|---|---|---|---|---|"]
            lines += [f"| {q['kind']} | {q['first_pass']} | {q['reviewed']} | {q['unknown']} | {q['regenerated']} |" for q in report["quality_history"]]
        if i == 6:
            lines += ["", "| Mã lỗi | Khâu | Loại | Mức | Trạng thái |", "|---|---|---|---|---|"]
            lines += ["| " + " | ".join(cell(e[k]) for k in ("id", "stage", "category", "severity", "status")) + " |" for e in report["open_error_items"]]
            lines += ["", *[f"- {w}" for w in report["warnings"]], "- Không suy tỉ lệ đạt lần đầu từ retry_count; không coi lượng usage là hóa đơn USD."]
        if i == 7:
            lines += ["", "Chỉ dẫn mở nguồn theo ID, không xuất văn bản tự do/email của quyết định hoặc tin:", *[f"- Quyết định {e['id']}: {e['phase']}" for e in report["ep_pending"]], *[f"- Hỏi chưa trả lời: {e['id']}" for e in report["pending_questions"]]]
            lines += ["", report["next_two_weeks"]["status"], *[f"- {a}" for a in report["next_two_weeks"]["actions"]]]
    return "\n".join(lines) + "\n"


def write_report(report, root):
    root = Path(root).resolve()
    _date(report["as_of"])
    directory = _inside(root, "docs/reports")
    directory.mkdir(parents=True, exist_ok=True)
    base = f"BAO_CAO_DU_AN_{report['as_of']}"
    md, structured = _inside(root, f"docs/reports/{base}.md"), _inside(root, f"docs/reports/{base}.json")
    # Replace inode đích, không mở truncate một hardlink có thể trỏ tới file ngoài root.
    for target, text in ((md, render_markdown(report)), (structured, json.dumps(report, ensure_ascii=False, indent=2))):
        descriptor, name = tempfile.mkstemp(prefix=".report-write-", dir=directory, suffix=".tmp")
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(text)
            _inside(root, "docs/reports/" + target.name)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()
    return md, structured


def _pdf_tools():
    pandoc = shutil.which("pandoc")
    browser = next((candidate for name in ("msedge", "chrome", "chromium") if (candidate := shutil.which(name))), None)
    if browser is None:
        for base in ("C:/Program Files", "C:/Program Files (x86)"):
            for relative in ("Microsoft/Edge/Application/msedge.exe", "Google/Chrome/Application/chrome.exe"):
                candidate = Path(base) / relative
                if candidate.is_file():
                    browser = str(candidate)
                    break
            if browser:
                break
    return pandoc, browser


def _browser_process(args, env, cwd):
    """Chỉ sở hữu cây renderer vừa mở; không dừng Chrome/Edge khác trên máy."""
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    process = subprocess.Popen(args, env=env, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **options)
    try:
        process.communicate(timeout=60)
        return process.returncode == 0
    except subprocess.TimeoutExpired:
        if process.poll() is None:
            if os.name == "nt":
                taskkill = str(Path(env.get("SYSTEMROOT", "C:/Windows")) / "System32/taskkill.exe")
                try:
                    subprocess.run([taskkill, "/PID", str(process.pid), "/T", "/F"], env=env, cwd=cwd, capture_output=True, timeout=10, check=False)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            else:
                import signal
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if process.poll() is None:
                process.kill()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)
        return False


def render_pdf(markdown, root):
    """Renderer local tùy chọn; không tải tool, không mở UI hoặc kế thừa secrets."""
    root = Path(root).resolve()
    markdown = Path(markdown).resolve()
    directory = _inside(root, "docs/reports")
    if markdown.parent != directory or markdown.suffix != ".md":
        raise ValueError("PDF chỉ nhận Markdown báo cáo trong docs/reports")
    output = _inside(root, "docs/reports/" + markdown.with_suffix(".pdf").name)
    pandoc, browser = _pdf_tools()
    if not pandoc or not browser:
        return None, "PDF: không có đủ pandoc và Chrome/Edge local; không tải công cụ"
    with tempfile.TemporaryDirectory(prefix=".report-pdf-", dir=directory) as temporary:
        temp = Path(temporary)
        if not temp.resolve().is_relative_to(directory):
            raise ValueError("Thư mục PDF vượt phạm vi")
        html = temp / "report.html"
        profile = temp / "profile"
        env = {k: os.environ[k] for k in ("PATH", "SYSTEMROOT", "WINDIR") if k in os.environ}
        env.update({"HOME": str(temp), "USERPROFILE": str(temp), "TEMP": str(temp), "TMP": str(temp), "PYTHONUTF8": "1"})
        commands = [[str(pandoc), str(markdown), "--from=gfm", "--to=html", "--standalone", "--metadata=pagetitle:Báo cáo dự án", "--output=" + str(html)],
                    [str(browser), "--headless=new", "--no-pdf-header-footer", "--disable-gpu", "--disable-background-networking", "--disable-sync", "--no-first-run", "--disable-extensions", "--disable-component-update", "--host-resolver-rules=MAP * ~NOTFOUND", "--user-data-dir=" + str(profile), "--print-to-pdf=" + str(temp / "report.pdf"), html.as_uri()]]
        try:
            first = subprocess.run(commands[0], env=env, cwd=temp, capture_output=True, timeout=60, check=False)
            if first.returncode != 0 or not html.is_file():
                return None, "PDF: chuyển HTML local không thành công; không xuất lỗi thô"
            text = html.read_text(encoding="utf-8")
            if "<head>" not in text:
                return None, "PDF: HTML thiếu head để đặt chính sách không mạng"
            csp = '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;; img-src data:; font-src &#39;none&#39;; connect-src &#39;none&#39;">'
            css = "<style>@page{size:A4 landscape;margin:12mm}html,body{max-width:none!important;width:auto!important;margin:0!important;padding:0!important;font:9pt Arial,sans-serif!important}table{width:100%;table-layout:fixed;border-collapse:collapse}th,td{overflow-wrap:anywhere;word-break:break-word;padding:3px;border:1px solid #aaa;font-size:8pt}thead{display:table-header-group}tr{break-inside:avoid}pre,code{white-space:pre-wrap;overflow-wrap:anywhere}</style>"
            html.write_text(text.replace("<head>", "<head>" + csp, 1).replace("</head>", css + "</head>", 1), encoding="utf-8")
            success = _browser_process(commands[1], env, temp)
            generated = temp / "report.pdf"
            if not success or not generated.is_file() or not generated.read_bytes().startswith(b"%PDF-"):
                return None, "PDF: renderer local chưa tạo PDF hợp lệ; không xuất lỗi thô"
            # Chỉ đưa file tạm đã kiểm vào đích cùng phạm vi, không ghi chỗ renderer chỉ định từ dữ liệu.
            _inside(root, "docs/reports/" + output.name)
            os.replace(generated, output)
        except (OSError, subprocess.TimeoutExpired):
            return None, "PDF: lỗi/timeout renderer local; không xuất lỗi thô"
    return output, ""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--as-of", help="Ngày chốt báo cáo YYYY-MM-DD, mặc định hôm nay Asia/Saigon")
    parser.add_argument("--week", action="store_true", help="Báo cáo kỳ 7 ngày (mặc định); không tạo lịch nền")
    parser.add_argument("--db", type=Path, help="CSDL chỉ đọc explicit, không bootstrap")
    parser.add_argument("--session-dir", type=Path, help="ĐÚNG một thư mục dự án Claude; không tự glob ~/.claude")
    parser.add_argument("--baseline", type=Path, help="JSON sidecar cùng schema/scope của kỳ trước")
    parser.add_argument("--pdf", action="store_true", help="PDF chỉ khi có công cụ local đã kiểm, không tải mạng")
    args = parser.parse_args(argv)
    try:
        report = collect_report(args.root, as_of=args.as_of, db=args.db, session_dir=args.session_dir, baseline=args.baseline)
        markdown, _ = write_report(report, args.root)
        if args.pdf:
            _, warning = render_pdf(markdown, args.root)
            if warning:
                report["warnings"].append(warning)
                write_report(report, args.root)
    except (ValueError, OSError):
        print("Không tạo báo cáo: phạm vi/nguồn/đích không hợp lệ; không xuất lỗi thô")
        return 1
    print("Đã tạo báo cáo Markdown/JSON trong docs/reports; dữ liệu nguồn chỉ đọc")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
