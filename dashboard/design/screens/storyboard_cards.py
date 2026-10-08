"""S13 nhánh F — Storyboard v2: thẻ ảnh kính, hero + thống kê, thanh hành động dính, thẻ Motion theo cảnh.

Chỉ chạy khi cờ ui_v2 bật (step2.py / step3.py gọi vào đây sau khi kiểm `ui.v2_on()`); cờ tắt thì không import gì từ file này.
Mọi khóa widget CŨ được giữ (a_, r_, dd_, c_, retry→dretry_, sel_btn_, note_, rn_, dfix_, hist_…_prev/_next, approve_all…, board_ok_…);
khóa mới có tiền tố `sb…` (card-sb-<cảnh>, sticky-sb, sbv_/sbvon_ cho chip phiên bản).
"""
import json
import os
from contextlib import contextmanager
from html import escape

import streamlit as st

from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers, như step2/step3)
from dashboard import common as C
from dashboard.design import components as D
from dashboard.design.screens.prompt_versions_ui import spin as _spin  # S14.17: spinner khi Đạo diễn viết lại prompt

# job.state -> trạng thái duyệt cố định của thiết kế (components.FRAME_STATES)
_FRAME = {"approved": "approved", "pending_review": "review", "succeeded": "review", "rejected": "rejected", "failed": "failed",
          "queued": "queued", "retryable": "queued", "running": "working"}
REVIEWABLE = ("succeeded", "pending_review")


def frame_state(state: str) -> str:
    return _FRAME.get(state, state)


def state_pill(state: str) -> str:
    """Pill từ trạng thái job THẬT; trạng thái lạ (đã hủy…) dùng nhãn cũ của ui.STATE_LABELS."""
    key = _FRAME.get(state)
    if key:
        return D.frame_state_pill(key)
    return D.pill(ui.state_label(state), "mute")


# ---------------------------------------------------------------------------------------------------------------- bớt chữ: một dòng + ⓘ
@contextmanager
def row(summary_html: str, key: str, ratio: int = 24):
    """MỘT dòng tóm tắt (HTML đã escape) + nút ⓘ bên phải; chi tiết dài viết trong khối `with` (QUY_TAC §5: P2 ngoài, P3 trong ⓘ)."""
    with D.info(key, anchor=summary_html) as pop:          # 02/10: bấm / rê chuột ngay trên dòng tóm tắt, không còn nút ⓘ riêng
        yield pop


def sum_html(text: str, kind: str = "") -> str:
    """Dòng tóm tắt: chữ muted, hoặc màu cảnh báo khi kind='warn'; text là chữ thường, được escape ở đây."""
    cls = "sb-sum" + (" sb-warn" if kind == "warn" else "")
    return f'<span class="{cls}">{escape(text)}</span>'


def note(text: str, details: str, key: str, kind: str = "") -> None:
    """Dòng tóm tắt + ⓘ chứa `details` (markdown); không có chi tiết thì chỉ còn dòng."""
    if not details:
        st.markdown(sum_html(text, kind), unsafe_allow_html=True)
        return
    with row(sum_html(text, kind), key):
        st.markdown(details)


def estimate_short(est: dict) -> str:
    unit = "ảnh" if est["kind"] == "image" else "clip"
    if not est.get("known"):
        over = est.get("unit_over")                    # S14.16: a missing price shows its high estimate
        return (f"{est['items']} {unit} ≈ {over * est['items']:.1f} {est['currency']} (ước tính dư, thiếu giá)" if over is not None
                else f"{est['items']} {unit} · chưa có giá")
    return f"{est['items']} {unit} ≈ {est['min']:.1f} {est['currency']} (ước tính)"


def show_estimate(est, runner) -> bool:
    """Như common.show_estimate nhưng ước tính tiền chỉ MỘT dòng; chi tiết trong ⓘ. Cùng ngữ nghĩa xác nhận batch lớn."""
    if est is None or est["items"] == 0:
        return True
    note("💰 Ước tính: " + estimate_short(est), cost.format_estimate(est), f"sb-est-{est['kind']}")
    return C._confirm_big_batch(est, runner)


def known_issues(active_issues) -> None:
    """Một dòng tóm tắt + MỘT expander đóng chứa chi tiết từng khâu (thay dòng đỏ dài + một expander mỗi khâu)."""
    total = sum(len(x["open"]) for x in active_issues)
    st.markdown(D.pill(f"⚠ {len(active_issues)} khâu có lỗi đã biết · {total} lỗi chưa sửa", "warn"), unsafe_allow_html=True)
    with st.expander("Xem lỗi đã biết và hướng sửa", expanded=False):
        for st_ in active_issues:
            st.markdown(f"**{st_['label']}** — {len(st_['open'])} lỗi chưa sửa")
            st.caption(st_["status"])
            for bug, fix in st_["open"]:
                st.markdown(f"- **Lỗi:** {bug}  \n  **Hướng sửa:** {fix}")
            if st_["fixed"]:
                st.caption("Đã sửa: " + "; ".join(st_["fixed"]))


# ---------------------------------------------------------------------------------------------------------------- số liệu / hero
def board_stats(p, pid: int) -> dict:
    """Đếm theo job MỚI NHẤT của mỗi cảnh (cùng cách chia với bộ lọc)."""
    rows = p.conn.execute("SELECT j.scene_id, j.state, j.escalated FROM jobs j WHERE j.project_id=? AND j.type='image_gen' ORDER BY j.id",
                          (pid,)).fetchall()
    latest = {}
    for r in rows:
        latest[r["scene_id"]] = r
    st_ = {"approved": 0, "review": 0, "failed": 0, "busy": 0, "rejected": 0}
    for r in latest.values():
        s = r["state"]
        if s == "approved":
            st_["approved"] += 1
        elif s in REVIEWABLE:
            st_["review"] += 1
        elif s == "failed":
            st_["failed"] += 1
        elif s in ("queued", "running", "retryable"):
            st_["busy"] += 1
        elif s == "rejected":
            st_["rejected"] += 1
    st_["scenes"] = len(latest)
    return st_


def hero(p, pid: int, summ: dict, proj) -> None:
    s = board_stats(p, pid)
    done, stale = summ["images"]
    total = summ["total"] or 0
    pills = [(ui.MODE_LABELS.get(proj["operating_mode"], proj["operating_mode"]), "info")]
    if s["review"]:
        pills.append((f"{s['review']} cần duyệt", "warn"))
    if stale:
        pills.append((f"⚠ {stale} ảnh cũ", "warn"))
    from core import chat_intake
    merged = chat_intake.enabled()                        # 07/10 cờ chat_first: bản đồ tiến độ đã nói số → nhãn chỉ khi có chuyện
    if merged:
        if s["failed"]:
            pills.append((f"{s['failed']} lỗi", "bad"))
        if s["busy"]:
            pills.append((f"{s['busy']} đang gen", "info"))
    with D.hero("sb"):
        st.markdown(D.hero_html("Storyboard · Ảnh + QC", "mỗi cảnh một ảnh đúng nhân vật, đúng bối cảnh, đã duyệt", pills), unsafe_allow_html=True)
        if merged:
            return
        c = st.columns(4)
        c[0].markdown(D.stat("Đã duyệt", f"{done} / {total}", f"{(done / total * 100) if total else 0:.0f} %"), unsafe_allow_html=True)
        c[1].markdown(D.stat("Chờ duyệt", str(s["review"])), unsafe_allow_html=True)
        c[2].markdown(D.stat("Lỗi", str(s["failed"])), unsafe_allow_html=True)
        c[3].markdown(D.stat("Đang gen / chờ gen", str(s["busy"])), unsafe_allow_html=True)
        st.markdown(D.meter((done / total) if total else 0), unsafe_allow_html=True)


def status_table(p, pid: int) -> str:
    """Bảng trạng thái từng cảnh (thay st.dataframe, nền theo giao diện)."""
    rows = p.conn.execute(
        "SELECT j.state, j.retry_count, j.escalated, s.idx, s.id sid, (SELECT AVG(score) FROM qc_results WHERE job_id=j.id) AS qc "
        "FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.project_id=? AND j.type='image_gen' AND j.state NOT IN ('rejected','cancelled') "
        "ORDER BY s.idx", (pid,)).fetchall()
    if not rows:
        return ""
    def qc(r):
        return "%.2f" % r["qc"] if r["qc"] is not None else "—"
    body = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (r["idx"], state_pill(r["state"]), qc(r), r["retry_count"]) for r in rows)
    return ('<table class="v2-table"><tr><th>Cảnh</th><th>Trạng thái</th><th>Điểm QC</th><th>Đã gen lại</th></tr>' + body + "</table>")


# ---------------------------------------------------------------------------------------------------------------- thẻ ảnh
def _qc_chips(p, proj, jid: int) -> str:
    scores = C.qc_scores(p, jid)
    if not scores:
        return ""
    thr = float(proj["qc_auto_pass_threshold"])
    mean = sum(s["score"] for s in scores) / len(scores)
    kind = "ok" if mean >= thr else "warn" if mean >= thr - 0.15 else "bad"
    return D.pill(f"QC {mean:.2f}", kind)                 # tiêu chí thấp nhất + từng tiêu chí: trong ⓘ (card_details)


def card_details(p, proj, j, is_latest: bool, stale_reason) -> None:
    """Nội dung của ⓘ trên thẻ ảnh (P3): điểm QC từng tiêu chí, lý do gen lại đầy đủ, cảnh báo ảnh cũ, nội dung kịch bản + prompt."""
    scores = C.qc_scores(p, j["id"])
    if scores:
        thr = float(proj["qc_auto_pass_threshold"])
        st.markdown(f"**Điểm QC từng tiêu chí** (ngưỡng đạt {thr:.2f})")
        st.markdown("\n".join(f"- {CRITERIA_LABEL.get(s['criterion'], s['criterion'])}: **{s['score']:.2f}**" + (" ⚠ dưới ngưỡng" if s["score"] < thr else "")
                              for s in scores))
    if stale_reason and is_latest:
        st.markdown(f"⚠ **Ảnh cũ:** {stale_reason}")
    if j["retry_reason"]:
        st.markdown(("**Lý do gen lại:** " if is_latest else "**Lý do gen lại lúc đó:** ") + str(j["retry_reason"]))
    C.scene_expander(p, j["scene_id"])


def _open_detail(pid: int, jid: int) -> None:
    st.session_state[f"sel_{pid}"] = jid
    detail_dialog(pid, jid)


def _version_strip(pid: int, sid: int, key: str, n: int, pointer: int) -> None:
    """v1…vN: bấm một chip = đặt con trỏ phiên bản (cùng việc ‹ › cũ đã làm; khóa ‹ › cũ giữ nguyên)."""
    if n <= 1:
        st.markdown(D.version_strip(1, 0), unsafe_allow_html=True)
        return
    shown = list(range(max(0, min(pointer - 2, n - 4)), min(n, max(0, min(pointer - 2, n - 4)) + 4)))
    with st.container(key=f"vers-{pid}-{sid}"):                      # CSS: hàng chip tự xuống dòng khi thẻ hẹp, không cắt “v..” (02/10)
        cols = st.columns([1] + [1] * len(shown) + [1], gap="small")
        if cols[0].button("‹", key=f"{key}_prev", disabled=pointer == 0):
            st.session_state[key] = pointer - 1
            st.rerun()
        for col, i in zip(cols[1:-1], shown):
            if col.button(f"v{i + 1}", key=f"{'sbvon' if i == pointer else 'sbv'}_{pid}_{sid}_{i}"):
                st.session_state[key] = i
                st.rerun()
        if cols[-1].button("›", key=f"{key}_next", disabled=pointer == n - 1):
            st.session_state[key] = pointer + 1
            st.rerun()


def _send_queued(p, pid: int) -> None:
    """07/10 (Khủng Long Đỏ): a redraw / retry only QUEUED the picture — with nothing else running, no poll sent it and ▶ Gen ảnh had
    nothing "to make", so it waited forever. Send what is queued now (the runner keeps its own limits)."""
    runner = C.image_runner(p)
    if runner is not None:
        act(lambda: runner.submit_pending(pid, wait_s=20))   # lỗi B 08/10: wait for the turn, not a silent 0 (bg_poll sends later)


def image_group_v2(p, pid: int, history: list, proj, stale_reason=None) -> None:
    """Một thẻ kính cho mỗi CẢNH: ảnh · nhãn · pill trạng thái · chip QC · dải phiên bản · 4 nút luôn hiện; mọi chi tiết (điểm QC từng tiêu chí, lý do gen lại, kịch bản) trong MỘT ⓘ."""
    sid = history[0]["scene_id"]
    n = len(history)
    key = f"hist_{pid}_{sid}"
    pointer = min(st.session_state.get(key, n - 1), n - 1)
    j = history[pointer]
    is_latest = pointer == n - 1
    jid, state = j["id"], j["state"]
    busy = state in ("queued", "running", "retryable")
    from core import image_models
    retake = cost.image_button_tag(image_models.of_project(proj), 1, retake_conn=p.conn) if is_latest else ""   # S14.2 A2
    with D.card(f"sb-{sid}"):
        img = C.job_image(pid, jid)
        if img and not busy:
            C.show_image(img, width="stretch")
        elif busy:
            st.markdown(D.shimmer(230), unsafe_allow_html=True)
        else:
            st.markdown(D.empty_state("Chưa có ảnh", ""), unsafe_allow_html=True)
        pills = state_pill(state)
        if j["escalated"]:
            pills += " " + D.pill("⚠ cần xem", "warn")
        if stale_reason and state == "approved" and is_latest:
            pills += " " + D.pill("⚠ ảnh cũ", "warn")
        if not is_latest:
            pills += " " + D.pill("bản cũ", "mute")
        with D.info(f"sb-{sid}-more", anchor=f'<b>{escape(C.unit_label(p, j["project_id"], j["idx"]))}</b>',
                    help_text="Điểm QC, lý do gen lại, nội dung kịch bản — bấm để xem"):
            card_details(p, proj, j, is_latest, stale_reason)
        st.markdown(pills + (" " + _qc_chips(p, proj, jid) if not busy else ""), unsafe_allow_html=True)
        _version_strip(pid, sid, key, n, pointer)
        if is_latest:                                       # S14.17: the Director rewrote this shot's prompt → old/new + ↩
            from dashboard.design.screens import prompt_versions_ui
            prompt_versions_ui.panel(p, sid, "image", act)

        def pair():
            a = st.columns(2, gap="small")
            b = st.columns(2, gap="small")
            return a[0], a[1], b[0], b[1]

        if not is_latest:                                   # an old take: look only, like before
            if st.button("🔍 Chi tiết", key=f"sel_btn_{jid}", width="stretch"):
                _open_detail(pid, jid)
        elif state in REVIEWABLE:
            note = st.text_input("Câu sửa (tiếng Anh)", key=f"note_{jid}", placeholder="vd: Kelly wears the yellow jacket")
            b1, b2, b3, b4 = pair()
            st.caption("↻ Vẽ lại 1 ảnh" + retake)
            if b1.button("✔ Duyệt", key=f"a_{jid}", type="primary", width="stretch"):
                act(lambda: p.approve(jid, "user"))
                st.rerun()
            if b2.button("✖ Loại", key=f"dd_{jid}", width="stretch"):
                act(lambda: p.reject(jid, "user", note or "đã xóa", respawn=False))
                st.rerun()
            if b3.button("↻ Vẽ lại", key=f"r_{jid}", width="stretch"):
                act(_spin(lambda: p.reject(jid, "user", note or None)))
                _send_queued(p, pid)
                st.rerun()
            if b4.button("✎ Sửa", key=f"sel_btn_{jid}", width="stretch"):
                _open_detail(pid, jid)
        elif busy:
            b1, b2, b3, b4 = pair()
            b1.button("✔ Duyệt", key=f"a_{jid}", disabled=True, width="stretch")
            if state != "retryable" and b2.button("■ Hủy", key=f"c_{jid}", width="stretch"):
                act(lambda: p.cancel(jid))
                st.rerun()
            b3.button("↻ Vẽ lại", key=f"r_{jid}", disabled=True, width="stretch")
            if b4.button("✎ Sửa", key=f"sel_btn_{jid}", width="stretch"):
                _open_detail(pid, jid)
        elif state == "failed" and not j["escalated"]:
            fix = st.text_input("Câu sửa (tiếng Anh)", key=f"dfix_{jid}", placeholder="để trống = gửi lại y nguyên",
                                help="Để trống = gửi lại Y NGUYÊN (chỉ khi lỗi do nhà cung cấp). Ảnh ra sai thì ghi câu sửa để đầu vào khác đi.")
            b1, b2, b3, b4 = pair()
            b1.button("✔ Duyệt", key=f"a_{jid}", disabled=True, width="stretch")
            b2.button("✖ Loại", key=f"dd_{jid}", disabled=True, width="stretch")
            st.caption("↻ Vẽ lại 1 ảnh" + retake)
            if b3.button("↻ Vẽ lại", key=f"dretry_{jid}", width="stretch",
                         help="Gen lại với câu sửa" if fix.strip() else "Gửi lại y nguyên — chỉ khi lỗi do nhà cung cấp"):
                act(lambda: p.retry(jid, "người dùng gen lại với câu sửa" if fix.strip() else "gửi lại (lỗi nhà cung cấp)", fix=fix, by_user=True))
                _send_queued(p, pid)
                st.rerun()
            if b4.button("✎ Sửa", key=f"sel_btn_{jid}", width="stretch"):
                _open_detail(pid, jid)
        elif state == "approved":
            r_note = st.text_input("Lý do bỏ duyệt", key=f"rn_{jid}", placeholder="chỉ cần khi bỏ duyệt")
            b1, b2, b3, b4 = pair()
            b1.button("✔ Duyệt", key=f"a_{jid}", disabled=True, width="stretch")
            b2.button("✖ Loại", key=f"dd_{jid}", disabled=True, width="stretch")
            st.caption("↻ Vẽ lại 1 ảnh" + retake)
            if b3.button("↻ Vẽ lại", key=f"reopen_{jid}", width="stretch",
                         help="Bỏ duyệt và gen lại ảnh (motion/video làm từ ảnh này sẽ hiện ⚠ cũ)"):
                if act(_spin(lambda: p.reopen_approved(jid, r_note or None)), "Đã bỏ duyệt, xếp hàng gen lại"):
                    _send_queued(p, pid)
                    st.rerun()
            if b4.button("✎ Sửa", key=f"sel_btn_{jid}", width="stretch"):
                _open_detail(pid, jid)
            if stale_reason and st.button("↻ Gen lại theo nội dung mới" + retake, key=f"stale_{jid}", type="primary", width="stretch"):
                if act(lambda: p.reopen_approved(jid, f"Nội dung cảnh đã đổi: {stale_reason}", fix=""), "Đã xếp hàng gen lại"):
                    _send_queued(p, pid)
                    st.rerun()
        else:                                               # rejected / cancelled / escalated failed
            b1, b2, b3, b4 = pair()
            b1.button("✔ Duyệt", key=f"a_{jid}", disabled=True, width="stretch")
            b2.button("✖ Loại", key=f"dd_{jid}", disabled=True, width="stretch")
            if j["escalated"]:
                st.caption("↺ Làm lại 1 ảnh" + retake)
                if b3.button("↺ Làm lại", key=f"rs_{jid}", type="primary", width="stretch", help="Đã hết số lần thử: bắt đầu lại cảnh này"):
                    if act(lambda: p.restart_job(jid), "Đã xếp hàng ảnh mới cho cảnh"):
                        _send_queued(p, pid)
                        st.rerun()
            else:
                b3.button("↻ Vẽ lại", key=f"r_{jid}", disabled=True, width="stretch")
            if b4.button("✎ Sửa", key=f"sel_btn_{jid}", width="stretch"):
                _open_detail(pid, jid)


@st.dialog("Chi tiết ảnh", width="large")
def detail_dialog(pid: int, jid: int) -> None:
    """✎ Sửa / 🔍 Chi tiết: ảnh lớn + kịch bản + điểm QC + nhập ảnh thủ công (các nút duyệt/loại/vẽ lại nằm ở thẻ)."""
    from dashboard.steps.step2 import image_detail
    p = C.scoped(Pipeline(connect(C.DB)))
    job = p.conn.execute("SELECT j.*, s.idx, s.title FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.id=?", (jid,)).fetchone()
    if job is None:
        st.caption("Ảnh này không còn.")
        return
    image_detail(p, pid, job, p.project(pid), on_card=True)


# ---------------------------------------------------------------------------------------------------------------- thanh hành động dính
def gate_waiting(p, pid: int) -> bool:
    from core import shots
    if not shots.shots_of(p, pid):
        return False
    return autopilot.get_gates(p, pid).get("waiting_for") == "storyboard" and autopilot.status(p, pid)["state"] == "waiting"


def _confirm_all_primary(key: str, ids, label: str, question: str, container, primary: bool) -> bool:
    """Như common.confirm_all (cùng khóa, cùng ngữ nghĩa hỏi-có/không) nhưng nút đầu là nút chính của thanh."""
    return D.confirm_all(key, ids, label, question, container, primary=primary, stretch=True)


def action_bar(p, pid: int) -> None:
    """MỘT thanh hành động dính ở cuối lưới: tóm tắt + ước tính tiền video (như trang Video) · Duyệt storyboard → gửi video · Duyệt tất cả."""
    from core import storyboard_gate
    pending = [r["id"] for r in p.conn.execute(
        "SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='pending_review' ORDER BY id", (pid,)).fetchall()]
    waiting = gate_waiting(p, pid)
    with st.container(key="sticky-sb"):
        with D.card("sb-actionbar"):
            if waiting:
                left, mid, right = st.columns([3.2, 2.4, 2.4], vertical_alignment="center")
            else:
                left, right = st.columns([3.2, 2.4], vertical_alignment="center")
                mid = None
            with left:
                pills = (D.pill(f"{len(pending)} ảnh chờ duyệt", "warn" if pending else "mute")
                         + (" " + D.pill("⏸ Chờ bạn duyệt storyboard", "warn", running=True) if waiting else ""))
                if waiting:                                  # P2: MỘT dòng (cờ + tiền video); chi tiết từng cảnh trong ⓘ
                    gate_line = storyboard_gate.summary(p, pid, C.DATA)
                    try:
                        est = cost.estimate_videos_by_scene(p, pid, cost.load_pricing())
                        money = ("Video ≈ " + (f"{est['min']:.1f} {est['currency']}" if est.get("known") else "chưa có giá")) if est and est.get("items") else ""
                        money_full = "Ước tính gen video sau khi duyệt: " + cost.format_estimate(est) if est and est.get("items") else ""
                    except Exception:  # noqa: BLE001 - an estimate problem must not hide the buttons
                        money, money_full = "chưa tính được tiền video", "Chưa tính được ước tính gen video (xem Bước Video)."
                    st.markdown(pills, unsafe_allow_html=True)
                    with row(sum_html(" · ".join(x for x in (gate_line, money) if x)), "sb-bar-more", ratio=10):
                        st.markdown(f"**Cổng storyboard:** {gate_line}")
                        if money_full:
                            st.markdown(money_full)
                else:
                    st.markdown(pills, unsafe_allow_html=True)
            if mid is not None:
                with mid:
                    try:                                         # S14.2 A2: the clips this sends, priced on the button
                        board_tag = cost.video_batch_tag(p, pid)
                    except Exception:  # noqa: BLE001 - the button stays; the label says the price is missing
                        board_tag = " · chưa có giá (không ước tính được)"
                    if st.button("✔ Duyệt storyboard → gửi video" + board_tag, key=f"board_ok_{pid}", type="secondary" if pending else "primary", width="stretch"):
                        autopilot.resume(p, pid, p.actor)
                        autopilot_manager(C.DB, C.DATA).start(pid, user=C.access_user())
                        st.rerun()
            with right:
                if _confirm_all_primary("approve_all", pending, f"✔ Duyệt tất cả ({len(pending)} ảnh)", f"Duyệt tất cả {len(pending)} ảnh đang chờ duyệt?",
                                        right, primary=bool(pending) or not waiting):
                    for jid in pending:
                        p.approve(jid, "user", note="gate_bulk")
                    st.rerun()


# ---------------------------------------------------------------------------------------------------------------- Motion (step3)
def motion_hero(p, pid: int, summ: dict, rows) -> None:
    stat = voice.status(p.conn, pid, C.DATA)
    out = os.path.join(C.DATA, str(pid), "output", "ANIMATIC.mp4")
    m_done, m_stale = summ["motion"]
    total = summ["total"] or 0
    pills = [("⚠ %d mục cũ" % m_stale, "warn")] if m_stale else []
    with D.hero("sb-mot"):
        st.markdown(D.hero_html("Storyboard · Motion, giọng thoại & animatic", "viết cách chuyển động cho từng cảnh, làm giọng, xem nhịp — trước khi tốn credit video",
                                pills), unsafe_allow_html=True)
        c = st.columns(3)
        c[0].markdown(D.stat("Motion prompt đã duyệt", f"{m_done} / {total}"), unsafe_allow_html=True)
        c[1].markdown(D.stat("Câu thoại có giọng", f"{stat.get('succeeded', 0)} / {stat['total']}" if stat["total"] else "—"), unsafe_allow_html=True)
        c[2].markdown(D.stat("Animatic", "đã dựng" if os.path.exists(out) else "chưa dựng"), unsafe_allow_html=True)
        st.markdown(D.meter((m_done / total) if total else 0, "Tiến độ motion prompt"), unsafe_allow_html=True)


def scene_voice_map(p, pid: int) -> dict:
    """scene_id -> (số câu đã có giọng, tổng số câu)."""
    out = {}
    try:
        directory = audio_lib.assets_dir(C.DATA, pid)
        items = {(e.get("scene_id"), e.get("line")): e for e in audio_lib.load(directory) if e["kind"] == "tts" and e.get("scene_id")}
        for ln in voice.planned_lines(p.conn, pid):
            e = items.get((ln["scene_id"], ln["line"]))
            done, tot = out.get(ln["scene_id"], (0, 0))
            ok = e is not None and e.get("text") == ln["text"] and e.get("state") == "succeeded"
            out[ln["scene_id"]] = (done + (1 if ok else 0), tot + 1)
    except Exception:  # noqa: BLE001 - pills are a hint, never a reason to lose the controls
        return {}
    return out


def motion_pills(r, srow: dict, voices: dict, has_image: bool, animatic_done: bool, flags=(), lint=None) -> str:
    if srow.get("motion_stale"):
        prompt = D.pill("Prompt cũ", "warn")
    elif r["state"] == "approved":
        prompt = D.pill("Prompt đã duyệt", "ok")
    else:
        prompt = D.pill("Prompt cần duyệt", "warn")
    done, tot = voices.get(r["sid"], (0, 0))
    voice_pill = D.pill("Không có thoại", "mute") if not tot else D.pill(f"Giọng {done}/{tot}", "ok" if done == tot else "warn")
    anim = D.pill("Animatic có", "ok") if animatic_done and has_image else D.pill("Animatic: thiếu ảnh", "mute") if not has_image else D.pill("Animatic: chưa dựng", "info")
    out = f"{prompt} {voice_pill} {anim}"
    if flags:
        out += " " + D.pill(f"⚑ {len(flags)} cờ", "warn")
    if lint:
        issues = lint.get("issues") or []
        out += " " + (D.pill("Rà prompt: ổn", "ok") if lint.get("ok") and not issues else D.pill(f"Rà prompt: {len(issues)} vấn đề", "warn"))
    return out
