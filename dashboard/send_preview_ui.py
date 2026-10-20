"""V3.1 M4.7 phần XEM (C-M47A, cờ send_preview_panel — tắt = thẻ clip y cũ): hai khung gập dưới thẻ clip Bước 4.
"📦 Gói sẽ gửi": bấm "Dựng gói (0 USD)" → core.send_preview.video_package (đúng đường nút Gen, không gửi, không gọi Claude / nhà cung cấp):
thứ tự ảnh ref + nhãn + vai, prompt, model, tham số, giá send_estimate (cờ đó bật), ghi chú của runner.
"🔎 QC shadow": bản ghi M4.2 / M4.3 / M4.1 của clip (core.send_preview.shadow_of). CHỈ XEM — không nút sửa / override (C3-4 chờ)."""
import json

import streamlit as st

from core import send_preview


def _data_dir(runner) -> str:
    if runner is not None and getattr(runner, "data_dir", None):
        return runner.data_dir
    from dashboard import common as C
    return C.DATA


def card_block(p, pid: int, j, runner, idx=None) -> None:
    """Nothing at all when the flag is off."""
    if not send_preview.enabled():
        return
    from dashboard.design import components as D
    jid = j["id"]
    with st.expander("📦 Gói sẽ gửi (xem trước, 0 USD)", expanded=False):
        st.caption("Dựng bằng đúng đường của nút Gen (job này) — không gửi, không gọi Claude / nhà cung cấp, không ghi gì.")
        key = f"sendpv_{jid}"
        if st.button("Dựng gói (0 USD)", key=f"sendpv_btn_{jid}"):
            if runner is None:
                st.session_state[key] = {"ok": False, "why": "chưa có runner video ở màn này", "notes": [], "refs": [], "price": None}
            else:
                st.session_state[key] = send_preview.video_package(p, runner, j)
        got = st.session_state.get(key)
        if got:
            _package(D, got)
    with st.expander("🔎 QC shadow (chỉ xem)", expanded=False):
        _shadow(D, send_preview.shadow_of(p.conn, _data_dir(runner), pid, j, idx))


def _package(D, got) -> None:
    from core import cost
    if got.get("price") is not None:
        st.markdown(f"**Giá lần gửi (send_estimate):** {cost.price_tag(got['price'])}")
    if not got.get("ok"):
        st.error(f"Không dựng được gói: {got.get('why')}")
    else:
        pkg = got["package"]
        st.markdown(f"**Model:** `{pkg.get('model') or '?'}` · **Nhà cung cấp:** `{pkg.get('provider') or '?'}`")
        st.markdown(D.table(["#", "Tham số", "Vai", "Nhãn", "Tệp"],
                            [[r["n"], r["param"], r["role"], r["label"] or "—", r["file"]] for r in got["refs"]],
                            empty="Không gửi ảnh / video tham chiếu"), unsafe_allow_html=True)
        st.markdown("**Prompt**")
        st.code(pkg.get("prompt") or "", language=None)
        if pkg.get("negative"):
            st.markdown("**Negative**")
            st.code(pkg["negative"], language=None)
        if pkg.get("params"):
            st.markdown("**Tham số khác**")
            st.code(json.dumps(pkg["params"], ensure_ascii=False, indent=1), language="json")
    for n in got.get("notes") or []:
        st.caption(f"{'⚠' if n['severity'] in ('warn', 'error') else 'ℹ'} {n['text']}")


def _finding_rows(findings):
    return [[f.get("qc_code") or "?", f.get("severity") or "?", f.get("why") or json.dumps(f.get("evidence") or {}, ensure_ascii=False)[:200]]
            for f in findings or []]


def _shadow(D, res) -> None:
    for rec in res["video"][-1:]:
        st.markdown(f"**QC video (M4.2)** · {rec.get('at') or ''} · {rec.get('status') or ''}")
        st.markdown(D.table(["Mã", "Mức", "Lý do"], _finding_rows(rec.get("findings")), empty="Không có phát hiện"),
                    unsafe_allow_html=True)
        for u in rec.get("chua_kiem") or []:
            st.caption(f"Chưa kiểm được: {u.get('vat') or u}")
        for n in rec.get("notes") or []:
            st.caption(n)
    if res["continuity"] or res["can_xem"]:
        st.markdown("**Logic xuyên shot (M4.3)**")
        st.markdown(D.table(["Mã", "Mức", "Lý do"], _finding_rows(res["continuity"]), empty="Không có phát hiện"),
                    unsafe_allow_html=True)
        if res["can_xem"]:
            st.caption("Cần xem: shot này phụ thuộc shot " + ", ".join(str(x) for x in res["can_xem"]) + " (có lỗi logic chuỗi)")
    for run in res["evidence"][-3:]:
        st.markdown(f"**Bằng chứng QC (M4.1)** · {run.get('qc_path') or ''} · {run.get('started_at') or ''}")
        st.markdown(D.table(["Mã", "Mức", "Lý do"], _finding_rows(run.get("findings")), empty="Không có phát hiện"),
                    unsafe_allow_html=True)
    for n in res["notes"]:
        st.caption(n)
