# HANDOFF — C-FIX6 phần A (nhánh claude/v31-fix6-desk)

**Đã xong:** mục 1–6 phần A cùng các lỗi rà quy ước 7. Chi tiết ở `docs/RA_CLOUD_FIX6_2026-10-22.md`. Test liên quan xanh: 342 passed. `py -m core.decisions check` khớp.

**Đang dở:** không có.

**Bước kế (phiên chính):**
1. Gộp cùng tích hợp M2 / C-M48-DESK-CORE khi golden ĐẠT.
2. Ghi XONG hộp thư C-FIX6, kèm 2 nhánh @ SHA. Phần B (C-M83-TOOL, `tools/load_test_ui.py`) làm riêng.
3. Ở bước gộp, chạy cả bộ và các test chậm `related_areas` nêu.
