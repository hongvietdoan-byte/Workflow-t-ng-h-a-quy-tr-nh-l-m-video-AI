"""UI v2 building blocks. HTML-only pieces return strings (render with `st.html` / `st.markdown(..., unsafe_allow_html=True)`); pieces that
must hold Streamlit widgets are `st.container(key="card-…")` helpers styled by theme.css (`.st-key-card-…`). Everything user-supplied is escaped.

CONTRACT (other lanes code against these signatures — do not change without telling the integrator):
  pill(text, kind="mute", running=False) -> str          kind: ok | warn | bad | info | mute
  meter(frac, text="", invert=False) -> str                colour by completion (ui.bar_color); invert=True for money bars (full = bad)
  stat(label, value, sub="") -> str
  empty_state(title, text, ) -> str
  hero_html(title, subtitle="", pills=()) -> str
  shimmer(height_px=120) -> str
  card(key, *, border=True) / hero(key)                    context managers returning the container (use `with card("frame-12"):`)
  frame_state_pill(state) -> str                           the fixed review labels: Cần duyệt / Đang làm / Đã duyệt / Từ chối / Lỗi
"""
import re
from contextlib import contextmanager
from html import escape
from typing import Iterable, Tuple

import streamlit as st

KINDS = ("ok", "warn", "bad", "info", "mute")

# fixed review-state vocabulary (Frame.io-style, rule 9 of docs/THIET_KE_GIAO_DIEN_2026-10-01.md)
FRAME_STATES = {"review": ("Cần duyệt", "warn"), "working": ("Đang làm", "info"), "approved": ("Đã duyệt", "ok"),
                "rejected": ("Từ chối", "bad"), "failed": ("Lỗi", "bad"), "queued": ("Chờ gen", "mute")}


def pill(text: str, kind: str = "mute", running: bool = False) -> str:
    kind = kind if kind in KINDS else "mute"
    return f'<span class="v2-pill v2-{kind}{" v2-run" if running else ""}">{escape(str(text))}</span>'


def frame_state_pill(state: str) -> str:
    label, kind = FRAME_STATES.get(state, (state, "mute"))
    return pill(label, kind, running=state == "working")


def _color(frac: float, invert: bool) -> str:
    f = max(0.0, min(1.0, float(frac or 0)))
    if invert:
        return "var(--bad)" if f >= 0.9 else "var(--warn)" if f >= 0.7 else "var(--ok)"
    return "var(--ok)" if f >= 0.999 else "var(--info)" if f >= 0.67 else "var(--warn)" if f >= 0.34 else "var(--bad)"


def meter(frac: float, text: str = "", invert: bool = False) -> str:
    f = max(0.0, min(1.0, float(frac or 0)))
    label = f'<div style="font-size:13px;color:var(--muted);margin-bottom:3px">{escape(text)}</div>' if text else ""
    return (f'{label}<div class="v2-meter-row"><div class="v2-meter"><i style="width:{f * 100:.0f}%;background:{_color(f, invert)}"></i></div>'
            f'<b>{f * 100:.0f}%</b></div>')


def stat(label: str, value: str, sub: str = "") -> str:
    return (f'<div class="v2-stat"><small>{escape(label)}</small><b>{escape(str(value))}</b>'
            + (f'<small>{escape(sub)}</small>' if sub else "") + "</div>")


def empty_state(title: str, text: str = "") -> str:
    return f'<div class="v2-empty"><b>{escape(title)}</b><span>{escape(text)}</span></div>'


def hero_html(title: str, subtitle: str = "", pills: Iterable[Tuple[str, str]] = ()) -> str:
    chips = " ".join(pill(t, k) for t, k in pills)
    return (f'<div class="v2-hero-title v2-grad-text">{escape(title)}</div>'
            + (f'<div class="v2-hero-sub">{escape(subtitle)}</div>' if subtitle else "") + (f"<div>{chips}</div>" if chips else ""))


def shimmer(height_px: int = 120) -> str:
    return f'<div class="v2-shimmer" style="height:{int(height_px)}px"></div>'


@contextmanager
def card(key: str):
    """A glass card that can hold widgets: `.st-key-card-<key>`. Keys must be unique per page."""
    with st.container(key=f"card-{key}") as c:
        yield c


@contextmanager
def hero(key: str):
    with st.container(key=f"hero-{key}") as c:
        yield c


class Raw(str):
    """Pre-built, already-escaped HTML (pills, meters) to put inside a `table()` cell."""


def _cell(v) -> str:
    return str(v) if isinstance(v, Raw) else escape("" if v is None else str(v))


def table(headers, rows, cls: str = "", num_cols=(), empty: str = "Chưa có dữ liệu") -> str:
    """`v2-table` HTML (follows light/dark). Cells are escaped unless wrapped in `Raw`; `num_cols` = column indexes aligned right."""
    head = "".join(f"<th{' class=num' if i in num_cols else ''}>{escape(h)}</th>" for i, h in enumerate(headers))
    body = []
    for r in rows:
        body.append("<tr>" + "".join(f"<td{' class=num' if i in num_cols else ''}>{_cell(v)}</td>" for i, v in enumerate(r)) + "</tr>")
    if not body:
        body.append(f'<tr><td colspan="{len(headers)}" style="color:var(--muted)">{escape(empty)}</td></tr>')
    wrap = (cls.split()[0] + "wrap") if cls else ""
    return f'<div class="{wrap}"><table class="v2-table {escape(cls)}"><tr>{head}</tr>{"".join(body)}</table></div>'


_COLORED_OLD = {"warn": "orange", "ok": "green", "bad": "red"}
_COLORED_ALIAS = {"orange": "warn", "green": "ok", "red": "bad", "yellow": "warn"}


def colored(kind: str, text: str, html: bool = True) -> str:
    """Chữ màu theo trạng thái cho st.markdown (kind: warn | ok | bad; chấp nhận cả tên màu cũ orange | green | red). Cờ ui_v2 bật →
    `<span class="v2-*-text">` màu token (đạt ≥ 4.5:1 ở sáng và tối) — người gọi truyền `unsafe_allow_html=True`; tắt → `:orange[…]` / `:green[…]` / `:red[…]` như cũ.
    `html=False`: dùng được trong st.markdown KHÔNG cho HTML (vd. chi tiết trong popover) — v2 chỉ in đậm (icon ✔ ⚠ ✖ đã mang nghĩa).
    `text` là markdown (người gọi tự escape nếu có dữ liệu ngoài)."""
    from dashboard import ui
    kind = _COLORED_ALIAS.get(kind, kind)
    kind = kind if kind in _COLORED_OLD else "warn"
    if ui.v2_on():
        return f'<span class="v2-{kind}-text">{text}</span>' if html else f"**{text}**"
    return f":{_COLORED_OLD[kind]}[{text}]"


def _records(rows) -> list:
    """list[dict] | DataFrame | list[sqlite3.Row] → list[dict]."""
    if hasattr(rows, "to_dict"):
        return rows.to_dict("records")
    return [dict(r) for r in rows or []]


def data_table(rows, *, empty: str = "Chưa có dữ liệu", num_cols=(), **dataframe_kwargs) -> None:
    """Thay MỌI `st.dataframe(rows, …)` chỉ-đọc: cờ ui_v2 bật → bảng HTML `v2-table` (nền theo sáng/tối, ô được escape); cờ tắt → đúng `st.dataframe(rows, **kwargs)` như cũ.
    `height=` (pixel) → bảng cuộn trong khung cao tối đa ngần đó. `num_cols` = chỉ số cột căn phải. Không dùng cho bảng sửa được (st.data_editor)."""
    from dashboard import ui
    if not ui.v2_on():
        st.dataframe(rows, **dataframe_kwargs)
        return
    recs = _records(rows)
    headers: list = []
    for r in recs:
        for k in r:
            if k not in headers:
                headers.append(k)
    body = [[("✓" if v is True else "" if v is False else v) for v in (r.get(h) for h in headers)] for r in recs]
    html = table([str(h) for h in headers], body, num_cols=num_cols, empty=empty)
    height = dataframe_kwargs.get("height")
    if isinstance(height, int) and height > 0:
        html = f'<div class="v2-table-scroll" style="max-height:{int(height)}px">{html}</div>'
    st.markdown(html, unsafe_allow_html=True)


# ---- chú thích dạng tooltip (người dùng 02/10: bỏ nút tròn ⓘ) ------------------------------------------------------------------------
# P1 trạng thái + nút chính luôn hiện; P2 một dòng tóm tắt; P3 chi tiết = tooltip khi rê chuột / focus NGAY TRÊN dòng đó (gạch chân chấm mờ gợi ý có
# chú thích), bấm vào dòng thì mở popover đầy đủ (máy cảm ứng / bàn phím); P4 không hiện. Không còn nút ⓘ riêng.
_TIP_MAX = 420


def md_plain(md: str, limit: int = _TIP_MAX) -> str:
    """Markdown → chữ thường ngắn cho tooltip: bỏ ** và `, gạch đầu dòng → •, cắt ở `limit`."""
    out = []
    for ln in str(md or "").replace("\r", "").split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        ln = re.sub(r"^#{1,6}\s*", "", ln)
        ln = re.sub(r"^[-*]\s+", "• ", ln)
        ln = re.sub(r"<[^>]+>", "", ln).replace("**", "").replace("`", "").replace("__", "")
        out.append(ln)
    text = "\n".join(out).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:—-·") + "…"
    return text


def _first_time(key: str) -> bool:
    """True đúng LẦN ĐẦU `key` hiện ra trong phiên → chỉ lúc đó phần tử mới có lớp .v2-glow (3 nhịp vầng sáng rồi dừng). Rerun sau (autopilot 5 s…) không nháy lại."""
    try:
        seen = st.session_state.setdefault("_v2_glow_seen", set())
    except Exception:  # noqa: BLE001 - no session (bare mode): no animation
        return False
    if key in seen:
        return False
    seen.add(key)
    return True


def _attr(text: str) -> str:
    """Giá trị thuộc tính HTML an toàn trong st.markdown: escape + xuống dòng thành &#10; (dòng trống sẽ cắt khối HTML của Markdown)."""
    return escape(text, quote=True).replace("\n", "&#10;")


def tip(text_html: str, tip_md: str, key: str = "", attention: bool = False) -> str:
    """HTML: `text_html` + tooltip CSS (hiện khi rê chuột HOẶC focus bàn phím / chạm). Không cần popover → dùng được TRONG popover.
    `text_html` do người gọi escape sẵn; `tip_md` được đổi sang chữ thường và escape ở đây."""
    plain = md_plain(tip_md)
    glow = " v2-attention" if attention and key and _first_time("tip:" + key) else ""
    return (f'<span class="v2-tip{glow}" tabindex="0" data-tip="{_attr(plain)}">'
            f'{text_html}</span>')


@contextmanager
def info(key: str, label: str = "Chi tiết", help_text: str = "Bấm để xem chi tiết", anchor: str = None, attention: bool = False):
    """Chi tiết nằm trong popover; không còn nút tròn ⓘ.

        with D.info("sb-3-why", anchor="<b>Cảnh 3</b>", help_text="tóm tắt cho tooltip"):   # bấm vào chính dòng/nhãn `anchor`
            st.markdown("…long explanation…")
        with D.info("home-scope", label="Chú thích"):                                       # không có nhãn để gắn → liên kết chữ nhỏ

    `anchor` (HTML đã escape): hiện dòng đó như chữ thường; rê chuột / focus → tooltip `help_text` (con trỏ help), bấm / Enter → popover.
    `attention=True` (mặc định TẮT): chỉ cho thông tin mới / bất thường / cảnh báo — vầng sáng mờ vài nhịp ĐÚNG LẦN ĐẦU hiện ra rồi dừng.
    Popover không lồng được trong popover: bên trong popover dùng `tip()` hoặc `shell_parts.fold()`."""
    if anchor is not None:
        with st.container(key=f"infoa-{key}"):
            # tooltip tự vẽ bằng CSS (hiện khi rê chuột HOẶC focus bàn phím; ẩn khi popover đang mở) — không dùng help= của Streamlit
            # (trễ, không hiện khi focus, không theo token); chữ đã đổi sang văn bản thường + escape
            glow = " v2-attention" if attention and _first_time("info:" + key) else ""
            st.markdown(f'<div class="v2-tip-anchor{glow}" data-tip="{_attr(md_plain(help_text))}">{anchor}</div>', unsafe_allow_html=True)
            with st.popover("Chi tiết") as p:
                yield p
    else:
        with st.container(key=f"info-{key}"):
            with st.popover(label, help=help_text) as p:
                yield p


def line(text_html: str, details_md: str = "", key: str = "", attention: bool = False) -> None:
    """One summary line (HTML already escaped by the caller, e.g. made with pill()/escape). With `details_md` + `key` the line itself carries the
    tooltip (hover/focus) and opens the full details on click."""
    if details_md and key:
        with info(key, anchor=text_html, help_text=md_plain(details_md), attention=attention):
            st.markdown(details_md)
    else:
        st.markdown(text_html, unsafe_allow_html=True)


_NOTE_KINDS = {"info": ("Ghi chú", "info"), "warning": ("Lưu ý", "warn"), "warn": ("Lưu ý", "warn"), "success": ("Đã xong", "ok"),
               "mute": ("Ghi chú", "mute")}


def short_text(text: str, limit: int = 88) -> str:
    """Câu đầu / mệnh đề đầu của một đoạn dài, không có dấu markdown, cắt ở `limit`."""
    plain = text.replace("**", "").replace("`", "").replace("\n", " ").strip()
    for stop in (". ", " — ", ": ", "; "):
        cut = plain.find(stop)
        if 30 <= cut <= limit:
            return plain[:cut].rstrip(" .:;") + ("…" if stop != ". " else "")
    return plain if len(plain) <= limit else plain[:limit].rsplit(" ", 1)[0] + "…"


def note(kind: str, text: str, summary: str = "", key: str = "", attention: bool = False) -> None:
    """Thay st.info / st.warning / st.success: nhãn + MỘT dòng tóm tắt; cả đoạn `text` ở tooltip + popover khi bấm.
    `summary` trống → câu đầu của `text`; không có `key` hoặc đoạn đã ngắn → hiện nguyên văn một dòng.
    Lỗi chặn KHÔNG đi qua đây (P1: st.error)."""
    label, tone = _NOTE_KINDS.get(kind, _NOTE_KINDS["info"])
    one = summary or short_text(text)
    plain = " ".join(str(text).split())
    if key and (summary or one != plain):
        line(f'{pill(label, tone)} <span class="v2-sum">{escape(one)}</span>', text, key, attention)
    else:
        st.markdown(f'{pill(label, tone)} <span class="v2-sum">{escape(plain)}</span>', unsafe_allow_html=True)


def version_strip(n: int, current: int) -> str:
    """Dải phiên bản chỉ-đọc v1…vN (HTML; `current` = chỉ số 0..n-1 đang xem). Tự xuống dòng khi hẹp, không bị cắt “v..”."""
    n = max(int(n or 1), 1)
    cur = max(0, min(int(current or 0), n - 1))
    return '<div class="v2-vers">' + "".join(f'<span class="v2-ver{" on" if i == cur else ""}">v{i + 1}</span>' for i in range(n)) + "</div>"


ONE_CLICK = ("approve_all", "btn_ok_all", "script-cta-budget_")    # chỉ việc DUYỆT (đảo lại được); xóa / bỏ vẫn hỏi Có/Không


def one_click(key: str) -> bool:
    """Người dùng 07/10 (Đợt 3, 'nhiều nút thành 1 nút'): with chat_first on, the approve-everything buttons act on one click — the label
    already says how many (or how much); delete-type confirmations keep their question."""
    from core import chat_intake
    return chat_intake.enabled() and any(key == k or (k.endswith("_") and key.startswith(k)) for k in ONE_CLICK)


def confirm_all(key: str, ids, label: str, question: str, container=st, yes_label: str = "Có, duyệt hết", primary: bool = False,
                stretch: bool = False) -> bool:
    """MỘT nút (“duyệt hết”, “xóa”…) rồi hỏi Có/Không; True chỉ khi người dùng bấm Có. Câu hỏi gắn với đúng tập `ids`: tập đổi → hỏi lại.
    Bản dùng chung của common.confirm_all (cùng khóa `key`, `key_yes`, `key_no`, `ask_<key>`); `primary` = nút đầu là nút chính của vùng."""
    ids = tuple(ids)
    extra = {"width": "stretch"} if stretch else {}
    if one_click(key):                                    # cờ chat_first (Đợt 3): duyệt hàng loạt = một click, số lượng đã ghi trên nút
        return container.button(label, key=key, disabled=not ids, type="primary" if primary else "secondary", **extra)
    pending_key = f"ask_{key}"
    if st.session_state.get(pending_key) not in (None, ids):
        st.session_state[pending_key] = None  # the list changed since the question: forget it
    if st.session_state.get(pending_key) != ids:
        if container.button(label, key=key, disabled=not ids, type="primary" if primary else "secondary", **extra):
            st.session_state[pending_key] = ids
            st.rerun()
        return False
    container.warning(question)
    yes, no = container.columns(2)
    if yes.button(yes_label, key=f"{key}_yes", type="primary"):
        st.session_state[pending_key] = None
        return True
    if no.button("Không", key=f"{key}_no"):
        st.session_state[pending_key] = None
        st.rerun()
    return False


@contextmanager
def cta_box(key: str):
    """Hộp của MỘT nút chính lớn của màn (cao 3,5 rem, chữ 17 px, toàn chiều rộng): `.st-key-cta-<key>`; mọi nút trong hộp (kể cả confirm_all) lớn như nhau."""
    with st.container(key=f"cta-{key}") as c:
        yield c


def cta(label: str, key: str, **kwargs) -> bool:
    """Nút chính lớn (type="primary", full width) trong `cta_box`. `kwargs` như st.button (on_click, args, disabled, help…)."""
    kwargs.setdefault("type", "primary")
    kwargs.setdefault("width", "stretch")
    with cta_box(f"btn-{key}"):
        return st.button(label, key=key, **kwargs)


def grid(count: int, cols: int = 3, gap: str = "small") -> list:
    """Lưới `cols` cột cho `count` thẻ: trả về danh sách `count` cột (mỗi `cols` cột là một hàng st.columns):

        for item, col in zip(items, D.grid(len(items), 3)):
            with col, D.card(f"x-{item.id}"): …
    """
    out = []
    cols = max(int(cols), 1)
    count = max(int(count), 0)
    for start in range(0, count, cols):
        row = st.columns(cols, gap=gap)
        out.extend(row[: min(cols, count - start)])
    return out
