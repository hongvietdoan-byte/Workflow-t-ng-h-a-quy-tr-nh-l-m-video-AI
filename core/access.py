"""Quyền theo DỰ ÁN (đợt F, 02/10 — người dùng chốt chính sách): ai thấy / sửa được dự án nào. Thực thi CỨNG ở lõi.

Chính sách
- Mỗi người chỉ thấy và thao tác dự án DO CHÍNH HỌ TẠO (projects.created_by).
- Cấp Owner (users.role = 'owner') thấy và làm được MỌI dự án (xem, sửa, gửi job, cất / khôi phục, xóa, đặt lại tiền…).
- "Theo dõi" (bảng project_watchers): Owner hoặc chủ dự án thêm một người vào dự án kèm mức 'view' (chỉ xem) hoặc 'edit' (xem + sửa, gửi
  job, duyệt). Người theo dõi thấy dự án ở ⌂ / 📥 và có đúng mức được cấp. Việc "quản trị" dự án (cất, khôi phục, xóa, đổi người theo dõi)
  chỉ của Owner và chủ dự án — người theo dõi mức 'edit' KHÔNG làm được.
- Dự án cũ không ghi chủ (created_by rỗng): chỉ Owner thấy cho tới khi Owner gán chủ (assign_creator); không ai khác thấy.

Cách thực thi: Pipeline có thuộc tính `user` ({'email','role'}). Dashboard gán nó cho người đang đăng nhập; mọi hàm lõi ghi / gửi job / duyệt
/ cất gọi `need_edit(p, project_id, việc)` (hoặc need_view / need_manage) và ném AccessDenied — thông báo tiếng Việt, nói rõ vì sao —
thay vì im lặng bỏ qua. `p.user = None` = chạy hệ thống (autopilot nền, worker, kiểm thử lõi) hoặc đăng nhập tắt: không giới hạn, đúng như
trước. Đây là kiểm quyền theo danh tính phiên đăng nhập của Dashboard; nó không thay cho việc bảo vệ mạng (xem core/auth.py: e-mail chỉ là lời khai).
"""
from typing import Dict, Iterable, List, Optional, Set

from . import auth

LEVELS = ("view", "edit")
LEVEL_LABEL = {"view": "Chỉ xem", "edit": "Được sửa"}
RANK = {None: 0, "view": 1, "edit": 2, "own": 3, "admin": 4}      # 'own' = người tạo dự án, 'admin' = cấp Owner / hệ thống


class AccessDenied(PermissionError):
    """Thiếu quyền trên một dự án. `str(e)` là câu tiếng Việt cho người dùng thấy."""


NOBODY_ROLE = "none"        # an identity with no e-mail: holds no right at all (S14.7)


def user_of(identity) -> Optional[Dict]:
    """{'email','role'} from an auth.Identity or the session's identity dict; None for 'no one' (system / sign-in off).

    S14.7 (D1, kế hoạch 3.5 ý 3): an identity that IS there but has no e-mail (a broken / half-built session) is CLOSED — it gets
    {'email': '', 'role': 'none'} and no right on any project — instead of being taken for the system (every right). Where identities
    are made (checked 05/10): dashboard header.require_login ("local" when sign-in is off, else auth.identity → always an e-mail);
    autopilot / worker never set p.user (only p.actor, a plain name) → None = system, unchanged."""
    if identity is None:
        return None
    get = identity.get if isinstance(identity, dict) else (lambda k, d=None: getattr(identity, k, d))
    email = (get("email") or "").strip().lower()
    if email == "local":                                      # sign-in off: dashboard puts a pseudo-owner "local"
        return None
    if not email:
        return {"email": "", "role": NOBODY_ROLE}
    return {"email": email, "role": get("role") or "member"}


def _row(conn, project_id: int):
    return conn.execute("SELECT id, name, created_by FROM projects WHERE id=?", (project_id,)).fetchone()


def level(conn, project_id: int, user) -> Optional[str]:
    """'admin' (Owner / system) > 'own' (creator) > 'edit' > 'view' > None (no right at all)."""
    u = user_of(user)
    if u is None:
        return "admin"
    if not u.get("email"):
        return None
    if u.get("role") == "owner":
        return "admin"
    row = _row(conn, project_id)
    if row is None:
        return None
    email = (u.get("email") or "").strip().lower()
    creator = (row["created_by"] or "").strip().lower()
    if creator and creator == email:
        return "own"
    w = conn.execute("SELECT level FROM project_watchers WHERE project_id=? AND email=?", (project_id, email)).fetchone()
    return w["level"] if w else None


def can_view(conn, project_id: int, user) -> bool:
    return RANK[level(conn, project_id, user)] >= RANK["view"]


def can_edit(conn, project_id: int, user) -> bool:
    return RANK[level(conn, project_id, user)] >= RANK["edit"]


def can_manage(conn, project_id: int, user) -> bool:
    """Cất / khôi phục / xóa dự án, đổi người theo dõi: Owner hoặc chủ dự án."""
    return RANK[level(conn, project_id, user)] >= RANK["own"]


def _who(row) -> str:
    return (row["created_by"] or "").strip() if row is not None else ""


def _deny(conn, project_id: int, user, need: str, action: str) -> AccessDenied:
    row = _row(conn, project_id)
    name = f"#{project_id} «{row['name']}»" if row is not None else f"#{project_id}"
    owner = _who(row)
    held = level(conn, project_id, user)
    what = f" — không thể {action}" if action else ""
    if held is None:
        who = f"do {owner} tạo" if owner else "chưa có chủ (chỉ Owner thấy)"
        return AccessDenied(f"Bạn không có quyền với dự án {name}{what}: dự án {who}. "
                            "Nhờ chủ dự án hoặc Owner thêm bạn vào danh sách theo dõi.")
    if need == "manage":
        return AccessDenied(f"Chỉ Owner hoặc chủ dự án ({owner or 'chưa có chủ'}) được quản trị dự án {name}{what}.")
    return AccessDenied(f"Bạn chỉ được XEM dự án {name} (quyền theo dõi: chỉ xem){what}. "
                        "Nhờ chủ dự án hoặc Owner nâng lên mức “Được sửa”.")


def require(conn, project_id: int, user, need: str = "edit", action: str = "") -> None:
    """Raise AccessDenied unless `user` holds the `need` ('view' | 'edit' | 'manage') right on the project."""
    held = RANK[level(conn, project_id, user)]
    want = {"view": RANK["view"], "edit": RANK["edit"], "manage": RANK["own"]}[need]
    if held < want:
        raise _deny(conn, project_id, user, need, action)


# ---- Pipeline-facing helpers (p.user = người đang thao tác; None = hệ thống) -------------------------------------------------------
def _p_user(p):
    return getattr(p, "user", None)


def need_view(p, project_id: int, action: str = "") -> None:
    if _p_user(p) is not None:
        require(p.conn, project_id, _p_user(p), "view", action)


def need_edit(p, project_id: int, action: str = "") -> None:
    if _p_user(p) is not None:
        require(p.conn, project_id, _p_user(p), "edit", action)


def need_manage(p, project_id: int, action: str = "") -> None:
    if _p_user(p) is not None:
        require(p.conn, project_id, _p_user(p), "manage", action)


def project_of_job(conn, job_id: int) -> Optional[int]:
    r = conn.execute("SELECT project_id FROM jobs WHERE id=?", (job_id,)).fetchone()
    return r["project_id"] if r else None


def project_of_scene(conn, scene_id: int) -> Optional[int]:
    r = conn.execute("SELECT project_id FROM scenes WHERE id=?", (scene_id,)).fetchone()
    return r["project_id"] if r else None


def need_edit_job(p, job_id: int, action: str = "") -> None:
    if _p_user(p) is not None:
        pid = project_of_job(p.conn, job_id)
        if pid is None:
            raise AccessDenied(f"Không tìm thấy việc #{job_id} để {action or 'thao tác'}.")
        require(p.conn, pid, _p_user(p), "edit", action)


def need_edit_scene(p, scene_id: int, action: str = "") -> None:
    if _p_user(p) is not None:
        pid = project_of_scene(p.conn, scene_id)
        if pid is None:
            raise AccessDenied(f"Không tìm thấy cảnh #{scene_id} để {action or 'thao tác'}.")
        require(p.conn, pid, _p_user(p), "edit", action)


# ---- danh sách thấy được -----------------------------------------------------------------------------------------------------------
def visible_ids(conn, user) -> Optional[Set[int]]:
    """Project ids this person may view; None = all of them (Owner / system)."""
    u = user_of(user)
    if u is None or (u.get("email") and u.get("role") == "owner"):
        return None
    email = (u.get("email") or "").strip().lower()
    if not email:
        return set()
    ids = {r["id"] for r in conn.execute("SELECT id FROM projects WHERE LOWER(TRIM(COALESCE(created_by,'')))=?", (email,))}
    ids |= {r["project_id"] for r in conn.execute("SELECT project_id FROM project_watchers WHERE email=?", (email,))}
    return ids


def filter_rows(conn, rows: Iterable, user, key: str = "id") -> List:
    ok = visible_ids(conn, user)
    return [r for r in rows if ok is None or r[key] in ok]


def levels_for(conn, user) -> Dict[int, str]:
    """{project_id: level} for the projects the person can see (Owner: every project as 'admin')."""
    u = user_of(user)
    if u is None or (u.get("email") and u.get("role") == "owner"):
        return {r["id"]: "admin" for r in conn.execute("SELECT id FROM projects")}
    email = (u.get("email") or "").strip().lower()
    if not email:
        return {}
    out = {r["project_id"]: r["level"] for r in conn.execute("SELECT project_id, level FROM project_watchers WHERE email=?", (email,))}
    for r in conn.execute("SELECT id FROM projects WHERE LOWER(TRIM(COALESCE(created_by,'')))=?", (email,)):
        out[r["id"]] = "own"
    return out


# ---- người theo dõi ----------------------------------------------------------------------------------------------------------------
def list_watchers(conn, project_id: int) -> List[Dict]:
    return [{"email": r["email"], "level": r["level"], "added_by": r["added_by"], "added_at": r["added_at"]}
            for r in conn.execute("SELECT * FROM project_watchers WHERE project_id=? ORDER BY email", (project_id,))]


def _now() -> str:
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S")


def set_watcher(conn, actor, project_id: int, email: str, lvl: str) -> None:
    """Add a person to the project's watch list, or change their level. Owner / the project's creator only."""
    require(conn, project_id, actor, "manage", "đổi danh sách người theo dõi")
    if lvl not in LEVELS:
        raise AccessDenied("Mức theo dõi phải là “Chỉ xem” hoặc “Được sửa”.")
    try:
        email = auth.normalize_email(email)
    except auth.AuthError as e:
        raise AccessDenied(str(e)) from e
    user = conn.execute("SELECT role, active FROM users WHERE email=?", (email,)).fetchone()
    if user is None or not user["active"]:
        raise AccessDenied(f"{email} chưa có tài khoản đang hoạt động — Owner mời ở 👥 Nhóm trước.")
    if user["role"] == "owner":
        raise AccessDenied(f"{email} là Owner nên đã thấy mọi dự án — không cần thêm vào danh sách theo dõi.")
    row = _row(conn, project_id)
    if row is not None and (row["created_by"] or "").strip().lower() == email:
        raise AccessDenied(f"{email} là người tạo dự án này — đã có đầy đủ quyền.")
    conn.execute("INSERT INTO project_watchers (project_id, email, level, added_by, added_at) VALUES (?,?,?,?,?)"
                 " ON CONFLICT(project_id, email) DO UPDATE SET level=excluded.level, added_by=excluded.added_by, added_at=excluded.added_at",
                 (project_id, email, lvl, (user_of(actor) or {}).get("email") or "system", _now()))
    conn.commit()
    auth.audit(conn, (user_of(actor) or {}).get("email"), "watch_set", f"#{project_id} {email} {lvl}")


def remove_watcher(conn, actor, project_id: int, email: str) -> None:
    require(conn, project_id, actor, "manage", "đổi danh sách người theo dõi")
    email = (email or "").strip().lower()
    cur = conn.execute("DELETE FROM project_watchers WHERE project_id=? AND email=?", (project_id, email))
    conn.commit()
    if cur.rowcount:
        auth.audit(conn, (user_of(actor) or {}).get("email"), "watch_remove", f"#{project_id} {email}")


def assign_creator(conn, actor, project_id: int, email: str) -> None:
    """Owner only: give a project with no recorded creator (an old one) to a person. That person becomes its owner of record; any
    watcher entry of theirs is dropped (the creator has full rights)."""
    u = user_of(actor)
    if u is not None and u.get("role") != "owner":
        raise AccessDenied("Chỉ Owner được gán chủ cho dự án.")
    try:
        email = auth.normalize_email(email)
    except auth.AuthError as e:
        raise AccessDenied(str(e)) from e
    if conn.execute("SELECT 1 FROM users WHERE email=? AND active=1", (email,)).fetchone() is None:
        raise AccessDenied(f"{email} chưa có tài khoản đang hoạt động.")
    if _row(conn, project_id) is None:
        raise AccessDenied(f"Không có dự án #{project_id}.")
    conn.execute("UPDATE projects SET created_by=? WHERE id=?", (email, project_id))
    conn.execute("DELETE FROM project_watchers WHERE project_id=? AND email=?", (project_id, email))
    conn.commit()
    auth.audit(conn, (u or {}).get("email"), "assign_creator", f"#{project_id} -> {email}")


def orphans(conn) -> List[Dict]:
    """Projects with no recorded creator: only the Owner sees them until assign_creator."""
    return [dict(r) for r in conn.execute(
        "SELECT id, name FROM projects WHERE TRIM(COALESCE(created_by,''))='' ORDER BY id")]
