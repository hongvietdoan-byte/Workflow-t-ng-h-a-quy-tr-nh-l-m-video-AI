"""N4 (08/10, docs/THIET_KE_2_BAC_CHAT_LUONG_VA_NHAC_2026-10-08.md mục 1 UI + 5a.5, 5a.8): giao diện video 2 bậc chất lượng.

Lõi là `core/quality_tier.py` (nhánh N1). Hợp đồng dùng ở đây:
- `quality_tier.state(conn, scene_id)` ∈ STATES;
- `quality_tier.final_estimate(conn, pid)` → {"usd", "scenes": [{scene_id, usd…}]} (ids cũng nhận) — UI chỉ tính cảnh draft_ok;
- `quality_tier.request_final(p, scene_id, actor)` CHỈ tạo job bản cao (không gửi) → UI gọi `runner.submit_pending` một lần;
- `quality_tier.set_path` ghi `motion_prompts.quality_path` (NULL = auto / draft_first / direct — người ghi đè).
Không có module hoặc cờ `two_tier_quality` tắt / chưa có → `enabled()` False và mọi màn y như cũ."""
from typing import Dict, List, Optional, Tuple

FLAG = "two_tier_quality"
STATES = ("none", "draft_running", "draft_review", "draft_ok", "draft_stale", "final_running", "final_ok", "direct_ok")
# huy hiệu trên thẻ cảnh: (chữ, loại pill)
STATE_PILL = {"none": ("Chưa gen", "mute"), "draft_running": ("Nháp · đang gen", "info"), "draft_review": ("Nháp · chờ duyệt", "warn"),
              "draft_ok": ("Nháp đã duyệt", "info"), "draft_stale": ("Nháp đã cũ", "warn"), "final_running": ("Bản cao · đang gen", "info"),
              "final_ok": ("Bản cao ✓", "ok"), "direct_ok": ("Cao luôn ✓", "ok")}
# clip đang dùng trong bản dựng còn là nháp (bản cao chưa xong)
DRAFT_IN_CUT = ("draft_review", "draft_ok", "draft_stale", "final_running")
DRAFT_ANY = ("draft_running",) + DRAFT_IN_CUT
FINAL_DONE = ("final_ok", "direct_ok")
# phần đã làm của một cảnh trong chặng clip: nháp → duyệt nháp → bản cao (hoặc gen thẳng)
WEIGHT = {"none": 0.0, "draft_running": 0.15, "draft_review": 0.3, "draft_stale": 0.3, "draft_ok": 0.5, "final_running": 0.7,
          "final_ok": 1.0, "direct_ok": 1.0}
PATHS = {"auto": "Tự động", "draft_first": "Nháp trước", "direct": "Cao luôn"}
DIFFICULTY = {"easy": "Dễ", "complex": "Phức tạp", "unknown": "Chưa rõ"}


def module():
    """core.quality_tier, or None while N1 is not there (looked up each call: the module may arrive without a restart)."""
    try:
        from core import quality_tier
    except ImportError:
        return None
    return quality_tier


def enabled() -> bool:
    from core import features
    if FLAG not in features.FEATURES:                # N1 adds the flag; not there yet = off
        return False
    try:
        return features.on(FLAG) and module() is not None
    except Exception:  # noqa: BLE001 - a broken flag read never breaks a screen
        return False


def state(conn, scene_id: int) -> str:
    qt = module()
    try:
        s = qt.state(conn, scene_id) if qt else "none"
    except Exception:  # noqa: BLE001 - one unreadable scene must not hide the others
        s = "none"
    return s if s in STATES else "none"


def states(conn, pid: int) -> Dict[int, str]:
    return {r["id"]: state(conn, r["id"]) for r in conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx", (pid,))}


def draft_scenes(conn, pid: int) -> List[Tuple[int, int]]:
    """(scene_id, idx) of the scenes whose clip in the cut is still a draft."""
    rows = conn.execute("SELECT id, idx FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
    return [(r["id"], r["idx"]) for r in rows if state(conn, r["id"]) in DRAFT_IN_CUT]


def clip_progress(conn, pid: int) -> Tuple[float, Dict[str, int]]:
    """(0..1 of the clip stage counted per tier, count per state). 1.0 only when every scene has its high-tier / direct clip."""
    st_ = states(conn, pid)
    counts = {k: 0 for k in STATES}
    for s in st_.values():
        counts[s] += 1
    frac = sum(WEIGHT[s] for s in st_.values()) / len(st_) if st_ else 0.0
    return frac, counts


def progress_lines(counts: Dict[str, int]) -> str:
    """One line of the clip stage: how many scenes at each step (only the non-zero ones)."""
    parts = [("nháp đang gen", counts.get("draft_running", 0)), ("nháp chờ duyệt", counts.get("draft_review", 0)),
             ("nháp đã duyệt", counts.get("draft_ok", 0)), ("nháp đã cũ", counts.get("draft_stale", 0)),
             ("bản cao đang gen", counts.get("final_running", 0)),
             ("bản cao / cao luôn xong", counts.get("final_ok", 0) + counts.get("direct_ok", 0)), ("chưa gen", counts.get("none", 0))]
    return " · ".join(f"{n} {t}" for t, n in parts if n)


def final_estimate(conn, pid: int) -> Dict:
    qt = module()
    try:
        est = qt.final_estimate(conn, pid) if qt else None
    except Exception:  # noqa: BLE001 - no estimate = 'chưa có giá', never a crash
        est = None
    est = dict(est or {})
    rows = [r if isinstance(r, dict) else {"scene_id": r} for r in (est.get("scenes") or [])]   # N1 gives rows, the contract ids
    by = dict(est.get("by_scene") or {})
    for r in rows:
        if r.get("usd") is not None:
            by.setdefault(r["scene_id"], r["usd"])
    ready = [r["scene_id"] for r in rows if state(conn, r["scene_id"]) == "draft_ok"]   # never a stale / unapproved draft
    est["by_scene"] = by
    est["scenes"] = ready
    if ready and all(sid in by for sid in ready):
        est["usd"] = round(sum(by[sid] for sid in ready), 2)                     # the price of what the button sends, not of all
    else:
        est["usd"] = None if ready else est.get("usd")
    return est


def scene_final_price(conn, pid: int, scene_id: int) -> Optional[float]:
    est = final_estimate(conn, pid)
    by = est.get("by_scene") or {}
    if scene_id in by:
        return by[scene_id]
    from core import cost
    try:
        return cost.clip_estimate(conn, scene_id)
    except Exception:  # noqa: BLE001
        return None


def quality_path(conn, scene_id: int) -> str:
    try:
        row = conn.execute("SELECT quality_path FROM motion_prompts WHERE scene_id=?", (scene_id,)).fetchone()
    except Exception:  # noqa: BLE001 - column not there before N1
        return "auto"
    return (row["quality_path"] if row and row["quality_path"] in PATHS else "auto")   # NULL (N1) = auto


def set_quality_path(conn, scene_id: int, value: str) -> bool:
    if value not in PATHS:
        raise ValueError(f"quality_path lạ: {value}")
    qt = module()
    if qt is not None and hasattr(qt, "set_path"):   # N1 owns the column (auto = NULL)
        if conn.execute("SELECT 1 FROM motion_prompts WHERE scene_id=?", (scene_id,)).fetchone() is None:
            return False
        qt.set_path(conn, scene_id, value)
        return True
    try:
        cur = conn.execute("UPDATE motion_prompts SET quality_path=? WHERE scene_id=?", (value, scene_id))
        conn.commit()
    except Exception:  # noqa: BLE001 - column not there before N1
        return False
    return cur.rowcount > 0


def difficulty_md(conn, scene_id: int) -> Tuple[str, str]:
    """(one line, details) of the Director's difficulty label + the cross-check; ('', '') when the shot has none."""
    import json
    row = conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    try:
        data = json.loads(row["data"] or "{}") if row else {}
    except ValueError:
        data = {}
    label = data.get("difficulty")
    if not label:
        return "", ""
    name = DIFFICULTY.get(label, str(label))
    why = data.get("difficulty_why") or ""
    line = f"Độ khó (Đạo diễn): **{name}**" + (f" — {why}" if why else "")
    check = data.get("difficulty_check") or {}
    detail = []
    if check.get("note"):
        detail.append(f"Kiểm chéo: {check['note']}")
    if check.get("factors"):
        detail.append(f"Dữ liệu shot (điểm {check.get('score', '?')}): " + " · ".join(str(f) for f in check["factors"]))
    return line, "\n\n".join(detail)


def stale_reason(conn, scene_id: int) -> str:
    """Why a draft is outdated (KLD-1 lineage reason when there is one)."""
    try:
        from core import lineage
        r = lineage.scan(conn, conn.execute("SELECT project_id FROM scenes WHERE id=?", (scene_id,)).fetchone()["project_id"]).get(scene_id) or {}
        return r.get("video_stale") or r.get("motion_stale") or r.get("image_stale") or "đầu vào đã đổi sau khi duyệt nháp"
    except Exception:  # noqa: BLE001
        return "đầu vào đã đổi sau khi duyệt nháp"


# ---- Streamlit parts -----------------------------------------------------------------------------------------------------------
def card_block(p, pid: int, scene_id: int, runner) -> None:
    """On the scene's clip card: tier badge · Director's difficulty · path choice · ⬆ Gen bản cao (draft_ok) / why not (draft_stale)."""
    import streamlit as st
    from core import cost
    from dashboard.common import act
    from dashboard.design import components as D
    s = state(p.conn, scene_id)
    text, kind = STATE_PILL[s]
    st.markdown(D.pill(text, kind), unsafe_allow_html=True)
    line, detail = difficulty_md(p.conn, scene_id)
    if line:
        st.markdown(line)
        if detail:
            st.caption(detail)
    cur = quality_path(p.conn, scene_id)
    keys = list(PATHS)
    pick = st.selectbox("Đường chất lượng", keys, index=keys.index(cur), format_func=PATHS.get, key=f"qpath_{scene_id}",
                        help="Tự động = theo nhãn độ khó của Đạo diễn (dễ → cao luôn; phức tạp / chưa rõ → nháp trước). Chọn tay thắng tự động.")
    if pick != cur and set_quality_path(p.conn, scene_id, pick):
        st.toast(f"Đã đặt đường: {PATHS[pick]}")
    if s == "draft_stale":
        st.warning("⚠ Nháp đã cũ: " + stale_reason(p.conn, scene_id) + " — không gen bản cao từ nháp này; gen lại nháp từ đầu vào mới.")
    if s == "draft_ok":
        price = scene_final_price(p.conn, pid, scene_id)
        if st.button("⬆ Gen bản cao" + cost.price_tag(price), key=f"qfinal_{scene_id}", width="stretch",
                     help="Nâng cảnh từ bản nháp đã duyệt lên bản chất lượng cao (người bấm — không tính vào trần tự gen lại)."):
            qt = module()
            if act(lambda: qt.request_final(p, scene_id, "user")):
                if runner is not None:
                    act(lambda: runner.submit_pending(pid))
                st.rerun()


def batch_block(p, pid: int, runner) -> None:
    """The batch bar: '⬆ Gen bản cao N cảnh — ≈ X USD (tham khảo)' with a yes/no box; a one-line state of the tiers."""
    import streamlit as st
    from dashboard.common import act, confirm_all
    _, counts = clip_progress(p.conn, pid)
    summary = progress_lines(counts)
    if summary:
        st.caption("Chất lượng 2 bậc: " + summary)
    est = final_estimate(p.conn, pid)
    scenes = est["scenes"]
    if not scenes:
        return
    usd = est["usd"]
    price = f"≈ {usd:.2f} USD (tham khảo)" if usd is not None else "chưa có giá"
    if confirm_all(f"qfinal_all_{pid}", scenes, f"⬆ Gen bản cao {len(scenes)} cảnh — {price}",
                   f"Gen bản cao cho {len(scenes)} cảnh có nháp đã duyệt — {price}?", yes_label="Có, gen bản cao"):
        qt = module()
        for sid in scenes:
            act(lambda sid=sid: qt.request_final(p, sid, "user"))
        if runner is not None:
            act(lambda: runner.submit_pending(pid))
        st.rerun()


def draft_render_note(conn, pid: int) -> str:
    """'DRAFT · N cảnh còn nháp (C1, C3)' when the cut still holds draft clips, else ''."""
    if not enabled():
        return ""
    drafts = draft_scenes(conn, pid)
    if not drafts:
        return ""
    return f"DRAFT · {len(drafts)} cảnh còn nháp (" + ", ".join(f"cảnh {i}" for _, i in drafts) + ")"


def draft_file_name(name: str, conn, pid: int) -> str:
    """The download name of a render made of draft clips gets '_DRAFT' before the extension."""
    if not draft_render_note(conn, pid):
        return name
    import os
    base, ext = os.path.splitext(name)
    return name if base.endswith("_DRAFT") else f"{base}_DRAFT{ext}"


def delivery_warning(conn, pid: int) -> str:
    """The warning shown after a delivery made with draft clips (warn, never block)."""
    note = draft_render_note(conn, pid)
    return ("⚠ Bản giao này là bản " + note + " — các cảnh đó chưa có bản chất lượng cao; gen bản cao ở màn Video rồi xuất lại."
            if note else "")
