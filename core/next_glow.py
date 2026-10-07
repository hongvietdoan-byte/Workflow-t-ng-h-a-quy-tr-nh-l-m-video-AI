"""Nút của bước kế sáng lên (người dùng 07/10: người mới chưa từng biết quy trình cũng dùng được; cờ `chat_first`).

MỘT đích sáng mỗi lúc: nút cần bấm ngay ("key"), tab Motion của Storyboard khi nút nằm ở tab đang ẩn ("tab"), hoặc ô của màn kế trên
thanh bước khi màn này đã xong ("step"). Thứ tự theo đường ngắn nhất đã đo (tools/ui_v2_acceptance.py clicks): Kịch bản theo nút chính
của lúc đó (step1_v2.next_kind) → Storyboard: gen ảnh → duyệt ảnh → viết motion → duyệt motion → Video: gen video → Bản giao.
Đang gen hoặc đang chạy tự động → không sáng gì (không có gì để bấm). Chỉ tính, 0 USD."""
import re
from typing import List, Optional, Tuple

Target = Tuple[str, object]
_SAFE = re.compile(r"^[A-Za-z0-9_\-]+$")
_SCRIPT = {"analyse": "box_in_{}", "plan": "script-cta_{}", "budget": "script-cta-budget_{}", "lock": "script-cta-lock_{}",
           "next": "script-cta-next_{}"}


def _any(rows, stage: str, *states: str) -> bool:
    return any(r[stage] in states for r in rows)


def target(step: int, script_kind: Optional[str], rows: List[dict], pid: int, on_motion_tab: bool = False) -> List[Target]:
    """step: 1 Kịch bản · 2 Storyboard · 3 Video (others: nothing). rows: core.stage_map.build."""
    if step == 1:
        key = _SCRIPT.get(script_kind or "")
        return [("key", key.format(pid))] if key else []
    if step == 2:
        if _any(rows, "image", "review"):
            return [("key", "approve_all")]
        if _any(rows, "image", "none", "failed", "stale"):
            return [("key", f"gen_img_{pid}")]
        if _any(rows, "image", "running"):
            return []
        tab = [] if on_motion_tab else [("tab", 2)]
        if _any(rows, "motion", "review"):
            return tab + [("key", "btn_ok_all")]
        if _any(rows, "motion", "none", "stale"):
            return tab + [("key", f"llm_mot_{pid}")]
        return [("step", "Video")] if rows else []
    if step == 3:
        if _any(rows, "video", "none", "failed", "stale"):
            return [("key", f"gen_vid_{pid}")]
        if rows and all(r["video"] == "done" for r in rows):
            return [("step", "Bản giao")]
    return []


_GLOW = ("animation: next-glow 1.6s ease-in-out infinite; border-color: #22c55e !important; "
         "box-shadow: 0 0 0 2px rgba(34,197,94,.55), 0 0 18px 4px rgba(34,197,94,.55);")
_STILL = "animation: none; box-shadow: 0 0 0 2px rgba(34,197,94,.7), 0 0 12px 3px rgba(34,197,94,.5);"
_LABEL = ('content: "👉 Bấm tiếp"; display: block; width: fit-content; margin: 0 0 4px; padding: 1px 8px; border-radius: 999px; '
          'font-size: 12px; font-weight: 600; color: #052e16; background: #22c55e;')


def css(targets: List[Target], steps: List[str]) -> str:
    """The <style> body for the targets ('' = nothing to light). A key that is not a plain widget key is never written into CSS."""
    sel = []
    for kind, val in targets:
        if kind == "key" and isinstance(val, str) and _SAFE.match(val):
            sel.append((f".st-key-{val} button, .st-key-{val}_yes button, .st-key-{val} textarea", f".st-key-{val}"))   # _yes: câu hỏi Có/Không
        elif kind == "step" and val in steps:
            sel.append((f'.st-key-step [role="radiogroup"] > label:nth-child({steps.index(val) + 1})', None))
        elif kind == "tab" and isinstance(val, int):
            sel.append((f'.st-key-sb_tab [data-baseweb="tab"]:nth-of-type({val})', None))
    if not sel:
        return ""
    glow = ", ".join(s for s, _ in sel)
    labels = ", ".join(f"{box}::before" for _, box in sel if box)
    out = ("@keyframes next-glow { 0%, 100% { box-shadow: 0 0 0 2px rgba(34,197,94,.35), 0 0 6px 1px rgba(34,197,94,.25); } "
           "50% { box-shadow: 0 0 0 2px rgba(34,197,94,.9), 0 0 22px 6px rgba(34,197,94,.6); } }\n"
           f"{glow} {{ {_GLOW} }}\n")
    if labels:
        out += f"{labels} {{ {_LABEL} }}\n"
    out += f"@media (prefers-reduced-motion: reduce) {{ {glow} {{ {_STILL} }} }}\n"
    return out


MAIN = ("script-cta_{}", "script-cta-budget_{}", "script-cta-lock_{}", "script-cta-next_{}", "gen_img_{}", "approve_all", "llm_mot_{}",
        "btn_ok_all", "gen_vid_{}")


def big_css(pid: int) -> str:
    """Người dùng 07/10: nút bước chính ở các màn làm việc to và rõ (cao hơn, chữ lớn đậm, đầy bề ngang khung chứa) — sáng hay không."""
    keys = [k.format(pid) for k in MAIN]
    sel = ", ".join(f".st-key-{k} button" for k in keys)
    return (f"{sel} {{ min-height: 3.1rem !important; font-size: 17px !important; font-weight: 700 !important; width: 100% !important; "
            "letter-spacing: .01em; }\n"
            f"{', '.join(f'.st-key-{k} button p' for k in keys)} {{ font-size: 17px !important; font-weight: 700 !important; }}\n")
