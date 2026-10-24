"""Diagnostics for real trial runs: what failed, what failed silently, and where the flow is not smooth.

Three parts:
- `record()`: every stage reports problems here (provider errors, transient retries, bad JSON from the model, stops...).
  Repeats are merged (one row with a counter) so a flood does not hide the rest. It never raises: watching must not
  break the work.
- `scan()`: looks at the database for things that went wrong WITHOUT any error being raised (a job stuck for
  ever, a "succeeded" job with no file, a run that stopped ticking, many retries...).
- `report()`: one redacted text (no tokens, no home paths) the user can paste into the chat so the problems can be fixed.
"""
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

STAGES = (("director", "Director (phân cảnh)"), ("previz", "Layout / storyboard"), ("image", "Gen ảnh"), ("qc", "QC ảnh"), ("motion", "Motion prompt"),
          ("video", "Gen video"), ("voice", "Giọng thoại (TTS)"), ("music", "Nhạc nền"), ("render", "Ghép & render"),
          ("autopilot", "Chạy tự động"), ("system", "Hệ thống"))
# C-DEVSYS-MAPS: sự kiện QUAN SÁT (bước bấm Dashboard / lệnh CLI, core/ui_step, cờ ui_step_log) — không phải lỗi: không vào bảng khâu,
# danh sách gần đây / lặp lại của ⚙ Chẩn đoán, trang Sức khỏe devsys hay đề xuất sổ lỗi (tools/project_error_report)
OBSERVE = ("ui_step", "cli_step")
_NOT_OBSERVE = "stage NOT IN ('ui_step', 'cli_step')"
OTHER = "other"                     # stage_table row for any stage name not in STAGES (S14.4 C1b: nothing disappears)
STAGE_LABEL = {**dict(STAGES), OTHER: "Khác"}
# S14.4 C1b (04/10): other spellings seen in the code / old rows -> the one name of STAGES. No 'lipsync' here: nothing writes it.
STAGE_ALIASES = {"videos": "video", "images": "image", "image_gen": "image", "video_gen": "video", "delivery": "render",
                 "translate": "motion",          # claude_tasks.translate_motion_fields (_run tag 'translate')
                 "qc_sequence": "qc"}             # core/sequence_logic.py (QC logic cả chuỗi clip)


def normalize_stage(stage) -> str:
    """'videos' -> 'video', 'delivery' -> 'render' …; an unknown name is kept (lower case) and shown under 'Khác'."""
    s = str(stage or "").strip().lower()
    return STAGE_ALIASES.get(s, s)
SEVERITIES = ("info", "warn", "error")
STUCK_MIN = {"image_gen": int(os.environ.get("DIAG_STUCK_IMAGE_MIN", "10")),
             "video_gen": int(os.environ.get("DIAG_STUCK_VIDEO_MIN", "30"))}
QUEUED_MIN = int(os.environ.get("DIAG_QUEUED_MIN", "15"))
RETRY_WARN = float(os.environ.get("DIAG_RETRY_WARN", "0.4"))

_SECRETS = [(re.compile(r"sk-[A-Za-z0-9_\-]{8,}"), "sk-***"), (re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{8,}"), "Bearer ***"),
            (re.compile(r"(?i)(token|key|secret|password)(\"?\s*[:=]\s*\"?)[^\s\",;]{6,}"), r"\1\2***"),
            (re.compile(r"[A-Za-z0-9+/_\-]{40,}"), None)]       # None: _long_run (a key / base64 run, but not a POSIX path)


def _long_run(m: "re.Match") -> str:
    """C-PORT4 (21/10): the 40+ run also matched a POSIX path ('/tmp/pytest-of-root/…/gone.png' → '***.png') — on Windows the '\\'
    breaks it, so the same note named the file there and hid it on Linux. An absolute path (starts with ONE '/', not after ':' / '=',
    every part between '/' shorter than 40) is kept; a key, base64 ('/9j/…' has a long part), '//host/…' or 'key=/…' is still hidden."""
    run, start = m.group(0), m.start()
    before = m.string[start - 1] if start else ""
    if run.startswith("/") and not run.startswith("//") and before not in (":", "=") \
            and all(len(part) < 40 for part in run.split("/")):
        return run
    return "***"


def redact(text: str) -> str:
    text = str(text)
    home = os.path.expanduser("~")
    if home and home != "~":
        text = text.replace(home, "~").replace(home.replace("\\", "/"), "~")
    for pattern, repl in _SECRETS:
        text = pattern.sub(repl if repl is not None else _long_run, text)
    return text


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


LOST = {"count": 0}                 # diagnostics that could not be written to the database (shown in the ⚙ diagnostics panel)


def lost() -> int:
    return LOST["count"]


def _db_file(conn) -> Optional[str]:
    try:
        row = conn.execute("PRAGMA database_list").fetchone()
        return row[2] or None
    except Exception:  # noqa: BLE001 - a closed / odd connection: no file to write next to
        return None


def _keep_lost(conn, line: str, error: Exception) -> None:
    """A diagnostic the database refused is not dropped silently: it goes to stderr and to <db>.diag_lost.log, and is counted."""
    LOST["count"] += 1
    text = f"{_now()} {line} [sqlite: {type(error).__name__}: {error}]"
    print(f"[diag] could not write to the database: {text}", file=sys.stderr)
    path = _db_file(conn)
    if path:
        try:
            with open(path + ".diag_lost.log", "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except OSError:
            pass


def record(conn, stage: str, severity: str, message: str, code: Optional[str] = None, project_id: Optional[int] = None,
           scene_id: Optional[int] = None, job_id: Optional[int] = None) -> None:
    """Note a problem. Same stage/severity/code/message/project within 10 minutes = one row with a growing counter.
    Never raises; a busy database is retried, and a diagnostic that still cannot be written is kept by _keep_lost (not swallowed)."""
    msg = redact(message)[:400]
    stage = normalize_stage(stage) or "system"
    last: Optional[Exception] = None
    for attempt in range(3):
        try:
            _write(conn, stage, severity, msg, code, project_id, scene_id, job_id)
            return
        except sqlite3.OperationalError as e:            # "database is locked": another thread is writing — wait a little
            last = e
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
            time.sleep(0.2 * (attempt + 1))
        except sqlite3.Error as e:
            last = e
            break
    _keep_lost(conn, f"{stage}/{severity}/{code or '-'} p{project_id or '-'}: {msg}", last)


MERGE_WINDOW_MIN = 24 * 60
"""V3.1 M1.7 (G56, cờ diag_merge): cửa sổ gộp theo (mã, shot) — #31 15–18/10 `change_review_hold` 4 435 lần, `plate_stale` 337 lần
(câu đổi theo job / lý do nên khóa "cùng câu trong 10 phút" không gộp được)."""
MERGE_CODES = ("change_review_hold", "video_pregen_hold", "final_wait", "end_frame_wait", "video_gate_hold", "plate_stale",
               "QUEUE_CAPACITY", "QUEUE_CONFIG", "QUEUE_UNKNOWN_CAPACITY",   # M1.5 Kho chủ thể (cờ subject_capacity_guard)
               "stage_desk_hold",                                            # C-FIX6: cổng S-C plate 3D bắt buộc (runner, mỗi vòng)
               "reference_roles_hold")                                       # CX24-P34-D6: thiếu/sai vai ảnh tham chiếu (mỗi vòng)
"""Chỉ các mã báo GIỮ / nền cũ lặp mỗi vòng (runner.HOLD_CODES + plate_stale) — rà quy ước 7: mã khác có nơi đọc theo job_id / theo chữ
(video_gate plate_layout, end_frames dropped_reason, money_policy.note [key]) nên KHÔNG gộp."""


def _merge_on() -> bool:
    try:
        from . import features
        return features.on("diag_merge")
    except Exception:  # noqa: BLE001 - a diagnostic is never lost for a settings problem: the old key
        return False


def _write(conn, stage, severity, msg, code, project_id, scene_id, job_id) -> None:
    row = None
    merged = False
    if code in MERGE_CODES and scene_id and _merge_on():   # G56: same code + shot + job within a day = one row, newest wording
        # C-FIX-M16-17: one job says plate_stale for SEVERAL shots of its scene ("shot N: …", runner._stale_plates) — the shot named in
        # the line is part of the key, else the other shots' lines were merged away into the newest one
        head = msg.split(":", 1)[0] + ":" if code == "plate_stale" and msg.startswith("shot ") and ":" in msg else ""
        row = conn.execute(
            "SELECT id FROM diag_events WHERE stage=? AND severity=? AND code=? AND COALESCE(project_id,0)=? AND scene_id=?"
            " AND COALESCE(job_id,0)=? AND substr(message, 1, ?)=? AND (julianday('now') - julianday(last_at)) * 1440 < ?"
            " ORDER BY id DESC LIMIT 1",
            (stage, severity, code, project_id or 0, scene_id, job_id or 0, len(head), head, MERGE_WINDOW_MIN)).fetchone()
        merged = row is not None
    if row is None:
        row = conn.execute(
            "SELECT id FROM diag_events WHERE stage=? AND severity=? AND COALESCE(code,'')=? AND message=?"
            " AND COALESCE(project_id,0)=? AND (julianday('now') - julianday(last_at)) * 1440 < 10 ORDER BY id DESC LIMIT 1",
            (stage, severity, code or "", msg, project_id or 0)).fetchone()
    now = _now()
    if row and merged:
        conn.execute("UPDATE diag_events SET count=count+1, last_at=?, message=? WHERE id=?", (now, msg, row["id"]))
    elif row:
        conn.execute("UPDATE diag_events SET count=count+1, last_at=? WHERE id=?", (now, row["id"]))
    else:
        conn.execute("INSERT INTO diag_events (at, last_at, stage, severity, code, message, project_id, scene_id, job_id)"
                     " VALUES (?,?,?,?,?,?,?,?,?)", (now, now, stage, severity, code, msg, project_id, scene_id, job_id))
    conn.commit()


def recent(conn, hours: float = 24, limit: int = 40) -> List[Dict]:
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec="seconds")
    return [dict(r) for r in conn.execute(f"SELECT * FROM diag_events WHERE last_at>=? AND {_NOT_OBSERVE} ORDER BY last_at DESC, id DESC "
                                          "LIMIT ?", (since, limit)).fetchall()]


def repeated(conn, hours: float = 24, min_count: int = 3) -> List[Dict]:
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec="seconds")
    return [dict(r) for r in conn.execute(
        "SELECT stage, severity, code, message, SUM(count) n, MIN(at) first_at, MAX(last_at) last_at FROM diag_events"
        f" WHERE last_at>=? AND {_NOT_OBSERVE} GROUP BY stage, severity, code, message HAVING n>=? ORDER BY n DESC LIMIT 15",
        (since, min_count)).fetchall()]


# ---- silent problems --------------------------------------------------------------------------
def _minutes_since(iso: Optional[str]) -> Optional[float]:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds() / 60


def scan(conn, data_dir: str, poll_sec: float = 15) -> List[Dict]:
    """Things that are wrong although nothing raised an error. Each: {severity, stage, title, detail, project_id}."""
    out: List[Dict] = []

    def add(severity, stage, title, detail, project_id=None):
        out.append({"severity": severity, "stage": stage, "title": title, "detail": detail, "project_id": project_id})

    stage_of = {"image_gen": "image", "video_gen": "video"}
    for j in conn.execute("SELECT id, project_id, scene_id, type, state, updated_at, created_at, external_id FROM jobs"
                          " WHERE type IN ('image_gen','video_gen') AND state IN ('running','queued','retryable')").fetchall():
        age = _minutes_since(j["updated_at"] or j["created_at"])
        if age is None:
            continue
        if j["state"] == "running" and age > STUCK_MIN[j["type"]]:
            add("error", stage_of[j["type"]], f"Job #{j['id']} chạy {age:.0f} phút không có tiến triển",
                f"Quá ngưỡng {STUCK_MIN[j['type']]} phút (DIAG_STUCK_*). Có thể nhà cung cấp treo hoặc không ai đang poll.", j["project_id"])
        elif j["state"] in ("queued", "retryable") and age > QUEUED_MIN:
            add("warn", stage_of[j["type"]], f"Job #{j['id']} nằm chờ {age:.0f} phút chưa được gửi",
                "Có thể đang bị giới hạn song song/429, dự án đã dừng, hoặc thiếu đầu vào.", j["project_id"])
    for j in conn.execute("SELECT id, project_id, type, result_path FROM jobs WHERE type IN ('image_gen','video_gen')"
                          " AND state IN ('succeeded','pending_review','approved')").fetchall():
        path = j["result_path"]
        if not path or not os.path.exists(path):
            add("error", stage_of[j["type"]], f"Job #{j['id']} báo xong nhưng không có file kết quả",
                f"result_path={'(trống)' if not path else 'không tồn tại'}", j["project_id"])
        elif os.path.getsize(path) == 0:
            add("error", stage_of[j["type"]], f"Job #{j['id']} có file rỗng (0 byte)", "", j["project_id"])
    for r in conn.execute("SELECT id, name, autopilot_state, autopilot_beat FROM projects WHERE autopilot_state='running'").fetchall():
        if r["autopilot_beat"] is None or time.time() - r["autopilot_beat"] > max(poll_sec * 4, 60):
            add("error", "autopilot", f"Dự án #{r['id']} {r['name']}: báo đang chạy nhưng không có tiến trình nào tick",
                "Máy chủ khởi động lại hoặc luồng nền chết. Bấm Tiếp tục.", r["id"])
    for r in conn.execute("SELECT s.project_id, s.idx FROM scenes s WHERE s.state='needs_attention'").fetchall():
        add("warn", "autopilot", f"Cảnh S{r['idx']:02d} (dự án #{r['project_id']}) đang chờ người xử lý", "", r["project_id"])
    for kind, stage in (("image_gen", "image"), ("video_gen", "video")):
        total = conn.execute("SELECT COUNT(*) FROM jobs WHERE type=? AND created_at>=?", (kind, _hours_ago(24))).fetchone()[0]
        retried = conn.execute("SELECT COUNT(*) FROM jobs WHERE type=? AND created_at>=? AND parent_job_id IS NOT NULL",
                               (kind, _hours_ago(24))).fetchone()[0]
        if total >= 5 and retried / total >= RETRY_WARN:
            add("warn", stage, f"{retried}/{total} job trong 24h là gen lại",
                "Tỉ lệ gen lại cao = tốn credit và quy trình chưa trơn. Xem lý do lỗi ở bảng sự kiện.")
    moderation = conn.execute("SELECT COUNT(*) FROM content_moderation_failures WHERE at>=?", (_hours_ago(24),)).fetchone()[0]
    if moderation:
        add("warn", "video", f"{moderation} lần bị risk control chặn trong 24h", "Xem góc Rủi ro, đổi prompt (bớt từ nhạy cảm) hoặc đổi model.")
    for r in conn.execute("SELECT id, name FROM projects WHERE autopilot_state='done'").fetchall():
        if not os.path.exists(os.path.join(data_dir, str(r["id"]), "output", "FINAL_VIDEO.mp4")):
            add("error", "render", f"Dự án #{r['id']} báo Hoàn tất nhưng không có FINAL_VIDEO.mp4", "", r["id"])
    for row in repeated(conn, 24, 3):
        add("warn" if row["severity"] != "error" else "error", row["stage"], f"Lặp lại {row['n']} lần: {row['message'][:120]}",
            f"code={row['code'] or '-'}, từ {row['first_at']} đến {row['last_at']}")
    order = {"error": 0, "warn": 1, "info": 2}
    return sorted(out, key=lambda f: order.get(f["severity"], 3))


def _hours_ago(h: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=h)).isoformat(timespec="seconds")


# ---- per stage table ---------------------------------------------------------------------------
def stage_table(conn, hours: float = 24) -> List[Dict]:
    since = _hours_ago(hours)
    rows = []
    by_stage: Dict[str, Dict[str, int]] = {}
    known = {s for s, _ in STAGES}
    for r in conn.execute(f"SELECT stage, severity, SUM(count) n FROM diag_events WHERE last_at>=? AND {_NOT_OBSERVE} "
                          "GROUP BY stage, severity", (since,)).fetchall():
        name = normalize_stage(r["stage"])                      # rows written before S14.4 under 'videos' / 'delivery' …
        name = name if name in known else OTHER
        bucket = by_stage.setdefault(name, {s: 0 for s in SEVERITIES})
        bucket[r["severity"]] = bucket.get(r["severity"], 0) + (r["n"] or 0)
    extra = ((OTHER, STAGE_LABEL[OTHER]),) if OTHER in by_stage else ()      # 'Khác' only when something landed there
    for stage, label in STAGES + extra:
        counts = by_stage.get(stage, {s: 0 for s in SEVERITIES})
        item = {"stage": stage, "label": label, "info": counts["info"], "warn": counts["warn"], "error": counts["error"],
                "jobs": None, "ok": None, "failed": None, "retried": None}
        kind = {"image": "image_gen", "video": "video_gen"}.get(stage)
        if kind:
            q = lambda extra="": conn.execute(  # noqa: E731
                "SELECT COUNT(*) FROM jobs WHERE type=? AND created_at>=? " + extra, (kind, since)).fetchone()[0]
            item.update(jobs=q(), ok=q("AND state IN ('succeeded','pending_review','approved')"), failed=q("AND state='failed'"),
                        retried=q("AND parent_job_id IS NOT NULL"))
        rows.append(item)
    return rows


def health(item: Dict) -> str:
    if item["error"] or (item["failed"] or 0):
        return "🔴"
    if item["warn"]:
        return "🟡"
    return "🟢"


# ---- the report to paste into the chat ---------------------------------------------------------
def report(conn, data_dir: str, extra: Optional[Dict] = None, hours: float = 24) -> str:
    lines = [f"# Báo cáo chẩn đoán — {datetime.now().strftime('%Y-%m-%d %H:%M')} (cửa sổ {hours:g}h)", ""]
    env = {k: ("đã đặt" if os.environ.get(k) else "chưa đặt") for k in ("CLIPAI_TOKEN", "DEEPIX_TOKEN", "ANTHROPIC_API_KEY", "MESHY_API_KEY")}
    plain = {k: os.environ.get(k) or "-" for k in ("IMAGE_PROVIDER", "VIDEO_PROVIDER", "AUDIO_PROVIDER", "LLM_PROVIDER",
                                                    "AUTOPILOT_MAX_PARALLEL", "THROTTLE_START")}
    lines += ["## Cấu hình (không có giá trị bí mật)", "- Khóa: " + ", ".join(f"{k}: {v}" for k, v in env.items()),
              "- " + ", ".join(f"{k}={v}" for k, v in plain.items())]
    for k, v in (extra or {}).items():
        lines.append(f"- {k}: {v}")
    lines += ["", "## Từng khâu", "| Khâu | Tình trạng | Job | Xong | Lỗi | Gen lại | Cảnh báo | Lỗi ghi nhận |", "|---|---|---|---|---|---|---|---|"]
    dash = lambda v: "-" if v is None else v  # noqa: E731
    for s in stage_table(conn, hours):
        lines.append(f"| {s['label']} | {health(s)} | {dash(s['jobs'])} | {dash(s['ok'])} | {dash(s['failed'])} | "
                     f"{dash(s['retried'])} | {s['warn']} | {s['error']} |")
    findings = scan(conn, data_dir)
    lines += ["", f"## Vấn đề phát hiện ({len(findings)})"]
    lines += [f"- [{f['severity']}] ({STAGE_LABEL.get(f['stage'], f['stage'])}) {redact(f['title'])}"
              + (f" — {redact(f['detail'])}" if f["detail"] else "") for f in findings] or ["- Không thấy vấn đề âm thầm."]
    lines += ["", "## Sự kiện gần đây (mới nhất trước; x = số lần lặp)"]
    for e in recent(conn, hours, 40):
        lines.append(f"- {e['last_at'][11:19]} [{e['severity']}] {e['stage']}"
                     f"{'/' + e['code'] if e['code'] else ''} x{e['count']}"
                     f"{' P#' + str(e['project_id']) if e['project_id'] else ''}: {e['message']}")
    if lines[-1].startswith("## "):
        lines.append("- (chưa có)")
    lines += ["", "## Dự án chạy tự động"]
    for r in conn.execute("SELECT id, name, autopilot_state st, autopilot_note note, autopilot_log lg FROM projects"
                          " WHERE autopilot_state IS NOT NULL ORDER BY id DESC LIMIT 10").fetchall():
        lines.append(f"- #{r['id']} {redact(r['name'])}: {r['st']} — {redact(r['note'] or '')}")
    return "\n".join(lines) + "\n"
