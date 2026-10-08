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

**Người dùng chốt 08/10 (thay phần chia cue theo đoạn cảnh ở bản nháp trước):** nhạc nền đi theo **diễn biến cảm xúc của cả câu chuyện**, ghép theo các **bước ngoặt tình huống** (mở đầu → căng → ngoặt → cao trào → kết), KHÔNG phải mỗi clip video / mỗi đoạn gen một đoạn nhạc. Nhạc rẻ hơn video rất nhiều → **không tiết kiệm ở nhạc**: được gen nhiều bản để chọn bản hợp cảm xúc nhất.

**`core/music_cues.py`: `plan()` = "đường cảm xúc" của truyện**
- Nguồn: ý đồ Đạo diễn (Bible / beat truyện, `music_intent.read_tone`, phần kịch bản TWIST / CAO TRÀO), không phải danh sách shot.
- Mỗi "đoạn nhạc" = một chặng cảm xúc của truyện (có thể dài qua nhiều cảnh/clip); chỗ đổi chặng đặt đúng giây xảy ra bước ngoặt trên bản dựng (từ `music_timing`), canh downbeat, nối mượt (crossfade / break / nhạc lặng trước cú ngoặt khi ý đồ cần).
- Ưu tiên **một bản nhạc AI liền mạch mang cả đường cảm xúc** (brief nêu từng chặng + giây đổi); chỉ tách nhiều bài khi truyện đổi hẳn chất liệu (vd đoạn nhảy theo bài gốc).
- Điểm vào bài lấy tự động, không cần đặt giây tay.

**Nguồn nhạc**
- Mặc định nhạc AI theo brief cảm xúc (giá thấp, người dùng không quan trọng tiền ở khâu này); Kho âm thanh / bài gốc dùng khi hợp hoặc người chọn.
- Gen nhiều bản nháp (mặc định 3) cho người nghe chọn; vẫn ghi sổ chi + hiện giá trước khi bấm.

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

## 5a. NGƯỜI DÙNG ĐÃ CHỐT 08/10 (thắng mọi phương án bên dưới)
1. **Bản cao Seedance 2.5 = (a)** nâng từ bản nháp đã duyệt (`draft_task`) — chạy thật 1 lần trước khi làm mặc định (hỏi giá trước).
2. **Chỉ video có 2 bậc**, ảnh không.
3. **Trần gen lại:** chuỗi nháp tối đa **2 lần gen lại**; bản cao dựa trên nháp đã duyệt nên phải đạt ngay lần đầu → bản cao chỉ được **gen lại 1 lần**.
4. **Bỏ "Thử rẻ" → Đạo diễn nhận diện độ khó ngay khâu phân tích cảnh:**
   1. Director ghi cho mỗi shot: `dễ` / `phức tạp` / `chưa rõ` (kèm lý do) ngay khi phân tích cảnh.
   2. **Dễ → gen thẳng chất lượng cao** (không nháp, tránh lãng phí một lượt thử).
   3. **Phức tạp và chưa rõ → nháp chất lượng thấp trước**, đạt rồi mới gen bản cao. Nháp gen lại 2 lần vẫn chưa đạt → **dừng, báo người dùng**.
   4. **Kiểm lại khâu gen lại**: mỗi lần gen lại phải sửa đúng lỗi của lần trước (đổi prompt/đầu vào theo lỗi QC/người dùng ghi), không gửi lại y nguyên (CHUAN_XAY_DUNG luật 3) — có kiểm bằng code.
5. **Nháp đạt thì vẫn dựng:** bản dựng từ các clip nháp là **bản DRAFT** để người dùng xem trọn bộ và đánh giá; khi giao phải **thông báo rõ** bản nào còn là nháp.
6. **Độ phức tạp:** dùng dữ liệu có sẵn (0 USD) — đồng ý; nhãn Đạo diễn (mục 4.1) là đầu vào chính, dữ liệu shot dùng để kiểm chéo.
7. **Ngưỡng:** theo nhận diện của Đạo diễn như mục 4 (không phải công thức tiền); số lần gen lại đo thật dùng để Đạo diễn/hệ thống rút kinh nghiệm phân loại.
8. **Thanh tiến độ** phải theo đúng tiến độ làm của dự án (nháp / đã duyệt nháp / bản cao / dựng draft / dựng cuối), không báo xong khi mới có nháp.

## 5. Quyết định cần người dùng chọn (★ = khuyến nghị) — bản đề xuất ban đầu, xem 5a
1. **Bản cao Seedance 2.5:** ★ `draft_task` 1080p, giữ đúng nháp (sau 1 lần chạy thật ≈ 2,1 USD) · hay gen lại 720p (rẻ hơn, clip có thể khác nháp).
2. **Ảnh có 2 bậc không?** ★ Không, chỉ video.
3. **Trần tự gen lại:** ★ chuỗi nháp ≤ 2 và chuỗi bản cao ≤ 2, tính riêng · hay gộp chung ≤ 2 cho cả cảnh.
4. **Dự án đang bật "Thử rẻ":** ★ chuyển thành `draft_first` cho cảnh chưa có clip; clip cũ giữ nguyên, không đánh dấu "đã cũ".
5. **Dựng/giao khi còn cảnh nháp:** ★ dựng xem trước có chữ NHÁP; giao thì cảnh báo, không chặn.
6. **Độ phức tạp:** ★ chỉ dùng trường dữ liệu có sẵn (0 USD); vision để sau.
7. **Ngưỡng:** ★ công thức r̂, đo lại sau mỗi dự án · hay đặt tay theo số điểm.
8. ✅ **Người dùng chốt 08/10:** nhạc theo đường cảm xúc của cả truyện, ghép theo bước ngoặt tình huống (không theo từng clip); không tiết kiệm ở nhạc — mặc định 3 bản nháp để chọn.
9. ✅ (gộp vào 8) ưu tiên một bản AI liền mạch mang cả đường cảm xúc; tách bài chỉ khi đổi hẳn chất liệu.

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
