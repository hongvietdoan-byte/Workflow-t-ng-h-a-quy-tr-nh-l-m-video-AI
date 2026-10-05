# Kelly -> Biên kịch: định dạng dựng chắc được + cách triển khai (S14.34, 05/10/2026)

> **Địa vị: GỢI Ý theo phong cách, trộn được, KHÔNG bắt buộc. Mục đích: MỞ RỘNG cách làm, không thu hẹp vào một kiểu; mọi dòng dưới đây đọc là "có thể / nên cân nhắc / khi nào hợp".** Rút từ 40 clip của MỘT kênh (`@freefire_kelly_official`; `knowledge/ff_styles/kelly_official.md`, `ne_canh_kho_dung.md`). Chỉ ràng buộc dựng-được (S14.31) và danh sách Kho là chặn cứng, vì thứ ngoài Kho thật sự không dựng được. Nên học cách kể, không sao chép cảnh/hình của kênh.

## Bốn khuôn kịch bản (chọn khuôn hợp ý người dùng; ý người dùng đứng trước khuôn)
- **A. Một cận + đồ hoạ trend (5-12 s, 1 shot):** 1 nhân vật, 1 nền đơn giản, mặt cận giữ ổn định; "trò chơi" là lớp chữ/đồ hoạ chồng lên (thanh đo, cột hạng, nhãn, ống ngắm). Dễ dựng nhất, chi phí gen thấp. Viết: 1 cảnh, mô tả khuôn mặt + biểu cảm đổi theo nhịp, ghi riêng "Lớp đồ hoạ (hậu kỳ): ...".
- **B. Tiểu phẩm 2-4 shot tĩnh + HUD (8-15 s):** <= 2 nhân vật cùng khung, 1 nền đời thường, trạng thái trận thể hiện bằng thanh máu + tên + số đội (+ đầu lâu khi "chết") TRÊN ĐẦU nhân vật; nhân vật nhìn xuống điện thoại nhưng KHÔNG thấy màn hình. Cú chốt là phản ứng mặt.
- **C. Quảng bá sự kiện (~17 s):** nền cửa hàng + bong bóng chữ + poster do đội thiết kế. Chỉ khi người dùng đưa poster/CTA.
- **D. Gag nhiều shot ngắn "tình huống -> insert vật -> phản ứng mặt" (10-16 shot):** tốn tiền gen và khó giữ mặt qua nhiều shot, chỉ khi ngân sách cho phép; mỗi insert là clip 1-2 s dùng lại.
- Chuỗi chạy/nhảy/rượt nhiều nền (E) và cận điện thoại thật, hợp tác người thật, tổng kết ghép cảnh cũ (F) hiện khó dựng chắc: nên cân nhắc thay bằng khuôn A-D khi hợp ý (phần thật sự không dựng được vẫn do ràng buộc dựng-được ở trên chặn).

## Kỹ thuật né (thay vì dựng cảnh khó)
Trận đấu -> HUD/bảng kill/icon trên đầu; màn hình game -> nhân vật diễn mặt + thẻ chữ; giành đồ -> insert cận vật từ trên xuống; hậu quả -> cận phản ứng mặt (sốc, bịt miệng, vùi mặt). Map FF là đạo cụ trong phòng (bản đồ trên TV/tường), không là bối cảnh trận. Đây là các cách để tham khảo và trộn với phong cách khác, không phải cách duy nhất. Khi dùng, có thể viết lớp thông tin thành dòng riêng "Hậu kỳ: ..." (đồ hoạ, chữ, HUD) vì model vẽ chữ/HUD hay hỏng, và nên chừa khoảng trống trên đầu nhân vật.

## Hook, nhịp, cú chốt
- Giây 0-3: hiện ngay chữ hoặc HUD hoặc hành động; không chào hỏi/logo. 15/33 clip ngắn mở bằng lớp chữ/HUD.
- Clip ngắn là chuẩn: trung vị ~14 s, nhiều clip 1 cú máy; nếu nhiều shot thì shot ~1,5 s, chỉ ~10 % shot >= 4 s. Máy gần như tĩnh, cắt cứng.
- Ít thoại. Kênh dùng nhạc trend + hiệu ứng game thay lời; khi cần nói, câu thật ngắn. Nhạc/hiệu ứng nên cân nhắc bản quyền (ghi vào notes).
- Cú chốt = phản ứng/gag bất ngờ ngắn (mặt sốc, người "ghi 4 mạng" uống sữa nhàn nhã), CTA hiếm (2/40) nên chỉ thêm khi người dùng đưa.
- Đội diễn viên lặp lại tạo quen thuộc (Kelly, Maxim, Alvaro, pet) nhưng chỉ dùng người CÓ trong Kho.

## Cách viết thành cảnh (khi hợp)
- Nhịp của dàn ý không nhất thiết là một CẢNH. Khi các nhịp liền nhau cùng một nơi, nên cân nhắc gộp thành một cảnh dài hơn (nhiều dòng mô tả theo thứ tự thời gian) thay vì mỗi nhịp một cảnh; chỉ tách cảnh khi đổi nơi hoặc đổi thời điểm. Clip 15 s thường chỉ 1-3 cảnh.
- Giữ nhãn kỹ thuật ngoài lời mô tả: các nhãn như "Điểm xoay:", "Hậu kỳ:", "Cận mặt X:" có thể ghi bằng câu thường ("Lớp hậu kỳ: ..."), không đặt đầu dòng dưới dạng `Nhãn: ...` vì dễ bị đọc nhầm là người nói; tên cấu trúc (hook, điểm xoay) thuộc dàn ý, không đưa vào mô tả cảnh.

## Cách triển khai nội dung (thứ tự nghĩ)
1. Chọn 1 tình huống đời thường dễ thấy, có nguyên nhân người xem hiểu ngay. 2. Chọn lớp thông tin nói thay game (HUD/chữ/icon). 3. Đặt 1 nhân vật phản ứng làm cú chốt. 4. Cắt bỏ mọi thứ không phục vụ cú chốt. Khuôn là gợi ý: trộn A+B hoặc bỏ khuôn nếu ý người dùng cần khác, và nói rõ trong `notes`.
