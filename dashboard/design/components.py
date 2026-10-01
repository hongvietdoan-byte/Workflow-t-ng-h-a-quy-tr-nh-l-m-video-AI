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
