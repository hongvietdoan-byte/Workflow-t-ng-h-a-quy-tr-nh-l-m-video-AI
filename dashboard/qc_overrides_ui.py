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

        if read_only or not access.can_edit(conn, project_id, identity):
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
            # Inputs inside a form reach Python only on submit; disabling based on the old
            # reason would lock a freshly opened form forever. Core validates every submit.
            submitted = st.form_submit_button("Ghi ngoại lệ")

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


def target_ref(kind: str, snapshot) -> str:
    """Identity of the exact finding/revision, never merely a reusable QC code."""
    raw = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return kind + ":" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def image_force_hold() -> bool:
    """Q6(a): fail closed until the image runner has a verified, side-effect-free package preview.

    Seeing scene data is not evidence that the human opened the actual provider package.
    OFF leaves the existing checkbox and legacy behavior unchanged.
    """
    if not qc_overrides.enabled():
        return False
    st.caption("Q6(a): chưa có thẻ gói ảnh dựng khô an toàn; tạm khóa ‘vẫn gen’. Sửa cổng trước khi gen; không gọi API để xem trước.")
    return True


def continuity_snapshot(data_dir, project_id):
    """Read the existing sequence-QC source, without changing the core cache/owner's API.

    The cached card drops run/channel provenance. Missing, malformed or oversized sources
    therefore keep continuity findings view-only instead of inventing a revision.
    """
    from core import continuity_shadow
    try:
        with open(continuity_shadow.result_path(data_dir, project_id), "rb") as source:
            raw = source.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            return None
        value = json.loads(raw)
        return value if isinstance(value, dict) else None
    except (OSError, ValueError, TypeError):
        return None


def render_findings(conn, project_id: int, job_id: int, result, *, session_token, read_only=False, continuity_snapshot=None):
    """Project-local QC ledger: annotate exact source/run/finding, without altering QC or submitting jobs."""
    if not qc_overrides.enabled():
        return
    identity = auth.identity(conn, session_token)
    if identity is None or not access.can_view(conn, project_id, identity):
        return
    st.caption("Sổ lỗi QC: ngoại lệ chỉ ghi lịch sử cho đúng finding/revision; không đổi kết luận QC hay tự gửi job.")
    sources = []
    for source in ("video", "evidence"):
        for run in result.get(source) or []:
            for finding in run.get("findings") or []:
                sources.append((source, run, finding))
    for finding in result.get("continuity") or []:
        matched = False
        if (isinstance(continuity_snapshot, dict)
                and type(continuity_snapshot.get("project_id")) is int
                and continuity_snapshot["project_id"] == project_id
                and isinstance(continuity_snapshot.get("at"), str) and continuity_snapshot["at"].strip()
                and continuity_snapshot.get("qc_version")):
            for channel in ("expected", "observed"):
                entries = continuity_snapshot.get(channel)
                if isinstance(entries, list) and finding in entries:
                    try:
                        revision = target_ref("sequence", continuity_snapshot)
                    except (ValueError, TypeError):
                        continue
                    sources.append(("continuity." + channel, {"snapshot": revision}, finding))
                    matched = True
        if not matched:
            st.caption("Logic xuyên shot: thiếu snapshot nguồn khớp finding; chỉ xem, chưa cho ghi ngoại lệ.")
    seen = set()
    for source, run, finding in sources:
        if not isinstance(finding, dict) or not isinstance(finding.get("qc_code"), str) or not finding["qc_code"].strip():
            continue
        ref = target_ref("finding", {"job": job_id, "source": source, "run": run, "finding": finding})
        if ref in seen:
            continue
        seen.add(ref)
        st.write(f"{finding['qc_code']} · {finding.get('severity') or 'chưa có mức'} · {finding.get('why') or 'chưa có lý do'}")
        render_override(conn, project_id=project_id, target_kind="finding", target_ref=ref,
                        error_code=finding["qc_code"], session_token=session_token, read_only=read_only)


def render_project(conn, project_id: int, *, session_token, read_only=False):
    """BYĐ and Q6(c) on both script compositions; no implicit migration or content editing.

    Q6(c) remains REVIEW as instructed in the main session's 23/10 reply; the existing lock callback is unchanged.
    """
    if not qc_overrides.enabled():
        return
    identity = auth.identity(conn, session_token)
    if identity is None or not access.can_view(conn, project_id, identity):
        return
    with st.expander("📋 BYĐ / ngoại lệ QC (0 USD)", expanded=False):
        st.caption("Chỉ đọc BYĐ đang lưu. Ghi ngoại lệ không sửa BYĐ, không duyệt ảnh, không gọi dịch vụ.")
        try:
            rows = conn.execute("SELECT id,idx,data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall()
            gate = qc_overrides.character_anchor_gate(conn, project_id)
        except (sqlite3.Error, ValueError, TypeError):
            st.warning("Không đọc được BYĐ / cổng ảnh mốc; chưa có kết luận kiểm tra.")
            return
        for message in gate["review"] + gate["warn"]:
            st.warning(message)
        for finding in gate["block"]:
            st.warning("REVIEW Q6(c): " + finding["message"] + " Quy tắc chặn cứng còn chờ EP; không chặn nút Duyệt & khóa.")
            render_override(conn, project_id=project_id, target_kind=finding["target_kind"], target_ref=finding["target_ref"],
                            error_code=finding["error_code"], session_token=session_token, read_only=read_only)
        for finding in gate["overridden"]:
            st.caption(f"Q6(c): {finding['name']} · đã ghi ngoại lệ revision {finding['revision']} cho tập BYĐ hiện tại.")
        if not rows:
            st.caption("Chưa có shot BYĐ.")
            return
        choices = {row["id"]: row for row in rows}
        sid = st.selectbox("Shot BYĐ", list(choices), format_func=lambda value: f"Shot {choices[value]['idx']}",
                           key=f"qc_byd_shot_{project_id}")
        opened = f"qc_byd_visible_{project_id}"
        if st.button("Mở BYĐ hiện tại", key=f"qc_byd_open_{project_id}_{sid}"):
            st.session_state[opened] = sid
        if st.session_state.get(opened) != sid:
            return
        try:
            data = json.loads(choices[sid]["data"] or "{}")
            byd = data.get("byd") if isinstance(data, dict) else None
        except (TypeError, ValueError):
            byd = None
        if not isinstance(byd, dict):
            st.warning("Shot chưa có BYĐ hợp lệ; không tạo ngoại lệ cho dữ liệu thiếu.")
            return
        st.json(byd)
        render_override(conn, project_id=project_id, target_kind="byd", target_ref=target_ref("byd", {"scene": sid, "byd": byd}),
                        error_code="BYD_MANUAL_REVIEW", session_token=session_token, read_only=read_only)
