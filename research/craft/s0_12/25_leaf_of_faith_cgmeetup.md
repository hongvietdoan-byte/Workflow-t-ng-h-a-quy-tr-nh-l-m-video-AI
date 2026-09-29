# 25 — Leaf of Faith (CGMeetup · Media Design School)

- **URL**: https://www.youtube.com/watch?v=qpv7sEjx52Y
- **Thể loại**: phim ngắn **hoạt hình CGI 3D** tốt nghiệp, gần như không thoại — một cây hoa nhỏ trong chậu ở căn hộ tối, bên cạnh những cây héo đáng sợ, tìm
  đường ra ánh sáng — mục 5.1 trong `MAU_S0_12.md`
- **Độ dài công bố**: 3:03 · file tải 1280×720 (tải lại bằng `--download-sections` lần 2, lần 1 phiên trước lỗi ffmpeg)
- **Đoạn đã đo**: **trọn phim** 0:00–3:03 (183.0s; tiếng đủ 183.0s — đã kiểm độ dài tiếng, xem TONG_HOP "Lỗi tải cụt tiếng")
- **Đã tải**: `v25_seg1.mkv` — **CHƯA xoá** (phiên tạm dừng 29/09, xem TONG_HOP "Bàn giao").

## Phương pháp
`analyze.py` ngưỡng 0.15, `motion_cv2b.py`, `tools/audio_listen.py --lang en` hai cửa sổ 0–90s và 90–183s.

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| Trọn phim 0:00–3:03 | 33 | **3.96s** | 0.38–24.2s | 10.8 | **tĩnh 61%**, zoom in 15%, tịnh tiến 9%, zoom out 6%, roll 3%, thiếu dữ liệu 6% |

- Âm thanh: LUFS **−27.9** (nhỏ nhất trong 28 video), LRA **22.6 LU**; quãng lặng **46** (nhiều nhất ở 0–50s và 122–183s).
- Nhạc (audio_listen): 0–90s **94%** nhưng nhỏ (−37…−50 dB); 90–183s **53%**. Lớp giọng: whisper chỉ bắt **một câu** (78.6–80.6s); còn lại là tiếng thở / rên của
  nhân vật (lớp giọng −30…−50 dB từng quãng).

### Nghe bằng số (audio_listen)
- 0–48s: nhạc rất nhỏ −37…−50 dB, lặng ngắn dày 0–15s; nhãn "Tap / Thunk / Knock" (2–14s), **"Ding-dong" 0.39–0.43 lặp 38–46s** (khi lò sưởi bật, shot 6).
- **50–58s nhạc lên −23 dB** (hoa co rúm vì hơi nóng / bóng tối — shot 8–10).
- 74s "Scary music" (0.08, điểm thấp), **76s "Gong" 0.80** — giữa cảnh cây héo khổng lồ (#11–13).
- 90–114s nhạc −31…−45; **116–120s nhạc lên đỉnh −19 dB** (hoa bị hất ra ngoài cửa sổ, CU trên nền trời — #25–26) → **122–128s tụt −43 → −67 dB, lặng 122.6–130.7s**
  đúng lúc **mở ra khu vườn trên mái** (#27 121.2s, #28 127.8s); chuông "Ding" 128s. Từ 148s lớp giọng câm (−120) — chữ cuối phim + cảnh vui (cây xương rồng).

## Bảng shot (trọn phim, ngưỡng 0.15)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1 | 0.0–24.2 | **WS kệ, chậu hoa nhỏ — shot mở 24.2s tĩnh** (6× trung vị) | ngang | tĩnh | lặng dày; tiếng gõ |
| 2–7 | 24.2–53.8 | hướng dương héo cạnh bên; CU hoa (mặt biểu cảm); **lò sưởi đỏ** (#6); hoa vươn lá | ngang | tĩnh×4, roll, tịnh tiến | "Ding-dong" 38–46s |
| 8–13 | 53.8–72.6 | hướng dương khô như quái vật (#8); CU hoa sợ (#9); **cây héo hình ma** (#11) | ngang / thấp | zoom in×2, zoom out×2, tĩnh | **nhạc lên −23 dB** |
| 14–21 | 72.6–101.6 | **tối**: hoa bứt khỏi chậu, bò trên sàn; đất vỡ (#19); CU giận dữ (#18, #20) | thấp sát sàn | tĩnh×5, tịnh tiến×2, zoom in | "Save yourself" 78.6s; Gong 76s |
| 22–26 | 101.6–121.2 | cửa sổ ánh sáng lạnh (#22); **góc từ trên nhìn xuống ống thông gió** (#23); CU hoa trên nền trời (#26) | cao / thấp | tĩnh, zoom in×2 | nhạc lên đỉnh −19 dB 116–120s |
| 27–29 | 121.2–150.0 | **WS vườn trên mái, trời xanh** (6.6s); hoa giữa vườn (16.5s); vẫy tay | ngang | tĩnh | **nhạc tụt gần câm, lặng 122.6–130.7s**; chuông 128s |
| 30–33 | 150.0–183.0 | chữ cuối (21.9s); cây xương rồng (cảnh vui); logo trường | — | tĩnh | lặng dần |

## Kỹ thuật đáng học
1. **Kể trọn truyện không lời** (1 câu thoại trong 183s): biểu cảm mặt hoa ở CU + tiếng thở / rên + nhạc nhỏ. Ý đồ **[chắc — theo mô tả phim trong MAU_S0_12]**:
   kể bằng hình. Cùng họ với 09 (2:38 đầu không thoại), 18 (montage không thoại), 27 (Bastion).
2. **Nhạc lên đỉnh ngay TRƯỚC khoảnh khắc thoát ra, rồi tụt gần câm khi không gian mở ra** (−19 dB 116–120s → −67 dB 124s; khu vườn mái ở 121.2s). Ý đồ
   **[có thể]**: để người xem "thở ra" cùng nhân vật bằng tiếng gió / chuông thay nhạc. Đây là **phản ví dụ một phần cho mẫu hình 7** ("nhạc vào / trồi lên ở shot mở
   không gian") — cùng loại khoảnh khắc, cách làm ngược lại. Độ tin: khá về số đo, có thể về ý đồ.
3. **Vật vô tri thành nhân vật đe doạ**: cây héo / hướng dương khô được dựng như quái vật ở góc thấp, trong tối, kèm Gong 0.80. Ý đồ **[có thể]**: cho người xem
   nỗi sợ theo tầm mắt của cây hoa nhỏ.
4. **Máy chủ yếu đứng yên (61%)** — chuyển động nằm ở nhân vật. Cùng hướng với phim CGI nhiều hành động nhỏ (khác 05 RISE 43% tĩnh). Độ tin: có thể.
5. **Shot mở 24.2s tĩnh** (≈ 6× trung vị) — cùng mẫu hình 9.

## Giới hạn / câu hỏi mở
- 360p/720p hình tối (#14–21) → OpenCV "thiếu dữ liệu" 6%.
- "Ding-dong" / "Gong" là nhãn AST — chưa nghe tai (có thể là tiếng lò sưởi / hiệu ứng tổng hợp).

## Xoá dữ liệu
**CHƯA xoá** media (phiên tạm dừng) — phiên sau chạy `bash clean.sh v25`. Số đo đã chép vào repo ở `research/craft/s0_12/so_do/` (`v25_seg1_result.json`, `v25_seg1_L0_numbers.json`,
`v25_seg1_L90_numbers.json` — không lời chép).
