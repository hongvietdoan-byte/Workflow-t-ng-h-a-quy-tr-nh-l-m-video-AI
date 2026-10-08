# Khủng Long Đỏ (#22) — so sánh các lượt chạy

Mỗi lượt có ảnh chụp đầy đủ (spec shot, prompt ảnh, motion prompt, model, số lượt gen, thiết lập dựng) ở `<nhãn>.json` + tóm tắt `<nhãn>.md`,
tạo bằng `py tools/project_snapshot.py <db> 22 <nhãn> docs/kld_runs --git <commit>`. Video giao ở `D:\AI-Video-Output\2026-10-07_du-an-22\`.
Phân tích theo khâu: `docs/TONG_HOP_3_LUOT_KHUNG_LONG_DO.md`; số liệu từng lượt: `THONG_KE_3_LUOT_2026-10-08.md`.

**"Chất lượng cao" là MỘT PHẦN:** chỉ 3 cảnh nhảy (shot 7–9) làm lại bằng Seedance 2.5 720p; shot 6 làm lại bằng Fast (động tác Kelly); shot 1, 2, 4 giữ clip Fast lượt 2; shot 3, 5 giữ clip 2.5 lượt 2.

| | Bản thử 1 | Bản thử 2 | Chất lượng cao (một phần) |
|---|---|---|---|
| Video | `KhungLongDo_ban_thu_re_2026-10-07.mp4` (51,6 s) | `KhungLongDo_ban_thu_re_v2.mp4` (52,6 s) | `FINAL_VIDEO_khung_long_do_2026-10-07.mp4` (52,6 s; bản dựng #34) — người dùng xác nhận **đạt** 08/10 |
| Ảnh chụp | `ban_thu_1` (CSDL `data/backup/manifest.before_kld_round3_2026-10-07.sqlite`) | `ban_thu_2` | `chat_luong_cao` (commit `5839f37`) |
| Model ảnh | Seedream 5 Pro (mặc định) | GPT Image 2.5 Sunburst | GPT Image 2.5 Sunburst (chỉ vẽ lại 3 ảnh cảnh nhảy: 556–558) |
| Model video | Seedance 2.0 Fast 720p (thử rẻ); thoại Seedance 2.5 | như bản 1 | Shot 7–9: Seedance 2.5 720p (568, 569, 561); shot 6: Fast (549); shot 1, 2, 4 Fast + 3, 5 Seedance 2.5 giữ từ bản 2 |
| Nền phòng tầng 2 | vẽ thêm cửa mở ra ngoài trời (sai) | đúng render 3D; vào từ mép khung (nhà FF không có cánh cửa) | giữ bản 2 |
| Chỗ đứng cảnh nhảy | trước nhà lớn phía Đông (`nha_lon_dong`) | như bản 1 | chân cầu thang giữa nhà 3 tầng và tháp (`bac_thang_giua`), nền 3D mới + ảnh toàn cảnh = render đồng trục + câu khóa nền |
| Bộ đồ trên giường | khủng long sai mẫu (không gửi ảnh trang phục) | đúng mẫu (gửi ảnh Kho cho shot không người) | giữ bản 2 |
| Thoại | "…xịn vậy! Hô biến!" — cứng | "Ủa, đồ này ở đâu ra mà nhìn hay zậy? Để mặc thử coi!" / "Ê, mặc đồ đôi mà hổng rủ tui hả?" | giữ bản 2 |
| Khớp môi (tương quan) | shot 3: 0,14 · shot 5: 0,45 | 0,03 · 0,44 (giọng ở giây 1,0) | 0,03 · 0,44 (dùng lại clip 539, 541; người dùng tạm chấp nhận) |
| Khẩu trang KL | Kelly kéo xuống cằm | luôn đeo kín | luôn đeo kín |
| Kelly | kém xinh (Seedream, cận MCU) | đẹp hơn; tóc lẫn bạc từ ảnh trang phục → ghi rõ tóc | giữ ảnh bản 2; tóc một màu trong clip nhảy |
| Mũ Maxim (prompt cảnh nhảy) | "red horned cap" | "red horned cap" | "black cap with small red horns" — **chưa xác nhận** đúng mẫu (tư liệu gốc ghi "mũ đỏ có sừng") |
| Kelly sau biến hình (shot 6) | cười | đứng yên (người dùng chê) | xoay, búng vành mũ, chữ V (clip Fast 549; QC ghi khung cuối là tay chỉnh vành mũ, chưa thấy rõ chữ V) |
| Nối 3 clip nhảy | lệch động tác + trang phục ở 28/39 s | nối từ khung cuối clip trước — liền tư thế/đồ | giữ cách nối; phải hoán đổi dòng job 560 ↔ 569 để nối từ bản người dùng chọn |
| Tháp đồng hồ đoạn nhảy | | đổi dần qua 3 clip, không giống map 3D (người dùng) | giữ đúng chỗ suốt 3 clip (xem 6 khung) |
| Máy quay đoạn nhảy | đứng yên | đẩy vào / lượn / hạ thấp | shot 7 gần tĩnh (bỏ đẩy vào), shot 9 hạ thấp rồi lùi → khung cuối nhiều sân trống, hai người nhỏ |
| Mặt trong clip nhảy (`clip_measure`, độ chi tiết so với khung đầu) | ×0,23–0,31 | ×0,22–0,30 | ×0,12–0,24 — chưa có số đo cho thấy nét hơn |
| QC video trung bình (identity) | 0,72 | 0,87 | 0,86 |
| Nhạc | chỉ nhạc gốc từ 17 s | ClipAI cảnh 1 (vào 1,8 s) + nhạc gốc từ 18,08 s | giữ bản 2 |
| Hậu kỳ | chớp trắng + rung ở 2 cú hô biến | + nhún theo nhịp đoạn nhảy (85 nhịp) | bỏ rung ở cú hô biến (rung chỉ khi đã vào nhạc nhảy); giữ chớp trắng + nhún 85 nhịp |
| Chi (giá bảng, theo thống kê 4A) | 19,06 USD | 11,99 USD | 20,07 USD, trong đó ≈ 10,7 USD ảnh/video không vào phim (gửi nhầm model 3,60; QC tự gen lại 2,76; phép so độ nét 1,33; đổi chỗ đứng sau khi gen 1,80; nút gen chung 1,20) |
| Chi (ước tính sổ chi, ghi lúc làm) | ≈ 22,5 USD lũy kế | +≈ 12 USD (đợt thử 34,53/74) | đợt thử 55,82 / 74,50 USD lúc kết thúc |
