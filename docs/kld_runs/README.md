# Khủng Long Đỏ (#22) — so sánh các lượt chạy

Mỗi lượt có ảnh chụp đầy đủ (spec shot, prompt ảnh, motion prompt, model, số lượt gen, thiết lập dựng) ở `<nhãn>.json` + tóm tắt `<nhãn>.md`,
tạo bằng `py tools/project_snapshot.py <db> 22 <nhãn> docs/kld_runs --git <commit>`. Video giao ở `D:\AI-Video-Output\2026-10-07_du-an-22\`.

| | Bản thử 1 | Bản thử 2 | Chất lượng cao |
|---|---|---|---|
| Video | `KhungLongDo_ban_thu_re_2026-10-07.mp4` (51,6 s) | `KhungLongDo_ban_thu_re_v2.mp4` (52,6 s) | _chưa làm_ |
| Ảnh chụp | `ban_thu_1` (CSDL `data/backup/manifest.before_kld_round3_2026-10-07.sqlite`) | `ban_thu_2` | `chat_luong_cao` |
| Model ảnh | Seedream 5 Pro (mặc định) | GPT Image 2.5 Sunburst | GPT Image 2.5 Sunburst |
| Model video | Seedance 2.0 Fast 720p (thử rẻ); thoại Seedance 2.5 | như bản 1 | Seedance 2.5 |
| Nền phòng tầng 2 | vẽ thêm cửa mở ra ngoài trời (sai) | đúng render 3D; vào từ mép khung (nhà FF không có cánh cửa) | |
| Bộ đồ trên giường | khủng long sai mẫu (không gửi ảnh trang phục) | đúng mẫu (gửi ảnh Kho cho shot không người) | |
| Thoại | "…xịn vậy! Hô biến!" — cứng | "Ủa, đồ này ở đâu ra mà nhìn hay zậy? Để mặc thử coi!" / "Ê, mặc đồ đôi mà hổng rủ tui hả?" | |
| Khớp môi (tương quan) | shot 3: 0,14 · shot 5: 0,45 | 0,03 · 0,44 (giọng ở giây 1,0) | |
| Khẩu trang KL | Kelly kéo xuống cằm | luôn đeo kín | |
| Kelly | kém xinh (Seedream, cận MCU) | đẹp hơn; tóc lẫn bạc từ ảnh trang phục → ghi rõ tóc | |
| Kelly sau biến hình (shot 6) | cười | đứng yên (người dùng chê) → v3: xoay, búng mũ, chữ V | |
| Nối 3 clip nhảy | lệch động tác + trang phục ở 28/39 s | nối từ khung cuối clip trước — liền tư thế/đồ | |
| Tháp đồng hồ đoạn nhảy | | đổi dần qua 3 clip, không giống map 3D (người dùng) | |
| Máy quay đoạn nhảy | đứng yên | đẩy vào / lượn / hạ thấp | |
| Nhạc | chỉ nhạc gốc từ 17 s | ClipAI cảnh 1 (vào 1,8 s) + nhạc gốc từ 18,08 s | |
| Hậu kỳ | chớp trắng + rung ở 2 cú hô biến | + nhún theo nhịp đoạn nhảy (85 nhịp) | rung chỉ khi đã vào nhạc nhảy |
| Chi (ước tính sổ chi) | ≈ 22,5 USD lũy kế | +≈ 12 USD (đợt thử 34,53/74) | |
