# 18 — Night of the Foxes (Short of the Week, đạo diễn Tom Haines)

- **URL**: https://www.youtube.com/watch?v=dKKZf7fHSAY
- **Thể loại**: phim ngắn live-action 16:9, chính kịch mùa hè vùng Kent (Anh): chủ vườn táo nợ nần, rượu, con gái tuổi mới lớn và cậu thợ hái — mục 2.4 trong
  `MAU_S0_12.md`
- **Độ dài công bố**: 14:34 · file tải 1280×720
- **Đoạn đã đo**:
  - (1) 0:00–3:00 (180.0s; khung đen ngắn 15.0–15.9, 16.7–18.0s giữa các thẻ chữ);
  - (2) yêu cầu 11:20–13:50 (đêm: ông chủ vườn lấy súng ra vườn táo cầm đèn pin) — file 160.0s, bắt đầu sớm ~10s → mốc gốc ≈ 11:10 + t **[ước tính]**.
- **Tổng đã đo**: ~340s / 874s (~39%)
- **Đã tải**: `v18_seg1.webm`, `v18_seg2.webm`, khúc quét 144p 3:00–14:34 (1 khung/10s) — **tất cả đã xoá** sau khi viết file.

## Cách chọn đoạn
Tờ quét 70 khung: ban ngày vườn táo, nắng ngược (3:00–7:00) → chạng vạng, bếp (7:00–11:00) → **đêm tối trong vườn** (11:40–13:50) → chữ cuối 14:00. Chọn đêm =
đoạn căng nhất (súng, đèn pin, cáo).

## Phương pháp
Như 16, 17 (`motion_cv2b.py`, `audio_listen --lang en`). **Hình đêm rất tối + máy cầm tay + đèn pin chớp**: đoạn 2 ở ngưỡng 0.25 ra 12 shot (có shot 42s và 59s),
ở ngưỡng 0.10 ra 57 shot với 18 "shot" ≤ 0.4s — tờ ảnh cho thấy nhiều "cắt" 0.10 là **đèn pin quét / chớp** hoặc máy cầm tay đi theo trong bếp (#4–12 cùng một
góc lưng người đàn ông). Số thật nằm giữa hai ngưỡng → chỉ báo dải, không báo một trung vị.

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| Mở đầu 0:00–3:00 (ngưỡng 0.25) | 63 | **2.52s** | 0.48–9.0s | 21.0 | tĩnh 49%, **tịnh tiến 32%**, zoom in 8%, roll 6%, zoom out 5% |
| Đêm trong vườn (file 160s) | 12 (0.25) ↔ 57 (0.10) | 4.74s ↔ 1.12s | 0.3–59.2s | 4.5 ↔ 21.4 | (0.10) tĩnh 23%, zoom out 19%, tịnh tiến 12%, roll 11%, **thiếu dữ liệu 32%** (quá tối) |

- Âm thanh: LUFS **−24.0** / **−23.1**, LRA **17.9** / **19.5 LU**; quãng lặng **47** / **22**.

### Nghe bằng số (audio_listen)
- **Đoạn 1**: 0–16s **không nhạc** (−63…−75 dB) dưới **đoạn mở gồm các khung "báo trước"** (cáo, cô gái, nụ hôn, bóng người trong đêm — 6 shot trong 13.4s) với tiếng
  vải xé 0.69 (0s), tiếng ngựa 0.30 (12s), bước chân; **nhạc vào −32.8 dB ở 18s đúng lúc chữ tên phim / logo liên hoan** và **giữ phẳng −23…−29 dB tới hết khúc
  90s**, trong khi lớp giọng gần như câm (−60…−100 dB) → **dựng theo nhạc, không thoại** (montage làm vườn: hái táo, lái xe, nắng ngược). Nhạc 86%.
- Sau 100s đoạn 1: 30+ quãng lặng ngắn — vào cảnh thoại.
- **Đoạn 2 (giây file)**: lặng 0–4.5s, rồi nhạc nhỏ −50…−58 dB + nhiều lặng ngắn (8–40s) dưới cảnh trong bếp; ngựa hí 0.43 (34s), bước chân 0.30 (32s); cửa 0.30 (24s);
  **nhạc lên đều từ 40s (−37) tới −24 dB ở 70s** khi ông ra vườn tối; nhạc to lên 59, 80, 94s. Giọng gần như câm 36–42s và 64–72s. "Scary music" 0.05 ở 46s (điểm thấp).

## Bảng shot — đoạn 1 (0:00–3:00, ngưỡng 0.25)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–6 | 0.0–14.2 | WS trời chạng vạng; **CU cáo**; CU cô gái; ECU nụ hôn; bóng người đêm; ngược sáng | ngang | zoom in×2, tịnh tiến×2, tĩnh×2 | **khung "báo trước"**; không nhạc; ngựa, vải xé |
| 7–16 | 14.2–39.4 | thẻ liên hoan; chữ trên nền trừu tượng (vệt sáng); **tên phim** (#15) | — | tĩnh | **nhạc vào ở 18s** |
| 17–35 | 39.4–93.4 | MS người hái táo; insert tay cầm táo; WS vườn; CU lái xe (trong cabin); CU nắng ngược | ngang; cabin | tịnh tiến×9, zoom×5, roll×2, tĩnh×3 | montage làm việc theo nhạc, gần như không thoại |
| 36–48 | 93.4–134.4 | WS bãi thùng táo; MS nhóm thợ; CU ông chủ | ngang | tịnh tiến×5, zoom×2, roll×1, tĩnh×5 | thoại bắt đầu; lặng ngắn dày 100–130s |
| 49–63 | 134.4–180.0 | CU ↔ CU ông chủ / thợ; insert tiền (#53) | ngang | tịnh tiến×5, zoom out×1, roll×1, tĩnh×8 | trả lương; lặng 143–180s (nhiều quãng) |

## Bảng shot — đoạn 2 (giây file; ≈ 11:10 + t; theo tờ ảnh ngưỡng 0.10)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–3 | 0.0–21.2 | WS sân đêm; MS cặp đôi đi vào vườn; CU ông chủ nhìn theo (14.9s) | ngang | tịnh tiến, zoom out | "It looks like you're staying" |
| 4–24 | 21.2–42.0 | **bếp: máy cầm tay theo lưng ông lấy súng trong tủ** (có thể một đường máy, 0.10 cắt nhầm); MS cầm súng | ngang, sau lưng | tịnh tiến / zoom out / thiếu dữ liệu | cửa, ngựa hí 34s; nhạc nhỏ |
| 25–29 | 42.0–71.1 | MS ra sân; **WS vườn đêm, đèn pin (21.1s, zoom in)** | ngang | roll, zoom in | **nhạc lên đều −37 → −24 dB** |
| 30–42 | 71.1–98.2 | tối gần đen: đèn pin; **chớp trắng cháy khung** (#36–37); CU ông | thấp | roll, zoom out, thiếu dữ liệu | nhạc to lên 80, 94s |
| 43–57 | 98.2–160.0 | cặp đôi trong bụi cây; CU ông cầm súng; đèn pin rọi đất; **shot 22.6s** (124.1–146.7) | ngang / thấp | zoom out×6, zoom in×1, roll×2, thiếu dữ liệu×5 | — |

## Kỹ thuật đáng học
1. **Mở bằng chuỗi khung "báo trước" không nhạc** (6 shot trong 13.4s: cáo, cô gái, nụ hôn, bóng người đêm) **rồi mới vào tên phim**. Ý đồ **[có thể]**: gieo các hình
   sẽ quay lại ở đoạn đêm (cáo, đèn, cặp đôi). Cùng họ với mẫu hình 11 (mở bằng cảnh tương lai) nhưng **rời rạc, không lời**. Độ tin: có thể.
2. **Nhạc vào đúng chữ tên phim và mang cả khúc montage không thoại** (18–93s, nhạc phẳng −23…−29 dB, giọng câm). Ý đồ **[có thể]**: giới thiệu thế giới (vườn táo,
   công việc, nắng) bằng nhịp nhạc thay lời. Cùng mẫu hình 7 (nhạc ở chữ tên phim: 09).
3. **Máy cầm tay đi theo sau lưng** khi nhân vật lấy súng (21–42s đoạn 2) và vào vườn — mức "thiếu dữ liệu" 32% + roll 11% là dấu hiệu máy rung trong tối. Ý đồ
   **[có thể]**: đặt người xem ngay sau lưng người sắp làm điều nguy hiểm. Độ tin: có thể.
4. **Nhạc tăng đều, không có cú nhấn**, dưới cuộc truy tìm trong đêm (−37 → −24 dB trong 30s). Ý đồ **[có thể]**: hồi hộp kéo dài thay vì giật mình. Độ tin: có thể.
5. **Đèn pin là nguồn sáng duy nhất + chớp trắng cháy khung** (#36–37). Ý đồ **[đoán]**: chỉ cho người xem thấy cái nhân vật rọi tới.

## Giới hạn / câu hỏi mở
- Đêm quá tối → số shot đoạn 2 không đáng tin (dải 12–57); cần mắt xem ≥ 5 khung/giây.
- Nhạc đoạn 1 có thể là bài hát có lời (whisper không bắt được lời) — chưa nghe tai.

## Xoá dữ liệu
Đã xoá `v18_seg1.webm`, `v18_seg2.webm`, tờ quét, `v18_seg*_frames/`, tờ ảnh, thư mục `v18_seg*_L*/` và log (xác nhận bằng `clean.sh v18`). Chỉ giữ
`v18_seg{1,2}_result.json`, `v18_seg1_L0_numbers.json`, `v18_seg2_L10_numbers.json` (không lời chép).
