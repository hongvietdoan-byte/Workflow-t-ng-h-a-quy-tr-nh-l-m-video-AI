# 04 — 《我的婆婆是軟柿子》(畫境故事 Painted Realm Stories)

- **URL**: https://www.youtube.com/watch?v=9gFRf8dFWbI
- **Thể loại**: AI short drama 9:16, bối cảnh thời đại (thập niên 80, theo `MAU_S0_12.md`), toàn tập gộp
- **Độ dài công bố**: 2:02:37 (7357s) · khung 360×640 (9:16)
- **Đoạn đã đo**: (1) 0:00–3:00 (mở đầu, 180.0s) · (2) 43:30–45:40 (đoạn "lật ngược", 130.0s — tìm bằng tờ ảnh thưa 1 khung/20s quét khúc 40:00–50:00, chọn đúng lúc phát hiện hộp thư tình cũ)
- **Tổng đã đo**: 310s / 7357s (~4.2%)
- **Đã tải**: `v04_seg1_9gFRf8dFWbI.webm` (6.7 MB) + `v04_seg2_9gFRf8dFWbI.webm` (5.3 MB) + 1 khúc quét thưa 480p 10 phút (đã xoá ngay sau khi chọn xong đoạn, không phân tích chi tiết) — **tất cả đã xoá sau khi viết xong file này**.

## Cách tìm đoạn "lật ngược" (cải tiến lượt 3, theo hướng dẫn phiên chính)
Tải khúc 40:00–50:00 ở 480p, dùng `ffmpeg fps=1/20` + `tile=6x5` ra 1 tờ ảnh 30 khung (mỗi khung cách nhau 20s, có mốc giờ). Đọc bằng mắt thấy: 42:00–43:20 có xung đột ngoài đường ("就凭我是周浩瀚的老婆" — tôi là vợ của Chu Hạo Hàn, bị tố "truyền tin đồn"); 44:00–45:20 mở ra một **hộp thiếc đựng thư tay cũ** rồi một **máy cát-xét phát giọng ghi âm** — rõ ràng là một khoảnh khắc xúc động/lật ngược (tiết lộ tình cảm giấu kín). Tải đúng khúc 43:30–45:40 để phân tích chi tiết — **cách này nhanh và chính xác hơn hẳn việc đoán theo tỉ lệ % thời lượng đã dùng sai ở video 02 lượt trước**.

## Phương pháp
Giống video 01–03 (cắt/tờ ảnh/LUFS-LRA-quãng lặng, bỏ báo cáo đỉnh) + bổ sung lượt 3: **chuyển động máy per-shot bằng OpenCV** (xem mô tả đầy đủ ở file `05_rise_worlds2018.md` mục Phương pháp) và **phổ âm thanh** (`showspectrumpic`, khúc 60s) đọc bằng mắt.

## Số đo
| Đoạn | Shot | Độ dài trung vị | Máy (OpenCV) |
|---|---|---|---|
| Mở đầu 0:00–3:00 | 76 | 2.04s | tĩnh 76%, tịnh tiến 22%, roll 1% |
| Lật ngược 43:30–45:40 | 48 | 2.15s | tĩnh 83%, tịnh tiến 13%, thiếu dữ liệu 4% |

- Âm thanh: LUFS đoạn 1 **−13.4**, đoạn 2 **−13.5** (LRA 5.3 và 8.7 LU). Quãng lặng: 3 và 2 lần — ít hơn hẳn video 01 (46+33 trong cùng độ dài) dù cùng là AI short drama thoại nhiều — **[có thể]**: khác biệt giữa 2 kênh khác nhau, không phải quy luật chung của thể loại (mâu thuẫn với giả thuyết trước — cần ghi rõ trong `TONG_HOP.md`).
- **Camera gần như hoàn toàn tĩnh (76–83%)** — khớp hướng của video 01 (thoại nhiều → máy tĩnh chiếm đa số), nhưng **tỉ lệ tĩnh ở video 04 thấp hơn** (76–83% so với ước lượng ~98% của DRAMA_DOC tham khảo) — có thể do đo bằng OpenCV nhạy hơn với rung nhẹ/zoom rất chậm mà mắt thường không nhận ra, không hẳn là khác biệt phong cách thật.

### Đọc phổ âm thanh
- Cả 2 đoạn: kết cấu **chủ yếu vạch dọc dày đặc, không thấy vệt ngang bền vững nhiều tầng rõ rệt** như video 05 (RISE) — khác biệt rõ so với RISE (nơi thấy hoà âm rõ). **Kết luận [có thể]**: video này hoặc không có nhạc nền rõ, hoặc nhạc rất nhỏ/bị thoại che gần hết phổ — **không đủ bằng chứng thị giác để khẳng định có nhạc**, khác hẳn RISE. Độ tin: có thể (kết cấu phổ nhất quán qua cả 5 khúc 60s đã xem của video 01 và 04 — 2/2 video AI short drama thoại-nhiều đều cho kết quả tương tự, đủ điều kiện ghi vào `TONG_HOP.md`).
- Một chi tiết nhỏ đáng chú ý: đoạn "lật ngược" (mở hộp thư, máy cát-xét) — dù nội dung hình cho thấy một máy cát-xét đang phát, **phổ âm ở đúng đoạn đó (giây ~97–110 của đoạn 2) không cho thấy dấu hiệu nhạc/giọng nói khác biệt rõ so với phần còn lại** — có thể giọng ghi âm phát ra từ cát-xét chỉ là một giọng nói (không phải nhạc), khớp với việc phổ vẫn là "vạch dọc dày đặc" kiểu thoại.

## Bảng shot — đoạn 1 (0:00–3:00, 76 shot, đủ mốc/cỡ cảnh/máy riêng từng shot)
| # | Vào–ra | Cỡ cảnh chủ đạo | Máy (OpenCV) | Nội dung |
|---|---|---|---|---|
| 1 | 0.0-1.6 | CU | tĩnh | Nữ chính uống nước, độc thoại nội tâm |
| 2–4 | 1.6-9.2 | CU/insert | tĩnh + 1 tịnh tiến | Cận sổ tay viết tay; "giao ước mười mấy năm trước" |
| 5–8 | 9.2-14.0 | CU/WS | tịnh tiến×2 + tĩnh×2 | Sân làng, nhóm đàn ông tụ tập, hỏi "tìm ai" |
| 9–13 | 14.0-25.5 | CU/insert | tĩnh | Cận tờ giấy đỏ/thông báo, "con trai thứ hai" |
| 14–17 | 25.5-38.3 | CU/insert | 1 tịnh tiến + tĩnh | Nữ chính giơ cao tờ giấy viết tay đọc to |
| 18–20 | 38.3-46.7 | CU | tĩnh | Đối thoại căng, "trưởng thôn bênh con gái ông ta" |
| 21–26 | 46.7-66.1 | CU/WS | 1 tịnh tiến + tĩnh | Nữ chính cầm gậy đe doạ nhóm đòi tiền |
| 27–30 | 66.1-71.9 | WS/CU | tĩnh | Nhóm người chạy đi, nữ chính đứng một mình |
| 31–33 | 71.9-75.4 | CU | 1 tịnh tiến + tĩnh | Chuyển bối cảnh sang quán ăn |
| 34–36 | 75.4-79.7 | WS/insert | 2 tịnh tiến + tĩnh | Người đàn ông vest bước vào quán |
| 37–48 | 79.7-106.3 | CU | 2 tịnh tiến + tĩnh | Cảnh xem mắt: "phó giáo sư đại học tỉnh" ngỏ lời cưới, nữ nghi ngờ |
| 49–60 | 106.3-135.9 | CU | 2 tịnh tiến + tĩnh | "Anh coi tôi là quả hồng mềm à", kể chuyện gia đình sau khi cha mất |
| 61–64 | 135.9-149.3 | CU/insert | tĩnh | Cận tiền mặt — "nửa năm lương 240 tệ" |
| 65–70 | 149.3-163.8 | CU/WS | 4 tịnh tiến + tĩnh | Tiếp tục nói chuyện sính lễ; toàn cảnh đi ngoài đường |
| 71–76 | 163.8-180.0 | WS/CU | 2 tịnh tiến + 1 roll + tĩnh | Cổng trụ sở xã, nữ chính cầm sổ hộ khẩu, "anh không cam lòng" |

## Bảng shot — đoạn 2 (43:30–45:40, 48 shot)
| # | Vào–ra | Cỡ cảnh chủ đạo | Máy (OpenCV) | Nội dung |
|---|---|---|---|---|
| 1–6 | 0.0-23.1 | CU/WS | tĩnh | Đối thoại căng: "tôi mới chả tiếc", "tôi bảo đảm sẽ không mềm nữa" |
| 7–11 | 23.1-39.2 | CU/WS | tĩnh | "Chuyện gì?"; toàn cảnh quán đêm; "anh mở xem đi" |
| 12–17 | 39.2-49.8 | insert/CU | tĩnh | Cận hộp thiếc thư cũ, "tôi viết cho em", "không dám nói trực tiếp" |
| 18–24 | 49.8-65.0 | insert/CU | tĩnh | Lật từng lá thư viết tay, "lần đầu anh gặp em" |
| 25–30 | 65.3-80.2 | CU/insert | tĩnh | Tiếp tục đọc, "chữ đẹp như con dấu", "anh viết lúc nào" |
| 31–36 | 80.2-94.2 | CU | tĩnh | "Mỗi ngày một lá", "để anh đi cùng em đến già" |
| 37–42 | 94.2-111.8 | insert/CU | tĩnh | Cận tay lấy máy cát-xét từ hộp, đặt lên bàn |
| 43–48 | 111.8-130.0 | CU | tĩnh | Máy phát "từ ngày yêu em bắt đầu"; nữ bật khóc; "không phải anh nói dối em" |

## Kỹ thuật đáng học
1. **Tìm đoạn lật ngược bằng tờ ảnh thưa 1 khung/20s** — nhanh (1 lượt tải 480p + 1 lệnh ffmpeg) và chính xác hơn hẳn đoán theo tỉ lệ % — nên dùng cách này cho mọi video gộp dài còn lại (đã áp dụng lại ở video 06, 07 bên dưới).
2. **Camera tĩnh áp đảo (76–83%) xuyên suốt cả đoạn xung đột lẫn đoạn xúc động** — khác video 02/03/05 (đổi nhịp cắt VÀ chuyển động máy theo kịch tính) — video AI short drama (01, 04) dùng thoại/nội dung để tạo cảm xúc, gần như không dùng chuyển động máy làm công cụ kể chuyện. Đây là **quan sát trùng giữa video 01 và 04** (2/2 video cùng nhóm thể loại) — đủ điều kiện ghi mẫu hình vào `TONG_HOP.md`.
3. **Vật thể vật lý (hộp thư, cát-xét) làm phương tiện lộ thông tin** thay vì hồi tưởng bằng hình ảnh (khác kỹ thuật "grayscale hồi tưởng" đã thấy ở DRAMA_DOC tham khảo trước) — một cách khác để kể lại quá khứ mà không cần dựng lại cảnh cũ, có thể rẻ hơn cho sản xuất AI. Độ tin: đoán, 1 mẫu.
4. **Phổ âm không cho thấy dấu hiệu nhạc rõ ở cả 2 đoạn** (giống video 01) — khác hẳn RISE — củng cố giả thuyết "AI short drama thoại nhiều có xu hướng ít/không có nhạc nền rõ, ưu tiên lời thoại" — nay có bằng chứng thị giác từ 2 video cùng nhóm.

## Giới hạn / câu hỏi mở
- Chỉ đo 310s/7357s (~4.2%) — vẫn rất ít so với toàn phim.
- Không xác nhận được máy cát-xét phát nhạc hay chỉ phát giọng nói ghi âm (phổ không phân biệt rõ) — cần nghe thật.
- Tỉ lệ "tĩnh" đo bằng OpenCV (76–83%) thấp hơn ước lượng bằng mắt trước đây (gần 100%) — có thể do ngưỡng đo còn nhạy với rung nhẹ/nén video, cần đối chiếu thêm.

## Xoá dữ liệu
Đã xoá `v04_seg1_9gFRf8dFWbI.webm`, `v04_seg2_9gFRf8dFWbI.webm`, khúc quét 480p, các thư mục `v04_seg*_frames/`, `v04_seg*_sheet_*.jpg`, `v04_seg*_spec_*.png` khỏi `scratchpad/s012` sau khi viết xong file này.
