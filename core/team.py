"""Nhiều người dùng chung một Dashboard (đợt 3, 01/10): vai dựng sẵn, tiền chi theo người, hạn mức cá nhân, ai đang mở dự án.

- VAI: bộ quyền dựng sẵn trên 5 quyền sẵn có của core/auth.py (không thêm quyền mới): Người làm / Người duyệt / Quản lý. Một bộ quyền
  tick lẻ không trùng vai nào là "Tùy chỉnh". Owner luôn là Owner.
- TIỀN THEO NGƯỜI: tổng USD ảnh + video (+ nhạc/giọng nếu có giá) của các job do người đó gửi (jobs.created_by), theo bảng giá. Tiền gọi
  Claude không gắn với người (usage_events không ghi job) nên không nằm ở đây.
- HẠN MỨC CÁ NHÂN (USD / tháng) chỉ là CẢNH BÁO: hiện % ở màn Nhóm và báo Owner ở hộp "Việc cần bạn" khi ≥ 90 %. KHÔNG chặn gửi — chặn
  thật vẫn là trần đợt thử + ngân sách khóa của dự án (core/budget.py, core/project_budget.py).
- ĐANG MỞ: mỗi lần một người mở một dự án, ghi (dự án → e-mail, giờ); người khác thấy 🔒 trong 2 phút để không duyệt chồng nhau. Chỉ báo,
  không khóa.
"""
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

ROLES = {
    "worker": {"label": "Người làm", "perms": [],
               "desc": "Làm video, chạy tự động, duyệt dự án của mình. Xem tiền của mình."},
    "reviewer": {"label": "Người duyệt", "perms": ["assets", "lessons"],
                 "desc": "Như Người làm + Kho tài nguyên, Bài học (duyệt ảnh nhập vào Kho, ghi bài học)."},
    "manager": {"label": "Quản lý", "perms": ["settings", "knowledge", "monitor", "lessons", "assets"],
                "desc": "Như Người duyệt + Theo dõi, Bảng giá / Tính năng thử, Kho kiến thức. Không quản lý người dùng."},
}
NO_NAME = "(chưa nhập tên)"           # same label as core/perf.by_user, so a nameless job keeps its money
LIMIT_WARN = 0.9
PRESENCE_SECONDS = 120


def role_of(perms: List[str]) -> str:
    """'worker' | 'reviewer' | 'manager' | 'custom' for a set of permissions."""
    have = set(perms or [])
    for key, r in ROLES.items():
        if have == set(r["perms"]):
            return key
    return "custom"


def role_label(user: Dict) -> str:
    if user.get("role") == "owner":
        return "Owner"
    key = role_of(user.get("perms") or [])
    return ROLES[key]["label"] if key in ROLES else "Tùy chỉnh"


def perms_for(role_key: str) -> List[str]:
    return list(ROLES[role_key]["perms"])


# ---- tiền theo người ------------------------------------------------------------------------------------------------------------
def _since(days: Optional[float]) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S") if days else "0000"


def _baseline_key(email: str) -> str:
    return "user_reset:" + (email or "").strip().lower()


def user_baseline(conn, email: str) -> Optional[str]:
    """The time (UTC, same text format as usage_events.at) the Owner reset this person's money bar, or None. The ledger is untouched."""
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (_baseline_key(email),)).fetchone()
    v = str(row[0]).strip().replace("T", " ")[:19] if row and row[0] else ""
    return v or None


def spend_by_user(conn, days: Optional[float] = None, since_baseline: bool = False) -> Dict[str, float]:
    """{e-mail or name: USD} of the jobs each person sent (image / video / priced audio), by the price table.
    `since_baseline`: count each person only from their reset point (the person's bar); the default is the whole ledger."""
    from . import budget, cost
    pricing = cost.load_pricing()
    since = _since(days)
    out: Dict[str, float] = {}
    bases: Dict[str, Optional[str]] = {}
    for r in conn.execute(
            "SELECT u.*, COALESCE(NULLIF(TRIM(j.created_by), ''), '') AS who FROM usage_events u JOIN jobs j ON j.id=u.job_id"
            " WHERE u.provider NOT LIKE 'mock%' AND j.created_at>=?", (since,)).fetchall():
        usd = budget.row_usd(pricing, r)
        if usd:
            who = r["who"] or NO_NAME
            if since_baseline:
                if who not in bases:
                    bases[who] = user_baseline(conn, who) if who != NO_NAME else None
                if bases[who] and str(r["at"] or "").replace("T", " ") < bases[who]:
                    continue
            out[who] = round(out.get(who, 0.0) + usd, 4)
    return out


# ---- hạn mức cá nhân (cảnh báo) -------------------------------------------------------------------------------------------------
def _limit_key(email: str) -> str:
    return "user_limit:" + (email or "").strip().lower()


def get_limit(conn, email: str) -> Optional[float]:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (_limit_key(email),)).fetchone()
    try:
        v = float(row[0]) if row else None
    except (TypeError, ValueError):
        v = None
    return v if v and v > 0 else None


def set_limit(conn, email: str, usd: Optional[float]) -> None:
    if not usd or float(usd) <= 0:
        conn.execute("DELETE FROM app_settings WHERE key=?", (_limit_key(email),))
    else:
        conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                     (_limit_key(email), str(float(usd))))
    conn.commit()


def month_spend(conn, email: str) -> float:
    """The last 30 days, counted from the person's reset point when the Owner set one (team.user_baseline)."""
    return spend_by_user(conn, 30, since_baseline=True).get((email or "").strip(), 0.0)


def limit_status(conn, email: str) -> Optional[Dict]:
    """{"limit", "spent", "share"} or None when the person has no limit."""
    lim = get_limit(conn, email)
    if lim is None:
        return None
    spent = month_spend(conn, email)
    return {"limit": lim, "spent": spent, "share": spent / lim}


# ---- ai đang mở dự án -----------------------------------------------------------------------------------------------------------
def touch(conn, project_id: int, email: Optional[str], now: Optional[float] = None) -> None:
    """Remember that `email` has this project open now (write at most every 30 s per person and project)."""
    if not email:
        return
    key = f"presence:{int(project_id)}"
    now = time.time() if now is None else now
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    try:
        data = json.loads(row[0]) if row else {}
    except ValueError:
        data = {}
    if now - float((data.get(email) or 0)) < 30:
        return
    data = {k: v for k, v in data.items() if now - float(v) < 3600}
    data[email] = now
    conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (key, json.dumps(data)))
    conn.commit()


def open_by(conn, project_id: int, exclude: Optional[str] = None, now: Optional[float] = None) -> List[str]:
    """Other people who had this project open in the last 2 minutes."""
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (f"presence:{int(project_id)}",)).fetchone()
    try:
        data = json.loads(row[0]) if row else {}
    except ValueError:
        return []
    now = time.time() if now is None else now
    return sorted(k for k, v in data.items() if k != exclude and now - float(v) <= PRESENCE_SECONDS)
