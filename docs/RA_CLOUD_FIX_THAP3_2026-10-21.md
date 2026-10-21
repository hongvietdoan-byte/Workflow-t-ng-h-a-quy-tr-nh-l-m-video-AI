# C-FIX-THAP-3 — 3 lỗi THẤP từ rà 20/10 (cloud-D, 21/10)

Nhánh `cloud/v31-fix-thap-3` từ `origin/main` (`447fde9b` đã gộp). Cờ giữ TẮT (`release_gate`). 0 USD.

1. **`core/release_gate.py` summary** — chỉ THIẾU ĐO (G4 đối soát chi phí luôn KHÔNG RÕ trên Dashboard) không còn gọi là "CHƯA ĐẠT":
   `❔ Cổng phát hành: CHƯA ĐO ĐỦ — đạt 7 · chưa đo 1 · chưa đạt 0`; có mục chưa đạt thật → `⚠ … CHƯA ĐẠT — đạt 6 · chưa đo 1 · chưa đạt 1`.
   `ok` vẫn False khi còn KHÔNG RÕ (không bao giờ coi là đạt); mục chưa đo vẫn liệt kê lý do.
2. **Cache G2/G3** — `check(..., cache=)` + `_cached`: `final_qc.run` và `delivery.status` nhớ theo (id bản final mới nhất, id output mới
   nhất của dự án = lớp phụ đề / card / kích thước, mtime tệp final) + hạn `CACHE_TTL_S` 120 s (thiết lập đổi mà chưa dựng lại vẫn hiện
   "⚠ cũ" trong ≤ 2 phút). Bản cũ của cùng phép đo bị bỏ khỏi cache. `dashboard/steps/step5.py` `_deliver_button` truyền
   `st.session_state["release_gate_cache"]`. Không truyền cache = đo mỗi lần như cũ.
3. **`devsys/errors_page.py`** `use_container_width=True` → `width="stretch"`.

Test `tests/test_v31_fix_thap3.py` (9; ĐỎ 8 trên code cũ → XANH 9). Vùng: test_v31_dp6_release_gate, test_errors_page, test_final_qc,
test_dashboard, test_delivery_resolution, test_ui_* — 294 qua.
Rủi ro: TTL 120 s là đánh đổi (đổi thiết lập không qua dựng lại → G3 cập nhật chậm tối đa 2 phút). Quy ước 7: luật cloud không mở Agent →
tự rà theo `tools/related_areas.py` (không khu vực nào khác gọi tới release_gate / errors_page).
