# 24 — Outliers x KLING AI: New Born — LUNA (MV làm bằng Kling AI)

- **URL**: https://www.youtube.com/watch?v=NDCjrBg7w2E (kênh chính chủ "Kling AI", tag #klingavatar)
- **Thể loại**: **MV ca sĩ ảo làm bằng AI** (Kling), 16:9, 1280×720 — đối tác sáng tạo "Outliers" — mục 4.4 trong `MAU_S0_12.md`.
  **Mẫu gần nhất với pipeline** (video AI thật, có hát khớp môi).
- **Độ dài công bố**: 2:44 · đo **trọn MV** (164.0s)
- **Tiếng**: bản tải theo đoạn bị **cụt tiếng ở 107s** → số âm thanh cũ sai; đo lại trên `v24_seg1f.mkv` (hình cũ + tiếng từ bản tải trọn, `fix_audio.py`).
- **Bài hát có bản quyền**: whisper chỉ lấy mốc câu, không chép lời.

## Phương pháp
`analyze.py` 0.15 (hình); `motion_cv2b.py`; `tools/audio_listen.py --lang en … song` giây 0–90 và 90–164 trên `v24_seg1f`; ebur128 + silencedetect trên `v24_seg1f`;
`beat_align.py` 0–164s.

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| Trọn MV 0:00–2:44 | **111** | **1.28s** | 0.30–5.8s | **40.6** | tĩnh 32%, **thiếu dữ liệu 19%**, zoom in 16%, tịnh tiến 15%, roll 10%, zoom out 8% |

- Âm thanh (tiếng đủ): LUFS **−16.1**, LRA 13.6 LU; **không quãng lặng** < −50 dB trừ đuôi (161–164s).
- **Điểm cắt so với phách** (BPM ~136): 110 cắt, trúng phách **33%** so với ngẫu nhiên 36%; nửa phách 65% so với 73% → **không bám phách**.
- 28 shot ≤ 0.5s; không shot nào > 5.8s (mỗi lần gen Kling 5–10s → mọi clip đều bị cắt ngắn lại).

### Nghe bằng số (audio_listen, tiếng đủ)
- **0–34s**: nhạc −28…−38 dB, **giọng hát gần như chưa vào** (−40…−90); nhãn Vehicle 4–16s (tàu điện), **Explosion 18–24s + Waves 20s** — sóng nước tràn sân ga.
- **36–148s**: giọng hát đều −20…−26 dB trên nhạc −16…−24 (nhạc to lên 63s, 122s); nhãn côn trùng (Fly / Mosquito) 52s, 120s — lớp âm môi trường mỏng dưới bài.
- **148–164s**: giọng tắt (−65), nhạc lùi −35…−59; tiếng tàu + cửa kéo 154–160s — **quay về sân ga** (khung kết).

## Bảng shot (trọn MV)
| # | Vào–ra | Nội dung (tờ ảnh) | Máy | Âm thanh |
|---|---|---|---|---|
| 1–19 | 0.0–25.6 | sân ga tàu điện: cô gái tai nghe, tàu chạy qua, chữ "NEW BORN", biển quảng cáo **sóng biển** | tĩnh, tịnh tiến | tiếng tàu, chưa hát |
| 20–33 | 25.6–40.0 | **nước tràn từ biển quảng cáo** ngập sân ga → dưới nước, cá bơi trong toa, cô gái chìm | zoom, tịnh tiến | Explosion + Waves |
| 34–42 | 40.0–61.1 | hoàng hôn trên biển, khối pha lê, rừng nhiệt đới, bước lên bờ | zoom, tịnh tiến | **giọng hát vào ~36s** |
| 43–52 | 61.1–68.2 | **hát giữa trường sao — cùng một khung, cắt vụn 7 lần 0.3–0.4s** (65.8–68.2) | roll, thiếu dữ liệu | nhạc to lên 63s |
| 53–77 | 68.2–~100 | hát trên đồng hoa dưới trời xoáy sao; cá, lá rừng; **pha lê tím nổ → khung trắng** | zoom, roll | — |
| 78–90 | ~100–125 | **đời thường**: cầm kem, bếp, bể cá vàng, tàu, siêu thị, thành phố hoàng hôn | tĩnh, zoom | — |
| 91–111 | ~125–164 | đêm trăng trên biển: hát, bước trên mặt nước sáng, sứa; về sân ga | tĩnh, zoom | giọng tắt 148s |

## Kỹ thuật đáng học
1. **Nhịp 40 shot/phút, không shot nào > 6s, trong khi Kling gen 5–10s / lần** → mọi clip bị cắt lấy phần tốt nhất. Ý đồ **[suy luận]**: cắt ngắn giấu lỗi AI (tay,
   chuyển động lệch cuối clip) và tạo năng lượng MV. Liên hệ pipeline: đo "phần dùng được" của mỗi clip AI thay vì dùng trọn thời lượng gen. Độ tin: chắc về số.
2. **Không bám phách** (33% so với ngẫu nhiên 36%) ngay cả ở MV nhịp nhanh làm bằng AI — cùng 22, 23. → **3 MV đo được không bám phách**; củng cố sửa E4.
3. **Cắt vụn cùng một take (7 × 0.3s, 65.8–68.2s)** — cùng khung hát, giật như nháy sáng. Ý đồ **[có thể]**: tạo nhấn nhịp mà không cần gen thêm clip (rẻ).
   Độ tin: chắc về hình (tờ ảnh #43–52 cùng bố cục).
4. **Chuyển thế giới bằng một vật trong khung**: biển quảng cáo sóng → nước tràn ra sân ga (#16–24); pha lê nổ → khung trắng → đời thường (#72–78). Cùng họ
   "chuyển cảnh che máy thiết kế trong chuyển động" (`knowledge/craft/chuyen_canh.md`). Với video AI: vẽ khung đầu / cuối cho clip chuyển (S4.6 hiệu ứng kỹ năng).
5. **Giọng hát vào muộn (~36s) sau đoạn âm thanh môi trường** (tàu, sóng) — cùng "đoạn thiết lập rồi mới vào bài" (18, 23, 09, 20, 22) → 6 video.
6. **Khép vòng**: kết quay về sân ga + tiếng tàu (148–164s) như mở đầu.

## Giới hạn / câu hỏi mở
- 19% shot quá ngắn cho OpenCV. Mốc # → giây sau shot 91 chỉ gần đúng (tờ ảnh 2 chưa đối chiếu từng shot).
- Khớp môi (tag #klingavatar): **chưa đo** bằng mốc môi (`core/clip_measure.lip_sync`) — việc tiếp theo đáng làm vì là mẫu AI có hát.
- `beat_align` librosa có thể lệch pha — cần nghe tai.

## Xoá dữ liệu
Media ở scratchpad phiên nice-bhabha (`s012/`: `v24_seg1.webm`, `v24_seg1f.mkv`, `v24_full.mp4`) — `bash clean.sh v24` + xoá `v24_full.mp4`, `v24_seg1f.mkv`.
Số đo ở `research/craft/s0_12/so_do/` (`v24_seg1_result.json`, `v24_seg1f_L0_numbers.json`, `v24_seg1f_L90_numbers.json`, `v24_beat.jsonl`).
