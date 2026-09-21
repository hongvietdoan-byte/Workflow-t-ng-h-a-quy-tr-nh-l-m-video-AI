"""Sign-in by e-mail and role-based permissions for the dashboard.

Roles
  owner   the single top-level owner (DASHBOARD_OWNER_EMAIL). Everything, including users, roles and shutdown.
  admin   delegated by the owner: settings, prices, knowledge base, monitoring, lessons; may invite members.
  member  the video workflow only (script -> images -> prompts -> video -> music -> render, automatic mode).

How people get in (no e-mail server needed)
  * Passwords are stored only as scrypt hashes. Nobody can sign in with just an e-mail address.
  * The owner's account is created at first start with NO password; a one-time setup code is written to
    data/owner_setup_code.txt on the machine running the dashboard. Whoever can read that file (i.e. has the machine)
    sets the owner password. `tools/reset_owner.py` does the same from a terminal if the owner forgets it.
  * The owner / an admin invites a person by e-mail and gets a one-time invite code to hand over (chat, in person).
    The invited person enters their e-mail, the code and a new password. Codes expire and work once.
  * 5 wrong passwords lock the account for 15 minutes. Sessions last 12 hours and are checked on every page action, so
    deactivating a person or changing a role takes effect at once.
Limits: the dashboard speaks plain HTTP, so on a network passwords travel unencrypted (use a trusted network / VPN or
put it behind HTTPS). Sessions live in the browser tab: a page reload asks for the password again.
"""
import base64
import hashlib
import hmac
import os
import re
import secrets
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

OWNER_EMAIL = os.environ.get("DASHBOARD_OWNER_EMAIL", "hongviet.doan@garena.vn").strip().lower()
SESSION_SECONDS = 12 * 3600
INVITE_SECONDS = 7 * 24 * 3600
LOCK_AFTER, LOCK_SECONDS = 5, 15 * 60
MIN_PASSWORD = 8
ROLES = ("owner", "admin", "member")
ROLE_LABEL = {"owner": "Owner (cao nhất)", "admin": "Admin", "member": "Thành viên"}
_MEMBER = {"workflow", "autopilot"}
_ADMIN = _MEMBER | {"settings", "pricing", "knowledge", "monitor", "lessons", "invite_members"}
_OWNER = _ADMIN | {"users", "roles", "shutdown"}
PERMISSIONS = {"owner": _OWNER, "admin": _ADMIN, "member": _MEMBER}
_EMAIL = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9\-]+(\.[a-z0-9\-]+)+$")


class AuthError(Exception):
    """Something the person can be told (wrong password, locked, weak password...). Never leaks whether an e-mail exists."""


@dataclass
class Identity:
    email: str
    name: str
    role: str


def can(role: Optional[str], permission: str) -> bool:
    return permission in PERMISSIONS.get(role or "", ())


def normalize_email(raw: str) -> str:
    email = (raw or "").strip().lower()
    if not _EMAIL.match(email) or len(email) > 120:
        raise AuthError("E-mail không hợp lệ")
    return email


def _now() -> float:
    return time.time()


def _stamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


# ---- passwords -------------------------------------------------------------------------------------
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, stored: Optional[str]) -> bool:
    try:
        _, salt_b64, digest_b64 = (stored or "").split("$")
        salt, want = base64.b64decode(salt_b64), base64.b64decode(digest_b64)
        got = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
        return hmac.compare_digest(got, want)
    except (ValueError, TypeError):
        return False


_DUMMY = hash_password("not-a-real-password")      # so an unknown e-mail costs the same time as a wrong password


def check_new_password(password: str, email: str = "") -> None:
    if len(password or "") < MIN_PASSWORD:
        raise AuthError(f"Mật khẩu cần ít nhất {MIN_PASSWORD} ký tự")
    if email and password.strip().lower() == email:
        raise AuthError("Mật khẩu không được trùng e-mail")


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _new_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"        # no look-alike characters
    raw = "".join(secrets.choice(alphabet) for _ in range(10))
    return raw[:5] + "-" + raw[5:]


# ---- audit ---------------------------------------------------------------------------------------------
def audit(conn, who: Optional[str], action: str, detail: str = "") -> None:
    conn.execute("INSERT INTO audit_log (at, email, action, detail) VALUES (?,?,?,?)", (_stamp(), who, action, detail[:300]))
    conn.commit()


def recent_audit(conn, limit: int = 60) -> List[Dict]:
    return [dict(r) for r in conn.execute("SELECT at, email, action, detail FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))]


# ---- the owner ---------------------------------------------------------------------------------------------
def ensure_owner(conn, data_dir: str = "data") -> Optional[str]:
    """Make sure the owner account exists. While it has no password, keep a fresh one-time setup code in
    <data_dir>/owner_setup_code.txt and return it; once the owner has a password the file is removed."""
    path = os.path.join(data_dir, "owner_setup_code.txt")
    row = conn.execute("SELECT * FROM users WHERE email=?", (OWNER_EMAIL,)).fetchone()
    if row is None:
        conn.execute("INSERT INTO users (email, name, role, active, created_at, created_by) VALUES (?,?,?,?,?,?)",
                     (OWNER_EMAIL, OWNER_EMAIL.split("@")[0], "owner", 1, _stamp(), "system"))
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE email=?", (OWNER_EMAIL,)).fetchone()
    if row["role"] != "owner":                                  # the owner e-mail is always the owner
        conn.execute("UPDATE users SET role='owner', active=1 WHERE email=?", (OWNER_EMAIL,))
        conn.commit()
    if row["pw_hash"]:
        if os.path.exists(path):
            os.remove(path)
        return None
    if row["invite_hash"] and (row["invite_expires"] or 0) > _now() and os.path.exists(path):
        return open(path, encoding="utf-8").read().split()[-1]
    code = _new_code()
    conn.execute("UPDATE users SET invite_hash=?, invite_expires=? WHERE email=?", (_hash_secret(code), _now() + INVITE_SECONDS, OWNER_EMAIL))
    conn.commit()
    os.makedirs(data_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Ma thiet lap mat khau Owner ({OWNER_EMAIL}), dung 1 lan, het han sau 7 ngay:\n{code}\n")
    audit(conn, "system", "owner_setup_code", "created")
    return code


# ---- invitations ----------------------------------------------------------------------------------------------
def _manageable(actor_role: str, target_role: str) -> bool:
    """May someone with actor_role act on an account of target_role? The owner is never touched."""
    if target_role == "owner":
        return False
    if actor_role == "owner":
        return True
    return actor_role == "admin" and target_role == "member"


def invite(conn, actor: Identity, email: str, role: str = "member", name: str = "") -> str:
    """Create (or re-issue) an account for `email` and return the one-time code to hand to that person."""
    email = normalize_email(email)
    if role not in ("admin", "member"):
        raise AuthError("Vai trò không hợp lệ")
    if not can(actor.role, "invite_members") and not can(actor.role, "users"):
        raise AuthError("Bạn không có quyền mời người dùng")
    if not _manageable(actor.role, role):
        raise AuthError("Bạn chỉ được mời thành viên (Owner mới được cấp quyền Admin)")
    row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if row is not None and not _manageable(actor.role, row["role"]):
        raise AuthError("Không thể thay đổi tài khoản này")
    code = _new_code()
    if row is None:
        conn.execute("INSERT INTO users (email, name, role, active, invite_hash, invite_expires, created_at, created_by)"
                     " VALUES (?,?,?,?,?,?,?,?)", (email, name.strip() or email.split("@")[0], role, 1, _hash_secret(code),
                                                    _now() + INVITE_SECONDS, _stamp(), actor.email))
    else:                                    # re-invite = also the way to reset a forgotten password
        conn.execute("UPDATE users SET role=?, active=1, pw_hash=NULL, invite_hash=?, invite_expires=?, failed=0, locked_until=NULL"
                     " WHERE email=?", (role, _hash_secret(code), _now() + INVITE_SECONDS, email))
        revoke_sessions(conn, email)
    conn.commit()
    audit(conn, actor.email, "invite", f"{email} as {role}")
    return code


def accept_invite(conn, email: str, code: str, new_password: str, data_dir: Optional[str] = None) -> None:
    email = normalize_email(email)
    check_new_password(new_password, email)
    row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    _guard_lock(row)
    ok = (row is not None and row["active"] and row["invite_hash"] and (row["invite_expires"] or 0) > _now()
          and hmac.compare_digest(row["invite_hash"], _hash_secret((code or "").strip().upper())))
    if not ok:
        _count_failure(conn, row)
        raise AuthError("Mã không đúng hoặc đã hết hạn")
    conn.execute("UPDATE users SET pw_hash=?, invite_hash=NULL, invite_expires=NULL, failed=0, locked_until=NULL WHERE email=?",
                 (hash_password(new_password), email))
    conn.commit()
    audit(conn, email, "password_set", "via invite/setup code")
    if email == OWNER_EMAIL and data_dir:
        ensure_owner(conn, data_dir)            # removes the one-time setup code file


# ---- sign in / sessions ----------------------------------------------------------------------------------------
def _guard_lock(row) -> None:
    if row is not None and (row["locked_until"] or 0) > _now():
        minutes = int(((row["locked_until"] - _now()) // 60) + 1)
        raise AuthError(f"Tài khoản tạm khóa do nhập sai nhiều lần. Thử lại sau {minutes} phút")


def _count_failure(conn, row) -> None:
    if row is None:
        return
    failed = (row["failed"] or 0) + 1
    locked = _now() + LOCK_SECONDS if failed >= LOCK_AFTER else None
    conn.execute("UPDATE users SET failed=?, locked_until=? WHERE email=?", (0 if locked else failed, locked, row["email"]))
    conn.commit()
    if locked:
        audit(conn, row["email"], "locked", f"{LOCK_AFTER} wrong attempts")


def login(conn, email: str, password: str) -> str:
    """Return a session token, or raise AuthError with a message safe to show (it does not reveal whether the e-mail exists)."""
    try:
        email = normalize_email(email)
    except AuthError:
        raise AuthError("Email hoặc mật khẩu không đúng") from None
    row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    _guard_lock(row)
    good = verify_password(password or "", row["pw_hash"] if row else _DUMMY)
    if row is None or not good or not row["active"]:
        _count_failure(conn, row)
        raise AuthError("Email hoặc mật khẩu không đúng")
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO sessions (token_hash, email, created_at, expires_at) VALUES (?,?,?,?)",
                 (_hash_secret(token), email, _now(), _now() + SESSION_SECONDS))
    conn.execute("UPDATE users SET failed=0, locked_until=NULL, last_login=? WHERE email=?", (_stamp(), email))
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (_now(),))
    conn.commit()
    audit(conn, email, "login", "")
    return token


def identity(conn, token: Optional[str]) -> Optional[Identity]:
    """Who is behind this session token right now (None when expired, signed out or the account was deactivated)."""
    if not token:
        return None
    row = conn.execute("SELECT u.email, u.name, u.role, u.active, s.expires_at FROM sessions s JOIN users u ON u.email=s.email"
                       " WHERE s.token_hash=?", (_hash_secret(token),)).fetchone()
    if row is None or row["expires_at"] < _now() or not row["active"]:
        return None
    return Identity(row["email"], row["name"] or row["email"], row["role"])


def logout(conn, token: Optional[str]) -> None:
    if token:
        conn.execute("DELETE FROM sessions WHERE token_hash=?", (_hash_secret(token),))
        conn.commit()


def revoke_sessions(conn, email: str) -> None:
    conn.execute("DELETE FROM sessions WHERE email=?", (email,))
    conn.commit()


def change_password(conn, email: str, old: str, new: str) -> None:
    row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if row is None or not verify_password(old or "", row["pw_hash"]):
        raise AuthError("Mật khẩu hiện tại không đúng")
    check_new_password(new, email)
    conn.execute("UPDATE users SET pw_hash=? WHERE email=?", (hash_password(new), email))
    conn.commit()
    audit(conn, email, "password_changed", "")


# ---- managing people ---------------------------------------------------------------------------------------------
def list_users(conn) -> List[Dict]:
    order = "CASE role WHEN 'owner' THEN 0 WHEN 'admin' THEN 1 ELSE 2 END, email"
    return [dict(r, pending=not r["pw_hash"]) for r in conn.execute(
        "SELECT email, name, role, active, pw_hash, last_login, created_at, created_by, invite_expires FROM users ORDER BY " + order)]


def _target(conn, actor: Identity, email: str):
    row = conn.execute("SELECT * FROM users WHERE email=?", (normalize_email(email),)).fetchone()
    if row is None:
        raise AuthError("Không có người dùng này")
    if not _manageable(actor.role, row["role"]) or not (can(actor.role, "users") or can(actor.role, "invite_members")):
        raise AuthError("Bạn không có quyền thay đổi tài khoản này")
    return row


def set_role(conn, actor: Identity, email: str, role: str) -> None:
    if not can(actor.role, "roles"):
        raise AuthError("Chỉ Owner được đổi vai trò")
    if role not in ("admin", "member"):
        raise AuthError("Vai trò không hợp lệ")
    row = _target(conn, actor, email)
    conn.execute("UPDATE users SET role=? WHERE email=?", (role, row["email"]))
    conn.commit()
    audit(conn, actor.email, "role", f"{row['email']} -> {role}")


def set_active(conn, actor: Identity, email: str, active: bool) -> None:
    row = _target(conn, actor, email)
    conn.execute("UPDATE users SET active=? WHERE email=?", (1 if active else 0, row["email"]))
    if not active:
        revoke_sessions(conn, row["email"])
    conn.commit()
    audit(conn, actor.email, "activate" if active else "deactivate", row["email"])
