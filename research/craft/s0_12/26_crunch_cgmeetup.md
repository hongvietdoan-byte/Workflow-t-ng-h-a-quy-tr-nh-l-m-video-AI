# 26 — Crunch (CGMeetup — Gof Animation, School of Visual Arts)

- **URL**: https://www.youtube.com/watch?v=iFUFFUb5W4w (lần tải đầu báo "not available"; bản tải trọn sau đó được, **chỉ 360p**)
- **Thể loại**: **phim ngắn hoạt hình CGI 3D tốt nghiệp**, không thoại rõ (tiếng động + nhạc), 16:9 — cậu bé mơ làm phi hành gia → lớn lên làm việc ở công ty tên lửa
  → bị đuổi → gặp sinh vật phát sáng — mục 5.2 trong `MAU_S0_12.md`
- **Độ dài công bố**: 9:32 · file tải **640×360**
- **Đoạn đã đo** (cắt từ `v26_full.mp4` → mốc **chính xác**):
  - (1) 0:00–3:00 (180.0s);
  - (2) 4:40–7:10 (150.0s).
- **Tổng đã đo**: 330s / 573s (~58%)

## Phương pháp
`analyze.py` 0.15; `motion_cv2b.py`; `tools/audio_listen.py --lang en` đoạn 1 giây 0–90 **và 90–180**, đoạn 2 giây 10–100.

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| 0:00–3:00 | 64 | 2.29s | 0.38–12.5s | 21.3 | **tĩnh 72%**, tịnh tiến 9%, zoom in 5%, roll 5%, zoom out 3% |
| 4:40–7:10 | 52 | 2.38s | 0.33–12.9s | 20.8 | tĩnh 60%, tịnh tiến 17%, zoom in 8%, zoom out 8%, roll 4% |

- Âm thanh: LUFS **−24.9** / **−20.2**, LRA 20.8 / 20.5 LU; quãng lặng **29** / 14 (dồn ở 112–158s đoạn 1 và 136–141s đoạn 2).

### Nghe bằng số (audio_listen)
- **Đoạn 1, 0–90s (giấc mơ)**: 0–5s không nhạc, Whoosh 2s, **Beep 4–6s** (đồng hồ báo thức); nhạc rõ từ 5s −31…−37 dB; **Explosion 0.54 (64s), 0.58 (80s)** — tên lửa
  phóng; điện thoại reo 38s, 86s; mưa 88s.
- **Đoạn 1, 90–180s (tỉnh dậy)**: mưa + sấm 90–100s (đêm); **Beep 0.48 106–108s** (báo thức lại); nhạc lúc rõ lúc nhỏ dưới tiếng động; **lặng ngắn dày 112–129s và
  146–158s**; chim hót 144–146s (sáng), tiếng bước 148–152s.
- **Đoạn 2 (giây 10–100)**: Gasp / Sigh 26–28s; **Explosion 0.55 (54s)** + Breaking 52–56s (tên lửa hỏng); tiếng xe 68–86s + máy ảnh chụp 74–78s; nhạc to lên 63s, 77s.

## Bảng shot — đoạn 1 (0:00–3:00)
| # | Vào–ra | Nội dung (tờ ảnh) | Máy | Âm thanh |
|---|---|---|---|---|
| 1–9 | 0.0–17.2 | **chuỗi buổi sáng**: Trái Đất → phố → đồng hồ báo thức → đánh răng → bánh mì → bàn đồ chơi tên lửa → cửa | tĩnh×9 | beep báo thức |
| 10–34 | 17.2–89.7 | **giấc mơ**: đám đông, bệ phóng, cậu bé đội mũ phi hành, tên lửa bay, hành tinh hồng, sinh vật xanh; **shot 12.5s zoom out** (77.2s) | tĩnh, tịnh tiến | nhạc rõ, nổ 64s / 80s |
| 35 | 89.7–90.6 | **đen** | — | mưa, sấm |
| 36–42 | 90.6–103.6 | phòng tối ban đêm, cậu bé trên giường, mưa | tĩnh | mưa |
| 43–55 | 103.6–130.8 | **chuỗi buổi sáng lặp lại** — cùng các bước #3–9 (đồng hồ, chân chạm sàn, đánh răng, gương, bếp) | tĩnh | beep 106–108s, lặng ngắn dày |
| 56–64 | 130.8–180.0 | lớn lên: xe buýt, toà nhà công ty tên lửa, bàn làm việc, máy tính, nhà vệ sinh công ty | tĩnh, tịnh tiến | chim hót, bước chân |

## Bảng shot — đoạn 2 (4:40–7:10)
| # | Vào–ra | Nội dung | Máy | Âm thanh |
|---|---|---|---|---|
| 1–21 | 0.0–53.7 | phòng thí nghiệm: sếp và đồng nghiệp, mô hình tên lửa, Crunch lo lắng (CU kính) | tĩnh, zoom | Gasp / Sigh |
| 22–25 | 53.7–74.0 | bãi thử: tên lửa hỏng, khói | zoom out 10.2s | **nổ 54s** |
| 26–33 | 74.0–82.4 | **cùng một khung, 8 shot 0.3–1.2s**: Crunch giữa hai toà nhà, tư thế đổi dần → dấu **"EXILE"** đóng lên hình | tĩnh, tịnh tiến | máy ảnh chụp |
| 34–38 | 82.4–99.4 | bị ném ra ngoài, rơi, đêm; **12.9s** | tĩnh | xe cộ |
| 39–52 | 99.4–150.0 | ánh xanh trong rừng / hang: **sinh vật phát sáng**, Crunch chạm tay | tịnh tiến, tĩnh | lặng 136–141s |

## Kỹ thuật đáng học
1. **Lặp lại chuỗi buổi sáng bằng đúng các shot cũ** (#3–9 ↔ #43–55) để nói "ngày nào cũng như ngày nào" sau khi tỉnh mơ. Ý đồ **[có thể]**: tương phản giấc mơ rực
   rỡ ↔ đời thường đơn điệu, không cần lời. Rẻ với video AI: dùng lại khung đầu / bố cục, chỉ đổi một chi tiết. Độ tin: chắc về cấu trúc (tờ ảnh).
2. **Mở bằng giấc mơ 0–89.7s rồi tỉnh dậy qua 1s đen + tiếng mưa** — cùng họ mẫu hình 11 (mở bằng cảnh tương lai / giấc mơ rồi quay về: 11, 23, 26) → **3 video**.
   Dấu chuyển: **đen + đổi hẳn âm thanh** (nhạc → mưa), đúng mẫu hình 8 (im lặng / đổi âm ở chỗ chuyển thực tại).
3. **Chuỗi "cùng khung, đổi tư thế" (8 shot trong 8s) + chữ "EXILE" đóng dấu** để kể việc bị đuổi việc trong vài giây — ellipsis bằng jump cut. Ý đồ **[có thể]**:
   nén thời gian + hài. Độ tin: chắc về hình.
4. **Máy tĩnh 60–72%** ở phim hoạt hình sinh viên — cùng họ 25 (61%), khác phim quay thật hành động. Mẫu hình 3 (mức động theo phong cách người làm).
5. **Báo thức beep làm "móc âm thanh"** mở cả hai buổi sáng (4s và 106s) — lặp âm để người xem nhận ra vòng lặp.

## Giới hạn / câu hỏi mở
- File 360p: OpenCV và ngưỡng cắt ổn, nhưng chi tiết mặt khó xem.
- Phần 3:00–4:40 và 7:10–9:32 chưa đo (kết phim).

## Xoá dữ liệu
Media ở scratchpad phiên nice-bhabha (`s012/`: `v26_full.mp4`, `v26_seg1.mp4`, `v26_seg2.mp4`) — `bash clean.sh v26` + xoá `v26_full.mp4`. Số đo ở
`research/craft/s0_12/so_do/` (`v26_seg{1,2}_result.json`, `v26_seg1_L0_numbers.json`, `v26_seg1_L90_numbers.json`, `v26_seg2_L10_numbers.json`).
