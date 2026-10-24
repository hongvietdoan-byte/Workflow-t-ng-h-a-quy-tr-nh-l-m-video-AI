"""M82 pha A: hạn mức tự động được EP duyệt; chỉ lưu/hiển thị, chưa nối gửi job.

Metadata riêng trong app_settings, không thay trần cảnh báo project_budget cũ.
Không dùng số này chặn thao tác tay hay mở quyền tự động; M8.4 là cổng riêng.
"""
import json
import math
from datetime import datetime, timezone

from . import features, project_budget


def enabled():
    return features.on("simple_mode")


def proposal(p, pid):
    # Chưa có dự toán qd3 xấu nhất + tự sửa 40%. Không đổi nhãn trần cảnh báo
    # cũ thành một hạn mức tự động có thể duyệt.
    return dict(project_budget.propose(p, pid), qd3_complete=False)


def _key(pid):
    return f"simple_auto_limit:{pid}"


def get(conn, pid):
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (_key(pid),)).fetchone()
    if not row:
        return None
    data = json.loads(row[0])
    if not isinstance(data, dict) or not _amount(data.get("limit_usd")):
        raise ValueError("Hạn mức tự động đã lưu không hợp lệ — cần EP kiểm tra")
    return data


def _amount(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value > 0


def current_user(p, pid, *, ep=False):
    """Không tin role cũ của session; kiểm user active và dự án trước mọi callback."""
    from . import access, stage_desk
    if p.conn.execute("SELECT 1 FROM projects WHERE id=?", (pid,)).fetchone() is None:
        raise PermissionError("Không tìm thấy dự án đang mở")
    identity = access.user_of(getattr(p, "user", None))
    if identity is None:
        if stage_desk.login_on():
            raise PermissionError("Cần đăng nhập để thực hiện thao tác này")
        who = None
    else:
        row = p.conn.execute("SELECT email,role,active FROM users WHERE email=?", (identity["email"],)).fetchone()
        if row is None or not row["active"]:
            raise PermissionError("Phiên đăng nhập không còn quyền hoạt động")
        who = {"email": row["email"], "role": row["role"]}
    if ep and not stage_desk.is_executive_producer(p.conn, pid, who):
        raise PermissionError("Chỉ Executive Producer của dự án được duyệt hạn mức tự động")
    if not ep:
        access.require(p.conn, pid, who, need="view", action="mở chế độ Cơ bản")
    return who


def approve(p, pid, *, expected_total, confirmed=False):
    """EP bấm xác nhận báo giá hiện tại. Lặp cùng xác nhận là no-op; không nâng ngầm."""
    if not enabled():
        raise PermissionError("Chế độ Cơ bản chưa được bật")
    who = current_user(p, pid, ep=True)
    from . import access
    access.need_edit(p, pid, "duyệt hạn mức tự động")  # ghi app_settings/audit_log: kiểm quyền sửa như mọi hàm ghi
    if confirmed is not True:
        raise ValueError("Cần xác nhận hạn mức chi của luồng tự động")
    prop = proposal(p, pid)
    if prop.get("qd3_complete") is not True:
        raise ValueError("Đang giữ — dự toán chưa đủ mức xấu nhất và ngân sách tự sửa 40%")
    amount = prop.get("total")
    if prop.get("incomplete") or not _amount(amount):
        raise ValueError("Chưa đủ báo giá toàn phim — giữ chờ, chưa duyệt hạn mức")
    if not _amount(expected_total) or round(expected_total, 2) != round(amount, 2):
        raise ValueError("Báo giá đã đổi — xem lại và xác nhận hạn mức mới")
    conn = p.conn
    conn.execute("SAVEPOINT simple_limit")
    try:
        old = get(conn, pid)
        if old:
            if old["limit_usd"] != round(amount, 2):
                raise ValueError("Đã có hạn mức được duyệt; tăng hạn mức cần EP duyệt riêng")
            result = old
        else:
            at = datetime.now(timezone.utc).isoformat()
            email = who["email"] if who else "local"
            result = {"limit_usd": round(amount, 2), "approved_by": email, "approved_at": at,
                      "scope": "automated_only", "revision": 1}
            conn.execute("INSERT INTO app_settings(key,value) VALUES(?,?)", (_key(pid), json.dumps(result)))
            conn.execute("INSERT INTO audit_log(at,email,action,detail) VALUES(?,?,?,?)",
                         (at, email, "simple_auto_limit_approve", json.dumps({"project_id": pid, "limit_usd": result["limit_usd"]})))
        conn.execute("RELEASE simple_limit")
        return result
    except Exception:
        conn.execute("ROLLBACK TO simple_limit")
        conn.execute("RELEASE simple_limit")
        raise


def utilization(approved, *, recorded, held):
    """Cảnh báo 80%, không phải quyền gửi hay luật chặn thủ công."""
    for value in (recorded, held):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError("Chưa xác minh được số tiền đã ghi nhận / giữ chỗ")
    limit = approved["limit_usd"] if approved else None
    ratio = (recorded + held) / limit if limit else None
    return {"recorded": recorded, "held": held, "limit": limit, "ratio": ratio,
            "warning": ratio is not None and ratio >= .8}
