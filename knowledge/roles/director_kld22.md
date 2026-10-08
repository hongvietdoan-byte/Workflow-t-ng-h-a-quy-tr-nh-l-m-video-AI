# Bổ sung vai Đạo diễn — bài học dự án #22 Khủng Long Đỏ (cờ `kld_lessons_prompts`)

> Bổ sung cho `director.md` (N4, Đ6, N3), không thay luật cũ. **Độ tin: 1 dự án (#22)** — là cách nghĩ có lý do, không phải luật chung;
> dự án khác có căn cứ khác thì làm khác và ghi `tradeoffs`. Nguồn: `docs/TONG_HOP_3_LUOT_KHUNG_LONG_DO.md` mục 4.2, 4.8.

## N4 bổ sung — Nhân vật đúng thiết kế
1. **Phụ kiện thuộc thiết kế trang phục** (khẩu trang, mũ, kính) giữ đúng trạng thái như ảnh OUTFIT trong mọi shot, kể cả shot nằm/ngồi
   hay shot cận. Muốn đổi (vd kéo khẩu trang xuống để thấy miệng) là **hy sinh thiết kế**: ghi `tradeoffs` và hỏi người dùng — vì trang phục
   là thứ video đang quảng bá. Căn cứ #22: người dùng chọn khẩu trang **đeo kín** suốt phim và chấp nhận khớp môi khó thấy.
2. **Chữ tiếng Việt nhiều nghĩa** (xanh = blue/green; mũ = cap/helmet/hood/beanie) → tra ảnh Kho hoặc hồ sơ của vật đó **trước** khi viết
   tiếng Anh. Ảnh là chuẩn thật (N4); nghĩa đầu tiên của từ điển thì không. Căn cứ #22: "mũ" từng thành *helmet*; mũ của MAXIM bản Khủng
   Long là **mũ đen có sừng đỏ** (người dùng xác nhận 08/10) — mô tả "mũ đỏ có sừng" sai vì chỉ nhìn ảnh chính diện. Không chắc → hỏi
   người dùng, đừng đoán.
3. **Shot nhảy / động tác theo video mẫu:** động tác là của video mẫu. `performance` chỉ tả mặt, ánh mắt, cường độ — không tự biên đạo
   thêm, vì hai nguồn động tác sẽ kéo nhau (#22 lượt 1). Video mẫu là gợi ý phong cách người dùng chọn cho shot đó, không là luật cho shot khác.

## Đ6 bổ sung — Kịch bản dán tay (không qua Biên kịch)
- Khi kịch bản dán tay (không có lượt Biên kịch), **đọc to từng câu thoại** trong đầu như người xem nghe. Câu nghe như khẩu hiệu hay lời
  quảng cáo (vd "Hô biến!") → ghi `script_notes` `kind: "thoại"` kèm câu hỏi gợi ý ("câu này nghe giống khẩu hiệu — nhân vật có nói vậy
  với bạn mình không?"). **Không tự sửa** (N1 vẫn thắng). Lý do: không lớp nào khác soát độ tự nhiên của thoại dán tay. Căn cứ:
  `screenwriter.md` B12/B13; #22 lượt 1 người dùng chê thoại cứng.

## N3 bổ sung — Dữ liệu khớp môi đã đo (#22)
- #22: Seedance 2.5 **chỉ-ảnh-tham-chiếu** + `reference_audio`, giọng đặt ở giây chẵn → điểm khớp môi 0,03 / 0,44, **chưa nhép**. Đường
  từng đạt 0,72–0,96 là `dialogue_take` (#10). Cách nghĩ: shot thoại cận cần thấy miệng thì cân nhắc `dialogue_take` (người dùng chọn);
  cảnh có trang phục che miệng (khẩu trang đeo kín) thì không thấy miệng là chấp nhận được — người dùng tạm chấp nhận ở #22. Mẫu: 2 clip,
  1 dự án — chưa là kết luận về model.
