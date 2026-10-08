"""Khung ứng dụng v2 (S13 nhánh B): dải hero của dự án + nút "Đặt lại 2 thanh về 0" (chỉ Owner, S14.39). Chỉ được gọi khi cờ ui_v2 bật.

Không đụng core: số liệu lấy từ những hàm app.py/header.py đã dùng (lineage, autopilot, project_budget, money_reset)."""
from html import escape
from typing import Callable, List, Tuple

import streamlit as st

from dashboard.design import components as D

# màn (chỉ số trong common.STEPS) → số bước của next_step.next_action
_NEXT_STEP = {1: 1, 2: 2, 3: 4, 4: 5}


def overall_progress(p, pid: int, done: list) -> float:
    """0..1 over the five stages: script (Bible locked) · pictures · motion · clips · final render. `done` = app.step_done()."""
    from core import lineage
    summ = lineage.summary(p.conn, pid)
    n = summ["total"]
    parts = [1.0 if done and done[0][0] == "done" else 0.0]
    for key in ("images", "motion", "videos"):
        parts.append(min(summ[key][0] / n, 1.0) if n else 0.0)
    rendered = len(done) > 4 and done[4][0] == "done"
    parts.append(1.0 if rendered else 0.0)
    from dashboard import quality_ui
    if quality_ui.enabled() and n:      # N4 (5a.8): clip = nháp → duyệt nháp → bản cao / gen thẳng; bản dựng còn nháp = DRAFT (nửa chặng)
        clip, _ = quality_ui.clip_progress(p.conn, pid)
        parts[3] = min(parts[3], clip)
        if rendered and quality_ui.draft_scenes(p.conn, pid):
            parts[4] = 0.5
    return sum(parts) / len(parts)


def status_pills(p, pid: int, proj) -> List[Tuple[str, str]]:
    from core import autopilot
    out: List[Tuple[str, str]] = []
    if proj["paused"]:
        out.append(("Tạm dừng", "warn"))
    ap = autopilot.status(p, pid)
    out.append({"running": ("Tự động: đang chạy", "info"), "queued": ("Tự động: đang xếp hàng", "info"),
                "waiting": ("Tự động: chờ bạn", "warn"), "needs_attention": ("Tự động: cần xem", "bad")
                }.get(ap["state"], ("Tự động: không chạy", "mute")))
    try:
        from core import project_budget
        if project_budget.enabled():                     # user 08/10: only "Tự chạy trong trần" has a budget to lock
            data = project_budget.get(p.conn, pid) or {}
            if data.get("locked"):
                out.append(("Ngân sách đã khóa", "ok"))
            elif project_budget.needs_lock(p, pid) and not project_budget.finished(p.conn, pid):
                out.append(("Ngân sách chưa khóa", "warn"))
    except Exception:  # noqa: BLE001 - a status chip only
        pass
    return out


NEXT_ERROR = "Không đọc được việc tiếp theo — thử tải lại (đã ghi vào ⚙ Chẩn đoán)."


def next_line(p, pid: int, screen_index: int, data_dir: str) -> Tuple[str, str]:
    """(text, level) of the one-line "việc tiếp theo" for the current screen, read by code (dashboard/next_step.py)."""
    from dashboard import next_step
    step = _NEXT_STEP.get(screen_index, 1)
    try:
        res = next_step.next_action(p, pid, step, data_dir)
    except Exception as e:  # noqa: BLE001 - the strip must never break the page; S14.8 U3: say so + diag, not "nothing to do"
        next_step.note_error(p, pid, step, e)
        return NEXT_ERROR, "warn"
    if not res:
        return "Chưa có việc nào đang chờ.", "done"
    if res[1] == "todo":                                  # cờ chat_first: nói 'nút sáng xanh' chỉ khi glow_ui thật sự thắp một nút
        from dashboard import glow_ui
        try:
            lit = glow_ui.targets(p, pid, screen_index)
        except Exception:  # noqa: BLE001 - a hint only; the line itself still shows
            lit = []
        if lit:
            return "🟢 Nút sáng xanh: " + res[0], res[1]
    return res


def cut_words(text: str, limit: int = 96) -> str:
    """S14.8 U5 (đổi tên từ short_text — khác components.short_text vốn tìm câu/mệnh đề đầu): one-line version of a longer sentence (cut at a word, with …); the caller puts the full text in a ⓘ when this differs."""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:—-·")
    return cut + "…"


def fold(label: str, body_md: str = "") -> None:
    """Chi tiết TRONG một POPOVER (popover không lồng được trong popover → mục gập có nhãn chữ; 02/10: bỏ glyph ⓘ cùng nút tròn)."""
    with st.expander("Chi tiết · " + label):
        if body_md:
            st.markdown(body_md)


_STAGES = ("Kịch bản", "Ảnh", "Motion", "Clip", "Bản giao")


def progress_details(pid: int, done: list, p=None) -> str:
    """The ⓘ of the overall-progress meter: what the percentage is made of + the per-stage state (the old meter label said the same in one line)."""
    mark = {"done": "xong", "stale": "đã cũ", "todo": "chưa xong"}
    rows = []
    for i, name in enumerate(_STAGES):
        state, text = done[i] if i < len(done) else ("todo", "")
        rows.append(f"- **{name}**: {mark.get(state, state)}" + (f" ({text})" if text else ""))
    from dashboard import quality_ui
    if p is not None and quality_ui.enabled():          # N4: chặng thật của clip + bản dựng DRAFT
        _, counts = quality_ui.clip_progress(p.conn, pid)
        line = quality_ui.progress_lines(counts)
        if line:
            rows.append(f"- **Clip 2 bậc**: {line}")
        note = quality_ui.draft_render_note(p.conn, pid)
        if note:
            rows.append(f"- **Bản dựng**: {note} — chưa phải bản cuối")
    return ("Tiến độ tổng = trung bình 5 phần: kịch bản (Bible đã khóa) · ảnh · motion · clip · bản giao.\n\n" + "\n".join(rows)
            + f"\n\nDự án #{pid}")


def project_hero(p, pid: int, done: list, screen_index: int, data_dir: str, level_fn: Callable) -> None:
    """The strip under the top bar on project screens: name · status pills · overall progress · 🎚 level · next step.
    Priority (docs/QUY_TAC_BO_CUC_UI_V2 §5): state pills + progress % + ONE next-step line outside; the breakdown, the project number and a
    long next-step sentence live in ⓘ."""
    proj = p.project(pid)
    frac = overall_progress(p, pid, done)
    text, level = next_line(p, pid, screen_index, data_dir)
    icon = {"wait": "⏸ ", "todo": "👉 Việc tiếp theo: ", "done": "✅ ", "warn": "⚠ "}.get(level, "")
    short = cut_words(text)
    with D.hero("shell"):
        # 02/10 (rà soát #10): hai CỘT liền thay cho hai hàng × hai cột — trước đây "Việc tiếp theo" bị căn giữa theo khối 🎚 cao bên phải
        # nên cách xa các pill; nay mỗi cột xếp sát từ trên xuống.
        left, right = st.columns([5, 4], vertical_alignment="top")
        with left:
            st.html(D.hero_html(proj["name"], "", status_pills(p, pid, proj)))
            if short != " ".join(text.split()):
                with D.info("shell-next", anchor=f'<div class="v2-note shell-next">{escape(icon + short)}</div>', help_text=D.md_plain(icon + text)):
                    st.markdown(icon + text)
            else:
                st.html(f'<div class="v2-note shell-next">{escape(icon + short)}</div>')
        with right:
            with D.info("shell-progress", anchor=D.meter(frac, "Tiến độ tổng"), help_text=D.md_plain(progress_details(pid, done, p))):
                st.markdown(progress_details(pid, done, p))
            with st.container(key="shell-level"):
                level_fn()


# ---- 💵 màu thanh theo mức dự tính (S14.16, core.money_policy) -------------------------------------------------------------------

_MONEY_COLOR = {"ok": "var(--ok)", "warn": "var(--warn)", "danger": "var(--bad)"}


def money_meter(spent: float, planned: float, text: str = "") -> str:
    """A 💵 meter coloured by the planned amount (chính sách tiền 04/10): green, yellow at ≥ money_policy.WARN_AT, red at ≥ DANGER_AT.
    The bar fills to 100 %; the number says the real share (it may pass 100 % — the caps warn, they do not stop)."""
    from core import money_policy
    share = float(spent or 0) / float(planned) if planned else 0.0
    color = _MONEY_COLOR[money_policy.level(spent, planned)]
    label = f'<div style="font-size:13px;color:var(--muted);margin-bottom:3px">{escape(text)}</div>' if text else ""
    return (f'{label}<div class="v2-meter-row"><div class="v2-meter"><i style="width:{min(share, 1.0) * 100:.0f}%;background:{color}">'
            f'</i></div><b>{share * 100:.0f}%</b></div>')


def money_flag(spent: float, planned: float) -> str:
    """' 🟡' / ' 🔴' after the 💵 label when the money passed the planned amount / passed it far ('' otherwise)."""
    from core import money_policy
    return {"warn": " 🟡", "danger": " 🔴"}.get(money_policy.level(spent, planned), "")


# ---- 💵 Đặt lại thanh tiền (chỉ Owner) -------------------------------------------------------------------------------------------

def last_reset_line(conn, bar: str, key=None) -> str:
    """HTML "Đặt lại lần cuối: <lúc> bởi <ai> — <vì sao>" ('' when never reset)."""
    from core import money_reset
    rec = money_reset.last(conn, bar, key)
    if not rec:
        return ""
    return (f'<div class="shell-last">Đặt lại lần cuối: {escape(str(rec.get("at", "")))} bởi {escape(str(rec.get("who", "?")))}'
            f' — {escape(str(rec.get("why", "")))}</div>')


def last_reset_md(conn, bar: str, label: str, key=None) -> str:
    """Markdown bullet "<label>: đặt lại lần cuối …" for the ⓘ of the 💵 card ('' when never reset)."""
    from core import money_reset
    rec = money_reset.last(conn, bar, key)
    if not rec:
        return ""
    return f"- **{label}** — đặt lại lần cuối: {rec.get('at', '')} bởi {rec.get('who', '?')} — {rec.get('why', '')}"


def summary_error(e: Exception) -> str:
    """Caption for "the estimate could not be computed" (what failed + what to do)."""
    return (f"Chưa tính được phần đã chi + ước tính phần còn lại: {str(e)[:160] or type(e).__name__}. Cách xử lý: kiểm tra dự án đã tách "
            "cảnh và bảng giá (⚙ Cài đặt), rồi tải lại trang; vẫn lỗi thì gửi báo cáo ở ⚙ Chẩn đoán.")


def summary_detail_md(cs: dict) -> str:
    """Per-part lines of project_budget.cost_summary for the "Chi tiết" fold (markdown, every `$` escaped)."""
    from core import project_budget
    audio = f"≈ ${cs['audio']:.2f}" if cs.get("audio") is not None else f"{cs.get('audio_items', 0)} lượt (chưa có giá USD, tính theo lượt)"
    rows = [f"- Ảnh ≈ ${cs['images']:.2f}", f"- Video ≈ ${cs['videos']:.2f}", f"- Âm thanh {audio}", f"- Claude ≈ ${cs['claude']:.2f}"]
    rows.append(f"- chat Kịch bản: đã chi ${cs.get('chat_spent', 0):.2f} · lượt kế ≈ ${cs.get('chat_est', 0):.2f} (đã nằm trong Claude, không cộng lần hai)")
    note = (f"{cs['unpriced']} mục chưa có giá được ước bằng giá cao nhất × 1,5." if cs.get("unpriced")
            else "Mọi mục đều có giá (giá cao nhất × 1,5 chỉ dùng khi thiếu giá).")
    return project_budget.md_safe("\n".join(rows) + f"\n\n{note}")


def reset_two_button(p, actor: dict) -> None:
    """S14.39: the ONE reset of the 💵 card: "↺ Đặt lại 2 thanh về 0" = Đợt thử starts a new budget round + Claude API restarts its count
    (core.budget_rounds.reset_two). Owner: one yes/no question, no reason to type (default reason, written to the audit log); anyone
    else sees the locked button with the reason. The ledger is untouched. core refuses non-owners too (this is not the guard)."""
    from core import budget_rounds
    from dashboard.common import confirm_all
    if (actor or {}).get("role") != "owner":
        st.button("↺ Đặt lại 2 thanh về 0", key="shell_mr_two", disabled=True, width="stretch",
                  help="Chỉ Owner được đặt lại thanh tiền — nhờ Owner nếu cần.")
        return
    if confirm_all("shell_mr_two", ("two",), "↺ Đặt lại 2 thanh về 0",
                   "Đặt lại 2 thanh (Đợt thử + Claude API) về 0? Đợt thử bắt đầu đợt ngân sách mới (đóng đợt cũ + lưu tóm tắt), "
                   "Claude API đếm lại từ bây giờ. Mức dự tính giữ nguyên, sổ chi giữ nguyên, việc này được ghi nhật ký.",
                   st, "Có, đặt lại"):
        try:
            out = budget_rounds.reset_two(p.conn, actor)
        except Exception as e:  # noqa: BLE001 - shown, never a crash of the bar
            st.error(f"Không đặt lại được: {e}")
            return
        st.toast(f"Đã đặt lại 2 thanh · mở «{out['opened']['name']}»")
        st.rerun()
