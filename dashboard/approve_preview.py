"""M8.0b E2 (cờ `safe_paid_buttons`; sổ ep-2210-e2-approve-all-preview): nút "Duyệt tất cả" (duyệt hết) ảnh / motion prompt / clip.

Cờ BẬT: bấm → XEM TRƯỚC từng mục sẽ được duyệt + giá (duyệt = 0 USD; bước kế tốn bao nhiêu) + mục HOLD (chưa đủ điều kiện, không duyệt) →
"Có" → hẹn UNDO_SEC giây có "↩ Hoàn tác" (paid_confirm.schedule, như "✔ Duyệt storyboard") → tới hạn so lại danh sách + HOLD, đổi thì
KHÔNG duyệt. Cờ TẮT: nơi gọi giữ confirm_all cũ (không qua đây).
HOLD: motion prompt cũ / cảnh chưa có ảnh duyệt; clip làm từ đầu vào cũ (lineage.scan); ảnh làm từ đầu vào cảnh đã đổi sau khi gen.
Luồng tự động (autopilot, cổng) không đi qua đây."""
from typing import Dict, List, Optional

import streamlit as st

KINDS: Dict[str, Dict] = {
    "images": {"noun": "ảnh", "event": "duyet_het_anh", "page": "storyboard"},
    "motion": {"noun": "motion prompt", "event": "duyet_het_motion", "page": "motion"},
    "clips": {"noun": "clip", "event": "duyet_het_clip", "page": "video"},
}
SHOW_MAX = 40                                            # dòng xem trước tối đa (còn lại ghi "… và N mục")
LINEAGE_UNKNOWN = "không xác minh được lineage"


def pending_ids(conn, pid: int, kind: str) -> List[int]:
    """Đúng tập nơi gọi đang hiện (cùng câu SQL với step2/step3/step4/storyboard_cards)."""
    if kind == "motion":
        return [r[0] for r in conn.execute(
            "SELECT s.id FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id WHERE s.project_id=?"
            " AND (m.state IS NULL OR m.state != 'approved') ORDER BY s.idx", (pid,))]
    jtype = "image_gen" if kind == "images" else "video_gen"
    return [r[0] for r in conn.execute(
        "SELECT id FROM jobs WHERE project_id=? AND type=? AND state='pending_review' ORDER BY id", (pid, jtype))]


def _scan(conn, pid: int) -> Dict:
    from core import lineage
    return lineage.scan(conn, pid)


def _scene_of(conn, kind: str, item_id: int) -> Optional[int]:
    if kind == "motion":
        return item_id
    row = conn.execute("SELECT scene_id FROM jobs WHERE id=?", (item_id,)).fetchone()
    return row[0] if row else None


def _image_hold(conn, pid: int, jid: int) -> Optional[str]:
    """Ảnh chờ duyệt làm từ đầu vào cảnh ĐÃ ĐỔI sau khi gen (dấu input_hash khác dấu hiện tại) → HOLD."""
    import json
    from core import lineage
    row = conn.execute("SELECT j.input_hash, s.data FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.id=?", (jid,)).fetchone()
    if row is None or not row[0]:
        return None
    d = json.loads(row[1] or "{}")
    cast_rows = conn.execute("SELECT * FROM characters WHERE project_id=?", (pid,)).fetchall()
    proj = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    aspect = lineage._aspect(conn, pid)
    now = (lineage._image_hash(d, cast_rows, aspect, proj),
           lineage._image_hash(d, cast_rows, aspect, proj, lineage.image_key(conn, pid, d)))
    return None if row[0] in now else "đầu vào cảnh đã đổi sau khi gen ảnh này (ảnh cũ)"


def rows(conn, pid: int, kind: str, ids) -> List[Dict]:
    """[{id, scene_id, idx, text, hold}] — `hold` = lý do chưa đủ điều kiện (None = duyệt được)."""
    try:
        scan = _scan(conn, pid)
    except Exception:  # noqa: BLE001 - scan lỗi không được mở khóa duyệt
        scan = None
    noun = KINDS[kind]["noun"]
    out = []
    for i in ids:
        try:
            sid = _scene_of(conn, kind, i)
        except Exception:  # noqa: BLE001 - không xác định được scene thì lineage chưa được xác minh
            sid = None
        s = scan.get(sid) if isinstance(scan, dict) and sid is not None else None
        if not isinstance(s, dict):
            s = None
        hold = None
        if kind == "motion":
            if s is None or not {"image_job_id", "motion_stale"}.issubset(s):
                hold = LINEAGE_UNKNOWN
            elif not s.get("image_job_id"):
                hold = "cảnh chưa có ảnh duyệt"
            elif s.get("motion_stale"):
                hold = f"motion prompt cũ: {s['motion_stale']}"
        elif kind == "clips":
            # lineage.scan chỉ lưu một video được chọn mỗi cảnh. Lý do cũ thuộc đúng job đó;
            # job chờ khác chưa có lineage được xác minh trong lượt scan này.
            if s is None or not {"video_job_id", "video_stale"}.issubset(s):
                hold = LINEAGE_UNKNOWN
            elif s.get("video_job_id") != i:
                hold = LINEAGE_UNKNOWN
            elif s.get("video_stale"):
                hold = f"clip làm từ đầu vào cũ: {s['video_stale']}"
        else:
            try:
                hold = _image_hold(conn, pid, i)
            except Exception:  # noqa: BLE001 - lỗi đọc dấu ảnh phải giữ HOLD
                hold = f"{LINEAGE_UNKNOWN}: lỗi đọc đầu vào ảnh"
        idx = s.get("idx") if s else None
        what = f"{noun} job {i}" if kind != "motion" else noun
        out.append({"id": i, "scene_id": sid, "idx": idx, "text": (f"S{idx:02d} · " if isinstance(idx, int) else "") + what, "hold": hold})
    return out


def price_line(conn, kind: str, items: List[Dict]) -> str:
    """Giá của lần duyệt: duyệt không gọi API (0 USD); ảnh / motion → bước kế là gen video các cảnh được duyệt ≈ X USD (khi gửi)."""
    if kind == "clips":
        return "Duyệt clip: 0 USD (không gửi gì, không gọi API)."
    from core import cost
    scenes = sorted({r["scene_id"] for r in items if not r["hold"] and r["scene_id"] is not None})
    try:
        prices = [cost.clip_estimate(conn, s) for s in scenes]
        nxt = None if any(x is None for x in prices) else sum(prices)
    except Exception:  # noqa: BLE001 - giá bước kế không tính được thì nói, không ẩn nút
        nxt = None
    after = (f"≈ {nxt:.2f} USD (ước tính, chỉ khi bạn gửi video)" if nxt is not None else "chưa có giá") if scenes else "0 USD"
    return f"Duyệt: 0 USD (không gọi API). Bước kế — gen video {len(scenes)} cảnh này: {after}."


def snapshot(conn, pid: int, kind: str, ids) -> Dict:
    items = rows(conn, pid, kind, ids)
    return {"ids": list(ids), "ok": [r["id"] for r in items if not r["hold"]], "items": items}


def _approve_one(p, kind: str, item_id: int) -> None:
    if kind == "images":
        p.approve(item_id, "user", note="gate_bulk")
    elif kind == "motion":
        from core import llm_io
        llm_io.approve_motion_prompt(p, item_id)
    else:
        from dashboard import quality_ui
        quality_ui.approve_clip(p, item_id, note="gate_bulk")


def run(p, it: Dict) -> str:
    """Tới hạn hoàn tác: so lại tập đang chờ + HOLD với lúc bấm; giống → duyệt các mục đủ điều kiện, trả "". Khác → không duyệt gì."""
    kind, pid = it["kind"], it["pid"]
    noun = KINDS[kind]["noun"]
    now = pending_ids(p.conn, pid, kind)
    if sorted(now) != sorted(it.get("ids") or []):
        return f"Không duyệt: danh sách {noun} chờ duyệt đã đổi trong lúc chờ hoàn tác — xem lại rồi bấm lại."
    ok_now = [r["id"] for r in rows(p.conn, pid, kind, now) if not r["hold"]]
    if sorted(ok_now) != sorted(it.get("ok") or []):
        return f"Không duyệt: mục đủ điều kiện (HOLD) đã đổi trong lúc chờ hoàn tác — xem lại rồi bấm lại."
    for i in it.get("ok") or []:
        _approve_one(p, kind, i)
    return ""


def approve_all_box(p, pid: int, kind: str, key: str, ids, label: str, container=None, *, primary: bool = False,
                    stretch: bool = False) -> None:
    """Cờ BẬT (nơi gọi đã kiểm paid_confirm.enabled()). Cùng khóa nút cũ `key`, `key_yes`, `key_no` (tools/ui_v2_acceptance)."""
    from dashboard import paid_confirm as P
    box = container if container is not None else st
    ss = st.session_state
    action = f"approve_{kind}"
    if P.waiting(ss, action, pid):
        box.caption("⏳ Đã hẹn duyệt — xem thanh ↩ Hoàn tác trên cùng.")
        return
    ids = tuple(ids)
    P.mark_drawn(ss, key)
    ask = f"{P.ASK_PREFIX}{key}"
    if ss.get(ask) not in (None, ids):
        ss.pop(ask, None)                                 # tập đổi từ lúc hỏi → hỏi lại
    extra = {"width": "stretch"} if stretch else {}
    if ss.get(ask) != ids:
        if box.button(label, key=key, disabled=not ids, type="primary" if primary else "secondary", **extra):
            ss[ask] = ids
            st.rerun()
        return
    snap = snapshot(p.conn, pid, kind, ids)
    noun = KINDS[kind]["noun"]
    ok, held = snap["ok"], [r for r in snap["items"] if r["hold"]]
    price = price_line(p.conn, kind, snap["items"])
    lines = [f"- {'⏸ HOLD — ' + r['hold'] + ' · ' if r['hold'] else '✔ '}{r['text']}" for r in snap["items"][:SHOW_MAX]]
    if len(snap["items"]) > SHOW_MAX:
        lines.append(f"- … và {len(snap['items']) - SHOW_MAX} mục nữa")
    box.warning(f"**Xem trước: duyệt {len(ok)}/{len(ids)} {noun}**" + (f" · {len(held)} HOLD (chưa đủ điều kiện, không duyệt)" if held else "")
                + f"\n\n{price}\n\nSau khi bấm Có: máy chờ {P.UNDO_SEC} s (↩ Hoàn tác được) rồi mới duyệt.")
    box.markdown("\n".join(lines))
    row = box.container(horizontal=True)
    if ok and row.button(f"Có, duyệt {len(ok)} {noun}", key=f"{key}_yes", type="primary"):
        ss.pop(ask, None)
        from dashboard import common as C
        P.schedule(ss, action, pid, f"Duyệt {len(ok)} {noun}", "", actor=p.actor, user=C.access_user(), ids=list(ids), ok=list(ok),
                   kind=kind, event=KINDS[kind]["event"], page=KINDS[kind]["page"], verb="duyệt", done="Đã duyệt",
                   log=f"duyệt hết {len(ok)} {noun} (HOLD {len(held)})")
        C.log_ui(p, "hen_duyet", page=KINDS[kind]["page"], project_id=pid,
                 detail=f"duyệt hết {len(ok)} {noun}, HOLD {len(held)} — chờ {P.UNDO_SEC} s hoàn tác")
        st.rerun()
    if not ok:
        box.caption("Không có mục nào đủ điều kiện duyệt — sửa các mục HOLD trước.")
    if row.button("Không", key=f"{key}_no"):
        ss.pop(ask, None)
        st.rerun()
