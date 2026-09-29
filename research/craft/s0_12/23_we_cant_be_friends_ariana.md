# 23 — we can't be friends (wait for your love) (MV Ariana Grande, đạo diễn Christian Breslauer)

- **URL**: https://www.youtube.com/watch?v=KNtJGQkC-WI
- **Thể loại**: MV kể chuyện quay thật 16:9 — cô gái đến một phòng khám **xoá ký ức** người yêu cũ; ký ức hiện thành những mảnh sáng màu (khu trò chơi neon, nằm
  trên tuyết) — mục 4.2 trong `MAU_S0_12.md`
- **Độ dài công bố**: 4:43 · file tải 1280×720
- **Đoạn đã đo**:
  - (1) 0:00–3:00 (180.0s);
  - (2) yêu cầu 3:00–4:43 — file 113.0s, bắt đầu sớm ~10s (keyframe) → mốc gốc ≈ 2:50 + t **[ước tính]**.
- **Tổng đã đo**: ~283s / 283s (**trọn MV**, chồng ~10s)
- **Đã tải**: `v23_seg1.webm`, `v23_seg2.webm`, tờ quét 144p (1 khung/10s) — **CHƯA xoá** (phiên tạm dừng 29/09, xem TONG_HOP "Bàn giao").

## Phương pháp
`analyze.py` ngưỡng **0.15** (hình tối, ánh đèn vàng), `motion_cv2b.py`, `tools/audio_listen.py --lang en` (cờ `song`: không in / lưu lời hát), thêm
**`beat_align.py`** (mới, 2026-09-29): librosa dò phách trên cả bản trộn → tỉ lệ điểm cắt nằm trong ±0.08s một phách, so với tỉ lệ ngẫu nhiên (2 × 0.08 / chu kỳ phách).

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| 0:00–3:00 | 28 | **3.40s** | 0.59–25.4s | 9.3 | tĩnh 57%, zoom in 18%, tịnh tiến 14%, zoom out 7%, roll 4% |
| ≈ 2:50–4:43 (file 113s) | 17 | **5.42s** | 1.08–21.2s | 9.0 | **zoom in 35%**, tĩnh 35%, roll 12%, thiếu dữ liệu 12%, zoom out 6% |

- Âm thanh: LUFS **−10.7** / **−10.6**, LRA 15.8 / 6.8 LU; quãng lặng **0** / 1 (4.5s cuối — chữ "Directed by").
- **Điểm cắt so với phách** (bài ~117 BPM theo librosa): đoạn 1 từ 52s: 23 cắt, trúng phách **39%** (ngẫu nhiên 31%), trúng nửa phách 61% (ngẫu nhiên 63%)
  → **gần mức ngẫu nhiên, cắt không khoá theo phách**. Đoạn 2: phép đo hỏng (dò phách mất ở quãng nhạc tắt 30–45s) — không dùng.

### Nghe bằng số (audio_listen)
- **Đoạn 1, 0–52s: chưa vào bài hát.** Nhạc nền nhỏ đều −38…−40 dB, lớp giọng câm (−90…−110 dB) trừ vài câu thoại ngắn 26s, 32–36s (phòng chờ). Nhãn
  "Door / Sliding door" 20–48s, **"Heart sounds, heartbeat" 0.27–0.43 ở 50–52s** ngay trước khi bài hát vào.
- **Bài hát vào ở ~52s** (−25 → −17 dB) và giữ phẳng −17…−19 dB; nhịp tim / "Throbbing" 0.16–0.31 còn lẫn trong lớp nhạc 54–62s.
- **Đoạn 2**: nhạc −12 dB tới 29s → **tụt −33 (30s) → −60 dB (34s)** với nhãn "Television" (36s) → −29 (38s) → **trở lại −11 dB ở 46s**. Giọng hát câm từ 80s;
  lặng hẳn 108.5–113s dưới chữ đạo diễn.

## Bảng shot — đoạn 1 (0:00–3:00, ngưỡng 0.15)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–3 | 0.0–31.7 | **insert tay ký giấy** (11.7s + 12.3s) kẹp MS cô gái ngồi bàn | từ trên / ngang | tịnh tiến, zoom out, tĩnh | nền nhỏ −38 dB; không hát |
| 4–5 | 31.7–63.3 | WS phòng chờ (14.1s tĩnh); MS phòng máy sáng chói (17.6s, zoom in) | ngang | tĩnh, zoom in | vài câu thoại; **nhịp tim 50–52s → bài hát vào ~52s** |
| 6–10 | 63.3–87.3 | MS y tá, máy móc; insert màn hình não; MS cô gái trên ghế (**14.9s zoom in**) | ngang | tĩnh×3, zoom in×2 | hát câu đầu |
| 11–16 | 87.3–104.7 | hành lang tối; **ký ức neon: máy gắp thú, tay, hai người cười — 0.6–1.1s mỗi shot** | ngang | tĩnh, tịnh tiến | nhạc phẳng −19 |
| 17–19 | 104.7–148.9 | cô gái một mình trong tối (**25.4s, zoom out**); phòng ngủ đỏ; tối (14.0s, roll) | ngang | zoom out, tĩnh, roll | — |
| 20–28 | 148.9–180.0 | **ký ức tuyết: hai người nằm làm "thiên thần tuyết"** (từ trên xuống); trắng loá 10.2s; giường xanh lạnh; hộp kỷ vật | **từ trên xuống** (#20–22) | zoom in×2, tĩnh×7 | — |

## Bảng shot — đoạn 2 (giây file; ≈ 2:50 + t)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–4 | 0.0–34.4 | hộp kỷ vật; phòng tối ánh nến, gấu bông (8.1s, 5.9s); | ngang | zoom in×2, tĩnh, zoom out | nhạc −12 dB; **tụt dần từ 29s** |
| 5 | 34.4–35.4 | **tế bào thần kinh loé sáng** (ký ức bị xoá) | — | roll | **nhạc −60 dB** + "Television" |
| 6–9 | 35.4–86.8 | CU cô gái đeo điện cực (13.0s); WS phòng khách; chó (21.2s) | ngang | **zoom in×4** | nhạc về −29 (38s) → **−11 dB (46s)** |
| 10–16 | 86.8–110.8 | cô gái trong phòng; tivi đỏ; **gặp lại người đàn ông dưới hoa anh đào** (#12–16, 1.1–1.6s) | ngang | tĩnh×4, roll, thiếu dữ liệu | giọng hát tắt ~80s |
| 17 | 110.8–113.0 | chữ "Directed by" | — | — | lặng |

## Kỹ thuật đáng học
1. **Đoạn mở ~52s không hát** (insert ký giấy, phòng chờ, nền nhỏ −38 dB, nhịp tim) trước khi vào bài. Ý đồ **[có thể]**: dựng "luật chơi" của truyện (xoá ký ức)
   trước để lời bài hát sau đó được hiểu theo truyện. Cùng họ với 09, 18 (nhạc vào sau một đoạn thiết lập). Độ tin: khá (số đo rõ).
2. **Ký ức = cụm shot ngắn 0.6–1.1s, màu khác hẳn** (neon hồng tím, tuyết trắng) chen giữa các shot dài 12–25s ở phòng khám tông vàng nâu. Ý đồ **[có thể]**: người
   xem nhận ra "đây là ký ức" nhờ **nhịp + màu** chứ không nhờ chữ. Cùng mẫu hình 2 (cụm shot ngắn cho một khoảnh khắc) — biến thể "khám phá ký ức".
3. **Nhạc tụt gần câm (−60 dB) đúng shot "tế bào thần kinh loé sáng"** (34.4s đoạn 2) rồi về dần trong 12s. Ý đồ **[có thể]**: khoảnh khắc ký ức bị xoá = âm thanh bị
   xoá. Cùng mẫu hình 5 (tắt nhạc dưới khoảnh khắc then chốt) — **ở MV**, nhưng nhạc về **dần**, không đúng một điểm cắt. Có thể là bản phối riêng cho MV. Độ tin: có thể.
4. **Máy zoom / dolly in chậm trên shot dài** (35% shot đoạn 2; shot 13–21s). Ý đồ **[đoán]**: kéo người xem vào đầu nhân vật trong lúc hát. Độ tin: đoán.
5. **Cắt không bám phách**: trúng phách 39% so với 31% ngẫu nhiên; trúng nửa phách ở mức ngẫu nhiên. MV kể chuyện này cắt theo **câu / cảnh**, không theo phách.
   Độ tin: khá cho đoạn đo (có thể sai nếu librosa dò lệch pha — cần nghe tai).

## Giới hạn / câu hỏi mở
- Hình tối + đèn nhấp nháy → ngưỡng 0.15 có thể bắt nhầm (#16–17 đoạn 2 "thiếu dữ liệu").
- Lời hát không lưu; whisper chỉ để lấy mốc câu. Nhịp tim / "Throbbing" là nhãn AST điểm thấp.
- Chỉ 1 phép đo phách đáng tin (đoạn 1).

## Xoá dữ liệu
**CHƯA xoá** media (phiên tạm dừng) — phiên sau chạy `bash clean.sh v23`. Số đo đã chép vào repo ở `research/craft/s0_12/so_do/` (`v23_seg{1,2}_result.json`,
`v23_seg{1,2}_L0_numbers.json`, `v23_beat.jsonl` — không lời hát).
