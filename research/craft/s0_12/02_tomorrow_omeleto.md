# 02 — TOMORROW (Omeleto)

- **URL**: https://www.youtube.com/watch?v=bVZl51CqUXk
- **Thể loại**: phim ngắn — **CGI/hoạt hình 3D kể chuyện, không phải người quay thật**. **Sửa lại so với `MAU_S0_12.md`**: mục đó ghi "Bối cảnh Iran thập niên 1970, cậu bé đường phố kết bạn với chó" và xếp vào nhóm "Short film (live-action)" — xem trực tiếp thì đây rõ ràng là nhân vật 3D animated (da/tóc/biểu cảm cách điệu, không phải người thật quay bằng camera), dù bối cảnh (Trung Đông, sạp hàng, tường gạch) vẫn đúng như mô tả. Cần sửa nhãn "live-action" → "CGI animation" trong bảng mẫu gốc.
- **Độ dài**: 16:46 (1005s) · khung 16:9 (1280×720 hoặc tương đương — không đo pixel chính xác, chỉ xem tỉ lệ khung phát)
- **Đoạn đã đo**: (1) 0:00–3:00 (mở đầu, 180s) · (2) 12:30–14:30 (750–870s, 120s — chọn theo tỉ lệ vị trí ~75–87% thời lượng, không có mục lục/tóm tắt để xác định đúng điểm cao trào, nên đây là **đoạn cuối gần kết** chứ chưa chắc là "cao trào" theo nghĩa kịch tính nhất)
- **Tổng đã đo**: 300s / 1005s (~30% video)

## Phương pháp
- Cùng kỹ thuật với video 01: khác biệt khung hình (grayscale, toàn khung — phim này không có phụ đề cứng nên không cần crop) tính trong trình duyệt qua canvas 40×23, lấy mẫu mỗi ~90ms trong khi phát ×2 (muted).
- Ngưỡng cắt: phải nâng lên `floor=40, factor=6, local_floor=45, local_factor=5` (cao hơn cả video 01 và cả nghiên cứu DRAMA_DOC trước) vì phim có **máy chuyển động liên tục + lá cây/gió rung** làm nhiễu tín hiệu diff — ngưỡng mặc định (18/4) cho ra 123 "cắt" giả trong 180s, ngưỡng 30/5 cho 53, ngưỡng 40/6 cho 37 — chọn 40/6 vì khớp với số cảnh hợp lý khi xem bằng mắt (không có cắt giả rõ rệt ở các khung đã xem).
- Âm thanh: **không nghe được** (không tải video, không mở được Web Audio trên iframe YouTube — xem giới hạn ở video 01).

## Số đo (2 đoạn, 300s, 41 "cắt")
| Đoạn | Số cắt phát hiện | Shot ước tính | Độ dài shot trung vị |
|---|---|---|---|
| Mở đầu 0:00–3:00 | 37 | 38 | 3.1s (max 16.7s) |
| ~12:30–14:30 | 3 | 4 | 35.3s (rất tĩnh, gần như 1 cảnh dài) |

**Chênh lệch rất lớn giữa 2 đoạn** — mở đầu cắt khá nhanh cho phim tự sự (median 3.1s, nhanh hơn phim truyện thông thường nhưng chậm hơn nhiều so với AI short drama ở video 01 ~1.6–2.0s), còn đoạn cuối gần như không cắt (3 lần cắt / 120s) — quan sát bằng mắt cho thấy đây là 1-2 cảnh toàn/rộng tĩnh, không có nhân vật nói, chỉ có chó ăn cạnh tường rồi một sân trong vắng lúc hoàng hôn.

## Quan sát trực tiếp
- **0:15** — toàn cảnh trung (MS) một sạp hàng ngoài chợ (hành, tỏi, gia vị), cậu bé xuất hiện góc trên đi ngang qua — máy tĩnh, ánh sáng chiều vàng, không thoại.
- **0:40** — trung cảnh hai người (cậu bé đưa tiền cho người đàn ông béo ngồi trước "Antique Shop") — góc ngang mắt hơi thấp (nhìn lên người đàn ông to lớn), máy tĩnh.
- **1:20** — trung cảnh con chó hoang đứng cạnh tường gạch trong hẻm, không có người — toàn cảnh vắng, gợi cô đơn/lang thang.
- **2:10** — cận (CU) người đàn ông béo và cậu bé giằng co gần nhau (căng thẳng thể chất), góc thấp một chút — biểu cảm giận dữ trên mặt người đàn ông rất rõ dù là CGI.
- **2:50** — cận đặc tả (CU/ECU) khuôn mặt người đàn ông, cau mày, ria mép rậm — dùng cận sát để nhấn tính cách đe doạ của nhân vật.
- **13:10** — toàn cảnh (WS) con chó ăn lặng lẽ cạnh tường gạch, chiều tà, lá vàng — không người, không thoại, máy tĩnh dài.
- **14:10** — toàn cảnh rộng (EWS) một sân/ngõ trống hoàn toàn, không nhân vật, cây lá đỏ mùa thu, ánh chiều — cảnh rất tĩnh, giữ máy lâu.

## Kỹ thuật đáng học
1. **Nhịp cắt mở đầu vừa phải (median 3.1s) xen các shot dài hơn (tới 16.7s)** để thiết lập không gian/quan hệ nhân vật — khác hẳn nhịp cực nhanh đồng đều của AI short drama (video 01). Ý đồ **[có thể]**: phim tự sự truyền thống cho khán giả thời gian "ở lại" trong không gian để cảm nhận bối cảnh, không chỉ đẩy thông tin thoại. Độ tin: có thể (khớp hiểu biết chung về phim ngắn festival, nhưng đây là quan sát 1 mẫu).
2. **Cảnh gần cuối gần như không cắt (3 cắt/120s), dùng toàn cảnh tĩnh dài, không thoại, không nhân vật chính trong khung** (chó ăn một mình, sân vắng) — ý đồ **[có thể]**: tạo khoảng lặng cảm xúc trước/sau một biến cố (mất mát, chia ly, hoặc kết truyện) — kỹ thuật "để hình ảnh trống nói thay lời" — cùng hướng với ghi chú "bạo lực/xung đột thể hiện qua hậu quả" trong nghiên cứu DRAMA_DOC trước (không quay va chạm mà quay dư âm), nhưng ở đây là dư âm cảm xúc chứ không phải bạo lực. Độ tin: có thể — cần xem đoạn liền trước/sau để biết chính xác chuyện gì vừa xảy ra (câu hỏi mở).
3. **CGI diễn cảm xúc rõ trên khuôn mặt cách điệu** (người đàn ông béo cau mày ở 2:50) dù không phải người thật — đáng học cho pipeline AI: biểu cảm mạnh (mày, miệng) vẫn truyền được cảm xúc dù nhân vật không photorealistic. Độ tin: có thể, 1 mẫu.

## Nhạc nền
**Không nghe được** — cùng giới hạn Web Audio như video 01. Không có dấu hiệu hình ảnh về thời điểm đổi nhạc trong 2 đoạn đã xem; đoạn gần cuối tĩnh lặng về hình có thể đi cùng nhạc rất nhẹ hoặc chỉ tiếng môi trường (gió, lá) — **suy đoán, không nghe được — cần người dùng nghe**.

## Giới hạn / câu hỏi mở
- Chỉ đo 300s / 1005s (~30%) — vẫn thiếu đoạn giữa phim (3:00–12:30) hoàn toàn.
- Đoạn 2 (750–870s) được chọn theo tỷ lệ vị trí, **chưa chắc là cao trào kịch tính** — cần xem mô tả/bình luận hoặc xem nhanh đoạn 3:00–12:30 để xác định đúng đỉnh truyện (ví dụ: xung đột với người đàn ông chủ shop có leo thang không, con chó có vai trò gì ở giữa phim).
- Ngưỡng phát hiện cắt phải điều chỉnh riêng cho từng video (chuyển động máy/lá cây làm nhiễu) — số shot ước tính có sai số, đặc biệt các shot dài có chuyển động chậm bên trong có thể bị bỏ sót nếu không đủ tương phản.
- Đã sửa một sai lệch trong `MAU_S0_12.md` (nhãn "live-action" → cần đổi thành "CGI animation" cho video này) — nên cập nhật lại bảng gốc.
