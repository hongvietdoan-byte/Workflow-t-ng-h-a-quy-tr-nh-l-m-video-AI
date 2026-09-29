# 16 — FEELING THROUGH (Omeleto)

- **URL**: https://www.youtube.com/watch?v=h1CqzntEZZ8
- **Thể loại**: phim ngắn live-action 16:9, chính kịch; thiếu niên vô gia cư Tereek giúp Artie (người điếc–mù thật) bắt xe buýt đêm ở New York — mục 2.2 trong
  `MAU_S0_12.md`
- **Độ dài công bố**: 18:25 · file tải 1280×720
- **Đoạn đã đo**:
  - (1) 0:00–3:00 (180.0s; 0–4.63s màn đen + logo Omeleto);
  - (2) yêu cầu 13:30–16:00 (Tereek đọc mẩu giấy "please leave the room…", đánh vần lên lòng bàn tay, xe buýt tới) — file 160.0s, bắt đầu sớm ~10s → mốc gốc ≈
    13:20 + t **[ước tính]**.
- **Tổng đã đo**: ~335s / 1105s (~30%)
- **Đã tải**: `v16_seg1.webm`, `v16_seg2.webm`, khúc quét 144p 3:00–18:25 (1 khung/10s) — **tất cả đã xoá**.

## Cách chọn đoạn
Tờ quét 93 khung: trạm xe buýt đêm, cửa hàng tạp hoá (8:00–9:10), sổ tay viết chữ (6:50, 10:00–11:10, 13:40), CU Tereek trùm mũ khóc (13:50–15:40), chữ
"YOU'LL BE OK" (15:40), tên phim 17:20. Chọn 13:30–16:00 = điểm cảm xúc cao nhất.

## Phương pháp
Như 11. **Hình đêm tương phản thấp**: ngưỡng 0.25 ở đoạn 1 chỉ ra 6 shot (một shot 115s) → **đo lại đoạn 1 ở ngưỡng 0.10 → 24 shot** (dùng số này). Đoạn 2 dùng
ngưỡng 0.25 (20 shot; bản 0.10 chưa chạy xong khi viết) — **có thể sót cắt** ở các shot dài. `audio_listen --lang en` đoạn 1 giây 0–90, đoạn 2 giây file 10–100.

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| Mở đầu 0:00–3:00 (ngưỡng 0.10) | 24 | **5.03s** | 1.17–25.11s | 8.0 | tĩnh 62%, tịnh tiến 29%, zoom in 4%, roll 4% |
| Tay đánh vần + xe buýt (ngưỡng 0.25) | 20 | 3.33s | 1.58–44.92s | 7.5 | tĩnh 40%, tịnh tiến 30%, zoom in 10%, zoom out 5%, roll 5%, thiếu dữ liệu 10% |
| Tay đánh vần + xe buýt (**ngưỡng 0.10, dùng số này**) | 38 | **2.91s** | 0.97–21.06s | 14.3 | tĩnh 55%, tịnh tiến 24%, roll 11%, zoom in 3%, zoom out 3%, thiếu dữ liệu 5% |

- **Kiểm lại ngưỡng 0.10 (xong sau khi viết bản đầu)**: "shot 44.9s" (84.7–129.6s) thực ra là **18 shot 1.0–6.1s** — đối đáp trên xe buýt; các shot dài 17.7s (0–17.7),
  **21.1s (CU khóc, 44.5–65.5)** giữ nguyên → CU khóc dài là thật. Đoạn 2 nhanh gần gấp đôi đoạn 1 (2.91s ↔ 5.03s) — cùng chiều mẫu hình 1 (phim ngắn đổi nhịp).

- Âm thanh: LUFS **−24.9** / **−22.5** (nhỏ nhất cùng 17, 18 — mức phim, không phải mức mạng xã hội), LRA **17.2** / **26.1 LU** (rộng nhất đã đo); quãng lặng **6** / **31**.

### Nghe bằng số (audio_listen)
- **Đoạn 1**: 0–4s lặng (logo). Nhạc 96%: lên chậm từ −49 dB (4s) → −35 (24s) → **−20 dB ở 42s** dưới shot đi bộ dài 21.9s (#4, 36.6–58.5s); lặng ngắn 48.5–52.4s;
  nhạc lại −21 ở 76s. Lớp giọng 55–85s có lời liên tục kiểu **rap / bài hát** trên nền (whisper chép ra câu có vần) — [có thể] bài hát trong nhạc phim; không chép lời.
- **Đoạn 2 (giây file)**: nhạc chỉ là **nền rất nhỏ −44…−48 dB** suốt 10–60s (màn viết sổ tay, Tereek khóc) — lớp giọng gần như câm (−100…−120 dB: Artie không nói,
  Tereek im); **lặng 30.7–42.2s và 60.8–67.5s**; rồi **nhạc trồi −41.6 → −16.3 dB ở 67–71s** cùng tiếng xe (Vehicle / Air brake 0.12–0.36, 74–98s) khi xe buýt tới
  (cắt 65.5). Nhãn "Sine wave 0.95" ở 64–66s = một âm đơn tần (có thể tiếng chuông / tiếng ù) ngay trước khi nhạc vào.

## Bảng shot — đoạn 1 (0:00–3:00, ngưỡng 0.10)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1 | 0.0–4.6 | màn đen + logo | — | tĩnh | lặng |
| 2 | 4.6–29.7 | WS phố đêm, Tereek đi qua; **bong bóng tin nhắn nổi trên hình** | ngang | zoom in (25.1s) | nhạc nhỏ lên dần |
| 3–4 | 29.7–58.5 | WS lối ga ngầm; MS đi bộ (21.9s) | ngang | tịnh tiến×1, tĩnh×1 | nhạc −20 dB ở 42s |
| 5–11 | 58.5–95.2 | WS tiệm tạp hoá; MS nhóm bạn trên phố; CU ăn | ngang | tịnh tiến×4, tĩnh×3 | lời kiểu rap trên nền |
| 12–17 | 95.2–150.4 | MS / CU Tereek một mình (14.0 / 12.8 / 11.6 / 10.5s); **tin nhắn nổi** (#13, #16, #17) | ngang | tĩnh×6 | nhắn xin ngủ nhờ — không ai nhận |
| 18–24 | 150.4–180.0 | MS người lạ (Artie) cầm cốc; CU Tereek ↔ WS trạm | ngang | tịnh tiến×2, roll×1, tĩnh×4 | gặp Artie |

## Bảng shot — đoạn 2 (giây file; ≈ 13:20 + t; ngưỡng 0.25)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–8 | 0.0–40.4 | MS hai người ngồi trạm (17.7s); **insert sổ tay chữ viết tay** (#2, #4, #6); CU Tereek | ngang | tịnh tiến×3, tĩnh×4, roll×1 | nhạc nền −44…−48; lặng 30.7–42.2 |
| 9 | 44.5–65.5 | **CU Tereek trùm mũ khóc, 21.1s** | ngang | zoom in | gần như câm; lặng 60.8–65.5 |
| 10 | 65.5–84.7 | trong xe buýt, 19.1s | ngang | tịnh tiến | **nhạc trồi −16 dB ở 71s** + tiếng xe |
| 11 | 84.7–129.6 | MS / CU hai người trên xe — ở ngưỡng 0.10 là **18 shot 1.0–6.1s** đối đáp | ngang | tĩnh×12, tịnh tiến×3, roll×3 (ngưỡng 0.10) | Tereek nói về Artie |
| 12–16 | 129.6–147.3 | **insert tay đánh vần lên lòng bàn tay** (#14) + **chữ "YOU'LL BE OK" hiện dần trên hình** (#14–15); CU Artie cười | ngang | tịnh tiến×3, tĩnh×2 | — |
| 17–20 | 147.3–160.0 | ôm nhau trên xe | ngang | zoom out×1, tĩnh×1, thiếu dữ liệu×2 | — |

## Kỹ thuật đáng học
1. **Giữ CU rất lâu trên mặt nhân vật im lặng** (21.1s khóc, 14.0 / 12.8 / 11.6 / 10.5s ở đoạn 1), nhạc chỉ là nền −44…−48 dB. Ý đồ **[có thể]**: để diễn xuất
   không lời mang cảm xúc — hợp với phim về giao tiếp không lời. Độ tin: có thể.
2. **Chữ trên hình thay lời thoại không nghe được**: bong bóng tin nhắn nổi trên cảnh phố (đoạn 1 #2, #13, #16, #17), sổ tay viết tay (đoạn 2), và **chữ "YOU'LL BE
   OK" hiện theo từng chữ cái đánh vần lên lòng bàn tay** (#14–15). Ý đồ **[khá]**: người xem "đọc" đúng thứ nhân vật cảm nhận bằng xúc giác. Cùng họ với lớp chữ
   trong hình của 11, 13, 17 — ở đây phục vụ **khả năng tiếp cận**, không phải thông tin phụ.
3. **Lặng rồi nhạc trồi mạnh cùng một sự kiện âm thanh thật** (lặng 60.8–67.5s → nhạc −16 dB ở 71s cùng tiếng xe buýt, cắt 65.5). Ý đồ **[có thể]**: xe buýt =
   lời giải của đêm; nhạc chỉ "được phép" lên khi nhiệm vụ hoàn thành. Cùng hình dạng mẫu hình 5 và 7.
4. **Nhạc lên rất chậm suốt 40s đầu** (−49 → −20 dB, 4–42s) dưới shot đi bộ dài. Ý đồ **[có thể]**: nhịp "một đêm lang thang" thay cho giới thiệu bằng thoại.

## Giới hạn / câu hỏi mở
- Đoạn 2: bảng theo cụm dựa trên ngưỡng 0.25; số chính xác lấy từ bản ngưỡng 0.10 (38 shot).
- Lời kiểu rap 55–85s đoạn 1: chưa rõ là nhạc phim hay nhân vật nói; không chép lời.

## Xoá dữ liệu
**CHƯA XOÁ** (lệnh shell bị chặn khi viết file): còn `v16_seg1.webm`, `v16_seg2.webm`, `v16_seg*_frames/`, tờ ảnh, thư mục `v16_seg*_L*/` và log trong
`scratchpad/s012` — phải chạy `bash clean.sh v16`. Sau khi dọn chỉ giữ `v16_seg{1,2}_result.json`,
`v16_seg1b_result.json` (ngưỡng 0.10), `v16_seg1_L0_numbers.json`, `v16_seg2_L10_numbers.json` (không lời chép).
