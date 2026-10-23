"""Thành phần độc lập để người có quyền ghi ngoại lệ QC vào lịch sử M4.7.

Caller truyền kết nối, project và token phiên đăng nhập hiện tại. Module không tự chạy migration, không suy danh tính từ tên/email do caller
đưa vào, và không hiển thị gì khi cờ M4.7 tắt.
"""
import hashlib
import json
import sqlite3

import streamlit as st

from core import access, auth, qc_overrides


def _widget_key(project_id: int, target_kind: str, target_ref: str) -> str:
    identity = f"{target_kind}\0{target_ref}".encode("utf-8")
    suffix = hashlib.sha256(identity).hexdigest()[:16]
    return f"qc_override_{project_id}_{suffix}"


def render_override(conn, *, project_id: int, target_kind: str, target_ref: str, error_code: str,
                    session_token: str | None, read_only: bool = False) -> None:
    """Vẽ lịch sử và form ghi revision cho một lỗi/finding/gói QC.

    Cờ OFF là no-op để giữ nguyên giao diện cũ. Token được xác minh lại ở đây cho quyền xem; `record` xác minh lại quyền edit khi ghi.
    """
    if not qc_overrides.enabled():
        return

    identity = auth.identity(conn, session_token)
    if identity is None:
        st.info("Đăng nhập lại để xem hoặc ghi lịch sử ngoại lệ QC.")
        return
    try:
        access.require(conn, project_id, identity, "view", "xem ngoại lệ QC")
    except access.AccessDenied as exc:
        st.info(str(exc))
        return

    if not qc_overrides.has_table(conn):
        st.caption("Bảng lịch sử ngoại lệ chưa được cài đặt; màn hình không tự chạy migration.")
        return
    try:
        row = qc_overrides.latest(conn, project_id, target_kind, target_ref)
    except sqlite3.Error:
        st.error("Không đọc được lịch sử ngoại lệ QC.")
        return

    with st.expander("📝 Lịch sử ngoại lệ QC", expanded=False):
        if row:
            st.caption(f"Lần ghi #{row['revision']} · {row['actor_email']} · {row['created_at']}")
            st.write(row["reason"])
            st.json(row["evidence"])
        else:
            st.caption("Chưa có ngoại lệ QC cho mục này.")

        if read_only:
            st.caption("Tài khoản hiện tại chỉ có quyền xem.")
            return

        key = _widget_key(project_id, target_kind, target_ref)
        with st.form(key=f"{key}_form", clear_on_submit=False):
            reason = st.text_area(
                "Lý do ngoại lệ",
                key=f"{key}_reason",
                max_chars=1000,
                help="Viết câu có nghĩa, tối thiểu 15 ký tự. Mỗi lần ghi tạo một revision mới.",
            )
            evidence_text = st.text_area(
                "Bằng chứng (JSON)",
                value="{}",
                key=f"{key}_evidence",
                max_chars=16_384,
                help='Ví dụ: {"type":"manual_review","ref":"qc/frame-3.png","sha256":"…"}',
            )
            submitted = st.form_submit_button("Ghi ngoại lệ", disabled=len((reason or "").strip()) < 15)

        if not submitted:
            return
        try:
            evidence = json.loads(evidence_text or "")
        except (TypeError, json.JSONDecodeError):
            st.error("Bằng chứng phải là JSON hợp lệ dạng đối tượng.")
            return
        if not isinstance(evidence, dict) or not evidence:
            st.error("Cần nhập bằng chứng có cấu trúc, không để trống.")
            return
        try:
            qc_overrides.record(
                conn,
                project_id=project_id,
                target_kind=target_kind,
                target_ref=target_ref,
                error_code=error_code,
                session_token=session_token,
                reason=reason,
                evidence=evidence,
            )
        except (ValueError, access.AccessDenied, qc_overrides.OverrideConflict, qc_overrides.OverrideDisabled) as exc:
            st.error(str(exc))
            return
        except sqlite3.Error:
            st.error("Không ghi được ngoại lệ QC vào CSDL.")
            return
        st.success("Đã ghi revision ngoại lệ QC.")
        st.rerun()
