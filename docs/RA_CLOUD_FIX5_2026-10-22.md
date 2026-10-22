# C-FIX5 — rà C-FIX4 + C-M83-TOOL (cloud-C, 22/10)

0 USD. Không đổi cờ.

## 1. VỪA — C-M83-TOOL chưa gộp: bản sao `--db` còn đường tới tệp THẬT (nhánh `cloud/v31-m83-tool`)
- Sửa bằng `relocate` ở mỗi mức đo. Chi tiết, bảng rà và test: `docs/RA_CLOUD_M83_TOOL_2026-10-22.md` mục "C-FIX5".
- Test chạy Chromium thật trên bản sao CSDL có `result_path` tuyệt đối tới tệp thật:
  - sau lượt đo, danh sách và mtime tệp thật không đổi;
  - CSDL của mức đo không còn đường thật;
  - tắt `relocate` thì test này ĐỎ.

## 2. THẤP — C-FIX4 (đã gộp main; nhánh `cloud/v31-fix5` từ main)
- `dashboard/change_review_ui.py`, nút "✓ Đã sửa":
  - trước đây `close()` ném `ValueError` khi mục rà lỗi vừa có thay đổi chưa rà (do phiên khác) và trang hiện traceback;
  - nay bắt lỗi và hiện `st.error` "… — tải lại trang để thấy nút ↻ Rà lại", giống nút Rà lại (rà THẤP-6: nút cũ còn hiện tới lần vẽ sau).
- `tests/test_v31_fix4.py`: `tmp_path` thay `tempfile.mkdtemp`. Test mới `test_fixed_on_a_failure_finding_that_gained_changes_meanwhile_says_why` ĐỎ trên main, XANH sau sửa.
- Rà (quy tắc 7): không còn nơi nào khác gọi `CR.close` / `rerun_failed` mà chưa bọc. `inbox_clean` và `pipeline` đóng mục bằng SQL và không chạm mục `review_fail`.

## Test
- `tests/test_v31_fix4.py` + `tests/test_change_review.py`: 70 xanh.
- `tests/test_load_test_ui.py` (nhánh m83): 30 xanh.
