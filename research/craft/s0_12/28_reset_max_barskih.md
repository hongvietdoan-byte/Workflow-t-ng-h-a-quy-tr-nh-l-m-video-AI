# 28 — RESET (Max Barskih — phim ngắn AI khoa học viễn tưởng, dự thi Higgsfield Global Film Festival)

- **URL**: https://www.youtube.com/watch?v=BMLTQ0ouz1U
- **Thể loại**: **phim ngắn làm bằng AI**, sử thi / viễn tưởng, khổ rộng (1280×550 ≈ 2.33:1 — đã xác nhận, không phải 16:9 như `MAU_S0_12.md` đoán), lời kể
  tiếng Anh ở phần sau — mục 6.2 trong `MAU_S0_12.md`
- **Độ dài công bố**: 11:07 · file tải 1280×550
- **Đoạn đã đo**:
  - (1) 0:00–3:00 (180.0s; đen 0–1.8s);
  - (2) yêu cầu 8:10–10:40 — file 160.0s, bắt đầu sớm ~10s → mốc gốc ≈ 8:00 + t **[ước tính]**.
- **Tổng đã đo**: ~340s / 667s (~51%)

## Cách chọn đoạn
Tờ quét: 3:00–6:40 **trận đánh** (quân đội, sư tử / gấu trắng làm thú cưỡi, người thằn lằn); 6:50–8:00 hoàng hậu đội vương miện nhọn khóc, vua thằn lằn; 8:10–10:10
**thiên thạch → Trái Đất → lụt nhấn chìm thành phố**; 10:20–10:40 vườn địa đàng; 10:50 chữ "RESET". Chọn 8:10–10:40 = cao trào + kết.

## Phương pháp
`analyze.py` 0.15; `motion_cv2b.py`; `tools/audio_listen.py --lang en` đoạn 1 giây 0–90, đoạn 2 giây file 10–100.

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| 0:00–3:00 | 64 | **2.56s** | 0.92–6.6s | 21.3 | **tĩnh 80%**, zoom in 12%, tịnh tiến 6%, roll 2% |
| ≈ 8:00–10:40 | 40 | 3.04s | 0.72–19.2s | 15.0 | **tĩnh 75%**, tịnh tiến 8%, zoom in 5%, zoom out 5%, thiếu dữ liệu 5% |

- Âm thanh: LUFS **−16.8** / **−12.3**, LRA 13.3 / 13.1 LU; quãng lặng 9 (dồn 78.8–94s) / **0**.
- Đoạn 1: **không shot nào > 6.6s**, gần như mọi shot 1.5–5.5s — độ dài một lần gen video AI, cắt bớt đầu / đuôi.

### Nghe bằng số (audio_listen)
- **Đoạn 1 (0–90s)**: nhạc rõ **−14 dB ngay từ 0s** (Bang 0.46 ở 0s); Door / Slam rải 2–38s (giáp, vũ khí); Roar 0.48 (64s) — thú gầm; Vehicle 42–62s (đoàn quân
  di chuyển); **80–84s không nhạc** (Timpani 82–84s rồi nhạc về −26); 88s nhạc nhỏ dưới câu nói.
- **Đoạn 2 (giây file 10–100)**: nhạc **liên tục −20 dB**, Cello (40s); **lời kể tiếng Anh dài 68–100s** (một đoạn độc thoại về "bắt đầu lại") trên cảnh lụt / thành
  phố trắng; không quãng lặng nào trong 160s.

## Bảng shot — đoạn 1 (0:00–3:00)
| # | Vào–ra | Nội dung (tờ ảnh) | Máy | Âm thanh |
|---|---|---|---|---|
| 1–14 | 0.0–31.8 | **hàng quân** giáp bạc / giáp đen, cờ, giáo; tướng trên ngựa trắng; cổ rồng | tĩnh×14 | nhạc −14, tiếng giáp |
| 15–27 | 31.8–63.6 | CU mắt bò sát; thú cưỡi sư tử / gấu trắng; CU mặt người, mặt thằn lằn | tĩnh, zoom in | Roar 64s |
| 28–33 | 63.6–88.3 | **mặt trăng, núi tuyết, cánh cửa đen, người đi vào hành lang** — shot 4.6–5.2s | tĩnh | **không nhạc 80–84s**, timpani |
| 34–64 | 88.3–180.0 | cung điện: hoàng hậu áo trắng vương miện nhọn, vua thằn lằn, tượng cánh, CU môi (#53), bàn tay | tĩnh, zoom in×5 | nhạc nhỏ dưới câu nói |

## Bảng shot — đoạn 2 (giây file; ≈ 8:00 + t)
| # | Vào–ra | Nội dung | Máy | Âm thanh |
|---|---|---|---|---|
| 1–9 | 0.0–49.1 | vua + hoàng hậu; vật hình vỏ sò; **mặt trăng → thiên thạch → Trái Đất bị đâm** | zoom out 12.4s, tĩnh | nhạc liên tục |
| 10–24 | 49.1–97.4 | biển, thành phố tháp nhọn, người đứng nhìn, **sóng thần nhấn chìm thành phố** | tĩnh | Cello 40s |
| 25–36 | 97.4–128.1 | thành phố trắng trên núi, người mặc áo bạc nhìn lên, khăn trắng bay, bậc thang | tĩnh | **lời kể 68–100s** |
| 37 | 128.1–147.2 | **19.2s zoom in → khung trắng** | zoom in | — |
| 38–40 | 147.2–160.0 | **vườn địa đàng**: cây, ánh vàng, hai người ôm nhau | tĩnh | — |

## Kỹ thuật đáng học
1. **Phim AI: máy tĩnh 75–80%, shot 1.5–5.5s, không shot nào dài** (trừ cú trắng 19s) — giống 24 (AI, < 6s) và khác phim quay thật cùng thể loại. Ý đồ
   **[suy luận]**: dùng phần ổn định nhất của mỗi lần gen; chuyển động máy AI dễ lỗi nên để tĩnh. Liên hệ pipeline: mặc định shot tĩnh + ngắn là hợp lý với AI;
   chuyển động máy chỉ ở shot then chốt. Độ tin: khá (2 video AI).
2. **Kể sử thi bằng chuỗi "tableau" tĩnh** (hàng quân, thú cưỡi, chân dung) thay vì hành động liên tục — tránh điểm yếu của AI (đánh nhau, tay chân). Độ tin: có thể.
3. **Tắt nhạc 4s + timpani ở chỗ chuyển từ chiến trường sang cung điện** (80–84s) — mẫu hình 8 (im lặng ở chỗ chuyển nơi / thời gian).
4. **Lời kể đặt trên cảnh thảm hoạ, nhạc liên tục không một quãng lặng** ở cao trào — ngược với "tắt nhạc dưới khoảnh khắc then chốt" (mẫu hình 5): ở đây lời kể là
   điểm nhấn, nhạc là thảm nền. Hai cách cùng tồn tại → ý nghĩa do ngữ cảnh.
5. **Chuyển kết bằng zoom in vào khung trắng 19s** rồi mở ra vườn địa đàng — "reset" bằng hình (trắng = xoá sạch).
6. **Mặt người AI đứng yên, cảm xúc bằng nước mắt / CU môi** (tờ quét 7:10–7:30) — cận mặt tinh tế là điểm yếu chung của AI (S0.14 T5): phim chọn CU tĩnh, ít biểu
   cảm chuyển động.

## Giới hạn / câu hỏi mở
- Chưa rõ công cụ AI cụ thể (Higgsfield?) — mô tả kênh không ghi.
- Mốc gốc đoạn 2 ước tính ±10s; 3:00–8:00 (trận đánh) chưa đo — đáng đo để xem AI làm cảnh đánh nhau thế nào.
- Lời kể: chỉ ghi ý, không chép.

## Xoá dữ liệu
Media ở scratchpad phiên nice-bhabha (`s012/`) — `bash clean.sh v28`. Số đo ở `research/craft/s0_12/so_do/` (`v28_seg{1,2}_result.json`, `v28_seg1_L0_numbers.json`,
`v28_seg2_L10_numbers.json`).
