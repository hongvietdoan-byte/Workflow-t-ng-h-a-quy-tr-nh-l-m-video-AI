# Phân shot (dự án chia shot — kế hoạch v3)

Dự án này sản xuất **theo shot**, không theo cảnh: mỗi cảnh kịch bản phải được chia thành nhiều shot ngắn, mỗi shot = 1 ảnh khung đầu + 1 clip video. Ngoài các trường của cảnh như hướng dẫn ở trên, **mỗi cảnh trong `scenes` phải có thêm `shots`** (danh sách theo thứ tự trên phim).

## Cách chia
- Đọc từng beat của cảnh (muốn gì – cản trở – bước ngoặt), mỗi thay đổi hành động, mỗi câu thoại, mỗi phản ứng quan trọng → một shot. Dùng ngữ pháp dựng Free Fire và phong cách của dự án ở phần kiến thức (số liệu là **khoảng tham khảo**, không phải con số cố định).
- **Nhịp do kịch bản quyết định**: shot hành động/phản ứng/chèn ngắn; shot thoại dài bằng thời gian nói câu đó (~3,5 âm tiết/giây + 0,4s); thiết lập, kết, money shot được dài hơn. Tổng thời lượng các shot nên khớp thời lượng kịch bản yêu cầu (nếu có ghi).
- Mở video bằng **hook**; kết bằng **ending** (tạo dáng, nhìn máy quay, câu chốt). Sau câu thoại/hành động quan trọng nên có **reaction**. Đổi cỡ cảnh có lý do; tránh 4 shot liền cùng cỡ.
- Thoại: **mỗi câu nằm trọn trong một shot**; không cắt ngang câu. Một shot có thể chứa 0, 1 hoặc vài câu ngắn liền nhau của cùng cảnh.
- **Không có khớp môi (BẮT BUỘC)**: giọng tiếng Việt được lồng sau, miệng nhân vật trong video không nói đúng câu đó. Shot có `dialogue` **KHÔNG được** là `ECU`/`CU`/`MCU` mà người nói có trong `characters` và nhìn thấy mặt (angle `eye`/`low`/`high`/`dutch`). Thay bằng: `MS`/`WS`; góc `ots` (qua vai người nghe, người nói ở trung cảnh); người nói quay nghiêng/quay lưng/đang hành động; hoặc đặt câu thoại lên **shot phản ứng của người nghe** (người nói ngoài khung — vẫn ghi `speaker` là người nói nhưng không đưa họ vào `characters`). Cận mặt người nói chỉ dùng cho khoảnh khắc **im lặng** (nước mắt rơi, sững người) — tách thành shot riêng không thoại.
- **Kịch bản ghi rõ góc máy thì giữ đúng**: "GÓC CAMERA SAU VAI X" / "qua vai X" → `angle: "ots"`, X có trong `characters` (vai/lưng mờ ở tiền cảnh); "CẬN CẢNH" → `CU` (không thoại, xem luật trên); "CHÍNH DIỆN" → nhân vật nhìn về máy; "TOÀN CẢNH" → `WS`. Chỉ đổi khi luật khớp môi buộc phải đổi — khi đó đổi cỡ cảnh, giữ tinh thần góc máy.
- **Chữ trên màn hình không phải thoại**: dòng "HỆ THỐNG: …", thông báo game, chữ kết/tiêu đề → ghi vào `on_screen_text` của shot (danh sách chuỗi), **không** đưa vào `dialogue`, không đặt người dẫn chuyện (NARRATOR) cho nó. Hình ảnh cũng không vẽ chữ (thêm ở hậu kỳ).
- **Độ dài shot**: shot dưới 2 giây chỉ cho chèn/phản ứng thật nhanh (tối đa khoảng 1/5 số shot) — model video luôn làm clip tối thiểu dài hơn rồi cắt, shot quá ngắn tốn tiền mà không thêm gì; gộp các nhịp nhỏ liền nhau vào một shot.
  - **Không có shot im lặng dưới 1 giây** (trừ `insert` trong pha hành động nhanh). Toàn cảnh `WS`/`EWS` **≥ 1,5 giây** (0,5 giây người xem không kịp đọc 3 người trong khung).
  - Nhịp im lặng ngắn (quay lại, khựng lại, nhìn nhau) **gộp vào đầu/cuối shot thoại kề bên** thay vì tách shot: "Kenta quay lại rồi nói…" là MỘT shot.
  - Không mở mỗi cảnh bằng một shot thiết lập 0,5 giây theo thói quen — chỉ thiết lập khi đổi địa điểm, và đủ dài để đọc.
- Chữ tiêu đề, chữ chương, logo, giao diện game **không** thành shot (làm ở hậu kỳ) — không dùng cỡ `GRAPHIC`.
- Gameplay kiểu trong game: dùng `GAME_TPS` (camera sau lưng nhân vật, cao hơn vai) với `angle: "high"`. `angle` **chỉ** nhận giá trị trong danh sách ở dưới — không tự đặt "behind", "tps", "back"… (một lần sai trường này là một lần hỏi lại trả tiền cả bản).
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
 "on_screen_text": ["chữ hiện trên màn hình (thông báo hệ thống, chữ kết) — không đọc thành tiếng; bỏ khi không có"],
 "continuous_with_next": false, "hero": false}
```
- `duration_s` từ 0,5 đến 15 giây. Shot ngắn hơn thời lượng tối thiểu của model video sẽ được gen dài hơn rồi cắt — cứ đặt đúng độ dài phim cần.
- `hero: true` cho 1–3 shot then chốt của cả video (cao trào, cú twist) — được dùng model video tốt nhất.
- Giữ nguyên văn mọi câu thoại của kịch bản, đúng người nói, đúng thứ tự; không thêm câu mới. (Chỉ khi khối "Thời lượng bắt buộc" ghi **được phép bỏ bớt câu thoại** thì mới được bỏ câu — vẫn không thêm, không sửa chữ câu giữ lại.)
- **Khi được phép bỏ câu thoại — thứ tự cắt khi thừa thời lượng**: (1) gộp/bỏ shot im lặng ngắn và shot thiết lập; (2) rút shot phản ứng/chèn; (3) chỉ khi vẫn thừa mới bỏ câu thoại. Câu được bỏ phải là câu **không ai đáp lại** và hình ảnh đã nói thay. **Không bỏ** câu mà câu kế tiếp đáp lại (cặp hỏi–đáp, lời xin–lời từ chối: bỏ "Kelly, nghe anh giải thích…" thì "Không cần." thành câu hụt; muốn bỏ thì bỏ cả cặp). **Không bỏ** câu gieo manh mối cho twist/kết, câu thể hiện nhân vật đã cố làm gì (vd cố giải thích — đó là cái khiến cú twist đau). Đọc lại đoạn thoại còn lại như người xem: mỗi câu vẫn có lý do để được nói ra.
- Các trường của cảnh (`location`, `time`, `mood`, `lighting`, `sequence`, `emotional_intent`, `beat`…) vẫn điền như cũ; `image_prompt`/`shot` của cảnh có thể mô tả chung cảnh.
