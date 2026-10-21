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

---

# C-FIX3-THAP-B — rà kỹ mở lại kịch bản "CAO 1" (cloud-C, 22/10)

- Cùng nhánh `cloud/v31-fix3-thap`. 0 USD, không đổi cờ, không migration.

## Lỗi (đề bài)
- Kịch bản:
  1. Cờ motion BẬT. Một nhóm rà của shot có sửa scene #a và sửa motion #b, lần rà lỗi (timeout) → cả hai `failed`. Mục ĐỎ gắn #b.
  2. Người sửa scene tiếp #c → rà đạt. `#c.before` đã ở trạng thái sau #a, nên Claude không thấy #a.
  3. Tắt cờ → #b `skipped` → mục đóng.
- Kết quả: #a nằm dưới "lần rà đạt gần nhất", nên không bao giờ ra mục mới → cổng mở, job tốn tiền được gửi khi #a chưa ai rà.

## Sửa (`core/change_review.py`)
Không vá riêng nhánh tắt cờ mà sửa gốc. Lượt rà đầu đã tìm thêm 3 lỗi cùng gốc, nên cách vá riêng bị bỏ.

**`_COVERED` — điều kiện "đã có mục che":** một lần rà lỗi được coi là đã che khi có mục `review_fail` thỏa cả 4 điều kiện:
- cùng shot;
- `event_id` ≥ lần lỗi đó;
- ghi SAU lần lỗi;
- còn mở, hoặc do người đóng (Bỏ qua / Rà lại / dọn dự án đã giao).

Mục tự đóng `'change_review'` (lần của mục đã rà xong hoặc bị bỏ) KHÔNG che các lần khác.

**`_hold_failed`:**
- Bỏ cận "id > lần rà đạt gần nhất".
- Lần rà lỗi mới nhất CHƯA được che → mục ĐỎ.
- **Mỗi shot chỉ MỘT mục mở:** nếu đã có mục mở, gắn lại mục đó vào lần lỗi mới (`event_id`, `msg`, `at`) thay vì `_add`. Trước đây `_add` bỏ qua mục trùng lời, nên lần lỗi mới không có mục nào che.

**`rerun_failed`:**
- Đưa về pending mọi lần lỗi mà mục này che (id ≤ lần của mục, không bị mục KHÁC còn mở hoặc đã Bỏ qua che).
- Trước đây nút ném "không còn trong sổ" (sai) khi lần sửa sau đã rà đạt.

**UPDATE:** không dùng bí danh bảng nữa.

**Nhánh tắt cờ trong `process_pending`:** giữ như C-FIX3-THAP. #b `skipped` → mục của nó tự đóng → #a hết được che → ra mục mới ngay trong cùng `blocking()`.

## Các lỗi phát hiện khi rà (quy tắc 7, 3 lượt agent)

| Mức | Lỗi | Xử lý |
|---|---|---|
| CAO (có từ trước) | Lần lỗi chưa ai gọi `blocking()` mà lần sửa sau rà đạt → không giữ. Đã ghi "Để lại" trong `docs/RA_CLOUD_M71_2026-10-21.md`; test cũ `test_failed_review_older_than_a_good_review_does_not_hold` khóa đúng lỗi này | Sửa; test đổi thành `…_still_holds` |
| VỪA | Rà lại ở kịch bản a/b/c ném "không còn trong sổ" | Sửa |
| VỪA | Lần scene lỗi đã được người Bỏ qua vẫn giữ lại motion khi tắt cờ (bản vá riêng đầu tiên) | Thiết kế mới không giữ |
| VỪA | Lần lỗi thứ 2 cùng lời → mục hiện lại ngay sau Bỏ qua; Rà lại chỉ rà một phần | Một mục mỗi shot, gắn lại |
| VỪA | Dữ liệu cũ có 2 mục mở: Rà lại mục sau → Rà lại mục trước báo lỗi sai | Mục đã Rà lại / ✓ Đã sửa (`resolved`) không cản lần rà lại khác |
| VỪA | "✓ Đã sửa" trên mục rà lỗi đóng `resolved` → che mọi lần lỗi → cổng mở khi chưa ai rà (vòng nền không tự rà lại `failed`) | `close(…, "resolved")` của mục rà lỗi = Rà lại; lần lỗi không còn trong sổ → đóng như cũ |
| THẤP | Gắn lại có thể kéo `event_id` lùi → mục lật e4↔e5 một nhịp | `event_id = MAX(event_id, lần mới)` |

- Ghi nhận, không sửa (THẤP): người đang đọc lời lỗi cũ, nhịp nền gắn lại lời mới, người bấm Bỏ qua → chấp nhận cả lần mới chưa đọc. Đây là chủ ý "Bỏ qua phủ cả shot".

## ⚠️ Cần phiên chính kiểm trước khi gộp (dữ liệu thật)
- Lần `failed` / `code_only` hết tiền cũ (trong `KEEP_DAYS`) chưa từng có mục che sẽ bật mục ĐỎ ở lần `blocking()` kế tiếp. Đúng ý: các thay đổi đó chưa ai rà.
- Hệ quả: autopilot giữ các shot đó; người phải Rà lại (tốn Claude) hoặc Bỏ qua.
- Đếm trước, chỉ đọc, trên `manifest.sqlite` của máy chính (bản trong repo không có dòng `change_events`):
  ```sql
  SELECT project_id, scene_id, COUNT(*) FROM change_events e
  WHERE (state='failed' OR (state='code_only' AND note LIKE 'quota:%'))
    AND NOT EXISTS (SELECT 1 FROM change_findings f WHERE f.source='review_fail' AND f.scene_id=e.scene_id AND f.event_id>=e.id
                    AND substr(f.at,1,19)>=substr(COALESCE(e.reviewed_at,''),1,19)
                    AND (f.status='open' OR COALESCE(f.resolved_by,'')<>'change_review'))
  GROUP BY 1, 2;
  ```
- Còn lại, có từ trước: lần lỗi bị `KEEP_DAYS` xóa trong khi mục còn mở → mục chỉ đóng được bằng Bỏ qua.

## Việc phụ
- `tests/test_v31_m71_fix.py`: dùng `tmp_path` thay `mkdtemp` (không còn rác thư mục tạm).
- `tests/test_v31_m63_gen_auth.py`: mock `_usd_of_jobs` ghi lại TỪNG lần gọi (`seen == [[1], [2]]`), không vỡ khi gọi với `ids` rỗng.

## Test
- Test mới / đổi trong `tests/test_change_review.py`: 9.
  - ĐỎ trên code trước sửa: 4 test của bản `_COVERED` đỏ trên C-FIX3-THAP; 3 test của bản gắn lại đỏ trên eb50a0ea; test ✓ Đã sửa đỏ trên 03ddd1c9.
  - Test "gắn lại rồi lần mới rà xong → mục mới cho lần cũ" là test chặn hồi quy.
- Test liên quan (`test_change_review`, `test_change_review_frames`): 70 xanh.
  - Test "Bỏ qua scene rồi tắt cờ" là test chặn hồi quy cho bản vá riêng đầu tiên.
- Full suite (cloud 3.13, `-m "not slow" -n auto`) trên 151653a9: **7100 passed**. 25 đỏ đều là golden cần native Python 3.14 (nền).
