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

### Đã giải quyết 06/10/2026 (0 USD; CSDL sao lưu trước ở `data/backup/manifest.before_kho_redo_2026-10-06.sqlite`)
Cách làm: Claude trích khung bằng ffmpeg quanh mốc gốc, tự nhìn từng khung, cắt sát. Không có hàm thay file ảnh tại chỗ trong `core/assets.py` → ảnh mới thêm vào CÙNG mục bằng `assets.add_image` (PIPELINE_DB = CSDL máy chính, file nằm ở `D:\AI-Video-Pipeline\data\assets`) rồi `kho_review.claude_approve`; ảnh cũ giữ nguyên `pending` + ghi thêm `reject` "đã thay bằng ảnh N" (không xóa dòng/file). File nguồn của ảnh mới: `data/ref_kelly/khung_sach/*_v2.png`. Âm thanh: ghi đè cùng tên file trong nguồn id 2 (giữ dòng `sounds`/id; đổi tên thì quét nguồn sẽ xóa dòng cũ), bản cũ chép sang `data/backup/kho_am_thanh_before_2026-10-06/`, `sound_lib.scan` + `analyze`, rồi `claude_approve_sound`; `NGUON.tsv` ghi mốc mới (tên file vẫn mang mốc cũ).

| id cũ | Kết quả | Mốc mới | Ghi chú |
|---|---|---|---|
| 1074 | Đã giải quyết 06/10: ảnh mới **1108** `claude_ok` | 7631554808293362945 @1,4 s | cắt riêng ô vũ khí chính (29/30, Reload); 2 ô dưới luôn có nền nội thất xuyên qua + chữ 10M/30M ở mọi khung nên bỏ; vệt chéo mờ còn rất nhẹ |
| 1087 | Đã giải quyết 06/10: ảnh mới **1109** `claude_ok` | 7595101706216836369 @0,6 s | clip gốc 7658256651924917525 huy hiệu luôn đè lên ảnh quay thật (cây, tường chữ FREE FIRE) → lấy huy hiệu tím 2 sao trên thẻ trắng nền trơn của clip "My rank" |
| 1089 | Đã giải quyết 06/10: ảnh mới **1110** `claude_ok` | 7595101706216836369 @3,0 s | thẻ đứng thẳng, huy hiệu vàng trọn trên nền trắng, không chữ "My rank"/số |
| 1090 | Bỏ (giữ loại) 06/10 | (khung tốt nhất 7670451475671289109 @12,8 s) | khung không emoji/chữ ở 12,8 s vẫn mờ do clip phóng to; cùng mẫu huy hiệu với ảnh mới 1110 (sắc nét hơn); mục 403 đã đủ 6 ảnh |
| 1091 | Đã giải quyết 06/10: ảnh mới **1111** `claude_ok` | 7619299701422050576 @1,2 s | icon pin 1 % bên TRÁI trọn khung trên tường trơn (icon bên phải luôn có vệt sáng dọc phía sau) |
| 1093 | Đã giải quyết 06/10: ảnh mới **1112** `claude_ok` | 7670451475671289109 @12,4 s | khung đã phóng to vào màn hình: thẻ hồ sơ (Maxim, Lv.52, huy hiệu, Heroic Emblem, chữ ký) không viền máy/ngón tay; mép phải thẻ do clip cắt |
| 1097 | Bỏ hẳn 06/10 (giữ loại) | — | trùng bố cục với 1096, theo phương án |
| 1102 | Đã giải quyết 06/10: ảnh mới **1113** `claude_ok` | 7592454501462772993 @3,0 s | cắt riêng thân máy đấm bên trái: không logo/áp phích Jujutsu, không dòng bản quyền, không nhân vật; máy bị khung clip cắt mép trái (clip không có khung nào thấy trọn máy) — cần máy trọn thì dựng 3D |
| 1104 | Đã giải quyết 06/10: ảnh mới **1114** `claude_ok` | 7595876646343806225 @9,65 s | chip HUD "2 Kelly" + đầu lâu có suốt cảnh 9,5–10,1 s → cắt từ dưới chip (mặt + thân trên sạch) |
| 1106 | Đã giải quyết 06/10: ảnh mới **1115** `claude_ok` | 7663436199532629269 @12,8 s | trước khi emoji hiện (13,2 s); cắt riêng Kelly, bỏ nhân vật bím tóc tím |
| âm thanh 907 funk pila | Đã giải quyết 06/10: ghi đè file, `claude_ok` | 0–19 s | trích lại từ clip, hạ 8 dB trước khi mã hóa: đỉnh -5,5 dBFS, RMS -15,9 dB, 0 % mẫu chạm trần (bản cũ đỉnh +0,5 dBFS). Bản trộn gốc vốn nén rất mạnh (đỉnh/RMS chỉ ~10 dB) — không sửa được phần đó |
| âm thanh 910 Triple kill | Đã giải quyết 06/10: ghi đè file, `claude_ok` (cần người nghe) | 10,3–11,6 s | lớp giọng demucs lẫn lời bài hát, whisper không nghe ra ở mọi mốc thử; bản TRỘN 10,3–11,6 s: whisper medium nghe "TRIPLE KILL!"; có nhạc nền nhỏ dưới; đỉnh -1,8 dBFS, RMS -15,7 dB |
| âm thanh 912 Unstoppable | Đã giải quyết 06/10: ghi đè file, `claude_ok` | 9,6–11,8 s | đo đường bao: giọng bắt đầu 9,7 s (bản cũ 10,2 s → cụt); lớp giọng demucs, whisper small + medium nghe "UNSTOPPABLE!"; đầu đoạn -53 dB, đỉnh -1,8 dBFS, RMS -14,6 dB |

## Pending KHÔNG thuộc S14.33 (liệt kê, không đụng)
37 ảnh `pending` khác vẫn chờ người dùng: KELLY 7, KENTA 3, MAXIM 6, WOLFRAHH 1 (người dùng tạo) và 20 ảnh của mục tự đồng bộ (`auto-sync`): burger 3, cong 3, cong dich chuyen 5, khu vuc nha kinh 5, mini Map 1, vung khong trong luc 3.

## Cách dùng danh sách
- Mỗi lượt duyệt tầng A sau này NỐI THÊM một mục "Lượt N — <nguồn>" với bảng cùng cột (id, loại, nguồn clip + mốc giây, lỗi, phương án, ước giá). Không sửa dòng cũ; khi đã giải quyết thì thêm cột/ghi chú "đã xử lý <ngày>".
- Gọi `kho_review.reject(conn, "image"|"sound", id, lý do)` để ghi nhật ký (không xóa); `kho_review.rejected(conn, kind)` liệt kê các mục đang bị loại. Một lần `claude_approve` sau đó (ví dụ sau khi làm lại) tự đưa mục khỏi danh sách loại.
- Chỉ thu hồi (`revoke`) mục `claude_ok`; mục `approved` của người dùng không bị Claude hạ.
