"""Đăng nhập admin phía server cho AI Dev System 8502 (trang Phiếu).

Dùng CHUNG bảng users / sessions của CSDL pipeline (`PIPELINE_DB`, mặc định data/manifest.sqlite) với Dashboard 8501:
  * Đăng nhập trên 8502 đi qua đúng một cửa của Dashboard (`core.machine_auth.sign_in` → `core.auth.login`): Owner từ máy khác cần mã
    Owner / bị chặn theo DASHBOARD_OWNER_LOCAL_ONLY, thành viên qua LAN cần máy đã duyệt, mọi lần đăng nhập ghi audit.
  * Phiên Dashboard đã có dùng được ở 8502 bằng liên kết `?s=<token>` (token phiên, không phải e-mail) — Owner chỉ từ chính máy chạy.
  * Danh tính đọc lại TỪ CSDL ở mỗi lần chạy trang (`auth.identity`), không tin role/email nào trong session_state hay trình duyệt.
  * Chỉ Owner được thao tác ghi phiếu; người khác vẫn xem chỉ đọc.
"""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st

from core import auth

TOKEN_KEY = "devsys_auth_token"
PENDING_KEY = "devsys_pending_link"        # token từ ?s= đã gỡ khỏi địa chỉ ngay đầu app (devsys/app.py take_link)
WRITE_TIMEOUT_S = 10


def db_path() -> Path:
    path = Path(os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    return path.resolve()


@contextmanager
def read_connection():
    conn = sqlite3.connect(db_path().as_uri() + "?mode=ro", uri=True, timeout=2)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def write_connection():
    """Kết nối GHI chỉ mở sau khi đã có Owner xác thực (hoặc để đăng nhập). Không migrate: CSDL chưa có bảng thì báo lỗi, không tạo."""
    path = db_path()
    if not path.exists():
        raise sqlite3.OperationalError(f"không có CSDL {path}")
    conn = sqlite3.connect(str(path), timeout=WRITE_TIMEOUT_S)   # Dashboard giữ khóa ghi lâu → báo lỗi sau 10 s, không treo trang
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def request_source() -> Tuple[str, bool]:
    """(nguồn cho audit, có phải chính máy chạy 8502 không) — cùng luật với dashboard/common.request_source: địa chỉ kết nối quyết định,
    header Host chỉ được tin khi Streamlit không cho địa chỉ (trình duyệt trên chính máy / test)."""
    try:
        host = st.context.headers.get("Host", "") or ""
        ip = st.context.ip_address or ""
    except Exception:  # noqa: BLE001 - Streamlit cũ / AppTest: không rõ nguồn → coi như máy này
        return "devsys", True
    if not isinstance(ip, str):
        ip = ""
    if ip:
        local = ip.strip("[]") in ("127.0.0.1", "::1") or ip.startswith("::ffff:127.")
    else:
        local = host.split(":")[0].strip("[]") in ("localhost", "127.0.0.1", "::1", "")
    return f"devsys host={host} ip={ip}", local


def _ip() -> str:
    try:
        ip = st.context.ip_address
    except Exception:  # noqa: BLE001
        return ""
    return ip if isinstance(ip, str) else ""


def take_link() -> None:
    """Gọi ở ĐẦU devsys/app.py cho mọi trang: gỡ token `?s=` khỏi địa chỉ ngay (không để nằm lại trên thanh địa chỉ / lịch sử),
    giữ tạm phía server cho current() xét."""
    linked = st.query_params.get("s")
    if linked:
        st.session_state[PENDING_KEY] = linked
        st.query_params.pop("s", None)


def current() -> Optional[auth.Identity]:
    """Người đang đăng nhập 8502 (đọc lại từ CSDL), hoặc None. Liên kết `?s=` từ Dashboard được xét một lần; phiên Owner qua liên kết
    chỉ nhận trên chính máy chạy (như Dashboard)."""
    take_link()
    token = st.session_state.get(TOKEN_KEY)
    linked = st.session_state.pop(PENDING_KEY, None)
    ident = None
    try:
        with read_connection() as conn:
            ident = auth.identity(conn, token) if token else None
            if ident is None and linked:
                by_link = auth.identity(conn, linked)
                if by_link is not None and not (by_link.role == "owner" and not request_source()[1]):
                    st.session_state[TOKEN_KEY] = linked
                    ident = by_link
    except (sqlite3.Error, OSError, ValueError):
        ident = None
    if ident is None:
        st.session_state.pop(TOKEN_KEY, None)
    return ident


def is_owner(ident: Optional[auth.Identity]) -> bool:
    return ident is not None and ident.role == "owner"


def sign_in(email: str, passcode: Optional[str] = None) -> Optional[str]:
    """Đăng nhập Owner qua cửa chung của Dashboard. Trả lỗi (chuỗi) hoặc None khi vào được.
    8502 chỉ dành cho Owner: e-mail khác bị từ chối TRƯỚC khi chạm CSDL (không tự tạo thành viên, không tự duyệt máy). Owner từ máy khác
    luôn cần mã Owner (DASHBOARD_OWNER_PASSCODE) — kể cả khi 8502 bị chạy tay mở ra mạng mà không nạp dashboard.env."""
    from core import machine_auth
    try:
        email = auth.normalize_email(email)
    except auth.AuthError as e:
        return str(e)
    if email != auth.OWNER_EMAIL:
        return "8502 chỉ cho Owner đăng nhập để duyệt phiếu; người khác xem chỉ đọc."
    source, local = request_source()
    if not local and not os.environ.get("DASHBOARD_OWNER_PASSCODE", "").strip():
        return ("Owner đăng nhập 8502 từ máy khác cần mã Owner — đặt DASHBOARD_OWNER_PASSCODE trong dashboard.env "
                "(hoặc mở 8502 trên chính máy chạy).")
    try:
        with write_connection() as conn:
            st.session_state[TOKEN_KEY] = machine_auth.sign_in(conn, email, _ip(), local, source, passcode)
    except machine_auth.MachinePending as e:
        return str(e)
    except auth.AuthError as e:
        return str(e)
    except (sqlite3.Error, OSError) as e:
        return f"không mở được CSDL để đăng nhập: {e}"
    return None


def sign_out() -> None:
    token = st.session_state.pop(TOKEN_KEY, None)
    if token:
        try:
            with write_connection() as conn:
                auth.logout(conn, token)
        except (sqlite3.Error, OSError):
            pass


def login_box(key: str = "devsys_login") -> None:
    """Ô đăng nhập gọn đặt ngay trên trang cần quyền admin (chỉ Owner)."""
    local = request_source()[1]
    with st.form(key):
        email = st.text_input("E-mail Owner", placeholder="ten@garena.vn")
        passcode = None if local else st.text_input("Mã Owner (đăng nhập từ máy khác)", type="password")
        if st.form_submit_button("Đăng nhập để duyệt", type="primary"):
            error = sign_in(email, passcode)
            if error:
                st.error(error)
            else:
                st.rerun()
    st.caption("Cùng tài khoản Owner của Dashboard 8501. Đã đăng nhập Dashboard thì mở 8502 bằng liên kết có `?s=` cũng được (chỉ trên máy chạy).")
