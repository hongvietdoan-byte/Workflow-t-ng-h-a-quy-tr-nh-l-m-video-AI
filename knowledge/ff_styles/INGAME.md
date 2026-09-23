# Phong cách: Gameplay trong game (video kỹ năng, mẹo, cập nhật phiên bản)

Ví dụ nội bộ OB55: Tình huống sử dụng Kenta, Combo Kenta, Combo ném lựu lửa, Lựu đạn dò, Túi cứu thương, Điều chỉnh vũ khí, Top 3 mở trạm, Tối ưu ngựa.

## Cách dựng
- **Mở lạnh** bằng khoảnh khắc đắt nhất (pha hạ gục, kỹ năng) hoặc nhân vật tạo dáng ở sảnh + **tiêu đề lớn chữ vàng**, rồi mới vào nội dung.
- **Thân** chia chương; **mỗi chương mở bằng một câu chữ vàng** (tên tình huống hoặc câu giải thích) giữ trên cả chuỗi shot.
- Gần như toàn bộ là **camera game — góc thứ ba sau lưng nhân vật (`GAME_TPS`)**, giữ nguyên giao diện game (HUD, "Monster Kill", bảng hạ gục) như phần thưởng cho người xem.
- Chèn shot rất ngắn 0,3–0,5s: ống ngắm cận, hiệu ứng kỹ năng/flash làm chuyển, khoảnh khắc lộ địch/hạ gục.
- Video so sánh phiên bản: **màn hình chia đôi** trên/dưới, nhãn phiên bản cố định, shot dài 6–13s cho người xem kịp so.
- Con số then chốt thành chữ lớn giữa màn hình ("3 GIÂY"); thông số: xanh = tăng, đỏ = giảm.
- **Kết** bằng nhân vật trình diễn ở sảnh + câu hỏi kêu gọi + ngày cập nhật (hoặc kết mở bằng một pha gameplay).

## Look
Render gốc của game, màu tươi bão hòa, trời xanh; sảnh nền tím; chữ vàng/trắng viền đen font game.

## Khi dùng cho AI video
Model video khó tái tạo HUD đúng — ưu tiên đặt chữ/giao diện bằng hậu kỳ (card, phụ đề) thay vì bắt model vẽ. Góc `GAME_TPS` cần mô tả rõ: camera sau lưng, cao hơn vai, nhân vật ở 1/3 dưới khung.

> Các con số dưới đây là **khoảng tham khảo** đo từ video Free Fire thật, không phải nhịp cố định: độ dài từng shot do kịch bản quyết định (beat, câu thoại, cảm xúc). Dùng chúng để biết shot kiểu gì thường dài/ngắn cỡ nào và phong cách này hay dùng cỡ cảnh, chuyển động, chữ trên hình ra sao.

## Số liệu (Gameplay trong game)
- **8 video, 82 shot, 288s** · video dài trung vị 35s · **17 shot/phút**
- Độ dài shot: phần lớn 1.3–5.1s (trung vị 3.0s; 10% ngắn nhất ≤ 0.4s, 10% dài nhất ≥ 7.6s)
- Độ dài theo vai trò (khoảng p25–p75): hành động 1.4–5.4s; chèn chi tiết 0.4–2.4s; kết 1.6–7.5s; thiết lập 3.3–5.7s; mở móc 2.3–5.0s; chuyển 0.3–0.3s
- Vai trò: hành động 50%, chèn chi tiết 13%, kết 12%, thiết lập 8%, mở móc 8%, chuyển 7%
- Cỡ cảnh: camera game (góc thứ ba sau lưng) 79%, đồ họa / tiêu đề toàn khung 10%, toàn 6%, cận đặc tả 4%, trung cận 1%
- Chuyển động máy: track 54%, static 39%, push_in 4%, whip 2%, pan 1%
- Chữ trên hình 54% shot · giao diện game 90% · hiệu ứng 39%
- Mở bằng: mở móc ×5, thiết lập ×3 · kết bằng: kết ×8

## Nguồn đã phân tích (8 video)
- So sánh túi cứu thương OB54/OB55 (nội bộ) (nội bộ)
- Combo Kenta — Leo rank cùng Keo Lì (nội bộ OB55) (nội bộ)
- Combo ném lựu lửa — Leo rank cùng Keo Lì (nội bộ OB55) (nội bộ)
- Điều chỉnh vũ khí tỉa và trường OB55 (nội bộ) (nội bộ)
- Lựu đạn dò OB55 (nội bộ) (nội bộ)
- Tình huống sử dụng Kenta OB55 (nội bộ) (nội bộ)
- Tối ưu ngựa OB55 (nội bộ) (nội bộ)
- Top 3 cách mở trạm vật phẩm (nội bộ) (nội bộ)
