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


# ---- progressive disclosure (người dùng 01/10): chi tiết ưu tiên thấp nằm trong dấu ⓘ, bên ngoài chỉ tóm tắt ------------------------------
@contextmanager
def info(key: str, label: str = "ⓘ", help_text: str = "Xem chi tiết"):
    """A small ⓘ button that opens a popover with the details; put the long text / lists / secondary controls inside it:

        with D.info("sb-3-why"):
            st.markdown("…long explanation…")

    Priority rule (docs/QUY_TAC_BO_CUC_UI_V2.md §5): P1 state + the main action stay visible; P2 gets ONE summary line; P3 goes in ⓘ;
    P4 (rarely useful) is not shown at all. The button always has the visible glyph "ⓘ" (never hover-only); click or keyboard opens it."""
    with st.container(key=f"info-{key}"):
        with st.popover(label, help=help_text) as p:
            yield p


def line(text_html: str, details_md: str = "", key: str = "") -> None:
    """One summary line (HTML already escaped by the caller, e.g. made with pill()/escape) + a ⓘ with `details_md` when given."""
    if details_md and key:
        c1, c2 = st.columns([12, 1], vertical_alignment="center")
        c1.markdown(text_html, unsafe_allow_html=True)
        with c2:
            with info(key):
                st.markdown(details_md)
    else:
        st.markdown(text_html, unsafe_allow_html=True)
