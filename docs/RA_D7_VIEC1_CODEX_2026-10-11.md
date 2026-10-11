# Rà Đợt 7 việc 1 — Codex, 11/10/2026

Nhánh `codex/d7-viec1-thiet-ke`, base `229f812`. RÀ NHẸ tài liệu; tự kiểm theo mục 2b.5 của `.claude/skills/vong-lam-viec-theo-plan/SKILL.md`, chưa phải rà độc lập. Không pytest vì chỉ tài liệu; chưa gộp hoặc chạy sản xuất/API/Blender.

| Mục đề bài | Bằng chứng | Kết quả |
|---|---|---|
| 1. Chốt, hai cấp, bốn lớp, luồng, quyền và tiền | Nghiên cứu B/C/Các chốt; thiết kế mục 1 | Đủ; thay đề xuất cũ theo chốt 11/10 |
| 2. Nơi phiếu, năm bảng và schema | Thiết kế mục 2; nghiên cứu Dữ liệu | Đủ; đề xuất AI Dev System, bảng cùng manifest; answers không phải ticket |
| 3. experience_cases | Nghiên cứu lớp 4; kiểm kê bổ sung | Đủ; nguồn core/experience.py:26–29 |
| 4. Gói gửi kèm | Thiết kế mục 3 | Đủ; scenes.data.package_overrides, sent_package bất biến, nối cuối gói, undo/quote/audit |
| 5. Pet desktop | Thiết kế mục 4; nghiên cứu C | Đủ; ba cách, broker chỉ đọc/login, toast/dedupe, chỉ mở Dashboard |
| 6. Bộ 42 ca | Thiết kế mục 5; nghiên cứu D | Đủ định dạng/nơi/provenance C01–09/evalset/chấm/chi/pilot 8 ca; C09 hoãn không tính đạt |
| 7. Tần suất × công từng tính năng | Thiết kế mục 6 | Đủ 22 hàng; hai trục F/công, chỉ số xếp F/công, nguồn giả thuyết; hai gói ở Đợt 1 |
| 8. Câu hỏi mở | Nghiên cứu Còn mở | Đủ ba câu kèm đề xuất; không hỏi lại bảy chốt |
| 9. Stale endframe | Thiết kế mục 7, variant C04, kiểm kê | Đủ; usable_path:56–62, UI/nút/quote trước enqueue |
| 10. Bốn tham chiếu | Kiểm kê và thiết kế mục 7 | Đủ; unlock:292, lessons:217–223, prep đặt người lên background, L13:24–31 |

Tự rà đã sửa:

- Mâu thuẫn cap người/ngày, opt-in, điện thoại gần, SLA 1 giờ/1 ngày và đồng nghiệp thấy phiếu: thay bằng dự án 2 USD/80%, hạn 3 ngày, phiếu ngầm, hoãn mobile.
- `usage_ledger` chỉ là tên khái niệm. Sổ thật: usage_events, llm_calls, core/cost.py:756 và core/llm_runner.py:615–623; bỏ tên module không tồn tại.
- cast_missing hiện VÀNG ở runner; tách khỏi ĐỎ editor đề xuất, không viết lại package_problem.
- Kiểm refs lần đầu bắt change_review_ui.py:8–37 vượt file 36 dòng; sửa thành 8–36. Bốn refs đề bài đã loại phiên bản cũ.
- Không giả 42 ca đạt khi C09 hoãn: báo 41 active + 1 deferred, cổng đủ 42 vẫn chờ thử/chốt bộ thay thế. Pilot 8 ca không mở worker tự động.
- Giá cache hit Sonnet 5.5 = 0,20 USD/MTok (input 2 × 0,1). Rà 11/10: câu cũ "nguồn ghi 0,10" là sai, đã bỏ.
- Chuẩn hóa khoảng trắng và bảng; giải thích ma trận tần suất × công sức trước chỉ số F/công.

Kiểm 2b.5: không đổi/nới test; không đọc/ghi dữ liệu thật hoặc dashboard.env; fixture và hook là thiết kế scoped server, không path chat tùy ý/CWD. Không đổi code/luồng bấm tay, autopilot, v2/v3/storyboard; điểm nối để sau #24. Không bật mặc định, không thêm parse/so chữ bỏ dấu. Cách ly OS/broker, session admin 8502, pet/toast/DPI chưa thử; worktree không được coi sandbox. Tách nhãn “Gói đã gửi”/“Gói gửi kèm” và bậc thao tác/hai trợ lý. Chi API cần duyệt riêng; pet không duyệt/gen; lô bảo trì chỉ sau admin cho phép.

Bằng chứng cục bộ: **42 mã C01–C42 duy nhất**, **123 tham chiếu file:dòng trong giới hạn**, **12 link nội bộ tồn tại**, `git diff --check` xanh. Script kiểm chỉ đo tồn tại/phạm vi, không chứng minh mọi số dòng kế thừa Đợt 5 đúng nghĩa; nguồn trọng tâm Đợt 7 đã mở trực tiếp. Không tuyên bố đã sửa/thử sản xuất.

Rủi ro và việc mở: nơi lưu phiếu, API hay CLI, ngưỡng lessons; C09 hoãn/cổng 42; session admin 8502, broker chỉ đọc và worker cách ly cần triển khai/rà kỹ/thử thật. Không push/gộp; TODO/PLAN/CODEX_TASKS do phiên chính ghi.
