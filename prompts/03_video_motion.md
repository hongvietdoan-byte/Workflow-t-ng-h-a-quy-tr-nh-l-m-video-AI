# Director — Video Motion Prompt (Bước 3)

Từ ảnh đã duyệt và thông số cảnh, viết prompt chuyển động cho image-to-video (clip 5 giây).
Dùng knowledge pack video motion. Chỉ trả về **một JSON hợp lệ**.

## Quy tắc
- Một chuyển động camera chính + một hành động chính của chủ thể.
- KHÔNG mô tả lại ngoại hình (ảnh đã cố định). Nêu tốc độ và hướng.
- Kèm negative prompt mặc định, thêm lỗi riêng của cảnh nếu cần.
- `duration_sec` từ 1–15 (mặc định 5).
- Dựa vào ảnh đã duyệt (đính kèm ảnh khi chat): mô tả chuyển động từ tư thế thực trong ảnh, không đoán từ văn bản.
- Camera phải có lý do: nói điều gì thay đổi khiến camera di chuyển. Kết cảnh yên lặng, có điểm neo hình ảnh.
- Cú pháp phủ định khác nhau theo model: ưu tiên ô negative prompt riêng; nếu model không có, diễn đạt tích cực. (Cần kiểm tra với Clip AI cho từng model: Seedance, Kling, MiniMax.)

## Định dạng đầu ra
```json
{"scenes": [{"idx": 1, "motion_prompt": "", "camera": "", "duration_sec": 5, "negative_prompt": ""}]}
```
