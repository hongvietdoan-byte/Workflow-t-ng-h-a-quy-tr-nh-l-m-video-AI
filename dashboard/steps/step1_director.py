"""Step 1 · 1d/1f: Director, its reports, dialogue review, re-plan of a scene (split from step1.py, S9.5)."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.steps.step1_v2 import cap, say, is_next  # noqa: F401  (v2: long captions / notes become a one-line summary + ⓘ)


def _director_summary(p: Pipeline, pid: int, chars) -> str:
    if not chars:
        return "chưa chạy"
    n = p.conn.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (pid,)).fetchone()[0]
    paid = None if ui.v2_on() else _paid_line(p, pid)           # v2 (P3): the paid-seconds line lives in "📋 Báo cáo Director" and the panel body
    return f"✅ đã chạy · {n} shot · {len(chars)} nhân vật" + (f" · {paid}" if paid else "")


def run_director_now(p: Pipeline, pid: int, client, resume: bool = False) -> None:
    """Run the Director (spinner, toast, rerun). Shared by the 1d button and the hero button of the v2 screen."""
    with st.spinner("Claude đang phân tích kịch bản…"):
        ok = act(lambda: st.session_state.__setitem__("llm_res", llm_runner.run_director(p, pid, client, resume=resume)))
    if ok:
        r = st.session_state.pop("llm_res")
        st.toast(f"Đã lưu {r['characters']} nhân vật, {r['scenes']} cảnh ({tokens_text(r)})"
                 + (f" · {r['calls']} lượt Claude" if r.get("two_pass") else "")
                 + (f" · Đạo diễn duyệt: cảnh {', '.join(map(str, r['flagged']))} cần xem" if r.get("flagged") else ""))
        st.rerun()


def director_panel(p: Pipeline, pid: int, chars) -> None:
    locked = any(c["locked"] for c in chars)
    kept = llm_io.locked_fields(p.conn, pid)
    with ui.fold("1d · 🎬 Director", _director_summary(p, pid, chars), f"director_{pid}", default_open=is_next("director", not chars),
                 sub="Character Bible + thông số, ý đồ, thoại từng cảnh") as director_open:  # E1.12
        if director_open:
            if kept:
                cap(f"🔒 {sum(len(r['fields']) for r in kept)} trường bạn đã sửa tay ở {len(kept)} cảnh được giữ nguyên khi chạy lại.")
            from dashboard.steps.step1_checklist import checklist_panel
            checklist_panel(p, pid, "dir")          # S14.23: flag asset_checklist off → draws nothing
            client = llm_client()
            if client is not None:
                from core import director_two_pass
                two = director_two_pass.enabled(p.project(pid))
                label = f"🤖 Chạy Director{' hai lượt' if two else ''} bằng {llm_label(client)}"
                if two:
                    cap("🧪 Director hai lượt (cờ `director_two_pass`, chưa thử thật): Tầng A Đạo diễn viết Bible + ý đồ từng cảnh → "
                               "Tầng B Quay phim chia shot mỗi cảnh một lượt (phần chung cache) → code Đạo diễn duyệt bảng shot so với ý đồ.")
                usd, scene_usd = None, None            # S14.2 A2: the estimate goes on the buttons too
                try:                                   # luật chi phí: the estimate before the click (both ways, so the choice is informed)
                    est = director_two_pass.estimate(p, pid, client)
                    usd = (est.get(est["active"]) or est["single"]).get("usd")
                    two_est = est.get("two_pass") or {}
                    if two_est.get("usd") is not None and est.get("scenes"):
                        scene_usd = two_est["usd"] / est["scenes"]
                    cap("💵 " + director_two_pass.estimate_text(est),            # v2: the figure stays outside, the breakdown goes in ⓘ
                        summary=("💵 Ước tính Director ≈ " + f"{usd:.2f}".replace(".", ",") + " USD") if usd is not None else "💵 Ước tính Director: model chưa có giá")
                except Exception as e:  # noqa: BLE001 - an estimate that cannot be made is said, never hidden
                    cap(f"💵 Chưa ước tính được chi phí Director ({type(e).__name__}: {e})")
                label += f" · Claude ≈ {usd:.2f} USD (ước tính)" if usd is not None else " · Claude: chưa có giá"
                go = (confirm_all(f"llm_dir_{pid}", ["again"], label + " (chạy lại)",
                                  "Character Bible đã khóa: chạy lại chỉ cập nhật thông số cảnh (trường bạn đã sửa tay được giữ), nhân vật đã khóa "
                                  "không đổi. Chạy?", st, "Có, chạy lại") if locked
                      else st.button(label, type="primary", key=f"llm_dir_{pid}"))
                pending = director_two_pass.pending_scenes(p, pid) if two else []
                resume = bool(pending) and st.button(
                    f"↻ Chỉ hỏi lại {len(pending)} cảnh lỗi (cảnh {', '.join(map(str, pending))})"
                    + (f" · Claude ≈ {scene_usd * len(pending):.2f} USD (ước tính)" if scene_usd is not None
                       else cost.llm_button_tag(p.conn, "director", len(pending))), key=f"llm_dir_resume_{pid}",
                    help="Lần chạy trước dừng vì Quay phim chưa chia được các cảnh này. Dùng lại ý đồ Tầng A và các cảnh đã chia (đã trả tiền) "
                         "khi kịch bản/luật không đổi — chỉ trả tiền cho các cảnh lỗi.")
                if go or resume:
                    run_director_now(p, pid, client, resume)
            else:
                cap(claude_hint() + " Hoặc dùng cách nhập tay bên dưới.")
            if C.expert():
                with st.expander("✍ Nâng cao: prompt gửi Claude + dán JSON kết quả", expanded=client is None and not chars):
                    st.code(prompts.build_director_bundle(p, pid), language="markdown")
                    raw = st.text_area("Dán JSON kết quả từ Claude", key=f"analysis_{pid}", height=120)
                    if st.button("Lưu phân tích", disabled=not raw.strip(), key=f"dir_paste_{pid}"):
                        from core import director_two_pass

                        def _paste():
                            llm_io.store_scene_analysis(p, pid, raw)
                            director_two_pass.forget(p, pid)      # the pasted plan replaces any two-pass intent
                        if act(_paste, "Đã lưu Character Bible + thông số cảnh"):
                            st.rerun()


def dialogue_review_panel(p: Pipeline, pid: int) -> None:
    """Dialogue: length against the clip (real voice length when voiced) and Claude's review (narration-writer skill)."""
    entries = dialogue.check(p, pid, voice.scene_seconds(p.conn, pid, C.DATA))
    if not entries:
        return
    bad = dialogue.problems(entries)
    key = f"dlg_review_{pid}"
    with st.expander(f"1f · 🗣 Rà thoại — {len(entries)} cảnh có thoại" + (f", {len(bad)} cần chú ý" if bad else ", độ dài đều vừa"),
                     expanded=(key in st.session_state) if ui.v2_on() else (bool(bad) or key in st.session_state)):   # v2: the count is in the label
        def entry_md(e) -> str:
            icon = {"ok": "✔", "tight": "◐", "extend": "⚠", "split": "✖"}[e["status"]]
            color = {"ok": "green", "tight": "orange", "extend": "orange", "split": "red"}[e["status"]]
            tag = colored(color, f"{icon} S{e['idx']:02d}", html=False)
            return (f"{tag} {escape(', '.join(e['speakers']))} · "
                    + (f"giọng thật ≈ {e['needed']:g}s" if e["measured"] else f"{e['syllables']} âm tiết ≈ {e['needed']:g}s")
                    + f" / clip {e['planned']:g}s (model tối đa {e['max']}s)" + (f" — {escape(e['advice'])}" if e["advice"] else ""))
        shown = entries
        if ui.v2_on() and len(entries) > 3:          # v2 (P3, list > 3): only the lines that need attention outside, the whole list in ⓘ
            from dashboard.design import components as D
            shown = bad
            D.line(f'<span class="script-sum">{len(entries) - len(bad)}/{len(entries)} cảnh vừa độ dài thoại</span>',
                   "\n\n".join(entry_md(e) for e in entries), f"script-dlg-list-{pid}")
        for e in shown:
            st.markdown(entry_md(e))
        fixable = [e for e in bad if e["status"] == "extend"]
        if fixable and st.button(f"⏱ Tự tăng thời lượng {len(fixable)} clip cho vừa thoại", key=f"dlg_fix_s1_{pid}"):
            dialogue.extend(p, entries)
            st.rerun()
        client = llm_client()
        if st.button("🤖 Claude rà thoại (6 lỗi thoại + độ dài)" + cost.llm_button_tag(p.conn, "director", 1), key=f"dlg_ai_{pid}", disabled=client is None,
                     help=None if client else claude_hint()):
            with st.spinner("Claude đang đọc thoại…"):
                act(lambda: st.session_state.__setitem__(key, claude_tasks.review_dialogue(p, pid, client)))
        res = st.session_state.get(key)
        if res:
            if res.get("summary"):
                say("info", res["summary"], f"script-dlg-sum-{pid}")
            for n, ln in enumerate(res.get("lines") or []):
                with st.container(border=True):
                    st.markdown(f"**S{ln['idx']:02d} · câu {ln['line']}** {escape(ln.get('speaker') or '')} — {escape(ln.get('problem') or '')}")
                    new = st.text_input("Đề xuất", ln["suggestion"], key=f"dlg_sug_{pid}_{n}")
                    if st.button("Áp dụng câu này", key=f"dlg_apply_{pid}_{n}"):
                        if act(lambda: claude_tasks.apply_dialogue_fix(p, pid, ln["idx"], ln["line"], new), "Đã sửa thoại"):
                            res["lines"] = [x for x in res["lines"] if x is not ln]
                            st.rerun()
            for sp in res.get("split") or []:
                say("warning", f"S{sp.get('idx')}: nên tách cảnh — {sp.get('why', '')}", f"script-dlg-split-{pid}-{sp.get('idx')}")
            if not res.get("lines") and not res.get("split"):
                say("success", "Claude không thấy lỗi thoại cần sửa.", f"script-dlg-ok-{pid}")


def _replan_button(p: Pipeline, pid: int, scene_idx: int, col) -> None:
    """1.4: re-plan the shots of one script scene (one cached Claude call, a few cents) — only while that scene and the later ones have
    no picture or clip yet."""
    later = [r["id"] for r in p.conn.execute("SELECT id, data FROM scenes WHERE project_id=?", (pid,))
             if (json.loads(r["data"] or "{}").get("story_scene") or 0) >= scene_idx]
    if later and p.conn.execute("SELECT 1 FROM jobs WHERE scene_id IN (" + ",".join("?" * len(later)) + ") LIMIT 1", later).fetchone():
        return
    client = llm_client()
    if client is None:
        return
    if col.button("↻ Chia shot lại cảnh này" + cost.llm_button_tag(p.conn, "director", 1), key=f"replan_{pid}_{scene_idx}",
                  help="Một lượt Claude chỉ cho cảnh này (phần luật chung được cache) — vài cent thay vì ~$0,3 của cả kịch bản. "
                       "Cảnh sau được ghi lại theo thứ tự phim, không đổi nội dung. Director hai lượt: Quay phim chia lại theo ý đồ "
                       "Tầng A đã lưu (không hỏi lại Đạo diễn)."):
        with st.spinner(f"Claude đang chia shot lại cảnh {scene_idx}…"):
            ok = act(lambda: st.session_state.__setitem__("replan_res", llm_runner.run_director_scene(p, pid, scene_idx, client)))
        if ok:
            r = st.session_state.pop("replan_res")
            st.toast(f"Cảnh {scene_idx}: {r['rows']} shot ({tokens_text(r)})")
            st.rerun()


def _paid_line(p: Pipeline, pid: int):
    """H6: seconds of video that will be billed for this shot plan (Kling, the model's minimum clip), one line per way of making it —
    worked out by code from the stored Director answer, before any picture or clip is paid for."""
    from core import director_report
    proj = p.project(pid)
    try:
        raw = json.loads(proj["director_raw"] or "{}")
        if not raw.get("scenes") or raw.get("truncated"):
            return None
        from core import shots as _shots
        r = director_report.report(director_report.with_current_shots(raw, _shots.shots_of(p, pid)), proj["script_text"] or "")
    except Exception:  # noqa: BLE001 - an old or odd answer must not break Step 1
        return None
    s, u = r["paid_s"], r["paid_usd"]
    bits = [f"từng shot {s['per_shot']:g}s" + (f" ≈ ${u['per_shot']:g}" if u["per_shot"] else ""),
            f"gom theo cảnh (multi-shot) {s['per_scene']:g}s" + (f" ≈ ${u['per_scene']:g}" if u["per_scene"] else "")]
    if s["per_setup"] is not None:
        bits.append(f"theo vị trí máy ({s['setups']}) {s['per_setup']:g}s" + (f" ≈ ${u['per_setup']:g}" if u["per_setup"] else ""))
    return f"💵 Video phải trả tiền cho {r['total_s']:g}s phim (Kling, chưa tính gen lại): " + " · ".join(bits)


def _crew_notes(p: Pipeline, pid: int) -> None:
    """GĐ4 (knowledge/roles/): what the Director gave up (`tradeoffs`, and a sacrifice it did not write down), the acting checks
    (core/performance.py) and the Director's notes for the script writer — suggestions only, the lines are never changed."""
    from core import director_report
    proj = p.project(pid)
    try:
        raw = json.loads(proj["director_raw"] or "{}")
        if not raw.get("scenes") or raw.get("truncated"):
            return
        from core import shots as _shots
        r = director_report.report(director_report.with_current_shots(raw, _shots.shots_of(p, pid)), proj["script_text"] or "")
        # fields the code dropped when the answer was saved are gone from the rows — said from the answer itself
        r["pacing"] = list(dict.fromkeys((r.get("pacing") or []) + director_report.retime_dropped(raw)))
    except Exception as e:  # noqa: BLE001 - an old or odd answer must not break Step 1, but the checks' absence is said
        cap(f"⚠ Không chạy được các kiểm của tổ làm phim trên bảng shot hiện tại: {escape(str(e)[:160])}")
        return
    try:                                             # S6.1 (Q7): the whole project's estimate the moment the shot plan exists
        from core import project_budget
        prop = project_budget.propose(p, pid)
        cap(f"💵 Dự tính tổng dự án theo bảng shot này ≈ **{prop['total']:.2f} USD** — "
                   + " · ".join(f"{label} {prop['stages'][k]['cap']:.2f}" for k, label in project_budget.STAGES.items()
                                if prop["stages"][k]["cap"]) + " (đã gồm vẽ lại / làm lại dự phòng; duyệt và khóa ở 💵 Ngân sách dự án)")
    except Exception:  # noqa: BLE001 - an estimate line only; the budget panel says why when opened
        pass
    from core import project_defaults
    for c in project_defaults.changed_places(p.conn, pid):      # S3.8: the plan was made with an older version of this place
        say("warning", f"🗺 Bối cảnh **{escape(c['name'])}** {c['what']} sau khi Director chia shot"
            + (f" — cảnh {', '.join(map(str, c['scenes']))} dùng bản cũ" if c["scenes"] else "")
            + ": bấm “↻ Chia shot lại cảnh này” ở cảnh đó (tốn một lượt Claude) hoặc giữ nguyên nếu thay đổi không ảnh hưởng.",
            f"script-place-{pid}-{c['name']}", f"🗺 Bối cảnh {c['name']} {c['what']} sau khi chia shot")
    if r.get("unrecorded"):
        say("warning", "⚠ Director đã hy sinh (" + ", ".join(r["unrecorded"]) + ") mà không ghi lý do (`tradeoffs`).", f"script-unrec-{pid}",
            f"Director hy sinh {len(r['unrecorded'])} thứ mà không ghi lý do")
    trade = [t for t in r["tradeoffs"] if isinstance(t, dict)]
    if trade:
        with st.expander(f"⚖ Director đã đánh đổi {len(trade)} chỗ"):
            st.markdown("\n".join(f"- Cảnh {t.get('scene', '?')}: chọn **{escape(str(t.get('chose') or ''))}**, bỏ "
                                  f"{escape(str(t.get('gave_up') or ''))} — {escape(str(t.get('why') or ''))}" for t in trade))
    if r.get("payoff_unplanted"):
        say("warning", "⚠ Cảnh gặt lại điều chưa được gieo ở cảnh nào trước (`beat.payoff` không có `plant` trước đó): "
            + ", ".join(map(str, r["payoff_unplanted"])), f"script-payoff-{pid}", f"{len(r['payoff_unplanted'])} cảnh gặt lại điều chưa được gieo")
    if r.get("turns_without_cause"):
        cap("💡 Gợi ý (nguyên nhân cú xoay · lý do máy chuyển động): " + " · ".join(escape(w) for w in r["turns_without_cause"]))
    from core import story_check
    seen = story_check.load(C.DATA, pid)
    if seen:
        lost = [c for c in seen.get("confusing") or [] if isinstance(c, dict)]
        with st.expander(f"👀 Người xem lần đầu hiểu {seen.get('understood', '?')}/5" + (f" · ❓ {len(lost)} chỗ khó hiểu" if lost else "")
                         + (" · (bảng shot đã đổi sau lần đọc)" if seen.get("fingerprint") != story_check.fingerprint(story_check.digest(p, pid))
                            else "")):
            st.markdown("\n".join(f"- {escape(line)}" for line in story_check.lines(seen)))
            cap("Claude chỉ đọc cái sẽ hiện trên màn hình (hành động, thoại, chữ), không đọc ý đồ Director — để thấy chỗ người xem thật "
                       "có thể không hiểu. Chỉ là gợi ý: kết mở / giấu nguyên nhân có chủ ý vẫn được.")
    if r.get("continuity"):
        cap("🧭 Liền mạch: " + " · ".join(escape(w) for w in r["continuity"]))
    if r.get("acting"):
        cap("🎭 Diễn xuất: " + " · ".join(escape(w) for w in r["acting"]))
    if r.get("pacing"):
        cap("⏱ Nhịp / góc máy kịch bản: " + " · ".join(escape(w) for w in r["pacing"]))
    if r.get("sound"):
        cap("🔊 Âm thanh: " + " · ".join(escape(w) for w in r["sound"]))
    if r.get("script_notes"):
        with st.expander(f"📝 Ghi chú kịch bản của Đạo diễn cho người viết ({len(r['script_notes'])}) — chỉ đề xuất, thoại không bị sửa"):
            st.markdown("\n".join(f"- Cảnh {n.get('scene', '?')}"
                                  + (f" · {escape(str(n['kind']))}" if n.get("kind") else "") + f": {escape(str(n['note']))}"
                                  for n in r["script_notes"]))


def _director_review(p: Pipeline, pid: int) -> None:
    """GĐ5 "Đạo diễn duyệt" (two-pass Director): code compared each scene's shots with the Director's intent — lines, seconds frame,
    focus character in frame, a hold shot after a strong moment. Flags need the person's eye; nothing is re-asked on its own."""
    from core import director_two_pass
    try:
        rv = json.loads(p.project(pid)["director_raw"] or "{}").get("review")
    except (ValueError, KeyError, AttributeError):
        rv = None
    if not isinstance(rv, dict) or not rv.get("scenes"):
        return
    rows = director_two_pass.review_text(rv)
    if rv.get("flagged"):
        say("warning", "🎬 Đạo diễn duyệt bảng shot của Quay phim: cảnh " + ", ".join(map(str, rv["flagged"])) + " lệch ý đồ — xem lại "
            "(sửa shot bằng ô sửa, hoặc “↻ Chia shot lại cảnh này” kèm lý do).", f"script-dirrev-{pid}",
            f"🎬 Đạo diễn duyệt: {len(rv['flagged'])} cảnh lệch ý đồ")
    with st.expander(f"🎬 Đạo diễn duyệt ({len(rv['scenes']) - len(rv.get('flagged') or [])}/{len(rv['scenes'])} cảnh đạt ý đồ)"):
        st.markdown("\n".join(f"- {escape(r)}" for r in rows))
        notes = [f"Cảnh {r['idx']}: {n}" for r in rv["scenes"] for n in r.get("notes") or []]
        if notes:
            cap("Ghi chú diễn xuất / âm thanh theo từng cảnh: " + " · ".join(escape(n) for n in notes[:12]))


# siblings (bottom import: the parts use each other's functions at call time only)
from dashboard.steps.step1_run import *  # noqa: F401,F403
from dashboard.steps.step1_run import _budget_summary  # noqa: F401
from dashboard.steps.step1_prep import *  # noqa: F401,F403
from dashboard.steps.step1_characters import *  # noqa: F401,F403
from dashboard.steps.step1_characters import _voices, _bible_summary, _anchor_reset  # noqa: F401
