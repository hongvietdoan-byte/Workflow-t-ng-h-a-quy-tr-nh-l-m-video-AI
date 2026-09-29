# 17 — STALLED (Omeleto)

- **URL**: https://www.youtube.com/watch?v=7mSH86O2qzA
- **Thể loại**: phim ngắn live-action 16:9, **hài khoa học viễn tưởng vòng lặp thời gian** trong nhà vệ sinh công ty (một nhân viên kẹt trong buồng vệ sinh trước
  cuộc họp quan trọng, gặp nhiều "phiên bản" của chính mình) — mục 2.3 trong `MAU_S0_12.md`
- **Độ dài công bố**: 19:55 · file tải 1280×720
- **Đoạn đã đo**:
  - (1) 0:00–3:00 (180.0s; 0–4.63s màn đen + logo Omeleto);
  - (2) yêu cầu 13:50–16:20 (đấu súng giữa các phiên bản) — file 160.0s, bắt đầu sớm ~10s (keyframe) → mốc gốc ≈ 13:40 + t **[ước tính]**.
- **Tổng đã đo**: ~335s / 1195s (~28%)
- **Đã tải**: `v17_seg1.webm`, `v17_seg2.webm`, khúc quét 144p 3:00–19:55 (1 khung/10s) — **tất cả đã xoá**.

## Cách chọn đoạn
Tờ quét 102 khung: cả phim trong một nhà vệ sinh xanh lục / xanh lam; giấy dán tường viết tay "you're trapped in a time loop" (6:40–7:00), mũi tên vẽ trên tường
(9:30–10:10), súng xuất hiện từ ~15:00. Chọn 13:50–16:20 = cao trào nhiều phiên bản chĩa súng vào nhau.

## Phương pháp
Như 11 (`motion_cv2b.py`); `tools/audio_listen.py --lang en` đoạn 1 giây 0–90, đoạn 2 giây file 10–100.
**Cảnh báo đo**: hình tối, tông lục đơn sắc → ở ngưỡng 0.25 đoạn 1 chỉ ra 22 shot, trong đó **shot 2 dài 91.6s (4.6–96.3s)**. Tờ quét 3:00–3:20 cho thấy cùng
một khung (CU người đàn ông trong buồng) → **[có thể] là một cảnh quay dài thật** (gọi điện thoại, máy tịnh tiến theo).
**Kiểm lại ở ngưỡng 0.10**: 29 shot, trung vị 2.96s; shot 2 tách thành 4.6–8.6s (4.0s) + **8.6–96.3s = 87.7s, máy tịnh tiến** — vẫn không có cắt → **[khá] một cảnh
dài 87.7s** (cần mắt xem ≥ 5 khung/giây để chắc). Cụm 125.4–129.6s ở ngưỡng 0.10 tách thêm 4 shot 0.4–0.6s (có thể là chớp đèn).

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| Mở đầu 0:00–3:00 (ngưỡng 0.25) | 22 | 3.24s | 1.12–**91.63s** | 7.3 | tĩnh 73%, tịnh tiến 14%, zoom out 9%, roll 5% |
| Mở đầu 0:00–3:00 (**ngưỡng 0.10, dùng số này**) | 29 | **2.96s** | 0.37–**87.67s** | 9.7 | tĩnh 62%, tịnh tiến 14%, zoom out 10%, roll 10%, thiếu dữ liệu 3% (đếm từ danh sách shot) |
| Đấu súng (file 160s) | **86** | **0.75s** | 0.33–22.11s | **32.2** | tĩnh 17%, tịnh tiến 21%, **roll 21%**, zoom out 12%, zoom in 7%, thiếu dữ liệu 22% |

- Âm thanh: LUFS **−23.3** / **−20.9**, LRA **17.9** / **11.5 LU**; quãng lặng **48** / **1**.
- **Tỉ lệ nhịp mở ↔ cao trào lớn nhất trong 17 video**: trung vị 2.96s (ngưỡng 0.10) → **0.75s** (×3.9); đoạn 2 có 50 shot ≤ 0.5s trong 79–155s. Máy gần như không bao giờ đứng yên
  ở cao trào (tĩnh 17%, roll 21% — máy cầm tay / nghiêng).

### Nghe bằng số (audio_listen)
- **Đoạn 1**: nhạc 69%, mức thấp −44…−52 dB (nền rất nhỏ), trồi −31…−35 dB từng nhịp ở 22, 36, 44, 58, 68s. **Nhãn "Tick / Tick-tock" 0.13–0.36 lặp lại ở 10, 12,
  62, 64, 76, 78, 82, 88s** và "Mechanisms / Gears" 0.13–0.31 (26, 30, 50, 52, 58, 84s) → [có thể] một **lớp tiếng đồng hồ tích tắc** chạy dưới cuộc gọi "anh trễ
  rồi" — chưa nghe tai. Tiếng vòi nước / bồn rửa 0.15–0.22 (48, 54, 72s).
- 0–4.7s lặng (logo); giọng bình luận thể thao trên radio 0.6–7.6s mở phim.
- **Đoạn 2**: nhạc **100%**, lớn dần: −47 dB (10s) → −25 (34s) → **−20 dB ở 68s** rồi giữ −22…−30 tới hết khúc; chỉ **1 quãng lặng** trong 160s — đối lập đoạn 1
  (48 quãng). Thoại chồng nhau, nhanh ("we just keep creating more paradoxes").

## Bảng shot — đoạn 1 (0:00–3:00, ngưỡng 0.25)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1 | 0.0–4.6 | màn đen + logo | — | tĩnh | lặng |
| 2 | 4.6–96.3 | MCU người đàn ông cầm điện thoại, đi vào nhà vệ sinh (**91.6s — chưa chắc là một cảnh**) | ngang | tịnh tiến | radio thể thao; gọi "anh trễ rồi", "cửa của tôi mở"; tích tắc |
| 3–8 | 96.3–132.7 | CU ông lão lao công ↔ MS hai người; insert cuộn giấy | ngang | zoom out×1, roll×1, tĩnh×4 | lặng 96.9–107.8 (4 quãng) |
| 9–13 | 132.7–147.0 | MS ngồi trong buồng; **insert đồng hồ đeo tay** (#12) | ngang; #10 cao | tịnh tiến×1, zoom out×1, tĩnh×3 | lặng dày 139–149s |
| 14–22 | 147.0–180.0 | insert chân dưới vách buồng; insert chốt cửa; **insert giấy "Don't PANIC"** (#19); MS | thấp (#16, #21 ngang sàn) | tịnh tiến×1, tĩnh×8 | lặng 149–170s (nhiều quãng) |

## Bảng shot — đoạn 2 (giây file; ≈ 13:40 + t)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–2 | 0.0–34.6 | WS nhà vệ sinh — hai phiên bản đứng hai đầu (22.1s, roll); MS lưng (12.5s) | ngang | roll×1, tĩnh×1 | cãi nhau "moron / idiot"; nhạc nhỏ |
| 3–14 | 34.6–79.0 | MS các phiên bản lần lượt bước ra (#9 hai người một khung); WS cửa buồng | ngang | tịnh tiến×1, zoom out×1, tĩnh×9, roll×1 | "last requests"; nhạc trồi 34s, 54s, **68s −20 dB** |
| 15–27 | 79.0–99.7 | **tông xanh lam**: CU một phiên bản ngửa mặt, tay chĩa súng vào cằm; shot 0.4–2.1s | thấp | roll×4, zoom out×1, tĩnh×4, thiếu dữ liệu×4 | nhạc đều −22…−29 |
| 28–75 | 99.7–143.1 | **tông lục**: MCU các phiên bản giơ tay / rút súng / chĩa súng — **48 shot, đa số 0.3–1.1s** | **thấp nhìn lên** (#61–66, #74–77) | tịnh tiến×17, roll×12, zoom×9, thiếu dữ liệu×10 | "time to close some doors" |
| 76–86 | 143.1–160.0 | MCU chĩa súng thẳng máy; tối dần | thấp | zoom out×5, zoom in×2, thiếu dữ liệu×3, roll×1 | — |

## Kỹ thuật đáng học
1. **Nhịp cắt đổi ×4 giữa thiết lập và cao trào** (3.24s → 0.75s; 50 shot ≤ 0.5s trong 76s). Ý đồ **[có thể]**: thiết lập chậm, dài (có thể một cảnh dài 91s) để
   người xem "kẹt" cùng nhân vật; cao trào vỡ vụn thành mảnh như chính nghịch lý thời gian. Độ tin: chắc về số đo — cùng chiều với 02, 03, 09 (mẫu hình 1).
2. **Âm thanh đi từ thưa (48 quãng lặng) sang liền một khối (1 quãng lặng, nhạc 100% lớn dần tới −20 dB)**. Ý đồ **[có thể]**: nhạc là "đồng hồ" đẩy áp lực.
   Độ tin: có thể.
3. **Motif tiếng tích tắc / bánh răng dưới cảnh mở** (nhãn Tick-tock 0.13–0.36 ở 8 cửa sổ, Mechanisms 0.13–0.31 ở 6 cửa sổ) + insert đồng hồ đeo tay (#12). Ý đồ
   **[có thể]**: gieo chủ đề "thời gian" trước khi truyện nói ra. Độ tin: **đoán** (nhãn AST điểm thấp; chưa nghe tai).
4. **Màu tách phiên bản / thời điểm**: khúc xanh lam (79–99.7s) ↔ khúc xanh lục (99.7s trở đi) trong cùng một nhà vệ sinh. Ý đồ **[đoán]**: giúp người xem phân
   biệt các "vòng" khi cùng một diễn viên đóng mọi vai. Độ tin: đoán — cần xem trọn.
5. **Góc thấp nhìn lên + súng chĩa thẳng ống kính** ở cao trào (#61–66, #74–77, #86). Ý đồ **[có thể]**: đặt người xem vào đầu nòng súng — đe doạ trực diện.
   Độ tin: có thể.
6. **Chữ viết tay trong hình kể luật chơi** (giấy "Don't PANIC" 161s; tờ quét: "you're trapped in a time loop…", mũi tên trên tường). Ý đồ **[có thể]**: giải thích
   cơ chế vòng lặp mà không cần giọng kể. Cùng họ với lớp chữ trong hình của 11, 13 (giao diện) nhưng là **đạo cụ trong truyện**.

## Giới hạn / câu hỏi mở
- Shot 2 dài 91.6s chưa được xác minh là một cảnh (tương phản thấp). Nếu là một cảnh thì đó là "một cảnh dài mở phim" — khác mọi mẫu khác.
- Tiếng tích tắc là nhãn AST điểm thấp — cần nghe tai.
- Chỉ xem 2 đoạn; phần giải thích vòng lặp (6:00–13:00) chỉ thấy qua tờ quét.

## Xoá dữ liệu
**CHƯA XOÁ** (lệnh shell bị chặn khi viết file): còn `v17_seg1.webm`, `v17_seg2.webm`, `v17_seg*_frames/`, tờ ảnh, thư mục `v17_seg*_L*/` và log trong
`scratchpad/s012` — phải chạy `bash clean.sh v17`. Sau khi dọn chỉ giữ `v17_seg{1,2}_result.json` (và
`v17_seg1b_result.json` nếu kiểm lại xong), `v17_seg1_L0_numbers.json`, `v17_seg2_L10_numbers.json` (không lời chép).
