# Free Fire gameplay thật trông thế nào — tư liệu tham khảo cho Đạo diễn và prompt

> **Là gì:** tư liệu để hiểu hình ảnh in-game Free Fire, dùng khi biên đạo kịch bản và viết prompt ảnh/video — **không** phải kho cảnh để
> ghép vào phim. Nguồn: *Free Fire In-Game Visual Replication Plan v1.0* (26/09/2026, nội bộ) + quan sát trực tiếp 2 tấm ghép khung hình
> trong tài liệu đó (1 video có giao diện game, 1 video giao diện tối giản). **Giới hạn:** hai video chỉ có **1 nhân vật, 1 địa điểm
> (nhà kho quân sự), khung ngang 16:9** — đừng coi bộ đồ vàng hay nhà kho tối là "chuẩn Free Fire". Đây là mô tả hình ảnh để tái tạo, không
> phải nội bộ engine. Có tư liệu mới thì bổ sung mục 2.

## 1. Ý chính (vì sao cần tài liệu này)
AI không thiếu khái niệm "game bắn súng". Khi chỉ tả bằng chữ, model **tự suy** sang game bắn súng tả thực kiểu PUBG / Call of Duty; chữ
*cinematic / photorealistic* trong prompt kéo mạnh thêm về phía đó. Vì vậy: **hình tham chiếu in-game là bằng chứng, chữ chỉ tả cảnh**, và
prompt không được chứa từ đẩy về tả thực. Dấu hiệu đang trượt khỏi Free Fire: ảnh "thật" hơn, vân bề mặt dày hơn, nền bị mờ nhòe kiểu ống
kính, đồ quân sự tả thực, người có tỉ lệ quá giống người thật.

## 2. Quan sát từ khung hình thật (23 khung, cùng nhà kho)
- **Máy gameplay (`GAME_TPS`)**: sau lưng nhân vật, cao hơn vai một chút, nhìn hơi chúc xuống; nhân vật thấy **trọn người**, cao khoảng
  **1/4–1/3 khung**, đứng giữa hoặc hơi dưới giữa khung; nền **nét toàn bộ** (không mờ hậu cảnh). Khung giao diện tối giản còn có góc
  trước mặt nhân vật (đứng cầm súng, nhìn về máy).
- **Nhân vật**: tỉ lệ game cách điệu, dáng rõ (silhouette đọc được từ xa), trang phục màu bão hòa nổi hẳn trên nền; vũ khí có màu/skin
  riêng (tím) đeo sau lưng hoặc cầm tay; ba lô, mũ là phụ kiện.
- **Bối cảnh**: nhà kho khung thép mái vòm, trong tối nhưng vẫn đọc được chi tiết; cửa lớn mở ra ngoài sáng rực (trời xanh, cây, container,
  xe tải); sàn bê tông có **vạch sơn vàng**, thùng gỗ xếp chồng. Vật thể hình khối đơn giản, vân bề mặt vừa phải.
- **Ánh sáng, màu**: ánh sáng kiểu gameplay (rõ, ít tương phản kịch tính), bóng cứng ở mép cửa; nền xám/ô liu trầm, nhân vật và hiệu ứng
  màu tươi; **không** chỉnh màu kiểu phim, không hạt phim.
- **Giao diện (HUD)**: bản đồ nhỏ góc trên trái; bộ đếm người còn sống, giờ trên phải; ô vũ khí + số đạn bên phải ("Thay đạn" khi nạp); nút
  bắn, ngồi, nằm, nhảy bên phải; nút túi, hộp cứu thương bên trái; thanh EP/HP dưới giữa; nhãn "18+" góc dưới trái. Giao diện che nhiều chi
  tiết — khung **không giao diện** mới là bằng chứng tốt cho nhân vật, máy và bối cảnh.
- **Hiệu ứng**: quả cầu sáng cam (hiệu ứng kỹ năng/vật phẩm) — hiệu ứng in-game sáng, bão hòa, viền rõ, không khói bụi tả thực.

## 3. Dùng thế nào khi biên đạo và viết prompt
Thứ tự ưu tiên khi các ý kéo nhau: **câu chuyện/cảm xúc (Đạo diễn)** > **look của dự án** (ảnh tài nguyên là chuẩn tuyệt đối) > tư liệu
này. Tư liệu này giúp chọn chữ và bố cục **đúng chất game**, không bắt mọi shot phải giống ảnh chụp gameplay.
- **Chọn máy theo loại video, không mặc định.** Video kỹ năng/mẹo (phong cách `INGAME`: 79% shot là `GAME_TPS`) → máy gameplay như mục 2,
  giao diện thêm ở hậu kỳ. Phim ngắn kịch tính (Kelly/Kenta) → vẫn dùng cận, trung, qua vai cho cảm xúc; phần "chất game" nằm ở **render,
  tỉ lệ, chất liệu, màu và bối cảnh**, không ở góc máy. Shot `GAME_TPS` trong phim kịch tính là lựa chọn có lý do (người xem nhận ra "đây là
  trận đấu"), ghi trong `why`.
- **Tả bối cảnh bằng danh từ cụ thể của game**: nhà kho khung thép, thùng gỗ, container, vạch sơn vàng trên sàn, xe tải, cửa lớn mở ra
  ngoài sáng — thay cho "chiến trường điện ảnh", "military base" chung chung (chữ chung → model lấp bằng hình PUBG).
- **Giao diện game (HUD) không bao giờ bắt model ảnh/video vẽ** — thêm ở hậu kỳ (thẻ chữ, phụ đề, lớp phủ). Model vẽ HUD luôn sai.
- **Look `FF_INGAME` — từ cấm trong `image_prompt` và câu chuyển động** (kéo về tả thực): *cinematic* (như một phong cách), *photorealistic,
  hyper-realistic, realistic skin, film still, movie still, bokeh, shallow depth of field, anamorphic, film grain, color grading, 8K, Unreal
  Engine, AAA, gritty realism*. Muốn đẹp thì tả **cái có trong khung** (ai, đâu, ánh sáng từ đâu, vật gì) + "Free Fire in-game 3D render,
  stylized proportions, moderate texture detail, clear gameplay lighting, everything in focus". Code tự gỡ các từ này khỏi `image_prompt`
  và câu chuyển động trước khi gửi, ghi lại đã gỡ gì (`looks.clean_prompt`, 📊 Theo dõi hiệu suất); câu look của dự án thêm vế "không phải
  ảnh phim, không mờ hậu cảnh, không phải game bắn súng tả thực". Danh sách tránh cho video cũng vào `negative_prompt`, nhưng ClipAI mặc
  định **không gửi** negative (chỉ khi `CLIPAI_NEGATIVE=append`) — nên đừng trông vào nó, cứ không viết các từ đó ra.
- "Ngôn ngữ điện ảnh" (cỡ cảnh, góc máy, nhịp dựng) vẫn là việc của Đạo diễn — cấm là cấm **chữ phong cách** trong prompt, không cấm cách
  kể chuyện bằng hình.

## 4. Lỗi hay gặp → cách sửa
| Lỗi | Nguyên nhân | Sửa |
|---|---|---|
| Giống PUBG / game tả thực | prompt chung chung, có chữ cinematic/photoreal, thiếu ảnh in-game | bỏ chữ tả thực; tả vật thể cụ thể; gửi ảnh tài nguyên in-game |
| Nhân vật quá giống người thật | model ưu tiên tả thực | ảnh tham chiếu nhân vật + "stylized mobile-game proportions" |
| Sai bản đồ / bối cảnh lạ | không có ảnh địa điểm | ảnh địa điểm trong kho (`location_asset`) hoặc gói bối cảnh |
| Sai góc máy gameplay | chỉ ghi "third-person" | ghi rõ: sau lưng, cao hơn vai, trọn người, nhân vật 1/4–1/3 khung, nền nét |
| Vân bề mặt quá chi tiết | model tự nâng lên kiểu AAA | "moderate texture detail, simplified geometry" |
| Màu như phim | chỉnh màu phim, mờ hậu cảnh | cấm bokeh/DOF/anamorphic/color grading |
| HUD sai | bắt model vẽ bằng chữ | bỏ khỏi prompt, thêm ở hậu kỳ |

## 5. Chấm độ giống in-game (khi cần đo)
Thang 0–100 của tài liệu gốc: nhận diện game 20 · máy/bố cục 20 · nhân vật 15 · bối cảnh 15 · độ tả thực của render 15 · màu/chất liệu
10 · HUD 5. Dưới 50 hỏng; 65–74 dùng được cho storyboard; 75–84 đạt mục tiêu; 85+ đủ làm ảnh neo phong cách. Là thước đo nội bộ để so
cấu hình (chỉ chữ / + 1 ảnh / + nhiều ảnh), chưa hiệu chỉnh với người chấm.
