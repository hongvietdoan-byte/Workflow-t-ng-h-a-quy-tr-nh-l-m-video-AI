"""M8.0 "An toàn tiền" (cờ `safe_paid_buttons`; sổ quyết định ep-2210-qf-money-safety-first, ep-2210-qd2-hard-stop-automated-only,
ep-2210-e2-approve-all-preview; docs/KE_HOACH_DASHBOARD_DON_GIAN_2026-10-21.md mục 8).

1. `paid_button` — nút tốn tiền = GIÁ trên nút + XÁC NHẬN một lần (bấm → hỏi "… · ≈ X USD — chạy thật?" Có / Không). `ask=False` chỉ
   dùng khi chính nút đã là bước xác nhận của một việc người dùng vừa làm (vd tin chat đã gõ + Enter → nút "📨 Gửi · ≈ X USD").
2. Hoàn tác — việc lớn bấm tay ("✔ Duyệt storyboard → gửi video", "✔ Đã duyệt — tiếp tục") sau khi xác nhận KHÔNG chạy ngay: ghi vào hàng
   chờ CỦA PHIÊN TRÌNH DUYỆT (st.session_state, không ghi CSDL) với hạn `not_before` = bây giờ + UNDO_SEC. Không luồng nền nào thấy hàng
   chờ này → không thể gửi trước hạn; "↩ Hoàn tác" xóa mục (0 USD). Tới hạn, khung `undo_bar` (vẽ ở mọi màn, tự chạy lại mỗi giây) mới
   làm đúng việc của nút cũ. Đóng trang trước hạn = KHÔNG gửi gì (nói rõ trên thanh). Luồng tự động (autopilot, tải lô, CLI) không đi qua
   đây — chặn cứng của luồng tự động là việc riêng (Q-D).
Cờ tắt → nút như cũ (bấm là chạy), giá vẫn hiện trên nhãn.
M8.0b: ~35 nút "chỉ có giá" dùng paid_button; "Duyệt tất cả" xem trước + HOLD + hẹn (dashboard/approve_preview.py); "✔ Mẫu thử ổn" hẹn
hoàn tác; khóa hỏi `paid_ask_<key>` của nút không còn được vẽ cả một lượt chạy bị bỏ (begin_run ở đầu app.main, mark_drawn ở paid_button).
"""
import time
import uuid
from typing import Callable, Dict, List, Optional

import streamlit as st

FLAG = "safe_paid_buttons"
UNDO_SEC = 30
UNDO_KEY = "_paid_undo"
RUN_KEY = "_paid_run"          # M8.0b: số lượt chạy cả trang (app.main gọi begin_run)
DRAWN_KEY = "_paid_drawn"      # {key nút: lượt chạy vẽ nút gần nhất}
ASK_PREFIX = "paid_ask_"


def enabled() -> bool:
    from core import features
    return features.on(FLAG)


# ---- 0. khóa hỏi treo (M8.0b) --------------------------------------------------------------------------------------------------
def begin_run(ss) -> int:
    """Đầu mỗi lượt chạy cả trang (app.main): tăng số lượt; bỏ `paid_ask_<key>` của nút KHÔNG được vẽ ở lượt trước (lượt vẽ cuối
    < lượt này - 1) — đổi màn / đóng khung rồi quay lại không còn thấy hộp hỏi cũ. Chạy lại riêng một fragment không qua đây (nút trong
    fragment vẫn mang lượt hiện tại)."""
    run = int(ss.get(RUN_KEY) or 0) + 1
    ss[RUN_KEY] = run
    drawn = ss.get(DRAWN_KEY)
    if not isinstance(drawn, dict):
        drawn = {}
        ss[DRAWN_KEY] = drawn
    for k in [k for k in list(ss.keys()) if isinstance(k, str) and k.startswith(ASK_PREFIX)]:
        last = drawn.get(k[len(ASK_PREFIX):])
        if last is None or last < run - 1:
            ss.pop(k, None)
    for k in [k for k, last in drawn.items() if last < run - 1]:
        drawn.pop(k, None)
    return run


def mark_drawn(ss, key: str) -> None:
    drawn = ss.get(DRAWN_KEY)
    if not isinstance(drawn, dict):
        drawn = {}
        ss[DRAWN_KEY] = drawn
    drawn[key] = int(ss.get(RUN_KEY) or 0)


# ---- 1. nút có giá + xác nhận một lần ----------------------------------------------------------------------------------------
def paid_button(label: str, key: str, tag: str, container=None, *, ask: bool = True, free: bool = False,
                off_tag: Optional[str] = None, question: Optional[str] = None, yes_label: str = "Có, chạy", **kwargs) -> bool:
    """Nút tốn tiền. `tag` = chữ giá do hàm ước tính có sẵn tính (cost.llm_button_tag, cost.video_batch_tag …) — bắt buộc; cờ BẬT mà
    rỗng thì ghi "chưa có giá" (không im lặng). True chỉ khi người dùng đã xác nhận (cờ tắt / ask=False: khi bấm nút).
    Cờ TẮT: nhãn = `label + tag` đúng như nút cũ (M8.0b — nút cũ không có giá thì không thêm chữ).
    `free` = ĐIỀU KIỆN lần bấm này 0 USD (vd phụ đề giữ nguyên ngôn ngữ, xuất bản không dịch) → nút thường, không hỏi; không được là
    hằng True (tests/test_safe_paid_buttons.py)."""
    box = container if container is not None else st
    if free or not enabled():
        return box.button(label + ((tag or "") if off_tag is None else off_tag), key=key, **kwargs)
    tag = tag or " · chưa có giá"
    text = label + tag
    if not ask:
        return box.button(text, key=key, **kwargs)
    ss = st.session_state
    mark_drawn(ss, key)
    pending = f"{ASK_PREFIX}{key}"
    if kwargs.get("disabled"):
        ss.pop(pending, None)
    if not ss.get(pending):
        if box.button(text, key=key, **kwargs):
            ss[pending] = True
            st.rerun()
        return False
    box.warning(question or f"**{label.strip()}**{tag} — chạy thật, tốn tiền. Chạy không?")
    row = box.container(horizontal=True)
    if row.button(yes_label + tag, key=f"{key}_yes", type="primary"):
        ss.pop(pending, None)
        return True
    if row.button("Không", key=f"{key}_no"):
        ss.pop(pending, None)
        st.rerun()
    return False


# ---- 2. hàng chờ hoàn tác (thuần, kiểm bằng dict) ------------------------------------------------------------------------------
def schedule(ss, action: str, pid: int, what: str, tag: str = "", now: Optional[float] = None, **extra) -> str:
    """Ghi một việc chờ hết hạn hoàn tác vào `ss` (session_state). Cùng việc + cùng dự án đang chờ → giữ mục cũ (bấm hai lần không
    gửi hai lần). Trả id mục."""
    items = ss.setdefault(UNDO_KEY, {})
    for uid, it in items.items():
        if it["action"] == action and it["pid"] == pid:
            return uid
    uid = uuid.uuid4().hex[:10]
    items[uid] = dict(extra, action=action, pid=pid, what=what, tag=tag, not_before=(now or time.time()) + UNDO_SEC)
    return uid


def pending(ss, pid: Optional[int] = None) -> List[Dict]:
    items = ss.get(UNDO_KEY) or {}
    return [dict(it, id=uid) for uid, it in items.items() if pid is None or it["pid"] == pid]


def waiting(ss, action: str, pid: int) -> bool:
    return any(it["action"] == action for it in pending(ss, pid))


def cancel(ss, uid: str) -> bool:
    """↩ Hoàn tác: bỏ mục — chưa có gì được gửi."""
    return (ss.get(UNDO_KEY) or {}).pop(uid, None) is not None


def take_due(ss, now: Optional[float] = None, force: Optional[str] = None) -> List[Dict]:
    """Lấy RA (xóa khỏi hàng chờ trước khi chạy → không chạy hai lần) các mục đã hết hạn hoàn tác; `force` = id mục người dùng bấm
    "Gửi ngay". Đây là lựa chọn có chủ ý để bỏ qua đồng hồ hoàn tác sau khi thấy nút riêng; nó chỉ bỏ qua thời gian chờ, không bỏ
    qua kiểm tra khi tới hạn: mọi mục vẫn đi qua `run_item` (cổng + fingerprint cho resume, danh sách + HOLD cho bulk, trạng thái mẫu
    cho pilot). Xóa trước khi chạy giữ bảo đảm một lần kể cả khi kiểm tra chặn hoặc phần thực thi lỗi."""
    items = ss.get(UNDO_KEY) or {}
    now = time.time() if now is None else now
    due = [uid for uid, it in items.items() if it["not_before"] <= now or uid == force]
    return [dict(items.pop(uid), id=uid) for uid in due]


# ---- 3. việc thật khi hết hạn ---------------------------------------------------------------------------------------------------
def _resume(p, it: Dict, start: Callable) -> str:
    """Việc cũ của nút "✔ Duyệt storyboard → gửi video" / "✔ Đã duyệt — tiếp tục": autopilot.resume + chạy nền. Trạng thái đổi trong lúc
    chờ (cổng khác, storyboard đổi ảnh) → KHÔNG gửi, nói lý do (người dùng đã đồng ý với đúng tập lúc bấm)."""
    from core import autopilot, storyboard_gate
    pid = it["pid"]
    gate = autopilot.get_gates(p, pid).get("waiting_for")
    if gate != it.get("waiting_for"):
        return f"Không gửi: trạng thái dự án đã đổi trong lúc chờ hoàn tác (chờ “{gate or 'không'}”) — xem lại rồi bấm lại."
    if it.get("fp") is not None and list(storyboard_gate.fingerprint(p, pid)) != list(it["fp"]):
        return "Không gửi: ảnh storyboard đã đổi trong lúc chờ hoàn tác — xem lại rồi bấm duyệt lại."
    autopilot.resume(p, pid, p.actor)
    try:                                                # cổng đã mở; khởi chạy nền lỗi → nói rõ, không báo "Đã gửi"
        ok = start(pid, it.get("user"))
    except Exception as e:  # noqa: BLE001 - nói lỗi cho người bấm
        return f"Đã duyệt nhưng chưa khởi chạy ({e}) — bấm ▶ Tiếp tục."
    if ok is False:                                     # Manager.start: False = lượt chạy đang sống / đã xếp hàng → nó tự đi tiếp
        return "Đã duyệt — chạy tự động đang chạy sẵn nên tự đi tiếp, không mở lượt mới."
    return ""


def _approve(p, it: Dict, start: Callable) -> str:
    """M8.0b E2: "Duyệt tất cả" đã xác nhận + hết hạn hoàn tác → duyệt đúng các mục đủ điều kiện lúc bấm (so lại, đổi thì không duyệt)."""
    from dashboard import approve_preview
    return approve_preview.run(p, it)


def _pilot_release(p, it: Dict, start: Callable) -> str:
    """M8.0b: "✔ Mẫu thử ổn — gen phần còn lại" hết hạn hoàn tác → mở gen cả lô, CHỈ khi mẫu thử vẫn đúng như lúc bấm."""
    from core import pilot
    state = pilot.get(p, it["pid"])
    if not state.get("enabled") or state.get("released") or list(state.get("scenes") or []) != list(it.get("scenes") or []):
        return "Không mở gen cả lô: mẫu thử đã đổi trong lúc chờ hoàn tác (bật/tắt, đổi cảnh hoặc đã mở) — xem lại rồi bấm lại."
    if not pilot.done(p, it["pid"]):
        return "Không mở gen cả lô: còn ảnh thử chưa duyệt (có ảnh bị bỏ duyệt trong lúc chờ hoàn tác) — xem lại rồi bấm lại."
    pilot.release(p, it["pid"])
    return ""


ACTIONS: Dict[str, Callable] = {"resume": _resume, "approve_images": _approve, "approve_motion": _approve, "approve_clips": _approve,
                                "pilot_release": _pilot_release}


def _paid_batch(p, it, start):
    from dashboard import paid_batch_preview
    return paid_batch_preview.run(p, it)


ACTIONS["paid_batch"] = _paid_batch


def run_item(p, it: Dict, start: Callable) -> str:
    """Chạy việc của một mục đã hết hạn. Trả "" khi đã gửi, hoặc câu nói vì sao không gửi."""
    fn = ACTIONS.get(it["action"])
    if fn is None:
        return f"Không gửi: việc “{it['action']}” không còn trong danh sách."
    return fn(p, it, start)


def resume_args(p, pid: int, with_fp: bool) -> Dict:
    """Ảnh chụp trạng thái lúc người dùng xác nhận (so lại khi hết hạn)."""
    from core import autopilot, storyboard_gate
    out = {"waiting_for": autopilot.get_gates(p, pid).get("waiting_for")}
    if with_fp:
        out["fp"] = list(storyboard_gate.fingerprint(p, pid))
    return out


# ---- 4. Streamlit: hẹn + thanh hoàn tác ------------------------------------------------------------------------------------------
def schedule_resume(p, pid: int, what: str, tag: str, log_detail: str, with_fp: bool = True) -> None:
    """Sau khi người dùng xác nhận: cờ bật → hẹn (hoàn tác được UNDO_SEC giây); cờ tắt → chạy ngay như cũ."""
    from dashboard import common as C
    if not enabled():
        from core import autopilot
        autopilot.resume(p, pid, p.actor)
        C.autopilot_manager(C.DB, C.DATA).start(pid, user=C.access_user())
        C.log_ui(p, "gen_video", page="storyboard", project_id=pid, detail=log_detail)
        return
    schedule(st.session_state, "resume", pid, what, tag, actor=p.actor, user=C.access_user(), log=log_detail,
             **resume_args(p, pid, with_fp))
    C.log_ui(p, "hen_gui", page="storyboard", project_id=pid, detail=f"{log_detail} — chờ {UNDO_SEC} s hoàn tác")


def undo_bar() -> None:
    """Vẽ ở mọi màn (app.main) khi phiên này có việc chờ hoàn tác — không có việc thì không vẽ gì (không tự chạy lại vô ích)."""
    if pending(st.session_state):
        _undo_fragment()


@st.fragment(run_every=1)
def _undo_fragment() -> None:
    from core.db import connect
    from core.pipeline import Pipeline
    from dashboard import common as C
    ss = st.session_state
    due = take_due(ss, force=ss.pop("_paid_undo_now", None))
    if due:
        for it in due:
            conn = connect(C.DB)
            try:
                p = C.scoped(Pipeline(conn))
                p.actor = it.get("actor")
                try:
                    why = run_item(p, it, lambda pid, user: C.autopilot_manager(C.DB, C.DATA).start(pid, user=user))
                except Exception as e:  # noqa: BLE001 - nói lỗi, không nuốt; mục đã ra khỏi hàng chờ nên không lặp
                    why = f"Không gửi được: {e}"
                if why:
                    st.session_state["_paid_undo_note"] = why
                else:                                    # M8.0b: mục duyệt hàng loạt / mẫu thử mang sự kiện + trang của nó
                    C.log_ui(p, it.get("event") or "gen_video", page=it.get("page") or "storyboard", project_id=it["pid"],
                             detail=it.get("log") or it["what"])
                    st.toast(f"{it.get('done') or 'Đã gửi'}: {it['what']}")
            finally:
                conn.close()                             # rà kỹ M8.0: mỗi lần tới hạn mở một kết nối → đóng ngay
        st.rerun(scope="app")
    note = ss.pop("_paid_undo_note", None)
    if note:
        st.warning(note)
    now = time.time()
    for it in pending(ss):
        left = max(0, int(round(it["not_before"] - now)))
        with st.container(border=True, key=f"paid_undo_{it['id']}"):
            verb = it.get("verb") or "gửi"
            st.markdown(f"⏳ **{it['what']}**{it['tag']} — máy {verb} sau **{left} giây**. Chưa {verb} gì, chưa tốn tiền; "
                        f"đóng trang trước hạn cũng KHÔNG {verb}.")
            row = st.container(horizontal=True)
            if row.button(f"↩ Hoàn tác ({left} s)", key=f"paid_undo_cancel_{it['id']}", type="primary"):
                cancel(ss, it["id"])
                st.toast("Đã hoàn tác — chưa gửi gì, 0 USD.")
                st.rerun(scope="app")
            if row.button(f"▶ {(it.get('verb') or 'gửi').capitalize()} ngay", key=f"paid_undo_now_{it['id']}"):
                ss["_paid_undo_now"] = it["id"]
                st.rerun(scope="fragment")
