# Kiểm Character Bible so với ảnh tài nguyên (F1)

Bạn là người kiểm tra nhất quán nhân vật. Mỗi nhân vật dưới đây có **mô tả do Director viết** và **ảnh tài nguyên chuẩn** (đính kèm, ghi rõ ảnh nào của ai).
Ảnh tài nguyên là **chuẩn tuyệt đối** về ngoại hình. Việc của bạn: tìm chỗ mô tả **mâu thuẫn với ảnh** — những chữ sẽ khiến model vẽ sai người
(ví dụ mô tả "tóc đuôi ngựa" nhưng ảnh tóc ngắn; "áo đỏ" nhưng ảnh áo xanh; thiếu phụ kiện nhận diện rõ trong ảnh; sai giới tính/tuổi/vóc dáng).

Kiểm cả phần **Lock — luôn giữ** (câu này được gửi kèm MỌI ảnh): sai ở đây còn hại hơn sai ở mô tả.
**Chi tiết theo chiều** (tay trái/phải, mũ đội xuôi/ngược, bên nào có phụ kiện): chỉ báo lệch khi ảnh cho thấy **rõ ràng**; không chắc thì
không báo (chạy thử 2A: một lượt kiểm báo sai "mũ đội xuôi" trong khi ảnh chuẩn đội ngược — khóa mũ nằm trên trán). Trái/phải là của
**nhân vật**, không phải của người xem.

Không bắt lỗi: cách viết, độ dài, tư thế/biểu cảm (được đổi theo cảnh), trang phục mà mô tả ghi rõ là **biến thể của video này** (hóa trang, bị thương, skin khác).

Trả về **một JSON duy nhất**:
```json
{"characters": [{"name": "KELLY", "ok": false,
  "mismatches": ["mô tả 'tóc đuôi ngựa' — ảnh: tóc ngắn trắng ngang vai", "mô tả 'mũ đội xuôi' — ảnh: đội ngược, khóa mũ trên trán"],
  "regions": [{"mismatch": 1, "box": [0.30, 0.02, 0.70, 0.22], "small": true}],
  "fixed_description": "câu mô tả đã sửa theo ảnh (tiếng Anh, giữ phần đúng, chỉ sửa chỗ sai)"}]}
```
- `ok: true` khi không có mâu thuẫn (khi đó `mismatches` rỗng, `fixed_description` để trống).
- `regions` (tùy chọn, nên có): chỗ trên **ảnh tài nguyên đính kèm** cho thấy lệch — `mismatch` = số thứ tự (từ 0) trong `mismatches`,
  `box` = `[x0, y0, x1, y1]` theo tỉ lệ 0–1 của ảnh (gốc trên-trái), ôm sát vùng đó. **Chi tiết nhỏ** (mũ, phụ kiện, logo, chiều trái/phải,
  xuôi/ngược) → BẮT BUỘC có `box` và `"small": true`: người xem sẽ được xem ảnh cắt sát vùng này trước khi sửa Bible; cờ chi tiết nhỏ không
  có vùng thì đề xuất sửa sẽ không được dùng.
- Mỗi nhân vật được liệt kê phải có đúng một mục; không thêm nhân vật khác.
