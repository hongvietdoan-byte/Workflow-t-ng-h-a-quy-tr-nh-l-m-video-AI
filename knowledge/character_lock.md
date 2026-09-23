# Character Lock và thứ tự rà nhất quán nhân vật (game-character-consistency-designer skill — chắt lọc, dịch)
Dùng cho: Director (điền `lock` cho mỗi nhân vật), QC ảnh, QC video.

## Character Lock — chỉ ghi điều có trong ảnh tham chiếu / kịch bản
- **Bắt buộc giữ (must_keep):** khuôn mặt và tỉ lệ mặt, dáng/màu/độ dài tóc và lọn đặc trưng, độ tuổi, tỉ lệ cơ thể, dấu hiệu nhận diện (sẹo, hình xăm, tai, sừng…); dáng trang phục và các khối màu chính, chất liệu giáp/vải, phụ kiện đặc trưng, vũ khí, vị trí biểu tượng, phong cách render.
- **Được đổi (may_change):** liệt kê rõ — tư thế, biểu cảm, cử chỉ tay, khoảng cách/góc máy, nền, thời tiết, hành động. Trang phục, kiểu tóc, tuổi, vóc dáng, vũ khí KHÔNG phải biến tự do trừ khi kịch bản yêu cầu.
- **Cấm lệch (forbidden):** những lỗi dễ xảy ra nhất với nhân vật này — đổi màu tóc, sẹo bị lật bên, mất phụ kiện, vũ khí bị vẽ lại, đổi bảng màu trang phục, trẻ/già đi, khác cấu trúc mặt, thừa chi, trượt từ phong cách game sang ảnh thật.

## Thứ tự prompt ổn định cho cả loạt
1 loại ảnh + tỉ lệ khung → 2 danh tính nhân vật + ảnh tham chiếu → 3 các nét Character Lock bất biến → 4 tư thế/biểu cảm/máy/cảnh riêng của khung này → 5 phong cách render, bảng màu chung → 6 lệch cấm, không chữ/logo giả/watermark.

## Thứ tự rà (QC)
1 **Danh tính:** mặt, dáng tóc, tuổi, tỉ lệ cơ thể còn là người đó? 2 **Bóng dáng:** dáng trang phục, phụ kiện lớn, đạo cụ nhận ra được ở cỡ thumbnail? 3 **Khối màu:** màu chính đúng chỗ? 4 **Chi tiết đặc trưng:** dấu hiệu, trang sức, chi tiết vũ khí đúng vị trí? 5 **Phong cách:** nét, chất liệu, mật độ render, ánh sáng giống ảnh mốc? 6 **Giải phẫu:** tay, chân, cấu trúc trang phục, chỗ cầm đạo cụ hợp lý? 7 **Yêu cầu:** đúng tư thế/biểu cảm/góc máy/cảnh đã đặt?
Lệch danh tính nghiêm trọng = khung HỎNG dù bố cục đẹp.
