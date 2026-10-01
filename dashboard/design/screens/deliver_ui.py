"""UI v2 helpers of the Bản giao screen (lane G, S13): pills / rows for the final check, the hero numbers. Pure presentation."""
from html import escape
from typing import Dict, List

from dashboard.design import components as D

FINAL_STATE = {"missing": ("Chưa dựng", "mute"), "fresh": ("Bản giao mới nhất", "ok"), "stale": ("Bản giao cũ", "warn")}


def state_pill(state: str) -> str:
    text, kind = FINAL_STATE.get(state, (state, "mute"))
    return D.pill(text, kind)


def qc_pills(res: Dict) -> str:
    """Result of the final check (core/final_qc) as pills: Đạt · N chặn · N cảnh báo."""
    out = []
    if res.get("ok") and not res.get("warns"):
        out.append(D.pill("Kiểm bản dựng: đạt", "ok"))
    else:
        out.append(D.pill(f"{res.get('blocks', 0)} lỗi chặn", "bad" if res.get("blocks") else "mute"))
        out.append(D.pill(f"{res.get('warns', 0)} cảnh báo", "warn" if res.get("warns") else "mute"))
    hints = sum(1 for i in res.get("issues", []) if i.get("level") == "hint")
    if hints:
        out.append(D.pill(f"{hints} gợi ý", "info"))
    return '<div class="del-qc">' + " ".join(out) + "</div>"


def qc_rows(issues: List[Dict], marks: Dict[str, str]) -> str:
    kind = {"block": "bad", "warn": "warn", "hint": "info"}
    label = {"block": "Chặn", "warn": "Cảnh báo", "hint": "Gợi ý"}
    rows = "".join(f'<div class="del-qrow">{D.pill(label.get(i["level"], "Lưu ý"), kind.get(i["level"], "mute"))}<span>{escape(str(i["msg"]))}</span></div>'
                   for i in issues)
    return f'<div class="del-qrows">{rows}</div>' if rows else ""
