"""S14.18 — giới hạn theo người trên giao diện (cả v1 lẫn v2). Lõi kiểm ở core/person_limits.py; ở đây chỉ HIỆN câu chặn có số liệu và các
lựa chọn đã chốt (kế hoạch nâng cấp dashboard mục 6d):

  open   (dự án dở thứ 3)       → danh sách dự án dở (tên, bước, đã chi ≈) · GIỮ = quay lại làm dự án đó · BỎ = cất 📦 (khôi phục được)
  daily  (dự án mới thứ 3/ngày) → ô lý do + gửi yêu cầu, Owner duyệt / từ chối ở 👥 Nhóm
  parked (dự án dở thứ 2 cất)   → khôi phục dự án đang cất (đổi chỗ) · xóa hẳn một dự án dở (thùng rác như ⚙ → Xóa) · xin Owner duyệt

Chỗ hiện (`where`): 'create' (➕ Dự án mới), 'clone' (🧬 Nhân bản), 'archive' (⚙ → 📦 Cất), 'restore' (⚙ → Dự án đã cất)."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from core import archive, person_limits as PL

KEY = "limit_block"


def remember(err: "PL.LimitReached", where: str, target=None) -> None:
    st.session_state[KEY] = {"kind": err.kind, "msg": str(err), "where": where, "target": target, "pending": err.pending,
                             "projects": [dict(r) for r in err.projects]}


def clear() -> None:
    st.session_state.pop(KEY, None)
    st.session_state.pop("lim_del_ask", None)


def _p() -> Pipeline:
    return C.scoped(Pipeline(connect(C.DB)))       # a callback runs in another thread than the one that made the page's `p`


def _keep(pid: int) -> None:
    """GIỮ: back to that unfinished project, nothing new is made."""
    st.session_state["global_pid"] = pid
    clear()


def _drop(pid: int) -> None:
    """BỎ: put the unfinished project away (📦, restorable) to make room — itself checked against the 📦 limit."""
    block = st.session_state.get(KEY) or {}
    p = _p()
    try:
        if block.get("where") == "restore" and block.get("target"):
            archive.swap(p, put_away=pid, bring_back=block["target"])    # restoring: one move, never 3 open nor 2 parked in between
            st.session_state["global_pid"] = block["target"]
            st.session_state["limit_done"] = f"Đã cất dự án #{pid} và khôi phục dự án #{block['target']} (vẫn đang tạm dừng)."
        else:
            archive.archive(p, pid)
            st.session_state["limit_done"] = f"Đã cất dự án #{pid} (📦, khôi phục được) — giờ tạo được dự án mới."
        clear()
    except PL.LimitReached as e:
        remember(e, block.get("where", "create"), pid)
        st.session_state[KEY]["then"] = block                          # the 📦 limit refused the BỎ: its own choices show


def _swap(bring_back: int) -> None:
    """📦 limit: bring a put-away project back and put the target away in the same move."""
    block = st.session_state.get(KEY) or {}
    try:
        archive.swap(_p(), put_away=block["target"], bring_back=bring_back)
        st.session_state["limit_done"] = (f"Đã khôi phục dự án #{bring_back} (vẫn đang tạm dừng) và cất dự án #{block['target']}.")
        clear()
    except PL.LimitReached as e:
        remember(e, block.get("where", "archive"), block.get("target"))


def _ask_delete(pid: int) -> None:
    st.session_state["lim_del_ask"] = pid


def _delete(pid: int) -> None:
    """Xóa hẳn a put-away unfinished project: the same flow as ⚙ → 🗑 Xóa dự án (stop the run, cancel at the provider, files to the
    trash for the retention period, spend history kept)."""
    from dashboard.header import cancel_everything
    from core import autopilot
    p = _p()
    name = (p.project(pid) or {"name": "?"})["name"]
    autopilot.stop(p, pid, "Dự án bị xóa")
    report = {}
    note = cancel_everything(p, pid, report)
    st.session_state.pop("lim_del_ask", None)
    if report.get("busy"):
        st.session_state["limit_done"] = f"Chưa xóa dự án #{pid}. {note}"
        return
    p.delete_project(pid, C.DATA)
    block = st.session_state.get(KEY) or {}
    block["projects"] = [r for r in block.get("projects", []) if r["id"] != pid]
    st.session_state["limit_done"] = f"Đã xóa dự án #{pid} “{name}” (file vào thùng rác). {note}"
    if block.get("kind") == "parked" and block.get("target"):
        try:
            archive.archive(p, block["target"])
            st.session_state["limit_done"] += f" Đã cất dự án #{block['target']}."
            clear()
        except PL.LimitReached as e:
            remember(e, "archive", block["target"])


def _request(kind: str) -> None:
    block = st.session_state.get(KEY) or {}
    reason = (st.session_state.get(f"lim_reason_{kind}") or "").strip()
    try:
        rid = PL.request(_p().conn, C.access_user(), kind, reason, project_id=block.get("target") if kind == "parked" else None)
    except ValueError as e:
        st.session_state["limit_done"] = f"Chưa gửi: {e}"
        return
    block["pending"] = rid
    st.session_state["limit_done"] = (f"Đã gửi yêu cầu #{rid} tới Owner (hiện ở 📥 và 👥 Nhóm của Owner). Được duyệt thì bấm lại "
                                      + ("“Tạo dự án”." if kind == "daily" else "“📦 Cất dự án này”."))


def panel(p: Pipeline, where: str) -> None:
    """The refusal of the last action made HERE, with its numbers and choices (nothing when no limit was hit)."""
    done = st.session_state.pop("limit_done", None)
    if done:
        st.info(done)
    block = st.session_state.get(KEY)
    if not block or block.get("where") != where:
        return
    st.warning(block["msg"])
    kind = block["kind"]
    if kind == "open":
        for r in block["projects"]:
            c = st.columns([3, 1.2, 1.2], vertical_alignment="center")
            c[0].markdown(f"**#{r['id']} {escape(r['name'])}**  \n<small>{escape(r['step'])} · đã chi ≈ ${r['spent']:.2f}</small>",
                          unsafe_allow_html=True)
            c[1].button("↩ GIỮ — làm tiếp", key=f"lim_keep_{r['id']}", on_click=_keep, args=(r["id"],),
                        help="Quay lại dự án này, không tạo dự án mới")
            c[2].button("📦 BỎ — cất", key=f"lim_drop_{r['id']}", on_click=_drop, args=(r["id"],),
                        help="Cất dự án này (khôi phục được ở ⚙ → Dự án đã cất) để có chỗ")
    elif kind == "daily":
        if block.get("pending"):
            st.caption(f"Yêu cầu #{block['pending']} đang chờ Owner duyệt — sửa lý do và gửi lại nếu cần.")
        st.text_input("Lý do cần thêm dự án hôm nay", key="lim_reason_daily", placeholder="ví dụ: bản gấp cho sự kiện cuối tuần")
        st.button("📨 Gửi yêu cầu cho Owner", key="lim_req_daily", on_click=_request, args=("daily",), type="primary")
    elif kind == "parked":
        ask = st.session_state.get("lim_del_ask")
        for r in block["projects"]:
            c = st.columns([3, 1.3, 1.2], vertical_alignment="center")
            c[0].markdown(f"**#{r['id']} {escape(r['name'])}** (đang cất)  \n<small>{escape(r['step'])} · đã chi ≈ ${r['spent']:.2f}</small>",
                          unsafe_allow_html=True)
            c[1].button("↩ Khôi phục để làm", key=f"lim_swap_{r['id']}", on_click=_swap, args=(r["id"],),
                        help=f"Khôi phục dự án này và cất dự án #{block.get('target')} cùng lúc")
            if ask == r["id"]:
                c[2].button("Có, xóa hẳn", key=f"lim_del_yes_{r['id']}", on_click=_delete, args=(r["id"],), type="primary")
            else:
                c[2].button("🗑 Xóa hẳn", key=f"lim_del_{r['id']}", on_click=_ask_delete, args=(r["id"],),
                            help="Xóa dự án này (file vào thùng rác như ⚙ → Xóa dự án) để có chỗ cất")
        if block.get("pending"):
            st.caption(f"Yêu cầu #{block['pending']} đang chờ Owner duyệt.")
        st.text_input("Hoặc xin Owner cho cất thêm — lý do", key="lim_reason_parked")
        st.button("📨 Xin Owner duyệt", key="lim_req_parked", on_click=_request, args=("parked",))
    st.button("Đóng", key=f"lim_close_{where}", on_click=clear)


def usage_caption(p: Pipeline) -> None:
    """➕ Dự án mới: where the person stands before pressing (Owner / sign-in off: no limit)."""
    user = C.access_user()
    if PL.exempt(user):
        return
    lim = PL.limits(p.conn, user["email"])
    st.caption(f"Của bạn: dự án dở {len(PL.open_projects(p.conn, user['email']))}/{lim['open']} · tạo hôm nay "
               f"{len(PL.created_today(p.conn, user['email']))}/{lim['daily']} · dự án dở đang cất "
               f"{len(PL.parked_projects(p.conn, user['email']))}/{lim['parked']}")


# ---- 👥 Nhóm (Owner) -----------------------------------------------------------------------------------------------------------------
TEAM_NOTE = ("Mức cơ bản mỗi người: 2 dự án dở cùng lúc · 2 dự án tạo mới mỗi ngày · 1 dự án dở đang cất 📦 (dự án đã xong cất vào Kho "
             "dự án đã xong, không giới hạn). Owner không bị giới hạn và nâng mức riêng cho từng người ở đây. Dự án thứ 3 trong ngày / "
             "dự án dở thứ 2 muốn cất → người đó gửi yêu cầu kèm lý do; một lần duyệt = một dự án (yêu cầu ngày chỉ dùng trong ngày duyệt).")


def team_block(p: Pipeline, members: list) -> None:
    """Owner: waiting requests (Duyệt / Từ chối) and each person's limits (0…, base 2/2/1)."""
    owner = C.me()
    st.markdown("**Giới hạn dự án theo người & yêu cầu vượt mức**", help=TEAM_NOTE)
    rows = PL.requests(p.conn, limit=30)
    waiting = [r for r in rows if r["status"] == "pending"]
    if not rows:
        st.caption("Chưa có yêu cầu vượt mức nào.")
    for r in rows[:15]:
        c = st.columns([3.2, 1.6, 1, 1], vertical_alignment="center")
        c[0].markdown(f"**#{r['id']} {escape(r['email'])}** — {escape(PL.KIND_LABELS.get(r['kind'], r['kind']))}"
                      + (f" (dự án #{r['project_id']})" if r["project_id"] else "")
                      + f"  \n<small>{escape(r['requested_at'])} · lý do: {escape(r['reason'])}</small>", unsafe_allow_html=True)
        c[1].markdown(PL.STATUS_LABELS.get(r["status"], r["status"]) + (f"  \n<small>{escape(r['decided_by'] or '')}</small>"
                                                                       if r["decided_by"] else ""), unsafe_allow_html=True)
        if r["status"] != "pending":
            continue
        try:
            if c[2].button("Duyệt", key=f"lim_ok_{r['id']}", type="primary"):
                PL.approve(p.conn, owner, r["id"])
                st.rerun()
            if c[3].button("Từ chối", key=f"lim_no_{r['id']}"):
                PL.reject(p.conn, owner, r["id"])
                st.rerun()
        except (auth.AuthError, ValueError) as e:
            st.error(str(e))
    if waiting:
        st.caption(f"{len(waiting)} yêu cầu đang chờ.")
    if not members:
        return
    with st.expander("Nâng mức riêng cho từng người (cơ bản 2 · 2 · 1)", expanded=False):
        for email in members:
            lim = PL.limits(p.conn, email)
            c = st.columns([2.6, 1, 1, 1, 0.9], vertical_alignment="bottom")
            c[0].markdown(f"**{escape(email)}**" + ("" if lim == PL.BASE else "  \n<small>đã nâng</small>"), unsafe_allow_html=True)
            o = c[1].number_input("Dở cùng lúc", min_value=0, value=lim["open"], step=1, key=f"plim_open_{email}")
            d = c[2].number_input("Mới / ngày", min_value=0, value=lim["daily"], step=1, key=f"plim_daily_{email}")
            k = c[3].number_input("Dở đang cất", min_value=0, value=lim["parked"], step=1, key=f"plim_parked_{email}")
            if c[4].button("💾", key=f"plim_save_{email}", help="Lưu mức của người này (ghi nhật ký)"):
                try:
                    PL.set_limits(p.conn, owner, email, open=int(o), daily=int(d), parked=int(k))
                except (auth.AuthError, ValueError) as e:
                    st.error(str(e))
                else:
                    st.toast(f"Đã lưu giới hạn của {email}")
                    st.rerun()
