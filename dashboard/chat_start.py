"""Tab Kịch bản kiểu chat — Đợt 2 (người dùng 07/10; cờ chat_first): bắt đầu dự án mới bằng một tin chat ở màn ⌂ (và khi chưa có dự án).
Tin đầu (chữ + tệp) tạo dự án (core/chat_flow.start_project), mở thẳng tab Kịch bản và được đưa vào khung chat của dự án như vừa gõ ở đó."""
from datetime import datetime

from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C

KEY = "home_start"


class _File:
    def __init__(self, name: str, data: bytes):
        self.name, self._data = name, data

    def getvalue(self) -> bytes:
        return self._data


class Seed:
    """What the chat input of the project would have returned for the first message (text + files)."""
    def __init__(self, text: str, files):
        self.text, self.files = text, [_File(n, d) for n, d in files]


def _start(p: Pipeline) -> None:
    """on_submit callback (runs before the widgets, so it may still switch the project picker and the step)."""
    got = st.session_state.get(KEY)
    if not got:
        return
    text = got if isinstance(got, str) else (getattr(got, "text", None) or "")
    files = [] if isinstance(got, str) else [(f.name, f.getvalue()) for f in (getattr(got, "files", None) or [])]
    p = C.scoped(Pipeline(connect(C.DB)))                     # a callback runs in another thread than the one that made `p`
    from core import chat_flow, person_limits
    try:
        pid = chat_flow.start_project(p, text, [n for n, _ in files], datetime.now().strftime("%d/%m %H:%M"),
                                      created_by=me().get("email") if auth_on() else None)
    except person_limits.LimitReached as e:
        from dashboard import limits_ui
        limits_ui.remember(e, "create")
        return
    st.session_state[f"chat_seed_{pid}"] = Seed(text, files) if files else text
    st.session_state["global_pid"] = pid
    st.session_state["step"] = STEPS[1]


def start_box(p: Pipeline) -> None:
    """The one way to start: a chat input. Nothing is paid here — the project is made, the message waits in its chat."""
    from core import chat_intake
    if not chat_intake.enabled():
        return
    with st.container(border=True):
        st.markdown("**💬 Bắt đầu dự án mới** — dán kịch bản, gõ ý tưởng, hoặc thả file kịch bản · ảnh · video · nhạc. "
                    "Tên dự án lấy từ dòng đầu; thiết lập như ➕ Dự án mới (khung dọc 9:16), đổi sau ở ⚙ Chi tiết.")
        st.chat_input("Bắt đầu dự án mới…", key=KEY, accept_file="multiple", file_type=list(chat_intake.ACCEPT),
                      on_submit=_start, args=(p,))
