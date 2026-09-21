"""Sign-in by e-mail (no password) and per-person permissions for the dashboard.

Simple on purpose:
  * Everyone signs in with just an e-mail address. Whoever the owner has listed gets the permissions the owner set.
  * An e-mail that is not listed but belongs to an auto-member domain (default garena.vn, owner can change it) is
    added as a plain member on first sign-in: it only gets the video workflow.
  * Any other e-mail is refused until the owner adds it.
  * Owner = DASHBOARD_OWNER_EMAIL (default hongviet.doan@garena.vn). Only the owner manages people and can shut the
    dashboard down. The owner cannot be removed or changed by anyone.

IMPORTANT LIMIT: with no password, an e-mail address is only a claim, not proof. Anyone who can open the dashboard and
types someone's e-mail is signed in as that person, including the owner's. That is acceptable only on a trusted network.
Optional hardening: DASHBOARD_OWNER_LOCAL_ONLY=1 lets the owner sign in only from the machine running the dashboard.
Every sign-in and permission change is written to the audit log (with the address it came from).
"""
import json
import os
import re
import secrets
import time
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional

OWNER_EMAIL = os.environ.get("DASHBOARD_OWNER_EMAIL", "hongviet.doan@garena.vn").strip().lower()
DEFAULT_DOMAINS = "garena.vn"
SESSION_SECONDS = 12 * 3600
# permissions the owner can hand out one by one; the video workflow itself is for everyone
PERM_LABELS = {"settings": "Cài đặt & bảng giá", "knowledge": "Kho kiến thức", "monitor": "Theo dõi hiệu suất",
               "lessons": "Bài học", "assets": "Kho tài nguyên"}
OWNER_ONLY = ("users", "shutdown")
ALWAYS = ("workflow", "autopilot")
_EMAIL = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9\-]+(\.[a-z0-9\-]+)+$")


class AuthError(Exception):
    """A message that can be shown to the person."""


@dataclass
class Identity:
    email: str
    name: str
    role: str                                   # 'owner' | 'member'
    perms: List[str] = field(default_factory=list)


def can(who, permission: str) -> bool:
    """`who` is an Identity or the identity dict kept in the session ({'role', 'perms'})."""
    role = getattr(who, "role", None) if not isinstance(who, dict) else who.get("role")
    perms = getattr(who, "perms", None) if not isinstance(who, dict) else who.get("perms")
    if role == "owner":
        return True
    if role != "member":
        return False
    return permission in ALWAYS or (permission in PERM_LABELS and permission in (perms or []))


def normalize_email(raw: str) -> str:
    email = (raw or "").strip().lower()
    if not _EMAIL.match(email) or len(email) > 120:
        raise AuthError("E-mail không hợp lệ")
    return email


def _now() -> float:
    return time.time()


def _stamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def audit(conn, who: Optional[str], action: str, detail: str = "") -> None:
    conn.execute("INSERT INTO audit_log (at, email, action, detail) VALUES (?,?,?,?)", (_stamp(), who, action, detail[:300]))
    conn.commit()


def recent_audit(conn, limit: int = 80) -> List[Dict]:
    return [dict(r) for r in conn.execute("SELECT at, email, action, detail FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))]


def meta(conn, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM learning_meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def auto_domains(conn) -> List[str]:
    raw = meta(conn, "auto_member_domains", DEFAULT_DOMAINS)
    return [d.strip().lower().lstrip("@") for d in raw.split(",") if d.strip()]


def set_auto_domains(conn, actor: Identity, text: str) -> None:
    _need_owner(actor)
    domains = [d.strip().lower().lstrip("@") for d in re.split(r"[,\s;]+", text or "") if d.strip()]
    if any(not re.match(r"^[a-z0-9\-]+(\.[a-z0-9\-]+)+$", d) for d in domains):
        raise AuthError("Tên miền không hợp lệ (ví dụ: garena.vn)")
    conn.execute("INSERT INTO learning_meta (key, value) VALUES ('auto_member_domains', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (",".join(domains),))
    conn.commit()
    audit(conn, actor.email, "auto_domains", ",".join(domains) or "(none)")


def _need_owner(actor: Identity) -> None:
    if not can(actor, "users"):
        raise AuthError("Chỉ Owner được quản lý người dùng")


def ensure_owner(conn) -> None:
    """The owner e-mail always exists, is active and is the owner."""
    row = conn.execute("SELECT role, active FROM users WHERE email=?", (OWNER_EMAIL,)).fetchone()
    if row is None:
        conn.execute("INSERT INTO users (email, name, role, active, created_at, created_by) VALUES (?,?,?,?,?,?)",
                     (OWNER_EMAIL, OWNER_EMAIL.split("@")[0], "owner", 1, _stamp(), "system"))
    elif row["role"] != "owner" or not row["active"]:
        conn.execute("UPDATE users SET role='owner', active=1 WHERE email=?", (OWNER_EMAIL,))
    conn.commit()


def _perms(raw) -> List[str]:
    try:
        return [p for p in json.loads(raw or "[]") if p in PERM_LABELS]
    except ValueError:
        return []


# ---- sign in ------------------------------------------------------------------------------------------------
def login(conn, email: str, source: str = "", local: bool = True) -> str:
    """Sign in with just an e-mail. Returns a session token. `source` (address the request came from) goes to the audit log."""
    email = normalize_email(email)
    ensure_owner(conn)
    if email == OWNER_EMAIL and os.environ.get("DASHBOARD_OWNER_LOCAL_ONLY", "").strip() in ("1", "true", "on") and not local:
        audit(conn, email, "owner_login_refused", f"not local ({source})")
        raise AuthError("Owner chỉ được đăng nhập từ chính máy đang chạy Dashboard (DASHBOARD_OWNER_LOCAL_ONLY)")
    row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if row is None:
        domain = email.split("@", 1)[1]
        if domain not in auto_domains(conn):
            audit(conn, email, "login_refused", f"not listed ({source})")
            raise AuthError("E-mail này chưa được cấp quyền. Nhờ Owner thêm e-mail của bạn vào bảng phân quyền.")
        conn.execute("INSERT INTO users (email, name, role, active, perms, created_at, created_by) VALUES (?,?,?,?,?,?,?)",
                     (email, email.split("@")[0], "member", 1, "[]", _stamp(), "auto-domain"))
        conn.commit()
        audit(conn, email, "auto_member", f"domain {domain}")
        row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not row["active"]:
        audit(conn, email, "login_refused", f"deactivated ({source})")
        raise AuthError("Tài khoản này đã bị vô hiệu hóa. Liên hệ Owner.")
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO sessions (token_hash, email, created_at, expires_at) VALUES (?,?,?,?)",
                 (_hash(token), email, _now(), _now() + SESSION_SECONDS))
    conn.execute("UPDATE users SET last_login=? WHERE email=?", (_stamp(), email))
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (_now(),))
    conn.commit()
    audit(conn, email, "login", source)
    return token


def identity(conn, token: Optional[str]) -> Optional[Identity]:
    """Who is behind this session right now (re-read on every page action, so changes apply at once)."""
    if not token:
        return None
    row = conn.execute("SELECT u.email, u.name, u.role, u.perms, u.active, s.expires_at FROM sessions s JOIN users u ON u.email=s.email"
                       " WHERE s.token_hash=?", (_hash(token),)).fetchone()
    if row is None or row["expires_at"] < _now() or not row["active"]:
        return None
    return Identity(row["email"], row["name"] or row["email"], row["role"], _perms(row["perms"]))


def logout(conn, token: Optional[str]) -> None:
    if token:
        conn.execute("DELETE FROM sessions WHERE token_hash=?", (_hash(token),))
        conn.commit()


def revoke_sessions(conn, email: str) -> None:
    conn.execute("DELETE FROM sessions WHERE email=?", (email,))
    conn.commit()


# ---- the permission table (owner only) ------------------------------------------------------------------------
def list_users(conn) -> List[Dict]:
    out = []
    for r in conn.execute("SELECT * FROM users ORDER BY CASE role WHEN 'owner' THEN 0 ELSE 1 END, email"):
        out.append({"email": r["email"], "name": r["name"], "role": r["role"], "active": bool(r["active"]),
                    "perms": _perms(r["perms"]), "last_login": r["last_login"], "created_by": r["created_by"]})
    return out


def add_user(conn, actor: Identity, email: str, perms: Optional[List[str]] = None) -> None:
    _need_owner(actor)
    email = normalize_email(email)
    if conn.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
        raise AuthError("E-mail này đã có trong bảng")
    conn.execute("INSERT INTO users (email, name, role, active, perms, created_at, created_by) VALUES (?,?,?,?,?,?,?)",
                 (email, email.split("@")[0], "member", 1, json.dumps(_perms(json.dumps(perms or []))), _stamp(), actor.email))
    conn.commit()
    audit(conn, actor.email, "add_user", f"{email} perms={perms or []}")


def set_user(conn, actor: Identity, email: str, perms: List[str], active: bool) -> None:
    """Save one row of the permission table."""
    _need_owner(actor)
    email = normalize_email(email)
    if email == OWNER_EMAIL:
        raise AuthError("Không thể thay đổi Owner")
    row = conn.execute("SELECT perms, active FROM users WHERE email=?", (email,)).fetchone()
    if row is None:
        raise AuthError("Không có người dùng này")
    new_perms = _perms(json.dumps(perms))
    if new_perms == _perms(row["perms"]) and bool(row["active"]) == bool(active):
        return
    conn.execute("UPDATE users SET perms=?, active=? WHERE email=?", (json.dumps(new_perms), 1 if active else 0, email))
    if not active:
        revoke_sessions(conn, email)
    conn.commit()
    audit(conn, actor.email, "set_user", f"{email} perms={new_perms} active={bool(active)}")


def remove_user(conn, actor: Identity, email: str) -> None:
    _need_owner(actor)
    email = normalize_email(email)
    if email == OWNER_EMAIL:
        raise AuthError("Không thể xóa Owner")
    conn.execute("DELETE FROM users WHERE email=?", (email,))
    revoke_sessions(conn, email)
    conn.commit()
    audit(conn, actor.email, "remove_user", email)


def apply_table(conn, actor: Identity, rows: List[Dict]) -> int:
    """Save the whole permission table ([{'email', 'active', 'perms'}]). Returns how many rows actually changed."""
    _need_owner(actor)
    before = {u["email"]: (u["perms"], u["active"]) for u in list_users(conn)}
    changed = 0
    for r in rows:
        email = normalize_email(r["email"])
        if email == OWNER_EMAIL:
            continue
        if before.get(email) != (_perms(json.dumps(r["perms"])), bool(r["active"])):
            set_user(conn, actor, email, r["perms"], r["active"])
            changed += 1
    return changed
