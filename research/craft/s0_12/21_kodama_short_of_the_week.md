# 21 — Kodama ("Samurai SWAT team on a rescue mission", Short of the Week)

- **URL**: https://www.youtube.com/watch?v=Jvqvo5OwCH0
- **Thể loại**: phim ngắn **hành động samurai + kỹ xảo siêu nhiên** quay thật, khổ rộng (1280×544 ≈ 2.35:1), gần như toàn cảnh đêm — mục 3.4 trong `MAU_S0_12.md`
- **Độ dài công bố**: 15:39 · file tải 1280×544
- **Đoạn đã đo**:
  - (1) 0:00–3:00 (180.0s; đen 0–1.5s, 14.0–20.0s);
  - (2) yêu cầu 9:50–12:20 (trận đánh trong vườn Nhật) — file 160.0s, bắt đầu sớm ~10s → mốc gốc ≈ 9:40 + t **[ước tính]**.
- **Tổng đã đo**: ~340s / 939s (~36%)
- **Đã tải**: `v21_seg1.webm`, `v21_seg2.webm`, tờ quét 3:00–15:39 — **chưa xoá** lúc viết.

## Cách chọn đoạn
Tờ quét: 3:00–3:40 xe chở đội (ánh xanh nhìn đêm); 4:00–5:40 đột nhập tối; 5:50–7:30 thế giới linh hồn (đèn lồng, sương); **9:20–12:40 đánh kiếm trong vườn**;
13:10–14:20 kết + hiệu ứng lửa; 14:30 chữ cuối. Chọn 9:50–12:20 = giữa trận.

## Phương pháp
`analyze.py` 0.15 **và kiểm lại 0.10** (phim rất tối — xem Số đo); `motion_cv2b.py` (theo ngưỡng 0.15); `tools/audio_listen.py --lang en` đoạn 1 giây 0–90,
đoạn 2 giây file 10–100.

## Số đo
| Đoạn | Ngưỡng | Shot | Trung vị | Shot/phút | Shot ≥ 10s | Máy (OpenCV, ngưỡng 0.15) |
|---|---|---|---|---|---|---|
| Mở 0:00–3:00 | 0.15 | 12 | 4.55s | 4.0 | 53.4, 53.3, 41.1 | tịnh tiến 33%, tĩnh 25%, roll 17%, zoom in 17% |
| | **0.10** | 23 | **2.70s** | 7.7 | 40.6 (chữ chạy), 25.5, 29.6 | — |
| Trận trong vườn (160s) | 0.15 | 29 | 3.80s | 10.9 | 11.2–17.9 ×5 | tĩnh 28%, tịnh tiến 24%, roll 17%, zoom in 17%, zoom out 14% |
| | **0.10** | 52 | **2.45s** | 19.5 | 11.4, 12.8 | — |

- Âm thanh: LUFS **−23.3** / **−20.5**, LRA 22.2 / 15.4 LU; quãng lặng 14 / **0**.
- **Ở phim tối, ngưỡng 0.15 bỏ sót gần nửa số cắt** (29 → 52 ở đoạn 2) — dùng số ngưỡng 0.10 khi so nhịp; số máy (OpenCV) theo shot 0.15 nên chỉ tham khảo.

### Nghe bằng số (audio_listen)
- **Đoạn 1 (0–90s)**: 0–16s nhạc to lên −15 dB dưới cảnh mở đầu (hai câu thoại ngắn ở 0–4s), **18s nhạc tụt −60** đúng chỗ đen chuyển sang chữ chạy; 18–56s nhạc
  nhỏ −41…−48 dB kèm nhãn **Explosion / Eruption 0.12–0.48 liên tục** (tiếng ầm trầm, không phải nổ thật) dưới **đoạn chữ giới thiệu thế giới chạy trên tranh nền**
  (23.2–63.8s); nhạc trồi −21 dB ở 56–60s; Typing 64s, Door / Slam 74–78s, Gasp 84s khi vào cảnh đối thoại.
- **Đoạn 2 (giây file 10–100)**: nhạc 100%, −18…−43 dB; nhãn va chạm kim loại dày: Smash / Crash 12–22s, **Clang 0.60 (48s), 0.53 (60s)**, Ding 26–52s
  (kiếm chạm), Breaking / Shatter 62s. **Không có quãng lặng** trong 160s.

## Bảng shot — đoạn 1 (0:00–3:00, ngưỡng 0.10)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Nội dung / âm thanh |
|---|---|---|---|---|
| 1–7 | 0.0–15.3 | mở nhanh: MCU hai người trong rừng tối, CU samurai giáp, insert kiếm, chữ tên phim | ngang | 2 câu ngắn, nhạc lên −15 |
| 8 | 15.3–23.2 | đen | — | nhạc tụt −60 |
| 9–10 | 23.2–75.4 | **tranh nền thành phố + chữ giới thiệu thế giới chạy 40.6s**, rồi cảnh ngắn 11.6s | ngang | tiếng ầm trầm dưới chữ |
| 11–15 | 75.4–82.7 | đen có chữ, chuyển cảnh | — | Door / Slam |
| 16–20 | 82.7–132.6 | **đối thoại trong phòng tối**: CU nhân vật chính, shot 14.1s và 25.5s | ngang | Gasp 84s |
| 21–23 | 132.6–180.0 | WS đêm ngoài trời (29.6s), rồi xe chở đội **ánh xanh nhìn đêm** | ngang | — |

## Bảng shot — đoạn 2 (giây file; ≈ 9:40 + t, ngưỡng 0.15)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–5 | 0.0–45.1 | WS vườn đêm, nhiều người đánh; ngã trong cỏ; shot dài 11–15s | ngang, thấp | roll, zoom×3 | Smash / Crash |
| 6–19 | 45.1–90.3 | MCU đấu kiếm, mặt nạ oni, insert kiếm, **chuỗi 6 shot tĩnh 2.2–3.4s** (74–90s) | ngang, thấp | tĩnh×7, tịnh tiến, zoom | Clang 48s, 60s |
| 20–29 | 90.3–160.0 | CU người lớn tuổi ↔ nữ samurai; WS trận; hai shot kết 15.2s, 17.9s | ngang | roll×3, tịnh tiến×3 | nhạc lên 95s |

## Kỹ thuật đáng học
1. **Giới thiệu thế giới bằng chữ chạy trên tranh nền ~40s** (sau đoạn mở nhanh 15s + đen 8s), dưới tiếng ầm trầm thay vì nhạc có giai điệu. Ý đồ **[có thể]**:
   phim ngắn thế giới lạ (linh hồn Yokai) cần luật chơi trước khi hành động — "móc" 15s trước, giải thích sau. Liên hệ: trailer / video FF nhiều khi cần giới thiệu
   bối cảnh — cách này rẻ (một ảnh nền + chữ) nhưng dài; với video 60s thì không hợp. Độ tin: chắc về cấu trúc (xem tờ ảnh), có thể về ý đồ.
2. **Âm thanh trận không có một quãng lặng nào trong 160s** (khác 19, 20 có nghỉ giữa trận). Cùng mẫu hình 10 (âm thanh liên tục ở phim hành động) — đoạn đo có thể
   chưa tới chỗ nghỉ.
3. **Tiếng kim loại (Clang / Ding) làm nhịp** thay cho tiếng đòn thân người (Whip / Slap ở 20). Ý đồ **[đoán]**: kiếm → tiếng va rõ, cao, cắt qua nhạc nền.
4. **Ánh xanh nhìn đêm cho cảnh xe chở đội** (tờ quét 3:00–3:40) đánh dấu "chế độ nhiệm vụ" — màu như một lớp kể chuyện (cùng họ mẫu hình 14 "lớp giao diện trong hình").

## Giới hạn / câu hỏi mở
- Phim rất tối: đếm cắt phụ thuộc ngưỡng (bảng trên); OpenCV dễ "thiếu dữ liệu" và gán roll nhầm khi ảnh nhiễu.
- Nhãn Explosion / Eruption dưới chữ chạy là tiếng ầm trầm — **chưa nghe tai**.
- Mốc gốc đoạn 2 ước tính ±10s.

## Xoá dữ liệu
Media ở scratchpad phiên nice-bhabha (`s012/`) — `bash clean.sh v21`. Số đo ở `research/craft/s0_12/so_do/` (`v21_seg{1,2}_result.json`, `v21_seg1_L0_numbers.json`,
`v21_seg2_L10_numbers.json`, `v21_seg{1,2}_t010.txt` — điểm cắt ngưỡng 0.10).
