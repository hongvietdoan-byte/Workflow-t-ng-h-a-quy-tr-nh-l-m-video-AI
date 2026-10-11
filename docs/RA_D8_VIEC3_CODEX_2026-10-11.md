# Bàn giao Đ8 việc 3 — báo giá video

- Nhánh `codex/d8-viec3-bao-gia-video`, base `5cd515b`; root đọc diff phần sửa, commit/push sau nhóm xanh.
- File sửa: `core/cost.py`, `core/model_router.py`, `core/quality_tier.py`; test mới `tests/test_video_quote_current.py`, cập nhật fixture `tests/test_seedance_refs.py`.
- Shared predicate `cost.video_need`: clip hoàn thành phải có source_job_id trùng ảnh approved hiện tại và input_hash khớp motion hiện tại; motion image_job_id/spec_hash cũ → cần gen; queued/running không được coi hoàn thành. Thiếu stamp → cần gen + lý do. Không dựng provider prompt, không gọi API. Runner `_stamp` ghi hash trên motion trước khi bọc prompt nên dùng lineage hash trực tiếp đúng hợp đồng hiện hữu.
- Shared `video_reference_seconds`: đọc motion ref hoặc skill refs; probe ffmpeg cục bộ 0 USD; đường tương đối theo root code, không CWD; không biết thời lượng → None + warnings/unknown, không coi 0 giây.
- Ref Seedance dùng `seedance_estimate`: cả output và input video giây, chọn mức video_in; model_router, clip_estimate và 2 đường quality_tier cùng dùng helper.
- Dữ liệu giả 9 shot, 1 clip trùng motion/ảnh, 8 clip old-motion, refs ở shot 5/6/8 mỗi 3,5 giây: predicate cũ 0 clip/0 USD (mọi clip approved); sau sửa 8 clip/5,51 USD, 8 lý do cần gen. Đây là fixture nhỏ 4 giây/shot, không giả nhận đạt đúng 27 USD của dữ liệu #24.
- RED: 3 hỏng test mới, trong đó 9 shot đếm 0 thay 8.
- GREEN lượt 2: 85 qua (test mới + cost_route_e1 + quality_tier + trial_fixes).
- Lượt 3: 92 qua/1 hỏng (test mới + cost + seedance_refs + cost_route_e1 + quality_tier + model_line_f4 + cheap_mode_override). Lỗi fixture Seedance chỉ ghi approved, không stamp, trái yêu cầu mới; đã cập nhật fixture bằng runner `_stamp` (không nới assert), đã chạy lại trong nhóm rà độc lập bên dưới.
- `git diff --check` qua. `related_areas` báo budget/step4, caller step1/autopilot/core_infra/plates3d/step5/diag/step2/knowledge/step3/dashboard_ui; test chậm bắt buộc khi tích hợp.
- `quality_tier.path unknown`: giữ nguyên nháp trước; có căn cứ docstring/quyết định 09/10, ưu tiên dư chi phí. Chưa có bằng chứng đủ để đổi.
- Tự rà 2b.5: không cờ mới, không dịch vụ trả tiền, không sửa runner/dashboard/env/data, không hash/probe dữ liệu sản xuất khi chạy fixture; không tăng areas version; không module mã mới cần đăng ký.
- Đã RÀ KỸ độc lập và root đọc phần sửa. Giới hạn: chỉ stamp lineage được coi bằng chứng hoàn thành; sent_package-only thiếu stamp vẫn cần gen và cảnh báo (chưa chứng minh provider wrapper đủ để bỏ gen). Đã bổ sung SHA gói gửi để bắt ảnh bị ghi đè cùng job id. Ref unknown giữ tiền fallback model dư hiện có + cảnh báo, chưa có upper-bound giây ref khi ffprobe thất bại. `_final_usd` ngoài phạm vi điểm đề bài chưa đổi.


## Rà kỹ độc lập và vòng sửa
- Bắt 2 lỗi: cùng image job bị ghi đè bytes vẫn được bỏ chi phí; video ref URL có thể gọi ffmpeg mạng dù helper ghi probe cục bộ.
- ĐỎ: 2 failed / 3 passed (test same-image overwrite + URL probe). Sửa gom: đối chiếu SHA trong sent_package với current approved result_path; thiếu gói/SHA/path hoặc không đọc được → cần gen + lý do. Ref chỉ file cục bộ tồn tại, URL/UNC không probe và báo chưa biết giây.
- Fixture clip giữ lại dùng ảnh temp thật + SHA gói gửi; test Seedance dùng stamp runner thật và SHA temp, giữ nguyên mọi assert. Test mới khai areas; version giữ nguyên.
- Giới hạn: ref là ảnh đánh số/đã chuyển đổi có path khác ảnh approved thì chưa có mapping chứng minh bytes gốc; ước tính bảo thủ cần gen + lý do, không coi thiếu bằng chứng là miễn tiền. Không thay runner để bổ sung provenance; có thể tính dư với clip nhóm/ref-only cũ.
- Rà lại phần sửa: không file #24, không gọi API, không đụng dữ liệu thật, không thay widget/cờ. No flag cần cho bugfix theo đề bài. Giá unknown vẫn cảnh báo và fallback như trước, không khẳng định trần ref khi thiếu duration.

- XANH sau sửa độc lập: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_video_quote_current.py tests/test_cost.py tests/test_seedance_refs.py tests/test_cost_route_e1.py tests/test_quality_tier.py tests/test_model_line_f4.py tests/test_cheap_mode_override.py` → **95 passed in 49.42s**. Đã chạy lại fixture Seedance stamp + SHA, không nới assertions. Không chạy toàn bộ (phiên tích hợp chạy theo đề bài).
