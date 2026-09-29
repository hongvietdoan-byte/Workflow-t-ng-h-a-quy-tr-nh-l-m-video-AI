# 22 — Not Like Us (Kendrick Lamar, MV — đạo diễn Dave Free & Kendrick Lamar)

- **URL**: https://www.youtube.com/watch?v=H58vbez_m4E (kênh chính chủ)
- **Thể loại**: **MV rap kể chuyện / trình diễn nhóm đông** quay thật 16:9 (file 1048×720 — viền), khu phố Compton, nhiều bối cảnh — mục 4.1 trong `MAU_S0_12.md`
- **Độ dài công bố**: 5:55 · file tải 1048×720
- **Đoạn đã đo**:
  - (1) 0:00–3:00 (180.0s; nhiều khung đen ngắn 2.5–19s — hành lang tối);
  - (2) file `v22_seg2f` 184s — **2:54.9 + t** (mốc chính xác bằng tương quan chéo tiếng với bản tải trọn, `fix_audio.py`; bản tải theo đoạn bị cụt tiếng).
- **Tổng đã đo**: ~354s / 354s (trọn MV, hai đoạn chồng ~5s)
- **Bài hát có bản quyền**: whisper chỉ dùng lấy mốc câu, **không chép / lưu lời**.

## Phương pháp
`analyze.py` 0.15; `motion_cv2b.py`; `tools/audio_listen.py --lang en … song` đoạn 1 giây 0–90, đoạn 2 giây 0–90; **`beat_align.py`** (librosa, dung sai ±0.08s)
đo điểm cắt so với phách.

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| 0:00–3:00 | 93 | **1.46s** | 0.33–9.9s | **31.0** | tĩnh 42%, **thiếu dữ liệu 19%** (shot < 0.4s), tịnh tiến 15%, roll 12%, zoom in 5%, zoom out 6% |
| cuối MV (184s) | 50 | 2.23s | 0.79–20.2s | 16.3 | **zoom out 24%, zoom in 22%**, tịnh tiến 22%, tĩnh 20%, roll 12% |

- Âm thanh: LUFS **−10.9** / **−10.8**, LRA **7.5** / **3.0** LU (rất nén — kiểu master nhạc rap); quãng lặng 12 (đều trong 0–40s) / 2 (**135.6–146.3s**).
- **Điểm cắt so với phách** (BPM ~99.4):
  - đoạn bài hát 44–180s: 64 cắt, trúng phách **27%** = ngẫu nhiên 27%; trúng nửa phách 53% = ngẫu nhiên 53%;
  - đoạn mở 0–40s (chưa vào bài): 27 cắt, trúng phách 44% so với ngẫu nhiên 27%;
  - cuối MV: 49 cắt, trúng phách 22% so với ngẫu nhiên 27%.
  → **trong bài hát, điểm cắt không bám phách** (librosa có thể lệch pha — xem Giới hạn).

### Nghe bằng số (audio_listen)
- **Đoạn 1**: 0–9s gần câm (−55…−63 dB) dưới cảnh toà nhà + hành lang tối; 10–18s nhạc dạo −9…−24; **20–38s nhạc tắt (−65…−72)**, nhãn **Knock 0.88 (20s)**,
  Knock 0.50 (22s), **Whistle 0.97 (36s)** — đoạn "gõ cửa / huýt sáo" không nhạc; **bài hát vào ~40–44s** (nhạc −8…−12 dB, giọng −20 dB đều).
- **Đoạn 2**: nhạc −8…−11 dB phẳng suốt 0–90s, hai chỗ tụt ngắn −22…−24 (12–14s, 64–66s — ngắt trong bài); **bài hết ~135s**, lặng 135.6–146.3s.

## Bảng shot — đoạn 1 (0:00–3:00)
| # | Vào–ra | Nội dung (tờ ảnh) | Máy | Âm thanh |
|---|---|---|---|---|
| 1–24 | 0.0–19.3 | WS toà nhà ban ngày → **hành lang tối đen trắng, nhiều shot 0.3–1s gần như đen**, người mặc trắng trong hành lang | tĩnh / thiếu dữ liệu | gần câm → nhạc dạo |
| 25–26 | 19.3–38.0 | **hai shot dài 9.9s + 8.8s**: phòng trắng mù sương, mặt nạ, bàn DJ | tĩnh | **không nhạc: gõ cửa, huýt sáo** |
| 27–48 | 38.0–93.7 | bàn xoay đĩa, **chữ tên bài**, nhóm ngồi ghế trong phòng trắng, người đứng giữa; phòng khách với ghế sofa, loa | tĩnh, roll, tịnh tiến | **bài hát vào ~44s** |
| 49–55 | 93.7–111.0 | **nền xanh dương phẳng: người đập piñata** (shot 0.4–1.5s liên tiếp) | roll, zoom out | — |
| 56–80 | 111.0–154.4 | đám đông khu phố, xe thể thao đỏ, quán burger, nhảy trong quán | tĩnh, tịnh tiến | — |
| 81–93 | 154.4–180.0 | **bãi container trắng: hai người nhảy**, MCU người mặc vest | tĩnh, zoom | — |

## Bảng shot — cuối MV (giây file)
| # | Vào–ra | Nội dung | Máy | Âm thanh |
|---|---|---|---|---|
| 1–10 | 0.0–21.8 | bãi container: nhảy đôi, gọi điện | tĩnh, zoom | nhạc phẳng |
| 11–24 | 21.8–75.6 | đám đông; người nhảy trên nền trời; sân nhà, nhóm đàn ông; phòng trắng (mặt nạ, trọng tài); **shot 15.8s zoom out** | zoom in / out xen kẽ | — |
| 25–46 | 75.6–134.8 | phòng khách đen trắng (mắt cá), khu phố đông, container, phòng trắng | tịnh tiến, zoom | — |
| 47 | 134.8–149.9 | **15.1s — người áo xanh cầm vật trong tối** | tịnh tiến | **lặng 135.6–146.3s (bài hết)** |
| 48–50 | 149.9–184.0 | lồng chim; **20.2s** cảnh kết; chữ "directed by" 12.8s | tịnh tiến, roll | — |

## Kỹ thuật đáng học
1. **Cắt không bám phách dù là MV rap nhịp mạnh** (27% = ngẫu nhiên, hai đoạn). Ý đồ **[có thể]**: điểm cắt theo **câu rap / đổi bối cảnh**, không theo phách —
   mỗi bối cảnh (phòng trắng, piñata, quán burger, container) ứng một đoạn lời. Đây là căn cứ đã dùng để sửa `editing.md` E4 (2026-09-29): bám câu / cảnh hay bám
   phách là lựa chọn theo ngữ cảnh. Độ tin: khá (librosa, chưa nghe tai).
2. **Mở MV bằng ~40s không nhạc bài**: hành lang tối + gõ cửa + huýt sáo, rồi mới vào bài. Cùng "đoạn thiết lập không nhạc / nhạc nhỏ rồi mới vào bài" (18, 23, 09, 20)
   → **5 video**. Độ tin: khá.
3. **Nhiều "thế giới" hình tách hẳn nhau** (phòng trắng mù sương, nền xanh phẳng, khu phố thật, bãi container trắng, phòng đen trắng), cắt qua lại suốt bài. Ý đồ
   **[có thể]**: mỗi thế giới một "giọng" (ẩn dụ / đời thật / trình diễn). Liên hệ video AI: dễ làm bằng bối cảnh dựng riêng từng khối gen.
4. **Cuối MV: zoom in / out chiếm 46%** (so với 11% ở đoạn 1) — máy đẩy / lùi chậm trên đám đông và người trình diễn. Chưa rõ vì sao đổi (có thể do phần cuối nhiều
   cảnh đám đông quay từ xa).
5. **Kết bằng lặng 10s sau khi bài hết, rồi hai shot dài 15–20s + chữ đạo diễn** — thở ra sau 2 phút nhạc nén LRA 3.

## Giới hạn / câu hỏi mở
- `beat_align.py` dùng librosa: phách có thể lệch pha → "không bám phách" cần **nghe tai** vài điểm cắt (đã ghi ở TONG_HOP mục người dùng nghe).
- 19% shot đoạn 1 quá ngắn cho OpenCV (< 0.4s) → tỉ lệ máy tĩnh chỉ tham khảo.
- Đoạn 2 chồng ~5s với đoạn 1 (2:54.9–3:00).

## Xoá dữ liệu
Media ở scratchpad phiên nice-bhabha (`s012/`: `v22_seg1.webm`, `v22_seg2*.`, `v22_full.mp4`) — `bash clean.sh v22` + xoá `v22_full.mp4`, `v22_seg2f.mkv`.
Số đo ở `research/craft/s0_12/so_do/` (`v22_seg1_*`, `v22_seg2f_*`, `v22_beat.jsonl` — không lời chép).
