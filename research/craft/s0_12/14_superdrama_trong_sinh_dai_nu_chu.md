# 14 — 星火剧场 SuperDrama: "這部新出的短劇也太精彩了吧？…" (大女主 / trọng sinh, không tên phim)

- **URL**: https://www.youtube.com/watch?v=7gNuOpfCS_k
- **Thể loại**: AI short drama 9:16 hiện đại **大女主 + trọng sinh (重生)**: bà vợ 40 năm phát hiện ở đám tang chồng có 8 "con riêng", rồi tỉnh lại thời trẻ và
  giành lại sự nghiệp. Thoại tiếng Trung + phụ đề Trung — mục 1.7 trong `MAU_S0_12.md`
- **Độ dài công bố**: 2:20:20 · file tải 360×640, 9:16
- **Đoạn đã đo**:
  - (1) 0:00–3:00 (180.0s, hình và âm cùng từ giây 0);
  - (2) yêu cầu 30:30–33:00 (bằng chứng thuốc ngủ + đối đầu với chồng) — file 160.0s, bắt đầu sớm ~10s (keyframe) → mốc gốc ≈ 30:20 + t **[ước tính]**.
- **Tổng đã đo**: ~340s / 8420s (~4%)
- **Đã tải**: `v14_seg1.webm`, `v14_seg2.webm`, khúc quét 144p 5:00–65:00 (1 khung/30s) — **tất cả đã xoá sau khi viết file này**.

## Cách chọn đoạn / kiểm lặp
Tờ quét 120 khung: tông tối, ánh sáng bên, **rất ít cảnh lặp** (văn phòng, nhà, phòng họp, tiệc sinh nhật 23:00, bãi xe 22:30 có thẻ địa điểm dọc). Không thấy thẻ
"未完待续" trong 120 khung → [có thể] kênh cắt bỏ thẻ ranh giới tập khi gộp. Chọn 30:30–33:00 (khung ECU mắt 31:00, bàn tay 32:00, đối đầu 32:30).

## Phương pháp
Như 11 (`motion_cv2b.py`). `tools/audio_listen.py --lang zh` đoạn 1 giây 0–90, đoạn 2 giây file 10–100.

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| Mở đầu 0:00–3:00 | 55 | **2.83s** | 0.33–12.33s | 18.3 | **tĩnh 47%, tịnh tiến 38%**, zoom in 4%, zoom out 4%, roll 4%, thiếu dữ liệu 4% |
| Bằng chứng + đối đầu (file 160s) | 43 | **3.20s** | 0.5–12.7s | 16.1 | **tĩnh 37%, tịnh tiến 49%**, roll 5%, zoom in 5%, thiếu dữ liệu 5% |

- Âm thanh: LUFS **−9.8** / **−12.1**, LRA **7.7** / **10.1 LU**; quãng lặng **18** / **25** (dài nhất: **146.5–154.5s đoạn 2 = 8.0s**).
- Máy **động nhất trong mọi AI drama đã đo** (tĩnh 37–47% so với 61–83% ở 04, 06, 10, 11, 12) — kiểu "máy trôi chậm" ở shot dài (7: 10.3s, 54: 12.3s đoạn 1;
  12: 12.7s đoạn 2).

### Nghe bằng số (audio_listen)
- **Nhạc 56% (đoạn 1) / 69% (đoạn 2)** — thưa, bật tắt theo câu: đoạn 1 có 8 lần "không nhạc" (0, 16, 35, 61, 66, 72, 81, 87s). Tempo / giọng điệu độ khớp thấp.
- Lớp "nhạc" chứa nhiều **tiếng động** hơn nhạc: Slam 0.40 (32s), **Slap 0.39 (38s)**, **Whip 0.50 (60s)**, Knock 0.35 (46s), tiếng chuông 0.83–0.86 (22, 50s),
  Hum / Throbbing 0.42 + tim đập 0.08 (84s).
- **Đoạn 1**: 0–7s không nhạc (−70 dB) dưới giọng kể "tôi và 顾成川 cưới gần 40 năm"; nhạc rõ −21.9 dB ở 28s (8 người đàn ông đi vào), **−16.5 ở 38s** (Slap) ↔
  cắt 37.9; −18.8 ở 53s ↔ câu "chúng tôi đều là con ruột" (51.7–53.6s).
- **Đoạn 2 (giây file)**: 10–14s không nhạc; **Explosion 0.59 ở 28s ↔ cắt 28.2** (chồng chặn ở hành lang); nhạc to lên 67s (−18.3), 89s (−16.6) dưới câu "tôi
  nhận việc" (89.8–90.6s); không nhạc 93s rồi rõ lại 95s ↔ cắt 95.1 sang nhà.
- **Lặng 8.0s (146.5–154.5s)** dưới chuỗi shot chồng cầm điện thoại / tin nhắn 10:30 (#39–41) — ngoài khúc audio_listen, chỉ có silencedetect.

## Bảng shot — đoạn 1 (0:00–3:00, 55 shot)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–7 | 0.0–28.7 | WS linh đường có ảnh thờ (thẻ chữ dọc); CU bà vợ; insert ảnh | ngang; #1 xa | tịnh tiến×3, tĩnh×4 (#7 10.3s) | **giọng kể** 40 năm hôn nhân; gần như không nhạc; lặng 0–1.4, 16.2–21.3 (4 quãng) |
| 8–14 | 28.7–48.9 | WS 8 người đàn ông áo đen đi vào, quỳ lạy; CU khách xì xào | ngang; #10 cao | tịnh tiến×5, tĩnh×1, zoom in×1 | nhạc rõ 28s; Slam 32s, Slap 38s ↔ cắt 37.9 |
| 15–23 | 48.9–76.8 | insert giấy xét nghiệm ADN; CU bà vợ ↔ mẹ chồng | ngang | tịnh tiến×3, zoom in×1, tĩnh×5 | "8 người đều là con ruột"; mẹ chồng "đã biết từ lâu" |
| 24–31 | 76.8–108.4 | MS luật sư đọc di chúc; giấy rơi đầy sàn; CU bà vợ (6.9 / 7.7s) | ngang; #26 cao | tịnh tiến×1, tĩnh×6, thiếu dữ liệu×1 | tài sản cho 8 con riêng |
| 32–38 | 108.4–131.0 | tối → CU cô gái trẻ tỉnh dậy; MS chồng trẻ; **insert lịch "15"**; ECU | ngang | tịnh tiến×2, tĩnh×5 | **trọng sinh** "tôi quay lại rồi"; lặng 115.4–117.2, 123.8–125.6 |
| 39–55 | 131.0–180.0 | **insert điện thoại 10:45**; CU nắm cổ tay; CU chồng; MS hai người (#54 12.3s) | ngang | tịnh tiến×9, zoom out×2, roll×2, tĩnh×3, thiếu dữ liệu×1 | "điện thoại cứ reo"; lặng 133.2–167.6 (6 quãng) |

## Bảng shot — đoạn 2 (giây file; ≈ 30:20 + t)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–12 | 0.0–55.6 | phòng họp (màn chiếu); CU nữ ↔ CU chồng ở hành lang; #12 12.7s | ngang | tịnh tiến×7, roll×1, tĩnh×4 | "phương án vốn là tôi làm"; Explosion ở cắt 28.2 |
| 13–24 | 55.6–95.1 | **insert báo cáo xét nghiệm thuốc**; CU nữ ↔ CU cố vấn đeo kính | ngang | tịnh tiến×4, roll×1, tĩnh×7 | thuốc gây ngủ mê; "lần sau ghi âm lại"; nhận việc — nhạc to lên 89s |
| 25–35 | 95.1–134.9 | nhà: WS bếp; MS mẹ chồng bưng bát; CU nữ giả vờ uống | ngang | tịnh tiến×6, zoom in×1, tĩnh×4 | lặng ngắn 122.3–129.8 (5 quãng) |
| 36–43 | 134.9–160.0 | **insert tin nhắn 10:30**; CU chồng cầm điện thoại; MS hai người | ngang | tịnh tiến×5, zoom in×1, thiếu dữ liệu×2 | **lặng 8.0s 146.5–154.5** |

## Kỹ thuật đáng học
1. **Mở bằng giọng kể của nhân vật trên cảnh đám tang, gần như không nhạc, để tiếng động (đập, tát, quất) làm dấu câu** (0–28.7s giọng kể, nhạc −70 dB 0–7s;
   Slap ở cắt 37.9, Whip 60s). Ý đồ **[có thể]**: đặt giọng "bi kịch thật" khác hẳn nhạc nền dày của 12. Độ tin: có thể.
2. **Chuyển trọng sinh bằng bóng tối → tỉnh dậy + insert lịch + một câu "tôi quay lại rồi", có lặng xen giữa** (108.4–131.0s; lặng 115.4–117.2, 123.8–125.6). Ý đồ
   **[có thể]**: báo nhảy thời gian không cần thẻ chữ "X năm trước". Độ tin: có thể — cùng họ với mẫu hình 8 (lặng ở chỗ chuyển thời gian).
3. **Máy trôi chậm ở shot dài + ánh sáng bên tông tối** (tĩnh chỉ 37–47%, shot 10–12.7s). Ý đồ **[có thể]**: nâng "cảm giác điện ảnh" cho truyện nghiêm, khác nhịp
   cắt 2s của drama "vả mặt". Độ tin: chắc về số đo; **phản ví dụ** cho "AI drama thoại = máy tĩnh" (mẫu hình 3).
4. **Lặng dài 8s dưới cảnh đọc tin nhắn / chờ điện thoại** (146.5–154.5s đoạn 2). Ý đồ **[có thể]**: hồi hộp bằng im lặng thay vì nhạc căng. Độ tin: có thể (chưa
   nghe lớp; chỉ silencedetect).
5. **Insert giấy tờ làm bằng chứng, giữ đủ để đọc** (ADN 56.5s đoạn 1; báo cáo thuốc đoạn 2 #14; di chúc). Ý đồ **[có thể]**: truyện "thắng bằng bằng chứng" cần
   người xem thấy bằng chứng. [suy luận] với AI: giấy tờ có chữ đọc được là tài sản dựng / ghép, không phải video sinh.

## Giới hạn / câu hỏi mở
- Không thấy thẻ ranh giới tập trong tờ quét → chưa biết kênh cắt thẻ hay phim không chia tập.
- Lớp "nhạc" chủ yếu là tiếng động → "nhạc 56–69%" là trên (nhạc + hiệu ứng).
- Không biết công cụ AI.

## Xoá dữ liệu
Đã xoá `v14_seg1.webm`, `v14_seg2.webm`, tờ quét, `v14_seg*_frames/`, các tờ ảnh, thư mục `v14_seg1_L0/`, `v14_seg2_L10/` và log. Chỉ giữ `v14_seg{1,2}_result.json`,
`v14_seg1_L0_numbers.json`, `v14_seg2_L10_numbers.json` (không lời chép).
