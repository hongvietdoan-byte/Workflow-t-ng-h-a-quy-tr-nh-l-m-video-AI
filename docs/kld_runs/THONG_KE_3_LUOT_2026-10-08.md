# Thống kê 3 lượt dự án #22 (chỉ đọc, CSDL `m.sqlite`)

> Lưu ý: cột trạng thái job (mục 2) là trạng thái **hiện tại** — ảnh/clip đã duyệt và dùng ở bản thử 1 về sau bị đánh "loại" khi lượt sau đổi đầu vào (xem `docs/TONG_HOP_3_LUOT_KHUNG_LONG_DO.md` mục 1).

## 1. Tiền theo lượt và model (USD, giá bảng; phần ước tính dư ghi riêng)

| Lượt | Loại | Model | Số lượng (ảnh / giây / lần gọi) | USD |
|---|---|---|---|---|
| Lượt 1 (thử) | video | dreamina-seedance-2-0-fast-260128:720p | 116 | 13.92 |
| Lượt 1 (thử) | video | dreamina-seedance-2-5-260628:720p | 8 | 1.84 |
| Lượt 1 (thử) | llm | claude-sonnet-5 | 43 | 1.74 |
| Lượt 1 (thử) | image | dola-seedream-5-0-pro-260628 | 30 | 1.56 |
| Lượt 1 (thử) | audio | eleven_v3 | 2 | 0.00 |
| **Lượt 1 (thử)** | | **cộng** | | **19.06** (trong đó ước tính 0.00) |
| Lượt 2 (thử) | video | dreamina-seedance-2-0-fast-260128:720p | 76 | 9.12 |
| Lượt 2 (thử) | video | dreamina-seedance-2-5-260628:720p | 8 | 1.84 |
| Lượt 2 (thử) | image | gpt-image-2.5-sunburst | 12 | 0.62 |
| Lượt 2 (thử) | llm | claude-sonnet-5 | 22 | 0.41 |
| Lượt 2 (thử) | audio | eleven_v3 | 2 | 0.00 |
| Lượt 2 (thử) | audio | music_v2 | 3 | 0.00 |
| **Lượt 2 (thử)** | | **cộng** | | **11.99** (trong đó ước tính 0.00) |
| Lượt 3 (chất lượng cao) | video | dreamina-seedance-2-5-260628:720p | 52 | 11.96 |
| Lượt 3 (chất lượng cao) | video | dreamina-seedance-2-0-260128:720p | 32 | 4.80 |
| Lượt 3 (chất lượng cao) | video | dreamina-seedance-2-0-fast-260128:720p | 16 | 1.92 |
| Lượt 3 (chất lượng cao) | image | gpt-image-2.5-sunburst | 10 | 0.52 |
| Lượt 3 (chất lượng cao) | llm | claude-sonnet-5 | 20 | 0.46 |
| Lượt 3 (chất lượng cao) | video | dreamina-seedance-2-5-260628:480p | 4 | 0.41 |
| **Lượt 3 (chất lượng cao)** | | **cộng** | | **20.07** (trong đó ước tính 0.00) |

## 2. Số lượt gen theo trạng thái (job tạo trong khoảng của lượt)

| Lượt | Loại | approved | cancelled | rejected | Tổng |
|---|---|---|---|---|---|
| Lượt 1 (thử) | image_gen | 0 | 10 | 18 | 28 |
| Lượt 1 (thử) | video_gen | 0 | 6 | 15 | 21 |
| Lượt 2 (thử) | image_gen | 6 | 1 | 5 | 12 |
| Lượt 2 (thử) | video_gen | 5 | 0 | 6 | 11 |
| Lượt 3 (chất lượng cao) | image_gen | 3 | 0 | 6 | 9 |
| Lượt 3 (chất lượng cao) | video_gen | 4 | 5 | 4 | 13 |

## 3. Lý do loại / gen lại (job không duyệt, có `retry_reason`)

| Loại | Lý do | Lượt 1 (thử) | Lượt 2 (thử) | Lượt 3 (chất lượng cao) |
|---|---|---|---|---|
| video_gen | gửi lại nguyên đầu vào (gửi lại clip lỗi (lỗi nhà cung cấp)) | 6 | 0 | 1 |
| image_gen | Frame as a medium close-up: head and chest. | 4 | 1 | 0 |
| image_gen | Frame as a medium shot: from the waist up. | 3 | 0 | 0 |
| image_gen | gửi lại nguyên đầu vào (gửi lại ảnh lỗi (lỗi nhà cung cấp)) | 3 | 0 | 0 |
| image_gen | MAXIM KL wears the red cap with two small white horns from t | 3 | 0 | 0 |
| video_gen | Check face render style across clip at frame 5 (8.9s) and fr | 2 | 0 | 0 |
| image_gen | Indoors only: the bed stands inside the 2nd-floor bedroom of | 1 | 0 | 0 |
| image_gen | KELLY KL must be in frame, medium shot from the waist up in  | 1 | 0 | 0 |
| image_gen | Exactly the same frame as the previous shot S01-3 picture: s | 1 | 0 | 0 |
| image_gen | Exactly the same frame as the previous shot S01-5 picture: s | 1 | 0 | 0 |
| image_gen | Same frame as the previous shot S01-3: same camera, medium c | 1 | 0 | 0 |
| image_gen | Same frame as the previous shot S01-5: same camera, medium c | 1 | 0 | 0 |
| video_gen | Smooth the facial render in frames 2-6 (≈2.6s-11.0s) to matc | 1 | 0 | 0 |
| video_gen | Check render style consistency for both characters' faces ar | 1 | 0 | 0 |
| video_gen | From the first to the last frame both dancers wear exactly t | 1 | 0 | 0 |
| video_gen | Fix look drift: Kelly's face shifts from a textured realisti | 1 | 0 | 0 |
| video_gen | Fix Kelly's hair to solid dark bob color at frame 2 (2.6s),  | 0 | 1 | 0 |
| video_gen | Fix Kelly's hair in frames 2 (2.6s), 3 (4.7s), 4 (6.8s) and  | 0 | 1 | 0 |

## 4. Cảnh báo `diag_events` theo loại (tổng số lần)

| Khâu | Mã | Mức | Lượt 1 (thử) | Lượt 2 (thử) | Lượt 3 (chất lượng cao) |
|---|---|---|---|---|---|
| image | look_words_removed | info | 30 | 8 | 9 |
| image | place_match | info | 20 | 10 | 7 |
| video | subjects | info | 15 | 11 | 10 |
| video | clip_measure | warn | 11 | 7 | 7 |
| image | place_match | warn | 5 | 2 | 2 |
| image | redraw | error | 7 | 1 | 0 |
| video | task_failed | error | 6 | 0 | 0 |
| video | look_words_removed | info | 6 | 0 | 0 |
| image | establishing | info | 2 | 0 | 1 |
| image | task_failed | error | 3 | 0 | 0 |
| director | auto_attach | info | 2 | 0 | 0 |
| director | director_refs | info | 2 | 0 | 0 |
| director | bad_json_retry | warn | 2 | 0 | 0 |
| director | auto_voice_cast | info | 2 | 0 | 0 |
| video | lipsync_not_applied | warn | 2 | 0 | 0 |
| director | dp_calls | info | 1 | 0 | 0 |
| director | director_review | info | 1 | 0 | 0 |
| video | auto_regen_limit | warn | 1 | 0 | 0 |
| video | download | warn | 1 | 0 | 0 |
| video | stale_input | warn | 0 | 0 | 1 |
| video | bad_json_retry | warn | 0 | 0 | 1 |

## 5. Điểm QC trung bình theo tiêu chí (số mẫu trong ngoặc)

| Loại | Tiêu chí | Lượt 1 (thử) | Lượt 2 (thử) | Lượt 3 (chất lượng cao) |
|---|---|---|---|---|
| image_gen | scene_qc_hold | 0.00 (21) | 0.00 (10) | 0.00 (9) |
| video_gen | artifacts | 0.79 (15) | 0.86 (11) | 0.83 (10) |
| video_gen | identity | 0.72 (15) | 0.87 (11) | 0.86 (10) |
| video_gen | motion_match | 0.77 (15) | 0.79 (11) | 0.80 (10) |
| video_gen | physics | 0.90 (15) | 0.92 (11) | 0.90 (10) |
