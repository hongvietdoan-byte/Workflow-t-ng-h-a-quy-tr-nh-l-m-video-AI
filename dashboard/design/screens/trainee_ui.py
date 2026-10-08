"""B7 học việc (08/10, docs/KE_HOACH_HOC_VIEC_2026-10-08.md mục 1 + 3): the 🎓 parts of the screens.

- `mode_control`: the 3-button switch "Tắt / 🎓 Học việc / Bật" of a flag that has the học việc mode (màn 🧪).
- `render_table`: one line per học việc flag — agreement pooled / per project, balanced, baseline, too strict / loose, money spent, what is
  still missing, and "🎓 đủ chuẩn — chờ bạn duyệt" when `trainee.agreement()["ready"]` (never changes `verified`: the person does).
- `render_cards`: the one-click 👍/👎 cards for the roles judged by a card (only rows of DELIVERED projects, still without a truth —
  the person decided first, the role's guess stays hidden until then).
- `build_split`: the step-5 build fold — "🧪 chưa kiểm thật" apart from "🎓 đang học việc" (that never changes the cut).
Every click here is 0 USD."""
import json
from html import escape
from typing import Dict, List, Optional

import streamlit as st

from core import features, trainee

MODE_LABELS = {"off": "Tắt", "trainee": "🎓 Học việc", "on": "Bật"}
TRAINEE_BADGE = "🎓 học việc — chi tiền ghi sổ riêng, không đổi phim"
READY = "🎓 đủ chuẩn — chờ bạn duyệt"
CARD_FEATURES = tuple(k for k, r in trainee.RULES.items() if r["truth"] == "card")
# KIEM_22 (08/10): with seedance_ref_groups on, these three really ON do nothing (refs-only clips: no group / stretch / end frame)
NO_EFFECT_WITH = {"camera_setups": "seedance_ref_groups", "continuous_takes": "seedance_ref_groups", "end_frames": "seedance_ref_groups"}
# usage_events.stage of a 🎓 role's paid call → its flag (B5 trainee_qc_team, B6 trainee_establishing)
STAGE_FEATURE = {"trainee_qc_team": "qc_team", "trainee_establishing": "scene_establishing"}
UNVERIFIED_NOTE = ("Bật / tắt ở màn 🧪 Tính năng thử (dòng FEATURE_… trong dashboard.env vẫn đọc, nhưng với cờ có chế độ học việc "
                   "giá trị 1 chỉ là 🎓 học việc — bật thật chỉ ở màn 🧪). Sau khi một lần chạy thật chứng minh tính năng đúng, ghi `verified` trong "
                   "core/features.py (kèm ngày, dự án, số đo) — bản giao chính nên chỉ dùng tính năng đã kiểm.")
DECISION_LABELS = {"establish": "vẽ ảnh toàn cảnh", "skip": "bỏ qua", "group": "gộp nhóm góc máy", "stretch": "quay liền một đoạn",
                   "need_end": "cần khung cuối"}


def apply_mode(name: str, mode: str) -> Dict:
    """"on"/"off" go to "flags", "trainee" to "modes" (features.save_settings keeps them apart)."""
    return features.save_settings(modes={name: mode})


def mode_control(name: str) -> None:
    cur = features.state(name)
    new = st.segmented_control("Chế độ", list(MODE_LABELS), default=cur, format_func=MODE_LABELS.get, key=f"featm_{name}",
                               label_visibility="collapsed")
    if new and new != cur:
        apply_mode(name, new)
        st.rerun()


def no_effect_note(name: str) -> str:
    """Said next to a flag that is really ON but changes nothing in this configuration."""
    other = NO_EFFECT_WITH.get(name)
    if other and features.on(name) and features.on(other):
        return (f"⚠ Bật thật nhưng không có tác dụng khi `{other}` bật (clip chỉ-ảnh-tham-chiếu: không gộp / quay liền / khung cuối) "
                "— dùng 🎓 Học việc để vẫn đo được.")
    return ""


def _row_usd(r, pricing: Dict) -> Optional[float]:
    from core import cost
    if str(r["provider"]).startswith("mock"):
        return 0.0
    if r["kind"] == "image":
        price = cost._number(pricing.get("per_image", {}).get(r["model"]))
    elif r["kind"] == "audio":
        price = cost._number(pricing.get("per_audio", {}).get(r["model"]))
    elif r["kind"] == "llm":
        from core.budget import token_price
        return token_price(pricing, r["model"], r["tier"], r["quantity"])
    else:
        return cost.clip_price(pricing, r["model"], r["tier"], r["quantity"])
    return None if price is None else price * r["quantity"]


def spent_by_feature(conn, pricing: Optional[Dict] = None) -> Dict[str, float]:
    """USD of the 🎓 roles' paid calls (usage_events.stage LIKE 'trainee_%'), per flag; a price that is unknown counts 0 (said apart)."""
    if pricing is None:
        from core import cost
        try:
            pricing = cost.load_pricing()
        except Exception:  # noqa: BLE001 - no price table: the spend column says "?" instead of breaking the screen
            return {}
    out: Dict[str, float] = {}
    for r in conn.execute("SELECT * FROM usage_events WHERE stage LIKE 'trainee_%'").fetchall():
        feat = STAGE_FEATURE.get(r["stage"]) or r["stage"][len("trainee_"):]
        usd = _row_usd(r, pricing)
        out[feat] = out.get(feat, 0.0) + (usd or 0.0)
    return out


def _look_trusted(conn) -> bool:
    row = conn.execute("SELECT detail FROM trainee_log WHERE feature='storyboard_auto_trust' ORDER BY at DESC, id DESC LIMIT 1").fetchone()
    try:
        return bool(row and json.loads(row["detail"] or "{}").get("trusted"))
    except ValueError:
        return False


def _pct(x) -> str:
    return "—" if x is None else f"{x:.0%}"


def table_rows(conn) -> List[Dict]:
    spent = spent_by_feature(conn)
    out = []
    for name in features.trainee_list():
        if name not in trainee.RULES:
            continue
        a = trainee.agreement(conn, name, look_trusted=_look_trusted(conn) if name == "storyboard_auto_trust" else None)
        per = ", ".join(f"#{p} {d['rate']:.0%} (n={d['n']})" for p, d in sorted(a["per_project"].items())) or "—"
        usd = spent[name] if name in spent else (a["cost_usd"] or 0.0)       # the ledger first; else what the rows say
        out.append({"feature": name, "mode": features.state(name), "ready": a["ready"], "missing": a["missing"],
                    "status": READY if a["ready"] else f"đang học ({a['n']} {trainee.RULES[name]['unit']} đã chấm)",
                    "Cờ": name, "Chế độ": MODE_LABELS[features.state(name)], "Khớp gộp": f"{_pct(a['rate'])} (n={a['n']})",
                    "Theo dự án": per, "Khớp cân bằng": _pct(a["balanced"]), "Mức nền": _pct(a["baseline"]),
                    "Quá chặt / lỏng": f"{a['too_strict']} / {a['too_loose']}", "Đã chi": f"{usd:.2f} USD",
                    "Còn thiếu": "; ".join(a["missing"]) or "—"})
    return out


def render_table(conn) -> None:
    rows = table_rows(conn)
    if not rows:
        return
    st.markdown("**🎓 Học việc — độ khớp với bạn** (chạy bóng, không đổi phim; đủ chuẩn thì bạn tự duyệt bật thật)")
    for r in rows:
        head = f"**{escape(r['feature'])}** · {r['Chế độ']} · " + (f"**{READY}**" if r["ready"] else escape(r["status"]))
        st.markdown(head + f"  \nKhớp gộp {r['Khớp gộp']} · theo dự án: {escape(r['Theo dự án'])} · khớp cân bằng {r['Khớp cân bằng']}"
                    f" · mức nền {r['Mức nền']} · quá chặt / lỏng {r['Quá chặt / lỏng']} · đã chi {r['Đã chi']}")
        if r["missing"]:
            st.caption("Còn thiếu: " + escape("; ".join(r["missing"])))


def rescore(conn) -> Dict[int, Dict]:
    """"Chấm lại" (0 USD): score every project that has a học việc row against the person's review_log."""
    pids = [r[0] for r in conn.execute("SELECT DISTINCT project_id FROM trainee_log ORDER BY project_id").fetchall()]
    return {pid: trainee.score_project(conn, pid) for pid in pids}


def card_rows(conn, limit: int = 40) -> List[Dict]:
    """Rows waiting for a 👍/👎: a card role, no truth yet, of a project that HAS a delivery (the person decided the film first)."""
    q = (f"SELECT t.id, t.feature, t.project_id, t.subject, t.decision, t.detail FROM trainee_log t "
         f"WHERE t.feature IN ({','.join('?' * len(CARD_FEATURES))}) AND t.truth IS NULL "
         "AND t.project_id IN (SELECT project_id FROM deliveries) ORDER BY t.project_id, t.id LIMIT ?")
    return [dict(r) for r in conn.execute(q, (*CARD_FEATURES, limit)).fetchall()]


def render_cards(conn) -> None:
    rows = card_rows(conn)
    with st.expander(f"Chấm học việc ({len(rows)} thẻ chờ)"):
        if not rows:
            st.caption("Chưa có thẻ: chỉ hiện quyết định của vai học việc ở dự án ĐÃ có bản giao (bạn quyết trước, 0 USD).")
            return
        st.caption("Vai học việc đã đoán thế này — đúng ý bạn không? 👍 đúng / 👎 sai. Một cú bấm, 0 USD.")
        for r in rows:
            c1, c2, c3 = st.columns([6, 1, 1], vertical_alignment="center")
            c1.markdown(f"#{r['project_id']} · `{escape(r['feature'])}` · {escape(r['subject'])} → "
                        f"**{escape(DECISION_LABELS.get(r['decision'], r['decision']))}**")
            for col, agree, icon, key in ((c2, True, "👍", "ok"), (c3, False, "👎", "no")):
                if col.button(icon, key=f"trn_{key}_{r['id']}"):
                    trainee.label(conn, r["id"], agree, "card")
                    st.rerun()


def render_panel(conn) -> None:
    """Màn 🧪: the agreement table, "Chấm lại" and the cards."""
    if not features.trainee_list():
        return
    render_table(conn)
    if st.button("↻ Chấm lại (0 USD)", key="trn_rescore", help="So quyết định của vai học việc với lần duyệt của bạn (review_log)"):
        rescore(conn)
        st.rerun()
    render_cards(conn)


def build_split() -> Dict:
    """Step 5: what this cut is really trying out (ON and not verified) vs the 🎓 roles that ran in the shadow (never in the cut)."""
    return {"unverified": features.on_unverified(), "trainee": [k for k in features.trainee_list() if features.shadow(k)]}


def render_build_split(conn=None) -> None:
    s = build_split()
    if s["unverified"]:
        with st.expander(f"🧪 Bản dựng đang dùng {len(s['unverified'])} tính năng chưa kiểm thật"):
            st.markdown("\n".join(f"- `{k}` — {escape(v['label'])}" for k, v in sorted(s["unverified"].items())))
            st.caption(UNVERIFIED_NOTE)
    if s["trainee"]:
        with st.expander(f"🎓 {len(s['trainee'])} vai đang học việc (không ảnh hưởng bản dựng này)"):
            for k in s["trainee"]:
                line = f"- `{k}` — {escape(features.FEATURES[k].get('label', ''))}"
                if conn is not None and k in trainee.RULES:
                    try:
                        a = trainee.agreement(conn, k)
                        line += f" · khớp {_pct(a['rate'])} (n={a['n']})" + (f" · **{READY}**" if a["ready"] else "")
                    except Exception:  # noqa: BLE001 - the figure is optional; the list is still shown
                        line += " · chưa tính được độ khớp"
                st.markdown(line)
            st.caption("Vai học việc chạy bóng: ghi quyết định để so với bạn, không chặn / vẽ lại / đổi gì trong phim. Chấm ở màn 🧪.")
