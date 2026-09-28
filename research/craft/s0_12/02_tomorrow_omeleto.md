# 02 — TOMORROW (Omeleto)

- **URL**: https://www.youtube.com/watch?v=bVZl51CqUXk
- **Thể loại**: phim ngắn — **CGI/hoạt hình 3D kể chuyện, không phải người quay thật** (xác nhận lại lần 2). **Sửa lại so với `MAU_S0_12.md`**: mục đó ghi "Bối cảnh Iran thập niên 1970, cậu bé đường phố kết bạn với chó" và xếp vào nhóm "Short film (live-action)" — đây là nhân vật 3D animated, không phải người thật quay. Cần sửa nhãn "live-action" → "CGI animation" trong bảng gốc.
- **Độ dài**: 16:46 (1005s) · khung **1280×720 (16:9)** — đo được chính xác lần này (ffprobe), không phải suy đoán như lượt trước.
- **Đoạn đã đo (LÀM LẠI bằng tải về)**: (1) 0:00–3:00 (mở đầu, 180.0s) · (2) 12:30–14:40 (750–880s, 130.0s)
- **Tổng đã đo**: 310s / 1005s (~31% video)
- **Đã tải**: `v02_seg1_bVZl51CqUXk.webm` (17.4 MB) + `v02_seg2_bVZl51CqUXk.webm` (8.5 MB) — **đã xoá cả hai + thư mục frame/sheet sau khi viết xong file này**.

## Phát hiện quan trọng nhất của lượt làm lại: **đoạn cao trào thật nằm TRONG 3 phút đầu, không phải ở phút 12–14 như đoán trước**
Lượt đo trong trình duyệt trước (không tải, chỉ xem vài khung rời rạc) đã bỏ lỡ một cảnh bạo lực rõ ràng ở **shot #19–30 (120.8–163.4s)**: người đàn ông béo (chủ tiệm đồ cổ) túm/đánh cậu bé, cậu bé ngã, xen cảnh con vật (chó?) bị đá/hất — xem bảng shot bên dưới. Đoạn 12:30–14:40 (đã đo cả hai lượt) hoá ra là **một cảnh cao trào KHÁC, còn kịch tính hơn**: cận nòng súng (#3, 21.9–40.6s) chĩa vào, cậu bé sợ hãi sau hàng rào dây thép (#4), rồi cảnh mặt trời lặn/qua ngày (#5) và các shot dài lặng lẽ — cho thấy phim có **ít nhất 2 cao trào/biến cố lớn** (bạo lực tay chân ở phút ~2, đe doạ bằng súng ở phút ~13), không phải chỉ 1 khoảnh khắc lặng như đoán trước.

## Phương pháp (v2 — tải về)
- Tải bằng `yt-dlp --download-sections`. Điểm cắt: ngưỡng `0.28` (như video 01) — 34 shot/180s (đoạn 1), 8 shot/130s (đoạn 2, rất ít cắt).
- Tờ ảnh: 2 tờ (30 + 4 shot) cho đoạn 1, 1 tờ (8 shot) cho đoạn 2 — đọc trực tiếp bằng mắt.
- Âm thanh: `ebur128`, `silencedetect`, RMS 1 mẫu/giây — cùng phương pháp video 01.
- Chuyển động máy trong shot: **không đo được đáng tin** bằng chỉ số khác biệt khung (cùng lý do đã ghi ở video 01 — lẫn với chuyển động nhân vật/lá cây); với phim này còn lẫn thêm hiệu ứng ống kính (rung máy quay giả lập, DOF) nên **không ghi `camera_move` per-shot chắc chắn**, chỉ mô tả bằng mắt khi rõ ràng (ví dụ shot toàn cảnh tĩnh, hoặc shot rõ ràng có lia/theo chủ thể).

## Số đo
| Đoạn | Shot | Độ dài trung vị | Min–Max |
|---|---|---|---|
| Mở đầu 0:00–3:00 | 34 | 3.7s | 0.37–14.5s |
| ~12:30–14:40 (750-880s) | 8 | 14.8s | 0.69–39.7s |

### Âm thanh — số đo
| Đoạn | LUFS tích hợp | LRA | Đỉnh thật | Số quãng lặng (≥0.3s) |
|---|---|---|---|---|
| Mở đầu | −20.7 LUFS | **21.3 LU** (rất rộng) | 0.6 dBFS | 11 |
| ~12:30–14:40 | −18.8 LUFS | 18.1 LU | **3.4 dBFS** (bất thường — vượt cả 0dBFS, có thể do inter-sample peak/hiệu ứng, chưa rõ nguyên nhân) | 3 |

- **LRA rất rộng (18–21 LU) so với video 01 (~9 LU)** — phim này có khoảng động lớn hơn nhiều: đoạn rất êm (gió, môi trường) xen đoạn cao trào to hẳn (có thể nhạc dữ dội ở cảnh súng/đánh nhau). Độ tin: **có thể**, đúng hướng với LRA cao là đặc trưng phim tự sự có nhạc phim thay đổi theo cảm xúc (khác track nhạc lặp đều của MV).
- **Rất ít quãng lặng thật sự** (11 và 3 lần) so với video 01 (46 và 33 lần trong cùng độ dài) — **[có thể]**: phim này gần như luôn có nhạc nền/âm thanh môi trường liên tục (matching MV ClipAI đã phân tích trước — "nhạc không bao giờ tắt"), khác kiểu ngắt-bật của video 01. Đây là khác biệt rõ giữa 2 thể loại — **độ tin: có thể**, cần nghe thật để xác nhận đó là nhạc phim liên tục hay chỉ là noise-floor môi trường không tắt hẳn.
- Đỉnh 3.4 dBFS ở đoạn 2 — bất thường hơn cả video 01 (0.0 dBFS); nếu đúng thì đây là hiện tượng "true peak vượt 0dBFS sau tái tạo" — dấu hiệu **hậu kỳ chưa kiểm true-peak limiter chặt** dù là phim của studio/trường lớn (Media Design School — theo ghi chú trong `MAU_S0_12.md`).

## Bảng shot — đoạn 1 (0:00–3:00, 34 shot)
> Góc máy: chủ yếu eye-level, có vài góc thấp/cao khi nhấn nhân vật (ghi ở cột). Chuyển cảnh: cut cứng, trừ #4 có chữ tiêu đề chồng lên hình (không phải chuyển cảnh riêng).

| # | Vào–ra | Dài | Cỡ cảnh | Hành động |
|---|---|---|---|---|
| 1 | 0.0-12.4 | 12.4s | WS | toàn cảnh khu phố/toà nhà — thiết lập bối cảnh |
| 2 | 12.4-27.0 | 14.5s | MS | cậu bé ở sạp hàng ngoài chợ (hành, gia vị) |
| 3 | 27.0-34.0 | 7.1s | MS | cậu bé đi dọc hẻm cạnh cây |
| 4 | 34.0-38.4 | 4.3s | CU | cậu bé một mình cạnh tường, chữ "A FILM BY: ARYA..." chồng hình (thẻ tựa đề) |
| 5–6 | 38.4-52.3 | 11.1/2.8s | CU | cậu bé cận, biểu cảm tò mò/lo lắng |
| 7 | 52.3-59.3 | 7.0s | CU | người đàn ông béo (chủ tiệm đồ cổ) xuất hiện, nhìn nghiêm nghị |
| 8 | 59.3-64.9 | 5.6s | CU | cậu bé cận tiếp |
| 9 | 64.9-73.1 | 8.2s | MS | cậu bé nấp sau gốc cây |
| 10–12 | 73.1-92.1 | 2.2/14.5/2.3s | CU/ECU | con chó xuất hiện — cận mũi to, một mình trong hẻm, cận tiếp |
| 13 | 92.1-94.5 | 2.4s | MS | cậu bé + chó cùng trong hẻm |
| 14–15 | 94.5-98.6 | 2.4/1.7s | MS | cậu bé bước đi khỏi tường; cậu bé chạy |
| 16 | 98.6-106.5 | 7.8s | WS | toàn cảnh phố với các toà nhà mái ngói |
| 17 | 106.5-111.5 | 5.0s | insert | cửa sổ có lưới sắt trang trí, có bóng người/vật phía sau |
| 18 | 111.5-120.8 | 9.3s | MS | nội thất tối, cậu bé đứng |
| **19–30** | **120.8-163.4** | 1.0–5.1s | **CU/MS** | **CAO TRÀO BẠO LỰC**: người đàn ông béo túm/đánh cậu bé, cậu bé bị hất/ngã nhiều lần, xen cận tay người đàn ông nắm chặt, hình dạng tối (con vật?) bị đá văng, cậu bé nằm trên đất — chuỗi 12 shot rất ngắn (nhiều shot < 3s, có shot 0.37s) khác hẳn nhịp chậm của phần trước |
| 31–33 | 163.4-176.4 | 1.1/2.6/9.3s | CU | người đàn ông đứng thở, cận tay/thắt lưng, người đàn ông cận tiếp (bình tĩnh lại) |
| 34 | 176.4-180.0 | 3.6s | WS | toàn cảnh hẻm vắng lúc chiều tà — hình dạng nhỏ (chó?) nằm giữa đường phía xa |

## Bảng shot — đoạn 2 (~12:30–14:40, 750–880s, 8 shot — RẤT ÍT CẮT)
| # | Vào–ra | Dài | Cỡ cảnh | Hành động |
|---|---|---|---|---|
| 1 | 0.0-18.3 | 18.3s | MS | người đàn ông béo bước đi nhanh, giận dữ |
| 2 | 18.3-21.9 | 3.6s | MS | cậu bé chạy theo/chạy trốn |
| 3 | 21.9-40.6 | **18.7s** | ECU/insert | **cận nòng súng trong tay** — shot rất dài, căng thẳng kéo dài |
| 4 | 40.6-80.3 | **39.7s** | CU | cậu bé sợ hãi sau hàng rào dây thép — **shot dài nhất trong cả 2 đoạn đã đo (gần 40s, ~10× trung vị đoạn 1)** |
| 5 | 80.3-82.5 | 2.2s | EWS | toàn cảnh núi non lúc hoàng hôn — chuyển thời gian/không gian |
| 6 | 82.5-93.8 | 11.3s | MS | cậu bé một mình, ngồi thu mình trong hẻm |
| 7 | 93.8-129.3 | **35.5s** | WS | chó chạy dọc con đường vắng — shot dài, không cắt |
| 8 | 129.3-130.0 | 0.7s | MS | cậu bé đứng ở khung cửa nhìn vào — cắt ngang do hết đoạn tải, không rõ nội dung tiếp |

## Kỹ thuật đáng học
1. **Nhịp cắt đổi hẳn theo mức độ căng thẳng**: đoạn thiết lập/dạo đầu median 3.7s (đã chậm hơn kịch bản trung bình), nhưng cụm cao trào bạo lực (#19–30) rút xuống có shot 0.37–1.0s — biên độ nhịp cắt trong CÙNG MỘT PHIM rộng hơn nhiều so với video 01 (AI drama giữ nhịp gần như đều suốt). Độ tin: **có thể**, đúng nguyên tắc dựng phim cổ điển (cắt nhanh = hỗn loạn/bạo lực, cắt chậm = tĩnh lặng/suy tư) — nhưng đây vẫn là 1 mẫu.
2. **Shot cực dài (18–40s) dùng cho khoảnh khắc đe doạ kéo dài và khoảnh khắc cô đơn sau biến cố** (#3, #4, #7 ở đoạn 2) — máy gần như không cắt trong lúc căng thẳng đỉnh điểm (súng chĩa vào) lẫn lúc trống trải sau đó (chó chạy một mình 35.5s không cắt). Ý đồ **[có thể]**: giữ nguyên thời gian thực của khoảnh khắc sợ hãi/mất mát, không cắt vụn để người xem "ở lại" cảm giác đó cùng nhân vật — ngược hẳn kỹ thuật cắt nhanh dồn dập của video 01. Độ tin: có thể.
3. **LRA rất rộng (18–21 LU) + rất ít quãng lặng** — gợi ý nhạc phim thay đổi cường độ liên tục theo cảm xúc thay vì bật/tắt như video 01. Độ tin: có thể, chưa nghe được để xác nhận.
4. **Cấu trúc: 2 biến cố lớn cách nhau ~10 phút** (đánh nhau ở phút ~2, đe doạ súng ở phút ~13) — phim ngắn có nhiều hơn 1 đỉnh kịch tính, không phải chỉ có 1 climax cuối như giả định ban đầu của lượt đo trước. Bài học phương pháp: **không nên đoán vị trí cao trào theo tỉ lệ % thời lượng** — cần xem lướt nhanh (hoặc đọc tóm tắt) trước khi chọn đoạn, thay vì nhảy thẳng tới một mốc theo phần trăm.

## Nhạc nền
Vẫn **không nghe được bằng tai**. Số đo (LRA rộng, ít quãng lặng, đỉnh bất thường ở đoạn cao trào) gợi ý nhạc/âm thanh môi trường chạy gần như liên tục và đổi cường độ mạnh theo cảnh — nhưng đây là suy luận từ số đo, **cần người dùng nghe trực tiếp** để xác nhận đây là nhạc phim thật sự thay đổi theo kịch tính hay chỉ là hiệu ứng môi trường (gió, tiếng phố).

## Giới hạn / câu hỏi mở
- Vẫn chỉ đo 310s/1005s (~31%) — đoạn giữa 3:00–12:30 và sau 14:40 chưa xem, có thể còn thêm biến cố khác.
- Đoạn 2 kết thúc giữa chừng shot #8 (hết đúng 130s tải) — không biết chuyện gì xảy ra tiếp ngay sau đó (cậu bé nhìn thấy gì ở khung cửa).
- Không xác định được người đàn ông béo trong đoạn 1 (đánh cậu bé) và đoạn 2 (cầm súng) có phải cùng một nhân vật hay không — thể hình giống nhau nhưng chưa đối chiếu kỹ trang phục giữa 2 đoạn cách nhau ~10 phút phim.
- `camera_move` per-shot vẫn không đo được đáng tin (xem mục Phương pháp).

## Xoá dữ liệu
Đã xoá `v02_seg1_bVZl51CqUXk.webm`, `v02_seg2_bVZl51CqUXk.webm`, thư mục `v02_seg1_frames/`, `v02_seg2_frames/`, và các `v02_seg*_sheet_*.jpg` khỏi `scratchpad/s012` sau khi viết xong file này — chỉ giữ JSON số đo nội bộ (không đưa vào repo).
