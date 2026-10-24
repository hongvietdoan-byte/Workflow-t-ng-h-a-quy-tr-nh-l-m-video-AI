"""👥 Nhóm (đợt 3, 01/10) — Owner / người có quyền "Theo dõi hiệu suất": ai làm gì, tốn bao nhiêu, ai được làm gì.

Reads what already exists (core/perf.by_user, core/auth users + audit log) and adds: money per person (core/team.spend_by_user), a soft
monthly limit (warning only), role presets (core/team.ROLES over the 5 permissions), invite by e-mail. Only the Owner changes people."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import access_ui, common as C, limits_ui
from contextlib import ExitStack
import os
from typing import Optional
import pandas as pd

from core import access, crew, features, handoff, perf, team
from dashboard import common
from dashboard.design import components as D
from dashboard.design.screens.v2_tables import Raw, table

NOTE = ("Số liệu theo e-mail đăng nhập (đăng nhập tắt: theo tên tự khai). “Tiền chi” = ảnh + video + âm thanh có giá của job người đó gửi; "
        "tiền gọi Claude không gắn với người. **Hạn mức chỉ để cảnh báo** (hiện ở hộp 📥 của Owner khi ≥ 90 %), không chặn gửi — chặn thật là "
        "trần đợt thử và ngân sách khóa của dự án.")
ACCESS_NOTE = ("Mỗi người chỉ thấy dự án DO CHÍNH HỌ TẠO. Owner thấy và làm được mọi dự án. Thêm người vào danh sách theo dõi của một dự án để họ "
               "thấy dự án đó: “Chỉ xem” (nút ghi bị khóa) hoặc “Được sửa” (duyệt, gen, sửa như chủ; không cất / xóa). Dự án cũ chưa có chủ "
               "chỉ Owner thấy cho tới khi gán chủ ở đây. Chủ dự án cũng đổi được danh sách này ở ⚙ → Dự án → “Người theo dõi dự án”.")
PERIODS ={"Hôm nay": 1, "7 ngày": 7, "30 ngày": 30, "Tất cả": None}
FILTERS = {"": "Tất cả", "over": "⚠ Gần hết hạn mức", "inact": "💤 Không hoạt động > 3 ngày", "owner": "Owner", "worker": "Người làm",
           "reviewer": "Người duyệt", "manager": "Quản lý", "custom": "Tùy chỉnh"}
TICKET_FLAG = "crew_error_tickets"


def ticket_screen_visible(p: Pipeline, pid: int) -> bool:
    """EP dự án được mở màn Nhóm khi M6.10 bật, không cấp quyền xem số liệu nhóm."""
    return features.on(TICKET_FLAG) and access.level(p.conn, pid, p.user) == "ep"


def _role_name(role_id: str, role_names: dict) -> str:
    return role_names.get(role_id) or ("Director" if role_id == "director" else role_id or "—")


def _ticket_rows(records: list, registry: dict) -> list:
    roles = registry.get("roles") or []
    role_names = {role.get("id"): role.get("name") or role.get("id") for role in roles if role.get("id")}
    out = []
    for record in records:
        evidence = record.get("qc_evidence") or []
        if not evidence:
            continue
        codes = [str(item.get("id")) for item in evidence if item.get("id")]
        first_evidence = evidence[0] if evidence else {}
        owner = crew.owner_of_error(qc_code=codes[0] if codes else None, layer=first_evidence.get("layer"), reg=registry)
        cannot_fix = owner.get("owner_cannot_fix")
        cannot_fix_label = "Có" if cannot_fix is True else "Không" if cannot_fix is False else "Chưa rõ"
        source = "; ".join(str(item.get("path") or item.get("id") or "") for item in evidence) or "—"
        out.append({
            "handoff_id": record.get("handoff_id", ""),
            "scene_id": record.get("scene_id"),
            "shot_no": record.get("shot_no"),
            "qc_codes": codes,
            "status": record.get("approval_state") or "Chưa có trạng thái",
            "owner_id": owner.get("owner") or "director",
            "owner": _role_name(owner.get("owner") or "director", role_names),
            "assigned_id": record.get("to_role") or "",
            "assigned": _role_name(record.get("to_role") or "", role_names),
            "fallback": owner.get("via") == "fallback",
            "owner_cannot_fix": cannot_fix_label,
            "owner_note": owner.get("note") or "",
            "source": source,
            "reason": record.get("reason") or "",
            "record": record,
        })
    return out


def _transfer_ticket(p: Pipeline, pid: int, ticket: dict, target_role: str, reason: str,
                     data_dir: str, registry: dict) -> None:
    if not features.on(TICKET_FLAG):
        raise handoff.HandoffInputError("Cờ crew_error_tickets đang TẮT; không chuyển phiếu.")
    access.need_edit(p, pid, "gán hoặc chuyển vai phiếu lỗi")
    if access.level(p.conn, pid, p.user) not in ("ep", "admin"):
        raise access.AccessDenied("Chỉ Executive Producer của dự án hoặc người có quyền quản trị dự án được gán / chuyển vai phiếu lỗi.")
    clean_reason = (reason or "").strip()
    if not clean_reason:
        raise handoff.HandoffInputError("Cần ghi lý do trước khi gán hoặc chuyển vai.")
    if len(clean_reason) > 1000:
        raise handoff.HandoffInputError("Lý do không được dài quá 1000 ký tự.")
    row = ticket["record"]
    if row.get("project_id") != pid:
        raise handoff.HandoffInputError("Phiếu không thuộc dự án đang mở.")
    role_ids = {role.get("id") for role in (registry.get("roles") or []) if role.get("id")}
    if target_role not in role_ids:
        raise handoff.HandoffInputError("Vai nhận không có trong Role Registry.")
    if not handoff.enabled():
        raise handoff.HandoffInputError("Cờ crew_handoff_shadow đang TẮT; không ghi phiếu.")
    saved = handoff.record(
        data_dir=data_dir, project_id=pid, scene_id=row["scene_id"], shot_no=row["shot_no"],
        from_role=row["to_role"], to_role=target_role, revision=row["revision"],
        dependencies=row["dependencies"], products=row["products"], qc_evidence=row["qc_evidence"],
        approval_state=row["approval_state"], handoff_id=row["handoff_id"], reason=clean_reason,
    )
    if saved is None:
        raise handoff.HandoffInputError("Cờ crew_handoff_shadow vừa TẮT; phiếu chưa được ghi.")


def error_tickets_panel(p: Pipeline, pid: int, data_dir: Optional[str] = None) -> None:
    """M6.10 phiếu theo vai; cờ OFF không vẽ UI, không đọc registry hay shadow JSONL."""
    if not features.on(TICKET_FLAG):
        return
    access.need_view(p, pid, "xem phiếu lỗi theo vai")
    data_root = os.path.abspath(data_dir or common.DATA)
    st.divider()
    st.subheader("🧭 Phiếu lỗi theo vai")
    missing = [name for name in ("crew_registry", handoff.FLAG) if not features.on(name)]
    if missing:
        st.info("M6.10 chưa đọc phiếu: cần bật rõ các cờ " + ", ".join(f"`{name}`" for name in missing) + ".")
        return
    try:
        registry = crew.load()
        records = handoff.list_for_project(data_root, pid)
    except (OSError, ValueError, handoff.HandoffInputError) as exc:
        st.error(f"Không đọc được phiếu M6.2: {exc}")
        return

    tickets = _ticket_rows(records, registry)
    role_ids = sorted({r["owner_id"] for r in tickets} | {r["assigned_id"] for r in tickets} |
                      {role.get("id") for role in (registry.get("roles") or []) if role.get("id")})
    status_values = sorted({str(r["status"]) for r in tickets})
    shot_values = sorted({r["shot_no"] for r in tickets if isinstance(r["shot_no"], int)})
    role_filter, shot_filter, status_filter = st.columns(3)
    selected_role = role_filter.selectbox(
        "Lọc vai", ["Tất cả", *role_ids], format_func=lambda key: "Tất cả" if key == "Tất cả" else _role_name(key, {
            role.get("id"): role.get("name") or role.get("id") for role in (registry.get("roles") or []) if role.get("id")
        }), key="m610_filter_role",
    )
    selected_shot = shot_filter.selectbox("Lọc shot", ["Tất cả", *shot_values], key="m610_filter_shot")
    selected_status = status_filter.selectbox("Lọc trạng thái", ["Tất cả", *status_values], key="m610_filter_status")
    shown = [ticket for ticket in tickets
             if (selected_role == "Tất cả" or selected_role in (ticket["owner_id"], ticket["assigned_id"]))
             and (selected_shot == "Tất cả" or selected_shot == ticket["shot_no"])
             and (selected_status == "Tất cả" or selected_status == ticket["status"])]
    if not tickets:
        st.info("Chưa có phiếu M6.2 cho dự án này.")
        return
    st.dataframe(pd.DataFrame([{
        "Vai chủ": ticket["owner"] + (f" · fallback {ticket['owner']}" if ticket["fallback"] else ""),
        "Vai nhận": ticket["assigned"], "Mã QC": ", ".join(ticket["qc_codes"]) or "—",
        "Shot": ticket["shot_no"], "Trạng thái": ticket["status"], "Nguồn bằng chứng": ticket["source"],
        "owner_cannot_fix": ticket["owner_cannot_fix"],
    } for ticket in shown]), hide_index=True, width="stretch")
    if not shown:
        st.info("Không có phiếu nào khớp bộ lọc.")
    role_names = {role.get("id"): role.get("name") or role.get("id") for role in (registry.get("roles") or []) if role.get("id")}
    for ticket in shown:
        ticket_id = ticket["handoff_id"]
        title = f"Shot {ticket['shot_no']} · {', '.join(ticket['qc_codes']) or ticket_id} · {ticket['assigned']}"
        with st.expander(title, key=f"m610_ticket_{ticket_id}"):
            if ticket["owner_note"]:
                st.caption(ticket["owner_note"])
            st.caption(f"Nguồn bằng chứng: {ticket['source']} · owner_cannot_fix: {ticket['owner_cannot_fix']}")
            if ticket["reason"]:
                st.caption(f"Lý do gần nhất: {ticket['reason']}")
            options = sorted(set(role_ids) | {ticket["assigned_id"]})
            current = ticket["assigned_id"]
            target = st.selectbox(
                "Gán / chuyển vai", options, index=options.index(current) if current in options else 0,
                format_func=lambda key: _role_name(key, role_names), key=f"m610_assign_{ticket_id}",
            )
            reason = st.text_area("Lý do (bắt buộc)", max_chars=1000, key=f"m610_reason_{ticket_id}")
            if st.button("Gán / chuyển vai", key=f"m610_transfer_{ticket_id}",
                         disabled=not reason.strip() or target == current, type="primary"):
                try:
                    _transfer_ticket(p, pid, ticket, target, reason, data_root, registry)
                    st.rerun()
                except (handoff.HandoffInputError, OSError) as exc:
                    st.error(str(exc))


def people_rows(p: Pipeline, days) -> list:
    """One row per person: the user table joined with what they sent (by e-mail; sign-in off → names typed by hand)."""
    conn = p.conn
    users = {u["email"]: u for u in auth.list_users(conn)}
    sent = {r["who"]: r for r in perf.by_user(conn, days)}
    money = team.spend_by_user(conn, days)
    month = team.spend_by_user(conn, 30, since_baseline=True)   # thanh theo người tôn trọng mốc 0 Owner đã đặt
    keys = list(users) + [k for k in sent if k not in users]
    out = []
    for k in keys:
        u = users.get(k)
        s = sent.get(k) or {}
        lim = team.get_limit(conn, k) if u else None
        last = (s.get("last_at") or "")[:16].replace("T", " ")
        inactive = not last or last < (__import__("datetime").datetime.now() - __import__("datetime").timedelta(days=3)).strftime("%Y-%m-%d %H:%M")
        out.append({"who": k, "user": u, "role": team.role_label(u) if u else "(không có tài khoản)",
                    "role_key": ("owner" if u and u["role"] == "owner" else team.role_of(u["perms"]) if u else ""),
                    "videos_ok": s.get("videos_ok", 0), "videos": s.get("videos", 0), "failed": s.get("videos_failed", 0),
                    "retry": s.get("videos_retry", 0), "seconds": s.get("seconds", 0), "images": s.get("images", 0),
                    "projects": s.get("projects", 0), "last": last or (u or {}).get("last_login") or "—",
                    "usd": money.get(k, 0.0), "month_usd": month.get(k, 0.0), "limit": lim, "share": (month.get(k, 0.0) / lim) if lim else None, "inactive": inactive})
    return out


def _hero(slot, rows: list, period: str) -> None:
    with slot:
        with D.hero("team"):
            st.markdown(D.hero_html("Nhóm", "Ai làm gì, tốn bao nhiêu, ai được làm gì."), unsafe_allow_html=True)
            sc = st.columns(3)
            sc[0].markdown(D.stat("Số người", str(len(rows)), f"{sum(1 for r in rows if r['user'])} có tài khoản"), unsafe_allow_html=True)
            sc[1].markdown(D.stat(f"Video xong · {period}", str(sum(r["videos_ok"] for r in rows)),
                                  f"{sum(r['videos'] for r in rows)} đã gửi · {sum(r['failed'] for r in rows)} lỗi"), unsafe_allow_html=True)
            sc[2].markdown(D.stat(f"Tiền chi · {period}", f"{sum(r['usd'] for r in rows):.2f} USD", "ảnh + video + âm thanh có giá"),
                           unsafe_allow_html=True)


def _money_cell(r: dict) -> Raw:
    html = f"<b>{r['usd']:.2f}</b> USD"
    if r["limit"]:
        html = f'<div class="team-money"><small>{r.get("month_usd", r["usd"]):.2f} USD / 30 ngày · hạn mức {r["limit"]:g}/tháng</small>' + D.meter(
            r["share"] or 0.0, invert=True) + "</div>"
        if (r["share"] or 0) >= team.LIMIT_WARN:
            html += D.pill("gần hết hạn mức", "bad")
    return Raw(html)


def _people_table(shown: list) -> None:
    kinds = {"owner": "info", "worker": "mute", "reviewer": "ok", "manager": "warn", "custom": "mute"}
    who = lambda r: Raw(f'<span class="team-who" title="{escape(r["who"])}">{escape(r["who"])}</span>')   # noqa: E731
    role = lambda r: Raw(D.pill(r["role"], kinds.get(r["role_key"], "mute")))                              # noqa: E731
    # P1/P2: who, role, videos done / sent, money (+ limit bar); the rare columns are one click away in the labelled expander below
    st.markdown(table(["Người dùng", "Vai", "Video (xong / gửi)", "Tiền chi"],
                      [(who(r), role(r), f"{r['videos_ok']} / {r['videos']}", _money_cell(r)) for r in shown],
                      cls="team-table", num_cols=(2,), empty="Không có ai khớp bộ lọc"), unsafe_allow_html=True)
    with st.expander("📋 Chi tiết từng người — lỗi · gen lại, giây video, ảnh, dự án, lần gần nhất", expanded=False):
        st.markdown(table(["Người dùng", "Lỗi · Gen lại", "Giây video", "Ảnh", "Dự án", "Gần nhất"],
                          [(who(r), f"{r['failed']} · {r['retry']}", f"{r['seconds']:g}", r["images"], r["projects"], r["last"]) for r in shown],
                          cls="team-table", num_cols=(1, 2, 3, 4), empty="Không có ai khớp bộ lọc"), unsafe_allow_html=True)


def _history_v2(log, gens) -> None:
    state_kind = {"succeeded": "ok", "failed": "bad", "running": "info", "queued": "mute"}
    c_a, c_b = st.columns(2)
    with c_a, D.card("team-audit"):
        st.markdown("**Nhật ký quyền**")
        st.markdown(table(["Lúc", "Ai", "Việc", "Chi tiết"], [(r["at"], r["email"], r["action"], r["detail"]) for r in log],
                          cls="team-table", empty="Chưa có thay đổi quyền nào"), unsafe_allow_html=True)
    with c_b, D.card("team-gens"):
        st.markdown("**Lượt gen gần đây**")
        st.markdown(table(["Lúc", "Ai", "Loại", "Dự án", "Trạng thái"],
                          [((r["created_at"] or "")[:16].replace("T", " "), r["who"], "video" if r["type"] == "video_gen" else "ảnh", r["name"],
                            Raw(D.pill(r["state"], state_kind.get(r["state"], "mute")))) for r in gens],
                          cls="team-table", empty="Chưa có lượt gen nào"), unsafe_allow_html=True)


def _usd(x) -> str:
    return f"{float(x or 0):.2f} USD"


def user_reset_block(p: Pipeline, actor: dict, rows: list, v2: bool) -> None:
    """Owner-only "↺ Đặt lại" of one person's monthly money bar (core.money_reset bar `user`). One row per person with the bar now and a
    button; the button opens a panel with a REQUIRED reason and a yes/no question that states the number before → after. The ledger is
    never touched and the personal limit stays a warning (hiding this is a convenience: core.money_reset refuses anyone but the Owner)."""
    from core import money_reset
    if actor.get("role") != "owner":
        return
    people = [r["who"] for r in rows if r["user"] or r["usd"]]
    ss = st.session_state
    target = ss.get("team_mr_target")
    if target not in people:
        target = ss["team_mr_target"] = None
    done = ss.get("team_mr_done")
    with st.expander("↺ Đặt lại thanh tiền của từng người (chỉ Owner)", expanded=bool(target or done)):
        st.caption("Thanh tháng của người đó đếm lại từ bây giờ; sổ chi giữ nguyên, mỗi lần đặt lại được ghi nhật ký kèm lý do. "
                   "Hạn mức cá nhân vẫn chỉ cảnh báo.")
        if done:
            if "user" in done:
                u = done["user"]
                st.success(f"Đặt mốc 0 cho {u.get('email', '?')}: thanh trước đó ${float(u.get('before_usd') or 0):.2f} (ước tính) → 0 "
                           f"từ {u.get('since', '?')} UTC (mốc cũ: {u.get('old_since') or 'không có'}). Sổ chi giữ nguyên.")
            else:
                st.success(f"Bỏ mốc 0 của {done.get('email', '?')} (mốc cũ {done.get('old_since')}): thanh "
                           f"${float(done.get('before_usd') or 0):.2f} → ${float(done.get('after_usd') or 0):.2f} (ước tính, đủ 30 ngày). "
                           "Sổ chi giữ nguyên.")
            ss["team_mr_done"] = None
        for who in people:
            bar = money_reset.user_bar(p.conn, who)
            rec = money_reset.last(p.conn, "user", who)
            c = st.columns([3, 2.4, 1.3], vertical_alignment="center")
            c[0].markdown(f"<b>{escape(who)}</b>" + (f"  \n<small>đặt lại lần cuối {escape(str(rec.get('at', '')))} bởi "
                                                   f"{escape(str(rec.get('who', '?')))} — {escape(str(rec.get('why', '')))}</small>"
                                                   if rec else ""), unsafe_allow_html=True)
            c[1].markdown(f"{_usd(bar['month_usd'])} / 30 ngày" + (f"  \n<small>hạn mức {bar['limit']:g} USD</small>" if bar["limit"] else ""),
                          unsafe_allow_html=True)
            if c[2].button("↺ Đặt lại", key=f"team_mr_{who}", help="Đếm lại thanh tiền tháng của người này từ bây giờ (cần lý do).",
                           type="primary" if who == target else "secondary"):
                ss["team_mr_target"] = who
                st.rerun()
        if not target:
            return
        bar = money_reset.user_bar(p.conn, target)
        with (D.card("team-mr") if v2 else st.container(border=True)):
            st.markdown(f"<b>Đặt lại thanh của {escape(target)}</b> — hiện {_usd(bar['month_usd'])} → sau khi đặt lại 0.00 USD "
                        "(chỉ tính từ các lượt gen sau bây giờ).", unsafe_allow_html=True)
            why = (st.text_input("Lý do (bắt buộc)", key=f"team_mr_why_{target}",
                                 placeholder="ví dụ: sang tháng mới, đã nạp thêm tiền") or "").strip()
            if not why:
                st.caption("Cần nhập lý do.")
            ids = (target, why) if why else ()
            if C.confirm_all(f"team_mr_go_{target}", ids, "↺ Đặt lại thanh này",
                             f"Đặt lại thanh của {target}? Đang {_usd(bar['month_usd'])} → 0.00 USD. Sổ chi giữ nguyên. Lý do: {why}",
                             st, "Có, đặt lại"):
                try:
                    res = money_reset.reset(p.conn, actor, ["user"], why, email=target)
                except Exception as e:  # noqa: BLE001 - shown, never a crash of the screen
                    st.error(f"Không đặt lại được: {e}")
                    return
                ss["team_mr_done"] = res
                ss["team_mr_target"] = None
                st.rerun()
            if bar["since"]:                # bỏ mốc: the bar counts the full 30 days again (core.money_reset.clear_user, Owner only)
                if C.confirm_all(f"team_mr_clear_{target}", ids, f"⊘ Bỏ mốc 0 ({bar['since']})",
                                 f"Bỏ mốc 0 của {target} (đặt lúc {bar['since']} UTC)? Thanh sẽ tính đủ 30 ngày như chưa đặt lại. "
                                 f"Sổ chi giữ nguyên. Lý do: {why}", st, "Có, bỏ mốc"):
                    try:
                        res = money_reset.clear_user(p.conn, actor, target, why)
                    except Exception as e:  # noqa: BLE001 - shown, never a crash of the screen
                        st.error(f"Không bỏ mốc được: {e}")
                        return
                    ss["team_mr_done"] = res
                    ss["team_mr_target"] = None
                    st.rerun()
            if st.button("Đóng", key="team_mr_close"):
                ss["team_mr_target"] = None
                st.rerun()


MACHINE_NOTE = ("Chỉ áp khi Dashboard mở cho mạng LAN (DASHBOARD_LAN=1). Thành viên chỉ đăng nhập được từ máy PC Owner đã duyệt cho e-mail đó "
                "(một người có thể có nhiều máy). Máy nhận qua DNS nội bộ (tên tra ngược từ IP, kiểm lại chiều thuận); không xác định được "
                "tên máy → bị từ chối kèm lý do. Owner: trên máy chạy Dashboard như cũ, từ máy khác cần mã Owner. **Lưu ý:** reverse proxy "
                "/ tunnel chạy trên cùng máy làm mọi người trông như đến từ máy chủ — đừng đặt Dashboard sau proxy khi dựa vào lớp này.")
MACHINE_STATUS = {"pending": "⏳ chờ duyệt", "approved": "✅ đã duyệt", "rejected": "⛔ từ chối / thu hồi"}


def machines_block(p: Pipeline) -> None:
    """S14.7 (D1): the Owner approves / refuses / takes back the PCs each e-mail may sign in from (core/machine_auth)."""
    from core import machine_auth
    rows = machine_auth.requests(p.conn)
    waiting = sum(1 for r in rows if r["status"] == "pending")
    st.markdown(f"**Máy được duyệt (đăng nhập LAN)**" + (f" — {waiting} yêu cầu chờ" if waiting else ""), help=MACHINE_NOTE)
    if not machine_auth.lan_on():
        st.caption("Dashboard đang chỉ mở trên máy này (không bật DASHBOARD_LAN) — không cần duyệt máy.")
    if not rows:
        st.caption("Chưa có yêu cầu nào.")
        return
    owner = me().get("email")
    for r in rows:
        tag = f"{r['email']}_{r['machine']}"
        c1, c2, c3, c4 = st.columns([3, 2.2, 1, 1], vertical_alignment="center")
        c1.markdown(f"**{escape(r['email'])}** · máy **{escape(r['machine'])}**  \n<small>yêu cầu {escape(r['requested_at'] or '')}"
                    f" · IP gần nhất {escape(r['last_ip'] or '—')}</small>", unsafe_allow_html=True)
        c2.markdown(MACHINE_STATUS.get(r["status"], r["status"]) + (f"  \n<small>{escape(r['decided_by'] or '')} · "
                    f"{escape(r['decided_at'] or '')}</small>" if r["decided_at"] else ""), unsafe_allow_html=True)
        if not machine_auth.is_owner(owner):    # rà D1: "monitor" sees the list; only the Owner gets the buttons (the core refuses others)
            continue
        try:
            if r["status"] != "approved" and c3.button("Duyệt", key=f"mach_ok_{tag}", type="primary" if r["status"] == "pending" else "secondary"):
                machine_auth.approve(p.conn, owner, r["email"], r["machine"])
                st.rerun()
            if r["status"] == "pending" and c4.button("Từ chối", key=f"mach_no_{tag}"):
                machine_auth.reject(p.conn, owner, r["email"], r["machine"])
                st.rerun()
            if r["status"] == "approved" and c4.button("Thu hồi", key=f"mach_rv_{tag}",
                                                       help="Người này bị đăng xuất ngay; máy này không vào được nữa cho tới khi duyệt lại"):
                machine_auth.revoke(p.conn, owner, r["email"], r["machine"])
                st.rerun()
        except auth.AuthError as e:
            st.error(str(e))


def team_screen(p: Pipeline, pid: int):
    if not (me().get("role") == "owner" or allowed("monitor")):
        if ticket_screen_visible(p, pid):
            error_tickets_panel(p, pid)
            return
        st.warning("Màn Nhóm dành cho Owner hoặc người có quyền “Theo dõi hiệu suất”.")
        return
    is_owner = me().get("role") == "owner"
    v2 = ui.v2_on()
    if not v2:
        st.markdown("### 👥 Nhóm")
    hero_slot = st.container() if v2 else None
    c1, c2, c3, *c4 = st.columns([1.4, 2.4, 2, 0.9] if v2 else [1.4, 2.4, 2], vertical_alignment="center")
    period = c1.selectbox("Khoảng", list(PERIODS), index=1, label_visibility="collapsed", key="team_period")
    q = c2.text_input("Tìm", placeholder="🔎 Tìm người dùng…", label_visibility="collapsed", key="team_q").strip().lower()
    flt = c3.selectbox("Lọc", list(FILTERS), format_func=FILTERS.get, label_visibility="collapsed", key="team_filter")
    rows = people_rows(p, PERIODS[period])
    shown = [r for r in rows if (not q or q in r["who"].lower())
             and (not flt or (flt == "over" and r["share"] is not None and r["share"] >= team.LIMIT_WARN)
                  or (flt == "inact" and r["inactive"]) or r["role_key"] == flt)]
    if v2:
        with c4[0]:
            with D.info("team-note", label="Chú thích", help_text=D.md_plain(NOTE)):
                st.markdown(NOTE)
        _hero(hero_slot, rows, period)
        _people_table(shown)
    else:
        data_table([{"Người dùng": r["who"], "Vai": r["role"], "Video (xong / gửi)": f"{r['videos_ok']} / {r['videos']}",
                       "Lỗi · Gen lại": f"{r['failed']} · {r['retry']}", "Giây video": f"{r['seconds']:g}", "Ảnh": r["images"],
                       "Tiền chi (USD)": round(r["usd"], 2), "Hạn mức/tháng": (f"{r['limit']:g} ({r['share']:.0%})" if r["limit"] else "—"),
                       "Dự án": r["projects"], "Gần nhất": r["last"]} for r in shown], hide_index=True, width="stretch")
    error_tickets_panel(p, pid)
    if not v2:
        st.caption(NOTE)
    if not is_owner:
        return
    st.divider()
    roles_md = "  \n".join(f"- **{r['label']}** — {r['desc']}" for r in team.ROLES.values())
    if v2:                                  # title stays; the how-to line + the role descriptions go in its ⓘ
        _roles_note = "Chọn vai thay vì tick từng quyền; quyền lẻ vẫn ở ⚙ → Hệ thống → 👥 Phân quyền.\n\n" + roles_md
        with D.info("team-roles", anchor="<b>Vai trò & hạn mức</b>", help_text=D.md_plain(_roles_note)):
            st.markdown(_roles_note)
    else:
        ui.html(ui.card_title("Vai trò & hạn mức", "chọn vai thay vì tick từng quyền; quyền lẻ vẫn ở ⚙ → Hệ thống → 👥 Phân quyền"))
        st.markdown(roles_md)
    actor = auth.Identity(me()["email"], me()["name"], me()["role"], me().get("perms", []))
    members = [r for r in rows if r["user"] and r["user"]["role"] != "owner"]
    labels = {k: v["label"] for k, v in team.ROLES.items()}
    labels["custom"] = "Tùy chỉnh (giữ nguyên)"
    roles_box = ExitStack()
    if v2:
        roles_box.enter_context(D.card("team-roles"))
    for r in members:
        u = r["user"]
        cols = st.columns([2.4, 1.6, 1.1, 1.2, 1], vertical_alignment="center")
        cols[0].markdown(f"**{escape(u['email'])}**  \n<small>{'đang hoạt động' if u['active'] else 'đã khóa'}</small>", unsafe_allow_html=True)
        cur_role = r["role_key"]
        keys = list(labels) if cur_role == "custom" else [k for k in labels if k != "custom"]
        role = cols[1].selectbox("Vai", keys, index=keys.index(cur_role) if cur_role in keys else 0, format_func=labels.get,
                                 key=f"team_role_{u['email']}", label_visibility="collapsed")
        limit = cols[2].number_input("Hạn mức", min_value=0.0, value=float(r["limit"] or 0.0), step=5.0, key=f"team_limit_{u['email']}",
                                     label_visibility="collapsed", help="USD / tháng, 0 = không đặt. Chỉ cảnh báo.")
        active = cols[3].checkbox("Được vào", u["active"], key=f"team_active_{u['email']}")
        if cols[4].button("💾 Lưu", key=f"team_save_{u['email']}"):
            try:
                perms = u["perms"] if role == "custom" else team.perms_for(role)
                auth.set_user(p.conn, actor, u["email"], perms, active)
                team.set_limit(p.conn, u["email"], limit or None)
            except auth.AuthError as e:
                st.error(str(e))
            else:
                st.toast(f"Đã lưu {u['email']}")
                st.rerun()
    roles_box.close()
    user_reset_block(p, me(), rows, v2)
    with (D.card("team-invite") if v2 else st.container(border=True)):
        st.markdown("**Mời người mới**")
        i1, i2, i3, i4 = st.columns([3, 1.6, 1.2, 1], vertical_alignment="bottom")
        email = i1.text_input("E-mail", key="team_new_email", placeholder="ten@garena.vn")
        role = i2.selectbox("Vai", list(team.ROLES), format_func=lambda k: team.ROLES[k]["label"], key="team_new_role")
        limit = i3.number_input("Hạn mức USD/tháng", min_value=0.0, value=0.0, step=5.0, key="team_new_limit")
        if i4.button("Mời", key="team_new_go", type="primary", disabled=not email.strip()):
            try:
                auth.add_user(p.conn, actor, email, team.perms_for(role))
                team.set_limit(p.conn, auth.normalize_email(email), limit or None)
            except auth.AuthError as e:
                st.error(str(e))
            else:
                st.rerun()
    with (D.card("team-machines") if v2 else st.container(border=True)):      # S14.7: LAN sign-in only from approved PCs
        machines_block(p)
    with (D.card("team-limits") if v2 else st.container(border=True)):        # S14.18: per-person project limits + requests
        limits_ui.team_block(p, [r["user"]["email"] for r in members])
    with (D.card("team-access") if v2 else st.container(border=True)):        # đợt F: who watches which project, and projects with no creator
        st.markdown("**Quyền theo dự án**", help=ACCESS_NOTE)
        access_ui.team_panel(p)
    if not v2:
        ui.html(ui.card_title("Lịch sử hoạt động", "đổi quyền / thêm bớt người (nhật ký của Owner) và lượt gen gần đây"))
    log = auth.recent_audit(p.conn, 15)
    gens = access.filter_rows(p.conn, p.conn.execute(
        "SELECT j.created_at, COALESCE(NULLIF(TRIM(j.created_by),''),'(chưa nhập tên)') who, j.type, j.state, pr.name, j.project_id"
        " FROM jobs j JOIN projects pr ON pr.id=j.project_id WHERE j.type IN ('image_gen','video_gen')"
        " ORDER BY j.id DESC LIMIT 200").fetchall(), C.access_user(), key="project_id")[:15]
    if v2:                                  # P3: both logs live in one labelled expander, closed by default
        with st.expander("🕘 Lịch sử hoạt động — nhật ký quyền (đổi quyền, thêm bớt người) và lượt gen gần đây", expanded=False):
            _history_v2(log, gens)
        return
    c_a, c_b = st.columns(2)
    with c_a:
        st.markdown("**Nhật ký quyền**")
        data_table([{"Lúc": r["at"], "Ai": r["email"], "Việc": r["action"], "Chi tiết": r["detail"]} for r in log],
                     hide_index=True, width="stretch")
    with c_b:
        st.markdown("**Lượt gen gần đây**")
        data_table([{"Lúc": (r["created_at"] or "")[:16].replace("T", " "), "Ai": r["who"],
                       "Loại": "video" if r["type"] == "video_gen" else "ảnh", "Dự án": r["name"], "Trạng thái": r["state"]} for r in gens],
                     hide_index=True, width="stretch")
