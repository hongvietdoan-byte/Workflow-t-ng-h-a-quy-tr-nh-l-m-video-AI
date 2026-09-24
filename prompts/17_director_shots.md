# Phân shot (dự án chia shot — kế hoạch v3)

Dự án này sản xuất **theo shot**, không theo cảnh: mỗi cảnh kịch bản phải được chia thành nhiều shot ngắn, mỗi shot = 1 ảnh khung đầu + 1 clip video. Ngoài các trường của cảnh như hướng dẫn ở trên, **mỗi cảnh trong `scenes` phải có thêm `shots`** (danh sách theo thứ tự trên phim).

## Cách chia
- Đọc từng beat của cảnh (muốn gì – cản trở – bước ngoặt), mỗi thay đổi hành động, mỗi câu thoại, mỗi phản ứng quan trọng → một shot. Dùng ngữ pháp dựng Free Fire và phong cách của dự án ở phần kiến thức (số liệu là **khoảng tham khảo**, không phải con số cố định).
- **Nhịp do kịch bản quyết định**: shot hành động/phản ứng/chèn ngắn; shot thoại dài bằng thời gian nói câu đó (~3,5 âm tiết/giây + 0,4s); thiết lập, kết, money shot được dài hơn. Tổng thời lượng các shot nên khớp thời lượng kịch bản yêu cầu (nếu có ghi).
- Mở video bằng **hook**; kết bằng **ending** (tạo dáng, nhìn máy quay, câu chốt). Sau câu thoại/hành động quan trọng nên có **reaction**. Đổi cỡ cảnh có lý do; tránh 4 shot liền cùng cỡ.
- Thoại: **mỗi câu nằm trọn trong một shot**; không cắt ngang câu. Một shot có thể chứa 0, 1 hoặc vài câu ngắn liền nhau của cùng cảnh.
- **Không có khớp môi**: giọng tiếng Việt được lồng sau, miệng nhân vật trong video không nói đúng câu đó. Vì vậy shot có thoại **tránh cận mặt người đang nói** (`ECU`/`CU`/`MCU` nhìn thấy mặt người nói) trừ khi cảm xúc câu đó thật sự cần. Ưu tiên: `MS`/`WS`; góc `ots` từ sau lưng người nói; người nói quay nghiêng/quay lưng/đang hành động; hoặc đặt câu thoại lên **shot phản ứng của người nghe** (người nói ngoài khung — vẫn ghi `speaker` là người nói, nhưng không đưa họ vào `characters` của shot đó).
- Chữ tiêu đề, chữ chương, logo, giao diện game **không** thành shot (làm ở hậu kỳ) — không dùng cỡ `GRAPHIC`.
- Gameplay kiểu trong game: dùng `GAME_TPS` (camera sau lưng nhân vật, cao hơn vai).
- Các shot liền mạch cùng địa điểm/thời điểm thuộc cùng `sequence` của cảnh; shot nào **nối liền hình với shot kế tiếp** (cùng hành động kéo dài qua điểm cắt) thì `continuous_with_next: true`.

## Trường của mỗi shot
```json
{"size": "ECU|CU|MCU|MS|WS|EWS|GAME_TPS", "angle": "eye|low|high|overhead|dutch|ots|pov",
 "camera_move": "static|push_in|pull_out|pan|tilt|track|orbit|handheld|crane|whip|zoom",
 "role": "hook|setup|action|reaction|insert|dialogue|transition|ending",
 "duration_s": 2.5,
 "action": "tiếng Việt, 1 hành động chính của shot",
 "start_frame": "tiếng Anh: ai ở đâu trong khung lúc bắt đầu shot (trái/giữa/phải, tiền/hậu cảnh, hướng mặt, tư thế)",
 "end_state": "tiếng Anh, chỉ khi shot đổi trạng thái rõ (vị trí/tư thế cuối shot); không thì bỏ",
 "image_prompt": "tiếng Anh: KHUNG ĐẦU của shot — cỡ cảnh, góc, nhân vật, bối cảnh, ánh sáng, theo khung hình dự án",
 "characters": ["TÊN trong Character Bible có mặt trong khung"],
 "dialogue": [{"speaker": "TÊN", "text": "câu thoại nguyên văn tiếng Việt"}],
 "continuous_with_next": false, "hero": false}
```
- `duration_s` từ 0,5 đến 15 giây. Shot ngắn hơn thời lượng tối thiểu của model video sẽ được gen dài hơn rồi cắt — cứ đặt đúng độ dài phim cần.
- `hero: true` cho 1–3 shot then chốt của cả video (cao trào, cú twist) — được dùng model video tốt nhất.
- Giữ nguyên văn mọi câu thoại của kịch bản, đúng người nói, đúng thứ tự; không thêm câu mới.
- Các trường của cảnh (`location`, `time`, `mood`, `lighting`, `sequence`, `emotional_intent`, `beat`…) vẫn điền như cũ; `image_prompt`/`shot` của cảnh có thể mô tả chung cảnh.
