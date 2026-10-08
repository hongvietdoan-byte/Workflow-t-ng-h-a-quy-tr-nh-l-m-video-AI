"""The "next thing to do" band under each step's head (kế hoạch sau #8, S9 · E0.1 — người dùng duyệt 2026-09-28).

One line, read from the project's state by code (no model call): what the automatic run waits for, else the first thing left in this step.
Kept apart from the steps so every step shows it the same way and a test can check each rule.
"""
import json
from typing import Optional, Tuple

from core import autopilot, lineage
from core.pipeline import Pipeline

WAITING = ("waiting", "needs_attention")


def _count(conn, sql: str, args) -> int:
    return int(conn.execute(sql, args).fetchone()[0])


def _drafts(conn, pid: int) -> int:
    """N4: scenes whose clip is still the draft (0 when the two-tier flag / core.quality_tier is not there)."""
    from dashboard import quality_ui
    return len(quality_ui.draft_scenes(conn, pid)) if quality_ui.enabled() else 0


def next_action(p: Pipeline, pid: int, step: int, data_dir: str = "") -> Optional[Tuple[str, str]]:
    """(text, level) — level "wait" (the automatic run waits for you), "todo" (something left here) or "done"; None when nothing to say."""
    info = autopilot.status(p, pid)
    if info["state"] in WAITING and info["note"]:
        return f"⏸ Chạy tự động đang chờ bạn: {info['note'][:220]}", "wait"
    conn = p.conn
    scenes = _count(conn, "SELECT COUNT(*) FROM scenes WHERE project_id=?", (pid,))
    if step == 1:
        from core import chat_intake
        chat = chat_intake.enabled()                # cờ chat_first: các thẻ 1a/1c/1d không còn — chỉ vào khung chat
        if not scenes:
            return ("Dán kịch bản hoặc thả file vào khung chat rồi bấm ▶ Phân tích" if chat else
                    "Tải file hoặc dán kịch bản ở 1a rồi bấm ▶ Phân tích"), "todo"
        chars = conn.execute("SELECT locked, anchor_approved FROM characters WHERE project_id=?", (pid,)).fetchall()
        if not chars:
            return ("Bấm 🤖 Lập kế hoạch trong khung chat (Đạo diễn chia shot + Character Bible)" if chat else
                    "Chạy Director ở 1d (hoặc 🚀 Tự động hoàn toàn ở 1c)"), "todo"
        from core import project_budget
        if (project_budget.needs_lock(p, pid) and not (project_budget.get(conn, pid) or {}).get("locked")
                and not project_budget.finished(conn, pid)):     # only "Tự chạy trong trần" asks for it (user 08/10)
            return ("Duyệt & KHÓA ngân sách dự án " + ("trong khung chat" if chat else "(💵 ở 1c)")
                    + " — chạy tự động chờ bước này trước khi gen ảnh"), "todo"
        if any(c["locked"] for c in chars):         # locked = approved (a locked Bible may use the Kho pictures, no anchor)
            return "Kịch bản xong — sang màn Storyboard", "done"
        waiting_anchor = sum(1 for c in chars if not c["anchor_approved"])
        if waiting_anchor:
            return f"Duyệt ảnh mốc của {waiting_anchor} nhân vật ở " + ("⚙ Chi tiết › Nhân vật" if chat else "1e"), "todo"
        return "Bấm ✔ Duyệt & khóa → Storyboard " + ("trong khung chat" if chat else "(cuối trang)"), "todo"
    if not scenes:
        return "Chưa có kịch bản — bắt đầu ở màn Kịch bản", "todo"
    summ = lineage.summary(conn, pid)
    total = summ["total"]
    if step == 2:
        review = _count(conn, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND state='pending_review'", (pid,))
        if review:
            return f"Duyệt {review} ảnh đang chờ", "todo"
        left = total - summ["images"][0]
        if left:
            return f"Gen ảnh cho {left} cảnh chưa có ảnh duyệt", "todo"
        return "Ảnh xong — sang tab 🎞 Motion (cùng màn Storyboard)", "done"
    if step == 3:
        left = total - summ["motion"][0]
        if left:
            return f"Viết / duyệt motion prompt cho {left} cảnh", "todo"
        from core import voice
        v = voice.status(conn, pid, data_dir)
        missing = v.get("missing", 0) + v.get("failed", 0)
        if missing:
            return f"Tạo giọng thoại cho {missing} câu còn thiếu", "todo"
        return "Motion & giọng xong — sang màn Video", "done"
    if step == 4:
        review = _count(conn, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='video_gen' AND state='pending_review'", (pid,))
        if review:
            return f"Duyệt {review} clip đang chờ", "todo"
        failed = _count(conn, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='video_gen' AND state='failed'", (pid,))
        left = total - summ["videos"][0]
        if left:
            return f"Gen video cho {left} cảnh chưa có clip" + (f" ({failed} lần lỗi — xem danh sách)" if failed else ""), "todo"
        drafts = _drafts(conn, pid)
        if drafts:                          # N4 (5a.8): only drafts is not "xong"
            return (f"{drafts} cảnh còn nháp — duyệt nháp rồi ⬆ Gen bản cao (bản dựng lúc này là bản DRAFT, xem được trọn bộ)"), "todo"
        return "Video xong — sang màn Bản giao", "done"
    if step == 5:
        fin = lineage.latest_output(conn, pid, "final")
        if fin is None:
            return "Bấm ▶ Dựng video cuối (5.3)", "todo"
        try:
            qc = json.loads(fin["manifest"] or "{}").get("final_qc")
        except ValueError:
            qc = None
        if qc and qc.get("blocks"):
            return f"Bản dựng còn {qc['blocks']} lỗi chặn — xem 🔎 Kiểm bản dựng (5.5)", "todo"
        drafts = _drafts(conn, pid)
        if drafts:                          # N4 (5a.5): the render of drafts is a DRAFT, not the finished video
            return f"Bản dựng là bản DRAFT ({drafts} cảnh còn nháp) — gen bản cao ở màn Video rồi dựng lại", "todo"
        return "Xem bản giao ở 5.5 · 🔎 Kiểm bản dựng trước khi đăng", "done"
    return None


def note_error(p: Pipeline, pid: int, step: int, error: Exception) -> None:
    """S14.8 U3: reading the next step failed — keep the reason in ⚙ Chẩn đoán (core/diag never raises)."""
    from core import diag
    conn = getattr(p, "conn", None)
    if conn is None:                   # no database to write to (the band / strip still shows the error to the person)
        return
    diag.record(conn, "system", "warn", f"việc tiếp theo (bước {step}) đọc lỗi: {type(error).__name__}: {error}", "next_step_error", pid)


def band(p: Pipeline, pid: int, step: int, data_dir: str = "") -> str:
    """HTML of the band ('' when nothing to say)."""
    from html import escape
    try:
        res = next_action(p, pid, step, data_dir)
    except Exception as e:  # noqa: BLE001 - the band must never break a step; the reason is shown + kept in diag (S14.8 U3)
        note_error(p, pid, step, e)
        return f'<div class="nextband warn">⚠ Không đọc được việc tiếp theo ({escape(type(e).__name__)})</div>'
    if not res:
        return ""
    text, level = res
    icon = {"wait": "", "todo": "👉 Việc tiếp theo: ", "done": "✅ "}[level]
    return f'<div class="nextband {level}">{escape(icon + text)}</div>'
