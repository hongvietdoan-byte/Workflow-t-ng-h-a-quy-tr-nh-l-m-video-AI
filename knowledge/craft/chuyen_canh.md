# Chuyển cảnh (S0.11 lượt 2, 2026-09-29)

> Đọc `README.md` trước. **Nguyên tắc người dùng:** chuyển cảnh che máy phải được **thiết kế trong chuyển động** của cảnh (vật / người đi ngang
> sát ống kính, máy lia theo vật, máy tiến vào vật đến khi che kín khung) — lên từ lúc chia shot, không chèn bù một cận vật ở khâu dựng.
> Luật pipeline: dp.md Q9 (cắt trên hành động, cắt khớp, trục), Q12; editing.md E1; trường `transition_in` (S3.6).

### Cắt cứng là mặc định
- **Cách làm:** nối thẳng hai shot, không hiệu ứng.
- **Có thể phục vụ:** giữ nhịp nhanh, không để kỹ thuật chen vào truyện · để dành hiệu ứng cho vài chỗ thật sự đổi thế giới.
- **Ví dụ:** [01 0–180s] 107 shot, không thấy fade / dissolve / wipe nào · [02] cắt cứng cả hai đoạn (trừ chữ tiêu đề chồng hình) · [CM] hòa hình
  chỉ một lần ở 3:14.
- **Nguồn:** tờ ảnh S0.12, CM. **Độ tin:** khá.

### Chuyển cảnh che máy — thiết kế trong chuyển động (hidden cut)
- **Cách làm:** shot trước kết ở khung bị che bởi một vật / người **có lý do trong cảnh** (đi ngang ống kính, máy lia theo vật, máy tiến vào vật);
  shot sau mở ra từ trạng thái che / hướng lia tiếp theo. Cả hai shot được chia cùng lúc: hành động + đường máy + khung cuối shot trước khớp khung
  đầu shot sau.
- **Có thể phục vụ:** nối hai không gian / thời điểm như một dòng liền · nối hai lần sinh video thành "một cú máy" · dồn nhịp nếu dùng liên tiếp.
- **Khi hợp / khi không:** vật che phải thuộc cảnh — vật phi lý làm người xem thấy "mẹo"; **không** phải chèn cận vật ngẫu nhiên để giấu chỗ nối.
- **Ví dụ:** [CM 1:16,3] tay lật quân Át lóe sáng giữa hai shot của nhân vật nữ — cử chỉ có chủ ý làm chỗ nối. Chưa gắn nhãn được trong 21 mẫu
  S0.12 (cần soi ≥ 5–10 khung/giây quanh điểm cắt; phép đo hiện tại chỉ bắt điểm cắt, không bắt che).
- **Với video AI:** hai cách: (1) một lần sinh nhiều shot có đường máy nối (Seedance, xem mục sau) · (2) hai shot riêng: shot A kết ở khung che
  kín bởi vật cụ thể, shot B mở từ cùng trạng thái — ghi ở `transition_in` + motion prompt của cả hai; ảnh khung cuối / khung đầu (cờ
  `end_frames`) giúp khớp.
- **Ví dụ thêm (S0.12 mẫu 20–28, 2026-09-29):** [24 ~16–30s] biển quảng cáo sóng biển → nước tràn ra sân ga → dưới nước: chuyển thế giới qua **một vật trong khung** (MV Kling AI).
- **Nguồn:** người dùng (cách làm nghề, 2026-09-29); dp.md Q12; Dmytryk "cắt giữa chuyển động để chuyển động che vết cắt" [E2]. **Độ tin:**
  cách làm: chắc (nghề + nguồn); ví dụ: có thể (1 mẫu CM) — cần thêm mẫu.

### Chuyển cảnh bằng đường máy trong cùng một clip
- **Cách làm:** máy đi liền từ không gian A sang B (bay qua, xuyên qua vật, hạ xuống), không có điểm cắt.
- **Có thể phục vụ:** đánh dấu bước sang một thế giới khác (siêu thực) · giữ mạch liền khi đổi nơi.
- **Ví dụ:** [CM 2:20,6–2:21] máy bay lên xuyên đèn chùm rồi hạ xuống mặt bàn phóng to — đổi sang thế giới siêu thực (dải 10 khung/giây liền).
- **Với video AI:** Seedance nhiều shot / một lần sinh, mô tả đường máy trong prompt (G-MV5; `research/craft/trung_quoc/PROMPT.md`) — rủi ro
  model tự thêm cắt; một chuyển động chính mỗi đoạn [Q8].
- **Nguồn:** CM (đo 10 khung/giây). **Độ tin:** có thể (1 mẫu).

### Chớp trắng / loé sáng làm nối hoặc dấu chấm
- **Cách làm:** khung cháy trắng (hoặc loé sáng / chớp trời) vài khung giữa hai shot hoặc trong shot.
- **Có thể phục vụ:** (a) đổi không gian đúng nhịp nhạc (đầu điệp khúc) · (b) "dấu chấm than" rẻ giữa các CU khóc, không cần diễn · (c) một
  khoảnh khắc trong truyện (súng / đèn chiếu thẳng) cắt ngang tầm nhìn.
- **Ví dụ:** (a) [08 109–120s] khói màu → **chớp trắng 114 s** → top-down → sa mạc 119,8 s, trùng đầu điệp khúc 2 (±1 s) · (b) [10] insert chớp
  trời 0,3–0,4 s giữa các CU khóc · (c) [18 đ2 +71–98s] chớp trắng cháy khung (#36–37) trong đêm đèn pin.
- **Với video AI:** chớp trắng / chớp trời là tài sản dựng (ffmpeg), không tốn lượt sinh; chớp làm phép đo cắt bắt nhầm (08, 09, 17).
- **Ví dụ thêm (S0.12 mẫu 20–28, 2026-09-29):** [24 ~72–77s] pha lê tím nổ → khung trắng → đời thường · [28 đ2 +128–147s] zoom vào trắng → vườn địa đàng ("reset").
- **Nguồn:** mẫu 08, 10, 18. **Độ tin:** khá (3 mẫu, 3 ý đồ khác nhau).

### Shot nối bối cảnh (insert vật / toàn cảnh rỗng giữa hai cảnh)
- **Cách làm:** giữa hai cảnh chèn một shot không người nói: vật đặc trưng của cảnh sau, hoặc toàn cảnh thiên nhiên.
- **Có thể phục vụ:** báo đổi nơi / nhóm nhân vật · báo trôi thời gian · khoảng thở sau một biến cố.
- **Khi hợp / khi không:** đây là shot **thuộc cảnh** (thiết lập), khác "cận vật che chỗ nối" mà người dùng đã bác.
- **Ví dụ:** [01 59.1–60.2s] insert xe Bentley biển số → nhóm nhân vật mới · [02 đ2 +80.3–82.5s] EWS núi hoàng hôn sau cảnh súng → cậu bé một mình
  · [10 14.2s] insert ảnh gia đình trên bàn bếp, mở "cuộc sống thường ngày" trong im lặng · [07 53–60.7s; đ2 +107–115s] toàn cảnh + lặng
  mở tập (có thể là chỗ nối tập của bản gộp).
- **Nguồn:** tờ ảnh S0.12. **Độ tin:** khá (4 mẫu).

### Nhảy thời gian / thực tại bằng tương phản (màu + lặng + một câu)
- **Cách làm:** cắt cứng nhưng đổi hẳn tông màu và / hoặc âm (vào im lặng), kèm một chi tiết xác nhận (câu "tôi mơ", insert lịch, dấu âm).
- **Có thể phục vụ:** từ giấc mơ về thực (lật lãng mạn thành hài) · từ cảnh tương lai về "trước đó" · trọng sinh · chen một hồi ức 1–2 shot vào
  hiện tại · ký ức trong MV.
- **Ví dụ:** [11 28.4s] đêm xanh lạnh → phòng hồng ấm, lặng 28,6–29,3 s, "我做梦了" · [10 14.2s] cảnh tương lai có nhạc → im lặng hoàn toàn đúng
  điểm cắt · [14 108.4–131s] bóng tối → tỉnh dậy + insert lịch + "tôi quay lại rồi", lặng xen giữa · [15 đ3 +77.6–80.5s] insert hồi ức nụ hôn
  (tông hồng / xanh neon) kèm Ding + Whoosh · [23 đ1] ký ức = cụm 0,6–1,1 s màu neon / tuyết giữa shot dài vàng nâu.
- **Với video AI:** màu làm ở hậu kỳ (E5) + lặng / dấu âm ở khâu trộn — không cần thẻ "X năm trước".
- **Ví dụ thêm (S0.12 mẫu 20–28, 2026-09-29):** [27 đ2 +60–89s] hồi ức: khung đỏ cam + nhạc vọt 14 dB; về hiện tại bằng CU mắt robot đổi xanh → đỏ · [26 89.7s] 1 s đen + tiếng mưa (tỉnh mơ).
- **Nguồn:** mẫu 10, 11, 14, 15, 23 (mẫu hình 8, 11 `TONG_HOP.md`). **Độ tin:** khá → chắc (5 mẫu, đo khớp tới 0,1–0,2 s ở 10, 11).

### Cắt khớp (match cut)
- **Cách làm:** hai shot có hình khối / chuyển động giống nhau nối hai nơi / thời điểm.
- **Có thể phục vụ (theo nguồn):** nối ý giữa hai thời điểm · chuyển cảnh mượt mà không cần hiệu ứng.
- **Ví dụ:** chưa gắn nhãn được trong 21 mẫu (cần so khối hình hai bên điểm cắt — chưa có công cụ). [15 99.6–155.2s] phát lại **đúng** các khung
  của cảnh mở khi truyện đuổi kịp — là lặp lại, không phải cắt khớp.
- **Nguồn:** dp.md Q9 [E3]. **Độ tin:** giả thuyết (chưa có mẫu).
