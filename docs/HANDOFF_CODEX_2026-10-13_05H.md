# Bàn giao Codex — 13/10/2026, lượt sau reset

Đọc AGENTS/CLAUDE/CHUAN/skill, git fetch origin, HỘP THƯ/Sổ việc và bảng đầu CODEX_TASKS trên origin/main mới nhất. Chỉ push nhánh riêng, không main/live pull/restart.

## Đã hoàn tất và push, không làm lại
- Đ18v1 kế hoạch: codex/d18-viec1-ke-hoach-san-khau d52253e6.
- Đ18v2 neo nhóm: code f89cbad6, HEAD6e80e98e (chuẩn hóa xuống dòng kết quả), 50 test.
- Đ18v3 UI: code5865a18, HEAD80dfcf6a (chuẩn hóa xuống dòng),27 test và2PNG.
- Đ15v3 vùng an toàn: coded864175d, HEAD37bfd9f0,99 test.
- Đ12v5 đồng thanh: backendWIPd197de0c, QA/nhãn4d7bb244, HEAD157084cf;51 test +2PNG; backend đã rà trước, chưa xác minh từng chữ≤60ms (proxy onset), chưa thử model thật.
- Đ14v3 âm local: code36be2286, HEAD18a66c64,131test +focusedcleanup;5P2 sửa,2PNG Windows; chưa nguồnGthật/Unix.
- Đ10v3b ngân sách gộp: code27c2e9f3, ghi kết quả/push cùng bàn giao này;146 test riêng biệt +4PNG;3P2 đã sửa và root đọc diff. Chưa production/cả bộ.

## Việc chờ người dùng
- Đ11v1b: codex/d11-viec1b-doi-chieu tại worktree cùng tên, tài liệu63fb5000 HEADb7a73d73; bảng20mục và9c đã push, CHƯA HTML/mockup mới. Câu hỏi async đang chờ chốt mockup gọn/điều chỉnh/để sau theo luật CODEX_TASKS(c). Không tự coi im lặng là duyệt.
- Đ18v4: phương án A trước→B/B ngay/C để sau vẫn chờ, chưa được duyệt; không bắt đầu backend sân khấu.
- Nhóm runner sau#24 vẫn chờ người dùng/phiên máy chính chốt, #27 đang chạy. Không runner/usage/follower/cut/seedance_refs; cloud tài khoản khác đang làm locomotion/ambient/xdist, tránh nhân đôi.

## Bước kế
Nếu chưa có câu trả lời mockup, bỏ qua phần chờ và làm Đ12v6 phát âm TTS; sau đó phần còn lại Đ13v4 (trừ phần đã gộp/project_budget/FALLBACK đã xong), Đ11v2/v4, Đ12v2–4, Đ13v1–3, Đ11v5 và các phần đã được phép theo bảng main mới nhất. Mỗi việc một worktree/nhánh từ origin/main. Đối chiếu dependency trước sửa; Đ12v5 branch cũ baseb8782dfe, các nhánh mới base3d6004bb, chưa cherry-pick main thêm vào nhánh dở.

Test đỏ→xanh, chỉ nhóm liên quan, RÀ KỸ riêng tiền/dữ liệu/quyền/caller CLAUDE7; register code/tests/flags giữ version; giữ keys. Không nới test, không API tốn tiền/data thật/env/secrets/admin_auth/maintenance worker/TODO/PLAN. GUI dùng DB/ASSET_DIR/DATA/flags/knowledge tạm, ảnh docs/images; không thử dịch vụ/model thật khi chưa duyệt trần.

## Hạn mức và lịch
5h đã dùng80%, còn20%; tuần51% dùng. Reset dự kiến09:00:13 13/10 Asia/Saigon. Dời chính automation ti-p-t-c-c-c-vi-c-codex-c-n-l-i-sau-reset sang09:05 cùng ngày, một lần, không tạo trùng/monitorquota. Lượt sau gọi get_usage_limits trước; không resetcredit/mua credit. >=60 chỉ một child,70–90 chỉ việc nhỏ,>=80thu nhỏ,>=90lưu push/nghỉ. Người dùng đã yêu cầu tự tiếp sau reset; cập nhật cùng lịch ở điểm nghỉ tiếp theo, xóa khi mọi việc được phép đã xong.

QA Streamlit tạm8519/8527 của lượt này đã dừng đúng process; không động8501/8502. Hai local handoff untracked ở nhánh Đ12v5 được giữ, không commit.
