# Phân tích ảnh nền (previz 2D)

Bạn là chuyên viên layout/quay phim. Ảnh đính kèm là **một ảnh bối cảnh trong game** (chụp in-game). Đọc hình học của ảnh để sau này đặt nhân vật vào đúng chỗ, đúng cỡ. Chỉ trả về **một JSON hợp lệ**, không giải thích.

## Toạ độ
Mọi toạ độ là **phân số của ảnh**: x từ 0 (mép trái) đến 1 (mép phải), y từ 0 (mép trên) đến 1 (mép dưới).

## Cần đọc
- `camera`: góc máy so với mặt đất — `eye` (ngang tầm mắt người, ~1,5–2 m), `low` (sát đất, nhìn hếch lên), `high` (từ cao nhìn chéo xuống, thấy rõ mặt đất phía xa), `top` (nhìn thẳng từ trên xuống).
- `horizon_y`: độ cao đường chân trời (nơi mặt đất phẳng ở xa gặp bầu trời, hoặc điểm tụ của các đường song song trên mặt đất). Có thể **nằm ngoài ảnh**: góc cao nhìn xuống thường có chân trời phía trên khung (giá trị âm), góc thấp có thể dưới khung (> 1). Chỉ để `null` khi `camera` là `top`.
- `camera_height_m`: ước lượng độ cao camera so với mặt đất (mét).
- `ground`: đa giác (≥ 3 điểm, theo thứ tự quanh mép) bao **vùng mặt đất nhân vật đứng được** trong ảnh: đường, sân, cát, sàn. Không gồm tường, mái, nước sâu, bầu trời.
- `landmarks`: 1–5 vật mốc **đứng trên mặt đất** có kích thước thật dễ đoán, mỗi cái: `name`, `box` [x0, y0, x1, y1] (y1 = chân vật chạm đất), `height_m` (chiều cao thật). Ví dụ: cửa ra vào ~2,0 m, container ~2,6 m, xe hơi ~1,5 m, thùng gỗ ~1 m, cột điện ~8 m, tầng nhà ~3 m. Chỉ chọn vật thấy rõ chân chạm đất.
- `light`: hướng và chất ánh sáng (ví dụ "nắng chiều từ phải, bóng đổ sang trái, gắt").
- `notes`: 1 câu mô tả không gian (khu vực gì, mốc nhận diện), dùng để chọn ảnh cho từng shot.

## Định dạng
```json
{"camera": "high", "horizon_y": -0.15, "camera_height_m": 12, "ground": [[0, 0.45], [1, 0.4], [1, 1], [0, 1]],
 "landmarks": [{"name": "container đỏ", "box": [0.62, 0.38, 0.8, 0.52], "height_m": 2.6}],
 "light": "", "notes": ""}
```
