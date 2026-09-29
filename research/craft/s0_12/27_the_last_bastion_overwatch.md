# 27 — Overwatch Animated Short "The Last Bastion" (Blizzard)

- **URL**: https://www.youtube.com/watch?v=to8yh83jlXg (kênh chính chủ PlayOverwatch)
- **Thể loại**: **phim ngắn CGI game, không thoại** — robot chiến tranh Bastion tỉnh dậy trong rừng, bạn là một chú chim — 16:9 — mục 5.4 trong `MAU_S0_12.md`.
  **Mẫu gần với "video game kể chuyện" của dự án FF.**
- **Độ dài công bố**: 7:22 · file tải 1280×720
- **Đoạn đã đo**:
  - (1) 0:00–3:00 (180.0s; đen 3.9–5.9s, 9.7–10.1s — logo);
  - (2) **4:13.8–6:53.8** (`v27_seg2f`, cắt từ bản tải trọn → mốc chính xác; bản tải theo đoạn bị cụt tiếng).
- **Tổng đã đo**: 340s / 443s (~77%)

## Phương pháp
`analyze.py` 0.15; `motion_cv2b.py`; `tools/audio_listen.py --lang en` đoạn 1 giây 0–90, đoạn 2 giây 10–100.

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| Mở 0:00–3:00 (rừng) | 34 | 3.48s | 1.42–26.9s | 11.3 | **tĩnh 88%**, tịnh tiến 9%, roll 3% |
| 4:14–6:54 (đồng cỏ → hồi ức chiến tranh) | 32 | 3.81s | 1.16–15.5s | 12.0 | tĩnh 53%, tịnh tiến 19%, **zoom in 16%**, zoom out 9% |

- Âm thanh: LUFS **−25.7** / **−11.4** (chênh **14 dB**), LRA 15.4 / **25.4** LU (đoạn 2 dải động rất rộng); quãng lặng 16 / 8.

### Nghe bằng số (audio_listen)
- **Đoạn 1 (0–90s)**: 0–23s không nhạc (logo + tiếng rừng, nhãn "Environmental noise"); nhạc nhỏ dưới tiếng rừng từ 23s (−40…−50), rõ dần −31 (50–54s), to lên 73s;
  Chink / clink 46s; **Whistling 0.42 (88s)** — chim hót. Không câu thoại nào.
- **Đoạn 2 (giây 10–100)**: nhạc rõ −30…−39 dưới cảnh đồng cỏ; **nhạc to vọt −13 dB ở 58s** (vào hồi ức chiến tranh); tiếng máy móc 96s. Sau 100s: **lặng 114.7–120.5s
  (5.8s)** ngay sau loạt bắn.

## Bảng shot — đoạn 1 (0:00–3:00)
| # | Vào–ra | Nội dung (tờ ảnh) | Máy | Âm thanh |
|---|---|---|---|---|
| 1 | 0.0–26.9 | logo, đen, **WS rừng — máy lướt chậm 17s** | tịnh tiến | không nhạc, tiếng rừng |
| 2–9 | 26.9–64.2 | chim vàng: tổ, CU mắt, bay | tĩnh×8 | nhạc nhỏ dưới tiếng rừng |
| 10–16 | 64.2–81.3 | rêu phủ, **lộ dần robot** (đèn mắt xanh, bàn tay, thân) | tĩnh | nhạc to lên 73s |
| 17–27 | 81.3–136.6 | chim đậu trên robot; **bản đồ hologram** (#20); robot đứng dậy đi; **14.5s** WS | tĩnh | chim hót 88s |
| 28–34 | 136.6–180.0 | bàn tay robot, chim trên đá, **16.5s** WS rừng | tĩnh | — |

## Bảng shot — đoạn 2 (4:13.8 + t)
| # | Vào–ra | Nội dung | Máy | Âm thanh |
|---|---|---|---|---|
| 1–15 | 0.0–60.4 | **đồng cỏ trời xanh**: robot nhìn quanh, xen WS mây / cỏ; tàn tích súng | tĩnh, zoom | nhạc rõ dưới nền |
| 16–17 | 60.4–85.0 | **hồi ức chiến tranh: khung đỏ cam, lửa, robot bắn** — 9.8s + **14.8s zoom in** | tịnh tiến, zoom in | **nhạc vọt −13 dB** |
| 18 | 85.0–88.9 | **CU mắt robot chuyển đỏ** (về hiện tại, chế độ chiến đấu) | zoom out | — |
| 19–27 | 88.9–124.0 | robot bắn vào rừng / đồng cỏ; WS trống | tĩnh, zoom in | **lặng 114.7–120.5s** |
| 28–32 | 124.0–160.0 | **chim vàng đậu lên nòng súng** (#25, #28), robot dừng; **15.5s zoom in** | zoom in, tĩnh | — |

## Kỹ thuật đáng học
1. **Máy gần như đứng yên (88%) trong 3 phút mở** — kể bằng chuyển động của nhân vật (chim bay, rêu rơi, robot cựa mình) chứ không bằng máy. Ý đồ **[có thể]**: nhịp
   yên bình trước khi hồi ức ập tới. Liên hệ video AI: shot tĩnh là loại model làm ổn nhất → mẫu CGI game chuyên nghiệp cũng chọn tĩnh. Độ tin: chắc về số.
2. **Hồi ức chiến tranh = đổi màu cả khung (đỏ cam) + nhạc vọt 14 dB + zoom in dài**, về hiện tại bằng **CU mắt đổi màu** (xanh → đỏ). Mẫu hình 11 / dấu hiệu hồi tưởng
   (`knowledge/craft/`): người xem biết ngay là hồi ức mà không cần chữ. Liên hệ #8: lỗi "hồi tưởng không có dấu hiệu" — đây là cách làm có dấu hiệu rõ. Độ tin: chắc.
3. **Lặng ~6s ngay sau loạt bắn** rồi chim quay lại — mẫu hình 8 (im lặng ở chỗ chuyển trạng thái) + 5 (tắt nhạc dưới khoảnh khắc then chốt).
4. **Mở 23s không nhạc, chỉ tiếng rừng**, nhạc vào nhỏ dưới tiếng rừng — cùng "đoạn thiết lập không nhạc rồi mới vào nhạc" (18, 23, 09, 20, 22, 24) → **7 video**.
5. **Không một câu thoại** trong 340s đo — kể bằng hành động + âm thanh (cùng nhóm 25, 09, 18 "kể không lời").
6. **Dải động rất rộng** (LUFS −25.7 → −11.4; LRA 25.4) — phim game chiếu rạp / YouTube dám để đoạn yên rất nhỏ. Với video mạng xã hội (xem trên điện thoại) cần cân
   nhắc: pipeline đang chuẩn hoá độ to (`loudness_normalize`).

## Giới hạn / câu hỏi mở
- Chưa nghe tai: tiếng "Whistling" có phải chim không; nhạc có chủ đề riêng cho chim không.
- 3:00–4:14 (robot đi qua rừng, gặp tàn tích) chưa đo.

## Xoá dữ liệu
Media ở scratchpad phiên nice-bhabha (`s012/`: `v27_seg1.webm`, `v27_seg2*.`, `v27_full.mp4`) — `bash clean.sh v27` + xoá `v27_full.mp4`, `v27_seg2f.mkv`.
Số đo ở `research/craft/s0_12/so_do/` (`v27_seg1_*`, `v27_seg2f_*`).
