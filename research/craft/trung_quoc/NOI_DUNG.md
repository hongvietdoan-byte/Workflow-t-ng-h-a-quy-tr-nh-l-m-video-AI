# Craft nội dung/kịch bản cho AI短剧 dọc (vertical short drama) (S phiên 2026-09-29)

> Tầng 3 (kỹ thuật/tư liệu) theo `knowledge/craft/PHUONG_PHAP_PHAN_TICH.md`. Số trong ngoặc dẫn `NGUON_TQ.md`. Đây là cách
> ngành TQ hay làm cho short drama dọc bán trên nền tảng trả phí theo tập (giống ReelShort) — **không phải luật cố định**, ghi
> rõ điều kiện áp dụng.

## 1. Vì sao nhịp khác phim dài — quan sát chung

Nguồn [10][11] đồng thuận về một quan sát: người xem short drama dừng lại trung bình **≈3 giây** trước khi lướt, nên 10 giây
đầu (nhiều nền tảng ép xuống 5–8 giây [16]) phải có xung đột mạnh hoặc nghi vấn mạnh ngay, không có chỗ cho phần dẫn nhập từ từ.
**Điều kiện áp dụng**: đây là đặc thù của *nền tảng phát theo dòng lướt dọc, trả phí xem tiếp* — khác với YouTube/phim rạp nơi
khán giả đã chủ động bấm vào. Không áp dụng máy móc cho nội dung không phát trên nền tảng kiểu này.

## 2. Ba yếu tố cảm xúc [10] (có thể phục vụ nhiều ý đồ khác nhau tuỳ câu chuyện — không phải công thức bắt buộc)

- **"Nhanh" (快)**: không có khoảng đệm; mở màn đã là cao trào.
- **"Gắt" (狠)**: mật độ cảm xúc cao — mỗi tập cần ít nhất 1 điểm bùng nổ cảm xúc (sướng/爽, đau/虐, hoặc phản转).
- **"Chuẩn" (准)**: cuối mỗi tập phải có nghi vấn/hook rõ ràng, vì đây là yếu tố quyết định tỷ lệ chuyển đổi trả phí xem tiếp.

**[suy luận của nguồn, chưa kiểm chứng độc lập]**: nguồn [10] khẳng định đây là công thức phổ biến trên các nền tảng dọc TQ,
nhưng không dẫn số liệu A/B test cụ thể — nên coi là kinh nghiệm thực hành phổ biến, không phải quy luật đã chứng minh.

## 3. Quy trình 4 bước viết kịch bản [10]

1. **Chốt đề tài + thiết lập cốt lõi**: chọn đề tài đang thịnh hành trên nền tảng (phục thù đổi đời, chốn công sở/thương
   trường, đổi thân phận…); dùng LLM sinh logline, thẻ nhân vật, mâu thuẫn cốt lõi, điểm phản转, hướng kết thúc.
2. **Đại cương + thiết kế hook từng tập**: mỗi tập tóm 1–2 câu + 1 "hook nghi vấn"; 5 giây đầu tập 1 phải bắt mắt ngay. Các
   loại hook thường gặp: lộ thân phận, treo khủng hoảng, báo trước phản转, bùng nổ cảm xúc.
3. **Chi tiết hoá thành phân cảnh**: mỗi shot 3–8 giây tối ưu, 1 hành động chính/shot, tránh chữ trong khung hình (AI hay sai
   chính tả — khớp với mục lỗi "文字拼写错误" trong tài liệu Seedance 2.5 chính thức [1]).
4. **Người duyệt lại thủ công**: nguồn không liệt kê chi tiết 5 tiêu chí duyệt — [suy luận] nhiều khả năng gồm tính nhất
   quán logic, tốc độ nhịp, độ dài lời thoại, phù hợp nền tảng, rủi ro bản quyền/kiểm duyệt.

## 4. Năm kỹ thuật nâng cao [10]

- **Kho thẻ nhân vật** (角色卡片库): mẫu mô tả thống nhất ngoại hình/trang phục/biểu cảm cho mỗi nhân vật, dùng lại xuyên suốt
  — tránh lệch mô tả giữa các tập (liên hệ trực tiếp tới nhất quán nhân vật, xem `QUY_TRINH.md` mục 4).
- **Đường cong cảm xúc kiểu tàu lượn**: cao trào → êm dịu → xung đột → đỉnh điểm → treo nghi vấn — không giữ 1 cường độ suốt
  tập.
- **"Luật 5 giây"**: cảnh mở đầu là 1 hành động/hình ảnh gây chú ý tức thì (ném hồ sơ, màn hình đen, cận cảnh sốc…).
- **Sinh hàng loạt rồi chọn**: để AI sinh 3–5 phiên bản đại cương/lời thoại, người chọn bản tốt nhất thay vì chỉ nhận 1 lần
  sinh.
- **Danh sách "yếu tố ăn khách"**: tát mặt, lật ngược thế cờ, lên cấp, giằng co tình cảm — nguồn liệt kê như motif hay dùng,
  **không phải yếu tố bắt buộc phải có** ở mọi câu chuyện.

## 5. Mười công thức hook mở đầu [11]

*(bảng công thức, mỗi công thức là 1 cách phối hình ảnh + tình huống — coi là ví dụ minh hoạ để hiểu logic, không phải khuôn
mẫu sao chép nguyên văn)*

| # | Logic cốt lõi | Ví dụ tình huống trong nguồn |
|---|---|---|
| 1 | Hình ảnh hoành tráng ghép tương phản thân phận thấp kém | Người lao công chỉ huy hạm đội thiên hà |
| 2 | Bối cảnh thiêng liêng + áp bức cực đoan | Nữ chính bị hành hạ trong cung điện |
| 3 | Luật sinh tồn phi logic tạo căng thẳng | "Đừng nhìn gương, ảnh phản chiếu sẽ động trước" |
| 4 | Chênh lệch sức mạnh cực đại → thoả mãn tức thì | Cụ già mù hạ gục lính có xe tăng |
| 5 | Dịch chuyển thời gian + va chạm văn minh | Đoàn lữ hành sa mạc phát hiện tàu ngầm chìm dưới cát |
| 6 | Nghi vấn mơ hồ, đứt gãy nhận thức | Bệnh nhân tỉnh dậy thấy mình nằm trên giường bệnh của chính mình |
| 7 | Tận thế cực đoan + lựa chọn đạo đức | 2 phi hành gia, 1 bộ đồ sinh tồn, 1% oxy |
| 8 | Xuyên thời gian định mệnh + luân hồi | Sinh vật cổ thức tỉnh sau 30.000 năm |
| 9 | Tương phản đẹp (váy cưới) và kinh dị (máu) | Cô dâu áo đỏ gục ngã, ánh mắt chuyển từ tuyệt vọng sang trả thù |
| 10 | Cảnh hành hình → đảo ngược thân phận ngay | Nhân vật bị xích trong lửa biến thành hoàng hậu trên kiệu |

**Cảnh báo thất bại đi kèm [11]**: hình ảnh rẻ tiền (độ phân giải thấp, chi tiết trang phục/trang sức thô) phá hỏng hook dù ý
tưởng hay; âm thanh phải đến **trước** hình ảnh ở khoảnh khắc gây sốc (tim ngừng đập, nhạc cụ đánh mạnh) — liên hệ trực tiếp
`NHAC_NEN.md`; tiền đề mở đầu phải khớp nội dung tập sau, lệch sẽ khiến khán giả rời đi ngay.

## 6. Thể loại hợp / không hợp AI [12] — snippet-only, độ tin vừa

- **Hợp**: đề tài cần hiệu ứng đặc biệt mạnh, kỳ ảo/xuyên không/cổ trang giả tưởng, hoạt hình động vật (khán giả khoan dung
  hơn với AI khi chủ thể không phải người), **kinh dị** (hiệu ứng "uncanny valley" của khuôn mặt AI tự nhiên hợp thể loại này
  thay vì là nhược điểm).
- **Không hợp** (theo nguồn, [suy luận] của người viết bài, chưa có số liệu đối chứng): nội dung tình cảm hiện thực đòi diễn
  xuất tinh tế — nguồn nhận định AI hiện chỉ đạt "70–80 điểm" diễn xuất, muốn "90+ điểm" cần sinh lại hàng trăm–nghìn lần, mất
  lợi thế chi phí.
- **Mô hình lai được khuyến nghị**: "người thật + AI" — người thật đóng cảnh cần diễn xuất tinh tế, AI đảm nhiệm cảnh kỳ ảo/
  khoa huyễn/cổ trang không thể quay thật.

## Điều kiện áp dụng — không mặc định cho mọi thể loại
Toàn bộ mục 1–5 mô tả **short drama dọc, trả phí theo tập, tối ưu giữ chân/chuyển đổi trên nền tảng lướt nhanh**. Với các thể
loại khác của dự án (MV, phim ngắn, hành động dài hơi) không nên áp "luật 5 giây" hay "mở đầu = cao trào" như một quy tắc mặc
định — cần đối chiếu lại `knowledge/craft/PHUONG_PHAP_PHAN_TICH.md` mục 2 ("tách clip này làm khỏi nên làm").

## Khoảng trống / câu hỏi còn mở
- Chưa tìm được phỏng vấn biên kịch có tên tuổi cụ thể (nguồn hiện tại đều là blogger/trang tổng hợp ẩn danh) — độ tin của
  toàn bộ mục "nội dung/kịch bản" dừng ở mức vừa.
- Chưa có số liệu A/B test thực tế nào chứng minh "10 công thức hook" hay "luật 5 giây" — chỉ là kinh nghiệm mô tả lại.
- 5 tiêu chí duyệt kịch bản thủ công ở mục 3 bước 4 chưa được nguồn liệt kê cụ thể.
