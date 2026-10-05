"""UI v2 (S13, lane E): the Kịch bản screen re-composed — same panels, same widget keys, fewer scrolls.

Order (S14.28): hero (title · pills · the ONE primary action of the moment · "Việc tiếp theo") → ① Kịch bản (ways in on one line, the
script box, the scene analysis) → 🖼 Tham chiếu (after the analysis, folded; one hint line before a script) → ② Chuẩn bị · Director · Nhân vật → ③ Chạy (tự động hoàn toàn + ngân sách). Rarely used things sit in a labelled "🔧 Tinh chỉnh" fold at
the bottom of their card. Only used when `ui.v2_on()`; the old composition stays in step1.step1()."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.design import components as D

LONG_CAPTION = 110          # characters; a caption longer than this is a P3 explanation (docs/QUY_TAC_BO_CUC_UI_V2.md §5)


def _short(text: str, limit: int = 88) -> str:
    """First sentence / clause of a caption, without markdown marks, cut at `limit` (shared: components.short_text)."""
    return D.short_text(text, limit)


def _uniq(base: str, scope: str = "") -> str:
    """Unique tooltip/popover key per call within one run (the same caption can be drawn twice, e.g. once per character).
    `scope` = a fragment that reruns by itself (autopilot_progress, every 5 s): it keeps its OWN counters and `reset_scope()` clears them at the start of each of its
    runs, so its keys stay the same from one refresh to the next — a changed key remounts the element and would close an open popover / tooltip (02/10)."""
    seen = st.session_state.setdefault("_script_cap_seen" + (f"_{scope}" if scope else ""), {})
    n = seen.get(base, 0)
    seen[base] = n + 1
    return f"{base}-{scope + '-' if scope else ''}{n}"


def reset_scope(scope: str) -> None:
    """Call at the top of a self-refreshing fragment that draws cap()/say() with `scope=` (see `_uniq`)."""
    st.session_state["_script_cap_seen_" + scope] = {}


def _auto_key(text: str, key: str = "") -> str:
    import zlib
    return key or f"script-cap-{zlib.crc32(text.encode('utf-8')) & 0xFFFFFF:x}"


def cap(text: str, key: str = "", summary: str = "", scope: str = "") -> None:
    """st.caption that, under UI v2, turns a LONG explanation into one summary line + a ⓘ holding the full text (nothing is lost).
    `summary` overrides the automatic first-clause summary (use it when a figure must stay visible). Short captions, and everything
    while the flag is off, are plain st.caption exactly as before."""
    if not ui.v2_on() or (len(text) <= LONG_CAPTION and not summary):
        st.caption(text)
        return
    D.line(f'<span class="script-sum">{escape(summary or _short(text))}</span>', text, _uniq(_auto_key(text, key), scope))


def say(kind: str, text: str, key: str = "", summary: str = "", scope: str = "") -> None:
    """st.info / st.warning / st.success that, under UI v2, becomes a pill + ONE summary line + a ⓘ with the whole message
    (P2 outside, P3 inside — docs/QUY_TAC_BO_CUC_UI_V2.md §5). Flag off: the plain Streamlit box, exactly as before.
    Blocking errors are NOT routed here (they stay st.error / red lines: P1)."""
    if not ui.v2_on():
        {"info": st.info, "warning": st.warning, "success": st.success}[kind](text)
        return
    D.note(kind, text, summary or _short(text), _uniq(_auto_key(text, key), scope))


def next_panel(p: Pipeline, pid: int, scenes, chars, locked: bool) -> str:
    """Which collapsed panel of card ② is the next thing to do (the only one drawn open): format → director → bible → none."""
    if not scenes:
        return ""
    proj = p.project(pid)
    if formats.project_aspect(proj) is None or not proj["genre"]:
        return "format"
    if not chars:
        return "director"
    if not locked or any(not c["anchor_approved"] for c in chars):
        return "bible"
    return ""


def is_next(name: str, legacy: bool) -> bool:
    """`expanded=` / `default_open=` of a panel: the old rule while the flag is off; under v2 only the panel that is the next job."""
    if not ui.v2_on():
        return legacy
    return st.session_state.get("_script_next") == name


def sync_folds(pid: int, nxt: str) -> None:
    """When the next job changes, the ui.fold panels follow it (one open at a time) instead of staying as they were left."""
    if st.session_state.get("_script_next_seen") == (pid, nxt):
        return
    st.session_state["_script_next_seen"] = (pid, nxt)
    for name in ("director", "bible"):
        st.session_state[f"fold_{name}_{pid}"] = name == nxt


_AUTO_BUSY =("queued", "running", "waiting", "needs_attention", "stopped", "error")


def _budget_state(p: Pipeline, pid: int):
    """(enabled, locked, total, spent) of the project budget; (False, …) when the feature is off or unreadable."""
    from core import project_budget
    if not project_budget.enabled():
        return False, False, 0.0, 0.0
    data = project_budget.get(p.conn, pid) or {}
    try:
        spent = sum(project_budget.spent_by_stage(p.conn, pid).values())
    except Exception:  # noqa: BLE001 - a pill only
        spent = 0.0
    return True, bool(data.get("locked")), float(data.get("total") or 0.0), float(spent)


def next_kind(p: Pipeline, pid: int, scenes, chars, locked: bool, budget_locked: bool, budget_on: bool) -> str:
    """The one primary action of the moment: analyse | plan | auto | budget | lock | next (same order as next_step.py)."""
    if not scenes:
        return "analyse"
    if autopilot.status(p, pid)["state"] in _AUTO_BUSY:
        return "auto"
    if not chars:
        return "plan"
    if budget_on and not budget_locked and allowed("autopilot"):
        return "budget"
    return "next" if locked else "lock"


def _hero(p: Pipeline, pid: int, proj, scenes, chars, locked: bool, stale: int) -> None:
    from dashboard.steps.step1 import _count_label, _lock_and_go
    b_on, b_locked, b_total, b_spent = _budget_state(p, pid)
    kind = next_kind(p, pid, scenes, chars, locked, b_locked, b_on)
    pills = [(_count_label(p, pid, scenes) if scenes else "Chưa có cảnh", "ok" if scenes else "mute"),
             (f"{len(chars)} nhân vật" if chars else "Chưa có nhân vật", "info" if chars else "mute"),
             (("Bible đã khóa", "ok") if locked else ("Bible chưa khóa", "warn")) if chars else ("Chưa có Bible", "mute")]
    if b_on:
        pills.append(("Ngân sách đã khóa", "ok") if b_locked else ("Ngân sách chưa duyệt", "warn"))
    if stale:
        pills.append((f"{stale} mục cũ", "warn"))
    with D.hero(f"script-{pid}"):
        a, b = st.columns([3, 2], gap="large", vertical_alignment="center")
        with a:
            st.html(D.hero_html(proj["name"] or "Dự án", "Kịch bản & đạo diễn · tách cảnh → chuẩn bị → Director → nhân vật → thoại → khóa", pills))
            # the "Việc tiếp theo" band is drawn once by the shell header in v2 (integrator, lane B) — not repeated here
        with b, D.cta_box("script"):
            _primary_action(p, pid, kind, scenes, chars, b_total, b_spent, _lock_and_go)


def _primary_action(p: Pipeline, pid: int, kind: str, scenes, chars, b_total: float, b_spent: float, lock_and_go) -> None:
    if kind == "analyse":
        st.html(D.empty_state("Bắt đầu từ kịch bản", "Dán hoặc tải kịch bản ở thẻ ① rồi bấm ▶ Phân tích"))
    elif kind == "auto":
        info = autopilot.status(p, pid)
        st.html(D.pill("Chạy tự động: " + info["state"], "info", running=info["state"] == "running"))
        D.line(f'<span class="script-sum">{escape(_short(info["note"], 70))} · điều khiển ở thẻ ③</span>',
               info["note"] + "\n\nĐiều khiển chạy tự động ở thẻ ③ Chạy bên dưới.", f"script-auto-note-{pid}")
    elif kind == "plan":
        from dashboard.steps.step1_checklist import checklist_panel
        checklist_panel(p, pid, "hero")            # S14.23: flag asset_checklist off → draws nothing
        client = llm_client()
        label = "🤖 Lập kế hoạch"
        if client is not None:
            from core import director_two_pass
            try:                                                   # the estimate the Director panel shows too — never invented here
                est = director_two_pass.estimate(p, pid, client)
                usd = (est.get(est["active"]) or est["single"]).get("usd")
                if usd is not None:
                    label += f" (≈ {usd:.2f} USD, ước tính)"
            except Exception:  # noqa: BLE001 - the button stays, only the number is missing
                pass
        if st.button(label, type="primary", key=f"script-cta_{pid}", disabled=client is None, width="stretch",
                     help="Chạy Director: Character Bible + thông số, ý đồ, thoại từng cảnh" if client else claude_hint()):
            from dashboard.steps.step1_director import run_director_now
            run_director_now(p, pid, client)
        D.line('<span class="script-sum">Director chia shot + lập Character Bible</span>',
               "Director chia cảnh thành shot và lập Character Bible. Tùy chọn hai lượt ở thẻ ②.", f"script-plan-note-{pid}")
    elif kind == "budget":
        from core import project_budget
        try:
            prop = project_budget.propose(p, pid)
        except Exception as e:  # noqa: BLE001 - say it, never hide the area
            st.warning(f"Không tính được ngân sách ({type(e).__name__}: {e})")
            return
        try:                                                   # S14.16: the approval shows the TOTAL estimated cost (tính dư)
            st.markdown("💵 " + project_budget.cost_summary(p, pid)["text"])
        except Exception as e:  # noqa: BLE001 - the approval still works; the missing estimate is said
            st.caption(f"Chưa tính được phần đã chi + ước tính phần còn lại: {str(e)[:160] or type(e).__name__}. Cách xử lý: kiểm tra dự án đã tách cảnh và bảng giá (⚙ Cài đặt), rồi tải lại trang; vẫn lỗi thì gửi báo cáo ở ⚙ Chẩn đoán.")
        if confirm_all(f"script-cta-budget_{pid}", ["go"], f"✔ Duyệt & khóa ngân sách ≈ {prop['total']:.2f} USD",
                       f"Khóa ngân sách dự án ≈ {prop['total']:.2f} USD (trần từng khâu như bảng ở thẻ ③)? Sau khi khóa, mọi lời gọi trả tiền "
                       "vượt mức khâu hoặc tổng sẽ được CẢNH BÁO (vẫn gửi); chỉ người được nâng mức, kèm lý do.", st, "Có, khóa"):
            project_budget.approve(p, pid, p.actor, prop)
            st.rerun()
        D.line('<span class="script-sum">Chạy tự động chờ bước này trước khi gen ảnh</span>',
               "Chạy tự động chờ bước này trước khi gen ảnh. Chi tiết từng khâu ở thẻ ③.", f"script-budget-note-{pid}")
    elif kind == "lock":
        st.button("✔ Duyệt & khóa → Storyboard", type="primary", key=f"script-cta-lock_{pid}", width="stretch",
                  on_click=lock_and_go, args=(p, pid))
        if st.session_state.get("lock_error"):
            st.error(st.session_state.pop("lock_error"))
        missing = [c["name"] for c in chars if not c["anchor_approved"]]
        if missing:
            D.line(f'<span class="script-sum">Chưa duyệt ảnh mốc: {len(missing)} nhân vật (thẻ ②)</span>',
                   "Chưa duyệt ảnh mốc: " + ", ".join(missing) + " (thẻ ②).", f"script-missing-anchor-{pid}")
    else:
        def go():
            st.session_state["step"] = STEPS[2]
        st.button("Sang Storyboard →", type="primary", key=f"script-cta-next_{pid}", width="stretch", on_click=go)
    if b_total and kind != "analyse":
        st.html(D.meter(b_spent / b_total, f"Ngân sách: đã chi {b_spent:.2f} / {b_total:.2f} USD", invert=True))


def _card_head(num: str, title: str, pills=()) -> None:
    chips = " ".join(D.pill(t, k) for t, k in pills)
    st.html(f'<div class="script-h"><span class="script-n">{num}</span><span>{escape(title)}</span>{chips}</div>')


def _tune(pid: int, name: str, summary: str):
    """The labelled "🔧 Tinh chỉnh" fold at the bottom of a card (a fold, not an expander: the panels inside have expanders of their own)."""
    return ui.fold("🔧 Tinh chỉnh", summary, f"tune_{name}_{pid}", default_open=False, sub="việc hiếm dùng — vẫn ở đây, không ẩn")


def step1_v2(p: Pipeline, pid: int, proj, scenes, chars, risky, char_names, locked: bool, stale: int) -> None:
    from dashboard.steps import step1 as S
    from dashboard.steps.step1_refs import inputs_and_refs_v2, modes_line
    st.session_state["_script_cap_seen"] = {}                           # one count of equal captions per run (unique ⓘ keys)
    nxt = next_panel(p, pid, scenes, chars, locked)                     # the one panel of card ② drawn open (everything else: one line)
    st.session_state["_script_next"] = nxt
    sync_folds(pid, nxt)
    _hero(p, pid, proj, scenes, chars, locked, stale)
    inherited = st.session_state.pop("inherited_note", None)            # S3.8: said once, right after the project was made
    if inherited:
        say("info", "↪ " + inherited + " — đổi ở màn Kịch bản · Định dạng nếu dự án này khác.", f"script-inherited-{pid}",
             "Dự án này kế thừa thiết lập từ dự án trước")

    # ① Kịch bản (1a) — S14.28: first card in the script mode (S11 video-ref / dance modes: their VIDEO ref box goes before it)
    with D.card(f"script-a-{pid}"):
        _card_head("1", "Kịch bản", [(S._script_summary(p, pid, scenes).replace("📜 ", ""), "ok" if scenes else "mute")])
        modes_line(pid)
        if st.session_state.get("parse_warn") and scenes:
            say("warning", st.session_state["parse_warn"], f"script-parse-warn-{pid}", "Không thấy tiêu đề cảnh — cả kịch bản thành 1 cảnh")
        if not scenes:
            st.html(D.empty_state("Chưa có kịch bản", "Tải file, dán văn bản hoặc gõ ý thô, rồi bấm ▶ Phân tích để tách cảnh."))
            S.script_input(p, pid, with_reset=False)
        else:
            from core import idea_to_script
            label = ("📥 Nhập / thay kịch bản (khung hội thoại: dán · ý tưởng · 📎 file)" if idea_to_script.enabled()   # S14.21: the box
                     else "📥 Nhập / thay kịch bản (tải file · dán văn bản · ý tưởng thô)")   # (no expander inside it — C2)
            with st.expander(label, expanded=bool(st.session_state.get("parse_warn"))):
                S.script_input(p, pid, with_reset=False)
            if st.session_state.get("parse_info"):
                S.parse_info_box()
            S.script_views(p, pid, proj, scenes, char_names)
            with _tune(pid, "script", "làm lại việc tách cảnh") as tune_open:
                if tune_open:
                    cap("↺ Làm lại: xóa các cảnh chưa có ảnh/video và nhân vật chưa khóa để tách lại kịch bản.")
                    S.reset_script_button(p, pid)

    # 🖼 Tham chiếu — S14.28: after the scene analysis, folded; per recognised character / place (Kho still matches by name)
    inputs_and_refs_v2(p, pid, bool(scenes))

    # ② Chuẩn bị · Director · Nhân vật (1b–1f)
    with D.card(f"script-b-{pid}"):
        _card_head("2", "Chuẩn bị · Director · Nhân vật",
                   [("Director đã chạy", "ok") if chars else ("Director chưa chạy", "mute")] if scenes else [])
        S.project_format_panel(p, pid)
        if scenes:
            S.assets_panel(p, pid)
            S.director_panel(p, pid, chars)
        if chars:
            S.character_bible_panel(p, pid, chars, risky)
            S.dialogue_review_panel(p, pid)
            with st.container(border=True):
                a, b = st.columns([2, 1], vertical_alignment="center")
                missing_anchor = [c["name"] for c in chars if not c["anchor_approved"]]
                with a:                                                 # P2 one line, P3 in ⓘ; the ONE primary button is in the hero
                    D.line('<span class="script-sum">' + (f"Chưa duyệt ảnh mốc: {len(missing_anchor)} nhân vật" if missing_anchor
                                                          else "Xong nhân vật → duyệt & khóa rồi sang màn Storyboard") + "</span>",
                           "Xong nhân vật (và storyboard nếu dựng): duyệt & khóa rồi sang màn Storyboard."
                           + (f" Chưa duyệt ảnh mốc: {', '.join(missing_anchor)}." if missing_anchor else ""), f"script-lock-row-{pid}")
                b.button("✔ Duyệt & khóa → Storyboard", key=f"lock_go_{pid}", on_click=S._lock_and_go, args=(p, pid))
                if st.session_state.get("lock_error"):
                    st.error(st.session_state.pop("lock_error"))
        if C.expert():
            with _tune(pid, "prep", "phong cách World Bible · dựng layout storyboard (chế độ Chuyên gia)") as tune_open:
                if tune_open:
                    S.world_bible_panel(p, pid)
                    if chars:
                        S.storyboard_panel(p, pid)

    # ③ Chạy (1c): the automatic run + the project budget. The level (who approves) is the 🎚 bar in the header.
    if scenes:
        with D.card(f"script-c-{pid}"):
            _card_head("3", "Chạy", [("tự động hoàn toàn hoặc lần lượt từng bước", "mute")])
            cap("🎚 Mức tự động (ai duyệt, cổng dừng, độ chặt QC) chọn ở thanh trên cùng. Chạy tự động bên dưới; "
                       "muốn đi từng bước thì làm xong thẻ ② rồi bấm Duyệt & khóa → Storyboard.")
            S.autopilot_panel(p, pid)
