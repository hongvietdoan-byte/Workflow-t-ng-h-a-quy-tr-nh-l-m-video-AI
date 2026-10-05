"""Step 1: 📋 Bảng kê tài nguyên trước Director (S14.23, cờ `asset_checklist`; core/asset_checklist.py).

Drawn right above the Director's run buttons (1d panel and the v2 hero "Lập kế hoạch"). Flag off → returns before touching Streamlit,
so the screen and the flow are exactly as before."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from core import asset_checklist


def _row_text(r) -> str:
    kind = assets.KINDS.get(r["kind"], r["kind"])
    who = f" (cho {r['for_character']})" if r.get("for_character") else ""
    where = f" · cảnh {', '.join(map(str, r['scenes']))}" if r.get("scenes") else ""
    main = " · chính" if r.get("main") else " · phụ"
    extra = " — ".join(x for x in [r.get("why"), r.get("note")] if x)
    mark = f" · 🔎 Claude duyệt ({r['claude_only']} ảnh, chưa xác nhận)" if r.get("claude_only") else ""
    return f"{r['status_label']}{mark} · **{r['name']}**{who} [{kind}]{where}{main}" + (f" — {extra}" if extra else "")


def checklist_panel(p: Pipeline, pid: int, scope: str = "dir") -> None:
    """`scope` keeps the widget keys apart when the panel is drawn twice on one screen (1d panel + v2 hero)."""
    if not asset_checklist.enabled():
        return
    with st.container(border=True):
        st.markdown("**📋 Bảng kê tài nguyên** — xem kịch bản cần gì, Kho đã có gì, TRƯỚC khi trả tiền cho Director "
                    "(🧪 cờ `asset_checklist`, chưa thử thật)")
        res = asset_checklist.get(p, pid)
        client = llm_client()
        if st.button(("📋 Lập bảng kê tài nguyên" if res is None else "↻ Lập lại bảng kê")
                     + cost.llm_button_tag(p.conn, asset_checklist.STAGE, 1),
                     key=f"asset_chk_{scope}_{pid}", disabled=client is None,
                     help="Một lượt Claude (không ảnh; tối đa 2 lượt nếu sai định dạng — giá trên nút đã tính cả 2): đọc kịch bản, kê nhân vật / nơi / đồ vật / vũ khí / thú cưng / trang phục, ghép với "
                          "Kho. Code kiểm lại id và loại." if client else claude_hint()):
            with st.spinner("Claude đang kê tài nguyên kịch bản cần…"):
                if act(lambda: asset_checklist.run(p, pid, client)):
                    st.rerun()
        if client is None:
            st.caption(claude_hint())
        if res is None:
            st.caption("Chưa lập bảng kê cho kịch bản này — Director vẫn chạy được như cũ.")
            return
        if res["stale"]:
            st.warning("Kịch bản đã đổi sau lần kê — bảng dưới có thể sai, bấm ↻ Lập lại bảng kê.")
        for w in res["warnings"]:
            st.warning(w)
        n_miss = len(res["missing"])
        st.markdown(f"{len(res['rows'])} thứ kịch bản cần · " + (f"⚠️ **{n_miss} thiếu**: {', '.join(res['missing'])}" if n_miss
                                                                  else "✅ Kho đã có đủ"))
        for i, r in enumerate(res["rows"]):
            c1, c2 = st.columns([6, 1])
            c1.markdown(_row_text(r))
            if r.get("claude_only") and r.get("asset_id") is not None:
                from core import kho_review
                if c2.button("Xác nhận", key=f"asset_chk_cf_{scope}_{pid}_{i}", help="Xác nhận ảnh Claude đã duyệt sơ bộ của mục này (→ đã duyệt)."):
                    if act(lambda aid=r["asset_id"]: kho_review.confirm_asset(p.conn, aid), f"Đã xác nhận ảnh của {r['name']}"):
                        st.rerun()
                if c2.button("Thu hồi", key=f"asset_chk_rv_{scope}_{pid}_{i}", help="Đưa ảnh Claude duyệt của mục này về chờ duyệt (không dùng nữa)."):
                    def _revoke(aid=r["asset_id"]):
                        for x in kho_review.claude_only_images(p.conn, [aid]):
                            kho_review.revoke(p.conn, "image", x["id"])
                    if act(_revoke, f"Đã thu hồi ảnh của {r['name']}"):
                        st.rerun()
            if r["status"] == "in_library":
                if c2.button("Gắn", key=f"asset_chk_att_{scope}_{pid}_{i}",
                             help="Gắn mục Kho này vào dự án — Director sẽ đọc nó trong 'Tài nguyên có sẵn'."):
                    if act(lambda aid=r["asset_id"]: asset_checklist.attach(p, pid, aid), f"Đã gắn {r['name']}"):
                        st.rerun()
        if n_miss:
            st.caption("Thứ ⚠️ thiếu: tạo mới ở 📚 Kho (hoặc khối 🖼 Tham chiếu & gắn ảnh sau phân tích cảnh) rồi bấm ↻ Lập lại bảng kê. "
                       "Chạy Director khi còn thiếu thì Director tự tả ngoại hình những thứ đó.")
