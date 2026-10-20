"""V3.1 M1.4b (D02 `v31-d02-claude-provider-per-project-2026-10-20`, gói Cấp 2 G2-2 người dùng duyệt 20/10): nhà cung cấp Claude THEO DỰ ÁN.

  - `projects.llm_provider` rỗng / NULL / cột chưa có = theo môi trường (`LLM_PROVIDER` — hành vi cũ, M1.4a: không khai thì không có client,
    có key mà không khai KHÔNG tự dùng API trả phí).
  - Tạo job → chụp `jobs.llm_provider` + `jobs.llm_config_ver` (provider thực tế + phiên bản cấu hình KHÔNG chứa bí mật). Job đã chụp giữ
    provider đó dù Dashboard / dashboard.env đổi sau; job cũ chưa có ảnh chụp (NULL) đi theo dự án / môi trường như trước.
  - Hết lượt gói (`usage_limit`) / hết tiền (`out_of_credit`) của một provider → ghi `app_settings['llm_quota']` kèm giờ mở lại (nếu Claude
    Code nói "resets …"); mọi lời gọi provider đó bị từ chối có lý do + giờ mở cho tới khi qua giờ mở / người mở lại. Không bao giờ tự chuyển
    sang provider khác (0 lời gọi API trả phí).
Các cột là migration Cấp 3 (C3-1, phiên chính sau backup): `core/db.migrate_llm_provider_up/down` — KHÔNG tự chạy khi mở CSDL. Thiếu cột →
mọi hàm ở đây chạy như cũ (đọc env, không chụp)."""
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

PROVIDERS = ("anthropic", "claude_cli", "mock")
QUOTA_KEY = "llm_quota"
QUOTA_CODES = ("usage_limit", "out_of_credit")
# không bí mật: chỉ những gì đổi cách gọi (model, endpoint) — KHÔNG có key / token
CONFIG_ENV = ("CLAUDE_CLI_MODEL", "ANTHROPIC_MODEL", "ANTHROPIC_API_BASE")


def normalize(kind) -> Optional[str]:
    k = str(kind or "").strip().lower()
    if k in ("claude_cli", "claude-cli", "cli"):
        return "claude_cli"
    return k if k in ("anthropic", "mock") else None


def env_provider() -> Optional[str]:
    return normalize(os.environ.get("LLM_PROVIDER"))


def config_version(kind: Optional[str]) -> Optional[str]:
    """Dấu vân tay cấu hình của provider (không chứa key) — ghi vào job để biết job chạy bằng cấu hình nào."""
    if kind is None:
        return None
    parts = [kind] + [f"{k}={os.environ.get(k, '').strip()}" for k in CONFIG_ENV]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]


_COLS: Dict[Tuple[str, str, str], bool] = {}


def _db_file(conn) -> Optional[str]:
    return next((r[2] for r in conn.execute("PRAGMA database_list") if r[1] == "main"), "") or None


def has_column(conn, table: str, column: str) -> bool:
    key = (str(_db_file(conn) or id(conn)), table, column)
    if key not in _COLS:
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        if column not in cols:
            return False                     # chưa có: không nhớ — migration có thể chạy giữa chừng
        _COLS[key] = True
    return _COLS[key]


def project_provider(conn, project_id: Optional[int]) -> Optional[str]:
    """Provider khai riêng cho dự án (None = theo môi trường / cột chưa có). Giá trị sai → None + lý do ở `resolve`."""
    if project_id is None or not has_column(conn, "projects", "llm_provider"):
        return None
    row = conn.execute("SELECT llm_provider FROM projects WHERE id=?", (project_id,)).fetchone()
    if row is None:
        return None
    return (row[0] or "").strip() or None


def resolve(conn, project_id: Optional[int]) -> Tuple[Optional[str], str]:
    """(provider hoặc None, nguồn / lý do): 'project' khi dự án khai, 'env' khi theo môi trường."""
    raw = project_provider(conn, project_id)
    if raw is not None:
        kind = normalize(raw)
        return (kind, "project") if kind else (None, f"dự án #{project_id} khai llm_provider={raw!r} không hợp lệ (anthropic | claude_cli | mock)")
    kind = env_provider()
    if kind:
        return kind, "env"
    from .llm_runner import provider_status
    return None, provider_status()[1]


def set_project_provider(conn, project_id: int, kind: Optional[str]) -> None:
    """Đặt / bỏ (None) provider của dự án. Job đã tạo giữ provider đã chụp."""
    if not has_column(conn, "projects", "llm_provider"):
        raise ValueError("CSDL chưa có cột projects.llm_provider — chạy migration M1.4b (core.db.migrate_llm_provider_up) sau khi sao lưu")
    if kind is not None and normalize(kind) is None:
        raise ValueError(f"llm_provider {kind!r} không hợp lệ (anthropic | claude_cli | mock)")
    conn.execute("UPDATE projects SET llm_provider=? WHERE id=?", (normalize(kind) if kind else None, project_id))
    conn.commit()


def snapshot_job(conn, job_id: int, parent_job_id: Optional[int] = None) -> Optional[str]:
    """Chụp provider + phiên bản cấu hình lúc tạo job (chỉ khi cột có và job chưa chụp). Job gen lại (có cha đã chụp) giữ provider của
    cha — cùng một việc không đổi provider giữa chừng. Không có provider → để NULL (không bịa)."""
    if not (has_column(conn, "jobs", "llm_provider") and has_column(conn, "jobs", "llm_config_ver")):
        return None
    row = conn.execute("SELECT project_id, llm_provider FROM jobs WHERE id=?", (job_id,)).fetchone()
    if row is None or row[1]:
        return row[1] if row else None
    kind, ver = None, None
    if parent_job_id is not None:
        par = conn.execute("SELECT llm_provider, llm_config_ver FROM jobs WHERE id=?", (parent_job_id,)).fetchone()
        if par is not None and normalize(par[0]):
            kind, ver = normalize(par[0]), par[1]
    if kind is None:
        kind, _ = resolve(conn, row[0])
        ver = config_version(kind)
    if kind:
        conn.execute("UPDATE jobs SET llm_provider=?, llm_config_ver=? WHERE id=? AND llm_provider IS NULL", (kind, ver, job_id))
    return kind


def job_provider(conn, job) -> Tuple[Optional[str], str]:
    """(provider, nguồn) cho một job: ảnh chụp lúc tạo ('job') nếu có, không thì như dự án."""
    row = job if hasattr(job, "keys") else conn.execute("SELECT * FROM jobs WHERE id=?", (int(job),)).fetchone()
    if row is None:
        return None, f"không có job {job}"
    snap = row["llm_provider"] if "llm_provider" in row.keys() else None
    if snap:
        kind = normalize(snap)
        return (kind, "job") if kind else (None, f"job #{row['id']} chụp llm_provider={snap!r} không hợp lệ")
    return resolve(conn, row["project_id"])


def _client(kind: Optional[str], ledger: Optional[str], transport=None):
    from . import llm_runner
    if kind is None:
        return None
    if kind == env_provider():                   # cùng provider với môi trường: đi đúng cửa cũ (client_from_env) như trước M1.4b
        return llm_runner.client_from_env(transport or llm_runner.urllib_transport, ledger=ledger)
    return llm_runner.client_for_provider(kind, transport or llm_runner.urllib_transport, ledger=ledger)


def client_for_project(conn, project_id: Optional[int], transport=None, ledger: Optional[str] = None):
    """Client Claude của dự án (ledger = CSDL này). Dự án không khai → `client_from_env` y như trước M1.4b (None / LlmError như cũ);
    dự án khai sai → None (nơi gọi báo `missing_hint_for`)."""
    from . import llm_runner
    ledger = ledger or llm_runner.db_file(conn)
    raw = project_provider(conn, project_id)
    if raw is None:
        return llm_runner.client_from_env(transport or llm_runner.urllib_transport, ledger=ledger)
    return _client(normalize(raw), ledger, transport)


def client_for_job(conn, job, transport=None, ledger: Optional[str] = None):
    """Client Claude cho việc của MỘT job: giữ provider đã chụp lúc tạo job dù cấu hình đổi; chưa chụp → như dự án."""
    from . import llm_runner
    row = job if hasattr(job, "keys") else conn.execute("SELECT * FROM jobs WHERE id=?", (int(job),)).fetchone()
    if row is None:
        return None
    snap = row["llm_provider"] if "llm_provider" in row.keys() else None
    if snap:
        return _client(normalize(snap), ledger or llm_runner.db_file(conn), transport)
    return client_for_project(conn, row["project_id"], transport, ledger)


def project_factory(db_path: Optional[str], project_id: Optional[int]):
    """Nhà máy client cho luồng nền (autoqc, đọc ảnh Kho…): mỗi lần gọi đọc lại provider của dự án từ CSDL."""
    def make():
        from .db import connect
        if not db_path:
            from . import llm_runner
            return llm_runner.client_from_env(ledger=None)        # CSDL trong bộ nhớ: như ledger_factory(None) trước M1.4b
        conn = connect(db_path)
        try:
            return client_for_project(conn, project_id, ledger=db_path)
        finally:
            conn.close()
    return make


class JobClients:
    """Mỗi provider một client trong một lượt (QC video từng job): job chụp provider khác dự án vẫn chạy đúng provider của nó."""

    def __init__(self, conn, ledger: Optional[str] = None):
        self.conn, self.ledger, self._by = conn, ledger, {}

    def for_job(self, job):
        kind, why = job_provider(self.conn, job)
        if kind not in self._by:
            self._by[kind] = client_for_job(self.conn, job, ledger=self.ledger)
        if self._by[kind] is None:               # rà C-RA-M14B: nói rõ (mã config = dừng lượt), không đưa None cho nơi gọi rồi hỏng từng job
            from .llm_runner import LlmError, missing_hint
            raise LlmError(f"không dựng được Claude cho job {job if not hasattr(job, 'keys') else job['id']}: "
                           + (why if kind is None else missing_hint()), code="config")
        return self._by[kind]

    def or_default(self, default):
        """job_id → Claude của job: ảnh chụp lúc tạo nếu có, không thì `default` (client dự án / ngữ cảnh đang chạy — job cũ NULL như
        trước M1.4b). Dùng cho QC hàng loạt (rà C-RA-M14B)."""
        def pick(job):
            row = job if hasattr(job, "keys") else self.conn.execute("SELECT * FROM jobs WHERE id=?", (int(job),)).fetchone()
            if row is None or "llm_provider" not in row.keys() or not row["llm_provider"]:
                return default
            return self.for_job(row)
        return pick


def missing_hint_for(conn, project_id: Optional[int]) -> str:
    kind, why = resolve(conn, project_id)
    if kind is None:
        return why
    from .llm_runner import missing_hint
    return missing_hint()


# ---- hết lượt / hết tiền: dừng có giờ mở lại ------------------------------------------------------------------------------------
# rà C-RA-M14B: "resets Oct 21, 4am" (giới hạn tuần) cũng đọc giờ — ngày bị bỏ qua: mở lại sớm hơn chỉ tốn MỘT lời gọi thử (0 USD API)
_RESET = re.compile(r"resets?\s+(?:at\s+)?(?:[A-Za-z]{3,9}\.?\s+\d{1,2},?\s+(?:at\s+)?)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?"
                    r"(?:\s*\(([A-Za-z_]+/[A-Za-z_]+)\))?", re.I)
# rà C-RA-M14B (CAO-1): không đọc được giờ mở lại → trước đây dừng VĨNH VIỄN (không nơi nào mở lại). Nay: sau PROBE_MINUTES cho đi MỘT lời
# gọi thử (claude_cli = 0 USD API); còn hết lượt thì CLI báo lại và dấu dừng ghi lại. Người có quyền mở lại ngay ở 💵 Tiền (dashboard/header).
PROBE_MINUTES = 60


def reset_at(message: str, now: Optional[datetime] = None) -> Optional[str]:
    """Giờ mở lại (UTC ISO) đọc từ lời Claude Code ('… resets 4:20am (Asia/Saigon)'); không đọc được → None (KHÔNG đoán)."""
    m = _RESET.search(str(message or ""))
    if not m:
        return None
    hour, minute, ampm, zone = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower(), m.group(4)
    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    tz = None
    if zone:
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(zone)
        except Exception:  # noqa: BLE001 - unknown zone name: the machine's local time
            tz = None
    now = now or datetime.now(timezone.utc)
    local = now.astimezone(tz) if tz else now.astimezone()
    at = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if at <= local:
        at += timedelta(days=1)
    return at.astimezone(timezone.utc).isoformat(timespec="seconds")


def _quota(conn) -> Dict:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (QUOTA_KEY,)).fetchone()
    try:
        return json.loads(row[0]) if row and row[0] else {}
    except ValueError:
        return {}


def _save_quota(conn, data: Dict) -> None:
    conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (QUOTA_KEY, json.dumps(data, ensure_ascii=False)))
    conn.commit()


def quota_halt(conn, provider: str, code: str, message: str, now: Optional[datetime] = None) -> Dict:
    data = _quota(conn)
    rec = {"code": code, "at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
           "reset_at": reset_at(message, now), "message": str(message)[:300]}
    data[provider] = rec
    _save_quota(conn, data)
    return rec


def quota_reopen(conn, provider: str) -> None:
    data = _quota(conn)
    if data.pop(provider, None) is not None:
        _save_quota(conn, data)


def quota_all(conn) -> Dict:
    """{provider: dấu dừng} đang ghi (kể cả đã qua giờ mở mà chưa ai gọi lại) — cho thẻ 💵 Tiền hiện + nút mở lại."""
    return _quota(conn)


def quota_halted(conn, provider: str, now: Optional[datetime] = None) -> Optional[Tuple[str, str]]:
    """(mã, lý do có giờ mở) khi provider đang dừng; qua giờ mở lại → tự mở (xóa dấu dừng) và trả None."""
    rec = _quota(conn).get(provider)
    if not rec:
        return None
    now = now or datetime.now(timezone.utc)
    vn = timezone(timedelta(hours=7))
    try:
        until = datetime.fromisoformat(rec["reset_at"]) if rec.get("reset_at") else \
            datetime.fromisoformat(rec["at"]) + timedelta(minutes=PROBE_MINUTES)
    except (KeyError, TypeError, ValueError):
        until = None                             # dấu dừng hỏng: vẫn dừng, người mở lại tay
    if until is not None and now >= until:
        quota_reopen(conn, provider)
        return None
    if rec.get("reset_at"):
        opens = f"mở lại lúc {until.astimezone(vn):%d/%m %H:%M} (giờ VN)"
    else:
        opens = ("chưa đọc được giờ mở lại — " + (f"tự thử lại 1 lời gọi lúc {until.astimezone(vn):%d/%m %H:%M} (giờ VN), " if until else "")
                 + "hoặc người có quyền mở lại ở 💵 Tiền khi gói / tài khoản dùng được")
    what = "hết lượt gói" if rec["code"] == "usage_limit" else "hết tiền"
    return rec["code"], (f"⛔ Claude ({provider}) {what} từ {rec['at']} — đã dừng mọi lời gọi tới provider này, KHÔNG tự chuyển sang "
                         f"provider khác; {opens}. Lời gốc: {rec['message'][:160]}")
