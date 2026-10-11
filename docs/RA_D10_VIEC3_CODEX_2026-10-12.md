# Đ10 việc 3 — báo giá video (12/10/2026)

Nhánh: `codex/d8-viec3-bao-gia-video`, nền `d11d69c`. Chưa commit/push; root chốt sau RÀ KỸ độc lập.

## Kết quả
- Follower runner thật MockVideoProvider: dùng `group_leader` + `sent_group` + cùng task + stamp source_job_id/input_hash riêng. Không tự chèn gói gửi; lệch motion vẫn cần gen.
- Task running đã gửi không bị tính lại (cả shot trong nhóm đang chạy); queued/retryable vẫn cần gen.
- Ref Seedance chưa probe được: dùng dư 15 s/ref, cảnh báo rõ; URL/UNC không probe. Kling/model không tính ref không bị None theo thời lượng ref.
- `memo.per_rerun` đệm video_need/thời lượng ref; model_router chỉ đọc ref đường Seedance. Hồi quy N+1 xanh, giữ nguyên ngưỡng <200.
- Cảnh báo clip cũ chỉ hiện khi thực sự có clip bị loại. Fixture 9 shot phân biệt stamp thiếu và motion lệch; start_from_prev_clip báo lý do thiếu bằng chứng khung nối.
- Final nhóm dùng sent_group đã gửi dù ref flag OFF; giây lấy usage/gói gửi/clip thật, không ưu tiên motion vừa sửa. Giá follower/batch cùng một nhóm; final_estimate tính leader một lần kể cả follower direct.
- Nâng 2.5 nháp 480p → 1080p 9:16: 0,5254 USD/s, nguồn #24 task_usage job670–676, 38 s/19,964 USD. 38 s báo19,9652 (làm tròn dư). Đường tỷ lệ khác công thức ×1,5, ghi chưa đo. Không cộng ref khi nâng từ task; gen mới bản cao cộng ref và dùng1080p cho2.5.
- `dashboard/model_line` cộng ref khi gen nháp/direct/gen mới, nâng từ task dùng cùng giá đo.
- `cost.record_usage` sửa giây final theo clip nháp CHỈ khi gói gửi call=submit_final_from_sample. Final gen MỚI giữ giây của lời gọi mới.

## Bằng chứng
- Lượt đỏ: 6 failed/107 passed, gồm running/follower, nhóm OFF, giá đo, ledger giây và N+1 (205 query).
- Lượt trung gian: 1 failed/112 passed (fixture mới chưa tạo draft); sửa fixture theo tier thật.
- Lượt3: 125 passed/63,47 s; 8 file: cost_route_e1, seedance_refs, cost, quality_tier, readiness_f5a, two_tier_labels_estimate, video_quote_current, model_line_f4. Không nới assert; kỳ vọng nâng cũ đổi sang bảng giá đo theo chốt người dùng.
- Sau lượt3 tự kiểm bổ sung guard ledger chỉ call nâng + test final gen mới giữ giây và lý do start_from_prev_clip: CHƯA chạy lại theo giới hạn3 lượt. Agent RÀ KỸ cần chạy lại nhóm liên quan (đặc biệt test_cost_route_e1/test_video_quote_current).
- `git diff --check` xanh trước các chỉnh sửa cuối; không gọi API trả tiền, không đọc/ghi dữ liệu thật. Chưa thử thật nhà cung cấp; Mock chỉ chứng minh luồng.

## Phạm vi liên quan và việc để sau
- related_areas: budget/step4; caller step1/autopilot/core_infra/plates3d/step5/diag/step2/knowledge/step3/dashboard_ui; cờ chung step1. Test CHẬM bắt buộc ở gộp (access/editor_apply/editor_review/rough_cut/ui_v2_acceptance).
- Mục2 project_budget CHỜ #24: không sửa.
- Runner final chỉ gọi submit_final_from_sample nên không `_finish_group`; follower02/03/09 còn480p: sau#24 phải gắn sent_group của draft vào job final hoặc lấy group draft trong `_after_download`, cắt follower từ nhóm1080p, có hồi quy runner. Không sửa runner trong nhánh này.
- Giá đo chỉ route nâng2.5 nháp480p→1080p dọc; không khẳng định route khác đã đo. `_clip_groups` ưu tiên nhóm đã gửi; agent rà cần kiểm trường hợp replan/gen lại một phần làm nhóm lịch sử cũ bị sử dụng.
- Không thêm module/test file mới; areas đã khai các file hiện hữu, không tăng version. TODO/PLAN/data thật/file#24 nguyên trạng.

## RÀ KỸ độc lập — Đ10v3 (12/10, Codex)
- Bắt 2 lỗi TIỀN cùng nguồn: `sent_group` lịch sử hút nháp lẻ mới của follower; leader đã gen nháp riêng mới vẫn bị nhóm cũ tính theo task cũ. Hồi quy 2 ca ĐỎ (2 failed/25 deselected), sửa trong `_clip_groups`: dùng take non-final mới nhất; follower mới chỉ giữ nhóm nếu `group_leader` trỏ đúng job. Routing refs BẬT cũng không ghép trở lại membership đã supersede; test cả BẬT/TẮT.
- Lượt xanh đầu sau sửa: 128 passed/56,36 s (đủ 8 file liên quan, gồm các guard worker thêm sau 125 xanh). Xác nhận guard routing BẬT: 128 passed/51,08 s.
- Giữ runner thật MockVideoProvider nhóm follower xanh; chứng minh stamp `source_job_id` + `input_hash`, membership/task leader và motion lệch phải gen lại. Không dựng gói SHA tay để giả bằng chứng runner.
- Giới hạn provenance: `_finish_group` hiện ghi stamp follower khi tải/cắt, không có ánh xạ original SHA ↔ derivative marked SHA trước khi gửi. Chưa chứng minh bytes ảnh gốc không đổi giữa submit/download hoặc ghi đè cùng job/path; phải bổ sung provenance runner sau #24. Không tự đoán mapping ảnh marked.
- `draft_seconds` clip lẻ ưu tiên probe file local thực tế trước usage/motion (hồi quy file 5,5 s vs usage/gói 4 s: ĐỎ 1 ca rồi sửa). Clip nhóm ưu tiên usage_events / duration trong gói đã gửi: đây là giây submit/tính tiền, chưa phải đối chiếu duration nhà cung cấp; fallback sent_group là metadata lúc submit. File nhóm chỉ là fallback vì leader có thể đã bị cắt, không còn full task. URL/UNC không probe. Không gọi API/data thật để đo lại.
- Leader gen lại riêng: follower còn thuộc task cũ không bị gán sang task mới; khi không giữ được leader lịch sử hiện tính riêng bảo thủ (có thể dư), chưa chứng minh nâng/cắt riêng subgroup. Nối runner/caller sau #24.
- Đơn giá 0,5254 chỉ route nháp Seedance 2.5 480p → 1080p 9:16; nguồn hộp thư/CODEX_TASKS #24 job670–676, 38 s/19,964 USD. Rà không đọc task_usage thật; đường khác ×1,5 vẫn là ước tính.
- `run_estimate`/`e1_estimate` nhánh giá chưa biết còn mẫu `or 0` cũ; phạm vi Đ10v3 xử lý ref chưa biết bằng 15 s/ref nên không rơi zero do ref. Model/pricing không biết toàn hệ thống và project_budget mục2 vẫn cần bước riêng sau #24.
- Không commit/push/TODO/PLAN/runner/file #24/data thật/API. Root đọc phần sửa và chốt.

- Xác nhận cuối sau bổ sung duration file thực tế: **129 passed / 58,90 s**, 8 file liên quan; `git diff --check` xanh. Rà bắt/sửa 3 ca (2 membership lịch sử + 1 ưu tiên giây file lẻ); không chạy cả bộ.
