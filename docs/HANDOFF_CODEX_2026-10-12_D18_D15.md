# Bàn giao Codex sau Đ18 và Đ15 việc3 — 12/10/2026

- Đ18v1 plan: codex/d18-viec1-ke-hoach-san-khau HEAD d52253e6; chỉ tài liệu, đã push.
- Đ18v2 neo nhóm: codex/d18-viec2-anh-neo-theo-spot code f89cbad6 / HEAD cb62a4dd, 50test xanh; đã push.
- Đ18v3 UI giữ bố cục: codex/d18-viec3-giu-bo-cuc code5865a18 / HEAD50a3508a, 27test xanh +2PNG Chrome1440/1280, đã push.
- Đ15v3 vùng an toàn: code d864175d trên codex/d15-viec3-vung-an-toan, 99test xanh/24,12s; 3P2 và overshoot đã sửa, root đọc diff; OFF baseline pixels giữ. Ghi kết quả rồi push cùng bàn giao này. HUD outline chưa đo, sản xuất/cả bộ Windows chưa làm.
- Đ18v4 vẫn chờ người dùng chọn A trước→B / B ngay / C để sau. Không tự chọn, chưa gọi API.
- Bước kế: Đ12v5 tiếp D:/AI-Video-Pipeline/.codex-wt/d12-viec5-dong-thanh nhánh codex/d12-viec5-dong-thanh codeWIPd197de0c đãpush; backend50test xanh đã rà, còn QA component GUI1440/1280 với DB/ASSET_DIR/temp rồi ghi kết quả. Đối chiếu main mới, tránh nhân đôi dependency. Sau đó Đ11v1b (cần bảng đánh giá/duyệt thiết kế), các việc còn lại theo bảng đầu CODEX_TASKS main.
- Origin/main lần đọc cuối62702921 đã gộp Đ17v3/layout_from_follow/send_claim, không làm lại. Khi tiếp gitfetch, đọc AGENTS/CLAUDE/CHUAN/skill/HỘP THƯ/Sổ việc/bảng ưu tiên main mới nhất.
- Người dùng mới yêu cầu lên lịch tự tiếp: automation ti-p-t-c-c-c-vi-c-codex-c-n-l-i-sau-reset ACTIVE, chạy một lần04:00 13/10 Asia/Saigon sau reset03:51:02. Có thể dời chính lịch sau reset kế tiếp nếu chạm ngưỡng, không tạo trùng. Lịch monitorquota cũ vẫn PAUSED.
- Hạn mức lúc chốt code: 5h ĐÃ DÙNG71%, CÒN29%; tuần38% dùng. Không resetcredit/muacredit. >=60 một child,70–90 việc nhỏ,>=80thu nhỏ,>=90lưu push nghỉ.
- Không mainmerge/livepull/restart/branchchange; không data thật/env/secrets/admin_auth/paidAPI. Các cờ mới OFF; chỉ push nhánh riêng. Không sửa TODO/PLAN, areasversion giữ.
- GUI QA Streamlit tạm8519 của Đ18 đã dừng, không động8501/8502. RasterPIL Đ15 không thayUI, không bịa1440/1280.
