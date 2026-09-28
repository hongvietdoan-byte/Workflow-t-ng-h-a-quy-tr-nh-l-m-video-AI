# Knowledge pack — Video motion prompt (image-to-video, v0.1, bản khởi đầu)

> Cần chuyên gia miền duyệt và đối chiếu hướng dẫn chính thức của Kling trước khi khóa version (PLAN.md Mục 3.6).

## Nguyên tắc
1. **Một clip 5 giây = một chuyển động camera chính + một hành động chính của chủ thể.** Đừng nhồi nhiều hành động.
2. Ảnh đã cố định ngoại hình → prompt chỉ mô tả **chuyển động**, không mô tả lại ngoại hình.
3. Viết cụ thể, có tốc độ và hướng: "slow push-in", "camera orbits 15° clockwise".
4. Luôn kèm negative prompt cho lỗi thường gặp (biến dạng tay/mặt, nháy hình, chữ/logo lạ).
5. Giữ nhất quán: nhân vật không đổi trang phục, không xuất hiện thêm người.

## Từ vựng camera
| Chuyển động | Mô tả |
|---|---|
| push-in / pull-out (dolly) | Tiến sát / lùi xa chủ thể |
| pan left/right | Xoay ngang tại chỗ |
| tilt up/down | Xoay dọc tại chỗ |
| orbit / arc | Di chuyển vòng quanh chủ thể |
| tracking / follow | Đi theo chủ thể |
| crane up/down | Nâng/hạ máy |
| handheld | Rung nhẹ, cảm giác đời thực |
| static | Máy cố định, chỉ chủ thể chuyển động |

## Tốc độ & nhịp
slow / medium / fast; ease-in / ease-out; "subtle" cho chuyển động nhỏ.

## Khung prompt gợi ý
`[camera move + tốc độ], [hành động chính của chủ thể], [chuyển động môi trường: gió, sương, lửa], [nhịp/cảm xúc]`

Ví dụ: "Slow push-in, Lyra turns her head toward the sound, mist drifts left to right, tense and quiet."

## Negative prompt mặc định
`deformed hands, extra fingers, distorted face, flickering, text, watermark, sudden cuts, extra people, outfit change`

## Theo thể loại (tham khảo, không mặc định — chọn theo ý đồ cảnh; mở rộng dần)
- **Hành động:** camera tracking nhanh, handheld, cắt nhịp gấp; hành động lớn của chủ thể.
- **Kinh dị/u ám:** static hoặc slow push-in, ánh sáng nhấp nháy, sương, chủ thể ít cử động.
- **Drama/đối thoại:** medium/close-up, rack focus nhẹ, chuyển động rất nhỏ.
- **Hùng vĩ/trailer game:** low angle, crane up, orbit chậm, cờ/áo choàng bay.
