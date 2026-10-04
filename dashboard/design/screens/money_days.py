"""💵 → "📅 Mức dùng theo ngày · đợt ngân sách" (S14.6 Gói K). Một hộp thoại: bảng mỗi ngày (ảnh / video / âm thanh / Claude, USD + số
lượt, dòng chưa có giá → ước tính dư ghi rõ), lọc theo đợt + dự án, chọn một ngày → từng dòng sổ chi; các đợt đã đóng với tóm tắt; khối
"Bắt đầu đợt mới" chỉ Owner (lý do bắt buộc, hỏi Có/Không). Số liệu: core.budget_rounds; mở đợt: core.budget_rounds.start_new (dùng
money_reset.set_planned — core từ chối người không phải Owner, ẩn khối chỉ là cho gọn)."""
from typing import Dict

import streamlit as st

from dashboard.design import components as D

FLAG = "dlg_money_days"


def open_button() -> None:
    """Nút trong thẻ 💵 (giữ khóa `mc_days`)."""
    from dashboard.common import open_dialog
    if st.button("📅 Mức dùng theo ngày · đợt ngân sách", key="mc_days", width="stretch",
                 help="Chi theo từng ngày (ảnh / video / âm thanh / Claude), lọc theo đợt + dự án, bấm một ngày xem từng dòng sổ chi"):
        open_dialog(FLAG)


def _money(slot: Dict) -> str:
    usd = slot["usd"] + slot["est_usd"]
    if not slot["n"] and not usd:
        return "—"
    text = f"${usd:.2f} · {slot['n']} lượt"
    return text + " (có ước tính)" if slot["est_usd"] else text


def _round_label(r: Dict) -> str:
    from core import budget_rounds as R
    start = (r.get("started_at") or "đầu sổ")[:16]
    end = (r.get("ended_at") or "nay")[:16]
    tag = "đang mở" if not r.get("ended_at") else "đã đóng"
    return f"{r['name']} ({start} → {end} UTC, {tag})" if r["name"] != R.FIRST_NAME or r.get("ended_at") else \
        f"{r['name']} (từ {start} UTC — mốc hiện tại, chưa mở đợt mới)"


def _summary_md(r: Dict) -> str:
    from core import budget_rounds as R
    s = r.get("summary") or {}
    if not s:
        return "_Chưa có tóm tắt._"
    kinds = " · ".join(f"{R.KIND_LABEL[k]} {_money(s['by_kind'][k])}" for k in R.KINDS if k in s.get("by_kind", {}))
    plan = f" / mức dự tính ${r['planned_usd']:.2f}" if r.get("planned_usd") else ""
    lines = [f"- **Tổng:** ${s.get('total_usd', 0):.2f}{plan} — {s.get('events', 0)} dòng sổ chi",
             f"- **Theo loại:** {kinds}",
             "- **Theo dự án:** " + (", ".join(f"#{k}: ${v:.2f}" for k, v in sorted((s.get("by_project") or {}).items())) or "—")]
    note = R.unpriced_note(s)
    if note:
        lines.append(f"- ⚠ {note}")
    who = " · ".join(x for x in (f"mở bởi {r['opened_by']}" if r.get("opened_by") else "",
                                  f"đóng bởi {r['closed_by']}" if r.get("closed_by") else "",
                                  f"lý do đóng: {r['close_reason']}" if r.get("close_reason") else "") if x)
    if who:
        lines.append(f"- {who}")
    return "\n".join(lines)


def new_round_block(conn, actor: Dict) -> None:
    """Chỉ Owner: tên + mức dự tính (USD tổng, Claude) + lý do bắt buộc → hỏi Có/Không → budget_rounds.start_new."""
    from core import budget, budget_rounds as R
    if (actor or {}).get("role") != "owner":
        return
    b = budget.get(conn)
    with st.expander("▶ Bắt đầu đợt ngân sách mới (chỉ Owner)"):
        st.caption("Đóng đợt hiện tại (lưu tóm tắt: đã chi theo loại, số lượt, theo dự án) rồi mở đợt mới: thanh đợt thử và thanh Claude "
                   "đếm lại từ bây giờ với mức dự tính mới. Mức dự tính chỉ để CẢNH BÁO (vàng ≥ 100 %, đỏ ≥ 150 %), không chặn. "
                   "Sổ chi giữ nguyên; mỗi lần mở đợt được ghi nhật ký.")
        name = (st.text_input("Tên đợt mới", key="md_new_name", placeholder="ví dụ: Đợt 04/10 — dự án thử 30 giây") or "").strip()
        c1, c2 = st.columns(2)
        usd = c1.number_input("Mức dự tính tổng (USD)", 0.0, 100000.0, float(b["usd"]), 5.0, key="md_new_usd")
        llm = c2.number_input("Mức dự tính Claude API (USD)", 0.0, 100000.0, float(b["llm_usd"]), 1.0, key="md_new_llm")
        why = (st.text_input("Lý do (bắt buộc)", key="md_new_why", placeholder="ví dụ: chính sách tiền mới 04/10") or "").strip()
        ready = bool(name) and bool(why)
        if not ready:
            st.caption("Cần nhập tên đợt và lý do.")
        cur = R.current(conn)
        ids = (name, float(usd), float(llm), why) if ready else ()
        if D.confirm_all("md_new_go", ids, "▶ Đóng đợt hiện tại & mở đợt mới",
                         f"Đóng đợt «{cur['name']}» và mở đợt «{name}» với mức dự tính ${usd:.2f} (Claude ${llm:.2f})? "
                         f"Thanh đợt thử + Claude đếm lại từ bây giờ (sổ chi giữ nguyên). Lý do: {why}", st, "Có, mở đợt mới"):
            try:
                out = R.start_new(conn, actor, name, usd, llm, why)
            except Exception as e:  # noqa: BLE001 - said, never a crash of the dialog
                st.error(f"Không mở được đợt mới: {e}")
                return
            st.success(f"Đã đóng «{out['closed']['name']}» (chi ${out['closed']['summary']['total_usd']:.2f}) và mở «{out['opened']['name']}».")


def body(conn, actor: Dict) -> None:
    """Nội dung hộp thoại (tách riêng để test bằng AppTest.from_function)."""
    from core import budget_rounds as R
    from dashboard.design.screens import shell_parts as SP
    rounds = R.history(conn)
    i = st.selectbox("Đợt", range(len(rounds)), format_func=lambda k: _round_label(rounds[k]), key="md_round")
    rnd = rounds[i or 0]
    since, until = R.window(rnd)
    projects = R.projects_in(conn, since, until)
    choices = [None] + [pid for pid, _ in projects]
    names = dict(projects)
    pid = st.selectbox("Dự án", choices, format_func=lambda x: "Tất cả dự án" if x is None else f"#{x} {names.get(x, '')}", key="md_project")
    days = R.daily(conn, since, until, pid)
    total = sum(d["total_usd"] for d in days)
    est = sum(d["est_usd"] for d in days)
    if rnd.get("planned_usd") and pid is None:
        st.html(SP.money_meter(total, rnd["planned_usd"], f"Đợt «{rnd['name']}»: ${total:.2f} / mức dự tính ${rnd['planned_usd']:.2f}"
                               + (f" (gồm ước tính dư ${est:.2f})" if est else "")))
    else:
        st.markdown(f"**Tổng trong đợt{' — dự án #' + str(pid) if pid else ''}:** ${total:.2f}" + (f" (gồm ước tính dư ${est:.2f})" if est else ""))
    rows = [{"Ngày": d["day"], **{R.KIND_LABEL[k]: _money(d[k]) for k in R.KINDS}, "Tổng (USD)": f"{d['total_usd']:.2f}",
             "Chưa có giá": R.unpriced_note(d)} for d in days]
    D.data_table(rows, empty="Chưa có dòng sổ chi nào trong đợt này.", hide_index=True, width="stretch")
    st.caption("Ngày theo giờ Việt Nam. Dòng chưa có giá trong bảng giá được ước tính DƯ (giá cao nhất đã biết × hệ số an toàn) và cộng "
               "vào tổng; nhà cung cấp giả lập không tính.")
    if days:
        day = st.selectbox("Xem từng dòng sổ chi của ngày", [""] + [d["day"] for d in days],
                           format_func=lambda x: "— chọn một ngày —" if not x else x, key="md_day")
        if day:
            detail = R.day_detail(conn, day, pid, since, until)
            D.data_table([{"Giờ": r["time"], "Dự án": r["project"], "Khâu": r["stage"], "Nhà cung cấp": r["provider"],
                           "Model": f"{r['model']}:{r['tier']}", "Số lượng": f"{r['quantity']:g} {r['unit']}",
                           "USD": "chưa có giá" if r["usd"] is None else
                           (f"≈ {r['usd']:.4f} (chưa có giá — ước tính dư)" if r["estimated"] else f"{r['usd']:.4f}")}
                          for r in detail], empty="Không có dòng nào.", hide_index=True, width="stretch")
    closed = [r for r in rounds if r.get("ended_at")]
    with st.expander(f"🗂 Các đợt đã đóng ({len(closed)})"):
        if not closed:
            st.caption("Chưa có đợt nào được đóng.")
        for r in closed:
            st.markdown(f"**{_round_label(r)}**\n\n" + _summary_md(r))
    new_round_block(conn, actor)


def dialog_if_open(actor: Dict) -> None:
    if st.session_state.get(FLAG):
        _dialog(actor)


def _close() -> None:
    from dashboard.common import close_dialog
    close_dialog(FLAG)


@st.dialog("📅 Mức dùng theo ngày · đợt ngân sách", width="large", on_dismiss=_close)
def _dialog(actor: Dict) -> None:
    from core.db import connect
    from dashboard import common as C
    body(connect(C.DB), actor)              # own connection: a dialog's buttons rerun in another thread (header._own)
