"""S14.18 — giới hạn theo NGƯỜI (kế hoạch nâng cấp dashboard 2026-10-03, mục 6d; người dùng chốt 04/10).

Nhận diện người = e-mail đăng nhập (Pipeline.user; máy LAN đã duyệt ở core/machine_auth). Kiểm ở LÕI: Pipeline.create_project,
compare.clone_project, archive.archive / restore / swap gọi vào đây, nên mọi đường tạo / cất dự án của người đã đăng nhập đều bị chặn.
Script dòng lệnh / chạy nền (Pipeline.user = None) và Owner KHÔNG bị giới hạn.

Ba mức cơ bản (Owner nâng riêng cho từng người ở 👥 Nhóm, lưu app_settings 'person_limits:<email>'):
  open   = 2  dự án DỞ cùng lúc (dở = chưa XUẤT BẢN GIAO — S14.30 core/delivered; đã cất 📦 hoặc đã xóa không tính)
  daily  = 2  dự án tạo mới trong một ngày (ngày theo giờ máy chạy Dashboard; xóa dự án không trả lại lượt). Thứ 3 trở đi: gửi yêu cầu
              kèm lý do → Owner duyệt / từ chối ở 👥 Nhóm (📥 của Owner báo có yêu cầu) → một lần duyệt = một dự án, trong ngày duyệt.
  parked = 1  dự án DỞ đang cất 📦. Dự án ĐÃ XONG cất vào "Kho dự án đã xong" — không giới hạn, không tính vào `open`.
Mỗi lần chặn: LimitReached (một AccessDenied) với câu tiếng Việt có số liệu + danh sách dự án liên quan (tên, bước, đã chi ước tính),
ghi nhật ký audit 'limit_block'. Trần job/ngày chung cả máy (AUTOPILOT_DAILY_JOBS) đã bỏ cùng việc này.
"""
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional

from . import access, auth

BASE = {"open": 2, "daily": 2, "parked": 1}
LABELS = {"open": "Dự án dở cùng lúc", "daily": "Dự án tạo mới / ngày", "parked": "Dự án dở đang cất 📦"}
KIND_LABELS = {"daily": "thêm 1 dự án mới hôm nay", "parked": "cất thêm 1 dự án dở"}
STATUS_LABELS = {"pending": "⏳ chờ duyệt", "approved": "✅ đã duyệt (chưa dùng)", "rejected": "⛔ từ chối", "used": "✔ đã dùng"}
LOCK = threading.RLock()
"""Rà 05/10: check + write of a creation / a 📦 move is ONE step in this process (the Dashboard is one process; two clicks at once must not
both pass the check nor use one approval twice). Callers hold it around check → write → commit."""


class LimitReached(access.AccessDenied):
    """A per-person limit refused the action. `str(e)` = the sentence with the numbers; `kind` 'open' | 'daily' | 'parked';
    `projects` = the rows that fill the limit ({id, name, step, spent, archived}); `pending` = the person's waiting request id."""

    def __init__(self, kind: str, message: str, projects: List[Dict], used: int, limit: int, pending: Optional[int] = None):
        super().__init__(message)
        self.kind, self.projects, self.used, self.limit, self.pending = kind, projects, used, limit, pending


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _email(who) -> str:
    if who is None:
        return ""
    if isinstance(who, str):
        return who.strip().lower()
    get = who.get if isinstance(who, dict) else (lambda k, d=None: getattr(who, k, d))
    return (get("email") or "").strip().lower()


def _role(who) -> Optional[str]:
    if who is None or isinstance(who, str):
        return None
    return who.get("role") if isinstance(who, dict) else getattr(who, "role", None)


def exempt(user) -> bool:
    """No signed-in person (script, background run, sign-in off) or the Owner: no limit."""
    return user is None or _role(user) == "owner" or not _email(user)


def _need_owner(actor) -> str:
    if _role(actor) != "owner":
        raise auth.AuthError("Chỉ Owner được duyệt yêu cầu / đổi giới hạn dự án của từng người.")
    return _email(actor)


# ---- mức của từng người ---------------------------------------------------------------------------------------------------------------
def _key(email: str) -> str:
    return f"person_limits:{email.strip().lower()}"


def limits(conn, email: str) -> Dict[str, int]:
    """The person's three limits: BASE with the Owner's raises on top."""
    out = dict(BASE)
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (_key(email),)).fetchone()
    if row:
        try:
            out.update({k: int(v) for k, v in json.loads(row["value"] or "{}").items() if k in BASE and v is not None})
        except (ValueError, TypeError):
            pass
    return out


def overrides(conn, email: str) -> Dict[str, int]:
    """Only what the Owner changed (empty = the base limits)."""
    return {k: v for k, v in limits(conn, email).items() if v != BASE[k]}


def set_limits(conn, actor, email: str, open: Optional[int] = None, daily: Optional[int] = None, parked: Optional[int] = None) -> Dict:
    """Owner: set one person's limits (None = keep; a value equal to the base drops the raise). Written to the audit log."""
    who = _need_owner(actor)
    email = auth.normalize_email(email)
    cur = limits(conn, email)
    for k, v in (("open", open), ("daily", daily), ("parked", parked)):
        if v is not None:
            if int(v) < 0:
                raise ValueError(f"{LABELS[k]}: không được âm")
            cur[k] = int(v)
    diff = {k: v for k, v in cur.items() if v != BASE[k]}
    if diff:
        conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                     (_key(email), json.dumps(diff)))
    else:
        conn.execute("DELETE FROM app_settings WHERE key=?", (_key(email),))
    conn.commit()
    auth.audit(conn, who, "limit_set", f"{email}: " + ", ".join(f"{k}={cur[k]}" for k in BASE) + " (cơ bản 2/2/1)")
    return cur


# ---- đếm ------------------------------------------------------------------------------------------------------------------------------
def is_finished(conn, project_id: int, data_dir: Optional[str] = None) -> bool:
    """'Hoàn thiện' = the delivery was EXPORTED (S14.30, người dùng chốt 05/10): core/delivered — one answer for the limits, the
    "Kho dự án đã xong" and 📥. A final cut alone (outputs 'final' / FINAL_VIDEO.mp4) is NOT finished any more. `data_dir` is kept
    for callers; it is not needed now."""
    from . import delivered
    return delivered.is_delivered(conn, project_id)


def _describe(conn, r) -> Dict:
    from . import perf
    spent = 0.0
    try:
        from . import project_budget
        spent = round(sum(project_budget.spent_by_stage(conn, r["id"]).values()), 2)
    except Exception:  # noqa: BLE001 - a money figure must never stop the limit check
        pass
    try:
        step = perf.step_label(conn, r["id"])
    except Exception:  # noqa: BLE001
        step = "?"
    from . import delivered
    return {"id": r["id"], "name": r["name"], "step": step, "spent": spent, "archived": bool(r["archived"]),
            "rendered": delivered.has_render(conn, r["id"])}          # S14.30: has a final cut, not delivered → told how to finish it


def _mine(conn, email: str, archived: int) -> List[Dict]:
    rows = conn.execute("SELECT id, name, COALESCE(archived, 0) archived FROM projects WHERE LOWER(TRIM(COALESCE(created_by, '')))=?"
                        " AND COALESCE(archived, 0)=? ORDER BY id", (email.strip().lower(), archived)).fetchall()
    return [_describe(conn, r) for r in rows if not is_finished(conn, r["id"])]


def open_projects(conn, email: str) -> List[Dict]:
    """The person's unfinished projects in use (not put away)."""
    return _mine(conn, email, 0)


def parked_projects(conn, email: str) -> List[Dict]:
    """The person's unfinished projects put away (📦)."""
    return _mine(conn, email, 1)


def created_today(conn, email: str) -> List[int]:
    return [r[0] for r in conn.execute("SELECT project_id FROM project_creations WHERE email=? AND day=? ORDER BY id",
                                       (email.strip().lower(), _today()))]


def _list(rows: List[Dict]) -> str:
    return "; ".join(f"#{r['id']} “{r['name']}” — {r['step']} — đã chi ≈ ${r['spent']:.2f}"
                     + (" — có bản cuối, chưa xuất bản giao" if r.get("rendered") else "") for r in rows)


def _deliver_hint(rows: List[Dict]) -> str:
    """S14.30: a project held back only because its delivery was never exported — say how to count it as done."""
    ids = [f"#{r['id']}" for r in rows if r.get("rendered")]
    if not ids:
        return ""
    from .delivered import HINT
    return (f" Dự án {', '.join(ids)} đã có bản cuối nhưng chưa xuất bản giao — bấm “📦 Xuất bản đầy đủ” ở bước Bản giao: "
            f"{HINT} (không còn tính vào giới hạn).")


def _pending(conn, email: str, kind: str) -> Optional[int]:
    row = conn.execute("SELECT id FROM limit_requests WHERE email=? AND kind=? AND status='pending' ORDER BY id DESC LIMIT 1",
                       (email, kind)).fetchone()
    return row[0] if row else None


def _approved(conn, email: str, kind: str, project_id: Optional[int] = None) -> Optional[int]:
    if kind == "daily":
        row = conn.execute("SELECT id FROM limit_requests WHERE email=? AND kind='daily' AND status='approved' AND decided_day=?"
                           " ORDER BY id LIMIT 1", (email, _today())).fetchone()
    else:
        row = conn.execute("SELECT id FROM limit_requests WHERE email=? AND kind='parked' AND status='approved'"
                           " AND (project_id IS NULL OR project_id=?) ORDER BY id LIMIT 1", (email, project_id)).fetchone()
    return row[0] if row else None


def _block(conn, email: str, err: LimitReached) -> LimitReached:
    auth.audit(conn, email, "limit_block", f"{err.kind}: {err}")
    return err


def _open_error(conn, email: str, rows: List[Dict], lim: int, action: str) -> LimitReached:
    return _block(conn, email, LimitReached(
        "open", f"Bạn đang có {len(rows)}/{lim} dự án dở (chưa xuất bản giao): {_list(rows)}. {action}: GIỮ — quay lại làm tiếp "
                f"một dự án dở (không tạo mới), hoặc BỎ — cất 📦 một dự án dở (khôi phục được) để có chỗ." + _deliver_hint(rows),
        rows, len(rows), lim))


# ---- kiểm trước khi làm ---------------------------------------------------------------------------------------------------------------
def check_create(conn, user) -> Optional[int]:
    """Before a new project (create or clone). Raises LimitReached; returns the approved request it will use (3rd+ of the day)."""
    if exempt(user):
        return None
    email = _email(user)
    lim = limits(conn, email)
    rows = open_projects(conn, email)
    if len(rows) >= lim["open"]:
        raise _open_error(conn, email, rows, lim["open"], "Muốn tạo dự án mới")
    today = created_today(conn, email)
    if len(today) < lim["daily"]:
        return None
    rid = _approved(conn, email, "daily")
    if rid is not None:
        return rid
    pending = _pending(conn, email, "daily")
    made = ", ".join(f"#{i}" for i in today) or "—"
    msg = (f"Hôm nay bạn đã tạo {len(today)}/{lim['daily']} dự án: {made}. Dự án thứ {len(today) + 1} trong ngày cần Owner duyệt — "
           + (f"yêu cầu #{pending} của bạn đang chờ Owner duyệt ở 👥 Nhóm." if pending else
              "gửi yêu cầu kèm lý do, Owner duyệt / từ chối ở 👥 Nhóm."))
    raise _block(conn, email, LimitReached("daily", msg, [{"id": i, "name": "", "step": "", "spent": 0.0, "archived": False}
                                                          for i in today], len(today), lim["daily"], pending))


def record_create(conn, user, project_id: int, request_id: Optional[int] = None) -> None:
    """After the project row exists, in the SAME transaction (no commit here; the caller commits or rolls back, holding LOCK): count it
    for the day (kept when the project is deleted) and use up the approval."""
    email = _email(user)
    if not email:
        return
    conn.execute("INSERT INTO project_creations (email, project_id, day, at, request_id) VALUES (?,?,?,?,?)",
                 (email, project_id, _today(), _stamp(), request_id))
    if request_id is not None:
        _use(conn, request_id, project_id)


def _use(conn, request_id: int, project_id: int) -> None:
    """Mark an approval used — no commit (the caller's transaction). Refuses when it was not 'approved' any more (used by another
    click): the caller rolls back, nothing is made."""
    cur = conn.execute("UPDATE limit_requests SET status='used', used_at=?, used_project_id=? WHERE id=? AND status='approved'",
                       (_stamp(), project_id, request_id))
    if cur.rowcount != 1:
        raise LimitReached("used", f"Lượt Owner duyệt #{request_id} đã được dùng cho dự án khác — không tạo / cất thêm.", [], 0, 0)


def audit_use(conn, request_id: Optional[int], project_id: int) -> None:
    """After the commit: the approval used, in the audit log."""
    if request_id is None:
        return
    row = conn.execute("SELECT email, kind FROM limit_requests WHERE id=?", (request_id,)).fetchone()
    if row:
        auth.audit(conn, row["email"], "limit_request_used", f"#{request_id} ({row['kind']}) → dự án #{project_id}")


def check_archive(conn, user, project_id: int, bringing_back: Optional[int] = None) -> Optional[int]:
    """Before putting a project away. A finished project goes to the 'Kho dự án đã xong': never limited. Returns the approved
    'parked' request it will use. `bringing_back` = a parked project restored in the same move (swap): its place is freed."""
    if exempt(user) or is_finished(conn, project_id):
        return None
    email = _email(user)
    lim = limits(conn, email)["parked"]
    rows = [r for r in parked_projects(conn, email) if r["id"] != bringing_back]
    if len(rows) < lim:
        return None
    rid = _approved(conn, email, "parked", project_id)
    if rid is not None:
        return rid
    pending = _pending(conn, email, "parked")
    msg = (f"Bạn đang cất {len(rows)}/{lim} dự án dở: {_list(rows)}. Muốn cất thêm dự án #{project_id}: khôi phục dự án đang cất để làm "
           "tiếp, xóa hẳn một dự án dở (vào thùng rác), hoặc xin Owner duyệt"
           + (f" (yêu cầu #{pending} đang chờ)" if pending else "") + ". Dự án đã xong cất vào “Kho dự án đã xong”, không giới hạn."
           + _deliver_hint(rows + [_describe(conn, conn.execute("SELECT id, name, COALESCE(archived, 0) archived FROM projects WHERE id=?",
                                                                   (project_id,)).fetchone())]))
    raise _block(conn, email, LimitReached("parked", msg, rows, len(rows), lim, pending))


def check_restore(conn, user, project_id: int, putting_away: Optional[int] = None) -> None:
    """Before bringing a put-away project back: an unfinished one takes an 'open' place (`putting_away` = one freed in the same move)."""
    if exempt(user) or is_finished(conn, project_id):
        return
    email = _email(user)
    lim = limits(conn, email)["open"]
    rows = [r for r in open_projects(conn, email) if r["id"] != putting_away]
    if len(rows) >= lim:
        raise _open_error(conn, email, rows, lim, f"Muốn khôi phục dự án #{project_id}")


# ---- yêu cầu vượt mức → Owner duyệt ---------------------------------------------------------------------------------------------------
def request(conn, user, kind: str, reason: str, project_id: Optional[int] = None) -> int:
    """A person asks the Owner for one place more ('daily' | 'parked'), with a reason. A waiting request of the same kind is updated."""
    if kind not in KIND_LABELS:
        raise ValueError(f"loại yêu cầu không hợp lệ: {kind}")
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Cần ghi lý do để Owner duyệt.")
    email = _email(user)
    if not email:
        raise ValueError("Cần đăng nhập để gửi yêu cầu.")
    rid = _pending(conn, email, kind)
    if rid is not None:
        conn.execute("UPDATE limit_requests SET reason=?, project_id=?, requested_at=? WHERE id=?", (reason[:500], project_id, _stamp(), rid))
    else:
        rid = conn.execute("INSERT INTO limit_requests (email, kind, reason, project_id, requested_at) VALUES (?,?,?,?,?)",
                           (email, kind, reason[:500], project_id, _stamp())).lastrowid
    conn.commit()
    auth.audit(conn, email, "limit_request", f"#{rid} {KIND_LABELS[kind]}" + (f" (dự án #{project_id})" if project_id else "")
               + f": {reason}")
    return rid


def requests(conn, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
    sql = "SELECT * FROM limit_requests" + (" WHERE status=?" if status else "")
    sql += " ORDER BY CASE status WHEN 'pending' THEN 0 ELSE 1 END, id DESC LIMIT ?"
    return [dict(r) for r in conn.execute(sql, ((status, limit) if status else (limit,)))]


def status_label(row) -> str:
    """👥 Nhóm: an approved 'daily' place not used on the day it was approved is expired (check_create only takes today's)."""
    if row["status"] == "approved" and row["kind"] == "daily" and row["decided_day"] and row["decided_day"] != _today():
        return f"⌛ hết hạn (duyệt cho ngày {row['decided_day']})"
    return STATUS_LABELS.get(row["status"], row["status"])


def pending_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM limit_requests WHERE status='pending'").fetchone()[0]


def _decide(conn, actor, request_id: int, new: str) -> None:
    who = _need_owner(actor)
    row = conn.execute("SELECT * FROM limit_requests WHERE id=?", (request_id,)).fetchone()
    if row is None:
        raise ValueError(f"không có yêu cầu #{request_id}")
    if row["status"] != "pending":
        raise ValueError(f"yêu cầu #{request_id} đã {STATUS_LABELS.get(row['status'], row['status'])}")
    conn.execute("UPDATE limit_requests SET status=?, decided_at=?, decided_by=?, decided_day=? WHERE id=?",
                 (new, _stamp(), who, _today(), request_id))
    conn.commit()
    auth.audit(conn, who, "limit_approve" if new == "approved" else "limit_reject",
               f"#{request_id} {row['email']}: {KIND_LABELS.get(row['kind'], row['kind'])} — {row['reason']}")


def approve(conn, actor, request_id: int) -> None:
    _decide(conn, actor, request_id, "approved")


def reject(conn, actor, request_id: int) -> None:
    _decide(conn, actor, request_id, "rejected")
