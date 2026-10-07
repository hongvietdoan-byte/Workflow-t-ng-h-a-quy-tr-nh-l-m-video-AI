# Bàn giao Khủng Long Đỏ #22 — phiên Claude 07/10/2026 (tài khoản $, gần hết hạn mức)

Người dùng sẽ xử lý các luồng thông tin ở tài khoản khác. Tài liệu này ghi **mọi thứ** đã làm, dữ liệu đã đổi, tiền đã tiêu, lỗi của phiên và việc còn mở. Đọc cùng `TODO.md` (khối "VIỆC ĐỂ SAU DỰ ÁN KHỦNG LONG ĐỎ") và memory `.claude-memory/projects/ai-video-pipeline.md`.

## 1. Kết quả
- **Video cuối** dựng từ 9 clip đã duyệt: `data/projects/22/output/FINAL_VIDEO.mp4` (1080×1920, ≈ 52,6 s). Bản sao lưu ngoài git: `D:\AI-Video-Output\2026-10-07_du-an-22\` (xem mục 7).
- 9 cảnh, clip dùng (job → file):

| Cảnh | scene | Job | Model | Ghi chú |
|---|---|---|---|---|
| 1 | 248 | 537 | seedance-fast | bản người dùng đã duyệt từ 06:33Z, KHÔI PHỤC từ thùng rác |
| 2 | 249 | 538 | seedance-fast | như trên |
| 3 | 250 | 539 | seedance-2.5 | |
| 4 | 251 | 540 | seedance-fast | khôi phục từ thùng rác |
| 5 | 252 | 541 | seedance-2.5 | |
| 6 | 253 | 549 | seedance-fast | khôi phục từ thùng rác, duyệt 07/10 (người dùng bảo "chốt") |
| 7 | 254 | 568 | seedance-2.5 (override) | nhảy 1, 720p, QC chưa chặn, cảnh báo clip_measure còn |
| 8 | 255 | 569 (mang nội dung job 560) | seedance-2.5 | QC 0,81 < 0,82 nhưng người dùng chọn giữ; xem mục 4 (hoán đổi dòng job) |
| 9 | 256 | 561 | seedance-2.5 | QC 0,82; khung cuối máy lùi nhiều, hai người nhỏ |

## 2. Tiền (ước tính, đã chi trong phiên)
- Phép so độ nét shot 6 (scene 253): A 720p 0,92 + B mẫu 480p 0,41 = 1,34 USD. B final 1080p 2,08 **chưa gửi**.
- Shot 7 thử rẻ (job 548) 1,44; ảnh khung đầu 3 lượt ≈ 0,53 (3×3 ảnh + ảnh toàn cảnh 1 lần).
- Video nhảy: 566 + 567 (Seedance **2.0** gửi nhầm, ≈ 3,6) + 568 (2.5, ≈ 2,76–3,18) + 560 + 569 (2.5 ×2, ≈ 5,5–6,4) + 561 (2.5, ≈ 2,76–3,18); hai clip lỡ gửi 562/563 (Seedance 2.0, ≈ 1,2).
- Ngân sách đợt thử: **55,82 / 74,50 USD** đã chi (còn 18,68) lúc ghi tài liệu. Tài khoản Claude chế độ $: **90 %** (362,63 / 400) trước khi viết file này.
- Giá thật ClipAI (người dùng chụp): **Seedance 2.0 · 12 s · 1080p · 9:16 = 2,93 USD**; công thức `cost.seedance_estimate` của repo cao hơn thật ≈ 33 % ở 2.0@1080p; 2.5 chưa kiểm với giá web.

## 3. Mã đã commit (main)
- `15fa692`: kind `high` ("C · 1080p gen thẳng", 2,08 USD) trong `core/quality_samples.py` + `core/adapters/clipai.py` (`high_res_sample`) + nút UI; chưa gửi thật lần nào; API có nhận 1080p non-draft cho 2.5 hay không là **chưa kiểm**.
- `5907f07`: `.claude-memory` bài học đổi chỗ đứng cảnh.
- `876b0e7`, `b1d432e`, `a0562d4`: TODO khối "việc để sau dự án" (9 mục).
- Commit cuối: tài liệu này + TODO.

## 4. Dữ liệu thật ĐÃ ĐỔI (máy chính `D:\AI-Video-Pipeline`, ngoài git; có sao lưu ở `data/backup/`)
- `assets` #263 (Tháp Đồng Hồ) `profile.model3d.spots`: thêm **`bac_thang_giua`** at (-253,7; 144,1; 3,925), facing 298°, nhóm `nhay` — chân cầu thang nhiều tầng giữa nhà 3 tầng và tháp (người dùng chọn vòng xanh).
- `scenes` 254–256: `plate_spot=bac_thang_giua`, `plate_view.background=124`, `lens_mm=18`, `location` = "Chân cầu thang nhiều tầng giữa nhà 3 tầng và Tháp Đồng Hồ"; sửa `image_prompt`, `blocking`, `spatial_state`, `action` (bỏ "sân đá phẳng / nhà mái đỏ thấp / nhà lớn phía Đông", thêm khóa nền).
- `motion_prompts` 254–256: prompt viết lại (bỏ push-in và vòng cung, thêm BACKGROUND + START LOCK, Maxim mũ đen sừng đỏ nhỏ), `video_model='seedance-2.5'` (override), đã `stamp_motion` + duyệt lại.
- `plates/index.json` 254–256 → nền 3D mới key `7728a0752476f84aae96` (đã dựng bằng Blender); `establish/index.json` cảnh 2: ảnh toàn cảnh = render 3D đồng trục W2 (lùi 30 m, hướng 118°), `scene_2.png` cũ (vẽ từ ngoài tường) lưu `scene_2_ve_tu_ngoai_tuong_bo.png`.
- `feature_settings.json`: `seedance_sample_mode` **BẬT** (để dùng hộp "So độ nét"; tắt nếu không cần). "Thử rẻ" của dự án đã **bật lại** như ban đầu.
- **Hoán đổi dòng job 560 ↔ 569** (cảnh 255): 569 (approved) mang task `cgt-20261007204256-31w54` + file `videos/08.mp4` = bản người dùng chọn; 560 (rejected) mang task `…lfuq4` + file `clips_khac/08_seedance25_job569.mp4`. Lý do: chuỗi nối cảnh (`start_from_prev_clip`) và `collect_clips` lấy **lần gen mới nhất theo số job**, nên bản được chọn phải nằm ở dòng có số lớn nhất. Ghi trong `job_events` (actor `claude`).
- Job 562, 563 (Seedance 2.0 lỡ gửi): đã hủy (state cancelled), tệp ở `data/projects/22/clips_khac/`. Job 564, 565: hủy trước khi gửi.
- Clip 537, 538, 540, 549 khôi phục từ `data/projects/22/trash/videos/NN__20261007-185642.mp4` về `videos/NN.mp4`, đặt lại state approved (549 → duyệt bằng `p.approve`), ghi `job_events` actor `claude`.
- Backup CSDL theo thời điểm: `manifest.before_kld_*` (ab, stairs, prompt_lock, lens18, motion, startlock, restore, keep560, swap560, cancel562, quality, place, round3) + `videos_before_restore_20261007_194423/` + `clip_255_job560_*.mp4` + `establish_index.before_*`.

## 5. LỖI của phiên Claude (đã khắc phục, cần biết)
1. Tắt "Thử rẻ" rồi bấm **"▶ Gen video" chung**: hệ thống tự loại 4 clip đã duyệt (scene 248, 249, 251, 253) và gửi nhầm 248, 249 bằng Seedance 2.0 (≈ 1,2 USD). Khôi phục như mục 4. **Đừng đổi cài đặt cả dự án rồi bấm nút gen chung.** Cách an toàn mình dùng: tạm đặt `motion_prompts.state='pending'` của các cảnh ngoài ý muốn → nút chỉ gửi job đang chờ → trả `approved`.
2. Alias `seedance` = **Seedance 2.0**; `seedance-2.5` mới là 2.5. Mình báo nhầm hai lần là 2.5 (≈ 3,6 USD gen sai model). Đã đặt override `seedance-2.5` cho 254–256.
3. Lượt vẽ lại ảnh đầu **dùng nền 3D cũ** vì đường vẽ thủ công không dựng lại nền khi đổi chỗ đứng (chỉ autopilot so khóa). Đã chạy `location_pack.ensure_plates` tay.
4. Đặt tệp sao dự phòng trong `data/projects/22/videos/` làm dựng video cuối **lặp cảnh nhảy**; đã chuyển sang `clips_khac/`. **Đừng để tệp phụ trong thư mục `videos/`.**
5. Gửi gen nhầm do mình coi bản nháp 480p là bước bắt buộc (0,41 USD); ước giá sai ban đầu cho shot 7–9.

## 6. Việc còn mở (xem TODO.md để đủ chi tiết)
- **Để sau dự án (người dùng yêu cầu):** phân luồng/tách biệt gen từng dự án; sửa nút gen chung (chỉ gửi cảnh chọn + hộp liệt kê giá); hiển thị tên model thật; so khóa nền 3D ở mọi đường gen; ảnh toàn cảnh cùng hướng camera; **bỏ nút "Thử rẻ", thay bằng nháp 480p tự chọn rồi gen lại chất lượng cao khi đạt**; cân nhắc **Seedance 2.0 @1080p** (2,93 USD/12 s theo ClipAI web, người dùng nhận xét chất lượng khá); hiệu chỉnh bảng giá; UI "chờ duyệt cảnh trước".
- **Khâu dựng cắt phần mở đầu clip** (người dùng đề xuất 07/10): hiện Editor chỉ có `shorten_shot` (giữ những giây đầu), `extend_hold`, `music_cue`; **chưa có loại sửa bỏ N giây đầu**. Thêm `trim_start` vào luồng Editor (đề xuất → người dùng tích → code kiểm → dựng lại → QC trước/sau). Chỗ cần xử lý trong phim này: nối 254→255 (khung cuối 254 tay giơ cao, đầu 255 tay trước ngực, khung hơi xa) và chỗ nhảy giây 1,5 / 7,0 của 255 (đến từ video nhảy tham chiếu, không phải lỗi gen).
- Clip 254: `clip_measure` còn cảnh báo "mặt mịn hơn ảnh khung đầu ×0,24"; khung cuối clip 256 có nhiều sân trống (prompt "lùi ra"). Có thể dựng lại hoặc cắt.
- B final 1080p 2,08 USD của phép so độ nét: chưa gửi, chờ người dùng.
- Bản Seedance 2.0 (clips_khac/01_…, 02_…) để so; người dùng chưa chọn dùng.
- Mô tả `docs/KE_HOACH_SUA_SAU_DU_AN_8.md` S4.11: trạng thái 🔄 → đã có A/B mẫu thật (A 720p + B mẫu 480p), A+ bỏ (phóng AI ≈ 1 giờ/clip, không hợp dây chuyền); chưa có B final.

## 7. Tệp xem nhanh (ngoài git, `D:\AI-Video-Output\2026-10-07_du-an-22\kiem_thu_phong_AI\`)
`A_4khung.png`, `anh_khung_dau_lan3_254_256.png`, `clip_254_seedance25.mp4`, `clip_255_seedance25.mp4`, `clip_255_job569.mp4`, `clip_256_seedance25.mp4` (+ `*_khung.png`, `noi_*.png`), `goc_thap*/` (các góc render thử), `final_luoi_3s.png`.
