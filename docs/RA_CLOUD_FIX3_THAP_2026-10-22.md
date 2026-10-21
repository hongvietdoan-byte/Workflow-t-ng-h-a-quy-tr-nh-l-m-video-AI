# C-FIX3-THAP — 3 lỗi THẤP sau rà kỹ C-M71-FIX + C-M63-FIX2 (cloud-C, 22/10)

- Nhánh: `cloud/v31-fix3-thap`, tách từ `origin/main`.
- 0 USD. Không đổi cờ.

## 1. Mục ĐỎ "rà lỗi" của sự kiện motion `failed` khi tắt cờ `change_review_motion` (`core/change_review.py` `process_pending`)
- Trước đây, khi cờ TẮT, chỉ sự kiện motion `pending` / `code_only` bị chuyển thành `skipped`.
  - Sự kiện motion `failed` (vd Claude timeout) không đổi, nên mục ĐỎ của nó vẫn mở và vẫn chặn cổng.
- Nay sự kiện `failed` cũng chuyển thành `skipped`, nên `_hold_failed` (C-M71-FIX) tự đóng mục.
- `note` giữ lời lỗi gốc (`… — trước: <lỗi>`) và ghi rõ: tắt cờ là bỏ HẲN việc rà các lần sửa motion trong thời gian đó, kể cả lần đã lỗi; bật lại cờ cũng không rà lại. Cách này nhất quán với thiết kế C4.
- Test chạy qua `process_pending` THẬT:
  1. cờ BẬT, client ném timeout → sự kiện `failed` + mục ĐỎ;
  2. cờ TẮT, `process_pending` → `blocking` = None, không còn mục `ra_soat`, note vẫn giữ lời lỗi.
- ĐỎ trên code cũ.

## 2. Test chạy `rewrite()` THẬT với hai nguồn Claude + `saved_view` (`tests/test_v31_m71_fix.py`)
- Kịch bản:
  - Claude của nguồn A (`anthropic`) ném `out_of_credit` → D6 của job A tạm ngừng, lượt sau không gọi Claude;
  - job nguồn B (`claude_cli`) vẫn gọi Claude và dùng bản D6.
- `saved_view`: A trả `paused`, B trả `saved`. `say` có `QUOTA_CODE` cho A, không có cho B, nên test chứng minh là tạm ngừng thật chứ không phải trúng cache D6.
- ĐỎ trên `chat_prompt.py` trước C-M71-FIX (khóa chung → B không được gọi).

## 3. Job clip nhóm có `scene_id` NULL (`core/gen_auth.py` `_repair_budget`)
- Trước đây job này bị bỏ khỏi CẢ lượt đầu lẫn làm lại, nên khoản chi biến mất khỏi ngân sách.
- Nay job được tính theo các shot thành viên, như trước C-M63-FIX2. Bên làm lại được ưu tiên (thận trọng tiền).
- **Phòng thủ:** schema `jobs.scene_id INTEGER NOT NULL` (`core/db.py:93`) và không có migration dựng lại bảng. Ngoài thực tế chỉ gặp với dữ liệu cũ / hỏng.
- Test dựng `ctx` tay. ĐỎ trên code cũ.

## Rà soát (quy tắc 7)
- Không có lỗi CAO hay VỪA. Đã sửa:
  - giữ lời lỗi gốc trong `note`;
  - assert chặt hơn ở test (2): `said`, B = `saved`.
- Ghi nhận, không sửa:
  - `resolved_by='change_review'` của mục đóng do tắt cờ trông giống "rà đạt"; xem `note` của sự kiện để biết lý do thật;
  - từ lúc tắt cờ tới lượt nền kế, mục vẫn chặn — vài chục giây.

## Test
- Test liên quan (`test_v31_m71_fix`, `test_change_review`, `test_v31_m63_gen_auth`): 103 xanh.
- Full suite (cloud 3.13): **7091 passed**. 25 đỏ đều là golden cần native Python 3.14 (nền). Không còn tệp lạ trong cây làm việc sau khi chạy.
