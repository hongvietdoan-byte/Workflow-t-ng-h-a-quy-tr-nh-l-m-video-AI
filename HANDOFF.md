# Bàn giao Đ20 việc 6

- Nhánh `codex/d20-viec6-so-loi`, nền `8a2296aa`; mã commit xem `git log -1`.
- Hoàn tất trang Sổ lỗi chỉ đọc + lọc/coverage/cảnh báo hợp đồng, sửa đếm items/schema và viền khâu theo lỗi mở.
- 9 test đỏ trước → 52 test xanh cuối (10,26s), có AppTest thật + fake Streamlit + XML regression; root RÀ NHẸ đã bắt/sửa alias số gây crash.
- Báo cáo: `docs/RA_D20_VIEC6_CODEX_2026-10-20.md`.
- Chưa push/gộp, chưa cả bộ Windows/slow, chưa live; không API, data thật, env thật, TODO/plan/version.
- Phiên chính tiếp: đọc diff, chạy kiểm tích hợp, xử lý trạng thái/gộp/push/restart theo quy trình. Không cần độc lập RÀ KỸ vì không thêm quyền/đường ghi.
- `.test-home/` untracked chỉ chứa fixture; không commit. Auto-review từ chối thao tác dọn exact path, không bypass.
