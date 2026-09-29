# Báo cáo sáng 29/09/2026 — chạy tiếp kế hoạch sau #8 qua đêm

> Theo lệnh của bạn: làm tiếp các việc cũ theo `docs/KE_HOACH_SUA_SAU_DU_AN_8.md` (phần không tốn tiền). Việc mới cần bạn quyết và việc tốn
> tiền không dừng hỏi giữa đêm mà ghi ở mục 4–5. **0 USD đã chi** (chỉ agent Claude Code + công cụ chạy trên máy). 1367 test qua.
> Mọi thay đổi đã lên `main` và đã kéo về `D:\AI-Video-Pipeline`.

## 1. Tiến độ
| | Tối 28/09 | Sáng 29/09 |
|---|---|---|
| Tổng (86 việc) | 37,4 % | **55,1 %** (44 xong · 4 đang làm · 8 chờ bạn) |
| S0 học phim tham khảo | 63,6 % | 79,6 % |
| S2 timeline theo âm thanh | 0 % | **81,8 %** (còn S2.6 chờ bạn) |
| S3 Director + Quay phim | 0 % | **80 %** (còn S3.7, S3.8) |
| S4 video chất lượng | 0 % | 10 % (S4.8, S4.9 xong; phần còn lại tốn tiền / chờ bạn) |
| S5, S6, S7, K, S8 | 0 % | 0 % — chưa tới lượt |

## 2. Đã làm (có bằng chứng)
**Học nghề (S0.10–S0.15)**
- Phương pháp phân tích 4 tầng (quan sát → ý đồ trong ngữ cảnh → kỹ thuật → gợi ý), sửa 16 chỗ gán nghĩa cố định trong kiến thức đang dùng.
- 50 nguồn chuyên gia (Murch, Randy Thom, Deakins, DGA, composer…) + 18 nguồn tiếng Trung (tài liệu chính thức Seedance 2.5 đọc trọn, 第一财经,
  澎湃…), nhạc phim theo thể loại, kiểm chứng thuật ngữ chuyển động máy bạn gửi (Tracking ≠ Truck, Zoom ≠ Dolly, Arc ≠ Orbit).
- **10 video mẫu đã phân tích bằng số** (`research/craft/s0_12/`, tải đoạn → đo → xóa): 4 AI short drama 9:16 (gồm DramaBox), phim ngắn CGI,
  hành động, MV, CGI game, phim AI võ hiệp. Phát hiện chính: AI drama thoại cắt đều ~30 shot/phút; **nhạc có hai kiểu** (nền liên tục 84–100 %
  hoặc thưa làm cú nhấn); **tắt nhạc 4–8 s ở nhịp then chốt rồi vào lại đúng điểm cắt**; âm nhấn / tim đập trùng điểm cắt; im lặng hoàn toàn
  ở chỗ nhảy thời gian.
- Công cụ **"nghe bằng số"** `tools/audio_listen.py` (demucs + AudioSet + faster-whisper, cài với sự đồng ý của bạn): kiểm trên #8 v4 — chép
  đúng lời tiếng Việt, bắt đúng 2 khoảng nhạc cố ý tắt.

**Prompt Seedance (S4.8, S4.9)** — theo tài liệu chính thức: 2.0/Fast chỉ số shot (gốc lỗi trôi hành động #8), 2.5 mốc giây nguyên; từ cảm
xúc quá mạnh được làm dịu + chặn mắt phát sáng; ⚠ shot dồn ≥ 3 hành động; ảnh tham chiếu ≤ 1280 px.

**Timeline theo âm thanh (S2.1–S2.5)**
- Giọng làm ngay sau Director, kéo độ dài shot theo giọng thật, cổng ±10 % mục tiêu, **khóa timeline trước khi làm ảnh** (cờ `audio_first`).
- **Animatic** ở Bước 2 · Storyboard (0 USD): chạy thật trên #8 → 33 shot, 63,7 s, 23 câu thoại, nhạc, phụ đề, ~40 s dựng
  (`data/projects/8/output/ANIMATIC_sub.mp4`). Đã kiểm nút trên dashboard thật.
- Clip Seedance đơn lẻ cắt ở đoạn có hành động, không dưới mức sàn (cờ `motion_trim`).

**Director + Quay phim (S3.1–S3.6)**
- `beat.cause`: cú xoay phải nói nguyên nhân và người xem thấy ở đâu (💡, không ép khuôn truyện) — gốc lỗi "Maxim trúng đạn không thấy ai bắn".
- **Người xem lần đầu** (cờ `story_check`): 1 lượt Claude chỉ đọc cái hiện trên màn hình, kể lại truyện + chỉ chỗ khó hiểu, hiện ở Bước 1.
- `action_peak`: khung đầu shot hành động vẽ tư thế đang giữa động tác (gốc lỗi "chạy giả, khựng").
- S3.5 **điều chỉnh theo nghiên cứu**: không ép "≤ 2 shot cùng cỡ" / "mỗi cảnh phải chuyển động" (phim thật máy tĩnh 98 %); chỉ nhắc khi máy
  chuyển động mà thiếu lý do.
- `transition_in` từng chỗ nối: chớp trắng / tối đi / lia nhòe / lao vào khung, vẽ trong 2 clip nên độ dài phim không đổi (cờ
  `shot_transitions`, đã kiểm bằng mắt). Sửa kèm 1 lỗi cũ: hiệu ứng hồi tưởng bị bỏ khi có khớp màu chạy trước.
- **Đoạn diễn liên tục theo góc máy** (cờ `continuous_takes`): mỗi vị trí máy quay trọn đoạn diễn, mỗi shot cắt đúng chỗ trong đoạn.

## 3. Chưa làm (theo thứ tự kế hoạch, làm tiếp khi bạn cho)
S3.7 (vi phạm móc / money shot → Director sửa — tốn lượt Claude), S3.8 (đổi bối cảnh → chạy lại Director), S5.1–S5.4 (render bộ ảnh chuẩn
từ GLB Tháp Đồng Hồ, chặn prompt thiếu câu bố cục, đo "tầng tường"), S6.1–S6.6 (ước tính trước Director, màn timeline tổng, e-mail khỏi URL,
cờ đã kiểm…), S7.0 (agent QC giữ cache), S0.12 còn 15 video + 1 DramaBox, rồi K (chạy kiểm) và S8 (chấm devsys).

## 4. Cần bạn quyết
1. **Bật cờ mới cho lần chạy kiểm K** (kịch bản hài 20–30 s): `audio_first`, `story_check`, `action_peak` (luôn bật, không cờ),
   `shot_transitions`, `motion_trim`, `camera_setups` + `continuous_takes`. Đề xuất bật cả, vì K là để đo chúng. Bạn đồng ý?
2. **8 việc đang ⏸**: S1.14 (nghe nhạc v4 #8 — bạn hẹn xem sau), S1.15 (Eleven Music v2.5), S2.6 (Seed Audio 1.0 làm track thoại),
   S4.7 (kho chủ thể thay dấu đỏ), S4.10 (A/B Seedance 2.5, ~3–4 USD), S4.11 (Sample Mode — kiểm API), S4.12 (Advanced Edit sửa clip, ~0,5
   USD), S5.6 (video white-model từ GLB).
3. **Xem animatic #8** (63,7 s — bằng độ dài kế hoạch, bản giao thật 83 s) và cho ý kiến: animatic đã đủ để duyệt nhịp trước khi trả tiền video chưa?
4. **Nghe xác nhận vài mốc nhạc** trong các file `research/craft/s0_12/0x_*.md` (mục "Nhạc") — công cụ chỉ "nghe bằng số".
5. Danh sách còn 15 video mẫu: làm tiếp hết, hay đủ 10 video (đã có đủ 5 thể loại) để chuyển sang đưa kiến thức vào `knowledge/craft/`?

## 5. Việc tốn tiền đang chờ (trần đợt 50 USD, đã dùng từ đầu đợt: 0 USD)
| Việc | Ước tính | Khi nào |
|---|---|---|
| S4.6 A/B (cận, hành động 3 model, khớp môi) | ≤ 12 USD | sau khi bạn duyệt S4 |
| S4.10 A/B Seedance 2.5 vs Fast | ~3–4 USD | nếu duyệt |
| S5.5 vẽ lại khung nền tháp | ≤ 2 USD | sau S5.1–S5.4 |
| S7.1 nghiệm thu agent QC | ≤ 1 USD | sau S7.0 |
| K chạy kiểm 20–30 s chất lượng cao (có TTS của `audio_first`) | ≤ 25 USD | cuối đợt |

## 6. Ghi chú kỹ thuật
- Đêm qua có ~1 giờ bị gián đoạn do hệ thống kiểm tra an toàn lỗi tạm thời và chạm giới hạn phiên — không mất dữ liệu.
- 3 kết nối (Adobe for creativity, bigdata.com, CodSpeed) cần bạn cấp quyền trong cài đặt connector nếu muốn dùng — dự án hiện không cần.
