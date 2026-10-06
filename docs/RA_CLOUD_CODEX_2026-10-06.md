# Rà hai nhánh cloud — 06/10/2026

Nguồn: `claude/read-s14-45-cloud-tasks-ngb0q2-v2` (`95f7a6d`) và `cloud/S14.25` (`528cfbf`), đối chiếu bàn giao `main` (`881f93b`). Nhánh tích hợp: `codex/s14-cloud-review`.

## Phạm vi giữ lại

- S14.45: số đo quy trình trong `devsys/workflow_runs.jsonl`, nhập từ kế hoạch và trang Hiệu quả quy trình.
- S14.24: agent chấm bài học **chế độ bóng**, cờ `lesson_judge` mặc định tắt. Chỉ ghi `lesson_reviews`; không tự duyệt bài hay sửa knowledge. Claude qua client có sổ chi, nhãn `lesson_judge`; nút có giá, ghi thêm tối đa hai lượt khi JSON hỏng.
- S14.25 Đợt 6a: góp ý thấp chuyển thành mistakes, cờ `feedback_to_mistakes` mặc định tắt, giữ van 3 lần / 2 dự án / người duyệt; chống ghi trùng bằng `(source, ref_id)`.
- S14.50: bản đồ Ai quyết và kiểm các điểm trỏ tới code.
- S14.51: bảng màu nhân vật, chỉ ghi chú `uncertain`, không tự loại/gen lại; cờ `palette_check` mặc định tắt.
- P1: thời gian lời gọi Claude và `request-id`; migration thêm cột, giữ tương thích constructor `HttpResponse` cũ.
- S14.29: chỉ bản lưu `docs/cat_giu/S14_29_ma_thiet_bi/`, **không có code tính năng đã bỏ**.

## Lỗi tìm được và sửa (test đỏ → xanh)

1. `lesson_judge.judge`: client ném `LlmError` làm dừng cả lượt chấm, không ghi van không gọi được Claude. Bắt đúng lỗi, ghi diag + `needs_human`, không tự gọi lại khi lỗi này; bài học/knowledge không đổi. Test `test_transport_failure_records_the_no_claude_valve`.
2. `lesson_judge.agreement`: bài học đã sửa nội dung vẫn được so với đánh giá cũ, có thể báo đủ chỉ tiêu sai. Chỉ tính đánh giá mới nhất có `body_hash` khớp bản hiện tại. Test `test_agreement_ignores_a_review_of_the_previous_body`.
3. `palette.character_palette`: file tham chiếu mất/không đọc được làm phép QC ném lỗi ở bước SHA. Trả lý do không đo được; không dùng bảng màu cũ để đoán. Test `test_missing_reference_reports_not_measurable_without_breaking_qc`.

Lỗi thiếu import `Optional` ở `step1_characters` đã lấy sửa vào G-a vì chặn Dashboard ngay từ lúc import.

## Kiểm thử

- Trước sửa: 77 test cloud qua; ba test hồi quy mới đỏ đúng nguyên nhân.
- Sau sửa: 80 test (`lesson_judge`, `s1451_palette`, `p1_llm_latency`, `devsys_workflow`, `devsys_decisions`) qua; 90 test (`s1425_feedback_mistakes`, `lessons`, `lesson_judge`, `devsys`) qua.
- Chưa chạy cả bộ bản tích hợp G-a + hai nhánh cloud. Chưa gộp/push `main`.
- Không gọi API trả phí, không có dữ liệu máy chính; chưa chạy UI thật trên Windows hoặc khởi động lại 8501/8502.
- Không có công cụ đo token Codex tương ứng số đo Claude; không bịa token làm/rà/sửa để ghi vào workflow.
