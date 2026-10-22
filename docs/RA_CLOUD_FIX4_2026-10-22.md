# C-FIX4 — nút "✓ Đã sửa" trên mục rà LỖI gọi Claude mà không báo giá (cloud-C, 22/10)

- Nhánh: `cloud/v31-fix4`, tách từ `origin/main` (đã có C-FIX3-THAP-B).
- 0 USD. Không đổi cờ, không migration.

## Lỗi
- C-FIX3-THAP-B đổi `close(…, "resolved")` trên mục rà lỗi (`review_fail`) thành `rerun_failed`, để nút "✓ Đã sửa" không mở cổng khi chưa ai rà.
- Hệ quả: bấm "✓ Đã sửa" âm thầm đưa thay đổi về chờ rà, và vòng nền gọi Claude.
- Lời gọi đó tốn tiền mà không có ước tính, không báo trước — trái `docs/CHUAN_XAY_DUNG.md` ("mọi lời gọi tốn tiền qua sổ chi + ước tính trước").
- Nút "↻ Rà lại" sẵn có cũng chưa hiện ước tính.

## Sửa
**`dashboard/change_review_ui.py`** — mục rà lỗi còn thay đổi chưa rà (`CR.rerun_targets(...) > 0`):
- KHÔNG có "✓ Đã sửa";
- chỉ còn "↻ Rà lại · Claude ≈ X USD (ước tính)" và "Bỏ qua";
- giá lấy qua `cost.llm_button_tag(conn, "change_review", 1)`, theo quy ước nút Claude S14.2 A2: nhân `LLM_MARGIN`, chưa có giá thì "ước tính dư". Giá tính một lần cho cả khung.
- Một lần Rà lại = một lời gọi: các lần lỗi của mục cùng một shot nên vòng nền gộp thành một nhóm.
- Thay đổi đã bị dọn (`KEEP_DAYS`, `rerun_targets` = 0): không còn gì để rà, nên hiện "✓ Đã sửa" (0 USD) như mục thường, không có nút Rà lại báo giá giả.

**`core/change_review.py`:**
- `close(…, "resolved")` trên mục rà lỗi còn thay đổi chưa rà → `ValueError(FIXED_ON_FAIL)`. Không đổi gì: không đóng mục (cổng vẫn giữ) và không gọi Claude. Thay đổi đã bị dọn thì đóng như thường.
- `rerun_targets(conn, finding_id)`: chỉ đọc, đếm các lần lỗi mà "Rà lại" sẽ đưa về chờ rà. Dùng chung điều kiện `_RERUN_WHERE` với `rerun_failed`.
- `rerun_tag(conn)`: chữ giá cho nút.
- Chỉ có `change_review_ui` gọi `CR.close`. `inbox_clean` và `pipeline` đóng mục bằng SQL trực tiếp, không gặp `ValueError` mới (rà).

## Test
- `tests/test_v31_fix4.py` (AppTest trên khung thật, 4 test):
  - mục rà lỗi không có `cr_ok_`, còn mục thường vẫn có;
  - nút `cr_rerun_` hiện giá ×`LLM_MARGIN` trước khi bấm;
  - vẽ khung không gọi Rà lại;
  - "Bỏ qua" không gọi `rerun_failed`;
  - chỉ bấm "Rà lại" mới đưa về chờ rà;
  - thay đổi đã bị dọn → hiện "✓ Đã sửa" và đóng được.
- `tests/test_change_review.py`:
  - `…neither_releases_nor_spends`: `close('resolved')` báo lỗi, `rerun_failed` KHÔNG được gọi, mục vẫn mở, cổng vẫn giữ;
  - `…whose_changes_are_gone`: thay đổi đã bị dọn → đóng được.
- ĐỎ trên main: test AppTest giá / không ✓ và 2 test core. "Bỏ qua" và "Rà lại" là test chặn hồi quy (xanh cả trên main).
- `tests/test_v31_fix4.py` đã được đăng ký vào khu vực `core_infra` (`devsys/areas.json`).

## Rà soát (quy tắc 7)
- Không có lỗi CAO. Đã sửa:
  - VỪA: giá thiếu `LLM_MARGIN` → dùng `llm_button_tag`;
  - THẤP: thay đổi đã bị dọn mà vẫn hiện nút Rà lại báo giá → hiện ✓;
  - THẤP: giá tính lại ở mỗi dòng → tính một lần.
- **Tồn đọng, có từ trước, ngoài phạm vi C-FIX4 — đề xuất cho phiên chính:**
  - Dự án không có Claude (vòng nền không có client): "Rà lại" đưa lần lỗi về `pending`, rồi `_review_group` chuyển thành `code_only` với `note` rỗng.
  - Trạng thái đó không còn nằm trong `_UNREVIEWED`, nên cổng mở khi chưa ai rà, trong khi nút vẫn báo "Claude ≈ X USD".
  - Cách sửa có thể: không cho Rà lại (hoặc giữ `failed`) khi dự án không có Claude.

## Kết quả cả bộ
- Full suite (cloud 3.13, `-m "not slow" -n auto`) trên 85992465: **7104 passed**. 25 đỏ đều là golden cần native Python 3.14 (nền).
- Sau bản sửa theo rà: test liên quan (`test_v31_fix4`, `test_change_review`) có 69 xanh; full suite **7105 passed** (25 golden nền).
