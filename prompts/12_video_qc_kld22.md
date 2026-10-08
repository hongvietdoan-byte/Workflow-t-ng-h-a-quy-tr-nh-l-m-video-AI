## Bổ sung cách viết `issues` — bài học #22 Khủng Long Đỏ (cờ `kld_lessons_prompts`; độ tin: 1 dự án)
- Trong câu sửa, tả **trạng thái đúng** cần thấy ("KELLY wears the red dinosaur hoodie"), không nhắc lại chữ của thứ sai ("yellow
  tracksuit"). Lý do: `issues` đi thẳng vào prompt lần gen lại — chữ của lỗi nằm trong prompt thì model dễ vẽ lại đúng thứ đó (#22).
- Clip đi đường **chỉ-ảnh-tham-chiếu** (không có "Ảnh khung đầu đã duyệt" đính kèm) mà lỗi chỉ là mặt mịn / kiểu vẽ lệch (`look_drift`):
  vẫn chấm `identity` theo mắt thấy, nhưng ghi vào `issues` thêm câu "model property — regenerating with the same route will not fix it".
  Lý do: ở #22 mặt mịn xuất hiện ở mọi clip ref-only (×0,12–0,39); gen lại cùng đường ra bản tệ hơn (0,81 → 0,72, mất 2,76 USD).
