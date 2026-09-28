# 01 — 《夫人又在掉馬甲了》 (AI心動劇場 | AI HeartBeat Drama)

- **URL**: https://www.youtube.com/watch?v=wPwzzQNtgr0
- **Thể loại**: AI short drama 9:16, 爽剧 (giải trí nhanh, plot twist liên tục), toàn tập gộp
- **Độ dài công bố**: 2:03:33 (7413.7s) · khung 360×640 (9:16) — xác nhận qua `video.videoWidth/videoHeight` trong trình duyệt
- **Đoạn đã đo**: (1) 0:00–3:00 (mở đầu, 180s) · (2) 1:14:08–1:15:08 (74:08–75:08, 60s, quanh câu thoại "黎溪下降頭了" — một diễn biến kịch tính giữa phim, chọn vì không có mục lục/chương trên video nên không xác định được đúng điểm "揭mặt" nêu trong tiêu đề; **chỉ đo 1 đoạn giữa phim thay vì 2 như phương pháp đề nghị, vì giới hạn ngân sách lượt công cụ của lượt chạy đầu — ghi nhận thiếu**)
- **Tổng đã đo**: 240s / 7413.7s (~3.2% video)

## Phương pháp
- Đo điểm cắt bằng khác biệt khung hình (grayscale, vùng 72% trên khung — loại bỏ dải phụ đề dưới) tính trực tiếp trong trình duyệt qua `javascript_tool`: vẽ khung `<video>` hiện tại vào canvas 32×41, lấy `getImageData`, so độ sáng trung bình với khung liền trước, lặp lại mỗi ~90ms trong khi video phát ở tốc độ ×2 (muted). **Xác nhận canvas đọc được pixel của `<video>` YouTube ở trang này (không bị tainted)** — khác với lo ngại ban đầu trong đề bài.
- Cắt điểm bằng `core.reference_analysis.cuts_from_diffs` (cổng sang JS, cùng công thức) với ngưỡng đã điều chỉnh theo nghiên cứu DRAMA_DOC trước (`floor=30, factor=5, local_floor=35, local_factor=4`) — ngưỡng mặc định (18/4/25/3) cho ra quá nhiều điểm cắt giả (112 so với 100 trong 180s).
- Nhãn cỡ cảnh/góc/hành động: chỉ xem trực tiếp bằng mắt tại một số mốc chụp được (không chụp được mọi shot — xem "Giới hạn" bên dưới).
- **Âm thanh: không nghe được** — không bật được Web Audio trên iframe YouTube trong phiên này (cùng giới hạn ghi nhận ở nghiên cứu DRAMA_DOC trước, `docs/NGHIEN_CUU_DRAMA_THAM_KHAO_2026-09-28.md`); phụ đề song ngữ (Trung + Anh) đọc được qua hình nên lời thoại vẫn ghi lại được bằng chữ.

## Số đo (2 đoạn, 240s, 130 shot)
| Đoạn | Shot | Độ dài trung vị | Min–Max | <1s | >4s |
|---|---|---|---|---|---|
| Mở đầu 0:00–3:00 | 101 | 1.59s | 0.59–5.94s | 13 (13%) | 2 (2%) |
| Giữa phim 74:08–75:08 | 29 | 1.99s | 0.80–4.40s | 3 (10%) | 1 (3%) |

Nhịp cắt ~29–34 shot/phút ở cả hai đoạn — nhanh, cùng độ lớn với phim tham khảo DRAMA_DOC đã đo trước đó (33 shot/phút, median 1.86s) dù đây là kênh/nội dung khác. **[có thể]**: nhịp cắt nhanh ổn định là đặc trưng chung của thể loại 爽剧/短剧 gộp tập, không riêng một kênh.

## Quan sát trực tiếp (các khung chụp được, do bị quảng cáo giữa video và lỗi làm mới khung khi tua lúc video đang tạm dừng cắt ngang việc lấy mẫu có hệ thống)
- **0:05** — cận (CU) một phụ nữ trẻ đọc quyển sách nhỏ, thoại phụ đề "送给你的高定限量款 / custom-made limited editions for you" — góc ngang mắt, máy tĩnh, ánh sáng ấm trong nhà.
- **~2:45 (1:14:08 lân cận)** — cận (CU) phụ nữ trẻ, mắt đỏ hoe, phụ đề "黎溪下降頭了 / is charmed by Li Xi" — biểu cảm hoảng hốt/đau khổ, nền tối, có vẻ là một tiết lộ/twist về nhân vật khác bị "hạ bùa". **[có thể]**: đây là một trong các cú ngoặt liên hoàn đặc trưng của 爽剧 — thông tin giật gân được thả liên tục qua các đoạn hội thoại ngắn thay vì một cảnh cao trào duy nhất.
- **~2:45 muộn hơn (khung khác cùng khu vực)** — cận (CU) phụ nữ lớn tuổi sang trọng (vòng ngọc trai, trang phục tối màu), phụ đề "是比王家 / They are a more powerful dynasty" — máy tĩnh, ánh sáng ngoài trời/ven đường.

## Kỹ thuật đáng học
1. **Cắt gần như toàn cận/trung cận theo câu thoại, nhịp rất nhanh (median ~1.6–2.0s, tới 29–34 shot/phút)** — mốc 0:00–3:00 và 74:08–75:08. Ý đồ ở đây **[có thể]**: giữ người xem không rời mắt trong định dạng xem lướt trên điện thoại (YouTube/TikTok), tối đa hoá lượng thông tin cảm xúc trên khuôn mặt mỗi giây — khớp với phát hiện CU+MCU chiếm đa số ở nghiên cứu DRAMA_DOC trước (79%), **độ tin: có thể**, vì đã thấy lặp lại ở 2 nguồn AI short drama khác nhau (kênh này + kênh trong `NGHIEN_CUU_DRAMA_THAM_KHAO_2026-09-28.md`).
2. **Phụ đề song ngữ Trung–Anh chồng 2 dòng** luôn hiện, kể cả không có "banner CTA" như phim tham khảo trước — ý đồ **[có thể]**: kênh nhắm cả khán giả nói tiếng Anh xem lại nội dung gốc Trung, mở rộng thị trường re-upload/localize. Độ tin: có thể (chỉ quan sát 1 kênh).
3. **Twist được thả liên tục qua đối thoại ngắn** (ví dụ câu "黎溪下降頭了" ở phút 74) thay vì dựng một cảnh riêng cho mỗi twist — ý đồ **[có thể]**: giảm chi phí sản xuất AI (không cần cảnh hành động minh hoạ "hạ bùa"), đồng thời giữ nhịp truyện dồn dập đúng kiểu 爽剧. Độ tin: đoán (chỉ 1 mẫu, cần xem thêm bối cảnh trước/sau câu thoại để xác nhận).

## Nhạc nền
**Không nghe được** — Web Audio bị chặn trên iframe YouTube trong phiên này (không tải video). Không có dấu hiệu hình ảnh nào (không có biểu tượng nhạc, không thấy nhân vật hát/nhảy) gợi ý thời điểm đổi nhạc trong 2 đoạn đã xem — cần người dùng nghe trực tiếp để bổ sung mục G (âm thanh).

## Giới hạn / câu hỏi mở
- **Chỉ đo 2 đoạn ngắn (240s / ~3.2% video)**, không đủ để kết luận về cấu trúc toàn phim (mở đầu → cao trào → kết) — chỉ nêu quan sát cục bộ.
- **Không lấy được ảnh mẫu có hệ thống cho từng shot**: khi tạm dừng video rồi đặt `currentTime`, khung hiển thị bị "đứng hình" ở vị trí cũ (YouTube không vẽ lại khi đang pause) — nhiều lần chụp lặp lại cùng một khung dù đã đổi thời điểm; khi phát tiếp thì quảng cáo giữa video (mid-roll) chen ngang bất kể vị trí tua tới. Do đó bảng shot-by-shot đầy đủ (in/out từng shot, cỡ/góc/máy/vai trò) **chưa làm được cho video này** — chỉ có số đo cắt (khách quan, đáng tin) + một số khung quan sát rời rạc (đã tách rõ trong mục "Quan sát trực tiếp").
- Chưa xác định đúng vị trí cảnh "揭面" (lộ mặt) nêu trong tiêu đề — không có mục lục/chương, cần người dùng chỉ mốc giây hoặc tìm trong bình luận ghim.
- Chưa xác nhận watermark "AI生成+" trực tiếp trong lần xem này (đã ghi trong `MAU_S0_12.md` từ trước, không kiểm tra lại để tiết kiệm lượt).
