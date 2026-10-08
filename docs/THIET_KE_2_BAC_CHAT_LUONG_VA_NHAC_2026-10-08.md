# Thiết kế: 2 bậc chất lượng (#9), chọn bậc theo độ phức tạp (#11), nhạc nền theo đoạn (#13) — 08/10/2026

Nguồn: TODO.md mục "VIỆC ĐỂ SAU DỰ ÁN KHỦNG LONG ĐỎ" điểm 9, 11, 13. Phiên con Plan đã đọc code ở máy chính và đo chỉ đọc trên `data/manifest.sqlite`. **Chưa code. Chờ người dùng chốt mục 5.**

## 0. Hiện trạng

**"Thử rẻ" = `projects.test_quality`.** Cột này đang được đọc ở:
- `model_router.py:141-155`: Seedance → Fast.
- `runner.py:648-650`.
- `image_models.py:77-84`.
- `end_frames.py:178`.
- `pipeline.py:67-78`: dự án mới tự bật.
- `compare.py:81`.
- UI: `header.py:442-453`, `step1_run.py:192`.

**Bản mẫu Seedance 2.5**
- `clipai.submit(draft=True)` gửi 480p.
- `submit_final_from_sample` gửi `draft_task` và gán cứng 1080p (`clipai.py:596-605`).
- `quality_samples.py:118-193` đã có khóa chi, ghi sổ, kiểm hạn bản mẫu.
- **Bản cuối 1080p chưa chạy thật lần nào**: giá ≈ 2,08 USD / 4 s mới là ước tính.

**Gen lại không tái lập được nội dung**
- Mọi clip gửi với `seed: -1` (ngẫu nhiên). Vì vậy gen lại 720p "cùng đầu vào" vẫn ra clip khác bản nháp.
- Chỉ `draft_task` giữ đúng nội dung bản nháp.

**Ảnh GPT Image 2.5** giá phẳng, cỡ nhỏ không rẻ hơn.

## 1. Mục 9 — bỏ "Thử rẻ", quy trình 2 bậc

**Dữ liệu** (thêm vào `V2_COLUMNS`)
- `jobs.quality_tier`: draft / final / direct.
- `jobs.draft_job_id`.
- `motion_prompts.quality_path`: auto / draft_first / direct, người dùng ghi đè được.
- `motion_prompts.complexity`: JSON.
- Trạng thái từng cảnh **tự suy**, không lưu cứng. `core/quality_tier.py: state()` trả một trong: none, draft_running, draft_review, draft_ok, draft_stale, final_running, final_ok, direct_ok.
- `draft_stale`: `input_hash` hiện tại khác `input_hash` của bản nháp đã duyệt. Khi đó chặn gen bản cao, dùng lại cơ chế `stale_input` của KLD-1.

**Luồng**
1. Gửi nháp: Seedance 2.5 `draft=True` 480p. Model khác thì dùng tier thấp nhất của model đó.
2. Người duyệt nháp.
3. Bấm "Gen bản cao" → tạo job `final` có `draft_job_id`:
   - Nháp Seedance 2.5 còn hạn → `submit_final_from_sample`, giữ đúng nội dung nháp.
   - Nháp hết hạn hoặc model khác → gửi lại đúng đầu vào ở tier cao. Thẻ cảnh ghi "nội dung có thể khác bản nháp".
4. Bản dựng có cảnh còn nháp → hiện chữ "NHÁP 480p". Khi giao thì cảnh báo, không chặn.

**UI**
- Thẻ cảnh có huy hiệu trạng thái, nút duyệt nháp, nút "Gen bản cao".
- Nút gom "Gen bản cao N cảnh — ước tính X USD (tham khảo)", có hộp xác nhận.

**Tiền**
- Mọi lượt gửi đi qua đường runner hiện có (SPEND_LOCK, spend_gate, record_usage).
- Trần tự gen lại tính theo từng chuỗi. Bấm "Gen bản cao" là việc người dùng làm, không tính vào trần.

**Khác biệt 480p với 720p/1080p**
- Seedance dùng ảnh làm tham chiếu, không khóa khung đầu, nên gen lại ở tier cao là một clip mới.
- Đề xuất đo trên 2–3 shot, và thử seed cố định (≈ 1,3 USD/shot 4 s).

## 2. Mục 11 — chọn bậc theo độ phức tạp

**`core/shot_complexity.py`** (0 USD, không gọi AI) chấm các yếu tố lấy từ trường có sẵn:
- số người;
- kỹ năng / hiệu ứng / video ref;
- chuyển động lớn / nhảy;
- tay;
- máy di chuyển;
- khớp môi / thoại;
- nền 3D.

**Ngưỡng theo tiền**
- Ký hiệu: L = giá nháp, H = giá bản cao, r = số lần gen lại kỳ vọng, q = xác suất bản cao vẫn hỏng.
- 2 bậc rẻ hơn gen cao luôn khi **r > (L + qH)/(H − L)**.
- Seedance 2.5, 4 s, q = 0: bản cao 720p → r > 0,8; bản cuối 1080p → r > 0,25.

**Đo sơ bộ r̂** (số lần gen lại trung bình mỗi shot, chưa tách nguồn gen lại)

| Dự án | Nhóm | Shot | Gen lại | r̂ |
|---|---|---|---|---|
| #8 | tất cả | 33 | 27 | 0,82 |
| #8 | thoại / khớp môi | 23 | 23 | 1,0 |
| #8 | không thoại | 10 | 4 | 0,4 |
| #8 | complex | 3 | 4 | 1,33 |
| #22 | nhảy / kỹ năng | 9 | 27 | 3,0 |

- Kết luận tạm: shot khớp môi, nhảy/kỹ năng, ≥ 2 người → nháp trước; shot tĩnh 1 người, không thoại → gen cao luôn.
- Công cụ `tools/measure_redo_by_factor.py` (chỉ đọc) tính lại r̂ sau mỗi dự án.

**UI thẻ cảnh**, ví dụ: "Độ phức tạp 5/8: khớp môi · 2 người · máy di chuyển → Nháp trước", kèm giá cả hai đường và ô chọn Tự động / Nháp trước / Cao luôn.

## 3. Mục 13 — nhạc nền mặc định theo đoạn

**`core/music_cues.py`: `plan()` chia "cue nhạc"**
- Lấy đoạn từ `music_timing.sections`.
- Gộp các đoạn liền nhau cùng giọng điệu; mỗi cue ≥ 8 s, tối đa 1 cue/20 s.
- Đổi cue tại điểm cắt cảnh, canh downbeat, crossfade 1,5–2 s.
- Điểm vào bài lấy tự động, không cần đặt giây tay.

**Nguồn nhạc**
- Ưu tiên Kho âm thanh (0 USD); thiếu thì dùng nhạc AI.
- Phim một giọng điệu: dùng 1 bản AI có điểm đổi đoạn.

**Dựng**
- `second_music` tổng quát thành N cue.
- Lưu `cues.json`; hash bản giao tính cả cues.
- Dự án đã chọn nhạc giữ nguyên.

**UI:** bước 5 có dải cue trên timeline, mỗi cue có nguồn, giây, nút đổi, giá nếu là AI.

**Ducking:** hiện chưa có số đo nào chứng minh hạ 8–12 dB → phải đo và chỉnh `DUCK`.

## 4. Test
- **#9:** `state()` đủ 8 trạng thái; chặn bản cao khi `draft_stale` hoặc nháp chưa duyệt; nhánh `draft_task` còn hạn / hết hạn; ghi sổ đúng tier; grep không còn chỗ đọc `test_quality`; sửa test cũ.
- **#11:** bảng yếu tố; công thức ngưỡng; ghi đè của người dùng thắng chế độ tự động.
- **#13:** chia cue; crossfade; đo ducking bằng tín hiệu tổng hợp; dự án cũ dựng y hệt.
- **Thử thật (tốn tiền, cần duyệt):** bản cuối `draft_task` 1080p ≈ 2,1 USD; seed cố định ≈ 1,3 USD; 1 phim 3 cue nhạc AI.

## 5. Quyết định cần người dùng chọn (★ = khuyến nghị)
1. **Bản cao Seedance 2.5:** ★ `draft_task` 1080p, giữ đúng nháp (sau 1 lần chạy thật ≈ 2,1 USD) · hay gen lại 720p (rẻ hơn, clip có thể khác nháp).
2. **Ảnh có 2 bậc không?** ★ Không, chỉ video.
3. **Trần tự gen lại:** ★ chuỗi nháp ≤ 2 và chuỗi bản cao ≤ 2, tính riêng · hay gộp chung ≤ 2 cho cả cảnh.
4. **Dự án đang bật "Thử rẻ":** ★ chuyển thành `draft_first` cho cảnh chưa có clip; clip cũ giữ nguyên, không đánh dấu "đã cũ".
5. **Dựng/giao khi còn cảnh nháp:** ★ dựng xem trước có chữ NHÁP; giao thì cảnh báo, không chặn.
6. **Độ phức tạp:** ★ chỉ dùng trường dữ liệu có sẵn (0 USD); vision để sau.
7. **Ngưỡng:** ★ công thức r̂, đo lại sau mỗi dự án · hay đặt tay theo số điểm.
8. **Nhạc AI theo cue:** ★ 1 bản nháp/cue, ưu tiên Kho · hay 2 bản nháp/cue (gấp đôi tiền).
9. **Phim một giọng điệu:** ★ 1 bản AI có điểm đổi đoạn; chỉ tách nhiều bài khi đổi giọng điệu thật hoặc có bài riêng (vd. nhảy).

## 6. Chia nhánh

| Nhánh | Nội dung | Phụ thuộc | Khối lượng |
|---|---|---|---|
| N1 | db + `quality_tier` + runner/clipai/model_router + gỡ `test_quality` | — | ~2 ngày |
| N2 | `shot_complexity` + tools/measure | không chặn | ~1 ngày |
| N3 | `music_cues` + delivery + autopilot + đo/chỉnh DUCK | độc lập | ~2 ngày |
| N4 | UI step4 | sau N1, N2 | ~1 ngày |
| N5 | UI step5 dải cue | sau N3 | ~0,5 ngày |

- Chống xung đột: N1 sở hữu `db.py`.
- Cờ mới `two_tier_quality` và `music_cues` TẮT cho tới khi chạy thật đạt.
