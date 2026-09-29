# 20 — NIGHT SHIFT (Lorenz Hideyoshi Ruwwe)

- **URL**: https://www.youtube.com/watch?v=syPO8e36YSI
- **Thể loại**: phim ngắn **hành động võ thuật quay thật** 16:9 (khung 1280×676), bối cảnh Sài Gòn về đêm, thoại tiếng Việt — tài xế xe ôm đêm gặp biến cố từ quá khứ —
  mục 3.3 trong `MAU_S0_12.md`
- **Độ dài công bố**: 11:36 · file tải 1280×676, 24 fps
- **Đoạn đã đo**:
  - (1) 0:00–3:00 (180.0s; đen 0–3.8s);
  - (2) yêu cầu 3:30–6:00 (trận đánh trong hẻm) — file 160.0s, bắt đầu sớm ~10s → mốc gốc ≈ 3:20 + t **[ước tính]**.
- **Tổng đã đo**: ~340s / 696s (~49%)
- **Đã tải**: `v20_seg1.webm`, `v20_seg2.webm`, tờ quét 3:00–11:36 (1 khung/10s) — **chưa xoá** lúc viết (xoá theo `clean.sh v20`).

## Cách chọn đoạn
Tờ quét: 3:00–3:30 đối mặt trong hẻm; **3:40–8:10 đánh nhau liên tục** (hẻm hẹp, người ngã, xe máy); 8:20–9:40 rượt / chạy xe; 9:50–10:10 phố đêm
đông người; 10:10 chữ tên phim, sau đó chữ cuối. Chọn 3:30–6:00 = đầu trận chính.

## Phương pháp
`analyze.py` ngưỡng 0.15; đoạn 1 kiểm lại ở **0.10** (cùng kết quả — xem Giới hạn) + tờ ảnh sáng lên 116–163s; `motion_cv2b.py`; `tools/audio_listen.py --lang vi`
đoạn 1 giây 0–90, đoạn 2 giây file 10–100. Tiếng đủ độ dài (180 / 160s).

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| Mở đầu 0:00–3:00 | 16 (**thiếu** — xem Giới hạn) | 3.60s | 1.16–**78.9s** | 5.3 | tĩnh 38%, tịnh tiến 44%, zoom in 12%, zoom out 6% |
| Trận trong hẻm (file 160s) | 66 | **1.87s** | 0.41–11.5s | 24.8 | tịnh tiến 26%, tĩnh 23%, zoom out 18%, zoom in 14%, **roll 14%**, thiếu dữ liệu 6% |

- Âm thanh: LUFS **−21.8** / **−11.6** (chênh 10 dB giữa mở đầu và trận đánh), LRA 20.7 / 19.0 LU; quãng lặng 23 / 14.
- Đoạn 2: 12 shot ≤ 1s; máy "động" 71% (tịnh tiến + zoom + roll) — máy cầm tay đi theo đòn.

### Nghe bằng số (audio_listen)
- **Đoạn 1 (0–90s)**: nhạc có nhưng **rất nhỏ −45…−55 dB tới ~50s**, rồi **lên đều** −42 → −21 dB (54–88s) đúng lúc nhân vật dắt xe ra khỏi hẻm và chạy ra phố.
  Thoại tiếng Việt 17–31s (khách hỏi giá, trả giá). Nhãn: cửa kéo 52s, xe 62–76s.
- **Đoạn 2 (giây file 10–100)**: nhạc 97%, to −12…−24 dB từ 24s; nhãn đòn đánh dày: Whip 0.65 (38s), 0.75 (44s), 0.56 (80s), Slap 0.39 (52s), Slam / Door
  rải 24–72s, Ding + Clang 74s. **96–98s nhạc tụt −48 → −63 dB**, quãng lặng dày **96.5–118s**.

## Bảng shot — đoạn 1 (0:00–3:00)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1 | 0.0–78.9 | **một cú máy liền ~75s** (sau 3.8s đen): WS hẻm đêm → người ngủ trên xe → khách tới → trả giá → dắt xe ra | ngang, máy đứng yên | tĩnh | nhạc nhỏ dưới thoại, lên dần từ ~54s |
| 2–9 | 78.9–116.2 | chạy xe phố đêm: WS đường, insert bánh xe, MS hai người trên xe, cầu | ngang, thấp | tịnh tiến×4, zoom×3 | nhạc rõ |
| 10 | 116.2–163.1 | **≥ 6 cảnh không bắt được điểm cắt**: chạy xe, chữ tên đoàn phim, insert gương xe, WS từ trên cao, chữ "NIGHT SHIFT", hẻm mưa | nhiều | (tịnh tiến) | — |
| 11–16 | 163.1–180.0 | hẻm mưa, xe đi vào; insert tay | ngang | tĩnh×5 | — |

## Bảng shot — đoạn 2 (giây file; ≈ 3:20 + t)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–7 | 0.0–23.7 | WS hẻm → MS đối mặt (mũ bảo hiểm xanh) → insert | ngang; từ trên (#3) | zoom in / out, roll | 18–22s hai câu thách thức |
| 8–45 | 23.7–95.8 | **đánh trong hẻm hẹp**: MS / MCU cầm tay, người ngã sát tường, ghép 0.4–1.5s ở pha đòn | ngang, thấp, nghiêng | **roll×7**, tịnh tiến×12, zoom×14 | Whip / Slap dày, nhạc −12…−20 |
| 46–53 | 95.8–123.0 | **nghỉ giữa trận**: shot 8.1s đi theo; CU hai phía nhìn nhau | ngang | tịnh tiến, tĩnh×4, zoom in×2 | **nhạc tụt −63 dB, lặng 96.5–118s** |
| 54–58 | 123.0–146.3 | **CU mặt đối thủ dưới đèn xanh** 5–7s, zoom out | ngang | zoom out×3 | — |
| 59–66 | 146.3–160.0 | vào lại trận: WS hẻm, đá, ngã | ngang | zoom, tịnh tiến | — |

## Kỹ thuật đáng học
1. **Mở phim bằng một cú máy liền ~75s, máy đứng yên ở đầu hẻm**, người diễn đi vào / ra khung (ngủ trên xe → khách tới → trả giá → dắt xe đi). Ý đồ **[có thể]**:
   cho người xem "ở cùng" nhịp đêm chậm, đời thường của nghề xe ôm trước khi bạo lực nổ ra — tương phản với đoạn 2 (1.87s). Cùng mẫu hình 9 (shot mở dài gấp nhiều lần
   trung vị) — ở đây ~40× trung vị đoạn 2. Độ tin: chắc về số đo (đã xem tờ ảnh 0–80s: cùng khung, người di chuyển).
2. **Nhạc gần như câm dưới cảnh đời thường, lên dần đúng lúc nhân vật ra phố** (−50 → −21 dB, 54–88s). Cùng mẫu hình 7 (nhạc trồi khi "mở không gian / thoát ra")
   và "đoạn thiết lập không nhạc rồi mới vào bài" (18, 23, 09). Độ tin: khá.
3. **Đánh nhau trong hẻm hẹp: máy cầm tay, roll 14%, shot ~1.9s**, nhiều góc thấp / nghiêng — khác 19 (cỡ rộng, 2.5s, máy đi theo khoe vũ đạo). Ý đồ **[có thể]**:
   không gian hẹp không cho cỡ rộng → dùng chuyển động máy để tạo cảm giác va chạm. Điều kiện: 19 và 20 cùng thể loại nhưng hai cách → "hành động" không kéo theo
   một kiểu dựng duy nhất.
4. **Nghỉ giữa trận: nhạc tắt + lặng ~20s + CU hai phía**, rồi CU mặt đối thủ 5–7s trước khi đánh tiếp. **Giống hệt cấu trúc ở 19** (nhạc tụt + gong + lặng 17s) →
   mẫu hình 5 thêm 1 video hành động. Độ tin: khá.
5. **Chữ tên đoàn phim chạy trên cảnh chạy xe** (phút 2–3), tên phim xuất hiện ở ~2:30 — sau cả cú máy mở và đoạn chạy xe (cùng 19: chữ tên đoàn trên xe máy).

## Giới hạn / câu hỏi mở
- **Đếm shot đoạn 1 thiếu**: 116–163s có ≥ 6 cảnh (tờ ảnh sáng lên 1 khung/4s) mà cả ngưỡng 0.15 và 0.10 đều không bắt — có thể do chuyển cảnh hoà / cảnh rất tối.
  Trung vị 3.60s và 5.3 shot/phút của đoạn 1 **không dùng được** để so; chỉ cú máy mở 0–78.9s là chắc.
- Mốc gốc đoạn 2 ước tính ±10s. Nhãn "Whip / Slap" là tên AudioSet cho tiếng đòn — chưa nghe tai.

## Xoá dữ liệu
Media ở scratchpad phiên nice-bhabha (`s012/`) — xoá bằng `bash clean.sh v20`. Số đo đã chép vào repo `research/craft/s0_12/so_do/` (`v20_seg{1,2}_result.json`,
`v20_seg1_L0_numbers.json`, `v20_seg2_L10_numbers.json` — không lời chép).
