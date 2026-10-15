"""C2 (15/10): the reason picker in front of every Loại / Vẽ lại / Loại & gen lại button (image + video). The button stays disabled until a
reason of the fixed list (core/lessons.REJECT_REASONS) is chosen — 'Khác' also needs words. Claude driving the Dashboard (?op=claude)
goes through the same picker: no reject without a reason from the screen."""
from typing import Optional, Tuple

import streamlit as st

from core import lessons

_NONE = "—"


def pick(key: str, label: str = "Lý do loại (bắt buộc)") -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """(code, words of 'Khác', error). `error` None = the reject button may be pressed; else it is the button's help text."""
    codes = [_NONE] + list(lessons.REJECT_REASONS)
    code = st.selectbox(label, codes, key=f"rreason_{key}",
                        format_func=lambda c: "— chọn lý do —" if c == _NONE else lessons.REJECT_REASONS[c][0])
    code = None if code == _NONE else code
    text = None
    if code == lessons.OTHER:
        text = st.text_input("Ghi rõ lý do 'Khác'", key=f"rreason_txt_{key}")
    return code, text, lessons.reject_reason_error(code, text)


def detail(code: Optional[str], text: Optional[str]) -> str:
    """For the action log (C.log_ui detail): the reason code (+ that words were written)."""
    return f"lý do: {code or lessons.NO_REASON}" + (" (có chữ)" if (text or "").strip() else "")
