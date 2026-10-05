# Danh sách tài nguyên Kho bị Claude loại ở tầng A (S14.42, 05/10/2026)

Quy ước duyệt 3 tầng (core/kho_review.py): `pending` → `claude_ok` (Claude nhìn/nghe, dùng được, hiện dấu "Claude duyệt") → `approved` (người dùng xác nhận).
Mục bị loại KHÔNG bị xóa: ảnh giữ `pending` (không dùng được), âm thanh giữ trong nguồn nhưng không được gợi ý nhạc nền; lý do ghi ở bảng `kho_review_log` (action `reject`).
Chưa giải quyết ngay — gom đủ nhiều rồi làm một lượt.

## Lượt 1 — Kho S14.33 (kênh Kelly), áp dụng ngày 05/10/2026
Kết quả: 23/33 ảnh `claude_ok`, 10 ảnh bị loại; 14/17 âm thanh `claude_ok`, 3 bị loại.
Lưu ý: 33 file ảnh của mục 396–413 không có trên đĩa (data/assets/396..413 trống) dù hàng CSDL còn; đã khôi phục bằng cách chép lại từ `src_path` (khớp sha256 cả 33 file) trước khi xem.

### Ảnh
| id | Loại | Nguồn (clip + mốc) | Lỗi | Phương án đề xuất | Ước giá |
|---|---|---|---|---|---|
| 1074 (mục 396 HUD ô vũ khí) | HUD | 7631554808293362945 @0,8 s | nền bẩn: vệt đen chéo, mảnh chữ ở mép dưới, nền nội thất, chữ đỏ 30M | trích lại khung khác của cùng clip (thử 0,4–1,5 s) rồi cắt sát khung HUD | 0 |
| 1087 (mục 403 huy hiệu hạng) | HUD | 7658256651924917525 @7,8 s | cảnh quay thật có người + tranh tường nhân vật bên thứ ba; hai huy hiệu tím lẫn nền | cắt riêng từng huy hiệu từ khung này hoặc trích khung khác khi huy hiệu nằm trên nền trơn; nếu vẫn lẫn nền thì bỏ hẳn (đã có huy hiệu đỏ 1088) | 0 |
| 1089 (mục 403) | HUD | 7595101706216836369 @1,7 s | huy hiệu vàng bị cắt mép trên/trái, dính chữ "My ra" và thẻ trắng | trích khung khác (gần 1,7 s) khi huy hiệu đủ khung, hoặc bỏ hẳn nếu clip không có khung sạch | 0 |
| 1090 (mục 403) | HUD | 7670451475671289109 @13,8 s | phóng to mờ, dính chữ Lv.52 / BATTLE ROYALE, biểu tượng dưới bị cắt | trích khung khác ở mốc 12–14 s với huy hiệu Heroic 100 trọn vẹn rồi cắt sát | 0 |
| 1091 (mục 404 pin yếu) | HUD | 7619299701422050576 @0,6 s | icon pin 1 % bị cắt ngang thân ở mép dưới/phải, vệt sáng dọc | trích khung ±0,3 s khi icon nằm trọn khung; hoặc bỏ hẳn (đã có ảnh điện thoại 1092) | 0 |
| 1093 (mục 405 hồ sơ người chơi) | UI | 7670451475671289109 @12,2 s | chụp qua màn hình điện thoại: viền máy + ngón tay, mép trái bị cắt | cắt riêng phần màn hình trong điện thoại (bỏ viền/ngón tay) hoặc dựng lại bằng ảnh UI của người dùng | 0 |
| 1097 (mục 407 bảng điểm) | HUD | 7667531129209097493 @4,5 s | trùng bố cục với 1096 (chỉ khác số điểm) | bỏ hẳn | 0 |
| 1102 (mục 411 máy đấm hơi) | Vật | 7592454501462772993 @5,2 s | dính logo JUJUTSU AWAKENING, áp phích Jujutsu, dòng bản quyền Gege Akutami/Shueisha (IP bên thứ ba) | KHÔNG thu khung này; trích khung khác của máy đấm không logo (nếu clip luôn có logo thì dựng lại máy đấm bằng Blender, đã có quy trình 3D) | 0 (Blender); Meshy khoảng 0,1–0,3 USD nếu dùng |
| 1104 (mục 413 biểu cảm Kelly sốc) | Biểu cảm | 7595876646343806225 @10,1 s | chip HUD "2 Kelly" + đầu lâu đè lên khung | trích khung khác ở 9,8–10,6 s khi HUD chưa hiện, hoặc cắt ngang vai | 0 |
| 1106 (mục 413 Kelly và nữ chính shock) | Biểu cảm | 7663436199532629269 @13,6 s | sticker emoji đè đầu; thêm nhân vật thứ hai làm lẫn | trích khung khác ngay trước/sau khi emoji hiện; hoặc bỏ hẳn | 0 |

### Âm thanh (nguồn id 2, data/ref_kelly/kho_am_thanh)
| id | Loại | Nguồn (clip + mốc) | Lỗi | Phương án đề xuất | Ước giá |
|---|---|---|---|---|---|
| nhạc "funk pila sôi động" (0-19s) | nhạc | 7670451475671289109 @0–19 s | méo/vỡ tiếng: 12,6 % mẫu chạm trần, RMS -5 dB | tải/trích lại đoạn gốc rồi hạ gain trước khi mã hóa (không để bản đã vỡ); hoặc bỏ hẳn | 0 |
| giọng "Triple kill" | giọng thông báo | 7595876646343806225 @10,4–11,5 s | nghe ra chỉ "Oh", không phải câu Triple kill | cắt lại: nghe lại stem giọng quanh 9,5–12,5 s, chọn mốc đúng; kiểm bằng faster-whisper | 0 |
| giọng "Unstoppable" | giọng thông báo | 7647055543156133137 @10,2–12,4 s | mở đầu cụt (-10 dB tới -47 dB), nhận ra "STOP A BALL", vỡ nhẹ | cắt lại với mốc bắt đầu sớm hơn ~0,3 s; kiểm lại bằng whisper | 0 |

## Pending KHÔNG thuộc S14.33 (liệt kê, không đụng)
37 ảnh `pending` khác vẫn chờ người dùng: KELLY 7, KENTA 3, MAXIM 6, WOLFRAHH 1 (người dùng tạo) và 20 ảnh của mục tự đồng bộ (`auto-sync`): burger 3, cong 3, cong dich chuyen 5, khu vuc nha kinh 5, mini Map 1, vung khong trong luc 3.

## Cách dùng danh sách
- Mỗi lượt duyệt tầng A sau này NỐI THÊM một mục "Lượt N — <nguồn>" với bảng cùng cột (id, loại, nguồn clip + mốc giây, lỗi, phương án, ước giá). Không sửa dòng cũ; khi đã giải quyết thì thêm cột/ghi chú "đã xử lý <ngày>".
- Gọi `kho_review.reject(conn, "image"|"sound", id, lý do)` để ghi nhật ký (không xóa); `kho_review.rejected(conn, kind)` liệt kê các mục đang bị loại. Một lần `claude_approve` sau đó (ví dụ sau khi làm lại) tự đưa mục khỏi danh sách loại.
- Chỉ thu hồi (`revoke`) mục `claude_ok`; mục `approved` của người dùng không bị Claude hạ.
