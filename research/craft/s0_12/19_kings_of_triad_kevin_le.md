# 19 — Kings of Triad: Uprising (Kevin Le, "Official Premiere")

- **URL**: https://www.youtube.com/watch?v=wTZG92dSOW8
- **Thể loại**: phim ngắn **hành động võ thuật** quay thật 16:9, độc lập — băng đảng Triad, đánh nhau tay không / dao trong nhà kho — mục 3.2 trong `MAU_S0_12.md`
- **Độ dài công bố**: 16:03 · file tải 1280×720
- **Đoạn đã đo**:
  - (1) 0:00–3:00 (180.0s; đen 0.6–1.2s, 7.0–7.3s — logo);
  - (2) yêu cầu 5:50–8:20 (trận đánh chính trong nhà kho) — file 160.0s, bắt đầu sớm ~10s → mốc gốc ≈ 5:40 + t **[ước tính]**.
- **Tổng đã đo**: ~340s / 963s (~35%)
- **Đã tải**: `v19_seg1.webm`, `v19_seg2.webm`, tờ quét 144p 3:00–16:03 (1 khung/10s) — **CHƯA xoá** (phiên tạm dừng 29/09, xem TONG_HOP "Bàn giao").

## Cách chọn đoạn
Tờ quét 79 khung: 3:10–4:10 nhà kho, đối mặt; **4:30–10:10 đánh nhau liên tục** (nhiều cỡ cảnh rộng, người ngã trên sàn); 10:20–12:40 nói chuyện, máu trên mặt;
13:00–14:50 cảnh "ông trùm" nền tối (phim mở rộng thế giới cho phần sau); 15:00 chữ cuối. Chọn 5:50–8:20 = giữa trận chính.

## Phương pháp
`analyze.py` ngưỡng 0.15, `motion_cv2b.py`, `tools/audio_listen.py --lang en` đoạn 1 giây 0–90, đoạn 2 giây file 10–100. Đã kiểm tiếng đủ độ dài (180 / 160s).

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| Mở đầu 0:00–3:00 | 29 | **4.87s** | 1.25–25.6s | 9.7 | tĩnh 41%, tịnh tiến 31%, zoom in 14%, zoom out 7%, roll 7% |
| Trận nhà kho (file 160s) | 54 | **2.52s** | 0.33–10.2s | 20.2 | **tịnh tiến 43%**, tĩnh 20%, roll 13%, zoom in 11%, thiếu dữ liệu 7%, zoom out 6% |

- Âm thanh: LUFS **−19.4** / **−21.5**, LRA 14.4 / 17.2 LU; quãng lặng 25 / 13.
- Đoạn 2: chỉ **9 shot ≤ 1s** trong 160s; **8 shot ≥ 5s**. Nhịp đổi ×1.9 giữa mở đầu và trận đánh (so 17: ×3.9; 03: ×2.6).

### Nghe bằng số (audio_listen)
- **Đoạn 1 (0–90s)**: nhạc **100%** −18…−37 dB, lớp giọng gần câm (trừ 4–16s, 34–36s, 66–72s). Nhãn "Vehicle / Car" 0.13–0.39 liên tục **4–44s** (xe máy chạy
  dưới chữ tên đoàn phim); "Explosion" 0.51 ở 54s; **"Slam / Door" 0.14–0.31 lặp 66–88s** — tiếng đòn đánh vào cọc gỗ khi tập (#9–11). Whisper không bắt được câu
  thoại nào đáng tin trong 0–90s.
- Sau 90s đoạn 1: **lặng ngắn dày 89.9–112s, 146–166s** — cảnh đối thoại ba người trong phòng tập.
- **Đoạn 2 (giây file 10–100)**: nhạc 99% −21…−30 dB; nhãn va chạm dày: Slam / Door / Clang / Whack / Whoosh / Smash 0.12–0.30 ở 12–88s; **Gasp 0.56 (70s)**.
  **92–98s nhạc tụt −36…−40 dB, lớp giọng câm (−105…−111)**, rồi **"Sonar" 0.54 + "Gong" 0.82 ở 96–98s**; quãng lặng dày **101–118s** = cảnh hai đối thủ đứng
  nhìn nhau (CU xen kẽ #35–41).

## Bảng shot — đoạn 1 (0:00–3:00, ngưỡng 0.15)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1 | 0.0–7.3 | logo | — | zoom out | nhạc vào ngay |
| 2–7 | 7.3–62.5 | xe máy chạy phố đêm, đường hầm (có chữ tên đoàn phim); **shot 16.3s + 15.8s**; CU người trẻ | ngang, thấp theo bánh xe | tịnh tiến×2, tĩnh×4 | tiếng xe 4–44s |
| 8–11 | 62.5–87.6 | phòng tập mù khói: đá cọc, **insert cọc quấn thừng**, đấm cọc | từ trên (#8), ngang | tịnh tiến×2, zoom in, tĩnh | "Slam" 66–88s |
| 12 | 87.6–113.2 | MS hai người đối mặt — **25.6s, zoom in** | ngang | zoom in | lặng dày 89.9–112s |
| 13–19 | 113.2–131.8 | insert tay đập gỗ, điện thoại, tay; CU | ngang | tịnh tiến×4, roll, tĩnh×2 | — |
| 20–29 | 131.8–180.0 | ba người trong phòng tập: MS ↔ CU; shot 10.3s, 11.4s | ngang | tĩnh×6, zoom in×2, roll, zoom out | lặng dày 146–166s |

## Bảng shot — đoạn 2 (giây file; ≈ 5:40 + t)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–4 | 0.0–13.8 | insert tay nắm; CU cười; MS ngã | ngang | tịnh tiến×3, tĩnh | nhạc −24 |
| 5–13 | 13.8–45.3 | **WS nhà kho, thấy trọn thân người khi đánh** (7.0s, 6.1s, 7.2s) | ngang, thấp | zoom in, roll, tịnh tiến×3, tĩnh×3 | va chạm dày |
| 14–34 | 45.3–94.3 | CU đối thủ khăn trùm đầu + dao; MS người ngã trên sàn **nhìn từ trên xuống** (#28–30); các shot 0.5–1.2s ở 81–86s | ngang; từ trên | tịnh tiến×10, roll×5, zoom×4 | **Gasp 70s**; Whoosh 72, 82s |
| 35–41 | 94.3–118.8 | **CU ↔ CU hai đối thủ đứng nhìn nhau** (1.9–5.5s) | ngang | zoom out, tịnh tiến, tĩnh×3, zoom in | **nhạc tụt, Gong 0.82 98s, lặng 101–118s** |
| 42–54 | 118.8–160.0 | WS cửa cuốn: hai người cầm dao đấu; MS ngã; WS xa có xe nâng | ngang, thấp | **tịnh tiến×9**, zoom in, roll, thiếu dữ liệu×2 | — |

## Kỹ thuật đáng học
1. **Đánh nhau quay bằng cỡ rộng, shot 2–7s, máy đi theo (tịnh tiến 43%)** thay vì cắt vụn. Ý đồ **[có thể]**: khoe vũ đạo thật của diễn viên võ thuật — người xem
   thấy trọn đòn. Khác 17 (0.75s, cắt vụn) và 03 (1.84s). Điều kiện **[suy luận]**: chỉ làm được khi động tác thật đủ đẹp — với video AI (động tác dễ lỗi) cắt ngắn
   hơn để giấu lỗi. Độ tin: khá về số đo.
2. **Nghỉ giữa trận: nhạc tụt + tiếng "gong" + lặng ~17s trên CU ↔ CU hai đối thủ** (94–118s đoạn 2). Ý đồ **[có thể]**: "hiệp hai" — cho người xem thở và nâng
   cược trước pha đấu dao. Cùng mẫu hình 5 (tắt nhạc dưới khoảnh khắc then chốt) — ở phim hành động. Độ tin: có thể.
3. **Mở phim bằng chuỗi xe máy chạy + chữ tên đoàn phim dài 55s trên nhạc**, rồi mới vào cảnh tập. Cùng mẫu hình 9 (shot mở dài 3–4× trung vị) và 18 (nhạc mang đoạn
   giới thiệu không thoại).
4. **Tiếng đòn trên cọc gỗ khi tập** báo trước tiếng đòn của trận chính (cùng họ nhãn "Slam" ở cả hai đoạn). Ý đồ **[đoán]**: gieo "âm thanh của nhân vật". Độ tin: đoán.

## Giới hạn / câu hỏi mở
- Nhãn "Slam / Door" là cách AudioSet gọi tiếng đòn — chưa nghe tai.
- Mốc gốc đoạn 2 chỉ ước tính ±10s.

## Xoá dữ liệu
**CHƯA xoá** media (phiên tạm dừng) — phiên sau chạy `bash clean.sh v19`. Số đo đã chép vào repo ở `research/craft/s0_12/so_do/` (`v19_seg{1,2}_result.json`, `v19_seg1_L0_numbers.json`,
`v19_seg2_L10_numbers.json` — không lời chép).
