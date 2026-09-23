# Character Lock từ ảnh (Bước 1 · Character Bible)

Đính kèm ảnh tham chiếu của MỘT nhân vật (và ảnh trang phục nếu có), cùng mô tả hiện có. Viết Character Lock theo knowledge/character_lock.md, tiếng Anh ngắn gọn, CHỈ những gì thấy trong ảnh hoặc có trong mô tả:
- `must_keep`: nét bắt buộc giữ (mặt, tóc, khối màu trang phục, phụ kiện, vũ khí/đạo cụ đặc trưng, vóc dáng, phong cách render).
- `may_change`: các biến được phép đổi giữa các cảnh (tư thế, biểu cảm, góc máy, nền, hành động…).
- `forbidden`: 3–6 kiểu lệch dễ xảy ra nhất với nhân vật này (ví dụ "hair turning brown", "missing gold earring", "outfit swapped with other characters").
Chỉ trả về **một JSON hợp lệ**:
```json
{"must_keep": "", "may_change": "", "forbidden": ""}
```
